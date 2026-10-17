from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import inf, nextafter

from greia_platform.input_core import (
    DEFAULT_INPUT_POLICY,
    InputEdge,
    InputSource,
    InteractionProfile,
    PhysicalControl,
    SemanticAction,
    StandardInputPolicy,
    navigation_direction,
    normalize_stick,
)
from greia_platform.pygame_input import PygameControllerSet, PygameInputTranslator


class ShellControllerCommand(StrEnum):
    """Trusted-Shell-only controller intents beyond the NAV/ACTIVATE/CANCEL set.

    These are never part of the Activity vocabulary (``SemanticAction``): the
    standard mapper withholds the Guide control and defines no shoulder meaning
    for Activities, so only the trusted Shell consumes them. ``SECTION_*`` is
    "previous/next section or page" of whichever Shell surface is active (Parent
    panel section, Collection page, badge shelf page); ``HOME`` is the reserved
    Greia Home control.
    """

    SECTION_PREVIOUS = "section_previous"
    SECTION_NEXT = "section_next"
    HOME = "home"


ShellInputAction = SemanticAction | ShellControllerCommand

_SHELL_COMMAND_CONTROLS = {
    PhysicalControl.CONTROLLER_LEFT_SHOULDER: ShellControllerCommand.SECTION_PREVIOUS,
    PhysicalControl.CONTROLLER_RIGHT_SHOULDER: ShellControllerCommand.SECTION_NEXT,
    PhysicalControl.CONTROLLER_GUIDE: ShellControllerCommand.HOME,
}


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
    def controllers(self) -> PygameControllerSet:
        return self._controllers

    @property
    def snapshot(self) -> ShellInputSnapshot:
        return ShellInputSnapshot(
            controller_supported=self._controllers.supported,
            opened_controllers=self._controllers.opened_count,
            held_analog_direction=self._held_analog_direction,
        )

    def start(self) -> ShellInputSnapshot:
        self._reset_analog()
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
        physical = self._translator.physical_digital(event)  # type: ignore[arg-type]
        if physical is None:
            return None
        control, edge, source = physical
        if source is not InputSource.CONTROLLER or edge is not InputEdge.PRESSED:
            return None
        translated = self._translator.digital(event)  # type: ignore[arg-type]
        if translated is None:
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

    def translate_event(self, event: object) -> ShellInputAction | None:
        """Return the one Shell action a controller event means, if any.

        Superset of :meth:`handle_event`: the standard NAV/ACTIVATE/CANCEL
        actions plus the trusted-Shell-only shoulder and Guide commands.
        Topology events are consumed exactly once (by ``handle_event``), and
        keyboard events are never translated here, so a surface can feed every
        non-keyboard event through this single call without double dispatch.
        """

        action = self.handle_event(event)
        if action is not None:
            return action
        physical = self._translator.physical_digital(event)  # type: ignore[arg-type]
        if physical is None:
            return None
        control, edge, source = physical
        if source is not InputSource.CONTROLLER or edge is not InputEdge.PRESSED:
            return None
        return _SHELL_COMMAND_CONTROLS.get(control)

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
        # Durations such as 1.30 + 0.10 can encode as 1.4000000000000001.
        # Treat a timestamp at the immediately adjacent representable value as
        # the configured deadline rather than delaying one UI polling cycle.
        if now < nextafter(self._next_repeat_at, -inf):
            return None
        self._next_repeat_at = now + self._policy.navigation_repeat_interval_seconds
        return direction

    def _reset_analog(self) -> None:
        self._held_analog_direction = None
        self._next_repeat_at = 0.0
