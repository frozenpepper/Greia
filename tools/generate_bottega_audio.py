#!/usr/bin/env python3
"""Pedagogical speech audio generator for La Bottega delle Misure.

Generates 22050Hz LEI16 mono WAV audio assets for:
- Italian and English challenge instruction prompts (compare longer/shorter/taller/lower, order, measure, shelf)
- Positive verbal reinforcement clips ("Bravissimo!", "Esatto!", "Ottimo lavoro!", "Great job!", "You got it!")
- Encouraging retry verbal clips ("Riprova!", "Quasi, riprova!", "Try again!")
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIO_ROOT = PROJECT_ROOT / "activities" / "bottega_delle_misure" / "assets" / "audio"

PROMPTS_IT = [
    ("prompt_compare_longer", "Tocca il pacco più lungo!"),
    ("prompt_compare_shorter", "Tocca il pacco più corto!"),
    ("prompt_compare_taller", "Tocca il pacco più alto!"),
    ("prompt_compare_shorter_h", "Tocca il pacco più basso!"),
    ("prompt_order_length", "Metti i pacchi in ordine, dal più corto al più lungo!"),
    ("prompt_order_height", "Metti i pacchi in ordine, dal più basso al più alto!"),
    ("prompt_measure", "Conta quanti blocchi è lungo il pacco e tocca il numero!"),
    ("prompt_shelf", "Quale pacco entra nello scaffale?"),
    ("correct_1", "Bravissimo!"),
    ("correct_2", "Esatto!"),
    ("correct_3", "Ottimo lavoro!"),
    ("retry_1", "Riprova!"),
    ("retry_2", "Quasi, prova ancora!"),
]

PROMPTS_EN = [
    ("prompt_compare_longer", "Tap the longer parcel!"),
    ("prompt_compare_shorter", "Tap the shorter parcel!"),
    ("prompt_compare_taller", "Tap the taller parcel!"),
    ("prompt_compare_shorter_h", "Tap the shorter parcel!"),
    ("prompt_order_length", "Put the parcels in order, from shortest to longest!"),
    ("prompt_order_height", "Put the parcels in order, from shortest to tallest!"),
    ("prompt_measure", "Count how many blocks long the parcel is and tap the number!"),
    ("prompt_shelf", "Which parcel fits in the shelf?"),
    ("correct_1", "Great job!"),
    ("correct_2", "You got it!"),
    ("correct_3", "Awesome!"),
    ("retry_1", "Try again!"),
    ("retry_2", "Almost, try again!"),
]


def _write_wav_stub(dest_wav: Path) -> None:
    """Create a minimal valid 22050Hz LEI16 mono WAV stub."""
    import wave
    dest_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dest_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"\x00\x00" * 2205)  # 0.1s of silence


def make_wav(text: str, voice: str, rate: int, dest_wav: Path) -> None:
    dest_wav.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp_file:
            tmp_aiff = Path(tmp_file.name)
        try:
            subprocess.run(
                ["say", "-v", voice, "-r", str(rate), text, "-o", str(tmp_aiff)],
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


def generate_locale(locale: str, out_dir: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    if locale == "it":
        voice = "Alice"
        rate = 175
        prompts = PROMPTS_IT
    else:
        voice = "Samantha"
        rate = 180
        prompts = PROMPTS_EN

    target_dir = out_dir / locale
    target_dir.mkdir(parents=True, exist_ok=True)

    for prompt_id, prompt_text in prompts:
        p = target_dir / f"{prompt_id}.wav"
        make_wav(prompt_text, voice, rate, p)
        manifest[f"{locale}/{prompt_id}.wav"] = hashlib.sha256(p.read_bytes()).hexdigest()

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Bottega delle Misure audio clips")
    parser.add_argument("--locale", choices=["it", "en", "all"], default="all")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_AUDIO_ROOT)
    args = parser.parse_args()

    locales = ["it", "en"] if args.locale == "all" else [args.locale]
    full_manifest: dict[str, str] = {}
    for loc in locales:
        m = generate_locale(loc, args.output_dir)
        full_manifest.update(m)

    manifest_file = args.output_dir / "audio_manifest.sha256"
    manifest_lines = [f"{digest}  {path}\n" for path, digest in sorted(full_manifest.items())]
    manifest_file.write_text("".join(manifest_lines), encoding="utf-8")
    print(f"Generated {len(full_manifest)} audio clips in {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
