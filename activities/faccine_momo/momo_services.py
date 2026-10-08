"""Typed, renderer-independent Greia progression adapter for Momo."""
from __future__ import annotations

from typing import Protocol

from greia_platform.activity_api import emit_activity_event


class MomoEventPort(Protocol):
    def emotion_discovered(self, emotion: str) -> None: ...
    def all_emotions_explored(self) -> None: ...


class NullMomoEvents:
    """Standalone-preview sink; production composition injects GreiaMomoEvents."""

    def emotion_discovered(self, emotion: str) -> None:
        pass

    def all_emotions_explored(self) -> None:
        pass


class GreiaMomoEvents:
    def emotion_discovered(self, emotion: str) -> None:
        emit_activity_event(
            "faccine_momo.emotion_discovered",
            {"emotion": emotion},
        )

    def all_emotions_explored(self) -> None:
        emit_activity_event("faccine_momo.all_emotions_explored", {})
