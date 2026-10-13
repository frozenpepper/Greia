"""Domain model and letter catalogue for L'Alfabeto di Leo."""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Final

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600


@dataclass(frozen=True)
class LetterItem:
    char: str
    word_it: str
    word_en: str
    symbol_it: str
    symbol_en: str
    color: tuple[int, int, int]
    word_es: str = ""
    symbol_es: str = ""
    word_fr: str = ""
    symbol_fr: str = ""

    @property
    def symbol(self) -> str:
        return self.symbol_it

    @staticmethod
    def _supported_lesson_language(locale: str) -> str:
        """Fail closed until a language has real curriculum example words.

        Translating Activity chrome is not equivalent to translating
        the alphabet's symbols, phonemes and accompanying spoken examples.
        """
        language = locale.replace("_", "-").split("-", 1)[0].lower()
        if language not in ("it", "en", "es", "fr"):
            raise ValueError(f"unsupported alphabet lesson language: {language}")
        return language

    def symbol_for(self, locale: str) -> str:
        language = self._supported_lesson_language(locale)
        symbol = getattr(self, f"symbol_{language}")
        if not symbol:
            raise ValueError(f"letter {self.char} has no {language} example")
        return symbol

    def word_for(self, locale: str) -> str:
        language = self._supported_lesson_language(locale)
        word = getattr(self, f"word_{language}")
        if not word:
            raise ValueError(f"letter {self.char} has no {language} example")
        return word


LETTERS_CATALOGUE: Final[list[LetterItem]] = [
    LetterItem("A", "APE", "APPLE", "🐝", "🍎", (240, 70, 70)),
    LetterItem("B", "BARCA", "BOAT", "⛵", "⛵", (70, 150, 240)),
    LetterItem("C", "CANE", "CAT", "🐶", "🐱", (245, 150, 60)),
    LetterItem("D", "DELFINO", "DUCK", "🐬", "🦆", (60, 190, 220)),
    LetterItem("E", "ELEFANTE", "ELEPHANT", "🐘", "🐘", (160, 120, 200)),
    LetterItem("F", "FARFALLA", "FISH", "🦋", "🐟", (240, 100, 170)),
    LetterItem("G", "GATTO", "GIRAFFE", "🐱", "🦒", (250, 180, 50)),
    LetterItem("H", "HOTEL", "HOUSE", "🏨", "🏠", (100, 180, 130)),
    LetterItem("I", "ISOLA", "IGLOO", "🏝️", "🧊", (70, 190, 180)),
    LetterItem("J", "JEEP", "JELLYFISH", "🚙", "🪼", (60, 140, 210)),
    LetterItem("K", "KOALA", "KITE", "🐨", "🪁", (170, 140, 120)),
    LetterItem("L", "LUNA", "LION", "🌙", "🦁", (255, 215, 60)),
    LetterItem("M", "MELA", "MOON", "🍎", "🌙", (230, 60, 60)),
    LetterItem("N", "NAVE", "NEST", "🚢", "🪺", (80, 130, 200)),
    LetterItem("O", "ORSO", "OWL", "🐻", "🦉", (175, 110, 65)),
    LetterItem("P", "PALLA", "PENGUIN", "⚽", "🐧", (235, 90, 130)),
    LetterItem("Q", "QUADRO", "QUEEN", "🖼️", "👑", (180, 130, 90)),
    LetterItem("R", "RANA", "RAINBOW", "🐸", "🌈", (110, 200, 70)),
    LetterItem("S", "SOLE", "SUN", "☀️", "☀️", (255, 190, 40)),
    LetterItem("T", "TRENO", "TRAIN", "🚂", "🚂", (210, 80, 60)),
    LetterItem("U", "UVA", "UMBRELLA", "🍇", "☂️", (150, 80, 190)),
    LetterItem("V", "VULCANO", "VIOLIN", "🌋", "🎻", (220, 100, 50)),
    LetterItem("W", "WAFER", "WHALE", "🧇", "🐋", (210, 160, 100)),
    LetterItem("X", "XILOFONO", "XYLOPHONE", "🎵", "🎵", (100, 170, 220)),
    LetterItem("Y", "YOGURT", "YACHT", "🥣", "⛵", (240, 140, 180)),
    LetterItem("Z", "ZEBRA", "ZEBRA", "🦓", "🦓", (70, 70, 80)),
]

LETTER_BY_CHAR: Final[dict[str, LetterItem]] = {item.char: item for item in LETTERS_CATALOGUE}



