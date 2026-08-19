from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = PROJECT_ROOT / "tools" / "greia_update.py"

spec = importlib.util.spec_from_file_location("greia_update_tool", TOOL_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class GreiaUpdateToolTests(unittest.TestCase):
    def test_profile_file_derives_exact_release_identity(self) -> None:
        target = module._target_from_profile_file(
            PROJECT_ROOT / "build" / "profiles" / "legacy-x86-i686.toml"
        )
        self.assertEqual(target.platform_family, "legacy-x86")
        self.assertEqual(target.architecture, "i386")
        self.assertEqual(target.profile, "legacy-x86-i686")

    def test_build_target_rejects_mixing_profile_file_and_explicit_identity(self) -> None:
        args = argparse.Namespace(
            profile_file=PROJECT_ROOT / "build" / "profiles" / "legacy-x86-i686.toml",
            platform_family="legacy-x86",
            architecture=None,
            profile=None,
        )
        with self.assertRaisesRegex(Exception, "profile-file.*not both"):
            module._resolve_target(args)

    def test_default_output_is_deterministic_and_project_local(self) -> None:
        args = argparse.Namespace(output=None, version="0.14.0")
        target = module.UpdateTarget("legacy-x86", "i386", "legacy-x86-i686")
        output = module._build_output(args, target)
        self.assertEqual(
            output,
            PROJECT_ROOT / "out" / "greia-0.14.0-legacy-x86-i686.greiaupdate",
        )

    def test_profile_parser_rejects_incomplete_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.toml"
            path.write_text('[profile]\nid = "x"\n', encoding="utf-8")
            with self.assertRaisesRegex(Exception, "profile.id, platform.family"):
                module._target_from_profile_file(path)


if __name__ == "__main__":
    unittest.main()
