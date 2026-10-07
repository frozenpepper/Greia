"""Shape Garden shared-image request/publish state; requires Pygame import."""
from __future__ import annotations

import hashlib
import unittest
from types import SimpleNamespace
from unittest import mock

from activities.shape_garden.garden_app import GardenApp
from activities.shape_garden.garden_model import GardenModel
from activities.shape_garden.garden_project_model import GardenProject


class FakeCreations:
    def __init__(self):
        self.requests = []
        self.polls = []
        self.published = []
        self.reply = SimpleNamespace(state="pending", selection_token=None)

    def request_selection(self, *, media_types):
        self.requests.append(media_types)
        return "request-1"

    def poll_selection(self, request_id):
        self.polls.append(request_id)
        return self.reply

    def publish_private_file(self, name, *, media_type, role):
        self.published.append((name, media_type, role))


class GardenCreationFlowTests(unittest.TestCase):
    def make_app(self):
        app = object.__new__(GardenApp)
        app.creations = FakeCreations()
        app.repository = SimpleNamespace()
        app.model = GardenModel()
        app.project = GardenProject()
        app.project_dirty = False
        app.project_error = False
        app.import_request = None
        app.import_next_poll = 0.0
        app.import_state = ""
        app.import_feedback_until = 0.0
        app.publish_state = ""
        app.publish_feedback_until = 0.0
        app._last_published_digest = None
        app._save_project = lambda: True
        return app

    def test_import_request_is_typed_and_nonblocking(self):
        app = self.make_app()
        with mock.patch("activities.shape_garden.garden_app.time.monotonic", return_value=10.0):
            app._request_background()
        self.assertEqual(app.creations.requests, [("image/png",)])
        self.assertEqual(app.import_request, "request-1")
        self.assertEqual(app.import_state, "pending")
        self.assertGreaterEqual(app.import_next_poll, 10.0 + app.IMPORT_POLL_SECONDS)

    def test_poll_is_rate_limited_and_cancel_is_noop_to_artwork(self):
        app = self.make_app()
        app.import_request = "request-1"
        app.import_next_poll = 20.0
        app._poll_background(19.9)
        self.assertEqual(app.creations.polls, [])
        app.creations.reply = SimpleNamespace(state="cancelled", selection_token=None)
        app._poll_background(20.0)
        self.assertEqual(app.creations.polls, ["request-1"])
        self.assertIsNone(app.import_request)
        self.assertEqual(app.import_state, "")

    def test_ready_handle_is_consumed_once_by_import_hook(self):
        app = self.make_app()
        app.import_request = "request-1"
        app.creations.reply = SimpleNamespace(
            state="ready", selection_token="one-use"
        )
        calls = []
        app._accept_background = lambda token: calls.append(token) or True
        app._poll_background(30.0)
        self.assertEqual(calls, ["one-use"])
        self.assertEqual(app.import_state, "imported")
        self.assertIsNone(app.import_request)

    def test_publish_deduplicates_same_flattened_snapshot(self):
        app = self.make_app()
        payload = b"flattened-png"
        app.repository.save_export = lambda data: "garden/shared.png"
        app._render_project_snapshot = lambda: object()
        with mock.patch(
            "activities.shape_garden.garden_app.encode_surface_png",
            return_value=payload,
        ), mock.patch(
            "activities.shape_garden.garden_app.emit_activity_event"
        ) as emit:
            app._publish_project()
            app._publish_project()
        self.assertEqual(
            app.creations.published,
            [("garden/shared.png", "image/png", "composition")],
        )
        emit.assert_called_once()
        self.assertEqual(emit.call_args.args[0], "creation.completed")
        self.assertEqual(
            app._last_published_digest, hashlib.sha256(payload).hexdigest()
        )


if __name__ == "__main__":
    unittest.main()
