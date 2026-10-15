"""Prepared, bounded art for Teatrino delle Fiabe.

Everything is resolved by semantic id from the shared library (stage layers,
scene biomes, cast variants, animals, FX, HUD glyphs) or from this package's
``assets/runtime`` renditions (fairy-tale puppets, the closed curtain, the
shows glyph). Each picture is decoded and scaled once into a bounded cache;
drawing code only blits (plus a cached rotation for a leaning puppet).

Puppets: the canonical cast is never redrawn. A ``PuppetLook`` takes the
shared ``character.<id>`` variants, removes the baked contact shadow (a rod
puppet floats) by cutting every variant at the neutral pose's lowest opaque
row, and scales all variants by one factor, so switching between talk /
cheer / wave never makes the body jump.
"""

from __future__ import annotations

from collections.abc import Callable
import math
from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import ControlArt
from greia_platform.ui_core import BoundedCache

if __package__:
    from .teatrino_content import (
        FX,
        PUPPETS_BY_ID,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SCENES_BY_ID,
        STAGE_FLOOR,
        STAGE_FRONT,
        ArtSource,
        FxSpec,
        PuppetSpec,
    )
else:
    from teatrino_content import (
        FX,
        PUPPETS_BY_ID,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SCENES_BY_ID,
        STAGE_FLOOR,
        STAGE_FRONT,
        ArtSource,
        FxSpec,
        PuppetSpec,
    )

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"
STAGE_SIZE: Final[tuple[int, int]] = (REFERENCE_WIDTH, REFERENCE_HEIGHT)

# Body height of a puppet on stage (logical px); the scale of every variant
# is derived from the neutral picture's opaque height so all friends match.
PUPPET_BODY_HEIGHT: Final = 136
TILT_STEP: Final = 4  # degrees; leaning puppets reuse a few cached rotations
LOOK_CACHE: Final = 8  # puppet looks kept (6 on stage + a little slack)
ROTATION_CACHE: Final = 48
ICON_CACHE: Final = 48
SCENE_CACHE: Final = 2  # full 1024x600 stage backgrounds kept
THUMB_CACHE: Final = 24
FX_SIZES: Final[dict[str, int]] = {
    "note_burst": 150,
    "sparkle": 150,
    "confetti": 300,
    "heart_pop": 140,
    "shooting_star": 170,
    "star_burst": 180,
    "dust_puff": 120,
    "bow_sparkle": 120,
}

# Wooden rod palette (canonical ink + a warm wood ramp).
INK: Final = (75, 55, 47)
WOOD: Final = (201, 138, 75)
WOOD_LIGHT: Final = (233, 185, 122)
HALO: Final = (255, 226, 138)
UNDERSTAGE: Final = (122, 58, 69)  # the stage apron colour (bg.stage.boards)


def _load(path: Path) -> pygame.Surface | None:
    try:
        image = pygame.image.load(str(path))
    except (OSError, pygame.error, FileNotFoundError):
        return None
    if pygame.display.get_surface() is not None:
        try:
            image = image.convert_alpha()
        except pygame.error:
            pass
    return image


def opaque_bounds(surface: pygame.Surface, threshold: int = 127) -> pygame.Rect:
    """Union of the opaque regions (alpha > ``threshold``) of ``surface``.

    Contact shadows in the library are ~14 % opacity, so they never count.
    """

    mask = pygame.mask.from_surface(surface, threshold)
    rects = mask.get_bounding_rects()
    if not rects:
        return surface.get_rect()
    bounds = rects[0].unionall(rects[1:]) if len(rects) > 1 else rects[0]
    return bounds


