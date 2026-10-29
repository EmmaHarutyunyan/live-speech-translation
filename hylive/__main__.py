"""Live Armenian -> English transcription in the terminal: microphone + system audio.

Run from the project folder:
    .\\.venv\\Scripts\\python.exe -m hylive --list-devices
    .\\.venv\\Scripts\\python.exe -m hylive                      (Windows default mic + default speakers' loopback)
    .\\.venv\\Scripts\\python.exe -m hylive --mic 9 --system 10
    .\\.venv\\Scripts\\python.exe -m hylive --sources system   (testing aid: one side only)
Stop with Ctrl+C.

Threads (one capture + segmentation pipeline per source; shared ASR and translation threads):
  PortAudio callback (mic)    -> audio queue (mic)    -> segmentation thread (mic)    --\\
                                                                                        phrase queue -> ASR thread (GPU)
  PortAudio callback (system) -> audio queue (system) -> segmentation thread (system) --/      -> text queue -> translation thread (CPU) -> terminal
The GPU transcribes the next phrase while the CPU translates the previous one (D-021).
System-side phrases get a speaker label (voice fingerprint + online clustering) in the translation thread (D-023).
A silent output stream keeps the loopback device delivering data during silence (D-010, D-019).
"""

import os

# Local only (brief): load every model from models/ and never contact the Hugging Face servers. Without this, the
# NLLB tokenizer checks online for updated files and hangs without internet (found 2026-10-27, D-024).
# Models are downloaded once during setup with scripts/download_models.py. Must be set before any HF library import.
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import argparse  # noqa: E402
from pathlib import Path  # noqa: E402
import queue  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
import warnings  # noqa: E402

# Harmless warning printed by silero-vad's model loader on every start (D-014); hidden so the live output stays readable.
warnings.filterwarnings("ignore", message=r"`torch\.jit\.load` is deprecated", category=FutureWarning)

from hylive.asr import DEFAULT_MODEL, Transcriber  # imported first: registers the NVIDIA DLLs (D-008)
from hylive.translate import Translator

import numpy as np  # noqa: E402
import pyaudiowpatch as pyaudio  # noqa: E402

from hylive.audio_capture import (  # noqa: E402
    DeviceCapture, DeviceInfo, SilentOutput, default_loopback, default_mic, get_device, recordable_devices,
)
from hylive.audio_convert import Resampler, to_float32_frames, to_mono  # noqa: E402
from hylive.segmenter import Segmenter, load_vad_model  # noqa: E402
from hylive.speakers import SpeakerEncoder, SpeakerTracker  # noqa: E402

STOP = None  # put on a queue to tell the next thread to finish
SOURCES = ("mic", "system")


