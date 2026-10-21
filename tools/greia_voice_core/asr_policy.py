"""Shared authoring ASR defaults and comparison-only Unicode normalization.

This module never changes a spoken script or downloads weights. Diacritic folding
is deliberately confined to recognition comparisons, with an explicit strict mode.
"""
from pathlib import Path
import unicodedata

DEFAULT_ASR_MODEL = "mlx-community/whisper-base-mlx"
DEFAULT_ASR_REVISION = "1e3e249fb8d01c655324bd6841b1deadffd6d04c"
DEFAULT_ASR_VERIFIER = "mlx-whisper-base"


def comparison_text(text: str, *, ignore_accents: bool = True) -> str:
    """Fold case and, by default, Unicode combining diacritics for ASR only."""
    text = unicodedata.normalize("NFC", text).casefold()
    if ignore_accents:
        text = "".join(c for c in unicodedata.normalize("NFD", text)
                       if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", text)


def cached_asr_model(model_id: str = DEFAULT_ASR_MODEL,
                     revision: str | None = None) -> Path:
    """Resolve installed weights offline, pinning the selected Base default."""
    from huggingface_hub import snapshot_download
    kwargs = {"local_files_only": True, "allow_patterns": ["config.json", "weights.npz", "weights.safetensors"]}
    if revision is not None or model_id == DEFAULT_ASR_MODEL:
        kwargs["revision"] = revision or DEFAULT_ASR_REVISION
    return Path(snapshot_download(model_id, **kwargs))
