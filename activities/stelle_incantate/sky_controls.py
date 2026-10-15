"""Shared control-kit wiring for Stelle Incantate (ADR 0037).

Stars are Activity-drawn ``ExternalTarget``s (the kit adds pointer
activation, keyboard/D-pad/stick focus and the focus ring); the goal strip is
a kit ``PromptBanner`` whose replay button repeats the goal; the missing
number is chosen on kit ``IconButton`` tiles; the next figure and the
curiosity fact are round kit ``IconButton``s with shared glyphs, and night
progress is ``ProgressDots``.

Focus is never moved to the right star for the child: after a tap it stays
where the child put it, and the default focus is the goal strip's replay
button, so keyboard and controller players also decide where to go.
"""

from __future__ import annotations

from collections.abc import Callable

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
    PromptBanner,
)

if __package__:
    from .sky_art import SkyArt
    from .sky_content import (
        CARD_CENTER,
        CARD_GAP,
        CARD_SIZE,
        FACT_CENTER,
        FACT_SIZE,
        NEXT_CENTER,
        NEXT_SIZE,
        STAR_SIZE,
        STAR_TARGET,
        sky_point,
    )
    from .sky_model import Phase, SkyRound
else:
    from sky_art import SkyArt
    from sky_content import (
        CARD_CENTER,
        CARD_GAP,
        CARD_SIZE,
        FACT_CENTER,
        FACT_SIZE,
        NEXT_CENTER,
        NEXT_SIZE,
        STAR_SIZE,
        STAR_TARGET,
        sky_point,
    )
    from sky_model import Phase, SkyRound

MAX_CARDS = 3
BANNER_HEIGHT = 64


def star_id(index: int) -> str:
    return f"star.{index}"


def card_id(index: int) -> str:
    return f"card.{index}"


