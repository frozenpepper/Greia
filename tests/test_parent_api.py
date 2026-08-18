from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_parent.api_server import ParentApiApplication
from greia_parent.credentials import (
    MAX_PAIRED_DEVICES,
    ParentCredentialError,
    ParentDeviceCredentialStore,
)
from greia_parent.package_api import _activity_install_enabled
from greia_parent.protocol import (
    API_BASE,
    API_VERSION,
    SERVICE_PORT,
    SERVICE_TYPE,
    api_index_payload,
)
from greia_parent.web_client import render_parent_web_app


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _Handler:
    def __init__(self, **headers: str):
        self.headers = headers


class ParentApiTests(unittest.TestCase):
    def test_per_device_credentials_persist_only_hashes_and_are_independently_revocable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = ParentDeviceCredentialStore(Path(temporary))
            first = store.issue("Dad's browser")
            second = store.issue("Mum's phone")

            raw = store.path.read_text(encoding="utf-8")
            self.assertNotIn(first.token, raw)
            self.assertNotIn(second.token, raw)
            document = json.loads(raw)
            self.assertEqual(document["schema_version"], 1)
            self.assertEqual(len(document["devices"][0]["token_sha256"]), 64)

            first_auth = store.authenticate(first.token)
            second_auth = store.authenticate(second.token)
            self.assertIsNotNone(first_auth)
            self.assertIsNotNone(second_auth)
            assert first_auth is not None
            assert second_auth is not None
            self.assertEqual(first_auth.device_id, first.device.device_id)
            self.assertEqual(second_auth.device_id, second.device.device_id)

            store.revoke(first.device.device_id)
            self.assertIsNone(store.authenticate(first.token))
            second_auth = store.authenticate(second.token)
            self.assertIsNotNone(second_auth)
            assert second_auth is not None
            self.assertEqual(second_auth.device_id, second.device.device_id)

    def test_credential_store_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = ParentDeviceCredentialStore(Path(temporary))
            with self.assertRaises(ParentCredentialError):
                store.issue("")
            with self.assertRaises(ParentCredentialError):
                store.issue("x" * 65)

            for index in range(MAX_PAIRED_DEVICES):
                store.issue(f"Device {index}")
            with self.assertRaisesRegex(ParentCredentialError, "limit"):
                store.issue("One too many")

    def test_versioned_protocol_advertises_only_real_capabilities(self) -> None:
        payload = api_index_payload()
        self.assertEqual(payload["api_version"], API_VERSION)
        self.assertEqual(payload["api_base"], API_BASE)
        self.assertEqual(payload["service_type"], SERVICE_TYPE)
        capabilities = payload["capabilities"]
        self.assertTrue(capabilities["profiles.manage"])
        self.assertTrue(capabilities["settings.input"])
        self.assertFalse(capabilities["activities.install"])
        self.assertFalse(capabilities["backup.manage"])
        self.assertFalse(capabilities["settings.audio"])
        self.assertFalse(capabilities["network.manage"])
        self.assertFalse(capabilities["maintenance.ssh"])
        paths = {resource["path"] for resource in payload["resources"]}
        self.assertIn(f"{API_BASE}/activities/install", paths)

    def test_install_capability_override_is_typed_and_does_not_change_default(self) -> None:
        self.assertTrue(api_index_payload({"activities.install": True})["capabilities"]["activities.install"])
        self.assertFalse(api_index_payload()["capabilities"]["activities.install"])
        with self.assertRaises(ValueError):
            api_index_payload({"invented.capability": True})

    def test_activity_install_is_fail_closed_without_explicit_owner_or_dev_enablement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            marker = Path(temporary) / "developer-remote"
            with mock.patch.dict(
                os.environ,
                {"GREIA_DEVELOPER_REMOTE_MARKER": str(marker)},
                clear=False,
            ):
                os.environ.pop("GREIA_PARENT_ACTIVITY_INSTALL", None)
                self.assertFalse(_activity_install_enabled())
                marker.write_text("enabled\n", encoding="utf-8")
                self.assertTrue(_activity_install_enabled())
                os.environ["GREIA_PARENT_ACTIVITY_INSTALL"] = "false"
                self.assertFalse(_activity_install_enabled())
                os.environ["GREIA_PARENT_ACTIVITY_INSTALL"] = "true"
                self.assertTrue(_activity_install_enabled())

    def test_parent_api_bootstrap_issues_device_credential_and_bearer_authenticates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = ParentApiApplication(
                PROJECT_ROOT,
                root / "parent",
                profiles_dir=root / "profiles",
                hardware_settings_dir=root / "hardware",
                hardware_status_path=root / "hardware-status.json",
                active_profile_status_path=root / "active-profile.json",
            )
            issued = app.bootstrap_device(app.token, "Family laptop")
            credential = str(issued["credential"])
            device = issued["device"]
            self.assertNotEqual(credential, app.token)
            self.assertEqual(device["display_name"], "Family laptop")
            self.assertTrue(
                app.authorized(
                    _Handler(Authorization=f"Bearer {credential}"),
                    {},
                )
            )
            self.assertFalse(
                app.authorized(
                    _Handler(Authorization="Bearer definitely-wrong"),
                    {},
                )
            )
            with self.assertRaises(PermissionError):
                app.bootstrap_device("wrong", "Intruder")

    def test_activity_api_payload_hides_filesystem_and_runtime_entrypoint_details(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = ParentApiApplication(
                PROJECT_ROOT,
                root / "parent",
                profiles_dir=root / "profiles",
                hardware_settings_dir=root / "hardware",
                hardware_status_path=root / "hardware-status.json",
            )
            payload = app.activities_payload()
            self.assertTrue(payload)
            encoded = json.dumps(payload, sort_keys=True)
            self.assertNotIn(str(PROJECT_ROOT), encoded)
            self.assertNotIn("entrypoint", encoded)
            self.assertNotIn("\"root\"", encoded)

    def test_html_parent_client_uses_versioned_api_not_legacy_mutation_paths(self) -> None:
        page = render_parent_web_app()
        self.assertIn('const API="/api/v1"', page)
        self.assertIn('request("/profiles"', page)
        self.assertIn('request("/settings/hardware"', page)
        self.assertNotIn('action="/api/profiles', page)
        self.assertNotIn('action="/api/hardware', page)

    def test_normal_image_advertises_parent_service_without_enabling_ssh(self) -> None:
        avahi = (
            PROJECT_ROOT
            / "build"
            / "overlay"
            / "etc"
            / "avahi"
            / "services"
            / "greia-parent.service"
        ).read_text(encoding="utf-8")
        self.assertIn(SERVICE_TYPE, avahi)
        self.assertIn(f"<port>{SERVICE_PORT}</port>", avahi)
        self.assertIn("<txt-record>api=1</txt-record>", avahi)
        self.assertIn("<txt-record>path=/api/v1</txt-record>", avahi)

        parent_service = (
            PROJECT_ROOT
            / "build"
            / "overlay"
            / "etc"
            / "systemd"
            / "system"
            / "greia-parent.service"
        ).read_text(encoding="utf-8")
        self.assertIn("-m greia_parent.package_api", parent_service)
        self.assertIn(
            "GREIA_PARENT_ACTIVITY_PACKAGE_ROOT=/var/lib/greia-os/activity-packages",
            parent_service,
        )
        self.assertNotIn("GREIA_PARENT_ACTIVITY_INSTALL=true", parent_service)

        normal_profile = (
            PROJECT_ROOT / "build" / "profiles" / "legacy-x86-i686.toml"
        ).read_text(encoding="utf-8")
        self.assertIn('"network-basic"', normal_profile)
        self.assertNotIn('"developer-remote"', normal_profile)


if __name__ == "__main__":
    unittest.main()
