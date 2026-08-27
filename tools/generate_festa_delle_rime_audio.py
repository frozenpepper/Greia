#!/usr/bin/env python3
"""Prepare Festa delle Rime speech through Greia VoiceEngine.

Rhyme/alliteration words are pronunciation-authoritative pedagogical speech. Generic
instructions are Dani system speech. No Activity code chooses native voices, commands,
conversion tools or silent fallbacks.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_CLI = PROJECT_ROOT / "tools" / "greia_voice.py"
DEFAULT_REVIEW_DIR = PROJECT_ROOT / "tmp" / "voice-review" / "festa_delle_rime"

WORDS_IT = [
    ("cane", "cane"), ("pane", "pane"), ("gatto", "gatto"), ("piatto", "piatto"),
    ("rana", "rana"), ("lana", "lana"), ("mela", "mela"), ("vela", "vela"),
    ("fiore", "fiore"), ("cuore", "cuore"), ("palla", "palla"), ("farfalla", "farfalla"),
    ("torta", "torta"), ("porta", "porta"), ("naso", "naso"), ("vaso", "vaso"),
    ("mare", "mare"), ("mano", "mano"), ("pera", "pera"), ("luna", "luna"),
    ("luce", "luce"), ("fata", "fata"), ("foglia", "foglia"), ("topo", "topo"),
    ("tenda", "tenda"), ("sole", "sole"), ("sasso", "sasso"), ("sedia", "sedia"),
]
PROMPTS_IT = [
    ("prompt_rhyme", "ascolta la parola e trova la rima"),
    ("prompt_odd", "trova la parola che non fa rima"),
    ("prompt_sound", "trova la parola con lo stesso suono iniziale"),
]
WORDS_EN = [
    ("cat", "cat"), ("hat", "hat"), ("moon", "moon"), ("spoon", "spoon"),
    ("cake", "cake"), ("snake", "snake"), ("log", "log"), ("frog", "frog"),
    ("bear", "bear"), ("chair", "chair"), ("boat", "boat"), ("goat", "goat"),
    ("star", "star"), ("car", "car"), ("mouse", "mouse"), ("house", "house"),
    ("map", "map"), ("pig", "pig"), ("pan", "pan"), ("pear", "pear"),
    ("leaf", "leaf"), ("lamp", "lamp"), ("fish", "fish"), ("fan", "fan"),
    ("fox", "fox"), ("top", "top"), ("tent", "tent"), ("turtle", "turtle"),
    ("sun", "sun"), ("sock", "sock"),
]
PROMPTS_EN = [
    ("prompt_rhyme", "listen to the word and find the rhyme"),
    ("prompt_odd", "find the word that does not rhyme"),
    ("prompt_sound", "find the word with the same beginning sound"),
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

    requests: list[dict[str, object]] = []
    for locale, words, prompts in (
        ("it", WORDS_IT, PROMPTS_IT),
        ("en", WORDS_EN, PROMPTS_EN),
    ):
        for cue_id, text in words:
            requests.append(
                {
                    "speaker": "pedagogical",
                    "kind": "pedagogical_speech",
                    "locale": locale,
                    "text": text,
                    "cue_id": f"festa_delle_rime.{cue_id}",
                    "output": _output_path(review_dir, locale, cue_id),
                    "verification": "off",
                    "max_attempts": 1,
                }
            )
        for cue_id, text in prompts:
            requests.append(
                {
                    "speaker": "dani",
                    "kind": "dani_system_speech",
                    "locale": locale,
                    "text": text,
                    "cue_id": f"festa_delle_rime.{cue_id}",
                    "output": _output_path(review_dir, locale, cue_id),
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
