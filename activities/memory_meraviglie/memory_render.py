"""Frame composition for Wonder Match (blits only).

``BoardMotion`` holds the short-lived presentation state (card turn-overs,
miss wiggles, glow halos, FX, stickers flying to the album page, Lilli's
peek); ``LilliCast`` wraps the shared ``CastFeedback`` with Lilli's point and
wave poses; ``MemoryRenderer`` draws the picker and the board from the model
plus that motion state. Every surface comes prepared from ``MemoryArt`` --
the only per-frame work is choosing which cached surface to blit where.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
import math

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose

if __package__:
    from .memory_art import MemoryArt, Side
    from .memory_content import PICKER_SCENE, Album
    from .memory_layout import LILLI_HEIGHT, LILLI_MIDBOTTOM, BoardLayout
    from .memory_model import CardState, MemoryBoard, StickerBook
else:
    from memory_art import MemoryArt, Side
    from memory_content import PICKER_SCENE, Album
    from memory_layout import LILLI_HEIGHT, LILLI_MIDBOTTOM, BoardLayout
    from memory_model import CardState, MemoryBoard, StickerBook

FLIP_SECONDS = 0.26
WOBBLE_SECONDS = 0.5
FLIGHT_SECONDS = 0.62
POP_SECONDS = 0.45
DEAL_STAGGER = 0.045
FX_SECONDS = 0.6
MAX_FX = 24
TRAY = (255, 251, 235, 150)


@dataclass(slots=True)
class Flight:
    start: float
    origin: tuple[int, int]
    target: tuple[int, int]
    asset_id: str
    duration: float = FLIGHT_SECONDS

    def position(self, now: float) -> tuple[int, int] | None:
        t = (now - self.start) / self.duration
        if t < 0 or t >= 1:
            return None
        ease = 1 - (1 - t) ** 3
        x = self.origin[0] + (self.target[0] - self.origin[0]) * ease
        y = self.origin[1] + (self.target[1] - self.origin[1]) * ease - math.sin(math.pi * t) * 70
        return int(x), int(y)


@dataclass(slots=True)
class BoardMotion:
    """Presentation-only timers for the current board (bounded, cleared per board)."""

    deal_start: float = -10.0
    flips: dict[int, tuple[float, Side, Side]] = field(default_factory=dict)
    wobbles: dict[int, float] = field(default_factory=dict)
    halos: dict[int, tuple[float, float]] = field(default_factory=dict)
    peek: set[int] = field(default_factory=set)
    gone: set[int] = field(default_factory=set)
    flights: list[Flight] = field(default_factory=list)
    incoming: set[str] = field(default_factory=set)
    pops: dict[str, float] = field(default_factory=dict)
    fx: deque = field(default_factory=lambda: deque(maxlen=MAX_FX))

    def clear(self) -> None:
        self.deal_start = -10.0
        self.flips.clear()
        self.wobbles.clear()
        self.halos.clear()
        self.peek.clear()
        self.gone.clear()
        self.flights.clear()
        self.incoming.clear()
        self.pops.clear()
        self.fx.clear()

    def turn(self, index: int, now: float, from_side: Side, to_side: Side) -> None:
        self.flips[index] = (now, from_side, to_side)

    def add_fx(self, name: str, position: tuple[int, int], start: float) -> None:
        self.fx.append((name, position, start))

    def active(self, now: float, card_count: int) -> bool:
        if now - self.deal_start < DEAL_STAGGER * card_count + 0.2:
            return True
        if any(now - start < FLIP_SECONDS for start, _, _ in self.flips.values()):
            return True
        if any(now - start < WOBBLE_SECONDS for start in self.wobbles.values()):
            return True
        if any(start <= now + 0.05 and now < end for start, end in self.halos.values()):
            return True
        if any(now - start < FX_SECONDS for _, _, start in self.fx):
            return True
        if any(now - start < POP_SECONDS for start in self.pops.values()):
            return True
        return bool(self.flights)

    def prune(self, now: float) -> None:
        for index in [i for i, (start, _, _) in self.flips.items() if now - start >= FLIP_SECONDS]:
            del self.flips[index]
        for index in [i for i, start in self.wobbles.items() if now - start >= WOBBLE_SECONDS]:
            del self.wobbles[index]
        for index in [i for i, (_, end) in self.halos.items() if now >= end]:
            del self.halos[index]
        for subject in [s for s, start in self.pops.items() if now - start >= POP_SECONDS]:
            del self.pops[subject]
        self.flights = [flight for flight in self.flights if now - flight.start < flight.duration]
        while self.fx and now - self.fx[0][2] >= FX_SECONDS:
            self.fx.popleft()


class LilliCast:
    """Lilli: shared cheer/think feedback plus point (hints) and wave (picker)."""

    def __init__(self, feedback: CastFeedback, art: MemoryArt, clock: Callable[[], float]) -> None:
        self.feedback = feedback
        self._clock = clock
        self._point = art.cast_pose("pose_point", LILLI_HEIGHT)
        self._wave = art.cast_pose("pose_wave", LILLI_HEIGHT)
        self._loader = art.loader
        self._point_until = 0.0
        self.waving = False

    @property
    def pose(self) -> CastPose:
        return self.feedback.pose

    @property
    def pointing(self) -> bool:
        return self._clock() < self._point_until and self.feedback.pose is CastPose.IDLE

    @property
    def animating(self) -> bool:
        return self.feedback.animating or self.pointing

    def correct(self) -> None:
        self._point_until = 0.0
        self.feedback.correct()

    def try_again(self) -> None:
        self._point_until = 0.0
        self.feedback.try_again()

    def point(self, seconds: float) -> None:
        self.feedback.reset()
        self._point_until = self._clock() + seconds

    def reset(self) -> None:
        self._point_until = 0.0
        self.feedback.reset()

    def update(self) -> bool:
        changed = self.feedback.update()
        if self._point_until and self._clock() >= self._point_until:
            self._point_until = 0.0
            changed = True
        return changed

    def draw(self, surface: pygame.Surface) -> None:
        if self.waving and self._wave is not None and self.feedback.pose is CastPose.IDLE:
            surface.blit(self._loader.presentable(self._wave, surface), self._wave.get_rect(midbottom=LILLI_MIDBOTTOM))
            return
        if self.pointing and self._point is not None:
            bob = int(math.sin((self._point_until - self._clock()) * 7.0) * 3)
            surface.blit(self._loader.presentable(self._point, surface), self._point.get_rect(midbottom=(LILLI_MIDBOTTOM[0], LILLI_MIDBOTTOM[1] + bob)))
            return
        self.feedback.draw(surface, LILLI_MIDBOTTOM)


class MemoryRenderer:
    """Compose picker and board frames from prepared art."""

    def __init__(self, art: MemoryArt, cast: LilliCast, clock: Callable[[], float]) -> None:
        self._art = art
        self._cast = cast
        self._clock = clock
        self._backdrop_key: tuple | None = None
        self._backdrop: pygame.Surface | None = None

    # -- picker -----------------------------------------------------------------

    def draw_picker(self, surface: pygame.Surface) -> None:
        surface.blit(self._art.background(PICKER_SCENE), (0, 0))
        self._cast.draw(surface)

    # -- board ------------------------------------------------------------------

    def draw_board(
        self,
        surface: pygame.Surface,
        album: Album,
        board: MemoryBoard,
        layout: BoardLayout,
        book: StickerBook,
        motion: BoardMotion,
    ) -> None:
        now = self._clock()
        surface.blit(self._board_backdrop(album, layout), (0, 0))
        self._draw_page(surface, album, layout, book, motion, now)
        for index, (halo_start, halo_end) in motion.halos.items():
            if halo_start <= now < halo_end and index < len(layout.cards):
                rect = layout.cards[index]
                surface.blit(self._art.halo(rect.size), (rect.x - 14, rect.y - 14))
        for index, card in enumerate(board.cards):
            if index < len(layout.cards):
                self._draw_card(surface, index, card.state, album.subject(card.subject_id).asset_id, layout, motion, now)
        for name, position, start in motion.fx:
            elapsed = now - start
            frames = self._art.fx_frames(name)
            if 0 <= elapsed < FX_SECONDS and frames:
                frame = frames[min(len(frames) - 1, int(elapsed / FX_SECONDS * len(frames)))]
                surface.blit(frame, frame.get_rect(center=position))
        for flight in motion.flights:
            position = flight.position(now)
            sticker = self._art.sticker(flight.asset_id, layout.sticker_size)
            if position is not None and sticker is not None:
                surface.blit(sticker, sticker.get_rect(center=position))
        self._cast.draw(surface)

    def _board_backdrop(self, album: Album, layout: BoardLayout) -> pygame.Surface:
        """Album scene + a soft cream table under the grid, composed once per board."""

        key = (album.album_id, tuple(layout.grid))
        if self._backdrop is None or key != self._backdrop_key:
            base = self._art.background(album.scene).copy()
            tray = pygame.Surface(layout.grid.inflate(36, 36).size, pygame.SRCALPHA)
            pygame.draw.rect(tray, TRAY, tray.get_rect(), border_radius=34)
            base.blit(tray, layout.grid.inflate(36, 36).topleft)
            self._backdrop = base
            self._backdrop_key = key
        return self._backdrop

    def _draw_page(
        self,
        surface: pygame.Surface,
        album: Album,
        layout: BoardLayout,
        book: StickerBook,
        motion: BoardMotion,
        now: float,
    ) -> None:
        surface.blit(self._art.page(layout.panel.size, album), layout.panel.topleft)
        for well, subject in zip(layout.wells, album.subjects):
            surface.blit(self._art.well(well.width), well.topleft)
            collected = book.has(album.album_id, subject.subject_id) and subject.subject_id not in motion.incoming
            image = (
                self._art.sticker(subject.asset_id, layout.sticker_size)
                if collected
                else self._art.silhouette(subject.asset_id, layout.sticker_size)
            )
            if image is None:
                continue
            centre = well.center
            popped = motion.pops.get(subject.subject_id)
            if collected and popped is not None and now - popped < POP_SECONDS:
                lift = int(math.sin(math.pi * (now - popped) / POP_SECONDS) * 10)
                centre = (centre[0], centre[1] - lift)
            surface.blit(image, image.get_rect(center=centre))

    def _draw_card(
        self,
        surface: pygame.Surface,
        index: int,
        state: CardState,
        asset_id: str,
        layout: BoardLayout,
        motion: BoardMotion,
        now: float,
    ) -> None:
        rect = layout.cards[index]
        if now < motion.deal_start + DEAL_STAGGER * index:
            return
        if index in motion.gone:
            surface.blit(self._art.empty_card(rect.size), rect.topleft)
            return
        size = rect.size
        x = rect.x
        wobble = motion.wobbles.get(index)
        if wobble is not None and now - wobble < WOBBLE_SECONDS:
            elapsed = now - wobble
            x += int(8 * (1 - elapsed / WOBBLE_SECONDS) * math.sin(elapsed * 42))
        flip = motion.flips.get(index)
        if flip is not None and now - flip[0] < FLIP_SECONDS:
            progress = (now - flip[0]) / FLIP_SECONDS
            side = flip[1] if progress < 0.5 else flip[2]
            step = 0 if progress < 0.25 or progress >= 0.75 else 1
            frame = self._art.card_squash(side, size, asset_id, step)
            surface.blit(frame, (x + (size[0] - frame.get_width()) // 2, rect.y))
            return
        face_up = state is not CardState.DOWN or index in motion.peek
        side = Side.FACE if face_up else Side.BACK
        surface.blit(self._art.card(side, size, asset_id), (x, rect.y))


__all__ = ["BoardMotion", "Flight", "LilliCast", "MemoryRenderer"]
