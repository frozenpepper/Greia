"""Bounded art cache for Il Viaggio del Delfino.

Art comes from the shared Greia library, resolved semantically:

- the scene: ``bg.sea_surface.{sky,far,sea}`` above the water and
  ``bg.underwater.{water,far,mid,ground,foreground}`` below it, baked once per
  journey into a few horizontally periodic parallax strips (each layer is
  tiled with its mirror image, so seams never show);
- the hero and the sea friends: ``creature.marine.*`` (swim / happy);
- landmarks (``prop.vocab.lighthouse``, ``prop.vocab.island``,
  ``prop.everyday.shell``) and feedback flipbooks (``fx.*``).

Two small Activity-private renditions live under ``assets/runtime`` (the
pearl and the finish arch; SVG sources beside them under ``assets/source``).

One owner decodes, crops, tints, scales and rotates; drawing only ever blits.
Scene sources are decoded only while baking and released afterwards; sprites
live in a hard-capped LRU so a long session on the Acer floor never grows.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

import pygame

from greia_platform.pygame_blit import prepare_static

try:
    from delfino_content import JOURNEYS, REFERENCE_HEIGHT, REFERENCE_WIDTH, SURFACE_Y, JourneySpec
except ImportError:  # repository/package import context
    from .delfino_content import JOURNEYS, REFERENCE_HEIGHT, REFERENCE_WIDTH, SURFACE_Y, JourneySpec

VisualResolver = Callable[[str, str], Path]

ASSETS_DIR: Final = Path(__file__).resolve().parent / "assets" / "runtime"

#: Horizon row of the shared sea-surface layers (sky / far / sea).
_SEA_HORIZON: Final = 334
#: Rows of the sea layer used as the moving water-surface band.
_SURFACE_BAND: Final = (-6, 34)

#: Hero dolphin box and pitch buckets (degrees, quantized).
DOLPHIN_BOX: Final = (196, 98)
ANGLE_STEP: Final = 6
MAX_ANGLE: Final = 30

#: Finish arch on screen (scaled once from the 512x256 master).
ARCH_SIZE: Final = (720, 360)

#: Landmark sizes drawn at each finish (kept in step with the renderer).
_LANDMARK_BOXES: Final = (
    ("prop.vocab.lighthouse", (150, 168)),
    ("prop.vocab.island", (330, 230)),
    ("prop.everyday.shell", (150, 130)),
)

#: Camera used for still pictures of a scene (lighthouse clear of the sun).
_POSTCARD_CAMERA: Final = 2600.0

_MAX_SPRITES: Final = 96
_MAX_FX: Final = 16


@dataclass(frozen=True, slots=True)
class SceneLook:
    """Per-journey treatment of the shared scene kit (baked once).

    ``golden_sky`` replaces the day sky with a warm theme-token gradient plus
    the shared ``prop.nature.sun`` / ``prop.nature.cloud`` props.
    """

    deep_tint: tuple[int, int, int] | None = None
    #: Family water: the Sea folder's deep saturated ocean gradient (shared
    #: with Orca Bay / Aquarium) under the shared layer's light rays.
    family_water: bool = False
    deep_lift: tuple[int, int, int] | None = None
    golden_sky: bool = False
    dense_mid: bool = False


LOOKS: Final[dict[str, SceneLook]] = {
    # Sunny bay: the shared kit as authored.
    "bay": SceneLook(family_water=True),
    # Coral reef: deeper blue water and twice the coral.
    "reef": SceneLook(family_water=True, dense_mid=True),
    # Golden-hour lagoon: bright turquoise water under a warm sky.
    "lagoon": SceneLook(deep_tint=(190, 255, 236), deep_lift=(22, 50, 40), golden_sky=True),
}

#: Theme tokens for the golden-hour sky (lavender top, peach, warm horizon).
_GOLDEN_SKY: Final = ((214, 200, 240), (248, 216, 189), (255, 236, 196))
#: Sea-folder family water (Orca Bay's day water, RGB top → bottom).
FAMILY_WATER: Final = ((2, 132, 199), (3, 105, 161))
#: How strongly the shared water layer's light rays show on family water.
_RAY_STRENGTH: Final = (150, 150, 150)
#: The far reef silhouette, deepened into the same blue family.
_FAMILY_REEF_TINT: Final = (96, 150, 214)
#: Mid corals and sand sit a little lower so the swimming band stays open.
_GROUND_DROP: Final = 26


@dataclass(slots=True)
class ParallaxStrip:
    """A horizontally periodic strip drawn at ``y`` and scrolled by ``factor``."""

    surface: pygame.Surface
    y: int
    factor: float

    def __post_init__(self) -> None:
        # Alpha bands are blitted every frame: SDL RLE makes a full-width
        # band ~2 ms instead of ~130 ms on the Atom (greia_platform.pygame_blit).
        if self.surface.get_flags() & pygame.SRCALPHA:
            self.surface = prepare_static(self.surface)

    def draw(self, target: pygame.Surface, camera_x: float, *, offset: float = 0.0) -> None:
        width = self.surface.get_width()
        x = -int(camera_x * self.factor + offset) % width
        target.blit(self.surface, (x - width, self.y))
        if x < REFERENCE_WIDTH:
            target.blit(self.surface, (x, self.y))


@dataclass(slots=True)
class SceneLayers:
    """Baked layers of one journey look, back to front."""

    sky: pygame.Surface
    back: tuple[ParallaxStrip, ...]
    front: tuple[ParallaxStrip, ...]

    def draw_back(self, target: pygame.Surface, camera_x: float) -> None:
        target.blit(self.sky, (0, 0))
        for strip in self.back:
            strip.draw(target, camera_x)

    def draw_front(self, target: pygame.Surface, camera_x: float) -> None:
        for strip in self.front:
            strip.draw(target, camera_x)


def _default_resolver(asset_id: str, variant: str) -> Path:
    from greia_platform.activity_api import get_shared_visual_path

    return get_shared_visual_path(asset_id, variant=variant)


def _convert(image: pygame.Surface, *, alpha: bool = True) -> pygame.Surface:
    if pygame.display.get_surface() is not None:
        try:
            return image.convert_alpha() if alpha else image.convert()
        except pygame.error:
            return image
    return image


def fit_size(size: tuple[int, int], box: tuple[int, int]) -> tuple[int, int]:
    width, height = size
    scale = min(box[0] / max(1, width), box[1] / max(1, height))
    return max(1, round(width * scale)), max(1, round(height * scale))


def quantize_angle(angle: float) -> int:
    clamped = max(-MAX_ANGLE, min(MAX_ANGLE, float(angle)))
    return int(round(clamped / ANGLE_STEP) * ANGLE_STEP)


def _paint_gradient(surface: pygame.Surface, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> None:
    width, height = surface.get_size()
    for row in range(height):
        t = row / max(1, height - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        pygame.draw.line(surface, color, (0, row), (width, row))


def _highlights(band: pygame.Surface) -> pygame.Surface:
    """Only what is brighter than each row's average (light rays, bubbles)."""

    width, height = band.get_size()
    opaque = pygame.Surface((width, height))
    opaque.blit(band, (0, 0))
    average = pygame.Surface((width, height))
    for row in range(height):
        color = pygame.transform.average_color(opaque, pygame.Rect(0, row, width, 1))[:3]
        pygame.draw.line(average, color, (0, row), (width, row))
    opaque.blit(average, (0, 0), special_flags=pygame.BLEND_RGB_SUB)
    opaque.fill(_RAY_STRENGTH, special_flags=pygame.BLEND_RGB_MULT)
    return opaque


