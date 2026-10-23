"""Versioned locale-aware spelling for authored letter and number targets.

Semantic request text remains authoritative and unchanged. This collaborator
only supplies the words sent to speech generation and exact, position-bound
letter-name aliases for comparing the retained target.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from .number_lexicon import cardinal_spellings

POLICY = "locale-spoken-letter-and-cardinal-v1"

# Standard names used only when a single grapheme is explicitly written as a
# letter example (e.g. "K as Koala"), never for letters inside ordinary words.
LETTER_NAMES = {
    "en": {"A":"ay", "B":"bee", "C":"see", "D":"dee", "E":"ee", "F":"eff", "G":"gee",
           "H":"aitch", "I":"eye", "J":"jay", "K":"kay", "L":"ell", "M":"em", "N":"en",
           "O":"oh", "P":"pee", "Q":"cue", "R":"ar", "S":"ess", "T":"tee", "U":"you",
           "V":"vee", "W":"double-u", "X":"ex", "Y":"why", "Z":"zee"},
    "it": {"A":"a", "B":"bi", "C":"ci", "D":"di", "E":"e", "F":"effe", "G":"gi", "H":"acca",
           "I":"i", "J":"i lunga", "K":"cappa", "L":"elle", "M":"emme", "N":"enne", "O":"o",
           "P":"pi", "Q":"cu", "R":"erre", "S":"esse", "T":"ti", "U":"u", "V":"vu",
           "W":"doppia vu", "X":"ics", "Y":"ipsilon", "Z":"zeta"},
    "fr": {"A":"a", "B":"bé", "C":"cé", "D":"dé", "E":"e", "F":"effe", "G":"gé", "H":"ache",
           "I":"i", "J":"ji", "K":"ka", "L":"elle", "M":"emme", "N":"enne", "O":"o", "P":"pé",
           "Q":"ku", "R":"erre", "S":"esse", "T":"té", "U":"u", "V":"vé", "W":"double vé",
           "X":"iks", "Y":"i grec", "Z":"zède"},
    "es": {"A":"a", "B":"be", "C":"ce", "D":"de", "E":"e", "F":"efe", "G":"ge", "H":"hache",
           "I":"i", "J":"jota", "K":"ka", "L":"ele", "M":"eme", "N":"ene", "Ñ":"eñe", "O":"o",
           "P":"pe", "Q":"cu", "R":"erre", "S":"ese", "T":"te", "U":"u", "V":"uve",
           "W":"doble u", "X":"equis", "Y":"ye", "Z":"zeta"},
}

CONNECTORS = {"en": "as", "it": "come", "fr": "comme", "es": "de"}
_CARDINAL = {locale: {str(value): word for value, word in enumerate(cardinal_spellings(locale))}
             for locale in ("en", "it", "fr", "es")}
_INTEGER = re.compile(r"(?<![\w.,:/+−-])(\d+)(?![\w.,:/+−-])", re.UNICODE)
_ANY_DIGIT = re.compile(r"\d", re.UNICODE)
_LETTER_EXAMPLE = re.compile(r"(?<!\w)([A-ZÑ])(?=\s+(?:as|de|come|comme)\b)", re.IGNORECASE | re.UNICODE)
_LETTER_EXAMPLE_PREFIX = re.compile(r"^([A-ZÑ])(?=\s+(?:as|de|come|comme)\b)", re.IGNORECASE | re.UNICODE)


@dataclass(frozen=True)
class SpokenTarget:
    """A semantic target and its frozen, human-spellable generation form."""

    semantic_text: str
    spoken_text: str
    locale: str
    policy: str = POLICY
    letter_code: str | None = None
    replacements: tuple[dict[str, str], ...] = ()


def letter_aliases(locale: str) -> dict[str, tuple[tuple[str, ...], ...]]:
    """Return exact written name and glyph aliases, indexed by letter code."""
    locale = locale.casefold().split("-", 1)[0]
    if locale not in LETTER_NAMES:
        raise ValueError("unsupported spoken-letter locale")
    result = {}
    for code, name in LETTER_NAMES[locale].items():
        aliases = {tuple(name.casefold().split()), (code.casefold(),)}
        if locale == "en" and code == "W":
            aliases.update({("double", "u"), ("double", "you")})
        if locale == "es" and code == "Y":
            aliases.add(("i", "griega"))
        result[code] = tuple(sorted(aliases, key=lambda parts: (-len(parts), parts)))
    if locale == "es":
        result["Ñ"] = (tuple("eñe".split()), ("ñ",))
    return result


def letter_example_code(locale: str, text: str) -> str | None:
    """Identify a leading standalone letter in the localized example syntax."""
    locale = locale.casefold().split("-", 1)[0]
    if locale not in CONNECTORS or not isinstance(text, str):
        return None
    match = _LETTER_EXAMPLE_PREFIX.match(text.strip())
    if not match:
        return None
    code = match.group(1).upper()
    return code if code in LETTER_NAMES[locale] else None


def spoken_target(locale: str, semantic_text: str) -> SpokenTarget:
    """Spell contextual letter graphemes and plain integer numerals safely.

    Number conversion is deliberately limited to standalone integers in the
    existing 0..100 locale lexicon. Embedded codes, decimals, dates, signed
    values and out-of-range numerals fail closed rather than being guessed.
    """
    locale = locale.casefold().split("-", 1)[0]
    if locale not in LETTER_NAMES or not isinstance(semantic_text, str):
        raise ValueError("unsupported locale or semantic target")
    replacements: list[dict[str, str]] = []
    text = semantic_text

    def number(match: re.Match[str]) -> str:
        numeral = match.group(1)
        if numeral not in _CARDINAL[locale]:
            raise ValueError(f"standalone cardinal {numeral} is outside the supported 0..100 lexicon")
        word = _CARDINAL[locale][numeral]
        replacements.append({"kind": "cardinal", "semantic": numeral, "spoken": word})
        return word

    text = _INTEGER.sub(number, text)
    if _ANY_DIGIT.search(text):
        raise ValueError("numeric code, decimal, signed value or date cannot be spoken as a guessed cardinal")
    names = LETTER_NAMES[locale]

    def letter(match: re.Match[str]) -> str:
        code = match.group(1).upper()
        if code not in names:
            raise ValueError(f"no spoken letter name for {locale}:{code}")
        name = names[code]
        replacements.append({"kind": "letter", "semantic": code, "spoken": name})
        return name

    text = _LETTER_EXAMPLE.sub(letter, text)
    code = letter_example_code(locale, semantic_text)
    return SpokenTarget(semantic_text, text, locale, letter_code=code, replacements=tuple(replacements))
