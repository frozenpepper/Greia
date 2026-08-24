from __future__ import annotations

from enum import Enum
import math
import random
from typing import Any

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
WATER_SURFACE_Y = 260.0


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


class FoodType(Enum):
    HERRING = "herring"
    SALMON = "salmon"
    SQUID = "squid"
    SHRIMP = "shrimp"
    ICE = "ice"


class OrcaEntity:
    """Represents an individual orca with distinctive personality, morphology, and AI behavior."""

    def __init__(
        self,
        orca_id: str,
        name_key: str,
        role: str,
        x: float,
        y: float,
        scale: float = 1.0,
        speed: float = 1.6,
    ) -> None:
        self.id = orca_id
        self.name_key = name_key
        self.role = role
        self.x = x
        self.y = y
        self.scale = scale
        self.base_speed = speed
        self.vx = speed * (1.0 if random.random() < 0.5 else -1.0)
        self.vy = 0.0
        self.target_vx = self.vx
        self.target_vy = 0.0
        self.facing = 1 if self.vx >= 0 else -1
        self.angle = 0.0
        self.target_angle = 0.0
        self.fluke_angle = 0.0
        self.mouth_open = 0.0
        self.swim_phase = random.random() * 6.28
        self.blink_timer = random.uniform(2.0, 4.5)
        self.is_blinking = False

        self.state = OrcaState.SWIMMING
        self.state_timer = 0.0
        self.jump_origin_y = y
        self.jump_peak_h = 160.0 * scale
        self.jump_flip_angle = 0.0
        self.cuddle_happiness = 0.0
        self.craved_food = random.choice(list(FoodType))
        self.jump_target_x = x

    @property
    def width(self) -> float:
        return 140.0 * self.scale

    @property
    def height(self) -> float:
        return 75.0 * self.scale

    def hit_test(self, px: float, py: float) -> bool:
        w = self.width * 1.25
        h = self.height * 1.25
        return (self.x - w / 2 <= px <= self.x + w / 2) and (self.y - h / 2 <= py <= self.y + h / 2)

    def trigger_cuddle(self) -> None:
        self.state = OrcaState.CUDDLE_BELLY
        self.state_timer = 2.8
        self.cuddle_happiness = min(1.0, self.cuddle_happiness + 0.4)
        self.vy = -1.2
        self.target_angle = 15.0 * (1 if random.random() < 0.5 else -1)

    def trigger_breach(self, jump_x: float, height_bonus: float = 0.0) -> None:
        self.state = OrcaState.BREACHING
        self.state_timer = 0.0
        self.jump_origin_y = max(WATER_SURFACE_Y + 40.0, self.y)
        self.jump_target_x = jump_x
        self.jump_peak_h = (155.0 + height_bonus) * self.scale
        self.facing = 1 if jump_x >= self.x else -1
        self.jump_flip_angle = 0.0

    def trigger_ring_jump(self, ring_x: float) -> None:
        self.state = OrcaState.RING_LEAP
        self.state_timer = 0.0
        self.jump_origin_y = max(WATER_SURFACE_Y + 40.0, self.y)
        self.jump_target_x = ring_x
        self.jump_peak_h = 185.0 * self.scale
        self.facing = 1 if ring_x >= self.x else -1
        self.jump_flip_angle = 0.0

    def trigger_sing(self, note_idx: int) -> None:
        self.state = OrcaState.SINGING
        self.state_timer = 1.6
        self.vy = -1.5
        self.mouth_open = 1.0

    def update(self, dt: float, foods: list[FoodEntity], toys: list[ToyEntity], night_mode: bool) -> list[str]:
        """Update orca physics, animation timers and state transitions. Returns event cues to trigger."""
        events: list[str] = []
        self.swim_phase += 0.08 * (self.base_speed / 1.5)

        # Blinking cycle
        self.blink_timer -= dt
        if self.blink_timer <= 0:
            if not self.is_blinking:
                self.is_blinking = True
                self.blink_timer = 0.18
            else:
                self.is_blinking = False
                self.blink_timer = random.uniform(2.5, 5.5)

        # Night time sleeping behavior
        if night_mode and self.state == OrcaState.SWIMMING:
            self.state = OrcaState.SLEEPING
        elif not night_mode and self.state == OrcaState.SLEEPING:
            self.state = OrcaState.SWIMMING

        # Natural tail fluke oscillation
        self.fluke_angle = math.sin(self.swim_phase) * 18.0

        # Mouth closing interpolation
        if self.state not in (OrcaState.EATING, OrcaState.SINGING):
            self.mouth_open = max(0.0, self.mouth_open - dt * 3.0)

        # State Machine Dispatch
        if self.state == OrcaState.SLEEPING:
            # Gentle rhythmic bobbing near surface with resting angle
            self.vx *= 0.94
            self.vy = math.sin(self.swim_phase * 0.5) * 0.4
            self.y += self.vy
            self.x += self.vx
            self.angle += (0.0 - self.angle) * 0.05
            return events

        elif self.state == OrcaState.CUDDLE_BELLY:
            self.state_timer -= dt
            self.vx *= 0.90
            self.vy = math.sin(self.swim_phase * 1.5) * 0.6
            self.y = max(WATER_SURFACE_Y - 5.0, min(WATER_SURFACE_Y + 40.0, self.y + self.vy))
            self.angle += (self.target_angle - self.angle) * 0.1
            if self.state_timer <= 0:
                self.state = OrcaState.SWIMMING
            return events

        elif self.state == OrcaState.SINGING:
            self.state_timer -= dt
            self.vx *= 0.92
            self.y += math.sin(self.swim_phase * 2.0) * 0.8
            self.mouth_open = min(1.0, self.mouth_open + dt * 4.0)
            self.angle += (-15.0 * self.facing - self.angle) * 0.12
            if self.state_timer <= 0:
                self.state = OrcaState.SWIMMING
            return events

        elif self.state == OrcaState.EATING:
            self.state_timer -= dt
            self.vx *= 0.85
            self.y += math.sin(self.swim_phase * 2.5) * 0.5
            self.mouth_open = min(1.0, self.mouth_open + dt * 5.0)
            if self.state_timer <= 0:
                self.craved_food = random.choice(list(FoodType))
                self.state = OrcaState.SWIMMING
            return events

        elif self.state in (OrcaState.BREACHING, OrcaState.RING_LEAP):
            self.state_timer += dt * 1.35
            # Parabolic trajectory arc (0.0 to 1.0)
            progress = self.state_timer
            if progress < 1.0:
                # Upward and downward parabolic arc
                h = math.sin(progress * math.pi) * self.jump_peak_h
                self.y = self.jump_origin_y - h
                # Dynamic leap pitch angle
                self.angle = (-38.0 + progress * 76.0) * self.facing
                if self.state == OrcaState.RING_LEAP:
                    # Barrel roll spin
                    self.jump_flip_angle += 360.0 * dt * 1.5
                self.x += (self.jump_target_x - self.x) * 0.08 + (self.facing * self.base_speed * 1.8)
            else:
                # Water Reentry Splashdown!
                self.y = WATER_SURFACE_Y + 30.0
                self.vy = 2.0
                self.angle = 0.0
                self.jump_flip_angle = 0.0
                self.state = OrcaState.SWIMMING
                events.append("splash")
                events.append("whistle")
            return events

        # Standard Swimming & Food / Toy Seeking
        seeking = False

        # 1. Seek Food if present in water
        if foods:
            closest_food = min(foods, key=lambda f: (f.x - self.x) ** 2 + (f.y - self.y) ** 2)
            dx = closest_food.x - self.x
            dy = closest_food.y - self.y
            dist = math.hypot(dx, dy)

            if dist < 320.0:
                seeking = True
                ndx = dx / max(1.0, dist)
                ndy = dy / max(1.0, dist)
                spd = self.base_speed * (2.0 if closest_food.kind == self.craved_food.value else 1.5)
                self.vx += (ndx * spd - self.vx) * 0.12
                self.vy += (ndy * spd - self.vy) * 0.12

                # Eating contact radius
                if dist < 38.0 * self.scale:
                    if closest_food in foods:
                        foods.remove(closest_food)
                    self.state = OrcaState.EATING
                    self.state_timer = 1.0
                    events.append("nibble")
                    events.append("purr")
                    if closest_food.kind == self.craved_food.value:
                        events.append("favorite_food")

        # 2. Seek Ball if near
        if not seeking and toys:
            balls = [t for t in toys if t.kind == "ball"]
            if balls:
                ball = balls[0]
                dist = math.hypot(ball.x - self.x, ball.y - self.y)
                if dist < 220.0 and random.random() < 0.4:
                    seeking = True
                    dx = ball.x - self.x
                    dy = ball.y - self.y
                    self.vx += ((dx / max(1.0, dist)) * self.base_speed * 1.4 - self.vx) * 0.08
                    self.vy += ((dy / max(1.0, dist)) * self.base_speed * 1.4 - self.vy) * 0.08

                    # Bump ball
                    if dist < 45.0 * self.scale:
                        ball.vx = (ball.x - self.x) * 0.25 + (self.facing * 4.0)
                        ball.vy = -6.5
                        events.append("bounce")
                        events.append("whistle")

        # Natural wandering when not actively pursuing a target
        if not seeking:
            self.vx += (self.target_vx - self.vx) * 0.04
            self.vy += (self.target_vy - self.vy) * 0.04
            if random.random() < 0.02:
                self.target_vy = random.uniform(-0.5, 0.5)
            if random.random() < 0.008:
                self.target_vx = -self.target_vx

        # Natural pitch angle derived from 2D velocity vector
        calc_pitch = math.degrees(math.atan2(self.vy, max(0.5, abs(self.vx)))) * (1 if self.facing >= 0 else -1)
        self.angle += (max(-25.0, min(25.0, calc_pitch)) - self.angle) * 0.08

        # Apply position update
        self.x += self.vx
        self.y += self.vy + math.sin(self.swim_phase * 2.0) * 0.7

        # Update facing direction with strong hysteresis
        if self.vx > 0.4:
            self.facing = 1
        elif self.vx < -0.4:
            self.facing = -1

        # Keep within aquarium / fjord boundaries
        min_x = 75.0 * self.scale
        max_x = REFERENCE_WIDTH - 75.0 * self.scale
        min_y = WATER_SURFACE_Y + 15.0
        max_y = REFERENCE_HEIGHT - 120.0

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
        elif self.y > max_y:
            self.y = max_y
            self.vy = -abs(self.vy)

        return events


