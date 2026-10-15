"""High-contrast storybook graphics renderer and HUD for Colline Allegre."""

from __future__ import annotations

import math
import random
from typing import Final

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .colline_content import (
        CHASSIS_HEIGHT,
        CHASSIS_WIDTH,
        PIXELS_PER_METER,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SYSTEM_CHROME_SAFE_X,
        SYSTEM_CHROME_SAFE_Y,
        WHEEL_RADIUS,
        WHEELBASE,
    )
    from .colline_model import CollineWorld, Vehicle
else:
    from colline_content import (
        CHASSIS_HEIGHT,
        CHASSIS_WIDTH,
        PIXELS_PER_METER,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SYSTEM_CHROME_SAFE_X,
        SYSTEM_CHROME_SAFE_Y,
        WHEEL_RADIUS,
        WHEELBASE,
    )
    from colline_model import CollineWorld, Vehicle

# Visual Palette
SKY_TOP: Final[tuple[int, int, int]] = (120, 195, 245)
SKY_BOTTOM: Final[tuple[int, int, int]] = (215, 240, 255)
HILLS_DISTANT: Final[tuple[int, int, int]] = (145, 210, 160)
HILLS_MID: Final[tuple[int, int, int]] = (105, 185, 115)
GRASS_TOP: Final[tuple[int, int, int]] = (80, 195, 60)
GRASS_EDGE: Final[tuple[int, int, int]] = (55, 160, 40)
EARTH_FILL: Final[tuple[int, int, int]] = (130, 90, 55)
BRIDGE_PLANK: Final[tuple[int, int, int]] = (185, 135, 75)
MUD_COLOR: Final[tuple[int, int, int]] = (95, 55, 30)
WHITE: Final[tuple[int, int, int]] = (255, 255, 255)
GOLD: Final[tuple[int, int, int]] = (255, 215, 35)
GOLD_DARK: Final[tuple[int, int, int]] = (225, 160, 20)
CHERRY_RED: Final[tuple[int, int, int]] = (235, 50, 50)
BEAR_BROWN: Final[tuple[int, int, int]] = (165, 105, 55)
BEAR_TAN: Final[tuple[int, int, int]] = (235, 185, 140)


class ConfettiParticle:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.vx = random.uniform(-160.0, 160.0)
        self.vy = random.uniform(-280.0, -80.0)
        self.color = random.choice([
            (255, 80, 80),
            (255, 220, 50),
            (80, 210, 255),
            (120, 240, 100),
            (255, 140, 220),
        ])
        self.size = random.uniform(5.0, 9.0)
        self.life = 1.0
        self.decay = random.uniform(0.7, 1.2)

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 320.0 * dt
        self.life -= self.decay * dt
        return self.life > 0.0


class DustParticle:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.vx = random.uniform(-60.0, -10.0)
        self.vy = random.uniform(-30.0, 10.0)
        self.radius = random.uniform(4.0, 8.0)
        self.life = 1.0

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.radius += 8.0 * dt
        self.life -= 1.8 * dt
        return self.life > 0.0


