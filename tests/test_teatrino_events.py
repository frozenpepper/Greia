"""Teatrino declared telemetry follows real saved shows only."""
from __future__ import annotations

import unittest

from teatrino_doubles import advance, make_app, record_show


class TeatrinoEventContractTests(unittest.TestCase):
    def test_saving_a_show_emits_story_recorded_once_with_its_id(self):
        events: list = []
        app = make_app(events=events)
        meta = record_show(app, 1.0)
        recorded = [kwargs for event, kwargs in events if event == "story.recorded"]
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["payload"]["id"], meta["id"])
        self.assertIn(meta["id"], recorded[0]["idempotency_key"])

    def test_watching_a_saved_show_to_the_end_emits_story_played(self):
        events: list = []
        app = make_app(events=events)
        meta = record_show(app, 1.0)
        app.library.open()
        app.tap(app.library.controls.cards[0].rect.center)
        advance(app, 3.0)
        played = [kwargs for event, kwargs in events if event == "story.played"]
        self.assertEqual(len(played), 1)
        self.assertEqual(played[0]["payload"], {"id": meta["id"]})
        self.assertIn(meta["id"], played[0]["idempotency_key"])

    def test_stopping_a_show_early_or_playing_with_puppets_claims_nothing(self):
        events: list = []
        app = make_app(events=events)
        record_show(app, 1.0)
        app._close_sheets()
        app.tap(app.controls.fx[1].rect.center)  # free play: no event
        app.library.open()
        app.tap(app.library.controls.cards[0].rect.center)
        advance(app, 0.5)
        app.tap(app.layout.rec.center)  # stop watching early
        advance(app, 3.0)
        self.assertEqual([event for event, _ in events], ["story.recorded"])


if __name__ == "__main__":
    unittest.main()
