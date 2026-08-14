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
        sdl_controller.CONTROLLER_BUTTON_DPAD_UP: PhysicalControl.CONTROLLER_DPAD_UP,
        sdl_controller.CONTROLLER_BUTTON_DPAD_DOWN: PhysicalControl.CONTROLLER_DPAD_DOWN,
        sdl_controller.CONTROLLER_BUTTON_DPAD_LEFT: PhysicalControl.CONTROLLER_DPAD_LEFT,
        sdl_controller.CONTROLLER_BUTTON_DPAD_RIGHT: PhysicalControl.CONTROLLER_DPAD_RIGHT,
        # SDL/Pygame names these A/B/X/Y, but the physical position is the
        # portable Greia contract. Activities never receive the brand labels.
        sdl_controller.CONTROLLER_BUTTON_A: PhysicalControl.CONTROLLER_FACE_SOUTH,
        sdl_controller.CONTROLLER_BUTTON_B: PhysicalControl.CONTROLLER_FACE_EAST,
        sdl_controller.CONTROLLER_BUTTON_X: PhysicalControl.CONTROLLER_FACE_WEST,
        sdl_controller.CONTROLLER_BUTTON_Y: PhysicalControl.CONTROLLER_FACE_NORTH,
        sdl_controller.CONTROLLER_BUTTON_LEFTSHOULDER: PhysicalControl.CONTROLLER_LEFT_SHOULDER,
        sdl_controller.CONTROLLER_BUTTON_RIGHTSHOULDER: PhysicalControl.CONTROLLER_RIGHT_SHOULDER,
        sdl_controller.CONTROLLER_BUTTON_START: PhysicalControl.CONTROLLER_START,
        sdl_controller.CONTROLLER_BUTTON_BACK: PhysicalControl.CONTROLLER_BACK,
        sdl_controller.CONTROLLER_BUTTON_GUIDE: PhysicalControl.CONTROLLER_GUIDE,
    }


def _controller_axis_map() -> dict[int, ControllerAxis]:
    if sdl_controller is None:
        return {}
    return {
        sdl_controller.CONTROLLER_AXIS_LEFTX: ControllerAxis.LEFT_X,
        sdl_controller.CONTROLLER_AXIS_LEFTY: ControllerAxis.LEFT_Y,
        sdl_controller.CONTROLLER_AXIS_RIGHTX: ControllerAxis.RIGHT_X,
        sdl_controller.CONTROLLER_AXIS_RIGHTY: ControllerAxis.RIGHT_Y,
        sdl_controller.CONTROLLER_AXIS_TRIGGERLEFT: ControllerAxis.LEFT_TRIGGER,
        sdl_controller.CONTROLLER_AXIS_TRIGGERRIGHT: ControllerAxis.RIGHT_TRIGGER,
    }


_CONTROLLER_BUTTONS = _controller_button_map()
_CONTROLLER_AXES = _controller_axis_map()
_CONTROLLER_BUTTON_DOWN = getattr(pygame, "CONTROLLERBUTTONDOWN", -1)
_CONTROLLER_BUTTON_UP = getattr(pygame, "CONTROLLERBUTTONUP", -1)
_CONTROLLER_AXIS_MOTION = getattr(pygame, "CONTROLLERAXISMOTION", -1)


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
            divisor = 32768.0 if raw < 0 else 32767.0
            value = min(1.0, max(-1.0, raw / divisor))
        return ControllerAxisEvent(axis, value)
