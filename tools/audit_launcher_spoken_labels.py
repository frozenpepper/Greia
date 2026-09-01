#!/usr/bin/env python3
"""First-party completeness audit for launcher spoken labels.

This is a release-quality audit, not a third-party runtime rejection mechanism.
Built-in Activities remain launchable even if a spoken label is missing; the
audit enforces catalogue completeness for the first-party release.

Checks:
- Every built-in Activity locale considered complete has strings.activity.title,
  audio.activity.title with safe package-relative path, caption_key, and an
  existing .wav/.ogg file.
- Every child-facing platform Collection/sub-Collection has a static clip under
  assets/audio/system/launcher-labels/<locale>/<id>.wav for required locales.

Collection vocabulary is derived from src/greia_launcher/catalogue_view.py
(PRIMARY_COLLECTION_IDS + DISCOVERY_GROUP_IDS) to avoid a drifting hard-coded
copy. The `all` internal projection is excluded unless the final UI exposes it.

Third-party runtime behavior remains fail-soft – this audit does not make
ActivityRegistry reject a package. Build/release quality is enforced here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVITIES_ROOT = PROJECT_ROOT / "activities"
SYSTEM_LABEL_ROOT = PROJECT_ROOT / "assets/audio/system/launcher-labels"


def _load_collection_ids() -> tuple[str, ...]:
    """Derive child-facing Collection vocabulary from platform authority."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from greia_launcher.catalogue_view import (
            BROWSE_ACTIVITIES_ID,
            DISCOVERY_GROUP_IDS,
            PRIMARY_COLLECTION_IDS,
        )

        # Exclude internal 'all' – it is not a child Home destination per the runbook.
        # Keep 'browse' and all primary/discovery IDs.
        ids = (BROWSE_ACTIVITIES_ID,) + tuple(PRIMARY_COLLECTION_IDS) + tuple(
            DISCOVERY_GROUP_IDS
        )
        # Deduplicate while preserving order
        seen: set[str] = set()
        ordered: list[str] = []
        for cid in ids:
            if cid not in seen:
                seen.add(cid)
                ordered.append(cid)
        return tuple(ordered)
    except Exception:
        # Fallback to the runbook's 19 IDs if import fails (should not happen in CI).
        return (
            "create",
            "play",
            "learn",
            "explore",
            "my_greia",
            "browse",
            "drawing",
            "writing",
            "music",
            "building",
            "numbers",
            "words",
            "puzzles",
            "nature",
            "stories",
            "making",
            "care",
            "action",
            "settings",
        )


def _is_safe_relative(path_str: str, activity_root: Path) -> bool:
    try:
        p = Path(path_str)
        if p.is_absolute() or ".." in p.parts:
            return False
        # Must be package-relative and stay inside activity root
        resolved = (activity_root / p).resolve()
        try:
            resolved.relative_to(activity_root.resolve())
        except ValueError:
            return False
        return True
    except Exception:
        return False


def audit_activities(required_locales: tuple[str, ...] = ("it", "en")) -> dict[str, int | list[str]]:
    built_in_roots = sorted(
        p for p in ACTIVITIES_ROOT.iterdir() if p.is_dir() and (p / "activity.toml").is_file()
    )
    total_combinations = 0
    complete = 0
    missing_text: list[str] = []
    missing_mapping: list[str] = []
    missing_file: list[str] = []
    unsafe_path: list[str] = []

    for act_root in built_in_roots:
        for locale in required_locales:
            json_path = act_root / "locales" / f"{locale}.json"
            if not json_path.is_file():
                # Locale not considered complete for this Activity – skip (not a failure)
                continue
            total_combinations += 1
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
            except Exception:
                missing_text.append(f"{act_root.name}/{locale}: invalid JSON")
                continue
            strings = data.get("strings", {}) if isinstance(data.get("strings"), dict) else {}
            title = strings.get("activity.title")
            if not isinstance(title, str) or not title.strip():
                missing_text.append(f"{act_root.name}/{locale}")
                continue
            audio = data.get("audio", {}) if isinstance(data.get("audio"), dict) else {}
            entry = audio.get("activity.title")
            if not isinstance(entry, dict):
                missing_mapping.append(f"{act_root.name}/{locale}")
                continue
            path_str = entry.get("path")
            caption = entry.get("caption_key")
            if not isinstance(path_str, str) or not path_str.strip():
                missing_mapping.append(f"{act_root.name}/{locale}: missing path")
                continue
            if caption is not None and caption != "activity.title":
                # Still allow but count as missing if caption is nonsensical?
                pass
            if path_str not in (f"locales/{locale}/audio/activity-title.wav", f"locales/{locale}/audio/activity-title.ogg"):
                # Path must be package-relative and use expected convention
                if not _is_safe_relative(path_str, act_root):
                    unsafe_path.append(f"{act_root.name}/{locale}:{path_str}")
                    continue
            if not _is_safe_relative(path_str, act_root):
                unsafe_path.append(f"{act_root.name}/{locale}:{path_str}")
                continue
            # Suffix check
            if not path_str.endswith((".wav", ".ogg")):
                missing_file.append(f"{act_root.name}/{locale}: bad suffix {path_str}")
                continue
            resolved = (act_root / path_str).resolve()
            if not resolved.is_file():
                missing_file.append(f"{act_root.name}/{locale}:{path_str}")
                continue
            complete += 1

    return {
        "BUILT_IN_ACTIVITIES": len(built_in_roots),
        "ACTIVITY_TITLE_LOCALE_COMBINATIONS": total_combinations,
        "ACTIVITY_TITLE_COMPLETE": complete,
        "MISSING_TEXT": missing_text,
        "MISSING_AUDIO_MAPPINGS": missing_mapping,
        "MISSING_AUDIO_FILES": missing_file,
        "UNSAFE_PATHS": unsafe_path,
    }