class PuppetLook:
    """Every prepared picture of one puppet at stage size.

    ``frame(variant)`` returns the variant cut and scaled once; ``anchor`` is
    the point of the frame that sits at the puppet's ``(x, y)``; ``rod_y`` is
    where the rod meets the body (the puppet's lowest opaque row). Variants a
    puppet does not have fall back to its neutral picture.
    """

    def __init__(
        self,
        spec: PuppetSpec,
        loader: Callable[[str], pygame.Surface | None],
        *,
        body_height: int = PUPPET_BODY_HEIGHT,
    ) -> None:
        self.spec = spec
        self._loader = loader
        self._frames: dict[str, pygame.Surface | None] = {}
        self._rotations: BoundedCache[tuple[str, int, bool], pygame.Surface] = BoundedCache(12)
        neutral = loader("default")
        if neutral is None:
            neutral = _placeholder()
        bounds = opaque_bounds(neutral)
        # Cut just below the feet: removes the baked contact shadow and keeps
        # every variant on the same frame (no jumping between poses).
        self._cut = min(neutral.get_height(), bounds.bottom + 2)
        # Wide animals (frog, pig) are normalised on their larger side so they
        # never dwarf the cast; tall friends keep the shared body height.
        self._scale = body_height * spec.scale / max(1.0, bounds.height, bounds.width * 0.86)
        self._size = (
            max(1, round(neutral.get_width() * self._scale)),
            max(1, round(self._cut * self._scale)),
        )
        self.anchor = (
            round(bounds.centerx * self._scale),
            round(bounds.centery * self._scale),
        )
        self.rod_y = round(bounds.bottom * self._scale) - 4
        self.half_width = max(36, round(bounds.width * self._scale / 2))
        self.half_height = max(40, round(bounds.height * self._scale / 2))
        self._frames["default"] = self._prepare(neutral)

    def _prepare(self, source: pygame.Surface) -> pygame.Surface:
        cut = min(self._cut, source.get_height())
        piece = source.subsurface(pygame.Rect(0, 0, source.get_width(), cut))
        return pygame.transform.smoothscale(piece, self._size)

    @property
    def size(self) -> tuple[int, int]:
        return self._size

    def frame(self, variant: str | None) -> pygame.Surface:
        key = variant or "default"
        if key not in self._frames:
            source = self._loader(key) if self.spec.source == ArtSource.CAST else None
            self._frames[key] = self._prepare(source) if source is not None else None
        return self._frames[key] or self._frames["default"]  # type: ignore[return-value]

    def posed(self, variant: str | None, tilt: float, flip: bool) -> tuple[pygame.Surface, tuple[int, int]]:
        """Frame plus the anchor inside it, mirrored/leaning as asked (cached)."""

        flip = flip and self.spec.mirror
        step = int(round(tilt / TILT_STEP)) * TILT_STEP
        base = self.frame(variant)
        ax, ay = self.anchor
        if flip:
            ax = base.get_width() - ax
        if not step and not flip:
            return base, (ax, ay)
        key = (variant or "default", step, flip)
        cached = self._rotations.get(key)
        if cached is None:
            image = pygame.transform.flip(base, True, False) if flip else base
            if step:
                image = pygame.transform.rotate(image, step)
            self._rotations[key] = image
            cached = image
        if not step:
            return cached, (ax, ay)
        # Rotate the anchor about the frame centre (pygame rotates CCW).
        cx, cy = base.get_width() / 2, base.get_height() / 2
        rad = math.radians(step)
        dx, dy = ax - cx, ay - cy
        rx = dx * math.cos(rad) + dy * math.sin(rad)
        ry = -dx * math.sin(rad) + dy * math.cos(rad)
        return cached, (round(cached.get_width() / 2 + rx), round(cached.get_height() / 2 + ry))

    def icon(self, height: int) -> pygame.Surface:
        """The neutral picture cropped to the body, scaled to ``height``."""

        base = self._frames["default"]
        assert base is not None
        crop = opaque_bounds(base).inflate(4, 4).clip(base.get_rect())
        piece = base.subsurface(crop)
        width = max(1, round(piece.get_width() * height / max(1, piece.get_height())))
        return pygame.transform.smoothscale(piece, (width, int(height)))


def _placeholder() -> pygame.Surface:
    surface = pygame.Surface((160, 160), pygame.SRCALPHA)
    pygame.draw.circle(surface, (253, 164, 175), (80, 84), 60)
    pygame.draw.circle(surface, INK, (80, 84), 60, 4)
    return surface


