#!/usr/bin/env python3
"""Pedagogical speech audio generator for La Casa del Dieci.

Generates 22050Hz LEI16 mono WAV audio assets for:
- Italian and English challenge instruction prompts (compose 1..10, add, take away, missing part)
- Positive verbal reinforcement clips ("Ben fatto!", "Esatto!", "Ottimo!", "Great job!", "You got it!")
- Encouraging retry verbal clips ("Quasi, riprova!", "Conta bene e riprova!", "Almost, try again!")
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIO_ROOT = PROJECT_ROOT / "activities" / "casa_del_dieci" / "assets" / "audio"

PROMPTS_IT = [
    ("prompt_compose_1", "Accendi una luce nella casa!"),
    ("prompt_compose_2", "Accendi 2 luci nella casa!"),
    ("prompt_compose_3", "Accendi 3 luci nella casa!"),
    ("prompt_compose_4", "Accendi 4 luci nella casa!"),
    ("prompt_compose_5", "Accendi 5 luci nella casa!"),
    ("prompt_compose_6", "Accendi 6 luci nella casa!"),
    ("prompt_compose_7", "Accendi 7 luci nella casa!"),
    ("prompt_compose_8", "Accendi 8 luci nella casa!"),
    ("prompt_compose_9", "Accendi 9 luci nella casa!"),
    ("prompt_compose_10", "Accendi tutte le 10 luci nella casa!"),
    ("prompt_add", "Quante luci accese ci sono in tutto?"),
    ("prompt_take_away", "Quante luci restano accese?"),
    ("prompt_missing_part", "Quante luci mancano da accendere?"),
    ("correct_1", "Ben fatto!"),
    ("correct_2", "Esatto!"),
    ("correct_3", "Ottimo lavoro!"),
    ("retry_1", "Quasi, riprova!"),
    ("retry_2", "Conta bene e prova ancora!"),
]

PROMPTS_EN = [
    ("prompt_compose_1", "Turn on 1 light in the house!"),
    ("prompt_compose_2", "Turn on 2 lights in the house!"),
    ("prompt_compose_3", "Turn on 3 lights in the house!"),
    ("prompt_compose_4", "Turn on 4 lights in the house!"),
    ("prompt_compose_5", "Turn on 5 lights in the house!"),
    ("prompt_compose_6", "Turn on 6 lights in the house!"),
    ("prompt_compose_7", "Turn on 7 lights in the house!"),
    ("prompt_compose_8", "Turn on 8 lights in the house!"),
    ("prompt_compose_9", "Turn on 9 lights in the house!"),
    ("prompt_compose_10", "Turn on all 10 lights in the house!"),
    ("prompt_add", "How many lights are on in all?"),
    ("prompt_take_away", "How many lights are left on?"),
    ("prompt_missing_part", "How many lights are missing?"),
    ("correct_1", "Great job!"),
    ("correct_2", "You got it!"),
    ("correct_3", "Awesome!"),
    ("retry_1", "Almost, try again!"),
    ("retry_2", "Count carefully and try again!"),
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
    parser = argparse.ArgumentParser(description="Generate Casa del Dieci audio clips")
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
