from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_launcher.runtime_adapter import (
    PythonRuntimeAdapter,
    PythonRuntimePolicy,
    RuntimeManager,
)
from greia_platform.activities import (
    ActivityRegistry,
    ActivityValidationError,
    RuntimeCatalogue,
    package_digest,
)
from greia_platform.activity_index import (
    ActivityIndex,
    ActivityIndexEntry,
    ActivityIndexError,
    ActivityIndexLoader,
    build_index,
    runtime_policy_fingerprint,
)
from greia_platform.device_capabilities import DeviceCapabilityService
from greia_platform.permissions import PermissionBroker, PermissionPolicy
from greia_platform.trust import ActivitySource, PackageTrust


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = PROJECT_ROOT / "runtime" / "child-runtime.toml"


def _make_source_tree(temporary: str) -> tuple[Path, ActivitySource, RuntimeCatalogue]:
    """Copy two small first-party packages into an isolated source root."""
    root = Path(temporary) / "activities"
    root.mkdir(parents=True)
    for name in ("shape_garden", "painting"):
        source = PROJECT_ROOT / "activities" / name
        if source.is_dir():
            shutil.copytree(source, root / name)
    runtime = RuntimeCatalogue.load(RUNTIME_PATH)
    source_desc = ActivitySource(root, PackageTrust.BUILT_IN, "greia-system")
    return root, source_desc, runtime


def _discover(source: ActivitySource, runtime: RuntimeCatalogue):
    registry = ActivityRegistry([source], runtime)
    return registry.discover_registrations()