def _mirror_tile(layer: pygame.Surface) -> pygame.Surface:
    """Layer + its mirror image: a strip that repeats without a seam."""

    width, height = layer.get_size()
    strip = pygame.Surface((width * 2, height), pygame.SRCALPHA)
    strip.blit(layer, (0, 0))
    strip.blit(pygame.transform.flip(layer, True, False), (width, 0))
    return strip


def _band(layer: pygame.Surface, min_alpha: int = 6) -> tuple[pygame.Surface, int] | None:
    """Crop a full-frame layer to its visible rows; return (band, top row)."""

    rect = layer.get_bounding_rect(min_alpha=min_alpha)
    if rect.height <= 0:
        return None
    rows = pygame.Rect(0, rect.top, layer.get_width(), rect.height)
    return layer.subsurface(rows).copy(), rect.top


class DelfinoArt:
    """Owner of every decoded/baked surface the Dolphin's Journey draws."""

    def __init__(self, resolver: VisualResolver | None = None, assets_dir: Path = ASSETS_DIR) -> None:
        self._resolver = resolver if resolver is not None else _default_resolver
        self._assets_dir = assets_dir
        self._sprites: OrderedDict[tuple, Optional[pygame.Surface]] = OrderedDict()
        self._decoded: dict[tuple[str, str], Optional[pygame.Surface]] = {}
        self._layer_sources: dict[str, Optional[pygame.Surface]] = {}
        self._scene: tuple[str, SceneLayers] | None = None
        self._thumbs: dict[tuple[str, tuple[int, int]], pygame.Surface] = {}
        self._fx: OrderedDict[tuple[str, int], list[pygame.Surface]] = OrderedDict()
        self._backdrop: pygame.Surface | None = None
        # Baked scenes shared by the picker thumbnails and backdrop while
        # warm_thumbnails runs (the bay was baked twice); None otherwise.
        self._warm_scenes: dict[str, SceneLayers] | None = None

    # -- decoding ----------------------------------------------------------

    def _load(self, path: Path) -> Optional[pygame.Surface]:
        try:
            return _convert(pygame.image.load(str(path)))
        except Exception:
            return None

    def shared(self, asset_id: str, variant: str = "default") -> Optional[pygame.Surface]:
        """Decoded sprite-sized shared art (kept; the set is fixed and small)."""

        key = (asset_id, variant)
        if key not in self._decoded:
            try:
                path = self._resolver(asset_id, variant)
            except Exception:
                path = None
            self._decoded[key] = self._load(path) if path is not None else None
        return self._decoded[key]

    def private(self, stem: str) -> Optional[pygame.Surface]:
        key = ("private", stem)
        if key not in self._decoded:
            self._decoded[key] = self._load(self._assets_dir / f"{stem}.png")
        return self._decoded[key]

    def _layer(self, asset_id: str) -> Optional[pygame.Surface]:
        """Full-frame scene layer, decoded only while baking."""

        if asset_id not in self._layer_sources:
            try:
                path = self._resolver(asset_id, "default")
            except Exception:
                path = None
            self._layer_sources[asset_id] = self._load(path) if path is not None else None
        return self._layer_sources[asset_id]

    def release_sources(self) -> None:
        """Drop decoded full-frame scene sources after baking."""

        self._layer_sources.clear()

    # -- bounded sprite cache ---------------------------------------------

    def _cached(self, key: tuple, build: Callable[[], Optional[pygame.Surface]]) -> Optional[pygame.Surface]:
        if key in self._sprites:
            self._sprites.move_to_end(key)
            return self._sprites[key]
        surface = build()
        if surface is not None:
            surface = prepare_static(surface)  # blitted per frame: RLE (pygame_blit)
        self._sprites[key] = surface
        while len(self._sprites) > _MAX_SPRITES:
            self._sprites.popitem(last=False)
        return surface

    @property
    def sprite_count(self) -> int:
        return len(self._sprites)

    def fitted(self, source: Optional[pygame.Surface], box: tuple[int, int]) -> Optional[pygame.Surface]:
        if source is None:
            return None
        crop = source.get_bounding_rect(min_alpha=8)
        if crop.width <= 0 or crop.height <= 0:
            return None
        return pygame.transform.smoothscale(source.subsurface(crop), fit_size(crop.size, box))

    def creature(
        self,
        visual: str,
        box: tuple[int, int],
        *,
        happy: bool = False,
        facing_right: bool = True,
    ) -> Optional[pygame.Surface]:
        """A shared creature fitted in ``box`` (cropped with one union rect)."""

        variant = "happy" if happy else "default"

        def build() -> Optional[pygame.Surface]:
            source = self.shared(visual, variant) or self.shared(visual)
            if source is None:
                return None
            crop = self._union_crop(visual)
            image = pygame.transform.smoothscale(source.subsurface(crop), fit_size(crop.size, box))
            return image if facing_right else pygame.transform.flip(image, True, False)

        return self._cached(("creature", visual, box, variant, facing_right), build)

    def _union_crop(self, visual: str) -> pygame.Rect:
        """One crop for both variants so swapping the face never jumps."""

        rect: pygame.Rect | None = None
        for variant in ("default", "happy"):
            image = self.shared(visual, variant)
            if image is None:
                continue
            bounds = image.get_bounding_rect(min_alpha=8)
            rect = bounds if rect is None else rect.union(bounds)
        return rect if rect is not None else pygame.Rect(0, 0, 1, 1)

    def dolphin(self, angle: float, *, happy: bool = False) -> Optional[pygame.Surface]:
        """The hero (shared dolphin art) pitched to a quantized angle."""

        quant = quantize_angle(angle)

        def build() -> Optional[pygame.Surface]:
            upright = self.creature("creature.marine.dolphin", DOLPHIN_BOX, happy=happy)
            if upright is None:
                return None
            return upright if quant == 0 else pygame.transform.rotozoom(upright, quant, 1.0)

        return self._cached(("dolphin", quant, happy), build)

    def warm_dolphin(self) -> None:
        """Bake every pitch bucket up front (no rotation during play)."""

        for happy in (False, True):
            for angle in range(-MAX_ANGLE, MAX_ANGLE + 1, ANGLE_STEP):
                self.dolphin(angle, happy=happy)

    def dolphin_mini(self, angle: float) -> Optional[pygame.Surface]:
        """Small tilted dolphin for the wordless leap hint (quantized, cached)."""

        quant = quantize_angle(angle)

        def build() -> Optional[pygame.Surface]:
            upright = self.creature("creature.marine.dolphin", (76, 38))
            if upright is None:
                return None
            return upright if quant == 0 else pygame.transform.rotozoom(upright, quant, 1.0)

        return self._cached(("dolphin_mini", quant), build)

    def jelly(self, *, happy: bool) -> Optional[pygame.Surface]:
        return self.creature("creature.marine.jellyfish", (78, 98), happy=happy)

    def pearl(self, size: int) -> Optional[pygame.Surface]:
        return self._cached(("pearl", size), lambda: self.fitted(self.private("pearl"), (size, size)))

    def finish_arch(self) -> Optional[pygame.Surface]:
        def build() -> Optional[pygame.Surface]:
            source = self.private("finish_arch")
            return pygame.transform.smoothscale(source, ARCH_SIZE) if source is not None else None

        return self._cached(("arch",), build)

    def prop(self, asset_id: str, box: tuple[int, int]) -> Optional[pygame.Surface]:
        return self._cached(("prop", asset_id, box), lambda: self.fitted(self.shared(asset_id), box))

    def fx_frames(self, fx_id: str, size: int) -> list[pygame.Surface]:
        """Shared ``fx.<id>`` flipbook frames at ``size`` (bounded cache)."""

        key = (fx_id, size)
        if key in self._fx:
            self._fx.move_to_end(key)
            return self._fx[key]
        frames: list[pygame.Surface] = []
        for variant in ("default", "frame_2", "frame_3"):
            image = self.shared(f"fx.{fx_id}", variant)
            if image is not None:
                frames.append(prepare_static(pygame.transform.smoothscale(image, (size, size))))
        self._fx[key] = frames
        while len(self._fx) > _MAX_FX:
            self._fx.popitem(last=False)
        return frames

    # -- scene ---------------------------------------------------------------

    def scene(self, look: str) -> SceneLayers:
        """Baked layers for ``look``; only the current journey's are kept."""

        if self._scene is not None and self._scene[0] == look:
            return self._scene[1]
        self._scene = None
        layers = self._bake_scene(LOOKS.get(look, SceneLook()))
        self.release_sources()
        self._scene = (look, layers)
        return layers

    def _bake_scene(self, look: SceneLook) -> SceneLayers:
        surface_y = int(SURFACE_Y)
        shift = surface_y - _SEA_HORIZON

        # Sky: the upper rows of the shared sky (sun and clouds), opaque.
        sky = pygame.Surface((REFERENCE_WIDTH, surface_y + _SURFACE_BAND[1]))
        source_sky = self._layer("bg.sea_surface.sky")
        if look.golden_sky:
            self._paint_golden_sky(sky)
        elif source_sky is not None:
            sky.blit(source_sky, (0, 0))
        else:
            sky.fill((186, 226, 247))
        sky = _convert(sky, alpha=False)

        back: list[ParallaxStrip] = []
        far = self._layer("bg.sea_surface.far")
        if far is not None:
            banded = _band(far)
            if banded is not None:
                band, top = banded
                if look.golden_sky:
                    band.fill((255, 226, 206, 255), special_flags=pygame.BLEND_RGBA_MULT)
                # One copy per period (not mirrored): the far islands and
                # lighthouse must not appear twice side by side.
                strip = pygame.Surface((band.get_width() * 2, band.get_height()), pygame.SRCALPHA)
                strip.blit(band, (0, 0))
                back.append(ParallaxStrip(_convert(strip), top + shift, 0.12))

        # Deep water: the underwater water + far reef, below the surface.
        deep = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT - surface_y))
        water = self._layer("bg.underwater.water")
        if look.family_water:
            _paint_gradient(deep, *FAMILY_WATER)
            if water is not None:
                rays = water.subsurface(pygame.Rect(0, surface_y, REFERENCE_WIDTH, deep.get_height())).copy()
                deep.blit(_highlights(rays), (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        elif water is not None:
            deep.blit(water, (0, -surface_y))
        else:
            deep.fill((52, 140, 196))
        reef = self._layer("bg.underwater.far")
        if reef is not None:
            if look.family_water:
                reef = reef.copy()
                reef.fill(_FAMILY_REEF_TINT + (255,), special_flags=pygame.BLEND_RGBA_MULT)
            deep.blit(reef, (0, -surface_y))
        if look.deep_tint is not None:
            deep.fill(look.deep_tint, special_flags=pygame.BLEND_RGB_MULT)
        if look.deep_lift is not None:
            deep.fill(look.deep_lift, special_flags=pygame.BLEND_RGB_ADD)
        deep_strip = pygame.Surface((REFERENCE_WIDTH * 2, deep.get_height()))
        deep_strip.blit(deep, (0, 0))
        deep_strip.blit(pygame.transform.flip(deep, True, False), (REFERENCE_WIDTH, 0))
        back.append(ParallaxStrip(_convert(deep_strip, alpha=False), surface_y, 0.3))

        for asset_id, factor in (
            ("bg.underwater.mid", 0.62),
            ("bg.underwater.foreground", 0.8),
            ("bg.underwater.ground", 1.0),
        ):
            layer = self._layer(asset_id)
            banded = _band(layer) if layer is not None else None
            if banded is None:
                continue
            band, top = banded
            if look.deep_tint is not None and asset_id.endswith("mid"):
                band.fill(look.deep_tint + (255,), special_flags=pygame.BLEND_RGBA_MULT)
            strip = _mirror_tile(band)
            if look.dense_mid and asset_id.endswith("mid"):
                # A second, offset copy of the corals fills the reef.
                width = strip.get_width()
                dense = strip.copy()
                dense.blit(strip, (width // 4, 0))
                dense.blit(strip, (width // 4 - width, 0))
                strip = dense
            back.append(ParallaxStrip(_convert(strip), top + _GROUND_DROP, factor))

        # Water surface band (wavelets) from the shared sea layer.
        sea = self._layer("bg.sea_surface.sea")
        if sea is not None:
            top_row = _SEA_HORIZON + _SURFACE_BAND[0]
            rows = pygame.Rect(0, top_row, sea.get_width(), _SURFACE_BAND[1] - _SURFACE_BAND[0])
            band = sea.subsurface(rows.clip(sea.get_rect())).copy()
            fade = pygame.Surface(band.get_size(), pygame.SRCALPHA)
            height = band.get_height()
            for row in range(height):
                # Opaque at the waterline, fading into the water below.
                alpha = 255 if row < height // 3 else int(255 * (1.0 - (row - height // 3) / (height * 2 / 3)))
                pygame.draw.line(fade, (255, 255, 255, max(0, alpha)), (0, row), (band.get_width(), row))
            band = band.convert_alpha() if pygame.display.get_surface() is not None else band
            band.blit(fade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            back.append(ParallaxStrip(_convert(_mirror_tile(band)), surface_y + _SURFACE_BAND[0], 1.0))

        # Nothing is drawn over the action: pearls and friends must never
        # hide behind scenery for a pre-reader.
        return SceneLayers(sky, tuple(back), ())

    def _paint_golden_sky(self, sky: pygame.Surface) -> None:
        width, height = sky.get_size()
        top, middle, horizon = _GOLDEN_SKY
        for row in range(height):
            t = row / max(1, height - 1)
            a, b, u = (top, middle, t / 0.55) if t < 0.55 else (middle, horizon, (t - 0.55) / 0.45)
            color = tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3))
            pygame.draw.line(sky, color, (0, row), (width, row))
        sun = self.fitted(self.shared("prop.nature.sun"), (104, 104))
        if sun is not None:
            sky.blit(sun, sun.get_rect(center=(880, 70)))
        cloud = self.fitted(self.shared("prop.nature.cloud"), (120, 64))
        if cloud is not None:
            sky.blit(cloud, cloud.get_rect(center=(250, 58)))
            small = pygame.transform.smoothscale(cloud, (cloud.get_width() * 2 // 3, cloud.get_height() * 2 // 3))
            sky.blit(small, small.get_rect(center=(600, 34)))

    def thumbnail(self, spec: JourneySpec, size: tuple[int, int]) -> pygame.Surface:
        """Picture of one journey for the picker card (built once)."""

        key = (spec.journey_id, size)
        cached = self._thumbs.get(key)
        if cached is not None:
            return cached
        scene = self._postcard_scene(spec.look)
        frame = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        scene.draw_back(frame, _POSTCARD_CAMERA)
        # The bay's far layer already shows its lighthouse.
        if spec.landmark is not None and spec.landmark != "prop.vocab.lighthouse":
            landmark = self.prop(spec.landmark, (300, 250))
            if landmark is not None:
                bottom = 560 if spec.look == "reef" else int(SURFACE_Y) + 50
                frame.blit(landmark, landmark.get_rect(midbottom=(820, bottom)))
        for index, friend in enumerate(spec.friends):
            box = (int(friend.box[0] * 1.6), int(friend.box[1] * 1.6))
            sprite = self.creature(friend.visual, box, facing_right=False)
            if sprite is not None:
                frame.blit(sprite, sprite.get_rect(center=(300 + index * 300, 350 + (index % 2) * 90)))
        thumb = pygame.transform.smoothscale(frame, size)
        mask = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=max(8, size[1] // 9))
        rounded = pygame.Surface(size, pygame.SRCALPHA)
        rounded.blit(thumb, (0, 0))
        rounded.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        thumb = _convert(rounded)
        self._thumbs[key] = thumb
        return thumb

    def warm_journey(self, spec: JourneySpec, fx: tuple[tuple[str, int], ...] = ()) -> None:
        """Prepare everything one journey draws before its first frame."""

        self.scene(spec.look)
        for friend in spec.friends:
            for happy, facing in ((False, False), (True, True)):
                self.creature(friend.visual, friend.box, happy=happy, facing_right=facing)
        self.jelly(happy=False)
        self.jelly(happy=True)
        self.finish_arch()
        if spec.landmark is not None:
            for box in _LANDMARK_BOXES:
                if box[0] == spec.landmark:
                    self.prop(spec.landmark, box[1])
        for fx_id, size in fx:
            self.fx_frames(fx_id, size)

    def picker_backdrop(self) -> pygame.Surface:
        """Opaque journey-picker backdrop (the bay scene), baked once."""

        if self._backdrop is None:
            scene = self._postcard_scene("bay")
            frame = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
            scene.draw_back(frame, _POSTCARD_CAMERA)
            self._backdrop = _convert(frame, alpha=False)
            self.release_sources()
        return self._backdrop

    def _postcard_scene(self, look: str) -> SceneLayers:
        memo = self._warm_scenes
        if memo is not None and look in memo:
            return memo[look]
        layers = self._bake_scene(LOOKS.get(look, SceneLook()))
        if memo is not None:
            memo[look] = layers
        return layers

    def warm_thumbnails(self, size: tuple[int, int]) -> None:
        self._warm_scenes = {}
        try:
            for spec in JOURNEYS:
                self.thumbnail(spec, size)
            self.picker_backdrop()
        finally:
            self._warm_scenes = None
        self.release_sources()


__all__ = [
    "ARCH_SIZE",
    "DOLPHIN_BOX",
    "DelfinoArt",
    "LOOKS",
    "ParallaxStrip",
    "SceneLayers",
    "fit_size",
    "quantize_angle",
]
