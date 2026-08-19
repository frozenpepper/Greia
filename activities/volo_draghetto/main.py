from __future__ import annotations

import io
import math
from pathlib import Path
import random
import struct
import time
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
from greia_platform.activity_ui import ChildUiMetrics, mix
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
STORAGE_KEY = "volo_draghetto.progress.v2"

# Dreamy Sky Color Palette
SKY_TOP = (120, 185, 255)
SKY_BOTTOM = (245, 220, 240)
CLOUD_SHADOW = (200, 220, 245)
GOLD = (255, 215, 0)
WHITE = (255, 255, 255)
DARK_TEXT = (50, 40, 60)
PINK = (255, 140, 180)

RAINBOW_COLORS = [
    (255, 80, 80),
    (255, 165, 0),
    (255, 235, 50),
    (70, 210, 120),
    (60, 175, 255),
    (160, 90, 255),
]


def _synth_wav(samples: list[int], rate: int = 22050) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        raw = b"".join(struct.pack("<h", max(-32767, min(32767, s))) for s in samples)
        w.writeframes(raw)
    return buf.getvalue()


class SoundManager:
    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self._init_sounds()
            self._enabled = True
        except Exception:
            self._enabled = False

    def _init_sounds(self) -> None:
        # 1. Star collect chime
        star_samples = []
        for i in range(4000):
            t = i / 22050.0
            f = 880.0 if t < 0.06 else 1320.0
            env = max(0.0, 1.0 - t / 0.18)
            star_samples.append(int(math.sin(2 * math.pi * f * t) * env * 12000))
        self._sounds["star"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(star_samples)))

        # 2. Whoosh / Turbo Dash
        whoosh_samples = []
        for i in range(8000):
            t = i / 22050.0
            f = 300.0 + math.sin(t * 15.0) * 120.0 + (1.0 - t / 0.36) * 400.0
            env = math.sin(math.pi * (t / 0.36))
            noise = (random.random() * 2.0 - 1.0) * 0.2
            whoosh_samples.append(int((math.sin(2 * math.pi * f * t) * 0.8 + noise) * env * 14000))
        self._sounds["whoosh"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(whoosh_samples)))

        # 3. Boing (Cloud bounce)
        boing_samples = []
        for i in range(5000):
            t = i / 22050.0
            f = 240.0 + (t / 0.22) * 320.0
            env = max(0.0, 1.0 - t / 0.22)
            boing_samples.append(int(math.sin(2 * math.pi * f * t) * env * 11000))
        self._sounds["boing"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(boing_samples)))

    def play(self, name: str) -> None:
        if self._enabled and name in self._sounds:
            try:
                self._sounds[name].play()
            except Exception:
                pass


class Particle:
    def __init__(self, x: float, y: float, symbol: str, color: tuple[int, int, int]) -> None:
        self.x = x
        self.y = y
        self.symbol = symbol
        self.color = color
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2.0, 6.0)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.decay = random.uniform(0.03, 0.06)

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay
        return self.life > 0

    def draw(self, surface: pygame.Surface, typography: GreiaTypography, cam_x: float) -> None:
        if self.life > 0:
            sx = int(self.x - cam_x)
            sy = int(self.y)
            if -50 <= sx <= REFERENCE_WIDTH + 50:
                sz = max(12, int(26 * self.life))
                p_surf = typography.render(self.symbol, FontRole.DISPLAY, sz, self.color)
                surface.blit(p_surf, p_surf.get_rect(center=(sx, sy)))


