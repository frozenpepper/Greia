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
    get_shared_visual_path,
    get_storage,
    get_theme,
    get_ui_preferences,
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
from greia_platform.pygame_completion import CompletionContent, PygameCompletionScreen
from greia_platform.pygame_scene import PygameSceneRenderer
from greia_platform.scene import (
    SceneDefinition,
    SceneFit,
    SceneNode,
)
from greia_platform.scene_actor import (
    SceneActorDefinition,
    sample_scene_actor,
)
from greia_platform.typography import FontRole, GreiaTypography

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
STORAGE_KEY = "costruiamo_ponti.progress.v2"

BLOCKS = [
    {"id": "wood", "color": (180, 83, 9), "border": (146, 64, 14), "type_name": "wood"},
    {"id": "stone", "color": (100, 116, 139), "border": (71, 85, 105), "type_name": "stone"},
    {"id": "shroom", "color": (239, 68, 68), "border": (220, 38, 38), "type_name": "shroom"},
    {"id": "rainbow", "color": (168, 85, 247), "border": (147, 51, 234), "type_name": "rainbow"},
]
BLOCK_TYPES = BLOCKS

LEVELS = [
    {
        "id": "river",
        "sky": (205, 238, 252),
        "gap_water": (56, 189, 248),
        "cliff_color": (34, 197, 94),
        "required": ["wood", "wood", "shroom", "wood"],
    },
    {
        "id": "canyon",
        "sky": (254, 225, 185),
        "gap_water": (217, 119, 6),
        "cliff_color": (120, 53, 15),
        "required": ["stone", "shroom", "stone", "rainbow"],
    },
    {
        "id": "space",
        "sky": (18, 22, 45),
        "gap_water": (30, 27, 75),
        "cliff_color": (59, 130, 246),
        "required": ["rainbow", "shroom", "rainbow", "shroom"],
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
        # Place thud
        thud_samples = []
        for i in range(int(rate * 0.08)):
            t = i / rate
            env = math.exp(-14.0 * t)
            val = math.sin(2.0 * math.pi * 220.0 * t)
            thud_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["place"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(thud_samples)))

        # Boing trampoline bounce
        boing_samples = []
        for i in range(int(rate * 0.22)):
            t = i / rate
            env = math.exp(-4.5 * t)
            freq = 300.0 + 500.0 * (t / 0.22)
            val = math.sin(2.0 * math.pi * freq * t)
            boing_samples.append(int(32767.0 * 0.32 * env * val))
        self._sounds["boing"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(boing_samples)))

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


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


