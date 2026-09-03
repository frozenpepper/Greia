"""Sottomarino Giramondo — Procedural & Bounded Graphic Generator.

Generates and caches all tactile cockpit assets, gauges, marine creatures,
and porthole masks at native reference resolution (1024x600).
Zero external image files required; renders crisp, warm, and highly tactile.
"""

from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

import pygame

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600

# Viewport Porthole Geometry (Centered in the upper cockpit area)
PORTHOLE_CENTER_X = 512
PORTHOLE_CENTER_Y = 218
PORTHOLE_RADIUS = 175


def _create_porthole_mask(width: int, height: int) -> pygame.Surface:
    """Pre-bake a mask that punches out the round glass porthole with rivets."""
    mask = pygame.Surface((width, height), pygame.SRCALPHA)
    # Fill cockpit surround
    # Upper rim / bulkhead metal color
    bulkhead_color = (45, 58, 72)
    mask.fill(bulkhead_color)

    # Cut out transparent circle for the ocean viewport
    pygame.draw.circle(mask, (0, 0, 0, 0), (PORTHOLE_CENTER_X, PORTHOLE_CENTER_Y), PORTHOLE_RADIUS)

    # Heavy brass/steel rim ring
    rim_outer = PORTHOLE_RADIUS + 24
    rim_inner = PORTHOLE_RADIUS - 4
    pygame.draw.circle(mask, (212, 160, 48), (PORTHOLE_CENTER_X, PORTHOLE_CENTER_Y), rim_outer, 24)
    pygame.draw.circle(mask, (150, 105, 25), (PORTHOLE_CENTER_X, PORTHOLE_CENTER_Y), rim_outer, 3)
    pygame.draw.circle(mask, (245, 205, 90), (PORTHOLE_CENTER_X, PORTHOLE_CENTER_Y), rim_inner, 3)

    # Rivet bolts around the rim
    for i in range(12):
        angle = i * (math.pi * 2 / 12)
        rx = PORTHOLE_CENTER_X + int((PORTHOLE_RADIUS + 12) * math.cos(angle))
        ry = PORTHOLE_CENTER_Y + int((PORTHOLE_RADIUS + 12) * math.sin(angle))
        pygame.draw.circle(mask, (100, 75, 20), (rx, ry), 6)
        pygame.draw.circle(mask, (250, 220, 120), (rx - 1, ry - 1), 3)

    # Soft glass reflection sheen arc across top-left of porthole
    glass_sheen = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.arc(
        glass_sheen,
        (255, 255, 255, 60),
        (PORTHOLE_CENTER_X - PORTHOLE_RADIUS + 15, PORTHOLE_CENTER_Y - PORTHOLE_RADIUS + 15, (PORTHOLE_RADIUS - 15) * 2, (PORTHOLE_RADIUS - 15) * 2),
        math.radians(100),
        math.radians(170),
        16
    )
    mask.blit(glass_sheen, (0, 0))
    return mask


