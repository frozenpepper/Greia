"""Prepared, bounded art for Il Giardino dei Numeri.

Everything is loaded and scaled once: the meadow backdrop is composed from the
shared ``bg.meadow_day`` layers into one opaque surface, garden objects come
from the shared prop/creature library, Dani's poses from the canonical cast,
FX from the shared ``fx.*`` set and the crate from this package's own SVG
renditions (``assets/source`` -> ``assets/runtime``). Number badges and the
numeral + dot cards are painted with the shared control-kit recipe and cached.
Drawing code only blits these surfaces.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlPainter, mix
from greia_platform.typography import FontRole

if __package__:
    from .giardino_model import CRATE_SIZE, ITEM_SIZE, POP_ITEM_SIZE, ItemKind
else:
    from giardino_model import CRATE_SIZE, ITEM_SIZE, POP_ITEM_SIZE, ItemKind

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"

# Field size, "pop" emphasis size, two hop in-betweens and the crate size.
ITEM_SIZES: Final[tuple[int, ...]] = (ITEM_SIZE, POP_ITEM_SIZE, 96, 82, 70)
WELL_ITEM_SIZE: Final[int] = 70
BADGE_SIZE: Final[int] = 50
CARD_SIZE: Final[tuple[int, int]] = (176, 214)
CLOSE_CARD_SIZE: Final[tuple[int, int]] = (236, 286)
FX_SIZES: Final[dict[str, int]] = {"sparkle": 120, "ripple": 120, "confetti": 260, "star_burst": 220}
GROUND_SHIFT: Final[int] = -165
HILLS_SHIFT: Final[int] = -150
FOREGROUND_WIDTH: Final[int] = 560

COCOA: Final[tuple[int, int, int]] = (61, 44, 31)
SUNSHINE: Final[tuple[int, int, int]] = (255, 194, 52)
CREAM: Final[tuple[int, int, int]] = (255, 251, 235)


class GardenArt:
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
        self._art = art if art is not None else ControlArt(max_entries=72)
        self._runtime_dir = runtime_dir
        self.background = self._compose_background(size)
        self.crate_back = self._load_private("crate_back.png", CRATE_SIZE)
        self.crate_front = self._load_private("crate_front.png", CRATE_SIZE)
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}
        self._badges: dict[int, pygame.Surface] = {}
        self._faces: dict[tuple[int, int], pygame.Surface] = {}
        self._close_cards: dict[int, pygame.Surface] = {}

    # -- garden objects ---------------------------------------------------

    def item(self, kind: ItemKind, size: int = ITEM_SIZE) -> pygame.Surface | None:
        """Shared prop at one of the prepared sizes (nearest prepared size)."""

        prepared = min(ITEM_SIZES, key=lambda value: abs(value - size))
        return self._art.image(kind.asset_id, prepared)

    def preload(self, kind: ItemKind) -> None:
        for size in ITEM_SIZES:
            self._art.image(kind.asset_id, size)

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

    def badge(self, number: int) -> pygame.Surface:
        """Small sunshine numeral token that pops above a counted object."""

        cached = self._badges.get(number)
        if cached is None:
            body = self._painter.body(BodyShape.ROUND, (BADGE_SIZE, BADGE_SIZE), SUNSHINE)
            cached = body.copy()
            label = self._painter.label(str(number), int(BADGE_SIZE * 0.62), COCOA, role=FontRole.DISPLAY)
            cached.blit(label, label.get_rect(center=(BADGE_SIZE // 2, BADGE_SIZE // 2 + 1)))
            self._badges[number] = cached
        return cached

    def card_face(self, number: int, size: tuple[int, int] = CARD_SIZE) -> pygame.Surface:
        """Numeral above a five/ten-frame of dots: the quantity card content."""

        key = (number, size[0])
        cached = self._faces.get(key)
        if cached is not None:
            return cached
        width, height = size
        face = pygame.Surface((int(width * 0.86), int(height * 0.8)), pygame.SRCALPHA)
        numeral_size = int(height * (0.42 if number <= 5 else 0.34))
        numeral = self._painter.label(str(number), numeral_size, COCOA, role=FontRole.DISPLAY)
        frame = self._dot_frame(number, face.get_width())
        gap = max(6, height // 30)
        # The numeral and its dot frame read as one group, centred on the card.
        top = max(0, (face.get_height() - numeral.get_height() - gap - frame.get_height()) // 2)
        face.blit(numeral, numeral.get_rect(midtop=(face.get_width() // 2, top)))
        face.blit(frame, frame.get_rect(midtop=(face.get_width() // 2, top + numeral.get_height() + gap)))
        if len(self._faces) >= 24:
            self._faces.pop(next(iter(self._faces)))
        self._faces[key] = face
        return face

    def close_card(self, number: int) -> pygame.Surface:
        """Big cream card for the cardinality close ("that's N")."""

        cached = self._close_cards.get(number)
        if cached is None:
            body = self._painter.body(BodyShape.PANEL, CLOSE_CARD_SIZE, CREAM, lip=8)
            cached = body.copy()
            face = self.card_face(number, CLOSE_CARD_SIZE)
            cached.blit(face, face.get_rect(center=(CLOSE_CARD_SIZE[0] // 2, (CLOSE_CARD_SIZE[1] - 8) // 2)))
            if len(self._close_cards) >= 4:
                self._close_cards.pop(next(iter(self._close_cards)))
            self._close_cards[number] = cached
        return cached

    def _dot_frame(self, number: int, width: int) -> pygame.Surface:
        wells = 10 if number > 5 else 5
        rows = wells // 5
        gap = max(4, width // 40)
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

    # -- loading --------------------------------------------------------------

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
        """Meadow layers with the grass raised so objects stand on the ground."""

        surface = pygame.Surface(size)
        # A throwaway loader: the five full-screen layers are released once the
        # opaque composite exists (only ~1.8 MB stays resident).
        loader = ControlArt(max_entries=6)

        def layer(name: str) -> pygame.Surface | None:
            return loader.image(f"bg.meadow_day.{name}", (1024, 600))

        sky = layer("sky")
        if sky is None:
            surface.fill((207, 234, 247))
        else:
            surface.blit(sky, (0, 0))
        ground = layer("ground")
        grass_bottom = ground.get_at((size[0] // 2, size[1] - 4))[:3] if ground is not None else (98, 188, 114)
        surface.fill(grass_bottom, pygame.Rect(0, size[1] // 2, size[0], size[1] - size[1] // 2))
        for name, shift in (("far", HILLS_SHIFT), ("mid", HILLS_SHIFT), ("ground", GROUND_SHIFT)):
            image = ground if name == "ground" else layer(name)
            if image is not None:
                surface.blit(image, (0, shift))
        foreground = layer("foreground")
        if foreground is not None:
            # Keep the bush and tufts behind Dani; the tree would hide the crate.
            surface.blit(foreground, (0, 0), pygame.Rect(0, 0, FOREGROUND_WIDTH, size[1]))
        loader.clear()
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        return surface

    def cast_pose(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self._art.image(f"character.{character}", height, variant=variant)


ArtFactory = Callable[[ControlPainter], GardenArt]

__all__ = ["ArtFactory", "BADGE_SIZE", "CARD_SIZE", "CLOSE_CARD_SIZE", "GardenArt", "WELL_ITEM_SIZE"]
