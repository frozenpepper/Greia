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
STORAGE_KEY = "foresta_parole.progress.v2"

# Enchanted Forest Color Palette
FOREST_SKY_TOP = (18, 24, 48)
FOREST_SKY_BOTTOM = (38, 64, 82)
CANOPY_DARK = (16, 32, 38)
CANOPY_LIGHT = (28, 58, 64)
BRANCH_BROWN = (72, 48, 34)
LEAF_GREEN = (52, 128, 80)
LEAF_LIGHT = (84, 182, 112)
CARD_BG = (255, 250, 240)
CARD_BORDER = (61, 44, 31)
GOLD = (255, 205, 50)
WHITE = (255, 255, 255)
# CRITICAL AUDIO / TTS SYNTHESIS INSTRUCTIONS:
# ============================================
# When generating audio with TTS (e.g. macOS `say`), ALWAYS pass lowercase strings (.lower()).
# Capital letters (like 'C' or 'C come Cane') cause macOS TTS to say "C maiuscola" or "capital C".
# Target speech rate: ~180 wpm for Italian, ~185 wpm for English (gentle, toddler-friendly pace).
# See `tools/generate_foresta_audio.py` to regenerate all audio assets.

PHONICS_DATA = {
    "it": [
        ("A", "a", "find_a", "Ape", "🐝", "ape"),
        ("B", "b", "find_b", "Barca", "⛵", "barca"),
        ("C", "c", "find_c", "Cane", "🐶", "cane"),
        ("D", "d", "find_d", "Delfino", "🐬", "delfino"),
        ("E", "e", "find_e", "Elefante", "🐘", "elefante"),
        ("F", "f", "find_f", "Fiore", "🌸", "fiore"),
        ("G", "g", "find_g", "Gatto", "🐱", "gatto"),
        ("I", "i", "find_i", "Isola", "🏝️", "isola"),
        ("L", "l", "find_l", "Luna", "🌙", "luna"),
        ("M", "m", "find_m", "Mela", "🍎", "mela"),
        ("N", "n", "find_n", "Nave", "🚢", "nave"),
        ("O", "o", "find_o", "Orso", "🐻", "orso"),
        ("P", "p", "find_p", "Pesce", "🐟", "pesce"),
        ("Q", "q", "find_q", "Quercia", "🌳", "quercia"),
        ("R", "r", "find_r", "Rana", "🐸", "rana"),
        ("S", "s", "find_s", "Sole", "☀️", "sole"),
        ("T", "t", "find_t", "Tigre", "🐯", "tigre"),
        ("U", "u", "find_u", "Uva", "🍇", "uva"),
        ("V", "v", "find_v", "Vento", "💨", "vento"),
        ("Z", "z", "find_z", "Zebra", "🦓", "zebra"),
    ],
    "en": [
        ("A", "a", "find_a", "Apple", "🍎", "apple"),
        ("B", "b", "find_b", "Boat", "⛵", "boat"),
        ("C", "c", "find_c", "Cat", "🐱", "cat"),
        ("D", "d", "find_d", "Dolphin", "🐬", "dolphin"),
        ("E", "e", "find_e", "Elephant", "🐘", "elephant"),
        ("F", "f", "find_f", "Flower", "🌸", "flower"),
        ("G", "g", "find_g", "Giraffe", "🦒", "giraffe"),
        ("H", "h", "find_h", "House", "🏡", "house"),
        ("I", "i", "find_i", "Island", "🏝️", "island"),
        ("L", "l", "find_l", "Lion", "🦁", "lion"),
        ("M", "m", "find_m", "Moon", "🌙", "moon"),
        ("N", "n", "find_n", "Nest", "🪺", "nest"),
        ("O", "o", "find_o", "Owl", "🦉", "owl"),
        ("P", "p", "find_p", "Penguin", "🐧", "penguin"),
        ("Q", "q", "find_q", "Queen", "👑", "queen"),
        ("R", "r", "find_r", "Rabbit", "🐰", "rabbit"),
        ("S", "s", "find_s", "Sun", "☀️", "sun"),
        ("T", "t", "find_t", "Tiger", "🐯", "tiger"),
        ("U", "u", "find_u", "Umbrella", "☂️", "umbrella"),
        ("V", "v", "find_v", "Volcano", "🌋", "volcano"),
        ("W", "w", "find_w", "Whale", "🐋", "whale"),
        ("Z", "z", "find_z", "Zebra", "🦓", "zebra"),
    ],
}

