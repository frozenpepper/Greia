"""Writing trusted UTF-8 creation publication/import contracts.

Execution is intentionally deferred to the accumulated desktop acceptance.
"""
from __future__ import annotations

import hashlib
import unittest
from types import SimpleNamespace
from unittest import mock

from greia_platform.creation_client import CreationTransfer

from activities.writing.writing_app import WritingApp
from activities.writing.writing_model import (
    DocumentRepository,
    TextBuffer,
    UndoHistory,
)


class MemoryStorage:
    def __init__(self):
        self.kv = {}
        self.files = {}
        self.fail_index = False

    def kv_get(self, key, default=None):
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        if self.fail_index:
            raise RuntimeError("index write failed")
        self.kv[key] = value

    def file_write_atomic(self, name, payload):
        self.files[name] = bytes(payload)

    def file_read(self, name):
        if name not in self.files:
            raise RuntimeError("missing")
        return self.files[name]

    def file_delete(self, name):
        return self.files.pop(name, None) is not None


class FakeCreations:
    def __init__(self):
        self.requests = []
        self.published = []
        self.reply = SimpleNamespace(state="pending", selection_token=None)
        self.transfer = None

    def request_selection(self, *, media_types, roles=()):
        self.requests.append((media_types, roles))
        return "request-1"

    def poll_selection(self, request_id):
        return self.reply

    def import_selected(self, token):
        return self.transfer

    def publish_private_file(self, name, *, media_type, role, title=""):
        self.published.append((name, media_type, role, title))
        return {"ok": True}


class _Renderer:
    def __init__(self):
        self.invalidations = 0

    def invalidate_layout(self):
        self.invalidations += 1


class WritingCreationTests(unittest.TestCase):
    def make_app(self):
        storage = MemoryStorage()
        repo = DocumentRepository(storage)
        record = repo.create_text("Original")
        app = object.__new__(WritingApp)
        app.repository = repo
        app.creations = FakeCreations()
        app.shared_request = None
        app.shared_next_poll = 0.0
        app.shared_state = ""
        app.shared_feedback_until = 0.0
        app._last_shared_digest = {}
        app.records = [record]
        app.current = record
        app.buffer = TextBuffer("Original", len("Original"))
        app.undo_history = UndoHistory()
        app.mode = "edit"
        app.emoji_picker_open = False
        app.dirty = False
        app.save_error = False
        app.scroll_line = 0
        app.renderer = _Renderer()
        app._keep_cursor_visible = lambda: None
        return app, storage

    def test_picker_accepts_document_and_postcard_roles_only(self):
        app, _ = self.make_app()
        app._request_shared_document()
        self.assertEqual(
            app.creations.requests,
            [(("text/plain",), ("document", "postcard"))],
        )

    def test_postcard_import_creates_independent_private_document(self):
        app, storage = self.make_app()
        payload = "Ciao 👩🏽‍🔬\nseconda riga".encode("utf-8")
        app.creations.transfer = CreationTransfer(
            {
                "media_type": "text/plain",
                "role": "postcard",
                "sha256": hashlib.sha256(payload).hexdigest(),
            },
            payload,
        )
        old_id = app.current.document_id
        self.assertTrue(app._accept_shared_document("one-use"))
        self.assertNotEqual(app.current.document_id, old_id)
        self.assertEqual(app.buffer.text, payload.decode("utf-8"))
        private_name = app.repository.private_document_name(
            app.current.document_id
        )
        self.assertEqual(storage.files[private_name], payload)
        self.assertEqual(app.renderer.invalidations, 1)

    def test_import_rejects_wrong_role_digest_and_invalid_utf8(self):
        app, _ = self.make_app()
        original = app.current.document_id
        for record, payload in (
            (
                {"media_type": "text/plain", "role": "caption", "sha256": hashlib.sha256(b"x").hexdigest()},
                b"x",
            ),
            (
                {"media_type": "text/plain", "role": "document", "sha256": "bad"},
                b"x",
            ),
            (
                {"media_type": "text/plain", "role": "document", "sha256": hashlib.sha256(b"\xff").hexdigest()},
                b"\xff",
            ),
        ):
            app.creations.transfer = CreationTransfer(record, payload)
            self.assertFalse(app._accept_shared_document("bad"))
            self.assertEqual(app.current.document_id, original)

    def test_publish_uses_saved_private_document_and_deduplicates_unchanged(self):
        app, storage = self.make_app()
        app._save = mock.Mock(return_value=True)
        with mock.patch(
            "activities.writing.writing_app.time.monotonic",
            return_value=10.0,
        ):
            app._publish_current_document()
            app._publish_current_document()
        self.assertEqual(len(app.creations.published), 1)
        name, media_type, role, _title = app.creations.published[0]
        self.assertEqual(
            name,
            app.repository.private_document_name(app.current.document_id),
        )
        self.assertEqual(media_type, "text/plain")
        self.assertEqual(role, "document")
        self.assertIn(name, storage.files)

    def test_create_import_rolls_back_new_file_when_index_commit_fails(self):
        storage = MemoryStorage()
        repo = DocumentRepository(storage)
        storage.fail_index = True
        with self.assertRaises(RuntimeError):
            repo.create_text("Never committed")
        self.assertEqual(storage.files, {})


if __name__ == "__main__":
    unittest.main()
