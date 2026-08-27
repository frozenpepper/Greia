"""Small shared presentation services for encyclopedia pages."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

import pygame

from greia_platform.activity_api import get_shared_visual_path


@dataclass(frozen=True, slots=True)
class EncyclopediaPalette:
    background: tuple[int, int, int]
    panel: tuple[int, int, int]
    accent: tuple[int, int, int]
    text: tuple[int, int, int]
    cream: tuple[int, int, int] = (255, 250, 239)
    ink: tuple[int, int, int] = (61, 44, 31)

    @classmethod
    def from_theme(cls, theme: object) -> "EncyclopediaPalette":
        return cls(
            background=tuple(getattr(theme, "background", (244, 250, 247))),
            panel=tuple(getattr(theme, "panel", (255, 250, 239))),
            accent=tuple(getattr(theme, "accent", (255, 194, 52))),
            text=tuple(getattr(theme, "text", (61, 44, 31))),
        )


class VisualLibrary:
    """Hard-bounded cache for optional shared Greia character renditions."""

    MAX_SURFACES = 24

    def __init__(self) -> None:
        self._cache: OrderedDict[tuple[str, str, int], pygame.Surface | None] = OrderedDict()

    def character(
        self,
        character_id: str,
        *,
        variant: str = "default",
        height: int = 150,
    ) -> pygame.Surface | None:
        return self._surface(f"character.{character_id}", variant, height)

    def clear(self) -> None:
        self._cache.clear()

    def _surface(
        self,
        asset_id: str,
        variant: str,
        height: int,
    ) -> pygame.Surface | None:
        key = (asset_id, variant, int(height))
        if key in self._cache:
            result = self._cache.pop(key)
            self._cache[key] = result
            return result
        result: pygame.Surface | None = None
        try:
            path = get_shared_visual_path(asset_id, variant=variant)
            source = pygame.image.load(str(path)).convert_alpha()
            if source.get_height() > 0:
                width = max(1, round(source.get_width() * height / source.get_height()))
                result = pygame.transform.smoothscale(source, (width, height))
        except (OSError, RuntimeError, ValueError, pygame.error):
            result = None
        self._cache[key] = result
        while len(self._cache) > self.MAX_SURFACES:
            self._cache.popitem(last=False)
        return result
