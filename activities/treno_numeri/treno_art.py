"""Prepared, bounded art for Treno Numeri.

Everything is loaded and scaled once. The backdrop is the shared
``bg.meadow_day`` layers plus this package's station strip (track bed and
platform) composed into one opaque surface; cargo comes from the shared prop
library, Dani's poses from the canonical cast, FX from the shared ``fx.*`` set,
and the train/order board from this package's SVG renditions
(``assets/source`` -> ``assets/runtime``, rendered at their display size).
Number badges, the board's numeral + dot card and the "same" pictogram are
painted with the shared control-kit recipe and cached. Drawing code only
blits these surfaces.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlPainter, mix
from greia_platform.typography import FontRole

if __package__:
    from .treno_content import (
        ITEM_SIZE,
        LOCO_SIZE,
        LOCO_WHEELS,
        POP_ITEM_SIZE,
        SIGN_FACE,
        SIGN_SIZE,
        STATION_TOP,
        WAGON_ITEM_SIZE,
        WAGON_SIZE,
        WAGON_WHEEL_SIZE,
        WAGON_WHEELS_X,
        CargoKind,
    )
else:
    from treno_content import (
        ITEM_SIZE,
        LOCO_SIZE,
        LOCO_WHEELS,
        POP_ITEM_SIZE,
        SIGN_FACE,
        SIGN_SIZE,
        STATION_TOP,
        WAGON_ITEM_SIZE,
        WAGON_SIZE,
        WAGON_WHEEL_SIZE,
        WAGON_WHEELS_X,
        CargoKind,
    )

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"

WAGON_POP_SIZE: Final[int] = 72
# Platform size, platform "pop", hop in-between, wagon pop (also a hop step) and wagon size.
ITEM_SIZES: Final[tuple[int, ...]] = (ITEM_SIZE, POP_ITEM_SIZE, 82, WAGON_POP_SIZE, WAGON_ITEM_SIZE)
BADGE_SIZE: Final[int] = 46
WHEEL_FRAMES: Final[int] = 4  # cross spokes repeat every 90 degrees
FX_SIZES: Final[dict[str, int]] = {
    "sparkle": 110,
    "confetti": 260,
    "star_burst": 200,
    "dust_puff": 84,
    "check_pop": 120,
}
HILLS_SHIFT: Final[int] = -170
GROUND_SHIFT: Final[int] = -150
WAGON_COLOURS: Final[tuple[str, str]] = ("orange", "leaf")

COCOA: Final[tuple[int, int, int]] = (61, 44, 31)
INK: Final[tuple[int, int, int]] = (75, 55, 47)
SUNSHINE: Final[tuple[int, int, int]] = (255, 194, 52)
CORAL: Final[tuple[int, int, int]] = (244, 111, 97)


class TrainArt:
    """Own every prepared surface the renderer blits (bounded, built once)."""

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
        self.locomotive = self._load_private("locomotive.png", LOCO_SIZE)
        self.sign = self._load_private("station_sign.png", SIGN_SIZE)
        self.wagon_back = tuple(self._load_private(f"wagon_back_{c}.png", WAGON_SIZE) for c in WAGON_COLOURS)
        self.wagon_front = tuple(self._load_private(f"wagon_front_{c}.png", WAGON_SIZE) for c in WAGON_COLOURS)
        wheel = self._load_private("wheel.png", (64, 64))
        sizes = {WAGON_WHEEL_SIZE, *(size for _, size in LOCO_WHEELS)}
        self._wheels = {size: _wheel_frames(wheel, size) for size in sizes}
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}
        self._badges: dict[int, pygame.Surface] = {}
        self._faces: dict[tuple[str, int], pygame.Surface] = {}
        self.extra_ring = self._ring(WAGON_POP_SIZE + 6, CORAL)
        self.missing_ghost = self._ghost(WAGON_ITEM_SIZE - 6)

    # -- cargo --------------------------------------------------------------

    def item(self, kind: CargoKind, size: int = ITEM_SIZE) -> pygame.Surface | None:
        """Shared prop at the nearest prepared size."""

        prepared = min(ITEM_SIZES, key=lambda value: abs(value - size))
        return self._art.image(kind.asset_id, prepared)

    def preload(self, kind: CargoKind) -> None:
        for size in ITEM_SIZES:
            self._art.image(kind.asset_id, size)

    def wheel(self, size: int, frame: int) -> pygame.Surface | None:
        frames = self._wheels.get(size)
        if not frames:
            return None
        return frames[frame % len(frames)]

    # -- FX -----------------------------------------------------------------

    def fx_frames(self, name: str) -> tuple[pygame.Surface, ...]:
        cached = self._fx.get(name)
        if cached is not None:
            return cached
        size = FX_SIZES.get(name, 128)
        frames = []
        for variant in ("default", "frame_2", "frame_3"):
            image = self._art.image(f"fx.{name}", size, variant=variant)
            if image is not None:
                frames.append(image)
        self._fx[name] = tuple(frames)
        return self._fx[name]

    # -- numbers and order cards ----------------------------------------------

    def badge(self, number: int) -> pygame.Surface:
        """Small sunshine numeral token that pops above cargo as it is counted."""

        cached = self._badges.get(number)
        if cached is None:
            body = self._painter.body(BodyShape.ROUND, (BADGE_SIZE, BADGE_SIZE), SUNSHINE)
            cached = body.copy()
            label = self._painter.label(str(number), int(BADGE_SIZE * 0.62), COCOA, role=FontRole.DISPLAY)
            cached.blit(label, label.get_rect(center=(BADGE_SIZE // 2, BADGE_SIZE // 2 + 1)))
            if len(self._badges) >= 12:
                self._badges.pop(next(iter(self._badges)))
            self._badges[number] = cached
        return cached

    def order_face(self, number: int, *, dots: bool) -> pygame.Surface:
        """Board content: the ordered numeral, with a dot card on the first rung."""

        key = ("dots" if dots else "numeral", number)
        cached = self._faces.get(key)
        if cached is not None:
            return cached
        width, height = SIGN_FACE[2], SIGN_FACE[3]
        face = pygame.Surface((width, height), pygame.SRCALPHA)
        if dots:
            numeral = self._painter.label(str(number), int(height * 0.5), COCOA, role=FontRole.DISPLAY)
            frame = self._dot_frame(number, int(width * 0.84))
            gap = 4
            top = max(0, (height - numeral.get_height() - gap - frame.get_height()) // 2)
            face.blit(numeral, numeral.get_rect(midtop=(width // 2, top)))
            face.blit(frame, frame.get_rect(midtop=(width // 2, top + numeral.get_height() + gap)))
        else:
            numeral = self._painter.label(str(number), int(height * 0.82), COCOA, role=FontRole.DISPLAY)
            face.blit(numeral, numeral.get_rect(center=(width // 2, height // 2 + 2)))
        self._remember_face(key, face)
        return face

    def same_face(self) -> pygame.Surface:
        """Board content for the compare stages: orange wagon = green wagon."""

        key = ("same", 0)
        cached = self._faces.get(key)
        if cached is not None:
            return cached
        width, height = SIGN_FACE[2], SIGN_FACE[3]
        face = pygame.Surface((width, height), pygame.SRCALPHA)
        # Mini wagons on wheels, stacked: the art's empty top/bottom margins
        # (about a quarter of its height) are allowed to overlap.
        scale = width * 0.83 / WAGON_SIZE[0]
        mini = (int(WAGON_SIZE[0] * scale), int(WAGON_SIZE[1] * scale))
        wheel = self._wheels.get(WAGON_WHEEL_SIZE, ())
        mini_wheel = int(WAGON_WHEEL_SIZE * scale)
        equals = self._painter.label("=", int(height * 0.24), COCOA, role=FontRole.DISPLAY)
        step = mini[1] + equals.get_height() - int(mini[1] * 0.42)
        top = (height - (mini[1] + step)) // 2 - int(mini[1] * 0.06)
        left = (width - mini[0]) // 2
        for index, y in enumerate((top, top + step)):
            if wheel:
                small = pygame.transform.smoothscale(wheel[0], (mini_wheel, mini_wheel))
                for wx in WAGON_WHEELS_X:
                    face.blit(small, small.get_rect(midbottom=(left + int(wx * scale), y + mini[1])))
            for layer in (self.wagon_back[index], self.wagon_front[index]):
                if layer is not None:
                    face.blit(pygame.transform.smoothscale(layer, mini), (left, y))
        face.blit(equals, equals.get_rect(center=(width // 2, top + mini[1] + (step - mini[1]) // 2 - int(mini[1] * 0.06))))
        self._remember_face(key, face)
        return face

    def _remember_face(self, key: tuple[str, int], face: pygame.Surface) -> None:
        if len(self._faces) >= 16:
            self._faces.pop(next(iter(self._faces)))
        self._faces[key] = face

    def _dot_frame(self, number: int, width: int) -> pygame.Surface:
        wells = 10 if number > 5 else 5
        rows = wells // 5
        gap = max(3, width // 36)
        dot = (width - 6 * gap) // 5
        frame = pygame.Surface((width, rows * dot + (rows + 1) * gap), pygame.SRCALPHA)
        theme = self._painter.theme
        tray = self._painter.body(
            BodyShape.PANEL,
            frame.get_size(),
            mix(theme.surface, theme.ink, 0.08),
            contour_width=2,
            highlight=False,
        )
        frame.blit(tray, (0, 0))
        filled = self._painter.body(BodyShape.ROUND, (dot, dot), theme.accent, contour_width=max(2, dot // 10))
        empty = self._painter.body(
            BodyShape.ROUND,
            (dot, dot),
            mix(theme.surface, theme.ink, 0.04),
            contour=mix(theme.ink, theme.surface, 0.5),
            contour_width=2,
            highlight=False,
        )
        for index in range(wells):
            row, column = divmod(index, 5)
            frame.blit(filled if index < number else empty, (gap + column * (dot + gap), gap + row * (dot + gap)))
        return frame

    # -- demonstration markers ---------------------------------------------------

    @staticmethod
    def _ring(size: int, colour: tuple[int, int, int]) -> pygame.Surface:
        ring = pygame.Surface((size, size), pygame.SRCALPHA)
        centre = (size // 2, size // 2)
        pygame.draw.circle(ring, INK, centre, size // 2)
        pygame.draw.circle(ring, colour, centre, size // 2 - 2)
        pygame.draw.circle(ring, (0, 0, 0, 0), centre, size // 2 - 8)
        return ring

    @staticmethod
    def _ghost(size: int) -> pygame.Surface:
        ghost = pygame.Surface((size, size), pygame.SRCALPHA)
        centre = (size // 2, size // 2)
        # An empty place that glows: pale centre, sunshine ring, ink contour.
        pygame.draw.circle(ghost, (*INK, 230), centre, size // 2)
        pygame.draw.circle(ghost, SUNSHINE, centre, size // 2 - 2)
        pygame.draw.circle(ghost, (255, 251, 235, 215), centre, size // 2 - 7)
        return ghost

    # -- loading ------------------------------------------------------------------

    def _load_private(self, name: str, size: tuple[int, int]) -> pygame.Surface | None:
        try:
            image = pygame.image.load(str(self._runtime_dir / name))
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
        except (OSError, pygame.error):
            return None
        if image.get_size() != size:
            image = pygame.transform.smoothscale(image, size)
        return image

    def _compose_background(self, size: tuple[int, int]) -> pygame.Surface:
        """Meadow layers raised behind the station strip (one opaque surface)."""

        surface = pygame.Surface(size)
        # A throwaway loader: the full-screen layers are released once the
        # opaque composite exists.
        loader = ControlArt(max_entries=6)

        def layer(name: str) -> pygame.Surface | None:
            return loader.image(f"bg.meadow_day.{name}", (1024, 600))

        sky = layer("sky")
        if sky is None:
            surface.fill((207, 234, 247))
        else:
            surface.blit(sky, (0, 0))
        ground = layer("ground")
        grass = ground.get_at((size[0] // 2, size[1] - 4))[:3] if ground is not None else (98, 188, 114)
        surface.fill(grass, pygame.Rect(0, size[1] // 2, size[0], size[1] - size[1] // 2))
        for name, shift in (("far", HILLS_SHIFT), ("mid", HILLS_SHIFT), ("ground", GROUND_SHIFT)):
            image = ground if name == "ground" else layer(name)
            if image is not None:
                surface.blit(image, (0, shift))
        loader.clear()
        station = self._load_private("station.png", (size[0], size[1] - STATION_TOP))
        if station is not None:
            surface.blit(station, (0, STATION_TOP))
        else:
            surface.fill((238, 221, 186), pygame.Rect(0, STATION_TOP, size[0], size[1] - STATION_TOP))
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        return surface

    def cast_pose(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self._art.image(f"character.{character}", height, variant=variant)


def _wheel_frames(wheel: pygame.Surface | None, size: int) -> tuple[pygame.Surface, ...]:
    """Pre-rotated wheel frames (rotation happens once here, never per frame)."""

    if wheel is None:
        return ()
    base = pygame.transform.smoothscale(wheel, (size, size))
    step = 90.0 / WHEEL_FRAMES
    return tuple(
        base if index == 0 else pygame.transform.rotozoom(base, -step * index, 1.0) for index in range(WHEEL_FRAMES)
    )


__all__ = ["BADGE_SIZE", "TrainArt", "WAGON_POP_SIZE"]
