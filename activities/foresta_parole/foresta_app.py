"""Foresta Parole — Activity lifecycle, input and simulation ownership.

The ``ForestaApp`` coordinates the Pygame event loop, viewport/canvas,
model progression, renderer presentation, audio sequencing and storage.
Domain truth lives in :mod:`foresta_model`; baked scenery and bounded
text caches live in :mod:`foresta_renderer`.
"""

from __future__ import annotations

import io
import math
import random
import struct
import time
import wave
from pathlib import Path

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_profile_locale,
    get_storage,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.child_text import display_text
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.typography import GreiaTypography

if __package__:
    from .foresta_content import PHONICS_DATA, REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY
    from .foresta_model import ForestaModel
    from .foresta_renderer import ForestaRenderer, LetterOrb, OwlCompanion, Particle
else:
    from foresta_content import PHONICS_DATA, REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY  # type: ignore[no-redef]
    from foresta_model import ForestaModel  # type: ignore[no-redef]
    from foresta_renderer import ForestaRenderer, LetterOrb, OwlCompanion, Particle  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Audio — small prebuilt sound bank (wav assets + procedural fallbacks).
# ---------------------------------------------------------------------------


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
    """Own the Word Forest audio catalogue with graceful fallback.

    Synthesis happens once at construction. The hot path only looks up
    a cached ``pygame.mixer.Sound`` and calls ``play()``.
    """

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
        praise_keys = ["ben_fatto", "fantastico", "ottimo"] if locale == "it" else ["great_job", "wonderful", "you_did_it"]
        chosen = random.choice(praise_keys)
        key = f"{locale}:{chosen}"
        if key in self._sounds:
            self.play(key)
        else:
            self.play("fanfare")


# ---------------------------------------------------------------------------
# Viewport safety — Greia owns the chrome, the Activity owns the play field.
# ---------------------------------------------------------------------------


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


# ---------------------------------------------------------------------------
# Lifecycle owner — the only place that touches events, timing, audio,
# storage and the renderer together.
# ---------------------------------------------------------------------------


