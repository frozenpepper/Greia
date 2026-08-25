from __future__ import annotations

import io
import math
from pathlib import Path
import random
import struct
import time
import wave

import pygame

from greia_platform.child_text import display_text
from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_profile_locale,
    get_storage,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics, is_home_clicked, mix
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
STORAGE_KEY = "cucciolo_mio.state.v3"

# Sweet Nursery Palette
ROOM_WALL = (255, 245, 238)
ROOM_FLOOR = (235, 195, 160)
NIGHT_WALL = (25, 25, 45)
NIGHT_FLOOR = (18, 18, 30)
WHITE = (255, 255, 255)
DARK_TEXT = (50, 40, 35)
GOLD = (255, 215, 50)
PINK = (255, 120, 165)
PASTEL_PINK = (255, 215, 230)
ACCENT_BLUE = (80, 175, 245)


def _synth_wav(samples: list[int], rate: int = 22050) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        raw = b"".join(struct.pack("<h", max(-32767, min(32767, s))) for s in samples)
        w.writeframes(raw)
    return buf.getvalue()


class SoundManager:
    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self._init_sounds()
            self._enabled = True
        except Exception:
            self._enabled = False

    def _init_sounds(self) -> None:
        pop_samples = [
            int(math.sin(2 * math.pi * (500 + (1000 - i) * 0.9) * (i / 22050.0)) * max(0.0, 1.0 - (i / 22050.0) / 0.05) * 14000)
            for i in range(1200)
        ]
        self._sounds["pop"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(pop_samples)))

        squeak_samples = []
        for i in range(3500):
            t = i / 22050.0
            f = 1200.0 + math.sin(t * 90.0) * 400.0
            env = max(0.0, 1.0 - t / 0.16)
            squeak_samples.append(int(math.sin(2 * math.pi * f * t) * env * 12000))
        self._sounds["squeak"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(squeak_samples)))

        crunch_samples = []
        for i in range(4000):
            t = i / 22050.0
            f = 250.0 + (random.random() * 300.0)
            env = max(0.0, 1.0 - t / 0.18)
            crunch_samples.append(int(math.sin(2 * math.pi * f * t) * env * 13000))
        self._sounds["crunch"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(crunch_samples)))

        sp_samples = []
        for i in range(7000):
            t = i / 22050.0
            f = 880.0 + math.sin(t * 60.0) * 350.0
            env = max(0.0, 1.0 - t / 0.32)
            sp_samples.append(int(math.sin(2 * math.pi * f * t) * env * 11000))
        self._sounds["sparkle"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(sp_samples)))

    def play(self, name: str) -> None:
        if self._enabled and name in self._sounds:
            try:
                self._sounds[name].play()
            except Exception:
                pass


