"""Split a 16 kHz mono audio stream into spoken phrases with Silero VAD.

Input:  16 kHz mono float32 blocks of any size (from audio_convert).
Output: `Segment` objects, one per phrase.

How it works: Silero's VADIterator looks at 512-sample windows (32 ms) and reports
{'start': n} when speech begins and {'end': n} after `min_silence_ms` of silence.
We keep the audio of the current phrase and cut it out when the phrase ends, or when it
reaches `max_segment_s` (so long monologues still appear within the latency budget).

Note for M5: WASAPI loopback sends no data while nothing plays (DECISIONS.md D-010), so on the
system stream the "end" may never arrive by itself. Not handled yet (mic stream only in M2).
"""

import time
from dataclasses import dataclass

import numpy as np
import torch
from silero_vad import VADIterator, load_silero_vad

SAMPLE_RATE = 16_000
VAD_WINDOW = 512  # Silero VAD requires exactly 512 samples per call at 16 kHz


@dataclass(frozen=True)
class Segment:
    source: str          # "mic" or "system"
    audio: np.ndarray    # 16 kHz mono float32
    start_s: float       # position in the stream (seconds since the stream started)
    end_s: float
    ended_at: float      # clock time when the end was detected (start of the latency measurement)


def load_vad_model():
    return load_silero_vad()


class Segmenter:
    def __init__(self, source: str, model, threshold: float = 0.5, min_silence_ms: int = 500,
                 speech_pad_ms: int = 100, max_segment_s: float = 10.0, preroll_s: float = 0.3):
        self.source = source
        self._vad = VADIterator(model, threshold=threshold, sampling_rate=SAMPLE_RATE,
                                min_silence_duration_ms=min_silence_ms, speech_pad_ms=speech_pad_ms)
        self._max_samples = int(max_segment_s * SAMPLE_RATE)
        # Audio kept before a phrase, so the padding has data to reach back into (at least padding + 0.2 s).
        self._preroll = int(max(preroll_s, speech_pad_ms / 1000 + 0.2) * SAMPLE_RATE)
        self._pending = np.empty(0, dtype=np.float32)  # samples waiting to fill the next 512-window
        self._buffer = np.empty(0, dtype=np.float32)   # recent audio already given to the VAD
        self._buffer_start = 0                          # stream sample index of _buffer[0]
        self._fed = 0                                   # total samples given to the VAD
        self._seg_start = None                          # stream sample index where the phrase started; None = silence

    def process(self, samples: np.ndarray, now: float | None = None) -> list[Segment]:
        """Add audio; return the phrases that ended in it (often an empty list)."""
        now = time.monotonic() if now is None else now
        self._pending = np.concatenate([self._pending, samples.astype(np.float32)])
        segments = []
        while len(self._pending) >= VAD_WINDOW:
            window = self._pending[:VAD_WINDOW]
            self._pending = self._pending[VAD_WINDOW:]
            self._buffer = np.concatenate([self._buffer, window])
            self._fed += VAD_WINDOW

            event = self._vad(torch.from_numpy(window))
            if event and "start" in event:
                self._seg_start = max(event["start"], self._buffer_start)
            elif event and "end" in event:
                end = min(event["end"], self._fed)
                if end > self._seg_start:  # can be <= right after a max-length cut: nothing left to emit
                    segments.append(self._cut(end, now))
                self._seg_start = None

            if self._seg_start is not None and self._fed - self._seg_start >= self._max_samples:
                segments.append(self._cut(self._fed, now))
                self._seg_start = self._fed  # still speaking: the rest becomes the next segment
            self._trim()
        return segments

    def flush(self, now: float | None = None) -> list[Segment]:
        """End of stream: return the unfinished phrase, if any."""
        now = time.monotonic() if now is None else now
        if self._seg_start is None or self._fed <= self._seg_start:
            return []
        segment = self._cut(self._fed, now)
        self._seg_start = None
        return [segment]

    def _cut(self, end: int, now: float) -> Segment:
        audio = self._buffer[self._seg_start - self._buffer_start:end - self._buffer_start].copy()
        return Segment(self.source, audio, self._seg_start / SAMPLE_RATE, end / SAMPLE_RATE, now)

    def _trim(self) -> None:
        """Drop audio we no longer need: keep the current phrase, or only the pre-roll during silence."""
        keep_from = self._seg_start if self._seg_start is not None else self._fed - self._preroll
        drop = keep_from - self._buffer_start
        if drop > 0:
            self._buffer = self._buffer[drop:]
            self._buffer_start = keep_from
