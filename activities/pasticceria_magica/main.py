from __future__ import annotations

import io
import math
from pathlib import Path
import random
import struct
import time
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
from greia_platform.activity_ui import ChildUiMetrics, mix
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
STORAGE_KEY = "pasticceria_magica.state.v3"

# Sweet Bakery Palette
BAKERY_WALL = (255, 243, 235)
BAKERY_COUNTER = (235, 195, 155)
COUNTER_TOP = (215, 165, 120)
PLATE_COLOR = (255, 255, 255)
PLATE_RIM = (230, 240, 255)
SHELF_COLOR = (195, 135, 90)
WHITE = (255, 255, 255)
DARK_TEXT = (55, 38, 30)
GOLD = (255, 215, 50)
PINK = (255, 125, 165)
PASTEL_PINK = (255, 215, 230)


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
        # Drop / Pop sound
        drop_samples = [
            int(math.sin(2 * math.pi * (450 + (900 - i) * 0.8) * (i / 22050.0)) * max(0.0, 1.0 - (i / 22050.0) / 0.06) * 14000)
            for i in range(1300)
        ]
        self._sounds["drop"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(drop_samples)))

        # Chime
        chime_samples = []
        for i in range(6000):
            t = i / 22050.0
            f = 587.33 if t < 0.09 else (880.0 if t < 0.18 else 1174.66)
            env = max(0.0, 1.0 - t / 0.27)
            chime_samples.append(int(math.sin(2 * math.pi * f * t) * env * 12000))
        self._sounds["chime"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(chime_samples)))

        # Ding (Bell)
        ding_samples = []
        for i in range(8000):
            t = i / 22050.0
            f = 1046.50
            env = math.exp(-6.0 * t)
            harm = math.sin(2 * math.pi * f * t) * 0.7 + math.sin(2 * math.pi * f * 2.75 * t) * 0.3
            ding_samples.append(int(harm * env * 15000))
        self._sounds["ding"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(ding_samples)))

        # Fanfare
        fanfare_samples = []
        notes = [523.25, 659.25, 783.99, 1046.50, 1318.51]
        for i in range(12000):
            t = i / 22050.0
            idx = min(len(notes) - 1, int(t / 0.08))
            env = max(0.0, 1.0 - t / 0.54)
            fanfare_samples.append(int(math.sin(2 * math.pi * notes[idx] * t) * env * 14000))
        self._sounds["fanfare"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(fanfare_samples)))

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
        speed = random.uniform(2.0, 6.0)
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


TOPPINGS = [
    ("strawberry", "🍓", (255, 80, 100)),
    ("blueberry", "🫐", (80, 140, 240)),
    ("star", "⭐", (255, 215, 50)),
    ("chocolate", "🍫", (140, 85, 55)),
    ("cherry", "🍒", (240, 50, 70)),
    ("cookie", "🍪", (220, 160, 90)),
]

