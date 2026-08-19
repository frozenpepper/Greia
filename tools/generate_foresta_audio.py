#!/usr/bin/env python3
"""Audio generator for Foresta delle Parole.

IMPORTANT RULE:
Always pass lowercase strings to TTS so macOS say never speaks 'maiuscola' or 'capital'.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from activities.foresta_parole.main import PHONICS_DATA

AUDIO_ROOT = PROJECT_ROOT / "activities" / "foresta_parole" / "assets" / "audio"
TMP_AIFF = Path("/tmp/greia_speech_gen.aiff")


def make_wav(text: str, voice: str, rate: int, dest_wav: Path) -> None:
    # Always ensure text is lowercase to prevent TTS 'maiuscola' / 'capital' announcements
    lower_text = text.lower()
    subprocess.run(["say", "-v", voice, "-r", str(rate), lower_text, "-o", str(TMP_AIFF)], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@22050", "-c", "1", str(TMP_AIFF), str(dest_wav)], check=True)


def generate_all() -> None:
    # Italian (Alice, 180 wpm)
    it_dir = AUDIO_ROOT / "it"
    it_dir.mkdir(parents=True, exist_ok=True)
    for letter, letter_id, prompt_id, word_display, emoji, word_stem in PHONICS_DATA["it"]:
        make_wav(f"{letter} come {word_display}", "Alice", 180, it_dir / f"{prompt_id}.wav")
        make_wav(letter, "Alice", 175, it_dir / f"{letter_id}.wav")
        make_wav(word_display, "Alice", 175, it_dir / f"{word_stem}.wav")

    make_wav("Bravissima!", "Alice", 180, it_dir / "bravissima.wav")
    make_wav("Fantastico!", "Alice", 180, it_dir / "fantastico.wav")
    make_wav("Ottimo!", "Alice", 180, it_dir / "ottimo.wav")

    # English (Samantha, 185 wpm)
    en_dir = AUDIO_ROOT / "en"
    en_dir.mkdir(parents=True, exist_ok=True)
    for letter, letter_id, prompt_id, word_display, emoji, word_stem in PHONICS_DATA["en"]:
        make_wav(f"{letter} as {word_display}", "Samantha", 185, en_dir / f"{prompt_id}.wav")
        make_wav(letter, "Samantha", 180, en_dir / f"{letter_id}.wav")
        make_wav(word_display, "Samantha", 180, en_dir / f"{word_stem}.wav")

    make_wav("Great job!", "Samantha", 185, en_dir / "great_job.wav")
    make_wav("Wonderful!", "Samantha", 185, en_dir / "wonderful.wav")
    make_wav("You did it!", "Samantha", 185, en_dir / "you_did_it.wav")

    print("Audio files generated cleanly with lowercase inputs!")


if __name__ == "__main__":
    generate_all()
