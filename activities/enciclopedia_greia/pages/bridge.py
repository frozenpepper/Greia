"""Bridge entry: child-friendly storybook bridge over water connecting friends."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
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
        draw_caption_ribbon,
        draw_machine_action_button,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class BridgeDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    BridgeDiscovery("load", "bridge.load", "encyclopedia.machines.bridge.load", (240, 185)),
    BridgeDiscovery("shapes", "bridge.shapes", "encyclopedia.machines.bridge.shapes", (765, 185)),
    BridgeDiscovery("forces", "bridge.forces", "encyclopedia.machines.bridge.forces", (240, 420)),
    BridgeDiscovery("path", "bridge.path", "encyclopedia.machines.bridge.path", (765, 420)),
)


class BridgeLoadModel:
    """Owns bridge interaction state: little car driving, rainbow arch, sturdy pillars, and friends."""

    SHAPES = ("arch", "beam", "truss")

    def __init__(self) -> None:
        self.shape_index = 0
        # Car dynamics
        self.car_progress = 0.50     # 0.15 (left bank) to 0.85 (right bank)
        self.car_target = 0.50
        self.car_driving = False
        self.car_beep_age = 0.0

        # Feature ages
        self.load_age = 0.0          # little car focus
        self.shapes_age = 0.0        # rainbow arch glow
        self.forces_age = 0.0        # sturdy pillars water splash
        self.path_age = 0.0          # connecting friends

    @property
    def shape(self) -> str:
        return self.SHAPES[self.shape_index]

    @property
    def load_position(self) -> float:
        return self.car_progress

    def update(self, dt: float) -> None:
        self.load_age = max(0.0, self.load_age - dt)
        self.shapes_age = max(0.0, self.shapes_age - dt)
        self.forces_age = max(0.0, self.forces_age - dt)
        self.path_age = max(0.0, self.path_age - dt)
        self.car_beep_age = max(0.0, self.car_beep_age - dt)

        # Smooth car driving animation across the bridge
        if self.car_driving:
            diff = self.car_target - self.car_progress
            if abs(diff) > 0.01:
                direction = 1.0 if diff > 0 else -1.0
                step = direction * dt * 0.40
                if abs(step) >= abs(diff):
                    self.car_progress = self.car_target
                    self.car_driving = False
                else:
                    self.car_progress += step
            else:
                self.car_progress = self.car_target
                self.car_driving = False

    def place_load(self) -> None:
        """Called when the child activates the little car."""
        self.load_age = 6.0
        self.car_beep_age = 2.5
        if self.car_progress > 0.75:
            self.car_target = 0.20
        else:
            self.car_target = min(0.82, self.car_progress + 0.32)
        self.car_driving = True

    def next_shape(self) -> None:
        """Called when child activates the rainbow arch shape."""
        self.shape_index = (self.shape_index + 1) % len(self.SHAPES)
        self.shapes_age = 6.0

    def reveal_forces(self) -> None:
        """Called when child activates the sturdy pillars."""
        self.forces_age = 6.0

    def reveal_path(self) -> None:
        """Called when child activates the connecting path for friends."""
        self.path_age = 6.0


class BridgePage(EncyclopediaPage):
    page_id = "machines.bridge"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._model = BridgeLoadModel()
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "bridge.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = 0.0
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._bridge_rect = pygame.Rect(310, 310, 400, 150)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.machines.bridge.intro")
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
        self._model.place_load()
        self._activate(0)

    def update(self, dt: float) -> None:
        self._time += dt
        self._model.update(dt)

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
                if self._bridge_rect.collidepoint(point):
                    self._model.place_load()
                    self._activate(0)
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
        if item.discovery_id == "load":
            self._model.place_load()
        elif item.discovery_id == "shapes":
            self._model.next_shape()
        elif item.discovery_id == "forces":
            self._model.reveal_forces()
        else:
            self._model.reveal_path()
        self.context.audio.play(item.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        # 1. Warm, soft sunny sky
        surface.fill((230, 244, 252))

        # Distant soft rolling hills
        pygame.draw.ellipse(surface, (196, 226, 185), (40, 230, 480, 160))
        pygame.draw.ellipse(surface, (180, 216, 168), (480, 220, 520, 180))

        # Drifting fluffy white clouds
        t = self._time
        cloud1_x = int((120 + t * 6) % 1100) - 80
        cloud2_x = int((650 + t * 4) % 1100) - 80
        self._draw_cloud(surface, cloud1_x, 110, 65)
        self._draw_cloud(surface, cloud2_x, 135, 52)

        # Title at the top
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("bridge.title"),
            center=(512, 68),
            size=36,
            color=(61, 44, 31),
            role=FontRole.DISPLAY,
        )

        # 2. Draw river, riverbanks, bridge, and cute vehicle
        self._draw_bridge_scene(surface)

        # 3. Discovery Tokens
        self._draw_hotspots(surface)

        # 4. Navigation controls and action button
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=self._time, can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_machine_action_button(
            surface, (512, 460), machine="bridge", time=self._time, active=True
        )

        # 5. Caption Ribbon
        self._draw_caption(surface)

        # 6. Presenter Dani (smiling and happy)
        draw_presenter(
            surface,
            self.context.visuals,
            "dani",
            position=(925, 565),
            height=142,
            variant="happy",
            fallback_color=(101, 171, 211),
        )

    def _draw_cloud(self, surface: pygame.Surface, cx: int, cy: int, size: int) -> None:
        s = pygame.Surface((size * 2, size), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 255, 255, 220), (size // 2, size // 2), size // 3)
        pygame.draw.circle(s, (255, 255, 255, 240), (size, size // 2 - 4), size // 2)
        pygame.draw.circle(s, (255, 255, 255, 220), (size + size // 2, size // 2), size // 3)
        surface.blit(s, (cx - size, cy - size // 2))

    def _draw_bridge_scene(self, surface: pygame.Surface) -> None:
        t = self._time

        # River Water Base (flowing all the way down across the center)
        river_points = [(260, 340), (764, 340), (780, 600), (244, 600)]
        pygame.draw.polygon(surface, (68, 155, 208), river_points)
        # Deep water stripe
        pygame.draw.polygon(surface, (52, 138, 192), [(270, 380), (754, 380), (770, 600), (254, 600)])

        # Animated sparkling water waves
        for row in range(5):
            y_base = 358 + row * 26
            offset_x = math.sin(t * 1.5 + row * 1.2) * 16
            for col in range(5):
                wx = 300 + col * 90 + offset_x
                pygame.draw.arc(surface, (150, 220, 255), (wx, y_base, 36, 12), math.pi, math.tau, 3)

        # Cheerful yellow rubber duck swimming in the river!
        duck_x = int(430 + math.sin(t * 0.9) * 45)
        duck_y = int(418 + math.cos(t * 2.2) * 3)
        pygame.draw.circle(surface, (255, 214, 46), (duck_x, duck_y), 11)
        pygame.draw.circle(surface, (255, 214, 46), (duck_x + 9, duck_y - 7), 7)
        pygame.draw.polygon(surface, (247, 132, 32), [(duck_x + 15, duck_y - 8), (duck_x + 21, duck_y - 6), (duck_x + 15, duck_y - 4)])
        pygame.draw.circle(surface, (40, 30, 25), (duck_x + 11, duck_y - 8), 1.5)
        pygame.draw.ellipse(surface, (170, 230, 255), (duck_x - 14, duck_y + 6, 28, 6), 2)

        # Grassy Riverbanks on left and right
        left_bank_points = [(0, 600), (0, 340), (140, 335), (280, 350), (290, 420), (270, 520), (250, 600)]
        pygame.draw.polygon(surface, (116, 182, 86), left_bank_points)
        pygame.draw.polygon(surface, (142, 208, 108), [(0, 340), (140, 335), (280, 350), (285, 365), (140, 350), (0, 355)])

        right_bank_points = [(1024, 600), (1024, 340), (880, 335), (744, 350), (734, 420), (754, 520), (774, 600)]
        pygame.draw.polygon(surface, (116, 182, 86), right_bank_points)
        pygame.draw.polygon(surface, (142, 208, 108), [(1024, 340), (880, 335), (744, 350), (739, 365), (880, 350), (1024, 355)])

        # Flowers on grassy banks
        for fx, fy, col in ((100, 370, (248, 86, 114)), (180, 385, (255, 222, 60)), (240, 375, (255, 255, 255)),
                            (780, 375, (255, 255, 255)), (840, 385, (255, 222, 60)), (920, 370, (248, 86, 114))):
            pygame.draw.circle(surface, col, (fx, fy), 4)
            pygame.draw.circle(surface, (255, 200, 40), (fx, fy), 2)

        left_x, right_x = 310, 714
        deck_y = 350

        # Two Sturdy Warm Brick/Stone Pillars
        for tx in (left_x + 70, right_x - 110):
            pygame.draw.ellipse(surface, (40, 105, 145), (tx - 6, deck_y + 68, 52, 16))
            pygame.draw.rect(surface, (208, 92, 66), (tx, deck_y + 12, 40, 64), border_radius=4)
            for my in (deck_y + 26, deck_y + 44, deck_y + 60):
                pygame.draw.line(surface, (168, 64, 42), (tx + 2, my), (tx + 38, my), 2)
            pygame.draw.rect(surface, (248, 240, 228), (tx - 4, deck_y + 8, 48, 10), border_radius=3)
            pygame.draw.rect(surface, (168, 64, 42), (tx - 4, deck_y + 8, 48, 10), width=2, border_radius=3)

            # Pillar water splashes if "forces" active
            if self._model.forces_age > 0.0:
                sw = 56 + math.sin(t * 8.0) * 8
                pygame.draw.ellipse(surface, (210, 245, 255), (tx - 8, deck_y + 66, int(sw), 14), 3)

        # Bridge Arch Underneath
        arch_rect = pygame.Rect(left_x + 50, deck_y - 10, (right_x - left_x) - 100, 90)
        pygame.draw.arc(surface, (188, 76, 52), arch_rect, 0, math.pi, 14)
        pygame.draw.arc(surface, (238, 228, 214), arch_rect, 0, math.pi, 3)

        # If "shapes" (Arch Load Distribution) is active, show force spreading along the arch to banks!
        if self._model.shapes_age > 0.0:
            # Glowing arch path
            pygame.draw.arc(surface, (255, 205, 60), arch_rect.inflate(8, 8), 0.05, math.pi - 0.05, 6)
            # Animated force flow chevrons flowing outward from center towards the abutments
            for s_idx in range(9):
                ang = math.pi * (0.12 + s_idx * 0.095)
                sx = arch_rect.centerx + int(math.cos(ang) * (arch_rect.width // 2))
                sy = arch_rect.centery - int(math.sin(ang) * (arch_rect.height // 2))
                # Pulse offset along curve
                flow_pulse = math.sin(t * 8.0 + (s_idx if ang > math.pi/2 else -s_idx)) * 3
                pygame.draw.circle(surface, (255, 245, 180), (sx, int(sy + flow_pulse)), 4)
                pygame.draw.circle(surface, (238, 120, 34), (sx, int(sy + flow_pulse)), 2)

            # Force distribution arrows pointing outward to riverbanks
            pygame.draw.polygon(surface, (238, 120, 34), [(left_x + 54, deck_y + 36), (left_x + 40, deck_y + 44), (left_x + 56, deck_y + 48)])
            pygame.draw.polygon(surface, (238, 120, 34), [(right_x - 54, deck_y + 36), (right_x - 40, deck_y + 44), (right_x - 56, deck_y + 48)])

        # Bridge Road Deck
        pygame.draw.line(surface, (178, 74, 52), (left_x, deck_y + 10), (right_x, deck_y + 10), 10)
        pygame.draw.line(surface, (58, 65, 72), (left_x, deck_y), (right_x, deck_y), 12)
        for rx in range(left_x + 10, right_x - 10, 24):
            pygame.draw.line(surface, (255, 255, 255), (rx, deck_y), (rx + 14, deck_y), 2)

        # White picket railing
        pygame.draw.line(surface, (248, 244, 236), (left_x, deck_y - 10), (right_x, deck_y - 10), 4)
        for rx in range(left_x + 8, right_x, 16):
            pygame.draw.line(surface, (248, 244, 236), (rx, deck_y + 2), (rx, deck_y - 10), 3)

        # Golden Lamp Posts on the pillars
        for lx in (left_x + 88, right_x - 92):
            pygame.draw.line(surface, (68, 52, 40), (lx, deck_y - 10), (lx, deck_y - 28), 3)
            pygame.draw.circle(surface, (255, 235, 120), (lx, deck_y - 30), 6)
            pygame.draw.circle(surface, (255, 255, 255), (lx - 1, deck_y - 32), 2)

        # If "forces" (Pillars & Bedrock) active, reveal underground bedrock anchors and downward load arrows!
        if self._model.forces_age > 0.0:
            for tx in (left_x + 88, right_x - 92):
                # Subterranean bedrock anchor block
                pygame.draw.rect(surface, (135, 115, 95), (tx - 26, deck_y + 78, 52, 28), border_radius=4)
                pygame.draw.rect(surface, (95, 78, 65), (tx - 26, deck_y + 78, 52, 28), width=2, border_radius=4)
                for rx in range(tx - 20, tx + 20, 10):
                    pygame.draw.line(surface, (160, 140, 120), (rx, deck_y + 82), (rx + 6, deck_y + 102), 2)
                # Downward force arrows discharging weight to rock
                pulse_y = int((math.sin(t * 8.0) * 0.5 + 0.5) * 8)
                pygame.draw.line(surface, (255, 220, 60), (tx, deck_y + 20), (tx, deck_y + 70 + pulse_y), 4)
                pygame.draw.polygon(surface, (255, 220, 60), [(tx - 6, deck_y + 64 + pulse_y), (tx + 6, deck_y + 64 + pulse_y), (tx, deck_y + 74 + pulse_y)])

        # If "path" (Steel Cables & Tension) is active, draw glowing tension cables pulling upward!
        if self._model.path_age > 0.0:
            # Main suspension cable catenary curves
            for tower_x in (left_x + 88, right_x - 92):
                pygame.draw.line(surface, (255, 215, 60), (tower_x, deck_y - 28), (tower_x - 80, deck_y), 3)
                pygame.draw.line(surface, (255, 215, 60), (tower_x, deck_y - 28), (512, deck_y - 4), 3)
            # Vertical tension hanger cables with upward chevrons
            for hx in range(left_x + 30, right_x - 20, 32):
                pygame.draw.line(surface, (255, 235, 140), (hx, deck_y - 2), (hx, deck_y - 18), 2)
                # Upward tension chevron ^
                pygame.draw.lines(surface, (255, 215, 60), False, [(hx - 4, deck_y - 10), (hx, deck_y - 15), (hx + 4, deck_y - 10)], 2)

        # THE CUTE TOY VEHICLE (Car / Load)
        car_x = int(left_x + (right_x - left_x) * self._model.car_progress)
        car_bounce = math.sin(t * 14.0) * 2 if self._model.car_driving else 0
        car_y = deck_y - 16 + int(car_bounce)

        self._draw_cute_car(surface, car_x, car_y)

        # Downward load / weight vector pressing on the bridge
        if self._model.load_age > 0.0 or self._model.car_driving:
            arrow_pulse = int(math.sin(t * 10.0) * 3)
            # Downward bold arrow
            pygame.draw.line(surface, (235, 75, 55), (car_x, car_y - 32 + arrow_pulse), (car_x, car_y - 10 + arrow_pulse), 4)
            pygame.draw.polygon(surface, (235, 75, 55), [(car_x - 6, car_y - 14 + arrow_pulse), (car_x + 6, car_y - 14 + arrow_pulse), (car_x, car_y - 6 + arrow_pulse)])

        self._draw_cute_car(surface, car_x, car_y)

        # Beep-beep speech bubble if car recently beeped
        if self._model.car_beep_age > 0.0:
            bubble_y = car_y - 32
            pygame.draw.ellipse(surface, (255, 252, 235), (car_x - 24, bubble_y, 48, 22))
            pygame.draw.ellipse(surface, (80, 65, 50), (car_x - 24, bubble_y, 48, 22), 2)
            pygame.draw.circle(surface, (232, 68, 56), (car_x - 8, bubble_y + 11), 3)
            pygame.draw.line(surface, (232, 68, 56), (car_x - 5, bubble_y + 11), (car_x - 5, bubble_y + 4), 2)
            pygame.draw.circle(surface, (232, 68, 56), (car_x + 8, bubble_y + 9), 3)
            pygame.draw.line(surface, (232, 68, 56), (car_x + 11, bubble_y + 9), (car_x + 11, bubble_y + 3), 2)
            pygame.draw.line(surface, (232, 68, 56), (car_x - 5, bubble_y + 4), (car_x + 11, bubble_y + 3), 2)

    def _draw_cute_car(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        pygame.draw.ellipse(surface, (30, 40, 48, 120), (cx - 24, cy + 12, 48, 8))
        pygame.draw.rect(surface, (232, 68, 56), (cx - 22, cy, 44, 14), border_radius=5)
        pygame.draw.rect(surface, (255, 250, 238), (cx - 14, cy - 12, 28, 14), border_radius=6)
        pygame.draw.rect(surface, (180, 40, 32), (cx - 22, cy, 44, 14), width=2, border_radius=5)
        pygame.draw.rect(surface, (180, 40, 32), (cx - 14, cy - 12, 28, 14), width=2, border_radius=6)

        pygame.draw.rect(surface, (110, 205, 250), (cx + 1, cy - 10, 11, 8), border_radius=3)
        pygame.draw.rect(surface, (110, 205, 250), (cx - 12, cy - 10, 11, 8), border_radius=3)
        pygame.draw.line(surface, (255, 255, 255), (cx + 3, cy - 8), (cx + 9, cy - 8), 1)

        pygame.draw.circle(surface, (50, 30, 30), (cx - 4, cy + 5), 1.5)
        pygame.draw.circle(surface, (50, 30, 30), (cx + 4, cy + 5), 1.5)
        pygame.draw.arc(surface, (50, 30, 30), (cx - 3, cy + 4, 6, 4), math.pi, math.tau, 1)

        pygame.draw.circle(surface, (255, 225, 60), (cx + 21, cy + 6), 3.5)
        pygame.draw.circle(surface, (255, 255, 255), (cx + 20, cy + 5), 1.5)

        for wx in (cx - 14, cx + 14):
            pygame.draw.circle(surface, (36, 40, 44), (wx, cy + 13), 6)
            pygame.draw.circle(surface, (240, 244, 248), (wx, cy + 13), 3)
            pygame.draw.circle(surface, (36, 40, 44), (wx, cy + 13), 1)

        if self._model.car_driving:
            smoke_x = cx - 28 + int(math.sin(self._time * 20.0) * 3)
            smoke_y = cy + 6
            pygame.draw.circle(surface, (255, 255, 255, 180), (smoke_x, smoke_y), 4)
            pygame.draw.circle(surface, (255, 255, 255, 120), (smoke_x - 7, smoke_y - 3), 3)

    def _draw_heart(self, surface: pygame.Surface, cx: int, cy: int, size: int, color: tuple[int, int, int]) -> None:
        left_circle = (cx - size // 2, cy - size // 2)
        right_circle = (cx + size // 2, cy - size // 2)
        pygame.draw.circle(surface, color, left_circle, size // 2 + 1)
        pygame.draw.circle(surface, color, right_circle, size // 2 + 1)
        triangle = [
            (cx - size, cy - size // 4),
            (cx + size, cy - size // 4),
            (cx, cy + size),
        ]
        pygame.draw.polygon(surface, color, triangle)

    @staticmethod
    def _draw_hotspot_icon(surface: pygame.Surface, item: BridgeDiscovery) -> None:
        cx, cy = item.center
        if item.discovery_id == "load":
            # Car with downward weight arrow
            pygame.draw.rect(surface, (232, 68, 56), (cx - 14, cy, 28, 10), border_radius=3)
            pygame.draw.rect(surface, (255, 250, 238), (cx - 9, cy - 8, 18, 9), border_radius=3)
            pygame.draw.circle(surface, (40, 44, 48), (cx - 8, cy + 10), 3)
            pygame.draw.circle(surface, (40, 44, 48), (cx + 8, cy + 10), 3)
            # Downward weight arrow
            pygame.draw.line(surface, (255, 195, 45), (cx, cy - 22), (cx, cy - 10), 3)
            pygame.draw.polygon(surface, (255, 195, 45), [(cx - 4, cy - 13), (cx + 4, cy - 13), (cx, cy - 8)])
        elif item.discovery_id == "shapes":
            # Arch with outward curved load distribution arrows
            pygame.draw.arc(surface, (217, 90, 63), (cx - 18, cy - 10, 36, 22), 0, math.pi, 4)
            pygame.draw.line(surface, (60, 65, 70), (cx - 20, cy + 4), (cx + 20, cy + 4), 2)
            # Outward distribution chevrons
            pygame.draw.line(surface, (255, 195, 45), (cx - 16, cy + 12), (cx - 6, cy + 12), 2)
            pygame.draw.polygon(surface, (255, 195, 45), [(cx - 13, cy + 9), (cx - 13, cy + 15), (cx - 18, cy + 12)])
            pygame.draw.line(surface, (255, 195, 45), (cx + 6, cy + 12), (cx + 16, cy + 12), 2)
            pygame.draw.polygon(surface, (255, 195, 45), [(cx + 13, cy + 9), (cx + 13, cy + 15), (cx + 18, cy + 12)])
        elif item.discovery_id == "forces":
            # Pillar column rooted in bedrock
            pygame.draw.rect(surface, (190, 80, 56), (cx - 10, cy - 16, 20, 22), border_radius=2)
            pygame.draw.rect(surface, (248, 240, 228), (cx - 12, cy - 18, 24, 4), border_radius=2)
            # Bedrock foundation block
            pygame.draw.rect(surface, (120, 105, 90), (cx - 16, cy + 6, 32, 12), border_radius=3)
            # Downward force arrow
            pygame.draw.line(surface, (255, 215, 60), (cx, cy - 8), (cx, cy + 4), 3)
            pygame.draw.polygon(surface, (255, 215, 60), [(cx - 4, cy + 1), (cx + 4, cy + 1), (cx, cy + 6)])
        else:
            # Suspension cables pulling upward in tension
            pygame.draw.line(surface, (60, 65, 70), (cx - 20, cy + 8), (cx + 20, cy + 8), 3)
            pygame.draw.line(surface, (255, 195, 45), (cx - 18, cy - 16), (cx, cy + 4), 2)
            pygame.draw.line(surface, (255, 195, 45), (cx + 18, cy - 16), (cx, cy + 4), 2)
            pygame.draw.line(surface, (255, 215, 80), (cx - 9, cy - 6), (cx - 9, cy + 8), 2)
            pygame.draw.line(surface, (255, 215, 80), (cx + 9, cy - 6), (cx + 9, cy + 8), 2)
            # Upward tension chevron
            pygame.draw.lines(surface, (255, 195, 45), False, [(cx - 5, cy - 10), (cx, cy - 16), (cx + 5, cy - 10)], 2)

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
