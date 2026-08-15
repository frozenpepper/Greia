from __future__ import annotations

from dataclasses import dataclass

import pygame

from .input_core import (
    ControllerAxis,
    InputEdge,
    InputSource,
    InteractionProfile,
    PhysicalControl,
    SemanticInputEvent,
    StandardInputMapper,
)

try:
    from pygame._sdl2 import controller as sdl_controller
except ImportError:  # pragma: no cover - depends on the curated pygame build
    sdl_controller = None


MAX_OPEN_CONTROLLERS = 4
MAX_CONTROLLER_SCAN = 16


def _controller_constant(name: str, fallback: int) -> int:
    """Return a stable SDL2 controller enum across Pygame packaging variants.

    Some distro Pygame builds expose pygame._sdl2.controller and its Controller
    API without re-exporting SDL's CONTROLLER_BUTTON_* / CONTROLLER_AXIS_*
    integer constants. SDL2 defines these enums with stable numeric values, so
    Greia keeps those values as compatibility fallbacks instead of making the
    whole input module unimportable on such builds.
    """

    if sdl_controller is None:
        return fallback
    return int(getattr(sdl_controller, name, fallback))


CONTROLLER_BUTTON_A = _controller_constant("CONTROLLER_BUTTON_A", 0)
CONTROLLER_BUTTON_B = _controller_constant("CONTROLLER_BUTTON_B", 1)
CONTROLLER_BUTTON_X = _controller_constant("CONTROLLER_BUTTON_X", 2)
CONTROLLER_BUTTON_Y = _controller_constant("CONTROLLER_BUTTON_Y", 3)
CONTROLLER_BUTTON_BACK = _controller_constant("CONTROLLER_BUTTON_BACK", 4)
CONTROLLER_BUTTON_GUIDE = _controller_constant("CONTROLLER_BUTTON_GUIDE", 5)
CONTROLLER_BUTTON_START = _controller_constant("CONTROLLER_BUTTON_START", 6)
CONTROLLER_BUTTON_LEFTSHOULDER = _controller_constant(
    "CONTROLLER_BUTTON_LEFTSHOULDER", 9
)
CONTROLLER_BUTTON_RIGHTSHOULDER = _controller_constant(
    "CONTROLLER_BUTTON_RIGHTSHOULDER", 10
)
CONTROLLER_BUTTON_DPAD_UP = _controller_constant("CONTROLLER_BUTTON_DPAD_UP", 11)
CONTROLLER_BUTTON_DPAD_DOWN = _controller_constant("CONTROLLER_BUTTON_DPAD_DOWN", 12)
CONTROLLER_BUTTON_DPAD_LEFT = _controller_constant("CONTROLLER_BUTTON_DPAD_LEFT", 13)
CONTROLLER_BUTTON_DPAD_RIGHT = _controller_constant("CONTROLLER_BUTTON_DPAD_RIGHT", 14)

CONTROLLER_AXIS_LEFTX = _controller_constant("CONTROLLER_AXIS_LEFTX", 0)
CONTROLLER_AXIS_LEFTY = _controller_constant("CONTROLLER_AXIS_LEFTY", 1)
CONTROLLER_AXIS_RIGHTX = _controller_constant("CONTROLLER_AXIS_RIGHTX", 2)
CONTROLLER_AXIS_RIGHTY = _controller_constant("CONTROLLER_AXIS_RIGHTY", 3)
CONTROLLER_AXIS_TRIGGERLEFT = _controller_constant("CONTROLLER_AXIS_TRIGGERLEFT", 4)
CONTROLLER_AXIS_TRIGGERRIGHT = _controller_constant("CONTROLLER_AXIS_TRIGGERRIGHT", 5)


@dataclass(frozen=True, slots=True)
class ControllerAxisEvent:
    """One SDL-controller axis update translated into Greia vocabulary."""

    axis: ControllerAxis
    value: float


_KEY_CONTROLS = {
    pygame.K_UP: PhysicalControl.KEY_UP,
    pygame.K_DOWN: PhysicalControl.KEY_DOWN,
    pygame.K_LEFT: PhysicalControl.KEY_LEFT,
    pygame.K_RIGHT: PhysicalControl.KEY_RIGHT,
    pygame.K_SPACE: PhysicalControl.KEY_SPACE,
    pygame.K_RETURN: PhysicalControl.KEY_ENTER,
    pygame.K_ESCAPE: PhysicalControl.KEY_ESCAPE,
}


