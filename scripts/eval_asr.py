"""Measure Armenian ASR accuracy on the evaluation set (milestone M3).

Each eval/audio/evalNN.wav goes through the same path as the live program
(mono -> 16 kHz -> VAD segmenter -> Whisper); the text is compared with eval/sentences.txt.
CER = character error rate after normalisation (lower case, no punctuation, "եւ" -> "և").

Run from the project folder, e.g.:
    .\\.venv\\Scripts\\python.exe scripts\\eval_asr.py --beam-size 1
    .\\.venv\\Scripts\\python.exe scripts\\eval_asr.py --beam-size 5 --prompt
    .\\.venv\\Scripts\\python.exe scripts\\eval_asr.py --translate   (also English for reference and ASR text)
"""

import argparse
import re
from dataclasses import replace
import sys
import time
import wave
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from hylive.asr import Transcriber  # noqa: E402  (imported first: registers the NVIDIA DLLs)
from hylive.audio_convert import Resampler, to_float32_frames, to_mono  # noqa: E402
from hylive.segmenter import Segmenter, load_vad_model  # noqa: E402

EVAL_DIR = PROJECT_DIR / "eval"


def set_paths(name: str) -> tuple[Path, Path, Path]:
    """'main' = original 10 sentences; other sets: eval/sentences_<name>.txt, eval/translations_<name>.txt, eval/audio/<name>/."""
    if name == "main":
        return EVAL_DIR / "sentences.txt", EVAL_DIR / "translations.txt", EVAL_DIR / "audio"
    return (EVAL_DIR / f"sentences_{name}.txt", EVAL_DIR / f"translations_{name}.txt", EVAL_DIR / "audio" / name)


def chrf_stats(hypothesis: str, reference: str, max_n: int = 6) -> list[tuple[int, int, int]]:
    """Character n-gram statistics for chrF (spaces removed, as in the standard chrF): (matches, hyp n-grams, ref n-grams)."""
    hyp, ref = hypothesis.replace(" ", ""), reference.replace(" ", "")
    stats = []
    for n in range(1, max_n + 1):
        h = [hyp[i:i + n] for i in range(len(hyp) - n + 1)]
        r = [ref[i:i + n] for i in range(len(ref) - n + 1)]
        counts: dict = {}
        for g in r:
            counts[g] = counts.get(g, 0) + 1
        matches = 0
        for g in h:
            if counts.get(g, 0) > 0:
                counts[g] -= 1
                matches += 1
        stats.append((matches, len(h), len(r)))
    return stats


def chrf(stats_list: list[list[tuple[int, int, int]]], beta: float = 2.0) -> float:
    """chrF score 0-100 over several sentences (statistics summed, then F-beta of average precision/recall)."""
    n_orders = len(stats_list[0])
    precisions, recalls = [], []
    for n in range(n_orders):
        m = sum(s[n][0] for s in stats_list)
        hyp_total = sum(s[n][1] for s in stats_list)
        ref_total = sum(s[n][2] for s in stats_list)
        precisions.append(m / hyp_total if hyp_total else 0.0)
        recalls.append(m / ref_total if ref_total else 0.0)
    p, r = sum(precisions) / n_orders, sum(recalls) / n_orders
    return 0.0 if p + r == 0 else 100 * (1 + beta ** 2) * p * r / (beta ** 2 * p + r)
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


