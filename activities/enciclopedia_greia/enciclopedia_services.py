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

    Encyclopedia authored scenes are flattened opaque full-screen RGB
    renditions, so they use ``Surface.convert()`` rather than per-pixel-alpha
    conversion. Canonical character sprites keep ``convert_alpha()`` because
    their transparent silhouettes genuinely require it.

    E3 section-world IDs are registered before their generated PNG tranche is
    committed. Missing renditions therefore fail soft to the page's retained
    procedural fallback; a partial generated section pack is forbidden by the
    visual-foundation source contract.
    """

    MAX_SURFACES = 40
    ART_ASSETS = {
        "encyclopedia.home.discovery_book": "home_discovery_book.png",
        "encyclopedia.animals.field_table": "animals_field_table.png",
        "encyclopedia.animals.lion.savanna": "lion_savanna.png",
        "encyclopedia.space.saturn.observatory": "saturn_observatory.png",
        "encyclopedia.machines.gears.workbench": "gears_workbench.png",
        "encyclopedia.history.pyramids.diorama": "pyramids_diorama.png",
        "encyclopedia.space.gallery.observatory": "space_gallery_observatory.png",
        "encyclopedia.earth.gallery.landscape": "earth_gallery_landscape.png",
        "encyclopedia.body.gallery.discovery_room": "body_gallery_discovery_room.png",
        "encyclopedia.machines.gallery.workbench": "machines_gallery_workbench.png",
        "encyclopedia.history.gallery.time_trail": "history_gallery_time_trail.png",
        # E4-D machines entry batch (build group ``e4_machines``).
        "encyclopedia.machines.magnet.lab": "magnet_lab.png",
        "encyclopedia.machines.bicycle.park": "bicycle_park.png",
        "encyclopedia.machines.airplane.sky": "airplane_sky.png",
        "encyclopedia.machines.bridge.river": "bridge_river.png",
        # E4-E history entry batch (build group ``e4_history``).
        "encyclopedia.history.dinosaurs.valley": "dinosaurs_valley.png",
        "encyclopedia.history.fossils.dig_site": "fossils_dig_site.png",
        "encyclopedia.history.mammoth.tundra": "mammoth_tundra.png",
        "encyclopedia.history.cave_paintings.wall": "cave_paintings_wall.png",
        # E4-A organic/nature entry batch (build group ``e4_nature``).
        "encyclopedia.animals.elephant.waterhole": "elephant_waterhole.png",
        "encyclopedia.animals.octopus.reef": "octopus_reef.png",
        "encyclopedia.animals.bee.meadow": "bee_meadow.png",
        "encyclopedia.animals.penguin.ice_shore": "penguin_ice_shore.png",
        "encyclopedia.animals.frog.pond": "frog_pond.png",
        "encyclopedia.earth.volcano.cross_section": "volcano_cross_section.png",
        "encyclopedia.earth.rain.water_cycle": "rain_water_cycle.png",
        "encyclopedia.earth.ocean.depths": "ocean_depths.png",
        "encyclopedia.earth.tree.hillside": "tree_hillside.png",
        "encyclopedia.earth.rainbow.shower": "rainbow_shower.png",
        # E4-B space entry batch (build group ``e4_space``; Saturn stays golden).
        "encyclopedia.space.sun.observatory": "sun_solar_observatory.png",
        "encyclopedia.space.mercury.observatory": "mercury_sunside_observatory.png",
        "encyclopedia.space.venus.observatory": "venus_cloud_observatory.png",
        "encyclopedia.space.earth.observatory": "earth_home_observatory.png",
        "encyclopedia.space.moon.observatory": "moon_night_observatory.png",
        "encyclopedia.space.mars.observatory": "mars_red_observatory.png",
        "encyclopedia.space.jupiter.observatory": "jupiter_giant_observatory.png",
        "encyclopedia.space.uranus.observatory": "uranus_tilted_observatory.png",
        "encyclopedia.space.neptune.observatory": "neptune_windy_observatory.png",
        # E4-C body entry batch (build group ``e4_body``).
        "encyclopedia.body.heart.discovery_room": "heart_discovery_room.png",
        "encyclopedia.body.lungs.discovery_room": "lungs_discovery_room.png",
        "encyclopedia.body.bones.xray_room": "bones_xray_room.png",
        "encyclopedia.body.teeth.dental_room": "teeth_dental_room.png",
        "encyclopedia.body.senses.mirror_room": "senses_mirror_room.png",
    }
    # Small planet sprites — transparent, cached, not full-screen
    PLANET_ASSETS = {
        "earth": "earth_planet_sprite.png",
    }
    # Transparent part sheets for heroes with live moving parts (build tool
    # ``SPRITE_SHEETS``). A page slices the returned sheet once with
    # ``Surface.subsurface``; nothing is decoded or scaled on a frame path.
    SPRITE_SHEETS = {
        "sheet.machines.airplane.parts": "sprites/airplane_parts.png",
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
            source = pygame.image.load(str(self._runtime_root / relative)).convert()
            if size is not None and source.get_size() != size:
                source = pygame.transform.smoothscale(source, size).convert()
            result = source
        except (OSError, RuntimeError, ValueError, pygame.error):
            result = None
        self._remember(key, result)
        return result

    def planet(self, planet_id: str, diameter: int) -> pygame.Surface | None:
        """Small transparent planet sprite, cached, with fallback to procedural."""
        relative = self.PLANET_ASSETS.get(planet_id)
        if relative is None:
            return None
        key = (f"planet:{planet_id}", "planet", int(diameter), 0)
        if key in self._cache:
            result = self._cache.pop(key)
            self._cache[key] = result
            return result
        result: pygame.Surface | None = None
        try:
            source = pygame.image.load(str(self._runtime_root / relative)).convert_alpha()
            if diameter > 0:
                result = pygame.transform.smoothscale(source, (diameter, diameter))
            else:
                result = source
        except (OSError, RuntimeError, ValueError, pygame.error):
            result = None
        self._remember(key, result)
        return result

    def sprite_sheet(self, asset_id: str) -> pygame.Surface | None:
        """Return one prebuilt transparent part sheet, or None to fail soft."""
        relative = self.SPRITE_SHEETS.get(asset_id)
        if relative is None:
            return None
        key = (f"sheet:{asset_id}", "sheet", 0, 0)
        if key in self._cache:
            result = self._cache.pop(key)
            self._cache[key] = result
            return result
        result: pygame.Surface | None = None
        try:
            result = pygame.image.load(str(self._runtime_root / relative)).convert_alpha()
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
