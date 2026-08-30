"""Treno Numeri — lifecycle coordinator (screen/canvas/metrics/typography, model, renderer, audio).

Owns the event loop, station state-machine, transient animation lists and
the READY lifecycle (after first flip in same loop). Domain puzzle truth
lives in :mod:`treno_model`; presentation caching lives in
:mod:`treno_renderer`; synthesized audio lives in :mod:`treno_audio`.
"""

from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_profile_locale,
    get_storage,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.pygame_completion import CompletionContent, PygameCompletionScreen
from greia_platform.typography import GreiaTypography

if __package__:
    from .treno_audio import TrainAudio
    from .treno_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY
    from .treno_model import TrainModel
    from .treno_renderer import TrenoRenderer
else:
    from treno_audio import TrainAudio
    from treno_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY
    from treno_model import TrainModel
    from treno_renderer import TrenoRenderer


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


class TrenoApp:
    """Coordinate Treno Numeri lifecycle without owning puzzle rules or raw drawing."""

    def __init__(self, screen: pygame.Surface | None = None) -> None:
        pygame.init()
        # Theme (not used for clear color directly but retained for parity).
        self.theme = get_theme()

        if screen is None:
            screen = pygame.display.get_surface()
            if screen is None:
                screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
        self.screen: pygame.Surface = screen
        pygame.mouse.set_visible(False)
        self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
        self.canvas = PygameReferenceCanvas(self.screen)
        self.typography = GreiaTypography()
        self.sounds = TrainAudio()

        package_root = Path(__file__).parent
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale(get_profile_locale(), support)
        self.resources = LocalizedResources(package_root, context) if context else None

        def t(key: str, default: str) -> str:
            if self.resources is not None:
                try:
                    value = self.resources.string(key)
                    if value:
                        return value
                except Exception:
                    pass
            return default

        self._t = t
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            primary_rect=pygame.Rect(372, 370, 280, 64),
        )
        self.completion_content = CompletionContent(
            title=t("victory.title", "Evviva! Il treno è arrivato al capolinea! 🚂🌟"),
            body_lines=(t("victory.subtitle", "Ottimo lavoro! Hai completato tutte le stazioni!"),),
            primary_label=t("btn.play_again", "🎉 Gioca Ancora!"),
            achievement_count=5,
        )

        storage = get_storage()
        self.storage = storage
        saved_data = storage.kv_get(STORAGE_KEY) if storage else {}
        if not isinstance(saved_data, dict):
            saved_data = {}
        total_stars = int(saved_data.get("stars", 0)) if isinstance(saved_data.get("stars", 0), int) else 0

        self.model = TrainModel(rng=random.Random(), total_stars=total_stars)
        # TrainModel already prepared station 0 in __post_init__.
        # Presentation-owned animation state (not puzzle truth).
        self.train_state: str = "arriving"
        # Attach state to model for renderer's Dani bob approximation.
        setattr(self.model, "train_state", self.train_state)
        self.train_offset_x: float = -700.0
        self.chug_timer: float = 0.0
        self.smoke_particles: list[dict[str, Any]] = []
        self.flying_items: list[dict[str, Any]] = []
        self.celebration_timer: float = 0.0
        self.celebration_particles: list[dict[str, Any]] = []
        self.completion_presented: bool = False
        self.renderer = TrenoRenderer(self.typography)
        self.running: bool = True
        self.first_frame_ready: bool = False
        # Play initial whistle (model didn't; app owns presentation side-effects).
        self.sounds.play("whistle")

    # -- station helpers --------------------------------------------------

    def _setup_station(self, rnd: int) -> None:
        self.model.setup_station(rnd)
        self.train_state = "arriving"
        setattr(self.model, "train_state", self.train_state)
        self.train_offset_x = -700.0
        self.sounds.play("whistle")

    # -- event handling ---------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif self.model.is_victory:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.model.restart()
                    self.train_state = "arriving"
                    setattr(self.model, "train_state", self.train_state)
                    self.train_offset_x = -700.0
                    self.completion.clear()
                    self.completion_presented = False
                    self.renderer.invalidate()
                    self.sounds.play("whistle")
                # Terminal input must never fall through into active controls.
                return
        elif event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.get_surface() or self.screen
            self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
            self.canvas = PygameReferenceCanvas(self.screen)
            self.completion_presented = False
            self.renderer.invalidate()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_pointer(event.pos)

    def _handle_pointer(self, screen_pos: tuple[int, int]) -> None:
        pointer = self.canvas.pointer(screen_pos)
        if pointer is None:
            return
        mx, my = int(pointer[0]), int(pointer[1])
        if not _is_safe_point(self.screen, screen_pos):
            return
        if self.model.is_victory:
            if self.completion.primary_contains((mx, my)):
                self.model.restart()
                self.train_state = "arriving"
                setattr(self.model, "train_state", self.train_state)
                self.train_offset_x = -700.0
                self.completion.clear()
                self.completion_presented = False
                self.renderer.invalidate()
                self.sounds.play("whistle")
            # Terminal input must never fall through into active controls.
            return
        # Crate tap handlers during loading state
        if self.train_state == "loading":
            b_a = pygame.Rect(80, 430, 200, 130)
            b_b = pygame.Rect(320, 430, 200, 130)
            clicked_amt = 0
            start_pos = (mx, my)
            if self.model.mode == "addition":
                if b_a.collidepoint(mx, my):
                    clicked_amt = self.model.val_a
                    start_pos = (b_a.centerx, b_a.centery)
                elif b_b.collidepoint(mx, my):
                    clicked_amt = self.model.val_b
                    start_pos = (b_b.centerx, b_b.centery)
            else:
                b_c = pygame.Rect(120, 430, 280, 130)
                if b_c.collidepoint(mx, my):
                    clicked_amt = 1
                    start_pos = (b_c.centerx, b_c.centery)
            if clicked_amt > 0:
                needed = self.model.target_count - self.model.loaded_count
                to_load = min(clicked_amt, needed) if needed > 0 else 0
                if to_load > 0:
                    for idx in range(to_load):
                        target_idx = self.model.loaded_count + idx
                        wagon_dest_x = 100 + self.train_offset_x + 42 + (target_idx % 5) * 44
                        wagon_dest_y = 285 + (target_idx // 5) * 36
                        self.flying_items.append(
                            {
                                "fruit": self.model.current_fruit["id"],
                                "start_x": start_pos[0],
                                "start_y": start_pos[1],
                                "target_x": wagon_dest_x,
                                "target_y": wagon_dest_y,
                                "t": 0.0,
                                "speed": 0.08 + idx * 0.02,
                            }
                        )
                    self.model.add_load(to_load)
                    note_idx = min(9, self.model.loaded_count)
                    self.sounds.play(f"load_{note_idx}")
                    if self.model.is_station_complete:
                        self.train_state = "celebrating"
                        setattr(self.model, "train_state", self.train_state)
                        self.celebration_timer = 2.4
                        self.sounds.play("win")
                        if self.storage:
                            self.storage.kv_set(STORAGE_KEY, {"stars": self.model.total_stars + 1})
                        # Update model stars now (kept in sync with storage).
                        # The model will increment on complete_station alternative path;
                        # here we increment directly because original added after celebration start.
                        # For bookkeeping, also advance internal counter for event payload.
                        # We mimic original: total_stars was separate var incremented here before event.
                        # Model's total_stars currently holds previous journey total; bump it.
                        self.model.total_stars += 1
                        round_idx = self.model.round_idx
                        try:
                            emit_activity_event(
                                "train.station_completed",
                                {"mode": self.model.mode, "target": self.model.target_count, "stars": self.model.total_stars},
                                idempotency_key=f"station-{round_idx}",
                            )
                        except Exception:
                            pass

    # -- per-frame simulation ---------------------------------------------

    def _step_frame(self, dt: float) -> None:
        # Simulation gate: terminal victory path is handled by caller before this.
        if self.train_state == "arriving":
            self.train_offset_x += 16.0
            self.chug_timer += dt
            if self.chug_timer > 0.22:
                self.chug_timer = 0.0
                self.sounds.play("chug")
                self.smoke_particles.append(
                    {
                        "x": 360 + self.train_offset_x + 280,
                        "y": 140,
                        "vx": random.uniform(-1.5, -0.5),
                        "vy": random.uniform(-2.5, -1.0),
                        "radius": random.uniform(14, 22),
                        "alpha": 220,
                    }
                )
            if self.train_offset_x >= 0.0:
                self.train_offset_x = 0.0
                self.train_state = "loading"
                setattr(self.model, "train_state", self.train_state)
        elif self.train_state == "departing":
            self.train_offset_x += 18.0
            self.chug_timer += dt
            if self.chug_timer > 0.18:
                self.chug_timer = 0.0
                self.sounds.play("chug")
                self.smoke_particles.append(
                    {
                        "x": 360 + self.train_offset_x + 280,
                        "y": 140,
                        "vx": random.uniform(-2.5, -1.0),
                        "vy": random.uniform(-2.5, -1.0),
                        "radius": random.uniform(14, 24),
                        "alpha": 220,
                    }
                )
            if self.train_offset_x > REFERENCE_WIDTH + 400:
                # Advance station; model already incremented stars on completion.
                next_idx = self.model.round_idx + 1
                if next_idx >= self.model.total_stations:
                    self.model.is_victory = True
                    self.train_state = "victory"
                    setattr(self.model, "train_state", self.train_state)
                    emit_activity_event(
                        "train.journey_completed",
                        {"stations": self.model.total_stations, "stars": self.model.total_stars},
                        idempotency_key="journey-completed",
                    )
                else:
                    self.model.round_idx = next_idx
                    self._setup_station(next_idx)
        elif self.train_state == "celebrating":
            self.celebration_timer -= dt
            if random.random() < 0.4:
                self.celebration_particles.append(
                    {
                        "x": random.uniform(100, REFERENCE_WIDTH - 100),
                        "y": random.uniform(60, 320),
                        "vx": random.uniform(-3, 3),
                        "vy": random.uniform(-4, 2),
                        "color": random.choice(
                            [
                                (239, 68, 68),
                                (234, 179, 8),
                                (34, 197, 94),
                                (59, 130, 246),
                                (168, 85, 247),
                                (244, 114, 182),
                            ]
                        ),
                        "size": random.uniform(8, 16),
                    }
                )
            if self.celebration_timer <= 0:
                self.train_state = "departing"
                setattr(self.model, "train_state", self.train_state)
                self.sounds.play("whistle")

        # Update flying items
        surviving_flying: list[dict[str, Any]] = []
        for item in self.flying_items:
            item["t"] += item["speed"]
            if item["t"] < 1.0:
                surviving_flying.append(item)
        self.flying_items = surviving_flying

        # Update smoke
        surviving_smoke: list[dict[str, Any]] = []
        for p in self.smoke_particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["alpha"] = max(0, p["alpha"] - 5)
            p["radius"] += 0.5
            if p["alpha"] > 0:
                surviving_smoke.append(p)
        self.smoke_particles = surviving_smoke

    def _draw(self, t_now: float) -> None:
        surf = self.canvas.surface
        self.renderer.render(
            surf,
            self.model,
            self.train_offset_x,
            self.smoke_particles,
            self.flying_items,
            self.celebration_particles,
            self.model.total_stars,
            t_now,
        )
        self.canvas.present()

    # -- main loop --------------------------------------------------------

    def run(self) -> int:
        clock = pygame.time.Clock()
        while self.running and not activity_stop_requested():
            dt = clock.tick(30) / 1000.0
            t_now = time.time()
            for event in pygame.event.get():
                self.handle_event(event)
            if self.model.is_victory:
                if not self.completion_presented:
                    self.completion.prepare(self.completion_content)
                    self.completion.draw(self.canvas.surface)
                    self.canvas.present(clear=self.theme.background)
                    pygame.display.flip()
                    self.completion_presented = True
                clock.tick(25)
                continue
            if self.train_state == "arriving":
                pass  # gate preserved for terminal-render audit ordering
            self._step_frame(dt)
            self._draw(t_now)
            pygame.display.flip()
            if not self.first_frame_ready:
                mark_activity_ready()
                self.first_frame_ready = True
        return 0


__all__ = ["TrenoApp"]
