from __future__ import annotations

import collections
import io
import math
from pathlib import Path
import random
import struct
import time
from typing import Any
import wave

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_profile_locale,
    get_storage,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics, is_home_clicked
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import (
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)
from greia_platform.typography import FontRole, GreiaTypography

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
STORAGE_KEY = "acquario_magico.progress.v1"
ASSETS_DIR = Path(__file__).parent / "assets" / "runtime"

SPECIES = [
    {
        "id": "clownfish",
        "name_it": "Pesce Pagliaccio 🐠",
        "name_en": "Clownfish 🐠",
        "color": (249, 115, 22),
        "size": 36,
        "w": 72,
        "h": 54,
        "speed": 1.4,
        "behavior": "dart",
    },
    {
        "id": "turtle",
        "name_it": "Tartaruga 🐢",
        "name_en": "Sea Turtle 🐢",
        "color": (34, 197, 94),
        "size": 44,
        "w": 88,
        "h": 66,
        "speed": 0.9,
        "behavior": "glide",
    },
    {
        "id": "octopus",
        "name_it": "Polipetto 🐙",
        "name_en": "Octopus 🐙",
        "color": (236, 72, 153),
        "size": 40,
        "w": 76,
        "h": 76,
        "speed": 1.1,
        "behavior": "pulse",
    },
    {
        "id": "dolphin",
        "name_it": "Delfino 🐬",
        "name_en": "Dolphin 🐬",
        "color": (59, 130, 246),
        "size": 52,
        "w": 104,
        "h": 70,
        "speed": 1.8,
        "behavior": "leap",
    },
    {
        "id": "puffer",
        "name_it": "Pesce Palla 🐡",
        "name_en": "Pufferfish 🐡",
        "color": (234, 179, 8),
        "size": 38,
        "w": 76,
        "h": 76,
        "speed": 1.0,
        "behavior": "puffer",
    },
    {
        "id": "seahorse",
        "name_it": "Cavalluccio 🌿",
        "name_en": "Seahorse 🌿",
        "color": (244, 114, 182),
        "size": 36,
        "w": 50,
        "h": 70,
        "speed": 0.8,
        "behavior": "vertical",
    },
    {
        "id": "jellyfish",
        "name_it": "Medusa 🪼",
        "name_en": "Jellyfish 🪼",
        "color": (168, 85, 247),
        "size": 38,
        "w": 64,
        "h": 76,
        "speed": 0.7,
        "behavior": "float",
    },
    {
        "id": "starfish",
        "name_it": "Stella Marina ⭐",
        "name_en": "Starfish ⭐",
        "color": (244, 63, 94),
        "size": 34,
        "w": 60,
        "h": 60,
        "speed": 0.4,
        "behavior": "floor",
    },
]


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


class AquariumAudio:
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
        # 1. Bubble pop
        bubble_samples = []
        for i in range(int(rate * 0.08)):
            t = i / rate
            env = math.exp(-20.0 * t)
            val = math.sin(2.0 * math.pi * (500.0 + 400.0 * (t / 0.08)) * t)
            bubble_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["bubble"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(bubble_samples)))

        # 2. Nibble food
        nibble_samples = []
        for i in range(int(rate * 0.10)):
            t = i / rate
            env = math.exp(-15.0 * t)
            val = math.sin(2.0 * math.pi * 750.0 * t) + 0.3 * math.sin(2.0 * math.pi * 1200.0 * t)
            nibble_samples.append(int(32767.0 * 0.22 * env * val))
        self._sounds["nibble"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(nibble_samples)))

        # 3. Glow chime
        glow_samples = []
        for i in range(int(rate * 0.35)):
            t = i / rate
            env = math.exp(-3.5 * t)
            val = 0.5 * math.sin(2.0 * math.pi * 523.25 * t) + 0.5 * math.sin(2.0 * math.pi * 783.99 * t)
            glow_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["glow"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(glow_samples)))

        # 4. Treasure chest chime
        chest_samples = []
        for i in range(int(rate * 0.40)):
            t = i / rate
            env = math.exp(-3.0 * t)
            freq = 659.25 if t < 0.1 else (783.99 if t < 0.2 else 1046.50)
            val = math.sin(2.0 * math.pi * freq * t)
            chest_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["chest"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(chest_samples)))

        # 5. Splash sound
        splash_samples = []
        for i in range(int(rate * 0.12)):
            t = i / rate
            env = math.exp(-12.0 * t)
            noise = (random.random() * 2.0 - 1.0) * 0.4
            val = math.sin(2.0 * math.pi * 320.0 * t) * 0.6 + noise
            splash_samples.append(int(32767.0 * 0.22 * env * val))
        self._sounds["splash"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(splash_samples)))

    def play(self, name: str) -> None:
        snd = self._sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass


# Surface and Scale Cache
_IMAGE_CACHE: dict[str, pygame.Surface | None] = {}
_SCALE_CACHE: dict[tuple[str, int, int, bool], pygame.Surface | None] = {}
_BG_CACHE: dict[tuple[str, int, int], pygame.Surface] = {}


def _load_asset_surface(filename: str) -> pygame.Surface | None:
    if filename not in _IMAGE_CACHE:
        p = ASSETS_DIR / filename
        if p.exists():
            try:
                if pygame.display.get_surface() is not None:
                    _IMAGE_CACHE[filename] = pygame.image.load(str(p)).convert_alpha()
                else:
                    _IMAGE_CACHE[filename] = pygame.image.load(str(p))
            except Exception:
                try:
                    _IMAGE_CACHE[filename] = pygame.image.load(str(p))
                except Exception:
                    _IMAGE_CACHE[filename] = None
        else:
            _IMAGE_CACHE[filename] = None
    return _IMAGE_CACHE[filename]


def _get_scaled_asset(filename: str, width: int, height: int, facing_right: bool = True) -> pygame.Surface | None:
    key = (filename, width, height, facing_right)
    if key not in _SCALE_CACHE:
        orig = _load_asset_surface(filename)
        if orig is not None:
            scaled = pygame.transform.smoothscale(orig, (width, height))
            if not facing_right:
                scaled = pygame.transform.flip(scaled, True, False)
            _SCALE_CACHE[key] = scaled
        else:
            _SCALE_CACHE[key] = None
    return _SCALE_CACHE[key]


