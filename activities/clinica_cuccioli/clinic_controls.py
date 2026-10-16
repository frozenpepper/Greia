"""Shared control-kit wiring for Little Vet Clinic (ADR 0037).

Every interactive element goes through ``greia_platform.activity_controls``:

* the "where does it hurt?" hotspots on the patient (ears, tummy, paw) are
  ``ExternalTarget``s, live only while the child is looking;
* the tool tray is a row of kit ``IconButton`` tiles (one tool picture each,
  no words), live only while the child is caring;
* progress through the clinic day is ``ProgressDots``.

Pointer, touch, keyboard and controller therefore share one focus ring and
one activation path. No control ever marks the right answer: hotspots and
tiles look the same whether or not they are the next step.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

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
)

if __package__:
    from .clinic_content import PATIENTS_PER_DAY, BodyPart, Tool
    from .clinic_layout import part_rects, tile_rects
    from .clinic_model import ClinicDay, Phase
else:
    from clinic_content import PATIENTS_PER_DAY, BodyPart, Tool
    from clinic_layout import part_rects, tile_rects
    from clinic_model import ClinicDay, Phase


def tool_id(tool: Tool) -> str:
    return f"tool.{tool.value}"


class ClinicControls:
    """Own the kit controls and the ``ControlLayer`` for the clinic screen."""

    def __init__(
        self,
        kit: ControlKit,
        layout: ControlLayout,
        *,
        tool_icons: Mapping[Tool, pygame.Surface | None],
        on_part: Callable[[BodyPart, tuple[int, int]], object],
        on_tool: Callable[[Tool], object],
    ) -> None:
        self._kit = kit
        self._tool_icons = tool_icons
        self._on_part = on_part
        self._on_tool = on_tool
        self.progress: ProgressDots = kit.progress_dots(
            "progress", pygame.Rect(0, 0, 10, 10), total=PATIENTS_PER_DAY
        )
        self.parts: dict[str, ExternalTarget] = {}
        self._part_kinds: dict[str, BodyPart] = {}
        self.tiles: dict[Tool, IconButton] = {}
        self.tray: tuple[Tool, ...] = ()
        self.layer: ControlLayer = kit.layer((self.progress,), layer_id="clinic.controls")
        self._phase: Phase | None = None
        self.relayout(layout)

    # -- geometry --------------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> None:
        """Progress dots on the top bar, right of the protected chrome."""

        height = layout.control_height(52, maximum=64)
        bar = layout.top_bar(height)
        dots_height = max(34, int(height * 0.7))
        dots_width = ProgressDots.preferred_width(PATIENTS_PER_DAY, dots_height)
        (dots_rect,) = layout.row(bar, [dots_width], align=Align.END, height=dots_height)
        self.progress.rect = pygame.Rect(dots_rect.x, bar.centery - dots_height // 2, dots_width, dots_height)
        self.layer.invalidation.invalidate()

    # -- per patient -------------------------------------------------------------

    def show_patient(self, day: ClinicDay, tray: Sequence[Tool]) -> None:
        """Build the hotspots for this patient and lay out its tool tray."""

        case = day.case
        hurt_pose = case.species.mood_variants and day.look.variant == "hurt"
        self.parts = {}
        self._part_kinds = {}
        for control_id, (part, rect) in part_rects(case.species, hurt_pose=hurt_pose).items():
            self.parts[control_id] = ExternalTarget(
                control_id,
                rect,
                (lambda chosen=part, spot=rect.center: self._on_part(chosen, spot)),
                enabled=False,
                focus_radius=rect.width // 2,
            )
            self._part_kinds[control_id] = part
        if tuple(tray) != self.tray:
            self.tray = tuple(tray)
            self.tiles = {
                tool: self._kit.icon_button(
                    tool_id(tool),
                    rect,
                    icon=self._tool_icons.get(tool),
                    shape=BodyShape.TILE,
                    on_activate=(lambda chosen=tool: self._on_tool(chosen)),
                    enabled=False,
                )
                for tool, rect in zip(self.tray, tile_rects(len(self.tray)))
            }
        focused = self.layer.focused_id
        visible = self.layer.focus_visible
        self.layer.set_targets((*self.parts.values(), *self.tiles.values(), self.progress))
        if focused is not None:
            self.layer.focus(focused, visible=visible)
        self._phase = None

    def tile_center(self, tool: Tool) -> tuple[int, int] | None:
        tile = self.tiles.get(tool)
        return tile.rect.center if tile is not None else None

    # -- state sync ---------------------------------------------------------------

    def sync(self, day: ClinicDay, *, busy: bool) -> None:
        """Mirror the day into control enablement (cheap; no answer marking)."""

        self.progress.set_progress(day.healed_count if day.phase is not Phase.DONE else PATIENTS_PER_DAY)
        # Tiles stay lit through the short care animations (input is simply
        # ignored while busy) so the tray does not flicker on every step.
        finding = day.phase is Phase.FIND and not busy
        caring = day.phase is Phase.CARE
        for target in self.parts.values():
            target.enabled = finding
        for tile in self.tiles.values():
            tile.enabled = caring
        if day.phase is not self._phase:
            self._phase = day.phase
            self._focus_default(day)
        elif not self._focused_is_live():
            self._focus_default(day)
        self.layer.invalidation.invalidate()

    def _focus_default(self, day: ClinicDay) -> None:
        """Park focus on a fixed, neutral place (never on the answer)."""

        if day.phase is Phase.FIND and self.parts:
            focused = self.layer.focused_id
            if focused not in self.parts:
                self.layer.focus("part.ear_left")
        elif day.phase is Phase.CARE and self.tiles:
            focused = self.layer.focused_id
            if focused is None or not focused.startswith("tool.") or not self._focused_is_live():
                self.layer.focus(tool_id(self.tray[0]))
        self.layer.ensure_focus()

    def _focused_is_live(self) -> bool:
        focused = self.layer.focused_id
        if focused is None:
            return False
        try:
            target = self.layer.target(focused)
        except KeyError:
            return False
        return target.focusable and target.enabled

    # -- drawing ---------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, offsets: Mapping[str, tuple[int, int]] | None = None) -> None:
        """Draw the layer; a demonstrated or rejected tile is briefly offset."""

        moved: list[tuple[IconButton, pygame.Rect]] = []
        for control_id, (dx, dy) in (offsets or {}).items():
            tile = next((t for t in self.tiles.values() if t.control_id == control_id), None)
            if tile is not None and (dx or dy):
                moved.append((tile, tile.rect))
                tile.rect = tile.rect.move(dx, dy)
        self.layer.draw(surface)
        for tile, rect in moved:
            tile.rect = rect


__all__ = ["ClinicControls", "tool_id"]