# Staged orthographic examples for alphabet discovery only. H is silent
# in Spanish/French; letter NAME vs PHONEME and digraph behavior require
# native review and approved voice clips before these are child-selectable.
EXAMPLES_ES: Final[dict[str, tuple[str, str]]] = {
    "A": ("ABEJA", "🐝"),
    "B": ("BARCO", "⛵"),
    "C": ("CASA", "🏠"),
    "D": ("DADO", "🎲"),
    "E": ("ELEFANTE", "🐘"),
    "F": ("FLOR", "🌸"),
    "G": ("GATO", "🐱"),
    "H": ("HELADO", "🍦"),
    "I": ("ISLA", "🏝️"),
    "J": ("JIRAFA", "🦒"),
    "K": ("KIWI", "🥝"),
    "L": ("LUNA", "🌙"),
    "M": ("MANZANA", "🍎"),
    "N": ("NUBE", "☁️"),
    "O": ("OSO", "🐻"),
    "P": ("PATO", "🦆"),
    "Q": ("QUESO", "🧀"),
    "R": ("RANA", "🐸"),
    "S": ("SOL", "☀️"),
    "T": ("TREN", "🚂"),
    "U": ("UVA", "🍇"),
    "V": ("VACA", "🐄"),
    "W": ("WAFLE", "🧇"),
    "X": ("XILÓFONO", "🎼"),
    "Y": ("YATE", "⛵"),
    "Z": ("ZAPATO", "👞"),
}

EXAMPLES_FR: Final[dict[str, tuple[str, str]]] = {
    "A": ("AVION", "✈️"),
    "B": ("BATEAU", "⛵"),
    "C": ("CAROTTE", "🥕"),
    "D": ("DINOSAURE", "🦕"),
    "E": ("ESCARGOT", "🐌"),
    "F": ("FLEUR", "🌸"),
    "G": ("GÂTEAU", "🎂"),
    "H": ("HÉRISSON", "🦔"),
    "I": ("IGLOO", "🧊"),
    "J": ("JARDIN", "🌳"),
    "K": ("KOALA", "🐨"),
    "L": ("LUNE", "🌙"),
    "M": ("MAISON", "🏠"),
    "N": ("NUAGE", "☁️"),
    "O": ("OURS", "🐻"),
    "P": ("POMME", "🍎"),
    "Q": ("QUATRE", "4️⃣"),
    "R": ("ROBOT", "🤖"),
    "S": ("SOLEIL", "☀️"),
    "T": ("TORTUE", "🐢"),
    "U": ("USINE", "🏭"),
    "V": ("VÉLO", "🚲"),
    "W": ("WAGON", "🚃"),
    "X": ("XYLOPHONE", "🎶"),
    "Y": ("YAOURT", "🥣"),
    "Z": ("ZÈBRE", "🦓"),
}


_SPANISH_STANDARD: Final[tuple[LetterItem, ...]] = tuple(
    replace(item,
            word_es=EXAMPLES_ES[item.char][0], symbol_es=EXAMPLES_ES[item.char][1])
    for item in LETTERS_CATALOGUE
)
# Ñ is a full Spanish alphabet letter between N and O, not a variant of N.
SPANISH_ENYE: Final[LetterItem] = LetterItem(
    "Ñ", "", "", "", "", (76, 135, 194),
    word_es="ÑANDÚ", symbol_es="🐦",
)
LETTERS_CATALOGUE_ES: Final[tuple[LetterItem, ...]] = (
    _SPANISH_STANDARD[:14] + (SPANISH_ENYE,) + _SPANISH_STANDARD[14:]
)
LETTERS_CATALOGUE_FR: Final[tuple[LetterItem, ...]] = tuple(
    replace(item,
            word_fr=EXAMPLES_FR[item.char][0], symbol_fr=EXAMPLES_FR[item.char][1])
    for item in LETTERS_CATALOGUE
)

_ALPHABETS: Final[dict[str, tuple[LetterItem, ...]]] = {
    "it": tuple(LETTERS_CATALOGUE),
    "en": tuple(LETTERS_CATALOGUE),
    "es": LETTERS_CATALOGUE_ES,
    "fr": LETTERS_CATALOGUE_FR,
}


def get_letter_catalogue(locale: str) -> tuple[LetterItem, ...]:
    """Actual lesson alphabet with Spanish Ñ; never guess a different language."""
    language = LetterItem._supported_lesson_language(locale)
    return _ALPHABETS[language]




class GameMode(StrEnum):
    EXPLORE = "explore"
    GUESS = "guess"


