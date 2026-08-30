"""Ocean entry: one connected ocean, salinity, fading light, and deep habitat."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        announce_focus_name,
        draw_entry_action_button,
        draw_focus_patch,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from .common import draw_centered_text, draw_presenter, focus_ring, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        announce_focus_name,
        draw_entry_action_button,
        draw_focus_patch,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class OceanDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    OceanDiscovery("water", "ocean.water", "encyclopedia.earth.ocean.water", (250, 190)),
    OceanDiscovery("salt", "ocean.salt", "encyclopedia.earth.ocean.salt", (755, 190)),
    OceanDiscovery("light", "ocean.light", "encyclopedia.earth.ocean.light", (250, 420)),
    OceanDiscovery("deep", "ocean.deep", "encyclopedia.earth.ocean.deep", (755, 420)),
)


class OceanDepthModel:
    """Own the finite teaching depth zones rather than a free unbounded camera."""

    ZONE_COUNT = 3

    def __init__(self) -> None:
        self.zone_index = 0

    def descend(self) -> None:
        self.zone_index = min(self.ZONE_COUNT - 1, self.zone_index + 1)

    def show_deep(self) -> None:
        self.zone_index = self.ZONE_COUNT - 1


class OceanPage(EncyclopediaPage):
    page_id = "earth.ocean"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._depth = OceanDepthModel()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "ocean.intro"
        self._world_age = 0.0
        self._salt_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.earth.ocean.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        disc = DISCOVERIES[self._selected]
        # Use helper that avoids ledger fragment
        cue = encyclopedia_focus_cue(disc.discovery_id, "name")
        if not announce_focus_name(self.context.audio, cue):
            announce_focus_name(self.context.audio, disc.cue_id)

    def _set_selected(self, index: int) -> None:
        index = max(0, min(len(DISCOVERIES) - 1, index))
        if index == self._selected:
            return
        self._selected = index
        self._announce_selected()

    def _trigger_main(self) -> None:
        self._activate(0)
        disc = DISCOVERIES[0]
        cue = encyclopedia_focus_cue(disc.discovery_id, "name")
        announce_focus_name(self.context.audio, cue)

    def update(self, dt: float) -> None:
        self._time += dt
        self._world_age = max(0.0, self._world_age - dt)
        self._salt_age = max(0.0, self._salt_age - dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            if event.kind is PageInputKind.POINTER_PRESS:
                if self._action_hit.collidepoint(point):
                    self._trigger_main()
                    return
                if self._arrow_left_hit.collidepoint(point):
                    self._set_selected(self._selected - 1)
                    return
                if self._arrow_right_hit.collidepoint(point):
                    self._set_selected(self._selected + 1)
                    return
            hit = next(
                (index for index, rect in enumerate(self._hotspots) if rect.collidepoint(point)),
                None,
            )
            if event.kind is PageInputKind.POINTER_MOVE and hit is not None and hit != self._selected:
                disc = DISCOVERIES[hit]
                cue = encyclopedia_focus_cue(disc.discovery_id, "name")
                announce_focus_name(self.context.audio, cue)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            if DISCOVERIES[self._selected].discovery_id == DISCOVERIES[0].discovery_id:
                self._trigger_main()
                return
            self._activate(self._selected)
            return
        prev = self._selected
        self._selected = grid_step(
            self._selected,
            event.command,
            columns=2,
            count=len(DISCOVERIES),
        )
        if self._selected != prev:
            self._announce_selected()
    def _activate(self, index: int) -> None:
        discovery = DISCOVERIES[index]
        self._caption_key = discovery.caption_key
        if discovery.discovery_id == "water":
            self._world_age = 4.2
        elif discovery.discovery_id == "salt":
            self._salt_age = 4.2
        elif discovery.discovery_id == "light":
            if self._depth.zone_index == OceanDepthModel.ZONE_COUNT - 1:
                self._depth.zone_index = 0
            else:
                self._depth.descend()
        else:
            self._depth.show_deep()
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        zone_colors = ((61, 155, 199), (39, 99, 151), (16, 38, 79))
        surface.fill(zone_colors[self._depth.zone_index])
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("ocean.title"),
            center=(500, 92),
            size=40,
            color=(244, 244, 225),
            role=FontRole.DISPLAY,
        )
        self._draw_water_column(surface)
        self._draw_hotspots(surface)
        for idx, rect in enumerate(self._hotspots):
            if idx == self._selected or idx == self._hovered:
                draw_focus_patch(surface, rect, active=True, radius=16, time=getattr(self, '_time', 0.0))
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_entry_action_button(
            surface, (512, 485), entry="ocean", time=getattr(self, '_time', 0.0), active=True
        )
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "tito",
            position=(925, 565),
            height=145,
            variant="surprised",
            fallback_color=(247, 151, 77),
        )

    def _draw_water_column(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(385, 145, 240, 330)
        pygame.draw.rect(surface, (19, 49, 87), panel, border_radius=26)
        bands = (
            (pygame.Rect(400, 160, 210, 92), (77, 174, 210)),
            (pygame.Rect(400, 252, 210, 96), (47, 111, 158)),
            (pygame.Rect(400, 348, 210, 112), (18, 38, 72)),
        )
        for rect, color in bands:
            pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, (239, 233, 199), panel, 3, border_radius=26)

        for index in range(7):
            end_y = 226 + index * 13
            pygame.draw.line(
                surface,
                (248, 230, 128),
                (427 + index * 25, 161),
                (439 + index * 19, end_y),
                max(1, 4 - index // 2),
            )

        for x, y, size in ((440, 212, 10), (514, 231, 8), (565, 192, 11)):
            pygame.draw.ellipse(surface, (241, 176, 77), (x - size, y - size // 2, size * 2, size))
            pygame.draw.polygon(surface, (241, 176, 77), [(x - size, y), (x - size - 8, y - 6), (x - size - 8, y + 6)])
        pygame.draw.ellipse(surface, (157, 188, 212), (462, 292, 45, 16))
        pygame.draw.polygon(surface, (157, 188, 212), [(462, 300), (448, 291), (448, 309)])
        pygame.draw.ellipse(surface, (116, 123, 154), (525, 389, 54, 20))
        pygame.draw.polygon(surface, (116, 123, 154), [(525, 399), (510, 389), (510, 409)])
        for x, y in ((447, 383), (488, 424), (592, 370)):
            pygame.draw.circle(surface, (109, 227, 213), (x, y), 4)

        selected_rect = bands[self._depth.zone_index][0]
        pygame.draw.rect(surface, (255, 221, 90), selected_rect.inflate(6, 6), 4, border_radius=8)

        if self._salt_age > 0:
            for index in range(24):
                x = 410 + (index * 41) % 190
                y = 176 + (index * 53) % 266
                pygame.draw.circle(surface, (239, 244, 233), (x, y), 2 + (index % 2))
            draw_centered_text(
                surface,
                self.context.typography,
                "≈35‰",
                center=(505, 474),
                size=18,
                color=(247, 239, 205),
                role=FontRole.CONTROL,
            )

        if self._world_age > 0:
            globe = (505, 311)
            pygame.draw.circle(surface, (79, 145, 201), globe, 74)
            pygame.draw.ellipse(surface, (101, 177, 99), (455, 268, 55, 34))
            pygame.draw.ellipse(surface, (101, 177, 99), (516, 321, 46, 29))
            pygame.draw.arc(surface, (246, 221, 113), (422, 228, 166, 166), 0.2, 5.9, 5)

        zone_labels = ("0–200m", "200–1000m", ">1000m")
        draw_centered_text(
            surface,
            self.context.typography,
            zone_labels[self._depth.zone_index],
            center=(505, 488),
            size=17,
            color=(246, 239, 209),
            role=FontRole.CONTROL,
        )

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (250, 247, 231), item.center, 37)
            pygame.draw.circle(surface, (52, 61, 66), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "water":
                pygame.draw.circle(surface, (76, 145, 202), (cx, cy), 21)
                pygame.draw.ellipse(surface, (103, 175, 101), (cx - 18, cy - 6, 22, 14))
            elif item.discovery_id == "salt":
                for ox, oy in ((-13, -9), (10, -10), (-5, 12), (16, 9)):
                    pygame.draw.circle(surface, (103, 158, 194), (cx + ox, cy + oy), 5)
            elif item.discovery_id == "light":
                pygame.draw.circle(surface, (246, 204, 73), (cx - 12, cy - 12), 9)
                for off in (-9, 2, 13):
                    pygame.draw.line(surface, (94, 159, 196), (cx - 2 + off, cy), (cx - 8 + off, cy + 24), 3)
            else:
                pygame.draw.rect(surface, (20, 43, 79), (cx - 24, cy - 22, 48, 44), border_radius=12)
                pygame.draw.circle(surface, (102, 224, 211), (cx + 4, cy), 4)
                pygame.draw.ellipse(surface, (142, 155, 178), (cx - 16, cy + 5, 31, 11))
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (250, 247, 231), panel, border_radius=22)
        pygame.draw.rect(surface, (52, 61, 66), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (48, 54, 58))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (48, 54, 58))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
