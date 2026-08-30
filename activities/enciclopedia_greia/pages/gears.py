"""Gears golden master: authored workshop board with semantic mechanism overlays."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        TOKEN_SHAPE_WORKSHOP_TAG,
        announce_focus_name,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_direction_toggle,
        draw_discovery_token,
        draw_focus_patch,
        draw_navigation_arrows,
        draw_pause_button,
        draw_speed_slider,
        draw_title,
        draw_turn_button,
        encyclopedia_focus_cue,
    )
    from .common import draw_presenter, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        TOKEN_SHAPE_WORKSHOP_TAG,
        announce_focus_name,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_direction_toggle,
        draw_discovery_token,
        draw_focus_patch,
        draw_navigation_arrows,
        draw_pause_button,
        draw_speed_slider,
        draw_title,
        draw_turn_button,
        encyclopedia_focus_cue,
    )
    from pages.common import draw_presenter, grid_step


@dataclass(frozen=True, slots=True)
class GearDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    GearDiscovery("teeth", "gears.teeth", "encyclopedia.machines.gears.teeth", (235, 195)),
    GearDiscovery(
        "direction",
        "gears.direction",
        "encyclopedia.machines.gears.direction",
        (775, 195),
    ),
    GearDiscovery("ratio", "gears.ratio", "encyclopedia.machines.gears.ratio", (235, 405)),
    GearDiscovery("rack", "gears.rack", "encyclopedia.machines.gears.rack", (775, 405)),
)


class GearTrainModel:
    """Own the finite interaction state shown over the authored mechanism board."""

    # Reusable toy: speed is child-controlled via slider, not hard-coded
    SPEED_LEVELS = (0.45, 0.85, 1.45)

    def __init__(self) -> None:
        self.driver_angle = 0.0
        self.direction = 1.0
        self.speed_level = 1
        self.speed = self.SPEED_LEVELS[self.speed_level]
        self.paused = False
        self.teeth_age = 0.0
        self.direction_age = 0.0
        self.ratio_age = 0.0
        self.rack_age = 0.0
        # Ambient idle wobble when paused — keeps page alive without obscuring
        self._idle_phase = 0.0

    def update(self, dt: float) -> None:
        if not self.paused:
            self.driver_angle += dt * self.speed * self.direction
        else:
            self._idle_phase += dt
        self.teeth_age = max(0.0, self.teeth_age - dt)
        self.direction_age = max(0.0, self.direction_age - dt)
        self.ratio_age = max(0.0, self.ratio_age - dt)
        self.rack_age = max(0.0, self.rack_age - dt)

    def set_speed_level(self, level: int) -> None:
        level = max(0, min(2, int(level)))
        self.speed_level = level
        self.speed = self.SPEED_LEVELS[level]
        self.paused = False

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def show_teeth(self) -> None:
        self.teeth_age = 3.2

    def reverse(self) -> None:
        self.direction *= -1.0
        self.direction_age = 3.2

    def show_ratio(self) -> None:
        self.ratio_age = 4.0

    def show_rack(self) -> None:
        self.rack_age = 4.0

    def nudge(self, delta_angle: float) -> None:
        """Direct drag — large hit, no pixel precision required."""
        self.driver_angle += delta_angle
        self.paused = False


class GearsPage(EncyclopediaPage):
    page_id = "machines.gears"

    # Live gear geometry — must match authored workbench positions used in reveals
    GEAR_SPECS = (
        ((385, 318), 72, 18),
        ((500, 318), 58, 14),
        ((592, 318), 47, 12),
    )

    def __init__(self, context) -> None:
        super().__init__(context)
        self._model = GearTrainModel()
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "gears.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 50, cy - 50, 100, 100)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = 0.0
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._turn_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._speed_hits: tuple[pygame.Rect, pygame.Rect, pygame.Rect] = (
            pygame.Rect(0, 0, 0, 0),
            pygame.Rect(0, 0, 0, 0),
            pygame.Rect(0, 0, 0, 0),
        )
        self._pause_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._direction_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._dragging = False
        self._last_drag_x: int | None = None

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.machines.gears.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        disc = DISCOVERIES[self._selected]
        cue = encyclopedia_focus_cue("machines", "gears", disc.discovery_id, "name")
        if not announce_focus_name(self.context.audio, cue):
            announce_focus_name(self.context.audio, disc.cue_id)

    def _set_selected(self, index: int) -> None:
        index = max(0, min(len(DISCOVERIES) - 1, index))
        if index == self._selected:
            return
        self._selected = index
        self._announce_selected()

    def update(self, dt: float) -> None:
        self._time += dt
        self._model.update(dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            # Toy controls first — large hit areas, reliable
            if event.kind is PageInputKind.POINTER_PRESS:
                if self._turn_hit.collidepoint(point):
                    # Big turn gives a visible burst
                    self._model.paused = False
                    self._model.driver_angle += 0.9 * self._model.direction
                    return
                for lvl, hit in enumerate(self._speed_hits):
                    if hit.collidepoint(point):
                        self._model.set_speed_level(lvl)
                        return
                if self._pause_hit.collidepoint(point):
                    self._model.toggle_pause()
                    return
                if self._direction_hit.collidepoint(point):
                    self._model.reverse()
                    return
                # Direct gear drag — check if press is on any gear
                for center, radius, _teeth in self.GEAR_SPECS:
                    dx = point[0] - center[0]
                    dy = point[1] - center[1]
                    if dx * dx + dy * dy <= (radius + 10) * (radius + 10):
                        self._dragging = True
                        self._last_drag_x = point[0]
                        return
                if self._arrow_left_hit.collidepoint(point):
                    self._set_selected(self._selected - 1)
                    return
                if self._arrow_right_hit.collidepoint(point):
                    self._set_selected(self._selected + 1)
                    return
            if event.kind is PageInputKind.POINTER_MOVE:
                if self._dragging and self._last_drag_x is not None:
                    delta = point[0] - self._last_drag_x
                    self._model.nudge(delta * 0.04)
                    self._last_drag_x = point[0]
                    # Hover still for discovery
                    hit = next(
                        (index for index, rect in enumerate(self._hotspots) if rect.collidepoint(point)),
                        None,
                    )
                    if hit is not None and hit != self._selected:
                        disc = DISCOVERIES[hit]
                        cue = encyclopedia_focus_cue("machines", "gears", disc.discovery_id, "name")
                        announce_focus_name(self.context.audio, cue)
                    self._hovered = hit
                    return
                hit = next(
                    (index for index, rect in enumerate(self._hotspots) if rect.collidepoint(point)),
                    None,
                )
                if hit is not None and hit != self._selected:
                    disc = DISCOVERIES[hit]
                    cue = encyclopedia_focus_cue("machines", "gears", disc.discovery_id, "name")
                    announce_focus_name(self.context.audio, cue)
                self._hovered = hit
                if hit is not None:
                    return
                # End drag when pointer moves off gear without press? Keep dragging until press release — here move without press ends drag
                self._dragging = False
                self._last_drag_x = None
                return
            # POINTER_PRESS already handled toy hits above; now check discovery tokens
            hit = next(
                (index for index, rect in enumerate(self._hotspots) if rect.collidepoint(point)),
                None,
            )
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            self._activate(self._selected)
        else:
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
        item = DISCOVERIES[index]
        self._caption_key = item.caption_key
        if item.discovery_id == "teeth":
            self._model.show_teeth()
        elif item.discovery_id == "direction":
            self._model.reverse()
        elif item.discovery_id == "ratio":
            self._model.show_ratio()
        else:
            self._model.show_rack()
        self.context.audio.play(item.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        if not draw_authored_scene(
            surface,
            self.context.visuals,
            "encyclopedia.machines.gears.workbench",
        ):
            surface.fill((239, 231, 205))
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("gears.title"),
            self.context.palette.ink,
        )
        self._draw_live_gears(surface)
        self._draw_reveals(surface)
        for index, item in enumerate(DISCOVERIES):
            draw_discovery_token(
                surface,
                item.center,
                selected=index == self._selected,
                hovered=index == self._hovered,
                recently_activated=self._recent(item.discovery_id),
                icon=lambda target, center, item=item: self._draw_icon(
                    target,
                    center,
                    item.discovery_id,
                ),
                token_shape=TOKEN_SHAPE_WORKSHOP_TAG,
            )
            if index == self._selected or index == self._hovered:
                draw_focus_patch(surface, self._hotspots[index], active=True, radius=18, time=self._time)
        # Standard navigation for discovery tokens
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=self._time, can_go_left=can_left, can_go_right=can_right
        )
        # Main toy chrome — turn + speed + pause/direction
        _, self._speed_hits = draw_speed_slider(
            surface, (185, 485), time=self._time, level=self._model.speed_level, paused=self._model.paused
        )
        self._turn_hit = draw_turn_button(
            surface, (512, 485), time=self._time, enabled=True, spinning=not self._model.paused
        )
        self._pause_hit = draw_pause_button(
            surface, (380, 485), time=self._time, paused=self._model.paused
        )
        self._direction_hit = draw_direction_toggle(
            surface, (700, 485), time=self._time, direction=self._model.direction
        )
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
        )
        draw_presenter(
            surface,
            self.context.visuals,
            "dani",
            position=(880, 575),
            height=190,
            variant="happy",
            fallback_color=(101, 171, 211),
        )

    def _draw_live_gears(self, surface: pygame.Surface) -> None:
        # Three meshed gears — live, not static PNG
        # Ratios based on authored radii: 72 -> 58 -> 47
        base_angle = self._model.driver_angle
        # Second gear opposite, scaled
        angle1 = base_angle
        angle2 = -base_angle * (72 / 58) + 0.12  # phase offset so teeth mesh visually
        angle3 = base_angle * (72 / 47) - 0.07
        specs = [
            ((385, 318), 72, 18, angle1, (83, 145, 181)),
            ((500, 318), 58, 14, angle2, (200, 170, 90)),
            ((592, 318), 47, 12, angle3, (160, 140, 110)),
        ]
        for center, radius, teeth, angle, color in specs:
            self._draw_gear(surface, center, radius, teeth, angle, color)

    @staticmethod
    def _draw_gear(
        surface: pygame.Surface,
        center: tuple[int, int],
        radius: int,
        teeth: int,
        angle: float,
        color: tuple[int, int, int],
    ) -> None:
        cx, cy = center
        # Body
        pygame.draw.circle(surface, color, center, radius)
        pygame.draw.circle(surface, (75, 70, 67), center, radius, 3)
        pygame.draw.circle(surface, (239, 231, 205), center, max(8, radius // 4))
        pygame.draw.circle(surface, (75, 70, 67), center, max(8, radius // 4), 2)
        # Teeth
        for i in range(teeth):
            theta = angle + i * math.tau / teeth
            x1 = cx + int(math.cos(theta) * radius)
            y1 = cy + int(math.sin(theta) * radius)
            x2 = cx + int(math.cos(theta) * (radius + 8))
            y2 = cy + int(math.sin(theta) * (radius + 8))
            pygame.draw.line(surface, (75, 70, 67), (x1, y1), (x2, y2), 3)
            # Tooth cap small rect
            pygame.draw.circle(surface, color, (x2, y2), 3)

    def _recent(self, discovery_id: str) -> bool:
        ages = {
            "teeth": self._model.teeth_age,
            "direction": self._model.direction_age,
            "ratio": self._model.ratio_age,
            "rack": self._model.rack_age,
        }
        return ages[discovery_id] > 0

    def _draw_reveals(self, surface: pygame.Surface) -> None:
        if self._model.teeth_age > 0:
            # The authored train has exactly two mesh boundaries. Keep the
            # teaching highlight tied to those real tooth-contact points.
            contact_points = ((450, 318), (550, 318))
            for point in contact_points:
                pygame.draw.circle(surface, (255, 228, 91), point, 20, 6)
                pygame.draw.circle(surface, (255, 170, 60), point, 8, 3)
            for index, point in enumerate(contact_points):
                ax, ay = point
                ax -= 6
                ay -= 28
                if index % 2 == 0:
                    ax2, ay2 = ax + 12, ay
                else:
                    ax2, ay2 = ax - 12, ay
                pygame.draw.line(surface, (255, 170, 60), (ax, ay), (ax2, ay2), 4)
                if index % 2 == 0:
                    pygame.draw.polygon(
                        surface,
                        (255, 170, 60),
                        [(ax2, ay2), (ax2 - 7, ay2 - 5), (ax2 - 7, ay2 + 5)],
                    )
                else:
                    pygame.draw.polygon(
                        surface,
                        (255, 170, 60),
                        [(ax2, ay2), (ax2 + 7, ay2 - 5), (ax2 + 7, ay2 + 5)],
                    )

        if self._model.direction_age > 0:
            specs = (
                ((385, 318), 72, self._model.direction),
                ((500, 318), 58, -self._model.direction),
                ((592, 318), 47, self._model.direction),
            )
            for center, radius, _direction in specs:
                rect = pygame.Rect(
                    center[0] - radius,
                    center[1] - radius,
                    radius * 2,
                    radius * 2,
                )
                pygame.draw.arc(surface, (255, 221, 89), rect, 0.3, 1.9, 5)

        if self._model.ratio_age > 0:
            for x, count in ((385, 2), (500, 3), (592, 4)):
                for index in range(count):
                    pygame.draw.rect(
                        surface,
                        (255, 218, 80),
                        (x - 30 + index * 18, 205, 11, 20),
                        border_radius=4,
                    )

        if self._model.rack_age > 0:
            offset = int(math.sin(self._model.driver_angle * 2.2) * 28)
            pygame.draw.line(
                surface,
                (255, 220, 86),
                (690 + offset, 410),
                (815 + offset, 410),
                6,
            )
            pygame.draw.polygon(
                surface,
                (255, 220, 86),
                [
                    (815 + offset, 410),
                    (799 + offset, 399),
                    (799 + offset, 421),
                ],
            )

    @staticmethod
    def _draw_icon(
        surface: pygame.Surface,
        center: tuple[int, int],
        discovery_id: str,
    ) -> None:
        cx, cy = center
        if discovery_id == "teeth":
            for offset in (-15, 0, 15):
                pygame.draw.rect(
                    surface,
                    (83, 145, 181),
                    (cx + offset - 6, cy - 20, 12, 40),
                    border_radius=3,
                )
        elif discovery_id == "direction":
            pygame.draw.arc(
                surface,
                (231, 157, 71),
                (cx - 23, cy - 23, 46, 46),
                0.2,
                math.pi * 1.6,
                6,
            )
        elif discovery_id == "ratio":
            pygame.draw.circle(surface, (83, 145, 181), (cx - 13, cy), 18)
            pygame.draw.circle(surface, (231, 157, 71), (cx + 19, cy), 10)
        else:
            pygame.draw.circle(surface, (155, 117, 183), (cx - 11, cy - 6), 13, 5)
            pygame.draw.rect(surface, (102, 84, 67), (cx, cy + 4, 27, 8))
