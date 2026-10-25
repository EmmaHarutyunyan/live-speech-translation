"""Armenian speech recognition with faster-whisper on the GPU.

Input:  one phrase as 16 kHz mono float32 audio (a Segment's audio).
Output: Armenian text (`transcribe`) or text + reliability information (`transcribe_full`).
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from hylive.gpu import register_nvidia_dlls

register_nvidia_dlls()
from faster_whisper import WhisperModel  # noqa: E402  (must be imported after the DLL registration)

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"  # git-ignored
COMPUTE_TYPE = "int8_float32"  # the int8 type CTranslate2 supports on the GTX 1060 (D-002)
# Bounds against repetition loops ("այդ այդ այդ ..."), which took 7-8 s each and blocked the queue (D-020).
MAX_NEW_TOKENS = 128            # far more than 5 s of normal speech needs; a loop stops here
MAX_COMPRESSION_RATIO = 2.4     # Whisper's own threshold: above it, the text is suspiciously repetitive


@dataclass(frozen=True)
class AsrResult:
    text: str
    compression_ratio: float    # gzip compression ratio of the text (high = repetitive)
    hit_token_limit: bool       # decoding was stopped by MAX_NEW_TOKENS

    @property
    def repetitive(self) -> bool:
        return self.compression_ratio > MAX_COMPRESSION_RATIO


class Transcriber:
    def __init__(self, model_name: str = "small", beam_size: int = 1, initial_prompt: str | None = None):
        self.model_name = model_name
        self.beam_size = beam_size
        self.initial_prompt = initial_prompt  # optional Armenian text given to Whisper as context (M3 test)
        self.model = WhisperModel(model_name, device="cuda", compute_type=COMPUTE_TYPE,
                                  download_root=str(MODELS_DIR))

    def warm_up(self) -> None:
        """The first transcription after loading is slower (D-009); do it before real audio arrives."""
        self.transcribe(np.zeros(16_000, dtype=np.float32))

    def transcribe(self, audio: np.ndarray) -> str:
        return self.transcribe_full(audio).text

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
        )
        segments = list(segments)  # decoding runs while the segments are read
        return AsrResult(
            text=" ".join(s.text.strip() for s in segments).strip(),
            compression_ratio=max((s.compression_ratio for s in segments), default=0.0),
            hit_token_limit=sum(len(s.tokens) for s in segments) >= MAX_NEW_TOKENS - 2,  # approximate
        )
