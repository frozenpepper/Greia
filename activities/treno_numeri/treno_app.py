"""Treno Numeri — lifecycle coordinator (screen/canvas/metrics/typography, model, renderer, audio).

Owns the event loop, station state-machine, transient animation lists and
the READY lifecycle (after first flip in same loop). Domain puzzle truth
lives in :mod:`treno_model`; presentation caching lives in
:mod:`treno_renderer`; synthesized audio lives in :mod:`treno_audio`.
"""

from __future__ import annotations

import random
import time
from uuid import uuid4
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
        self._journey_id = uuid4().hex
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
            title=t("victory.title", "🚂🌟"),
            body_lines=(t("victory.subtitle", "🌟"),),
            primary_label=t("btn.play_again", "🔄"),
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
        self.selected_crate: int = 0
        # Play initial whistle (model didn't; app owns presentation side-effects).
        self.sounds.play("whistle")

    # -- station helpers --------------------------------------------------

    def _setup_station(self, rnd: int) -> None:
        self.model.setup_station(rnd)
        self.train_state = "arriving"
        setattr(self.model, "train_state", self.train_state)
        self.train_offset_x = -700.0
        self.celebration_particles.clear()
        self.sounds.play("whistle")
        self.selected_crate = 0

    # -- event handling ---------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif self.model.is_victory:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self._restart_journey()
                # Terminal input must never fall through into active controls.
                return
            elif self.train_state == "loading":
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT,
                                 pygame.K_UP, pygame.K_DOWN):
                    self.selected_crate = (self.selected_crate + 1) % (
                        2 if self.model.mode == "addition" else 1
                    )
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self._load_crate(self.selected_crate)
        elif event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.get_surface() or self.screen
            self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
            self.canvas = PygameReferenceCanvas(self.screen)
            self.completion_presented = False
            self.renderer.invalidate()
        elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
              and not getattr(event, "touch", False)):
            self._handle_pointer(event.pos)
        elif event.type == pygame.FINGERDOWN:
            width, height = self.screen.get_size()
            self._handle_pointer((int(event.x * width), int(event.y * height)))

    def _restart_journey(self) -> None:
        """One restart transaction regardless of keyboard/pointer input."""
        self.model.restart()
        self._journey_id = uuid4().hex
        self.train_state = "arriving"
        setattr(self.model, "train_state", self.train_state)
        self.train_offset_x = -700.0
        self.selected_crate = 0
        self.flying_items.clear()
        self.smoke_particles.clear()
        self.celebration_particles.clear()
        self.completion.clear()
        self.completion_presented = False
        self.renderer.invalidate()
        self.sounds.play("whistle")

    def _handle_pointer(self, screen_pos: tuple[int, int]) -> None:
        pointer = self.canvas.pointer(screen_pos)
        if pointer is None:
            return
        mx, my = int(pointer[0]), int(pointer[1])
        if not _is_safe_point(self.screen, screen_pos):
            return
        if self.model.is_victory:
            if self.completion.primary_contains((mx, my)):
                self._restart_journey()
            # Terminal input must never fall through into active controls.
            return
        if self.train_state != "loading":
            return
        first = pygame.Rect(80, 430, 200, 130)
        second = pygame.Rect(320, 430, 200, 130)
        single = pygame.Rect(120, 430, 280, 130)
        if self.model.mode == "addition":
            if first.collidepoint(mx, my):
                self.selected_crate = 0
                self._load_crate(0)
            elif second.collidepoint(mx, my):
                self.selected_crate = 1
                self._load_crate(1)
        elif single.collidepoint(mx, my):
            self.selected_crate = 0
            self._load_crate(0)

    def _load_crate(self, crate_index: int) -> None:
        """Apply one crate choice through the original model/event path."""
        if self.train_state != "loading" or self.model.is_victory:
            return
        if self.model.mode == "addition":
            if crate_index not in (0, 1):
                return
            amount = self.model.val_a if crate_index == 0 else self.model.val_b
            rect = (pygame.Rect(80, 430, 200, 130)
                    if crate_index == 0 else pygame.Rect(320, 430, 200, 130))
        else:
            if crate_index != 0:
                return
            amount = 1
            rect = pygame.Rect(120, 430, 280, 130)
        needed = self.model.needed
        to_load = min(amount, needed)
        if to_load <= 0:
            return
        for idx in range(to_load):
            target_idx = self.model.loaded_count + idx
            wagon_dest_x = 100 + self.train_offset_x + 42 + (target_idx % 5) * 44
            wagon_dest_y = 285 + (target_idx // 5) * 36
            self.flying_items.append(
                {
                    "fruit": self.model.current_fruit["id"],
                    "start_x": rect.centerx,
                    "start_y": rect.centery,
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
            self.model.total_stars += 1
            if self.storage:
                self.storage.kv_set(STORAGE_KEY, {"stars": self.model.total_stars})
            try:
                emit_activity_event(
                    "train.station_completed",
                    {"mode": self.model.mode, "target": self.model.target_count,
                     "stars": self.model.total_stars},
                    idempotency_key=f"train:{self._journey_id}:station:{self.model.round_idx}",
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
                        idempotency_key=f"train:{self._journey_id}:completed",
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
            # Terminal/replay sessions must not accumulate unlimited
            # celebration entities on the small Acer memory floor.
            if len(self.celebration_particles) > 96:
                del self.celebration_particles[:-96]
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
        if self.train_state == "loading":
            if self.model.mode == "addition":
                rect = (pygame.Rect(80, 430, 200, 130)
                        if self.selected_crate == 0 else pygame.Rect(320, 430, 200, 130))
            else:
                rect = pygame.Rect(120, 430, 280, 130)
            pygame.draw.rect(surf, (15, 23, 42), rect.inflate(8, 8), 6, border_radius=16)
            pygame.draw.rect(surf, (56, 189, 248), rect.inflate(8, 8), 3, border_radius=16)
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