def _draw_block_icon_procedural(surface: pygame.Surface, block_id: str, cx: int, cy: int, size: int) -> None:
    """Procedural fallback for block icons if image asset is unavailable."""
    r = size // 2
    dark = (30, 41, 59)
    if block_id == "wood":
        pygame.draw.rect(surface, (180, 83, 9), (cx - r, cy - r // 2, size, r), border_radius=8)
        pygame.draw.rect(surface, (217, 119, 6), (cx - r + 3, cy - r // 2 + 2, size - 6, r - 4), border_radius=6)
        pygame.draw.ellipse(surface, (245, 158, 11), pygame.Rect(cx + r - r // 3, cy - r // 2, r * 2 // 3, r))
        pygame.draw.circle(surface, (146, 64, 14), (cx + r, cy), max(2, r // 4))
        pygame.draw.rect(surface, dark, (cx - r, cy - r // 2, size, r), width=2, border_radius=8)
        pygame.draw.circle(surface, (254, 240, 138), (cx - r + 7, cy), max(2, r // 7))
    elif block_id == "stone":
        pygame.draw.rect(surface, (71, 85, 105), (cx - r, cy - r, size, size), border_radius=10)
        pygame.draw.rect(surface, (148, 163, 184), (cx - r + 3, cy - r + 3, size - 6, size - 6), border_radius=8)
        pygame.draw.rect(surface, (203, 213, 225), (cx - r + 5, cy - r + 5, size - 10, size // 3), border_radius=4)
        pygame.draw.rect(surface, dark, (cx - r, cy - r, size, size), width=2, border_radius=10)
    elif block_id == "shroom":
        pygame.draw.rect(surface, (255, 255, 255), (cx - r // 4, cy, r // 2, r), border_radius=4)
        pygame.draw.rect(surface, dark, (cx - r // 4, cy, r // 2, r), width=2, border_radius=4)
        pygame.draw.ellipse(surface, (239, 68, 68), pygame.Rect(cx - r, cy - r, size, r * 5 // 4))
        pygame.draw.ellipse(surface, dark, pygame.Rect(cx - r, cy - r, size, r * 5 // 4), 2)
        pygame.draw.circle(surface, (255, 255, 255), (cx - r // 2, cy - r // 3), max(3, r // 4))
        pygame.draw.circle(surface, (255, 255, 255), (cx + r // 2, cy - r // 3), max(3, r // 4))
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy - r * 2 // 3), max(3, r // 4))
    else:  # rainbow
        colors = [(239, 68, 68), (245, 158, 11), (234, 179, 8), (34, 197, 94), (59, 130, 246), (168, 85, 247)]
        for idx, col in enumerate(colors):
            rad = r - idx * max(2, r // 6)
            if rad > 2:
                pygame.draw.arc(surface, col, pygame.Rect(cx - rad, cy - rad, rad * 2, rad * 2), 0, math.pi, max(3, r // 5))
        pygame.draw.circle(surface, (255, 255, 255), (cx - r * 2 // 3, cy), max(3, r // 4))
        pygame.draw.circle(surface, (255, 255, 255), (cx + r * 2 // 3, cy), max(3, r // 4))
        pygame.draw.circle(surface, dark, (cx - r * 2 // 3, cy), max(3, r // 4), 2)
        pygame.draw.circle(surface, dark, (cx + r * 2 // 3, cy), max(3, r // 4), 2)


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

    play_again_rect = pygame.Rect(REFERENCE_WIDTH // 2 - 120, REFERENCE_HEIGHT // 2 + 70, 240, 60)
    completion = PygameCompletionScreen(
        typography,
        width=REFERENCE_WIDTH,
        height=REFERENCE_HEIGHT,
        primary_rect=play_again_rect,
    )
    completion_content = CompletionContent(
        title="OTTIMO LAVORO!",
        primary_label="GIOCA ANCORA",
        achievement_count=5,
    )
    completion_presented = False

    # Shared scene renderer
    try:
        scene_renderer = PygameSceneRenderer.for_activity()
    except Exception:
        scene_renderer = None

    # Load Activity-local runtime assets
    run_dir = Path(__file__).parent / "assets" / "runtime"
    block_surfs: dict[str, pygame.Surface] = {}
    for blk in ["wood", "stone", "shroom", "rainbow"]:
        p = run_dir / f"block_{blk}.png"
        if p.exists():
            try:
                block_surfs[blk] = pygame.image.load(str(p)).convert_alpha()
            except Exception:
                pass

    bank_surfs: dict[str, pygame.Surface] = {}
    bank_scaled_surfs: dict[str, tuple[pygame.Surface, pygame.Surface]] = {}
    for world in ["river", "canyon", "space"]:
        p = run_dir / f"bank_{world}.png"
        if p.exists():
            try:
                raw_b = pygame.image.load(str(p)).convert_alpha()
                bank_surfs[world] = raw_b
                l_scaled = pygame.transform.smoothscale(raw_b, (220, 270))
                r_scaled = pygame.transform.flip(pygame.transform.smoothscale(raw_b, (224, 270)), True, False)
                bank_scaled_surfs[world] = (l_scaled, r_scaled)
            except Exception:
                pass

    trampoline_surf: pygame.Surface | None = None
    p_tramp = run_dir / "trampoline.png"
    if p_tramp.exists():
        try:
            raw_t = pygame.image.load(str(p_tramp)).convert_alpha()
            trampoline_surf = pygame.transform.smoothscale(raw_t, (160, 64))
        except Exception:
            pass

    goal_flag_surf: pygame.Surface | None = None
    p_flag = run_dir / "goal_flag.png"
    if p_flag.exists():
        try:
            raw_f = pygame.image.load(str(p_flag)).convert_alpha()
            goal_flag_surf = pygame.transform.smoothscale(raw_f, (90, 112))
        except Exception:
            pass

    # Pre-render world abyss gradient surfaces
    bridge_start_x = 220
    bridge_end_x = 800
    bridge_y = 350
    abyss_w = (bridge_end_x - bridge_start_x) + 20
    abyss_h = REFERENCE_HEIGHT - bridge_y
    river_abyss_surf = pygame.Surface((abyss_w, abyss_h))
    for y in range(abyss_h):
        ratio = y / max(1, abyss_h)
        r = int(56 * (1 - ratio) + 14 * ratio)
        g = int(189 * (1 - ratio) + 116 * ratio)
        b = int(248 * (1 - ratio) + 144 * ratio)
        pygame.draw.line(river_abyss_surf, (r, g, b), (0, y), (abyss_w, y))

    canyon_abyss_surf = pygame.Surface((abyss_w, abyss_h))
    for y in range(abyss_h):
        ratio = y / max(1, abyss_h)
        r = int(217 * (1 - ratio) + 69 * ratio)
        g = int(119 * (1 - ratio) + 26 * ratio)
        b = int(6 * (1 - ratio) + 3 * ratio)
        pygame.draw.line(canyon_abyss_surf, (r, g, b), (0, y), (abyss_w, y))

    icon_scale_cache: dict[tuple[str, int], pygame.Surface] = {}

    def draw_block_icon(surf: pygame.Surface, block_id: str, cx: int, cy: int, size: int) -> None:
        b_img = block_surfs.get(block_id)
        if b_img is not None:
            cache_key = (block_id, size)
            scaled = icon_scale_cache.get(cache_key)
            if scaled is None:
                scaled = pygame.transform.smoothscale(b_img, (size, size))
                icon_scale_cache[cache_key] = scaled
            surf.blit(scaled, scaled.get_rect(center=(cx, cy)))
        else:
            _draw_block_icon_procedural(surf, block_id, cx, cy, size)

    storage = get_storage()
    saved_data = storage.kv_get(STORAGE_KEY) if storage else {}
    if not isinstance(saved_data, dict):
        saved_data = {}
    total_stars = saved_data.get("stars", 0)

    level_idx = 0
    selected_block_id = "wood"
    slots: list[str | None] = [None, None, None, None]

    # Flash companion traveler state
    flash_state = "neutral"  # "neutral", "blink", "happy", "surprised"
    flash_motion = "idle_bounce"
    flash_pos = [90.0, 260.0]
    flash_target_step = 0
    flash_anim_timer = 0.0
    is_victory = False
    particles: list[dict[str, Any]] = []

    # Deterministic starfield for space world
    rng_stars = random.Random(77)
    space_stars = [
        (
            rng_stars.randint(10, REFERENCE_WIDTH - 10),
            rng_stars.randint(10, REFERENCE_HEIGHT - 10),
            rng_stars.randint(1, 3),
            (255, 255, 255) if rng_stars.random() > 0.3 else (147, 197, 253),
        )
        for _ in range(70)
    ]

    def setup_level(idx: int) -> None:
        nonlocal slots, flash_state, flash_motion, flash_pos, flash_target_step, flash_anim_timer
        cur_lvl = LEVELS[idx % len(LEVELS)]
        slots = [None for _ in cur_lvl["required"]]
        flash_state = "neutral"
        flash_motion = "idle_bounce"
        flash_pos = [90.0, 260.0]
        flash_target_step = 0
        flash_anim_timer = 0.0

    setup_level(0)

    running = True
    ready_published = False
    start_time = time.time()

    while running and not activity_stop_requested():
        frame_start = time.monotonic()
        cur_lvl = LEVELS[level_idx % len(LEVELS)]
        required = cur_lvl["required"]
        num_slots = len(required)
        elapsed = time.time() - start_time
        motion_enabled = True

        # Slot layout
        bridge_start_x = 220
        bridge_end_x = 800
        slot_w = (bridge_end_x - bridge_start_x) // num_slots
        bridge_y = 350

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
                completion_presented = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pointer = canvas.pointer(event.pos)
                if pointer is None:
                    continue
                mx, my = int(pointer[0]), int(pointer[1])

                if not _is_safe_point(screen, event.pos):
                    continue

                if is_victory:
                    if completion.primary_contains((mx, my)):
                        is_victory = False
                        level_idx = 0
                        setup_level(0)
                        completion.clear()
                        completion_presented = False
                    continue

                # Material Palette Selection (Bottom)
                palette_y = 475
                for b_idx, blk in enumerate(BLOCKS):
                    btn_rect = pygame.Rect(180 + b_idx * 170, palette_y, 140, 96)
                    if btn_rect.collidepoint(mx, my):
                        selected_block_id = blk["id"]
                        sounds.play("place")
                        continue

                # Bridge Slots Tapping
                if flash_state in ("neutral", "blink"):
                    for s_idx in range(num_slots):
                        sx = bridge_start_x + s_idx * slot_w
                        slot_rect = pygame.Rect(sx + 4, bridge_y, slot_w - 8, 70)
                        if slot_rect.collidepoint(mx, my):
                            slots[s_idx] = selected_block_id
                            sounds.play("place")
                            for _ in range(10):
                                particles.append({
                                    "x": slot_rect.centerx,
                                    "y": slot_rect.centery,
                                    "vx": random.uniform(-3, 3),
                                    "vy": random.uniform(-4, -1),
                                    "color": (254, 240, 138),
                                    "size": random.uniform(4, 8),
                                    "life": 1.0,
                                })

                # GO Button (Cross bridge)
                go_btn = pygame.Rect(REFERENCE_WIDTH - 180, 16, 160, 60)
                if go_btn.collidepoint(mx, my) and flash_state in ("neutral", "blink"):
                    flash_state = "happy"
                    flash_motion = "happy_hop"
                    flash_target_step = 0
                    flash_anim_timer = 0.0

                # Clear Button
                clear_btn = pygame.Rect(REFERENCE_WIDTH - 360, 16, 165, 60)
                if clear_btn.collidepoint(mx, my) and flash_state in ("neutral", "blink"):
                    slots = [None for _ in required]
                    sounds.play("place")

        if is_victory:
            if not completion_presented:
                completion.prepare(completion_content)
                completion.draw(canvas.surface)
                canvas.present()
                pygame.display.flip()
                completion_presented = True
            # Terminal state remains responsive without running or repainting the game.
            time.sleep(0.04)
            continue

        # Flash Traveler Crossing & Physics Logic
        if flash_motion == "happy_hop" and flash_state == "happy":
            flash_anim_timer += 0.04
            if flash_target_step < num_slots:
                target_x = bridge_start_x + (flash_target_step + 0.5) * slot_w - 48
            else:
                target_x = bridge_end_x + 50
            dx = target_x - flash_pos[0]
            if dx > 4:
                flash_pos[0] += 6.0
                flash_pos[1] = 260.0 - abs(math.sin(flash_anim_timer * 8.0)) * 25.0
            else:
                # Arrived at slot - test block
                if flash_target_step < num_slots:
                    placed = slots[flash_target_step]
                    expected = required[flash_target_step]
                    if placed != expected:
                        # Mismatched or missing block -> Fall & Trampoline bounce!
                        flash_state = "surprised"
                        flash_motion = "surprised_wobble"
                        flash_anim_timer = 0.0
                        sounds.play("boing")
                    else:
                        # Correct block!
                        if placed == "shroom":
                            sounds.play("boing")
                            for _ in range(12):
                                particles.append({
                                    "x": flash_pos[0] + 48,
                                    "y": flash_pos[1] + 80,
                                    "vx": random.uniform(-4, 4),
                                    "vy": random.uniform(-6, -2),
                                    "color": (239, 68, 68),
                                    "size": random.uniform(4, 7),
                                    "life": 0.8,
                                })
                        elif placed == "rainbow":
                            for _ in range(12):
                                particles.append({
                                    "x": flash_pos[0] + 48,
                                    "y": flash_pos[1] + 70,
                                    "vx": random.uniform(-3, 3),
                                    "vy": random.uniform(-4, 0),
                                    "color": (250, 204, 21),
                                    "size": random.uniform(3, 6),
                                    "life": 0.8,
                                })
                        flash_target_step += 1
                else:
                    # Reached right cliff!
                    flash_state = "happy"
                    flash_motion = "celebrate_pop"
                    flash_anim_timer = 0.0
                    sounds.play("win")
                    total_stars += 1
                    if storage:
                        storage.kv_set(STORAGE_KEY, {"stars": total_stars})
                    try:
                        emit_activity_event("bridge.level_completed", {"level": level_idx + 1, "stars": total_stars})
                    except Exception:
                        pass

        elif flash_motion == "surprised_wobble" and flash_state == "surprised":
            flash_anim_timer += 0.04
            # Fall down to safety trampoline at y=360, then bounce back up to x=90
            if flash_anim_timer < 0.45:
                flash_pos[1] += 9.0
            else:
                t = (flash_anim_timer - 0.45) / 0.85
                if t < 1.0:
                    flash_pos[0] = flash_pos[0] * (1 - 0.08) + 90.0 * 0.08
                    flash_pos[1] = 360.0 - math.sin(t * math.pi) * 140.0
                else:
                    flash_pos = [90.0, 260.0]
                    flash_state = "neutral"
                    flash_motion = "idle_bounce"

        elif flash_motion == "celebrate_pop":
            flash_anim_timer += 0.04
            flash_pos[1] = 260.0 - abs(math.sin(flash_anim_timer * 6.0)) * 20.0
            # Victory star celebration particles
            if len(particles) < 30:
                particles.append({
                    "x": flash_pos[0] + random.uniform(10, 80),
                    "y": flash_pos[1] + random.uniform(0, 40),
                    "vx": random.uniform(-3, 3),
                    "vy": random.uniform(-5, -1),
                    "color": random.choice([(250, 204, 21), (34, 197, 94), (59, 130, 246), (239, 68, 68)]),
                    "size": random.uniform(4, 9),
                    "life": 1.2,
                })
            if flash_anim_timer > 2.0:
                level_idx += 1
                if level_idx >= len(LEVELS):
                    is_victory = True
                    completion_presented = False
                else:
                    setup_level(level_idx)

        # Update particles
        surviving_p = []
        for p in particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 0.04
            if p["life"] > 0:
                surviving_p.append(p)
        particles = surviving_p

        # RENDER TO CANVAS
        surf = canvas.surface
        w_id = cur_lvl["id"]

        # 1. Build Scene Nodes for World Backdrop
        nodes: list[SceneNode] = []
        if w_id == "river":
            nodes.append(SceneNode(node_id="hills", asset_id="hills.distant.01", rect=(0, 160, 1024, 220), z=5))
            nodes.append(SceneNode(node_id="cloud_l", asset_id="cloud.large.01", rect=(100, 35, 180, 72), z=6))
            nodes.append(SceneNode(node_id="cloud_s", asset_id="cloud.small.01", rect=(680, 65, 130, 56), z=6))
            nodes.append(SceneNode(node_id="sunlight", asset_id="atmosphere.sunlight_rays.01", rect=(640, 0, 360, 240), z=7))
            nodes.append(SceneNode(node_id="bush", asset_id="bush.flowering.01", rect=(25, 275, 88, 68), z=40))
            nodes.append(SceneNode(node_id="rock", asset_id="rock.cluster.large.01", rect=(890, 295, 96, 54), z=40))
        elif w_id == "canyon":
            nodes.append(SceneNode(node_id="cloud_l", asset_id="cloud.large.01", rect=(160, 35, 170, 65), z=6))
            nodes.append(SceneNode(node_id="sunlight", asset_id="atmosphere.sunlight_rays.01", rect=(640, 0, 360, 240), z=7))

        # Flash Traveler Scene Actor
        flash_actor = SceneActorDefinition(
            actor_id="flash_traveler",
            asset_id="character.flash",
            rect=(flash_pos[0], flash_pos[1], 96, 96),
            shadow_asset_id="shadow.contact.small.01",
            shadow_rect=(flash_pos[0] + 8, flash_pos[1] + 80, 80, 22),
            state=flash_state,
            motion=flash_motion,
            z=45,
        )
        actor_sample = sample_scene_actor(flash_actor, elapsed_seconds=elapsed, motion_enabled=motion_enabled)
        for n in actor_sample.nodes:
            nodes.append(n)

        scene_def = SceneDefinition(
            scene_id=f"ponti_{w_id}",
            canvas_size=(REFERENCE_WIDTH, REFERENCE_HEIGHT),
            background=cur_lvl["sky"],
            nodes=tuple(nodes),
            fit=SceneFit.COVER,
        )

        # 2. Render Backdrop Scene (Far Background: z <= 10)
        if scene_renderer is not None:
            try:
                scene_renderer.draw(scene_def, surf, max_z=10, motion_enabled=motion_enabled, elapsed_seconds=elapsed)
            except Exception:
                surf.fill(cur_lvl["sky"])
        else:
            surf.fill(cur_lvl["sky"])

        # 3. World-Specific Gap Abyss Features
        if w_id == "river":
            surf.blit(river_abyss_surf, (bridge_start_x - 10, bridge_y))
            wave_off = math.sin(elapsed * 2.0) * 8.0 if motion_enabled else 0.0
            for wy in range(bridge_y + 20, REFERENCE_HEIGHT - 60, 35):
                pygame.draw.arc(surf, (186, 230, 253), pygame.Rect(bridge_start_x + 20 + wave_off, wy, 160, 20), 0, 3.14159, 2)
                pygame.draw.arc(surf, (186, 230, 253), pygame.Rect(bridge_start_x + 240 - wave_off, wy + 15, 180, 20), 0, 3.14159, 2)
                pygame.draw.arc(surf, (186, 230, 253), pygame.Rect(bridge_start_x + 380 + wave_off, wy - 8, 140, 20), 0, 3.14159, 2)

        elif w_id == "canyon":
            pygame.draw.polygon(surf, (217, 119, 6), [(0, bridge_y - 80), (140, bridge_y - 140), (280, bridge_y - 80), (0, bridge_y)])
            pygame.draw.polygon(surf, (180, 83, 9), [(200, bridge_y - 60), (380, bridge_y - 160), (560, bridge_y - 70), (200, bridge_y)])
            pygame.draw.polygon(surf, (217, 119, 6), [(500, bridge_y - 90), (700, bridge_y - 150), (900, bridge_y - 75), (500, bridge_y)])
            surf.blit(canyon_abyss_surf, (bridge_start_x - 10, bridge_y))

        else:  # space
            for sx, sy, s_rad, s_col in space_stars:
                pygame.draw.circle(surf, s_col, (sx, sy), s_rad)
                if s_rad >= 2:
                    pygame.draw.line(surf, (255, 255, 255), (sx - 4, sy), (sx + 4, sy), 1)
                    pygame.draw.line(surf, (255, 255, 255), (sx, sy - 4), (sx, sy + 4), 1)
            pygame.draw.circle(surf, (241, 245, 249), (130, 85), 36)
            pygame.draw.circle(surf, (203, 213, 225), (120, 78), 8)
            pygame.draw.circle(surf, (203, 213, 225), (145, 92), 10)
            pygame.draw.rect(surf, (10, 10, 24), pygame.Rect(bridge_start_x - 10, bridge_y, (bridge_end_x - bridge_start_x) + 20, REFERENCE_HEIGHT - bridge_y))

        # 4. Cliffs / Banks (Left and Right)
        b_scaled = bank_scaled_surfs.get(w_id)
        if b_scaled is not None:
            left_bank_scaled, right_bank_scaled = b_scaled
            surf.blit(left_bank_scaled, (0, bridge_y - 20))
            surf.blit(right_bank_scaled, (bridge_end_x, bridge_y - 20))
        else:
            pygame.draw.rect(surf, cur_lvl["cliff_color"], pygame.Rect(0, bridge_y - 20, bridge_start_x, REFERENCE_HEIGHT - bridge_y + 20), border_top_right_radius=24)
            pygame.draw.rect(surf, cur_lvl["cliff_color"], pygame.Rect(bridge_end_x, bridge_y - 20, REFERENCE_WIDTH - bridge_end_x, REFERENCE_HEIGHT - bridge_y + 20), border_top_left_radius=24)

        # 5. Foreground Scene Nodes & Flash Actor (z >= 20)
        if scene_renderer is not None:
            try:
                scene_renderer.draw(scene_def, surf, min_z=20, clear=False, motion_enabled=motion_enabled, elapsed_seconds=elapsed)
            except Exception:
                bx, by = flash_pos[0] + 48, flash_pos[1] + 48
                pygame.draw.circle(surf, (255, 255, 255), (int(bx), int(by)), 28)
                pygame.draw.circle(surf, (20, 20, 30), (int(bx - 8), int(by - 4)), 5)
                pygame.draw.circle(surf, (20, 20, 30), (int(bx + 8), int(by - 4)), 5)
        else:
            bx, by = flash_pos[0] + 48, flash_pos[1] + 48
            pygame.draw.circle(surf, (255, 255, 255), (int(bx), int(by)), 28)

        # 6. Safety Trampoline in Gap
        if trampoline_surf is not None:
            surf.blit(trampoline_surf, (REFERENCE_WIDTH // 2 - 80, 435))
        else:
            tramp_x = (bridge_start_x + bridge_end_x) // 2
            pygame.draw.rect(surf, (239, 68, 68), pygame.Rect(tramp_x - 120, 440, 240, 36), border_radius=18)
            pygame.draw.rect(surf, (254, 240, 138), (tramp_x - 100, 446, 200, 24), border_radius=12)

        # 7. Suspension Bridge Cables & Pillars
        pier_col = (51, 65, 85)
        if w_id == "canyon":
            pier_col = (120, 53, 15)
        elif w_id == "space":
            pier_col = (30, 41, 59)
        pygame.draw.rect(surf, pier_col, (bridge_start_x - 12, bridge_y - 60, 14, 80), border_radius=4)
        pygame.draw.rect(surf, pier_col, (bridge_end_x - 2, bridge_y - 60, 14, 80), border_radius=4)
        pygame.draw.line(surf, (71, 85, 105), (bridge_start_x - 5, bridge_y - 50), (REFERENCE_WIDTH // 2, bridge_y + 15), 4)
        pygame.draw.line(surf, (71, 85, 105), (REFERENCE_WIDTH // 2, bridge_y + 15), (bridge_end_x + 5, bridge_y - 50), 4)
        pygame.draw.line(surf, (148, 163, 184), (bridge_start_x - 5, bridge_y - 48), (REFERENCE_WIDTH // 2, bridge_y + 17), 2)
        pygame.draw.line(surf, (148, 163, 184), (REFERENCE_WIDTH // 2, bridge_y + 17), (bridge_end_x + 5, bridge_y - 48), 2)

        # 8. Bridge Slots & Placed Blocks
        now = time.time()
        for s_idx in range(num_slots):
            sx = bridge_start_x + s_idx * slot_w
            slot_rect = pygame.Rect(sx + 6, bridge_y, slot_w - 12, 64)
            placed = slots[s_idx]
            req_type = required[s_idx]

            cable_y = bridge_y - 50 + int(abs(slot_rect.centerx - REFERENCE_WIDTH // 2) / (bridge_end_x - bridge_start_x) * 130)
            pygame.draw.line(surf, (100, 116, 139), (slot_rect.centerx, cable_y), (slot_rect.centerx, slot_rect.top), 2)

            if placed is not None:
                is_correct = (placed == req_type)
                border_color = (34, 197, 94) if is_correct else (217, 119, 6)
                pygame.draw.rect(surf, (255, 255, 255), slot_rect, border_radius=16)
                pygame.draw.rect(surf, border_color, slot_rect, width=4, border_radius=16)
                pygame.draw.line(surf, (100, 116, 139), (slot_rect.left - 4, slot_rect.top + 6), (slot_rect.right + 4, slot_rect.top + 6), 3)
                draw_block_icon(surf, placed, slot_rect.centerx, slot_rect.centery + 2, 54)
                chk_x = slot_rect.right - 14
                chk_y = slot_rect.top + 14
                if is_correct:
                    pygame.draw.circle(surf, (34, 197, 94), (chk_x, chk_y), 11)
                    pygame.draw.circle(surf, (255, 255, 255), (chk_x, chk_y), 11, 2)
                    pygame.draw.polygon(surf, (255, 255, 255), [(chk_x - 4, chk_y), (chk_x - 1, chk_y + 3), (chk_x + 4, chk_y - 3)], 2)
                else:
                    pygame.draw.circle(surf, (217, 119, 6), (chk_x, chk_y), 8)
                    pygame.draw.circle(surf, (255, 255, 255), (chk_x, chk_y), 8, 2)
            else:
                pygame.draw.rect(surf, (248, 250, 252), slot_rect, border_radius=16)
                pygame.draw.rect(surf, (148, 163, 184), slot_rect, width=2, border_radius=16)
                pygame.draw.circle(surf, (255, 255, 255), (slot_rect.centerx, slot_rect.centery + 2), 24)
                pygame.draw.circle(surf, (203, 213, 225), (slot_rect.centerx, slot_rect.centery + 2), 24, 2)
                draw_block_icon(surf, req_type, slot_rect.centerx, slot_rect.centery + 2, 40)
                arrow_bob = int(math.sin(now * 5.0 + s_idx) * 3.0) if motion_enabled else 0
                arrow_y = slot_rect.top + 10 + arrow_bob
                pygame.draw.polygon(surf, (234, 179, 8), [
                    (slot_rect.centerx - 6, arrow_y - 4),
                    (slot_rect.centerx + 6, arrow_y - 4),
                    (slot_rect.centerx, arrow_y + 4),
                ])
                pygame.draw.polygon(surf, (180, 83, 9), [
                    (slot_rect.centerx - 6, arrow_y - 4),
                    (slot_rect.centerx + 6, arrow_y - 4),
                    (slot_rect.centerx, arrow_y + 4),
                ], 1)

        # 9. Goal Flag on Right Cliff
        if goal_flag_surf is not None:
            g_scaled = pygame.transform.smoothscale(goal_flag_surf, (90, 112))
            surf.blit(g_scaled, (bridge_end_x + 50, bridge_y - 95))
        else:
            flag_x = bridge_end_x + 70
            pygame.draw.rect(surf, (120, 53, 15), (flag_x, 240, 8, 100), border_radius=4)
            pygame.draw.polygon(surf, (234, 179, 8), [(flag_x + 8, 240), (flag_x + 60, 260), (flag_x + 8, 280)])
            pygame.draw.circle(surf, (249, 115, 22), (flag_x + 35, 310), 16)

        # 10. Particles
        for p in particles:
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), int(p["size"]))

        # 11. Bottom Palette (140x96px tactile cards)
        palette_y = 475
        block_labels = {
            "wood": "LEGNO",
            "stone": "PIETRA",
            "shroom": "FUNGO",
            "rainbow": "ARCOBALENO",
        }
        for b_idx, blk in enumerate(BLOCKS):
            btn_rect = pygame.Rect(180 + b_idx * 170, palette_y, 140, 96)
            is_sel = (blk["id"] == selected_block_id)
            pygame.draw.rect(surf, (255, 255, 255), btn_rect, border_radius=22)
            if is_sel:
                pygame.draw.rect(surf, (234, 179, 8), btn_rect, width=5, border_radius=22)
            else:
                pygame.draw.rect(surf, (203, 213, 225), btn_rect, width=2, border_radius=22)

            draw_block_icon(surf, blk["id"], btn_rect.centerx, btn_rect.top + 34, 46)

            lbl = block_labels.get(blk["id"], "")
            t_col = (180, 83, 9) if is_sel else (71, 85, 105)
            lbl_surf = typography.render(lbl, FontRole.DISPLAY, 16, t_col)
            surf.blit(lbl_surf, (btn_rect.centerx - lbl_surf.get_width() // 2, btn_rect.bottom - 24))

        # 12. Top Controls
        # Star Pill
        star_pill = pygame.Rect(80, 16, 130, 60)
        pygame.draw.rect(surf, (255, 255, 255), star_pill, border_radius=20)
        pygame.draw.rect(surf, (234, 179, 8), star_pill, width=3, border_radius=20)
        pygame.draw.circle(surf, (234, 179, 8), (star_pill.left + 30, star_pill.centery), 16)
        s_txt = typography.render(str(total_stars), FontRole.DISPLAY, 28, (180, 83, 9))
        surf.blit(s_txt, (star_pill.left + 58, star_pill.centery - s_txt.get_height() // 2))

        # Clear Button (PULISCI)
        clear_btn = pygame.Rect(REFERENCE_WIDTH - 360, 16, 165, 60)
        pygame.draw.rect(surf, (241, 245, 249), clear_btn, border_radius=20)
        pygame.draw.rect(surf, (148, 163, 184), clear_btn, width=3, border_radius=20)
        cx = clear_btn.left + 28
        cy = clear_btn.centery
        pygame.draw.line(surf, (120, 53, 15), (cx - 12, cy - 10), (cx + 4, cy + 6), 4)
        pygame.draw.polygon(surf, (234, 179, 8), [(cx + 2, cy + 2), (cx + 14, cy - 4), (cx + 10, cy + 14), (cx - 2, cy + 10)])
        c_txt = typography.render("PULISCI", FontRole.DISPLAY, 18, (71, 85, 105))
        surf.blit(c_txt, (clear_btn.left + 52, clear_btn.centery - c_txt.get_height() // 2))

        # GO Button (VAI!)
        go_btn = pygame.Rect(REFERENCE_WIDTH - 180, 16, 160, 60)
        pygame.draw.rect(surf, (34, 197, 94), go_btn, border_radius=20)
        pygame.draw.rect(surf, (22, 101, 52), go_btn, width=4, border_radius=20)
        bx = go_btn.left + 28
        by = go_btn.centery + 2
        pygame.draw.circle(surf, (255, 255, 255), (bx, by), 14)
        pygame.draw.ellipse(surf, (255, 255, 255), pygame.Rect(bx - 8, by - 20, 6, 14))
        pygame.draw.ellipse(surf, (255, 255, 255), pygame.Rect(bx + 2, by - 20, 6, 14))
        pygame.draw.circle(surf, (20, 20, 30), (bx - 4, by - 2), 2)
        pygame.draw.circle(surf, (20, 20, 30), (bx + 4, by - 2), 2)
        go_txt = typography.render("VAI!", FontRole.DISPLAY, 24, (255, 255, 255))
        surf.blit(go_txt, (go_btn.left + 54, go_btn.centery - go_txt.get_height() // 2))
        pygame.draw.polygon(surf, (255, 255, 255), [(go_btn.right - 35, go_btn.centery - 12), (go_btn.right - 15, go_btn.centery), (go_btn.right - 35, go_btn.centery + 12)])

        # Present Canvas
        canvas.present()
        pygame.display.flip()

        if not ready_published:
            mark_activity_ready()
            ready_published = True

        elapsed_frame = time.monotonic() - frame_start
        delay = max(0.002, (1.0 / 30.0) - elapsed_frame)
        time.sleep(delay)

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
