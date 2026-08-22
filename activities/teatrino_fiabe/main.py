"""Teatrino delle Fiabe (Puppet Theater) Activity for Greia OS.

A storybook puppet theater where children create puppet shows,
narrate their stories through the computer microphone, save recordings
in a persistent story library, and watch full theatrical replaying.
"""

from __future__ import annotations

import io
import json
import math
import os
from pathlib import Path
import random
import struct
import time
import uuid
import wave

import pygame

try:
    from pygame._sdl2 import audio as sdl2_audio
except ImportError:
    sdl2_audio = None

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_icon_path,
    get_storage,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import (
    ChildUiMetrics,
    draw_activity_pointer,
    draw_system_chrome_overlay,
    is_home_clicked,
    mix,
)
from greia_platform.typography import FontRole, GreiaTypography

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
MAX_RECORDING_SECONDS = 45.0
MAX_SAVED_SHOWS = 16
SHOWS_INDEX_KEY = "teatrino.shows.index.v1"

# Stage Theme Palette
STAGE_RED = (185, 28, 28)
STAGE_CURTAIN = (153, 27, 27)
STAGE_CURTAIN_DARK = (127, 29, 29)
STAGE_CURTAIN_LIGHT = (220, 38, 38)
STAGE_GOLD = (245, 158, 11)
STAGE_GOLD_LIGHT = (254, 240, 138)
STAGE_WOOD_TOP = (180, 110, 50)
STAGE_WOOD_BASE = (120, 65, 20)
DARK_TEXT = (45, 25, 15)
WHITE = (255, 255, 255)
REC_RED = (239, 68, 68)
MIC_GREEN = (34, 197, 94)

BG_CONFIGS = [
    ("cottage", "🏡", "Casetta"),
    ("castle", "🏰", "Castello"),
    ("ocean", "🌊", "Mare"),
    ("forest", "🌲", "Bosco"),
    ("sky", "☁️", "Cielo"),
]

PUPPET_ROSTER = [
    # Page 1: Canonical Greia Cast
    ("lilli", "Lilli"),
    ("leo", "Leo"),
    ("flash", "Flash"),
    ("dani", "Dani"),
    ("tito", "Tito"),
    ("momo", "Momo"),
    # Page 2: Classic Fairytale Troupe
    ("principessa", "Principessa"),
    ("draghetto", "Draghetto"),
    ("cavaliere", "Cavaliere"),
    ("bebe", "Bebè"),
    ("re", "Re"),
    ("lupetto", "Lupetto"),
    # Page 3: Magical Characters
    ("orsetto", "Orsetto"),
    ("sirenetta", "Sirenetta"),
    ("mago", "Mago"),
    ("fatina", "Fatina"),
]

FX_BUTTONS = [
    ("trumpet", "🎺"),
    ("magic", "✨"),
    ("applause", "👏"),
    ("giggle", "😄"),
    ("mystery", "🔮"),
    ("boing", "💥"),
]


# ============================================================================
# PERSISTENT SHOW LIBRARY ENGINE
# ============================================================================

class ShowRepository:
    """Manages persistent saved shows and companion audio narration tracks."""

    def __init__(self, storage) -> None:
        self.storage = storage

    def list_shows(self) -> list[dict]:
        raw = self.storage.kv_get(SHOWS_INDEX_KEY, [])
        if not isinstance(raw, list):
            return []
        cleaned: list[dict] = []
        for item in raw:
            if isinstance(item, dict) and "id" in item:
                cleaned.append(item)
        return cleaned[:MAX_SAVED_SHOWS]

    def save_show(
        self,
        backdrop_id: str,
        puppets: list[dict],
        frames: list[dict],
        sfx_events: list[dict],
        duration: float,
        audio_wav_bytes: bytes | None = None,
    ) -> dict:
        show_id = uuid.uuid4().hex[:12]
        show_meta = {
            "id": show_id,
            "title": f"Storia {len(self.list_shows()) + 1}",
            "backdrop": backdrop_id,
            "actors": [p["id"] for p in puppets],
            "duration": round(duration, 1),
            "has_audio": bool(audio_wav_bytes and len(audio_wav_bytes) > 0),
            "created_at": time.time(),
        }

        show_payload = {
            "metadata": show_meta,
            "puppets": puppets,
            "frames": frames,
            "sfx_events": sfx_events,
        }

        # Save companion JSON and audio files atomically
        json_bytes = json.dumps(show_payload).encode("utf-8")
        self.storage.file_write_atomic(f"show_{show_id}.json", json_bytes)
        if audio_wav_bytes:
            self.storage.file_write_atomic(f"show_{show_id}.wav", audio_wav_bytes)

        # Update index
        shows = self.list_shows()
        new_shows = [show_meta, *shows][:MAX_SAVED_SHOWS]
        self.storage.kv_set(SHOWS_INDEX_KEY, new_shows)
        return show_meta

    def load_show(self, show_id: str) -> tuple[dict | None, bytes | None]:
        try:
            raw_json = self.storage.file_read(f"show_{show_id}.json")
            if not raw_json:
                return None, None
            show_data = json.loads(raw_json.decode("utf-8"))
        except Exception:
            return None, None

        audio_bytes = None
        try:
            audio_bytes = self.storage.file_read(f"show_{show_id}.wav")
        except Exception:
            pass

        return show_data, audio_bytes

    def delete_show(self, show_id: str) -> None:
        shows = [s for s in self.list_shows() if s.get("id") != show_id]
        self.storage.kv_set(SHOWS_INDEX_KEY, shows)
        try:
            self.storage.file_delete(f"show_{show_id}.json")
        except Exception:
            pass
        try:
            self.storage.file_delete(f"show_{show_id}.wav")
        except Exception:
            pass


# ============================================================================
# NATIVE MICROPHONE CAPTURE (pygame._sdl2.audio)
# ============================================================================

