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
STORAGE_KEY = "acquario_magico.progress.v1"

SPECIES = [
    {"id": "clownfish", "name_it": "Pesce Pagliaccio 🐠", "name_en": "Clownfish 🐠", "color": (249, 115, 22), "stripe": (255, 255, 255), "size": 24},
    {"id": "turtle", "name_it": "Tartaruga 🐢", "name_en": "Sea Turtle 🐢", "color": (34, 197, 94), "stripe": (22, 101, 52), "size": 36},
    {"id": "octopus", "name_it": "Polipetto 🐙", "name_en": "Octopus 🐙", "color": (236, 72, 153), "stripe": (244, 114, 182), "size": 30},
    {"id": "dolphin", "name_it": "Delfino 🐬", "name_en": "Dolphin 🐬", "color": (59, 130, 246), "stripe": (191, 219, 254), "size": 42},
    {"id": "puffer", "name_it": "Pesce Palla 🐡", "name_en": "Pufferfish 🐡", "color": (234, 179, 8), "stripe": (254, 240, 138), "size": 28},
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


class AquariumAudio:
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
        # Bubble pop
        bubble_samples = []
        for i in range(int(rate * 0.08)):
            t = i / rate
            env = math.exp(-20.0 * t)
            val = math.sin(2.0 * math.pi * (500.0 + 400.0 * (t / 0.08)) * t)
            bubble_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["bubble"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(bubble_samples)))

        # Nibble food
        nibble_samples = []
        for i in range(int(rate * 0.10)):
            t = i / rate
            env = math.exp(-15.0 * t)
            val = math.sin(2.0 * math.pi * 750.0 * t)
            nibble_samples.append(int(32767.0 * 0.20 * env * val))
        self._sounds["nibble"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(nibble_samples)))

        # Glow chime
        glow_samples = []
        for i in range(int(rate * 0.35)):
            t = i / rate
            env = math.exp(-3.0 * t)
            val = 0.5 * math.sin(2.0 * math.pi * 523.25 * t) + 0.5 * math.sin(2.0 * math.pi * 783.99 * t)
            glow_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["glow"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(glow_samples)))

        # Splash
        splash_samples = []
        for i in range(int(rate * 0.14)):
            t = i / rate
            env = math.exp(-8.0 * t)
            val = random.uniform(-1.0, 1.0)
            splash_samples.append(int(32767.0 * 0.20 * env * val))
        self._sounds["splash"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(splash_samples)))

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
    sounds = AquariumAudio()

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

    glow_mode = False

    # Swimming creatures
    creatures: list[dict[str, Any]] = []
    food_pellets: list[dict[str, Any]] = []
    bubbles: list[dict[str, Any]] = []
    particles: list[dict[str, Any]] = []

    def spawn_creature(spec_idx: int | None = None) -> None:
        if len(creatures) >= 12:
            return
        sp = SPECIES[spec_idx % len(SPECIES)] if spec_idx is not None else random.choice(SPECIES)
        vx = random.choice([-1.5, -1.0, 1.0, 1.5])
        creatures.append({
            "spec": sp,
            "x": random.uniform(100, REFERENCE_WIDTH - 100),
            "y": random.uniform(120, REFERENCE_HEIGHT - 160),
            "vx": vx,
            "vy": random.uniform(-0.5, 0.5),
            "swim_t": random.random() * 6.28,
            "puffed": 0.0,
        })
        sounds.play("splash")

    # Initial fish in tank
    for i in range(4):
        spawn_creature(i)

    running = True
    ready_published = False

    while running and not activity_stop_requested():
        t_now = time.time()

        # Ambient bubbles generator
        if random.random() < 0.15:
            bubbles.append({
                "x": random.uniform(80, REFERENCE_WIDTH - 80),
                "y": float(REFERENCE_HEIGHT - 60),
                "vy": random.uniform(-2.5, -1.2),
                "vx": random.uniform(-0.3, 0.3),
                "size": random.uniform(5.0, 14.0),
            })

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    # Drop food
                    food_pellets.append({"x": random.uniform(200, 800), "y": 90.0, "vy": 1.2})
                elif event.key == pygame.K_a:
                    spawn_creature()
                elif event.key == pygame.K_g:
                    glow_mode = not glow_mode
                    sounds.play("glow")

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if not _is_safe_point(screen, event.pos):
                    continue
                logical = canvas.pointer(event.pos)
                if logical is None:
                    continue
                mx, my = logical

                # Bottom Toolbar Actions
                tool_y = REFERENCE_HEIGHT - 85
                # 0: Add Fish Button
                if pygame.Rect(100, tool_y, 180, 72).collidepoint(mx, my):
                    spawn_creature()
                    continue

                # 1: Feed Button
                if pygame.Rect(310, tool_y, 180, 72).collidepoint(mx, my):
                    for _ in range(5):
                        food_pellets.append({
                            "x": random.uniform(200, REFERENCE_WIDTH - 200),
                            "y": random.uniform(80, 120),
                            "vy": random.uniform(1.0, 1.8),
                        })
                    sounds.play("splash")
                    try:
                        emit_activity_event("aquarium.fish_fed", {"pellets": len(food_pellets)})
                    except Exception:
                        pass
                    continue

                # 2: Bubbles Button
                if pygame.Rect(520, tool_y, 180, 72).collidepoint(mx, my):
                    for _ in range(15):
                        bubbles.append({
                            "x": random.uniform(100, REFERENCE_WIDTH - 100),
                            "y": random.uniform(300, 500),
                            "vy": random.uniform(-3.5, -1.8),
                            "vx": random.uniform(-0.5, 0.5),
                            "size": random.uniform(8.0, 20.0),
                        })
                    sounds.play("bubble")
                    continue

                # 3: Glow Toggle Button
                if pygame.Rect(730, tool_y, 180, 72).collidepoint(mx, my):
                    glow_mode = not glow_mode
                    sounds.play("glow")
                    try:
                        emit_activity_event("aquarium.glow_mode_toggled", {"glow": glow_mode})
                    except Exception:
                        pass
                    continue

                # Pop bubbles by clicking
                popped = False
                for b in bubbles:
                    if math.hypot(b["x"] - mx, b["y"] - my) < b["size"] * 1.5:
                        bubbles.remove(b)
                        sounds.play("bubble")
                        for _ in range(6):
                            particles.append({
                                "x": float(mx),
                                "y": float(my),
                                "vx": random.uniform(-1.5, 1.5),
                                "vy": random.uniform(-1.5, 1.5),
                                "color": (186, 230, 253),
                                "size": random.uniform(2.0, 4.0),
                                "life": 1.0,
                                "decay": 0.05,
                            })
                        popped = True
                        break
                if popped:
                    continue

                # Tickle creature (puff up pufferfish or speed up)
                for c in creatures:
                    if math.hypot(c["x"] - mx, c["y"] - my) < c["spec"]["size"] * 1.8:
                        c["puffed"] = 1.0
                        sounds.play("bubble")
                        for _ in range(8):
                            particles.append({
                                "x": float(c["x"]),
                                "y": float(c["y"]),
                                "vx": random.uniform(-1.5, 1.5),
                                "vy": random.uniform(-1.5, 1.5),
                                "color": (254, 240, 138),
                                "size": random.uniform(3.0, 6.0),
                                "life": 1.0,
                                "decay": 0.04,
                            })
                        break

        # Update creatures
        for c in creatures:
            c["swim_t"] += 0.05
            if c["puffed"] > 0:
                c["puffed"] = max(0.0, c["puffed"] - 0.02)

            # Food attraction
            if food_pellets:
                nearest = min(food_pellets, key=lambda f: math.hypot(f["x"] - c["x"], f["y"] - c["y"]))
                f_dist = math.hypot(nearest["x"] - c["x"], nearest["y"] - c["y"])
                if f_dist < 180.0:
                    c["vx"] = 2.0 if nearest["x"] > c["x"] else -2.0
                    c["vy"] = 1.2 if nearest["y"] > c["y"] else -1.2
                    if f_dist < 20.0:
                        if nearest in food_pellets:
                            food_pellets.remove(nearest)
                            sounds.play("nibble")
                            for _ in range(6):
                                particles.append({
                                    "x": float(c["x"]),
                                    "y": float(c["y"]),
                                    "vx": random.uniform(-1.0, 1.0),
                                    "vy": random.uniform(-1.0, 1.0),
                                    "color": (254, 202, 87),
                                    "size": random.uniform(2.0, 5.0),
                                    "life": 1.0,
                                    "decay": 0.04,
                                })

            c["x"] += c["vx"]
            c["y"] += c["vy"] + math.sin(c["swim_t"]) * 0.4

            # Boundary bounce
            if c["x"] < 80:
                c["x"] = 80
                c["vx"] = abs(c["vx"])
            elif c["x"] > REFERENCE_WIDTH - 80:
                c["x"] = REFERENCE_WIDTH - 80
                c["vx"] = -abs(c["vx"])

            if c["y"] < 90:
                c["y"] = 90
                c["vy"] = abs(c["vy"])
            elif c["y"] > REFERENCE_HEIGHT - 120:
                c["y"] = REFERENCE_HEIGHT - 120
                c["vy"] = -abs(c["vy"])

        # Update food pellets
        surviving_food = []
        for f in food_pellets:
            f["y"] += f["vy"]
            if f["y"] < REFERENCE_HEIGHT - 80:
                surviving_food.append(f)
        food_pellets = surviving_food

        # Update bubbles
        surviving_b = []
        for b in bubbles:
            b["y"] += b["vy"]
            b["x"] += b["vx"]
            if b["y"] > 70:
                surviving_b.append(b)
        bubbles = surviving_b

        # Update particles
        surviving_p = []
        for p in particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= p["decay"]
            if p["life"] > 0:
                surviving_p.append(p)
        particles = surviving_p

        # RENDER TO CANVAS
        surf = canvas.surface

        # 1. Water Background (Daylight Teal vs Bioluminescent Deep Ocean)
        if glow_mode:
            surf.fill((10, 15, 45))  # Midnight glow
            # Glowing Jellyfish in background
            for jx, jy in [(200, 180), (750, 220), (450, 140)]:
                pygame.draw.circle(surf, (192, 132, 252), (jx, int(jy + math.sin(t_now * 2.0 + jx) * 15)), 22)
                for tx in range(jx - 12, jx + 13, 6):
                    pygame.draw.line(surf, (216, 180, 254), (tx, int(jy + math.sin(t_now * 2.0 + jx) * 15)), (tx, int(jy + math.sin(t_now * 2.0 + jx) * 15) + 30), 2)
        else:
            surf.fill((14, 165, 233))  # Tropical cyan ocean

        # 2. Swaying Kelp Seaweed Forests
        for kx in range(40, REFERENCE_WIDTH, 110):
            kelp_col = (134, 239, 172) if glow_mode else (22, 101, 52)
            pts = [(kx, REFERENCE_HEIGHT - 60)]
            for ky in range(REFERENCE_HEIGHT - 60, 200, -40):
                sway = math.sin(t_now * 2.5 + kx * 0.1 + ky * 0.05) * 16.0
                pts.append((kx + int(sway), ky))
            if len(pts) > 1:
                pygame.draw.lines(surf, kelp_col, False, pts, 8)

        # 3. Sandy Seafloor & Shells
        sand_col = (45, 30, 70) if glow_mode else (254, 243, 199)
        pygame.draw.rect(surf, sand_col, (0, REFERENCE_HEIGHT - 80, REFERENCE_WIDTH, 80))
        for sx in [150, 340, 520, 780, 920]:
            shell_col = (254, 202, 87) if glow_mode else (244, 114, 182)
            pygame.draw.circle(surf, shell_col, (sx, REFERENCE_HEIGHT - 70), 12)
            pygame.draw.circle(surf, (255, 255, 255), (sx, REFERENCE_HEIGHT - 70), 6)

        # 4. Draw Food Pellets
        for f in food_pellets:
            pygame.draw.circle(surf, (245, 158, 11), (int(f["x"]), int(f["y"])), 5)
            pygame.draw.circle(surf, (254, 240, 138), (int(f["x"] - 1), int(f["y"] - 1)), 2)

        # 5. Draw Creatures
        for c in creatures:
            sp = c["spec"]
            cx = int(c["x"])
            cy = int(c["y"])
            facing_right = c["vx"] > 0
            base_sz = sp["size"] + int(c["puffed"] * 18.0)

            # Tail fin
            tail_dir = -1 if facing_right else 1
            tail_x = cx + tail_dir * (base_sz + 8)
            tail_sway = math.sin(c["swim_t"] * 3.0) * 8.0
            pygame.draw.polygon(surf, sp["color"], [
                (cx + tail_dir * base_sz, cy),
                (int(tail_x), int(cy - 12 + tail_sway)),
                (int(tail_x), int(cy + 12 + tail_sway)),
            ])

            # Body
            pygame.draw.ellipse(surf, sp["color"], (cx - base_sz, cy - base_sz // 2, base_sz * 2, base_sz))
            # Stripe
            pygame.draw.line(surf, sp["stripe"], (cx, cy - base_sz // 2), (cx, cy + base_sz // 2), max(3, base_sz // 5))

            # Eye
            eye_x = cx + (base_sz // 2 if facing_right else -base_sz // 2)
            eye_y = cy - base_sz // 6
            pygame.draw.circle(surf, (255, 255, 255), (eye_x, eye_y), max(3, base_sz // 5))
            pygame.draw.circle(surf, (20, 20, 30), (eye_x + (1 if facing_right else -1), eye_y), max(2, base_sz // 8))

        # 6. Draw Bubbles
        for b in bubbles:
            bx = int(b["x"])
            by = int(b["y"])
            bsz = int(b["size"])
            pygame.draw.circle(surf, (255, 255, 255), (bx, by), bsz, 2)
            pygame.draw.circle(surf, (255, 255, 255), (bx - bsz // 3, by - bsz // 3), max(1, bsz // 4))

        # 7. Draw Particles
        for p in particles:
            cur_sz = max(1.5, p["size"] * max(0.0, min(1.0, p["life"])))
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), int(cur_sz))

        # 8. Top HUD (Star Pill)
        star_pill = pygame.Rect(80, 16, 130, 56)
        pygame.draw.rect(surf, (255, 255, 255), star_pill, border_radius=18)
        pygame.draw.rect(surf, (56, 189, 248), star_pill, width=3, border_radius=18)
        pygame.draw.circle(surf, (56, 189, 248), (star_pill.left + 30, star_pill.centery), 16)
        s_txt = typography.render(str(len(creatures)), FontRole.DISPLAY, 28, (2, 132, 199))
        surf.blit(s_txt, (star_pill.left + 58, star_pill.centery - s_txt.get_height() // 2))

        # 9. Bottom Toolbar (Giant Chunky 180x72px Buttons with Icon + Label)
        tool_y = REFERENCE_HEIGHT - 85
        tools_info = [
            (100, 180, 0, "PESCE", (34, 197, 94)),
            (310, 180, 1, "CIBO", (249, 115, 22)),
            (520, 180, 2, "BOLLE", (56, 189, 248)),
            (730, 180, 3, "LUCE", (168, 85, 247) if glow_mode else (71, 85, 105)),
        ]

        for bx, bw, t_idx, lbl, col in tools_info:
            b_rect = pygame.Rect(bx, tool_y, bw, 72)
            pygame.draw.rect(surf, col, b_rect, border_radius=20)
            pygame.draw.rect(surf, (255, 255, 255), b_rect, width=3, border_radius=20)
            cx = b_rect.centerx
            cy = b_rect.top + 28

            if t_idx == 0:
                # 0: Giant Clownfish Icon
                pygame.draw.ellipse(surf, (255, 107, 107), pygame.Rect(cx - 22, cy - 12, 34, 24))
                pygame.draw.polygon(surf, (255, 107, 107), [(cx + 8, cy), (cx + 22, cy - 10), (cx + 22, cy + 10)])
                pygame.draw.ellipse(surf, (255, 255, 255), pygame.Rect(cx - 6, cy - 12, 8, 24))
                pygame.draw.circle(surf, (255, 255, 255), (cx - 12, cy - 4), 5)
                pygame.draw.circle(surf, (15, 23, 42), (cx - 13, cy - 4), 2)

            elif t_idx == 1:
                # 1: Giant Food Shaker Bottle & Pellets
                pygame.draw.rect(surf, (254, 240, 138), pygame.Rect(cx - 16, cy - 12, 20, 24), border_radius=5)
                pygame.draw.rect(surf, (234, 88, 12), pygame.Rect(cx - 12, cy - 18, 12, 6), border_radius=2)
                pygame.draw.circle(surf, (251, 146, 60), (cx + 12, cy - 6), 4)
                pygame.draw.circle(surf, (251, 146, 60), (cx + 16, cy + 4), 5)
                pygame.draw.circle(surf, (251, 146, 60), (cx + 10, cy + 12), 4)

            elif t_idx == 2:
                # 2: Giant Bubbles Cluster
                pygame.draw.circle(surf, (255, 255, 255), (cx - 10, cy + 4), 11, 2)
                pygame.draw.circle(surf, (255, 255, 255), (cx + 10, cy - 6), 14, 2)
                pygame.draw.circle(surf, (255, 255, 255), (cx - 2, cy - 14), 7, 2)

            elif t_idx == 3:
                # 3: Giant Sparkle Wand / Magic Glow Light
                pygame.draw.circle(surf, (254, 240, 138), (cx, cy), 13)
                pygame.draw.circle(surf, (255, 255, 255), (cx, cy), 6)
                for ang in (0, 45, 90, 135, 180, 225, 270, 315):
                    rad = math.radians(ang)
                    pygame.draw.line(surf, (254, 240, 138), (cx + int(math.cos(rad)*14), cy + int(math.sin(rad)*14)), (cx + int(math.cos(rad)*19), cy + int(math.sin(rad)*19)), 2)

            # Supporting label underneath
            lbl_surf = typography.render(lbl, FontRole.DISPLAY, 16, (255, 255, 255))
            surf.blit(lbl_surf, (cx - lbl_surf.get_width() // 2, b_rect.bottom - 22))

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
                "creatures_count": len(creatures),
                "timestamp": time.time(),
            })
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
