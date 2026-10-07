"""Posta di Leo trusted UTF-8 import/publication and storage contracts.

Execution is intentionally deferred to the accumulated desktop acceptance.
"""
from __future__ import annotations

import hashlib
import random
import unittest
from types import SimpleNamespace

from greia_platform.creation_client import CreationTransfer

from activities.posta_di_leo.postcard_app import PostcardActivity
from activities.posta_di_leo.postcard_model import (
    MAX_GRAPHEMES,
    PostcardDraft,
    PostcardLibrary,
    SavedPostcard,
)
from activities.posta_di_leo.postcard_services import GreiaPostcardStorage
from greia_platform.typography import grapheme_spans


class MemoryStorage:
    def __init__(self):
        self.value = None
        self.files = {}
        self.fail_get = False
        self.fail_set = False

    def kv_get(self, key):
        if self.fail_get:
            raise RuntimeError("read failed")
        return self.value

    def kv_set(self, key, value):
        if self.fail_set:
            raise RuntimeError("write failed")
        self.value = value

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
        self.transfer = None
        self.reply = SimpleNamespace(state="pending", selection_token=None)

    def request_selection(self, *, media_types, roles=()):
        self.requests.append((media_types, roles))
        return "request-text"

    def poll_selection(self, request_id):
        return self.reply

    def import_selected(self, token):
        return self.transfer

    def publish_private_file(self, name, *, media_type, role, title=""):
        self.published.append((name, media_type, role, title))
        return {"ok": True}


class FakeAudio:
    def __init__(self):
        self.played = []

    def play(self, sound_id):
        self.played.append(sound_id)


class PostaStorageCreationTests(unittest.TestCase):
    def card(self, card_id="card-100-000001", text="Ciao Leo"):
        return SavedPostcard(card_id, 100, "leo", "heart", text)

    def test_saved_card_has_durable_private_utf8_source(self):
        storage = MemoryStorage()
        repo = GreiaPostcardStorage(storage)
        card = self.card(text="Ciao 👩🏽‍🔬")
        self.assertTrue(repo.save(PostcardLibrary([card])))
        name = repo.private_card_text_name(card.card_id)
        self.assertEqual(storage.files[name], card.text.encode("utf-8"))

    def test_index_failure_rolls_back_new_card_source(self):
        storage = MemoryStorage()
        repo = GreiaPostcardStorage(storage)
        existing = self.card()
        self.assertTrue(repo.save(PostcardLibrary([existing])))
        before_files = dict(storage.files)
        before_index = storage.value

        added = self.card("card-101-000002", "Nuova")
        storage.fail_set = True
        self.assertFalse(repo.save(PostcardLibrary([added, existing])))
        storage.fail_set = False

        self.assertEqual(storage.value, before_index)
        self.assertEqual(storage.files, before_files)

    def test_successful_delete_reclaims_text_only_after_index_commit(self):
        storage = MemoryStorage()
        repo = GreiaPostcardStorage(storage)
        first = self.card("card-100-000001", "Uno")
        second = self.card("card-101-000002", "Due")
        self.assertTrue(repo.save(PostcardLibrary([second, first])))
        first_name = repo._text_name(first.card_id)
        second_name = repo._text_name(second.card_id)
        self.assertTrue(repo.save(PostcardLibrary([second])))
        self.assertNotIn(first_name, storage.files)
        self.assertIn(second_name, storage.files)

    def test_unreadable_index_refuses_mutation(self):
        storage = MemoryStorage()
        repo = GreiaPostcardStorage(storage)
        storage.fail_get = True
        self.assertFalse(repo.save(PostcardLibrary([self.card()])))
        self.assertEqual(storage.files, {})


class PostaCreationFlowTests(unittest.TestCase):
    def make_app(self):
        storage_backend = MemoryStorage()
        storage = GreiaPostcardStorage(storage_backend)
        draft = PostcardDraft(recipient_id="leo", stamp_id="heart")
        app = object.__new__(PostcardActivity)
        app.draft = draft
        app.library = PostcardLibrary()
        app.storage = storage
        app.creations = FakeCreations()
        app.audio = FakeAudio()
        app.clock = lambda: 10.0
        app.shared_request = None
        app.shared_next_poll = 0.0
        app.shared_state = ""
        app.shared_feedback_until = 0.0
        app._shared_card_ids = set()
        app._cursor_visible = True
        app._last_blink = 0.0
        app.rng = random.Random(1)
        return app, storage_backend

    def test_picker_scopes_plain_text_to_document_and_postcard(self):
        app, _ = self.make_app()
        app._request_shared_text()
        self.assertEqual(
            app.creations.requests,
            [(("text/plain",), ("document", "postcard"))],
        )

    def test_document_import_compacts_and_grapheme_truncates_into_draft(self):
        app, _ = self.make_app()
        text = ("Ciao\n\tLeo   " + "👩🏽‍🔬" * (MAX_GRAPHEMES + 20))
        payload = text.encode("utf-8")
        app.creations.transfer = CreationTransfer(
            {
                "media_type": "text/plain",
                "role": "document",
                "sha256": hashlib.sha256(payload).hexdigest(),
            },
            payload,
        )
        self.assertTrue(app._accept_shared_text("one-use"))
        self.assertNotIn("\n", app.draft.text)
        self.assertNotIn("\t", app.draft.text)
        self.assertLessEqual(len(grapheme_spans(app.draft.text)), MAX_GRAPHEMES)
        self.assertFalse(app.draft.text.endswith("👩🏽‍"))

    def test_import_failure_preserves_existing_draft(self):
        app, _ = self.make_app()
        app.draft.replace_text("Keep me")
        payload = b"bad"
        app.creations.transfer = CreationTransfer(
            {
                "media_type": "text/plain",
                "role": "caption",
                "sha256": hashlib.sha256(payload).hexdigest(),
            },
            payload,
        )
        self.assertFalse(app._accept_shared_text("bad"))
        self.assertEqual(app.draft.text, "Keep me")

    def test_only_saved_postcard_is_published_and_share_is_deduplicated(self):
        app, storage_backend = self.make_app()
        card = SavedPostcard(
            "card-100-000001",
            100,
            "leo",
            "heart",
            "Messaggio salvato",
        )
        app.library = PostcardLibrary([card])
        self.assertTrue(app.storage.save(app.library))
        app._publish_saved_postcard(card)
        app._publish_saved_postcard(card)
        self.assertEqual(len(app.creations.published), 1)
        name, media_type, role, _title = app.creations.published[0]
        self.assertEqual(media_type, "text/plain")
        self.assertEqual(role, "postcard")
        self.assertEqual(
            storage_backend.files[name],
            card.text.encode("utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
