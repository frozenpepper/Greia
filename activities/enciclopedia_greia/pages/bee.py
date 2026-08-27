"""Bee entry: flower food, pollen transfer, pollination and varied bee homes."""

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
class BeeDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    BeeDiscovery("food", "bee.food", "encyclopedia.animals.bee.food", (250, 195)),
    BeeDiscovery("pollen", "bee.pollen", "encyclopedia.animals.bee.pollen", (755, 195)),
    BeeDiscovery("pollination", "bee.pollination", "encyclopedia.animals.bee.pollination", (250, 420)),
    BeeDiscovery("homes", "bee.homes", "encyclopedia.animals.bee.homes", (755, 420)),
)

_FLOWER_POSITIONS = ((395, 355), (625, 355))


class BeePollinationModel:
    """Own the finite pollen-transfer sequence independently of rendering."""

    def __init__(self) -> None:
        self.current_flower = 0
        self.from_flower = 0
        self.to_flower = 0
        self.flight_progress = 1.0
        self.carrying_pollen = False
        self.pollinated = False
        self.food_age = 0.0
        self.pollination_age = 0.0
        self.home_mode = 0
        self.home_age = 0.0

    @property
    def flying(self) -> bool:
        return self.flight_progress < 1.0

    def update(self, dt: float) -> None:
        self.food_age = max(0.0, self.food_age - dt)
        self.pollination_age = max(0.0, self.pollination_age - dt)
        self.home_age = max(0.0, self.home_age - dt)
        if not self.flying:
            return
        self.flight_progress = min(1.0, self.flight_progress + dt * 0.65)
        if self.flight_progress >= 1.0:
            self.current_flower = self.to_flower
            if self.current_flower == 1 and self.carrying_pollen:
                self.pollinated = True
                self.pollination_age = max(self.pollination_age, 4.0)

    def show_food(self) -> None:
        self.food_age = 4.0

    def travel(self) -> None:
        if self.flying:
            return
        self.from_flower = self.current_flower
        self.to_flower = 1 - self.current_flower
        if self.from_flower == 0:
            self.carrying_pollen = True
        self.flight_progress = 0.0

    def demonstrate_pollination(self) -> None:
        if self.current_flower == 1 and self.carrying_pollen:
            self.pollinated = True
            self.pollination_age = 4.0
            return
        if not self.flying:
            if self.current_flower == 1:
                self.current_flower = 0
            self.carrying_pollen = True
            self.from_flower = 0
            self.to_flower = 1
            self.flight_progress = 0.0

    def toggle_homes(self) -> None:
        self.home_mode = 1 - self.home_mode
        self.home_age = 4.5

    def bee_position(self) -> tuple[int, int]:
        if not self.flying:
            x, y = _FLOWER_POSITIONS[self.current_flower]
            return x, y - 60
        start_x, start_y = _FLOWER_POSITIONS[self.from_flower]
        end_x, end_y = _FLOWER_POSITIONS[self.to_flower]
        t = self.flight_progress
        x = int(start_x + (end_x - start_x) * t)
        y = int(start_y - 60 + (end_y - start_y) * t - math.sin(t * math.pi) * 55)
        return x, y


