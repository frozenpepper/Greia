from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import copysign, hypot


class InteractionProfile(StrEnum):
    """Greia's small runtime-neutral Activity interaction vocabulary."""

    NAVIGATION = "navigation"
    POINTER = "pointer"
    DIRECTIONAL = "directional"
    GAME = "game"
    TEXT = "text"
    HYBRID = "hybrid"


SUPPORTED_INTERACTION_PROFILES = frozenset(item.value for item in InteractionProfile)


class InputSource(StrEnum):
    KEYBOARD = "keyboard"
    POINTER = "pointer"
    TOUCH = "touch"
    CONTROLLER = "controller"


class PhysicalControl(StrEnum):
    """Brand-neutral physical controls understood by standard Greia mappings."""

    KEY_UP = "key_up"
    KEY_DOWN = "key_down"
    KEY_LEFT = "key_left"
    KEY_RIGHT = "key_right"
    KEY_SPACE = "key_space"
    KEY_ENTER = "key_enter"
    KEY_ESCAPE = "key_escape"

    CONTROLLER_DPAD_UP = "controller_dpad_up"
    CONTROLLER_DPAD_DOWN = "controller_dpad_down"
    CONTROLLER_DPAD_LEFT = "controller_dpad_left"
    CONTROLLER_DPAD_RIGHT = "controller_dpad_right"
    CONTROLLER_FACE_SOUTH = "controller_face_south"
    CONTROLLER_FACE_EAST = "controller_face_east"
    CONTROLLER_FACE_WEST = "controller_face_west"
    CONTROLLER_FACE_NORTH = "controller_face_north"
    CONTROLLER_LEFT_SHOULDER = "controller_left_shoulder"
    CONTROLLER_RIGHT_SHOULDER = "controller_right_shoulder"
    CONTROLLER_START = "controller_start"
    CONTROLLER_BACK = "controller_back"
    CONTROLLER_GUIDE = "controller_guide"


class ControllerAxis(StrEnum):
    LEFT_X = "left_x"
    LEFT_Y = "left_y"
    RIGHT_X = "right_x"
    RIGHT_Y = "right_y"
    LEFT_TRIGGER = "left_trigger"
    RIGHT_TRIGGER = "right_trigger"


class SemanticAction(StrEnum):
    """Portable Activity intents produced by Greia's standard mappings."""

    NAV_UP = "nav_up"
    NAV_DOWN = "nav_down"
    NAV_LEFT = "nav_left"
    NAV_RIGHT = "nav_right"
    MOVE_UP = "move_up"
    MOVE_DOWN = "move_down"
    MOVE_LEFT = "move_left"
    MOVE_RIGHT = "move_right"
    ACTIVATE = "activate"
    CANCEL = "cancel"
    PRIMARY = "primary"
    SECONDARY = "secondary"


class InputEdge(StrEnum):
    PRESSED = "pressed"
    RELEASED = "released"


@dataclass(frozen=True, slots=True)
class SemanticInputEvent:
    action: SemanticAction
    edge: InputEdge
    source: InputSource


@dataclass(frozen=True, slots=True)
class MovementVector:
    """Normalized two-axis movement after Greia dead-zone processing."""

    x: float
    y: float

    @property
    def magnitude(self) -> float:
        return min(1.0, hypot(self.x, self.y))


@dataclass(frozen=True, slots=True)
class StandardInputPolicy:
    """Bounded platform defaults shared by controller-aware input adapters.

    These values are initial product defaults, not hardware facts. They are
    intentionally centralized so UX tuning does not fragment per Activity.
    """

    stick_dead_zone: float = 0.22
    navigation_threshold: float = 0.55
    pointer_speed_fraction_per_second: float = 1.10
    pointer_precision_floor: float = 0.35

    def __post_init__(self) -> None:
        if not 0.0 <= self.stick_dead_zone < 0.95:
            raise ValueError("stick_dead_zone must be in [0, 0.95)")
        if not self.stick_dead_zone < self.navigation_threshold <= 1.0:
            raise ValueError("navigation_threshold must exceed dead zone and be <= 1")
        if not 0.05 <= self.pointer_speed_fraction_per_second <= 4.0:
            raise ValueError("pointer speed fraction is outside the supported bound")
        if not 0.0 < self.pointer_precision_floor <= 1.0:
            raise ValueError("pointer precision floor must be in (0, 1]")


DEFAULT_INPUT_POLICY = StandardInputPolicy()


