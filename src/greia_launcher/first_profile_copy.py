"""Localized copy and voice cues for the Shell's first-boot profile setup.

The setup wizard is word-light: every step is carried by Leo's spoken line,
a picture and big controls. On-screen text is a short heading (shown in the
child's capital-letter case policy) plus one small grown-up hint. Spoken
transcripts are the recording source in
``docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/VOICE_LINES_FIRST_BOOT_WIZARD.md``;
this module owns the stable cue ids and the clip paths the Shell resolves.

Speech is prerecorded only (no TTS). A missing clip resolves through
``locale -> base language -> English -> silence`` and never raises.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from greia_platform.localization import LocalizationError, LocaleTag


#: Platform-owned clip folder, relative to the Greia OS root.
FIRST_PROFILE_AUDIO_ROOT = Path("assets/audio/system/first-boot")

#: Stable semantic cue ids (``first_boot.<name>``); the clip is ``<name>.wav``.
FIRST_PROFILE_CUES: tuple[str, ...] = (
    "first_boot.welcome",
    "first_boot.ask_name",
    "first_boot.name_empty",
    "first_boot.ask_avatar",
    "first_boot.ask_age",
    "first_boot.check",
    "first_boot.celebrate",
    "first_boot.try_again",
)

FIRST_PROFILE_LOCALES: tuple[str, ...] = ("en", "it", "es", "fr")


@dataclass(frozen=True, slots=True)
class FirstProfileCopy:
    """Short on-screen text for one locale (headings are pre-case-policy)."""

    welcome: str
    ask_name: str
    ask_avatar: str
    ask_age: str
    check: str
    celebrate: str
    try_again: str
    skip: str
    grown_up_hint: str
    #: Extra letters offered after A-Z on the on-screen keyboard.
    extra_letters: tuple[str, ...]


_COPY: dict[str, FirstProfileCopy] = {
    "en": FirstProfileCopy(
        welcome="Hello!",
        ask_name="What's your name?",
        ask_avatar="Choose your picture",
        ask_age="How old are you?",
        check="Is this you?",
        celebrate="Hooray!",
        try_again="Let's try again",
        skip="Skip",
        grown_up_hint="Grown-ups: this sets up the first child. Add more children later in Parent settings.",
        extra_letters=(),
    ),
    "it": FirstProfileCopy(
        welcome="Ciao!",
        ask_name="Come ti chiami?",
        ask_avatar="Scegli la tua immagine",
        ask_age="Quanti anni hai?",
        check="Sei tu?",
        celebrate="Evviva!",
        try_again="Riproviamo",
        skip="Salta",
        grown_up_hint="Per i grandi: qui si crea il primo bambino. Altri bambini si aggiungono nelle impostazioni genitori.",
        extra_letters=("À", "È", "É", "Ì", "Ò", "Ù"),
    ),
    "es": FirstProfileCopy(
        welcome="¡Hola!",
        ask_name="¿Cómo te llamas?",
        ask_avatar="Elige tu dibujo",
        ask_age="¿Cuántos años tienes?",
        check="¿Eres tú?",
        celebrate="¡Hurra!",
        try_again="Probemos otra vez",
        skip="Saltar",
        grown_up_hint="Para los adultos: aquí se crea el primer niño. Puedes añadir más en los ajustes para padres.",
        extra_letters=("Á", "É", "Í", "Ñ", "Ó", "Ú"),
    ),
    "fr": FirstProfileCopy(
        welcome="Bonjour !",
        ask_name="Comment tu t'appelles ?",
        ask_avatar="Choisis ton image",
        ask_age="Quel âge as-tu ?",
        check="C'est toi ?",
        celebrate="Hourra !",
        try_again="On réessaie",
        skip="Passer",
        grown_up_hint="Pour les parents : ceci crée le premier enfant. Ajoutez-en d'autres dans les réglages parents.",
        extra_letters=("É", "È", "Ë", "Ï", "Ç", "Ô"),
    ),
}


def copy_locale(locale: str | None) -> str:
    """Return the bundle locale for ``locale`` (base language, else English)."""

    raw = (locale or "").strip().replace("_", "-")
    try:
        chain = [tag.value for tag in LocaleTag.parse(raw).fallback_chain()] if raw else []
    except LocalizationError:
        chain = []
    for candidate in chain:
        if candidate in _COPY:
            return candidate
    return "en"


def first_profile_copy(locale: str | None) -> FirstProfileCopy:
    """Resolve the wizard copy for an effective UI locale (never process LANG)."""

    return _COPY[copy_locale(locale)]


def cue_clip_name(cue_id: str) -> str:
    """``first_boot.ask_name`` -> ``ask_name`` (raises for unknown cues)."""

    if cue_id not in FIRST_PROFILE_CUES:
        raise ValueError(f"unknown first-boot cue: {cue_id!r}")
    return cue_id.split(".", 1)[1]


def first_profile_clip(root: Path, cue_id: str, locale: str | None) -> Path | None:
    """Resolve a recorded cue: locale, base language, English, else ``None``."""

    from .spoken_labels import locale_candidates

    name = cue_clip_name(cue_id)
    try:
        candidates = locale_candidates((locale or "en").strip().replace("_", "-") or "en")
    except LocalizationError:
        candidates = locale_candidates("en")
    folder = Path(root) / FIRST_PROFILE_AUDIO_ROOT
    for candidate in candidates:
        path = folder / candidate.value / f"{name}.wav"
        if path.is_file():
            return path
    return None
