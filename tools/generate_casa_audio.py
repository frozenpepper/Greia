#!/usr/bin/env python3
"""Prepare La Casa del Dieci guidance as Dani system speech via VoiceEngine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_CLI = PROJECT_ROOT / "tools" / "greia_voice.py"
DEFAULT_REVIEW_DIR = PROJECT_ROOT / "tmp" / "voice-review" / "casa_del_dieci"

PROMPTS_IT = [
    ("prompt_compose_1", "Accendi una luce nella casa!"),
    ("prompt_compose_2", "Accendi 2 luci nella casa!"),
    ("prompt_compose_3", "Accendi 3 luci nella casa!"),
    ("prompt_compose_4", "Accendi 4 luci nella casa!"),
    ("prompt_compose_5", "Accendi 5 luci nella casa!"),
    ("prompt_compose_6", "Accendi 6 luci nella casa!"),
    ("prompt_compose_7", "Accendi 7 luci nella casa!"),
    ("prompt_compose_8", "Accendi 8 luci nella casa!"),
    ("prompt_compose_9", "Accendi 9 luci nella casa!"),
    ("prompt_compose_10", "Accendi tutte le 10 luci nella casa!"),
    ("prompt_add", "Quante luci accese ci sono in tutto?"),
    ("prompt_take_away", "Quante luci restano accese?"),
    ("prompt_missing_part", "Quante luci mancano da accendere?"),
    ("correct_1", "Ben fatto!"), ("correct_2", "Esatto!"), ("correct_3", "Ottimo lavoro!"),
    ("retry_1", "Quasi, riprova!"), ("retry_2", "Conta bene e prova ancora!"),
]

PROMPTS_EN = [
    ("prompt_compose_1", "Turn on 1 light in the house!"),
    ("prompt_compose_2", "Turn on 2 lights in the house!"),
    ("prompt_compose_3", "Turn on 3 lights in the house!"),
    ("prompt_compose_4", "Turn on 4 lights in the house!"),
    ("prompt_compose_5", "Turn on 5 lights in the house!"),
    ("prompt_compose_6", "Turn on 6 lights in the house!"),
    ("prompt_compose_7", "Turn on 7 lights in the house!"),
    ("prompt_compose_8", "Turn on 8 lights in the house!"),
    ("prompt_compose_9", "Turn on 9 lights in the house!"),
    ("prompt_compose_10", "Turn on all 10 lights in the house!"),
    ("prompt_add", "How many lights are on in all?"),
    ("prompt_take_away", "How many lights are left on?"),
    ("prompt_missing_part", "How many lights are missing?"),
    ("correct_1", "Great job!"), ("correct_2", "You got it!"), ("correct_3", "Awesome!"),
    ("retry_1", "Almost, try again!"), ("retry_2", "Count carefully and try again!"),
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
            "cue_id": f"casa_del_dieci.{key}",
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
