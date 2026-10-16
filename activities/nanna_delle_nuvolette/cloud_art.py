"""Prepared, bounded art for Cloud Bedtime.

* The night is the shared ``bg.night_sky`` scene kit, composed once into one
  opaque surface per sky "dimness" step (the sky darkens a little for every
  cloud that falls asleep) with the quilt tray panel baked in.
* The little clouds, their quilts and the dream bubble are this package's own
  art (``assets/source/*.svg`` -> ``assets/runtime/*.png``). Cloud bodies and
  quilts are neutral fills tinted once per colour (multiply), then the ink
  contour and the face go on top, so one drawing serves every colour.
* Stars, FX and Momo's poses are the shared library (``prop.shape.star``,
  ``fx.*``, ``character.momo`` variants).

Every surface is built once per content/size and kept in a hard-bounded cache;
drawing only blits. Missing art degrades to simple fallbacks, never a crash.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import ControlArt
from greia_platform.ui_core import BoundedCache

if __package__:
    from .cloud_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, Quilt, dice_points
    from .cloud_layout import (
        ART_FRAME,
        MOON_CENTER,
        BUBBLE_INNER,
        BUBBLE_SIZE,
        CLOUD_SIZE,
        QUILT_CROP,
        QUILT_PATCH,
        TILE_QUILT_WIDTH,
        TRAY_PANEL,
    )
else:
    from cloud_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, Quilt, dice_points
    from cloud_layout import (
        ART_FRAME,
        MOON_CENTER,
        BUBBLE_INNER,
        BUBBLE_SIZE,
        CLOUD_SIZE,
        QUILT_CROP,
        QUILT_PATCH,
        TILE_QUILT_WIDTH,
        TRAY_PANEL,
    )

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"
SKY_LAYERS: Final = (
    "bg.night_sky.sky",
    "bg.night_sky.stars",
    "bg.night_sky.far",
    "bg.night_sky.mid",
    "bg.night_sky.ground",
)
# Night deepens with every sleeping cloud: (overlay alpha) per step.
DIM_ALPHAS: Final = (0, 48, 92, 136)
DIM_COLOUR: Final = (14, 16, 40)
TRAY_FILL: Final = (37, 59, 89, 150)       # navy token, translucent
TRAY_EDGE: Final = (232, 221, 247, 90)     # lavender token
GLOW: Final = (255, 231, 166)               # moon glow (sky layer #FFE7A6)
MOON_PATCH_RADIUS: Final = 70
FACES: Final = ("awake", "yawn", "asleep")
FX_SIZES: Final[dict[str, int]] = {"sparkle": 120, "star_burst": 150, "shooting_star": 150}
# Stars on a tucked quilt sit on this arc (256 frame): y = base - lift * (1 - d^2).
TUCKED_STAR_BASE: Final = 216
TUCKED_STAR_LIFT: Final = 10


def _tinted(source: pygame.Surface, colour: tuple[int, int, int]) -> pygame.Surface:
    tinted = source.copy()
    tinted.fill((*colour, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return tinted


class CloudArt:
    """Own every prepared surface the renderer blits."""

    def __init__(self, *, loader: ControlArt | None = None, runtime_dir: Path = RUNTIME_DIR) -> None:
        # Content art gets its own bounded loader so it never evicts kit glyphs.
        self._art = loader if loader is not None else ControlArt(max_entries=48)
        self._runtime_dir = runtime_dir
        self._private: BoundedCache[str, pygame.Surface | None] = BoundedCache(12)
        self._backdrops: BoundedCache[int, pygame.Surface] = BoundedCache(2)
        self._sky: pygame.Surface | None = None
        self._surfaces: BoundedCache[tuple, pygame.Surface] = BoundedCache(40)
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}

    @property
    def loader(self) -> ControlArt:
        return self._art

    # -- the night ----------------------------------------------------------------

    def backdrop(self, dim_step: int) -> pygame.Surface:
        """The night sky darkened ``dim_step`` times, tray panel included (opaque)."""

        step = max(0, min(len(DIM_ALPHAS) - 1, int(dim_step)))
        cached = self._backdrops.get(step)
        if cached is not None:
            return cached
        surface = self._night().copy()
        if DIM_ALPHAS[step]:
            veil = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            veil.fill((*DIM_COLOUR, DIM_ALPHAS[step]))
            surface.blit(veil, (0, 0))
            # The moon keeps shining while the night deepens around it.
            moon = self._moon_patch()
            surface.blit(moon, moon.get_rect(center=MOON_CENTER))
        panel = pygame.Surface(TRAY_PANEL.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, TRAY_FILL, panel.get_rect(), border_radius=34)
        pygame.draw.rect(panel, TRAY_EDGE, panel.get_rect(), width=3, border_radius=34)
        surface.blit(panel, TRAY_PANEL.topleft)
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        self._backdrops[step] = surface
        return surface

    def _night(self) -> pygame.Surface:
        if self._sky is not None:
            return self._sky
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surface.fill((37, 59, 89))
        loader = ControlArt(max_entries=len(SKY_LAYERS))
        for asset_id in SKY_LAYERS:
            layer = loader.image(asset_id, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
            if layer is not None:
                surface.blit(layer, (0, 0))
        loader.clear()
        self._sky = surface
        return surface

    def _moon_patch(self) -> pygame.Surface:
        """The undimmed moon and its halo with a soft round edge (built once)."""

        key = ("moon_patch",)
        cached = self._surfaces.get(key)
        if cached is not None:
            return cached
        radius = MOON_PATCH_RADIUS
        area = pygame.Rect(0, 0, radius * 2, radius * 2)
        area.center = MOON_CENTER
        patch = pygame.Surface(area.size, pygame.SRCALPHA)
        patch.blit(self._night(), (0, 0), area)
        # Radial alpha mask: draw rings outer -> inner; pygame.draw writes the
        # RGBA value as-is on an SRCALPHA surface, so alpha rises to the centre.
        mask = pygame.Surface(area.size, pygame.SRCALPHA)
        rings = 14
        for ring in range(rings):
            r = radius - ring * radius // (rings + 4)
            alpha = min(255, int(255 * (ring + 1) / (rings * 0.55)))
            pygame.draw.circle(mask, (255, 255, 255, alpha), (radius, radius), r)
        patch.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self._surfaces[key] = patch
        return patch

    def moon_glow(self, radius: int) -> pygame.Surface:
        key = ("moon_glow", radius)
        cached = self._surfaces.get(key)
        if cached is None:
            cached = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            # Soft halo: many faint rings, denser towards the moon.
            for step in range(16):
                r = radius - step * radius // 16
                pygame.draw.circle(cached, (*GLOW, 3 + step), (radius, radius), r)
            self._surfaces[key] = cached
        return cached

    # -- private pictures -----------------------------------------------------------

    def _source(self, name: str) -> pygame.Surface | None:
        if name in self._private:
            return self._private[name]
        image: pygame.Surface | None
        try:
            image = pygame.image.load(str(self._runtime_dir / f"{name}.png"))
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
        except (OSError, pygame.error):
            image = None
        self._private[name] = image
        return image

    def cloud(self, tint: tuple[int, int, int], face: str) -> pygame.Surface:
        """A little cloud of colour ``tint`` with ``face`` (awake/yawn/asleep)."""

        key = ("cloud", tint, face)
        cached = self._surfaces.get(key)
        if cached is not None:
            return cached
        frame = pygame.Surface((ART_FRAME, ART_FRAME), pygame.SRCALPHA)
        body = self._source("cloud_body")
        if body is not None:
            frame.blit(_tinted(body, tint), (0, 0))
        else:
            pygame.draw.ellipse(frame, (*tint, 255), (24, 70, 208, 136))
        for layer in ("cloud_line", f"cloud_face_{face}"):
            image = self._source(layer)
            if image is not None:
                frame.blit(image, (0, 0))
        cached = pygame.transform.smoothscale(frame, (CLOUD_SIZE, CLOUD_SIZE))
        self._surfaces[key] = cached
        return cached

    def tucked_quilt(self, quilt: Quilt) -> pygame.Surface:
        """The quilt pulled up to a cloud's chin (same frame as the cloud)."""

        key = ("tucked", quilt)
        cached = self._surfaces.get(key)
        if cached is not None:
            return cached
        frame = self._quilt_frame(quilt, "blanket_tucked")
        if quilt.stars:
            size = 30 if quilt.stars <= 3 else 25
            spacing = size + 6
            star = self.star(size)
            first = ART_FRAME / 2 - spacing * (quilt.stars - 1) / 2
            for index in range(quilt.stars):
                x = first + index * spacing
                d = (x - ART_FRAME / 2) / (ART_FRAME / 2)
                y = TUCKED_STAR_BASE - TUCKED_STAR_LIFT * (1 - d * d)
                if star is not None:
                    frame.blit(star, star.get_rect(center=(int(x), int(y))))
        cached = pygame.transform.smoothscale(frame, (CLOUD_SIZE, CLOUD_SIZE))
        self._surfaces[key] = cached
        return cached

    def tile_quilt(self, quilt: Quilt, width: int = TILE_QUILT_WIDTH) -> pygame.Surface:
        """A flat quilt as it lies in the tray: its stars in one row."""

        key = ("tile", quilt, width)
        cached = self._surfaces.get(key)
        if cached is not None:
            return cached
        frame = self._quilt_frame(quilt, "blanket")
        if quilt.stars:
            patch = QUILT_PATCH
            size = min(44, int((patch.width - 8) / quilt.stars) - 4)
            spacing = (patch.width - 8) / quilt.stars
            star = self.star(size)
            for index in range(quilt.stars):
                x = patch.x + 4 + spacing * (index + 0.5)
                if star is not None:
                    frame.blit(star, star.get_rect(center=(int(x), patch.centery)))
        crop = frame.subsurface(QUILT_CROP).copy()
        height = int(round(QUILT_CROP.height * width / QUILT_CROP.width))
        cached = pygame.transform.smoothscale(crop, (width, height))
        self._surfaces[key] = cached
        return cached

    def _quilt_frame(self, quilt: Quilt, name: str) -> pygame.Surface:
        frame = pygame.Surface((ART_FRAME, ART_FRAME), pygame.SRCALPHA)
        body = self._source(f"{name}_body")
        if body is not None:
            frame.blit(_tinted(body, quilt.colour.quilt), (0, 0))
        else:
            pygame.draw.rect(frame, (*quilt.colour.quilt, 255), QUILT_CROP, border_radius=18)
        line = self._source(f"{name}_line")
        if line is not None:
            frame.blit(line, (0, 0))
        return frame

    def bubble(self, dream: Quilt) -> pygame.Surface:
        """The dream bubble: the wished quilt colour, and its stars as a dice face.

        The stars float beside the quilt in a dice pattern (not in the row the
        tray quilts use), so the child matches a number, not a picture.
        """

        key = ("bubble", dream)
        cached = self._surfaces.get(key)
        if cached is not None:
            return cached
        frame = pygame.Surface((ART_FRAME, ART_FRAME), pygame.SRCALPHA)
        shell = self._source("dream_bubble")
        if shell is not None:
            frame.blit(shell, (0, 0))
        else:
            pygame.draw.ellipse(frame, (244, 238, 251, 255), (20, 30, 216, 160))
        ix, iy, iw, ih = BUBBLE_INNER
        if dream.stars:
            quilt = self.tile_quilt(Quilt(dream.colour_id), 92)
            frame.blit(quilt, quilt.get_rect(center=(ix + 50, iy + ih // 2 + 2)))
            box = pygame.Rect(ix + 104, iy + 6, 84, ih - 12)
            size = 38 if dream.stars <= 2 else 32 if dream.stars <= 4 else 29
            star = self.star(size)
            for px, py in dice_points(dream.stars):
                if star is not None:
                    frame.blit(star, star.get_rect(center=(int(box.x + px * box.width), int(box.y + py * box.height))))
        else:
            quilt = self.tile_quilt(Quilt(dream.colour_id), 150)
            frame.blit(quilt, quilt.get_rect(center=(ix + iw // 2, iy + ih // 2 + 4)))
        cached = pygame.transform.smoothscale(frame, (BUBBLE_SIZE, BUBBLE_SIZE))
        self._surfaces[key] = cached
        return cached

    # -- shared library -------------------------------------------------------------

    def star(self, size: int) -> pygame.Surface | None:
        return self._art.image("prop.shape.star", int(size))

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

    def momo(self, variant: str, height: int, *, mirrored: bool = False) -> pygame.Surface | None:
        """Momo's canonical pose; ``mirrored`` flips the whole character (rules §8.3)."""

        image = self._art.image("character.momo", height, variant=variant)
        if image is None or not mirrored:
            return image
        key = ("momo_mirrored", variant, height)
        cached = self._surfaces.get(key)
        if cached is None:
            cached = pygame.transform.flip(image, True, False)
            self._surfaces[key] = cached
        return cached

    def glow(self, size: tuple[int, int]) -> pygame.Surface:
        """Soft moonlight ring used for hints (around a dream or a quilt)."""

        key = ("glow", *size)
        cached = self._surfaces.get(key)
        if cached is None:
            width, height = size
            cached = pygame.Surface((width, height), pygame.SRCALPHA)
            for inset, alpha in ((0, 50), (7, 95), (14, 150)):
                rect = pygame.Rect(inset, inset, width - 2 * inset, height - 2 * inset)
                if rect.width > 0 and rect.height > 0:
                    pygame.draw.ellipse(cached, (*GLOW, alpha), rect, width=7)
            self._surfaces[key] = cached
        return cached

    def clear(self) -> None:
        self._private.clear()
        self._backdrops.clear()
        self._surfaces.clear()
        self._fx.clear()
        self._sky = None


__all__ = ["CloudArt", "DIM_ALPHAS", "FACES", "RUNTIME_DIR", "SKY_LAYERS"]
