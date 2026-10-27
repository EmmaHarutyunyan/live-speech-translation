# HANDOVER — M5 + fixes + offline done; next: README

Updated 2026-10-27 19:25. Everything so far happened in ONE Cowork session (session 01).
Read this file, then `CLAUDE.md`. Details: `TESTS.md` (all measurements), `DECISIONS.md` (D-001 … D-022),
`TIMELOG.md`. The official Mathrix brief is the source of truth. Target: finish by Oct 30.

## Goal (from the brief)
Python terminal program: capture microphone + system audio at the same time, transcribe spoken Armenian,
translate to English, print each segment with time, speaker (`Me` / `Speaker 1`, `Speaker 2`, … stable for
the session), Armenian original and English translation — at most 5 s after the end of a phrase.
All models local. Deadline: 2026-11-01 23:59 Yerevan time (target: finish Oct 31).
Budget ~20 h; **~11.5 h used**, ≈ 8.5 h left.

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

## Where we are
- M0 setup ✅ · M1 audio capture ✅ · M2 live skeleton ✅ · M3 ASR settings ✅ · M4 translation ✅ ·
  system audio + much of M6 latency work ✅ · **M5 speaker identification ✅** · small fixes ✅ · offline check ✅ · README ☐ · fresh-setup check ☐ · real call ☐ · rehearsal ☐
- Live program: `.\.venv\Scripts\python.exe -m hylive [--list-devices] [--mic N] [--system N] [--sources mic|system|mic,system]
  [--asr-model large-v3] [--min-silence-ms 500] [--max-segment-s 5] [--speaker-threshold 0.35]`. Mic = 9, loopback = 10 on this laptop.
- Pipeline (D-017/D-021): capture (PortAudio callback, 10 ms blocks) → per source: 16 kHz mono (soxr) + Silero VAD
  segmenter (own model per source) → shared ASR thread (Whisper large-v3, GPU, int8_float32, beam 1, temp 0,
  128-token cap, repetition guard) → translation thread (speaker label for system phrases: SpeechBrain ECAPA +
  online clustering, D-023; then NLLB-200 600M, CPU int8) → terminal.
  Keep-alive silence on the speakers while capturing loopback (D-019).
- Output per block: `[hh:mm:ss] Me|Speaker ?`, HY, EN, `latency X s (ASR, translation, queue A+B)`.
  Exit summary per source: detected / printed / discarded, PortAudio flags, latency median / max / % ≤ 5 s.
- Key numbers: eval CER 8.6 % (10 sentences, laptop mic); live loopback = offline accuracy (Test A 5.7 % = 5.7 %);
  one side talking: latency median 2.8 s, 100 % ≤ 5 s; overlap + echo: 64–70 % ≤ 5 s, max 8.7 s.

## Code map
- `hylive/audio_capture.py` — DeviceInfo, AudioChunk, get_device, default_mic, default_loopback, recordable_devices,
  DeviceCapture, output_device_for_loopback, SilentOutput
- `hylive/audio_convert.py` — to_float32_frames, to_mono, Resampler (soxr)
- `hylive/segmenter.py` — Segment, load_vad_model, Segmenter (process, flush)
- `hylive/asr.py` — Transcriber (transcribe, transcribe_full → AsrResult), MAX_NEW_TOKENS, MAX_COMPRESSION_RATIO
- `hylive/translate.py` — Translator (NLLB via CTranslate2)
- `hylive/speakers.py` — SpeakerEncoder (ECAPA), SpeakerTracker (threshold, short-phrase rule, count)
- `hylive/gpu.py` — register_nvidia_dlls (must run before importing ctranslate2/faster_whisper)
- `hylive/__main__.py` — CLI, threads, output, summary
- `scripts/` — list_devices, record_test (--label, --keep-alive), convert_test, vad_test, asr_test, mt_test,
  record_eval, eval_asr (--model, --beam-size, --prompt, --pad-ms, --translate), play_eval (--ids, --gap),
  speaker_test (--thresholds), gpu_smoke_test
- `recordings/20261027-184504_twowomen_system.wav` + segments (git-ignored): M5 test clip with ground truth
- `eval/sentences.txt` (committed), `eval/audio/` (git-ignored)

