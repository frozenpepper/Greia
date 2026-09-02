#!/usr/bin/env python3
"""Generate complete in-game spoken audio according to Greia voice contracts:
- Pedagogical targets (letters, spelling, counting numbers): deterministic system TTS (pedagogical_speech)
- Character dialogue (greetings, instructions, questions, praise): character's voice (character_dialogue / dani_system_speech)
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_CLI = PROJECT_ROOT / "tools" / "greia_voice.py"

GIARDINO_ROOT = PROJECT_ROOT / "activities" / "il_giardino_dei_numeri"
ALFABETO_ROOT = PROJECT_ROOT / "activities" / "alfabeto_leo"

GIARDINO_DANI_SPEECH = {
    "it": [
        ("intro", "Ciao! Tocca e conta con me!"),
        ("prompt", "Tocca e conta!"),
        ("well_done", "Fantastico!"),
        ("praise_1", "Bravissimo!"),
        ("praise_2", "Ben fatto!"),
        ("basket_full", "Che meraviglia, il cesto è pieno!"),
    ],
    "en": [
        ("intro", "Hi! Touch and count with me!"),
        ("prompt", "Touch and count!"),
        ("well_done", "Great job!"),
        ("praise_1", "Awesome!"),
        ("praise_2", "Well done!"),
        ("basket_full", "Wonderful, the basket is full!"),
    ],
}

GIARDINO_COUNTING_TARGETS = {
    "it": [
        ("count_1", "Uno!"),
        ("count_2", "Due!"),
        ("count_3", "Tre!"),
        ("count_4", "Quattro!"),
        ("count_5", "Cinque!"),
    ],
    "en": [
        ("count_1", "One!"),
        ("count_2", "Two!"),
        ("count_3", "Three!"),
        ("count_4", "Four!"),
        ("count_5", "Five!"),
    ],
}

ALFABETO_PHONICS_TARGETS_IT = [
    ("A", "A come Ape"),
    ("B", "B come Barca"),
    ("C", "C come Cane"),
    ("D", "D come Delfino"),
    ("E", "E come Elefante"),
    ("F", "F come Farfalla"),
    ("G", "G come Gatto"),
    ("H", "H come Hotel"),
    ("I", "I come Isola"),
    ("J", "J come Jeep"),
    ("K", "K come Koala"),
    ("L", "L come Luna"),
    ("M", "M come Mela"),
    ("N", "N come Nave"),
    ("O", "O come Orso"),
    ("P", "P come Palla"),
    ("Q", "Q come Quadro"),
    ("R", "R come Rana"),
    ("S", "S come Sole"),
    ("T", "T come Treno"),
    ("U", "U come Uva"),
    ("V", "V come Vulcano"),
    ("W", "W come Wafer"),
    ("X", "X come Xilofono"),
    ("Y", "Y come Yogurt"),
    ("Z", "Z come Zebra"),
]

ALFABETO_PHONICS_TARGETS_EN = [
    ("A", "A is for Apple"),
    ("B", "B is for Boat"),
    ("C", "C is for Cat"),
    ("D", "D is for Duck"),
    ("E", "E is for Elephant"),
    ("F", "F is for Fish"),
    ("G", "G is for Giraffe"),
    ("H", "H is for House"),
    ("I", "I is for Igloo"),
    ("J", "J is for Jellyfish"),
    ("K", "K is for Kite"),
    ("L", "L is for Lion"),
    ("M", "M is for Moon"),
    ("N", "N is for Nest"),
    ("O", "O is for Owl"),
    ("P", "P is for Penguin"),
    ("Q", "Q is for Queen"),
    ("R", "R is for Rainbow"),
    ("S", "S is for Sun"),
    ("T", "T is for Train"),
    ("U", "U is for Umbrella"),
    ("V", "V is for Violin"),
    ("W", "W is for Whale"),
    ("X", "X is for Xylophone"),
    ("Y", "Y is for Yacht"),
    ("Z", "Z is for Zebra"),
]


def generate_giardino_audio() -> int:
    requests = []

    # 1. Pedagogical counting targets (deterministic computer TTS)
    for locale, items in GIARDINO_COUNTING_TARGETS.items():
        loc_dir = GIARDINO_ROOT / "assets" / "audio" / locale
        loc_dir.mkdir(parents=True, exist_ok=True)
        for key, text in items:
            out_file = loc_dir / f"{key}.wav"
            rel_out = str(out_file.relative_to(PROJECT_ROOT))
            requests.append(
                {
                    "speaker": "pedagogical",
                    "kind": "pedagogical_speech",
                    "locale": locale,
                    "text": text,
                    "cue_id": f"il_giardino_dei_numeri.{key}",
                    "output": rel_out,
                    "verification": "off",
                    "max_attempts": 1,
                }
            )

    # 2. Dani character speech (robot instructions and praise)
    for locale, items in GIARDINO_DANI_SPEECH.items():
        loc_dir = GIARDINO_ROOT / "assets" / "audio" / locale
        loc_dir.mkdir(parents=True, exist_ok=True)
        for key, text in items:
            out_file = loc_dir / f"{key}.wav"
            rel_out = str(out_file.relative_to(PROJECT_ROOT))
            requests.append(
                {
                    "speaker": "dani",
                    "kind": "dani_system_speech",
                    "locale": locale,
                    "text": text,
                    "cue_id": f"il_giardino_dei_numeri.{key}",
                    "output": rel_out,
                    "verification": "off",
                    "max_attempts": 1,
                }
            )

    batch_path = PROJECT_ROOT / "tmp" / "voice_requests_giardino.jsonl"
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    batch_path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in requests), encoding="utf-8"
    )
    print(f"Generating {len(requests)} audio clips for Il Giardino dei Numeri...")
    res = subprocess.run([sys.executable, str(VOICE_CLI), "batch", "--input", str(batch_path)], cwd=PROJECT_ROOT)
    return res.returncode


def generate_alfabeto_audio() -> int:
    requests = []

    for locale, phonics_list in [("it", ALFABETO_PHONICS_TARGETS_IT), ("en", ALFABETO_PHONICS_TARGETS_EN)]:
        loc_dir = ALFABETO_ROOT / "assets" / "audio" / locale
        loc_dir.mkdir(parents=True, exist_ok=True)

        # 1. Phonics pronunciation targets (deterministic computer TTS for precise educational reproduction)
        for char, phrase in phonics_list:
            out_file = loc_dir / f"letter_{char}.wav"
            rel_out = str(out_file.relative_to(PROJECT_ROOT))
            requests.append(
                {
                    "speaker": "pedagogical",
                    "kind": "pedagogical_speech",
                    "locale": locale,
                    "text": phrase,
                    "cue_id": f"alfabeto_leo.letter_{char}",
                    "output": rel_out,
                    "verification": "off",
                    "max_attempts": 1,
                }
            )

        # 2. Leo's character dialogue (Chatterbox cloned canonical Leo voice)
        intro_text = (
            "Ciao, sono Leo! Tocca una lettera per scoprire la sorpresa!"
            if locale == "it"
            else "Hi, I'm Leo! Touch a letter to discover a surprise!"
        )
        guess_intro_text = (
            "Indovina la lettera giusta!"
            if locale == "it"
            else "Find the matching letter!"
        )
        well_done_text = "Esatto! Bravissimo!" if locale == "it" else "That's it! Great job!"
        try_again_text = "Quasi! Prova ancora!" if locale == "it" else "Almost! Try again!"

        general_cues = [
            ("intro", intro_text),
            ("mode_guess_intro", guess_intro_text),
            ("well_done", well_done_text),
            ("try_again", try_again_text),
        ]
        for key, text in general_cues:
            out_file = loc_dir / f"{key}.wav"
            rel_out = str(out_file.relative_to(PROJECT_ROOT))
            requests.append(
                {
                    "speaker": "leo",
                    "kind": "character_dialogue",
                    "locale": locale,
                    "text": text,
                    "cue_id": f"alfabeto_leo.{key}",
                    "output": rel_out,
                    "verification": "off",
                    "max_attempts": 1,
                }
            )

        # Spoken question prompts from Leo ("Dov'è la lettera S?" / "Where is the letter S?")
        for char, _ in phonics_list:
            question_text = f"Dov'è la lettera {char}?" if locale == "it" else f"Where is the letter {char}?"
            out_file = loc_dir / f"ask_{char}.wav"
            rel_out = str(out_file.relative_to(PROJECT_ROOT))
            requests.append(
                {
                    "speaker": "leo",
                    "kind": "character_dialogue",
                    "locale": locale,
                    "text": question_text,
                    "cue_id": f"alfabeto_leo.ask_{char}",
                    "output": rel_out,
                    "verification": "off",
                    "max_attempts": 1,
                }
            )

    batch_path = PROJECT_ROOT / "tmp" / "voice_requests_alfabeto.jsonl"
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    batch_path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in requests), encoding="utf-8"
    )
    print(f"Generating {len(requests)} audio clips for L'Alfabeto di Leo...")
    res = subprocess.run([sys.executable, str(VOICE_CLI), "batch", "--input", str(batch_path)], cwd=PROJECT_ROOT)
    return res.returncode


BOSCO_ROOT = PROJECT_ROOT / "activities" / "bosco_numeri"

BOSCO_COUNTING_NUMBERS = {
    "it": [
        ("count_1", "Uno!"),
        ("count_2", "Due!"),
        ("count_3", "Tre!"),
        ("count_4", "Quattro!"),
        ("count_5", "Cinque!"),
        ("count_6", "Sei!"),
        ("count_7", "Sette!"),
        ("count_8", "Otto!"),
        ("count_9", "Nove!"),
        ("count_10", "Dieci!"),
    ],
    "en": [
        ("count_1", "One!"),
        ("count_2", "Two!"),
        ("count_3", "Three!"),
        ("count_4", "Four!"),
        ("count_5", "Five!"),
        ("count_6", "Six!"),
        ("count_7", "Seven!"),
        ("count_8", "Eight!"),
        ("count_9", "Nine!"),
        ("count_10", "Ten!"),
    ],
}

BOSCO_TITO_SPEECH = {
    "it": [
        ("intro", "Ciao, sono Tito! Contiamo insieme fino a dieci nel bosco!"),
        ("mode_count", "Tocca e conta con me!"),
        ("mode_guess", "Indovina il numero giusto!"),
        ("well_done", "Esatto! Bravissimo!"),
        ("try_again", "Quasi! Prova ancora!"),
        ("celebrate", "Fantastico! Li abbiamo contati tutti!"),
    ],
    "en": [
        ("intro", "Hi, I'm Tito! Let's count to ten together in the forest!"),
        ("mode_count", "Touch and count with me!"),
        ("mode_guess", "Find the right number!"),
        ("well_done", "That's it! Great job!"),
        ("try_again", "Almost! Try again!"),
        ("celebrate", "Fantastic! We counted them all!"),
    ],
}


def generate_bosco_audio() -> int:
    requests = []

    for locale in ["it", "en"]:
        loc_dir = BOSCO_ROOT / "assets" / "audio" / locale
        loc_dir.mkdir(parents=True, exist_ok=True)

        # 1. Deterministic pedagogical counting numbers 1 to 10
        for key, text in BOSCO_COUNTING_NUMBERS[locale]:
            out_file = loc_dir / f"{key}.wav"
            rel_out = str(out_file.relative_to(PROJECT_ROOT))
            requests.append(
                {
                    "speaker": "pedagogical",
                    "kind": "pedagogical_speech",
                    "locale": locale,
                    "text": text,
                    "cue_id": f"bosco_numeri.{key}",
                    "output": rel_out,
                    "verification": "off",
                    "max_attempts": 1,
                }
            )

        # 2. Tito character dialogue (greetings, instructions, praise)
        for key, text in BOSCO_TITO_SPEECH[locale]:
            out_file = loc_dir / f"{key}.wav"
            rel_out = str(out_file.relative_to(PROJECT_ROOT))
            requests.append(
                {
                    "speaker": "tito",
                    "kind": "character_dialogue",
                    "locale": locale,
                    "text": text,
                    "cue_id": f"bosco_numeri.{key}",
                    "output": rel_out,
                    "verification": "off",
                    "max_attempts": 1,
                }
            )

        # 3. Tito spoken questions: 'Dov'è il numero N?'
        for n in range(1, 11):
            q_text = f"Dov'è il numero {n}?" if locale == "it" else f"Where is number {n}?"
            out_file = loc_dir / f"ask_{n}.wav"
            rel_out = str(out_file.relative_to(PROJECT_ROOT))
            requests.append(
                {
                    "speaker": "tito",
                    "kind": "character_dialogue",
                    "locale": locale,
                    "text": q_text,
                    "cue_id": f"bosco_numeri.ask_{n}",
                    "output": rel_out,
                    "verification": "off",
                    "max_attempts": 1,
                }
            )

    batch_path = PROJECT_ROOT / "tmp" / "voice_requests_bosco.jsonl"
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    batch_path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in requests), encoding="utf-8"
    )
    print(f"Generating {len(requests)} audio clips for Il Bosco dei Numeri di Tito...")
    res = subprocess.run([sys.executable, str(VOICE_CLI), "batch", "--input", str(batch_path)], cwd=PROJECT_ROOT)
    return res.returncode


def main() -> int:
    # Only generate bosco audio when called directly, or all if requested
    if len(sys.argv) > 1 and sys.argv[1] == "all":
        rc1 = generate_giardino_audio()
        if rc1 != 0:
            return rc1
        rc2 = generate_alfabeto_audio()
        if rc2 != 0:
            return rc2
    return generate_bosco_audio()


if __name__ == "__main__":
    raise SystemExit(main())
