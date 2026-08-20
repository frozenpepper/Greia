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
STORAGE_KEY = "costruiamo_ponti.progress.v2"

BLOCKS = [
    {"id": "wood", "color": (180, 83, 9), "border": (146, 64, 14), "type_name": "wood"},
    {"id": "stone", "color": (100, 116, 139), "border": (71, 85, 105), "type_name": "stone"},
    {"id": "shroom", "color": (239, 68, 68), "border": (220, 38, 38), "type_name": "shroom"},
    {"id": "rainbow", "color": (168, 85, 247), "border": (147, 51, 234), "type_name": "rainbow"},
]
BLOCK_TYPES = BLOCKS

LEVELS = [
    {
        "id": "river",
        "sky": (186, 230, 253),
        "gap_water": (56, 189, 248),
        "cliff_color": (34, 197, 94),
        "required": ["wood", "wood", "shroom", "wood"],
    },
    {
        "id": "canyon",
        "sky": (254, 215, 170),
        "gap_water": (217, 119, 6),
        "cliff_color": (120, 53, 15),
        "required": ["stone", "shroom", "stone", "rainbow"],
    },
    {
        "id": "space",
        "sky": (15, 23, 42),
        "gap_water": (30, 27, 75),
        "cliff_color": (59, 130, 246),
        "required": ["rainbow", "shroom", "rainbow", "shroom"],
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


class BridgeAudio:
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
        # Place thud
        thud_samples = []
        for i in range(int(rate * 0.08)):
            t = i / rate
            env = math.exp(-14.0 * t)
            val = math.sin(2.0 * math.pi * 220.0 * t)
            thud_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["place"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(thud_samples)))

        # Boing trampoline bounce
        boing_samples = []
        for i in range(int(rate * 0.22)):
            t = i / rate
            env = math.exp(-4.5 * t)
            freq = 300.0 + 500.0 * (t / 0.22)
            val = math.sin(2.0 * math.pi * freq * t)
            boing_samples.append(int(32767.0 * 0.32 * env * val))
        self._sounds["boing"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(boing_samples)))

        # Win fanfare
        win_samples = []
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