class BeePage(EncyclopediaPage):
    page_id = "animals.bee"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._model = BeePollinationModel()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "bee.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.animals.bee.intro")

    def update(self, dt: float) -> None:
        self._time += dt
        self._model.update(dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            hit = next(
                (index for index, rect in enumerate(self._hotspots) if rect.collidepoint(point)),
                None,
            )
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
        self._selected = grid_step(
            self._selected,
            event.command,
            columns=2,
            count=len(DISCOVERIES),
        )

    def _activate(self, index: int) -> None:
        discovery = DISCOVERIES[index]
        self._caption_key = discovery.caption_key
        if discovery.discovery_id == "food":
            self._model.show_food()
        elif discovery.discovery_id == "pollen":
            self._model.travel()
        elif discovery.discovery_id == "pollination":
            self._model.demonstrate_pollination()
        else:
            self._model.toggle_homes()
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((224, 239, 199))
        pygame.draw.rect(surface, (135, 183, 99), (0, 445, 1024, 155))
        pygame.draw.circle(surface, (252, 218, 89), (870, 125), 42)
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("bee.title"),
            center=(500, 92),
            size=40,
            color=self.context.palette.ink,
            role=FontRole.DISPLAY,
        )
        self._draw_flowers(surface)
        self._draw_bee(surface)
        self._draw_home_demo(surface)
        self._draw_hotspots(surface)
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "tito",
            position=(925, 565),
            height=142,
            variant="happy",
            fallback_color=(247, 151, 77),
        )

    def _draw_flowers(self, surface: pygame.Surface) -> None:
        colors = ((223, 108, 133), (125, 137, 220))
        for index, ((cx, cy), petal_color) in enumerate(zip(_FLOWER_POSITIONS, colors)):
            pygame.draw.line(surface, (75, 135, 72), (cx, cy + 22), (cx, 455), 10)
            for angle in range(0, 360, 60):
                radians = math.radians(angle)
                px = cx + int(math.cos(radians) * 26)
                py = cy + int(math.sin(radians) * 26)
                pygame.draw.circle(surface, petal_color, (px, py), 20)
            center_color = (246, 205, 68) if index == 0 or self._model.pollinated else (220, 181, 70)
            pygame.draw.circle(surface, center_color, (cx, cy), 22)

            if self._model.food_age > 0:
                for grain in range(8):
                    angle = grain * math.pi / 4
                    px = cx + int(math.cos(angle) * 13)
                    py = cy + int(math.sin(angle) * 13)
                    pygame.draw.circle(surface, (245, 177, 53), (px, py), 3)
                pygame.draw.circle(surface, (106, 177, 223), (cx + 36, cy - 28), 7)

        if self._model.pollination_age > 0 or self._model.pollinated:
            for index in range(4):
                x = 600 + index * 17
                pygame.draw.ellipse(surface, (103, 161, 82), (x, 415 - index * 4, 11, 18))

    def _draw_bee(self, surface: pygame.Surface) -> None:
        cx, cy = self._model.bee_position()
        wing_bob = int(math.sin(self._time * 16.0) * 5)
        pygame.draw.ellipse(surface, (218, 239, 247), (cx - 30, cy - 26 - wing_bob, 28, 26))
        pygame.draw.ellipse(surface, (218, 239, 247), (cx + 2, cy - 26 + wing_bob, 28, 26))
        pygame.draw.ellipse(surface, (247, 204, 63), (cx - 28, cy - 16, 56, 32))
        for x in (cx - 12, cx + 5):
            pygame.draw.line(surface, (55, 49, 43), (x, cy - 13), (x, cy + 13), 5)
        pygame.draw.circle(surface, (55, 49, 43), (cx + 22, cy - 2), 4)
        if self._model.carrying_pollen:
            for dx, dy in ((-22, 13), (-10, 17), (5, 16), (18, 10)):
                pygame.draw.circle(surface, (241, 158, 44), (cx + dx, cy + dy), 4)

    def _draw_home_demo(self, surface: pygame.Surface) -> None:
        if self._model.home_age <= 0:
            return
        panel = pygame.Rect(405, 180, 200, 105)
        pygame.draw.rect(surface, (255, 249, 227), panel, border_radius=18)
        pygame.draw.rect(surface, (83, 74, 57), panel, 3, border_radius=18)
        if self._model.home_mode == 0:
            # Generic solitary wild-bee example: one bee and one simple ground nest.
            pygame.draw.ellipse(surface, (142, 107, 72), (440, 230, 70, 25))
            pygame.draw.circle(surface, (73, 58, 46), (475, 238), 9)
            pygame.draw.ellipse(surface, (247, 204, 63), (520, 220, 42, 23))
            pygame.draw.line(surface, (55, 49, 43), (536, 221), (536, 240), 4)
        else:
            # Explicit honey-bee social case; this is not presented as universal bee behavior.
            for row in range(3):
                for col in range(4):
                    center = (455 + col * 28 + (row % 2) * 14, 215 + row * 25)
                    pygame.draw.polygon(
                        surface,
                        (232, 177, 63),
                        [
                            (center[0] - 9, center[1]),
                            (center[0] - 4, center[1] - 8),
                            (center[0] + 5, center[1] - 8),
                            (center[0] + 10, center[1]),
                            (center[0] + 5, center[1] + 8),
                            (center[0] - 4, center[1] + 8),
                        ],
                        2,
                    )
            for x in (565, 580, 592):
                pygame.draw.circle(surface, (55, 49, 43), (x, 230 + (x % 3) * 8), 5)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (255, 250, 230), item.center, 37)
            pygame.draw.circle(surface, (70, 68, 51), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "food":
                pygame.draw.circle(surface, (246, 205, 68), (cx - 10, cy), 12)
                pygame.draw.circle(surface, (106, 177, 223), (cx + 14, cy - 4), 8)
            elif item.discovery_id == "pollen":
                pygame.draw.ellipse(surface, (247, 204, 63), (cx - 24, cy - 12, 48, 24))
                for dx in (-16, -4, 8, 18):
                    pygame.draw.circle(surface, (241, 158, 44), (cx + dx, cy + 14), 4)
            elif item.discovery_id == "pollination":
                pygame.draw.circle(surface, (223, 108, 133), (cx - 14, cy), 13)
                pygame.draw.line(surface, (241, 158, 44), (cx - 1, cy), (cx + 20, cy), 5)
                pygame.draw.circle(surface, (125, 137, 220), (cx + 22, cy), 11)
            else:
                pygame.draw.circle(surface, (142, 107, 72), (cx - 14, cy + 8), 10)
                pygame.draw.polygon(surface, (232, 177, 63), [(cx + 4, cy + 14), (cx + 14, cy - 15), (cx + 25, cy + 14)])
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (255, 250, 230), panel, border_radius=22)
        pygame.draw.rect(surface, (70, 68, 51), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (54, 52, 44))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (54, 52, 44))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
