"""Speaker identification for the system-audio side: "Speaker 1", "Speaker 2", ... (milestone M5).

Input:  one phrase as 16 kHz mono float32 audio.
Output: a label that stays the same for the same voice during the session.

How it works:
1. SpeechBrain ECAPA-TDNN turns the phrase into a "voice fingerprint" (192 numbers), on the CPU.
2. Online clustering: the fingerprint is compared (cosine similarity) with the average fingerprint of each
   speaker heard so far. Best match >= threshold -> that speaker (its average is updated);
   otherwise -> a new speaker.
3. Short phrases (< MIN_NEW_SPEAKER_S) give weak fingerprints: they never create a new speaker and do not
   change a speaker's average; they get the closest known speaker.
"""

from pathlib import Path

import numpy as np
import torch
from speechbrain.inference.classifiers import EncoderClassifier
from speechbrain.utils.fetching import LocalStrategy

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"  # git-ignored
MODEL_SOURCE = "speechbrain/spkrec-ecapa-voxceleb"
MIN_NEW_SPEAKER_S = 1.0  # shorter phrases created fake speakers in testing (TESTS.md M5)


class SpeakerEncoder:
    def __init__(self):
        # COPY_SKIP_CACHE: download straight into models/ (the default SYMLINK needs admin rights or Developer Mode
        # on Windows, and the cache would be on C:, see D-004).
        self.model = EncoderClassifier.from_hparams(
            source=MODEL_SOURCE, savedir=str(MODELS_DIR / "spkrec-ecapa-voxceleb"),
            run_opts={"device": "cpu"}, local_strategy=LocalStrategy.COPY_SKIP_CACHE)

    def embed(self, audio: np.ndarray) -> np.ndarray:
        """16 kHz mono audio -> unit-length fingerprint (192 numbers)."""
        with torch.no_grad():
            embedding = self.model.encode_batch(torch.from_numpy(audio.astype(np.float32)).unsqueeze(0))
        vector = embedding.squeeze().numpy()
        return vector / np.linalg.norm(vector)


class SpeakerTracker:
    def __init__(self, threshold: float):
        self.threshold = threshold
        self._sums: list[np.ndarray] = []  # per speaker: sum of its fingerprints (direction = average voice)

    def assign(self, embedding: np.ndarray, duration_s: float) -> tuple[str, float]:
        """Return (label, best similarity to a known speaker; 0.0 for the first speaker)."""
        best, best_sim = None, 0.0
        for i, s in enumerate(self._sums):
            sim = float(np.dot(embedding, s / np.linalg.norm(s)))
            if best is None or sim > best_sim:
                best, best_sim = i, sim
        if best is not None and duration_s < MIN_NEW_SPEAKER_S:
            return f"Speaker {best + 1}", best_sim  # too short to trust: closest speaker, average unchanged
        if best is not None and best_sim >= self.threshold:
            self._sums[best] = self._sums[best] + embedding
            return f"Speaker {best + 1}", best_sim
        self._sums.append(embedding.copy())
        return f"Speaker {len(self._sums)}", best_sim

    @property
    def count(self) -> int:
        return len(self._sums)
