"""Creation capabilities are validated manifest metadata, not file access rights."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_platform.activities import ActivityRegistry, ActivityValidationError, RuntimeCatalogue
from greia_platform.activity_index import ActivityIndexLoader, build_index
from greia_platform.trust import ActivitySource, PackageTrust


ROOT = Path(__file__).resolve().parents[1]


def _write_package(root: Path, declarations: str) -> Path:
    package = root / "creative_fixture"
    package.mkdir()
    (package / "main.py").write_text("def main(): return 0\n", encoding="utf-8")
    (package / "activity.toml").write_text(
        '''[activity]
id = "org.greia.creative-fixture"
legacy_ids = []
title_key = "activity.creative_fixture.title"
version = "0.1.0"
icon = "robot"
languages = ["en"]

[education]
categories = ["creativity"]
difficulty = 1
skills = [{ id = "creation.art", weight = 1 }]
events = []

[runtime]
type = "python"
api_version = "0.1"
entrypoint = "main.py"

[requirements]
required_capabilities = ["display"]
optional_capabilities = []

[permissions]
requested = []

[storage]
schema_version = 1
''' + declarations,
        encoding="utf-8",
    )
    return package


class CreationManifestTests(unittest.TestCase):
    def _discover(self, declarations: str):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        _write_package(root, declarations)
        runtime = RuntimeCatalogue.load(ROOT / "runtime" / "child-runtime.toml")
        source = ActivitySource(root, PackageTrust.BUILT_IN, "fixture")
        registration, = ActivityRegistry([source], runtime).discover_registrations()
        return registration, source, runtime

    def test_old_activity_declares_no_media_and_remains_valid(self):
        registration, _, _ = self._discover("")
        self.assertEqual(registration.manifest.creations_produces, ())
        self.assertEqual(registration.manifest.creations_consumes, ())

    def test_media_declarations_survive_exact_built_in_index_roundtrip(self):
        registration, source, runtime = self._discover(
            '\n[creations]\nproduces = ["image/png", "text/plain"]\nconsumes = ["audio/wav"]\n'
        )
        index = build_index((registration,), source=source, runtime=runtime)
        rebuilt, = ActivityIndexLoader.from_runtime(source, runtime).loads(index.dump_bytes())
        self.assertEqual(rebuilt.manifest.creations_produces, ("image/png", "text/plain"))
        self.assertEqual(rebuilt.manifest.creations_consumes, ("audio/wav",))
        self.assertEqual(rebuilt.package_digest, registration.package_digest)

    def test_declared_unsupported_format_is_rejected(self):
        with self.assertRaisesRegex(ActivityValidationError, "unsupported media"):
            self._discover('\n[creations]\nproduces = ["application/x-shellscript"]\n')

    def test_duplicate_claims_and_malformed_table_fail_closed(self):
        with self.assertRaisesRegex(ActivityValidationError, "duplicates"):
            self._discover('\n[creations]\nproduces = ["image/png", "image/png"]\n')
        with self.assertRaisesRegex(ActivityValidationError, "creations must be a table"):
            self._discover('\ncreations = "all-files"\n')


if __name__ == "__main__":
    unittest.main()