def _controller_button_map() -> dict[int, PhysicalControl]:
    if sdl_controller is None:
        return {}
    return {
        CONTROLLER_BUTTON_DPAD_UP: PhysicalControl.CONTROLLER_DPAD_UP,
        CONTROLLER_BUTTON_DPAD_DOWN: PhysicalControl.CONTROLLER_DPAD_DOWN,
        CONTROLLER_BUTTON_DPAD_LEFT: PhysicalControl.CONTROLLER_DPAD_LEFT,
        CONTROLLER_BUTTON_DPAD_RIGHT: PhysicalControl.CONTROLLER_DPAD_RIGHT,
        # SDL/Pygame names these A/B/X/Y, but the physical position is the
        # portable Greia contract. Activities never receive the brand labels.
        CONTROLLER_BUTTON_A: PhysicalControl.CONTROLLER_FACE_SOUTH,
        CONTROLLER_BUTTON_B: PhysicalControl.CONTROLLER_FACE_EAST,
        CONTROLLER_BUTTON_X: PhysicalControl.CONTROLLER_FACE_WEST,
        CONTROLLER_BUTTON_Y: PhysicalControl.CONTROLLER_FACE_NORTH,
        CONTROLLER_BUTTON_LEFTSHOULDER: PhysicalControl.CONTROLLER_LEFT_SHOULDER,
        CONTROLLER_BUTTON_RIGHTSHOULDER: PhysicalControl.CONTROLLER_RIGHT_SHOULDER,
        CONTROLLER_BUTTON_START: PhysicalControl.CONTROLLER_START,
        CONTROLLER_BUTTON_BACK: PhysicalControl.CONTROLLER_BACK,
        CONTROLLER_BUTTON_GUIDE: PhysicalControl.CONTROLLER_GUIDE,
    }


def _controller_axis_map() -> dict[int, ControllerAxis]:
    if sdl_controller is None:
        return {}
    return {
        CONTROLLER_AXIS_LEFTX: ControllerAxis.LEFT_X,
        CONTROLLER_AXIS_LEFTY: ControllerAxis.LEFT_Y,
        CONTROLLER_AXIS_RIGHTX: ControllerAxis.RIGHT_X,
        CONTROLLER_AXIS_RIGHTY: ControllerAxis.RIGHT_Y,
        CONTROLLER_AXIS_TRIGGERLEFT: ControllerAxis.LEFT_TRIGGER,
        CONTROLLER_AXIS_TRIGGERRIGHT: ControllerAxis.RIGHT_TRIGGER,
    }


_CONTROLLER_BUTTONS = _controller_button_map()
_CONTROLLER_AXES = _controller_axis_map()
_CONTROLLER_BUTTON_DOWN = getattr(pygame, "CONTROLLERBUTTONDOWN", -1)
_CONTROLLER_BUTTON_UP = getattr(pygame, "CONTROLLERBUTTONUP", -1)
_CONTROLLER_AXIS_MOTION = getattr(pygame, "CONTROLLERAXISMOTION", -1)
_CONTROLLER_DEVICE_EVENTS = frozenset(
    {
        getattr(pygame, "CONTROLLERDEVICEADDED", -2),
        getattr(pygame, "CONTROLLERDEVICEREMOVED", -3),
        getattr(pygame, "CONTROLLERDEVICEREMAPPED", -4),
    }
)


