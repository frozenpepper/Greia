"""Lifecycle coordinator for Cucciolo Mio.

Owns the event loop, input routing, ball physics and cross-service sequencing.
Domain rules stay in cucciolo_model, presentation in cucciolo_renderer.
"""

from __future__ import annotations

import io
import math
import random
import struct
import time
import wave
from pathlib import Path

import pygame

from greia_platform.activity_api import activity_stop_requested, emit_activity_event, mark_activity_ready
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.child_text import display_text
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.typography import GreiaTypography

if __package__:
    from .cucciolo_content import (
        GOLD,
        MAX_BUBBLES,
        MAX_PARTICLES,
        PINK,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
    )
    from .cucciolo_model import Particle, PetEntity
    from .cucciolo_renderer import CuccioloRenderer
else:
    from cucciolo_content import GOLD, MAX_BUBBLES, MAX_PARTICLES, PINK, REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY  # type: ignore[import-not-found,no-redef]
    from cucciolo_model import Particle, PetEntity  # type: ignore[import-not-found,no-redef]
    from cucciolo_renderer import CuccioloRenderer  # type: ignore[import-not-found,no-redef]


def _synth_wav(samples: list[int], rate: int = 22050) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        raw = b"".join(struct.pack("<h", max(-32767, min(32767, s))) for s in samples)
        w.writeframes(raw)
    return buf.getvalue()


class SoundManager:
    """Bounded audio owner; synthesizes the 4 effect sounds once."""

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self._init_sounds()
            self._enabled = True
        except Exception:
            self._enabled = False

    def _init_sounds(self) -> None:
        pop_samples = [
            int(math.sin(2 * math.pi * (500 + (1000 - i) * 0.9) * (i / 22050.0)) * max(0.0, 1.0 - (i / 22050.0) / 0.05) * 14000)
            for i in range(1200)
        ]
        self._sounds["pop"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(pop_samples)))

        squeak_samples = []
        for i in range(3500):
            t = i / 22050.0
            f = 1200.0 + math.sin(t * 90.0) * 400.0
            env = max(0.0, 1.0 - t / 0.16)
            squeak_samples.append(int(math.sin(2 * math.pi * f * t) * env * 12000))
        self._sounds["squeak"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(squeak_samples)))

        crunch_samples = []
        for i in range(4000):
            t = i / 22050.0
            f = 250.0 + (random.random() * 300.0)
            env = max(0.0, 1.0 - t / 0.18)
            crunch_samples.append(int(math.sin(2 * math.pi * f * t) * env * 13000))
        self._sounds["crunch"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(crunch_samples)))

        sp_samples = []
        for i in range(7000):
            t = i / 22050.0
            f = 880.0 + math.sin(t * 60.0) * 350.0
            env = max(0.0, 1.0 - t / 0.32)
            sp_samples.append(int(math.sin(2 * math.pi * f * t) * env * 11000))
        self._sounds["sparkle"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(sp_samples)))

    def play(self, name: str) -> None:
        if self._enabled and name in self._sounds:
            try:
                self._sounds[name].play()
            except Exception:
                pass


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


