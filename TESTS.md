# TESTS — derived from the brief, not from the code

Status: ☐ not run · ✅ passed · ❌ failed (with note)

## Environment
- ✅ ENV-1 Windows 11, GTX 1060 3 GB visible to `nvidia-smi`, driver 582.28 (2026-10-21)
- ✅ ENV-2 Python 3.12 available via `py -3.12` (2026-10-21)
- ✅ ENV-3 Armenian text (incl. ՞ and ։) displays correctly in PowerShell (2026-10-21)
- ✅ ENV-4 CTranslate2 / faster-whisper runs on the GPU (int8) (2026-10-21, `scripts/gpu_smoke_test.py`)
  - Supported GPU compute types reported: float32, int8, int8_float32
  - Whisper tiny, int8_float32, 5 s synthetic tone: 0.67 s with `temperature=0.0` (no retries);
    4.01 s with default temperature fallback (retries). Synthetic audio only — not a real speed benchmark.
- ☐ ENV-5 Program is run as a normal (non-admin) user from `D:\Em\mathrix`

## R1 — Two audio sources at once
- ☐ R1-1 Program prints a list of input devices
- ☐ R1-2 Mic and system-audio devices can be chosen by command-line flags
- ☐ R1-3 Mic and system audio are captured at the same time during a real call
- ☐ R1-4 The user still hears the call normally while capturing

## R2 — Armenian transcription
- ☐ R2-1 Evaluation set exists (short Armenian clips + correct text; audio kept local, not committed)
- ☐ R2-2 CER/WER measured for each candidate model; results recorded in DECISIONS.md

## R3 — English translation
- ☐ R3-1 Fixed Armenian sentence list with reference English; each candidate model judged "understandable" or not
- ☐ R3-2 Every transcribed segment gets an English line

## R4 — Speaker identification
- ☐ R4-1 Everything from the mic is labelled `Me`
- ☐ R4-2 Two different remote voices get different labels (`Speaker 1`, `Speaker 2`)
- ☐ R4-3 Labels stay the same for the same person over a 10+ minute session (count wrong labels)

## R5 — Live terminal output
- ☐ R5-1 Each segment shows time, speaker, Armenian original, English translation
- ☐ R5-2 Segments appear while the conversation is still running

## Constraints
- ☐ C-1 Latency: logged per segment as (end of phrase → English line printed); report median, worst case, % under 5 s
- ☐ C-2 Local only: full run works with Wi-Fi off after models are downloaded
- ☐ C-3 Repo contains no model weights, audio recordings or keys (`git ls-files` check)

## Deliverables
- ☐ D-1 README: setup + run + audio device setup; models + alternatives + reasons; architecture; limitations + improvements
- ☐ D-2 `chats/` contains every Cowork session, full and unedited, one `.md` file each (checked against `chats/INDEX.md`)
- ☐ D-3 Fresh rehearsal: program installed and audio setup working, live call with ≥ 2 people on the call side
