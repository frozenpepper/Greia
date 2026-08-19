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
STORAGE_KEY = "orchestra_animali.state.v2"

# Grand Theater Palette
STAGE_WALL_TOP = (22, 18, 42)
STAGE_WALL_BOTTOM = (45, 30, 65)
STAGE_CURTAIN = (175, 30, 45)
STAGE_CURTAIN_DARK = (120, 18, 30)
STAGE_CURTAIN_GOLD = (245, 195, 60)
STAGE_WOOD_TOP = (180, 115, 60)
STAGE_WOOD_BOTTOM = (110, 65, 30)
STAGE_GOLD = (255, 215, 60)
WHITE = (255, 255, 255)
DARK_TEXT = (45, 35, 42)

RAINBOW_COLORS = [
    (245, 75, 75),    # 1: C (Do) - Red
    (250, 140, 45),   # 2: D (Re) - Orange
    (255, 215, 45),   # 3: E (Mi) - Yellow
    (85, 205, 105),   # 4: F (Fa) - Green
    (65, 180, 245),   # 5: G (Sol) - Cyan
    (115, 110, 235),  # 6: A (La) - Indigo
    (200, 85, 215),   # 7: B (Si) - Violet
    (255, 95, 160),   # 8: C5 (Do alto) - Pink
]

NOTE_NAMES_IT = ["DO", "RE", "MI", "FA", "SOL", "LA", "SI", "DO"]
NOTE_NAMES_EN = ["C", "D", "E", "F", "G", "A", "B", "C"]
NOTE_FREQS = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25]
KEYBOARD_SHORTCUTS = ["1", "2", "3", "4", "5", "6", "7", "8"]


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
        self._notes: list[pygame.mixer.Sound] = []
        self._inst_sounds: dict[str, pygame.mixer.Sound] = {}
        self._enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self._init_sounds()
            self._enabled = True
        except Exception:
            self._enabled = False

    def _init_sounds(self) -> None:
        for freq in NOTE_FREQS:
            samples = []
            for i in range(8800):
                t = i / 22050.0
                env = math.exp(-t * 4.2)
                val = int((math.sin(2 * math.pi * freq * t) * 0.72 +
                           math.sin(4 * math.pi * freq * t) * 0.22 +
                           math.sin(6 * math.pi * freq * t) * 0.06) * env * 15000)
                samples.append(val)
            self._notes.append(pygame.mixer.Sound(io.BytesIO(_synth_wav(samples))))

        # Drums (Bass + Snare pop)
        bd_samples = []
        for i in range(4500):
            t = i / 22050.0
            freq = max(45.0, 160.0 - t * 450.0)
            env = math.exp(-t * 10.0)
            val = int(math.sin(2 * math.pi * freq * t) * env * 18000)
            bd_samples.append(val)
        self._inst_sounds["drums"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(bd_samples)))

        # Trumpet Fanfare
        tr_samples = []
        for i in range(6500):
            t = i / 22050.0
            f = 587.33 + math.sin(t * 40) * 12
            env = max(0.0, 1.0 - t / 0.28)
            val = int((math.sin(2 * math.pi * f * t) * 0.6 + math.sin(4 * math.pi * f * t) * 0.4) * env * 15000)
            tr_samples.append(val)
        self._inst_sounds["trumpet"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(tr_samples)))

        # Maracas Shaker
        mr_samples = []
        for i in range(3500):
            t = i / 22050.0
            env = max(0.0, 1.0 - t / 0.15)
            val = int(random.uniform(-1, 1) * env * 12000)
            mr_samples.append(val)
        self._inst_sounds["maracas"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(mr_samples)))

        # Singing Bird Tweet
        bd_tweet = []
        for i in range(6000):
            t = i / 22050.0
            f = 1046.50 + math.sin(t * 50) * 220
            env = max(0.0, 1.0 - t / 0.25)
            val = int(math.sin(2 * math.pi * f * t) * env * 13000)
            bd_tweet.append(val)
        self._inst_sounds["bird"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(bd_tweet)))

        # Piano Chime Chord
        pn_samples = []
        for i in range(8000):
            t = i / 22050.0
            f1, f2 = 523.25, 659.25
            env = math.exp(-t * 3.5)
            val = int((math.sin(2 * math.pi * f1 * t) + math.sin(2 * math.pi * f2 * t)) * 0.5 * env * 14000)
            pn_samples.append(val)
        self._inst_sounds["piano"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(pn_samples)))

        # Ball bounce boing
        bn_samples = []
        for i in range(2500):
            t = i / 22050.0
            f = 380.0 + (1.0 - t / 0.12) * 260.0
            env = max(0.0, 1.0 - t / 0.11)
            val = int(math.sin(2 * math.pi * f * t) * env * 11000)
            bn_samples.append(val)
        self._inst_sounds["bounce"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(bn_samples)))

    def play_note(self, index: int) -> None:
        if self._enabled and 0 <= index < len(self._notes):
            try:
                self._notes[index].play()
            except Exception:
                pass

    def play_inst(self, name: str) -> None:
        if self._enabled and name in self._inst_sounds:
            try:
                self._inst_sounds[name].play()
            except Exception:
                pass


