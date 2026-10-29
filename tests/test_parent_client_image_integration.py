from __future__ import annotations

import json
import os
import stat
import subprocess
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path

from greia_parent.parent_client_integrity import (
    ParentClientIntegrityError,
    ParentClientRuntimeContract,
)


ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / "runtime" / "parent-app-client.toml"
MANIFEST = ROOT / "runtime" / "parent-app-client.manifest.json"
VENDORED = ROOT / "vendor" / "parent-app"
IMAGE_OVERLAY = ROOT / "build" / "overlay" / "usr" / "share" / "greia-parent-app"


class ParentClientImageIntegrationTests(unittest.TestCase):
    def test_vendored_and_image_runtime_match_exact_frozen_contract(self) -> None:
        contract = ParentClientRuntimeContract.load(MANIFEST, PIN)
        contract.verify(VENDORED)
        contract.verify(IMAGE_OVERLAY)

    def test_parent_app_renders_the_connected_wifi_state(self) -> None:
        js = (IMAGE_OVERLAY / "src" / "views_device.js").read_text(encoding="utf-8")
        self.assertIn("connected_ssid", js)
        self.assertIn('tr("device.wifi.connected_state", { name: connected })', js)
        self.assertIn('tr("device.wifi.not_connected_state")', js)
        strings = (IMAGE_OVERLAY / "src" / "localization.js").read_text(encoding="utf-8")
        self.assertIn('"en": "Connected to {name}"', strings)
        self.assertIn('"en": "Not connected to Wi-Fi"', strings)

    def test_parent_app_refreshes_wifi_when_device_view_opens(self) -> None:
        js = (IMAGE_OVERLAY / "src" / "app.js").read_text(encoding="utf-8")
        self.assertIn("_refreshWifiForDevice", js)
        self.assertIn("refreshWifi", js)
        self.assertIn('this.route !== "device"', js)

    def test_production_manifest_excludes_demo_fixtures(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertFalse(any(path.startswith("src/demo") for path in manifest["files"]))
        self.assertFalse((IMAGE_OVERLAY / "src" / "demo_api.js").exists())
        self.assertFalse((IMAGE_OVERLAY / "src" / "demo_management_api.js").exists())

    def test_pin_records_completed_vendored_image_integration(self) -> None:
        with PIN.open("rb") as handle:
            pin = tomllib.load(handle)
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(pin["repository"], manifest["repository"])
        self.assertEqual(pin["revision"], manifest["revision"])
        self.assertEqual(pin["runtime_root"], "/usr/share/greia-parent-app")
        self.assertEqual(pin["integration_state"], "vendored-image-integrity-enforced")

    def test_composition_normalizes_restrictive_parent_runtime_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            web = root / "usr/share/greia-parent-app"
            (web / "src").mkdir(parents=True)
            (web / "src/app.js").write_text("ok", encoding="utf-8")
            web.chmod(0o700)
            (web / "src").chmod(0o700)
            (web / "src/app.js").chmod(0o600)
            subprocess.run(["bash", "-c", 'source "$1"; compose_normalize_parent_client_permissions "$2"',
                "bash", str(ROOT / "build/lib/compose.sh"), str(root)], check=True)
            self.assertEqual(stat.S_IMODE(web.stat().st_mode), 0o755)
            self.assertEqual(stat.S_IMODE((web / "src").stat().st_mode), 0o755)
            self.assertEqual(stat.S_IMODE((web / "src/app.js").stat().st_mode), 0o644)

    def test_contract_rejects_unexpected_runtime_file(self) -> None:
        contract = ParentClientRuntimeContract.load(MANIFEST, PIN)
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / "parent-app"
            shutil.copytree(VENDORED, runtime)
            (runtime / "src" / "unexpected.js").write_text("export {};\n", encoding="utf-8")
            with self.assertRaisesRegex(ParentClientIntegrityError, "unexpected"):
                contract.verify(runtime)

    def test_contract_rejects_tampered_runtime_file(self) -> None:
        contract = ParentClientRuntimeContract.load(MANIFEST, PIN)
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / "parent-app"
            shutil.copytree(VENDORED, runtime)
            app = runtime / "src" / "app.js"
            app.write_text(app.read_text(encoding="utf-8") + "\n// tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(ParentClientIntegrityError, "size mismatch|digest mismatch"):
                contract.verify(runtime)


if __name__ == "__main__":
    unittest.main()