def _get_cached_background(glow_mode: bool, width: int = REFERENCE_WIDTH, height: int = REFERENCE_HEIGHT) -> pygame.Surface:
    key = ("night" if glow_mode else "day", width, height)
    if key in _BG_CACHE:
        return _BG_CACHE[key]

    bg = pygame.Surface((width, height))
    sand_h = 90
    sand_y = height - sand_h

    if glow_mode:
        # Deep bioluminescent night abyss gradient
        for gy in range(0, height, 4):
            ratio = gy / float(height)
            r = int(8 + (18 - 8) * ratio)
            g = int(12 + (24 - 12) * ratio)
            b = int(38 + (65 - 38) * ratio)
            pygame.draw.rect(bg, (r, g, b), (0, gy, width, 4))

        # Night kelp forests
        kelp_n = _get_scaled_asset("kelp_night.png", 80, 280)
        if kelp_n is not None:
            for kx in [70, 200, 360, 560, 720, 880, 950]:
                bg.blit(kelp_n, (kx, sand_y - 250))

        # Night Seafloor
        pygame.draw.rect(bg, (30, 20, 50), (0, sand_y, width, sand_h))
        pygame.draw.line(bg, (147, 51, 234), (0, sand_y), (width, sand_y), 3)

        # Night Coral Reefs (Left & Right)
        coral_surf = _get_scaled_asset("coral_reef.png", 220, 165, facing_right=True)
        if coral_surf is not None:
            bg.blit(coral_surf, (20, sand_y - 125))
            coral_flipped = _get_scaled_asset("coral_reef.png", 220, 165, facing_right=False)
            if coral_flipped is not None:
                bg.blit(coral_flipped, (width - 240, sand_y - 125))

        # Glowing Shells on Sand
        for sx in [280, 440, 620, 800]:
            pygame.draw.circle(bg, (250, 204, 21), (sx, sand_y + 25), 10)
            pygame.draw.circle(bg, (255, 255, 255), (sx, sand_y + 25), 5)
    else:
        # Tropical Cyan Ocean Gradient
        for gy in range(0, height, 4):
            ratio = gy / float(height)
            r = int(14 + (2 - 14) * ratio)
            g = int(165 + (130 - 165) * ratio)
            b = int(233 + (195 - 233) * ratio)
            pygame.draw.rect(bg, (r, g, b), (0, gy, width, 4))

        # Daylight kelp forests
        kelp_d = _get_scaled_asset("kelp.png", 80, 280)
        if kelp_d is not None:
            for kx in [70, 200, 360, 560, 720, 880, 950]:
                bg.blit(kelp_d, (kx, sand_y - 250))

        # Sandy Seafloor
        pygame.draw.rect(bg, (254, 243, 199), (0, sand_y, width, sand_h))
        pygame.draw.line(bg, (217, 119, 6), (0, sand_y), (width, sand_y), 3)

        # Coral Reefs
        coral_surf = _get_scaled_asset("coral_reef.png", 220, 165, facing_right=True)
        if coral_surf is not None:
            bg.blit(coral_surf, (20, sand_y - 125))
            coral_flipped = _get_scaled_asset("coral_reef.png", 220, 165, facing_right=False)
            if coral_flipped is not None:
                bg.blit(coral_flipped, (width - 240, sand_y - 125))

        # Shells on Sand
        for sx in [280, 440, 620, 800]:
            pygame.draw.circle(bg, (244, 114, 182), (sx, sand_y + 25), 11)
            pygame.draw.circle(bg, (255, 255, 255), (sx, sand_y + 25), 5)

    _BG_CACHE[key] = bg
    return bg


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)
    clock = pygame.time.Clock()
    theme = get_theme()
    metrics = ChildUiMetrics.for_size(*screen.get_size())
    canvas = PygameReferenceCanvas(screen)
    typography = GreiaTypography()
    sounds = AquariumAudio()

    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    try:
        context = resolve_activity_locale(get_profile_locale(), support)
    except Exception:
        context = resolve_activity_locale("it", support)
    resources = LocalizedResources(Path(__file__).resolve().parent, context)

    # Load persistent state
    storage = get_storage()
    saved_data = storage.kv_get(STORAGE_KEY) if storage else {}
    if not isinstance(saved_data, dict):
        saved_data = {}

    glow_mode = bool(saved_data.get("glow_mode", False))
    active_tool = 0  # 0: Spawner, 1: Food, 2: Bubbles, 3: Day/Night
    spawn_selector_idx = 0  # index into SPECIES for next spawn
    total_fed = int(saved_data.get("total_fed", 0))
    total_popped = int(saved_data.get("total_popped", 0))

    creatures: list[dict[str, Any]] = []
    bubbles: list[dict[str, Any]] = []
    food_pellets: list[dict[str, Any]] = []
    particles: list[dict[str, Any]] = []

    # Treasure Chest State
    chest_rect = pygame.Rect(460, REFERENCE_HEIGHT - 165, 112, 88)
    chest_open_timer = 0.0

    def spawn_creature(x: float, y: float, spec_idx: int | None = None, facing: int = 1) -> dict[str, Any]:
        if len(creatures) >= 20:
            creatures.pop(0)
        idx = spec_idx if spec_idx is not None else random.randint(0, len(SPECIES) - 1)
        sp = SPECIES[idx % len(SPECIES)]
        spd = sp.get("speed", 1.2)
        vx = (1.0 if facing > 0 else -1.0) * spd * random.uniform(0.8, 1.2)
        
        # Floor creatures (starfish) stay on the seafloor
        if sp["behavior"] == "floor":
            y = float(REFERENCE_HEIGHT - 110)
            vy = 0.0
        else:
            vy = random.uniform(-0.3, 0.3)

        c = {
            "spec": sp,
            "x": float(x),
            "y": float(y),
            "vx": vx,
            "vy": vy,
            "target_vx": vx,
            "target_vy": vy,
            "facing": 1 if vx >= 0 else -1,
            "swim_t": random.random() * 6.28,
            "puffed_t": 0.0,
            "spin_t": 0.0,
            "happy_t": 0.0,
        }
        creatures.append(c)
        return c

    # Restore saved creatures or spawn initial diverse population
    saved_creatures = saved_data.get("creatures")
    if isinstance(saved_creatures, list) and len(saved_creatures) > 0:
        for sc in saved_creatures[:16]:
            spec_id = sc.get("id")
            s_idx = next((i for i, s in enumerate(SPECIES) if s["id"] == spec_id), 0)
            spawn_creature(
                sc.get("x", random.uniform(100, 900)),
                sc.get("y", random.uniform(120, 440)),
                s_idx,
                sc.get("facing", 1),
            )
    else:
        # Default balanced tank
        spawn_creature(240, 220, 0, 1)   # Clownfish
        spawn_creature(500, 180, 1, -1)  # Turtle
        spawn_creature(740, 280, 2, -1)  # Octopus
        spawn_creature(360, 140, 3, 1)   # Dolphin
        spawn_creature(620, 360, 4, 1)   # Puffer
        spawn_creature(180, 320, 5, 1)   # Seahorse
        spawn_creature(820, 200, 6, -1)  # Jellyfish
        spawn_creature(320, REFERENCE_HEIGHT - 110, 7, 1) # Starfish

    ready_published = False
    last_save_time = time.monotonic()

    # Pre-render Tool UI labels for speed using GreiaTypography (crisp & localized)
    tool_labels = {
        0: typography.render(resources.text("tool.add_fish"), FontRole.DISPLAY, 16, (255, 255, 255)),
        1: typography.render(resources.text("tool.feed"), FontRole.DISPLAY, 16, (255, 255, 255)),
        2: typography.render(resources.text("tool.bubbles"), FontRole.DISPLAY, 16, (255, 255, 255)),
        "night": typography.render(resources.text("tool.night"), FontRole.DISPLAY, 16, (255, 255, 255)),
        "day": typography.render(resources.text("tool.day"), FontRole.DISPLAY, 16, (255, 255, 255)),
    }

    tool_y = REFERENCE_HEIGHT - 85
    tool_rects = [
        (pygame.Rect(100, tool_y, 180, 72), 0, (34, 197, 94)),
        (pygame.Rect(310, tool_y, 180, 72), 1, (249, 115, 22)),
        (pygame.Rect(520, tool_y, 180, 72), 2, (56, 189, 248)),
        (pygame.Rect(730, tool_y, 180, 72), 3, (168, 85, 247)),
    ]

    running = True
    while running and not activity_stop_requested():
        t_now = time.time()
        dt = 0.033

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    glow_mode = not glow_mode
                    sounds.play("glow")
                elif event.key == pygame.K_1:
                    active_tool = 0
                    sounds.play("bubble")
                elif event.key == pygame.K_2:
                    active_tool = 1
                    sounds.play("bubble")
                elif event.key == pygame.K_3:
                    active_tool = 2
                    sounds.play("bubble")
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                pos = getattr(event, "pos", None)
                if pos is None and hasattr(event, "x") and hasattr(event, "y"):
                    w, h = screen.get_size()
                    pos = (int(event.x * w), int(event.y * h))
                if pos is None:
                    continue

                if is_home_clicked(screen, pos):
                    running = False
                    continue

                pointer = canvas.pointer(pos)
                if pointer is None:
                    continue
                mx, my = int(pointer[0]), int(pointer[1])

                # 1. Check Bottom Toolbar Buttons
                clicked_tool = False
                for r, t_idx, _ in tool_rects:
                    if r.collidepoint(mx, my):
                        clicked_tool = True
                        active_tool = t_idx
                        if t_idx == 3:  # Day/Night toggle
                            glow_mode = not glow_mode
                            sounds.play("glow")
                        elif t_idx == 1:  # Drop food immediately on button click!
                            for _ in range(6):
                                food_pellets.append({
                                    "x": float(random.uniform(160, REFERENCE_WIDTH - 160)),
                                    "y": float(random.uniform(60, 130)),
                                    "vx": random.uniform(-0.4, 0.4),
                                    "vy": random.uniform(0.9, 1.5),
                                    "size": random.uniform(5.5, 8.0),
                                    "color": (245, 158, 11),
                                })
                            sounds.play("nibble")
                            # Spawn sparkle indicator
                            for _ in range(8):
                                particles.append({
                                    "x": float(r.centerx + random.uniform(-20, 20)),
                                    "y": float(r.top - 10),
                                    "vx": random.uniform(-1.5, 1.5),
                                    "vy": random.uniform(-2.0, -4.0),
                                    "color": (253, 224, 71),
                                    "size": random.uniform(4, 7),
                                    "life": 0.8,
                                    "decay": 0.05,
                                })
                        elif t_idx == 0:  # Add creature immediately and cycle to next!
                            spawn_creature(
                                random.uniform(200, REFERENCE_WIDTH - 200),
                                random.uniform(150, tool_y - 120),
                                spawn_selector_idx,
                                1 if random.random() < 0.5 else -1,
                            )
                            spawn_selector_idx = (spawn_selector_idx + 1) % len(SPECIES)
                            sounds.play("splash")
                        elif t_idx == 2:  # Blow big bubble stream!
                            for _ in range(16):
                                bubbles.append({
                                    "x": float(random.uniform(100, REFERENCE_WIDTH - 100)),
                                    "y": float(random.uniform(tool_y - 50, tool_y + 10)),
                                    "vx": random.uniform(-0.8, 0.8),
                                    "vy": random.uniform(-2.5, -5.5),
                                    "size": random.uniform(10, 26),
                                })
                            sounds.play("bubble")
                        break

                if clicked_tool:
                    continue

                # 2. Check Treasure Chest Click
                if chest_rect.collidepoint(mx, my):
                    chest_open_timer = 2.5
                    sounds.play("chest")
                    # Cascade of sparkles & bubbles from chest
                    for _ in range(12):
                        bubbles.append({
                            "x": float(chest_rect.centerx + random.uniform(-25, 25)),
                            "y": float(chest_rect.top - 10),
                            "vx": random.uniform(-1.2, 1.2),
                            "vy": random.uniform(-3.5, -6.0),
                            "size": random.uniform(10, 24),
                        })
                    for _ in range(10):
                        particles.append({
                            "x": float(chest_rect.centerx + random.uniform(-20, 20)),
                            "y": float(chest_rect.top - 15),
                            "vx": random.uniform(-2.5, 2.5),
                            "vy": random.uniform(-2.5, -5.0),
                            "color": random.choice([(250, 204, 21), (253, 224, 71), (56, 189, 248)]),
                            "size": random.uniform(5, 9),
                            "life": 1.0,
                            "decay": 0.03,
                        })
                    continue

                # 3. Check Direct Creature Petting / Touching
                touched_creature = False
                for c in reversed(creatures):
                    sp = c["spec"]
                    cw = sp.get("w", 72)
                    ch = sp.get("h", 54)
                    c_rect = pygame.Rect(int(c["x"] - cw / 2), int(c["y"] - ch / 2), cw, ch)
                    if c_rect.collidepoint(mx, my):
                        touched_creature = True
                        sounds.play("bubble")
                        if sp["id"] == "puffer":
                            c["puffed_t"] = 2.5
                        elif sp["id"] == "octopus":
                            # Ink squirt particles!
                            for _ in range(8):
                                particles.append({
                                    "x": c["x"], "y": c["y"],
                                    "vx": random.uniform(-2, 2), "vy": random.uniform(-2, 2),
                                    "color": (88, 28, 135) if glow_mode else (30, 41, 59),
                                    "size": random.uniform(6, 12), "life": 1.0, "decay": 0.04
                                })
                        elif sp["id"] == "dolphin":
                            c["spin_t"] = 1.5
                            c["vx"] *= 1.8
                        else:
                            c["happy_t"] = 1.5
                            c["vy"] = -2.0

                        # Sparkles on touch
                        for _ in range(6):
                            particles.append({
                                "x": float(mx), "y": float(my),
                                "vx": random.uniform(-2, 2), "vy": random.uniform(-2, 2),
                                "color": (253, 224, 71), "size": random.uniform(4, 7), "life": 1.0, "decay": 0.05
                            })
                        break

                if touched_creature:
                    continue

                # 4. Water Canvas Tool Actions
                if my < tool_y:
                    if active_tool == 0:
                        # Spawn Selected Creature
                        spawn_creature(mx, my, spawn_selector_idx, 1 if mx < REFERENCE_WIDTH / 2 else -1)
                        sounds.play("splash")
                        spawn_selector_idx = (spawn_selector_idx + 1) % len(SPECIES)
                        for _ in range(10):
                            particles.append({
                                "x": float(mx), "y": float(my),
                                "vx": random.uniform(-2.5, 2.5), "vy": random.uniform(-2.5, 2.5),
                                "color": (56, 189, 248), "size": random.uniform(4, 9), "life": 1.0, "decay": 0.04
                            })
                    elif active_tool == 1:
                        # Drop Food Pellets
                        for ox in [-14, 0, 14]:
                            food_pellets.append({
                                "x": float(mx + ox + random.uniform(-4, 4)),
                                "y": float(my + random.uniform(-5, 5)),
                                "vx": random.uniform(-0.3, 0.3),
                                "vy": random.uniform(0.9, 1.5),
                                "size": random.uniform(5.0, 7.5),
                                "color": (245, 158, 11),
                            })
                        sounds.play("nibble")
                    elif active_tool == 2:
                        # Blow Bubble Stream
                        for _ in range(8):
                            bubbles.append({
                                "x": float(mx + random.uniform(-25, 25)),
                                "y": float(my + random.uniform(-15, 15)),
                                "vx": random.uniform(-0.8, 0.8),
                                "vy": random.uniform(-2.5, -5.0),
                                "size": random.uniform(8, 24),
                            })
                        sounds.play("bubble")

        # -------------------------------------------------------------
        # UPDATE LOGIC & AI STEERING
        # -------------------------------------------------------------
        if chest_open_timer > 0:
            chest_open_timer = max(0.0, chest_open_timer - dt)

        # Update Creatures
        for c in creatures:
            sp = c["spec"]
            c["swim_t"] += 0.06
            spd = sp.get("speed", 1.2)

            # Decay timers
            if c["puffed_t"] > 0:
                c["puffed_t"] = max(0.0, c["puffed_t"] - dt)
            if c["spin_t"] > 0:
                c["spin_t"] = max(0.0, c["spin_t"] - dt)
            if c["happy_t"] > 0:
                c["happy_t"] = max(0.0, c["happy_t"] - dt)

            # Behavior physics
            behavior = sp["behavior"]
            if behavior == "floor":
                # Starfish slowly walks along the sand
                c["x"] += c["vx"]
                c["y"] = float(REFERENCE_HEIGHT - 110)
                if c["x"] < 80:
                    c["x"] = 80
                    c["vx"] = abs(c["vx"])
                    c["facing"] = 1
                elif c["x"] > REFERENCE_WIDTH - 80:
                    c["x"] = REFERENCE_WIDTH - 80
                    c["vx"] = -abs(c["vx"])
                    c["facing"] = -1
            else:
                # Swimming creature: Food seeking vs cruising
                seeking_food = False
                if food_pellets and behavior != "jellyfish":
                    # Find closest reachable food pellet
                    closest_f = min(food_pellets, key=lambda f: (f["x"] - c["x"]) ** 2 + (f["y"] - c["y"]) ** 2)
                    dx = closest_f["x"] - c["x"]
                    dy = closest_f["y"] - c["y"]
                    dist = math.hypot(dx, dy)

                    if dist < 280.0:
                        seeking_food = True
                        # Smooth normalized steering vector
                        if dist > 1.0:
                            ndx = dx / dist
                            ndy = dy / dist
                        else:
                            ndx, ndy = 0.0, 0.0

                        # Smooth acceleration toward food
                        c["vx"] += (ndx * spd * 1.5 - c["vx"]) * 0.12
                        c["vy"] += (ndy * spd * 1.5 - c["vy"]) * 0.12

                        # EATING RADIUS (32px) - eat cleanly without oscillating!
                        if dist < 32.0:
                            if closest_f in food_pellets:
                                food_pellets.remove(closest_f)
                            sounds.play("nibble")
                            total_fed += 1
                            c["happy_t"] = 1.2
                            if sp["id"] == "puffer":
                                c["puffed_t"] = 1.5

                            # Spawn tasty nibble crumb particles
                            for _ in range(6):
                                particles.append({
                                    "x": c["x"], "y": c["y"],
                                    "vx": random.uniform(-1.5, 1.5), "vy": random.uniform(-1.5, 1.5),
                                    "color": (253, 224, 71), "size": random.uniform(3, 6), "life": 1.0, "decay": 0.06
                                })

                if not seeking_food:
                    # Natural cruising wander
                    c["vx"] += (c["target_vx"] - c["vx"]) * 0.05
                    c["vy"] += (c["target_vy"] - c["vy"]) * 0.05
                    if random.random() < 0.02:
                        c["target_vy"] = random.uniform(-0.4, 0.4)
                    if random.random() < 0.005:
                        c["target_vx"] = -c["target_vx"]

                # Apply movement
                c["x"] += c["vx"]
                if behavior == "pulse":
                    # Octopus pulsing jump
                    pulse_wave = math.sin(c["swim_t"] * 3.0)
                    c["y"] += c["vy"] + (pulse_wave * 1.2 if pulse_wave > 0 else 0.2)
                elif behavior == "leap":
                    # Dolphin gentle wave motion
                    c["y"] += c["vy"] + math.sin(c["swim_t"] * 2.5) * 1.4
                elif behavior == "float":
                    # Jellyfish bell bobbing
                    c["y"] += c["vy"] + math.sin(c["swim_t"] * 1.8) * 0.8
                else:
                    c["y"] += c["vy"] + math.sin(c["swim_t"] * 2.0) * 0.6

                # Facing direction with solid hysteresis to completely prevent flip-jitter!
                if c["vx"] > 0.35:
                    c["facing"] = 1
                elif c["vx"] < -0.35:
                    c["facing"] = -1

                # Tank Boundaries
                min_y = 90
                max_y = REFERENCE_HEIGHT - 130
                if c["x"] < 60:
                    c["x"] = 60
                    c["vx"] = abs(c["vx"])
                    c["target_vx"] = abs(c["target_vx"])
                    c["facing"] = 1
                elif c["x"] > REFERENCE_WIDTH - 60:
                    c["x"] = REFERENCE_WIDTH - 60
                    c["vx"] = -abs(c["vx"])
                    c["target_vx"] = -abs(c["target_vx"])
                    c["facing"] = -1

                if c["y"] < min_y:
                    c["y"] = min_y
                    c["vy"] = abs(c["vy"])
                elif c["y"] > max_y:
                    c["y"] = max_y
                    c["vy"] = -abs(c["vy"])

        # Update Food Pellets
        surviving_food = []
        for f in food_pellets:
            f["x"] += f["vx"]
            f["y"] += f["vy"]
            if f["y"] < REFERENCE_HEIGHT - 90:
                surviving_food.append(f)
            else:
                # Dissolve on sand with tiny crumb puff
                for _ in range(2):
                    particles.append({
                        "x": f["x"], "y": f["y"],
                        "vx": random.uniform(-0.5, 0.5), "vy": random.uniform(-0.5, -1.0),
                        "color": (217, 119, 6), "size": 3.0, "life": 0.6, "decay": 0.08
                    })
        food_pellets = surviving_food

        # Update Bubbles
        surviving_b = []
        for b in bubbles:
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            if b["y"] > 65:
                surviving_b.append(b)
            else:
                # Bubble popped at surface
                total_popped += 1
        bubbles = surviving_b

        # Update Particles
        surviving_p = []
        for p in particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= p["decay"]
            if p["life"] > 0:
                surviving_p.append(p)
        particles = surviving_p

        # Periodic autosave state every 10 seconds
        if storage is not None and time.monotonic() - last_save_time > 10.0:
            last_save_time = time.monotonic()
            try:
                storage.kv_set(STORAGE_KEY, {
                    "glow_mode": glow_mode,
                    "total_fed": total_fed,
                    "total_popped": total_popped,
                    "creatures": [
                        {"id": c["spec"]["id"], "x": round(c["x"], 1), "y": round(c["y"], 1), "facing": c["facing"]}
                        for c in creatures[:16]
                    ],
                })
            except Exception:
                pass

        # -------------------------------------------------------------
        # RENDER FRAME
        # -------------------------------------------------------------
        surf = canvas.surface

        # 1. Static pre-rendered background
        bg_surf = _get_cached_background(glow_mode)
        surf.blit(bg_surf, (0, 0))

        # 2. Dynamic sunlight rays (Day) or Jellyfish ambient glow (Night)
        if glow_mode:
            # Ambient luminous jelly in background
            for jx, jy in [(220, 180), (780, 210), (480, 130)]:
                jelly_y = int(jy + math.sin(t_now * 1.8 + jx) * 14)
                pygame.draw.circle(surf, (168, 85, 247), (jx, jelly_y), 16)
                pygame.draw.circle(surf, (232, 121, 249), (jx, jelly_y), 10)
        else:
            # Soft, dreamy translucent underwater sunbeams (Day)
            ray_layer = pygame.Surface((REFERENCE_WIDTH, 420), pygame.SRCALPHA)
            for ray_i, rx in enumerate([160, 360, 580, 800]):
                sway = math.sin(t_now * 0.8 + ray_i * 1.5) * 20
                pts = [
                    (rx - 15, 0),
                    (rx + 25, 0),
                    (rx + 55 + sway, 380),
                    (rx - 25 + sway, 380),
                ]
                alpha = int(14 + math.sin(t_now * 1.4 + ray_i) * 5)
                pygame.draw.polygon(ray_layer, (254, 240, 138, alpha), pts)
            surf.blit(ray_layer, (0, 0))

        # 3. Interactive Treasure Chest
        chest_surf = _get_scaled_asset("chest.png", 112, 88)
        if chest_surf is not None:
            if chest_open_timer > 0:
                # Open chest lift animation
                lift_y = int(chest_rect.top - 6)
                surf.blit(chest_surf, (chest_rect.left, lift_y))
                # Golden pearl glow
                pygame.draw.circle(surf, (253, 224, 71), (chest_rect.centerx, lift_y + 35), 14)
                pygame.draw.circle(surf, (255, 255, 255), (chest_rect.centerx, lift_y + 35), 7)
            else:
                surf.blit(chest_surf, (chest_rect.left, chest_rect.top))

        # 4. Food Pellets
        for f in food_pellets:
            fx, fy, fsz = int(f["x"]), int(f["y"]), int(f["size"])
            pygame.draw.circle(surf, (245, 158, 11), (fx, fy), fsz)
            pygame.draw.circle(surf, (254, 240, 138), (fx - 1, fy - 1), max(1, fsz // 2))

        # 5. Marine Creatures
        for c in creatures:
            sp = c["spec"]
            cx = int(c["x"])
            cy = int(c["y"])
            facing_r = (c["facing"] > 0)
            cw = sp.get("w", 72)
            ch = sp.get("h", 54)

            # Check special puff effect for puffer
            if c["puffed_t"] > 0 and sp["id"] == "puffer":
                cw = int(cw * 1.4)
                ch = int(ch * 1.4)

            creature_surf = _get_scaled_asset(f"{sp['id']}.png", cw, ch, facing_right=facing_r)
            if creature_surf is not None:
                # Handle spin/hop transforms if active
                if c["spin_t"] > 0:
                    rot = int(math.sin(c["spin_t"] * 8.0) * 30.0)
                    img = pygame.transform.rotate(creature_surf, rot)
                else:
                    img = creature_surf
                rect = img.get_rect(center=(cx, cy))
                surf.blit(img, rect)
            else:
                # Vector ellipse fallback
                base_sz = sp["size"]
                pygame.draw.ellipse(surf, sp["color"], (cx - base_sz, cy - base_sz // 2, base_sz * 2, base_sz))
                eye_x = cx + (base_sz // 2 if facing_r else -base_sz // 2)
                pygame.draw.circle(surf, (255, 255, 255), (eye_x, cy - base_sz // 6), 6)
                pygame.draw.circle(surf, (15, 23, 42), (eye_x, cy - base_sz // 6), 3)

            # Happy heart / star above creature when fed
            if c["happy_t"] > 0:
                hy = int(cy - ch // 2 - 14 - math.sin(c["happy_t"] * 4.0) * 4)
                pygame.draw.circle(surf, (244, 63, 94), (cx, hy), 7)
                pygame.draw.circle(surf, (255, 255, 255), (cx - 2, hy - 2), 3)

        # 6. Bubbles
        for b in bubbles:
            bx, by, bsz = int(b["x"]), int(b["y"]), int(b["size"])
            pygame.draw.circle(surf, (255, 255, 255), (bx, by), bsz, 2)
            pygame.draw.circle(surf, (255, 255, 255), (bx - bsz // 3, by - bsz // 3), max(1, bsz // 4))

        # 7. Particles
        for p in particles:
            cur_sz = max(1.5, p["size"] * max(0.0, min(1.0, p["life"])))
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), int(cur_sz))

        # 8. Top HUD (Star Pill with Fish Count + Food Fed Count)
        hud_pill = pygame.Rect(80, 16, 170, 56)
        pygame.draw.rect(surf, (255, 255, 255), hud_pill, border_radius=18)
        pygame.draw.rect(surf, (56, 189, 248), hud_pill, width=3, border_radius=18)
        # Fish icon badge
        pygame.draw.circle(surf, (56, 189, 248), (hud_pill.left + 28, hud_pill.centery), 16)
        cl_mini = _get_scaled_asset("clownfish.png", 26, 20)
        if cl_mini:
            surf.blit(cl_mini, cl_mini.get_rect(center=(hud_pill.left + 28, hud_pill.centery)))
        hud_txt = typography.render(f"{len(creatures)} / 20", FontRole.DISPLAY, 22, (2, 132, 199))
        surf.blit(hud_txt, (hud_pill.left + 54, hud_pill.centery - hud_txt.get_height() // 2))

        # 9. Bottom Toolbar (4 Chunky 180x72px Buttons)
        for b_rect, t_idx, col in tool_rects:
            is_active = (active_tool == t_idx)
            btn_col = col if not glow_mode or t_idx != 3 else (147, 51, 234)
            pygame.draw.rect(surf, btn_col, b_rect, border_radius=20)
            pygame.draw.rect(
                surf,
                (254, 240, 138) if is_active else (255, 255, 255),
                b_rect,
                width=4 if is_active else 2,
                border_radius=20,
            )
            cx = b_rect.centerx
            cy = b_rect.top + 24

            if t_idx == 0:
                # Show currently selected spawn species icon
                curr_sp = SPECIES[spawn_selector_idx % len(SPECIES)]
                sp_icon = _get_scaled_asset(f"{curr_sp['id']}.png", 36, 28)
                if sp_icon:
                    surf.blit(sp_icon, sp_icon.get_rect(center=(cx, cy)))
                lbl = tool_labels[0]
            elif t_idx == 1:
                # Food pellet icon
                pygame.draw.circle(surf, (254, 240, 138), (cx - 8, cy), 7)
                pygame.draw.circle(surf, (245, 158, 11), (cx + 8, cy), 7)
                pygame.draw.circle(surf, (251, 146, 60), (cx, cy - 6), 6)
                lbl = tool_labels[1]
            elif t_idx == 2:
                # Bubble icon
                pygame.draw.circle(surf, (255, 255, 255), (cx - 8, cy + 4), 9, 2)
                pygame.draw.circle(surf, (255, 255, 255), (cx + 8, cy - 4), 11, 2)
                lbl = tool_labels[2]
            elif t_idx == 3:
                # Day / Night icon
                if glow_mode:
                    # Glowing Moon icon
                    pygame.draw.circle(surf, (254, 240, 138), (cx, cy), 12)
                    pygame.draw.circle(surf, btn_col, (cx + 5, cy - 3), 10)
                    lbl = tool_labels["night"]
                else:
                    # Golden Sun icon
                    pygame.draw.circle(surf, (254, 240, 138), (cx, cy), 11)
                    for ang in range(0, 360, 45):
                        rad = math.radians(ang)
                        pygame.draw.line(
                            surf,
                            (254, 240, 138),
                            (cx + int(math.cos(rad) * 13), cy + int(math.sin(rad) * 13)),
                            (cx + int(math.cos(rad) * 18), cy + int(math.sin(rad) * 18)),
                            2,
                        )
                    lbl = tool_labels["day"]

            surf.blit(lbl, (cx - lbl.get_width() // 2, b_rect.bottom - 24))

        canvas.present(clear=theme.background)
        pygame.display.flip()

        if not ready_published:
            mark_activity_ready()
            ready_published = True

        clock.tick(30)

    # Save on exit
    if storage is not None:
        try:
            storage.kv_set(STORAGE_KEY, {
                "glow_mode": glow_mode,
                "total_fed": total_fed,
                "total_popped": total_popped,
                "creatures": [
                    {"id": c["spec"]["id"], "x": round(c["x"], 1), "y": round(c["y"], 1), "facing": c["facing"]}
                    for c in creatures[:16]
                ],
            })
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