class DragonPlayer:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.target_y = y
        self.speed = 6.5
        self.dash_timer = 0.0
        self.wing_flap = 0.0
        self.accessory = "crown"  # "bow", "crown", "glasses", "flower", "none"

    @property
    def is_dashing(self) -> bool:
        return self.dash_timer > 0

    def update(self) -> None:
        # Move forward
        cur_speed = self.speed * (2.2 if self.is_dashing else 1.0)
        self.x += cur_speed

        # Smooth vertical movement towards target
        dy = self.target_y - self.y
        self.y += dy * 0.14
        self.y = max(80.0, min(520.0, self.y))

        # Flap wings
        self.wing_flap += 0.35 if self.is_dashing else 0.2
        if self.dash_timer > 0:
            self.dash_timer -= 0.035

    def draw(self, surface: pygame.Surface, typography: GreiaTypography, cam_x: float) -> None:
        sx = int(self.x - cam_x)
        sy = int(self.y)

        wing_y_offset = math.sin(self.wing_flap) * 16.0

        # Turbo Speed Aura
        if self.is_dashing:
            for r_i, r_col in enumerate(RAINBOW_COLORS):
                aura_surf = pygame.Surface((130, 90), pygame.SRCALPHA)
                pygame.draw.ellipse(aura_surf, (*r_col, 80), (0, 0, 130, 90))
                surface.blit(aura_surf, (sx - 65 - r_i * 12, sy - 45))

        # Tail
        tail_pts = [(sx - 35, sy + 5), (sx - 75, sy + math.sin(self.wing_flap) * 10), (sx - 40, sy + 15)]
        pygame.draw.polygon(surface, (95, 205, 130), tail_pts)
        pygame.draw.circle(surface, (255, 190, 60), (int(tail_pts[1][0]), int(tail_pts[1][1])), 7)

        # Back Wing
        pygame.draw.polygon(surface, (205, 140, 235), [(sx - 10, sy - 15), (sx - 20, sy - 55 - wing_y_offset), (sx + 15, sy - 25)])

        # Chubby Body
        pygame.draw.ellipse(surface, (95, 205, 130), (sx - 40, sy - 25, 80, 55))
        # Tummy
        pygame.draw.ellipse(surface, (255, 245, 180), (sx - 15, sy - 5, 45, 32))

        # Front Wing
        pygame.draw.polygon(surface, (235, 180, 255), [(sx + 5, sy - 10), (sx - 5, sy - 50 + wing_y_offset), (sx + 30, sy - 20)])

        # Head
        pygame.draw.ellipse(surface, (95, 205, 130), (sx + 15, sy - 35, 55, 48))
        # Horns
        pygame.draw.polygon(surface, (255, 190, 60), [(sx + 30, sy - 33), (sx + 35, sy - 48), (sx + 42, sy - 33)])
        pygame.draw.polygon(surface, (255, 190, 60), [(sx + 45, sy - 30), (sx + 52, sy - 44), (sx + 55, sy - 28)])

        # Rosy Cheek
        pygame.draw.ellipse(surface, (255, 130, 155), (sx + 36, sy - 10, 14, 10))

        # Eye
        pygame.draw.ellipse(surface, (40, 40, 50), (sx + 42, sy - 26, 16, 18))
        pygame.draw.circle(surface, WHITE, (sx + 46, sy - 22), 4)
        pygame.draw.circle(surface, WHITE, (sx + 52, sy - 16), 2)

        # Smiling mouth
        pygame.draw.arc(surface, (30, 80, 40), (sx + 50, sy - 12, 14, 12), 0, math.pi, 2)

        # Accessory
        if self.accessory == "bow":
            bx, by = sx + 25, sy - 38
            pygame.draw.polygon(surface, PINK, [(bx, by), (bx - 12, by - 8), (bx - 12, by + 8)])
            pygame.draw.polygon(surface, PINK, [(bx, by), (bx + 12, by - 8), (bx + 12, by + 8)])
            pygame.draw.circle(surface, (255, 80, 120), (bx, by), 5)
        elif self.accessory == "crown":
            cx, cy = sx + 38, sy - 44
            pygame.draw.polygon(surface, GOLD, [(cx - 15, cy), (cx - 15, cy - 14), (cx - 7, cy - 6), (cx, cy - 16), (cx + 7, cy - 6), (cx + 15, cy - 14), (cx + 15, cy)])
        elif self.accessory == "glasses":
            gx, gy = sx + 48, sy - 18
            pygame.draw.circle(surface, (30, 30, 30), (gx, gy), 10, 2)
            pygame.draw.line(surface, (30, 30, 30), (gx - 10, gy), (gx - 18, gy - 4), 2)
        elif self.accessory == "flower":
            fx, fy = sx + 35, sy - 40
            for a_i in range(5):
                fa = a_i * (2 * math.pi / 5)
                pygame.draw.circle(surface, PINK, (int(fx + math.cos(fa) * 8), int(fy + math.sin(fa) * 8)), 5)
            pygame.draw.circle(surface, GOLD, (fx, fy), 4)