# 16 Distinct, Non-Overlapping Slot Coordinates on the Cake Plate
CAKE_SLOTS: list[tuple[int, int]] = [
    # Center Cluster (4 slots)
    (435, 310), (495, 310), (435, 365), (495, 365),
    # Inner Oval Ring (6 slots)
    (380, 290), (550, 290), (350, 340), (580, 340), (380, 390), (550, 390),
    # Outer Decor Ring (6 slots)
    (465, 270), (320, 315), (610, 315), (320, 375), (610, 375), (465, 410),
]


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

    # Localization
    package_root = Path(__file__).parent
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    profile_lang = get_profile_locale()
    context = resolve_activity_locale(profile_lang, support)
    resources = LocalizedResources(package_root, context) if context else None
    active_locale = context.selected.language if context else "it"

    mode = "orders"  # "orders", "patterns", "free"
    score = 0
    stars = 0
    recipes_served = 0

    if storage is not None:
        try:
            saved = storage.kv_get(STORAGE_KEY, {})
            if isinstance(saved, dict):
                score = int(saved.get("score", 0))
                stars = int(saved.get("stars", 0))
                recipes_served = int(saved.get("recipes_served", 0))
        except Exception:
            pass

    # Order mode state
    current_order = [("strawberry", 3), ("blueberry", 2)]
    placed_toppings: list[tuple[str, str, int, int]] = []  # id, icon, x, y

    # Pattern mode state
    pattern_options = [
        (["🍓", "⭐", "🍓", "⭐"], "🍓", ["🍓", "🫐", "🍪"]),
        (["🫐", "🍪", "🫐", "🍪"], "🫐", ["⭐", "🫐", "🍫"]),
        (["🍫", "🍓", "🍫", "🍓"], "🍫", ["🍫", "🍒", "🍓"]),
        (["🍒", "⭐", "🍒", "⭐"], "🍒", ["🍪", "⭐", "🍒"]),
        (["🍪", "🍪", "⭐", "🍪", "🍪"], "⭐", ["⭐", "🍓", "🍫"]),
    ]
    pattern_idx = 0

    particles: list[Particle] = []
    feedback_text = ""
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
                    mode = "orders"
                elif event.key == pygame.K_2:
                    mode = "patterns"
                elif event.key == pygame.K_3:
                    mode = "free"
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if not _is_safe_point(screen, event.pos):
                    continue
                logical = canvas.pointer(event.pos)
                if logical is not None:
                    lx, ly = logical

                    # 1. Mode Switcher (Header tabs)
                    if 230 <= lx <= 390 and 10 <= ly <= 68:
                        mode = "orders"
                        sounds.play("drop")
                        continue
                    elif 405 <= lx <= 565 and 10 <= ly <= 68:
                        mode = "patterns"
                        sounds.play("drop")
                        continue
                    elif 580 <= lx <= 740 and 10 <= ly <= 68:
                        mode = "free"
                        sounds.play("drop")
                        continue

                    # 2. Orders & Free Mode Interactions
                    if mode in {"orders", "free"}:
                        # Check if child clicked an existing topping on the cake to REMOVE it
                        removed = False
                        for t_idx, (t_id, t_icon, tx, ty) in enumerate(list(placed_toppings)):
                            if (lx - tx) ** 2 + (ly - ty) ** 2 <= 28 ** 2:
                                placed_toppings.pop(t_idx)
                                sounds.play("drop")
                                for _ in range(8):
                                    particles.append(Particle(tx, ty, "✨", GOLD))
                                removed = True
                                break
                        if removed:
                            continue

                        # Check Pantry Shelf clicks (Right Shelf x = 705..995, y = 135..435)
                        for idx, (t_id, t_icon, _) in enumerate(TOPPINGS):
                            col_idx = idx % 2
                            row_idx = idx // 2
                            bx = 720 + col_idx * 135
                            by = 140 + row_idx * 95
                            if bx <= lx <= bx + 125 and by <= ly <= by + 85:
                                # Place topping into the next free slot on the cake
                                if len(placed_toppings) < len(CAKE_SLOTS):
                                    slot_idx = len(placed_toppings)
                                    px, py = CAKE_SLOTS[slot_idx]
                                    placed_toppings.append((t_id, t_icon, px, py))
                                    sounds.play("drop")
                                    particles.append(Particle(px, py, "✨", GOLD))
                                break

                        # 🧹 Pulisci (Clean) Button: x=710..840, y=455..560
                        if 710 <= lx <= 840 and 455 <= ly <= 565:
                            placed_toppings.clear()
                            sounds.play("drop")
                            feedback_text = ""
                            continue

                        # 🔔 SERVI! Button: x=850..1000, y=455..560
                        if 850 <= lx <= 1000 and 455 <= ly <= 565:
                            sounds.play("ding")
                            if mode == "orders":
                                counts: dict[str, int] = {}
                                for t_id, _, _, _ in placed_toppings:
                                    counts[t_id] = counts.get(t_id, 0) + 1

                                is_correct = True
                                for req_id, req_count in current_order:
                                    if counts.get(req_id, 0) != req_count:
                                        is_correct = False
                                        break
                                if len(counts) != len(current_order):
                                    is_correct = False

                                if is_correct:
                                    sounds.play("fanfare")
                                    score += 15
                                    stars += 1
                                    recipes_served += 1
                                    for _ in range(30):
                                        particles.append(Particle(465, 340, random.choice(["🍰", "✨", "🍓", "💖"]), GOLD))
                                    feedback_text = resources.text("feedback.perfect") if resources else "Perfetto! Delizioso! ✨🍰"
                                    feedback_timer = 3.0
                                    placed_toppings.clear()
                                    # Next recipe
                                    t1 = random.choice(TOPPINGS)[0]
                                    t2 = random.choice([t[0] for t in TOPPINGS if t[0] != t1])
                                    current_order = [(t1, random.randint(1, 4)), (t2, random.randint(1, 3))]
                                    safe_emit("recipe.completed", f"recipe-{time.time()}")
                                else:
                                    sounds.play("drop")
                                    feedback_text = resources.text("feedback.try_again") if resources else "Controlla la ricetta 💕"
                                    feedback_timer = 2.5
                            else:
                                sounds.play("fanfare")
                                for _ in range(25):
                                    particles.append(Particle(465, 340, "✨", GOLD))
                                feedback_text = resources.text("feedback.perfect") if resources else "Che capolavoro! ✨"
                                feedback_timer = 2.5
                            continue

                    # 3. Pattern Candidate Clicks
                    elif mode == "patterns":
                        _, correct_sym, candidates = pattern_options[pattern_idx]
                        for c_idx, cand_sym in enumerate(candidates):
                            cx = 330 + c_idx * 135
                            cy = 380
                            if cx <= lx <= cx + 110 and cy <= ly <= cy + 110:
                                if cand_sym == correct_sym:
                                    sounds.play("chime")
                                    score += 10
                                    stars += 1
                                    for _ in range(20):
                                        particles.append(Particle(cx + 55, cy + 55, "🌟", GOLD))
                                    feedback_text = resources.text("feedback.pattern_correct") if resources else "Sequenza completata! 🌟"
                                    feedback_timer = 2.5
                                    pattern_idx = (pattern_idx + 1) % len(pattern_options)
                                    safe_emit("pattern.matched", f"pat-{time.time()}")
                                else:
                                    sounds.play("drop")
                                    feedback_text = resources.text("feedback.try_again") if resources else "Riprova 💕"
                                    feedback_timer = 1.5

        # Updates
        particles = [p for p in particles if p.update()]
        if feedback_timer > 0:
            feedback_timer -= 0.035
        else:
            feedback_text = ""

        # --- RENDERING (Logical Canvas 1024x600) ---
        surf = canvas.surface

        # 1. Bakery Room & Counter
        surf.fill(BAKERY_WALL)
        for wx in range(0, REFERENCE_WIDTH, 40):
            pygame.draw.rect(surf, (255, 232, 220), (wx, 0, 20, 110))

        # Wooden Counter
        pygame.draw.rect(surf, BAKERY_COUNTER, (0, 460, REFERENCE_WIDTH, 140))
        pygame.draw.rect(surf, COUNTER_TOP, (0, 450, REFERENCE_WIDTH, 20))

        # 2. Header Mode Tabs (Large & clear)
        btn1_c = GOLD if mode == "orders" else WHITE
        btn2_c = GOLD if mode == "patterns" else WHITE
        btn3_c = GOLD if mode == "free" else WHITE
        for b_idx, (b_name, b_col, b_x) in enumerate([
            ("🧁 Ordini" if active_locale == "it" else "🧁 Orders", btn1_c, 230),
            ("🍪 Sequenze" if active_locale == "it" else "🍪 Patterns", btn2_c, 405),
            ("🎨 Libero" if active_locale == "it" else "🎨 Free", btn3_c, 580),
        ]):
            b_rect = pygame.Rect(b_x, 12, 160, 52)
            pygame.draw.rect(surf, b_col, b_rect, border_radius=16)
            pygame.draw.rect(surf, (200, 160, 130), b_rect, width=2, border_radius=16)
            m_surf = typography.render(b_name, FontRole.TITLE, 22, DARK_TEXT)
            surf.blit(m_surf, m_surf.get_rect(center=b_rect.center))

        # 3. Top-Right HUD Badge (Stars & Score)
        hud_badge = pygame.Rect(REFERENCE_WIDTH - 250, 12, 235, 52)
        pygame.draw.rect(surf, WHITE, hud_badge, border_radius=16)
        pygame.draw.rect(surf, (200, 160, 130), hud_badge, width=2, border_radius=16)
        hud_txt = f"⭐ {stars}   🏆 {score}"
        h_surf = typography.render(hud_txt, FontRole.TITLE, 24, (180, 90, 20))
        surf.blit(h_surf, h_surf.get_rect(center=hud_badge.center))

        # 4. Mode Content Rendering
        if mode in {"orders", "free"}:
            # Recipe Order Ticket Card (Left x = 20..270, y = 90..445)
            if mode == "orders":
                ticket_rect = pygame.Rect(20, 90, 250, 350)
                pygame.draw.rect(surf, WHITE, ticket_rect, border_radius=20)
                pygame.draw.rect(surf, (255, 200, 220), ticket_rect, width=3, border_radius=20)
                # Pink Header
                pygame.draw.rect(surf, PINK, (20, 90, 250, 50), border_top_left_radius=20, border_top_right_radius=20)
                r_title = typography.render("📋 Ricetta Dolce" if active_locale == "it" else "📋 Sweet Order", FontRole.TITLE, 22, WHITE)
                surf.blit(r_title, r_title.get_rect(center=(145, 115)))

                for o_idx, (t_id, t_qty) in enumerate(current_order):
                    icon_sym = next(t[1] for t in TOPPINGS if t[0] == t_id)
                    oy = 155 + o_idx * 135
                    item_rect = pygame.Rect(32, oy, 226, 125)
                    pygame.draw.rect(surf, (255, 248, 240), item_rect, border_radius=16)
                    pygame.draw.rect(surf, (245, 215, 195), item_rect, width=2, border_radius=16)

                    # Big text: 3 x 🍓
                    t_str = f"{t_qty} x {icon_sym}"
                    txt_o = typography.render(t_str, FontRole.DISPLAY, 44, DARK_TEXT)
                    surf.blit(txt_o, txt_o.get_rect(center=(145, oy + 38)))

                    # Visual 1-to-1 matching icons for non-readers: 🍓 🍓 🍓
                    visual_row = " ".join([icon_sym] * t_qty)
                    vis_surf = typography.render(visual_row, FontRole.DISPLAY, 28, DARK_TEXT)
                    surf.blit(vis_surf, vis_surf.get_rect(center=(145, oy + 88)))
            else:
                # Free mode banner
                ticket_rect = pygame.Rect(20, 90, 250, 220)
                pygame.draw.rect(surf, WHITE, ticket_rect, border_radius=20)
                pygame.draw.rect(surf, (255, 200, 220), ticket_rect, width=3, border_radius=20)
                f_title = typography.render("🎨 Decora a piacere!" if active_locale == "it" else "🎨 Decorate freely!", FontRole.TITLE, 22, DARK_TEXT)
                surf.blit(f_title, f_title.get_rect(center=(145, 200)))

            # Center Plate & Cake (x=280..690)
            pygame.draw.ellipse(surf, PLATE_RIM, (280, 235, 390, 220))
            pygame.draw.ellipse(surf, PLATE_COLOR, (295, 245, 360, 200))

            # Cake Base
            pygame.draw.ellipse(surf, (230, 180, 120), (320, 265, 310, 160))
            # Icing Top
            pygame.draw.ellipse(surf, (255, 175, 200), (335, 275, 280, 130))
            pygame.draw.ellipse(surf, WHITE, (360, 290, 230, 90))

            # Placed Toppings in Distinct Non-Overlapping Slots
            for t_id, t_icon, tx, ty in placed_toppings:
                # Pedestal halo to make it stand out distinctly
                halo_surf = pygame.Surface((64, 64), pygame.SRCALPHA)
                pygame.draw.circle(halo_surf, (255, 255, 255, 220), (32, 32), 26)
                pygame.draw.circle(halo_surf, (200, 160, 130, 180), (32, 32), 26, width=2)
                surf.blit(halo_surf, (tx - 32, ty - 32))

                t_surf = typography.render(t_icon, FontRole.DISPLAY, 40, DARK_TEXT)
                surf.blit(t_surf, t_surf.get_rect(center=(tx, ty)))

            # Right Pantry Shelf (x = 705..1000)
            pantry_card = pygame.Rect(705, 90, 295, 350)
            pygame.draw.rect(surf, SHELF_COLOR, pantry_card, border_radius=20)
            p_title = typography.render("Dispensa Topping" if active_locale == "it" else "Pantry Toppings", FontRole.TITLE, 22, WHITE)
            surf.blit(p_title, p_title.get_rect(center=(852, 115)))

            for idx, (t_id, t_icon, _) in enumerate(TOPPINGS):
                col_idx = idx % 2
                row_idx = idx // 2
                bx = 720 + col_idx * 135
                by = 140 + row_idx * 95
                b_rect = pygame.Rect(bx, by, 125, 85)
                pygame.draw.rect(surf, WHITE, b_rect, border_radius=16)
                pygame.draw.rect(surf, (240, 215, 190), b_rect, width=2, border_radius=16)
                i_surf = typography.render(t_icon, FontRole.DISPLAY, 50, DARK_TEXT)
                surf.blit(i_surf, i_surf.get_rect(center=b_rect.center))

            # 🧹 Pulisci (Clean) Button: Large and prominent
            clean_rect = pygame.Rect(710, 455, 130, 95)
            pygame.draw.rect(surf, (230, 240, 250), clean_rect, border_radius=18)
            pygame.draw.rect(surf, (180, 205, 230), clean_rect, width=3, border_radius=18)
            c_icon = typography.render("🧹", FontRole.DISPLAY, 48, DARK_TEXT)
            c_label = typography.render("Pulisci" if active_locale == "it" else "Clear", FontRole.TITLE, 18, DARK_TEXT)
            surf.blit(c_icon, c_icon.get_rect(center=(clean_rect.centerx, clean_rect.centery - 14)))
            surf.blit(c_label, c_label.get_rect(center=(clean_rect.centerx, clean_rect.centery + 24)))

            # 🔔 SERVI! (Serve) Button: Huge and celebratory
            serve_rect = pygame.Rect(855, 455, 145, 95)
            pygame.draw.rect(surf, GOLD, serve_rect, border_radius=18)
            pygame.draw.rect(surf, (220, 150, 20), serve_rect, width=3, border_radius=18)
            s_icon = typography.render("🔔", FontRole.DISPLAY, 48, DARK_TEXT)
            s_label = typography.render("SERVI!" if active_locale == "it" else "SERVE!", FontRole.DISPLAY, 20, DARK_TEXT)
            surf.blit(s_icon, s_icon.get_rect(center=(serve_rect.centerx, serve_rect.centery - 14)))
            surf.blit(s_label, s_label.get_rect(center=(serve_rect.centerx, serve_rect.centery + 24)))

        elif mode == "patterns":
            # Pattern Sequence Tray (Center Stage)
            seq, _, candidates = pattern_options[pattern_idx]
            pygame.draw.rect(surf, WHITE, (120, 120, 784, 210), border_radius=24)
            pygame.draw.rect(surf, PINK, (120, 120, 784, 210), width=3, border_radius=24)
            p_prompt = typography.render("Quale biscotto completa la sequenza?" if active_locale == "it" else "Which cookie completes the pattern?", FontRole.TITLE, 26, DARK_TEXT)
            surf.blit(p_prompt, p_prompt.get_rect(center=(512, 160)))

            total_items = len(seq) + 1
            start_x = 512 - (total_items * 55)
            for s_i, sym in enumerate(seq):
                ck_rect = pygame.Rect(start_x + s_i * 110, 205, 95, 95)
                pygame.draw.rect(surf, (255, 245, 230), ck_rect, border_radius=18)
                pygame.draw.rect(surf, (230, 180, 130), ck_rect, width=3, border_radius=18)
                ck_sym = typography.render(sym, FontRole.DISPLAY, 48, DARK_TEXT)
                surf.blit(ck_sym, ck_sym.get_rect(center=ck_rect.center))

            slot_rect = pygame.Rect(start_x + len(seq) * 110, 205, 95, 95)
            pygame.draw.rect(surf, (255, 235, 160), slot_rect, border_radius=18)
            pygame.draw.rect(surf, GOLD, slot_rect, width=4, border_radius=18)
            q_sym = typography.render("?", FontRole.DISPLAY, 48, DARK_TEXT)
            surf.blit(q_sym, q_sym.get_rect(center=slot_rect.center))

            for c_i, cand_sym in enumerate(candidates):
                cx = 330 + c_i * 135
                cy = 380
                c_rect = pygame.Rect(cx, cy, 110, 110)
                pygame.draw.rect(surf, WHITE, c_rect, border_radius=20)
                pygame.draw.rect(surf, PINK, c_rect, width=3, border_radius=20)
                cand_s = typography.render(cand_sym, FontRole.DISPLAY, 52, DARK_TEXT)
                surf.blit(cand_s, cand_s.get_rect(center=c_rect.center))

        # Particles
        for p in particles:
            p.draw(surf, typography)

        # Feedback Toast
        if feedback_text:
            f_rect = pygame.Rect(262, 510, 500, 52)
            pygame.draw.rect(surf, WHITE, f_rect, border_radius=18)
            pygame.draw.rect(surf, PINK, f_rect, width=3, border_radius=18)
            t_msg = typography.render(feedback_text, FontRole.TITLE, 26, DARK_TEXT)
            surf.blit(t_msg, t_msg.get_rect(center=f_rect.center))

        # Present Canvas
        canvas.present(clear=theme.background)

        # Star pointer cursor
        if pygame.mouse.get_focused():
            mpos = pygame.mouse.get_pos()
            pygame.draw.circle(screen, GOLD, mpos, metrics.px(10))
            pygame.draw.circle(screen, WHITE, mpos, metrics.px(5))

        pygame.display.flip()

        if not ready_published:
            mark_activity_ready()
            ready_published = True

        clock.tick(30)

    if storage is not None:
        try:
            storage.kv_set(STORAGE_KEY, {
                "score": score,
                "stars": stars,
                "recipes_served": recipes_served,
                "timestamp": time.time(),
            })
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
