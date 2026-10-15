"""Leo's Post trusted My Creations exchange (UTF-8 text with Writing, PNG fronts).

Headless (dummy SDL) source evidence; no hardware claim.
"""
from __future__ import annotations

import hashlib
import os
import random
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from greia_platform.creation_client import CreationTransfer
from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.pygame_png import encode_surface_png
from greia_platform.typography import GreiaTypography, grapheme_spans

from activities.posta_di_leo.postcard_app import PostcardActivity
from activities.posta_di_leo.postcard_audio import PostcardAudio
from activities.posta_di_leo.postcard_model import (
    MAX_GRAPHEMES,
    CardFront,
    PostcardDraft,
    PostcardLibrary,
    SavedPostcard,
)
from activities.posta_di_leo.postcard_services import GreiaPostcardStorage

ACTIVITY_ROOT = Path(__file__).resolve().parents[1] / "activities" / "posta_di_leo"


class MemoryStorage:
    def __init__(self):
        self.value = None
        self.kv = {}
        self.files = {}
        self.fail_get = False
        self.fail_set = False

    def kv_get(self, key, default=None):
        if self.fail_get:
            raise RuntimeError("read failed")
        if key == "posta_di_leo.library.v1":
            return self.value
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        if self.fail_set:
            raise RuntimeError("write failed")
        if key == "posta_di_leo.library.v1":
            self.value = value
        else:
            self.kv[key] = value

    def kv_delete(self, key):
        return self.kv.pop(key, None) is not None

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
        return "request-1"

    def poll_selection(self, request_id):
        return self.reply

    def import_selected(self, token):
        return self.transfer

    def publish_private_file(self, name, *, media_type, role, title=""):
        self.published.append((name, media_type, role, title))
        return {"ok": True}


def _png(size=(320, 200), color=(239, 77, 83)) -> bytes:
    surface = pygame.Surface(size)
    surface.fill(color)
    return encode_surface_png(surface)


def _transfer(payload: bytes, media_type: str, role: str, *, sha: str | None = None) -> CreationTransfer:
    return CreationTransfer(
        {"media_type": media_type, "role": role, "sha256": sha or hashlib.sha256(payload).hexdigest()},
        payload,
    )


class PostaCreationTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    def make_app(self, draft: PostcardDraft | None = None):
        backend = MemoryStorage()
        storage = GreiaPostcardStorage(backend)
        screen = pygame.display.set_mode((1024, 600))
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        now = [10.0]
        app = PostcardActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            typography=GreiaTypography(),
            resources=LocalizedResources(ACTIVITY_ROOT, resolve_activity_locale("it", support)),
            storage=storage,
            events=SimpleNamespace(postcard_created=lambda card: None),
            audio=PostcardAudio(locale="it"),
            rng=random.Random(1),
            creations=FakeCreations(),
            draft=draft,
            clock=lambda: now[0],
        )
        return app, backend, now


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
        storage.fail_set = True
        self.assertFalse(repo.save(PostcardLibrary([self.card("card-101-000002", "Nuova"), existing])))
        storage.fail_set = False
        self.assertEqual(storage.value, before_index)
        self.assertEqual(storage.files, before_files)

    def test_successful_delete_reclaims_text_only_after_index_commit(self):
        storage = MemoryStorage()
        repo = GreiaPostcardStorage(storage)
        first = self.card("card-100-000001", "Uno")
        second = self.card("card-101-000002", "Due")
        self.assertTrue(repo.save(PostcardLibrary([second, first])))
        self.assertTrue(repo.save(PostcardLibrary([second])))
        self.assertNotIn(repo._text_name(first.card_id), storage.files)
        self.assertIn(repo._text_name(second.card_id), storage.files)

    def test_unreadable_index_refuses_mutation(self):
        storage = MemoryStorage()
        repo = GreiaPostcardStorage(storage)
        storage.fail_get = True
        self.assertFalse(repo.save(PostcardLibrary([self.card()])))
        self.assertEqual(storage.files, {})


