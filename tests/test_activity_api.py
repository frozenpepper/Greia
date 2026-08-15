from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from greia_platform import activity_api


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ActivityApiCapabilityTests(unittest.TestCase):
    def tearDown(self) -> None:
        activity_api._root.cache_clear()
        activity_api._catalogue.cache_clear()
        activity_api._theme_store.cache_clear()
        activity_api._media_scanner.cache_clear()
        activity_api._profile_policy.cache_clear()

    def test_theme_palette_requires_declared_capability(self) -> None:
        with patch.dict(os.environ, {"GREIA_ACTIVITY_CAPABILITIES": ""}, clear=False):
            with self.assertRaisesRegex(PermissionError, "customization.manage"):
                activity_api.get_theme_palette()

    def test_declared_capability_allows_palette_access(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            os.environ,
            {
                "GREIA_ACTIVITY_CAPABILITIES": "display,customization.manage",
                "GREIA_OS_ROOT": str(PROJECT_ROOT),
                "GREIA_CUSTOMIZATION_DIR": temporary,
            },
            clear=False,
        ):
            palette = activity_api.get_theme_palette()
        self.assertEqual(palette.default_background, "cream")

    def test_theme_access_without_profile_scope_uses_canonical_default(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GREIA_ACTIVITY_CAPABILITIES": "display,customization.manage",
                "GREIA_OS_ROOT": str(PROJECT_ROOT),
            },
            clear=True,
        ):
            theme = activity_api.get_theme()
            expected = activity_api._default_theme_store().resolve()
        self.assertEqual(theme, expected)

    def test_avatar_change_uses_scoped_request_file_not_profile_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            os.environ,
            {
                "GREIA_ACTIVITY_CAPABILITIES": "profile.manage_own",
                "GREIA_OS_ROOT": str(PROJECT_ROOT),
                "GREIA_PROFILE_ID": "0123456789abcdef0123456789abcdef",
                "GREIA_PROFILE_NAME": "Mia",
                "GREIA_PROFILE_AVATAR": "unicorn",
                "GREIA_AVATAR_REQUEST_PATH": str(Path(temporary) / "avatar-request.json"),
            },
            clear=True,
        ):
            updated = activity_api.set_active_profile_avatar("owl")
            request = (Path(temporary) / "avatar-request.json").read_text()
        self.assertEqual(updated["avatar_id"], "owl")
        self.assertIn('"avatar_id":"owl"', request)
        self.assertNotIn("secret", request)


class ActivityApiLifecycleTests(unittest.TestCase):
    def test_mark_ready_writes_current_session_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary) / "activity-data"
            ready = data / ".greia" / "runtime" / "abc" / "ready"
            with patch.dict(
                os.environ,
                {
                    "GREIA_ACTIVITY_SESSION_ID": "abc",
                    "GREIA_ACTIVITY_DATA_DIR": str(data),
                    "GREIA_ACTIVITY_READY_PATH": str(ready),
                },
                clear=True,
            ):
                activity_api.mark_activity_ready()
            self.assertEqual(ready.read_text(encoding="ascii"), "abc\n")

    def test_stop_request_accepts_only_matching_session_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary) / "activity-data"
            stop = data / ".greia" / "runtime" / "abc" / "stop-requested"
            stop.parent.mkdir(parents=True)
            environment = {
                "GREIA_ACTIVITY_SESSION_ID": "abc",
                "GREIA_ACTIVITY_DATA_DIR": str(data),
                "GREIA_ACTIVITY_STOP_PATH": str(stop),
            }
            stop.write_text("wrong\n", encoding="ascii")
            with patch.dict(os.environ, environment, clear=True):
                self.assertFalse(activity_api.activity_stop_requested())
            stop.write_text("abc\n", encoding="ascii")
            with patch.dict(os.environ, environment, clear=True):
                self.assertTrue(activity_api.activity_stop_requested())

    def test_lifecycle_path_cannot_escape_activity_private_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary) / "activity-data"
            escaped = Path(temporary) / "outside" / "ready"
            with patch.dict(
                os.environ,
                {
                    "GREIA_ACTIVITY_SESSION_ID": "abc",
                    "GREIA_ACTIVITY_DATA_DIR": str(data),
                    "GREIA_ACTIVITY_READY_PATH": str(escaped),
                },
                clear=True,
            ):
                with self.assertRaisesRegex(RuntimeError, "escapes"):
                    activity_api.mark_activity_ready()


if __name__ == "__main__":
    unittest.main()
