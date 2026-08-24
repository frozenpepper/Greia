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
from greia_platform.pygame_completion import CompletionContent, PygameCompletionScreen
from greia_platform.typography import FontRole, GreiaTypography

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
STORAGE_KEY = "treno_numeri.progress.v2"
ASSETS_DIR = Path(__file__).parent / "assets" / "runtime"

FRUITS = [
    {"id": "apple", "color": (239, 68, 68), "leaf": (34, 197, 94), "stem": (120, 53, 15)},
    {"id": "banana", "color": (234, 179, 8), "leaf": (161, 98, 7), "stem": (113, 63, 18)},
    {"id": "carrot", "color": (249, 115, 22), "leaf": (34, 197, 94), "stem": (22, 101, 52)},
    {"id": "strawberry", "color": (244, 63, 94), "leaf": (34, 197, 94), "stem": (225, 29, 72)},
]
ITEMS = FRUITS


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


class TrainAudio:
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
        # Whistle
        whistle_samples = []
        for i in range(int(rate * 0.45)):
            t = i / rate
            env = min(1.0, t * 12.0) * math.exp(-1.5 * t)
            freq = 600.0 if t < 0.15 else 760.0
            val = math.sin(2.0 * math.pi * freq * t) + 0.5 * math.sin(2.0 * math.pi * (freq * 1.25) * t)
            whistle_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["whistle"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(whistle_samples)))

        # Steam chug
        chug_samples = []
        for i in range(int(rate * 0.08)):
            t = i / rate
            env = math.exp(-15.0 * t)
            val = random.uniform(-1.0, 1.0)
            chug_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["chug"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(chug_samples)))

        # Musical notes 1..10
        scale = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25, 587.33, 659.25, 783.99, 880.00]
        for idx, freq in enumerate(scale):
            samples = []
            for i in range(int(rate * 0.22)):
                t = i / rate
                env = math.exp(-5.5 * t)
                val = math.sin(2.0 * math.pi * freq * t)
                samples.append(int(32767.0 * 0.28 * env * val))
            self._sounds[f"load_{idx}"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(samples)))

        # Win Fanfare
        win_samples = []
        for i in range(int(rate * 0.60)):
            t = i / rate
            env = math.exp(-2.2 * t)
            note_idx = min(3, int(t / 0.15))
            freq = [523.25, 659.25, 783.99, 1046.50][note_idx]
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


# Surface and Scale Cache
_IMAGE_CACHE: dict[str, pygame.Surface] = {}
_SCALE_CACHE: dict[tuple[str, int, int], pygame.Surface] = {}


def _load_asset_surface(filename: str) -> pygame.Surface | None:
    if filename not in _IMAGE_CACHE:
        p = ASSETS_DIR / filename
        if p.exists():
            try:
                _IMAGE_CACHE[filename] = pygame.image.load(str(p)).convert_alpha()
            except Exception:
                _IMAGE_CACHE[filename] = None
        else:
            _IMAGE_CACHE[filename] = None
    return _IMAGE_CACHE[filename]


def _get_scaled_asset(filename: str, width: int, height: int) -> pygame.Surface | None:
    key = (filename, width, height)
    if key not in _SCALE_CACHE:
        orig = _load_asset_surface(filename)
        if orig is not None:
            _SCALE_CACHE[key] = pygame.transform.smoothscale(orig, (width, height))
        else:
            _SCALE_CACHE[key] = None
    return _SCALE_CACHE[key]


