"""Piccola Serra — lifecycle coordinator.

Owns the screen/canvas/metrics/typography, model, renderer and audio.
Handles semantic input routing, per-frame simulation and READY lifecycle
(after first flip in same loop). Domain truth lives in :mod:`serra_model`;
presentation caching lives in :mod:`serra_renderer`.
"""

from __future__ import annotations

import io
import math
import random
import struct
import time
import wave
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
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .serra_content import PLANTS, REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY
    from .serra_model import SerraModel
    from .serra_renderer import POT_RECTS, SerraRenderer
else:
    from serra_content import PLANTS, REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY
    from serra_model import SerraModel
    from serra_renderer import POT_RECTS, SerraRenderer


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


class GreenhouseAudio:
    """Bounded prepared sound bank for Piccola Serra.

    Sounds are synthesized once when the owner is constructed, then
    played by name. Mixer unavailability in headless tests is tolerated.
    """

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
        # Water trickle
        water_samples = []
        for i in range(int(rate * 0.18)):
            t = i / rate
            env = math.exp(-8.0 * t)
            val = math.sin(2.0 * math.pi * (800.0 + random.uniform(-100, 100)) * t)
            water_samples.append(int(32767.0 * 0.22 * env * val))
        self._sounds["water"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(water_samples)))

        # Sprout chime
        sprout_samples = []
        for i in range(int(rate * 0.20)):
            t = i / rate
            env = math.exp(-6.0 * t)
            freq = 440.0 + 440.0 * (t / 0.20)
            val = math.sin(2.0 * math.pi * freq * t)
            sprout_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["sprout"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(sprout_samples)))

        # Bloom chime
        bloom_samples = []
        for i in range(int(rate * 0.35)):
            t = i / rate
            env = math.exp(-3.0 * t)
            val = 0.5 * math.sin(2.0 * math.pi * 587.33 * t) + 0.5 * math.sin(2.0 * math.pi * 880.0 * t)
            bloom_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["bloom"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(bloom_samples)))

        # Harvest pop
        harvest_samples = []
        for i in range(int(rate * 0.15)):
            t = i / rate
            env = math.exp(-10.0 * t)
            val = math.sin(2.0 * math.pi * 650.0 * t)
            harvest_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["harvest"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(harvest_samples)))

        # Win fanfare
        win_samples = []
        for i in range(int(rate * 0.45)):
            t = i / rate
            env = math.exp(-2.0 * t)
            freq = 523.25 if t < 0.12 else (659.25 if t < 0.24 else (783.99 if t < 0.36 else 1046.50))
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


