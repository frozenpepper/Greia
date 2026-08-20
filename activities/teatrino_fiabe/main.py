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


REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
STORAGE_KEY = "teatrino_fiabe.state.v2"

# Grand Theater Palette
STAGE_GOLD = (255, 215, 60)
STAGE_CURTAIN = (180, 25, 40)
STAGE_CURTAIN_DARK = (115, 15, 25)
STAGE_WOOD_TOP = (175, 110, 55)
STAGE_WOOD_BOTTOM = (105, 60, 25)
WHITE = (255, 255, 255)
DARK_TEXT = (45, 35, 42)
REC_RED = (240, 50, 50)


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
        # Pop
        pop_samples = [
            int(math.sin(2 * math.pi * (500 + (1100 - i) * 0.9) * (i / 22050.0)) * max(0.0, 1.0 - (i / 22050.0) / 0.05) * 14000)
            for i in range(1200)
        ]
        self._sounds["pop"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(pop_samples)))

        # Trumpet Fanfare
        fanfare_samples = []
        notes = [523.25, 659.25, 783.99, 1046.50]
        for i in range(10000):
            t = i / 22050.0
            idx = min(len(notes) - 1, int(t / 0.09))
            env = max(0.0, 1.0 - t / 0.42)
            fanfare_samples.append(int(math.sin(2 * math.pi * notes[idx] * t) * env * 15000))
        self._sounds["trumpet"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(fanfare_samples)))

        # Magic sparkle
        sp_samples = []
        for i in range(7000):
            t = i / 22050.0
            f = 900.0 + math.sin(t * 80) * 450
            env = max(0.0, 1.0 - t / 0.32)
            sp_samples.append(int(math.sin(2 * math.pi * f * t) * env * 12000))
        self._sounds["magic"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(sp_samples)))

        # Applause
        ap_samples = []
        for i in range(18000):
            t = i / 22050.0
            env = min(1.0, t / 0.15) * max(0.0, 1.0 - t / 0.82)
            ap_samples.append(int(random.uniform(-1, 1) * env * 11000))
        self._sounds["applause"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(ap_samples)))

        # Giggle
        gg_samples = []
        for i in range(8000):
            t = i / 22050.0
            f = 600.0 + math.sin(t * 60) * 180
            env = max(0.0, 1.0 - t / 0.35)
            gg_samples.append(int(math.sin(2 * math.pi * f * t) * env * 13000))
        self._sounds["giggle"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(gg_samples)))

        # Mystery chime
        my_samples = []
        for i in range(9000):
            t = i / 22050.0
            f = 440.0 + (1.0 - t / 0.4) * 220
            env = math.exp(-t * 4.0)
            my_samples.append(int(math.sin(2 * math.pi * f * t) * env * 14000))
        self._sounds["mystery"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(my_samples)))

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
        speed = random.uniform(2.5, 7.0)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 1.0
        self.life = 1.0
        self.decay = random.uniform(0.025, 0.045)
        self.size = random.randint(18, 30)

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.06
        self.life -= self.decay
        return self.life > 0

    def draw(self, surface: pygame.Surface, typography: GreiaTypography) -> None:
        if self.life > 0:
            sz = max(10, int(self.size * self.life))
            txt_surf = typography.render(self.symbol, FontRole.BODY, sz, self.color)
            surface.blit(txt_surf, (int(self.x) - txt_surf.get_width() // 2, int(self.y) - txt_surf.get_height() // 2))


class Puppet:
    def __init__(self, puppet_id: str, icon: str, name: str, x: float, y: float) -> None:
        self.puppet_id = puppet_id
        self.icon = icon
        self.name = name
        self.x = x
        self.y = y
        self.radius = 42.0
        self.is_held = False
        self.wobble = 0.0

    def update(self) -> None:
        self.wobble += 0.05

    def contains(self, px: float, py: float) -> bool:
        return (self.x - px) ** 2 + (self.y - py) ** 2 <= (self.radius + 12) ** 2

    def draw(self, surface: pygame.Surface, typography: GreiaTypography) -> None:
        px = int(self.x)
        py = int(self.y)
        if not self.is_held:
            py += int(math.sin(self.wobble) * 3.0)

        # Drop shadow on stage
        pygame.draw.ellipse(surface, (15, 12, 20), (px - 36, 420, 72, 18))

        # Puppet rod / stick
        pygame.draw.line(surface, (140, 95, 60), (px, py + 30), (px, 420), 4)

        # Puppet avatar badge
        pygame.draw.circle(surface, (255, 250, 240), (px, py), int(self.radius))
        border_col = (255, 190, 50) if self.is_held else (61, 44, 31)
        border_w = 4 if self.is_held else 3
        pygame.draw.circle(surface, border_col, (px, py), int(self.radius), width=border_w)

        # Puppet Icon Emoji
        txt = typography.render(self.icon, FontRole.DISPLAY, 40, DARK_TEXT)
        surface.blit(txt, (px - txt.get_width() // 2, py - txt.get_height() // 2))


PUPPET_TYPES = [
    ("princess", "👑", "Principessa"),
    ("dragon", "🐲", "Draghetto"),
    ("fairy", "🧚", "Fatina"),
    ("unicorn", "🦄", "Unicorno"),
    ("cat", "🐱", "Gatto Mago"),
    ("mermaid", "🧜", "Sirenetta"),
    ("robot", "🤖", "Robotino"),
    ("star", "🌟", "Stella"),
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

    active_bg = "castle"
    puppets_on_stage: list[Puppet] = [
        Puppet("princess", "👑", "Principessa", 380, 280),
        Puppet("dragon", "🐲", "Draghetto", 600, 280),
    ]
    dragging_puppet: Puppet | None = None

    # Recording / Playback Engine
    is_recording = False
    is_playing_show = False
    record_frames: list[tuple[float, list[tuple[str, float, float]]]] = []
    recorded_sound_events: list[tuple[float, str]] = []
    record_start_time = 0.0
    playback_start_time = 0.0
    curtain_open_amount = 1.0  # 1.0 = open, 0.0 = closed

    bg_options = [("castle", "🏰"), ("forest", "🌲"), ("ocean", "🌊"), ("space", "🚀")]
    fx_buttons = [("fanfare", "🎺"), ("magic", "✨"), ("applause", "👏"), ("giggle", "😄"), ("mystery", "🔮")]

    particles: list[Particle] = []
    feedback_text = ""
    feedback_timer = 0.0

    if storage is not None:
        try:
            saved = storage.kv_get(STORAGE_KEY, {})
            if isinstance(saved, dict):
                active_bg = str(saved.get("backdrop", "castle"))
        except Exception:
            pass

    running = True
    ready_published = False

    # Top Control Buttons (Clear of Home at x < 130)
    bg_selector_rect = pygame.Rect(140, 16, 170, 52)
    rec_btn_rect = pygame.Rect(330, 16, 160, 52)
    play_btn_rect = pygame.Rect(510, 16, 170, 52)
    clear_btn_rect = pygame.Rect(700, 16, 80, 52)

    while running and not activity_stop_requested():
        now = time.time()

        # Capture frame if recording
        if is_recording:
            elapsed = now - record_start_time
            frame_data = [(p.puppet_id, p.x, p.y) for p in puppets_on_stage]
            record_frames.append((elapsed, frame_data))

        # Playback animation logic
        if is_playing_show:
            elapsed = now - playback_start_time
            if record_frames and elapsed < record_frames[-1][0]:
                # Interpolate recorded positions
                for t_stamp, p_data in record_frames:
                    if t_stamp >= elapsed:
                        for p_id, px, py in p_data:
                            for staged in puppets_on_stage:
                                if staged.puppet_id == p_id:
                                    staged.x = px
                                    staged.y = py
                        break
            else:
                # Demo show animation if no frames recorded or show finished
                if not record_frames:
                    t = elapsed
                    if t < 6.0:
                        if len(puppets_on_stage) >= 2:
                            puppets_on_stage[0].x = 380 + math.sin(t * 3.0) * 120.0
                            puppets_on_stage[0].y = 280 + math.sin(t * 6.0) * 30.0
                            puppets_on_stage[1].x = 600 - math.sin(t * 3.0) * 120.0
                            puppets_on_stage[1].y = 280 + math.cos(t * 5.0) * 30.0
                        if random.random() < 0.2:
                            particles.append(Particle(random.uniform(300, 700), random.uniform(180, 350), "✨", STAGE_GOLD))
                    else:
                        is_playing_show = False
                        sounds.play("applause")
                        feedback_text = "Gran Finale! 👏🌟"
                        feedback_timer = 3.0
                else:
                    is_playing_show = False
                    sounds.play("applause")
                    feedback_text = "Fine dello Spettacolo! 👏✨"
                    feedback_timer = 3.0

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
                    # Check puppet grab
                    for p in reversed(puppets_on_stage):
                        if p.contains(lx, ly):
                            p.is_held = True
                            dragging_puppet = p
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

                    # 1. Backdrop Selector (x = 140..310, y = 16..68)
                    if bg_selector_rect.collidepoint(lx, ly):
                        bg_ids = [b[0] for b in bg_options]
                        cur_b_idx = bg_ids.index(active_bg) if active_bg in bg_ids else 0
                        active_bg = bg_ids[(cur_b_idx + 1) % len(bg_ids)]
                        sounds.play("pop")
                        for _ in range(14):
                            particles.append(Particle(lx, ly, "✨", STAGE_GOLD))
                        continue

                    # 2. Record Button (🔴 Registra)
                    if rec_btn_rect.collidepoint(lx, ly):
                        if not is_recording:
                            is_recording = True
                            is_playing_show = False
                            record_frames.clear()
                            record_start_time = now
                            sounds.play("pop")
                            feedback_text = "🔴 Registrazione in corso..." if active_locale == "it" else "🔴 Recording show..."
                            feedback_timer = 2.5
                        else:
                            is_recording = False
                            sounds.play("trumpet")
                            feedback_text = "Spettacolo Registrato! 🎭✨"
                            feedback_timer = 3.0
                        continue

                    # 3. Play Show Button (▶️ Spettacolo)
                    if play_btn_rect.collidepoint(lx, ly):
                        is_playing_show = True
                        is_recording = False
                        playback_start_time = now
                        sounds.play("trumpet")
                        sounds.play("applause")
                        feedback_text = "In scena! ✨👏"
                        feedback_timer = 3.5
                        # If stage is empty, spawn 3 fairy tale actors for the show!
                        if len(puppets_on_stage) == 0:
                            puppets_on_stage.append(Puppet("princess", "👑", "Principessa", 340, 300))
                            puppets_on_stage.append(Puppet("dragon", "🐲", "Draghetto", 512, 280))
                            puppets_on_stage.append(Puppet("fairy", "🧚", "Fatina", 680, 300))
                        for p in puppets_on_stage:
                            p.jump()
                        safe_emit("scene.recorded", f"show-{time.time()}")
                        for _ in range(30):
                            particles.append(Particle(512, 280, "🎉", STAGE_GOLD))
                            particles.append(Particle(512, 280, "✨", PINK))
                        continue

                    # 4. Clear Stage Button (🗑️)
                    if clear_btn_rect.collidepoint(lx, ly):
                        puppets_on_stage.clear()
                        sounds.play("pop")
                        continue

                    # 5. Magic Sound FX Buttons (Right Sidebar x=920, y=100..440)
                    for f_idx, (fx_id, fx_sym) in enumerate(fx_buttons):
                        fy = 110 + f_idx * 64
                        if 910 <= lx <= 990 and fy <= ly <= fy + 52:
                            sounds.play(fx_id)
                            for _ in range(12):
                                particles.append(Particle(lx, ly, fx_sym, STAGE_GOLD))
                            break

                    # 6. Puppet Tray (Bottom x=80..940, y=510..585)
                    for p_idx, (p_id, p_icon, p_name) in enumerate(PUPPET_TYPES):
                        px = 110 + p_idx * 96
                        if px <= lx <= px + 80 and 510 <= ly <= 585:
                            sounds.play("pop")
                            if len(puppets_on_stage) < 6:
                                new_p = Puppet(p_id, p_icon, p_name, random.uniform(320, 700), 280)
                                puppets_on_stage.append(new_p)
                                for _ in range(14):
                                    particles.append(Particle(new_p.x, new_p.y, p_icon, STAGE_GOLD))
                                safe_emit("puppet.moved", f"puppet-{time.time()}", payload={"puppet": p_id})

        # Dragging puppet motion
        if dragging_puppet is not None and pygame.mouse.get_focused():
            mpos = pygame.mouse.get_pos()
            if _is_safe_point(screen, mpos):
                plog = canvas.pointer(mpos)
                if plog is not None:
                    dragging_puppet.x = max(160.0, min(860.0, plog[0]))
                    dragging_puppet.y = max(140.0, min(420.0, plog[1]))

        # State updates
        for p in puppets_on_stage:
            p.update()
        particles = [p for p in particles if p.update()]

        if feedback_timer > 0:
            feedback_timer -= 0.035
        else:
            feedback_text = ""

        # --- RENDERING ---
        surf = canvas.surface

        # 1. Scenery Backdrop
        if active_bg == "castle":
            for y in range(0, 430, 8):
                pygame.draw.rect(surf, mix((30, 35, 55), (60, 50, 75), y / 430.0), (0, y, REFERENCE_WIDTH, 8))
            # Arched castle windows
            for wx in (300, 512, 724):
                pygame.draw.rect(surf, (255, 230, 140), (wx - 36, 130, 72, 110), border_radius=36)
                pygame.draw.rect(surf, (30, 25, 40), (wx - 36, 130, 72, 110), width=3, border_radius=36)
        elif active_bg == "forest":
            for y in range(0, 430, 8):
                pygame.draw.rect(surf, mix((15, 35, 30), (35, 75, 55), y / 430.0), (0, y, REFERENCE_WIDTH, 8))
            # Glowing trees & moon
            pygame.draw.circle(surf, (255, 245, 200), (512, 120), 40)
            pygame.draw.circle(surf, (15, 45, 35), (250, 360), 160)
            pygame.draw.circle(surf, (15, 45, 35), (770, 360), 160)
        elif active_bg == "ocean":
            for y in range(0, 430, 8):
                pygame.draw.rect(surf, mix((10, 30, 70), (20, 80, 140), y / 430.0), (0, y, REFERENCE_WIDTH, 8))
            # Corals & underwater bubbles
            for bx in (260, 420, 620, 780):
                pygame.draw.circle(surf, (200, 235, 255), (bx, 200 + int(math.sin(now * 2 + bx) * 40)), 12, width=2)
        else:  # Space
            for y in range(0, 430, 8):
                pygame.draw.rect(surf, mix((10, 8, 25), (35, 18, 55), y / 430.0), (0, y, REFERENCE_WIDTH, 8))
            # Stars & Planets
            pygame.draw.circle(surf, (240, 140, 80), (740, 140), 38)
            pygame.draw.ellipse(surf, (255, 200, 120), (700, 150, 80, 16), width=3)

        # Stage Floor
        for y in range(430, 500, 6):
            col = mix(STAGE_WOOD_TOP, STAGE_WOOD_BOTTOM, (y - 430) / 70.0)
            pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 6))

        # 2. Puppets on Stage
        for p in puppets_on_stage:
            p.draw(surf, typography)

        # 3. Stage Frame & Velvet Curtains
        pygame.draw.polygon(surf, STAGE_CURTAIN_DARK, [(0, 0), (130, 0), (80, 440), (0, 440)])
        pygame.draw.polygon(surf, STAGE_CURTAIN, [(0, 0), (110, 0), (60, 430), (0, 430)])
        pygame.draw.polygon(surf, STAGE_CURTAIN_DARK, [(REFERENCE_WIDTH, 0), (REFERENCE_WIDTH - 130, 0), (REFERENCE_WIDTH - 80, 440), (REFERENCE_WIDTH, 440)])
        pygame.draw.polygon(surf, STAGE_CURTAIN, [(REFERENCE_WIDTH, 0), (REFERENCE_WIDTH - 110, 0), (REFERENCE_WIDTH - 60, 430), (REFERENCE_WIDTH, 430)])

        # Top Valance Swags
        for vx in range(120, 900, 130):
            pygame.draw.circle(surf, STAGE_CURTAIN, (vx + 65, 30), 75)
            pygame.draw.circle(surf, STAGE_GOLD, (vx + 65, 30), 75, width=2)

        # 4. Particles
        for p in particles:
            p.draw(surf, typography)

        # 5. Top Controls (Clear of Home at x < 130)
        # Backdrop button
        pygame.draw.rect(surf, (255, 250, 240), bg_selector_rect, border_radius=14)
        pygame.draw.rect(surf, (61, 44, 31), bg_selector_rect, width=2, border_radius=14)
        cur_bg_icon = next(b[1] for b in bg_options if b[0] == active_bg)
        bg_lbl = f"Scena {cur_bg_icon}"
        bg_surf = typography.render(bg_lbl, FontRole.TITLE, 18, DARK_TEXT)
        surf.blit(bg_surf, (bg_selector_rect.centerx - bg_surf.get_width() // 2, bg_selector_rect.centery - bg_surf.get_height() // 2))

        # Record Button
        rec_col = (255, 180, 180) if is_recording else (255, 250, 240)
        pygame.draw.rect(surf, rec_col, rec_btn_rect, border_radius=14)
        pygame.draw.rect(surf, REC_RED if is_recording else (61, 44, 31), rec_btn_rect, width=3 if is_recording else 2, border_radius=14)
        rec_txt = "⏹️ Stop REC" if is_recording else "🔴 Registra"
        rec_surf = typography.render(rec_txt, FontRole.TITLE, 18, REC_RED if is_recording else DARK_TEXT)
        surf.blit(rec_surf, (rec_btn_rect.centerx - rec_surf.get_width() // 2, rec_btn_rect.centery - rec_surf.get_height() // 2))

        # Play Show Button
        play_col = (220, 255, 220) if is_playing_show else (255, 250, 240)
        pygame.draw.rect(surf, play_col, play_btn_rect, border_radius=14)
        pygame.draw.rect(surf, (40, 160, 60) if is_playing_show else (61, 44, 31), play_btn_rect, width=3 if is_playing_show else 2, border_radius=14)
        play_txt = "🎭 In Scena!" if is_playing_show else "▶️ Spettacolo"
        play_surf = typography.render(play_txt, FontRole.TITLE, 18, (40, 140, 50) if is_playing_show else DARK_TEXT)
        surf.blit(play_surf, (play_btn_rect.centerx - play_surf.get_width() // 2, play_btn_rect.centery - play_surf.get_height() // 2))

        # Clear button
        pygame.draw.rect(surf, (255, 250, 240), clear_btn_rect, border_radius=14)
        pygame.draw.rect(surf, (61, 44, 31), clear_btn_rect, width=2, border_radius=14)
        clr_surf = typography.render("🗑️", FontRole.TITLE, 22, DARK_TEXT)
        surf.blit(clr_surf, (clear_btn_rect.centerx - clr_surf.get_width() // 2, clear_btn_rect.centery - clr_surf.get_height() // 2))

        # 6. Magic Sound FX Sidebar (Right side x=910..990)
        for f_idx, (fx_id, fx_sym) in enumerate(fx_buttons):
            fy = 110 + f_idx * 64
            fx_rect = pygame.Rect(915, fy, 70, 52)
            pygame.draw.rect(surf, (255, 250, 240), fx_rect, border_radius=12)
            pygame.draw.rect(surf, STAGE_GOLD, fx_rect, width=2, border_radius=12)
            fx_s = typography.render(fx_sym, FontRole.DISPLAY, 26, DARK_TEXT)
            surf.blit(fx_s, (fx_rect.centerx - fx_s.get_width() // 2, fx_rect.centery - fx_s.get_height() // 2))

        # 7. Puppet Tray (Bottom Toolbar y=500..600)
        pygame.draw.rect(surf, (30, 24, 40), (0, 500, REFERENCE_WIDTH, 100))
        pygame.draw.rect(surf, STAGE_GOLD, (0, 500, REFERENCE_WIDTH, 4))
        for p_idx, (p_id, p_icon, p_name) in enumerate(PUPPET_TYPES):
            px = 110 + p_idx * 96
            tray_rect = pygame.Rect(px, 510, 80, 78)
            pygame.draw.rect(surf, (255, 250, 240), tray_rect, border_radius=14)
            pygame.draw.rect(surf, (61, 44, 31), tray_rect, width=2, border_radius=14)
            p_s = typography.render(p_icon, FontRole.DISPLAY, 34, DARK_TEXT)
            surf.blit(p_s, (tray_rect.centerx - p_s.get_width() // 2, tray_rect.y + 8))
            n_s = typography.render(p_name[:7], FontRole.CONTROL, 12, DARK_TEXT)
            surf.blit(n_s, (tray_rect.centerx - n_s.get_width() // 2, tray_rect.y + 54))

        # 8. Feedback Banner
        if feedback_text:
            fb_surf = typography.render(feedback_text, FontRole.TITLE, 24, STAGE_GOLD)
            fb_bg = pygame.Rect(REFERENCE_WIDTH // 2 - fb_surf.get_width() // 2 - 20, 80, fb_surf.get_width() + 40, 44)
            pygame.draw.rect(surf, (20, 16, 32), fb_bg, border_radius=12)
            pygame.draw.rect(surf, STAGE_GOLD, fb_bg, width=2, border_radius=12)
            surf.blit(fb_surf, (REFERENCE_WIDTH // 2 - fb_surf.get_width() // 2, 88))

        canvas.present(clear=theme.background)
        pygame.display.flip()
        if not ready_published:
            mark_activity_ready()
            ready_published = True

        clock.tick(30)

    if storage is not None:
        try:
            storage.kv_set(STORAGE_KEY, {"backdrop": active_bg})
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
