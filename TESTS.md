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

### M2 sub-step 2 — voice activity detection + segmenter (`scripts/vad_test.py`, 2026-10-25)
Settings: threshold 0.5, min silence 500 ms, max segment 10 s, speech padding 100 ms; fed in 10 ms blocks like live audio.
| Recording | Phrases (start–end, s) | Speech / total | Detected after phrase end | Processing per s of audio |
|---|---|---|---|---|
| `laptop_mic` (peak 0.137) | 1.44–4.90, 5.69–8.20 | 6.0 / 10.0 s | 0.46 s, 0.47 s | 0.144 s (first run, includes model load) |
| `headset_mic` (peak 0.008) | 1.34–6.34, 7.29–8.55 | 6.3 / 10.0 s | 0.46 s, 0.48 s | 0.031 s |
- ✅ Speech is split into phrases; leading, middle and trailing pauses are skipped.
- ✅ User listened to all 4 segment files: correct phrases, nothing cut off at start or end.
- ✅ End-of-phrase detection costs ~0.47 s of the 5 s latency budget.
- ✅ VAD is fast enough for live use (~3 % of real time after loading).
- Note: VAD also detects the very quiet headset speech — this does NOT mean ASR will understand it (D-012 stands).

## R2 — Armenian transcription
- ✅ R2-1 Evaluation set exists: `eval/sentences.txt` (10 sentences, committed) + `eval/audio/evalNN.wav`
  (laptop mic, peaks 0.105–0.293, git-ignored) (2026-10-25)
- ✅ R2-2 CER measured per setting with `scripts/eval_asr.py`; results below and in DECISIONS.md D-015/D-018

## R3 — English translation
- ✅ R3-1 NLLB-200 judged on the 10 evaluation sentences (user + Claude agreed, 2026-10-25): see M4 table below
- ✅ R3-2 Every transcribed segment gets an English line (live program and `eval_asr.py --translate`)

## R4 — Speaker identification
- ☐ R4-1 Everything from the mic is labelled `Me`
- ☐ R4-2 Two different remote voices get different labels (`Speaker 1`, `Speaker 2`)
- ☐ R4-3 Labels stay the same for the same person over a 10+ minute session (count wrong labels)

## R5 — Live terminal output
- ✅ R5-1 Each segment shows time, speaker, Armenian original, English translation (mic side, 2026-10-25; re-check with system audio in M5)
- ✅ R5-2 Segments appear while the conversation is still running (mic side, 2026-10-25)

## Constraints
- ☐ C-1 Latency: logged per segment as (end of phrase → English line printed); report median, worst case, % under 5 s
- ☐ C-2 Local only: full run works with Wi-Fi off after models are downloaded
- ☐ C-3 Repo contains no model weights, audio recordings or keys (`git ls-files` check)

## Deliverables
- ☐ D-1 README: setup + run + audio device setup; models + alternatives + reasons; architecture; limitations + improvements
- ☐ D-2 `chats/` contains every Cowork session, full and unedited, one `.md` file each (checked against `chats/INDEX.md`)
- ☐ D-3 Fresh rehearsal: program installed and audio setup working, live call with ≥ 2 people on the call side

