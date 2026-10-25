"""Play evaluation recordings through the speakers, as a "call side" with a known transcript (milestone M6).

Run this in a SECOND PowerShell window while `python -m hylive` runs in the first one. The live program
hears the clips via loopback, and its Armenian output can be compared with eval/sentences.txt (CER).

Run from the project folder, e.g.:
    .\\.venv\\Scripts\\python.exe scripts\\play_eval.py                       (all 10 clips, 2 s apart)
    .\\.venv\\Scripts\\python.exe scripts\\play_eval.py --ids 01,02,03,04,05 --gap 7
"""

import argparse
import time
import wave
from pathlib import Path

import pyaudiowpatch as pyaudio

PROJECT_DIR = Path(__file__).resolve().parent.parent
SENTENCES_FILE = PROJECT_DIR / "eval" / "sentences.txt"
AUDIO_DIR = PROJECT_DIR / "eval" / "audio"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", help="comma-separated sentence ids (default: all)")
    parser.add_argument("--gap", type=float, default=2.0, help="seconds of silence between clips")
    parser.add_argument("--start-delay", type=float, default=3.0, help="seconds before the first clip")
    args = parser.parse_args()

    sentences = dict(line.split("\t", 1) for line in SENTENCES_FILE.read_text(encoding="utf-8").splitlines()
                     if line.strip())
    ids = [i.strip() for i in args.ids.split(",")] if args.ids else list(sentences)
    unknown = [i for i in ids if i not in sentences]
    if unknown:
        raise ValueError(f"Unknown sentence ids: {unknown}")

    p = pyaudio.PyAudio()
    try:
        out_index = p.get_host_api_info_by_type(pyaudio.paWASAPI)["defaultOutputDevice"]
        print(f"playing on [{out_index}] {p.get_device_info_by_index(out_index)['name']}")
        time.sleep(args.start_delay)
        for n, sid in enumerate(ids):
            with wave.open(str(AUDIO_DIR / f"eval{sid}.wav"), "rb") as wav:
                stream = p.open(format=p.get_format_from_width(wav.getsampwidth()), channels=wav.getnchannels(),
                                rate=wav.getframerate(), output=True, output_device_index=out_index)
                print(f"[{time.strftime('%H:%M:%S')}] playing {sid}: {sentences[sid]}", flush=True)
                stream.write(wav.readframes(wav.getnframes()))
                stream.stop_stream()
                stream.close()
            if n < len(ids) - 1:
                time.sleep(args.gap)
        print("done")
    finally:
        p.terminate()


if __name__ == "__main__":
    main()