class Particle:
    def __init__(self, x: float, y: float, symbol: str, color: tuple[int, int, int]) -> None:
        self.x = x
        self.y = y
        self.symbol = symbol
        self.color = color
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2.5, 7.0)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 1.5
        self.life = 1.0
        self.decay = random.uniform(0.025, 0.045)
        self.size = random.randint(18, 28)

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.08
        self.life -= self.decay
        return self.life > 0

    def draw(self, surface: pygame.Surface, typography: GreiaTypography) -> None:
        if self.life > 0:
            sz = max(10, int(self.size * self.life))
            txt_surf = typography.render(self.symbol, FontRole.BODY, sz, self.color)
            surface.blit(txt_surf, (int(self.x) - txt_surf.get_width() // 2, int(self.y) - txt_surf.get_height() // 2))


class AnimalMusician:
    def __init__(self, mus_id: str, icon: str, name: str, inst_name: str, sound_name: str, x: float, y: float) -> None:
        self.mus_id = mus_id
        self.icon = icon
        self.name = name
        self.inst_name = inst_name
        self.sound_name = sound_name
        self.x = x
        self.y = y
        self.radius = 48.0
        self.jump_timer = 0.0
        self.is_active = False
        self.phase = random.uniform(0, 2 * math.pi)

    def trigger(self) -> None:
        self.jump_timer = 1.2

    def update(self) -> None:
        self.phase += 0.04
        if self.jump_timer > 0:
            self.jump_timer -= 0.04

    def contains(self, px: float, py: float) -> bool:
        return (self.x - px) ** 2 + (self.y - py) ** 2 <= (self.radius + 12) ** 2

    def draw(self, surface: pygame.Surface, typography: GreiaTypography) -> None:
        ox = int(self.x)
        oy = int(self.y)
        if self.jump_timer > 0:
            oy += int(-math.sin(self.jump_timer * math.pi) * 24.0)
        else:
            oy += int(math.sin(self.phase) * 4.0)

        # Floor shadow
        pygame.draw.ellipse(surface, (15, 12, 25), (ox - 40, int(self.y) + 38, 80, 20))

        # Spotlight glow
        spot_surf = pygame.Surface((120, 120), pygame.SRCALPHA)
        glow_alpha = 140 if self.jump_timer > 0 else 60
        pygame.draw.circle(spot_surf, (255, 240, 180, glow_alpha), (60, 60), 55)
        surface.blit(spot_surf, (ox - 60, oy - 60))

        # Pedestal / Podium
        pygame.draw.ellipse(surface, (140, 90, 50), (ox - 44, oy + 28, 88, 24))
        pygame.draw.ellipse(surface, STAGE_GOLD, (ox - 44, oy + 28, 88, 24), width=2)

        # Musician Card Avatar
        avatar_bg = (255, 248, 235)
        pygame.draw.circle(surface, avatar_bg, (ox, oy), int(self.radius))
        border_col = STAGE_GOLD if self.jump_timer > 0 else (61, 44, 31)
        border_w = 4 if self.jump_timer > 0 else 3
        pygame.draw.circle(surface, border_col, (ox, oy), int(self.radius), width=border_w)

        # Character Emoji Icon
        char_surf = typography.render(self.icon, FontRole.DISPLAY, 46, DARK_TEXT)
        surface.blit(char_surf, (ox - char_surf.get_width() // 2, oy - char_surf.get_height() // 2 - 4))

        # Instrument badge
        inst_badge = pygame.Rect(ox - 38, oy + 26, 76, 22)
        pygame.draw.rect(surface, (30, 24, 45), inst_badge, border_radius=6)
        pygame.draw.rect(surface, STAGE_GOLD, inst_badge, width=1, border_radius=6)
        lbl_surf = typography.render(self.inst_name, FontRole.CONTROL, 14, STAGE_GOLD)
        surface.blit(lbl_surf, (inst_badge.centerx - lbl_surf.get_width() // 2, inst_badge.centery - lbl_surf.get_height() // 2))


class BouncyBall:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.vx = 4.0
        self.vy = -3.0
        self.radius = 22.0
        self.is_held = False
        self.trail: list[tuple[float, float]] = []
        self.last_pos = (x, y)

    def update(self, bounds_rect: pygame.Rect) -> list[str]:
        events = []
        if self.is_held:
            return events

        # Apply gravity & air resistance
        self.vy += 0.45
        self.vx *= 0.995

        self.x += self.vx
        self.y += self.vy

        self.trail.append((self.x, self.y))
        if len(self.trail) > 8:
            self.trail.pop(0)

        # Wall collisions
        # Left wall
        if self.x - self.radius < bounds_rect.left:
            self.x = bounds_rect.left + self.radius
            self.vx = abs(self.vx) * 0.82
            events.append("bounce")
        # Right wall
        elif self.x + self.radius > bounds_rect.right:
            self.x = bounds_rect.right - self.radius
            self.vx = -abs(self.vx) * 0.82
            events.append("bounce")

        # Ceiling
        if self.y - self.radius < bounds_rect.top:
            self.y = bounds_rect.top + self.radius
            self.vy = abs(self.vy) * 0.82
            events.append("bounce")

        # Floor (above keyboard)
        if self.y + self.radius > 580:
            self.y = 580 - self.radius
            self.vy = -abs(self.vy) * 0.76
            events.append("bounce")

        return events

    def draw(self, surface: pygame.Surface) -> None:
        # Draw motion trail
        for i, (tx, ty) in enumerate(self.trail):
            r = max(2, int(self.radius * (i + 1) / len(self.trail) * 0.6))
            alpha = int(120 * (i + 1) / len(self.trail))
            t_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(t_surf, (255, 140, 50, alpha), (r, r), r)
            surface.blit(t_surf, (int(tx) - r, int(ty) - r))

        cx, cy = int(self.x), int(self.y)
        # Glow
        glow_surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (255, 190, 80, 90), (32, 32), 30)
        surface.blit(glow_surf, (cx - 32, cy - 32))

        # Ball body with 3D gradient
        pygame.draw.circle(surface, (255, 90, 40), (cx, cy), int(self.radius))
        pygame.draw.circle(surface, (255, 180, 80), (cx - 5, cy - 5), int(self.radius * 0.65))
        pygame.draw.circle(surface, WHITE, (cx - 8, cy - 8), 6)
        pygame.draw.circle(surface, (60, 30, 20), (cx, cy), int(self.radius), width=2)


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

    package_root = Path(__file__).parent
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    profile_lang = get_profile_locale()
    context = resolve_activity_locale(profile_lang, support)
    resources = LocalizedResources(package_root, context) if context else None
    active_locale = context.selected.language if context else "it"
    note_labels = NOTE_NAMES_IT if active_locale == "it" else NOTE_NAMES_EN

    score = 0
    stars = 0

    if storage is not None:
        try:
            saved = storage.kv_get(STORAGE_KEY, {})
            if isinstance(saved, dict):
                score = int(saved.get("score", 0))
                stars = int(saved.get("stars", 0))
        except Exception:
            pass

    # 5 Animal Musicians on Stage
    musicians = [
        AnimalMusician("cat", "🐱", "Gattina", "Pianoforte", "piano", 190, 230),
        AnimalMusician("dog", "🐶", "Cagnolino", "Batteria", "drums", 350, 210),
        AnimalMusician("frog", "🐸", "Ranocchia", "Tromba", "trumpet", 512, 230),
        AnimalMusician("bear", "🐻", "Orsetto", "Maracas", "maracas", 670, 210),
        AnimalMusician("bird", "🐦", "Uccellino", "Voce", "bird", 830, 230),
    ]

    particles: list[Particle] = []
    ball = BouncyBall(512, 140)
    stage_bounds = pygame.Rect(40, 100, 944, 480)

    # Piano Key highlight timers
    key_highlight_timers = [0.0] * 8
    key_pressed = [False] * 8

    feedback_text = ""
    feedback_timer = 0.0

    running = True
    ready_published = False

    def trigger_piano_key(k_idx: int):
        if 0 <= k_idx < 8:
            sounds.play_note(k_idx)
            key_highlight_timers[k_idx] = 1.0
            kx = 64 + k_idx * 112
            for _ in range(12):
                particles.append(Particle(kx + 52, 460, "🎵", RAINBOW_COLORS[k_idx]))
            safe_emit("instrument.played", f"note-{time.time()}", payload={"note": k_idx})

    while running and not activity_stop_requested():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                # Keyboard shortcuts 1..8 and A..K
                key_map = {
                    pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3,
                    pygame.K_5: 4, pygame.K_6: 5, pygame.K_7: 6, pygame.K_8: 7,
                    pygame.K_a: 0, pygame.K_s: 1, pygame.K_d: 2, pygame.K_f: 3,
                    pygame.K_g: 4, pygame.K_h: 5, pygame.K_j: 6, pygame.K_k: 7,
                }
                if event.key in key_map:
                    trigger_piano_key(key_map[event.key])
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not _is_safe_point(screen, event.pos):
                    continue
                logical = canvas.pointer(event.pos)
                if logical is not None:
                    lx, ly = logical
                    # Check grabbing the bouncy ball
                    if math.hypot(lx - ball.x, ly - ball.y) <= ball.radius + 16:
                        ball.is_held = True
                        ball.vx = 0.0
                        ball.vy = 0.0
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if ball.is_held:
                    ball.is_held = False
                    # Velocity from flick
                    if pygame.mouse.get_focused():
                        mpos = pygame.mouse.get_pos()
                        plog = canvas.pointer(mpos)
                        if plog is not None:
                            dx = plog[0] - ball.last_pos[0]
                            dy = plog[1] - ball.last_pos[1]
                            ball.vx = max(-18.0, min(18.0, dx * 0.8))
                            ball.vy = max(-18.0, min(18.0, dy * 0.8))

                if not _is_safe_point(screen, event.pos):
                    continue
                logical = canvas.pointer(event.pos)
                if logical is not None:
                    lx, ly = logical

                    # 1. Animal Musicians direct tap
                    for m in musicians:
                        if m.contains(lx, ly):
                            m.trigger()
                            sounds.play_inst(m.sound_name)
                            for _ in range(16):
                                particles.append(Particle(m.x, m.y - 20, "🎶", STAGE_GOLD))
                            safe_emit("instrument.played", f"mus-{time.time()}", payload={"musician": m.mus_id})

                    # 2. Rainbow Piano Keys direct tap (y = 440..570)
                    for k_i in range(8):
                        kx = 64 + k_i * 112
                        if kx <= lx <= kx + 104 and 440 <= ly <= 570:
                            trigger_piano_key(k_i)

        # Dragging ball motion
        if ball.is_held and pygame.mouse.get_focused():
            mpos = pygame.mouse.get_pos()
            if _is_safe_point(screen, mpos):
                plog = canvas.pointer(mpos)
                if plog is not None:
                    ball.last_pos = (ball.x, ball.y)
                    ball.x = max(60.0, min(964.0, plog[0]))
                    ball.y = max(110.0, min(550.0, plog[1]))

        # Ball physics & Collisions
        ball_events = ball.update(stage_bounds)
        if "bounce" in ball_events:
            sounds.play_inst("bounce")

        if not ball.is_held:
            # Check collision with animal musicians
            for m in musicians:
                dist = math.hypot(ball.x - m.x, ball.y - m.y)
                if dist < ball.radius + m.radius:
                    # Bounce ball off musician
                    nx = (ball.x - m.x) / max(0.1, dist)
                    ny = (ball.y - m.y) / max(0.1, dist)
                    ball.vx = nx * 8.5 + random.uniform(-2, 2)
                    ball.vy = ny * 8.5 - 3.0
                    ball.x = m.x + nx * (ball.radius + m.radius + 2)
                    ball.y = m.y + ny * (ball.radius + m.radius + 2)

                    m.trigger()
                    sounds.play_inst(m.sound_name)
                    score += 5
                    stars += 1
                    for _ in range(16):
                        particles.append(Particle(m.x, m.y - 20, "✨", STAGE_GOLD))
                    safe_emit("instrument.played", f"ball-{time.time()}", payload={"musician": m.mus_id})

            # Check collision with piano keys
            if 435 <= ball.y <= 485:
                for k_i in range(8):
                    kx = 64 + k_i * 112
                    if kx <= ball.x <= kx + 104 and ball.vy > 0:
                        trigger_piano_key(k_i)
                        ball.vy = -abs(ball.vy) * 0.85 - 2.5
                        score += 5
                        break

        # State updates
        for m in musicians:
            m.update()
        for i in range(8):
            if key_highlight_timers[i] > 0:
                key_highlight_timers[i] -= 0.05
        particles = [p for p in particles if p.update()]

        # --- RENDERING ---
        surf = canvas.surface

        # 1. Grand Theater Stage Background
        for y in range(0, 430, 8):
            ratio = y / 430.0
            col = mix(STAGE_WALL_TOP, STAGE_WALL_BOTTOM, ratio)
            pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 8))

        # Stage Floor with wood plank lines
        for y in range(430, REFERENCE_HEIGHT, 6):
            ratio = (y - 430) / float(REFERENCE_HEIGHT - 430)
            col = mix(STAGE_WOOD_TOP, STAGE_WOOD_BOTTOM, ratio)
            pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 6))

        # Velvet Stage Curtains along top and sides
        pygame.draw.polygon(surf, STAGE_CURTAIN_DARK, [(0, 0), (140, 0), (90, 440), (0, 440)])
        pygame.draw.polygon(surf, STAGE_CURTAIN, [(0, 0), (120, 0), (70, 430), (0, 430)])
        pygame.draw.polygon(surf, STAGE_CURTAIN_DARK, [(REFERENCE_WIDTH, 0), (REFERENCE_WIDTH - 140, 0), (REFERENCE_WIDTH - 90, 440), (REFERENCE_WIDTH, 440)])
        pygame.draw.polygon(surf, STAGE_CURTAIN, [(REFERENCE_WIDTH, 0), (REFERENCE_WIDTH - 120, 0), (REFERENCE_WIDTH - 70, 430), (REFERENCE_WIDTH, 430)])

        # Top valance swag
        for vx in range(120, 900, 130):
            pygame.draw.circle(surf, STAGE_CURTAIN, (vx + 65, 30), 75)
            pygame.draw.circle(surf, STAGE_CURTAIN_GOLD, (vx + 65, 30), 75, width=2)

        # 2. Animal Musicians on Stage
        for m in musicians:
            m.draw(surf, typography)

        # 3. Interactive Physics Bouncy Ball
        ball.draw(surf)

        # 4. Particles
        for p in particles:
            p.draw(surf, typography)

        # 5. Rainbow Piano Keys with Keyboard Number Badges (y = 440..570)
        for k_i in range(8):
            kx = 64 + k_i * 112
            key_rect = pygame.Rect(kx, 440, 104, 130)
            hl = key_highlight_timers[k_i]
            base_col = RAINBOW_COLORS[k_i]

            # Key Drop Shadow
            pygame.draw.rect(surf, (20, 15, 25), (kx + 3, 444, 104, 130), border_radius=14)

            # Key Plate
            fill_col = mix(base_col, WHITE, 0.4) if hl > 0 else base_col
            pygame.draw.rect(surf, fill_col, key_rect, border_radius=14)
            pygame.draw.rect(surf, WHITE, (kx + 8, 446, 88, 14), border_radius=6)  # Bevel highlight
            pygame.draw.rect(surf, (61, 44, 31), key_rect, width=3, border_radius=14)

            # Keyboard shortcut badge [ 1 ]
            badge_rect = pygame.Rect(kx + 32, 448, 40, 22)
            pygame.draw.rect(surf, (255, 250, 240), badge_rect, border_radius=6)
            pygame.draw.rect(surf, (61, 44, 31), badge_rect, width=1, border_radius=6)
            sc_surf = typography.render(KEYBOARD_SHORTCUTS[k_i], FontRole.CONTROL, 14, DARK_TEXT)
            surf.blit(sc_surf, (badge_rect.centerx - sc_surf.get_width() // 2, badge_rect.centery - sc_surf.get_height() // 2))

            # Note Name (DO, RE, MI...)
            note_str = note_labels[k_i]
            n_surf = typography.render(note_str, FontRole.DISPLAY, 26, (255, 255, 255) if hl <= 0 else DARK_TEXT)
            surf.blit(n_surf, (kx + 52 - n_surf.get_width() // 2, 490))

        # 6. Top Header & HUD (Clear of Home at x < 120)
        # Title card (x = 360..664, y = 16..68)
        title_rect = pygame.Rect(360, 16, 304, 52)
        pygame.draw.rect(surf, (255, 250, 240), title_rect, border_radius=14)
        pygame.draw.rect(surf, (61, 44, 31), title_rect, width=2, border_radius=14)
        title_str = "🎵 Orchestra degli Animali 🐾" if active_locale == "it" else "🎵 Animal Orchestra 🐾"
        t_surf = typography.render(title_str, FontRole.TITLE, 20, DARK_TEXT)
        surf.blit(t_surf, (title_rect.centerx - t_surf.get_width() // 2, title_rect.centery - t_surf.get_height() // 2))

        # HUD Stars & Score (Top Right x=775..1000)
        hud_rect = pygame.Rect(775, 12, 225, 56)
        pygame.draw.rect(surf, (255, 250, 240), hud_rect, border_radius=16)
        pygame.draw.rect(surf, (61, 44, 31), hud_rect, width=2, border_radius=16)
        hud_text = f"⭐ {stars}   🏆 {score}"
        hud_surf = typography.render(hud_text, FontRole.TITLE, 24, (180, 90, 20))
        surf.blit(hud_surf, (hud_rect.centerx - hud_surf.get_width() // 2, hud_rect.centery - hud_surf.get_height() // 2))

        canvas.present(clear=theme.background)
        pygame.display.flip()
        if not ready_published:
            mark_activity_ready()
            ready_published = True

        clock.tick(30)

    if storage is not None:
        try:
            storage.kv_set(STORAGE_KEY, {"score": score, "stars": stars})
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
