from __future__ import annotations

from greia_platform.hal_legacy_x import LegacyXHardwareSessionController
from greia_platform.hardware_session import HardwareSessionController


def provisional_installer_hardware_controller() -> HardwareSessionController:
    """Return today's explicit compatibility backend for the live installer.

    R7 may replace this composition with a direct/Wayland settings controller
    after the corresponding display-session architecture is selected. Installer
    UI/state code depends only on HardwareSessionController.
    """

    return LegacyXHardwareSessionController()
