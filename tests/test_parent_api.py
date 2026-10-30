from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from unittest import mock

from greia_parent.api_server import (
    ParentApiApplication,
    ParentApiHTTPServer,
    hardware_form_from_json,
)
from greia_parent.credentials import (
    MAX_PAIRED_DEVICES,
    ParentCredentialError,
    ParentDeviceCredentialStore,
)
from greia_parent.package_api import (
    PackageParentApiApplication,
    PackageParentApiHTTPServer,
)
from greia_parent.protocol import (
    API_BASE,
    API_VERSION,
    SERVICE_PORT,
    SERVICE_TYPE,
    api_index_payload,
)
from greia_parent.web_client import render_parent_web_app
from greia_platform.activity_packages import ActivityPackageError
from greia_platform.hardware import HardwareSettingsError
from greia_platform.usage_limits import UsageLimitError
from greia_platform.ssh_maintenance import MockSshMaintenanceProvider, SshMaintenanceService
from greia_platform.wifi import DemoWifiBackend


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _Handler:
    def __init__(self, **headers: str):
        self.headers = headers


def _app(root: Path) -> ParentApiApplication:
    # Hermetic device-host fix: inject the deterministic DemoWifiBackend so this
    # contract test does not depend on iwd/python3-dbus presence. On hosts with
    # /var/lib/iwd the default would select IwdWifiBackend and raise WifiError
    # where dbus is absent; the Demo backend is the established testing backend.
    # Likewise inject the in-memory Mock SSH provider: on the device host the
    # default is the real systemd provider (ssh.service is active there, and an
    # unprivileged disable is a silent no-op), so the enable/disable contract
    # assertions require the Mock provider. Never touch real system SSH state.
    return ParentApiApplication(
        PROJECT_ROOT,
        root / "parent",
        profiles_dir=root / "profiles",
        hardware_settings_dir=root / "hardware",
        hardware_status_path=root / "hardware-status.json",
        active_profile_status_path=root / "active-profile.json",
        wifi_backend=DemoWifiBackend(),
        ssh_service=SshMaintenanceService(MockSshMaintenanceProvider()),
    )


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
        self.assertTrue(capabilities["usage_limits.manage"])
        self.assertTrue(capabilities["settings.input"])
        self.assertFalse(capabilities["activities.install"])
        self.assertFalse(capabilities["backup.manage"])
        self.assertFalse(capabilities["settings.audio"])
        self.assertTrue(capabilities["network.manage"])
        self.assertTrue(capabilities["maintenance.ssh"])
        self.assertTrue(capabilities["parent.password"])
        paths = {resource["path"] for resource in payload["resources"]}
        self.assertIn(f"{API_BASE}/activities/install", paths)
        self.assertIn(f"{API_BASE}/usage-limits", paths)
        self.assertIn(f"{API_BASE}/profiles/{{profile_id}}/usage-limit", paths)
        self.assertIn(f"{API_BASE}/network/wifi", paths)
        self.assertIn(f"{API_BASE}/maintenance/ssh", paths)

    def test_install_capability_override_is_typed_and_does_not_change_default(self) -> None:
        self.assertTrue(api_index_payload({"activities.install": True})["capabilities"]["activities.install"])
        self.assertFalse(api_index_payload()["capabilities"]["activities.install"])
        with self.assertRaises(ValueError):
            api_index_payload({"invented.capability": True})

    def test_api_v1_startup_retires_legacy_shared_token_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_dir = root / "parent"
            state_dir.mkdir(parents=True)
            token_path = state_dir / "parent-pairing-token"
            token_path.write_text("legacy-shared-secret\n", encoding="ascii")

            app = _app(root)

            self.assertEqual(app.token, "")
            self.assertFalse(token_path.exists())
            self.assertFalse((state_dir / "parent-pairing-token").exists())

    def test_parent_api_password_bootstrap_issues_device_credential_and_only_bearer_authenticates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = _app(Path(temporary))
            issued = app.bootstrap_device("greia", "Family laptop")
            credential = str(issued["credential"])
            device = issued["device"]
            self.assertNotEqual(credential, "greia")
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
            self.assertFalse(
                app.authorized(
                    _Handler(**{"X-Pip-Token": app.token}),
                    {},
                    allow_query_token=True,
                )
            )
            with self.assertRaises(PermissionError):
                app.bootstrap_device("wrong", "Intruder")

    def test_parent_password_change_requires_current_password_and_never_exposes_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = _app(Path(temporary))
            payload = app.parent_password_payload()
            self.assertEqual(payload["username"], "greia")
            self.assertNotIn("password", payload)
            with self.assertRaises(Exception):
                app.change_parent_password("wrong", "newpass1")
            app.change_parent_password("greia", "newpass1")
            self.assertTrue(app.main_credential.verify("newpass1"))
            self.assertFalse(app.main_credential.verify("greia"))
            with self.assertRaises(PermissionError):
                app.bootstrap_device("greia", "Old password browser")
            issued = app.bootstrap_device("newpass1", "New password browser")
            self.assertIn("credential", issued)

    def test_activity_api_payload_hides_filesystem_and_runtime_entrypoint_details(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = _app(Path(temporary))
            payload = app.activities_payload()
            self.assertTrue(payload)
            encoded = json.dumps(payload, sort_keys=True)
            self.assertNotIn(str(PROJECT_ROOT), encoded)
            self.assertNotIn("entrypoint", encoded)
            self.assertNotIn("\"root\"", encoded)

    def test_activity_policy_exposes_and_persists_difficulty_range(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = _app(Path(temporary))
            profile = app.profile_store.list_profiles()[0]
            updated = app.update_activity_policy(
                profile.profile_id,
                visibility_mode="show_all",
                difficulty_min=3,
                difficulty_max=6,
                overrides={},
            )
            self.assertEqual(updated["difficulty_min"], 3)
            self.assertEqual(updated["difficulty_max"], 6)
            reloaded = app.activity_policy_payload(profile.profile_id)
            self.assertEqual(reloaded["difficulty_min"], 3)
            self.assertEqual(reloaded["difficulty_max"], 6)
            with self.assertRaises(Exception):
                app.update_activity_policy(
                    profile.profile_id,
                    visibility_mode="show_all",
                    difficulty_min=8,
                    difficulty_max=4,
                    overrides={},
                )

    def test_usage_limit_domain_api_supports_device_and_profile_budgets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _app(root)
            profile = app.profile_store.list_profiles()[0]

            device = app.usage_limits_payload()
            self.assertIsNone(device["daily_minutes"])
            self.assertIsNone(device["remaining_seconds"])

            device = app.update_usage_limits(90)
            self.assertEqual(device["daily_minutes"], 90)
            self.assertEqual(device["remaining_seconds"], 90 * 60)

            child = app.update_profile_usage_limit(profile.profile_id, 45)
            self.assertEqual(child["profile_daily_minutes"], 45)
            self.assertEqual(child["effective_remaining_seconds"], 45 * 60)

            app.usage_limits.record_activity_time(profile.profile_id, 120)
            child = app.profile_usage_limit_payload(profile.profile_id)
            self.assertEqual(child["profile_used_seconds"], 120)
            self.assertEqual(child["device_used_seconds"], 120)
            self.assertEqual(child["effective_remaining_seconds"], 43 * 60)

            app.update_profile_usage_limit(profile.profile_id, None)
            app.update_usage_limits(None)
            child = app.profile_usage_limit_payload(profile.profile_id)
            self.assertIsNone(child["profile_daily_minutes"])
            self.assertIsNone(child["device_daily_minutes"])
            self.assertIsNone(child["effective_remaining_seconds"])
            self.assertTrue((root / "profiles" / "usage-limits.json").is_file())

    def test_usage_limit_domain_api_rejects_invalid_minutes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = _app(Path(temporary))
            profile = app.profile_store.list_profiles()[0]
            for invalid in (0, -1, 1441, True, "30"):
                with self.subTest(invalid=invalid):
                    with self.assertRaises(UsageLimitError):
                        app.update_usage_limits(invalid)
                    with self.assertRaises(UsageLimitError):
                        app.update_profile_usage_limit(profile.profile_id, invalid)

    def test_html_parent_client_uses_versioned_api_not_legacy_mutation_paths(self) -> None:
        # 155dbc74 removed the legacy embedded Parent app: the fallback is
        # fail-closed with no management controls and no sample data. The
        # versioned API remains the only management surface (covered by the
        # hardware/usage/policy tests); the pinned static client lives in the
        # parent-app/ directory (out of scope per T09 brief).
        page = render_parent_web_app()
        self.assertIn("not installed correctly", page)
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
        self.assertIn("-m greia_parent.production_api", parent_service)
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

    def test_parent_api_wifi_and_ssh_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = _app(Path(temporary))
            wifi_data = app.wifi_payload()
            self.assertTrue(wifi_data["available"])
            self.assertIsInstance(wifi_data["networks"], list)
            self.assertIn("connected_ssid", wifi_data)

            conn = app.connect_wifi("Greia Family Wi-Fi", "testpassphrase")
            self.assertTrue(conn["connected"])
            self.assertEqual(conn["ssid"], "Greia Family Wi-Fi")

            ssh_data = app.ssh_payload()
            self.assertIn("active", ssh_data)
            self.assertIn("enabled", ssh_data)
            self.assertEqual(ssh_data["username"], "greia")

            updated = app.update_ssh(True)
            self.assertTrue(updated["active"])
            self.assertTrue(updated["enabled"])

            disabled = app.update_ssh(False)
            self.assertFalse(disabled["active"])
            self.assertFalse(disabled["enabled"])

    def test_hardware_get_shape_desired_applied_and_facts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _app(root)
            status_path = root / "hardware-status.json"
            status_path.write_text(
                json.dumps(
                    {
                        "applied": True,
                        "backend": "legacy_x",
                        "display_output": "LVDS-1",
                        "display_modes": [
                            {
                                "width": 1024,
                                "height": 600,
                                "refresh_hz": 60.0,
                                "preferred": True,
                                "current": True,
                            }
                        ],
                        "display_metrics": {
                            "pixel_width": 1024,
                            "pixel_height": 600,
                            "physical_size_known": False,
                            "orientation": "landscape",
                            "source": "unknown",
                        },
                        "pointer_devices": [
                            {
                                "kind": "touchpad",
                                "label": "Touchpad",
                                "supports_tap": True,
                                "supports_natural_scrolling": True,
                                "supports_disable_while_typing": True,
                                "supports_speed": True,
                            }
                        ],
                        "message": "ok",
                    }
                ),
                encoding="utf-8",
            )
            payload = app.hardware_payload()
            self.assertIn("desired", payload)
            self.assertIn("applied", payload)
            self.assertTrue(payload["applied"])
            self.assertEqual(payload["backend"], "legacy_x")
            desired = payload["desired"]
            assert isinstance(desired, dict)
            self.assertIn("disable_while_typing", desired)
            self.assertIn("touchpad_tap", desired)
            metrics = payload["display_metrics"]
            assert isinstance(metrics, dict)
            self.assertEqual(metrics["pixel_width"], 1024)
            devices = payload["pointer_devices"]
            assert isinstance(devices, list)
            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0]["kind"], "touchpad")
            # Protocol-style alias mirrors the T05 device list.
            self.assertEqual(payload["pointer_capabilities"], devices)
            self.assertLessEqual(len(devices), 8)
            self.assertLessEqual(len(payload["display_modes"]), 32)

    def test_hardware_get_bounds_pointer_and_mode_lists(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _app(root)
            status_path = root / "hardware-status.json"
            status_path.write_text(
                json.dumps(
                    {
                        "applied": True,
                        "backend": "legacy_x",
                        "display_output": "LVDS-1",
                        "display_modes": [
                            {
                                "width": 800 + index,
                                "height": 600,
                                "refresh_hz": 60.0,
                                "preferred": False,
                                "current": index == 0,
                            }
                            for index in range(40)
                        ],
                        "display_metrics": None,
                        "pointer_devices": [
                            {
                                "kind": "mouse",
                                "label": f"Mouse {index}",
                                "supports_tap": False,
                                "supports_natural_scrolling": False,
                                "supports_disable_while_typing": False,
                                "supports_speed": True,
                            }
                            for index in range(20)
                        ],
                        "message": "x" * 900,
                    }
                ),
                encoding="utf-8",
            )
            payload = app.hardware_payload()
            assert isinstance(payload["pointer_devices"], list)
            assert isinstance(payload["display_modes"], list)
            assert isinstance(payload["message"], str)
            self.assertLessEqual(len(payload["pointer_devices"]), 8)
            self.assertLessEqual(len(payload["display_modes"]), 32)
            self.assertLessEqual(len(payload["message"]), 500)

    def test_hardware_put_updates_pointer_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = _app(Path(temporary))
            current = app.hardware_store.read().as_json_dict()
            form = hardware_form_from_json(
                {
                    "touchpad_tap": True,
                    "disable_while_typing": True,
                    "natural_scrolling": True,
                    "touchpad_speed": 0.25,
                    "mouse_speed": -0.25,
                },
                current,
            )
            updated = app.update_hardware(form)
            self.assertTrue(updated["touchpad_tap"])
            self.assertTrue(updated["disable_while_typing"])
            self.assertTrue(updated["natural_scrolling"])
            self.assertEqual(updated["touchpad_speed"], 0.25)
            self.assertEqual(updated["mouse_speed"], -0.25)

    def test_hardware_put_rejects_non_boolean_pointer_flags(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = _app(Path(temporary))
            current = app.hardware_store.read().as_json_dict()
            for key in (
                "touchpad_tap",
                "natural_scrolling",
                "disable_while_typing",
            ):
                for bad in ("on", "true", 1, 0, None, []):
                    with self.subTest(field=key, value=bad):
                        with self.assertRaises(HardwareSettingsError):
                            hardware_form_from_json({key: bad}, current)

    def test_hardware_put_rejects_out_of_range_and_nonfinite_speeds(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = _app(Path(temporary))
            current = app.hardware_store.read().as_json_dict()
            # Non-finite never reaches the store.
            for bad in (float("inf"), float("-inf"), float("nan")):
                with self.subTest(value=bad):
                    with self.assertRaises(HardwareSettingsError):
                        hardware_form_from_json({"mouse_speed": bad}, current)
            # Wrong JSON types never reach the store.
            for bad in ("0.5", True, None, []):
                with self.subTest(value=bad):
                    with self.assertRaises(HardwareSettingsError):
                        hardware_form_from_json({"mouse_speed": bad}, current)
            # Finite but outside platform bounds fails at the store.
            form = hardware_form_from_json({"mouse_speed": 5.0}, current)
            with self.assertRaises(HardwareSettingsError):
                app.update_hardware(form)

    def test_hardware_put_rejects_unknown_and_backend_controls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = _app(Path(temporary))
            current = app.hardware_store.read().as_json_dict()
            for bad_key in (
                "xinput_id",
                "property",
                "matrix",
                "command",
                "shell",
                "backend",
                "device_id",
                "coordinate_matrix",
                "libinput_prop",
                "invented_field",
            ):
                with self.subTest(field=bad_key):
                    with self.assertRaises(HardwareSettingsError):
                        hardware_form_from_json({bad_key: True}, current)

    def test_hardware_reset_returns_canonical_v2_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = _app(Path(temporary))
            current = app.hardware_store.read().as_json_dict()
            app.update_hardware(
                hardware_form_from_json(
                    {"touchpad_tap": True, "disable_while_typing": True},
                    current,
                )
            )
            reset = app.reset_hardware()
            self.assertEqual(reset["schema_version"], 2)
            self.assertFalse(reset["touchpad_tap"])
            self.assertFalse(reset["disable_while_typing"])
            self.assertFalse(reset["natural_scrolling"])
            self.assertEqual(reset["resolution"], "auto")

    def test_hardware_old_status_file_without_new_fields_still_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _app(root)
            (root / "hardware-status.json").write_text(
                json.dumps(
                    {
                        "applied": False,
                        "display_output": None,
                        "display_modes": [],
                        "message": "Hardware session has not reported yet.",
                    }
                ),
                encoding="utf-8",
            )
            payload = app.hardware_payload()
            self.assertIn("desired", payload)
            self.assertIn("applied", payload)
            self.assertFalse(payload["applied"])
            self.assertIsNone(payload["backend"])
            self.assertIsNone(payload["display_metrics"])
            self.assertEqual(payload["pointer_devices"], [])
            self.assertEqual(payload["pointer_capabilities"], [])

    def test_hardware_api_surface_has_no_backend_command_vocabulary(self) -> None:
        for name in ("api_server.py", "server.py", "protocol.py"):
            text = (PROJECT_ROOT / "src" / "greia_parent" / name).read_text(
                encoding="utf-8"
            )
            lowered = text.lower()
            for token in ("xinput", "xrandr", "coordinate transformation"):
                self.assertNotIn(token, lowered, f"{name} leaks {token}")

    def test_hardware_endpoints_require_authorization_and_validate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _app(root)
            issued = app.bootstrap_device("greia", "Test browser")
            credential = str(issued["credential"])
            server = ParentApiHTTPServer(("127.0.0.1", 0), app)
            port = server.server_address[1]
            thread = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.05},
                daemon=True,
            )
            thread.start()
            try:
                base = f"http://127.0.0.1:{port}{API_BASE}/settings/hardware"

                def _request(
                    method: str,
                    url: str,
                    token: str | None = None,
                    body: dict[str, object] | None = None,
                ) -> tuple[int, dict[str, object]]:
                    data = (
                        json.dumps(body).encode("utf-8")
                        if body is not None
                        else None
                    )
                    request = urllib.request.Request(
                        url, data=data, method=method
                    )
                    if token is not None:
                        request.add_header("Authorization", f"Bearer {token}")
                    if body is not None:
                        request.add_header("Content-Type", "application/json")
                    try:
                        with urllib.request.urlopen(
                            request, timeout=5
                        ) as response:
                            return (
                                response.status,
                                json.loads(response.read().decode("utf-8")),
                            )
                    except urllib.error.HTTPError as exc:
                        raw = exc.read().decode("utf-8", "replace")
                        try:
                            parsed: dict[str, object] = json.loads(raw)
                        except ValueError:
                            parsed = {"raw": raw}
                        return exc.code, parsed

                status, _ = _request("GET", base)
                self.assertEqual(status, 401)
                status, payload = _request("GET", base, token=credential)
                self.assertEqual(status, 200)
                self.assertIn("desired", payload)
                self.assertIn("pointer_devices", payload)

                status, _ = _request(
                    "PUT", base, body={"touchpad_tap": True}
                )
                self.assertEqual(status, 401)
                status, _ = _request(
                    "PUT",
                    base,
                    token=credential,
                    body={"touchpad_tap": "on"},
                )
                self.assertEqual(status, 400)
                status, _ = _request(
                    "PUT",
                    base,
                    token=credential,
                    body={"mouse_speed": 5.0},
                )
                self.assertEqual(status, 400)
                status, _ = _request(
                    "PUT",
                    base,
                    token=credential,
                    body={"xinput_id": 12},
                )
                self.assertEqual(status, 400)
                status, payload = _request(
                    "PUT",
                    base,
                    token=credential,
                    body={"disable_while_typing": True},
                )
                self.assertEqual(status, 200)
                assert isinstance(payload, dict)
                self.assertTrue(payload["disable_while_typing"])

                reset_url = base + "/reset"
                status, _ = _request("POST", reset_url)
                self.assertEqual(status, 401)
                status, payload = _request(
                    "POST", reset_url, token=credential, body={}
                )
                self.assertEqual(status, 200)
                assert isinstance(payload, dict)
                self.assertFalse(payload["touchpad_tap"])
                self.assertFalse(payload["disable_while_typing"])

                legacy_url = f"http://127.0.0.1:{port}/pair?token={app.token}"
                status, _ = _request("GET", legacy_url)
                self.assertEqual(status, 404)
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()


if __name__ == "__main__":
    unittest.main()


class RePairingClientDoesNotExhaustTheLimitTests(unittest.TestCase):
    """A client that re-pairs must not consume a new slot every time.

    The on-device panel re-pairs on each launch. Before this, sixteen launches
    filled the store and every subsequent parent password was refused with
    "paired-device limit reached", which the panel had no way to tell apart
    from the password being unavailable.
    """

    def _store(self, tmp: str) -> ParentDeviceCredentialStore:
        return ParentDeviceCredentialStore(Path(tmp))

    def test_repeated_pairing_of_one_client_stays_within_the_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            for _ in range(MAX_PAIRED_DEVICES + 8):
                store.issue("greia-on-device")
            self.assertEqual(len(store.list_devices()), 1)

    def test_distinct_clients_keep_separate_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            store.issue("greia-on-device")
            store.issue("parent-phone")
            names = sorted(d.display_name for d in store.list_devices())
            self.assertEqual(names, ["greia-on-device", "parent-phone"])

    def test_limit_still_refuses_genuinely_distinct_clients(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            for index in range(MAX_PAIRED_DEVICES):
                store.issue("device-%d" % index)
            with self.assertRaises(ParentCredentialError):
                store.issue("one-too-many")


INSTALLED_ACTIVITY_ID = "org.example.policy-probe"


def _write_installed_activity_archive(destination: Path) -> None:
    """Package a copy of Painting under an id no built-in uses."""

    source = PROJECT_ROOT / "activities" / "painting"
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            relative = path.relative_to(source).as_posix()
            if relative == "activity.toml":
                text = path.read_text(encoding="utf-8")
                archive.writestr(
                    relative,
                    text.replace('id = "org.greia.painting"', f'id = "{INSTALLED_ACTIVITY_ID}"', 1),
                )
            else:
                archive.write(path, relative)


class PackageActivityPolicyCatalogueTests(unittest.TestCase):
    """Parent policy must cover the same catalogue ``GET /activities`` lists.

    Regression: policy validation and ``effective_activity_ids`` once used the
    built-in registry only, so the HTML client's "Save Activity choices" (which
    PUTs an override for every listed Activity, ``null`` meaning automatic)
    failed with 400 as soon as one Parent-installed Activity existed.
    """

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name).resolve()
        # A minimal OS root with one real built-in keeps validated discovery
        # cheap; runtime and asset catalogues are the repository's own.
        os_root = self.root / "os"
        os_root.mkdir()
        (os_root / "runtime").symlink_to(PROJECT_ROOT / "runtime")
        (os_root / "assets").symlink_to(PROJECT_ROOT / "assets")
        shutil.copytree(
            PROJECT_ROOT / "activities" / "writing",
            os_root / "activities" / "writing",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        environment = mock.patch.dict(
            os.environ,
            {
                "GREIA_OS_ROOT": str(os_root),
                "GREIA_PARENT_ACTIVITY_PACKAGE_ROOT": str(self.root / "packages"),
            },
        )
        environment.start()
        self.addCleanup(environment.stop)
        self.app = PackageParentApiApplication(
            os_root,
            self.root / "parent",
            profiles_dir=self.root / "profiles",
            hardware_settings_dir=self.root / "hardware",
            hardware_status_path=self.root / "hardware-status.json",
            active_profile_status_path=self.root / "active-profile.json",
            wifi_backend=DemoWifiBackend(),
            ssh_service=SshMaintenanceService(MockSshMaintenanceProvider()),
        )
        archive = self.root / "probe.greiaactivity"
        _write_installed_activity_archive(archive)
        self.app.package_service.install_archive(archive)
        self.profile_id = self.app.profile_store.list_profiles()[0].profile_id

    def _client_overrides(self, **explicit: str) -> dict[str, object]:
        """Mirror the HTML client: one entry per listed Activity, null = auto."""

        return {
            str(item["activity_id"]): explicit.get(str(item["activity_id"]))
            for item in self.app.activities_payload()
        }

    def test_installed_activity_is_in_policy_catalogue_and_effective_set(self) -> None:
        listed = [item["activity_id"] for item in self.app.activities_payload()]
        self.assertEqual(listed, ["org.greia.writing", INSTALLED_ACTIVITY_ID])
        payload = self.app.activity_policy_payload(self.profile_id)
        self.assertIn(INSTALLED_ACTIVITY_ID, payload["effective_activity_ids"])

    def test_override_for_installed_activity_is_accepted_and_applied(self) -> None:
        hidden = self.app.update_activity_policy(
            self.profile_id,
            visibility_mode="show_all",
            difficulty_min=1,
            difficulty_max=10,
            overrides={INSTALLED_ACTIVITY_ID: "always_hide"},
        )
        self.assertEqual(hidden["overrides"], {INSTALLED_ACTIVITY_ID: "always_hide"})
        self.assertNotIn(INSTALLED_ACTIVITY_ID, hidden["effective_activity_ids"])

        shown = self.app.update_activity_policy(
            self.profile_id,
            visibility_mode="show_all",
            difficulty_min=1,
            difficulty_max=10,
            overrides={INSTALLED_ACTIVITY_ID: "always_show"},
        )
        self.assertIn(INSTALLED_ACTIVITY_ID, shown["effective_activity_ids"])

    def test_client_shaped_put_with_null_for_installed_activity_succeeds(self) -> None:
        issued = self.app.bootstrap_device("greia", "Test browser")
        credential = str(issued["credential"])
        server = PackageParentApiHTTPServer(("127.0.0.1", 0), self.app)
        thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"poll_interval": 0.05},
            daemon=True,
        )
        thread.start()
        try:
            port = server.server_address[1]
            url = (
                f"http://127.0.0.1:{port}{API_BASE}/profiles/"
                f"{self.profile_id}/activity-policy"
            )
            body = {
                "visibility_mode": "show_all",
                "difficulty_min": 1,
                "difficulty_max": 10,
                "overrides": self._client_overrides(),
            }
            self.assertIsNone(body["overrides"][INSTALLED_ACTIVITY_ID])  # type: ignore[index]
            request = urllib.request.Request(
                url, data=json.dumps(body).encode("utf-8"), method="PUT"
            )
            request.add_header("Authorization", f"Bearer {credential}")
            request.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(request, timeout=60) as response:
                self.assertEqual(response.status, 200)
                payload = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertEqual(payload["overrides"], {})
        self.assertIn(INSTALLED_ACTIVITY_ID, payload["effective_activity_ids"])

    def test_stale_override_for_removed_activity_can_be_cleared(self) -> None:
        self.app.update_activity_policy(
            self.profile_id,
            visibility_mode="show_all",
            difficulty_min=1,
            difficulty_max=10,
            overrides={INSTALLED_ACTIVITY_ID: "always_hide"},
        )
        self.app.package_service.uninstall(INSTALLED_ACTIVITY_ID)
        stale = self.app.activity_policy_payload(self.profile_id)
        self.assertEqual(stale["overrides"], {INSTALLED_ACTIVITY_ID: "always_hide"})
        self.assertNotIn(INSTALLED_ACTIVITY_ID, stale["effective_activity_ids"])

        for cleared_value in (None, "default"):
            cleared = self.app.update_activity_policy(
                self.profile_id,
                visibility_mode="show_all",
                difficulty_min=1,
                difficulty_max=10,
                overrides={INSTALLED_ACTIVITY_ID: cleared_value},
            )
            self.assertEqual(cleared["overrides"], {})

        # Setting a real visibility for an id that is not installed stays an error.
        with self.assertRaisesRegex(Exception, "unknown Activity visibility override"):
            self.app.update_activity_policy(
                self.profile_id,
                visibility_mode="show_all",
                difficulty_min=1,
                difficulty_max=10,
                overrides={INSTALLED_ACTIVITY_ID: "always_show"},
            )

    def test_unloadable_installed_set_degrades_to_built_ins_like_the_shell(self) -> None:
        with mock.patch.object(
            self.app.package_service,
            "load_active_registrations",
            side_effect=ActivityPackageError("damaged active set"),
        ):
            payload = self.app.activity_policy_payload(self.profile_id)
            self.assertEqual(payload["effective_activity_ids"], ["org.greia.writing"])
            cleared = self.app.update_activity_policy(
                self.profile_id,
                visibility_mode="show_all",
                difficulty_min=1,
                difficulty_max=10,
                overrides={"org.greia.writing": None, INSTALLED_ACTIVITY_ID: None},
            )
            self.assertEqual(cleared["overrides"], {})

    def test_base_composition_tolerates_clearing_unknown_ids(self) -> None:
        base = self.root / "base"
        app = ParentApiApplication(
            self.app.root,
            base / "parent",
            profiles_dir=base / "profiles",
            hardware_settings_dir=base / "hardware",
            hardware_status_path=base / "hardware-status.json",
            active_profile_status_path=base / "active-profile.json",
            wifi_backend=DemoWifiBackend(),
            ssh_service=SshMaintenanceService(MockSshMaintenanceProvider()),
        )
        profile_id = app.profile_store.list_profiles()[0].profile_id
        cleared = app.update_activity_policy(
            profile_id,
            visibility_mode="show_all",
            difficulty_min=1,
            difficulty_max=10,
            overrides={INSTALLED_ACTIVITY_ID: None},
        )
        self.assertEqual(cleared["overrides"], {})
        with self.assertRaisesRegex(Exception, "unknown Activity visibility override"):
            app.update_activity_policy(
                profile_id,
                visibility_mode="show_all",
                difficulty_min=1,
                difficulty_max=10,
                overrides={INSTALLED_ACTIVITY_ID: "always_hide"},
            )
        with self.assertRaisesRegex(Exception, "invalid Activity identifier"):
            app.update_activity_policy(
                profile_id,
                visibility_mode="show_all",
                difficulty_min=1,
                difficulty_max=10,
                overrides={"Bad/Id": None},
            )