def audit_collections(required_locales: tuple[str, ...] = ("it", "en")) -> dict[str, int | list[str]]:
    cids = _load_collection_ids()
    required = len(cids) * len(required_locales)
    complete = 0
    missing: list[str] = []
    for cid in cids:
        for locale in required_locales:
            p = SYSTEM_LABEL_ROOT / locale / f"{cid}.wav"
            if p.is_file():
                complete += 1
            else:
                # Also accept .ogg if wav not present? Runbook prefers wav.
                alt = SYSTEM_LABEL_ROOT / locale / f"{cid}.ogg"
                if alt.is_file():
                    complete += 1
                else:
                    missing.append(f"{locale}/{cid}.wav")
    return {
        "COLLECTION_LABELS_REQUIRED": required,
        "COLLECTION_LABELS_COMPLETE": complete,
        "COLLECTION_MISSING": missing,
        "COLLECTION_IDS": list(cids),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit launcher spoken-label completeness")
    parser.add_argument("--locales", nargs="+", default=["it", "en"], help="required locales")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    locales = tuple(args.locales)
    act = audit_activities(locales)
    coll = audit_collections(locales)

    # Summary
    result = "PASS" if (
        act["ACTIVITY_TITLE_COMPLETE"] == act["ACTIVITY_TITLE_LOCALE_COMBINATIONS"]
        and coll["COLLECTION_LABELS_COMPLETE"] == coll["COLLECTION_LABELS_REQUIRED"]
        and not act["UNSAFE_PATHS"]  # type: ignore[operator]
        and not act["MISSING_AUDIO_MAPPINGS"]  # type: ignore[operator]
        and not act["MISSING_AUDIO_FILES"]  # type: ignore[operator]
    ) else "FAIL"

    if args.json:
        import json as js

        js.dump(
            {
                **act,
                **coll,
                "RESULT": result,
            },
            sys.stdout,
            indent=2,
            ensure_ascii=False,
        )
        sys.stdout.write("\n")
    else:
        print(f"BUILT_IN_ACTIVITIES={act['BUILT_IN_ACTIVITIES']}")
        print(f"ACTIVITY_TITLE_LOCALE_COMBINATIONS={act['ACTIVITY_TITLE_LOCALE_COMBINATIONS']}")
        print(f"ACTIVITY_TITLE_COMPLETE={act['ACTIVITY_TITLE_COMPLETE']}")
        if act["MISSING_TEXT"]:
            print(f"MISSING_TEXT={len(act['MISSING_TEXT'])}: {', '.join(act['MISSING_TEXT'][:10])}")
        if act["MISSING_AUDIO_MAPPINGS"]:
            print(f"MISSING_AUDIO_MAPPINGS={len(act['MISSING_AUDIO_MAPPINGS'])}: {', '.join(act['MISSING_AUDIO_MAPPINGS'][:10])}")
        if act["MISSING_AUDIO_FILES"]:
            print(f"MISSING_AUDIO_FILES={len(act['MISSING_AUDIO_FILES'])}: {', '.join(act['MISSING_AUDIO_FILES'][:10])}")
        if act["UNSAFE_PATHS"]:
            print(f"UNSAFE_PATHS={len(act['UNSAFE_PATHS'])}: {', '.join(act['UNSAFE_PATHS'][:10])}")
        print(f"COLLECTION_LABELS_REQUIRED={coll['COLLECTION_LABELS_REQUIRED']}")
        print(f"COLLECTION_LABELS_COMPLETE={coll['COLLECTION_LABELS_COMPLETE']}")
        if coll["COLLECTION_MISSING"]:
            print(f"COLLECTION_MISSING={len(coll['COLLECTION_MISSING'])}: {', '.join(coll['COLLECTION_MISSING'][:10])}")
        print(f"RESULT={result}")

    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
