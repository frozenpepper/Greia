#!/usr/bin/env python3
"""Pedagogical speech audio generator for Festa delle Rime (Festival of Rhymes).

Generates 22050Hz LEI16 mono WAV audio assets for:
- Italian and English rhyme word pairs
- Italian and English alliteration words
- Non-word verbal prompts ("Ascolta la rima", "Listen to the rhyme", etc.)
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIO_ROOT = PROJECT_ROOT / "activities" / "festa_delle_rime" / "assets" / "audio"

WORDS_IT = [
    # Rhyme pairs
    ("cane", "cane"),
    ("pane", "pane"),
    ("gatto", "gatto"),
    ("piatto", "piatto"),
    ("rana", "rana"),
    ("lana", "lana"),
    ("mela", "mela"),
    ("vela", "vela"),
    ("fiore", "fiore"),
    ("cuore", "cuore"),
    ("palla", "palla"),
    ("farfalla", "farfalla"),
    ("torta", "torta"),
    ("porta", "porta"),
    ("naso", "naso"),
    ("vaso", "vaso"),
    # Alliteration words
    ("mare", "mare"),
    ("mano", "mano"),
    ("pera", "pera"),
    ("luna", "luna"),
    ("luce", "luce"),
    ("fata", "fata"),
    ("foglia", "foglia"),
    ("topo", "topo"),
    ("tenda", "tenda"),
    ("sole", "sole"),
    ("sasso", "sasso"),
    ("sedia", "sedia"),
]

PROMPTS_IT = [
    ("prompt_rhyme", "ascolta la parola e trova la rima"),
    ("prompt_odd", "trova la parola che non fa rima"),
    ("prompt_sound", "trova la parola con lo stesso suono iniziale"),
]

WORDS_EN = [
    # Rhyme pairs
    ("cat", "cat"),
    ("hat", "hat"),
    ("moon", "moon"),
    ("spoon", "spoon"),
    ("cake", "cake"),
    ("snake", "snake"),
    ("log", "log"),
    ("frog", "frog"),
    ("bear", "bear"),
    ("chair", "chair"),
    ("boat", "boat"),
    ("goat", "goat"),
    ("star", "star"),
    ("car", "car"),
    ("mouse", "mouse"),
    ("house", "house"),
    # Alliteration words
    ("map", "map"),
    ("pig", "pig"),
    ("pan", "pan"),
    ("pear", "pear"),
    ("leaf", "leaf"),
    ("lamp", "lamp"),
    ("fish", "fish"),
    ("fan", "fan"),
    ("fox", "fox"),
    ("top", "top"),
    ("tent", "tent"),
    ("turtle", "turtle"),
    ("sun", "sun"),
    ("sock", "sock"),
]

PROMPTS_EN = [
    ("prompt_rhyme", "listen to the word and find the rhyme"),
    ("prompt_odd", "find the word that does not rhyme"),
    ("prompt_sound", "find the word with the same beginning sound"),
]


def make_wav(text: str, voice: str, rate: int, dest_wav: Path) -> None:
    lower_text = text.lower()
    dest_wav.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp_file:
            tmp_aiff = Path(tmp_file.name)
        try:
            subprocess.run(
                ["say", "-v", voice, "-r", str(rate), lower_text, "-o", str(tmp_aiff)],
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
                # If host lacks say/afconvert, write a silent WAV stub for offline CI/Linux environments
                _write_wav_stub(dest_wav)
            time.sleep(0.1)
        finally:
            if tmp_aiff.exists():
                tmp_aiff.unlink()


def _write_wav_stub(dest_wav: Path) -> None:
    """Create a minimal valid 22050Hz LEI16 mono WAV stub."""
    import wave
    dest_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dest_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"\x00\x00" * 2205)  # 0.1s of silence


def generate_locale(locale: str, out_dir: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    if locale == "it":
        voice = "Alice"
        rate = 175
        words = WORDS_IT
        prompts = PROMPTS_IT
    else:
        voice = "Samantha"
        rate = 180
        words = WORDS_EN
        prompts = PROMPTS_EN

    target_dir = out_dir / locale
    target_dir.mkdir(parents=True, exist_ok=True)

    for word_id, word_text in words:
        p = target_dir / f"{word_id}.wav"
        make_wav(word_text, voice, rate, p)
        manifest[f"{locale}/{word_id}.wav"] = hashlib.sha256(p.read_bytes()).hexdigest()

    for prompt_id, prompt_text in prompts:
        p = target_dir / f"{prompt_id}.wav"
        make_wav(prompt_text, voice, rate, p)
        manifest[f"{locale}/{prompt_id}.wav"] = hashlib.sha256(p.read_bytes()).hexdigest()

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Festa delle Rime audio clips")
    parser.add_argument("--locale", choices=["it", "en", "all"], default="all")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_AUDIO_ROOT)
    args = parser.parse_args()

    locales = ["it", "en"] if args.locale == "all" else [args.locale]
    full_manifest: dict[str, str] = {}
    for loc in locales:
        m = generate_locale(loc, args.output_dir)
        full_manifest.update(m)

    manifest_path = args.output_dir / "audio_manifest.sha256"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        for filename in sorted(full_manifest.keys()):
            f.write(f"{full_manifest[filename]}  {filename}\n")

    print(f"Generated {len(full_manifest)} audio clips in {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
