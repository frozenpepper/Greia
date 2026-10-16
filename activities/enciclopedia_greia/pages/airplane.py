"""Airplane entry: a friendly teaching plane flown by Tito through the clouds.

The plane is authored art: ``assets/source/sprites/airplane_parts.svg`` builds
to one transparent parts sheet (body, propeller frames + motion disc, and the
sunshine-yellow control surfaces in five deflection frames each). The page only
slices that sheet once and blits parts, so the propeller spins and the
aileron / elevator / rudder really move while every overlay (lift, air,
thrust, altitude) stays live. When the sheet is missing a neutral procedural
plane with the same geometry is drawn instead (fail-soft). The livery is
deliberately neutral: no flags, stars, roundels or any state/military insignia.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        draw_authored_scene,
        draw_caption_ribbon,
        draw_machine_action_button,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_centered_text, draw_presenter, focus_ring, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        draw_authored_scene,
        draw_caption_ribbon,
        draw_machine_action_button,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class AirplaneDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    AirplaneDiscovery("lift", "airplane.lift", "encyclopedia.machines.airplane.lift", (240, 185)),
    AirplaneDiscovery("myth", "airplane.myth", "encyclopedia.machines.airplane.myth", (765, 185)),
    AirplaneDiscovery("forces", "airplane.forces", "encyclopedia.machines.airplane.forces", (240, 420)),
    AirplaneDiscovery("thrust", "airplane.thrust", "encyclopedia.machines.airplane.thrust", (765, 420)),
)

SCENE_ID = "encyclopedia.machines.airplane.sky"
PLANE_SHEET_ID = "sheet.machines.airplane.parts"

# Storybook palette (Greia tokens / cast constants).
INK = (75, 55, 47)
CREAM = (255, 251, 235)
OCEAN = (74, 145, 216)
OCEAN_LIGHT = (137, 184, 230)
OCEAN_SHADE = (62, 110, 159)
SUNSHINE = (255, 194, 52)
SUNSHINE_LIGHT = (255, 216, 115)
LEAF = (89, 184, 106)
SKY_LIGHT = (207, 234, 247)
WHITE = (255, 255, 255)

# The plane at rest is authored around this scene point; a pose only adds dy.
PLANE_REST_CENTER = (512, 305)
PROPELLER_FRAMES = 6  # two-blade propeller, 30 degree steps over half a turn
CONTROL_FRAMES = 5  # 0 = full up/away .. 2 = neutral .. 4 = full down/toward
CONTROL_NEUTRAL = 2

# Parts sheet layout, mirrored from data-cell / data-origin in the source SVG:
# name -> (cell rect in the sheet, scene top-left at rest).
PLANE_PARTS: dict[str, tuple[tuple[int, int, int, int], tuple[int, int]]] = {
    "body": ((0, 0, 270, 200), (380, 196)),
    "prop_0": ((272, 0, 46, 100), (352, 252)),
    "prop_1": ((320, 0, 46, 100), (352, 252)),
    "prop_2": ((368, 0, 46, 100), (352, 252)),
    "prop_3": ((416, 0, 46, 100), (352, 252)),
    "prop_4": ((464, 0, 46, 100), (352, 252)),
    "prop_5": ((0, 202, 46, 100), (352, 252)),
    "prop_disc": ((48, 202, 28, 96), (366, 254)),
    "aileron_0": ((78, 202, 76, 88), (540, 324)),
    "aileron_1": ((156, 202, 76, 88), (540, 324)),
    "aileron_2": ((234, 202, 76, 88), (540, 324)),
    "aileron_3": ((312, 202, 76, 88), (540, 324)),
    "aileron_4": ((390, 202, 76, 88), (540, 324)),
    "elevator_0": ((0, 304, 56, 66), (600, 286)),
    "elevator_1": ((58, 304, 56, 66), (600, 286)),
    "elevator_2": ((116, 304, 56, 66), (600, 286)),
    "elevator_3": ((174, 304, 56, 66), (600, 286)),
    "elevator_4": ((232, 304, 56, 66), (600, 286)),
    "rudder_0": ((290, 304, 42, 80), (624, 208)),
    "rudder_1": ((334, 304, 42, 80), (624, 208)),
    "rudder_2": ((378, 304, 42, 80), (624, 208)),
    "rudder_3": ((422, 304, 42, 80), (624, 208)),
    "rudder_4": ((466, 304, 42, 80), (624, 208)),
}
_PROP_NAMES = tuple(f"prop_{index}" for index in range(PROPELLER_FRAMES))
_AILERON_NAMES = tuple(f"aileron_{index}" for index in range(CONTROL_FRAMES))
_ELEVATOR_NAMES = tuple(f"elevator_{index}" for index in range(CONTROL_FRAMES))
_RUDDER_NAMES = tuple(f"rudder_{index}" for index in range(CONTROL_FRAMES))

# Geometry shared by the authored parts, the fallback plane and the overlays
# (scene coordinates with the plane at rest).
PROPELLER_HUB = (379, 302)
WING_PLANFORM = (
    (462, 326), (496, 378), (501, 369), (515, 362), (535, 361), (557, 365),
    (576, 372), (542, 347), (565, 346), (546, 322),
)
# The curved airfoil the page teaches: the near wing's tip face (upper, lower).
WING_TIP_UPPER = ((496, 378), (501, 369), (515, 362), (535, 361), (557, 365), (576, 372), (589, 380), (594, 383))
WING_TIP_LOWER = ((594, 383), (589, 383), (575, 383), (556, 384), (534, 386), (514, 387), (501, 385), (496, 378))
TAIL_PLANE = ((578, 300), (594, 326), (603, 322), (618, 323), (629, 325), (618, 298))
FIN = ((572, 272), (604, 220), (625, 213), (630, 214), (631, 282))
AILERON_HINGE = ((565, 346), (576, 372))
ELEVATOR_HINGE = ((618, 298), (629, 325))

# Airflow around the wing-tip airfoil (lift) and behind the plane (thrust).
_UPPER_STREAM = ((462, 368), (482, 366), (498, 360), (515, 353), (535, 351), (557, 355), (576, 362), (594, 372), (620, 386), (652, 402))
_LOWER_STREAM = ((462, 396), (500, 395), (534, 396), (575, 393), (600, 392), (630, 399), (662, 410))
_THRUST_LINES = ((662, 276, 52), (676, 300, 66), (662, 324, 52))
# Ice crystals that twinkle beside the authored high cirrus wisps.
_ICE_CRYSTALS = ((338, 108), (440, 112), (612, 104), (738, 126), (196, 92))


def _resample(points: tuple[tuple[int, int], ...], step: float = 5.0) -> tuple[tuple[float, float], ...]:
    """Evenly spaced points along a polyline (computed once, at import)."""
    result: list[tuple[float, float]] = [points[0]]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        length = math.hypot(x1 - x0, y1 - y0)
        count = max(1, int(length // step))
        for index in range(1, count + 1):
            t = index / count
            result.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return tuple(result)


UPPER_STREAM = _resample(_UPPER_STREAM)
LOWER_STREAM = _resample(_LOWER_STREAM)


@dataclass(frozen=True, slots=True)
class PlanePose:
    """Everything a plane renderer needs for one frame."""

    dy: int
    propeller_frame: int
    motion_disc: bool
    aileron: int = CONTROL_NEUTRAL
    elevator: int = CONTROL_NEUTRAL
    rudder: int = CONTROL_NEUTRAL


class PlaneRenderer(Protocol):
    """Draws the airplane for one pose; authored and procedural variants exist."""

    def draw(self, surface: pygame.Surface, pose: PlanePose) -> None: ...


class SheetPlaneRenderer:
    """Composites the authored transparent parts sheet (no decode, no scaling).

    Parts are ``subsurface`` views into the one cached sheet, so the per-frame
    cost is a handful of blits.
    """

    def __init__(self, sheet: pygame.Surface) -> None:
        self._parts = {
            name: (sheet.subsurface(pygame.Rect(cell)), origin)
            for name, (cell, origin) in PLANE_PARTS.items()
        }

    def _blit(self, surface: pygame.Surface, name: str, dy: int) -> None:
        part, (x, y) = self._parts[name]
        surface.blit(part, (x, y + dy))

    def draw(self, surface: pygame.Surface, pose: PlanePose) -> None:
        dy = pose.dy
        if pose.motion_disc:
            self._blit(surface, "prop_disc", dy)
        self._blit(surface, "body", dy)
        self._blit(surface, _RUDDER_NAMES[pose.rudder], dy)
        self._blit(surface, _ELEVATOR_NAMES[pose.elevator], dy)
        self._blit(surface, _AILERON_NAMES[pose.aileron], dy)
        self._blit(surface, _PROP_NAMES[pose.propeller_frame], dy)


def _shift(points, dy: int) -> list[tuple[float, float]]:
    return [(x, y + dy) for x, y in points]


def _hinged(hinge: tuple[tuple[int, int], tuple[int, int]], chord: int, step: int, dy: int) -> list[tuple[float, float]]:
    """Control strip behind a hinge line, its trailing edge tilted by ``step``."""
    angle = math.radians((step - CONTROL_NEUTRAL) * 13)
    tx, ty = chord * math.cos(angle), chord * math.sin(angle)
    (x0, y0), (x1, y1) = hinge
    return [(x0, y0 + dy), (x1, y1 + dy), (x1 + tx, y1 + ty + dy), (x0 + tx, y0 + ty + dy)]


class ProceduralPlaneRenderer:
    """Neutral fallback plane used only when the authored sheet is absent."""

    def draw(self, surface: pygame.Surface, pose: PlanePose) -> None:
        dy = pose.dy
        # Fin + rudder (sunshine = the parts that move).
        pygame.draw.polygon(surface, OCEAN, _shift(FIN, dy))
        pygame.draw.polygon(surface, INK, _shift(FIN, dy), 3)
        rudder_width = 22 + (pose.rudder - CONTROL_NEUTRAL) * 5
        rudder = [(630, 214 + dy), (630 + rudder_width, 222 + dy), (630 + rudder_width, 274 + dy), (630, 281 + dy)]
        pygame.draw.polygon(surface, SUNSHINE, rudder)
        pygame.draw.polygon(surface, INK, rudder, 2)
        # Fuselage, livery stripe and engine cowling.
        body = pygame.Rect(384, 254 + dy, 252, 90)
        pygame.draw.ellipse(surface, CREAM, body)
        pygame.draw.ellipse(surface, INK, body, 3)
        pygame.draw.line(surface, OCEAN, (424, 308 + dy), (628, 290 + dy), 8)
        cowling = pygame.Rect(384, 262 + dy, 46, 76)
        pygame.draw.ellipse(surface, OCEAN_SHADE, cowling)
        pygame.draw.ellipse(surface, INK, cowling, 3)
        # Empty cockpit windscreen.
        windscreen = [(440, 257 + dy), (452, 233 + dy), (458, 235 + dy), (456, 256 + dy)]
        pygame.draw.polygon(surface, SKY_LIGHT, windscreen)
        pygame.draw.polygon(surface, INK, windscreen, 2)
        # Tail plane + elevator, wing + aileron, curved tip face.
        pygame.draw.polygon(surface, OCEAN_LIGHT, _shift(TAIL_PLANE, dy))
        pygame.draw.polygon(surface, INK, _shift(TAIL_PLANE, dy), 2)
        elevator = _hinged(ELEVATOR_HINGE, 16, pose.elevator, dy)
        pygame.draw.polygon(surface, SUNSHINE, elevator)
        pygame.draw.polygon(surface, INK, elevator, 2)
        pygame.draw.polygon(surface, OCEAN, _shift(WING_PLANFORM, dy))
        pygame.draw.polygon(surface, INK, _shift(WING_PLANFORM, dy), 3)
        face = _shift(WING_TIP_UPPER + WING_TIP_LOWER, dy)
        pygame.draw.polygon(surface, CREAM, face)
        pygame.draw.polygon(surface, INK, face, 2)
        aileron = _hinged(AILERON_HINGE, 22, pose.aileron, dy)
        pygame.draw.polygon(surface, SUNSHINE, aileron)
        pygame.draw.polygon(surface, INK, aileron, 2)
        # Wheel.
        pygame.draw.line(surface, INK, (450, 340 + dy), (444, 362 + dy), 4)
        pygame.draw.circle(surface, (91, 74, 66), (443, 366 + dy), 13)
        pygame.draw.circle(surface, CREAM, (443, 366 + dy), 5)
        # Spinning propeller (seen almost edge-on) and spinner.
        hub_x, hub_y = PROPELLER_HUB[0], PROPELLER_HUB[1] + dy
        reach = int(40 * abs(math.cos(math.radians(pose.propeller_frame * 30))))
        if pose.motion_disc:
            pygame.draw.ellipse(surface, SKY_LIGHT, (hub_x - 9, hub_y - 44, 18, 88), 2)
        if reach > 4:
            pygame.draw.line(surface, OCEAN_SHADE, (hub_x, hub_y - reach), (hub_x, hub_y + reach), 8)
        spinner = [(388, 287 + dy), (362, 302 + dy), (388, 317 + dy)]
        pygame.draw.polygon(surface, SUNSHINE, spinner)
        pygame.draw.polygon(surface, INK, spinner, 2)


def _ink_lines(surface: pygame.Surface, color, points, width: int) -> None:
    """Storybook stroke: cocoa contour under a coloured line."""
    pygame.draw.lines(surface, INK, False, points, width + 4)
    pygame.draw.lines(surface, color, False, points, width)


def _ink_arrow(surface: pygame.Surface, color, start, end, width: int = 6, head: int = 13) -> None:
    """Straight teaching arrow with a cocoa contour."""
    (x0, y0), (x1, y1) = start, end
    length = math.hypot(x1 - x0, y1 - y0) or 1.0
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    nx, ny = -uy, ux
    base = (x1 - ux * head, y1 - uy * head)
    tip = [(x1, y1), (base[0] + nx * head * 0.75, base[1] + ny * head * 0.75), (base[0] - nx * head * 0.75, base[1] - ny * head * 0.75)]
    pygame.draw.line(surface, INK, start, base, width + 4)
    pygame.draw.polygon(surface, INK, tip)
    pygame.draw.polygon(surface, INK, tip, 4)
    pygame.draw.line(surface, color, start, base, width)
    inner = [
        (x1 - ux * 3, y1 - uy * 3),
        (base[0] + nx * (head * 0.75 - 3), base[1] + ny * (head * 0.75 - 3)),
        (base[0] - nx * (head * 0.75 - 3), base[1] - ny * (head * 0.75 - 3)),
    ]
    pygame.draw.polygon(surface, color, inner)


def _swing_arrow(surface: pygame.Surface, center, radius: int, start_deg: float, end_deg: float) -> None:
    """Small curved double arrow showing a control surface swinging both ways."""
    cx, cy = center
    points = [
        (cx + radius * math.cos(math.radians(start_deg + (end_deg - start_deg) * i / 8)),
         cy + radius * math.sin(math.radians(start_deg + (end_deg - start_deg) * i / 8)))
        for i in range(9)
    ]
    _ink_lines(surface, SUNSHINE, points, 4)
    for tip, before in ((points[0], points[1]), (points[-1], points[-2])):
        dx, dy = tip[0] - before[0], tip[1] - before[1]
        length = math.hypot(dx, dy) or 1.0
        ux, uy = dx / length, dy / length
        nx, ny = -uy, ux
        head = [(tip[0] + ux * 7, tip[1] + uy * 7), (tip[0] + nx * 6, tip[1] + ny * 6), (tip[0] - nx * 6, tip[1] - ny * 6)]
        pygame.draw.polygon(surface, SUNSHINE, head)
        pygame.draw.polygon(surface, INK, head, 2)


class AirplanePage(EncyclopediaPage):
    page_id = "machines.airplane"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "airplane.intro"

        # Animation feature timers
        self._airflow_age = 0.0      # wings / lift
        self._myth_age = 0.0         # flight controls
        self._forces_age = 0.0       # altitude and clouds
        self._thrust_age = 0.0       # spinning propeller / thrust
        self._loop_age = 0.0         # celebratory hop
        self._propeller_angle = 0.0
        self._plane: PlaneRenderer | None = None

        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._plane_hit = pygame.Rect(380, 240, 260, 160)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.machines.airplane.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        disc = DISCOVERIES[self._selected]
        cue = encyclopedia_focus_cue("machines", disc.discovery_id, "name")
        if not self._focus_audio.announce_once(self.context.audio, cue):
            self._focus_audio.announce_once(self.context.audio, disc.cue_id)

    def _set_selected(self, index: int) -> None:
        index = max(0, min(len(DISCOVERIES) - 1, index))
        if index == self._selected:
            return
        self._selected = index
        self._announce_selected()

    def _trigger_main(self) -> None:
        self._thrust_age = 6.0
        self._loop_age = 2.0
        self._activate(3)

    def update(self, dt: float) -> None:
        self._time += dt
        self._airflow_age = max(0.0, self._airflow_age - dt)
        self._myth_age = max(0.0, self._myth_age - dt)
        self._forces_age = max(0.0, self._forces_age - dt)
        self._thrust_age = max(0.0, self._thrust_age - dt)
        self._loop_age = max(0.0, self._loop_age - dt)

        # Propeller rotation speed
        spin_speed = 1800.0 if self._thrust_age > 0.0 else 600.0
        self._propeller_angle = (self._propeller_angle + dt * spin_speed) % 360.0

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
                if self._plane_hit.collidepoint(point):
                    self._trigger_main()
                    return

            hit = next(
                (index for index, rect in enumerate(self._hotspots) if rect.collidepoint(point)),
                None,
            )
            if event.kind is PageInputKind.POINTER_MOVE and hit is not None and hit != self._selected:
                disc = DISCOVERIES[hit]
                cue = encyclopedia_focus_cue("machines", disc.discovery_id, "name")
                self._focus_audio.announce_once(self.context.audio, cue)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self._activate(hit)
            return

        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return

        if event.command is PageCommand.ACTIVATE:
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
        item = DISCOVERIES[index]
        self._caption_key = item.caption_key
        if item.discovery_id == "lift":
            self._airflow_age = 6.0
        elif item.discovery_id == "myth":
            self._myth_age = 6.0
        elif item.discovery_id == "forces":
            self._forces_age = 6.0
        else:
            self._thrust_age = 6.0
        self.context.audio.play(item.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        # 1. Authored sky (sun, high cirrus, low cumulus, world far below).
        authored = draw_authored_scene(surface, self.context.visuals, SCENE_ID)
        if not authored:
            self._draw_fallback_sky(surface)
        else:
            self._draw_wind_streaks(surface)

        # Title at the top
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("airplane.title"),
            center=(512, 68),
            size=36,
            color=(61, 44, 31),
            role=FontRole.DISPLAY,
        )

        # 2. Airplane & live teaching overlays
        self._draw_airplane_scene(surface)

        # 3. Discovery Tokens
        self._draw_hotspots(surface)

        # 4. Navigation controls and action button
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=self._time, can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_machine_action_button(
            surface, (512, 460), machine="airplane", time=self._time, active=True
        )

        # 5. Caption Ribbon
        self._draw_caption(surface)

        # 6. Presenter Flash (happy)
        draw_presenter(
            surface,
            self.context.visuals,
            "flash",
            position=(925, 565),
            height=142,
            variant="happy",
            fallback_color=(235, 139, 70),
        )

    # (start x, y, speed px/s): thin air streaks drifting past the flying plane.
    _WIND_STREAKS = ((120, 262, 46.0), (420, 214, 60.0), (760, 300, 52.0), (300, 372, 40.0))

    def _draw_wind_streaks(self, surface: pygame.Surface) -> None:
        """Cheap live motion cue over the static authored sky (no allocation)."""
        for base_x, y, speed in self._WIND_STREAKS:
            x = int((base_x + self._time * speed) % 1100) - 40
            pygame.draw.line(surface, (255, 255, 255), (x, y), (x + 30, y), 3)

    def _draw_fallback_sky(self, surface: pygame.Surface) -> None:
        """Contained procedural sky used only when the authored PNG is absent."""
        surface.fill((216, 238, 252))

        t = self._time

        # Warm sun in the upper right corner, where the authored scene has it.
        sun_x, sun_y = 846, 140
        pygame.draw.circle(surface, (255, 245, 185), (sun_x, sun_y), 38)
        pygame.draw.circle(surface, (255, 211, 92), (sun_x, sun_y), 26)

        # Drifting Fluffy Clouds
        for base_x, base_y, sz, speed in (
            (80, 220, 60, 8.0),
            (420, 160, 75, 12.0),
            (780, 240, 68, 9.0),
            (260, 390, 55, 7.0),
            (680, 410, 70, 11.0),
        ):
            cx = int((base_x + t * speed) % 1160) - 80
            self._draw_cloud(surface, cx, base_y, sz)

    def _draw_cloud(self, surface: pygame.Surface, cx: int, cy: int, size: int) -> None:
        # Opaque puffs straight onto the frame (fallback only; no allocation).
        pygame.draw.circle(surface, (255, 253, 246), (cx - size // 2, cy), size // 3)
        pygame.draw.circle(surface, (255, 253, 246), (cx, cy - 4), size // 2)
        pygame.draw.circle(surface, (255, 253, 246), (cx + size // 2, cy), size // 3)

    # ------------------------------------------------------------------ plane
    def _plane_renderer(self) -> PlaneRenderer:
        """Resolve the authored parts sheet once; fall back to the neutral plane."""
        if self._plane is None:
            loader = getattr(self.context.visuals, "sprite_sheet", None)
            sheet = loader(PLANE_SHEET_ID) if loader is not None else None
            renderer: PlaneRenderer = ProceduralPlaneRenderer()
            if sheet is not None:
                try:
                    renderer = SheetPlaneRenderer(sheet)
                except (ValueError, pygame.error):
                    renderer = ProceduralPlaneRenderer()
            self._plane = renderer
        return self._plane

    def _control_pose(self) -> tuple[int, int, int]:
        """Flight-controls demo: elevator, then ailerons, then rudder swing in turn."""
        if self._myth_age <= 0.0:
            return CONTROL_NEUTRAL, CONTROL_NEUTRAL, CONTROL_NEUTRAL
        elapsed = 6.0 - self._myth_age
        stage = min(2, int(elapsed // 2.0))
        swing = math.sin((elapsed % 2.0) * math.pi * 1.5)
        step = CONTROL_NEUTRAL + int(round(swing * 2))
        poses = [CONTROL_NEUTRAL, CONTROL_NEUTRAL, CONTROL_NEUTRAL]
        poses[stage] = step
        return poses[1], poses[0], poses[2]  # aileron, elevator, rudder

    def _control_stage(self) -> int | None:
        if self._myth_age <= 0.0:
            return None
        return min(2, int((6.0 - self._myth_age) // 2.0))

    def _draw_airplane_scene(self, surface: pygame.Surface) -> None:
        t = self._time

        # Gentle floating bob; the main action makes the plane hop up (only up,
        # so the wing never dips onto the action button below it).
        bob_y = math.sin(t * 2.5) * 7.0
        loop_offset_y = -math.sin(self._loop_age * math.pi * 0.5) * 35.0 if self._loop_age > 0.0 else 0.0
        dy = int(bob_y + loop_offset_y)

        if self._forces_age > 0.0:
            self._draw_altitude_overlay(surface, dy)
        if self._thrust_age > 0.0:
            self._draw_thrust_wake(surface, dy)

        aileron, elevator, rudder = self._control_pose()
        pose = PlanePose(
            dy=dy,
            propeller_frame=int(self._propeller_angle // 30.0) % PROPELLER_FRAMES,
            motion_disc=self._thrust_age > 0.0,
            aileron=aileron,
            elevator=elevator,
            rudder=rudder,
        )
        self._plane_renderer().draw(surface, pose)

        if self._airflow_age > 0.0:
            self._draw_lift_overlay(surface, dy)
        if self._myth_age > 0.0:
            self._draw_controls_overlay(surface, dy)
        if self._thrust_age > 0.0:
            self._draw_thrust_arrow(surface, dy)

    # Wings & lift: air hugs the curved wing, is pushed down, the plane goes up.
    def _draw_lift_overlay(self, surface: pygame.Surface, dy: int) -> None:
        t = self._time
        glow = SUNSHINE if int(t * 4) % 2 == 0 else SUNSHINE_LIGHT
        pygame.draw.lines(surface, glow, False, _shift(WING_TIP_UPPER, dy), 4)
        for offset, stream in enumerate((UPPER_STREAM, LOWER_STREAM)):
            points = _shift(stream, dy)
            pygame.draw.lines(surface, OCEAN_SHADE, False, points, 6)
            pygame.draw.lines(surface, WHITE, False, points, 3)
            # Two bright air "puffs" travel along each line, left to right.
            count = len(stream)
            for puff in range(2):
                index = int((t * 40 + puff * count / 2 + offset * 7) % (count - 3))
                pygame.draw.lines(surface, SUNSHINE_LIGHT, False, points[index:index + 4], 5)
        # Air pushed downward behind the wing ...
        drop = int((t * 30) % 10)
        _ink_arrow(surface, OCEAN_LIGHT, (628, 400 + dy + drop), (638, 430 + dy + drop), width=6, head=12)
        _ink_arrow(surface, OCEAN_LIGHT, (664, 404 + dy + drop), (674, 434 + dy + drop), width=6, head=12)
        # ... so the wing is lifted up.
        pulse = int(math.sin(t * 6.0) * 6)
        _ink_arrow(surface, LEAF, (530, 350 + dy), (530, 222 + dy - pulse), width=8, head=18)

    # Flight controls: the yellow surfaces swing and a curved arrow shows how.
    def _draw_controls_overlay(self, surface: pygame.Surface, dy: int) -> None:
        stage = self._control_stage()
        if stage == 0:  # elevator: climb / descend
            _swing_arrow(surface, (636, 312 + dy), 30, -40, 40)
        elif stage == 1:  # ailerons: roll to turn
            _swing_arrow(surface, (586, 362 + dy), 30, -40, 40)
        elif stage == 2:  # rudder: swing left / right
            _swing_arrow(surface, (641, 240 + dy), 32, 235, 305)

    # Altitude & clouds: icy cirrus up high, fluffy cumulus down low.
    def _draw_altitude_overlay(self, surface: pygame.Surface, dy: int) -> None:
        t = self._time
        x, top, bottom = 136, 112, 470
        middle = (top + bottom) // 2
        pygame.draw.line(surface, INK, (x, top), (x, bottom), 14)
        pygame.draw.circle(surface, INK, (x, top), 7)
        pygame.draw.line(surface, SKY_LIGHT, (x, top + 2), (x, middle), 9)
        pygame.draw.line(surface, (255, 246, 227), (x, middle), (x, bottom - 2), 9)
        for tick_y in range(top + 40, bottom, 60):
            pygame.draw.line(surface, INK, (x - 9, tick_y), (x + 9, tick_y), 3)
        # High end: cirrus wisps and an ice crystal (it is icy cold up there).
        for offset in (0, 9):
            pygame.draw.arc(surface, WHITE, (x - 34, top - 30 + offset, 40, 18), 0.4, 2.6, 3)
        self._draw_ice_crystal(surface, (x + 22, top - 18), 8)
        # Low end: a fluffy cumulus puff.
        for cx, cy, r in ((x - 14, bottom + 10, 11), (x + 2, bottom + 4, 15), (x + 18, bottom + 11, 10)):
            pygame.draw.circle(surface, INK, (cx, cy), r + 2)
        for cx, cy, r in ((x - 14, bottom + 10, 11), (x + 2, bottom + 4, 15), (x + 18, bottom + 11, 10)):
            pygame.draw.circle(surface, WHITE, (cx, cy), r)
        # The plane's own height marker rides the ruler.
        marker_y = PLANE_REST_CENTER[1] + dy
        marker = [(x + 12, marker_y), (x + 30, marker_y - 9), (x + 30, marker_y + 9)]
        pygame.draw.polygon(surface, SUNSHINE, marker)
        pygame.draw.polygon(surface, INK, marker, 3)
        # Twinkling ice crystals beside the authored high cirrus.
        for index, center in enumerate(_ICE_CRYSTALS):
            if int(t * 3 + index) % 3:
                self._draw_ice_crystal(surface, center, 9)

    @staticmethod
    def _draw_ice_crystal(surface: pygame.Surface, center: tuple[int, int], size: int) -> None:
        cx, cy = center
        for angle in (90, 30, 150):
            dx = math.cos(math.radians(angle)) * size
            dy = math.sin(math.radians(angle)) * size
            pygame.draw.line(surface, OCEAN_SHADE, (cx - dx, cy - dy), (cx + dx, cy + dy), 5)
        for angle in (90, 30, 150):
            dx = math.cos(math.radians(angle)) * size
            dy = math.sin(math.radians(angle)) * size
            pygame.draw.line(surface, WHITE, (cx - dx, cy - dy), (cx + dx, cy + dy), 2)

    # Engine & propeller: speed lines stream behind, the push points forward.
    def _draw_thrust_wake(self, surface: pygame.Surface, dy: int) -> None:
        t = self._time
        for index, (x, y, length) in enumerate(_THRUST_LINES):
            shift = int((t * 120 + index * 17) % 24)
            start = (x + shift, y + dy)
            end = (x + shift + length, y + dy)
            pygame.draw.line(surface, OCEAN_LIGHT, start, end, 7)
            pygame.draw.line(surface, WHITE, start, end, 3)

    def _draw_thrust_arrow(self, surface: pygame.Surface, dy: int) -> None:
        pulse = int(math.sin(self._time * 14.0) * 4)
        hub_y = PROPELLER_HUB[1] + dy
        _ink_arrow(surface, SUNSHINE, (348, hub_y), (300 + pulse, hub_y), width=8, head=17)

    @staticmethod
    def _draw_hotspot_icon(surface: pygame.Surface, item: AirplaneDiscovery) -> None:
        cx, cy = item.center
        if item.discovery_id == "lift":
            # Curved wing with an upward lift arrow
            wing = [(cx - 20, cy + 8), (cx - 14, cy - 2), (cx - 2, cy - 7), (cx + 12, cy - 4), (cx + 20, cy + 6), (cx + 2, cy + 6)]
            pygame.draw.polygon(surface, OCEAN, wing)
            pygame.draw.polygon(surface, INK, wing, 2)
            pygame.draw.line(surface, LEAF, (cx, cy + 4), (cx, cy - 16), 4)
            pygame.draw.polygon(surface, LEAF, [(cx - 6, cy - 12), (cx + 6, cy - 12), (cx, cy - 21)])
        elif item.discovery_id == "myth":
            # Tail fin with its yellow rudder swinging
            fin = [(cx - 14, cy + 12), (cx - 2, cy - 14), (cx + 4, cy - 14), (cx + 4, cy + 12)]
            pygame.draw.polygon(surface, OCEAN, fin)
            pygame.draw.polygon(surface, INK, fin, 2)
            rudder = [(cx + 4, cy - 14), (cx + 15, cy - 10), (cx + 15, cy + 10), (cx + 4, cy + 12)]
            pygame.draw.polygon(surface, SUNSHINE, rudder)
            pygame.draw.polygon(surface, INK, rudder, 2)
            pygame.draw.arc(surface, OCEAN_SHADE, (cx + 4, cy - 22, 24, 16), 0.3, 2.6, 2)
        elif item.discovery_id == "forces":
            # Cloud types: Cumulus down low, Cirrus up high
            pygame.draw.circle(surface, (255, 255, 255), (cx - 8, cy + 6), 8)
            pygame.draw.circle(surface, (255, 255, 255), (cx + 4, cy + 4), 10)
            pygame.draw.line(surface, (210, 235, 255), (cx - 12, cy - 12), (cx + 14, cy - 8), 2)
            pygame.draw.line(surface, (210, 235, 255), (cx - 6, cy - 6), (cx + 16, cy - 2), 2)
            pygame.draw.line(surface, (255, 195, 45), (cx - 14, cy + 12), (cx - 14, cy - 14), 2)
            pygame.draw.polygon(surface, (255, 195, 45), [(cx - 17, cy - 11), (cx - 11, cy - 11), (cx - 14, cy - 16)])
        else:
            # Engine & propeller pushing forward
            pygame.draw.circle(surface, OCEAN_SHADE, (cx + 10, cy), 9)
            pygame.draw.line(surface, OCEAN_SHADE, (cx + 2, cy - 15), (cx + 2, cy + 15), 4)
            pygame.draw.circle(surface, SUNSHINE, (cx + 2, cy), 4)
            pygame.draw.line(surface, (255, 195, 45), (cx - 4, cy), (cx - 16, cy), 3)
            pygame.draw.polygon(surface, (255, 195, 45), [(cx - 12, cy - 5), (cx - 12, cy + 5), (cx - 19, cy)])

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (255, 250, 238), item.center, 38)
            pygame.draw.circle(surface, (88, 68, 52), item.center, 38, 3)
            self._draw_hotspot_icon(surface, item)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
        )
