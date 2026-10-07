"""Teatrino declared completion telemetry follows real saved-show playback."""
from __future__ import annotations

import unittest
from unittest import mock

from activities.teatrino_fiabe.teatrino_app import TeatrinoApp


class TeatrinoEventContractTests(unittest.TestCase):
    def test_saved_show_completion_emits_declared_story_played(self):
        app = object.__new__(TeatrinoApp)
        app.playback_show_meta = {"id": "show-123"}
        app.play_start_time = 12.345
        with mock.patch(
            "activities.teatrino_fiabe.teatrino_app.emit_activity_event"
        ) as emit:
            app._emit_saved_story_played()
        emit.assert_called_once()
        args = emit.call_args
        self.assertEqual(args.args[0], "story.played")
        self.assertEqual(args.kwargs["payload"], {"id": "show-123"})
        self.assertIn("show-123", args.kwargs["idempotency_key"])

    def test_free_stage_play_has_no_false_saved_story_completion(self):
        app = object.__new__(TeatrinoApp)
        app.playback_show_meta = None
        app.play_start_time = 99.0
        with mock.patch(
            "activities.teatrino_fiabe.teatrino_app.emit_activity_event"
        ) as emit:
            app._emit_saved_story_played()
        emit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
