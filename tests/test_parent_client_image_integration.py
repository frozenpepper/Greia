from __future__ import annotations

import hashlib
import json
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
PARENT_APP = ROOT / "parent-app"
IMAGE_OVERLAY = ROOT / "build" / "overlay" / "usr" / "share" / "greia-parent-app"


class ParentClientImageIntegrationTests(unittest.TestCase):
    def test_image_overlay_matches_exact_frozen_contract(self) -> None:
        contract = ParentClientRuntimeContract.load(MANIFEST, PIN)
        contract.verify(IMAGE_OVERLAY)

    def test_parent_app_source_matches_pinned_runtime_bytes(self) -> None:
        """Fail when parent-app/ runtime files changed without repinning the image."""

        contract = ParentClientRuntimeContract.load(MANIFEST, PIN)
        advice = (
            "run tools/update_parent_client_pin.py after committing parent-app/ "
            "(the image overlay and runtime/parent-app-client.* must be repinned)"
        )
        manifest_paths = {item.path for item in contract.files}
        overlay_paths = {
            path.relative_to(IMAGE_OVERLAY).as_posix()
            for path in IMAGE_OVERLAY.rglob("*")
            if path.is_file()
        }
        self.assertEqual(overlay_paths, manifest_paths, f"overlay file set drifted: {advice}")
        for item in contract.files:
            source = PARENT_APP / item.path
            self.assertTrue(source.is_file(), f"parent-app/{item.path} is missing: {advice}")
            data = source.read_bytes()
            self.assertEqual(
                hashlib.sha256(data).hexdigest(),
                item.sha256,
                f"parent-app/{item.path} differs from the pinned manifest: {advice}",
            )
            self.assertEqual(len(data), item.bytes, f"parent-app/{item.path} size drifted: {advice}")
            self.assertEqual(
                data,
                (IMAGE_OVERLAY / item.path).read_bytes(),
                f"overlay/{item.path} differs from parent-app/{item.path}: {advice}",
            )

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

    def test_pin_records_completed_image_integration(self) -> None:
        with PIN.open("rb") as handle:
            pin = tomllib.load(handle)
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(pin["repository"], manifest["repository"])
        self.assertEqual(pin["revision"], manifest["revision"])
        self.assertEqual(pin["repository"], "frozenpepper/Greia:parent-app")
        # The revision is the Git tree id of the committed parent-app/ directory.
        self.assertRegex(pin["revision"], r"^[0-9a-f]{40}$")
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
            shutil.copytree(IMAGE_OVERLAY, runtime)
            (runtime / "src" / "unexpected.js").write_text("export {};\n", encoding="utf-8")
            with self.assertRaisesRegex(ParentClientIntegrityError, "unexpected"):
                contract.verify(runtime)

    def test_contract_rejects_tampered_runtime_file(self) -> None:
        contract = ParentClientRuntimeContract.load(MANIFEST, PIN)
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / "parent-app"
            shutil.copytree(IMAGE_OVERLAY, runtime)
            app = runtime / "src" / "app.js"
            app.write_text(app.read_text(encoding="utf-8") + "\n// tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(ParentClientIntegrityError, "size mismatch|digest mismatch"):
                contract.verify(runtime)


if __name__ == "__main__":
    unittest.main()
