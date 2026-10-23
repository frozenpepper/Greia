"""Exact locale-aware number equivalence for speech verification.

Current spellings cover 0..100; historical v1 retains its 0..25 inventory.
There is no fuzzy or substring match. Parakeet requests use a separately
versioned lexical CH/C/K normalization after locale-number parsing; v2 and
historical policies retain their original semantics. Finite English spoken-letter
and name policies remain separately named. Extraction receipts retain their
comparison-policy identity.
"""
from __future__ import annotations
from dataclasses import dataclass
import re
import unicodedata
from functools import lru_cache
from .number_lexicon import cardinal_spellings

LEGACY_COMPARISON_POLICY = "locale-number-tokens-v1"
COMPARISON_POLICY = "locale-number-tokens-v2"
PARAKEET_COMPARISON_POLICY = "locale-number-tokens-v3-chck-orthographic"
ORTHOGRAPHIC_COMPARISON_POLICY = "locale-number-tokens-v2-oskar-en-v1"
ENGLISH_SPOKEN_COMPARISON_POLICY = "locale-number-tokens-v2-spoken-en-v1"
OSKAR_LOCALE_COMPARISON_POLICY = "locale-number-tokens-v2-oskar-all-v1"
SUPPORTED_COMPARISON_POLICIES = frozenset({
    OSKAR_LOCALE_COMPARISON_POLICY, LEGACY_COMPARISON_POLICY, COMPARISON_POLICY,
    PARAKEET_COMPARISON_POLICY, ORTHOGRAPHIC_COMPARISON_POLICY,
    ENGLISH_SPOKEN_COMPARISON_POLICY,
})

# Explicit inventories; tuple position is the value from 0 to 25.
_NUMBER_WORDS = {
    "en": ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "twenty-one", "twenty-two", "twenty-three", "twenty-four", "twenty-five"),
    "it": ("zero", "uno", "due", "tre", "quattro", "cinque", "sei", "sette", "otto", "nove", "dieci", "undici", "dodici", "tredici", "quattordici", "quindici", "sedici", "diciassette", "diciotto", "diciannove", "venti", "ventuno", "ventidue", "ventitré", "ventiquattro", "venticinque"),
    "fr": ("zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf", "vingt", "vingt et un", "vingt-deux", "vingt-trois", "vingt-quatre", "vingt-cinq"),
    "es": ("cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés", "veinticuatro", "veinticinco"),
}

