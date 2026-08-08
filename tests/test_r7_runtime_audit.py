from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = (
    PROJECT_ROOT
    / "build"
    / "overlay"
    / "usr"
    / "local"
    / "sbin"
    / "greia-collect-runtime-audit"
)
BUILD_IMAGE = PROJECT_ROOT / "build" / "build-image.sh"


class R7RuntimeAuditTests(unittest.TestCase):
    def test_runtime_audit_collects_passive_direct_graphics_snapshot(self) -> None:
        collector = COLLECTOR.read_text(encoding="utf-8")
        self.assertIn("collector_version=3", collector)
        self.assertIn("direct-graphics-probe.json", collector)
        self.assertIn("python3 -m greia_platform.direct_graphics_probe", collector)
        self.assertIn("PYTHONPATH=/opt/greia-os/src", collector)
        self.assertNotIn("SDL_VIDEODRIVER=kmsdrm", collector)
        self.assertNotIn("pygame.display", collector)
        self.assertNotIn("/dev/input/event", collector)

    def test_probe_module_is_in_the_existing_installed_source_tree(self) -> None:
        builder = BUILD_IMAGE.read_text(encoding="utf-8")
        module = PROJECT_ROOT / "src" / "greia_platform" / "direct_graphics_probe.py"
        self.assertTrue(module.is_file())
        self.assertIn('"$PROJECT_ROOT/src"', builder)
        self.assertIn('"$ROOTFS/opt/greia-os/"', builder)

    def test_probe_contract_never_equates_prerequisites_with_active_success(self) -> None:
        source = (
            PROJECT_ROOT / "src" / "greia_platform" / "direct_graphics_probe.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"active_kmsdrm_test_required": True', source)
        self.assertIn('"kmsdrm_prerequisites_visible"', source)
        self.assertNotIn("pygame.display.set_mode", source)
        self.assertNotIn("SDL_Init", source)


if __name__ == "__main__":
    unittest.main()
