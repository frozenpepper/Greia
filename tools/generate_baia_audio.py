#!/usr/bin/env python3
"""Prepare Baia delle Orche Tito speech through Greia's canonical VoiceEngine.

This replaces the historical direct-Chatterbox generator and its silent-stub failure
path. Generation failures are now VoiceEngine failures; they are never converted into
fake valid audio. Existing packaged Activity audio is left untouched. New takes are
written to a review workspace and require human listening before integration.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_CLI = PROJECT_ROOT / "tools" / "greia_voice.py"
DEFAULT_REVIEW_DIR = PROJECT_ROOT / "tmp" / "voice-review" / "baia_delle_orche"

FACTS = {
    "it": [
        ("fact_breach", "I grandi salti fuori dall'acqua si chiamano breaching. Quando l'orca ricade fa un gran rumore, che può aiutare a mandare un segnale alle altre orche anche da lontano!"),
        ("fact_swallow", "Le orche non masticano il cibo: usano i denti per afferrare i pesciolini e poi li inghiottono tutti interi!"),
        ("fact_sleep", "Le orche dormono con un occhio aperto e metà cervello sveglio per ricordarsi di salire a respirare l'aria!"),
        ("fact_song", "Ogni famiglia di orche ha fischi speciali e una propria canzone unica, diversa da tutte le altre!"),
        ("fact_pod", "I cuccioli di orca restano sempre vicini alla loro mamma e al loro branco per tutta la vita!"),
        ("fact_fin", "La grande pinna sulla schiena dell'orca si chiama pinna dorsale e aiuta a nuotare dritti come frecce nell'acqua!"),
    ],
    "en": [
        ("fact_breach", "Big jumps out of the water are called breaching. When the orca splashes down it makes a huge sound, which helps send a signal to other orcas far away!"),
        ("fact_swallow", "Orcas don't chew their food: they use their teeth to catch fish and then swallow them whole!"),
        ("fact_sleep", "Orcas sleep with one eye open and half their brain awake so they remember to surface and breathe air!"),
        ("fact_song", "Every orca family has special whistles and its own unique song, different from all the others!"),
        ("fact_pod", "Orca calves stay close to their mother and their pod for their entire lives!"),
        ("fact_fin", "The big fin on an orca's back is called the dorsal fin, and it helps them swim straight like arrows in the water!"),
    ],
}


def _output_path(review_dir: Path, locale: str, key: str) -> str:
    output = review_dir / locale / f"tito_{key}.wav"
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
            "cue_id": f"baia_delle_orche.{key}",
            "output": _output_path(review_dir, locale, key),
            "verification": "auto",
            "max_attempts": 2,
        }
        for locale, items in FACTS.items()
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
        print(f"Generated {len(requests)} Tito review candidates under {review_dir}")
        print("No silent stubs are produced. Human listening review is required.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
