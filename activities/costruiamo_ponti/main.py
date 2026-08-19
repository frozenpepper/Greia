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
STORAGE_KEY = "costruiamo_ponti.progress.v1"

BLOCK_TYPES = [
    {"id": "wood", "name_it": "Legno 🪵", "name_en": "Wood 🪵", "color": (180, 83, 9), "border": (146, 64, 14), "bouncy": False},
    {"id": "stone", "name_it": "Pietra 🪨", "name_en": "Stone 🪨", "color": (100, 116, 139), "border": (71, 85, 105), "bouncy": False},
    {"id": "shroom", "name_it": "Fungo 🍄", "name_en": "Mushroom 🍄", "color": (239, 68, 68), "border": (220, 38, 38), "bouncy": True},
    {"id": "rainbow", "name_it": "Arcobaleno 🌈", "name_en": "Rainbow 🌈", "color": (168, 85, 247), "border": (147, 51, 234), "bouncy": False},
]

LEVELS = [
    {
        "id": "river",
        "name_it": "Fiume Verde 🌊",
        "name_en": "Green River 🌊",
        "sky": (186, 230, 253),
        "gap_bg": (56, 189, 248),
        "cliff_color": (34, 197, 94),
        "slots": 5,
    },
    {
        "id": "canyon",
        "name_it": "Canyon Roccioso 🏔️",
        "name_en": "Rocky Canyon 🏔️",
        "sky": (254, 215, 170),
        "gap_bg": (217, 119, 6),
        "cliff_color": (120, 53, 15),
        "slots": 5,
    },
    {
        "id": "space",
        "name_it": "Abisso Stellare 🌌",
        "name_en": "Cosmic Abyss 🌌",
        "sky": (15, 23, 42),
        "gap_bg": (30, 27, 75),
        "cliff_color": (59, 130, 246),
        "slots": 5,
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
        # Place block (wood thud)
        thud_samples = []
        for i in range(int(rate * 0.08)):
            t = i / rate
            env = math.exp(-14.0 * t)
            val = math.sin(2.0 * math.pi * 220.0 * t)
            thud_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["place"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(thud_samples)))

        # Boing jump
        boing_samples = []
        for i in range(int(rate * 0.20)):
            t = i / rate
            env = math.exp(-5.0 * t)
            freq = 300.0 + 400.0 * (t / 0.20)
            val = math.sin(2.0 * math.pi * freq * t)
            boing_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["boing"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(boing_samples)))

        # Step
        step_samples = []
        for i in range(int(rate * 0.05)):
            t = i / rate
            env = math.exp(-18.0 * t)
            val = math.sin(2.0 * math.pi * 380.0 * t)
            step_samples.append(int(32767.0 * 0.20 * env * val))
        self._sounds["step"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(step_samples)))

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
    sounds = BridgeAudio()

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

    level_idx = 0
    selected_block_idx = 0

    gap_start = 240
    gap_end = 780
    slot_count = 5
    slot_w = (gap_end - gap_start) // slot_count
    bridge_y = 360

    slots: list[dict[str, Any] | None] = [None] * slot_count

    # Hero crossing state
    is_crossing = False
    hero_x = 120.0
    hero_target_x = 120.0
    hero_hop_y = 0.0
    cross_step = -1

    particles: list[dict[str, Any]] = []
    is_victory = False

    def reset_bridge() -> None:
        nonlocal slots, is_crossing, hero_x, hero_target_x, hero_hop_y, cross_step, is_victory
        slots = [None] * slot_count
        is_crossing = False
        hero_x = 120.0
        hero_target_x = 120.0
        hero_hop_y = 0.0
        cross_step = -1
        is_victory = False
        particles.clear()

    reset_bridge()

    running = True
    ready_published = False

    while running and not activity_stop_requested():
        t_now = time.time()
        lvl = LEVELS[level_idx]

        # Hero walking logic
        if is_crossing:
            dx = hero_target_x - hero_x
            if abs(dx) > 2.0:
                hero_x += dx * 0.12
                hero_hop_y = -math.sin((1.0 - abs(dx) / slot_w) * math.pi) * 35.0
            else:
                hero_x = hero_target_x
                hero_hop_y = 0.0
                cross_step += 1
                if cross_step < slot_count:
                    current_blk = slots[cross_step]
                    if current_blk is not None:
                        hero_target_x = gap_start + (cross_step + 0.5) * slot_w
                        if current_blk["bouncy"]:
                            sounds.play("boing")
                        else:
                            sounds.play("step")
                    else:
                        # Fall / stop
                        is_crossing = False
                elif cross_step == slot_count:
                    # Reached right cliff!
                    hero_target_x = 880.0
                    sounds.play("step")
                elif cross_step > slot_count:
                    # VICTORY!
                    is_crossing = False
                    is_victory = True
                    sounds.play("win")
                    try:
                        emit_activity_event("bridge.crossing_completed", {"level": lvl["id"]})
                    except Exception:
                        pass
                    for _ in range(50):
                        particles.append({
                            "x": random.uniform(700, 950),
                            "y": random.uniform(200, 360),
                            "vx": random.uniform(-2.0, 2.0),
                            "vy": random.uniform(-2.0, 2.0),
                            "color": (254, 202, 87),
                            "size": random.uniform(4.0, 8.0),
                            "life": 1.0,
                            "decay": 0.02,
                        })

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
                        level_idx = (level_idx + 1) % len(LEVELS)
                        reset_bridge()
                    elif not is_crossing and all(s is not None for s in slots):
                        is_crossing = True
                        cross_step = 0
                        hero_target_x = gap_start + 0.5 * slot_w
                elif event.key == pygame.K_c:
                    reset_bridge()

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
                        level_idx = (level_idx + 1) % len(LEVELS)
                        reset_bridge()
                        continue

                # Cross Button (Top Right)
                cross_btn = pygame.Rect(REFERENCE_WIDTH - 160, 15, 140, 42)
                if cross_btn.collidepoint(mx, my):
                    if not is_crossing and all(s is not None for s in slots):
                        is_crossing = True
                        cross_step = 0
                        hero_target_x = gap_start + 0.5 * slot_w
                    continue

                # Clear Button (Top Right - 310)
                clear_btn = pygame.Rect(REFERENCE_WIDTH - 310, 15, 140, 42)
                if clear_btn.collidepoint(mx, my):
                    reset_bridge()
                    continue

                # Bottom Block Selectors
                tool_y = REFERENCE_HEIGHT - 58
                for b_idx in range(len(BLOCK_TYPES)):
                    bx = 180 + b_idx * 160
                    if pygame.Rect(bx, tool_y, 145, 44).collidepoint(mx, my):
                        selected_block_idx = b_idx
                        break

                # Slot Clicks (Building the bridge)
                if not is_crossing and not is_victory:
                    for s_i in range(slot_count):
                        sx = gap_start + s_i * slot_w
                        slot_rect = pygame.Rect(sx, bridge_y - 20, slot_w, 60)
                        if slot_rect.collidepoint(mx, my):
                            slots[s_i] = BLOCK_TYPES[selected_block_idx]
                            sounds.play("place")
                            try:
                                emit_activity_event("bridge.block_placed", {"slot": s_i, "block": slots[s_i]["id"]})
                            except Exception:
                                pass
                            # Sparkle
                            for _ in range(8):
                                particles.append({
                                    "x": float(slot_rect.centerx),
                                    "y": float(slot_rect.centery),
                                    "vx": random.uniform(-1.5, 1.5),
                                    "vy": random.uniform(-1.5, 1.5),
                                    "color": slots[s_i]["color"],
                                    "size": random.uniform(3.0, 6.0),
                                    "life": 1.0,
                                    "decay": 0.04,
                                })
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
        surf.fill(lvl["sky"])

        # Gap Background (River / Canyon / Cosmic Void)
        pygame.draw.rect(surf, lvl["gap_bg"], (gap_start, 350, gap_end - gap_start, REFERENCE_HEIGHT - 350))

        # Left Cliff
        pygame.draw.polygon(surf, lvl["cliff_color"], [
            (0, 360), (gap_start, 360), (gap_start - 30, REFERENCE_HEIGHT), (0, REFERENCE_HEIGHT)
        ])
        # Right Cliff
        pygame.draw.polygon(surf, lvl["cliff_color"], [
            (gap_end, 360), (REFERENCE_WIDTH, 360), (REFERENCE_WIDTH, REFERENCE_HEIGHT), (gap_end + 30, REFERENCE_HEIGHT)
        ])

        # Picnic Basket Goal on Right Cliff
        pygame.draw.rect(surf, (249, 115, 22), (860, 320, 50, 40), border_radius=6)
        pygame.draw.circle(surf, (239, 68, 68), (875, 310), 12)  # Balloon
        pygame.draw.circle(surf, (234, 179, 8), (895, 305), 12)  # Balloon

        # 2. Draw Bridge Slots & Placed Blocks
        for s_i in range(slot_count):
            sx = gap_start + s_i * slot_w
            slot_rect = pygame.Rect(sx + 3, bridge_y, slot_w - 6, 30)
            blk = slots[s_i]

            if blk is None:
                # Empty ghost dashed slot
                pygame.draw.rect(surf, (255, 255, 255), slot_rect, width=2, border_radius=6)
                pygame.draw.circle(surf, (255, 255, 255), slot_rect.center, 6)
            else:
                # Render Block
                pygame.draw.rect(surf, blk["color"], slot_rect, border_radius=8)
                pygame.draw.rect(surf, blk["border"], slot_rect, width=3, border_radius=8)
                if blk["bouncy"]:
                    # Mushroom white dots
                    pygame.draw.circle(surf, (255, 255, 255), (slot_rect.centerx - 15, slot_rect.centery), 4)
                    pygame.draw.circle(surf, (255, 255, 255), (slot_rect.centerx + 15, slot_rect.centery), 4)

        # 3. Draw Hero Character (Bunny 🐰)
        char_x = hero_x
        char_y = bridge_y - 25 + hero_hop_y
        char_r = 24
        # Bunny Ears
        pygame.draw.ellipse(surf, (255, 255, 255), (char_x - 14, char_y - 38, 10, 22))
        pygame.draw.ellipse(surf, (255, 255, 255), (char_x + 4, char_y - 38, 10, 22))
        pygame.draw.ellipse(surf, (244, 114, 182), (char_x - 12, char_y - 34, 6, 16))
        pygame.draw.ellipse(surf, (244, 114, 182), (char_x + 6, char_y - 34, 6, 16))
        # Body
        pygame.draw.circle(surf, (255, 255, 255), (int(char_x), int(char_y)), char_r)
        # Face
        pygame.draw.circle(surf, (30, 30, 40), (int(char_x - 7), int(char_y - 4)), 4)
        pygame.draw.circle(surf, (30, 30, 40), (int(char_x + 7), int(char_y - 4)), 4)
        pygame.draw.circle(surf, (244, 114, 182), (int(char_x), int(char_y + 4)), 3)

        # 4. Draw Particles
        for p in particles:
            cur_sz = max(2.0, p["size"] * max(0.0, min(1.0, p["life"])))
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), int(cur_sz))

        # 5. Top HUD
        title_surf = typography.render(t("activity.title", "Costruiamo i Ponti"), FontRole.DISPLAY, 24, (30, 41, 59))
        surf.blit(title_surf, (80, 20))

        l_name = lvl["name_it"] if active_locale == "it" else lvl["name_en"]
        lvl_surf = typography.render(l_name, FontRole.TITLE, 20, (71, 85, 105))
        surf.blit(lvl_surf, (370, 22))

        # Cross Button
        cross_btn = pygame.Rect(REFERENCE_WIDTH - 160, 15, 140, 42)
        can_cross = all(s is not None for s in slots)
        cross_col = (34, 197, 94) if can_cross else (148, 163, 184)
        pygame.draw.rect(surf, cross_col, cross_btn, border_radius=12)
        c_txt = typography.render(t("btn.cross", "🐾 Attraversa!"), FontRole.CONTROL, 17, (255, 255, 255))
        surf.blit(c_txt, (cross_btn.centerx - c_txt.get_width() // 2, cross_btn.centery - c_txt.get_height() // 2))

        # Clear Button
        clear_btn = pygame.Rect(REFERENCE_WIDTH - 310, 15, 140, 42)
        pygame.draw.rect(surf, (71, 85, 105), clear_btn, border_radius=12)
        cl_txt = typography.render(t("btn.clear", "🧹 Pulisci"), FontRole.CONTROL, 17, (255, 255, 255))
        surf.blit(cl_txt, (clear_btn.centerx - cl_txt.get_width() // 2, clear_btn.centery - cl_txt.get_height() // 2))

        # 6. Bottom Block Toolbar
        tool_y = REFERENCE_HEIGHT - 58
        for b_idx, blk in enumerate(BLOCK_TYPES):
            bx = 180 + b_idx * 160
            b_rect = pygame.Rect(bx, tool_y, 145, 44)
            is_sel = selected_block_idx == b_idx
            bg_col = blk["color"] if is_sel else (255, 255, 255)
            txt_col = (255, 255, 255) if is_sel else (30, 41, 59)
            pygame.draw.rect(surf, bg_col, b_rect, border_radius=12)
            pygame.draw.rect(surf, blk["border"], b_rect, width=3 if is_sel else 2, border_radius=12)
            b_name = blk["name_it"] if active_locale == "it" else blk["name_en"]
            lbl_surf = typography.render(b_name, FontRole.CONTROL, 16, txt_col)
            surf.blit(lbl_surf, (b_rect.centerx - lbl_surf.get_width() // 2, b_rect.centery - lbl_surf.get_height() // 2))

        # 7. Victory Modal
        if is_victory:
            overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 15, 30, 200))
            surf.blit(overlay, (0, 0))

            card = pygame.Rect(REFERENCE_WIDTH // 2 - 220, REFERENCE_HEIGHT // 2 - 140, 440, 280)
            pygame.draw.rect(surf, (30, 41, 59), card, border_radius=20)
            pygame.draw.rect(surf, (254, 202, 87), card, width=3, border_radius=20)

            v_title = typography.render(t("victory.title", "Il ponte è solidissimo! 🐾🎉"), FontRole.DISPLAY, 22, (254, 202, 87))
            surf.blit(v_title, (card.centerx - v_title.get_width() // 2, card.top + 30))

            v_sub = typography.render(t("victory.subtitle", "Il cucciolo ha raggiunto il picnic!"), FontRole.BODY, 18, (241, 245, 249))
            surf.blit(v_sub, (card.centerx - v_sub.get_width() // 2, card.top + 75))

            for i in range(3):
                star_x = card.centerx - 50 + i * 50
                star_y = card.top + 130
                pygame.draw.circle(surf, (254, 202, 87), (star_x, star_y), 18)

            again_btn = pygame.Rect(card.centerx - 110, card.bottom - 65, 220, 46)
            pygame.draw.rect(surf, (34, 197, 94), again_btn, border_radius=14)
            again_lbl = typography.render(t("btn.play_again", "🎉 Prossimo Livello!"), FontRole.CONTROL, 20, (255, 255, 255))
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
                "level_idx": level_idx,
                "timestamp": time.time(),
            })
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
