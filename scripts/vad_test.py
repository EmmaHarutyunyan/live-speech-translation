"""Run the VAD segmenter on a recorded WAV, fed in 10 ms blocks like live audio (milestone M2).

Prints each detected phrase and saves it as a WAV in recordings/segments/<file name>/ (git-ignored).
"Detected after" = how long after the end of the phrase the segmenter reported it
(this delay counts towards the 5-second latency budget).

Run from the project folder, e.g.:
    .\\.venv\\Scripts\\python.exe scripts\\vad_test.py recordings\\20261023-193822_laptop_mic.wav
"""

import argparse
import sys
import time
import wave
from pathlib import Path

import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from hylive.audio_convert import TARGET_RATE, Resampler, to_float32_frames, to_mono  # noqa: E402
from hylive.segmenter import Segmenter, load_vad_model  # noqa: E402

BLOCK_SECONDS = 0.010  # live capture delivers 10 ms blocks


def write_wav(path: Path, audio: np.ndarray) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(TARGET_RATE)
        wav.writeframes((np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16).tobytes())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wav", type=Path)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--min-silence-ms", type=int, default=500)
    parser.add_argument("--max-segment-s", type=float, default=10.0)
    args = parser.parse_args()

    with wave.open(str(args.wav), "rb") as wav:
        if wav.getsampwidth() != 2:
            raise ValueError("Expected a 16-bit WAV file (as written by record_test.py).")
        channels, in_rate = wav.getnchannels(), wav.getframerate()
        frames = to_float32_frames(wav.readframes(wav.getnframes()), channels)
    if len(frames) == 0:
        raise ValueError(f"{args.wav} contains no audio.")

    model = load_vad_model()
    segmenter = Segmenter("mic", model, threshold=args.threshold,
                          min_silence_ms=args.min_silence_ms, max_segment_s=args.max_segment_s)
    resampler = Resampler(in_rate)
    block = int(in_rate * BLOCK_SECONDS)
    starts = range(0, len(frames), block)

    segments = []
    t0 = time.perf_counter()
    for i, start in enumerate(starts):
        audio16k = resampler.process(to_mono(frames[start:start + block]), last=(i == len(starts) - 1))
        stream_time = (start + block) / in_rate  # simulated "now": how much audio has arrived so far
        segments += segmenter.process(audio16k, now=stream_time)
    segments += segmenter.flush(now=len(frames) / in_rate)
    processing = time.perf_counter() - t0

    out_dir = PROJECT_DIR / "recordings" / "segments" / args.wav.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(frames) / in_rate
    print(f"{args.wav.name}: {total:.2f} s | threshold {args.threshold}, min silence "
          f"{args.min_silence_ms} ms, max segment {args.max_segment_s} s\n")
    print(f"{'#':>3}  {'start':>6}  {'end':>6}  {'dur':>5}  {'detected after':>14}  file")
    for n, seg in enumerate(segments, 1):
        path = out_dir / f"seg{n:02d}.wav"
        write_wav(path, seg.audio)
        print(f"{n:>3}  {seg.start_s:6.2f}  {seg.end_s:6.2f}  {seg.end_s - seg.start_s:5.2f}  "
              f"{seg.ended_at - seg.end_s:13.2f}s  {path.relative_to(PROJECT_DIR)}")
    speech = sum(seg.end_s - seg.start_s for seg in segments)
    print(f"\n{len(segments)} phrases, {speech:.1f} s of speech in {total:.1f} s of audio")
    print(f"processing time {processing:.2f} s ({processing / total:.3f} s per second of audio)")


if __name__ == "__main__":
    main()
