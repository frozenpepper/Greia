"""Polymorphic pair scenes for Mondo Contrari.

Each opposite pair is one ``PairScene``. The app drives every scene through
the same small contract: two choice targets, ``present_ask`` (any transition
before the child may answer), ``perform`` (the correct concept happening),
``demonstrate`` (show the asked concept after a try-again), ``pulse`` (idle
hint on BOTH choices, never only the answer) and ``draw``. Two families share
most behaviour:

* ``MakeScene`` — the child moves one thing (tap a destination or drag it):
  ``UpDownScene`` (balloon to the cloud or the flowers) and ``InOutScene``
  (kitten into the box or out to its ball).
* ``FindScene`` — two copies of the same picture differ only by the concept;
  the child picks one: ``BigSmallScene``, ``OpenClosedScene`` and
  ``FastSlowScene`` (two lanes, same racer, two speeds).

Motion is computed from the injected clock (no per-frame allocation, decode
or scaling); all surfaces come from ``ContrariArt``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import math
from typing import Final

import pygame

if __package__:
    from .contrari_art import ContrariArt
    from .contrari_layout import (
        BALL_SIZE,
        BALLOON_SIZE,
        BALLOON_TOP_DOWN,
        BALLOON_TOP_NEUTRAL,
        BALLOON_TOP_UP,
        BALLOON_X,
        BIG_SIZE,
        BOX_BOTTOM,
        BOX_SIZE,
        BOX_SLOTS,
        CLOUD_CENTER,
        CLOUD_SIZE,
        FLOWER_SIZE,
        FLOWER_SPOTS,
        GIFT_SIZE,
        GRASS_TARGET,
        GROUND_Y,
        KITTEN_SIZE,
        LANE_RECTS,
        PUPPY_SIZE,
        RACE_END_X,
        RACE_START_X,
        RACER_SIZES,
        SKY_TARGET,
        SLOT_CENTERS,
        SMALL_SIZE,
        STAGE_LEFT,
        box_target,
        out_target,
        slot_rect,
    )
    from .contrari_model import Ask, OppositeCategory, PairRound, Pole
else:
    from contrari_art import ContrariArt
    from contrari_layout import (
        BALL_SIZE,
        BALLOON_SIZE,
        BALLOON_TOP_DOWN,
        BALLOON_TOP_NEUTRAL,
        BALLOON_TOP_UP,
        BALLOON_X,
        BIG_SIZE,
        BOX_BOTTOM,
        BOX_SIZE,
        BOX_SLOTS,
        CLOUD_CENTER,
        CLOUD_SIZE,
        FLOWER_SIZE,
        FLOWER_SPOTS,
        GIFT_SIZE,
        GRASS_TARGET,
        GROUND_Y,
        KITTEN_SIZE,
        LANE_RECTS,
        PUPPY_SIZE,
        RACE_END_X,
        RACE_START_X,
        RACER_SIZES,
        SKY_TARGET,
        SLOT_CENTERS,
        SMALL_SIZE,
        STAGE_LEFT,
        box_target,
        out_target,
        slot_rect,
    )
    from contrari_model import Ask, OppositeCategory, PairRound, Pole

NEUTRAL: Final = None  # the "between the poles" resting state of a make scene
PULSE_SECONDS: Final = 1.4
WOBBLE_SECONDS: Final = 0.45
SWAP_SECONDS: Final = 0.7
HOP_SECONDS: Final = 0.55
DEMO_HOLD: Final = 0.7
FAST_SPEED: Final = 430.0
SLOW_SPEED: Final = 26.0


def _ease(progress: float) -> float:
    progress = max(0.0, min(1.0, progress))
    return progress * progress * (3.0 - 2.0 * progress)


@dataclass(slots=True)
class Tween:
    """A point moving from ``start`` to ``end`` with an optional hop arc."""

    began: float
    duration: float
    start: tuple[float, float]
    end: tuple[float, float]
    lift: float = 0.0

    def progress(self, now: float) -> float:
        if self.duration <= 0:
            return 1.0
        return max(0.0, min(1.0, (now - self.began) / self.duration))

    def at(self, now: float) -> tuple[float, float]:
        raw = self.progress(now)
        t = _ease(raw)
        x = self.start[0] + (self.end[0] - self.start[0]) * t
        y = self.start[1] + (self.end[1] - self.start[1]) * t - self.lift * math.sin(math.pi * raw)
        return (x, y)

    def done(self, now: float) -> bool:
        return now >= self.began + self.duration


class PairScene(ABC):
    """One opposite pair on the meadow stage (see module docstring)."""

    category: OppositeCategory

    def __init__(self, art: ContrariArt) -> None:
        self._art = art
        self.sides: tuple[Pole, Pole] | None = None
        self._halos: dict[int, tuple[float, float]] = {}
        self._wobbles: dict[int, float] = {}
        self._busy_until = 0.0

    # -- round lifecycle ----------------------------------------------------------

    def begin_round(self, round_: PairRound, now: float) -> None:
        self.sides = round_.asks[0].sides
        self._halos.clear()
        self._wobbles.clear()
        self._busy_until = now

    def present_ask(self, ask: Ask, index: int, now: float) -> float:
        """Prepare one ask; return the seconds of transition before answering."""

        self.sides = ask.sides
        return 0.0

    def pole_at(self, index: int) -> Pole | None:
        if self.sides is None or not 0 <= index < 2:
            return None
        return self.sides[index]

    def index_of(self, pole: Pole) -> int:
        assert self.sides is not None
        return self.sides.index(pole)

    # -- geometry ----------------------------------------------------------------

    @abstractmethod
    def target_rects(self) -> tuple[pygame.Rect, pygame.Rect]:
        """Choice 0 and choice 1 in logical pixels (never overlapping)."""

    def fx_point(self, pole: Pole, now: float = 0.0) -> tuple[int, int]:
        return self.target_rects()[self.index_of(pole)].center

    # -- feedback ----------------------------------------------------------------

    @abstractmethod
    def perform(self, pole: Pole, now: float) -> float:
        """The correct concept happens; returns its duration."""

    @abstractmethod
    def demonstrate(self, pole: Pole, now: float) -> float:
        """Show the asked concept after a try-again; returns its duration."""

    def wrong(self, index: int, now: float) -> None:
        self._wobbles[index] = now

    def pulse(self, now: float) -> None:
        """Idle hint: both choices glow, so nothing is revealed."""

        self._halos[0] = (now, PULSE_SECONDS)
        self._halos[1] = (now, PULSE_SECONDS)

    def glow(self, index: int, now: float, seconds: float) -> None:
        self._halos[index] = (now, seconds)

    # -- drag (make scenes only) ---------------------------------------------------

    def drag_handle(self) -> pygame.Rect | None:
        return None

    def drag_to(self, position: tuple[int, int]) -> None:
        return None

    def drop(self, position: tuple[int, int]) -> Pole | None:
        return None

    def cancel_drag(self) -> None:
        return None

    # -- drawing -----------------------------------------------------------------

    def animating(self, now: float) -> bool:
        if now < self._busy_until:
            return True
        if any(now < start + seconds for start, seconds in self._halos.values()):
            return True
        return any(now < start + WOBBLE_SECONDS for start in self._wobbles.values())

    @abstractmethod
    def draw(self, surface: pygame.Surface, now: float) -> None:
        """Draw the pair scene (background and Flash are drawn by the renderer)."""

    def _wobble_dx(self, index: int, now: float) -> int:
        started = self._wobbles.get(index)
        if started is None:
            return 0
        elapsed = now - started
        if elapsed >= WOBBLE_SECONDS:
            return 0
        return int(10 * (1 - elapsed / WOBBLE_SECONDS) * math.sin(elapsed * 46))

    def _draw_halos(self, surface: pygame.Surface, now: float) -> None:
        for index, (start, seconds) in self._halos.items():
            elapsed = now - start
            if elapsed < 0 or elapsed >= seconds:
                continue
            rect = self.target_rects()[index].inflate(12, 12)
            halo = self._art.halo(rect.size)
            halo.set_alpha(int(150 + 105 * abs(math.sin(elapsed * 5.0))))
            surface.blit(halo, rect.topleft)

    def _hold(self, now: float, seconds: float) -> float:
        self._busy_until = max(self._busy_until, now + seconds)
        return seconds


# =============================================================================
# Make scenes
# =============================================================================


class MakeScene(PairScene):
    """The child moves one thing to the place that means the word."""

    def __init__(self, art: ContrariArt) -> None:
        super().__init__(art)
        self.state: Pole | None = NEUTRAL
        self._tween: Tween | None = None
        self._return: tuple[float, Pole | None] | None = None
        self._dragging: tuple[float, float] | None = None
        self._drag_offset = (0.0, 0.0)

    @abstractmethod
    def anchor(self, state: Pole | None) -> tuple[float, float]:
        """Logical position of the moving thing for a state (None = neutral)."""

    def begin_round(self, round_: PairRound, now: float) -> None:
        super().begin_round(round_, now)
        self.state = NEUTRAL
        self._tween = None
        self._return = None
        self._dragging = None

    def present_ask(self, ask: Ask, index: int, now: float) -> float:
        super().present_ask(ask, index, now)
        if index >= 2 and self.state is not NEUTRAL:
            # The surprise third word starts from the middle again.
            self._move(NEUTRAL, now, 0.6, lift=0.0)
            return self._hold(now, 0.6)
        return 0.0

    def resting(self) -> tuple[float, float]:
        """Where the thing is (or will be) once the current motion ends."""

        if self._tween is not None:
            return self._tween.end
        return self.anchor(self.state)

    def position(self, now: float) -> tuple[float, float]:
        if self._dragging is not None:
            return self._dragging
        if self._tween is not None and not self._tween.done(now):
            return self._tween.at(now)
        return self.resting()

    def perform(self, pole: Pole, now: float) -> float:
        duration = self._move_duration(pole)
        self._return = None
        self._move(pole, now, duration, lift=self._lift(pole))
        return self._hold(now, duration)

    def demonstrate(self, pole: Pole, now: float) -> float:
        """Go there, wait, and come back: the child still does it themselves."""

        go = self._move_duration(pole) * 0.8
        self._tween = Tween(now, go, self.position(now), self.anchor(pole), self._lift(pole))
        self._return = (now + go + DEMO_HOLD, self.state)
        self.glow(self.index_of(pole), now, go + DEMO_HOLD)
        return self._hold(now, go + DEMO_HOLD + go)

    def update(self, now: float) -> None:
        """Start the way back of a demonstration when it is due."""

        if self._return is None or now < self._return[0]:
            return
        began, back = self._return
        self._return = None
        start = self._tween.end if self._tween is not None else self.anchor(back)
        self._tween = Tween(began, self._move_duration(back) * 0.8, start, self.anchor(back), self._lift(back))

    def _move(self, state: Pole | None, now: float, duration: float, *, lift: float) -> None:
        start = self.position(now)
        self.state = state
        self._tween = Tween(now, duration, start, self.anchor(state), lift)

    def _move_duration(self, pole: Pole | None) -> float:
        return 0.8

    def _lift(self, pole: Pole | None) -> float:
        return 0.0

    # -- drag ---------------------------------------------------------------------

    def drag_to(self, position: tuple[int, int]) -> None:
        if self._dragging is None:
            here = self.resting()
            self._drag_offset = (here[0] - position[0], here[1] - position[1])
        self._dragging = (position[0] + self._drag_offset[0], position[1] + self._drag_offset[1])

    def cancel_drag(self) -> None:
        self._dragging = None

    def release(self, now: float) -> None:
        """End a drag; the thing glides back to its state unless it is moved."""

        if self._dragging is None:
            return
        start = self._dragging
        self._dragging = None
        self._tween = Tween(now, 0.3, start, self.anchor(self.state))
        self._hold(now, 0.3)

    @property
    def dragging(self) -> bool:
        return self._dragging is not None

    def animating(self, now: float) -> bool:
        return (
            super().animating(now)
            or self._dragging is not None
            or self._return is not None
            or (self._tween is not None and not self._tween.done(now))
        )


class UpDownScene(MakeScene):
    """A balloon between the cloud (UP) and the flowers on the grass (DOWN)."""

    category = OppositeCategory.UP_DOWN

    def target_rects(self) -> tuple[pygame.Rect, pygame.Rect]:
        return (SKY_TARGET.copy(), GRASS_TARGET.copy())

    def anchor(self, state: Pole | None) -> tuple[float, float]:
        top = {Pole.UP: BALLOON_TOP_UP, Pole.DOWN: BALLOON_TOP_DOWN}.get(state, BALLOON_TOP_NEUTRAL)
        return (float(BALLOON_X), float(top))

    def fx_point(self, pole: Pole, now: float = 0.0) -> tuple[int, int]:
        top = BALLOON_TOP_UP if pole is Pole.UP else BALLOON_TOP_DOWN
        return (BALLOON_X, int(top + BALLOON_SIZE * 0.36))

    def _move_duration(self, pole: Pole | None) -> float:
        return 0.95

    def drag_handle(self) -> pygame.Rect | None:
        x, top = self.resting()
        return pygame.Rect(int(x - BALLOON_SIZE * 0.32), int(top), int(BALLOON_SIZE * 0.64), int(BALLOON_SIZE * 0.72))

    def drop(self, position: tuple[int, int]) -> Pole | None:
        top = position[1] + self._drag_offset[1]
        if top < BALLOON_TOP_NEUTRAL - 50:
            return Pole.UP
        if top > BALLOON_TOP_NEUTRAL + 50:
            return Pole.DOWN
        return None

    def draw(self, surface: pygame.Surface, now: float) -> None:
        self.update(now)
        cloud = self._art.shared("prop.nature.cloud", CLOUD_SIZE)
        if cloud is not None:
            surface.blit(cloud, cloud.get_rect(center=(CLOUD_CENTER[0] + self._wobble_dx(0, now), CLOUD_CENTER[1])))
        flower = self._art.shared("prop.nature.flower", FLOWER_SIZE)
        if flower is not None:
            dx = self._wobble_dx(1, now)
            for x, y in FLOWER_SPOTS:
                surface.blit(flower, flower.get_rect(midbottom=(x + dx, y)))
        x, top = self.position(now)
        span = max(1.0, BALLOON_TOP_DOWN - BALLOON_TOP_UP)
        step = int(round(5 * max(0.0, min(1.0, (top - BALLOON_TOP_UP) / span))))
        shadow = self._art.ground_shadow(step)
        if shadow is not None:
            surface.blit(shadow, shadow.get_rect(center=(int(x), GROUND_Y - 6)))
        balloon = self._art.private("balloon", BALLOON_SIZE)
        if balloon is not None:
            sway = int(4 * math.sin(now * 1.7)) if self._dragging is None else 0
            surface.blit(balloon, balloon.get_rect(midtop=(int(x) + sway, int(top))))
        self._draw_halos(surface, now)


class InOutScene(MakeScene):
    """A kitten perched on a cardboard box: hop IN, or OUT to play with its ball."""

    category = OppositeCategory.IN_OUT

    def __init__(self, art: ContrariArt) -> None:
        super().__init__(art)
        self._box_x = BOX_SLOTS[0]
        self._out_x = BOX_SLOTS[1]
        self.cheering = False

    def begin_round(self, round_: PairRound, now: float) -> None:
        super().begin_round(round_, now)
        sides = round_.asks[0].sides
        box_index = sides.index(Pole.IN)
        self._box_x = BOX_SLOTS[box_index]
        self._out_x = BOX_SLOTS[1 - box_index]
        self.cheering = False

    def target_rects(self) -> tuple[pygame.Rect, pygame.Rect]:
        rects = {Pole.IN: box_target(self._box_x), Pole.OUT: out_target(self._out_x)}
        sides = self.sides or (Pole.IN, Pole.OUT)
        return (rects[sides[0]], rects[sides[1]])

    def anchor(self, state: Pole | None) -> tuple[float, float]:
        # Midbottom of the kitten picture.
        if state is Pole.IN:
            return (float(self._box_x), 504.0)
        if state is Pole.OUT:
            return (float(self._out_x - 34), float(GROUND_Y + 6))
        return (float(self._box_x), 458.0)  # sitting on the front rim

    def fx_point(self, pole: Pole, now: float = 0.0) -> tuple[int, int]:
        x, y = self.anchor(pole)
        return (int(x + KITTEN_SIZE * 0.45), int(y - KITTEN_SIZE * 0.85))

    def _move_duration(self, pole: Pole | None) -> float:
        return HOP_SECONDS

    def _lift(self, pole: Pole | None) -> float:
        return 70.0

    def drag_handle(self) -> pygame.Rect | None:
        x, bottom = self.resting()
        return pygame.Rect(int(x - KITTEN_SIZE * 0.32), int(bottom - KITTEN_SIZE * 0.85), int(KITTEN_SIZE * 0.64), int(KITTEN_SIZE * 0.7))

    def drop(self, position: tuple[int, int]) -> Pole | None:
        point = (position[0] + self._drag_offset[0], position[1] + self._drag_offset[1] - KITTEN_SIZE // 3)
        if box_target(self._box_x).inflate(0, 80).collidepoint(point):
            return Pole.IN
        if out_target(self._out_x).collidepoint(point):
            return Pole.OUT
        return None

    def _inside(self, now: float) -> bool:
        """Draw the kitten between the box layers once it has dropped in."""

        if self._dragging is not None:
            return False
        inside = self.anchor(Pole.IN)
        tween = self._tween
        if tween is not None and not tween.done(now):
            if tween.end == inside:
                return tween.progress(now) > 0.7
            if tween.start == inside:
                return tween.progress(now) < 0.3
            return False
        return self.resting() == inside

    def draw(self, surface: pygame.Surface, now: float) -> None:
        self.update(now)
        ball = self._art.shared("prop.everyday.ball", BALL_SIZE)
        if ball is not None:
            surface.blit(ball, ball.get_rect(midbottom=(self._out_x + 78 + self._wobble_dx(self._out_index(), now), GROUND_Y + 4)))
        back = self._art.private("box_back", BOX_SIZE)
        front = self._art.private("box_front", BOX_SIZE)
        box_dx = self._wobble_dx(1 - self._out_index(), now)
        box_rect = pygame.Rect(0, 0, BOX_SIZE, BOX_SIZE)
        box_rect.midbottom = (self._box_x + box_dx, BOX_BOTTOM)
        variant = "happy" if self.cheering else "default"
        kitten = self._art.shared("creature.pet.kitten", KITTEN_SIZE, variant=variant)
        x, bottom = self.position(now)
        inside = self._inside(now)
        if back is not None:
            surface.blit(back, box_rect)
        if kitten is not None and inside:
            surface.blit(kitten, kitten.get_rect(midbottom=(int(x) + box_dx, int(bottom))))
        if front is not None:
            surface.blit(front, box_rect)
        if kitten is not None and not inside:
            surface.blit(kitten, kitten.get_rect(midbottom=(int(x), int(bottom))))
        self._draw_halos(surface, now)

    def perform(self, pole: Pole, now: float) -> float:
        self.cheering = True
        return super().perform(pole, now)

    def present_ask(self, ask: Ask, index: int, now: float) -> float:
        self.cheering = False
        return super().present_ask(ask, index, now)

    def _out_index(self) -> int:
        sides = self.sides or (Pole.IN, Pole.OUT)
        return sides.index(Pole.OUT)


# =============================================================================
# Find scenes
# =============================================================================


class FindScene(PairScene):
    """Two copies of one picture that differ only by the concept."""

    def __init__(self, art: ContrariArt) -> None:
        super().__init__(art)
        self._swap: tuple[float, tuple[Pole, Pole]] | None = None  # (began, old sides)
        self._hops: dict[Pole, float] = {}
        self.cheering: Pole | None = None

    def begin_round(self, round_: PairRound, now: float) -> None:
        super().begin_round(round_, now)
        self._swap = None
        self._hops.clear()
        self.cheering = None

    def present_ask(self, ask: Ask, index: int, now: float) -> float:
        old = self.sides
        self.sides = ask.sides
        self.cheering = None
        if old is not None and old != ask.sides:
            self._swap = (now, old)
            return self._hold(now, SWAP_SECONDS + 0.1)
        return 0.0

    def target_rects(self) -> tuple[pygame.Rect, pygame.Rect]:
        return (slot_rect(0), slot_rect(1))

    def perform(self, pole: Pole, now: float) -> float:
        self._hops[pole] = now
        self.cheering = pole
        return self._hold(now, 0.9)

    def demonstrate(self, pole: Pole, now: float) -> float:
        index = self.index_of(pole)
        self._hops[pole] = now + 0.15
        self.glow(index, now, 1.6)
        return self._hold(now, 1.6)

    def slot_x(self, pole: Pole, now: float) -> float:
        """Current centre x of a pole's picture (slides across while swapping)."""

        assert self.sides is not None
        target = SLOT_CENTERS[self.sides.index(pole)]
        if self._swap is None:
            return float(target)
        began, old = self._swap
        progress = (now - began) / SWAP_SECONDS
        if progress >= 1.0:
            self._swap = None
            return float(target)
        source = SLOT_CENTERS[old.index(pole)]
        return source + (target - source) * _ease(progress)

    def swap_lift(self, pole: Pole, now: float) -> float:
        if self._swap is None:
            return 0.0
        progress = max(0.0, min(1.0, (now - self._swap[0]) / SWAP_SECONDS))
        assert self.sides is not None
        # One picture arcs over the other so they never collide.
        direction = 1.0 if self.sides.index(pole) == 0 else -0.35
        return 70.0 * direction * math.sin(math.pi * progress)

    def hop(self, pole: Pole, now: float) -> float:
        started = self._hops.get(pole)
        if started is None or now < started:
            return 0.0
        elapsed = now - started
        if elapsed >= 0.9:
            return 0.0
        # Two happy bounces.
        return 34.0 * abs(math.sin(math.pi * elapsed / 0.45)) * (1 - elapsed / 0.9)

    def animating(self, now: float) -> bool:
        return super().animating(now) or self._swap is not None or any(
            0 <= now - started < 0.9 for started in self._hops.values()
        )

    def draw(self, surface: pygame.Surface, now: float) -> None:
        if self.sides is None:
            return
        for pole in self.sides:
            index = self.sides.index(pole)
            x = self.slot_x(pole, now) + self._wobble_dx(index, now)
            lift = self.swap_lift(pole, now) + self.hop(pole, now)
            self.draw_item(surface, pole, (int(x), int(GROUND_Y - lift)), now)
        self._draw_halos(surface, now)

    @abstractmethod
    def draw_item(self, surface: pygame.Surface, pole: Pole, midbottom: tuple[int, int], now: float) -> None:
        """Draw one picture standing at ``midbottom``."""


