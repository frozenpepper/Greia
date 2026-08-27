"""Volcano final-entry pilot: magma, vents, gas pressure and eruption styles."""
from __future__ import annotations
from dataclasses import dataclass
import math
import pygame
from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from .common import draw_centered_text, draw_presenter, focus_ring, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class VolcanoDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    VolcanoDiscovery("magma", "volcano.magma", "encyclopedia.earth.volcano.magma", (260, 205)),
    VolcanoDiscovery("vent", "volcano.vent", "encyclopedia.earth.volcano.vent", (745, 205)),
    VolcanoDiscovery("style", "volcano.style", "encyclopedia.earth.volcano.style", (260, 410)),
    VolcanoDiscovery("ash", "volcano.ash", "encyclopedia.earth.volcano.ash", (745, 410)),
)
_FLOW = "flow"
_EXPLOSIVE = "explosive"


class VolcanoModel:
    """Own bounded teaching state; this is not a physical volcano simulation."""

    def __init__(self) -> None:
        self.pressure = 0.15
        self.eruption_style = _FLOW
        self.eruption_age = 0.0
        self.vent_age = 0.0
        self.ash_age = 0.0

    def update(self, dt: float) -> None:
        self.pressure += (0.15 - self.pressure) * min(1.0, dt * 0.35)
        self.eruption_age = max(0.0, self.eruption_age - dt)
        self.vent_age = max(0.0, self.vent_age - dt)
        self.ash_age = max(0.0, self.ash_age - dt)

    def pump_magma(self) -> None:
        self.pressure = min(1.0, self.pressure + 0.28)
        if self.pressure >= 0.95:
            self.erupt()

    def show_vent(self) -> None:
        self.vent_age = 3.0
        self.pressure = min(1.0, self.pressure + 0.12)

    def toggle_style(self) -> None:
        self.eruption_style = _EXPLOSIVE if self.eruption_style == _FLOW else _FLOW
        self.pressure = 1.0 if self.eruption_style == _EXPLOSIVE else 0.72
        self.erupt()

    def show_ash(self) -> None:
        self.eruption_style = _EXPLOSIVE
        self.ash_age = 3.2
        self.pressure = 1.0
        self.erupt()

    def erupt(self) -> None:
        self.eruption_age = 2.6
        if self.eruption_style == _EXPLOSIVE:
            self.ash_age = max(self.ash_age, 2.6)
        self.pressure = 0.22


