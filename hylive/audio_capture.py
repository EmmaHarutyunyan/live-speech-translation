"""Audio capture from WASAPI devices (microphone and speaker loopback).

Output of this module: `AudioChunk` objects put on a queue, in the device's
native format (16-bit integer samples, device sample rate and channel count).
Conversion to 16 kHz mono for the speech model happens later (M2).
"""

import queue
import time
from dataclasses import dataclass

import pyaudiowpatch as pyaudio

SAMPLE_FORMAT = pyaudio.paInt16  # 16-bit samples
SAMPLE_WIDTH_BYTES = 2
FRAMES_PER_BUFFER = 480          # 10 ms at 48 kHz: how often the callback is called


@dataclass(frozen=True)
class DeviceInfo:
    index: int
    name: str
    sample_rate: int
    channels: int
    is_loopback: bool


@dataclass(frozen=True)
class AudioChunk:
    source: str          # "mic" or "system"
    data: bytes          # raw 16-bit samples, channels interleaved
    captured_at: float   # time.monotonic() when the block arrived


def _to_device_info(info: dict) -> DeviceInfo:
    return DeviceInfo(
        index=info["index"],
        name=info["name"],
        sample_rate=int(info["defaultSampleRate"]),
        channels=info["maxInputChannels"],
        is_loopback=info["isLoopbackDevice"],
    )


def get_device(p: pyaudio.PyAudio, index: int) -> DeviceInfo:
    """Look up a device by index; it must be a recordable WASAPI device."""
    wasapi_index = p.get_host_api_info_by_type(pyaudio.paWASAPI)["index"]
    info = p.get_device_info_by_index(index)
    if info["hostApi"] != wasapi_index:
        raise ValueError(f"Device {index} ({info['name']}) is not a WASAPI device. Run scripts/list_devices.py.")
    if info["maxInputChannels"] == 0:
        raise ValueError(f"Device {index} ({info['name']}) cannot be recorded (it is an output device).")
    return _to_device_info(info)


def default_mic(p: pyaudio.PyAudio) -> DeviceInfo:
    return get_device(p, p.get_host_api_info_by_type(pyaudio.paWASAPI)["defaultInputDevice"])


def default_loopback(p: pyaudio.PyAudio) -> DeviceInfo:
    return _to_device_info(p.get_default_wasapi_loopback())


class DeviceCapture:
    """Records one device. PortAudio calls `_callback` on its own thread for every block."""

    def __init__(self, p: pyaudio.PyAudio, device: DeviceInfo, source: str, out_queue: queue.Queue):
        self.p = p
        self.device = device
        self.source = source
        self.out_queue = out_queue
        self.status_flag_count = 0   # blocks where PortAudio reported a problem (e.g. lost audio)
        self.stream = None

    def _callback(self, in_data, frame_count, time_info, status):
        if status:
            self.status_flag_count += 1
        self.out_queue.put(AudioChunk(self.source, in_data, time.monotonic()))
        return (None, pyaudio.paContinue)

    def start(self) -> None:
        self.stream = self.p.open(
            format=SAMPLE_FORMAT,
            channels=self.device.channels,
            rate=self.device.sample_rate,
            input=True,
            input_device_index=self.device.index,
            frames_per_buffer=FRAMES_PER_BUFFER,
            stream_callback=self._callback,
        )

    def stop(self) -> None:
        self.stream.stop_stream()
        self.stream.close()


def recordable_devices(p: pyaudio.PyAudio) -> list[DeviceInfo]:
    """All WASAPI devices that can be recorded: microphones and loopback devices."""
    wasapi_index = p.get_host_api_info_by_type(pyaudio.paWASAPI)["index"]
    devices = []
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info["hostApi"] == wasapi_index and info["maxInputChannels"] > 0:
            devices.append(_to_device_info(info))
    return devices


def output_device_for_loopback(p: pyaudio.PyAudio, loopback: DeviceInfo) -> dict:
    """Find the speaker (output) device that a loopback device records from: same name without ' [Loopback]'."""
    suffix = " [Loopback]"
    if not loopback.name.endswith(suffix):
        raise ValueError(f"Device {loopback.index} ({loopback.name}) is not a loopback device.")
    name = loopback.name[: -len(suffix)]
    wasapi_index = p.get_host_api_info_by_type(pyaudio.paWASAPI)["index"]
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if (info["hostApi"] == wasapi_index and info["maxOutputChannels"] > 0
                and not info["isLoopbackDevice"] and info["name"] == name):
            return info
    raise ValueError(f"No WASAPI output device named {name!r} found for loopback device {loopback.index}.")


class SilentOutput:
    """Plays digital silence (all zeros, inaudible) on the speakers that the loopback device records.

    WASAPI loopback delivers no data at all while nothing is playing (DECISIONS.md D-010). Keeping an
    output stream open makes Windows process the speakers continuously, so loopback keeps delivering blocks.
    """

    def __init__(self, p: pyaudio.PyAudio, loopback: DeviceInfo):
        self.p = p
        self.info = output_device_for_loopback(p, loopback)
        self._channels = self.info["maxOutputChannels"]
        self.stream = None

    def _callback(self, in_data, frame_count, time_info, status):
        return (bytes(frame_count * self._channels * SAMPLE_WIDTH_BYTES), pyaudio.paContinue)

    def start(self) -> None:
        self.stream = self.p.open(
            format=SAMPLE_FORMAT,
            channels=self._channels,
            rate=int(self.info["defaultSampleRate"]),
            output=True,
            output_device_index=self.info["index"],
            frames_per_buffer=FRAMES_PER_BUFFER,
            stream_callback=self._callback,
        )

    def stop(self) -> None:
        self.stream.stop_stream()
        self.stream.close()
