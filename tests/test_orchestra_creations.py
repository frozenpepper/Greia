"""Orchestra trusted backing-track import/play-along contracts.

Execution is intentionally deferred to the accumulated desktop acceptance.
"""
from __future__ import annotations

import hashlib
import io
import struct
import unittest
import wave
from types import SimpleNamespace
from unittest import mock

import pygame

from greia_platform.creation_client import CreationTransfer

from activities.orchestra_animali.orchestra_app import OrchestraApp
from activities.orchestra_animali.orchestra_audio import (
    BackingTrackPlayer,
    ImportedBackingTrack,
)
from activities.orchestra_animali.orchestra_backing import BackingTrackRecord


def _wav(seconds: float, *, rate: int = 8000) -> bytes:
    frames = max(1, int(round(seconds * rate)))
    pcm = struct.pack("<" + "h" * frames, *([300] * frames))
    out = io.BytesIO()
    with wave.open(out, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(rate)
        target.writeframes(pcm)
    return out.getvalue()


class FakeCreations:
    def __init__(self):
        self.requests = []
        self.reply = SimpleNamespace(state="pending", selection_token=None)
        self.transfer = None

    def request_selection(self, *, media_types, roles=()):
        self.requests.append((media_types, roles))
        return "request-backing"

    def poll_selection(self, request_id):
        return self.reply

    def import_selected(self, token):
        return self.transfer


class FakeStore:
    def __init__(self):
        self.saved = []
        self.fail = False

    def save(self, payload, *, role, title, duration_seconds):
        if self.fail:
            raise RuntimeError("save failed")
        record = BackingTrackRecord(
            hashlib.sha256(payload).hexdigest(),
            role,
            title,
            duration_seconds,
        )
        self.saved.append((payload, role, title, duration_seconds))
        return record


class FakePlayer:
    def __init__(self):
        self.track = None
        self.state = "ready"
        self.stops = 0
        self.loaded = []
        self.refresh_result = False

    def stop(self):
        self.stops += 1
        if self.track is not None:
            self.state = "ready"

    def load(self, track):
        self.track = track
        self.loaded.append(track)
        self.state = "ready"

    def toggle(self):
        self.state = "playing" if self.state != "playing" else "paused"
        return self.state

    def refresh(self):
        result = self.refresh_result
        self.refresh_result = False
        return result


class FakeChannel:
    def __init__(self):
        self.busy = True
        self.paused = False
        self.plays = []
        self.stops = 0

    def play(self, sound):
        self.plays.append(sound)

    def get_busy(self):
        return self.busy

    def pause(self):
        self.paused = True

    def unpause(self):
        self.paused = False

    def stop(self):
        self.stops += 1
        self.busy = False


class OrchestraBackingFlowTests(unittest.TestCase):
    def make_app(self):
        app = object.__new__(OrchestraApp)
        app.creations = FakeCreations()
        app.backing_store = FakeStore()
        app.backing_player = FakePlayer()
        app.backing_record = None
        app.backing_request = None
        app.backing_next_poll = 0.0
        app.backing_import_state = ""
        app.backing_feedback_until = 0.0
        app.backing_notes_played = 0
        app.instruments = []
        app.key_highlight_timers = [0.0] * 8
        app.particles = []
        return app

    def test_import_request_is_unavailable_without_trusted_store(self):
        app = self.make_app()
        app.backing_store = None
        app._request_backing_track()
        self.assertEqual(app.creations.requests, [])
        self.assertIsNone(app.backing_request)

    def test_picker_is_wav_and_semantically_scoped(self):
        app = self.make_app()
        app.backing_player.track = object()
        with mock.patch(
            "activities.orchestra_animali.orchestra_app.time.monotonic",
            return_value=10.0,
        ):
            app._request_backing_track()
        self.assertEqual(
            app.creations.requests,
            [(("audio/wav",), ("narration", "song", "music"))],
        )
        self.assertEqual(app.backing_request, "request-backing")
        self.assertGreaterEqual(app.backing_next_poll, 10.12)
        self.assertEqual(app.backing_player.stops, 1)

    def test_valid_selection_persists_before_active_track_changes(self):
        app = self.make_app()
        old_track = object()
        app.backing_player.track = old_track
        payload = _wav(1.0)
        app.creations.transfer = CreationTransfer(
            {
                "media_type": "audio/wav",
                "role": "narration",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "title": "My voice",
            },
            payload,
        )
        self.assertTrue(app._accept_backing_track("one-use"))
        self.assertEqual(len(app.backing_store.saved), 1)
        self.assertIsInstance(app.backing_player.track, ImportedBackingTrack)
        self.assertEqual(app.backing_record.role, "narration")

    def test_failed_persistence_preserves_previous_track(self):
        app = self.make_app()
        old_track = object()
        app.backing_player.track = old_track
        app.backing_store.fail = True
        payload = _wav(1.0)
        app.creations.transfer = CreationTransfer(
            {
                "media_type": "audio/wav",
                "role": "music",
                "sha256": hashlib.sha256(payload).hexdigest(),
            },
            payload,
        )
        self.assertFalse(app._accept_backing_track("one-use"))
        self.assertIs(app.backing_player.track, old_track)
        self.assertEqual(app.backing_player.loaded, [])

    def test_wrong_role_or_digest_preserves_previous_track(self):
        app = self.make_app()
        old_track = object()
        app.backing_player.track = old_track
        payload = _wav(1.0)
        for record in (
            {
                "media_type": "audio/wav",
                "role": "sound-effect",
                "sha256": hashlib.sha256(payload).hexdigest(),
            },
            {
                "media_type": "audio/wav",
                "role": "narration",
                "sha256": "bad",
            },
        ):
            app.creations.transfer = CreationTransfer(record, payload)
            self.assertFalse(app._accept_backing_track("bad"))
            self.assertIs(app.backing_player.track, old_track)

    def test_completed_backing_emits_concert_only_after_live_input(self):
        app = self.make_app()
        events = []
        app._safe_emit = lambda event_id, key, payload=None: events.append(
            (event_id, payload)
        )
        app.backing_player.refresh_result = True
        app.backing_notes_played = 3
        app._update_state()
        self.assertEqual(
            events,
            [("concert.performed", {"live_inputs": 3})],
        )
        self.assertEqual(app.backing_notes_played, 0)

    def test_completed_backing_without_live_input_is_not_a_concert(self):
        app = self.make_app()
        events = []
        app._safe_emit = lambda event_id, key, payload=None: events.append(
            (event_id, payload)
        )
        app.backing_player.refresh_result = True
        app.backing_notes_played = 0
        app._update_state()
        self.assertEqual(events, [])


class BackingTrackAudioTests(unittest.TestCase):
    def test_wav_is_canonical_and_duration_bounded(self):
        track = ImportedBackingTrack.from_wav(_wav(1.25))
        self.assertAlmostEqual(track.duration_seconds, 1.25, places=2)
        with self.assertRaises(ValueError):
            ImportedBackingTrack.from_wav(b"not-wave")

    def test_reserved_channel_pause_resume_and_natural_finish(self):
        track = ImportedBackingTrack.from_wav(_wav(0.25))
        player = BackingTrackPlayer()
        player.load(track)
        channel = FakeChannel()
        sound = object()
        with (
            mock.patch(
                "activities.orchestra_animali.orchestra_audio.pygame.mixer.get_init",
                return_value=(22050, -16, 1),
            ),
            mock.patch(
                "activities.orchestra_animali.orchestra_audio.pygame.mixer.set_reserved"
            ) as reserve,
            mock.patch(
                "activities.orchestra_animali.orchestra_audio.pygame.mixer.Channel",
                return_value=channel,
            ) as channel_ctor,
            mock.patch(
                "activities.orchestra_animali.orchestra_audio.pygame.mixer.Sound",
                return_value=sound,
            ),
        ):
            self.assertEqual(player.toggle(), "playing")
            reserve.assert_called_once_with(1)
            channel_ctor.assert_called_once_with(0)
            self.assertEqual(channel.plays, [sound])
            self.assertEqual(player.toggle(), "paused")
            self.assertTrue(channel.paused)
            self.assertEqual(player.toggle(), "playing")
            self.assertFalse(channel.paused)
            channel.busy = False
            self.assertTrue(player.refresh())
            self.assertEqual(player.state, "ready")


if __name__ == "__main__":
    unittest.main()