class FoodEntity:
    """Fish or treat tossed into the bay for orcas to eat."""

    def __init__(self, x: float, y: float, kind: str, vx: float = 0.0, vy: float = 1.2) -> None:
        self.x = x
        self.y = y
        self.kind = kind
        self.vx = vx
        self.vy = vy
        self.size = 28.0
        self.rotation = random.uniform(-30.0, 30.0)

    def update(self, dt: float) -> bool:
        # Air vs Water physics
        if self.y < WATER_SURFACE_Y:
            # Falling through air (gravity)
            self.vy += 9.8 * dt * 1.5
        else:
            # Buoyant drag in ocean water
            self.vy = max(0.4, min(1.6, self.vy * 0.92))
            self.vx *= 0.95
            self.rotation += 0.5

        self.x += self.vx
        self.y += self.vy
        return self.y < REFERENCE_HEIGHT - 95.0


class ToyEntity:
    """Interactive floating toy such as a beach ball or jump hoop."""

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
            # Gravity above surface, buoyancy push at/below surface
            if self.y < WATER_SURFACE_Y:
                self.vy += 12.0 * dt
            else:
                # Buoyancy rebound
                depth = self.y - WATER_SURFACE_Y
                self.vy -= depth * 0.15
                self.vy *= 0.88

            self.x += self.vx
            self.y += self.vy

            # Horizontal bounds
            if self.x < 70.0:
                self.x = 70.0
                self.vx = abs(self.vx) * 0.8
            elif self.x > REFERENCE_WIDTH - 70.0:
                self.x = REFERENCE_WIDTH - 70.0
                self.vx = -abs(self.vx) * 0.8


