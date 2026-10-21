"""GPU smoke test (milestone M0, TESTS.md ENV-4).

Checks that faster-whisper / CTranslate2 can run a Whisper model on this
laptop's GPU (GTX 1060, compute capability 6.1) with int8 weights.

Run from the project folder:
    .\\.venv\\Scripts\\python.exe scripts\\gpu_smoke_test.py

There is deliberately no CPU fallback: if the GPU does not work, this script
stops with an error so we see the real problem.
"""

import importlib.util
import os
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_DIR / "models"  # excluded by .gitignore
COMPUTE_TYPE = "int8_float32"        # the int8 type CTranslate2 uses on compute capability 6.1
SAMPLE_RATE = 16_000                 # Whisper expects 16 kHz mono audio


def add_nvidia_dlls_to_search_path() -> None:
    """Make the cuBLAS/cuDNN DLLs from the nvidia-* pip packages findable on Windows.

    pip puts them in .venv\\Lib\\site-packages\\nvidia\\<lib>\\bin, which Windows
    does not search by default. Must run BEFORE ctranslate2 is imported.
    """
    spec = importlib.util.find_spec("nvidia")
    if spec is None or not spec.submodule_search_locations:
        raise SystemExit("ERROR: the 'nvidia' pip packages are not installed in this environment.")

    bin_dirs = []
    for location in spec.submodule_search_locations:
        bin_dirs.extend(p for p in Path(location).glob("*/bin") if p.is_dir())
    if not bin_dirs:
        raise SystemExit("ERROR: no nvidia/*/bin folders with DLLs found.")

    for d in bin_dirs:
        print(f"  adding DLL folder: {d}")
        os.add_dll_directory(str(d))                              # for Python-loaded DLLs
        os.environ["PATH"] = str(d) + os.pathsep + os.environ["PATH"]  # for DLLs loaded later by CTranslate2


def main() -> None:
    print("1) Registering NVIDIA DLL folders")
    add_nvidia_dlls_to_search_path()

    import ctranslate2
    import numpy as np
    from faster_whisper import WhisperModel

    print(f"\n2) ctranslate2 {ctranslate2.__version__}")
    gpu_count = ctranslate2.get_cuda_device_count()
    print(f"   CUDA devices seen: {gpu_count}")
    if gpu_count == 0:
        raise SystemExit("ERROR: CTranslate2 does not see any CUDA GPU.")

    supported = sorted(ctranslate2.get_supported_compute_types("cuda"))
    print(f"   Supported compute types on GPU: {supported}")
    if COMPUTE_TYPE not in supported:
        raise SystemExit(f"ERROR: '{COMPUTE_TYPE}' is not supported on this GPU.")

    print(f"\n3) Loading Whisper 'tiny' on cuda with {COMPUTE_TYPE} (downloads ~75 MB the first time)")
    t0 = time.perf_counter()
    model = WhisperModel("tiny", device="cuda", compute_type=COMPUTE_TYPE,
                         download_root=str(MODELS_DIR))
    print(f"   Loaded in {time.perf_counter() - t0:.1f} s (model files in {MODELS_DIR})")

    print("\n4) Transcribing 5 s of generated test audio on the GPU (twice: 1st run includes warm-up)")
    t = np.arange(5 * SAMPLE_RATE) / SAMPLE_RATE
    audio = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)  # a quiet 440 Hz tone
    for run in (1, 2):
        t0 = time.perf_counter()
        segments, _info = model.transcribe(audio, language="hy", beam_size=1, temperature=0.0)
        text = " ".join(s.text for s in segments)  # transcription runs while we read the segments
        print(f"   run {run}: {time.perf_counter() - t0:.2f} s, text={text!r} (text content does not matter here)")

    print("\nSUCCESS: Whisper runs on the GPU with", COMPUTE_TYPE)


if __name__ == "__main__":
    main()
