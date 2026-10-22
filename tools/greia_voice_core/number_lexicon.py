"""Bounded cardinal spellings for EN/IT/FR/ES speech comparison (0..100).

This is lexical normalization, not fuzzy pronunciation correction. Space and
hyphen variants are handled by the caller's tokenizer. No runtime dependency,
network lookup or unbounded inverse-number search is needed.
"""
from functools import lru_cache


@lru_cache(maxsize=4)
def cardinal_spellings(locale: str) -> tuple[str, ...]:
    """Return one explicit standard cardinal form per value, indexed 0..100."""
    small = {
        "en": "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen",
        "it": "zero uno due tre quattro cinque sei sette otto nove dieci undici dodici tredici quattordici quindici sedici diciassette diciotto diciannove",
        "fr": "zéro un deux trois quatre cinq six sept huit neuf dix onze douze treize quatorze quinze seize dix-sept dix-huit dix-neuf",
        "es": "cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciséis diecisiete dieciocho diecinueve",
    }[locale].split()
    tens = {
        "en": ("twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"),
        "it": ("venti", "trenta", "quaranta", "cinquanta", "sessanta", "settanta", "ottanta", "novanta"),
        "fr": ("vingt", "trente", "quarante", "cinquante", "soixante"),
        "es": ("veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"),
    }[locale]
    result = list(small)
    for value in range(20, 100):
        unit = value % 10
        if locale == "fr" and value >= 70:
            if value < 80:
                tail = small[value - 60]
                spelling = "soixante" + (" et " if value == 71 else "-") + tail
            elif value == 80:
                spelling = "quatre-vingts"
            else:
                spelling = "quatre-vingt-" + small[value - 80]
        else:
            ten = tens[value // 10 - 2]
            if not unit:
                spelling = ten
            elif locale == "en":
                spelling = ten + "-" + small[unit]
            elif locale == "it":
                # Standard vowel elision before uno/otto; compounds ending in
                # tre carry their written accent (ventitré, trentatré, ...).
                spelling = (ten[:-1] if unit in (1, 8) else ten) + ("tré" if unit == 3 else small[unit])
            elif locale == "fr":
                spelling = ten + (" et " if unit == 1 else "-") + small[unit]
            elif value < 30:
                spelling = {21: "veintiuno", 22: "veintidós", 23: "veintitrés", 24: "veinticuatro", 25: "veinticinco", 26: "veintiséis", 27: "veintisiete", 28: "veintiocho", 29: "veintinueve"}[value]
            else:
                spelling = ten + " y " + small[unit]
        result.append(spelling)
    result.append({"en": "one hundred", "it": "cento", "fr": "cent", "es": "cien"}[locale])
    return tuple(result)
