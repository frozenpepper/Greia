"""Art for Il Volo del Draghetto: shared library + three private renditions.

Shared art (resolved semantically, scaled once): the layered ``bg.sky_clouds``
scene, ``prop.nature.cloud`` (bouncy clouds), ``prop.nature.rainbow`` (decor
and the finish rainbow), ``ui.control.star`` (stars), ``prop.shape.diamond``
(gems), look props (``prop.vocab.crown`` / ``prop.vocab.hat`` /
``prop.nature.flower`` / ``prop.shape.star``) and the ``fx.*`` frames.

Activity-private renditions (``assets/source/*.svg`` -> ``assets/runtime``,
GREIA_SVG_AUTHORING_RULES): the dragon in three wing frames (a non-cast
creature), the rainbow ring as back/front halves so the dragon flies *through*
it, and a floating sky island.

Performance (Acer floor): the sky + far cloud bank are composed once per
course into one opaque surface; the mid/foreground cloud layers are cut once
into small sprites (mask bounding rects) so parallax only blits cloud pixels.
Everything else is scaled once into bounded caches; drawing is blits only.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import ControlArt
from greia_platform.ui_core import BoundedCache

try:
    from dragon_courses import COURSES, CourseSpec, SkyDecor, look_by_id
    from dragon_model import REFERENCE_HEIGHT, REFERENCE_WIDTH
except ImportError:  # pragma: no cover - package import path
    from .dragon_courses import COURSES, CourseSpec, SkyDecor, look_by_id
    from .dragon_model import REFERENCE_HEIGHT, REFERENCE_WIDTH

PACKAGE_ROOT: Final = Path(__file__).resolve().parent
RUNTIME_DIR: Final = PACKAGE_ROOT / "assets" / "runtime"
DRAGON_FRAMES: Final = ("dragon_fly_up", "dragon_fly_mid", "dragon_fly_down")
#: Body centre of the dragon in its 256 px master (collision pivot).
DRAGON_PIVOT: Final = (138.0, 132.0)
DRAGON_HEIGHT: Final = 150
#: Inner half-height of the ring opening in its 256 px master.
RING_INNER_HALF: Final = 84.0
RING_VISUAL_SLACK: Final = 12.0
SKY_LAYERS: Final = ("bg.sky_clouds.sky", "bg.sky_clouds.far", "bg.sky_clouds.mid", "bg.sky_clouds.foreground")
FX_FRAMES: Final = {
    "sparkle": ("default", "frame_2"),
    "star_burst": ("default", "frame_2", "frame_3"),
    "dust_puff": ("default", "frame_2", "frame_3"),
    "confetti": ("default", "frame_2", "frame_3"),
}
NAVY: Final = (37, 59, 89)

Sprite = tuple[pygame.Surface, int, int]


def _display_ready() -> bool:
    return pygame.display.get_init() and pygame.display.get_surface() is not None


def _alpha(surface: pygame.Surface) -> pygame.Surface:
    return surface.convert_alpha() if _display_ready() else surface


def _opaque(surface: pygame.Surface) -> pygame.Surface:
    return surface.convert() if _display_ready() else surface


class DragonArt:
    """Own every scene/hero surface for one Activity run (bounded caches)."""

    def __init__(
        self,
        art: ControlArt,
        *,
        runtime_dir: Path = RUNTIME_DIR,
        layer_loader: Callable[[str], pygame.Surface | None] | None = None,
    ) -> None:
        self.art = art
        self._runtime_dir = runtime_dir
        self._layer_loader = layer_loader or self._load_shared_layer
        self._private: dict[str, pygame.Surface | None] = {}
        self._dragon: BoundedCache[tuple[str, int], tuple[pygame.Surface, ...]] = BoundedCache(4)
        self._rings: BoundedCache[int, tuple[pygame.Surface, pygame.Surface]] = BoundedCache(6)
        self._backdrops: BoundedCache[str, pygame.Surface] = BoundedCache(2)
        self._misc: BoundedCache[tuple, pygame.Surface | None] = BoundedCache(48)
        self._mid: list[Sprite] | None = None
        self._front: list[Sprite] | None = None
        self._sky: pygame.Surface | None = None
        self._far: pygame.Surface | None = None

    # -- loading -------------------------------------------------------------

    @staticmethod
    def _load_shared_layer(asset_id: str) -> pygame.Surface | None:
        try:
            from greia_platform.activity_api import get_shared_visual_path

            return pygame.image.load(str(get_shared_visual_path(asset_id)))
        except Exception:
            return None

    def private(self, name: str) -> pygame.Surface | None:
        if name not in self._private:
            try:
                surface = _alpha(pygame.image.load(str(self._runtime_dir / f"{name}.png")))
            except Exception:
                surface = None
            self._private[name] = surface
        return self._private[name]

    def _scaled_private(self, name: str, size: tuple[int, int]) -> pygame.Surface | None:
        key = ("private", name, size)
        if key not in self._misc:
            source = self.private(name)
            self._misc[key] = None if source is None else pygame.transform.smoothscale(source, size)
        return self._misc[key]

    def _layers(self) -> None:
        if self._sky is not None:
            return
        size = (REFERENCE_WIDTH, REFERENCE_HEIGHT)
        loaded = []
        for asset_id in SKY_LAYERS:
            layer = self._layer_loader(asset_id)
            if layer is not None and layer.get_size() != size:
                layer = pygame.transform.smoothscale(layer, size)
            loaded.append(layer)
        sky, far, mid, front = loaded
        if sky is None:
            sky = pygame.Surface(size)
            top, bottom = (159, 205, 236), (233, 228, 240)
            for y in range(size[1]):
                t = y / size[1]
                sky.fill(tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)), (0, y, size[0], 1))
        self._sky = _opaque(sky)
        self._far = _alpha(far) if far is not None else None
        self._mid = _cut_sprites(mid)
        self._front = _cut_sprites(front)

    # -- scene ---------------------------------------------------------------

    def backdrop(self, spec: CourseSpec) -> pygame.Surface:
        """Opaque sky + far cloud bank for one course (composed once)."""

        cached = self._backdrops.get(spec.course_id)
        if cached is not None:
            return cached
        self._layers()
        assert self._sky is not None
        surface = self._sky.copy()
        if spec.decor is SkyDecor.SUNSET:
            # Evening light: coral at the top warming to peach near the clouds.
            _wash(surface, (244, 150, 128), (255, 200, 140), spec.tint_amount + 0.24)
        elif spec.tint is not None and spec.tint_amount > 0:
            _wash(surface, spec.tint, spec.tint, spec.tint_amount)
        if self._far is not None:
            surface.blit(self._far, (0, 0))
        if spec.decor is SkyDecor.SUNSET:
            _wash(surface, (255, 196, 150), (255, 214, 170), 0.2)
        surface = _opaque(surface)
        self._backdrops[spec.course_id] = surface
        return surface

    @property
    def mid_clouds(self) -> list[Sprite]:
        self._layers()
        return self._mid or []

    @property
    def front_clouds(self) -> list[Sprite]:
        self._layers()
        return self._front or []

    def decor(self, spec: CourseSpec) -> list[tuple[pygame.Surface, int, int]]:
        """Repeating background motif (period ``DECOR_PERIOD``) for a course."""

        key = ("decor", spec.decor.value)
        cached = self._misc.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        items: list[tuple[pygame.Surface, int, int]] = []
        if spec.decor in (SkyDecor.ISLANDS, SkyDecor.SUNSET):
            for width, x, y in ((190, 120, 96), (140, 760, 120), (170, 1300, 360)):
                island = self._scaled_private("sky_island", (width, width // 2))
                if island is not None:
                    items.append((_haze(island), x, y))
        elif spec.decor is SkyDecor.RAINBOWS:
            for width, x, y in ((260, 160, 330), (200, 980, 96)):
                bow = self.art.image("prop.nature.rainbow", (width, width // 2))
                if bow is not None:
                    items.append((_haze(bow), x, y))
        self._misc[key] = items  # type: ignore[assignment]
        return items

    # -- hero ----------------------------------------------------------------

    def dragon_frames(self, look_id: str, height: int = DRAGON_HEIGHT) -> tuple[pygame.Surface, ...]:
        """Three wing frames (up, mid, down) wearing ``look_id``, scaled once."""

        key = (look_id, int(height))
        cached = self._dragon.get(key)
        if cached is not None:
            return cached
        look = look_by_id(look_id)
        hat: pygame.Surface | None = None
        if look.visual_id is not None:
            prop = self.art.image(look.visual_id, max(8, int(height * look.scale)))
            if prop is not None:
                hat = pygame.transform.rotozoom(prop, look.tilt, 1.0)
        frames: list[pygame.Surface] = []
        for name in DRAGON_FRAMES:
            frame = self._scaled_private(name, (int(height), int(height)))
            if frame is None:
                frame = _fallback_dragon(int(height))
            frame = frame.copy()
            if hat is not None:
                anchor = (int(height * look.anchor[0]), int(height * look.anchor[1]))
                frame.blit(hat, hat.get_rect(midbottom=(anchor[0], anchor[1] + hat.get_height() // 6)))
            frames.append(frame)
        result = tuple(frames)
        self._dragon[key] = result
        return result

    @staticmethod
    def dragon_rect(frame: pygame.Surface, center: tuple[float, float]) -> pygame.Rect:
        """Place a dragon frame so its body pivot sits on ``center``."""

        scale = frame.get_height() / 256.0
        return frame.get_rect(
            topleft=(int(center[0] - DRAGON_PIVOT[0] * scale), int(center[1] - DRAGON_PIVOT[1] * scale))
        )

    def ring(self, half_open: float) -> tuple[pygame.Surface, pygame.Surface]:
        """(back, front) halves sized so the opening matches the tolerance."""

        size = int(round(256 * (half_open + RING_VISUAL_SLACK) / RING_INNER_HALF / 4.0)) * 4
        cached = self._rings.get(size)
        if cached is not None:
            return cached
        back = self._scaled_private("ring_back", (size, size))
        front = self._scaled_private("ring_front", (size, size))
        if back is None or front is None:
            back, front = _fallback_ring(size)
        result = (back, front)
        self._rings[size] = result
        return result

    def image(self, asset_id: str, size: int | tuple[int, int], variant: str = "default") -> pygame.Surface | None:
        return self.art.image(asset_id, size, variant=variant)

    def star(self, size: int = 46) -> pygame.Surface | None:
        return self.art.image("ui.control.star", size)

    def gem(self, size: int = 52) -> pygame.Surface | None:
        return self.art.image("prop.shape.diamond", size)

    def cloud(self, width: int) -> pygame.Surface | None:
        return self.art.image("prop.nature.cloud", width)

    def island(self, width: int) -> pygame.Surface | None:
        return self._scaled_private("sky_island", (int(width), int(width) // 2))

    def finish_rainbow(self, width: int = 640) -> pygame.Surface | None:
        return self.art.image("prop.nature.rainbow", (width, width // 2))

    def fx(self, kind: str, frame: int, size: int) -> pygame.Surface | None:
        variants = FX_FRAMES.get(kind, ("default",))
        return self.art.image(f"fx.{kind}", size, variant=variants[min(frame, len(variants) - 1)])

    def fx_frames(self, kind: str) -> int:
        return len(FX_FRAMES.get(kind, ("default",)))

    # -- pre-flight pictures -------------------------------------------------

    def course_picture(self, spec: CourseSpec, width: int, *, earned: int, locked: bool) -> pygame.Surface:
        """A course card picture: its sky + motif + ring, and earned stars."""

        key = ("thumb", spec.course_id, int(width), locked, earned)
        cached = self._misc.get(key)
        if cached is not None:
            return cached
        height = int(width * 0.62)
        stars_h = int(width * 0.24)
        surface = pygame.Surface((width, height + stars_h + 4), pygame.SRCALPHA)
        sky = pygame.transform.smoothscale(self.backdrop(spec), (int(height * REFERENCE_WIDTH / REFERENCE_HEIGHT), height))
        picture = pygame.Surface((width, height), pygame.SRCALPHA)
        picture.blit(sky, ((width - sky.get_width()) // 2, 0))
        motif = self._motif(spec, width)
        if motif is not None:
            picture.blit(motif, motif.get_rect(midbottom=(int(width * 0.3), height - 4)))
        back, front = self.ring(40.0)
        ring_size = int(height * 0.9)
        back = pygame.transform.smoothscale(back, (ring_size, ring_size))
        front = pygame.transform.smoothscale(front, (ring_size, ring_size))
        picture.blit(back, back.get_rect(center=(int(width * 0.68), height // 2)))
        picture.blit(front, front.get_rect(center=(int(width * 0.68), height // 2)))
        rounded = _round_corners(picture, max(8, width // 12))
        pygame.draw.rect(rounded, (75, 55, 47), rounded.get_rect(), width=3, border_radius=max(8, width // 12))
        surface.blit(rounded, (0, 0))
        star_size = stars_h
        gap = max(2, star_size // 8)
        total = 3 * star_size + 2 * gap
        x = (width - total) // 2
        for index in range(3):
            star = self.art.image("ui.control.star", star_size, variant="default" if index < earned else "off")
            if star is not None:
                surface.blit(star, (x + index * (star_size + gap), height + 4))
        self._misc[key] = surface
        return surface

    def _motif(self, spec: CourseSpec, width: int) -> pygame.Surface | None:
        if spec.decor in (SkyDecor.ISLANDS, SkyDecor.SUNSET):
            w = int(width * 0.55)
            return self._scaled_private("sky_island", (w, w // 2))
        if spec.decor is SkyDecor.RAINBOWS:
            w = int(width * 0.55)
            return self.art.image("prop.nature.rainbow", (w, w // 2))
        return self.art.image("prop.nature.cloud", int(width * 0.42))

    def look_icon(self, look_id: str, size: int) -> pygame.Surface | None:
        """Picture for a look button: the prop, or the bare dragon head."""

        look = look_by_id(look_id)
        if look.visual_id is not None:
            return self.art.image(look.visual_id, size)
        key = ("head", size)
        if key not in self._misc:
            source = self.private("dragon_fly_mid")
            head = None
            if source is not None:
                crop = source.subsurface(pygame.Rect(116, 34, 124, 124)).copy()
                head = pygame.transform.smoothscale(crop, (size, size))
            self._misc[key] = head
        return self._misc[key]

    def clear(self) -> None:
        self._dragon.clear()
        self._rings.clear()
        self._backdrops.clear()
        self._misc.clear()
        self._private.clear()


def _cut_sprites(layer: pygame.Surface | None) -> list[Sprite]:
    """Split a mostly transparent layer into its opaque pieces (once)."""

    if layer is None:
        return []
    layer = _alpha(layer)
    mask = pygame.mask.from_surface(layer, 12)
    width, height = layer.get_size()
    sprites: list[Sprite] = []
    for rect in mask.get_bounding_rects():
        # The layer does not tile: pieces cut by the canvas edge would show a
        # seam when scrolled, so only whole clouds become parallax sprites.
        if rect.width * rect.height < 64 or rect.left <= 0 or rect.right >= width or rect.top <= 0:
            continue
        sprites.append((layer.subsurface(rect).copy(), rect.x, rect.y))
    return sprites[:24]


def _wash(surface: pygame.Surface, top: tuple[int, int, int], bottom: tuple[int, int, int], amount: float) -> None:
    """Blend a vertical colour wash over an opaque surface (composition time only)."""

    width, height = surface.get_size()
    wash = pygame.Surface((width, height))
    for y in range(0, height, 4):
        t = y / max(1, height - 1)
        wash.fill(tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)), (0, y, width, 4))
    wash.set_alpha(int(255 * max(0.0, min(1.0, amount))))
    surface.blit(wash, (0, 0))


def _haze(surface: pygame.Surface) -> pygame.Surface:
    """Far-layer value: lighter, bluer, less contrast (no blur)."""

    hazed = surface.copy()
    hazed.fill((70, 80, 92, 0), special_flags=pygame.BLEND_RGBA_ADD)
    hazed.fill((255, 255, 255, 190), special_flags=pygame.BLEND_RGBA_MULT)
    return hazed


def _round_corners(surface: pygame.Surface, radius: int) -> pygame.Surface:
    mask = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    result = surface.copy()
    result.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return result


def _fallback_dragon(size: int) -> pygame.Surface:
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    s = size / 256.0
    pygame.draw.ellipse(surface, (89, 184, 106), (int(56 * s), int(108 * s), int(106 * s), int(82 * s)))
    pygame.draw.circle(surface, (89, 184, 106), (int(166 * s), int(112 * s)), int(46 * s))
    pygame.draw.circle(surface, (52, 44, 53), (int(178 * s), int(104 * s)), max(2, int(9 * s)))
    return surface


def _fallback_ring(size: int) -> tuple[pygame.Surface, pygame.Surface]:
    back = pygame.Surface((size, size), pygame.SRCALPHA)
    front = pygame.Surface((size, size), pygame.SRCALPHA)
    rect = pygame.Rect(size * 0.24, size * 0.06, size * 0.52, size * 0.88)
    pygame.draw.ellipse(back, (244, 111, 97), rect, max(4, size // 18))
    pygame.draw.arc(front, (244, 111, 97), rect, -1.57, 1.57, max(4, size // 18))
    return back, front


__all__ = ["DRAGON_HEIGHT", "DragonArt", "NAVY"]
