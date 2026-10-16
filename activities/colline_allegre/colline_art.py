"""Prepared, bounded art for Colline Allegre.

* Backdrops are the shared biome kits (``bg.<biome>.sky/far/mid``): the sky
  is one opaque surface; the far and mid bands are cropped to their pixels
  and mirror-tiled once into 2048-px strips, so parallax scrolling is a
  seamless pair of blits whatever the layer's edges look like.
* The ground is drawn by code in the biome's ground colours (cocoa contour,
  one light band under the edge, the GREIA_SVG_AUTHORING_RULES recipe) and
  pre-rendered once per 256-px strip ("chunk") together with everything
  static on it: bridges over the pond, mud, the snail "slow down" signs and
  shared-library decor (flowers, trees, pines, a woodland spectator). Chunks
  live in a small LRU; drawing a frame only blits.
* Tito's buggy is Activity-private art (``assets/source`` -> ``assets/runtime``)
  composed once per pose with the canonical ``character.tito`` variant in
  the seat, then rotated in 3-degree steps into a bounded cache. Wheels are
  pre-turned in 10-degree steps (the rim has a 90-degree symmetry).
* Stars, mushrooms, friends and FX are the shared library.
* Everything blitted per frame is prepared with
  ``greia_platform.pygame_blit.prepare_static`` (display format + SDL RLE):
  on the Atom an un-encoded per-pixel-alpha blit costs ~0.22 us/pixel, so
  the two parallax bands and the ground strips alone took ~190 ms a frame.
  Fades use baked ``FadeSteps`` instead of per-frame ``set_alpha``.

Missing art degrades to simple vector fallbacks; nothing raises.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.activity_controls import ControlArt
from greia_platform.pygame_blit import FadeSteps, prepare_static
from greia_platform.ui_core import BoundedCache

if __package__:
    from .colline_content import BASE_Y, REFERENCE_HEIGHT, REFERENCE_WIDTH, FeatureKind
    from .colline_layout import CHUNK_WIDTH, DECOR_HEADROOM, FRIEND_HEIGHT
    from .colline_model import CourseLayout
else:
    from colline_content import BASE_Y, REFERENCE_HEIGHT, REFERENCE_WIDTH, FeatureKind
    from colline_layout import CHUNK_WIDTH, DECOR_HEADROOM, FRIEND_HEIGHT
    from colline_model import CourseLayout

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"

INK: Final = (75, 55, 47)
CREAM: Final = (255, 251, 235)
GOLD: Final = (251, 191, 36)
GOLD_DEEP: Final = (245, 158, 11)
GLOW: Final = (255, 214, 102)
WATER: Final = (120, 183, 223)
WATER_LIGHT: Final = (180, 218, 240)
WATER_EDGE: Final = (70, 128, 170)
WOOD_LIGHT: Final = (226, 172, 116)
WOOD: Final = (196, 134, 82)
WOOD_DARK: Final = (150, 98, 58)
MUD: Final = (139, 94, 60)
MUD_DARK: Final = (101, 66, 42)

# Vehicle composite: chassis centre sits at the composite's centre.
COMPOSITE_SIZE: Final = (200, 200)
BODY_SIZE: Final = (171, 85)
BODY_ANCHOR: Final = (85, 50)  # chassis centre inside the body/back art
DRIVER_HEIGHT: Final = 96
DRIVER_OFFSET: Final = (-24, 18)  # driver image midbottom relative to the chassis centre
WHEEL_SIZE: Final = 46
ANGLE_STEP_DEG: Final = 3
WHEEL_STEP_DEG: Final = 10
DRIVER_POSES: Final = ("happy", "pose_cheer", "pose_think", "pose_point", "surprised")

FX_SIZES: Final[dict[str, int]] = {"sparkle": 90, "star_burst": 150, "confetti": 240, "dust_puff": 120}
STAR_SIZE: Final = 64
MUSHROOM_SIZE: Final = 96
FLAG_SIZE: Final = 112
SIGN_SIZE: Final = 120
ARCH_SIZE: Final = 240
PICNIC_SIZE: Final = (240, 120)


@dataclass(frozen=True, slots=True)
class Decor:
    asset_id: str
    height: int
    variant: str = "default"
    sink: int = 6  # px the base sits below the ground line (trees: the trunk is buried)
    behind: bool = False  # drawn before the ground fill


@dataclass(frozen=True, slots=True)
class BiomeStyle:
    """Ground colours and decor of one shared biome kit."""

    layers: tuple[str, ...]
    ground_light: tuple[int, int, int]
    ground: tuple[int, int, int]
    contour: tuple[int, int, int]
    small: tuple[Decor, ...]
    large: tuple[Decor, ...]
    spectator: Decor | None


_GRASS = ((176, 222, 160), (108, 192, 120), (81, 114, 78))

BIOMES: Final[dict[str, BiomeStyle]] = {
    "meadow_day": BiomeStyle(
        ("sky", "far", "mid"),
        *_GRASS,
        (Decor("prop.nature.flower", 44),),
        (Decor("prop.vocab.tree", 150, sink=10, behind=True),),
        Decor("creature.woodland.hedgehog", 70),
    ),
    "woodland_pond": BiomeStyle(
        ("sky", "far", "mid"),
        *_GRASS,
        (Decor("prop.nature.flower", 44),),
        (Decor("prop.vocab.tree", 160, sink=10, behind=True),),
        Decor("creature.woodland.frog", 64),
    ),
    "woodland_autumn": BiomeStyle(
        ("sky", "far", "mid"),
        (216, 214, 150),
        (178, 186, 96),
        (117, 114, 64),
        (Decor("prop.nature.mushroom", 40), Decor("prop.nature.leaf_autumn", 34)),
        (Decor("prop.vocab.tree", 150, sink=10, behind=True),),
        Decor("creature.woodland.squirrel", 76),
    ),
    "woodland_snow": BiomeStyle(
        ("sky", "far", "mid"),
        (255, 255, 255),
        (226, 235, 246),
        (128, 146, 176),
        (Decor("prop.nature.pinecone", 30),),
        (Decor("prop.vocab.pine", 160, sink=10, behind=True),),
        Decor("creature.woodland.deer", 86),
    ),
    "sky_clouds": BiomeStyle(
        ("sky", "far", "mid"),
        (196, 232, 178),
        (128, 204, 136),
        (81, 114, 78),
        (Decor("prop.nature.flower", 44),),
        (Decor("prop.nature.rainbow", 120, sink=-40, behind=True),),
        Decor("creature.woodland.butterfly", 60, sink=-60),
    ),
}


class Backdrop:
    """One biome's sky + mirror-tiled far/mid strips (built once per course)."""

    def __init__(self, art: ControlArt, biome: str) -> None:
        self.biome = biome
        sky = art.image(f"bg.{biome}.sky", (REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surface.fill((207, 234, 247))
        if sky is not None:
            surface.blit(sky, (0, 0))
        self.sky = _convert(surface, alpha=False)
        self.far = self._strip(art, f"bg.{biome}.far")
        self.mid = self._strip(art, f"bg.{biome}.mid")
        self.fill: tuple[int, int, int] | None = None
        if self.mid is not None:
            strip, top = self.mid
            # A little above the bottom row (the band's lowest rows are a contour).
            color = strip.get_at((REFERENCE_WIDTH // 2, max(0, strip.get_height() - 16)))
            if color.a >= 250:
                self.fill = (color.r, color.g, color.b)
            self.mid_bottom = top + strip.get_height()
        else:
            self.mid_bottom = REFERENCE_HEIGHT

    @staticmethod
    def _strip(art: ControlArt, asset_id: str) -> tuple[pygame.Surface, int] | None:
        layer = art.image(asset_id, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
        if layer is None:
            return None
        bounds = layer.get_bounding_rect()
        if bounds.height <= 0:
            return None
        band = layer.subsurface(pygame.Rect(0, bounds.top, REFERENCE_WIDTH, bounds.height)).copy()
        strip = pygame.Surface((REFERENCE_WIDTH * 2, bounds.height), pygame.SRCALPHA)
        strip.blit(band, (0, 0))
        strip.blit(pygame.transform.flip(band, True, False), (REFERENCE_WIDTH, 0))
        return prepare_static(strip), bounds.top

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float) -> None:
        surface.blit(self.sky, (0, 0))
        for layer, rate, lift in ((self.far, 0.12, 0.08), (self.mid, 0.3, 0.18)):
            if layer is None:
                continue
            strip, top = layer
            width = strip.get_width()
            offset = int(cam_x * rate) % width
            y = int(top - cam_y * lift)
            surface.blit(strip, (-offset, y))
            if width - offset < REFERENCE_WIDTH:
                surface.blit(strip, (width - offset, y))
        if self.fill is not None:
            bottom = int(self.mid_bottom - cam_y * 0.18)
            if bottom < REFERENCE_HEIGHT:
                surface.fill(self.fill, pygame.Rect(0, bottom, REFERENCE_WIDTH, REFERENCE_HEIGHT - bottom))


@dataclass(frozen=True, slots=True)
class Chunk:
    surface: pygame.Surface
    top: int  # world y of the surface's top row
    solid_from: int  # world y below which the strip is plain ground colour
    fill: tuple[int, int, int]


class CollineArt:
    """Own every prepared surface the renderer blits."""

    def __init__(self, *, loader: ControlArt | None = None, runtime_dir: Path = RUNTIME_DIR) -> None:
        self._art = loader if loader is not None else ControlArt(max_entries=64)
        self._runtime_dir = runtime_dir
        self._private: dict[str, pygame.Surface | None] = {}
        self._backdrop: Backdrop | None = None
        self._chunks: BoundedCache[tuple, Chunk] = BoundedCache(10)
        self._decor: tuple[tuple[str, list], ...] = ()
        self._composites: dict[str, pygame.Surface] = {}
        self._rotated: BoundedCache[tuple[str, int], pygame.Surface] = BoundedCache(48)
        self._wheels: dict[int, pygame.Surface] = {}
        self._misc: BoundedCache[tuple, pygame.Surface | None] = BoundedCache(40)
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}
        self._sign_glow: FadeSteps | None = None

    @property
    def loader(self) -> ControlArt:
        return self._art

    # -- private renditions -----------------------------------------------------------

    def private(self, name: str) -> pygame.Surface | None:
        if name in self._private:
            return self._private[name]
        try:
            image: pygame.Surface | None = pygame.image.load(str(self._runtime_dir / f"{name}.png"))
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
        except (pygame.error, FileNotFoundError, OSError):
            image = None
        self._private[name] = image
        return image

    # -- backdrop -----------------------------------------------------------------------

    def backdrop(self, biome: str) -> Backdrop:
        if self._backdrop is None or self._backdrop.biome != biome:
            self._backdrop = None
            loader = ControlArt(max_entries=4)
            self._backdrop = Backdrop(loader, biome)
            loader.clear()
        return self._backdrop

    # -- ground chunks -------------------------------------------------------------------

    def begin_course(self, layout: CourseLayout) -> None:
        """Forget the previous course's chunks and place this course's decor."""

        self._chunks.clear()
        style = BIOMES.get(layout.spec.biome, BIOMES["meadow_day"])
        self._decor = tuple(_place_decor(layout, style))

    def chunk(self, layout: CourseLayout, index: int) -> Chunk:
        key = (layout.spec.course_id, layout.rung, index)
        cached = self._chunks.get(key)
        if cached is not None:
            return cached
        chunk = self._build_chunk(layout, index)
        self._chunks[key] = chunk
        return chunk

    def _build_chunk(self, layout: CourseLayout, index: int) -> Chunk:
        style = BIOMES.get(layout.spec.biome, BIOMES["meadow_day"])
        x0 = index * CHUNK_WIDTH
        xs = list(range(x0 - 8, x0 + CHUNK_WIDTH + 12, 4))
        ys = [layout.height(float(x)) for x in xs]
        top = int(min(ys)) - DECOR_HEADROOM
        solid_from = int(max(ys)) + 40
        for span in layout.spans:
            if span.feature.kind is FeatureKind.BRIDGE and span.x0 < x0 + CHUNK_WIDTH and span.x1 > x0:
                solid_from = max(solid_from, int(BASE_Y + span.feature.height * layout.scale) + 24)
        height = max(8, solid_from - top)
        surface = pygame.Surface((CHUNK_WIDTH, height), pygame.SRCALPHA)
        local = [(x - x0, y - top) for x, y in zip(xs, ys)]

        for decor, items in self._decor:
            for item in items:
                if item[0] - 200 <= x0 + CHUNK_WIDTH and item[0] + 200 >= x0 and item[2].behind:
                    self._blit_decor(surface, layout, item, x0, top)

        polygon = [*local, (local[-1][0], height + 2), (local[0][0], height + 2)]
        pygame.draw.polygon(surface, style.ground, polygon)
        self._texture(surface, style, x0, local, height)
        band = [(x, y + 10) for x, y in local]
        pygame.draw.lines(surface, style.ground_light, False, band, 9)
        pygame.draw.lines(surface, style.contour, False, local, 5)
        for dy in (-2.5, 2.5):
            pygame.draw.aalines(surface, style.contour, False, [(x, y + dy) for x, y in local])

        self._surfaces(surface, layout, x0, top)
        for decor, items in self._decor:
            for item in items:
                if item[0] - 200 <= x0 + CHUNK_WIDTH and item[0] + 200 >= x0 and not item[2].behind:
                    self._blit_decor(surface, layout, item, x0, top)
        sign = self.sign()
        for drop in layout.drops:
            if drop.sign_x - SIGN_SIZE <= x0 + CHUNK_WIDTH and drop.sign_x + SIGN_SIZE >= x0 and sign is not None:
                ground = layout.height(drop.sign_x)
                surface.blit(sign, sign.get_rect(midbottom=(int(drop.sign_x - x0), int(ground - top + 8))))
        return Chunk(prepare_static(surface), top, solid_from, style.ground)

    @staticmethod
    def _texture(surface: pygame.Surface, style: BiomeStyle, x0: int, local, height: int) -> None:
        """Small darker grass strokes inside the ground body (fixed per strip)."""

        rng = random.Random(x0 * 7 + 3)
        shade = tuple(int(c * 0.86) for c in style.ground)
        for _ in range(7):
            lx = rng.randint(6, CHUNK_WIDTH - 26)
            column = min(len(local) - 1, max(0, (lx + 8) // 4))
            ground = local[column][1]
            y = rng.randint(int(ground) + 34, int(ground) + 150)
            if y >= height - 6:
                continue
            w = rng.randint(14, 24)
            pygame.draw.arc(surface, shade, pygame.Rect(lx, y, w, 10), 0.3, 2.8, 2)

    def _surfaces(self, surface: pygame.Surface, layout: CourseLayout, x0: int, top: int) -> None:
        """Pond + bridge deck, and mud, inside this chunk."""

        for span in layout.spans:
            if span.x1 < x0 - 40 or span.x0 > x0 + CHUNK_WIDTH + 40:
                continue
            kind = span.feature.kind
            if kind is FeatureKind.BRIDGE:
                deck = int(BASE_Y - top)
                depth = int(span.feature.height * layout.scale)
                pond = pygame.Rect(int(span.x0 + 46 - x0), deck + 6, int(span.x1 - span.x0 - 92), depth)
                pygame.draw.rect(surface, WATER, pond, border_radius=26)
                pygame.draw.rect(surface, WATER_EDGE, pond, width=3, border_radius=26)
                for k in range(3):
                    wave_y = pond.top + 18 + k * 16
                    if wave_y < pond.bottom - 10:
                        pygame.draw.line(surface, WATER_LIGHT, (pond.left + 30 + k * 40, wave_y), (pond.left + 80 + k * 40, wave_y), 4)
                left, right = int(span.x0 - x0), int(span.x1 - x0)
                for post in range(left + 40, right - 20, 90):
                    pygame.draw.rect(surface, WOOD_DARK, (post, deck, 12, depth - 4), border_radius=4)
                    pygame.draw.rect(surface, INK, (post, deck, 12, depth - 4), width=2, border_radius=4)
                deck_rect = pygame.Rect(left, deck - 8, right - left, 18)
                pygame.draw.rect(surface, WOOD, deck_rect, border_radius=6)
                pygame.draw.line(surface, WOOD_LIGHT, (left + 8, deck - 4), (right - 8, deck - 4), 3)
                for plank in range(left + 18, right - 8, 20):
                    pygame.draw.line(surface, WOOD_DARK, (plank, deck - 6), (plank, deck + 8), 2)
                pygame.draw.rect(surface, INK, deck_rect, width=3, border_radius=6)
            elif kind is FeatureKind.MUD:
                start, end = span.at(0.1), span.at(0.9)
                lo, hi = max(start, x0 - 8), min(end, x0 + CHUNK_WIDTH + 8)
                if hi <= lo:
                    continue
                xs = [lo + (hi - lo) * k / 24 for k in range(25)]
                # A soft brown puddle following the ground, thin at both ends.
                upper, lower = [], []
                for x in xs:
                    t = (x - start) / (end - start)
                    thick = 4 + 12 * math.sin(math.pi * t) ** 0.5
                    gy = layout.height(x) - top
                    wobble = math.sin(x * 0.09) * 1.5
                    upper.append((x - x0, gy - 3 + wobble))
                    lower.append((x - x0, gy + thick))
                pygame.draw.polygon(surface, MUD, upper + lower[::-1])
                pygame.draw.lines(surface, MUD_DARK, False, upper, 3)
                rng = random.Random(int(start))
                for _ in range(int((end - start) // 70)):
                    bx = rng.uniform(start + 30, end - 30)
                    if lo <= bx <= hi:
                        gy = layout.height(bx) - top
                        pygame.draw.ellipse(surface, (176, 132, 96), pygame.Rect(int(bx - x0 - 9), int(gy + 1), 18, 5))

    def _blit_decor(self, surface: pygame.Surface, layout: CourseLayout, item, x0: int, top: int) -> None:
        x, flip, decor = item
        image = self._decor_image(decor, flip)
        if image is None:
            return
        ground = layout.height(x)
        surface.blit(image, image.get_rect(midbottom=(int(x - x0), int(ground - top + decor.sink))))

    def _decor_image(self, decor: Decor, flip: bool) -> pygame.Surface | None:
        key = ("decor", decor.asset_id, decor.height, flip)
        if key in self._misc:
            return self._misc[key]
        image = self._art.fit(decor.asset_id, decor.height, variant=decor.variant)
        if image is not None and flip:
            image = pygame.transform.flip(image, True, False)
        self._misc[key] = image
        return image

    # -- buggy ---------------------------------------------------------------------------

    def vehicle(self, pose: str, angle: float) -> pygame.Surface:
        """Buggy + Tito (``pose``) turned to ``angle`` (radians, + = nose down)."""

        step = int(round(math.degrees(angle) / ANGLE_STEP_DEG)) % (360 // ANGLE_STEP_DEG)
        key = (pose, step)
        cached = self._rotated.get(key)
        if cached is not None:
            return cached
        base = self.composite(pose)
        rotated = prepare_static(base if step == 0 else pygame.transform.rotozoom(base, -step * ANGLE_STEP_DEG, 1.0))
        self._rotated[key] = rotated
        return rotated

    def composite(self, pose: str) -> pygame.Surface:
        cached = self._composites.get(pose)
        if cached is not None:
            return cached
        surface = pygame.Surface(COMPOSITE_SIZE, pygame.SRCALPHA)
        cx, cy = COMPOSITE_SIZE[0] // 2, COMPOSITE_SIZE[1] // 2
        body_at = (cx - BODY_ANCHOR[0], cy - BODY_ANCHOR[1])
        back = self.private("buggy_back")
        if back is not None:
            surface.blit(back, body_at)
        driver = self._art.image("character.tito", DRIVER_HEIGHT, variant=pose if pose in DRIVER_POSES else "happy")
        if driver is not None:
            surface.blit(driver, driver.get_rect(midbottom=(cx + DRIVER_OFFSET[0], cy + DRIVER_OFFSET[1])))
        body = self.private("buggy_body")
        if body is not None:
            surface.blit(body, body_at)
        else:
            pygame.draw.rect(surface, (148, 100, 201), (cx - 75, cy - 12, 150, 30), border_radius=12)
            pygame.draw.rect(surface, INK, (cx - 75, cy - 12, 150, 30), width=3, border_radius=12)
        surface = _convert(surface)
        self._composites[pose] = surface
        return surface

    def wheel(self, spin: float) -> pygame.Surface:
        step = int(math.degrees(spin) % 90 // WHEEL_STEP_DEG)
        cached = self._wheels.get(step)
        if cached is not None:
            return cached
        base = self.private("buggy_wheel")
        if base is None:
            base = pygame.Surface((WHEEL_SIZE, WHEEL_SIZE), pygame.SRCALPHA)
            pygame.draw.circle(base, (79, 82, 88), (WHEEL_SIZE // 2, WHEEL_SIZE // 2), WHEEL_SIZE // 2 - 1)
            pygame.draw.circle(base, CREAM, (WHEEL_SIZE // 2, WHEEL_SIZE // 2), WHEEL_SIZE // 4)
        image = prepare_static(base if step == 0 else pygame.transform.rotozoom(base, -step * WHEEL_STEP_DEG, 1.0))
        self._wheels[step] = image
        return image

    def mini_buggy(self, height: int) -> pygame.Surface | None:
        """The HUD marker: the buggy with Tito, small."""

        key = ("mini", height)
        if key in self._misc:
            return self._misc[key]
        base = self.composite("happy").copy()
        wheel = self.private("buggy_wheel")
        if wheel is not None:
            for dx in (-48, 48):
                base.blit(wheel, wheel.get_rect(center=(100 + dx, 100 + 30)))
        bounds = base.get_bounding_rect()
        cropped = base.subsurface(bounds).copy()
        width = max(1, round(cropped.get_width() * height / max(1, cropped.get_height())))
        image = prepare_static(pygame.transform.smoothscale(cropped, (width, height)))
        self._misc[key] = image
        return image

    # -- props ---------------------------------------------------------------------------

    def star(self, size: int = STAR_SIZE) -> pygame.Surface | None:
        return self._blitted(("star", size), lambda: self._art.image("prop.vocab.star", size))

    def star_off(self, size: int) -> pygame.Surface | None:
        return self._blitted(("star_off", size), lambda: self._art.image("ui.control.star", size, variant="off"))

    def mushroom(self, squash: float = 0.0) -> pygame.Surface | None:
        step = int(round(max(0.0, min(1.0, squash)) * 4))

        def build() -> pygame.Surface | None:
            base = self._art.image("prop.nature.mushroom", MUSHROOM_SIZE)
            if base is None or step == 0:
                return base
            factor = 1.0 - 0.07 * step
            return pygame.transform.smoothscale(
                base, (int(MUSHROOM_SIZE * (1.0 + 0.05 * step)), int(MUSHROOM_SIZE * factor))
            )

        return self._blitted(("mushroom", step), build)

    def flag(self, on: bool) -> pygame.Surface | None:
        name = "checkpoint_on" if on else "checkpoint"
        return self._blitted(("private", name), lambda: self.private(name))

    def arch(self) -> pygame.Surface | None:
        return self._blitted(("private", "finish_arch"), lambda: self.private("finish_arch"))

    def picnic(self) -> pygame.Surface | None:
        return self._blitted(("private", "picnic"), lambda: self.private("picnic"))

    def sign(self) -> pygame.Surface | None:
        """The "slow down" sign: the private board with the shared snail on it."""

        def build() -> pygame.Surface | None:
            board = self.private("sign_slow")
            if board is None:
                return None
            image = board.copy()
            snail = self._art.image("prop.vocab.snail", int(SIGN_SIZE * 0.5))
            if snail is not None:
                image.blit(snail, snail.get_rect(center=(SIGN_SIZE // 2, int(SIGN_SIZE * 0.36))))
            return image

        return self._cached(("sign",), build)

    def sign_glow(self) -> FadeSteps:
        """The pulsing glow behind a hinted sign, pre-faded (``FadeSteps.at(alpha)``)."""

        if self._sign_glow is None:
            self._sign_glow = FadeSteps(self._sign_glow_surface(), steps=8)
        return self._sign_glow

    def _sign_glow_surface(self) -> pygame.Surface:
        def build() -> pygame.Surface:
            size = SIGN_SIZE + 40
            ss = 2
            big = pygame.Surface((size * ss, size * ss), pygame.SRCALPHA)
            center = (size * ss // 2, int((SIGN_SIZE * 0.38 + 20) * ss))
            pygame.draw.circle(big, (*GLOW, 120), center, int(SIGN_SIZE * 0.5 * ss) + 16 * ss)
            pygame.draw.circle(big, GOLD_DEEP, center, int(SIGN_SIZE * 0.5 * ss) + 8 * ss, width=5 * ss)
            return pygame.transform.smoothscale(big, (size, size))

        result = self._cached(("sign_glow",), build)
        assert result is not None
        return result

    def friend(self, character: str, variant: str) -> pygame.Surface | None:
        return self._blitted(
            ("friend", character, variant), lambda: self._art.image(f"character.{character}", FRIEND_HEIGHT, variant=variant)
        )

    def portrait(self, character: str, size: int) -> pygame.Surface | None:
        return self._cached(("portrait", character, size), lambda: self._art.image(f"character.{character}", size, variant="happy"))

    def fx_frames(self, name: str) -> tuple[pygame.Surface, ...]:
        cached = self._fx.get(name)
        if cached is not None:
            return cached
        size = FX_SIZES.get(name, 120)
        frames = []
        for variant in ("default", "frame_2", "frame_3"):
            image = self._art.image(f"fx.{name}", size, variant=variant)
            if image is not None:
                frames.append(prepare_static(image))
        self._fx[name] = tuple(frames)
        return self._fx[name]

    def _cached(self, key: tuple, build) -> pygame.Surface | None:
        if key in self._misc:
            return self._misc[key]
        image = build()
        self._misc[key] = image
        return image

    def _blitted(self, key: tuple, build) -> pygame.Surface | None:
        """Like ``_cached`` for surfaces blitted every frame: an RLE copy of ``build()``."""

        def prepared() -> pygame.Surface | None:
            image = build()
            return prepare_static(image) if image is not None else None

        return self._cached(("blit", *key), prepared)

    def clear(self) -> None:
        self._chunks.clear()
        self._rotated.clear()
        self._misc.clear()
        self._composites.clear()
        self._wheels.clear()
        self._fx.clear()
        self._sign_glow = None
        self._backdrop = None


def _place_decor(layout: CourseLayout, style: BiomeStyle) -> list[tuple[str, list]]:
    """Deterministic decor positions for a course (same course -> same meadow)."""

    rng = random.Random(f"{layout.spec.course_id}:{layout.rung}")
    busy: list[tuple[float, float]] = [(x0, x1) for x0, x1, _ in layout.surface_spans()]
    busy += [(d.sign_x - 90, d.bottom_x + 60) for d in layout.drops]
    busy += [(flag - 150, flag + 40) for flag in layout.checkpoints]
    busy += [(layout.finish_x - 160, layout.length)]
    busy += [(layout.start_x - 140, layout.start_x + 120)]

    def free(x: float, half: float) -> bool:
        return all(x + half < a or x - half > b for a, b in busy)

    groups: list[tuple[str, list]] = []
    small: list = []
    x = 260.0
    while x < layout.finish_x:
        x += rng.uniform(150, 260)
        if style.small and free(x, 24):
            small.append((x, rng.random() < 0.5, rng.choice(style.small)))
    groups.append(("small", small))
    large: list = []
    x = 500.0
    while x < layout.finish_x - 200:
        x += rng.uniform(700, 1100)
        if style.large and free(x, 80):
            large.append((x, rng.random() < 0.5, rng.choice(style.large)))
    groups.append(("large", large))
    if style.spectator is not None:
        # One woodland friend watches from the top of the highest hill.
        best_x, best_y = None, BASE_Y
        for span in layout.spans:
            if span.feature.kind is FeatureKind.HILL:
                cx = span.at(0.5)
                if layout.height(cx) < best_y and free(cx, 50):
                    best_x, best_y = cx + 60, layout.height(cx)
        if best_x is not None:
            groups.append(("spectator", [(best_x, False, style.spectator)]))
    return groups


def _convert(surface: pygame.Surface, *, alpha: bool = True) -> pygame.Surface:
    if pygame.display.get_surface() is None:
        return surface
    return surface.convert_alpha() if alpha else surface.convert()


__all__ = [
    "BIOMES",
    "Backdrop",
    "BiomeStyle",
    "Chunk",
    "CollineArt",
    "Decor",
    "DRIVER_POSES",
    "STAR_SIZE",
]
