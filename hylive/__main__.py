"""Live Armenian -> English transcription in the terminal (milestone M2: microphone only).

Run from the project folder:
    .\\.venv\\Scripts\\python.exe -m hylive --list-devices
    .\\.venv\\Scripts\\python.exe -m hylive              (Windows default microphone)
    .\\.venv\\Scripts\\python.exe -m hylive --mic 9
Stop with Ctrl+C.

Threads:
  PortAudio callback  -> audio queue  (raw 10 ms blocks, hylive.audio_capture)
  segmentation thread -> phrase queue (16 kHz mono + VAD, hylive.audio_convert / hylive.segmenter)
  processing thread   -> terminal     (ASR + translation, hylive.asr / hylive.translate)
"""

import argparse
import queue
import threading
import time

from hylive.asr import Transcriber  # imported first: registers the NVIDIA DLLs (D-008)
from hylive.translate import Translator

import pyaudiowpatch as pyaudio  # noqa: E402

from hylive.audio_capture import DeviceCapture, DeviceInfo, default_mic, get_device, recordable_devices  # noqa: E402
from hylive.audio_convert import Resampler, to_float32_frames, to_mono  # noqa: E402
from hylive.segmenter import Segmenter, load_vad_model  # noqa: E402

STOP = None  # put on a queue to tell the next thread to finish


def format_time(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def segment_audio(audio_q: queue.Queue, phrase_q: queue.Queue, device: DeviceInfo,
                  segmenter: Segmenter, clock: dict, stats: dict) -> None:
    """Thread 1: raw blocks -> 16 kHz mono -> phrases."""
    resampler = Resampler(device.sample_rate)
    while True:
        chunk = audio_q.get()
        if chunk is STOP:
            for seg in segmenter.flush():
                phrase_q.put(seg)
                stats["detected"] += 1
                stats["at_shutdown"] += 1
            phrase_q.put(STOP)
            return
        frames = to_float32_frames(chunk.data, device.channels)
        if "stream_start" not in clock:
            # Clock time of the first sample: the first block arrived after it was recorded.
            clock["stream_start"] = chunk.captured_at - len(frames) / device.sample_rate
        for seg in segmenter.process(resampler.process(to_mono(frames)), now=chunk.captured_at):
            phrase_q.put(seg)
            stats["detected"] += 1


def process_phrases(phrase_q: queue.Queue, transcriber: Transcriber, translator: Translator,
                    clock: dict, stats: dict, label: str) -> None:
    """Thread 2: phrase -> Armenian text -> English text -> terminal."""
    while True:
        seg = phrase_q.get()
        if seg is STOP:
            return
        t0 = time.monotonic()
        hy = transcriber.transcribe(seg.audio)
        t1 = time.monotonic()
        en = translator.translate(hy)
        t2 = time.monotonic()
        # Latency as defined in the brief: end of the spoken phrase -> English line printed.
        # (Approximation: assumes the mic stream has no gaps, verified in M1; ignores driver buffering.)
        latency = t2 - (clock["stream_start"] + seg.end_s)
        print(f"[{format_time(seg.start_s)}] {label}", flush=True)
        print(f"HY: {hy or '(nothing recognised)'}")
        print(f"EN: {en}")
        print(f"    latency {latency:.1f} s (ASR {t1 - t0:.1f} s, translation {t2 - t1:.1f} s, "
              f"queue {phrase_q.qsize()})\n", flush=True)
        stats["printed"] += 1


def start_thread(target, args, errors: list, done: threading.Event | None = None) -> threading.Thread:
    """Start a thread; if it crashes, store the error so the main thread stops loudly.

    `done` is set when the thread has finished (normally or with an error). The main thread waits on
    this event instead of Thread.join()/is_alive(): in testing, Ctrl+C during join() made the main
    thread exit while the processing thread was still working, which lost the last phrases.
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
    parser = argparse.ArgumentParser(description="Live Armenian -> English transcription (microphone).")
    parser.add_argument("--list-devices", action="store_true", help="print recordable devices and exit")
    parser.add_argument("--mic", type=int, help="microphone device index (default: Windows default mic)")
    parser.add_argument("--asr-model", default="large-v3", help="faster-whisper model (default large-v3, D-015)")
    parser.add_argument("--min-silence-ms", type=int, default=500)
    parser.add_argument("--max-segment-s", type=float, default=10.0)
    args = parser.parse_args()

    p = pyaudio.PyAudio()
    try:
        if args.list_devices:
            for d in recordable_devices(p):
                kind = "LOOPBACK" if d.is_loopback else "INPUT"
                print(f"{d.index:>4}  {kind:<8}  {d.channels} ch  {d.sample_rate} Hz  {d.name}")
            return

        mic = get_device(p, args.mic) if args.mic is not None else default_mic(p)
        if mic.is_loopback:
            raise ValueError(f"--mic {mic.index} is a loopback device; choose an INPUT device.")
        print(f"mic: [{mic.index}] {mic.name}{'' if args.mic is not None else '  (Windows default)'}")

        print("loading VAD ...", flush=True)
        segmenter = Segmenter("mic", load_vad_model(), min_silence_ms=args.min_silence_ms,
                              max_segment_s=args.max_segment_s)
        print(f"loading Whisper '{args.asr_model}' on GPU ...", flush=True)
        transcriber = Transcriber(args.asr_model)
        transcriber.warm_up()
        print("loading NLLB translation on CPU ...", flush=True)
        translator = Translator()
        translator.translate("Բարև")  # warm-up

        audio_q: queue.Queue = queue.Queue()
        phrase_q: queue.Queue = queue.Queue()
        clock: dict = {}
        stats = {"detected": 0, "at_shutdown": 0, "printed": 0}  # to check that no phrase is lost
        errors: list = []
        capture = DeviceCapture(p, mic, "mic", audio_q)
        start_thread(segment_audio, (audio_q, phrase_q, mic, segmenter, clock, stats), errors)
        processing_done = threading.Event()
        start_thread(process_phrases, (phrase_q, transcriber, translator, clock, stats, "Me"), errors,
                     processing_done)
        capture.start()
        print("\nReady. Speak Armenian. Press Ctrl+C to stop.\n", flush=True)

        try:
            while not processing_done.is_set() and not errors:
                processing_done.wait(0.2)  # short waits so Ctrl+C is noticed on Windows
        except KeyboardInterrupt:
            print("\nStopping: finishing the last phrase ...", flush=True)
        capture.stop()
        if not errors:
            audio_q.put(STOP)  # segmentation thread flushes, then tells the processing thread to finish
            while not processing_done.is_set() and not errors:
                processing_done.wait(0.2)
        if errors:
            raise errors[0]
        print(f"phrases detected: {stats['detected']} (of which {stats['at_shutdown']} at shutdown), "
              f"printed: {stats['printed']}")
        print(f"problem flags from PortAudio: {capture.status_flag_count} blocks")
    finally:
        p.terminate()


if __name__ == "__main__":
    main()
