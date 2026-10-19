"""One composition policy for CLI, warm service and repository producers."""
from __future__ import annotations

import os

from .providers import ChatterboxMLXProvider, MacOSNativeSpeechProvider, UnsupportedNativeSpeechProvider, VoiceProvider
from .voxstage_provider import VoxStageProvider


CHARACTER_PROVIDERS = ("voxstage", "chatterbox")


def selected_character_provider(explicit: str | None = None) -> str:
    """Resolve operator policy once; never silently substitute another voice engine."""
    name = explicit if explicit is not None else os.environ.get("GREIA_VOICE_CHARACTER_PROVIDER", "voxstage")
    if name not in CHARACTER_PROVIDERS:
        raise ValueError(f"character provider must be one of {CHARACTER_PROVIDERS}: {name}")
    return name


def build_providers(character_provider: str | None = None) -> tuple[VoiceProvider, ...]:
    """Select one character renderer plus the independent pedagogical providers."""
    factories = {"voxstage": VoxStageProvider, "chatterbox": ChatterboxMLXProvider}
    character = factories[selected_character_provider(character_provider)]()
    return character, MacOSNativeSpeechProvider(), UnsupportedNativeSpeechProvider()
