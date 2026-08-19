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
STORAGE_KEY = "nascondino_bosco.progress.v1"

SEASONS = [
    {
        "id": "spring",
        "name_it": "🌱 Primavera",
        "name_en": "🌱 Spring",
        "sky": (186, 230, 253),
        "ground": (74, 222, 128),
        "foliage": (34, 197, 94),
        "trunk": (120, 80, 50),
    },
    {
        "id": "autumn",
        "name_it": "🍂 Autunno",
        "name_en": "🍂 Autumn",
        "sky": (254, 215, 170),
        "ground": (217, 119, 6),
        "foliage": (234, 88, 12),
        "trunk": (90, 55, 35),
    },
    {
        "id": "night",
        "name_it": "🌙 Notte Magica",
        "name_en": "🌙 Magic Night",
        "sky": (15, 23, 42),
        "ground": (22, 101, 52),
        "foliage": (20, 83, 45),
        "trunk": (60, 40, 30),
    },
]

ANIMALS = [
    {"id": "fox", "name_it": "Volpina 🦊", "name_en": "Fox 🦊", "color": (249, 115, 22)},
    {"id": "bunny", "name_it": "Coniglietto 🐰", "name_en": "Bunny 🐰", "color": (248, 250, 252)},
    {"id": "owl", "name_it": "Gufo 🦉", "name_en": "Owl 🦉", "color": (161, 98, 7)},
    {"id": "hedgehog", "name_it": "Riccio 🦔", "name_en": "Hedgehog 🦔", "color": (120, 53, 15)},
    {"id": "squirrel", "name_it": "Scoiattolo 🐿️", "name_en": "Squirrel 🐿️", "color": (217, 119, 6)},
    {"id": "frog", "name_it": "Ranocchia 🐸", "name_en": "Frog 🐸", "color": (34, 197, 94)},
]

