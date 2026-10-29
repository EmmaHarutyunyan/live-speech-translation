"""Download and prepare all models in models/ once, during setup (needs internet). Afterwards the program
runs offline (D-024). This is the only setup step after installing requirements.txt.

Run from the project folder:
    .\\.venv\\Scripts\\python.exe scripts\\download_models.py
    .\\.venv\\Scripts\\python.exe scripts\\download_models.py --with-large-v3   (also the fallback ASR model, ~3 GB)
"""

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
os.environ["HF_HUB_OFFLINE"] = "0"  # this script is the one place that is allowed to download
os.environ.setdefault("HF_HOME", str(PROJECT_DIR / "models" / "hf_home"))  # keep downloads inside the project (D-004)

import argparse  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, str(PROJECT_DIR))

from hylive.asr import DEFAULT_MODEL_DIR, MODELS_DIR, Transcriber  # noqa: E402  (imported first: NVIDIA DLLs)
import transformers  # noqa: E402
from ctranslate2.converters import TransformersConverter  # noqa: E402

from hylive.speakers import SpeakerEncoder  # noqa: E402
from hylive.translate import MODEL_DIR as NLLB_DIR, SOURCE_LANG, TOKENIZER_NAME  # noqa: E402

ASR_SOURCE = "Chillarmo/whisper-large-v3-turbo-armenian"  # Armenian fine-tuned Whisper large-v3-turbo (D-027)
NLLB_SOURCE = "facebook/nllb-200-distilled-600M"


def convert(source: str, output_dir: Path, copy_files: list[str] | None = None) -> None:
    """Download a Hugging Face model and convert it to CTranslate2 int8 (skipped if already converted)."""
    if output_dir.exists():
        print(f"   already there: {output_dir.relative_to(PROJECT_DIR)}")
        return
    TransformersConverter(source, copy_files=copy_files).convert(str(output_dir), quantization="int8")
    print(f"   converted: {output_dir.relative_to(PROJECT_DIR)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-large-v3", action="store_true", help="also download the fallback model large-v3 (~3 GB)")
    args = parser.parse_args()

    print(f"1/4 speech recognition: {ASR_SOURCE} -> CTranslate2 int8 (~1.6 GB download) ...", flush=True)
    convert(ASR_SOURCE, DEFAULT_MODEL_DIR, copy_files=["tokenizer.json", "preprocessor_config.json"])
    print(f"2/4 translation: {NLLB_SOURCE} -> CTranslate2 int8 (~2.5 GB download) ...", flush=True)
    convert(NLLB_SOURCE, NLLB_DIR)
    print("3/4 NLLB tokenizer ...", flush=True)
    transformers.AutoTokenizer.from_pretrained(TOKENIZER_NAME, src_lang=SOURCE_LANG, cache_dir=str(MODELS_DIR))
    print("4/4 speaker model (SpeechBrain ECAPA, ~80 MB) ...", flush=True)
    SpeakerEncoder()
    if args.with_large_v3:
        print("extra: fallback model Whisper large-v3 (~3 GB) ...", flush=True)
        Transcriber("large-v3")
    print(f"done: models are in {MODELS_DIR}. The Silero VAD model is included in the silero-vad package.")


if __name__ == "__main__":
    main()