class Particle:
    def __init__(self, x: float, y: float, symbol: str, color: tuple[int, int, int]) -> None:
        self.x = x
        self.y = y
        self.symbol = symbol
        self.color = color
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2.0, 5.5)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.decay = random.uniform(0.03, 0.05)

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay
        return self.life > 0

    def draw(self, surface: pygame.Surface, typography: GreiaTypography) -> None:
        if self.life > 0:
            sz = max(12, int(28 * self.life))
            p_surf = typography.render(self.symbol, FontRole.DISPLAY, sz, self.color)
            surface.blit(p_surf, (int(self.x) - p_surf.get_width() // 2, int(self.y) - p_surf.get_height() // 2))


class PetEntity:
    def __init__(self, x: float, y: float, species: str = "cat") -> None:
        self.x = x
        self.y = y
        self.target_x = x
        self.species = species
        self.accessory = "bow"
        self.is_sleeping = False
        self.blink_timer = random.uniform(2.0, 4.5)
        self.chew_timer = 0.0
        self.wag_angle = 0.0
        self.bubble_count = 0

    def update(self) -> None:
        dx = self.target_x - self.x
        self.x += dx * 0.12

        self.wag_angle += 0.15
        self.blink_timer -= 0.03
        if self.blink_timer <= 0:
            self.blink_timer = random.uniform(2.5, 5.0)

        if self.chew_timer > 0:
            self.chew_timer -= 0.04

    def draw(self, surface: pygame.Surface) -> None:
        px = int(self.x)
        py = int(self.y)

        body_col = (255, 175, 110) if self.species == "cat" else ((240, 235, 230) if self.species == "bunny" else (225, 160, 100))
        tummy_col = (255, 250, 245)

        tail_wag = math.sin(self.wag_angle) * 16.0
        if self.species == "cat":
            pygame.draw.circle(surface, body_col, (px + 60 + int(tail_wag * 0.5), py + 35), 14)
        elif self.species == "puppy":
            pygame.draw.ellipse(surface, (190, 120, 60), (px + 45, py + 20 - int(tail_wag), 20, 36))
        else:
            pygame.draw.circle(surface, WHITE, (px + 50, py + 35), 16)

        pygame.draw.ellipse(surface, body_col, (px - 50, py - 20, 100, 90))
        pygame.draw.ellipse(surface, tummy_col, (px - 32, py - 10, 64, 70))

        pygame.draw.circle(surface, tummy_col, (px - 30, py + 65), 14)
        pygame.draw.circle(surface, tummy_col, (px + 30, py + 65), 14)

        pygame.draw.ellipse(surface, body_col, (px - 55, py - 95, 110, 95))

        if self.species == "cat":
            pygame.draw.polygon(surface, body_col, [(px - 50, py - 75), (px - 45, py - 130), (px - 10, py - 85)])
            pygame.draw.polygon(surface, PINK, [(px - 44, py - 80), (px - 40, py - 120), (px - 16, py - 88)])
            pygame.draw.polygon(surface, body_col, [(px + 10, py - 85), (px + 45, py - 130), (px + 50, py - 75)])
            pygame.draw.polygon(surface, PINK, [(px + 16, py - 88), (px + 40, py - 120), (px + 44, py - 80)])
        elif self.species == "bunny":
            pygame.draw.ellipse(surface, body_col, (px - 45, py - 170, 32, 90))
            pygame.draw.ellipse(surface, PINK, (px - 37, py - 160, 16, 70))
            pygame.draw.ellipse(surface, body_col, (px + 15, py - 170, 32, 90))
            pygame.draw.ellipse(surface, PINK, (px + 23, py - 160, 16, 70))
        else:
            pygame.draw.ellipse(surface, (170, 105, 50), (px - 65, py - 85, 34, 75))
            pygame.draw.ellipse(surface, (170, 105, 50), (px + 31, py - 85, 34, 75))

        pygame.draw.ellipse(surface, tummy_col, (px - 38, py - 45, 76, 45))

        pygame.draw.circle(surface, (255, 130, 160), (px - 36, py - 30), 10)
        pygame.draw.circle(surface, (255, 130, 160), (px + 36, py - 30), 10)

        if self.is_sleeping:
            pygame.draw.arc(surface, DARK_TEXT, (px - 38, py - 60, 24, 18), 0, math.pi, 3)
            pygame.draw.arc(surface, DARK_TEXT, (px + 14, py - 60, 24, 18), 0, math.pi, 3)
        elif self.blink_timer > 0.18:
            pygame.draw.ellipse(surface, (30, 25, 35), (px - 36, py - 65, 24, 30))
            pygame.draw.ellipse(surface, (30, 25, 35), (px + 12, py - 65, 24, 30))
            pygame.draw.circle(surface, WHITE, (px - 28, py - 58), 6)
            pygame.draw.circle(surface, WHITE, (px - 20, py - 48), 3)
            pygame.draw.circle(surface, WHITE, (px + 20, py - 58), 6)
            pygame.draw.circle(surface, WHITE, (px + 28, py - 48), 3)
        else:
            pygame.draw.line(surface, DARK_TEXT, (px - 36, py - 50), (px - 14, py - 50), 3)
            pygame.draw.line(surface, DARK_TEXT, (px + 14, py - 50), (px + 36, py - 50), 3)

        pygame.draw.polygon(surface, (245, 110, 140), [(px, py - 34), (px - 6, py - 40), (px + 6, py - 40)])

        if self.chew_timer > 0:
            chew_h = int(abs(math.sin(self.chew_timer * 18.0)) * 8) + 2
            pygame.draw.ellipse(surface, (240, 80, 110), (px - 10, py - 30, 20, chew_h))
        else:
            pygame.draw.arc(surface, DARK_TEXT, (px - 14, py - 34, 14, 12), math.pi, 2 * math.pi, 2)
            pygame.draw.arc(surface, DARK_TEXT, (px, py - 34, 14, 12), math.pi, 2 * math.pi, 2)

        if self.accessory == "bow":
            bx, by = px - 35, py - 90
            pygame.draw.polygon(surface, PINK, [(bx, by), (bx - 14, by - 10), (bx - 14, by + 10)])
            pygame.draw.polygon(surface, PINK, [(bx, by), (bx + 14, by - 10), (bx + 14, by + 10)])
            pygame.draw.circle(surface, (255, 80, 120), (bx, by), 6)
        elif self.accessory == "crown":
            cx, cy = px, py - 100
            pygame.draw.polygon(surface, GOLD, [(cx - 22, cy), (cx - 22, cy - 20), (cx - 11, cy - 8), (cx, cy - 24), (cx + 11, cy - 8), (cx + 22, cy - 20), (cx + 22, cy)])
        elif self.accessory == "glasses":
            gx, gy = px - 24, py - 50
            pygame.draw.circle(surface, (40, 40, 50), (gx, gy), 14, 3)
            pygame.draw.circle(surface, (40, 40, 50), (gx + 48, gy), 14, 3)
            pygame.draw.line(surface, (40, 40, 50), (gx + 14, gy), (gx + 34, gy), 3)
        elif self.accessory == "party_hat":
            hx, hy = px, py - 95
            pygame.draw.polygon(surface, (130, 90, 240), [(hx, hy - 45), (hx - 22, hy), (hx + 22, hy)])
            pygame.draw.circle(surface, GOLD, (hx, hy - 45), 7)


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
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    theme = get_theme()
    metrics = ChildUiMetrics.for_size(*screen.get_size())
    canvas = PygameReferenceCanvas(screen)
    typography = GreiaTypography()
    sounds = SoundManager()
    try:
        storage = get_storage()
    except Exception:
        storage = None

    def safe_emit(ev_id: str, ikey: str, payload: object = None) -> None:
        try:
            emit_activity_event(ev_id, idempotency_key=ikey, payload=payload)
        except Exception:
            pass

    package_root = Path(__file__).parent
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    profile_lang = get_profile_locale()
    context = resolve_activity_locale(profile_lang, support)
    resources = LocalizedResources(package_root, context) if context else None
    active_locale = context.selected.language if context else "it"

    pet = PetEntity(512.0, 340.0, species="cat")
    happiness = 5
    hunger = 4
    cleanliness = 5

    if storage is not None:
        try:
            saved = storage.kv_get(STORAGE_KEY, {})
            if isinstance(saved, dict):
                pet.species = str(saved.get("species", "cat"))
                pet.accessory = str(saved.get("accessory", "bow"))
                happiness = int(saved.get("happiness", 5))
                hunger = int(saved.get("hunger", 4))
                cleanliness = int(saved.get("cleanliness", 5))
        except Exception:
            pass

    active_tab = "feed"
    particles: list[Particle] = []
    bubbles: list[tuple[float, float, float]] = []

    ball_pos = [512.0, 440.0]
    ball_vel = [0.0, 0.0]
    ball_last_pos = [512.0, 440.0]
    is_dragging_ball = False

    feedback_msg = ""
    feedback_timer = 0.0

    running = True
    ready_published = False

    while running and not activity_stop_requested():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_1:
                    pet.species = "cat"
                elif event.key == pygame.K_2:
                    pet.species = "bunny"
                elif event.key == pygame.K_3:
                    pet.species = "puppy"
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                logical = canvas.pointer(event.pos)
                if logical is not None:
                    lx, ly = logical
                    if active_tab == "play" and (lx - ball_pos[0]) ** 2 + (ly - ball_pos[1]) ** 2 <= 40 ** 2:
                        is_dragging_ball = True
                        ball_vel = [0.0, 0.0]
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if is_home_clicked(screen, event.pos):
                    running = False
                    continue
                if is_dragging_ball:
                    is_dragging_ball = False
                    ball_vel[0] = max(-16.0, min(16.0, (ball_pos[0] - ball_last_pos[0]) * 0.9))
                    ball_vel[1] = max(-16.0, min(16.0, (ball_pos[1] - ball_last_pos[1]) * 0.9))
                if not _is_safe_point(screen, event.pos):
                    continue
                logical = canvas.pointer(event.pos)
                if logical is not None:
                    lx, ly = logical

                    if 470 <= lx <= 542 and 10 <= ly <= 76:
                        pet.species = "cat"
                        sounds.play("sparkle")
                    elif 550 <= lx <= 622 and 10 <= ly <= 76:
                        pet.species = "bunny"
                        sounds.play("sparkle")
                    elif 630 <= lx <= 702 and 10 <= ly <= 76:
                        pet.species = "puppy"
                        sounds.play("sparkle")

                    tabs = ["feed", "bath", "play", "sleep", "dress"]
                    for idx, tab_id in enumerate(tabs):
                        tx = 95 + idx * 170
                        if tx <= lx <= tx + 155 and 500 <= ly <= 585:
                            active_tab = tab_id
                            sounds.play("pop")
                            if active_tab == "sleep":
                                pet.is_sleeping = True
                                sounds.play("sparkle")
                                feedback_msg = resources.text("msg.sleep") if resources else display_text("Sogni d'oro... 🌙")
                                feedback_timer = 2.5
                                safe_emit("pet.tucked_in", f"sleep-{time.time()}")
                            else:
                                pet.is_sleeping = False

                    if active_tab == "feed" and 100 <= ly <= 480:
                        pet.chew_timer = 1.2
                        hunger = min(5, hunger + 1)
                        happiness = min(5, happiness + 1)
                        sounds.play("crunch")
                        for _ in range(16):
                            particles.append(Particle(pet.x, pet.y - 40, "💖", PINK))
                        feedback_msg = resources.text("msg.nom_nom") if resources else display_text("Gnam gnam! 💖")
                        feedback_timer = 2.0
                        safe_emit("pet.fed", f"feed-{time.time()}")

                    elif active_tab == "bath":
                        sounds.play("pop")
                        pet.bubble_count += 3
                        for _ in range(8):
                            bubbles.append((random.uniform(pet.x - 70, pet.x + 70), random.uniform(pet.y - 90, pet.y + 40), random.uniform(16, 30)))
                        if pet.bubble_count >= 10:
                            sounds.play("sparkle")
                            cleanliness = 5
                            happiness = min(5, happiness + 1)
                            for _ in range(20):
                                particles.append(Particle(pet.x, pet.y, "✨", GOLD))
                            feedback_msg = resources.text("msg.sparkle") if resources else display_text("Tutto pulito! ✨")
                            feedback_timer = 2.0
                            pet.bubble_count = 0
                            bubbles.clear()
                            safe_emit("pet.groomed", f"bath-{time.time()}")

                    elif active_tab == "dress":
                        acc_list = ["bow", "crown", "glasses", "party_hat", "none"]
                        cur_idx = acc_list.index(pet.accessory) if pet.accessory in acc_list else 0
                        pet.accessory = acc_list[(cur_idx + 1) % len(acc_list)]
                        sounds.play("sparkle")
                        for _ in range(14):
                            particles.append(Particle(pet.x, pet.y - 60, "🎀", PINK))
                        feedback_msg = resources.text("msg.dress") if resources else display_text("Che bel look! 🎀")
                        feedback_timer = 2.0

        if active_tab == "play":
            if is_dragging_ball and pygame.mouse.get_focused():
                mpos = pygame.mouse.get_pos()
                if _is_safe_point(screen, mpos):
                    plog = canvas.pointer(mpos)
                    if plog is not None:
                        ball_last_pos[0] = ball_pos[0]
                        ball_last_pos[1] = ball_pos[1]
                        ball_pos[0] = max(150.0, min(874.0, plog[0]))
                        ball_pos[1] = max(160.0, min(450.0, plog[1]))
                        pet.target_x = max(240.0, min(780.0, ball_pos[0]))
            else:
                ball_vel[1] += 0.45
                ball_vel[0] *= 0.99
                ball_pos[0] += ball_vel[0]
                ball_pos[1] += ball_vel[1]

                if ball_pos[0] < 160.0:
                    ball_pos[0] = 160.0
                    ball_vel[0] = abs(ball_vel[0]) * 0.78
                    sounds.play("squeak")
                elif ball_pos[0] > 864.0:
                    ball_pos[0] = 864.0
                    ball_vel[0] = -abs(ball_vel[0]) * 0.78
                    sounds.play("squeak")

                if ball_pos[1] > 450.0:
                    ball_pos[1] = 450.0
                    if abs(ball_vel[1]) > 1.5:
                        ball_vel[1] = -abs(ball_vel[1]) * 0.76
                        sounds.play("squeak")
                    else:
                        ball_vel[1] = 0.0
                        ball_vel[0] *= 0.92

                pet.target_x = max(240.0, min(780.0, ball_pos[0]))
                dist = math.hypot(ball_pos[0] - pet.x, ball_pos[1] - (pet.y - 10))
                if dist < 65.0 and abs(ball_vel[1]) > 0.5:
                    ball_vel[1] = -8.5
                    ball_vel[0] = (ball_pos[0] - pet.x) * 0.25 + random.uniform(-2.0, 2.0)
                    sounds.play("squeak")
                    particles.append(Particle(ball_pos[0], ball_pos[1], "💖", GOLD))
                    happiness = min(5, happiness + 1)
                    safe_emit("pet.played", f"play-{time.time()}")

        if pet.is_sleeping and random.random() < 0.06:
            particles.append(Particle(pet.x + 30, pet.y - 70, "💤", (180, 200, 255)))

        pet.update()
        particles = [p for p in particles if p.update()]
        if feedback_timer > 0:
            feedback_timer -= 0.035
        else:
            feedback_msg = ""

        surf = canvas.surface

        wall_col = NIGHT_WALL if pet.is_sleeping else ROOM_WALL
        floor_col = NIGHT_FLOOR if pet.is_sleeping else ROOM_FLOOR
        surf.fill(wall_col)
        pygame.draw.rect(surf, floor_col, (0, 420, REFERENCE_WIDTH, 180))
        pygame.draw.line(surf, (200, 170, 140) if not pet.is_sleeping else (45, 38, 65), (0, 420), (REFERENCE_WIDTH, 420), 4)

        rug_col = (255, 210, 220) if not pet.is_sleeping else (50, 45, 80)
        pygame.draw.ellipse(surf, rug_col, (262, 380, 500, 120))
        pygame.draw.ellipse(surf, (255, 190, 205) if not pet.is_sleeping else (65, 58, 100), (282, 390, 460, 100))

        if pet.is_sleeping:
            random.seed(99)
            for _ in range(25):
                sx = random.randint(30, REFERENCE_WIDTH - 30)
                sy = random.randint(20, 360)
                pygame.draw.circle(surf, (255, 255, 200), (sx, sy), 3)
            random.seed()

        card_bg = (255, 255, 255) if not pet.is_sleeping else (45, 40, 70)
        border_col = (61, 44, 31) if not pet.is_sleeping else (120, 100, 150)
        txt_col = DARK_TEXT if not pet.is_sleeping else WHITE

        stats_data = [
            ("💖", happiness, 5, PINK, 138),
            ("🍎", hunger, 5, (255, 150, 40), 246),
            ("✨", cleanliness, 5, ACCENT_BLUE, 354),
        ]
        for s_icon, s_val, s_max, s_col, s_x in stats_data:
            pill_rect = pygame.Rect(s_x, 10, 104, 66)
            pygame.draw.rect(surf, card_bg, pill_rect, border_radius=16)
            pygame.draw.rect(surf, border_col, pill_rect, width=2, border_radius=16)

            i_surf = typography.render(s_icon, FontRole.DISPLAY, 36, txt_col)
            surf.blit(i_surf, (s_x + 6, 12))
            v_surf = typography.render(f"{s_val}/{s_max}", FontRole.TITLE, 20, txt_col)
            surf.blit(v_surf, (s_x + 50, 18))

            bar_bg = pygame.Rect(s_x + 10, 50, 84, 14)
            pygame.draw.rect(surf, (225, 225, 230) if not pet.is_sleeping else (60, 55, 85), bar_bg, border_radius=7)
            fill_w = int(84 * (s_val / float(s_max)))
            if fill_w > 0:
                bar_fill = pygame.Rect(s_x + 10, 50, fill_w, 14)
                pygame.draw.rect(surf, s_col, bar_fill, border_radius=7)

        for s_idx, (spec_id, spec_icon) in enumerate([("cat", "🐱"), ("bunny", "🐰"), ("puppy", "🐶")]):
            bx = 470 + s_idx * 78
            is_sel = (pet.species == spec_id)
            btn_bg = GOLD if is_sel else card_bg
            btn_rect = pygame.Rect(bx, 10, 72, 66)
            pygame.draw.rect(surf, btn_bg, btn_rect, border_radius=18)
            pygame.draw.rect(surf, (220, 150, 20) if is_sel else border_col, btn_rect, width=3 if is_sel else 2, border_radius=18)
            s_icon = typography.render(spec_icon, FontRole.DISPLAY, 46, txt_col)
            surf.blit(s_icon, s_icon.get_rect(center=btn_rect.center))

        hud_rect = pygame.Rect(775, 10, 230, 66)
        pygame.draw.rect(surf, card_bg, hud_rect, border_radius=18)
        pygame.draw.rect(surf, border_col, hud_rect, width=2, border_radius=18)
        hud_str = f"⭐ {happiness}   🏆 {happiness * 20}"
        h_surf = typography.render(hud_str, FontRole.TITLE, 26, (180, 90, 20) if not pet.is_sleeping else GOLD)
        surf.blit(h_surf, h_surf.get_rect(center=hud_rect.center))

        pet.draw(surf)

        if active_tab == "feed" and not pet.is_sleeping:
            pygame.draw.rect(surf, WHITE, (290, 90, 444, 76), border_radius=22)
            pygame.draw.rect(surf, PINK, (290, 90, 444, 76), width=3, border_radius=22)
            f_treats = typography.render("🐟   🍓   🍪   🥛   🧁", FontRole.DISPLAY, 46, DARK_TEXT)
            surf.blit(f_treats, f_treats.get_rect(center=(512, 128)))
        elif active_tab == "bath":
            for bx, by, br in bubbles:
                pygame.draw.circle(surf, (220, 240, 255, 180), (int(bx), int(by)), int(br))
                pygame.draw.circle(surf, WHITE, (int(bx - 4), int(by - 4)), int(br // 3))
        elif active_tab == "play" and not pet.is_sleeping:
            bx, by = int(ball_pos[0]), int(ball_pos[1])
            pygame.draw.circle(surf, (255, 90, 90), (bx, by), 26)
            pygame.draw.ellipse(surf, (255, 220, 50), (bx - 13, by - 26, 26, 52))
            pygame.draw.circle(surf, WHITE, (bx - 7, by - 7), 7)

        for p in particles:
            p.draw(surf, typography)

        if feedback_msg:
            f_rect = pygame.Rect(262, 440, 500, 50)
            pygame.draw.rect(surf, WHITE, f_rect, border_radius=16)
            pygame.draw.rect(surf, PINK, f_rect, width=3, border_radius=16)
            t_msg = typography.render(feedback_msg, FontRole.TITLE, 26, DARK_TEXT)
            surf.blit(t_msg, t_msg.get_rect(center=f_rect.center))

        tabs = [
            ("feed", "🐟", "Pappa" if active_locale == "it" else "Treats"),
            ("bath", "🧼", "Bagnetto" if active_locale == "it" else "Bath"),
            ("play", "🎾", "Giochi" if active_locale == "it" else "Play"),
            ("sleep", "🌙", "Nanna" if active_locale == "it" else "Sleep"),
            ("dress", "🎀", "Look" if active_locale == "it" else "Dress"),
        ]
        for idx, (tab_id, tab_icon, tab_label) in enumerate(tabs):
            tx = 95 + idx * 170
            t_active = (active_tab == tab_id)
            t_bg = PINK if t_active else WHITE
            t_border = (220, 80, 130) if t_active else (210, 195, 185)
            t_txt_col = WHITE if t_active else DARK_TEXT

            tab_rect = pygame.Rect(tx, 500, 155, 84)
            pygame.draw.rect(surf, t_bg, tab_rect, border_radius=20)
            pygame.draw.rect(surf, t_border, tab_rect, width=3, border_radius=20)

            i_surf = typography.render(tab_icon, FontRole.DISPLAY, 40, t_txt_col)
            surf.blit(i_surf, i_surf.get_rect(center=(tx + 77, 526)))

            l_surf = typography.render(tab_label, FontRole.TITLE, 17, t_txt_col)
            surf.blit(l_surf, l_surf.get_rect(center=(tx + 77, 564)))

        canvas.present(clear=theme.background)

        pygame.display.flip()

        if not ready_published:
            mark_activity_ready()
            ready_published = True

        clock.tick(30)

    if storage is not None:
        try:
            storage.kv_set(STORAGE_KEY, {
                "species": pet.species,
                "accessory": pet.accessory,
                "happiness": happiness,
                "hunger": hunger,
                "cleanliness": cleanliness,
                "timestamp": time.time(),
            })
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
