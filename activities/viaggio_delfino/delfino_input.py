"""Il Viaggio del Delfino — runtime-neutral swim input (ADR 0020).

While swimming, the Activity uses the standard *directional* vocabulary:
arrows / W-S / D-pad hold the dolphin's depth up or down, the left stick
steers proportionally (through Greia's central dead zone), and Space / Enter
/ the south face button leap. Events are translated with the shared
``PygameInputTranslator``; no device is opened here. Pointer and touch
steering (aim at a depth, tap to leap) are routed by the app because they
need the canvas mapping and the protected-chrome check.
"""

from __future__ import annotations

from enum import StrEnum

import pygame

from greia_platform.input_core import (
    DEFAULT_INPUT_POLICY,
    ControllerAxis,
    InputEdge,
    InteractionProfile,
    SemanticAction,
    StandardInputPolicy,
    normalize_stick,
)
from greia_platform.pygame_input import PygameInputTranslator


class SwimInput(StrEnum):
    """What one translated event meant for the swim."""

    STEER = "steer"
    LEAP = "leap"


_UP_KEYS = frozenset({pygame.K_w})
_DOWN_KEYS = frozenset({pygame.K_s})


class DolphinSteering:
    """Hold-to-steer state for keyboard, D-pad and stick (bounded, tiny)."""

    #: Target-depth speed while a direction is held (logical px per second).
    HOLD_SPEED = 430.0

    def __init__(self, policy: StandardInputPolicy = DEFAULT_INPUT_POLICY) -> None:
        self._translator = PygameInputTranslator(InteractionProfile.DIRECTIONAL)
        self._policy = policy
        self._up: set[str] = set()
        self._down: set[str] = set()
        self._stick_y = 0.0

    def reset(self) -> None:
        self._up.clear()
        self._down.clear()
        self._stick_y = 0.0

    @property
    def axis(self) -> float:
        """-1 (up) .. 1 (down); held buttons win over the stick."""

        held = (1.0 if self._down else 0.0) - (1.0 if self._up else 0.0)
        return held if held else self._stick_y

    @property
    def active(self) -> bool:
        return bool(self._up or self._down or self._stick_y)

    def step(self, dt: float) -> float:
        """Target-depth change for this frame."""

        return self.axis * self.HOLD_SPEED * dt

    def handle(self, event: pygame.event.Event) -> SwimInput | None:
        if event.type in (pygame.KEYDOWN, pygame.KEYUP):
            key = getattr(event, "key", None)
            pressed = event.type == pygame.KEYDOWN
            if key in _UP_KEYS:
                return self._hold(self._up, "key_w", pressed)
            if key in _DOWN_KEYS:
                return self._hold(self._down, "key_s", pressed)
        semantic = self._translator.digital(event)
        if semantic is not None:
            pressed = semantic.edge is InputEdge.PRESSED
            source = semantic.source.value
            if semantic.action is SemanticAction.MOVE_UP:
                return self._hold(self._up, source, pressed)
            if semantic.action is SemanticAction.MOVE_DOWN:
                return self._hold(self._down, source, pressed)
            if semantic.action in (SemanticAction.PRIMARY, SemanticAction.ACTIVATE) and pressed:
                return SwimInput.LEAP
            return None
        axis = self._translator.controller_axis(event)
        if axis is not None and axis.axis is ControllerAxis.LEFT_Y:
            vector = normalize_stick(0.0, axis.value, self._policy.stick_dead_zone)
            self._stick_y = vector.y
            return SwimInput.STEER if vector.y else None
        return None

    @staticmethod
    def _hold(group: set[str], source: str, pressed: bool) -> SwimInput:
        if pressed:
            group.add(source)
        else:
            group.discard(source)
        return SwimInput.STEER


__all__ = ["DolphinSteering", "SwimInput"]
