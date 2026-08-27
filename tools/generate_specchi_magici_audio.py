#!/usr/bin/env python3
"""Prepare Specchi Magici Lilli speech through Greia VoiceEngine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_CLI = PROJECT_ROOT / "tools" / "greia_voice.py"
DEFAULT_REVIEW_DIR = PROJECT_ROOT / "tmp" / "voice-review" / "specchi_magici"

PROMPTS_IT = [
    ("welcome", "Ciao! Guarda lo specchio magico e posiziona le forme uguali dall altra parte!"),
    ("prompt_place", "Rifletti le forme sullo specchio magico!"),
    ("correct_1", "Ottimo lavoro!"),
    ("correct_2", "Ben fatto!"),
    ("correct_3", "Esatto!"),
    ("correct_4", "Fantastico!"),
    ("correct_5", "Evviva!"),
    ("retry_1", "Quasi! Guarda bene la distanza dallo specchio!"),
    ("retry_2", "Riprova, sei quasi riuscito!"),
    ("mosaic_complete", "Che bello specchio! Ecco il prossimo mosaico!"),
    ("shape_circle", "Cerchio!"),
    ("shape_square", "Quadrato!"),
    ("shape_triangle", "Triangolo!"),
    ("shape_semicircle", "Semicerchio!"),
]

PROMPTS_EN = [
    ("welcome", "Hello! Look in the magic mirror and place the matching shapes on the other side!"),
    ("prompt_place", "Mirror the shapes across the magic line!"),
    ("correct_1", "Great job!"),
    ("correct_2", "Well done!"),
    ("correct_3", "Exactly right!"),
    ("correct_4", "Awesome!"),
    ("correct_5", "Hooray!"),
    ("retry_1", "Almost! Look closely at the distance from the mirror!"),
    ("retry_2", "Try again, you are so close!"),
    ("mosaic_complete", "Beautiful mirror! Here is the next mosaic!"),
    ("shape_circle", "Circle!"),
    ("shape_square", "Square!"),
    ("shape_triangle", "Triangle!"),
    ("shape_semicircle", "Semicircle!"),
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
            "speaker": "lilli",
            "kind": "character_dialogue",
            "locale": locale,
            "text": text,
            "cue_id": f"specchi_magici.{key}",
            "output": _output_path(review_dir, locale, key),
            "verification": "auto",
            "max_attempts": 2,
        }
        for locale, items in prompts.items()
        for key, text in items
    ]
    batch_path = review_dir / "voice_requests.jsonl"
    batch_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in requests),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(VOICE_CLI), "batch", "--input", str(batch_path)],
        cwd=PROJECT_ROOT,
    )
    if result.returncode == 0:
        print(f"Generated {len(requests)} Lilli review candidates under {review_dir}")
        print("Human listening review is required before Activity integration.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
