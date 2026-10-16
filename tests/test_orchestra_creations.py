"""Orchestra trusted backing-track import/play-along contracts (``PlayAlong``).

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

from activities.orchestra_animali.orchestra_audio import (
    BackingTrackPlayer,
    ImportedBackingTrack,
)
from activities.orchestra_animali.orchestra_backing import BackingTrackRecord
from activities.orchestra_animali.orchestra_playalong import PlayAlong


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
    def make_flow(self):
        self.events = []
        return PlayAlong(
            creations=FakeCreations(),
            store=FakeStore(),
            player=FakePlayer(),
            on_concert=lambda live: self.events.append(("concert.performed", {"live_inputs": live})),
        )

    def test_import_request_is_unavailable_without_trusted_store(self):
        flow = self.make_flow()
        flow.store = None
        flow.request(10.0)
        self.assertEqual(flow.creations.requests, [])
        self.assertIsNone(flow.request_id)

    def test_picker_is_wav_and_semantically_scoped(self):
        flow = self.make_flow()
        flow.player.track = object()
        flow.request(10.0)
        self.assertEqual(
            flow.creations.requests,
            [(("audio/wav",), ("narration", "song", "music"))],
        )
        self.assertEqual(flow.request_id, "request-backing")
        self.assertGreaterEqual(flow.next_poll, 10.12)
        self.assertEqual(flow.player.stops, 1)

    def test_valid_selection_persists_before_active_track_changes(self):
        flow = self.make_flow()
        old_track = object()
        flow.player.track = old_track
        payload = _wav(1.0)
        flow.creations.transfer = CreationTransfer(
            {
                "media_type": "audio/wav",
                "role": "narration",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "title": "My voice",
            },
            payload,
        )
        self.assertTrue(flow.accept("one-use"))
        self.assertEqual(len(flow.store.saved), 1)
        self.assertIsInstance(flow.player.track, ImportedBackingTrack)
        self.assertEqual(flow.record.role, "narration")

    def test_ready_poll_imports_and_shows_brief_feedback(self):
        flow = self.make_flow()
        payload = _wav(0.5)
        flow.creations.transfer = CreationTransfer(
            {"media_type": "audio/wav", "role": "song", "sha256": hashlib.sha256(payload).hexdigest()},
            payload,
        )
        flow.request(1.0)
        flow.creations.reply = SimpleNamespace(state="ready", selection_token="tok")
        self.assertTrue(flow.poll(2.0))
        self.assertEqual(flow.import_state, "imported")
        self.assertIsNone(flow.request_id)
        self.assertTrue(flow.update(5.0))
        self.assertEqual(flow.import_state, "")

    def test_failed_persistence_preserves_previous_track(self):
        flow = self.make_flow()
        old_track = object()
        flow.player.track = old_track
        flow.store.fail = True
        payload = _wav(1.0)
        flow.creations.transfer = CreationTransfer(
            {
                "media_type": "audio/wav",
                "role": "music",
                "sha256": hashlib.sha256(payload).hexdigest(),
            },
            payload,
        )
        self.assertFalse(flow.accept("one-use"))
        self.assertIs(flow.player.track, old_track)
        self.assertEqual(flow.player.loaded, [])

    def test_wrong_role_or_digest_preserves_previous_track(self):
        flow = self.make_flow()
        old_track = object()
        flow.player.track = old_track
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
            flow.creations.transfer = CreationTransfer(record, payload)
            self.assertFalse(flow.accept("bad"))
            self.assertIs(flow.player.track, old_track)

    def test_completed_backing_emits_concert_only_after_live_input(self):
        flow = self.make_flow()
        flow.player.refresh_result = True
        flow.notes_played = 3
        flow.update(1.0)
        self.assertEqual(self.events, [("concert.performed", {"live_inputs": 3})])
        self.assertEqual(flow.notes_played, 0)

    def test_completed_backing_without_live_input_is_not_a_concert(self):
        flow = self.make_flow()
        flow.player.refresh_result = True
        flow.notes_played = 0
        flow.update(1.0)
        self.assertEqual(self.events, [])

    def test_notes_count_only_while_the_track_plays(self):
        flow = self.make_flow()
        flow.player.state = "ready"
        flow.note_played()
        flow.player.state = "playing"
        flow.note_played()
        self.assertEqual(flow.notes_played, 1)


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