class FxPlayer:
    """A few short library FX bursts (bounded, frame-indexed by time)."""

    MAX_BURSTS: Final = 6
    FRAME_SECONDS: Final = 0.12

    def __init__(self, art: "TeatrinoArt", clock: Callable[[], float]) -> None:
        self._art = art
        self._clock = clock
        self._bursts: list[tuple[tuple[pygame.Surface, ...], tuple[int, int], float]] = []

    def burst(self, name: str, center: tuple[int, int]) -> None:
        frames = self._art.fx_frames(name)
        if not frames:
            return
        self._bursts = [*self._bursts[-(self.MAX_BURSTS - 1):], (frames, (int(center[0]), int(center[1])), self._clock())]

    def _duration(self, frames: tuple[pygame.Surface, ...]) -> float:
        return max(0.5, len(frames) * self.FRAME_SECONDS * 2)

    def prune(self) -> None:
        now = self._clock()
        self._bursts = [b for b in self._bursts if now - b[2] < self._duration(b[0])]

    @property
    def active(self) -> bool:
        return bool(self._bursts)

    def draw(self, target: pygame.Surface) -> None:
        now = self._clock()
        for frames, center, started in self._bursts:
            elapsed = now - started
            index = min(len(frames) - 1, int(elapsed / (self.FRAME_SECONDS * 2)))
            image = frames[index]
            target.blit(image, image.get_rect(center=(center[0], center[1] - int(elapsed * 30))))

    def clear(self) -> None:
        self._bursts = []


