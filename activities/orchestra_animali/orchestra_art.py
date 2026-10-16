"""Prepared, bounded art for the Animal Band stage.

Everything is resolved semantically from the shared library and scaled once:
the stage (``bg.stage.*`` layers) with the rainbow xylophone baked in, the six
canonical musicians (``character.<id>`` ``happy`` / ``pose_play`` /
``pose_point`` / ``pose_wave``), their ``prop.instrument.*`` props, FX
(``fx.note_burst``, ``fx.beat_ring``, ``fx.sparkle``, ``fx.star_burst``) and
HUD glyphs. Xylophone bars, rails and the speech bubble are painted once with
the shared control-kit recipe. Drawing code only blits these surfaces.
"""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlPainter, mix

if __package__:
    from .orchestra_content import BAND, REFERENCE_HEIGHT, REFERENCE_WIDTH, XYLOPHONE_COLORS
    from .orchestra_layout import (
        BAR_RECTS,
        BUBBLE_HEIGHT,
        BUBBLE_ICON,
        BUBBLE_TOKEN,
        CAST_HEIGHT,
        INSTRUMENT_SIZE,
        XYLOPHONE_FRAME,
    )
else:  # pragma: no cover - runtime/script fallback
    from orchestra_content import BAND, REFERENCE_HEIGHT, REFERENCE_WIDTH, XYLOPHONE_COLORS
    from orchestra_layout import (
        BAR_RECTS,
        BUBBLE_HEIGHT,
        BUBBLE_ICON,
        BUBBLE_TOKEN,
        CAST_HEIGHT,
        INSTRUMENT_SIZE,
        XYLOPHONE_FRAME,
    )

STAGE_LAYERS: Final = (
    "bg.stage.wall_dark",
    "bg.stage.boards",
    "bg.stage.curtain_left",
    "bg.stage.curtain_right",
    "bg.stage.valance",
)
POSES: Final = ("happy", "pose_play", "pose_point", "pose_wave")
FX_SIZES: Final[dict[str, int]] = {
    "note_burst": 112,
    "note_burst_soft": 72,
    "beat_ring": 150,
    "sparkle": 110,
    "star_burst": 176,
}
TOGGLE_ICONS: Final[dict[str, str]] = {
    "soft": "prop.vocab.mouse",
    "loud": "prop.vocab.lion",
    "slow": "prop.vocab.snail",
    "fast": "prop.vocab.horse",
}
COCOA: Final = (61, 44, 31)
CREAM: Final = (255, 251, 235)
WOOD: Final = (186, 124, 74)
SPOT: Final = (255, 236, 170)
BUBBLE_CACHE: Final = 8


