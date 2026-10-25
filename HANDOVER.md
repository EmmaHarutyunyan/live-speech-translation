# HANDOVER — M4 complete; next: system audio in the live program

Written 2026-10-21 at the end of M0; updated 2026-10-23 after M1 and M2 sub-step 1; 2026-10-25 after M2 (complete). Both were done in the same Cowork
session (session 01); `chats/INDEX.md` needs updating accordingly.
New session: read this file, then `CLAUDE.md` (project rules). Look up details in `PLAN.md`,
`DECISIONS.md` and `TESTS.md` only when needed. The official Mathrix brief is the source of truth.

## Goal (from the brief)
Python terminal program: capture microphone + system audio at the same time, transcribe spoken Armenian,
translate to English, print each segment with time, speaker (`Me` / `Speaker 1`, `Speaker 2`, … stable for
the session), Armenian original and English translation — at most 5 s after the end of a phrase.
All models local. Deadline: 2026-11-01 23:59 Yerevan time. Budget ~20 h; ~7.5 h used (see TIMELOG.md). Target: finish by Oct 31.

## How we work (agreed)
- The user (junior Python dev, new to ML/audio) wants to understand every decision; explain simply.
- One step at a time; ask before installing anything, changing files or making major changes.
- Claude can only write files in `D:\Em\mathrix` (it cannot run Windows commands). The user runs every
  command in a normal (non-admin) PowerShell from `D:\Em\mathrix` and pastes the output.
- Always use the venv Python directly: `.\.venv\Scripts\python.exe ...` (no activation — avoids changing
  the PowerShell execution policy).
- Verify library facts in official docs/PyPI before relying on them; cite sources.
- Never paste secrets/tokens into chats (chats are submitted unedited).

## Environment (verified)
Windows 11 Home (build 26200) · i5-8300H 4C/8T · 7.9 GB RAM · GTX 1060 3 GB (Pascal, compute capability 6.1),
driver 582.28 (do not update — D-005) · Python 3.12.1 via `py -3.12` · Git 2.44 · venv at `D:\Em\mathrix\.venv`
· C: 26.6 GB free, D: 397 GB free · audio endpoints: `Микрофон (Realtek(R) Audio)`, `Динамики (Realtek(R) Audio)`
· Armenian text displays correctly in PowerShell · VS Code has no Copilot extension.
Installed in venv (pinned in `requirements.txt`): faster-whisper 1.2.1, ctranslate2 4.8.3,
nvidia-cublas-cu12 12.9.2.10, nvidia-cudnn-cu12 9.27.0.42, onnxruntime 1.31.0, numpy 2.5.4,
PyAudioWPatch 0.2.12.9, soxr 1.1.0,
silero-vad 6.2.3, torch 2.14.1+cpu, transformers. Models in `models/`: faster-whisper small,
medium, large-v3; NLLB converted to `models/nllb-200-distilled-600M-ct2-int8`.

## Done (M0 complete)
- Project docs: PLAN.md, DECISIONS.md, TESTS.md, CLAUDE.md, chats/INDEX.md, .gitignore, requirements.txt
- `scripts/gpu_smoke_test.py`: registers NVIDIA DLL folders from the venv, checks GPU + compute types,
  runs Whisper tiny on the GPU with `int8_float32` — PASSED.
- Git (local only, branch `main`): `dcdb5a8` (docs), `be69054` (smoke test + decisions), `f8dca82` (handover),
  then the M1 commit. No GitHub remote yet.

## Done (M1 complete)
- `hylive/audio_capture.py`: `DeviceInfo`, `AudioChunk(source, data, captured_at)`, `get_device`,
  `default_mic`, `default_loopback`, `DeviceCapture` (PortAudio callback → queue; native format 48 kHz,
  2 ch, int16; 10 ms blocks; counts PortAudio status flags).
