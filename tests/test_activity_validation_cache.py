"""Discovery memoises tree validation but never returns stale results."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_platform import activities
from greia_platform.activities import ActivityRegistry, ActivityValidationError, RuntimeCatalogue
from greia_platform.trust import ActivitySource, PackageTrust

REPO = Path(__file__).resolve().parents[1]


class ActivityValidationCacheTests(unittest.TestCase):
    def setUp(self):
        activities._validated_tree_cache.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.source_root = Path(self.tmp.name) / "activities"
        shutil.copytree(REPO / "activities" / "painting", self.source_root / "painting")
        runtime = RuntimeCatalogue.load(REPO / "runtime" / "child-runtime.toml")
        self.registry = ActivityRegistry(
            (ActivitySource(self.source_root, PackageTrust.BUILT_IN, "greia-system"),), runtime
        )

    def tearDown(self):
        self.tmp.cleanup()

    def discover_digest(self):
        (registration,) = self.registry.discover_registrations()
        return registration.package_digest

    def test_unchanged_tree_is_validated_once(self):
        with mock.patch.object(ActivityRegistry, "_validate_tree", autospec=True, side_effect=ActivityRegistry._validate_tree) as validate:
            first = self.discover_digest()
            second = self.discover_digest()
        self.assertEqual(first, second)
        self.assertEqual(validate.call_count, 1)

    def test_same_size_rewrite_preserving_mtime_revalidates(self):
        first = self.discover_digest()
        target = next((self.source_root / "painting").glob("*.py"))
        stat = target.stat()
        data = bytearray(target.read_bytes())
        data[-1:] = b" " if data[-1:] != b" " else b"\n"
        target.write_bytes(bytes(data))
        os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertNotEqual(self.discover_digest(), first)

    def test_new_forbidden_file_is_still_rejected(self):
        self.discover_digest()
        (self.source_root / "painting" / "install.sh").write_text("echo hi\n")
        with self.assertRaises(ActivityValidationError):
            self.registry.validate_registration(self.source_root / "painting")

    def test_cache_is_bounded(self):
        activities._validated_tree_cache.update(
            {(f"/x/{i}", ()): ((), "d") for i in range(activities._VALIDATED_TREE_CACHE_LIMIT)}
        )
        self.discover_digest()
        self.assertLessEqual(len(activities._validated_tree_cache), activities._VALIDATED_TREE_CACHE_LIMIT)


if __name__ == "__main__":
    unittest.main()
