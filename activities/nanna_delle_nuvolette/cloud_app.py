"""Main application and interaction loop for Nanna delle Nuvolette."""

from __future__ import annotations

import time
from typing import Final

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .cloud_audio import CloudAudio
    from .cloud_content import BLANKETS
    from .cloud_model import NightScene, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .cloud_renderer import CloudRenderer
    from .cloud_services import GreiaCloudEvents, GreiaCloudStorage
else:
    from cloud_audio import CloudAudio
    from cloud_content import BLANKETS
    from cloud_model import NightScene, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from cloud_renderer import CloudRenderer
    from cloud_services import GreiaCloudEvents, GreiaCloudStorage


PROTECTED_LEFT: Final[int] = 80
PROTECTED_TOP: Final[int] = 80


def _is_home_clicked(screen: pygame.Surface, pos: tuple[int, int]) -> bool:
    return pos[0] <= PROTECTED_LEFT and pos[1] <= PROTECTED_TOP


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

        if event.type == pygame.MOUSEMOTION:
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

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if _is_home_clicked(self.screen, event.pos):
                self._running = False
                return
            logical = self.canvas.pointer(event.pos)
            if logical is not None:
                point = (int(logical[0]), int(logical[1]))
                if self._handle_pointer_click(point):
                    self._dirty = True
            return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            logical = self.canvas.pointer(event.pos)
            if logical is not None:
                point = (int(logical[0]), int(logical[1]))
                if self._handle_pointer_drop(point):
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
        self._selected_blanket_idx = None
        self._holding_star = False
        self._drag_pos = None
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
        self.night_id = f"night-{int(time.time()):06d}"
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
