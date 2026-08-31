from __future__ import annotations

import unittest

from greia_launcher.system_chrome import SystemChromeCoordinator
from greia_platform.system_chrome import (
    ActivitySystemChromeLayout,
    SystemNavigationAction,
)
from greia_simulator.child_shell import GreiaSimulatorChildShell
from greia_simulator.device import DEFAULT_CAPABILITIES, SimulatedDeviceProfile
from greia_simulator.system_chrome import (
    SimulatorSystemChromeBackend,
    SimulatorSystemChromeRemoteBridge,
)


class SimulatorSystemChromeTests(unittest.TestCase):
    def test_protected_home_is_diverted_before_activity_delivery(self) -> None:
        bridge = SimulatorSystemChromeRemoteBridge(port=0)
        coordinator = SystemChromeCoordinator(
            SimulatorSystemChromeBackend(bridge, width=1024, height=600)
        )
        lease = coordinator.prepare("session-1", back_available=False)
        coordinator.activity_ready(lease)

        layout = ActivitySystemChromeLayout.for_surface(1024, 600)
        home_x = layout.home_hitbox.x + layout.home_hitbox.width // 2
        home_y = layout.home_hitbox.y + layout.home_hitbox.height // 2

        bridge.queue_mouse(home_x, home_y, action="click", button=1)
        bridge.queue_mouse(400, 300, action="click", button=1)

        self.assertIs(coordinator.poll_action(lease), SystemNavigationAction.HOME)
        self.assertEqual(
            bridge.drain_events(),
            [
                {
                    "type": "mouse",
                    "x": 400,
                    "y": 300,
                    "action": "click",
                    "button": 1,
                }
            ],
        )
        coordinator.activity_ended(lease)

    def test_simulator_shell_composes_system_chrome_coordinator(self) -> None:
        bridge = SimulatorSystemChromeRemoteBridge(port=0)
        shell = object.__new__(GreiaSimulatorChildShell)
        shell.simulated_device = SimulatedDeviceProfile(
            1024,
            600,
            DEFAULT_CAPABILITIES,
        )
        shell._remote_bridge = bridge

        coordinator = shell._system_chrome_coordinator()
        self.assertIsNotNone(coordinator)
        assert coordinator is not None
        self.assertEqual(coordinator.backend_id, "simulator-system-chrome")


if __name__ == "__main__":
    unittest.main()
