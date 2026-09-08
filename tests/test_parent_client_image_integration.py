from __future__ import annotations

import json
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
