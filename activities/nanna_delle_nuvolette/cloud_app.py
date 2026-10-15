"""Main application and interaction loop for Nanna delle Nuvolette."""

from __future__ import annotations

import math
import time
from uuid import uuid4

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.input_core import InputEdge, InteractionProfile, SemanticAction
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.pygame_input import PygameInputTranslator
from greia_platform.typography import GreiaTypography

if __package__:
    from .cloud_audio import CloudAudio
    from .cloud_content import BLANKETS
    from .cloud_model import NightScene, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .cloud_renderer import BASKET_RECT, CLOUD_RECTS, MOON_RECT, CloudRenderer
    from .cloud_services import GreiaCloudEvents, GreiaCloudStorage
else:
    from cloud_audio import CloudAudio
    from cloud_content import BLANKETS
    from cloud_model import NightScene, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from cloud_renderer import BASKET_RECT, CLOUD_RECTS, MOON_RECT, CloudRenderer
    from cloud_services import GreiaCloudEvents, GreiaCloudStorage


def _is_safe_point(screen: pygame.Surface, pos: tuple[int, int]) -> bool:
    """Reject platform-protected coordinates without claiming Home ownership."""
    viewport = activity_viewport_for_surface(screen)
    x, y = pos
    return (
        0 <= x < viewport.surface.width
        and 0 <= y < viewport.surface.height
        and not any(r.x <= x < r.right and r.y <= y < r.bottom for r in viewport.protected_regions)
    )


# A press that moves less than this (reference px) before release is a tap, not
# a drag: the picked-up blanket/star stays in hand for a tap on a cloud.
DRAG_THRESHOLD_PX = 14

_FOCUS_STEP = {
    SemanticAction.NAV_LEFT: -1,
    SemanticAction.NAV_UP: -1,
    SemanticAction.NAV_RIGHT: 1,
    SemanticAction.NAV_DOWN: 1,
}


