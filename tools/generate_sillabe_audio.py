#!/usr/bin/env python3
"""Audio generator for Sillabe Magiche (Magic Syllables).

Generates crystal-clear 22050Hz LEI16 mono WAV audio assets for:
- All Italian and English consonant-vowel (CV) syllables
- Syllable listening challenge prompts ("Trova ba", "Find ba")
- 2-Syllable words and their component syllables
- Cheerful child praise and encouragement

CRITICAL RULES:
1. Always pass lowercase strings to TTS so macOS `say` never pronounces 'maiuscola' or 'capital'.
2. Use toddler-friendly speech rate: ~175 wpm for Italian (Alice), ~180 wpm for English (Samantha).
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIO_ROOT = PROJECT_ROOT / "activities" / "sillabe_magiche" / "assets" / "audio"

CONSONANTS_IT = ["B", "C", "D", "F", "G", "L", "M", "N", "P", "R", "S", "T", "V", "Z"]
VOWELS_IT = ["A", "E", "I", "O", "U"]

WORDS_DATA_IT = [
    ("CASA", ("CA", "SA"), "🏠", "casa"),
    ("SOLE", ("SO", "LE"), "☀️", "sole"),
    ("LUNA", ("LU", "NA"), "🌙", "luna"),
    ("MELA", ("ME", "LA"), "🍎", "mela"),
    ("RANA", ("RA", "NA"), "🐸", "rana"),
    ("TOPO", ("TO", "PO"), "🐭", "topo"),
    ("MANO", ("MA", "NO"), "🖐️", "mano"),
    ("PANE", ("PA", "NE"), "🥖", "pane"),
    ("NAVE", ("NA", "VE"), "🚢", "nave"),
    ("VASO", ("VA", "SO"), "🏺", "vaso"),
    ("PERA", ("PE", "RA"), "🍐", "pera"),
    ("MURO", ("MU", "RO"), "🧱", "muro"),
    ("LUPO", ("LU", "PO"), "🐺", "lupo"),
    ("FILO", ("FI", "LO"), "🧵", "filo"),
    ("ROSA", ("RO", "SA"), "🌹", "rosa"),
    ("FARO", ("FA", "RO"), "🗼", "faro"),
    ("GUFO", ("GU", "FO"), "🦉", "gufo"),
    ("MOTO", ("MO", "TO"), "🏍️", "moto"),
    ("LAMA", ("LA", "MA"), "🦙", "lama"),
    ("PINO", ("PI", "NO"), "🌲", "pino"),
    ("RETE", ("RE", "TE"), "🥅", "rete"),
    ("SUCO", ("SU", "CO"), "🧃", "suco"),
    ("VELA", ("VE", "LA"), "⛵", "vela"),
    ("DADO", ("DA", "DO"), "🎲", "dado"),
    ("FATA", ("FA", "TA"), "🧚", "fata"),
    ("CANE", ("CA", "NE"), "🐶", "cane"),
    ("PIZZA", ("PI", "ZZA"), "🍕", "pizza"),
]

WORDS_DATA_EN = [
    ("BABY", ("BA", "BY"), "👶", "baby"),
    ("TIGER", ("TI", "GER"), "🐯", "tiger"),
    ("ROBOT", ("RO", "BOT"), "🤖", "robot"),
    ("LEMON", ("LE", "MON"), "🍋", "lemon"),
    ("PAPER", ("PA", "PER"), "📄", "paper"),
    ("WATER", ("WA", "TER"), "💧", "water"),
    ("MUSIC", ("MU", "SIC"), "🎵", "music"),
    ("RABBIT", ("RAB", "BIT"), "🐰", "rabbit"),
    ("PIZZA", ("PIZ", "ZA"), "🍕", "pizza"),
    ("ZEBRA", ("ZE", "BRA"), "🦓", "zebra"),
    ("PANDA", ("PAN", "DA"), "🐼", "panda"),
    ("ROCKET", ("ROCK", "ET"), "🚀", "rocket"),
    ("SUNNY", ("SUN", "NY"), "☀️", "sunny"),
]

PRAISES_IT = [
    ("esatto", "esatto"),
    ("fantastico", "fantastico"),
    ("super", "super"),
    ("magnifico", "magnifico"),
    ("ottimo", "ottimo lavoro"),
    ("ben_fatto", "ben fatto"),
    ("parola_composta", "hai composto la parola"),
]

PRAISES_EN = [
    ("great_job", "great job"),
    ("wonderful", "wonderful"),
    ("you_did_it", "you did it"),
    ("fantastic", "fantastic"),
    ("super", "super"),
    ("well_done", "well done"),
    ("word_complete", "you made the word"),
]


def make_wav(text: str, voice: str, rate: int, dest_wav: Path) -> None:
    lower_text = text.lower()
    for attempt in range(3):
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp_file:
            tmp_aiff = Path(tmp_file.name)
        try:
            subprocess.run(["say", "-v", voice, "-r", str(rate), lower_text, "-o", str(tmp_aiff)], check=True)
            subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@22050", "-c", "1", str(tmp_aiff), str(dest_wav)], check=True)
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(0.1)
        finally:
            if tmp_aiff.exists():
                tmp_aiff.unlink()


PHONETIC_OVERRIDE_IT = {
    "to": "tò",
    "do": "dò",
    "no": "nò",
    "so": "sò",
    "po": "pò",
    "bo": "bò",
    "co": "cò",
    "fo": "fò",
    "go": "gò",
    "lo": "lò",
    "mo": "mò",
    "ro": "rò",
    "vo": "vò",
    "zo": "zò",
    "be": "bè",
    "de": "dè",
    "fe": "fè",
    "ge": "gè",
    "le": "lè",
    "me": "mè",
    "ne": "nè",
    "pe": "pè",
    "re": "rè",
    "se": "sè",
    "te": "tè",
    "ve": "vè",
    "ze": "zè",
}


def generate_italian() -> None:
    it_dir = AUDIO_ROOT / "it"
    it_dir.mkdir(parents=True, exist_ok=True)
    voice = "Alice"
    rate = 175

    print(f"Generating Italian audio in {it_dir}...")

    # 1. Single Consonants and Vowels
    for c in CONSONANTS_IT:
        make_wav(c, voice, rate, it_dir / f"letter_{c.lower()}.wav")
    for v in VOWELS_IT:
        make_wav(v, voice, rate, it_dir / f"vowel_{v.lower()}.wav")

    # 2. All Consonant+Vowel Syllables and "Trova..." prompts
    for c in CONSONANTS_IT:
        for v in VOWELS_IT:
            syl = f"{c}{v}".lower()
            spoken_syl = PHONETIC_OVERRIDE_IT.get(syl, syl)
            make_wav(spoken_syl, voice, rate, it_dir / f"syl_{syl}.wav")
            make_wav(f"trova {spoken_syl}", voice, rate, it_dir / f"find_{syl}.wav")

    # 3. Special syllables needed for words (like 'zza', 'ne', etc. if not standard)
    extra_sylls = {"zza", "ne", "re", "te", "co", "do", "ta"}
    for es in extra_sylls:
        dest = it_dir / f"syl_{es}.wav"
        spoken_es = PHONETIC_OVERRIDE_IT.get(es, es)
        make_wav(spoken_es, voice, rate, dest)
        make_wav(f"trova {spoken_es}", voice, rate, it_dir / f"find_{es}.wav")

    # 4. Words
    for word_display, (s1, s2), emoji, stem in WORDS_DATA_IT:
        make_wav(stem, voice, rate, it_dir / f"word_{stem}.wav")
        for s in (s1, s2):
            syl_path = it_dir / f"syl_{s.lower()}.wav"
            if not syl_path.exists():
                make_wav(s.lower(), voice, rate, syl_path)

    # 5. Praises & UI prompts
    for key, phrase in PRAISES_IT:
        make_wav(phrase, voice, rate, it_dir / f"{key}.wav")

    make_wav("ascolta e tocca la sillaba", voice, rate, it_dir / "instruction_catch.wav")
    make_wav("componi la parola", voice, rate, it_dir / "instruction_build.wav")
    make_wav("tocca una consonante", voice, rate, it_dir / "instruction_explore.wav")


def generate_english() -> None:
    en_dir = AUDIO_ROOT / "en"
    en_dir.mkdir(parents=True, exist_ok=True)
    voice = "Samantha"
    rate = 180

    print(f"Generating English audio in {en_dir}...")

    # 1. Consonant+Vowel Syllables
    for c in ["B", "C", "D", "F", "G", "L", "M", "N", "P", "R", "S", "T", "V", "W", "Z"]:
        for v in ["A", "E", "I", "O", "U"]:
            syl = f"{c}{v}".lower()
            make_wav(syl, voice, rate, en_dir / f"syl_{syl}.wav")
            make_wav(f"find {syl}", voice, rate, en_dir / f"find_{syl}.wav")

    # 2. English Words & component syllables
    for word_display, (s1, s2), emoji, stem in WORDS_DATA_EN:
        make_wav(stem, voice, rate, en_dir / f"word_{stem}.wav")
        for s in (s1, s2):
            s_low = s.lower()
            dest = en_dir / f"syl_{s_low}.wav"
            if not dest.exists():
                make_wav(s_low, voice, rate, dest)
                make_wav(f"find {s_low}", voice, rate, en_dir / f"find_{s_low}.wav")

    # 3. Praises & Instructions
    for key, phrase in PRAISES_EN:
        make_wav(phrase, voice, rate, en_dir / f"{key}.wav")

    make_wav("listen and find the syllable", voice, rate, en_dir / "instruction_catch.wav")
    make_wav("build the word", voice, rate, en_dir / "instruction_build.wav")
    make_wav("tap a consonant", voice, rate, en_dir / "instruction_explore.wav")


def generate_all() -> None:
    generate_italian()
    generate_english()
    print("All Sillabe Magiche audio assets successfully generated!")


if __name__ == "__main__":
    generate_all()
