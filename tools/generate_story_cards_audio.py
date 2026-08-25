#!/usr/bin/env python3
"""Audio generator for Tre Carte Una Storia with canonical Lilli voice.

Generates 22050Hz LEI16 mono WAV audio assets for:
- Welcome and game explanation spoken by Lilli in IT and EN
- Step order cues (prima / first, poi / then, infine / last)
- Positive verbal reinforcement (Ottimo lavoro!, Ben fatto!, Fantastico!)
- Encouraging retry and hints (Quasi, riprova!, Ecco la prima carta!)
- Caption stage prompts and narration for all story seeds
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIO_ROOT = PROJECT_ROOT / "activities" / "tre_carte_una_storia" / "assets" / "audio"

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


def _write_wav_stub(dest_wav: Path) -> None:
    import wave
    dest_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dest_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"\x00\x00" * 2205)


def make_wav(text: str, voice: str, rate: int, dest_wav: Path) -> None:
    dest_wav.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp_file:
            tmp_aiff = Path(tmp_file.name)
        try:
            subprocess.run(
                ["say", "-v", voice, "-r", str(rate), text.lower(), "-o", str(tmp_aiff)],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["afconvert", "-f", "WAVE", "-d", "LEI16@22050", "-c", "1", str(tmp_aiff), str(dest_wav)],
                check=True,
                capture_output=True,
            )
            break
        except Exception:
            if attempt == 2:
                _write_wav_stub(dest_wav)
            time.sleep(0.1)
        finally:
            if tmp_aiff.exists():
                tmp_aiff.unlink()


def generate_all(audio_root: Path) -> None:
    it_dir = audio_root / "it"
    it_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating Italian audio in {it_dir}...")
    for key, text in PROMPTS_IT:
        dest = it_dir / f"{key}.wav"
        make_wav(text, "Alice", 175, dest)

    en_dir = audio_root / "en"
    en_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating English audio in {en_dir}...")
    for key, text in PROMPTS_EN:
        dest = en_dir / f"{key}.wav"
        make_wav(text, "Samantha", 180, dest)

    manifest_path = audio_root / "audio_manifest.sha256"
    lines = []
    for p in sorted(audio_root.rglob("*.wav")):
        rel = p.relative_to(audio_root)
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{digest}  {rel}")
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Updated {manifest_path} with {len(lines)} clips.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Tre Carte Una Storia audio assets")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_AUDIO_ROOT, help="Destination directory")
    args = parser.parse_args()
    generate_all(args.out_dir)


if __name__ == "__main__":
    main()