class CollineRenderer:
    """Hardware-friendly cached storybook renderer for Colline Allegre."""

    def __init__(
        self,
        typography: GreiaTypography,
        resources: LocalizedResources | None = None,
    ) -> None:
        self._typography = typography
        # Child-visible copy is resolved once from the Activity locale
        # bundles (``resources.text`` applies the child letter-case policy).
        # Without resources only the pictograms remain: no fixed-language
        # fallback sentence is ever drawn.
        self._copy: dict[str, str] = {
            key: resources.text(key) if resources else ""
            for key in ("ui.go", "ui.brake", "ui.perfect_landing", "ui.boing")
        }
        self._text_cache: dict[tuple, pygame.Surface] = {}
        self._sky_surface: pygame.Surface | None = None
        self._confetti: list[ConfettiParticle] = []
        self._dust: list[DustParticle] = []
        self.gas_pressed = False
        self.brake_pressed = False

        # Touch Pedal geometry
        self.gas_pedal_rect = pygame.Rect(REFERENCE_WIDTH - 130, REFERENCE_HEIGHT - 120, 100, 100)
        self.brake_pedal_rect = pygame.Rect(140, REFERENCE_HEIGHT - 120, 92, 92)

    def _render_cached_text(
        self,
        text: str,
        role: FontRole,
        size: int,
        color: tuple[int, int, int],
        max_width: int | None = None,
    ) -> pygame.Surface:
        key = (text, role.name, size, color, max_width)
        cached = self._text_cache.get(key)
        if cached is not None:
            return cached
        fitted = size
        if max_width is not None:
            while fitted > 10 and self._typography.measure(text, role, fitted).width > max_width:
                fitted -= 1
        surf = self._typography.render(text, role, fitted, color)
        if len(self._text_cache) > 200:
            self._text_cache.clear()
        self._text_cache[key] = surf
        return surf

    def _get_sky(self) -> pygame.Surface:
        if self._sky_surface is not None:
            return self._sky_surface
        surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        for y in range(REFERENCE_HEIGHT):
            t = y / float(REFERENCE_HEIGHT)
            r = int(SKY_TOP[0] * (1.0 - t) + SKY_BOTTOM[0] * t)
            g = int(SKY_TOP[1] * (1.0 - t) + SKY_BOTTOM[1] * t)
            b = int(SKY_TOP[2] * (1.0 - t) + SKY_BOTTOM[2] * t)
            pygame.draw.line(surf, (r, g, b), (0, y), (REFERENCE_WIDTH, y))
        self._sky_surface = surf
        return surf

    def emit_confetti(self, x: float, y: float, count: int = 35) -> None:
        for _ in range(count):
            self._confetti.append(ConfettiParticle(x, y))

    def update_particles(self, dt: float) -> None:
        self._confetti = [p for p in self._confetti if p.update(dt)]
        self._dust = [d for d in self._dust if d.update(dt)]

    def render(self, surface: pygame.Surface, world: CollineWorld, dt: float) -> None:
        self.update_particles(dt)

        cam_x = world.vehicle.x - 260.0
        cam_y = 0.0

        # 1. Sky Background
        surface.blit(self._get_sky(), (0, 0))

        # 2. Distant Parallax Clouds
        self._draw_clouds(surface, cam_x)

        # 3. Distant Mountains/Hills (Parallax 0.25)
        self._draw_distant_hills(surface, cam_x)

        # 4. Midground Rolling Hills (Parallax 0.5)
        self._draw_midground_hills(surface, cam_x)

        # 5. Active Foreground Terrain & Hazards/Bridges
        self._draw_foreground_terrain(surface, world, cam_x)

        # 6. Collectibles (Stars, Gears, Balloons)
        self._draw_collectibles(surface, world, cam_x)

        # 7. Dust Particles
        for d in self._dust:
            sx = int(d.x - cam_x)
            sy = int(d.y - cam_y)
            if 0 <= sx <= REFERENCE_WIDTH:
                alpha = int(max(0.0, d.life) * 160)
                dust_surf = pygame.Surface((int(d.radius * 2), int(d.radius * 2)), pygame.SRCALPHA)
                pygame.draw.circle(dust_surf, (220, 200, 180, alpha), (int(d.radius), int(d.radius)), int(d.radius))
                surface.blit(dust_surf, (sx - int(d.radius), sy - int(d.radius)))

        # 8. Tito's Buggy & Character
        self._draw_vehicle(surface, world.vehicle, cam_x)

        # 9. Confetti Particles
        for p in self._confetti:
            sx = int(p.x - cam_x)
            sy = int(p.y - cam_y)
            if 0 <= sx <= REFERENCE_WIDTH and 0 <= sy <= REFERENCE_HEIGHT:
                pygame.draw.rect(surface, p.color, (sx, sy, int(p.size), int(p.size)))

        # 10. Floating Perfect Landing / Boing Banners
        self._draw_floating_cues(surface, world.vehicle, cam_x)

        # 11. HUD & Pedals (Respecting Top-Left System Chrome Clearance!)
        self._draw_hud(surface, world)
        self._draw_pedals(surface)

    def _draw_clouds(self, surface: pygame.Surface, cam_x: float) -> None:
        cloud_color = (255, 255, 255, 200)
        cloud_surf = pygame.Surface((REFERENCE_WIDTH, 140), pygame.SRCALPHA)
        cloud_data = [(100, 45, 30), (140, 35, 36), (180, 48, 28), (420, 60, 32), (460, 52, 40), (820, 40, 34)]
        for cx, cy, cr in cloud_data:
            sx = int(cx - cam_x * 0.12) % (REFERENCE_WIDTH + 200) - 100
            pygame.draw.circle(cloud_surf, cloud_color, (sx, cy), cr)
            pygame.draw.circle(cloud_surf, cloud_color, (sx + 26, cy + 5), cr - 6)
            pygame.draw.circle(cloud_surf, cloud_color, (sx - 24, cy + 6), cr - 8)
        surface.blit(cloud_surf, (0, 0))

    def _draw_distant_hills(self, surface: pygame.Surface, cam_x: float) -> None:
        pts = [(0, REFERENCE_HEIGHT)]
        for x in range(0, REFERENCE_WIDTH + 20, 20):
            world_x = x + cam_x * 0.25
            y = 380.0 + math.sin(world_x / 320.0) * 45.0 + math.cos(world_x / 600.0) * 25.0
            pts.append((x, int(y)))
        pts.append((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        pygame.draw.polygon(surface, HILLS_DISTANT, pts)

    def _draw_midground_hills(self, surface: pygame.Surface, cam_x: float) -> None:
        pts = [(0, REFERENCE_HEIGHT)]
        for x in range(0, REFERENCE_WIDTH + 16, 16):
            world_x = x + cam_x * 0.5
            y = 410.0 + math.sin(world_x / 240.0) * 40.0 + math.cos(world_x / 450.0) * 20.0
            pts.append((x, int(y)))
        pts.append((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        pygame.draw.polygon(surface, HILLS_MID, pts)

    def _draw_foreground_terrain(self, surface: pygame.Surface, world: CollineWorld, cam_x: float) -> None:
        # Build polygon for on-screen slice of terrain
        step = 12
        left_world = cam_x - 20
        right_world = cam_x + REFERENCE_WIDTH + 20

        poly_pts: list[tuple[int, int]] = []
        grass_line: list[tuple[int, int]] = []

        curr_x = left_world
        while curr_x <= right_world:
            sx = int(curr_x - cam_x)
            sy = int(world.terrain.get_height(curr_x))
            poly_pts.append((sx, sy))
            grass_line.append((sx, sy))
            curr_x += step

        # Close polygon at bottom
        poly_pts.append((REFERENCE_WIDTH + 20, REFERENCE_HEIGHT))
        poly_pts.append((-20, REFERENCE_HEIGHT))

        # Fill soil
        pygame.draw.polygon(surface, EARTH_FILL, poly_pts)

        # Draw thick grassy ridge line
        if len(grass_line) >= 2:
            pygame.draw.lines(surface, GRASS_TOP, False, grass_line, 8)
            pygame.draw.lines(surface, GRASS_EDGE, False, grass_line, 2)

        # Draw Bridges, Mud, and Mushrooms
        for x in range(int(left_world), int(right_world), 24):
            kind = world.terrain.get_surface_kind(float(x))
            sx = int(x - cam_x)
            sy = int(world.terrain.get_height(float(x)))

            if kind == "bridge":
                # Wooden plank
                pygame.draw.rect(surface, BRIDGE_PLANK, (sx - 10, sy - 4, 20, 10), border_radius=2)
                pygame.draw.circle(surface, (60, 40, 20), (sx - 6, sy), 2)
                pygame.draw.circle(surface, (60, 40, 20), (sx + 6, sy), 2)
            elif kind == "mud":
                # Mud splash puddle
                pygame.draw.ellipse(surface, MUD_COLOR, (sx - 14, sy - 2, 28, 8))
            elif kind == "mushroom" and abs(x % 100) < 25:
                # Bouncy red mushroom
                # Stalk
                pygame.draw.rect(surface, (240, 235, 220), (sx - 5, sy - 18, 10, 18), border_radius=3)
                # Cap
                pygame.draw.ellipse(surface, (230, 40, 40), (sx - 16, sy - 30, 32, 18))
                # Polka dots
                pygame.draw.circle(surface, WHITE, (sx - 6, sy - 23), 3)
                pygame.draw.circle(surface, WHITE, (sx + 6, sy - 23), 3)
                pygame.draw.circle(surface, WHITE, (sx, sy - 26), 2)

    def _draw_collectibles(self, surface: pygame.Surface, world: CollineWorld, cam_x: float) -> None:
        for c in world.collectibles:
            if c.collected:
                continue
            sx = int(c.x - cam_x)
            sy = int(c.y)
            if -30 <= sx <= REFERENCE_WIDTH + 30:
                if c.kind == "star":
                    # Shiny rotating golden star
                    self._draw_star(surface, sx, sy, 18, GOLD, GOLD_DARK)
                elif c.kind == "gear":
                    # Golden cog
                    pygame.draw.circle(surface, GOLD_DARK, (sx, sy), 15)
                    pygame.draw.circle(surface, GOLD, (sx, sy), 12)
                    pygame.draw.circle(surface, EARTH_FILL, (sx, sy), 5)
                elif c.kind == "balloon":
                    # Cheerful floating balloon
                    pygame.draw.ellipse(surface, (255, 90, 120), (sx - 12, sy - 16, 24, 30))
                    pygame.draw.line(surface, WHITE, (sx, sy + 14), (sx, sy + 28), 2)

    def _draw_star(
        self, surface: pygame.Surface, cx: int, cy: int, r: int, fill: tuple[int, int, int], outline: tuple[int, int, int]
    ) -> None:
        pts = []
        for i in range(10):
            ang = i * math.pi / 5.0 - math.pi / 2.0
            rad = r if i % 2 == 0 else int(r * 0.45)
            pts.append((cx + int(math.cos(ang) * rad), cy + int(math.sin(ang) * rad)))
        pygame.draw.polygon(surface, fill, pts)
        pygame.draw.polygon(surface, outline, pts, 2)

    def _draw_vehicle(self, surface: pygame.Surface, veh: Vehicle, cam_x: float) -> None:
        sx = int(veh.x - cam_x)
        sy = int(veh.y)
        angle = veh.angle
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        def to_screen(lx: float, ly: float) -> tuple[int, int]:
            return int(sx + lx * cos_a - ly * sin_a), int(sy + lx * sin_a + ly * cos_a)

        # 1. Exhaust puffs when driving
        if veh.vx > 80.0 and random.random() < 0.3:
            rx, ry = to_screen(-CHASSIS_WIDTH / 2.0 - 10.0, 12.0)
            self._dust.append(DustParticle(rx + cam_x, ry))

        # 2. Suspension Struts
        for w in [veh.rear_wheel, veh.front_wheel]:
            mx, my = to_screen(w.rel_x, 14.0)
            hx = int(w.hub_x - cam_x)
            hy = int(w.hub_y)
            # Coil spring
            pygame.draw.line(surface, (100, 105, 115), (mx, my), (hx, hy), 6)
            pygame.draw.line(surface, (220, 220, 230), (mx, my), (hx, hy), 2)

        # 3. Chunky Wheels
        for w in [veh.rear_wheel, veh.front_wheel]:
            hx = int(w.hub_x - cam_x)
            hy = int(w.hub_y)
            # Tire
            pygame.draw.circle(surface, (40, 42, 45), (hx, hy), int(WHEEL_RADIUS))
            # Tread ridges
            for ang_deg in range(0, 360, 40):
                rad = math.radians(ang_deg + (veh.x * 0.2))
                tx = hx + int(math.cos(rad) * (WHEEL_RADIUS - 2))
                ty = hy + int(math.sin(rad) * (WHEEL_RADIUS - 2))
                ix = hx + int(math.cos(rad) * (WHEEL_RADIUS - 6))
                iy = hy + int(math.sin(rad) * (WHEEL_RADIUS - 6))
                pygame.draw.line(surface, (70, 72, 75), (tx, ty), (ix, iy), 3)
            # Rim (Cream White)
            pygame.draw.circle(surface, (245, 245, 235), (hx, hy), 12)
            # Hub center nut (Golden)
            pygame.draw.circle(surface, GOLD, (hx, hy), 5)

        # 4. Comical Boxing Glove on Accordion Spring (if flipping or bounce active)
        if veh.bounce_active:
            # Giant red boxing glove popping out from chassis underside!
            prog = min(1.0, veh.bounce_timer / 0.4)
            extension = math.sin(prog * math.pi) * 65.0
            bx, by = to_screen(0.0, 16.0 + extension)
            # Accordion yellow spring
            prev_pt = to_screen(0.0, 16.0)
            for step in range(1, 6):
                zig = 14 if step % 2 == 1 else -14
                seg_pt = to_screen(zig, 16.0 + (extension * step / 5.0))
                pygame.draw.line(surface, GOLD, prev_pt, seg_pt, 4)
                prev_pt = seg_pt
            # Red boxing glove
            pygame.draw.circle(surface, (240, 30, 30), (bx, by), 24)
            pygame.draw.ellipse(surface, (210, 20, 20), (bx - 10, by - 8, 20, 14))

        # 5. Tito Bear inside cockpit
        # Bear head & cap
        head_pos = to_screen(-6.0, -22.0)
        hx, hy = head_pos
        # Bear head
        pygame.draw.circle(surface, BEAR_BROWN, (hx, hy), 16)
        # Bear ears
        e1 = to_screen(-18.0, -32.0)
        e2 = to_screen(6.0, -32.0)
        pygame.draw.circle(surface, BEAR_BROWN, e1, 6)
        pygame.draw.circle(surface, BEAR_BROWN, e2, 6)
        pygame.draw.circle(surface, BEAR_TAN, e1, 3)
        pygame.draw.circle(surface, BEAR_TAN, e2, 3)
        # Explorer Cap & Cyan Goggles
        pygame.draw.circle(surface, (235, 100, 40), (hx, hy - 8), 14)
        gog1 = to_screen(-8.0, -22.0)
        gog2 = to_screen(2.0, -22.0)
        pygame.draw.circle(surface, (80, 200, 240), gog1, 5)
        pygame.draw.circle(surface, (80, 200, 240), gog2, 5)
        pygame.draw.circle(surface, (40, 40, 40), gog1, 5, 1)
        pygame.draw.circle(surface, (40, 40, 40), gog2, 5, 1)
        # Muzzle & Nose
        muz = to_screen(-2.0, -16.0)
        pygame.draw.circle(surface, BEAR_TAN, muz, 6)
        pygame.draw.circle(surface, (40, 25, 20), muz, 2)
        # Cheerful waving paw
        paw = to_screen(22.0, -26.0)
        pygame.draw.circle(surface, BEAR_BROWN, paw, 6)

        # 6. Buggy Wooden Chassis (Cherry Red with golden racing stripe)
        p1 = to_screen(-CHASSIS_WIDTH / 2.0, 14.0)
        p2 = to_screen(-CHASSIS_WIDTH / 2.0 + 4.0, -8.0)
        p3 = to_screen(-16.0, -18.0)
        p4 = to_screen(24.0, -18.0)
        p5 = to_screen(CHASSIS_WIDTH / 2.0 - 4.0, -4.0)
        p6 = to_screen(CHASSIS_WIDTH / 2.0, 14.0)

        pygame.draw.polygon(surface, CHERRY_RED, [p1, p2, p3, p4, p5, p6])
        pygame.draw.polygon(surface, (180, 30, 30), [p1, p2, p3, p4, p5, p6], 3)

        # Yellow racing stripe
        s1 = to_screen(-CHASSIS_WIDTH / 2.0 + 4.0, 2.0)
        s2 = to_screen(CHASSIS_WIDTH / 2.0 - 4.0, 2.0)
        s3 = to_screen(CHASSIS_WIDTH / 2.0 - 4.0, 8.0)
        s4 = to_screen(-CHASSIS_WIDTH / 2.0 + 4.0, 8.0)
        pygame.draw.polygon(surface, GOLD, [s1, s2, s3, s4])

        # Windshield
        w1 = to_screen(8.0, -18.0)
        w2 = to_screen(16.0, -32.0)
        w3 = to_screen(26.0, -18.0)
        pygame.draw.polygon(surface, (190, 235, 255), [w1, w2, w3])
        pygame.draw.polygon(surface, (120, 180, 220), [w1, w2, w3], 2)

        # Headlight
        hl = to_screen(CHASSIS_WIDTH / 2.0, 2.0)
        pygame.draw.circle(surface, (255, 255, 170), hl, 6)
        pygame.draw.circle(surface, GOLD_DARK, hl, 6, 2)

        # Speed lines if flying fast
        if veh.vx > 340.0:
            for dy in [-10, 0, 10]:
                sw1 = to_screen(-CHASSIS_WIDTH / 2.0 - 15.0, float(dy))
                sw2 = to_screen(-CHASSIS_WIDTH / 2.0 - 45.0, float(dy))
                pygame.draw.line(surface, WHITE, sw1, sw2, 3)

    def _draw_floating_cues(self, surface: pygame.Surface, veh: Vehicle, cam_x: float) -> None:
        sx = int(veh.x - cam_x)
        sy = int(veh.y)

        # Perfect Landing Banner
        if veh.perfect_landing_active:
            lift = int(veh.perfect_landing_timer * 40.0)
            txt_surf = self._render_cached_text(
                f"{self._copy['ui.perfect_landing']} ⭐".strip(), FontRole.TITLE, 22, (255, 240, 80)
            )
            rect = txt_surf.get_rect(center=(sx, sy - 85 - lift))
            # Background pill
            pill = rect.inflate(20, 10)
            pygame.draw.rect(surface, (30, 40, 60), pill, border_radius=12)
            pygame.draw.rect(surface, GOLD, pill, 2, border_radius=12)
            surface.blit(txt_surf, rect)

        # Comical Flip Boing Banner
        if veh.bounce_active:
            txt_surf = self._render_cached_text(
                f"💥 {self._copy['ui.boing']} 💥".replace("  ", " "), FontRole.TITLE, 28, (255, 80, 80)
            )
            rect = txt_surf.get_rect(center=(sx, sy - 90))
            pill = rect.inflate(24, 12)
            pygame.draw.rect(surface, WHITE, pill, border_radius=14)
            pygame.draw.rect(surface, CHERRY_RED, pill, 3, border_radius=14)
            surface.blit(txt_surf, rect)

    def _draw_hud(self, surface: pygame.Surface, world: CollineWorld) -> None:
        # STRICT RULE: Top-left (0..100, 0..100) is reserved for Greia system navigation (Home/Back).
        # We place our HUD safely at top-center and top-right!

        # 1. Distance Badge (Top Center)
        dist_m = int(world.distance_traveled)
        dist_str = f"🏁  {dist_m} m"
        dist_surf = self._render_cached_text(dist_str, FontRole.TITLE, 24, WHITE)
        dist_rect = dist_surf.get_rect(center=(REFERENCE_WIDTH // 2 - 60, 45))
        pill_dist = dist_rect.inflate(28, 14)
        pygame.draw.rect(surface, (35, 55, 80), pill_dist, border_radius=16)
        pygame.draw.rect(surface, (70, 110, 160), pill_dist, 2, border_radius=16)
        surface.blit(dist_surf, dist_rect)

        # 2. Stars Badge (Top Right)
        star_str = f"⭐  {world.stars_collected}"
        star_surf = self._render_cached_text(star_str, FontRole.TITLE, 24, GOLD)
        star_rect = star_surf.get_rect(center=(REFERENCE_WIDTH // 2 + 110, 45))
        pill_star = star_rect.inflate(28, 14)
        pygame.draw.rect(surface, (35, 55, 80), pill_star, border_radius=16)
        pygame.draw.rect(surface, GOLD_DARK, pill_star, 2, border_radius=16)
        surface.blit(star_surf, star_rect)

        # 3. Speed Bar Gauge (Top Right edge)
        gauge_x = REFERENCE_WIDTH - 170
        gauge_y = 35
        speed_ratio = min(1.0, max(0.0, world.vehicle.vx / 500.0))
        pygame.draw.rect(surface, (35, 55, 80), (gauge_x, gauge_y, 140, 20), border_radius=10)
        fill_w = int(136 * speed_ratio)
        if fill_w > 0:
            bar_color = (80, 210, 255) if speed_ratio < 0.75 else (255, 120, 60)
            pygame.draw.rect(surface, bar_color, (gauge_x + 2, gauge_y + 2, fill_w, 16), border_radius=8)
        pygame.draw.rect(surface, (70, 110, 160), (gauge_x, gauge_y, 140, 20), 2, border_radius=10)

    def _draw_pedals(self, surface: pygame.Surface) -> None:
        # Bottom-Right: Gas Pedal [VAI]
        gx, gy = self.gas_pedal_rect.center
        gas_color = (120, 235, 80) if self.gas_pressed else (75, 195, 55)
        gas_outline = (255, 255, 255) if self.gas_pressed else (45, 140, 30)
        r = 45 if self.gas_pressed else 48
        pygame.draw.circle(surface, gas_color, (gx, gy), r)
        pygame.draw.circle(surface, gas_outline, (gx, gy), r, 4)

        # [VAI] text & icon
        vai_txt = self._render_cached_text(self._copy["ui.go"], FontRole.CONTROL, 22, WHITE, 78)
        v_rect = vai_txt.get_rect(center=(gx, gy - 8))
        surface.blit(vai_txt, v_rect)
        # Double arrows
        pygame.draw.polygon(surface, WHITE, [(gx - 14, gy + 12), (gx - 2, gy + 18), (gx - 14, gy + 24)])
        pygame.draw.polygon(surface, WHITE, [(gx, gy + 12), (gx + 12, gy + 18), (gx, gy + 24)])

        # Bottom-Left: Brake Pedal [FRENA]
        bx, by = self.brake_pedal_rect.center
        brk_color = (255, 160, 40) if self.brake_pressed else (235, 120, 30)
        brk_outline = (255, 255, 255) if self.brake_pressed else (170, 75, 15)
        br = 40 if self.brake_pressed else 44
        pygame.draw.circle(surface, brk_color, (bx, by), br)
        pygame.draw.circle(surface, brk_outline, (bx, by), br, 4)

        # [FRENA] text & icon
        frena_txt = self._render_cached_text(self._copy["ui.brake"], FontRole.CONTROL, 16, WHITE, 70)
        f_rect = frena_txt.get_rect(center=(bx, by - 6))
        surface.blit(frena_txt, f_rect)
        # Stop square
        pygame.draw.rect(surface, WHITE, (bx - 8, by + 8, 16, 16), border_radius=4)
