"""Segment a recorded WAV with VAD, then transcribe each phrase with faster-whisper (milestone M2).

Prints the Armenian text and the transcription time of each phrase.

Run from the project folder, e.g.:
    .\\.venv\\Scripts\\python.exe scripts\\asr_test.py recordings\\20261023-193822_laptop_mic.wav
    .\\.venv\\Scripts\\python.exe scripts\\asr_test.py recordings\\20261023-193822_laptop_mic.wav --model medium
"""

import argparse
import sys
import time
import wave
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from hylive.asr import Transcriber  # noqa: E402  (imported first: registers the NVIDIA DLLs)
from hylive.audio_convert import Resampler, to_float32_frames, to_mono  # noqa: E402
from hylive.segmenter import Segmenter, load_vad_model  # noqa: E402

BLOCK_SECONDS = 0.010


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wav", type=Path)
    parser.add_argument("--model", default="small", help="faster-whisper model name, e.g. small, medium, large-v3")
    parser.add_argument("--beam-size", type=int, default=1)
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

    # 1) Phrases, exactly as in vad_test.py
    segmenter = Segmenter("mic", load_vad_model(), min_silence_ms=args.min_silence_ms,
                          max_segment_s=args.max_segment_s)
    resampler = Resampler(in_rate)
    block = int(in_rate * BLOCK_SECONDS)
    starts = range(0, len(frames), block)
    segments = []
    for i, start in enumerate(starts):
        audio16k = resampler.process(to_mono(frames[start:start + block]), last=(i == len(starts) - 1))
        segments += segmenter.process(audio16k, now=(start + block) / in_rate)
    segments += segmenter.flush(now=len(frames) / in_rate)
    print(f"{args.wav.name}: {len(segments)} phrases\n")

    # 2) Load the model (downloads it the first time) and warm up
    t0 = time.perf_counter()
    transcriber = Transcriber(args.model, beam_size=args.beam_size)
    print(f"model '{args.model}' (beam {args.beam_size}) loaded in {time.perf_counter() - t0:.1f} s")
    t0 = time.perf_counter()
    transcriber.warm_up()
    print(f"warm-up: {time.perf_counter() - t0:.2f} s\n")

    # 3) Transcribe each phrase
    total_audio = total_time = 0.0
    for n, seg in enumerate(segments, 1):
        duration = seg.end_s - seg.start_s
        t0 = time.perf_counter()
        text = transcriber.transcribe(seg.audio)
        elapsed = time.perf_counter() - t0
        total_audio += duration
        total_time += elapsed
        print(f"[{n}] {seg.start_s:5.2f}-{seg.end_s:5.2f} s ({duration:.2f} s audio) -> transcribed in {elapsed:.2f} s")
        print(f"    HY: {text}")
    if segments:
        print(f"\ntotal: {total_audio:.1f} s audio transcribed in {total_time:.2f} s "
              f"({total_time / total_audio:.2f} s per second of audio)")


if __name__ == "__main__":
    main()
