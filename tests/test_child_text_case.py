from __future__ import annotations

import contextlib
import os
import tempfile
import unittest
from pathlib import Path

from greia_platform.child_text import (
    DEFAULT_CHILD_TEXT_CASE,
    ENVIRONMENT_NAME,
    ChildTextCase,
    child_text_case_from_environment,
    display_text,
    parse_child_text_case,
    set_child_text_case,
)
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.profiles import ProfileStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@contextlib.contextmanager
def _child_text_case(case):
    set_child_text_case(case)
    try:
        yield
    finally:
        set_child_text_case(None)


@contextlib.contextmanager
def _environment(name: str, value: str | None):
    sentinel = object()
    previous = os.environ.get(name, sentinel)
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
    try:
        yield
    finally:
        if previous is sentinel:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


class ChildTextCasePolicyTests(unittest.TestCase):
    def tearDown(self) -> None:
        set_child_text_case(None)

    def test_platform_default_is_uppercase(self) -> None:
        self.assertIs(DEFAULT_CHILD_TEXT_CASE, ChildTextCase.UPPERCASE)

    def test_parse_accepts_bounded_semantic_and_boolean_values(self) -> None:
        for raw, expected in (
            ("uppercase", ChildTextCase.UPPERCASE),
            ("normal", ChildTextCase.NORMAL),
            ("UPPER", ChildTextCase.UPPERCASE),
            ("1", ChildTextCase.UPPERCASE),
            ("0", ChildTextCase.NORMAL),
            (True, ChildTextCase.UPPERCASE),
            (False, ChildTextCase.NORMAL),
            ("nonsense", ChildTextCase.UPPERCASE),
            (None, ChildTextCase.UPPERCASE),
        ):
            with self.subTest(raw=raw):
                self.assertIs(parse_child_text_case(raw), expected)

    def test_display_text_defaults_to_capitals_until_parent_disables(self) -> None:
        self.assertEqual(display_text("Crea"), "CREA")
        with _child_text_case(ChildTextCase.NORMAL):
            self.assertEqual(display_text("Crea"), "Crea")
        with _child_text_case("normal"):
            self.assertEqual(display_text("Impara"), "Impara")

    def test_environment_resolves_once_per_process_value_change(self) -> None:
        with _environment(ENVIRONMENT_NAME, "normal"):
            set_child_text_case(None)
            self.assertIs(
                child_text_case_from_environment(), ChildTextCase.NORMAL
            )
        with _environment(ENVIRONMENT_NAME, "uppercase"):
            set_child_text_case(None)
            self.assertIs(
                child_text_case_from_environment(), ChildTextCase.UPPERCASE
            )
        with _environment(ENVIRONMENT_NAME, None):
            set_child_text_case(None)
            self.assertIs(child_text_case_from_environment(), DEFAULT_CHILD_TEXT_CASE)


class LocalizationUppercasePresentationTests(unittest.TestCase):
    def _resources(self, root: Path) -> LocalizedResources:
        directory = root / "locales"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "it.json").write_text(
            '{"schema_version": 1, "locale": "it", "direction": "ltr", '
            '"strings": {"feedback.correct": "Ottimo lavoro!"}, "audio": {}}',
            encoding="utf-8",
        )
        context = resolve_activity_locale(
            "it",
            ActivityLocaleSupport.localized(("it",), default_ui_locale="it"),
        )
        assert context is not None
        return LocalizedResources(root, context)

    def test_resolved_text_is_presented_in_capitals_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            resources = self._resources(Path(temporary))
            set_child_text_case(None)
            self.assertEqual(resources.text("feedback.correct"), "OTTIMO LAVORO!")
            with _child_text_case(ChildTextCase.NORMAL):
                self.assertEqual(resources.text("feedback.correct"), "Ottimo lavoro!")


class ProfileUppercasePreferenceTests(unittest.TestCase):
    def make_store(self, root: Path) -> ProfileStore:
        return ProfileStore.load(
            PROJECT_ROOT / "runtime" / "profile-defaults.toml", root
        )

    def test_new_children_default_to_capital_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            profile = store.create("Mia", "rainbow")
            self.assertTrue(profile.uppercase_text)

    def test_parent_can_disable_and_reenable_capital_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            profile = store.create("Mia", "rainbow")
            updated = store.update(profile.profile_id, uppercase_text=False)
            self.assertFalse(updated.uppercase_text)
            reread = store.get(profile.profile_id)
            self.assertFalse(reread.uppercase_text)
            restored = store.update(profile.profile_id, uppercase_text=True)
            self.assertTrue(restored.uppercase_text)

    def test_legacy_registry_without_field_defaults_to_capital_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            profile = store.create("Mia", "rainbow", uppercase_text=False)
            registry_path = store.root / store.REGISTRY_NAME
            raw = json_load(registry_path)
            for entry in raw["profiles"]:
                entry.pop("uppercase_text", None)
            write_json(registry_path, raw)
            reread = store.get(profile.profile_id)
            # Old registries predate the parent preference; the platform
            # default presents capitals until the parent explicitly chooses.
            self.assertTrue(reread.uppercase_text)

    def test_public_dict_exposes_preference_for_parent_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            profile = store.create("Mia", "rainbow", uppercase_text=False)
            payload = profile.public_dict()
            self.assertIn("uppercase_text", payload)
            self.assertFalse(payload["uppercase_text"])


def json_load(path: Path) -> dict:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    import json

    path.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