# Hyphens are token separators. Multiword spellings therefore map over token
# sequences, using longest exact phrases before individual number words.
_MULTIWORD = {
    "en": {
        ("twenty", "one"): 21, ("twenty", "two"): 22,
        ("twenty", "three"): 23, ("twenty", "four"): 24,
        ("twenty", "five"): 25,
    },
    "it": {},
    "fr": {
        ("dix", "sept"): 17, ("dix", "huit"): 18, ("dix", "neuf"): 19,
        ("vingt", "et", "un"): 21, ("vingt", "et", "une"): 21,
        ("vingt", "deux"): 22, ("vingt", "trois"): 23,
        ("vingt", "quatre"): 24, ("vingt", "cinq"): 25,
    },
    "es": {},
}
_WORD_OR_DIGIT = re.compile(r"[+−-]?\d+(?:[.,:/]\d+)+|[+−-]\d+|[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)


def _normalize(value: str, ignore_accents: bool) -> str:
    value = unicodedata.normalize("NFC", value).casefold().replace("’", "'")
    if ignore_accents:
        value = "".join(ch for ch in unicodedata.normalize("NFD", value)
                        if unicodedata.category(ch) != "Mn")
    return value


@lru_cache(maxsize=16)
def _locale_data(locale: str, ignore_accents: bool, policy: str) -> tuple[dict[str, int], dict[tuple[str, ...], int]]:
    words = {}
    phrases = {}
    spellings = _NUMBER_WORDS[locale] if policy == LEGACY_COMPARISON_POLICY else cardinal_spellings(locale)
    for number, spelling in enumerate(spellings):
        parts = tuple(_WORD_OR_DIGIT.findall(_normalize(spelling, ignore_accents)))
        if len(parts) == 1:
            words[parts[0]] = number
        else:
            phrases[parts] = number
    for phrase, number in _MULTIWORD[locale].items():
        normalized = tuple(_normalize(part, ignore_accents) for part in phrase)
        phrases[normalized] = number
    return words, phrases


def canonical_number_tokens(locale: str, text: str, *, ignore_accents: bool = True,
                            policy: str = COMPARISON_POLICY) -> tuple[str, ...]:
    """Return exact locale-specific cardinal tokens as ``<num:N>``.

    NFC/casefold is always applied. By default accents are ignored, matching
    the extant comparison policy; pass ``ignore_accents=False`` for strict
    diacritic comparison. Hyphens split lexical tokens, so listed compounds
    and unrelated hyphenated words are both represented as their word parts.
    Apostrophe forms are kept as a single token with a normalized apostrophe.
    Only the Parakeet v3 policy folds lexical ``ch``, ``c`` and ``k`` together,
    after localized cardinals and numeric identities have been recognized.
    """
    if not isinstance(locale, str):
        raise TypeError("locale must be str")
    locale = locale.casefold()
    if locale not in _NUMBER_WORDS:
        raise ValueError(f"unsupported locale: {locale}")
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if not isinstance(ignore_accents, bool):
        raise TypeError("ignore_accents must be bool")
    if policy not in SUPPORTED_COMPARISON_POLICIES:
        raise ValueError("unsupported number comparison policy")

    normalized = _normalize(text, ignore_accents)
    if policy == ENGLISH_SPOKEN_COMPARISON_POLICY and locale == "en":
        # W has a multiword spoken name; these two exact transcriber spellings
        # represent the same letter. Do not normalize its example word.
        normalized = re.sub(r"\bdouble (?:u|you)\b", "w", normalized)
    tokens = [match.group(0) for match in _WORD_OR_DIGIT.finditer(normalized)]
    number_words, phrases = _locale_data(locale, ignore_accents, policy)
    result = []
    index = 0
    ordered_phrases = sorted(phrases.items(), key=lambda item: (-len(item[0]), item[0]))
    while index < len(tokens):
        hit = None
        for phrase, value in ordered_phrases:
            if tuple(tokens[index:index + len(phrase)]) == phrase:
                hit = (len(phrase), value)
                break
        if hit:
            length, value = hit
            result.append(f"<num:{value}>")
            index += length
            continue
        token = tokens[index]
        if (token.isdecimal() and len(token) <= (2 if policy == LEGACY_COMPARISON_POLICY else 32)
                and (policy != LEGACY_COMPARISON_POLICY or int(token) <= 25)
                and len(token) == len(str(int(token)))):
            result.append(f"<num:{int(token)}>")
        elif token in number_words:
            result.append(f"<num:{number_words[token]}>")
        elif policy != LEGACY_COMPARISON_POLICY and any(ch.isdecimal() for ch in token):
            # Codes/signs/decimals stay literal, but changing one must still trip
            # the numeric identity guard even inside a long matching sentence.
            result.append(f"<numeric-literal:{token}>")
        else:
            # Parakeet v3 applies the owner's approved CH/K and C/K
            # interchangeability to lexical tokens only. Rewrite the digraph
            # first; number spellings and numeric identities have already been
            # resolved above and remain exact.
            result.append(token.replace("ch", "k").replace("c", "k")
                          if policy == PARAKEET_COMPARISON_POLICY else token)
        index += 1
    # Explicit English proper-name spelling equivalence. Never apply fuzzy
    # aliases to arbitrary names, and never reinterpret historical v1/v2 receipts.
    if (policy == OSKAR_LOCALE_COMPARISON_POLICY or
            policy in {ORTHOGRAPHIC_COMPARISON_POLICY, ENGLISH_SPOKEN_COMPARISON_POLICY} and locale == "en"):
        result = ["oskar" if token == "oscar" else token for token in result]
    return tuple(result)


def same_number_aware_text(locale: str, left: str, right: str, *, ignore_accents: bool = True) -> bool:
    """Compare lexical sequences after exact number canonicalization."""
    return (canonical_number_tokens(locale, left, ignore_accents=ignore_accents)
            == canonical_number_tokens(locale, right, ignore_accents=ignore_accents))


@dataclass(frozen=True)
class TargetTranscriptComparison:
    """One comparison observation shared by cut selection and delivery screening."""

    score: float
    expected_tokens: tuple[str, ...]
    actual_tokens: tuple[str, ...]

    @property
    def exact_match(self) -> bool:
        return self.expected_tokens == self.actual_tokens

    @property
    def word_count_matches(self) -> bool:
        return len(self.expected_tokens) == len(self.actual_tokens)

    @property
    def numbers_match(self) -> bool:
        return (tuple(t for t in self.expected_tokens if t.startswith(("<num:", "<numeric-literal:")))
                == tuple(t for t in self.actual_tokens if t.startswith(("<num:", "<numeric-literal:"))))

    def flags(self, *, require_word_count: bool = True) -> list[str]:
        result = []
        if not self.numbers_match:
            result.append("TARGET_NUMBER_MISMATCH")
        if require_word_count and not self.word_count_matches:
            result.append("TARGET_WORD_COUNT_MISMATCH")
        return result


def compare_target_transcript(locale: str, expected: str, actual: str, *,
                              ignore_accents: bool = True,
                              policy: str = COMPARISON_POLICY) -> TargetTranscriptComparison:
    """Score number-equivalent text while retaining count and numeric invariants."""
    from .verification import transcript_similarity
    expected_tokens = canonical_number_tokens(locale, expected, ignore_accents=ignore_accents, policy=policy)
    actual_tokens = canonical_number_tokens(locale, actual, ignore_accents=ignore_accents, policy=policy)
    if policy == ENGLISH_SPOKEN_COMPARISON_POLICY and locale.casefold() == "en" and len(expected_tokens) == len(actual_tokens):
        # These exact English homophones cannot be distinguished acoustically.
        # Resolve only corresponding positions; never erase a different number,
        # drop a word, or use arbitrary phonetic/fuzzy name matching.
        groups = (frozenset({"<num:1>", "won"}), frozenset({"<num:2>", "to", "too"}),
                  frozenset({"<num:4>", "for"}), frozenset({"<num:8>", "ate"}))
        actual_tokens = tuple(expected if any(expected in group and actual in group for group in groups) else actual
                              for expected, actual in zip(expected_tokens, actual_tokens))
    def scoring_text(tokens: tuple[str, ...]) -> str:
        if policy == LEGACY_COMPARISON_POLICY:
            return " ".join(tokens)
        # Internal labels must not inflate character similarity: <num:10>
        # would give an unrelated word extra shared characters merely because
        # the same number follows it. Score the human representation instead.
        return " ".join(t[5:-1] if t.startswith("<num:") else
                        t[len("<numeric-literal:"):-1] if t.startswith("<numeric-literal:") else t
                        for t in tokens)
    score = transcript_similarity(scoring_text(expected_tokens), scoring_text(actual_tokens),
                                  ignore_accents=ignore_accents)
    return TargetTranscriptComparison(score, expected_tokens, actual_tokens)
