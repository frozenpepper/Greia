from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from greia_platform import developer_control as devctl  # noqa: E402
from greia_platform.developer_session import DeveloperDisplayEndpoint  # noqa: E402


ACTIVITY_SOURCE = PROJECT_ROOT / "activities" / "labirinto_magico"
RUNTIME_CATALOGUE = PROJECT_ROOT / "runtime" / "child-runtime.toml"
ACTIVITY_ID = "org.greia.opaque-example"


def _copy_activity(destination: Path, *, activity_id: str = ACTIVITY_ID) -> Path:
    shutil.copytree(ACTIVITY_SOURCE, destination)
    manifest = destination / "activity.toml"
    text = manifest.read_text(encoding="utf-8")
    text = text.replace(
        'id = "org.greia.labirinto-magico"',
        f'id = "{activity_id}"',
        1,
    )
    manifest.write_text(text, encoding="utf-8")
    return destination


def _add_legacy_id(activity_root: Path, legacy_id: str) -> None:
    manifest = activity_root / "activity.toml"
    text = manifest.read_text(encoding="utf-8")
    text = text.replace(
        "legacy_ids = []",
        f'legacy_ids = ["{legacy_id}"]',
        1,
    )
    manifest.write_text(text, encoding="utf-8")


@contextmanager
def _control_fixture(root: Path):
    marker = root / "etc/greia-os/developer-remote"
    marker.parent.mkdir(parents=True)
    marker.write_text("enabled\n", encoding="utf-8")
    state_root = root / "developer-state"
    system_root = root / "system-activities"
    upload_root = root / "upload"
    system_root.mkdir()
    upload_root.mkdir()
    endpoint = DeveloperDisplayEndpoint(user="greiakid", display=":0")
    with (
        mock.patch.object(devctl, "DEVELOPER_MARKER", marker),
        mock.patch.object(devctl, "SYSTEM_ACTIVITY_ROOT", system_root),
        mock.patch.object(devctl, "RUNTIME_CATALOGUE", RUNTIME_CATALOGUE),
        mock.patch.object(devctl, "STATE_ROOT", state_root),
        mock.patch.object(devctl, "DEVELOPER_ACTIVITY_ROOT", state_root / "activities"),
        mock.patch.object(devctl, "UPLOAD_ROOT", upload_root),
        mock.patch.object(devctl, "STAGING_ROOT", state_root / "staging"),
        mock.patch.object(devctl, "BACKUP_ROOT", state_root / "backups"),
        mock.patch.object(devctl, "STATE_FILE", state_root / "deployments.json"),
        mock.patch("greia_platform.developer_control.os.geteuid", return_value=0),
        mock.patch.object(
            devctl.DeveloperDisplayEndpoint,
            "load",
            return_value=endpoint,
        ),
        mock.patch.object(devctl, "_make_tree_read_only"),
    ):
        control = devctl.DeveloperControl()
        control.restart_launcher = mock.Mock()
        yield control, system_root, upload_root, state_root