class VolcanoPage(EncyclopediaPage):
    page_id = "earth.volcano"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._model = VolcanoModel()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "volcano.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.earth.volcano.intro")

    def update(self, dt: float) -> None:
        self._time += dt
        self._model.update(dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {PageInputKind.POINTER_MOVE, PageInputKind.POINTER_PRESS}:
            point = (int(event.position[0]), int(event.position[1]))
            hit = next((index for index, rect in enumerate(self._hotspots) if rect.collidepoint(point)), None)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._selected = hit
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            self._activate(self._selected)
            return
        self._selected = grid_step(self._selected, event.command, columns=2, count=len(DISCOVERIES))

    def _activate(self, index: int) -> None:
        discovery = DISCOVERIES[index]
        self._caption_key = discovery.caption_key
        if discovery.discovery_id == "magma":
            self._model.pump_magma()
        elif discovery.discovery_id == "vent":
            self._model.show_vent()
        elif discovery.discovery_id == "style":
            self._model.toggle_style()
        else:
            self._model.show_ash()
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((187, 224, 235))
        pygame.draw.rect(surface, (153, 117, 82), (0, 345, 1024, 255))
        pygame.draw.rect(surface, (115, 83, 60), (0, 455, 1024, 145))
        draw_centered_text(
            surface, self.context.typography, self.context.resources.text("volcano.title"),
            center=(500, 92), size=40, color=self.context.palette.ink, role=FontRole.DISPLAY,
        )
        self._draw_cross_section(surface)
        self._draw_hotspots(surface)
        self._draw_caption(surface)
        draw_presenter(
            surface, self.context.visuals, "tito", position=(925, 565), height=142,
            variant="surprised", fallback_color=(247, 151, 77),
        )

    def _draw_cross_section(self, surface: pygame.Surface) -> None:
        cx = 505
        crater_y = 205
        pygame.draw.polygon(surface, (105, 91, 79), [(355, 345), (470, 185), (540, 185), (655, 345)])
        pygame.draw.polygon(surface, (137, 105, 83), [(445, 225), (470, 185), (540, 185), (565, 225)])
        pygame.draw.ellipse(surface, (78, 68, 61), (470, 174, 70, 24))
        chamber = pygame.Rect(435, 430, 140, 74)
        pygame.draw.ellipse(surface, (221, 78, 48), chamber)
        glow = int(12 * self._model.pressure)
        pygame.draw.ellipse(surface, (246, 135, 55), chamber.inflate(glow, glow // 2), max(3, 8 - glow // 3))
        vent_color = (246, 119, 45) if self._model.vent_age > 0 or self._model.eruption_age > 0 else (168, 84, 58)
        pygame.draw.line(surface, vent_color, (505, 440), (505, crater_y + 2), 18)
        for index in range(4):
            filled = (index + 1) / 4 <= self._model.pressure + 0.02
            color = (255, 190, 73) if filled else (102, 79, 65)
            pygame.draw.circle(surface, color, (455 + index * 34, 525), 11)
            pygame.draw.circle(surface, (80, 61, 53), (455 + index * 34, 525), 11, 2)
        if self._model.eruption_age > 0:
            intensity = min(1.0, self._model.eruption_age / 1.2)
            if self._model.eruption_style == _FLOW:
                pygame.draw.line(surface, (232, 86, 43), (520, 205), (585, 280), 18)
                pygame.draw.line(surface, (242, 112, 43), (585, 280), (625, 342), 13)
            else:
                height = 80 + int(35 * intensity)
                pygame.draw.polygon(surface, (239, 89, 39), [(490, 195), (505, 195 - height), (520, 195)])
        if self._model.ash_age > 0:
            spread = 1.0 - min(1.0, self._model.ash_age / 3.2)
            for index in range(22):
                angle = index * 0.77 + self._time * 0.23
                radius = 18 + int(spread * (35 + index % 6 * 9))
                x = cx + int(math.cos(angle) * radius * 1.5)
                y = 135 + int(math.sin(angle) * radius * 0.55) - index % 3 * 4
                pygame.draw.circle(surface, (86, 82, 79), (x, y), 4 + index % 4)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (255, 249, 229), item.center, 37)
            pygame.draw.circle(surface, (75, 62, 53), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "magma":
                pygame.draw.ellipse(surface, (225, 79, 45), (cx - 23, cy - 13, 46, 26))
                pygame.draw.circle(surface, (255, 184, 65), (cx, cy - 2), 8)
            elif item.discovery_id == "vent":
                pygame.draw.polygon(surface, (111, 92, 79), [(cx - 24, cy + 20), (cx, cy - 25), (cx + 24, cy + 20)])
                pygame.draw.line(surface, (240, 100, 42), (cx, cy + 12), (cx, cy - 18), 7)
            elif item.discovery_id == "style":
                pygame.draw.line(surface, (232, 86, 43), (cx - 22, cy + 10), (cx - 2, cy - 12), 8)
                pygame.draw.polygon(surface, (239, 89, 39), [(cx + 4, cy + 12), (cx + 16, cy - 22), (cx + 28, cy + 12)])
            else:
                for dx, dy, radius in ((-13, 5, 9), (0, -8, 12), (15, 5, 8), (4, 11, 10)):
                    pygame.draw.circle(surface, (91, 87, 83), (cx + dx, cy + dy), radius)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (255, 249, 229), panel, border_radius=22)
        pygame.draw.rect(surface, (75, 62, 53), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (56, 49, 45))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (56, 49, 45))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
