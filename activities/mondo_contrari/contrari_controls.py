"""Shared control-kit wiring for Mondo Contrari (ADR 0037).

The two choices of the current pair scene (sky/grass, box/ball, left/right
picture, upper/lower lane) are ``ExternalTarget``s, so pointer, touch,
keyboard, D-pad, stick and the south button all reach them with the shared
focus ring. The replay-voice button is a round kit ``IconButton`` (shared
listen glyph), progress is ``ProgressDots`` (one dot per pair) and the word
caption is a display-only ``PromptBanner`` that appears only after the child
has made the concept happen. Nothing is placed in the protected Home/Back
region: the top bar comes from ``ControlLayout``.
"""

from __future__ import annotations

from collections.abc import Callable

import pygame

from greia_platform.activity_controls import (
    Align,
    ControlKit,
    ControlLayer,
    ControlLayout,
    ExternalTarget,
    IconButton,
    ProgressDots,
    PromptBanner,
)

CHOICE_IDS = ("choice.0", "choice.1")
CAPTION_WIDTH = 320


class ContrariControls:
    """Own the kit controls and the ``ControlLayer`` of the play screen."""

    def __init__(
        self,
        kit: ControlKit,
        layout: ControlLayout,
        *,
        total: int,
        on_choice: Callable[[int], object],
        on_listen: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._on_choice = on_choice
        self.choices: tuple[ExternalTarget, ExternalTarget] = self._targets(
            (pygame.Rect(0, 0, 10, 10), pygame.Rect(20, 0, 10, 10))
        )
        self.listen: IconButton = kit.icon_button(
            "listen",
            pygame.Rect(0, 0, 64, 64),
            icon=kit.glyph("listen", 40),
            on_activate=on_listen,
        )
        self.progress: ProgressDots = kit.progress_dots("progress", pygame.Rect(0, 0, 10, 10), total=total)
        self.caption: PromptBanner = kit.prompt_banner(
            "caption", pygame.Rect(0, 0, CAPTION_WIDTH, 60), icon=kit.star(40), text_size=36
        )
        self.caption.visible = False
        self.layer: ControlLayer = kit.layer(self._all(), layer_id="contrari.controls")
        self._layout = layout
        self.relayout(layout)

    def _targets(self, rects: tuple[pygame.Rect, pygame.Rect]) -> tuple[ExternalTarget, ExternalTarget]:
        return tuple(  # type: ignore[return-value]
            ExternalTarget(CHOICE_IDS[index], rect, (lambda i=index: self._on_choice(i)), focus_radius=28)
            for index, rect in enumerate(rects)
        )

    def _all(self):
        return (*self.choices, self.caption, self.listen, self.progress)

    # -- geometry --------------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> None:
        """Top bar beside protected chrome: caption centred, replay + dots at the end."""

        self._layout = layout
        height = layout.control_height(56, maximum=72)
        bar = layout.top_bar(height)
        dots_height = max(34, int(height * 0.66))
        dots_width = ProgressDots.preferred_width(self.progress.total, dots_height)
        listen_rect, dots_rect = layout.row(bar, [height, dots_width], align=Align.END, height=height)
        self.listen.rect = listen_rect
        self.progress.rect = pygame.Rect(dots_rect.x, dots_rect.centery - dots_height // 2, dots_width, dots_height)
        caption = pygame.Rect(0, bar.y, CAPTION_WIDTH, height)
        caption.centerx = 512
        caption = layout.clear_of_chrome(caption)
        if caption.right > listen_rect.left - 8:
            caption.right = listen_rect.left - 8
        self.caption.rect = caption
        self.layer.invalidation.invalidate()

    def set_total(self, total: int) -> None:
        if total != self.progress.total:
            self.progress.total = total
            self.relayout(self._layout)

    def set_scene_targets(self, rects: tuple[pygame.Rect, pygame.Rect]) -> None:
        """Point the two choice targets at the current scene's rects."""

        focused = self.layer.focused_id
        self.choices = self._targets(rects)
        self.layer.set_targets(self._all())
        if focused is not None:
            self.layer.focus(focused)
        self.layer.invalidation.invalidate()

    # -- state ----------------------------------------------------------------

    def set_answering(self, answering: bool) -> None:
        for target in self.choices:
            target.enabled = answering
        self.layer.invalidation.invalidate()

    def show_caption(self, text: str | None) -> None:
        if text:
            self.caption.set_text(text)
            self.caption.visible = True
        else:
            self.caption.visible = False
        self.layer.invalidation.invalidate()

    def focus_default(self) -> None:
        """Keyboard/controller focus starts on choice 0 (a fixed place, not the answer)."""

        if not self.layer.focus(CHOICE_IDS[0]):
            self.layer.ensure_focus()


__all__ = ["CHOICE_IDS", "ContrariControls"]
