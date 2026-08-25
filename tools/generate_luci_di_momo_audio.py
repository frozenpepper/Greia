#!/usr/bin/env python3
"""Generate Luci di Momo audio assets using Chatterbox Multilingual V3 with canonical Momo voice."""

from __future__ import annotations

import gc
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile

import mlx.core as mx
import numpy as np
import soundfile as sf
from mlx_audio.tts.utils import load_model
from mlx_audio.utils import load_audio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIO_ROOT = PROJECT_ROOT / "activities" / "luci_di_momo" / "assets" / "audio"
REFERENCE_AUDIO = PROJECT_ROOT / "assets" / "audio" / "characters" / "canonical" / "v0.1" / "momo-reference-v1.flac"

PROMPTS_IT = [
    ("welcome", "Ciao! Guarda bene quante lucciole brillano nella notte, poi tocca il numero giusto!"),
    ("prompt_ready", "Tocca il grande pulsante quando sei pronto per far brillare le lucciole!"),
    ("prompt_choose", "Quante lucciole hai visto?"),
    ("correct_1", "Ottimo lavoro!"),
    ("correct_2", "Ben fatto!"),
    ("correct_3", "Esatto!"),
    ("correct_4", "Fantastico!"),
    ("correct_5", "Evviva!"),
    ("retry_1", "Quasi! Guarda di nuovo quante lucciole brillano!"),
    ("retry_2", "Riprova, guarda bene le lucine!"),
    ("count_1", "Una lucciola!"),
    ("count_2", "Due lucciole!"),
    ("count_3", "Tre lucciole!"),
    ("count_4", "Quattro lucciole!"),
    ("count_5", "Cinque lucciole!"),
    ("garden_complete", "Che meraviglia! Tutte le lucciole sono felici e illuminate!"),
]

PROMPTS_EN = [
    ("welcome", "Hello! Look closely at how many fireflies glow in the night, then tap the right number!"),
    ("prompt_ready", "Tap the big play button when you are ready to see the fireflies glow!"),
    ("prompt_choose", "How many fireflies did you see?"),
    ("correct_1", "Great job!"),
    ("correct_2", "Well done!"),
    ("correct_3", "Exactly right!"),
    ("correct_4", "Awesome!"),
    ("correct_5", "Hooray!"),
    ("retry_1", "Almost! Look again at how many fireflies glow!"),
    ("retry_2", "Try again, look closely at the little lights!"),
    ("count_1", "One firefly!"),
    ("count_2", "Two fireflies!"),
    ("count_3", "Three fireflies!"),
    ("count_4", "Four fireflies!"),
    ("count_5", "Five fireflies!"),
    ("garden_complete", "Wonderful! All the fireflies are shining bright and happy!"),
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
    print(f"Generating {len(prompts)} clips for {lang_code} in {out_dir}...", flush=True)
    for idx, (key, text) in enumerate(prompts, start=1):
        dest_wav = out_dir / f"{key}.wav"
        if dest_wav.exists() and dest_wav.stat().st_size > 1000:
            print(f"[{idx}/{len(prompts)}] Skipping {key} (already exists)", flush=True)
            continue
        print(f"[{idx}/{len(prompts)}] Generating {key}: {text}", flush=True)
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
                # Clear Metal and Python memory cache immediately after generation
                mx.metal.clear_cache()
                gc.collect()
                break
            except Exception as e:
                print(f"  Attempt {attempt + 1} failed: {e}", flush=True)
                mx.metal.clear_cache()
                gc.collect()
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
    print(f"Successfully generated all {len(lines)} clips with Momo canonical voice!")
    print(f"Updated {manifest_path}")


if __name__ == "__main__":
    main()
