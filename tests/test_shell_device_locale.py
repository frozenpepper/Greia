"""The Shell speaks the device language saved at install, not a hard-coded Italian.

On an installed Greia no GREIA_* locale variable is set: the Shell, the
Activity launch environment and the achievement chrome must all read the
persisted device language (install record, then the parent's override) through
the canonical registry, with the policy fallback for unreadable/retired values.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from greia_platform.system_language import (
    CachedDeviceLocale,
    SystemLanguageStore,
    resolve_child_locale,
    resolve_device_locale,
)

_LOCALE_VARS = ("GREIA_PROFILE_LOCALE", "GREIA_DEVICE_LOCALE")


class _Device:
    """Temporary installed-device language files wired through the environment."""

    def __init__(self, install_locale: str | None, override: str | None = None) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.record = root / "install-record.json"
        self.settings = root / "settings"
        self.settings.mkdir()
        if install_locale is not None:
            self.record.write_text(json.dumps({"locale": install_locale}), encoding="utf-8")
        if override is not None:
            (self.settings / "language.json").write_text(
                json.dumps({"schema_version": 1, "locale": override}), encoding="utf-8"
            )
        env = {k: v for k, v in os.environ.items() if k not in _LOCALE_VARS}
        env["GREIA_SYSTEM_SETTINGS_DIR"] = str(self.settings)
        env["GREIA_INSTALL_RECORD"] = str(self.record)
        self._patch = mock.patch.dict(os.environ, env, clear=True)

    def __enter__(self) -> "_Device":
        self._patch.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._patch.stop()
        self._tmp.cleanup()


class DeviceLocaleResolutionTests(unittest.TestCase):
    def test_installer_choice_is_the_default_for_every_released_language(self) -> None:
        for locale in ("en", "it", "es", "fr"):
            with self.subTest(locale=locale), _Device(locale):
                self.assertEqual(resolve_device_locale(), locale)
                self.assertEqual(resolve_child_locale(), locale)

    def test_parent_override_wins_over_install_record(self) -> None:
        with _Device("it", override="fr"):
            self.assertEqual(resolve_device_locale(), "fr")

    def test_missing_or_retired_values_fall_back_to_policy_default(self) -> None:
        with _Device(None):
            self.assertEqual(resolve_device_locale(), "en")
        with _Device("de"):
            self.assertEqual(resolve_device_locale(), "en")

    def test_explicit_launch_values_win_and_bad_values_are_ignored(self) -> None:
        with _Device("es"):
            self.assertEqual(resolve_device_locale({"GREIA_DEVICE_LOCALE": "it"}), "it")
            self.assertEqual(resolve_device_locale({"GREIA_DEVICE_LOCALE": "xx-bad"}), "es")
            self.assertEqual(resolve_child_locale("fr", {}), "fr")
            self.assertEqual(resolve_child_locale(None, {"GREIA_PROFILE_LOCALE": "nope"}), "es")
            self.assertEqual(resolve_child_locale("es-MX", {}), "es")

    def test_cached_reader_refreshes_after_its_ttl(self) -> None:
        now = [0.0]
        with _Device("en") as device:
            cache = CachedDeviceLocale(2.0, clock=lambda: now[0])
            self.assertEqual(cache.get(), "en")
            SystemLanguageStore(device.settings, install_record_path=device.record).replace("es")
            self.assertEqual(cache.get(), "en")  # still within the TTL
            now[0] = 2.5
            self.assertEqual(cache.get(), "es")


class ShellUsesDeviceLanguageTests(unittest.TestCase):
    def test_shell_active_locale_reads_saved_device_language(self) -> None:
        from greia_launcher.presentation import GreiaLauncherPresentation

        for locale in ("es", "fr", "en"):
            with self.subTest(locale=locale), _Device(locale):
                shell = GreiaLauncherPresentation.__new__(GreiaLauncherPresentation)
                shell._active_profile = None
                self.assertEqual(shell._active_locale, locale)

    def test_profile_override_still_wins_in_the_shell(self) -> None:
        from greia_launcher.presentation import GreiaLauncherPresentation

        with _Device("es"):
            shell = GreiaLauncherPresentation.__new__(GreiaLauncherPresentation)
            shell._active_profile = SimpleNamespace(profile=SimpleNamespace(locale="it"))
            self.assertEqual(shell._active_locale, "it")

    def test_achievement_chrome_follows_the_device_language(self) -> None:
        from greia_launcher.achievement_localization import resolve_achievement_locale

        with _Device("fr"):
            self.assertEqual(resolve_achievement_locale(), "fr")

    def test_supervisor_injects_resolved_locales_not_a_hardcoded_default(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "src/greia_launcher/supervisor.py").read_text(encoding="utf-8")
        self.assertIn('"GREIA_DEVICE_LOCALE": resolve_device_locale()', source)
        self.assertNotIn('or "it"', source)


if __name__ == "__main__":
    unittest.main()
