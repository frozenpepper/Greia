"""Domain model and simulation state for Il Viaggio del Delfino.

The module owns the gameplay invariants:

- the dolphin always advances rightward; the child steers altitude and dash;
- above the water line motion is ballistic (breaching), below it swimming is
  a smooth spring-damped pursuit of a target altitude (no fail state);
- jellyfish never damage: contact gently pushes the dolphin away;
- chapters advance purely by travelled distance and emit semantic events.

Rendering, audio, storage and platform IO live elsewhere; this file stays
pure simulation so it is unit-testable without pygame or Greia services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
from typing import Final

try:
    from delfino_content import CHAPTERS, TOTAL_JOURNEY_X, chapter_index_for_x
except ImportError:  # repository/package import context
    from .delfino_content import CHAPTERS, TOTAL_JOURNEY_X, chapter_index_for_x

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600

#: Water line in reference coordinates. Above it the dolphin breaches.
SURFACE_Y: Final = 175.0

#: Vertical bounds for the dolphin centre. The upper bound allows real leaps
#: above the waves while keeping the animal fully on screen.
MIN_SWIM_Y: Final = 70.0
MAX_SWIM_Y: Final = 520.0

#: Collision radius used for all pickups/obstacles against the dolphin centre.
DOLPHIN_RADIUS: Final = 46.0

#: The dolphin sprite is long; children aim with the nose. Starfish treasure
#: also collects when the nose reaches it, not only mid-body.
DOLPHIN_NOSE_OFFSET: Final = 92.0

#: Cruise speed in px/s at 60 fps-normalised dt; dash multiplies it briefly.
BASE_SPEED: Final = 180.0
DASH_MULTIPLIER: Final = 1.9
DASH_DURATION: Final = 2.0

#: Ballistics for breaching (px/s^2). Tuned so a full leap lasts ~1.6 s.
GRAVITY: Final = 900.0
LEAVE_WATER_BOOST: Final = -430.0

#: Breach somersault duration (s). Slightly shorter than the ballistic air
#: time so the flip finishes and the dolphin levels out before re-entry.
FLIP_DURATION: Final = 0.85

#: While cruising (not dashing) the swim target is clamped just under the
#: surface, so leaping is a deliberate dash-through-the-waves action instead
#: of an accidental spring oscillation.
SURFACE_SWIM_MARGIN: Final = 30.0

SCORE_PER_PEARL: Final = 10
SCORE_PER_STARFISH: Final = 25

#: Minimum world distance between two golden starfish so special treasures
#: (and their spoken facts) stay evenly paced instead of clustering.
STARFISH_MIN_GAP: Final = 2400.0


@dataclass(slots=True)
class Dolphin:
    """The child-controlled dolphin."""

    x: float = 220.0
    y: float = 300.0
    target_y: float = 300.0
    vertical_velocity: float = 0.0
    dash_timer: float = 0.0
    tail_phase: float = 0.0
    #: Set when the nose crosses SURFACE_Y so splash FX fire exactly once.
    airborne: bool = False
    #: Seconds accumulated while airborne; drives the breach flip animation.
    air_time: float = 0.0
    #: Hysteresis after re-entry so fast spring steering cannot machine-gun
    #: splash events; the dolphin must dive back down before breaching again.
    surface_cooldown: float = 0.0

    @property
    def speed(self) -> float:
        return BASE_SPEED * (DASH_MULTIPLIER if self.dash_timer > 0.0 else 1.0)

    @property
    def is_dashing(self) -> bool:
        return self.dash_timer > 0.0

    def trigger_dash(self) -> None:
        self.dash_timer = DASH_DURATION

    @property
    def flip_step_fraction(self) -> float:
        """Normalized 0..1 progress through the breach somersault."""

        if not self.airborne:
            return 0.0
        return min(1.0, self.air_time / FLIP_DURATION)

    def steer(self, delta_y: float) -> None:
        """Immediate altitude nudge from keyboard/controller semantics."""

        self.target_y = max(MIN_SWIM_Y, min(MAX_SWIM_Y, self.target_y + delta_y))

    def update(self, dt: float) -> str | None:
        """Advance one step; return "splash_in"/"splash_out" when crossing the surface."""

        event: str | None = None
        self.x += self.speed * dt
        if self.surface_cooldown > 0.0:
            self.surface_cooldown = max(0.0, self.surface_cooldown - dt)

        if self.y < SURFACE_Y - 8.0:
            # Airborne: ballistic arc. The boost fires once per leap entry;
            # only a dash can carry the dolphin through the surface, so each
            # breach is one deliberate child action.
            if not self.airborne and self.surface_cooldown <= 0.0:
                self.airborne = True
                self.air_time = 0.0
                self.vertical_velocity = LEAVE_WATER_BOOST
                event = "splash_out"
            self.air_time += dt
            self.vertical_velocity += GRAVITY * dt
            self.y += self.vertical_velocity * dt
            if self.y >= SURFACE_Y + 10.0:
                event = "splash_in"
        else:
            if self.airborne:
                self.airborne = False
                self.air_time = 0.0
                self.surface_cooldown = 0.6
                # Re-entry ends the boost: one dash buys exactly one leap.
                self.dash_timer = 0.0
                event = "splash_in"
            # In water: spring-damped chase of the child's target altitude.
            # Cruising cannot cross the surface; a dash unlocks the leap.
            effective_target = self.target_y
            if not self.is_dashing:
                effective_target = max(effective_target, SURFACE_Y + SURFACE_SWIM_MARGIN)
            dy = effective_target - self.y
            self.vertical_velocity = dy * 3.2
            self.y += self.vertical_velocity * dt

        self.y = max(MIN_SWIM_Y, min(MAX_SWIM_Y, self.y))
        beat = 9.0 if self.is_dashing else 5.5
        self.tail_phase = (self.tail_phase + beat * dt) % (2.0 * math.pi)

        if self.dash_timer > 0.0:
            self.dash_timer = max(0.0, self.dash_timer - dt)
        return event


@dataclass(slots=True)
class Pearl:
    """A shiny pearl resting in an open shell."""

    x: float
    y: float
    bob_phase: float = 0.0
    collected: bool = False

    @property
    def effective_y(self) -> float:
        return self.y + math.sin(self.bob_phase) * 5.0

    def update(self, dt: float) -> None:
        self.bob_phase = (self.bob_phase + 2.6 * dt) % (2.0 * math.pi)

    def collides_with(self, px: float, py: float) -> bool:
        if self.collected:
            return False
        return (
            (px - self.x) ** 2 + (py - self.effective_y) ** 2
            <= DOLPHIN_RADIUS**2
        )


@dataclass(slots=True)
class Starfish:
    """A rare golden starfish bonus."""

    x: float
    y: float
    spin_phase: float = 0.0
    collected: bool = False

    def update(self, dt: float) -> None:
        self.spin_phase = (self.spin_phase + 2.0 * dt) % (2.0 * math.pi)

    def collides_with(self, px: float, py: float) -> bool:
        if self.collected:
            return False
        return (px - self.x) ** 2 + (py - self.y) ** 2 <= DOLPHIN_RADIUS**2


@dataclass(slots=True)
class Jellyfish:
    """A friendly drifting jellyfish.

    Contact never harms the child: the model only records a bounded cooldown
    so one pass produces exactly one gentle bounce.
    """

    x: float
    y: float
    drift_amplitude: float = 42.0
    drift_phase: float = 0.0
    drift_speed: float = 1.1
    bump_cooldown: float = 0.0

    @property
    def effective_y(self) -> float:
        return self.y + math.sin(self.drift_phase) * self.drift_amplitude

    def update(self, dt: float) -> None:
        self.drift_phase = (self.drift_phase + self.drift_speed * dt) % (2.0 * math.pi)
        if self.bump_cooldown > 0.0:
            self.bump_cooldown = max(0.0, self.bump_cooldown - dt)

    def collides_with(self, px: float, py: float) -> bool:
        return (
            abs(px - self.x) <= DOLPHIN_RADIUS
            and abs(py - self.effective_y) <= DOLPHIN_RADIUS
            and self.bump_cooldown <= 0.0
        )


@dataclass(slots=True)
class SeaDecor:
    """Non-interactive background scenery (kelp columns, corals)."""

    x: float
    kind: str  # "kelp" | "coral"


@dataclass(slots=True)
class Bubble:
    """Ambient bubble with bounded lifetime."""

    x: float
    y: float
    vy: float
    life: float = 2.2
    size: int = 10

    def update(self, dt: float) -> bool:
        self.y -= self.vy * dt
        self.life -= dt
        return self.life > 0.0 and self.y > SURFACE_Y - 20.0


@dataclass(slots=True)
class SparkleParticle:
    """Short celebration particle with velocity and decay."""

    x: float
    y: float
    vx: float
    vy: float
    life: float = 1.0
    decay: float = 2.2
    kind: str = "sparkle"  # "sparkle" | "splash" | "confetti"
    color: tuple[int, int, int] = (255, 236, 150)
    size: float = 14.0

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.kind == "splash":
            self.vy += 500.0 * dt
        self.life -= self.decay * dt
        return self.life > 0.0


@dataclass
class JourneyState:
    """Complete simulation state for one journey."""

    dolphin: Dolphin = field(default_factory=Dolphin)
    pearls: list[Pearl] = field(default_factory=list)
    starfish: list[Starfish] = field(default_factory=list)
    jellies: list[Jellyfish] = field(default_factory=list)
    decor: list[SeaDecor] = field(default_factory=list)
    bubbles: list[Bubble] = field(default_factory=list)
    particles: list[SparkleParticle] = field(default_factory=list)

    session_pearls: int = 0
    chapter_value: float = 0.0
    chapters_completed: int = 0
    finished: bool = False

    next_spawn_x: float = 700.0
    _bubble_timer: float = 0.35
    _dash_bubble_timer: float = 0.0
    _last_starfish_x: float = -10_000.0

    def start_journey(self, rng: random.Random | None = None) -> None:
        """Reset to a fresh journey (used at launch and on replay)."""

        rng = rng or random.Random()
        self.dolphin = Dolphin()
        for collection in (self.pearls, self.starfish, self.jellies, self.decor, self.bubbles, self.particles):
            collection.clear()
        self.session_pearls = 0
        self.chapter_value = 0.0
        self.chapters_completed = 0
        self.finished = False
        self.next_spawn_x = 700.0
        self._last_starfish_x = -10_000.0
        # Fixed landmarks mark each chapter boundary and the golden finish;
        # they are decorative world objects, never collisions.
        self.decor.append(SeaDecor(9850.0, "arch_coral"))
        self.decor.append(SeaDecor(19750.0, "arch_kelp"))
        self.decor.append(SeaDecor(29700.0, "reef_gold"))
        self._spawn_chunk(700.0, 3200.0, rng)
        self.next_spawn_x = 3200.0

    # ------------------------------------------------------------------ sim

    def update(self, dt: float, rng: random.Random | None = None) -> list[str]:
        """Advance the world; return semantic event IDs for the app layer."""

        rng = rng or random.Random()
        events: list[str] = []
        dolf = self.dolphin
        cam_x = dolf.x - 220.0

        splash = dolf.update(dt)
        if splash == "splash_out":
            events.append("splash_out")
            self._spawn_splash(dolf.x, SURFACE_Y, downward=False, rng=rng)
        elif splash == "splash_in":
            events.append("splash_in")
            self._spawn_splash(dolf.x, SURFACE_Y, downward=True, rng=rng)

        # Stream new content ahead of the dolphin (a little past the finish
        # so the last stretch still sparkles).
        if dolf.x + 1900.0 > self.next_spawn_x:
            end = min(self.next_spawn_x + 2500.0, TOTAL_JOURNEY_X + 400.0)
            self._spawn_chunk(self.next_spawn_x, end, rng)
            self.next_spawn_x = end

        # Ambient bubbles (bounded).
        self._bubble_timer -= dt
        if self._bubble_timer <= 0.0:
            self._bubble_timer = random.uniform(0.5, 1.4)
            if len(self.bubbles) < 40:
                self.bubbles.append(
                    Bubble(
                        x=dolf.x + random.uniform(-160.0, 320.0),
                        y=random.uniform(SURFACE_Y + 80.0, MAX_SWIM_Y),
                        vy=random.uniform(26.0, 58.0),
                        size=random.choice((7, 9, 11)),
                    )
                )
        # Dash wake: small trailing bubbles while boosting underwater.
        self._dash_bubble_timer -= dt
        if self._dash_bubble_timer <= 0.0:
            self._dash_bubble_timer = 0.12
            if dolf.is_dashing and not dolf.airborne and len(self.bubbles) < 56:
                for _ in range(2):
                    self.bubbles.append(
                        Bubble(
                            x=dolf.x - random.uniform(40.0, 90.0),
                            y=dolf.y + random.uniform(-22.0, 22.0),
                            vy=random.uniform(24.0, 46.0),
                            size=random.choice((5, 6, 7)),
                            life=1.4,
                        )
                    )
        self.bubbles = [b for b in self.bubbles if b.update(dt)]

        # Pickups.
        for pearl in self.pearls:
            pearl.update(dt)
            if pearl.collides_with(dolf.x, dolf.y):
                pearl.collected = True
                self.session_pearls += 1
                self.chapter_value += SCORE_PER_PEARL
                events.append("pearl_collected")
                self._spawn_sparkle(pearl.x, pearl.effective_y, "sparkle", rng)
        for star in self.starfish:
            star.update(dt)
            if star.collides_with(dolf.x, dolf.y) or star.collides_with(
                dolf.x + DOLPHIN_NOSE_OFFSET, dolf.y
            ):
                star.collected = True
                self.session_pearls += 1
                self.chapter_value += SCORE_PER_STARFISH
                events.append("starfish_collected")
                self._spawn_sparkle(star.x, star.y, "confetti", rng)

        # Jellyfish: gentle push away, never harm.
        for jelly in self.jellies:
            jelly.update(dt)
            if jelly.collides_with(dolf.x, dolf.y):
                jelly.bump_cooldown = 1.4
                away = MIN_SWIM_Y + 50.0 if dolf.y >= jelly.effective_y else MAX_SWIM_Y - 50.0
                dolf.target_y = away
                events.append("jelly_bounce")
                self._spawn_sparkle(jelly.x, jelly.effective_y, "sparkle", rng)

        self.particles = [p for p in self.particles if p.update(dt)]

        # Prune passed world objects (bounded memory over a long swim).
        cutoff = cam_x - 400.0
        self.pearls = [p for p in self.pearls if p.x > cutoff]
        self.starfish = [s for s in self.starfish if s.x > cutoff]
        self.jellies = [j for j in self.jellies if j.x > cutoff]
        self.decor = [d for d in self.decor if d.x > cutoff]

        # Chapter progression: crossing into chapter i completes i chapters;
        # swimming the full journey completes all of them exactly once.
        done_now = chapter_index_for_x(dolf.x)
        if dolf.x >= TOTAL_JOURNEY_X:
            done_now = len(CHAPTERS)
        while self.chapters_completed < done_now and not self.finished:
            self.chapters_completed += 1
            events.append("chapter_completed")
            self._spawn_celebration(rng)
            if self.chapters_completed >= len(CHAPTERS):
                self.finished = True
                events.append("journey_finished")
        return events

    # -------------------------------------------------------------- spawning

    def _spawn_chunk(self, start_x: float, end_x: float, rng: random.Random) -> None:
        """Generate rhythmic pickup/obstacle waves between two world x values."""

        cur = start_x
        while cur < end_x:
            chapter_idx = min(chapter_index_for_x(cur), len(CHAPTERS) - 1)
            pattern = rng.choice(self._patterns_for(chapter_idx))
            getattr(self, f"_pattern_{pattern}")(cur, rng)
            cur += rng.uniform(420.0, 560.0)

    @staticmethod
    def _patterns_for(chapter_idx: int) -> tuple[str, ...]:
        if chapter_idx == 0:
            return ("pearl_wave", "breach_arc", "coral_row", "lone_jelly", "star_solo")
        if chapter_idx == 1:
            return ("kelp_grove", "kelp_grove", "pearl_cluster", "jelly_pair", "pearl_wave")
        return ("big_breach", "starfish_run", "jelly_trio", "breach_arc")

    def _spawn_starfish(self, x: float, y: float) -> None:
        """Place a golden starfish only if the pacing gap is respected."""

        if x - self._last_starfish_x < STARFISH_MIN_GAP:
            self.pearls.append(Pearl(x, y))
            return
        self._last_starfish_x = x
        self.starfish.append(Starfish(x, y))

    def _pattern_pearl_wave(self, x: float, rng: random.Random) -> None:
        base_y = rng.uniform(SURFACE_Y + 90.0, MAX_SWIM_Y - 90.0)
        freq = rng.uniform(0.55, 0.85)
        amp = rng.uniform(38.0, 64.0)
        for step in range(5):
            y = base_y + math.sin(step * freq) * amp
            y = max(SURFACE_Y + 40.0, min(MAX_SWIM_Y, y))
            self.pearls.append(Pearl(x + step * 78.0, y))
        if rng.random() < 0.5:
            self.jellies.append(
                Jellyfish(x + 200.0, rng.uniform(MAX_SWIM_Y - 160.0, MAX_SWIM_Y - 60.0))
            )

    def _pattern_breach_arc(self, x: float, rng: random.Random) -> None:
        """Pearls arcing out of and back into the water: rewards a well-timed leap."""

        apex = rng.uniform(MIN_SWIM_Y + 30.0, SURFACE_Y - 60.0)
        mid = (apex + (SURFACE_Y + 120.0)) / 2.0
        positions = (
            (0.0, SURFACE_Y + 110.0),
            (95.0, mid),
            (185.0, apex),
            (280.0, mid),
            (370.0, SURFACE_Y + 110.0),
        )
        for dx, y in positions:
            self.pearls.append(Pearl(x + dx, y))
        if rng.random() < 0.65:
            self.jellies.append(Jellyfish(x + 480.0, rng.uniform(330.0, MAX_SWIM_Y - 70.0)))

    def _pattern_big_breach(self, x: float, rng: random.Random) -> None:
        """Chapter-3 grand arc crowned by a golden starfish."""

        apex = rng.uniform(MIN_SWIM_Y + 20.0, SURFACE_Y - 70.0)
        mid = (apex + SURFACE_Y + 140.0) / 2.0
        self.pearls.append(Pearl(x, SURFACE_Y + 130.0))
        self.pearls.append(Pearl(x + 100.0, mid))
        self._spawn_starfish(x + 205.0, apex)
        self.pearls.append(Pearl(x + 310.0, mid))
        self.pearls.append(Pearl(x + 410.0, SURFACE_Y + 130.0))

    def _pattern_starfish_run(self, x: float, rng: random.Random) -> None:
        base_y = rng.uniform(SURFACE_Y + 120.0, MAX_SWIM_Y - 110.0)
        for step in range(3):
            self.pearls.append(Pearl(x + step * 85.0, base_y))
        self._spawn_starfish(x + 260.0, base_y - 70.0)

    def _pattern_star_solo(self, x: float, rng: random.Random) -> None:
        """Early-chapter single treasure so stars appear from the start."""

        y = rng.uniform(SURFACE_Y + 110.0, MAX_SWIM_Y - 110.0)
        self._spawn_starfish(x + 120.0, y)
        for step in range(2):
            self.pearls.append(Pearl(x + 40.0 + step * 160.0, y + 46.0))

    def _pattern_coral_row(self, x: float, rng: random.Random) -> None:
        for step in range(3):
            self.decor.append(SeaDecor(x + step * 240.0, "coral"))
        base_y = rng.uniform(SURFACE_Y + 150.0, MAX_SWIM_Y - 80.0)
        for step in range(4):
            self.pearls.append(Pearl(x + 60.0 + step * 82.0, base_y))

    def _pattern_kelp_grove(self, x: float, rng: random.Random) -> None:
        """A dense, tall algae grove — the kelp forest must look like one."""

        for step in range(6):
            self.decor.append(SeaDecor(x + step * 170.0, "kelp"))
        slot_y = rng.uniform(SURFACE_Y + 100.0, MAX_SWIM_Y - 100.0)
        for step in range(3):
            self.pearls.append(Pearl(x + 105.0 + step * 210.0, slot_y))
        if rng.random() < 0.45:
            self._spawn_starfish(x + 510.0, slot_y - 60.0)
        if rng.random() < 0.5:
            self.jellies.append(
                Jellyfish(x + 315.0, rng.uniform(SURFACE_Y + 140.0, MAX_SWIM_Y - 80.0))
            )

    def _pattern_pearl_cluster(self, x: float, rng: random.Random) -> None:
        cx = x + 120.0
        cy = rng.uniform(SURFACE_Y + 120.0, MAX_SWIM_Y - 90.0)
        for dx, dy in ((-42.0, 0.0), (0.0, -36.0), (42.0, 0.0), (0.0, 36.0), (0.0, 0.0)):
            self.pearls.append(Pearl(cx + dx, cy + dy))

    def _pattern_lone_jelly(self, x: float, rng: random.Random) -> None:
        self.jellies.append(Jellyfish(x + 90.0, rng.uniform(SURFACE_Y + 170.0, MAX_SWIM_Y - 70.0)))
        self.pearls.append(Pearl(x + 90.0, max(SURFACE_Y + 40.0, rng.uniform(SURFACE_Y + 60.0, SURFACE_Y + 130.0))))

    def _pattern_jelly_pair(self, x: float, rng: random.Random) -> None:
        y_low = rng.uniform(MAX_SWIM_Y - 150.0, MAX_SWIM_Y - 60.0)
        y_high = rng.uniform(SURFACE_Y + 150.0, y_low - 140.0)
        self.jellies.append(Jellyfish(x + 110.0, y_low, drift_speed=0.9))
        self.jellies.append(Jellyfish(x + 340.0, y_high, drift_speed=1.3))

    def _pattern_jelly_trio(self, x: float, rng: random.Random) -> None:
        for step, speed in enumerate((0.8, 1.15, 1.5)):
            y = rng.uniform(SURFACE_Y + 160.0, MAX_SWIM_Y - 70.0)
            self.jellies.append(Jellyfish(x + 100.0 + step * 230.0, y, drift_speed=speed))

    # ------------------------------------------------------------- particles

    def _spawn_sparkle(self, x: float, y: float, kind: str, rng: random.Random) -> None:
        count = 8 if kind == "sparkle" else 12
        color = (255, 226, 120) if kind == "sparkle" else (255, 208, 74)
        for _ in range(count):
            angle = rng.uniform(0.0, 2.0 * math.pi)
            speed = rng.uniform(70.0, 190.0)
            self.particles.append(
                SparkleParticle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=1.0,
                    decay=rng.uniform(1.8, 2.8),
                    kind=kind,
                    color=color,
                    size=rng.uniform(10.0, 17.0),
                )
            )

    def _spawn_splash(self, x: float, y: float, *, downward: bool, rng: random.Random) -> None:
        for _ in range(10):
            angle = rng.uniform(-math.pi, 0.0) if not downward else rng.uniform(math.pi * 0.15, math.pi * 0.85)
            speed = rng.uniform(120.0, 260.0)
            self.particles.append(
                SparkleParticle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed * 0.6,
                    vy=abs(math.sin(angle)) * speed * (0.6 if not downward else -0.4),
                    life=1.0,
                    decay=2.4,
                    kind="splash",
                    color=(214, 240, 255),
                    size=rng.uniform(9.0, 16.0),
                )
            )

    def _spawn_celebration(self, rng: random.Random) -> None:
        for _ in range(24):
            angle = rng.uniform(0.0, 2.0 * math.pi)
            speed = rng.uniform(120.0, 300.0)
            color = rng.choice(((255, 214, 90), (126, 222, 178), (255, 148, 176), (140, 198, 255)))
            self.particles.append(
                SparkleParticle(
                    x=self.dolphin.x,
                    y=self.dolphin.y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=1.2,
                    decay=1.1,
                    kind="confetti",
                    color=color,
                    size=rng.uniform(12.0, 19.0),
                )
            )
