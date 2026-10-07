"""Painting publication: retained draft and explicit shared snapshots."""
from __future__ import annotations

import hashlib
import unittest
from types import SimpleNamespace
from unittest import mock

from greia_platform.creation_client import CreationTransfer

from activities.painting.painting_app import PaintingApp
from activities.painting.painting_model import PaintingRecord


class PrivateDrawing:
    def __init__(self):
        self.png = b"sample png data for publisher stub"

    def private_png_name(self, painting_id):
        return f"paintings/{painting_id}.png"

    def load_png(self, painting_id):
        return self.png


class ShareRecorder:
    def __init__(self):
        self.published = []
        self.fail = False

    def publish_private_file(self, name, *, media_type, role):
        if self.fail:
            raise RuntimeError("broker unavailable")
        self.published.append((name, media_type, role))
        return {"creation_id": "fake"}


class PaintingCreationTests(unittest.TestCase):
    def make_app(self):
        app = object.__new__(PaintingApp)
        app.repository = PrivateDrawing()
        app.creations = ShareRecorder()
        app.current = PaintingRecord("0123456789abcdef0123456789abcdef")
        app._last_shared = None
        app.shared_feedback = ""
        app.shared_feedback_until = 0.0
        app._save = lambda: True
        return app

    def test_publish_deliberate_and_deduplicate_identical_content(self):
        app = self.make_app()
        self.assertEqual(app.creations.published, [])
        app._publish_current()
        self.assertEqual(app.creations.published, [(
            app.repository.private_png_name(app.current.painting_id),
            "image/png", "drawing",
        )])
        app._publish_current()
        self.assertEqual(len(app.creations.published), 1)
        app.repository.png += b"changed"
        app._publish_current()
        self.assertEqual(len(app.creations.published), 2)

    def test_publish_failure_preserves_private_document(self):
        app = self.make_app()
        app.creations.fail = True
        app._publish_current()
        self.assertEqual(app.shared_feedback, "error")
        self.assertIsNone(app._last_shared)
        self.assertEqual(app.current.painting_id, "0123456789abcdef0123456789abcdef")

    def test_import_selected_png_creates_independent_editable_private_project(self):
        app = self.make_app()
        original_id = app.current.painting_id
        app.repository.create = lambda png: PaintingRecord("abcdef0123456789abcdef0123456789")
        app.records = [app.current]
        app.renderer = SimpleNamespace(canvas_rect=SimpleNamespace(size=(512, 380)))
        app.history = SimpleNamespace(clear=lambda: None)
        app.active_points = []
        app.mode = "gallery"
        app.dirty = False
        payload = b"decoded fake picture"
        record = {"media_type": "image/png", "sha256": hashlib.sha256(payload).hexdigest()}
        app.creations.import_selected = lambda token: CreationTransfer(record, payload)
        fake_surface = SimpleNamespace(copy=lambda: SimpleNamespace())
        with mock.patch("activities.painting.painting_app._decode_png", return_value=fake_surface):
            self.assertTrue(app.accept_selected_png("one-time-picker-grant"))
        self.assertEqual(app.current.painting_id, "abcdef0123456789abcdef0123456789")
        self.assertNotEqual(app.current.painting_id, original_id)
        self.assertEqual(app.mode, "paint")
        self.assertFalse(app.save_error)
        self.assertEqual(app.records[1].painting_id, original_id)

    def test_invalid_shared_picture_does_not_replace_current_painting(self):
        app = self.make_app()
        original = app.current
        app.records = [original]
        app.creations.import_selected = lambda token: CreationTransfer(
            {"media_type": "image/png", "sha256": "tampered"}, b"not a valid image"
        )
        self.assertFalse(app.accept_selected_png("expired-or-corrupt"))
        self.assertEqual(app.current, original)
        self.assertTrue(app.save_error)

    def test_no_publication_if_private_save_fails(self):
        app = self.make_app()
        app._save = lambda: False
        app._publish_current()
        self.assertEqual(app.creations.published, [])
        self.assertEqual(app.shared_feedback, "error")
