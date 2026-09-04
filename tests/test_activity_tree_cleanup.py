from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from greia_platform.activity_tree_cleanup import scrub_activity_tree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVICE_FILE = PROJECT_ROOT / "build/overlay/etc/systemd/system/greia-launcher.service"
SCRUB_HELPER = PROJECT_ROOT / "build/overlay/usr/local/lib/greia-os/scrub-activity-trees"
LAUNCHER_MAIN = PROJECT_ROOT / "src/greia_launcher/main.py"
BUILD_IMAGE = PROJECT_ROOT / "build/build-image.sh"


def _exec_start_pre_directives(unit_text: str) -> list[str]:
    """Return non-comment ExecStartPre directives from a systemd unit file."""
    directives = []
    for line in unit_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("ExecStartPre="):
            directives.append(stripped)
    return directives


class ActivityTreeCleanupTests(unittest.TestCase):
    def _tree(self, root: Path) -> None:
        (root / "activities").mkdir(parents=True)
        act = root / "activities" / "demo"
        (act / "assets").mkdir(parents=True)
        (act / "locales").mkdir(parents=True)
        (act / "assets" / "sub").mkdir(parents=True)
        (act / "main.py").write_text("print('x')\n", encoding="utf-8")
        (act / "activity.toml").write_text("x=1\n", encoding="utf-8")
        (act / "locales" / "it.json").write_text("{}", encoding="utf-8")
        # Development noise that must be removed.
        (act / "._assets").write_bytes(b"ab")
        (act / "assets" / ".DS_Store").write_bytes(b"")
        (act / "assets" / "sub" / "._sub").write_bytes(b"ab")
        (act / "Thumbs.db").write_bytes(b"")
        (act / "locales" / "it.json~").write_bytes(b"")
        (act / "main.pyc").write_bytes(b"")
        (act / "assets" / "__pycache__").mkdir()
        (act / "assets" / "__pycache__" / "main.cpython-311.pyc").write_bytes(b"")
        (act / "_junk.py").write_text("x\n", encoding="utf-8")  # not noise, keep

    def test_scrub_removes_dev_noise_and_keeps_real_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._tree(root)
            result = scrub_activity_tree(root / "activities")
            act = root / "activities" / "demo"
            self.assertFalse((act / "._assets").exists())
            self.assertFalse((act / "assets" / ".DS_Store").exists())
            self.assertFalse((act / "assets" / "sub" / "._sub").exists())
            self.assertFalse((act / "Thumbs.db").exists())
            self.assertFalse((act / "locales" / "it.json~").exists())
            self.assertFalse((act / "main.pyc").exists())
            self.assertFalse((act / "assets" / "__pycache__").exists())
            self.assertTrue((act / "main.py").exists())
            self.assertTrue((act / "activity.toml").exists())
            self.assertTrue((act / "locales" / "it.json").exists())
            self.assertTrue((act / "_junk.py").exists())
            self.assertGreater(result.removed_files, 0)
            self.assertGreater(result.removed_dirs, 0)

    def test_scrub_does_not_follow_symlink_out_of_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "activities").mkdir()
            outside = root / "outside"
            outside.mkdir()
            (outside / "keep.txt").write_text("x", encoding="utf-8")
            # A symlinked dir outside the tree must not be descended into.
            link = root / "activities" / "linked"
            link.symlink_to(outside)
            leak = outside / "._junk"
            leak.write_bytes(b"ab")
            scrub_activity_tree(root / "activities")
            self.assertTrue((outside / "keep.txt").exists())
            # The scrub does not descend into the symlink, so a junk file inside
            # the target is untouched.
            self.assertTrue(leak.exists())

    def test_scrub_missing_root_is_benign(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = scrub_activity_tree(root / "nope")
            self.assertEqual(result.removed_files, 0)
            self.assertEqual(result.removed_dirs, 0)

    def test_scrub_matches_case_insensitive_exact_names(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "activities"
            root.mkdir(parents=True)
            (root / ".Ds_StOrE").write_bytes(b"")
            (root / "ThUmBs.DB").write_bytes(b"")
            (root / "MAIN.PYC").write_bytes(b"")
            scrub_activity_tree(root)
            self.assertEqual(list(root.iterdir()), [])


class BootScrubRelocationTests(unittest.TestCase):
    """2A: no recurring Activity-tree scrub remains on the production boot path."""

    def test_production_boot_has_no_scrub_pre_hook(self) -> None:
        directives = _exec_start_pre_directives(
            SERVICE_FILE.read_text(encoding="utf-8")
        )
        self.assertNotEqual(directives, [])
        for directive in directives:
            self.assertNotIn("scrub-activity-trees", directive)
        # B2's lines are preserved byte-for-byte: the VT pre-hook stays.
        self.assertIn(
            "ExecStartPre=+/usr/local/lib/greia-os/prepare-launcher-vt", directives
        )

    def test_pre_hook_predicate_is_sensitive_positive_control(self) -> None:
        """The assertion above must detect a scrub line, not pass vacuously."""
        fixture = (
            "ExecStartPre=+/usr/local/lib/greia-os/scrub-activity-trees\n"
            "ExecStartPre=+/usr/local/lib/greia-os/prepare-launcher-vt\n"
        )
        hits = [
            directive
            for directive in _exec_start_pre_directives(fixture)
            if "scrub-activity-trees" in directive
        ]
        self.assertEqual(len(hits), 1)

    def test_launcher_constructs_without_in_process_scrub(self) -> None:
        main_text = LAUNCHER_MAIN.read_text(encoding="utf-8")
        self.assertNotIn("scrub_activity_tree", main_text)
        # The scrub module itself survives only as the repurposed
        # maintenance/recovery command, documented where it lives.
        helper = SCRUB_HELPER.read_text(encoding="utf-8")
        self.assertIn("greia_platform.activity_tree_cleanup", helper)
        self.assertIn("NOT part of normal boot", helper)
        self.assertIn("/usr/local/lib/greia-os/scrub-activity-trees", helper)

    def test_build_gate_owns_builtin_hygiene_before_composition(self) -> None:
        builder = BUILD_IMAGE.read_text(encoding="utf-8")
        self.assertIn("GREIA_BUILTIN_GATE", builder)
        rsync_anchor = "rsync -a --delete --exclude '__pycache__'"
        self.assertIn(rsync_anchor, builder)
        self.assertLess(
            builder.index("GREIA_BUILTIN_GATE"), builder.index(rsync_anchor)
        )

    def test_build_junk_scan_catches_what_validation_allows(self) -> None:
        """The gate's junk scan is load-bearing: `notes.txt~` passes the
        registry but must fail the build, while a clean tree passes both."""
        import shutil

        from greia_platform.activities import (
            ActivityRegistry,
            RuntimeCatalogue,
        )
        from greia_platform.activity_tree_cleanup import _is_junk_name
        from greia_platform.trust import ActivitySource, PackageTrust

        painting = PROJECT_ROOT / "activities" / "painting"
        runtime = RuntimeCatalogue.load(
            PROJECT_ROOT / "runtime" / "child-runtime.toml"
        )
        with tempfile.TemporaryDirectory() as td:
            noisy = Path(td) / "painting"
            shutil.copytree(painting, noisy, symlinks=True)
            (noisy / "notes.txt~").write_bytes(b"draft")
            junk_hits = [
                path
                for path in sorted(noisy.rglob("*"))
                if not (path.name == "__pycache__" or "__pycache__" in path.parts)
                and _is_junk_name(path.name)
            ]
            self.assertEqual([hit.name for hit in junk_hits], ["notes.txt~"])
            # The registry alone would accept this noise, so without the
            # build-time scan it would ship into the image.
            source = ActivitySource(
                noisy.parent, PackageTrust.BUILT_IN, "build-gate-probe"
            )
            ActivityRegistry((source,), runtime).validate_package(noisy)

            clean = Path(td) / "clean"
            shutil.copytree(painting, clean, symlinks=True)
            clean_hits = [
                path
                for path in sorted(clean.rglob("*"))
                if not (path.name == "__pycache__" or "__pycache__" in path.parts)
                and _is_junk_name(path.name)
            ]
            self.assertEqual(clean_hits, [])
            clean_source = ActivitySource(
                clean.parent, PackageTrust.BUILT_IN, "build-gate-probe"
            )
            ActivityRegistry((clean_source,), runtime).validate_package(clean)

    def test_bad_builtin_fails_registry_validation(self) -> None:
        """A built-in carrying a symlink or an executable file fails the same
        registry validation the image build runs before composition."""
        import shutil

        from greia_platform.activities import (
            ActivityRegistry,
            ActivityValidationError,
            RuntimeCatalogue,
        )
        from greia_platform.trust import ActivitySource, PackageTrust

        painting = PROJECT_ROOT / "activities" / "painting"
        runtime = RuntimeCatalogue.load(
            PROJECT_ROOT / "runtime" / "child-runtime.toml"
        )
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "painting"
            shutil.copytree(painting, bad, symlinks=True)
            (bad / "sneaky").symlink_to("/etc/passwd")
            source = ActivitySource(
                bad.parent, PackageTrust.BUILT_IN, "build-gate-probe"
            )
            registry = ActivityRegistry((source,), runtime)
            with self.assertRaisesRegex(
                ActivityValidationError, "symlinks are forbidden"
            ):
                registry.validate_package(bad)

            (bad / "sneaky").unlink()
            (bad / "main.py").chmod(0o755)
            with self.assertRaisesRegex(
                ActivityValidationError, "executable activity files are forbidden"
            ):
                registry.validate_package(bad)

    def test_developer_mode_keeps_intended_validation(self) -> None:
        """Mode signal pinned: `GREIA_DEVELOPER_ACTIVITY_ROOT` presence gates
        the developer source in the launcher; privileged operations stay
        behind the `/etc/greia-os/developer-remote` image marker. Mode off
        adds no source and no scan; mode on validates through the registry."""
        import shutil

        from greia_launcher.main import LauncherPaths, _activity_sources
        from greia_platform import developer_control as devctl
        from greia_platform.activities import (
            ActivityRegistry,
            ActivityValidationError,
            RuntimeCatalogue,
        )
        from greia_platform.trust import ActivitySource, PackageTrust

        self.assertEqual(
            devctl.DEVELOPER_MARKER, Path("/etc/greia-os/developer-remote")
        )
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            builtin = base / "os" / "activities"
            builtin.mkdir(parents=True)
            dev_root = base / "dev"
            dev_root.mkdir()

            def paths_for(developer: Path | None) -> LauncherPaths:
                return LauncherPaths(
                    root=base / "os",
                    activities=builtin,
                    developer_activities=developer,
                    runtime_catalogue=base / "runtime.toml",
                    asset_catalogue=base / "a.toml",
                    shared_visual_catalogue=base / "s.toml",
                    theme_defaults=base / "t.toml",
                    profile_defaults=base / "p.toml",
                    permission_policy=base / "perm.toml",
                    storage_policy=base / "st.toml",
                    history_policy=base / "h.toml",
                    progression_policy=base / "pr.toml",
                    profiles_dir=base / "profiles",
                    active_profile_status=base / "status.json",
                )

            off_sources = _activity_sources(paths_for(None))
            self.assertEqual(len(off_sources), 1)
            on_sources = _activity_sources(paths_for(dev_root))
            self.assertEqual(len(on_sources), 2)
            self.assertEqual(on_sources[1].trust, PackageTrust.DEVELOPER_UNSIGNED)

            painting = PROJECT_ROOT / "activities" / "painting"
            shutil.copytree(painting, dev_root / "painting", symlinks=True)
            runtime = RuntimeCatalogue.load(
                PROJECT_ROOT / "runtime" / "child-runtime.toml"
            )
            registry = ActivityRegistry(
                (
                    ActivitySource(
                        dev_root, PackageTrust.DEVELOPER_UNSIGNED, "probe"
                    ),
                ),
                runtime,
            )
            registry.validate_package(dev_root / "painting")
            (dev_root / "painting" / "sneaky").symlink_to("/etc/passwd")
            with self.assertRaisesRegex(
                ActivityValidationError, "symlinks are forbidden"
            ):
                registry.validate_package(dev_root / "painting")


if __name__ == "__main__":
    unittest.main()