class MicrophoneRecorder:
    """Non-blocking low-latency microphone capture with live voice waveform."""

    def __init__(self) -> None:
        self.enabled = True
        self.is_recording = False
        self.sample_rate = 22050
        self.recorded_pcm = bytearray()
        self.current_volume = 0.0
        self._dev = None
        self.has_hardware = False

        if sdl2_audio is not None:
            try:
                names = sdl2_audio.get_audio_device_names(True)
                if names:
                    self.has_hardware = True
            except Exception:
                self.has_hardware = False

    def toggle(self) -> bool:
        if not self.has_hardware:
            self.enabled = False
            return False
        self.enabled = not self.enabled
        return self.enabled

    def start_recording(self) -> None:
        self.recorded_pcm.clear()
        self.current_volume = 0.0
        if not self.enabled or not self.has_hardware or sdl2_audio is None:
            self.is_recording = True
            return

        def _audio_callback(dev, data: bytes):
            if not self.is_recording:
                return
            self.recorded_pcm.extend(data)
            if len(data) >= 128:
                try:
                    num_samples = len(data) // 2
                    samples = struct.unpack(f"<{num_samples}h", data[: num_samples * 2])
                    peak = max(abs(s) for s in samples[::8])
                    self.current_volume = min(1.0, peak / 18000.0)
                except Exception:
                    pass

        try:
            self._dev = sdl2_audio.AudioDevice(
                "",
                True,
                self.sample_rate,
                sdl2_audio.AUDIO_S16LSB,
                1,
                1024,
                0,
                _audio_callback,
            )
            self._dev.pause(0)
            self.is_recording = True
        except Exception:
            self._dev = None
            self.is_recording = True

    def stop_recording(self) -> bytes | None:
        if not self.is_recording:
            return None
        self.is_recording = False
        if self._dev is not None:
            try:
                self._dev.pause(1)
                self._dev.close()
            except Exception:
                pass
            self._dev = None

        if not self.recorded_pcm:
            return None

        out_io = io.BytesIO()
        try:
            with wave.open(out_io, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(bytes(self.recorded_pcm))
            return out_io.getvalue()
        except Exception:
            return None


# ============================================================================
# PROCEDURAL SOUND SYNTHESIS
# ============================================================================

class SoundManager:
    """Procedural audio effects for theater cues and magic sound buttons."""

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._enabled = True
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self._build_all_effects()
        except Exception:
            self._enabled = False

    def _build_sound(self, generator_func, duration: float = 0.3) -> pygame.mixer.Sound:
        sample_rate = 22050
        total_samples = int(sample_rate * duration)
        raw = bytearray()
        for i in range(total_samples):
            t = i / float(sample_rate)
            val = generator_func(t, duration)
            sample = int(max(-1.0, min(1.0, val)) * 30000.0)
            raw.extend(struct.pack("<hh", sample, sample))
        return pygame.mixer.Sound(buffer=bytes(raw))

    def _build_all_effects(self) -> None:
        self._sounds["pop"] = self._build_sound(
            lambda t, d: math.sin(2 * math.pi * (300 + 700 * (t / d)) * t) * (1.0 - t / d),
            0.12,
        )
        self._sounds["trumpet"] = self._build_sound(
            lambda t, d: (
                (0.6 * math.sin(2 * math.pi * (523.25 if t < 0.15 else 659.25 if t < 0.3 else 783.99) * t)
                 + 0.3 * math.sin(4 * math.pi * (523.25 if t < 0.15 else 659.25 if t < 0.3 else 783.99) * t))
                * min(1.0, t * 20.0) * (1.0 - t / d)
            ),
            0.55,
        )
        self._sounds["magic"] = self._build_sound(
            lambda t, d: (
                math.sin(2 * math.pi * (800 + 1200 * math.sin(t * 30)) * t)
                * (0.5 + 0.5 * math.sin(t * 80))
                * (1.0 - t / d)
            ),
            0.5,
        )
        self._sounds["applause"] = self._build_sound(
            lambda t, d: (
                (random.random() * 2.0 - 1.0)
                * (0.3 + 0.7 * (math.sin(t * 40) ** 2))
                * (1.0 - (t / d) ** 0.5)
            ),
            0.8,
        )
        self._sounds["giggle"] = self._build_sound(
            lambda t, d: (
                math.sin(2 * math.pi * (600 + 250 * math.sin(t * 35)) * t)
                * min(1.0, t * 15.0)
                * (1.0 - t / d)
            ),
            0.4,
        )
        self._sounds["mystery"] = self._build_sound(
            lambda t, d: (
                (0.7 * math.sin(2 * math.pi * (220 + 80 * math.cos(t * 8)) * t)
                 + 0.3 * math.sin(2 * math.pi * (330 + 120 * math.sin(t * 12)) * t))
                * (1.0 - t / d)
            ),
            0.6,
        )
        self._sounds["boing"] = self._build_sound(
            lambda t, d: (
                math.sin(2 * math.pi * (160 + 600 * math.exp(-t * 8)) * t)
                * (1.0 - t / d)
            ),
            0.35,
        )

    def play(self, sound_name: str) -> None:
        if not self._enabled:
            return
        snd = self._sounds.get(sound_name)
        if snd:
            try:
                snd.play()
            except Exception:
                pass


# ============================================================================
# INTERACTIVE MARIONETTE PUPPET
# ============================================================================

class Puppet:
    """An interactive theatrical puppet with wooden rod and physics."""

    def __init__(self, puppet_id: str, name: str, x: float, y: float) -> None:
        self.puppet_id = puppet_id
        self.name = name
        self.x = float(x)
        self.y = float(y)
        self.target_x = float(x)
        self.target_y = float(y)
        self.is_held = False
        self.flip_x = False
        self.tilt_angle = 0.0
        self.talk_timer = 0.0
        self.jump_timer = 0.0
        self.size = 110
        self.shadow_size = 90
        self._last_x = float(x)

    def contains(self, px: int, py: int) -> bool:
        half = self.size // 2
        return (self.x - half <= px <= self.x + half) and (self.y - half <= py <= self.y + half + 40)

    def jump(self) -> None:
        self.jump_timer = 1.0

    def speak(self) -> None:
        self.talk_timer = 1.0

    def update(self) -> None:
        if self.talk_timer > 0.0:
            self.talk_timer = max(0.0, self.talk_timer - 0.04)
        if self.jump_timer > 0.0:
            self.jump_timer = max(0.0, self.jump_timer - 0.05)

        dx = self.x - self._last_x
        if abs(dx) > 1.5:
            self.flip_x = dx < 0.0
            self.tilt_angle = max(-15.0, min(15.0, -dx * 1.8))
        else:
            self.tilt_angle *= 0.85
        self._last_x = self.x

    def draw(self, surface: pygame.Surface, sprite_img: pygame.Surface, typography: GreiaTypography) -> None:
        self.update()

        # Floor drop shadow
        shadow_rect = pygame.Rect(0, 0, self.shadow_size, 20)
        shadow_rect.center = (int(self.x), 430)
        shadow_surf = pygame.Surface((self.shadow_size, 20), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 85), (0, 0, self.shadow_size, 20))
        surface.blit(shadow_surf, shadow_rect.topleft)

        # Wooden Marionette Control Rod
        rod_top_y = int(self.y + 20)
        pygame.draw.line(surface, (160, 100, 45), (int(self.x), rod_top_y), (int(self.x), 430), 6)
        pygame.draw.line(surface, (210, 150, 80), (int(self.x - 1), rod_top_y), (int(self.x - 1), 430), 2)

        # Calculate Jump & Bob Offset
        jump_offset = math.sin(self.jump_timer * math.pi) * 36.0 if self.jump_timer > 0.0 else 0.0
        talk_offset = math.sin(self.talk_timer * 18.0) * 8.0 if self.talk_timer > 0.0 else 0.0
        render_y = self.y - jump_offset + talk_offset

        # Sprite Transformation
        img = sprite_img
        if self.flip_x:
            img = pygame.transform.flip(img, True, False)
        if abs(self.tilt_angle) > 0.8:
            img = pygame.transform.rotate(img, self.tilt_angle)

        img_rect = img.get_rect(center=(int(self.x), int(render_y)))
        surface.blit(img, img_rect.topleft)

        # Selection / Interaction Glow
        if self.is_held or self.talk_timer > 0.0:
            glow_surf = pygame.Surface((self.size + 30, self.size + 30), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (254, 240, 138, 80), ((self.size + 30) // 2, (self.size + 30) // 2), (self.size + 20) // 2)
            surface.blit(glow_surf, (int(self.x - (self.size + 30) // 2), int(render_y - (self.size + 30) // 2)))


# ============================================================================
# RICH PROCEDURAL BACKDROPS (Cached Surfaces for 0ms Per-Frame Cost)
# ============================================================================

def render_backdrop_surface(bg_id: str) -> pygame.Surface:
    """Pre-render multi-layered storybook scenery to a static high-res surface."""
    surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))

    if bg_id == "cottage":
        # ====================================================================
        # JOYFUL, CHEERFUL SUNNY COTTAGE WITH RAINBOW & BLOOMING GARDEN
        # ====================================================================
        # Bright Sky Gradient
        for y in range(0, 430, 4):
            col = mix((100, 195, 255), (210, 240, 255), y / 430.0)
            pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 4))

        # Golden Shining Sun with Rays
        pygame.draw.circle(surf, (255, 245, 160), (840, 90), 54)
        pygame.draw.circle(surf, (255, 215, 0), (840, 90), 44)
        for ang_deg in range(0, 360, 30):
            ang = math.radians(ang_deg)
            x1 = 840 + math.cos(ang) * 58
            y1 = 90 + math.sin(ang) * 58
            x2 = 840 + math.cos(ang) * 82
            y2 = 90 + math.sin(ang) * 82
            pygame.draw.line(surf, (255, 220, 50), (x1, y1), (x2, y2), 4)

        # 6-Band Vibrant Fairytale Rainbow Arching across the Sky
        rb_colors = [
            (239, 68, 68),   # Red
            (249, 115, 22),  # Orange
            (234, 179, 8),   # Yellow
            (34, 197, 94),   # Green
            (59, 130, 246),  # Blue
            (168, 85, 247),  # Purple
        ]
        for r_idx, r_col in enumerate(rb_colors):
            pygame.draw.arc(surf, r_col, (60, 40 + r_idx * 6, 780, 560), 0.2, math.pi - 0.2, 7)

        # Fluffy Cloud Castles
        for cx, cy, r in ((220, 110, 36), (260, 100, 44), (300, 110, 34), (720, 130, 32), (755, 122, 40), (790, 132, 30)):
            pygame.draw.circle(surf, WHITE, (cx, cy), r)

        # Rolling Bright Green Fairytale Hills
        pygame.draw.circle(surf, (110, 205, 90), (220, 480), 260)
        pygame.draw.circle(surf, (85, 185, 65), (820, 490), 280)
        pygame.draw.circle(surf, (125, 215, 105), (512, 540), 320)

        # Charming Storybook Timber Cottage
        # Cottage Base Walls (Warm Honey Gold Timber)
        cot_x, cot_y, cot_w, cot_h = 420, 220, 184, 175
        pygame.draw.rect(surf, (245, 195, 120), (cot_x, cot_y, cot_w, cot_h), border_radius=12)
        pygame.draw.rect(surf, (135, 75, 25), (cot_x, cot_y, cot_w, cot_h), width=4, border_radius=12)

        # Decorative Timber Beams
        for by in (cot_y + 45, cot_y + 90, cot_y + 135):
            pygame.draw.line(surf, (160, 95, 35), (cot_x, by), (cot_x + cot_w, by), 4)

        # Stone Chimney with Heart Smoke Puffs
        pygame.draw.rect(surf, (148, 163, 184), (cot_x + 120, cot_y - 65, 36, 70), border_radius=4)
        pygame.draw.rect(surf, (71, 85, 105), (cot_x + 116, cot_y - 70, 44, 10), border_radius=3)
        # Smoke puffs
        for sm_x, sm_y, sm_r in ((cot_x + 138, cot_y - 85, 12), (cot_x + 148, cot_y - 110, 16), (cot_x + 162, cot_y - 138, 20)):
            pygame.draw.circle(surf, (255, 255, 255, 200), (sm_x, sm_y), sm_r)

        # Scalloped Bright Red Roof
        roof_poly = [(cot_x - 30, cot_y + 10), (cot_x + cot_w // 2, cot_y - 85), (cot_x + cot_w + 30, cot_y + 10)]
        pygame.draw.polygon(surf, (220, 38, 38), roof_poly)
        pygame.draw.polygon(surf, (153, 27, 27), roof_poly, 4)

        # Scallop Roof Tile Highlights
        for rx in range(cot_x - 10, cot_x + cot_w + 10, 24):
            pygame.draw.circle(surf, (239, 68, 68), (rx, cot_y + 6), 12)

        # Glowing Cozy Windows with Flower Boxes
        for wx in (cot_x + 22, cot_x + 110):
            # Window Frame & Glass
            pygame.draw.rect(surf, (254, 240, 138), (wx, cot_y + 35, 46, 52), border_radius=8)
            pygame.draw.rect(surf, (120, 65, 20), (wx, cot_y + 35, 46, 52), width=3, border_radius=8)
            pygame.draw.line(surf, (120, 65, 20), (wx + 23, cot_y + 35), (wx + 23, cot_y + 87), 2)
            pygame.draw.line(surf, (120, 65, 20), (wx, cot_y + 61), (wx + 46, cot_y + 61), 2)

            # Flower Box
            pygame.draw.rect(surf, (136, 70, 20), (wx - 6, cot_y + 84, 58, 16), border_radius=4)
            # Flowers in box (Pink, Yellow, Red)
            for fx in range(wx - 2, wx + 50, 11):
                f_col = (244, 114, 182) if (fx % 2 == 0) else (250, 204, 21)
                pygame.draw.circle(surf, f_col, (fx, cot_y + 82), 6)
                pygame.draw.circle(surf, WHITE, (fx, cot_y + 82), 2)

        # Wooden Front Door with Heart
        door_x = cot_x + cot_w // 2 - 20
        pygame.draw.rect(surf, (161, 98, 7), (door_x, cot_y + 100, 40, 75), border_top_left_radius=18, border_top_right_radius=18)
        pygame.draw.rect(surf, (69, 26, 3), (door_x, cot_y + 100, 40, 75), width=3, border_top_left_radius=18, border_top_right_radius=18)
        pygame.draw.circle(surf, (254, 240, 138), (door_x + 30, cot_y + 140), 4)

        # Cobblestone Garden Path
        for px, py, pr in ((door_x + 20, cot_y + 185, 14), (door_x + 15, cot_y + 205, 16), (door_x + 28, cot_y + 215, 15)):
            pygame.draw.ellipse(surf, (203, 213, 225), (px - pr, py - 6, pr * 2, 14))
            pygame.draw.ellipse(surf, (148, 163, 184), (px - pr, py - 6, pr * 2, 14), 2)

        # Blooming Sunflower & Tulip Garden Beds
        flower_spots = [
            (160, 400, (239, 68, 68)),
            (210, 415, (244, 114, 182)),
            (270, 395, (250, 204, 21)),
            (340, 420, (168, 85, 247)),
            (680, 410, (250, 204, 21)),
            (740, 395, (239, 68, 68)),
            (800, 418, (244, 114, 182)),
            (860, 402, (59, 130, 246)),
        ]
        for fx, fy, fcol in flower_spots:
            pygame.draw.line(surf, (22, 101, 52), (fx, fy + 24), (fx, fy), 4)
            pygame.draw.circle(surf, fcol, (fx, fy), 12)
            pygame.draw.circle(surf, (254, 240, 138), (fx, fy), 5)

        # Fluttering Butterflies
        for btx, bty, bcol in ((310, 260, (244, 114, 182)), (710, 240, (56, 189, 248)), (820, 280, (250, 204, 21))):
            pygame.draw.ellipse(surf, bcol, (btx - 8, bty - 8, 8, 12))
            pygame.draw.ellipse(surf, bcol, (btx + 2, bty - 8, 8, 12))
            pygame.draw.line(surf, (40, 30, 20), (btx, bty - 6), (btx, bty + 6), 2)

    elif bg_id == "castle":
        # ====================================================================
        # GRAND ROYAL FAIRY TALE CASTLE
        # ====================================================================
        # Indigo Starlit Wall
        for y in range(0, 430, 6):
            col = mix((30, 27, 75), (49, 46, 129), y / 430.0)
            pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 6))

        # Stone Wall Pillars
        for px in range(120, 920, 140):
            pygame.draw.rect(surf, (24, 24, 48), (px, 0, 48, 430))
            pygame.draw.rect(surf, (45, 45, 80), (px, 0, 48, 430), 2)

        # Arched Gothic Stained Glass Windows with Amber/Ruby Glow
        for wx in (260, 476, 692):
            pygame.draw.rect(surf, (255, 230, 140), (wx, 110, 72, 130), border_top_left_radius=36, border_top_right_radius=36)
            pygame.draw.rect(surf, (60, 40, 20), (wx, 110, 72, 130), width=4, border_top_left_radius=36, border_top_right_radius=36)
            # Stained glass grid
            pygame.draw.line(surf, (60, 40, 20), (wx + 36, 110), (wx + 36, 240), 3)
            pygame.draw.line(surf, (60, 40, 20), (wx, 175), (wx + 72, 175), 3)
            pygame.draw.circle(surf, (239, 68, 68), (wx + 36, 140), 14)

        # Royal Heraldic Banners
        for bx, bcol in ((190, (185, 28, 28)), (820, (30, 64, 175))):
            poly = [(bx, 100), (bx + 40, 100), (bx + 40, 220), (bx + 20, 200), (bx, 220)]
            pygame.draw.polygon(surf, bcol, poly)
            pygame.draw.polygon(surf, STAGE_GOLD, poly, 2)
            pygame.draw.circle(surf, STAGE_GOLD, (bx + 20, 140), 6)

        # Grand Brass Chandeliers
        for ch_x in (360, 660):
            pygame.draw.line(surf, STAGE_GOLD, (ch_x, 0), (ch_x, 70), 3)
            pygame.draw.ellipse(surf, STAGE_GOLD, (ch_x - 30, 65, 60, 16), 3)
            for fx in (ch_x - 22, ch_x, ch_x + 22):
                pygame.draw.circle(surf, (255, 245, 180), (fx, 62), 6)
                pygame.draw.circle(surf, (245, 130, 30), (fx, 62), 3)

    elif bg_id == "ocean":
        # ====================================================================
        # UNDERWATER CORAL REEF & SUNBEAMS
        # ====================================================================
        for y in range(0, 430, 6):
            col = mix((10, 40, 90), (16, 120, 175), y / 430.0)
            pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 6))

        # Sunbeam Caustics
        for rx, rw in ((240, 60), (450, 90), (680, 75)):
            beam_poly = [(rx, 0), (rx + rw, 0), (rx + rw + 70, 430), (rx - 40, 430)]
            beam_surf = pygame.Surface((REFERENCE_WIDTH, 430), pygame.SRCALPHA)
            pygame.draw.polygon(beam_surf, (255, 255, 255, 24), beam_poly)
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
        # ====================================================================
        # ENCHANTED TWILIGHT OAK FOREST
        # ====================================================================
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

        # Luminous Bioluminescent Mushrooms
        for mx, mcol in ((300, (236, 72, 153)), (340, (45, 212, 191)), (680, (250, 204, 21)), (720, (192, 132, 252))):
            pygame.draw.rect(surf, (255, 245, 230), (mx - 4, 395, 8, 30), border_radius=3)
            pygame.draw.ellipse(surf, mcol, (mx - 18, 385, 36, 20))
            pygame.draw.circle(surf, WHITE, (mx - 6, 392), 3)

    elif bg_id == "sky":
        # ====================================================================
        # DREAMY CLOUD CASTLE & STARRY SKY
        # ====================================================================
        for y in range(0, 430, 6):
            col = mix((40, 24, 75), (90, 50, 135), y / 430.0)
            pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 6))

        # Smiling Golden Crescent Moon
        pygame.draw.circle(surf, (254, 240, 138), (720, 110), 48)
        pygame.draw.circle(surf, (40, 24, 75), (700, 100), 44)

        # Planetary Rings
        pygame.draw.circle(surf, (249, 115, 22), (280, 120), 30)
        pygame.draw.ellipse(surf, (254, 215, 170), (235, 114, 90, 12), width=3)

        # Dream Clouds
        for cx, cy in ((200, 350), (512, 330), (800, 360)):
            for ox, oy, r in ((-35, 10, 32), (0, -10, 42), (35, 10, 32)):
                pygame.draw.circle(surf, (240, 230, 255), (cx + ox, cy + oy), r)

    # Floor / Stage Boards (Warm Polished Mahogany Wood)
    for y in range(430, REFERENCE_HEIGHT):
        col = mix(STAGE_WOOD_TOP, STAGE_WOOD_BASE, (y - 430) / (REFERENCE_HEIGHT - 430))
        pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 1))

    # Stage Floor Planks Placed with Perspective
    for px in range(0, REFERENCE_WIDTH + 80, 80):
        pygame.draw.line(surf, (90, 45, 15), (px, 430), (int(px * 1.1 - 40), REFERENCE_HEIGHT), 2)

    # Stage Floor Front Brass Lip
    pygame.draw.rect(surf, STAGE_GOLD, (0, 430, REFERENCE_WIDTH, 4))
    return surf


