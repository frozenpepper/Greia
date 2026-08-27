#!/usr/bin/env python3
"""Prepare Stelle Incantate Leo speech through Greia's canonical VoiceEngine.

This Activity owns only semantic cue IDs and reviewed localized wording. Provider
selection, canonical reference validation, model loading, token budgets, trimming,
verification, packaging and receipts belong to ``tools/greia_voice.py``.

Existing packaged Activity audio is not rewritten automatically. New takes are
written to a review workspace and remain human-review PENDING until explicitly
accepted and integrated.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_CLI = PROJECT_ROOT / "tools" / "greia_voice.py"
DEFAULT_REVIEW_DIR = PROJECT_ROOT / "tmp" / "voice-review" / "stelle_incantate"

FACTS: dict[str, list[tuple[str, str]]] = {
    "it": [
        ("curiosity-triangolo", "Nel cielo ci sono 88 costellazioni ufficiali, decise dagli astronomi di tutto il mondo!"),
        ("curiosity-cassiopea", "Cassiopea era una regina delle storie antiche: la sua W di stelle brilla ancora ogni notte."),
        ("curiosity-cigno", "Il Cigno vola nel cielo estivo con le sue stelle a forma di grande croce."),
        ("curiosity-carro", "Le due stelle del bordo del Grande Carro indicano la strada verso la Stella Polare!"),
        ("curiosity-leone", "Il Leone è una costellazione antichissima: la guardiamo da migliaia di anni."),
        ("curiosity-orione", "Le stelle di una costellazione sembrano vicine, ma in realtà molte sono lontanissime tra loro!"),
    ],
    "en": [
        ("curiosity-triangolo", "There are 88 official constellations, chosen by astronomers all over the world!"),
        ("curiosity-cassiopea", "Cassiopeia was a queen from ancient stories: her W of stars still shines every night."),
        ("curiosity-cigno", "The Swan flies across the summer sky with its stars shaped like a big cross."),
        ("curiosity-carro", "The two stars on the edge of the Big Dipper point the way to the North Star!"),
        ("curiosity-leone", "The Lion is a very ancient constellation: people have watched it for thousands of years."),
        ("curiosity-orione", "The stars of a constellation look close together, but many are really far, far apart!"),
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

    batch_path = review_dir / "voice_requests.jsonl"
    requests = []
    for locale, items in FACTS.items():
        for cue, text in items:
            requests.append(
                {
                    "speaker": "leo",
                    "kind": "character_dialogue",
                    "locale": locale,
                    "text": text,
                    "cue_id": f"stelle_incantate.{cue}",
                    "output": _output_path(review_dir, locale, cue),
                    "verification": "auto",
                    "max_attempts": 2,
                }
            )
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
