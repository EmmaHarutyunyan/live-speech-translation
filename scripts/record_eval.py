"""Record the evaluation sentences one by one (milestone M3).

Shows each sentence from eval/sentences.txt, waits for Enter, records it from the microphone
and saves eval/audio/evalNN.wav in the device's native format (git-ignored: no audio in the repo).

Run from the project folder (headphones unplugged = laptop mic):
    .\\.venv\\Scripts\\python.exe scripts\\record_eval.py
    .\\.venv\\Scripts\\python.exe scripts\\record_eval.py --only 03     (re-record one sentence)
"""

import argparse
import queue
import sys
import time
import wave
from pathlib import Path

import numpy as np
import pyaudiowpatch as pyaudio

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from hylive.audio_capture import SAMPLE_WIDTH_BYTES, DeviceCapture, default_mic, get_device  # noqa: E402

SENTENCES_FILE = PROJECT_DIR / "eval" / "sentences.txt"
AUDIO_DIR = PROJECT_DIR / "eval" / "audio"
QUIET_PEAK = 0.02  # below this the recording is probably too quiet (laptop mic speech was ~0.14)


def load_sentences() -> list[tuple[str, str]]:
    lines = SENTENCES_FILE.read_text(encoding="utf-8").splitlines()
    return [tuple(line.split("\t", 1)) for line in lines if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mic", type=int)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--only", help="record only this sentence id, e.g. 03")
    args = parser.parse_args()

    sentences = load_sentences()
    if args.only:
        sentences = [s for s in sentences if s[0] == args.only]
        if not sentences:
            raise ValueError(f"No sentence with id {args.only} in {SENTENCES_FILE}")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    p = pyaudio.PyAudio()
    try:
        mic = get_device(p, args.mic) if args.mic is not None else default_mic(p)
        print(f"mic: [{mic.index}] {mic.name}\n")
        for sid, text in sentences:
            input(f"[{sid}] {text}\n     Press Enter, then read the sentence ({args.seconds:.0f} s) ...")
            chunks: queue.Queue = queue.Queue()
            capture = DeviceCapture(p, mic, "mic", chunks)
            capture.start()
            time.sleep(args.seconds)
            capture.stop()
            data = b"".join(chunks.get().data for _ in range(chunks.qsize()))
            peak = float(np.abs(np.frombuffer(data, dtype=np.int16)).max()) / 32768 if data else 0.0

            path = AUDIO_DIR / f"eval{sid}.wav"
            with wave.open(str(path), "wb") as wav:
                wav.setnchannels(mic.channels)
                wav.setsampwidth(SAMPLE_WIDTH_BYTES)
                wav.setframerate(mic.sample_rate)
                wav.writeframes(data)
            warning = "   <-- TOO QUIET? re-record with --only " + sid if peak < QUIET_PEAK else ""
            print(f"     saved {path.relative_to(PROJECT_DIR)}  peak {peak:.3f}  "
                  f"problem flags {capture.status_flag_count}{warning}\n")
    finally:
        p.terminate()


if __name__ == "__main__":
    main()
