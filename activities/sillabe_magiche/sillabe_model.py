from __future__ import annotations

"""Pure domain state for Sillabe Magiche — no pygame, no IO.

SillabeSession owns persistent progression (score/stars/words_completed) and
the logical syllable/word challenge state. Rendering, audio timing, storage
IO and event emission live outside this module; the session only decides what
a child action means and how persistent counters advance.

Randomness is injected so tests can freeze generation without monkey-patching
global state. Storage mapping is intentionally trivial so the app can reuse
GreiaStorage without duplicating policy.
"""

from dataclasses import dataclass, field
import random
from typing import Protocol, Sequence


class RandomSource(Protocol):
    def choice(self, seq: Sequence[object]) -> object: ...

    def sample(self, population: Sequence[str], k: int) -> list[str]: ...

    def shuffle(self, x: list[object]) -> None: ...

    def uniform(self, a: float, b: float) -> float: ...


@dataclass(slots=True)
class SillabeSession:
    """Own deterministic syllable-magic progression state.

    The session knows the current locale's word pool and the Italian consonant/
    vowel inventories, but it never touches pygame, storage or audio. The app
    drives timers and presentation; the session decides correctness and scoring.
    """

    words_pool: list[tuple[str, tuple[str, str], str, str]] = field(default_factory=list, repr=False)
    consonants_pool: Sequence[str] = field(default_factory=tuple, repr=False)  # type: ignore[assignment]
    vowels_pool: Sequence[str] = field(default_factory=tuple, repr=False)  # type: ignore[assignment]
    rng: RandomSource = field(default_factory=random.Random, repr=False)  # type: ignore[assignment]

    # Persistent progression
    score: int = 0
    stars: int = 0
    words_completed: int = 0

    # Explorer
    active_consonant: str = "B"
    consonant_index: int = 0

    # Catcher (Acchiappa)
    target_syl: str = "BA"
    catcher_state: str = "idle"  # "idle" | "praise_pending" | "next_round_pending"
    catcher_timer: float = 0.0

    # Builder (Crea Parole)
    word_index: int = 0
    cur_word_display: str = "CASA"
    cur_s1: str = "CA"
    cur_s2: str = "SA"
    cur_emoji: str = "🏠"
    cur_stem: str = "casa"
    slot1_filled: bool = False
    slot2_filled: bool = False
    word_completed: bool = False
    syllable_speech_step: int = 0
    syllable_speech_timer: float = 0.0
    word_completion_step: int = 0
    word_completion_timer: float = 0.0
    current_mode: str = "explorer"  # "explorer" | "catcher" | "builder"

    def __post_init__(self) -> None:
        if self.score < 0:
            self.score = 0
        if self.stars < 0:
            self.stars = 0
        if self.words_completed < 0:
            self.words_completed = 0
        if self.words_pool:
            self._sync_word_from_index()
        if self.consonants_pool:
            # Clamp active consonant to pool
            if self.active_consonant not in self.consonants_pool:
                self.active_consonant = str(self.consonants_pool[0])
                self.consonant_index = 0
            else:
                self.consonant_index = list(self.consonants_pool).index(self.active_consonant)
        # Ensure target/catcher have a valid syllable
        if not self.target_syl and self.consonants_pool and self.vowels_pool:
            self.target_syl = f"{self.consonants_pool[0]}{self.vowels_pool[0]}"

    # ------------------------------------------------------------------ #
    # Persistence helpers
    # ------------------------------------------------------------------ #
    def load_progress(self, data: object) -> None:
        if not isinstance(data, dict):
            return
        try:
            self.score = int(data.get("score", self.score))  # type: ignore[union-attr]
            self.stars = int(data.get("stars", self.stars))  # type: ignore[union-attr]
            self.words_completed = int(data.get("words_completed", self.words_completed))  # type: ignore[union-attr]
        except Exception:
            pass
        if self.score < 0:
            self.score = 0
        if self.stars < 0:
            self.stars = 0
        if self.words_completed < 0:
            self.words_completed = 0

    def save_progress(self) -> dict[str, int]:
        return {"score": self.score, "stars": self.stars, "words_completed": self.words_completed}

    # ------------------------------------------------------------------ #
    # Explorer
    # ------------------------------------------------------------------ #
    def set_active_consonant(self, consonant: str) -> None:
        if consonant not in self.consonants_pool:
            raise ValueError(f"unknown consonant {consonant!r}")
        self.active_consonant = consonant
        self.consonant_index = list(self.consonants_pool).index(consonant)

    def explorer_syllables(self) -> list[str]:
        return [f"{self.active_consonant}{v}" for v in self.vowels_pool]

    def on_explore(self, syl: str) -> None:
        # Every explorer tap that reaches the domain is a scored exploration.
        self.score += 1

    # ------------------------------------------------------------------ #
    # Catcher
    # ------------------------------------------------------------------ #
    def start_catcher_round(self) -> tuple[str, list[str]]:
        """Pick a new target and 6 orb syllables (including duplicates of target).

        Returns the chosen target and the shuffled orb list. Caller owns placement.
        """
        # Choose target syllable
        c = self.rng.choice(list(self.consonants_pool))  # type: ignore[arg-type]
        v = self.rng.choice(list(self.vowels_pool))  # type: ignore[arg-type]
        self.target_syl = f"{c}{v}"
        self.catcher_state = "idle"
        self.catcher_timer = 0.0

        orb_syls: list[str] = [self.target_syl, self.target_syl]
        # Fill to 6 unique distractors
        attempts = 0
        while len(orb_syls) < 6 and attempts < 100:
            rc = self.rng.choice(list(self.consonants_pool))  # type: ignore[arg-type]
            rv = self.rng.choice(list(self.vowels_pool))  # type: ignore[arg-type]
            cand = f"{rc}{rv}"
            if cand != self.target_syl and cand not in orb_syls:
                orb_syls.append(cand)
            attempts += 1
        # Shuffle in place via injected rng
        try:
            self.rng.shuffle(orb_syls)  # type: ignore[attr-defined]
        except Exception:
            random.shuffle(orb_syls)
        return self.target_syl, list(orb_syls)

    def on_catcher_tap(self, syl: str) -> bool:
        """Process a tap on an orb while in idle state.

        Returns True when the tap matches the target and advances scoring/state.
        No-op when not idle. Correct taps arm praise/next-round timers.
        """
        if self.catcher_state != "idle":
            return False
        if syl == self.target_syl:
            self.stars += 1
            self.score += 5
            self.catcher_state = "praise_pending"
            self.catcher_timer = 0.55
            return True
        return False

    # ------------------------------------------------------------------ #
    # Builder
    # ------------------------------------------------------------------ #
    def _sync_word_from_index(self) -> None:
        if not self.words_pool:
            return
        entry = self.words_pool[self.word_index % len(self.words_pool)]
        disp, (s1, s2), emoji, stem = entry
        self.cur_word_display = disp
        self.cur_s1 = s1
        self.cur_s2 = s2
        self.cur_emoji = emoji
        self.cur_stem = stem
        self.slot1_filled = False
        self.slot2_filled = False
        self.word_completed = False
        self.syllable_speech_step = 0
        self.syllable_speech_timer = 0.0
        self.word_completion_step = 0
        self.word_completion_timer = 0.0

    def start_word_round(self) -> tuple[tuple[str, tuple[str, str], str, str], list[str]]:
        """Reset builder slots and generate 4 tile choices for the current word.

        Returns the current word tuple and the shuffled choice list.
        """
        self._sync_word_from_index()
        choices = [self.cur_s1, self.cur_s2]
        attempts = 0
        while len(choices) < 4 and attempts < 100:
            rc = self.rng.choice(list(self.consonants_pool))  # type: ignore[arg-type]
            rv = self.rng.choice(list(self.vowels_pool))  # type: ignore[arg-type]
            cand = f"{rc}{rv}"
            if cand not in choices:
                choices.append(cand)
            attempts += 1
        try:
            self.rng.shuffle(choices)  # type: ignore[attr-defined]
        except Exception:
            random.shuffle(choices)
        return (self.cur_word_display, (self.cur_s1, self.cur_s2), self.cur_emoji, self.cur_stem), list(choices)

    def on_builder_tile(self, syl: str) -> str:
        """Process a builder tile tap.

        Returns one of: "wrong_slot1", "slot1_ok", "wrong_slot2", "word_done", "already_done".
        Updates slots, score and stars where appropriate and arms timed audio steps.
        """
        if self.word_completed:
            return "already_done"
        if not self.slot1_filled:
            if syl == self.cur_s1:
                self.slot1_filled = True
                return "slot1_ok"
            return "wrong_slot1"
        if not self.slot2_filled:
            if syl == self.cur_s2:
                self.slot2_filled = True
                self.word_completed = True
                self.word_completion_step = 1
                self.word_completion_timer = 0.50
                self.stars += 2
                self.score += 10
                self.words_completed += 1
                return "word_done"
            return "wrong_slot2"
        return "already_done"

    def advance_word(self) -> None:
        self.word_index += 1
        self.start_word_round()

    def start_syllable_breakdown(self) -> None:
        self.syllable_speech_step = 1
        self.syllable_speech_timer = 0.52

    # ------------------------------------------------------------------ #
    # Mode
    # ------------------------------------------------------------------ #
    def set_mode(self, mode: str) -> None:
        if mode not in ("explorer", "catcher", "builder"):
            raise ValueError(f"unknown mode {mode!r}")
        self.current_mode = mode


__all__ = ["RandomSource", "SillabeSession"]
