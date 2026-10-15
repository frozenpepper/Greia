"""Letter catalogue and round model for L'Alfabeto di Leo — Leo's Letter Garden.

One core experience: *meet a letter, find it, trace it*. A garden round takes
one small group of letters (two or three). For each letter Leo says its name
with its example word ("A as Apple") beside the picture (MEET), the child finds
it among a few letter tiles (FIND), then traces it stroke by stroke (TRACE);
the letter blooms and is planted in the garden. Two review finds close the
round. Letters are introduced in teaching groups (frequent, easy-to-say
letters first, never A→Z), and the stages of the same loop get harder:

* groups 1–2: two tiles, shapes that look different;
* groups 3–4: three tiles;
* group 5 onwards: three tiles where one decoy looks alike (E/F, P/R, M/N…);
* after the whole alphabet: review gardens of three letters the child has
  traced least, always with look-alike decoys.

Example words follow the owner-approved letter clips (``letter_<X>.wav`` say
"A as Apple" / "A come Ape"), so the picture always matches what is heard.
ES/FR are staged curricula (not voice-approved, not manifest-enabled).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
import random
from typing import Final, Sequence

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600
REVIEW_FINDS: Final[int] = 2
MAX_GROUP_LETTERS: Final[int] = 3
# A picture ID for staged words that still lack library art (never EN/IT).
PICTURE_PENDING: Final[str] = "pending"
SUPPORTED_LANGUAGES: Final[tuple[str, ...]] = ("it", "en", "es", "fr")


@dataclass(frozen=True)
class LetterItem:
    """One alphabet letter with each language's example word and picture.

    ``picture_*`` is a shared visual ID (``prop.*``, ``creature.*``,
    ``character.<id>#<variant>``), an ``activity:<name>`` picture under this
    package's ``assets/runtime``, or ``PICTURE_PENDING``.
    """

    char: str
    word_it: str
    word_en: str
    picture_it: str
    picture_en: str
    color: str
    word_es: str = ""
    picture_es: str = ""
    word_fr: str = ""
    picture_fr: str = ""

    @staticmethod
    def _supported_lesson_language(locale: str) -> str:
        """Fail closed until a language has real curriculum example words.

        Translating Activity chrome is not equivalent to translating the
        alphabet's examples and their spoken clips.
        """

        language = locale.replace("_", "-").split("-", 1)[0].lower()
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"unsupported alphabet lesson language: {language}")
        return language

    def word_for(self, locale: str) -> str:
        language = self._supported_lesson_language(locale)
        word = getattr(self, f"word_{language}")
        if not word:
            raise ValueError(f"letter {self.char} has no {language} example")
        return word

    def picture_for(self, locale: str) -> str:
        language = self._supported_lesson_language(locale)
        picture = getattr(self, f"picture_{language}")
        if not picture:
            raise ValueError(f"letter {self.char} has no {language} picture entry")
        return picture


# Colour tokens (runtime/theme-defaults accents) give each letter its own ink.
LETTERS_CATALOGUE: Final[list[LetterItem]] = [
    LetterItem("A", "APE", "APPLE", "prop.vocab.bee", "prop.food.apple", "coral"),
    LetterItem("B", "BARCA", "BOAT", "prop.vocab.boat", "prop.vocab.boat", "ocean"),
    LetterItem("C", "CANE", "CAT", "prop.vocab.dog", "prop.vocab.cat", "orange"),
    LetterItem("D", "DELFINO", "DUCK", "creature.marine.dolphin", "prop.everyday.duck", "turquoise"),
    LetterItem("E", "ELEFANTE", "ELEPHANT", "prop.vocab.elephant", "prop.vocab.elephant", "grape"),
    LetterItem("F", "FARFALLA", "FISH", "prop.vocab.butterfly", "prop.food.fish", "raspberry"),
    LetterItem("G", "GATTO", "GIRAFFE", "prop.vocab.cat", "activity:giraffe", "leaf"),
    LetterItem("H", "HOTEL", "HOUSE", "activity:hotel", "prop.vocab.house", "ocean"),
    LetterItem("I", "ISOLA", "IGLOO", "activity:island", "activity:igloo", "turquoise"),
    LetterItem("J", "JEEP", "JELLYFISH", "activity:jeep", "creature.marine.jellyfish", "grape"),
    LetterItem("K", "KOALA", "KITE", "activity:koala", "prop.vocab.kite", "coral"),
    LetterItem("L", "LUNA", "LION", "prop.vocab.moon", "prop.vocab.lion", "orange"),
    LetterItem("M", "MELA", "MOON", "prop.food.apple", "prop.vocab.moon", "raspberry"),
    LetterItem("N", "NAVE", "NEST", "activity:ship", "prop.vocab.nest", "ocean"),
    LetterItem("O", "ORSO", "OWL", "prop.vocab.bear", "character.leo#pose_wave", "orange"),
    LetterItem("P", "PALLA", "PENGUIN", "prop.everyday.ball", "prop.vocab.penguin", "coral"),
    LetterItem("Q", "QUADRO", "QUEEN", "activity:painting", "prop.vocab.crown", "grape"),
    LetterItem("R", "RANA", "RAINBOW", "prop.vocab.frog", "prop.nature.rainbow", "leaf"),
    LetterItem("S", "SOLE", "SUN", "prop.nature.sun", "prop.nature.sun", "orange"),
    LetterItem("T", "TRENO", "TRAIN", "prop.vocab.train", "prop.vocab.train", "coral"),
    LetterItem("U", "UVA", "UMBRELLA", "prop.vocab.grapes", "prop.vocab.umbrella", "grape"),
    LetterItem("V", "VULCANO", "VIOLIN", "activity:volcano", "activity:violin", "raspberry"),
    LetterItem("W", "WAFER", "WHALE", "activity:wafer", "prop.vocab.whale", "ocean"),
    LetterItem("X", "XILOFONO", "XYLOPHONE", "activity:xylophone", "activity:xylophone", "turquoise"),
    LetterItem("Y", "YOGURT", "YACHT", "activity:yogurt", "activity:yacht", "raspberry"),
    LetterItem("Z", "ZEBRA", "ZEBRA", "activity:zebra", "activity:zebra", "leaf"),
]

LETTER_BY_CHAR: Final[dict[str, LetterItem]] = {item.char: item for item in LETTERS_CATALOGUE}


# Staged orthographic examples (word, picture). H is silent in Spanish/French;
# letter NAME vs PHONEME and digraph behaviour need native review and approved
# voice clips before these become child-selectable.
EXAMPLES_ES: Final[dict[str, tuple[str, str]]] = {
    "A": ("ABEJA", "prop.vocab.bee"),
    "B": ("BARCO", "prop.vocab.boat"),
    "C": ("CASA", "prop.vocab.house"),
    "D": ("DADO", "pending"),
    "E": ("ELEFANTE", "prop.vocab.elephant"),
    "F": ("FLOR", "prop.nature.flower"),
    "G": ("GATO", "prop.vocab.cat"),
    "H": ("HELADO", "prop.vocab.ice_cream"),
    "I": ("ISLA", "activity:island"),
    "J": ("JIRAFA", "activity:giraffe"),
    "K": ("KIWI", "pending"),
    "L": ("LUNA", "prop.vocab.moon"),
    "M": ("MANZANA", "prop.food.apple"),
    "N": ("NUBE", "prop.nature.cloud"),
    "O": ("OSO", "prop.vocab.bear"),
    "P": ("PATO", "prop.everyday.duck"),
    "Q": ("QUESO", "pending"),
    "R": ("RANA", "prop.vocab.frog"),
    "S": ("SOL", "prop.nature.sun"),
    "T": ("TREN", "prop.vocab.train"),
    "U": ("UVA", "prop.vocab.grapes"),
    "V": ("VACA", "pending"),
    "W": ("WAFLE", "activity:wafer"),
    "X": ("XILÓFONO", "activity:xylophone"),
    "Y": ("YATE", "activity:yacht"),
    "Z": ("ZAPATO", "pending"),
}

EXAMPLES_FR: Final[dict[str, tuple[str, str]]] = {
    "A": ("AVION", "prop.vocab.plane"),
    "B": ("BATEAU", "prop.vocab.boat"),
    "C": ("CAROTTE", "prop.food.carrot"),
    "D": ("DINOSAURE", "pending"),
    "E": ("ESCARGOT", "prop.vocab.snail"),
    "F": ("FLEUR", "prop.nature.flower"),
    "G": ("GÂTEAU", "prop.vocab.cake"),
    "H": ("HÉRISSON", "creature.woodland.hedgehog"),
    "I": ("IGLOO", "activity:igloo"),
    "J": ("JARDIN", "pending"),
    "K": ("KOALA", "activity:koala"),
    "L": ("LUNE", "prop.vocab.moon"),
    "M": ("MAISON", "prop.vocab.house"),
    "N": ("NUAGE", "prop.nature.cloud"),
    "O": ("OURS", "prop.vocab.bear"),
    "P": ("POMME", "prop.food.apple"),
    "Q": ("QUATRE", "pending"),
    "R": ("ROBOT", "pending"),
    "S": ("SOLEIL", "prop.nature.sun"),
    "T": ("TORTUE", "creature.marine.turtle"),
    "U": ("USINE", "pending"),
    "V": ("VÉLO", "prop.vocab.bicycle"),
    "W": ("WAGON", "pending"),
    "X": ("XYLOPHONE", "activity:xylophone"),
    "Y": ("YAOURT", "activity:yogurt"),
    "Z": ("ZÈBRE", "activity:zebra"),
}


_SPANISH_STANDARD: Final[tuple[LetterItem, ...]] = tuple(
    replace(item, word_es=EXAMPLES_ES[item.char][0], picture_es=EXAMPLES_ES[item.char][1])
    for item in LETTERS_CATALOGUE
)
# Ñ is a full Spanish alphabet letter between N and O, not a variant of N.
SPANISH_ENYE: Final[LetterItem] = LetterItem(
    "Ñ", "", "", "", "", "ocean",
    word_es="ÑANDÚ", picture_es=PICTURE_PENDING,
)
LETTERS_CATALOGUE_ES: Final[tuple[LetterItem, ...]] = (
    _SPANISH_STANDARD[:14] + (SPANISH_ENYE,) + _SPANISH_STANDARD[14:]
)
LETTERS_CATALOGUE_FR: Final[tuple[LetterItem, ...]] = tuple(
    replace(item, word_fr=EXAMPLES_FR[item.char][0], picture_fr=EXAMPLES_FR[item.char][1])
    for item in LETTERS_CATALOGUE
)

_ALPHABETS: Final[dict[str, tuple[LetterItem, ...]]] = {
    "it": tuple(LETTERS_CATALOGUE),
    "en": tuple(LETTERS_CATALOGUE),
    "es": LETTERS_CATALOGUE_ES,
    "fr": LETTERS_CATALOGUE_FR,
}

# Teaching order: frequent letters with easy, distinct names first; look-alike
# pairs are kept in different groups. English follows the common phonics order
# (s a t / p i n …); the Romance languages start from the five vowels.
TEACHING_GROUPS: Final[dict[str, tuple[str, ...]]] = {
    "en": ("SAT", "PIN", "MDO", "CKE", "GUR", "HBF", "LJV", "WYZ", "XQ"),
    "it": ("AEI", "OUL", "MPS", "NRT", "BCD", "FGV", "ZHQ", "JKW", "XY"),
    "es": ("AEI", "OUL", "MPS", "NRT", "BCD", "FGV", "ZHÑ", "JQY", "KWX"),
    "fr": ("AEI", "OUL", "MPS", "NRT", "BCD", "FGV", "ZHQ", "JKW", "XY"),
}

# Capital letters children confuse; decoys from here make the late stages harder.
LOOK_ALIKES: Final[dict[str, str]] = {
    "A": "HVN", "B": "RPD", "C": "GOU", "D": "OBP", "E": "FB", "F": "EPT",
    "G": "CQO", "H": "NAK", "I": "LTJ", "J": "UIL", "K": "XRH", "L": "ITE",
    "M": "NWV", "N": "MHZ", "Ñ": "NMH", "O": "QCD", "P": "RBF", "Q": "OGC",
    "R": "PBK", "S": "ZG", "T": "IYL", "U": "VJO", "V": "YUW", "W": "MV",
    "X": "KYV", "Y": "VTX", "Z": "SN",
}


def lesson_language(locale: str) -> str:
    return LetterItem._supported_lesson_language(locale)


def get_letter_catalogue(locale: str) -> tuple[LetterItem, ...]:
    """Actual lesson alphabet with Spanish Ñ; never guess a different language."""

    return _ALPHABETS[lesson_language(locale)]


def teaching_groups(locale: str) -> tuple[str, ...]:
    return TEACHING_GROUPS[lesson_language(locale)]


class StepKind(StrEnum):
    MEET = "meet"
    FIND = "find"
    TRACE = "trace"
    REVIEW = "review"


@dataclass(frozen=True, slots=True)
class GardenStep:
    """One step of a garden round. FIND/REVIEW carry the letter tiles."""

    kind: StepKind
    letter: LetterItem
    choices: tuple[LetterItem, ...] = ()
    correct_index: int = 0

    def __post_init__(self) -> None:
        if self.kind in {StepKind.FIND, StepKind.REVIEW}:
            if not 2 <= len(self.choices) <= 3:
                raise ValueError("a find step needs two or three letter tiles")
            if len({item.char for item in self.choices}) != len(self.choices):
                raise ValueError("letter tiles must be distinct")
            if self.choices[self.correct_index].char != self.letter.char:
                raise ValueError("the correct tile must show the target letter")

    @property
    def is_find(self) -> bool:
        return self.kind in {StepKind.FIND, StepKind.REVIEW}

    @property
    def counts_as_task(self) -> bool:
        return self.kind is not StepKind.MEET


@dataclass(frozen=True, slots=True)
class FindResult:
    correct: bool
    errors: int
    round_complete: bool = False


@dataclass(slots=True)
class _StepProgress:
    errors: int = 0
    hints: int = 0
    eliminated: set[int] = field(default_factory=set)


class GardenPlanner:
    """Build garden rounds: which letters, in which order, with which decoys."""

    def __init__(self, rng: random.Random, locale: str = "it") -> None:
        self._rng = rng
        self._locale = locale
        self._letters = {item.char: item for item in get_letter_catalogue(locale)}
        self._groups = teaching_groups(locale)

    @property
    def group_count(self) -> int:
        return len(self._groups)

    def letters_for(self, group: int, traced: dict[str, int] | None = None) -> tuple[LetterItem, ...]:
        """Letters of teaching ``group``; past the last group, a review trio."""

        if 0 <= group < len(self._groups):
            return tuple(self._letters[char] for char in self._groups[group])
        counts = traced or {}
        pool = list(self._letters.values())
        self._rng.shuffle(pool)
        pool.sort(key=lambda item: counts.get(item.char, 0))  # least practised first (stable)
        return tuple(pool[:MAX_GROUP_LETTERS])

    def build(self, group: int, traced: dict[str, int] | None = None) -> tuple[GardenStep, ...]:
        letters = self.letters_for(group, traced)
        known = self._known_before(group)
        choices = 2 if group < 2 else 3
        look_alike = group >= 4
        # Decoys prefer letters the child has met (this group, then earlier ones).
        pool = tuple(item.char for item in letters) + known
        steps: list[GardenStep] = []
        last_slot = -1
        for item in letters:
            steps.append(GardenStep(StepKind.MEET, item))
            find, last_slot = self._find(StepKind.FIND, item, choices, look_alike, pool=pool, last_slot=last_slot)
            steps.append(find)
            steps.append(GardenStep(StepKind.TRACE, item))
        for target in self._review_targets(letters):
            review, last_slot = self._find(StepKind.REVIEW, target, choices, look_alike, pool=pool, last_slot=last_slot)
            steps.append(review)
        return tuple(steps)

    # -- helpers ---------------------------------------------------------------
    def _known_before(self, group: int) -> tuple[str, ...]:
        if group <= 0:
            return ()
        upto = min(group, len(self._groups))
        return tuple(char for chars in self._groups[:upto] for char in chars)

    def _review_targets(self, letters: Sequence[LetterItem]) -> list[LetterItem]:
        """Review letters in a new order; never the letter just traced first."""

        order = list(letters)
        self._rng.shuffle(order)
        if len(order) > 1 and order[0].char == letters[-1].char:
            order.append(order.pop(0))
        while len(order) < REVIEW_FINDS:
            order.append(self._rng.choice(list(letters)))
        return order[:REVIEW_FINDS]

    def _find(
        self,
        kind: StepKind,
        target: LetterItem,
        count: int,
        look_alike: bool,
        *,
        pool: Sequence[str],
        last_slot: int,
    ) -> tuple[GardenStep, int]:
        decoys = self._decoys(target, count - 1, look_alike, pool)
        options = [slot for slot in range(len(decoys) + 1) if slot != last_slot] or [0]
        slot = self._rng.choice(options)
        ordered = list(decoys)
        ordered.insert(slot, target)
        return GardenStep(kind, target, tuple(ordered), slot), slot

    def _decoys(self, target: LetterItem, wanted: int, look_alike: bool, pool: Sequence[str]) -> list[LetterItem]:
        similar = [c for c in LOOK_ALIKES.get(target.char, "") if c in self._letters and c != target.char]
        picked: list[str] = []
        if look_alike and similar:
            picked.append(self._rng.choice(similar))
        preferred = [c for c in dict.fromkeys(pool) if c != target.char and c not in picked]
        self._rng.shuffle(preferred)
        if not look_alike:
            # Early stages: decoys must look clearly different from the target.
            preferred = [c for c in preferred if c not in similar]
        others = [c for c in self._letters if c != target.char and c not in picked and c not in preferred]
        self._rng.shuffle(others)
        if not look_alike:
            others = [c for c in others if c not in similar]
        for char in preferred + others:
            if len(picked) >= wanted:
                break
            if char not in picked:
                picked.append(char)
        return [self._letters[c] for c in picked[:wanted]]


class GardenRound:
    """State of one garden round: steps, tries, hints, traced letters, completion."""

    def __init__(self, steps: Sequence[GardenStep], *, group: int) -> None:
        if not steps:
            raise ValueError("a garden round needs steps")
        self._steps = tuple(steps)
        self.group = int(group)
        self._index = 0
        self._progress = _StepProgress()
        self._planted: list[LetterItem] = []
        self.find_errors = 0
        self.hints = 0
        self.first_try_finds = 0
        self._completion_consumed = False

    # -- queries -----------------------------------------------------------------
    @property
    def steps(self) -> tuple[GardenStep, ...]:
        return self._steps

    @property
    def step(self) -> GardenStep | None:
        return None if self.is_complete else self._steps[self._index]

    @property
    def step_index(self) -> int:
        return self._index

    @property
    def is_complete(self) -> bool:
        return self._index >= len(self._steps)

    @property
    def letters(self) -> tuple[LetterItem, ...]:
        return tuple(step.letter for step in self._steps if step.kind is StepKind.MEET)

    @property
    def planted(self) -> tuple[LetterItem, ...]:
        """Letters traced this round, in order (the garden beds that bloomed)."""

        return tuple(self._planted)

    @property
    def task_total(self) -> int:
        return sum(step.counts_as_task for step in self._steps)

    @property
    def tasks_done(self) -> int:
        return sum(step.counts_as_task for step in self._steps[: self._index])

    @property
    def eliminated(self) -> frozenset[int]:
        return frozenset(self._progress.eliminated)

    @property
    def errors(self) -> int:
        return self._progress.errors

    # -- actions -----------------------------------------------------------------
    def record_hint(self) -> None:
        if not self.is_complete:
            self._progress.hints = min(32, self._progress.hints + 1)
            self.hints = min(999, self.hints + 1)

    def finish_meet(self) -> None:
        self._require(StepKind.MEET)
        self._advance()

    def select(self, index: int) -> FindResult:
        step = self.step
        if step is None or not step.is_find:
            raise RuntimeError("no letter tiles to choose from")
        if not 0 <= index < len(step.choices):
            raise IndexError("tile index out of range")
        progress = self._progress
        if index != step.correct_index:
            progress.errors += 1
            progress.eliminated.add(index)
            self.find_errors += 1
            return FindResult(False, progress.errors)
        if progress.errors == 0:
            self.first_try_finds += 1
        self._advance()
        return FindResult(True, 0, self.is_complete)

    def finish_trace(self) -> bool:
        """Plant the traced letter; True when the round is complete."""

        step = self._require(StepKind.TRACE)
        self._planted.append(step.letter)
        self._advance()
        return self.is_complete

    def consume_completion(self) -> dict[str, int] | None:
        if not self.is_complete or self._completion_consumed:
            return None
        self._completion_consumed = True
        return {
            "group": self.group + 1,
            "letters": len(self._planted),
            "first_try_finds": self.first_try_finds,
            "retries": self.find_errors,
        }

    def _require(self, kind: StepKind) -> GardenStep:
        step = self.step
        if step is None or step.kind is not kind:
            raise RuntimeError(f"current step is not {kind.value}")
        return step

    def _advance(self) -> None:
        self._index += 1
        self._progress = _StepProgress()


def next_group(current: int, round_: GardenRound, group_count: int) -> int:
    """Bounded adaptation: repeat a group the child found hard, else move on.

    Past the last teaching group the child stays in review gardens
    (``group_count``), which pick the least-practised letters.
    """

    if round_.find_errors >= 3:
        return max(0, min(current, group_count))
    return min(group_count, current + 1)


__all__ = [
    "EXAMPLES_ES",
    "EXAMPLES_FR",
    "FindResult",
    "GardenPlanner",
    "GardenRound",
    "GardenStep",
    "LETTERS_CATALOGUE",
    "LETTER_BY_CHAR",
    "LOOK_ALIKES",
    "LetterItem",
    "PICTURE_PENDING",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "REVIEW_FINDS",
    "SPANISH_ENYE",
    "StepKind",
    "TEACHING_GROUPS",
    "get_letter_catalogue",
    "lesson_language",
    "next_group",
    "teaching_groups",
]
