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
STORAGE_KEY = "clinica_cuccioli.progress.v1"

PATIENTS = [
    {
        "id": "puppy",
        "name_it": "Cagnolino 🐶",
        "name_en": "Puppy 🐶",
        "color": (217, 119, 6),
        "ear_color": (180, 83, 9),
        "belly_color": (254, 243, 199),
    },
    {
        "id": "kitten",
        "name_it": "Gattino 🐱",
        "name_en": "Kitten 🐱",
        "color": (251, 146, 60),
        "ear_color": (234, 88, 12),
        "belly_color": (255, 237, 213),
    },
    {
        "id": "bunny",
        "name_it": "Coniglietto 🐰",
        "name_en": "Bunny 🐰",
        "color": (248, 250, 252),
        "ear_color": (244, 114, 182),
        "belly_color": (255, 255, 255),
    },
    {
        "id": "dragon",
        "name_it": "Draghetto 🐲",
        "name_en": "Little Dragon 🐲",
        "color": (16, 185, 129),
        "ear_color": (5, 150, 105),
        "belly_color": (167, 243, 208),
    },
]

TOOLS = [
    {"id": "stetho", "name_it": "🩺 Visita", "name_en": "🩺 Checkup", "color": (59, 130, 246)},
    {"id": "sponge", "name_it": "🧼 Bagnetto", "name_en": "🧼 Bath", "color": (56, 189, 248)},
    {"id": "bandage", "name_it": "🩹 Cerotto", "name_en": "🩹 Bandage", "color": (244, 114, 182)},
    {"id": "snack", "name_it": "🥣 Pappa", "name_en": "🥣 Treat", "color": (234, 179, 8)},
    {"id": "cuddle", "name_it": "💖 Coccole", "name_en": "💖 Cuddles", "color": (236, 72, 153)},
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


class VetAudio:
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
        self._sounds["heart"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(heart_samples)))

        # Bubble wash
        bubble_samples = []
        for i in range(int(rate * 0.12)):
            t = i / rate
            env = math.exp(-10.0 * t)
            val = math.sin(2.0 * math.pi * (400.0 + 300.0 * (t / 0.12)) * t)
            bubble_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["bubble"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(bubble_samples)))

        # Heal sparkle
        sparkle_samples = []
        for i in range(int(rate * 0.25)):
            t = i / rate
            env = math.exp(-5.0 * t)
            val = 0.5 * math.sin(2.0 * math.pi * 660.0 * t) + 0.5 * math.sin(2.0 * math.pi * 990.0 * t)
            sparkle_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["sparkle"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(sparkle_samples)))

        # Happy purr / bark
        purr_samples = []
        for i in range(int(rate * 0.30)):
            t = i / rate
            env = min(1.0, t * 10.0) * math.exp(-3.0 * t)
            val = math.sin(2.0 * math.pi * (140.0 + 30.0 * math.sin(20.0 * t)) * t)
            purr_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["purr"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(purr_samples)))

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
    sounds = VetAudio()

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

    patient_idx = 0
    selected_tool_idx = 0

    # Patient Status
    has_examined = False
    is_washed = False
    has_bandage = False
    has_eaten = False
    is_cuddled = False

    particles: list[dict[str, Any]] = []
    is_victory = False

    def reset_patient() -> None:
        nonlocal has_examined, is_washed, has_bandage, has_eaten, is_cuddled, is_victory
        has_examined = False
        is_washed = False
        has_bandage = False
        has_eaten = False
        is_cuddled = False
        is_victory = False
        particles.clear()

    reset_patient()

    running = True
    ready_published = False

    while running and not activity_stop_requested():
        t_now = time.time()
        patient = PATIENTS[patient_idx]
        is_fully_healed = has_examined and is_washed and has_bandage and has_eaten and is_cuddled

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN) and is_victory:
                    patient_idx = (patient_idx + 1) % len(PATIENTS)
                    reset_patient()

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
                        patient_idx = (patient_idx + 1) % len(PATIENTS)
                        reset_patient()
                        continue

                # Tool selection toolbar (Bottom)
                tool_y = REFERENCE_HEIGHT - 58
                for t_idx in range(len(TOOLS)):
                    bx = 120 + t_idx * 155
                    if pygame.Rect(bx, tool_y, 140, 44).collidepoint(mx, my):
                        selected_tool_idx = t_idx
                        break

                # Patient Click (Clinic Bed x = 320..700, y = 180..420)
                bed_rect = pygame.Rect(320, 180, 380, 240)
                if bed_rect.collidepoint(mx, my) and not is_victory:
                    tool = TOOLS[selected_tool_idx]
                    t_id = tool["id"]

                    if t_id == "stetho":
                        has_examined = True
                        sounds.play("heart")
                        for _ in range(6):
                            particles.append({
                                "x": float(bed_rect.centerx + random.uniform(-30, 30)),
                                "y": float(bed_rect.centery + random.uniform(-30, 30)),
                                "vx": random.uniform(-1.0, 1.0),
                                "vy": random.uniform(-2.0, -0.5),
                                "color": (59, 130, 246),
                                "size": random.uniform(6.0, 10.0),
                                "life": 1.0,
                                "decay": 0.03,
                            })
                    elif t_id == "sponge":
                        is_washed = True
                        sounds.play("bubble")
                        for _ in range(16):
                            particles.append({
                                "x": float(bed_rect.centerx + random.uniform(-50, 50)),
                                "y": float(bed_rect.centery + random.uniform(-40, 40)),
                                "vx": random.uniform(-1.5, 1.5),
                                "vy": random.uniform(-1.5, 1.5),
                                "color": (186, 230, 253),
                                "size": random.uniform(8.0, 16.0),
                                "life": 1.0,
                                "decay": 0.04,
                            })
                    elif t_id == "bandage":
                        has_bandage = True
                        sounds.play("sparkle")
                        for _ in range(12):
                            particles.append({
                                "x": float(bed_rect.centerx + random.uniform(-40, 40)),
                                "y": float(bed_rect.centery + random.uniform(-30, 30)),
                                "vx": random.uniform(-1.5, 1.5),
                                "vy": random.uniform(-1.5, 1.5),
                                "color": (244, 114, 182),
                                "size": random.uniform(4.0, 8.0),
                                "life": 1.0,
                                "decay": 0.03,
                            })
                    elif t_id == "snack":
                        has_eaten = True
                        sounds.play("purr")
                        for _ in range(10):
                            particles.append({
                                "x": float(bed_rect.centerx + random.uniform(-30, 30)),
                                "y": float(bed_rect.centery + random.uniform(-30, 30)),
                                "vx": random.uniform(-1.0, 1.0),
                                "vy": random.uniform(-2.0, -0.5),
                                "color": (234, 179, 8),
                                "size": random.uniform(5.0, 9.0),
                                "life": 1.0,
                                "decay": 0.03,
                            })
                    elif t_id == "cuddle":
                        is_cuddled = True
                        sounds.play("purr")
                        for _ in range(15):
                            particles.append({
                                "x": float(bed_rect.centerx + random.uniform(-50, 50)),
                                "y": float(bed_rect.centery + random.uniform(-40, 40)),
                                "vx": random.uniform(-1.5, 1.5),
                                "vy": random.uniform(-2.5, -1.0),
                                "color": (236, 72, 153),
                                "size": random.uniform(8.0, 14.0),
                                "life": 1.0,
                                "decay": 0.025,
                            })

                    try:
                        emit_activity_event("vet.treatment_applied", {"tool": t_id, "patient": patient["id"]})
                    except Exception:
                        pass

                    if has_examined and is_washed and has_bandage and has_eaten and is_cuddled:
                        is_victory = True
                        sounds.play("win")
                        try:
                            emit_activity_event("vet.patient_healed", {"patient": patient["id"]})
                        except Exception:
                            pass

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

        # 1. Warm Clinic Room Background
        surf.fill((254, 242, 242))  # Soft pastel pink/cream clinic

        # Wallpaper stripes
        for sx in range(0, REFERENCE_WIDTH, 40):
            pygame.draw.line(surf, (254, 226, 226), (sx, 0), (sx, 380), 20)

        # Floor
        pygame.draw.rect(surf, (254, 243, 199), (0, 380, REFERENCE_WIDTH, 220))
        pygame.draw.line(surf, (251, 191, 36), (0, 380), (REFERENCE_WIDTH, 380), 6)

        # 2. Clinic Bed & Cozy Mat
        bed_rect = pygame.Rect(290, 210, 444, 200)
        pygame.draw.rect(surf, (226, 232, 240), bed_rect, border_radius=20)
        pygame.draw.rect(surf, (255, 255, 255), (310, 230, 404, 160), border_radius=16)
        pygame.draw.rect(surf, (148, 163, 184), (310, 230, 404, 160), width=2, border_radius=16)

        # 3. Draw Patient Animal
        cx = 512
        cy = 300
        # Tail wag animation
        tail_ang = math.sin(t_now * 8.0) * 0.4 if is_fully_healed else math.sin(t_now * 2.0) * 0.1
        tx = cx + 70 + math.cos(tail_ang) * 35
        ty = cy + 20 + math.sin(tail_ang) * 35
        pygame.draw.line(surf, patient["ear_color"], (cx + 60, cy + 20), (int(tx), int(ty)), 12)

        # Body
        pygame.draw.ellipse(surf, patient["color"], (cx - 70, cy - 30, 140, 90))
        pygame.draw.ellipse(surf, patient["belly_color"], (cx - 40, cy - 10, 80, 60))

        # Head
        pygame.draw.circle(surf, patient["color"], (cx - 50, cy - 35), 45)

        # Ears
        if patient["id"] == "bunny":
            pygame.draw.ellipse(surf, patient["color"], (cx - 80, cy - 110, 20, 50))
            pygame.draw.ellipse(surf, patient["color"], (cx - 50, cy - 110, 20, 50))
            pygame.draw.ellipse(surf, patient["ear_color"], (cx - 76, cy - 100, 12, 36))
            pygame.draw.ellipse(surf, patient["ear_color"], (cx - 46, cy - 100, 12, 36))
        else:
            # Floppy / Cat ears
            pygame.draw.circle(surf, patient["ear_color"], (cx - 85, cy - 50), 18)
            pygame.draw.circle(surf, patient["ear_color"], (cx - 25, cy - 50), 18)

        # Eyes & Nose
        eye_y = cy - 40
        if is_fully_healed:
            # Happy arched eyes ^ ^
            pygame.draw.arc(surf, (20, 20, 30), (cx - 70, eye_y - 8, 16, 16), 0.2, 2.9, 3)
            pygame.draw.arc(surf, (20, 20, 30), (cx - 45, eye_y - 8, 16, 16), 0.2, 2.9, 3)
        else:
            pygame.draw.circle(surf, (20, 20, 30), (cx - 62, eye_y), 6)
            pygame.draw.circle(surf, (20, 20, 30), (cx - 38, eye_y), 6)
            pygame.draw.circle(surf, (255, 255, 255), (cx - 60, eye_y - 2), 2)
            pygame.draw.circle(surf, (255, 255, 255), (cx - 36, eye_y - 2), 2)

        # Nose & Smile
        pygame.draw.circle(surf, (20, 20, 30), (cx - 50, cy - 25), 5)
        pygame.draw.arc(surf, (20, 20, 30), (cx - 58, cy - 28, 16, 14), 3.4, 6.0, 2)

        # Mud splatters if not washed
        if not is_washed:
            pygame.draw.circle(surf, (120, 53, 15), (cx + 10, cy + 10), 12)
            pygame.draw.circle(surf, (120, 53, 15), (cx + 35, cy + 25), 8)
            pygame.draw.circle(surf, (120, 53, 15), (cx - 20, cy + 30), 10)

        # Bandage on back if applied
        if has_bandage:
            b_rect = pygame.Rect(cx + 10, cy - 10, 36, 20)
            pygame.draw.rect(surf, (254, 205, 211), b_rect, border_radius=4)
            pygame.draw.rect(surf, (244, 63, 94), b_rect, width=2, border_radius=4)
            pygame.draw.line(surf, (244, 63, 94), (cx + 28, cy - 6), (cx + 28, cy + 6), 2)

        # 4. Care Checklist Badges (Top Right Area)
        checklist_items = [
            ("🩺 Visita", has_examined),
            ("🧼 Bagnetto", is_washed),
            ("🩹 Cerotto", has_bandage),
            ("🥣 Pappa", has_eaten),
            ("💖 Coccole", is_cuddled),
        ]
        for idx, (lbl, done) in enumerate(checklist_items):
            bx = 760
            by = 120 + idx * 42
            badge_rect = pygame.Rect(bx, by, 180, 34)
            bg = (220, 252, 231) if done else (241, 245, 249)
            border = (34, 197, 94) if done else (203, 213, 225)
            pygame.draw.rect(surf, bg, badge_rect, border_radius=8)
            pygame.draw.rect(surf, border, badge_rect, width=2, border_radius=8)
            txt = f"✓ {lbl}" if done else f"○ {lbl}"
            txt_col = (22, 101, 52) if done else (100, 116, 139)
            c_surf = typography.render(txt, FontRole.CONTROL, 14, txt_col)
            surf.blit(c_surf, (bx + 12, by + 7))

        # 5. Draw Particles
        for p in particles:
            cur_sz = max(2.0, p["size"] * max(0.0, min(1.0, p["life"])))
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), int(cur_sz))

        # 6. Top HUD
        title_surf = typography.render(t("activity.title", "La Clinica dei Cuccioli"), FontRole.DISPLAY, 24, (30, 41, 59))
        surf.blit(title_surf, (80, 20))

        p_name = patient["name_it"] if active_locale == "it" else patient["name_en"]
        p_surf = typography.render(f"Paziente: {p_name}", FontRole.TITLE, 20, (236, 72, 153))
        surf.blit(p_surf, (430, 22))

        # 7. Bottom Tool Toolbar
        tool_y = REFERENCE_HEIGHT - 58
        for t_idx, tool in enumerate(TOOLS):
            bx = 120 + t_idx * 155
            b_rect = pygame.Rect(bx, tool_y, 140, 44)
            is_sel = selected_tool_idx == t_idx
            bg_col = tool["color"] if is_sel else (255, 255, 255)
            txt_col = (255, 255, 255) if is_sel else (30, 41, 59)
            pygame.draw.rect(surf, bg_col, b_rect, border_radius=12)
            pygame.draw.rect(surf, tool["color"], b_rect, width=3 if is_sel else 2, border_radius=12)
            lbl = tool["name_it"] if active_locale == "it" else tool["name_en"]
            lbl_surf = typography.render(lbl, FontRole.CONTROL, 16, txt_col)
            surf.blit(lbl_surf, (b_rect.centerx - lbl_surf.get_width() // 2, b_rect.centery - lbl_surf.get_height() // 2))

        # 8. Victory Modal
        if is_victory:
            overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 15, 30, 200))
            surf.blit(overlay, (0, 0))

            card = pygame.Rect(REFERENCE_WIDTH // 2 - 220, REFERENCE_HEIGHT // 2 - 140, 440, 280)
            pygame.draw.rect(surf, (30, 41, 59), card, border_radius=20)
            pygame.draw.rect(surf, (254, 202, 87), card, width=3, border_radius=20)

            v_title = typography.render(t("victory.title", "Il cucciolo è guarito! 🐶💖"), FontRole.DISPLAY, 22, (254, 202, 87))
            surf.blit(v_title, (card.centerx - v_title.get_width() // 2, card.top + 30))

            v_sub = typography.render(t("victory.subtitle", "Sei una dottoressa fantastica!"), FontRole.BODY, 18, (241, 245, 249))
            surf.blit(v_sub, (card.centerx - v_sub.get_width() // 2, card.top + 75))

            for i in range(3):
                star_x = card.centerx - 50 + i * 50
                star_y = card.top + 130
                pygame.draw.circle(surf, (254, 202, 87), (star_x, star_y), 18)

            again_btn = pygame.Rect(card.centerx - 110, card.bottom - 65, 220, 46)
            pygame.draw.rect(surf, (34, 197, 94), again_btn, border_radius=14)
            again_lbl = typography.render(t("btn.next_patient", "🐾 Prossimo Paziente!"), FontRole.CONTROL, 18, (255, 255, 255))
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
                "patient_idx": patient_idx,
                "timestamp": time.time(),
            })
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
