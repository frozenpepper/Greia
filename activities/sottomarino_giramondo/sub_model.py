"""Domain model for Sottomarino Giramondo (pure logic, no rendering).

The child pilots a submarine through three depth zones (coral reef, kelp
forest, glowing abyss), watches creatures glide past the porthole, plays
with the instruments (lights, sonar, bubbles, horn, alarm), meets a friendly
octopus or shark at the glass and, if they like, follows Captain Leo's
spoken orders. Orders are optional invitations: they are never failed, they
reveal a hint after a few seconds (or after two other instruments), and they
fade quietly when ignored. Three followed orders earn a star.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import enum
import math
import random
from typing import Dict, List, Optional, Tuple

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600

# Depth layers (meters)
MAX_DEPTH = 100.0
MIN_DEPTH = 0.0
# One press of Dive/Surface moves the target by this many metres, so the three
# zones (boundaries at 25 m and 65 m) are each a few taps apart for a child.
DEPTH_STEP = 15.0

# Every species below has four recorded facts in every bundled language.
FACT_SPECIES = frozenset({"whale", "turtle", "dolphin", "manta", "clownfish", "coral", "kelp", "krill"})
FACTS_PER_SPECIES = 4
# Facts are spoken on their own at most this often (taps can ask sooner), so
# they never crowd out the captain's orders.
AUTO_FACT_GAP_SECONDS = 30.0
FIRST_AUTO_FACT_SECONDS = 8.0
NAME_DISPLAY_SECONDS = 3.5
FACT_DISPLAY_SECONDS = 9.0

ORDER_HINT_SECONDS = 6.0
ORDER_EXPIRE_SECONDS = 25.0
ORDER_MISSES_BEFORE_HINT = 2
ORDERS_PER_STAR = 3

POPULATION = 26
# Entities closer than this have passed the glass and are retired.
NEAR_RETIRE_Z = 0.16
DISCOVERY_Z = 0.45


class BiomeType(enum.Enum):
    SHALLOW_REEF = "shallow"     # 0 - 25m: turquoise, sunbeams, clownfish, turtles
    TWILIGHT_KELP = "twilight"   # 25 - 65m: deep blue, kelp, dolphins, mantas
    MIDNIGHT_ABYSS = "abyss"     # 65 - 100m: dark indigo, krill, anglerfish, whales


def get_biome(depth: float) -> BiomeType:
    if depth < 25.0:
        return BiomeType.SHALLOW_REEF
    if depth < 65.0:
        return BiomeType.TWILIGHT_KELP
    return BiomeType.MIDNIGHT_ABYSS


BIOME_KINDS: Dict[BiomeType, Tuple[str, ...]] = {
    BiomeType.SHALLOW_REEF: ("clownfish", "clownfish", "turtle", "coral", "bubble"),
    BiomeType.TWILIGHT_KELP: ("dolphin", "manta", "kelp", "turtle", "bubble"),
    BiomeType.MIDNIGHT_ABYSS: ("angler", "whale", "krill", "manta", "bubble"),
}

# Relative size of each kind (the original cockpit's proportions).
KIND_SIZE: Dict[str, float] = {
    "clownfish": 0.9,
    "turtle": 1.4,
    "dolphin": 1.8,
    "manta": 2.0,
    "angler": 1.2,
    "whale": 3.0,
    "coral": 1.6,
    "kelp": 2.2,
    "krill": 1.5,
    "bubble": 0.4,
}

# Captain's orders: (order id, picture/instrument id, spoken cue).
ORDER_TABLE: Dict[str, Tuple[str, str]] = {
    "ahead": ("ahead", "voice.order.ahead"),
    "stop": ("stop", "voice.order.stop"),
    "left": ("steer_left", "voice.order.left"),
    "right": ("steer_right", "voice.order.right"),
    "light": ("light", "voice.btn.light"),
    "sonar": ("sonar", "voice.btn.sonar"),
    "bubbles": ("bubbles", "voice.btn.bubbles"),
    "horn": ("horn", "voice.btn.horn"),
}


@dataclass
class MarineEntity3D:
    """A 3D ocean entity located in camera-relative coordinates (x, y, z).

    x: [-1.0, 1.0] horizontal (negative = left, positive = right)
    y: [-0.6, 0.6] vertical (negative = up, positive = down)
    z: [0.1, 1.5] depth distance (1.5 = far in fog, 0.1 = close to viewport)
    """
    id: str
    kind: str
    x: float
    y: float
    z: float
    vx: float = 0.0
    vy: float = 0.0
    vz: float = -0.1    # approaching camera by default
    size_base: float = 1.0
    phase: float = 0.0  # oscillation / swimming phase
    discovered: bool = False


class EncounterType(enum.Enum):
    NONE = "none"
    OCTOPUS_HUG = "octopus_hug"  # Giant cuddly octopus hugs the porthole glass
    SHARK_WAVE = "shark_wave"    # Curious smiling shark waves at the glass


# Which instruments make each visitor happy (the alarm always works too).
ENCOUNTER_HELPERS: Dict[EncounterType, Tuple[str, ...]] = {
    EncounterType.OCTOPUS_HUG: ("horn", "bubbles"),
    EncounterType.SHARK_WAVE: ("light",),
}


@dataclass
class OrderState:
    order_id: str = "none"       # "ahead", "stop", "left", "right", "light", "sonar", "bubbles", "horn"
    prompt_text_key: str = ""
    cue_key: str = ""
    active: bool = False
    solved: bool = False
    timer: float = 0.0           # celebration time left once solved
    age: float = 0.0             # seconds since the order was given
    misses: int = 0              # other instruments pressed meanwhile
    hinted: bool = False

    @property
    def target(self) -> str:
        """Instrument/button id that follows this order."""
        return ORDER_TABLE.get(self.order_id, ("", ""))[0]

    @property
    def waiting(self) -> bool:
        return self.active and not self.solved


@dataclass
class FactState:
    species: str = ""
    fact_index: int = 1
    text_key: str = ""           # empty: name only (no fact)
    cue_key: str = ""
    display_timer: float = 0.0
    serial: int = 0              # increments for every new card


@dataclass
class EncounterState:
    active_type: EncounterType = EncounterType.NONE
    progress: float = 0.0        # 0.0 to 1.0 (fade-in / active)
    solved: bool = False
    solve_timer: float = 0.0
    reaction_cue: str = ""


@dataclass
class SubmarineLog:
    """Durable, profile-scoped progress (architecture-neutral JSON)."""

    stars: int = 0
    species: List[str] = field(default_factory=list)

    SCHEMA = 1
    MAX_STARS = 9999

    def export(self) -> dict:
        return {"schema": self.SCHEMA, "stars": int(self.stars), "species": sorted(set(self.species))}

    @classmethod
    def from_payload(cls, payload: object) -> "SubmarineLog":
        if not isinstance(payload, dict):
            return cls()
        stars = payload.get("stars", 0)
        species = payload.get("species", [])
        known = set(KIND_SIZE) - {"bubble"}
        return cls(
            stars=max(0, min(cls.MAX_STARS, stars)) if isinstance(stars, int) else 0,
            species=[s for s in species if isinstance(s, str) and s in known] if isinstance(species, list) else [],
        )


class SubmarineModel:
    """Pure domain model of the submarine exploration vehicle."""

    def __init__(self, rng: Optional[random.Random] = None, log: Optional[SubmarineLog] = None) -> None:
        self._rng = rng if rng is not None else random.Random()
        self.log = log if log is not None else SubmarineLog()

        # Submarine dynamics
        self.depth: float = 5.0
        self.target_depth: float = 5.0
        self.heading: float = 0.0        # Horizontal turn offset [-1.0, 1.0]
        self.wheel_angle: float = 0.0    # Ship rudder wheel rotation in degrees
        self.speed: float = 0.5          # Forward engine speed [0.0, 1.0]

        # Cockpit instruments
        self.lights_on: bool = False
        self.sonar_active: bool = False
        self.sonar_timer: float = 0.0
        self.radar_angle: float = 0.0
        self.bubble_release_timer: float = 0.0

        self.entities: List[MarineEntity3D] = []
        self._next_id = 0
        self._spawn_ambient_entities()

        self.encounter = EncounterState()
        self._encounter_cooldown: float = 12.0

        self.current_order = OrderState()
        self._order_cooldown: float = 4.0
        self.orders_in_set: int = 0

        self.active_fact = FactState()
        self._fact_cooldown: float = FIRST_AUTO_FACT_SECONDS
        self._fact_next: Dict[str, int] = {}

        # Species met during this session (events + spoken names).
        self.discovered_species: set[str] = set()

    # -- population ---------------------------------------------------------

    def _spawn_ambient_entities(self) -> None:
        self.entities.clear()
        for _ in range(POPULATION):
            self._spawn_random_entity(initial_z=self._rng.uniform(0.3, 1.4))

    def _spawn_random_entity(self, initial_z: Optional[float] = None) -> None:
        rng = self._rng
        biome = get_biome(self.depth)
        z = initial_z if initial_z is not None else rng.uniform(1.2, 1.5)

        # 75% spawn in the porthole's field of view; 25% on the flanks swimming inward
        if rng.random() < 0.75:
            x = rng.uniform(-0.45, 0.45)
            vx = rng.uniform(-0.03, 0.03)
        else:
            side = -1.0 if rng.random() < 0.5 else 1.0
            x = side * rng.uniform(0.5, 0.85)
            vx = -side * rng.uniform(0.04, 0.08)
        y = rng.uniform(-0.4, 0.4)

        kind = rng.choice(BIOME_KINDS[biome])
        size = KIND_SIZE[kind]
        if kind == "clownfish":
            y = rng.uniform(-0.3, 0.3)
        elif kind == "whale":
            z = max(0.4, z)  # glides past majestically, never nose-first into the glass
        elif kind == "coral":
            y = rng.uniform(0.15, 0.45)  # sits near the reef floor
            vx = 0.0
        elif kind == "kelp":
            y = rng.uniform(0.05, 0.4)
            vx = 0.0
        elif kind == "bubble":
            vx = rng.uniform(-0.02, 0.02)

        vy = rng.uniform(-0.015, 0.015)
        vz = -rng.uniform(0.04, 0.1) if kind != "bubble" else -0.02
        self.entities.append(MarineEntity3D(
            id=self._new_id(kind), kind=kind, x=x, y=y, z=z, vx=vx, vy=vy, vz=vz,
            size_base=size, phase=rng.uniform(0, math.pi * 2),
        ))

    def _new_id(self, kind: str) -> str:
        self._next_id += 1
        return f"{kind}_{self._next_id}"

    # -- instruments --------------------------------------------------------

    def toggle_lights(self) -> bool:
        self.lights_on = not self.lights_on
        return self.lights_on

    def trigger_sonar(self) -> None:
        self.sonar_active = True
        self.sonar_timer = 2.5

    def trigger_bubbles(self, at: Optional[Tuple[float, float]] = None) -> None:
        """Release a burst of close bubbles (around ``at`` in view space if given)."""
        self.bubble_release_timer = 1.5
        cx, cy = at if at is not None else (0.0, 0.4)
        rng = self._rng
        # Keep the burst bounded: old close bubbles make room for new ones.
        close = [e for e in self.entities if e.kind == "bubble" and e.vz == 0.0]
        for old in close[: max(0, len(close) - 16)]:
            self.entities.remove(old)
        for _ in range(8):
            self.entities.append(MarineEntity3D(
                id=self._new_id("bubble"), kind="bubble",
                x=cx * 0.25 + rng.uniform(-0.12, 0.12),
                y=cy * 0.25 + rng.uniform(0.0, 0.12),
                z=rng.uniform(0.18, 0.3),
                vx=rng.uniform(-0.05, 0.05), vy=-rng.uniform(0.2, 0.5), vz=0.0,
                size_base=rng.uniform(0.3, 0.7),
            ))

    def trigger_horn(self) -> None:
        """The horn's ripple is presentation; resolution is handled by the app."""

    def steer(self, dx: float, dy: float) -> None:
        """Steer heading (-1.0 to 1.0) and adjust target depth (0 to 100m)."""
        self.heading = max(-1.0, min(1.0, self.heading + dx * 0.1))
        self.target_depth = max(MIN_DEPTH, min(MAX_DEPTH, self.target_depth + dy * 2.0))

    def change_depth(self, direction: int) -> float:
        """Dive (+1) or surface (-1) by one step; returns the new target depth."""
        step = DEPTH_STEP if direction > 0 else -DEPTH_STEP
        self.target_depth = max(MIN_DEPTH, min(MAX_DEPTH, self.target_depth + step))
        return self.target_depth

    def set_speed(self, speed: float) -> None:
        self.speed = max(0.0, min(1.0, speed))

    # -- captain's orders ---------------------------------------------------

    def check_action(self, action_name: str) -> bool:
        """True when ``action_name`` (or the current state) follows the order."""
        order = self.current_order
        if not order.waiting:
            return False

        target = order.order_id
        is_match = False
        if target == "ahead" and (action_name in ("ahead", "forward") or self.speed > 0.4):
            is_match = True
        elif target == "stop" and (action_name in ("stop", "halt") or self.speed <= 0.1):
            is_match = True
        elif target == "left" and (action_name in ("left", "steer_left") or self.heading < -0.15):
            is_match = True
        elif target == "right" and (action_name in ("right", "steer_right") or self.heading > 0.15):
            is_match = True
        elif target == "light" and (action_name == "light" or self.lights_on):
            is_match = True
        elif target == "sonar" and (action_name == "sonar" or self.sonar_active):
            is_match = True
        elif target == "bubbles" and action_name == "bubbles":
            is_match = True
        elif target == "horn" and action_name in ("horn", "action"):
            is_match = True

        if is_match:
            order.solved = True
            order.timer = 2.0
            return True
        return False

    def note_other_instrument(self) -> None:
        """Another instrument was used while an order waits: hint sooner."""
        order = self.current_order
        if order.waiting:
            order.misses += 1
            if order.misses >= ORDER_MISSES_BEFORE_HINT:
                order.hinted = True

    def record_order_followed(self) -> bool:
        """Count one followed order; True when it completes a star."""
        self.orders_in_set += 1
        if self.orders_in_set >= ORDERS_PER_STAR:
            self.orders_in_set = 0
            self.log.stars = min(SubmarineLog.MAX_STARS, self.log.stars + 1)
            return True
        return False

    def _issue_order(self) -> None:
        eligible: List[str] = []
        if self.speed <= 0.3:
            eligible.append("ahead")
        if self.speed >= 0.4:
            eligible.append("stop")
        if self.heading >= -0.15:
            eligible.append("left")
        if self.heading <= 0.15:
            eligible.append("right")
        if not self.lights_on:
            eligible.append("light")
        if not self.sonar_active:
            eligible.append("sonar")
        eligible += ["bubbles", "horn"]
        chosen = self._rng.choice(eligible)
        self.current_order = OrderState(
            order_id=chosen,
            prompt_text_key=f"order.{chosen}",
            cue_key=ORDER_TABLE[chosen][1],
            active=True,
        )

    # -- facts --------------------------------------------------------------

    def trigger_species_fact(self, species: str) -> bool:
        """Show (and let the app speak) the next recorded fact for ``species``.

        Facts rotate through the four recordings so a child hears them all.
        Species without recorded facts show only their name.
        """
        if species == "bubble" or species not in KIND_SIZE:
            return False
        fact = self.active_fact
        fact.species = species
        fact.serial += 1
        if species in FACT_SPECIES:
            idx = self._fact_next.get(species, 1)
            self._fact_next[species] = idx % FACTS_PER_SPECIES + 1
            fact.fact_index = idx
            fact.text_key = f"voice.fact.{species}.{idx}"
            fact.cue_key = fact.text_key
            fact.display_timer = FACT_DISPLAY_SECONDS
        else:
            fact.fact_index = 0
            fact.text_key = ""
            fact.cue_key = ""
            fact.display_timer = NAME_DISPLAY_SECONDS
        self._fact_cooldown = AUTO_FACT_GAP_SECONDS
        return True

    def show_species_name(self, species: str) -> None:
        """Show a species name card without a fact (a first sighting)."""
        fact = self.active_fact
        fact.species = species
        fact.fact_index = 0
        fact.text_key = ""
        fact.cue_key = ""
        fact.display_timer = NAME_DISPLAY_SECONDS
        fact.serial += 1

    # -- encounters ---------------------------------------------------------

    def resolve_encounter(self) -> bool:
        """Called when the child uses a helping instrument during an encounter."""
        if self.encounter.active_type != EncounterType.NONE and not self.encounter.solved:
            self.encounter.solved = True
            self.encounter.solve_timer = 2.0
            return True
        return False

    def encounter_waiting(self) -> bool:
        return self.encounter.active_type != EncounterType.NONE and not self.encounter.solved

    # -- simulation ---------------------------------------------------------

    def update(self, dt: float) -> Tuple[List[str], Optional[str]]:
        """Advance simulation time.

        Returns (newly_discovered_creatures, newly_completed_event).
        """
        dt = max(0.0, min(0.25, dt))
        discovered: List[str] = []
        completed_event: Optional[str] = None
        biome_before = get_biome(self.depth)

        self.depth += (self.target_depth - self.depth) * min(1.0, dt * 1.5)
        self.heading *= max(0.0, 1.0 - dt * 0.8)
        target_wheel = self.heading * 75.0
        self.wheel_angle += (target_wheel - self.wheel_angle) * min(1.0, dt * 5.0)
        self.radar_angle = (self.radar_angle + dt * 180.0) % 360.0

        if self.sonar_timer > 0:
            self.sonar_timer -= dt
            if self.sonar_timer <= 0:
                self.sonar_active = False
        if self.bubble_release_timer > 0:
            self.bubble_release_timer -= dt
        if self.active_fact.display_timer > 0:
            self.active_fact.display_timer -= dt
        if self._fact_cooldown > 0:
            self._fact_cooldown -= dt

        self._update_order(dt)

        # Entities in 3D space
        forward_advance = self.speed * dt * 0.4
        surviving: List[MarineEntity3D] = []
        auto_fact_species: Optional[str] = None
        for ent in self.entities:
            ent.phase += dt * 3.0
            ent.x -= self.heading * dt * 0.5
            ent.z += ent.vz * forward_advance * 3.0 + (ent.vz * dt * 0.2)
            ent.x += ent.vx * dt
            ent.y += ent.vy * dt
            ent.y += math.sin(ent.phase) * dt * 0.05

            if ent.z < DISCOVERY_Z and not ent.discovered and ent.kind != "bubble" and abs(ent.x) < 0.45:
                ent.discovered = True
                if ent.kind not in self.discovered_species:
                    self.discovered_species.add(ent.kind)
                    discovered.append(ent.kind)
                    if ent.kind not in self.log.species:
                        self.log.species.append(ent.kind)
                elif auto_fact_species is None and ent.kind in FACT_SPECIES:
                    auto_fact_species = ent.kind

            if NEAR_RETIRE_Z < ent.z < 1.6 and abs(ent.x) < 1.5 and ent.y > -1.2:
                surviving.append(ent)
        self.entities = surviving

        # A zone change refreshes the view with that zone's creatures.
        if get_biome(self.depth) != biome_before:
            self.entities = [e for e in self.entities if e.kind == "bubble" or e.z < 0.6]
        while sum(1 for e in self.entities if not (e.kind == "bubble" and e.vz == 0.0)) < POPULATION:
            self._spawn_random_entity(
                initial_z=self._rng.uniform(0.7, 1.45) if get_biome(self.depth) != biome_before else None
            )

        quiet = not self.current_order.active and self.encounter.active_type == EncounterType.NONE
        if discovered and self.active_fact.display_timer <= 0:
            self.show_species_name(discovered[0])
        elif (
            auto_fact_species is not None
            and quiet
            and self._fact_cooldown <= 0
            and self.active_fact.display_timer <= 0
        ):
            self.trigger_species_fact(auto_fact_species)

        completed_event = self._update_encounter(dt)
        return discovered, completed_event

    def _update_order(self, dt: float) -> None:
        order = self.current_order
        if order.active:
            if order.solved:
                order.timer -= dt
                if order.timer <= 0:
                    self._end_order()
            else:
                order.age += dt
                if order.age >= ORDER_HINT_SECONDS:
                    order.hinted = True
                if order.age >= ORDER_EXPIRE_SECONDS:
                    self._end_order()  # ignored invitations simply fade
        elif self.encounter.active_type == EncounterType.NONE:
            self._order_cooldown -= dt
            if self._order_cooldown <= 0:
                self._issue_order()

    def _end_order(self) -> None:
        self.current_order = OrderState()
        self._order_cooldown = self._rng.uniform(8.0, 14.0)

    def _update_encounter(self, dt: float) -> Optional[str]:
        enc = self.encounter
        if enc.active_type == EncounterType.NONE:
            # Encounters wait politely while an order is being followed.
            if not self.current_order.waiting:
                self._encounter_cooldown -= dt
            if self._encounter_cooldown <= 0.0:
                enc.active_type = self._rng.choice([EncounterType.OCTOPUS_HUG, EncounterType.SHARK_WAVE])
                enc.progress = 0.0
                enc.solved = False
                enc.solve_timer = 0.0
            return None
        if not enc.solved:
            enc.progress = min(1.0, enc.progress + dt * 1.5)
            return None
        enc.solve_timer -= dt
        if enc.solve_timer <= 0:
            enc.active_type = EncounterType.NONE
            enc.solved = False
            self._encounter_cooldown = self._rng.uniform(15.0, 25.0)
            return "submarine.encounter_resolved"
        return None
