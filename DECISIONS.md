# DECISIONS

Each entry: what was decided, why, what else was considered, status. Newest at the bottom.

## D-001 — Capture system audio with Windows WASAPI loopback (2026-10-21)
- **Decision:** Record the call side directly from the output device ("Динамики (Realtek)") using WASAPI loopback.
- **Why:** Built into Windows; no extra driver; the user still hears the call normally. It is the Windows equivalent of the macOS BlackHole setup mentioned in the brief.
- **Alternatives:** VB-Audio Virtual Cable (extra driver, more setup); "Stereo Mix" (not present on this laptop's device list).
- **Status:** Accepted. Fallback to VB-Cable only if loopback fails in testing.

## D-002 — Run GPU models through CTranslate2; keep PyTorch on CPU only (2026-10-21)
- **Decision:** Use CTranslate2-based engines (faster-whisper for ASR, CTranslate2 for translation) on the GPU. Any PyTorch-based parts (e.g. speaker embeddings) run on the CPU.
- **Why:** The GTX 1060 is a Pascal GPU. The PyTorch team states that CUDA 12.8+ builds already dropped Pascal, CUDA 13 does not support it, and PyTorch 2.14 (cu126) is the last version with prebuilt Pascal support. CTranslate2 ships its own CUDA libraries, so it avoids this dependency.
  Source: https://dev-discuss.pytorch.org/t/notice-cuda-12-6-wheels-will-no-longer-be-published-from-pytorch-2-15-drops-maxwell-pascal-volta/3432
- **Alternatives:** PyTorch 2.14 cu126 on GPU (works today, but pins an old version; may be revisited if we need it to compare a model).
- **Status:** Verified 2026-10-21 — GPU smoke test passed: CTranslate2 sees the GPU and runs Whisper with `int8_float32` (TESTS.md ENV-4). Speed of larger models still to be measured (M3).

## D-003 — Python 3.12 via the `py` launcher (2026-10-21)
- **Decision:** Use the installed Python 3.12 (`py -3.12`); do not install another Python.
- **Why:** Already installed; supported by the libraries we plan to use. `python` is not on PATH, so commands use `py -3.12` or the venv's Python.
- **Status:** Accepted.

## D-004 — Keep the virtual environment and model cache on D: (2026-10-21)
- **Decision:** venv at `D:\Em\mathrix\.venv`; model downloads cached inside the project folder, both excluded by `.gitignore`.
- **Why:** C: has only 26.6 GB free; models and libraries can take 10–15 GB.
- **Status:** Accepted.

## D-005 — Do not update the NVIDIA driver before the interview (2026-10-21)
- **Decision:** Keep driver 582.28.
- **Why:** NVIDIA has stated that the 580 branch is the last to support Maxwell/Pascal/Volta. A working setup must not be put at risk.
- **Status:** Accepted.

## D-006 — GitHub repository visibility (2026-10-21)
- **Decision:** Create the repository as private first; ask Mathrix whether they prefer a public link or collaborator access; switch before submission.
- **Why:** The brief only asks for "a link to a Git repository". The `chats/` folder will be included unedited, so nothing private may ever be pasted into a chat.
- **Status:** Pending answer from Mathrix.

## D-007 — Calling application for tests (2026-10-21)
- **Decision:** Google Meet in Chrome as primary test app (no install for helpers); Zoom as backup. Wired headphones; app output on the default device.
- **Why:** The program captures any system audio, so the app does not change the code. Free tier limits still to be verified.
- **Status:** Provisional — rehearse with the app Mathrix will use in the interview, once known.

## D-008 — NVIDIA cuBLAS/cuDNN from pip packages inside the venv (2026-10-21)
- **Decision:** Install `nvidia-cublas-cu12` and `nvidia-cudnn-cu12` with pip into `.venv`; register their `bin` DLL folders (`os.add_dll_directory` + `PATH`) at program start, before importing ctranslate2.
- **Why:** Keeps everything inside the project environment, reproducible from `requirements.txt`, no system-wide install. The faster-whisper README calls the pip method "Linux only", but Windows wheels exist and the smoke test proved it works.
- **Alternatives:** NVIDIA CUDA Toolkit + cuDNN installers (several GB on the nearly full C: drive, system-wide); Purfview's whisper-standalone-win DLL archive (third-party copies, manual PATH change).
- **Working versions:** ctranslate2 4.8.3, faster-whisper 1.2.1, nvidia-cublas-cu12 12.9.2.10, nvidia-cudnn-cu12 9.27.0.42 (all pinned in `requirements.txt`).
- **Status:** Verified 2026-10-21.

## D-009 — Whisper temperature fallback multiplies latency (finding; decision pending) (2026-10-21)
- **Finding:** On a 5 s synthetic tone, Whisper tiny took 4.01 s with the default temperature fallback (it re-decodes up to several times when output looks bad, then discarded the text) and 0.67 s with `temperature=0.0` (one decode, but the hallucinated text "A-A-A-…" was kept).
- **Consequence:** Retries can break the 5-second budget; without retries, non-speech produces garbage. Non-speech must be removed before ASR (VAD), and the first transcription after loading is slower (warm-up run at start-up).
- **Plan:** Start with `temperature=0.0` + VAD in M2; measure on real Armenian speech in M2/M3 and decide then whether a limited fallback or a visible repetition check is needed.
- **Status:** Pending measurement.

## D-010 — WASAPI loopback sends no data during silence (finding; solution pending) (2026-10-23)
- **Finding:** With nothing playing, the loopback device delivered 0 blocks in 15 s. When a video started
  ~1.5 s after recording began, the first block arrived after 1.47 s; after that, no gaps.
- **Consequence:** The segmenter must not wait for "silence after speech" samples that never arrive on the
  system stream, or the last phrase before a quiet moment may never be printed.
- **Options for M2:** (a) the program plays a silent output stream on the speakers to keep loopback
  delivering data (common workaround — to be verified, not assumed); (b) close a phrase when no new audio
  arrives for a set time, using the clock. Also to test: whether call apps keep sending audio when nobody speaks.
- **Status:** Pending (M2).

## D-011 — PyAudioWPatch for audio capture (2026-10-23)
- **Decision:** Use PyAudioWPatch 0.2.12.9 (PortAudio V19.7.0) in callback mode; WASAPI devices only, for the mic too.
- **Why:** Actively maintained (release Oct 6, 2026), Python 3.12 Windows wheel, loopback devices appear as
  extra input devices so mic and system audio use the same code. Verified: device list, simultaneous capture
  of both devices with no lost blocks.
- **Alternatives:** `soundcard` (its PyPI page lists Windows issues: garbage single-channel recording,
  ignored blocksize, buffer underruns); `sounddevice` (not evaluated).
- **Status:** Verified 2026-10-23.

## D-012 — Laptop mic + headphones without a mic during calls (provisional; corrected 2026-10-23)
- **Decision:** Wear headphones (so call audio does not leak into the mic and get labelled "Me"; echo
  handling is out of scope in the brief), but keep the laptop's built-in mic as the "Me" input.
- **Why (measured, see TESTS.md M1 table):** With the current 3-ring headphones plugged in, Windows records
  their cable mic instead of the laptop mic, under the same device name. That mic is weak and variable:
  peak 0.008 hanging, 0.011 held 10–15 cm from the mouth, 0.020–0.055 in earlier recordings — vs 0.137 for
  the laptop mic. Holding it closer improved it only ~1.4x, so distance is not the main cause.
- **Correction:** An earlier version of this entry said the headset mic was "~3x quieter than the laptop mic
  (0.055)". That 0.055 recording was itself the headset mic (correlation +1.00); corrected with labelled recordings.
- **Options to get "laptop mic + headphones":** (1) headphones without a mic (2-ring plug); (2) a TRRS→TRS
  audio-only adapter; (3) a Realtek setting that treats the jack device as "headphones" (system setting —
  only with the user's explicit OK; the user prefers not to change Windows settings for now).
  Verification: correlation ~+0.75 while headphones are plugged in.
- **Rejected:** headset cable mic (too weak/variable); Windows "Microphone Boost" (amplifies noise too; system setting).
- **Status:** Provisional — waiting for the hardware choice.

## D-013 — soxr streaming resampler for 48 kHz → 16 kHz (2026-10-23)
- **Decision:** Average channels to mono, then resample with `soxr.ResampleStream` (soxr 1.1.0, quality "HQ")
  block by block (`hylive/audio_convert.py`).
- **Why:** Streaming keeps filter state between 10 ms blocks (no clicks at block edges); very simple API;
  small dependency (requires only numpy). Verified: durations preserved exactly, clean sound, no channel
  cancellation (TESTS.md, M2 sub-step 1).
- **Alternatives:** PyAV `AudioResampler` (already installed, but more complex frame-based code); plain numpy
  average-of-3 decimation (no install, but weak filter → aliasing); `scipy.signal.resample_poly` (large
  install, no state between blocks → wrong for streaming).
- **Source:** https://python-soxr.readthedocs.io/en/latest/soxr.html (`ResampleStream`, `resample_chunk(x, last=False)`)
- **Status:** Verified 2026-10-23.

## D-014 — Official silero-vad + own segmenter for phrase detection (2026-10-25)
- **Decision:** Use `silero-vad` 6.2.3 (`VADIterator`, default model) with CPU torch 2.14.1+cpu, wrapped in our
  own `hylive/segmenter.py` (512-sample windows, pre-roll buffer, max segment length, `Segment` output).
  Settings: threshold 0.5, min silence 500 ms, speech padding 100 ms, max segment 10 s (to be tuned with real data).
- **Why:** Official, maintained, documented streaming API; CPU torch is needed anyway for speaker embeddings
  in M5 (D-002). Read from the installed source: `VADIterator` returns {'start': n} / {'end': n}, uses
  hysteresis (start ≥ threshold, end < threshold − 0.15), default min silence only 100 ms (too short for
  phrases), and has no maximum length — so the segmenter adds it.
- **Verified:** phrases correct and not clipped (user listened), end detected ~0.47 s after speech ends,
  ~3 % CPU of real time (TESTS.md, M2 sub-step 2). torch is the CPU build (`torch.version.cuda` = None).
- **Alternatives:** the Silero ONNX model bundled inside faster-whisper (no install, but an internal,
  whole-file wrapper with a custom export — not a documented streaming API); `webrtcvad` (older, generally
  less accurate on noisy audio).
- **Known warning:** `torch.jit.load is deprecated` (FutureWarning from silero_vad's default model loader).
  Harmless now; possible cleanup: `load_silero_vad(onnx=True)` (onnxruntime already installed) — not changed, untested.
- **Status:** Verified 2026-10-25.

## D-015 — Whisper large-v3 as the ASR baseline (2026-10-25)
- **Decision rule, set before testing large-v3:** adopt it if it fits in VRAM, takes ≤ 3 s per phrase and has clearly
  lower CER than medium (37 %); otherwise keep medium.
- **Result (one sentence, TESTS.md):** small 43 % CER / ~0.5 s, medium 37 % / ~1.1 s, large-v3 21 % / ~1.8 s,
  fits in 3 GB VRAM → large-v3 adopted. Load time ~20–30 s after the first download; warm-up ~12 s.
- **Limits:** one sentence is not an evaluation; Armenian accuracy is still poor (Բ→Վ/Հ errors).
  M3 measures cheap improvements (beam size, Armenian initial prompt) and at most one fine-tuned model, capped at 1.5 h.
- **Alternatives:** small/medium (faster, much worse); large-v3-turbo (not tested yet).
- **Status:** Confirmed by M3 (2026-10-25): beam 1, no prompt, 100 ms padding — CER 8.6 % on the 10-sentence
  evaluation set, ASR max 1.89 s (TESTS.md M3, D-018).

## D-016 — NLLB-200 distilled 600M via CTranslate2 (CPU, int8) for translation (2026-10-25)
- **Decision:** Convert `facebook/nllb-200-distilled-600M` once with
  `ct2-transformers-converter --quantization int8` into `models/nllb-200-distilled-600M-ct2-int8`; run on the CPU;
  source `hye_Armn`, target `eng_Latn` (`hylive/translate.py`, following the official CTranslate2 NLLB example).
- **Why:** Explicit Armenian support; ~0.3–0.9 s per phrase on the CPU keeps the GPU free for Whisper; good English
  from correct Armenian (TESTS.md).
- **Setup detail:** set `$env:HF_HOME = "D:\Em\mathrix\models\hf_home"` before converting, otherwise the 2.5 GB
  original model is downloaded to C: (D-004). Needs `transformers` (installed 2026-10-25).
- **License:** NLLB-200 is released for non-commercial use (CC-BY-NC 4.0) — acceptable for this challenge; stated in README.
- **Alternatives:** Helsinki-NLP opus-mt-hy-en (smaller/faster, not tested); NLLB on the GPU (not needed so far).
- **Status:** Verified 2026-10-25.

## D-017 — Two worker threads and an Event-based shutdown (2026-10-25)
- **Decision:** PortAudio callback → audio queue → segmentation thread (convert + VAD) → phrase queue → processing
  thread (ASR + translation + print). On Ctrl+C: stop capture, send STOP through both queues (the segmenter flushes
  an unfinished phrase), and the main thread waits on a `threading.Event` set by the processing thread.
- **Why:** Segmentation must keep up with live audio while ASR takes ~2 s per phrase. Waiting with
  `Thread.join()`/`is_alive()` failed in testing: after Ctrl+C the main thread exited while a phrase was still being
  transcribed (counters: detected 2, printed 1). Exact cause not confirmed (possibly Ctrl+C interrupting `join()`);
  the Event avoids relying on it. Crashes in a thread are stored and re-raised by the main thread (fail loudly).
- **Verified:** TESTS.md M2 live tests 1 and 2.
- **Status:** Verified 2026-10-25.

## D-018 — M3: keep beam 1, no initial prompt, 100 ms VAD padding (2026-10-25)
- **Decision rule (set before measuring):** lowest CER with max ASR time ≤ ~2.5 s; improvements < ~2 CER points do
  not justify a slower or more complex setting.
- **Results (TESTS.md M3):** beam 1 8.6 % / max 1.89 s; beam 5 6.4 % / max 3.73 s (too slow); beam 5 + prompt
  12.8 % (hallucination); pad 300 ms 7.7 % (+0.9 points only, Բ errors unchanged).
- **Hypothesis tested and rejected:** "VAD cuts off the first sound, causing Բ→Վ". With 300 ms padding the same
  words were still wrong → Whisper limitation, documented as a known limitation.
- **Kept in code:** `eval_asr.py --pad-ms` and a pre-roll of at least padding + 0.2 s in the segmenter (no effect at 100 ms).
- **Not done (time cap):** community Armenian fine-tuned Whisper models — a possible improvement listed for the README.
- **Status:** Decided 2026-10-25. M3 closed (~0.5 h of the 1.5 h cap).
