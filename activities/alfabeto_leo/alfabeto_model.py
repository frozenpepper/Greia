"""Domain model and letter catalogue for L'Alfabeto di Leo."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600


@dataclass(frozen=True)
class LetterItem:
    char: str
    word_it: str
    word_en: str
    symbol: str
    color: tuple[int, int, int]

    def word_for(self, locale: str) -> str:
        return self.word_it if locale.startswith("it") else self.word_en


LETTERS_CATALOGUE: Final[list[LetterItem]] = [
    LetterItem("A", "APE", "APPLE", "🍎", (240, 70, 70)),
    LetterItem("B", "BARCA", "BOAT", "⛵", (70, 150, 240)),
    LetterItem("C", "CANE", "CAT", "🐶", (245, 150, 60)),
    LetterItem("D", "DELFINO", "DUCK", "🐬", (60, 190, 220)),
    LetterItem("E", "ELEFANTE", "ELEPHANT", "🐘", (160, 120, 200)),
    LetterItem("F", "FARFALLA", "FISH", "🦋", (240, 100, 170)),
    LetterItem("G", "GATTO", "GIRAFFE", "🐱", (250, 180, 50)),
    LetterItem("H", "HOTEL", "HOUSE", "🏠", (100, 180, 130)),
    LetterItem("I", "ISOLA", "IGLOO", "🏝️", (70, 190, 180)),
    LetterItem("J", "JEEP", "JELLYFISH", "🚙", (60, 140, 210)),
    LetterItem("K", "KOALA", "KITE", "🐨", (170, 140, 120)),
    LetterItem("L", "LUNA", "LION", "🌙", (255, 215, 60)),
    LetterItem("M", "MELA", "MOON", "🍎", (230, 60, 60)),
    LetterItem("N", "NAVE", "NEST", "🚢", (80, 130, 200)),
    LetterItem("O", "ORSO", "OWL", "🐻", (175, 110, 65)),
    LetterItem("P", "PALLA", "PENGUIN", "⚽", (235, 90, 130)),
    LetterItem("Q", "QUADRO", "QUEEN", "🖼️", (180, 130, 90)),
    LetterItem("R", "RANA", "RAINBOW", "🐸", (110, 200, 70)),
    LetterItem("S", "SOLE", "SUN", "☀️", (255, 190, 40)),
    LetterItem("T", "TRENO", "TRAIN", "🚂", (210, 80, 60)),
    LetterItem("U", "UVA", "UMBRELLA", "🍇", (150, 80, 190)),
    LetterItem("V", "VULCANO", "VIOLIN", "🌋", (220, 100, 50)),
    LetterItem("W", "WAFER", "WHALE", "🧇", (210, 160, 100)),
    LetterItem("X", "XILOFONO", "XYLOPHONE", "🎵", (100, 170, 220)),
    LetterItem("Y", "YOGURT", "YACHT", "🥣", (240, 140, 180)),
    LetterItem("Z", "ZEBRA", "ZEBRA", "🦓", (70, 70, 80)),
]

LETTER_BY_CHAR: Final[dict[str, LetterItem]] = {item.char: item for item in LETTERS_CATALOGUE}


class GameMode(StrEnum):
    EXPLORE = "explore"
    GUESS = "guess"


@dataclass
class AlfabetoModel:
    """State machine for toddler letter exploration."""

    locale: str = "it"
    mode: GameMode = GameMode.EXPLORE
    current_index: int = 0
    active_letter: LetterItem = field(default_factory=lambda: LETTERS_CATALOGUE[0])
    revealed: bool = False
    reveal_timer: float = 0.0
    wobble_timer: float = 0.0
    wobble_card: str | None = None
    discovered_letters: set[str] = field(default_factory=set)
    celebrating: bool = False
    celebration_timer: float = 0.0
    leo_mood: str = "neutral"
    leo_jump: float = 0.0
    # Guess mode state
    target_letter: LetterItem = field(default_factory=lambda: LETTERS_CATALOGUE[0])
    guess_choices: list[LetterItem] = field(default_factory=list)
    guess_solved: bool = False

    def __post_init__(self) -> None:
        self.select_letter("A")
        self.setup_guess_round()

    def select_letter(self, char: str) -> bool:
        """Select a letter by character (A-Z)."""
        clean = char.upper()
        item = LETTER_BY_CHAR.get(clean)
        if item is None:
            return False

        self.active_letter = item
        self.current_index = [it.char for it in LETTERS_CATALOGUE].index(clean)
        self.revealed = True
        self.reveal_timer = 0.6
        self.leo_mood = "happy"
        self.leo_jump = 0.3
        self.discovered_letters.add(clean)
        return True

    def setup_guess_round(self) -> None:
        """Prepare a peek-a-boo round: 1 target and 2 friendly distractors."""
        self.target_letter = random.choice(LETTERS_CATALOGUE)
        pool = [it for it in LETTERS_CATALOGUE if it.char != self.target_letter.char]
        distractors = random.sample(pool, 2)
        choices = [self.target_letter] + distractors
        random.shuffle(choices)
        self.guess_choices = choices
        self.guess_solved = False
        self.celebrating = False
        self.celebration_timer = 0.0
        self.leo_mood = "neutral"

    def handle_guess_choice(self, char: str) -> tuple[str, LetterItem]:
        """Process a guess selection."""
        if self.guess_solved:
            self.setup_guess_round()
            return ("next", self.target_letter)

        if char.upper() == self.target_letter.char:
            self.guess_solved = True
            self.celebrating = True
            self.celebration_timer = 0.0
            self.leo_mood = "surprised"
            self.leo_jump = 0.4
            self.discovered_letters.add(char.upper())
            return ("correct", self.target_letter)
        else:
            # Gentle wobble on the wrong choice, zero punishment
            self.wobble_card = char.upper()
            self.wobble_timer = 0.35
            self.leo_mood = "blink"
            return ("wobble", self.target_letter)

    def switch_mode(self, new_mode: GameMode) -> None:
        self.mode = new_mode
        self.celebrating = False
        self.celebration_timer = 0.0
        self.leo_mood = "neutral"
        if new_mode == GameMode.GUESS:
            self.setup_guess_round()

    def update(self, dt: float) -> list[str]:
        events: list[str] = []

        if self.reveal_timer > 0.0:
            self.reveal_timer = max(0.0, self.reveal_timer - dt)

        if self.wobble_timer > 0.0:
            self.wobble_timer = max(0.0, self.wobble_timer - dt)
            if self.wobble_timer == 0.0:
                self.wobble_card = None

        if self.leo_jump > 0.0:
            self.leo_jump = max(0.0, self.leo_jump - dt)

        if self.celebrating:
            prev = self.celebration_timer
            self.celebration_timer += dt
            if prev == 0.0:
                events.append("letter.discovered")
                if len(self.discovered_letters) >= 10:
                    events.append("alphabet.parade_completed")
            if self.celebration_timer >= 2.8:
                if self.mode == GameMode.GUESS:
                    self.setup_guess_round()

        return events
