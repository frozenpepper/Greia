#!/usr/bin/env python3
"""Generate Tre Carte Una Storia voice assets using Chatterbox Multilingual V3 with Lilli reference audio."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import numpy as np
import soundfile as sf
from mlx_audio.tts.utils import load_model
from mlx_audio.utils import load_audio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIO_ROOT = PROJECT_ROOT / "activities" / "tre_carte_una_storia" / "assets" / "audio"
REFERENCE_AUDIO = PROJECT_ROOT / "assets" / "audio" / "characters" / "canonical" / "v0.1" / "lilli-reference-v1.flac"

PROMPTS_IT = [
    ("welcome", "Ciao! Metti in ordine le tre carte per raccontare la storia: prima, poi, e infine!"),
    ("prompt_sequence", "Metti in ordine le tre carte!"),
    ("slot_1", "Prima!"),
    ("slot_2", "Poi!"),
    ("slot_3", "Infine!"),
    ("correct_1", "Ottimo lavoro! La storia è perfetta!"),
    ("correct_2", "Ben fatto!"),
    ("correct_3", "Fantastico!"),
    ("retry_1", "Quasi! Guarda bene cosa succede prima!"),
    ("hint_first", "Ecco la prima carta!"),
    ("caption_intro", "Ora scegli la frase per la tua storia!"),
    ("story_drawing_c1", "Prendo fogli e colori."),
    ("story_drawing_c2", "Disegno una bella figura!"),
    ("story_drawing_c3", "Regalo il disegno a un amico."),
    ("story_rain_c1", "Inizia a piovere dal cielo."),
    ("story_rain_c2", "Apro l ombrello colorato."),
    ("story_rain_c3", "Salto felice nella pozzanghera!"),
    ("story_kite_c1", "Il filo dell aquilone si scioglie."),
    ("story_kite_c2", "Faccio un bel nodo stretto."),
    ("story_kite_c3", "L aquilone vola alto nel cielo!"),
    ("story_picnic_c1", "Preparo il cestino con la merenda."),
    ("story_picnic_c2", "Cammino verso il prato verde."),
    ("story_picnic_c3", "Facciamo merenda insieme!"),
    ("story_postcard_c1", "Scrivo un messaggio affettuoso."),
    ("story_postcard_c2", "Metto la cartolina nella busta."),
    ("story_postcard_c3", "L amico apre la lettera con un sorriso!"),
    ("story_tower_c1", "Impilo i cubi di legno."),
    ("story_tower_c2", "Costruisco una torre alta."),
    ("story_tower_c3", "Metto la bandierina in cima!"),
    ("story_cloud_c1", "Trovo una nuvoletta infreddolita."),
    ("story_cloud_c2", "La avvolgo in una coperta morbida."),
    ("story_cloud_c3", "La nuvoletta splende felice e calda!"),
    ("story_spill_c1", "Si rovescia un po d acqua."),
    ("story_spill_c2", "Prendo un panno per pulire."),
    ("story_spill_c3", "Il pavimento è di nuovo pulito e asciutto!"),
]

PROMPTS_EN = [
    ("welcome", "Hello! Put the three cards in order to tell the story: first, then, and last!"),
    ("prompt_sequence", "Put the three cards in order!"),
    ("slot_1", "First!"),
    ("slot_2", "Then!"),
    ("slot_3", "Last!"),
    ("correct_1", "Great job! Your story is in order!"),
    ("correct_2", "Well done!"),
    ("correct_3", "Awesome!"),
    ("retry_1", "Almost! Look carefully at what happens first!"),
    ("hint_first", "Here is the first card!"),
    ("caption_intro", "Now choose a sentence for your story!"),
    ("story_drawing_c1", "I get paper and crayons."),
    ("story_drawing_c2", "I draw a pretty picture!"),
    ("story_drawing_c3", "I give the picture to a friend."),
    ("story_rain_c1", "Rain begins to fall from the sky."),
    ("story_rain_c2", "I open my colorful umbrella."),
    ("story_rain_c3", "I jump happily in the puddle!"),
    ("story_kite_c1", "The kite string is loose."),
    ("story_kite_c2", "I tie a tight knot."),
    ("story_kite_c3", "The kite flies high in the sky!"),
    ("story_picnic_c1", "I pack the picnic basket."),
    ("story_picnic_c2", "I walk to the green meadow."),
    ("story_picnic_c3", "We share a picnic together!"),
    ("story_postcard_c1", "I write a kind message."),
    ("story_postcard_c2", "I put the card in an envelope."),
    ("story_postcard_c3", "My friend opens it with a smile!"),
    ("story_tower_c1", "I stack the wooden blocks."),
    ("story_tower_c2", "I build a tall tower."),
    ("story_tower_c3", "I put the flag on top!"),
    ("story_cloud_c1", "I find a chilly little cloud."),
    ("story_cloud_c2", "I wrap it in a soft blanket."),
    ("story_cloud_c3", "The cloud glows warmly and happy!"),
    ("story_spill_c1", "Some water spills on the floor."),
    ("story_spill_c2", "I fetch a cloth to wipe it."),
    ("story_spill_c3", "The floor is dry and clean again!"),
]


def convert_to_le16_mono_22050(src_wav: Path, dest_wav: Path) -> None:
    dest_wav.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "afconvert",
            "-f", "WAVE",
            "-d", "LEI16@22050",
            "-c", "1",
            str(src_wav),
            str(dest_wav),
        ],
        check=True,
        capture_output=True,
    )


def generate_set(model, ref_audio, prompts, lang_code, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating {len(prompts)} clips for {lang_code} in {out_dir}...")
    for idx, (key, text) in enumerate(prompts, start=1):
        dest_wav = out_dir / f"{key}.wav"
        print(f"[{idx}/{len(prompts)}] Generating {key}: '{text}'")
        for attempt in range(3):
            try:
                results = model.generate(
                    text=text,
                    lang_code=lang_code,
                    ref_audio=ref_audio,
                    temperature=0.7,
                )
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    tmp_wav = Path(tmp_file.name)
                for res in results:
                    sf.write(str(tmp_wav), np.array(res.audio), res.sample_rate)
                    break
                convert_to_le16_mono_22050(tmp_wav, dest_wav)
                tmp_wav.unlink(missing_ok=True)
                break
            except Exception as e:
                print(f"  Attempt {attempt + 1} failed: {e}")
                if attempt == 2:
                    raise


def main() -> None:
    if not REFERENCE_AUDIO.exists():
        print(f"Error: reference audio not found at {REFERENCE_AUDIO}")
        sys.exit(1)

    print("Loading Chatterbox Multilingual V3 model on Apple Silicon...")
    model = load_model("mlx-community/chatterbox-multilingual-v3")
    ref_audio = load_audio(str(REFERENCE_AUDIO), sample_rate=model.sample_rate)
    print("Loaded reference:", REFERENCE_AUDIO)

    audio_root = DEFAULT_AUDIO_ROOT
    generate_set(model, ref_audio, PROMPTS_IT, "it", audio_root / "it")
    generate_set(model, ref_audio, PROMPTS_EN, "en", audio_root / "en")

    # Update manifest
    manifest_path = audio_root / "audio_manifest.sha256"
    lines = []
    for p in sorted(audio_root.rglob("*.wav")):
        rel = p.relative_to(audio_root)
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{digest}  {rel}")
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Successfully generated all {len(lines)} clips with Lilli canonical voice!")
    print(f"Updated {manifest_path}")


if __name__ == "__main__":
    main()
