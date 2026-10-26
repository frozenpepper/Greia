#!/usr/bin/env python3
"""Prepare editable locale JSON without offering an unfinished language.

Use from the repository root: PYTHONPATH=src python3 tools/scaffold_greia_language.py de
After translating and testing, promote by adding that locale's manifest.json.
The program never modifies existing files, manifests, voice or Activity metadata.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from greia_platform.localization import LocaleTag
from greia_installer.i18n import _ITALIAN
from greia_launcher import catalogue_view, panel_localization, panel_strings
from greia_launcher.achievement_localization import _UI_STRINGS
from greia_launcher.first_profile_copy import _COPY as FIRST_COPY
from greia_launcher.launch_feedback import _COPY as LAUNCH_COPY
from greia_launcher.usage_limit_presentation import _MESSAGES as TIME_COPY
from greia_platform.creation_gallery_painter import _GALLERY_TEXT


def reference_sections() -> dict[str, dict[str, str]]:
    """Source all editable keys from their exact existing English owners."""
    first = FIRST_COPY["en"]
    achievement = _UI_STRINGS["en"]
    feedback = LAUNCH_COPY["en"]
    return {
        "installer": {key: key for key in sorted(_ITALIAN)},
        "installer_dynamic": {
            "press_key": "Press the key that types “{value}”",
            "connecting": "Connecting to {value}…",
            "connected": "Connected to {value}",
            "pressed": "{left} of {right} pressed",
            "more_keys_one": "After one more key I'll show a list to confirm.",
            "more_keys": "After {value} more keys I'll show a list to confirm.",
            "power_unknown": "Connect the power adapter before installing (battery level could not be read).",
            "power_percent": "Connect the power adapter before installing (battery is {value}%).",
            "nice_click": "Nice click!{value}",
            "greia_screens": "Greia screens: {value}",
            "resolution": "Resolution: {value}",
            "pointer_unavailable": "Pointer preview unavailable{value}",
            "hold_seconds": "Keep the button pressed for {value} seconds.",
            "hold_keys_seconds": "Hold Enter or Space for {value} seconds.",
            "not_adjustable": "Not adjustable on this touchpad: {value}",
        },
        "parent": {key: values["en"] for key, values in sorted(panel_localization._MESSAGES.items())},
        "parent_constants": {
            key: getattr(panel_strings, key)
            for key in sorted(panel_localization._FORM_TRANSLATIONS)
        },
        "parent_audio_presets": {
            str(key): val for key, val in panel_strings.AUDIO_PRESET_NAMES.items()
        },
        "collections": {
            key: vals["en"] for key, vals in catalogue_view._CATEGORY_TRANSLATIONS.items()
        } | {"my_creations_compact": "Creations"},
        "discoveries": {
            key: vals["en"] for key, vals in catalogue_view._DISCOVERY_TRANSLATIONS.items()
        },
        "launcher_feedback": vars(feedback) if hasattr(feedback, "__dict__") else {
            "overlay": feedback.overlay, "badge": feedback.badge, "wait": feedback.wait
        },
        "gallery": {key: vals["en"] for key, vals in _GALLERY_TEXT.items()},
        "usage_limit": dict(TIME_COPY["en"]),
        "achievements": {
            "library_title": achievement.library_title,
            "empty_library": achievement.empty_library,
            "new_label": achievement.new_label,
            "new_badge": achievement.new_badge,
        },
        "first_profile": {
            "welcome": first.welcome, "ask_name": first.ask_name,
            "ask_avatar": first.ask_avatar, "ask_age": first.ask_age,
            "check": first.check, "celebrate": first.celebrate,
            "try_again": first.try_again, "skip": first.skip,
            "grown_up_hint": first.grown_up_hint,
            "extra_letters": "",
        },
    }


def prepare(locale: str, root: Path = ROOT) -> list[Path]:
    tag = LocaleTag.parse(locale).value
    if tag == "en":
        raise ValueError("English is the source locale, not a translation target")
    language_root = root / "src" / "greia_platform" / "languages" / tag
    ui = language_root / "ui.json"
    activities = sorted((root / "activities").glob("*/locales/en.json"))
    targets = [ui] + [source.with_name(f"{tag}.json") for source in activities]
    existing = [path for path in targets if path.exists()]
    if existing:
        raise FileExistsError(f"refusing to overwrite existing translation: {existing[0]}")
    language_root.mkdir(parents=True, exist_ok=True)
    ui.write_text(json.dumps({
        "schema_version": 1, **reference_sections()
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for source, dest in zip(activities, targets[1:]):
        raw = json.loads(source.read_text(encoding="utf-8"))
        raw["locale"] = tag
        raw["audio"] = {}  # do not falsely declare existing English audio as localized
        dest.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("locale", help="canonical locale tag: de, pt-BR, ...")
    args = parser.parse_args()
    try:
        created = prepare(args.locale)
    except (ValueError, FileExistsError, OSError) as exc:
        parser.error(str(exc))
    print(f"Created {len(created)} English-reference JSON files for translation.")
    print("The language is NOT selectable. Translate and test before adding manifest.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