class OrchestraArt:
    """Own every prepared surface the renderer blits (bounded, built once)."""

    def __init__(
        self,
        painter: ControlPainter,
        *,
        art: ControlArt | None = None,
        size: tuple[int, int] = (REFERENCE_WIDTH, REFERENCE_HEIGHT),
    ) -> None:
        self._painter = painter
        # Content art gets its own bounded cache so it never evicts kit glyphs.
        self.art = art if art is not None else ControlArt(max_entries=64)
        self._size = size
        self.poses: dict[tuple[int, str], pygame.Surface | None] = {
            (index, pose): self.art.image(musician.character_id, CAST_HEIGHT, variant=pose)
            for index, musician in enumerate(BAND)
            for pose in POSES
        }
        self.instruments: tuple[pygame.Surface | None, ...] = tuple(
            self.art.image(musician.prop_id, INSTRUMENT_SIZE) for musician in BAND
        )
        self.tokens: tuple[pygame.Surface | None, ...] = tuple(
            self.art.image(musician.prop_id, BUBBLE_TOKEN) for musician in BAND
        )
        self.bar_token = self._bar_token()
        self.bar_lit: tuple[pygame.Surface, ...] = tuple(
            self._bar(index, rect.size, lit=True) for index, rect in enumerate(BAR_RECTS)
        )
        self.listen_icon = self.art.image("icon.hud.ear", BUBBLE_ICON)
        self.go_icon = self.art.image("icon.hud.go", BUBBLE_ICON)
        self.spotlight = self._spotlight()
        self.bubble_tail = self._bubble_tail()
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}
        self._bubbles: dict[int, pygame.Surface] = {}
        self.background = self._compose_background()

    # -- shared library ------------------------------------------------------------

    def pose(self, index: int, pose: str) -> pygame.Surface | None:
        return self.poses.get((index, pose)) or self.poses.get((index, "happy"))

    def toggle_icon(self, name: str, size: int) -> pygame.Surface | None:
        return self.art.image(TOGGLE_ICONS[name], size)

    def fx_frames(self, name: str) -> tuple[pygame.Surface, ...]:
        cached = self._fx.get(name)
        if cached is not None:
            return cached
        size = FX_SIZES.get(name, 128)
        asset = "fx.note_burst" if name == "note_burst_soft" else f"fx.{name}"
        frames = []
        for variant in ("default", "frame_2", "frame_3"):
            image = self.art.image(asset, size, variant=variant)
            if image is not None:
                frames.append(image)
        self._fx[name] = tuple(frames)
        return self._fx[name]

    # -- painted content -------------------------------------------------------------

    def bubble(self, width: int) -> pygame.Surface:
        """A cream speech-bubble panel (cached per width; tail drawn separately)."""

        width = max(BUBBLE_HEIGHT, int(width))
        cached = self._bubbles.get(width)
        if cached is not None:
            return cached
        if len(self._bubbles) >= BUBBLE_CACHE:
            self._bubbles.pop(next(iter(self._bubbles)))
        surface = self._painter.body(BodyShape.PANEL, (width, BUBBLE_HEIGHT), CREAM, contour_width=4)
        self._bubbles[width] = surface
        return surface

    def _bubble_tail(self) -> pygame.Surface:
        """Tail that points from the bubble down at the inviting musician."""

        tail = pygame.Surface((44, 34), pygame.SRCALPHA)
        pygame.draw.polygon(tail, COCOA, [(2, 0), (42, 0), (22, 33)])
        pygame.draw.polygon(tail, CREAM, [(9, 0), (35, 0), (22, 24)])
        return tail

    def _bar(self, index: int, size: tuple[int, int], *, lit: bool) -> pygame.Surface:
        base = XYLOPHONE_COLORS[index]
        fill = mix(base, (255, 255, 255), 0.45) if lit else base
        surface = self._painter.body(BodyShape.TILE, size, fill, contour_width=3).copy()
        # Two little nails where the bar rests on the rails.
        for y in (int(size[1] * 0.22), int(size[1] * 0.78)):
            pygame.draw.circle(surface, mix(fill, COCOA, 0.55), (size[0] // 2, y), 5)
            pygame.draw.circle(surface, COCOA, (size[0] // 2, y), 5, 2)
        return surface

    def _bar_token(self) -> pygame.Surface:
        """Tiny rainbow xylophone for the echo bubble."""

        size = BUBBLE_TOKEN
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        bar_w = size // 5
        for slot, color_index in enumerate((0, 2, 4, 6)):
            height = int(size * (0.86 - slot * 0.1))
            rect = pygame.Rect(2 + slot * (bar_w + 2), (size - height) // 2, bar_w, height)
            body = self._painter.body(BodyShape.TILE, rect.size, XYLOPHONE_COLORS[color_index], contour_width=2, highlight=False)
            surface.blit(body, rect)
        return surface

    def _spotlight(self) -> pygame.Surface:
        surface = pygame.Surface((220, 60), pygame.SRCALPHA)
        for step in range(6):
            alpha = 26 + step * 14
            rect = pygame.Rect(0, 0, 220 - step * 30, 60 - step * 8)
            rect.center = (110, 30)
            pygame.draw.ellipse(surface, (*SPOT, alpha), rect)
        return surface

    def _compose_background(self) -> pygame.Surface:
        surface = pygame.Surface(self._size)
        surface.fill((58, 40, 74))
        # A throwaway loader: the five full-screen layers are released once
        # composed instead of staying in the long-lived content cache.
        layers = ControlArt(max_entries=1)
        for layer in STAGE_LAYERS:
            image = layers.image(layer, self._size)
            if image is not None:
                surface.blit(image, (0, 0))
        layers.clear()
        self._draw_xylophone(surface)
        try:
            if pygame.display.get_surface() is not None:
                surface = surface.convert()
        except pygame.error:
            pass
        return surface

    def _draw_xylophone(self, surface: pygame.Surface) -> None:
        frame = XYLOPHONE_FRAME
        shadow = pygame.Surface((frame.width + 30, 26), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (40, 24, 20, 90), shadow.get_rect())
        surface.blit(shadow, (frame.x - 15, frame.bottom + 6))
        for y in (frame.top, frame.bottom - 18):
            rail = self._painter.body(BodyShape.PILL, (frame.width, 18), WOOD, contour_width=3)
            surface.blit(rail, (frame.x, y))
        for index, rect in enumerate(BAR_RECTS):
            surface.blit(self._bar(index, rect.size, lit=False), rect)


__all__ = ["OrchestraArt", "POSES", "TOGGLE_ICONS"]
