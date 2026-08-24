"""Visual art, background baking, and cached sprites for Nascondino nel Bosco."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Final

import pygame

from greia_platform.pygame_scene import PygameSceneRenderer, SceneRenderError
from greia_platform.scene import load_scene
from greia_platform.scene_actor import SceneActorDefinition, actor_scene_sample
from greia_platform.ui_core import BoundedCache

try:
    from woodland_model import (
        ALL_ANIMALS,
        GROUNDED_SPOTS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        AnimalDefinition,
        HidingSpotDefinition,
    )
except ImportError:
    from .woodland_model import (
        ALL_ANIMALS,
        GROUNDED_SPOTS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        AnimalDefinition,
        HidingSpotDefinition,
    )

LILLI_ACTOR: Final = SceneActorDefinition(
    actor_id="lilli",
    asset_id="character.lilli",
    rect=(50, 105, 150, 150),
    shadow_asset_id="shadow.contact.small.01",
    shadow_rect=(78, 232, 96, 24),
    z=56,
    parallax=0.28,
    idle_amplitude=3.0,
    idle_period_seconds=2.4,
    blink_period_seconds=4.8,
    blink_duration_seconds=0.18,
)


def _draw_legacy_forest_background(surf: pygame.Surface) -> None:
    """Fail-soft fallback background when shared visual assets are unavailable."""
    surf.fill((186, 230, 253))  # Soft sky
    pygame.draw.circle(surf, (254, 240, 138), (140, 90), 45)

    # Distant hills & treeline
    for bx in range(0, REFERENCE_WIDTH, 120):
        pygame.draw.polygon(
            surf,
            (74, 222, 128),
            [(bx, 380), (bx + 60, 220), (bx + 120, 380)],
        )

    # Ground
    pygame.draw.rect(surf, (34, 197, 94), (0, 380, REFERENCE_WIDTH, 220))
    pygame.draw.ellipse(surf, (22, 163, 74), pygame.Rect(-60, 370, 500, 100))
    pygame.draw.ellipse(surf, (22, 163, 74), pygame.Rect(400, 370, 700, 100))

    # Hero Oak tree trunk on left
    pygame.draw.rect(surf, (120, 53, 15), (70, 200, 90, 220), border_radius=12)
    pygame.draw.circle(surf, (34, 197, 94), (115, 180), 95)

    # Bush & log props
    pygame.draw.ellipse(surf, (22, 163, 74), pygame.Rect(50, 440, 150, 80))
    pygame.draw.rect(surf, (90, 55, 35), (400, 460, 170, 50), border_radius=10)
    pygame.draw.ellipse(surf, (100, 116, 139), pygame.Rect(630, 450, 170, 70))
    pygame.draw.ellipse(surf, (34, 197, 94), pygame.Rect(810, 435, 160, 80))


class WoodlandArtLibrary:
    """Pre-renders static woodland background and manages bounded sprite caches."""

    def __init__(self, root_path: Path | None = None) -> None:
        if root_path is None:
            # Resolves repo root from activities/nascondino_bosco/
            root_path = Path(__file__).resolve().parents[2]
        self._root = root_path
        self._portrait_cache: BoundedCache[tuple[str, int], pygame.Surface] = BoundedCache(32)
        self._bg_surface: pygame.Surface | None = None
        self._hollow_overlay: pygame.Surface | None = None

    def get_background(self) -> pygame.Surface:
        """Return the pre-baked 1024x600 opaque woodland background."""
        if self._bg_surface is None:
            self._bg_surface = self._bake_background()
        return self._bg_surface

    def _bake_background(self) -> pygame.Surface:
        """Render the rich vector scene once onto an opaque converted Surface."""
        bg = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        if pygame.display.get_init() and pygame.display.get_surface():
            try:
                bg = bg.convert()
            except Exception:
                pass

        scene_file = self._root / "assets" / "scenes" / "forest_meadow_day_v1.toml"
        baked_cleanly = False

        if scene_file.is_file():
            try:
                scene = load_scene(scene_file)
                renderer = PygameSceneRenderer.for_activity(max_entries=32)
                # Render background & midground scenery (z <= 59)
                renderer.draw(
                    scene,
                    bg,
                    elapsed_seconds=0.0,
                    motion_enabled=False,
                    clear=True,
                    max_z=59,
                )
                # Render Lilli Mascot Guide
                lilli_scene = actor_scene_sample(
                    LILLI_ACTOR,
                    canvas_size=scene.canvas_size,
                    elapsed_seconds=0.0,
                    fit=scene.fit,
                    motion_enabled=False,
                )
                renderer.draw(
                    lilli_scene,
                    bg,
                    elapsed_seconds=0.0,
                    motion_enabled=False,
                    clear=False,
                )
                baked_cleanly = True
            except Exception:
                baked_cleanly = False

        if not baked_cleanly:
            _draw_legacy_forest_background(bg)

        # Cut the dark hollow into the left hero oak tree trunk at (110, 350)
        # to create a natural, grounded hiding nook
        pygame.draw.ellipse(bg, (30, 18, 12), pygame.Rect(75, 305, 70, 90))
        pygame.draw.ellipse(bg, (20, 10, 6), pygame.Rect(80, 315, 60, 70))

        return bg

    def get_animal_portrait(self, animal_id: str, size: int) -> pygame.Surface:
        """Return a cached high-quality animal portrait surface."""
        key = (animal_id, size)
        cached = self._portrait_cache.get(key)
        if cached is not None:
            return cached

        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = size // 2
        cy = size // 2
        r = size // 2
        dark = (30, 41, 59)

        if animal_id == "fox":
            # Orange Fox with white cheeks & perky ears
            pygame.draw.circle(surf, (249, 115, 22), (cx, cy), r)
            pygame.draw.circle(surf, dark, (cx, cy), r, 2)
            # Ears
            pygame.draw.polygon(
                surf,
                (249, 115, 22),
                [(cx - r, cy - r // 3), (cx - r * 3 // 4, cy - r), (cx - r // 4, cy - r // 2)],
            )
            pygame.draw.polygon(
                surf,
                dark,
                [(cx - r, cy - r // 3), (cx - r * 3 // 4, cy - r), (cx - r // 4, cy - r // 2)],
                2,
            )
            pygame.draw.polygon(
                surf,
                (249, 115, 22),
                [(cx + r, cy - r // 3), (cx + r * 3 // 4, cy - r), (cx + r // 4, cy - r // 2)],
            )
            pygame.draw.polygon(
                surf,
                dark,
                [(cx + r, cy - r // 3), (cx + r * 3 // 4, cy - r), (cx + r // 4, cy - r // 2)],
                2,
            )
            # Cheeks & snout
            pygame.draw.circle(surf, (255, 237, 213), (cx - r // 3, cy + r // 4), r // 3)
            pygame.draw.circle(surf, (255, 237, 213), (cx + r // 3, cy + r // 4), r // 3)
            pygame.draw.circle(surf, dark, (cx - r // 3, cy - r // 6), max(2, r // 6))
            pygame.draw.circle(surf, dark, (cx + r // 3, cy - r // 6), max(2, r // 6))
            pygame.draw.circle(surf, dark, (cx, cy + r // 5), max(2, r // 7))

        elif animal_id == "bunny":
            # Soft White Bunny with tall pink-lined ears
            pygame.draw.ellipse(surf, (255, 255, 255), pygame.Rect(cx - r // 2, cy - r, r // 3, r))
            pygame.draw.ellipse(surf, dark, pygame.Rect(cx - r // 2, cy - r, r // 3, r), 2)
            pygame.draw.ellipse(
                surf, (244, 114, 182), pygame.Rect(cx - r // 2 + 2, cy - r + 4, r // 3 - 4, r - 8)
            )
            pygame.draw.ellipse(surf, (255, 255, 255), pygame.Rect(cx + r // 6, cy - r, r // 3, r))
            pygame.draw.ellipse(surf, dark, pygame.Rect(cx + r // 6, cy - r, r // 3, r), 2)
            pygame.draw.ellipse(
                surf, (244, 114, 182), pygame.Rect(cx + r // 6 + 2, cy - r + 4, r // 3 - 4, r - 8)
            )
            # Face
            pygame.draw.circle(surf, (255, 255, 255), (cx, cy + r // 4), r * 3 // 4)
            pygame.draw.circle(surf, dark, (cx, cy + r // 4), r * 3 // 4, 2)
            pygame.draw.circle(surf, dark, (cx - r // 4, cy + r // 6), max(2, r // 7))
            pygame.draw.circle(surf, dark, (cx + r // 4, cy + r // 6), max(2, r // 7))
            pygame.draw.circle(surf, (244, 114, 182), (cx, cy + r // 3), max(2, r // 8))

        elif animal_id == "owl":
            # Wise Brown Owl with big bright yellow eyes & orange beak
            pygame.draw.circle(surf, (161, 98, 7), (cx, cy), r)
            pygame.draw.circle(surf, dark, (cx, cy), r, 2)
            # Big eyes
            pygame.draw.circle(surf, (254, 240, 138), (cx - r // 3, cy - r // 6), r // 3)
            pygame.draw.circle(surf, (254, 240, 138), (cx + r // 3, cy - r // 6), r // 3)
            pygame.draw.circle(surf, dark, (cx - r // 3, cy - r // 6), r // 3, 2)
            pygame.draw.circle(surf, dark, (cx + r // 3, cy - r // 6), r // 3, 2)
            pygame.draw.circle(surf, dark, (cx - r // 3, cy - r // 6), r // 6)
            pygame.draw.circle(surf, dark, (cx + r // 3, cy - r // 6), r // 6)
            # Beak
            pygame.draw.polygon(
                surf, (249, 115, 22), [(cx - 4, cy), (cx + 4, cy), (cx, cy + r // 3)]
            )
            pygame.draw.polygon(
                surf, dark, [(cx - 4, cy), (cx + 4, cy), (cx, cy + r // 3)], 1
            )

        elif animal_id == "frog":
            # Cheerful Green Frog with protruding eyes & happy smile
            pygame.draw.circle(surf, (34, 197, 94), (cx, cy), r)
            pygame.draw.circle(surf, (34, 197, 94), (cx - r // 2, cy - r // 2), r // 3)
            pygame.draw.circle(surf, (34, 197, 94), (cx + r // 2, cy - r // 2), r // 3)
            pygame.draw.circle(surf, (255, 255, 255), (cx - r // 2, cy - r // 2), r // 5)
            pygame.draw.circle(surf, (255, 255, 255), (cx + r // 2, cy - r // 2), r // 5)
            pygame.draw.circle(surf, dark, (cx - r // 2, cy - r // 2), r // 8)
            pygame.draw.circle(surf, dark, (cx + r // 2, cy - r // 2), r // 8)
            pygame.draw.circle(surf, dark, (cx, cy), r, 2)
            pygame.draw.arc(
                surf, dark, pygame.Rect(cx - r // 2, cy - r // 4, r, r // 2), 3.4, 6.0, 3
            )

        elif animal_id == "squirrel":
            # Golden Squirrel with light muzzle & cute round eyes
            pygame.draw.circle(surf, (217, 119, 6), (cx, cy), r)
            pygame.draw.circle(surf, dark, (cx, cy), r, 2)
            pygame.draw.circle(surf, (254, 215, 170), (cx - r // 3, cy + r // 4), r // 3)
            pygame.draw.circle(surf, (254, 215, 170), (cx + r // 3, cy + r // 4), r // 3)
            pygame.draw.circle(surf, dark, (cx - r // 4, cy - r // 6), max(2, r // 7))
            pygame.draw.circle(surf, dark, (cx + r // 4, cy - r // 6), max(2, r // 7))
            pygame.draw.circle(surf, dark, (cx, cy + r // 5), max(2, r // 8))

        else:  # hedgehog
            # Brown Hedgehog with warm creamy face & dark nose
            pygame.draw.circle(surf, (120, 53, 15), (cx, cy), r)
            pygame.draw.circle(surf, dark, (cx, cy), r, 2)
            pygame.draw.circle(surf, (254, 243, 199), (cx - r // 4, cy + r // 6), r // 2)
            pygame.draw.circle(surf, dark, (cx - r // 3, cy), max(2, r // 7))
            pygame.draw.circle(surf, dark, (cx - r * 2 // 3, cy + r // 6), max(2, r // 6))

        if pygame.display.get_init() and pygame.display.get_surface():
            try:
                surf = surf.convert_alpha()
            except Exception:
                pass

        self._portrait_cache[key] = surf
        return surf

    def draw_peeking_clue(
        self,
        target_surface: pygame.Surface,
        spot: HidingSpotDefinition,
        animal_id: str,
        t_now: float,
    ) -> None:
        """Render a subtle, grounded animated clue at a hiding spot."""
        sx, sy = spot.cx, spot.cy

        if spot.kind == "tree_hollow":
            # Clue inside tree hollow
            if animal_id == "owl":
                # Blinking glowing owl eyes in the dark hollow
                blink = abs(math.sin(t_now * 2.8)) > 0.18
                if blink:
                    pygame.draw.circle(target_surface, (254, 240, 138), (sx - 14, sy), 9)
                    pygame.draw.circle(target_surface, (20, 20, 30), (sx - 14, sy), 5)
                    pygame.draw.circle(target_surface, (254, 240, 138), (sx + 14, sy), 9)
                    pygame.draw.circle(target_surface, (20, 20, 30), (sx + 14, sy), 5)
            elif animal_id == "squirrel":
                # Squirrel tail peeking out of hollow
                sway = math.sin(t_now * 4.0) * 8.0
                pygame.draw.circle(
                    target_surface, (217, 119, 6), (int(sx + 24 + sway), sy - 10), 16
                )
                pygame.draw.circle(
                    target_surface, (254, 215, 170), (int(sx + 30 + sway), sy - 14), 8
                )
            else:
                portrait = self.get_animal_portrait(animal_id, 34)
                target_surface.blit(portrait, (sx - 17, sy - 17))

        elif spot.kind in ("round_bush", "flowering_bush"):
            # Clue peeking above/beside bush
            if animal_id == "bunny":
                # Twitching ears over bush
                ear_w = math.sin(t_now * 5.5) * 3.5
                pygame.draw.ellipse(
                    target_surface,
                    (255, 255, 255),
                    pygame.Rect(sx - 18 + ear_w, sy - 60, 14, 34),
                )
                pygame.draw.ellipse(
                    target_surface,
                    (244, 114, 182),
                    pygame.Rect(sx - 15 + ear_w, sy - 56, 8, 22),
                )
                pygame.draw.ellipse(
                    target_surface,
                    (255, 255, 255),
                    pygame.Rect(sx + 4 - ear_w, sy - 60, 14, 34),
                )
                pygame.draw.ellipse(
                    target_surface,
                    (244, 114, 182),
                    pygame.Rect(sx + 7 - ear_w, sy - 56, 8, 22),
                )
            elif animal_id == "fox":
                # Wagging bushy orange tail on the side
                tail_w = math.sin(t_now * 4.0) * 12.0
                pygame.draw.circle(
                    target_surface, (249, 115, 22), (int(sx + 45 + tail_w), sy - 20), 18
                )
                pygame.draw.circle(
                    target_surface, (255, 237, 213), (int(sx + 55 + tail_w), sy - 24), 9
                )
            elif animal_id == "hedgehog":
                # Sniffing little nose peeking from leaves
                sniff = math.sin(t_now * 7.0) * 2.5
                pygame.draw.circle(
                    target_surface, (254, 243, 199), (int(sx + sniff), sy - 40), 15
                )
                pygame.draw.circle(
                    target_surface, (30, 41, 59), (int(sx - 10 + sniff), sy - 40), 5
                )
            else:
                portrait = self.get_animal_portrait(animal_id, 32)
                target_surface.blit(portrait, (sx - 16, sy - 45))

        elif spot.kind == "fallen_log":
            # Clue peeking over the fallen log
            if animal_id == "frog":
                # Bouncing frog eyes over log
                f_y = sy - 45 + math.sin(t_now * 4.5) * 6.0
                pygame.draw.circle(target_surface, (34, 197, 94), (sx - 14, int(f_y)), 10)
                pygame.draw.circle(target_surface, (255, 255, 255), (sx - 14, int(f_y)), 6)
                pygame.draw.circle(target_surface, (30, 41, 59), (sx - 14, int(f_y)), 3)
                pygame.draw.circle(target_surface, (34, 197, 94), (sx + 14, int(f_y)), 10)
                pygame.draw.circle(target_surface, (255, 255, 255), (sx + 14, int(f_y)), 6)
                pygame.draw.circle(target_surface, (30, 41, 59), (sx + 14, int(f_y)), 3)
            elif animal_id == "squirrel":
                tail_w = math.sin(t_now * 5.0) * 10.0
                pygame.draw.circle(
                    target_surface, (217, 119, 6), (int(sx + 35 + tail_w), sy - 45), 18
                )
                pygame.draw.circle(
                    target_surface, (254, 215, 170), (int(sx + 42 + tail_w), sy - 50), 9
                )
            else:
                portrait = self.get_animal_portrait(animal_id, 32)
                target_surface.blit(portrait, (sx - 16, sy - 48))

        else:  # rock_cluster
            # Clue peeking around the rocks
            if animal_id == "hedgehog":
                sniff = math.sin(t_now * 8.0) * 3.0
                pygame.draw.circle(
                    target_surface, (254, 243, 199), (int(sx - 20 + sniff), sy - 35), 16
                )
                pygame.draw.circle(
                    target_surface, (30, 41, 59), (int(sx - 32 + sniff), sy - 35), 5
                )
            elif animal_id == "owl":
                blink = abs(math.sin(t_now * 3.0)) > 0.15
                if blink:
                    pygame.draw.circle(target_surface, (254, 240, 138), (sx - 12, sy - 42), 8)
                    pygame.draw.circle(target_surface, (20, 20, 30), (sx - 12, sy - 42), 4)
                    pygame.draw.circle(target_surface, (254, 240, 138), (sx + 12, sy - 42), 8)
                    pygame.draw.circle(target_surface, (20, 20, 30), (sx + 12, sy - 42), 4)
            else:
                portrait = self.get_animal_portrait(animal_id, 32)
                target_surface.blit(portrait, (sx - 16, sy - 45))
