"""Tests for tools/greia_audio_micro_extract.py."""

from __future__ import annotations

import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import wave

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.greia_audio_micro_extract import (
    check_ffmpeg_available,
    derive_speech_segments,
    detect_silence,
    probe_audio,
    run_extraction,
)


def create_synthetic_wav(
    path: Path,
    segments: list[tuple[float, bool]],  # (duration_seconds, is_tone)
    sample_rate: int = 24000,
    freq_hz: float = 440.0,
    amplitude: float = 0.5,
) -> None:
    """Create synthetic WAV file with alternating tone and silence segments."""
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        frames = bytearray()
        for dur, is_tone in segments:
            num_samples = int(dur * sample_rate)
            for i in range(num_samples):
                if is_tone:
                    sample_val = int(amplitude * 32767.0 * math.sin(2.0 * math.pi * freq_hz * i / sample_rate))
                else:
                    sample_val = 0
                frames.extend(struct.pack("<h", sample_val))
        wav.writeframes(frames)


class AudioMicroExtractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Device-host hermetic: pure-logic segmentation tests must stay GREEN
        # where ffmpeg/ffprobe are absent; ffmpeg-dependent legs skip with an
        # explicit device-deferred reason instead of erroring the whole module.
        try:
            cls.ffmpeg_bin, cls.ffprobe_bin = check_ffmpeg_available()
            cls.has_ffmpeg = True
        except RuntimeError:
            cls.ffmpeg_bin, cls.ffprobe_bin = None, None
            cls.has_ffmpeg = False

    def _require_ffmpeg(self):
        if not self.has_ffmpeg:
            self.skipTest(
                "device-deferred: ffmpeg/ffprobe not installed on this host; "
                "needs recorded authority amendment per T01-FIX-ENV"
            )

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_derive_speech_segments_logic(self):
        total_duration = 3.0
        # Silence at 0.0-0.2, 0.8-1.2, 1.8-2.2, 2.8-3.0
        silence_intervals = [(0.0, 0.2), (0.8, 1.2), (1.8, 2.2), (2.8, 3.0)]
        segments = derive_speech_segments(total_duration, silence_intervals)
        self.assertEqual(len(segments), 3)
        self.assertEqual(segments[0], (0.2, 0.8))
        self.assertEqual(segments[1], (1.2, 1.8))
        self.assertEqual(segments[2], (2.2, 2.8))

    def test_derive_speech_segments_no_silence(self):
        total_duration = 1.5
        segments = derive_speech_segments(total_duration, [])
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0], (0.0, 1.5))

    def test_extract_exact_middle_segment_success(self):
        self._require_ffmpeg()
        test_wav = self.work_dir / "triple_test.wav"
        out_wav = self.work_dir / "middle_extracted.wav"
        report_json = self.work_dir / "report.json"
        log_path = self.work_dir / "analysis.log"

        pattern = [
            (0.1, False),
            (0.4, True),
            (0.3, False),
            (0.4, True),
            (0.3, False),
            (0.4, True),
            (0.1, False),
        ]
        create_synthetic_wav(test_wav, pattern)

        success, report = run_extraction(
            input_wav=test_wav,
            output_wav=out_wav,
            noise_db=-30.0,
            min_silence_ms=150.0,
            expected_segments=3,
            segment_index=2,
            report_json_path=report_json,
            analysis_log_path=log_path,
        )

        self.assertTrue(success)
        self.assertEqual(report["detected_segment_count"], 3)
        self.assertTrue(out_wav.is_file())
        self.assertTrue(report_json.is_file())
        self.assertTrue(log_path.is_file())

        clip = report["extracted_clip"]
        self.assertIsNotNone(clip)
        self.assertAlmostEqual(clip["duration_seconds"], 0.48, delta=0.08)

        probe = probe_audio(out_wav, self.ffprobe_bin)
        self.assertEqual(probe["sample_rate_hz"], 24000)
        self.assertEqual(probe["channels"], 1)

    def test_check_only_mode(self):
        self._require_ffmpeg()
        test_wav = self.work_dir / "check_only.wav"
        pattern = [
            (0.1, False),
            (0.3, True),
            (0.2, False),
            (0.3, True),
            (0.2, False),
            (0.3, True),
            (0.1, False),
        ]
        create_synthetic_wav(test_wav, pattern)

        success, report = run_extraction(
            input_wav=test_wav,
            output_wav=None,
            noise_db=-30.0,
            min_silence_ms=150.0,
            expected_segments=3,
            segment_index=2,
        )
        self.assertTrue(success)
        self.assertEqual(report["detected_segment_count"], 3)
        self.assertIsNone(report["output_path"])

    def test_fail_when_two_segments_found(self):
        self._require_ffmpeg()
        test_wav = self.work_dir / "two_segments.wav"
        out_wav = self.work_dir / "out.wav"
        report_json = self.work_dir / "report.json"

        pattern = [
            (0.1, False),
            (0.4, True),
            (0.3, False),
            (0.4, True),
            (0.1, False),
        ]
        create_synthetic_wav(test_wav, pattern)

        success, report = run_extraction(
            input_wav=test_wav,
            output_wav=out_wav,
            noise_db=-30.0,
            min_silence_ms=150.0,
            expected_segments=3,
            segment_index=2,
            report_json_path=report_json,
        )

        self.assertFalse(success)
        self.assertEqual(report["detected_segment_count"], 2)
        self.assertIn("Expected 3 speech segments, but found 2", report["error"])
        self.assertFalse(out_wav.exists())

    def test_fail_when_four_segments_found(self):
        self._require_ffmpeg()
        test_wav = self.work_dir / "four_segments.wav"
        out_wav = self.work_dir / "out.wav"

        pattern = [
            (0.1, False),
            (0.3, True),
            (0.2, False),
            (0.3, True),
            (0.2, False),
            (0.3, True),
            (0.2, False),
            (0.3, True),
            (0.1, False),
        ]
        create_synthetic_wav(test_wav, pattern)

        success, report = run_extraction(
            input_wav=test_wav,
            output_wav=out_wav,
            noise_db=-30.0,
            min_silence_ms=150.0,
            expected_segments=3,
            segment_index=2,
        )

        self.assertFalse(success)
        self.assertEqual(report["detected_segment_count"], 4)
        self.assertIn("Expected 3 speech segments, but found 4", report["error"])

    def test_fail_when_invalid_segment_index(self):
        self._require_ffmpeg()
        test_wav = self.work_dir / "valid_triple.wav"
        pattern = [
            (0.1, False),
            (0.3, True),
            (0.2, False),
            (0.3, True),
            (0.2, False),
            (0.3, True),
            (0.1, False),
        ]
        create_synthetic_wav(test_wav, pattern)

        success, report = run_extraction(
            input_wav=test_wav,
            output_wav=self.work_dir / "out.wav",
            noise_db=-30.0,
            min_silence_ms=150.0,
            expected_segments=3,
            segment_index=5,
        )
        self.assertFalse(success)
        self.assertIn("out of range", report["error"])

    def test_missing_input_file_raises(self):
        self._require_ffmpeg()
        missing = self.work_dir / "missing.wav"
        with self.assertRaises(FileNotFoundError):
            run_extraction(missing, self.work_dir / "out.wav")


if __name__ == "__main__":
    unittest.main()