def _draw_block_icon(surface: pygame.Surface, block_id: str, cx: int, cy: int, size: int) -> None:
    """Draws the block icon in its TRUE, IDENTICAL, VIBRANT colors and shape everywhere."""
    r = size // 2
    dark = (30, 41, 59)
    if block_id == "wood":
        # 3D Log Plank with rich woodgrain, end-ring and brass nails
        pygame.draw.rect(surface, (180, 83, 9), (cx - r, cy - r // 2, size, r), border_radius=8)
        pygame.draw.rect(surface, (217, 119, 6), (cx - r + 3, cy - r // 2 + 2, size - 6, r - 4), border_radius=6)
        pygame.draw.ellipse(surface, (245, 158, 11), pygame.Rect(cx + r - r // 3, cy - r // 2, r * 2 // 3, r))
        pygame.draw.circle(surface, (146, 64, 14), (cx + r, cy), max(2, r // 4))
        pygame.draw.rect(surface, dark, (cx - r, cy - r // 2, size, r), width=2, border_radius=8)
        # Golden nails
        pygame.draw.circle(surface, (254, 240, 138), (cx - r + 7, cy), max(2, r // 7))
        pygame.draw.circle(surface, (180, 83, 9), (cx - r + 7, cy), max(2, r // 7), 1)
    elif block_id == "stone":
        # Heavy stone block with 3D bevel and mortar
        pygame.draw.rect(surface, (71, 85, 105), (cx - r, cy - r, size, size), border_radius=10)
        pygame.draw.rect(surface, (148, 163, 184), (cx - r + 3, cy - r + 3, size - 6, size - 6), border_radius=8)
        pygame.draw.rect(surface, (203, 213, 225), (cx - r + 5, cy - r + 5, size - 10, size // 3), border_radius=4)
        pygame.draw.rect(surface, dark, (cx - r, cy - r, size, size), width=2, border_radius=10)
    elif block_id == "shroom":
        # Bouncy mushroom cap with bright red dome and white polka dots
        pygame.draw.rect(surface, (255, 255, 255), (cx - r // 4, cy, r // 2, r), border_radius=4)
        pygame.draw.rect(surface, dark, (cx - r // 4, cy, r // 2, r), width=2, border_radius=4)
        pygame.draw.ellipse(surface, (239, 68, 68), pygame.Rect(cx - r, cy - r, size, r * 5 // 4))
        pygame.draw.ellipse(surface, dark, pygame.Rect(cx - r, cy - r, size, r * 5 // 4), 2)
        pygame.draw.circle(surface, (255, 255, 255), (cx - r // 2, cy - r // 3), max(3, r // 4))
        pygame.draw.circle(surface, (255, 255, 255), (cx + r // 2, cy - r // 3), max(3, r // 4))
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy - r * 2 // 3), max(3, r // 4))
    else:  # rainbow
        # Glowing 5-band rainbow arch
        colors = [(239, 68, 68), (245, 158, 11), (234, 179, 8), (34, 197, 94), (59, 130, 246), (168, 85, 247)]
        for idx, col in enumerate(colors):
            rad = r - idx * max(2, r // 6)
            if rad > 2:
                pygame.draw.arc(surface, col, pygame.Rect(cx - rad, cy - rad, rad * 2, rad * 2), 0, math.pi, max(3, r // 5))
        pygame.draw.circle(surface, (255, 255, 255), (cx - r * 2 // 3, cy), max(3, r // 4))
        pygame.draw.circle(surface, (255, 255, 255), (cx + r * 2 // 3, cy), max(3, r // 4))
        pygame.draw.circle(surface, dark, (cx - r * 2 // 3, cy), max(3, r // 4), 2)
        pygame.draw.circle(surface, dark, (cx + r * 2 // 3, cy), max(3, r // 4), 2)


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
    sounds = BridgeAudio()

    storage = get_storage()
    saved_data = storage.kv_get(STORAGE_KEY) if storage else {}
    if not isinstance(saved_data, dict):
        saved_data = {}
    total_stars = saved_data.get("stars", 0)

    level_idx = 0
    selected_block_id = "wood"
    slots: list[str | None] = [None, None, None, None]

    # Bunny animation state
    bunny_state = "idle"  # "idle", "walking", "failing", "celebrating"
    bunny_pos = [100.0, 310.0]
    bunny_target_step = 0
    bunny_anim_timer = 0.0
    is_victory = False
    particles: list[dict[str, Any]] = []

    def setup_level(idx: int) -> None:
        nonlocal slots, bunny_state, bunny_pos, bunny_target_step
        cur_lvl = LEVELS[idx % len(LEVELS)]
        slots = [None for _ in cur_lvl["required"]]
        bunny_state = "idle"
        bunny_pos = [100.0, 310.0]
        bunny_target_step = 0

    setup_level(0)

    running = True
    ready_published = False

    while running and not activity_stop_requested():
        cur_lvl = LEVELS[level_idx % len(LEVELS)]
        required = cur_lvl["required"]
        num_slots = len(required)

        # Slot layout
        bridge_start_x = 220
        bridge_end_x = 800
        slot_w = (bridge_end_x - bridge_start_x) // num_slots
        bridge_y = 350

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
                    play_again_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 120, REFERENCE_HEIGHT // 2 + 70, 240, 60)
                    if play_again_btn.collidepoint(mx, my):
                        is_victory = False
                        level_idx = 0
                        setup_level(0)
                    continue

                # Material Palette Selection (Bottom)
                palette_y = 475
                for b_idx, blk in enumerate(BLOCKS):
                    btn_rect = pygame.Rect(180 + b_idx * 170, palette_y, 140, 96)
                    if btn_rect.collidepoint(mx, my):
                        selected_block_id = blk["id"]
                        sounds.play("place")
                        continue

                # Bridge Slots Tapping
                if bunny_state == "idle":
                    for s_idx in range(num_slots):
                        sx = bridge_start_x + s_idx * slot_w
                        slot_rect = pygame.Rect(sx + 4, bridge_y, slot_w - 8, 70)
                        if slot_rect.collidepoint(mx, my):
                            slots[s_idx] = selected_block_id
                            sounds.play("place")
                            for _ in range(8):
                                particles.append({
                                    "x": slot_rect.centerx,
                                    "y": slot_rect.centery,
                                    "vx": random.uniform(-3, 3),
                                    "vy": random.uniform(-4, -1),
                                    "color": (254, 240, 138),
                                    "size": random.uniform(4, 8),
                                    "life": 1.0,
                                })

                # GO Button (Cross bridge)
                go_btn = pygame.Rect(REFERENCE_WIDTH - 180, 16, 160, 60)
                if go_btn.collidepoint(mx, my) and bunny_state == "idle":
                    bunny_state = "walking"
                    bunny_target_step = 0
                    bunny_anim_timer = 0.0

                # Clear Button
                clear_btn = pygame.Rect(REFERENCE_WIDTH - 350, 16, 150, 60)
                if clear_btn.collidepoint(mx, my) and bunny_state == "idle":
                    slots = [None for _ in required]
                    sounds.play("place")

        # Bunny Crossing / Physics Logic
        if bunny_state == "walking":
            bunny_anim_timer += 0.04
            # Step to next slot
            target_x = bridge_start_x + (bunny_target_step + 0.5) * slot_w
            dx = target_x - bunny_pos[0]
            if dx > 4:
                bunny_pos[0] += 6.0
                bunny_pos[1] = 310.0 - abs(math.sin(bunny_anim_timer * 8.0)) * 25.0
            else:
                # Arrived at slot - test block
                if bunny_target_step < num_slots:
                    placed = slots[bunny_target_step]
                    expected = required[bunny_target_step]
                    if placed != expected:
                        # Mismatched or missing block -> Fall & Trampoline bounce!
                        bunny_state = "failing"
                        bunny_anim_timer = 0.0
                        sounds.play("boing")
                    else:
                        # Correct block!
                        if placed == "shroom":
                            sounds.play("boing")
                        bunny_target_step += 1
                else:
                    # Reached the right cliff!
                    bunny_pos[0] += 6.0
                    if bunny_pos[0] >= 870:
                        bunny_state = "celebrating"
                        sounds.play("win")
                        total_stars += 1
                        if storage:
                            storage.kv_set(STORAGE_KEY, {"stars": total_stars})
                        try:
                            emit_activity_event("bridge.level_completed", {"level": level_idx + 1, "stars": total_stars})
                        except Exception:
                            pass

        elif bunny_state == "failing":
            bunny_anim_timer += 0.04
            # Fall down to safety trampoline at y=430, then bounce back up to x=100
            if bunny_anim_timer < 0.5:
                bunny_pos[1] += 8.0
            else:
                # Bounce arc back to start
                t = (bunny_anim_timer - 0.5) / 0.8
                if t < 1.0:
                    bunny_pos[0] = bunny_pos[0] * (1 - 0.08) + 100.0 * 0.08
                    bunny_pos[1] = 430.0 - math.sin(t * math.pi) * 120.0
                else:
                    bunny_pos = [100.0, 310.0]
                    bunny_state = "idle"

        elif bunny_state == "celebrating":
            bunny_anim_timer += 0.04
            if bunny_anim_timer > 1.8:
                level_idx += 1
                if level_idx >= len(LEVELS):
                    is_victory = True
                else:
                    setup_level(level_idx)

        # Update particles
        surviving_p = []
        for p in particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 0.04
            if p["life"] > 0:
                surviving_p.append(p)
        particles = surviving_p

        # RENDER TO CANVAS
        surf = canvas.surface

        # 1. Sky & Backdrop
        surf.fill(cur_lvl["sky"])

        # Sun / Moon
        pygame.draw.circle(surf, (254, 240, 138), (140, 100), 45)

        # 2. Gap (Water / Abyss)
        gap_rect = pygame.Rect(bridge_start_x - 10, bridge_y, (bridge_end_x - bridge_start_x) + 20, REFERENCE_HEIGHT - bridge_y)
        pygame.draw.rect(surf, cur_lvl["gap_water"], gap_rect)

        # Safety Trampoline at the bottom of the chasm
        tramp_x = (bridge_start_x + bridge_end_x) // 2
        tramp_rect = pygame.Rect(tramp_x - 120, 440, 240, 36)
        pygame.draw.rect(surf, (239, 68, 68), tramp_rect, border_radius=18)
        pygame.draw.rect(surf, (254, 240, 138), (tramp_x - 100, 446, 200, 24), border_radius=12)

        # 3. Cliffs (Left and Right)
        left_cliff = pygame.Rect(0, bridge_y - 20, bridge_start_x, REFERENCE_HEIGHT - bridge_y + 20)
        right_cliff = pygame.Rect(bridge_end_x, bridge_y - 20, REFERENCE_WIDTH - bridge_end_x, REFERENCE_HEIGHT - bridge_y + 20)
        pygame.draw.rect(surf, cur_lvl["cliff_color"], left_cliff, border_top_right_radius=24)
        pygame.draw.rect(surf, cur_lvl["cliff_color"], right_cliff, border_top_left_radius=24)

        # Goal Party Flag on the Right Cliff
        flag_x = bridge_end_x + 80
        pygame.draw.rect(surf, (120, 53, 15), (flag_x, 240, 8, 100), border_radius=4)
        pygame.draw.polygon(surf, (234, 179, 8), [(flag_x + 8, 240), (flag_x + 60, 260), (flag_x + 8, 280)])
        # Golden Carrot Reward
        pygame.draw.circle(surf, (249, 115, 22), (flag_x + 35, 310), 16)
        pygame.draw.polygon(surf, (34, 197, 94), [(flag_x + 30, 294), (flag_x + 40, 294), (flag_x + 35, 285)])

        # 4. Bridge Slots & Placed Blocks
        now = time.time()
        for s_idx in range(num_slots):
            sx = bridge_start_x + s_idx * slot_w
            slot_rect = pygame.Rect(sx + 6, bridge_y, slot_w - 12, 60)
            placed = slots[s_idx]
            req_type = required[s_idx]

            if placed is not None:
                # ----------------------------------------------------
                # PLACED STATE: Solid, walkable bridge deck plank
                # ----------------------------------------------------
                # Solid plank deck background
                pygame.draw.rect(surf, (255, 255, 255), slot_rect, border_radius=14)
                pygame.draw.rect(surf, (34, 197, 94), slot_rect, width=4, border_radius=14)
                # Continuous suspension bridge rope across slot
                pygame.draw.line(surf, (180, 83, 9), (slot_rect.left - 6, slot_rect.top + 8), (slot_rect.right + 6, slot_rect.top + 8), 4)
                # Solid large block illustration
                _draw_block_icon(surf, placed, slot_rect.centerx, slot_rect.centery + 2, 54)
                # Green Checkmark Badge in top-right corner
                chk_x = slot_rect.right - 14
                chk_y = slot_rect.top + 14
                pygame.draw.circle(surf, (34, 197, 94), (chk_x, chk_y), 10)
                pygame.draw.circle(surf, (255, 255, 255), (chk_x, chk_y), 10, 2)
                pygame.draw.polygon(surf, (255, 255, 255), [(chk_x - 4, chk_y), (chk_x - 1, chk_y + 3), (chk_x + 4, chk_y - 3)], 2)
            else:
                # ----------------------------------------------------
                # EMPTY SLOT STATE: Hollow blueprint target with identical, true-color block hint
                # ----------------------------------------------------
                # Hollow dashed slot frame
                pygame.draw.rect(surf, (248, 250, 252), slot_rect, border_radius=14)
                pygame.draw.rect(surf, (148, 163, 184), slot_rect, width=2, border_radius=14)
                
                # White target halo pedestal in center
                pygame.draw.circle(surf, (255, 255, 255), (slot_rect.centerx, slot_rect.centery + 2), 22)
                pygame.draw.circle(surf, (203, 213, 225), (slot_rect.centerx, slot_rect.centery + 2), 22, 2)

                # REQUIRED BLOCK ICON IN FULL, TRUE, VIBRANT ORIGINAL COLORS (Wood=Brown, Shroom=Red, Stone=Gray, Rainbow=Rainbow)
                _draw_block_icon(surf, req_type, slot_rect.centerx, slot_rect.centery + 2, 38)

                # Pulsing golden hint arrow above icon pointing down "⬇ Place Here"
                arrow_bob = int(math.sin(now * 5.0 + s_idx) * 3.0)
                arrow_y = slot_rect.top + 12 + arrow_bob
                pygame.draw.polygon(surf, (234, 179, 8), [
                    (slot_rect.centerx - 6, arrow_y - 4),
                    (slot_rect.centerx + 6, arrow_y - 4),
                    (slot_rect.centerx, arrow_y + 4),
                ])
                pygame.draw.polygon(surf, (180, 83, 9), [
                    (slot_rect.centerx - 6, arrow_y - 4),
                    (slot_rect.centerx + 6, arrow_y - 4),
                    (slot_rect.centerx, arrow_y + 4),
                ], 1)

        # 5. Bunny Character
        bx, by = bunny_pos
        # Body
        pygame.draw.circle(surf, (255, 255, 255), (int(bx), int(by)), 30)
        # Ears (Twitch animation)
        ear_twitch = math.sin(time.time() * 6.0) * 3.0
        pygame.draw.ellipse(surf, (255, 255, 255), pygame.Rect(bx - 18 + ear_twitch, by - 55, 14, 34))
        pygame.draw.ellipse(surf, (244, 114, 182), pygame.Rect(bx - 14 + ear_twitch, by - 48, 8, 22))
        pygame.draw.ellipse(surf, (255, 255, 255), pygame.Rect(bx + 4 - ear_twitch, by - 55, 14, 34))
        pygame.draw.ellipse(surf, (244, 114, 182), pygame.Rect(bx + 8 - ear_twitch, by - 48, 8, 22))
        # Eyes & Cute Nose
        pygame.draw.circle(surf, (20, 20, 30), (int(bx - 8), int(by - 4)), 5)
        pygame.draw.circle(surf, (20, 20, 30), (int(bx + 8), int(by - 4)), 5)
        pygame.draw.circle(surf, (244, 114, 182), (int(bx), int(by + 4)), 4)

        # 6. Particles
        for p in particles:
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), int(p["size"]))

        # 7. Bottom Palette Buttons (Giant Chunky 140x96px Targets with Icon + Label)
        palette_y = 475
        block_labels = {
            "wood": "LEGNO",
            "stone": "PIETRA",
            "shroom": "FUNGO",
            "rainbow": "ARCOBALENO",
        }
        for b_idx, blk in enumerate(BLOCKS):
            btn_rect = pygame.Rect(180 + b_idx * 170, palette_y, 140, 96)
            is_sel = (blk["id"] == selected_block_id)
            pygame.draw.rect(surf, (255, 255, 255), btn_rect, border_radius=20)
            pygame.draw.rect(surf, (234, 179, 8) if is_sel else (203, 213, 225), btn_rect, width=5 if is_sel else 2, border_radius=20)
            _draw_block_icon(surf, blk["id"], btn_rect.centerx, btn_rect.top + 34, 46)
            lbl = block_labels.get(blk["id"], "")
            t_col = (180, 83, 9) if is_sel else (71, 85, 105)
            lbl_surf = typography.render(lbl, FontRole.DISPLAY, 16, t_col)
            surf.blit(lbl_surf, (btn_rect.centerx - lbl_surf.get_width() // 2, btn_rect.bottom - 24))

        # 8. Top Control Buttons (Giant Clean Buttons with Icon + Label)
        # GO / Cross Button (Giant Green Button with Big Bunny/Arrow Icon + VAI!)
        go_btn = pygame.Rect(REFERENCE_WIDTH - 180, 16, 160, 60)
        pygame.draw.rect(surf, (34, 197, 94), go_btn, border_radius=20)
        pygame.draw.rect(surf, (22, 101, 52), go_btn, width=4, border_radius=20)
        # White Bunny Icon
        bx = go_btn.left + 28
        by = go_btn.centery + 2
        pygame.draw.circle(surf, (255, 255, 255), (bx, by), 14)
        pygame.draw.ellipse(surf, (255, 255, 255), pygame.Rect(bx - 8, by - 20, 6, 14))
        pygame.draw.ellipse(surf, (244, 114, 182), pygame.Rect(bx - 6, by - 18, 3, 10))
        pygame.draw.ellipse(surf, (255, 255, 255), pygame.Rect(bx + 2, by - 20, 6, 14))
        pygame.draw.ellipse(surf, (244, 114, 182), pygame.Rect(bx + 4, by - 18, 3, 10))
        pygame.draw.circle(surf, (20, 20, 30), (bx - 4, by - 2), 2)
        pygame.draw.circle(surf, (20, 20, 30), (bx + 4, by - 2), 2)
        # Text VAI!
        go_txt = typography.render("VAI!", FontRole.DISPLAY, 24, (255, 255, 255))
        surf.blit(go_txt, (go_btn.left + 54, go_btn.centery - go_txt.get_height() // 2))
        # Arrow
        pygame.draw.polygon(surf, (255, 255, 255), [(go_btn.right - 35, go_btn.centery - 12), (go_btn.right - 15, go_btn.centery), (go_btn.right - 35, go_btn.centery + 12)])

        # Clear Button (Giant Button with Big Broom Icon + PULISCI)
        clear_btn = pygame.Rect(REFERENCE_WIDTH - 360, 16, 165, 60)
        pygame.draw.rect(surf, (241, 245, 249), clear_btn, border_radius=20)
        pygame.draw.rect(surf, (148, 163, 184), clear_btn, width=3, border_radius=20)
        # Broom / Erase Icon
        cx = clear_btn.left + 28
        cy = clear_btn.centery
        pygame.draw.line(surf, (120, 53, 15), (cx - 12, cy - 10), (cx + 4, cy + 6), 4)  # Handle
        pygame.draw.polygon(surf, (234, 179, 8), [(cx + 2, cy + 2), (cx + 14, cy - 4), (cx + 10, cy + 14), (cx - 2, cy + 10)])  # Straw
        c_txt = typography.render("PULISCI", FontRole.DISPLAY, 18, (71, 85, 105))
        surf.blit(c_txt, (clear_btn.left + 52, clear_btn.centery - c_txt.get_height() // 2))

        # Star Pill
        star_pill = pygame.Rect(80, 16, 130, 60)
        pygame.draw.rect(surf, (255, 255, 255), star_pill, border_radius=20)
        pygame.draw.rect(surf, (234, 179, 8), star_pill, width=3, border_radius=20)
        pygame.draw.circle(surf, (234, 179, 8), (star_pill.left + 30, star_pill.centery), 16)
        s_txt = typography.render(str(total_stars), FontRole.DISPLAY, 28, (180, 83, 9))
        surf.blit(s_txt, (star_pill.left + 58, star_pill.centery - s_txt.get_height() // 2))

        # 9. Victory Modal
        if is_victory:
            overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 15, 30, 210))
            surf.blit(overlay, (0, 0))

            card = pygame.Rect(REFERENCE_WIDTH // 2 - 250, REFERENCE_HEIGHT // 2 - 160, 500, 320)
            pygame.draw.rect(surf, (255, 252, 245), card, border_radius=28)
            pygame.draw.rect(surf, (234, 179, 8), card, width=5, border_radius=28)

            v_title = typography.render("BRAVISSIMA!", FontRole.DISPLAY, 32, (217, 119, 6))
            surf.blit(v_title, (card.centerx - v_title.get_width() // 2, card.top + 35))

            for i in range(5):
                sx = card.centerx - 100 + i * 50
                sy = card.top + 130
                pygame.draw.circle(surf, (234, 179, 8), (sx, sy), 22)
                pygame.draw.circle(surf, (254, 240, 138), (sx, sy), 10)

            again_btn = pygame.Rect(card.centerx - 120, card.bottom - 80, 240, 60)
            pygame.draw.rect(surf, (34, 197, 94), again_btn, border_radius=20)
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
