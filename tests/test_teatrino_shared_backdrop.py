"""Teatrino nonblocking shared-backdrop and truthful save state."""
from __future__ import annotations

import hashlib
import unittest
from types import SimpleNamespace
from unittest import mock

from greia_platform.creation_client import CreationTransfer

from activities.teatrino_fiabe.teatrino_app import TeatrinoApp
from activities.teatrino_fiabe.teatrino_model import ShowStorageError


class FakeCreations:
    def __init__(self):
        self.requests = []
        self.polls = []
        self.reply = SimpleNamespace(state="pending", selection_token=None)
        self.transfer = None

    def request_selection(self, *, media_types):
        self.requests.append(media_types)
        return "request-1"

    def poll_selection(self, request_id):
        self.polls.append(request_id)
        return self.reply

    def import_selected(self, token):
        return self.transfer


class FakeSound:
    def __init__(self):
        self.played = []

    def play(self, sound_id):
        self.played.append(sound_id)


class TeatrinoBackdropFlowTests(unittest.TestCase):
    def make_app(self):
        app = object.__new__(TeatrinoApp)
        app.creations = FakeCreations()
        app.app_mode = "stage"
        app.is_recording = False
        app.backdrop_import_request = None
        app.backdrop_import_next_poll = 0.0
        app.backdrop_import_state = ""
        app.backdrop_import_feedback_until = 0.0
        app.feedback_text = ""
        app.feedback_timer = 0.0
        app.custom_backdrop_png = None
        app.custom_backdrop_surface = None
        return app

    def test_request_is_png_only_and_poll_is_bounded(self):
        app = self.make_app()
        with mock.patch(
            "activities.teatrino_fiabe.teatrino_app.time.monotonic",
            return_value=10.0,
        ):
            app._request_shared_backdrop()
        self.assertEqual(app.creations.requests, [("image/png",)])
        self.assertEqual(app.backdrop_import_request, "request-1")
        self.assertGreaterEqual(app.backdrop_import_next_poll, 10.12)
        app._poll_shared_backdrop(10.1)
        self.assertEqual(app.creations.polls, [])

    def test_cancel_preserves_current_backdrop(self):
        app = self.make_app()
        app.custom_backdrop_png = b"current"
        app.custom_backdrop_surface = object()
        app.backdrop_import_request = "request-1"
        app.creations.reply = SimpleNamespace(
            state="cancelled", selection_token=None
        )
        app._poll_shared_backdrop(20.0)
        self.assertEqual(app.custom_backdrop_png, b"current")
        self.assertIsNotNone(app.custom_backdrop_surface)
        self.assertIsNone(app.backdrop_import_request)

    def test_ready_handle_validates_digest_before_replacing_backdrop(self):
        app = self.make_app()
        payload = b"new-picture"
        record = {
            "media_type": "image/png",
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        app.creations.transfer = CreationTransfer(record, payload)
        surface = object()
        with mock.patch(
            "activities.teatrino_fiabe.teatrino_app.decode_png_surface",
            return_value=surface,
        ):
            self.assertTrue(app._accept_shared_backdrop("one-use"))
        self.assertEqual(app.custom_backdrop_png, payload)
        self.assertIs(app.custom_backdrop_surface, surface)

    def test_integrity_failure_keeps_existing_backdrop(self):
        app = self.make_app()
        old_surface = object()
        app.custom_backdrop_png = b"old"
        app.custom_backdrop_surface = old_surface
        app.creations.transfer = CreationTransfer(
            {"media_type": "image/png", "sha256": "bad"},
            b"corrupt",
        )
        self.assertFalse(app._accept_shared_backdrop("bad-handle"))
        self.assertEqual(app.custom_backdrop_png, b"old")
        self.assertIs(app.custom_backdrop_surface, old_surface)

    def test_failed_show_save_reports_error_and_emits_no_creation_event(self):
        app = self.make_app()
        app.show_repo = SimpleNamespace(
            save_show=mock.Mock(side_effect=ShowStorageError("disk")),
            list_shows=mock.Mock(return_value=[]),
        )
        app.sound_mgr = FakeSound()
        app.ui_strings = {
            "recording_save_failed": "Could not save this show."
        }
        app.puppets_on_stage = []
        app.recorded_frames = []
        app.recorded_sfx = []
        with mock.patch(
            "activities.teatrino_fiabe.teatrino_app.emit_activity_event"
        ) as emit:
            result = app._persist_recorded_show(
                "forest", 3.0, b"RIFF", feedback_seconds=2.5
            )
        self.assertIsNone(result)
        emit.assert_not_called()
        self.assertEqual(app.sound_mgr.played, ["boing"])
        self.assertIn("Could not save", app.feedback_text)

    def test_successful_show_save_emits_after_durable_repository_result(self):
        app = self.make_app()
        app.show_repo = SimpleNamespace(
            save_show=mock.Mock(return_value={"id": "show-1"}),
            list_shows=mock.Mock(return_value=[{"id": "show-1"}]),
        )
        app.sound_mgr = FakeSound()
        app.ui_strings = {"recording_saved": "Saved"}
        app.puppets_on_stage = []
        app.recorded_frames = []
        app.recorded_sfx = []
        with mock.patch(
            "activities.teatrino_fiabe.teatrino_app.emit_activity_event"
        ) as emit:
            result = app._persist_recorded_show(
                "forest", 3.0, None, feedback_seconds=2.5
            )
        self.assertEqual(result, {"id": "show-1"})
        emit.assert_called_once()
        self.assertEqual(app.sound_mgr.played, ["applause"])


if __name__ == "__main__":
    unittest.main()
