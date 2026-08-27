"""Bicycle entry: drivetrain motion and qualitative gear-ratio tradeoffs."""

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
class BicycleDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    BicycleDiscovery("drive", "bicycle.drive", "encyclopedia.machines.bicycle.drive", (250, 190)),
    BicycleDiscovery("ratio", "bicycle.ratio", "encyclopedia.machines.bicycle.ratio", (755, 190)),
    BicycleDiscovery("travel", "bicycle.travel", "encyclopedia.machines.bicycle.travel", (250, 420)),
    BicycleDiscovery("energy", "bicycle.energy", "encyclopedia.machines.bicycle.energy", (755, 420)),
)


class DrivetrainModel:
    """Own coupled crank, rear-wheel and finite ratio state."""

    RATIOS = (0.75, 1.65)

    def __init__(self) -> None:
        self.ratio_index = 0
        self.crank_angle = 0.0
        self.wheel_angle = 0.0
        self.drive_age = 0.0
        self.travel_age = 0.0
        self.energy_age = 0.0

    @property
    def ratio(self) -> float:
        return self.RATIOS[self.ratio_index]

    def update(self, dt: float) -> None:
        if self.drive_age > 0.0:
            delta = dt * 2.3
            self.crank_angle = (self.crank_angle + delta) % math.tau
            self.wheel_angle = (self.wheel_angle + delta * self.ratio) % math.tau
        self.drive_age = max(0.0, self.drive_age - dt)
        self.travel_age = max(0.0, self.travel_age - dt)
        self.energy_age = max(0.0, self.energy_age - dt)

    def run_drive(self) -> None:
        self.drive_age = 5.0

    def toggle_ratio(self) -> None:
        self.ratio_index = 1 - self.ratio_index
        self.drive_age = 4.0

    def compare_travel(self) -> None:
        self.travel_age = 4.5
        self.drive_age = 4.5

    def show_tradeoff(self) -> None:
        self.energy_age = 4.5


