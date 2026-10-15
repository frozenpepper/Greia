"""Shared control-kit wiring for La Casa del Dieci (ADR 0037 pilot).

The Activity keeps its own house, windows and fireflies; every interactive
element goes through ``greia_platform.activity_controls``: the ten windows
and the waiting guest fireflies are ``ExternalTarget``s (pointer activation,
keyboard / D-pad / stick focus and the shared focus ring), the "how many?"
answers are kit ``IconButton`` tiles showing a numeral (+ a mini ten-frame at
stage 3), "the house is ready" is a primary round ``IconButton`` with the
shared check glyph, the replay voice is a round ``IconButton`` with the
shared listen glyph and progress is ``ProgressDots``. There is no text on the
play screen. Gameplay rules stay in ``TenHouseSession``; this class only maps
controls to the app callbacks and mirrors session state into them.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pygame

from greia_platform.activity_controls import (
    Align,
    BodyShape,
    ButtonRole,
    ControlKit,
    ControlLayer,
    ControlLayout,
    ExternalTarget,
    IconButton,
    ProgressDots,
)

if __package__:
    from .ten_house_art import TenHouseArt
    from .ten_house_layout import CHOICE_RECTS, CONFIRM_RECT, GUEST_SLOTS, GUEST_TARGET, ROOM_RECTS
    from .ten_house_model import CHALLENGE_COUNT, Phase, TenHouseSession
else:
    from ten_house_art import TenHouseArt
    from ten_house_layout import CHOICE_RECTS, CONFIRM_RECT, GUEST_SLOTS, GUEST_TARGET, ROOM_RECTS
    from ten_house_model import CHALLENGE_COUNT, Phase, TenHouseSession


def room_id(index: int) -> str:
    return f"room.{index}"


def guest_id(index: int) -> str:
    return f"guest.{index}"


def choice_id(index: int) -> str:
    return f"choice.{index}"


class TenHouseControls:
    """Own the kit controls and the ``ControlLayer`` for the Ten House screen."""

    def __init__(
        self,
        kit: ControlKit,
        art: TenHouseArt,
        layout: ControlLayout,
        *,
        on_room: Callable[[int], object],
        on_guest: Callable[[int], object],
        on_choice: Callable[[int], object],
        on_confirm: Callable[[], object],
        on_replay: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._art = art
        self.rooms = tuple(
            ExternalTarget(room_id(index), rect, (lambda i=index: on_room(i)), focus_radius=14)
            for index, rect in enumerate(ROOM_RECTS)
        )
        half = GUEST_TARGET // 2
        self.guests = tuple(
            ExternalTarget(
                guest_id(index),
                pygame.Rect(x - half, y - half, GUEST_TARGET, GUEST_TARGET),
                (lambda i=index: on_guest(i)),
                enabled=False,
                focus_radius=half,
            )
            for index, (x, y) in enumerate(GUEST_SLOTS)
        )
        self.choices: tuple[IconButton, ...] = tuple(
            kit.icon_button(
                choice_id(index),
                rect,
                icon=None,
                shape=BodyShape.TILE,
                on_activate=(lambda i=index: on_choice(i)),
                enabled=False,
            )
            for index, rect in enumerate(CHOICE_RECTS)
        )
        self.confirm: IconButton = kit.icon_button(
            "confirm",
            CONFIRM_RECT,
            icon=kit.glyph("check", 64),
            role=ButtonRole.PRIMARY,
            on_activate=on_confirm,
        )
        self.listen: IconButton = kit.icon_button(
            "listen",
            pygame.Rect(0, 0, 64, 64),
            icon=kit.glyph("listen", 40),
            on_activate=on_replay,
        )
        self.progress: ProgressDots = kit.progress_dots(
            "progress", pygame.Rect(0, 0, 10, 10), total=CHALLENGE_COUNT
        )
        self.layer: ControlLayer = kit.layer(
            (*self.rooms, *self.guests, *self.choices, self.confirm, self.listen, self.progress),
            layer_id="ten_house.controls",
        )
        self._challenge_id: str | None = None
        self._phase: Phase | None = None
        self._choice_values: tuple[int, ...] = ()
        self.relayout(layout)

    # -- geometry --------------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> None:
        """Top bar beside protected chrome: replay voice, then progress dots."""

        height = layout.control_height(56, maximum=72)
        bar = layout.top_bar(height)
        dots_height = max(34, int(height * 0.66))
        dots_width = ProgressDots.preferred_width(CHALLENGE_COUNT, dots_height)
        listen_rect, dots_rect = layout.row(bar, [height, dots_width], align=Align.END, height=height)
        self.listen.rect = listen_rect
        self.progress.rect = pygame.Rect(dots_rect.x, dots_rect.centery - dots_height // 2, dots_width, dots_height)
        self.layer.invalidation.invalidate()

    # -- state sync ---------------------------------------------------------------

    def choice_value(self, index: int) -> int | None:
        if 0 <= index < len(self._choice_values):
            return self._choice_values[index]
        return None

    def sync(
        self,
        session: TenHouseSession,
        *,
        waiting: Sequence[int] = (),
        busy: bool = False,
        refocus: bool = False,
    ) -> None:
        """Mirror the session into control enablement/visibility (cheap).

        ``busy`` is True while a scripted moment plays (fireflies flying,
        Dani demonstrating): controls stay visible but cannot be activated.
        """

        challenge = session.current_challenge
        self.progress.set_progress(session.completed_count)
        if challenge is None:
            self.layer.invalidation.invalidate()
            return
        phase = session.phase
        building = phase is Phase.BUILD and not busy
        arriving = phase is Phase.ARRIVING and not busy
        asking = phase is Phase.ASKING
        for index, room in enumerate(self.rooms):
            room.enabled = building or (arriving and index >= session.lit)
        live_guests = set(waiting) if arriving else set()
        for index, guest in enumerate(self.guests):
            guest.enabled = index in live_guests
        if challenge.choice_values != self._choice_values or challenge.challenge_id != self._challenge_id:
            self._choice_values = challenge.choice_values
            frames = session.presentation.card_frames
            for button, value in zip(self.choices, self._choice_values):
                button.icon = self._art.card_face(value, frame=frames)
        for index, button in enumerate(self.choices):
            value = self.choice_value(index)
            button.visible = asking and value is not None
            button.enabled = button.visible and not busy and value not in session.rejected
        self.confirm.visible = phase is Phase.BUILD
        self.confirm.enabled = building
        self.listen.enabled = phase is not Phase.SOLVED
        changed_round = challenge.challenge_id != self._challenge_id
        changed_phase = phase is not self._phase
        self._challenge_id = challenge.challenge_id
        self._phase = phase
        if refocus or changed_round or changed_phase or not self._focused_is_live():
            self.focus_default(session, waiting)
        self.layer.invalidation.invalidate()

    def focus_default(self, session: TenHouseSession, waiting: Sequence[int] = ()) -> None:
        phase = session.phase
        if phase is Phase.BUILD:
            self.layer.focus(room_id(min(session.lit, len(self.rooms) - 1)))
        elif phase is Phase.ARRIVING and waiting:
            self.layer.focus(guest_id(waiting[0]))
        elif phase is Phase.ASKING:
            enabled = [button for button in self.choices if button.enabled]
            if enabled:
                middle = enabled[len(enabled) // 2]
                self.layer.focus(middle.control_id)
        self.layer.ensure_focus()

    def _focused_is_live(self) -> bool:
        focused = self.layer.focused_id
        if focused is None:
            return False
        target = self.layer.target(focused)
        return target.focusable and target.enabled

    def wobble_target(self, control_id: str | None) -> IconButton | None:
        """Return the answer control that shakes on a try-again."""

        if control_id == self.confirm.control_id:
            return self.confirm
        return next((button for button in self.choices if button.control_id == control_id), None)


__all__ = ["TenHouseControls", "choice_id", "guest_id", "room_id"]
