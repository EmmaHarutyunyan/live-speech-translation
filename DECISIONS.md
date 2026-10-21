# DECISIONS

Each entry: what was decided, why, what else was considered, status. Newest at the bottom.

## D-001 — Capture system audio with Windows WASAPI loopback (2026-10-21)
- **Decision:** Record the call side directly from the output device ("Динамики (Realtek)") using WASAPI loopback.
- **Why:** Built into Windows; no extra driver; the user still hears the call normally. It is the Windows equivalent of the macOS BlackHole setup mentioned in the brief.
- **Alternatives:** VB-Audio Virtual Cable (extra driver, more setup); "Stereo Mix" (not present on this laptop's device list).
- **Status:** Accepted. Fallback to VB-Cable only if loopback fails in testing.

## D-002 — Run GPU models through CTranslate2; keep PyTorch on CPU only (2026-10-21)
- **Decision:** Use CTranslate2-based engines (faster-whisper for ASR, CTranslate2 for translation) on the GPU. Any PyTorch-based parts (e.g. speaker embeddings) run on the CPU.
- **Why:** The GTX 1060 is a Pascal GPU. The PyTorch team states that CUDA 12.8+ builds already dropped Pascal, CUDA 13 does not support it, and PyTorch 2.14 (cu126) is the last version with prebuilt Pascal support. CTranslate2 ships its own CUDA libraries, so it avoids this dependency.
  Source: https://dev-discuss.pytorch.org/t/notice-cuda-12-6-wheels-will-no-longer-be-published-from-pytorch-2-15-drops-maxwell-pascal-volta/3432
- **Alternatives:** PyTorch 2.14 cu126 on GPU (works today, but pins an old version; may be revisited if we need it to compare a model).
- **Status:** Accepted, pending GPU smoke test — CTranslate2 support for compute capability 6.1 and int8 speed are NOT yet verified.

## D-003 — Python 3.12 via the `py` launcher (2026-10-21)
- **Decision:** Use the installed Python 3.12 (`py -3.12`); do not install another Python.
- **Why:** Already installed; supported by the libraries we plan to use. `python` is not on PATH, so commands use `py -3.12` or the venv's Python.
- **Status:** Accepted.

## D-004 — Keep the virtual environment and model cache on D: (2026-10-21)
- **Decision:** venv at `D:\Em\mathrix\.venv`; model downloads cached inside the project folder, both excluded by `.gitignore`.
- **Why:** C: has only 26.6 GB free; models and libraries can take 10–15 GB.
- **Status:** Accepted.

## D-005 — Do not update the NVIDIA driver before the interview (2026-10-21)
- **Decision:** Keep driver 582.28.
- **Why:** NVIDIA has stated that the 580 branch is the last to support Maxwell/Pascal/Volta. A working setup must not be put at risk.
- **Status:** Accepted.

## D-006 — GitHub repository visibility (2026-10-21)
- **Decision:** Create the repository as private first; ask Mathrix whether they prefer a public link or collaborator access; switch before submission.
- **Why:** The brief only asks for "a link to a Git repository". The `chats/` folder will be included unedited, so nothing private may ever be pasted into a chat.
- **Status:** Pending answer from Mathrix.

## D-007 — Calling application for tests (2026-10-21)
- **Decision:** Google Meet in Chrome as primary test app (no install for helpers); Zoom as backup. Wired headphones; app output on the default device.
- **Why:** The program captures any system audio, so the app does not change the code. Free tier limits still to be verified.
- **Status:** Provisional — rehearse with the app Mathrix will use in the interview, once known.
