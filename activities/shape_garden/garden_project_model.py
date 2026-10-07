"""Pure persistent Shape Garden project model."""
from __future__ import annotations

from dataclasses import dataclass

if __package__:
    from .garden_content import COLORS, MAX_SHAPES, REFERENCE_WIDTH, SOIL_TOP
    from .garden_model import GardenModel, PlacedShape
else:  # pragma: no cover - direct script fallback
    from garden_content import COLORS, MAX_SHAPES, REFERENCE_WIDTH, SOIL_TOP
    from garden_model import GardenModel, PlacedShape


@dataclass(frozen=True, slots=True)
class GardenStamp:
    x: int
    y: int
    size: int
    kind: int
    color_index: int

    def __post_init__(self) -> None:
        if not (
            type(self.x) is int
            and type(self.y) is int
            and type(self.size) is int
            and type(self.kind) is int
            and type(self.color_index) is int
            and 0 <= self.x < REFERENCE_WIDTH
            and 0 <= self.y < SOIL_TOP
            and 8 <= self.size <= 96
            and 0 <= self.kind <= 2
            and 0 <= self.color_index < len(COLORS)
        ):
            raise ValueError("invalid garden stamp")

    @classmethod
    def from_shape(cls, shape: PlacedShape) -> "GardenStamp":
        return cls(shape.x, shape.y, shape.size, shape.kind, shape.color_index)

    @classmethod
    def from_raw(cls, raw: object) -> "GardenStamp":
        if not isinstance(raw, dict):
            raise ValueError("stamp must be an object")
        values = (
            raw.get("x"),
            raw.get("y"),
            raw.get("size"),
            raw.get("kind"),
            raw.get("color"),
        )
        if not all(type(value) is int for value in values):
            raise ValueError("stamp fields must be integers")
        x, y, size, kind, color = values
        return cls(x, y, size, kind, color)  # type: ignore[arg-type]

    def as_raw(self) -> dict[str, int]:
        return {
            "x": self.x,
            "y": self.y,
            "size": self.size,
            "kind": self.kind,
            "color": self.color_index,
        }


@dataclass(frozen=True, slots=True)
class GardenProject:
    stamps: tuple[GardenStamp, ...] = ()
    background_sha256: str | None = None

    def __post_init__(self) -> None:
        if len(self.stamps) > MAX_SHAPES:
            raise ValueError("too many garden stamps")
        digest = self.background_sha256
        if digest is not None and (
            len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)
        ):
            raise ValueError("invalid garden background digest")

    @classmethod
    def from_model(
        cls, model: GardenModel, background_sha256: str | None = None
    ) -> "GardenProject":
        return cls(
            tuple(GardenStamp.from_shape(shape) for shape in model.active_shapes()),
            background_sha256,
        )

    def restore_model(self, model: GardenModel, now: float) -> None:
        """Restore durable shapes fully grown; transient animation starts fresh."""
        model.shapes = [
            PlacedShape(
                x=stamp.x,
                y=stamp.y,
                size=stamp.size,
                kind=stamp.kind,
                color_index=stamp.color_index,
                spawn_time=now - 1.0,
            )
            for stamp in self.stamps
        ]
        model.particles.clear()
        model.reaction_until = 0.0


__all__ = ["GardenProject", "GardenStamp"]
