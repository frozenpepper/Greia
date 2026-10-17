from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_launcher import launch_validation_cache as cache_module
from greia_launcher.launch_validation_cache import (
    LaunchValidationCache,
    read_only_built_in_package,
)
from greia_launcher.runtime_adapter import (
    PythonRuntimeAdapter,
    PythonRuntimePolicy,
    RuntimeManager,
    RuntimeValidationError,
)
from greia_platform.activities import ActivityManifest
from greia_platform.input_core import InteractionProfile
from greia_platform.trust import PackageTrust


RUNTIME_POLICY = Path(__file__).resolve().parents[1] / "runtime" / "child-runtime.toml"


def _always_eligible(_manifest: ActivityManifest, _trust: PackageTrust | None) -> bool:
    # Stands in for "read-only root-owned built-in tree", which a test
    # process cannot create.
    return True


class _CountingAdapter:
    runtime_type = "python"

    def __init__(self, inner: PythonRuntimeAdapter | None = None) -> None:
        self.calls = 0
        self._inner = inner

    def validate_package(self, manifest: ActivityManifest) -> None:
        self.calls += 1
        if self._inner is not None:
            self._inner.validate_package(manifest)


class LaunchValidationCacheTests(unittest.TestCase):
    def _package(self, source: str = "import math\nprint(math.pi)\n") -> ActivityManifest:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "main.py").write_text(source, encoding="utf-8")
        (root / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")
        return ActivityManifest(
            activity_id="org.greia.test.launch-cache",
            legacy_ids=(),
            title_key="activity.test.title",
            version="0.1.0",
            runtime_type="python",
            api_version="0.1",
            entrypoint=Path("main.py"),
            icon_id="test",
            categories=("test",),
            skills=(),
            events=(),
            difficulty=1,
            languages=("en",),
            required_capabilities=(),
            optional_capabilities=(),
            requested_permissions=(),
            storage_schema_version=1,
            root=root,
            input_profile=InteractionProfile.HYBRID.value,
        )

    def _policy_adapter(self) -> PythonRuntimeAdapter:
        return PythonRuntimeAdapter(policy=PythonRuntimePolicy.load(RUNTIME_POLICY))

    def test_unchanged_eligible_tree_reuses_validation(self) -> None:
        manifest = self._package()
        adapter = _CountingAdapter()
        cache = LaunchValidationCache(eligible=_always_eligible)

        self.assertFalse(cache.validate(adapter, manifest, PackageTrust.BUILT_IN))
        self.assertTrue(cache.validate(adapter, manifest, PackageTrust.BUILT_IN))
        self.assertEqual(adapter.calls, 1)

    def test_fingerprint_mismatch_forces_full_validation(self) -> None:
        manifest = self._package()
        adapter = _CountingAdapter()
        cache = LaunchValidationCache(eligible=_always_eligible)
        cache.validate(adapter, manifest, PackageTrust.BUILT_IN)

        # Same size, different content: mtime/ctime still move.
        (manifest.root / "helper.py").write_text("VALUE = 2\n", encoding="utf-8")
        self.assertFalse(cache.validate(adapter, manifest, PackageTrust.BUILT_IN))
        self.assertEqual(adapter.calls, 2)

        # A new file is a mismatch as well.
        (manifest.root / "extra.py").write_text("X = 1\n", encoding="utf-8")
        self.assertFalse(cache.validate(adapter, manifest, PackageTrust.BUILT_IN))
        self.assertEqual(adapter.calls, 3)
        self.assertTrue(cache.validate(adapter, manifest, PackageTrust.BUILT_IN))
        self.assertEqual(adapter.calls, 3)

    def test_changed_file_that_violates_policy_is_rejected_and_not_cached(self) -> None:
        manifest = self._package()
        adapter = _CountingAdapter(self._policy_adapter())
        cache = LaunchValidationCache(eligible=_always_eligible)
        cache.validate(adapter, manifest, PackageTrust.BUILT_IN)

        (manifest.root / "helper.py").write_text(
            "import importlib\nimportlib.import_module('socket')\n", encoding="utf-8"
        )
        with self.assertRaises(RuntimeValidationError):
            cache.validate(adapter, manifest, PackageTrust.BUILT_IN)
        # The failure is never cached: the next launch validates (and fails) again.
        with self.assertRaises(RuntimeValidationError):
            cache.validate(adapter, manifest, PackageTrust.BUILT_IN)
        self.assertEqual(adapter.calls, 3)

    def test_changed_file_that_violates_path_policy_is_rejected(self) -> None:
        manifest = self._package()
        adapter = self._policy_adapter()
        cache = LaunchValidationCache(eligible=_always_eligible)
        cache.validate(adapter, manifest, PackageTrust.BUILT_IN)

        (manifest.root / "bundled.whl").write_bytes(b"PK")
        with self.assertRaisesRegex(RuntimeValidationError, "suffix"):
            cache.validate(adapter, manifest, PackageTrust.BUILT_IN)

    def test_edited_but_valid_file_still_launches(self) -> None:
        manifest = self._package()
        adapter = _CountingAdapter(self._policy_adapter())
        cache = LaunchValidationCache(eligible=_always_eligible)
        cache.validate(adapter, manifest, PackageTrust.BUILT_IN)

        (manifest.root / "main.py").write_text(
            "import math\nimport helper\nprint(math.tau, helper.VALUE)\n", encoding="utf-8"
        )
        self.assertFalse(cache.validate(adapter, manifest, PackageTrust.BUILT_IN))
        self.assertEqual(adapter.calls, 2)

    def test_writable_location_packages_are_always_validated(self) -> None:
        manifest = self._package()
        adapter = _CountingAdapter()
        cache = LaunchValidationCache()  # default eligibility

        for trust in (
            PackageTrust.BUILT_IN,  # a writable checkout/tmp tree, even if built-in
            PackageTrust.PARENT_TRUSTED_UNSIGNED,
            PackageTrust.DEVELOPER_UNSIGNED,
            None,
        ):
            cache.validate(adapter, manifest, trust)
            cache.validate(adapter, manifest, trust)
        self.assertEqual(adapter.calls, 8)
        self.assertEqual(len(cache), 0)

    def test_default_eligibility_requires_built_in_trust_and_read_only_root_tree(self) -> None:
        manifest = self._package()
        self.assertFalse(read_only_built_in_package(manifest, PackageTrust.BUILT_IN))
        with mock.patch.object(cache_module, "_read_only_root_owned", return_value=True):
            self.assertTrue(read_only_built_in_package(manifest, PackageTrust.BUILT_IN))
            for trust in (
                PackageTrust.PARENT_TRUSTED_UNSIGNED,
                PackageTrust.DEVELOPER_UNSIGNED,
                None,
            ):
                self.assertFalse(read_only_built_in_package(manifest, trust))

    @unittest.skipIf(os.geteuid() == 0, "root can write anywhere")
    def test_owned_writable_directory_is_not_read_only_root_owned(self) -> None:
        manifest = self._package()
        self.assertFalse(cache_module._read_only_root_owned(manifest.root))

    def test_fingerprint_error_falls_back_to_full_validation(self) -> None:
        manifest = self._package()
        adapter = _CountingAdapter()

        def broken(_root: Path) -> bytes:
            raise OSError("unreadable")

        cache = LaunchValidationCache(eligible=_always_eligible, fingerprint=broken)
        cache.validate(adapter, manifest, PackageTrust.BUILT_IN)
        cache.validate(adapter, manifest, PackageTrust.BUILT_IN)
        self.assertEqual(adapter.calls, 2)
        self.assertEqual(len(cache), 0)

    def test_cache_is_bounded_least_recently_used(self) -> None:
        manifests = [self._package() for _ in range(3)]
        adapter = _CountingAdapter()
        cache = LaunchValidationCache(capacity=2, eligible=_always_eligible)
        for manifest in manifests:
            cache.validate(adapter, manifest, PackageTrust.BUILT_IN)
        self.assertEqual(len(cache), 2)
        self.assertEqual(adapter.calls, 3)
        # The oldest entry was evicted and validates again.
        cache.validate(adapter, manifests[0], PackageTrust.BUILT_IN)
        self.assertEqual(adapter.calls, 4)
        cache.validate(adapter, manifests[2], PackageTrust.BUILT_IN)
        self.assertEqual(adapter.calls, 4)

    def test_runtime_manager_threads_package_trust_into_the_cache(self) -> None:
        manifest = self._package()
        adapter = _CountingAdapter()
        seen: list[PackageTrust | None] = []

        def eligible(_manifest: ActivityManifest, trust: PackageTrust | None) -> bool:
            seen.append(trust)
            return trust is PackageTrust.BUILT_IN

        cache = LaunchValidationCache(eligible=eligible)
        manager = RuntimeManager(
            {"python": adapter}, mock.Mock(), validation_cache=cache
        )
        with mock.patch.object(manager, "compatibility_for", side_effect=RuntimeError("stop")):
            for trust in (None, PackageTrust.PARENT_TRUSTED_UNSIGNED, PackageTrust.BUILT_IN, PackageTrust.BUILT_IN):
                with self.assertRaisesRegex(RuntimeError, "stop"):
                    manager.prepare_launch(manifest, package_trust=trust)
        self.assertEqual(
            seen,
            [None, PackageTrust.PARENT_TRUSTED_UNSIGNED, PackageTrust.BUILT_IN, PackageTrust.BUILT_IN],
        )
        self.assertEqual(adapter.calls, 3)


class PythonPackageSourceWalkTests(unittest.TestCase):
    """The single scandir walk keeps the previous rglob path-policy semantics."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "main.py").write_text("import math\n", encoding="utf-8")
        self.policy = PythonRuntimePolicy.load(RUNTIME_POLICY)

    def _sources(self) -> list[Path]:
        from greia_launcher.runtime_adapter import _python_package_sources

        return _python_package_sources(self.root, self.policy)

    def test_nested_sources_are_listed_sorted(self) -> None:
        (self.root / "pkg").mkdir()
        (self.root / "pkg" / "b.py").write_text("", encoding="utf-8")
        (self.root / "pkg" / "a.py").write_text("", encoding="utf-8")
        self.assertEqual(
            self._sources(),
            sorted([self.root / "main.py", self.root / "pkg" / "a.py", self.root / "pkg" / "b.py"]),
        )

    def test_forbidden_suffix_deep_in_tree_is_rejected(self) -> None:
        suffix = sorted(self.policy.forbidden_suffixes)[0]
        (self.root / "a" / "b").mkdir(parents=True)
        (self.root / "a" / "b" / f"blob{suffix}").write_bytes(b"x")
        with self.assertRaisesRegex(RuntimeValidationError, "suffix"):
            self._sources()

    def test_pycache_subtree_skips_name_policy(self) -> None:
        suffix = sorted(self.policy.forbidden_suffixes)[0]
        (self.root / "__pycache__").mkdir()
        (self.root / "__pycache__" / f"main{suffix}").write_bytes(b"x")
        self.assertEqual(self._sources(), [self.root / "main.py"])

    def test_symlinked_directory_is_not_descended(self) -> None:
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        (Path(outside.name) / "elsewhere.py").write_text("", encoding="utf-8")
        (self.root / "linked").symlink_to(outside.name, target_is_directory=True)
        self.assertEqual(self._sources(), [self.root / "main.py"])


if __name__ == "__main__":
    unittest.main()