_PLATFORM_RESERVED_CONTROLS = frozenset({PhysicalControl.CONTROLLER_GUIDE})


_NAVIGATION_MAP = {
    PhysicalControl.KEY_UP: SemanticAction.NAV_UP,
    PhysicalControl.KEY_DOWN: SemanticAction.NAV_DOWN,
    PhysicalControl.KEY_LEFT: SemanticAction.NAV_LEFT,
    PhysicalControl.KEY_RIGHT: SemanticAction.NAV_RIGHT,
    PhysicalControl.CONTROLLER_DPAD_UP: SemanticAction.NAV_UP,
    PhysicalControl.CONTROLLER_DPAD_DOWN: SemanticAction.NAV_DOWN,
    PhysicalControl.CONTROLLER_DPAD_LEFT: SemanticAction.NAV_LEFT,
    PhysicalControl.CONTROLLER_DPAD_RIGHT: SemanticAction.NAV_RIGHT,
    PhysicalControl.KEY_SPACE: SemanticAction.ACTIVATE,
    PhysicalControl.KEY_ENTER: SemanticAction.ACTIVATE,
    PhysicalControl.CONTROLLER_FACE_SOUTH: SemanticAction.ACTIVATE,
    PhysicalControl.KEY_ESCAPE: SemanticAction.CANCEL,
    PhysicalControl.CONTROLLER_FACE_EAST: SemanticAction.CANCEL,
}

_DIRECTIONAL_MAP = {
    PhysicalControl.KEY_UP: SemanticAction.MOVE_UP,
    PhysicalControl.KEY_DOWN: SemanticAction.MOVE_DOWN,
    PhysicalControl.KEY_LEFT: SemanticAction.MOVE_LEFT,
    PhysicalControl.KEY_RIGHT: SemanticAction.MOVE_RIGHT,
    PhysicalControl.CONTROLLER_DPAD_UP: SemanticAction.MOVE_UP,
    PhysicalControl.CONTROLLER_DPAD_DOWN: SemanticAction.MOVE_DOWN,
    PhysicalControl.CONTROLLER_DPAD_LEFT: SemanticAction.MOVE_LEFT,
    PhysicalControl.CONTROLLER_DPAD_RIGHT: SemanticAction.MOVE_RIGHT,
    PhysicalControl.KEY_SPACE: SemanticAction.PRIMARY,
    PhysicalControl.CONTROLLER_FACE_SOUTH: SemanticAction.PRIMARY,
    PhysicalControl.KEY_ENTER: SemanticAction.ACTIVATE,
    PhysicalControl.KEY_ESCAPE: SemanticAction.CANCEL,
    PhysicalControl.CONTROLLER_FACE_EAST: SemanticAction.CANCEL,
}

_GAME_MAP = {
    **_DIRECTIONAL_MAP,
    PhysicalControl.CONTROLLER_FACE_EAST: SemanticAction.SECONDARY,
    PhysicalControl.CONTROLLER_BACK: SemanticAction.CANCEL,
}

_POINTER_MAP = {
    PhysicalControl.CONTROLLER_FACE_SOUTH: SemanticAction.PRIMARY,
    PhysicalControl.CONTROLLER_FACE_EAST: SemanticAction.CANCEL,
}

_PROFILE_MAPS = {
    InteractionProfile.NAVIGATION: _NAVIGATION_MAP,
    InteractionProfile.POINTER: _POINTER_MAP,
    InteractionProfile.DIRECTIONAL: _DIRECTIONAL_MAP,
    InteractionProfile.GAME: _GAME_MAP,
    # Text and Hybrid deliberately do not steal keyboard keys. Text Activities
    # own textual/caret semantics; Hybrid Activities compose explicit contexts.
    InteractionProfile.TEXT: {},
    InteractionProfile.HYBRID: {},
}


class StandardInputMapper:
    """Map normalized physical controls onto Greia's learned input vocabulary.

    This class is deliberately independent of Pygame, SDL, Web APIs and Linux
    device nodes. Runtime/backend adapters translate their native events into
    PhysicalControl values, then share these rules.
    """

    def __init__(self, profile: InteractionProfile | str):
        self.profile = parse_interaction_profile(profile)

    def digital(
        self,
        control: PhysicalControl,
        edge: InputEdge,
        source: InputSource,
    ) -> SemanticInputEvent | None:
        if control in _PLATFORM_RESERVED_CONTROLS:
            return None
        action = _PROFILE_MAPS[self.profile].get(control)
        if action is None:
            return None
        return SemanticInputEvent(action, edge, source)