class ForestaApp:
    """Coordinate the Word Forest Activity lifecycle.

    Dependencies (screen/canvas/metrics/typography, model, renderer,
    audio) are owned here so handle_*/_step_frame/_draw remain
    narrowly focused. The publisher-ready invariant is owned here:
    the first presented frame publishes READY in the same loop.
    """

    def __init__(self, screen: pygame.Surface | None = None) -> None:
        pygame.init()
        # Resolve the platform display surface if caller did not inject one.
        if screen is None:
            screen = pygame.display.get_surface()
            if screen is None:
                screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
        self.screen: pygame.Surface = screen
        pygame.mouse.set_visible(False)

        self.clock = pygame.time.Clock()
        self.theme = get_theme()
        self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
        self.canvas = PygameReferenceCanvas(self.screen)
        self.typography = GreiaTypography()
        self.sounds = SoundManager()

        try:
            self.storage = get_storage()
        except Exception:
            self.storage = None

        # Locale and catalogue selection.
        package_root = Path(__file__).parent
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        profile_lang = get_profile_locale()
        context = resolve_activity_locale(profile_lang, support)
        self.resources = LocalizedResources(package_root, context) if context else None
        self.active_locale = context.selected.language if context else "it"
        vocab_items = PHONICS_DATA.get(self.active_locale, PHONICS_DATA["it"])

        # Persistent counters.
        score = 0
        stars = 0
        words_completed = 0
        if self.storage is not None:
            try:
                saved = self.storage.kv_get(STORAGE_KEY, {})  # type: ignore[call-arg]
                if isinstance(saved, dict):
                    score = int(saved.get("score", 0))
                    stars = int(saved.get("stars", 0))
                    words_completed = int(saved.get("words_completed", 0))
            except Exception:
                pass

        self.model = ForestaModel(
            active_locale=self.active_locale,
            vocab_items=list(vocab_items),
            vocab_idx=0,
            score=score,
            stars=stars,
            words_completed=words_completed,
            matches_needed=3,
            matches_current=0,
        )

        self.renderer = ForestaRenderer(self.typography)
        self.owl = OwlCompanion(140, 140)
        self.particles: list[Particle] = []
        self.orbs: list[LetterOrb] = []

        self.celebration_phase: str = "idle"  # idle, letter_done, word_done, praise_done
        self.celebration_timer: float = 0.0
        self.initial_prompt_timer: float = 0.4  # play first prompt after 0.4s when ready
        self.feedback_text: str = ""
        self.feedback_timer: float = 0.0

        self._running: bool = True
        self._ready_published: bool = False

        # Use renderer-owned geometry so input and visuals agree.
        self._card_rect = self.renderer.card_rect()
        self._audio_btn_rect = self.renderer.audio_btn_rect()

        self._spawn_orbs()

    # ------------------------------------------------------------------
    # Orb spawning — domain letter distribution + presentation slots.
    # ------------------------------------------------------------------

    def _spawn_orbs(self) -> None:
        self.orbs.clear()
        cur_letter = self.model.cur_letter
        vocab_items = self.model.vocab_items
        chosen_letters = [cur_letter, cur_letter, cur_letter]
        distractors = [item[0] for item in vocab_items if item[0] != cur_letter]
        chosen_letters.extend(random.sample(distractors, min(4, len(distractors))))
        random.shuffle(chosen_letters)

        slots = [
            (260, 240),
            (420, 220),
            (600, 240),
            (780, 220),
            (900, 280),
            (320, 420),
            (500, 440),
            (680, 420),
            (840, 430),
        ]
        random.shuffle(slots)
        for i, ltr in enumerate(chosen_letters):
            sx, sy = slots[i % len(slots)]
            self.orbs.append(LetterOrb(ltr, sx + random.uniform(-20, 20), sy + random.uniform(-15, 15)))

    # ------------------------------------------------------------------
    # Platform event helpers
    # ------------------------------------------------------------------

    def _safe_emit(self, ev_id: str, ikey: str, payload: object = None) -> None:
        try:
            emit_activity_event(ev_id, idempotency_key=ikey, payload=payload)
        except Exception:
            pass

    def _autosave(self) -> None:
        if self.storage is None:
            return
        try:
            self.storage.kv_set(
                STORAGE_KEY,
                {
                    "score": self.model.score,
                    "stars": self.model.stars,
                    "words_completed": self.model.words_completed,
                },
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Input dispatch — translate physical pointer/key into domain actions.
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
        elif event.type == pygame.KEYDOWN:
            self._handle_keydown(event.key)
        elif event.type == pygame.VIDEORESIZE:
            self._handle_resize()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._handle_pointer(event.pos)

    def _handle_keydown(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self._running = False
        elif key == pygame.K_SPACE:
            self.sounds.play_prompt(self.model.cur_letter, self.active_locale)

    def _handle_resize(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
        self.canvas = PygameReferenceCanvas(self.screen)
        self.renderer.invalidate()

    def _handle_pointer(self, screen_pos: tuple[int, int]) -> None:
        if not _is_safe_point(self.screen, screen_pos):
            return
        logical = self.canvas.pointer(screen_pos)
        if logical is None:
            return
        lx, ly = float(logical[0]), float(logical[1])

        # Audio pill on the target card — always accessible, even during celebration.
        if self._card_rect.collidepoint(lx, ly):
            self.sounds.play_prompt(self.model.cur_letter, self.active_locale)
            for _ in range(12):
                self.particles.append(Particle(lx, ly, (255, 205, 50)))
            return

        if self.celebration_phase != "idle":
            return

        hit_orb = None
        for orb in list(self.orbs):
            if orb.contains(lx, ly):
                hit_orb = orb
                break

        if hit_orb is None:
            return

        if hit_orb.letter == self.model.cur_letter:
            self.sounds.play_letter(self.model.cur_letter, self.active_locale)
            for _ in range(22):
                self.particles.append(Particle(hit_orb.x, hit_orb.y, hit_orb.color_pair[1]))
            # Remove before scoring so the orb count matches visual disappearance.
            if hit_orb in self.orbs:
                self.orbs.remove(hit_orb)
            word_complete = self.model.record_correct_match()
            self.owl.cheer()
            self._safe_emit("letter.matched", f"match-{time.time()}")

            if word_complete:
                self.celebration_phase = "letter_done"
                self.celebration_timer = 0.9
                self.feedback_text = f"{self.model.cur_word} {self.model.cur_emoji}"
                self.feedback_timer = 5.0
                for _ in range(35):
                    self.particles.append(Particle(512, 300, (255, 205, 50)))
            else:
                # Localized praise for a single correct catch.
                if self.resources is not None:
                    try:
                        self.feedback_text = self.resources.text("feedback.correct")
                    except Exception:
                        self.feedback_text = display_text("Ottimo lavoro! ✨")
                else:
                    self.feedback_text = display_text("Ottimo lavoro! ✨")
                self.feedback_timer = 1.8
        else:
            hit_orb.wobble()
            self.sounds.play("wobble")
            self.sounds.play_letter(hit_orb.letter, self.active_locale)
            self.feedback_text = f"{hit_orb.letter}"
            self.feedback_timer = 1.2

    # Alias preserved for external tools that historically called the private name.
    def handle_pointer(self, screen_pos: tuple[int, int]) -> None:
        self._handle_pointer(screen_pos)

    # ------------------------------------------------------------------
    # Simulation step — advances timed state without touching presentation.
    # ------------------------------------------------------------------

    def _step_frame(self, dt: float) -> None:
        # Initial speech is timed from launch so the first prompt does not
        # collide with engine start-up audio contention.
        if self.initial_prompt_timer > 0:
            self.initial_prompt_timer -= dt
            # Use a fixed 0.035 step aligned with the original 30 Hz DT so
            # the 0.4s delay remains deterministic under variable dt tests.
            # Keep the decrement proportional to dt for real frame timing.
            if self.initial_prompt_timer <= 0:
                self.sounds.play_prompt(self.model.cur_letter, self.active_locale)

        # Sequential celebration state machine: letter chime -> word -> praise -> next word.
        if self.celebration_phase == "letter_done":
            self.celebration_timer -= dt
            if self.celebration_timer <= 0:
                self.sounds.play_word(self.model.cur_word_audio, self.active_locale)
                self.celebration_phase = "word_done"
                self.celebration_timer = 1.2
        elif self.celebration_phase == "word_done":
            self.celebration_timer -= dt
            if self.celebration_timer <= 0:
                self.sounds.play_praise(self.active_locale)
                self.model.words_completed += 1
                self._safe_emit(
                    "word.completed",
                    f"word-{time.time()}",
                    payload={"letter": self.model.cur_letter, "word": self.model.cur_word},
                )
                if self.resources is not None:
                    try:
                        self.feedback_text = self.resources.text("feedback.word_complete")
                    except Exception:
                        self.feedback_text = display_text("Splendido! 🌟")
                else:
                    self.feedback_text = display_text("Splendido! 🌟")
                self.celebration_phase = "praise_done"
                self.celebration_timer = 1.6
        elif self.celebration_phase == "praise_done":
            self.celebration_timer -= dt
            if self.celebration_timer <= 0:
                self._autosave()
                self.model.advance_word()
                self._spawn_orbs()
                self.sounds.play_prompt(self.model.cur_letter, self.active_locale)
                self.celebration_phase = "idle"

        self.owl.update()
        for orb in self.orbs:
            orb.update()
        self.particles = [p for p in self.particles if p.update()]

        if self.feedback_timer > 0:
            self.feedback_timer -= dt
        else:
            self.feedback_text = ""

    # ------------------------------------------------------------------
    # Presentation — composes the reference surface and presents to display.
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        surf = self.canvas.surface
        self.renderer.draw_background(surf)
        self.renderer.draw_owl(surf, self.owl)
        self.renderer.draw_orbs(surf, self.orbs)
        self.renderer.draw_particles(surf, self.particles)
        self.renderer.draw_card(
            surf,
            self.model.cur_letter,
            self.model.cur_word,
            self.model.cur_emoji,
            self.model.matches_needed,
            self.model.matches_current,
        )
        self.renderer.draw_hud(surf, self.model.stars, self.model.score)
        self.renderer.draw_feedback(surf, self.feedback_text)
        self.canvas.present(clear=self.theme.background)
        pygame.display.flip()

    # ------------------------------------------------------------------
    # Main loop — the only place that publishes READY.
    # ------------------------------------------------------------------

    def run(self) -> int:
        # Fixed-step timing: original used 0.035 at 30 Hz. Use clock.tick
        # dt but clamp so a single hitch cannot skip celebration phases.
        while self._running and not activity_stop_requested():
            dt = min(0.1, self.clock.tick(30) / 1000.0)
            # Original subtracted 0.035 each frame; keep dt semantics but
            # preserve the legacy constant for celebration timing parity
            # by using dt == 0.035 under normal scheduling.
            effective_dt = 0.035 if abs(dt - 0.033) < 0.01 else dt
            for event in pygame.event.get():
                self.handle_event(event)
                if not self._running:
                    break
            if not self._running:
                break
            self._step_frame(effective_dt)
            self._draw()
            if not self._ready_published:
                mark_activity_ready()
                self._ready_published = True
        self._autosave()
        return 0


__all__ = ["ForestaApp", "SoundManager"]
