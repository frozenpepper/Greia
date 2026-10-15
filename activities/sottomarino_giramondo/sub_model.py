"""Domain Model and State for Sottomarino Giramondo.

Maintains submarine speed, depth, heading, 3D entity simulation,
cockpit control states, and creature encounters. Pure domain logic,
free of direct rendering dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import enum
import math
import random
from typing import List, Optional, Tuple

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600

# Depth layers (meters)
MAX_DEPTH = 100.0
MIN_DEPTH = 0.0
# One press of Dive/Surface moves the target by this many metres, so the three
# zones (boundaries at 25 m and 65 m) are each a few taps apart for a child.
DEPTH_STEP = 15.0

class BiomeType(enum.Enum):
    SHALLOW_REEF = "shallow"     # 0 - 25m: Turquoise, sunbeams, clownfish, turtles
    TWILIGHT_KELP = "twilight"   # 25 - 65m: Deep blue, kelp, dolphins, mantas
    MIDNIGHT_ABYSS = "abyss"     # 65 - 100m: Dark indigo, glowing particles, anglerfish, whales

def get_biome(depth: float) -> BiomeType:
    if depth < 25.0:
        return BiomeType.SHALLOW_REEF
    elif depth < 65.0:
        return BiomeType.TWILIGHT_KELP
    else:
        return BiomeType.MIDNIGHT_ABYSS


@dataclass
class MarineEntity3D:
    """A 3D ocean entity located in camera-relative coordinates (x, y, z).

    x: [-1.0, 1.0] horizontal (negative = left, positive = right)
    y: [-0.6, 0.6] vertical (negative = up, positive = down)
    z: [0.1, 1.5] depth distance (1.5 = far in fog, 0.1 = close to viewport)
    """
    id: str
    kind: str           # "clownfish", "turtle", "dolphin", "manta", "angler", "whale", "bubble"
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
    OCTOPUS_HUG = "octopus_hug"  # Giant cuddly octopus hugs porthole glass
    SHARK_WAVE = "shark_wave"    # Curious smiling shark taps glass


@dataclass
class OrderState:
    order_id: str = "none"       # "ahead", "stop", "left", "right", "light", "sonar", "bubbles", "horn"
    prompt_text_key: str = ""
    cue_key: str = ""
    active: bool = False
    solved: bool = False
    timer: float = 0.0


@dataclass
class FactState:
    species: str = ""
    fact_index: int = 1
    text_key: str = ""
    cue_key: str = ""
    display_timer: float = 0.0


@dataclass
class EncounterState:
    active_type: EncounterType = EncounterType.NONE
    progress: float = 0.0        # 0.0 to 1.0 (fade-in / active)
    solved: bool = False
    solve_timer: float = 0.0
    reaction_cue: str = ""       # e.g. "giggle", "wave"


class SubmarineModel:
    """Pure domain model of the submarine exploration vehicle."""

    def __init__(self) -> None:
        # Submarine dynamics
        self.depth: float = 5.0          # Current depth in meters
        self.target_depth: float = 5.0
        self.heading: float = 0.0        # Horizontal turn offset [-1.0, 1.0]
        self.wheel_angle: float = 0.0   # Ship rudder wheel rotation in degrees
        self.speed: float = 0.5          # Forward engine speed [0.0, 1.0]

        # Cockpit instrument toggles
        self.lights_on: bool = False
        self.sonar_active: bool = False
        self.sonar_timer: float = 0.0
        self.radar_angle: float = 0.0    # 0 to 360 degrees for rotating sweep
        self.bubble_release_timer: float = 0.0

        # World entities
        self.entities: List[MarineEntity3D] = []
        self._spawn_ambient_entities()

        # Encounter & Order state
        self.encounter = EncounterState()
        self._encounter_cooldown: float = 12.0  # seconds until next possible creature encounter

        self.current_order = OrderState()
        self._order_cooldown: float = 4.0      # seconds until next navigation/action order

        # Active educational fact
        self.active_fact = FactState()

        # Discovered species tracking for milestone events
        self.discovered_species: set[str] = set()

    def _spawn_ambient_entities(self) -> None:
        self.entities.clear()
        # Spawn initial populated batch of marine creatures and floating bubbles
        for i in range(26):
            self._spawn_random_entity(initial_z=random.uniform(0.15, 1.4))

    def _spawn_random_entity(self, initial_z: Optional[float] = None) -> None:
        biome = get_biome(self.depth)
        z = initial_z if initial_z is not None else random.uniform(1.2, 1.5)

        # 75% spawn directly in porthole field of view; 25% spawn on flanks swimming inward
        if random.random() < 0.75:
            x = random.uniform(-0.45, 0.45)
            vx = random.uniform(-0.03, 0.03)
        else:
            side = -1.0 if random.random() < 0.5 else 1.0
            x = side * random.uniform(0.5, 0.85)
            # Swim toward viewport center
            vx = -side * random.uniform(0.04, 0.08)

        y = random.uniform(-0.4, 0.4)

        # Species matching current biome, including corals, kelp, krill
        if biome == BiomeType.SHALLOW_REEF:
            kinds = ["clownfish", "clownfish", "turtle", "coral", "bubble"]
        elif biome == BiomeType.TWILIGHT_KELP:
            kinds = ["dolphin", "manta", "kelp", "turtle", "bubble"]
        else:
            kinds = ["angler", "whale", "krill", "manta", "bubble"]

        kind = random.choice(kinds)
        size = 1.0
        if kind == "clownfish":
            size = 0.9
            y = random.uniform(-0.3, 0.3)
        elif kind == "turtle":
            size = 1.4
        elif kind == "dolphin":
            size = 1.8
        elif kind == "manta":
            size = 2.0
        elif kind == "angler":
            size = 1.2
        elif kind == "whale":
            size = 3.0
            # Keep whale slightly deeper so it glides past majestically
            z = max(0.4, z)
        elif kind == "coral":
            size = 1.6
            y = random.uniform(0.15, 0.45)  # sits near reef floor
            vx = 0.0
        elif kind == "kelp":
            size = 2.2
            y = random.uniform(0.05, 0.4)
            vx = 0.0
        elif kind == "krill":
            size = 1.5
        elif kind == "bubble":
            size = 0.4
            vx = random.uniform(-0.02, 0.02)

        vy = random.uniform(-0.015, 0.015)
        vz = -random.uniform(0.04, 0.1) if kind != "bubble" else -0.02

        ent = MarineEntity3D(
            id=f"ent_{random.randint(1000, 9999)}",
            kind=kind,
            x=x,
            y=y,
            z=z,
            vx=vx,
            vy=vy,
            vz=vz,
            size_base=size,
            phase=random.uniform(0, math.pi * 2)
        )
        self.entities.append(ent)

    def toggle_lights(self) -> bool:
        self.lights_on = not self.lights_on
        return self.lights_on

    def trigger_sonar(self) -> None:
        self.sonar_active = True
        self.sonar_timer = 2.5

    def trigger_bubbles(self) -> None:
        self.bubble_release_timer = 1.5
        # Spawn a cluster of close-range bubbles rushing up
        for _ in range(8):
            self.entities.append(MarineEntity3D(
                id=f"bubble_{random.randint(1000, 9999)}",
                kind="bubble",
                x=random.uniform(-0.4, 0.4),
                y=random.uniform(0.2, 0.6),
                z=random.uniform(0.1, 0.3),
                vx=random.uniform(-0.05, 0.05),
                vy=-random.uniform(0.2, 0.5),
                vz=0.0,
                size_base=random.uniform(0.3, 0.7)
            ))

    def trigger_horn(self) -> None:
        # Horn sends out an acoustic ripple that startles bubbles or resolves encounters
        pass

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

    def check_action(self, action_name: str) -> bool:
        """Check if child performed an action corresponding to the current Captain's order."""
        if not self.current_order.active or self.current_order.solved:
            return False

        target = self.current_order.order_id
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
        elif target == "horn" and (action_name in ("horn", "action")):
            is_match = True

        if is_match:
            self.current_order.solved = True
            self.current_order.timer = 2.0
            return True
        return False

    def trigger_species_fact(self, species: str) -> None:
        """Select an educational fact for the encountered species."""
        if species in ("bubble",):
            return
        # If species has multiple recorded facts, choose between them
        if species == "whale":
            idx = random.randint(1, 4)
        elif species == "turtle":
            idx = random.randint(1, 2)
        else:
            idx = 1
        self.active_fact.species = species
        self.active_fact.fact_index = idx
        self.active_fact.text_key = f"voice.fact.{species}.{idx}"
        self.active_fact.cue_key = f"voice.fact.{species}.{idx}"
        self.active_fact.display_timer = 9.0

    def resolve_encounter(self) -> bool:
        """Called when the child presses any resolution instrument during an encounter."""
        if self.encounter.active_type != EncounterType.NONE and not self.encounter.solved:
            self.encounter.solved = True
            self.encounter.solve_timer = 2.0
            return True
        return False

    def update(self, dt: float) -> Tuple[List[str], Optional[str]]:
        """Advance simulation time.

        Returns (newly_discovered_creatures, newly_completed_event).
        """
        discovered: List[str] = []
        completed_event: Optional[str] = None

        # Smooth depth transition
        depth_diff = self.target_depth - self.depth
        self.depth += depth_diff * min(1.0, dt * 1.5)

        # Smooth heading decay toward center when not actively steered
        self.heading *= max(0.0, 1.0 - dt * 0.8)

        # Smooth wheel rotation to reflect current rudder heading
        target_wheel = self.heading * 75.0
        self.wheel_angle += (target_wheel - self.wheel_angle) * min(1.0, dt * 5.0)

        # Radar sweep animation
        self.radar_angle = (self.radar_angle + dt * 180.0) % 360.0

        if self.sonar_timer > 0:
            self.sonar_timer -= dt
            if self.sonar_timer <= 0:
                self.sonar_active = False

        if self.bubble_release_timer > 0:
            self.bubble_release_timer -= dt

        # Update educational fact display timer
        if self.active_fact.display_timer > 0:
            self.active_fact.display_timer -= dt

        # Update Captain's orders state machine
        if self.current_order.active:
            if self.current_order.solved:
                self.current_order.timer -= dt
                if self.current_order.timer <= 0:
                    self.current_order.active = False
                    self.current_order.solved = False
                    self._order_cooldown = random.uniform(8.0, 14.0)
        else:
            # Only issue orders when no encounter is blocking
            if self.encounter.active_type == EncounterType.NONE:
                self._order_cooldown -= dt
                if self._order_cooldown <= 0:
                    # Smart order filtering: only suggest actions that make sense in current state
                    eligible_orders = []
                    if self.speed <= 0.3:
                        eligible_orders.append(("ahead", "order.ahead", "voice.order.ahead"))
                    if self.speed >= 0.4:
                        eligible_orders.append(("stop", "order.stop", "voice.order.stop"))
                    if self.heading >= -0.15:
                        eligible_orders.append(("left", "order.left", "voice.order.left"))
                    if self.heading <= 0.15:
                        eligible_orders.append(("right", "order.right", "voice.order.right"))
                    if not self.lights_on:
                        eligible_orders.append(("light", "order.light", "voice.btn.light"))
                    if not self.sonar_active:
                        eligible_orders.append(("sonar", "order.sonar", "voice.btn.sonar"))
                    eligible_orders.append(("bubbles", "order.bubbles", "voice.btn.bubbles"))
                    eligible_orders.append(("horn", "order.horn", "voice.btn.horn"))

                    chosen = random.choice(eligible_orders)
                    self.current_order.order_id = chosen[0]
                    self.current_order.prompt_text_key = chosen[1]
                    self.current_order.cue_key = chosen[2]
                    self.current_order.active = True
                    self.current_order.solved = False
                    self.current_order.timer = 0.0

        # Update entities in 3D space
        forward_advance = self.speed * dt * 0.4
        surviving_entities: List[MarineEntity3D] = []

        for ent in self.entities:
            ent.phase += dt * 3.0
            # Steer influence
            ent.x -= self.heading * dt * 0.5
            # Forward motion
            ent.z += ent.vz * forward_advance * 3.0 + (ent.vz * dt * 0.2)
            ent.x += ent.vx * dt
            ent.y += ent.vy * dt

            # Gentle bobbing
            ent.y += math.sin(ent.phase) * dt * 0.05

            # Creature discovery when close to porthole (z < 0.45 and in porthole view)
            if ent.z < 0.45 and not ent.discovered and ent.kind != "bubble" and abs(ent.x) < 0.45:
                ent.discovered = True
                self.trigger_species_fact(ent.kind)
                if ent.kind not in self.discovered_species:
                    self.discovered_species.add(ent.kind)
                    discovered.append(ent.kind)

            # Keep if still in front of sub (z > 0.05) and not too far behind
            if 0.05 < ent.z < 1.6 and abs(ent.x) < 1.5:
                surviving_entities.append(ent)

        self.entities = surviving_entities

        # Maintain population at 26 entities
        while len(self.entities) < 26:
            self._spawn_random_entity()

        # Update Encounter State Machine
        if self.encounter.active_type == EncounterType.NONE:
            self._encounter_cooldown -= dt
            if self._encounter_cooldown <= 0.0:
                # Trigger a friendly encounter
                self.encounter.active_type = random.choice([
                    EncounterType.OCTOPUS_HUG,
                    EncounterType.SHARK_WAVE
                ])
                self.encounter.progress = 0.0
                self.encounter.solved = False
                self.encounter.solve_timer = 0.0
        else:
            if not self.encounter.solved:
                self.encounter.progress = min(1.0, self.encounter.progress + dt * 1.5)
            else:
                self.encounter.solve_timer -= dt
                if self.encounter.solve_timer <= 0:
                    completed_event = "submarine.encounter_resolved"
                    self.encounter.active_type = EncounterType.NONE
                    self.encounter.solved = False
                    self._encounter_cooldown = random.uniform(15.0, 25.0)

        return discovered, completed_event
