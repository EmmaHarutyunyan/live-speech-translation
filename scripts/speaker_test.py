"""Offline speaker-identification test on a recording with several voices (milestone M5).

Cuts the recording into phrases exactly like the live program (VAD, max 5 s), saves each phrase as
recordings/segments/<name>/segNN.wav so you can listen and note who speaks, computes a voice fingerprint per
phrase and prints the labels the online clustering would give for several thresholds.

Run from the project folder, e.g.:
    .\\.venv\\Scripts\\python.exe scripts\\speaker_test.py recordings\\<time>_twovoices_system.wav
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
from hylive.speakers import SpeakerEncoder, SpeakerTracker  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wav", type=Path)
    parser.add_argument("--thresholds", default="0.3,0.4,0.5,0.6")
    parser.add_argument("--max-segment-s", type=float, default=5.0)
    args = parser.parse_args()
    thresholds = [float(t) for t in args.thresholds.split(",")]

    with wave.open(str(args.wav), "rb") as wav:
        channels, rate = wav.getnchannels(), wav.getframerate()
        frames = to_float32_frames(wav.readframes(wav.getnframes()), channels)
    segmenter = Segmenter("system", load_vad_model(), max_segment_s=args.max_segment_s)
    resampler = Resampler(rate)
    block = int(rate * 0.010)
    starts = range(0, len(frames), block)
    segments = []
    for i, start in enumerate(starts):
        audio16k = resampler.process(to_mono(frames[start:start + block]), last=(i == len(starts) - 1))
        segments += segmenter.process(audio16k, now=0.0)
    segments += segmenter.flush(now=0.0)

    out_dir = PROJECT_DIR / "recordings" / "segments" / args.wav.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    encoder = SpeakerEncoder()
    print(f"{len(segments)} phrases; speaker model loaded in {time.perf_counter() - t0:.1f} s\n")

    embeddings, embed_times = [], []
    for n, seg in enumerate(segments, 1):
        with wave.open(str(out_dir / f"seg{n:02d}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(TARGET_RATE)
            w.writeframes((np.clip(seg.audio, -1, 1) * 32767).astype(np.int16).tobytes())
        t0 = time.perf_counter()
        embeddings.append(encoder.embed(seg.audio))
        embed_times.append(time.perf_counter() - t0)

    labels = {}
    for th in thresholds:
        tracker = SpeakerTracker(th)
        labels[th] = [tracker.assign(e, seg.end_s - seg.start_s) for e, seg in zip(embeddings, segments)]

    header = "  ".join(f"th {th:<12}" for th in thresholds)
    print(f"{'#':>3}  {'start':>6} {'dur':>5}   {header}")
    for n, seg in enumerate(segments):
        cells = "  ".join(f"{labels[th][n][0].replace('Speaker ', 'S'):<3} ({labels[th][n][1]:+.2f})  " for th in thresholds)
        print(f"{n + 1:>3}  {seg.start_s:6.1f} {seg.end_s - seg.start_s:5.1f}   {cells}")
    print("\nnumber of speakers found: " + ", ".join(
        f"th {th}: {len({l for l, _ in labels[th]})}" for th in thresholds))
    print(f"fingerprint time per phrase: avg {np.mean(embed_times):.2f} s, max {max(embed_times):.2f} s")
    print(f"phrases saved in {out_dir.relative_to(PROJECT_DIR)} (seg01.wav, seg02.wav, ...)")


if __name__ == "__main__":
    main()
