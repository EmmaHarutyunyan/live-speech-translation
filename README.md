# hylive — live Armenian → English transcription in the terminal

A Python program that listens to a live conversation (your microphone **and** the other side of a call),
transcribes spoken Armenian, translates it to English and prints each phrase with time and speaker.

Real output from a live test with the default settings (microphone, 2026-10-31), unedited:

```
[00:00:03] Me
HY: Բարև, ո՞նց ես.
EN: Hi, how are you?
    latency 2.7 s (ASR 1.7 s, translation 0.5 s, queue 0+0)

[00:00:05] Me
HY: Այսօր ամբողջ օրը զբաղված էի.
EN: I was busy all day today.
    latency 1.9 s (ASR 1.0 s, translation 0.4 s, queue 0+0)

[00:00:07] Me
HY: Բայց վերջապես կարողացա ավարտել իմ աշխատանքը։
EN: But I was finally able to finish my work.
    latency 2.1 s (ASR 1.0 s, translation 0.5 s, queue 0+0)

[00:00:12] Me
HY: Երեք ընկերուհուս հետ խոսում էինք մեր ապագա պլաների մասի՞
EN: Did we talk to three friends about our future plans?
    latency 2.2 s (ASR 1.1 s, translation 0.6 s, queue 0+0)

[00:00:17] Me
HY: Ու որոշեցինք մյուս շաբաթ հանդիպել։
EN: And we decided to meet next week.
    latency 1.9 s (ASR 1.0 s, translation 0.4 s, queue 0+0)
```
The fourth block shows a typical error: «Երեկ» (yesterday) was heard as «Երեք» (three) and a question mark was
added, so the English became a wrong question. Call-side phrases are labelled `Speaker 1`, `Speaker 2`, …

Everything runs **locally** (no cloud APIs; verified with Wi-Fi switched off). Built for the Mathrix AI coding
challenge on Windows 11 with an NVIDIA GTX 1060 (3 GB).