- `scripts/list_devices.py` (WASAPI devices only) and `scripts/record_test.py` (records both devices at
  once to `recordings/`, prints audio received, first-block delay, largest gap, peak level, problem flags).
- Devices on this laptop: mic = 9, loopback = 10 (unchanged with headphones plugged in).
- `record_test.py --label <name>` puts the label in the file names.

## Done (M2 sub-step 1)
- `hylive/audio_convert.py`: `to_float32_frames`, `to_mono`, `Resampler` (soxr `ResampleStream`, 48 kHz → 16 kHz).
- `scripts/convert_test.py <wav>`: converts in 10 ms blocks, writes `<name>_16k.wav`, prints levels per
  channel, mono mix and channel correlation (correlation tells which mic was active: ~+0.75 laptop, ~+1.00 headset).
- Verified: durations preserved, clean sound, no cancellation (D-013).
- Finding: with the 3-ring headphones plugged in, the weak headset cable mic replaces the laptop mic
  (peak ~0.01 vs 0.137) → D-012 corrected: laptop mic + headphones without a mic.

## Done (M2 sub-step 2)
- `hylive/segmenter.py`: `Segment(source, audio, start_s, end_s, ended_at)`, `load_vad_model()`,
  `Segmenter.process(samples)` / `flush()` (VADIterator on 512-sample windows, 0.3 s pre-roll,
  max segment 10 s, min silence 500 ms, padding 100 ms).
- `scripts/vad_test.py <wav> [--threshold] [--min-silence-ms] [--max-segment-s]`: feeds a recording in 10 ms
  blocks, prints phrases + "detected after", saves `recordings/segments/<name>/segNN.wav`.
- Verified on laptop_mic and headset_mic: correct phrases, not clipped, end detected ~0.47 s after speech, ~3 % CPU.

## Done (M2 complete)
- `hylive/gpu.py` (`register_nvidia_dlls`), `hylive/asr.py` (`Transcriber`: large-v3 default, beam 1, temperature 0,
  language hy, no internal VAD, no previous-text conditioning, warm-up), `hylive/translate.py` (`Translator`: NLLB
  CTranslate2 int8 CPU, hye_Armn → eng_Latn).
- `hylive/__main__.py`: `python -m hylive [--list-devices] [--mic N] [--asr-model] [--min-silence-ms] [--max-segment-s]`;
  two threads (D-017); prints `[hh:mm:ss] Me`, HY, EN, latency (ASR, translation, queue); exit summary
  "phrases detected / printed" + PortAudio problem flags.
- Test scripts: `scripts/asr_test.py <wav> [--model] [--beam-size]`, `scripts/mt_test.py [--device]`.
- Live results: latency 3.0–3.6 s per sentence, 4.8 s for two merged sentences; ASR is the weakest link.

## Tests passed (TESTS.md)
ENV-1 GPU/driver · ENV-2 Python 3.12 · ENV-3 Armenian in terminal · ENV-4 GPU runs int8_float32 ·
R1-1 to R1-4 (device list, flags, simultaneous capture, user still hears audio). Mic level reference
values and one open issue (unexplained silent mic recordings) are in TESTS.md.

## Key decisions (details in DECISIONS.md)
- D-001 System audio via Windows WASAPI loopback (VB-Cable only as fallback).
- D-002 GPU models via CTranslate2; PyTorch CPU-only (current PyTorch GPU builds dropped Pascal). Verified.
- D-004 venv + model cache on D: inside the project (`models/`, git-ignored).
- D-005 Do not update the NVIDIA driver.
- D-006 GitHub repo private first; ask Mathrix public vs. collaborator access. (Pending)
- D-007 Test calls: Google Meet in Chrome, Zoom backup, wired headphones. (Provisional; ask Mathrix which app the interview uses)
- D-008 cuBLAS/cuDNN from pip in the venv, DLL folders registered at start-up. Verified.
- D-009 Whisper temperature fallback multiplied latency (4.01 s vs 0.67 s on a synthetic tone; with no
  retries it hallucinated "A-A-A-…"). Plan: `temperature=0.0` + VAD, decide after real-speech tests. (Pending)
