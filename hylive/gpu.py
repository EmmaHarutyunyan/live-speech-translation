"""Make the NVIDIA cuBLAS/cuDNN DLLs from the nvidia-* pip packages findable on Windows (DECISIONS.md D-008).

pip installs them in .venv\\Lib\\site-packages\\nvidia\\<lib>\\bin, which Windows does not search.
Must be called BEFORE ctranslate2 / faster_whisper is imported.
"""

import importlib.util
import os
from pathlib import Path

_registered = False


def register_nvidia_dlls() -> None:
    global _registered
    if _registered:
        return
    spec = importlib.util.find_spec("nvidia")
    if spec is None or not spec.submodule_search_locations:
        raise RuntimeError("The 'nvidia' pip packages are not installed in this environment.")
    bin_dirs = [p for loc in spec.submodule_search_locations for p in Path(loc).glob("*/bin") if p.is_dir()]
    if not bin_dirs:
        raise RuntimeError("No nvidia/*/bin folders with DLLs found.")
    for d in bin_dirs:
        os.add_dll_directory(str(d))                                    # DLLs loaded by Python
        os.environ["PATH"] = str(d) + os.pathsep + os.environ["PATH"]  # DLLs loaded later by CTranslate2
    _registered = True