class CloudActivity:
    """Bedtime cloud play activity for age-three calm play."""

    def __init__(
        self,
        screen: pygame.Surface,
        renderer: CloudRenderer,
        audio: CloudAudio,
        events: GreiaCloudEvents,
        storage: GreiaCloudStorage,
        *,
        night_id: str = "night-001",
        clock=time.monotonic,
    ) -> None:
        self.screen = screen
        self.canvas = PygameReferenceCanvas(screen)
        self.renderer = renderer
        self.audio = audio
        self.events = events
        self.storage = storage
        self.night_id = night_id
        self.clock = clock

        self.scene = NightScene.create_night(night_id)
        self._running = True
        self._ready_published = False
        self._dirty = True

        self._selected_blanket_idx: int | None = None
        self._holding_star: bool = False
        self._drag_pos: tuple[int, int] | None = None

        self._hovered_cloud: int | None = None
        self._hovered_blanket: int | None = None
        self._hovered_basket: bool = False
        self._hovered_moon: bool = False

        # Pointer press origin (to tell a tap from a drag) and keyboard /
        # controller focus over the same targets the pointer can hit.
        self._press_point: tuple[int, int] | None = None
        self._focus: int | None = None
        # Pointer Activities still get a learned focus context for their
        # controls (arrows / D-pad move focus, Space / south button activate).
        self._translator = PygameInputTranslator(InteractionProfile.NAVIGATION)

        # Yawn animation tracking for 3 clouds (progress 0.0 .. 1.0)
        self._yawn_starts: list[float | None] = [None, None, None]
        self._completed_emitted: bool = False

    def run(self) -> int:
        ticker = pygame.time.Clock()
        while self._running and not activity_stop_requested():
            for event in pygame.event.get():
                self._handle_event(event)

            if self._advance_animation():
                self._dirty = True

            if self._dirty:
                self._render()
                self.canvas.present()
                pygame.display.flip()
                self._dirty = False
                if not self._ready_published:
                    mark_activity_ready()
                    self._ready_published = True

            ticker.tick(30)
        return 0

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            # Cancel held item or exit if not holding anything
            if self._selected_blanket_idx is not None or self._holding_star:
                self._selected_blanket_idx = None
                self._holding_star = False
                self._drag_pos = None
                self._dirty = True
            else:
                self._running = False
            return

        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.get_surface() or self.screen
            self.canvas = PygameReferenceCanvas(self.screen)
            self._dirty = True
            return

        if event.type == pygame.WINDOWFOCUSLOST:
            self._cancel_held_item()
            return

        semantic = self._translator.digital(event)
        if semantic is not None:
            self._handle_semantic(semantic.action, semantic.edge)
            return

        if event.type == pygame.MOUSEMOTION:
            if not _is_safe_point(self.screen, event.pos):
                return
            logical = self.canvas.pointer(event.pos)
            if logical is not None:
                point = (int(logical[0]), int(logical[1]))
                if self._selected_blanket_idx is not None or self._holding_star:
                    self._drag_pos = point
                else:
                    self._drag_pos = None

                new_c = self.renderer.cloud_at(point)
                new_b = self.renderer.blanket_at(point)
                new_bsk = self.renderer.basket_contains(point)
                new_m = self.renderer.moon_contains(point) if self.scene.all_asleep else False

                if (
                    new_c != self._hovered_cloud
                    or new_b != self._hovered_blanket
                    or new_bsk != self._hovered_basket
                    or new_m != self._hovered_moon
                    or self._drag_pos is not None
                ):
                    self._hovered_cloud = new_c
                    self._hovered_blanket = new_b
                    self._hovered_basket = new_bsk
                    self._hovered_moon = new_m
                    self._dirty = True
            return

        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
            if event.type == pygame.MOUSEBUTTONDOWN and event.button != 1:
                return
            pos = self._event_position(event)
            if not _is_safe_point(self.screen, pos):
                return
            logical = self.canvas.pointer(pos)
            if logical is not None:
                point = (int(logical[0]), int(logical[1]))
                self._press_point = point
                self._focus = None
                if self._handle_pointer_click(point):
                    self._dirty = True
            return

        if event.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
            if event.type == pygame.MOUSEBUTTONUP and event.button != 1:
                return
            pos = self._event_position(event)
            if not _is_safe_point(self.screen, pos):
                self._cancel_held_item()
                return
            logical = self.canvas.pointer(pos)
            if logical is None:
                self._cancel_held_item()
                return
            point = (int(logical[0]), int(logical[1]))
            if self._handle_pointer_drop(point):
                self._dirty = True

    # ------------------------------------------------------------------
    # Keyboard / controller focus
    # ------------------------------------------------------------------

    def _focus_targets(self) -> list[tuple[str, int, pygame.Rect]]:
        """Focusable targets in reading order: blankets, star basket, clouds, moon."""
        targets: list[tuple[str, int, pygame.Rect]] = [
            ("blanket", idx, self.renderer.blanket_rect_at(idx))
            for idx in range(len(BLANKETS))
        ]
        targets.append(("basket", 0, BASKET_RECT))
        targets.extend(("cloud", idx, rect) for idx, rect in enumerate(CLOUD_RECTS))
        if self.scene.all_asleep:
            targets.append(("moon", 0, MOON_RECT))
        return targets

    def _handle_semantic(self, action: SemanticAction, edge: InputEdge) -> None:
        if edge is not InputEdge.PRESSED:
            return
        step = _FOCUS_STEP.get(action)
        if step is not None:
            targets = self._focus_targets()
            if self._focus is None:
                self._focus = 0 if step > 0 else len(targets) - 1
            else:
                self._focus = (self._focus + step) % len(targets)
            self._apply_focus(targets)
            self.audio.play("chime")
            return
        if action is SemanticAction.ACTIVATE:
            targets = self._focus_targets()
            if self._focus is None or self._focus >= len(targets):
                self._focus = 0
                self._apply_focus(targets)
                return
            point = targets[self._focus][2].center
            self._handle_pointer_click(point)
            # The set of targets can change (the moon appears at the end).
            self._apply_focus(self._focus_targets())
            return
        if action is SemanticAction.CANCEL:
            self._cancel_held_item()

    def _apply_focus(self, targets: list[tuple[str, int, pygame.Rect]]) -> None:
        """Mirror keyboard focus into the pointer hover highlight state."""
        self._hovered_cloud = self._hovered_blanket = None
        self._hovered_basket = self._hovered_moon = False
        if self._focus is not None and self._focus < len(targets):
            kind, idx, rect = targets[self._focus]
            if kind == "blanket":
                self._hovered_blanket = idx
            elif kind == "cloud":
                self._hovered_cloud = idx
            elif kind == "basket":
                self._hovered_basket = True
            elif kind == "moon":
                self._hovered_moon = True
            if self._selected_blanket_idx is not None or self._holding_star:
                self._drag_pos = rect.center
        self._dirty = True

    def _event_position(self, event: pygame.event.Event) -> tuple[int, int]:
        position = getattr(event, "pos", None)
        if position is not None:
            return (int(position[0]), int(position[1]))
        width, height = self.screen.get_size()
        return (int(event.x * width), int(event.y * height))

    def _cancel_held_item(self) -> None:
        if self._selected_blanket_idx is not None or self._holding_star or self._drag_pos is not None:
            self._selected_blanket_idx = None
            self._holding_star = False
            self._drag_pos = None
            self._dirty = True

    def _handle_pointer_click(self, point: tuple[int, int]) -> bool:
        # 1. Click on Moon (new night) if all asleep
        if self.scene.all_asleep and self.renderer.moon_contains(point):
            self._start_new_night()
            return True

        # 2. Click on Blanket Card
        b_idx = self.renderer.blanket_at(point)
        if b_idx is not None:
            self._selected_blanket_idx = b_idx
            self._holding_star = False
            self._drag_pos = point
            self.audio.play("rustle")
            return True

        # 3. Click on Star Basket
        if self.renderer.basket_contains(point):
            if self.scene.available_stars > 0:
                self._holding_star = True
                self._selected_blanket_idx = None
                self._drag_pos = point
                self.audio.play("star")
                return True
            return False

        # 4. Click on Cloud Friend
        c_idx = self.renderer.cloud_at(point)
        if c_idx is not None:
            cloud = self.scene.clouds[c_idx]
            # If holding blanket, tuck it in
            if self._selected_blanket_idx is not None and self._selected_blanket_idx < len(BLANKETS):
                b = BLANKETS[self._selected_blanket_idx]
                if self.scene.tuck_blanket(cloud.cloud_id, b.blanket_id):
                    self.audio.play("rustle")
                    self._selected_blanket_idx = None
                    self._drag_pos = None
                    return True

            # If holding star, attach it
            if self._holding_star:
                if self.scene.add_star(cloud.cloud_id):
                    self.audio.play("star")
                    self._holding_star = False
                    self._drag_pos = None
                    return True

            # If not holding anything, tap to put to sleep if ready
            if not cloud.asleep and self._yawn_starts[c_idx] is None:
                if cloud.ready_to_sleep:
                    self._yawn_starts[c_idx] = self.clock()
                    self.audio.play("yawn")
                    return True
                else:
                    # Neutral hint feedback
                    cloud.trigger_hint(self.clock())
                    self.audio.play("chime")
                    return True

        return False

    def _handle_pointer_drop(self, point: tuple[int, int]) -> bool:
        press, self._press_point = self._press_point, None
        dragged = (
            press is not None
            and math.hypot(point[0] - press[0], point[1] - press[1]) > DRAG_THRESHOLD_PX
        )
        if not dragged:
            # A plain tap: the item picked up on press stays in hand so the next
            # tap on a cloud tucks/attaches it (tap-then-tap works like drag).
            return True
        c_idx = self.renderer.cloud_at(point)
        if c_idx is not None:
            cloud = self.scene.clouds[c_idx]
            if self._selected_blanket_idx is not None and self._selected_blanket_idx < len(BLANKETS):
                b = BLANKETS[self._selected_blanket_idx]
                if self.scene.tuck_blanket(cloud.cloud_id, b.blanket_id):
                    self.audio.play("rustle")
                    self._selected_blanket_idx = None
                    self._drag_pos = None
                    return True
            if self._holding_star:
                if self.scene.add_star(cloud.cloud_id):
                    self.audio.play("star")
                    self._holding_star = False
                    self._drag_pos = None
                    return True

        # Drop into empty space cancels drag
        self._cancel_held_item()
        return True

    def _advance_animation(self) -> bool:
        changed = False
        now = self.clock()

        for idx, start_t in enumerate(self._yawn_starts):
            if start_t is not None:
                elapsed = now - start_t
                if elapsed >= 0.80:
                    self._yawn_starts[idx] = None
                    cloud = self.scene.clouds[idx]
                    self.scene.put_to_sleep(cloud.cloud_id)
                    changed = True
                    self._check_all_asleep()
                else:
                    changed = True

        return changed

    def _check_all_asleep(self) -> None:
        if self.scene.all_asleep and not self._completed_emitted:
            self._completed_emitted = True
            total_stars = sum(len(c.star_ids) for c in self.scene.clouds)
            self.events.rest_completed(
                self.night_id,
                {
                    "night_id": self.night_id,
                    "cloud_count": 3,
                    "star_count": total_stars,
                },
            )
            # Persist preferences
            b_ids = tuple(c.blanket_id for c in self.scene.clouds if c.blanket_id)
            if len(b_ids) == 3:
                self.storage.save_preferences(b_ids)
            self.audio.play("chime")

    def _start_new_night(self) -> None:
        self.night_id = f"night-{uuid4().hex}"
        self.scene = NightScene.create_night(self.night_id)
        self._yawn_starts = [None, None, None]
        self._completed_emitted = False
        self._selected_blanket_idx = None
        self._holding_star = False
        self._drag_pos = None
        self._dirty = True
        self.audio.play("chime")

    def _render(self) -> None:
        now = self.clock()
        yawn_progs: list[float] = []
        for start_t in self._yawn_starts:
            if start_t is not None:
                yawn_progs.append(min(1.0, (now - start_t) / 0.80))
            else:
                yawn_progs.append(0.0)

        self.renderer.draw_scene(
            self.canvas.surface,
            self.scene,
            hovered_cloud_idx=self._hovered_cloud,
            hovered_blanket_idx=self._hovered_blanket,
            hovered_basket=self._hovered_basket,
            hovered_moon=self._hovered_moon,
            selected_blanket_idx=self._selected_blanket_idx,
            holding_star=self._holding_star,
            drag_pos=self._drag_pos,
            yawn_progresses=(yawn_progs[0], yawn_progs[1], yawn_progs[2]),
        )
