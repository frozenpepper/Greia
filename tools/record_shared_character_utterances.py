#!/usr/bin/env python3
"""Produce Greia's shared character utterance library through VoiceEngine.

This is intentionally a thin semantic producer. It does not import Chatterbox,
Whisper, MLX, native TTS or FFmpeg directly; provider mechanics belong to
``tools/greia_voice_core``.

Generated clips remain human-review pending. This tool never marks shared audio
accepted merely because generation or ASR succeeds.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from greia_voice import build_engine
from greia_voice_core.locking import InterprocessGenerationLock, NullGenerationLock
from greia_voice_core.models import SpeechKind, VoiceRequest
from greia_voice_core.paths import voice_home

WORK_DIR = PROJECT_ROOT / "tmp" / "shared-character-utterances"

CHARACTERS = ("lilli", "leo", "flash", "tito", "momo", "dani")

PHRASES = {
    "it": {
        "praise.general": ["Complimenti!", "Ottimo lavoro!", "Ben fatto!"],
        "celebrate.success": ["Ce l'hai fatta!", "Evviva!", "Che meraviglia!"],
        "encourage.retry": ["Riproviamo!", "Quasi! Proviamo ancora!", "Ancora una volta!"],
        "encourage.progress": ["Continua così!", "Ci sei quasi!", "Vai avanti!"],
        "ready.go": ["Forza, andiamo!", "Ci siamo? Via!", "Si parte!"],
    },
    "en": {
        "praise.general": ["Congratulations!", "Great work!", "Well done!"],
        "celebrate.success": ["You did it!", "Hooray!", "Wonderful!"],
        "encourage.retry": ["Let's try again!", "Almost! Let's try again!", "One more time!"],
        "encourage.progress": ["Keep going!", "Almost there!", "You're doing great!"],
        "ready.go": ["Come on, let's go!", "Ready? Go!", "Here we go!"],
    },
}


def _selected_characters(raw: str) -> tuple[str, ...]:
    requested = tuple(part.strip().lower() for part in raw.split(",") if part.strip())
    unknown = sorted(set(requested) - set(CHARACTERS))
    if unknown:
        raise ValueError(f"unknown shared-utterance characters: {', '.join(unknown)}")
    if not requested:
        raise ValueError("at least one character must be selected")
    return requested


def _portable_path(path: Path) -> str:
    """Prefer repository-relative evidence paths without rejecting external workspaces."""
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path.resolve())


def _request(
    character: str,
    locale: str,
    family: str,
    variant: int,
    text: str,
    output: Path,
) -> VoiceRequest:
    return VoiceRequest(
        speaker=character,
        kind=SpeechKind.SHARED_CHARACTER_UTTERANCE,
        locale=locale,
        text=text,
        cue_id=f"shared.{family}.{variant:02d}",
        output=output,
        max_attempts=2,
    )


def _row(
    *,
    character: str,
    locale: str,
    family: str,
    variant: int,
    text: str,
    output: Path,
    result: str,
    notes: str,
) -> dict[str, object]:
    return {
        "character": character,
        "locale": locale,
        "family": family,
        "variant": variant,
        "text": text,
        "file": _portable_path(output),
        "result": result,
        "notes": notes,
    }


def run(output_root: Path, characters: tuple[str, ...]) -> list[dict[str, object]]:
    output_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []

    # Hold the global generation lock for the complete recording run so the
    # engine can keep its model warm without another process loading a second copy.
    with InterprocessGenerationLock(voice_home() / "generation.lock"):
        with build_engine(generation_lock=NullGenerationLock()) as engine:
            for character in characters:
                for locale, families in PHRASES.items():
                    for family, variants in families.items():
                        for variant, text in enumerate(variants, 1):
                            filename = f"{character}__{locale}__{family}__{variant:02d}.wav"
                            output = output_root / character / locale / filename
                            receipt = output.with_suffix(output.suffix + ".receipt.json")

                            if output.exists() or receipt.exists():
                                if output.is_file() and output.stat().st_size > 1000 and receipt.is_file():
                                    rows.append(
                                        _row(
                                            character=character,
                                            locale=locale,
                                            family=family,
                                            variant=variant,
                                            text=text,
                                            output=output,
                                            result="EXISTING_REVIEW_CANDIDATE",
                                            notes="not regenerated; inspect existing audio + receipt",
                                        )
                                    )
                                    continue
                                rows.append(
                                    _row(
                                        character=character,
                                        locale=locale,
                                        family=family,
                                        variant=variant,
                                        text=text,
                                        output=output,
                                        result="BLOCKED_PARTIAL_OUTPUT",
                                        notes="audio/receipt pair is incomplete; inspect before retry",
                                    )
                                )
                                continue

                            result = engine.generate(
                                _request(character, locale, family, variant, text, output)
                            )
                            notes = result.detail
                            verification = result.verification
                            notes = (
                                f"{notes}; verifier={verification.verifier_id}; "
                                f"verification={verification.disposition.value}; "
                                f"transcript={verification.transcript!r}; score={verification.score}"
                            )
                            rows.append(
                                _row(
                                    character=character,
                                    locale=locale,
                                    family=family,
                                    variant=variant,
                                    text=text,
                                    output=output,
                                    result=result.disposition.value,
                                    notes=notes,
                                )
                            )
                            print(
                                f"{character:5s} | {locale} | {family:18s} | "
                                f"v{variant:02d} -> {result.disposition.value}",
                                flush=True,
                            )

    return rows


def write_review_csv(output_root: Path, rows: list[dict[str, object]]) -> Path:
    path = output_root / "review.csv"
    fieldnames = [
        "character", "locale", "family", "variant", "text", "file", "result", "notes"
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Produce Greia shared character utterance review candidates through VoiceEngine"
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=WORK_DIR,
        help="review workspace (default: ./tmp/shared-character-utterances)",
    )
    parser.add_argument(
        "--characters",
        default=",".join(CHARACTERS),
        help="comma-separated subset; default: lilli,leo,flash,tito,momo,dani",
    )
    args = parser.parse_args(argv)

    output_root = args.output_root.resolve()
    characters = _selected_characters(args.characters)
    rows = run(output_root, characters)
    csv_path = write_review_csv(output_root, rows)

    failures = [
        row
        for row in rows
        if row["result"]
        not in {
            "REVIEW_REQUIRED",
            "REVIEW_REQUIRED_ASR_WARNING",
            "EXISTING_REVIEW_CANDIDATE",
        }
    ]
    print(f"Review CSV: {csv_path}", flush=True)
    print(
        f"Candidates: {len(rows) - len(failures)}; blocked/unavailable/rejected: {len(failures)}",
        flush=True,
    )
    print("Human listening review remains mandatory.", flush=True)
    return 0 if not failures else 2


if __name__ == "__main__":
    sys.exit(main())
