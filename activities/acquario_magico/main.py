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
STORAGE_KEY = "acquario_magico.progress.v1"
ASSETS_DIR = Path(__file__).parent / "assets" / "runtime"

SPECIES = [
    {"id": "clownfish", "name_it": "Pesce Pagliaccio 🐠", "name_en": "Clownfish 🐠", "color": (249, 115, 22), "stripe": (255, 255, 255), "size": 36, "w": 72, "h": 54},
    {"id": "turtle", "name_it": "Tartaruga 🐢", "name_en": "Sea Turtle 🐢", "color": (34, 197, 94), "stripe": (22, 101, 52), "size": 44, "w": 88, "h": 66},
    {"id": "octopus", "name_it": "Polipetto 🐙", "name_en": "Octopus 🐙", "color": (236, 72, 153), "stripe": (244, 114, 182), "size": 40, "w": 76, "h": 76},
    {"id": "dolphin", "name_it": "Delfino 🐬", "name_en": "Dolphin 🐬", "color": (59, 130, 246), "stripe": (191, 219, 254), "size": 52, "w": 104, "h": 70},
    {"id": "puffer", "name_it": "Pesce Palla 🐡", "name_en": "Pufferfish 🐡", "color": (234, 179, 8), "stripe": (254, 240, 138), "size": 38, "w": 76, "h": 76},
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

    def play(self, name: str) -> None:
        snd = self._sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass


# Surface and Scale Cache
_IMAGE_CACHE: dict[str, pygame.Surface] = {}
_SCALE_CACHE: dict[tuple[str, int, int], pygame.Surface] = {}


def _load_asset_surface(filename: str) -> pygame.Surface | None:
    if filename not in _IMAGE_CACHE:
        p = ASSETS_DIR / filename
        if p.exists():
            try:
                _IMAGE_CACHE[filename] = pygame.image.load(str(p)).convert_alpha()
            except Exception:
                _IMAGE_CACHE[filename] = None
        else:
            _IMAGE_CACHE[filename] = None
    return _IMAGE_CACHE[filename]


def _get_scaled_asset(filename: str, width: int, height: int) -> pygame.Surface | None:
    key = (filename, width, height)
    if key not in _SCALE_CACHE:
        orig = _load_asset_surface(filename)
        if orig is not None:
            _SCALE_CACHE[key] = pygame.transform.smoothscale(orig, (width, height))
        else:
            _SCALE_CACHE[key] = None
    return _SCALE_CACHE[key]


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

    storage = get_storage()
    saved_data = storage.kv_get(STORAGE_KEY) if storage else {}
    if not isinstance(saved_data, dict):
        saved_data = {}

    glow_mode = False
    active_tool = 0  # 0: Spawn Fish, 1: Drop Food, 2: Blow Bubbles, 3: Day/Night Glow Toggle

    creatures: list[dict[str, Any]] = []
    bubbles: list[dict[str, Any]] = []
    food_pellets: list[dict[str, Any]] = []
    particles: list[dict[str, Any]] = []

    def spawn_creature(x: float, y: float, spec_idx: int | None = None) -> None:
        if len(creatures) >= 24:
            creatures.pop(0)
        sp = SPECIES[spec_idx if spec_idx is not None else random.randint(0, len(SPECIES) - 1)]
        vx = random.choice([-1.5, -1.0, 1.0, 1.5])
        creatures.append({
            "spec": sp,
            "x": float(x),
            "y": float(y),
            "vx": vx,
            "vy": random.uniform(-0.4, 0.4),
            "target_y": float(y),
            "puffed": 0.0,
            "swim_t": random.random() * 6.28,
        })

    # Initial fish
    spawn_creature(300, 250, 0)
    spawn_creature(500, 180, 1)
    spawn_creature(700, 320, 2)
    spawn_creature(400, 380, 4)

    ready_published = False

    running = True
    while running and not activity_stop_requested():
        t_now = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    glow_mode = not glow_mode
                    sounds.play("glow")
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

                # Check Bottom Toolbar (y = 515..587)
                tool_y = REFERENCE_HEIGHT - 85
                tool_clicked = False
                for t_idx, bx in enumerate([100, 310, 520, 730]):
                    if pygame.Rect(bx, tool_y, 180, 72).collidepoint(mx, my):
                        active_tool = t_idx
                        tool_clicked = True
                        if t_idx == 3:  # Toggle Day/Night Glow Mode
                            glow_mode = not glow_mode
                            sounds.play("glow")
                        else:
                            sounds.play("bubble")
                        break

                if not tool_clicked and my < tool_y:
                    # Interact with water canvas based on selected tool
                    if active_tool == 0:
                        # Spawn Fish
                        spawn_creature(mx, my)
                        sounds.play("bubble")
                        for _ in range(8):
                            particles.append({
                                "x": float(mx), "y": float(my),
                                "vx": random.uniform(-2, 2), "vy": random.uniform(-2, 2),
                                "color": (56, 189, 248), "size": random.uniform(4, 8), "life": 1.0, "decay": 0.05
                            })
                    elif active_tool == 1:
                        # Drop Food Pellets
                        for ox in [-12, 0, 12]:
                            food_pellets.append({
                                "x": float(mx + ox), "y": float(my),
                                "vy": random.uniform(1.2, 2.0),
                                "vx": random.uniform(-0.3, 0.3),
                                "size": random.uniform(4, 6),
                            })
                        sounds.play("bubble")
                    elif active_tool == 2:
                        # Blow Bubble Stream
                        for _ in range(6):
                            bubbles.append({
                                "x": float(mx + random.uniform(-20, 20)),
                                "y": float(my + random.uniform(-10, 10)),
                                "vx": random.uniform(-0.5, 0.5),
                                "vy": random.uniform(-2.5, -4.5),
                                "size": random.uniform(8, 22),
                            })
                        sounds.play("bubble")

        # Update Creatures
        for c in creatures:
            c["swim_t"] += 0.08
            c["x"] += c["vx"]
            c["y"] += math.sin(c["swim_t"] * 2.0) * 0.8

            # Screen bounds wrap / turn around
            if c["x"] < 60:
                c["x"] = 60
                c["vx"] = abs(c["vx"])
            elif c["x"] > REFERENCE_WIDTH - 60:
                c["x"] = REFERENCE_WIDTH - 60
                c["vx"] = -abs(c["vx"])

            if c["y"] < 90:
                c["y"] = 90
            elif c["y"] > REFERENCE_HEIGHT - 120:
                c["y"] = REFERENCE_HEIGHT - 120

            # Seek nearest food
            if food_pellets:
                closest_f = min(food_pellets, key=lambda f: (f["x"] - c["x"]) ** 2 + (f["y"] - c["y"]) ** 2)
                dist_sq = (closest_f["x"] - c["x"]) ** 2 + (closest_f["y"] - c["y"]) ** 2
                if dist_sq < 3600:
                    c["vx"] += (1.0 if closest_f["x"] > c["x"] else -1.0) * 0.1
                    c["y"] += (1.0 if closest_f["y"] > c["y"] else -1.0) * 0.8
                    if dist_sq < 400:
                        food_pellets.remove(closest_f)
                        sounds.play("nibble")
                        for _ in range(6):
                            particles.append({
                                "x": c["x"], "y": c["y"],
                                "vx": random.uniform(-1.5, 1.5), "vy": random.uniform(-1.5, 1.5),
                                "color": (254, 240, 138), "size": random.uniform(3, 6), "life": 1.0, "decay": 0.06
                            })

        # Update Food Pellets
        surviving_f = []
        for f in food_pellets:
            f["y"] += f["vy"]
            f["x"] += f["vx"]
            if f["y"] < REFERENCE_HEIGHT - 90:
                surviving_f.append(f)
        food_pellets = surviving_f

        # Update Bubbles
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
            surf.fill((10, 15, 45))  # Deep midnight abyss
            # Glowing Jellyfish in background
            for jx, jy in [(200, 180), (750, 220), (450, 140)]:
                jelly_y = int(jy + math.sin(t_now * 2.0 + jx) * 16)
                pygame.draw.circle(surf, (192, 132, 252, 160), (jx, jelly_y), 24)
                pygame.draw.circle(surf, (232, 121, 249), (jx, jelly_y), 18)
                for tx in range(jx - 14, jx + 15, 6):
                    pygame.draw.line(surf, (216, 180, 254), (tx, jelly_y), (tx + int(math.sin(t_now * 4.0 + tx) * 6), jelly_y + 36), 2)
        else:
            # Tropical Cyan Ocean with Soft Gradient
            for gy in range(0, REFERENCE_HEIGHT, 16):
                ratio = gy / float(REFERENCE_HEIGHT)
                r_col = int(14 + (2 - 14) * ratio)
                g_col = int(165 + (132 - 165) * ratio)
                b_col = int(233 + (199 - 233) * ratio)
                pygame.draw.rect(surf, (r_col, g_col, b_col), (0, gy, REFERENCE_WIDTH, 16))

            # Sunlight Caustics Rays filtering down from surface
            for ray_i, rx in enumerate([140, 320, 560, 780, 920]):
                sway = math.sin(t_now * 1.5 + ray_i) * 30
                ray_pts = [(rx - 25, 0), (rx + 25, 0), (int(rx + 60 + sway), 380), (int(rx - 20 + sway), 380)]
                caustic_surf = pygame.Surface((REFERENCE_WIDTH, 400), pygame.SRCALPHA)
                pygame.draw.polygon(caustic_surf, (255, 255, 255, 30), ray_pts)
                surf.blit(caustic_surf, (0, 0))

        # 2. Swaying Kelp Seaweed Forests
        for kx in range(40, REFERENCE_WIDTH, 110):
            kelp_col = (134, 239, 172) if glow_mode else (22, 101, 52)
            pts = [(kx, REFERENCE_HEIGHT - 60)]
            for ky in range(REFERENCE_HEIGHT - 60, 180, -35):
                sway = math.sin(t_now * 2.5 + kx * 0.1 + ky * 0.05) * 18.0
                pts.append((kx + int(sway), ky))
            if len(pts) > 1:
                pygame.draw.lines(surf, kelp_col, False, pts, 8)
                pygame.draw.lines(surf, (74, 222, 128) if not glow_mode else (192, 132, 252), False, pts, 3)

        # 3. Sandy Seafloor & Coral Reefs (Grounded Marine World)
        sand_col = (45, 30, 70) if glow_mode else (254, 243, 199)
        pygame.draw.rect(surf, sand_col, (0, REFERENCE_HEIGHT - 85, REFERENCE_WIDTH, 85))
        pygame.draw.line(surf, (217, 119, 6) if not glow_mode else (88, 28, 135), (0, REFERENCE_HEIGHT - 85), (REFERENCE_WIDTH, REFERENCE_HEIGHT - 85), 3)

        # Baked Coral Reef on Left and Right Seabed
        coral_surf = _get_scaled_asset("coral_reef.png", 220, 165)
        if coral_surf is not None:
            surf.blit(coral_surf, (20, REFERENCE_HEIGHT - 210))
            surf.blit(pygame.transform.flip(coral_surf, True, False), (REFERENCE_WIDTH - 240, REFERENCE_HEIGHT - 210))

        # Seashells on Sand
        for sx in [280, 440, 620, 800]:
            shell_col = (254, 202, 87) if glow_mode else (244, 114, 182)
            pygame.draw.circle(surf, shell_col, (sx, REFERENCE_HEIGHT - 65), 12)
            pygame.draw.circle(surf, (255, 255, 255), (sx, REFERENCE_HEIGHT - 65), 6)

        # 4. Food Pellets
        for f in food_pellets:
            pygame.draw.circle(surf, (245, 158, 11), (int(f["x"]), int(f["y"])), int(f["size"]))
            pygame.draw.circle(surf, (254, 240, 138), (int(f["x"] - 1), int(f["y"] - 1)), int(f["size"] // 2))

        # 5. Marine Creatures (Illustrated Species)
        for c in creatures:
            sp = c["spec"]
            cx = int(c["x"])
            cy = int(c["y"])
            facing_r = c["vx"] > 0
            cw = sp.get("w", 72)
            ch = sp.get("h", 54)

            # Try baked high-res asset
            creature_surf = _get_scaled_asset(f"{sp['id']}.png", cw, ch)
            if creature_surf is not None:
                img = creature_surf if facing_r else pygame.transform.flip(creature_surf, True, False)
                surf.blit(img, img.get_rect(center=(cx, cy)))
            else:
                # Fallback vector ellipse
                base_sz = sp["size"]
                pygame.draw.ellipse(surf, sp["color"], (cx - base_sz, cy - base_sz // 2, base_sz * 2, base_sz))
                pygame.draw.circle(surf, (255, 255, 255), (cx + (base_sz // 2 if facing_r else -base_sz // 2), cy - base_sz // 6), 6)
                pygame.draw.circle(surf, (15, 23, 42), (cx + (base_sz // 2 if facing_r else -base_sz // 2), cy - base_sz // 6), 3)

        # 6. Bubbles
        for b in bubbles:
            bx = int(b["x"])
            by = int(b["y"])
            bsz = int(b["size"])
            pygame.draw.circle(surf, (255, 255, 255), (bx, by), bsz, 2)
            pygame.draw.circle(surf, (255, 255, 255), (bx - bsz // 3, by - bsz // 3), max(1, bsz // 4))

        # 7. Particles
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
            (730, 180, 3, "NOTTE" if not glow_mode else "GIORNO", (168, 85, 247) if glow_mode else (71, 85, 105)),
        ]

        for bx, bw, t_idx, lbl, col in tools_info:
            b_rect = pygame.Rect(bx, tool_y, bw, 72)
            is_active = (active_tool == t_idx)
            pygame.draw.rect(surf, col, b_rect, border_radius=20)
            pygame.draw.rect(surf, (254, 240, 138) if is_active else (255, 255, 255), b_rect, width=4 if is_active else 2, border_radius=20)
            cx = b_rect.centerx
            cy = b_rect.top + 28

            if t_idx == 0:
                cl_icon = _get_scaled_asset("clownfish.png", 40, 30)
                if cl_icon is not None:
                    surf.blit(cl_icon, cl_icon.get_rect(center=(cx, cy)))
            elif t_idx == 1:
                pygame.draw.rect(surf, (254, 240, 138), pygame.Rect(cx - 14, cy - 10, 18, 22), border_radius=5)
                pygame.draw.rect(surf, (234, 88, 12), pygame.Rect(cx - 10, cy - 15, 10, 5), border_radius=2)
                pygame.draw.circle(surf, (251, 146, 60), (cx + 10, cy - 4), 4)
                pygame.draw.circle(surf, (251, 146, 60), (cx + 14, cy + 5), 4)
            elif t_idx == 2:
                pygame.draw.circle(surf, (255, 255, 255), (cx - 8, cy + 4), 10, 2)
                pygame.draw.circle(surf, (255, 255, 255), (cx + 8, cy - 4), 12, 2)
            elif t_idx == 3:
                pygame.draw.circle(surf, (254, 240, 138), (cx, cy), 12)
                pygame.draw.circle(surf, (255, 255, 255), (cx, cy), 5)
                for ang in (0, 45, 90, 135, 180, 225, 270, 315):
                    rad = math.radians(ang)
                    pygame.draw.line(surf, (254, 240, 138), (cx + int(math.cos(rad)*13), cy + int(math.sin(rad)*13)), (cx + int(math.cos(rad)*17), cy + int(math.sin(rad)*17)), 2)

            lbl_surf = typography.render(lbl, FontRole.DISPLAY, 16, (255, 255, 255))
            surf.blit(lbl_surf, (cx - lbl_surf.get_width() // 2, b_rect.bottom - 22))

        canvas.present(clear=theme.background)
        pygame.display.flip()

        if not ready_published:
            mark_activity_ready()
            ready_published = True

        clock.tick(30)

    if storage is not None:
        try:
            storage.kv_set(STORAGE_KEY, {
                "species_count": len(creatures),
            })
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