class TeatrinoArt:
    """Own every prepared surface the theatre blits (built lazily, bounded)."""

    def __init__(
        self,
        *,
        art: ControlArt | None = None,
        runtime_dir: Path = RUNTIME_DIR,
    ) -> None:
        # Content art has its own bounded cache so it never evicts kit glyphs.
        self._art = art if art is not None else ControlArt(max_entries=64)
        self._runtime_dir = runtime_dir
        self._looks: BoundedCache[str, PuppetLook] = BoundedCache(LOOK_CACHE)
        self._icons: BoundedCache[tuple, pygame.Surface | None] = BoundedCache(ICON_CACHE)
        self._scenes: BoundedCache[str, pygame.Surface] = BoundedCache(SCENE_CACHE)
        self._thumbs: BoundedCache[tuple, pygame.Surface] = BoundedCache(THUMB_CACHE)
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}
        self._halos: BoundedCache[tuple[int, int], pygame.Surface] = BoundedCache(8)
        self._front: list[tuple[pygame.Surface, tuple[int, int]]] | None = None
        self._floor: pygame.Surface | None = None
        self._curtains: tuple[pygame.Surface, pygame.Surface] | None = None

    # -- shared library -------------------------------------------------------

    def shared(self, asset_id: str, size: tuple[int, int] | int, *, variant: str = "default") -> pygame.Surface | None:
        return self._art.image(asset_id, size, variant=variant)

    def shared_path_image(self, asset_id: str, variant: str) -> pygame.Surface | None:
        """Full-size source picture (not cached here; callers prepare once)."""

        try:
            from greia_platform.activity_api import get_shared_visual_path

            return _load(get_shared_visual_path(asset_id, variant=variant))
        except Exception:
            return None

    def private(self, name: str) -> pygame.Surface | None:
        return _load(self._runtime_dir / f"{name}.png")

    # -- puppets -------------------------------------------------------------

    def look(self, puppet_id: str) -> PuppetLook | None:
        spec = PUPPETS_BY_ID.get(puppet_id)
        if spec is None:
            return None
        cached = self._looks.get(puppet_id)
        if cached is not None:
            return cached
        if spec.source == ArtSource.PRIVATE:
            source = self.private(f"puppet_{puppet_id}")
            loader: Callable[[str], pygame.Surface | None] = lambda _variant: source  # noqa: E731
        else:
            asset_id = spec.asset_id or ""
            loader = lambda variant: self.shared_path_image(asset_id, variant)  # noqa: E731
        look = PuppetLook(spec, loader)
        self._looks[puppet_id] = look
        return look

    def puppet_icon(self, puppet_id: str, height: int) -> pygame.Surface | None:
        key = ("puppet", puppet_id, int(height))
        if key in self._icons:
            return self._icons[key]
        look = self.look(puppet_id)
        icon = look.icon(int(height)) if look is not None else None
        self._icons[key] = icon
        return icon

    def halo(self, size: tuple[int, int]) -> pygame.Surface:
        key = (int(size[0]) // 8 * 8, int(size[1]) // 8 * 8)
        cached = self._halos.get(key)
        if cached is None:
            width, height = key
            cached = pygame.Surface((width, height), pygame.SRCALPHA)
            for inset, alpha in ((0, 50), (8, 70), (16, 90)):
                pygame.draw.ellipse(cached, (*HALO, alpha), pygame.Rect(inset, inset, width - 2 * inset, height - 2 * inset))
            self._halos[key] = cached
        return cached

    # -- stage composition ------------------------------------------------------

    def _layer(self, asset_id: str) -> pygame.Surface | None:
        image = self.shared_path_image(asset_id, "default")
        if image is not None and image.get_size() != STAGE_SIZE:
            image = pygame.transform.smoothscale(image, STAGE_SIZE)
        return image

    def floor(self) -> pygame.Surface | None:
        if self._floor is None:
            self._floor = self._layer(STAGE_FLOOR)
        return self._floor

    def apron(self) -> tuple[pygame.Surface, tuple[int, int]] | None:
        """The stage front (gold edge, footlights, apron) as a piece to draw
        over puppet rods on posters."""

        floor = self.floor()
        if floor is None:
            return None
        top = 554
        return floor.subsurface(pygame.Rect(0, top, REFERENCE_WIDTH, REFERENCE_HEIGHT - top)), (0, top)

    def scene_backdrop(self, scene_id: str) -> pygame.Surface:
        """One scene's biome layers + props flattened (no stage floor)."""

        spec = SCENES_BY_ID.get(scene_id) or next(iter(SCENES_BY_ID.values()))
        surface = pygame.Surface(STAGE_SIZE)
        surface.fill(spec.base)
        for layer in spec.layers:
            image = self._layer(layer)
            if image is not None:
                surface.blit(image, (0, 0))
        for prop in spec.props:
            image = self.shared_path_image(prop.asset_id, "default")
            if image is not None:
                image = pygame.transform.smoothscale(image, (prop.size, prop.size))
                surface.blit(image, image.get_rect(midbottom=prop.midbottom))
        return surface

    def stage_background(
        self,
        scene_id: str,
        custom: pygame.Surface | None = None,
        *,
        custom_key: str = "",
        floor_dy: int = 0,
    ) -> pygame.Surface:
        """Opaque scene (or the child's own picture) + stage floor (bounded cache).

        ``custom_key`` identifies the custom picture (its content digest), so a
        cached composition is reused only for the very same picture.
        """

        key = f"custom:{custom_key}:{floor_dy}" if custom is not None else f"{scene_id}:{floor_dy}"
        cached = self._scenes.get(key)
        if cached is not None:
            return cached
        surface = pygame.Surface(STAGE_SIZE)
        if custom is not None:
            surface.blit(pygame.transform.smoothscale(custom, STAGE_SIZE) if custom.get_size() != STAGE_SIZE else custom, (0, 0))
        else:
            surface.blit(self.scene_backdrop(scene_id), (0, 0))
        floor = self.floor()
        if floor is not None:
            surface.blit(floor, (0, floor_dy))
            if floor_dy < 0:
                pygame.draw.rect(surface, UNDERSTAGE, (0, REFERENCE_HEIGHT + floor_dy, REFERENCE_WIDTH, -floor_dy))
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        self._scenes[key] = surface
        return surface

    def scene_thumbnail(self, scene_id: str, size: tuple[int, int]) -> pygame.Surface:
        key = ("scene", scene_id, int(size[0]), int(size[1]))
        cached = self._thumbs.get(key)
        if cached is None:
            cached = pygame.transform.smoothscale(self.scene_backdrop(scene_id), (int(size[0]), int(size[1])))
            self._thumbs[key] = cached
        return cached

    def front_pieces(self) -> list[tuple[pygame.Surface, tuple[int, int]]]:
        """Curtains + valance as tight sub-pictures (cheap per-frame blits)."""

        if self._front is None:
            pieces: list[tuple[pygame.Surface, tuple[int, int]]] = []
            for asset_id in STAGE_FRONT:
                image = self._layer(asset_id)
                if image is None:
                    continue
                bounds = image.get_bounding_rect()
                if bounds.width and bounds.height:
                    pieces.append((image.subsurface(bounds).copy(), bounds.topleft))
            self._front = pieces
        return self._front

    def curtain_halves(self) -> tuple[pygame.Surface, pygame.Surface]:
        """Closed stage curtain: left half (package art) and its mirror."""

        if self._curtains is None:
            left = self.private("curtain_closed")
            half = (REFERENCE_WIDTH // 2, REFERENCE_HEIGHT)
            if left is None:
                left = pygame.Surface(half, pygame.SRCALPHA)
                left.fill((230, 98, 114))
                for x in range(40, half[0], 70):
                    pygame.draw.line(left, (196, 88, 105), (x, 0), (x, half[1]), 7)
                pygame.draw.line(left, (122, 58, 69), (half[0] - 2, 0), (half[0] - 2, half[1]), 4)
            elif left.get_size() != half:
                left = pygame.transform.smoothscale(left, half)
            self._curtains = (left, pygame.transform.flip(left, True, False))
        return self._curtains

    # -- pictures for controls ----------------------------------------------

    def icon(self, asset_id: str, size: int, *, variant: str = "default") -> pygame.Surface | None:
        """A library picture cropped to its subject and fitted into ``size``."""

        key = ("icon", asset_id, variant, int(size))
        if key in self._icons:
            return self._icons[key]
        image = self.shared_path_image(asset_id, variant)
        result = _fit(image, int(size)) if image is not None else None
        self._icons[key] = result
        return result

    def private_icon(self, name: str, size: int) -> pygame.Surface | None:
        key = ("private", name, int(size))
        if key in self._icons:
            return self._icons[key]
        image = self.private(name)
        result = pygame.transform.smoothscale(image, (int(size), int(size))) if image is not None else None
        self._icons[key] = result
        return result

    def fx_icon(self, spec: FxSpec, size: int) -> pygame.Surface | None:
        return self.icon(spec.picture, size, variant=spec.picture_variant)

    def fx_frames(self, name: str) -> tuple[pygame.Surface, ...]:
        cached = self._fx.get(name)
        if cached is not None:
            return cached
        size = FX_SIZES.get(name, 140)
        frames = []
        for variant in ("default", "frame_2", "frame_3"):
            image = self._art.image(f"fx.{name}", size, variant=variant)
            if image is not None:
                frames.append(image)
        self._fx[name] = tuple(frames)
        return self._fx[name]

    def clear(self) -> None:
        self._art.clear()
        self._looks.clear()
        self._icons.clear()
        self._scenes.clear()
        self._thumbs.clear()
        self._fx.clear()
        self._halos.clear()
        self._front = None
        self._floor = None
        self._curtains = None


def _fit(image: pygame.Surface, size: int) -> pygame.Surface:
    crop = opaque_bounds(image, 40).inflate(6, 6).clip(image.get_rect())
    piece = image.subsurface(crop)
    scale = size / max(piece.get_width(), piece.get_height(), 1)
    return pygame.transform.smoothscale(
        piece, (max(1, round(piece.get_width() * scale)), max(1, round(piece.get_height() * scale)))
    )


def draw_rod(target: pygame.Surface, top: tuple[int, int], bottom_y: int) -> None:
    """A wooden puppet rod with an ink contour and one highlight."""

    x, y = top
    if bottom_y <= y:
        return
    pygame.draw.line(target, INK, (x, y), (x, bottom_y), 10)
    pygame.draw.line(target, WOOD, (x, y), (x, bottom_y), 6)
    pygame.draw.line(target, WOOD_LIGHT, (x - 1, y + 2), (x - 1, bottom_y), 2)
    # A little wooden cup where the rod meets the puppet.
    cup = pygame.Rect(0, 0, 26, 12)
    cup.center = (x, y + 2)
    pygame.draw.ellipse(target, WOOD, cup)
    pygame.draw.ellipse(target, INK, cup, 3)


__all__ = [
    "FX",
    "FxPlayer",
    "PUPPET_BODY_HEIGHT",
    "PuppetLook",
    "RUNTIME_DIR",
    "TeatrinoArt",
    "draw_rod",
    "opaque_bounds",
]
