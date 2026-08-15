from __future__ import annotations

import unittest
from pathlib import Path

from greia_installer.main import InstallerApplication
from greia_platform.hardware import DisplayMode
from greia_platform.hardware_session import DisplayProbe


class _Controller:
    backend_id = "fake-direct"

    def __init__(self):
        self.probes = 0

    def topology_token(self):
        return ("fake",)

    def probe_display(self):
        self.probes += 1
        return DisplayProbe(
            "panel-0",
            (
                DisplayMode(1024, 600, 60.0, preferred=True, current=True),
                DisplayMode(800, 600, 60.0),
            ),
        )

    def apply(self, settings):  # pragma: no cover - installer only probes here
        raise AssertionError("installer resolution discovery must not apply settings")


class InstallerHardwareAdapterTests(unittest.TestCase):
    def test_resolution_discovery_uses_injected_semantic_controller(self) -> None:
        controller = _Controller()
        application = InstallerApplication.__new__(InstallerApplication)
        application.demo = False
        application.hardware_controller = controller

        self.assertEqual(
            application._available_resolutions(),
            ("auto", "1024x600", "800x600"),
        )
        self.assertEqual(controller.probes, 1)

    def test_demo_resolution_discovery_needs_no_controller(self) -> None:
        application = InstallerApplication.__new__(InstallerApplication)
        application.demo = True
        application.hardware_controller = None
        self.assertEqual(
            application._available_resolutions(),
            ("auto", "800x600", "1024x600", "1024x768"),
        )

    def test_installer_ui_source_contains_no_x_settings_implementation(self) -> None:
        import greia_installer.main as installer_main
        import greia_platform.hardware_session as hardware_session

        installer_source = Path(installer_main.__file__).read_text(encoding="utf-8")
        generic_source = Path(hardware_session.__file__).read_text(encoding="utf-8")
        for source in (installer_source, generic_source):
            self.assertNotIn("XSessionHardwareController", source)
            self.assertNotIn('"xrandr"', source)
            self.assertNotIn('"xinput"', source)

    def test_installer_composition_is_the_explicit_legacy_compatibility_boundary(self) -> None:
        import greia_installer.composition as composition

        source = Path(composition.__file__).read_text(encoding="utf-8")
        self.assertIn("LegacyXHardwareSessionController", source)
        self.assertIn("provisional_installer_hardware_controller", source)


if __name__ == "__main__":
    unittest.main()
