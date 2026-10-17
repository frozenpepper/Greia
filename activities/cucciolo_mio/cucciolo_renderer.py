"""Frame composition for My Cute Pet (blits only).

``SceneMotion`` holds short-lived presentation state: the pet acting out its
need (``tell``), the "not now" head shake, happy hops, bites, the ball throw,
the plaster, the sponge, a room slide, hint glows, FX and the bedtime lights.
``LilliCast`` wraps the shared ``CastFeedback`` (cheer / think) with Lilli's
point pose. ``CuccioloRenderer`` draws one frame from a ``SceneView`` (what
the app shows) plus that motion; every surface comes prepared from
``CuccioloArt``.
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
    from .cucciolo_art import FADE_LEVELS, CuccioloArt
    from .cucciolo_content import REFERENCE_WIDTH, SPECIES_BY_ID, Care, Need, Room
    from .cucciolo_layout import (
        BALL_CATCH,
        BALL_REST,
        BALL_SIZE,
        HOME_FLOOR,
        LILLI_HEIGHT,
        LILLI_MIDBOTTOM,
        NAME_PET_FLOOR,
        PET_SIZE,
        PLASTER_SIZE,
        SPONGE_SIZE,
        SPONGE_SPOTS,
        STAGES,
        pet_rect,
    )
else:
    from cucciolo_art import FADE_LEVELS, CuccioloArt
    from cucciolo_content import REFERENCE_WIDTH, SPECIES_BY_ID, Care, Need, Room
    from cucciolo_layout import (
        BALL_CATCH,
        BALL_REST,
        BALL_SIZE,
        HOME_FLOOR,
        LILLI_HEIGHT,
        LILLI_MIDBOTTOM,
        NAME_PET_FLOOR,
        PET_SIZE,
        PLASTER_SIZE,
        SPONGE_SIZE,
        SPONGE_SPOTS,
        STAGES,
        pet_rect,
    )

TELL_SECONDS = 1.0
SHAKE_SECONDS = 0.6
HOP_SECONDS = 0.45
BITE_SECONDS = 0.32
THROW_SECONDS = 0.95
PLASTER_SECONDS = 0.4
SCRUB_SECONDS = 0.5
SLIDE_SECONDS = 0.55
DIM_SECONDS = 1.2
FX_SECONDS = 0.6
WOBBLE_SECONDS = 0.4
OFFER_SECONDS = 0.7
OFFER_ICON = 96
MAX_FX = 16


class Screen(StrEnum):
    ADOPT = "adopt"
    NAME = "name"
    DAY = "day"
    END = "end"


@dataclass(frozen=True, slots=True)
class SceneView:
    """What the app wants on screen this frame (semantic, no surfaces)."""

    screen: Screen
    room: Room = Room.PLAYROOM
    species: str | None = None
    variant: str = "default"
    care: Care | None = None
    steps_done: int = 0
    dim: bool = False


def _tell_offset(need: Need, t: float) -> tuple[int, int]:
    """How the pet acts out each need (body language, never words)."""

    k = max(0.0, min(1.0, t / TELL_SECONDS))
    fade = 1.0 - k
    if need is Need.HUNGRY:  # two little bounces towards the child
        return (0, -int(abs(math.sin(t * 2 * math.pi * 2.0)) * 10 * fade))
    if need is Need.DIRTY:  # shakes itself like a wet, muddy dog
        return (int(math.sin(t * 38.0) * 7 * fade), 0)
    if need is Need.PLAYFUL:  # two springy play hops
        return (0, -int(abs(math.sin(t * 2 * math.pi * 1.0)) * 26 * fade))
    if need is Need.HURT:  # small tremble
        return (int(math.sin(t * 60.0) * 2.5 * fade), 0)
    return (int(math.sin(t * 4.0) * 7 * fade), int(abs(math.sin(t * 2.0)) * 4))  # sleepy sway


@dataclass(slots=True)
class SceneMotion:
    """Presentation-only timers (bounded; cleared when the screen changes)."""

    tell_need: Need | None = None
    tell_start: float = -10.0
    shake_start: float = -10.0
    hop_start: float = -10.0
    bite_start: float = -10.0
    throw_start: float = -10.0
    plaster_start: float = -10.0
    scrub_start: float = -10.0
    scrub_spot: int = 0
    dim_start: float = -10.0
    slide_from: Room | None = None
    slide_to: Room | None = None
    slide_start: float = -10.0
    glow_care: Care | None = None
    glow_until: float = -10.0
    pet_glow_until: float = -10.0
    wobble_care: Care | None = None
    wobble_start: float = -10.0
    offer_care: Care | None = None
    offer_start: float = -10.0
    offer_from: tuple[int, int] = (0, 0)
    offer_to: tuple[int, int] = (0, 0)
    offer_returns: bool = False
    fx: deque = field(default_factory=lambda: deque(maxlen=MAX_FX))

    def reset(self) -> None:
        self.tell_need = None
        self.tell_start = self.shake_start = self.hop_start = self.bite_start = -10.0
        self.throw_start = self.plaster_start = self.scrub_start = self.dim_start = -10.0
        self.slide_from = self.slide_to = None
        self.slide_start = -10.0
        self.glow_care = None
        self.glow_until = self.pet_glow_until = self.wobble_start = -10.0
        self.wobble_care = None
        self.offer_care = None
        self.offer_start = -10.0
        self.fx.clear()

    # -- events --
    def tell(self, need: Need, now: float) -> None:
        self.tell_need = need
        self.tell_start = now

    def shake(self, now: float) -> None:
        self.shake_start = now

    def hop(self, now: float) -> None:
        self.hop_start = now

    def slide(self, old: Room, new: Room, now: float) -> None:
        self.slide_from, self.slide_to, self.slide_start = old, new, now

    def glow(self, care: Care, now: float, seconds: float) -> None:
        self.glow_care, self.glow_until = care, now + seconds

    def wobble(self, care: Care, now: float) -> None:
        self.wobble_care, self.wobble_start = care, now

    def offer(self, care: Care, origin: tuple[int, int], target: tuple[int, int], now: float, *, returns: bool) -> None:
        """The chosen care flies to the pet (and back again for "not now")."""

        self.offer_care, self.offer_start = care, now
        self.offer_from, self.offer_to, self.offer_returns = origin, target, returns

    def offer_position(self, now: float) -> tuple[int, int] | None:
        t = now - self.offer_start
        if self.offer_care is None or not 0.0 <= t < OFFER_SECONDS:
            return None
        go, hold = 0.3, 0.45
        if t < go:
            k = 1.0 - (1.0 - t / go) ** 2
        elif t < hold or not self.offer_returns:
            k = 1.0
        else:
            k = 1.0 - (t - hold) / (OFFER_SECONDS - hold)
        if not self.offer_returns and t >= hold:
            return None
        (x0, y0), (x1, y1) = self.offer_from, self.offer_to
        lift = math.sin(math.pi * k) * 50
        return (int(x0 + (x1 - x0) * k), int(y0 + (y1 - y0) * k - lift))

    def add_fx(self, name: str, position: tuple[int, int], start: float) -> None:
        self.fx.append((name, position, start))

    def prune(self, now: float) -> None:
        while self.fx and now - self.fx[0][2] >= FX_SECONDS:
            self.fx.popleft()

    # -- queries --
    def sliding(self, now: float) -> bool:
        return self.slide_to is not None and now - self.slide_start < SLIDE_SECONDS

    def glowing(self, care: Care, now: float) -> bool:
        return self.glow_care is care and now < self.glow_until

    def wobble_offset(self, care: Care, now: float) -> int:
        t = now - self.wobble_start
        if self.wobble_care is not care or not 0.0 <= t < WOBBLE_SECONDS:
            return 0
        return int(round(math.sin(t * 40.0) * 8.0 * (1.0 - t / WOBBLE_SECONDS)))

    def pet_offset(self, now: float) -> tuple[int, int]:
        dx = dy = 0
        t = now - self.tell_start
        if self.tell_need is not None and 0.0 <= t < TELL_SECONDS:
            ox, oy = _tell_offset(self.tell_need, t)
            dx, dy = dx + ox, dy + oy
        t = now - self.shake_start
        if 0.0 <= t < SHAKE_SECONDS:  # "not now": a gentle head shake
            dx += int(math.sin(t * 30.0) * 11 * (1.0 - t / SHAKE_SECONDS))
        t = now - self.hop_start
        if 0.0 <= t < HOP_SECONDS:
            dy -= int(math.sin(math.pi * t / HOP_SECONDS) * 30)
        t = now - self.bite_start
        if 0.0 <= t < BITE_SECONDS:
            dip = math.sin(math.pi * t / BITE_SECONDS)
            dx, dy = dx + int(dip * 14), dy + int(dip * 6)
        t = now - self.throw_start
        if THROW_SECONDS * 0.3 <= t < THROW_SECONDS * 0.7:  # jump to catch the ball
            local = (t - THROW_SECONDS * 0.3) / (THROW_SECONDS * 0.4)
            dy -= int(math.sin(math.pi * local) * 46)
        return dx, dy

    def active(self, now: float) -> bool:
        if any(now - start < FX_SECONDS for _, _, start in self.fx):
            return True
        if self.sliding(now) or now < self.glow_until or now < self.pet_glow_until:
            return True
        timers = (
            (self.tell_start, TELL_SECONDS),
            (self.shake_start, SHAKE_SECONDS),
            (self.hop_start, HOP_SECONDS),
            (self.bite_start, BITE_SECONDS),
            (self.throw_start, THROW_SECONDS),
            (self.plaster_start, PLASTER_SECONDS),
            (self.scrub_start, SCRUB_SECONDS),
            (self.dim_start, DIM_SECONDS),
            (self.wobble_start, WOBBLE_SECONDS),
            (self.offer_start, OFFER_SECONDS),
        )
        return any(0.0 <= now - start < length + 0.05 for start, length in timers)


class LilliCast:
    """Lilli: shared cheer/think feedback plus a point pose (goals, hints)."""

    def __init__(self, feedback: CastFeedback, art: CuccioloArt, clock: Callable[[], float]) -> None:
        self.feedback = feedback
        self._clock = clock
        self._point = art.cast_pose("pose_point", LILLI_HEIGHT)
        self._loader = art.loader
        self._point_until = 0.0

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
        if self.pointing and self._point is not None:
            bob = int(math.sin((self._point_until - self._clock()) * 7.0) * 3)
            surface.blit(self._loader.presentable(self._point, surface), self._point.get_rect(midbottom=(LILLI_MIDBOTTOM[0], LILLI_MIDBOTTOM[1] + bob)))
            return
        self.feedback.draw(surface, LILLI_MIDBOTTOM)


class CuccioloRenderer:
    """Compose frames from prepared art (no scaling, no text)."""

    def __init__(self, art: CuccioloArt, cast: LilliCast) -> None:
        self._art = art
        self._cast = cast

    def draw(
        self,
        surface: pygame.Surface,
        view: SceneView,
        motion: SceneMotion,
        now: float,
        *,
        sun_rect: pygame.Rect | None = None,
        moon_rect: pygame.Rect | None = None,
        tray_rect: Callable[[Care], pygame.Rect | None] | None = None,
    ) -> None:
        shift = self._draw_rooms(surface, view, motion, now)
        if view.screen is Screen.NAME and view.species is not None:
            self._draw_pet(surface, view, motion, now, NAME_PET_FLOOR, shift=0)
        elif view.screen is Screen.DAY and view.species is not None:
            self._draw_stage(surface, view, motion, now, shift)
        self._draw_fx(surface, motion, now)
        if view.screen is Screen.DAY and tray_rect is not None and motion.glow_care is not None:
            self._draw_tool_glow(surface, motion, now, tray_rect)
        self._cast.draw(surface)
        if view.dim:
            self._draw_night(surface, motion, now)
        if view.screen is Screen.DAY:
            self._draw_day_strip(surface, sun_rect, moon_rect)

    # -- rooms ------------------------------------------------------------------

    def _draw_rooms(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float) -> int:
        if motion.sliding(now) and motion.slide_from is not None and motion.slide_to is not None:
            k = (now - motion.slide_start) / SLIDE_SECONDS
            ease = 1.0 - (1.0 - max(0.0, min(1.0, k))) ** 3
            shift = int(REFERENCE_WIDTH * (1.0 - ease))
            surface.blit(self._art.room(motion.slide_from), (shift - REFERENCE_WIDTH, 0))
            surface.blit(self._art.room(motion.slide_to), (shift, 0))
            return shift
        surface.blit(self._art.room(view.room), (0, 0))
        return 0

    # -- pet + care stage --------------------------------------------------------

    def _draw_stage(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float, shift: int) -> None:
        care = view.care
        if care is None:
            self._draw_pet(surface, view, motion, now, HOME_FLOOR, shift)
            if motion.pet_glow_until > now:
                self._draw_pet_glow(surface, pet_rect(HOME_FLOOR).move(shift, 0), now)
            self._draw_offer(surface, view, motion, now)
            return
        stage = STAGES[care]
        prop = stage.prop.move(shift, 0) if stage.prop is not None else None
        if care is Care.BED and prop is not None:
            back = self._art.private("bed_back.png", prop.size)
            if back is not None:
                surface.blit(back, prop)
        if motion.pet_glow_until > now:
            self._draw_pet_glow(surface, stage.target.move(shift, 0), now)
        self._draw_pet(surface, view, motion, now, stage.floor, shift)
        if care is Care.BED and prop is not None:
            front = self._art.private("bed_front.png", prop.size)
            if front is not None:
                surface.blit(front, prop)
        elif care is Care.FOOD and prop is not None:
            amount = 1.0 - view.steps_done / 3.0
            self._art.draw_bowl(surface, prop, view.species or "puppy", amount)
        elif care is Care.BALL:
            self._draw_ball(surface, motion, now, shift)
        elif care is Care.BATH:
            self._draw_sponge(surface, view, motion, now, shift)

    def _draw_offer(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float) -> None:
        position = motion.offer_position(now)
        if position is None or motion.offer_care is None:
            return
        icon = self._art.care_icon(motion.offer_care, view.species or "puppy", OFFER_ICON)
        if icon is not None:
            surface.blit(icon, icon.get_rect(center=position))

    def _pet_image(self, view: SceneView, motion: SceneMotion, now: float) -> list[pygame.Surface]:
        """Layers for the pet this frame (bath: clean art under fading mud)."""

        species = view.species or "puppy"
        if view.care is Care.BATH and view.variant == "dirty" and view.steps_done > 0:
            layers = []
            clean = self._art.pet(species, "default", PET_SIZE)
            if clean is not None:
                layers.append(clean)
            level = FADE_LEVELS[min(len(FADE_LEVELS), view.steps_done) - 1]
            faded = self._art.pet_fading(species, "dirty", PET_SIZE, level)
            if faded is not None:
                layers.append(faded)
            return layers
        image = self._art.pet(species, view.variant, PET_SIZE)
        return [image] if image is not None else []

    def _draw_pet(
        self,
        surface: pygame.Surface,
        view: SceneView,
        motion: SceneMotion,
        now: float,
        floor: tuple[int, int],
        shift: int,
    ) -> None:
        dx, dy = motion.pet_offset(now)
        rect = pet_rect(floor).move(shift + dx, dy)
        for layer in self._pet_image(view, motion, now):
            surface.blit(layer, rect)
        if view.care is Care.PLASTER and view.steps_done >= 1 and view.variant == "hurt":
            self._draw_plaster(surface, view, motion, now, rect)

    def _draw_plaster(self, surface, view: SceneView, motion: SceneMotion, now: float, rect: pygame.Rect) -> None:
        plaster = self._art.private("plaster.png", (PLASTER_SIZE, PLASTER_SIZE))
        if plaster is None:
            return
        paw = SPECIES_BY_ID[view.species or "puppy"].paw
        target = (rect.x + int(paw[0] * rect.width), rect.y + int(paw[1] * rect.height))
        t = now - motion.plaster_start
        if 0.0 <= t < PLASTER_SECONDS:  # flies in from the tray side
            k = 1.0 - (1.0 - t / PLASTER_SECONDS) ** 2
            start = (target[0] + 220, target[1] + 160)
            target = (int(start[0] + (target[0] - start[0]) * k), int(start[1] + (target[1] - start[1]) * k))
        surface.blit(plaster, plaster.get_rect(center=target))

    def _draw_ball(self, surface: pygame.Surface, motion: SceneMotion, now: float, shift: int) -> None:
        ball = self._art.shared("prop.everyday.ball", BALL_SIZE)
        if ball is None:
            return
        t = now - motion.throw_start
        rest = (BALL_REST[0] + shift, BALL_REST[1])
        catch = (BALL_CATCH[0] + shift, BALL_CATCH[1])
        if 0.0 <= t < THROW_SECONDS:
            half = THROW_SECONDS / 2
            if t < half:  # up to the pet's jump
                k = t / half
                origin, target, lift = rest, catch, 120
            else:  # and back down to rest
                k = (t - half) / half
                origin, target, lift = catch, rest, 60
            x = origin[0] + (target[0] - origin[0]) * k
            y = origin[1] + (target[1] - origin[1]) * k - math.sin(math.pi * k) * lift
            surface.blit(ball, ball.get_rect(center=(int(x), int(y))))
            return
        surface.blit(ball, ball.get_rect(center=rest))

    def _draw_sponge(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float, shift: int) -> None:
        sponge = self._art.shared("prop.everyday.sponge", SPONGE_SIZE)
        if sponge is None:
            return
        t = now - motion.scrub_start
        if 0.0 <= t < SCRUB_SECONDS:
            spot = SPONGE_SPOTS[motion.scrub_spot % len(SPONGE_SPOTS)]
            wiggle = int(math.sin(t * 30.0) * 10)
            surface.blit(sponge, sponge.get_rect(center=(spot[0] + shift + wiggle, spot[1])))
            return
        if view.variant == "dirty":
            surface.blit(sponge, sponge.get_rect(center=(760 + shift, 452)))

    def _draw_pet_glow(self, surface: pygame.Surface, rect: pygame.Rect, now: float) -> None:
        if int(now * 4) % 2:
            return
        glow = self._art.glow((rect.width + 24, rect.height + 24))
        surface.blit(glow, glow.get_rect(center=rect.center))

    def _draw_tool_glow(self, surface, motion: SceneMotion, now: float, tray_rect) -> None:
        care = motion.glow_care
        if care is None or not motion.glowing(care, now) or int(now * 3) % 2:
            return
        rect = tray_rect(care)
        if rect is None:
            return
        glow = self._art.glow((rect.width + 30, rect.height + 30))
        surface.blit(glow, glow.get_rect(center=rect.center))

    # -- overlays ------------------------------------------------------------------

    def _draw_fx(self, surface: pygame.Surface, motion: SceneMotion, now: float) -> None:
        for name, position, start in motion.fx:
            frames = self._art.fx_frames(name)
            t = now - start
            if not frames or not 0.0 <= t < FX_SECONDS:
                continue
            frame = frames[min(len(frames) - 1, int(t / FX_SECONDS * len(frames)))]
            surface.blit(frame, frame.get_rect(center=position))

    def _draw_night(self, surface: pygame.Surface, motion: SceneMotion, now: float) -> None:
        veil = self._art.night()
        t = now - motion.dim_start
        alpha = 255 if t >= DIM_SECONDS or t < 0 else int(255 * t / DIM_SECONDS)
        veil.set_alpha(alpha)
        surface.blit(veil, (0, 0))

    def _draw_day_strip(self, surface: pygame.Surface, sun_rect, moon_rect) -> None:
        if sun_rect is not None:
            sun = self._art.shared("prop.nature.sun", sun_rect.width)
            if sun is not None:
                surface.blit(sun, sun_rect)
        if moon_rect is not None:
            moon = self._art.shared("prop.vocab.moon", moon_rect.width)
            if moon is not None:
                surface.blit(moon, moon_rect)


__all__ = [
    "CuccioloRenderer",
    "HOP_SECONDS",
    "LilliCast",
    "SHAKE_SECONDS",
    "SLIDE_SECONDS",
    "SceneMotion",
    "SceneView",
    "Screen",
    "TELL_SECONDS",
    "THROW_SECONDS",
]
