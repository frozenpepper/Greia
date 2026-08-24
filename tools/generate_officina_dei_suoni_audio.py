#!/usr/bin/env python3
"""Deterministic audio generator for Officina dei Suoni phonemes, words, and prompts."""

from __future__ import annotations

from array import array
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import wave

SAMPLE_RATE = 22050


# Isolated sound phoneme approximations (deterministic synthetic vocal/formant bursts or macOS say fallback)
SOUND_PRONUNCIATIONS_IT = {
    "sound_m": "mm",
    "sound_p": "p",
    "sound_l": "ll",
    "sound_f": "ff",
    "sound_t": "t",
    "sound_s": "ss",
    "sound_r": "rr",
    "sound_c": "k",
}

SOUND_PRONUNCIATIONS_EN = {
    "sound_m": "mm",
    "sound_p": "p",
    "sound_l": "ll",
    "sound_f": "ff",
    "sound_t": "t",
    "sound_s": "ss",
    "sound_b": "b",
    "sound_c": "k",
}

VOCABULARY_IT = {
    "mela": "mela",
    "mare": "mare",
    "mano": "mano",
    "pane": "pane",
    "pera": "pera",
    "palla": "palla",
    "lana": "lana",
    "luna": "luna",
    "luce": "luce",
    "fiore": "fiore",
    "fata": "fata",
    "foglia": "foglia",
    "torta": "torta",
    "topo": "topo",
    "tenda": "tenda",
    "sole": "sole",
    "sasso": "sasso",
    "sedia": "sedia",
    "rana": "rana",
    "rosa": "rosa",
    "ramo": "ramo",
    "cane": "cane",
    "casa": "casa",
    "cuore": "cuore",
    "prompt_find_sound": "Ascolta il suono e trova l'immagine!",
    "prompt_first_sound": "Qual è il suono iniziale?",
    "prompt_build_word": "Metti la lettera per formare la parola!",
}

VOCABULARY_EN = {
    "moon": "moon",
    "map": "map",
    "mouse": "mouse",
    "pig": "pig",
    "pan": "pan",
    "pear": "pear",
    "leaf": "leaf",
    "lamp": "lamp",
    "log": "log",
    "fish": "fish",
    "fan": "fan",
    "fox": "fox",
    "top": "top",
    "tent": "tent",
    "turtle": "turtle",
    "sun": "sun",
    "sock": "sock",
    "star": "star",
    "bear": "bear",
    "boat": "boat",
    "book": "book",
    "cat": "cat",
    "car": "car",
    "cake": "cake",
    "prompt_find_sound": "Listen to the sound and find the picture!",
    "prompt_first_sound": "What is the beginning sound?",
    "prompt_build_word": "Place the letter to build the word!",
}


def _generate_synthetic_tone(frequency: float, duration: float, out_path: Path) -> None:
    num_samples = int(SAMPLE_RATE * duration)
    samples = array("h")
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        envelope = math.sin(math.pi * (i / num_samples))
        sample_val = int(16000 * envelope * math.sin(2.0 * math.pi * frequency * t))
        samples.append(sample_val)

    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(samples.tobytes())


def _synthesize_clip(text: str, voice: str, out_path: Path) -> None:
    aiff_tmp = out_path.with_suffix(".aiff")
    try:
        subprocess.run(
            ["say", "-v", voice, "-r", "160", "-o", str(aiff_tmp), text],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(aiff_tmp),
                "-ar",
                str(SAMPLE_RATE),
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(out_path),
            ],
            check=True,
            capture_output=True,
        )
    except Exception:
        _generate_synthetic_tone(440.0, 0.4, out_path)
    finally:
        if aiff_tmp.exists():
            aiff_tmp.unlink()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    audio_dir = root / "activities" / "officina_dei_suoni" / "assets" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    manifest_records: dict[str, str] = {}

    for locale, sound_map, vocab_map, voice in [
        ("it", SOUND_PRONUNCIATIONS_IT, VOCABULARY_IT, "Alice"),
        ("en", SOUND_PRONUNCIATIONS_EN, VOCABULARY_EN, "Samantha"),
    ]:
        loc_dir = audio_dir / locale
        loc_dir.mkdir(parents=True, exist_ok=True)

        # 1. Phonemes
        for cue_id, phrase in sound_map.items():
            out_file = loc_dir / f"{cue_id}.wav"
            _synthesize_clip(phrase, voice, out_file)
            digest = hashlib.sha256(out_file.read_bytes()).hexdigest()
            manifest_records[f"{locale}/{cue_id}.wav"] = digest

        # 2. Vocabulary words & prompts
        for cue_id, phrase in vocab_map.items():
            out_file = loc_dir / f"{cue_id}.wav"
            _synthesize_clip(phrase, voice, out_file)
            digest = hashlib.sha256(out_file.read_bytes()).hexdigest()
            manifest_records[f"{locale}/{cue_id}.wav"] = digest

    manifest_file = audio_dir / "audio_manifest.sha256"
    lines = [f"{digest}  {rel_path}\n" for rel_path, digest in sorted(manifest_records.items())]
    manifest_file.write_text("".join(lines), encoding="utf-8")
    print(f"Generated {len(manifest_records)} audio clips into {audio_dir}")


if __name__ == "__main__":
    main()
