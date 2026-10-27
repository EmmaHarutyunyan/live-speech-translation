# hylive — live Armenian → English transcription in the terminal

A Python program that listens to a live conversation (your microphone **and** the other side of a call),
transcribes spoken Armenian, translates it to English and prints each phrase with time and speaker:

```
[00:00:39] Speaker 2
HY: Ներքին ճանապար էս անցել, որովհետև ներքին ինքն աբավությու
EN: I went through the inner path, because the inner self is the abomination.
    latency 4.0 s (ASR 2.5 s, translation 0.9 s, speaker 0.6 s, similarity 0.23, queue 0+0)

[00:00:23] Me
HY: խոսում են կին և տղամարդ։
EN: It's a woman and a man.
    latency 3.0 s (ASR 1.8 s, translation 0.7 s, queue 0+0)
```
(Real output from a test run; the spelling errors in the first block are Whisper's.)

Everything runs **locally** on the laptop (no cloud APIs); it was verified with Wi-Fi switched off.
Built for the Mathrix AI coding challenge on Windows 11 with an NVIDIA GTX 1060 (3 GB).

Honest summary of the result (details in [Test results](#test-results)):
- All required features work live: two audio sources at once, Armenian transcription, English translation,
  `Me` / `Speaker 1` / `Speaker 2` labels that stay stable, live terminal output.
- Latency: after the latency fixes, with one person speaking at a time, 93–100 % of phrases appeared within 5 s
  (median 2.8–4.0 s).
  **Not every phrase meets the 5 s target**: with overlapping speech the worst observed case was 8.7 s
  (64–70 % within 5 s), because one GPU transcribes one phrase at a time.
- Accuracy is the main limitation: Armenian is a low-resource language. Character error rate (CER) was 8.6 % on
  clearly read sentences, but small spelling errors often change the meaning of the English translation.

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
| RAM | 8 GB | Whisper on GPU; translation, voice detection and speaker model on CPU |
| Disk | ~7 GB for models | Keep the project on a drive with space; all models go into `models\` |
| Headphones | wired headphones | So the call audio does not leak into your microphone (see [Audio setup](#audio-setup-windows)) |

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
```

`requirements.txt` pins every package that was tested, including the NVIDIA cuBLAS/cuDNN libraries
(`nvidia-cublas-cu12`, `nvidia-cudnn-cu12`) and the CPU build of PyTorch.

```powershell
# 2. Check that the GPU works (downloads Whisper "tiny", ~75 MB)
.\.venv\Scripts\python.exe scripts\gpu_smoke_test.py          # must end with "SUCCESS"

# 3. Download the models into models\ (needs internet, once: Whisper large-v3 ~3 GB, NLLB tokenizer, speaker model)
.\.venv\Scripts\python.exe scripts\download_models.py

# 4. Convert the NLLB translation model to CTranslate2 int8 (needs internet, once; downloads ~2.5 GB)
#    HF_HOME keeps the download inside the project instead of C:\Users\<you>\.cache
$env:HF_HOME = "$PWD\models\hf_home"
.\.venv\Scripts\ct2-transformers-converter.exe --model facebook/nllb-200-distilled-600M `
    --output_dir models\nllb-200-distilled-600M-ct2-int8 --quantization int8
```

After these steps the program runs **without internet**: it sets `HF_HUB_OFFLINE=1` itself and loads every model
from `models\` ([D-024](DECISIONS.md)). The Silero voice-detection model is part of the `silero-vad` package.

## Audio setup (Windows)

No virtual audio driver is needed. Windows can record "what the speakers play" through **WASAPI loopback**; the
program records that loopback device for the call side and your microphone for `Me` — at the same time.

1. **Plug in wired headphones first**, then start the program (device numbers are read at start-up).
2. In the call app (Google Meet, Zoom, …) leave the **speaker/output on the Windows default device**, the one whose
   loopback you record. You hear the call normally.
3. Keep the **call volume moderate**. At normal volume our echo check found no call audio leaking into the headset
   microphone; with a loud video it did, and those phrases were then labelled `Me` (echo handling is out of scope).
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
program finishes the phrases it already heard and prints a summary per source:

```
mic    phrases detected: 4 (of which 1 at shutdown), printed: 4 (of which 0 discarded as repetitive), PortAudio problem flags: 0
       latency: median 3.0 s, max 3.9 s, <= 5 s: 4/4 (100 %)
system phrases detected: 16 (of which 0 at shutdown), printed: 16 (of which 0 discarded as repetitive), PortAudio problem flags: 0
       latency: median 4.1 s, max 5.9 s, <= 5 s: 14/16 (88 %)
speakers identified on the system side: 2 (threshold 0.35)
```

Each block shows time (session clock, the same for both sides), speaker, Armenian, English, and a measurement line:
`latency` = end of the spoken phrase → English line printed (the brief's definition), split into ASR, translation and
speaker time; `queue A+B` = phrases waiting for transcription + translation.

| Option | Default | Meaning |
|---|---|---|
| `--list-devices` | | print recordable devices and exit |
| `--mic N`, `--system N` | Windows defaults | microphone / loopback device |
| `--asr-model` | `large-v3` | faster-whisper model name |
| `--max-segment-s` | `5` | longest phrase before it is cut (longer phrases broke the 5 s latency) |
| `--min-silence-ms` | `500` | pause that ends a phrase |
| `--speaker-threshold` | `0.35` | voice similarity needed to count as a known speaker |
| `--sources` | `mic,system` | testing aid: `mic` or `system` only |

Special lines you may see: `HY: (repetitive output discarded - likely noise or echo …)` — Whisper produced a
repetition loop (typical for noise, music or laughter); it is shown but not translated, and the speaker is shown as
`Speaker ?`. `(cut at token limit)` — the output reached the safety limit of 128 tokens.

## How it works

```
 microphone ──► capture ──► 16 kHz mono ──► VAD + segmenter ──┐
                                                              ├─► phrase queue ─► ASR thread (GPU) ─► text queue ─► translation thread (CPU) ─► terminal
 loopback ────► capture ──► 16 kHz mono ──► VAD + segmenter ──┘     Whisper large-v3            speaker label (system side) + NLLB
 (+ silent keep-alive on the speakers)
```

| Module | Input → output |
|---|---|
| `hylive/audio_capture.py` | device → 10 ms audio blocks (PortAudio callback, native 48 kHz stereo); device lookup; keep-alive silence |
| `hylive/audio_convert.py` | blocks → 16 kHz mono float32 (channel average + streaming `soxr` resampler, no clicks at block edges) |
| `hylive/segmenter.py` | 16 kHz audio → phrases (Silero VAD: phrase ends after 500 ms of silence; cut at 5 s; one VAD model per source) |
| `hylive/asr.py` | phrase → Armenian text + reliability info (Whisper large-v3, beam 1, temperature 0, 128-token limit, repetition checks) |
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
| Speech recognition | **Whisper large-v3** via faster-whisper 1.2.1 (CTranslate2 4.8.3), GPU, `int8_float32`, beam 1 | small (CER 43 %), medium (37 %) on one test sentence; **large-v3-turbo**: 1.8× faster but CER 23.0 % vs 8.6 % on the 10-sentence set; beam 5: CER 6.4 % but max 3.7 s per phrase; Armenian initial prompt: CER 12.8 % (caused a hallucination) | Best Armenian accuracy that fits in 3 GB VRAM and stays fast enough (avg 1.7 s, max 1.9 s per phrase) |
| GPU engine | CTranslate2 (in faster-whisper) | PyTorch on GPU | Current PyTorch CUDA builds dropped GTX 10-series (Pascal) support; CTranslate2 supports `int8` on this GPU. PyTorch is used on the CPU only |
| Translation | **NLLB-200 distilled 600M**, converted to CTranslate2 int8, CPU | Helsinki-NLP opus-mt-hy-en (considered, not tested) | Explicit Armenian support; 0.3–0.9 s per phrase on the CPU, GPU stays free; 10/10 test sentences translated understandably. Rule set in advance: test opus-mt only if > 3/10 failed |
| Voice detection | **Silero VAD** 6.2.3 (`VADIterator`) + own segmenter | Silero copy inside faster-whisper (internal, whole-file API); webrtcvad | Official streaming API; ~3 % of real time; also stops Whisper from transcribing silence |
| Speaker identification | **SpeechBrain ECAPA-TDNN** (`speechbrain/spkrec-ecapa-voxceleb`), CPU | plain audio statistics; Whisper encoder output; ONNX speaker model (needs hand-written preprocessing) | Standard pretrained speaker model with built-in preprocessing, very little own code. Accepted only after a `pip --dry-run` showed it keeps our PyTorch and adds no large packages |
| Resampling | soxr 1.1.0 (streaming) | PyAV, numpy decimation, scipy | Streaming filter state between 10 ms blocks; tiny dependency |
| Audio capture | PyAudioWPatch 0.2.12.9 (WASAPI loopback) | soundcard; VB-Cable virtual driver | Loopback devices appear as normal inputs; no extra driver |

Licences to be aware of: Whisper weights — MIT; Silero VAD — MIT; SpeechBrain — Apache 2.0 (see the model card of
`spkrec-ecapa-voxceleb`); **NLLB-200 — CC-BY-NC 4.0 (non-commercial use only)**.

## Test results

All numbers come from runs on the target laptop; see [TESTS.md](TESTS.md) for every run, the method and the raw values.

### Armenian transcription
Evaluation set: 10 Armenian sentences read by me (laptop microphone), correct text in `eval/sentences.txt`, scored with
`scripts/eval_asr.py` through the same path as the live program (CER = character error rate after removing punctuation).

| Setting (large-v3) | CER | ASR time avg / max |
|---|---|---|
| **beam 1 (chosen)** | **8.6 %** | 1.67 s / 1.89 s |
| beam 5 | 6.4 % | 2.80 s / 3.73 s |
| beam 5 + Armenian prompt | 12.8 % | 2.50 s / 3.85 s |
| beam 1, 300 ms padding | 7.7 % | 1.67 s / 1.87 s |
| large-v3-turbo | 23.0 % | 0.93 s / 0.98 s |

- Live through system audio (sentences played as the "call side"): CER **5.7 %**, identical to offline on the same clips.
- Live, my own sentences over a playing video (headset mic): CER **12.4 %**.

### English translation
- From the correct Armenian text: **10/10** sentences understandable.
- From Whisper's text (what the program shows): **2 correct, 3 gist, 5 wrong** — e.g. «սուրջ» instead of «սուրճ»
  turned *coffee* into *seriously*. The translator is fine; transcription errors are the problem.

### Speaker identification
Three 60–80 s interview recordings with known speaker changes (`scripts/speaker_test.py`):

| Recording | Wrong labels at threshold 0.35 | Same speaker similarity | New speaker's first phrase |
|---|---|---|---|
| man + woman | 0 | 0.54–0.77 | 0.21 |
| same gender (first) | 0 (speaker returning after 20 s gets the same label) | 0.73–0.80 | 0.14 |
| two women (laughing, overlap) | 0 | 0.51–0.88 | 0.16 |

Thresholds 0.35 and 0.4 gave 0 errors on all three recordings (0.25–0.3 were tested on two of them, 0.45–0.5 on
one, also with 0 errors; 0.2 merged two speakers, 0.55 created extra ones). 0.35 is in the middle of the safe range. Live runs on the two-women clip
and on the man + woman interview gave the correct speakers (2 of 2).

### Latency (end of phrase → English line)

| Run | Within 5 s | Median | Max |
|---|---|---|---|
| Evaluation clips played as call side | 6/6 (100 %) | 2.8 s | 3.2 s |
| Two-women interview, call side only, with speaker ID | 18/18 (100 %) | 3.9 s | 4.4 s |
| Interview + speaker ID, user silent | 16/16 (100 %) | 4.0 s | 4.8 s |
| Full program (interview + my speech): `Me` | 4/4 (100 %) | 3.0 s | 3.9 s |
| Full program (interview + my speech): call side | 14/16 (88 %) | 4.1 s | 5.9 s |
| Earlier run with overlapping speech + echo (before speaker ID) | 64–70 % | 4.1–4.8 s | 8.7 s |

Phrases over 5 s came from: the first phrase after start-up, a repetition loop that the filter missed (a stricter
rule was added afterwards and checked on the recorded text, not yet in a new live run), and overlapping speech on both
sides (one GPU transcribes one phrase at a time).

### Other checks
- Both sources captured at the same time with 0 lost audio blocks (PortAudio problem flags 0 in all runs).
- No phrase lost on Ctrl+C: detected = printed in every run (a shutdown bug that lost phrases was found and fixed).
- **Offline**: full program with Wi-Fi off — all models load, no network access ([D-024](DECISIONS.md)).

## Known limitations

- **Armenian accuracy.** Word-initial «Բ» is often heard as «Վ» or dropped («Վարև» for «Բարև») in every setting
  tested; one wrong letter can change the English meaning. Clear speech helps a lot (CER 8.6 % read vs ~21 % on a
  spontaneous test recording).
- **Mixed languages.** Russian and English words inside Armenian (out of scope in the brief) are written in Armenian
  letters; translation recovers some ("meeting", "Okay") but not others («Давай» → "the lady of liberty").
- **Latency under overlapping speech.** One GPU transcribes one phrase at a time (~1.5–3 s each). When both sides
  talk at once, phrases wait and some exceed 5 s. The first phrase after start-up is also slower.
- **Phrase cutting.** Phrases are cut at 5 s to keep latency down; long sentences are split, which makes some
  translations choppy. If the speaker changes inside a phrase, its first 1–2 s get the previous speaker's label.
- **Speaker identification** was tested on 60–80 s clips with 2 speakers, not yet on 10+ minute calls, more than
  two people or real call compression (Meet/Zoom). Very short phrases keep the closest known speaker.
- **Echo.** If the call is loud enough to leak from the headphones into the microphone, it is transcribed again as
  `Me` (echo handling is out of scope). Use headphones and a moderate volume.
- **Repetition filter.** A real phrase that repeats the same words many times could be discarded as a loop.
- **Platform.** Windows only (WASAPI loopback) and an NVIDIA GPU is required; tested on one laptop.
- **NLLB licence** is non-commercial.

## What I would improve with more time

1. **Better Armenian recognition:** evaluate community Whisper models fine-tuned on Armenian (converted to
   CTranslate2) on the same evaluation set; collect a larger, more varied evaluation set (more speakers, real calls).
2. **Throughput under overlap:** transcribe several waiting phrases in one GPU batch (faster-whisper has a batched
   mode), or use a GPU with more memory/speed.
3. **Smarter phrase cutting:** cut at short pauses near the 5 s limit instead of exactly at 5 s; detect speaker
   changes inside a phrase.
4. **Robustness:** longer sessions and real calls with several people; tune the speaker threshold on call audio;
   simple echo suppression for setups without headphones.
5. **Usability:** pick devices by name, handle headphones being plugged in during a session.

## Repository layout

```
hylive/                 the program (python -m hylive)
scripts/                tools used to build and test it:
  gpu_smoke_test.py       GPU check            list_devices.py, record_test.py   devices / recordings
  download_models.py      one-time downloads   convert_test.py, vad_test.py       resampling / VAD checks
  asr_test.py, mt_test.py ASR / MT checks      record_eval.py, eval_asr.py        evaluation set + CER
  play_eval.py            play clips as call   speaker_test.py                    speaker ID thresholds
eval/sentences.txt      evaluation sentences (audio is not committed)
PLAN.md                 original plan         DECISIONS.md   every decision with reasons and numbers
TESTS.md                all test results      TIMELOG.md     time spent (~20 h budget)
HANDOVER.md             current state / next steps (used between work sessions)
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
