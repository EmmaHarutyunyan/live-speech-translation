"""Record microphone and system audio at the same time (milestone M1, TESTS.md R1-2, R1-3).

Saves two WAV files in recordings/ (git-ignored) and prints diagnostics.

Run from the project folder:
    .\\.venv\\Scripts\\python.exe scripts\\record_test.py --mic 9 --system 10 --seconds 15
Without --mic / --system, the Windows default microphone and the loopback of the
default speakers are used (and printed).
"""

import argparse
import queue
import re
import sys
import time
import wave
from pathlib import Path

import numpy as np
import pyaudiowpatch as pyaudio

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))  # so "import hylive" works when running this script

from hylive.audio_capture import (  # noqa: E402
    SAMPLE_WIDTH_BYTES, DeviceCapture, default_loopback, default_mic, get_device,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mic", type=int, help="microphone device index (see scripts/list_devices.py)")
    parser.add_argument("--system", type=int, help="loopback device index (see scripts/list_devices.py)")
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--label", help="added to the file names, e.g. laptop -> <time>_laptop_mic.wav")
    args = parser.parse_args()
    if args.label is not None and not re.fullmatch(r"[A-Za-z0-9_-]+", args.label):
        raise ValueError("--label may only contain letters, digits, _ and -")

    p = pyaudio.PyAudio()
    try:
        mic = get_device(p, args.mic) if args.mic is not None else default_mic(p)
        system = get_device(p, args.system) if args.system is not None else default_loopback(p)
        if mic.is_loopback:
            raise ValueError(f"--mic {mic.index} is a loopback device; choose an INPUT device.")
        if not system.is_loopback:
            raise ValueError(f"--system {system.index} is not a loopback device; choose a LOOPBACK device.")

        print(f"mic:    [{mic.index}] {mic.name} ({mic.sample_rate} Hz, {mic.channels} ch)"
              f"{'' if args.mic is not None else '  (Windows default)'}")
        print(f"system: [{system.index}] {system.name} ({system.sample_rate} Hz, {system.channels} ch)"
              f"{'' if args.system is not None else '  (default speakers)'}")

        chunks: queue.Queue = queue.Queue()
        captures = [DeviceCapture(p, mic, "mic", chunks), DeviceCapture(p, system, "system", chunks)]

        print(f"\nRecording {args.seconds:.0f} s ...")
        started = time.monotonic()
        for c in captures:
            c.start()
        time.sleep(args.seconds)
        for c in captures:
            c.stop()
        wall_seconds = time.monotonic() - started

        # Sort the received blocks by source.
        by_source = {"mic": [], "system": []}
        while not chunks.empty():
            chunk = chunks.get()
            by_source[chunk.source].append(chunk)

        out_dir = PROJECT_DIR / "recordings"
        out_dir.mkdir(exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        if args.label:
            stamp += f"_{args.label}"

        print(f"\nWall-clock time: {wall_seconds:.1f} s")
        for capture in captures:
            device = capture.device
            received = by_source[capture.source]
            data = b"".join(c.data for c in received)
            seconds_received = len(data) / (device.sample_rate * device.channels * SAMPLE_WIDTH_BYTES)
            samples = np.frombuffer(data, dtype=np.int16)
            peak = float(np.abs(samples).max()) / 32768 if samples.size else 0.0
            times = [c.captured_at for c in received]
            first_delay = times[0] - started if times else float("nan")
            largest_gap = max(np.diff(times), default=0.0) if len(times) > 1 else float("nan")

            path = out_dir / f"{stamp}_{capture.source}.wav"
            with wave.open(str(path), "wb") as wav:
                wav.setnchannels(device.channels)
                wav.setsampwidth(SAMPLE_WIDTH_BYTES)
                wav.setframerate(device.sample_rate)
                wav.writeframes(data)

            print(f"\n[{capture.source}] -> {path.relative_to(PROJECT_DIR)}")
            print(f"  audio received:   {seconds_received:.1f} s in {len(received)} blocks")
            print(f"  first block after {first_delay:.2f} s; largest gap between blocks {largest_gap:.3f} s")
            print(f"  peak level:       {peak:.3f}  (0 = silent, 1 = maximum)")
            print(f"  problem flags:    {capture.status_flag_count} blocks")
    finally:
        p.terminate()


if __name__ == "__main__":
    main()
