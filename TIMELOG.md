# TIMELOG

Budget from the brief: about 20 hours ("please do not spend much more").
Hours are active working time as estimated by the user, not wall-clock time.

| Date | Start | End | Hours | Milestone | Notes |
|---|---|---|---|---|---|
| 2026-10-21 | 18:32 | 23:20 | ~2.5 | M0 | Requirements, plan, environment check, project docs, GPU smoke test, handover (with breaks) |
| 2026-10-23 | 17:31 | 19:10 | ~1.6 | M1 | Audio capture: PyAudioWPatch, device list, simultaneous recording, mic level / loopback findings |
| 2026-10-23 | 19:10 | 20:00 | ~0.9 | M2 | Sub-step 1: soxr 16 kHz mono conversion; `--label`; labelled mic tests → headset mic rejected (D-012 corrected) |
| 2026-10-25 | 01:41 | 02:45 | ~0.6 | M2 | Sub-step 2: silero-vad + torch CPU, segmenter, VAD test on recordings (time away from laptop excluded) |
| 2026-10-25 | 02:45 | 03:55 | ~1.1 | M2 | Whisper small/medium/large-v3, NLLB translation, live program, shutdown bug fix (M2 complete) |
| 2026-10-25 | 03:56 | 04:05 | ~0.15 | M3 | Evaluation set (10 sentences) + record/eval scripts written, not yet run |
| 2026-10-25 | 16:38 | 17:00 | ~0.35 | M3 | Recorded eval set, 4 ASR settings compared, Բ hypothesis tested; M3 closed |
| 2026-10-25 | 17:00 | 17:10 | ~0.15 | M4 | Translation judged on the eval set (`--translate`); NLLB kept, opus-mt not needed |
| 2026-10-25 | 17:07 | 18:50 | ~1.7 | M6 (early) | System audio: keep-alive, two streams, phrase bounds, translation thread, turbo test, Test A, real-world test, docs |
| 2026-10-27 | 17:40 | 19:25 | ~1.7 | M5 | Speaker ID: option check, SpeechBrain install, 3 recordings with ground truth, short-phrase rule, live L1/L2, docs |
| 2026-10-27 | 19:25 | 20:00 | ~0.6 | M6 | Echo check, mixed-language check, small fixes, offline mode + download script, docs |
| 2026-10-27 | 20:00 | 20:20 | ~0.4 | M7 | README (first complete version), download script tested |

**Total so far:** ~11.9 h of ~20 h (≈ 8 h left; target: finish Oct 30, deadline Nov 1 23:59)