class BigSmallScene(FindScene):
    """The same picture twice: a BIG one and a SMALL one."""

    category = OppositeCategory.BIG_SMALL

    def __init__(self, art: ContrariArt) -> None:
        super().__init__(art)
        self.subject = "prop.vocab.elephant"

    def begin_round(self, round_: PairRound, now: float) -> None:
        super().begin_round(round_, now)
        self.subject = round_.subject or self.subject

    def fx_point(self, pole: Pole, now: float = 0.0) -> tuple[int, int]:
        size = BIG_SIZE if pole is Pole.BIG else SMALL_SIZE
        return (SLOT_CENTERS[self.index_of(pole)], int(GROUND_Y - size * 0.6))

    def draw_item(self, surface: pygame.Surface, pole: Pole, midbottom: tuple[int, int], now: float) -> None:
        size = BIG_SIZE if pole is Pole.BIG else SMALL_SIZE
        image = self._art.shared(self.subject, size)
        if image is not None:
            surface.blit(image, image.get_rect(midbottom=(midbottom[0], midbottom[1] + 4)))


class OpenClosedScene(FindScene):
    """Two gift boxes: one OPEN with a puppy friend inside, one CLOSED."""

    category = OppositeCategory.OPEN_CLOSED

    def fx_point(self, pole: Pole, now: float = 0.0) -> tuple[int, int]:
        return (SLOT_CENTERS[self.index_of(pole)], int(GROUND_Y - GIFT_SIZE * 0.72))

    def draw_item(self, surface: pygame.Surface, pole: Pole, midbottom: tuple[int, int], now: float) -> None:
        box = pygame.Rect(0, 0, GIFT_SIZE, GIFT_SIZE)
        box.midbottom = (midbottom[0], midbottom[1] + 6)
        if pole is Pole.CLOSED:
            image = self._art.private("gift_closed", GIFT_SIZE)
            if image is not None:
                surface.blit(image, box)
            return
        back = self._art.private("gift_open_back", GIFT_SIZE)
        front = self._art.private("gift_open_front", GIFT_SIZE)
        variant = "happy" if self.cheering is Pole.OPEN else "default"
        puppy = self._art.shared("creature.pet.puppy", PUPPY_SIZE, variant=variant)
        if back is not None:
            surface.blit(back, box)
        if puppy is not None:
            # The friend peeks over the rim (pops a little higher when cheering).
            pop = int(self.hop(Pole.OPEN, now) * 0.8)
            surface.blit(puppy, puppy.get_rect(midbottom=(box.centerx, box.top + int(GIFT_SIZE * 0.71) - pop)))
        if front is not None:
            surface.blit(front, box)