def _draw_fruit(surface: pygame.Surface, fruit_id: str, cx: int, cy: int, size: int) -> None:
    asset_name = f"fruit_{fruit_id}.png"
    scaled = _get_scaled_asset(asset_name, size, size)
    if scaled is not None:
        surface.blit(scaled, (cx - size // 2, cy - size // 2))
        return

    r = size // 2
    dark = (30, 41, 59)
    if fruit_id == "apple":
        pygame.draw.circle(surface, (239, 68, 68), (cx - r // 4, cy), r * 4 // 5)
        pygame.draw.circle(surface, (220, 38, 38), (cx + r // 4, cy), r * 4 // 5)
        pygame.draw.circle(surface, dark, (cx - r // 4, cy), r * 4 // 5, 2)
        pygame.draw.circle(surface, dark, (cx + r // 4, cy), r * 4 // 5, 2)
        pygame.draw.rect(surface, (120, 53, 15), (cx - 2, cy - r, 4, r // 2), border_radius=2)
        pygame.draw.ellipse(surface, (34, 197, 94), pygame.Rect(cx + 2, cy - r + 2, r // 2, r // 3))
    elif fruit_id == "banana":
        pygame.draw.arc(surface, (234, 179, 8), pygame.Rect(cx - r, cy - r, r * 2, r * 2), 0.6, 2.6, max(4, r // 2))
        pygame.draw.circle(surface, (161, 98, 7), (cx + r * 2 // 3, cy - r // 3), max(2, r // 6))
    elif fruit_id == "carrot":
        pts = [(cx - r // 2, cy - r // 2), (cx + r // 2, cy - r // 2), (cx, cy + r)]
        pygame.draw.polygon(surface, (249, 115, 22), pts)
        pygame.draw.polygon(surface, dark, pts, 2)
        pygame.draw.polygon(surface, (34, 197, 94), [(cx - 4, cy - r // 2), (cx - 8, cy - r), (cx, cy - r // 2)])
        pygame.draw.polygon(surface, (34, 197, 94), [(cx + 4, cy - r // 2), (cx + 8, cy - r), (cx, cy - r // 2)])
    else:  # strawberry
        pts = [(cx - r * 3 // 4, cy - r // 3), (cx + r * 3 // 4, cy - r // 3), (cx, cy + r)]
        pygame.draw.polygon(surface, (244, 63, 94), pts)
        pygame.draw.polygon(surface, dark, pts, 2)
        pygame.draw.polygon(surface, (34, 197, 94), [(cx - r // 2, cy - r // 2), (cx + r // 2, cy - r // 2), (cx, cy - r * 3 // 4)])


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    theme = get_theme()
    metrics = ChildUiMetrics.for_size(*screen.get_size())
    canvas = PygameReferenceCanvas(screen)
    typography = GreiaTypography()
    sounds = TrainAudio()

    package_root = Path(__file__).parent
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    context = resolve_activity_locale(get_profile_locale(), support)
    resources = LocalizedResources(package_root, context) if context else None

    def t(key: str, default: str) -> str:
        if resources is not None:
            try:
                value = resources.string(key)
                if value:
                    return value
            except Exception:
                pass
        return default

    completion = PygameCompletionScreen(
        typography,
        width=REFERENCE_WIDTH,
        height=REFERENCE_HEIGHT,
        primary_rect=pygame.Rect(372, 370, 280, 64),
    )
    completion_content = CompletionContent(
        title=t("victory.title", "Evviva! Il treno è arrivato al capolinea! 🚂🌟"),
        body_lines=(t("victory.subtitle", "Bravissima! Hai completato tutte le stazioni!"),),
        primary_label=t("btn.play_again", "🎉 Gioca Ancora!"),
        achievement_count=5,
    )

    # Load persistent stars
    storage = get_storage()
    saved_data = storage.kv_get(STORAGE_KEY) if storage else {}
    if not isinstance(saved_data, dict):
        saved_data = {}
    total_stars = saved_data.get("stars", 0)

    # Station levels with math modes
    round_idx = 0
    total_stations = 5
    is_victory = False

    # Problem state
    mode = "addition"  # "addition" or "count"
    val_a = 2
    val_b = 1
    target_count = 3
    loaded_count = 0
    current_fruit = FRUITS[0]

    # Animation
    train_state = "arriving"  # "arriving", "loading", "departing", "celebrating"
    train_offset_x = -700.0
    chug_timer = 0.0
    smoke_particles: list[dict[str, Any]] = []
    flying_items: list[dict[str, Any]] = []
    celebration_timer = 0.0
    celebration_particles: list[dict[str, Any]] = []
    completion_presented = False

    def setup_station(rnd: int) -> None:
        nonlocal mode, val_a, val_b, target_count, loaded_count, current_fruit, train_state, train_offset_x
        current_fruit = FRUITS[rnd % len(FRUITS)]
        loaded_count = 0
        train_state = "arriving"
        train_offset_x = -700.0
        sounds.play("whistle")

        if rnd % 2 == 0:
            mode = "addition"
            pairs = [(1, 1), (1, 2), (2, 1), (2, 2), (2, 3), (3, 2), (1, 3), (3, 1), (4, 1), (2, 4)]
            val_a, val_b = random.choice(pairs)
            target_count = val_a + val_b
        else:
            mode = "count"
            target_count = random.choice([2, 3, 4, 5, 6])
            val_a = target_count
            val_b = 0

    setup_station(0)
    first_frame_ready = False

    running = True
    while running and not activity_stop_requested():
        dt = clock.tick(30) / 1000.0
        t_now = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif is_victory:
                    if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        is_victory = False
                        round_idx = 0
                        completion.clear()
                        completion_presented = False
                        setup_station(0)
                    # Terminal input must never fall through into active controls.
                    continue
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
                completion_presented = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if is_home_clicked(screen, event.pos):
                    running = False
                    continue
                pointer = canvas.pointer(event.pos)
                if pointer is None:
                    continue
                mx, my = int(pointer[0]), int(pointer[1])

                if not _is_safe_point(screen, event.pos):
                    continue

                if is_victory:
                    if completion.primary_contains((mx, my)):
                        is_victory = False
                        round_idx = 0
                        completion.clear()
                        completion_presented = False
                        setup_station(0)
                    # Terminal input must never fall through into active controls.
                    continue

                # Crate tap handlers during loading state
                if train_state == "loading":
                    b_a = pygame.Rect(80, 430, 200, 130)
                    b_b = pygame.Rect(320, 430, 200, 130)

                    clicked_amt = 0
                    start_pos = (mx, my)

                    if mode == "addition":
                        if b_a.collidepoint(mx, my):
                            clicked_amt = val_a
                            start_pos = (b_a.centerx, b_a.centery)
                        elif b_b.collidepoint(mx, my):
                            clicked_amt = val_b
                            start_pos = (b_b.centerx, b_b.centery)
                    else:
                        b_c = pygame.Rect(120, 430, 280, 130)
                        if b_c.collidepoint(mx, my):
                            clicked_amt = 1
                            start_pos = (b_c.centerx, b_c.centery)

                    if clicked_amt > 0:
                        needed = target_count - loaded_count
                        to_load = min(clicked_amt, needed)
                        if to_load > 0:
                            for idx in range(to_load):
                                target_idx = loaded_count + idx
                                wagon_dest_x = 100 + train_offset_x + 42 + (target_idx % 5) * 44
                                wagon_dest_y = 285 + (target_idx // 5) * 36
                                flying_items.append({
                                    "fruit": current_fruit["id"],
                                    "start_x": start_pos[0],
                                    "start_y": start_pos[1],
                                    "target_x": wagon_dest_x,
                                    "target_y": wagon_dest_y,
                                    "t": 0.0,
                                    "speed": 0.08 + idx * 0.02,
                                })
                            loaded_count += to_load
                            note_idx = min(9, loaded_count)
                            sounds.play(f"load_{note_idx}")

                            if loaded_count >= target_count:
                                train_state = "celebrating"
                                celebration_timer = 2.4
                                sounds.play("win")
                                total_stars += 1
                                if storage:
                                    storage.kv_set(STORAGE_KEY, {"stars": total_stars})
                                try:
                                    emit_activity_event(
                                        "train.station_completed",
                                        {"mode": mode, "target": target_count, "stars": total_stars},
                                        idempotency_key=f"station-{round_idx}",
                                    )
                                except Exception:
                                    pass

        if is_victory:
            if not completion_presented:
                completion.prepare(completion_content)
                completion.draw(canvas.surface)
                canvas.present(clear=theme.background)
                pygame.display.flip()
                completion_presented = True
            clock.tick(25)
            continue

        # Update train animation state machine
        if train_state == "arriving":
            train_offset_x += 16.0
            chug_timer += dt
            if chug_timer > 0.22:
                chug_timer = 0.0
                sounds.play("chug")
                smoke_particles.append({
                    "x": 360 + train_offset_x + 280,
                    "y": 140,
                    "vx": random.uniform(-1.5, -0.5),
                    "vy": random.uniform(-2.5, -1.0),
                    "radius": random.uniform(14, 22),
                    "alpha": 220,
                })
            if train_offset_x >= 0.0:
                train_offset_x = 0.0
                train_state = "loading"

        elif train_state == "departing":
            train_offset_x += 18.0
            chug_timer += dt
            if chug_timer > 0.18:
                chug_timer = 0.0
                sounds.play("chug")
                smoke_particles.append({
                    "x": 360 + train_offset_x + 280,
                    "y": 140,
                    "vx": random.uniform(-2.5, -1.0),
                    "vy": random.uniform(-2.5, -1.0),
                    "radius": random.uniform(14, 24),
                    "alpha": 220,
                })
            if train_offset_x > REFERENCE_WIDTH + 400:
                round_idx += 1
                if round_idx >= total_stations:
                    is_victory = True
                    train_state = "victory"
                    emit_activity_event(
                        "train.journey_completed",
                        {"stations": total_stations, "stars": total_stars},
                        idempotency_key="journey-completed",
                    )
                else:
                    setup_station(round_idx)

        elif train_state == "celebrating":
            celebration_timer -= dt
            if random.random() < 0.4:
                celebration_particles.append({
                    "x": random.uniform(100, REFERENCE_WIDTH - 100),
                    "y": random.uniform(60, 320),
                    "vx": random.uniform(-3, 3),
                    "vy": random.uniform(-4, 2),
                    "color": random.choice([(239, 68, 68), (234, 179, 8), (34, 197, 94), (59, 130, 246), (168, 85, 247), (244, 114, 182)]),
                    "size": random.uniform(8, 16),
                })
            if celebration_timer <= 0:
                train_state = "departing"
                sounds.play("whistle")

        # Update flying items
        surviving_flying: list[dict[str, Any]] = []
        for item in flying_items:
            item["t"] += item["speed"]
            if item["t"] < 1.0:
                surviving_flying.append(item)
        flying_items = surviving_flying

        # Update smoke
        surviving_smoke = []
        for p in smoke_particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["alpha"] = max(0, p["alpha"] - 5)
            p["radius"] += 0.5
            if p["alpha"] > 0:
                surviving_smoke.append(p)
        smoke_particles = surviving_smoke

        # RENDER TO CANVAS
        surf = canvas.surface

        # 1. Sky & Sun
        surf.fill((186, 230, 253))  # Soft Italian azure sky
        # Smiling Sun with Corona Rays
        sun_cx, sun_cy = 150, 100
        sun_ang_base = t_now * 0.5
        for ray_i in range(12):
            ang = sun_ang_base + ray_i * (math.pi / 6.0)
            rx1 = sun_cx + math.cos(ang) * 46
            ry1 = sun_cy + math.sin(ang) * 46
            rx2 = sun_cx + math.cos(ang) * 62
            ry2 = sun_cy + math.sin(ang) * 62
            pygame.draw.line(surf, (253, 224, 71), (int(rx1), int(ry1)), (int(rx2), int(ry2)), 4)
        pygame.draw.circle(surf, (254, 240, 138), (sun_cx, sun_cy), 44)
        pygame.draw.circle(surf, (250, 204, 21), (sun_cx, sun_cy), 38)
        # Sun Friendly Face
        pygame.draw.circle(surf, (161, 98, 7), (sun_cx - 10, sun_cy - 4), 4)
        pygame.draw.circle(surf, (161, 98, 7), (sun_cx + 10, sun_cy - 4), 4)
        pygame.draw.arc(surf, (161, 98, 7), (sun_cx - 12, sun_cy - 4, 24, 18), math.pi, 0, 3)

        # Distant Cumulus Clouds
        for c_idx, (cl_x, cl_y, cl_w, cl_h) in enumerate([(380, 70, 140, 50), (680, 95, 180, 60), (880, 50, 120, 44)]):
            cx_drift = int((cl_x - t_now * 4.0) % (REFERENCE_WIDTH + 300)) - 100
            pygame.draw.ellipse(surf, (255, 255, 255), (cx_drift, cl_y, cl_w, cl_h))
            pygame.draw.ellipse(surf, (241, 245, 249), (cx_drift + 10, cl_y - 12, cl_w - 40, cl_h))

        # 2. Layered Countryside Hills (Depth & Grounding)
        # Far hills
        pygame.draw.ellipse(surf, (134, 239, 172), pygame.Rect(-120, 240, 650, 260))
        pygame.draw.ellipse(surf, (110, 231, 183), pygame.Rect(380, 230, 780, 280))
        # Near hills
        pygame.draw.ellipse(surf, (74, 222, 128), pygame.Rect(120, 290, 520, 220))
        pygame.draw.ellipse(surf, (34, 197, 94), pygame.Rect(580, 300, 500, 220))

        # Ground Meadow
        pygame.draw.rect(surf, (22, 163, 74), (0, 390, REFERENCE_WIDTH, 210))
        pygame.draw.rect(surf, (21, 128, 61), (0, 420, REFERENCE_WIDTH, 180))

        # Wildflower patches
        for fx, fy in [(60, 405), (280, 412), (520, 402), (760, 410), (940, 404)]:
            pygame.draw.circle(surf, (254, 240, 138), (fx, fy), 6)
            pygame.draw.circle(surf, (244, 63, 94), (fx - 4, fy - 3), 4)
            pygame.draw.circle(surf, (244, 63, 94), (fx + 4, fy - 3), 4)
            pygame.draw.circle(surf, (244, 63, 94), (fx, fy + 4), 4)

        # 3. Railway Track & Ballast Bed
        # Gravel ballast foundation
        pygame.draw.rect(surf, (100, 116, 139), (0, 370, REFERENCE_WIDTH, 24))
        for gx in range(0, REFERENCE_WIDTH, 16):
            pygame.draw.circle(surf, (71, 85, 105), (gx + 8, 382), 4)

        # Wooden Ties (Sleepers)
        for tx_idx in range(0, REFERENCE_WIDTH, 34):
            pygame.draw.rect(surf, (120, 53, 15), (tx_idx, 366, 16, 30), border_radius=3)
            pygame.draw.rect(surf, (69, 26, 3), (tx_idx + 2, 368, 12, 26), width=1, border_radius=2)

        # Polished Steel Rails
        pygame.draw.rect(surf, (148, 163, 184), (0, 368, REFERENCE_WIDTH, 6))
        pygame.draw.rect(surf, (241, 245, 249), (0, 368, REFERENCE_WIDTH, 2))
        pygame.draw.rect(surf, (71, 85, 105), (0, 374, REFERENCE_WIDTH, 3))

        # 4. Smoke Particles (Behind Train)
        for p in smoke_particles:
            alpha_surf = pygame.Surface((int(p["radius"] * 2), int(p["radius"] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(alpha_surf, (255, 255, 255, int(p["alpha"])), (int(p["radius"]), int(p["radius"])), int(p["radius"]))
            pygame.draw.circle(alpha_surf, (226, 232, 240, int(p["alpha"] * 0.6)), (int(p["radius"] - 2), int(p["radius"] - 2)), int(p["radius"] * 0.7))
            surf.blit(alpha_surf, (p["x"] - p["radius"], p["y"] - p["radius"]))

        # 5. Train Rendering (Wagon + Locomotive + Conductor Dani + Wheels)
        tx = train_offset_x
        wheel_ang = tx * 0.12

        # A. Cargo Wagon (Behind on Left)
        wagon_x = 100 + tx
        wagon_surf = _get_scaled_asset("wagon.png", 260, 162)
        if wagon_surf is not None:
            surf.blit(wagon_surf, (int(wagon_x), 215))
        else:
            pygame.draw.rect(surf, (217, 119, 6), (wagon_x, 240, 260, 130), border_radius=14)

        # Loaded Fruits inside Wagon
        for idx in range(loaded_count):
            fx = wagon_x + 42 + (idx % 5) * 44
            fy = 285 + (idx // 5) * 36
            _draw_fruit(surf, current_fruit["id"], int(fx), int(fy), 38)

        # Wagon Wheels (Rotating Small Wheels)
        w_small_surf = _get_scaled_asset("wheel_small.png", 46, 46)
        for wgw in (wagon_x + 55, wagon_x + 205):
            if w_small_surf is not None:
                rot_w = pygame.transform.rotate(w_small_surf, math.degrees(wheel_ang))
                surf.blit(rot_w, rot_w.get_rect(center=(int(wgw), 378)))
            else:
                pygame.draw.circle(surf, (30, 41, 59), (int(wgw), 378), 20)
                pygame.draw.circle(surf, (234, 179, 8), (int(wgw), 378), 12)

        # B. Locomotive (Engine in Front on Right)
        loco_x = 360 + tx
        loco_surf = _get_scaled_asset("locomotive.png", 340, 255)
        if loco_surf is not None:
            surf.blit(loco_surf, (int(loco_x), 130))
        else:
            pygame.draw.rect(surf, (239, 68, 68), (loco_x + 90, 210, 220, 150), border_radius=18)
            pygame.draw.rect(surf, (59, 130, 246), (loco_x, 180, 130, 180), border_radius=16)

        # Conductor Dani Mascot leaning out of cab window
        dani_surf = _get_scaled_asset("conductor_dani.png", 66, 66)
        if dani_surf is not None:
            dani_y_bob = int(math.sin(t_now * 6.0) * 2.0) if train_state in ("arriving", "departing") else 0
            if train_state == "celebrating":
                dani_y_bob = -6 + int(math.sin(t_now * 12.0) * 5.0)
            surf.blit(dani_surf, (int(loco_x + 40), 195 + dani_y_bob))

        # Large Locomotive Driving Wheels with Rotating Counterweights
        w_large_surf = _get_scaled_asset("wheel_large.png", 66, 66)
        for wx in (loco_x + 130, loco_x + 205, loco_x + 280):
            if w_large_surf is not None:
                rot_wl = pygame.transform.rotate(w_large_surf, math.degrees(wheel_ang))
                surf.blit(rot_wl, rot_wl.get_rect(center=(int(wx), 378)))
            else:
                pygame.draw.circle(surf, (30, 41, 59), (int(wx), 378), 24)
                pygame.draw.circle(surf, (234, 179, 8), (int(wx), 378), 16)

        # Steel Connecting Driving Rod
        rod_y_off = math.sin(wheel_ang) * 9
        rod_x_off = math.cos(wheel_ang) * 9
        rod_p1 = (int(loco_x + 130 + rod_x_off), int(378 + rod_y_off))
        rod_p2 = (int(loco_x + 280 + rod_x_off), int(378 + rod_y_off))
        pygame.draw.line(surf, (148, 163, 184), rod_p1, rod_p2, 7)
        pygame.draw.line(surf, (51, 65, 85), rod_p1, rod_p2, 2)
        pygame.draw.circle(surf, (254, 240, 138), rod_p1, 5)
        pygame.draw.circle(surf, (254, 240, 138), rod_p2, 5)

        # 6. Flying Fruits
        for item in flying_items:
            t = item["t"]
            cx = item["start_x"] + (item["target_x"] - item["start_x"]) * t
            cy = item["start_y"] + (item["target_y"] - item["start_y"]) * t - math.sin(t * math.pi) * 140.0
            pygame.draw.ellipse(surf, (30, 41, 59, 80), (int(cx - 16), int(cy + 24), 32, 12))
            _draw_fruit(surf, item["fruit"], int(cx), int(cy), 48)

        # 7. Top Station Equation Billboard
        goal_rect = pygame.Rect(REFERENCE_WIDTH // 2 - 280, 14, 560, 94)
        pygame.draw.rect(surf, (255, 252, 245), goal_rect, border_radius=24)
        pygame.draw.rect(surf, (234, 179, 8), goal_rect, width=4, border_radius=24)
        pygame.draw.rect(surf, (254, 240, 138), (goal_rect.left + 6, goal_rect.top + 6, goal_rect.width - 12, 10), border_radius=5)

        if mode == "addition":
            num_a_surf = typography.render(str(val_a), FontRole.DISPLAY, 48, (217, 119, 6))
            surf.blit(num_a_surf, (goal_rect.left + 28, goal_rect.centery - num_a_surf.get_height() // 2))
            _draw_fruit(surf, current_fruit["id"], goal_rect.left + 78, goal_rect.centery, 38)

            plus_surf = typography.render("+", FontRole.DISPLAY, 48, (100, 116, 139))
            surf.blit(plus_surf, (goal_rect.left + 114, goal_rect.centery - plus_surf.get_height() // 2))

            num_b_surf = typography.render(str(val_b), FontRole.DISPLAY, 48, (217, 119, 6))
            surf.blit(num_b_surf, (goal_rect.left + 158, goal_rect.centery - num_b_surf.get_height() // 2))
            _draw_fruit(surf, current_fruit["id"], goal_rect.left + 208, goal_rect.centery, 38)

            eq_surf = typography.render("=", FontRole.DISPLAY, 48, (100, 116, 139))
            surf.blit(eq_surf, (goal_rect.left + 244, goal_rect.centery - eq_surf.get_height() // 2))

            num_tgt_surf = typography.render(str(target_count), FontRole.DISPLAY, 54, (22, 101, 52))
            surf.blit(num_tgt_surf, (goal_rect.left + 295, goal_rect.centery - num_tgt_surf.get_height() // 2))
            _draw_fruit(surf, current_fruit["id"], goal_rect.left + 355, goal_rect.centery, 46)

            # Slot indicators
            for s in range(target_count):
                slot_x = goal_rect.left + 405 + s * 26
                slot_y = goal_rect.centery
                if s < loaded_count:
                    pygame.draw.circle(surf, (34, 197, 94), (slot_x, slot_y), 11)
                    pygame.draw.circle(surf, (255, 255, 255), (slot_x - 3, slot_y - 3), 3)
                else:
                    pygame.draw.circle(surf, (203, 213, 225), (slot_x, slot_y), 11, 3)

        else:  # Count mode
            num_tgt_surf = typography.render(f"{loaded_count} / {target_count}", FontRole.DISPLAY, 52, (22, 101, 52))
            surf.blit(num_tgt_surf, (goal_rect.left + 60, goal_rect.centery - num_tgt_surf.get_height() // 2))
            _draw_fruit(surf, current_fruit["id"], goal_rect.left + 280, goal_rect.centery, 52)
            for s in range(target_count):
                slot_x = goal_rect.left + 340 + s * 34
                slot_y = goal_rect.centery
                if s < loaded_count:
                    pygame.draw.circle(surf, (34, 197, 94), (slot_x, slot_y), 12)
                    pygame.draw.circle(surf, (255, 255, 255), (slot_x - 3, slot_y - 3), 4)
                else:
                    pygame.draw.circle(surf, (203, 213, 225), (slot_x, slot_y), 12, 3)

        # 8. Bottom Fruit Cargo Crates (Interaction Targets)
        crate_surf = _get_scaled_asset("crate_basket.png", 200, 130)
        if mode == "addition":
            b_a = pygame.Rect(80, 430, 200, 130)
            if crate_surf is not None:
                surf.blit(crate_surf, (b_a.left, b_a.top))
            else:
                pygame.draw.rect(surf, (254, 243, 199), b_a, border_radius=20)
                pygame.draw.rect(surf, (217, 119, 6), b_a, width=4, border_radius=20)

            lbl_a = typography.render(str(val_a), FontRole.DISPLAY, 46, (180, 83, 9))
            surf.blit(lbl_a, (b_a.centerx - 52, b_a.centery - lbl_a.get_height() // 2))
            for i in range(val_a):
                _draw_fruit(surf, current_fruit["id"], b_a.centerx + 10 + (i % 2) * 36, b_a.centery - 15 + (i // 2) * 30, 36)

            b_b = pygame.Rect(320, 430, 200, 130)
            if crate_surf is not None:
                surf.blit(crate_surf, (b_b.left, b_b.top))
            else:
                pygame.draw.rect(surf, (254, 243, 199), b_b, border_radius=20)
                pygame.draw.rect(surf, (217, 119, 6), b_b, width=4, border_radius=20)

            lbl_b = typography.render(str(val_b), FontRole.DISPLAY, 46, (180, 83, 9))
            surf.blit(lbl_b, (b_b.centerx - 52, b_b.centery - lbl_b.get_height() // 2))
            for i in range(val_b):
                _draw_fruit(surf, current_fruit["id"], b_b.centerx + 10 + (i % 2) * 36, b_b.centery - 15 + (i // 2) * 30, 36)

        else:
            b_c = pygame.Rect(120, 430, 280, 130)
            crate_large_surf = _get_scaled_asset("crate_basket.png", 280, 130)
            if crate_large_surf is not None:
                surf.blit(crate_large_surf, (b_c.left, b_c.top))
            else:
                pygame.draw.rect(surf, (254, 243, 199), b_c, border_radius=20)
                pygame.draw.rect(surf, (217, 119, 6), b_c, width=4, border_radius=20)

            _draw_fruit(surf, current_fruit["id"], b_c.centerx - 45, b_c.centery, 52)
            lbl_one = typography.render("+1", FontRole.DISPLAY, 48, (22, 101, 52))
            surf.blit(lbl_one, (b_c.centerx + 25, b_c.centery - lbl_one.get_height() // 2))

        # 9. Top Star Pill (HUD)
        star_pill = pygame.Rect(80, 16, 130, 56)
        pygame.draw.rect(surf, (255, 255, 255), star_pill, border_radius=18)
        pygame.draw.rect(surf, (234, 179, 8), star_pill, width=3, border_radius=18)
        pygame.draw.circle(surf, (234, 179, 8), (star_pill.left + 30, star_pill.centery), 16)
        s_txt = typography.render(str(total_stars), FontRole.DISPLAY, 28, (180, 83, 9))
        surf.blit(s_txt, (star_pill.left + 58, star_pill.centery - s_txt.get_height() // 2))

        # 10. Celebration Stars Burst
        for p in celebration_particles:
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), int(p["size"]))
            pygame.draw.circle(surf, (255, 255, 255), (int(p["x"] - 2), int(p["y"] - 2)), int(p["size"] // 3))

        canvas.present()
        pygame.display.flip()

        if not first_frame_ready:
            mark_activity_ready()
            first_frame_ready = True

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
