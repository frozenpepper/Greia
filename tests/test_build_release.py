from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "build_release_tool",
    Path(__file__).resolve().parents[1] / "tools" / "build_release.py",
)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
import sys

sys.modules[spec.name] = module
spec.loader.exec_module(module)


class BuildReleaseTests(unittest.TestCase):
    def _staging(self, root: Path) -> Path:
        staging = root / "staging"
        (staging / "etc" / "greia-os").mkdir(parents=True)
        (staging / "etc" / "greia-os" / "build-info").write_text(
            "GREIA_OS_VERSION=0.15.0\n", encoding="utf-8"
        )
        (staging / "opt" / "greia-os" / "src").mkdir(parents=True)
        (staging / "opt" / "greia-os" / "src" / "placeholder.py").write_text(
            "# placeholder\n", encoding="utf-8"
        )
        return staging

    def test_payload_build_and_verify_with_headroom(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = self._staging(root)
            kernel = root / "vmlinuz"
            kernel.write_bytes(b"generic-kernel" * 64)
            initramfs = root / "initrd"
            initramfs.write_bytes(b"generic-initramfs" * 64)
            output = root / "payload.bin"
            result = module.build_release_payload(
                staging_dir=staging,
                kernel_path=kernel,
                initramfs_path=initramfs,
                output=output,
                profile_id="legacy-x86-i686",
                release_id="greia-0.15.0",
                release_sequence=11,
                filesystem_bytes=4 * 1024 * 1024,
                minimum_slot_bytes=5 * 1024 * 1024,
            )
            self.assertEqual(output.stat().st_size, 4 * 1024 * 1024)
            self.assertIn("sha256", result)
            payload = module.verify_release_payload(output)
            self.assertGreaterEqual(payload["members"], 4)
            # Deterministic: rebuild into a second file from the same staging.
            staging2 = self._staging(root / "second-root")
            output2 = root / "payload2.bin"
            module.build_release_payload(
                staging_dir=staging2,
                kernel_path=kernel,
                initramfs_path=initramfs,
                output=output2,
                profile_id="legacy-x86-i686",
                release_id="greia-0.15.0",
                release_sequence=11,
                filesystem_bytes=4 * 1024 * 1024,
                minimum_slot_bytes=5 * 1024 * 1024,
            )
            self.assertEqual(
                output.read_bytes()[:8192], output2.read_bytes()[:8192]
            )

    def test_payload_rejects_missing_required_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging"
            staging.mkdir()
            kernel = root / "vmlinuz"
            kernel.write_bytes(b"k")
            initramfs = root / "initrd"
            initramfs.write_bytes(b"i")
            with self.assertRaises(module.ReleaseBuildError):
                module.build_release_payload(
                    staging_dir=staging,
                    kernel_path=kernel,
                    initramfs_path=initramfs,
                    output=root / "payload.bin",
                    profile_id="legacy-x86-i686",
                    release_id="greia-0.15.0",
                    release_sequence=1,
                    filesystem_bytes=2 * 1024 * 1024,
                    minimum_slot_bytes=2 * 1024 * 1024,
                )

    def test_persistent_contract_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "a.json"
            second = root / "b.json"
            module.build_persistent_contract(first)
            module.build_persistent_contract(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            parsed = json.loads(first.read_text(encoding="utf-8"))
            self.assertEqual(parsed["schema_version"], 1)
            self.assertIn("child-profiles", parsed["namespaces"])

    def test_hardware_support_rejects_executable_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = root / "pool-root"
            pool.mkdir()
            (pool / "pool").mkdir()
            (pool / "manifest.json").write_text("{}", encoding="utf-8")
            hook = pool / "evil.hook"
            hook.write_text("#!/bin/sh\n", encoding="utf-8")
            hook.chmod(0o755)
            with self.assertRaises(module.ReleaseBuildError):
                module._assert_no_hooks(pool)


if __name__ == "__main__":
    unittest.main()
