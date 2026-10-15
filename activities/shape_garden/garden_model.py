"""Shape Garden — pure composition model (no pygame).

``PlacedShape`` and ``GardenState`` are immutable values; ``GardenEditor``
owns the one garden being edited, the current selection and a bounded undo
history of whole states. Because states are immutable tuples, an undo step
is a cheap reference, never a deep copy.

Ghost pictures are derived, never stored as progress: a slot counts as
filled while some shape sits exactly on it, so undo, moves and deletes keep
"filled" honest without extra bookkeeping.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, replace
import math

if __package__:
    from .garden_content import (
        BACKDROP_IDS,
        COLOUR_IDS,
        DEFAULT_BACKDROP,
        DEFAULT_SIZE,
        GARDEN_HEIGHT,
        GARDEN_WIDTH,
        MAX_SHAPES,
        MAX_UNDO,
        PICTURE_BACKDROP,
        SHAPE_KINDS,
        SIZE_LEVELS,
        TURN_STEPS,
        GhostPicture,
        GhostSlot,
        ghost_picture,
    )
else:  # pragma: no cover - direct script fallback
    from garden_content import (
        BACKDROP_IDS,
        COLOUR_IDS,
        DEFAULT_BACKDROP,
        DEFAULT_SIZE,
        GARDEN_HEIGHT,
        GARDEN_WIDTH,
        MAX_SHAPES,
        MAX_UNDO,
        PICTURE_BACKDROP,
        SHAPE_KINDS,
        SIZE_LEVELS,
        TURN_STEPS,
        GhostPicture,
        GhostSlot,
        ghost_picture,
    )


@dataclass(frozen=True, slots=True)
class PlacedShape:
    """One shape in the garden: kind, colour, box centre, size step and turn."""

    kind: str
    colour: str
    x: int
    y: int
    size: int = DEFAULT_SIZE
    turn: int = 0

    def __post_init__(self) -> None:
        if (
            self.kind not in SHAPE_KINDS
            or self.colour not in COLOUR_IDS
            or type(self.x) is not int
            or type(self.y) is not int
            or type(self.size) is not int
            or type(self.turn) is not int
            or not (0 <= self.x <= GARDEN_WIDTH)
            or not (0 <= self.y <= GARDEN_HEIGHT)
            or not (0 <= self.size < len(SIZE_LEVELS))
            or not (0 <= self.turn < TURN_STEPS)
        ):
            raise ValueError("invalid placed shape")

    @property
    def box(self) -> int:
        """Side of the square art box in garden pixels."""
        return SIZE_LEVELS[self.size]

    def contains(self, point: tuple[float, float]) -> bool:
        """Forgiving round hit area (the renderer refines it per pixel)."""
        radius = self.box * 0.44
        return (point[0] - self.x) ** 2 + (point[1] - self.y) ** 2 <= radius * radius

    def matches(self, slot: GhostSlot) -> bool:
        return (
            self.kind == slot.kind
            and self.size == slot.size
            and self.turn == slot.turn
            and abs(self.x - slot.x) <= 2
            and abs(self.y - slot.y) <= 2
        )


@dataclass(frozen=True, slots=True)
class GardenState:
    """Everything that makes one garden picture (what undo restores)."""

    shapes: tuple[PlacedShape, ...] = ()
    backdrop: str = DEFAULT_BACKDROP
    picture: str | None = None  # sha256 of an imported backdrop PNG

    def __post_init__(self) -> None:
        if len(self.shapes) > MAX_SHAPES:
            raise ValueError("too many shapes")
        if self.backdrop == PICTURE_BACKDROP:
            if not _is_digest(self.picture):
                raise ValueError("picture backdrop needs a digest")
        elif self.backdrop not in BACKDROP_IDS:
            raise ValueError("unknown backdrop")
        elif self.picture is not None and not _is_digest(self.picture):
            raise ValueError("invalid picture digest")

    @property
    def blank(self) -> bool:
        """Nothing the child made: no shape and no picture of their own."""
        return not self.shapes and self.picture is None


def clamp_point(x: float, y: float) -> tuple[int, int]:
    return (
        int(round(min(GARDEN_WIDTH, max(0.0, x)))),
        int(round(min(GARDEN_HEIGHT, max(0.0, y)))),
    )


def snap_slot(shape: PlacedShape, ghost: GhostPicture | None, shapes: Iterable[PlacedShape] = ()) -> GhostSlot | None:
    """Return the free ghost slot ``shape`` was dropped close to, if any.

    Matching is deliberately generous for small hands: same kind and the box
    centre within about half a slot. Size and turn do not have to match; the
    snap adopts the slot's, which is the gentle "it fits!" moment.
    """

    if ghost is None:
        return None
    others = tuple(shapes)
    best: tuple[float, GhostSlot] | None = None
    for slot in ghost.slots:
        if slot.kind != shape.kind or any(other.matches(slot) for other in others):
            continue
        reach = max(44.0, SIZE_LEVELS[slot.size] * 0.5)
        distance = math.hypot(shape.x - slot.x, shape.y - slot.y)
        if distance <= reach and (best is None or distance < best[0]):
            best = (distance, slot)
    return best[1] if best is not None else None


@dataclass(slots=True)
class GardenEditor:
    """Edit one garden: selection, bounded undo and every child action.

    Each public action records one undo step when it changes the state and
    returns whether it did. ``revision`` increases on every change so the
    renderer and autosave can react without diffing.
    """

    state: GardenState = field(default_factory=GardenState)
    ghost: str | None = None
    selected: int | None = None
    revision: int = 0
    _history: list[GardenState] = field(default_factory=list)
    _drag_origin: GardenState | None = None

    # -- queries -------------------------------------------------------------

    @property
    def shapes(self) -> tuple[PlacedShape, ...]:
        return self.state.shapes

    @property
    def full(self) -> bool:
        return len(self.state.shapes) >= MAX_SHAPES

    @property
    def can_undo(self) -> bool:
        return bool(self._history)

    @property
    def selected_shape(self) -> PlacedShape | None:
        if self.selected is None or not (0 <= self.selected < len(self.state.shapes)):
            return None
        return self.state.shapes[self.selected]

    @property
    def ghost_picture(self) -> GhostPicture | None:
        return ghost_picture(self.ghost)

    def filled_slots(self) -> tuple[bool, ...]:
        picture = self.ghost_picture
        if picture is None:
            return ()
        return tuple(any(shape.matches(slot) for shape in self.state.shapes) for slot in picture.slots)

    def ghost_complete(self) -> bool:
        filled = self.filled_slots()
        return bool(filled) and all(filled)

    def next_free_slot(self) -> GhostSlot | None:
        picture = self.ghost_picture
        if picture is None:
            return None
        for slot, filled in zip(picture.slots, self.filled_slots()):
            if not filled:
                return slot
        return None

    def shape_at(self, point: tuple[float, float]) -> int | None:
        """Topmost shape whose forgiving hit area contains ``point``."""
        for index in range(len(self.state.shapes) - 1, -1, -1):
            if self.state.shapes[index].contains(point):
                return index
        return None

    # -- lifecycle -----------------------------------------------------------

    def load(self, state: GardenState, ghost: str | None = None) -> None:
        """Open a garden: fresh history, nothing selected."""
        self.state = state
        self.ghost = ghost if ghost_picture(ghost) is not None else None
        self.selected = None
        self._history.clear()
        self._drag_origin = None
        self.revision += 1

    def _commit(self, new_state: GardenState, *, record: bool = True) -> bool:
        if new_state == self.state:
            return False
        if record:
            self._history.append(self.state)
            if len(self._history) > MAX_UNDO:
                del self._history[0]
        self.state = new_state
        self.revision += 1
        return True

    def _replace_shape(self, index: int, shape: PlacedShape, *, record: bool = True) -> bool:
        shapes = list(self.state.shapes)
        shapes[index] = shape
        return self._commit(replace(self.state, shapes=tuple(shapes)), record=record)

    # -- actions -------------------------------------------------------------

    def plant(self, kind: str, colour: str, point: tuple[float, float], size: int = DEFAULT_SIZE) -> GhostSlot | None | bool:
        """Add a shape on top and select it.

        Returns the ghost slot it snapped into, ``True`` for a free planting,
        or ``False`` when the garden is full (nothing is ever evicted).
        """

        if self.full:
            return False
        x, y = clamp_point(*point)
        shape = PlacedShape(kind, colour, x, y, size, 0)
        slot = snap_slot(shape, self.ghost_picture, self.state.shapes)
        if slot is not None:
            shape = replace(shape, x=slot.x, y=slot.y, size=slot.size, turn=slot.turn)
        self._commit(replace(self.state, shapes=(*self.state.shapes, shape)))
        self.selected = len(self.state.shapes) - 1
        if slot is not None:
            self._layer_ghost()
        return slot if slot is not None else True

    def select(self, index: int | None) -> None:
        if index is not None and not (0 <= index < len(self.state.shapes)):
            index = None
        if index != self.selected:
            self.selected = index
            self.revision += 1

    def begin_drag(self, index: int) -> None:
        """Lift a shape to the top for dragging; the whole drag is one undo step."""
        if not (0 <= index < len(self.state.shapes)):
            return
        self._drag_origin = self.state
        shapes = list(self.state.shapes)
        shape = shapes.pop(index)
        shapes.append(shape)
        self._commit(replace(self.state, shapes=tuple(shapes)), record=False)
        self.selected = len(shapes) - 1

    def drag_to(self, point: tuple[float, float]) -> None:
        shape = self.selected_shape
        if shape is None or self._drag_origin is None:
            return
        x, y = clamp_point(*point)
        self._replace_shape(self.selected, replace(shape, x=x, y=y), record=False)  # type: ignore[arg-type]

    def end_drag(self) -> GhostSlot | None:
        """Drop the dragged shape (snapping into a near free slot)."""
        origin, self._drag_origin = self._drag_origin, None
        shape = self.selected_shape
        if origin is None or shape is None:
            return None
        others = tuple(s for i, s in enumerate(self.state.shapes) if i != self.selected)
        slot = snap_slot(shape, self.ghost_picture, others)
        if slot is not None:
            self._replace_shape(
                self.selected,  # type: ignore[arg-type]
                replace(shape, x=slot.x, y=slot.y, size=slot.size, turn=slot.turn),
                record=False,
            )
            self._layer_ghost()
        if self.state != origin:
            self._history.append(origin)
            if len(self._history) > MAX_UNDO:
                del self._history[0]
            self.revision += 1
        return slot

    def cancel_drag_into_bin(self) -> bool:
        """The dragged shape was dropped on the bin: remove it (one undo step)."""
        origin, self._drag_origin = self._drag_origin, None
        if origin is None or self.selected is None:
            return False
        shapes = list(self.state.shapes)
        del shapes[self.selected]
        self.state = replace(self.state, shapes=tuple(shapes))
        self._history.append(origin)
        if len(self._history) > MAX_UNDO:
            del self._history[0]
        self.selected = None
        self.revision += 1
        return True

    def _layer_ghost(self) -> None:
        """Stack shapes sitting in ghost slots in the picture's slot order.

        A roof planted before the wall, or a door before the house, would
        otherwise vanish behind the later piece. Only snapped shapes swap
        places among themselves; every free shape keeps its layer, and the
        reorder belongs to the same undo step as the snap.
        """
        picture = self.ghost_picture
        if picture is None:
            return

        def slot_index(shape: PlacedShape) -> int | None:
            for index, slot in enumerate(picture.slots):
                if shape.matches(slot):
                    return index
            return None

        shapes = list(self.state.shapes)
        positions = [i for i, shape in enumerate(shapes) if slot_index(shape) is not None]
        if len(positions) < 2:
            return
        chosen = self.selected_shape
        ordered = sorted((shapes[i] for i in positions), key=lambda shape: slot_index(shape) or 0)
        for position, shape in zip(positions, ordered):
            shapes[position] = shape
        if tuple(shapes) == self.state.shapes:
            return
        self.state = replace(self.state, shapes=tuple(shapes))
        self.revision += 1
        if chosen is not None:
            self.selected = next(i for i, shape in enumerate(shapes) if shape is chosen)

    @property
    def dragging(self) -> bool:
        return self._drag_origin is not None

    def resize(self, step: int) -> bool:
        shape = self.selected_shape
        if shape is None:
            return False
        size = max(0, min(len(SIZE_LEVELS) - 1, shape.size + step))
        return self._replace_shape(self.selected, replace(shape, size=size))  # type: ignore[arg-type]

    def rotate(self) -> bool:
        shape = self.selected_shape
        if shape is None:
            return False
        return self._replace_shape(self.selected, replace(shape, turn=(shape.turn + 1) % TURN_STEPS))  # type: ignore[arg-type]

    def recolour(self, colour: str) -> bool:
        shape = self.selected_shape
        if shape is None or colour not in COLOUR_IDS:
            return False
        return self._replace_shape(self.selected, replace(shape, colour=colour))  # type: ignore[arg-type]

    def send_back(self) -> bool:
        """Put the selected shape behind all the others."""
        if self.selected is None or self.selected_shape is None or self.selected == 0:
            return False
        shapes = list(self.state.shapes)
        shape = shapes.pop(self.selected)
        shapes.insert(0, shape)
        changed = self._commit(replace(self.state, shapes=tuple(shapes)))
        self.selected = 0
        return changed

    def remove_selected(self) -> bool:
        if self.selected is None or self.selected_shape is None:
            return False
        shapes = list(self.state.shapes)
        del shapes[self.selected]
        self.selected = None
        return self._commit(replace(self.state, shapes=tuple(shapes)))

    def set_backdrop(self, backdrop: str, picture: str | None = None) -> bool:
        if backdrop == PICTURE_BACKDROP:
            new_state = replace(self.state, backdrop=backdrop, picture=picture)
        else:
            # Leaving the child's picture keeps it remembered until another
            # picture replaces it, so the backdrop sheet can offer it again.
            new_state = replace(self.state, backdrop=backdrop)
        return self._commit(new_state)

    def set_ghost(self, ghost: str | None) -> bool:
        ghost = ghost if ghost_picture(ghost) is not None else None
        if ghost == self.ghost:
            return False
        self.ghost = ghost
        self.revision += 1
        return True

    def undo(self) -> bool:
        if self._drag_origin is not None:
            # Undo during a carry puts the shape back where it was picked up.
            self.state, self._drag_origin = self._drag_origin, None
            self.selected = None
            self.revision += 1
            return True
        if not self._history:
            return False
        self.state = self._history.pop()
        if self.selected is not None and self.selected >= len(self.state.shapes):
            self.selected = None
        self.revision += 1
        return True

    def free_spot(self) -> tuple[int, int]:
        """Where a tapped (not dragged) shape lands: near the centre, fanning
        out so several taps never pile exactly on top of each other."""
        count = len(self.state.shapes)
        cx, cy = GARDEN_WIDTH // 2, GARDEN_HEIGHT // 2 + 20
        if count == 0:
            return cx, cy
        angle = count * 2.39996  # golden angle
        radius = 70 + 22 * (count % 9)
        return clamp_point(cx + math.cos(angle) * radius, cy + math.sin(angle) * radius * 0.6)


def _is_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


__all__ = [
    "GardenEditor",
    "GardenState",
    "PlacedShape",
    "clamp_point",
    "snap_slot",
]
