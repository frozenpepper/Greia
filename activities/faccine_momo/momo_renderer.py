"""Visual rendering and facial expressions for Le Faccine di Momo."""

from __future__ import annotations

import math
from typing import Final

import pygame

if __package__:
    from .momo_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        Emotion,
        GameMode,
        MomoModel,
        MomoParticle,
    )
else:
    from momo_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        Emotion,
        GameMode,
        MomoModel,
        MomoParticle,
    )

# Palette
COLOR_WALLPAPER_TOP: Final = (255, 243, 224)
COLOR_WALLPAPER_BOT: Final = (255, 224, 178)

COLOR_MIRROR_FRAME: Final = (255, 202, 40)
COLOR_MIRROR_INNER: Final = (255, 236, 179)
COLOR_MIRROR_GLASS: Final = (225, 245, 254)

COLOR_MOMO_BODY: Final = (186, 104, 200)
COLOR_MOMO_SHADOW: Final = (156, 77, 174)
COLOR_MOMO_EARS: Final = (171, 71, 188)
COLOR_MOMO_CHEEKS: Final = (255, 138, 128)
COLOR_MOMO_EYES: Final = (45, 25, 55)

EMOTION_ACCENTS: Final = {
    Emotion.HAPPY: (255, 193, 7),
    Emotion.SAD: (66, 165, 245),
    Emotion.SURPRISED: (255, 112, 67),
    Emotion.SILLY: (126, 87, 194),
    Emotion.ANGRY: (239, 83, 80),
    Emotion.SLEEPY: (92, 107, 192),
}

EMOTION_LABELS: Final = {
    Emotion.HAPPY: "FELICE",
    Emotion.SAD: "TRISTE",
    Emotion.SURPRISED: "SORPRESO",
    Emotion.SILLY: "BUFFO",
    Emotion.ANGRY: "ARRABBIATO",
    Emotion.SLEEPY: "SONNO",
}