def format_time(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def segment_audio(source: str, audio_q: queue.Queue, phrase_q: queue.Queue, device: DeviceInfo,
                  segmenter: Segmenter, clocks: dict, stats: dict) -> None:
    """One per source: raw blocks -> 16 kHz mono -> phrases."""
    resampler = Resampler(device.sample_rate)
    while True:
        chunk = audio_q.get()
        if chunk is STOP:
            for seg in segmenter.flush():
                phrase_q.put(seg)
                stats[source]["detected"] += 1
                stats[source]["at_shutdown"] += 1
            phrase_q.put(STOP)
            return
        frames = to_float32_frames(chunk.data, device.channels)
        if source not in clocks:
            # Clock time of this stream's first sample: the first block arrived after it was recorded.
            clocks[source] = chunk.captured_at - len(frames) / device.sample_rate
        for seg in segmenter.process(resampler.process(to_mono(frames)), now=chunk.captured_at):
            phrase_q.put(seg)
            stats[source]["detected"] += 1


def transcribe_phrases(phrase_q: queue.Queue, text_q: queue.Queue, transcriber: Transcriber,
                       stats: dict, n_sources: int) -> None:
    """ASR thread (GPU), shared by all sources: phrase -> Armenian text."""
    stops = 0
    while True:
        seg = phrase_q.get()
        if seg is STOP:
            stops += 1
            if stops == n_sources:  # all segmentation threads are done
                text_q.put(STOP)
                return
            continue
        t0 = time.monotonic()
        asr = transcriber.transcribe_full(seg.audio)
        text_q.put((seg, asr, time.monotonic() - t0, phrase_q.qsize()))


def translate_and_print(text_q: queue.Queue, translator: Translator, clocks: dict, stats: dict,
                        encoder: SpeakerEncoder | None, tracker: SpeakerTracker | None) -> None:
    """Translation thread (CPU): speaker label + Armenian text -> English text -> terminal. The only printer."""
    while True:
        item = text_q.get()
        if item is STOP:
            return
        seg, asr, asr_time, asr_queue = item
        t0 = time.monotonic()
        speaker_info = ""
        if seg.source == "mic":
            label = "Me"
        elif asr.repetitive:
            label = "Speaker ?"  # noise/echo: not used for speaker identification, so it cannot spoil a voice average
        else:
            label, similarity = tracker.assign(encoder.embed(seg.audio), seg.end_s - seg.start_s)
            speaker_info = f", speaker {time.monotonic() - t0:.1f} s, similarity {similarity:.2f}"
        t1 = time.monotonic()
        if asr.repetitive:
            # Repetition loop (typical for noise or echo): show it, but do not spend seconds translating it (D-020).
            hy = (f"(repetitive output discarded - likely noise or echo; compression ratio {asr.compression_ratio:.1f}, "
                  f"different words {asr.unique_word_ratio:.0%})")
            en = ""
            stats[seg.source]["discarded"] += 1
        else:
            hy = asr.text + (" (cut at token limit)" if asr.hit_token_limit else "")
            en = translator.translate(asr.text)
        done_at = time.monotonic()
        stream_start = clocks[seg.source]
        # Session time shown in the output: the same clock for both sources.
        session_time = stream_start + seg.start_s - clocks["session"]
        # Latency as defined in the brief: end of the spoken phrase -> English line printed.
        # (Approximation: assumes no gaps in the stream — true for the mic and, with the keep-alive, for loopback.)
        latency = done_at - (stream_start + seg.end_s)
        print(f"[{format_time(session_time)}] {label}", flush=True)
        print(f"HY: {hy or '(nothing recognised)'}")
        print(f"EN: {en}")
        print(f"    latency {latency:.1f} s (ASR {asr_time:.1f} s, translation {done_at - t1:.1f} s{speaker_info}, "
              f"queue {asr_queue}+{text_q.qsize()})\n", flush=True)
        stats[seg.source]["printed"] += 1
        stats[seg.source]["latencies"].append(latency)


def start_thread(target, args, errors: list, done: threading.Event | None = None) -> threading.Thread:
    """Start a thread; if it crashes, store the error so the main thread stops loudly.

    `done` is set when the thread has finished (normally or with an error). The main thread waits on
    this event instead of Thread.join()/is_alive(): in testing, Ctrl+C during join() made the main
    thread exit while the processing thread was still working, which lost the last phrases (D-017).
    """
    def run():
        try:
            target(*args)
        except BaseException as e:  # noqa: BLE001 - re-raised by the main thread
            errors.append(e)
            raise
        finally:
            if done is not None:
                done.set()
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


def main() -> None:
    parser = argparse.ArgumentParser(description="Live Armenian -> English transcription (microphone + system audio).")
    parser.add_argument("--list-devices", action="store_true", help="print recordable devices and exit")
    parser.add_argument("--mic", type=int, help="microphone device index (default: Windows default mic)")
    parser.add_argument("--system", type=int, help="loopback device index (default: loopback of the default speakers)")
    parser.add_argument("--asr-model", default=DEFAULT_MODEL,
                        help="Whisper model: default = Armenian fine-tuned turbo in models/ (D-027); "
                             "fallback: large-v3 (needs scripts/download_models.py --with-large-v3)")
    parser.add_argument("--min-silence-ms", type=int, default=500)
    parser.add_argument("--max-segment-s", type=float, default=5.0,
                        help="cut phrases longer than this (default 5 s: longer phrases broke the 5 s latency, D-020)")
    parser.add_argument("--speaker-threshold", type=float, default=0.35,
                        help="voice similarity needed to count as a known speaker (default 0.35, D-023)")
    parser.add_argument("--sources", default="mic,system",
                        help="testing aid: 'mic', 'system' or 'mic,system' (default, required by the brief)")
    args = parser.parse_args()
    sources = tuple(s.strip() for s in args.sources.split(","))
    if not sources or any(s not in SOURCES for s in sources) or len(set(sources)) != len(sources):
        raise ValueError(f"--sources must be 'mic', 'system' or 'mic,system', got {args.sources!r}")

    if os.environ["HF_HUB_OFFLINE"] == "1":
        print("offline mode: all models are loaded from models/ (no internet needed)")
    p = pyaudio.PyAudio()
    try:
        if args.list_devices:
            for d in recordable_devices(p):
                kind = "LOOPBACK" if d.is_loopback else "INPUT"
                print(f"{d.index:>4}  {kind:<8}  {d.channels} ch  {d.sample_rate} Hz  {d.name}")
            return

        devices = {
            "mic": get_device(p, args.mic) if args.mic is not None else default_mic(p),
            "system": get_device(p, args.system) if args.system is not None else default_loopback(p),
        }
        if devices["mic"].is_loopback:
            raise ValueError(f"--mic {devices['mic'].index} is a loopback device; choose an INPUT device.")
        if not devices["system"].is_loopback:
            raise ValueError(f"--system {devices['system'].index} is not a loopback device; choose a LOOPBACK device.")
        for source, flag in (("mic", args.mic), ("system", args.system)):
            if source in sources:
                d = devices[source]
                print(f"{source + ':':<8}[{d.index}] {d.name}{'' if flag is not None else '  (Windows default)'}")
        if len(sources) < len(SOURCES):
            print(f"NOTE: testing mode, only {', '.join(sources)} is captured")
        keep_alive = SilentOutput(p, devices["system"]) if "system" in sources else None
        if keep_alive:
            print(f"keep-alive: inaudible silence on [{keep_alive.info['index']}] {keep_alive.info['name']}")

        print("loading VAD (one model per source: the model keeps internal state) ...", flush=True)
        segmenters = {s: Segmenter(s, load_vad_model(), min_silence_ms=args.min_silence_ms,
                                   max_segment_s=args.max_segment_s) for s in sources}
        print(f"loading Whisper '{Path(args.asr_model).name}' on GPU ...", flush=True)
        transcriber = Transcriber(args.asr_model)
        transcriber.warm_up()
        print("loading NLLB translation on CPU ...", flush=True)
        translator = Translator()
        translator.translate("Բարև")  # warm-up
        encoder = tracker = None
        if "system" in sources:
            print("loading speaker model on CPU ...", flush=True)
            encoder = SpeakerEncoder()
            encoder.embed(np.zeros(16_000, dtype=np.float32))  # warm-up
            tracker = SpeakerTracker(args.speaker_threshold)

        audio_qs = {s: queue.Queue() for s in sources}
        phrase_q: queue.Queue = queue.Queue()
        clocks: dict = {}
        stats = {s: {"detected": 0, "at_shutdown": 0, "printed": 0, "discarded": 0, "latencies": []}
                 for s in sources}  # to check that no phrase is lost, and to summarise latency
        errors: list = []
        captures = {s: DeviceCapture(p, devices[s], s, audio_qs[s]) for s in sources}
        for s in sources:
            start_thread(segment_audio, (s, audio_qs[s], phrase_q, devices[s], segmenters[s], clocks, stats), errors)
        text_q: queue.Queue = queue.Queue()
        processing_done = threading.Event()  # set when the translation thread (the last one) has finished
        start_thread(transcribe_phrases, (phrase_q, text_q, transcriber, stats, len(sources)), errors)
        start_thread(translate_and_print, (text_q, translator, clocks, stats, encoder, tracker), errors,
                     processing_done)

        if keep_alive:
            keep_alive.start()
        clocks["session"] = time.monotonic()
        for c in captures.values():
            c.start()
        print("\nReady. Speak Armenian (and/or play the call). Press Ctrl+C to stop.\n", flush=True)

        try:
            while not processing_done.is_set() and not errors:
                processing_done.wait(0.2)  # short waits so Ctrl+C is noticed on Windows
        except KeyboardInterrupt:
            print("\nStopping: finishing the last phrases ...", flush=True)
        for c in captures.values():
            c.stop()
        if keep_alive:
            keep_alive.stop()
        if not errors:
            for q in audio_qs.values():
                q.put(STOP)  # each segmentation thread flushes, then tells the processing thread it is done
            while not processing_done.is_set() and not errors:
                processing_done.wait(0.2)
        if errors:
            raise errors[0]
        for s in sources:
            st = stats[s]
            print(f"{s:<6} phrases detected: {st['detected']} (of which {st['at_shutdown']} at shutdown), "
                  f"printed: {st['printed']} (of which {st['discarded']} discarded as repetitive), "
                  f"PortAudio problem flags: {captures[s].status_flag_count}")
            lat = sorted(st["latencies"])
            if lat:
                under = sum(1 for x in lat if x <= 5.0)
                print(f"       latency: median {lat[len(lat) // 2]:.1f} s, max {lat[-1]:.1f} s, "
                      f"<= 5 s: {under}/{len(lat)} ({100 * under / len(lat):.0f} %)")
        if tracker:
            print(f"speakers identified on the system side: {tracker.count} (threshold {args.speaker_threshold})")
    finally:
        p.terminate()


if __name__ == "__main__":
    main()
