#!/usr/bin/env python3
"""Generate complete spoken audio for 'Il Bosco dei Numeri di Tito' (Tito lead presenter).

Follows Greia voice production rules:
- Speaker: Tito (canonical character dialogue)
- Provider: Chatterbox / VoiceEngine via tools/greia_voice.py
- Output locales: it, en
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_CLI = PROJECT_ROOT / "tools" / "greia_voice.py"
ACTIVITY_ROOT = PROJECT_ROOT / "activities" / "bosco_numeri"

TITO_SCRIPTS = {
    "it": [
        ("activity-title", "Il Bosco dei Numeri di Tito"),
    ],
    "en": [
        ("activity-title", "Tito's Number Forest"),
    ],
}


def generate_audio() -> int:
    requests = []

    for locale in ["it", "en"]:
        loc_dir = ACTIVITY_ROOT / "locales" / locale / "audio"
        loc_dir.mkdir(parents=True, exist_ok=True)

        for key, text in TITO_SCRIPTS[locale]:
            out_file = loc_dir / f"{key}.wav"
            rel_out = str(out_file.relative_to(PROJECT_ROOT))
            requests.append(
                {
                    "speaker": "tito",
                    "kind": "character_dialogue",
                    "locale": locale,
                    "text": text,
                    "cue_id": f"bosco_numeri.{key}",
                    "output": rel_out,
                    "verification": "off",
                    "max_attempts": 1,
                }
            )

    batch_path = PROJECT_ROOT / "tmp" / "voice_requests_bosco_numeri.jsonl"
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    batch_path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in requests), encoding="utf-8"
    )
    print(f"Generating {len(requests)} audio clips for Il Bosco dei Numeri di Tito...")
    res = subprocess.run([sys.executable, str(VOICE_CLI), "batch", "--input", str(batch_path)], cwd=PROJECT_ROOT)
    return res.returncode


def main() -> int:
    return generate_audio()


if __name__ == "__main__":
    raise SystemExit(main())
