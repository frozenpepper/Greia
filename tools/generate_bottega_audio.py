#!/usr/bin/env python3
"""Prepare La Bottega delle Misure guidance as Dani system speech.

These lines are ordinary Activity guidance/reinforcement, not pronunciation-authoritative
pedagogical targets. The Activity therefore names Dani explicitly and delegates native
TTS selection/rates/conversion to Greia VoiceEngine. Existing packaged audio is left
untouched; generated takes go to review and require human acceptance before integration.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_CLI = PROJECT_ROOT / "tools" / "greia_voice.py"
DEFAULT_REVIEW_DIR = PROJECT_ROOT / "tmp" / "voice-review" / "bottega_delle_misure"

PROMPTS_IT = [
    ("prompt_compare_longer", "Tocca il pacco più lungo!"),
    ("prompt_compare_shorter", "Tocca il pacco più corto!"),
    ("prompt_compare_taller", "Tocca il pacco più alto!"),
    ("prompt_compare_shorter_h", "Tocca il pacco più basso!"),
    ("prompt_order_length", "Metti i pacchi in ordine, dal più corto al più lungo!"),
    ("prompt_order_height", "Metti i pacchi in ordine, dal più basso al più alto!"),
    ("prompt_measure", "Conta quanti blocchi è lungo il pacco e tocca il numero!"),
    ("prompt_shelf", "Quale pacco entra nello scaffale?"),
    ("correct_1", "Ben fatto!"), ("correct_2", "Esatto!"), ("correct_3", "Ottimo lavoro!"),
    ("retry_1", "Riprova!"), ("retry_2", "Quasi, prova ancora!"),
]

PROMPTS_EN = [
    ("prompt_compare_longer", "Tap the longer parcel!"),
    ("prompt_compare_shorter", "Tap the shorter parcel!"),
    ("prompt_compare_taller", "Tap the taller parcel!"),
    ("prompt_compare_shorter_h", "Tap the shorter parcel!"),
    ("prompt_order_length", "Put the parcels in order, from shortest to longest!"),
    ("prompt_order_height", "Put the parcels in order, from shortest to tallest!"),
    ("prompt_measure", "Count how many blocks long the parcel is and tap the number!"),
    ("prompt_shelf", "Which parcel fits in the shelf?"),
    ("correct_1", "Great job!"), ("correct_2", "You got it!"), ("correct_3", "Awesome!"),
    ("retry_1", "Try again!"), ("retry_2", "Almost, try again!"),
]


def _output_path(review_dir: Path, locale: str, key: str) -> str:
    output = review_dir / locale / f"{key}.wav"
    try:
        return str(output.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(output.resolve())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-dir", type=Path, default=DEFAULT_REVIEW_DIR)
    args = parser.parse_args()
    review_dir = args.review_dir.resolve()
    review_dir.mkdir(parents=True, exist_ok=True)
    prompts = {"it": PROMPTS_IT, "en": PROMPTS_EN}
    requests = [
        {
            "speaker": "dani",
            "kind": "dani_system_speech",
            "locale": locale,
            "text": text,
            "cue_id": f"bottega_delle_misure.{key}",
            "output": _output_path(review_dir, locale, key),
            "verification": "off",
            "max_attempts": 1,
        }
        for locale, items in prompts.items()
        for key, text in items
    ]
    batch_path = review_dir / "voice_requests.jsonl"
    batch_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in requests), encoding="utf-8"
    )
    result = subprocess.run(
        [sys.executable, str(VOICE_CLI), "batch", "--input", str(batch_path)], cwd=PROJECT_ROOT
    )
    if result.returncode == 0:
        print(f"Generated {len(requests)} Dani review candidates under {review_dir}")
        print("Human listening review is required before Activity integration.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
