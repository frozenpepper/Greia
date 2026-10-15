"""Baia delle Orche — domain model (no Pygame).

The pod of three orcas (Kiko the calf, Luna the acrobat, Oskar the elder), the
food the child drops, the floating toys, short library FX and the bay's
persistent counters. Everything here is plain Python so the behaviour can be
unit-tested headlessly; the renderer only reads it and the app drives it.
"""

from __future__ import annotations

from enum import Enum
import math
import random
from typing import Any

try:
    from orca_content import (
        BALL_START,
        FACT_KEYS,
        FACT_SECONDS,
        HAPPY_SECONDS,
        HOOP_POSITION,
        MAX_EFFECTS,
        MAX_FOODS,
        MAX_SAVED_COUNTER,
        MAX_SAVED_STARS,
        NAME_TAG_SECONDS,
        ORCA_MAX_Y,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SAVE_SCHEMA,
        WATER_SURFACE_Y,
        FoodType,
        Tool,
    )
except ImportError:
    from .orca_content import (
        BALL_START,
        FACT_KEYS,
        FACT_SECONDS,
        HAPPY_SECONDS,
        HOOP_POSITION,
        MAX_EFFECTS,
        MAX_FOODS,
        MAX_SAVED_COUNTER,
        MAX_SAVED_STARS,
        NAME_TAG_SECONDS,
        ORCA_MAX_Y,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SAVE_SCHEMA,
        WATER_SURFACE_Y,
        FoodType,
        Tool,
    )


class OrcaState(Enum):
    SWIMMING = "swimming"
    SEEKING_FOOD = "seeking_food"
    EATING = "eating"
    BREACHING = "breaching"
    RING_LEAP = "ring_leap"
    BALL_PLAY = "ball_play"
    CUDDLE_BELLY = "cuddle_belly"
    SINGING = "singing"
    SLEEPING = "sleeping"


def safe_counter(value: Any, limit: int = MAX_SAVED_COUNTER) -> int:
    """Corrupt persisted counters must not crash the first frame or grow unbounded."""

    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(0, min(parsed, limit))


