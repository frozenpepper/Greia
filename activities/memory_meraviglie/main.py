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
STORAGE_KEY = "memory_meraviglie.progress.v1"

THEMES = [
    {
        "id": "animals",
        "name_it": "🐾 Animali",
        "name_en": "🐾 Animals",
        "bg": (240, 249, 255),
        "card_back": (59, 130, 246),
        "items": [
            {"id": "lion", "emoji": "🦁", "color": (245, 158, 11), "label_it": "Leoncino", "label_en": "Lion"},
            {"id": "panda", "emoji": "🐼", "color": (100, 116, 139), "label_it": "Pandino", "label_en": "Panda"},
            {"id": "fox", "emoji": "🦊", "color": (249, 115, 22), "label_it": "Volpe", "label_en": "Fox"},
            {"id": "unicorn", "emoji": "🦄", "color": (236, 72, 153), "label_it": "Unicorno", "label_en": "Unicorn"},
            {"id": "cat", "emoji": "🐱", "color": (234, 179, 8), "label_it": "Gattino", "label_en": "Kitty"},
            {"id": "frog", "emoji": "🐸", "color": (34, 197, 94), "label_it": "Ranocchia", "label_en": "Frog"},
        ],
    },
    {
        "id": "sweets",
        "name_it": "🍭 Dolcetti",
        "name_en": "🍭 Sweets",
        "bg": (253, 242, 248),
        "card_back": (236, 72, 153),
        "items": [
            {"id": "cupcake", "emoji": "🧁", "color": (244, 114, 182), "label_it": "Cupcake", "label_en": "Cupcake"},
            {"id": "icecream", "emoji": "🍦", "color": (251, 146, 60), "label_it": "Gelato", "label_en": "Ice Cream"},
            {"id": "donut", "emoji": "🍩", "color": (217, 119, 6), "label_it": "Ciambella", "label_en": "Donut"},
            {"id": "strawberry", "emoji": "🍓", "color": (239, 68, 68), "label_it": "Fragola", "label_en": "Strawberry"},
            {"id": "cookie", "emoji": "🍪", "color": (180, 83, 9), "label_it": "Biscotto", "label_en": "Cookie"},
            {"id": "candy", "emoji": "🍬", "color": (168, 85, 247), "label_it": "Caramella", "label_en": "Candy"},
        ],
    },
    {
        "id": "vehicles",
        "name_it": "🚀 Veicoli",
        "name_en": "🚀 Vehicles",
        "bg": (238, 242, 255),
        "card_back": (99, 102, 241),
        "items": [
            {"id": "rocket", "emoji": "🚀", "color": (239, 68, 68), "label_it": "Razzo", "label_en": "Rocket"},
            {"id": "train", "emoji": "🚂", "color": (59, 130, 246), "label_it": "Treno", "label_en": "Train"},
            {"id": "boat", "emoji": "⛵", "color": (14, 165, 233), "label_it": "Barca", "label_en": "Boat"},
            {"id": "helicopter", "emoji": "🚁", "color": (245, 158, 11), "label_it": "Elicottero", "label_en": "Helicopter"},
            {"id": "car", "emoji": "🚗", "color": (220, 38, 38), "label_it": "Auto", "label_en": "Car"},
            {"id": "plane", "emoji": "✈️", "color": (16, 185, 129), "label_it": "Aereo", "label_en": "Plane"},
        ],
    },
    {
        "id": "nature",
        "name_it": "🌸 Natura",
        "name_en": "🌸 Nature",
        "bg": (240, 253, 244),
        "card_back": (34, 197, 94),
        "items": [
            {"id": "sunflower", "emoji": "🌻", "color": (234, 179, 8), "label_it": "Girasole", "label_en": "Sunflower"},
            {"id": "mushroom", "emoji": "🍄", "color": (239, 68, 68), "label_it": "Fungo", "label_en": "Mushroom"},
            {"id": "rainbow", "emoji": "🌈", "color": (168, 85, 247), "label_it": "Arcobaleno", "label_en": "Rainbow"},
            {"id": "star", "emoji": "⭐", "color": (254, 202, 87), "label_it": "Stella", "label_en": "Star"},
            {"id": "clover", "emoji": "🍀", "color": (16, 185, 129), "label_it": "Quadrifoglio", "label_en": "Clover"},
            {"id": "moon", "emoji": "🌙", "color": (253, 224, 71), "label_it": "Luna", "label_en": "Moon"},
        ],
    },
]