class FastSlowScene(FindScene):
    """Two lanes, the same racer twice: one zooms FAST, one crawls SLOW."""

    category = OppositeCategory.FAST_SLOW

    def __init__(self, art: ContrariArt, lanes: tuple[pygame.Surface | None, pygame.Surface | None] = (None, None)) -> None:
        super().__init__(art)
        self.subject = "creature.woodland.snail"
        self._lanes = lanes
        self._t0 = 0.0
        self._slow_from = 0.0
        self._lane_y: dict[Pole, Tween] = {}

    def begin_round(self, round_: PairRound, now: float) -> None:
        super().begin_round(round_, now)
        self.subject = round_.subject or self.subject
        self._t0 = now
        self._lane_y.clear()

    def present_ask(self, ask: Ask, index: int, now: float) -> float:
        old = self.sides
        self.sides = ask.sides
        self.cheering = None
        if old is not None and old != ask.sides:
            for pole in ask.sides:
                start = self._lane_bottom(old.index(pole))
                end = self._lane_bottom(ask.sides.index(pole))
                self._lane_y[pole] = Tween(now, SWAP_SECONDS, (0.0, start), (0.0, end), 0.0)
            return self._hold(now, SWAP_SECONDS + 0.1)
        return 0.0

    def target_rects(self) -> tuple[pygame.Rect, pygame.Rect]:
        return (LANE_RECTS[0].copy(), LANE_RECTS[1].copy())

    def fx_point(self, pole: Pole, now: float = 0.0) -> tuple[int, int]:
        lane = LANE_RECTS[self.index_of(pole)]
        return (int(min(lane.right - 80, max(lane.left + 80, self.racer_x(pole, now)))), lane.top + 10)

    def racer_x(self, pole: Pole, now: float) -> float:
        span = RACE_END_X - (STAGE_LEFT - 90)
        elapsed = max(0.0, now - self._t0)
        if pole is Pole.FAST:
            return (STAGE_LEFT - 90) + (RACE_START_X - STAGE_LEFT + 90 + FAST_SPEED * elapsed) % span
        travelled = SLOW_SPEED * elapsed
        return RACE_START_X + travelled % (RACE_END_X - RACE_START_X)

    def _lane_bottom(self, index: int) -> float:
        return float(LANE_RECTS[index].bottom - 6)

    def animating(self, now: float) -> bool:
        return True  # the racers keep moving

    def draw(self, surface: pygame.Surface, now: float) -> None:
        if self.sides is None:
            return
        for index, lane in enumerate(LANE_RECTS):
            strip = self._lanes[index]
            if strip is not None:
                surface.blit(strip, strip.get_rect(midbottom=(lane.centerx, lane.bottom - 2)))
        clip = surface.get_clip()
        surface.set_clip(pygame.Rect(STAGE_LEFT, 0, surface.get_width() - STAGE_LEFT, surface.get_height()))
        for pole in self.sides:
            index = self.sides.index(pole)
            tween = self._lane_y.get(pole)
            bottom = tween.at(now)[1] if tween is not None and not tween.done(now) else self._lane_bottom(index)
            size = RACER_SIZES[index]
            x = self.racer_x(pole, now) + self._wobble_dx(index, now)
            bounce = self.hop(pole, now)
            if pole is Pole.FAST:
                bounce += abs(math.sin(now * 18.0)) * 5
                puffs = self._art.fx_frames("dust_puff")
                if puffs:
                    puff = puffs[int(now * 10) % len(puffs)]
                    surface.blit(puff, puff.get_rect(midbottom=(int(x - size * 0.62), int(bottom))))
            else:
                bounce += abs(math.sin(now * 2.0)) * 2
            racer = self._art.racer(self.subject, size)
            if racer is not None:
                surface.blit(racer, racer.get_rect(midbottom=(int(x), int(bottom - bounce))))
        surface.set_clip(clip)
        self._draw_halos(surface, now)

    def draw_item(self, surface: pygame.Surface, pole: Pole, midbottom: tuple[int, int], now: float) -> None:
        return None  # lanes are drawn by ``draw``


def build_scenes(art: ContrariArt, lanes: tuple[pygame.Surface | None, pygame.Surface | None]) -> dict[OppositeCategory, PairScene]:
    """One scene object per pair (cheap: art is shared and lazily scaled)."""

    scenes: tuple[PairScene, ...] = (
        UpDownScene(art),
        BigSmallScene(art),
        InOutScene(art),
        OpenClosedScene(art),
        FastSlowScene(art, lanes),
    )
    return {scene.category: scene for scene in scenes}


__all__ = [
    "BigSmallScene",
    "FastSlowScene",
    "FindScene",
    "InOutScene",
    "MakeScene",
    "OpenClosedScene",
    "PairScene",
    "Tween",
    "UpDownScene",
    "build_scenes",
]
