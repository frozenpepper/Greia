from __future__ import annotations

import io
import math
from pathlib import Path
import random
import struct
import time
import wave

import pygame

from greia_platform.child_text import display_text
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


REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
STORAGE_KEY = "sillabe_magiche.progress.v1"

# Magical Meadow & Workshop Palette
BG_SKY_TOP = (235, 245, 255)
BG_SKY_BOTTOM = (215, 235, 250)
BG_GRASS_BACK = (160, 220, 170)
BG_GRASS_FRONT = (120, 200, 140)
CARD_BG = (255, 254, 250)
CARD_BORDER = (55, 45, 70)
DARK_TEXT = (45, 35, 55)
LIGHT_TEXT = (255, 255, 255)
GOLD = (255, 200, 40)
GOLD_BORDER = (210, 150, 15)
GOLD_LIGHT = (255, 235, 150)
CORAL = (255, 105, 125)
SKY_BLUE = (65, 175, 255)
MINT_GREEN = (75, 210, 135)
LAVENDER = (170, 130, 245)
PEACH = (255, 155, 95)
ROSE_PINK = (255, 135, 175)
AMBER = (255, 175, 60)
SHADOW_COLOR = (35, 25, 55, 45)

SYLLABLE_COLORS = [
    ((255, 120, 140), (255, 180, 195)),  # Coral / Rose
    ((65, 175, 255), (155, 220, 255)),   # Sky Blue
    ((75, 210, 140), (165, 245, 200)),   # Mint Green
    ((255, 170, 70), (255, 215, 145)),   # Sunny Amber
    ((170, 125, 245), (215, 185, 255)),  # Lavender
    ((255, 135, 190), (255, 195, 225)),  # Magenta / Pink
]

CONSONANTS_IT = ["B", "C", "D", "F", "G", "L", "M", "N", "P", "R", "S", "T", "V", "Z"]
VOWELS_IT = ["A", "E", "I", "O", "U"]

WORDS_DATA_IT = [
    ("CASA", ("CA", "SA"), "🏠", "casa"),
    ("SOLE", ("SO", "LE"), "☀️", "sole"),
    ("LUNA", ("LU", "NA"), "🌙", "luna"),
    ("MELA", ("ME", "LA"), "🍎", "mela"),
    ("RANA", ("RA", "NA"), "🐸", "rana"),
    ("TOPO", ("TO", "PO"), "🐭", "topo"),
    ("MANO", ("MA", "NO"), "🖐️", "mano"),
    ("PANE", ("PA", "NE"), "🥖", "pane"),
    ("NAVE", ("NA", "VE"), "🚢", "nave"),
    ("VASO", ("VA", "SO"), "🏺", "vaso"),
    ("PERA", ("PE", "RA"), "🍐", "pera"),
    ("MURO", ("MU", "RO"), "🧱", "muro"),
    ("LUPO", ("LU", "PO"), "🐺", "lupo"),
    ("FILO", ("FI", "LO"), "🧵", "filo"),
    ("ROSA", ("RO", "SA"), "🌹", "rosa"),
    ("FARO", ("FA", "RO"), "🗼", "faro"),
    ("GUFO", ("GU", "FO"), "🦉", "gufo"),
    ("MOTO", ("MO", "TO"), "🏍️", "moto"),
    ("LAMA", ("LA", "MA"), "🦙", "lama"),
    ("PINO", ("PI", "NO"), "🌲", "pino"),
    ("RETE", ("RE", "TE"), "🥅", "rete"),
    ("SUCO", ("SU", "CO"), "🧃", "suco"),
    ("VELA", ("VE", "LA"), "⛵", "vela"),
    ("DADO", ("DA", "DO"), "🎲", "dado"),
    ("FATA", ("FA", "TA"), "🧚", "fata"),
    ("CANE", ("CA", "NE"), "🐶", "cane"),
    ("PIZZA", ("PI", "ZZA"), "🍕", "pizza"),
]

WORDS_DATA_EN = [
    ("BABY", ("BA", "BY"), "👶", "baby"),
    ("TIGER", ("TI", "GER"), "🐯", "tiger"),
    ("ROBOT", ("RO", "BOT"), "🤖", "robot"),
    ("LEMON", ("LE", "MON"), "🍋", "lemon"),
    ("PAPER", ("PA", "PER"), "📄", "paper"),
    ("WATER", ("WA", "TER"), "💧", "water"),
    ("MUSIC", ("MU", "SIC"), "🎵", "music"),
    ("RABBIT", ("RAB", "BIT"), "🐰", "rabbit"),
    ("PIZZA", ("PIZ", "ZA"), "🍕", "pizza"),
    ("ZEBRA", ("ZE", "BRA"), "🦓", "zebra"),
    ("PANDA", ("PAN", "DA"), "🐼", "panda"),
    ("ROCKET", ("ROCK", "ET"), "🚀", "rocket"),
    ("SUNNY", ("SUN", "NY"), "☀️", "sunny"),
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
        self._audio_dir = Path(__file__).resolve().parent / "assets" / "audio"
        self._enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self._init_synth_effects()
            self._enabled = True
        except Exception:
            self._enabled = False

    def _init_synth_effects(self) -> None:
        # Pop Sound (Bubbly tap)
        pop_samples = [
            int(math.sin(2 * math.pi * (500 + (1000 - i) * 0.8) * (i / 22050.0)) * max(0.0, 1.0 - (i / 22050.0) / 0.05) * 14000)
            for i in range(1200)
        ]
        self._sounds["pop"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(pop_samples)))

        # Chime (Upward 4 notes)
        chime_samples = []
        for i in range(6000):
            t = i / 22050.0
            f = 523.25 if t < 0.07 else (659.25 if t < 0.14 else (783.99 if t < 0.21 else 1046.50))
            env = max(0.0, 1.0 - t / 0.28)
            chime_samples.append(int(math.sin(2 * math.pi * f * t) * env * 12000))
        self._sounds["chime"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(chime_samples)))

        # Fanfare (Victory flourish)
        fanfare_samples = []
        notes = [523.25, 659.25, 783.99, 1046.50, 1318.51]
        for i in range(12000):
            t = i / 22050.0
            idx = min(len(notes) - 1, int(t / 0.08))
            f = notes[idx]
            env = max(0.0, 1.0 - t / 0.54)
            fanfare_samples.append(int(math.sin(2 * math.pi * f * t) * env * 14000))
        self._sounds["fanfare"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(fanfare_samples)))

        # Wobble (Spring / oops)
        wobble_samples = [
            int(math.sin(2 * math.pi * (320 + math.sin(i * 0.05) * 45) * (i / 22050.0)) * max(0.0, 1.0 - (i / 22050.0) / 0.16) * 10000)
            for i in range(3500)
        ]
        self._sounds["wobble"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(wobble_samples)))

        # Swoosh (Tile snap)
        swoosh_samples = [
            int(math.sin(2 * math.pi * (200 + i * 0.4) * (i / 22050.0)) * max(0.0, 1.0 - (i / 22050.0) / 0.12) * 9000)
            for i in range(2600)
        ]
        self._sounds["swoosh"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(swoosh_samples)))

    def _get_sound(self, key: str) -> pygame.mixer.Sound | None:
        if not self._enabled:
            return None
        if key in self._sounds:
            return self._sounds[key]
        if ":" in key:
            loc, name = key.split(":", 1)
            audio_file = self._audio_dir / loc / f"{name}.wav"
            if audio_file.exists():
                try:
                    sound = pygame.mixer.Sound(str(audio_file))
                    self._sounds[key] = sound
                    return sound
                except Exception:
                    pass
        return None

    def play(self, name: str) -> None:
        sound = self._get_sound(name)
        if sound is not None:
            try:
                sound.play()
            except Exception:
                pass

    def play_syllable(self, syl: str, locale: str = "it") -> None:
        key = f"{locale}:syl_{syl.lower()}"
        if self._get_sound(key) is not None:
            self.play(key)
        else:
            self.play("pop")

    def play_prompt(self, syl: str, locale: str = "it") -> None:
        key = f"{locale}:find_{syl.lower()}"
        if self._get_sound(key) is not None:
            self.play(key)
        else:
            self.play_syllable(syl, locale)

    def play_word(self, word_stem: str, locale: str = "it") -> None:
        key = f"{locale}:word_{word_stem.lower()}"
        if self._get_sound(key) is not None:
            self.play(key)
        else:
            self.play("chime")

    def play_consonant(self, letter: str, locale: str = "it") -> None:
        key = f"{locale}:letter_{letter.lower()}"
        if self._get_sound(key) is not None:
            self.play(key)
        else:
            self.play("pop")

    def play_praise(self, locale: str = "it") -> None:
        praises = ["esatto", "fantastico", "super", "magnifico", "ottimo", "ben_fatto"] if locale == "it" else ["great_job", "wonderful", "you_did_it", "fantastic", "super", "well_done"]
        chosen = random.choice(praises)
        key = f"{locale}:{chosen}"
        if self._get_sound(key) is not None:
            self.play(key)
        else:
            self.play("fanfare")


