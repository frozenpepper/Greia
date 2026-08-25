#!/usr/bin/env python3
"""Generate Specchi Magici audio assets using Chatterbox Multilingual V3 with canonical Lilli voice."""

from __future__ import annotations

import hashlib
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
DEFAULT_AUDIO_ROOT = PROJECT_ROOT / "activities" / "specchi_magici" / "assets" / "audio"
REFERENCE_AUDIO = PROJECT_ROOT / "assets" / "audio" / "characters" / "canonical" / "v0.1" / "lilli-reference-v1.flac"

PROMPTS_IT = [
    ("welcome", "Ciao! Guarda lo specchio magico e posiziona le forme uguali dall altra parte!"),
    ("prompt_place", "Rifletti le forme sullo specchio magico!"),
    ("correct_1", "Ottimo lavoro!"),
    ("correct_2", "Ben fatto!"),
    ("correct_3", "Esatto!"),
    ("correct_4", "Fantastico!"),
    ("correct_5", "Evviva!"),
    ("retry_1", "Quasi! Guarda bene la distanza dallo specchio!"),
    ("retry_2", "Riprova, sei quasi riuscito!"),
    ("mosaic_complete", "Che bello specchio! Ecco il prossimo mosaico!"),
    ("shape_circle", "Cerchio!"),
    ("shape_square", "Quadrato!"),
    ("shape_triangle", "Triangolo!"),
    ("shape_semicircle", "Semicerchio!"),
]

PROMPTS_EN = [
    ("welcome", "Hello! Look in the magic mirror and place the matching shapes on the other side!"),
    ("prompt_place", "Mirror the shapes across the magic line!"),
    ("correct_1", "Great job!"),
    ("correct_2", "Well done!"),
    ("correct_3", "Exactly right!"),
    ("correct_4", "Awesome!"),
    ("correct_5", "Hooray!"),
    ("retry_1", "Almost! Look closely at the distance from the mirror!"),
    ("retry_2", "Try again, you are so close!"),
    ("mosaic_complete", "Beautiful mirror! Here is the next mosaic!"),
    ("shape_circle", "Circle!"),
    ("shape_square", "Square!"),
    ("shape_triangle", "Triangle!"),
    ("shape_semicircle", "Semicircle!"),
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
        print(f"[{idx}/{len(prompts)}] Generating {key}: {text}")
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
