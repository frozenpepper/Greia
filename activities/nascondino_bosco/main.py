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
STORAGE_KEY = "nascondino_bosco.progress.v2"
SEASONS = ["spring", "summer", "autumn"]

ANIMALS = [
    {"id": "fox", "color": (249, 115, 22), "belly": (255, 237, 213), "cue": "tail"},
    {"id": "bunny", "color": (255, 255, 255), "belly": (244, 114, 182), "cue": "ears"},
    {"id": "owl", "color": (161, 98, 7), "belly": (254, 240, 138), "cue": "eyes"},
    {"id": "frog", "color": (34, 197, 94), "belly": (187, 247, 208), "cue": "eyes"},
    {"id": "squirrel", "color": (217, 119, 6), "belly": (254, 215, 170), "cue": "tail"},
    {"id": "hedgehog", "color": (120, 53, 15), "belly": (254, 243, 199), "cue": "nose"},
]

SPOTS = [
    {"id": "tree_hollow", "x": 160, "y": 280, "w": 180, "h": 220, "kind": "tree"},
    {"id": "berry_bush", "x": 340, "y": 420, "w": 190, "h": 140, "kind": "bush"},
    {"id": "rock_cave", "x": 580, "y": 410, "w": 190, "h": 140, "kind": "rock"},
    {"id": "pond_reeds", "x": 820, "y": 420, "w": 180, "h": 140, "kind": "pond"},
    {"id": "tall_pine", "x": 860, "y": 210, "w": 160, "h": 220, "kind": "pine"},
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


class WoodlandAudio:
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
        # Rustle / Peek sound
        rustle_samples = []
        for i in range(int(rate * 0.08)):
            t = i / rate
            env = math.exp(-15.0 * t)
            val = random.uniform(-1.0, 1.0)
            rustle_samples.append(int(32767.0 * 0.20 * env * val))
        self._sounds["rustle"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(rustle_samples)))

        # Joyful pop chime
        pop_samples = []
        for i in range(int(rate * 0.25)):
            t = i / rate
            env = math.exp(-6.0 * t)
            freq = 440.0 + 440.0 * (t / 0.25)
            val = math.sin(2.0 * math.pi * freq * t)
            pop_samples.append(int(32767.0 * 0.32 * env * val))
        self._sounds["pop"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(pop_samples)))

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


