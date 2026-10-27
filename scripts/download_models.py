"""Download all models into models/ once, during setup (needs internet). Afterwards the program runs offline (D-024).

Run from the project folder, after installing requirements.txt:
    .\\.venv\\Scripts\\python.exe scripts\\download_models.py
The NLLB translation model must also be converted once (see README):
    ct2-transformers-converter --model facebook/nllb-200-distilled-600M ...
"""

import os

os.environ["HF_HUB_OFFLINE"] = "0"  # this script is the one place that is allowed to download

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from hylive.asr import MODELS_DIR, Transcriber  # noqa: E402  (imported first: registers the NVIDIA DLLs)
import transformers  # noqa: E402

from hylive.speakers import SpeakerEncoder  # noqa: E402
from hylive.translate import SOURCE_LANG, TOKENIZER_NAME  # noqa: E402


def main() -> None:
    print("1/3 Whisper large-v3 (~3 GB) ...", flush=True)
    Transcriber("large-v3")
    print("2/3 NLLB tokenizer ...", flush=True)
    transformers.AutoTokenizer.from_pretrained(TOKENIZER_NAME, src_lang=SOURCE_LANG, cache_dir=str(MODELS_DIR))
    print("3/3 speaker model (SpeechBrain ECAPA, ~80 MB) ...", flush=True)
    SpeakerEncoder()
    print(f"done: models are in {MODELS_DIR}. The Silero VAD model is included in the silero-vad package.")


if __name__ == "__main__":
    main()
