"""Explicit experimental source normalization before carrier extraction."""
from pathlib import Path
import hashlib

from .audio import AudioPipeline

SOURCE_POLICY = "canonical-carrier-pcm22050-v1"


class CarrierSourcePreparation:
    """Prepare bounded mono PCM with the existing audio owner, preserving native bytes.

    This collaborator is intentionally not selected by ShortPhrasePipeline yet.
    Experiments can compare the same provider take at native/canonical rates
    without changing prompts, spending another take or changing a runtime file.
    """

    def __init__(self, audio: AudioPipeline | None = None):
        self.audio = audio or AudioPipeline()
        if self.audio.target_sample_rate_hz != 22050:
            raise ValueError("canonical carrier source requires 22050 Hz")

    def prepare(self, native: Path, destination: Path) -> dict:
        """Return both source identities; never allow the copy to alias the native take."""
        if native.resolve() == destination.resolve() or (destination.exists() and native.samefile(destination)):
            raise ValueError("canonical carrier destination aliases native source")
        original = self.audio.validate_review_wav(native)
        self.audio.package(native, destination)
        prepared = self.audio.validate_review_wav(destination)
        if prepared.sample_rate_hz != 22050 or prepared.channels != 1:
            raise ValueError("canonical carrier source has unexpected PCM format")
        if hashlib.sha256(native.read_bytes()).hexdigest() != original.sha256:
            raise ValueError("native carrier changed during preparation")
        return {"policy": SOURCE_POLICY, "native_path": str(native.resolve()),
                "native_sha256": original.sha256, "native_sample_rate": original.sample_rate_hz,
                "prepared_path": str(destination.resolve()), "prepared_sha256": prepared.sha256,
                "prepared_sample_rate": prepared.sample_rate_hz, "human_review": "PENDING"}
