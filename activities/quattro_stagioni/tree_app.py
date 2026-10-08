"""Main interactive application loop for Il Grande Albero delle Stagioni."""

from __future__ import annotations

import random
import time
from typing import Protocol
from uuid import uuid4

import pygame

from greia_platform.activity_api import activity_stop_requested, emit_activity_event, mark_activity_ready
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface

if __package__:
    from .tree_audio import SpeechQueue, TreeAudio
    from .tree_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        Particle,
        Season,
        TreeModel,
        WeatherMode,
    )
    from .tree_renderer import TreeRenderer
else:
    from tree_audio import SpeechQueue, TreeAudio
    from tree_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        Particle,
        Season,
        TreeModel,
        WeatherMode,
    )
    from tree_renderer import TreeRenderer


class SeasonEventPort(Protocol):
    def season_explored(self, season: Season) -> None: ...
    def all_seasons_discovered(self) -> None: ...


class GreiaSeasonEvents:
    def __init__(self) -> None:
        self._session = uuid4().hex

    def season_explored(self, season: Season) -> None:
        emit_activity_event(
            "quattro_stagioni.cycle_explored",
            {"season": season.value},
            idempotency_key=f"seasons:{self._session}:{season.value}",
        )

    def all_seasons_discovered(self) -> None:
        emit_activity_event(
            "quattro_stagioni.all_seasons_discovered",
            {"total": len(Season)},
            idempotency_key=f"seasons:{self._session}:all",
        )


class TreeActivity:
    """Greia Activity controller for Il Grande Albero delle Stagioni."""

    def __init__(
        self,
        screen: pygame.Surface,
        renderer: TreeRenderer,
        audio: TreeAudio,
        model: TreeModel,
        events: SeasonEventPort | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = PygameReferenceCanvas(screen)
        self.events = events if events is not None else GreiaSeasonEvents()
        self.renderer = renderer
        self.audio = audio
        self.model = model
        self.speech_queue = SpeechQueue(self.audio)
        self.clock = pygame.time.Clock()
        self.running = True

        # Initial friendly welcome prompt from Tito
        self.speech_queue.enqueue("welcome", delay_after=0.5)

    def run(self) -> int:
        last_time = time.perf_counter()
        ready_published = False

        while self.running and not activity_stop_requested():
            now = time.perf_counter()
            dt = min(0.1, now - last_time)
            last_time = now

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.get_surface() or self.screen
                    self.canvas = PygameReferenceCanvas(self.screen)
                elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button != 1:
                        continue
                    pos = getattr(event, "pos", None)
                    if pos is None:
                        w, h = self.screen.get_size()
                        pos = (int(event.x * w), int(event.y * h))
                    self._handle_pointer_down(pos)

            # Update simulation & speech
            self.model.update(dt)
            self.speech_queue.update(dt)

            # Render scene
            self.renderer.render(self.canvas.surface, self.model)
            self.canvas.present()
            pygame.display.flip()
            if not ready_published:
                mark_activity_ready()
                ready_published = True
            self.clock.tick(60)

        pygame.quit()
        return 0

    def _to_reference_pos(self, physical_pos: tuple[int, int]) -> tuple[int, int] | None:
        vp = activity_viewport_for_surface(self.screen)
        x, y = physical_pos
        if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
            return None
        if any(r.x <= x < r.right and r.y <= y < r.bottom for r in vp.protected_regions):
            return None
        logical = self.canvas.pointer(physical_pos)
        return (int(logical[0]), int(logical[1])) if logical is not None else None

    def _handle_pointer_down(self, physical_pos: tuple[int, int]) -> None:
        point = self._to_reference_pos(physical_pos)
        if point is None:
            return
        ref_x, ref_y = point

        # 1. Check Sun / Moon celestial tap
        if self.renderer.celestial_rect.collidepoint(ref_x, ref_y):
            is_day = self.model.toggle_day_night()
            self.audio.play_sfx("chime")
            if is_day:
                self.speech_queue.enqueue("day", delay_after=0.4)
            else:
                self.speech_queue.enqueue("night", delay_after=0.4)
            return

        # 2. Check Weather selector buttons
        for mode, rect in self.renderer.weather_buttons.items():
            if rect.collidepoint(ref_x, ref_y):
                self.model.set_weather(mode)
                self.audio.play_sfx("pop")
                self.speech_queue.enqueue(mode.value, delay_after=0.4)
                return

        # 3. Check Season selector buttons
        for season, rect in self.renderer.season_buttons.items():
            if rect.collidepoint(ref_x, ref_y):
                was_new = season not in self.model.discovered_seasons
                had_completed = self.model.completed_cycle
                self.model.set_season(season)
                if was_new:
                    self.events.season_explored(season)
                if not had_completed and self.model.completed_cycle:
                    self.events.all_seasons_discovered()
                self.audio.play_sfx("pop")
                self.speech_queue.enqueue(season.value, delay_after=0.4)
                return

        # 4. Check Tito Fox tap
        if self.renderer.tito_rect.collidepoint(ref_x, ref_y):
            self.model.tap_tito()
            self.audio.play_sfx("boing")
            praise_cues = ["praise_1", "praise_2", "praise_3"]
            self.speech_queue.enqueue(random.choice(praise_cues), delay_after=0.3)
            return

        # 5. Summer: check apple taps
        if self.model.season == Season.SUMMER:
            tx = self.renderer.tree_center_x
            ty = self.renderer.tree_center_y
            for idx, apple in enumerate(self.model.apples):
                ax = tx + apple.tree_rel_x
                ay = ty + apple.tree_rel_y + apple.fall_y
                if abs(ref_x - ax) < 24 and abs(ref_y - ay) < 24:
                    if self.model.tap_apple(idx):
                        self.audio.play_sfx("thud")
                        return

        # 6. Winter: check snowman tap
        if self.model.season == Season.WINTER:
            snowman_rect = pygame.Rect(720, 360, 80, 120)
            if snowman_rect.collidepoint(ref_x, ref_y):
                if self.model.tap_snowman():
                    self.audio.play_sfx("chime")
                    return

        # 7. Ambient tap on particles/screen: spawn tap sparkles!
        self.audio.play_sfx("pop")
        for _ in range(5):
            self.model.particles.append(
                Particle(
                    x=ref_x + random.uniform(-15, 15),
                    y=ref_y + random.uniform(-15, 15),
                    vx=random.uniform(-40, 40),
                    vy=random.uniform(-60, -10),
                    kind="sparkle",
                    color=(255, 230, 100),
                    size=random.uniform(3, 7),
                )
            )
