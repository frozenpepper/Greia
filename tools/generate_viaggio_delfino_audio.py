#!/usr/bin/env python3
"""Prepare Il Viaggio del Delfino Tito speech through Greia VoiceEngine.

The Activity owns semantic cue IDs and reviewed localized wording only. Chatterbox,
canonical reference files, model lifecycle, trimming, verification and packaging are
VoiceEngine implementation details. Existing packaged audio is left untouched; new
takes are review candidates until a human accepts and integrates them.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_CLI = PROJECT_ROOT / "tools" / "greia_voice.py"
DEFAULT_REVIEW_DIR = PROJECT_ROOT / "tmp" / "voice-review" / "viaggio_delfino"

CLIPS: dict[str, list[tuple[str, str]]] = {
    "it": [
        ("presenter-welcome", "Ciao! Io sono Tito! Muovi il mouse o usa le frecce per nuotare, e premi la barra per saltare fuori dall'acqua! Raccogli tutte le perle!"),
        ("curiosity-breaching", "I delfini saltano fuori dall'acqua, finanche a quattro metri! Lo fanno per giocare e per farsi vedere dagli amici lontani."),
        ("curiosity-echolocation", "Il delfino emette piccoli click: ascoltando l'eco trova i pesci perfino dove non si vede!"),
        ("curiosity-blowhole", "Il delfino non è un pesce: è un mammifero! Respira l'aria dal foro sulla testa, il sfiatatoio."),
        ("curiosity-pods", "I delfini vivono in famiglie chiamate branchi: insieme cacciano i pesci e si proteggono."),
        ("curiosity-teeth", "Il delfino ha tanti dentini, ma non mastica mai: afferra il pesce e lo ingoia tutto intero!"),
        ("curiosity-whistle", "Ogni delfino ha un fischietto speciale, quasi un nome: così gli amici lo riconoscono!"),
    ],
    "en": [
        ("presenter-welcome", "Hi! I'm Tito! Move the mouse or use the arrow keys to swim, and press the space bar to leap out of the water! Collect all the pearls!"),
        ("curiosity-breaching", "Dolphins leap out of the water, up to four metres high! They do it to play and to show faraway friends where they are."),
        ("curiosity-echolocation", "The dolphin makes little clicks: listening to the echoes, it finds fish even where it cannot see!"),
        ("curiosity-blowhole", "A dolphin is not a fish: it is a mammal! It breathes air through the hole on top of its head, the blowhole."),
        ("curiosity-pods", "Dolphins live in families called pods: together they herd fish and keep each other safe."),
        ("curiosity-teeth", "A dolphin has many tiny teeth, but it never chews: it grabs the fish and swallows it whole!"),
        ("curiosity-whistle", "Every dolphin has its own special whistle, almost like a name: that is how friends recognise it!"),
    ],
}


def _output_path(review_dir: Path, locale: str, cue: str) -> str:
    output = review_dir / locale / f"{cue}.ogg"
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

    requests = [
        {
            "speaker": "tito",
            "kind": "character_dialogue",
            "locale": locale,
            "text": text,
            "cue_id": f"viaggio_delfino.{cue}",
            "output": _output_path(review_dir, locale, cue),
            "verification": "auto",
            "max_attempts": 2,
        }
        for locale, items in CLIPS.items()
        for cue, text in items
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
        print(f"Generated {len(requests)} review candidates under {review_dir}")
        print("Human listening review is still required before Activity integration.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
