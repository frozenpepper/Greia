"""Select one canonical VoxCPM2 renderer plus historical opt-in providers."""
from __future__ import annotations
import os

from .providers import ChatterboxMLXProvider, MacOSNativeSpeechProvider, VoiceProvider
from .voxstage_provider import VoxStageProvider
from .voxcpm_provider import VoxCPM2TorchProvider

CHARACTER_PROVIDERS = ("voxcpm2", "voxstage", "chatterbox")


def selected_character_provider(explicit: str | None = None) -> str:
    name = explicit if explicit is not None else os.environ.get("GREIA_VOICE_CHARACTER_PROVIDER", "voxcpm2")
    if name not in CHARACTER_PROVIDERS:
        raise ValueError(f"character provider must be one of {CHARACTER_PROVIDERS}: {name}")
    return name


def build_providers(character_provider: str | None = None) -> tuple[VoiceProvider, ...]:
    """Portable VoxCPM2 is the default on every OS; no substitute TTS per host."""
    factories = {"voxcpm2": VoxCPM2TorchProvider,
                 "voxstage": VoxStageProvider,
                 "chatterbox": ChatterboxMLXProvider}
    return factories[selected_character_provider(character_provider)](), MacOSNativeSpeechProvider()
