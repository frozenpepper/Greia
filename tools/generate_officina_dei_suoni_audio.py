#!/usr/bin/env python3
"""Prepare Officina dei Suoni speech through Greia VoiceEngine.

Phonemes and vocabulary are pronunciation-authoritative pedagogical speech. Generic
instructions are Dani system speech. The historical Activity-local synthetic-tone,
macOS ``say`` and FFmpeg fallback implementation is intentionally removed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_CLI = PROJECT_ROOT / "tools" / "greia_voice.py"
DEFAULT_REVIEW_DIR = PROJECT_ROOT / "tmp" / "voice-review" / "officina_dei_suoni"

SOUNDS_IT = {"sound_m": "mm", "sound_p": "p", "sound_l": "ll", "sound_f": "ff", "sound_t": "t", "sound_s": "ss", "sound_r": "rr", "sound_c": "k"}
SOUNDS_EN = {"sound_m": "mm", "sound_p": "p", "sound_l": "ll", "sound_f": "ff", "sound_t": "t", "sound_s": "ss", "sound_b": "b", "sound_c": "k"}

WORDS_IT = {
    "mela": "mela", "mare": "mare", "mano": "mano", "pane": "pane", "pera": "pera", "palla": "palla",
    "lana": "lana", "luna": "luna", "luce": "luce", "fiore": "fiore", "fata": "fata", "foglia": "foglia",
    "torta": "torta", "topo": "topo", "tenda": "tenda", "sole": "sole", "sasso": "sasso", "sedia": "sedia",
    "rana": "rana", "rosa": "rosa", "ramo": "ramo", "cane": "cane", "casa": "casa", "cuore": "cuore",
}
PROMPTS_IT = {
    "prompt_find_sound": "Ascolta il suono e trova l'immagine!",
    "prompt_first_sound": "Qual è il suono iniziale?",
    "prompt_build_word": "Metti la lettera per formare la parola!",
}
WORDS_EN = {
    "moon": "moon", "map": "map", "mouse": "mouse", "pig": "pig", "pan": "pan", "pear": "pear",
    "leaf": "leaf", "lamp": "lamp", "log": "log", "fish": "fish", "fan": "fan", "fox": "fox",
    "top": "top", "tent": "tent", "turtle": "turtle", "sun": "sun", "sock": "sock", "star": "star",
    "bear": "bear", "boat": "boat", "book": "book", "cat": "cat", "car": "car", "cake": "cake",
}
PROMPTS_EN = {
    "prompt_find_sound": "Listen to the sound and find the picture!",
    "prompt_first_sound": "What is the beginning sound?",
    "prompt_build_word": "Place the letter to build the word!",
}


def _output_path(review_dir: Path, locale: str, cue_id: str) -> str:
    output = review_dir / locale / f"{cue_id}.wav"
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

    requests: list[dict[str, object]] = []
    for locale, sounds, words, prompts in (
        ("it", SOUNDS_IT, WORDS_IT, PROMPTS_IT),
        ("en", SOUNDS_EN, WORDS_EN, PROMPTS_EN),
    ):
        for cue_id, text in {**sounds, **words}.items():
            requests.append(
                {
                    "speaker": "pedagogical",
                    "kind": "pedagogical_speech",
                    "locale": locale,
                    "text": text,
                    "cue_id": f"officina_dei_suoni.{cue_id}",
                    "output": _output_path(review_dir, locale, cue_id),
                    "verification": "off",
                    "max_attempts": 1,
                }
            )
        for cue_id, text in prompts.items():
            requests.append(
                {
                    "speaker": "dani",
                    "kind": "dani_system_speech",
                    "locale": locale,
                    "text": text,
                    "cue_id": f"officina_dei_suoni.{cue_id}",
                    "output": _output_path(review_dir, locale, cue_id),
                    "verification": "off",
                    "max_attempts": 1,
                }
            )

    batch_path = review_dir / "voice_requests.jsonl"
    batch_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in requests), encoding="utf-8"
    )
    result = subprocess.run(
        [sys.executable, str(VOICE_CLI), "batch", "--input", str(batch_path)], cwd=PROJECT_ROOT
    )
    if result.returncode == 0:
        print(f"Generated {len(requests)} review candidates under {review_dir}")
        print("Human listening review is required before Activity integration.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
