"""Convert captured audio to the format the models need: 16 kHz, mono, float32 in [-1, 1].

Input: raw 16-bit blocks from `audio_capture` (device rate, e.g. 48 kHz, 1-2 channels).
Output: mono float32 numpy arrays at 16 kHz.
"""

import numpy as np
import soxr

TARGET_RATE = 16_000  # Silero VAD and Whisper expect 16 kHz


def to_float32_frames(data: bytes, channels: int) -> np.ndarray:
    """Raw interleaved int16 bytes -> float32 array of shape (frames, channels), values in [-1, 1]."""
    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    return samples.reshape(-1, channels)


def to_mono(frames: np.ndarray) -> np.ndarray:
    """Average the channels: (frames, channels) -> (frames,)."""
    return frames.mean(axis=1)


class Resampler:
    """Streaming resampler: remembers the end of the previous block, so block edges do not click."""

    def __init__(self, in_rate: int, out_rate: int = TARGET_RATE):
        self._stream = soxr.ResampleStream(in_rate, out_rate, num_channels=1, dtype="float32")

    def process(self, mono: np.ndarray, last: bool = False) -> np.ndarray:
        """Resample one mono block. Pass last=True once, on the final block, to flush what is left."""
        return self._stream.resample_chunk(mono.astype(np.float32), last=last)
