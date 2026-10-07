from __future__ import annotations

import unittest
from types import SimpleNamespace

from greia_launcher.system_chrome import SystemChromeCoordinator
from greia_platform.system_chrome import (
    ActivitySystemChromeLayout,
    SystemNavigationAction,
)
from greia_simulator.child_shell import GreiaSimulatorChildShell
from greia_simulator.device import DEFAULT_CAPABILITIES, SimulatedDeviceProfile
from greia_simulator.shell_window import SimulatorShellWindowController
from greia_simulator.system_chrome import (
    SimulatorSystemChromeBackend,
    SimulatorSystemChromeRemoteBridge,
)


class _EventFactory:
    @staticmethod
    def Event(event_type, **kwargs):
        return SimpleNamespace(type=event_type, **kwargs)


class _FakePygame:
    KEYDOWN = 1
    KEYUP = 2
    TEXTINPUT = 3
    MOUSEMOTION = 4
    MOUSEBUTTONDOWN = 5
    MOUSEBUTTONUP = 6
    K_LEFT = 10
    K_RIGHT = 11
    K_UP = 12
    K_DOWN = 13
    K_RETURN = 14
    K_ESCAPE = 15
    K_TAB = 16
    K_SPACE = 17
    K_BACKSPACE = 18
    event = _EventFactory()


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

    def test_shell_modal_diverts_ordinary_remote_input_but_preserves_home(self) -> None:
        bridge = SimulatorSystemChromeRemoteBridge(port=0)
        layout = ActivitySystemChromeLayout.for_surface(1024, 600)
        bridge.activate_system_chrome("session-1", layout)
        controller = SimulatorShellWindowController(bridge)
        lease = controller.prepare_activity_modal(
            object(), session_id="session-1", activity_pid=4321
        )
        self.assertIsNotNone(lease)
        self.assertTrue(controller.show_activity_modal(lease))

        # The Activity HTTP transport is withheld while the trusted Shell owns
        # the synthetic display, but the Shell can drain the same queued input.
        bridge.queue_key("LEFT")
        bridge.queue_mouse(400, 300, action="click", button=1)
        self.assertEqual(bridge.drain_events(), [])
        shell_events = bridge.poll_events(_FakePygame())
        self.assertEqual(
            [event.type for event in shell_events],
            [
                _FakePygame.KEYDOWN,
                _FakePygame.KEYUP,
                _FakePygame.MOUSEMOTION,
                _FakePygame.MOUSEBUTTONDOWN,
                _FakePygame.MOUSEBUTTONUP,
            ],
        )

        home_x = layout.home_hitbox.x + layout.home_hitbox.width // 2
        home_y = layout.home_hitbox.y + layout.home_hitbox.height // 2
        bridge.queue_mouse(home_x, home_y, action="click", button=1)
        self.assertIs(
            bridge.poll_system_navigation("session-1"),
            SystemNavigationAction.HOME,
        )
        self.assertTrue(controller.dismiss_activity_modal(lease))
        controller.abandon_activity_modal(lease)

    def test_activity_frames_cannot_overwrite_active_shell_modal(self) -> None:
        bridge = SimulatorSystemChromeRemoteBridge(port=0)
        layout = ActivitySystemChromeLayout.for_surface(1024, 600)
        bridge.activate_system_chrome("session-1", layout)
        controller = SimulatorShellWindowController(bridge)
        bridge.set_external_frame_png(b"before", mode="activity")
        lease = controller.prepare_activity_modal(
            object(), session_id="session-1", activity_pid=4321
        )
        self.assertIsNotNone(lease)
        self.assertTrue(controller.show_activity_modal(lease))
        bridge.set_external_frame_png(b"during", mode="activity")
        self.assertEqual(bridge.get_latest_frame_png(), b"before")
        self.assertTrue(controller.dismiss_activity_modal(lease))
        bridge.set_external_frame_png(b"after", mode="activity")
        self.assertEqual(bridge.get_latest_frame_png(), b"after")

    def test_simulator_modal_requires_matching_active_system_chrome_session(self) -> None:
        bridge = SimulatorSystemChromeRemoteBridge(port=0)
        controller = SimulatorShellWindowController(bridge)
        self.assertIsNone(
            controller.prepare_activity_modal(
                object(), session_id="session-1", activity_pid=4321
            )
        )
        layout = ActivitySystemChromeLayout.for_surface(1024, 600)
        bridge.activate_system_chrome("session-other", layout)
        self.assertIsNone(
            controller.prepare_activity_modal(
                object(), session_id="session-1", activity_pid=4321
            )
        )

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
