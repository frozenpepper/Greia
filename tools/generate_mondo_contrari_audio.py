#!/usr/bin/env python3
"""Generate complete spoken audio for 'Mondo Contrari' (Flash rabbit lead presenter).

Follows Greia voice production rules:
- Speaker: Flash (canonical character dialogue)
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
ACTIVITY_ROOT = PROJECT_ROOT / "activities" / "mondo_contrari"

FLASH_SCRIPTS = {
    "it": [
        ("welcome", "Ciao! Giochiamo con i contrari? È divertentissimo!"),
        ("up", "SUUUU! In alto verso le nuvole!"),
        ("down", "GIÙÙÙ! In basso sul prato!"),
        ("big", "GRAAANDE! Enorme come un elefante!"),
        ("small", "Piccolo piccolo, come una formichina!"),
        ("in", "DENTRO la scatola! Cucù, dove sono finito?"),
        ("out", "FUORI! Un bel salto, eccomi qui!"),
        ("open", "APERTO! Ciao amico!"),
        ("closed", "CHIUSO! Tutto al sicuro!"),
        ("fast", "VELOCISSIMO! Come un lampo! Vruuum!"),
        ("slow", "Piaaaano... lento come una lumachina..."),
        ("praise_1", "Che meraviglia!"),
        ("praise_2", "Ottimo lavoro!"),
        ("praise_3", "Fantastico!"),
        ("activity-title", "Mondo Contrari"),
    ],
    "en": [
        ("welcome", "Hi! Let's play with opposites! It's so much fun!"),
        ("up", "UP! High up in the clouds!"),
        ("down", "DOWN! Down to the grass!"),
        ("big", "BIG! Huge like an elephant!"),
        ("small", "Small, tiny like a little ant!"),
        ("in", "INSIDE the box! Peek-a-boo!"),
        ("out", "OUTSIDE! A big hop, here I am!"),
        ("open", "OPEN! Hello friend!"),
        ("closed", "CLOSED! Safe and sound!"),
        ("fast", "FAST! Fast like lightning! Vroom!"),
        ("slow", "Sloooow... like a little snail..."),
        ("praise_1", "How wonderful!"),
        ("praise_2", "Great job!"),
        ("praise_3", "Fantastic!"),
        ("activity-title", "Opposites World"),
    ],
}


def generate_audio() -> int:
    requests = []

    for locale in ["it", "en"]:
        loc_dir = ACTIVITY_ROOT / "locales" / locale / "audio"
        loc_dir.mkdir(parents=True, exist_ok=True)

        for key, text in FLASH_SCRIPTS[locale]:
            out_file = loc_dir / f"{key}.wav"
            rel_out = str(out_file.relative_to(PROJECT_ROOT))
            requests.append(
                {
                    "speaker": "flash",
                    "kind": "character_dialogue",
                    "locale": locale,
                    "text": text,
                    "cue_id": f"mondo_contrari.{key}",
                    "output": rel_out,
                    "verification": "off",
                    "max_attempts": 1,
                }
            )

    batch_path = PROJECT_ROOT / "tmp" / "voice_requests_mondo_contrari.jsonl"
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    batch_path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in requests), encoding="utf-8"
    )
    print(f"Generating {len(requests)} audio clips for Mondo Contrari...")
    res = subprocess.run([sys.executable, str(VOICE_CLI), "batch", "--input", str(batch_path)], cwd=PROJECT_ROOT)
    return res.returncode


def main() -> int:
    return generate_audio()


if __name__ == "__main__":
    raise SystemExit(main())
