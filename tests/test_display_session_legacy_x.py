from __future__ import annotations

import unittest

from greia_launcher.display_session import DisplayTransportKind
from greia_launcher.display_session_legacy_x import LegacyXDisplaySessionBackend


class LegacyXDisplaySessionBackendTests(unittest.TestCase):
    def test_xinit_style_display_without_xauthority_is_representable(self) -> None:
        backend = LegacyXDisplaySessionBackend({"DISPLAY": ":0"})
        transport = backend.prepare_activity("session-1")

        self.assertEqual(transport.kind, DisplayTransportKind.LEGACY_X11)
        self.assertEqual(
            dict(transport.environment()),
            {"SDL_VIDEODRIVER": "x11", "DISPLAY": ":0"},
        )

    def test_existing_xauthority_is_preserved_and_validated(self) -> None:
        backend = LegacyXDisplaySessionBackend(
            {
                "DISPLAY": ":0",
                "XAUTHORITY": "/var/lib/greia-kid/.Xauthority",
            }
        )
        transport = backend.prepare_activity("session-2")
        self.assertEqual(
            transport.environment()["XAUTHORITY"],
            "/var/lib/greia-kid/.Xauthority",
        )

        invalid = LegacyXDisplaySessionBackend(
            {"DISPLAY": ":0", "XAUTHORITY": "relative-authority"}
        )
        with self.assertRaisesRegex(ValueError, "must be absolute"):
            invalid.prepare_activity("session-3")

    def test_missing_display_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "no DISPLAY"):
            LegacyXDisplaySessionBackend({}).prepare_activity("session-4")

    def test_ambiguous_wayland_or_conflicting_sdl_backend_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Wayland"):
            LegacyXDisplaySessionBackend(
                {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0"}
            ).prepare_activity("session-5")

        with self.assertRaisesRegex(RuntimeError, "conflicting SDL_VIDEODRIVER"):
            LegacyXDisplaySessionBackend(
                {"DISPLAY": ":0", "SDL_VIDEODRIVER": "kmsdrm"}
            ).prepare_activity("session-6")

    def test_present_and_restore_do_not_create_parallel_x_mechanisms(self) -> None:
        backend = LegacyXDisplaySessionBackend({"DISPLAY": ":0"})
        backend.present_activity("session-7")
        backend.restore_shell("session-7")


if __name__ == "__main__":
    unittest.main()
