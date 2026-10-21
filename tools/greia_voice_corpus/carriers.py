"""Frozen native spoken-carrier policy for short runtime cues."""
from __future__ import annotations

import unicodedata

from voice_carrier import ALGORITHM_VERSION, GAP_POLICY, spoken_words


CARRIER_MODE = "spoken-short-v1"
PREFIXES = {
    "en": "Listen to this phrase in English.",
    "it": "Ascolta questa frase in italiano.",
    "fr": "Cette phrase est en français.",
    "es": "Escucha esta frase en español.",
}
SPEAKERS = frozenset({"dani", "momo", "tito", "lilli", "leo", "flash"})


def eligible_text(text: str) -> bool:
    """Select at most 3 words, or up to 4 with at most 28 Unicode alnums."""
    words = spoken_words(text)
    letters_digits = sum(ch.isalnum() for ch in unicodedata.normalize("NFC", text))
    return 1 <= len(words) <= 3 or (len(words) == 4 and letters_digits <= 28)


def freeze_row(row: dict, target_verification: str = "required",
               speakers: frozenset[str] = SPEAKERS) -> dict | None:
    """Freeze an exact carrier request for an eligible, still-READY cue."""
    if row.get("state") != "READY" or row.get("request", {}).get("speaker") not in speakers:
        return None
    if target_verification not in {"required", "warn"}:
        raise ValueError("carrier target verification must be required or warn")
    request = row["request"]
    locale, target = request.get("locale"), request.get("text")
    if locale not in PREFIXES or not isinstance(target, str) or not eligible_text(target):
        return None
    return {
        "mode": CARRIER_MODE,
        "prefix": PREFIXES[locale],
        "prefix_word_count": len(spoken_words(PREFIXES[locale])),
        "target": target,
        "target_word_count": len(spoken_words(target)),
        "target_verification": target_verification,
        "composite_text": f"{PREFIXES[locale]} {target}",
        "composite_delivery_prompt": carrier_delivery(request.get("delivery_prompt", ""), locale, row["path"]),
        "normalization": "NFC/casefold/apostrophe-normalized Unicode word tokens; accents preserved",
        "extractor_version": ALGORITHM_VERSION,
        "gap_policy": GAP_POLICY.copy(),
    }


def carrier_delivery(original: str, locale: str, relative_path: str) -> str:
    result = (f"{original.strip()} Speak the first sentence naturally, pause briefly, then "
              "speak the final phrase exactly as written. Do not add any words.")
    directions = {"en": "English", "it": "Italian", "fr": "French", "es": "Spanish"}
    effective = f"Speak in {directions[locale]}. {result}"
    if len(effective) > 300:
        raise ValueError(f"carrier delivery exceeds the VoxStage 300-character limit for {relative_path}")
    return result
