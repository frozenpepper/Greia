"""Teatrino shared narration picker (P5) and the no-microphone performance flow."""
from __future__ import annotations

import hashlib
from types import SimpleNamespace
import unittest
from unittest import mock

from teatrino_doubles import FakeCreations, advance, make_app

from greia_platform.creation_client import CreationTransfer


class FakeChannel:
    def __init__(self):
        self.stops = 0

    def stop(self):
        self.stops += 1


class FakeTrack:
    def __init__(self, duration=3.0):
        self.duration_seconds = duration
        self.channel = FakeChannel()
        self.trim_calls = []

    def play(self):
        return object(), self.channel

    def trimmed(self, seconds):
        self.trim_calls.append(seconds)
        return b"trimmed-narration"

    def level_at(self, seconds):
        return 0.5


def _choose_saved_voice(app):
    app.tap(app.layout.mic.center)
    app.tap(app.surfaces.overlays[-1].layer.target("voice.imported").rect.center)


class TeatrinoNarrationFlowTests(unittest.TestCase):
    def test_picker_is_wav_and_narration_role_only(self):
        creations = FakeCreations()
        app = make_app(creations=creations)
        _choose_saved_voice(app)
        self.assertEqual(creations.requests, [(("audio/wav",), ("narration",))])
        self.assertEqual(app.top_sheet, "", "the voice sheet closes while the platform picker is up")

    def test_audio_request_does_not_compete_with_pending_picture_picker(self):
        creations = FakeCreations()
        app = make_app(creations=creations)
        self.assertTrue(app.bridge.request_backdrop())
        self.assertFalse(app.bridge.request_narration())
        self.assertEqual(len(creations.requests), 1)

    def test_cancel_keeps_existing_narration(self):
        creations = FakeCreations()
        app = make_app(creations=creations)
        existing = FakeTrack()
        app.voice.use_narration(existing)
        _choose_saved_voice(app)
        creations.reply = SimpleNamespace(state="cancelled", selection_token=None)
        app.clock.now += 0.2
        app.step()
        self.assertIs(app.imported_narration, existing)
        self.assertFalse(app.bridge.busy)

    def test_ready_selection_requires_audio_narration_digest(self):
        creations = FakeCreations()
        app = make_app(creations=creations)
        payload = b"canonical-wave"
        record = {"media_type": "audio/wav", "role": "narration", "sha256": hashlib.sha256(payload).hexdigest()}
        creations.transfer = CreationTransfer(record, payload)
        selected = FakeTrack(duration=2.0)
        with mock.patch(
            "activities.teatrino_fiabe.teatrino_creations.ImportedNarrationTrack.from_wav", return_value=selected
        ) as prepare:
            self.assertTrue(app.bridge.accept_narration("one-use"))
        self.assertIs(app.imported_narration, selected)
        prepare.assert_called_once()
        self.assertEqual(app.voice.state, "imported")
        creations.transfer = CreationTransfer({**record, "role": "sound-effect"}, payload)
        self.assertFalse(app.bridge.accept_narration("wrong-role"))
        self.assertIs(app.imported_narration, selected)

    def test_recording_with_imported_narration_never_opens_microphone(self):
        app = make_app()
        track = FakeTrack(duration=3.0)
        app.voice.use_narration(track)
        app.tap(app.layout.rec.center)
        advance(app, 3.0)
        self.assertTrue(app.is_recording)
        self.assertEqual(app.mic_recorder.started, 0)
        self.assertEqual(app.voice.limit, 3.0, "the show lasts as long as the chosen voice")

    def test_early_stop_trims_imported_narration_and_persists_that_copy(self):
        app = make_app()
        track = FakeTrack(duration=10.0)
        app.voice.use_narration(track)
        app.tap(app.layout.rec.center)
        advance(app, 3.0)
        advance(app, 1.0)
        performed = app.clock.now - app.rec_started
        app.tap(app.layout.rec.center)
        self.assertEqual(len(track.trim_calls), 1)
        self.assertAlmostEqual(track.trim_calls[0], performed, delta=0.01)
        self.assertLess(performed, 10.0)
        self.assertEqual(track.channel.stops, 1)
        self.assertEqual(app.last_recorded_wav, b"trimmed-narration")
        self.assertEqual(app.mic_recorder.stopped, 0)
        _data, wav = app.show_repo.load_show(app.saved_meta["id"])
        self.assertEqual(wav, b"trimmed-narration")

    def test_a_narration_that_ends_ends_the_show(self):
        app = make_app()
        app.voice.use_narration(FakeTrack(duration=1.0))
        app.tap(app.layout.rec.center)
        advance(app, 3.0)
        advance(app, 1.5)
        self.assertFalse(app.is_recording)
        self.assertIsNotNone(app.saved_meta)

    def test_microphone_recording_path_without_import(self):
        app = make_app()
        app.tap(app.layout.rec.center)
        advance(app, 3.0)
        self.assertEqual(app.mic_recorder.started, 1)
        advance(app, 1.0)
        app.tap(app.layout.rec.center)
        self.assertEqual(app.mic_recorder.stopped, 1)
        self.assertTrue(app.last_recorded_wav.startswith(b"RIFF"))


if __name__ == "__main__":
    unittest.main()
