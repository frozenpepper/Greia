from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

from greia_platform.customization import WallpaperCandidate
from greia_platform.system_chrome import ActivitySystemChromeLayout


ROOT = Path(__file__).resolve().parents[1]


def _load_activity():
    name = "greia_test_my_greia_activity"
    spec = importlib.util.spec_from_file_location(
        name,
        ROOT / "activities" / "workshop_settings" / "main.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load My Greia Activity")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MY_GREIA = _load_activity()


def _overlaps(left, right) -> bool:
    return not (
        left.right <= right.x
        or right.right <= left.x
        or left.bottom <= right.y
        or right.bottom <= left.y
    )


class MyGreiaRuntimeTests(unittest.TestCase):
    def test_thumbnail_fails_soft_when_removable_media_disappears_after_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "gone.png"
            candidate = WallpaperCandidate(
                path=path,
                media_id="test-media",
                display_name="gone",
                size_bytes=128,
            )
            activity = object.__new__(MY_GREIA.MyGreiaSettings)
            activity.thumbnail_cache = {}

            self.assertFalse(path.exists())
            self.assertIsNone(activity._thumbnail(candidate, (120, 90)))
            self.assertEqual(activity.thumbnail_cache, {})

    def test_safe_settings_region_avoids_platform_home_back_chrome(self) -> None:
        for width, height in (
            (640, 480),
            (800, 600),
            (1024, 600),
            (1366, 768),
            (1920, 1080),
            (720, 1280),
            (3840, 2160),
        ):
            with self.subTest(size=(width, height)):
                safe = MY_GREIA.settings_safe_ui_rect(width, height)
                protected = ActivitySystemChromeLayout.for_surface(
                    width, height
                ).protected_region
                self.assertGreater(safe.width, 0)
                self.assertGreater(safe.height, 0)
                self.assertGreaterEqual(safe.x, 0)
                self.assertGreaterEqual(safe.y, 0)
                self.assertLessEqual(safe.right, width)
                self.assertLessEqual(safe.bottom, height)
                self.assertFalse(_overlaps(safe, protected))


if __name__ == "__main__":
    unittest.main()
