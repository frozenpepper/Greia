"""Imported Theatre narration WAV validation and trimming."""
from __future__ import annotations

import io
import struct
import unittest
import wave

from activities.teatrino_fiabe.teatrino_audio import ImportedNarrationTrack


def _wav(seconds: float, *, rate: int = 8000) -> bytes:
    frames = max(1, int(round(seconds * rate)))
    pcm = struct.pack("<" + "h" * frames, *([500] * frames))
    out = io.BytesIO()
    with wave.open(out, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(rate)
        target.writeframes(pcm)
    return out.getvalue()


class ImportedNarrationTrackTests(unittest.TestCase):
    def test_valid_wav_is_canonical_and_reports_duration(self):
        track = ImportedNarrationTrack.from_wav(
            _wav(1.25),
            max_duration_seconds=2.0,
        )
        self.assertAlmostEqual(track.duration_seconds, 1.25, places=2)
        with wave.open(io.BytesIO(track.wav_bytes), "rb") as source:
            self.assertEqual(source.getnchannels(), 1)
            self.assertEqual(source.getframerate(), 8000)
            self.assertEqual(source.getsampwidth(), 2)

    def test_duration_bound_rejects_longer_shared_audio(self):
        with self.assertRaises(ValueError):
            ImportedNarrationTrack.from_wav(
                _wav(2.5),
                max_duration_seconds=2.0,
            )

    def test_invalid_wav_fails_closed(self):
        with self.assertRaises(ValueError):
            ImportedNarrationTrack.from_wav(
                b"not-a-wave",
                max_duration_seconds=2.0,
            )

    def test_early_stop_trim_keeps_valid_pcm_prefix(self):
        track = ImportedNarrationTrack.from_wav(
            _wav(1.0),
            max_duration_seconds=2.0,
        )
        trimmed = track.trimmed(0.25)
        with wave.open(io.BytesIO(trimmed), "rb") as source:
            self.assertEqual(source.getframerate(), 8000)
            self.assertEqual(source.getnframes(), 2000)

    def test_loudness_envelope_drives_lip_sync_and_is_bounded(self):
        track = ImportedNarrationTrack.from_wav(_wav(1.0), max_duration_seconds=2.0)
        self.assertGreater(track.level_at(0.5), 0.0)
        self.assertEqual(track.level_at(5.0), 0.0)
        self.assertLessEqual(len(track.envelope), 45 * 15 + 2)

    def test_full_duration_trim_reuses_canonical_payload(self):
        track = ImportedNarrationTrack.from_wav(
            _wav(0.5),
            max_duration_seconds=2.0,
        )
        self.assertIs(track.trimmed(0.5), track.wav_bytes)


if __name__ == "__main__":
    unittest.main()