class ParticleEntity:
    """Visual feedback particle (splash, heart, bubble, music note, sparkle)."""

    def __init__(
        self,
        x: float,
        y: float,
        kind: str,
        vx: float,
        vy: float,
        color: tuple[int, int, int],
        size: float = 6.0,
        life: float = 1.0,
        decay: float = 0.04,
        symbol: str = "",
    ) -> None:
        self.x = x
        self.y = y
        self.kind = kind
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.life = life
        self.decay = decay
        self.symbol = symbol

    def update(self, dt: float) -> bool:
        self.x += self.vx
        self.y += self.vy
        if self.kind in ("splash", "bubble", "heart", "note"):
            self.vy -= 0.02  # Gentle upward float
        self.life -= self.decay
        return self.life > 0.0


class OrcaPod:
    """Domain model coordinating the orca pod, toys, food, and environmental state."""

    def __init__(self) -> None:
        self.orcas: list[OrcaEntity] = [
            OrcaEntity("kiko", "orca.kiko", "baby", 280.0, 360.0, scale=0.72, speed=1.8),
            OrcaEntity("luna", "orca.luna", "acrobat", 520.0, 320.0, scale=1.0, speed=1.6),
            OrcaEntity("oskar", "orca.oskar", "elder", 780.0, 420.0, scale=1.35, speed=1.2),
        ]
        self.foods: list[FoodEntity] = []
        self.toys: list[ToyEntity] = [
            ToyEntity("ball", 480.0, WATER_SURFACE_Y),
            ToyEntity("ring", 680.0, WATER_SURFACE_Y - 15.0),
        ]
        self.particles: list[ParticleEntity] = []

        self.night_mode = False
        self.active_tool = 0  # 0: Feed, 1: Cuddle, 2: Play/Tricks, 3: Song, 4: Night/Day
        self.selected_food_idx = 0

        # Persistent activity stats
        self.total_fed = 0
        self.total_cuddled = 0
        self.total_acrobatics = 0
        self.total_songs = 0

    def restore_progress(self, data: dict[str, Any]) -> None:
        self.total_fed = int(data.get("total_fed", 0))
        self.total_cuddled = int(data.get("total_cuddled", 0))
        self.total_acrobatics = int(data.get("total_acrobatics", 0))
        self.total_songs = int(data.get("total_songs", 0))
        self.night_mode = bool(data.get("night_mode", False))

    def export_progress(self) -> dict[str, Any]:
        return {
            "total_fed": self.total_fed,
            "total_cuddled": self.total_cuddled,
            "total_acrobatics": self.total_acrobatics,
            "total_songs": self.total_songs,
            "night_mode": self.night_mode,
        }

    def spawn_food(self, x: float, y: float, kind: FoodType | None = None) -> FoodEntity:
        k = kind.value if kind is not None else list(FoodType)[self.selected_food_idx % len(FoodType)].value
        food = FoodEntity(x, y, k, vx=random.uniform(-0.6, 0.6), vy=random.uniform(1.2, 2.4))
        self.foods.append(food)
        self.selected_food_idx = (self.selected_food_idx + 1) % len(FoodType)
        return food

    def spawn_splash_particles(self, x: float, y: float, count: int = 12, col: tuple[int, int, int] = (186, 230, 253)) -> None:
        for _ in range(count):
            self.particles.append(
                ParticleEntity(
                    x=x + random.uniform(-20.0, 20.0),
                    y=y + random.uniform(-8.0, 8.0),
                    kind="splash",
                    vx=random.uniform(-2.5, 2.5),
                    vy=random.uniform(-4.5, -1.0),
                    color=col,
                    size=random.uniform(4.0, 8.0),
                    decay=random.uniform(0.03, 0.06),
                )
            )

    def spawn_heart_particles(self, x: float, y: float, count: int = 5) -> None:
        for _ in range(count):
            self.particles.append(
                ParticleEntity(
                    x=x + random.uniform(-15.0, 15.0),
                    y=y + random.uniform(-10.0, 5.0),
                    kind="heart",
                    vx=random.uniform(-1.2, 1.2),
                    vy=random.uniform(-2.5, -0.8),
                    color=(244, 63, 94),
                    size=random.uniform(14.0, 22.0),
                    decay=0.03,
                    symbol="❤️",
                )
            )

    def spawn_music_particles(self, x: float, y: float, note_symbol: str = "🎵") -> None:
        for _ in range(3):
            self.particles.append(
                ParticleEntity(
                    x=x + random.uniform(-12.0, 12.0),
                    y=y + random.uniform(-10.0, 5.0),
                    kind="note",
                    vx=random.uniform(-1.0, 1.0),
                    vy=random.uniform(-2.0, -1.0),
                    color=(250, 204, 21) if not self.night_mode else (168, 85, 247),
                    size=random.uniform(18.0, 26.0),
                    decay=0.025,
                    symbol=note_symbol,
                )
            )

    def update(self, dt: float) -> list[str]:
        all_events: list[str] = []

        # Update orcas
        for orca in self.orcas:
            cues = orca.update(dt, self.foods, self.toys, self.night_mode)
            for cue in cues:
                if cue == "splash":
                    self.spawn_splash_particles(orca.x, WATER_SURFACE_Y, count=16)
                    self.total_acrobatics += 1
                elif cue == "nibble":
                    self.total_fed += 1
                elif cue == "favorite_food":
                    self.spawn_heart_particles(orca.x, orca.y - 20.0, count=4)
                all_events.append(cue)

        # Update food
        self.foods = [f for f in self.foods if f.update(dt)]

        # Update toys
        for toy in self.toys:
            toy.update(dt)

        # Update particles
        self.particles = [p for p in self.particles if p.update(dt)]

        return all_events