class OrcaEntity:
    """One orca with its personality (size, speed), motion and mood timers."""

    def __init__(
        self,
        orca_id: str,
        name_key: str,
        role: str,
        x: float,
        y: float,
        scale: float = 1.0,
        speed: float = 1.6,
        rng: random.Random | None = None,
    ) -> None:
        self._rng = rng or random.Random()
        self.id = orca_id
        self.name_key = name_key
        self.role = role
        self.x = x
        self.y = y
        self.scale = scale
        self.base_speed = speed
        self.vx = speed * (1.0 if self._rng.random() < 0.5 else -1.0)
        self.vy = 0.0
        self.target_vx = self.vx
        self.target_vy = 0.0
        self.facing = 1 if self.vx >= 0 else -1
        self.angle = 0.0
        self.target_angle = 0.0
        self.mouth_open = 0.0
        self.swim_phase = self._rng.random() * 6.28

        self.state = OrcaState.SWIMMING
        self.state_timer = 0.0
        self.jump_origin_y = y
        self.jump_peak_h = 160.0 * scale
        self.cuddle_happiness = 0.0
        self.craved_food = self._rng.choice(list(FoodType))
        self.jump_target_x = x
        # Short presentation timers (seconds): happy face and name tag.
        self.happy_t = 0.0
        self.name_t = 0.0

    @property
    def width(self) -> float:
        return 165.0 * self.scale

    @property
    def height(self) -> float:
        return 85.0 * self.scale

    @property
    def max_y(self) -> float:
        """Deepest centre for this orca (its body stays above the toolbar)."""

        return ORCA_MAX_Y - 62.0 * self.scale

    @property
    def is_happy(self) -> bool:
        return self.happy_t > 0.0 or self.state in (
            OrcaState.CUDDLE_BELLY,
            OrcaState.SINGING,
            OrcaState.EATING,
        )

    @property
    def airborne(self) -> bool:
        return self.state in (OrcaState.BREACHING, OrcaState.RING_LEAP)

    def hit_test(self, px: float, py: float) -> bool:
        w = self.width * 1.25
        h = self.height * 1.25
        return (self.x - w / 2 <= px <= self.x + w / 2) and (self.y - h / 2 <= py <= self.y + h / 2)

    def cheer(self, seconds: float = HAPPY_SECONDS) -> None:
        self.happy_t = max(self.happy_t, seconds)

    def show_name(self, seconds: float = NAME_TAG_SECONDS) -> None:
        self.name_t = seconds

    def trigger_cuddle(self) -> None:
        self.state = OrcaState.CUDDLE_BELLY
        self.state_timer = 2.8
        self.cuddle_happiness = min(1.0, self.cuddle_happiness + 0.4)
        self.vy = -1.2
        self.target_angle = 15.0 * (1 if self._rng.random() < 0.5 else -1)

    def trigger_breach(self, jump_x: float, height_bonus: float = 0.0) -> None:
        self.state = OrcaState.BREACHING
        self.state_timer = 0.0
        self.jump_origin_y = max(WATER_SURFACE_Y + 40.0, self.y)
        self.jump_target_x = jump_x
        self.jump_peak_h = (155.0 + height_bonus) * self.scale
        self.facing = 1 if jump_x >= self.x else -1

    def trigger_ring_jump(self, ring_x: float, ring_y: float = HOOP_POSITION[1]) -> None:
        """Leap over the floating hoop: the arc's top reaches the hoop's middle."""

        self.state = OrcaState.RING_LEAP
        self.state_timer = 0.0
        self.jump_origin_y = max(WATER_SURFACE_Y + 40.0, self.y)
        self.facing = 1 if ring_x >= self.x else -1
        # The arc moves ~half way to its target by the apex: aim past the hoop.
        self.jump_target_x = ring_x + (ring_x - self.x)
        self.jump_peak_h = max(80.0, self.jump_origin_y - ring_y)

    def trigger_sing(self, note_idx: int) -> None:
        self.state = OrcaState.SINGING
        self.state_timer = 1.6
        self.vy = -1.5
        self.mouth_open = 1.0

    def update(self, dt: float, foods: list["FoodEntity"], toys: list["ToyEntity"], night_mode: bool) -> list[str]:
        """Advance physics, mood timers and state; return sound/feedback cues."""

        events: list[str] = []
        self.swim_phase += 0.08 * (self.base_speed / 1.5)
        self.happy_t = max(0.0, self.happy_t - dt)
        self.name_t = max(0.0, self.name_t - dt)
        self.cuddle_happiness = max(0.0, self.cuddle_happiness - dt * 0.05)

        # Night time: the pod rests near the surface.
        if night_mode and self.state == OrcaState.SWIMMING:
            self.state = OrcaState.SLEEPING
        elif not night_mode and self.state == OrcaState.SLEEPING:
            self.state = OrcaState.SWIMMING

        if self.state not in (OrcaState.EATING, OrcaState.SINGING):
            self.mouth_open = max(0.0, self.mouth_open - dt * 3.0)

        if self.state == OrcaState.SLEEPING:
            self.vx *= 0.94
            self.vy = math.sin(self.swim_phase * 0.5) * 0.4
            self.y = min(self.max_y, self.y + self.vy)
            self.x += self.vx
            self.angle += (0.0 - self.angle) * 0.05
            self._keep_in_bay()
            return events

        if self.state == OrcaState.CUDDLE_BELLY:
            self.state_timer -= dt
            self.vx *= 0.90
            self.vy = math.sin(self.swim_phase * 1.5) * 0.6
            self.y = max(WATER_SURFACE_Y + 10.0, min(self.max_y, self.y + self.vy))
            self.angle += (self.target_angle - self.angle) * 0.1
            if self.state_timer <= 0:
                self.state = OrcaState.SWIMMING
            return events

        if self.state == OrcaState.SINGING:
            self.state_timer -= dt
            self.vx *= 0.92
            self.y = max(WATER_SURFACE_Y + 10.0, min(self.max_y, self.y + math.sin(self.swim_phase * 2.0) * 0.8))
            self.mouth_open = min(1.0, self.mouth_open + dt * 4.0)
            self.angle += (-15.0 * self.facing - self.angle) * 0.12
            if self.state_timer <= 0:
                self.state = OrcaState.SWIMMING
            return events

        if self.state == OrcaState.EATING:
            self.state_timer -= dt
            self.vx *= 0.85
            self.y += math.sin(self.swim_phase * 2.5) * 0.5
            self.mouth_open = min(1.0, self.mouth_open + dt * 5.0)
            if self.state_timer <= 0:
                self.craved_food = self._rng.choice(list(FoodType))
                self.state = OrcaState.SWIMMING
            return events

        if self.state in (OrcaState.BREACHING, OrcaState.RING_LEAP):
            self.state_timer += dt * 1.2
            progress = self.state_timer
            if progress < 1.0:
                h = math.sin(progress * math.pi) * self.jump_peak_h
                self.y = self.jump_origin_y - h
                # Graceful pitch: nose up on the way out, nose down for the dive.
                self.angle = (-20.0 + progress * 40.0) * self.facing
                self.x += (self.jump_target_x - self.x) * 0.05 + (self.facing * self.base_speed * 1.4)
                # Keep the whole body on screen at the top of the arc.
                half = 112.0 * self.scale
                self.x = max(half, min(REFERENCE_WIDTH - half, self.x))
            else:
                self.y = WATER_SURFACE_Y + 30.0
                self.vy = 1.5
                self.angle = 0.0
                self.state = OrcaState.SWIMMING
                events.append("splash")
                events.append("whistle")
            return events

        seeking = False
        if foods:
            closest_food = min(foods, key=lambda f: (f.x - self.x) ** 2 + (f.y - self.y) ** 2)
            dx = closest_food.x - self.x
            dy = closest_food.y - self.y
            dist = math.hypot(dx, dy)
            if dist < 320.0 and closest_food.y > WATER_SURFACE_Y - 10.0:
                seeking = True
                ndx = dx / max(1.0, dist)
                ndy = dy / max(1.0, dist)
                spd = self.base_speed * (2.0 if closest_food.kind == self.craved_food.value else 1.5)
                self.vx += (ndx * spd - self.vx) * 0.12
                self.vy += (ndy * spd - self.vy) * 0.12
                if dist < 38.0 * self.scale:
                    foods.remove(closest_food)
                    self.state = OrcaState.EATING
                    self.state_timer = 1.0
                    events.append("nibble")
                    events.append("purr")
                    events.append("ate:" + closest_food.kind)
                    if closest_food.kind == self.craved_food.value:
                        events.append("favorite_food")

        if not seeking and toys:
            balls = [t for t in toys if t.kind == "ball"]
            if balls:
                ball = balls[0]
                dist = math.hypot(ball.x - self.x, ball.y - self.y)
                if dist < 220.0 and self._rng.random() < 0.4:
                    seeking = True
                    dx = ball.x - self.x
                    dy = ball.y - self.y
                    self.vx += ((dx / max(1.0, dist)) * self.base_speed * 1.4 - self.vx) * 0.08
                    self.vy += ((dy / max(1.0, dist)) * self.base_speed * 1.4 - self.vy) * 0.08
                    if dist < 45.0 * self.scale and ball.vy >= -1.0:
                        ball.vx = (ball.x - self.x) * 0.25 + (self.facing * 4.0)
                        ball.vy = -6.5
                        events.append("bounce")
                        events.append("whistle")

        if not seeking:
            self.vx += (self.target_vx - self.vx) * 0.04
            self.vy += (self.target_vy - self.vy) * 0.04
            if self._rng.random() < 0.02:
                self.target_vy = self._rng.uniform(-0.5, 0.5)
            if self._rng.random() < 0.008:
                self.target_vx = -self.target_vx

        calc_pitch = math.degrees(math.atan2(self.vy, max(0.8, abs(self.vx)))) * (1.0 if self.facing >= 0 else -1.0)
        target_p = max(-14.0, min(14.0, calc_pitch))
        self.angle += (target_p - self.angle) * 0.08

        self.x += self.vx
        self.y += self.vy + math.sin(self.swim_phase * 2.0) * 0.5

        # Facing flips with hysteresis so the sprite does not flicker.
        if self.vx > 0.4:
            self.facing = 1
        elif self.vx < -0.4:
            self.facing = -1
        self._keep_in_bay()
        return events

    def _keep_in_bay(self) -> None:
        min_x = 112.0 * self.scale
        max_x = REFERENCE_WIDTH - 112.0 * self.scale
        min_y = WATER_SURFACE_Y + 15.0
        if self.x < min_x:
            self.x = min_x
            self.vx = abs(self.vx)
            self.target_vx = abs(self.target_vx)
            self.facing = 1
        elif self.x > max_x:
            self.x = max_x
            self.vx = -abs(self.vx)
            self.target_vx = -abs(self.target_vx)
            self.facing = -1
        if self.y < min_y:
            self.y = min_y
            self.vy = abs(self.vy)
        elif self.y > self.max_y:
            self.y = self.max_y
            self.vy = -abs(self.vy)


