# HANDOVER — next step: M2 (walking skeleton, mic only)

Written 2026-10-21 at the end of M0; updated 2026-10-23 after M1. Both were done in the same Cowork
session (session 01); `chats/INDEX.md` needs updating accordingly.
New session: read this file, then `CLAUDE.md` (project rules). Look up details in `PLAN.md`,
`DECISIONS.md` and `TESTS.md` only when needed. The official Mathrix brief is the source of truth.

## Goal (from the brief)
Python terminal program: capture microphone + system audio at the same time, transcribe spoken Armenian,
translate to English, print each segment with time, speaker (`Me` / `Speaker 1`, `Speaker 2`, … stable for
the session), Armenian original and English translation — at most 5 s after the end of a phrase.
All models local. Deadline: 2026-11-01 23:59 Yerevan time. Budget ~20 h; ~4.1 h used (see TIMELOG.md).

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
PyAudioWPatch 0.2.12.9.

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
- D-012 Headphones in calls (avoids echo into "Me"); headset cable mic ~3x quieter than laptop mic. (Provisional)
- Lesson: request `int8_float32` explicitly — CTranslate2 silently falls back to float32 if float16 is requested on this GPU.

## Open items for the user
- Ask Mathrix: public repo or collaborator access? Which calling app in the interview?
- Confirm two helpers for live speaker tests (needed around M5 and M7).
- Test the chat export (Settings → Privacy → Export data): is this session included, in what format?
- Export session 01 to `chats/` and record it in `chats/INDEX.md` (final export at the very end).

## Remaining milestones (PLAN.md)
M1 audio capture (2 h) → M2 walking skeleton, mic only (2.5 h) → M3 eval set + ASR comparison (3.5 h)
→ M4 translation comparison (1.5 h) → M5 both streams + speaker ID (3.5 h) → M6 latency/reliability (2 h)
→ M7 README + rehearsal (2 h) · buffer 1.5 h.

## M2 plan (to be explained and approved step by step)
Walking skeleton, mic only: capture → 16 kHz mono conversion → voice activity detection (Silero VAD) →
faster-whisper (small model first, `temperature=0.0`, `int8_float32`) → translation (NLLB-200 distilled
600M via CTranslate2 — to be verified) → terminal line with time, `Me`, HY, EN and measured latency.
Open design points: how to resample 48 kHz stereo → 16 kHz mono (options and dependencies to compare);
how the segmenter handles D-010; warm-up run at start-up (D-009); whether the headset mic level is enough.

## Next step
Explain the first M2 sub-step (16 kHz mono conversion: options and trade-offs) and wait for approval.
