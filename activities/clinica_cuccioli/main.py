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
STORAGE_KEY = "clinica_cuccioli.progress.v2"

TOOLS = [
    {"id": "stethoscope", "color": (59, 130, 246)},
    {"id": "bath", "color": (14, 165, 233)},
    {"id": "bandaid", "color": (236, 72, 153)},
    {"id": "food", "color": (234, 179, 8)},
    {"id": "cuddle", "color": (239, 68, 68)},
]

PATIENTS = [
    {"id": "dog", "color": (217, 119, 6), "ear_color": (180, 83, 9), "muzzle": (254, 243, 199)},
    {"id": "cat", "color": (251, 146, 60), "ear_color": (244, 114, 182), "muzzle": (255, 255, 255)},
    {"id": "bunny", "color": (248, 250, 252), "ear_color": (244, 114, 182), "muzzle": (255, 255, 255)},
    {"id": "bear", "color": (146, 64, 14), "ear_color": (120, 53, 15), "muzzle": (254, 215, 170)},
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


class ClinicAudio:
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
        # Heartbeat
        heart_samples = []
        for i in range(int(rate * 0.15)):
            t = i / rate
            env = math.exp(-12.0 * t)
            val = math.sin(2.0 * math.pi * 90.0 * t)
            heart_samples.append(int(32767.0 * 0.35 * env * val))
        self._sounds["stethoscope"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(heart_samples)))

        # Splash / Soap bubbles
        bubble_samples = []
        for i in range(int(rate * 0.20)):
            t = i / rate
            env = math.exp(-6.0 * t)
            freq = 400.0 + 300.0 * math.sin(t * 40.0)
            val = math.sin(2.0 * math.pi * freq * t)
            bubble_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["bath"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(bubble_samples)))

        # Sparkle bandaid
        sparkle_samples = []
        for i in range(int(rate * 0.22)):
            t = i / rate
            env = math.exp(-5.0 * t)
            val = math.sin(2.0 * math.pi * 880.0 * t)
            sparkle_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["bandaid"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(sparkle_samples)))

        # Munching food
        munch_samples = []
        for i in range(int(rate * 0.18)):
            t = i / rate
            env = math.exp(-10.0 * t)
            val = (2.0 / math.pi) * math.asin(math.sin(2.0 * math.pi * 260.0 * t))
            munch_samples.append(int(32767.0 * 0.28 * env * val))
        self._sounds["food"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(munch_samples)))

        # Purr cuddle
        purr_samples = []
        for i in range(int(rate * 0.25)):
            t = i / rate
            env = math.exp(-4.0 * t)
            freq = 587.0 + 200.0 * (t / 0.25)
            val = math.sin(2.0 * math.pi * freq * t)
            purr_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["cuddle"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(purr_samples)))

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


VetAudio = ClinicAudio