class FoodEntity:
    """Fish or squid dropped into the bay for the orcas to eat."""

    def __init__(self, x: float, y: float, kind: str, vx: float = 0.0, vy: float = 1.2) -> None:
        self.x = x
        self.y = y
        self.kind = kind
        self.vx = vx
        self.vy = vy
        self.size = 28.0

    def update(self, dt: float) -> bool:
        if self.y < WATER_SURFACE_Y:
            self.vy += 9.8 * dt * 1.5
        else:
            self.vy = max(0.4, min(1.6, self.vy * 0.92))
            self.vx *= 0.95
        self.x += self.vx
        self.y += self.vy
        return self.y < REFERENCE_HEIGHT - 95.0


class ToyEntity:
    """Floating toy: the beach ball (physics) or the jump hoop (anchored)."""

    def __init__(self, kind: str, x: float, y: float) -> None:
        self.kind = kind
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.rotation = 0.0
        self.scale = 1.0

    def update(self, dt: float) -> None:
        self.rotation += self.vx * 2.0
        self.vx *= 0.96
        if self.kind == "ball":
            if self.y < WATER_SURFACE_Y:
                self.vy += 12.0 * dt
            else:
                depth = self.y - WATER_SURFACE_Y
                self.vy -= depth * 0.15
                self.vy *= 0.88
            self.x += self.vx
            self.y += self.vy
            self.y = max(40.0, self.y)
            if self.x < 70.0:
                self.x = 70.0
                self.vx = abs(self.vx) * 0.8
            elif self.x > REFERENCE_WIDTH - 70.0:
                self.x = REFERENCE_WIDTH - 70.0
                self.vx = -abs(self.vx) * 0.8


