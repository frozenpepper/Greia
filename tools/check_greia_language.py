#!/usr/bin/env python3
"""Audit staged and manifest-advertised locales before release."""
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
from greia_platform.localization import LocaleTag, LocalizationError
from scaffold_greia_language import reference_sections

LEGACY_LANGUAGES = frozenset({"en", "it", "es", "fr"})


def fields(template: str) -> set[str]:
    """Collect named placeholders, including those inside format specifications.

    E.g. '{count:{width}d}' requires both 'count' and 'width'. Python's
    Formatter.parse() yields the nested expression as a format_spec, so
    inspecting only the top-level fields would miss a runtime KeyError.
    """
    result: set[str] = set()

    def visit(value: str, depth: int) -> None:
        if depth > 8:
            raise ValueError("format placeholders are nested too deeply")
        for _, name, format_spec, _ in Formatter().parse(value):
            if name is not None:
                result.add(name)
            if format_spec and "{" in format_spec:
                visit(format_spec, depth + 1)

    visit(template, 0)
    return result


def audit(locale: str, root: Path = ROOT, *, staged: bool = False) -> list[str]:
    """Check locale resources; release mode also requires an offered manifest."""
    errors: list[str] = []
    try:
        canonical = LocaleTag.parse(locale).value
    except LocalizationError as exc:
        return [f"invalid locale {locale!r}: {exc}"]
    if locale != canonical:
        return [f"locale must use canonical spelling: {canonical}"]
    if not staged and locale not in SUPPORTED_SYSTEM_LOCALES:
        return [f"{locale}: no offered manifest exists in the installed language folder"]
    if staged and not (root / "src" / "greia_platform" / "languages" / locale).is_dir():
        return [f"{locale}: no language staging folder found"]
    if locale not in LEGACY_LANGUAGES:
        path = root / "src" / "greia_platform" / "languages" / locale / "ui.json"
        try:
            if path.stat().st_size > 256 * 1024:
                raise ValueError("UI catalog exceeds runtime 256 KiB limit")
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
                raise ValueError("expected schema_version 1 object")
            for name, mapping in data.items():
                if name == "schema_version":
                    continue
                if not isinstance(name, str) or not isinstance(mapping, dict):
                    raise ValueError(f"UI section {name!r} must be an object")
                if any(not isinstance(key, str) or not isinstance(value, str)
                       or len(key) > 160 or len(value) > 8192
                       for key, value in mapping.items()):
                    raise ValueError(f"UI section {name!r} contains invalid text")
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{locale}: invalid UI catalog: {exc}")
            data = {}
        for section, expected in reference_sections().items():
            actual = data.get(section)
            if not isinstance(actual, dict):
                errors.append(f"{locale}: missing UI section {section}")
                continue
            for key, english in expected.items():
                translated = actual.get(key)
                if not isinstance(translated, str) or (not translated.strip() and not (section == "first_profile" and key == "extra_letters")):
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
            if not isinstance(original, dict) or not isinstance(translated, dict):
                errors.append(f"{directory.name}: invalid strings catalog")
                continue
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
    parser.add_argument("locale", help="canonical locale, e.g. de")
    parser.add_argument("--staged", action="store_true",
                        help="audit translations before manifest promotion")
    args = parser.parse_args()
    issues = audit(args.locale, staged=args.staged)
    for issue in issues:
        print(f"ERROR: {issue}")
    print(f"Greia {args.locale} ({'staged' if args.staged else 'offered'}): {len(issues)} source/placeholder problems; "
          "audio, font, rendered UI and device acceptance remain separate.")
    return 2 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
