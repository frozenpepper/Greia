#!/usr/bin/env python3
"""Source-side text/audio census for Greia's four-language rollout.

This script is intentionally an inventory, NOT an acceptance validator.
It reports missing locale bundles and declared audio cues without faking
production voice needs from every text label. Legacy voices loaded from code
are explicitly emitted as manual-review owners and must be reconciled.
No model/API/runtime Pygame dependency and no network; writes only --output.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path
import sys
import tomllib
from typing import Any

LOCALES = ("en", "it", "es", "fr")
SOURCE_LOCALES = ("en", "it")
SPEECH_EXTENSIONS = {".wav", ".ogg"}


def _load_bundle(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(f"{path}: invalid locale JSON: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{path}: bundle must be an object")
        return None
    if data.get("locale") != path.stem:
        errors.append(f"{path}: locale tag does not match filename")
    if not isinstance(data.get("strings"), dict):
        errors.append(f"{path}: strings must be an object")
        data["strings"] = {}
    if not isinstance(data.get("audio", {}), dict):
        errors.append(f"{path}: audio must be an object")
        data["audio"] = {}
    return data


def _audio_asset(root: Path, rel: str | None) -> tuple[str, bool]:
    if not rel:
        return "", False
    path = Path(rel)
    if path.is_absolute() or ".." in path.parts or path.suffix.lower() not in SPEECH_EXTENSIONS:
        return rel, False
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()):
        return rel, False
    return rel, target.is_file()


def _foresta_lesson_audio(root: Path, errors: list[str]) -> list[dict[str, Any]]:
    """Inventory code-owned phonics audio as explicit candidate cues.

    The Word Forest's actual runtime uses foresta_content.PHONICS_DATA,
    not the locale JSON's audio table. Parse only a literal data assignment;
    never import pygame/game code or invent a phoneme/prompt transcript.
    """
    package = root / "activities" / "foresta_parole"
    path = package / "foresta_content.py"
    if not path.is_file():
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        definitions = [
            node for node in tree.body
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "PHONICS_DATA"
        ]
        if len(definitions) != 1:
            raise ValueError("expected one literal PHONICS_DATA")
        rows = ast.literal_eval(definitions[0].value)
        if not isinstance(rows, dict):
            raise ValueError("PHONICS_DATA must be a locale dictionary")
    except (SyntaxError, ValueError, TypeError, OSError, UnicodeError) as exc:
        errors.append(f"{path}: cannot inventory Word Forest phonics: {exc}")
        return []

    cues: list[dict[str, Any]] = []
    for locale in LOCALES:
        lessons = rows.get(locale)
        if not isinstance(lessons, list) or not lessons:
            errors.append(f"{path}: missing phonics lessons for {locale}")
            continue
        seen: set[str] = set()
        for lesson in lessons:
            if (not isinstance(lesson, (tuple, list)) or len(lesson) != 6
                    or any(not isinstance(field, str) or not field for field in lesson)):
                errors.append(f"{path}: malformed {locale} phonics lesson")
                continue
            letter, letter_stem, prompt_stem, word, _emoji, word_stem = lesson
            # Prevent a malformed code catalogue from manufacturing unsafe
            # candidate recording output destinations.
            names = (letter_stem, prompt_stem, word_stem)
            if any(not item.isascii() or not item.replace("_", "").isalnum()
                   or item != item.lower() for item in names):
                errors.append(f"{path}: unsafe {locale} phonics audio stem")
                continue
            if not word.casefold().startswith(letter.casefold()):
                errors.append(f"{path}: {locale} example {word!r} does not begin with {letter}")
                continue
            for kind, stem, script in (
                ("letter", letter_stem, None),
                ("prompt", prompt_stem, None),
                ("word", word_stem, word),
            ):
                cue_id = f"phonics.{kind}.{stem}"
                if cue_id in seen:
                    errors.append(f"{path}: duplicate {locale}/{cue_id}")
                    continue
                seen.add(cue_id)
                rel = f"assets/audio/{locale}/{stem}.wav"
                _, exists = _audio_asset(package, rel)
                cues.append({
                    "source": "activities/foresta_parole",
                    "locale": locale,
                    "cue_id": cue_id,
                    "caption_key": f"phonics.{letter_stem}" if kind == "word" else None,
                    # Prompt recordings may teach phoneme vs letter name;
                    # no authoritative spoken script is currently declared.
                    "text": script,
                    "path": rel,
                    "file_exists": exists,
                    "state": (
                        "BLOCKED_TEXT" if not script else
                        "EXISTING_ASSET_NEEDS_REVIEW" if exists else "MISSING_AUDIO"
                    ),
                    "speaker": "UNASSIGNED",
                    "kind": "UNASSIGNED",
                })
    return cues


def _report_activity(root: Path, errors: list[str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    dirs = sorted(
        path for path in (root / "activities").iterdir()
        if path.is_dir() and (path / "activity.toml").is_file()
    )
    summary: dict[str, Any] = {}
    cues: list[dict[str, Any]] = []
    for activity in dirs:
        try:
            manifest = tomllib.loads(
                (activity / "activity.toml").read_text(encoding="utf-8")
            )
            declaration = manifest.get("activity", {}).get("languages", [])
            if not isinstance(declaration, list) or any(
                not isinstance(item, str) for item in declaration
            ):
                errors.append(f"{activity.name}: invalid Activity language declaration")
                declaration = []
            supported_locales = tuple(declaration)
        except (OSError, UnicodeError, tomllib.TOMLDecodeError, AttributeError) as exc:
            errors.append(f"{activity.name}: cannot read Activity language declaration: {exc}")
            supported_locales = ()
        bundles = {
            locale: _load_bundle(activity / "locales" / f"{locale}.json", errors)
            for locale in LOCALES
        }
        reference_keys = set().union(*(
            set((bundles[locale] or {}).get("strings", {}))
            for locale in SOURCE_LOCALES
        ))
        reference_audio = set().union(*(
            set((bundles[locale] or {}).get("audio", {}))
            for locale in SOURCE_LOCALES
        ))
        entry: dict[str, Any] = {
            "locale_text": {}, "locale_audio": {}, "source_strings": len(reference_keys),
            "source_spoken_keys": len(reference_audio),
            "audio_modules_to_review": [],
            # Source bundle presence is not a claim of supported product locale.
            "advertised_languages": list(supported_locales),
        }
        for file in sorted(activity.rglob("*.py")):
            try:
                source = file.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                errors.append(f"{file}: {exc}")
                continue
            if any(token in source for token in (
                "play_voice", "voice_cue", ".wav", ".ogg", "tts", "speak("
            )):
                entry["audio_modules_to_review"].append(str(file.relative_to(root)))
        for locale in LOCALES:
            bundle = bundles[locale]
            strings = bundle.get("strings", {}) if bundle is not None else {}
            audio = bundle.get("audio", {}) if bundle is not None else {}
            missing_keys = sorted(reference_keys - set(strings))
            missing_audio_mappings = sorted(reference_audio - set(audio))
            entry["locale_text"][locale] = {
                "bundle_exists": bundle is not None,
                "present_keys": len(strings),
                "missing_reference_keys": missing_keys,
                "advertised_by_manifest": locale in supported_locales,
                # Text-key parity is not reviewed translation, playable
                # language curriculum or verified narration.
                "stage": (
                    "NO_BUNDLE" if bundle is None else
                    "INCOMPLETE_TEXT_KEYS" if missing_keys else
                    "SOURCE_TEXT_KEYS_ONLY"
                ),
            }
            audio_missing: list[str] = []
            for cue_id in sorted(reference_audio):
                binding = audio.get(cue_id)
                if not isinstance(binding, dict):
                    audio_missing.append(cue_id)
                    cues.append({
                        "source": str(activity.relative_to(root)),
                        "locale": locale, "cue_id": cue_id,
                        "caption_key": cue_id, "text": strings.get(cue_id),
                        "path": None, "file_exists": False,
                        "state": "BLOCKED_TEXT" if cue_id not in strings else "MISSING_MAPPING",
                        "speaker": "UNASSIGNED", "kind": "UNASSIGNED",
                    })
                    continue
                caption = binding.get("caption_key", cue_id)
                if not isinstance(caption, str):
                    errors.append(f"{activity.name}/{locale}/{cue_id}: invalid caption_key")
                    caption = cue_id
                path_value = binding.get("path")
                path_string, exists = _audio_asset(
                    activity, path_value if isinstance(path_value, str) else None
                )
                if not exists:
                    audio_missing.append(cue_id)
                cues.append({
                    "source": str(activity.relative_to(root)),
                    "locale": locale, "cue_id": cue_id,
                    "caption_key": caption,
                    "text": strings.get(caption),
                    "path": path_string or None,
                    "file_exists": exists,
                    "state": (
                        "BLOCKED_TEXT" if not isinstance(strings.get(caption), str)
                        or not str(strings.get(caption)).strip()
                        else "EXISTING_ASSET_NEEDS_REVIEW" if exists
                        else "MISSING_AUDIO"
                    ),
                    "speaker": "UNASSIGNED", "kind": "UNASSIGNED",
                })
            entry["locale_audio"][locale] = {
                "mapped_cues": len(audio),
                "missing_reference_mappings": missing_audio_mappings,
                "missing_or_invalid_files": audio_missing,
            }
        if activity.name == "foresta_parole":
            # Not present in the Activity's locale audio declarations:
            # code owns letter, find-letter prompt, and example-word playback.
            runtime_cues = _foresta_lesson_audio(root, errors)
            cues.extend(runtime_cues)
            entry["code_owned_phonics_audio"] = {
                locale: sum(1 for cue in runtime_cues if cue["locale"] == locale)
                for locale in LOCALES
            }
        summary[activity.name] = entry
    return summary, cues


def _report_launcher_labels(root: Path, errors: list[str]) -> list[dict[str, Any]]:
    base = root / "assets/audio/system/launcher-labels"
    label_text: dict[str, dict[str, str]] = {}
    expected = {
        file.stem
        for locale in SOURCE_LOCALES
        for suffix in SPEECH_EXTENSIONS
        for file in (base / locale).glob(f"*{suffix}")
    }
    # Read the platform-owned vocabulary from static declarations in the
    # canonical source, not only from files that happen to exist. Otherwise
    # missing clips (notably my_creations.wav) vanish from the inventory.
    catalogue = root / "src/greia_launcher/catalogue_view.py"
    if catalogue.is_file():
        try:
            parsed = ast.parse(catalogue.read_text(encoding="utf-8"))
            wanted = {
                "BROWSE_ACTIVITIES_ID", "MY_CREATIONS_PORTAL_ID",
                "PRIMARY_COLLECTION_IDS", "DISCOVERY_GROUP_IDS",
            }
            seen: set[str] = set()
            source_names: dict[str, str | tuple[str, ...]] = {}
            for statement in parsed.body:
                if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                    target = statement.targets[0]
                    if isinstance(target, ast.Name) and target.id in wanted:
                        value = ast.literal_eval(statement.value)
                        names = (value,) if isinstance(value, str) else value
                        source_names[target.id] = value
                        expected.update(names)
                        seen.add(target.id)
            # These are purely source-declared translations, read as AST
            # literals. No app imports, side effects, eval() or network.
            for statement in parsed.body:
                if not isinstance(statement, ast.AnnAssign) or not isinstance(statement.target, ast.Name):
                    continue
                if statement.target.id not in {"_CATEGORY_TRANSLATIONS", "_DISCOVERY_TRANSLATIONS"}:
                    continue
                if not isinstance(statement.value, ast.Dict):
                    errors.append(f"{catalogue}: translations must be a literal dict")
                    continue
                for key_node, translations_node in zip(statement.value.keys, statement.value.values):
                    if isinstance(key_node, ast.Name):
                        key = source_names.get(key_node.id)
                    else:
                        key = ast.literal_eval(key_node)
                    values = ast.literal_eval(translations_node)
                    if isinstance(key, str) and isinstance(values, dict):
                        label_text[key] = {
                            lang: value for lang, value in values.items()
                            if isinstance(lang, str) and isinstance(value, str)
                        }
            if seen != wanted:
                errors.append(f"{catalogue}: incomplete source collection vocabulary: {sorted(wanted - seen)}")
        except (OSError, UnicodeError, SyntaxError, ValueError, TypeError) as exc:
            errors.append(f"{catalogue}: cannot audit source collection vocabulary: {exc}")
    expected_names = sorted(expected)
    results = []
    for name in expected_names:
        for locale in LOCALES:
            wav = base / locale / f"{name}.wav"
            ogg = base / locale / f"{name}.ogg"
            actual = wav if wav.is_file() else ogg if ogg.is_file() else None
            source_text = label_text.get(name, {}).get(locale)
            results.append({
                "source": "assets/audio/system/launcher-labels",
                "locale": locale, "cue_id": f"collection.{name}",
                "caption_key": f"collection.{name}",
                "text": source_text,
                "path": str(actual.relative_to(root)) if actual else
                        f"assets/audio/system/launcher-labels/{locale}/{name}.wav",
                "file_exists": actual is not None,
                "state": "EXISTING_ASSET_NEEDS_REVIEW" if actual else
                         "MISSING_AUDIO" if source_text else "BLOCKED_TEXT",
                "speaker": "UNASSIGNED", "kind": "UNASSIGNED",
            })
    return results


def build_inventory(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    activities, spoken = _report_activity(root, errors)
    spoken.extend(_report_launcher_labels(root, errors))
    counts = {
        locale: {
            "activity_bundles": sum(
                1 for a in activities.values() if a["locale_text"][locale]["bundle_exists"]
            ),
            "activity_keys_missing": sum(
                len(a["locale_text"][locale]["missing_reference_keys"])
                for a in activities.values()
            ),
            "text_key_complete_bundles": sum(
                1 for a in activities.values()
                if a["locale_text"][locale]["stage"] == "SOURCE_TEXT_KEYS_ONLY"
            ),
            "advertised_activity_locales": sum(
                1 for a in activities.values()
                if a["locale_text"][locale]["advertised_by_manifest"]
            ),
            "audio_inventory_rows": sum(1 for item in spoken if item["locale"] == locale),
            "audio_missing_or_unmapped": sum(
                1 for item in spoken
                if item["locale"] == locale and not item["file_exists"]
            ),
        }
        for locale in LOCALES
    }
    return {
        "schema_version": 1,
        "status": "SOURCE_INVENTORY_ONLY_NOT_SPEECH_ACCEPTANCE",
        "locales": list(LOCALES),
        "activities": activities,
        "spoken_resources": spoken,
        "summary": counts,
        "manual_inventory_required": [
            "Orca/Stars/other runtime-loaded character voice modules",
            "System/Parent/Shell spoken prompts and unbundled voice libraries",
            "Encyclopedia, character shared utterances, and content-language cues",
            "Inline literal UI strings beyond the locale bundle catalogue",
        ],
        "structural_errors": errors,
    }




_LEDGER_COLUMNS = (
    "source", "locale", "speaker", "kind", "cue_id", "exact_text",
    "caption_key", "output_path", "existing_asset_sha256", "state",
    "provider", "receipt_path", "asr_result", "human_review", "notes",
)


def write_recording_ledger(root: Path, report: dict[str, Any], output: Path) -> int:
    """Produce exact-script candidates without inventing voice speakers.

    Actual approvals/receipts are never inferred from a file's existence.
    Rows needing an author-approved voice or transcript remain blocked.
    Custom Python-loaded cues are explicitly outside this mechanical census.
    """
    rows: list[dict[str, str]] = []
    for item in sorted(
        report["spoken_resources"],
        key=lambda entry: (entry["source"], entry["locale"], entry["cue_id"]),
    ):
        locale = item["locale"]
        source = item["source"]
        cue = item["cue_id"]
        text_value = item.get("text")
        text_value = text_value if isinstance(text_value, str) else ""
        media_path = item.get("path") or ""
        unsafe_declared_path = False
        # Never hand the recording agent a path outside the owning package.
        # Missing malformed paths need explicit authoring review, not a
        # synthesized destination for voice output.
        if media_path:
            candidate = Path(media_path)
            if candidate.is_absolute() or ".." in candidate.parts or chr(92) in media_path:
                unsafe_declared_path = True
                media_path = ""
        # Activity bundle audio paths are relative to the Activity package;
        # system launcher labels are already relative to project root.
        if media_path and source.startswith("activities/"):
            media_path = f"{source}/{media_path}"
        if not media_path and not unsafe_declared_path and cue == "activity.title" and source.startswith("activities/"):
            media_path = f"{source}/locales/{locale}/audio/activity-title.wav"
        digest = ""
        if item.get("file_exists") and media_path:
            path = (root / media_path).resolve()
            if path.is_file() and path.is_relative_to(root.resolve()):
                hasher = hashlib.sha256()
                with path.open("rb") as stream:
                    for block in iter(lambda: stream.read(65536), b""):
                        hasher.update(block)
                digest = hasher.hexdigest()
        state = (
            "BLOCKED_TEXT" if not text_value.strip()
            else "EXISTING_REVIEW_PENDING" if digest
            else "PATH_REVIEW_REQUIRED" if unsafe_declared_path or not media_path
            else "MISSING_AUDIO"
        )
        rows.append({
            "source": source,
            "locale": locale,
            "speaker": "UNASSIGNED",
            "kind": "UNASSIGNED",
            "cue_id": cue,
            "exact_text": text_value,
            "caption_key": item.get("caption_key") or "",
            "output_path": media_path,
            "existing_asset_sha256": digest,
            "state": state,
            "provider": "",
            "receipt_path": "",
            "asr_result": "",
            "human_review": "",
            "notes": (
                "Source inventory only; assign speaker/kind and review script"
                "; extra code-loaded speech still needs a separate scan"
            ),
        })
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_LEDGER_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--recording-ledger", type=Path,
        help="optional candidate CSV; no audio or provider calls",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not (root / "activities").is_dir():
        parser.error("Greia activities directory not found")
    report = build_inventory(root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    ledger_count = (
        write_recording_ledger(root, report, args.recording_ledger)
        if args.recording_ledger is not None else 0
    )
    print(json.dumps({
        "report": str(args.output), "status": report["status"],
        "recording_ledger": str(args.recording_ledger) if args.recording_ledger else None,
        "recording_candidate_rows": ledger_count,
        "activities": len(report["activities"]),
        "summary": report["summary"],
        "structural_errors": len(report["structural_errors"]),
    }, ensure_ascii=False))
    return 2 if report["structural_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