## M2 — ASR and translation tests (2026-10-25, recording `laptop_mic`, reference:
"Բարև, ես հիմա փորձարկում եմ իմ խոսափողը, համակարգչով ոչինչ միացված չէ")
| Whisper model (beam 1, int8_float32, temperature 0) | CER | WER | Time per phrase (GPU) |
|---|---|---|---|
| small | 43 % | 91 % | ~0.5 s |
| medium | 37 % | 73 % | ~1.1 s |
| large-v3 | 21 % | 73 % | ~1.8 s (fits in 3 GB VRAM) |
- WER stays high because most large-v3 words are 1–2 letters off (Վարև/Բարև, խոսապողը/խոսափողը); CER is the fairer measure here.
- Recurring error: Armenian Բ recognised as Վ or Հ (Վարև, Վատև, Հարև for Բարև) — target for M3.
- NLLB-200 600M (CPU int8), ~0.3–0.9 s per phrase: correct Armenian → good English ("Nothing is connected to the
  computer.", "Hi, how are you?"); misspelled ASR output → meaning often changes ("deactivating my speaker").
  The ASR is the weakest link.

## M2 — live program `python -m hylive` (microphone only, laptop mic, 2026-10-25)
- ✅ Walking skeleton: speak → `[time] Me` + HY + EN in the terminal. `--list-devices` works in the main program.
- Latency (end of phrase → English line): single sentences 3.0 / 3.3 / 3.4 / 3.6 s (ASR 1.6–2.5 s, translation
  0.4–0.7 s, queue 0); two sentences merged into one phrase (pause < 0.5 s): **4.8 s** (ASR 3.0 s, translation 0.9 s).
- RISK for M6: ASR time grows with the number of words in a phrase → lower `--max-segment-s` (≈5–6 s) and measure.
- Live example: said «Վաղը ես կհանդիպեմ իմ ընկերներին» → HY «Ողաղը ես կահանդիպեմ իմ ընկերների» (CER 13 %)
  → EN "I'll meet my friends tomorrow." (correct).
- BUG FOUND AND FIXED: on Ctrl+C the main thread exited while the processing thread was still transcribing
  (found with the new "phrases detected / printed" counters: detected 2, printed 1 at exit) — this likely lost
  the sentences in the first live run. Fix: wait on a `threading.Event` instead of `Thread.join()` (D-017).
  - ✅ Test 1: 3 sentences, wait, Ctrl+C → detected 3, printed 3, summary printed last.
  - ✅ Test 2: Ctrl+C while still speaking → phrase rescued by `flush()`: detected 1 (1 at shutdown), printed 1.
- ✅ 0 PortAudio problem flags in all runs.

## M3 — Armenian ASR accuracy on the evaluation set (2026-10-25, `scripts/eval_asr.py`, live path incl. VAD)
Decision rule set in advance: lowest CER with max ASR time ≤ ~2.5 s; gains < ~2 CER points → keep the simpler/faster setting.
| Setting (large-v3, int8_float32, temperature 0) | CER | ASR avg | ASR max | Verdict |
|---|---|---|---|---|
| **beam 1, no prompt, pad 100 ms (baseline)** | **8.6 %** | 1.67 s | **1.89 s** | ✅ chosen |
| beam 5 | 6.4 % | 2.80 s | 3.73 s | ❌ too slow (latency would reach ~5 s); gain mostly from one sentence (07) |
| beam 5 + Armenian initial prompt | 12.8 % | 2.50 s | 3.85 s | ❌ worse: prompt caused a hallucination on 07 («3-3 անձր է վերկալիս») |
| beam 1, pad 300 ms | 7.7 % | 1.67 s | 1.87 s | ❌ only 0.9 points better, mixed per sentence, Բ errors unchanged |
- Perfect or near-perfect: 03 (0 %), 05, 10 (< 3 %). Hardest: 01, 07, 08 (~21 %).
- KNOWN LIMITATION: word-initial Բ is recognised as Վ or dropped in 3 of 4 cases (Վարև, Ոլորը, Վաժիշկը) in every
  setting. The pad-300 test rules out VAD clipping as the cause → it comes from Whisper itself on this voice/mic.
  Other recurring errors: ճ→ջ (սուրջ), dropped հ (շնորակալություն), split words (երեկ ոյան).
- Note: 8.6 % CER on read sentences is much better than the 21 % on the earlier spontaneous test recording —
  clear speech helps a lot (relevant for the interview).

## M4 — translation on the evaluation set (2026-10-25, `scripts/eval_asr.py --translate`, NLLB-200 600M CPU int8)
Judged "understandable?" (the brief's wording) by the user and Claude.
| # | EN from the correct Armenian | EN from the ASR text (what the live program shows) |
|---|---|---|
| 01 | ✅ Hi, how are you? | ❌ Wow, what do you look like? (Բ→Վ) |
| 02 | ✅ I'm fine, thank you. | ⚠️ Thank you very much. (gist only) |
| 03 | ✅ I'm meeting my friends tomorrow. | ✅ identical |
| 04 | ✅ They're all home now. | ✅ They've already returned home. |
| 05 | ✅ We're testing the new program today. | ⚠️ This is how we test the new program. |
| 06 | ✅ Can you repeat the last sentence? | ❌ You can make the last statement. |
| 07 | ✅ It was raining last night. | ❌ It was raining about three feet. |
| 08 | ✅ The doctor will call you in the morning. | ❌ The singer will be alive tomorrow morning. |
| 09 | ✅ Our meeting was moved to the next week. | ⚠️ …moved to the next round. |
| 10 | ✅ I like to drink coffee before work. | ❌ I like to drink seriously before work. (սուրջ for սուրճ) |
| | **10/10 understandable** | **2 correct, 3 gist, 5 wrong** |
- Translation time 0.38–0.53 s per sentence.
- KNOWN LIMITATION: the translator is good, but single-letter ASR errors often flip the meaning (coffee → seriously,
  doctor → singer). Improving the English means improving the Armenian ASR, not the translator.
