from __future__ import annotations

from dataclasses import dataclass

from greia_platform.input_core import (
    DEFAULT_INPUT_POLICY,
    InputEdge,
    InteractionProfile,
    SemanticAction,
    StandardInputPolicy,
    navigation_direction,
    normalize_stick,
)
from greia_platform.pygame_input import PygameControllerSet, PygameInputTranslator


@dataclass(frozen=True, slots=True)
class ShellInputSnapshot:
    """Small observable state for diagnostics/tests, not persistent product state."""

    controller_supported: bool
    opened_controllers: int
    held_analog_direction: SemanticAction | None


class ShellInputController:
    """Own controller navigation for the trusted Greia Shell.

    The Shell consumes only the standard NAV/ACTIVATE/CANCEL vocabulary. Raw
    SDL controller naming, handle ownership, dead zones and analog repeat stay
    below this class. The object is explicitly bounded by PygameControllerSet
    and must be closed with the Shell lifecycle.

    Secret/text entry remains keyboard-owned. Callers decide whether a semantic
    action is meaningful in the current Shell mode; this class never edits text
    and never opens Activity devices.
    """

    def __init__(
        self,
        *,
        controllers: PygameControllerSet | None = None,
        policy: StandardInputPolicy = DEFAULT_INPUT_POLICY,
    ) -> None:
        self._controllers = controllers or PygameControllerSet()
        self._translator = PygameInputTranslator(InteractionProfile.NAVIGATION)
        self._policy = policy
        self._held_analog_direction: SemanticAction | None = None
        self._next_repeat_at = 0.0

    @property
    def snapshot(self) -> ShellInputSnapshot:
        return ShellInputSnapshot(
            controller_supported=self._controllers.supported,
            opened_controllers=self._controllers.opened_count,
            held_analog_direction=self._held_analog_direction,
        )

    def start(self) -> ShellInputSnapshot:
        self._controllers.start()
        return self.snapshot

    def close(self) -> None:
        self._controllers.close()
        self._reset_analog()

    def handle_event(self, event: object) -> SemanticAction | None:
        """Return one pressed semantic controller action, if any.

        Device topology events are consumed only to refresh the bounded trusted
        controller set. Keyboard events remain on the launcher's established
        path so this integration cannot change existing keyboard behavior.
        """

        if self._controllers.handle_event(event):  # type: ignore[arg-type]
            self._reset_analog()
            return None
        translated = self._translator.digital(event)  # type: ignore[arg-type]
        if translated is None or translated.edge is not InputEdge.PRESSED:
            return None
        if translated.action in {
            SemanticAction.NAV_UP,
            SemanticAction.NAV_DOWN,
            SemanticAction.NAV_LEFT,
            SemanticAction.NAV_RIGHT,
            SemanticAction.ACTIVATE,
            SemanticAction.CANCEL,
        }:
            return translated.action
        return None

    def poll_analog(self, now: float) -> SemanticAction | None:
        """Emit deterministic left-stick navigation with bounded key-like repeat."""

        if now < 0.0:
            raise ValueError("now must be non-negative")
        raw_x, raw_y = self._controllers.first_left_stick()
        direction = navigation_direction(
            normalize_stick(raw_x, raw_y, self._policy.stick_dead_zone),
            self._policy.navigation_threshold,
        )
        if direction is None:
            self._reset_analog()
            return None
        if direction is not self._held_analog_direction:
            self._held_analog_direction = direction
            self._next_repeat_at = now + self._policy.navigation_repeat_delay_seconds
            return direction
        if now < self._next_repeat_at:
            return None
        self._next_repeat_at = now + self._policy.navigation_repeat_interval_seconds
        return direction

    def _reset_analog(self) -> None:
        self._held_analog_direction = None
        self._next_repeat_at = 0.0