class OrcaPod:
    """The bay's state: orcas, food, toys, FX, facts, day/night and counters."""

    FACT_KEYS: tuple[str, ...] = FACT_KEYS

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self.orcas: list[OrcaEntity] = [
            OrcaEntity("kiko", "orca.kiko", "baby", 280.0, 370.0, scale=0.72, speed=1.8, rng=self._rng),
            OrcaEntity("luna", "orca.luna", "acrobat", 520.0, 340.0, scale=1.0, speed=1.6, rng=self._rng),
            OrcaEntity("oskar", "orca.oskar", "elder", 760.0, 400.0, scale=1.35, speed=1.2, rng=self._rng),
        ]
        self.foods: list[FoodEntity] = []
        self.toys: list[ToyEntity] = [
            ToyEntity("ball", BALL_START[0], BALL_START[1]),
            ToyEntity("ring", HOOP_POSITION[0], HOOP_POSITION[1]),
        ]
        # Short library FX: {"kind", "x", "y", "age", "life", "scale"}.
        self.effects: list[dict[str, Any]] = []

        self.night_mode = False
        self.active_tool = Tool.FEED
        self.selected_food = FoodType.SALMON

        self.active_fact: str | None = None
        self.fact_timer: float = 0.0
        self.current_fact_idx: int = 0
        self.discovered_facts: set[str] = set()

        # Facts the app drains each frame (what happened, for missions/events).
        self.meals: list[tuple[str, str, bool]] = []

        self.total_fed = 0
        self.total_cuddled = 0
        self.total_acrobatics = 0
        self.total_songs = 0
        self.stars = 0

    # -- persistence -----------------------------------------------------

    def restore_progress(self, data: Any) -> None:
        if not isinstance(data, dict):
            return
        self.total_fed = safe_counter(data.get("total_fed", 0))
        self.total_cuddled = safe_counter(data.get("total_cuddled", 0))
        self.total_acrobatics = safe_counter(data.get("total_acrobatics", 0))
        self.total_songs = safe_counter(data.get("total_songs", 0))
        self.stars = safe_counter(data.get("stars", 0), MAX_SAVED_STARS)
        self.night_mode = bool(data.get("night_mode", False))
        facts = data.get("discovered_facts", [])
        if isinstance(facts, (list, tuple)):
            self.discovered_facts = {key for key in facts if key in self.FACT_KEYS}
        food = data.get("food")
        if isinstance(food, str) and food in {f.value for f in FoodType}:
            self.selected_food = FoodType(food)
        # Continue with the first fact this child has not heard yet.
        unheard = [i for i, key in enumerate(self.FACT_KEYS) if key not in self.discovered_facts]
        self.current_fact_idx = unheard[0] if unheard else 0

    def export_progress(self) -> dict[str, Any]:
        return {
            "schema": SAVE_SCHEMA,
            "total_fed": self.total_fed,
            "total_cuddled": self.total_cuddled,
            "total_acrobatics": self.total_acrobatics,
            "total_songs": self.total_songs,
            "night_mode": self.night_mode,
            "discovered_facts": sorted(self.discovered_facts),
            "stars": self.stars,
            "food": self.selected_food.value,
        }

    # -- lookups ---------------------------------------------------------

    def orca(self, orca_id: str) -> OrcaEntity | None:
        for orca in self.orcas:
            if orca.id == orca_id:
                return orca
        return None

    def nearest_orca(self, x: float) -> OrcaEntity:
        return min(self.orcas, key=lambda o: abs(o.x - x))

    # -- facts -----------------------------------------------------------

    def trigger_fact(self, key: str | None = None) -> str:
        if key is None:
            key = self.FACT_KEYS[self.current_fact_idx % len(self.FACT_KEYS)]
            self.current_fact_idx += 1
        self.active_fact = key
        self.fact_timer = FACT_SECONDS
        self.discovered_facts.add(key)
        return key

    def dismiss_fact(self) -> None:
        self.active_fact = None
        self.fact_timer = 0.0

    # -- spawning --------------------------------------------------------

    def spawn_food(self, x: float, y: float, kind: FoodType | None = None) -> FoodEntity:
        chosen = kind if kind is not None else self.selected_food
        food = FoodEntity(x, y, chosen.value, vx=self._rng.uniform(-0.6, 0.6), vy=self._rng.uniform(1.2, 2.4))
        if len(self.foods) >= MAX_FOODS:
            self.foods.pop(0)
        self.foods.append(food)
        return food

    def emit_effect(self, kind: str, x: float, y: float, scale: float = 1.0, life: float = 0.7) -> None:
        if len(self.effects) >= MAX_EFFECTS:
            self.effects.pop(0)
        self.effects.append({"kind": kind, "x": float(x), "y": float(y), "age": 0.0, "life": life, "scale": scale})

    # -- update ----------------------------------------------------------

    def update(self, dt: float) -> list[str]:
        all_events: list[str] = []
        for orca in self.orcas:
            for cue in orca.update(dt, self.foods, self.toys, self.night_mode):
                if cue == "splash":
                    self.emit_effect("splash", orca.x, WATER_SURFACE_Y - 10.0, 1.1)
                    self.total_acrobatics = min(MAX_SAVED_COUNTER, self.total_acrobatics + 1)
                elif cue == "nibble":
                    self.total_fed = min(MAX_SAVED_COUNTER, self.total_fed + 1)
                elif cue == "favorite_food":
                    orca.cheer()
                    self.emit_effect("heart_pop", orca.x, orca.y - 40.0 * orca.scale, 0.8)
                elif cue.startswith("ate:"):
                    kind = cue[4:]
                    self.meals.append((orca.id, kind, kind == orca.craved_food.value))
                    if len(self.meals) > 16:
                        del self.meals[:-16]
                    continue
                all_events.append(cue)

        self.foods = [f for f in self.foods if f.update(dt)]
        for toy in self.toys:
            toy.update(dt)
        for effect in self.effects:
            effect["age"] += dt
        self.effects = [e for e in self.effects if e["age"] < e["life"]]

        if self.fact_timer > 0.0:
            self.fact_timer -= dt
            if self.fact_timer <= 0.0:
                self.active_fact = None
        return all_events


__all__ = [
    "FoodEntity",
    "FoodType",
    "OrcaEntity",
    "OrcaPod",
    "OrcaState",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "ToyEntity",
    "WATER_SURFACE_Y",
    "safe_counter",
]
