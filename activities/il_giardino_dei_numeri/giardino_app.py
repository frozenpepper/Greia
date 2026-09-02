"""Main application loop and input handling for Il Giardino dei Numeri."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .giardino_audio import GiardinoAudio
    from .giardino_model import GardenModel
    from .giardino_renderer import GiardinoRenderer
    from .giardino_services import GiardinoServices, GiardinoStorageState
else:
    from giardino_audio import GiardinoAudio
    from giardino_model import GardenModel
    from giardino_renderer import GiardinoRenderer
    from giardino_services import GiardinoServices, GiardinoStorageState


@dataclass
class GiardinoApp:
    """Toddler counting experience in a cheerful garden."""

    screen: pygame.Surface
    canvas: PygameReferenceCanvas
    renderer: GiardinoRenderer
    audio: GiardinoAudio
    services: GiardinoServices
    resources: LocalizedResources
    typography: GreiaTypography
    model: GardenModel = field(default_factory=GardenModel)
    ready_published: bool = False
    anim_time: float = 0.0

    def __post_init__(self) -> None:
        saved = self.services.load_state()
        self.model.baskets_filled = saved.baskets_filled
        self.model.total_counted = saved.total_counted

    def run(self) -> int:
        clock = pygame.time.Clock()
        running = True
        last_frame = time.monotonic()

        while running and not activity_stop_requested():
            now = time.monotonic()
            dt = min(0.05, now - last_frame)
            last_frame = now
            self.anim_time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self._handle_advance()
                    elif pygame.K_1 <= event.key <= pygame.K_5:
                        self._handle_number_key(event.key - pygame.K_0)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    ref_pos = self.canvas.pointer(event.pos)
                    if ref_pos is not None:
                        self._handle_click(ref_pos)

            events = self.model.update(dt)
            for ev in events:
                self.services.emit_event(ev)
                if ev == "garden.set_counted":
                    self.audio.play_celebration()
                elif ev == "garden.basket_filled":
                    self.audio.play_basket_full()
                    self.services.save_state(
                        GiardinoStorageState(
                            total_counted=self.model.total_counted,
                            baskets_filled=self.model.baskets_filled,
                            highest_count=self.model.target_count,
                        )
                    )

            self.renderer.render(self.model, self.anim_time)
            self.canvas.present()
            pygame.display.flip()

            if not self.ready_published:
                mark_activity_ready()
                self.ready_published = True
                self.audio.play_intro()

            clock.tick(30)

        self.services.save_state(
            GiardinoStorageState(
                total_counted=self.model.total_counted,
                baskets_filled=self.model.baskets_filled,
                highest_count=self.model.target_count,
            )
        )
        self.typography.clear()
        return 0

    def _handle_click(self, ref_pos: tuple[float, float]) -> None:
        rx, ry = ref_pos
        # Greia consumes protected Home/Back input before Activity delivery.
        outcome, order = self.model.handle_tap(rx, ry)
        if outcome == "counted":
            self.audio.play_count(order)
        elif outcome == "giggle":
            self.audio.play("giggle")
        elif outcome == "miss":
            self.audio.play("ripple")
        elif outcome == "advance":
            self.audio.play("rustle")

    def _handle_advance(self) -> None:
        if self.model.celebrating:
            self.model.next_round()
            self.audio.play("rustle")

    def _handle_number_key(self, num: int) -> None:
        # One key press advances one countable object; the number keys are a
        # secondary keyboard-access path, not a replacement for pointer counting.
        del num
        uncounted = [it for it in self.model.items if not it.counted]
        if uncounted:
            outcome, order = self.model.handle_tap(uncounted[0].x, uncounted[0].y)
            if outcome == "counted":
                self.audio.play_count(order)
