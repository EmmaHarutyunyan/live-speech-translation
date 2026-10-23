"""List WASAPI audio devices (milestone M1, TESTS.md R1-1).

Shows only WASAPI devices: loopback (recording what the speakers play) exists
only in WASAPI, so we use WASAPI for the microphone too.

Run from the project folder:
    .\\.venv\\Scripts\\python.exe scripts\\list_devices.py
"""

import pyaudiowpatch as pyaudio


def device_type(info: dict) -> str:
    if info["isLoopbackDevice"]:          # field added by PyAudioWPatch
        return "LOOPBACK"
    if info["maxInputChannels"] > 0:
        return "INPUT"
    return "OUTPUT"


def main() -> None:
    p = pyaudio.PyAudio()
    try:
        wasapi = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_mic = wasapi["defaultInputDevice"]
        default_loopback = p.get_default_wasapi_loopback()["index"]

        print(f"WASAPI devices (host API index {wasapi['index']}):\n")
        print(f"{'idx':>4}  {'type':<8}  {'ch':>2}  {'rate':>6}  name")
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info["hostApi"] != wasapi["index"]:
                continue
            kind = device_type(info)
            channels = info["maxInputChannels"] if kind != "OUTPUT" else info["maxOutputChannels"]
            marker = ""
            if i == default_mic:
                marker = "   <-- default microphone"
            elif i == default_loopback:
                marker = "   <-- loopback of default speakers"
            print(f"{i:>4}  {kind:<8}  {channels:>2}  {int(info['defaultSampleRate']):>6}  {info['name']}{marker}")

        print("\nUse an INPUT index for --mic and a LOOPBACK index for --system.")
    finally:
        p.terminate()  # release PortAudio even if something above fails


if __name__ == "__main__":
    main()