# ============================================================================
# AMBIENT STAGE SPARKS
# ============================================================================

class AmbientSpark:
    def __init__(self, bg_id: str) -> None:
        self.bg_id = bg_id
        self.x = random.uniform(140, 900)
        self.y = random.uniform(80, 420)
        self.speed_y = random.uniform(-0.6, -0.2)
        self.speed_x = random.uniform(-0.3, 0.3)
        self.alpha = random.uniform(0.3, 1.0)
        self.size = random.uniform(2.0, 4.5)

    def update(self) -> None:
        self.y += self.speed_y
        self.x += self.speed_x
        self.alpha -= 0.008
        if self.y < 70 or self.alpha <= 0.0:
            self.x = random.uniform(140, 900)
            self.y = random.uniform(320, 420)
            self.alpha = random.uniform(0.6, 1.0)

    def draw(self, surface: pygame.Surface) -> None:
        if self.alpha <= 0.0:
            return
        col = (254, 240, 138) if self.bg_id in ("forest", "sky") else (200, 240, 255)
        spark_surf = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
        pygame.draw.circle(spark_surf, (*col, int(self.alpha * 180)), (int(self.size), int(self.size)), int(self.size))
        surface.blit(spark_surf, (int(self.x - self.size), int(self.y - self.size)))


