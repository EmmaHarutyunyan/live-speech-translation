# TIMELOG

Budget from the brief: about 20 hours ("please do not spend much more").
**Counting rule (set by the user, 2026-10-28):** only time actively working on the project — coding, testing,
debugging, writing docs. NOT counted: breaks, waiting (downloads, emails), time away from the computer.
**No guessing (user, 2026-10-29):** a block counts as *confirmed* only when the user gave or confirmed its active
time. Other values are Claude's estimates from message times and are marked as such; they may include waiting.

| Date | Start | End | Active h | Status | Milestone | Notes |
|---|---|---|---|---|---|---|
| 2026-10-21 | 18:32 | 23:20 | 2.5 | **confirmed** (user: "around 2.5 hours", 2026-10-23) | M0 | Requirements, plan, environment, docs, GPU smoke test, handover |
| 2026-10-23 | 17:31 | 19:10 | ~1.6 | estimate | M1 | Audio capture, device list, simultaneous recording, mic/loopback findings |
| 2026-10-23 | 19:10 | 20:00 | ~0.9 | estimate | M2 | 16 kHz conversion (soxr), `--label`, headset mic tests |
| 2026-10-25 | 01:41 | 02:45 | ~0.6 | estimate (time away excluded) | M2 | Silero VAD, segmenter |
| 2026-10-25 | 02:45 | 03:55 | ~1.1 | estimate | M2 | Whisper small/medium/large-v3, NLLB, live program, shutdown fix |
| 2026-10-25 | 03:56 | 04:05 | ~0.15 | estimate | M3 | Eval set + scripts |
| 2026-10-25 | 16:38 | 17:00 | ~0.35 | estimate | M3 | ASR settings compared |
| 2026-10-25 | 17:00 | 17:10 | ~0.15 | estimate | M4 | Translation judged |
| 2026-10-25 | 17:07 | 18:50 | ~1.7 | estimate (likely includes waiting) | M6 | System audio, keep-alive, latency fixes, real-world tests |
| 2026-10-27 | 17:40 | 19:25 | ~1.7 | estimate | M5 | Speaker identification |
| 2026-10-27 | 19:25 | 20:00 | ~0.6 | estimate | M6 | Echo/mixed-language checks, fixes, offline mode |
| 2026-10-27 | 20:00 | 20:20 | ~0.4 | estimate | M7 | README, download script |
| 2026-10-28 | 13:42 | 15:40 | ~1.3 | estimate (user asked to confirm; not yet confirmed) | M6 | Translation experiments (none adopted), natural set |
| 2026-10-29/30 | 21:33 | 00:20 | — | **waiting for the user's active minutes** (clock span 2 h 47 min = upper bound) | M6/M7 | Armenian turbo model adopted (D-027), punctuation cleanup, one-script setup, Zoom tests Z1/Z2, docs |

**Totals (2026-10-30, 00:20, last block not included yet):**
- Confirmed: **2.5 h** · Estimated (not confirmed): **~10.55 h** · Together: **~13.05 h** of ~20 h → **~6.95 h left**.
- The 2026-10-29/30 block is added as soon as the user gives its active minutes (not guessed). Its clock span is
  2 h 47 min, so at most: ~15.8 h used, ≥ ~4.2 h left. Remaining = 6.95 h − active time of that block.