def card_rects(count: int) -> list[pygame.Rect]:
    width, height = CARD_SIZE
    total = count * width + (count - 1) * CARD_GAP
    left = CARD_CENTER[0] - total // 2
    return [
        pygame.Rect(left + index * (width + CARD_GAP), CARD_CENTER[1] - height // 2, width, height)
        for index in range(count)
    ]


def _square(centre: tuple[int, int], size: int) -> pygame.Rect:
    rect = pygame.Rect(0, 0, size, size)
    rect.center = centre
    return rect


class SkyControls:
    """Own the kit controls and the ``ControlLayer`` for the sky screen."""

    def __init__(
        self,
        kit: ControlKit,
        art: SkyArt,
        layout: ControlLayout,
        figures: int,
        *,
        on_star: Callable[[int], object],
        on_card: Callable[[int], object],
        on_goal: Callable[[], object],
        on_next: Callable[[], object],
        on_fact: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._art = art
        self._on_star = on_star
        self.stars: list[ExternalTarget] = []
        self.goal: PromptBanner = kit.prompt_banner(
            "goal",
            pygame.Rect(0, 0, 320, BANNER_HEIGHT),
            replay_icon=kit.glyph("listen", 34),
            on_replay=on_goal,
        )
        self.cards: tuple[IconButton, ...] = tuple(
            kit.icon_button(
                card_id(index),
                rect,
                icon=None,
                shape=BodyShape.TILE,
                on_activate=(lambda i=index: on_card(i)),
                enabled=False,
            )
            for index, rect in enumerate(card_rects(MAX_CARDS))
        )
        self.next: IconButton = kit.icon_button(
            "next",
            _square(NEXT_CENTER, NEXT_SIZE),
            icon=kit.glyph("go", 60),
            role=ButtonRole.PRIMARY,
            on_activate=on_next,
            enabled=False,
        )
        self.fact: IconButton = kit.icon_button(
            "fact",
            _square(FACT_CENTER, FACT_SIZE),
            icon=kit.glyph("hint", 46),
            on_activate=on_fact,
            enabled=False,
        )
        for button in (*self.cards, self.next, self.fact):
            button.visible = False
        self.progress: ProgressDots = kit.progress_dots("progress", pygame.Rect(0, 0, 10, 10), total=figures)
        self.layer: ControlLayer = kit.layer((), layer_id="stelle.controls")
        self._choices: tuple[int, ...] = ()
        self._ready = False
        self._fact = False
        self._layout = layout
        self.relayout(layout)

    # -- geometry -----------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> None:
        """Goal strip centred in the top bar; progress dots at its end."""

        self._layout = layout
        height = layout.control_height(56, maximum=72)
        bar = layout.top_bar(height)
        dots_height = max(34, int(height * 0.66))
        dots_width = ProgressDots.preferred_width(self.progress.total, dots_height)
        (dots_rect,) = layout.row(bar, [dots_width], align=Align.END, height=dots_height)
        self.progress.rect = dots_rect
        banner_width = max(240, self.goal.preferred_width())
        free = pygame.Rect(bar.left, bar.top, max(0, dots_rect.left - layout.gap - bar.left), bar.height)
        banner = pygame.Rect(0, 0, min(banner_width, free.width), BANNER_HEIGHT)
        banner.center = (min(max(free.centerx, 512), free.right - banner.width // 2), bar.top + BANNER_HEIGHT // 2)
        self.goal.rect = banner
        self.layer.invalidation.invalidate()

    # -- round binding --------------------------------------------------------

    def bind_round(self, round_: SkyRound, goal_icon: pygame.Surface) -> None:
        """One focus target per star; reset the strip, cards and buttons."""

        half = STAR_TARGET // 2
        self.stars = [
            ExternalTarget(
                star_id(index),
                pygame.Rect(sky_point(point)[0] - half, sky_point(point)[1] - half, STAR_TARGET, STAR_TARGET),
                (lambda i=index: self._on_star(i)),
                focus_radius=STAR_SIZE // 2,
            )
            for index, point in enumerate(round_.figure.stars)
        ]
        self.goal.set_text("", icon=goal_icon)
        self._choices = ()
        self._ready = False
        self._fact = False
        self.relayout(self._layout)
        self.layer.set_targets(
            (*self.stars, *self.cards, self.goal, *self.goal.controls[1:], self.next, self.fact, self.progress)
        )
        self.sync(round_, refocus=True)

    def choice_value(self, index: int) -> int | None:
        if 0 <= index < len(self._choices):
            return self._choices[index]
        return None

    def sync(
        self, round_: SkyRound, *, refocus: bool = False, ready: bool | None = None, fact: bool | None = None
    ) -> None:
        """Mirror round state into control enablement/visibility (cheap).

        ``ready`` (set when the reveal starts) shows the next button only once
        the picture appears; ``fact`` shows the curiosity button for real
        constellations. Both persist until the next ``bind_round``.
        """

        if ready is not None:
            self._ready = ready
        if fact is not None:
            self._fact = fact

        playing = round_.phase is Phase.PLAYING
        for target in self.stars:
            target.enabled = playing
        choosing = round_.phase is Phase.CHOOSING
        if choosing and self._choices != round_.choices:
            self._choices = round_.choices
            for rect, button, value in zip(card_rects(len(round_.choices)), self.cards, round_.choices):
                button.rect = rect
                button.icon = self._art.card_numeral(value)
        for index, button in enumerate(self.cards):
            value = self.choice_value(index)
            button.visible = choosing and value is not None
            button.enabled = button.visible and value not in round_.rejected
        revealed = round_.phase is Phase.REVEALED
        self.next.visible = self.next.enabled = revealed and self._ready
        self.fact.visible = self.fact.enabled = revealed and self._ready and self._fact
        if self.goal.replay is not None:
            self.goal.replay.enabled = not revealed
        if refocus or not self._focused_is_live():
            self.focus_default(round_)
        self.layer.invalidation.invalidate()

    def focus_default(self, round_: SkyRound) -> None:
        """Neutral default focus: never the star the child should find."""

        if round_.phase is Phase.CHOOSING:
            for button in self.cards:
                if button.enabled:
                    self.layer.focus(button.control_id)
                    return
        if round_.phase is Phase.REVEALED and self.next.enabled:
            self.layer.focus("next")
            return
        if round_.last_lit is not None and round_.phase is Phase.PLAYING:
            self.layer.focus(star_id(round_.last_lit))
            return
        if self.goal.replay is not None and self.goal.replay.enabled:
            self.layer.focus(self.goal.replay.control_id)
            return
        self.layer.ensure_focus()

    def _focused_is_live(self) -> bool:
        focused = self.layer.focused_id
        if focused is None:
            return False
        target = self.layer.target(focused)
        return target.focusable and target.enabled

    def set_progress(self, done: int) -> None:
        self.progress.set_progress(done)
        self.layer.invalidation.invalidate()


__all__ = ["SkyControls", "card_id", "card_rects", "star_id"]
