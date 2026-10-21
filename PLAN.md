# PLAN — Live Armenian Transcription → English Translation

Source of truth: the official Mathrix AI challenge brief. This plan must not add requirements that are not in the brief.

## Goal
A Python terminal program that captures the microphone and the system audio output at the same time,
transcribes spoken Armenian, translates it to English and prints each segment with time and speaker
label, within 5 seconds of the end of a spoken phrase. All models run locally.

## Modules (inputs → outputs)
| Module | Input | Output |
|---|---|---|
| `audio_capture` | device choice (CLI flag or printed list) | stream of audio chunks (mono, 16 kHz, float32) tagged with source `mic` / `system` and capture time |
| `segmenter` (VAD) | audio chunks of one source | `Segment(source, audio, start_time, end_time)` — one spoken phrase |
| `asr` | segment audio | Armenian text |
| `translate` | Armenian text | English text |
| `speakers` | source + segment audio | label: `Me` for mic; `Speaker 1`, `Speaker 2`, … for system audio, stable for the session |
| `output` | time, label, HY text, EN text | lines printed to the terminal |
| `main` / pipeline | CLI flags | starts capture threads, connects modules with queues |

Data flow: `mic + system capture → VAD → phrase queue → ASR → translation (+ speaker ID for system audio) → terminal`

## Milestones (~20 h, adjusted by real test results)
| # | Milestone | Est. h | Done when |
|---|---|---|---|
| M0 | Setup: docs, git, venv on D:, GPU smoke test | 1.5 | GPU usable from CTranslate2; docs committed |
| M1 | Audio capture: device list, flags, mic + loopback recorded at the same time | 2 | Both test recordings are clean during a real call |
| M2 | Walking skeleton (mic only): VAD → small ASR → MT → terminal | 2.5 | Armenian speech produces HY + EN lines with measured latency |
| M3 | Evaluation set + ASR model comparison | 3.5 | Numbers (CER/WER, speed) decide the ASR model |
| M4 | Translation model comparison | 1.5 | MT model chosen with reasons |
| M5 | Both streams + speaker identification | 3.5 | Two remote voices keep separate, stable labels |
| M6 | Latency and reliability | 2 | ≥ 95 % of segments under 5 s in a 10-minute call |
| M7 | README + full rehearsal | 2 | Someone else could follow the README; dry run passes |
| — | Buffer | 1.5 | |

## Main risks
1. Armenian ASR quality (low-resource language) — decide only by measurement on own recordings.
2. GTX 1060 (Pascal, 3 GB VRAM): current PyTorch GPU builds dropped Pascal; CTranslate2 support on compute capability 6.1 not yet verified.
3. Telling remote speakers apart live, from short, compressed call audio.
4. 5-second latency with two streams sharing one GPU.
5. Whisper inventing text on silence/noise (mitigated by VAD).
6. 8 GB RAM shared with the call app and browser.

## Testing
See `TESTS.md`. Decisions and their reasons: see `DECISIONS.md`.
