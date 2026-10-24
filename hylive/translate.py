"""Armenian -> English translation with Meta NLLB-200 distilled 600M, run by CTranslate2.

Input:  Armenian text (one transcribed phrase).
Output: English text.

The model must be converted once (see README / DECISIONS.md D-016):
    ct2-transformers-converter --model facebook/nllb-200-distilled-600M
        --output_dir models/nllb-200-distilled-600M-ct2-int8 --quantization int8
"""

from pathlib import Path

from hylive.gpu import register_nvidia_dlls

register_nvidia_dlls()  # ctranslate2 may load CUDA libraries; keep the import order the same everywhere
import ctranslate2  # noqa: E402
import transformers  # noqa: E402

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"  # git-ignored
MODEL_DIR = MODELS_DIR / "nllb-200-distilled-600M-ct2-int8"
TOKENIZER_NAME = "facebook/nllb-200-distilled-600M"
SOURCE_LANG = "hye_Armn"  # NLLB code for Armenian
TARGET_LANG = "eng_Latn"  # NLLB code for English


class Translator:
    def __init__(self, device: str = "cpu", compute_type: str = "int8", beam_size: int = 2):
        if not MODEL_DIR.exists():
            raise FileNotFoundError(f"Converted model not found at {MODEL_DIR}. Run the conversion command first.")
        self.beam_size = beam_size
        self.translator = ctranslate2.Translator(str(MODEL_DIR), device=device, compute_type=compute_type)
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
            TOKENIZER_NAME, src_lang=SOURCE_LANG, cache_dir=str(MODELS_DIR))

    def translate(self, text: str) -> str:
        if not text.strip():
            return ""
        source = self.tokenizer.convert_ids_to_tokens(self.tokenizer.encode(text))
        results = self.translator.translate_batch([source], target_prefix=[[TARGET_LANG]], beam_size=self.beam_size)
        target = results[0].hypotheses[0][1:]  # first token is the target language code
        return self.tokenizer.decode(self.tokenizer.convert_tokens_to_ids(target), skip_special_tokens=True)
