"""Teatrino nonblocking shared-backdrop import (P4), poster share and truthful save state."""
from __future__ import annotations

import hashlib
from types import SimpleNamespace
import unittest
from unittest import mock

from teatrino_doubles import FakeCreations, MemoryStorage, make_app, record_show

from greia_platform.creation_client import CreationTransfer

from activities.teatrino_fiabe.teatrino_content import POSTER_FILE, POSTER_ROLE
from activities.teatrino_fiabe.teatrino_model import ShowStorageError


def _pick_my_picture(app):
    app.tap(app.layout.scene.center)
    mine = app.surfaces.overlays[-1].layer.target("scene.mine")
    app.tap(mine.rect.center)


class TeatrinoBackdropFlowTests(unittest.TestCase):
    def test_my_picture_card_asks_for_png_only_and_polls_politely(self):
        creations = FakeCreations()
        app = make_app(creations=creations)
        _pick_my_picture(app)
        self.assertEqual(creations.requests, [(("image/png",), ())])
        self.assertTrue(app.bridge.busy)
        app.clock.now += 0.05
        app.step()
        self.assertEqual(creations.polls, [], "no poll before the bounded interval")
        app.clock.now += 0.1
        app.step()
        self.assertEqual(len(creations.polls), 1)

    def test_cancel_preserves_the_current_scene(self):
        creations = FakeCreations()
        app = make_app(creations=creations)
        _pick_my_picture(app)
        creations.reply = SimpleNamespace(state="cancelled", selection_token=None)
        app.clock.now += 0.2
        app.step()
        self.assertIsNone(app.custom_backdrop_surface)
        self.assertFalse(app.bridge.busy)

    def test_ready_handle_validates_digest_before_replacing_backdrop(self):
        creations = FakeCreations()
        app = make_app(creations=creations)
        payload = b"new-picture"
        creations.transfer = CreationTransfer({"media_type": "image/png", "sha256": hashlib.sha256(payload).hexdigest()}, payload)
        surface = app.art.scene_backdrop("sky")
        with mock.patch("activities.teatrino_fiabe.teatrino_creations.decode_png_surface", return_value=surface):
            self.assertTrue(app.bridge.accept_backdrop("one-use"))
        self.assertEqual(app.custom_backdrop_png, payload)
        self.assertIs(app.custom_backdrop_surface, surface)
        meta = record_show(app, 1.0)
        self.assertTrue(meta["has_custom_backdrop"], "the show keeps its own copy of the picture")

    def test_integrity_failure_keeps_existing_backdrop(self):
        creations = FakeCreations()
        app = make_app(creations=creations)
        creations.transfer = CreationTransfer({"media_type": "image/png", "sha256": "bad"}, b"corrupt")
        self.assertFalse(app.bridge.accept_backdrop("bad-handle"))
        self.assertIsNone(app.custom_backdrop_png)

    def test_failed_show_save_is_pictorial_and_emits_no_creation_event(self):
        events: list = []
        storage = MemoryStorage()
        app = make_app(storage=storage, events=events)
        app.show_repo.save_show = mock.Mock(side_effect=ShowStorageError("disk"))
        self.assertIsNone(record_show(app, 1.0))
        self.assertEqual(events, [])
        self.assertTrue(app.save_error)
        self.assertIn("boing", app.sound_mgr.played)
        self.assertEqual(app.cast.pose.value, "think")
        self.assertEqual(app.top_sheet, "", "no curtain call for a show that was not saved")

    def test_share_publishes_the_poster_once_as_a_picture(self):
        creations = FakeCreations()
        storage = MemoryStorage()
        app = make_app(storage=storage, creations=creations)
        record_show(app, 1.0)
        share = app.surfaces.overlays[-1].layer.target("call.share")
        app.tap(share.rect.center)
        app.tap(share.rect.center)
        self.assertEqual(creations.published, [(POSTER_FILE, "image/png", POSTER_ROLE)])
        self.assertTrue(storage.files[POSTER_FILE].startswith(b"\x89PNG"))

    def test_no_creations_broker_means_no_share_or_picture_buttons(self):
        app = make_app(creations=None)
        record_show(app, 1.0)
        ids = {t.control_id for t in app.surfaces.overlays[-1].layer.targets}
        self.assertNotIn("call.share", ids)
        app._close_sheets()
        app.tap(app.layout.scene.center)
        ids = {t.control_id for t in app.surfaces.overlays[-1].layer.targets}
        self.assertNotIn("scene.mine", ids)


if __name__ == "__main__":
    unittest.main()