SPOTS = [
    {"name": "hollow_tree", "x": 160, "y": 280, "w": 130, "h": 140, "kind": "tree"},
    {"name": "berry_bush", "x": 110, "y": 460, "w": 140, "h": 90, "kind": "bush"},
    {"name": "flower_bush", "x": 380, "y": 470, "w": 150, "h": 90, "kind": "bush"},
    {"name": "rock_cave", "x": 620, "y": 460, "w": 140, "h": 100, "kind": "rock"},
    {"name": "tall_pine", "x": 860, "y": 260, "w": 120, "h": 150, "kind": "tree"},
    {"name": "pond_reeds", "x": 880, "y": 470, "w": 130, "h": 90, "kind": "reeds"},
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


class WoodlandAudio:
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
        # Rustle sound
        rustle_samples = []
        for i in range(int(rate * 0.08)):
            t = i / rate
            env = math.exp(-15.0 * t)
            val = random.uniform(-1.0, 1.0)
            rustle_samples.append(int(32767.0 * 0.20 * env * val))
        self._sounds["rustle"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(rustle_samples)))

        # Found pop / chirp
        found_samples = []
        for i in range(int(rate * 0.22)):
            t = i / rate
            env = math.exp(-6.0 * t)
            val = math.sin(2.0 * math.pi * (650.0 + 300.0 * (t / 0.22)) * t)
            found_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["found"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(found_samples)))

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
    sounds = WoodlandAudio()

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

    season_idx = 0
    hiding_spots: list[dict[str, Any]] = []
    found_count = 0
    total_animals = 4
    particles: list[dict[str, Any]] = []
    is_victory = False

    def start_new_round() -> None:
        nonlocal hiding_spots, found_count, total_animals, particles, is_victory
        found_count = 0
        total_animals = 4
        is_victory = False
        particles.clear()

        # Pick 4 random spots out of 6
        selected_spot_defs = random.sample(SPOTS, total_animals)
        selected_animals = random.sample(ANIMALS, total_animals)

        hiding_spots = []
        for s_def, animal in zip(selected_spot_defs, selected_animals):
            hiding_spots.append({
                "def": s_def,
                "animal": animal,
                "is_found": False,
                "pop_anim": 0.0,
                "rustle_t": random.random() * 6.28,
            })

    start_new_round()

    running = True
    ready_published = False

    while running and not activity_stop_requested():
        t_now = time.time()
        season = SEASONS[season_idx]

        # Update animations
        for hs in hiding_spots:
            if hs["is_found"]:
                if hs["pop_anim"] < 1.0:
                    hs["pop_anim"] = min(1.0, hs["pop_anim"] + 0.10)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN) and is_victory:
                    start_new_round()
                elif event.key == pygame.K_n:
                    start_new_round()

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
                        start_new_round()
                        continue

                # Season switch button
                season_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 65, REFERENCE_HEIGHT - 50, 130, 40)
                if season_btn.collidepoint(mx, my):
                    season_idx = (season_idx + 1) % len(SEASONS)
                    continue

                # New round button
                new_btn = pygame.Rect(REFERENCE_WIDTH - 150, 15, 130, 42)
                if new_btn.collidepoint(mx, my):
                    start_new_round()
                    continue

                # Check spot clicks
                if not is_victory:
                    for hs in hiding_spots:
                        s_def = hs["def"]
                        spot_rect = pygame.Rect(s_def["x"], s_def["y"], s_def["w"], s_def["h"])
                        if spot_rect.collidepoint(mx, my):
                            if not hs["is_found"]:
                                hs["is_found"] = True
                                found_count += 1
                                sounds.play("found")
                                try:
                                    emit_activity_event("woodland.animal_found", {"animal": hs["animal"]["id"]})
                                except Exception:
                                    pass
                                # Burst sparkles
                                for _ in range(16):
                                    ang = random.uniform(0, 6.28)
                                    spd = random.uniform(2.0, 5.0)
                                    particles.append({
                                        "x": spot_rect.centerx,
                                        "y": spot_rect.centery,
                                        "vx": math.cos(ang) * spd,
                                        "vy": math.sin(ang) * spd,
                                        "color": hs["animal"]["color"],
                                        "size": random.uniform(4.0, 8.0),
                                        "life": 1.0,
                                        "decay": 0.03,
                                    })

                                if found_count >= total_animals:
                                    is_victory = True
                                    sounds.play("win")
                                    try:
                                        emit_activity_event("woodland.round_completed", {"found": found_count})
                                    except Exception:
                                        pass
                            else:
                                sounds.play("rustle")
                            break

        # Update particles
        surviving = []
        for p in particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= p["decay"]
            if p["life"] > 0:
                surviving.append(p)
        particles = surviving

        # RENDER TO CANVAS
        surf = canvas.surface

        # 1. Sky & Backdrop
        surf.fill(season["sky"])

        # Sun / Moon
        if season["id"] == "night":
            # Moon & Stars
            pygame.draw.circle(surf, (254, 240, 138), (860, 90), 38)
            pygame.draw.circle(surf, season["sky"], (845, 80), 32)
            for star_pos in [(150, 60), (320, 80), (550, 50), (720, 90), (940, 70)]:
                pygame.draw.circle(surf, (255, 255, 255), star_pos, 3)
        else:
            # Sun
            pygame.draw.circle(surf, (254, 240, 138), (860, 90), 45)

        # Distant Woodland Trees
        for dx in range(50, REFERENCE_WIDTH, 140):
            pygame.draw.polygon(surf, season["foliage"], [(dx, 200), (dx - 70, 360), (dx + 70, 360)])

        # Woodland Floor
        pygame.draw.rect(surf, season["ground"], (0, 340, REFERENCE_WIDTH, 260))

        # 2. Draw Hiding Spots & Animals
        for hs in hiding_spots:
            s_def = hs["def"]
            animal = hs["animal"]
            sx = s_def["x"]
            sy = s_def["y"]
            sw = s_def["w"]
            sh = s_def["h"]

            # Animal Sprite (pops up when found or peeks gently)
            peek_y = 0.0
            if not hs["is_found"]:
                # Gentle breathing/twitch peek
                peek_y = math.sin(t_now * 3.0 + hs["rustle_t"]) * 4.0
            else:
                # Full pop up
                peek_y = -35.0 * hs["pop_anim"]

            char_cx = sx + sw // 2
            char_cy = sy + sh // 2 + int(peek_y)
            char_r = 28

            # Shadow under animal
            pygame.draw.ellipse(surf, (20, 30, 20), (char_cx - 24, sy + sh // 2 + 10, 48, 16))
            # Animal body
            pygame.draw.circle(surf, animal["color"], (char_cx, char_cy), char_r)
            # Eyes
            pygame.draw.circle(surf, (20, 20, 30), (char_cx - 9, char_cy - 4), 5)
            pygame.draw.circle(surf, (20, 20, 30), (char_cx + 9, char_cy - 4), 5)
            pygame.draw.circle(surf, (255, 255, 255), (char_cx - 7, char_cy - 6), 2)
            pygame.draw.circle(surf, (255, 255, 255), (char_cx + 11, char_cy - 6), 2)

            # Draw Covering Landscape (Tree / Bush / Rock)
            if s_def["kind"] == "tree":
                # Trunk with hollow hole
                pygame.draw.rect(surf, season["trunk"], (sx + 20, sy - 40, sw - 40, sh + 40), border_radius=12)
                pygame.draw.ellipse(surf, (30, 20, 15), (sx + 35, sy + 20, sw - 70, 55))
            elif s_def["kind"] == "bush":
                # Leafy Bush
                pygame.draw.circle(surf, season["foliage"], (sx + 40, sy + 45), 42)
                pygame.draw.circle(surf, season["foliage"], (sx + sw - 40, sy + 45), 42)
                pygame.draw.circle(surf, season["foliage"], (sx + sw // 2, sy + 30), 48)
                # Flowers / Berries
                pygame.draw.circle(surf, (244, 63, 94), (sx + 35, sy + 30), 6)
                pygame.draw.circle(surf, (254, 240, 138), (sx + sw - 35, sy + 35), 6)
            elif s_def["kind"] == "rock":
                # Mossy Rock Cave
                pygame.draw.ellipse(surf, (100, 116, 139), (sx, sy + 10, sw, sh - 10))
                pygame.draw.ellipse(surf, (30, 41, 59), (sx + 25, sy + 30, sw - 50, sh - 40))
            elif s_def["kind"] == "reeds":
                # Pond Water & Reeds
                pygame.draw.ellipse(surf, (56, 189, 248), (sx - 20, sy + 30, sw + 40, 50))
                for rx in range(sx, sx + sw, 15):
                    pygame.draw.line(surf, (22, 101, 52), (rx, sy + 60), (rx + 5, sy), 5)

            # If found, show animal name badge above it
            if hs["is_found"] and hs["pop_anim"] > 0.6:
                a_name = animal["name_it"] if active_locale == "it" else animal["name_en"]
                b_surf = typography.render(a_name, FontRole.TITLE, 16, (30, 41, 59))
                b_rect = pygame.Rect(char_cx - b_surf.get_width() // 2 - 8, char_cy - 50, b_surf.get_width() + 16, 26)
                pygame.draw.rect(surf, (255, 255, 255), b_rect, border_radius=8)
                pygame.draw.rect(surf, animal["color"], b_rect, width=2, border_radius=8)
                surf.blit(b_surf, (char_cx - b_surf.get_width() // 2, b_rect.centery - b_surf.get_height() // 2))

        # 3. Draw Particles
        for p in particles:
            cur_sz = max(2.0, p["size"] * max(0.0, min(1.0, p["life"])))
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), int(cur_sz))

        # 4. Top HUD
        title_surf = typography.render(t("activity.title", "Nascondino nel Bosco"), FontRole.DISPLAY, 24, (30, 41, 59) if season["id"] != "night" else (255, 255, 255))
        surf.blit(title_surf, (80, 20))

        found_txt = f"Animali Trovati: {found_count}/{total_animals}" if active_locale == "it" else f"Animals Found: {found_count}/{total_animals}"
        found_surf = typography.render(found_txt, FontRole.TITLE, 20, (71, 85, 105) if season["id"] != "night" else (254, 240, 138))
        surf.blit(found_surf, (370, 22))

        # New Round Button
        new_btn = pygame.Rect(REFERENCE_WIDTH - 150, 15, 130, 42)
        pygame.draw.rect(surf, (71, 85, 105), new_btn, border_radius=12)
        new_txt = typography.render(t("btn.new_round", "🔄 Nuovo"), FontRole.CONTROL, 18, (255, 255, 255))
        surf.blit(new_txt, (new_btn.centerx - new_txt.get_width() // 2, new_btn.centery - new_txt.get_height() // 2))

        # 5. Bottom Season Switcher
        season_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 65, REFERENCE_HEIGHT - 50, 130, 40)
        pygame.draw.rect(surf, (51, 65, 85), season_btn, border_radius=10)
        s_name = season["name_it"] if active_locale == "it" else season["name_en"]
        season_lbl = typography.render(s_name, FontRole.BODY, 15, (255, 255, 255))
        surf.blit(season_lbl, (season_btn.centerx - season_lbl.get_width() // 2, season_btn.centery - season_lbl.get_height() // 2))

        # 6. Victory Modal
        if is_victory:
            overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 15, 30, 200))
            surf.blit(overlay, (0, 0))

            card = pygame.Rect(REFERENCE_WIDTH // 2 - 220, REFERENCE_HEIGHT // 2 - 140, 440, 280)
            pygame.draw.rect(surf, (30, 41, 59), card, border_radius=20)
            pygame.draw.rect(surf, (254, 202, 87), card, width=3, border_radius=20)

            v_title = typography.render(t("victory.title", "Li hai trovati tutti! 🌲🐾"), FontRole.DISPLAY, 22, (254, 202, 87))
            surf.blit(v_title, (card.centerx - v_title.get_width() // 2, card.top + 30))

            v_sub = typography.render(t("victory.subtitle", "Tutti gli animaletti sono felici!"), FontRole.BODY, 18, (241, 245, 249))
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
                "season_idx": season_idx,
                "timestamp": time.time(),
            })
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
