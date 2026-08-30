"""Shape Garden — pure domain state (no pygame).

Owns the garden's shape and particle invariants. No rendering, storage
or Greia event IO. The model enforces bounded collections and exposes
pure helpers for placement and particle integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field

if __package__:
    from .garden_content import MAX_PARTICLES, MAX_SHAPES
else:
    from garden_content import MAX_PARTICLES, MAX_SHAPES


@dataclass(slots=True)
class PlacedShape:
    x: int
    y: int
    size: int
    kind: int
    color_index: int
    spawn_time: float


@dataclass(slots=True)
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    birth_time: float
    lifetime: float


@dataclass(slots=True)
class GardenModel:
    """Deterministic garden state without display concerns.

    The app owns input mapping and rendering; this model owns the
    placed shapes, sparkle particles and companion reaction timing.
    All collections are explicitly bounded for the Acer-class floor.
    """

    shapes: list[PlacedShape] = field(default_factory=list)
    particles: list[Particle] = field(default_factory=list)
    reaction_until: float = 0.0

    # -- shape -------------------------------------------------------

    def add_shape(self, shape: PlacedShape) -> None:
        self.shapes.append(shape)
        if len(self.shapes) > MAX_SHAPES:
            # Keep most recent bounded window; mirrors original shapes[-120:].
            self.shapes = self.shapes[-MAX_SHAPES:]

    def active_shapes(self) -> list[PlacedShape]:
        return self.shapes[-MAX_SHAPES:]

    # -- particles ---------------------------------------------------

    def add_particle(self, particle: Particle) -> None:
        self.particles.append(particle)
        if len(self.particles) > MAX_PARTICLES:
            self.particles = self.particles[-MAX_PARTICLES:]

    def add_particles(self, particles: list[Particle]) -> None:
        for p in particles:
            self.add_particle(p)

    def update_particles(self, now: float, dt: float = 1.0 / 30.0) -> None:
        """Integrate particles and cull expired ones."""
        surviving: list[Particle] = []
        for pt in self.particles:
            p_age = now - pt.birth_time
            if p_age >= pt.lifetime:
                continue
            pt.x += pt.vx * dt
            pt.y += pt.vy * dt
            pt.vy += 45.0 * dt  # Gentle gravity
            surviving.append(pt)
        # Bounded to MAX_PARTICLES most recent.
        self.particles = surviving[-MAX_PARTICLES:]

    # -- companion ---------------------------------------------------

    def trigger_reaction(self, now: float, duration: float = 0.85) -> None:
        self.reaction_until = now + duration

    def is_reacting(self, now: float) -> bool:
        return now < self.reaction_until


__all__ = ["GardenModel", "Particle", "PlacedShape"]
