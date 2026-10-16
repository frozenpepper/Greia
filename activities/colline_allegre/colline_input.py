"""Driving input for Colline Allegre: the platform ``game`` profile -> pedals.

Learned Greia game mapping (ADR 0020), no raw device numbers:

* GO: Right arrow / Up arrow / Space, D-pad right / up, the south face
  button, the right trigger, left stick pushed right;
* BRAKE: Left arrow / Down arrow, D-pad left / down, the east face button,
  the left trigger, left stick pushed left;
* in the air, right leans the nose down and left leans it back;
* touch / pointer: hold the big GO or BRAKE pedal.

``DriveInput`` only tracks what is held; it never opens a device.
"""

from __future__ import annotations

import pygame

from greia_platform.input_core import (
    ControllerAxis,
    InputEdge,
    InteractionProfile,
    PhysicalControl,
    SemanticAction,
)
from greia_platform.pygame_input import PygameInputTranslator

if __package__:
    from .colline_model import Controls
else:
    from colline_model import Controls

GO_ACTIONS = frozenset({SemanticAction.MOVE_RIGHT, SemanticAction.MOVE_UP, SemanticAction.PRIMARY})
BRAKE_ACTIONS = frozenset({SemanticAction.MOVE_LEFT, SemanticAction.MOVE_DOWN, SemanticAction.SECONDARY})
LISTEN_CONTROLS = frozenset({PhysicalControl.CONTROLLER_FACE_NORTH})
STICK_THRESHOLD = 0.5
TRIGGER_THRESHOLD = 0.3


class DriveInput:
    """What the child is holding right now, from every input family."""

    def __init__(self) -> None:
        self._translator = PygameInputTranslator(InteractionProfile.GAME)
        self._held: set[SemanticAction] = set()
        self._stick_x = 0.0
        self._triggers = {ControllerAxis.LEFT_TRIGGER: 0.0, ControllerAxis.RIGHT_TRIGGER: 0.0}
        self.touch_go = False
        self.touch_brake = False

    # -- events -----------------------------------------------------------------------

    def handle(self, event: pygame.event.Event) -> SemanticAction | str | None:
        """Consume a keyboard/controller event.

        Returns ``"listen"`` for the replay-the-goal buttons (Enter, north face),
        the pressed driving action, ``SemanticAction.CANCEL`` for Escape / Back,
        or ``None`` when the event is not driving input.
        """

        physical = self._translator.physical_digital(event)
        if physical is not None and physical[0] in LISTEN_CONTROLS:
            return "listen" if physical[1] is InputEdge.PRESSED else None
        semantic = self._translator.digital(event)
        if semantic is not None:
            action = semantic.action
            if action in GO_ACTIONS or action in BRAKE_ACTIONS:
                if semantic.edge is InputEdge.PRESSED:
                    self._held.add(action)
                    return action
                self._held.discard(action)
                return None
            if semantic.edge is not InputEdge.PRESSED:
                return None
            if action is SemanticAction.ACTIVATE:
                return "listen"
            if action is SemanticAction.CANCEL:
                return SemanticAction.CANCEL
            return None
        axis = self._translator.controller_axis(event)
        if axis is not None:
            if axis.axis is ControllerAxis.LEFT_X:
                was = self.go or self.brake
                self._stick_x = axis.value
                if not was and (self.go or self.brake):
                    return SemanticAction.MOVE_RIGHT if self.go else SemanticAction.MOVE_LEFT
            elif axis.axis in self._triggers:
                was = self.go or self.brake
                self._triggers[axis.axis] = axis.value
                if not was and (self.go or self.brake):
                    return SemanticAction.MOVE_RIGHT if self.go else SemanticAction.MOVE_LEFT
        return None

    def release_all(self) -> None:
        self._held.clear()
        self._stick_x = 0.0
        for axis in self._triggers:
            self._triggers[axis] = 0.0
        self.touch_go = False
        self.touch_brake = False

    # -- state --------------------------------------------------------------------------

    @property
    def go(self) -> bool:
        return bool(
            self._held & GO_ACTIONS
            or self.touch_go
            or self._stick_x > STICK_THRESHOLD
            or self._triggers[ControllerAxis.RIGHT_TRIGGER] > TRIGGER_THRESHOLD
        )

    @property
    def brake(self) -> bool:
        return bool(
            self._held & BRAKE_ACTIONS
            or self.touch_brake
            or self._stick_x < -STICK_THRESHOLD
            or self._triggers[ControllerAxis.LEFT_TRIGGER] > TRIGGER_THRESHOLD
        )

    @property
    def tilt(self) -> float:
        tilt = 0.0
        if SemanticAction.MOVE_RIGHT in self._held:
            tilt += 1.0
        if SemanticAction.MOVE_LEFT in self._held:
            tilt -= 1.0
        if abs(self._stick_x) > 0.2:
            tilt += self._stick_x
        return max(-1.0, min(1.0, tilt))

    def controls(self) -> Controls:
        go = self.go
        brake = self.brake and not go
        return Controls(go=go, brake=brake, tilt=self.tilt)


__all__ = ["DriveInput"]