- D-010 WASAPI loopback sends NO data while nothing plays → segmenter must not wait for silence samples. (Pending, M2)
- D-011 PyAudioWPatch for capture, WASAPI only. Verified.
- D-012 Laptop mic + headphones WITHOUT a mic (headset cable mic too weak/variable; corrected). (Provisional, hardware pending)
- D-013 soxr 1.1.0 streaming resampler, channels averaged to mono. Verified.
- D-014 silero-vad 6.2.3 VADIterator + own segmenter (0.5 / 500 ms / 10 s / 100 ms pad). Verified.
- D-015 Whisper large-v3 ASR baseline (CER 21 % vs medium 37 %, small 43 %; ~1.8 s/phrase). Provisional until M3.
- D-016 NLLB-200 600M, CTranslate2 int8 on CPU (~0.5 s). Non-commercial license. Verified.
- D-017 Two threads + Event-based shutdown (fixed lost phrases on Ctrl+C). Verified.
- D-018 M3: beam 1, no prompt, 100 ms padding (CER 8.6 %, max 1.89 s). Բ→Վ is a Whisper limitation.
- Lesson: request `int8_float32` explicitly — CTranslate2 silently falls back to float32 if float16 is requested on this GPU.

## Open items for the user
- Ask Mathrix: public repo or collaborator access? Which calling app in the interview?
- Confirm two helpers for live speaker tests (needed around M5 and M7).
- Headphone setup: mic-less headphones (2-ring), TRRS→TRS adapter, or check whether Realtek Audio Console
  exists. The user prefers NOT to change Windows settings for now.
- Test the chat export (Settings → Privacy → Export data): is this session included, in what format?
- Export session 01 to `chats/` and record it in `chats/INDEX.md` (final export at the very end).

## Remaining milestones (PLAN.md)
M1 audio capture (2 h) → M2 walking skeleton, mic only (2.5 h) → M3 eval set + ASR comparison (3.5 h)
→ M4 translation comparison (1.5 h) → M5 both streams + speaker ID (3.5 h) → M6 latency/reliability (2 h)
→ M7 README + rehearsal (2 h) · buffer 1.5 h.

## Plan to Oct 31 (≈13 h left)
| When | Work | h |
|---|---|---|
| next | M3: Armenian ASR accuracy (capped 1.5 h) | 1.5 |
| Oct 26–27 | system stream in the live program + D-010 (no loopback data in silence); max segment ≈5–6 s | 1.5 |
| Oct 28–29 | M5 speaker labels (needs 2 helpers + mic-less headphones / adapter) | 3.5 |
| Oct 30 | M6 latency/reliability + README | 3 |
| Oct 31 | rehearsal, chat export, submit | 2 |

## Done (M3 complete, 2026-10-25)
- Eval set recorded (`eval/audio/`, git-ignored); `scripts/record_eval.py`, `scripts/eval_asr.py [--beam-size] [--prompt] [--pad-ms]`.
- Chosen: large-v3, beam 1, no prompt, 100 ms padding — CER 8.6 %, ASR max 1.89 s (D-018). Live default unchanged.

## Done (M4 complete, 2026-10-25)
- `eval_asr.py --translate`: NLLB 10/10 understandable on correct Armenian; from ASR text 2 correct / 3 gist / 5 wrong.
  Translator kept; ASR is the limit (TESTS.md M4). Revisit ASR (e.g. beam 5 + shorter max segment) only if time remains.

## Next step
1. System audio in the live program: `--system N` (default: loopback of default speakers), a second capture +
   segmentation thread labelled per stream, shared processing thread; handle D-010 (no loopback data during silence).
   First tests with an Armenian YouTube video in headphones. Explain design first, wait for approval.
2. M5 speaker labels (needs 2 helpers + mic-less headphones / adapter).
