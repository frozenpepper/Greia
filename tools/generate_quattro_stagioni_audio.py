#!/usr/bin/env python3
"""Generate complete spoken audio for 'Il Grande Albero delle Stagioni' (Tito lead presenter).

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
ACTIVITY_ROOT = PROJECT_ROOT / "activities" / "quattro_stagioni"

TITO_SCRIPTS = {
    "it": [
        ("welcome", "Ciao! Guarda il mio grande albero! Giochiamo insieme?"),
        ("day", "È arrivato il giorno! Buongiorno sole!"),
        ("night", "È arrivata la notte! Guarda le stelle e la luna! Buonanotte!"),
        ("sun", "Che bel sole caldo! Splende alto nel cielo!"),
        ("rain", "Piove! Plip plop! Mettiamoci gli stivaletti!"),
        ("wind", "Uuuh, che vento! Soffia forte e fa ballare le foglie!"),
        ("snow", "Nevica! Fiocchi di neve soffici e bianchi!"),
        ("spring", "In primavera sbocciano tanti fiorellini colorati!"),
        ("summer", "È estate! L'albero ha tante foglie verdi e mele dolci!"),
        ("autumn", "In autunno le foglie diventano rosse e cadono: frusc frusc!"),
        ("winter", "In inverno c'è la neve! Facciamo un pupazzo di neve insieme!"),
        ("praise_1", "Che meraviglia!"),
        ("praise_2", "Ottimo lavoro!"),
        ("praise_3", "Fantastico!"),
        ("activity-title", "Il Grande Albero delle Stagioni"),
    ],
    "en": [
        ("welcome", "Hi! Look at my big tree! Let's play together!"),
        ("day", "Daytime is here! Good morning, sun!"),
        ("night", "Nighttime is here! Look at the stars and the moon! Good night!"),
        ("sun", "Such a warm sun! Shining high in the sky!"),
        ("rain", "It's raining! Plip plop! Let's put on our boots!"),
        ("wind", "Whoosh, what wind! Blowing strong and making leaves dance!"),
        ("snow", "It's snowing! Soft and white snowflakes!"),
        ("spring", "In spring, lots of colorful flowers bloom!"),
        ("summer", "It's summer! The tree has green leaves and sweet apples!"),
        ("autumn", "In autumn the leaves turn red and fall down: swoosh swoosh!"),
        ("winter", "In winter there is snow! Let's make a snowman together!"),
        ("praise_1", "How wonderful!"),
        ("praise_2", "Great job!"),
        ("praise_3", "Fantastic!"),
        ("activity-title", "The Big Seasons Tree"),
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
                    "cue_id": f"quattro_stagioni.{key}",
                    "output": rel_out,
                    "verification": "off",
                    "max_attempts": 1,
                }
            )

    batch_path = PROJECT_ROOT / "tmp" / "voice_requests_quattro_stagioni.jsonl"
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    batch_path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in requests), encoding="utf-8"
    )
    print(f"Generating {len(requests)} audio clips for Il Grande Albero delle Stagioni...")
    res = subprocess.run([sys.executable, str(VOICE_CLI), "batch", "--input", str(batch_path)], cwd=PROJECT_ROOT)
    return res.returncode


def main() -> int:
    return generate_audio()


if __name__ == "__main__":
    raise SystemExit(main())
