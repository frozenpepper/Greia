from __future__ import annotations

"""Pygame presentation owner for Costruiamo Ponti.

Caches are bounded and prepared once. Per-frame work is limited to
blitting prepared surfaces and drawing small dynamic elements. Image
scaling uses ``smoothscale`` only at cache miss; fonts are provided
by ``GreiaTypography`` with its own bounded cache.
"""

import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pygame

from greia_platform.pygame_completion import CompletionContent, PygameCompletionScreen
from greia_platform.pygame_scene import PygameSceneRenderer
from greia_platform.scene import SceneDefinition, SceneFit, SceneNode
from greia_platform.scene_actor import SceneActorDefinition, sample_scene_actor
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .ponti_content import (
        BLOCKS,
        BRIDGE_END_X,
        BRIDGE_START_X,
        BRIDGE_Y,
        LEVELS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )
    from .ponti_model import PontiModel
else:
    from ponti_content import (
        BLOCKS,
        BRIDGE_END_X,
        BRIDGE_START_X,
        BRIDGE_Y,
        LEVELS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )
    from ponti_model import PontiModel


PALETTE_Y = 475
PLAY_AGAIN_RECT = pygame.Rect(REFERENCE_WIDTH // 2 - 120, REFERENCE_HEIGHT // 2 + 70, 240, 60)
GO_RECT = pygame.Rect(REFERENCE_WIDTH - 180, 16, 160, 60)
CLEAR_RECT = pygame.Rect(REFERENCE_WIDTH - 360, 16, 165, 60)
STAR_PILL_RECT = pygame.Rect(80, 16, 130, 60)
_MAX_ICON_CACHE = 32
_MAX_PARTICLES = 64


@dataclass(slots=True)
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    size: float
    life: float = 1.0


def _draw_block_icon_procedural(surface: pygame.Surface, block_id: str, cx: int, cy: int, size: int) -> None:
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


class PontiRenderer:
    """Own Pygame presentation for Costruiamo Ponti."""

    def __init__(self, typography: GreiaTypography, run_dir: Path | None = None) -> None:
        self._typography = typography
        self._run_dir = run_dir or (Path(__file__).resolve().parent / "assets" / "runtime")
        # Bounded caches
        self._block_surfs: dict[str, pygame.Surface] = {}
        self._bank_scaled_surfs: dict[str, tuple[pygame.Surface, pygame.Surface]] = {}
        self._trampoline_surf: pygame.Surface | None = None
        self._goal_flag_surf: pygame.Surface | None = None
        self._river_abyss_surf: pygame.Surface
        self._canyon_abyss_surf: pygame.Surface
        self._icon_scale_cache: dict[tuple[str, int], pygame.Surface] = {}
        self._label_cache: dict[tuple[str, int, tuple[int, int, int]], pygame.Surface] = {}
        self._star_value: int | None = None
        self._star_surface: pygame.Surface | None = None
        self._particles: list[Particle] = []
        self._scene_renderer: PygameSceneRenderer | None = None
        self._space_stars: list[tuple[int, int, int, tuple[int, int, int]]] = []
        # Completion
        self._completion = PygameCompletionScreen(
            typography, width=REFERENCE_WIDTH, height=REFERENCE_HEIGHT, primary_rect=PLAY_AGAIN_RECT
        )
        self._completion_content = CompletionContent(
            title="OTTIMO LAVORO!", primary_label="GIOCA ANCORA", achievement_count=5
        )
        self._load_assets()
        self._build_static_surfaces()
        self._init_scene_renderer()
        self._build_space_stars()

    def _load_assets(self) -> None:
        # Block icons – convert_alpha once at preparation.
        for blk in ["wood", "stone", "shroom", "rainbow"]:
            p = self._run_dir / f"block_{blk}.png"
            if p.exists():
                try:
                    surf = pygame.image.load(str(p))
                    # convert_alpha requires display; fallback to original if unavailable.
                    try:
                        surf = surf.convert_alpha()
                    except Exception:
                        pass
                    self._block_surfs[blk] = surf
                except Exception:
                    pass
        # Banks pre-scaled once.
        for world in ["river", "canyon", "space"]:
            p = self._run_dir / f"bank_{world}.png"
            if p.exists():
                try:
                    raw = pygame.image.load(str(p))
                    try:
                        raw = raw.convert_alpha()
                    except Exception:
                        pass
                    l_scaled = pygame.transform.smoothscale(raw, (220, 270))
                    r_scaled = pygame.transform.flip(pygame.transform.smoothscale(raw, (224, 270)), True, False)
                    # Convert once for fast blit
                    try:
                        l_scaled = l_scaled.convert_alpha()
                        r_scaled = r_scaled.convert_alpha()
                    except Exception:
                        pass
                    self._bank_scaled_surfs[world] = (l_scaled, r_scaled)
                except Exception:
                    pass
        p_tramp = self._run_dir / "trampoline.png"
        if p_tramp.exists():
            try:
                raw = pygame.image.load(str(p_tramp))
                try:
                    raw = raw.convert_alpha()
                except Exception:
                    pass
                surf = pygame.transform.smoothscale(raw, (160, 64))
                try:
                    surf = surf.convert_alpha()
                except Exception:
                    pass
                self._trampoline_surf = surf
            except Exception:
                pass
        p_flag = self._run_dir / "goal_flag.png"
        if p_flag.exists():
            try:
                raw = pygame.image.load(str(p_flag))
                try:
                    raw = raw.convert_alpha()
                except Exception:
                    pass
                surf = pygame.transform.smoothscale(raw, (90, 112))
                try:
                    surf = surf.convert_alpha()
                except Exception:
                    pass
                self._goal_flag_surf = surf
            except Exception:
                pass

    def _build_static_surfaces(self) -> None:
        abyss_w = (BRIDGE_END_X - BRIDGE_START_X) + 20
        abyss_h = REFERENCE_HEIGHT - BRIDGE_Y
        self._river_abyss_surf = pygame.Surface((abyss_w, abyss_h))
        try:
            self._river_abyss_surf = self._river_abyss_surf.convert()
        except Exception:
            pass
        for y in range(abyss_h):
            ratio = y / max(1, abyss_h)
            r = int(56 * (1 - ratio) + 14 * ratio)
            g = int(189 * (1 - ratio) + 116 * ratio)
            b = int(248 * (1 - ratio) + 144 * ratio)
            pygame.draw.line(self._river_abyss_surf, (r, g, b), (0, y), (abyss_w, y))
        self._canyon_abyss_surf = pygame.Surface((abyss_w, abyss_h))
        try:
            self._canyon_abyss_surf = self._canyon_abyss_surf.convert()
        except Exception:
            pass
        for y in range(abyss_h):
            ratio = y / max(1, abyss_h)
            r = int(217 * (1 - ratio) + 69 * ratio)
            g = int(119 * (1 - ratio) + 26 * ratio)
            b = int(6 * (1 - ratio) + 3 * ratio)
            pygame.draw.line(self._canyon_abyss_surf, (r, g, b), (0, y), (abyss_w, y))

    def _init_scene_renderer(self) -> None:
        try:
            self._scene_renderer = PygameSceneRenderer.for_activity()
        except Exception:
            self._scene_renderer = None

    def _build_space_stars(self) -> None:
        rng = random.Random(77)
        self._space_stars = [
            (
                rng.randint(10, REFERENCE_WIDTH - 10),
                rng.randint(10, REFERENCE_HEIGHT - 10),
                rng.randint(1, 3),
                (255, 255, 255) if rng.random() > 0.3 else (147, 197, 253),
            )
            for _ in range(70)
        ]

    # ------------------------------------------------------------------ #
    # Cache helpers
    # ------------------------------------------------------------------ #
    def _scaled_block_icon(self, block_id: str, size: int) -> pygame.Surface | None:
        b_img = self._block_surfs.get(block_id)
        if b_img is None:
            return None
        key = (block_id, size)
        cached = self._icon_scale_cache.get(key)
        if cached is not None:
            return cached
        if len(self._icon_scale_cache) >= _MAX_ICON_CACHE:
            # Bounded eviction – clear oldest half.
            keys = list(self._icon_scale_cache.keys())
            for k in keys[: _MAX_ICON_CACHE // 2]:
                self._icon_scale_cache.pop(k, None)
        scaled = pygame.transform.smoothscale(b_img, (size, size))
        try:
            scaled = scaled.convert_alpha()
        except Exception:
            pass
        self._icon_scale_cache[key] = scaled
        return scaled

    def _label(self, text: str, size: int, color: tuple[int, int, int]) -> pygame.Surface:
        key = (text, size, color)
        cached = self._label_cache.get(key)
        if cached is not None:
            return cached
        # Bounded label cache – finite labels (4 palette + stars).
        if len(self._label_cache) >= 32:
            self._label_cache.clear()
        surf = self._typography.render(text, FontRole.DISPLAY, size, color)
        self._label_cache[key] = surf
        return surf

    def invalidate(self) -> None:
        """Invalidate renderer caches that depend on display format."""
        # Abyss surfaces were built with convert(); rebuild if display changed.
        # Keep icon cache but it remains valid as converted sources.
        pass

    # ------------------------------------------------------------------ #
    # Particles
    # ------------------------------------------------------------------ #
    def spawn_particles(
        self,
        x: float,
        y: float,
        color: tuple[int, int, int],
        count: int = 10,
        vx_range: tuple[float, float] = (-3, 3),
        vy_range: tuple[float, float] = (-4, -1),
        size_range: tuple[float, float] = (4, 8),
        life: float = 1.0,
    ) -> None:
        for _ in range(count):
            self._particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=random.uniform(vx_range[0], vx_range[1]),
                    vy=random.uniform(vy_range[0], vy_range[1]),
                    color=color,
                    size=random.uniform(size_range[0], size_range[1]),
                    life=life,
                )
            )
        if len(self._particles) > _MAX_PARTICLES:
            self._particles = self._particles[-_MAX_PARTICLES:]

    def clear_particles(self) -> None:
        self._particles.clear()

    def update_particles(self) -> None:
        surviving: list[Particle] = []
        for p in self._particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 0.04
            if p.life > 0:
                surviving.append(p)
        self._particles = surviving

    @property
    def particle_count(self) -> int:
        return len(self._particles)

    def reset_transients(self) -> None:
        self.clear_particles()
        self._completion.clear()

    # ------------------------------------------------------------------ #
    # Hit testing – single source of truth for App
    # ------------------------------------------------------------------ #
    def palette_hit(self, point: tuple[int, int]) -> str | None:
        for idx, blk in enumerate(BLOCKS):
            rect = pygame.Rect(180 + idx * 170, PALETTE_Y, 140, 96)
            if rect.collidepoint(point):
                return str(blk["id"])
        return None

    def slot_hit(self, point: tuple[int, int], num_slots: int) -> int | None:
        slot_w = (BRIDGE_END_X - BRIDGE_START_X) // max(1, num_slots)
        for s_idx in range(num_slots):
            sx = BRIDGE_START_X + s_idx * slot_w
            rect = pygame.Rect(sx + 4, BRIDGE_Y, slot_w - 8, 70)
            if rect.collidepoint(point):
                return s_idx
        return None

    def go_contains(self, point: tuple[int, int]) -> bool:
        return GO_RECT.collidepoint(point)

    def clear_contains(self, point: tuple[int, int]) -> bool:
        return CLEAR_RECT.collidepoint(point)

    def play_again_contains(self, point: tuple[int, int]) -> bool:
        return self._completion.primary_contains(point)

    def prepare_completion(self) -> None:
        self._completion.prepare(self._completion_content)

    def draw_completion(self, surf: pygame.Surface) -> None:
        self._completion.draw(surf)

    # ------------------------------------------------------------------ #
    # Main draw
    # ------------------------------------------------------------------ #
    def draw(self, surf: pygame.Surface, model: PontiModel, elapsed: float, now: float) -> None:
        if model.is_victory:
            self._completion.prepare(self._completion_content)
            self._completion.draw(surf)
            return

        w_id = str(model.cur_level["id"])
        # 1. Backdrop scene nodes (z<=10)
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

        flash_actor = SceneActorDefinition(
            actor_id="flash_traveler",
            asset_id="character.flash",
            rect=(model.flash_pos[0], model.flash_pos[1], 96, 96),
            shadow_asset_id="shadow.contact.small.01",
            shadow_rect=(model.flash_pos[0] + 8, model.flash_pos[1] + 80, 80, 22),
            state=model.flash_state,
            motion=model.flash_motion,
            z=45,
        )
        try:
            actor_sample = sample_scene_actor(flash_actor, elapsed_seconds=elapsed, motion_enabled=True)
            for n in actor_sample.nodes:
                nodes.append(n)
        except Exception:
            nodes.append(
                SceneNode(node_id="flash_fallback", asset_id="character.flash", rect=(model.flash_pos[0], model.flash_pos[1], 96, 96), z=45)
            )

        scene_def = SceneDefinition(
            scene_id=f"ponti_{w_id}",
            canvas_size=(REFERENCE_WIDTH, REFERENCE_HEIGHT),
            background=model.cur_level["sky"],  # type: ignore[arg-type]
            nodes=tuple(nodes),
            fit=SceneFit.COVER,
        )

        if self._scene_renderer is not None:
            try:
                self._scene_renderer.draw(scene_def, surf, max_z=10, motion_enabled=True, elapsed_seconds=elapsed)
            except Exception:
                surf.fill(model.cur_level["sky"])  # type: ignore[arg-type]
        else:
            surf.fill(model.cur_level["sky"])  # type: ignore[arg-type]

        # World-specific gap abyss
        if w_id == "river":
            surf.blit(self._river_abyss_surf, (BRIDGE_START_X - 10, BRIDGE_Y))
            wave_off = math.sin(elapsed * 2.0) * 8.0
            for wy in range(BRIDGE_Y + 20, REFERENCE_HEIGHT - 60, 35):
                pygame.draw.arc(surf, (186, 230, 253), pygame.Rect(BRIDGE_START_X + 20 + wave_off, wy, 160, 20), 0, 3.14159, 2)
                pygame.draw.arc(surf, (186, 230, 253), pygame.Rect(BRIDGE_START_X + 240 - wave_off, wy + 15, 180, 20), 0, 3.14159, 2)
                pygame.draw.arc(surf, (186, 230, 253), pygame.Rect(BRIDGE_START_X + 380 + wave_off, wy - 8, 140, 20), 0, 3.14159, 2)
        elif w_id == "canyon":
            pygame.draw.polygon(surf, (217, 119, 6), [(0, BRIDGE_Y - 80), (140, BRIDGE_Y - 140), (280, BRIDGE_Y - 80), (0, BRIDGE_Y)])
            pygame.draw.polygon(surf, (180, 83, 9), [(200, BRIDGE_Y - 60), (380, BRIDGE_Y - 160), (560, BRIDGE_Y - 70), (200, BRIDGE_Y)])
            pygame.draw.polygon(surf, (217, 119, 6), [(500, BRIDGE_Y - 90), (700, BRIDGE_Y - 150), (900, BRIDGE_Y - 75), (500, BRIDGE_Y)])
            surf.blit(self._canyon_abyss_surf, (BRIDGE_START_X - 10, BRIDGE_Y))
        else:  # space
            for sx, sy, s_rad, s_col in self._space_stars:
                pygame.draw.circle(surf, s_col, (sx, sy), s_rad)
                if s_rad >= 2:
                    pygame.draw.line(surf, (255, 255, 255), (sx - 4, sy), (sx + 4, sy), 1)
                    pygame.draw.line(surf, (255, 255, 255), (sx, sy - 4), (sx, sy + 4), 1)
            pygame.draw.circle(surf, (241, 245, 249), (130, 85), 36)
            pygame.draw.circle(surf, (203, 213, 225), (120, 78), 8)
            pygame.draw.circle(surf, (203, 213, 225), (145, 92), 10)
            pygame.draw.rect(surf, (10, 10, 24), pygame.Rect(BRIDGE_START_X - 10, BRIDGE_Y, (BRIDGE_END_X - BRIDGE_START_X) + 20, REFERENCE_HEIGHT - BRIDGE_Y))

        # Cliffs / Banks
        b_scaled = self._bank_scaled_surfs.get(w_id)
        if b_scaled is not None:
            left_b, right_b = b_scaled
            surf.blit(left_b, (0, BRIDGE_Y - 20))
            surf.blit(right_b, (BRIDGE_END_X, BRIDGE_Y - 20))
        else:
            pygame.draw.rect(surf, model.cur_level["cliff_color"], pygame.Rect(0, BRIDGE_Y - 20, BRIDGE_START_X, REFERENCE_HEIGHT - BRIDGE_Y + 20), border_top_right_radius=24)  # type: ignore[arg-type]
            pygame.draw.rect(surf, model.cur_level["cliff_color"], pygame.Rect(BRIDGE_END_X, BRIDGE_Y - 20, REFERENCE_WIDTH - BRIDGE_END_X, REFERENCE_HEIGHT - BRIDGE_Y + 20), border_top_left_radius=24)  # type: ignore[arg-type]

        # Foreground scene nodes & actor z>=20
        if self._scene_renderer is not None:
            try:
                self._scene_renderer.draw(scene_def, surf, min_z=20, clear=False, motion_enabled=True, elapsed_seconds=elapsed)
            except Exception:
                bx, by = model.flash_pos[0] + 48, model.flash_pos[1] + 48
                pygame.draw.circle(surf, (255, 255, 255), (int(bx), int(by)), 28)
                pygame.draw.circle(surf, (20, 20, 30), (int(bx - 8), int(by - 4)), 5)
                pygame.draw.circle(surf, (20, 20, 30), (int(bx + 8), int(by - 4)), 5)
        else:
            bx, by = model.flash_pos[0] + 48, model.flash_pos[1] + 48
            pygame.draw.circle(surf, (255, 255, 255), (int(bx), int(by)), 28)

        # Safety trampoline
        if self._trampoline_surf is not None:
            surf.blit(self._trampoline_surf, (REFERENCE_WIDTH // 2 - 80, 435))
        else:
            tramp_x = (BRIDGE_START_X + BRIDGE_END_X) // 2
            pygame.draw.rect(surf, (239, 68, 68), pygame.Rect(tramp_x - 120, 440, 240, 36), border_radius=18)
            pygame.draw.rect(surf, (254, 240, 138), (tramp_x - 100, 446, 200, 24), border_radius=12)

        # Suspension cables & pillars
        pier_col = (51, 65, 85)
        if w_id == "canyon":
            pier_col = (120, 53, 15)
        elif w_id == "space":
            pier_col = (30, 41, 59)
        pygame.draw.rect(surf, pier_col, (BRIDGE_START_X - 12, BRIDGE_Y - 60, 14, 80), border_radius=4)
        pygame.draw.rect(surf, pier_col, (BRIDGE_END_X - 2, BRIDGE_Y - 60, 14, 80), border_radius=4)
        pygame.draw.line(surf, (71, 85, 105), (BRIDGE_START_X - 5, BRIDGE_Y - 50), (REFERENCE_WIDTH // 2, BRIDGE_Y + 15), 4)
        pygame.draw.line(surf, (71, 85, 105), (REFERENCE_WIDTH // 2, BRIDGE_Y + 15), (BRIDGE_END_X + 5, BRIDGE_Y - 50), 4)
        pygame.draw.line(surf, (148, 163, 184), (BRIDGE_START_X - 5, BRIDGE_Y - 48), (REFERENCE_WIDTH // 2, BRIDGE_Y + 17), 2)
        pygame.draw.line(surf, (148, 163, 184), (REFERENCE_WIDTH // 2, BRIDGE_Y + 17), (BRIDGE_END_X + 5, BRIDGE_Y - 48), 2)

        # Bridge slots & placed blocks
        slot_w = model.slot_w
        for s_idx in range(model.num_slots):
            sx = BRIDGE_START_X + s_idx * slot_w
            slot_rect = pygame.Rect(sx + 6, BRIDGE_Y, slot_w - 12, 64)
            placed = model.slots[s_idx]
            req_type = model.required[s_idx]
            cable_y = BRIDGE_Y - 50 + int(abs(slot_rect.centerx - REFERENCE_WIDTH // 2) / (BRIDGE_END_X - BRIDGE_START_X) * 130)
            pygame.draw.line(surf, (100, 116, 139), (slot_rect.centerx, cable_y), (slot_rect.centerx, slot_rect.top), 2)
            if placed is not None:
                is_correct = (placed == req_type)
                border_color = (34, 197, 94) if is_correct else (217, 119, 6)
                pygame.draw.rect(surf, (255, 255, 255), slot_rect, border_radius=16)
                pygame.draw.rect(surf, border_color, slot_rect, width=4, border_radius=16)
                pygame.draw.line(surf, (100, 116, 139), (slot_rect.left - 4, slot_rect.top + 6), (slot_rect.right + 4, slot_rect.top + 6), 3)
                self._draw_block_icon(surf, placed, slot_rect.centerx, slot_rect.centery + 2, 54)
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
                self._draw_block_icon(surf, req_type, slot_rect.centerx, slot_rect.centery + 2, 40)
                arrow_bob = int(math.sin(now * 5.0 + s_idx) * 3.0)
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

        # Goal flag
        if self._goal_flag_surf is not None:
            # Already scaled at load; avoid per-frame smoothscale.
            surf.blit(self._goal_flag_surf, (BRIDGE_END_X + 50, BRIDGE_Y - 95))
        else:
            flag_x = BRIDGE_END_X + 70
            pygame.draw.rect(surf, (120, 53, 15), (flag_x, 240, 8, 100), border_radius=4)
            pygame.draw.polygon(surf, (234, 179, 8), [(flag_x + 8, 240), (flag_x + 60, 260), (flag_x + 8, 280)])
            pygame.draw.circle(surf, (249, 115, 22), (flag_x + 35, 310), 16)

        # Particles
        for p in self._particles:
            pygame.draw.circle(surf, p.color, (int(p.x), int(p.y)), int(p.size))

        # Bottom palette
        block_labels = {"wood": "LEGNO", "stone": "PIETRA", "shroom": "FUNGO", "rainbow": "ARCOBALENO"}
        for b_idx, blk in enumerate(BLOCKS):
            btn_rect = pygame.Rect(180 + b_idx * 170, PALETTE_Y, 140, 96)
            is_sel = (str(blk["id"]) == model.selected_block_id)
            pygame.draw.rect(surf, (255, 255, 255), btn_rect, border_radius=22)
            if is_sel:
                pygame.draw.rect(surf, (234, 179, 8), btn_rect, width=5, border_radius=22)
            else:
                pygame.draw.rect(surf, (203, 213, 225), btn_rect, width=2, border_radius=22)
            self._draw_block_icon(surf, str(blk["id"]), btn_rect.centerx, btn_rect.top + 34, 46)
            lbl = block_labels.get(str(blk["id"]), "")
            t_col = (180, 83, 9) if is_sel else (71, 85, 105)
            lbl_surf = self._label(lbl, 16, t_col)
            surf.blit(lbl_surf, (btn_rect.centerx - lbl_surf.get_width() // 2, btn_rect.bottom - 24))

        # Top controls
        star_pill = STAR_PILL_RECT
        pygame.draw.rect(surf, (255, 255, 255), star_pill, border_radius=20)
        pygame.draw.rect(surf, (234, 179, 8), star_pill, width=3, border_radius=20)
        pygame.draw.circle(surf, (234, 179, 8), (star_pill.left + 30, star_pill.centery), 16)
        if self._star_value != model.total_stars or self._star_surface is None:
            self._star_value = model.total_stars
            self._star_surface = self._label(str(model.total_stars), 28, (180, 83, 9))
        surf.blit(self._star_surface, (star_pill.left + 58, star_pill.centery - self._star_surface.get_height() // 2))

        clear_btn = CLEAR_RECT
        pygame.draw.rect(surf, (241, 245, 249), clear_btn, border_radius=20)
        pygame.draw.rect(surf, (148, 163, 184), clear_btn, width=3, border_radius=20)
        cx = clear_btn.left + 28
        cy = clear_btn.centery
        pygame.draw.line(surf, (120, 53, 15), (cx - 12, cy - 10), (cx + 4, cy + 6), 4)
        pygame.draw.polygon(surf, (234, 179, 8), [(cx + 2, cy + 2), (cx + 14, cy - 4), (cx + 10, cy + 14), (cx - 2, cy + 10)])
        c_txt = self._label("PULISCI", 18, (71, 85, 105))
        surf.blit(c_txt, (clear_btn.left + 52, clear_btn.centery - c_txt.get_height() // 2))

        go_btn = GO_RECT
        pygame.draw.rect(surf, (34, 197, 94), go_btn, border_radius=20)
        pygame.draw.rect(surf, (22, 101, 52), go_btn, width=4, border_radius=20)
        bx = go_btn.left + 28
        by = go_btn.centery + 2
        pygame.draw.circle(surf, (255, 255, 255), (bx, by), 14)
        pygame.draw.ellipse(surf, (255, 255, 255), pygame.Rect(bx - 8, by - 20, 6, 14))
        pygame.draw.ellipse(surf, (255, 255, 255), pygame.Rect(bx + 2, by - 20, 6, 14))
        pygame.draw.circle(surf, (20, 20, 30), (bx - 4, by - 2), 2)
        pygame.draw.circle(surf, (20, 20, 30), (bx + 4, by - 2), 2)
        go_txt = self._label("VAI!", 24, (255, 255, 255))
        surf.blit(go_txt, (go_btn.left + 54, go_btn.centery - go_txt.get_height() // 2))
        pygame.draw.polygon(surf, (255, 255, 255), [(go_btn.right - 35, go_btn.centery - 12), (go_btn.right - 15, go_btn.centery), (go_btn.right - 35, go_btn.centery + 12)])

    def _draw_block_icon(self, surf: pygame.Surface, block_id: str, cx: int, cy: int, size: int) -> None:
        scaled = self._scaled_block_icon(block_id, size)
        if scaled is not None:
            surf.blit(scaled, scaled.get_rect(center=(cx, cy)))
        else:
            _draw_block_icon_procedural(surf, block_id, cx, cy, size)


__all__ = ["PontiRenderer", "PLAY_AGAIN_RECT", "GO_RECT", "CLEAR_RECT", "STAR_PILL_RECT"]
