#!/usr/bin/env python3
"""Audit one manifest-advertised Greia locale before making release claims."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tomllib
from string import Formatter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from greia_platform.system_language import SUPPORTED_SYSTEM_LOCALES
from scaffold_greia_language import reference_sections

LEGACY_LANGUAGES = frozenset({"en", "it", "es", "fr"})


def fields(template: str) -> set[str]:
    return {name for _, name, _, _ in Formatter().parse(template) if name is not None}


def audit(locale: str, root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    if locale not in SUPPORTED_SYSTEM_LOCALES:
        return [f"{locale}: no offered manifest exists in the installed language folder"]
    if locale not in LEGACY_LANGUAGES:
        path = root / "src" / "greia_platform" / "languages" / locale / "ui.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{locale}: unreadable UI catalog: {exc}")
            data = {}
        for section, expected in reference_sections().items():
            actual = data.get(section)
            if not isinstance(actual, dict):
                errors.append(f"{locale}: missing UI section {section}")
                continue
            for key, english in expected.items():
                translated = actual.get(key)
                if not isinstance(translated, str) or not translated.strip():
                    errors.append(f"{locale}: missing UI text {section}/{key}")
                    continue
                try:
                    if fields(translated) != fields(english):
                        errors.append(f"{locale}: placeholder mismatch {section}/{key}")
                except ValueError:
                    errors.append(f"{locale}: invalid format string {section}/{key}")
    for activity in sorted((root / "activities").glob("*/activity.toml")):
        directory = activity.parent
        try:
            manifest = tomllib.loads(activity.read_text(encoding="utf-8"))
            declared = manifest["activity"]["languages"]
            if locale not in declared and declared != ["*"]:
                errors.append(f"{directory.name}: {locale} absent from activity.toml")
            reference = json.loads((directory / "locales" / "en.json").read_text(encoding="utf-8"))
            actual = json.loads((directory / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            if actual.get("locale") != locale:
                errors.append(f"{directory.name}: locale field mismatch")
            original = reference["strings"]
            translated = actual["strings"]
            if set(original) != set(translated):
                errors.append(f"{directory.name}: locale string key mismatch")
            for key in original.keys() & translated.keys():
                if not isinstance(translated[key], str) or not translated[key].strip():
                    errors.append(f"{directory.name}/{key}: empty text")
                    continue
                try:
                    if fields(original[key]) != fields(translated[key]):
                        errors.append(f"{directory.name}/{key}: placeholder mismatch")
                except ValueError:
                    errors.append(f"{directory.name}/{key}: bad placeholder")
        except (OSError, KeyError, ValueError, TypeError, UnicodeError) as exc:
            errors.append(f"{directory.name}: unreadable language metadata: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("locale", help="one installed/offered manifest locale, e.g. de")
    args = parser.parse_args()
    issues = audit(args.locale)
    for issue in issues:
        print(f"ERROR: {issue}")
    print(f"Greia {args.locale}: {len(issues)} source/placeholder problems; "
          "audio, font, rendered UI and device acceptance remain separate.")
    return 2 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
