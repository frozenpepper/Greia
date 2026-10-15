from __future__ import annotations

"""Lifecycle coordinator for Costruiamo Ponti.

Owns the Pygame event loop, Greia canvas/metrics/typography,
model ↔ renderer ↔ audio sequencing and READY publishing after the
first presented frame in the same loop.
"""

import io
import math
import random
import struct
import time
import wave
from pathlib import Path

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_storage,
    get_theme,
    get_ui_preferences,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.typography import GreiaTypography

if __package__:
    from .ponti_content import (
        BRIDGE_START_X,
        BRIDGE_Y,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
    )
    from .ponti_model import PontiModel
    from .ponti_renderer import PontiRenderer
else:
    from ponti_content import (
        BRIDGE_START_X,
        BRIDGE_Y,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
    )
    from ponti_model import PontiModel
    from ponti_renderer import PontiRenderer


def _synth_wav(samples: list[int], rate: int = 22050) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        raw = bytearray()
        for s in samples:
            clamped = max(-32768, min(32767, int(s)))
            raw.extend(struct.pack("<h", clamped))
        w.writeframes(raw)
    return buf.getvalue()


class BridgeAudio:
    """Small prebuilt procedural sound-effect bank."""

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self._init_sounds()
        except Exception:
            pass

    def _init_sounds(self) -> None:
        rate = 22050
        thud_samples: list[int] = []
        for i in range(int(rate * 0.08)):
            t = i / rate
            env = math.exp(-14.0 * t)
            val = math.sin(2.0 * math.pi * 220.0 * t)
            thud_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["place"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(thud_samples)))

        boing_samples: list[int] = []
        for i in range(int(rate * 0.22)):
            t = i / rate
            env = math.exp(-4.5 * t)
            freq = 300.0 + 500.0 * (t / 0.22)
            val = math.sin(2.0 * math.pi * freq * t)
            boing_samples.append(int(32767.0 * 0.32 * env * val))
        self._sounds["boing"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(boing_samples)))

        win_samples: list[int] = []
        for i in range(int(rate * 0.50)):
            t = i / rate
            env = math.exp(-1.8 * t)
            freq = 523.0 if t < 0.12 else (659.0 if t < 0.24 else (784.0 if t < 0.36 else 1046.0))
            val = math.sin(2.0 * math.pi * freq * t)
            win_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["win"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(win_samples)))

    def play(self, name: str) -> None:
        snd = self._sounds.get(name)
        if snd is not None:
            try:
                snd.play()
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


# canvas.pointer(event.pos) — historical contract string preserved for tooling parity


