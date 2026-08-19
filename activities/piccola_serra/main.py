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
STORAGE_KEY = "piccola_serra.progress.v1"

PLANTS = [
    {
        "id": "sunflower",
        "name_it": "Girasole 🌻",
        "name_en": "Sunflower 🌻",
        "flower_color": (254, 240, 138),
        "center_color": (120, 53, 15),
        "petal_color": (234, 179, 8),
    },
    {
        "id": "strawberry",
        "name_it": "Fragola 🍓",
        "name_en": "Strawberry 🍓",
        "flower_color": (239, 68, 68),
        "center_color": (254, 202, 87),
        "petal_color": (244, 63, 94),
    },
    {
        "id": "tulip",
        "name_it": "Tulipano 🌷",
        "name_en": "Tulip 🌷",
        "flower_color": (236, 72, 153),
        "center_color": (244, 114, 182),
        "petal_color": (219, 39, 119),
    },
    {
        "id": "carrot",
        "name_it": "Carota 🥕",
        "name_en": "Carrot 🥕",
        "flower_color": (249, 115, 22),
        "center_color": (34, 197, 94),
        "petal_color": (234, 88, 12),
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


class GreenhouseAudio:
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
    sounds = GreenhouseAudio()

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

    # Tools: 0 = Seed, 1 = Water, 2 = Sun, 3 = Harvest
    active_tool = 0
    selected_plant_type = 0
    harvest_count = 0
    target_harvest = 6

    # 4 Pots on wooden table
    pots = [
        {"plant": None, "stage": 0, "growth": 0.0, "water_level": 0.0},
        {"plant": None, "stage": 0, "growth": 0.0, "water_level": 0.0},
        {"plant": None, "stage": 0, "growth": 0.0, "water_level": 0.0},
        {"plant": None, "stage": 0, "growth": 0.0, "water_level": 0.0},
    ]

    pot_rects = [
        pygame.Rect(130, 280, 160, 160),
        pygame.Rect(330, 280, 160, 160),
        pygame.Rect(530, 280, 160, 160),
        pygame.Rect(730, 280, 160, 160),
    ]

    particles: list[dict[str, Any]] = []
    is_victory = False

    def reset_greenhouse() -> None:
        nonlocal harvest_count, is_victory
        harvest_count = 0
        is_victory = False
        for p in pots:
            p["plant"] = None
            p["stage"] = 0
            p["growth"] = 0.0
            p["water_level"] = 0.0
        particles.clear()

    running = True
    ready_published = False

    while running and not activity_stop_requested():
        t_now = time.time()

        # Update pot growth
        for idx, pot in enumerate(pots):
            if pot["stage"] in (1, 2, 3):
                # Needs water & sun to grow
                speed = 0.005 + (0.015 if pot["water_level"] > 0 else 0.0)
                pot["growth"] += speed
                if pot["water_level"] > 0:
                    pot["water_level"] = max(0.0, pot["water_level"] - 0.003)

                if pot["growth"] >= 1.0:
                    pot["growth"] = 0.0
                    pot["stage"] += 1
                    if pot["stage"] == 4:
                        sounds.play("bloom")
                        try:
                            emit_activity_event("greenhouse.flower_bloomed", {"plant": pot["plant"]["id"]})
                        except Exception:
                            pass
                        # Sparkle burst
                        cx, cy = pot_rects[idx].centerx, pot_rects[idx].top + 30
                        for _ in range(16):
                            ang = random.uniform(0, 6.28)
                            spd = random.uniform(2.0, 4.5)
                            particles.append({
                                "x": cx,
                                "y": cy,
                                "vx": math.cos(ang) * spd,
                                "vy": math.sin(ang) * spd,
                                "color": pot["plant"]["flower_color"],
                                "size": random.uniform(4.0, 7.0),
                                "life": 1.0,
                                "decay": 0.03,
                            })
                    else:
                        sounds.play("sprout")

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN) and is_victory:
                    reset_greenhouse()

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
                        reset_greenhouse()
                        continue

                # Tool selection buttons (Bottom toolbar)
                tool_y = REFERENCE_HEIGHT - 85
                # 0: Seed button
                if pygame.Rect(120, tool_y, 180, 72).collidepoint(mx, my):
                    if active_tool == 0:
                        selected_plant_type = (selected_plant_type + 1) % len(PLANTS)
                    active_tool = 0
                    continue

                # 1: Water button
                if pygame.Rect(320, tool_y, 180, 72).collidepoint(mx, my):
                    active_tool = 1
                    continue

                # 2: Sun button
                if pygame.Rect(520, tool_y, 180, 72).collidepoint(mx, my):
                    active_tool = 2
                    continue

                # 3: Harvest button
                if pygame.Rect(720, tool_y, 180, 72).collidepoint(mx, my):
                    active_tool = 3
                    continue

                # Pot Interactions
                if not is_victory:
                    for idx, r_pot in enumerate(pot_rects):
                        if r_pot.collidepoint(mx, my):
                            pot = pots[idx]
                            if active_tool == 0:
                                # Plant seed
                                if pot["stage"] == 0:
                                    pot["plant"] = PLANTS[selected_plant_type]
                                    pot["stage"] = 1
                                    pot["growth"] = 0.0
                                    pot["water_level"] = 0.5
                                    sounds.play("sprout")
                                    try:
                                        emit_activity_event("greenhouse.seed_planted", {"plant": pot["plant"]["id"]})
                                    except Exception:
                                        pass
                            elif active_tool == 1:
                                # Water plant
                                if pot["stage"] >= 1:
                                    pot["water_level"] = 1.0
                                    sounds.play("water")
                                    # Rain drops
                                    for _ in range(12):
                                        particles.append({
                                            "x": r_pot.centerx + random.uniform(-40, 40),
                                            "y": r_pot.top + random.uniform(10, 40),
                                            "vx": random.uniform(-0.5, 0.5),
                                            "vy": random.uniform(2.0, 4.0),
                                            "color": (56, 189, 248),
                                            "size": random.uniform(3.0, 5.0),
                                            "life": 1.0,
                                            "decay": 0.05,
                                        })
                            elif active_tool == 2:
                                # Sun lamp
                                if pot["stage"] >= 1:
                                    pot["growth"] += 0.35
                                    sounds.play("sprout")
                                    # Sun rays
                                    for _ in range(10):
                                        particles.append({
                                            "x": r_pot.centerx + random.uniform(-30, 30),
                                            "y": r_pot.top + random.uniform(-10, 20),
                                            "vx": random.uniform(-1.0, 1.0),
                                            "vy": random.uniform(-1.0, 1.0),
                                            "color": (254, 240, 138),
                                            "size": random.uniform(4.0, 8.0),
                                            "life": 1.0,
                                            "decay": 0.04,
                                        })
                            elif active_tool == 3:
                                # Harvest flower/produce
                                if pot["stage"] == 4:
                                    pot["stage"] = 0
                                    pot["plant"] = None
                                    harvest_count += 1
                                    sounds.play("harvest")
                                    # Harvest burst
                                    for _ in range(16):
                                        particles.append({
                                            "x": r_pot.centerx,
                                            "y": r_pot.top + 30,
                                            "vx": random.uniform(-2.5, 2.5),
                                            "vy": random.uniform(-3.5, -1.0),
                                            "color": (254, 202, 87),
                                            "size": random.uniform(4.0, 7.0),
                                            "life": 1.0,
                                            "decay": 0.03,
                                        })
                                    if harvest_count >= target_harvest:
                                        is_victory = True
                                        sounds.play("win")
                                        try:
                                            emit_activity_event("greenhouse.harvest_completed", {"harvest": harvest_count})
                                        except Exception:
                                            pass
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

        # 1. Greenhouse Glass & Garden Background
        surf.fill((224, 242, 254))  # Pale sky glass

        # Distant green hills through glass panes
        pygame.draw.circle(surf, (187, 247, 208), (200, 360), 240)
        pygame.draw.circle(surf, (134, 239, 172), (800, 380), 280)

        # Glass pane grid lines
        for gx in range(0, REFERENCE_WIDTH, 200):
            pygame.draw.line(surf, (255, 255, 255), (gx, 0), (gx, 340), 4)
        pygame.draw.line(surf, (255, 255, 255), (0, 160), (REFERENCE_WIDTH, 160), 4)

        # Wooden Greenhouse Table
        pygame.draw.rect(surf, (180, 83, 9), (40, 330, REFERENCE_WIDTH - 80, 160), border_radius=12)
        pygame.draw.rect(surf, (146, 64, 14), (40, 330, REFERENCE_WIDTH - 80, 20), border_radius=6)
        # Floor
        pygame.draw.rect(surf, (254, 243, 199), (0, 480, REFERENCE_WIDTH, 120))

        # 2. Draw Terracotta Pots and Growing Plants
        for idx, pot in enumerate(pots):
            r_pot = pot_rects[idx]
            px = r_pot.centerx
            py = r_pot.bottom - 40

            # Pot Shape (Terracotta)
            pygame.draw.polygon(surf, (194, 65, 12), [
                (px - 45, py), (px + 45, py),
                (px + 36, py + 65), (px - 36, py + 65)
            ])
            pygame.draw.rect(surf, (234, 88, 12), (px - 50, py - 10, 100, 16), border_radius=4)
            # Soil inside rim
            pygame.draw.ellipse(surf, (69, 26, 3), (px - 44, py - 8, 88, 12))

            # Water level highlight
            if pot["water_level"] > 0:
                pygame.draw.ellipse(surf, (56, 189, 248), (px - 40, py - 6, 80, 8))

            # Plant Growth Visualization
            stage = pot["stage"]
            plant = pot["plant"]

            if stage == 1:
                # Tiny seed in soil
                pygame.draw.circle(surf, (254, 240, 138), (px, py - 2), 4)
            elif stage == 2:
                # Small green sprout
                pygame.draw.line(surf, (34, 197, 94), (px, py - 2), (px, py - 25), 4)
                pygame.draw.ellipse(surf, (74, 222, 128), (px - 14, py - 30, 14, 8))
                pygame.draw.ellipse(surf, (74, 222, 128), (px, py - 30, 14, 8))
            elif stage == 3:
                # Growing stem & bud
                pygame.draw.line(surf, (34, 197, 94), (px, py - 2), (px, py - 55), 6)
                pygame.draw.ellipse(surf, (74, 222, 128), (px - 20, py - 40, 20, 10))
                pygame.draw.ellipse(surf, (74, 222, 128), (px, py - 48, 20, 10))
                # Bud
                pygame.draw.circle(surf, plant["petal_color"], (px, py - 60), 12)
            elif stage == 4:
                # FULL BLOOM / FRUIT
                pygame.draw.line(surf, (34, 197, 94), (px, py - 2), (px, py - 75), 7)
                pygame.draw.ellipse(surf, (74, 222, 128), (px - 26, py - 50, 26, 12))
                pygame.draw.ellipse(surf, (74, 222, 128), (px, py - 60, 26, 12))

                # Flower petals
                fx = px
                fy = py - 85
                petal_r = 16
                for ang in range(0, 360, 45):
                    rad = math.radians(ang)
                    ptx = fx + math.cos(rad) * 18
                    pty = fy + math.sin(rad) * 18
                    pygame.draw.circle(surf, plant["petal_color"], (int(ptx), int(pty)), petal_r)

                # Center core
                pygame.draw.circle(surf, plant["center_color"], (fx, fy), 18)
                pygame.draw.circle(surf, (255, 255, 255), (fx - 4, fy - 4), 4)

        # 3. Draw Particles
        for p in particles:
            cur_sz = max(2.0, p["size"] * max(0.0, min(1.0, p["life"])))
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), int(cur_sz))

        # 4. Top HUD (Harvest Goal Pill)
        star_pill = pygame.Rect(80, 16, 140, 56)
        pygame.draw.rect(surf, (255, 255, 255), star_pill, border_radius=18)
        pygame.draw.rect(surf, (234, 179, 8), star_pill, width=3, border_radius=18)
        pygame.draw.circle(surf, (234, 179, 8), (star_pill.left + 30, star_pill.centery), 16)
        s_txt = typography.render(f"{harvest_count}/{target_harvest}", FontRole.DISPLAY, 28, (180, 83, 9))
        surf.blit(s_txt, (star_pill.left + 54, star_pill.centery - s_txt.get_height() // 2))

        # 7. Bottom Toolbar (Giant Chunky 180x72px Buttons with Icon + Label)
        tool_y = REFERENCE_HEIGHT - 85
        tools_info = [
            (100, 0, "SEME", (22, 101, 52)),
            (310, 1, "ACQUA", (2, 132, 199)),
            (520, 2, "SOLE", (202, 138, 4)),
            (730, 3, "RACCOLTA", (194, 65, 12)),
        ]

        for tx, t_idx, lbl, col in tools_info:
            b_rect = pygame.Rect(tx, tool_y, 180, 72)
            is_sel = active_tool == t_idx
            bg_col = col if is_sel else (255, 255, 255)
            border_w = 5 if is_sel else 2
            pygame.draw.rect(surf, bg_col, b_rect, border_radius=20)
            pygame.draw.rect(surf, col, b_rect, width=border_w, border_radius=20)
            cx = b_rect.centerx
            cy = b_rect.top + 28

            if t_idx == 0:
                # 0: Giant Seed Sprout Icon
                seed_col = (255, 255, 255) if is_sel else (22, 101, 52)
                leaf_col = (220, 252, 231) if is_sel else (34, 197, 94)
                pygame.draw.circle(surf, seed_col, (cx, cy + 6), 8)
                pygame.draw.line(surf, leaf_col, (cx, cy + 6), (cx, cy - 8), 3)
                pygame.draw.ellipse(surf, leaf_col, pygame.Rect(cx - 14, cy - 14, 14, 8))
                pygame.draw.ellipse(surf, leaf_col, pygame.Rect(cx, cy - 14, 14, 8))

            elif t_idx == 1:
                # 1: Giant Watering Can & Droplets Icon
                can_col = (255, 255, 255) if is_sel else (2, 132, 199)
                drop_col = (224, 242, 254) if is_sel else (56, 189, 248)
                pygame.draw.rect(surf, can_col, pygame.Rect(cx - 14, cy - 8, 22, 18), border_radius=4)
                pygame.draw.line(surf, can_col, (cx + 8, cy - 3), (cx + 20, cy - 11), 4)
                pygame.draw.arc(surf, can_col, pygame.Rect(cx - 24, cy - 10, 14, 16), 1.5, 4.7, 3)
                pygame.draw.circle(surf, drop_col, (cx + 22, cy - 1), 3)
                pygame.draw.circle(surf, drop_col, (cx + 24, cy + 7), 4)

            elif t_idx == 2:
                # 2: Giant Radiant Sun Icon
                sun_col = (255, 255, 255) if is_sel else (234, 179, 8)
                ray_col = (254, 240, 138) if is_sel else (202, 138, 4)
                pygame.draw.circle(surf, sun_col, (cx, cy), 13)
                for ang in (0, 45, 90, 135, 180, 225, 270, 315):
                    rad = math.radians(ang)
                    pygame.draw.line(surf, ray_col, (cx + int(math.cos(rad)*14), cy + int(math.sin(rad)*14)), (cx + int(math.cos(rad)*19), cy + int(math.sin(rad)*19)), 2)

            elif t_idx == 3:
                # 3: Giant Harvest Basket
                bask_col = (255, 255, 255) if is_sel else (194, 65, 12)
                pygame.draw.polygon(surf, bask_col, [
                    (cx - 16, cy - 2), (cx + 16, cy - 2),
                    (cx + 11, cy + 14), (cx - 11, cy + 14)
                ])
                pygame.draw.arc(surf, bask_col, pygame.Rect(cx - 13, cy - 16, 26, 20), 0, 3.14, 3)
                pygame.draw.circle(surf, (239, 68, 68), (cx - 4, cy - 5), 5)
                pygame.draw.circle(surf, (234, 179, 8), (cx + 5, cy - 5), 5)

            # Supporting label underneath
            lbl_surf = typography.render(lbl, FontRole.DISPLAY, 16, (255, 255, 255) if is_sel else col)
            surf.blit(lbl_surf, (cx - lbl_surf.get_width() // 2, b_rect.bottom - 22))

        # 6. Victory Modal
        if is_victory:
            overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 15, 30, 200))
            surf.blit(overlay, (0, 0))

            card = pygame.Rect(REFERENCE_WIDTH // 2 - 220, REFERENCE_HEIGHT // 2 - 140, 440, 280)
            pygame.draw.rect(surf, (30, 41, 59), card, border_radius=20)
            pygame.draw.rect(surf, (254, 202, 87), card, width=3, border_radius=20)

            v_title = typography.render("SPLENDIDO RACCOLTO!", FontRole.DISPLAY, 24, (254, 202, 87))
            surf.blit(v_title, (card.centerx - v_title.get_width() // 2, card.top + 30))

            v_sub = typography.render("La serra e' un vero paradiso!", FontRole.BODY, 18, (241, 245, 249))
            surf.blit(v_sub, (card.centerx - v_sub.get_width() // 2, card.top + 75))

            for i in range(3):
                star_x = card.centerx - 50 + i * 50
                star_y = card.top + 130
                pygame.draw.circle(surf, (254, 202, 87), (star_x, star_y), 18)

            again_btn = pygame.Rect(card.centerx - 110, card.bottom - 65, 220, 46)
            pygame.draw.rect(surf, (34, 197, 94), again_btn, border_radius=14)
            again_lbl = typography.render("COLTIVA ANCORA", FontRole.CONTROL, 20, (255, 255, 255))
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
                "harvest_count": harvest_count,
                "timestamp": time.time(),
            })
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
