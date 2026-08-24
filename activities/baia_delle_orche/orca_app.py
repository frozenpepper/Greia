from __future__ import annotations

import time
from typing import Sequence

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    mark_activity_ready,
)
from greia_platform.activity_ui import is_home_clicked
from greia_platform.pygame_canvas import PygameReferenceCanvas

try:
    from orca_audio import OrcaAudio
    from orca_model import (
        FoodType,
        OrcaEntity,
        OrcaPod,
        OrcaState,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WATER_SURFACE_Y,
    )
    from orca_renderer import OrcaRenderer
    from orca_services import GreiaOrcaEvents, GreiaOrcaProgress
except ImportError:
    from .orca_audio import OrcaAudio
    from .orca_model import (
        FoodType,
        OrcaEntity,
        OrcaPod,
        OrcaState,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WATER_SURFACE_Y,
    )
    from .orca_renderer import OrcaRenderer
    from .orca_services import GreiaOrcaEvents, GreiaOrcaProgress


class OrcaBayActivity:
    """Manages top-level lifecycle, input routing, simulation clock, and service persistence."""

    def __init__(
        self,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        pod: OrcaPod,
        renderer: OrcaRenderer,
        audio: OrcaAudio,
        progress: GreiaOrcaProgress,
        events: GreiaOrcaEvents,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.pod = pod
        self.renderer = renderer
        self.audio = audio
        self.progress = progress
        self.events = events

        self._clock = pygame.time.Clock()
        self._running = True
        self._ready_published = False
        self._last_save_time = time.monotonic()

    def handle_tool_click(self, tool_idx: int) -> None:
        self.pod.active_tool = tool_idx
        if tool_idx == 4:
            # Day / Aurora Night Toggle
            self.pod.night_mode = not self.pod.night_mode
            self.audio.play("aurora")
            self.pod.spawn_splash_particles(REFERENCE_WIDTH // 2, WATER_SURFACE_Y, count=12)
        elif tool_idx == 0:
            # Immediate fish drop from feeder
            food = self.pod.spawn_food(REFERENCE_WIDTH // 2, WATER_SURFACE_Y - 40.0)
            self.audio.play("splash")
        elif tool_idx == 1:
            # Cuddle sound prompt
            self.audio.play("purr")
        elif tool_idx == 2:
            # Trigger synchronized pod jump
            for orca in self.pod.orcas:
                orca.trigger_breach(orca.x + orca.facing * 120.0, height_bonus=25.0)
            self.audio.play("splash")
            self.events.record_acrobatics("all", "pod_breach")
        elif tool_idx == 3:
            # Play first chime note
            self.audio.play("bell_0")

    def handle_pointer_down(self, mx: float, my: float) -> None:
        # 1. Check Bottom Toolbar Clicks
        for rect, tool_idx, _, _, _ in self.renderer.tool_rects:
            if rect.collidepoint(int(mx), int(my)):
                self.handle_tool_click(tool_idx)
                return

        # 2. Check Musical Bell Clicks (if in Song mode)
        if self.pod.active_tool == 3:
            for b_rect, b_idx, _, _ in self.renderer.bell_rects:
                if b_rect.collidepoint(int(mx), int(my)):
                    self.audio.play(f"bell_{b_idx}")
                    self.pod.spawn_music_particles(b_rect.centerx, b_rect.top)
                    self.pod.total_songs += 1
                    self.events.record_song_completed(1)
                    # Nearest orca responds in song!
                    closest_orca = min(self.pod.orcas, key=lambda o: abs(o.x - b_rect.centerx))
                    closest_orca.trigger_sing(b_idx)
                    self.audio.play("clicks")
                    return

        # 3. Check Direct Orca Petting / Touching
        touched_orca: OrcaEntity | None = None
        for orca in reversed(self.pod.orcas):
            if orca.hit_test(mx, my):
                touched_orca = orca
                break

        if touched_orca is not None:
            if self.pod.active_tool == 1 or touched_orca.state == OrcaState.SWIMMING:
                # Cuddle & Tickle belly
                touched_orca.trigger_cuddle()
                self.audio.play("purr")
                self.audio.play("whistle")
                self.pod.spawn_heart_particles(touched_orca.x, touched_orca.y - 15.0, count=6)
                self.pod.total_cuddled += 1
                self.events.record_cuddled(touched_orca.id, "belly_rub")
            elif self.pod.active_tool == 2:
                # Acrobatic leap trigger
                touched_orca.trigger_breach(mx + touched_orca.facing * 100.0)
                self.audio.play("splash")
                self.events.record_acrobatics(touched_orca.id, "solo_breach")
            return

        # 4. Check Beach Ball Touching
        for toy in self.pod.toys:
            if toy.kind == "ball":
                dist = (toy.x - mx) ** 2 + (toy.y - my) ** 2
                if dist < 35.0 ** 2:
                    toy.vx = (toy.x - mx) * 0.35
                    toy.vy = -7.5
                    self.audio.play("bounce")
                    self.pod.spawn_splash_particles(toy.x, toy.y, count=8)
                    return

        # 5. Canvas Water Interaction based on Active Tool
        if my < REFERENCE_HEIGHT - 85:
            if self.pod.active_tool == 0:
                # Drop Food Pellet / Fish
                self.pod.spawn_food(mx, my)
                self.audio.play("splash")
            elif self.pod.active_tool == 1:
                # Water cuddle splash
                self.pod.spawn_heart_particles(mx, my, count=3)
                self.audio.play("bubble")
            elif self.pod.active_tool == 2:
                # Acrobatic breach towards tapped water spot
                closest_orca = min(self.pod.orcas, key=lambda o: abs(o.x - mx))
                closest_orca.trigger_breach(mx)
                self.audio.play("splash")
                self.events.record_acrobatics(closest_orca.id, "target_leap")
            elif self.pod.active_tool == 3:
                # Water chime splash
                self.audio.play("whistle")
                self.pod.spawn_music_particles(mx, my)

    def run(self) -> int:
        """Main activity execution loop."""
        while self._running and not activity_stop_requested():
            dt = 0.033

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._running = False
                    elif event.key == pygame.K_SPACE:
                        self.handle_tool_click(4)  # Toggle Day/Night
                    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                        self.handle_tool_click(event.key - pygame.K_1)
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.get_surface() or self.screen
                    self.canvas = PygameReferenceCanvas(self.screen)
                elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                    pos = getattr(event, "pos", None)
                    if pos is None and hasattr(event, "x") and hasattr(event, "y"):
                        w, h = self.screen.get_size()
                        pos = (int(event.x * w), int(event.y * h))
                    if pos is None:
                        continue

                    # Platform Protected Home/Back navigation
                    if is_home_clicked(self.screen, pos):
                        self._running = False
                        continue

                    pointer = self.canvas.pointer(pos)
                    if pointer is None:
                        continue

                    self.handle_pointer_down(pointer[0], pointer[1])

            # Update Domain Physics and State
            events = self.pod.update(dt)
            for ev in events:
                if ev in ("splash", "whistle", "clicks", "nibble", "purr", "bubble", "bounce"):
                    self.audio.play(ev)

            # Draw complete frame to reference canvas
            self.renderer.render_frame(self.canvas.surface, self.pod)
            self.canvas.present()
            pygame.display.flip()

            # Publish READY exactly once after first presentable frame
            if not self._ready_published:
                mark_activity_ready()
                self._ready_published = True

            # Periodic background state persistence (every 5 seconds)
            now = time.monotonic()
            if now - self._last_save_time >= 5.0:
                self._last_save_time = now
                self.progress.save_progress(self.pod.export_progress())

            self._clock.tick(30)

        # Final state save upon normal exit
        self.progress.save_progress(self.pod.export_progress())
        return 0
