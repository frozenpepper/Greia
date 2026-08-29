from __future__ import annotations

import math
from pathlib import Path
import random
import time

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

if __package__:
    from .orchestra_audio import SoundManager
    from .orchestra_content import (
        DARK_TEXT,
        KEYBOARD_SHORTCUTS,
        NOTE_NAMES_EN,
        NOTE_NAMES_IT,
        RAINBOW_COLORS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STAGE_CURTAIN,
        STAGE_CURTAIN_DARK,
        STAGE_CURTAIN_GOLD,
        STAGE_GOLD,
        STAGE_WALL_BOTTOM,
        STAGE_WALL_TOP,
        STAGE_WOOD_BOTTOM,
        STAGE_WOOD_TOP,
        STORAGE_KEY,
        WHITE,
    )
else:
    from orchestra_audio import SoundManager
    from orchestra_content import (
        DARK_TEXT,
        KEYBOARD_SHORTCUTS,
        NOTE_NAMES_EN,
        NOTE_NAMES_IT,
        RAINBOW_COLORS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STAGE_CURTAIN,
        STAGE_CURTAIN_DARK,
        STAGE_CURTAIN_GOLD,
        STAGE_GOLD,
        STAGE_WALL_BOTTOM,
        STAGE_WALL_TOP,
        STAGE_WOOD_BOTTOM,
        STAGE_WOOD_TOP,
        STORAGE_KEY,
        WHITE,
    )


