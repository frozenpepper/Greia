#!/usr/bin/env python3
"""Prepare Sillabe Magiche speech through Greia VoiceEngine.

Letters, syllables, target-bearing "find" prompts, words and word components use
``pedagogical_speech`` because exact pronunciation is educational truth. Generic
instructions and praise are Dani system speech. macOS voice names, lowercasing and
Italian pronunciation overrides are owned by the VoiceEngine provider, not this Activity.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_CLI = PROJECT_ROOT / "tools" / "greia_voice.py"
DEFAULT_REVIEW_DIR = PROJECT_ROOT / "tmp" / "voice-review" / "sillabe_magiche"

CONSONANTS_IT = ["B", "C", "D", "F", "G", "L", "M", "N", "P", "R", "S", "T", "V", "Z"]
VOWELS_IT = ["A", "E", "I", "O", "U"]

WORDS_DATA_IT = [
    ("CASA", ("CA", "SA"), "casa"), ("SOLE", ("SO", "LE"), "sole"),
    ("LUNA", ("LU", "NA"), "luna"), ("MELA", ("ME", "LA"), "mela"),
    ("RANA", ("RA", "NA"), "rana"), ("TOPO", ("TO", "PO"), "topo"),
    ("MANO", ("MA", "NO"), "mano"), ("PANE", ("PA", "NE"), "pane"),
    ("NAVE", ("NA", "VE"), "nave"), ("VASO", ("VA", "SO"), "vaso"),
    ("PERA", ("PE", "RA"), "pera"), ("MURO", ("MU", "RO"), "muro"),
    ("LUPO", ("LU", "PO"), "lupo"), ("FILO", ("FI", "LO"), "filo"),
    ("ROSA", ("RO", "SA"), "rosa"), ("FARO", ("FA", "RO"), "faro"),
    ("GUFO", ("GU", "FO"), "gufo"), ("MOTO", ("MO", "TO"), "moto"),
    ("LAMA", ("LA", "MA"), "lama"), ("PINO", ("PI", "NO"), "pino"),
    ("RETE", ("RE", "TE"), "rete"), ("SUCO", ("SU", "CO"), "suco"),
    ("VELA", ("VE", "LA"), "vela"), ("DADO", ("DA", "DO"), "dado"),
    ("FATA", ("FA", "TA"), "fata"), ("CANE", ("CA", "NE"), "cane"),
    ("PIZZA", ("PI", "ZZA"), "pizza"),
]

WORDS_DATA_EN = [
    ("BABY", ("BA", "BY"), "baby"), ("TIGER", ("TI", "GER"), "tiger"),
    ("ROBOT", ("RO", "BOT"), "robot"), ("LEMON", ("LE", "MON"), "lemon"),
    ("PAPER", ("PA", "PER"), "paper"), ("WATER", ("WA", "TER"), "water"),
    ("MUSIC", ("MU", "SIC"), "music"), ("RABBIT", ("RAB", "BIT"), "rabbit"),
    ("PIZZA", ("PIZ", "ZA"), "pizza"), ("ZEBRA", ("ZE", "BRA"), "zebra"),
    ("PANDA", ("PAN", "DA"), "panda"), ("ROCKET", ("ROCK", "ET"), "rocket"),
    ("SUNNY", ("SUN", "NY"), "sunny"),
]

PRAISES_IT = [
    ("esatto", "esatto"), ("fantastico", "fantastico"), ("super", "super"),
    ("magnifico", "magnifico"), ("ottimo", "ottimo lavoro"), ("ben_fatto", "ben fatto"),
    ("parola_composta", "hai composto la parola"),
]
PRAISES_EN = [
    ("great_job", "great job"), ("wonderful", "wonderful"), ("you_did_it", "you did it"),
    ("fantastic", "fantastic"), ("super", "super"), ("well_done", "well done"),
    ("word_complete", "you made the word"),
]
INSTRUCTIONS = {
    "it": [
        ("instruction_catch", "ascolta e tocca la sillaba"),
        ("instruction_build", "componi la parola"),
        ("instruction_explore", "tocca una consonante"),
    ],
    "en": [
        ("instruction_catch", "listen and find the syllable"),
        ("instruction_build", "build the word"),
        ("instruction_explore", "tap a consonant"),
    ],
}


def _output_path(review_dir: Path, locale: str, filename: str) -> str:
    output = review_dir / locale / filename
    try:
        return str(output.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(output.resolve())


def _request(review_dir: Path, locale: str, cue_id: str, text: str, *, pedagogical: bool) -> dict[str, object]:
    return {
        "speaker": "pedagogical" if pedagogical else "dani",
        "kind": "pedagogical_speech" if pedagogical else "dani_system_speech",
        "locale": locale,
        "text": text,
        "cue_id": f"sillabe_magiche.{cue_id}",
        "output": _output_path(review_dir, locale, f"{cue_id}.wav"),
        "verification": "off",
        "max_attempts": 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-dir", type=Path, default=DEFAULT_REVIEW_DIR)
    args = parser.parse_args()
    review_dir = args.review_dir.resolve()
    review_dir.mkdir(parents=True, exist_ok=True)

    requests: dict[tuple[str, str], dict[str, object]] = {}

    def add(locale: str, cue_id: str, text: str, *, pedagogical: bool) -> None:
        requests[(locale, cue_id)] = _request(review_dir, locale, cue_id, text, pedagogical=pedagogical)

    for c in CONSONANTS_IT:
        add("it", f"letter_{c.lower()}", c, pedagogical=True)
    for v in VOWELS_IT:
        add("it", f"vowel_{v.lower()}", v, pedagogical=True)
    for c in CONSONANTS_IT:
        for v in VOWELS_IT:
            syllable = f"{c}{v}".lower()
            add("it", f"syl_{syllable}", syllable, pedagogical=True)
            add("it", f"find_{syllable}", f"trova {syllable}", pedagogical=True)
    for syllable in {"zza", "ne", "re", "te", "co", "do", "ta"}:
        add("it", f"syl_{syllable}", syllable, pedagogical=True)
        add("it", f"find_{syllable}", f"trova {syllable}", pedagogical=True)
    for _display, components, stem in WORDS_DATA_IT:
        add("it", f"word_{stem}", stem, pedagogical=True)
        for component in components:
            syllable = component.lower()
            add("it", f"syl_{syllable}", syllable, pedagogical=True)
    for cue_id, text in PRAISES_IT:
        add("it", cue_id, text, pedagogical=False)
    for cue_id, text in INSTRUCTIONS["it"]:
        add("it", cue_id, text, pedagogical=False)

    for c in ["B", "C", "D", "F", "G", "L", "M", "N", "P", "R", "S", "T", "V", "W", "Z"]:
        for v in ["A", "E", "I", "O", "U"]:
            syllable = f"{c}{v}".lower()
            add("en", f"syl_{syllable}", syllable, pedagogical=True)
            add("en", f"find_{syllable}", f"find {syllable}", pedagogical=True)
    for _display, components, stem in WORDS_DATA_EN:
        add("en", f"word_{stem}", stem, pedagogical=True)
        for component in components:
            syllable = component.lower()
            add("en", f"syl_{syllable}", syllable, pedagogical=True)
            add("en", f"find_{syllable}", f"find {syllable}", pedagogical=True)
    for cue_id, text in PRAISES_EN:
        add("en", cue_id, text, pedagogical=False)
    for cue_id, text in INSTRUCTIONS["en"]:
        add("en", cue_id, text, pedagogical=False)

    rows = list(requests.values())
    batch_path = review_dir / "voice_requests.jsonl"
    batch_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    result = subprocess.run(
        [sys.executable, str(VOICE_CLI), "batch", "--input", str(batch_path)], cwd=PROJECT_ROOT
    )
    if result.returncode == 0:
        print(f"Generated {len(rows)} review candidates under {review_dir}")
        print("Human listening review is required before Activity integration.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