class MomoRenderer:
    """Render the magic mirror, animated facial features of Momo, and generous touch controls."""

    def __init__(self) -> None:
        self._reference_surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        self.mirror_center = (512, 280)
        self.mirror_radius_x = 195
        self.mirror_radius_y = 215

        # Hitboxes
        self.momo_face_rect = pygame.Rect(512 - 130, 280 - 140, 260, 280)
        self.momo_left_cheek = pygame.Rect(512 - 100, 280 + 15, 60, 50)
        self.momo_right_cheek = pygame.Rect(512 + 40, 280 + 15, 60, 50)

        # Mode toggle button (top center)
        self.mode_button_rect = pygame.Rect(512 - 120, 20, 240, 54)

        # Free mirror emotion buttons (3 on left, 3 on right)
        btn_sz = 94
        self.left_buttons: list[tuple[Emotion, pygame.Rect]] = [
            (Emotion.HAPPY, pygame.Rect(40, 110, btn_sz, btn_sz)),
            (Emotion.SURPRISED, pygame.Rect(40, 235, btn_sz, btn_sz)),
            (Emotion.SILLY, pygame.Rect(40, 360, btn_sz, btn_sz)),
        ]
        self.right_buttons: list[tuple[Emotion, pygame.Rect]] = [
            (Emotion.SAD, pygame.Rect(REFERENCE_WIDTH - 40 - btn_sz, 110, btn_sz, btn_sz)),
            (Emotion.ANGRY, pygame.Rect(REFERENCE_WIDTH - 40 - btn_sz, 235, btn_sz, btn_sz)),
            (Emotion.SLEEPY, pygame.Rect(REFERENCE_WIDTH - 40 - btn_sz, 360, btn_sz, btn_sz)),
        ]

        # Quiz choice buttons (bottom center)
        q_w, q_h = 220, 84
        self.quiz_choice_rects = [
            pygame.Rect(512 - q_w - 20, 480, q_w, q_h),
            pygame.Rect(512 + 20, 480, q_w, q_h),
        ]

    def render(self, target_surface: pygame.Surface, model: MomoModel) -> None:
        ref = self._reference_surf

        # 1. Cheerful Background Wallpaper
        self._render_background(ref)

        # 2. Ornate Magic Mirror
        self._render_mirror(ref, model)

        # 3. Momo Monster inside Mirror
        self._render_momo(ref, model)

        # 4. Particles (hearts, confetti, steam, Zzz)
        self._render_particles(ref, model)

        # 5. Pre-reader UI Controls
        self._render_ui(ref, model)

        # Scale to physical window
        sw, sh = target_surface.get_size()
        if (sw, sh) == (REFERENCE_WIDTH, REFERENCE_HEIGHT):
            target_surface.blit(ref, (0, 0))
        else:
            scaled = pygame.transform.smoothscale(ref, (sw, sh))
            target_surface.blit(scaled, (0, 0))

    def _render_background(self, surf: pygame.Surface) -> None:
        # Vertical pastel gradient
        for y in range(0, REFERENCE_HEIGHT, 8):
            frac = y / REFERENCE_HEIGHT
            r = int(COLOR_WALLPAPER_TOP[0] + (COLOR_WALLPAPER_BOT[0] - COLOR_WALLPAPER_TOP[0]) * frac)
            g = int(COLOR_WALLPAPER_TOP[1] + (COLOR_WALLPAPER_BOT[1] - COLOR_WALLPAPER_TOP[1]) * frac)
            b = int(COLOR_WALLPAPER_TOP[2] + (COLOR_WALLPAPER_BOT[2] - COLOR_WALLPAPER_TOP[2]) * frac)
            pygame.draw.rect(surf, (r, g, b), (0, y, REFERENCE_WIDTH, 8))

        # Subtle playful wallpaper polka dots
        dot_color = (255, 255, 255, 80)
        for row in range(5):
            for col in range(12):
                ox = 40 + col * 90 + (45 if row % 2 == 1 else 0)
                oy = 40 + row * 120
                pygame.draw.circle(surf, (255, 238, 205), (ox, oy), 8)

    def _render_mirror(self, surf: pygame.Surface, model: MomoModel) -> None:
        cx, cy = self.mirror_center
        rx, ry = self.mirror_radius_x, self.mirror_radius_y

        # Mirror outer frame shadow
        pygame.draw.ellipse(surf, (210, 160, 40), (cx - rx - 18, cy - ry - 14, (rx + 18) * 2, (ry + 18) * 2))
        # Golden Frame
        pygame.draw.ellipse(surf, COLOR_MIRROR_FRAME, (cx - rx - 14, cy - ry - 14, (rx + 14) * 2, (ry + 14) * 2))
        # Inner Frame groove
        pygame.draw.ellipse(surf, COLOR_MIRROR_INNER, (cx - rx - 4, cy - ry - 4, (rx + 4) * 2, (ry + 4) * 2))
        # Glass Surface
        pygame.draw.ellipse(surf, COLOR_MIRROR_GLASS, (cx - rx, cy - ry, rx * 2, ry * 2))

        # Mirror glass highlight reflection arc
        pygame.draw.arc(surf, (255, 255, 255), (cx - rx + 16, cy - ry + 16, (rx - 16) * 2, (ry - 16) * 2), math.pi * 0.75, math.pi * 1.15, 6)

    def _render_momo(self, surf: pygame.Surface, model: MomoModel) -> None:
        cx = self.mirror_center[0] + int(model.shake_offset * math.sin(model.anim_timer * 25.0))
        cy = self.mirror_center[1] - int(model.hop_offset)
        t = model.anim_timer
        emo = model.emotion

        # 1. Cute Fluffy Horns/Tufts (wiggle gently)
        ear_wiggle = math.sin(t * 5.0) * 4
        # Left ear
        pygame.draw.ellipse(surf, COLOR_MOMO_EARS, (cx - 105 + ear_wiggle, cy - 170, 52, 70))
        pygame.draw.ellipse(surf, (206, 147, 216), (cx - 97 + ear_wiggle, cy - 160, 36, 48))
        # Right ear
        pygame.draw.ellipse(surf, COLOR_MOMO_EARS, (cx + 53 - ear_wiggle, cy - 170, 52, 70))
        pygame.draw.ellipse(surf, (206, 147, 216), (cx + 61 - ear_wiggle, cy - 160, 36, 48))

        # 2. Main Head & Body
        head_w, head_h = 240, 250
        # Soft shadow underneath
        pygame.draw.ellipse(surf, COLOR_MOMO_SHADOW, (cx - head_w // 2, cy - head_h // 2 + 10, head_w, head_h))
        # Head surface
        pygame.draw.ellipse(surf, COLOR_MOMO_BODY, (cx - head_w // 2, cy - head_h // 2, head_w, head_h))

        # 3. Rosy Cheeks
        cheek_alpha = (255, 170, 170)
        pygame.draw.circle(surf, COLOR_MOMO_CHEEKS, (cx - 75, cy + 30), 22)
        pygame.draw.circle(surf, COLOR_MOMO_CHEEKS, (cx + 75, cy + 30), 22)
        if model.is_comforted or emo == Emotion.HAPPY:
            # Extra cute blushing glow
            pygame.draw.circle(surf, cheek_alpha, (cx - 75, cy + 30), 14)
            pygame.draw.circle(surf, cheek_alpha, (cx + 75, cy + 30), 14)

        # 4. Eyes & Eyebrows (according to emotion)
        self._render_eyes(surf, cx, cy, model)

        # 5. Mouth & Expression
        self._render_mouth(surf, cx, cy, model)

    def _render_eyes(self, surf: pygame.Surface, cx: int, cy: int, model: MomoModel) -> None:
        emo = model.emotion
        eye_y = cy - 20
        lx, rx = cx - 48, cx + 48

        if model.is_comforted or emo == Emotion.HAPPY:
            # Cheerful closed crescent eyes ^ ^
            pygame.draw.arc(surf, COLOR_MOMO_EYES, (lx - 20, eye_y - 12, 40, 26), math.pi * 0.15, math.pi * 0.85, 5)
            pygame.draw.arc(surf, COLOR_MOMO_EYES, (rx - 20, eye_y - 12, 40, 26), math.pi * 0.15, math.pi * 0.85, 5)

        elif emo == Emotion.SAD:
            # Drooping sad eyes with tear
            pygame.draw.arc(surf, COLOR_MOMO_EYES, (lx - 18, eye_y - 6, 36, 24), math.pi * 1.15, math.pi * 1.85, 4)
            pygame.draw.arc(surf, COLOR_MOMO_EYES, (rx - 18, eye_y - 6, 36, 24), math.pi * 1.15, math.pi * 1.85, 4)
            # Tear on right cheek
            tear_y = eye_y + 20 + int((model.anim_timer * 30.0) % 35)
            pygame.draw.ellipse(surf, (66, 165, 245), (rx + 14, tear_y, 8, 14))

        elif emo == Emotion.SURPRISED:
            # Big wide round open white eyes with dark pupils
            for ex in (lx, rx):
                pygame.draw.circle(surf, (255, 255, 255), (ex, eye_y), 24)
                pygame.draw.circle(surf, COLOR_MOMO_EYES, (ex, eye_y), 12)
                pygame.draw.circle(surf, (255, 255, 255), (ex - 4, eye_y - 4), 4)

        elif emo == Emotion.SILLY:
            # Left eye wide open with crazy pupil, Right eye winking closed
            pygame.draw.circle(surf, (255, 255, 255), (lx, eye_y), 22)
            pygame.draw.circle(surf, COLOR_MOMO_EYES, (lx + 2, eye_y - 2), 10)
            pygame.draw.circle(surf, (255, 255, 255), (lx, eye_y - 4), 3)
            # Winking right eye
            pygame.draw.line(surf, COLOR_MOMO_EYES, (rx - 18, eye_y), (rx + 18, eye_y), 5)
            pygame.draw.line(surf, COLOR_MOMO_EYES, (rx - 14, eye_y - 8), (rx + 14, eye_y + 8), 4)

        elif emo == Emotion.ANGRY:
            # Furrowed eyes and angled eyebrows
            pygame.draw.line(surf, (136, 14, 79), (lx - 24, eye_y - 18), (lx + 18, eye_y - 4), 6)
            pygame.draw.line(surf, (136, 14, 79), (rx + 24, eye_y - 18), (rx - 18, eye_y - 4), 6)
            pygame.draw.circle(surf, (255, 255, 255), (lx, eye_y), 18)
            pygame.draw.circle(surf, COLOR_MOMO_EYES, (lx + 4, eye_y), 9)
            pygame.draw.circle(surf, (255, 255, 255), (rx, eye_y), 18)
            pygame.draw.circle(surf, COLOR_MOMO_EYES, (rx - 4, eye_y), 9)

        elif emo == Emotion.SLEEPY:
            # Peaceful horizontal closed lines
            pygame.draw.line(surf, COLOR_MOMO_EYES, (lx - 16, eye_y), (lx + 16, eye_y), 4)
            pygame.draw.line(surf, COLOR_MOMO_EYES, (rx - 16, eye_y), (rx + 16, eye_y), 4)

    def _render_mouth(self, surf: pygame.Surface, cx: int, cy: int, model: MomoModel) -> None:
        emo = model.emotion
        my = cy + 45

        if model.is_comforted:
            # Sweet gentle smile after cuddle
            pygame.draw.arc(surf, (136, 14, 79), (cx - 30, my - 15, 60, 30), math.pi * 1.15, math.pi * 1.85, 4)

        elif emo == Emotion.HAPPY:
            # Big open grinning mouth with single cute white tooth
            pygame.draw.polygon(
                surf,
                (194, 24, 91),
                [(cx - 38, my), (cx + 38, my), (cx + 25, my + 38), (cx - 25, my + 38)],
            )
            pygame.draw.arc(surf, (136, 14, 79), (cx - 40, my - 10, 80, 52), math.pi * 1.0, math.pi * 2.0, 4)
            # White tooth
            pygame.draw.rect(surf, (255, 255, 255), (cx - 8, my, 16, 12), border_radius=2)

        elif emo == Emotion.SAD:
            # Downward curved frown
            pygame.draw.arc(surf, (136, 14, 79), (cx - 32, my + 5, 64, 30), math.pi * 0.15, math.pi * 0.85, 4)

        elif emo == Emotion.SURPRISED:
            # Big round open 'O' mouth
            pygame.draw.ellipse(surf, (194, 24, 91), (cx - 18, my - 6, 36, 44))
            pygame.draw.ellipse(surf, (136, 14, 79), (cx - 18, my - 6, 36, 44), 3)

        elif emo == Emotion.SILLY:
            # Wide grin with big tongue out (bleeeh!)
            pygame.draw.arc(surf, (136, 14, 79), (cx - 36, my - 10, 72, 36), math.pi * 1.1, math.pi * 1.9, 4)
            # Pink floppy tongue
            pygame.draw.ellipse(surf, (255, 64, 129), (cx - 16, my + 6, 32, 38))
            pygame.draw.line(surf, (216, 27, 96), (cx, my + 10), (cx, my + 34), 2)

        elif emo == Emotion.ANGRY:
            # Grumpy pouty zig-zag mouth
            points = [(cx - 28, my + 10), (cx - 10, my + 5), (cx + 10, my + 12), (cx + 28, my + 6)]
            pygame.draw.lines(surf, (136, 14, 79), False, points, 4)

        elif emo == Emotion.SLEEPY:
            # Soft yawning oval
            pygame.draw.ellipse(surf, (194, 24, 91), (cx - 14, my, 28, 22))
            pygame.draw.ellipse(surf, (136, 14, 79), (cx - 14, my, 28, 22), 2)

    def _render_particles(self, surf: pygame.Surface, model: MomoModel) -> None:
        for p in model.particles:
            if p.kind == "heart":
                self._draw_heart(surf, int(p.x), int(p.y), p.size, p.color)
            elif p.kind == "star":
                self._draw_star(surf, int(p.x), int(p.y), p.size, p.color)
            elif p.kind == "confetti":
                pygame.draw.rect(surf, p.color, (int(p.x), int(p.y), int(p.size), int(p.size * 0.7)))
            elif p.kind == "puff":
                pygame.draw.circle(surf, p.color, (int(p.x), int(p.y)), int(p.size))
            elif p.kind == "zzz":
                self._draw_zzz(surf, int(p.x), int(p.y), int(p.size), p.color)

    def _draw_heart(self, surf: pygame.Surface, x: int, y: int, size: float, color: tuple[int, int, int]) -> None:
        r = size * 0.45
        pygame.draw.circle(surf, color, (int(x - r * 0.7), int(y - r * 0.4)), int(r))
        pygame.draw.circle(surf, color, (int(x + r * 0.7), int(y - r * 0.4)), int(r))
        pts = [(x - r * 1.5, y - r * 0.2), (x + r * 1.5, y - r * 0.2), (x, y + r * 1.8)]
        pygame.draw.polygon(surf, color, pts)

    def _draw_star(self, surf: pygame.Surface, cx: int, cy: int, size: float, color: tuple[int, int, int]) -> None:
        points = []
        for i in range(10):
            ang = i * (math.pi / 5) - math.pi / 2
            r = size if i % 2 == 0 else size * 0.45
            points.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
        pygame.draw.polygon(surf, color, points)

    def _draw_zzz(self, surf: pygame.Surface, x: int, y: int, size: int, color: tuple[int, int, int]) -> None:
        pygame.draw.line(surf, color, (x, y), (x + size, y), 3)
        pygame.draw.line(surf, color, (x + size, y), (x, y + size), 3)
        pygame.draw.line(surf, color, (x, y + size), (x + size, y + size), 3)

    def _render_ui(self, surf: pygame.Surface, model: MomoModel) -> None:
        font_large = pygame.font.Font(None, 28)
        font_small = pygame.font.Font(None, 20)

        # 1. Mode Toggle Button (Top Center)
        is_quiz = model.mode == GameMode.GUESS_EMOTION
        mode_rect = self.mode_button_rect
        pygame.draw.rect(surf, (255, 255, 255), mode_rect, border_radius=27)
        pygame.draw.rect(surf, (255, 145, 0) if is_quiz else (171, 71, 188), mode_rect, 4, border_radius=27)
        mode_text = "COME SI SENTE?" if is_quiz else "SPECCHIO LIBERO"
        lbl = font_large.render(mode_text, True, (60, 60, 60))
        surf.blit(lbl, lbl.get_rect(center=mode_rect.center))

        # 2. Controls in Free Mirror Mode
        if model.mode == GameMode.FREE_MIRROR:
            for emo, rect in self.left_buttons + self.right_buttons:
                is_active = model.emotion == emo
                accent = EMOTION_ACCENTS[emo]
                bg = (255, 255, 255) if is_active else (248, 245, 250)
                pygame.draw.circle(surf, bg, rect.center, rect.width // 2)
                pygame.draw.circle(surf, accent if is_active else (200, 200, 210), rect.center, rect.width // 2, 4 if is_active else 2)

                # Icon preview
                self._draw_emotion_icon(surf, emo, rect.centerx, rect.centery - 8)
                lbl_name = font_small.render(EMOTION_LABELS[emo], True, accent if is_active else (80, 80, 80))
                surf.blit(lbl_name, lbl_name.get_rect(center=(rect.centerx, rect.centery + 24)))

        # 3. Controls in Quiz Mode
        else:
            for idx, choice_emo in enumerate(model.quiz_choices):
                rect = self.quiz_choice_rects[idx]
                accent = EMOTION_ACCENTS[choice_emo]
                pygame.draw.rect(surf, (255, 255, 255), rect, border_radius=24)
                pygame.draw.rect(surf, accent, rect, 4, border_radius=24)

                self._draw_emotion_icon(surf, choice_emo, rect.centerx - 45, rect.centery)
                lbl_ch = font_large.render(EMOTION_LABELS[choice_emo], True, (50, 50, 50))
                surf.blit(lbl_ch, lbl_ch.get_rect(center=(rect.centerx + 30, rect.centery)))

    def _draw_emotion_icon(self, surf: pygame.Surface, emo: Emotion, cx: int, cy: int) -> None:
        # Mini expressive face icon inside button
        pygame.draw.circle(surf, (255, 235, 120), (cx, cy), 18)
        if emo == Emotion.HAPPY:
            pygame.draw.arc(surf, (40, 40, 40), (cx - 10, cy - 8, 20, 16), math.pi * 1.1, math.pi * 1.9, 2)
            pygame.draw.circle(surf, (40, 40, 40), (cx - 6, cy - 3), 2)
            pygame.draw.circle(surf, (40, 40, 40), (cx + 6, cy - 3), 2)
        elif emo == Emotion.SAD:
            pygame.draw.arc(surf, (40, 40, 40), (cx - 8, cy + 2, 16, 12), math.pi * 0.1, math.pi * 0.9, 2)
            pygame.draw.circle(surf, (40, 40, 40), (cx - 5, cy - 3), 2)
            pygame.draw.circle(surf, (40, 40, 40), (cx + 5, cy - 3), 2)
        elif emo == Emotion.SURPRISED:
            pygame.draw.circle(surf, (40, 40, 40), (cx, cy + 5), 4)
            pygame.draw.circle(surf, (40, 40, 40), (cx - 6, cy - 4), 2)
            pygame.draw.circle(surf, (40, 40, 40), (cx + 6, cy - 4), 2)
        elif emo == Emotion.SILLY:
            pygame.draw.arc(surf, (40, 40, 40), (cx - 8, cy, 16, 10), math.pi * 1.1, math.pi * 1.9, 2)
            pygame.draw.circle(surf, (255, 64, 129), (cx, cy + 7), 4)
            pygame.draw.circle(surf, (40, 40, 40), (cx - 6, cy - 3), 2)
            pygame.draw.line(surf, (40, 40, 40), (cx + 4, cy - 3), (cx + 8, cy - 3), 2)
        elif emo == Emotion.ANGRY:
            pygame.draw.line(surf, (40, 40, 40), (cx - 8, cy - 7), (cx - 2, cy - 4), 2)
            pygame.draw.line(surf, (40, 40, 40), (cx + 8, cy - 7), (cx + 2, cy - 4), 2)
            pygame.draw.circle(surf, (40, 40, 40), (cx - 5, cy - 2), 2)
            pygame.draw.circle(surf, (40, 40, 40), (cx + 5, cy - 2), 2)
            pygame.draw.line(surf, (40, 40, 40), (cx - 6, cy + 6), (cx + 6, cy + 4), 2)
        elif emo == Emotion.SLEEPY:
            pygame.draw.line(surf, (40, 40, 40), (cx - 8, cy - 3), (cx - 2, cy - 3), 2)
            pygame.draw.line(surf, (40, 40, 40), (cx + 2, cy - 3), (cx + 8, cy - 3), 2)
            pygame.draw.circle(surf, (40, 40, 40), (cx, cy + 4), 3)