def _draw_animal_portrait(surface: pygame.Surface, animal_id: str, cx: int, cy: int, size: int) -> None:
    r = size // 2
    if animal_id == "fox":
        pygame.draw.circle(surface, (249, 115, 22), (cx, cy), r)
        pygame.draw.polygon(surface, (249, 115, 22), [(cx - r, cy - r // 3), (cx - r * 3 // 4, cy - r), (cx - r // 4, cy - r // 2)])
        pygame.draw.polygon(surface, (249, 115, 22), [(cx + r, cy - r // 3), (cx + r * 3 // 4, cy - r), (cx + r // 4, cy - r // 2)])
        pygame.draw.circle(surface, (255, 237, 213), (cx - r // 3, cy + r // 4), r // 3)
        pygame.draw.circle(surface, (255, 237, 213), (cx + r // 3, cy + r // 4), r // 3)
        pygame.draw.circle(surface, (20, 20, 30), (cx - r // 3, cy - r // 6), max(2, r // 6))
        pygame.draw.circle(surface, (20, 20, 30), (cx + r // 3, cy - r // 6), max(2, r // 6))
        pygame.draw.circle(surface, (20, 20, 30), (cx, cy + r // 5), max(2, r // 7))

    elif animal_id == "bunny":
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy + r // 4), r * 3 // 4)
        pygame.draw.ellipse(surface, (255, 255, 255), pygame.Rect(cx - r // 2, cy - r, r // 3, r))
        pygame.draw.ellipse(surface, (244, 114, 182), pygame.Rect(cx - r // 2 + 2, cy - r + 4, r // 3 - 4, r - 8))
        pygame.draw.ellipse(surface, (255, 255, 255), pygame.Rect(cx + r // 6, cy - r, r // 3, r))
        pygame.draw.ellipse(surface, (244, 114, 182), pygame.Rect(cx + r // 6 + 2, cy - r + 4, r // 3 - 4, r - 8))
        pygame.draw.circle(surface, (20, 20, 30), (cx - r // 4, cy + r // 6), max(2, r // 7))
        pygame.draw.circle(surface, (20, 20, 30), (cx + r // 4, cy + r // 6), max(2, r // 7))
        pygame.draw.circle(surface, (244, 114, 182), (cx, cy + r // 3), max(2, r // 8))

    elif animal_id == "owl":
        pygame.draw.circle(surface, (161, 98, 7), (cx, cy), r)
        # Giant glowing eyes
        pygame.draw.circle(surface, (254, 240, 138), (cx - r // 3, cy - r // 6), r // 3)
        pygame.draw.circle(surface, (254, 240, 138), (cx + r // 3, cy - r // 6), r // 3)
        pygame.draw.circle(surface, (20, 20, 30), (cx - r // 3, cy - r // 6), r // 6)
        pygame.draw.circle(surface, (20, 20, 30), (cx + r // 3, cy - r // 6), r // 6)
        # Beak
        pygame.draw.polygon(surface, (249, 115, 22), [(cx - 4, cy), (cx + 4, cy), (cx, cy + r // 3)])

    elif animal_id == "frog":
        pygame.draw.circle(surface, (34, 197, 94), (cx, cy), r)
        pygame.draw.circle(surface, (34, 197, 94), (cx - r // 2, cy - r // 2), r // 3)
        pygame.draw.circle(surface, (34, 197, 94), (cx + r // 2, cy - r // 2), r // 3)
        pygame.draw.circle(surface, (255, 255, 255), (cx - r // 2, cy - r // 2), r // 5)
        pygame.draw.circle(surface, (255, 255, 255), (cx + r // 2, cy - r // 2), r // 5)
        pygame.draw.circle(surface, (20, 20, 30), (cx - r // 2, cy - r // 2), r // 8)
        pygame.draw.circle(surface, (20, 20, 30), (cx + r // 2, cy - r // 2), r // 8)
        pygame.draw.arc(surface, (20, 20, 30), pygame.Rect(cx - r // 2, cy - r // 4, r, r // 2), 3.4, 6.0, 3)

    elif animal_id == "squirrel":
        pygame.draw.circle(surface, (217, 119, 6), (cx, cy), r)
        pygame.draw.circle(surface, (254, 215, 170), (cx - r // 3, cy + r // 4), r // 3)
        pygame.draw.circle(surface, (254, 215, 170), (cx + r // 3, cy + r // 4), r // 3)
        pygame.draw.circle(surface, (20, 20, 30), (cx - r // 4, cy - r // 6), max(2, r // 7))
        pygame.draw.circle(surface, (20, 20, 30), (cx + r // 4, cy - r // 6), max(2, r // 7))
        pygame.draw.circle(surface, (20, 20, 30), (cx, cy + r // 5), max(2, r // 8))

    else:  # hedgehog
        pygame.draw.circle(surface, (120, 53, 15), (cx, cy), r)
        pygame.draw.circle(surface, (254, 243, 199), (cx - r // 4, cy + r // 6), r // 2)
        pygame.draw.circle(surface, (20, 20, 30), (cx - r // 3, cy), max(2, r // 7))
        pygame.draw.circle(surface, (20, 20, 30), (cx - r * 2 // 3, cy + r // 6), max(2, r // 6))


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
    sounds = WoodlandAudio()

    storage = get_storage()
    saved_data = storage.kv_get(STORAGE_KEY) if storage else {}
    if not isinstance(saved_data, dict):
        saved_data = {}
    total_stars = saved_data.get("stars", 0)

    # Game state
    hiding_map: dict[str, str] = {}  # spot_id -> animal_id
    target_animal_id = "fox"
    found_count = 0
    total_to_find = 4
    is_victory = False

    # Leaping animal animation state
    leaping_animal: dict[str, Any] | None = None
    particles: list[dict[str, Any]] = []

    def start_round() -> None:
        nonlocal hiding_map, target_animal_id, found_count
        shuffled_animals = random.sample(ANIMALS, len(SPOTS))
        hiding_map = {spot["id"]: animal["id"] for spot, animal in zip(SPOTS, shuffled_animals)}
        target_animal_id = random.choice(list(hiding_map.values()))
        found_count = 0

    start_round()

    running = True
    ready_published = False

    while running and not activity_stop_requested():
        t_now = time.time()

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
                        start_round()
                    continue

                # Check tapping on Hiding Spots
                for spot in SPOTS:
                    spot_rect = pygame.Rect(spot["x"] - spot["w"] // 2, spot["y"] - spot["h"] // 2, spot["w"], spot["h"])
                    if spot_rect.collidepoint(mx, my):
                        animal_id = hiding_map.get(spot["id"])
                        if animal_id is not None:
                            sounds.play("pop")
                            sounds.play("rustle")
                            # Start leap animation
                            leaping_animal = {
                                "animal_id": animal_id,
                                "cx": spot["x"],
                                "cy": spot["y"],
                                "t": 0.0,
                                "is_target": (animal_id == target_animal_id),
                            }
                            # Sparkles
                            for _ in range(12):
                                particles.append({
                                    "x": spot["x"],
                                    "y": spot["y"],
                                    "vx": random.uniform(-4, 4),
                                    "vy": random.uniform(-6, -1),
                                    "color": (254, 240, 138),
                                    "size": random.uniform(5, 10),
                                    "life": 1.0,
                                })

                            if animal_id == target_animal_id:
                                found_count += 1
                                total_stars += 1
                                if storage:
                                    storage.kv_set(STORAGE_KEY, {"stars": total_stars})
                                try:
                                    emit_activity_event("woodland.animal_found", {"animal": animal_id, "stars": total_stars})
                                except Exception:
                                    pass

                                # Pick new target animal or victory
                                if found_count >= total_to_find:
                                    is_victory = True
                                    sounds.play("win")
                                else:
                                    remaining = [a for a in hiding_map.values() if a != target_animal_id]
                                    if remaining:
                                        target_animal_id = random.choice(remaining)

        # Update leap animation
        if leaping_animal is not None:
            leaping_animal["t"] += 0.04
            if leaping_animal["t"] > 1.2:
                leaping_animal = None

        # Update particles
        surviving_p = []
        for p in particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 0.03
            if p["life"] > 0:
                surviving_p.append(p)
        particles = surviving_p

        # RENDER TO CANVAS
        surf = canvas.surface

        # 1. Forest Sky & Rolling Hills
        surf.fill((186, 230, 253))  # Soft sky
        pygame.draw.circle(surf, (254, 240, 138), (140, 90), 45)

        # Pine backdrop trees
        for bx in range(40, REFERENCE_WIDTH, 140):
            pygame.draw.polygon(surf, (74, 222, 128), [(bx, 280), (bx + 70, 120), (bx + 140, 280)])
            pygame.draw.polygon(surf, (34, 197, 94), [(bx + 15, 280), (bx + 70, 160), (bx + 125, 280)])

        # Green ground
        pygame.draw.rect(surf, (34, 197, 94), (0, 360, REFERENCE_WIDTH, 240))
        pygame.draw.ellipse(surf, (22, 163, 74), pygame.Rect(-100, 340, 600, 100))
        pygame.draw.ellipse(surf, (22, 163, 74), pygame.Rect(450, 340, 700, 100))

        # 2. Draw Hiding Spots with Animated Peeking Clues
        for spot in SPOTS:
            sx, sy, sw, sh = spot["x"], spot["y"], spot["w"], spot["h"]
            animal_id = hiding_map.get(spot["id"])

            if spot["kind"] == "tree":
                # Hollow Oak Tree
                pygame.draw.rect(surf, (120, 53, 15), (sx - 40, sy - 50, 80, 150), border_radius=12)
                pygame.draw.circle(surf, (34, 197, 94), (sx, sy - 80), 85)
                # Hollow Hole
                pygame.draw.ellipse(surf, (40, 20, 10), pygame.Rect(sx - 35, sy, 70, 80))
                # Animated Clue inside Tree Hollow (Blinking Owl Eyes)
                if animal_id == "owl":
                    blink = abs(math.sin(t_now * 3.0)) > 0.15
                    if blink:
                        pygame.draw.circle(surf, (254, 240, 138), (sx - 14, sy + 35), 10)
                        pygame.draw.circle(surf, (20, 20, 30), (sx - 14, sy + 35), 5)
                        pygame.draw.circle(surf, (254, 240, 138), (sx + 14, sy + 35), 10)
                        pygame.draw.circle(surf, (20, 20, 30), (sx + 14, sy + 35), 5)
                elif animal_id:
                    _draw_animal_portrait(surf, animal_id, sx, sy + 35, 36)

            elif spot["kind"] == "bush":
                # Lush Berry Bush
                pygame.draw.circle(surf, (22, 163, 74), (sx - 45, sy), 55)
                pygame.draw.circle(surf, (34, 197, 94), (sx + 45, sy), 55)
                pygame.draw.circle(surf, (74, 222, 128), (sx, sy - 20), 65)
                # Berries
                for b_off in [(-30, -10), (25, 0), (-10, 20), (35, -25)]:
                    pygame.draw.circle(surf, (239, 68, 68), (sx + b_off[0], sy + b_off[1]), 8)
                # Animated Clue (Twitching Bunny Ears or Wagging Fox Tail)
                if animal_id == "bunny":
                    ear_w = math.sin(t_now * 6.0) * 4.0
                    pygame.draw.ellipse(surf, (255, 255, 255), pygame.Rect(sx - 20 + ear_w, sy - 75, 16, 40))
                    pygame.draw.ellipse(surf, (244, 114, 182), pygame.Rect(sx - 16 + ear_w, sy - 70, 8, 26))
                    pygame.draw.ellipse(surf, (255, 255, 255), pygame.Rect(sx + 4 - ear_w, sy - 75, 16, 40))
                    pygame.draw.ellipse(surf, (244, 114, 182), pygame.Rect(sx + 8 - ear_w, sy - 70, 8, 26))
                elif animal_id == "fox":
                    tail_w = math.sin(t_now * 4.0) * 15.0
                    pygame.draw.circle(surf, (249, 115, 22), (int(sx + 65 + tail_w), sy - 25), 22)
                    pygame.draw.circle(surf, (255, 255, 255), (int(sx + 78 + tail_w), sy - 30), 10)
                elif animal_id:
                    _draw_animal_portrait(surf, animal_id, sx, sy - 35, 34)

            elif spot["kind"] == "rock":
                # Cozy Stone Cave
                pygame.draw.ellipse(surf, (100, 116, 139), pygame.Rect(sx - 80, sy - 50, 160, 120))
                pygame.draw.ellipse(surf, (30, 41, 59), pygame.Rect(sx - 50, sy - 20, 100, 80))
                # Sniffing Hedgehog Nose or Eyes
                if animal_id == "hedgehog":
                    sniff = math.sin(t_now * 8.0) * 3.0
                    pygame.draw.circle(surf, (254, 243, 199), (sx, sy + 15), 18)
                    pygame.draw.circle(surf, (20, 20, 30), (int(sx - 15 + sniff), sy + 15), 6)
                elif animal_id:
                    _draw_animal_portrait(surf, animal_id, sx, sy + 15, 36)

            elif spot["kind"] == "pond":
                # Sparkling Water Pond & Reeds
                pygame.draw.ellipse(surf, (56, 189, 248), pygame.Rect(sx - 80, sy - 10, 160, 80))
                for rx in range(sx - 50, sx + 60, 18):
                    pygame.draw.rect(surf, (22, 101, 52), (rx, sy - 50, 6, 70), border_radius=3)
                    pygame.draw.ellipse(surf, (120, 53, 15), pygame.Rect(rx - 2, sy - 55, 10, 25))
                # Splashing Frog Eyes
                if animal_id == "frog":
                    f_y = sy - 30 + math.sin(t_now * 5.0) * 8.0
                    pygame.draw.circle(surf, (34, 197, 94), (sx - 16, int(f_y)), 12)
                    pygame.draw.circle(surf, (255, 255, 255), (sx - 16, int(f_y)), 7)
                    pygame.draw.circle(surf, (20, 20, 30), (sx - 16, int(f_y)), 4)
                    pygame.draw.circle(surf, (34, 197, 94), (sx + 16, int(f_y)), 12)
                    pygame.draw.circle(surf, (255, 255, 255), (sx + 16, int(f_y)), 7)
                    pygame.draw.circle(surf, (20, 20, 30), (sx + 16, int(f_y)), 4)
                elif animal_id:
                    _draw_animal_portrait(surf, animal_id, sx, sy - 15, 34)

            else:  # pine
                # Tall Evergreen Pine
                pygame.draw.rect(surf, (90, 55, 35), (sx - 20, sy - 20, 40, 120), border_radius=6)
                pygame.draw.polygon(surf, (22, 101, 52), [(sx - 70, sy + 30), (sx, sy - 80), (sx + 70, sy + 30)])
                pygame.draw.polygon(surf, (34, 197, 94), [(sx - 55, sy - 20), (sx, sy - 120), (sx + 55, sy - 20)])
                # Squirrel Tail Clue
                if animal_id == "squirrel":
                    s_tail = math.sin(t_now * 5.0) * 12.0
                    pygame.draw.circle(surf, (217, 119, 6), (int(sx + 45 + s_tail), sy - 35), 20)
                    pygame.draw.circle(surf, (254, 215, 170), (int(sx + 52 + s_tail), sy - 40), 10)
                elif animal_id:
                    _draw_animal_portrait(surf, animal_id, sx, sy - 35, 34)

        # 3. Leaping Animal Animation
        if leaping_animal is not None:
            t = leaping_animal["t"]
            anim_sz = int(80 + math.sin(t * math.pi) * 50)
            anim_y = leaping_animal["cy"] - math.sin(t * math.pi) * 140.0
            _draw_animal_portrait(surf, leaping_animal["animal_id"], leaping_animal["cx"], int(anim_y), anim_sz)

        # 4. Particles
        for p in particles:
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), int(p["size"]))

        # 5. Top Center "WANTED ANIMAL" Target Card (Icon + Label)
        target_card = pygame.Rect(REFERENCE_WIDTH // 2 - 160, 14, 320, 94)
        pygame.draw.rect(surf, (255, 252, 245), target_card, border_radius=24)
        pygame.draw.rect(surf, (234, 179, 8), target_card, width=4, border_radius=24)

        # Magnifying glass icon on left
        pygame.draw.circle(surf, (59, 130, 246), (target_card.left + 36, target_card.centery - 5), 18, 4)
        pygame.draw.line(surf, (59, 130, 246), (target_card.left + 48, target_card.centery + 7), (target_card.left + 62, target_card.centery + 21), 5)

        # Target Animal Giant Portrait
        _draw_animal_portrait(surf, target_animal_id, target_card.left + 115, target_card.centery, 68)

        # Animal Name Text
        animal_names_it = {
            "fox": "VOLPE",
            "bunny": "CONIGLIO",
            "deer": "CERVO",
            "owl": "GUFO",
            "hedgehog": "RICCIO",
            "squirrel": "SCOIATTOLO",
        }
        name_str = animal_names_it.get(target_animal_id, "ANIMALE")
        n_txt = typography.render(name_str, FontRole.DISPLAY, 18, (180, 83, 9))
        surf.blit(n_txt, (target_card.left + 160, target_card.centery - n_txt.get_height() // 2))

        # Progress Stars on Target Card
        for s in range(total_to_find):
            st_x = target_card.right - 35 + (s % 2) * 18
            st_y = target_card.top + 28 + (s // 2) * 28
            if s < found_count:
                pygame.draw.circle(surf, (234, 179, 8), (st_x, st_y), 8)
            else:
                pygame.draw.circle(surf, (203, 213, 225), (st_x, st_y), 8, 2)

        # 6. Star Pill (Top Left)
        star_pill = pygame.Rect(80, 16, 130, 56)
        pygame.draw.rect(surf, (255, 255, 255), star_pill, border_radius=18)
        pygame.draw.rect(surf, (234, 179, 8), star_pill, width=3, border_radius=18)
        pygame.draw.circle(surf, (234, 179, 8), (star_pill.left + 30, star_pill.centery), 16)
        s_txt = typography.render(str(total_stars), FontRole.DISPLAY, 28, (180, 83, 9))
        surf.blit(s_txt, (star_pill.left + 58, star_pill.centery - s_txt.get_height() // 2))

        # 7. Victory Celebration Modal
        if is_victory:
            overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 15, 30, 210))
            surf.blit(overlay, (0, 0))

            card = pygame.Rect(REFERENCE_WIDTH // 2 - 250, REFERENCE_HEIGHT // 2 - 160, 500, 320)
            pygame.draw.rect(surf, (255, 252, 245), card, border_radius=28)
            pygame.draw.rect(surf, (234, 179, 8), card, width=5, border_radius=28)

            v_title = typography.render("TROVATI TUTTI!", FontRole.DISPLAY, 32, (217, 119, 6))
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