class StarCollectible:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.collected = False
        self.bob = random.uniform(0, 2 * math.pi)

    def draw(self, surface: pygame.Surface, typography: GreiaTypography, cam_x: float) -> None:
        if not self.collected:
            sx = int(self.x - cam_x)
            sy = int(self.y + math.sin(self.bob) * 6)
            if -50 <= sx <= REFERENCE_WIDTH + 50:
                # Shimmer aura
                halo = pygame.Surface((60, 60), pygame.SRCALPHA)
                pygame.draw.circle(halo, (255, 235, 120, 90), (30, 30), 26)
                surface.blit(halo, (sx - 30, sy - 30))
                txt = typography.render("⭐", FontRole.DISPLAY, 36, DARK_TEXT)
                surface.blit(txt, txt.get_rect(center=(sx, sy)))


class RainbowArch:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.passed = False

    def draw(self, surface: pygame.Surface, cam_x: float) -> None:
        sx = int(self.x - cam_x)
        sy = int(self.y)
        if -160 <= sx <= REFERENCE_WIDTH + 160:
            # Draw rainbow arch
            for i, col in enumerate(RAINBOW_COLORS):
                r = 80 - i * 7
                pygame.draw.arc(surface, col, (sx - r, sy - r, r * 2, r * 2), math.pi, 2 * math.pi, 7)

            # Clouds at base
            pygame.draw.circle(surface, WHITE, (sx - 75, sy), 24)
            pygame.draw.circle(surface, WHITE, (sx + 75, sy), 24)
            pygame.draw.circle(surface, (230, 245, 255), (sx - 65, sy + 6), 18)
            pygame.draw.circle(surface, (230, 245, 255), (sx + 65, sy + 6), 18)


