from __future__ import annotations

import unittest

from greia_platform.device_capabilities import (
    DeviceCapabilityError,
    DeviceCapabilityService,
    DeviceCapabilitySnapshot,
    HALDeviceCapabilityProbe,
)
from greia_platform.hal import (
    AudioState,
    DisplayState,
    GreiaHAL,
    InputState,
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
from greia_platform.hardware import DisplayMode


class DeviceCapabilityTests(unittest.TestCase):
    def test_snapshot_is_semantic_portable_and_immutable(self) -> None:
        details = {"display": {"backend": "test", "modes": ["800x600"]}}
        snapshot = DeviceCapabilitySnapshot.create(
            {"display", "pointer"},
            source_id="unit-test",
            machine="i686",
            details=details,
            observed_at="1970-01-01T00:00:00Z",
        )
        details["display"]["backend"] = "mutated"
        self.assertEqual(snapshot.machine, "i686")
        self.assertTrue(snapshot.has("display"))
        self.assertEqual(snapshot.details["display"]["backend"], "test")  # type: ignore[index]
        with self.assertRaises(TypeError):
            snapshot.details["new"] = True  # type: ignore[index]
        self.assertEqual(len(snapshot.token), 64)

    def test_invalid_capability_and_source_ids_fail_closed(self) -> None:
        with self.assertRaises(DeviceCapabilityError):
            DeviceCapabilitySnapshot.create({"Display"}, source_id="test")
        with self.assertRaises(DeviceCapabilityError):
            DeviceCapabilitySnapshot.create({"display"}, source_id="bad source")

    def test_hal_probe_maps_typed_states_to_semantic_capabilities(self) -> None:
        mode = DisplayMode(width=1024, height=600, refresh_hz=60.0)
        hal = GreiaHAL(
            display=StaticDisplayHAL(DisplayState(True, (mode,), "kms-test")),
            input=StaticInputHAL(InputState(True, True, False, "input-test")),
            audio=StaticAudioHAL(AudioState(True, "audio-test")),
            removable_media=StaticRemovableMediaHAL(
                RemovableMediaState(True, "media-test")
            ),
            network=StaticNetworkHAL(NetworkState(False, "network-test")),
            power=StaticPowerHAL(PowerState(True, "power-test")),
        )
        snapshot = HALDeviceCapabilityProbe(hal, source_id="test-hal").probe()
        self.assertEqual(
            snapshot.capabilities,
            frozenset(
                {
                    "display",
                    "pointer",
                    "keyboard",
                    "audio.basic",
                    "removable_media",
                    "power.controlled_shutdown",
                }
            ),
        )
        self.assertEqual(snapshot.details["display"]["backend"], "kms-test")  # type: ignore[index]
        self.assertFalse(snapshot.details["network"]["service_available"])  # type: ignore[index]

    def test_service_caches_until_explicit_refresh(self) -> None:
        first = DeviceCapabilitySnapshot.create(
            {"display"}, source_id="first", observed_at="1970-01-01T00:00:00Z"
        )
        second = DeviceCapabilitySnapshot.create(
            {"display", "pointer"}, source_id="second", observed_at="1970-01-01T00:00:01Z"
        )

        class Probe:
            def __init__(self) -> None:
                self.calls = 0

            def probe(self) -> DeviceCapabilitySnapshot:
                self.calls += 1
                return first if self.calls == 1 else second

        probe = Probe()
        service = DeviceCapabilityService(probe)
        self.assertIs(service.snapshot(), first)
        self.assertIs(service.snapshot(), first)
        self.assertEqual(probe.calls, 1)
        self.assertIs(service.snapshot(refresh=True), second)
        self.assertEqual(probe.calls, 2)


if __name__ == "__main__":
    unittest.main()
