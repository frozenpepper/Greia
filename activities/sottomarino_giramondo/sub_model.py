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

        # Encounter state
        self.encounter = EncounterState()
        self._encounter_cooldown: float = 12.0  # seconds until next possible encounter

        # Discovered species tracking for milestone events
        self.discovered_species: set[str] = set()

    def _spawn_ambient_entities(self) -> None:
        self.entities.clear()
        # Spawn initial batch of marine creatures and floating particles
        for i in range(12):
            self._spawn_random_entity(initial_z=random.uniform(0.2, 1.4))

    def _spawn_random_entity(self, initial_z: Optional[float] = None) -> None:
        biome = get_biome(self.depth)
        z = initial_z if initial_z is not None else random.uniform(1.2, 1.5)
        x = random.uniform(-1.2, 1.2)
        y = random.uniform(-0.5, 0.5)

        # Species matching current biome
        if biome == BiomeType.SHALLOW_REEF:
            kinds = ["clownfish", "turtle", "bubble", "bubble"]
        elif biome == BiomeType.TWILIGHT_KELP:
            kinds = ["dolphin", "manta", "turtle", "bubble"]
        else:
            kinds = ["angler", "whale", "manta", "bubble"]

        kind = random.choice(kinds)
        size = 1.0
        if kind == "clownfish":
            size = 0.8
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
        elif kind == "bubble":
            size = 0.4

        vx = random.uniform(-0.02, 0.02)
        vy = random.uniform(-0.01, 0.01)
        vz = -random.uniform(0.04, 0.1)

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

    def set_speed(self, speed: float) -> None:
        self.speed = max(0.0, min(1.0, speed))

    def resolve_encounter(self) -> bool:
        """Called when the child presses the active action / siren button during an encounter."""
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

        # Radar sweep animation
        self.radar_angle = (self.radar_angle + dt * 180.0) % 360.0

        if self.sonar_timer > 0:
            self.sonar_timer -= dt
            if self.sonar_timer <= 0:
                self.sonar_active = False

        if self.bubble_release_timer > 0:
            self.bubble_release_timer -= dt

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

            # Creature discovery when close to porthole (z < 0.4) and not yet discovered
            if ent.z < 0.45 and not ent.discovered and ent.kind != "bubble":
                ent.discovered = True
                if ent.kind not in self.discovered_species:
                    self.discovered_species.add(ent.kind)
                    discovered.append(ent.kind)

            # Keep if still in front of sub (z > 0.05) and not too far behind
            if 0.05 < ent.z < 1.6 and abs(ent.x) < 2.0:
                surviving_entities.append(ent)

        self.entities = surviving_entities

        # Maintain population
        while len(self.entities) < 14:
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