# ============================================================================
# MAIN ENTRYPOINT & SCENE LOOP
# ============================================================================

def main() -> int:
    os.environ["SDL_VIDEO_ALLOW_SCALING"] = "1"
    pygame.init()
    pygame.font.init()

    canvas = ChildUiMetrics.create_reference_canvas(REFERENCE_WIDTH, REFERENCE_HEIGHT)
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))

    pygame.display.set_caption("Teatrino delle Fiabe")
    clock = pygame.time.Clock()
    theme = get_theme()
    typography = GreiaTypography()
    storage = get_storage("org.greia.teatrino-fiabe")
    show_repo = ShowRepository(storage)

    # 1. Load Localizations
    locales_dir = Path(__file__).resolve().parent / "locales"
    it_file = locales_dir / "it.json"
    ui_strings = {}
    puppet_names = {}
    if it_file.is_file():
        try:
            loc_data = json.loads(it_file.read_text(encoding="utf-8"))
            ui_strings = loc_data.get("ui", {})
            puppet_names = loc_data.get("puppets", {})
        except Exception:
            pass

    # 2. Load Sprites for all 16 Characters
    runtime_dir = Path(__file__).resolve().parent / "assets" / "runtime"
    puppet_sprites: dict[str, pygame.Surface] = {}
    for p_id, p_name in PUPPET_ROSTER:
        png_path = runtime_dir / f"puppet_{p_id}.png"
        if png_path.is_file():
            try:
                img = pygame.image.load(str(png_path)).convert_alpha()
                puppet_sprites[p_id] = pygame.transform.smoothscale(img, (110, 110))
            except Exception:
                pass

    # Fallback placeholder sprite if any fails to load
    if "lilli" not in puppet_sprites:
        fb_s = pygame.Surface((110, 110), pygame.SRCALPHA)
        pygame.draw.circle(fb_s, (244, 114, 182), (55, 55), 45)
        puppet_sprites["lilli"] = fb_s

    # 3. Pre-render & Cache All 5 Storybook Backdrops
    cached_backdrops: dict[str, pygame.Surface] = {}
    for bg_id, _, _ in BG_CONFIGS:
        cached_backdrops[bg_id] = render_backdrop_surface(bg_id)

    sound_mgr = SoundManager()
    mic_recorder = MicrophoneRecorder()

    # Ambient Magic Particles
    sparks = [AmbientSpark("cottage") for _ in range(16)]

    # State Variables
    active_bg_idx = 0
    puppets_on_stage: list[Puppet] = [
        Puppet("lilli", puppet_names.get("lilli", "Lilli"), 380, 270),
        Puppet("draghetto", puppet_names.get("draghetto", "Draghetto"), 600, 270),
    ]
    puppets_on_stage[1].flip_x = True

    held_puppet: Puppet | None = None
    held_offset_x = 0.0
    held_offset_y = 0.0

    # Tray Pagination (6 puppets per page across 3 pages for 16 puppets)
    tray_page = 0
    puppets_per_page = 6
    max_tray_pages = (len(PUPPET_ROSTER) + puppets_per_page - 1) // puppets_per_page

    # UI Modes
    # "stage" | "library" | "viewer"
    app_mode = "stage"

    # Recording Engine
    is_recording = False
    rec_start_time = 0.0
    recorded_frames: list[dict] = []
    recorded_sfx: list[dict] = []
    feedback_text = ""
    feedback_timer = 0.0

    # Playback Engine (for Stage Show & Viewer)
    is_playing_show = False
    play_start_time = 0.0
    playback_frames: list[dict] = []
    playback_sfx: list[dict] = []
    playback_audio_channel: pygame.mixer.Channel | None = None
    playback_duration = 0.0
    playback_show_meta: dict | None = None

    # Library Modal State
    library_page = 0
    library_shows = show_repo.list_shows()

    mark_activity_ready()

    def _is_safe_point(s: pygame.Surface, pos: tuple[int, int]) -> bool:
        w, h = s.get_size()
        r = ChildUiMetrics.safe_region(w, h)
        return r.collidepoint(pos)

    # ========================================================================
    # MAIN LOOP
    # ========================================================================
    running = True
    while running and not activity_stop_requested():
        dt = clock.tick(30) / 1000.0

        if feedback_timer > 0.0:
            feedback_timer -= dt
            if feedback_timer <= 0.0:
                feedback_text = ""

        # Update ambient particles
        active_bg_id = BG_CONFIGS[active_bg_idx][0]
        for sp in sparks:
            sp.bg_id = active_bg_id
            sp.update()

        # Update puppets
        for p in puppets_on_stage:
            p.update()

        # --------------------------------------------------------------------
        # RECORDING RUNTIME LOGIC
        # --------------------------------------------------------------------
        if is_recording:
            elapsed = time.time() - rec_start_time
            if elapsed >= MAX_RECORDING_SECONDS:
                # Max duration reached -> Auto save show to library!
                is_recording = False
                wav_bytes = mic_recorder.stop_recording()
                saved_meta = show_repo.save_show(
                    active_bg_id,
                    [{"id": p.puppet_id, "name": p.name} for p in puppets_on_stage],
                    recorded_frames,
                    recorded_sfx,
                    elapsed,
                    wav_bytes,
                )
                library_shows = show_repo.list_shows()
                feedback_text = f"🎉 {ui_strings.get('recording_saved', 'Spettacolo salvato nella libreria!')}"
                feedback_timer = 4.0
                emit_activity_event("story.recorded", {"duration": round(elapsed, 1), "id": saved_meta["id"]})
                sound_mgr.play("applause")
            else:
                # Capture frame snapshot (timestamp, positions, flips, jump/talk timers)
                frame_data = {
                    "t": round(elapsed, 2),
                    "puppets": [
                        {
                            "id": p.puppet_id,
                            "x": round(p.x, 1),
                            "y": round(p.y, 1),
                            "flip": p.flip_x,
                            "jumping": p.jump_timer > 0.0,
                            "talking": p.talk_timer > 0.0,
                        }
                        for p in puppets_on_stage
                    ],
                }
                recorded_frames.append(frame_data)

        # --------------------------------------------------------------------
        # PLAYBACK RUNTIME LOGIC (Stage Show or Dedicated Viewer)
        # --------------------------------------------------------------------
        if is_playing_show:
            play_elapsed = time.time() - play_start_time
            if play_elapsed >= playback_duration:
                is_playing_show = False
                feedback_text = "👏 Evviva lo Spettacolo!"
                feedback_timer = 3.0
                sound_mgr.play("applause")
            else:
                # Interpolate puppet positions
                if playback_frames:
                    prev_f = playback_frames[0]
                    next_f = playback_frames[-1]
                    for f in playback_frames:
                        if f["t"] <= play_elapsed:
                            prev_f = f
                        else:
                            next_f = f
                            break
                    
                    # Apply interpolated state
                    span = max(0.01, next_f["t"] - prev_f["t"])
                    ratio = min(1.0, max(0.0, (play_elapsed - prev_f["t"]) / span))
                    for p_data in prev_f["puppets"]:
                        for live_p in puppets_on_stage:
                            if live_p.puppet_id == p_data["id"]:
                                target_x = p_data["x"]
                                target_y = p_data["y"]
                                # Match in next frame
                                for np in next_f["puppets"]:
                                    if np["id"] == p_data["id"]:
                                        target_x = p_data["x"] + (np["x"] - p_data["x"]) * ratio
                                        target_y = p_data["y"] + (np["y"] - p_data["y"]) * ratio
                                        break
                                live_p.x = target_x
                                live_p.y = target_y
                                live_p.flip_x = p_data["flip"]
                                if p_data["jumping"] and live_p.jump_timer <= 0.0:
                                    live_p.jump()
                                if p_data["talking"] and live_p.talk_timer <= 0.0:
                                    live_p.speak()

                # Trigger timed SFX
                for sfx in list(playback_sfx):
                    if sfx["t"] <= play_elapsed:
                        sound_mgr.play(sfx["sound"])
                        playback_sfx.remove(sfx)

        # --------------------------------------------------------------------
        # EVENT HANDLING
        # --------------------------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = event.pos
                if not _is_safe_point(screen, mouse_pos):
                    continue

                rx, ry = canvas.to_reference(mouse_pos)

                # ============================================================
                # MODE: LIBRARY GALLERY MODAL
                # ============================================================
                if app_mode == "library":
                    # Close Button [❌] (x: 880..930, y: 70..120)
                    if 870 <= rx <= 930 and 70 <= ry <= 130:
                        sound_mgr.play("pop")
                        app_mode = "stage"
                        continue

                    # Card interactions
                    cards_per_page = 4
                    visible_shows = library_shows[library_page * cards_per_page : (library_page + 1) * cards_per_page]
                    for s_idx, show_item in enumerate(visible_shows):
                        card_y = 150 + s_idx * 90
                        # Play Show Button [▶️ Guarda] (x: 670..770, y: card_y + 16 .. card_y + 68)
                        if 670 <= rx <= 770 and card_y + 12 <= ry <= card_y + 68:
                            show_data, wav_bytes = show_repo.load_show(show_item["id"])
                            if show_data:
                                sound_mgr.play("trumpet")
                                # Setup Viewer Mode
                                app_mode = "viewer"
                                is_playing_show = True
                                play_start_time = time.time()
                                playback_show_meta = show_item
                                playback_frames = show_data.get("frames", [])
                                playback_sfx = list(show_data.get("sfx_events", []))
                                playback_duration = show_item.get("duration", 10.0)

                                # Set backdrop
                                saved_bg = show_item.get("backdrop", "cottage")
                                for b_idx, (b_id, _, _) in enumerate(BG_CONFIGS):
                                    if b_id == saved_bg:
                                        active_bg_idx = b_idx
                                        break

                                # Instantiate puppets
                                puppets_on_stage = []
                                for p_meta in show_data.get("puppets", []):
                                    p_obj = Puppet(
                                        p_meta["id"],
                                        puppet_names.get(p_meta["id"], p_meta.get("name", "Puppet")),
                                        512,
                                        270,
                                    )
                                    puppets_on_stage.append(p_obj)

                                # Play audio track
                                if wav_bytes:
                                    try:
                                        snd = pygame.mixer.Sound(io.BytesIO(wav_bytes))
                                        snd.play()
                                    except Exception:
                                        pass
                            break

                        # Delete Show Button [🗑️] (x: 785..845, y: card_y + 12 .. card_y + 68)
                        if 785 <= rx <= 845 and card_y + 12 <= ry <= card_y + 68:
                            sound_mgr.play("boing")
                            show_repo.delete_show(show_item["id"])
                            library_shows = show_repo.list_shows()
                            break

                    continue

                # ============================================================
                # MODE: VIEWER FULL-THEATER MODE
                # ============================================================
                if app_mode == "viewer":
                    # Exit Viewer Button [⏹️ Esci] (x: 140..250, y: 16..68)
                    if 140 <= rx <= 250 and 16 <= ry <= 68:
                        sound_mgr.play("pop")
                        is_playing_show = False
                        app_mode = "stage"
                        continue

                    # Replay Button [🔁 Rivedi] (x: 270..380, y: 16..68)
                    if 270 <= rx <= 380 and 16 <= ry <= 68:
                        if playback_show_meta:
                            sound_mgr.play("trumpet")
                            is_playing_show = True
                            play_start_time = time.time()
                            show_data, wav_bytes = show_repo.load_show(playback_show_meta["id"])
                            if show_data:
                                playback_frames = show_data.get("frames", [])
                                playback_sfx = list(show_data.get("sfx_events", []))
                                if wav_bytes:
                                    try:
                                        snd = pygame.mixer.Sound(io.BytesIO(wav_bytes))
                                        snd.play()
                                    except Exception:
                                        pass
                        continue

                # ============================================================
                # MODE: STAGE EDITOR (Main Mode)
                # ============================================================
                # --- TOP TOOLBAR ---
                # 1. Microphone Toggle Button [🎙️ ON/OFF] (x: 140..215, y: 16..68)
                if 140 <= rx <= 215 and 16 <= ry <= 68:
                    sound_mgr.play("pop")
                    new_state = mic_recorder.toggle()
                    feedback_text = "🎙️ Microfono ATTIVO" if new_state else "🔇 Microfono DISATTIVATO"
                    feedback_timer = 2.5
                    continue

                # 2. Show Library Button [🎬 Storie (N)] (x: 225..345, y: 16..68)
                if 225 <= rx <= 345 and 16 <= ry <= 68:
                    sound_mgr.play("pop")
                    library_shows = show_repo.list_shows()
                    app_mode = "library"
                    continue

                # 3. Record Button [🔴 REC] / [⏹️ STOP] (x: 415..545, y: 16..68)
                if 415 <= rx <= 545 and 16 <= ry <= 68:
                    if not is_recording:
                        # START RECORDING
                        is_recording = True
                        rec_start_time = time.time()
                        recorded_frames = []
                        recorded_sfx = []
                        mic_recorder.start_recording()
                        feedback_text = f"🔴 {ui_strings.get('recording_active', 'Registrazione in corso... Racconta la tua storia!')}"
                        feedback_timer = 3.0
                        sound_mgr.play("trumpet")
                    else:
                        # STOP RECORDING -> SAVE SHOW
                        is_recording = False
                        elapsed = max(0.5, time.time() - rec_start_time)
                        wav_bytes = mic_recorder.stop_recording()
                        saved_meta = show_repo.save_show(
                            active_bg_id,
                            [{"id": p.puppet_id, "name": p.name} for p in puppets_on_stage],
                            recorded_frames,
                            recorded_sfx,
                            elapsed,
                            wav_bytes,
                        )
                        library_shows = show_repo.list_shows()
                        feedback_text = f"🎉 {ui_strings.get('recording_saved', 'Spettacolo salvato nella libreria!')}"
                        feedback_timer = 3.5
                        emit_activity_event("story.recorded", {"duration": round(elapsed, 1), "id": saved_meta["id"]})
                        sound_mgr.play("applause")
                    continue

                # 4. Play Show Button [▶️ SHOW] (x: 560..690, y: 16..68)
                if 560 <= rx <= 690 and 16 <= ry <= 68:
                    if recorded_frames:
                        # Replay latest recording
                        is_playing_show = True
                        play_start_time = time.time()
                        playback_frames = list(recorded_frames)
                        playback_sfx = list(recorded_sfx)
                        playback_duration = max(2.0, recorded_frames[-1]["t"])
                        feedback_text = f"▶️ {ui_strings.get('playing_show', 'Spettacolo in corso! Evviva!')}"
                        feedback_timer = 3.0
                        sound_mgr.play("trumpet")
                    else:
                        # Play built-in show demo
                        is_playing_show = True
                        play_start_time = time.time()
                        playback_duration = 5.0
                        for p in puppets_on_stage:
                            p.jump()
                            p.speak()
                        sound_mgr.play("trumpet")
                        feedback_text = "▶️ Spettacolo delle Marionette!"
                        feedback_timer = 3.0
                    continue

                # 5. Clear Stage Button [🗑️] (x: 740..805, y: 16..68)
                if 740 <= rx <= 805 and 16 <= ry <= 68:
                    sound_mgr.play("boing")
                    puppets_on_stage.clear()
                    feedback_text = f"✨ {ui_strings.get('stage_cleared', 'Palcoscenico pronto!')}"
                    feedback_timer = 2.0
                    continue

                # --- RIGHT SIDEBAR: MAGIC DECK (x: 915..985) ---
                # 6. Scene Change Button [🖼️] AT THE TOP OF THE SIDEBAR (y: 24..78)
                if 915 <= rx <= 985 and 24 <= ry <= 78:
                    sound_mgr.play("magic")
                    active_bg_idx = (active_bg_idx + 1) % len(BG_CONFIGS)
                    feedback_text = f"✨ Scena: {BG_CONFIGS[active_bg_idx][2]}"
                    feedback_timer = 2.0
                    continue

                # 7. Sound Effect Magic Buttons (y: 88..440)
                fx_clicked = False
                for f_idx, (fx_id, _) in enumerate(FX_BUTTONS):
                    fy = 88 + f_idx * 58
                    if 915 <= rx <= 985 and fy <= ry <= fy + 52:
                        sound_mgr.play(fx_id)
                        for p in puppets_on_stage:
                            p.jump()
                        if is_recording:
                            recorded_sfx.append({"t": round(time.time() - rec_start_time, 2), "sound": fx_id})
                        fx_clicked = True
                        break
                if fx_clicked:
                    continue

                # --- BOTTOM PUPPET TRAY (y: 500..600) ---
                if ry >= 500:
                    # Page Left Arrow [◀] (x: 40..94, y: 522..576)
                    if 40 <= rx <= 94 and 522 <= ry <= 576:
                        sound_mgr.play("pop")
                        tray_page = (tray_page - 1) % max_tray_pages
                        continue

                    # Page Right Arrow [▶] (x: 930..984, y: 522..576)
                    if 930 <= rx <= 984 and 522 <= ry <= 576:
                        sound_mgr.play("pop")
                        tray_page = (tray_page + 1) % max_tray_pages
                        continue

                    # Character Selection Cards on current page
                    page_puppets = PUPPET_ROSTER[tray_page * puppets_per_page : (tray_page + 1) * puppets_per_page]
                    for p_idx, (p_id, p_name) in enumerate(page_puppets):
                        card_x = 110 + p_idx * 135
                        if card_x <= rx <= card_x + 120 and 508 <= ry <= 592:
                            sound_mgr.play("pop")
                            # Add character to stage
                            loc_name = puppet_names.get(p_id, p_name)
                            spawn_x = random.randint(300, 720)
                            new_puppet = Puppet(p_id, loc_name, spawn_x, 270)
                            new_puppet.jump()
                            puppets_on_stage.append(new_puppet)
                            break
                    continue

                # --- STAGE PUPPET DRAG & DROP SELECTION ---
                for p in reversed(puppets_on_stage):
                    if p.contains(rx, ry):
                        held_puppet = p
                        p.is_held = True
                        p.speak()
                        sound_mgr.play("pop")
                        held_offset_x = p.x - rx
                        held_offset_y = p.y - ry
                        # Bring to front
                        puppets_on_stage.remove(p)
                        puppets_on_stage.append(p)
                        break

            elif event.type == pygame.MOUSEMOTION:
                if held_puppet is not None:
                    rx, ry = canvas.to_reference(event.pos)
                    held_puppet.x = max(180, min(840, rx + held_offset_x))
                    held_puppet.y = max(160, min(360, ry + held_offset_y))

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if held_puppet is not None:
                    held_puppet.is_held = False
                    held_puppet = None

        # --------------------------------------------------------------------
        # RENDERING PIPELINE
        # --------------------------------------------------------------------
        surf = canvas.surface

        # 1. Background Scenery (0ms blit from pre-rendered cache)
        active_bg_id = BG_CONFIGS[active_bg_idx][0]
        surf.blit(cached_backdrops[active_bg_id], (0, 0))

        # 2. Ambient Sparks
        for sp in sparks:
            sp.draw(surf)

        # 3. Puppets on Stage
        for p in puppets_on_stage:
            spr = puppet_sprites.get(p.puppet_id, puppet_sprites["lilli"])
            p.draw(surf, spr, typography)

        # 4. Stage Curtains & Velvet Valance Drapery
        # Side Curtains
        pygame.draw.polygon(surf, STAGE_CURTAIN_DARK, [(0, 0), (130, 0), (70, 440), (0, 440)])
        pygame.draw.polygon(surf, STAGE_CURTAIN, [(0, 0), (110, 0), (55, 430), (0, 430)])
        pygame.draw.polygon(surf, STAGE_CURTAIN_LIGHT, [(0, 0), (70, 0), (35, 420), (0, 420)])

        pygame.draw.polygon(surf, STAGE_CURTAIN_DARK, [(REFERENCE_WIDTH, 0), (REFERENCE_WIDTH - 130, 0), (REFERENCE_WIDTH - 70, 440), (REFERENCE_WIDTH, 440)])
        pygame.draw.polygon(surf, STAGE_CURTAIN, [(REFERENCE_WIDTH, 0), (REFERENCE_WIDTH - 110, 0), (REFERENCE_WIDTH - 55, 430), (REFERENCE_WIDTH, 430)])
        pygame.draw.polygon(surf, STAGE_CURTAIN_LIGHT, [(REFERENCE_WIDTH, 0), (REFERENCE_WIDTH - 70, 0), (REFERENCE_WIDTH - 35, 420), (REFERENCE_WIDTH, 420)])

        # Top Valance Swags
        for vx in range(120, 890, 110):
            pygame.draw.circle(surf, STAGE_CURTAIN_DARK, (vx + 55, 24), 68)
            pygame.draw.circle(surf, STAGE_CURTAIN, (vx + 55, 24), 62)
            pygame.draw.circle(surf, STAGE_GOLD, (vx + 55, 24), 62, width=2)
            pygame.draw.circle(surf, STAGE_GOLD, (vx + 55, 86), 4)

        # Proscenium Top Bar & Brass Molding
        pygame.draw.rect(surf, (60, 40, 15), (0, 0, REFERENCE_WIDTH, 14))
        pygame.draw.rect(surf, STAGE_GOLD, (0, 10, REFERENCE_WIDTH, 4))

        # --------------------------------------------------------------------
        # 5. TOP TOOLBAR (Ergonomic & Separated)
        # --------------------------------------------------------------------
        if app_mode == "stage":
            # LEFT DECK: Mic & Story Library (x: 140..345)
            # A) Mic Toggle Button [🎙️ ON/OFF]
            mic_rect = pygame.Rect(140, 16, 75, 52)
            mic_bg = (220, 255, 225) if mic_recorder.enabled else (255, 230, 230)
            mic_border = MIC_GREEN if mic_recorder.enabled else (220, 38, 38)
            pygame.draw.rect(surf, mic_bg, mic_rect, border_radius=14)
            pygame.draw.rect(surf, mic_border, mic_rect, width=3, border_radius=14)
            mic_label = f"🎙️ {ui_strings.get('mic_on', 'ON')}" if mic_recorder.enabled else f"🔇 {ui_strings.get('mic_off', 'OFF')}"
            mic_s = typography.render(mic_label, FontRole.TITLE, 14, mic_border)
            surf.blit(mic_s, (mic_rect.centerx - mic_s.get_width() // 2, mic_rect.centery - mic_s.get_height() // 2))

            # B) Show Library Button [🎬 Storie (N)]
            lib_rect = pygame.Rect(225, 16, 120, 52)
            pygame.draw.rect(surf, (255, 250, 240), lib_rect, border_radius=14)
            pygame.draw.rect(surf, (61, 44, 31), lib_rect, width=2, border_radius=14)
            num_saved = len(library_shows)
            lib_label = f"🎬 {ui_strings.get('stories', 'Storie')} ({num_saved})"
            lib_s = typography.render(lib_label, FontRole.TITLE, 14, DARK_TEXT)
            surf.blit(lib_s, (lib_rect.centerx - lib_s.get_width() // 2, lib_rect.centery - lib_s.get_height() // 2))

            # CENTER DECK: Record & Play (x: 415..690) - Separated with 70px gap!
            # C) Record Button [🔴 REC] / [⏹️ STOP]
            rec_rect = pygame.Rect(415, 16, 130, 52)
            if is_recording:
                pygame.draw.rect(surf, (255, 210, 210), rec_rect, border_radius=14)
                pygame.draw.rect(surf, REC_RED, rec_rect, width=3, border_radius=14)
                rec_label = f"⏹️ {ui_strings.get('stop', 'STOP')}"
                rec_s = typography.render(rec_label, FontRole.TITLE, 16, REC_RED)
                surf.blit(rec_s, (rec_rect.centerx - rec_s.get_width() // 2, rec_rect.centery - rec_s.get_height() // 2))

                # Live Voice Waveform Sound Meter
                meter_x = 425
                meter_y = 72
                vol = mic_recorder.current_volume
                for bar_idx in range(5):
                    bar_h = int(4 + math.sin(time.time() * 12 + bar_idx * 1.5) * 8 * vol + vol * 14)
                    pygame.draw.rect(surf, REC_RED, (meter_x + bar_idx * 6, meter_y + (20 - bar_h) // 2, 4, bar_h), border_radius=2)
                t_str = f"{int(time.time() - rec_start_time)}s / {int(MAX_RECORDING_SECONDS)}s"
                t_surf = typography.render(t_str, FontRole.CONTROL, 11, REC_RED)
                surf.blit(t_surf, (meter_x + 36, meter_y + 3))
            else:
                pygame.draw.rect(surf, (255, 250, 240), rec_rect, border_radius=14)
                pygame.draw.rect(surf, (61, 44, 31), rec_rect, width=2, border_radius=14)
                rec_label = f"🔴 {ui_strings.get('rec', 'REC')}"
                rec_s = typography.render(rec_label, FontRole.TITLE, 16, DARK_TEXT)
                surf.blit(rec_s, (rec_rect.centerx - rec_s.get_width() // 2, rec_rect.centery - rec_s.get_height() // 2))

            # D) Play Show Button [▶️ SHOW]
            play_rect = pygame.Rect(560, 16, 130, 52)
            pygame.draw.rect(surf, (255, 250, 240), play_rect, border_radius=14)
            pygame.draw.rect(surf, (61, 44, 31), play_rect, width=2, border_radius=14)
            play_label = f"▶️ {ui_strings.get('show', 'SHOW')}"
            ply_s = typography.render(play_label, FontRole.TITLE, 16, DARK_TEXT)
            surf.blit(ply_s, (play_rect.centerx - ply_s.get_width() // 2, play_rect.centery - ply_s.get_height() // 2))

            # RIGHT DECK: Clear Stage Button [🗑️]
            clear_rect = pygame.Rect(740, 16, 65, 52)
            pygame.draw.rect(surf, (255, 250, 240), clear_rect, border_radius=14)
            pygame.draw.rect(surf, (61, 44, 31), clear_rect, width=2, border_radius=14)
            clr_s = typography.render("🗑️", FontRole.TITLE, 22, DARK_TEXT)
            surf.blit(clr_s, (clear_rect.centerx - clr_s.get_width() // 2, clear_rect.centery - clr_s.get_height() // 2))

        elif app_mode == "viewer":
            # VIEWER CONTROLS: [⏹️ Esci] and [🔁 Rivedi]
            exit_rect = pygame.Rect(140, 16, 110, 52)
            pygame.draw.rect(surf, (255, 230, 230), exit_rect, border_radius=14)
            pygame.draw.rect(surf, (220, 38, 38), exit_rect, width=2, border_radius=14)
            exit_s = typography.render(f"⏹️ {ui_strings.get('exit_viewer', 'Esci')}", FontRole.TITLE, 15, (185, 28, 28))
            surf.blit(exit_s, (exit_rect.centerx - exit_s.get_width() // 2, exit_rect.centery - exit_s.get_height() // 2))

            rep_rect = pygame.Rect(265, 16, 120, 52)
            pygame.draw.rect(surf, (255, 250, 240), rep_rect, border_radius=14)
            pygame.draw.rect(surf, (61, 44, 31), rep_rect, width=2, border_radius=14)
            rep_s = typography.render(f"🔁 {ui_strings.get('replay_story', 'Rivedi')}", FontRole.TITLE, 15, DARK_TEXT)
            surf.blit(rep_s, (rep_rect.centerx - rep_s.get_width() // 2, rep_rect.centery - rep_s.get_height() // 2))

        # --------------------------------------------------------------------
        # 6. RIGHT SIDEBAR: MAGIC DECK (Scene on Top, then Sound FX)
        # --------------------------------------------------------------------
        if app_mode == "stage":
            # Scene Change Button on Top (y: 24..78)
            sc_icon, sc_name = BG_CONFIGS[active_bg_idx][1], BG_CONFIGS[active_bg_idx][2]
            sc_rect = pygame.Rect(915, 24, 70, 54)
            pygame.draw.rect(surf, (255, 250, 240), sc_rect, border_radius=14)
            pygame.draw.rect(surf, STAGE_GOLD, sc_rect, width=3, border_radius=14)
            sc_s = typography.render(sc_icon, FontRole.DISPLAY, 26, DARK_TEXT)
            surf.blit(sc_s, (sc_rect.centerx - sc_s.get_width() // 2, sc_rect.centery - sc_s.get_height() // 2 - 4))
            sc_lbl = typography.render(ui_strings.get("scene", "Scena"), FontRole.CONTROL, 10, DARK_TEXT)
            surf.blit(sc_lbl, (sc_rect.centerx - sc_lbl.get_width() // 2, sc_rect.bottom - 13))

            # 6 Sound Effect Buttons Underneath (y: 88..440)
            for f_idx, (fx_id, fx_sym) in enumerate(FX_BUTTONS):
                fy = 88 + f_idx * 58
                fx_rect = pygame.Rect(915, fy, 70, 50)
                pygame.draw.rect(surf, (255, 250, 240), fx_rect, border_radius=14)
                pygame.draw.rect(surf, STAGE_GOLD, fx_rect, width=2, border_radius=14)
                fx_s = typography.render(fx_sym, FontRole.DISPLAY, 26, DARK_TEXT)
                surf.blit(fx_s, (fx_rect.centerx - fx_s.get_width() // 2, fx_rect.centery - fx_s.get_height() // 2))

        # --------------------------------------------------------------------
        # 7. BOTTOM PUPPET TRAY (Pagination for 16 Characters)
        # --------------------------------------------------------------------
        if app_mode == "stage":
            pygame.draw.rect(surf, (30, 24, 40), (0, 500, REFERENCE_WIDTH, 100))
            pygame.draw.rect(surf, STAGE_GOLD, (0, 500, REFERENCE_WIDTH, 4))

            # Page Left Arrow [◀]
            tray_prev_rect = pygame.Rect(40, 522, 54, 54)
            pygame.draw.rect(surf, (255, 250, 240), tray_prev_rect, border_radius=12)
            pygame.draw.rect(surf, STAGE_GOLD, tray_prev_rect, width=2, border_radius=12)
            cx, cy = tray_prev_rect.center
            pygame.draw.polygon(surf, (61, 44, 31), [(cx - 8, cy), (cx + 6, cy - 10), (cx + 6, cy + 10)])

            # Page Right Arrow [▶]
            tray_next_rect = pygame.Rect(930, 522, 54, 54)
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

                # Thumbnail Sprite
                spr = puppet_sprites.get(p_id, puppet_sprites["lilli"])
                thumb = pygame.transform.smoothscale(spr, (52, 52))
                surf.blit(thumb, (card_rect.centerx - 26, card_rect.y + 6))

                # Localized Puppet Name
                loc_name = puppet_names.get(p_id, p_name)
                name_s = typography.render(loc_name, FontRole.CONTROL, 11, DARK_TEXT)
                surf.blit(name_s, (card_rect.centerx - name_s.get_width() // 2, card_rect.y + 63))

        # --------------------------------------------------------------------
        # 8. LIBRARY MODAL GALLERY OVERLAY
        # --------------------------------------------------------------------
        if app_mode == "library":
            # Dim Background
            modal_overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            modal_overlay.fill((10, 8, 20, 220))
            surf.blit(modal_overlay, (0, 0))

            # Modal Box
            box_rect = pygame.Rect(100, 50, 824, 500)
            pygame.draw.rect(surf, (255, 250, 240), box_rect, border_radius=20)
            pygame.draw.rect(surf, STAGE_GOLD, box_rect, width=4, border_radius=20)

            # Header
            hdr_surf = typography.render(f"🎬 {ui_strings.get('stories', 'Storie Magiche')}", FontRole.DISPLAY, 26, DARK_TEXT)
            surf.blit(hdr_surf, (box_rect.centerx - hdr_surf.get_width() // 2, box_rect.y + 20))

            # Close [❌] Button
            cls_rect = pygame.Rect(box_rect.right - 55, box_rect.y + 15, 40, 40)
            pygame.draw.rect(surf, (254, 226, 226), cls_rect, border_radius=10)
            pygame.draw.rect(surf, (220, 38, 38), cls_rect, width=2, border_radius=10)
            cx, cy = cls_rect.center
            pygame.draw.line(surf, (185, 28, 28), (cx - 8, cy - 8), (cx + 8, cy + 8), 3)
            pygame.draw.line(surf, (185, 28, 28), (cx + 8, cy - 8), (cx - 8, cy + 8), 3)

            # Saved Shows List
            if not library_shows:
                no_s = typography.render(ui_strings.get("no_stories", "Nessuna storia salvata! Registra uno spettacolo!"), FontRole.TITLE, 18, (140, 100, 60))
                surf.blit(no_s, (box_rect.centerx - no_s.get_width() // 2, box_rect.centery - 20))
            else:
                cards_per_page = 4
                visible_shows = library_shows[library_page * cards_per_page : (library_page + 1) * cards_per_page]
                for s_idx, show_item in enumerate(visible_shows):
                    card_y = 100 + s_idx * 95
                    c_rect = pygame.Rect(box_rect.x + 30, card_y, box_rect.width - 60, 82)
                    pygame.draw.rect(surf, (248, 240, 225), c_rect, border_radius=14)
                    pygame.draw.rect(surf, (180, 140, 90), c_rect, width=2, border_radius=14)

                    # Backdrop & Actor Thumbnails
                    bg_sym = "🏡"
                    for b_id, b_sym, _ in BG_CONFIGS:
                        if b_id == show_item.get("backdrop"):
                            bg_sym = b_sym
                            break
                    bg_icon_s = typography.render(bg_sym, FontRole.DISPLAY, 32, DARK_TEXT)
                    surf.blit(bg_icon_s, (c_rect.x + 18, c_rect.centery - bg_icon_s.get_height() // 2))

                    # Actor miniature sprites
                    for a_idx, actor_id in enumerate(show_item.get("actors", [])[:3]):
                        spr = puppet_sprites.get(actor_id, puppet_sprites["lilli"])
                        micro = pygame.transform.smoothscale(spr, (38, 38))
                        surf.blit(micro, (c_rect.x + 70 + a_idx * 34, c_rect.centery - 19))

                    # Title & Duration Badge
                    title_s = typography.render(show_item.get("title", "Storia"), FontRole.TITLE, 18, DARK_TEXT)
                    surf.blit(title_s, (c_rect.x + 200, c_rect.y + 14))

                    mic_indicator = "🎙️ " if show_item.get("has_audio") else ""
                    dur_text = f"{mic_indicator}{show_item.get('duration', 0)}s"
                    dur_s = typography.render(dur_text, FontRole.CONTROL, 13, (120, 60, 20))
                    surf.blit(dur_s, (c_rect.x + 200, c_rect.y + 44))

                    # Play Button [▶️ Guarda]
                    ply_btn_rect = pygame.Rect(c_rect.right - 200, c_rect.centery - 24, 110, 48)
                    pygame.draw.rect(surf, (220, 255, 225), ply_btn_rect, border_radius=12)
                    pygame.draw.rect(surf, MIC_GREEN, ply_btn_rect, width=2, border_radius=12)
                    ply_btn_s = typography.render(f"▶️ {ui_strings.get('play_story', 'Guarda')}", FontRole.TITLE, 15, (20, 100, 40))
                    surf.blit(ply_btn_s, (ply_btn_rect.centerx - ply_btn_s.get_width() // 2, ply_btn_rect.centery - ply_btn_s.get_height() // 2))

                    # Delete Button [🗑️]
                    del_btn_rect = pygame.Rect(c_rect.right - 70, c_rect.centery - 24, 50, 48)
                    pygame.draw.rect(surf, (255, 230, 230), del_btn_rect, border_radius=12)
                    pygame.draw.rect(surf, (220, 38, 38), del_btn_rect, width=2, border_radius=12)
                    del_btn_s = typography.render("🗑️", FontRole.TITLE, 18, (185, 28, 28))
                    surf.blit(del_btn_s, (del_btn_rect.centerx - del_btn_s.get_width() // 2, del_btn_rect.centery - del_btn_s.get_height() // 2))

        # --------------------------------------------------------------------
        # 9. FEEDBACK BANNER (Floating Center Notification)
        # --------------------------------------------------------------------
        if feedback_text and app_mode == "stage":
            fb_surf = typography.render(feedback_text, FontRole.TITLE, 19, STAGE_GOLD)
            fb_bg = pygame.Rect(REFERENCE_WIDTH // 2 - fb_surf.get_width() // 2 - 20, 100, fb_surf.get_width() + 40, 42)
            pygame.draw.rect(surf, (20, 16, 32), fb_bg, border_radius=12)
            pygame.draw.rect(surf, STAGE_GOLD, fb_bg, width=2, border_radius=12)
            surf.blit(fb_surf, (REFERENCE_WIDTH // 2 - fb_surf.get_width() // 2, 108))

        canvas.present(clear=theme.background)
        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
