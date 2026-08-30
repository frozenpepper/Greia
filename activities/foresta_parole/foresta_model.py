"""Foresta Parole — pure domain state (vocab progression, scoring).

Owns the letter/word invariants and progression without pygame, storage
or audio. Rendering, input timing and platform IO live outside this class.
"""

from __future__ import annotations

from dataclasses import dataclass, field

if __package__:
    from .foresta_content import MATCHES_NEEDED, PHONICS_DATA
else:
    from foresta_content import MATCHES_NEEDED, PHONICS_DATA  # type: ignore[no-redef]


@dataclass(slots=True)
class ForestaModel:
    """Deterministic phonics progression for one Word Forest session.

    The model tracks which letter/word the forest is currently teaching,
    how many correct catches the child has made for that letter, and the
    durable counters (score, stars, words_completed). It never performs
    rendering, audio or storage; those owners are injected by the app.

    The letter's identity (`cur_letter`) is domain truth, while the
    child's selection lives as transient orb clicks in the app layer.
    """

    active_locale: str = "it"
    vocab_idx: int = 0
    score: int = 0
    stars: int = 0
    words_completed: int = 0
    matches_needed: int = MATCHES_NEEDED
    matches_current: int = 0

    vocab_items: list[tuple[str, str, str, str, str, str]] = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.score < 0:
            self.score = 0
        if self.stars < 0:
            self.stars = 0
        if self.words_completed < 0:
            self.words_completed = 0
        if self.vocab_items is None:
            self.vocab_items = PHONICS_DATA.get(self.active_locale, PHONICS_DATA["it"])
        if not self.vocab_items:
            self.vocab_items = PHONICS_DATA["it"]
        if self.matches_needed <= 0:
            self.matches_needed = MATCHES_NEEDED
        if self.matches_current < 0:
            self.matches_current = 0
        if self.matches_current > self.matches_needed:
            self.matches_current = self.matches_needed
        # Clamp vocab index into valid range even after stale saves.
        if self.vocab_idx < 0 or self.vocab_idx >= len(self.vocab_items):
            self.vocab_idx %= len(self.vocab_items) if self.vocab_items else 1

    # -- current vocabulary ------------------------------------------------

    @property
    def cur(self) -> tuple[str, str, str, str, str, str]:
        if not self.vocab_items:
            return ("A", "a", "find_a", "Ape", "🐝", "ape")
        return self.vocab_items[self.vocab_idx % len(self.vocab_items)]

    @property
    def cur_letter(self) -> str:
        return self.cur[0]

    @property
    def cur_letter_id(self) -> str:
        return self.cur[1]

    @property
    def cur_prompt_id(self) -> str:
        return self.cur[2]

    @property
    def cur_word(self) -> str:
        return self.cur[3]

    @property
    def cur_emoji(self) -> str:
        return self.cur[4]

    @property
    def cur_word_audio(self) -> str:
        return self.cur[5]

    # -- scoring / progression ---------------------------------------------

    def record_correct_match(self) -> bool:
        """Register one correct letter catch.

        Returns True when the current word is now complete and celebration
        should start. Score/stars are always incremented for a correct catch.
        """

        self.score += 10
        self.stars += 1
        self.matches_current += 1
        return self.matches_current >= self.matches_needed

    def reset_matches(self) -> None:
        self.matches_current = 0

    def advance_word(self) -> None:
        """Move to next vocabulary entry after celebration completes."""

        self.vocab_idx = (self.vocab_idx + 1) % len(self.vocab_items) if self.vocab_items else 0
        self.matches_current = 0

    @property
    def is_word_complete(self) -> bool:
        return self.matches_current >= self.matches_needed

    # -- persistence helpers ------------------------------------------------

    def to_storage(self) -> dict[str, int]:
        return {
            "score": int(self.score),
            "stars": int(self.stars),
            "words_completed": int(self.words_completed),
            "vocab_idx": int(self.vocab_idx),
            "matches_current": int(self.matches_current),
        }

    def apply_storage(self, saved: dict[str, object] | None) -> None:
        if not isinstance(saved, dict):
            return
        try:
            self.score = int(saved.get("score", self.score))  # type: ignore[arg-type]
        except Exception:
            pass
        try:
            self.stars = int(saved.get("stars", self.stars))  # type: ignore[arg-type]
        except Exception:
            pass
        try:
            self.words_completed = int(saved.get("words_completed", self.words_completed))  # type: ignore[arg-type]
        except Exception:
            pass
        # Older saves may not have vocab_idx; preserve current if missing.
        if "vocab_idx" in saved:
            try:
                raw_idx = int(saved.get("vocab_idx", self.vocab_idx))  # type: ignore[arg-type]
                if self.vocab_items:
                    self.vocab_idx = raw_idx % len(self.vocab_items)
            except Exception:
                pass


__all__ = ["ForestaModel"]
