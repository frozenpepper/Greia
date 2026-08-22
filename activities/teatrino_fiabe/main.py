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
from greia_platform.activity_ui import ChildUiMetrics, is_home_clicked, mix
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

# Optional Pygame SDL2 Audio Capture
try:
    import pygame._sdl2.audio as sdl2_audio
except Exception:
    sdl2_audio = None


REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
STORAGE_KEY = "teatrino_fiabe.state.v3"
MAX_RECORDING_SECONDS = 45.0

# Grand Theater Palette
STAGE_GOLD = (255, 215, 60)
STAGE_GOLD_DARK = (180, 130, 20)
STAGE_CURTAIN = (180, 25, 40)
STAGE_CURTAIN_DARK = (115, 15, 25)
STAGE_CURTAIN_LIGHT = (215, 45, 60)
STAGE_WOOD_TOP = (175, 110, 55)
STAGE_WOOD_BOTTOM = (105, 60, 25)
WHITE = (255, 255, 255)
DARK_TEXT = (45, 35, 42)
REC_RED = (235, 45, 45)
MIC_GREEN = (40, 180, 80)
MIC_MUTED = (160, 60, 60)


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
    """High quality synthesized theater sound effects."""

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
        # 1. Pop (Puppet grab / Spawn / Click)
        pop_samples = [
            int(math.sin(2 * math.pi * (520 + (1200 - i) * 0.95) * (i / 22050.0)) * max(0.0, 1.0 - (i / 22050.0) / 0.055) * 14000)
            for i in range(1300)
        ]
        self._sounds["pop"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(pop_samples)))

        # 2. Trumpet Fanfare
        fanfare_samples = []
        notes = [523.25, 659.25, 783.99, 1046.50]
        for i in range(11000):
            t = i / 22050.0
            idx = min(len(notes) - 1, int(t / 0.10))
            env = max(0.0, 1.0 - t / 0.46)
            fanfare_samples.append(int(math.sin(2 * math.pi * notes[idx] * t) * env * 15000))
        self._sounds["trumpet"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(fanfare_samples)))

        # 3. Magic Sparkle
        sp_samples = []
        for i in range(8000):
            t = i / 22050.0
            f = 950.0 + math.sin(t * 85) * 500
            env = max(0.0, 1.0 - t / 0.35)
            sp_samples.append(int(math.sin(2 * math.pi * f * t) * env * 13000))
        self._sounds["magic"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(sp_samples)))

        # 4. Grand Applause
        ap_samples = []
        for i in range(22000):
            t = i / 22050.0
            env = min(1.0, t / 0.15) * max(0.0, 1.0 - t / 0.98)
            ap_samples.append(int(random.uniform(-1, 1) * env * 12000))
        self._sounds["applause"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(ap_samples)))

        # 5. Giggle
        gg_samples = []
        for i in range(9000):
            t = i / 22050.0
            f = 640.0 + math.sin(t * 65) * 200
            env = max(0.0, 1.0 - t / 0.38)
            gg_samples.append(int(math.sin(2 * math.pi * f * t) * env * 13500))
        self._sounds["giggle"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(gg_samples)))

        # 6. Mystery Spell
        my_samples = []
        for i in range(10000):
            t = i / 22050.0
            f = 460.0 + (1.0 - t / 0.45) * 240
            env = math.exp(-t * 3.5)
            my_samples.append(int(math.sin(2 * math.pi * f * t) * env * 14000))
        self._sounds["mystery"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(my_samples)))

        # 7. Boing (Jump bounce)
        boing_samples = []
        for i in range(7000):
            t = i / 22050.0
            f = 220.0 + math.sin(t * 50) * 140.0 * (1.0 - t / 0.3)
            env = max(0.0, 1.0 - t / 0.3)
            boing_samples.append(int(math.sin(2 * math.pi * f * t) * env * 14000))
        self._sounds["boing"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(boing_samples)))

    def play(self, name: str) -> None:
        if self._enabled and name in self._sounds:
            try:
                self._sounds[name].play()
            except Exception:
                pass


class MicrophoneRecorder:
    """Non-blocking live microphone audio recorder using Pygame SDL2 Audio."""

    def __init__(self) -> None:
        self.available_devices: list[str] = []
        self.has_hardware = False
        self.enabled = False
        self.is_recording = False
        self._audio_device = None
        self._chunks: list[bytes] = []
        self.current_amplitude = 0.0

        if sdl2_audio is not None:
            try:
                self.available_devices = sdl2_audio.get_audio_device_names(True)
                if self.available_devices:
                    self.has_hardware = True
                    self.enabled = True
            except Exception:
                self.has_hardware = False
                self.enabled = False

    def toggle(self) -> bool:
        if self.has_hardware:
            self.enabled = not self.enabled
        else:
            self.enabled = False
        return self.enabled

    def start_recording(self) -> bool:
        if not self.enabled or not self.has_hardware or sdl2_audio is None:
            self.is_recording = False
            return False

        self._chunks.clear()
        self.current_amplitude = 0.0

        def _callback(device, data: memoryview) -> None:
            raw = bytes(data)
            self._chunks.append(raw)
            # Calculate peak audio amplitude for meter
            try:
                fmt = f"<{len(raw) // 2}h"
                vals = struct.unpack(fmt, raw)
                if vals:
                    peak = max(abs(v) for v in vals) / 32768.0
                    self.current_amplitude = min(1.0, peak * 2.5)
            except Exception:
                self.current_amplitude = 0.3

        try:
            device_name = self.available_devices[0] if self.available_devices else None
            self._audio_device = sdl2_audio.AudioDevice(
                device_name,
                True,  # iscapture
                22050,
                sdl2_audio.AUDIO_S16LSB,
                1,  # mono
                1024,
                0,
                _callback,
            )
            self._audio_device.pause(0)
            self.is_recording = True
            return True
        except Exception:
            self.is_recording = False
            self._audio_device = None
            return False

    def stop_recording(self) -> pygame.mixer.Sound | None:
        if not self.is_recording:
            return None

        self.is_recording = False
        if self._audio_device is not None:
            try:
                self._audio_device.pause(1)
                self._audio_device.close()
            except Exception:
                pass
            self._audio_device = None

        if not self._chunks:
            return None

        try:
            raw_pcm = b"".join(self._chunks)
            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(22050)
                w.writeframes(raw_pcm)
            return pygame.mixer.Sound(io.BytesIO(buf.getvalue()))
        except Exception:
            return None