Summary of the result (details in [Test results](#test-results)):
- All required features work live: two audio sources at once, Armenian transcription, English translation,
  `Me` / `Speaker N` labels that stay stable within a session, live terminal output.
- Latency: in the live and Zoom tests with the current model (including a 3-person Zoom call), every phrase
  appeared within 5 s (median 2.1–2.9 s).
  This is not guaranteed: one GPU transcribes one phrase at a time, and with the earlier, slower model overlapping
  speech produced delays of up to 8.7 s.
- Accuracy is the main limitation. On clearly read sentences the character error rate (CER) is 1.3 %; on natural,
  fast speech it is about 20 %, and single wrong letters can change the meaning of the English translation.
- Echo: in Zoom with a headset whose microphone sits on the earphone cable, the call leaked into the microphone and
  was transcribed a second time as `Me` (more than half of the `Me` blocks in the final test; see
  [Known limitations](#known-limitations)).

---

## Contents
1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Audio setup (Windows)](#audio-setup-windows)
4. [Running](#running)
5. [How it works](#how-it-works)
6. [Models: what was chosen and why](#models-what-was-chosen-and-why)
7. [Test results](#test-results)
8. [Known limitations](#known-limitations)
9. [What I would improve with more time](#what-i-would-improve-with-more-time)
10. [Repository layout](#repository-layout)
11. [How this was built](#how-this-was-built)

---

## Requirements

| | Tested with | Notes |
|---|---|---|
| OS | Windows 11 | System audio is captured with **WASAPI loopback** (Windows only) |
| GPU | NVIDIA GTX 1060 3 GB, driver 582.28 | Required: Whisper runs on the GPU with `int8_float32`. CUDA 12 libraries are installed by pip; no CUDA Toolkit needed |
| Python | 3.12 (`py -3.12`) | |
| RAM | 8 GB | Whisper on the GPU; translation, voice detection and speaker model on the CPU |
| Disk | ~6 GB free during setup, ~1.6 GB of models afterwards | All models go into `models\` |
| Headphones | wired headphones | So the call audio does not reach your microphone (see [Audio setup](#audio-setup-windows)) |

Do **not** update the NVIDIA driver on a GTX 10-series card without reason: NVIDIA's 580 driver branch is the last
one that supports this GPU generation ([D-005](DECISIONS.md)).

## Installation

All commands: a **normal (non-administrator) PowerShell**, in the project folder.

```powershell
git clone https://github.com/EmmaHarutyunyan/live-speech-translation.git
cd live-speech-translation

# 1. Virtual environment (no activation needed; we always call its python.exe directly)
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt

# 2. Check that the GPU works (downloads Whisper "tiny", ~75 MB)
.\.venv\Scripts\python.exe scripts\gpu_smoke_test.py          # must end with "SUCCESS"

# 3. Download and convert all models into models\ (needs internet, once)
.\.venv\Scripts\python.exe scripts\download_models.py
```

`requirements.txt` pins every tested package, including the NVIDIA cuBLAS/cuDNN libraries and the CPU build of
PyTorch. `download_models.py` downloads the Armenian Whisper model and NLLB-200, converts both to CTranslate2 int8,
and downloads the NLLB tokenizer and the speaker model. It skips anything already present. The original downloads are
kept in `models\hf_home` (~5 GB) and can be deleted after setup. Optional: `--with-large-v3` also downloads the
previous ASR model (~3 GB) as a fallback.

After setup the program runs **without internet**: it sets `HF_HUB_OFFLINE=1` itself and loads every model from
`models\` ([D-024](DECISIONS.md)). The Silero voice-detection model is part of the `silero-vad` package.

## Audio setup (Windows)

No virtual audio driver is needed. Windows can record "what the speakers play" through **WASAPI loopback**; the
program records that loopback device for the call side and your microphone for `Me`, at the same time.

1. **Plug in wired headphones first**, then start the program (device numbers are read at start-up).
2. In the call app (tested with Zoom desktop) set **speaker and microphone to the Windows default devices** ("Same as
   System"). You hear the call normally in the headphones.
3. Keep the call volume moderate and make sure the call audio cannot reach the microphone. With a headset whose
   microphone is on the earphone cable, Zoom audio leaked into the microphone even at 30–40 % volume. Earphones
   without a microphone (the laptop microphone is then used) avoid this; that setup is the recommended one but has
   not been measured yet.
4. List the devices:

```powershell
.\.venv\Scripts\python.exe -m hylive --list-devices
```
```
   9  INPUT     2 ch  48000 Hz  Микрофон (Realtek(R) Audio)
  10  LOOPBACK  2 ch  48000 Hz  Динамики (Realtek(R) Audio) [Loopback]
```

Without flags the program uses the **Windows default microphone** and the **loopback of the default speakers**, and
prints which ones it chose. Choose others with `--mic <INPUT index>` and `--system <LOOPBACK index>`.

While capturing the call side, the program plays **digital silence** (inaudible) on those speakers: Windows sends no
loopback data at all while nothing plays, which would stop phrase detection ([D-010, D-019](DECISIONS.md)).

## Running

```powershell
.\.venv\Scripts\python.exe -m hylive                       # default devices
.\.venv\Scripts\python.exe -m hylive --mic 9 --system 10   # chosen devices
```

Wait for `Ready.` (all models are loaded and warmed up first), then talk / start the call. Stop with **Ctrl+C**: the
program finishes the phrases it already heard and prints a summary per source, for example (real Zoom test):

```
mic    phrases detected: 14 (of which 0 at shutdown), printed: 14 (of which 0 discarded as repetitive), PortAudio problem flags: 0
       latency: median 2.2 s, max 3.1 s, <= 5 s: 14/14 (100 %)
system phrases detected: 8 (of which 0 at shutdown), printed: 8 (of which 0 discarded as repetitive), PortAudio problem flags: 0
       latency: median 2.9 s, max 5.0 s, <= 5 s: 8/8 (100 %)
```

Each block shows time (session clock, the same for both sides), speaker, Armenian, English, and a measurement line:
`latency` = end of the spoken phrase → English line printed (the brief's definition), split into ASR, translation and
speaker time; `similarity` = voice match with the chosen speaker; `queue A+B` = phrases waiting for transcription +
translation.

| Option | Default | Meaning |
|---|---|---|
| `--list-devices` | | print recordable devices and exit |
| `--mic N`, `--system N` | Windows defaults | microphone / loopback device |
| `--asr-model` | Armenian Whisper turbo in `models\` | path or faster-whisper name (e.g. `large-v3` after `--with-large-v3`) |
| `--asr-beam` | `5` | Whisper beam size |
| `--max-segment-s` | `5` | longest phrase before it is cut (longer phrases broke the 5 s latency) |
| `--min-silence-ms` | `500` | pause that ends a phrase |
| `--speaker-threshold` | `0.35` | voice similarity needed to count as a known speaker |
| `--sources` | `mic,system` | testing aid: `mic` or `system` only |

Special lines you may see: `HY: (repetitive output discarded - likely noise or echo …)` means Whisper produced a
repetition loop (typical for noise, music or laughter); it is shown but not translated, and the speaker is shown as
`Speaker ?`. `(cut at token limit)` means the output reached the safety limit of 128 tokens.

## How it works

```
 microphone ──► capture ──► 16 kHz mono ──► VAD + segmenter ──┐
                                                              ├─► phrase queue ─► ASR thread (GPU) ─► text queue ─► translation thread (CPU) ─► terminal
 loopback ────► capture ──► 16 kHz mono ──► VAD + segmenter ──┘     Whisper (Armenian turbo)    speaker label (call side) + NLLB
 (+ silent keep-alive on the speakers)
```

| Module | Input → output |
|---|---|
| `hylive/audio_capture.py` | device → 10 ms audio blocks (PortAudio callback, native 48 kHz stereo); device lookup; keep-alive silence |
| `hylive/audio_convert.py` | blocks → 16 kHz mono float32 (channel average + streaming `soxr` resampler, no clicks at block edges) |
| `hylive/segmenter.py` | 16 kHz audio → phrases (Silero VAD: phrase ends after 500 ms of silence; cut at 5 s; one VAD model per source) |
| `hylive/asr.py` | phrase → Armenian text + reliability info (beam 5, temperature 0, 128-token limit, repetition checks, punctuation cleanup) |
| `hylive/speakers.py` | phrase → `Speaker N` (voice fingerprint + online clustering) |
| `hylive/translate.py` | Armenian → English (NLLB-200 600M via CTranslate2) |
| `hylive/__main__.py` | command line, threads, output, summary, offline mode |

Design points:
- **Two sources, one GPU.** Each source has its own capture and segmentation thread; one shared ASR thread uses the
  GPU (one phrase at a time); a separate translation thread on the CPU lets the GPU start the next phrase while the
  previous one is translated ([D-017, D-021](DECISIONS.md)).
- **Bounded work per phrase.** Without limits, a Whisper repetition loop once took 7–8 s plus a 17–20 s translation
  and the queue grew to 90 s of delay. Phrases are now cut at 5 s, Whisper output is limited, loops are detected and
  discarded visibly, and translation length is limited ([D-020, D-025](DECISIONS.md)).
- **Speaker identification.** For each call-side phrase, SpeechBrain ECAPA-TDNN computes a 192-number voice
  fingerprint on the CPU. It is compared (cosine similarity) with each known speaker's average fingerprint: ≥ 0.35 →
  that speaker, otherwise a new `Speaker N`. Phrases under 1 s never create a speaker. Everything from the microphone
  is `Me` ([D-023](DECISIONS.md)).
- **Fail loudly.** No silent fallbacks: wrong devices, missing models or a crashed thread stop the program with a
  clear error; the summary shows detected vs. printed phrases so lost phrases would be visible.

## Models: what was chosen and why

All decisions with the full reasoning and numbers are in [DECISIONS.md](DECISIONS.md); measurements in [TESTS.md](TESTS.md).

| Task | Chosen | Alternatives tested / considered | Why |
|---|---|---|---|
| Speech recognition | **`Chillarmo/whisper-large-v3-turbo-armenian`** (Whisper large-v3-turbo fine-tuned on Common Voice Armenian), converted to CTranslate2 int8, run with faster-whisper 1.2.1 on the GPU, beam 5 | Whisper small and medium (CER 43 % / 37 % on one test sentence); **large-v3** (previous default: CER 8.6 % read / 27.2 % natural, 12 setting variations tried without a clear gain); plain large-v3-turbo (CER 23 %) | Clearly the most accurate on all three test sets, and about twice as fast as large-v3 (≈1.0–1.5 s per phrase), so beam 5 costs almost no latency ([D-027, D-028](DECISIONS.md)) |
| GPU engine | CTranslate2 (in faster-whisper) | PyTorch on GPU | Current PyTorch CUDA builds dropped GTX 10-series (Pascal) support; CTranslate2 supports `int8` on this GPU. PyTorch is used on the CPU only |
| Translation | **NLLB-200 distilled 600M**, converted to CTranslate2 int8, CPU, beam 2 | Helsinki-NLP opus-mt-hy-en (considered); larger beams, Whisper's own speech translation (tested, not better) | Explicit Armenian support; 0.3–0.9 s per phrase on the CPU, GPU stays free; 10/10 correct Armenian test sentences translated understandably |
| Voice detection | **Silero VAD** 6.2.3 (`VADIterator`) + own segmenter | Silero copy inside faster-whisper (internal, whole-file API); webrtcvad | Official streaming API; ~3 % of real time; also stops Whisper from transcribing silence |
| Speaker identification | **SpeechBrain ECAPA-TDNN** (`speechbrain/spkrec-ecapa-voxceleb`), CPU | plain audio statistics; Whisper encoder output; ONNX speaker model (needs hand-written preprocessing) | Standard pretrained speaker model with built-in preprocessing, very little own code; keeps the existing PyTorch and adds no large packages |
| Resampling | soxr 1.1.0 (streaming) | PyAV, numpy decimation, scipy | Streaming filter state between 10 ms blocks; tiny dependency |
| Audio capture | PyAudioWPatch 0.2.12.9 (WASAPI loopback) | soundcard; VB-Cable virtual driver | Loopback devices appear as normal inputs; no extra driver |

Licences: Armenian Whisper turbo — Apache 2.0; Whisper — MIT; Silero VAD — MIT; SpeechBrain — Apache 2.0;
**NLLB-200 — CC-BY-NC 4.0 (non-commercial use only)**.

## Test results

All numbers come from runs on the target laptop; [TESTS.md](TESTS.md) has every run, the method and the raw values.

### Armenian transcription and English translation
Three sets of my own recordings with known correct text and reference translations (`eval/`): **read** (10 clearly
read sentences), **natural** (6 colloquial sentences at normal call speed), **check** (5 sentences recorded later,
used only to confirm the model change). Scored with `scripts/eval_asr.py` through the same path as the live program.
CER/WER = character/word error rate after removing punctuation; English judged by hand as correct / gist / wrong.

| Set | Model | CER | WER | English correct / gist / wrong | ASR max per phrase |
|---|---|---|---|---|---|
| read (10) | large-v3, beam 1 (previous) | 8.6 % | | 2 / 3 / 5 | 2.08 s |
| read (10) | **turbo-armenian, beam 5** | **1.3 %** | 8.2 % | 9 / 1 / 0 (beam 1) | 1.89 s (all sets) |
| natural (6) | large-v3, beam 1 | 27.2 % | | 0 / 3 / 3 | 2.63 s |
| natural (6) | **turbo-armenian, beam 5** | **19.5 %** | 37.0 % | 2 / 2 / 2 (beam 1) | |
| check (5) | large-v3, beam 1 | 11.6 % | | 0 / 2 / 3 | 2.87 s |
| check (5) | **turbo-armenian, beam 5** | **5.6 %** | 17.5 % | 3 / 1 / 1 (beam 1, with punctuation cleanup) | |

- Beam 5 vs beam 1 on turbo-armenian: better or equal on every set (all 21 sentences: CER 9.25 → 8.64 %). The gain is
  smaller than the 1-point threshold I set before the test; it was adopted because nothing got worse and the latency
  cost is ~0.1 s ([D-028](DECISIONS.md)). The English judgements were made with beam 1 and not repeated.
- From the *correct* Armenian text NLLB translated 10/10 read sentences understandably: the remaining English errors
  come mostly from transcription errors (e.g. «սուրջ» instead of «սուրճ» turned *coffee* into *seriously* with the
  previous model).
- Remaining typical errors: թ/տ and similar sounds («կատ» → "goats"), «Երեք» for «Երեկ», Russian words, words
  split in two («Խոս ափող»).

### Speaker identification
Three 60–80 s interview recordings with known speaker changes (`scripts/speaker_test.py`):

| Recording | Wrong labels at threshold 0.35 | Same speaker similarity | New speaker's first phrase |
|---|---|---|---|
| man + woman | 0 | 0.54–0.77 | 0.21 |
| same gender | 0 (speaker returning after 20 s gets the same label) | 0.73–0.80 | 0.14 |
| two women (laughing, overlap) | 0 | 0.51–0.88 | 0.16 |

Thresholds 0.35 and 0.4 gave 0 errors on all three recordings; 0.2 merged two speakers and 0.55 created extra ones.
Live runs on two of the recordings gave the correct speakers. In the final 3-person Zoom test (two friends on the
call side) the labels were correct: `Speaker 1` and `Speaker 2`, and Speaker 1 kept its label when returning after
Speaker 2 (similarity 0.81). In earlier Zoom runs, a very short first phrase sometimes created an extra speaker.

### Latency (end of phrase → English line)

| Run | Model | Within 5 s | Median | Max |
|---|---|---|---|---|
| Live microphone, 2026-10-31 | turbo-armenian, beam 5 | 8/8 | 2.1 s | 2.7 s |
| **Zoom, 2 friends, fast natural speech (final test): `Me` / call side** | turbo-armenian, beam 5 | **22/22 / 11/11** | **2.6 / 2.7 s** | **4.1 / 3.3 s** |
| Zoom, 1 helper (Z1): `Me` / call side | turbo-armenian, beam 1 | 9/9 / 5/5 | 2.5 / 3.0 s | 4.4 / 4.0 s |
| Zoom, 1 helper, both talking (Z2): `Me` / call side | turbo-armenian, beam 1 | 14/14 / 8/8 | 2.2 / 2.9 s | 3.1 / 5.0 s |
| Interview played as call side + my speech | large-v3, beam 1 | 18/20 | 3.0–4.1 s | 5.9 s |
| Overlapping speech + echo (before later fixes) | large-v3, beam 1 | 64–70 % | 4.1–4.8 s | 8.7 s |

Z1 and Z2 used beam 1, before beam 5 became the default. In the final test, sentences cut at the 5 s limit gave
most of the wrong translations (call side: ~6 correct, 2 gist, 3 wrong of 11, by my judgement; [TESTS.md](TESTS.md)).

### Other checks
- Both sources captured at the same time with 0 lost audio blocks (PortAudio problem flags 0 in all runs).
- No phrase lost on Ctrl+C: detected = printed in every run (a shutdown bug that lost phrases was found and fixed).
- **Offline**: full program with Wi-Fi off — all models load, no network access ([D-024](DECISIONS.md)).

## Known limitations

- **Armenian accuracy on natural speech.** CER is ~20 % on fast colloquial speech (1.3 % on clear reading). One
  wrong letter can change the English meaning, and a wrongly added `՞` turns a statement into a question.
- **Echo.** If call audio reaches the microphone, it is transcribed again as `Me` (echo handling is out of scope in
  the brief). This happened in Zoom with a headset whose microphone is on the earphone cable: in the final 3-person
  test, 13 of 22 `Me` blocks repeated the friends' words. An echo filter was not added because it would delay `Me`
  lines and could not be tested before submission. Earphones without a microphone should avoid it but were not measured.
- **Repetition filter.** It catches most Whisper loops but not all: a loop with 50 % different words was printed
  and translated (the filter needs < 40 %). A real phrase that repeats the same words many times could be discarded.
- **Mixed languages.** Russian and English words inside Armenian (out of scope in the brief) are written in Armenian
  letters; translation recovers some ("meeting", "Okay") but not others.
- **Latency under overlapping speech.** One GPU transcribes one phrase at a time. When both sides talk at once,
  phrases wait; the 5 s target is not guaranteed. The first phrase after start-up is also slower.
- **Phrase cutting.** Phrases are cut at 5 s to keep latency down; long sentences are split, which makes some
  translations choppy. If the speaker changes inside a phrase, the whole phrase gets one label.
- **Speaker identification** was tested on short recordings and Zoom calls with up to two other people (1–2 minutes
  each), not on long calls. Very short phrases can create an extra speaker or keep the closest known one.
- **Overlapping speech** was not tested with the current model in the final Zoom test.
- **Platform.** Windows only (WASAPI loopback), an NVIDIA GPU is required; tested on one laptop.
- **NLLB licence** is non-commercial.

## What I would improve with more time

1. **Echo:** drop a `Me` phrase that overlaps in time with a call-side phrase and has nearly the same text, or use
   proper echo cancellation.
2. **Accuracy:** a larger, more varied evaluation set (more speakers, real call audio); fine-tuning or evaluating
   further Armenian models on it; a stricter but tested repetition filter.
3. **Throughput under overlap:** transcribe several waiting phrases in one GPU batch, or use a faster GPU.
4. **Smarter phrase cutting:** cut at short pauses near the 5 s limit; detect speaker changes inside a phrase.
5. **Robustness and usability:** longer sessions with more people; tune the speaker threshold on call audio; pick
   devices by name; handle headphones being plugged in during a session.

## Repository layout

```
hylive/                 the program (python -m hylive)
scripts/                tools used to build and test it:
  gpu_smoke_test.py       GPU check            list_devices.py, record_test.py   devices / recordings
  download_models.py      one-time setup       convert_test.py, vad_test.py       resampling / VAD checks
  asr_test.py, mt_test.py ASR / MT checks      record_eval.py, eval_asr.py        evaluation sets + CER/WER/chrF
  play_eval.py            play clips as call   speaker_test.py                    speaker ID thresholds
eval/                   evaluation sentences and reference translations (audio is not committed)
PLAN.md                 original plan         DECISIONS.md   every decision with reasons and numbers
TESTS.md                all test results      TIMELOG.md     time spent (20 h limit)
HANDOVER.md             state / next steps between work sessions
CLAUDE.md               project rules given to the AI assistant
chats/                  complete, unedited AI chat transcripts (required by the brief)
requirements.txt        pinned package versions
```

Not committed (`.gitignore`): model weights (`models/`), audio recordings (`recordings/`, `eval/audio/`), the
virtual environment, secrets.

## How this was built

I worked with Claude Cowork as the only AI assistant, step by step: plan first, a thin end-to-end version early,
then improving the weakest part, deciding by measurements with rules set before each test. Every decision and test is
written down in `DECISIONS.md` and `TESTS.md`; the complete conversations are in `chats/`.