class CuccioloApp:
    """Coordinate Cucciolo lifecycle without owning domain or rendering details."""

    def __init__(
        self,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        metrics: ChildUiMetrics,
        typography: GreiaTypography,
        theme,
        storage,
        resources: LocalizedResources | None,
        active_locale: str,
    ) -> None:
        self._screen = screen
        self._canvas = canvas
        self._metrics = metrics
        self._typography = typography
        self._theme = theme
        self._storage = storage
        self._resources = resources
        self._active_locale = active_locale
        self._sounds = SoundManager()
        self._renderer = CuccioloRenderer(typography)

        self._pet = PetEntity(512.0, 340.0, species="cat")
        self._happiness = 5
        self._hunger = 4
        self._cleanliness = 5

        if storage is not None:
            try:
                saved = storage.kv_get(STORAGE_KEY, {})
                if isinstance(saved, dict):
                    self._pet.species = str(saved.get("species", "cat"))
                    # Clamp to valid species
                    if self._pet.species not in ("cat", "bunny", "puppy"):
                        self._pet.species = "cat"
                    acc = str(saved.get("accessory", "bow"))
                    if acc in ("bow", "crown", "glasses", "party_hat", "none"):
                        self._pet.accessory = acc
                    self._happiness = int(saved.get("happiness", 5))
                    self._hunger = int(saved.get("hunger", 4))
                    self._cleanliness = int(saved.get("cleanliness", 5))
                    # Clamp stats
                    self._happiness = max(0, min(5, self._happiness))
                    self._hunger = max(0, min(5, self._hunger))
                    self._cleanliness = max(0, min(5, self._cleanliness))
            except Exception:
                pass

        self._active_tab = "feed"
        self._particles: list[Particle] = []
        self._bubbles: list[tuple[float, float, float]] = []

        self._ball_pos = [512.0, 440.0]
        self._ball_vel = [0.0, 0.0]
        self._ball_last_pos = [512.0, 440.0]
        self._is_dragging_ball = False

        self._feedback_msg = ""
        self._feedback_timer = 0.0

        self._running = True
        self._ready_published = False

    # ------------------------------------------------------------------ #
    # Event handling

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._running = False
            elif event.key == pygame.K_1:
                self._pet.species = "cat"
            elif event.key == pygame.K_2:
                self._pet.species = "bunny"
            elif event.key == pygame.K_3:
                self._pet.species = "puppy"
        elif event.type == pygame.VIDEORESIZE:
            self._screen = pygame.display.get_surface() or self._screen
            self._metrics = ChildUiMetrics.for_size(*self._screen.get_size())
            self._canvas = PygameReferenceCanvas(self._screen)
            self._renderer.invalidate()
        elif event.type == pygame.WINDOWFOCUSLOST:
            self._is_dragging_ball = False
            self._ball_vel = [0.0, 0.0]
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not _is_safe_point(self._screen, event.pos):
                return
            logical = self._canvas.pointer(event.pos)
            if logical is not None:
                lx, ly = logical
                if self._active_tab == "play" and (lx - self._ball_pos[0]) ** 2 + (ly - self._ball_pos[1]) ** 2 <= 40 ** 2:
                    self._is_dragging_ball = True
                    self._ball_vel = [0.0, 0.0]
        elif event.type == pygame.MOUSEMOTION and self._is_dragging_ball:
            self._move_dragged_ball(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_dragging = self._is_dragging_ball
            if was_dragging:
                self._is_dragging_ball = False
                self._ball_vel[0] = max(-16.0, min(16.0, (self._ball_pos[0] - self._ball_last_pos[0]) * 0.9))
                self._ball_vel[1] = max(-16.0, min(16.0, (self._ball_pos[1] - self._ball_last_pos[1]) * 0.9))
                return
            if not _is_safe_point(self._screen, event.pos):
                return
            logical = self._canvas.pointer(event.pos)
            if logical is not None:
                lx, ly = logical
                self._handle_pointer_click(lx, ly)

    def _move_dragged_ball(self, position: tuple[int, int]) -> None:
        if not _is_safe_point(self._screen, position):
            return
        logical = self._canvas.pointer(position)
        if logical is None:
            return
        self._ball_last_pos[:] = self._ball_pos
        self._ball_pos[0] = max(150.0, min(874.0, logical[0]))
        self._ball_pos[1] = max(160.0, min(450.0, logical[1]))
        self._pet.target_x = max(240.0, min(780.0, self._ball_pos[0]))

    def _handle_pointer_click(self, lx: float, ly: float) -> None:
        # Species buttons
        if 470 <= lx <= 542 and 10 <= ly <= 76:
            self._pet.species = "cat"
            self._sounds.play("sparkle")
        elif 550 <= lx <= 622 and 10 <= ly <= 76:
            self._pet.species = "bunny"
            self._sounds.play("sparkle")
        elif 630 <= lx <= 702 and 10 <= ly <= 76:
            self._pet.species = "puppy"
            self._sounds.play("sparkle")

        # Tabs
        tabs = ["feed", "bath", "play", "sleep", "dress"]
        for idx, tab_id in enumerate(tabs):
            tx = 95 + idx * 170
            if tx <= lx <= tx + 155 and 500 <= ly <= 585:
                self._active_tab = tab_id
                self._sounds.play("pop")
                if self._active_tab == "sleep":
                    self._pet.is_sleeping = True
                    self._sounds.play("sparkle")
                    self._feedback_msg = self._resources.text("msg.sleep") if self._resources else display_text("Sogni d'oro... 🌙")
                    self._feedback_timer = 2.5
                    self._safe_emit("pet.tucked_in", f"sleep-{time.time()}")
                else:
                    self._pet.is_sleeping = False

        # Tab-specific actions (triggered by any click inside content area)
        if self._active_tab == "feed" and 100 <= ly <= 480:
            self._pet.chew_timer = 1.2
            self._hunger = min(5, self._hunger + 1)
            self._happiness = min(5, self._happiness + 1)
            self._sounds.play("crunch")
            for _ in range(16):
                self._add_particle(Particle(self._pet.x, self._pet.y - 40, "💖", PINK))
            self._feedback_msg = self._resources.text("msg.nom_nom") if self._resources else display_text("Gnam gnam! 💖")
            self._feedback_timer = 2.0
            self._safe_emit("pet.fed", f"feed-{time.time()}")

        elif self._active_tab == "bath":
            self._sounds.play("pop")
            self._pet.bubble_count += 3
            for _ in range(8):
                if len(self._bubbles) < MAX_BUBBLES:
                    self._bubbles.append((random.uniform(self._pet.x - 70, self._pet.x + 70), random.uniform(self._pet.y - 90, self._pet.y + 40), random.uniform(16, 30)))
            if self._pet.bubble_count >= 10:
                self._sounds.play("sparkle")
                self._cleanliness = 5
                self._happiness = min(5, self._happiness + 1)
                for _ in range(20):
                    self._add_particle(Particle(self._pet.x, self._pet.y, "✨", GOLD))
                self._feedback_msg = self._resources.text("msg.sparkle") if self._resources else display_text("Tutto pulito! ✨")
                self._feedback_timer = 2.0
                self._pet.bubble_count = 0
                self._bubbles.clear()
                self._safe_emit("pet.groomed", f"bath-{time.time()}")

        elif self._active_tab == "dress":
            # Cycle accessory on any click when dress tab active (preserves original behavior)
            # Original cycled on every click inside dress tab; we keep that.
            acc_list = ["bow", "crown", "glasses", "party_hat", "none"]
            cur_idx = acc_list.index(self._pet.accessory) if self._pet.accessory in acc_list else 0
            # Only cycle if click wasn't on species/tabs already handled? Original code cycles on any click when dress active regardless.
            # To avoid double-trigger on species/tab clicks, we still cycle but preserve original: it cycled unconditionally.
            # We replicate original: dress cycling happens for any click when active_tab==dress, even if tab click itself.
            # The preceding tab handling already set active_tab, so a tab click to dress will also cycle once.
            self._pet.accessory = acc_list[(cur_idx + 1) % len(acc_list)]
            self._sounds.play("sparkle")
            for _ in range(14):
                self._add_particle(Particle(self._pet.x, self._pet.y - 60, "🎀", PINK))
            self._feedback_msg = self._resources.text("msg.dress") if self._resources else display_text("Che bel look! 🎀")
            self._feedback_timer = 2.0

    def _add_particle(self, particle: Particle) -> None:
        self._particles.append(particle)
        if len(self._particles) > MAX_PARTICLES:
            # Keep most recent
            self._particles = self._particles[-MAX_PARTICLES:]

    def _safe_emit(self, ev_id: str, ikey: str, payload: object = None) -> None:
        try:
            emit_activity_event(ev_id, idempotency_key=ikey, payload=payload)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Frame stepping (ball physics, timers, pet)

    def _step_frame(self) -> None:
        # Ball physics when play tab active
        if self._active_tab == "play":
            if not self._is_dragging_ball:
                self._ball_vel[1] += 0.45
                self._ball_vel[0] *= 0.99
                self._ball_pos[0] += self._ball_vel[0]
                self._ball_pos[1] += self._ball_vel[1]

                if self._ball_pos[0] < 160.0:
                    self._ball_pos[0] = 160.0
                    self._ball_vel[0] = abs(self._ball_vel[0]) * 0.78
                    self._sounds.play("squeak")
                elif self._ball_pos[0] > 864.0:
                    self._ball_pos[0] = 864.0
                    self._ball_vel[0] = -abs(self._ball_vel[0]) * 0.78
                    self._sounds.play("squeak")

                if self._ball_pos[1] > 450.0:
                    self._ball_pos[1] = 450.0
                    if abs(self._ball_vel[1]) > 1.5:
                        self._ball_vel[1] = -abs(self._ball_vel[1]) * 0.76
                        self._sounds.play("squeak")
                    else:
                        self._ball_vel[1] = 0.0
                        self._ball_vel[0] *= 0.92

                self._pet.target_x = max(240.0, min(780.0, self._ball_pos[0]))
                dist = math.hypot(self._ball_pos[0] - self._pet.x, self._ball_pos[1] - (self._pet.y - 10))
                if dist < 65.0 and abs(self._ball_vel[1]) > 0.5:
                    self._ball_vel[1] = -8.5
                    self._ball_vel[0] = (self._ball_pos[0] - self._pet.x) * 0.25 + random.uniform(-2.0, 2.0)
                    self._sounds.play("squeak")
                    self._add_particle(Particle(self._ball_pos[0], self._ball_pos[1], "💖", GOLD))
                    self._happiness = min(5, self._happiness + 1)
                    self._safe_emit("pet.played", f"play-{time.time()}")

        if self._pet.is_sleeping and random.random() < 0.06:
            self._add_particle(Particle(self._pet.x + 30, self._pet.y - 70, "💤", (180, 200, 255)))

        self._pet.update()
        self._particles = [p for p in self._particles if p.update()]
        if self._feedback_timer > 0:
            self._feedback_timer -= 0.035
        else:
            self._feedback_msg = ""

    # ------------------------------------------------------------------ #
    # Drawing

    def _draw(self) -> None:
        self._renderer.render(
            self._canvas.surface,
            self._pet,
            self._happiness,
            self._hunger,
            self._cleanliness,
            self._active_tab,
            self._active_locale,
            self._particles,
            self._bubbles,
            self._ball_pos,
            self._feedback_msg,
        )
        self._canvas.present(clear=self._theme.background)
        pygame.display.flip()

    # ------------------------------------------------------------------ #
    # Public lifecycle

    def run(self) -> int:
        clock = pygame.time.Clock()
        while self._running and not activity_stop_requested():
            for event in pygame.event.get():
                self._handle_event(event)

            self._step_frame()
            self._draw()

            if not self._ready_published:
                mark_activity_ready()
                self._ready_published = True

            clock.tick(30)

        # Persist on exit
        if self._storage is not None:
            try:
                self._storage.kv_set(STORAGE_KEY, {
                    "species": self._pet.species,
                    "accessory": self._pet.accessory,
                    "happiness": self._happiness,
                    "hunger": self._hunger,
                    "cleanliness": self._cleanliness,
                    "timestamp": time.time(),
                })
            except Exception:
                pass
        return 0


__all__ = ["CuccioloApp", "SoundManager"]
