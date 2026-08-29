from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRITING = ROOT / "activities" / "writing" / "main.py"
PAINTING = ROOT / "activities" / "painting" / "main.py"
PYGAME_CANVAS = ROOT / "src" / "greia_platform" / "pygame_canvas.py"
SIMULATOR_BOOTSTRAP = ROOT / "src" / "greia_simulator" / "python_activity.py"


class FirstWaveActivityTrustedChromeMigrationTests(unittest.TestCase):
    def test_writing_and_painting_do_not_implement_platform_home(self) -> None:
        for path in (WRITING, PAINTING):
            with self.subTest(path=path):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("draw_system_chrome_overlay", source)
                self.assertNotIn("is_home_clicked", source)
                self.assertIn("activity_stop_requested", source)
                self.assertIn("activity_toolbar_button", source)

    def test_reference_canvas_reserves_geometry_but_does_not_render_home(self) -> None:
        source = PYGAME_CANVAS.read_text(encoding="utf-8")
        self.assertIn("ActivitySystemChromeLayout", source)
        self.assertIn("protected_regions=", source)
        self.assertNotIn(
            "from .activity_ui import draw_system_chrome_overlay",
            source,
        )
        self.assertNotIn("draw_system_chrome_overlay(self.target)", source)
        self.assertIn("system_chrome: bool = False", source)
        self.assertIn("del system_chrome", source)

    def test_simulator_bootstrap_still_owns_compatibility_home(self) -> None:
        source = SIMULATOR_BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("ActivitySystemChromeLayout", source)
        self.assertIn("draw_system_chrome_overlay", source)
        self.assertIn("chrome.home_hitbox.contains", source)
        self.assertIn("pygame.event.get = simulator_get_events", source)
        self.assertIn("pygame.display.flip = simulator_flip", source)


if __name__ == "__main__":
    unittest.main()
