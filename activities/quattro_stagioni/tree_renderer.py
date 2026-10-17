"""Frame composition for The Big Seasons Tree (blits only).

* ``SceneMotion`` holds short-lived presentation state: FX, the card flying
  into the scene (and back, when it does not belong), hint glows, card hops,
  the tree shaking when tapped.
* ``WeatherFall`` animates the chosen weather with a fixed pool of small
  prepared sprites (raindrops, snowflakes, autumn leaves).
* ``TitoCast`` is the shared ``CastFeedback`` (cheer / think) plus Tito's
  point and wave poses, and draws the clothes he wears on top of any pose.
* ``ScenePiece`` presenters draw what each dressed slot looks like; the
  renderer dispatches on the slot instead of branching on item kinds.

Every surface comes prepared from ``SeasonsArt``; nothing is scaled, decoded
or rendered as text per frame.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import math
import random
from typing import Protocol

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose
from greia_platform.pygame_blit import PreparedSurfaces

if __package__:
    from .tree_art import SeasonsArt
    from .tree_content import ITEMS, Item, Season, Slot, Weather
    from .tree_layout import (
        ANIMAL_ANCHOR,
        ANIMAL_SIZE,
        CLOUDS,
        FLYING_LIFT,
        GROUND_ANCHOR,
        GROUND_DEFAULT,
        GROUND_PIECES,
        SLOT_SPOTS,
        SUN_CENTER,
        SUN_SIZE,
        TITO_HEIGHT,
        TITO_MIDBOTTOM,
        TREE_RECT,
        prop_rect,
    )
else:
    from tree_art import SeasonsArt
    from tree_content import ITEMS, Item, Season, Slot, Weather
    from tree_layout import (
        ANIMAL_ANCHOR,
        ANIMAL_SIZE,
        CLOUDS,
        FLYING_LIFT,
        GROUND_ANCHOR,
        GROUND_DEFAULT,
        GROUND_PIECES,
        SLOT_SPOTS,
        SUN_CENTER,
        SUN_SIZE,
        TITO_HEIGHT,
        TITO_MIDBOTTOM,
        TREE_RECT,
        prop_rect,
    )

FX_SECONDS = 0.6
FLY_SECONDS = 0.38
TRY_HOLD_SECONDS = 0.55
SHAKE_SECONDS = 0.6
HOP_SECONDS = 0.5
MAX_FX = 16


@dataclass(slots=True)
class Flight:
    """A card picture flying to its slot (and back again when it does not fit)."""

    icon: pygame.Surface
    origin: tuple[int, int]
    target: tuple[int, int]
    start: float
    returning: bool
    item_id: str = ""
    slot: Slot | None = None

    @property
    def end(self) -> float:
        return self.start + (2 * FLY_SECONDS + TRY_HOLD_SECONDS if self.returning else FLY_SECONDS)

    def holding(self, now: float) -> bool:
        """True while a card that does not belong is being tried in the scene."""

        t = now - self.start
        return self.returning and FLY_SECONDS <= t < FLY_SECONDS + TRY_HOLD_SECONDS

    def position(self, now: float) -> tuple[int, int] | None:
        """Where the card picture is drawn (``None`` while tried in the scene)."""

        t = now - self.start
        if t < 0 or now >= self.end or self.holding(now):
            return None
        if t < FLY_SECONDS:
            k = _ease(t / FLY_SECONDS)
            a, b = self.origin, self.target
            lift = math.sin(math.pi * k) * 60
        else:
            k = _ease((t - FLY_SECONDS - TRY_HOLD_SECONDS) / FLY_SECONDS)
            a, b = self.target, self.origin
            lift = math.sin(math.pi * k) * 40
        x = a[0] + (b[0] - a[0]) * k
        y = a[1] + (b[1] - a[1]) * k - lift
        return (int(x), int(y))


def _ease(k: float) -> float:
    k = max(0.0, min(1.0, k))
    return 1 - (1 - k) ** 3


@dataclass(slots=True)
class SceneMotion:
    """Presentation-only timers of the current round (bounded, cleared per round)."""

    fx: deque = field(default_factory=lambda: deque(maxlen=MAX_FX))
    flights: list[Flight] = field(default_factory=list)
    slot_glow: tuple[Slot, float] | None = None
    card_hops: dict[int, float] = field(default_factory=dict)
    card_glow: tuple[int, float] | None = None
    tree_shake: float = -10.0

    def reset(self) -> None:
        self.fx.clear()
        self.flights.clear()
        self.slot_glow = None
        self.card_hops.clear()
        self.card_glow = None
        self.tree_shake = -10.0

    def add_fx(self, name: str, position: tuple[int, int], start: float) -> None:
        self.fx.append((name, position, start))

    def fly(self, flight: Flight) -> None:
        self.flights.append(flight)

    def glow_slot(self, slot: Slot, until: float) -> None:
        self.slot_glow = (slot, until)

    def hop_card(self, index: int, now: float) -> None:
        self.card_hops[index] = now

    def glow_card(self, index: int, until: float) -> None:
        self.card_glow = (index, until)

    def shake_tree(self, now: float) -> None:
        self.tree_shake = now

    def prune(self, now: float) -> None:
        self.flights = [flight for flight in self.flights if now < flight.end]
        while self.fx and now - self.fx[0][2] >= FX_SECONDS:
            self.fx.popleft()
        self.card_hops = {index: start for index, start in self.card_hops.items() if now - start < HOP_SECONDS}
        if self.slot_glow is not None and now >= self.slot_glow[1]:
            self.slot_glow = None
        if self.card_glow is not None and now >= self.card_glow[1]:
            self.card_glow = None

    def card_offset(self, index: int, now: float) -> int:
        start = self.card_hops.get(index)
        if start is None or not 0.0 <= now - start < HOP_SECONDS:
            return 0
        k = (now - start) / HOP_SECONDS
        return -int(round(abs(math.sin(2 * math.pi * k)) * 16 * (1.0 - k)))

    def tree_offset(self, now: float) -> int:
        t = now - self.tree_shake
        if 0.0 <= t < SHAKE_SECONDS:
            return int(round(math.sin(t * 34.0) * 5.0 * (1.0 - t / SHAKE_SECONDS)))
        return 0

    def active(self, now: float) -> bool:
        return bool(
            self.flights
            or self.card_hops
            or self.slot_glow
            or self.card_glow
            or any(now - start < FX_SECONDS for _, _, start in self.fx)
            or now - self.tree_shake < SHAKE_SECONDS
        )


# -- weather ---------------------------------------------------------------------


@dataclass(slots=True)
class _Mote:
    x: float
    y: float
    vx: float
    vy: float
    sprite: int
    phase: float


class WeatherFall:
    """A fixed pool of falling/blowing sprites for rain, snow or wind."""

    POOL = {Weather.RAIN: 34, Weather.SNOW: 28, Weather.WIND: 12}

    def __init__(self, weather: Weather, art: SeasonsArt, rng: random.Random | None = None) -> None:
        self.weather = weather
        self._rng = rng if rng is not None else random.Random(7)
        if weather is Weather.RAIN:
            self._sprites = [art.particle("rain", 18), art.particle("rain", 14)]
        elif weather is Weather.SNOW:
            self._sprites = [art.particle("snow", 16), art.particle("snow", 22), art.particle("snow", 12)]
        elif weather is Weather.WIND:
            self._sprites = [art.particle("leaf", 30, turn) for turn in (0, 50, 110, 200)]
        else:
            self._sprites = []
        self._sprites = [sprite for sprite in self._sprites if sprite is not None]
        self.motes = [self._spawn(initial=True) for _ in range(self.POOL.get(weather, 0) if self._sprites else 0)]

    def _spawn(self, *, initial: bool = False) -> _Mote:
        rng = self._rng
        y = rng.uniform(40, 470) if initial else rng.uniform(-30, 20)
        if self.weather is Weather.RAIN:
            return _Mote(rng.uniform(0, 1040), y, -40.0, rng.uniform(420, 520), rng.randrange(len(self._sprites)), 0.0)
        if self.weather is Weather.SNOW:
            return _Mote(rng.uniform(0, 1024), y, 0.0, rng.uniform(40, 80), rng.randrange(len(self._sprites)), rng.uniform(0, 6.28))
        x = rng.uniform(-40, 1024) if initial else rng.uniform(-60, -10)
        return _Mote(x, rng.uniform(60, 440), rng.uniform(150, 230), rng.uniform(20, 60), rng.randrange(len(self._sprites)), rng.uniform(0, 6.28))

    def update(self, dt: float) -> None:
        dt = max(0.0, min(0.1, dt))
        for index, mote in enumerate(self.motes):
            mote.phase += dt
            sway = math.sin(mote.phase * 2.0) * (24.0 if self.weather is Weather.SNOW else 40.0 if self.weather is Weather.WIND else 0.0)
            mote.x += (mote.vx + sway) * dt
            mote.y += mote.vy * dt
            if mote.y > 478 or mote.x > 1080 or mote.x < -80:
                self.motes[index] = self._spawn()

    def draw(self, surface: pygame.Surface) -> None:
        for mote in self.motes:
            sprite = self._sprites[mote.sprite]
            surface.blit(sprite, (int(mote.x), int(mote.y)))


# -- Tito ------------------------------------------------------------------------


class TitoCast:
    """Tito: shared cheer/think feedback, point/wave poses, and what he wears."""

    def __init__(self, feedback: CastFeedback, art: SeasonsArt, clock: Callable[[], float]) -> None:
        self.feedback = feedback
        self._art = art
        self._clock = clock
        self._point = art.cast_pose("pose_point")
        self._wave = art.cast_pose("pose_wave")
        self._fast = PreparedSurfaces(max_entries=4)  # RLE copies of the two poses (opaque targets only)
        self._point_until = 0.0
        self._wave_until = 0.0
        self.waving = False  # held wave (season picker)
        self._since = clock()

    @property
    def pose(self) -> CastPose:
        return self.feedback.pose

    @property
    def pointing(self) -> bool:
        return self._clock() < self._point_until and self.feedback.pose is CastPose.IDLE

    @property
    def animating(self) -> bool:
        return self.feedback.animating or self.pointing or self._clock() < self._wave_until

    def wave_for(self, seconds: float) -> None:
        """A short hello wave (Tito tapped); never a correct/try-again signal."""

        self.feedback.reset()
        self._point_until = 0.0
        self._wave_until = self._clock() + seconds

    def correct(self) -> None:
        self._point_until = 0.0
        self._since = self._clock()
        self.feedback.correct()

    def try_again(self) -> None:
        self._point_until = 0.0
        self._since = self._clock()
        self.feedback.try_again()

    def point(self, seconds: float) -> None:
        self.feedback.reset()
        self._point_until = self._clock() + seconds

    def reset(self) -> None:
        self._point_until = 0.0
        self._wave_until = 0.0
        self.feedback.reset()

    def update(self) -> bool:
        changed = self.feedback.update()
        now = self._clock()
        if self._point_until and now >= self._point_until:
            self._point_until = 0.0
            changed = True
        if self._wave_until and now >= self._wave_until:
            self._wave_until = 0.0
            changed = True
        return changed

    def _variant_and_offset(self) -> tuple[str, pygame.Surface | None, tuple[int, int]]:
        now = self._clock()
        if self.pointing:
            bob = int(math.sin((self._point_until - now) * 7.0) * 3)
            return "pose_point", self._point, (0, bob)
        pose = self.feedback.pose
        if pose is CastPose.CHEER:
            return "pose_cheer", None, self._feedback_offset(now)
        if pose is CastPose.THINK:
            return "pose_think", None, self._feedback_offset(now)
        if (self.waving or now < self._wave_until) and self._wave is not None:
            return "pose_wave", self._wave, (0, 0)
        return "happy", None, (0, 0)

    def _feedback_offset(self, now: float) -> tuple[int, int]:
        # Mirrors CastFeedback's hop/sway so worn clothes move with the pose.
        elapsed = now - self._since
        hop = CastFeedback.HOP_SECONDS
        if self.feedback.pose is CastPose.CHEER and elapsed < hop:
            return (0, -int(round(math.sin(math.pi * elapsed / hop) * TITO_HEIGHT * 0.09)))
        if self.feedback.pose is CastPose.THINK and elapsed < hop * 1.5:
            return (int(round(math.sin(2 * math.pi * elapsed / (hop * 1.5)) * TITO_HEIGHT * 0.025)), 0)
        return (0, 0)

    def draw(self, surface: pygame.Surface, worn: Item | None) -> None:
        variant, own, (dx, dy) = self._variant_and_offset()
        midbottom = (TITO_MIDBOTTOM[0] + dx, TITO_MIDBOTTOM[1] + dy)
        if own is not None:
            surface.blit(self._fast.for_target(own, surface), own.get_rect(midbottom=midbottom))
        else:
            self.feedback.draw(surface, TITO_MIDBOTTOM)
        if worn is None:
            return
        layer = self._art.wear(worn, variant)
        if layer is not None:
            image, (ox, oy) = layer
            surface.blit(image, (midbottom[0] - TITO_HEIGHT // 2 + ox, midbottom[1] - TITO_HEIGHT + oy))


# -- scene pieces ------------------------------------------------------------------


class ScenePiece(Protocol):
    """Draw one dressed slot (behind or in front of the tree, per presenter)."""

    def draw(self, surface: pygame.Surface, item: Item, now: float, motion: SceneMotion) -> None: ...


class TreePiece:
    def __init__(self, art: SeasonsArt) -> None:
        self._art = art

    def draw(self, surface: pygame.Surface, item: Item, now: float, motion: SceneMotion) -> None:
        canopy = self._art.canopy(item)
        if canopy is not None:
            surface.blit(canopy, TREE_RECT.move(motion.tree_offset(now), 0))


class SkyPiece:
    """Sun with a soft halo, or the clouds that bring rain, snow or wind."""

    def __init__(self, art: SeasonsArt) -> None:
        self._art = art

    def draw(self, surface: pygame.Surface, item: Item, now: float, motion: SceneMotion) -> None:
        if item.weather is Weather.SUN:
            halo = self._art.halo(int(SUN_SIZE * 1.6))
            surface.blit(halo, halo.get_rect(center=SUN_CENTER))
            sun = self._art.sun(SUN_SIZE)
            if sun is not None:
                bob = int(round(math.sin(now * 1.6) * 3))
                surface.blit(sun, sun.get_rect(center=(SUN_CENTER[0], SUN_CENTER[1] + bob)))
            return
        drift = 0
        if item.weather is Weather.WIND:
            drift = int(round(math.sin(now * 0.9) * 14))
        for x, y, width in CLOUDS:
            cloud = self._art.cloud(width, grey=item.weather is not Weather.WIND)
            if cloud is not None:
                surface.blit(cloud, cloud.get_rect(center=(x + drift, y)))


class GroundPiece:
    def __init__(self, art: SeasonsArt) -> None:
        self._art = art

    def draw(self, surface: pygame.Surface, item: Item, now: float, motion: SceneMotion) -> None:
        if item.scene is None:
            return
        for dx, dy, size in GROUND_PIECES.get(item.item_id, GROUND_DEFAULT):
            image = self._art.image(item.scene, size)
            if image is not None:
                surface.blit(image, prop_rect((GROUND_ANCHOR[0] + dx, GROUND_ANCHOR[1] + dy), size))


class AnimalPiece:
    def __init__(self, art: SeasonsArt) -> None:
        self._art = art

    def draw(self, surface: pygame.Surface, item: Item, now: float, motion: SceneMotion) -> None:
        if item.scene is None:
            return
        image = self._art.image(item.scene, ANIMAL_SIZE)
        if image is None:
            return
        rect = prop_rect(ANIMAL_ANCHOR, ANIMAL_SIZE)
        if item.item_id == "butterfly":
            rect.y -= FLYING_LIFT + int(round(math.sin(now * 2.4) * 8))
        surface.blit(image, rect)


@dataclass(frozen=True, slots=True)
class SceneView:
    """Everything one frame needs from the app (read-only)."""

    season: Season
    placed: Mapping[Slot, str]
    hint_slot: Slot | None = None


class TreeRenderer:
    """Compose a frame: landscape, sky, tree, meadow, friend, Tito, weather, FX."""

    def __init__(self, art: SeasonsArt, cast: TitoCast) -> None:
        self._art = art
        self._cast = cast
        self._pieces: dict[Slot, ScenePiece] = {
            Slot.SKY: SkyPiece(art),
            Slot.TREE: TreePiece(art),
            Slot.GROUND: GroundPiece(art),
            Slot.ANIMAL: AnimalPiece(art),
        }
        self.weather: WeatherFall | None = None

    def set_weather(self, weather: Weather | None, rng: random.Random | None = None) -> None:
        if weather is None or weather is Weather.SUN:
            self.weather = None
        elif self.weather is None or self.weather.weather is not weather:
            self.weather = WeatherFall(weather, self._art, rng)

    def draw(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float) -> None:
        surface.blit(self._art.backdrop(view.season), (0, 0))
        placed = {slot: ITEMS[item_id] for slot, item_id in view.placed.items()}
        # A card that does not belong is shown in its place for a moment
        # (the demonstration), then flies back to its card.
        for flight in motion.flights:
            if flight.slot is not None and flight.holding(now) and flight.slot not in placed:
                placed[flight.slot] = ITEMS[flight.item_id]
        self._glow(surface, motion, now, behind=True)
        self._piece(surface, Slot.SKY, placed, now, motion)
        trunk = self._art.trunk()
        if trunk is not None:
            surface.blit(trunk, TREE_RECT.move(motion.tree_offset(now), 0))
        self._piece(surface, Slot.TREE, placed, now, motion)
        self._piece(surface, Slot.GROUND, placed, now, motion)
        self._piece(surface, Slot.ANIMAL, placed, now, motion)
        self._cast.draw(surface, placed.get(Slot.CLOTHES))
        self._glow(surface, motion, now, behind=False)
        if self.weather is not None:
            self.weather.draw(surface)
        self._draw_fx(surface, motion, now)
        for flight in motion.flights:
            position = flight.position(now)
            if position is not None:
                surface.blit(flight.icon, flight.icon.get_rect(center=position))

    def draw_card_glow(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        glow = self._art.glow((rect.width + 44, rect.height + 40))
        surface.blit(glow, glow.get_rect(center=rect.center))

    def _piece(self, surface, slot: Slot, placed: Mapping[Slot, Item], now: float, motion: SceneMotion) -> None:
        item = placed.get(slot)
        piece = self._pieces.get(slot)
        if item is not None and piece is not None:
            piece.draw(surface, item, now, motion)

    def _glow(self, surface: pygame.Surface, motion: SceneMotion, now: float, *, behind: bool) -> None:
        if motion.slot_glow is None:
            return
        slot = motion.slot_glow[0]
        # Meadow, friend and sky glows lie behind the scene; the tree and Tito
        # glows ring their subject in front (a ring never hides it).
        on_ground = slot in (Slot.GROUND, Slot.ANIMAL, Slot.SKY)
        if on_ground != behind:
            return
        rect = SLOT_SPOTS[slot].glow
        glow = self._art.glow(rect.size)
        bob = int(round(math.sin(now * 5.0) * 3))
        surface.blit(glow, rect.move(0, bob))

    def _draw_fx(self, surface: pygame.Surface, motion: SceneMotion, now: float) -> None:
        for name, position, start in motion.fx:
            frames = self._art.fx_frames(name)
            t = now - start
            if not frames or not 0.0 <= t < FX_SECONDS:
                continue
            frame = frames[min(len(frames) - 1, int(t / FX_SECONDS * len(frames)))]
            surface.blit(frame, frame.get_rect(center=position))


__all__ = [
    "FLY_SECONDS",
    "Flight",
    "SceneMotion",
    "SceneView",
    "TRY_HOLD_SECONDS",
    "TitoCast",
    "TreeRenderer",
    "WeatherFall",
]
