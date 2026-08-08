from __future__ import annotations

import tempfile
import unittest
from unittest import mock
from http import cookies
from pathlib import Path
from http.server import HTTPServer

from greia_parent.server import ParentHTTPServer, ParentStatusApplication, render_status_page
from greia_platform.activities import ActivityValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ParentStatusTests(unittest.TestCase):
    def test_status_page_escapes_activity_ids(self) -> None:
        page = render_status_page(
            {
                "runtime_api_version": "0.1",
                "uptime_seconds": 10,
                "memory_available_bytes": 100,
                "memory_total_bytes": 200,
                "disk_free_bytes": 300,
                "disk_total_bytes": 400,
                "activities": ("<bad>",),
                "customization": {
                    "background_color": "#F7EBCB",
                    "accent_color": "#FFC234",
                    "text_color": "#3D2C1F",
                    "wallpaper_enabled": False,
                },
            }
        )
        self.assertIn("&lt;bad&gt;", page)
        self.assertNotIn("<li><bad></li>", page)
        self.assertIn("Reset child appearance", page)

    def test_parent_reset_restores_defaults_and_removes_wallpaper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "parent"
            customization = root / "customization"
            app = ParentStatusApplication(
                PROJECT_ROOT,
                state,
                customization,
                root / "hardware",
                root / "hardware-status.json",
            )
            app.theme_store.set_colors(background="sky", accent="grape", text="navy")
            customization.mkdir(parents=True, exist_ok=True)
            app.theme_store.wallpaper_path.write_bytes(b"placeholder")
            app.theme_store.set_wallpaper_enabled(True)

            reset = app.reset_customization()
            self.assertEqual(reset["background"], "cream")
            self.assertFalse(reset["wallpaper_enabled"])
            self.assertFalse(app.theme_store.wallpaper_path.exists())

    def test_parent_hardware_controls_are_bounded_and_resettable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = ParentStatusApplication(
                PROJECT_ROOT,
                root / "parent",
                root / "customization",
                root / "hardware",
                root / "hardware-status.json",
            )
            updated = app.update_hardware(
                {
                    "touchpad_tap": ["on"],
                    "mouse_speed": ["0.50"],
                    "touchpad_speed": ["-0.25"],
                    "resolution": ["auto"],
                }
            )
            self.assertTrue(updated["touchpad_tap"])
            self.assertEqual(updated["mouse_speed"], 0.5)
            reset = app.reset_hardware()
            self.assertFalse(reset["touchpad_tap"])
            self.assertEqual(reset["resolution"], "auto")

    def test_parent_profile_lifecycle_is_typed_and_never_returns_password_material(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = ParentStatusApplication(
                PROJECT_ROOT,
                root / "parent",
                root / "compatibility-customization",
                root / "hardware",
                root / "hardware-status.json",
                profiles_dir=root / "profiles",
                active_profile_status_path=root / "active-profile.json",
            )
            created = app.create_profile(
                {
                    "display_name": ["Mia"],
                    "avatar_id": ["robot"],
                    "secret": ["2468"],
                    "mask_secret": ["on"],
                }
            )
            profile_id = str(created["profile_id"])
            self.assertTrue(created["has_secret"])
            self.assertTrue(created["mask_secret"])
            self.assertNotIn("secret", created)
            self.assertNotIn("digest", created)

            updated = app.update_profile(
                {
                    "profile_id": [profile_id],
                    "display_name": ["Mia Rose"],
                    "avatar_id": ["owl"],
                    "secret_action": ["clear"],
                }
            )
            self.assertEqual(updated["display_name"], "Mia Rose")
            self.assertEqual(updated["avatar_id"], "owl")
            self.assertFalse(updated["has_secret"])

            app._theme_store(profile_id).set_colors(background="sky")
            reset = app.reset_customization(profile_id)
            self.assertEqual(reset["background"], "cream")

            payload = app.profiles_payload()
            encoded = repr(payload).lower()
            self.assertNotIn("digest", encoded)
            self.assertNotIn("salt", encoded)
            self.assertNotIn("2468", encoded)

            deleted = app.delete_profile(
                {"profile_id": [profile_id], "confirm": ["delete"]}
            )
            self.assertEqual(deleted, {"deleted": profile_id})
            self.assertFalse((root / "profiles" / "data" / profile_id).exists())

    def test_active_profile_must_be_switched_away_before_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = ParentStatusApplication(
                PROJECT_ROOT,
                root / "parent",
                profiles_dir=root / "profiles",
                hardware_settings_dir=root / "hardware",
                hardware_status_path=root / "hardware-status.json",
                active_profile_status_path=root / "active-profile.json",
            )
            active = app.profile_store.list_profiles()[0]
            second = app.profile_store.create("Mia", "robot")
            app.active_session.write(second)
            with self.assertRaisesRegex(Exception, "switch away"):
                app.delete_profile(
                    {"profile_id": [second.profile_id], "confirm": ["delete"]}
                )
            self.assertIsNotNone(app.profile_store.get(second.profile_id))
            app.active_session.write(active)
            self.assertEqual(
                app.delete_profile(
                    {"profile_id": [second.profile_id], "confirm": ["delete"]}
                ),
                {"deleted": second.profile_id},
            )

    def test_empty_pairing_token_is_rotated_and_never_authorizes_empty_request(self) -> None:
        class Handler:
            headers: dict[str, str] = {}

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "parent"
            state.mkdir()
            token_path = state / "parent-pairing-token"
            token_path.write_text("\n", encoding="ascii")
            app = ParentStatusApplication(
                PROJECT_ROOT,
                state,
                profiles_dir=root / "profiles",
                hardware_settings_dir=root / "hardware",
                hardware_status_path=root / "hardware-status.json",
            )
            self.assertGreaterEqual(len(app.token), 32)
            self.assertEqual(token_path.read_text(encoding="ascii").strip(), app.token)
            self.assertFalse(app.authorized(Handler(), {}))

    def test_malformed_cookie_is_unauthorized_not_a_handler_crash(self) -> None:
        class Handler:
            headers = {"Cookie": "broken"}

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = ParentStatusApplication(
                PROJECT_ROOT,
                root / "parent",
                profiles_dir=root / "profiles",
                hardware_settings_dir=root / "hardware",
                hardware_status_path=root / "hardware-status.json",
            )
            with mock.patch.object(
                cookies.SimpleCookie, "load", side_effect=cookies.CookieError("bad")
            ):
                self.assertFalse(app.authorized(Handler(), {}))

    def test_invalid_activity_catalogue_does_not_take_down_parent_controls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = ParentStatusApplication(
                PROJECT_ROOT,
                root / "parent",
                profiles_dir=root / "profiles",
                hardware_settings_dir=root / "hardware",
                hardware_status_path=root / "hardware-status.json",
            )
            with mock.patch.object(
                app.registry, "discover", side_effect=ActivityValidationError("broken package")
            ):
                payload = app.health_payload()
            self.assertEqual(payload["activities"], ())
            self.assertIn("broken package", str(payload["activity_catalogue_error"]))
            self.assertTrue(payload["profiles"])

    def test_parent_server_is_single_threaded_and_has_socket_timeout(self) -> None:
        self.assertTrue(issubclass(ParentHTTPServer, HTTPServer))
        self.assertEqual(ParentHTTPServer.request_timeout_seconds, 10.0)



if __name__ == "__main__":
    unittest.main()
