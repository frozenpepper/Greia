"""Shared control-kit wiring for La Casa del Dieci (ADR 0037 pilot).

The Activity keeps its own house/window art; every interactive control comes
from ``greia_platform.activity_controls``: the ten windows are focus targets,
the prompt is a ``PromptBanner`` with a replay-voice button, answers are
``PillButton``s, OK is the primary pill and progress is ``ProgressDots``.
Gameplay rules stay in ``TenHouseSession``; this class only maps controls to
the Activity callbacks and mirrors focus into the session for compatibility.
"""

from __future__ import annotations

from collections.abc import Callable

import pygame

from greia_platform.activity_controls import (
    Align,
    ButtonRole,
    ControlKit,
    ControlLayer,
    ControlLayout,
    ExternalTarget,
    PillButton,
    ProgressDots,
    PromptBanner,
)
from greia_platform.localization import LocalizationError, LocalizedResources

if __package__:
    from .ten_house_model import CHALLENGE_COUNT, OperationMode, REFERENCE_WIDTH, ROOM_COUNT, TenHouseSession
    from .ten_house_renderer import CHOICE_RECTS, CONFIRM_RECT, ROOM_RECTS
else:
    from ten_house_model import CHALLENGE_COUNT, OperationMode, REFERENCE_WIDTH, ROOM_COUNT, TenHouseSession
    from ten_house_renderer import CHOICE_RECTS, CONFIRM_RECT, ROOM_RECTS

BANNER_Y = 416
BANNER_HEIGHT = 54


def room_id(index: int) -> str:
    return f"room.{index}"


def choice_id(index: int) -> str:
    return f"choice.{index}"


class TenHouseControls:
    """Own the kit controls and the ``ControlLayer`` for one Ten House screen."""

    def __init__(
        self,
        kit: ControlKit,
        resources: LocalizedResources,
        layout: ControlLayout,
        *,
        on_room: Callable[[int], object],
        on_choice: Callable[[int], object],
        on_confirm: Callable[[], object],
        on_replay: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._resources = resources
        self._turn_on = {value: self._resolve("goal.turn_on", {"target": value}) for value in range(ROOM_COUNT + 1)}
        self._bulb = kit.text_icon("💡", 30)
        self.rooms = tuple(
            ExternalTarget(room_id(index), rect, (lambda i=index: on_room(i)), focus_radius=12)
            for index, rect in enumerate(ROOM_RECTS)
        )
        self.choices = tuple(
            kit.pill_button(
                choice_id(index),
                rect,
                label="0",
                icon=self._bulb,
                label_size=40,
                on_activate=(lambda i=index: on_choice(i)),
            )
            for index, rect in enumerate(CHOICE_RECTS)
        )
        self.confirm: PillButton = kit.pill_button(
            "confirm",
            CONFIRM_RECT,
            label="OK",
            icon=kit.glyph("check", 40),
            label_size=34,
            role=ButtonRole.PRIMARY,
            on_activate=on_confirm,
        )
        self.banner: PromptBanner = kit.prompt_banner(
            "prompt",
            pygame.Rect(0, BANNER_Y, 600, BANNER_HEIGHT),
            replay_icon=kit.glyph("listen", 34),
            on_replay=on_replay,
            text_size=28,
        )
        self.progress: ProgressDots = kit.progress_dots(
            "progress", pygame.Rect(0, 0, 10, 10), total=CHALLENGE_COUNT
        )
        self.layer: ControlLayer = kit.layer(
            (*self.rooms, *self.banner.controls, *self.choices, self.confirm, self.progress),
            layer_id="ten_house.controls",
        )
        self._challenge_id: str | None = None
        self.relayout(layout)

    def _resolve(self, key: str, variables: dict[str, object] | None = None) -> str:
        try:
            return self._resources.text(key, variables).strip()
        except LocalizationError:
            return ""

    # -- geometry --
    def relayout(self, layout: ControlLayout) -> None:
        """Place the progress dots in the top bar beside protected chrome."""

        height = 36
        bar = layout.top_bar(48)
        width = ProgressDots.preferred_width(CHALLENGE_COUNT, height)
        (rect,) = layout.row(bar, [width], align=Align.END, height=height)
        self.progress.rect = rect

    # -- state sync --
    def sync(self, session: TenHouseSession) -> None:
        """Mirror the session into control content/visibility (cheap; cached)."""

        challenge = session.current_challenge
        self.progress.set_progress(session.challenge_index)
        if challenge is None:
            return
        compose = challenge.mode == OperationMode.COMPOSE
        for room in self.rooms:
            room.enabled = compose
        for button, value in zip(self.choices, challenge.choice_values):
            button.label = str(value)
            button.visible = not compose
        self.confirm.visible = compose
        self.confirm.role = ButtonRole.PRIMARY if session.lit_count > 0 else ButtonRole.NEUTRAL
        self.banner.set_text(self._prompt_text(challenge, session))
        width = min(REFERENCE_WIDTH - 360, max(380, self.banner.preferred_width()))
        self.banner.rect = pygame.Rect(REFERENCE_WIDTH // 2 - width // 2 + 40, BANNER_Y, width, BANNER_HEIGHT)
        if challenge.challenge_id != self._challenge_id:
            self._challenge_id = challenge.challenge_id
            self.layer.focus(room_id(0) if compose else choice_id(1))
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()

    def _prompt_text(self, challenge, session: TenHouseSession) -> str:
        if challenge.mode == OperationMode.COMPOSE:
            turn_on = self._turn_on.get(challenge.target, "") or str(challenge.target)
            return f"🎯 {turn_on} 💡   {session.lit_count} / {challenge.target}"
        if challenge.mode == OperationMode.ADD:
            return f"🎯 {challenge.starting_lit} 💡 + {challenge.delta} 💡 = ❓"
        if challenge.mode == OperationMode.TAKE_AWAY:
            return f"🎯 {challenge.starting_lit} 💡 - {challenge.delta} 💡 = ❓"
        if challenge.mode == OperationMode.MISSING_PART:
            return f"🎯 {challenge.starting_lit} 💡 + ❓ = {challenge.target} 💡"
        return f"🎯 {challenge.target}"

    def mirror_focus(self, session: TenHouseSession) -> None:
        """Keep the session's legacy focus fields equal to the kit focus."""

        focused = self.layer.focused_id or ""
        if focused.startswith("room."):
            session.focused_room = int(focused.split(".", 1)[1])
            session.focus_in_choices = False
        elif focused.startswith("choice."):
            session.focused_choice = int(focused.split(".", 1)[1])
            session.focus_in_choices = True
        elif focused == "confirm":
            session.focused_choice = 0
            session.focus_in_choices = True

    def wobble_target(self) -> PillButton | None:
        """Return the answer control that shakes on a try-again."""

        if self.confirm.visible:
            return self.confirm
        focused = self.layer.focused_id
        for button in self.choices:
            if button.control_id == focused:
                return button
        return None


__all__ = ["TenHouseControls", "choice_id", "room_id"]
