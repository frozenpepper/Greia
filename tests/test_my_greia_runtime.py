from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

from greia_platform.customization import WallpaperCandidate


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


if __name__ == "__main__":
    unittest.main()
