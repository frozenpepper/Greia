"""Controller virtual pointer for Painting (``pointer`` interaction profile).

ACTIVITY_INPUT_STANDARDS: in a pointer Activity the controller's left stick
drives a Greia virtual pointer and the south face button presses there. This
class owns that state (stick vector, ``VirtualPointer``, active/pressed flags)
and reports pointer phases through callbacks, so the app routes them exactly
like mouse/touch input. It never opens a device; it only interprets events
the runtime already delivers. D-pad navigation stays with the control kit.
"""

from __future__ import annotations

from collections.abc import Callable

import pygame

from greia_platform.input_core import (
    DEFAULT_INPUT_POLICY,
    ControllerAxis,
    InputEdge,
    PhysicalControl,
    VirtualPointer,
    normalize_stick,
)
from greia_platform.pygame_input import PygameInputTranslator

Point = tuple[int, int]


class ControllerPointer:
    """Left stick → Greia virtual pointer; south button → press/release."""

    def __init__(self, surface_size: Callable[[], tuple[int, int]], home: Callable[[], Point]) -> None:
        self._surface_size = surface_size
        self._home = home
        self._translator = PygameInputTranslator("pointer")
        self._stick = (0.0, 0.0)
        self._pointer: VirtualPointer | None = None
        self.active = False
        self.pressed = False

    @property
    def position(self) -> Point | None:
        return self._pointer.position if self._pointer is not None else None

    def deactivate(self) -> None:
        """Another input (mouse, keys, D-pad) took over."""
        self.active = False

    def reset(self) -> None:
        """Forget geometry after a display resize."""
        self._pointer = None
        self.active = False
        self.pressed = False

    def handle(
        self,
        event: pygame.event.Event,
        *,
        on_down: Callable[[Point], object],
        on_up: Callable[[Point], object],
    ) -> bool:
        """Consume stick motion and (while active) the south button."""
        axis = self._translator.controller_axis(event)
        if axis is not None:
            if axis.axis in {ControllerAxis.LEFT_X, ControllerAxis.LEFT_Y}:
                x, y = self._stick
                self._stick = (axis.value, y) if axis.axis is ControllerAxis.LEFT_X else (x, axis.value)
                if normalize_stick(*self._stick, DEFAULT_INPUT_POLICY.stick_dead_zone).magnitude > 0.0:
                    if self._pointer is None:
                        width, height = self._surface_size()
                        hx, hy = self._home()
                        self._pointer = VirtualPointer(width, height, x=hx, y=hy)
                    self.active = True
            return True
        physical = self._translator.physical_digital(event)
        if (
            physical is None
            or physical[0] is not PhysicalControl.CONTROLLER_FACE_SOUTH
            or not self.active
            or self._pointer is None
        ):
            return False
        if physical[1] is InputEdge.PRESSED:
            self.pressed = True
            on_down(self._pointer.position)
        else:
            self.pressed = False
            on_up(self._pointer.position)
        return True

    def step(self, elapsed: float) -> Point | None:
        """Advance the pointer; return its new position when it moved."""
        if self._pointer is None or not self.active:
            return None
        before = self._pointer.position
        after = self._pointer.move(*self._stick, min(1.0, max(0.0, elapsed)))
        return after if after != before else None


__all__ = ["ControllerPointer"]
