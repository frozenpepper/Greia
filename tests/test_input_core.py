from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_platform.device_capabilities import HALDeviceCapabilityProbe
from greia_platform.hal import (
    AudioState,
    DisplayState,
    GreiaHAL,
    InputState,
    LinuxControllerPresenceProbe,
    NetworkState,
    PowerState,
    RemovableMediaState,
    StaticAudioHAL,
    StaticDisplayHAL,
    StaticInputHAL,
    StaticNetworkHAL,
    StaticPowerHAL,
    StaticRemovableMediaHAL,
)
from greia_platform.input_core import (
    InputEdge,
    InputSource,
    InteractionProfile,
    MovementVector,
    PhysicalControl,
    SemanticAction,
    StandardInputMapper,
    VirtualPointer,
    is_platform_reserved,
    navigation_direction,
    normalize_stick,
)


class StandardInputMapperTests(unittest.TestCase):
    def test_navigation_learns_arrows_space_enter_dpad_and_south_face(self) -> None:
        mapper = StandardInputMapper(InteractionProfile.NAVIGATION)
        cases = (
            (PhysicalControl.KEY_UP, SemanticAction.NAV_UP),
            (PhysicalControl.KEY_LEFT, SemanticAction.NAV_LEFT),
            (PhysicalControl.KEY_SPACE, SemanticAction.ACTIVATE),
            (PhysicalControl.KEY_ENTER, SemanticAction.ACTIVATE),
            (PhysicalControl.CONTROLLER_DPAD_RIGHT, SemanticAction.NAV_RIGHT),
            (PhysicalControl.CONTROLLER_FACE_SOUTH, SemanticAction.ACTIVATE),
        )
        for control, expected in cases:
            event = mapper.digital(control, InputEdge.PRESSED, InputSource.CONTROLLER)
            self.assertIsNotNone(event)
            assert event is not None
            self.assertIs(event.action, expected)

    def test_game_baseline_is_arrows_space_and_controller_move_primary(self) -> None:
        mapper = StandardInputMapper(InteractionProfile.GAME)
        self.assertIs(
            mapper.digital(
                PhysicalControl.KEY_RIGHT,
                InputEdge.PRESSED,
                InputSource.KEYBOARD,
            ).action,
            SemanticAction.MOVE_RIGHT,
        )
        self.assertIs(
            mapper.digital(
                PhysicalControl.KEY_SPACE,
                InputEdge.PRESSED,
                InputSource.KEYBOARD,
            ).action,
            SemanticAction.PRIMARY,
        )
        self.assertIs(
            mapper.digital(
                PhysicalControl.CONTROLLER_FACE_SOUTH,
                InputEdge.PRESSED,
                InputSource.CONTROLLER,
            ).action,
            SemanticAction.PRIMARY,
        )
        self.assertIs(
            mapper.digital(
                PhysicalControl.CONTROLLER_FACE_EAST,
                InputEdge.PRESSED,
                InputSource.CONTROLLER,
            ).action,
            SemanticAction.SECONDARY,
        )
        self.assertIs(
            mapper.digital(
                PhysicalControl.CONTROLLER_BACK,
                InputEdge.PRESSED,
                InputSource.CONTROLLER,
            ).action,
            SemanticAction.CANCEL,
        )

    def test_pointer_profile_uses_controller_south_as_primary_without_stealing_arrows(self) -> None:
        mapper = StandardInputMapper(InteractionProfile.POINTER)
        event = mapper.digital(
            PhysicalControl.CONTROLLER_FACE_SOUTH,
            InputEdge.PRESSED,
            InputSource.CONTROLLER,
        )
        self.assertIsNotNone(event)
        assert event is not None
        self.assertIs(event.action, SemanticAction.PRIMARY)
        self.assertIsNone(
            mapper.digital(
                PhysicalControl.KEY_RIGHT,
                InputEdge.PRESSED,
                InputSource.KEYBOARD,
            )
        )

    def test_text_and_hybrid_profiles_do_not_steal_typing_keys(self) -> None:
        for profile in (InteractionProfile.TEXT, InteractionProfile.HYBRID):
            mapper = StandardInputMapper(profile)
            self.assertIsNone(
                mapper.digital(
                    PhysicalControl.KEY_SPACE,
                    InputEdge.PRESSED,
                    InputSource.KEYBOARD,
                )
            )
            self.assertIsNone(
                mapper.digital(
                    PhysicalControl.KEY_ENTER,
                    InputEdge.PRESSED,
                    InputSource.KEYBOARD,
                )
            )

    def test_controller_guide_is_platform_reserved_and_never_mapped_to_activity(self) -> None:
        self.assertTrue(is_platform_reserved(PhysicalControl.CONTROLLER_GUIDE))
        for profile in InteractionProfile:
            self.assertIsNone(
                StandardInputMapper(profile).digital(
                    PhysicalControl.CONTROLLER_GUIDE,
                    InputEdge.PRESSED,
                    InputSource.CONTROLLER,
                )
            )


