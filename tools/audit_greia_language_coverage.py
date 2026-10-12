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
import json
from pathlib import Path
import sys
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


def _report_activity(root: Path, errors: list[str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    dirs = sorted(
        path for path in (root / "activities").iterdir()
        if path.is_dir() and (path / "activity.toml").is_file()
    )
    summary: dict[str, Any] = {}
    cues: list[dict[str, Any]] = []
    for activity in dirs:
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
        summary[activity.name] = entry
    return summary, cues


def _report_launcher_labels(root: Path, errors: list[str]) -> list[dict[str, Any]]:
    base = root / "assets/audio/system/launcher-labels"
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
            for statement in parsed.body:
                if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                    target = statement.targets[0]
                    if isinstance(target, ast.Name) and target.id in wanted:
                        value = ast.literal_eval(statement.value)
                        names = (value,) if isinstance(value, str) else value
                        expected.update(names)
                        seen.add(target.id)
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
            results.append({
                "source": "assets/audio/system/launcher-labels",
                "locale": locale, "cue_id": f"collection.{name}",
                "caption_key": f"collection.{name}",
                "text": None,
                "path": str(actual.relative_to(root)) if actual else
                        f"assets/audio/system/launcher-labels/{locale}/{name}.wav",
                "file_exists": actual is not None,
                "state": "EXISTING_ASSET_NEEDS_REVIEW" if actual else "BLOCKED_TEXT",
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
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
    print(json.dumps({
        "report": str(args.output), "status": report["status"],
        "activities": len(report["activities"]),
        "summary": report["summary"],
        "structural_errors": len(report["structural_errors"]),
    }, ensure_ascii=False))
    return 2 if report["structural_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
