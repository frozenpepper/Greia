"""Smoke test for tools/installer_screenshots.py on a reduced state matrix."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "installer_screenshots", PROJECT_ROOT / "tools" / "installer_screenshots.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # dataclasses resolve their module through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class InstallerScreenshotToolTests(unittest.TestCase):
    def test_reduced_matrix_renders_without_hit_target_faults(self) -> None:
        tool = _load_tool()
        states = (
            "01-language",
            "02-welcome",
            "05-keyboard-list",
            "12-wifi-password",
            "23-confirm-wifi-holding",
            "25-installing",
            "27-error",
        )
        with tempfile.TemporaryDirectory() as tmp:
            reports = tool.render_matrix(
                Path(tmp), locales=("it", "fr"), sizes=((800, 480),), only=states
            )
            self.assertEqual(len(reports), 2 * len(states))
            for report in reports:
                self.assertTrue(report.path.is_file(), report.path)
                self.assertEqual(report.overlaps, (), report.path.name)
                self.assertEqual(report.offscreen, (), report.path.name)
            sheet = tool.write_contact_sheet(reports, Path(tmp) / "sheet.png", columns=3, thumb_width=160)
            self.assertTrue(sheet.is_file())

    def test_every_scenario_id_is_unique_and_covers_every_page(self) -> None:
        tool = _load_tool()
        ids = [state_id for state_id, _ in tool.SCENARIOS]
        self.assertEqual(len(ids), len(set(ids)))
        from greia_installer.main import InstallerPage

        app = tool._make_app("en")
        seen = set()
        for _state_id, setup in tool.SCENARIOS:
            setup(app)
            seen.add(app.state.page)
        missing = set(InstallerPage) - seen - {InstallerPage.SETTINGS}
        self.assertEqual(missing, set())


if __name__ == "__main__":
    unittest.main()
