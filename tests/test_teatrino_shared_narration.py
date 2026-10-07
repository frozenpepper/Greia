"""Teatrino shared narration picker and no-microphone performance flow."""
from __future__ import annotations

import hashlib
import unittest
from types import SimpleNamespace
from unittest import mock

from greia_platform.creation_client import CreationTransfer

from activities.teatrino_fiabe.teatrino_app import TeatrinoApp


class FakeCreations:
    def __init__(self):
        self.requests = []
        self.polls = []
        self.reply = SimpleNamespace(state="pending", selection_token=None)
        self.transfer = None

    def request_selection(self, *, media_types, roles=()):
        self.requests.append((media_types, roles))
        return "request-audio"

    def poll_selection(self, request_id):
        self.polls.append(request_id)
        return self.reply

    def import_selected(self, token):
        return self.transfer


class FakeChannel:
    def __init__(self):
        self.stops = 0

    def stop(self):
        self.stops += 1


class FakeTrack:
    def __init__(self, duration=3.0):
        self.duration_seconds = duration
        self.sound = object()
        self.channel = FakeChannel()
        self.trim_calls = []

    def play(self):
        return self.sound, self.channel

    def trimmed(self, seconds):
        self.trim_calls.append(seconds)
        return b"trimmed-narration"


class FakeMic:
    def __init__(self):
        self.enabled = True
        self.current_volume = 0.0
        self.started = 0
        self.stopped = 0

    def start_recording(self):
        self.started += 1

    def stop_recording(self):
        self.stopped += 1
        return b"microphone-wav"


class FakeSound:
    def __init__(self):
        self.played = []

    def play(self, sound_id):
        self.played.append(sound_id)


class TeatrinoNarrationFlowTests(unittest.TestCase):
    def make_app(self):
        app = object.__new__(TeatrinoApp)
        app.creations = FakeCreations()
        app.app_mode = "stage"
        app.is_recording = False
        app.backdrop_import_request = None
        app.narration_import_request = None
        app.narration_import_next_poll = 0.0
        app.narration_import_state = ""
        app.narration_import_feedback_until = 0.0
        app.imported_narration = None
        app.recording_narration_track = None
        app.recording_narration_sound = None
        app.recording_narration_channel = None
        app.recorded_frames = []
        app.recorded_sfx = []
        app.rec_start_time = 0.0
        app.last_recorded_wav = None
        app.feedback_text = ""
        app.feedback_timer = 0.0
        app.ui_strings = {}
        app.mic_recorder = FakeMic()
        app.sound_mgr = FakeSound()
        app.active_bg_idx = 0
        app.puppets_on_stage = []
        return app

    def test_picker_is_wav_and_narration_role_only(self):
        app = self.make_app()
        with mock.patch(
            "activities.teatrino_fiabe.teatrino_app.time.monotonic",
            return_value=10.0,
        ):
            app._request_shared_narration()
        self.assertEqual(
            app.creations.requests,
            [(("audio/wav",), ("narration",))],
        )
        self.assertEqual(app.narration_import_request, "request-audio")
        self.assertGreaterEqual(app.narration_import_next_poll, 10.12)

    def test_audio_request_does_not_compete_with_pending_backdrop_picker(self):
        app = self.make_app()
        app.backdrop_import_request = "image-request"
        app._request_shared_narration()
        self.assertEqual(app.creations.requests, [])
        self.assertIsNone(app.narration_import_request)

    def test_cancel_keeps_existing_narration(self):
        app = self.make_app()
        existing = FakeTrack()
        app.imported_narration = existing
        app.narration_import_request = "request-audio"
        app.creations.reply = SimpleNamespace(
            state="cancelled",
            selection_token=None,
        )
        app._poll_shared_narration(20.0)
        self.assertIs(app.imported_narration, existing)
        self.assertIsNone(app.narration_import_request)

    def test_ready_selection_requires_audio_narration_digest(self):
        app = self.make_app()
        payload = b"canonical-wave"
        app.creations.transfer = CreationTransfer(
            {
                "media_type": "audio/wav",
                "role": "narration",
                "sha256": hashlib.sha256(payload).hexdigest(),
            },
            payload,
        )
        selected = FakeTrack(duration=2.0)
        with mock.patch(
            "activities.teatrino_fiabe.teatrino_app.ImportedNarrationTrack.from_wav",
            return_value=selected,
        ) as prepare:
            self.assertTrue(app._accept_shared_narration("one-use"))
        self.assertIs(app.imported_narration, selected)
        prepare.assert_called_once()

        app.creations.transfer = CreationTransfer(
            {
                "media_type": "audio/wav",
                "role": "sound-effect",
                "sha256": hashlib.sha256(payload).hexdigest(),
            },
            payload,
        )
        self.assertFalse(app._accept_shared_narration("wrong-role"))
        self.assertIs(app.imported_narration, selected)

    def test_recording_with_imported_narration_never_opens_microphone(self):
        app = self.make_app()
        track = FakeTrack(duration=3.0)
        app.imported_narration = track
        with mock.patch(
            "activities.teatrino_fiabe.teatrino_app.time.time",
            return_value=100.0,
        ):
            self.assertTrue(app._start_recording())
        self.assertTrue(app.is_recording)
        self.assertIs(app.recording_narration_track, track)
        self.assertEqual(app.mic_recorder.started, 0)
        self.assertIs(app.recording_narration_channel, track.channel)

    def test_early_stop_trims_imported_narration_and_persists_that_copy(self):
        app = self.make_app()
        track = FakeTrack(duration=3.0)
        app.imported_narration = track
        app._start_recording()
        app._persist_recorded_show = mock.Mock(return_value={"id": "show-1"})
        result = app._finish_recording(
            1.25,
            feedback_seconds=2.0,
        )
        self.assertEqual(result, {"id": "show-1"})
        self.assertEqual(track.trim_calls, [1.25])
        self.assertEqual(track.channel.stops, 1)
        self.assertEqual(app.last_recorded_wav, b"trimmed-narration")
        self.assertEqual(app.mic_recorder.stopped, 0)
        args = app._persist_recorded_show.call_args.args
        self.assertEqual(args[2], b"trimmed-narration")

    def test_microphone_recording_path_remains_unchanged_without_import(self):
        app = self.make_app()
        app._persist_recorded_show = mock.Mock(return_value={"id": "show-2"})
        self.assertTrue(app._start_recording())
        self.assertEqual(app.mic_recorder.started, 1)
        result = app._finish_recording(
            1.0,
            feedback_seconds=2.0,
        )
        self.assertEqual(result, {"id": "show-2"})
        self.assertEqual(app.mic_recorder.stopped, 1)
        self.assertEqual(app.last_recorded_wav, b"microphone-wav")


if __name__ == "__main__":
    unittest.main()