ORB_COLORS = [
    ((255, 140, 60), (255, 200, 120)),
    ((60, 180, 255), (150, 220, 255)),
    ((255, 90, 140), (255, 170, 200)),
    ((140, 90, 255), (200, 160, 255)),
    ((70, 210, 120), (160, 245, 190)),
    ((255, 210, 50), (255, 240, 140)),
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
        audio_dir = Path(__file__).resolve().parent / "assets" / "audio"
        for loc in ("it", "en"):
            loc_dir = audio_dir / loc
            if loc_dir.exists():
                for wav in loc_dir.glob("*.wav"):
                    try:
                        self._sounds[f"{loc}:{wav.stem.lower()}"] = pygame.mixer.Sound(str(wav))
                    except Exception:
                        pass

        pop_samples = [
            int(math.sin(2 * math.pi * (600 + (1200 - i) * 0.8) * (i / 22050.0)) * max(0.0, 1.0 - (i / 22050.0) / 0.05) * 14000)
            for i in range(1200)
        ]
        self._sounds["pop"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(pop_samples)))

        chime_samples = []
        for i in range(6000):
            t = i / 22050.0
            f = 523.25 if t < 0.08 else (659.25 if t < 0.16 else (783.99 if t < 0.24 else 1046.50))
            env = max(0.0, 1.0 - t / 0.27)
            chime_samples.append(int(math.sin(2 * math.pi * f * t) * env * 12000))
        self._sounds["chime"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(chime_samples)))

        fanfare_samples = []
        notes = [523.25, 659.25, 783.99, 1046.50, 1318.51]
        for i in range(11000):
            t = i / 22050.0
            idx = min(len(notes) - 1, int(t / 0.08))
            f = notes[idx]
            env = max(0.0, 1.0 - t / 0.48)
            fanfare_samples.append(int(math.sin(2 * math.pi * f * t) * env * 14000))
        self._sounds["fanfare"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(fanfare_samples)))

        wobble_samples = [
            int(math.sin(2 * math.pi * (340 + math.sin(i * 0.04) * 40) * (i / 22050.0)) * max(0.0, 1.0 - (i / 22050.0) / 0.15) * 9000)
            for i in range(3300)
        ]
        self._sounds["wobble"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(wobble_samples)))

    def play(self, name: str) -> None:
        if self._enabled and name in self._sounds:
            try:
                self._sounds[name].play()
            except Exception:
                pass

    def play_prompt(self, letter: str, locale: str = "it") -> None:
        key = f"{locale}:find_{letter.lower()}"
        if key in self._sounds:
            self.play(key)
        else:
            self.play_letter(letter, locale)

    def play_letter(self, letter: str, locale: str = "it") -> None:
        key = f"{locale}:{letter.lower()}"
        if key in self._sounds:
            self.play(key)
        else:
            self.play("pop")

    def play_word(self, word: str, locale: str = "it") -> None:
        key = f"{locale}:{word.lower()}"
        if key in self._sounds:
            self.play(key)
        else:
            self.play("chime")

    def play_praise(self, locale: str = "it") -> None:
        praise_keys = ["bravissima", "fantastico", "ottimo"] if locale == "it" else ["great_job", "wonderful", "you_did_it"]
        chosen = random.choice(praise_keys)
        key = f"{locale}:{chosen}"
        if key in self._sounds:
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
        self.vy += 0.08
        self.life -= self.decay
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        if self.life > 0:
            sz = max(1, int(self.size * self.life))
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), sz)
            pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), max(1, sz // 2))


class LetterOrb:
    def __init__(self, letter: str, x: float, y: float) -> None:
        self.letter = letter
        self.x = x
        self.y = y
        self.base_y = y
        self.radius = 38.0
        self.color_pair = random.choice(ORB_COLORS)
        self.phase = random.uniform(0, 2 * math.pi)
        self.vx = random.choice([-0.8, -0.5, 0.5, 0.8])
        self.wobble_timer = 0.0
        self.pulse = 0.0

    def update(self) -> None:
        self.phase += 0.035
        self.y = self.base_y + math.sin(self.phase) * 16.0
        self.x += self.vx
        if self.x < 180:
            self.x = 180
            self.vx = abs(self.vx)
        elif self.x > 940:
            self.x = 940
            self.vx = -abs(self.vx)
        if self.wobble_timer > 0:
            self.wobble_timer -= 0.05
        self.pulse += 0.04

    def wobble(self) -> None:
        self.wobble_timer = 1.0

    def contains(self, px: float, py: float) -> bool:
        return (self.x - px) ** 2 + (self.y - py) ** 2 <= (self.radius + 10) ** 2

    def draw(self, surface: pygame.Surface, typography: GreiaTypography) -> None:
        cx, cy = int(self.x), int(self.y)
        if self.wobble_timer > 0:
            cx += int(math.sin(self.wobble_timer * 18.0) * 8.0)

        glow_r = int(self.radius + 8 + math.sin(self.pulse) * 4)
        glow_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color_pair[1], 80), (glow_r + 2, glow_r + 2), glow_r)
        surface.blit(glow_surf, (cx - glow_r - 2, cy - glow_r - 2))

        pygame.draw.circle(surface, self.color_pair[0], (cx, cy), int(self.radius))
        pygame.draw.circle(surface, self.color_pair[1], (cx - 8, cy - 8), int(self.radius * 0.65))
        pygame.draw.circle(surface, WHITE, (cx - 12, cy - 12), 7)
        pygame.draw.circle(surface, DARK_TEXT, (cx, cy), int(self.radius), width=3)

        letter_surf = typography.render(self.letter, FontRole.DISPLAY, 36, DARK_TEXT)
        lx = cx - letter_surf.get_width() // 2
        ly = cy - letter_surf.get_height() // 2
        surface.blit(letter_surf, (lx, ly))