@dataclass
class AlfabetoModel:
    """State management for toddler alphabet discovery."""

    locale: str = "it"
    current_index: int = 0
    revealed: bool = True
    reveal_timer: float = 0.0
    discovered_letters: set[str] = field(default_factory=lambda: {"A"})
    mode: GameMode = GameMode.EXPLORE

    # Guess Mode State
    target_letter: LetterItem = field(default_factory=lambda: LETTERS_CATALOGUE[0])
    guess_choices: list[LetterItem] = field(default_factory=list)
    guess_solved: bool = False
    guess_solved_timer: float = 0.0
    wobble_card: str = ""
    wobble_timer: float = 0.0
    celebrating: bool = False
    _pending_discoveries: list[str] = field(default_factory=list, repr=False)
    _parade_recorded: bool = False

    def __post_init__(self) -> None:
        # Reject unsupported pedagogical locales even before the first frame.
        get_letter_catalogue(self.locale)
        self.select_letter("A")

    @property
    def letters(self) -> tuple[LetterItem, ...]:
        return get_letter_catalogue(self.locale)

    @property
    def active_letter(self) -> LetterItem:
        return self.letters[self.current_index]

    def step(self, delta: int) -> LetterItem:
        """Step previous (-1) or next (+1) in alphabet."""
        self.current_index = (self.current_index + delta) % len(self.letters)
        item = self.active_letter
        self._discover(item.char)
        self.revealed = True
        self.reveal_timer = 0.6
        return item

    def select_letter(self, char: str) -> bool:
        """Jump directly to a specific letter."""
        char_upper = char.upper()
        for idx, item in enumerate(self.letters):
            if item.char == char_upper:
                self.current_index = idx
                self._discover(item.char)
                self.revealed = True
                self.reveal_timer = 0.6
                return True
        return False

    def _discover(self, char: str) -> None:
        if char not in self.discovered_letters:
            self.discovered_letters.add(char)
            self._pending_discoveries.append(char)

    def restore_discoveries(self, letters: set[str]) -> None:
        """Restore previously seen letters without creating new history facts."""
        valid = {item.char for item in self.letters}
        self.discovered_letters.update(letters & valid)
        self._parade_recorded = len(self.discovered_letters) == len(valid)
        self._pending_discoveries.clear()

    def switch_mode(self, mode: GameMode) -> None:
        self.mode = mode
        self.celebrating = False
        self.wobble_card = ""
        self.wobble_timer = 0.0
        if mode == GameMode.GUESS:
            self.setup_new_guess()

    def setup_new_guess(self) -> None:
        """Set up a new 3-choice letter guessing challenge."""
        self.guess_solved = False
        self.guess_solved_timer = 0.0
        self.celebrating = False
        self.wobble_card = ""
        self.wobble_timer = 0.0

        # Choose target letter
        self.target_letter = random.choice(self.letters)

        # Pick 2 different distractors
        other_letters = [item for item in self.letters if item.char != self.target_letter.char]
        distractors = random.sample(other_letters, 2)

        choices = [self.target_letter, distractors[0], distractors[1]]
        random.shuffle(choices)
        self.guess_choices = choices

    def handle_guess_choice(self, chosen_char: str) -> tuple[str, LetterItem]:
        """Handle child tap on one of the 3 cards."""
        if self.guess_solved:
            return ("next", self.target_letter)

        if chosen_char == self.target_letter.char:
            self.guess_solved = True
            self.guess_solved_timer = 1.8
            self.celebrating = True
            self._discover(self.target_letter.char)
            return ("correct", self.target_letter)
        else:
            self.wobble_card = chosen_char
            self.wobble_timer = 0.5
            return ("wobble", self.target_letter)

    def update(self, dt: float) -> list[str]:
        """Update animation timers and state transitions."""
        events: list[str] = ["letter.discovered" for _ in self._pending_discoveries]
        if self._pending_discoveries:
            self._pending_discoveries.clear()
            if len(self.discovered_letters) == len(self.letters) and not self._parade_recorded:
                self._parade_recorded = True
                events.append("alphabet.parade_completed")

        if self.reveal_timer > 0.0:
            self.reveal_timer = max(0.0, self.reveal_timer - dt)

        if self.wobble_timer > 0.0:
            self.wobble_timer = max(0.0, self.wobble_timer - dt)
            if self.wobble_timer == 0.0:
                self.wobble_card = ""

        if self.guess_solved:
            self.guess_solved_timer -= dt
            if self.guess_solved_timer <= 0.0:
                self.setup_new_guess()

        return events
