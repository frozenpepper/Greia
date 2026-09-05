from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from greia_launcher.runtime_adapter import (
    PythonRuntimeAdapter,
    PythonRuntimePolicy,
    RuntimeManager,
)
from greia_platform.activities import (
    ActivityRegistry,
    RuntimeCatalogue,
    package_digest,
)
from greia_platform.activity_index import ActivityIndex, ActivityIndexLoader
from greia_platform.device_capabilities import DeviceCapabilityService
from greia_platform.permissions import PermissionBroker, PermissionPolicy
from greia_platform.trust import ActivitySource, PackageTrust


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL = PROJECT_ROOT / "tools" / "build_activity_index.py"
RUNTIME_PATH = PROJECT_ROOT / "runtime" / "child-runtime.toml"


def _make_source_tree(temporary: str) -> Path:
    """Copy two small first-party packages into an isolated source root."""
    root = Path(temporary) / "activities"
    root.mkdir(parents=True)
    for name in ("shape_garden", "painting"):
        source = PROJECT_ROOT / "activities" / name
        if source.is_dir():
            shutil.copytree(source, root / name)
    return root


def _run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )


class BuildActivityIndexTests(unittest.TestCase):
    def test_generator_byte_identical_across_repeat_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source_root = _make_source_tree(temporary)
            first = Path(temporary) / "first.json"
            second = Path(temporary) / "second.json"
            for destination in (first, second):
                result = _run_tool(
                    "--activities", str(source_root),
                    "--runtime", str(RUNTIME_PATH),
                    "--output", str(destination),
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            payload = first.read_bytes()
            # Deterministic serialization contract: UTF-8, newline terminated,
            # stable sorted key ordering, sorted registrations.
            self.assertTrue(payload.endswith(b"\n"))
            text = payload.decode("utf-8")
            self.assertEqual(text.encode("utf-8"), payload)
            positions = [
                text.index(f'"{key}"')
                for key in (
                    "generated_from_policy_hash",
                    "generated_from_policy_version",
                    "package_trust",
                    "platform_activity_api_version",
                    "registrations",
                    "schema_version",
                    "source_id",
                )
            ]
            self.assertEqual(positions, sorted(positions))
            activity_ids = [
                entry["activity_id"] for entry in json.loads(text)["registrations"]
            ]
            self.assertEqual(activity_ids, sorted(activity_ids))
            self.assertGreaterEqual(len(activity_ids), 1)

    def test_invalid_builtin_fails_closed_without_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source_root = _make_source_tree(temporary)
            destination = Path(temporary) / "index.json"
            # Seed a valid output first so the fail-closed run must preserve it.
            seeded = _run_tool(
                "--activities", str(source_root),
                "--runtime", str(RUNTIME_PATH),
                "--output", str(destination),
            )
            self.assertEqual(seeded.returncode, 0, msg=seeded.stderr)
            before = destination.read_bytes()
            # Inject an invalid built-in package: a forbidden executable suffix
            # that the authoritative registry tree validation must reject.
            bad_package = source_root / "shape_garden"
            (bad_package / "evil.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            failed = _run_tool(
                "--activities", str(source_root),
                "--runtime", str(RUNTIME_PATH),
                "--output", str(destination),
            )
            self.assertNotEqual(failed.returncode, 0)
            # No partial output: the previously written index is byte-preserved,
            # and no staging file is left behind.
            self.assertEqual(destination.read_bytes(), before)
            self.assertFalse(destination.with_name(destination.name + ".tmp").exists())

    def test_invalid_builtin_creates_no_output_when_none_existed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source_root = _make_source_tree(temporary)
            (source_root / "shape_garden" / "payload.exe").write_bytes(b"MZ")
            destination = Path(temporary) / "fresh.json"
            result = _run_tool(
                "--activities", str(source_root),
                "--runtime", str(RUNTIME_PATH),
                "--output", str(destination),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(destination.exists())
            self.assertFalse(destination.with_name(destination.name + ".tmp").exists())

    def test_recorded_digests_equal_package_digest_of_validated_trees(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source_root = _make_source_tree(temporary)
            destination = Path(temporary) / "index.json"
            result = _run_tool(
                "--activities", str(source_root),
                "--runtime", str(RUNTIME_PATH),
                "--output", str(destination),
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            index = ActivityIndex.load_file(destination)
            runtime = RuntimeCatalogue.load(RUNTIME_PATH)
            source = ActivitySource(
                source_root, PackageTrust.BUILT_IN, "greia-system"
            )
            registry = ActivityRegistry([source], runtime)
            registrations = registry.discover_registrations()
            expected = {item.manifest.activity_id: item for item in registrations}
            self.assertGreaterEqual(len(expected), 1)
            self.assertEqual(len(index.registrations), len(expected))
            for entry in index.registrations:
                original = expected[entry.activity_id]
                tree_digest = package_digest(original.manifest.root)
                self.assertEqual(entry.package_digest, original.package_digest)
                self.assertEqual(entry.package_digest, tree_digest)
                on_disk = source_root / entry.package_relpath
                self.assertEqual(entry.package_digest, package_digest(on_disk))

    def test_launch_path_and_digest_semantics_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source_root = _make_source_tree(temporary)
            destination = Path(temporary) / "index.json"
            result = _run_tool(
                "--activities", str(source_root),
                "--runtime", str(RUNTIME_PATH),
                "--output", str(destination),
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            runtime = RuntimeCatalogue.load(RUNTIME_PATH)
            source = ActivitySource(
                source_root, PackageTrust.BUILT_IN, "greia-system"
            )
            registry = ActivityRegistry([source], runtime)
            registrations = registry.discover_registrations()
            loader = ActivityIndexLoader.from_runtime(source, runtime)
            rebuilt = loader.load_file(destination)
            expected = {item.manifest.activity_id: item for item in registrations}
            self.assertEqual(len(rebuilt), len(registrations))
            broker = PermissionBroker(
                PermissionPolicy.phase0(runtime),
                DeviceCapabilityService.static(
                    set(runtime.allowed_capabilities),
                    source_id="build-activity-index-test",
                ),
            )
            manager = RuntimeManager(
                [PythonRuntimeAdapter(policy=PythonRuntimePolicy.load(RUNTIME_PATH))],
                DeviceCapabilityService.static(
                    set(runtime.allowed_capabilities),
                    source_id="build-activity-index-test",
                ),
            )
            for item in rebuilt:
                original = expected[item.manifest.activity_id]
                self.assertEqual(item.package_digest, original.package_digest)
                self.assertEqual(
                    item.package_digest, package_digest(original.manifest.root)
                )
                self.assertEqual(item.package_trust, PackageTrust.BUILT_IN)
                self.assertEqual(item.source_id, "greia-system")
                self.assertEqual(item.manifest.root, original.manifest.root)
                self.assertEqual(item.manifest.launch_path, original.manifest.launch_path)
                self.assertTrue(item.manifest.launch_path.is_file())
                self.assertEqual(item.manifest.entrypoint, original.manifest.entrypoint)
                self.assertEqual(broker.issue(item), broker.issue(original))
                manager.validate_package(item.manifest)

    def test_generator_reuses_authoritative_registry_without_second_validator(self) -> None:
        text = TOOL.read_text(encoding="utf-8")
        self.assertIn("ActivityRegistry", text)
        self.assertIn("discover_registrations", text)
        self.assertIn("build_index", text)
        self.assertIn("RuntimeCatalogue.load", text)
        for forbidden in (
            "_validate_tree",
            "_parse_manifest",
            "_validate_manifest",
            "forbidden_suffixes",
            "forbidden_file_names",
            "ast.parse",
            "tomllib",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