class DeveloperControlMappingTests(unittest.TestCase):
    def test_manifest_identity_resolves_snake_case_path_and_restores_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with _control_fixture(root) as (control, system_root, upload_root, state_root):
                _copy_activity(system_root / "opaque_example")
                staged = _copy_activity(upload_root / "payload")

                record = control.deploy_activity(staged, replace_system=True)

                self.assertEqual(record.activity_id, ACTIVITY_ID)
                self.assertEqual(record.kind, "system-replacement")
                self.assertTrue((system_root / "opaque_example" / "activity.toml").is_file())
                backup = Path(record.original_backup or "")
                self.assertEqual(backup.parent, state_root / "backups")
                self.assertTrue(backup.is_dir())
                self.assertEqual(
                    json.loads((state_root / "deployments.json").read_text()),
                    {ACTIVITY_ID: record.as_dict()},
                )

                control.restore_activity(ACTIVITY_ID)

                self.assertTrue((system_root / "opaque_example" / "activity.toml").is_file())
                self.assertFalse(backup.exists())
                self.assertEqual(control._load_state(), {})
                self.assertEqual(control.restart_launcher.call_count, 2)

    def test_missing_manifest_identity_refuses_system_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with _control_fixture(root) as (control, system_root, upload_root, _):
                _copy_activity(system_root / "other_activity", activity_id="org.greia.other")
                staged = _copy_activity(upload_root / "payload")

                with self.assertRaisesRegex(
                    devctl.DeveloperControlError,
                    "not an installed system Activity",
                ):
                    control.deploy_activity(staged, replace_system=True)

                self.assertFalse((system_root / ACTIVITY_ID).exists())
                self.assertTrue((system_root / "other_activity").is_dir())

    def test_legacy_identity_is_not_used_to_infer_system_path(self):
        legacy_id = "org.greia.legacy-example"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with _control_fixture(root) as (control, system_root, upload_root, _):
                installed = _copy_activity(system_root / "opaque_example")
                _add_legacy_id(installed, legacy_id)
                staged = _copy_activity(upload_root / "payload", activity_id=legacy_id)

                with self.assertRaisesRegex(
                    devctl.DeveloperControlError,
                    "not an installed system Activity",
                ):
                    control.deploy_activity(staged, replace_system=True)

                self.assertTrue((system_root / "opaque_example").is_dir())
                self.assertFalse((system_root / legacy_id).exists())

    def test_duplicate_manifest_identity_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with _control_fixture(root) as (control, system_root, upload_root, _):
                _copy_activity(system_root / "first_activity")
                _copy_activity(system_root / "second_activity")
                staged = _copy_activity(upload_root / "payload")

                with self.assertRaisesRegex(
                    devctl.DeveloperControlError,
                    "cannot resolve built-in Activity identity.*collision",
                ):
                    control.deploy_activity(staged, replace_system=True)

    def test_ordinary_developer_deployment_refuses_built_in_collision(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with _control_fixture(root) as (control, system_root, upload_root, state_root):
                _copy_activity(system_root / "opaque_example")
                staged = _copy_activity(upload_root / "payload")

                with self.assertRaisesRegex(
                    devctl.DeveloperControlError,
                    "installed system Activity; use --replace-system",
                ):
                    control.deploy_activity(staged, replace_system=False)

                self.assertFalse((state_root / "activities" / ACTIVITY_ID).exists())

    def test_unsafe_system_package_path_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with _control_fixture(root) as (control, system_root, upload_root, _):
                outside = root / "outside_activity"
                _copy_activity(outside)
                (system_root / "opaque_example").symlink_to(
                    outside,
                    target_is_directory=True,
                )
                staged = _copy_activity(upload_root / "payload")

                with self.assertRaisesRegex(
                    devctl.DeveloperControlError,
                    "cannot resolve built-in Activity identity.*outside configured roots",
                ):
                    control.deploy_activity(staged, replace_system=True)

    def test_restore_rejects_backup_path_outside_configured_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with _control_fixture(root) as (control, system_root, upload_root, state_root):
                _copy_activity(system_root / "opaque_example")
                staged = _copy_activity(upload_root / "payload")
                record = control.deploy_activity(staged, replace_system=True)
                state_path = state_root / "deployments.json"
                state = json.loads(state_path.read_text(encoding="utf-8"))
                state[ACTIVITY_ID]["original_backup"] = str(root / "outside-backup")
                state_path.write_text(json.dumps(state), encoding="utf-8")

                with self.assertRaisesRegex(
                    devctl.DeveloperControlError,
                    "missing or outside backup root",
                ):
                    control.restore_activity(ACTIVITY_ID)

                self.assertTrue((system_root / "opaque_example").is_dir())
                self.assertEqual(control._load_state()[ACTIVITY_ID]["kind"], record.kind)


if __name__ == "__main__":
    unittest.main()