class Particle:
    def __init__(self, x: float, y: float, symbol: str, color: tuple[int, int, int]) -> None:
        self.x = x
        self.y = y
        self.symbol = symbol
        self.color = color
        angle = random.uniform(-math.pi * 0.8, -math.pi * 0.2)
        speed = random.uniform(3.0, 7.0)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.decay = random.uniform(0.035, 0.06)
        self.size = random.randint(22, 32)

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.12
        self.life -= self.decay
        return self.life > 0

    def draw(self, surface: pygame.Surface, typography: GreiaTypography) -> None:
        if self.life > 0:
            sz = max(12, int(self.size * self.life))
            txt_surf = typography.render(self.symbol, FontRole.BODY, sz, self.color)
            surface.blit(txt_surf, (int(self.x) - txt_surf.get_width() // 2, int(self.y) - txt_surf.get_height() // 2))


class InstrumentCard:
    def __init__(self, inst_id: str, icon: str, name_it: str, name_en: str, sound_name: str, x: float, y: float, color: tuple[int, int, int]) -> None:
        self.inst_id = inst_id
        self.icon = icon
        self.name_it = name_it
        self.name_en = name_en
        self.sound_name = sound_name
        self.x = x
        self.y = y
        self.radius = 54.0
        self.jump_timer = 0.0
        self.phase = random.uniform(0, 2 * math.pi)
        self.color = color

    def trigger(self) -> None:
        self.jump_timer = 1.0

    def update(self) -> None:
        self.phase += 0.04
        if self.jump_timer > 0:
            self.jump_timer -= 0.05

    def contains(self, px: float, py: float) -> bool:
        return (self.x - px) ** 2 + (self.y - py) ** 2 <= (self.radius + 14) ** 2

    def draw(self, surface: pygame.Surface, typography: GreiaTypography, is_it: bool) -> None:
        ox = int(self.x)
        oy = int(self.y)
        if self.jump_timer > 0:
            oy += int(-math.sin(self.jump_timer * math.pi) * 22.0)
        else:
            oy += int(math.sin(self.phase) * 3.0)

        dark = (30, 41, 59)

        # Floor Shadow
        pygame.draw.ellipse(surface, (15, 12, 25), (ox - 48, int(self.y) + 42, 96, 22))

        # Pedestal / Golden Stage Stand
        pygame.draw.ellipse(surface, (180, 115, 60), (ox - 52, oy + 32, 104, 28))
        pygame.draw.ellipse(surface, STAGE_GOLD, (ox - 52, oy + 32, 104, 28), width=3)

        # Instrument Card Avatar
        avatar_bg = (255, 255, 255)
        border_col = STAGE_GOLD if self.jump_timer > 0 else self.color
        border_w = 5 if self.jump_timer > 0 else 3

        # Glow halo if triggered
        if self.jump_timer > 0:
            pygame.draw.circle(surface, (254, 240, 138), (ox, oy), int(self.radius + 8), width=4)

        pygame.draw.circle(surface, avatar_bg, (ox, oy), int(self.radius))
        pygame.draw.circle(surface, border_col, (ox, oy), int(self.radius), width=border_w)

        # Giant Dedicated Instrument Icon
        char_surf = typography.render(self.icon, FontRole.DISPLAY, 54, DARK_TEXT)
        surface.blit(char_surf, (ox - char_surf.get_width() // 2, oy - char_surf.get_height() // 2 - 6))

        # Instrument Name Badge underneath
        lbl_text = self.name_it if is_it else self.name_en
        lbl_surf = typography.render(lbl_text, FontRole.CONTROL, 14, (255, 255, 255))
        badge_w = max(80, lbl_surf.get_width() + 16)
        badge_rect = pygame.Rect(ox - badge_w // 2, oy + 30, badge_w, 24)
        pygame.draw.rect(surface, (30, 24, 45), badge_rect, border_radius=8)
        pygame.draw.rect(surface, STAGE_GOLD if self.jump_timer > 0 else (203, 213, 225), badge_rect, width=2, border_radius=8)
        surface.blit(lbl_surf, (badge_rect.centerx - lbl_surf.get_width() // 2, badge_rect.centery - lbl_surf.get_height() // 2))


def _build_stage_background() -> pygame.Surface:
    """Pre-renders the theater stage background once to avoid per-frame allocations."""
    surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
    
    # 1. Theater Wall Gradient
    for y in range(0, 430, 8):
        ratio = y / 430.0
        col = mix(STAGE_WALL_TOP, STAGE_WALL_BOTTOM, ratio)
        pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 8))

    # 2. Stage Floor Wood Planks
    for y in range(430, REFERENCE_HEIGHT, 6):
        ratio = (y - 430) / float(REFERENCE_HEIGHT - 430)
        col = mix(STAGE_WOOD_TOP, STAGE_WOOD_BOTTOM, ratio)
        pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 6))

    # Plank Lines
    for px in range(0, REFERENCE_WIDTH, 120):
        pygame.draw.line(surf, (80, 45, 20), (px, 430), (px, REFERENCE_HEIGHT), 2)
    pygame.draw.line(surf, STAGE_GOLD, (0, 430), (REFERENCE_WIDTH, 430), 4)

    # 3. Velvet Stage Curtains
    pygame.draw.polygon(surf, STAGE_CURTAIN_DARK, [(0, 0), (140, 0), (90, 440), (0, 440)])
    pygame.draw.polygon(surf, STAGE_CURTAIN, [(0, 0), (120, 0), (70, 430), (0, 430)])
    pygame.draw.polygon(surf, STAGE_CURTAIN_DARK, [(REFERENCE_WIDTH, 0), (REFERENCE_WIDTH - 140, 0), (REFERENCE_WIDTH - 90, 440), (REFERENCE_WIDTH, 440)])
    pygame.draw.polygon(surf, STAGE_CURTAIN, [(REFERENCE_WIDTH, 0), (REFERENCE_WIDTH - 120, 0), (REFERENCE_WIDTH - 70, 430), (REFERENCE_WIDTH, 430)])

    # Gold Fringe & Ties
    pygame.draw.line(surf, STAGE_CURTAIN_GOLD, (70, 0), (35, 430), 3)
    pygame.draw.line(surf, STAGE_CURTAIN_GOLD, (REFERENCE_WIDTH - 70, 0), (REFERENCE_WIDTH - 35, 430), 3)

    # Top Valance Swags
    for vx in range(120, 900, 130):
        pygame.draw.circle(surf, STAGE_CURTAIN, (vx + 65, 30), 75)
        pygame.draw.circle(surf, STAGE_CURTAIN_GOLD, (vx + 65, 30), 75, width=3)

    return surf


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
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    theme = get_theme()
    metrics = ChildUiMetrics.for_size(*screen.get_size())
    canvas = PygameReferenceCanvas(screen)
    typography = GreiaTypography()
    sounds = SoundManager()

    # Pre-render static stage background once (ultra-fast 60 FPS on Intel Atom)
    bg_surface = _build_stage_background()

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
    is_it = (active_locale == "it")
    note_labels = NOTE_NAMES_IT if is_it else NOTE_NAMES_EN

    stars = 0
    if storage is not None:
        try:
            saved = storage.kv_get(STORAGE_KEY, {})
            if isinstance(saved, dict):
                stars = int(saved.get("stars", 0))
        except Exception:
            pass

    # 5 Clear Musical Instruments on Stage (No confusing animals)
    instruments = [
        InstrumentCard("piano", "🎹", "Pianoforte", "Piano", "piano", 150, 230, (59, 130, 246)),
        InstrumentCard("drums", "🥁", "Batteria", "Drums", "drums", 330, 210, (239, 68, 68)),
        InstrumentCard("trumpet", "🎺", "Tromba", "Trumpet", "trumpet", 512, 230, (234, 179, 8)),
        InstrumentCard("guitar", "🎸", "Chitarra", "Guitar", "guitar", 694, 210, (249, 115, 22)),
        InstrumentCard("maracas", "🪇", "Maracas", "Maracas", "maracas", 874, 230, (34, 197, 94)),
    ]

    particles: list[Particle] = []
    key_highlight_timers = [0.0] * 8

    running = True
    ready_published = False

    def trigger_piano_key(k_idx: int):
        nonlocal stars
        if 0 <= k_idx < 8:
            sounds.play_note(k_idx)
            key_highlight_timers[k_idx] = 1.0
            stars += 1
            kx = 64 + k_idx * 112
            for _ in range(8):
                particles.append(Particle(kx + 52, 460, random.choice(["🎵", "🎶", "♪", "♫"]), RAINBOW_COLORS[k_idx]))
            safe_emit("instrument.played", f"note-{time.time()}", payload={"note": k_idx})

    while running and not activity_stop_requested():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                # Keyboard shortcuts 1..8 and A..K for piano keys
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
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if not _is_safe_point(screen, event.pos):
                    continue
                logical = canvas.pointer(event.pos)
                if logical is not None:
                    lx, ly = logical

                    # 1. Instruments Direct Tap
                    for inst in instruments:
                        if inst.contains(lx, ly):
                            inst.trigger()
                            sounds.play_inst(inst.sound_name)
                            stars += 2
                            for _ in range(12):
                                particles.append(Particle(inst.x, inst.y - 20, random.choice(["🎵", "🎶", "✨", "⭐"]), STAGE_GOLD))
                            safe_emit("instrument.played", f"inst-{time.time()}", payload={"instrument": inst.inst_id})

                    # 2. Rainbow Piano Keys direct tap (y = 440..570)
                    for k_i in range(8):
                        kx = 64 + k_i * 112
                        if kx <= lx <= kx + 104 and 440 <= ly <= 570:
                            trigger_piano_key(k_i)

        # State updates
        for inst in instruments:
            inst.update()
        for i in range(8):
            if key_highlight_timers[i] > 0:
                key_highlight_timers[i] -= 0.05
        particles = [p for p in particles if p.update()]

        # --- RENDERING ---
        surf = canvas.surface

        # 1. Blit Pre-rendered Theater Stage Background (0.05 ms direct copy)
        surf.blit(bg_surface, (0, 0))

        # 2. Draw 5 Dedicated Instrument Cards on Stage
        for inst in instruments:
            inst.draw(surf, typography, is_it)

        # 3. Floating Music Note Particles
        for p in particles:
            p.draw(surf, typography)

        # 4. Rainbow Piano Keys with Keyboard Number Badges (y = 440..570)
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
            pygame.draw.rect(surf, (30, 41, 59), key_rect, width=3, border_radius=14)

            # Keyboard shortcut badge [ 1 ]
            badge_rect = pygame.Rect(kx + 32, 448, 40, 22)
            pygame.draw.rect(surf, (255, 250, 240), badge_rect, border_radius=6)
            pygame.draw.rect(surf, (30, 41, 59), badge_rect, width=1, border_radius=6)
            sc_surf = typography.render(KEYBOARD_SHORTCUTS[k_i], FontRole.CONTROL, 14, DARK_TEXT)
            surf.blit(sc_surf, (badge_rect.centerx - sc_surf.get_width() // 2, badge_rect.centery - sc_surf.get_height() // 2))

            # Note Name (DO, RE, MI...)
            note_str = note_labels[k_i]
            n_surf = typography.render(note_str, FontRole.DISPLAY, 26, (255, 255, 255) if hl <= 0 else DARK_TEXT)
            surf.blit(n_surf, (kx + 52 - n_surf.get_width() // 2, 490))

        # 5. Top Header & HUD (Clear of Home at x < 120)
        # Title card (x = 360..664, y = 16..68)
        title_rect = pygame.Rect(360, 16, 304, 52)
        pygame.draw.rect(surf, (255, 250, 240), title_rect, border_radius=14)
        pygame.draw.rect(surf, (30, 41, 59), title_rect, width=2, border_radius=14)
        title_str = "🎵 Orchestra Magica 🎶" if is_it else "🎵 Magic Orchestra 🎶"
        t_surf = typography.render(title_str, FontRole.TITLE, 20, DARK_TEXT)
        surf.blit(t_surf, (title_rect.centerx - t_surf.get_width() // 2, title_rect.centery - t_surf.get_height() // 2))

        # HUD Star Pill (Top Right x=820..980)
        hud_rect = pygame.Rect(820, 12, 160, 56)
        pygame.draw.rect(surf, (255, 250, 240), hud_rect, border_radius=16)
        pygame.draw.rect(surf, (234, 179, 8), hud_rect, width=3, border_radius=16)
        pygame.draw.circle(surf, (234, 179, 8), (hud_rect.left + 30, hud_rect.centery), 16)
        hud_surf = typography.render(str(stars), FontRole.DISPLAY, 26, (180, 90, 20))
        surf.blit(hud_surf, (hud_rect.left + 58, hud_rect.centery - hud_surf.get_height() // 2))

        canvas.present(clear=theme.background)
        pygame.display.flip()
        if not ready_published:
            mark_activity_ready()
            ready_published = True

        clock.tick(60)

    if storage is not None:
        try:
            storage.kv_set(STORAGE_KEY, {"stars": stars})
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
