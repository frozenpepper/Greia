#!/usr/bin/env python3
"""Generate in-game spoken audio for Il Giardino dei Numeri and L'Alfabeto di Leo via VoiceEngine."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_CLI = PROJECT_ROOT / "tools" / "greia_voice.py"

GIARDINO_ROOT = PROJECT_ROOT / "activities" / "il_giardino_dei_numeri"
ALFABETO_ROOT = PROJECT_ROOT / "activities" / "alfabeto_leo"

GIARDINO_PROMPTS = {
    "it": [
        ("count_1", "Uno!"),
        ("count_2", "Due!"),
        ("count_3", "Tre!"),
        ("count_4", "Quattro!"),
        ("count_5", "Cinque!"),
        ("prompt", "Tocca e conta!"),
        ("well_done", "Fantastico!"),
        ("basket_full", "Che meraviglia, il cesto è pieno!"),
    ],
    "en": [
        ("count_1", "One!"),
        ("count_2", "Two!"),
        ("count_3", "Three!"),
        ("count_4", "Four!"),
        ("count_5", "Five!"),
        ("prompt", "Touch and count!"),
        ("well_done", "Great job!"),
        ("basket_full", "Wonderful, the basket is full!"),
    ],
}

ALFABETO_PROMPTS_IT = [
    ("letter_A", "A come Ape"),
    ("letter_B", "B come Barca"),
    ("letter_C", "C come Cane"),
    ("letter_D", "D come Delfino"),
    ("letter_E", "E come Elefante"),
    ("letter_F", "F come Farfalla"),
    ("letter_G", "G come Gatto"),
    ("letter_H", "H come Hotel"),
    ("letter_I", "I come Isola"),
    ("letter_J", "J come Jeep"),
    ("letter_K", "K come Koala"),
    ("letter_L", "L come Luna"),
    ("letter_M", "M come Mela"),
    ("letter_N", "N come Nave"),
    ("letter_O", "O come Orso"),
    ("letter_P", "P come Palla"),
    ("letter_Q", "Q come Quadro"),
    ("letter_R", "R come Rana"),
    ("letter_S", "S come Sole"),
    ("letter_T", "T come Treno"),
    ("letter_U", "U come Uva"),
    ("letter_V", "V come Vulcano"),
    ("letter_W", "W come Wafer"),
    ("letter_X", "X come Xilofono"),
    ("letter_Y", "Y come Yogurt"),
    ("letter_Z", "Z come Zebra"),
    ("well_done", "Ben fatto!"),
    ("try_again", "Prova ancora!"),
    ("guess_prompt", "Dov'è la lettera giusta?"),
]

ALFABETO_PROMPTS_EN = [
    ("letter_A", "A is for Apple"),
    ("letter_B", "B is for Boat"),
    ("letter_C", "C is for Cat"),
    ("letter_D", "D is for Duck"),
    ("letter_E", "E is for Elephant"),
    ("letter_F", "F is for Fish"),
    ("letter_G", "G is for Giraffe"),
    ("letter_H", "H is for House"),
    ("letter_I", "I is for Igloo"),
    ("letter_J", "J is for Jellyfish"),
    ("letter_K", "K is for Kite"),
    ("letter_L", "L is for Lion"),
    ("letter_M", "M is for Moon"),
    ("letter_N", "N is for Nest"),
    ("letter_O", "O is for Owl"),
    ("letter_P", "P is for Penguin"),
    ("letter_Q", "Q is for Queen"),
    ("letter_R", "R is for Rainbow"),
    ("letter_S", "S is for Sun"),
    ("letter_T", "T is for Train"),
    ("letter_U", "U is for Umbrella"),
    ("letter_V", "V is for Violin"),
    ("letter_W", "W is for Whale"),
    ("letter_X", "X is for Xylophone"),
    ("letter_Y", "Y is for Yacht"),
    ("letter_Z", "Z is for Zebra"),
    ("well_done", "Well done!"),
    ("try_again", "Try again!"),
    ("guess_prompt", "Find the matching letter!"),
]


def generate_giardino_audio() -> int:
    requests = []
    for locale, items in GIARDINO_PROMPTS.items():
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
    prompts = {"it": ALFABETO_PROMPTS_IT, "en": ALFABETO_PROMPTS_EN}
    requests = []
    for locale, items in prompts.items():
        loc_dir = ALFABETO_ROOT / "assets" / "audio" / locale
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
                    "cue_id": f"alfabeto_leo.{key}",
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


def main() -> int:
    rc1 = generate_giardino_audio()
    if rc1 != 0:
        return rc1
    rc2 = generate_alfabeto_audio()
    return rc2


if __name__ == "__main__":
    raise SystemExit(main())
