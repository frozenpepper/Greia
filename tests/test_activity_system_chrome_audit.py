from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "audit_activity_system_chrome_ownership.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("activity_system_chrome_audit", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ActivitySystemChromeAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = _load_tool()

    def _scan(self, source: str):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "activity.py"
            path.write_text(source, encoding="utf-8")
            return self.audit.scan_python_source(path, root=root)

    def test_reports_legacy_helper_import_and_call(self) -> None:
        findings = self._scan(
            "from greia_platform.activity_ui import is_home_clicked\n"
            "def click(surface, pos):\n"
            "    return is_home_clicked(surface, pos)\n"
        )
        self.assertEqual(
            [(item.kind, item.symbol) for item in findings],
            [
                ("legacy_helper_import", "is_home_clicked"),
                ("legacy_helper_call", "is_home_clicked"),
            ],
        )

    def test_reports_reference_canvas_system_chrome_keyword(self) -> None:
        findings = self._scan(
            "def present(canvas):\n"
            "    canvas.present(clear=(0, 0, 0), system_chrome=True)\n"
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "legacy_canvas_chrome_request")
        self.assertEqual(findings[0].symbol, "system_chrome")

    def test_backend_neutral_activity_code_is_clean(self) -> None:
        findings = self._scan(
            "from greia_platform.activity_api import activity_stop_requested\n"
            "from greia_platform.pygame_canvas import PygameReferenceCanvas\n"
            "def loop(canvas):\n"
            "    if activity_stop_requested():\n"
            "        return\n"
            "    canvas.present()\n"
        )
        self.assertEqual(findings, ())


if __name__ == "__main__":
    unittest.main()
