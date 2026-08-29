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
from greia_platform.pygame_completion import CompletionContent, PygameCompletionScreen
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

    completion = PygameCompletionScreen(
        typography,
        width=REFERENCE_WIDTH,
        height=REFERENCE_HEIGHT,
        primary_rect=pygame.Rect(392, 380, 240, 52),
    )
    completion_content = CompletionContent(
        title=t("victory.title", "Che magnifico raccolto! 🌻🍓🥕"),
        body_lines=(t("victory.subtitle", "La tua serra è un vero paradiso!"),),
        primary_label=t("btn.play_again", "🎉 Coltiva Ancora!"),
        achievement_count=3,
    )

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
        pygame.Rect(120, 160, 180, 280),
        pygame.Rect(320, 160, 180, 280),
        pygame.Rect(520, 160, 180, 280),
        pygame.Rect(720, 160, 180, 280),
    ]

    particles: list[dict[str, Any]] = []
    is_victory = False
    completion_presented = False

    def reset_greenhouse() -> None:
        nonlocal harvest_count, is_victory, completion_presented
        harvest_count = 0
        is_victory = False
        completion.clear()
        completion_presented = False
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

        # Active-world particles stop advancing once terminal state is entered.
        if not is_victory:
            surviving = []
            for p in particles:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["life"] -= p["decay"]
                if p["life"] > 0:
                    surviving.append(p)
            particles = surviving

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
                completion_presented = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    continue
                if is_victory:
                    if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        reset_greenhouse()
                    # Terminal input must never fall through into active controls.
                    continue

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if not _is_safe_point(screen, event.pos):
                    continue
                logical = canvas.pointer(event.pos)
                if logical is None:
                    continue
                mx, my = logical

                if is_victory:
                    if completion.primary_contains((int(mx), int(my))):
                        reset_greenhouse()
                    # Terminal input must never fall through into active controls.
                    continue

                # Tool selection buttons (Bottom toolbar)
                tool_y = REFERENCE_HEIGHT - 85
                # 0: Seed button
                if pygame.Rect(100, tool_y, 180, 72).collidepoint(mx, my):
                    if active_tool == 0:
                        selected_plant_type = (selected_plant_type + 1) % len(PLANTS)
                    active_tool = 0
                    continue

                # 1: Water button
                if pygame.Rect(310, tool_y, 180, 72).collidepoint(mx, my):
                    active_tool = 1
                    continue

                # 2: Sun button
                if pygame.Rect(520, tool_y, 180, 72).collidepoint(mx, my):
                    active_tool = 2
                    continue

                # 3: Harvest button
                if pygame.Rect(730, tool_y, 180, 72).collidepoint(mx, my):
                    active_tool = 3
                    continue

                # Pot Interactions (Explicit Multi-Step Player Care Required)
                if not is_victory:
                    for idx, r_pot in enumerate(pot_rects):
                        if r_pot.collidepoint(mx, my):
                            pot = pots[idx]
                            stage = pot["stage"]
                            
                            # Determine what this pot needs
                            # Stage 0: Needs Seed (0)
                            # Stage 1: Needs Water (1)
                            # Stage 2: Needs Sun (2)
                            # Stage 3: Needs Water (1)
                            # Stage 4: Needs Harvest (3)
                            needed_tool = 0 if stage == 0 else (1 if stage == 1 else (2 if stage == 2 else (1 if stage == 3 else 3)))

                            if active_tool == needed_tool:
                                if stage == 0:
                                    # 1. Plant Seed
                                    pot["plant"] = PLANTS[selected_plant_type]
                                    pot["stage"] = 1
                                    sounds.play("sprout")
                                    for _ in range(8):
                                        particles.append({
                                            "x": r_pot.centerx + random.uniform(-20, 20),
                                            "y": r_pot.bottom - 40,
                                            "vx": random.uniform(-1, 1),
                                            "vy": random.uniform(-2, -0.5),
                                            "color": (120, 53, 15),
                                            "size": random.uniform(3, 6),
                                            "life": 1.0,
                                            "decay": 0.04,
                                        })
                                    try:
                                        emit_activity_event("greenhouse.seed_planted", {"plant": pot["plant"]["id"]})
                                    except Exception:
                                        pass

                                elif stage == 1:
                                    # 2. Water Seed -> Sprouts!
                                    pot["stage"] = 2
                                    sounds.play("water")
                                    for _ in range(14):
                                        particles.append({
                                            "x": r_pot.centerx + random.uniform(-30, 30),
                                            "y": r_pot.top + random.uniform(20, 50),
                                            "vx": random.uniform(-0.5, 0.5),
                                            "vy": random.uniform(2.0, 4.5),
                                            "color": (56, 189, 248),
                                            "size": random.uniform(3.0, 5.0),
                                            "life": 1.0,
                                            "decay": 0.04,
                                        })

                                elif stage == 2:
                                    # 3. Sun on Sprout -> Grows tall bud!
                                    pot["stage"] = 3
                                    sounds.play("sprout")
                                    for _ in range(12):
                                        particles.append({
                                            "x": r_pot.centerx + random.uniform(-30, 30),
                                            "y": r_pot.top + random.uniform(0, 30),
                                            "vx": random.uniform(-1.5, 1.5),
                                            "vy": random.uniform(-1.5, 1.5),
                                            "color": (254, 240, 138),
                                            "size": random.uniform(4.0, 8.0),
                                            "life": 1.0,
                                            "decay": 0.04,
                                        })

                                elif stage == 3:
                                    # 4. Water Bud -> FULL BLOOM!
                                    pot["stage"] = 4
                                    sounds.play("bloom")
                                    for _ in range(18):
                                        ang = random.uniform(0, 6.28)
                                        spd = random.uniform(2.0, 4.5)
                                        particles.append({
                                            "x": r_pot.centerx,
                                            "y": r_pot.top + 20,
                                            "vx": math.cos(ang) * spd,
                                            "vy": math.sin(ang) * spd,
                                            "color": pot["plant"]["flower_color"],
                                            "size": random.uniform(4.0, 7.0),
                                            "life": 1.0,
                                            "decay": 0.03,
                                        })
                                    try:
                                        emit_activity_event("greenhouse.flower_bloomed", {"plant": pot["plant"]["id"]})
                                    except Exception:
                                        pass

                                elif stage == 4:
                                    # 5. Harvest Bloomed Flower / Fruit!
                                    pot["stage"] = 0
                                    pot["plant"] = None
                                    harvest_count += 1
                                    sounds.play("harvest")
                                    for _ in range(18):
                                        particles.append({
                                            "x": r_pot.centerx,
                                            "y": r_pot.top + 20,
                                            "vx": random.uniform(-2.5, 2.5),
                                            "vy": random.uniform(-3.5, -1.0),
                                            "color": (254, 202, 87),
                                            "size": random.uniform(4.0, 8.0),
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

        if is_victory:
            if not completion_presented:
                completion.prepare(completion_content)
                completion.draw(canvas.surface)
                canvas.present(clear=theme.background)
                pygame.display.flip()
                completion_presented = True
            clock.tick(25)
            continue

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

            # Floating Thought Bubble Showing Required Care Tool (Positioned high in clear sky)
            if not is_victory:
                needed_tool = 0 if stage == 0 else (1 if stage == 1 else (2 if stage == 2 else (1 if stage == 3 else 3)))
                is_matching = (active_tool == needed_tool)

                # Float high at y=130 in clear sky, well above mature flowers (which end around y=270)
                bob = int(math.sin(t_now * 4.0 + idx) * 3.0)
                bx = px
                by = 130 + bob

                dark = (30, 41, 59)
                white = (255, 255, 255)

                # Trailing thought dots connecting plant to bubble
                pygame.draw.circle(surf, white, (bx, by + 45), 5)
                pygame.draw.circle(surf, dark, (bx, by + 45), 5, 2)
                pygame.draw.circle(surf, white, (bx, by + 30), 7)
                pygame.draw.circle(surf, dark, (bx, by + 30), 7, 2)

                # Thought Bubble Cloud Card
                bubble_border = (34, 197, 94) if is_matching else (203, 213, 225)
                border_w = 4 if is_matching else 2
                
                # Cloud puffs
                for ox, oy, rad in [(-16, 0, 18), (16, 0, 18), (0, -10, 20), (0, 10, 18)]:
                    pygame.draw.circle(surf, white, (bx + ox, by + oy), rad)
                    pygame.draw.circle(surf, bubble_border, (bx + ox, by + oy), rad, border_w)
                for ox, oy, rad in [(-16, 0, 16), (16, 0, 16), (0, -10, 18), (0, 10, 16)]:
                    pygame.draw.circle(surf, white, (bx + ox, by + oy), rad)

                # Mini Tool Icon in Bubble (High-contrast, crisp details)
                if needed_tool == 0:
                    # Seed Grain + Sprout Leaf
                    pygame.draw.circle(surf, (180, 83, 9), (bx, by + 5), 7)
                    pygame.draw.circle(surf, dark, (bx, by + 5), 7, 2)
                    pygame.draw.ellipse(surf, (34, 197, 94), pygame.Rect(bx - 10, by - 12, 10, 7))
                    pygame.draw.ellipse(surf, (34, 197, 94), pygame.Rect(bx, by - 12, 10, 7))
                    pygame.draw.ellipse(surf, dark, pygame.Rect(bx - 10, by - 12, 10, 7), 1)
                    pygame.draw.ellipse(surf, dark, pygame.Rect(bx, by - 12, 10, 7), 1)
                elif needed_tool == 1:
                    # Blue Water Droplet with Specular Highlight
                    pygame.draw.circle(surf, (14, 165, 233), (bx, by + 4), 9)
                    pygame.draw.polygon(surf, (14, 165, 233), [(bx - 8, by + 2), (bx + 8, by + 2), (bx, by - 11)])
                    pygame.draw.circle(surf, dark, (bx, by + 4), 9, 2)
                    pygame.draw.circle(surf, (255, 255, 255), (bx - 3, by + 2), 3)
                elif needed_tool == 2:
                    # Radiant Glowing Sun
                    pygame.draw.circle(surf, (234, 179, 8), (bx, by), 10)
                    pygame.draw.circle(surf, dark, (bx, by), 10, 2)
                    for sang in (0, 45, 90, 135, 180, 225, 270, 315):
                        srad = math.radians(sang)
                        pygame.draw.line(surf, (217, 119, 6), (bx + int(math.cos(srad)*11), by + int(math.sin(srad)*11)), (bx + int(math.cos(srad)*16), by + int(math.sin(srad)*16)), 3)
                elif needed_tool == 3:
                    # Harvest Basket / Ripe Golden Sparkle Fruit
                    pygame.draw.circle(surf, (239, 68, 68), (bx, by + 3), 10)
                    pygame.draw.circle(surf, dark, (bx, by + 3), 10, 2)
                    pygame.draw.circle(surf, (255, 255, 255), (bx - 3, by), 3)
                    pygame.draw.ellipse(surf, (34, 197, 94), pygame.Rect(bx - 3, by - 11, 7, 5))
                    pygame.draw.ellipse(surf, dark, pygame.Rect(bx - 3, by - 11, 7, 5), 1)

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

        # Present Canvas
        canvas.present(clear=theme.background)

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
