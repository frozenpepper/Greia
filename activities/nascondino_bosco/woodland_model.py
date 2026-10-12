"""Domain model and state invariants for Nascondino nel Bosco."""

from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Final, Sequence

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
STORAGE_KEY: Final = "nascondino_bosco.progress.v2"


@dataclass(frozen=True, slots=True)
class AnimalDefinition:
    """Stable animal metadata and identification."""

    id: str
    name_key: str
    primary_color: tuple[int, int, int]
    secondary_color: tuple[int, int, int]
    clue_kind: str


ALL_ANIMALS: Final[tuple[AnimalDefinition, ...]] = (
    AnimalDefinition(
        id="fox",
        name_key="animal.fox",
        primary_color=(249, 115, 22),
        secondary_color=(255, 237, 213),
        clue_kind="fox_tail",
    ),
    AnimalDefinition(
        id="bunny",
        name_key="animal.bunny",
        primary_color=(255, 255, 255),
        secondary_color=(244, 114, 182),
        clue_kind="bunny_ears",
    ),
    AnimalDefinition(
        id="owl",
        name_key="animal.owl",
        primary_color=(161, 98, 7),
        secondary_color=(254, 240, 138),
        clue_kind="owl_eyes",
    ),
    AnimalDefinition(
        id="frog",
        name_key="animal.frog",
        primary_color=(34, 197, 94),
        secondary_color=(187, 247, 208),
        clue_kind="frog_eyes",
    ),
    AnimalDefinition(
        id="squirrel",
        name_key="animal.squirrel",
        primary_color=(217, 119, 6),
        secondary_color=(254, 215, 170),
        clue_kind="squirrel_tail",
    ),
    AnimalDefinition(
        id="hedgehog",
        name_key="animal.hedgehog",
        primary_color=(120, 53, 15),
        secondary_color=(254, 243, 199),
        clue_kind="hedgehog_nose",
    ),
)

ANIMALS_BY_ID: Final[dict[str, AnimalDefinition]] = {
    animal.id: animal for animal in ALL_ANIMALS
}


@dataclass(frozen=True, slots=True)
class HidingSpotDefinition:
    """A natural hiding spot physically grounded in the woodland scene."""

    spot_id: str
    kind: str
    cx: int
    cy: int
    width: int
    height: int

    @property
    def rect_tuple(self) -> tuple[int, int, int, int]:
        return (
            self.cx - self.width // 2,
            self.cy - self.height // 2,
            self.width,
            self.height,
        )

    def contains(self, px: int, py: int) -> bool:
        left = self.cx - self.width // 2
        top = self.cy - self.height // 2
        return left <= px <= left + self.width and top <= py <= top + self.height


# Grounded scene spot anchors matching forest_meadow_day_v1 geometry:
# 1. tree.hero.01 hollow at left trunk (x=146, y=398)
# 2. bush.round.01 on left ground (x=125, y=475)
# 3. log.fallen.01 in center meadow (x=485, y=485)
# 4. rock.cluster.large.01 on right ground (x=715, y=480)
# 5. bush.flowering.01 on right edge (x=890, y=470)
GROUNDED_SPOTS: Final[tuple[HidingSpotDefinition, ...]] = (
    HidingSpotDefinition(
        spot_id="hero_tree_hollow",
        kind="tree_hollow",
        cx=146,
        cy=398,
        width=70,
        height=80,
    ),
    HidingSpotDefinition(
        spot_id="left_round_bush",
        kind="round_bush",
        cx=125,
        cy=475,
        width=150,
        height=110,
    ),
    HidingSpotDefinition(
        spot_id="center_fallen_log",
        kind="fallen_log",
        cx=485,
        cy=485,
        width=180,
        height=100,
    ),
    HidingSpotDefinition(
        spot_id="right_rock_cluster",
        kind="rock_cluster",
        cx=715,
        cy=480,
        width=160,
        height=100,
    ),
    HidingSpotDefinition(
        spot_id="right_flowering_bush",
        kind="flowering_bush",
        cx=890,
        cy=470,
        width=150,
        height=110,
    ),
)


@dataclass(slots=True)
class LeapingAnimal:
    """Active leap presentation state when a spot is clicked."""

    animal_id: str
    cx: int
    cy: int
    is_target: bool
    t: float = 0.0
    duration: float = 0.95

    @property
    def is_finished(self) -> bool:
        return self.t >= self.duration


@dataclass(slots=True)
class Particle:
    """Lightweight sparkle particle during reward/reveal."""

    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    size: float
    life: float = 1.0

    def update(self, dt: float) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.life -= dt * 1.5
        return self.life > 0.0


@dataclass(slots=True)
class WoodlandGameState:
    """Pure domain state of a Nascondino session."""

    spots: tuple[HidingSpotDefinition, ...] = GROUNDED_SPOTS
    total_to_find: int = 4
    total_stars: int = 0
    hiding_map: dict[str, str] = field(default_factory=dict)
    target_animal_id: str = "fox"
    found_count: int = 0
    is_victory: bool = False
    found_spot_ids: set[str] = field(default_factory=set)
    leaping_animal: LeapingAnimal | None = None
    particles: list[Particle] = field(default_factory=list)

    def start_round(self) -> None:
        """Shuffle animals into spots and choose a new search target."""
        num_spots = len(self.spots)
        available = list(ALL_ANIMALS)
        chosen_animals = random.sample(available, min(num_spots, len(available)))
        self.hiding_map = {
            spot.spot_id: animal.id
            for spot, animal in zip(self.spots, chosen_animals)
        }
        self.target_animal_id = random.choice(list(self.hiding_map.values()))
        self.found_count = 0
        self.found_spot_ids.clear()
        self.is_victory = False
        self.leaping_animal = None
        self.particles.clear()

    def inspect_spot(self, spot_id: str) -> tuple[bool, str | None]:
        """Child clicked on a spot.

        Returns (is_target, animal_id). If target matched, advances count and
        selects next target animal or enters victory.
        """
        if self.is_victory:
            return False, None
        animal_id = self.hiding_map.get(spot_id)
        if animal_id is None or spot_id in self.found_spot_ids:
            return False, None

        spot = next((s for s in self.spots if s.spot_id == spot_id), None)
        if spot is not None:
            self.leaping_animal = LeapingAnimal(
                animal_id=animal_id,
                cx=spot.cx,
                cy=spot.cy,
                is_target=(animal_id == self.target_animal_id),
            )
            # Spawn bounded sparkles
            for _ in range(10):
                self.particles.append(
                    Particle(
                        x=float(spot.cx),
                        y=float(spot.cy),
                        vx=random.uniform(-3.5, 3.5),
                        vy=random.uniform(-5.0, -1.0),
                        color=(254, 240, 138),
                        size=random.uniform(5.0, 9.0),
                    )
                )

        is_target = animal_id == self.target_animal_id
        if is_target:
            self.found_spot_ids.add(spot_id)
            self.found_count += 1
            self.total_stars += 1
            if self.found_count >= self.total_to_find:
                self.is_victory = True
            else:
                remaining = [
                    a_id
                    for candidate_spot, a_id in self.hiding_map.items()
                    if candidate_spot not in self.found_spot_ids
                ]
                if remaining:
                    self.target_animal_id = random.choice(remaining)

        return is_target, animal_id

    def update_animations(self, dt: float) -> None:
        """Advance time-based presentation entities."""
        if self.leaping_animal is not None:
            self.leaping_animal.t += dt
            if self.leaping_animal.is_finished:
                self.leaping_animal = None

        if self.particles:
            self.particles = [p for p in self.particles if p.update(dt)]