class CloudObstacle:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def draw(self, surface: pygame.Surface, cam_x: float) -> None:
        sx = int(self.x - cam_x)
        sy = int(self.y)
        if -150 <= sx <= REFERENCE_WIDTH + 150:
            pygame.draw.ellipse(surface, WHITE, (sx - 55, sy - 28, 110, 56))
            pygame.draw.ellipse(surface, (240, 248, 255), (sx - 32, sy - 42, 64, 48))
            pygame.draw.ellipse(surface, (230, 240, 255), (sx - 45, sy - 6, 90, 28))


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
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    theme = get_theme()
    metrics = ChildUiMetrics.for_size(*screen.get_size())
    canvas = PygameReferenceCanvas(screen)
    typography = GreiaTypography()
    sounds = SoundManager()
    try:
        storage = get_storage()
    except Exception:
        storage = None

    def safe_emit(ev_id: str, ikey: str, payload: object = None) -> None:
        try:
            emit_activity_event(ev_id, idempotency_key=ikey, payload=payload)
        except Exception:
            pass

    # Localization
    package_root = Path(__file__).parent
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    profile_lang = get_profile_locale()
    context = resolve_activity_locale(profile_lang, support)
    resources = LocalizedResources(package_root, context) if context else None
    active_locale = context.selected.language if context else "it"

    score = 0
    stars_count = 0
    if storage is not None:
        try:
            saved = storage.kv_get(STORAGE_KEY, {})
            if isinstance(saved, dict):
                score = int(saved.get("score", 0))
                stars_count = int(saved.get("stars", 0))
        except Exception:
            pass

    dragon = DragonPlayer(200.0, 300.0)
    stars: list[StarCollectible] = []
    arches: list[RainbowArch] = []
    clouds: list[CloudObstacle] = []
    particles: list[Particle] = []

    last_spawn_x = 400.0

    def spawn_chunk(start_x: float, end_x: float) -> None:
        # Spawn stars in gentle paths
        cur_x = start_x
        while cur_x < end_x:
            pattern_type = random.choice(["wave", "arc", "cluster"])
            if pattern_type == "wave":
                base_y = random.uniform(180, 420)
                for step in range(5):
                    sy = base_y + math.sin(step * 0.8) * 60
                    stars.append(StarCollectible(cur_x + step * 70, sy))
                cur_x += 450
            elif pattern_type == "arc":
                # Rainbow Arch with stars underneath
                arch_y = random.uniform(220, 400)
                arches.append(RainbowArch(cur_x + 120, arch_y))
                for s_i in range(3):
                    stars.append(StarCollectible(cur_x + 60 + s_i * 60, arch_y - 20))
                cur_x += 480
            else:
                cy = random.uniform(150, 450)
                clouds.append(CloudObstacle(cur_x + 100, cy))
                stars.append(StarCollectible(cur_x + 100, cy - 80 if cy > 300 else cy + 80))
                cur_x += 380

    spawn_chunk(400, 3000)
    last_spawn_x = 3000

    feedback_text = ""
    feedback_timer = 0.0

    running = True
    ready_published = False

    while running and not activity_stop_requested():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    # Dash
                    dragon.dash_timer = 4.0
                    sounds.play("whoosh")
            elif event.type == pygame.MOUSEMOTION:
                if _is_safe_point(screen, event.pos):
                    plog = canvas.pointer(event.pos)
                    if plog is not None:
                        dragon.target_y = max(80.0, min(520.0, plog[1]))
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if not _is_safe_point(screen, event.pos):
                    continue
                logical = canvas.pointer(event.pos)
                if logical is not None:
                    lx, ly = logical
                    # Accessory Switcher Button (Top Right x = 600..750, y = 10..70)
                    if 600 <= lx <= 750 and 10 <= ly <= 70:
                        acc_list = ["crown", "bow", "glasses", "flower", "none"]
                        c_idx = acc_list.index(dragon.accessory) if dragon.accessory in acc_list else 0
                        dragon.accessory = acc_list[(c_idx + 1) % len(acc_list)]
                        sounds.play("star")
                        for _ in range(12):
                            particles.append(Particle(dragon.x, dragon.y, "✨", PINK))

        # Continuous Keyboard Arrow Keys & WASD Support
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dragon.target_y = max(80.0, dragon.target_y - 8.0)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dragon.target_y = min(520.0, dragon.target_y + 8.0)

        # Update Dragon
        dragon.update()
        cam_x = dragon.x - 200.0

        # Chunk streaming
        if dragon.x + 1500 > last_spawn_x:
            spawn_chunk(last_spawn_x, last_spawn_x + 2000)
            last_spawn_x += 2000

        # Particle trail
        if dragon.is_dashing:
            t_col = random.choice(RAINBOW_COLORS)
            particles.append(Particle(dragon.x - 30, dragon.y, "✨", t_col))
            particles.append(Particle(dragon.x - 45, dragon.y + random.uniform(-12, 12), "🌟", t_col))
        elif random.random() < 0.3:
            particles.append(Particle(dragon.x - 30, dragon.y, "✨", (255, 240, 200)))

        # Collisions: Stars
        for st in stars:
            if not st.collected:
                st.bob += 0.08
                if (dragon.x - st.x) ** 2 + (dragon.y - st.y) ** 2 <= 55 ** 2:
                    st.collected = True
                    sounds.play("star")
                    stars_count += 1
                    score += 10 * (2 if dragon.is_dashing else 1)
                    for _ in range(10):
                        particles.append(Particle(st.x, st.y, "⭐", GOLD))
                    safe_emit("flight.star_collected", f"star-{time.time()}")

        # Collisions: Rainbow Arches (Flying through the arch gives Super Rainbow Turbo Boost!)
        for arch in arches:
            if not arch.passed and abs(dragon.x - arch.x) < 65 and (arch.y - 120 <= dragon.y <= arch.y + 40):
                arch.passed = True
                dragon.dash_timer = 5.0
                sounds.play("whoosh")
                sounds.play("star")
                score += 25
                stars_count += 2
                feedback_text = resources.text("msg.rainbow_dash") if resources else "🌈 TURBO ARCOBALENO! 🚀"
                feedback_timer = 2.5
                for _ in range(30):
                    particles.append(Particle(arch.x, arch.y - 40, "🌈", random.choice(RAINBOW_COLORS)))
                    particles.append(Particle(arch.x, arch.y - 40, "⭐", GOLD))
                safe_emit("flight.rainbow_boost", f"rainbow-{time.time()}")

        # Collisions: Clouds (Bouncy and giggle!)
        for cl in clouds:
            if abs(dragon.x - cl.x) < 50 and abs(dragon.y - cl.y) < 40:
                sounds.play("boing")
                dragon.target_y = 120.0 if dragon.y > cl.y else 480.0
                for _ in range(8):
                    particles.append(Particle(cl.x, cl.y, "☁️", (220, 235, 255)))

        # Clean old world items
        stars = [s for s in stars if s.x > cam_x - 200]
        arches = [a for a in arches if a.x > cam_x - 200]
        clouds = [c for c in clouds if c.x > cam_x - 200]
        particles = [p for p in particles if p.update()]

        if feedback_timer > 0:
            feedback_timer -= 0.035
        else:
            feedback_text = ""

        # --- RENDERING (Logical Canvas 1024x600) ---
        surf = canvas.surface

        # 1. Sky Gradient Background
        for gy in range(0, REFERENCE_HEIGHT, 8):
            c_sky = mix(SKY_TOP, SKY_BOTTOM, gy / float(REFERENCE_HEIGHT))
            pygame.draw.rect(surf, c_sky, (0, gy, REFERENCE_WIDTH, 8))

        # Distant background clouds parallax
        random.seed(42)
        for c_i in range(12):
            cx = (c_i * 280 - int(cam_x * 0.3)) % (REFERENCE_WIDTH + 300) - 100
            cy = 80 + (c_i % 4) * 110
            pygame.draw.ellipse(surf, (255, 255, 255, 120), (cx, cy, 140, 50))
        random.seed()

        # 2. World Elements
        for cl in clouds:
            cl.draw(surf, cam_x)
        for arch in arches:
            arch.draw(surf, cam_x)
        for st in stars:
            st.draw(surf, typography, cam_x)

        # 3. Dragon Player
        dragon.draw(surf, typography, cam_x)

        # Particles
        for p in particles:
            p.draw(surf, typography, cam_x)

        # 4. Top Accessory Button (x=590..740, y=12..64)
        acc_box = pygame.Rect(590, 12, 150, 52)
        pygame.draw.rect(surf, WHITE, acc_box, border_radius=16)
        pygame.draw.rect(surf, (160, 120, 180), acc_box, width=2, border_radius=16)
        acc_txt = typography.render(f"👑 Look", FontRole.TITLE, 22, DARK_TEXT)
        surf.blit(acc_txt, acc_txt.get_rect(center=acc_box.center))

        # 5. Top-Right HUD Badge (Stars & Score)
        hud_box = pygame.Rect(765, 12, 235, 52)
        pygame.draw.rect(surf, WHITE, hud_box, border_radius=16)
        pygame.draw.rect(surf, (160, 120, 180), hud_box, width=2, border_radius=16)
        hud_str = f"⭐ {stars_count}   🏆 {score}"
        h_surf = typography.render(hud_str, FontRole.TITLE, 24, (160, 80, 20))
        surf.blit(h_surf, h_surf.get_rect(center=hud_box.center))

        # 6. Feedback Toast Message
        if feedback_text:
            f_rect = pygame.Rect(262, 80, 500, 48)
            pygame.draw.rect(surf, WHITE, f_rect, border_radius=16)
            pygame.draw.rect(surf, PINK, f_rect, width=3, border_radius=16)
            t_msg = typography.render(feedback_text, FontRole.TITLE, 24, DARK_TEXT)
            surf.blit(t_msg, t_msg.get_rect(center=f_rect.center))

        # Present Canvas
        canvas.present(clear=theme.background)

        # Star pointer cursor
        if pygame.mouse.get_focused():
            mpos = pygame.mouse.get_pos()
            pygame.draw.circle(screen, GOLD, mpos, metrics.px(10))
            pygame.draw.circle(screen, WHITE, mpos, metrics.px(5))

        pygame.display.flip()

        if not ready_published:
            mark_activity_ready()
            ready_published = True

        clock.tick(30)

    if storage is not None:
        try:
            storage.kv_set(STORAGE_KEY, {
                "score": score,
                "stars": stars_count,
                "timestamp": time.time(),
            })
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
