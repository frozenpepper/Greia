"""Same NVIDIA Parakeet-TDT 0.6B v3 model on macOS, Windows and Linux.

onnx-asr is the portable inference runtime. Setup downloads the model once;
doctor/generation/review cannot trigger network downloads.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import os
import threading
from typing import Any

from .paths import voice_home


@dataclass
class OnnxParakeetTranscriber:
    model_id: str = "nvidia/parakeet-tdt-0.6b-v3"
    model_revision: str = "istupakov/parakeet-tdt-0.6b-v3-onnx"
    recognizer_id: str = "onnx-asr-parakeet-tdt-v3"
    _model: Any = field(default=None, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    @staticmethod
    def model_path() -> Path:
        return Path(os.environ.get("GREIA_PARAKEET_MODEL_DIR") or
                    (voice_home() / "models" / "parakeet-tdt-v3")).expanduser()

    def _load(self):
        if self._model is not None:
            return self._model
        directory = self.model_path()
        # onnx_asr.load_model creates/downloads if the folder is missing.
        # Guard it BEFORE calling, including inside doctor.
        if not directory.is_dir() or not any(directory.rglob("*.onnx")):
            raise FileNotFoundError(
                f"Parakeet-TDT v3 ONNX files are absent at {directory}; run setup_voice_models.py")
        import onnx_asr
        self._model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v3", str(directory))
        return self._model

    def probe(self) -> tuple[bool, str]:
        with self._lock:
            try:
                self._load()
            except Exception as exc:
                return False, f"Parakeet v3 not ready: {exc}"
        return True, f"{self.model_id} ({self.model_revision})"

    def transcribe(self, wav_path: Path, locale: str | None = None) -> dict[str, Any]:
        del locale  # multilingual model recognizes the recording
        with self._lock:
            try:
                result = self._load().recognize(str(wav_path))
                transcript = result if isinstance(result, str) else getattr(result, "text", None)
                if not isinstance(transcript, str):
                    raise ValueError("Parakeet returned no transcript text")
                return {
                    "text": transcript.strip(), "segments": [],
                    "model_id": self.model_id, "model_revision": self.model_revision,
                    "recognizer": self.recognizer_id,
                }
            except Exception as exc:
                raise RuntimeError(f"Parakeet ONNX transcription failed: {exc}") from exc

    def __call__(self, wav_path: Path, locale: str | None = None):
        return self.transcribe(wav_path, locale)
