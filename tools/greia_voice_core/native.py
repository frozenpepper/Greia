from __future__ import annotations

from dataclasses import dataclass
import re


ITALIAN_PEDAGOGICAL_OVERRIDES: dict[str, str] = {
    "to": "tò", "do": "dò", "no": "nò", "so": "sò", "po": "pò",
    "bo": "bò", "co": "cò", "fo": "fò", "go": "gò", "lo": "lò",
    "mo": "mò", "ro": "rò", "vo": "vò", "zo": "zò", "be": "bè",
    "de": "dè", "fe": "fè", "ge": "gè", "le": "lè", "me": "mè",
    "ne": "nè", "pe": "pè", "re": "rè", "se": "sè", "te": "tè",
    "ve": "vè", "ze": "zè",
}


@dataclass(frozen=True)
class NativeSpeechProfile:
    voice: str
    rate_wpm: int


MACOS_PEDAGOGICAL_PROFILES: dict[str, NativeSpeechProfile] = {
    "it": NativeSpeechProfile(voice="Alice", rate_wpm=175),
    "en": NativeSpeechProfile(voice="Samantha", rate_wpm=180),
}


MACOS_DANI_PROFILES: dict[str, NativeSpeechProfile] = {
    # Keep Dani clearly system-generated. Exact per-host voice may be overridden by
    # GREIA_VOICE_DANI_VOICE_<LANG>; these defaults intentionally stay ordinary and
    # deterministic rather than pretending to be a cloned canonical voice.
    "it": NativeSpeechProfile(voice="Alice", rate_wpm=185),
    "en": NativeSpeechProfile(voice="Samantha", rate_wpm=190),
}


def pedagogical_synthesis_text(text: str, language: str) -> str:
    """Return host synthesis text while preserving the caller's educational target.

    The request/receipt retains the exact pedagogical text. This function contains
    provider-specific pronunciation hints only; they never leak back into Activity
    localization or semantic cue identity.
    """
    lowered = text.strip().lower()
    if language != "it":
        return lowered

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        return ITALIAN_PEDAGOGICAL_OVERRIDES.get(token, token)

    pattern = r"\b(?:" + "|".join(map(re.escape, ITALIAN_PEDAGOGICAL_OVERRIDES)) + r")\b"
    return re.sub(pattern, replace, lowered)
