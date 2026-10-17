"""Frame composition for Magic Bakery (blits only).

``SceneMotion`` holds short-lived presentation state: the customer walking
in and out, the cake sliding away and a fresh one arriving, counting badges,
wobbles, hint glows, late-hint ghosts and FX. ``CounterCast`` wraps the
shared ``CastFeedback`` (cheer / think) with the cast's wave and point poses
for whoever stands at the counter (a customer, or Momo the baker in the
make-your-own-cake ending). ``BakeryRenderer`` draws one frame from a
``SceneView`` (what the app shows) plus that motion, and flattens the child's
own cake into the picture shared with My Creations. Every surface comes
prepared from ``BakeryArt``.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
import math

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose

if __package__:
    from .pasticceria_art import BakeryArt
    from .pasticceria_content import COUNT, PATTERN, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .pasticceria_layout import (
        BUBBLE_INNER,
        PLACES,
        BUBBLE_RECT,
        CAKE_POS,
        COUNT_POINTS,
        CUSTOMER_HEIGHT,
        CUSTOMER_MIDBOTTOM,
        PATTERN_POINTS,
        PATTERN_SIZE,
        TOPPING_SIZE,
        WALK_DISTANCE,
        from_frosting,
        sprite_rect,
    )
    from .pasticceria_model import CountCake, CountOrder, FreeCake, PatternCake, PatternOrder
else:
    from pasticceria_art import BakeryArt
    from pasticceria_content import COUNT, PATTERN, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from pasticceria_layout import (
        BUBBLE_INNER,
        PLACES,
        BUBBLE_RECT,
        CAKE_POS,
        COUNT_POINTS,
        CUSTOMER_HEIGHT,
        CUSTOMER_MIDBOTTOM,
        PATTERN_POINTS,
        PATTERN_SIZE,
        TOPPING_SIZE,
        WALK_DISTANCE,
        from_frosting,
        sprite_rect,
    )
    from pasticceria_model import CountCake, CountOrder, FreeCake, PatternCake, PatternOrder

WALK_SECONDS = 0.7
CAKE_SLIDE_SECONDS = 0.6
CAKE_DROP_SECONDS = 0.35
BADGE_SECONDS = 1.1
WOBBLE_SECONDS = 0.5
FX_SECONDS = 0.6
CARD_POP_SECONDS = 0.3
BADGE_SIZE = 34
MAX_FX = 8
MAX_BADGES = 16
CAKE_EXIT = REFERENCE_WIDTH - CAKE_POS[0] + 40  # far enough right to leave the screen


class Screen(StrEnum):
    ROUND = "round"
    FREE = "free"
    END = "end"


@dataclass(frozen=True, slots=True)
class SceneView:
    """What the app wants on screen this frame (semantic, no surfaces)."""

    screen: Screen
    order: CountOrder | PatternOrder | None = None
    cake: CountCake | PatternCake | None = None
    free_cake: FreeCake | None = None
    show_card: bool = False


def _ease(k: float) -> float:
    k = max(0.0, min(1.0, k))
    return 1.0 - (1.0 - k) ** 2


@dataclass(slots=True)
class Slide:
    """One horizontal move: offset ``start_x`` -> ``end_x`` over ``seconds``."""

    start: float = -10.0
    seconds: float = 0.0
    start_x: int = 0
    end_x: int = 0

    def offset(self, now: float) -> int:
        if self.seconds <= 0:
            return self.end_x
        k = _ease((now - self.start) / self.seconds)
        return int(round(self.start_x + (self.end_x - self.start_x) * k))

    def moving(self, now: float) -> bool:
        return self.seconds > 0 and 0.0 <= now - self.start < self.seconds + 0.05


@dataclass(slots=True)
class SceneMotion:
    """Presentation-only timers (bounded; cleared when the screen changes)."""

    customer: Slide = field(default_factory=Slide)
    cake: Slide = field(default_factory=Slide)
    cake_drop_start: float = -10.0
    card_start: float = -10.0
    badges: deque = field(default_factory=lambda: deque(maxlen=MAX_BADGES))
    wobble: dict = field(default_factory=dict)
    ghosts: tuple = ()
    nudge: tuple = ()  # places that keep wobbling gently (late hint) until the cake changes
    fx: deque = field(default_factory=lambda: deque(maxlen=MAX_FX))
    card_glow_until: float = -10.0
    card_row: int | None = None
    card_row_until: float = -10.0
    tile_glow: str | None = None
    tile_glow_until: float = -10.0

    def reset(self) -> None:
        self.customer = Slide()
        self.cake = Slide()
        self.cake_drop_start = self.card_start = -10.0
        self.badges.clear()
        self.wobble.clear()
        self.ghosts = ()
        self.nudge = ()
        self.fx.clear()
        self.card_glow_until = self.card_row_until = self.tile_glow_until = -10.0
        self.card_row = None
        self.tile_glow = None

    # -- events --
    def walk(self, now: float, start_x: int, end_x: int) -> None:
        self.customer = Slide(now, WALK_SECONDS, start_x, end_x)

    def slide_cake(self, now: float, start_x: int, end_x: int, seconds: float = CAKE_SLIDE_SECONDS) -> None:
        self.cake = Slide(now, seconds, start_x, end_x)

    def drop_cake(self, now: float) -> None:
        self.cake = Slide()
        self.cake_drop_start = now

    def show_card(self, now: float) -> None:
        self.card_start = now

    def badge(self, index: int, value: int, start: float) -> None:
        self.badges.append((index, value, start))

    def shake(self, indexes, now: float) -> None:
        for index in indexes:
            self.wobble[index] = now
        while len(self.wobble) > MAX_BADGES:
            self.wobble.pop(next(iter(self.wobble)))

    def add_fx(self, name: str, position: tuple[int, int], start: float) -> None:
        self.fx.append((name, position, start))

    def glow_card(self, now: float, seconds: float) -> None:
        self.card_glow_until = now + seconds

    def highlight_row(self, row: int | None, until: float) -> None:
        self.card_row, self.card_row_until = row, until

    def glow_tile(self, topping_id: str | None, now: float, seconds: float) -> None:
        self.tile_glow, self.tile_glow_until = topping_id, now + seconds

    def prune(self, now: float) -> None:
        while self.fx and now - self.fx[0][2] >= FX_SECONDS:
            self.fx.popleft()
        while self.badges and now - self.badges[0][2] >= BADGE_SECONDS:
            self.badges.popleft()
        for index in [i for i, start in self.wobble.items() if now - start >= WOBBLE_SECONDS]:
            del self.wobble[index]

    # -- queries --
    def wobble_offset(self, index: int, now: float) -> int:
        start = self.wobble.get(index)
        if start is None and index in self.nudge:
            # Every 1.6 s a small shake: "this one does not belong".
            start = now - (now % 1.6)
        if start is None:
            return 0
        t = now - start
        if not 0.0 <= t < WOBBLE_SECONDS:
            return 0
        return int(round(math.sin(t * 38.0) * 7.0 * (1.0 - t / WOBBLE_SECONDS)))

    def cake_offset(self, now: float) -> tuple[int, int]:
        dx = self.cake.offset(now)
        t = now - self.cake_drop_start
        dy = 0
        if 0.0 <= t < CAKE_DROP_SECONDS:
            dy = -int(round(70 * (1.0 - _ease(t / CAKE_DROP_SECONDS))))
        return dx, dy

    def active(self, now: float) -> bool:
        if self.nudge:
            return True
        if any(0.0 <= now - start < FX_SECONDS for _, _, start in self.fx):
            return True
        if any(0.0 <= now - start < BADGE_SECONDS for _, _, start in self.badges):
            return True
        if any(0.0 <= now - start < WOBBLE_SECONDS for start in self.wobble.values()):
            return True
        if self.customer.moving(now) or self.cake.moving(now):
            return True
        if now < self.card_glow_until or now < self.card_row_until or now < self.tile_glow_until:
            return True
        return 0.0 <= now - self.cake_drop_start < CAKE_DROP_SECONDS + 0.05 or 0.0 <= now - self.card_start < CARD_POP_SECONDS


class CounterCast:
    """Whoever stands at the counter: shared cheer/think plus wave and point poses."""

    def __init__(self, art: BakeryArt, clock: Callable[[], float], *, height: int = CUSTOMER_HEIGHT) -> None:
        self._art = art
        self._clock = clock
        self._height = height
        self.character: str | None = None
        self.feedback: CastFeedback | None = None
        self._pose_until = 0.0
        self._pose: pygame.Surface | None = None
        self._pose_name = ""

    def set_character(self, character: str) -> None:
        if character == self.character:
            return
        self.character = character
        self.feedback = CastFeedback(character, height=self._height, art=self._art.loader, clock=self._clock)
        self._pose_until = 0.0

    @property
    def pose(self) -> CastPose | None:
        return self.feedback.pose if self.feedback is not None else None

    @property
    def posing(self) -> str:
        """``pose_point`` / ``pose_wave`` while one is held, else ``""``."""

        if self._clock() < self._pose_until and (self.feedback is None or self.feedback.pose is CastPose.IDLE):
            return self._pose_name
        return ""

    @property
    def animating(self) -> bool:
        return bool(self.posing) or (self.feedback is not None and self.feedback.animating)

    def correct(self) -> None:
        self._pose_until = 0.0
        if self.feedback is not None:
            self.feedback.correct()

    def try_again(self) -> None:
        self._pose_until = 0.0
        if self.feedback is not None:
            self.feedback.try_again()

    def point(self, seconds: float) -> None:
        self._hold("pose_point", seconds)

    def wave(self, seconds: float) -> None:
        self._hold("pose_wave", seconds)

    def _hold(self, variant: str, seconds: float) -> None:
        if self.character is None:
            return
        if self.feedback is not None:
            self.feedback.reset()
        self._pose = self._art.cast(self.character, variant, self._height)
        self._pose_name = variant
        self._pose_until = self._clock() + seconds

    def reset(self) -> None:
        self._pose_until = 0.0
        if self.feedback is not None:
            self.feedback.reset()

    def update(self) -> bool:
        changed = self.feedback.update() if self.feedback is not None else False
        if self._pose_until and self._clock() >= self._pose_until:
            self._pose_until = 0.0
            changed = True
        return changed

    def draw(self, surface: pygame.Surface, dx: int = 0) -> None:
        midbottom = (CUSTOMER_MIDBOTTOM[0] + dx, CUSTOMER_MIDBOTTOM[1])
        if self.posing and self._pose is not None:
            bob = int(math.sin((self._pose_until - self._clock()) * 7.0) * 3)
            surface.blit(self._art.loader.presentable(self._pose, surface), self._pose.get_rect(midbottom=(midbottom[0], midbottom[1] + bob)))
            return
        if self.feedback is not None:
            self.feedback.draw(surface, midbottom)


class CountCardPainter:
    """Order card for a counting order: numeral + pictures (or one picture)."""

    def draw(self, surface: pygame.Surface, art: BakeryArt, order: CountOrder, inner: pygame.Rect, highlight: int | None) -> None:
        rows = len(order.items)
        row_h = inner.height // max(1, rows)
        for row, item in enumerate(order.items):
            area = pygame.Rect(inner.x, inner.y + row * row_h, inner.width, row_h)
            if highlight == row:
                glow = art.glow((area.width + 8, area.height + 4))
                surface.blit(glow, glow.get_rect(center=area.center))
            numeral = art.numeral(item.amount, 68 if rows == 1 else 50)
            num_rect = numeral.get_rect(midleft=(area.x + 6, area.centery))
            surface.blit(numeral, num_rect)
            pics = pygame.Rect(num_rect.right + 10, area.y, area.right - num_rect.right - 12, area.height)
            if order.pictures:
                self._pictures(surface, art, item.topping_id, item.amount, pics)
            else:
                size = min(84, area.height - 10)
                icon = art.topping(item.topping_id, size)
                if icon is not None:
                    surface.blit(icon, icon.get_rect(center=pics.center))

    @staticmethod
    def _pictures(surface, art: BakeryArt, topping_id: str, amount: int, area: pygame.Rect) -> None:
        lines = 1 if amount <= 3 or area.height < 100 else 2
        per_line = math.ceil(amount / lines)
        gap = 3
        size = int(min(area.height / lines - 6, (area.width - (per_line - 1) * gap) / per_line, 80))
        icon = art.topping(topping_id, max(16, size))
        if icon is None:
            return
        drawn = 0
        top = area.centery - (lines * size + (lines - 1) * gap) // 2
        for line in range(lines):
            count = min(per_line, amount - drawn)
            width = count * size + (count - 1) * gap
            left = area.centerx - width // 2
            for column in range(count):
                surface.blit(icon, (left + column * (size + gap), top + line * (size + gap)))
            drawn += count


class PatternCardPainter:
    """Order card for a pattern order: the start of the row, then ``?`` places."""

    def draw(self, surface: pygame.Surface, art: BakeryArt, order: PatternOrder, inner: pygame.Rect, highlight: int | None) -> None:
        count = len(order.answer)
        gap = 4
        size = min(44, (inner.width - (count - 1) * gap) // count)
        left = inner.centerx - (count * size + (count - 1) * gap) // 2
        top = inner.centery - size // 2
        if highlight is not None:
            glow = art.glow((inner.width + 8, size + 24))
            surface.blit(glow, glow.get_rect(center=(inner.centerx, inner.centery)))
        for index in range(count):
            rect = pygame.Rect(left + index * (size + gap), top, size, size)
            if index < order.given:
                icon = art.topping(order.answer[index], size)
            else:
                icon = art.card_blank(size)
            if icon is not None:
                surface.blit(icon, rect)


CARD_PAINTERS = {COUNT: CountCardPainter(), PATTERN: PatternCardPainter()}


class CountCakePainter:
    """Toppings on their count places (plus late-hint ghosts on open places)."""

    def sprites(self, art: BakeryArt, cake: CountCake, motion: SceneMotion, now: float, offset):
        result = []
        for index, value in cake.placements():
            base = _moved(COUNT_POINTS[index], offset)
            icon = art.topping(value, TOPPING_SIZE)
            if icon is not None:
                rect = sprite_rect(base, TOPPING_SIZE).move(motion.wobble_offset(index, now), 0)
                result.append((base[1], icon, rect))
        for index, ghost_id in motion.ghosts:
            if 0 <= index < len(COUNT_POINTS):
                base = _moved(COUNT_POINTS[index], offset)
                ghost = art.ghost(ghost_id, TOPPING_SIZE)
                if ghost is not None:
                    result.append((base[1], ghost, sprite_rect(base, TOPPING_SIZE)))
        return result


class PatternCakePainter:
    """The pattern row: the customer's start, the child's toppings, open sockets."""

    def sprites(self, art: BakeryArt, cake: PatternCake, motion: SceneMotion, now: float, offset):
        result = []
        ghosts = dict(motion.ghosts)
        for index, value in enumerate(cake.row()):
            base = _moved(PATTERN_POINTS[index], offset)
            if value is None:
                socket = art.socket(PATTERN_SIZE - 6)
                # Sockets lie flat on the frosting, under every topping.
                result.append((-1, socket, socket.get_rect(center=(base[0], base[1] - 4))))
                ghost_id = ghosts.get(index)
                if ghost_id is not None:
                    ghost = art.ghost(ghost_id, PATTERN_SIZE)
                    if ghost is not None:
                        result.append((base[1], ghost, sprite_rect(base, PATTERN_SIZE)))
                continue
            icon = art.topping(value, PATTERN_SIZE)
            if icon is not None:
                rect = sprite_rect(base, PATTERN_SIZE).move(motion.wobble_offset(index, now), 0)
                result.append((base[1], icon, rect))
            ghost_id = ghosts.get(index)
            if ghost_id is not None and ghost_id != value:
                ghost = art.ghost(ghost_id, PATTERN_SIZE)
                if ghost is not None:
                    result.append((base[1] + 1, ghost, sprite_rect(base, PATTERN_SIZE).move(0, -PATTERN_SIZE // 2)))
        return result


CAKE_PAINTERS = {COUNT: CountCakePainter(), PATTERN: PatternCakePainter()}


class BakeryRenderer:
    """Compose frames from prepared art (no scaling, no text construction per frame)."""

    def __init__(self, art: BakeryArt, cast: CounterCast) -> None:
        self._art = art
        self._cast = cast

    def draw(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float, *, tile_rect=None) -> None:
        surface.blit(self._art.backdrop(), (0, 0))
        if view.screen is Screen.END:
            return
        self._cast.draw(surface, motion.customer.offset(now))
        if view.show_card and view.order is not None and view.screen is Screen.ROUND:
            self._draw_card(surface, view.order, motion, now)
        dx, dy = motion.cake_offset(now)
        surface.blit(self._art.cake(), (CAKE_POS[0] + dx, CAKE_POS[1] + dy))
        if view.screen is Screen.FREE and view.free_cake is not None:
            self._draw_free(surface, view.free_cake, motion, now, (dx, dy))
        elif view.cake is not None and view.order is not None:
            self._draw_cake_top(surface, view.order, view.cake, motion, now, (dx, dy))
        self._draw_badges(surface, view, motion, now, (dx, dy))
        if tile_rect is not None:
            self._draw_tile_glow(surface, motion, now, tile_rect)
        self._draw_fx(surface, motion, now)

    # -- the order card ---------------------------------------------------------------

    def _draw_card(self, surface: pygame.Surface, order, motion: SceneMotion, now: float) -> None:
        t = now - motion.card_start
        lift = int(round(18 * (1.0 - _ease(t / CARD_POP_SECONDS)))) if 0.0 <= t < CARD_POP_SECONDS else 0
        if now < motion.card_glow_until and int(now * 3) % 2 == 0:
            body = BUBBLE_RECT.height * 164 // 206  # the bubble body without its tail
            glow = self._art.glow((BUBBLE_RECT.width + 20, body + 20))
            surface.blit(glow, glow.get_rect(center=(BUBBLE_RECT.centerx, BUBBLE_RECT.top + body // 2 + lift)))
        surface.blit(self._art.bubble(), (BUBBLE_RECT.x, BUBBLE_RECT.y + lift))
        highlight = motion.card_row if now < motion.card_row_until else None
        painter = CARD_PAINTERS.get(order.kind)
        if painter is not None:
            painter.draw(surface, self._art, order, BUBBLE_INNER.move(0, lift), highlight)

    # -- the cake ---------------------------------------------------------------------

    def _draw_cake_top(self, surface, order, cake, motion: SceneMotion, now: float, offset: tuple[int, int]) -> None:
        painter = CAKE_PAINTERS.get(order.kind)
        if painter is None:
            return
        sprites = painter.sprites(self._art, cake, motion, now, offset)
        for _, icon, rect in sorted(sprites, key=lambda item: item[0]):
            surface.blit(icon, rect)

    def _draw_free(self, surface, cake: FreeCake, motion: SceneMotion, now: float, offset: tuple[int, int]) -> None:
        order = sorted(range(len(cake.toppings)), key=lambda i: cake.toppings[i].v)
        for index in order:
            topping = cake.toppings[index]
            base = _moved(from_frosting(topping.u, topping.v), offset)
            icon = self._art.topping(topping.topping_id, TOPPING_SIZE)
            if icon is not None:
                surface.blit(icon, sprite_rect(base, TOPPING_SIZE).move(motion.wobble_offset(index, now), 0))

    def _draw_badges(self, surface, view: SceneView, motion: SceneMotion, now: float, offset) -> None:
        if view.order is None or view.order.kind not in PLACES:
            return
        points, size = PLACES[view.order.kind]
        for index, value, start in motion.badges:
            t = now - start
            if not 0.0 <= t < BADGE_SECONDS or not 0 <= index < len(points):
                continue
            base = _moved(points[index], offset)
            rise = int(round(10 * _ease(t / 0.25)))
            badge = self._art.badge(value, BADGE_SIZE)
            surface.blit(badge, badge.get_rect(midbottom=(base[0], base[1] - size - 2 - rise)))

    def _draw_tile_glow(self, surface, motion: SceneMotion, now: float, tile_rect) -> None:
        if motion.tile_glow is None or now >= motion.tile_glow_until or int(now * 3) % 2:
            return
        rect = tile_rect(motion.tile_glow)
        if rect is None:
            return
        glow = self._art.glow((rect.width + 30, rect.height + 30))
        surface.blit(glow, glow.get_rect(center=rect.center))

    def _draw_fx(self, surface: pygame.Surface, motion: SceneMotion, now: float) -> None:
        for name, position, start in motion.fx:
            frames = self._art.fx_frames(name)
            t = now - start
            if not frames or not 0.0 <= t < FX_SECONDS:
                continue
            frame = frames[min(len(frames) - 1, int(t / FX_SECONDS * len(frames)))]
            surface.blit(frame, frame.get_rect(center=position))

    # -- the shared picture -------------------------------------------------------------

    def picture(self, cake: FreeCake) -> pygame.Surface:
        """The child's cake in the shop, without controls or cast (1024x600, opaque)."""

        frame = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        frame.blit(self._art.backdrop(), (0, 0))
        frame.blit(self._art.cake(), CAKE_POS)
        self._draw_free(frame, cake, SceneMotion(), 0.0, (0, 0))
        return frame


def _moved(point: tuple[int, int], offset: tuple[int, int]) -> tuple[int, int]:
    return (point[0] + offset[0], point[1] + offset[1])


__all__ = [
    "BADGE_SECONDS",
    "CAKE_DROP_SECONDS",
    "CAKE_EXIT",
    "CAKE_SLIDE_SECONDS",
    "BakeryRenderer",
    "CounterCast",
    "SceneMotion",
    "SceneView",
    "Screen",
    "WALK_DISTANCE",
    "WALK_SECONDS",
]