class SubmarineArt:
    """Owner of cached visual surfaces for creatures and instruments."""

    def __init__(self) -> None:
        self.porthole_mask = _create_porthole_mask(REFERENCE_WIDTH, REFERENCE_HEIGHT)
        self._sprite_cache: Dict[str, pygame.Surface] = {}
        self._bake_creatures()

    def _bake_creatures(self) -> None:
        # Pre-render marine creature sprites to keep hot render loop fast
        self._sprite_cache["clownfish"] = self._render_clownfish()
        self._sprite_cache["turtle"] = self._render_turtle()
        self._sprite_cache["dolphin"] = self._render_dolphin()
        self._sprite_cache["manta"] = self._render_manta()
        self._sprite_cache["angler"] = self._render_angler()
        self._sprite_cache["whale"] = self._render_whale()
        self._sprite_cache["bubble"] = self._render_bubble()
        self._sprite_cache["octopus"] = self._render_octopus()
        self._sprite_cache["shark"] = self._render_shark()
        self._sprite_cache["coral"] = self._render_coral()
        self._sprite_cache["kelp"] = self._render_kelp()
        self._sprite_cache["krill"] = self._render_krill()

    def get_sprite(self, name: str) -> Optional[pygame.Surface]:
        return self._sprite_cache.get(name)

    def _render_clownfish(self) -> pygame.Surface:
        surf = pygame.Surface((80, 50), pygame.SRCALPHA)
        # Orange oval body
        pygame.draw.ellipse(surf, (255, 110, 30), (10, 10, 55, 30))
        # White stripes
        pygame.draw.ellipse(surf, (255, 255, 255), (32, 8, 10, 34))
        pygame.draw.ellipse(surf, (255, 255, 255), (48, 12, 7, 26))
        # Black stripe outlines
        pygame.draw.arc(surf, (30, 30, 30), (32, 8, 10, 34), 0, math.pi * 2, 2)
        # Tail fin
        pygame.draw.polygon(surf, (255, 90, 20), [(15, 25), (0, 12), (0, 38)])
        # Eye
        pygame.draw.circle(surf, (255, 255, 255), (56, 20), 5)
        pygame.draw.circle(surf, (20, 20, 20), (58, 20), 3)
        return surf

    def _render_turtle(self) -> pygame.Surface:
        surf = pygame.Surface((110, 80), pygame.SRCALPHA)
        # Shell
        pygame.draw.ellipse(surf, (40, 140, 70), (25, 20, 60, 45))
        pygame.draw.ellipse(surf, (70, 180, 100), (30, 24, 50, 36))
        # Flippers
        pygame.draw.ellipse(surf, (50, 150, 80), (60, 10, 35, 18))  # front-top
        pygame.draw.ellipse(surf, (50, 150, 80), (60, 52, 35, 18))  # front-bottom
        pygame.draw.ellipse(surf, (40, 120, 65), (15, 16, 22, 14))  # rear-top
        pygame.draw.ellipse(surf, (40, 120, 65), (15, 50, 22, 14))  # rear-bottom
        # Head
        pygame.draw.ellipse(surf, (60, 160, 90), (80, 32, 25, 20))
        # Eye
        pygame.draw.circle(surf, (20, 20, 20), (96, 38), 3)
        return surf

    def _render_dolphin(self) -> pygame.Surface:
        surf = pygame.Surface((150, 80), pygame.SRCALPHA)
        # Sleek grey-blue curved body
        pygame.draw.ellipse(surf, (90, 140, 180), (25, 22, 105, 40))
        pygame.draw.ellipse(surf, (210, 235, 250), (45, 40, 75, 22))  # Belly
        # Dorsal fin
        pygame.draw.polygon(surf, (80, 130, 170), [(70, 25), (85, 5), (95, 25)])
        # Tail flukes
        pygame.draw.polygon(surf, (80, 130, 170), [(28, 42), (5, 25), (12, 42), (5, 58)])
        # Snout / beak
        pygame.draw.ellipse(surf, (90, 140, 180), (120, 38, 26, 14))
        # Eye and cute smile
        pygame.draw.circle(surf, (20, 20, 20), (120, 34), 4)
        pygame.draw.circle(surf, (255, 255, 255), (121, 33), 1)
        return surf

    def _render_manta(self) -> pygame.Surface:
        surf = pygame.Surface((160, 110), pygame.SRCALPHA)
        # Diamond wings
        points = [(80, 15), (150, 55), (80, 95), (20, 55)]
        pygame.draw.polygon(surf, (60, 75, 95), points)
        # Belly inner diamond
        inner = [(80, 28), (135, 55), (80, 82), (35, 55)]
        pygame.draw.polygon(surf, (220, 230, 240), inner)
        # Tail
        pygame.draw.line(surf, (40, 50, 65), (20, 55), (0, 55), 4)
        # Horns / cephalic lobes
        pygame.draw.ellipse(surf, (60, 75, 95), (140, 42, 18, 10))
        pygame.draw.ellipse(surf, (60, 75, 95), (140, 58, 18, 10))
        return surf

    def _render_angler(self) -> pygame.Surface:
        surf = pygame.Surface((100, 70), pygame.SRCALPHA)
        # Round chubby deep-sea body
        pygame.draw.ellipse(surf, (45, 35, 55), (20, 20, 65, 45))
        # Big glowing yellow lure on stalk
        pygame.draw.arc(surf, (80, 70, 90), (45, 0, 40, 30), 0, math.pi * 0.8, 3)
        pygame.draw.circle(surf, (255, 240, 100), (48, 10), 9)
        pygame.draw.circle(surf, (255, 255, 200), (48, 10), 5)
        # Tail
        pygame.draw.polygon(surf, (45, 35, 55), [(22, 42), (5, 28), (5, 56)])
        # Eye
        pygame.draw.circle(surf, (255, 255, 255), (70, 32), 6)
        pygame.draw.circle(surf, (20, 20, 20), (72, 32), 4)
        return surf

    def _render_whale(self) -> pygame.Surface:
        surf = pygame.Surface((220, 110), pygame.SRCALPHA)
        # Huge gentle blue whale body
        pygame.draw.ellipse(surf, (40, 85, 140), (35, 25, 165, 65))
        # Pleated throat lines
        pygame.draw.ellipse(surf, (160, 200, 240), (80, 55, 110, 32))
        # Tail flukes
        pygame.draw.polygon(surf, (35, 75, 125), [(42, 55), (5, 25), (18, 55), (5, 85)])
        # Eye
        pygame.draw.circle(surf, (20, 20, 20), (175, 48), 5)
        pygame.draw.circle(surf, (255, 255, 255), (176, 47), 2)
        return surf

    def _render_bubble(self) -> pygame.Surface:
        surf = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(surf, (200, 240, 255, 180), (15, 15), 12, 2)
        pygame.draw.circle(surf, (255, 255, 255, 220), (11, 10), 3)
        return surf

    def _render_octopus(self) -> pygame.Surface:
        """Encounter: Friendly orange octopus hugging porthole."""
        surf = pygame.Surface((320, 320), pygame.SRCALPHA)
        center = (160, 160)
        # Bulbous cute head
        pygame.draw.ellipse(surf, (245, 110, 70), (100, 60, 120, 110))
        # Big friendly cartoon eyes
        pygame.draw.circle(surf, (255, 255, 255), (135, 110), 16)
        pygame.draw.circle(surf, (20, 20, 20), (137, 110), 9)
        pygame.draw.circle(surf, (255, 255, 255), (139, 107), 4)

        pygame.draw.circle(surf, (255, 255, 255), (185, 110), 16)
        pygame.draw.circle(surf, (20, 20, 20), (183, 110), 9)
        pygame.draw.circle(surf, (255, 255, 255), (185, 107), 4)

        # Cheerful smile
        pygame.draw.arc(surf, (150, 40, 20), (145, 125, 30, 20), math.pi, 0, 4)

        # Tentacles with suction cups hugging the edges
        for i in range(6):
            angle = math.radians(20 + i * 28)
            tx = int(160 + 130 * math.cos(angle))
            ty = int(160 + 130 * math.sin(angle))
            pygame.draw.circle(surf, (245, 110, 70), (tx, ty), 22)
            # Suction cup rings pressed against glass
            pygame.draw.circle(surf, (255, 220, 200), (tx, ty), 14, 4)
            pygame.draw.circle(surf, (255, 240, 230), (tx, ty), 7)
        return surf

    def _render_shark(self) -> pygame.Surface:
        """Encounter: Friendly smiling shark waving a fin."""
        surf = pygame.Surface((300, 220), pygame.SRCALPHA)
        # Body
        pygame.draw.ellipse(surf, (90, 115, 140), (50, 50, 200, 100))
        # White belly
        pygame.draw.ellipse(surf, (240, 245, 250), (90, 95, 150, 50))
        # Big dorsal fin
        pygame.draw.polygon(surf, (80, 105, 130), [(140, 55), (170, 10), (195, 55)])
        # Pectoral fin waving
        pygame.draw.polygon(surf, (80, 105, 130), [(130, 120), (110, 175), (160, 135)])
        # Happy smile
        pygame.draw.arc(surf, (30, 30, 30), (180, 95, 45, 30), math.pi * 0.9, 0, 4)
        # Kind eye
        pygame.draw.circle(surf, (255, 255, 255), (210, 75), 10)
        pygame.draw.circle(surf, (20, 20, 20), (212, 75), 5)
        pygame.draw.circle(surf, (255, 255, 255), (213, 73), 2)
        return surf

    def _render_coral(self) -> pygame.Surface:
        """Colorful branching coral reef formation."""
        surf = pygame.Surface((180, 160), pygame.SRCALPHA)
        # Base rock shelf
        pygame.draw.ellipse(surf, (60, 55, 70), (20, 120, 140, 35))
        # Orange/Pink staghorn branches
        coral_col = (255, 105, 120)
        branches = [
            [(45, 130), (50, 80), (35, 45), (45, 20)],
            [(50, 80), (70, 50), (75, 25)],
            [(90, 130), (90, 70), (85, 30), (100, 15)],
            [(90, 70), (115, 50), (120, 25)],
            [(135, 130), (130, 80), (145, 50), (140, 25)],
        ]
        for b in branches:
            pygame.draw.lines(surf, coral_col, False, b, 14)
            for pt in b:
                pygame.draw.circle(surf, coral_col, pt, 7)
        # Brain coral dome on side
        pygame.draw.circle(surf, (110, 210, 160), (140, 115), 24)
        pygame.draw.circle(surf, (80, 175, 130), (140, 115), 20, 3)
        return surf

    def _render_kelp(self) -> pygame.Surface:
        """Tall undulating kelp stalk with golden-green fronds."""
        surf = pygame.Surface((140, 260), pygame.SRCALPHA)
        kelp_stem = (40, 130, 60)
        kelp_leaf = (70, 175, 80)
        kelp_light = (110, 210, 110)
        # Stem wave
        stem_pts = [(70, 255), (65, 200), (75, 140), (60, 80), (70, 15)]
        pygame.draw.lines(surf, kelp_stem, False, stem_pts, 8)
        # Fronds branching out with air bladders
        leaf_data = [
            (65, 200, -35, 18),
            (70, 170, 40, -15),
            (75, 135, -45, 12),
            (65, 100, 42, -10),
            (60, 65, -40, 8),
            (68, 30, 35, -8),
        ]
        for lx, ly, dx, dy in leaf_data:
            # Gas bladder
            pygame.draw.circle(surf, (130, 210, 90), (lx, ly), 5)
            # Long flowing leaf blade
            pygame.draw.ellipse(surf, kelp_leaf, (min(lx, lx + dx), min(ly, ly + dy), abs(dx) + 15, 22))
            pygame.draw.ellipse(surf, kelp_light, (min(lx, lx + dx) + 3, min(ly, ly + dy) + 3, abs(dx) + 8, 12))
        return surf

    def _render_krill(self) -> pygame.Surface:
        """Sparkling cluster of translucent bioluminescent krill."""
        surf = pygame.Surface((150, 100), pygame.SRCALPHA)
        krill_positions = [
            (25, 30), (45, 20), (70, 35), (95, 25), (120, 40),
            (35, 60), (60, 55), (85, 70), (110, 65), (75, 85)
        ]
        for kx, ky in krill_positions:
            # Glowing aura
            pygame.draw.circle(surf, (80, 200, 255, 60), (kx, ky), 10)
            # Translucent shrimp body
            pygame.draw.ellipse(surf, (255, 140, 100, 220), (kx - 8, ky - 3, 16, 7))
            # Bioluminescent blue photophore light
            pygame.draw.circle(surf, (140, 240, 255), (kx + 2, ky + 1), 3)
            pygame.draw.circle(surf, (255, 255, 255), (kx + 2, ky + 1), 1)
            # Tiny tail
            pygame.draw.line(surf, (255, 120, 80, 200), (kx - 8, ky), (kx - 12, ky - 2), 2)
        return surf
