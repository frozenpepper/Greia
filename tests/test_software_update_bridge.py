from __future__ import annotations

import os
import json
import shutil
import hashlib
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from greia_platform.software_update_bridge import (
    _archive_base,
    _extract_source_archive,
    build_receiver_bridge,
)
from greia_platform.software_update_package import (
    SoftwareUpdatePackageError,
    build_software_update_package,
    inspect_software_update_package,
)
from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.activity_index import build_index
from greia_platform.software_update_generation import GenerationLayout
from greia_platform.trust import ActivitySource, PackageTrust


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEGACY_BASE = "1275e0be1a9e0cda724ce18151ae65a25f03c98c"


class SoftwareUpdateBridgeTests(unittest.TestCase):
    def test_bridge_is_accepted_by_real_legacy_reader_and_current_data_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bridge = root / "bridge.greia_update"
            base_sha, manifest = build_receiver_bridge(
                bridge,
                base_ref=LEGACY_BASE,
                repository_root=PROJECT_ROOT,
                python_source_root=PROJECT_ROOT,
                version="1.0.0",
                release_id="greia-receiver-bridge-test",
            )
            self.assertEqual(base_sha, LEGACY_BASE)
            self.assertFalse(any("/languages/" in item.path for item in manifest.python_files))
            self.assertEqual(inspect_software_update_package(bridge).manifest.type.value, "python_platform")

            current = root / "current.greia_update"
            build_software_update_package(
                current,
                version="1.0.1",
                release_id="greia-current-languages-test",
                python_source_root=PROJECT_ROOT,
            )
            current_manifest = inspect_software_update_package(current).manifest
            self.assertTrue(any("/languages/" in item.path for item in current_manifest.python_files))

            tar_path = root / "base.tar"
            _archive_base(PROJECT_ROOT, LEGACY_BASE, tar_path)
            base_source = root / "legacy"
            base_source.mkdir()
            _extract_source_archive(tar_path, base_source)
            env = dict(os.environ)
            env["PYTHONPATH"] = str(base_source / "src")
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            script = """import sys
from pathlib import Path
from greia_platform.software_update_package import SoftwareUpdatePackageError, inspect_software_update_package
inspect_software_update_package(Path(sys.argv[1]))
try:
    inspect_software_update_package(Path(sys.argv[2]))
except SoftwareUpdatePackageError:
    raise SystemExit(23)
raise SystemExit(0)
"""
            result = subprocess.run(
                [sys.executable, "-c", script, str(bridge), str(current)],
                cwd=root,
                env=env,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(result.returncode, 23, result.stderr or result.stdout)

    def test_bridge_rejects_unresolvable_base(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "does not resolve"):
                build_receiver_bridge(
                    Path(directory) / "bridge.greia_update",
                    base_ref="not-a-real-greia-base",
                    repository_root=PROJECT_ROOT,
                    python_source_root=PROJECT_ROOT,
                    version="1.0.0",
                    release_id="greia-receiver-bridge-test",
                )

    def test_bridge_cli_resolves_relative_output_from_calling_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "relative.greia_update"
            tool = PROJECT_ROOT / "tools/greia_software_update.py"
            result = subprocess.run(
                [
                    sys.executable,
                    str(tool),
                    "build-receiver-bridge",
                    "--base-ref",
                    LEGACY_BASE,
                    "--version",
                    "1.0.0",
                    "--release-id",
                    "greia-relative-bridge-test",
                    "--output",
                    "relative",
                ],
                cwd=directory,
                env=dict(os.environ, PYTHONPATH=str(PROJECT_ROOT / "src"), PYTHONDONTWRITEBYTECODE="1"),
                check=False,
                capture_output=True,
                text=True,
                timeout=80,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            result_record = json.loads(result.stdout.splitlines()[0])
            self.assertEqual(Path(result_record["path"]), Path("relative.greia_update"))

    def test_bridge_rejects_symlinked_receiver_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory) / "source"
            target = source_root / "src/greia_platform/software_update_package.py"
            target.parent.mkdir(parents=True)
            target.symlink_to(PROJECT_ROOT / "src/greia_platform/software_update_package.py")
            generation = target.parent / "software_update_generation.py"
            generation.write_text("# placeholder", encoding="utf-8")
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "overlay source is not a regular"):
                build_receiver_bridge(
                    Path(directory) / "bridge.greia_update",
                    base_ref=LEGACY_BASE,
                    repository_root=PROJECT_ROOT,
                    python_source_root=source_root,
                    version="1.0.0",
                    release_id="greia-receiver-bridge-test",
                )

    def test_two_step_bridge_stages_on_real_legacy_tree_then_accepts_current_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="greia-two-step-bridge-") as directory:
            root = Path(directory)
            archive_path = root / "1275-source.tar"
            _archive_base(PROJECT_ROOT, LEGACY_BASE, archive_path)
            exported = root / "exported"
            exported.mkdir()
            _extract_source_archive(archive_path, exported)

            generation_root = root / "opt/greia-software/generations"
            generation_root.mkdir(parents=True)
            base_generation = generation_root / "base"
            shutil.copytree(exported, base_generation)
            application_root = root / "opt/greia-os"
            application_root.symlink_to(Path("greia-software/generations/base"), target_is_directory=True)
            activities = base_generation / "activities"
            activities.mkdir()
            for folder in ("painting", "writing"):
                shutil.copytree(PROJECT_ROOT / "activities" / folder, activities / folder)
            (base_generation / "assets").mkdir()
            (base_generation / "assets/sentinel.bin").write_bytes(b"legacy asset preserved")
            runtime = RuntimeCatalogue.load(base_generation / "runtime/child-runtime.toml")
            source = ActivitySource(activities, PackageTrust.BUILT_IN, "greia-system")
            registrations = ActivityRegistry((source,), runtime).discover_registrations()
            build_index(registrations, source=source, runtime=runtime).write_file(
                base_generation / "activity-index-v1.json"
            )
            layout = GenerationLayout(
                application_root=application_root,
                generation_root=generation_root,
                activity_package_state=root / "var/lib/greia-os/activity-packages",
            )

            bridge = root / "bridge.greia_update"
            source_hash = hashlib.sha256(
                (PROJECT_ROOT / "src/greia_platform/software_update_package.py").read_bytes()
            ).hexdigest()
            base_registry = base_generation / "src/greia_platform/system_language.py"
            registry_hash = hashlib.sha256(base_registry.read_bytes()).hexdigest()
            build_receiver_bridge(
                bridge,
                base_ref=LEGACY_BASE,
                repository_root=PROJECT_ROOT,
                python_source_root=PROJECT_ROOT,
                version="1.0.0",
                release_id="greia-two-step-bridge-v1",
            )
            old_env = dict(os.environ, PYTHONPATH=str(base_generation / "src"), PYTHONDONTWRITEBYTECODE="1")
            old_stage_script = """import json, sys
from pathlib import Path
from greia_platform.software_update_package import inspect_software_update_package
from greia_platform.software_update_generation import ApplicationGenerationBuilder, GenerationLayout
layout = GenerationLayout(application_root=Path(sys.argv[2]), generation_root=Path(sys.argv[3]), activity_package_state=Path(sys.argv[4]))
inspected = inspect_software_update_package(Path(sys.argv[1]))
staged = ApplicationGenerationBuilder(layout).stage(Path(sys.argv[1]), inspected, job_id=sys.argv[5])
print(json.dumps({'path': str(staged.generation_path), 'previous': staged.previous_generation_id}))
"""
            first = subprocess.run(
                [sys.executable, "-c", old_stage_script, str(bridge), str(application_root), str(generation_root), str(layout.activity_package_state), "1" * 32],
                cwd=root,
                env=old_env,
                check=False,
                capture_output=True,
                text=True,
                timeout=40,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            first_path = Path(json.loads(first.stdout)["path"])
            legacy_import = subprocess.run(
                [sys.executable, "-c", "from greia_platform.system_language import SUPPORTED_SYSTEM_LOCALES; print(','.join(SUPPORTED_SYSTEM_LOCALES))"],
                cwd=root,
                env=dict(os.environ, PYTHONPATH=str(first_path / "src"), PYTHONDONTWRITEBYTECODE="1"),
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(legacy_import.returncode, 0, legacy_import.stderr)
            self.assertEqual(legacy_import.stdout.strip(), "en,it,es,fr")
            self.assertEqual(hashlib.sha256(base_registry.read_bytes()).hexdigest(), registry_hash)
            self.assertFalse((base_generation / "src/greia_platform/languages").exists())

            application_root.unlink()
            application_root.symlink_to(Path("greia-software/generations") / first_path.name, target_is_directory=True)
            current_package = root / "current.greia_update"
            build_software_update_package(
                current_package,
                version="1.0.1",
                release_id="greia-two-step-current-v1",
                python_source_root=PROJECT_ROOT,
            )
            current_inspected = inspect_software_update_package(current_package)
            self.assertTrue(any("/languages/" in item.path for item in current_inspected.manifest.python_files))
            second_run = subprocess.run(
                [sys.executable, "-c", old_stage_script, str(current_package), str(application_root), str(generation_root), str(layout.activity_package_state), "2" * 32],
                cwd=root,
                env=dict(os.environ, PYTHONPATH=str(first_path / "src"), PYTHONDONTWRITEBYTECODE="1"),
                check=False,
                capture_output=True,
                text=True,
                timeout=40,
            )
            self.assertEqual(second_run.returncode, 0, second_run.stderr)
            second_path = Path(json.loads(second_run.stdout)["path"])
            current_import = subprocess.run(
                [sys.executable, "-c", "import json; from greia_platform.system_language import SUPPORTED_SYSTEM_LOCALES; print(json.dumps(SUPPORTED_SYSTEM_LOCALES))"],
                cwd=root,
                env=dict(os.environ, PYTHONPATH=str(second_path / "src"), PYTHONDONTWRITEBYTECODE="1"),
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(current_import.returncode, 0, current_import.stderr)
            with zipfile.ZipFile(current_package) as archive:
                language_manifests = [
                    json.loads(archive.read(item.member))
                    for item in current_inspected.manifest.python_files
                    if item.path.endswith("/manifest.json")
                ]
            expected_locales = [
                row["locale"]
                for row in sorted(language_manifests, key=lambda item: (item.get("order", 1000), item["locale"]))
            ]
            self.assertEqual(json.loads(current_import.stdout), expected_locales)
            self.assertTrue((base_generation / "assets/sentinel.bin").is_file())
            self.assertEqual(
                hashlib.sha256((PROJECT_ROOT / "src/greia_platform/software_update_package.py").read_bytes()).hexdigest(),
                source_hash,
            )


if __name__ == "__main__":
    unittest.main()