def phrases_from_wav(path: Path, vad_model, pad_ms: int, min_silence_ms: int = 500) -> list:
    with wave.open(str(path), "rb") as wav:
        channels, rate = wav.getnchannels(), wav.getframerate()
        frames = to_float32_frames(wav.readframes(wav.getnframes()), channels)
    segmenter = Segmenter("mic", vad_model, speech_pad_ms=pad_ms, min_silence_ms=min_silence_ms)
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
    parser.add_argument("--pad-ms", type=int, default=100, help="VAD speech padding before/after each phrase")
    parser.add_argument("--min-silence-ms", type=int, default=500, help="pause that ends a phrase (live default 500)")
    parser.add_argument("--translate", action="store_true", help="also translate reference and ASR text with NLLB (M4)")
    parser.add_argument("--set", default="main", help="sentence set: main (default) or e.g. natural")
    parser.add_argument("--mt-beam", type=int, default=2, help="NLLB beam size (live default 2)")
    parser.add_argument("--normalize", action="store_true", help="test: peak-normalise each phrase to 0.9 before Whisper")
    parser.add_argument("--anti-repeat", action="store_true",
                        help="test: Whisper no_repeat_ngram_size=3, repetition_penalty=1.2")
    parser.add_argument("--whisper-translate", action="store_true",
                        help="also let Whisper translate directly from the audio (needs --translate for the references)")
    args = parser.parse_args()
    SENTENCES_FILE, TRANSLATIONS_FILE, AUDIO_DIR = set_paths(args.set)

    sentences = [line.split("\t", 1) for line in SENTENCES_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    english_refs = {}
    if args.translate:
        english_refs = dict(line.split("\t", 1) for line in TRANSLATIONS_FILE.read_text(encoding="utf-8").splitlines()
                            if line.strip())
    missing = [sid for sid, _ in sentences if not (AUDIO_DIR / f"eval{sid}.wav").exists()]
    if missing:
        raise FileNotFoundError(f"Missing recordings for {missing}. Run scripts/record_eval.py first.")

    vad_model = load_vad_model()
    decode_options = {"no_repeat_ngram_size": 3, "repetition_penalty": 1.2} if args.anti_repeat else None
    transcriber = Transcriber(args.model, beam_size=args.beam_size, initial_prompt=PROMPT if args.prompt else None,
                              decode_options=decode_options)
    transcriber.warm_up()
    translator = None
    if args.translate:
        from hylive.translate import Translator  # only loaded when needed
        translator = Translator(beam_size=args.mt_beam)
        translator.translate("Բարև")  # warm-up
    setting = (f"set {args.set}, model {args.model}, beam {args.beam_size}, prompt {'on' if args.prompt else 'off'}, "
               f"pad {args.pad_ms} ms, silence {args.min_silence_ms} ms, NLLB beam {args.mt_beam}, "
               f"normalize {'on' if args.normalize else 'off'}, "
               f"anti-repeat {'on' if args.anti_repeat else 'off'}")
    print(f"\nSetting: {setting}\n")

    total_edits = total_chars = 0
    total_word_edits = total_words = 0
    times, mt_times = [], []
    chrf_asr, chrf_upper = [], []  # English from the ASR text / from the correct Armenian, both vs. the English reference
    chrf_whisper, whisper_times = [], []  # English directly from the audio (Whisper task="translate")
    for sid, reference in sentences:
        segments = phrases_from_wav(AUDIO_DIR / f"eval{sid}.wav", vad_model, args.pad_ms, args.min_silence_ms)
        if args.normalize:  # same phrase, louder: peak at 0.9 (the mic peaks at only ~0.1-0.3)
            segments = [replace(s, audio=s.audio * (0.9 / max(float(abs(s.audio).max()), 1e-6))) for s in segments]
        t0 = time.perf_counter()
        hypothesis = " ".join(transcriber.transcribe(s.audio) for s in segments).strip()
        times.append(time.perf_counter() - t0)
        ref, hyp = normalise(reference), normalise(hypothesis)
        edits = edit_distance(ref, hyp)
        total_edits += edits
        total_chars += len(ref)
        total_word_edits += edit_distance(ref.split(), hyp.split())
        total_words += len(ref.split())
        print(f"[{sid}] CER {100 * edits / len(ref):5.1f} %  {times[-1]:.2f} s  {len(segments)} phrase(s)")
        print(f"     ref: {reference}")
        print(f"     hyp: {hypothesis or '(nothing recognised)'}")
        if translator is not None:
            t0 = time.perf_counter()
            en_hyp = translator.translate(hypothesis)
            mt_times.append(time.perf_counter() - t0)
            en_from_ref = translator.translate(reference)
            en_ref = english_refs[sid]
            chrf_asr.append(chrf_stats(en_hyp, en_ref))
            chrf_upper.append(chrf_stats(en_from_ref, en_ref))
            print(f"     EN reference:          {en_ref}")
            print(f"     EN from correct HY:    {en_from_ref}   (chrF {chrf([chrf_upper[-1]]):.0f})")
            print(f"     EN from ASR (shown):   {en_hyp}   (chrF {chrf([chrf_asr[-1]]):.0f}, {mt_times[-1]:.2f} s)")
            if args.whisper_translate:
                t0 = time.perf_counter()
                en_whisper = " ".join(transcriber.translate_speech(s.audio) for s in segments).strip()
                whisper_times.append(time.perf_counter() - t0)
                chrf_whisper.append(chrf_stats(en_whisper, en_ref))
                print(f"     EN Whisper translate:  {en_whisper}   (chrF {chrf([chrf_whisper[-1]]):.0f}, "
                      f"{whisper_times[-1]:.2f} s extra GPU)")

    print(f"\nRESULT ({setting}): CER {100 * total_edits / total_chars:.1f} %, "
          f"WER {100 * total_word_edits / total_words:.1f} % over {len(sentences)} sentences, "
          f"ASR time avg {sum(times) / len(times):.2f} s, max {max(times):.2f} s")
    if translator is not None:
        print(f"TRANSLATION: chrF from ASR text {chrf(chrf_asr):.1f} | chrF from correct Armenian {chrf(chrf_upper):.1f} "
              f"(upper bound for this translator) | MT time avg {sum(mt_times) / len(mt_times):.2f} s, max {max(mt_times):.2f} s")
    if chrf_whisper:
        print(f"WHISPER TRANSLATE: chrF {chrf(chrf_whisper):.1f} | extra GPU time avg "
              f"{sum(whisper_times) / len(whisper_times):.2f} s, max {max(whisper_times):.2f} s")


if __name__ == "__main__":
    main()
