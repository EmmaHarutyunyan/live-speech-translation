"""Armenian speech recognition with faster-whisper on the GPU.

Input:  one phrase as 16 kHz mono float32 audio (a Segment's audio).
Output: Armenian text (`transcribe`) or text + reliability information (`transcribe_full`).
"""

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from hylive.gpu import register_nvidia_dlls

register_nvidia_dlls()
from faster_whisper import WhisperModel  # noqa: E402  (must be imported after the DLL registration)

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"  # git-ignored
# Default since 2026-10-29: Armenian fine-tuned Whisper large-v3-turbo, converted to CTranslate2 int8 by
# scripts/download_models.py (D-027). "large-v3" stays available as a fallback (--asr-model large-v3).
DEFAULT_MODEL_DIR = MODELS_DIR / "whisper-turbo-armenian-ct2"
DEFAULT_MODEL = str(DEFAULT_MODEL_DIR)
COMPUTE_TYPE = "int8_float32"  # the int8 type CTranslate2 supports on the GTX 1060 (D-002)
# Bounds against repetition loops ("այդ այդ այդ ..."), which took 7-8 s each and blocked the queue (D-020).
MAX_NEW_TOKENS = 128            # far more than 5 s of normal speech needs; a loop stops here
MAX_COMPRESSION_RATIO = 2.4     # Whisper's own threshold: above it, the text is suspiciously repetitive
# Loops the compression ratio missed («… այդ համար այդ համար …», 2026-10-27): long text made of few different words.
MIN_WORDS_FOR_LOOP_CHECK = 8
MIN_UNIQUE_WORD_RATIO = 0.4


def clean_punctuation(text: str) -> str:
    """Remove subtitle-style punctuation that the Armenian turbo model often adds and that confuses NLLB:
    dialog dashes ("- Text", "… - Text"), ellipses, doubled question marks. Hyphens inside words are kept (D-027)."""
    text = re.sub(r"(?:^|(?<=\s))[-–—]\s+", "", text)  # dash + space at the start or after a space
    text = text.replace("…", ".")
    text = re.sub(r"՞{2,}", "՞", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass(frozen=True)
class AsrResult:
    text: str
    compression_ratio: float    # gzip compression ratio of the text (high = repetitive)
    hit_token_limit: bool       # decoding was stopped by MAX_NEW_TOKENS

    @property
    def unique_word_ratio(self) -> float:
        words = self.text.split()
        return len(set(words)) / len(words) if words else 1.0

    @property
    def repetitive(self) -> bool:
        too_few_different_words = (len(self.text.split()) >= MIN_WORDS_FOR_LOOP_CHECK
                                   and self.unique_word_ratio < MIN_UNIQUE_WORD_RATIO)
        return self.compression_ratio > MAX_COMPRESSION_RATIO or too_few_different_words


class Transcriber:
    def __init__(self, model_name: str = DEFAULT_MODEL, beam_size: int = 1, initial_prompt: str | None = None,
                 decode_options: dict | None = None):
        if ("/" in model_name or "\\" in model_name) and not Path(model_name).exists() and model_name.count("/") != 1:
            raise FileNotFoundError(f"ASR model folder not found: {model_name}. Run scripts/download_models.py first.")
        self.model_name = model_name
        self.beam_size = beam_size
        self.decode_options = decode_options or {}  # extra faster-whisper options, used only by tests so far
        self.initial_prompt = initial_prompt  # optional Armenian text given to Whisper as context (M3 test)
        self.model = WhisperModel(model_name, device="cuda", compute_type=COMPUTE_TYPE,
                                  download_root=str(MODELS_DIR))

    def warm_up(self) -> None:
        """The first transcription after loading is slower (D-009); do it before real audio arrives."""
        self.transcribe(np.zeros(16_000, dtype=np.float32))

    def transcribe(self, audio: np.ndarray) -> str:
        return self.transcribe_full(audio).text

    def translate_speech(self, audio: np.ndarray) -> str:
        """English directly from Armenian speech (Whisper's own "translate" task). Test only (translation step 1)."""
        segments, _info = self.model.transcribe(
            audio, language="hy", task="translate", beam_size=self.beam_size, temperature=0.0,
            vad_filter=False, condition_on_previous_text=False, without_timestamps=True,
            max_new_tokens=MAX_NEW_TOKENS)
        return " ".join(s.text.strip() for s in segments).strip()

    def transcribe_full(self, audio: np.ndarray) -> AsrResult:
        segments, _info = self.model.transcribe(
            audio,
            language="hy",
            task="transcribe",
            beam_size=self.beam_size,
            temperature=0.0,                    # one decoding pass, no hidden retries (D-009)
            vad_filter=False,                   # we already cut the phrase with our own VAD (D-014)
            condition_on_previous_text=False,   # each phrase on its own: one bad phrase cannot spoil the next
            without_timestamps=True,            # we only need the text
            initial_prompt=self.initial_prompt,
            max_new_tokens=MAX_NEW_TOKENS,
            **self.decode_options,
        )
        segments = list(segments)  # decoding runs while the segments are read
        return AsrResult(
            # "\ufffd" = half an Armenian character when a phrase is cut in the middle of a word (5 s limit)
            text=clean_punctuation(" ".join(s.text.strip() for s in segments).replace("\ufffd", "")),
            compression_ratio=max((s.compression_ratio for s in segments), default=0.0),
            hit_token_limit=sum(len(s.tokens) for s in segments) >= MAX_NEW_TOKENS - 2,  # approximate
        )