## Done (M5, 2026-10-27)
Speaker identification works offline (3 recordings, 0 wrong labels) and live (L1b, L2); threshold 0.35; see D-023.
Full application test L2: Me + Speaker 1 + Speaker 2 correct; latency Me 100 %, system 88 % ≤ 5 s.

## Done since M5 (2026-10-27)
- Echo check at interview volume: 0 echo phrases → keep current headphones, moderate volume (D-012).
- Small fixes (D-025): "�" stripped, extra loop rule, torch.jit warning hidden. Eval CER 8.6 % unchanged.
- Offline: `HF_HUB_OFFLINE=1` in the live program + `scripts/download_models.py`; Wi-Fi-off run passed (D-024).
- Mixed Armenian/Russian/English checked and documented as a limitation (TESTS.md).

## NEXT (in this order, keep it simple)
1. README (setup incl. audio devices + headphones + keep-alive, download/convert models, run; models + alternatives
   + reasons with numbers; architecture; limitations; improvements).
2. Fresh-setup check following the README (new venv in a temp folder, `requirements.txt`, `download_models.py`,
   NLLB conversion) — at least the steps that are cheap to repeat.
3. Chat export test; GitHub repo (private first); email Mathrix (visibility, calling app); 2 helpers for a real call.
4. Real call (Meet/Zoom) with 2 helpers; rehearsal; final chat export; submit.

## OPEN ISSUES before submission (priority order)
1. ~~Echo / headset mic~~ — echo check passed at interview volume (D-012); re-check in the real call. Was: get mic-less headphones (2-ring plug) or a TRRS→TRS adapter; then re-run
   the real-world test (both streams) and re-measure latency and "Me" labelling.
2. ~~M5 speaker identification~~ ✅ done 2026-10-27 (D-023). Remaining: 10+ min and real-call test.
3. **Latency under overlapping speech (C-1):** 64–70 % ≤ 5 s with echo. Re-test echo-free; if still needed, consider
   batching queued phrases on the GPU (faster-whisper batched mode) — verify first.
4. **ASR accuracy limits (README):** word-initial Բ → Վ/dropped; single-letter errors flip the English meaning.
   Optional if time: beam 5 with the shorter 5 s phrases (measure latency); community Armenian fine-tune.
5. ~~Cosmetic~~ mostly done (D-025); `queue` shows stop signals at shutdown (cosmetic). Was: "�" at the end of phrases cut mid-word (strip U+FFFD or similar); "(cut at token limit)" flag
   never appeared although one output looked truncated ("այդ հ") — check the approximate token count logic;
   torch.jit / Hugging Face symlink + token warnings at start-up (document or silence via env vars).
6. ~~Local-only check (C-2)~~ ✅ (D-024). Was: run with Wi-Fi off after all downloads; Hugging Face may try the network for the
   tokenizer/models → test, possibly set `HF_HUB_OFFLINE=1`.
7. **README** (setup incl. audio devices, keep-alive, models + alternatives + reasons with numbers, architecture,
   limitations, improvements) — not started. PLAN.md milestone table is outdated (update or point to HANDOVER).
8. **Fresh-setup check:** follow the README from scratch (new venv, `requirements.txt`, NLLB conversion with HF_HOME on D:).
9. **Chats (deliverable):** test the export (Settings → Privacy → Export data) NOW; final export after the last
   message; one .md per session in `chats/`, unedited; update `chats/INDEX.md` (so far 1 session).
10. **Repo + Mathrix:** create the GitHub repo (private first, D-006); ask Mathrix: public vs. collaborator access,
    and which calling app the interview uses (D-007).
11. **Helpers:** 2 people for a test call (M5 test and final rehearsal); record one 2-voice call for offline tuning.
12. Optional: Test B with eval clips + reading (clips as call side, known text for both sides).

## Remaining time plan (≈ 9 h, target Oct 30)
| When | Work | h |
|---|---|---|
| Oct 27 (rest) | small fixes, offline check | 0.5 |
| Oct 28 | README; hardware fix + echo-free test | 2.5 |
| Oct 29 | fresh-setup check, real call with 2 helpers, fixes | 2.5 |
| Oct 30 | rehearsal, chat export, repo, submit | 2 |
| | buffer | ~1.5 |
