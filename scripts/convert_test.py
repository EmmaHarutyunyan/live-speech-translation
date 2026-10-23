"""Convert a recorded WAV to 16 kHz mono in 10 ms blocks, like live audio (milestone M2).

Writes <name>_16k.wav next to the input (git-ignored) and prints levels per channel,
so we can see whether averaging the two mic channels cancels the voice.

Run from the project folder, e.g.:
    .\\.venv\\Scripts\\python.exe scripts\\convert_test.py recordings\\20261023-182923_mic.wav
"""

import argparse
import sys
import wave
from pathlib import Path

import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from hylive.audio_convert import TARGET_RATE, Resampler, to_float32_frames, to_mono  # noqa: E402

BLOCK_FRAMES = 480  # same block size as live capture (10 ms at 48 kHz)


def level(x: np.ndarray) -> str:
    return f"peak {np.abs(x).max():.3f}, RMS {np.sqrt(np.mean(x ** 2)):.4f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wav", type=Path, help="a WAV file from recordings/")
    args = parser.parse_args()

    with wave.open(str(args.wav), "rb") as wav:
        if wav.getsampwidth() != 2:
            raise ValueError("Expected a 16-bit WAV file (as written by record_test.py).")
        channels, in_rate = wav.getnchannels(), wav.getframerate()
        data = wav.readframes(wav.getnframes())

    frames = to_float32_frames(data, channels)
    if len(frames) == 0:
        raise ValueError(f"{args.wav} contains no audio.")
    print(f"input:  {args.wav.name}: {len(frames) / in_rate:.2f} s, {in_rate} Hz, {channels} ch")

    # Levels per channel and after averaging (RMS = average loudness, peak = loudest sample).
    for ch in range(channels):
        print(f"  channel {ch}: {level(frames[:, ch])}")
    mono_full = to_mono(frames)
    print(f"  mono mix:  {level(mono_full)}")
    if channels == 2:
        corr = np.corrcoef(frames[:, 0], frames[:, 1])[0, 1]
        print(f"  channel correlation: {corr:+.2f}  (+1 = identical, 0 = unrelated, -1 = inverted -> voice cancels in the mix)")

    # Convert block by block, exactly like the live pipeline will.
    resampler = Resampler(in_rate)
    out_blocks = []
    starts = range(0, len(frames), BLOCK_FRAMES)
    for i, start in enumerate(starts):
        block = to_mono(frames[start:start + BLOCK_FRAMES])
        out_blocks.append(resampler.process(block, last=(i == len(starts) - 1)))
    out = np.concatenate(out_blocks)

    out_path = args.wav.with_name(args.wav.stem + "_16k.wav")
    with wave.open(str(out_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(TARGET_RATE)
        wav.writeframes((np.clip(out, -1.0, 1.0) * 32767).astype(np.int16).tobytes())

    print(f"output: {out_path.name}: {len(out) / TARGET_RATE:.2f} s, {TARGET_RATE} Hz, 1 ch, {level(out)}")


if __name__ == "__main__":
    main()
