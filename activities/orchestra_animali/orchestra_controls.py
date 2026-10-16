"""Shared control-kit wiring for the Animal Band (ADR 0037).

Every interactive element goes through ``greia_platform.activity_controls``:
the six musicians and the eight xylophone bars are ``ExternalTarget``s (the
Activity draws them; the kit supplies keyboard / D-pad / stick focus and the
focus ring), "play along with my recording" is a round ``IconButton`` with the
shared audio-creation pictogram plus a play/pause ``IconButton``, loud/soft
(mouse | lion) and slow/fast (snail | horse) are two picture ``ToolStrip``s,
and the concert's echo invitations are ``ProgressDots``. There is no text on
the play screen. Pointer presses on musicians/bars are handled by the app on
press (music must sound on touch-down); the targets here serve focus input.
"""

from __future__ import annotations

from collections.abc import Callable

import pygame

from greia_platform.activity_controls import (
    Align,
    BodyShape,
    ControlKit,
    ControlLayer,
    ControlLayout,
    ExternalTarget,
    IconButton,
    ProgressDots,
    ToolStrip,
)

if __package__:
    from .orchestra_art import OrchestraArt
    from .orchestra_content import BAND, SESSION_ECHOES, Dynamics, Tempo
    from .orchestra_layout import BAR_RECTS, MUSICIAN_HIT
else:  # pragma: no cover - runtime/script fallback
    from orchestra_art import OrchestraArt
    from orchestra_content import BAND, SESSION_ECHOES, Dynamics, Tempo
    from orchestra_layout import BAR_RECTS, MUSICIAN_HIT

TOGGLE_ICON = 46


def musician_id(index: int) -> str:
    return f"musician.{index}"


def bar_id(index: int) -> str:
    return f"bar.{index}"


class OrchestraControls:
    """Own the kit controls and the ``ControlLayer`` for the band stage."""

    def __init__(
        self,
        kit: ControlKit,
        art: OrchestraArt,
        layout: ControlLayout,
        *,
        on_musician: Callable[[int], object],
        on_bar: Callable[[int], object],
        on_import: Callable[[], object],
        on_play: Callable[[], object],
        on_dynamics: Callable[[Dynamics], object],
        on_tempo: Callable[[Tempo], object],
        dynamics: Dynamics = Dynamics.LOUD,
        tempo: Tempo = Tempo.SLOW,
    ) -> None:
        self._kit = kit
        self.musicians = tuple(
            ExternalTarget(musician_id(index), rect, (lambda i=index: on_musician(i)), focus_radius=26)
            for index, rect in enumerate(MUSICIAN_HIT)
        )
        self.bars = tuple(
            ExternalTarget(bar_id(index), rect, (lambda i=index: on_bar(i)), focus_radius=14)
            for index, rect in enumerate(BAR_RECTS)
        )
        self.import_button: IconButton = kit.icon_button(
            "import",
            pygame.Rect(0, 0, 64, 64),
            icon=art.art.image("ui.pictogram.creation", 44, variant="audio"),
            on_activate=on_import,
        )
        self._play_icon = kit.glyph("play", 34)
        self._pause_icon = kit.glyph("pause", 34)
        self.play_button: IconButton = kit.icon_button(
            "play",
            pygame.Rect(0, 0, 64, 64),
            icon=self._play_icon,
            on_activate=on_play,
            enabled=False,
        )
        self.volume: ToolStrip = kit.tool_strip(
            "volume",
            [
                (Dynamics.SOFT.value, "", art.toggle_icon("soft", TOGGLE_ICON)),
                (Dynamics.LOUD.value, "", art.toggle_icon("loud", TOGGLE_ICON)),
            ],
            shape=BodyShape.TILE,
            selected=dynamics.value,
            on_select=lambda value: on_dynamics(Dynamics(value)),
        )
        self.tempo: ToolStrip = kit.tool_strip(
            "tempo",
            [
                (Tempo.SLOW.value, "", art.toggle_icon("slow", TOGGLE_ICON)),
                (Tempo.FAST.value, "", art.toggle_icon("fast", TOGGLE_ICON)),
            ],
            shape=BodyShape.TILE,
            selected=tempo.value,
            on_select=lambda value: on_tempo(Tempo(value)),
        )
        self.progress: ProgressDots = kit.progress_dots(
            "progress", pygame.Rect(0, 0, 10, 10), total=SESSION_ECHOES
        )
        self.layer: ControlLayer = kit.layer(
            (
                *self.musicians,
                *self.bars,
                self.import_button,
                self.play_button,
                *self.volume.controls,
                *self.tempo.controls,
                self.progress,
            ),
            layer_id="orchestra.controls",
        )
        self.relayout(layout)

    # -- geometry ------------------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> None:
        """Top bar beside protected chrome: play-along | progress | loud/soft, slow/fast."""

        height = layout.control_height(60, maximum=72)
        bar = layout.top_bar(height)
        left = layout.row(bar, [height, height], align=Align.START, height=height)
        self.import_button.rect, self.play_button.rect = left
        right = layout.row(bar, [height, height, 16, height, height], align=Align.END, gap=6, height=height)
        for slot, rect in zip((*self.volume.controls, *self.tempo.controls), (*right[:2], *right[3:])):
            slot.rect = rect
        dots_h = max(34, int(height * 0.62))
        dots_w = ProgressDots.preferred_width(SESSION_ECHOES, dots_h)
        span_left, span_right = left[-1].right, right[0].left
        center = (span_left + span_right) // 2
        self.progress.rect = pygame.Rect(center - dots_w // 2, bar.centery - dots_h // 2, dots_w, dots_h)
        self.layer.invalidation.invalidate()

    # -- state sync --------------------------------------------------------------------

    def sync(
        self,
        *,
        stage_live: bool,
        free_play: bool,
        can_import: bool,
        import_state: str,
        has_track: bool,
        track_playing: bool,
        completed: int,
    ) -> None:
        """Mirror app state into enablement (cheap; called on state changes)."""

        for target in (*self.musicians, *self.bars):
            target.enabled = stage_live
        self.import_button.enabled = free_play and can_import and import_state != "pending"
        self.import_button.selected = import_state in {"pending", "imported"}
        self.play_button.enabled = has_track and (free_play or track_playing)
        icon = self._pause_icon if track_playing else self._play_icon
        if icon is not None and self.play_button.icon is not icon:
            self.play_button.icon = icon
        self.play_button.selected = track_playing
        self.progress.set_progress(completed)
        self.layer.invalidation.invalidate()

    def set_toggles(self, dynamics: Dynamics, tempo: Tempo) -> None:
        self.volume.select(dynamics.value)
        self.tempo.select(tempo.value)
        self.layer.invalidation.invalidate()

    def focus_musician(self, index: int) -> None:
        if 0 <= index < len(BAND):
            self.layer.focus(musician_id(index))

    def pointer_target(self, point: tuple[int, int]) -> tuple[str, int] | None:
        """Return ``("musician"|"bar", index)`` under ``point`` when it is live."""

        for index, target in enumerate(self.bars):
            if target.enabled and target.contains(point):
                return ("bar", index)
        for index, target in enumerate(self.musicians):
            if target.enabled and target.contains(point):
                return ("musician", index)
        return None


__all__ = ["OrchestraControls", "bar_id", "musician_id"]
