"""Scene drawing for Il Volo del Draghetto (blits only, cached art).

``FlightRenderer`` draws one flight frame back to front: the course
backdrop, parallax decor and clouds, bouncy clouds, ring back halves,
stars/gems, the finish rainbow, hint dots, the dragon, ring front halves (so
the dragon flies *through* each ring), feedback FX, foreground clouds, the
idle-hint input glyph and Flash. Every alpha sprite is blitted through a
bounded ``PreparedSurfaces`` cache (SDL RLE copies): on the Acer a plain
per-pixel-alpha blit costs ~0.22 us/px, so the 900 px finish rainbow alone
took ~90 ms a frame. ``MapRenderer`` draws the pre-flight sky map
behind its kit controls. ``FlashCast`` wraps the shared ``CastFeedback`` with a
pointing pose and a peek-in/out from the bottom-left corner.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
import math

import pygame

from greia_platform.activity_feedback import CastFeedback
from greia_platform.pygame_blit import PreparedSurfaces

try:
    from dragon_art import DragonArt
    from dragon_courses import CourseSpec
    from dragon_model import (
        DRAGON_SCREEN_X,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        RING_MOVE_SECONDS,
        FlightRun,
        PickupKind,
    )
except ImportError:  # pragma: no cover - package import path
    from .dragon_art import DragonArt
    from .dragon_courses import CourseSpec
    from .dragon_model import (
        DRAGON_SCREEN_X,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        RING_MOVE_SECONDS,
        FlightRun,
        PickupKind,
    )

FX_SECONDS = 0.5
MAX_FX = 24
MID_PARALLAX = 0.22
DECOR_PARALLAX = 0.38
FRONT_PARALLAX = 1.35
DECOR_PERIOD = 1700
CAST_HEIGHT = 150
CAST_MARGIN = 14
PEEK_SECONDS = 0.28
FINISH_WIDTH = 900
STAR_SIZE = 46
GEM_SIZE = 54
CLOUD_WIDTH = 176
GUIDE_DOTS = 7


@dataclass(slots=True)
class FxBurst:
    kind: str
    x: float
    y: float
    start: float
    size: int
    world: bool = True


@dataclass
class FlightMotion:
    """Transient presentation state (bounded): FX, hint and guide timers."""

    fx: deque[FxBurst] = field(default_factory=lambda: deque(maxlen=MAX_FX))
    guide_until: float = -1.0
    hint_glyphs: tuple[str, ...] = ()
    hint_since: float = -1.0
    ring_pulse_until: float = -1.0

    def add(self, kind: str, x: float, y: float, now: float, size: int = 96, *, world: bool = True) -> None:
        self.fx.append(FxBurst(kind, x, y, now, size, world))

    def prune(self, now: float) -> None:
        while self.fx and now - self.fx[0].start > FX_SECONDS + 1.5:
            self.fx.popleft()

    def clear(self) -> None:
        self.fx.clear()
        self.guide_until = -1.0
        self.hint_glyphs = ()
        self.ring_pulse_until = -1.0

    def active(self, now: float) -> bool:
        return any(0.0 <= now - burst.start <= FX_SECONDS for burst in self.fx)


class FlashCast:
    """Flash peeks in from the bottom-left to cheer, think or point."""

    def __init__(
        self,
        feedback: CastFeedback,
        point: pygame.Surface | None,
        clock: Callable[[], float],
        height: int = CAST_HEIGHT,
    ) -> None:
        self.feedback = feedback
        self._point = point
        self._clock = clock
        self.height = height
        self._mode = "hidden"
        self._shown_at = -10.0
        self._until = -10.0
        #: Optional RLE cache shared with the renderer (set by ``FlightRenderer``).
        self.fast: PreparedSurfaces | None = None

    @property
    def visible(self) -> bool:
        return self._clock() < self._until + PEEK_SECONDS

    @property
    def mode(self) -> str:
        return self._mode if self.visible else "hidden"

    def _show(self, mode: str, seconds: float) -> None:
        now = self._clock()
        if not self.visible:
            self._shown_at = now
        self._mode = mode
        self._until = now + seconds

    def cheer(self, seconds: float = 1.8) -> None:
        self.feedback.correct()
        self._show("cheer", seconds)

    def think(self, seconds: float = 2.0) -> None:
        self.feedback.try_again()
        self._show("think", seconds)

    def point(self, seconds: float = 2.2) -> None:
        self.feedback.reset()
        self._show("point", seconds)

    def hide(self) -> None:
        self._until = -10.0
        self.feedback.reset()

    def update(self) -> bool:
        changed = self.feedback.update()
        return changed or self.visible

    def _peek(self) -> float:
        now = self._clock()
        rise = min(1.0, (now - self._shown_at) / PEEK_SECONDS)
        fall = min(1.0, max(0.0, (self._until + PEEK_SECONDS - now) / PEEK_SECONDS))
        return max(0.0, min(rise, fall))

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return
        peek = self._peek()
        base_x = CAST_MARGIN + self.height // 2
        base_y = REFERENCE_HEIGHT + int((1.0 - peek) * (self.height + 10)) - 4
        if self._mode == "point" and self._point is not None:
            point = self._point if self.fast is None else self.fast(self._point)
            surface.blit(point, point.get_rect(midbottom=(base_x, base_y)))
        else:
            self.feedback.draw(surface, (base_x, base_y))


class FlightRenderer:
    """Compose one flight frame from cached art (no scaling or text here)."""

    def __init__(self, art: DragonArt, cast: FlashCast, glyph: Callable[[str, int], pygame.Surface | None]) -> None:
        self._art = art
        self._cast = cast
        self._glyph = glyph
        # Every sprite the flight blits is a stable cached object: blit its
        # RLE copy (bounded by entries and pixels; see greia_platform.pygame_blit).
        self.fast = PreparedSurfaces(max_entries=96, max_pixels=1024 * 600 * 3)
        cast.fast = self.fast
        self._dot = _guide_dot(20)
        self._spec: CourseSpec | None = None
        self._finish: pygame.Surface | None = None

    def prepare(self, spec: CourseSpec) -> None:
        """Warm the per-course caches before the first frame."""

        self._spec = spec
        self._art.backdrop(spec)
        fast = self.fast
        for sprite, _x, _y in (*self._art.decor(spec), *self._art.mid_clouds, *self._art.front_clouds):
            fast(sprite)
        self._finish = self._art.finish_rainbow(FINISH_WIDTH)
        # Encode the big finish rainbow now, not on the frame it scrolls in.
        fast(self._finish)

    def draw(
        self,
        surface: pygame.Surface,
        run: FlightRun,
        frames: tuple[pygame.Surface, ...],
        motion: FlightMotion,
        now: float,
    ) -> None:
        spec = run.spec
        if self._spec is not spec:
            self.prepare(spec)
        distance = run.distance
        fast = self.fast
        surface.blit(self._art.backdrop(spec), (0, 0))
        _draw_repeating(surface, self._art.decor(spec), distance * DECOR_PARALLAX, DECOR_PERIOD, fast)
        _draw_repeating(surface, self._art.mid_clouds, distance * MID_PARALLAX, REFERENCE_WIDTH, fast)
        self._draw_clouds(surface, run)
        rings = self._ring_positions(run)
        for back, _front, pos in rings:
            surface.blit(back, back.get_rect(center=pos))
        self._draw_pickups(surface, run)
        self._draw_finish(surface, run)
        if now < motion.guide_until:
            self._draw_guide(surface, run, now)
        frame = fast(frames[run.flier.wing_frame])
        bob = math.sin(run.time * 3.2) * 3.0
        surface.blit(frame, self._art.dragon_rect(frame, (DRAGON_SCREEN_X, run.flier.y + bob)))
        for _back, front, pos in rings:
            surface.blit(front, front.get_rect(center=pos))
        self._draw_ring_pulse(surface, run, motion, now)
        self._draw_fx(surface, run, motion, now)
        _draw_repeating(surface, self._art.front_clouds, distance * FRONT_PARALLAX, REFERENCE_WIDTH, fast)
        self._draw_hint(surface, run, motion, now)
        self._cast.draw(surface)

    # -- pieces ------------------------------------------------------------

    def _draw_clouds(self, surface: pygame.Surface, run: FlightRun) -> None:
        sprite = self.fast(self._art.cloud(CLOUD_WIDTH))
        if sprite is None:
            return
        half = sprite.get_width() // 2 + 4
        for cloud in run.course.clouds:
            sx = run.screen_x(cloud.x)
            if sx < -half or sx > REFERENCE_WIDTH + half:
                continue
            squish = run.time - cloud.bumped_at
            wobble = math.sin(squish * 30.0) * 6.0 * (1.0 - squish / 0.4) if 0.0 <= squish < 0.4 else 0.0
            surface.blit(sprite, sprite.get_rect(center=(int(sx), int(cloud.y + wobble))))

    def _ring_positions(self, run: FlightRun) -> list[tuple[pygame.Surface, pygame.Surface, tuple[int, int]]]:
        placed = []
        for ring in run.course.rings:
            x, y = ring.x, ring.y
            if ring.moved_from is not None:
                t = (run.time - ring.moved_at) / RING_MOVE_SECONDS
                if 0.0 <= t < 1.0:
                    ease = 1.0 - (1.0 - t) ** 3
                    fx, fy = ring.moved_from
                    x = fx + (ring.x - fx) * ease
                    y = fy + (ring.y - fy) * ease - math.sin(math.pi * t) * 60.0
            sx = run.screen_x(x)
            back, front = self._art.ring(ring.half_open)
            back, front = self.fast(back), self.fast(front)
            if -back.get_width() < sx < REFERENCE_WIDTH + back.get_width():
                placed.append((back, front, (int(sx), int(y))))
        return placed

    def _draw_pickups(self, surface: pygame.Surface, run: FlightRun) -> None:
        star = self.fast(self._art.star(STAR_SIZE))
        gem = self.fast(self._art.gem(GEM_SIZE))
        left = run.distance - DRAGON_SCREEN_X - 60
        right = left + REFERENCE_WIDTH + 120
        for pickup in run.course.pickups:
            if pickup.x < left:
                continue
            if pickup.x > right:
                break
            if pickup.taken:
                continue
            sprite = gem if pickup.kind is PickupKind.GEM else star
            if sprite is None:
                continue
            bob = math.sin(run.time * 3.0 + pickup.x * 0.013) * 5.0
            surface.blit(sprite, sprite.get_rect(center=(int(run.screen_x(pickup.x)), int(pickup.y + bob))))

    def _draw_finish(self, surface: pygame.Surface, run: FlightRun) -> None:
        if self._finish is None:
            return
        sx = run.screen_x(run.course.finish_x)
        half = self._finish.get_width() // 2
        if -half < sx < REFERENCE_WIDTH + half:
            finish = self.fast(self._finish)
            surface.blit(finish, finish.get_rect(midbottom=(int(sx), REFERENCE_HEIGHT + 30)))

    def _draw_guide(self, surface: pygame.Surface, run: FlightRun, now: float) -> None:
        ring = run.next_ring
        if ring is None:
            return
        sx = run.screen_x(ring.x)
        if sx <= DRAGON_SCREEN_X + 60:
            return
        x0, y0 = DRAGON_SCREEN_X + 70, run.flier.y
        x1, y1 = min(sx - 40, REFERENCE_WIDTH - 20), ring.y
        phase = (now * 2.0) % 1.0
        dot = self.fast(self._dot)
        for i in range(GUIDE_DOTS):
            t = (i + phase) / GUIDE_DOTS
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * (t * t * (3 - 2 * t))
            surface.blit(dot, dot.get_rect(center=(int(x), int(y))))

    def _draw_ring_pulse(self, surface: pygame.Surface, run: FlightRun, motion: FlightMotion, now: float) -> None:
        if now >= motion.ring_pulse_until:
            return
        ring = run.next_ring
        if ring is None:
            return
        sx = run.screen_x(ring.x)
        if not 0 < sx < REFERENCE_WIDTH:
            return
        frame = int(now * 6) % 2
        sparkle = self.fast(self._art.fx("sparkle", frame, 84))
        if sparkle is not None:
            top = ring.y - ring.half_open - 40
            surface.blit(sparkle, sparkle.get_rect(center=(int(sx), int(top))))
            surface.blit(sparkle, sparkle.get_rect(center=(int(sx), int(ring.y + ring.half_open + 40))))

    def _draw_fx(self, surface: pygame.Surface, run: FlightRun, motion: FlightMotion, now: float) -> None:
        for burst in motion.fx:
            age = now - burst.start
            if not 0.0 <= age <= FX_SECONDS:
                continue
            count = self._art.fx_frames(burst.kind)
            frame = min(count - 1, int(age / FX_SECONDS * count))
            sprite = self.fast(self._art.fx(burst.kind, frame, burst.size))
            if sprite is None:
                continue
            x = run.screen_x(burst.x) if burst.world else burst.x
            surface.blit(sprite, sprite.get_rect(center=(int(x), int(burst.y))))

    def _draw_hint(self, surface: pygame.Surface, run: FlightRun, motion: FlightMotion, now: float) -> None:
        if not motion.hint_glyphs or motion.hint_since < 0:
            return
        pulse = 1.0 if int((now - motion.hint_since) * 2.5) % 2 == 0 else 0.0
        size = 56
        x = DRAGON_SCREEN_X - 20
        y = run.flier.y - 118 - int(pulse * 6)
        if y < 96:
            y = run.flier.y + 70
        total = len(motion.hint_glyphs) * size + (len(motion.hint_glyphs) - 1) * 8
        left = x - total // 2
        for index, glyph_id in enumerate(motion.hint_glyphs):
            glyph = self.fast(self._glyph(glyph_id, size))
            if glyph is not None:
                surface.blit(glyph, (left + index * (size + 8), int(y)))


class MapRenderer:
    """The sky map behind the course tiles: sky, clouds, island, dragon."""

    def __init__(self, art: DragonArt, spec: CourseSpec, fast: PreparedSurfaces | None = None) -> None:
        self._art = art
        self._spec = spec
        self.fast = fast if fast is not None else PreparedSurfaces(max_entries=48)

    def draw(self, surface: pygame.Surface, frames: tuple[pygame.Surface, ...], now: float, center: tuple[int, int]) -> None:
        fast = self.fast
        surface.blit(self._art.backdrop(self._spec), (0, 0))
        _draw_repeating(surface, self._art.mid_clouds, now * 8.0, REFERENCE_WIDTH, fast)
        isle = fast(self._art.island(300))
        if isle is not None:
            surface.blit(isle, isle.get_rect(midtop=(center[0], center[1] + 70)))
        frame = fast(frames[(0, 1, 2, 1)[int(now * 4.5) % 4]])
        bob = math.sin(now * 2.4) * 8.0
        surface.blit(frame, self._art.dragon_rect(frame, (center[0], center[1] + bob)))
        _draw_repeating(surface, self._art.front_clouds, now * 14.0, REFERENCE_WIDTH, fast)


def _draw_repeating(
    surface: pygame.Surface,
    sprites,
    offset: float,
    period: int,
    fast: Callable[[pygame.Surface], pygame.Surface] | None = None,
) -> None:
    shift = int(offset) % period
    width = surface.get_width()
    for sprite, x, y in sprites:
        if fast is not None:
            sprite = fast(sprite)
        base = x - shift
        w = sprite.get_width()
        for sx in (base, base + period, base - period):
            if -w < sx < width:
                surface.blit(sprite, (sx, y))


def _guide_dot(size: int) -> pygame.Surface:
    dot = pygame.Surface((size, size), pygame.SRCALPHA)
    r = size // 2
    pygame.draw.circle(dot, (75, 55, 47), (r, r), r)
    pygame.draw.circle(dot, (255, 194, 52), (r, r), r - 3)
    pygame.draw.circle(dot, (255, 251, 235), (r - 2, r - 2), max(1, r // 3))
    return dot


__all__ = ["FlashCast", "FlightMotion", "FlightRenderer", "FxBurst", "MapRenderer"]
