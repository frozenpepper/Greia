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
from greia_platform.activity_ui import ChildUiMetrics
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
STORAGE_KEY = "treno_numeri.progress.v1"

ITEMS = [
    {"id": "apple", "emoji": "🍎", "color": (239, 68, 68), "name_it": "mele", "name_en": "apples"},
    {"id": "carrot", "emoji": "🥕", "color": (249, 115, 22), "name_it": "carote", "name_en": "carrots"},
    {"id": "banana", "emoji": "🍌", "color": (234, 179, 8), "name_it": "banane", "name_en": "bananas"},
    {"id": "strawberry", "emoji": "🍓", "color": (244, 63, 94), "name_it": "fragole", "name_en": "strawberries"},
    {"id": "pumpkin", "emoji": "🎃", "color": (249, 115, 22), "name_it": "zucche", "name_en": "pumpkins"},
    {"id": "orange", "emoji": "🍊", "color": (245, 158, 11), "name_it": "arance", "name_en": "oranges"},
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
        # Choo-choo whistle
        whistle_samples = []
        for i in range(int(rate * 0.45)):
            t = i / rate
            env = min(1.0, t * 10.0) * math.exp(-1.5 * t)
            freq = 600.0 if t < 0.15 else 750.0
            val = math.sin(2.0 * math.pi * freq * t) + 0.5 * math.sin(2.0 * math.pi * (freq * 1.25) * t)
            whistle_samples.append(int(32767.0 * 0.25 * env * val))
        snd_whistle = pygame.mixer.Sound(io.BytesIO(_synth_wav(whistle_samples)))
        self._sounds["whistle"] = snd_whistle

        # Steam chug
        chug_samples = []
        for i in range(int(rate * 0.08)):
            t = i / rate
            env = math.exp(-15.0 * t)
            val = random.uniform(-1.0, 1.0)
            chug_samples.append(int(32767.0 * 0.25 * env * val))
        snd_chug = pygame.mixer.Sound(io.BytesIO(_synth_wav(chug_samples)))
        self._sounds["chug"] = snd_chug

        # Item drop count (pentatonic notes for 1..10)
        scale = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25, 587.33, 659.25, 783.99, 880.00]
        for idx, freq in enumerate(scale):
            samples = []
            for i in range(int(rate * 0.20)):
                t = i / rate
                env = math.exp(-6.0 * t)
                val = math.sin(2.0 * math.pi * freq * t)
                samples.append(int(32767.0 * 0.30 * env * val))
            self._sounds[f"count_{idx + 1}"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(samples)))

        # Win chime
        win_samples = []
        for i in range(int(rate * 0.50)):
            t = i / rate
            env = math.exp(-2.0 * t)
            freq = 523.25 if t < 0.12 else (659.25 if t < 0.24 else (783.99 if t < 0.36 else 1046.50))
            val = math.sin(2.0 * math.pi * freq * t)
            win_samples.append(int(32767.0 * 0.30 * env * val))
        snd_win = pygame.mixer.Sound(io.BytesIO(_synth_wav(win_samples)))
        self._sounds["win"] = snd_win

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

    try:
        storage = get_storage()
    except Exception:
        storage = None

    package_root = Path(__file__).parent
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    profile_lang = get_profile_locale()
    context = resolve_activity_locale(profile_lang, support)
    resources = LocalizedResources(package_root, context) if context else None
    active_locale = context.selected.language if context else "it"

    def t(key: str, default: str) -> str:
        if resources is not None:
            try:
                res = resources.string(key)
                if res:
                    return res
            except Exception:
                pass
        return default

    # Game State
    station_number = 1
    total_stations = 5
    total_stars = 0

    current_item = ITEMS[0]
    target_count = 3
    loaded_count = 0

    train_x = 0.0
    target_train_x = 0.0
    is_departing = False
    depart_timer = 0.0

    particles: list[dict[str, Any]] = []
    flying_items: list[dict[str, Any]] = []
    is_victory = False

    def next_station() -> None:
        nonlocal station_number, current_item, target_count, loaded_count, is_departing, depart_timer, train_x, target_train_x
        current_item = ITEMS[(station_number - 1) % len(ITEMS)]
        target_count = min(10, 2 + station_number)
        loaded_count = 0
        train_x = -300.0
        target_train_x = 0.0
        is_departing = False
        depart_timer = 0.0
        sounds.play("whistle")

    def start_new_journey() -> None:
        nonlocal station_number, total_stars, is_victory
        station_number = 1
        total_stars = 0
        is_victory = False
        next_station()

    start_new_journey()

    def add_loaded_item(source_pos: tuple[float, float]) -> None:
        nonlocal loaded_count, is_departing, depart_timer, station_number, total_stars, is_victory
        if is_departing or is_victory or loaded_count >= target_count:
            return

        # Target position in wagon (approx x = 520, y = 330)
        wagon_target_x = 480 + (loaded_count % 5) * 28
        wagon_target_y = 315 + (loaded_count // 5) * 26

        flying_items.append({
            "start_x": source_pos[0],
            "start_y": source_pos[1],
            "target_x": float(wagon_target_x),
            "target_y": float(wagon_target_y),
            "t": 0.0,
            "color": current_item["color"],
            "emoji": current_item["emoji"],
        })

        loaded_count += 1
        sounds.play(f"count_{min(10, loaded_count)}")

        if loaded_count == target_count:
            # Station completed!
            total_stars += 1
            sounds.play("whistle")
            try:
                emit_activity_event("train.station_completed", {"station": station_number})
            except Exception:
                pass
            is_departing = True
            depart_timer = 2.0
            # Burst stars
            for _ in range(25):
                ang = random.uniform(0, 6.28)
                spd = random.uniform(2.0, 5.0)
                particles.append({
                    "x": 520.0,
                    "y": 330.0,
                    "vx": math.cos(ang) * spd,
                    "vy": math.sin(ang) * spd,
                    "color": (254, 202, 87),
                    "size": random.uniform(4.0, 8.0),
                    "life": 1.0,
                    "decay": 0.03,
                })

    running = True
    ready_published = False

    while running and not activity_stop_requested():
        t_now = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if is_victory:
                        start_new_journey()
                    elif not is_departing:
                        # Add item via keyboard
                        add_loaded_item((220.0, 480.0))
                elif event.key == pygame.K_w:
                    sounds.play("whistle")

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if not _is_safe_point(screen, event.pos):
                    continue
                logical = canvas.pointer(event.pos)
                if logical is None:
                    continue
                mx, my = logical

                if is_victory:
                    btn_rect = pygame.Rect(REFERENCE_WIDTH // 2 - 120, REFERENCE_HEIGHT // 2 + 80, 240, 52)
                    if btn_rect.collidepoint(mx, my):
                        start_new_journey()
                        continue

                # Whistle Button
                whistle_btn = pygame.Rect(REFERENCE_WIDTH - 150, 15, 130, 42)
                if whistle_btn.collidepoint(mx, my):
                    sounds.play("whistle")
                    # Spawn extra steam puffs
                    for _ in range(6):
                        particles.append({
                            "x": 260.0 + train_x,
                            "y": 250.0,
                            "vx": random.uniform(-1.5, -0.2),
                            "vy": random.uniform(-2.0, -1.0),
                            "color": (255, 255, 255),
                            "size": random.uniform(12.0, 24.0),
                            "life": 1.0,
                            "decay": 0.02,
                        })
                    continue

                # Supply Crate Click (Bottom Left Shelf x = 80..380, y = 430..550)
                crate_rect = pygame.Rect(80, 430, 300, 120)
                if crate_rect.collidepoint(mx, my):
                    add_loaded_item((float(mx), float(my)))
                    continue

        # Train movement
        if is_departing:
            target_train_x = 1100.0
            depart_timer -= 0.033
            if train_x > 1000.0:
                if station_number >= total_stations:
                    is_victory = True
                    sounds.play("win")
                    try:
                        emit_activity_event("train.journey_completed", {"stars": total_stars})
                    except Exception:
                        pass
                else:
                    station_number += 1
                    next_station()

        dx = target_train_x - train_x
        if abs(dx) > 1.0:
            train_x += dx * 0.10
            # Puff steam while moving
            if random.random() < 0.3:
                sounds.play("chug")
                particles.append({
                    "x": 260.0 + train_x,
                    "y": 240.0,
                    "vx": random.uniform(-2.5, -0.5),
                    "vy": random.uniform(-1.5, -0.5),
                    "color": (255, 255, 255),
                    "size": random.uniform(10.0, 20.0),
                    "life": 1.0,
                    "decay": 0.03,
                })
        else:
            train_x = target_train_x

        # Update flying items
        surviving_items = []
        for item in flying_items:
            item["t"] += 0.08
            if item["t"] >= 1.0:
                # Arrived at wagon: add mini puff
                for _ in range(4):
                    particles.append({
                        "x": item["target_x"],
                        "y": item["target_y"],
                        "vx": random.uniform(-1.0, 1.0),
                        "vy": random.uniform(-1.0, 1.0),
                        "color": (255, 255, 255),
                        "size": random.uniform(3.0, 6.0),
                        "life": 1.0,
                        "decay": 0.06,
                    })
            else:
                surviving_items.append(item)
        flying_items = surviving_items

        # Update particles
        surviving_particles = []
        for p in particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= p["decay"]
            if p["life"] > 0:
                surviving_particles.append(p)
        particles = surviving_particles

        # RENDER TO CANVAS
        surf = canvas.surface

        # 1. Sky & Rolling Hills Background
        surf.fill((186, 230, 253))  # Soft sky blue
        # Sun
        pygame.draw.circle(surf, (254, 240, 138), (850, 90), 45)
        # Background Hills
        pygame.draw.circle(surf, (134, 239, 172), (250, 480), 320)
        pygame.draw.circle(surf, (74, 222, 128), (800, 520), 380)
        # Ground
        pygame.draw.rect(surf, (34, 197, 94), (0, 390, REFERENCE_WIDTH, 210))

        # 2. Train Tracks
        pygame.draw.line(surf, (100, 116, 139), (0, 395), (REFERENCE_WIDTH, 395), 8)
        pygame.draw.line(surf, (71, 85, 105), (0, 405), (REFERENCE_WIDTH, 405), 8)
        for tie_x in range(0, REFERENCE_WIDTH, 25):
            pygame.draw.rect(surf, (120, 80, 50), (tie_x, 392, 14, 18))

        # 3. Draw Steam Locomotive & Wagon
        tx = train_x

        # Wagon (Back)
        wagon_rect = pygame.Rect(440 + tx, 290, 200, 90)
        pygame.draw.rect(surf, (249, 115, 22), wagon_rect, border_radius=12)
        pygame.draw.rect(surf, (194, 65, 12), wagon_rect, width=3, border_radius=12)
        # Wagon Wheels
        pygame.draw.circle(surf, (30, 41, 59), (480 + int(tx), 390), 16)
        pygame.draw.circle(surf, (148, 163, 184), (480 + int(tx), 390), 8)
        pygame.draw.circle(surf, (30, 41, 59), (600 + int(tx), 390), 16)
        pygame.draw.circle(surf, (148, 163, 184), (600 + int(tx), 390), 8)

        # Connector chain
        pygame.draw.line(surf, (51, 65, 85), (380 + tx, 350), (440 + tx, 350), 6)

        # Locomotive (Front)
        cab_rect = pygame.Rect(180 + tx, 240, 110, 140)
        boiler_rect = pygame.Rect(280 + tx, 280, 110, 100)
        pygame.draw.rect(surf, (59, 130, 246), cab_rect, border_radius=10)
        pygame.draw.rect(surf, (37, 99, 235), cab_rect, width=3, border_radius=10)
        pygame.draw.rect(surf, (239, 68, 68), boiler_rect, border_radius=14)
        # Chimney
        pygame.draw.rect(surf, (30, 41, 59), (340 + tx, 225, 26, 60), border_radius=4)
        pygame.draw.polygon(surf, (234, 179, 8), [(335 + tx, 225), (370 + tx, 225), (352 + tx, 210)])
        # Cab Window
        pygame.draw.rect(surf, (224, 242, 254), (200 + tx, 260, 45, 45), border_radius=8)
        # Train Wheels
        pygame.draw.circle(surf, (30, 41, 59), (230 + int(tx), 390), 22)
        pygame.draw.circle(surf, (234, 179, 8), (230 + int(tx), 390), 12)
        pygame.draw.circle(surf, (30, 41, 59), (310 + int(tx), 390), 18)
        pygame.draw.circle(surf, (234, 179, 8), (310 + int(tx), 390), 9)
        pygame.draw.circle(surf, (30, 41, 59), (365 + int(tx), 390), 18)
        pygame.draw.circle(surf, (234, 179, 8), (365 + int(tx), 390), 9)

        # Draw Loaded Items inside Wagon
        for idx in range(loaded_count):
            item_x = 480 + tx + (idx % 5) * 28
            item_y = 315 + (idx // 5) * 26
            pygame.draw.circle(surf, current_item["color"], (int(item_x), int(item_y)), 12)
            pygame.draw.circle(surf, (255, 255, 255), (int(item_x - 3), int(item_y - 3)), 4)

        # 4. Draw Flying Items
        for item in flying_items:
            # Parabolic trajectory
            t = item["t"]
            cur_x = item["start_x"] + (item["target_x"] - item["start_x"]) * t
            cur_y = item["start_y"] + (item["target_y"] - item["start_y"]) * t - math.sin(t * math.pi) * 100.0
            pygame.draw.circle(surf, item["color"], (int(cur_x), int(cur_y)), 16)
            pygame.draw.circle(surf, (255, 255, 255), (int(cur_x - 4), int(cur_y - 4)), 5)

        # 5. Draw Particles
        for p in particles:
            cur_sz = max(2.0, p["size"] * max(0.0, min(1.0, p["life"])))
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), int(cur_sz))

        # 6. Top Goal Billboard
        board_rect = pygame.Rect(REFERENCE_WIDTH // 2 - 200, 20, 400, 70)
        pygame.draw.rect(surf, (255, 255, 255), board_rect, border_radius=16)
        pygame.draw.rect(surf, (234, 179, 8), board_rect, width=3, border_radius=16)

        item_name = current_item["name_it"] if active_locale == "it" else current_item["name_en"]
        prompt_txt = f"Carica {target_count} {item_name} nel vagone!" if active_locale == "it" else f"Load {target_count} {item_name} in the wagon!"
        p_surf = typography.render(prompt_txt, FontRole.DISPLAY, 20, (30, 41, 59))
        surf.blit(p_surf, (board_rect.centerx - p_surf.get_width() // 2, board_rect.centery - p_surf.get_height() // 2))

        # 7. Supply Crate (Bottom Shelf)
        crate_rect = pygame.Rect(80, 430, 300, 120)
        pygame.draw.rect(surf, (254, 243, 199), crate_rect, border_radius=16)
        pygame.draw.rect(surf, (217, 119, 6), crate_rect, width=3, border_radius=16)
        crate_title = typography.render("📦 Cassa di Frutta (Tocca qui!)", FontRole.CONTROL, 16, (146, 64, 14)) if active_locale == "it" else typography.render("📦 Fruit Crate (Tap here!)", FontRole.CONTROL, 16, (146, 64, 14))
        surf.blit(crate_title, (crate_rect.centerx - crate_title.get_width() // 2, crate_rect.top + 10))

        # Draw crate fruits preview
        for i in range(4):
            fx = crate_rect.left + 50 + i * 65
            fy = crate_rect.top + 68
            pygame.draw.circle(surf, current_item["color"], (fx, fy), 18)
            pygame.draw.circle(surf, (255, 255, 255), (fx - 4, fy - 4), 5)

        # 8. Top HUD Buttons (Whistle, Score)
        whistle_btn = pygame.Rect(REFERENCE_WIDTH - 150, 15, 130, 42)
        pygame.draw.rect(surf, (234, 179, 8), whistle_btn, border_radius=12)
        w_txt = typography.render(t("btn.whistle", "🚂 Fischia!"), FontRole.CONTROL, 18, (20, 20, 30))
        surf.blit(w_txt, (whistle_btn.centerx - w_txt.get_width() // 2, whistle_btn.centery - w_txt.get_height() // 2))

        stat_txt = f"Stazione {station_number}/{total_stations}  ★ {total_stars}" if active_locale == "it" else f"Station {station_number}/{total_stations}  ★ {total_stars}"
        stat_surf = typography.render(stat_txt, FontRole.TITLE, 20, (15, 23, 42))
        surf.blit(stat_surf, (80, 25))

        # 9. Victory Modal
        if is_victory:
            overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 15, 30, 200))
            surf.blit(overlay, (0, 0))

            card = pygame.Rect(REFERENCE_WIDTH // 2 - 220, REFERENCE_HEIGHT // 2 - 140, 440, 280)
            pygame.draw.rect(surf, (30, 41, 59), card, border_radius=20)
            pygame.draw.rect(surf, (254, 202, 87), card, width=3, border_radius=20)

            v_title = typography.render(t("victory.title", "Evviva! Treno al capolinea! 🚂🌟"), FontRole.DISPLAY, 22, (254, 202, 87))
            surf.blit(v_title, (card.centerx - v_title.get_width() // 2, card.top + 30))

            v_sub = typography.render(t("victory.subtitle", "Bravissima! Viaggio completato!"), FontRole.BODY, 18, (241, 245, 249))
            surf.blit(v_sub, (card.centerx - v_sub.get_width() // 2, card.top + 75))

            for i in range(3):
                star_x = card.centerx - 50 + i * 50
                star_y = card.top + 130
                pygame.draw.circle(surf, (254, 202, 87), (star_x, star_y), 18)

            again_btn = pygame.Rect(card.centerx - 110, card.bottom - 65, 220, 46)
            pygame.draw.rect(surf, (34, 197, 94), again_btn, border_radius=14)
            again_lbl = typography.render(t("btn.play_again", "🎉 Gioca Ancora!"), FontRole.CONTROL, 20, (255, 255, 255))
            surf.blit(again_lbl, (again_btn.centerx - again_lbl.get_width() // 2, again_btn.centery - again_lbl.get_height() // 2))

        # Present Canvas
        canvas.present(clear=theme.background)

        # Pointer cursor
        if pygame.mouse.get_focused():
            mpos = pygame.mouse.get_pos()
            pygame.draw.circle(screen, (254, 202, 87), mpos, metrics.px(10))
            pygame.draw.circle(screen, (255, 255, 255), mpos, metrics.px(5))

        pygame.display.flip()

        if not ready_published:
            mark_activity_ready()
            ready_published = True

        clock.tick(30)

    if storage is not None:
        try:
            storage.kv_set(STORAGE_KEY, {
                "total_stars": total_stars,
                "timestamp": time.time(),
            })
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
