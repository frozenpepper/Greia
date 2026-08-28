"""Small shared presentation services for encyclopedia pages."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import pygame

from greia_platform.activity_api import get_shared_visual_path
from greia_platform.typography import FontRole, GreiaTypography


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


class CachedEncyclopediaTypography(GreiaTypography):
    """Greia typography with a hard-bounded cache for repeated static lines."""

    MAX_TEXT_SURFACES = 160

    def __init__(self) -> None:
        super().__init__()
        self._text_surfaces: OrderedDict[
            tuple[str, FontRole, int, tuple[int, ...]], pygame.Surface
        ] = OrderedDict()

    def render(
        self,
        text: str,
        role: FontRole,
        size: int,
        color: tuple[int, int, int] | tuple[int, int, int, int],
    ) -> pygame.Surface:
        key = (text, role, int(size), tuple(int(channel) for channel in color))
        cached = self._text_surfaces.pop(key, None)
        if cached is not None:
            self._text_surfaces[key] = cached
            return cached
        surface = super().render(text, role, size, color)
        self._text_surfaces[key] = surface
        while len(self._text_surfaces) > self.MAX_TEXT_SURFACES:
            self._text_surfaces.popitem(last=False)
        return surface

    def clear(self) -> None:
        self._text_surfaces.clear()
        super().clear()


class VisualLibrary:
    """Bounded cache for shared characters and package-local authored art.

    Runtime art is an explicit semantic-id map; the Activity never scans the
    package or rasterizes SVG at runtime. Scaling happens only on a bounded
    cache miss and page hot paths only receive prepared Surfaces.
    """

    MAX_SURFACES = 40
    ART_ASSETS = {
        "encyclopedia.home.discovery_book": "home_discovery_book.png",
        "encyclopedia.animals.field_table": "animals_field_table.png",
        "encyclopedia.animals.lion.savanna": "lion_savanna.png",
        "encyclopedia.space.saturn.observatory": "saturn_observatory.png",
        "encyclopedia.machines.gears.workbench": "gears_workbench.png",
        "encyclopedia.history.pyramids.diorama": "pyramids_diorama.png",
    }

    def __init__(self, package_root: Path) -> None:
        self._runtime_root = package_root / "assets" / "runtime"
        self._cache: OrderedDict[
            tuple[str, str, int, int], pygame.Surface | None
        ] = OrderedDict()

    def character(
        self,
        character_id: str,
        *,
        variant: str = "default",
        height: int = 150,
    ) -> pygame.Surface | None:
        return self._shared_character(f"character.{character_id}", variant, height)

    def art(
        self,
        asset_id: str,
        *,
        size: tuple[int, int] | None = None,
    ) -> pygame.Surface | None:
        relative = self.ART_ASSETS.get(asset_id)
        if relative is None:
            return None
        width, height = size or (0, 0)
        key = (f"art:{asset_id}", "runtime", int(width), int(height))
        if key in self._cache:
            result = self._cache.pop(key)
            self._cache[key] = result
            return result

        result: pygame.Surface | None = None
        try:
            source = pygame.image.load(str(self._runtime_root / relative)).convert_alpha()
            if size is not None and source.get_size() != size:
                source = pygame.transform.smoothscale(source, size)
            result = source
        except (OSError, RuntimeError, ValueError, pygame.error):
            result = None
        self._remember(key, result)
        return result

    def clear(self) -> None:
        self._cache.clear()

    def _shared_character(
        self,
        asset_id: str,
        variant: str,
        height: int,
    ) -> pygame.Surface | None:
        key = (asset_id, variant, 0, int(height))
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
        self._remember(key, result)
        return result

    def _remember(
        self,
        key: tuple[str, str, int, int],
        result: pygame.Surface | None,
    ) -> None:
        self._cache[key] = result
        while len(self._cache) > self.MAX_SURFACES:
            self._cache.popitem(last=False)