class PostaTextExchangeTests(PostaCreationTestBase):
    def test_picker_scopes_plain_text_to_document_and_postcard(self):
        app, _, _ = self.make_app()
        app._request_shared_text()
        self.assertEqual(app.creations.requests, [(("text/plain",), ("document", "postcard"))])

    def test_document_import_compacts_and_grapheme_truncates_into_draft(self):
        app, _, _ = self.make_app()
        text = "Ciao\n\tLeo   " + "👩🏽‍🔬" * (MAX_GRAPHEMES + 20)
        app.creations.transfer = _transfer(text.encode("utf-8"), "text/plain", "document")
        self.assertTrue(app._accept_shared_text("one-use"))
        self.assertNotIn("\n", app.draft.text)
        self.assertNotIn("\t", app.draft.text)
        self.assertLessEqual(len(grapheme_spans(app.draft.text)), MAX_GRAPHEMES)
        self.assertFalse(app.draft.text.endswith("👩🏽‍"))

    def test_import_failure_preserves_existing_draft(self):
        app, _, _ = self.make_app()
        app.draft.replace_text("Keep me")
        app.creations.transfer = _transfer(b"bad", "text/plain", "caption")
        self.assertFalse(app._accept_shared_text("bad"))
        self.assertEqual(app.draft.text, "Keep me")

    def test_picker_round_trip_brings_a_writing_page_into_the_message(self):
        app, _, now = self.make_app(PostcardDraft(recipient_id="lilli", front=CardFront.scene("rainbow")))
        app._go_step("message")
        app._request_shared_text()
        self.assertEqual(app.shared_state, "pending")
        app.creations.transfer = _transfer("Una pagina di Writing".encode("utf-8"), "text/plain", "document")
        app.creations.reply = SimpleNamespace(state="ready", selection_token="tok")
        now[0] += 0.5
        app.step_frame()
        self.assertEqual(app.draft.text, "Una pagina di Writing")
        self.assertIsNone(app.shared_request)

    def test_saved_postcard_shares_picture_and_text_once(self):
        app, backend, _ = self.make_app()
        card = SavedPostcard("card-100-000001", 100, "leo", "heart", "Messaggio salvato", CardFront.scene("castle"))
        app.library = PostcardLibrary([card])
        self.assertTrue(app.storage.save(app.library))
        app._publish_saved_postcard(card)
        app._publish_saved_postcard(card)
        published = app.creations.published
        self.assertEqual([(m, r) for _n, m, r, _t in published], [("image/png", "postcard"), ("text/plain", "postcard")])
        png_name, text_name = published[0][0], published[1][0]
        self.assertTrue(backend.files[png_name].startswith(b"\x89PNG"))
        # Writing imports this exact UTF-8 text (role "postcard").
        self.assertEqual(backend.files[text_name], card.text.encode("utf-8"))

    def test_picture_only_card_shares_just_the_picture(self):
        app, _, _ = self.make_app()
        card = SavedPostcard("card-100-000002", 100, "momo", "heart", "", CardFront.scene("candy"))
        app.library = PostcardLibrary([card])
        self.assertTrue(app.storage.save(app.library))
        app._publish_saved_postcard(card)
        self.assertEqual([m for _n, m, _r, _t in app.creations.published], ["image/png"])


class PostaPictureFrontTests(PostaCreationTestBase):
    def test_picker_scopes_pictures_to_creative_roles(self):
        app, _, _ = self.make_app()
        app._request_shared_picture()
        self.assertEqual(
            app.creations.requests, [(("image/png",), ("drawing", "composition", "picture", "postcard"))]
        )

    def test_painting_drawing_becomes_the_card_front_and_is_sent_with_it(self):
        app, backend, now = self.make_app(PostcardDraft(recipient_id="flash"))
        app.creations.transfer = _transfer(_png(), "image/png", "drawing")
        self.assertTrue(app._accept_shared_picture("tok"))
        self.assertEqual(app.draft.front, CardFront.picture())
        self.assertTrue(app.draft.ready)
        app._on_send()
        card = app.library.cards[0]
        stored = backend.files[f"postcards/{card.card_id}.front.png"]
        self.assertTrue(stored.startswith(b"\x89PNG"))
        # Reopening the postbox decodes the child's own picture again.
        app._pictures.clear()
        self.assertIsNotNone(app._card_picture(card))

    def test_bad_pictures_never_replace_the_front(self):
        app, _, _ = self.make_app(PostcardDraft(recipient_id="tito", front=CardFront.scene("forest")))
        for transfer in (
            _transfer(b"not a png", "image/png", "drawing"),
            _transfer(_png(), "image/png", "selfie"),
            _transfer(_png(), "image/png", "drawing", sha="0" * 64),
            _transfer(_png(), "text/plain", "drawing"),
        ):
            app.creations.transfer = transfer
            self.assertFalse(app._accept_shared_picture("tok"))
            self.assertEqual(app.draft.front, CardFront.scene("forest"))


if __name__ == "__main__":
    unittest.main()