class PygameControllerSet:
    """Explicit bounded owner for controllers in trusted Pygame surfaces.

    This is suitable for Greia Shell and controlled backend prototypes. It is
    deliberately not an Activity permission mechanism: production Activities
    should receive brokered/semantic input rather than raw `/dev/input` access.

    On a topology event the tiny controller set is rebuilt from SDL's mapping
    catalogue. Rebuilding avoids stale instance bookkeeping and is bounded by
    both scan and open limits.
    """

    def __init__(
        self,
        *,
        maximum_open: int = MAX_OPEN_CONTROLLERS,
        maximum_scan: int = MAX_CONTROLLER_SCAN,
    ) -> None:
        if not 1 <= maximum_open <= 8:
            raise ValueError("maximum_open must be in [1, 8]")
        if not maximum_open <= maximum_scan <= 64:
            raise ValueError("maximum_scan must be between maximum_open and 64")
        self._maximum_open = int(maximum_open)
        self._maximum_scan = int(maximum_scan)
        self._controllers: list[object] = []
        self._started = False

    @property
    def supported(self) -> bool:
        return sdl_controller is not None

    @property
    def opened_count(self) -> int:
        return len(self._controllers)

    def start(self) -> int:
        if self._started:
            return self.opened_count
        self._started = True
        if sdl_controller is None:
            return 0
        try:
            sdl_controller.init()
            sdl_controller.set_eventstate(True)
            self._refresh()
        except (pygame.error, RuntimeError):
            self.close()
            return 0
        return self.opened_count

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Refresh after a bounded controller topology event.

        Returns True when the event represented controller topology, allowing a
        caller to invalidate any controller-specific UI hints if desired.
        """

        if event.type not in _CONTROLLER_DEVICE_EVENTS:
            return False
        if self._started and sdl_controller is not None:
            self._refresh()
        return True

    def first_left_stick(self) -> tuple[float, float]:
        """Return the first attached controller's normalized left-stick state."""

        if sdl_controller is None:
            return 0.0, 0.0
        for controller in self._controllers:
            try:
                if not controller.attached():
                    continue
                raw_x = controller.get_axis(CONTROLLER_AXIS_LEFTX)
                raw_y = controller.get_axis(CONTROLLER_AXIS_LEFTY)
            except (pygame.error, RuntimeError):
                continue
            return _signed_axis(raw_x), _signed_axis(raw_y)
        return 0.0, 0.0

    def close(self) -> None:
        for controller in reversed(self._controllers):
            try:
                controller.quit()
            except (pygame.error, RuntimeError):
                pass
        self._controllers.clear()
        if self._started and sdl_controller is not None:
            try:
                sdl_controller.quit()
            except (pygame.error, RuntimeError):
                pass
        self._started = False

    def _refresh(self) -> None:
        assert sdl_controller is not None
        for controller in reversed(self._controllers):
            try:
                controller.quit()
            except (pygame.error, RuntimeError):
                pass
        self._controllers.clear()
        count = min(max(0, int(sdl_controller.get_count())), self._maximum_scan)
        for index in range(count):
            if len(self._controllers) >= self._maximum_open:
                break
            try:
                if not sdl_controller.is_controller(index):
                    continue
                self._controllers.append(sdl_controller.Controller(index))
            except (pygame.error, RuntimeError):
                continue

    def __enter__(self) -> "PygameControllerSet":
        self.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()


class PygameInputTranslator:
    """Translate Pygame keyboard/SDL-controller events into Greia semantics.

    The translator does not open devices and does not own the Pygame event
    queue. A production Greia input broker/session backend may feed the same
    renderer-neutral controls without exposing raw controller devices to the
    Activity. This class exists so current Python consumers share the same
    learned mappings rather than inventing per-Activity button numbers.
    """

    def __init__(self, profile: InteractionProfile | str):
        self._mapper = StandardInputMapper(profile)

    @property
    def profile(self) -> InteractionProfile:
        return self._mapper.profile

    @property
    def controller_translation_available(self) -> bool:
        return sdl_controller is not None

    def digital(self, event: pygame.event.Event) -> SemanticInputEvent | None:
        translated = self.physical_digital(event)
        if translated is None:
            return None
        control, edge, source = translated
        return self._mapper.digital(control, edge, source)

    def physical_digital(
        self, event: pygame.event.Event
    ) -> tuple[PhysicalControl, InputEdge, InputSource] | None:
        if event.type in {pygame.KEYDOWN, pygame.KEYUP}:
            control = _KEY_CONTROLS.get(getattr(event, "key", None))
            if control is None:
                return None
            return (
                control,
                InputEdge.PRESSED if event.type == pygame.KEYDOWN else InputEdge.RELEASED,
                InputSource.KEYBOARD,
            )
        if event.type in {_CONTROLLER_BUTTON_DOWN, _CONTROLLER_BUTTON_UP}:
            control = _CONTROLLER_BUTTONS.get(getattr(event, "button", None))
            if control is None:
                return None
            return (
                control,
                InputEdge.PRESSED
                if event.type == _CONTROLLER_BUTTON_DOWN
                else InputEdge.RELEASED,
                InputSource.CONTROLLER,
            )
        return None

    def controller_axis(self, event: pygame.event.Event) -> ControllerAxisEvent | None:
        if event.type != _CONTROLLER_AXIS_MOTION:
            return None
        axis = _CONTROLLER_AXES.get(getattr(event, "axis", None))
        raw = getattr(event, "value", None)
        if axis is None or not isinstance(raw, int) or isinstance(raw, bool):
            return None
        if axis in {ControllerAxis.LEFT_TRIGGER, ControllerAxis.RIGHT_TRIGGER}:
            value = min(1.0, max(0.0, raw / 32768.0))
        else:
            value = _signed_axis(raw)
        return ControllerAxisEvent(axis, value)


def _signed_axis(raw: int) -> float:
    if not isinstance(raw, int) or isinstance(raw, bool):
        raise TypeError("controller axis value must be an integer")
    divisor = 32768.0 if raw < 0 else 32767.0
    return min(1.0, max(-1.0, raw / divisor))
