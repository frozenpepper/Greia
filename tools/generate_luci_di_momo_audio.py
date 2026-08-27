#!/usr/bin/env python3
"""Prepare Luci di Momo character speech through Greia VoiceEngine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_CLI = PROJECT_ROOT / "tools" / "greia_voice.py"
DEFAULT_REVIEW_DIR = PROJECT_ROOT / "tmp" / "voice-review" / "luci_di_momo"

PROMPTS_IT = [
    ("welcome", "Ciao! Guarda bene quante lucciole brillano nella notte, poi tocca il numero giusto!"),
    ("prompt_ready", "Tocca il grande pulsante quando sei pronto per far brillare le lucciole!"),
    ("prompt_choose", "Quante lucciole hai visto?"),
    ("correct_1", "Ottimo lavoro!"),
    ("correct_2", "Ben fatto!"),
    ("correct_3", "Esatto!"),
    ("correct_4", "Fantastico!"),
    ("correct_5", "Evviva!"),
    ("retry_1", "Quasi! Guarda di nuovo quante lucciole brillano!"),
    ("retry_2", "Riprova, guarda bene le lucine!"),
    ("count_1", "Una lucciola!"),
    ("count_2", "Due lucciole!"),
    ("count_3", "Tre lucciole!"),
    ("count_4", "Quattro lucciole!"),
    ("count_5", "Cinque lucciole!"),
    ("garden_complete", "Che meraviglia! Tutte le lucciole sono felici e illuminate!"),
]

PROMPTS_EN = [
    ("welcome", "Hello! Look closely at how many fireflies glow in the night, then tap the right number!"),
    ("prompt_ready", "Tap the big play button when you are ready to see the fireflies glow!"),
    ("prompt_choose", "How many fireflies did you see?"),
    ("correct_1", "Great job!"),
    ("correct_2", "Well done!"),
    ("correct_3", "Exactly right!"),
    ("correct_4", "Awesome!"),
    ("correct_5", "Hooray!"),
    ("retry_1", "Almost! Look again at how many fireflies glow!"),
    ("retry_2", "Try again, look closely at the little lights!"),
    ("count_1", "One firefly!"),
    ("count_2", "Two fireflies!"),
    ("count_3", "Three fireflies!"),
    ("count_4", "Four fireflies!"),
    ("count_5", "Five fireflies!"),
    ("garden_complete", "Wonderful! All the fireflies are shining bright and happy!"),
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
            "speaker": "momo",
            "kind": "character_dialogue",
            "locale": locale,
            "text": text,
            "cue_id": f"luci_di_momo.{key}",
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
        print(f"Generated {len(requests)} Momo review candidates under {review_dir}")
        print("Human listening review is required before Activity integration.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
