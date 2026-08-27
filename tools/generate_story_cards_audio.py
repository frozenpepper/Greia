#!/usr/bin/env python3
"""Prepare Tre Carte Una Storia Lilli speech through Greia VoiceEngine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_CLI = PROJECT_ROOT / "tools" / "greia_voice.py"
DEFAULT_REVIEW_DIR = PROJECT_ROOT / "tmp" / "voice-review" / "tre_carte_una_storia"

PROMPTS_IT = [
    ("welcome", "Ciao! Metti in ordine le tre carte per raccontare la storia: prima, poi, e infine!"),
    ("prompt_sequence", "Metti in ordine le tre carte!"),
    ("slot_1", "Prima!"), ("slot_2", "Poi!"), ("slot_3", "Infine!"),
    ("correct_1", "Ottimo lavoro! La storia è perfetta!"), ("correct_2", "Ben fatto!"), ("correct_3", "Fantastico!"),
    ("retry_1", "Quasi! Guarda bene cosa succede prima!"), ("hint_first", "Ecco la prima carta!"),
    ("caption_intro", "Ora scegli la frase per la tua storia!"),
    ("story_drawing_c1", "Prendo fogli e colori."), ("story_drawing_c2", "Disegno una bella figura!"), ("story_drawing_c3", "Regalo il disegno a un amico."),
    ("story_rain_c1", "Inizia a piovere dal cielo."), ("story_rain_c2", "Apro l ombrello colorato."), ("story_rain_c3", "Salto felice nella pozzanghera!"),
    ("story_kite_c1", "Il filo dell aquilone si scioglie."), ("story_kite_c2", "Faccio un bel nodo stretto."), ("story_kite_c3", "L aquilone vola alto nel cielo!"),
    ("story_picnic_c1", "Preparo il cestino con la merenda."), ("story_picnic_c2", "Cammino verso il prato verde."), ("story_picnic_c3", "Facciamo merenda insieme!"),
    ("story_postcard_c1", "Scrivo un messaggio affettuoso."), ("story_postcard_c2", "Metto la cartolina nella busta."), ("story_postcard_c3", "L amico apre la lettera con un sorriso!"),
    ("story_tower_c1", "Impilo i cubi di legno."), ("story_tower_c2", "Costruisco una torre alta."), ("story_tower_c3", "Metto la bandierina in cima!"),
    ("story_cloud_c1", "Trovo una nuvoletta infreddolita."), ("story_cloud_c2", "La avvolgo in una coperta morbida."), ("story_cloud_c3", "La nuvoletta splende felice e calda!"),
    ("story_spill_c1", "Si rovescia un po d acqua."), ("story_spill_c2", "Prendo un panno per pulire."), ("story_spill_c3", "Il pavimento è di nuovo pulito e asciutto!"),
]

PROMPTS_EN = [
    ("welcome", "Hello! Put the three cards in order to tell the story: first, then, and last!"),
    ("prompt_sequence", "Put the three cards in order!"),
    ("slot_1", "First!"), ("slot_2", "Then!"), ("slot_3", "Last!"),
    ("correct_1", "Great job! Your story is in order!"), ("correct_2", "Well done!"), ("correct_3", "Awesome!"),
    ("retry_1", "Almost! Look carefully at what happens first!"), ("hint_first", "Here is the first card!"),
    ("caption_intro", "Now choose a sentence for your story!"),
    ("story_drawing_c1", "I get paper and crayons."), ("story_drawing_c2", "I draw a pretty picture!"), ("story_drawing_c3", "I give the picture to a friend."),
    ("story_rain_c1", "Rain begins to fall from the sky."), ("story_rain_c2", "I open my colorful umbrella."), ("story_rain_c3", "I jump happily in the puddle!"),
    ("story_kite_c1", "The kite string is loose."), ("story_kite_c2", "I tie a tight knot."), ("story_kite_c3", "The kite flies high in the sky!"),
    ("story_picnic_c1", "I pack the picnic basket."), ("story_picnic_c2", "I walk to the green meadow."), ("story_picnic_c3", "We share a picnic together!"),
    ("story_postcard_c1", "I write a kind message."), ("story_postcard_c2", "I put the card in an envelope."), ("story_postcard_c3", "My friend opens it with a smile!"),
    ("story_tower_c1", "I stack the wooden blocks."), ("story_tower_c2", "I build a tall tower."), ("story_tower_c3", "I put the flag on top!"),
    ("story_cloud_c1", "I find a chilly little cloud."), ("story_cloud_c2", "I wrap it in a soft blanket."), ("story_cloud_c3", "The cloud glows warmly and happy!"),
    ("story_spill_c1", "Some water spills on the floor."), ("story_spill_c2", "I fetch a cloth to wipe it."), ("story_spill_c3", "The floor is dry and clean again!"),
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
            "speaker": "lilli",
            "kind": "character_dialogue",
            "locale": locale,
            "text": text,
            "cue_id": f"tre_carte_una_storia.{key}",
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
        [sys.executable, str(VOICE_CLI), "batch", "--input", str(batch_path)], cwd=PROJECT_ROOT
    )
    if result.returncode == 0:
        print(f"Generated {len(requests)} Lilli review candidates under {review_dir}")
        print("Human listening review is required before Activity integration.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
