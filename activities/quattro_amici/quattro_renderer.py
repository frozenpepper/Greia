"""Storybook presentation for Quattro Amici in Fila.

The renderer draws the meadow stage (one opaque blit), the discs inside the
board, the falling disc, the board's front plate, hint and win highlights,
the hovering disc of the friend whose turn it is, Flash and Leo with their
score plates, and FX. Kit controls and their focus ring are drawn afterwards
by the shared ``ControlLayer`` (ADR 0037). Per-frame work is blits only:
every surface comes prepared from ``QuattroArt``; motion is offsets.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import math
import time

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose

if __package__:
    from .quattro_art import QuattroArt
    from .quattro_content import WINS_FOR_MATCH, Player
    from .quattro_layout import CAST_HEIGHT, CAST_MIDBOTTOM, BoardGeometry, plate_rect
    from .quattro_model import QuattroGame
else:
    from quattro_art import QuattroArt
    from quattro_content import WINS_FOR_MATCH, Player
    from quattro_layout import CAST_HEIGHT, CAST_MIDBOTTOM, BoardGeometry, plate_rect
    from quattro_model import QuattroGame

GLIDE_SPEED = 900.0  # px/s of the hovering disc moving between columns
TURN_HOP_SECONDS = 0.4
PULSE_SECONDS = 1.6
WOBBLE_SECONDS = 0.4
WIN_STEP_SECONDS = 0.28
SCORE_POP_SECONDS = 0.6
MAX_FX = 16
FX_SECONDS = {"sparkle": 0.5, "star_burst": 0.8, "heart_pop": 1.0, "confetti": 1.6}
FX_RISE = {"heart_pop": -40.0, "confetti": 60.0}


@dataclass
class DropAnimation:
    """State of an in-flight falling disc with a short landing bounce."""

    col: int
    target_row: int
    player: Player
    current_y: float
    target_y: float
    velocity_y: float = 0.0
    bounce_timer: float = 0.0
    settled: bool = False
    landed: bool = False
    _landing_pending: bool = False

    BOUNCE_SECONDS = 0.15

    def update(self, dt: float) -> bool:
        """Advance by ``dt``; return True once settled.

        Two explicit phases: falling, then a short landing bounce. The bounce
        must never push the disc back into the falling phase (it sits above
        the target), so the phase is tracked by ``landed`` rather than by
        comparing ``current_y`` with ``target_y``.
        """

        if self.settled:
            return True
        if not self.landed:
            self.velocity_y += 2200.0 * dt
            self.current_y += self.velocity_y * dt
            if self.current_y >= self.target_y:
                self.current_y = self.target_y
                self.landed = True
                self._landing_pending = True
                self.bounce_timer = self.BOUNCE_SECONDS
            return False
        self.bounce_timer -= dt
        if self.bounce_timer <= 0.0:
            self.bounce_timer = 0.0
            self.current_y = self.target_y
            self.settled = True
        else:
            offset = math.sin(self.bounce_timer / self.BOUNCE_SECONDS * math.pi) * 8.0
            self.current_y = self.target_y - offset
        return self.settled

    def consume_landing(self) -> bool:
        """Return True exactly once, on the frame the disc first reaches its row."""

        if self._landing_pending:
            self._landing_pending = False
            return True
        return False


class FriendCast:
    """Flash or Leo: the shared feedback grammar plus turn/hint poses.

    ``CastFeedback`` owns cheer (correct / won) and think (try again); this
    wrapper adds the friend whose turn it is (``happy`` + a hop), the waiting
    friend (``default``), Leo choosing a column (``pose_think``), graduated
    hints (``pose_point``, mirrored for Leo so he points at the board) and
    short reactions (``surprised``). Grammar poses always win over the rest.
    """

    def __init__(
        self,
        player: Player,
        feedback: CastFeedback,
        art: QuattroArt,
        clock: Callable[[], float],
        height: int = CAST_HEIGHT,
    ) -> None:
        self.player = player
        self.feedback = feedback
        self._art = art
        self._clock = clock
        self._height = height
        self._active = False
        self._hop_since = -10.0
        self._transient: tuple[str, float] | None = None  # (variant, until)

    @property
    def active(self) -> bool:
        return self._active

    def set_active(self, active: bool) -> None:
        if active and not self._active:
            self._hop_since = self._clock()
        self._active = active

    def correct(self) -> None:
        self._transient = None
        self.feedback.correct()

    def try_again(self) -> None:
        self._transient = None
        self.feedback.try_again()

    def show(self, variant: str, seconds: float) -> None:
        """Hold a transient pose (``pose_point``, ``pose_think``, ``surprised``)."""

        self._transient = (variant, self._clock() + seconds)

    def reset(self) -> None:
        self._transient = None
        self.feedback.reset()

    @property
    def pose_name(self) -> str:
        """The variant currently drawn (for tests and diagnostics)."""

        if self.feedback.pose is CastPose.CHEER:
            return "pose_cheer"
        if self.feedback.pose is CastPose.THINK:
            return "pose_think"
        if self._transient is not None and self._clock() < self._transient[1]:
            return self._transient[0]
        return "happy" if self._active else "default"

    @property
    def animating(self) -> bool:
        return (
            self.feedback.animating
            or self._transient is not None
            or self._clock() - self._hop_since < TURN_HOP_SECONDS
        )

    def update(self) -> bool:
        changed = self.feedback.update()
        if self._transient is not None and self._clock() >= self._transient[1]:
            self._transient = None
            changed = True
        if self._clock() - self._hop_since < TURN_HOP_SECONDS + 0.05:
            changed = True
        return changed

    def draw(self, target: pygame.Surface, midbottom: tuple[int, int]) -> None:
        if self.feedback.pose is not CastPose.IDLE:
            self.feedback.draw(target, midbottom)
            return
        variant = self.pose_name
        mirrored = self.player is Player.LEO and variant == "pose_point"
        image = self._art.cast(self.player, variant, self._height, mirrored=mirrored)
        if image is None:
            self.feedback.draw(target, midbottom)
            return
        hop = self._clock() - self._hop_since
        lift = int(math.sin(math.pi * hop / TURN_HOP_SECONDS) * self._height * 0.07) if hop < TURN_HOP_SECONDS else 0
        target.blit(image, image.get_rect(midbottom=(midbottom[0], midbottom[1] - lift)))


@dataclass
class BoardMotion:
    """Bounded, time-stamped presentation state owned by the app."""

    drop: DropAnimation | None = None
    selector_col: int = 0
    selector_x: float | None = None
    show_selector: bool = False
    selector_since: float = 0.0
    pulse_start: float | None = None
    glow_col: int | None = None
    glow_until: float = 0.0
    wobble_col: int | None = None
    wobble_start: float = 0.0
    win_cells: list[tuple[int, int]] = field(default_factory=list)
    win_start: float = 0.0
    win_band: pygame.Surface | None = None
    fx: list[tuple[str, tuple[int, int], float]] = field(default_factory=list)
    score_pop: tuple[Player, float] | None = None

    def clear(self) -> None:
        self.drop = None
        self.pulse_start = None
        self.glow_col = None
        self.wobble_col = None
        self.win_cells = []
        self.win_band = None
        self.fx.clear()
        self.score_pop = None

    def add_fx(self, name: str, position: tuple[int, int], start: float) -> None:
        self.fx.append((name, position, start))
        del self.fx[:-MAX_FX]

    def prune(self, now: float) -> None:
        self.fx = [entry for entry in self.fx if now - entry[2] < FX_SECONDS.get(entry[0], 0.6)]
        if self.glow_col is not None and now >= self.glow_until:
            self.glow_col = None

    def active(self, now: float, geometry: BoardGeometry) -> bool:
        if self.drop is not None:
            return True
        if self.fx or (self.glow_col is not None and now < self.glow_until):
            return True
        if self.pulse_start is not None and now - self.pulse_start < PULSE_SECONDS:
            return True
        if self.wobble_col is not None and now - self.wobble_start < WOBBLE_SECONDS:
            return True
        if self.win_cells and now - self.win_start < WIN_STEP_SECONDS * (len(self.win_cells) + 2):
            return True
        if self.score_pop is not None and now - self.score_pop[1] < SCORE_POP_SECONDS:
            return True
        if self.show_selector and now - self.selector_since < 2.5:
            return True  # the hovering disc bobs briefly when a turn starts
        if self.selector_x is not None and self.show_selector:
            return abs(self.selector_x - geometry.column_x(self.selector_col)) > 0.5
        return False


class QuattroRenderer:
    """Renders the match scene onto the reference canvas surface."""

    def __init__(
        self,
        art: QuattroArt,
        friends: dict[Player, FriendCast],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.art = art
        self.friends = friends
        self.geometry: BoardGeometry | None = None
        self._human_turn = True
        self._clock = clock
        self._last = clock()

    def get_column_at_x(self, model: object, x: float) -> int | None:
        """Board column under logical ``x`` (``model`` kept for the caller's API)."""

        return self.geometry.column_at(x) if self.geometry is not None else None

    # -- frame ---------------------------------------------------------------------

    def draw(
        self,
        target: pygame.Surface,
        game: QuattroGame,
        geometry: BoardGeometry,
        motion: BoardMotion,
        wins: dict[Player, int],
        selected_col: int,
        *,
        human_turn: bool = True,
    ) -> None:
        now = self._clock()
        self._human_turn = human_turn
        dt = max(0.0, min(0.1, now - self._last))
        self._last = now
        target.blit(self.art.scene, (0, 0))
        self._draw_friends(target, wins, motion, now)
        self._draw_discs(target, game, geometry, motion)
        if self.art.plate is not None:
            target.blit(self.art.plate, geometry.frame.topleft)
        self._draw_glow(target, geometry, motion, now)
        self._draw_win(target, game, geometry, motion, now)
        self._draw_selector(target, game, geometry, motion, selected_col, now, dt)
        self._draw_fx(target, motion, now)

    # -- pieces ---------------------------------------------------------------------

    def _draw_friends(self, target: pygame.Surface, wins: dict[Player, int], motion: BoardMotion, now: float) -> None:
        for player, friend in self.friends.items():
            midbottom = CAST_MIDBOTTOM[player]
            if friend.active:
                spot = self.art.spotlight(176)
                target.blit(spot, spot.get_rect(center=(midbottom[0], midbottom[1] - 10)))
            friend.draw(target, midbottom)
            plate = self.art.score_plate(player, wins.get(player, 0), WINS_FOR_MATCH, friend.active)
            rect = plate_rect(player)
            lift = 0
            if motion.score_pop is not None and motion.score_pop[0] is player:
                age = now - motion.score_pop[1]
                if 0.0 <= age < SCORE_POP_SECONDS:
                    lift = int(math.sin(math.pi * age / SCORE_POP_SECONDS) * 12)
            target.blit(plate, (rect.x, rect.y - lift))

    def _draw_discs(self, target: pygame.Surface, game: QuattroGame, geometry: BoardGeometry, motion: BoardMotion) -> None:
        size = geometry.token_size
        drop = motion.drop
        hidden = (drop.target_row, drop.col) if drop is not None and not drop.settled else None
        board = game.board
        for row in range(board.rows):
            for col in range(board.cols):
                player = board.grid[row][col]
                if player == Player.EMPTY or (row, col) == hidden:
                    continue
                disc = self.art.token(player, size)
                target.blit(disc, disc.get_rect(center=geometry.cell_center(row, col)))
        if drop is not None and not drop.settled:
            disc = self.art.token(drop.player, size)
            target.blit(disc, disc.get_rect(center=(geometry.column_x(drop.col), int(drop.current_y))))

    def _draw_glow(self, target: pygame.Surface, geometry: BoardGeometry, motion: BoardMotion, now: float) -> None:
        if motion.glow_col is not None and now < motion.glow_until:
            if int(now * 3) % 3 != 2:  # gentle blink
                target.blit(self.art.column_glow(geometry), geometry.column_rect(motion.glow_col).topleft)

    def _draw_win(
        self, target: pygame.Surface, game: QuattroGame, geometry: BoardGeometry, motion: BoardMotion, now: float
    ) -> None:
        if not motion.win_cells:
            return
        age = now - motion.win_start
        shown = min(len(motion.win_cells), int(age / WIN_STEP_SECONDS) + 1) if age >= 0 else 0
        if shown >= len(motion.win_cells) and motion.win_band is not None:
            target.blit(motion.win_band, geometry.frame.topleft)
        ring = self.art.win_ring(geometry)
        for index, (row, col) in enumerate(motion.win_cells[:shown]):
            center = geometry.cell_center(row, col)
            target.blit(ring, ring.get_rect(center=center))
            player = game.board.grid[row][col]
            if player != Player.EMPTY:
                pop = now - (motion.win_start + index * WIN_STEP_SECONDS)
                if 0.0 <= pop < 0.22:
                    disc = self.art.token(player, int(geometry.token_size * 1.12))
                    target.blit(disc, disc.get_rect(center=center))

    def _draw_selector(
        self,
        target: pygame.Surface,
        game: QuattroGame,
        geometry: BoardGeometry,
        motion: BoardMotion,
        selected_col: int,
        now: float,
        dt: float,
    ) -> None:
        motion.selector_col = selected_col
        if not motion.show_selector or game.finished:
            return
        goal_x = float(geometry.column_x(selected_col))
        if motion.selector_x is None:
            motion.selector_x = goal_x
        step = GLIDE_SPEED * dt
        delta = goal_x - motion.selector_x
        motion.selector_x = goal_x if abs(delta) <= step else motion.selector_x + math.copysign(step, delta)
        bob = 0.0
        since = now - motion.selector_since
        if since < 2.5:
            bob = math.sin(since * 6.0) * 5.0 * (1.0 - since / 2.5)
        pulse = motion.pulse_start is not None and now - motion.pulse_start < PULSE_SECONDS
        if pulse:
            bob = -abs(math.sin((now - motion.pulse_start) * 7.0)) * 12.0
        wobble = 0
        if motion.wobble_col is not None and now - motion.wobble_start < WOBBLE_SECONDS:
            elapsed = now - motion.wobble_start
            wobble = int(9 * (1 - elapsed / WOBBLE_SECONDS) * (1 if int(elapsed * 40) % 2 else -1))
        size = geometry.selector_size
        disc = self.art.token(game.current_player, size)
        center = (int(motion.selector_x) + wobble, int(geometry.selector_y + bob))
        target.blit(disc, disc.get_rect(center=center))
        arrow = self.art.glyph("arrow_down", max(22, int(geometry.cell * 0.34)))
        if arrow is not None and self._human_turn:
            target.blit(arrow, arrow.get_rect(midtop=(center[0], center[1] + size // 2 - 4)))

    def _draw_fx(self, target: pygame.Surface, motion: BoardMotion, now: float) -> None:
        for name, position, start in motion.fx:
            frames = self.art.fx_frames(name)
            duration = FX_SECONDS.get(name, 0.6)
            age = now - start
            if not frames or age < 0.0 or age >= duration:
                continue
            frame = frames[min(len(frames) - 1, int(age / duration * len(frames)))]
            drift = int(FX_RISE.get(name, 0.0) * age / duration)
            target.blit(frame, frame.get_rect(center=(position[0], position[1] + drift)))


__all__ = ["BoardMotion", "DropAnimation", "FriendCast", "QuattroRenderer"]
