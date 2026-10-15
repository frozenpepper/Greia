"""Shared control-kit wiring for Pasticceria Magica (ADR 0037 pilot).

Mode tabs are a ``ToolStrip``; the score/stars HUD is two ``HudChip``s; pantry
toppings and pattern candidates are tile ``IconButton``s; Clear and Serve are
captioned tile buttons; feedback is a ``PromptBanner``. Every control is
focusable from the keyboard/controller through the shared ``ControlLayer``.
Rules stay in ``PasticceriaModel``; the app owns what each control does.
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
    HudChip,
    IconButton,
    PromptBanner,
    ToolStrip,
)
from greia_platform.localization import LocalizationError

if __package__:
    from .pasticceria_content import TOPPINGS
else:
    from pasticceria_content import TOPPINGS

MODES = ("orders", "patterns", "free")
_MODE_ICONS = {"orders": "🧁", "patterns": "🍪", "free": "🎨"}

# Gameplay geometry in the 1024x600 reference canvas (unchanged rules/targets).
TOPPING_RECTS: tuple[pygame.Rect, ...] = tuple(
    pygame.Rect(720 + (index % 2) * 135, 140 + (index // 2) * 95, 125, 85)
    for index in range(len(TOPPINGS))
)
CANDIDATE_RECTS: tuple[pygame.Rect, ...] = tuple(
    pygame.Rect(330 + index * 135, 380, 110, 110) for index in range(3)
)
CLEAR_RECT = pygame.Rect(712, 458, 128, 108)
SERVE_RECT = pygame.Rect(852, 458, 150, 108)
FEEDBACK_RECT = pygame.Rect(166, 504, 524, 62)
CAST_MIDBOTTOM = (86, 598)
CAST_HEIGHT = 168


class PasticceriaControls:
    """Own the bakery's kit controls and their ``ControlLayer``."""

    def __init__(
        self,
        kit: ControlKit,
        resources,
        layout: ControlLayout,
        *,
        mode: str,
        on_mode: Callable[[str], object],
        on_topping: Callable[[str], object],
        on_candidate: Callable[[int], object],
        on_clear: Callable[[], object],
        on_serve: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._resources = resources
        self._layout = layout
        self.tabs: ToolStrip = kit.tool_strip(
            "mode",
            [(mode_id, self._label(f"tab.{mode_id}"), kit.text_icon(_MODE_ICONS[mode_id], 30)) for mode_id in MODES],
            selected=mode,
            on_select=on_mode,
        )
        self.stars: HudChip = kit.hud_chip("hud.stars", pygame.Rect(0, 0, 120, 56), icon=kit.star(40))
        self.score: HudChip = kit.hud_chip("hud.score", pygame.Rect(0, 0, 140, 56), icon=kit.glyph("trophy", 38))
        self.toppings: tuple[IconButton, ...] = tuple(
            kit.icon_button(
                f"topping.{topping_id}",
                rect,
                icon=kit.text_icon(icon, 50),
                shape=BodyShape.TILE,
                on_activate=(lambda chosen=topping_id: on_topping(chosen)),
            )
            for (topping_id, icon, _), rect in zip(TOPPINGS, TOPPING_RECTS)
        )
        self.candidates: tuple[IconButton, ...] = tuple(
            kit.icon_button(
                f"candidate.{index}",
                rect,
                icon=None,
                shape=BodyShape.TILE,
                on_activate=(lambda chosen=index: on_candidate(chosen)),
            )
            for index, rect in enumerate(CANDIDATE_RECTS)
        )
        self.clear: IconButton = kit.icon_button(
            "clear",
            CLEAR_RECT,
            icon=kit.glyph("clear", 50),
            caption=self._label("action.clear"),
            shape=BodyShape.TILE,
            on_activate=on_clear,
        )
        self.serve: IconButton = kit.icon_button(
            "serve",
            SERVE_RECT,
            icon=kit.glyph("bell", 54),
            caption=self._label("action.serve"),
            shape=BodyShape.TILE,
            role=ButtonRole.PRIMARY,
            on_activate=on_serve,
        )
        self.feedback: PromptBanner = kit.prompt_banner("feedback", FEEDBACK_RECT, text_size=26)
        self.feedback.visible = False
        self.layer: ControlLayer = kit.layer(
            (
                *self.tabs.controls,
                self.stars,
                self.score,
                *self.toppings,
                *self.candidates,
                self.clear,
                self.serve,
                self.feedback,
            ),
            layer_id="pasticceria.controls",
        )
        self._candidate_symbols: tuple[str, ...] = ()
        self._mode = mode
        self.relayout(layout)
        self.sync_mode(mode)
        self.layer.focus(f"mode.{mode}")

    def _label(self, key: str) -> str:
        if self._resources is None:
            return ""
        try:
            return self._resources.text(key).strip()
        except LocalizationError:
            return ""

    # -- geometry --
    def relayout(self, layout: ControlLayout) -> None:
        """Fit tabs (left) and HUD chips (right) into the bar beside the chrome."""

        self._layout = layout
        height = layout.control_height(64, maximum=72)
        bar = layout.top_bar(height)
        chip_h = max(44, height - 10)
        for chip, digits in ((self.stars, 2), (self.score, 3)):
            chip.rect = pygame.Rect(0, 0, 10, chip_h)
            chip.rect = pygame.Rect(0, 0, chip.preferred_width(digits=digits), chip_h)
        chip_widths = [self.stars.rect.width, self.score.rect.width]
        chip_rects = layout.row(bar, chip_widths, align=Align.END, height=chip_h, gap=8)
        self.stars.rect, self.score.rect = chip_rects
        tabs_bar = pygame.Rect(bar.left, bar.top, chip_rects[0].left - 18 - bar.left, height)
        for slot in self.tabs.slots:
            slot.rect = pygame.Rect(0, 0, 10, height)
        preferred = [slot.preferred_width() for slot in self.tabs.slots]
        minimum = [slot.compact_width() for slot in self.tabs.slots]
        widths, compact = layout.fit(tabs_bar.width, preferred, minimum, 10)
        for slot, rect in zip(self.tabs.slots, layout.row(tabs_bar, widths, gap=10)):
            slot.rect = rect
            slot.compact = compact
        self.layer.invalidation.invalidate()

    # -- state --
    def sync_mode(self, mode: str) -> None:
        if mode != self.tabs.selected:
            self.tabs.select(mode)
        self._mode = mode
        building = mode in {"orders", "free"}
        for button in (*self.toppings, self.clear, self.serve):
            button.visible = building
        for button in self.candidates:
            button.visible = mode == "patterns"
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()

    def sync(self, model) -> None:
        """Mirror model values into controls; content-keyed caches make it cheap."""

        if model.mode != self._mode:
            self.sync_mode(model.mode)
        self.stars.value = model.stars
        self.score.value = model.score
        if model.mode == "patterns":
            _, _, candidates = model.current_pattern
            symbols = tuple(candidates)
            if symbols != self._candidate_symbols:
                self._candidate_symbols = symbols
                for button, symbol in zip(self.candidates, symbols):
                    button.icon = self._kit.text_icon(symbol, 52)
        text = model.feedback_text or ""
        self.feedback.visible = bool(text)
        if text and text != self.feedback.text:
            self.feedback.set_text(text)


__all__ = [
    "CANDIDATE_RECTS",
    "CAST_HEIGHT",
    "CAST_MIDBOTTOM",
    "CLEAR_RECT",
    "FEEDBACK_RECT",
    "MODES",
    "PasticceriaControls",
    "SERVE_RECT",
    "TOPPING_RECTS",
]