class Particle:
    def __init__(self, x: float, y: float, color: tuple[int, int, int]) -> None:
        self.x = x
        self.y = y
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2.5, 7.5)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.decay = random.uniform(0.025, 0.045)
        self.color = color
        self.size = random.randint(5, 11)

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.10
        self.life -= self.decay
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        if self.life > 0:
            sz = max(1, int(self.size * self.life))
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), sz)
            pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), max(1, sz // 2))


class LeoCompanion:
    """Leo the Scholar Owl — Canonical Greia reading & language mascot."""
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.bob = 0.0
        self.blink_timer = 3.0
        self.happy_timer = 0.0
        self.wiggle_timer = 0.0

    def cheer(self) -> None:
        self.happy_timer = 2.2

    def wiggle(self) -> None:
        self.wiggle_timer = 1.2

    def update(self) -> None:
        self.bob += 0.05
        self.blink_timer -= 0.02
        if self.blink_timer <= 0:
            self.blink_timer = random.uniform(2.5, 4.5)
        if self.happy_timer > 0:
            self.happy_timer -= 0.035
        if self.wiggle_timer > 0:
            self.wiggle_timer -= 0.04

    def contains(self, px: float, py: float) -> bool:
        return (self.x - px) ** 2 + (self.y - py) ** 2 <= 55 ** 2

    def draw(self, surface: pygame.Surface) -> None:
        mx = int(self.x)
        my = int(self.y + math.sin(self.bob) * 5)
        if self.happy_timer > 0:
            my += int(abs(math.sin(self.happy_timer * 14.0)) * -16)
        if self.wiggle_timer > 0:
            mx += int(math.sin(self.wiggle_timer * 18.0) * 8)

        # Shadow
        shadow_surf = pygame.Surface((96, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, SHADOW_COLOR, (0, 0, 96, 24))
        surface.blit(shadow_surf, (mx - 48, int(self.y) + 40))

        # Leo Owl Body Colors
        body_col = (110, 75, 160)       # Rich royal purple / plum
        belly_col = (255, 240, 215)      # Cream plumage
        wing_col = (90, 55, 140)         # Darker plum wing
        beak_col = (255, 175, 45)        # Amber gold beak
        glasses_col = (245, 90, 115)     # Cheerful coral glasses

        # Wings
        pygame.draw.ellipse(surface, wing_col, (mx - 46, my - 15, 26, 48))
        pygame.draw.ellipse(surface, wing_col, (mx + 20, my - 15, 26, 48))

        # Body Bean
        pygame.draw.ellipse(surface, body_col, (mx - 38, my - 44, 76, 84))
        pygame.draw.ellipse(surface, CARD_BORDER, (mx - 38, my - 44, 76, 84), width=3)

        # Feather Ear Tufts
        pygame.draw.polygon(surface, body_col, [(mx - 32, my - 36), (mx - 42, my - 58), (mx - 18, my - 42)])
        pygame.draw.polygon(surface, CARD_BORDER, [(mx - 32, my - 36), (mx - 42, my - 58), (mx - 18, my - 42)], width=2)
        pygame.draw.polygon(surface, body_col, [(mx + 32, my - 36), (mx + 42, my - 58), (mx + 18, my - 42)])
        pygame.draw.polygon(surface, CARD_BORDER, [(mx + 32, my - 36), (mx + 42, my - 58), (mx + 18, my - 42)], width=2)

        # Soft Belly Plumage
        pygame.draw.ellipse(surface, belly_col, (mx - 25, my - 6, 50, 42))
        # Plumage V-marks
        pygame.draw.arc(surface, (180, 150, 130), (mx - 14, my + 6, 12, 8), math.pi, 2 * math.pi, 2)
        pygame.draw.arc(surface, (180, 150, 130), (mx + 2, my + 6, 12, 8), math.pi, 2 * math.pi, 2)
        pygame.draw.arc(surface, (180, 150, 130), (mx - 6, my + 18, 12, 8), math.pi, 2 * math.pi, 2)

        # Big Round Scholar Glasses (Signature Leo trait)
        gl_left = (mx - 16, my - 22)
        gl_right = (mx + 16, my - 22)
        gl_r = 16

        # Glasses bridge
        pygame.draw.line(surface, glasses_col, (mx - 6, my - 22), (mx + 6, my - 22), 4)

        # Glass Rim & Eyes
        pygame.draw.circle(surface, (255, 255, 255), gl_left, gl_r)
        pygame.draw.circle(surface, (255, 255, 255), gl_right, gl_r)

        if self.happy_timer > 0:
            # Happy smiling eye arcs
            pygame.draw.arc(surface, DARK_TEXT, (gl_left[0] - 10, gl_left[1] - 8, 20, 16), 0, math.pi, 3)
            pygame.draw.arc(surface, DARK_TEXT, (gl_right[0] - 10, gl_right[1] - 8, 20, 16), 0, math.pi, 3)
        elif self.blink_timer < 0.2:
            # Blink closed
            pygame.draw.line(surface, DARK_TEXT, (gl_left[0] - 8, gl_left[1]), (gl_left[0] + 8, gl_left[1]), 3)
            pygame.draw.line(surface, DARK_TEXT, (gl_right[0] - 8, gl_right[1]), (gl_right[0] + 8, gl_right[1]), 3)
        else:
            # Big curious pupils with gloss reflections
            pygame.draw.circle(surface, (40, 30, 50), (gl_left[0] + 1, gl_left[1] - 1), 7)
            pygame.draw.circle(surface, (40, 30, 50), (gl_right[0] - 1, gl_right[1] - 1), 7)
            pygame.draw.circle(surface, (255, 255, 255), (gl_left[0] - 2, gl_left[1] - 4), 3)
            pygame.draw.circle(surface, (255, 255, 255), (gl_right[0] - 4, gl_right[1] - 4), 3)

        pygame.draw.circle(surface, glasses_col, gl_left, gl_r, width=3)
        pygame.draw.circle(surface, glasses_col, gl_right, gl_r, width=3)

        # Beak
        pygame.draw.polygon(surface, beak_col, [(mx - 7, my - 16), (mx + 7, my - 16), (mx, my - 4)])
        pygame.draw.polygon(surface, CARD_BORDER, [(mx - 7, my - 16), (mx + 7, my - 16), (mx, my - 4)], width=2)

        # Little Feet
        pygame.draw.ellipse(surface, beak_col, (mx - 22, my + 34, 18, 10))
        pygame.draw.ellipse(surface, beak_col, (mx + 4, my + 34, 18, 10))


class SyllableCard:
    """Juicy, bouncy card for single syllable in Station 1."""
    def __init__(self, syl: str, x: float, y: float, w: float = 114.0, h: float = 136.0, color_idx: int = 0) -> None:
        self.syl = syl
        self.rect = pygame.Rect(int(x), int(y), int(w), int(h))
        self.base_x = x
        self.base_y = y
        self.w = w
        self.h = h
        self.color_pair = SYLLABLE_COLORS[color_idx % len(SYLLABLE_COLORS)]
        self.bounce_timer = 0.0
        self.pulse = random.uniform(0, 2 * math.pi)

    def bounce(self) -> None:
        self.bounce_timer = 1.0

    def contains(self, px: float, py: float) -> bool:
        return self.rect.collidepoint(int(px), int(py))

    def update(self) -> None:
        self.pulse += 0.05
        if self.bounce_timer > 0:
            self.bounce_timer -= 0.055

    def draw(self, surface: pygame.Surface, typography: GreiaTypography) -> None:
        scale = 1.0
        if self.bounce_timer > 0:
            scale = 1.0 + math.sin(self.bounce_timer * math.pi) * 0.20

        bw = int(self.w * scale)
        bh = int(self.h * scale)
        bx = int(self.base_x + (self.w - bw) / 2)
        by = int(self.base_y + (self.h - bh) / 2)
        self.rect = pygame.Rect(bx, by, bw, bh)

        # Deep Drop Shadow
        shadow_surf = pygame.Surface((bw + 8, bh + 10), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, SHADOW_COLOR, (0, 0, bw, bh), border_radius=22)
        surface.blit(shadow_surf, (bx + 5, by + 8))

        # Main Card Body with 3D Border
        pygame.draw.rect(surface, self.color_pair[0], self.rect, border_radius=22)
        inner_rect = pygame.Rect(bx + 6, by + 6, bw - 12, bh - 12)
        pygame.draw.rect(surface, self.color_pair[1], inner_rect, border_radius=18)
        pygame.draw.rect(surface, CARD_BORDER, self.rect, width=3, border_radius=22)

        # Gloss Reflex
        gloss_rect = pygame.Rect(bx + 10, by + 10, bw - 20, int(bh * 0.32))
        pygame.draw.rect(surface, (255, 255, 255, 110), gloss_rect, border_radius=12)

        # Syllable Text
        text_surf = typography.render(self.syl, FontRole.DISPLAY, 46, DARK_TEXT)
        tx = bx + (bw - text_surf.get_width()) // 2
        ty = by + 22
        surface.blit(text_surf, (tx, ty))

        # Mini Speaker Icon
        icon_surf = typography.render("🔉", FontRole.DISPLAY, 22, (255, 255, 255))
        surface.blit(icon_surf, (bx + (bw - icon_surf.get_width()) // 2, by + bh - 36))


class FloatingOrb:
    """Floating syllable bubble for Station 2 (Acchiappa-Sillaba)."""
    def __init__(self, syl: str, x: float, y: float, is_target: bool = False, color_idx: int = 0) -> None:
        self.syl = syl
        self.x = x
        self.y = y
        self.base_y = y
        self.radius = 44.0
        self.is_target = is_target
        self.color_pair = SYLLABLE_COLORS[color_idx % len(SYLLABLE_COLORS)]
        self.phase = random.uniform(0, 2 * math.pi)
        self.vx = random.choice([-0.7, -0.4, 0.4, 0.7])
        self.wobble_timer = 0.0
        self.pulse = 0.0

    def update(self) -> None:
        self.phase += 0.035
        self.y = self.base_y + math.sin(self.phase) * 15.0
        self.x += self.vx
        if self.x < 150:
            self.x = 150
            self.vx = abs(self.vx)
        elif self.x > 880:
            self.x = 880
            self.vx = -abs(self.vx)
        if self.wobble_timer > 0:
            self.wobble_timer -= 0.05
        self.pulse += 0.04

    def wobble(self) -> None:
        self.wobble_timer = 1.0

    def contains(self, px: float, py: float) -> bool:
        return (self.x - px) ** 2 + (self.y - py) ** 2 <= (self.radius + 12) ** 2

    def draw(self, surface: pygame.Surface, typography: GreiaTypography) -> None:
        cx, cy = int(self.x), int(self.y)
        if self.wobble_timer > 0:
            cx += int(math.sin(self.wobble_timer * 20.0) * 9.0)

        # Target Glow Pulse
        if self.is_target:
            glow_r = int(self.radius + 12 + math.sin(self.pulse * 2.0) * 6)
            glow_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*GOLD, 110), (glow_r + 2, glow_r + 2), glow_r)
            surface.blit(glow_surf, (cx - glow_r - 2, cy - glow_r - 2))

        # Shadow
        shadow_surf = pygame.Surface((int(self.radius * 2 + 10), int(self.radius * 2 + 10)), pygame.SRCALPHA)
        pygame.draw.circle(shadow_surf, SHADOW_COLOR, (int(self.radius + 5), int(self.radius + 8)), int(self.radius))
        surface.blit(shadow_surf, (cx - int(self.radius + 5), cy - int(self.radius)))

        # Main Bubble Orb
        pygame.draw.circle(surface, self.color_pair[0], (cx, cy), int(self.radius))
        pygame.draw.circle(surface, self.color_pair[1], (cx - 7, cy - 7), int(self.radius * 0.68))
        pygame.draw.circle(surface, (255, 255, 255), (cx - 14, cy - 14), 9)
        pygame.draw.circle(surface, CARD_BORDER, (cx, cy), int(self.radius), width=3)

        # Syllable Text
        s_surf = typography.render(self.syl, FontRole.DISPLAY, 38, DARK_TEXT)
        sx = cx - s_surf.get_width() // 2
        sy = cy - s_surf.get_height() // 2
        surface.blit(s_surf, (sx, sy))


class WordTile:
    """Tile for 2-syllable word builder in Station 3."""
    def __init__(self, syl: str, x: float, y: float, w: float = 120.0, h: float = 98.0, color_idx: int = 0) -> None:
        self.syl = syl
        self.rect = pygame.Rect(int(x), int(y), int(w), int(h))
        self.base_x = x
        self.base_y = y
        self.w = w
        self.h = h
        self.color_pair = SYLLABLE_COLORS[color_idx % len(SYLLABLE_COLORS)]
        self.used = False
        self.wobble_timer = 0.0
        self.bounce_timer = 0.0

    def wobble(self) -> None:
        self.wobble_timer = 1.0

    def bounce(self) -> None:
        self.bounce_timer = 1.0

    def contains(self, px: float, py: float) -> bool:
        if self.used:
            return False
        return self.rect.collidepoint(int(px), int(py))

    def update(self) -> None:
        if self.wobble_timer > 0:
            self.wobble_timer -= 0.05
        if self.bounce_timer > 0:
            self.bounce_timer -= 0.05

    def draw(self, surface: pygame.Surface, typography: GreiaTypography) -> None:
        if self.used:
            return

        bx, by = int(self.base_x), int(self.base_y)
        if self.wobble_timer > 0:
            bx += int(math.sin(self.wobble_timer * 18.0) * 8.0)

        # Shadow
        shadow_surf = pygame.Surface((int(self.w + 8), int(self.h + 8)), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, SHADOW_COLOR, (0, 0, int(self.w), int(self.h)), border_radius=18)
        surface.blit(shadow_surf, (bx + 4, by + 6))

        self.rect = pygame.Rect(bx, by, int(self.w), int(self.h))
        pygame.draw.rect(surface, self.color_pair[0], self.rect, border_radius=18)
        inner_rect = pygame.Rect(bx + 5, by + 5, int(self.w) - 10, int(self.h) - 10)
        pygame.draw.rect(surface, self.color_pair[1], inner_rect, border_radius=14)
        pygame.draw.rect(surface, CARD_BORDER, self.rect, width=3, border_radius=18)

        t_surf = typography.render(self.syl, FontRole.DISPLAY, 42, DARK_TEXT)
        tx = bx + (int(self.w) - t_surf.get_width()) // 2
        ty = by + (int(self.h) - t_surf.get_height()) // 2
        surface.blit(t_surf, (tx, ty))


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

    words_pool = WORDS_DATA_IT if active_locale == "it" else WORDS_DATA_EN
    consonants_pool = CONSONANTS_IT

    # Persistent Progression State
    score = 0
    stars = 0
    words_completed_count = 0
    current_mode = "explorer"  # "explorer", "catcher", "builder"

    if storage is not None:
        try:
            saved = storage.kv_get(STORAGE_KEY, {})
            if isinstance(saved, dict):
                score = int(saved.get("score", 0))
                stars = int(saved.get("stars", 0))
                words_completed_count = int(saved.get("words_completed", 0))
        except Exception:
            pass

    def save_progress():
        if storage is not None:
            try:
                storage.kv_set(STORAGE_KEY, {
                    "score": score,
                    "stars": stars,
                    "words_completed": words_completed_count,
                })
            except Exception:
                pass

    mascot = LeoCompanion(935, 480)
    particles: list[Particle] = []

    # -------------------------------------------------------------
    # Station 1 State: Sillabario Explorer
    # -------------------------------------------------------------
    consonant_idx = 0
    active_consonant = consonants_pool[consonant_idx]
    cards_station1: list[SyllableCard] = []

    def refresh_station1_cards():
        cards_station1.clear()
        base_x = 230
        card_w = 118
        gap = 20
        for i, v in enumerate(VOWELS_IT):
            syl = f"{active_consonant}{v}"
            cx = base_x + i * (card_w + gap)
            cy = 280
            cards_station1.append(SyllableCard(syl, cx, cy, w=card_w, h=136, color_idx=i))

    refresh_station1_cards()

    # -------------------------------------------------------------
    # Station 2 State: Acchiappa-Sillaba (Sequential Audio State Machine)
    # -------------------------------------------------------------
    target_syl = "BA"
    catcher_orbs: list[FloatingOrb] = []
    catcher_state = "idle"  # "idle", "praise_pending", "next_round_pending"
    catcher_timer = 0.0

    def start_catcher_round(play_audio: bool = True):
        nonlocal target_syl, catcher_state, catcher_timer
        chosen_consonant = random.choice(consonants_pool)
        chosen_vowel = random.choice(VOWELS_IT)
        target_syl = f"{chosen_consonant}{chosen_vowel}"
        catcher_state = "idle"
        catcher_timer = 0.0

        catcher_orbs.clear()
        orb_syls = [target_syl, target_syl]
        while len(orb_syls) < 6:
            rc = random.choice(consonants_pool)
            rv = random.choice(VOWELS_IT)
            cand = f"{rc}{rv}"
            if cand != target_syl and cand not in orb_syls:
                orb_syls.append(cand)

        random.shuffle(orb_syls)
        slots = [
            (240, 230), (430, 200), (620, 230), (800, 210),
            (320, 390), (530, 410), (730, 390)
        ]
        random.shuffle(slots)
        for i, s in enumerate(orb_syls):
            sx, sy = slots[i % len(slots)]
            catcher_orbs.append(FloatingOrb(s, sx + random.uniform(-15, 15), sy + random.uniform(-10, 10), is_target=(s == target_syl), color_idx=i))

        if play_audio:
            sounds.play_prompt(target_syl, active_locale)

    start_catcher_round(play_audio=False)

    # -------------------------------------------------------------
    # Station 3 State: Crea Parole (Word Builder & Syllable Breakdown)
    # -------------------------------------------------------------
    word_idx = 0
    cur_word_display, (cur_s1, cur_s2), cur_emoji, cur_stem = words_pool[word_idx]
    slot1_filled = False
    slot2_filled = False
    word_completed_flag = False
    word_tiles: list[WordTile] = []
    
    # Syllable Breakdown Timed Audio State
    syllable_speech_step = 0
    syllable_speech_timer = 0.0
    
    # Completion Fanfare Timed Audio State
    word_completion_step = 0
    word_completion_timer = 0.0

    # Prominent Icon-Only Word Card Audio Buttons (Zero-Text to avoid spoiling the spelling)
    btn_whole_word_rect = pygame.Rect(385, 208, 110, 58)
    btn_split_syllables_rect = pygame.Rect(525, 208, 110, 58)

    def start_word_round(play_audio: bool = True):
        nonlocal slot1_filled, slot2_filled, word_completed_flag, cur_word_display, cur_s1, cur_s2, cur_emoji, cur_stem
        nonlocal syllable_speech_step, syllable_speech_timer, word_completion_step, word_completion_timer
        cur_word_display, (cur_s1, cur_s2), cur_emoji, cur_stem = words_pool[word_idx % len(words_pool)]
        slot1_filled = False
        slot2_filled = False
        word_completed_flag = False
        syllable_speech_step = 0
        syllable_speech_timer = 0.0
        word_completion_step = 0
        word_completion_timer = 0.0

        choices = [cur_s1, cur_s2]
        while len(choices) < 4:
            rc = random.choice(consonants_pool)
            rv = random.choice(VOWELS_IT)
            cand = f"{rc}{rv}"
            if cand not in choices:
                choices.append(cand)
        random.shuffle(choices)

        word_tiles.clear()
        base_x = 240
        tile_w = 120
        gap = 26
        for i, s in enumerate(choices):
            tx = base_x + i * (tile_w + gap)
            ty = 440
            word_tiles.append(WordTile(s, tx, ty, w=tile_w, h=98, color_idx=i))

        if play_audio:
            sounds.play_word(cur_stem, active_locale)

    start_word_round(play_audio=False)

    # Top Tabs Geometry
    tab_w = 175
    tab_h = 58
    tabs = [
        ("explorer", "📖 " + ("Sillabario" if active_locale == "it" else "Syllabary"), pygame.Rect(180, 16, tab_w, tab_h)),
        ("catcher", "🎯 " + ("Acchiappa" if active_locale == "it" else "Catch"), pygame.Rect(370, 16, tab_w, tab_h)),
        ("builder", "🧩 " + ("Crea Parole" if active_locale == "it" else "Words"), pygame.Rect(560, 16, tab_w, tab_h)),
    ]

    audio_btn_rect = pygame.Rect(755, 14, 68, 62)
    star_jar_rect = pygame.Rect(835, 14, 130, 62)

    initial_prompt_timer = 0.45
    running = True
    ready_published = False
    virtual_pointer = (512, 300)
    pointer_down = False

    while running and not activity_stop_requested():
        dt = clock.tick(60) / 1000.0

        if initial_prompt_timer > 0:
            initial_prompt_timer -= dt
            if initial_prompt_timer <= 0:
                sounds.play_consonant(active_consonant, active_locale)

        # -------------------------------------------------------------
        # Audio State Machine Updates (Station 2: Acchiappa-Sillaba)
        # -------------------------------------------------------------
        if catcher_state == "praise_pending":
            catcher_timer -= dt
            if catcher_timer <= 0:
                sounds.play_praise(active_locale)
                catcher_state = "next_round_pending"
                catcher_timer = 1.15
        elif catcher_state == "next_round_pending":
            catcher_timer -= dt
            if catcher_timer <= 0:
                start_catcher_round(play_audio=True)

        # -------------------------------------------------------------
        # Audio State Machine Updates (Station 3: Syllable Breakdown & Word Completion)
        # -------------------------------------------------------------
        if syllable_speech_step == 1:
            syllable_speech_timer -= dt
            if syllable_speech_timer <= 0:
                sounds.play_syllable(cur_s2, active_locale)
                syllable_speech_step = 0

        if word_completion_step == 1:
            word_completion_timer -= dt
            if word_completion_timer <= 0:
                sounds.play_word(cur_stem, active_locale)
                word_completion_step = 2
                word_completion_timer = 0.90
        elif word_completion_step == 2:
            word_completion_timer -= dt
            if word_completion_timer <= 0:
                sounds.play_praise(active_locale)
                word_completion_step = 3
                word_completion_timer = 1.40
        elif word_completion_step == 3:
            word_completion_timer -= dt
            if word_completion_timer <= 0:
                word_completion_step = 0
                word_idx += 1
                start_word_round(play_audio=True)

        # -------------------------------------------------------------
        # Event Processing
        # -------------------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    if current_mode == "explorer":
                        sounds.play_consonant(active_consonant, active_locale)
                    elif current_mode == "catcher":
                        sounds.play_prompt(target_syl, active_locale)
                    elif current_mode == "builder":
                        sounds.play_word(cur_stem, active_locale)
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
            elif event.type == pygame.MOUSEMOTION:
                logical = canvas.pointer(event.pos)
                if logical is not None:
                    virtual_pointer = logical
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                pointer_down = False
                if is_home_clicked(screen, event.pos):
                    running = False
                    continue
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pointer_down = True
                if is_home_clicked(screen, event.pos):
                    running = False
                    continue
                logical = canvas.pointer(event.pos)
                if logical is None:
                    continue
                lx, ly = logical

                if not _is_safe_point(screen, event.pos):
                    continue

                # 1. Top Mode Tabs
                mode_changed = False
                for m_id, m_label, r in tabs:
                    if r.collidepoint(lx, ly) and current_mode != m_id:
                        current_mode = m_id
                        mode_changed = True
                        if current_mode == "explorer":
                            sounds.play_consonant(active_consonant, active_locale)
                        elif current_mode == "catcher":
                            start_catcher_round(play_audio=True)
                        elif current_mode == "builder":
                            start_word_round(play_audio=True)
                        break

                if mode_changed:
                    continue

                # 2. Main Audio Replay Button
                if audio_btn_rect.collidepoint(lx, ly):
                    if current_mode == "explorer":
                        sounds.play_consonant(active_consonant, active_locale)
                    elif current_mode == "catcher":
                        sounds.play_prompt(target_syl, active_locale)
                    elif current_mode == "builder":
                        sounds.play_word(cur_stem, active_locale)
                    continue

                # 3. Mascot Tap
                if mascot.contains(lx, ly):
                    mascot.wiggle()
                    sounds.play("pop")
                    continue

                # 4. Mode Interactions
                if current_mode == "explorer":
                    # Consonant Palette Buttons
                    pal_w = 68
                    pal_h = 56
                    for i, c in enumerate(consonants_pool):
                        row = i % 7
                        col = i // 7
                        bx = 40 + col * 76
                        by = 136 + row * 62
                        btn_rect = pygame.Rect(bx, by, pal_w, pal_h)
                        if btn_rect.collidepoint(lx, ly):
                            active_consonant = c
                            sounds.play_consonant(c, active_locale)
                            refresh_station1_cards()
                            mascot.wiggle()
                            break

                    for card in cards_station1:
                        if card.contains(lx, ly):
                            card.bounce()
                            sounds.play_syllable(card.syl, active_locale)
                            mascot.cheer()
                            for _ in range(16):
                                particles.append(Particle(card.rect.centerx, card.rect.centery, card.color_pair[0]))
                            safe_emit("syllable.explored", f"syl_{card.syl}_{time.time()}")
                            score += 1

                elif current_mode == "catcher":
                    # Lock input while celebrating praise / next round
                    if catcher_state == "idle":
                        for orb in catcher_orbs:
                            if orb.contains(lx, ly):
                                if orb.syl == target_syl:
                                    sounds.play_syllable(orb.syl, active_locale)
                                    mascot.cheer()
                                    stars += 1
                                    score += 5
                                    save_progress()
                                    safe_emit("syllable.matched", f"match_{target_syl}_{time.time()}")
                                    for _ in range(24):
                                        particles.append(Particle(orb.x, orb.y, GOLD))
                                    # Trigger sequential praise -> then next round
                                    catcher_state = "praise_pending"
                                    catcher_timer = 0.55
                                else:
                                    orb.wobble()
                                    sounds.play_syllable(orb.syl, active_locale)
                                break

                elif current_mode == "builder":
                    # Whole Word Audio Button
                    if btn_whole_word_rect.collidepoint(lx, ly):
                        sounds.play_word(cur_stem, active_locale)
                        mascot.wiggle()
                        continue

                    # Syllable Breakdown Audio Button
                    if btn_split_syllables_rect.collidepoint(lx, ly):
                        sounds.play_syllable(cur_s1, active_locale)
                        syllable_speech_step = 1
                        syllable_speech_timer = 0.52
                        mascot.wiggle()
                        continue

                    if not word_completed_flag:
                        for tile in word_tiles:
                            if tile.contains(lx, ly):
                                if not slot1_filled:
                                    if tile.syl == cur_s1:
                                        slot1_filled = True
                                        tile.used = True
                                        sounds.play_syllable(cur_s1, active_locale)
                                        for _ in range(12):
                                            particles.append(Particle(tile.rect.centerx, tile.rect.centery, MINT_GREEN))
                                    else:
                                        tile.wobble()
                                        sounds.play_syllable(tile.syl, active_locale)
                                elif not slot2_filled:
                                    if tile.syl == cur_s2:
                                        slot2_filled = True
                                        tile.used = True
                                        word_completed_flag = True
                                        # Start timed non-overlapping completion sequence
                                        sounds.play_syllable(cur_s2, active_locale)
                                        word_completion_step = 1
                                        word_completion_timer = 0.50
                                        mascot.cheer()
                                        stars += 2
                                        score += 10
                                        words_completed_count += 1
                                        save_progress()
                                        safe_emit("word.completed", f"word_{cur_stem}_{time.time()}")
                                        for _ in range(30):
                                            particles.append(Particle(512, 170, GOLD))
                                    else:
                                        tile.wobble()
                                        sounds.play_syllable(tile.syl, active_locale)
                                break
                    else:
                        word_idx += 1
                        start_word_round(play_audio=True)

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                pointer_down = False

        # Update Scene Entities
        mascot.update()
        particles = [p for p in particles if p.update()]

        if current_mode == "explorer":
            for c in cards_station1:
                c.update()
        elif current_mode == "catcher":
            for orb in catcher_orbs:
                orb.update()
        elif current_mode == "builder":
            for tile in word_tiles:
                tile.update()

        # =============================================================
        # RENDERING (1024 x 600 Reference Space)
        # =============================================================
        logical_surf = canvas.surface

        # 1. Background Meadow
        for y in range(REFERENCE_HEIGHT):
            ratio = y / float(REFERENCE_HEIGHT)
            col = mix(BG_SKY_TOP, BG_SKY_BOTTOM, ratio)
            pygame.draw.line(logical_surf, col, (0, y), (REFERENCE_WIDTH, y))

        pygame.draw.ellipse(logical_surf, BG_GRASS_BACK, (-80, 480, 600, 240))
        pygame.draw.ellipse(logical_surf, BG_GRASS_BACK, (420, 500, 700, 220))
        pygame.draw.ellipse(logical_surf, BG_GRASS_FRONT, (-40, 520, 1100, 180))

        # 2. Top Navigation Bar
        for m_id, m_label, r in tabs:
            is_active = (current_mode == m_id)
            tab_bg = GOLD if is_active else CARD_BG
            tab_border = GOLD_BORDER if is_active else CARD_BORDER
            pygame.draw.rect(logical_surf, (0, 0, 0, 30), (r.x + 2, r.y + 4, r.w, r.h), border_radius=16)
            pygame.draw.rect(logical_surf, tab_bg, r, border_radius=16)
            pygame.draw.rect(logical_surf, tab_border, r, width=3 if is_active else 2, border_radius=16)

            tab_text = typography.render(m_label, FontRole.CONTROL, 20, DARK_TEXT)
            logical_surf.blit(tab_text, (r.x + (r.w - tab_text.get_width()) // 2, r.y + (r.h - tab_text.get_height()) // 2))

        # Audio Button
        pygame.draw.rect(logical_surf, (0, 0, 0, 30), (audio_btn_rect.x + 2, audio_btn_rect.y + 4, audio_btn_rect.w, audio_btn_rect.h), border_radius=16)
        pygame.draw.rect(logical_surf, SKY_BLUE, audio_btn_rect, border_radius=16)
        pygame.draw.rect(logical_surf, CARD_BORDER, audio_btn_rect, width=2, border_radius=16)
        speaker_icon = typography.render("🔊", FontRole.DISPLAY, 26, (255, 255, 255))
        logical_surf.blit(speaker_icon, (audio_btn_rect.x + (audio_btn_rect.w - speaker_icon.get_width()) // 2, audio_btn_rect.y + (audio_btn_rect.h - speaker_icon.get_height()) // 2))

        # Star Jar Counter
        pygame.draw.rect(logical_surf, (0, 0, 0, 30), (star_jar_rect.x + 2, star_jar_rect.y + 4, star_jar_rect.w, star_jar_rect.h), border_radius=16)
        pygame.draw.rect(logical_surf, CARD_BG, star_jar_rect, border_radius=16)
        pygame.draw.rect(logical_surf, GOLD_BORDER, star_jar_rect, width=2, border_radius=16)
        star_icon = typography.render(f"⭐ {stars}", FontRole.CONTROL, 22, (220, 145, 10))
        logical_surf.blit(star_icon, (star_jar_rect.x + (star_jar_rect.w - star_icon.get_width()) // 2, star_jar_rect.y + (star_jar_rect.h - star_icon.get_height()) // 2))

        # 3. Mode Content
        if current_mode == "explorer":
            # Consonant Toy Box Shelf
            shelf_rect = pygame.Rect(28, 92, 172, 490)
            pygame.draw.rect(logical_surf, (0, 0, 0, 25), (shelf_rect.x + 3, shelf_rect.y + 4, shelf_rect.w, shelf_rect.h), border_radius=18)
            pygame.draw.rect(logical_surf, (248, 242, 230), shelf_rect, border_radius=18)
            pygame.draw.rect(logical_surf, (215, 195, 170), shelf_rect, width=3, border_radius=18)

            pal_title = typography.render(display_text("Consonanti"), FontRole.TITLE, 18, DARK_TEXT)
            logical_surf.blit(pal_title, (shelf_rect.centerx - pal_title.get_width() // 2, 104))

            pal_w = 68
            pal_h = 56
            for i, c in enumerate(consonants_pool):
                row = i % 7
                col = i // 7
                bx = 38 + col * 78
                by = 136 + row * 62
                btn_rect = pygame.Rect(bx, by, pal_w, pal_h)
                is_sel = (c == active_consonant)

                # Button Shadow
                pygame.draw.rect(logical_surf, (0, 0, 0, 30), (bx + 2, by + 4, pal_w, pal_h), border_radius=14)

                c_bg = GOLD if is_sel else (255, 255, 255)
                c_border = GOLD_BORDER if is_sel else CARD_BORDER
                pygame.draw.rect(logical_surf, c_bg, btn_rect, border_radius=14)
                pygame.draw.rect(logical_surf, c_border, btn_rect, width=3 if is_sel else 2, border_radius=14)

                c_text = typography.render(c, FontRole.DISPLAY, 30, DARK_TEXT)
                logical_surf.blit(c_text, (bx + (pal_w - c_text.get_width()) // 2, by + (pal_h - c_text.get_height()) // 2 - 2))

                if is_sel:
                    # Active Star Badge
                    pygame.draw.circle(logical_surf, (255, 255, 255), (bx + pal_w - 6, by + 6), 6)
                    pygame.draw.circle(logical_surf, CORAL, (bx + pal_w - 6, by + 6), 4)

            # Central Workshop Header Card
            top_card = pygame.Rect(226, 92, 670, 140)
            pygame.draw.rect(logical_surf, (0, 0, 0, 25), (top_card.x + 3, top_card.y + 4, top_card.w, top_card.h), border_radius=22)
            pygame.draw.rect(logical_surf, CARD_BG, top_card, border_radius=22)
            pygame.draw.rect(logical_surf, CARD_BORDER, top_card, width=3, border_radius=22)

            # Blending Formula Visual
            formula_surf = typography.render(display_text(f"Fabbrica delle Sillabe:   [ {active_consonant} ]  ➕  Vocali ( A , E , I , O , U )"), FontRole.TITLE, 22, DARK_TEXT)
            logical_surf.blit(formula_surf, (top_card.centerx - formula_surf.get_width() // 2, top_card.y + 20))

            instruct_surf = typography.render(display_text("Tocca ogni tessera per ascoltare e imparare la sillaba!"), FontRole.BODY, 18, (100, 85, 115))
            logical_surf.blit(instruct_surf, (top_card.centerx - instruct_surf.get_width() // 2, top_card.y + 72))

            for card in cards_station1:
                card.draw(logical_surf, typography)

        elif current_mode == "catcher":
            banner_rect = pygame.Rect(260, 95, 504, 76)
            pygame.draw.rect(logical_surf, (0, 0, 0, 25), (banner_rect.x + 3, banner_rect.y + 4, banner_rect.w, banner_rect.h), border_radius=18)
            pygame.draw.rect(logical_surf, CARD_BG, banner_rect, border_radius=18)
            pygame.draw.rect(logical_surf, GOLD_BORDER, banner_rect, width=3, border_radius=18)

            p_txt = display_text("Ascolta e tocca:  ")
            p_surf = typography.render(p_txt, FontRole.TITLE, 28, DARK_TEXT)
            target_surf = typography.render(target_syl, FontRole.DISPLAY, 40, CORAL)
            total_w = p_surf.get_width() + target_surf.get_width()
            sx = banner_rect.centerx - total_w // 2
            logical_surf.blit(p_surf, (sx, banner_rect.centery - p_surf.get_height() // 2))
            logical_surf.blit(target_surf, (sx + p_surf.get_width(), banner_rect.centery - target_surf.get_height() // 2))

            for orb in catcher_orbs:
                orb.draw(logical_surf, typography)

        elif current_mode == "builder":
            center_card = pygame.Rect(240, 86, 544, 320)
            pygame.draw.rect(logical_surf, (0, 0, 0, 25), (center_card.x + 4, center_card.y + 5, center_card.w, center_card.h), border_radius=24)
            pygame.draw.rect(logical_surf, CARD_BG, center_card, border_radius=24)
            pygame.draw.rect(logical_surf, CARD_BORDER, center_card, width=3, border_radius=24)

            # Illustration Emoji
            emoji_surf = typography.render(cur_emoji, FontRole.DISPLAY, 80, DARK_TEXT)
            logical_surf.blit(emoji_surf, (center_card.centerx - emoji_surf.get_width() // 2, center_card.y + 12))

            # Completed Word Banner
            if word_completed_flag:
                comp_txt = typography.render(f"✨ {cur_word_display} ✨", FontRole.TITLE, 32, (220, 130, 20))
                logical_surf.blit(comp_txt, (center_card.centerx - comp_txt.get_width() // 2, center_card.y + 104))

            # ---------------------------------------------------------
            # 2 Prominent Icon-Only Word Audio Buttons (No Text Spoilers)
            # ---------------------------------------------------------
            # 1. Whole Word Audio Button [ 🔊 ]
            pygame.draw.rect(logical_surf, (0, 0, 0, 25), (btn_whole_word_rect.x + 2, btn_whole_word_rect.y + 4, btn_whole_word_rect.w, btn_whole_word_rect.h), border_radius=18)
            pygame.draw.rect(logical_surf, GOLD, btn_whole_word_rect, border_radius=18)
            pygame.draw.rect(logical_surf, GOLD_BORDER, btn_whole_word_rect, width=3, border_radius=18)
            btn1_icon = typography.render("🔊", FontRole.DISPLAY, 32, DARK_TEXT)
            logical_surf.blit(btn1_icon, (btn_whole_word_rect.centerx - btn1_icon.get_width() // 2, btn_whole_word_rect.centery - btn1_icon.get_height() // 2))

            # 2. Syllable Breakdown Audio Button [ 🗣️ ]
            pygame.draw.rect(logical_surf, (0, 0, 0, 25), (btn_split_syllables_rect.x + 2, btn_split_syllables_rect.y + 4, btn_split_syllables_rect.w, btn_split_syllables_rect.h), border_radius=18)
            is_speaking_split = (syllable_speech_step > 0)
            pygame.draw.rect(logical_surf, SKY_BLUE if not is_speaking_split else MINT_GREEN, btn_split_syllables_rect, border_radius=18)
            pygame.draw.rect(logical_surf, CARD_BORDER, btn_split_syllables_rect, width=3, border_radius=18)
            btn2_icon = typography.render("🗣️", FontRole.DISPLAY, 32, DARK_TEXT if is_speaking_split else LIGHT_TEXT)
            logical_surf.blit(btn2_icon, (btn_split_syllables_rect.centerx - btn2_icon.get_width() // 2, btn_split_syllables_rect.centery - btn2_icon.get_height() // 2))

            # ---------------------------------------------------------
            # 2 Syllable Puzzle Slots
            # ---------------------------------------------------------
            slot_w, slot_h = 135, 96
            slot1_rect = pygame.Rect(center_card.centerx - slot_w - 18, center_card.y + 195, slot_w, slot_h)
            slot2_rect = pygame.Rect(center_card.centerx + 18, center_card.y + 195, slot_w, slot_h)

            if slot1_filled:
                pygame.draw.rect(logical_surf, MINT_GREEN, slot1_rect, border_radius=18)
                pygame.draw.rect(logical_surf, CARD_BORDER, slot1_rect, width=3, border_radius=18)
                s1_txt = typography.render(cur_s1, FontRole.DISPLAY, 46, (255, 255, 255))
                logical_surf.blit(s1_txt, (slot1_rect.centerx - s1_txt.get_width() // 2, slot1_rect.centery - s1_txt.get_height() // 2))
            else:
                pygame.draw.rect(logical_surf, (244, 244, 244), slot1_rect, border_radius=18)
                pygame.draw.rect(logical_surf, (160, 160, 175), slot1_rect, width=3, border_radius=18)
                q1_txt = typography.render(display_text("1° Sillaba"), FontRole.TITLE, 20, (160, 160, 175))
                logical_surf.blit(q1_txt, (slot1_rect.centerx - q1_txt.get_width() // 2, slot1_rect.centery - q1_txt.get_height() // 2))

            if slot2_filled:
                pygame.draw.rect(logical_surf, MINT_GREEN, slot2_rect, border_radius=18)
                pygame.draw.rect(logical_surf, CARD_BORDER, slot2_rect, width=3, border_radius=18)
                s2_txt = typography.render(cur_s2, FontRole.DISPLAY, 46, (255, 255, 255))
                logical_surf.blit(s2_txt, (slot2_rect.centerx - s2_txt.get_width() // 2, slot2_rect.centery - s2_txt.get_height() // 2))
            else:
                pygame.draw.rect(logical_surf, (244, 244, 244), slot2_rect, border_radius=18)
                pygame.draw.rect(logical_surf, (160, 160, 175), slot2_rect, width=3, border_radius=18)
                q2_txt = typography.render(display_text("2° Sillaba"), FontRole.TITLE, 20, (160, 160, 175))
                logical_surf.blit(q2_txt, (slot2_rect.centerx - q2_txt.get_width() // 2, slot2_rect.centery - q2_txt.get_height() // 2))

            for tile in word_tiles:
                tile.draw(logical_surf, typography)

        # 4. Companion Leo
        mascot.draw(logical_surf)

        # 5. Confetti & Star Particles
        for p in particles:
            p.draw(logical_surf)

        # 6. Virtual Cursor
        cx, cy = virtual_pointer
        pygame.draw.circle(logical_surf, (255, 255, 255), (int(cx), int(cy)), 10)
        pygame.draw.circle(logical_surf, CORAL if pointer_down else SKY_BLUE, (int(cx), int(cy)), 7)
        pygame.draw.circle(logical_surf, CARD_BORDER, (int(cx), int(cy)), 10, width=2)

        canvas.present(clear=theme.background)
        pygame.display.flip()

        if not ready_published:
            mark_activity_ready()
            ready_published = True

    if storage is not None:
        try:
            storage.kv_set(STORAGE_KEY, {
                "score": score,
                "stars": stars,
                "words_completed": words_completed_count,
            })
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    main()
