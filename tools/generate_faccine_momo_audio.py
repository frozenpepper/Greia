#!/usr/bin/env python3
"""Generate complete spoken audio for 'Le Faccine di Momo' (Momo lead presenter).

Follows Greia voice production rules:
- Speaker: Momo (canonical character dialogue)
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
ACTIVITY_ROOT = PROJECT_ROOT / "activities" / "faccine_momo"

MOMO_SCRIPTS = {
    "it": [
        ("welcome", "Ciao! Io sono Momo! Giochiamo con le faccine?"),
        ("happy", "Yeeee! Sono felicissimo! Che gioia!"),
        ("sad", "Oh no... sono un po' triste... mi fai una coccola?"),
        ("comfort", "Grazie per la coccola! Ora sto molto meglio!"),
        ("surprised", "Oooooh! Ma che cos'è?! Che sorpresa incredibile!"),
        ("silly", "Ahaha! Facciamo le boccacce! Bleeeeh!"),
        ("angry", "Uffa! Ho un po' di rabbia... facciamo un respiro profondo insieme: uuuuh!"),
        ("sleepy", "Yawn... che sonno... facciamo la nanna..."),
        ("game_prompt", "Come si sente Momo adesso? Guarda la mia faccina!"),
        ("praise_1", "Che meraviglia!"),
        ("praise_2", "Ottimo lavoro!"),
        ("praise_3", "Fantastico!"),
        ("activity-title", "Le Faccine di Momo"),
    ],
    "en": [
        ("welcome", "Hi! I am Momo! Let's play with faces!"),
        ("happy", "Yaaay! I am so happy! What joy!"),
        ("sad", "Oh no... I am a little sad... will you give me a hug?"),
        ("comfort", "Thank you for the cuddle! I feel much better now!"),
        ("surprised", "Oooooh! What is that?! Such an amazing surprise!"),
        ("silly", "Ahaha! Let's make silly faces! Bleeeeh!"),
        ("angry", "Hmph! I'm a bit grumpy... let's take a deep breath together: whooosh!"),
        ("sleepy", "Yawn... so sleepy... let's take a nap..."),
        ("game_prompt", "How is Momo feeling now? Look at my face!"),
        ("praise_1", "How wonderful!"),
        ("praise_2", "Great job!"),
        ("praise_3", "Fantastic!"),
        ("activity-title", "Momo's Happy Faces"),
    ],
}


def generate_audio() -> int:
    requests = []

    for locale in ["it", "en"]:
        loc_dir = ACTIVITY_ROOT / "locales" / locale / "audio"
        loc_dir.mkdir(parents=True, exist_ok=True)

        for key, text in MOMO_SCRIPTS[locale]:
            out_file = loc_dir / f"{key}.wav"
            rel_out = str(out_file.relative_to(PROJECT_ROOT))
            requests.append(
                {
                    "speaker": "momo",
                    "kind": "character_dialogue",
                    "locale": locale,
                    "text": text,
                    "cue_id": f"faccine_momo.{key}",
                    "output": rel_out,
                    "verification": "off",
                    "max_attempts": 1,
                }
            )

    batch_path = PROJECT_ROOT / "tmp" / "voice_requests_faccine_momo.jsonl"
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    batch_path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in requests), encoding="utf-8"
    )
    print(f"Generating {len(requests)} audio clips for Le Faccine di Momo...")
    res = subprocess.run([sys.executable, str(VOICE_CLI), "batch", "--input", str(batch_path)], cwd=PROJECT_ROOT)
    return res.returncode


def main() -> int:
    return generate_audio()


if __name__ == "__main__":
    raise SystemExit(main())