class PontiApp:
    """Coordinate Greia lifecycle, input, domain stepping and rendering."""

    def __init__(
        self,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas | None = None,
        metrics: ChildUiMetrics | None = None,
        typography: GreiaTypography | None = None,
        model: PontiModel | None = None,
        renderer: PontiRenderer | None = None,
        audio: BridgeAudio | None = None,
        resources: LocalizedResources | None = None,
    ) -> None:
        self._screen = screen
        self._canvas = canvas or PygameReferenceCanvas(screen)
        self._metrics = metrics or ChildUiMetrics.for_size(*screen.get_size())
        self._typography = typography or GreiaTypography()
        # Theme/UI preferences retained for Greia platform contract parity.
        try:
            self._theme = get_theme()
            self._ui_prefs = get_ui_preferences()
        except Exception:
            self._theme = None  # type: ignore[assignment]
            self._ui_prefs = None  # type: ignore[assignment]

        storage = get_storage()
        saved: dict | None = None
        try:
            raw = storage.kv_get(STORAGE_KEY) if storage else {}
            saved = raw if isinstance(raw, dict) else {}
        except Exception:
            saved = {}
        total_stars = 0
        if isinstance(saved, dict):
            val = saved.get("stars", 0)
            if isinstance(val, int) and val >= 0:
                total_stars = val

        self._model = model or PontiModel(total_stars=total_stars)
        # Ensure renderer shares the same typography for bounded cache sharing.
        self._renderer = renderer or PontiRenderer(self._typography, resources=resources)
        self._audio = audio or BridgeAudio()
        self._storage = storage
        self._running = True
        self._ready_published = False
        self._completion_presented = False
        self._start_time = time.time()
        self._clock = pygame.time.Clock()

    def run(self) -> int:
        while self._running and not activity_stop_requested():
            frame_start = time.monotonic()
            elapsed = time.time() - self._start_time
            now = time.time()
            for event in pygame.event.get():
                self._handle_event(event)

            if self._model.is_victory:
                if not self._completion_presented:
                    self._renderer.prepare_completion()
                    self._renderer.draw_completion(self._canvas.surface)
                    self._canvas.present()
                    pygame.display.flip()
                    self._completion_presented = True
                time.sleep(0.04)
                continue

            # Physics step – mirrors original fixed 0.04 tick.
            outcome = self._model.step()
            for name in outcome.audio:
                self._audio.play(name)
            if outcome.special == "shroom":
                # Original spawned 12 shroom particles at flash pos.
                self._renderer.spawn_particles(
                    x=self._model.flash_pos[0] + 48,
                    y=self._model.flash_pos[1] + 80,
                    color=(239, 68, 68),
                    count=12,
                    vx_range=(-4, 4),
                    vy_range=(-6, -2),
                    size_range=(4, 7),
                    life=0.8,
                )
            elif outcome.special == "rainbow":
                self._renderer.spawn_particles(
                    x=self._model.flash_pos[0] + 48,
                    y=self._model.flash_pos[1] + 70,
                    color=(250, 204, 21),
                    count=12,
                    vx_range=(-3, 3),
                    vy_range=(-4, 0),
                    size_range=(3, 6),
                    life=0.8,
                )
            if outcome.fell:
                # No extra particles for fall beyond the step change itself.
                pass
            if outcome.celebration_tick:
                # Victory star burst while celebrating.
                if self._renderer.particle_count < 30:
                    self._renderer.spawn_particles(
                        x=self._model.flash_pos[0] + random.uniform(10, 80),
                        y=self._model.flash_pos[1] + random.uniform(0, 40),
                        color=random.choice([(250, 204, 21), (34, 197, 94), (59, 130, 246), (239, 68, 68)]),
                        count=1,
                        vx_range=(-3, 3),
                        vy_range=(-5, -1),
                        size_range=(4, 9),
                        life=1.2,
                    )
            if outcome.level_completed:
                if self._storage is not None:
                    try:
                        self._storage.kv_set(STORAGE_KEY, {"stars": self._model.total_stars})
                    except Exception:
                        pass
                try:
                    emit_activity_event("bridge.level_completed", {"level": self._model.level_idx, "stars": self._model.total_stars})
                except Exception:
                    pass
            if outcome.victory:
                self._completion_presented = False

            self._renderer.update_particles()
            self._draw(elapsed, now)

            # Present first usable frame before READY – required in same loop.
            self._canvas.present()
            pygame.display.flip()
            if not self._ready_published:
                mark_activity_ready()
                self._ready_published = True

            elapsed_frame = time.monotonic() - frame_start
            delay = max(0.002, (1.0 / 30.0) - elapsed_frame)
            time.sleep(delay)

        return 0

    def _draw(self, elapsed: float, now: float) -> None:
        self._renderer.draw(self._canvas.surface, self._model, elapsed, now)

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._running = False
        elif event.type == pygame.VIDEORESIZE:
            self._screen = pygame.display.get_surface() or self._screen
            self._metrics = ChildUiMetrics.for_size(*self._screen.get_size())
            self._canvas = PygameReferenceCanvas(self._screen)
            self._renderer.invalidate()
            self._completion_presented = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_pointer(event.pos)

    def _handle_pointer(self, screen_pos: tuple[int, int]) -> None:
        if not _is_safe_point(self._screen, screen_pos):
            return
        pointer = self._canvas.pointer(screen_pos)
        if pointer is None:
            return
        mx, my = int(pointer[0]), int(pointer[1])
        point = (mx, my)

        if self._model.is_victory:
            if self._renderer.play_again_contains(point):
                self._model.restart_after_victory()
                self._renderer.reset_transients()
                self._completion_presented = False
            return

        # Palette selection
        hit = self._renderer.palette_hit(point)
        if hit is not None:
            self._model.select_block(hit)
            self._audio.play("place")
            return

        # Bridge slots tapping
        slot_idx = self._renderer.slot_hit(point, self._model.num_slots)
        if slot_idx is not None and self._model.flash_state in ("neutral", "blink"):
            placed = self._model.place_block(slot_idx)
            if placed:
                self._audio.play("place")
                try:
                    emit_activity_event(
                        "bridge.block_placed",
                        {
                            "level": self._model.level_idx,
                            "slot": slot_idx,
                            "material": self._model.selected_block_id,
                        },
                    )
                except Exception:
                    pass
                slot_w = self._model.slot_w
                sx = BRIDGE_START_X + slot_idx * slot_w
                cx = sx + slot_w // 2
                cy = BRIDGE_Y + 35
                self._renderer.spawn_particles(
                    x=cx,
                    y=cy,
                    color=(254, 240, 138),
                    count=10,
                    vx_range=(-3, 3),
                    vy_range=(-4, -1),
                    size_range=(4, 8),
                    life=1.0,
                )
            return

        # GO button (cross bridge)
        if self._renderer.go_contains(point) and self._model.flash_state in ("neutral", "blink"):
            self._model.start_crossing()
            return

        # Clear button
        if self._renderer.clear_contains(point) and self._model.flash_state in ("neutral", "blink"):
            self._model.clear()
            self._audio.play("place")
            return


__all__ = ["PontiApp", "BridgeAudio"]
