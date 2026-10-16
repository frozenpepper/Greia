"""Prepared, bounded art for Quattro Amici in Fila.

Everything is loaded, painted and scaled once:

* the opaque *stage scene* — shared ``bg.meadow_day`` layers plus this
  stage's board stand, contact shadow and hole wells — is one blit per frame;
* the board's front plate (holes cut out) is painted with the kit recipe at
  2x and smooth-scaled once per stage, so discs sit *inside* the board;
* discs are this package's ``assets/runtime/token_{carrot,acorn}.png``
  (shared-library candidates ``prop.token.*``), scaled once per size;
* cast poses, HUD glyphs, FX and the hand prop come from the shared library.

Drawing code only blits these surfaces. Caches are small and hard-bounded.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlPainter, mix

if __package__:
    from .quattro_content import (
        CREAM,
        INK,
        PLAYER_ACCENT,
        SAND,
        SAND_LIGHT,
        SAND_SHADE,
        SAND_WELL,
        SHADOW,
        SUNSHINE,
        SUNSHINE_LIGHT,
        WOOD,
        Player,
    )
    from .quattro_layout import FEET_HEIGHT, PLATE_SIZE, BoardGeometry
else:
    from quattro_content import (
        CREAM,
        INK,
        PLAYER_ACCENT,
        SAND,
        SAND_LIGHT,
        SAND_SHADE,
        SAND_WELL,
        SHADOW,
        SUNSHINE,
        SUNSHINE_LIGHT,
        WOOD,
        Player,
    )
    from quattro_layout import FEET_HEIGHT, PLATE_SIZE, BoardGeometry

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"
TOKEN_FILES: Final[dict[Player, str]] = {Player.FLASH: "token_carrot.png", Player.LEO: "token_acorn.png"}
MEADOW_LAYERS: Final = ("sky", "far", "mid", "ground")
FX_SIZES: Final[dict[str, int]] = {"sparkle": 92, "star_burst": 150, "heart_pop": 110, "confetti": 300}
CACHE_LIMIT: Final = 24
_S: Final = 2  # supersample for painted shapes


def _store(cache: dict, key, value):
    if len(cache) >= CACHE_LIMIT:
        cache.pop(next(iter(cache)))
    cache[key] = value
    return value


class QuattroArt:
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
        self._size = size
        self.background = self._compose_background(size)
        self._token_sources = {player: self._load_private(name) for player, name in TOKEN_FILES.items()}
        self._tokens: dict[tuple[Player, int], pygame.Surface] = {}
        self._stage_key: tuple | None = None
        self.scene: pygame.Surface = self.background
        self.plate: pygame.Surface | None = None
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}
        self._misc: dict[tuple, pygame.Surface | None] = {}
        self._cast: dict[tuple, pygame.Surface | None] = {}
        self._plates: dict[tuple, pygame.Surface] = {}

    @property
    def art(self) -> ControlArt:
        return self._art

    # -- stage board -----------------------------------------------------------

    def prepare_stage(self, geometry: BoardGeometry) -> None:
        """Compose the opaque stage scene and the front plate (once per stage)."""

        key = (geometry.cols, geometry.rows, geometry.cell, tuple(geometry.frame))
        if key == self._stage_key:
            return
        self._stage_key = key
        scene = self.background.copy()
        frame = geometry.frame
        shadow = pygame.Surface((int(frame.width * 1.16), 30), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (*SHADOW, 44), shadow.get_rect())
        scene.blit(shadow, shadow.get_rect(center=(frame.centerx, frame.bottom + FEET_HEIGHT - 2)))
        foot_w = max(40, int(geometry.cell * 0.9))
        foot = self._painter.body(BodyShape.TILE, (foot_w, FEET_HEIGHT + 22), WOOD, contour_width=3, highlight=False)
        for x in (frame.left + geometry.cell // 2, frame.right - geometry.cell // 2 - foot_w):
            scene.blit(foot, (x, frame.bottom - 22))
        radius = geometry.hole_radius + 1
        for row in range(geometry.rows):
            for col in range(geometry.cols):
                center = geometry.cell_center(row, col)
                pygame.draw.circle(scene, mix(SAND_WELL, INK, 0.25), center, radius)
                lower = pygame.Rect(0, 0, int(radius * 1.5), int(radius * 0.9))
                lower.midbottom = (center[0], center[1] + radius - 3)
                pygame.draw.ellipse(scene, SAND_WELL, lower)
        self.scene = scene.convert() if pygame.display.get_surface() is not None else scene
        self.plate = self._paint_plate(geometry)
        self._misc = {k: v for k, v in self._misc.items() if k[0] not in {"glow", "ring"}}
        self._tokens.clear()

    def _paint_plate(self, geometry: BoardGeometry) -> pygame.Surface:
        frame = geometry.frame
        width, height = frame.width * _S, frame.height * _S
        canvas = pygame.Surface((width, height), pygame.SRCALPHA)
        stroke = 4 * _S
        radius = 26 * _S
        outer = canvas.get_rect()
        pygame.draw.rect(canvas, INK, outer, border_radius=radius)
        inner = outer.inflate(-2 * stroke, -2 * stroke)
        mask = pygame.Surface(inner.size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius - stroke)
        gradient = pygame.Surface(inner.size)
        span = max(1, inner.height - 1)
        for y in range(inner.height):
            pygame.draw.line(gradient, mix(SAND_LIGHT, SAND, min(1.0, y / span)), (0, y), (inner.width, y))
        mask.blit(gradient, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        canvas.blit(mask, inner.topleft)
        gloss = pygame.Surface((int(inner.width * 0.34), 7 * _S), pygame.SRCALPHA)
        pygame.draw.rect(gloss, (255, 255, 255, 120), gloss.get_rect(), border_radius=gloss.get_height() // 2)
        canvas.blit(gloss, (inner.left + radius // 2, inner.top + 5 * _S))
        bevel = inner.inflate(-10 * _S, -10 * _S)
        pygame.draw.rect(canvas, SAND_SHADE, bevel, width=2 * _S, border_radius=radius - 8 * _S)
        hole = geometry.hole_radius * _S
        rim = mix(SAND, INK, 0.55)
        for row in range(geometry.rows):
            for col in range(geometry.cols):
                cx, cy = geometry.cell_center(row, col)
                center = ((cx - frame.left) * _S, (cy - frame.top) * _S)
                pygame.draw.circle(canvas, SAND_SHADE, center, hole + 4 * _S)
                pygame.draw.circle(canvas, (0, 0, 0, 0), center, hole)
                pygame.draw.circle(canvas, rim, center, hole + 1 * _S, width=3 * _S)
        plate = pygame.transform.smoothscale(canvas, frame.size)
        return plate.convert_alpha() if pygame.display.get_surface() is not None else plate

    # -- discs -------------------------------------------------------------------

    def token(self, player: Player, size: int) -> pygame.Surface:
        key = (player, int(size))
        cached = self._tokens.get(key)
        if cached is not None:
            return cached
        source = self._token_sources.get(player)
        if source is not None:
            surface = pygame.transform.smoothscale(source, (int(size), int(size)))
        else:  # vector fallback keeps the game playable without the rendition
            surface = self._painter.body(BodyShape.ROUND, (int(size), int(size)), PLAYER_ACCENT[player])
        return _store(self._tokens, key, surface)

    def goal_icon(self, player: Player, target: int, height: int) -> pygame.Surface:
        """``target`` discs in a row on a golden band: the pictorial goal."""

        key = ("goal", player, target, height)
        cached = self._misc.get(key)
        if cached is not None:
            return cached
        disc = self.token(player, height)
        step = int(height * 0.78)
        width = step * (target - 1) + height
        icon = pygame.Surface((width, height), pygame.SRCALPHA)
        band = pygame.Rect(height // 2 - 4, height // 2 - height // 7, width - height + 8, 2 * (height // 7))
        pygame.draw.rect(icon, INK, band.inflate(4, 4), border_radius=band.height)
        pygame.draw.rect(icon, SUNSHINE, band, border_radius=band.height)
        for index in range(target):
            icon.blit(disc, (index * step, 0))
        return _store(self._misc, key, icon)

    # -- cast and HUD ------------------------------------------------------------

    def cast(self, player: Player, variant: str, height: int, *, mirrored: bool = False) -> pygame.Surface | None:
        key = (player, variant, height, mirrored)
        if key in self._cast:
            return self._cast[key]
        image = self._art.image(f"character.{player.cast_id}", height, variant=variant)
        if image is not None and mirrored:
            image = pygame.transform.flip(image, True, False)
        return _store(self._cast, key, image)

    def glyph(self, name: str, size: int) -> pygame.Surface | None:
        key = ("glyph", name, size)
        if key not in self._misc:
            _store(self._misc, key, self._art.image(f"icon.hud.{name}", size))
        return self._misc[key]

    def mode_icon(self, two_players: bool, height: int) -> pygame.Surface:
        """Leo (he plays himself) or two hands (two friends play)."""

        key = ("mode_two" if two_players else "mode_vs", height)
        cached = self._misc.get(key)
        if cached is not None:
            return cached
        icon = pygame.Surface((int(height * 1.2), height), pygame.SRCALPHA)
        if two_players:
            hand = self._art.image("prop.vocab.hand", int(height * 0.86))
            if hand is not None:
                icon.blit(pygame.transform.flip(hand, True, False), (0, height - hand.get_height()))
                icon.blit(hand, (icon.get_width() - hand.get_width(), height - hand.get_height()))
        else:
            leo = self._art.image("character.leo", int(height * 1.12))
            if leo is not None:
                icon.blit(leo, leo.get_rect(midbottom=(icon.get_width() // 2, height + int(height * 0.07))))
        return _store(self._misc, key, icon)

    def spotlight(self, width: int) -> pygame.Surface:
        """Soft sunny pool under the friend whose turn it is."""

        key = ("spot", width)
        cached = self._misc.get(key)
        if cached is None:
            cached = pygame.Surface((width, max(18, width // 5)), pygame.SRCALPHA)
            rect = cached.get_rect()
            pygame.draw.ellipse(cached, (*SUNSHINE_LIGHT, 120), rect)
            pygame.draw.ellipse(cached, (*SUNSHINE, 150), rect, width=3)
            _store(self._misc, key, cached)
        return cached

    def score_plate(self, player: Player, wins: int, needed: int, active: bool) -> pygame.Surface:
        """Cream plate: the friend's disc, then one star per win needed."""

        key = (player, wins, needed, active)
        cached = self._plates.get(key)
        if cached is not None:
            return cached
        width, height = PLATE_SIZE
        contour = PLAYER_ACCENT[player] if active else None
        plate = self._painter.body(
            BodyShape.PILL, (width, height), CREAM, lip=4, contour=contour, contour_width=4 if active else 3
        ).copy()
        disc = self.token(player, height - 18)
        plate.blit(disc, (10, (height - 4 - disc.get_height()) // 2))
        star_size = height - 22
        x = 10 + disc.get_width() + 8
        for index in range(needed):
            star = self._star(star_size, index < wins)
            plate.blit(star, (x, (height - 4 - star.get_height()) // 2))
            x += star_size + 4
        return _store(self._plates, key, plate)

    def _star(self, size: int, filled: bool) -> pygame.Surface:
        key = ("star", size, filled)
        if key not in self._misc:
            image = self._art.image("ui.control.star", size, variant="default" if filled else "off")
            _store(self._misc, key, image if image is not None else self._painter.star(size, filled=filled))
        return self._misc[key]  # type: ignore[return-value]

    # -- highlights --------------------------------------------------------------

    def column_glow(self, geometry: BoardGeometry) -> pygame.Surface:
        """Golden column halo for graduated hints."""

        rect = geometry.column_rect(0)
        key = ("glow", rect.width, rect.height)
        cached = self._misc.get(key)
        if cached is None:
            cached = pygame.Surface(rect.size, pygame.SRCALPHA)
            body = cached.get_rect().inflate(-6, -6)
            pygame.draw.rect(cached, (*SUNSHINE_LIGHT, 92), body, border_radius=body.width // 2)
            pygame.draw.rect(cached, (*SUNSHINE, 220), body, width=4, border_radius=body.width // 2)
            _store(self._misc, key, cached)
        return cached

    def win_ring(self, geometry: BoardGeometry) -> pygame.Surface:
        size = geometry.token_size + 18
        key = ("ring", size)
        cached = self._misc.get(key)
        if cached is None:
            big = pygame.Surface((size * _S, size * _S), pygame.SRCALPHA)
            center = (size * _S // 2, size * _S // 2)
            pygame.draw.circle(big, INK, center, size * _S // 2)
            pygame.draw.circle(big, SUNSHINE, center, size * _S // 2 - 3 * _S)
            pygame.draw.circle(big, (255, 255, 255), center, size * _S // 2 - 7 * _S)
            pygame.draw.circle(big, (0, 0, 0, 0), center, size * _S // 2 - 9 * _S)
            cached = pygame.transform.smoothscale(big, (size, size))
            _store(self._misc, key, cached)
        return cached

    def win_band(self, geometry: BoardGeometry, cells: list[tuple[int, int]]) -> pygame.Surface:
        """Golden band through the winning discs (built once per win)."""

        frame = geometry.frame
        band = pygame.Surface(frame.size, pygame.SRCALPHA)
        points = [geometry.cell_center(r, c) for r, c in cells]
        points = [(x - frame.left, y - frame.top) for x, y in points]
        width = max(6, int(geometry.cell * 0.1))
        start, end = points[0], points[-1]
        for color, w in ((INK, width + 4), (SUNSHINE, width)):
            pygame.draw.line(band, color, start, end, w)
            for point in (start, end):
                pygame.draw.circle(band, color, point, w // 2 + 1)
        return band

    # -- FX ------------------------------------------------------------------------

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

    # -- loading ------------------------------------------------------------------

    def _load_private(self, name: str) -> pygame.Surface | None:
        try:
            image = pygame.image.load(str(self._runtime_dir / name))
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
        except (OSError, pygame.error):
            return None
        return image

    def _compose_background(self, size: tuple[int, int]) -> pygame.Surface:
        surface = pygame.Surface(size)
        surface.fill((207, 234, 247))
        loader = ControlArt(max_entries=6)  # throwaway: layers are released after compositing
        for name in MEADOW_LAYERS:
            image = loader.image(f"bg.meadow_day.{name}", size)
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        return surface


__all__ = ["QuattroArt", "TOKEN_FILES"]
