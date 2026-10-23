"""Shared authoring ASR defaults and comparison-only Unicode normalization.

This module never changes a spoken script or downloads weights. Diacritic folding
is deliberately confined to recognition comparisons, with an explicit strict mode.
"""
from pathlib import Path
import unicodedata

DEFAULT_ASR_MODEL = "mlx-community/whisper-base-mlx"
DEFAULT_ASR_REVISION = "1e3e249fb8d01c655324bd6841b1deadffd6d04c"
DEFAULT_ASR_VERIFIER = "mlx-whisper-base"

# Current generation uses the multilingual Parakeet-TDT v3 export. Keep the
# historical Whisper identities above intact: saved receipts and frozen corpus
# runs must continue to interpret their original evidence with their original
# recognizer.
DEFAULT_PARAKEET_MODEL = "mlx-community/parakeet-tdt-0.6b-v3"
DEFAULT_PARAKEET_REVISION = "ed2b7e8c15f9aaa0b5772e2efb986255eaef7e15"
DEFAULT_PARAKEET_VERIFIER = "mlx-audio-parakeet-tdt-v3"


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


def cached_parakeet_model() -> Path:
    """Resolve only the selected local Parakeet snapshot; never download at run time."""
    from huggingface_hub import snapshot_download

    path = Path(snapshot_download(
        DEFAULT_PARAKEET_MODEL,
        revision=DEFAULT_PARAKEET_REVISION,
        cache_dir=Path.home() / ".cache" / "huggingface" / "hub",
        local_files_only=True,
        allow_patterns=["config.json", "model.safetensors", "tokenizer.model", "tokenizer.vocab", "vocab.txt"],
    ))
    if not (path / "config.json").is_file() or not (path / "model.safetensors").is_file():
        raise FileNotFoundError(f"incomplete cached Parakeet snapshot: {path}")
    return path
