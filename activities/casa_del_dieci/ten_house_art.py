"""Prepared, bounded art for La Casa del Dieci.

Everything is loaded and scaled once. The opaque backdrop is the shared
``bg.night_sky`` layers with this package's house (``assets/source/house.svg``
-> ``assets/runtime/house.png``) composited on top, so a frame starts with one
blit. Lit-room glass comes from the private window renditions; fireflies,
FX and Dani's poses come from the shared library; numerals, the roof sign,
answer-card faces, count badges and the number-bond strip are painted with
the shared control-kit recipe and cached in small bounded dictionaries.
Drawing code only blits these surfaces.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlPainter, mix
from greia_platform.typography import FontRole

if __package__:
    from .ten_house_layout import CARD_SIZE, HOUSE_ORIGIN, HOUSE_SIZE, ROOM_SIZE, SIGN_RECT
    from .ten_house_model import RoomState
else:
    from ten_house_layout import CARD_SIZE, HOUSE_ORIGIN, HOUSE_SIZE, ROOM_SIZE, SIGN_RECT
    from ten_house_model import RoomState

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"

FIREFLY_ID: Final = "creature.woodland.firefly"
FIREFLY_SIZES: Final[dict[str, int]] = {"room": 62, "flying": 62, "guest": 84, "sky": 64}
FX_SIZES: Final[dict[str, int]] = {"sparkle": 116, "star_burst": 150, "heart_pop": 76, "confetti": 260}
BADGE_SIZE: Final = 50
BOND_DISC: Final = 84
CACHE_LIMIT: Final = 24

COCOA: Final = (61, 44, 31)
CREAM: Final = (255, 251, 235)
SUNSHINE: Final = (255, 194, 52)
SUNSHINE_LIGHT: Final = (255, 218, 133)
TURQUOISE_LIGHT: Final = (143, 212, 206)
LAVENDER: Final = (232, 221, 247)
HALO: Final = (255, 226, 138)


class Tone(StrEnum):
    """Colour family of a badge / bond disc; matches the room glass."""

    HOME = "home"
    GUEST = "guest"
    AWAY = "away"
    WHOLE = "whole"


_TONE_FILL: Final = {
    Tone.HOME: SUNSHINE_LIGHT,
    Tone.GUEST: TURQUOISE_LIGHT,
    Tone.AWAY: LAVENDER,
    Tone.WHOLE: CREAM,
}


class TenHouseArt:
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
        self._art = art if art is not None else ControlArt(max_entries=40)
        self._runtime_dir = runtime_dir
        self.background = self._compose_background(size)
        self.windows: dict[RoomState, pygame.Surface | None] = {
            RoomState.HOME: self._load_private("window_home.png", ROOM_SIZE),
            RoomState.GUEST: self._load_private("window_guest.png", ROOM_SIZE),
        }
        self.fireflies = {name: self._art.image(FIREFLY_ID, px) for name, px in FIREFLY_SIZES.items()}
        self.halo = self._build_halo()
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}
        self._badges: dict[tuple[int, Tone], pygame.Surface] = {}
        self._signs: dict[tuple[int | None, bool], pygame.Surface] = {}
        self._cards: dict[tuple[int, bool], pygame.Surface] = {}
        self._discs: dict[tuple[int, Tone], pygame.Surface] = {}
        self._symbols: dict[str, pygame.Surface] = {}

    # -- cast / creatures ---------------------------------------------------

    def cast_pose(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self._art.image(f"character.{character}", height, variant=variant)

    def firefly(self, role: str) -> pygame.Surface | None:
        return self.fireflies.get(role)

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

    # -- numbers ------------------------------------------------------------

    def badge(self, number: int, tone: Tone = Tone.HOME) -> pygame.Surface:
        """Round numeral token that pops above a room while counting with Dani."""

        key = (number, tone)
        cached = self._badges.get(key)
        if cached is None:
            cached = self._painter.body(BodyShape.ROUND, (BADGE_SIZE, BADGE_SIZE), _fill(tone)).copy()
            label = self._painter.label(str(number), int(BADGE_SIZE * 0.6), COCOA, role=FontRole.DISPLAY)
            cached.blit(label, label.get_rect(center=(BADGE_SIZE // 2, BADGE_SIZE // 2 + 1)))
            _store(self._badges, key, cached)
        return cached

    def sign_face(self, number: int | None, *, dots: bool) -> pygame.Surface:
        """Content of the roof sign: the numeral (and its ten-frame at stage 1).

        ``None`` shows the house's firefly emblem: add / take-away challenges
        have no target to print until the child has answered.
        """

        key = (number, dots)
        cached = self._signs.get(key)
        if cached is not None:
            return cached
        width, height = SIGN_RECT.size
        face = pygame.Surface((width, height), pygame.SRCALPHA)
        if number is None:
            emblem = self._art.image(FIREFLY_ID, height - 8)
            if emblem is not None:
                face.blit(emblem, emblem.get_rect(center=(width // 2, height // 2)))
        elif dots:
            numeral = self._painter.label(str(number), 66, COCOA, role=FontRole.DISPLAY)
            frame = self._dot_frame(number, 112)
            gap = 12
            left = (width - numeral.get_width() - gap - frame.get_width()) // 2
            face.blit(numeral, numeral.get_rect(midleft=(left, height // 2 + 2)))
            face.blit(frame, frame.get_rect(midleft=(left + numeral.get_width() + gap, height // 2)))
        else:
            numeral = self._painter.label(str(number), 74, COCOA, role=FontRole.DISPLAY)
            face.blit(numeral, numeral.get_rect(center=(width // 2, height // 2 + 2)))
        _store(self._signs, key, face)
        return face

    def card_face(self, number: int, *, frame: bool) -> pygame.Surface:
        """Answer-card content: a big numeral, with a mini ten-frame at stage 3."""

        key = (number, frame)
        cached = self._cards.get(key)
        if cached is not None:
            return cached
        width, height = CARD_SIZE
        face = pygame.Surface((int(width * 0.86), int(height * 0.8)), pygame.SRCALPHA)
        if frame:
            numeral = self._painter.label(str(number), int(height * 0.4), COCOA, role=FontRole.DISPLAY)
            dots = self._dot_frame(number, face.get_width() - 6)
            top = max(0, (face.get_height() - numeral.get_height() - 6 - dots.get_height()) // 2)
            face.blit(numeral, numeral.get_rect(midtop=(face.get_width() // 2, top)))
            face.blit(dots, dots.get_rect(midtop=(face.get_width() // 2, top + numeral.get_height() + 6)))
        else:
            numeral = self._painter.label(str(number), int(height * 0.58), COCOA, role=FontRole.DISPLAY)
            face.blit(numeral, numeral.get_rect(center=(face.get_width() // 2, face.get_height() // 2 + 2)))
        _store(self._cards, key, face)
        return face

    def bond_disc(self, number: int, tone: Tone) -> pygame.Surface:
        """One disc of the number-bond strip, coloured like its rooms."""

        key = (number, tone)
        cached = self._discs.get(key)
        if cached is None:
            cached = self._painter.body(BodyShape.ROUND, (BOND_DISC, BOND_DISC), _fill(tone), lip=0).copy()
            label = self._painter.label(str(number), int(BOND_DISC * 0.62), COCOA, role=FontRole.DISPLAY)
            cached.blit(label, label.get_rect(center=(BOND_DISC // 2, BOND_DISC // 2 + 2)))
            _store(self._discs, key, cached)
        return cached

    def symbol(self, text: str) -> pygame.Surface:
        """``+``, ``-`` or ``=`` between bond discs (cream with an ink shadow)."""

        cached = self._symbols.get(text)
        if cached is None:
            glyph = self._painter.label(text, 58, CREAM, role=FontRole.DISPLAY)
            shadow = self._painter.label(text, 58, (37, 59, 89), role=FontRole.DISPLAY)
            cached = pygame.Surface((glyph.get_width() + 3, glyph.get_height() + 3), pygame.SRCALPHA)
            cached.blit(shadow, (3, 3))
            cached.blit(glyph, (0, 0))
            self._symbols[text] = cached
        return cached

    def _dot_frame(self, number: int, width: int) -> pygame.Surface:
        """A 2x5 ten-frame of dots, filled in reading order."""

        gap = max(3, width // 32)
        dot = (width - 6 * gap) // 5
        frame = pygame.Surface((width, 2 * dot + 3 * gap), pygame.SRCALPHA)
        theme = self._painter.theme
        tray = self._painter.body(
            BodyShape.PANEL,
            frame.get_size(),
            mix(theme.surface, theme.ink, 0.08),
            contour_width=2,
            highlight=False,
        )
        frame.blit(tray, (0, 0))
        filled = self._painter.body(BodyShape.ROUND, (dot, dot), SUNSHINE, contour_width=max(2, dot // 10))
        empty = self._painter.body(
            BodyShape.ROUND,
            (dot, dot),
            mix(theme.surface, theme.ink, 0.04),
            contour=mix(theme.ink, theme.surface, 0.5),
            contour_width=2,
            highlight=False,
        )
        for index in range(10):
            row, column = divmod(index, 5)
            frame.blit(filled if index < number else empty, (gap + column * (dot + gap), gap + row * (dot + gap)))
        return frame

    # -- loading --------------------------------------------------------------

    def _build_halo(self) -> pygame.Surface:
        """Soft glow ring around a room for hints (built once)."""

        width, height = ROOM_SIZE[0] + 24, ROOM_SIZE[1] + 24
        halo = pygame.Surface((width, height), pygame.SRCALPHA)
        for inset, alpha in ((0, 70), (4, 120), (8, 190)):
            pygame.draw.rect(
                halo,
                (*HALO, alpha),
                pygame.Rect(inset, inset, width - 2 * inset, height - 2 * inset),
                width=4,
                border_radius=22 - inset,
            )
        return halo

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
        """Night-sky layers plus the house, flattened into one opaque surface."""

        surface = pygame.Surface(size)
        surface.fill((37, 59, 89))
        # A throwaway loader: the layers are released once the composite exists.
        loader = ControlArt(max_entries=6)
        for name in ("sky", "stars", "far", "mid", "ground"):
            image = loader.image(f"bg.night_sky.{name}", size)
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        house = self._load_private("house.png", HOUSE_SIZE)
        if house is not None:
            surface.blit(house, HOUSE_ORIGIN)
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        return surface


def _fill(tone: Tone) -> tuple[int, int, int]:
    return _TONE_FILL.get(tone, CREAM)


def _store(cache: dict, key, value: pygame.Surface) -> None:
    if len(cache) >= CACHE_LIMIT:
        cache.pop(next(iter(cache)))
    cache[key] = value


__all__ = ["BADGE_SIZE", "BOND_DISC", "TenHouseArt", "Tone"]
