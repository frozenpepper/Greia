from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_launcher.runtime_adapter import RuntimeCommand
from greia_launcher.supervisor import ActivitySupervisor
from greia_platform.activities import ActivityManifest, SkillContribution
from greia_platform.trust import PackageTrust


class _Profile:
    profile_id = "0123456789abcdef0123456789abcdef"
    display_name = "Mia"
    avatar_id = "unicorn"


class _ProfileContext:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.profile = _Profile()
        self.customization_dir = root / "customization"
        self.customization_dir.mkdir(parents=True, exist_ok=True)

    def activity_data_dir(self, activity_id: str) -> Path:
        path = self.root / "activities" / activity_id
        path.mkdir(parents=True, exist_ok=True)
        return path


class _Authority:
    effective_capabilities = frozenset({"display", "pointer"})

    def has_capability(self, capability: str) -> bool:
        return capability in self.effective_capabilities

    def has_permission(self, permission: str) -> bool:
        del permission
        return False


class ActivitySandboxDeviceAuthorityTests(unittest.TestCase):
    def test_ordinary_activity_receives_no_drm_or_raw_input_device_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            activity_root = root / "activity"
            activity_root.mkdir()
            entrypoint = activity_root / "main.py"
            entrypoint.write_text("print('ok')\n", encoding="utf-8")
            manifest = ActivityManifest(
                activity_id="org.greia.r7-device-authority-test",
                legacy_ids=(),
                title_key="activity.test.title",
                version="0.1.0",
                runtime_type="python",
                api_version="0.1",
                entrypoint=Path("main.py"),
                icon_id="test",
                categories=("test",),
                skills=(SkillContribution("test", 1),),
                events=(),
                difficulty=1,
                languages=("en",),
                required_capabilities=("display", "pointer"),
                optional_capabilities=(),
                requested_permissions=(),
                storage_schema_version=1,
                root=activity_root,
            )
            command = ActivitySupervisor._sandbox_command(
                root / "bwrap",
                RuntimeCommand(command=("python3", "main.py"), cwd=activity_root),
                manifest,
                _ProfileContext(root / "profile"),
                _Authority(),
            )

        self.assertNotIn("/dev/dri", command)
        self.assertNotIn("/dev/input", command)
        self.assertNotIn("/sys/class/drm", command)
        self.assertNotIn("/sys/class/input", command)


if __name__ == "__main__":
    unittest.main()