class ActivityIndexTests(unittest.TestCase):
    def test_roundtrip_preserves_manifest_digest_and_launch_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, source, runtime = _make_source_tree(temporary)
            registrations = _discover(source, runtime)
            self.assertGreaterEqual(len(registrations), 1)
            index = build_index(registrations, source=source, runtime=runtime)
            loader = ActivityIndexLoader.from_runtime(source, runtime)
            rebuilt = loader.loads(index.dump_bytes())
            self.assertEqual(len(rebuilt), len(registrations))
            expected = {item.manifest.activity_id: item for item in registrations}
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
                self.assertEqual(item.manifest.version, original.manifest.version)

    def test_deterministic_serialization_sorted_stable_newline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, source, runtime = _make_source_tree(temporary)
            registrations = _discover(source, runtime)
            forward = build_index(registrations, source=source, runtime=runtime)
            backward = build_index(
                tuple(reversed(registrations)), source=source, runtime=runtime
            )
            self.assertEqual(forward.dumps(), backward.dumps())
            text = forward.dumps()
            self.assertTrue(text.endswith("\n"))
            self.assertEqual(text.encode("utf-8").decode("utf-8"), text)
            payload = forward.dump_bytes()
            self.assertTrue(payload.endswith(b"\n"))
            # Stable key ordering: top-level keys appear sorted in the raw text.
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
                entry["activity_id"]
                for entry in json.loads(text)["registrations"]
            ]
            self.assertEqual(activity_ids, sorted(activity_ids))

    def test_forged_trust_via_json_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, source, runtime = _make_source_tree(temporary)
            registrations = _discover(source, runtime)
            index = build_index(registrations, source=source, runtime=runtime)
            raw = index.to_dict()
            forged = copy.deepcopy(raw)
            forged["package_trust"] = PackageTrust.DEVELOPER_UNSIGNED.value
            loader = ActivityIndexLoader.from_runtime(source, runtime)
            with self.assertRaises(ActivityIndexError):
                loader.load_dict(forged)
            # Unknown trust token is equally rejected.
            unknown = copy.deepcopy(raw)
            unknown["package_trust"] = "superuser"
            with self.assertRaises(ActivityIndexError):
                loader.load_dict(unknown)

    def test_forged_source_id_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, source, runtime = _make_source_tree(temporary)
            registrations = _discover(source, runtime)
            index = build_index(registrations, source=source, runtime=runtime)
            raw = index.to_dict()
            forged = copy.deepcopy(raw)
            forged["source_id"] = "attacker-source"
            loader = ActivityIndexLoader.from_runtime(source, runtime)
            with self.assertRaises(ActivityIndexError):
                loader.load_dict(forged)

    def test_path_escape_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, source, runtime = _make_source_tree(temporary)
            registrations = _discover(source, runtime)
            index = build_index(registrations, source=source, runtime=runtime)
            loader = ActivityIndexLoader.from_runtime(source, runtime)
            for escaped in (
                "../escape",
                "/absolute/path",
                "",
                ".",
                "a/../../b",
                "a/../b",
            ):
                with self.subTest(relpath=escaped):
                    raw = copy.deepcopy(index.to_dict())
                    raw["registrations"][0]["package_relpath"] = escaped
                    with self.assertRaises(ActivityIndexError):
                        loader.load_dict(raw)

    def test_entrypoint_escape_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, source, runtime = _make_source_tree(temporary)
            registrations = _discover(source, runtime)
            index = build_index(registrations, source=source, runtime=runtime)
            loader = ActivityIndexLoader.from_runtime(source, runtime)
            for escaped in ("../outside.py", "/absolute.py", ""):
                with self.subTest(entrypoint=escaped):
                    raw = copy.deepcopy(index.to_dict())
                    raw["registrations"][0]["entrypoint"] = escaped
                    with self.assertRaises(ActivityIndexError):
                        loader.load_dict(raw)

    def test_missing_index_file_controlled_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, source, runtime = _make_source_tree(temporary)
            loader = ActivityIndexLoader.from_runtime(source, runtime)
            with self.assertRaises(ActivityIndexError):
                loader.load_file(Path(temporary) / "no-such-index.json")

    def test_missing_source_root_controlled_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, source, runtime = _make_source_tree(temporary)
            registrations = _discover(source, runtime)
            index = build_index(registrations, source=source, runtime=runtime)
            payload = index.dump_bytes()
            missing_root = Path(temporary) / "gone"
            missing_source = ActivitySource(
                missing_root, PackageTrust.BUILT_IN, "greia-system"
            )
            loader = ActivityIndexLoader.from_runtime(missing_source, runtime)
            with self.assertRaisesRegex(ActivityIndexError, "source root is missing"):
                loader.loads(payload)
            self.assertFalse(missing_root.exists())
            _ = root  # keep root alive for the valid-source comparison below

    def test_schema_mismatch_controlled_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, source, runtime = _make_source_tree(temporary)
            registrations = _discover(source, runtime)
            index = build_index(registrations, source=source, runtime=runtime)
            raw = copy.deepcopy(index.to_dict())
            raw["schema_version"] = 999
            loader = ActivityIndexLoader.from_runtime(source, runtime)
            with self.assertRaises(ActivityIndexError):
                loader.load_dict(raw)

    def test_api_mismatch_controlled_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, source, runtime = _make_source_tree(temporary)
            registrations = _discover(source, runtime)
            index = build_index(registrations, source=source, runtime=runtime)
            loader = ActivityIndexLoader.from_runtime(source, runtime)
            raw = copy.deepcopy(index.to_dict())
            raw["platform_activity_api_version"] = "9.9"
            with self.assertRaises(ActivityIndexError):
                loader.load_dict(raw)
            entry_forged = copy.deepcopy(index.to_dict())
            entry_forged["registrations"][0]["api_version"] = "9.9"
            with self.assertRaises(ActivityIndexError):
                loader.load_dict(entry_forged)

    def test_policy_mismatch_controlled_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, source, runtime = _make_source_tree(temporary)
            registrations = _discover(source, runtime)
            index = build_index(registrations, source=source, runtime=runtime)
            loader = ActivityIndexLoader.from_runtime(source, runtime)
            version_forged = copy.deepcopy(index.to_dict())
            version_forged["generated_from_policy_version"] = "9.9"
            with self.assertRaises(ActivityIndexError):
                loader.load_dict(version_forged)
            hash_forged = copy.deepcopy(index.to_dict())
            hash_forged["generated_from_policy_hash"] = "0" * 64
            with self.assertRaises(ActivityIndexError):
                loader.load_dict(hash_forged)

    def test_corrupt_index_never_triggers_silent_rescan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, source, runtime = _make_source_tree(temporary)
            loader = ActivityIndexLoader.from_runtime(source, runtime)
            corrupt_payloads = (
                b"{not-json",
                b"",
                b"\xff\xfe{}",
                json.dumps({"schema_version": 1}).encode("utf-8"),
            )
            with mock.patch.object(
                ActivityRegistry,
                "discover_registrations",
                side_effect=AssertionError("loader must not rescan"),
            ) as discover_mock, mock.patch.object(
                ActivityRegistry,
                "discover",
                side_effect=AssertionError("loader must not rescan"),
            ) as discover_simple_mock:
                for payload in corrupt_payloads:
                    with self.subTest(payload=payload[:12]):
                        with self.assertRaises(ActivityIndexError):
                            loader.loads(payload)
                with self.assertRaises(ActivityIndexError):
                    loader.load_file(Path(temporary) / "missing.json")
                discover_mock.assert_not_called()
                discover_simple_mock.assert_not_called()

    def test_loader_does_not_recompute_package_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, source, runtime = _make_source_tree(temporary)
            registrations = _discover(source, runtime)
            index = build_index(registrations, source=source, runtime=runtime)
            payload = index.dump_bytes()
            loader = ActivityIndexLoader.from_runtime(source, runtime)
            with mock.patch(
                "greia_platform.activities.package_digest",
                side_effect=AssertionError("loader must not recompute digests"),
            ):
                rebuilt = loader.loads(payload)
            self.assertEqual(len(rebuilt), len(registrations))

    def test_launch_path_and_permission_semantics_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, source, runtime = _make_source_tree(temporary)
            registrations = _discover(source, runtime)
            index = build_index(registrations, source=source, runtime=runtime)
            loader = ActivityIndexLoader.from_runtime(source, runtime)
            rebuilt = loader.loads(index.dump_bytes())
            broker = PermissionBroker(
                PermissionPolicy.phase0(runtime),
                DeviceCapabilityService.static(
                    set(runtime.allowed_capabilities),
                    source_id="activity-index-test",
                ),
            )
            manager = RuntimeManager(
                [PythonRuntimeAdapter(policy=PythonRuntimePolicy.load(RUNTIME_PATH))],
                DeviceCapabilityService.static(
                    set(runtime.allowed_capabilities),
                    source_id="activity-index-test",
                ),
            )
            expected = {item.manifest.activity_id: item for item in registrations}
            for item in rebuilt:
                original = expected[item.manifest.activity_id]
                original_authority = broker.issue(original)
                rebuilt_authority = broker.issue(item)
                self.assertEqual(rebuilt_authority, original_authority)
                self.assertEqual(
                    rebuilt_authority.package_digest, original.package_digest
                )
                manager.validate_package(item.manifest)

    def test_positive_control_break_restore_cycle(self) -> None:
        """Known-bad fixture proves the loader check is sensitive (not vacuously green)."""
        with tempfile.TemporaryDirectory() as temporary:
            _, source, runtime = _make_source_tree(temporary)
            registrations = _discover(source, runtime)
            index = build_index(registrations, source=source, runtime=runtime)
            path = Path(temporary) / "activity-index.json"
            path.write_bytes(index.dump_bytes())
            loader = ActivityIndexLoader.from_runtime(source, runtime)
            # GREEN: valid snapshot reconstructs without tree re-reads.
            self.assertEqual(len(loader.load_file(path)), len(registrations))
            # BREAK: forge one trusted field in the stored JSON.
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw["package_trust"] = PackageTrust.DEVELOPER_UNSIGNED.value
            path.write_text(
                json.dumps(raw, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            # RED: the same loader now fails closed on the forged trust.
            with self.assertRaises(ActivityIndexError):
                loader.load_file(path)
            # RESTORE: exact intended bytes load again.
            path.write_bytes(index.dump_bytes())
            self.assertEqual(len(loader.load_file(path)), len(registrations))

    def test_policy_fingerprint_tracks_runtime_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, _, runtime = _make_source_tree(temporary)
            first = runtime_policy_fingerprint(runtime)
            self.assertEqual(len(first), 64)
            self.assertEqual(first, runtime_policy_fingerprint(runtime))

    def test_build_rejects_foreign_source_registration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, source, runtime = _make_source_tree(temporary)
            registrations = _discover(source, runtime)
            other = ActivitySource(
                Path(temporary) / "other", PackageTrust.DEVELOPER_UNSIGNED, "other"
            )
            with self.assertRaises(ActivityIndexError):
                build_index(registrations, source=other, runtime=runtime)

    def test_index_entry_dataclass_is_frozen(self) -> None:
        entry = ActivityIndexEntry(
            activity_id="org.greia.example",
            package_relpath="example",
            package_digest="0" * 64,
            title_key="activity.example.title",
            version="0.1.0",
            runtime_type="python",
            api_version="0.1",
            entrypoint="main.py",
            icon_id="robot",
        )
        with self.assertRaises(Exception):
            entry.activity_id = "mutated"  # type: ignore[misc]

    def test_duplicate_activity_id_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, source, runtime = _make_source_tree(temporary)
            registrations = _discover(source, runtime)
            self.assertGreaterEqual(len(registrations), 1)
            index = build_index(registrations, source=source, runtime=runtime)
            raw = copy.deepcopy(index.to_dict())
            raw["registrations"].append(copy.deepcopy(raw["registrations"][0]))
            loader = ActivityIndexLoader.from_runtime(source, runtime)
            with self.assertRaisesRegex(ActivityIndexError, "duplicate"):
                loader.load_dict(raw)


if __name__ == "__main__":
    unittest.main()
