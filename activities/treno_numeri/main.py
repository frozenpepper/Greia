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
STORAGE_KEY = "treno_numeri.progress.v2"

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
                samples.append(int(32767.0 * 0.32 * env * val))
            self._sounds[f"count_{idx + 1}"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(samples)))

        # Win chime
        win_samples = []
        for i in range(int(rate * 0.55)):
            t = i / rate
            env = math.exp(-1.8 * t)
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


def _draw_fruit(surface: pygame.Surface, fruit_id: str, cx: int, cy: int, size: int) -> None:
    r = size // 2
    dark = (30, 41, 59)
    if fruit_id == "apple":
        pygame.draw.circle(surface, (239, 68, 68), (cx - r // 4, cy), r * 4 // 5)
        pygame.draw.circle(surface, (220, 38, 38), (cx + r // 4, cy), r * 4 // 5)
        pygame.draw.circle(surface, dark, (cx - r // 4, cy), r * 4 // 5, 2)
        pygame.draw.circle(surface, dark, (cx + r // 4, cy), r * 4 // 5, 2)
        pygame.draw.rect(surface, (120, 53, 15), (cx - 2, cy - r, 4, r // 2), border_radius=2)
        pygame.draw.ellipse(surface, (34, 197, 94), pygame.Rect(cx + 2, cy - r + 2, r // 2, r // 3))
        pygame.draw.ellipse(surface, dark, pygame.Rect(cx + 2, cy - r + 2, r // 2, r // 3), 1)
        pygame.draw.circle(surface, (255, 255, 255), (cx - r // 3, cy - r // 3), max(2, r // 4))
    elif fruit_id == "banana":
        pygame.draw.arc(surface, dark, pygame.Rect(cx - r - 2, cy - r - 2, r * 2 + 4, r * 2 + 4), 0.6, 2.6, max(6, r // 2 + 4))
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
        pygame.draw.circle(surface, (244, 63, 94), (cx - r // 3, cy - r // 3), r // 2)
        pygame.draw.circle(surface, (244, 63, 94), (cx + r // 3, cy - r // 3), r // 2)
        pygame.draw.polygon(surface, dark, pts, 2)
        pygame.draw.circle(surface, dark, (cx - r // 3, cy - r // 3), r // 2, 2)
        pygame.draw.circle(surface, dark, (cx + r // 3, cy - r // 3), r // 2, 2)
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
    train_offset_x = 0.0
    train_departing = False
    train_arriving = True
    train_speed = 12.0
    smoke_particles: list[dict[str, Any]] = []
    flying_items: list[dict[str, Any]] = []
    confetti: list[dict[str, Any]] = []
    whistle_anim = 0.0

    def setup_station(idx: int) -> None:
        nonlocal mode, val_a, val_b, target_count, loaded_count, current_fruit
        nonlocal train_departing, train_arriving, train_offset_x
        current_fruit = FRUITS[idx % len(FRUITS)]
        loaded_count = 0
        train_offset_x = -float(REFERENCE_WIDTH)
        train_arriving = True
        train_departing = False

        if idx % 2 == 0:
            mode = "addition"
            val_a = random.randint(1, 3)
            val_b = random.randint(1, 3)
            target_count = val_a + val_b
        else:
            mode = "count"
            val_a = random.randint(2, 5)
            val_b = 0
            target_count = val_a

    setup_station(0)

    running = True
    ready_published = False

    while running and not activity_stop_requested():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
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
                    # Restart button
                    play_again_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 120, REFERENCE_HEIGHT // 2 + 70, 240, 60)
                    if play_again_btn.collidepoint(mx, my):
                        is_victory = False
                        round_idx = 0
                        setup_station(0)
                    continue

                # Whistle Button
                whistle_btn = pygame.Rect(REFERENCE_WIDTH - 160, 16, 140, 56)
                if whistle_btn.collidepoint(mx, my):
                    sounds.play("whistle")
                    whistle_anim = 1.0
                    for _ in range(8):
                        smoke_particles.append({
                            "x": 611 + train_offset_x,
                            "y": 165,
                            "vx": random.uniform(-2, -5),
                            "vy": random.uniform(-4, -8),
                            "radius": random.uniform(14, 26),
                            "alpha": 255,
                        })
                    continue

                # Math Baskets
                if not train_arriving and not train_departing:
                    if mode == "addition":
                        basket_a_rect = pygame.Rect(80, 430, 200, 130)
                        basket_b_rect = pygame.Rect(320, 430, 200, 130)

                        if basket_a_rect.collidepoint(mx, my) and val_a > 0:
                            for i in range(val_a):
                                flying_items.append({
                                    "fruit": current_fruit["id"],
                                    "start_x": basket_a_rect.centerx + (i - val_a / 2) * 20,
                                    "start_y": basket_a_rect.centery,
                                    "target_x": 140 + train_offset_x + ((loaded_count + i) % 5) * 44,
                                    "target_y": 295 + ((loaded_count + i) // 5) * 36,
                                    "t": 0.0,
                                    "speed": 0.05,
                                })
                            loaded_count += val_a
                            val_a = 0
                            sounds.play(f"count_{min(10, loaded_count)}")

                        elif basket_b_rect.collidepoint(mx, my) and val_b > 0:
                            for i in range(val_b):
                                flying_items.append({
                                    "fruit": current_fruit["id"],
                                    "start_x": basket_b_rect.centerx + (i - val_b / 2) * 20,
                                    "start_y": basket_b_rect.centery,
                                    "target_x": 140 + train_offset_x + ((loaded_count + i) % 5) * 44,
                                    "target_y": 295 + ((loaded_count + i) // 5) * 36,
                                    "t": 0.0,
                                    "speed": 0.05,
                                })
                            loaded_count += val_b
                            val_b = 0
                            sounds.play(f"count_{min(10, loaded_count)}")

                    else:  # Count mode
                        tree_rect = pygame.Rect(120, 420, 360, 140)
                        if tree_rect.collidepoint(mx, my) and loaded_count < target_count:
                            flying_items.append({
                                "fruit": current_fruit["id"],
                                "start_x": mx,
                                "start_y": my,
                                "target_x": 140 + train_offset_x + (loaded_count % 5) * 44,
                                "target_y": 295 + (loaded_count // 5) * 36,
                                "t": 0.0,
                                "speed": 0.06,
                            })
                            loaded_count += 1
                            sounds.play(f"count_{min(10, loaded_count)}")

                    # Check completion
                    if loaded_count >= target_count and not train_departing:
                        train_departing = True
                        sounds.play("whistle")
                        sounds.play("win")
                        total_stars += 1
                        if storage:
                            storage.kv_set(STORAGE_KEY, {"stars": total_stars})
                        try:
                            emit_activity_event("train.station_completed", {"station": round_idx + 1, "stars": total_stars})
                        except Exception:
                            pass

        # Train arrival / departure kinematics
        if train_arriving:
            train_offset_x += train_speed
            if random.random() < 0.25:
                smoke_particles.append({
                    "x": 611 + train_offset_x,
                    "y": 165,
                    "vx": random.uniform(-4, -1),
                    "vy": random.uniform(-2, -5),
                    "radius": random.uniform(10, 18),
                    "alpha": 200,
                })
            if train_offset_x >= 0:
                train_offset_x = 0
                train_arriving = False
                sounds.play("chug")
        elif train_departing:
            train_offset_x += train_speed * 1.5
            if random.random() < 0.35:
                smoke_particles.append({
                    "x": 611 + train_offset_x,
                    "y": 165,
                    "vx": random.uniform(-5, -2),
                    "vy": random.uniform(-3, -6),
                    "radius": random.uniform(12, 22),
                    "alpha": 220,
                })
            if train_offset_x > REFERENCE_WIDTH:
                round_idx += 1
                if round_idx >= total_stations:
                    is_victory = True
                    for _ in range(60):
                        confetti.append({
                            "x": random.uniform(100, REFERENCE_WIDTH - 100),
                            "y": random.uniform(50, 300),
                            "vx": random.uniform(-3, 3),
                            "vy": random.uniform(2, 6),
                            "color": random.choice([(239, 68, 68), (234, 179, 8), (34, 197, 94), (59, 130, 246), (168, 85, 247)]),
                            "size": random.uniform(6, 12),
                        })
                else:
                    setup_station(round_idx)

        # Update flying fruits
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
            p["alpha"] = max(0, p["alpha"] - 6)
            p["radius"] += 0.4
            if p["alpha"] > 0:
                surviving_smoke.append(p)
        smoke_particles = surviving_smoke

        # RENDER TO CANVAS
        surf = canvas.surface

        # 1. Sky & Landscape
        surf.fill((186, 230, 253))  # Soft sky
        # Sun
        pygame.draw.circle(surf, (254, 240, 138), (140, 100), 50)
        pygame.draw.circle(surf, (253, 224, 71), (140, 100), 42)

        # Rolling green hills
        pygame.draw.ellipse(surf, (134, 239, 172), pygame.Rect(-100, 260, 600, 300))
        pygame.draw.ellipse(surf, (74, 222, 128), pygame.Rect(400, 280, 750, 300))
        pygame.draw.rect(surf, (34, 197, 94), (0, 390, REFERENCE_WIDTH, 210))

        # Train Tracks
        pygame.draw.rect(surf, (120, 53, 15), (0, 380, REFERENCE_WIDTH, 14))
        for tx in range(0, REFERENCE_WIDTH, 36):
            pygame.draw.rect(surf, (180, 83, 9), (tx, 374, 14, 26), border_radius=2)
        pygame.draw.rect(surf, (148, 163, 184), (0, 372, REFERENCE_WIDTH, 6))

        # 2. Smoke Particles
        for p in smoke_particles:
            alpha_surf = pygame.Surface((int(p["radius"] * 2), int(p["radius"] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(alpha_surf, (241, 245, 249, int(p["alpha"])), (int(p["radius"]), int(p["radius"])), int(p["radius"]))
            surf.blit(alpha_surf, (p["x"] - p["radius"], p["y"] - p["radius"]))

        # 3. Train & Wagons (Locomotive in Front Leading, Wagon Behind)
        tx = train_offset_x
        wheel_ang = tx * 0.12

        # Cargo Wagon (Behind on Left)
        wagon_x = 100 + tx
        pygame.draw.rect(surf, (217, 119, 6), (wagon_x, 260, 260, 110), border_radius=14)
        pygame.draw.rect(surf, (180, 83, 9), (wagon_x, 260, 260, 110), width=4, border_radius=14)
        # Wagon Slats
        for sl in range(4):
            pygame.draw.line(surf, (180, 83, 9), (wagon_x + 10, 280 + sl * 22), (wagon_x + 250, 280 + sl * 22), 3)
        # Wagon Wheels
        for wgw in (wagon_x + 55, wagon_x + 205):
            pygame.draw.circle(surf, (30, 41, 59), (int(wgw), 378), 20)
            pygame.draw.circle(surf, (234, 179, 8), (int(wgw), 378), 12)
            w_sp1 = (int(wgw + math.cos(wheel_ang) * 9), int(378 + math.sin(wheel_ang) * 9))
            w_sp2 = (int(wgw - math.cos(wheel_ang) * 9), int(378 - math.sin(wheel_ang) * 9))
            pygame.draw.line(surf, (180, 83, 9), w_sp1, w_sp2, 3)
            pygame.draw.circle(surf, (255, 255, 255), (int(wgw), 378), 4)

        # Draw Loaded Fruits inside Wagon
        for idx in range(loaded_count):
            fx = wagon_x + 40 + (idx % 5) * 44
            fy = 295 + (idx // 5) * 36
            _draw_fruit(surf, current_fruit["id"], int(fx), int(fy), 36)

        # Coupler Hitch
        pygame.draw.rect(surf, (71, 85, 105), (wagon_x + 258, 320, 44, 16), border_radius=4)
        pygame.draw.circle(surf, (203, 213, 225), (wagon_x + 280, 328), 6)

        # Locomotive (Engine in Front on Right)
        loco_x = 400 + tx
        # Cab (Back of locomotive)
        pygame.draw.rect(surf, (59, 130, 246), (loco_x, 220, 130, 150), border_radius=16)
        pygame.draw.rect(surf, (29, 78, 216), (loco_x, 220, 130, 150), width=4, border_radius=16)
        # Cab Window with Friendly Driver
        pygame.draw.rect(surf, (224, 242, 254), (loco_x + 25, 245, 65, 55), border_radius=12)
        pygame.draw.circle(surf, (251, 191, 36), (int(loco_x + 57), 275), 18)  # Driver Face
        # Boiler (Front of locomotive)
        pygame.draw.rect(surf, (239, 68, 68), (loco_x + 110, 250, 140, 120), border_radius=18)
        pygame.draw.rect(surf, (185, 28, 28), (loco_x + 110, 250, 140, 120), width=4, border_radius=18)
        # Steam Dome
        pygame.draw.rect(surf, (234, 179, 8), (loco_x + 140, 230, 24, 22), border_radius=6)
        # Chimney & Funnel
        pygame.draw.rect(surf, (30, 41, 59), (loco_x + 195, 185, 32, 70), border_radius=6)
        pygame.draw.polygon(surf, (234, 179, 8), [(loco_x + 185, 185), (loco_x + 237, 185), (loco_x + 211, 165)])
        # Headlamp & Cowcatcher (Facing Forward Right)
        pygame.draw.circle(surf, (254, 240, 138), (loco_x + 248, 275), 14)
        pygame.draw.circle(surf, (234, 179, 8), (loco_x + 248, 275), 14, 3)
        pygame.draw.polygon(surf, (234, 179, 8), [(loco_x + 245, 345), (loco_x + 280, 375), (loco_x + 245, 375)])

        # Large Golden Locomotive Wheels with Rotating Spokes and Driving Rod
        wheel_ang = (train_offset_x) * 0.12
        for wx in (loco_x + 45, loco_x + 125, loco_x + 205):
            pygame.draw.circle(surf, (30, 41, 59), (int(wx), 378), 24)
            pygame.draw.circle(surf, (234, 179, 8), (int(wx), 378), 16)
            sp1_x = wx + math.cos(wheel_ang) * 12
            sp1_y = 378 + math.sin(wheel_ang) * 12
            sp2_x = wx - math.cos(wheel_ang) * 12
            sp2_y = 378 - math.sin(wheel_ang) * 12
            pygame.draw.line(surf, (180, 83, 9), (int(sp1_x), int(sp1_y)), (int(sp2_x), int(sp2_y)), 3)
            sp3_x = wx - math.sin(wheel_ang) * 12
            sp3_y = 378 + math.cos(wheel_ang) * 12
            sp4_x = wx + math.sin(wheel_ang) * 12
            sp4_y = 378 - math.cos(wheel_ang) * 12
            pygame.draw.line(surf, (180, 83, 9), (int(sp3_x), int(sp3_y)), (int(sp4_x), int(sp4_y)), 3)
            pygame.draw.circle(surf, (255, 255, 255), (int(wx), 378), 6)

        # Connecting driving rod
        rod_y_off = math.sin(wheel_ang) * 8
        rod_x_off = math.cos(wheel_ang) * 8
        rod_p1 = (int(loco_x + 45 + rod_x_off), int(378 + rod_y_off))
        rod_p2 = (int(loco_x + 205 + rod_x_off), int(378 + rod_y_off))
        pygame.draw.line(surf, (148, 163, 184), rod_p1, rod_p2, 6)
        pygame.draw.line(surf, (51, 65, 85), rod_p1, rod_p2, 2)

        # 4. Flying Fruits
        for item in flying_items:
            t = item["t"]
            cx = item["start_x"] + (item["target_x"] - item["start_x"]) * t
            cy = item["start_y"] + (item["target_y"] - item["start_y"]) * t - math.sin(t * math.pi) * 120.0
            _draw_fruit(surf, item["fruit"], int(cx), int(cy), 44)

        # 5. Top Math Goal Billboard (Zero-Text Visual Equation)
        goal_rect = pygame.Rect(REFERENCE_WIDTH // 2 - 270, 14, 540, 94)
        pygame.draw.rect(surf, (255, 252, 245), goal_rect, border_radius=24)
        pygame.draw.rect(surf, (234, 179, 8), goal_rect, width=4, border_radius=24)

        if mode == "addition":
            # Display: [val_a] [Fruit]  +  [val_b] [Fruit]  =  [target] [Fruit]
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
                    pygame.draw.circle(surf, (34, 197, 94), (slot_x, slot_y), 10)
                else:
                    pygame.draw.circle(surf, (203, 213, 225), (slot_x, slot_y), 10, 3)

        else:  # Count mode
            num_tgt_surf = typography.render(f"{loaded_count} / {target_count}", FontRole.DISPLAY, 52, (22, 101, 52))
            surf.blit(num_tgt_surf, (goal_rect.left + 60, goal_rect.centery - num_tgt_surf.get_height() // 2))
            _draw_fruit(surf, current_fruit["id"], goal_rect.left + 280, goal_rect.centery, 52)
            # Slot indicators
            for s in range(target_count):
                slot_x = goal_rect.left + 340 + s * 34
                slot_y = goal_rect.centery
                if s < loaded_count:
                    pygame.draw.circle(surf, (34, 197, 94), (slot_x, slot_y), 12)
                else:
                    pygame.draw.circle(surf, (203, 213, 225), (slot_x, slot_y), 12, 3)

        # 6. Bottom Interaction Baskets (Giant Chunky Hit Targets)
        if mode == "addition":
            # Basket A
            b_a = pygame.Rect(80, 430, 200, 130)
            pygame.draw.rect(surf, (254, 243, 199), b_a, border_radius=20)
            pygame.draw.rect(surf, (217, 119, 6), b_a, width=4, border_radius=20)
            lbl_a = typography.render(str(val_a), FontRole.DISPLAY, 46, (180, 83, 9))
            surf.blit(lbl_a, (b_a.centerx - 45, b_a.centery - lbl_a.get_height() // 2))
            for i in range(val_a):
                _draw_fruit(surf, current_fruit["id"], b_a.centerx + 10 + (i % 2) * 34, b_a.centery - 15 + (i // 2) * 30, 32)

            # Basket B
            b_b = pygame.Rect(320, 430, 200, 130)
            pygame.draw.rect(surf, (254, 243, 199), b_b, border_radius=20)
            pygame.draw.rect(surf, (217, 119, 6), b_b, width=4, border_radius=20)
            lbl_b = typography.render(str(val_b), FontRole.DISPLAY, 46, (180, 83, 9))
            surf.blit(lbl_b, (b_b.centerx - 45, b_b.centery - lbl_b.get_height() // 2))
            for i in range(val_b):
                _draw_fruit(surf, current_fruit["id"], b_b.centerx + 10 + (i % 2) * 34, b_b.centery - 15 + (i // 2) * 30, 32)

        else:
            # Giant Fruit Tree/Crate
            tree_crate = pygame.Rect(120, 420, 380, 145)
            pygame.draw.rect(surf, (254, 243, 199), tree_crate, border_radius=24)
            pygame.draw.rect(surf, (217, 119, 6), tree_crate, width=4, border_radius=24)
            for i in range(target_count - loaded_count):
                fx = tree_crate.left + 50 + (i % 5) * 65
                fy = tree_crate.top + 50 + (i // 5) * 50
                _draw_fruit(surf, current_fruit["id"], int(fx), int(fy), 46)

        # 7. Whistle & Station HUD Buttons
        w_btn = pygame.Rect(REFERENCE_WIDTH - 150, 14, 130, 58)
        pygame.draw.rect(surf, (234, 179, 8), w_btn, border_radius=18)
        pygame.draw.rect(surf, (202, 138, 4), w_btn, width=3, border_radius=18)
        wy = w_btn.centery
        # Whistle icon + steam
        pygame.draw.rect(surf, (241, 245, 249), (w_btn.left + 14, wy - 8, 28, 16), border_radius=4)
        pygame.draw.rect(surf, (239, 68, 68), (w_btn.left + 22, wy - 16, 10, 10), border_radius=2)
        w_txt = typography.render("TUUT!", FontRole.DISPLAY, 18, (120, 53, 15))
        surf.blit(w_txt, (w_btn.left + 48, wy - w_txt.get_height() // 2))

        # Station Stars Indicator (Top Left)
        star_pill = pygame.Rect(80, 16, 130, 56)
        pygame.draw.rect(surf, (255, 255, 255), star_pill, border_radius=18)
        pygame.draw.rect(surf, (234, 179, 8), star_pill, width=3, border_radius=18)
        pygame.draw.circle(surf, (234, 179, 8), (star_pill.left + 30, star_pill.centery), 16)
        s_txt = typography.render(str(total_stars), FontRole.DISPLAY, 28, (180, 83, 9))
        surf.blit(s_txt, (star_pill.left + 58, star_pill.centery - s_txt.get_height() // 2))

        # 8. Victory Celebration Modal
        if is_victory:
            overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 15, 30, 210))
            surf.blit(overlay, (0, 0))

            card = pygame.Rect(REFERENCE_WIDTH // 2 - 250, REFERENCE_HEIGHT // 2 - 160, 500, 320)
            pygame.draw.rect(surf, (255, 252, 245), card, border_radius=28)
            pygame.draw.rect(surf, (234, 179, 8), card, width=5, border_radius=28)

            v_title = typography.render("BRAVISSIMA!", FontRole.DISPLAY, 36, (217, 119, 6))
            surf.blit(v_title, (card.centerx - v_title.get_width() // 2, card.top + 35))

            # Golden Stars
            for i in range(5):
                sx = card.centerx - 100 + i * 50
                sy = card.top + 130
                pygame.draw.circle(surf, (234, 179, 8), (sx, sy), 22)
                pygame.draw.circle(surf, (254, 240, 138), (sx, sy), 10)

            again_btn = pygame.Rect(card.centerx - 120, card.bottom - 80, 240, 60)
            pygame.draw.rect(surf, (34, 197, 94), again_btn, border_radius=20)
            pygame.draw.rect(surf, (22, 101, 52), again_btn, width=3, border_radius=20)
            again_lbl = typography.render("GIOCA ANCORA", FontRole.DISPLAY, 22, (255, 255, 255))
            surf.blit(again_lbl, (again_btn.centerx - again_lbl.get_width() // 2, again_btn.centery - again_lbl.get_height() // 2))

        # Present Canvas
        canvas.present()
        pygame.display.flip()

        if not ready_published:
            mark_activity_ready()
            ready_published = True

        clock.tick(30)

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
