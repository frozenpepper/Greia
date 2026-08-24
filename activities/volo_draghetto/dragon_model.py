"""Domain model and simulation state for Il Volo del Draghetto."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
from typing import Final, Sequence

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
STORAGE_KEY: Final = "volo_draghetto.progress.v2"
ROUND_STAR_TARGET: Final = 20

# Sky vertical boundaries
MIN_FLIGHT_Y: Final = 85.0
MAX_FLIGHT_Y: Final = 515.0

# Available Dragon Accessories
ACCESSORIES: Final[tuple[str, ...]] = (
    "crown",
    "bow",
    "glasses",
    "flower",
    "none",
)

RAINBOW_COLORS: Final[tuple[tuple[int, int, int], ...]] = (
    (255, 80, 80),
    (255, 165, 0),
    (255, 235, 50),
    (70, 210, 120),
    (60, 175, 255),
    (160, 90, 255),
)


@dataclass(slots=True)
class DragonPlayer:
    """The friendly magical baby dragon flown by the child."""

    x: float = 200.0
    y: float = 300.0
    target_y: float = 300.0
    base_speed: float = 6.0
    dash_timer: float = 0.0
    wing_flap_phase: float = 0.0
    accessory: str = "crown"
    vertical_velocity: float = 0.0

    @property
    def is_dashing(self) -> bool:
        return self.dash_timer > 0.0

    @property
    def current_speed(self) -> float:
        return self.base_speed * (2.0 if self.is_dashing else 1.0)

    def trigger_dash(self, duration: float = 3.5) -> None:
        self.dash_timer = max(self.dash_timer, duration)

    def cycle_accessory(self) -> str:
        idx = ACCESSORIES.index(self.accessory) if self.accessory in ACCESSORIES else 0
        self.accessory = ACCESSORIES[(idx + 1) % len(ACCESSORIES)]
        return self.accessory

    def update(self, dt: float = 1.0 / 30.0) -> None:
        # Forward propulsion
        self.x += self.current_speed

        # Smooth vertical tracking with spring-damper inertia
        dy = self.target_y - self.y
        self.vertical_velocity = dy * 0.16
        self.y += self.vertical_velocity
        self.y = max(MIN_FLIGHT_Y, min(MAX_FLIGHT_Y, self.y))

        # Flap wing cycle
        flap_speed = 10.0 if self.is_dashing else 6.0
        self.wing_flap_phase = (self.wing_flap_phase + flap_speed * dt) % (2.0 * math.pi)

        # Decay dash timer
        if self.dash_timer > 0.0:
            self.dash_timer = max(0.0, self.dash_timer - dt)


@dataclass(slots=True)
class CollectibleStar:
    """A floating magical gold star to gather."""

    x: float
    y: float
    bob_phase: float = 0.0
    collected: bool = False

    @property
    def effective_y(self) -> float:
        return self.y + math.sin(self.bob_phase) * 6.0

    def update(self, dt: float = 1.0 / 30.0) -> None:
        self.bob_phase = (self.bob_phase + 3.0 * dt) % (2.0 * math.pi)

    def collides_with(self, px: float, py: float, radius: float = 52.0) -> bool:
        if self.collected:
            return False
        return (px - self.x) ** 2 + (py - self.effective_y) ** 2 <= radius ** 2


@dataclass(slots=True)
class RainbowGate:
    """A glowing rainbow portal that gives a super turbo dash boost."""

    x: float
    y: float
    passed: bool = False

    def collides_with(self, px: float, py: float) -> bool:
        if self.passed:
            return False
        return abs(px - self.x) <= 60.0 and (self.y - 120.0 <= py <= self.y + 40.0)


@dataclass(slots=True)
class BouncyCloud:
    """A fluffy, smiling bouncy cloud obstacle that bounces the dragon safely."""

    x: float
    y: float
    width: float = 110.0
    height: float = 56.0

    def collides_with(self, px: float, py: float) -> bool:
        return abs(px - self.x) <= 52.0 and abs(py - self.y) <= 42.0


@dataclass(slots=True)
class VisualParticle:
    """A lightweight particle effect with bounded lifetime."""

    x: float
    y: float
    vx: float
    vy: float
    life: float = 1.0
    decay: float = 0.04
    kind: str = "star"  # "star", "rainbow", "cloud", "sparkle"
    color: tuple[int, int, int] = (255, 215, 0)
    size: float = 16.0

    def update(self, dt: float = 1.0 / 30.0) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay
        return self.life > 0.0


@dataclass
class FlightWorldState:
    """Complete domain simulation state for Il Volo del Draghetto."""

    dragon: DragonPlayer = field(default_factory=DragonPlayer)
    stars: list[CollectibleStar] = field(default_factory=list)
    rainbow_gates: list[RainbowGate] = field(default_factory=list)
    clouds: list[BouncyCloud] = field(default_factory=list)
    particles: list[VisualParticle] = field(default_factory=list)

    # Score and round progression
    round_stars: int = 0
    total_stars: int = 0
    score: int = 0
    round_star_target: int = ROUND_STAR_TARGET
    is_victory: bool = False

    # Chunk generation tracking
    last_spawn_x: float = 400.0
    feedback_text_key: str = ""
    feedback_timer: float = 0.0

    def start_flight(self) -> None:
        """Initialize or reset flight world state for a new round."""
        self.dragon = DragonPlayer(x=200.0, y=300.0)
        self.stars.clear()
        self.rainbow_gates.clear()
        self.clouds.clear()
        self.particles.clear()
        self.round_stars = 0
        self.is_victory = False
        self.last_spawn_x = 400.0
        self.feedback_text_key = ""
        self.feedback_timer = 0.0

        # Pre-seed initial track chunk
        self._spawn_world_chunk(400.0, 3200.0)
        self.last_spawn_x = 3200.0

    def update(self, dt: float = 1.0 / 30.0) -> list[str]:
        """Advance world simulation by dt and return triggered event IDs."""
        events: list[str] = []
        if self.is_victory:
            return events

        # Update dragon
        self.dragon.update(dt)
        cam_x = self.dragon.x - 200.0

        # Update collectibles bobbing
        for star in self.stars:
            star.update(dt)

        # Stream ahead chunks
        if self.dragon.x + 1800.0 > self.last_spawn_x:
            self._spawn_world_chunk(self.last_spawn_x, self.last_spawn_x + 2200.0)
            self.last_spawn_x += 2200.0

        # Collision: Stars
        for star in self.stars:
            if star.collides_with(self.dragon.x, self.dragon.y):
                star.collected = True
                self.round_stars += 1
                self.total_stars += 1
                self.score += 10 * (2 if self.dragon.is_dashing else 1)
                events.append("star_collected")
                self._spawn_star_burst(star.x, star.effective_y)

                # Check round victory target
                if self.round_stars >= self.round_star_target and not self.is_victory:
                    self.is_victory = True
                    events.append("round_completed")

        # Collision: Rainbow Gates (Super Turbo Boost!)
        for gate in self.rainbow_gates:
            if gate.collides_with(self.dragon.x, self.dragon.y):
                gate.passed = True
                self.dragon.trigger_dash(4.5)
                self.score += 30
                self.round_stars += 1
                self.total_stars += 1
                self.feedback_text_key = "msg.rainbow_dash"
                self.feedback_timer = 2.5
                events.append("rainbow_boost")
                self._spawn_rainbow_burst(gate.x, gate.y - 30.0)

        # Collision: Bouncy Clouds
        for cloud in self.clouds:
            if cloud.collides_with(self.dragon.x, self.dragon.y):
                # Bounce dragon smoothly away from cloud center
                bounce_target = MIN_FLIGHT_Y + 40.0 if self.dragon.y > cloud.y else MAX_FLIGHT_Y - 40.0
                self.dragon.target_y = bounce_target
                events.append("cloud_bounce")
                self._spawn_cloud_puffs(cloud.x, cloud.y)

        # Update & prune particles
        self.particles = [p for p in self.particles if p.update(dt)]

        # Prune passed world elements
        self.stars = [s for s in self.stars if s.x > cam_x - 300.0]
        self.rainbow_gates = [g for g in self.rainbow_gates if g.x > cam_x - 300.0]
        self.clouds = [c for c in self.clouds if c.x > cam_x - 300.0]

        # Decay feedback message timer
        if self.feedback_timer > 0.0:
            self.feedback_timer = max(0.0, self.feedback_timer - dt)
            if self.feedback_timer == 0.0:
                self.feedback_text_key = ""

        return events

    def _spawn_world_chunk(self, start_x: float, end_x: float) -> None:
        """Generate playful rhythmic waves of stars, rainbows, and bouncy clouds."""
        cur_x = start_x
        while cur_x < end_x:
            pattern = random.choice(["sine_wave", "rainbow_arch", "cloud_meadow", "star_cluster"])
            if pattern == "sine_wave":
                base_y = random.uniform(200.0, 400.0)
                freq = random.uniform(0.6, 0.9)
                amp = random.uniform(50.0, 80.0)
                for step in range(5):
                    sy = base_y + math.sin(step * freq) * amp
                    self.stars.append(CollectibleStar(cur_x + step * 75.0, sy))
                cur_x += 460.0

            elif pattern == "rainbow_arch":
                arch_y = random.uniform(230.0, 380.0)
                self.rainbow_gates.append(RainbowGate(cur_x + 130.0, arch_y))
                for s_i in range(3):
                    self.stars.append(CollectibleStar(cur_x + 70.0 + s_i * 60.0, arch_y - 25.0))
                cur_x += 480.0

            elif pattern == "cloud_meadow":
                cy = random.uniform(180.0, 420.0)
                self.clouds.append(BouncyCloud(cur_x + 110.0, cy))
                star_y = cy - 85.0 if cy > 300.0 else cy + 85.0
                self.stars.append(CollectibleStar(cur_x + 110.0, max(MIN_FLIGHT_Y, min(MAX_FLIGHT_Y, star_y))))
                cur_x += 390.0

            else:  # star_cluster
                center_y = random.uniform(220.0, 380.0)
                for dx, dy in ((-40, 0), (0, -35), (40, 0), (0, 35), (0, 0)):
                    self.stars.append(CollectibleStar(cur_x + 100.0 + dx, center_y + dy))
                cur_x += 420.0

    def _spawn_star_burst(self, x: float, y: float) -> None:
        for _ in range(8):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(2.5, 5.5)
            self.particles.append(
                VisualParticle(
                    x=x,
                    y=y,
                    vx=math.cos(ang) * spd,
                    vy=math.sin(ang) * spd,
                    life=1.0,
                    decay=random.uniform(0.04, 0.08),
                    kind="star",
                    color=(255, 215, 0),
                    size=random.uniform(10.0, 18.0),
                )
            )

    def _spawn_rainbow_burst(self, x: float, y: float) -> None:
        for _ in range(16):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(3.0, 7.0)
            col = random.choice(RAINBOW_COLORS)
            self.particles.append(
                VisualParticle(
                    x=x,
                    y=y,
                    vx=math.cos(ang) * spd,
                    vy=math.sin(ang) * spd,
                    life=1.0,
                    decay=random.uniform(0.03, 0.06),
                    kind="rainbow",
                    color=col,
                    size=random.uniform(12.0, 20.0),
                )
            )

    def _spawn_cloud_puffs(self, x: float, y: float) -> None:
        for _ in range(6):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(1.5, 3.5)
            self.particles.append(
                VisualParticle(
                    x=x,
                    y=y,
                    vx=math.cos(ang) * spd,
                    vy=math.sin(ang) * spd,
                    life=1.0,
                    decay=random.uniform(0.04, 0.07),
                    kind="cloud",
                    color=(240, 248, 255),
                    size=random.uniform(16.0, 26.0),
                )
            )