def _draw_tool_icon(surface: pygame.Surface, tool_id: str, cx: int, cy: int, size: int) -> None:
    r = size // 2
    if tool_id == "stethoscope":
        pygame.draw.arc(surface, (59, 130, 246), pygame.Rect(cx - r * 3 // 4, cy - r, r * 3 // 2, r * 3 // 2), math.pi, 2 * math.pi, 5)
        pygame.draw.circle(surface, (148, 163, 184), (cx, cy + r // 2), r // 3)
        pygame.draw.circle(surface, (59, 130, 246), (cx, cy + r // 2), r // 6)
    elif tool_id == "bath":
        pygame.draw.rect(surface, (14, 165, 233), (cx - r * 3 // 4, cy - r // 4, r * 3 // 2, r), border_radius=8)
        pygame.draw.circle(surface, (224, 242, 254), (cx - r // 3, cy - r // 2), r // 3)
        pygame.draw.circle(surface, (224, 242, 254), (cx + r // 4, cy - r * 2 // 3), r // 4)
    elif tool_id == "bandaid":
        pygame.draw.rect(surface, (244, 114, 182), (cx - r, cy - r // 3, size, r * 2 // 3), border_radius=8)
        pygame.draw.rect(surface, (255, 255, 255), (cx - r // 4, cy - r // 3, r // 2, r * 2 // 3))
        pygame.draw.circle(surface, (244, 63, 94), (cx, cy), max(2, r // 6))
    elif tool_id == "food":
        pygame.draw.ellipse(surface, (234, 179, 8), pygame.Rect(cx - r, cy - r // 4, size, r))
        pygame.draw.circle(surface, (180, 83, 9), (cx - r // 4, cy - r // 3), max(2, r // 4))
        pygame.draw.circle(surface, (180, 83, 9), (cx + r // 4, cy - r // 3), max(2, r // 4))
    else:  # cuddle
        pygame.draw.circle(surface, (239, 68, 68), (cx - r // 3, cy - r // 4), r // 2)
        pygame.draw.circle(surface, (239, 68, 68), (cx + r // 3, cy - r // 4), r // 2)
        pygame.draw.polygon(surface, (239, 68, 68), [(cx - r * 3 // 4, cy - r // 8), (cx + r * 3 // 4, cy - r // 8), (cx, cy + r * 3 // 4)])


def _draw_patient(surface: pygame.Surface, patient_id: str, cx: int, cy: int, size: int, has_mud: bool, has_scratch: bool) -> None:
    r = size // 2
    # Body
    if patient_id == "dog":
        pygame.draw.ellipse(surface, (217, 119, 6), pygame.Rect(cx - r, cy - r // 2, size, r * 5 // 4))
        pygame.draw.ellipse(surface, (254, 243, 199), pygame.Rect(cx - r // 2, cy - r // 4, r, r * 3 // 4))
        # Head
        pygame.draw.circle(surface, (217, 119, 6), (cx - r // 2, cy - r // 2), r * 2 // 3)
        # Floppy Ears
        pygame.draw.ellipse(surface, (180, 83, 9), pygame.Rect(cx - r - 10, cy - r // 2, r // 2, r))
        pygame.draw.ellipse(surface, (180, 83, 9), pygame.Rect(cx - r // 3, cy - r // 2, r // 2, r))
        # Muzzle & Eyes
        pygame.draw.circle(surface, (254, 243, 199), (cx - r // 2, cy - r // 3), r // 3)
        pygame.draw.circle(surface, (20, 20, 30), (cx - r // 2, cy - r // 3), 6)  # Nose
        pygame.draw.circle(surface, (20, 20, 30), (cx - r * 2 // 3, cy - r * 3 // 5), 7)
        pygame.draw.circle(surface, (20, 20, 30), (cx - r // 3, cy - r * 3 // 5), 7)
        pygame.draw.circle(surface, (255, 255, 255), (cx - r * 2 // 3 + 2, cy - r * 3 // 5 - 2), 2)
        pygame.draw.circle(surface, (255, 255, 255), (cx - r // 3 + 2, cy - r * 3 // 5 - 2), 2)
        # Tail
        pygame.draw.arc(surface, (217, 119, 6), pygame.Rect(cx + r * 2 // 3, cy - r // 2, r // 2, r // 2), 0.5, 2.8, 8)

    elif patient_id == "cat":
        pygame.draw.ellipse(surface, (251, 146, 60), pygame.Rect(cx - r, cy - r // 2, size, r * 5 // 4))
        pygame.draw.circle(surface, (251, 146, 60), (cx - r // 2, cy - r // 2), r * 2 // 3)
        # Pointy ears
        pygame.draw.polygon(surface, (251, 146, 60), [(cx - r, cy - r // 2), (cx - r * 3 // 4, cy - r), (cx - r // 2, cy - r // 2)])
        pygame.draw.polygon(surface, (244, 114, 182), [(cx - r + 4, cy - r // 2), (cx - r * 3 // 4, cy - r + 8), (cx - r // 2 - 4, cy - r // 2)])
        pygame.draw.polygon(surface, (251, 146, 60), [(cx - r // 2, cy - r // 2), (cx - r // 4, cy - r), (cx, cy - r // 2)])
        pygame.draw.polygon(surface, (244, 114, 182), [(cx - r // 2 + 4, cy - r // 2), (cx - r // 4, cy - r + 8), (cx - 4, cy - r // 2)])
        # Eyes & cute nose
        pygame.draw.circle(surface, (20, 20, 30), (cx - r * 2 // 3, cy - r * 3 // 5), 7)
        pygame.draw.circle(surface, (20, 20, 30), (cx - r // 3, cy - r * 3 // 5), 7)
        pygame.draw.circle(surface, (244, 114, 182), (cx - r // 2, cy - r // 3), 5)

    elif patient_id == "bunny":
        pygame.draw.ellipse(surface, (248, 250, 252), pygame.Rect(cx - r, cy - r // 2, size, r * 5 // 4))
        pygame.draw.circle(surface, (248, 250, 252), (cx - r // 2, cy - r // 2), r * 2 // 3)
        # Long bunny ears
        pygame.draw.ellipse(surface, (248, 250, 252), pygame.Rect(cx - r * 3 // 4, cy - r * 5 // 4, r // 3, r * 4 // 5))
        pygame.draw.ellipse(surface, (244, 114, 182), pygame.Rect(cx - r * 3 // 4 + 3, cy - r * 5 // 4 + 6, r // 3 - 6, r * 4 // 5 - 12))
        pygame.draw.ellipse(surface, (248, 250, 252), pygame.Rect(cx - r // 3, cy - r * 5 // 4, r // 3, r * 4 // 5))
        pygame.draw.ellipse(surface, (244, 114, 182), pygame.Rect(cx - r // 3 + 3, cy - r * 5 // 4 + 6, r // 3 - 6, r * 4 // 5 - 12))
        # Eyes & pink nose
        pygame.draw.circle(surface, (20, 20, 30), (cx - r * 2 // 3, cy - r * 3 // 5), 6)
        pygame.draw.circle(surface, (20, 20, 30), (cx - r // 3, cy - r * 3 // 5), 6)
        pygame.draw.circle(surface, (244, 114, 182), (cx - r // 2, cy - r // 3), 4)

    else:  # bear
        pygame.draw.ellipse(surface, (146, 64, 14), pygame.Rect(cx - r, cy - r // 2, size, r * 5 // 4))
        pygame.draw.circle(surface, (146, 64, 14), (cx - r // 2, cy - r // 2), r * 2 // 3)
        # Round bear ears
        pygame.draw.circle(surface, (120, 53, 15), (cx - r * 3 // 4, cy - r * 4 // 5), r // 4)
        pygame.draw.circle(surface, (120, 53, 15), (cx - r // 4, cy - r * 4 // 5), r // 4)
        pygame.draw.circle(surface, (254, 215, 170), (cx - r // 2, cy - r // 3), r // 3)
        pygame.draw.circle(surface, (20, 20, 30), (cx - r // 2, cy - r // 3), 6)
        pygame.draw.circle(surface, (20, 20, 30), (cx - r * 2 // 3, cy - r * 3 // 5), 6)
        pygame.draw.circle(surface, (20, 20, 30), (cx - r // 3, cy - r * 3 // 5), 6)

    # Mud Spots on Body
    if has_mud:
        for m_off in [(cx, cy), (cx + r // 3, cy + r // 4), (cx + r // 2, cy - r // 6)]:
            pygame.draw.circle(surface, (120, 53, 15), m_off, 14)
            pygame.draw.circle(surface, (90, 40, 10), m_off, 8)

    # Scratch / Boo-boo on Body
    if has_scratch:
        pygame.draw.line(surface, (239, 68, 68), (cx + r // 4, cy - r // 4), (cx + r // 2, cy + r // 6), 4)
        pygame.draw.line(surface, (239, 68, 68), (cx + r // 4, cy + r // 6), (cx + r // 2, cy - r // 4), 4)


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
    sounds = ClinicAudio()

    storage = get_storage()
    saved_data = storage.kv_get(STORAGE_KEY) if storage else {}
    if not isinstance(saved_data, dict):
        saved_data = {}
    total_stars = saved_data.get("stars", 0)

    # Procedural prescriptions for variety
    patient_idx = 0
    selected_tool_id = "stethoscope"
    required_steps: list[str] = []
    completed_steps: list[str] = []
    is_victory = False
    hearts_and_sparkles: list[dict[str, Any]] = []

    def setup_patient(idx: int) -> None:
        nonlocal required_steps, completed_steps, selected_tool_id
        # Randomize prescription: 2, 3, or 4 steps
        all_possible = ["stethoscope", "bath", "bandaid", "food", "cuddle"]
        step_count = random.choice([2, 2, 3, 3, 4])
        required_steps = random.sample(all_possible, step_count)
        completed_steps = []
        selected_tool_id = required_steps[0]

    setup_patient(0)

    running = True
    ready_published = False

    while running and not activity_stop_requested():
        cur_patient = PATIENTS[patient_idx % len(PATIENTS)]
        next_needed = next((t for t in required_steps if t not in completed_steps), None)

        has_mud = ("bath" in required_steps and "bath" not in completed_steps)
        has_scratch = ("bandaid" in required_steps and "bandaid" not in completed_steps)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pointer = metrics.to_reference(event.pos)
                mx, my = pointer.x, pointer.y

                if not _is_safe_point(screen, event.pos):
                    continue

                if is_victory:
                    play_again_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 120, REFERENCE_HEIGHT // 2 + 70, 240, 60)
                    if play_again_btn.collidepoint(mx, my):
                        is_victory = False
                        patient_idx = 0
                        setup_patient(0)
                    continue

                # Tool selection from bottom palette
                palette_y = 475
                for t_idx, tool in enumerate(TOOLS):
                    btn_rect = pygame.Rect(80 + t_idx * 175, palette_y, 150, 96)
                    if btn_rect.collidepoint(mx, my):
                        selected_tool_id = tool["id"]
                        sounds.play(tool["id"])
                        continue

                # Patient exam table tap
                exam_table = pygame.Rect(REFERENCE_WIDTH // 2 - 240, 160, 480, 280)
                if exam_table.collidepoint(mx, my) and next_needed is not None:
                    if selected_tool_id == next_needed:
                        completed_steps.append(selected_tool_id)
                        sounds.play(selected_tool_id)

                        # Spawn celebration particles
                        for _ in range(14):
                            hearts_and_sparkles.append({
                                "x": mx + random.uniform(-20, 20),
                                "y": my + random.uniform(-20, 20),
                                "vx": random.uniform(-2, 2),
                                "vy": random.uniform(-4, -1),
                                "color": (239, 68, 68) if selected_tool_id == "cuddle" else (254, 240, 138),
                                "size": random.uniform(6, 12),
                                "life": 1.0,
                            })

                        # Auto-select next needed tool
                        rem = [t for t in required_steps if t not in completed_steps]
                        if rem:
                            selected_tool_id = rem[0]
                        else:
                            # Patient healed!
                            sounds.play("win")
                            total_stars += 1
                            if storage:
                                storage.kv_set(STORAGE_KEY, {"stars": total_stars})
                            try:
                                emit_activity_event("clinic.patient_cured", {"patient": cur_patient["id"], "stars": total_stars})
                            except Exception:
                                pass

                            patient_idx += 1
                            if patient_idx >= 4:
                                is_victory = True
                            else:
                                setup_patient(patient_idx)

        # Update floating particles
        surviving_h = []
        for p in hearts_and_sparkles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 0.03
            if p["life"] > 0:
                surviving_h.append(p)
        hearts_and_sparkles = surviving_h

        # RENDER TO CANVAS
        surf = canvas.surface

        # 1. Warm Clinic Wallpaper
        surf.fill((255, 247, 237))  # Cozy warm cream
        # Pastel wall stripes
        for sx in range(0, REFERENCE_WIDTH, 48):
            pygame.draw.rect(surf, (254, 237, 222), (sx, 0, 24, REFERENCE_HEIGHT))

        # Clinic Floor
        pygame.draw.rect(surf, (254, 215, 170), (0, 420, REFERENCE_WIDTH, 180))
        pygame.draw.line(surf, (217, 119, 6), (0, 420), (REFERENCE_WIDTH, 420), 4)

        # 2. Examination Bed
        table_rect = pygame.Rect(REFERENCE_WIDTH // 2 - 250, 160, 500, 260)
        pygame.draw.rect(surf, (255, 255, 255), table_rect, border_radius=28)
        pygame.draw.rect(surf, (203, 213, 225), table_rect, width=6, border_radius=28)
        pygame.draw.ellipse(surf, (241, 245, 249), pygame.Rect(table_rect.left + 20, table_rect.top + 20, table_rect.width - 40, table_rect.height - 40))

        # 3. Patient Creature (Center of Examination Table)
        _draw_patient(surf, cur_patient["id"], table_rect.centerx + 20, table_rect.centery + 15, 180, has_mud, has_scratch)

        # 4. Animated Thought Bubble (Zero-Text Prescription Goal)
        if next_needed is not None:
            tb_x = table_rect.left + 70
            tb_y = table_rect.top + 30
            # Small bubble dots
            pygame.draw.circle(surf, (255, 255, 255), (tb_x + 50, tb_y + 45), 8)
            pygame.draw.circle(surf, (255, 255, 255), (tb_x + 35, tb_y + 30), 12)
            # Main Thought Bubble
            pygame.draw.circle(surf, (255, 255, 255), (tb_x, tb_y), 44)
            pygame.draw.circle(surf, (234, 179, 8), (tb_x, tb_y), 44, 4)
            # Draw needed tool icon inside bubble
            _draw_tool_icon(surf, next_needed, tb_x, tb_y, 48)

        # 5. Step Progress Badges (Top Center)
        badge_start_x = REFERENCE_WIDTH // 2 - (len(required_steps) * 45) // 2
        for s_idx, step_id in enumerate(required_steps):
            bx = badge_start_x + s_idx * 50
            by = 40
            is_done = step_id in completed_steps
            pygame.draw.circle(surf, (34, 197, 94) if is_done else (255, 255, 255), (bx, by), 20)
            pygame.draw.circle(surf, (22, 101, 52) if is_done else (203, 213, 225), (bx, by), 20, 3)
            if is_done:
                pygame.draw.circle(surf, (254, 240, 138), (bx, by), 8)
            else:
                _draw_tool_icon(surf, step_id, bx, by, 22)

        # 6. Floating Particles
        for p in hearts_and_sparkles:
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), int(p["size"]))

        # 7. Bottom Tool Palette (Giant Chunky 150x96px Targets)
        palette_y = 475
        for t_idx, tool in enumerate(TOOLS):
            btn_rect = pygame.Rect(80 + t_idx * 175, palette_y, 150, 96)
            is_sel = (tool["id"] == selected_tool_id)
            is_active_needed = (tool["id"] == next_needed)

            pygame.draw.rect(surf, (255, 255, 255), btn_rect, border_radius=22)
            outline_col = (234, 179, 8) if is_sel else ((34, 197, 94) if is_active_needed else (203, 213, 225))
            pygame.draw.rect(surf, outline_col, btn_rect, width=5 if is_sel else (4 if is_active_needed else 2), border_radius=22)
            _draw_tool_icon(surf, tool["id"], btn_rect.centerx, btn_rect.centery, 58)

        # 8. Star Pill (Top Left)
        star_pill = pygame.Rect(80, 16, 130, 56)
        pygame.draw.rect(surf, (255, 255, 255), star_pill, border_radius=18)
        pygame.draw.rect(surf, (234, 179, 8), star_pill, width=3, border_radius=18)
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

            v_title = typography.render("CUCCIOLI CURATI!", FontRole.DISPLAY, 30, (217, 119, 6))
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

        clock.tick(60)

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
