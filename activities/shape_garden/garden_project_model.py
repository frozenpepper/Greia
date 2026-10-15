"""Shape Garden save format (schema 2) and the v1 migration (no pygame).

A saved garden is one small JSON object in the Activity's key-value store::

    {"schema": 2, "backdrop": "meadow", "picture": null, "ghost": "house",
     "shapes": [["circle", "coral", 512, 300, 2, 0], ...]}

Shapes are stored by *name* (kind, colour), never by tray index, so a later
tray order can never repaint old gardens. Every field is validated on load;
one bad shape rejects the whole record rather than half-loading it.

``legacy_state`` converts the v1 tap-to-grow project (random circles,
squares and the pentagon that was labelled "triangle") into an editable
schema-2 garden without touching the v1 key.
"""

from __future__ import annotations

from dataclasses import dataclass

if __package__:
    from .garden_content import (
        BACKDROP_IDS,
        DEFAULT_BACKDROP,
        GHOST_IDS,
        LEGACY_COLOURS,
        LEGACY_KINDS,
        MAX_SHAPES,
        PICTURE_BACKDROP,
        SIZE_LEVELS,
    )
    from .garden_model import GardenState, PlacedShape, clamp_point
else:  # pragma: no cover - direct script fallback
    from garden_content import (
        BACKDROP_IDS,
        DEFAULT_BACKDROP,
        GHOST_IDS,
        LEGACY_COLOURS,
        LEGACY_KINDS,
        MAX_SHAPES,
        PICTURE_BACKDROP,
        SIZE_LEVELS,
    )
    from garden_model import GardenState, PlacedShape, clamp_point

SCHEMA = 2


@dataclass(frozen=True, slots=True)
class GardenProject:
    """One saved garden: the picture state plus the optional ghost hint."""

    state: GardenState
    ghost: str | None = None

    def as_raw(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "backdrop": self.state.backdrop,
            "picture": self.state.picture,
            "ghost": self.ghost,
            "shapes": [
                [s.kind, s.colour, s.x, s.y, s.size, s.turn] for s in self.state.shapes
            ],
        }

    @classmethod
    def from_raw(cls, raw: object) -> "GardenProject":
        if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
            raise ValueError("unsupported garden record")
        items = raw.get("shapes")
        if not isinstance(items, list) or len(items) > MAX_SHAPES:
            raise ValueError("invalid shape list")
        shapes = []
        for item in items:
            if not isinstance(item, list) or len(item) != 6:
                raise ValueError("invalid shape entry")
            kind, colour, x, y, size, turn = item
            if not (isinstance(kind, str) and isinstance(colour, str)):
                raise ValueError("invalid shape names")
            shapes.append(PlacedShape(kind, colour, x, y, size, turn))
        backdrop = raw.get("backdrop")
        picture = raw.get("picture")
        ghost = raw.get("ghost")
        if not isinstance(backdrop, str) or (backdrop not in BACKDROP_IDS and backdrop != PICTURE_BACKDROP):
            raise ValueError("invalid backdrop")
        if ghost is not None and ghost not in GHOST_IDS:
            ghost = None  # a retired hint must not hide the child's garden
        state = GardenState(tuple(shapes), backdrop, picture if picture is not None else None)
        return cls(state, ghost)


def legacy_state(raw: object) -> GardenState | None:
    """Map the v1 project (``schema_version`` 1) to a schema-2 state.

    v1 stamps were ``{x, y, size(radius 8-96), kind 0-2, color 0-4}`` on the
    same 1024x600 picture. The radius becomes the nearest size step (the new
    art fills ~88 % of its box). Returns ``None`` for an empty/unknown project.
    """

    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        return None
    items = raw.get("stamps", [])
    if not isinstance(items, list):
        return None
    shapes: list[PlacedShape] = []
    for item in items[:MAX_SHAPES]:
        if not isinstance(item, dict):
            continue
        values = (item.get("x"), item.get("y"), item.get("size"), item.get("kind"), item.get("color"))
        if not all(type(value) is int for value in values):
            continue
        x, y, radius, kind, colour = values  # type: ignore[misc]
        if not (0 <= kind < len(LEGACY_KINDS) and 0 <= colour < len(LEGACY_COLOURS)):
            continue
        box = 2 * max(1, radius) / 0.88
        size = min(range(len(SIZE_LEVELS)), key=lambda i: abs(SIZE_LEVELS[i] - box))
        px, py = clamp_point(x, y)
        shapes.append(PlacedShape(LEGACY_KINDS[kind], LEGACY_COLOURS[colour], px, py, size, 0))
    digest = raw.get("background_sha256")
    picture = digest if isinstance(digest, str) else None
    try:
        state = GardenState(
            tuple(shapes),
            PICTURE_BACKDROP if picture is not None else DEFAULT_BACKDROP,
            picture,
        )
    except ValueError:
        state = GardenState(tuple(shapes))
    return None if state.blank else state


__all__ = ["GardenProject", "SCHEMA", "legacy_state"]
