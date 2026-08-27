#!/usr/bin/env python3
"""Prepare Foresta delle Parole speech through Greia VoiceEngine.

Letters, words and letter/word association prompts are pronunciation-authoritative
pedagogical speech. Generic praise is Dani system speech. The Activity never chooses
host voices or native-TTS commands directly.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from activities.foresta_parole.main import PHONICS_DATA

VOICE_CLI = PROJECT_ROOT / "tools" / "greia_voice.py"
DEFAULT_REVIEW_DIR = PROJECT_ROOT / "tmp" / "voice-review" / "foresta_parole"

PRAISE = {
    "it": [("ben_fatto", "Ben fatto!"), ("fantastico", "Fantastico!"), ("ottimo", "Ottimo!")],
    "en": [("great_job", "Great job!"), ("wonderful", "Wonderful!"), ("you_did_it", "You did it!")],
}


def _output_path(review_dir: Path, locale: str, filename: str) -> str:
    output = review_dir / locale / filename
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

    requests: list[dict[str, object]] = []
    for locale in ("it", "en"):
        for letter, letter_id, prompt_id, word_display, _emoji, word_stem in PHONICS_DATA[locale]:
            association = f"{letter} come {word_display}" if locale == "it" else f"{letter} as {word_display}"
            for cue_id, text, filename in (
                (prompt_id, association, f"{prompt_id}.wav"),
                (letter_id, letter, f"{letter_id}.wav"),
                (word_stem, word_display, f"{word_stem}.wav"),
            ):
                requests.append(
                    {
                        "speaker": "pedagogical",
                        "kind": "pedagogical_speech",
                        "locale": locale,
                        "text": text,
                        "cue_id": f"foresta_parole.{cue_id}",
                        "output": _output_path(review_dir, locale, filename),
                        "verification": "off",
                        "max_attempts": 1,
                    }
                )
        for cue_id, text in PRAISE[locale]:
            requests.append(
                {
                    "speaker": "dani",
                    "kind": "dani_system_speech",
                    "locale": locale,
                    "text": text,
                    "cue_id": f"foresta_parole.{cue_id}",
                    "output": _output_path(review_dir, locale, f"{cue_id}.wav"),
                    "verification": "off",
                    "max_attempts": 1,
                }
            )

    batch_path = review_dir / "voice_requests.jsonl"
    batch_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in requests), encoding="utf-8"
    )
    result = subprocess.run(
        [sys.executable, str(VOICE_CLI), "batch", "--input", str(batch_path)], cwd=PROJECT_ROOT
    )
    if result.returncode == 0:
        print(f"Generated {len(requests)} review candidates under {review_dir}")
        print("Human listening review is required before Activity integration.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