class AnalogInputTests(unittest.TestCase):
    def test_stick_dead_zone_and_normalization_are_centralized(self) -> None:
        self.assertEqual(normalize_stick(0.1, -0.1), MovementVector(0.0, 0.0))
        vector = normalize_stick(1.0, 1.0)
        self.assertLessEqual(vector.magnitude, 1.0)
        self.assertGreater(vector.x, 0.0)
        self.assertGreater(vector.y, 0.0)

    def test_navigation_direction_uses_dominant_axis_after_threshold(self) -> None:
        self.assertIsNone(navigation_direction(MovementVector(0.2, 0.1)))
        self.assertIs(
            navigation_direction(MovementVector(-0.8, 0.4)),
            SemanticAction.NAV_LEFT,
        )
        self.assertIs(
            navigation_direction(MovementVector(0.3, 0.9)),
            SemanticAction.NAV_DOWN,
        )

    def test_virtual_pointer_is_screen_relative_and_hard_bounded(self) -> None:
        pointer = VirtualPointer(1024, 600, x=512, y=300)
        start = pointer.position
        moved = pointer.move(1.0, 0.0, 0.25)
        self.assertGreater(moved[0], start[0])
        self.assertEqual(moved[1], start[1])
        for _ in range(20):
            pointer.move(1.0, 1.0, 1.0)
        self.assertEqual(pointer.position, (1023, 599))
        for _ in range(20):
            pointer.move(-1.0, -1.0, 1.0)
        self.assertEqual(pointer.position, (0, 0))


class ControllerCapabilityTests(unittest.TestCase):
    def test_linux_presence_probe_detects_conventional_joystick_node(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertFalse(LinuxControllerPresenceProbe(root).available())
            (root / "js0").write_bytes(b"")
            self.assertTrue(LinuxControllerPresenceProbe(root).available())

    def test_hal_snapshot_exposes_controller_without_conflating_pointer(self) -> None:
        hal = GreiaHAL(
            display=StaticDisplayHAL(DisplayState(True)),
            input=StaticInputHAL(
                InputState(pointer=False, keyboard=True, touch=False, controller=True)
            ),
            audio=StaticAudioHAL(AudioState(False)),
            removable_media=StaticRemovableMediaHAL(RemovableMediaState(False)),
            network=StaticNetworkHAL(NetworkState(False)),
            power=StaticPowerHAL(PowerState(False)),
        )
        snapshot = HALDeviceCapabilityProbe(hal).probe()
        self.assertIn("controller", snapshot.capabilities)
        self.assertIn("keyboard", snapshot.capabilities)
        self.assertNotIn("pointer", snapshot.capabilities)
        self.assertTrue(snapshot.details["input"]["controller"])


if __name__ == "__main__":
    unittest.main()