class BicyclePage(EncyclopediaPage):
    page_id = "machines.bicycle"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._model = DrivetrainModel()
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "bicycle.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.machines.bicycle.intro")

    def update(self, dt: float) -> None:
        self._model.update(dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {PageInputKind.POINTER_MOVE, PageInputKind.POINTER_PRESS}:
            point = (int(event.position[0]), int(event.position[1]))
            hit = next((i for i, rect in enumerate(self._hotspots) if rect.collidepoint(point)), None)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._selected = hit
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            self._activate(self._selected)
        else:
            self._selected = grid_step(self._selected, event.command, columns=2, count=len(DISCOVERIES))

    def _activate(self, index: int) -> None:
        item = DISCOVERIES[index]
        self._caption_key = item.caption_key
        if item.discovery_id == "drive":
            self._model.run_drive()
        elif item.discovery_id == "ratio":
            self._model.toggle_ratio()
        elif item.discovery_id == "travel":
            self._model.compare_travel()
        else:
            self._model.show_tradeoff()
        self.context.audio.play(item.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((237, 244, 232))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("bicycle.title"),
            center=(500, 92),
            size=40,
            color=self.context.palette.ink,
            role=FontRole.DISPLAY,
        )
        self._draw_bicycle(surface)
        self._draw_hotspots(surface)
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "flash",
            position=(925, 565),
            height=142,
            variant="happy",
            fallback_color=(235, 139, 70),
        )

    def _draw_bicycle(self, surface: pygame.Surface) -> None:
        rear = (410, 360)
        front = (620, 360)
        wheel_r = 76
        for center in (rear, front):
            pygame.draw.circle(surface, (58, 64, 66), center, wheel_r, 5)
            for spoke in range(8):
                angle = self._model.wheel_angle + spoke * math.tau / 8
                end = (center[0] + int(math.cos(angle) * (wheel_r - 7)), center[1] + int(math.sin(angle) * (wheel_r - 7)))
                pygame.draw.line(surface, (154, 160, 160), center, end, 2)

        crank = (505, 348)
        frame = (76, 135, 181)
        pygame.draw.line(surface, frame, rear, (470, 265), 7)
        pygame.draw.line(surface, frame, (470, 265), crank, 7)
        pygame.draw.line(surface, frame, crank, rear, 7)
        pygame.draw.line(surface, frame, crank, (578, 272), 7)
        pygame.draw.line(surface, frame, (578, 272), front, 7)
        pygame.draw.line(surface, frame, (470, 265), (578, 272), 7)
        pygame.draw.line(surface, (73, 69, 65), (460, 255), (492, 255), 7)
        pygame.draw.line(surface, (73, 69, 65), (578, 272), (592, 226), 6)
        pygame.draw.line(surface, (73, 69, 65), (574, 226), (615, 226), 5)

        front_ring = 29 if self._model.ratio_index == 1 else 22
        rear_ring = 16 if self._model.ratio_index == 1 else 24
        pygame.draw.circle(surface, (225, 173, 65), crank, front_ring, 4)
        pygame.draw.circle(surface, (225, 173, 65), rear, rear_ring, 4)
        pygame.draw.line(surface, (80, 75, 68), (crank[0], crank[1] - front_ring), (rear[0], rear[1] - rear_ring), 4)
        pygame.draw.line(surface, (80, 75, 68), (crank[0], crank[1] + front_ring), (rear[0], rear[1] + rear_ring), 4)

        pedal = (
            crank[0] + int(math.cos(self._model.crank_angle) * 42),
            crank[1] + int(math.sin(self._model.crank_angle) * 42),
        )
        opposite = (2 * crank[0] - pedal[0], 2 * crank[1] - pedal[1])
        pygame.draw.line(surface, (72, 68, 64), opposite, pedal, 5)
        for p in (pedal, opposite):
            pygame.draw.line(surface, (72, 68, 64), (p[0] - 9, p[1]), (p[0] + 9, p[1]), 5)

        if self._model.drive_age > 0.0:
            for phase in (0.1, 0.36, 0.62, 0.88):
                x = int(crank[0] + (rear[0] - crank[0]) * phase)
                y = int((crank[1] - front_ring) + ((rear[1] - rear_ring) - (crank[1] - front_ring)) * phase)
                pygame.draw.circle(surface, (250, 211, 82), (x, y), 5)

        if self._model.travel_age > 0.0:
            easy_len = 82
            hard_len = 165
            pygame.draw.line(surface, (95, 160, 101), (350, 462), (350 + easy_len, 462), 8)
            pygame.draw.line(surface, (220, 123, 75), (525, 462), (525 + hard_len, 462), 8)
            for x in (350, 350 + easy_len, 525, 525 + hard_len):
                pygame.draw.line(surface, (75, 70, 66), (x, 452), (x, 472), 3)

        if self._model.energy_age > 0.0:
            pygame.draw.polygon(surface, (95, 160, 101), [(390, 225), (435, 225), (435, 210), (465, 240), (435, 270), (435, 255), (390, 255)])
            pygame.draw.polygon(surface, (220, 123, 75), [(620, 225), (575, 225), (575, 210), (545, 240), (575, 270), (575, 255), (620, 255)])

    @staticmethod
    def _draw_hotspot_icon(surface: pygame.Surface, item: BicycleDiscovery) -> None:
        cx, cy = item.center
        if item.discovery_id == "drive":
            pygame.draw.circle(surface, (225, 173, 65), (cx - 13, cy), 15, 3)
            pygame.draw.circle(surface, (225, 173, 65), (cx + 20, cy), 9, 3)
            pygame.draw.line(surface, (80, 75, 68), (cx - 13, cy - 15), (cx + 20, cy - 9), 3)
            pygame.draw.line(surface, (80, 75, 68), (cx - 13, cy + 15), (cx + 20, cy + 9), 3)
        elif item.discovery_id == "ratio":
            pygame.draw.circle(surface, (225, 173, 65), (cx - 14, cy), 20, 3)
            pygame.draw.circle(surface, (225, 173, 65), (cx + 18, cy), 10, 3)
        elif item.discovery_id == "travel":
            pygame.draw.circle(surface, (68, 72, 73), (cx - 15, cy), 17, 3)
            pygame.draw.line(surface, (95, 160, 101), (cx + 5, cy + 15), (cx + 29, cy + 15), 5)
        else:
            pygame.draw.polygon(surface, (95, 160, 101), [(cx - 27, cy - 9), (cx - 3, cy - 9), (cx - 3, cy - 19), (cx + 10, cy), (cx - 3, cy + 19), (cx - 3, cy + 9), (cx - 27, cy + 9)])
            pygame.draw.polygon(surface, (220, 123, 75), [(cx + 27, cy - 9), (cx + 3, cy - 9), (cx + 3, cy - 19), (cx - 10, cy), (cx + 3, cy + 19), (cx + 3, cy + 9), (cx + 27, cy + 9)])

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (252, 249, 233), item.center, 37)
            pygame.draw.circle(surface, (71, 69, 64), item.center, 37, 3)
            self._draw_hotspot_icon(surface, item)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (252, 249, 233), panel, border_radius=22)
        pygame.draw.rect(surface, (71, 69, 64), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (53, 52, 49))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (53, 52, 49))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
