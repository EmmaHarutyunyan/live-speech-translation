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
- ✅ R1-1 Program prints a list of input devices (2026-10-23, `scripts/list_devices.py`): WASAPI only;
  mic = 9, loopback = 10, both 48 kHz / 2 ch. Same numbers with and without headphones plugged in.
  (To be re-ticked when the logic is in the main program as `--list-devices`.)
- ✅ R1-2 Devices chosen with `--mic` / `--system` (`scripts/record_test.py`); without flags the Windows
  default mic and default-speaker loopback are used and printed. Wrong device kinds are refused with an error.
- ✅ R1-3 Mic and system audio captured at the same time (2026-10-23): 15 s each, 10 ms blocks, largest gap
  0.016 s, 0 problem flags. Tested with a YouTube video, not yet with a real call (repeat in M5/M7).
- ✅ R1-4 User heard the video normally in headphones while capturing (2026-10-23).

### M1 measurements and notes
- Mic levels, normal speech, 10 s, nothing playing unless noted (corrected 2026-10-23 with labelled recordings;
  earlier values were assigned to the wrong mic — the earlier "laptop ~0.055" recording was the headset mic):
  | Setup | Active mic (channel correlation) | Peak | RMS |
  |---|---|---|---|
  | Room noise, nobody speaking | — | ~0.003 | — |
  | Headphones unplugged (`laptop`) | laptop 2-mic array (+0.75) | 0.137 | 0.0067 |
  | Headphones plugged in, cable mic hanging (`headset`) | headset cable mic (+0.99) | 0.008 | 0.0013 |
  | Headset cable mic held 10–15 cm from mouth (`headset_close`) | headset cable mic (+1.00) | 0.011 | 0.0018 |
  | Headphones unplugged, video playing on speakers | laptop array (+0.84) | 0.230 | 0.0125 |
  Earlier unlabelled headset recordings peaked at 0.020–0.055: the headset mic is weak AND variable.
- Check for which mic is active: channel correlation from `scripts/convert_test.py` —
  ~+0.75–0.84 = laptop array, ~+1.00 = headset cable mic (one mic copied to both channels).
- WASAPI loopback delivers no data while nothing plays: 0 blocks in 15 s of silence; when a video started
  late, the first block arrived after 1.47 s (see DECISIONS.md D-010).
- OPEN ISSUE: twice the mic recording seemed to contain no voice; no diagnostics were captured. Likely cause
  (updated): with headphones plugged in, the weak and variable headset cable mic was recording (see table).
  Rule: always read the printed peak level and correlation first. Close once the final headphone setup
  (D-012) is verified.

### M2 sub-step 1 — 48 kHz stereo → 16 kHz mono (`scripts/convert_test.py`, 2026-10-23)
- ✅ Block-by-block (10 ms) streaming conversion keeps the duration exactly (15.02→15.02 s, 15.03→15.03 s,
  10.01→10.01 s): no audio lost or duplicated at block edges.
- ✅ Averaging the two mic channels does not cancel the voice (correlation always positive; mono RMS ≈ channel RMS).
- ✅ Converted files sound clean (no clicks); the laptop's high-frequency noise above 8 kHz disappears.
- ☐ Recording 3 (`headset_video`: video playing + speaking) — postponed until the final headphone setup is chosen.

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
