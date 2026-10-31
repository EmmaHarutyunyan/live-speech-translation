# HANDOVER — final day (2026-10-31)

Read this file, then `CLAUDE.md`. Details: `TESTS.md` (all measurements), `DECISIONS.md` (D-001 … D-028),
`TIMELOG.md`. The official Mathrix brief is the source of truth. Deadline: 2026-11-01 23:59 Yerevan time
(target: submit 2026-10-31). Strict 20 h limit: 3.5 h were left at 16:45 on 2026-10-31.

## How we work (agreed)
- Explain simply; one step at a time; ask before installing anything, changing files or deleting.
- The user runs every command in a normal PowerShell from `D:\Em\mathrix` with `.\.venv\Scripts\python.exe`.
- Verify facts before relying on them; measure with rules set in advance; no hardcoded fixes for test sentences.
- Never paste secrets into chats (chats are submitted unedited). Track only active time; never guess.

## Current state — feature complete, final live test done
- Program: `.\.venv\Scripts\python.exe -m hylive` (mic 9 + loopback 10 = Windows defaults on this laptop).
- Defaults: Armenian fine-tuned Whisper turbo (`models/whisper-turbo-armenian-ct2`, CTranslate2 int8, GPU, beam 5,
  D-027/D-028) → NLLB-200 600M (CPU int8, beam 2) → SpeechBrain ECAPA speaker labels (threshold 0.35, D-023).
  Phrases end after 500 ms silence, cut at 5 s. Offline (`HF_HUB_OFFLINE=1`, D-024).
- Setup: `pip install -r requirements.txt` + `scripts/download_models.py` (tested). README rewritten 2026-10-31.
- Models kept locally (git-ignored): turbo-armenian, large-v3 (fallback), tiny (GPU smoke test), NLLB ct2 + tokenizer,
  speaker model. Removed 2026-10-31: small, medium, plain turbo, `models/hf_home` (unused).
- Final 3-person Zoom test (TESTS.md): 33/33 phrases ≤ 5 s (max 4.1 s), 2 speakers correct, 0 audio problems;
  ECHO: 13 of 22 "Me" blocks were the friends' words (headset cable mic). User decision: no code fix (untested,
  would add latency) → documented limitation; for the interview use earphones without a microphone.

## Known limitations (all in README)
Natural-speech CER ~20 %; echo with a cable-mic headset; some repetition loops not caught (50 % unique words);
5 s cut splits sentences (fragment translations); Russian words; overlap not tested with the current model;
speaker ID only tested on 1–2 minute calls; Windows + NVIDIA only; NLLB non-commercial.

## NEXT — submission (in this order)
1. Commit + push the final docs (check: no audio/model files tracked).
2. Chat export → one .md per session in `chats/` (unedited) + update `chats/INDEX.md`; commit + push.
3. Repository check (clean clone view on GitHub, README renders, no large/secret files); visibility as Mathrix
   requires (public, or collaborator access).
4. Submit the repository link to Mathrix. Record the final active time in TIMELOG.md.
Not planned (time limit): echo filter, stricter loop filter, fresh-install check in a new folder.

- Repository: https://github.com/EmmaHarutyunyan/live-speech-translation
