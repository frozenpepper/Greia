"""Shape Garden presentation: layout, composed garden, gallery and sheets.

Everything is drawn on the 1024x600 reference canvas. Static parts (studio
background, tray panel, paint shelf, garden frame) are built once; the
garden picture itself is composed into one view-sized surface only when its
content changes (``GardenComposer``) and blitted per frame. The dragged
shape, selection ring, cast, hints and FX are the only per-frame extras.

Interactive controls are kit controls (``garden_controls``); this module
provides their rectangles and the Activity-drawn art beneath them.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Sequence
import math
from pathlib import Path
import time

import pygame

from greia_platform.activity_controls import BodyShape, ControlKit, mix
from greia_platform.pygame_png import decode_png_surface

if __package__:
    from .garden_art import BackdropArt, ShapeArt, box_side
    from .garden_content import (
        BIN_TILE,
        COLOUR_IDS,
        COLOURS,
        DANI_MIDBOTTOM,
        GALLERY_PAGE_SIZE,
        GARDEN_HEIGHT,
        GARDEN_VIEW,
        GARDEN_WIDTH,
        LEFT_COLUMN_X,
        PICTURE_BACKDROP,
        POT_DIAMETER,
        RIGHT_COLUMN_X,
        COLUMN_WIDTH,
        SHAPE_KINDS,
        TOOL_TILE,
        TRAY_GAP,
        TRAY_PANEL,
        TRAY_TILE,
        GhostPicture,
    )
    from .garden_model import GardenState, PlacedShape
else:  # pragma: no cover - direct script fallback
    from garden_art import BackdropArt, ShapeArt, box_side
    from garden_content import (
        BIN_TILE,
        COLOUR_IDS,
        COLOURS,
        DANI_MIDBOTTOM,
        GALLERY_PAGE_SIZE,
        GARDEN_HEIGHT,
        GARDEN_VIEW,
        GARDEN_WIDTH,
        LEFT_COLUMN_X,
        PICTURE_BACKDROP,
        POT_DIAMETER,
        RIGHT_COLUMN_X,
        COLUMN_WIDTH,
        SHAPE_KINDS,
        TOOL_TILE,
        TRAY_GAP,
        TRAY_PANEL,
        TRAY_TILE,
        GhostPicture,
    )
    from garden_model import GardenState, PlacedShape

ASSET_DIR = Path(__file__).parent / "assets" / "runtime"
INK = (75, 55, 47)
PAPER = (255, 251, 240)
STUDIO_TOP = (252, 246, 232)
STUDIO_BOTTOM = (246, 236, 214)
CORAL = (244, 111, 97)
LEAF = (89, 184, 106)
SUNSHINE = (255, 194, 52)
WHITE = (255, 255, 255)


class GardenComposer:
    """Draw one ``GardenState`` (backdrop, free ghost slots, shapes) at a scale.

    The same code produces the on-screen view, the gallery thumbnails and the
    1024x600 PNG that is shared, so what the child sees is what gets saved.
    """

    def __init__(self, shapes: ShapeArt, backdrops: BackdropArt) -> None:
        self.shapes = shapes
        self.backdrops = backdrops

    def compose(
        self,
        state: GardenState,
        size: tuple[int, int],
        *,
        picture: pygame.Surface | None = None,
        ghost: GhostPicture | None = None,
        filled: Sequence[bool] = (),
        skip: int | None = None,
    ) -> pygame.Surface:
        width, height = int(size[0]), int(size[1])
        scale = width / GARDEN_WIDTH
        if state.backdrop == PICTURE_BACKDROP and picture is not None:
            base = picture if picture.get_size() == (width, height) else pygame.transform.smoothscale(picture, (width, height))
            surface = base.copy()
        else:
            backdrop = state.backdrop if state.backdrop != PICTURE_BACKDROP else "paper"
            surface = self.backdrops.scaled(backdrop, (width, height)).copy()
        if ghost is not None:
            for index, slot in enumerate(ghost.slots):
                if index < len(filled) and filled[index]:
                    continue
                image = self.shapes.image(slot.kind, "slot", box_side(slot.size, scale), slot.turn)
                if image is not None:
                    surface.blit(image, image.get_rect(center=(round(slot.x * scale), round(slot.y * scale))))
        for index, shape in enumerate(state.shapes):
            if index != skip:
                self.draw_shape(surface, shape, scale, (0, 0))
        return surface

    def draw_shape(
        self,
        target: pygame.Surface,
        shape: PlacedShape,
        scale: float,
        origin: tuple[int, int],
        *,
        lift: float = 0.0,
    ) -> pygame.Rect | None:
        side = box_side(shape.size, scale * (1.0 + lift))
        image = self.shapes.image(shape.kind, shape.colour, side, shape.turn)
        if image is None:
            return None
        centre = (origin[0] + round(shape.x * scale), origin[1] + round(shape.y * scale))
        rect = image.get_rect(center=centre)
        target.blit(image, rect)
        return rect


class FxBurst:
    """One short shared-library FX animation (frames scaled once)."""

    DURATION = 0.7

    def __init__(self, frames: list[pygame.Surface], center: tuple[int, int], *, clock=time.monotonic) -> None:
        self._frames = frames
        self._center = center
        self._clock = clock
        self._start = clock()

    @property
    def done(self) -> bool:
        return self._clock() - self._start >= self.DURATION

    def draw(self, target: pygame.Surface) -> None:
        if not self._frames or self.done:
            return
        progress = (self._clock() - self._start) / self.DURATION
        frame = self._frames[min(len(self._frames) - 1, int(progress * len(self._frames) * 2) % len(self._frames))]
        target.blit(frame, frame.get_rect(center=self._center))


class GardenRenderer:
    """Own Shape Garden geometry, static surfaces and bounded caches."""

    THUMBNAIL_LIMIT = 24

    def __init__(self, kit: ControlKit, *, shapes: ShapeArt | None = None, backdrops: BackdropArt | None = None) -> None:
        self.kit = kit
        self.shapes = shapes if shapes is not None else ShapeArt()
        self.backdrops = backdrops if backdrops is not None else BackdropArt()
        self.composer = GardenComposer(self.shapes, self.backdrops)
        self.view = pygame.Rect(GARDEN_VIEW)
        self.scale = self.view.width / GARDEN_WIDTH
        self.assets: dict[str, pygame.Surface] = {}
        self._static: dict[str, pygame.Surface] = {}
        self._garden: pygame.Surface | None = None
        self._garden_key: tuple | None = None
        self._status_icons: dict[str, pygame.Surface] = {}
        self._fx_frames: dict[tuple[str, int], list[pygame.Surface]] = {}
        self._dim: pygame.Surface | None = None
        self.thumbnail_cache: OrderedDict[str, pygame.Surface] = OrderedDict()
        self.top_bar = pygame.Rect(156, 12, 856, 64)
        self._load_assets()

    def _load_assets(self) -> None:
        for name in ("tool_gallery", "tool_ghost", "tool_grow", "tool_shrink", "tool_back"):
            path = ASSET_DIR / f"{name}.png"
            try:
                surface = pygame.image.load(str(path))
            except (pygame.error, FileNotFoundError, OSError):
                continue
            self.assets[name] = surface.convert_alpha() if pygame.display.get_surface() is not None else surface

    def icon(self, name: str, size: int) -> pygame.Surface | None:
        source = self.assets.get(name)
        if source is None:
            return None
        return source if source.get_width() == size else pygame.transform.smoothscale(source, (size, size))

    def set_top_bar(self, bar: pygame.Rect) -> None:
        """Top bar from the kit layout (right of the protected Home/Back)."""
        if pygame.Rect(bar) != self.top_bar:
            self.top_bar = pygame.Rect(bar)
            self._static.clear()

    # -- geometry -------------------------------------------------------------

    def to_screen(self, point: tuple[float, float]) -> tuple[int, int]:
        return (self.view.x + round(point[0] * self.scale), self.view.y + round(point[1] * self.scale))

    def to_garden(self, point: tuple[float, float]) -> tuple[float, float]:
        return ((point[0] - self.view.x) / self.scale, (point[1] - self.view.y) / self.scale)

    def toolbar_rects(self) -> dict[str, pygame.Rect]:
        bar = self.top_bar
        size = bar.height
        gap = 10
        left = [pygame.Rect(bar.left + i * (size + gap), bar.top, size, size) for i in range(2)]
        right = [pygame.Rect(bar.right - (3 - i) * size - (2 - i) * gap, bar.top, size, size) for i in range(3)]
        share = pygame.Rect(0, bar.top, size, size)
        share.centerx = (left[1].right + right[0].left) // 2
        return {
            "gallery": left[0], "undo": left[1], "share": share,
            "backdrop": right[0], "ghost": right[1], "new": right[2],
        }

    def status_rect(self) -> pygame.Rect:
        anchor = self.toolbar_rects()["backdrop"]
        rect = pygame.Rect(0, 0, 30, 30)
        rect.midright = (anchor.left - 14, anchor.centery)
        return rect

    def pot_rects(self) -> list[pygame.Rect]:
        """Natural (rainbow) pot on top, then two columns of three accents."""
        d = POT_DIAMETER
        cx = LEFT_COLUMN_X + COLUMN_WIDTH // 2
        rects = [pygame.Rect(cx - d // 2, 108, d, d)]
        for index in range(len(COLOUR_IDS) - 1):
            row, col = divmod(index, 2)
            x = cx - d - 8 if col == 0 else cx + 8
            rects.append(pygame.Rect(x, 108 + (row + 1) * (d + 14), d, d))
        return rects

    def shelf_rect(self) -> pygame.Rect:
        pots = self.pot_rects()
        top = pots[0].top - 12
        bottom = pots[-1].bottom + 16
        return pygame.Rect(LEFT_COLUMN_X + 6, top, COLUMN_WIDTH - 12, bottom - top)

    def tool_rects(self) -> dict[str, pygame.Rect]:
        x = RIGHT_COLUMN_X + (COLUMN_WIDTH - TOOL_TILE) // 2
        names = ("grow", "shrink", "turn", "back")
        return {
            name: pygame.Rect(x, 104 + index * (TOOL_TILE + 12), TOOL_TILE, TOOL_TILE)
            for index, name in enumerate(names)
        }

    def bin_rect(self) -> pygame.Rect:
        rect = pygame.Rect(0, 0, BIN_TILE, BIN_TILE)
        rect.midbottom = (RIGHT_COLUMN_X + COLUMN_WIDTH // 2, TRAY_PANEL[1] + TRAY_PANEL[3] - 2)
        return rect

    def tray_rect(self) -> pygame.Rect:
        return pygame.Rect(TRAY_PANEL)

    def tray_tiles(self) -> list[pygame.Rect]:
        tray = self.tray_rect()
        count = len(SHAPE_KINDS)
        total = count * TRAY_TILE + (count - 1) * TRAY_GAP
        left = tray.centerx - total // 2
        top = tray.centery - TRAY_TILE // 2 - 2
        return [pygame.Rect(left + i * (TRAY_TILE + TRAY_GAP), top, TRAY_TILE, TRAY_TILE) for i in range(count)]

    def gallery_area(self) -> pygame.Rect:
        return pygame.Rect(LEFT_COLUMN_X + 4, self.view.top, 1000 - 8, self.view.height)

    @staticmethod
    def gallery_page_count(count: int) -> int:
        return max(1, -(-int(count) // GALLERY_PAGE_SIZE))

    def gallery_cards(self, count: int, page: int) -> list[pygame.Rect]:
        area = self.gallery_area()
        gap = 18
        card_w = (area.width - 2 * gap) // 3
        card_h = (area.height - gap) // 2
        page = max(0, min(int(page), self.gallery_page_count(count) - 1))
        first = page * GALLERY_PAGE_SIZE
        rects = []
        for slot in range(max(0, min(GALLERY_PAGE_SIZE, count - first))):
            row, col = divmod(slot, 3)
            rects.append(pygame.Rect(area.left + col * (card_w + gap), area.top + row * (card_h + gap), card_w, card_h))
        return rects

    def card_thumb_rect(self, card: pygame.Rect) -> pygame.Rect:
        inner = card.inflate(-24, -28)
        height = min(inner.height, int(inner.width * GARDEN_HEIGHT / GARDEN_WIDTH))
        width = int(height * GARDEN_WIDTH / GARDEN_HEIGHT)
        rect = pygame.Rect(0, 0, width, height)
        rect.center = (card.centerx, card.centery - 2)
        return rect

    def gallery_nav_rects(self) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        """Previous, delete and next tiles in the tray band."""
        tray = self.tray_rect()
        y = tray.centery - 33
        previous = pygame.Rect(LEFT_COLUMN_X + 18, y, 96, 66)
        following = pygame.Rect(LEFT_COLUMN_X + 1000 - 18 - 96, y, 96, 66)
        delete = pygame.Rect(0, y, 66, 66)
        delete.midright = (following.left - 64, tray.centery)
        return previous, delete, following

    def sheet_tiles(self, count: int, columns: int, tile: tuple[int, int]) -> tuple[pygame.Rect, list[pygame.Rect]]:
        """A sheet panel centred on the garden with a grid of picture tiles."""
        pad, gap = 16, 12
        rows = -(-count // columns)
        width = columns * tile[0] + (columns - 1) * gap + 2 * pad
        height = rows * tile[1] + (rows - 1) * gap + 2 * pad
        panel = pygame.Rect(0, 0, width, height)
        panel.center = self.view.center
        tiles = []
        for index in range(count):
            row, col = divmod(index, columns)
            row_count = min(columns, count - row * columns)
            offset = (columns - row_count) * (tile[0] + gap) // 2
            tiles.append(pygame.Rect(panel.left + pad + offset + col * (tile[0] + gap), panel.top + pad + row * (tile[1] + gap), *tile))
        return panel, tiles

    def delete_dialog_rects(self) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect, pygame.Rect]:
        panel = pygame.Rect(0, 0, 520, 400)
        panel.center = (512, 316)
        preview = pygame.Rect(0, 0, 400, int(400 * GARDEN_HEIGHT / GARDEN_WIDTH))
        preview.midtop = (panel.centerx, panel.top + 22)
        button = 78
        y = panel.bottom - 20 - button
        cancel = pygame.Rect(panel.centerx - 20 - button, y, button, button)
        confirm = pygame.Rect(panel.centerx + 20, y, button, button)
        return panel, preview, cancel, confirm

    # -- static parts ------------------------------------------------------------

    def _panel(self, size: tuple[int, int], fill=PAPER, lip: int = 4) -> pygame.Surface:
        return self.kit.painter.body(BodyShape.PANEL, size, fill, lip=lip, highlight=False)

    def _build_static(self, size: tuple[int, int], mode: str) -> pygame.Surface:
        surface = pygame.Surface(size)
        span = max(1, size[1] - 1)
        for row in range(size[1]):
            pygame.draw.line(surface, mix(STUDIO_TOP, STUDIO_BOTTOM, row / span), (0, row), (size[0], row))
        line_y = self.top_bar.bottom + 8
        pygame.draw.line(surface, (236, 224, 200), (0, line_y), (size[0], line_y), 2)
        tray = self.tray_rect()
        if mode == "gallery":
            band = pygame.Rect(LEFT_COLUMN_X + 4, tray.top, 1000 - 8, tray.height)
            surface.blit(self._panel((band.width, band.height + 4)), band.topleft)
            return surface.convert() if pygame.display.get_surface() is not None else surface
        surface.blit(self._panel((tray.width, tray.height + 4)), tray.topleft)
        shelf = self.shelf_rect()
        surface.blit(self._panel((shelf.width, shelf.height + 4), fill=(255, 247, 228)), shelf.topleft)
        frame = self.view.inflate(14, 14)
        frame.height += 4
        surface.blit(self._panel(frame.size, fill=(110, 84, 68), lip=4), frame.topleft)
        return surface.convert() if pygame.display.get_surface() is not None else surface

    def draw_static(self, target: pygame.Surface, mode: str = "garden") -> None:
        cached = self._static.get(mode)
        if cached is None or cached.get_size() != target.get_size():
            cached = self._static[mode] = self._build_static(target.get_size(), mode)
        target.blit(cached, (0, 0))

    # -- garden ---------------------------------------------------------------------

    def draw_garden(
        self,
        target: pygame.Surface,
        key: tuple,
        state: GardenState,
        *,
        picture: pygame.Surface | None,
        ghost: GhostPicture | None,
        filled: Sequence[bool],
        skip: int | None,
    ) -> None:
        """Blit the composed garden, recomposing only when ``key`` changed."""
        if self._garden is None or key != self._garden_key:
            self._garden = self.composer.compose(
                state, self.view.size, picture=picture, ghost=ghost, filled=filled, skip=skip,
            )
            self._garden_key = key
        target.blit(self._garden, self.view.topleft)

    def invalidate_garden(self) -> None:
        self._garden = None
        self._garden_key = None

    def draw_lifted(self, target: pygame.Surface, shape: PlacedShape, lift: float = 0.08) -> None:
        """The dragged shape: a soft contact shadow and a slightly bigger body."""
        centre = self.to_screen((shape.x, shape.y))
        side = box_side(shape.size, self.scale)
        shadow = pygame.Rect(0, 0, int(side * 0.8), max(6, int(side * 0.18)))
        shadow.center = (centre[0] + 4, centre[1] + int(side * 0.48))
        layer = pygame.Surface(shadow.size, pygame.SRCALPHA)
        pygame.draw.ellipse(layer, (106, 81, 71, 60), layer.get_rect())
        target.blit(layer, shadow)
        clip = target.get_clip()
        target.set_clip(self.view.inflate(8, 8).union(self.tray_rect()).union(self.bin_rect()))
        self.composer.draw_shape(target, shape, self.scale, self.view.topleft, lift=lift)
        target.set_clip(clip)

    def draw_floating(
        self, target: pygame.Surface, kind: str, colour: str, size: int, turn: int, centre: tuple[int, int],
    ) -> None:
        """One shape centred on a screen point (dragged from the tray, over the bin, hints)."""
        image = self.shapes.image(kind, colour, box_side(size, self.scale), turn)
        if image is not None:
            target.blit(image, image.get_rect(center=centre))

    def shape_screen_rect(self, shape: PlacedShape) -> pygame.Rect:
        side = int(box_side(shape.size, self.scale) * 0.92)
        rect = pygame.Rect(0, 0, side, side)
        rect.center = self.to_screen((shape.x, shape.y))
        return rect.clip(self.view) if rect.colliderect(self.view) else rect

    def hit_shape(self, shapes: Sequence[PlacedShape], point: tuple[int, int]) -> int | None:
        """Topmost shape whose visible pixels are under ``point`` (screen space).

        Pixel test first so a tap on a thin rectangle beside a big circle picks
        what the child sees; then a forgiving radius for small fingers.
        """
        if not self.view.collidepoint(point):
            return None
        for index in range(len(shapes) - 1, -1, -1):
            shape = shapes[index]
            image = self.shapes.image(shape.kind, shape.colour, box_side(shape.size, self.scale), shape.turn)
            if image is None:
                continue
            rect = image.get_rect(center=self.to_screen((shape.x, shape.y)))
            if rect.collidepoint(point) and image.get_at((point[0] - rect.x, point[1] - rect.y)).a > 40:
                return index
        garden_point = self.to_garden(point)
        best: tuple[float, int] | None = None
        for index, shape in enumerate(shapes):
            reach = shape.box * 0.5 + 14 / self.scale
            distance = math.hypot(garden_point[0] - shape.x, garden_point[1] - shape.y)
            if distance <= reach and (best is None or distance <= best[0]):
                best = (distance, index)
        return best[1] if best is not None else None

    def draw_selection(self, target: pygame.Surface, shape: PlacedShape, now: float) -> None:
        centre = self.to_screen((shape.x, shape.y))
        radius = int(box_side(shape.size, self.scale) * 0.56) + 6
        pulse = int(2 * math.sin(now * 5.0))
        pygame.draw.circle(target, INK, centre, radius + 4 + pulse, 2)
        pygame.draw.circle(target, SUNSHINE, centre, radius + 2 + pulse, 4)
        pygame.draw.circle(target, INK, centre, radius - 1 + pulse, 1)

    # -- pots, tray, status ------------------------------------------------------------

    def draw_pots(self, target: pygame.Surface, selected: str) -> None:
        for rect, colour_id in zip(self.pot_rects(), COLOUR_IDS):
            chosen = colour_id == selected
            centre = (rect.centerx, rect.centery - (4 if chosen else 0))
            radius = rect.width // 2
            pygame.draw.circle(target, (226, 214, 190), (centre[0] + 2, centre[1] + 4), radius)
            if colour_id == "natural":
                self._rainbow_pot(target, centre, radius)
            else:
                colour = COLOURS[colour_id]
                pygame.draw.circle(target, INK, centre, radius)
                pygame.draw.circle(target, colour, centre, radius - 3)
                gloss = pygame.Rect(0, 0, radius, max(4, radius // 2))
                gloss.center = (centre[0] - radius // 4, centre[1] - radius // 2 + 2)
                pygame.draw.ellipse(target, mix(colour, WHITE, 0.55), gloss)
            if chosen:
                ring = radius + 6
                pygame.draw.circle(target, INK, centre, ring + 2, 3)
                pygame.draw.circle(target, SUNSHINE, centre, ring, 4)

    def _rainbow_pot(self, target: pygame.Surface, centre: tuple[int, int], radius: int) -> None:
        pygame.draw.circle(target, INK, centre, radius)
        accents = [COLOURS[c] for c in COLOUR_IDS[1:]]
        inner = radius - 3
        steps = len(accents)
        for index, colour in enumerate(accents):
            start = -math.pi / 2 + index * math.tau / steps
            end = start + math.tau / steps
            points = [centre]
            for k in range(7):
                angle = start + (end - start) * k / 6
                points.append((centre[0] + math.cos(angle) * inner, centre[1] + math.sin(angle) * inner))
            pygame.draw.polygon(target, colour, points)
        pygame.draw.circle(target, WHITE, centre, max(3, radius // 3))
        pygame.draw.circle(target, INK, centre, max(3, radius // 3), 2)

    def draw_status(self, target: pygame.Surface, state: str) -> None:
        icon = self._status_icons.get(state)
        if icon is None:
            icon = self._status_icons[state] = self._build_status_icon(state)
        target.blit(icon, icon.get_rect(center=self.status_rect().center))

    @staticmethod
    def _build_status_icon(state: str) -> pygame.Surface:
        """Word-free save state: green tick, amber dots or coral "!" (2x supersampled)."""
        size, s = 30, 2
        big = pygame.Surface((size * s, size * s), pygame.SRCALPHA)
        c = size * s // 2
        fill = {"saved": LEAF, "saving": SUNSHINE, "error": CORAL}[state]
        pygame.draw.circle(big, INK, (c, c), c)
        pygame.draw.circle(big, fill, (c, c), c - 5)
        u = s
        if state == "saved":
            pygame.draw.lines(big, WHITE, False, [(c - 7 * u, c), (c - 2 * u, c + 5 * u), (c + 7 * u, c - 5 * u)], 4 * u)
        elif state == "saving":
            for dx in (-7, 0, 7):
                pygame.draw.circle(big, WHITE, (c + dx * u, c), int(2.6 * u))
        else:
            pygame.draw.rect(big, WHITE, (c - 2 * u, c - 9 * u, 4 * u, 11 * u), border_radius=2 * u)
            pygame.draw.circle(big, WHITE, (c, c + 7 * u), int(2.4 * u))
        return pygame.transform.smoothscale(big, (size, size))

    def draw_full_badge(self, target: pygame.Surface, anchor: pygame.Rect) -> None:
        """Word-free "this shelf is full" badge: six filled cells and a "!"."""
        badge = pygame.Rect(0, 0, 150, 48)
        badge.center = anchor.center
        target.blit(self.kit.painter.body(BodyShape.PILL, badge.size, (250, 214, 208), lip=0, highlight=False), badge.topleft)
        cell = 11
        x0 = badge.left + 20
        for index in range(6):
            row, col = divmod(index, 3)
            pygame.draw.rect(target, CORAL, (x0 + col * (cell + 3), badge.centery - cell - 1 + row * (cell + 3), cell, cell), border_radius=2)
        cx = badge.right - 30
        pygame.draw.circle(target, INK, (cx, badge.centery), 15)
        pygame.draw.circle(target, CORAL, (cx, badge.centery), 13)
        pygame.draw.rect(target, PAPER, (cx - 2, badge.centery - 8, 5, 10), border_radius=2)
        pygame.draw.circle(target, PAPER, (cx, badge.centery + 7), 3)

    # -- gallery -------------------------------------------------------------------------

    def thumbnail(self, garden_id: str, render) -> pygame.Surface | None:
        """Cached gallery picture of one garden (``render`` builds it once)."""
        cached = self.thumbnail_cache.get(garden_id)
        if cached is not None:
            self.thumbnail_cache.move_to_end(garden_id)
            return cached
        surface = render()
        if surface is None:
            return None
        self.thumbnail_cache[garden_id] = surface
        while len(self.thumbnail_cache) > self.THUMBNAIL_LIMIT:
            self.thumbnail_cache.popitem(last=False)
        return surface

    def invalidate_thumbnail(self, garden_id: str | None) -> None:
        if garden_id is not None:
            self.thumbnail_cache.pop(garden_id, None)

    def draw_gallery(
        self,
        target: pygame.Surface,
        cards: Sequence[pygame.Rect],
        thumbs: Sequence[pygame.Surface | None],
        focus_slot: int | None,
        *,
        page: int,
        page_count: int,
        library_full: bool,
    ) -> None:
        if not cards:
            self._draw_empty_gallery(target)
        for slot, (card, thumb) in enumerate(zip(cards, thumbs)):
            selected = slot == focus_slot
            target.blit(self.kit.painter.body(BodyShape.TILE, card.size, SUNSHINE if selected else PAPER, lip=5), card.topleft)
            inner = self.card_thumb_rect(card)
            if thumb is not None:
                target.blit(thumb, inner)
            else:
                pygame.draw.rect(target, PAPER, inner)
            pygame.draw.rect(target, INK, inner, width=2)
        previous, _delete, following = self.gallery_nav_rects()
        left = previous.right + 16
        if library_full:
            badge = pygame.Rect(left, previous.top, 150, previous.height)
            self.draw_full_badge(target, badge)
            left = badge.right + 16
        if page_count > 1:
            dot, gap = 9, 12
            delete = self.gallery_nav_rects()[1]
            total = page_count * dot * 2 + (page_count - 1) * gap
            x = left + max(0, (delete.left - 16 - left - total) // 2) + dot
            for index in range(page_count):
                current = index == page
                radius = dot if current else dot - 2
                pygame.draw.circle(target, INK, (x, previous.centery), radius)
                pygame.draw.circle(target, CORAL if current else (236, 224, 200), (x, previous.centery), radius - 2)
                x += dot * 2 + gap

    def _draw_empty_gallery(self, target: pygame.Surface) -> None:
        area = self.gallery_area()
        card = pygame.Rect(0, 0, area.width // 3, area.height * 2 // 3)
        card.center = area.center
        target.blit(self.kit.painter.body(BodyShape.TILE, card.size, PAPER, lip=5), card.topleft)
        flower = self.shapes.image("heart", "coral", min(card.width, card.height) // 2)
        if flower is not None:
            target.blit(flower, flower.get_rect(center=card.center))

    # -- sheets ------------------------------------------------------------------------

    def draw_dim(self, target: pygame.Surface) -> None:
        if self._dim is None or self._dim.get_size() != target.get_size():
            self._dim = pygame.Surface(target.get_size(), pygame.SRCALPHA)
            self._dim.fill((61, 44, 31, 120))
        target.blit(self._dim, (0, 0))

    def draw_sheet_panel(self, target: pygame.Surface, panel: pygame.Rect, *, dim: bool = True) -> None:
        if dim:
            self.draw_dim(target)
        target.blit(self._panel(panel.size), panel.topleft)

    def draw_delete_dialog(self, target: pygame.Surface, preview: pygame.Surface | None) -> None:
        panel, preview_rect, _cancel, _confirm = self.delete_dialog_rects()
        self.draw_dim(target)
        target.blit(self._panel(panel.size), panel.topleft)
        if preview is not None:
            target.blit(preview, preview_rect)
        pygame.draw.rect(target, INK, preview_rect, width=3)
        trash = self.kit.glyph("trash", 58)
        if trash is not None:
            target.blit(trash, trash.get_rect(midtop=(panel.centerx, preview_rect.bottom + 6)))

    # -- fx / cast --------------------------------------------------------------------

    def fx_frames(self, asset_id: str, size: int) -> list[pygame.Surface]:
        key = (asset_id, int(size))
        frames = self._fx_frames.get(key)
        if frames is None:
            frames = []
            for variant in ("default", "frame_2", "frame_3"):
                image = self.kit.art.image(asset_id, int(size), variant=variant)
                if image is not None:
                    frames.append(image)
            if len(self._fx_frames) >= 8:
                self._fx_frames.pop(next(iter(self._fx_frames)))
            self._fx_frames[key] = frames
        return frames

    @staticmethod
    def dani_midbottom() -> tuple[int, int]:
        return DANI_MIDBOTTOM

    def draw_drag_hint(self, target: pygame.Surface, phase: float) -> None:
        """A shared "drag" hand glides a shape from the tray into the garden."""
        if not 0.0 <= phase <= 1.0:
            return
        start = self.tray_tiles()[0].center
        end = (self.view.centerx - 40, self.view.centery + 30)
        ease = 1 - (1 - min(1.0, phase / 0.8)) ** 2
        x = start[0] + (end[0] - start[0]) * ease
        y = start[1] + (end[1] - start[1]) * ease - math.sin(ease * math.pi) * 40
        fade = 255 if phase < 0.8 else int(255 * (1 - (phase - 0.8) / 0.2))
        shape = self.shapes.image(SHAPE_KINDS[0], "natural", 62)
        if shape is not None:
            ghost = shape.copy()
            ghost.fill((255, 255, 255, min(200, fade)), special_flags=pygame.BLEND_RGBA_MULT)
            target.blit(ghost, ghost.get_rect(center=(int(x), int(y))))
        hand = self.kit.glyph("drag_hint", 60)
        if hand is not None:
            hand = hand.copy()
            hand.fill((255, 255, 255, fade), special_flags=pygame.BLEND_RGBA_MULT)
            target.blit(hand, hand.get_rect(topleft=(int(x) + 4, int(y) + 6)))


def decode_picture(payload: bytes) -> pygame.Surface:
    """Decode an imported backdrop PNG to the 1024x600 garden (contain fit)."""
    surface = decode_png_surface(payload, (GARDEN_WIDTH, GARDEN_HEIGHT))
    return surface.convert() if pygame.display.get_surface() is not None else surface


__all__ = ["FxBurst", "GardenComposer", "GardenRenderer", "decode_picture"]
