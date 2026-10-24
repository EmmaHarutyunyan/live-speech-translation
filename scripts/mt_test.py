"""Translate a few Armenian sentences with NLLB and time it (milestone M2/M4).

Compares the correct sentence with the large-v3 transcription (with its spelling errors),
to see how much ASR errors hurt the English.

Run from the project folder:
    .\\.venv\\Scripts\\python.exe scripts\\mt_test.py
    .\\.venv\\Scripts\\python.exe scripts\\mt_test.py --device cuda
"""

import argparse
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from hylive.translate import Translator  # noqa: E402

SENTENCES = [
    ("reference, phrase 1", "Բարև, ես հիմա փորձարկում եմ իմ խոսափողը։"),
    ("large-v3,  phrase 1", "Վարև, ես իմ ապործարկում եմ խոսապողը։"),
    ("reference, phrase 2", "Համակարգչով ոչինչ միացված չէ։"),
    ("large-v3,  phrase 2", "համակարգթյով ոչինք միածված չէ։"),
    ("brief example", "Բարև, ինչպե՞ս ես։"),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    args = parser.parse_args()
    compute_type = "int8" if args.device == "cpu" else "int8_float32"

    t0 = time.perf_counter()
    translator = Translator(device=args.device, compute_type=compute_type)
    print(f"NLLB loaded on {args.device} ({compute_type}) in {time.perf_counter() - t0:.1f} s")
    t0 = time.perf_counter()
    translator.translate("Բարև")  # warm-up
    print(f"warm-up: {time.perf_counter() - t0:.2f} s\n")

    for label, text in SENTENCES:
        t0 = time.perf_counter()
        english = translator.translate(text)
        print(f"[{label}] {time.perf_counter() - t0:.2f} s")
        print(f"    HY: {text}")
        print(f"    EN: {english}")


if __name__ == "__main__":
    main()
