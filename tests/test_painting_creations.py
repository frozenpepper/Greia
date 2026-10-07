"""Painting publication: retained draft and explicit shared snapshots."""
from __future__ import annotations

import unittest

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

    def test_no_publication_if_private_save_fails(self):
        app = self.make_app()
        app._save = lambda: False
        app._publish_current()
        self.assertEqual(app.creations.published, [])
        self.assertEqual(app.shared_feedback, "error")