GRID_CONFIGS = [
    {"id": "small", "label": "2x2 (4)", "cols": 2, "rows": 2, "pairs": 2},
    {"id": "medium", "label": "3x2 (6)", "cols": 3, "rows": 2, "pairs": 3},
    {"id": "large", "label": "4x3 (12)", "cols": 4, "rows": 3, "pairs": 6},
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


class MemoryAudio:
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
        # Flip sound (card snap)
        flip_samples = []
        for i in range(int(rate * 0.05)):
            t = i / rate
            env = math.exp(-20.0 * t)
            val = math.sin(2.0 * math.pi * 450.0 * t)
            flip_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["flip"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(flip_samples)))

        # Match chime (harmonic chord)
        match_samples = []
        for i in range(int(rate * 0.25)):
            t = i / rate
            env = math.exp(-4.0 * t)
            val = 0.6 * math.sin(2.0 * math.pi * 523.25 * t) + 0.4 * math.sin(2.0 * math.pi * 659.25 * t)
            match_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["match"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(match_samples)))

        # Mismatch tap
        mismatch_samples = []
        for i in range(int(rate * 0.08)):
            t = i / rate
            env = math.exp(-12.0 * t)
            val = math.sin(2.0 * math.pi * 180.0 * t)
            mismatch_samples.append(int(32767.0 * 0.20 * env * val))
        self._sounds["mismatch"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(mismatch_samples)))

        # Win chime
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
    sounds = MemoryAudio()

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

    theme_idx = 0
    grid_idx = 1  # 3x2 default (6 cards, 3 pairs)

    cards: list[dict[str, Any]] = []
    flipped_indices: list[int] = []
    pairs_found = 0
    total_pairs = 3
    moves_count = 0
    unflip_timer = 0.0
    particles: list[dict[str, Any]] = []
    is_victory = False

    def start_new_game() -> None:
        nonlocal cards, flipped_indices, pairs_found, total_pairs, moves_count, unflip_timer, particles, is_victory
        theme_cfg = THEMES[theme_idx]
        grid_cfg = GRID_CONFIGS[grid_idx]
        total_pairs = grid_cfg["pairs"]
        pairs_found = 0
        moves_count = 0
        flipped_indices.clear()
        unflip_timer = 0.0
        particles.clear()
        is_victory = False

        selected_items = random.sample(theme_cfg["items"], total_pairs)
        deck_items = selected_items * 2
        random.shuffle(deck_items)

        cards.clear()
        for idx, item in enumerate(deck_items):
            cards.append({
                "id": item["id"],
                "item": item,
                "is_matched": False,
                "is_revealed": False,
                "flip_anim": 0.0,  # 0.0 = face down, 1.0 = face up
            })

    start_new_game()

    running = True
    ready_published = False

    while running and not activity_stop_requested():
        t_now = time.time()
        theme_cfg = THEMES[theme_idx]
        grid_cfg = GRID_CONFIGS[grid_idx]

        # Calculate card grid positions
        cols = grid_cfg["cols"]
        rows = grid_cfg["rows"]
        top_y = 100
        bottom_y = REFERENCE_HEIGHT - 70
        avail_w = REFERENCE_WIDTH - 120
        avail_h = bottom_y - top_y

        card_w = min(170, (avail_w - (cols - 1) * 20) // cols)
        card_h = min(220, (avail_h - (rows - 1) * 20) // rows)
        grid_w = cols * card_w + (cols - 1) * 20
        grid_h = rows * card_h + (rows - 1) * 20
        grid_ox = (REFERENCE_WIDTH - grid_w) // 2
        grid_oy = top_y + (avail_h - grid_h) // 2

        # Card rects calculation
        card_rects = []
        for i in range(len(cards)):
            c = i % cols
            r = i // cols
            rx = grid_ox + c * (card_w + 20)
            ry = grid_oy + r * (card_h + 20)
            card_rects.append(pygame.Rect(rx, ry, card_w, card_h))

        # Check pending unflip
        if unflip_timer > 0.0:
            unflip_timer -= 0.033
            if unflip_timer <= 0.0:
                for idx in flipped_indices:
                    if not cards[idx]["is_matched"]:
                        cards[idx]["is_revealed"] = False
                flipped_indices.clear()

        # Update card flip animation
        for card in cards:
            target_flip = 1.0 if (card["is_revealed"] or card["is_matched"]) else 0.0
            diff = target_flip - card["flip_anim"]
            if abs(diff) > 0.01:
                card["flip_anim"] += diff * 0.25
            else:
                card["flip_anim"] = target_flip

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN) and is_victory:
                    start_new_game()
                elif event.key == pygame.K_n:
                    start_new_game()

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
                        start_new_game()
                        continue

                # Top New Game button
                new_btn = pygame.Rect(REFERENCE_WIDTH - 150, 15, 130, 42)
                if new_btn.collidepoint(mx, my):
                    start_new_game()
                    continue

                # Bottom Theme Button
                theme_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 140, REFERENCE_HEIGHT - 50, 130, 40)
                if theme_btn.collidepoint(mx, my):
                    theme_idx = (theme_idx + 1) % len(THEMES)
                    start_new_game()
                    continue

                # Bottom Grid Size Button
                grid_btn = pygame.Rect(REFERENCE_WIDTH // 2 + 10, REFERENCE_HEIGHT - 50, 130, 40)
                if grid_btn.collidepoint(mx, my):
                    grid_idx = (grid_idx + 1) % len(GRID_CONFIGS)
                    start_new_game()
                    continue

                # Card Clicks
                if unflip_timer <= 0.0 and not is_victory:
                    for idx, rect in enumerate(card_rects):
                        if rect.collidepoint(mx, my):
                            card = cards[idx]
                            if not card["is_revealed"] and not card["is_matched"]:
                                card["is_revealed"] = True
                                sounds.play("flip")
                                flipped_indices.append(idx)

                                if len(flipped_indices) == 2:
                                    moves_count += 1
                                    idx1, idx2 = flipped_indices[0], flipped_indices[1]
                                    if cards[idx1]["id"] == cards[idx2]["id"]:
                                        # Match found!
                                        cards[idx1]["is_matched"] = True
                                        cards[idx2]["is_matched"] = True
                                        pairs_found += 1
                                        sounds.play("match")
                                        try:
                                            emit_activity_event("memory.pair_found", {"pairs": pairs_found})
                                        except Exception:
                                            pass
                                        # Sparkle burst
                                        for cr in [card_rects[idx1], card_rects[idx2]]:
                                            for _ in range(16):
                                                ang = random.uniform(0, 6.28)
                                                spd = random.uniform(2.0, 5.0)
                                                particles.append({
                                                    "x": cr.centerx,
                                                    "y": cr.centery,
                                                    "vx": math.cos(ang) * spd,
                                                    "vy": math.sin(ang) * spd,
                                                    "color": (254, 202, 87),
                                                    "size": random.uniform(4.0, 8.0),
                                                    "life": 1.0,
                                                    "decay": 0.03,
                                                })
                                        flipped_indices.clear()

                                        if pairs_found >= total_pairs:
                                            is_victory = True
                                            sounds.play("win")
                                            try:
                                                emit_activity_event("memory.game_completed", {"moves": moves_count})
                                            except Exception:
                                                pass
                                    else:
                                        sounds.play("mismatch")
                                        unflip_timer = 1.0
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
        surf.fill(theme_cfg["bg"])

        # 1. Draw Cards
        for idx, card in enumerate(cards):
            rect = card_rects[idx]
            flip = card["flip_anim"]  # 0 = back, 1 = front
            cos_flip = abs(math.cos(flip * math.pi))
            cur_w = max(4, int(card_w * cos_flip))
            cur_rect = pygame.Rect(rect.centerx - cur_w // 2, rect.top, cur_w, card_h)

            # Shadow
            pygame.draw.rect(surf, (203, 213, 225), cur_rect.move(3, 4), border_radius=14)

            is_front = flip >= 0.5
            if is_front:
                # Front face
                pygame.draw.rect(surf, (255, 255, 255), cur_rect, border_radius=18)
                pygame.draw.rect(surf, (203, 213, 225), cur_rect, width=3, border_radius=18)
                if cos_flip > 0.4:
                    item = card["item"]
                    # Giant colorful emblem
                    emblem_r = int(card_w * 0.34)
                    pygame.draw.circle(surf, item["color"], cur_rect.center, emblem_r)
                    pygame.draw.circle(surf, (255, 255, 255), (cur_rect.centerx - emblem_r // 3, cur_rect.centery - emblem_r // 3), max(3, emblem_r // 3))
                    pygame.draw.circle(surf, (20, 20, 30), cur_rect.center, emblem_r, 3)
            else:
                # Back face
                pygame.draw.rect(surf, theme_cfg["card_back"], cur_rect, border_radius=18)
                pygame.draw.rect(surf, (255, 255, 255), cur_rect, width=4, border_radius=18)
                if cos_flip > 0.4:
                    pygame.draw.circle(surf, (255, 255, 255), cur_rect.center, int(card_w * 0.22), 4)
                    pygame.draw.circle(surf, (254, 240, 138), cur_rect.center, int(card_w * 0.14))

        # 2. Draw Particles
        for p in particles:
            cur_sz = max(2.0, p["size"] * max(0.0, min(1.0, p["life"])))
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), int(cur_sz))

        # 3. Top HUD (Star Pill & Giant Buttons)
        star_pill = pygame.Rect(80, 16, 130, 56)
        pygame.draw.rect(surf, (255, 255, 255), star_pill, border_radius=18)
        pygame.draw.rect(surf, (234, 179, 8), star_pill, width=3, border_radius=18)
        pygame.draw.circle(surf, (234, 179, 8), (star_pill.left + 30, star_pill.centery), 16)
        s_txt = typography.render(f"★ {pairs_found}/{total_pairs}", FontRole.DISPLAY, 24, (180, 83, 9))
        surf.blit(s_txt, (star_pill.left + 54, star_pill.centery - s_txt.get_height() // 2))

        # New Game Button
        new_btn = pygame.Rect(REFERENCE_WIDTH - 160, 16, 140, 56)
        pygame.draw.rect(surf, (71, 85, 105), new_btn, border_radius=18)
        new_txt = typography.render("🔄 NUOVO", FontRole.DISPLAY, 20, (255, 255, 255))
        surf.blit(new_txt, (new_btn.centerx - new_txt.get_width() // 2, new_btn.centery - new_txt.get_height() // 2))

        # 4. Bottom Selectors
        theme_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 140, REFERENCE_HEIGHT - 50, 130, 40)
        pygame.draw.rect(surf, (51, 65, 85), theme_btn, border_radius=10)
        t_name = theme_cfg["name_it"] if active_locale == "it" else theme_cfg["name_en"]
        theme_lbl = typography.render(t_name, FontRole.BODY, 15, (255, 255, 255))
        surf.blit(theme_lbl, (theme_btn.centerx - theme_lbl.get_width() // 2, theme_btn.centery - theme_lbl.get_height() // 2))

        grid_btn = pygame.Rect(REFERENCE_WIDTH // 2 + 10, REFERENCE_HEIGHT - 50, 130, 40)
        pygame.draw.rect(surf, (51, 65, 85), grid_btn, border_radius=10)
        grid_lbl = typography.render("📐 " + grid_cfg["label"], FontRole.BODY, 15, (255, 255, 255))
        surf.blit(grid_lbl, (grid_btn.centerx - grid_lbl.get_width() // 2, grid_btn.centery - grid_lbl.get_height() // 2))

        # 5. Victory Modal
        if is_victory:
            overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 15, 30, 200))
            surf.blit(overlay, (0, 0))

            card = pygame.Rect(REFERENCE_WIDTH // 2 - 220, REFERENCE_HEIGHT // 2 - 140, 440, 280)
            pygame.draw.rect(surf, (30, 41, 59), card, border_radius=20)
            pygame.draw.rect(surf, (254, 202, 87), card, width=3, border_radius=20)

            v_title = typography.render(t("victory.title", "Bravissima! Coppie trovate! 🌟"), FontRole.DISPLAY, 22, (254, 202, 87))
            surf.blit(v_title, (card.centerx - v_title.get_width() // 2, card.top + 30))

            v_sub = typography.render(t("victory.subtitle", "Che memoria fantastica!"), FontRole.BODY, 18, (241, 245, 249))
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
                "theme_idx": theme_idx,
                "grid_idx": grid_idx,
                "timestamp": time.time(),
            })
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
