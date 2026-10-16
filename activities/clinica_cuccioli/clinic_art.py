"""Prepared, bounded art for Little Vet Clinic.

Everything is loaded and scaled once. The opaque backdrop is the shared vet
corner (``bg.indoor_room.wall_vet_corner`` over ``floor_tile``) with this
package's exam table and the kit tool-tray panel composited on top, so a
frame starts with one blit. Patients come from the shared creature library
(``creature.pet.*`` mood variants, ``creature.woodland.*``); the sponge,
heart, raindrop, FX and Momo come from the shared library too. Only the
stethoscope, towel, medicine, bandage, exam table and the two "it hurts
here" marks are Activity-private (``assets/source/*.svg`` ->
``assets/runtime/*.png``). Drawing code only blits these surfaces.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlPainter, mix

if __package__:
    from .clinic_content import SPECIES, Overlay, Tool
    from .clinic_layout import PATIENT_SIZE, TABLE_ORIGIN, TABLE_SIZE, TRAY_PANEL
else:
    from clinic_content import SPECIES, Overlay, Tool
    from clinic_layout import PATIENT_SIZE, TABLE_ORIGIN, TABLE_SIZE, TRAY_PANEL

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"

# Shared library tools; the rest are private renditions in assets/runtime.
_SHARED_TOOLS: Final[dict[Tool, tuple[str, str]]] = {
    Tool.SPONGE: ("prop.everyday.sponge", "default"),
    Tool.CUDDLE: ("icon.hud.heart", "default"),
}
_PRIVATE_TOOLS: Final[dict[Tool, str]] = {
    Tool.STETHOSCOPE: "stethoscope.png",
    Tool.TOWEL: "towel.png",
    Tool.MEDICINE: "medicine.png",
    Tool.BANDAGE: "bandage.png",
}
TILE_ICON: Final = 76
FLIGHT_ICON: Final = 110
OVERLAY_SIZES: Final[dict[Overlay, int]] = {
    Overlay.THROB: 76,
    Overlay.SWIRL: 88,
    Overlay.WET: 120,
    Overlay.BANDAGE: 52,
}
FX_SIZES: Final[dict[str, int]] = {
    "sparkle": 120,
    "bubble_pop": 130,
    "heart_pop": 120,
    "beat_ring": 96,
    "star_burst": 170,
    "check_pop": 96,
    "ripple": 90,
}
PATIENT_CACHE_LIMIT: Final = 12
HALO: Final = (255, 194, 52)


class ClinicArt:
    """Own every prepared surface the renderer and the tray blit."""

    def __init__(
        self,
        painter: ControlPainter,
        *,
        art: ControlArt | None = None,
        runtime_dir: Path = RUNTIME_DIR,
        size: tuple[int, int] = (1024, 600),
    ) -> None:
        self._painter = painter
        # Content art gets its own bounded cache so it never evicts kit glyphs.
        self._art = art if art is not None else ControlArt(max_entries=48)
        self._runtime_dir = runtime_dir
        self.background = self._compose_background(size)
        self._tool_sources: dict[Tool, pygame.Surface | None] = {tool: self._tool_source(tool) for tool in Tool}
        self.tile_icons: dict[Tool, pygame.Surface | None] = {
            tool: _scaled(source, TILE_ICON) for tool, source in self._tool_sources.items()
        }
        self.flight_icons: dict[Tool, pygame.Surface | None] = {
            tool: _scaled(source, FLIGHT_ICON) for tool, source in self._tool_sources.items()
        }
        self.overlays: dict[Overlay, pygame.Surface | None] = self._build_overlays()
        self.halo = self._build_halo(96)
        self._patients: OrderedDict[tuple[str, str], pygame.Surface | None] = OrderedDict()
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}

    # -- cast / patients -----------------------------------------------------

    def cast_pose(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self._art.image(f"character.{character}", height, variant=variant)

    def patient(self, species_id: str, variant: str) -> pygame.Surface | None:
        """One library creature pose at patient size (bounded LRU)."""

        key = (species_id, variant)
        if key in self._patients:
            self._patients.move_to_end(key)
            return self._patients[key]
        species = SPECIES[species_id]
        image = self._art.image(species.asset_id, PATIENT_SIZE, variant=variant)
        if image is None and variant != "default":
            image = self._art.image(species.asset_id, PATIENT_SIZE)
        self._patients[key] = image
        while len(self._patients) > PATIENT_CACHE_LIMIT:
            self._patients.popitem(last=False)
        return image

    # -- FX -----------------------------------------------------------------

    def fx_frames(self, name: str) -> tuple[pygame.Surface, ...]:
        cached = self._fx.get(name)
        if cached is not None:
            return cached
        size = FX_SIZES.get(name, 120)
        frames = []
        for variant in ("default", "frame_2", "frame_3"):
            image = self._art.image(f"fx.{name}", size, variant=variant)
            if image is not None:
                frames.append(image)
        self._fx[name] = tuple(frames)
        return self._fx[name]

    # -- building -------------------------------------------------------------

    def _tool_source(self, tool: Tool) -> pygame.Surface | None:
        shared = _SHARED_TOOLS.get(tool)
        if shared is not None:
            asset_id, variant = shared
            return self._art.image(asset_id, 256 if asset_id.startswith("prop.") else 96, variant=variant)
        return self._load_private(_PRIVATE_TOOLS[tool])

    def _build_overlays(self) -> dict[Overlay, pygame.Surface | None]:
        overlays: dict[Overlay, pygame.Surface | None] = {
            Overlay.THROB: _scaled(self._load_private("ache_throb.png"), OVERLAY_SIZES[Overlay.THROB]),
            Overlay.SWIRL: _scaled(self._load_private("ache_swirl.png"), OVERLAY_SIZES[Overlay.SWIRL]),
        }
        bandage = self._tool_sources.get(Tool.BANDAGE)
        overlays[Overlay.BANDAGE] = (
            pygame.transform.rotozoom(_scaled(bandage, OVERLAY_SIZES[Overlay.BANDAGE] + 16), 20, 1.0)
            if bandage is not None
            else None
        )
        # Freshly washed fur: three water drops around the body (one surface).
        drop = self._art.image("prop.nature.raindrop", 34)
        size = OVERLAY_SIZES[Overlay.WET]
        wet: pygame.Surface | None = None
        if drop is not None:
            wet = pygame.Surface((size * 2, size), pygame.SRCALPHA)
            for x, y in ((14, 46), (size - 18, 8), (2 * size - 50, 54)):
                wet.blit(drop, (x, y))
        overlays[Overlay.WET] = wet
        return overlays

    def _build_halo(self, size: int) -> pygame.Surface:
        """Soft round glow for "look here" hints (built once)."""

        halo = pygame.Surface((size, size), pygame.SRCALPHA)
        for inset, alpha in ((0, 70), (5, 120), (10, 200)):
            pygame.draw.circle(halo, (*HALO, alpha), (size // 2, size // 2), size // 2 - inset, width=5)
        return halo

    def _load_private(self, name: str) -> pygame.Surface | None:
        try:
            image = pygame.image.load(str(self._runtime_dir / name))
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
        except (OSError, pygame.error):
            return None
        return image

    def _compose_background(self, size: tuple[int, int]) -> pygame.Surface:
        """Vet corner, exam table and tool tray flattened into one opaque surface."""

        surface = pygame.Surface(size)
        surface.fill((217, 242, 208))
        # A throwaway loader: the layers are released once the composite exists.
        loader = ControlArt(max_entries=4)
        for layer in ("bg.indoor_room.wall_vet_corner", "bg.indoor_room.floor_tile"):
            image = loader.image(layer, size)
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        table = self._load_private("exam_table.png")
        if table is not None:
            if table.get_size() != TABLE_SIZE:
                table = pygame.transform.smoothscale(table, TABLE_SIZE)
            surface.blit(table, TABLE_ORIGIN)
        theme = self._painter.theme
        tray = self._painter.body(
            BodyShape.PANEL,
            TRAY_PANEL.size,
            mix(theme.surface, theme.ink, 0.06),
            contour_width=3,
            highlight=False,
        )
        surface.blit(tray, TRAY_PANEL.topleft)
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        return surface


def _scaled(source: pygame.Surface | None, size: int) -> pygame.Surface | None:
    if source is None:
        return None
    if source.get_width() == source.get_height() == size:
        return source
    width, height = source.get_size()
    scale = size / max(width, height)
    return pygame.transform.smoothscale(source, (max(1, round(width * scale)), max(1, round(height * scale))))


__all__ = ["ClinicArt", "FLIGHT_ICON", "TILE_ICON"]