class OwlCompanion:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.blink_timer = 3.0
        self.happy_timer = 0.0
        self.bob = 0.0

    def cheer(self) -> None:
        self.happy_timer = 2.5

    def update(self) -> None:
        self.bob += 0.04
        self.blink_timer -= 0.02
        if self.blink_timer <= 0:
            self.blink_timer = random.uniform(2.5, 5.0)
        if self.happy_timer > 0:
            self.happy_timer -= 0.035

    def draw(self, surface: pygame.Surface) -> None:
        ox = int(self.x)
        oy = int(self.y + math.sin(self.bob) * 5)
        if self.happy_timer > 0:
            oy += int(abs(math.sin(self.happy_timer * 12.0)) * -14)

        pygame.draw.rect(surface, BRANCH_BROWN, (ox - 50, oy + 40, 100, 14), border_radius=6)
        pygame.draw.circle(surface, LEAF_GREEN, (ox + 50, oy + 38), 16)
        pygame.draw.circle(surface, LEAF_LIGHT, (ox + 56, oy + 34), 12)

        pygame.draw.ellipse(surface, (145, 95, 60), (ox - 32, oy - 26, 64, 72))
        pygame.draw.ellipse(surface, (235, 205, 170), (ox - 22, oy - 8, 44, 48))

        pygame.draw.polygon(surface, (120, 75, 45), [(ox - 28, oy - 24), (ox - 18, oy - 46), (ox - 6, oy - 24)])
        pygame.draw.polygon(surface, (120, 75, 45), [(ox + 6, oy - 24), (ox + 18, oy - 46), (ox + 28, oy - 24)])

        if self.blink_timer > 0.18:
            pygame.draw.circle(surface, WHITE, (ox - 14, oy - 8), 13)
            pygame.draw.circle(surface, WHITE, (ox + 14, oy - 8), 13)
            pygame.draw.circle(surface, DARK_TEXT, (ox - 12, oy - 8), 7)
            pygame.draw.circle(surface, DARK_TEXT, (ox + 12, oy - 8), 7)
            pygame.draw.circle(surface, WHITE, (ox - 14, oy - 10), 3)
            pygame.draw.circle(surface, WHITE, (ox + 10, oy - 10), 3)
        else:
            pygame.draw.line(surface, DARK_TEXT, (ox - 22, oy - 8), (ox - 6, oy - 8), 3)
            pygame.draw.line(surface, DARK_TEXT, (ox + 6, oy - 8), (ox + 22, oy - 8), 3)

        pygame.draw.polygon(surface, (255, 175, 35), [(ox, oy + 6), (ox - 6, oy - 2), (ox + 6, oy - 2)])

        if self.happy_timer > 0:
            pygame.draw.ellipse(surface, (120, 75, 45), (ox - 46, oy - 14, 20, 36))
            pygame.draw.ellipse(surface, (120, 75, 45), (ox + 26, oy - 14, 20, 36))
        else:
            pygame.draw.ellipse(surface, (120, 75, 45), (ox - 36, oy - 4, 16, 42))
            pygame.draw.ellipse(surface, (120, 75, 45), (ox + 20, oy - 4, 16, 42))


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
    vocab_items = PHONICS_DATA.get(active_locale, PHONICS_DATA["it"])

    score = 0
    stars = 0
    words_completed = 0

    if storage is not None:
        try:
            saved = storage.kv_get(STORAGE_KEY, {})
            if isinstance(saved, dict):
                score = int(saved.get("score", 0))
                stars = int(saved.get("stars", 0))
                words_completed = int(saved.get("words_completed", 0))
        except Exception:
            pass

    vocab_idx = 0
    cur_letter, cur_sound, cur_prompt, cur_word, cur_emoji, cur_word_audio = vocab_items[vocab_idx]
    matches_needed = 3
    matches_current = 0

    owl = OwlCompanion(140, 140)
    particles: list[Particle] = []
    orbs: list[LetterOrb] = []

    def spawn_orbs():
        orbs.clear()
        chosen_letters = [cur_letter, cur_letter, cur_letter]
        distractors = [item[0] for item in vocab_items if item[0] != cur_letter]
        chosen_letters.extend(random.sample(distractors, min(4, len(distractors))))
        random.shuffle(chosen_letters)

        slots = [
            (260, 240), (420, 220), (600, 240), (780, 220), (900, 280),
            (320, 420), (500, 440), (680, 420), (840, 430),
        ]
        random.shuffle(slots)
        for i, ltr in enumerate(chosen_letters):
            sx, sy = slots[i % len(slots)]
            orbs.append(LetterOrb(ltr, sx + random.uniform(-20, 20), sy + random.uniform(-15, 15)))

    spawn_orbs()

    feedback_text = ""
    feedback_timer = 0.0

    # Clean sequential audio & celebration transition state machine
    celebration_phase = "idle"  # "idle", "letter_done", "word_done", "praise_done"
    celebration_timer = 0.0
    initial_prompt_timer = 0.4  # Play first prompt after 0.4s when ready

    running = True
    ready_published = False

    card_rect = pygame.Rect(280, 14, 480, 96)
    audio_btn_rect = pygame.Rect(670, 24, 76, 76)

    while running and not activity_stop_requested():
        # Handle initial prompt speech cleanly after launch
        if initial_prompt_timer > 0:
            initial_prompt_timer -= 0.035
            if initial_prompt_timer <= 0:
                sounds.play_prompt(cur_letter, active_locale)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    sounds.play_prompt(cur_letter, active_locale)
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

                    # 1. Target Card Audio Button Click
                    if card_rect.collidepoint(lx, ly):
                        sounds.play_prompt(cur_letter, active_locale)
                        for _ in range(12):
                            particles.append(Particle(lx, ly, GOLD))
                        continue

                    # If in active celebration transition, pause orb clicks
                    if celebration_phase != "idle":
                        continue

                    hit_orb = None
                    for orb in list(orbs):
                        if orb.contains(lx, ly):
                            hit_orb = orb
                            break

                    if hit_orb is not None:
                        if hit_orb.letter == cur_letter:
                            sounds.play_letter(cur_letter, active_locale)
                            for _ in range(22):
                                particles.append(Particle(hit_orb.x, hit_orb.y, hit_orb.color_pair[1]))
                            orbs.remove(hit_orb)
                            score += 10
                            stars += 1
                            matches_current += 1
                            owl.cheer()
                            safe_emit("letter.matched", f"match-{time.time()}")

                            if matches_current >= matches_needed:
                                # Start sequential celebration queue
                                celebration_phase = "letter_done"
                                celebration_timer = 0.9
                                feedback_text = f"{cur_word} {cur_emoji}"
                                feedback_timer = 5.0
                                for _ in range(35):
                                    particles.append(Particle(512, 300, GOLD))
                            else:
                                feedback_text = resources.text("feedback.correct") if resources else "Bravissima! ✨"
                                feedback_timer = 1.8
                        else:
                            hit_orb.wobble()
                            sounds.play("wobble")
                            sounds.play_letter(hit_orb.letter, active_locale)
                            feedback_text = f"{hit_orb.letter}"
                            feedback_timer = 1.2

        # Step celebration state machine sequentially without audio collision
        if celebration_phase == "letter_done":
            celebration_timer -= 0.035
            if celebration_timer <= 0:
                sounds.play_word(cur_word_audio, active_locale)
                celebration_phase = "word_done"
                celebration_timer = 1.2
        elif celebration_phase == "word_done":
            celebration_timer -= 0.035
            if celebration_timer <= 0:
                sounds.play_praise(active_locale)
                words_completed += 1
                safe_emit("word.completed", f"word-{time.time()}", payload={"letter": cur_letter, "word": cur_word})
                feedback_text = resources.text("feedback.word_complete") if resources else "Splendido! 🌟"
                celebration_phase = "praise_done"
                celebration_timer = 1.6
        elif celebration_phase == "praise_done":
            celebration_timer -= 0.035
            if celebration_timer <= 0:
                # Save progress
                if storage is not None:
                    try:
                        storage.kv_set(STORAGE_KEY, {
                            "score": score,
                            "stars": stars,
                            "words_completed": words_completed,
                        })
                    except Exception:
                        pass

                # Advance to next letter
                vocab_idx = (vocab_idx + 1) % len(vocab_items)
                cur_letter, cur_sound, cur_prompt, cur_word, cur_emoji, cur_word_audio = vocab_items[vocab_idx]
                matches_current = 0
                spawn_orbs()
                sounds.play_prompt(cur_letter, active_locale)
                celebration_phase = "idle"

        owl.update()
        for orb in orbs:
            orb.update()
        particles = [p for p in particles if p.update()]

        if feedback_timer > 0:
            feedback_timer -= 0.035
        else:
            feedback_text = ""

        surf = canvas.surface

        for y in range(0, REFERENCE_HEIGHT, 10):
            ratio = y / float(REFERENCE_HEIGHT)
            col = mix(FOREST_SKY_BOTTOM, FOREST_SKY_TOP, ratio)
            pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 10))

        pygame.draw.circle(surf, CANOPY_DARK, (80, 520), 220)
        pygame.draw.circle(surf, CANOPY_DARK, (940, 520), 240)
        pygame.draw.circle(surf, CANOPY_LIGHT, (512, 590), 380)

        for fx in range(120, 920, 140):
            pygame.draw.circle(surf, LEAF_GREEN, (fx, 580), 28)
            pygame.draw.circle(surf, LEAF_LIGHT, (fx + 10, 574), 18)

        owl.draw(surf)

        for orb in orbs:
            orb.draw(surf, typography)

        for p in particles:
            p.draw(surf)

        pygame.draw.rect(surf, (15, 20, 30), (card_rect.x + 3, card_rect.y + 4, card_rect.width, card_rect.height), border_radius=16)
        pygame.draw.rect(surf, CARD_BG, card_rect, border_radius=16)
        pygame.draw.rect(surf, CARD_BORDER, card_rect, width=3, border_radius=16)

        letter_pill = pygame.Rect(card_rect.x + 12, card_rect.y + 10, 76, 76)
        pygame.draw.rect(surf, GOLD, letter_pill, border_radius=14)
        pygame.draw.rect(surf, CARD_BORDER, letter_pill, width=3, border_radius=14)
        big_l_surf = typography.render(cur_letter, FontRole.DISPLAY, 52, DARK_TEXT)
        surf.blit(big_l_surf, (letter_pill.centerx - big_l_surf.get_width() // 2, letter_pill.centery - big_l_surf.get_height() // 2))

        hint_str = f"{cur_word} {cur_emoji}"
        hint_surf = typography.render(hint_str, FontRole.TITLE, 34, DARK_TEXT)
        surf.blit(hint_surf, (card_rect.x + 104, card_rect.y + 12))

        for s_i in range(matches_needed):
            dot_x = card_rect.x + 108 + s_i * 38
            dot_y = card_rect.y + 60
            if s_i < matches_current:
                star_surf = typography.render("⭐", FontRole.BODY, 28, GOLD)
                surf.blit(star_surf, (dot_x, dot_y - 4))
            else:
                pygame.draw.circle(surf, (210, 195, 175), (dot_x + 12, dot_y + 12), 10)
                pygame.draw.circle(surf, CARD_BORDER, (dot_x + 12, dot_y + 12), 10, width=2)

        pygame.draw.rect(surf, (255, 225, 90), audio_btn_rect, border_radius=14)
        pygame.draw.rect(surf, CARD_BORDER, audio_btn_rect, width=3, border_radius=14)
        speaker_surf = typography.render("🔊", FontRole.DISPLAY, 38, DARK_TEXT)
        surf.blit(speaker_surf, (audio_btn_rect.centerx - speaker_surf.get_width() // 2, audio_btn_rect.centery - speaker_surf.get_height() // 2))

        hud_rect = pygame.Rect(785, 14, 215, 60)
        pygame.draw.rect(surf, CARD_BG, hud_rect, border_radius=16)
        pygame.draw.rect(surf, CARD_BORDER, hud_rect, width=3, border_radius=16)
        hud_text = f"⭐ {stars}   🏆 {score}"
        hud_surf = typography.render(hud_text, FontRole.TITLE, 24, DARK_TEXT)
        surf.blit(hud_surf, (hud_rect.centerx - hud_surf.get_width() // 2, hud_rect.centery - hud_surf.get_height() // 2))

        if feedback_text:
            fb_surf = typography.render(feedback_text, FontRole.TITLE, 28, GOLD)
            fb_bg = pygame.Rect(REFERENCE_WIDTH // 2 - fb_surf.get_width() // 2 - 24, 120, fb_surf.get_width() + 48, 48)
            pygame.draw.rect(surf, (20, 28, 44), fb_bg, border_radius=12)
            pygame.draw.rect(surf, GOLD, fb_bg, width=2, border_radius=12)
            surf.blit(fb_surf, (REFERENCE_WIDTH // 2 - fb_surf.get_width() // 2, 128))

        canvas.present(clear=theme.background)
        pygame.display.flip()
        if not ready_published:
            mark_activity_ready()
            ready_published = True

        clock.tick(30)

    if storage is not None:
        try:
            storage.kv_set(STORAGE_KEY, {
                "score": score,
                "stars": stars,
                "words_completed": words_completed,
            })
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
