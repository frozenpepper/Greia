"""Frame composition for My Greia (blits only).

The room colour fills the screen, the live Home preview sits in a cream
picture frame on the left, the choices stand on a soft panel on the right,
and kit controls draw on top (chosen tiles get the shared check glyph; the
focus ring is drawn last so it is never hidden). Frame and panel bodies come
from the kit painter cache; nothing here decodes, scales or renders text per
frame.
"""

from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.activity_controls import BodyShape, ControlKit, KitControl, mix

if not __package__:
    __package__ = "activities.workshop_settings"  # type: ignore[assignment]

try:
    from .workshop_art import MyGreiaArt
    from .workshop_content import CAPTION_CREAM
    from .workshop_controls import MyGreiaControls
    from .workshop_model import MyGreiaModel
    from .workshop_preview import HomePreview
    from .workshop_services import MyGreiaChoices
except ImportError:
    from workshop_art import MyGreiaArt  # type: ignore[no-redef]
    from workshop_content import CAPTION_CREAM  # type: ignore[no-redef]
    from workshop_controls import MyGreiaControls  # type: ignore[no-redef]
    from workshop_model import MyGreiaModel  # type: ignore[no-redef]
    from workshop_preview import HomePreview  # type: ignore[no-redef]
    from workshop_services import MyGreiaChoices  # type: ignore[no-redef]

FRAME_BORDER = 12
WHITE = (255, 255, 255)


class MyGreiaRenderer:
    """Draw one My Greia frame from the model, preview and controls."""

    def __init__(self, kit: ControlKit, art: MyGreiaArt, preview: HomePreview, controls: MyGreiaControls) -> None:
        self._kit = kit
        self._art = art
        self._preview = preview
        self._controls = controls

    def draw(
        self,
        surface: pygame.Surface,
        model: MyGreiaModel,
        choices: MyGreiaChoices,
        *,
        custom: Path | None = None,
    ) -> None:
        look = model.look
        room = choices.background(look.background)
        surface.fill(room)
        geometry = self._controls.geometry
        painter = self._kit.painter

        panel = geometry.panel
        panel_body = painter.body(
            BodyShape.PANEL, panel.size, mix(room, WHITE, 0.55), lip=0, contour=mix(room, (75, 55, 47), 0.35), contour_width=2,
            highlight=False,
        )
        surface.blit(panel_body, panel.topleft)

        frame = geometry.preview.inflate(2 * FRAME_BORDER, 2 * FRAME_BORDER)
        frame_body = painter.body(
            BodyShape.PANEL, (frame.width, frame.height + 8), CAPTION_CREAM, lip=8, contour_width=3, highlight=False,
        )
        surface.blit(frame_body, frame.topleft)
        self._preview.resize(geometry.preview.size)
        self._preview.draw(surface, geometry.preview.topleft, look, choices, custom=custom)

        layer = self._controls.layer
        for item in layer.targets:
            if isinstance(item, KitControl):
                item.draw(surface)
        self._draw_checks(surface)
        layer.draw_focus(surface)
        layer.invalidation.mark_drawn()

    def _draw_checks(self, surface: pygame.Surface) -> None:
        for tile in self._controls.tiles:
            if not tile.selected:
                continue
            rect = tile.rect
            size = max(22, min(38, round(min(rect.width, rect.height) * 0.32)))
            badge = self._art.check_badge(size)
            surface.blit(badge, badge.get_rect(center=(rect.right - size // 4, rect.top + size // 4)))


__all__ = ["MyGreiaRenderer"]
