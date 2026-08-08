from __future__ import annotations

import shutil
import tempfile
import textwrap
import unittest
from pathlib import Path

from greia_platform.activities import ActivityRegistry, ActivityValidationError, RuntimeCatalogue


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = PROJECT_ROOT / "runtime" / "child-runtime.toml"


class ActivityContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = RuntimeCatalogue.load(RUNTIME_PATH)

    def test_sample_activity_is_discovered(self) -> None:
        registry = ActivityRegistry([PROJECT_ROOT / "activities"], self.runtime)
        activities = registry.discover()
        self.assertEqual(
            [activity.activity_id for activity in activities],
            ["shape_garden", "workshop_settings"],
        )
        self.assertEqual(activities[0].icon_id, "garden")
        self.assertIn("customization.manage", activities[1].capabilities)

    def test_forbidden_dependency_file_is_rejected(self) -> None:
        with self._copy_sample() as root:
            (root / "requirements.txt").write_text("requests\n", encoding="utf-8")
            with self.assertRaisesRegex(ActivityValidationError, "forbidden package file"):
                ActivityRegistry([root.parent], self.runtime).validate_package(root)

    def test_forbidden_dependency_directory_is_rejected(self) -> None:
        with self._copy_sample() as root:
            (root / ".venv").mkdir()
            with self.assertRaisesRegex(ActivityValidationError, "forbidden package directory"):
                ActivityRegistry([root.parent], self.runtime).validate_package(root)

    def test_executable_file_is_rejected(self) -> None:
        with self._copy_sample() as root:
            payload = root / "payload"
            payload.write_text("not executable code", encoding="utf-8")
            payload.chmod(0o755)
            with self.assertRaisesRegex(ActivityValidationError, "executable activity files"):
                ActivityRegistry([root.parent], self.runtime).validate_package(root)

    def test_forbidden_import_is_rejected(self) -> None:
        with self._copy_sample() as root:
            (root / "main.py").write_text("import subprocess\n", encoding="utf-8")
            with self.assertRaisesRegex(ActivityValidationError, "forbidden import"):
                ActivityRegistry([root.parent], self.runtime).validate_package(root)

    def test_unknown_third_party_import_is_rejected(self) -> None:
        with self._copy_sample() as root:
            (root / "main.py").write_text("import requests\n", encoding="utf-8")
            with self.assertRaisesRegex(ActivityValidationError, "outside the curated child runtime"):
                ActivityRegistry([root.parent], self.runtime).validate_package(root)

    def test_dynamic_import_is_rejected(self) -> None:
        with self._copy_sample() as root:
            (root / "main.py").write_text("__import__('pygame')\n", encoding="utf-8")
            with self.assertRaisesRegex(ActivityValidationError, "dynamic imports are forbidden"):
                ActivityRegistry([root.parent], self.runtime).validate_package(root)

    def test_entrypoint_escape_is_rejected(self) -> None:
        with self._copy_sample() as root:
            manifest = (root / "activity.toml").read_text(encoding="utf-8")
            manifest = manifest.replace('entrypoint = "main.py"', 'entrypoint = "../main.py"')
            (root / "activity.toml").write_text(manifest, encoding="utf-8")
            with self.assertRaisesRegex(ActivityValidationError, "safe relative path"):
                ActivityRegistry([root.parent], self.runtime).validate_package(root)

    def test_symlink_is_rejected(self) -> None:
        with self._copy_sample() as root:
            target = root / "linked.py"
            try:
                target.symlink_to(root / "main.py")
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(ActivityValidationError, "symlinks are forbidden"):
                ActivityRegistry([root.parent], self.runtime).validate_package(root)

    def test_sitecustomize_auto_execution_file_is_rejected(self) -> None:
        with self._copy_sample() as root:
            (root / "sitecustomize.py").write_text("raise SystemExit()\n", encoding="utf-8")
            with self.assertRaisesRegex(ActivityValidationError, "forbidden package file"):
                ActivityRegistry([root.parent], self.runtime).validate_package(root)

    def test_activity_cannot_shadow_curated_python_module(self) -> None:
        with self._copy_sample() as root:
            (root / "pygame.py").write_text("# fake runtime module\n", encoding="utf-8")
            with self.assertRaisesRegex(ActivityValidationError, "shadow curated module"):
                ActivityRegistry([root.parent], self.runtime).validate_package(root)

    def test_unknown_capability_is_rejected(self) -> None:
        with self._copy_sample() as root:
            manifest = (root / "activity.toml").read_text(encoding="utf-8")
            manifest = manifest.replace(
                'capabilities = ["display", "pointer", "audio.basic"]',
                'capabilities = ["display", "pointer", "kernel.root"]',
            )
            (root / "activity.toml").write_text(manifest, encoding="utf-8")
            with self.assertRaisesRegex(ActivityValidationError, "unknown capabilities"):
                ActivityRegistry([root.parent], self.runtime).validate_package(root)

    def test_privileged_capability_is_limited_to_trusted_built_in_activity(self) -> None:
        with self._copy_sample() as root:
            manifest = (root / "activity.toml").read_text(encoding="utf-8")
            manifest = manifest.replace(
                'capabilities = ["display", "pointer", "audio.basic"]',
                'capabilities = ["display", "pointer", "customization.manage"]',
            )
            (root / "activity.toml").write_text(manifest, encoding="utf-8")
            with self.assertRaisesRegex(ActivityValidationError, "not trusted"):
                ActivityRegistry([root.parent], self.runtime).validate_package(root)

    def test_duplicate_capabilities_are_rejected(self) -> None:
        with self._copy_sample() as root:
            manifest = (root / "activity.toml").read_text(encoding="utf-8")
            manifest = manifest.replace(
                'capabilities = ["display", "pointer", "audio.basic"]',
                'capabilities = ["display", "display"]',
            )
            (root / "activity.toml").write_text(manifest, encoding="utf-8")
            with self.assertRaisesRegex(ActivityValidationError, "must not contain duplicates"):
                ActivityRegistry([root.parent], self.runtime).validate_package(root)

    def test_discovery_token_changes_when_activity_manifest_changes(self) -> None:
        with self._copy_sample() as root:
            registry = ActivityRegistry([root.parent], self.runtime)
            before = registry.discovery_token()
            manifest = root / "activity.toml"
            manifest.write_text(manifest.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            after = registry.discovery_token()
            self.assertNotEqual(before, after)


    def test_runtime_rejects_import_root_present_in_both_lists(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "runtime.toml"
            content = RUNTIME_PATH.read_text(encoding="utf-8").replace(
                'forbidden_import_roots = [',
                'forbidden_import_roots = [\n  "pygame",',
                1,
            )
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ActivityValidationError, "both allowed and forbidden"):
                RuntimeCatalogue.load(path)

    def test_runtime_rejects_privileged_capability_not_in_allowed_set(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "runtime.toml"
            content = RUNTIME_PATH.read_text(encoding="utf-8").replace(
                'privileged = [',
                'privileged = [\n  "kernel.root",',
                1,
            )
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ActivityValidationError, "must also be allowed"):
                RuntimeCatalogue.load(path)

    def test_runtime_rejects_unsafe_privileged_activity_identifier(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "runtime.toml"
            content = RUNTIME_PATH.read_text(encoding="utf-8").replace(
                'privileged_activity_ids = ["workshop_settings"]',
                'privileged_activity_ids = ["Workshop Settings"]',
            )
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ActivityValidationError, "identifiers are unsafe"):
                RuntimeCatalogue.load(path)

    def test_api_mismatch_is_rejected(self) -> None:
        with self._copy_sample() as root:
            manifest = (root / "activity.toml").read_text(encoding="utf-8")
            manifest = manifest.replace('api_version = "0.1"', 'api_version = "9.9"')
            (root / "activity.toml").write_text(manifest, encoding="utf-8")
            with self.assertRaisesRegex(ActivityValidationError, "targets API"):
                ActivityRegistry([root.parent], self.runtime).validate_package(root)

    def _copy_sample(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "shape_garden"
        shutil.copytree(PROJECT_ROOT / "activities" / "shape_garden", root)

        class Context:
            def __enter__(self_nonlocal):
                return root

            def __exit__(self_nonlocal, *args: object):
                temporary.cleanup()

        return Context()


if __name__ == "__main__":
    unittest.main()