class VirtualPointer:
    """Greia-owned controller cursor motion for pointer-style Activities.

    The cursor uses normalized stick input and screen-relative speed so one
    centrally tuned policy behaves similarly across 1024x600 and larger modes.
    It does not emulate a Linux mouse device.
    """

    def __init__(
        self,
        width: int,
        height: int,
        *,
        x: float | None = None,
        y: float | None = None,
        policy: StandardInputPolicy = DEFAULT_INPUT_POLICY,
    ) -> None:
        if width < 1 or height < 1:
            raise ValueError("virtual pointer surface must be positive")
        self._width = int(width)
        self._height = int(height)
        self._policy = policy
        self._x = float((width - 1) / 2 if x is None else x)
        self._y = float((height - 1) / 2 if y is None else y)
        self._clamp()

    @property
    def position(self) -> tuple[int, int]:
        return round(self._x), round(self._y)

    def move(self, raw_x: float, raw_y: float, elapsed_seconds: float) -> tuple[int, int]:
        if elapsed_seconds < 0.0 or elapsed_seconds > 1.0:
            raise ValueError("elapsed_seconds must be in [0, 1]")
        vector = normalize_stick(raw_x, raw_y, self._policy.stick_dead_zone)
        if vector.magnitude == 0.0 or elapsed_seconds == 0.0:
            return self.position
        # Preserve fine low-stick motion while still allowing quick traversal.
        response = self._policy.pointer_precision_floor + (
            1.0 - self._policy.pointer_precision_floor
        ) * vector.magnitude
        pixels_per_second = (
            min(self._width, self._height)
            * self._policy.pointer_speed_fraction_per_second
            * response
        )
        self._x += vector.x * pixels_per_second * elapsed_seconds
        self._y += vector.y * pixels_per_second * elapsed_seconds
        self._clamp()
        return self.position

    def set_position(self, x: float, y: float) -> tuple[int, int]:
        self._x = float(x)
        self._y = float(y)
        self._clamp()
        return self.position

    def _clamp(self) -> None:
        self._x = min(float(self._width - 1), max(0.0, self._x))
        self._y = min(float(self._height - 1), max(0.0, self._y))


def parse_interaction_profile(value: InteractionProfile | str) -> InteractionProfile:
    if isinstance(value, InteractionProfile):
        return value
    if not isinstance(value, str):
        raise TypeError("interaction profile must be text")
    try:
        return InteractionProfile(value.strip().casefold())
    except ValueError as exc:
        raise ValueError(f"unsupported interaction profile: {value!r}") from exc


def is_platform_reserved(control: PhysicalControl) -> bool:
    """Return whether an input control is withheld from Activity mappings."""

    return control in _PLATFORM_RESERVED_CONTROLS


def normalize_stick(
    raw_x: float,
    raw_y: float,
    dead_zone: float = DEFAULT_INPUT_POLICY.stick_dead_zone,
) -> MovementVector:
    """Normalize a controller stick to a circular dead zone and unit magnitude."""

    x = _axis(raw_x)
    y = _axis(raw_y)
    if not 0.0 <= dead_zone < 0.95:
        raise ValueError("dead_zone must be in [0, 0.95)")
    magnitude = hypot(x, y)
    if magnitude <= dead_zone:
        return MovementVector(0.0, 0.0)
    unit_x = x / magnitude
    unit_y = y / magnitude
    scaled = min(1.0, (magnitude - dead_zone) / (1.0 - dead_zone))
    return MovementVector(unit_x * scaled, unit_y * scaled)


def navigation_direction(
    vector: MovementVector,
    threshold: float = DEFAULT_INPUT_POLICY.navigation_threshold,
) -> SemanticAction | None:
    """Convert one analog stick direction into deterministic menu navigation."""

    if not 0.0 < threshold <= 1.0:
        raise ValueError("threshold must be in (0, 1]")
    if max(abs(vector.x), abs(vector.y)) < threshold:
        return None
    if abs(vector.x) > abs(vector.y):
        return SemanticAction.NAV_RIGHT if vector.x > 0 else SemanticAction.NAV_LEFT
    return SemanticAction.NAV_DOWN if vector.y > 0 else SemanticAction.NAV_UP


def _axis(value: float) -> float:
    number = float(value)
    if number == 0.0:
        return 0.0
    return copysign(min(1.0, abs(number)), number)
