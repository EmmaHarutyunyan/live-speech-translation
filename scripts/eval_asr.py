"""Measure Armenian ASR accuracy on the evaluation set (milestone M3).

Each eval/audio/evalNN.wav goes through the same path as the live program
(mono -> 16 kHz -> VAD segmenter -> Whisper); the text is compared with eval/sentences.txt.
CER = character error rate after normalisation (lower case, no punctuation, "եւ" -> "և").

Run from the project folder, e.g.:
    .\\.venv\\Scripts\\python.exe scripts\\eval_asr.py --beam-size 1
    .\\.venv\\Scripts\\python.exe scripts\\eval_asr.py --beam-size 5 --prompt
"""

import argparse
import re
import sys
import time
import wave
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from hylive.asr import Transcriber  # noqa: E402  (imported first: registers the NVIDIA DLLs)
from hylive.audio_convert import Resampler, to_float32_frames, to_mono  # noqa: E402
from hylive.segmenter import Segmenter, load_vad_model  # noqa: E402

SENTENCES_FILE = PROJECT_DIR / "eval" / "sentences.txt"
AUDIO_DIR = PROJECT_DIR / "eval" / "audio"
# Neutral Armenian context for --prompt ("This is an Armenian conversation. We speak Armenian.").
# Deliberately shares no words with the evaluation sentences, so it cannot "give away" answers.
PROMPT = "Սա հայերեն խոսակցություն է։ Մենք խոսում ենք հայերեն։"
BLOCK_SECONDS = 0.010


def normalise(text: str) -> str:
    text = text.lower().replace("եւ", "և")
    text = re.sub(r"[^\w\s]", "", text)  # removes punctuation, incl. Armenian ։ ՞ ՛ ՜ ,
    return re.sub(r"\s+", " ", text).strip()


def edit_distance(a, b) -> int:
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def phrases_from_wav(path: Path, vad_model) -> list:
    with wave.open(str(path), "rb") as wav:
        channels, rate = wav.getnchannels(), wav.getframerate()
        frames = to_float32_frames(wav.readframes(wav.getnframes()), channels)
    segmenter = Segmenter("mic", vad_model)
    resampler = Resampler(rate)
    block = int(rate * BLOCK_SECONDS)
    starts = range(0, len(frames), block)
    segments = []
    for i, start in enumerate(starts):
        audio16k = resampler.process(to_mono(frames[start:start + block]), last=(i == len(starts) - 1))
        segments += segmenter.process(audio16k, now=0.0)
    return segments + segmenter.flush(now=0.0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--beam-size", type=int, default=1)
    parser.add_argument("--prompt", action="store_true", help=f"use initial_prompt: {PROMPT}")
    args = parser.parse_args()

    sentences = [line.split("\t", 1) for line in SENTENCES_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    missing = [sid for sid, _ in sentences if not (AUDIO_DIR / f"eval{sid}.wav").exists()]
    if missing:
        raise FileNotFoundError(f"Missing recordings for {missing}. Run scripts/record_eval.py first.")

    vad_model = load_vad_model()
    transcriber = Transcriber(args.model, beam_size=args.beam_size, initial_prompt=PROMPT if args.prompt else None)
    transcriber.warm_up()
    setting = f"model {args.model}, beam {args.beam_size}, prompt {'on' if args.prompt else 'off'}"
    print(f"\nSetting: {setting}\n")

    total_edits = total_chars = 0
    times = []
    for sid, reference in sentences:
        segments = phrases_from_wav(AUDIO_DIR / f"eval{sid}.wav", vad_model)
        t0 = time.perf_counter()
        hypothesis = " ".join(transcriber.transcribe(s.audio) for s in segments).strip()
        times.append(time.perf_counter() - t0)
        ref, hyp = normalise(reference), normalise(hypothesis)
        edits = edit_distance(ref, hyp)
        total_edits += edits
        total_chars += len(ref)
        print(f"[{sid}] CER {100 * edits / len(ref):5.1f} %  {times[-1]:.2f} s  {len(segments)} phrase(s)")
        print(f"     ref: {reference}")
        print(f"     hyp: {hypothesis or '(nothing recognised)'}")

    print(f"\nRESULT ({setting}): CER {100 * total_edits / total_chars:.1f} % over {len(sentences)} sentences, "
          f"ASR time avg {sum(times) / len(times):.2f} s, max {max(times):.2f} s")


if __name__ == "__main__":
    main()
