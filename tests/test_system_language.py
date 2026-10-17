from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from greia_parent.protocol import CAPABILITIES, RESOURCES
from greia_parent.update_api import UpdateParentApiApplication
from greia_platform import activity_api
from greia_platform.system_language import (
    DEFAULT_SYSTEM_LOCALE,
    SUPPORTED_SYSTEM_LANGUAGES,
    SystemLanguageError,
    SystemLanguageStore,
    system_language,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SystemLanguageTests(unittest.TestCase):
    def test_registry_is_single_bounded_product_list_with_required_languages(self) -> None:
        locales = [item.locale for item in SUPPORTED_SYSTEM_LANGUAGES]
        self.assertEqual(len(locales), len(set(locales)))
        self.assertEqual(DEFAULT_SYSTEM_LOCALE, "en")
        self.assertEqual(locales, ["en", "it", "es", "fr"])
        for unavailable in ("de", "zh-CN", "pt", "ar", "hi", "id", "bn", "sw"):
            self.assertNotIn(unavailable, locales)
            with self.assertRaises(SystemLanguageError):
                system_language(unavailable)
        for item in SUPPORTED_SYSTEM_LANGUAGES:
            self.assertTrue(item.flag)
            self.assertTrue(item.name)
            self.assertTrue(item.native_name)

    def test_legacy_unsupported_aliases_are_no_longer_selectable(self) -> None:
        with self.assertRaises(SystemLanguageError):
            system_language("zh")
        with self.assertRaises(SystemLanguageError):
            system_language("ZH-cn")

    def test_install_record_is_initial_device_language_then_state_override_wins(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = root / "install-record.json"
            record.write_text(json.dumps({"locale": "it"}), encoding="utf-8")
            store = SystemLanguageStore(root / "settings", install_record_path=record)
            self.assertEqual(store.read().locale, "it")
            saved = store.replace("en")
            self.assertEqual(saved.locale, "en")
            self.assertEqual(store.read().locale, "en")
            payload = store.as_json_dict()
            self.assertEqual(payload["locale"], "en")
            self.assertEqual(len(payload["languages"]), len(SUPPORTED_SYSTEM_LANGUAGES))

    def test_legacy_install_and_override_do_not_crash_or_rewrite_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = root / "install-record.json"
            # Retired tags from the old twelve-language registry fail soft.
            record.write_text(json.dumps({"locale": "de"}), encoding="utf-8")
            settings = root / "settings"
            settings.mkdir()
            override = settings / "language.json"
            override.write_text(
                json.dumps({"schema_version": 1, "locale": "zh-CN"}), encoding="utf-8"
            )
            store = SystemLanguageStore(settings, install_record_path=record)
            self.assertEqual(store.read().locale, "en")
            self.assertEqual(json.loads(record.read_text())["locale"], "de")
            self.assertEqual(json.loads(override.read_text())["locale"], "zh-CN")
            store.replace("it")
            self.assertEqual(store.read().locale, "it")

    def test_invalid_persisted_state_falls_back_without_crashing_child_ui(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = root / "install-record.json"
            record.write_text(json.dumps({"locale": "it"}), encoding="utf-8")
            state = root / "settings"
            state.mkdir()
            (state / "language.json").write_text("not-json", encoding="utf-8")
            store = SystemLanguageStore(state, install_record_path=record)
            self.assertEqual(store.read().locale, "it")
            with self.assertRaises(SystemLanguageError):
                store.replace("xx-NOPE")

    def test_activity_api_reads_same_device_store_when_no_profile_override_exists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / "settings"
            record = root / "install-record.json"
            record.write_text(json.dumps({"locale": "it"}), encoding="utf-8")
            with patch.dict(
                os.environ,
                {
                    "GREIA_SYSTEM_SETTINGS_DIR": str(settings),
                    "GREIA_INSTALL_RECORD": str(record),
                },
                clear=False,
            ):
                os.environ.pop("GREIA_PROFILE_LOCALE", None)
                os.environ.pop("GREIA_DEVICE_LOCALE", None)
                activity_api._system_language_store.cache_clear()
                self.assertEqual(activity_api.get_profile_locale(), "it")
                os.environ["GREIA_PROFILE_LOCALE"] = "it"
                self.assertEqual(activity_api.get_profile_locale(), "it")
            activity_api._system_language_store.cache_clear()

    def test_parent_protocol_advertises_typed_language_resource(self) -> None:
        resources = {resource.name: resource for resource in RESOURCES}
        self.assertEqual(
            resources["language_settings"].path,
            "/api/v1/settings/language",
        )
        self.assertEqual(resources["language_settings"].methods, ("GET", "PUT"))
        self.assertTrue(CAPABILITIES["settings.language"])

    def test_parent_application_reads_and_updates_the_same_store(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / "system-settings"
            record = root / "install-record.json"
            record.write_text(json.dumps({"locale": "it"}), encoding="utf-8")
            environment = {
                "GREIA_INSTALL_RECORD": str(record),
                "GREIA_PARENT_ACTIVITY_INSTALL": "0",
                "GREIA_PARENT_SYSTEM_UPDATE_UPLOAD": "0",
                "GREIA_PARENT_ACTIVITY_PACKAGE_ROOT": str(root / "packages"),
            }
            with patch.dict(os.environ, environment, clear=False):
                app = UpdateParentApiApplication(
                    PROJECT_ROOT,
                    root / "parent-state",
                    hardware_settings_dir=settings,
                    hardware_status_path=root / "hardware-status.json",
                    profiles_dir=root / "profiles",
                    active_profile_status_path=root / "active-profile.json",
                )
                self.assertEqual(app.language_payload()["locale"], "it")
                self.assertEqual([item["locale"] for item in app.language_payload()["languages"]], ["en", "it", "es", "fr"])
                with self.assertRaises(SystemLanguageError):
                    app.update_language("hi")
                self.assertEqual(app.update_language("en")["locale"], "en")
                self.assertEqual(
                    SystemLanguageStore(settings, install_record_path=record).read().locale,
                    "en",
                )

    def test_installer_service_uses_language_first_entrypoint_and_helper_is_narrow(self) -> None:
        service = (
            PROJECT_ROOT
            / "build"
            / "installer-overlay"
            / "etc"
            / "systemd"
            / "system"
            / "greia-installer.service"
        ).read_text(encoding="utf-8")
        # The installer module is exec'd by the xinit client wrapper, which
        # also owns the stdin detach; the unit names that client.
        self.assertIn("greia-installer-client", service)
        client = (
            PROJECT_ROOT
            / "build/installer-overlay/usr/local/lib/greia-os/greia-installer-client"
        ).read_text(encoding="utf-8")
        self.assertIn("-m greia_installer.entrypoint", client)
        entrypoint = (
            PROJECT_ROOT / "src" / "greia_installer" / "entrypoint.py"
        ).read_text(encoding="utf-8")
        self.assertIn("SUPPORTED_SYSTEM_LANGUAGES", entrypoint)
        # Step 8A.5 split: the language-first selection reaches the install
        # through the transaction settings snapshot, not a direct request.
        self.assertIn("def _snapshot_locale", entrypoint)
        self.assertIn("return self.locale", entrypoint)

        installer_packages = {
            line.strip()
            for line in (
                PROJECT_ROOT / "build" / "package-sets" / "installer-base.txt"
            ).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertIn("fonts-noto-color-emoji", installer_packages)
        self.assertIn("python3-pil", installer_packages)
        self.assertIn("python3-regex", installer_packages)

        helper_rule = (
            PROJECT_ROOT
            / "build"
            / "overlay"
            / "etc"
            / "sudoers.d"
            / "greia-language"
        ).read_text(encoding="utf-8")
        self.assertIn("greia-languagectl set *", helper_rule)
        self.assertNotIn("ALL=(ALL) NOPASSWD: ALL", helper_rule)
        tmpfiles_rule = (
            PROJECT_ROOT
            / "build"
            / "overlay"
            / "usr"
            / "lib"
            / "tmpfiles.d"
            / "greia-language-helper.conf"
        ).read_text(encoding="utf-8")
        self.assertIn("greia-languagectl 0755 root root", tmpfiles_rule)


if __name__ == "__main__":
    unittest.main()