class SerraApp:
    """Coordinate Piccola Serra lifecycle without owning raw drawing."""

    def __init__(self, screen: pygame.Surface | None = None) -> None:
        pygame.init()
        if screen is None:
            screen = pygame.display.get_surface()
            if screen is None:
                screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
        pygame.mouse.set_visible(False)
        self.screen: pygame.Surface = screen
        self.theme = get_theme()
        self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
        self.canvas = PygameReferenceCanvas(self.screen)
        self.typography = GreiaTypography()
        self.sounds = GreenhouseAudio()

        try:
            self.storage = get_storage()
        except Exception:
            self.storage = None

        package_root = Path(__file__).parent
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        profile_lang = get_profile_locale()
        context = resolve_activity_locale(profile_lang, support)
        self.resources = LocalizedResources(package_root, context) if context else None

        def t(key: str, default: str) -> str:
            if self.resources is not None:
                try:
                    res = self.resources.string(key)
                    if res:
                        return res
                except Exception:
                    pass
            return default

        self._t = t
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            primary_rect=pygame.Rect(392, 380, 240, 52),
        )
        self.completion_content = CompletionContent(
            title=t("victory.title", "Che magnifico raccolto! 🌻🍓🥕"),
            body_lines=(t("victory.subtitle", "La tua serra è un vero paradiso!"),),
            primary_label=t("btn.play_again", "🎉 Coltiva Ancora!"),
            achievement_count=3,
        )

        self.model = SerraModel()
        self.renderer = SerraRenderer(self.typography)
        # UI selection state lives in the app, not the pure model.
        self.active_tool: int = 0
        self.selected_plant_type: int = 0
        self.completion_presented: bool = False
        self.running: bool = True
        self._ready_published: bool = False

    # -- lifecycle helpers ------------------------------------------------

    def _reset_greenhouse(self) -> None:
        self.model.reset()
        self.completion.clear()
        self.completion_presented = False
        # active_tool / selected_plant_type keep their last value so the
        # child does not lose tool context on replay; harvest is in model.

    # -- input ------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.get_surface() or self.screen
            self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
            self.canvas = PygameReferenceCanvas(self.screen)
            self.completion_presented = False
            self.renderer.invalidate()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False
                return
            if self.model.is_victory:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self._reset_greenhouse()
                # Terminal input must never fall through into active controls.
                return
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._handle_pointer(event.pos)

    def _handle_pointer(self, screen_pos: tuple[int, int]) -> None:
        if not _is_safe_point(self.screen, screen_pos):
            return
        logical = self.canvas.pointer(screen_pos)
        if logical is None:
            return
        mx, my = int(logical[0]), int(logical[1])

        if self.model.is_victory:
            if self.completion.primary_contains((int(mx), int(my))):
                self._reset_greenhouse()
            # Terminal input must never fall through into active controls.
            return

        # Tool selection buttons (Bottom toolbar)
        tool_y = REFERENCE_HEIGHT - 85
        if pygame.Rect(100, tool_y, 180, 72).collidepoint(mx, my):
            if self.active_tool == 0:
                self.selected_plant_type = (self.selected_plant_type + 1) % len(PLANTS)
            self.active_tool = 0
            return
        if pygame.Rect(310, tool_y, 180, 72).collidepoint(mx, my):
            self.active_tool = 1
            return
        if pygame.Rect(520, tool_y, 180, 72).collidepoint(mx, my):
            self.active_tool = 2
            return
        if pygame.Rect(730, tool_y, 180, 72).collidepoint(mx, my):
            self.active_tool = 3
            return

        self._handle_pot_click(mx, my)

    def _handle_pot_click(self, mx: int, my: int) -> None:
        if self.model.is_victory:
            return
        for idx, r_pot in enumerate(POT_RECTS):
            if r_pot.collidepoint(mx, my):
                result = self.model.apply_tool(idx, self.active_tool, self.selected_plant_type)
                if result is None:
                    break
                stage = result.get("stage", 0)
                # Particle & sound side-effects per transition.
                if stage == 1:
                    # Plant seed
                    self.sounds.play("sprout")
                    for _ in range(8):
                        self.model.particles.append(
                            {
                                "x": r_pot.centerx + random.uniform(-20, 20),
                                "y": r_pot.bottom - 40,
                                "vx": random.uniform(-1, 1),
                                "vy": random.uniform(-2, -0.5),
                                "color": (120, 53, 15),
                                "size": random.uniform(3, 6),
                                "life": 1.0,
                                "decay": 0.04,
                            }
                        )
                    try:
                        emit_activity_event("greenhouse.seed_planted", {"plant": result["plant_id"]})
                    except Exception:
                        pass
                elif stage == 2:
                    self.sounds.play("water")
                    for _ in range(14):
                        self.model.particles.append(
                            {
                                "x": r_pot.centerx + random.uniform(-30, 30),
                                "y": r_pot.top + random.uniform(20, 50),
                                "vx": random.uniform(-0.5, 0.5),
                                "vy": random.uniform(2.0, 4.5),
                                "color": (56, 189, 248),
                                "size": random.uniform(3.0, 5.0),
                                "life": 1.0,
                                "decay": 0.04,
                            }
                        )
                elif stage == 3:
                    self.sounds.play("sprout")
                    for _ in range(12):
                        self.model.particles.append(
                            {
                                "x": r_pot.centerx + random.uniform(-30, 30),
                                "y": r_pot.top + random.uniform(0, 30),
                                "vx": random.uniform(-1.5, 1.5),
                                "vy": random.uniform(-1.5, 1.5),
                                "color": (254, 240, 138),
                                "size": random.uniform(4.0, 8.0),
                                "life": 1.0,
                                "decay": 0.04,
                            }
                        )
                elif stage == 4:
                    self.sounds.play("bloom")
                    for _ in range(18):
                        ang = random.uniform(0, 6.28)
                        spd = random.uniform(2.0, 4.5)
                        self.model.particles.append(
                            {
                                "x": r_pot.centerx,
                                "y": r_pot.top + 20,
                                "vx": math.cos(ang) * spd,
                                "vy": math.sin(ang) * spd,
                                "color": self.model.pots[idx]["plant"]["flower_color"] if self.model.pots[idx]["plant"] else (254, 240, 138),
                                "size": random.uniform(4.0, 7.0),
                                "life": 1.0,
                                "decay": 0.03,
                            }
                        )
                    try:
                        emit_activity_event("greenhouse.flower_bloomed", {"plant": result["plant_id"]})
                    except Exception:
                        pass
                elif stage == 0:
                    # Harvest
                    # Need to distinguish bloom->harvest vs seed? Already 0 from 4.
                    # Check if this was a harvest (victory flag may be set)
                    self.sounds.play("harvest")
                    for _ in range(18):
                        self.model.particles.append(
                            {
                                "x": r_pot.centerx,
                                "y": r_pot.top + 20,
                                "vx": random.uniform(-2.5, 2.5),
                                "vy": random.uniform(-3.5, -1.0),
                                "color": (254, 202, 87),
                                "size": random.uniform(4.0, 8.0),
                                "life": 1.0,
                                "decay": 0.03,
                            }
                        )
                    if result.get("victory"):
                        self.sounds.play("win")
                        try:
                            emit_activity_event(
                                "greenhouse.harvest_completed", {"harvest": self.model.harvest_count}
                            )
                        except Exception:
                            pass
                break

    # -- per-frame simulation ---------------------------------------------

    def _step_frame(self, t_now: float) -> None:
        # Active-world particles stop advancing once terminal state is entered.
        if not self.model.is_victory:
            surviving = []
            for p in self.model.particles:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["life"] -= p["decay"]
                if p["life"] > 0:
                    surviving.append(p)
            self.model.particles = surviving

    def _draw(self, t_now: float) -> None:
        # RENDER TO CANVAS
        surf = self.canvas.surface
        self.renderer.render(surf, self.model, self.active_tool, t_now)
        self.canvas.present(clear=self.theme.background)

    # -- main loop --------------------------------------------------------

    def run(self) -> int:
        clock = pygame.time.Clock()
        while self.running and not activity_stop_requested():
            t_now = time.time()
            self._step_frame(t_now)
            for event in pygame.event.get():
                self.handle_event(event)
                # Victory resize handling already done via handle_event;
                # keep loop responsive.

            if self.model.is_victory:
                if not self.completion_presented:
                    self.completion.prepare(self.completion_content)
                    self.completion.draw(self.canvas.surface)
                    self.canvas.present(clear=self.theme.background)
                    pygame.display.flip()
                    self.completion_presented = True
                clock.tick(25)
                continue

            self._draw(t_now)
            pygame.display.flip()
            if not self._ready_published:
                mark_activity_ready()
                self._ready_published = True
            clock.tick(30)

        if self.storage is not None:
            try:
                self.storage.kv_set(
                    STORAGE_KEY,
                    {
                        "harvest_count": self.model.harvest_count,
                        "timestamp": time.time(),
                    },
                )
            except Exception:
                pass
        return 0


__all__ = ["SerraApp", "GreenhouseAudio"]
