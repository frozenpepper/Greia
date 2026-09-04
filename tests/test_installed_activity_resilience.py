from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_launcher.composition import load_runtime_progression_policy
from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.activity_tree_cleanup import (
    _is_unprivileged_installed_built_in,
    installed_activity_roots,
    scrub_activity_tree,
)
from greia_platform.history import HistoryPolicyError, ProgressionPolicy
from greia_platform.trust import ActivitySource, PackageTrust


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class InstalledActivityResilienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        runtime = RuntimeCatalogue.load(PROJECT_ROOT / "runtime" / "child-runtime.toml")
        source = ActivitySource(
            PROJECT_ROOT / "activities",
            PackageTrust.BUILT_IN,
            "greia-system",
        )
        cls.activities = ActivityRegistry([source], runtime).discover()

    def test_installed_root_set_covers_all_launcher_activity_sources(self) -> None:
        env = {
            "GREIA_OS_ROOT": "/test/os",
            "GREIA_DEVELOPER_ACTIVITY_ROOT": "/test/dev",
            "GREIA_PARENT_ACTIVITY_PACKAGE_ROOT": "/test/parent-state",
        }
        self.assertEqual(
            installed_activity_roots(env),
            (
                Path("/test/os/activities"),
                Path("/test/dev"),
                Path("/test/parent-state/active"),
            ),
        )

        env["GREIA_PARENT_ACTIVITY_ROOT"] = "/test/parent-active-override"
        self.assertEqual(
            installed_activity_roots(env)[2],
            Path("/test/parent-active-override"),
        )

    def test_only_canonical_unprivileged_installed_root_delegates_to_prestart(self) -> None:
        with mock.patch(
            "greia_platform.activity_tree_cleanup.os.geteuid",
            return_value=1000,
        ):
            with mock.patch.dict(
                "os.environ",
                {"GREIA_OS_ROOT": "/opt/greia-os"},
                clear=False,
            ):
                self.assertTrue(
                    _is_unprivileged_installed_built_in(
                        Path("/opt/greia-os/activities")
                    )
                )
            with tempfile.TemporaryDirectory() as temporary:
                source_root = Path(temporary)
                with mock.patch.dict(
                    "os.environ",
                    {"GREIA_OS_ROOT": str(source_root)},
                    clear=False,
                ):
                    self.assertFalse(
                        _is_unprivileged_installed_built_in(
                            source_root / "activities"
                        )
                    )

    def test_source_checkout_root_keeps_in_process_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            os_root = Path(temporary) / "checkout"
            activities = os_root / "activities"
            activities.mkdir(parents=True)
            junk = activities / ".DS_Store"
            junk.write_bytes(b"x")
            with (
                mock.patch.dict(
                    "os.environ",
                    {"GREIA_OS_ROOT": str(os_root)},
                    clear=False,
                ),
                mock.patch(
                    "greia_platform.activity_tree_cleanup.os.geteuid",
                    return_value=1000,
                ),
            ):
                result = scrub_activity_tree(activities)
            self.assertFalse(junk.exists())
            self.assertGreaterEqual(result.roots_scrubbed, 1)
            self.assertEqual(result.removed_files, 1)

    def test_cleanup_failure_is_counted_not_reported_as_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            junk = root / ".DS_Store"
            junk.write_bytes(b"x")
            with mock.patch(
                "greia_platform.activity_tree_cleanup._remove_path",
                return_value=False,
            ):
                result = scrub_activity_tree(root)
        self.assertEqual(result.removed_files, 0)
        self.assertEqual(result.removed_dirs, 0)
        self.assertEqual(result.failed_removals, 1)

    def test_symlink_root_is_never_followed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            outside = base / "outside"
            outside.mkdir()
            junk = outside / ".DS_Store"
            junk.write_bytes(b"x")
            root_link = base / "activities"
            root_link.symlink_to(outside, target_is_directory=True)
            result = scrub_activity_tree(root_link)
            self.assertTrue(junk.exists())
            self.assertEqual(result.removed_files, 0)
            self.assertGreaterEqual(result.failed_removals, 1)

    def test_runtime_progression_corruption_disables_enrichment_not_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            policy = Path(temporary) / "progression-policy.toml"
            policy.write_text("this is not toml = [", encoding="utf-8")
            runtime_policy = load_runtime_progression_policy(policy, self.activities)
        self.assertEqual(runtime_policy.rules, ())

    def test_runtime_stale_event_binding_disables_progression(self) -> None:
        manifest = self.activities[0]
        with tempfile.TemporaryDirectory() as temporary:
            policy = Path(temporary) / "progression-policy.toml"
            policy.write_text(
                "schema_version = 1\n"
                "[[rules]]\n"
                'id = "stale-binding"\n'
                f'activity_id = "{manifest.activity_id}"\n'
                'event_id = "event.that.is.not.declared"\n'
                "once_per_session = true\n"
                'reward_id = "star"\n'
                "reward_delta = 1\n",
                encoding="utf-8",
            )
            # Strict source/build validation still rejects the same policy.
            with self.assertRaises(HistoryPolicyError):
                ProgressionPolicy.load(policy, self.activities)
            runtime_policy = load_runtime_progression_policy(policy, self.activities)
        self.assertEqual(runtime_policy.rules, ())

    def test_launcher_service_runs_privileged_scrub_before_unprivileged_shell(self) -> None:
        service = (
            PROJECT_ROOT
            / "build/overlay/etc/systemd/system/greia-launcher.service"
        ).read_text(encoding="utf-8")
        scrub = "ExecStartPre=+/usr/local/lib/greia-os/scrub-activity-trees"
        prepare = "ExecStartPre=+/usr/local/lib/greia-os/prepare-launcher-vt"
        self.assertIn("User=greiakid", service)
        # 2A relocation authority: recurring launcher-start scrub relocated to
        # owning boundaries (build-time R1 proof, in-transaction R3 staged
        # scrub, mode-gated R2); normal launcher path must not scrub.
        self.assertNotIn(scrub, service)
        self.assertIn(prepare, service)

    def test_installed_scrub_wrapper_is_explicitly_fail_open(self) -> None:
        wrapper = (
            PROJECT_ROOT
            / "build/overlay/usr/local/lib/greia-os/scrub-activity-trees"
        ).read_text(encoding="utf-8")
        self.assertIn("greia_platform.activity_tree_cleanup", wrapper)
        self.assertIn("PYTHONDONTWRITEBYTECODE=1", wrapper)
        self.assertIn("exit 0", wrapper)


if __name__ == "__main__":
    unittest.main()