class Particle:
    def __init__(self, x: float, y: float, symbol: str, color: tuple[int, int, int]) -> None:
        self.x = x
        self.y = y
        self.symbol = symbol
        self.color = color
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2.0, 6.5)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 1.2
        self.life = 1.0
        self.decay = random.uniform(0.025, 0.045)
        self.size = random.randint(18, 30)

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.07
        self.life -= self.decay
        return self.life > 0

    def draw(self, surface: pygame.Surface, typography: GreiaTypography) -> None:
        if self.life > 0:
            sz = max(10, int(self.size * self.life))
            txt_surf = typography.render(self.symbol, FontRole.BODY, sz, self.color)
            surface.blit(txt_surf, (int(self.x) - txt_surf.get_width() // 2, int(self.y) - txt_surf.get_height() // 2))


class AmbientSpark:
    """Ambient floating particles (fireflies, bubbles, stars)."""

    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.reset()

    def reset(self) -> None:
        self.x = random.uniform(140, 880)
        self.y = random.uniform(100, 420)
        self.vx = random.uniform(-0.6, 0.6)
        self.vy = random.uniform(-0.8, -0.2) if self.kind == "ocean" else random.uniform(-0.4, 0.4)
        self.radius = random.uniform(2.5, 5.5)
        self.alpha_phase = random.uniform(0, math.pi * 2)

    def update(self) -> None:
        self.x += self.vx
        self.y += self.vy
        self.alpha_phase += 0.06
        if self.x < 120 or self.x > 900 or self.y < 80 or self.y > 440:
            self.reset()

    def draw(self, surface: pygame.Surface) -> None:
        px = int(self.x)
        py = int(self.y)
        glow = int((math.sin(self.alpha_phase) * 0.5 + 0.5) * 180 + 75)
        if self.kind == "ocean":
            pygame.draw.circle(surface, (180, 230, 255), (px, py), int(self.radius), width=1)
        elif self.kind == "forest":
            pygame.draw.circle(surface, (glow, glow, 120), (px, py), int(self.radius))
        elif self.kind == "castle":
            pygame.draw.circle(surface, (255, glow, 80), (px, py), int(self.radius))
        elif self.kind == "sky":
            pygame.draw.circle(surface, (glow, 220, 255), (px, py), int(self.radius))
        else:  # cottage
            pygame.draw.circle(surface, (255, glow, 140), (px, py), int(self.radius))


class Puppet:
    """Rich interactive marionette on the theatrical stage."""

    def __init__(self, puppet_id: str, name: str, x: float, y: float) -> None:
        self.puppet_id = puppet_id
        self.name = name
        self.x = x
        self.y = y
        self.vx = 0.0
        self.is_held = False
        self.flip_x = False
        self.tilt = 0.0
        self.wobble = random.uniform(0, math.pi * 2)
        self.jump_timer = 0.0
        self.talk_timer = 0.0
        self.width = 110
        self.height = 110

    def jump(self) -> None:
        self.jump_timer = 1.0

    def speak(self) -> None:
        self.talk_timer = 1.0

    def contains(self, px: float, py: float) -> bool:
        return abs(self.x - px) <= 48 and abs(self.y - py) <= 52

    def update(self) -> None:
        self.wobble += 0.05
        if self.jump_timer > 0:
            self.jump_timer -= 0.04
        if self.talk_timer > 0:
            self.talk_timer -= 0.05

        # Smooth tilt recovery
        if not self.is_held:
            self.tilt *= 0.85

    def draw(self, surface: pygame.Surface, sprite: pygame.Surface, typography: GreiaTypography) -> None:
        px = int(self.x)
        py = int(self.y)

        # Stage drop shadow on wooden floor
        pygame.draw.ellipse(surface, (20, 15, 25), (px - 44, 420, 88, 20))

        # Marionette Wooden Control Rod
        rod_bottom = 422
        rod_top = py + 36
        if rod_top < rod_bottom:
            pygame.draw.line(surface, (145, 95, 55), (px, rod_top), (px, rod_bottom), 5)
            pygame.draw.line(surface, (185, 130, 80), (px - 1, rod_top), (px - 1, rod_bottom), 2)

        # Calculate height offset
        draw_y = py
        if self.jump_timer > 0:
            draw_y += int(-math.sin(self.jump_timer * math.pi) * 32.0)
        elif self.talk_timer > 0:
            draw_y += int(-abs(math.sin(self.talk_timer * math.pi * 4.0)) * 14.0)
        elif not self.is_held:
            draw_y += int(math.sin(self.wobble) * 3.5)

        # Marionette Glow when held
        if self.is_held or self.jump_timer > 0:
            halo_surf = pygame.Surface((140, 140), pygame.SRCALPHA)
            pygame.draw.circle(halo_surf, (255, 215, 60, 120), (70, 70), 58)
            surface.blit(halo_surf, (px - 70, draw_y - 70))

        # Render Character Sprite
        spr = sprite
        if self.flip_x:
            spr = pygame.transform.flip(spr, True, False)

        # Tilt rotation if moving
        if abs(self.tilt) > 1.0:
            spr = pygame.transform.rotate(spr, -self.tilt)

        rect = spr.get_rect(center=(px, draw_y))
        surface.blit(spr, rect)


# All 12 Rich Illustrated Puppet Characters
PUPPET_ROSTER = [
    ("lilli", "Lilli"),
    ("principessa", "Principessa"),
    ("draghetto", "Draghetto"),
    ("cavaliere", "Cavaliere"),
    ("leo", "Leo"),
    ("flash", "Flash"),
    ("dani", "Dani"),
    ("tito", "Tito"),
    ("momo", "Momo"),
    ("sirenetta", "Sirenetta"),
    ("mago", "Mago"),
    ("fatina", "Fatina"),
]

BG_CONFIGS = [
    ("castle", "🏰", "Castello"),
    ("ocean", "🌊", "Mare"),
    ("forest", "🌲", "Bosco"),
    ("sky", "☁️", "Cielo"),
    ("cottage", "🏡", "Casetta"),
]

FX_BUTTONS = [
    ("trumpet", "🎺"),
    ("magic", "✨"),
    ("applause", "👏"),
    ("giggle", "😄"),
    ("mystery", "🔮"),
    ("boing", "💥"),
]


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


def render_backdrop_surface(bg_id: str) -> pygame.Surface:
    """Pre-render multi-layered storybook scenery to a static 1024x600 surface."""
    surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))

    if bg_id == "castle":
        # Royal Castle Archway Hall
        for y in range(0, 430, 6):
            col = mix((25, 28, 50), (55, 48, 75), y / 430.0)
            pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 6))

        # Stone Wall Pillars
        for px in (180, 400, 624, 844):
            pygame.draw.rect(surf, (45, 40, 60), (px - 20, 60, 40, 370))
            pygame.draw.rect(surf, (60, 52, 78), (px - 14, 60, 28, 370))

        # Grand Stained Glass Gothic Arched Windows
        for wx in (290, 512, 734):
            # Window glow
            pygame.draw.rect(surf, (255, 220, 130), (wx - 42, 100, 84, 150), border_radius=42)
            pygame.draw.rect(surf, (30, 25, 40), (wx - 42, 100, 84, 150), width=4, border_radius=42)
            # Window panes
            pygame.draw.line(surf, (30, 25, 40), (wx, 100), (wx, 250), 3)
            pygame.draw.line(surf, (30, 25, 40), (wx - 42, 175), (wx + 42, 175), 3)

        # Hanging Gold Chandeliers with Warm Candle Flames
        for cx in (290, 512, 734):
            pygame.draw.line(surf, (215, 170, 40), (cx, 40), (cx, 85), 3)
            pygame.draw.ellipse(surf, (255, 215, 60), (cx - 24, 80, 48, 12))
            for fx in (cx - 18, cx, cx + 18):
                pygame.draw.circle(surf, (255, 240, 160), (fx, 75), 5)
                pygame.draw.circle(surf, (245, 130, 30), (fx, 73), 3)

    elif bg_id == "ocean":
        # Underwater Sunlit Deep Sea
        for y in range(0, 430, 6):
            col = mix((12, 45, 95), (20, 115, 170), y / 430.0)
            pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 6))

        # Sunbeam caustics from water surface
        for rx, rw in ((240, 60), (450, 90), (680, 75)):
            beam_poly = [(rx, 0), (rx + rw, 0), (rx + rw + 70, 430), (rx - 40, 430)]
            beam_surf = pygame.Surface((REFERENCE_WIDTH, 430), pygame.SRCALPHA)
            pygame.draw.polygon(beam_surf, (255, 255, 255, 22), beam_poly)
            surf.blit(beam_surf, (0, 0))

        # Swaying Emerald Kelp Forests
        for kx in (160, 210, 800, 860):
            for seg in range(7):
                ky = 430 - seg * 45
                kx_off = int(math.sin(seg * 1.2) * 18)
                pygame.draw.ellipse(surf, (15, 110, 75), (kx + kx_off - 12, ky - 30, 24, 38))

        # Colorful Coral Reef Garden
        for cx, cr, col in ((280, 55, (244, 114, 182)), (340, 45, (251, 146, 60)), (670, 60, (168, 85, 247)), (740, 48, (234, 88, 12))):
            pygame.draw.circle(surf, col, (cx, 420), cr)

        # Sunken Treasure Chest
        pygame.draw.rect(surf, (120, 70, 30), (480, 390, 64, 36), border_radius=6)
        pygame.draw.rect(surf, STAGE_GOLD, (480, 390, 64, 36), width=3, border_radius=6)
        pygame.draw.circle(surf, STAGE_GOLD, (512, 408), 5)

    elif bg_id == "forest":
        # Enchanted Twilight Oak Forest
        for y in range(0, 430, 6):
            col = mix((16, 32, 38), (28, 72, 60), y / 430.0)
            pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 6))

        # Giant Glowing Moon
        pygame.draw.circle(surf, (255, 250, 210), (512, 115), 52)
        pygame.draw.circle(surf, (255, 255, 240), (512, 115), 45)

        # Ancient Giant Oak Trunks & Canopy
        pygame.draw.circle(surf, (18, 52, 42), (200, 340), 170)
        pygame.draw.circle(surf, (18, 52, 42), (824, 340), 170)
        pygame.draw.circle(surf, (28, 85, 65), (512, 220), 120)

        # Luminous Magical Mushrooms
        for mx, mcol in ((300, (236, 72, 153)), (340, (45, 212, 191)), (680, (250, 204, 21)), (720, (192, 132, 252))):
            pygame.draw.rect(surf, (255, 245, 230), (mx - 4, 395, 8, 30), border_radius=3)
            pygame.draw.ellipse(surf, mcol, (mx - 18, 385, 36, 20))
            pygame.draw.circle(surf, WHITE, (mx - 6, 392), 3)
            pygame.draw.circle(surf, WHITE, (mx + 6, 392), 3)

    elif bg_id == "sky":
        # Cosmic Dream & Starry Cloud Realm
        for y in range(0, 430, 6):
            col = mix((35, 15, 65), (95, 45, 125), y / 430.0)
            pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 6))

        # Golden Crescent Moon
        pygame.draw.circle(surf, (255, 225, 90), (740, 110), 46)
        pygame.draw.circle(surf, (45, 20, 75), (760, 100), 40)

        # Distant Planet with Rings
        pygame.draw.circle(surf, (251, 146, 60), (280, 120), 32)
        pygame.draw.ellipse(surf, (254, 215, 170), (230, 124, 100, 18), width=3)

        # Fluffy Cloud Islands
        for cx in (220, 512, 800):
            for ox, oy, r in ((-45, 20, 36), (0, 0, 48), (45, 20, 36)):
                pygame.draw.circle(surf, (245, 235, 255), (cx + ox, 360 + oy), r)

    else:  # cottage
        # Cozy Storybook Cottage at Sunset
        for y in range(0, 430, 6):
            col = mix((245, 130, 90), (255, 215, 140), y / 430.0)
            pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 6))

        # Distant Sunset Rolling Hills
        pygame.draw.circle(surf, (105, 145, 80), (300, 460), 220)
        pygame.draw.circle(surf, (85, 125, 65), (750, 460), 240)

        # Timber Cottage Body
        pygame.draw.rect(surf, (165, 105, 65), (430, 240, 164, 185), border_radius=6)
        # Stone Chimney with Smoke
        pygame.draw.rect(surf, (120, 115, 125), (550, 160, 28, 80))
        for s_idx, (sx, sy, sr) in enumerate(((564, 145, 12), (572, 120, 18), (565, 90, 24))):
            pygame.draw.circle(surf, (255, 255, 255, 160), (sx, sy), sr)
        # Cottage Roof
        pygame.draw.polygon(surf, (185, 45, 45), [(410, 240), (512, 155), (614, 240)])
        # Glowing Warm Windows
        pygame.draw.rect(surf, (255, 230, 120), (455, 270, 40, 40), border_radius=4)
        pygame.draw.rect(surf, (80, 45, 20), (455, 270, 40, 40), width=3, border_radius=4)
        pygame.draw.line(surf, (80, 45, 20), (475, 270), (475, 310), 2)
        pygame.draw.line(surf, (80, 45, 20), (455, 290), (495, 290), 2)

    # Polished Stage Wooden Floor
    for y in range(430, 500, 6):
        col = mix(STAGE_WOOD_TOP, STAGE_WOOD_BOTTOM, (y - 430) / 70.0)
        pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 6))

    # Stage Floor Planks Lines
    for px in range(0, REFERENCE_WIDTH + 1, 90):
        pygame.draw.line(surf, (75, 40, 15), (px, 430), (px, 500), 2)

    return surf


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
    mic_recorder = MicrophoneRecorder()

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

    # Pre-load Puppet Sprites
    puppet_sprites: dict[str, pygame.Surface] = {}
    runtime_dir = package_root / "assets" / "runtime"
    for p_id, _ in PUPPET_ROSTER:
        png_file = runtime_dir / f"puppet_{p_id}.png"
        if png_file.is_file():
            img = pygame.image.load(str(png_file)).convert_alpha()
            puppet_sprites[p_id] = pygame.transform.smoothscale(img, (110, 110))
        else:
            # Fallback placeholder surface
            fallback = pygame.Surface((110, 110), pygame.SRCALPHA)
            pygame.draw.circle(fallback, STAGE_GOLD, (55, 55), 48)
            puppet_sprites[p_id] = fallback

    # Pre-render all 5 Backdrops
    cached_backdrops: dict[str, pygame.Surface] = {
        bg_id: render_backdrop_surface(bg_id) for bg_id, _, _ in BG_CONFIGS
    }

    active_bg = "castle"
    if storage is not None:
        try:
            saved = storage.kv_get(STORAGE_KEY, {})
            if isinstance(saved, dict):
                saved_bg = str(saved.get("backdrop", "castle"))
                if saved_bg in cached_backdrops:
                    active_bg = saved_bg
        except Exception:
            pass

    # Puppets on Stage (Initial 2 actors)
    puppets_on_stage: list[Puppet] = [
        Puppet("lilli", "Lilli", 360, 280),
        Puppet("draghetto", "Draghetto", 620, 280),
    ]
    puppets_on_stage[1].flip_x = True

    dragging_puppet: Puppet | None = None
    drag_prev_x = 0.0

    # Recording / Narration / Playback Engine
    is_recording = False
    is_playing_show = False
    record_start_time = 0.0
    playback_start_time = 0.0
    recorded_frames: list[tuple[float, list[tuple[str, float, float, bool, bool]]]] = []
    recorded_sfx_events: list[tuple[float, str]] = []
    recorded_narration_sound: pygame.mixer.Sound | None = None

    # Ambient Sparkles & Particles
    particles: list[Particle] = []
    ambient_sparks: list[AmbientSpark] = [AmbientSpark(active_bg) for _ in range(16)]

    # Feedback Banner
    feedback_text = ""
    feedback_timer = 0.0

    # Puppet Tray Pagination (6 puppets per page)
    tray_page = 0
    puppets_per_page = 6
    total_tray_pages = (len(PUPPET_ROSTER) + puppets_per_page - 1) // puppets_per_page

    # Top Control Buttons Geometry (Clear of Home at x < 130)
    bg_btn_rect = pygame.Rect(140, 16, 140, 52)
    mic_btn_rect = pygame.Rect(290, 16, 115, 52)
    rec_btn_rect = pygame.Rect(415, 16, 155, 52)
    play_btn_rect = pygame.Rect(580, 16, 165, 52)
    clear_btn_rect = pygame.Rect(755, 16, 68, 52)

    # Tray Paging Buttons
    tray_prev_rect = pygame.Rect(40, 522, 54, 54)
    tray_next_rect = pygame.Rect(930, 522, 54, 54)

    running = True
    ready_published = False

    while running and not activity_stop_requested():
        now = time.time()

        # Capture Frame if Recording
        if is_recording:
            elapsed = now - record_start_time
            if elapsed >= MAX_RECORDING_SECONDS:
                # Stop recording on duration timeout
                is_recording = False
                recorded_narration_sound = mic_recorder.stop_recording()
                sounds.play("trumpet")
                feedback_text = "Spettacolo Registrato! 🎬✨" if active_locale == "it" else "Show Recorded! 🎬✨"
                feedback_timer = 3.5
            else:
                frame_data = [(p.puppet_id, p.x, p.y, p.flip_x, p.jump_timer > 0) for p in puppets_on_stage]
                recorded_frames.append((elapsed, frame_data))

        # Playback Choreography Logic
        if is_playing_show:
            elapsed = now - playback_start_time
            if recorded_frames and elapsed < recorded_frames[-1][0]:
                for t_stamp, p_data in recorded_frames:
                    if t_stamp >= elapsed:
                        for p_id, px, py, p_flip, is_jmp in p_data:
                            for staged in puppets_on_stage:
                                if staged.puppet_id == p_id:
                                    staged.x = px
                                    staged.y = py
                                    staged.flip_x = p_flip
                                    if is_jmp:
                                        staged.speak()
                        break
            else:
                # Demo show choreography if no recording or playback completed
                if not recorded_frames:
                    t = elapsed
                    if t < 6.0:
                        if len(puppets_on_stage) >= 2:
                            puppets_on_stage[0].x = 360 + math.sin(t * 3.0) * 130.0
                            puppets_on_stage[0].y = 280 + math.sin(t * 6.0) * 25.0
                            puppets_on_stage[0].flip_x = (math.cos(t * 3.0) < 0)
                            puppets_on_stage[0].speak()

                            puppets_on_stage[1].x = 620 - math.sin(t * 3.0) * 130.0
                            puppets_on_stage[1].y = 280 + math.cos(t * 5.0) * 25.0
                            puppets_on_stage[1].flip_x = (math.cos(t * 3.0) >= 0)
                            puppets_on_stage[1].speak()

                        if random.random() < 0.25:
                            particles.append(Particle(random.uniform(300, 720), random.uniform(180, 360), "✨", STAGE_GOLD))
                    else:
                        is_playing_show = False
                        sounds.play("applause")
                        feedback_text = "Gran Finale! 👏🌟" if active_locale == "it" else "Grand Finale! 👏🌟"
                        feedback_timer = 3.5
                else:
                    is_playing_show = False
                    sounds.play("applause")
                    feedback_text = "Fine dello Spettacolo! 👏✨" if active_locale == "it" else "Show Finale! 👏✨"
                    feedback_timer = 3.5

        # Process Input Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    sounds.play("applause")
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
                    # Check puppet grab on stage
                    for p in reversed(puppets_on_stage):
                        if p.contains(lx, ly):
                            p.is_held = True
                            p.jump()
                            dragging_puppet = p
                            drag_prev_x = lx
                            sounds.play("pop")
                            break
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if is_home_clicked(screen, event.pos):
                    running = False
                    continue
                if dragging_puppet is not None:
                    dragging_puppet.is_held = False
                    dragging_puppet = None

                if not _is_safe_point(screen, event.pos):
                    continue
                logical = canvas.pointer(event.pos)
                if logical is not None:
                    lx, ly = logical

                    # 1. Backdrop Selector Button (Cycle through 5 backdrops)
                    if bg_btn_rect.collidepoint(lx, ly):
                        bg_ids = [b[0] for b in BG_CONFIGS]
                        cur_idx = bg_ids.index(active_bg) if active_bg in bg_ids else 0
                        active_bg = bg_ids[(cur_idx + 1) % len(bg_ids)]
                        sounds.play("magic")
                        for s in ambient_sparks:
                            s.kind = active_bg
                        for _ in range(16):
                            particles.append(Particle(lx, ly, "✨", STAGE_GOLD))
                        safe_emit("scene.created", f"bg-{time.time()}", payload={"backdrop": active_bg})
                        continue

                    # 2. Microphone Toggle Button
                    if mic_btn_rect.collidepoint(lx, ly):
                        mic_enabled = mic_recorder.toggle()
                        sounds.play("pop")
                        if mic_enabled:
                            feedback_text = "🎙️ Microfono Attivo" if active_locale == "it" else "🎙️ Mic ON"
                        else:
                            feedback_text = "🔇 Microfono Spento" if active_locale == "it" else "🔇 Mic Muted"
                        feedback_timer = 2.0
                        continue

                    # 3. Record Button (🔴 Registra / ⏹️ Stop REC)
                    if rec_btn_rect.collidepoint(lx, ly):
                        if not is_recording:
                            is_recording = True
                            is_playing_show = False
                            recorded_frames.clear()
                            recorded_sfx_events.clear()
                            record_start_time = now
                            mic_recorder.start_recording()
                            sounds.play("pop")
                            feedback_text = "🔴 Racconta la tua storia!" if active_locale == "it" else "🔴 Narrate your story!"
                            feedback_timer = 3.0
                            safe_emit("story.recorded", f"rec-{time.time()}")
                        else:
                            is_recording = False
                            recorded_narration_sound = mic_recorder.stop_recording()
                            sounds.play("trumpet")
                            feedback_text = "🎬 Spettacolo Registrato!" if active_locale == "it" else "🎬 Show Recorded!"
                            feedback_timer = 3.0
                            for _ in range(25):
                                particles.append(Particle(512, 280, "✨", STAGE_GOLD))
                        continue

                    # 4. Play Show Button (▶️ Spettacolo)
                    if play_btn_rect.collidepoint(lx, ly):
                        is_recording = False
                        if mic_recorder.is_recording:
                            recorded_narration_sound = mic_recorder.stop_recording()
                        is_playing_show = True
                        playback_start_time = now
                        sounds.play("trumpet")

                        # If voice narration was recorded, play it!
                        if recorded_narration_sound is not None:
                            try:
                                recorded_narration_sound.play()
                            except Exception:
                                pass

                        feedback_text = "🎭 In Scena! Sipario!" if active_locale == "it" else "🎭 Curtains Up!"
                        feedback_timer = 3.0

                        # If stage was empty, summon 3 star actors for the show
                        if len(puppets_on_stage) == 0:
                            puppets_on_stage.append(Puppet("principessa", "Principessa", 340, 280))
                            puppets_on_stage.append(Puppet("draghetto", "Draghetto", 512, 280))
                            puppets_on_stage.append(Puppet("lilli", "Lilli", 680, 280))
                            puppets_on_stage[1].flip_x = True

                        for p in puppets_on_stage:
                            p.jump()

                        safe_emit("story.played", f"show-{time.time()}")
                        for _ in range(30):
                            particles.append(Particle(512, 280, "🎉", STAGE_GOLD))
                            particles.append(Particle(512, 280, "✨", (255, 130, 170)))
                        continue

                    # 5. Clear Stage Button (🗑️)
                    if clear_btn_rect.collidepoint(lx, ly):
                        puppets_on_stage.clear()
                        sounds.play("pop")
                        continue

                    # 6. Magic Sound FX Buttons (Right Sidebar x=915..985)
                    for f_idx, (fx_id, fx_sym) in enumerate(FX_BUTTONS):
                        fy = 100 + f_idx * 56
                        if 915 <= lx <= 985 and fy <= ly <= fy + 48:
                            sounds.play(fx_id)
                            if is_recording:
                                recorded_sfx_events.append((now - record_start_time, fx_id))
                            for p in puppets_on_stage:
                                p.speak()
                            for _ in range(12):
                                particles.append(Particle(lx, ly, fx_sym, STAGE_GOLD))
                            break

                    # 7. Puppet Tray Pagination Buttons (◀ and ▶)
                    if tray_prev_rect.collidepoint(lx, ly):
                        tray_page = (tray_page - 1) % total_tray_pages
                        sounds.play("pop")
                        continue
                    if tray_next_rect.collidepoint(lx, ly):
                        tray_page = (tray_page + 1) % total_tray_pages
                        sounds.play("pop")
                        continue

                    # 8. Puppet Tray Selection (Spawn on stage)
                    page_puppets = PUPPET_ROSTER[tray_page * puppets_per_page : (tray_page + 1) * puppets_per_page]
                    for p_idx, (p_id, p_name) in enumerate(page_puppets):
                        card_x = 110 + p_idx * 135
                        card_rect = pygame.Rect(card_x, 508, 120, 84)
                        if card_rect.collidepoint(lx, ly):
                            sounds.play("pop")
                            if len(puppets_on_stage) < 5:
                                new_x = random.uniform(320, 700)
                                new_p = Puppet(p_id, p_name, new_x, 280)
                                new_p.jump()
                                puppets_on_stage.append(new_p)
                                for _ in range(16):
                                    particles.append(Particle(new_x, 280, "✨", STAGE_GOLD))
                                safe_emit("scene.created", f"puppet-{time.time()}", payload={"puppet": p_id})
                            break

        # Dragging puppet motion & tilt physics
        if dragging_puppet is not None and pygame.mouse.get_focused():
            mpos = pygame.mouse.get_pos()
            if _is_safe_point(screen, mpos):
                plog = canvas.pointer(mpos)
                if plog is not None:
                    dx = plog[0] - drag_prev_x
                    drag_prev_x = plog[0]
                    dragging_puppet.x = max(160.0, min(860.0, plog[0]))
                    dragging_puppet.y = max(140.0, min(390.0, plog[1]))
                    # Horizontal facing direction
                    if dx < -2.0:
                        dragging_puppet.flip_x = True
                        dragging_puppet.tilt = max(-18.0, dragging_puppet.tilt - 3.5)
                    elif dx > 2.0:
                        dragging_puppet.flip_x = False
                        dragging_puppet.tilt = min(18.0, dragging_puppet.tilt + 3.5)

        # State updates
        for p in puppets_on_stage:
            p.update()
        for s in ambient_sparks:
            s.update()
        particles = [p for p in particles if p.update()]

        if feedback_timer > 0:
            feedback_timer -= 0.035
        else:
            feedback_text = ""

        # --- RENDERING ---
        surf = canvas.surface

        # 1. Blit Pre-Rendered Scenery Backdrop (0ms per-frame overhead!)
        surf.blit(cached_backdrops[active_bg], (0, 0))

        # 2. Ambient Particles
        for s in ambient_sparks:
            s.draw(surf)

        # 3. Puppets on Stage
        for p in puppets_on_stage:
            spr = puppet_sprites.get(p.puppet_id, puppet_sprites["lilli"])
            p.draw(surf, spr, typography)

        # 4. Proscenium Stage Frame & Velvet Curtains
        # Side Curtains
        pygame.draw.polygon(surf, STAGE_CURTAIN_DARK, [(0, 0), (130, 0), (70, 440), (0, 440)])
        pygame.draw.polygon(surf, STAGE_CURTAIN, [(0, 0), (110, 0), (55, 430), (0, 430)])
        pygame.draw.polygon(surf, STAGE_CURTAIN_LIGHT, [(0, 0), (70, 0), (35, 420), (0, 420)])

        pygame.draw.polygon(surf, STAGE_CURTAIN_DARK, [(REFERENCE_WIDTH, 0), (REFERENCE_WIDTH - 130, 0), (REFERENCE_WIDTH - 70, 440), (REFERENCE_WIDTH, 440)])
        pygame.draw.polygon(surf, STAGE_CURTAIN, [(REFERENCE_WIDTH, 0), (REFERENCE_WIDTH - 110, 0), (REFERENCE_WIDTH - 55, 430), (REFERENCE_WIDTH, 430)])
        pygame.draw.polygon(surf, STAGE_CURTAIN_LIGHT, [(REFERENCE_WIDTH, 0), (REFERENCE_WIDTH - 70, 0), (REFERENCE_WIDTH - 35, 420), (REFERENCE_WIDTH, 420)])

        # Top Ornate Valance Swags
        for vx in range(120, 890, 110):
            pygame.draw.circle(surf, STAGE_CURTAIN_DARK, (vx + 55, 24), 68)
            pygame.draw.circle(surf, STAGE_CURTAIN, (vx + 55, 24), 62)
            pygame.draw.circle(surf, STAGE_GOLD, (vx + 55, 24), 62, width=2)
            # Golden fringe tassel
            pygame.draw.circle(surf, STAGE_GOLD, (vx + 55, 86), 4)

        # Top Gold Proscenium Bar
        pygame.draw.rect(surf, (60, 40, 15), (0, 0, REFERENCE_WIDTH, 14))
        pygame.draw.rect(surf, STAGE_GOLD, (0, 10, REFERENCE_WIDTH, 4))

        # 5. Magic Particles
        for p in particles:
            p.draw(surf, typography)

        # 6. Top Stage Toolbar Controls (Clear of Home at x < 130)
        # Backdrop button (🏰 Scena)
        pygame.draw.rect(surf, (255, 250, 240), bg_btn_rect, border_radius=14)
        pygame.draw.rect(surf, (61, 44, 31), bg_btn_rect, width=2, border_radius=14)
        cur_bg_icon = next(b[1] for b in BG_CONFIGS if b[0] == active_bg)
        bg_lbl = f"{cur_bg_icon} Scena" if active_locale == "it" else f"{cur_bg_icon} Scene"
        bg_surf = typography.render(bg_lbl, FontRole.TITLE, 17, DARK_TEXT)
        surf.blit(bg_surf, (bg_btn_rect.centerx - bg_surf.get_width() // 2, bg_btn_rect.centery - bg_surf.get_height() // 2))

        # Microphone Toggle button (🎙️ ON / 🔇 OFF)
        mic_col = (220, 255, 225) if mic_recorder.enabled else (255, 225, 225)
        mic_border = MIC_GREEN if mic_recorder.enabled else MIC_MUTED
        pygame.draw.rect(surf, mic_col, mic_btn_rect, border_radius=14)
        pygame.draw.rect(surf, mic_border, mic_btn_rect, width=3 if mic_recorder.enabled else 2, border_radius=14)
        mic_txt = "🎙️ ON" if mic_recorder.enabled else "🔇 OFF"
        mic_surf = typography.render(mic_txt, FontRole.TITLE, 17, (30, 120, 50) if mic_recorder.enabled else (160, 40, 40))
        surf.blit(mic_surf, (mic_btn_rect.centerx - mic_surf.get_width() // 2, mic_btn_rect.centery - mic_surf.get_height() // 2))

        # Record Button (🔴 Registra / ⏹️ Stop REC)
        rec_col = (255, 185, 185) if is_recording else (255, 250, 240)
        pygame.draw.rect(surf, rec_col, rec_btn_rect, border_radius=14)
        pygame.draw.rect(surf, REC_RED if is_recording else (61, 44, 31), rec_btn_rect, width=3 if is_recording else 2, border_radius=14)
        rec_txt = "⏹️ Stop REC" if is_recording else ("🔴 Registra" if active_locale == "it" else "🔴 Record")
        rec_surf = typography.render(rec_txt, FontRole.TITLE, 17, REC_RED if is_recording else DARK_TEXT)
        surf.blit(rec_surf, (rec_btn_rect.centerx - rec_surf.get_width() // 2, rec_btn_rect.centery - rec_surf.get_height() // 2))

        # Play Show Button (▶️ Spettacolo)
        play_col = (220, 255, 220) if is_playing_show else (255, 250, 240)
        pygame.draw.rect(surf, play_col, play_btn_rect, border_radius=14)
        pygame.draw.rect(surf, (40, 160, 60) if is_playing_show else (61, 44, 31), play_btn_rect, width=3 if is_playing_show else 2, border_radius=14)
        play_txt = ("🎭 In Scena!" if active_locale == "it" else "🎭 On Stage!") if is_playing_show else ("▶️ Spettacolo" if active_locale == "it" else "▶️ Play Show")
        play_surf = typography.render(play_txt, FontRole.TITLE, 17, (35, 135, 45) if is_playing_show else DARK_TEXT)
        surf.blit(play_surf, (play_btn_rect.centerx - play_surf.get_width() // 2, play_btn_rect.centery - play_surf.get_height() // 2))

        # Clear button (🗑️)
        pygame.draw.rect(surf, (255, 250, 240), clear_btn_rect, border_radius=14)
        pygame.draw.rect(surf, (61, 44, 31), clear_btn_rect, width=2, border_radius=14)
        clr_surf = typography.render("🗑️", FontRole.TITLE, 22, DARK_TEXT)
        surf.blit(clr_surf, (clear_btn_rect.centerx - clr_surf.get_width() // 2, clear_btn_rect.centery - clr_surf.get_height() // 2))

        # 7. Live Audio Waveform Meter during Recording
        if is_recording:
            elapsed_sec = int(now - record_start_time)
            meter_x = 425
            meter_y = 74
            # Draw 5 bouncing audio wave bars
            amp = mic_recorder.current_amplitude if mic_recorder.enabled else (math.sin(now * 8.0) * 0.4 + 0.5)
            for bar_idx in range(5):
                bar_h = max(4, int((math.sin(now * 12 + bar_idx) * 0.5 + 0.5) * amp * 18 + 4))
                pygame.draw.rect(surf, REC_RED, (meter_x + bar_idx * 6, meter_y + (18 - bar_h) // 2, 4, bar_h), border_radius=2)
            time_txt = f"{elapsed_sec}s / {int(MAX_RECORDING_SECONDS)}s"
            t_surf = typography.render(time_txt, FontRole.CONTROL, 12, REC_RED)
            surf.blit(t_surf, (meter_x + 36, meter_y + 2))

        # 8. Magic Sound FX Sidebar (Right side x=915..985)
        for f_idx, (fx_id, fx_sym) in enumerate(FX_BUTTONS):
            fy = 100 + f_idx * 56
            fx_rect = pygame.Rect(915, fy, 70, 48)
            pygame.draw.rect(surf, (255, 250, 240), fx_rect, border_radius=14)
            pygame.draw.rect(surf, STAGE_GOLD, fx_rect, width=2, border_radius=14)
            fx_s = typography.render(fx_sym, FontRole.DISPLAY, 24, DARK_TEXT)
            surf.blit(fx_s, (fx_rect.centerx - fx_s.get_width() // 2, fx_rect.centery - fx_s.get_height() // 2))

        # 9. Bottom Puppet Tray Toolbar (y=500..600)
        pygame.draw.rect(surf, (30, 24, 40), (0, 500, REFERENCE_WIDTH, 100))
        pygame.draw.rect(surf, STAGE_GOLD, (0, 500, REFERENCE_WIDTH, 4))

        # Tray Prev/Next Buttons with vector arrow triangles
        pygame.draw.rect(surf, (255, 250, 240), tray_prev_rect, border_radius=12)
        pygame.draw.rect(surf, STAGE_GOLD, tray_prev_rect, width=2, border_radius=12)
        cx, cy = tray_prev_rect.center
        pygame.draw.polygon(surf, (61, 44, 31), [(cx - 8, cy), (cx + 6, cy - 10), (cx + 6, cy + 10)])

        pygame.draw.rect(surf, (255, 250, 240), tray_next_rect, border_radius=12)
        pygame.draw.rect(surf, STAGE_GOLD, tray_next_rect, width=2, border_radius=12)
        cx, cy = tray_next_rect.center
        pygame.draw.polygon(surf, (61, 44, 31), [(cx + 8, cy), (cx - 6, cy - 10), (cx - 6, cy + 10)])

        # 6 Large Puppet Selection Cards on current page
        page_puppets = PUPPET_ROSTER[tray_page * puppets_per_page : (tray_page + 1) * puppets_per_page]
        for p_idx, (p_id, p_name) in enumerate(page_puppets):
            card_x = 110 + p_idx * 135
            card_rect = pygame.Rect(card_x, 508, 120, 84)
            pygame.draw.rect(surf, (255, 250, 240), card_rect, border_radius=14)
            pygame.draw.rect(surf, (61, 44, 31), card_rect, width=2, border_radius=14)

            # Draw Thumbnail Sprite
            spr = puppet_sprites.get(p_id, puppet_sprites["lilli"])
            thumb = pygame.transform.smoothscale(spr, (52, 52))
            surf.blit(thumb, (card_rect.centerx - 26, card_rect.y + 6))

            # Puppet Localized Name
            name_s = typography.render(p_name, FontRole.CONTROL, 11, DARK_TEXT)
            surf.blit(name_s, (card_rect.centerx - name_s.get_width() // 2, card_rect.y + 63))

        # 10. Feedback Banner
        if feedback_text:
            fb_surf = typography.render(feedback_text, FontRole.TITLE, 20, STAGE_GOLD)
            fb_bg = pygame.Rect(REFERENCE_WIDTH // 2 - fb_surf.get_width() // 2 - 20, 100, fb_surf.get_width() + 40, 42)
            pygame.draw.rect(surf, (20, 16, 32), fb_bg, border_radius=12)
            pygame.draw.rect(surf, STAGE_GOLD, fb_bg, width=2, border_radius=12)
            surf.blit(fb_surf, (REFERENCE_WIDTH // 2 - fb_surf.get_width() // 2, 108))

        canvas.present(clear=theme.background)
        pygame.display.flip()
        if not ready_published:
            mark_activity_ready()
            ready_published = True

        clock.tick(30)

    # Clean up audio recorder on exit
    if mic_recorder.is_recording:
        mic_recorder.stop_recording()

    if storage is not None:
        try:
            storage.kv_set(STORAGE_KEY, {"backdrop": active_bg})
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
