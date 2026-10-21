# Project rules (read at the start of every chat)

## Source of truth
- The official Mathrix AI challenge brief defines the requirements. Do not invent requirements.
- Out of scope (do not build): GUI, installer, echo handling, naming/remembering speakers across sessions, saving transcripts, non-Armenian input.
- Spare time goes into reliability of the core, not new features.

## Hard constraints
- Transcription, translation and speaker identification run locally. No cloud speech/translation APIs, no paid APIs.
- Never commit model weights, audio recordings, API keys or secrets.
- Never paste passwords, tokens or other people's personal data into any chat — chats are submitted unedited.
- Only Claude Cowork is used as AI assistant for this project.

## Environment
- Windows 11, GTX 1060 3 GB (Pascal), 8 GB RAM, Python 3.12 via `py -3.12`, venv at `D:\Em\mathrix\.venv`.
- Do not update the NVIDIA driver (see DECISIONS.md D-005).
- The user runs all commands in a normal (non-admin) PowerShell from `D:\Em\mathrix` and pastes the output back.

## Code style
- Keep audio, segmentation, ASR, translation, speakers and output in separate modules with clear inputs/outputs (see PLAN.md).
- Keep it simple and readable. Fail loudly with clear errors; no silent fallbacks, no hidden retries or timeouts.
- Do not add features or edge-case handling that the brief does not ask for.

## Way of working
- Ask before installing software, deleting files or making major changes.
- One change at a time; commit after every working step.
- Verify model names, APIs and parameters in official docs before using them; cite the source.
- Decide models by measurement (TESTS.md, eval set), not impressions.
- Record important decisions with reasons in DECISIONS.md.
- If something fails three times, stop, go back to the last working commit and narrow the problem down.
- Explain technical concepts in simple English.
