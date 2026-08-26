"""Pre-rendered visual assets and bounded sprite caches for Il Viaggio del Delfino.

Everything the renderer blits is prepared here once: an opaque converted
backdrop, colorkey scenery/sprite frames, pitch-pose dolphin frames, HUD
furniture and Tito's canonical portrait. No decode/scale/rotate happens in
the frame loop (see ENGINEERING.md §7). Caches are natural-bounded by their
fixed key sets.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Final

import pygame

from greia_platform.ui_core import BoundedCache

try:
    from delfino_model import MAX_SWIM_Y, REFERENCE_HEIGHT, REFERENCE_WIDTH, SURFACE_Y
except ImportError:  # repository/package import context
    from .delfino_model import MAX_SWIM_Y, REFERENCE_HEIGHT, REFERENCE_WIDTH, SURFACE_Y


#: Colorkey must differ from every sea/sky/sprite color used below.
COLORKEY: Final = (2, 1, 3)

#: Pre-baked frames of the breach somersault (a full front flip).
FLIP_STEPS: Final = 10

# ---------------------------------------------------------------- palette
SKY_TOP = (116, 188, 248)
SKY_HORIZON = (206, 238, 252)
SEA_TOP = (74, 170, 228)
SEA_MID = (40, 122, 190)
SEA_DEEP = (22, 72, 128)
SAND = (236, 216, 168)
FOAM = (240, 250, 255)
DOLPHIN_TOP = (88, 162, 216)
DOLPHIN_MID = (110, 186, 234)
DOLPHIN_BELLY = (226, 243, 252)
DOLPHIN_EDGE = (42, 92, 146)
PEARL_SHELL = (244, 186, 208)
PEARL_SHELL_DARK = (214, 138, 172)
#: Clam treasure palette — warm cream/caramel, clearly distinct from the pink
#: jellyfish so pickups and friendly obstacles never read as the same thing.
CLAM_SHELL = (248, 226, 178)
CLAM_SHELL_LIGHT = (255, 244, 216)
CLAM_RIM = (186, 134, 74)
STAR_GOLD = (255, 202, 62)
STAR_EDGE = (214, 148, 20)
JELLY_BODY = (242, 152, 202)
JELLY_LIGHT = (252, 190, 222)
JELLY_TENTACLE = (198, 130, 214)
KELP_MAIN = (64, 158, 114)
KELP_DARK = (40, 118, 86)
CORAL_MAIN = (250, 132, 112)
CORAL_DARK = (220, 96, 88)
GOLD_REEF = (255, 210, 92)
WHITE = (255, 255, 255)
INK = (36, 52, 84)


def _mix(
    c1: tuple[int, int, int], c2: tuple[int, int, int], factor: float
) -> tuple[int, int, int]:
    f = max(0.0, min(1.0, factor))
    return (
        int(round(c1[0] * (1.0 - f) + c2[0] * f)),
        int(round(c1[1] * (1.0 - f) + c2[1] * f)),
        int(round(c1[2] * (1.0 - f) + c2[2] * f)),
    )


def _sea_color_at(y: int) -> tuple[int, int, int]:
    """Sea gradient color at reference y (shared by backdrop and shafts)."""

    horizon = int(SURFACE_Y) + 26
    t = (y - horizon) / float(REFERENCE_HEIGHT - horizon)
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        return _mix(SEA_TOP, SEA_MID, t / 0.5)
    return _mix(SEA_MID, SEA_DEEP, (t - 0.5) / 0.5)


def _colorkey_surface(width: int, height: int) -> pygame.Surface:
    surf = pygame.Surface((width, height))
    if pygame.display.get_init() and pygame.display.get_surface():
        try:
            surf = surf.convert()
        except Exception:
            pass
    surf.fill(COLORKEY)
    surf.set_colorkey(COLORKEY)
    return surf


class DelfinoArtLibrary:
    """Owns every pre-rendered surface used by the journey renderer."""

    def __init__(self, root_path: Path | None = None) -> None:
        self._root = root_path
        self._backdrop: pygame.Surface | None = None
        self._islands: pygame.Surface | None = None
        self._clouds: tuple[pygame.Surface, pygame.Surface, pygame.Surface] | None = None
        self._wave_tiles: tuple[pygame.Surface, pygame.Surface] | None = None
        self._pearl: pygame.Surface | None = None
        self._small_pearl: pygame.Surface | None = None
        self._starfish: pygame.Surface | None = None
        self._jelly_frames: tuple[pygame.Surface, ...] | None = None
        self._kelp_strips: dict[int, pygame.Surface] = {}
        self._coral: pygame.Surface | None = None
        self._landmarks: dict[str, pygame.Surface] = {}
        self._dolphin_poses: dict[tuple[int, int], pygame.Surface] = {}
        self._flip_frames: dict[int, pygame.Surface] = {}
        self._particle_cache: BoundedCache = BoundedCache(48)
        self._hud_bar: pygame.Surface | None = None
        self._marker: pygame.Surface | None = None
        self._tito: pygame.Surface | None = None

    # ------------------------------------------------------------- backdrop

    def get_backdrop(self) -> pygame.Surface:
        """Opaque 1024x600 baked sky/sea gradient with sun and light shafts."""

        if self._backdrop is not None:
            return self._backdrop
        surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        if pygame.display.get_init() and pygame.display.get_surface():
            try:
                surf = surf.convert()
            except Exception:
                pass

        horizon = int(SURFACE_Y) + 26
        for y in range(horizon):
            t = y / float(horizon)
            pygame.draw.line(surf, _mix(SKY_TOP, SKY_HORIZON, t), (0, y), (REFERENCE_WIDTH, y))

        for y in range(horizon, REFERENCE_HEIGHT):
            pygame.draw.line(surf, _sea_color_at(y), (0, y), (REFERENCE_WIDTH, y))

        # Sun: soft halo + core, small and corner-friendly.
        sun_x, sun_y = 872, 76
        pygame.draw.circle(surf, _mix(SKY_HORIZON, (255, 224, 130), 0.55), (sun_x, sun_y), 54)
        pygame.draw.circle(surf, (255, 236, 160), (sun_x, sun_y), 40)
        pygame.draw.circle(surf, (255, 222, 108), (sun_x, sun_y), 30)
        pygame.draw.circle(surf, (255, 240, 190), (sun_x - 9, sun_y - 9), 9)

        # Soft, subtle light shafts: slim slanted wedges lightened from the
        # sea color at their own depth, so they glow without banding.
        for base_x, top_w, bot_w, strength in ((150, 22, 60, 0.10), (430, 16, 44, 0.08), (700, 26, 70, 0.09)):
            steps = 12
            for i in range(steps):
                t = i / float(steps - 1)
                y0 = int(SURFACE_Y) + 6 + t * 130
                y1 = y0 + 130
                color = _mix(_sea_color_at(y0 + 65), (255, 255, 255), strength)
                drift = int(t * 46)
                pygame.draw.polygon(
                    surf,
                    color,
                    [
                        (base_x + drift, y0),
                        (base_x + drift + top_w, y0),
                        (base_x + drift + top_w + 18, y1),
                        (base_x + drift + bot_w, y1),
                    ],
                )

        # Sandy seabed with gentle dunes and tiny shells.
        pygame.draw.ellipse(surf, SAND, (-140, REFERENCE_HEIGHT - 56, REFERENCE_WIDTH + 280, 120))
        pygame.draw.ellipse(surf, _mix(SAND, WHITE, 0.25), (420, REFERENCE_HEIGHT - 44, 700, 90))
        pygame.draw.ellipse(surf, _mix(SAND, (196, 168, 120), 0.35), (-80, REFERENCE_HEIGHT - 30, 520, 70))
        for sx, sy in ((210, 574), (540, 566), (852, 578)):
            pygame.draw.circle(surf, PEARL_SHELL_DARK, (sx, sy), 5)
            pygame.draw.circle(surf, _mix(PEARL_SHELL_DARK, WHITE, 0.4), (sx - 1, sy - 1), 2)

        self._backdrop = surf
        return surf

    def get_islands(self) -> pygame.Surface:
        """Wide misty island silhouettes scrolled behind the waves."""

        if self._islands is not None:
            return self._islands
        w, h = 2048, 130
        surf = _colorkey_surface(w, h)
        misty = _mix(SKY_HORIZON, SEA_MID, 0.45)
        misty_far = _mix(SKY_HORIZON, SEA_MID, 0.28)

        def hump(cx: int, base_w: int, height: int, color: tuple[int, int, int]) -> None:
            """Rounded island hill (low dome, never a sharp fin)."""

            pygame.draw.ellipse(surf, color, (cx - base_w // 2, h - height, base_w, height * 2))

        hump(300, 460, 74, misty_far)
        hump(760, 340, 54, misty)
        # Tiny sail on the nearest hill: a friendly, readable silhouette.
        sail_x, sail_y = 764, h - 50
        pygame.draw.line(surf, misty, (sail_x, sail_y + 22), (sail_x, sail_y - 10), 4)
        pygame.draw.polygon(
            surf,
            misty,
            [(sail_x + 1, sail_y - 10), (sail_x + 18, sail_y + 8), (sail_x + 1, sail_y + 8)],
        )
        pygame.draw.line(surf, misty, (sail_x - 14, sail_y + 22), (sail_x + 14, sail_y + 22), 4)
        hump(1450, 520, 82, misty_far)
        hump(1850, 300, 46, misty)
        self._islands = surf
        return surf

    def get_clouds(self) -> tuple[pygame.Surface, pygame.Surface, pygame.Surface]:
        if self._clouds is not None:
            return self._clouds
        clouds = []
        # Lobe centres/radii keep every circle fully inside its canvas so no
        # cloud is cut at the top.
        for w, h, lobes in (
            (150, 78, ((38, 42, 24), (74, 38, 28), (110, 44, 22))),
            (210, 96, ((50, 56, 34), (98, 50, 42), (152, 56, 30))),
            (170, 84, ((44, 46, 27), (84, 42, 32), (126, 48, 26))),
        ):
            cloud = _colorkey_surface(w, h)
            body = _mix(WHITE, (222, 240, 252), 0.35)
            pygame.draw.ellipse(cloud, body, (10, h // 2 - 12, w - 20, 34))
            for lx, ly, lr in lobes:
                pygame.draw.circle(cloud, WHITE, (lx, ly), lr)
                pygame.draw.circle(cloud, body, (lx + lr // 5, ly + lr // 5), int(lr * 0.8))
            clouds.append(cloud)
        self._clouds = (clouds[0], clouds[1], clouds[2])
        return self._clouds

    def get_wave_tiles(self) -> tuple[pygame.Surface, pygame.Surface]:
        """Two scrolling foam strips drawn along the water line."""

        if self._wave_tiles is not None:
            return self._wave_tiles
        tiles = []
        for variant in range(2):
            tw, th = 256, 40
            tile = _colorkey_surface(tw, th)
            # Foam band with scalloped underside; phase differs per variant.
            phase = variant * math.pi / 2.0
            points_top = []
            for x in range(0, tw + 8, 8):
                y = 10 + int(math.sin((x / tw) * math.pi * 4 + phase) * 4)
                points_top.append((x, y))
            for i in range(len(points_top) - 1):
                pygame.draw.line(tile, FOAM, points_top[i], points_top[i + 1], 8)
            for x in range(12, tw, 32):
                r = 9 + (variant * 2)
                cx = x + int(math.sin(x * 0.09 + phase) * 5)
                pygame.draw.circle(tile, FOAM, (cx, 16), r)
                pygame.draw.circle(tile, _mix(FOAM, SEA_TOP, 0.35), (cx + 3, 21), max(4, r - 4))
            tiles.append(tile)
        self._wave_tiles = (tiles[0], tiles[1])
        return self._wave_tiles

    # -------------------------------------------------------------- pickups

    def get_pearl(self) -> pygame.Surface:
        """Classic open-clam treasure: back shell, high pearl, scalloped cup."""

        if self._pearl is not None:
            return self._pearl
        size = 56
        surf = _colorkey_surface(size, size)
        cx = float(size // 2)
        rim_y = 30.0
        cup_half_w, cup_depth = 24.0, 18.0

        # Back shell leaf (opened upwards), drawn first so it sits behind.
        back: list[tuple[float, float]] = []
        for i in range(0, 13):
            angle = math.pi * i / 12.0
            back.append(
                (cx + 21.0 * math.cos(angle), rim_y - 4.0 - 17.0 * math.sin(angle))
            )
        pygame.draw.polygon(surf, CLAM_SHELL_LIGHT, back)
        pygame.draw.polygon(surf, CLAM_RIM, back, 2)
        pygame.draw.line(surf, CLAM_RIM, (cx - 21.0, rim_y - 4.0), (cx + 21.0, rim_y - 4.0), 2)

        # Glossy pearl rising well above the cup so it is always visible.
        pearl_cy = rim_y - 12.0
        pygame.draw.ellipse(surf, _mix(CLAM_RIM, INK, 0.2), (cx - 9, rim_y - 8, 18, 7))
        pygame.draw.circle(surf, (226, 218, 234), (int(cx), int(pearl_cy) + 2), 10)
        pygame.draw.circle(surf, WHITE, (int(cx), int(pearl_cy)), 9)
        pygame.draw.circle(surf, WHITE, (int(cx) - 3, int(pearl_cy) - 4), 3)
        pygame.draw.circle(surf, (255, 240, 250), (int(cx) + 3, int(pearl_cy) + 2), 2)

        # Front cup: scalloped rim across the top, rounded bowl underneath.
        cup: list[tuple[float, float]] = [(cx - cup_half_w, rim_y)]
        bumps = 5
        seg = (2.0 * cup_half_w) / bumps
        for k in range(bumps):
            mid_x = cx - cup_half_w + k * seg + seg / 2.0
            cup.append((mid_x, rim_y - 4.0))
            cup.append((cx - cup_half_w + (k + 1) * seg, rim_y))
        for i in range(1, 13):
            angle = math.pi * i / 12.0
            cup.append((cx + cup_half_w * math.cos(angle), rim_y + cup_depth * math.sin(angle)))
        pygame.draw.polygon(surf, CLAM_SHELL, cup)
        pygame.draw.polygon(surf, CLAM_RIM, cup, 2)
        # Ribs fanning from the bowl base to the rim valleys.
        for k in range(bumps + 1):
            vx = cx - cup_half_w + k * seg
            pygame.draw.line(
                surf,
                _mix(CLAM_RIM, CLAM_SHELL, 0.4),
                (cx, rim_y + cup_depth - 4.0),
                (vx, rim_y + 2.0),
                2,
            )
        self._pearl = surf
        return surf

    def get_small_pearl(self) -> pygame.Surface:
        """Pre-scaled 36 px pearl for the HUD counter (scaled exactly once)."""

        if self._small_pearl is not None:
            return self._small_pearl
        small = pygame.transform.scale(self.get_pearl(), (36, 36))
        small.set_colorkey(COLORKEY)
        self._small_pearl = small
        return small

    def get_starfish(self) -> pygame.Surface:
        if self._starfish is not None:
            return self._starfish
        size = 58
        surf = _colorkey_surface(size, size)
        cx, cy = size // 2, size // 2
        pts = []
        for i in range(10):
            angle = -math.pi / 2 + i * (math.pi / 5)
            r = 25 if i % 2 == 0 else 11
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        pygame.draw.polygon(surf, STAR_GOLD, pts)
        pygame.draw.polygon(surf, STAR_EDGE, pts, 3)
        for i in range(5):
            angle = -math.pi / 2 + i * (2 * math.pi / 5)
            tip = (cx + 17 * math.cos(angle), cy + 17 * math.sin(angle))
            pygame.draw.circle(surf, _mix(STAR_GOLD, WHITE, 0.5), (int(tip[0]), int(tip[1])), 3)
        pygame.draw.circle(surf, STAR_EDGE, (cx - 5, cy - 3), 2)
        pygame.draw.circle(surf, STAR_EDGE, (cx + 5, cy - 3), 2)
        pygame.draw.arc(surf, STAR_EDGE, (cx - 5, cy, 10, 8), math.pi, 2 * math.pi, 2)
        self._starfish = surf
        return surf

    def get_jelly_frames(self) -> tuple[pygame.Surface, ...]:
        """Three gentle pulse frames of the friendly jellyfish."""

        if self._jelly_frames is not None:
            return self._jelly_frames
        frames = []
        for pulse in range(3):
            w, h = 104, 118
            surf = _colorkey_surface(w, h)
            cx = w // 2
            dome_w = 76 + pulse * 6
            dome_h = 52 - pulse * 4
            dome_rect = pygame.Rect(cx - dome_w // 2, 100 - dome_h - 34, dome_w, dome_h * 2)
            rim = _mix(JELLY_BODY, INK, 0.30)
            pygame.draw.ellipse(surf, JELLY_BODY, dome_rect)
            pygame.draw.ellipse(surf, rim, dome_rect, 3)
            glow_rect = dome_rect.inflate(-20, -22)
            pygame.draw.ellipse(surf, JELLY_LIGHT, glow_rect)
            # Scalloped skirt.
            for dx in range(-dome_w // 2 + 6, dome_w // 2 - 4, 12):
                pygame.draw.circle(surf, JELLY_BODY, (cx + dx, 100 - 34), 8)
                pygame.draw.circle(surf, rim, (cx + dx, 100 - 34), 8, 2)
            pygame.draw.ellipse(surf, JELLY_BODY, (cx - dome_w // 2, 100 - 40, dome_w, 16))
            # Tentacles sway slightly per frame.
            for i, tx in enumerate((-24, -8, 8, 24)):
                points = [(cx + tx, 100 - 28)]
                for seg in range(1, 4):
                    offset = int(math.sin(pulse * 2.1 + i * 0.8 + seg) * 6)
                    points.append((cx + tx + offset, 100 - 28 + seg * 17))
                pygame.draw.lines(surf, JELLY_TENTACLE, False, points, 4)
            # Sleepy happy face on the dome.
            eye_y = dome_rect.y + int(dome_h * 0.9)
            pygame.draw.arc(surf, INK, (cx - 16, eye_y, 10, 8), math.pi, 2 * math.pi, 2)
            pygame.draw.arc(surf, INK, (cx + 6, eye_y, 10, 8), math.pi, 2 * math.pi, 2)
            blush = _mix(JELLY_LIGHT, (255, 120, 160), 0.55)
            pygame.draw.circle(surf, blush, (cx - 20, eye_y + 7), 4)
            pygame.draw.circle(surf, blush, (cx + 20, eye_y + 7), 4)
            pygame.draw.arc(surf, INK, (cx - 4, eye_y + 5, 8, 6), math.pi * 1.1, math.pi * 1.9, 2)
            frames.append(surf)
        self._jelly_frames = tuple(frames)
        return self._jelly_frames

    # -------------------------------------------------------------- scenery

    def get_kelp_strip(self, height: int) -> pygame.Surface:
        cached = self._kelp_strips.get(height)
        if cached is not None:
            return cached
        width = 84
        surf = _colorkey_surface(width, height)
        cx = width // 2
        segments = max(3, height // 44)
        for seg in range(segments):
            t = seg / float(segments)
            y_base = height - seg * (height // segments)
            leaf_h = height // segments
            sway = int(math.sin(t * math.pi * 2.2) * 10)
            rect = pygame.Rect(cx - 9 + sway, y_base - leaf_h, 18, leaf_h + 4)
            pygame.draw.ellipse(surf, KELP_MAIN, rect)
            pygame.draw.ellipse(surf, KELP_DARK, rect, 2)
            left = pygame.Rect(cx - 30 + sway, y_base - leaf_h + 6, 26, 14)
            right = pygame.Rect(cx + 4 + sway, y_base - leaf_h + 14, 26, 14)
            pygame.draw.ellipse(surf, _mix(KELP_MAIN, WHITE, 0.18), left)
            pygame.draw.ellipse(surf, _mix(KELP_MAIN, KELP_DARK, 0.35), right)
        self._kelp_strips[height] = surf
        return surf

    def get_coral(self) -> pygame.Surface:
        if self._coral is not None:
            return self._coral
        w, h = 150, 112
        surf = _colorkey_surface(w, h)
        base_y = h - 10
        # Trunk plus rounded branches.
        pygame.draw.line(surf, CORAL_MAIN, (w // 2, base_y), (w // 2, 44), 14)
        pygame.draw.line(surf, CORAL_DARK, (w // 2, base_y), (w // 2, 44), 4)
        branches = (((w // 2, 52), (w // 2 - 34, 26)), ((w // 2, 52), (w // 2 + 36, 22)), ((w // 2 - 34, 26), (w // 2 - 48, 40)))
        for start, end in branches:
            pygame.draw.line(surf, CORAL_MAIN, start, end, 10)
            pygame.draw.line(surf, _mix(CORAL_MAIN, WHITE, 0.25), start, end, 3)
        for bx, by in ((w // 2 - 48, 40), (w // 2 - 34, 26), (w // 2 + 36, 22), (w // 2, 44)):
            pygame.draw.circle(surf, CORAL_MAIN, (bx, by), 9)
            pygame.draw.circle(surf, _mix(CORAL_MAIN, WHITE, 0.4), (bx - 2, by - 2), 3)
        self._coral = surf
        return surf

    def get_landmark(self, kind: str) -> pygame.Surface:
        """Big decorative gate objects at chapter boundaries / finish."""

        cached = self._landmarks.get(kind)
        if cached is not None:
            return cached
        if kind == "arch_coral":
            w, h = 360, 330
            surf = _colorkey_surface(w, h)
            base = h - 16
            pygame.draw.rect(surf, CORAL_MAIN, (w // 2 - 26, base - 200, 52, 200), border_radius=24)
            pygame.draw.rect(surf, CORAL_DARK, (w // 2 - 26, base - 200, 52, 200), 4, border_radius=24)
            # Arc bounding box stays fully inside the canvas (no top clipping).
            pygame.draw.arc(surf, CORAL_MAIN, (w // 2 - 150, base - 296, 300, 216), 0, math.pi, 34)
            pygame.draw.arc(surf, _mix(CORAL_MAIN, WHITE, 0.3), (w // 2 - 142, base - 288, 284, 200), 0, math.pi, 8)
            for bx, by in ((w // 2 - 150, base - 190), (w // 2 + 150, base - 190)):
                for r, col in ((26, CORAL_MAIN), (14, _mix(CORAL_MAIN, WHITE, 0.35))):
                    pygame.draw.circle(surf, col, (bx, by), r)
            pygame.draw.ellipse(surf, SAND, (w // 2 - 170, base - 26, 340, 40))
        elif kind == "arch_kelp":
            w, h = 380, 320
            surf = _colorkey_surface(w, h)
            base = h - 16
            for side, sign in (("l", -1), ("r", 1)):
                kelp = self.get_kelp_strip(230)
                surf.blit(kelp, (w // 2 + sign * 120 - 42, base - 230))
                pygame.draw.rect(
                    surf,
                    KELP_DARK,
                    (w // 2 + sign * 120 - 30, base - 240, 60, 240),
                    10,
                    border_radius=30,
                )
            pygame.draw.arc(surf, KELP_MAIN, (w // 2 - 160, base - 290, 320, 240), 0, math.pi, 26)
            for dx in (-120, -60, 0, 60, 120):
                pygame.draw.circle(surf, _mix(KELP_MAIN, WHITE, 0.3), (w // 2 + dx, base - 168), 10)
            pygame.draw.ellipse(surf, SAND, (w // 2 - 175, base - 24, 350, 40))
        else:  # reef_gold finish
            w, h = 400, 330
            surf = _colorkey_surface(w, h)
            base = h - 16
            # Rocky reef mound.
            pygame.draw.polygon(
                surf,
                _mix(SEA_DEEP, SAND, 0.55),
                [(30, base), (120, base - 130), (210, base - 60), (300, base - 150), (370, base)],
            )
            pygame.draw.polygon(
                surf,
                _mix(GOLD_REEF, SAND, 0.35),
                [(30, base), (120, base - 130), (210, base - 60), (300, base - 150), (370, base)],
                6,
            )
            # Golden star beacon on the tallest spire.
            star_pts = []
            scx, scy = 300, base - 178
            for i in range(10):
                ang = -math.pi / 2 + i * (math.pi / 5)
                r = 34 if i % 2 == 0 else 15
                star_pts.append((scx + r * math.cos(ang), scy + r * math.sin(ang)))
            pygame.draw.polygon(surf, GOLD_REEF, star_pts)
            pygame.draw.polygon(surf, STAR_EDGE, star_pts, 3)
            pygame.draw.circle(surf, WHITE, (scx - 6, scy - 6), 7)
            pygame.draw.ellipse(surf, SAND, (10, base - 22, 380, 40))
            for bx in (90, 200, 320):
                pygame.draw.circle(surf, _mix(GOLD_REEF, WHITE, 0.5), (bx, base - 30), 6)
            landmark = surf
            self._landmarks[kind] = landmark
            return landmark
        self._landmarks[kind] = surf
        return surf

    # -------------------------------------------------------------- dolphin

    def get_dolphin_frame(self, pose: int, tail_step: int) -> pygame.Surface:
        """Cached dolphin sprite for pose (-1 up, 0 level, 1 down) × tail beat."""

        key = (pose, tail_step)
        cached = self._dolphin_poses.get(key)
        if cached is not None:
            return cached
        level = self._build_level_dolphin(tail_step)
        if pose == 0:
            frame = level
        else:
            # Pygame rotates counter-clockwise for positive angles; the sprite
            # faces right, so climbing water pitches the nose UP (+) and a
            # dive pitches the nose DOWN (-).
            angle = 16 if pose < 0 else -14
            frame = pygame.transform.rotate(level, angle)
            frame.set_colorkey(COLORKEY)
        if len(self._dolphin_poses) > 12:
            self._dolphin_poses.clear()
        self._dolphin_poses[key] = frame
        return frame

    def get_flip_frame(self, step: int) -> pygame.Surface:
        """Pre-rotated breach somersault frame (backflip, tail swings over)."""

        key = step % FLIP_STEPS
        cached = self._flip_frames.get(key)
        if cached is not None:
            return cached
        base = self._build_level_dolphin(1)
        if key == 0:
            frame = base
        else:
            # Owner-reviewed direction: the somersault swings the tail over
            # first, which is counter-clockwise on screen (positive angles).
            frame = pygame.transform.rotate(base, 360.0 * key / float(FLIP_STEPS))
            frame.set_colorkey(COLORKEY)
        self._flip_frames[key] = frame
        return frame

    def _build_level_dolphin(self, tail_step: int) -> pygame.Surface:
        """Draw one level-pose dolphin frame from a single smooth silhouette.

        The body reads sleek and dolphin-like: deep rounded melon flowing into
        a short blunt beak (never a marlin point), chest-deepest trunk tapering
        to a slim peduncle, small falcate dorsal fin and a broad two-lobed
        fluke whose sweep carries the whole tail-beat animation.
        """

        w, h = 240, 150
        surf = _colorkey_surface(w, h)
        cx, cy = 120.0, 80.0
        td = (12, 4, -9, 0)[tail_step]

        def pt(x: float, y: float, f: float = 0.0) -> tuple[float, float]:
            """Map design space to canvas space; ``f`` scales the tail sweep."""

            return (cx + x, cy + y + td * f)

        # Single closed silhouette: beak tip → melon → back → fluke → belly.
        outline_design: list[tuple[float, float, float]] = [
            (108, 2, 0.0),     # blunt rounded beak tip
            (92, -6, 0.0),     # smile crease where beak meets melon
            (80, -14, 0.0),    # round melon front
            (62, -20, 0.0),
            (44, -23, 0.0),    # blowhole plateau
            (16, -24, 0.0),    # back
            (-16, -21, 0.0),
            (-44, -14, 0.0),   # rear taper
            (-68, -6, 0.0),    # peduncle top
            (-96, -18, 1.0),   # fluke upper tip
            (-86, 0, 0.35),    # fluke notch
            (-100, 16, 1.0),   # fluke lower tip
            (-72, 6, 0.3),     # peduncle underside
            (-50, 12, 0.15),
            (-26, 19, 0.0),    # belly
            (2, 24, 0.0),
            (30, 27, 0.0),
            (54, 28, 0.0),     # deepest under the chest
            (74, 24, 0.0),
            (88, 16, 0.0),     # jaw curve
            (102, 9, 0.0),     # beak underside
        ]
        points = [pt(x, y, f) for x, y, f in outline_design]
        pygame.draw.polygon(surf, DOLPHIN_MID, points)
        pygame.draw.polygon(surf, DOLPHIN_EDGE, points, 3)

        # Darker cape along the back (classic dolphin two-tone), kept inside
        # the silhouette so no seams show against the outline.
        cape_design: list[tuple[float, float]] = [
            (96, 0), (78, -8), (56, -15), (30, -20), (2, -22),
            (-24, -19), (-46, -13), (-64, -6), (-70, -3), (-48, -4),
            (-20, -9), (8, -13), (44, -12), (72, -4), (92, 3),
        ]
        pygame.draw.polygon(surf, DOLPHIN_TOP, [pt(x, y) for x, y in cape_design])

        # Small curved (falcate) dorsal fin swept slightly backwards.
        dorsal = [(8, -22), (18, -42), (28, -37), (38, -26), (42, -21)]
        pygame.draw.polygon(surf, DOLPHIN_TOP, [pt(x, y) for x, y in dorsal])
        pygame.draw.polygon(surf, DOLPHIN_EDGE, [pt(x, y) for x, y in dorsal], 3)
        seam = [(4, -22), (44, -20), (40, -15), (8, -16)]
        pygame.draw.polygon(surf, DOLPHIN_TOP, [pt(x, y) for x, y in seam])

        # Light belly patch along the lower body.
        belly = [
            (-46, 11), (-20, 18), (8, 23), (36, 26), (60, 26),
            (76, 20), (58, 12), (20, 9), (-16, 5),
        ]
        pygame.draw.polygon(surf, DOLPHIN_BELLY, [pt(x, y) for x, y in belly])

        # Rounded pectoral flipper below the body.
        fin = [(16, 16), (4, 36), (20, 39), (36, 22)]
        pygame.draw.polygon(surf, DOLPHIN_TOP, [pt(x, y) for x, y in fin])
        pygame.draw.polygon(surf, DOLPHIN_EDGE, [pt(x, y) for x, y in fin], 2)

        # Face: big friendly eye with double glint, rosy cheek, short smile
        # sweeping back from the beak, tiny blowhole cue on the plateau.
        eye_c = pt(74, -6)
        pygame.draw.ellipse(surf, INK, (eye_c[0] - 9, eye_c[1] - 10, 18, 21))
        pygame.draw.circle(surf, WHITE, (int(eye_c[0]) - 3, int(eye_c[1]) - 5), 5)
        pygame.draw.circle(surf, WHITE, (int(eye_c[0]) + 4, int(eye_c[1]) + 3), 2)
        cheek_c = pt(87, 6)
        pygame.draw.ellipse(surf, (250, 168, 186), (cheek_c[0] - 7, cheek_c[1] - 4, 14, 9))
        mouth = [pt(106, 6), pt(94, 10), pt(82, 11)]
        pygame.draw.lines(surf, DOLPHIN_EDGE, False, mouth, 2)
        bh1, bh2 = pt(40, -23), pt(48, -24)
        pygame.draw.line(surf, DOLPHIN_EDGE, bh1, bh2, 3)
        return surf

    def pose_for_motion(self, vertical_velocity: float, airborne: bool) -> int:
        """Pick a cached pose bucket from vertical motion."""

        threshold_up = -70.0
        threshold_down = 90.0
        if airborne or vertical_velocity < threshold_down:
            if vertical_velocity < threshold_up:
                return -1
            if vertical_velocity > threshold_down:
                return 1
            return 0
        return 0

    # ------------------------------------------------------------ particles

    def get_particle(self, kind: str, size_bucket: int, color: tuple[int, int, int]) -> pygame.Surface:
        key = (kind, size_bucket, color)
        cached = self._particle_cache.get(key)
        if cached is not None:
            return cached
        s = max(6, min(28, size_bucket))
        surf = _colorkey_surface(s, s)
        cx = cy = s // 2
        r = s // 2
        if kind == "sparkle":
            pts = []
            for i in range(8):
                ang = -math.pi / 2 + i * (math.pi / 4)
                pr = r if i % 2 == 0 else max(2, r // 3)
                pts.append((cx + pr * math.cos(ang), cy + pr * math.sin(ang)))
            pygame.draw.polygon(surf, color, pts)
        elif kind == "splash":
            pygame.draw.circle(surf, color, (cx, cy), max(2, r - 1))
            pygame.draw.circle(surf, WHITE, (cx - max(1, r // 3), cy - max(1, r // 3)), max(2, r // 2))
        else:  # confetti / generic dot
            pygame.draw.circle(surf, color, (cx, cy), max(2, r - 2))
            pygame.draw.circle(surf, WHITE, (cx - 2, cy - 2), max(1, r // 4))
        self._particle_cache[key] = surf
        return surf

    # ------------------------------------------------------------------ HUD

    def get_progress_bar(self) -> pygame.Surface:
        """Pre-rendered chapter progress bar with three landmark pips."""

        if self._hud_bar is not None:
            return self._hud_bar
        w, h = 396, 40
        surf = _colorkey_surface(w, h)
        track = pygame.Rect(6, 14, w - 12, 12)
        pygame.draw.rect(surf, (255, 252, 244), track, border_radius=8)
        pygame.draw.rect(surf, (240, 200, 90), track, 3, border_radius=8)
        pip_positions = (w // 3, 2 * w // 3, w - 22)
        pip_colors = (CORAL_MAIN, KELP_MAIN, STAR_EDGE)
        for px, pc in zip(pip_positions, pip_colors):
            pygame.draw.circle(surf, pc, (px, 20), 8)
            pygame.draw.circle(surf, WHITE, (px - 2, 18), 3)
        self._hud_bar = surf
        return surf

    def get_marker(self) -> pygame.Surface:
        if self._marker is not None:
            return self._marker
        surf = _colorkey_surface(26, 26)
        pygame.draw.polygon(surf, DOLPHIN_TOP, [(4, 20), (22, 13), (4, 6)])
        pygame.draw.polygon(surf, DOLPHIN_EDGE, [(4, 20), (22, 13), (4, 6)], 2)
        self._marker = surf
        return surf

    def get_tito_portrait(self, size: int = 56) -> pygame.Surface:
        """Canonical Tito portrait via the shared visual catalogue, fail-soft."""

        if self._tito is not None:
            return self._tito
        loaded: pygame.Surface | None = None
        try:
            from greia_platform.activity_api import get_shared_visual_path

            path = get_shared_visual_path("character.tito", variant="happy")
            raw = pygame.image.load(str(path))
            loaded = pygame.transform.smoothscale(raw.convert_alpha(), (size, size))
        except Exception:
            loaded = None
        if loaded is None:
            # Static private fallback so the presenter affordance still reads.
            loaded = _colorkey_surface(size, size)
            pygame.draw.circle(loaded, (232, 140, 58), (size // 2, size // 2), size // 2 - 2)
            pygame.draw.circle(loaded, WHITE, (size // 2 - 8, size // 2 - 6), 6)
            pygame.draw.circle(loaded, WHITE, (size // 2 + 8, size // 2 - 6), 6)
            pygame.draw.circle(loaded, INK, (size // 2 - 7, size // 2 - 5), 3)
            pygame.draw.circle(loaded, INK, (size // 2 + 9, size // 2 - 5), 3)
        self._tito = loaded
        return loaded
