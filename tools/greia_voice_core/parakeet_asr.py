"""Offline-only Parakeet-TDT v3 transcription through the installed MLX runtime."""
from __future__ import annotations

from dataclasses import dataclass, field
import threading
from pathlib import Path
from typing import Any

from .asr_policy import (
    DEFAULT_PARAKEET_MODEL,
    DEFAULT_PARAKEET_REVISION,
    DEFAULT_PARAKEET_VERIFIER,
    cached_parakeet_model,
)


class ParakeetTranscriptionError(RuntimeError):
    """A local-model or audio-read failure; callers must stop and preserve evidence."""


@dataclass
class ParakeetTranscriber:
    """Own one warm local Parakeet model and serialize its bounded inference calls."""

    model_id: str = DEFAULT_PARAKEET_MODEL
    model_revision: str = DEFAULT_PARAKEET_REVISION
    recognizer_id: str = DEFAULT_PARAKEET_VERIFIER
    _model: Any = field(default=None, init=False, repr=False)
    _model_path: Path | None = field(default=None, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def _load(self) -> Any:
        if self._model is not None:
            return self._model
        if (self.model_id, self.model_revision) != (DEFAULT_PARAKEET_MODEL, DEFAULT_PARAKEET_REVISION):
            raise ParakeetTranscriptionError("only the selected pinned Parakeet v3 model is supported")
        try:
            from mlx_audio.stt.utils import load

            self._model_path = cached_parakeet_model()
            # The HF snapshot basename is the commit hash, not the architecture.
            # Set the known local architecture explicitly; do not edit model files.
            self._model = load(str(self._model_path), model_type="parakeet")
        except Exception as exc:
            raise ParakeetTranscriptionError(f"pinned local Parakeet model unavailable: {exc}") from exc
        return self._model

    def probe(self) -> tuple[bool, str]:
        with self._lock:
            try:
                self._load()
            except ParakeetTranscriptionError as exc:
                return False, str(exc)
        return True, f"{self.model_id}@{self.model_revision}"

    def transcribe(self, wav_path: Path, locale: str | None = None) -> dict[str, Any]:
        """Transcribe audio without expected-text prompting or forced language labels."""
        del locale  # v3 detects among its supported languages; comparison uses request locale.
        with self._lock:
            try:
                model = self._load()
                result = model.generate(str(wav_path))
                transcript = getattr(result, "text", None)
                if not isinstance(transcript, str):
                    raise ValueError("Parakeet returned no text field")
                sentences = getattr(result, "sentences", None)
                segments = []
                if sentences is not None:
                    for sentence in sentences:
                        # MLX Audio Parakeet exposes timestamped aligned tokens,
                        # not Whisper-style word timings. Preserve their actual
                        # text/times without synthesizing pseudo-word boundaries.
                        tokens = getattr(sentence, "tokens", None)
                        if tokens is None:
                            continue
                        segments.append({"tokens": [
                            {"text": getattr(token, "text", ""),
                             "start": getattr(token, "start", None),
                             "end": getattr(token, "end", None)}
                            for token in tokens
                        ]})
                return {"text": transcript.strip(), "segments": segments,
                        "model_id": self.model_id, "model_revision": self.model_revision,
                        "recognizer": self.recognizer_id}
            except Exception as exc:
                if isinstance(exc, ParakeetTranscriptionError):
                    raise
                raise ParakeetTranscriptionError(f"Parakeet transcription failed for {wav_path}: {exc}") from exc
            finally:
                try:
                    import mlx.core as mx
                    mx.clear_cache()
                except Exception:
                    pass

    def __call__(self, wav_path: Path, locale: str | None = None) -> dict[str, Any]:
        return self.transcribe(wav_path, locale)
