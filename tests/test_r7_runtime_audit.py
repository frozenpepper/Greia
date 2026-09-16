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

    def test_runtime_audit_only_copies_prior_active_acceptance_result(self) -> None:
        collector = COLLECTOR.read_text(encoding="utf-8")
        self.assertIn(
            "copy_if_readable /var/lib/greia-kmsdrm-acceptance/result.json kmsdrm-acceptance.json",
            collector,
        )
        self.assertNotIn("systemctl start greia-kmsdrm-acceptance.service", collector)
        self.assertNotIn("greia_platform.kmsdrm_acceptance", collector)
        self.assertNotIn("--acknowledge-display-takeover", collector)

    def test_probe_module_is_in_the_existing_installed_source_tree(self) -> None:
        # T01: Greia content installation lives in the shared engine.
        builder = (PROJECT_ROOT / "build" / "lib" / "compose.sh").read_text(encoding="utf-8")
        module = PROJECT_ROOT / "src" / "greia_platform" / "direct_graphics_probe.py"
        self.assertTrue(module.is_file())
        self.assertIn('"$project_root/src"', builder)
        self.assertIn('"$rootfs/opt/greia-os/"', builder)
        consumer = (PROJECT_ROOT / "build" / "build-image.sh").read_text(encoding="utf-8")
        self.assertIn('compose_root --profile "$PROFILE_PATH" --role target', consumer)

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
