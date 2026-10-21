from __future__ import annotations

import math
import contextlib
import io
import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from voice_carrier import (  # noqa: E402
    ExtractionRejected,
    extract,
    main,
    measure_gap,
    parse_word_timings,
    spoken_words,
    validate_transcript_and_boundary,
)


def result(*words: tuple[str, float, float], text: str | None = None) -> dict:
    return {
        "text": text if text is not None else " ".join(word for word, _, _ in words),
        "segments": [{
            "start": words[0][1] if words else 0.0,
            "end": words[-1][2] if words else 0.0,
            "text": text or "",
            "words": [{"word": word, "start": start, "end": end} for word, start, end in words],
        }] if words else [],
    }


class VoiceCarrierTests(unittest.TestCase):
    def test_tokenizer_keeps_unicode_and_internal_apostrophes(self) -> None:
        self.assertEqual(spoken_words("L’été, l'ours voit Luna!"), ["l'été", "l'ours", "voit", "luna"])
        self.assertEqual(spoken_words("¿Está bien?"), ["está", "bien"])

    def test_exact_prefix_and_target_word_timings_pass(self) -> None:
        observed = result(("Cette", .1, .2), ("phrase", .21, .3), ("est", .31, .4),
                          ("en", .41, .46), ("français.", .47, .7), ("Trouve", 1., 1.3),
                          ("Luna.", 1.31, 1.6))
        timings, boundary, target_exact, _, _ = validate_transcript_and_boundary(
            observed, "Cette phrase est en français.", "Trouve Luna.", 5
        )
        self.assertEqual(boundary, 5)
        self.assertTrue(target_exact)
        self.assertEqual(timings[5].token, "trouve")

    def test_prefix_word_count_must_match_explicit_remove_count(self) -> None:
        observed = result(("Find", .1, .2), ("Luna", .5, .7))
        with self.assertRaisesRegex(ExtractionRejected, "disagrees"):
            validate_transcript_and_boundary(observed, "Find.", "Luna.", 2)

    def test_warn_target_policy_still_requires_exact_prefix_and_suffix(self) -> None:
        observed = result(("Find", .1, .2), ("l'une", .5, .65), ("à", .66, .7))
        timings, prefix_count, target_exact, _, _ = validate_transcript_and_boundary(
            observed, "Find", "Luna", 1, target_verification="warn"
        )
        self.assertEqual(prefix_count, 1)
        self.assertEqual(len(timings), 3)
        self.assertFalse(target_exact)
        with self.assertRaisesRegex(ExtractionRejected, "carrier prefix"):
            validate_transcript_and_boundary(
                result(("Fine", .1, .2), ("Luna", .5, .7)), "Find", "Luna", 1,
                target_verification="warn",
            )
        with self.assertRaisesRegex(ExtractionRejected, "no recognized words"):
            validate_transcript_and_boundary(
                result(("Find", .1, .2)), "Find", "Luna", 1, target_verification="warn"
            )

    def test_missing_repeated_or_changed_target_rejects(self) -> None:
        for words in [
            (("Find", .1, .2),),
            (("Find", .1, .2), ("Luna", .5, .7), ("Luna", .8, .9)),
            (("Find", .1, .2), ("Lina", .5, .7)),
        ]:
            with self.subTest(words=words), self.assertRaises(ExtractionRejected):
                validate_transcript_and_boundary(result(*words), "Find", "Luna", 1)

    def test_malformed_missing_and_ambiguous_timestamps_reject(self) -> None:
        with self.assertRaisesRegex(ExtractionRejected, "missing word timestamps"):
            parse_word_timings({"segments": [{"text": "Find Luna"}]})
        with self.assertRaisesRegex(ExtractionRejected, "timestamp"):
            parse_word_timings({"segments": [{"words": [{"word": "Find", "start": 0.3, "end": 0.2}]}]})
        with self.assertRaisesRegex(ExtractionRejected, "overlap"):
            parse_word_timings(result(("Find", .1, .4), ("Luna", .38, .7)))

    def test_too_short_or_merged_word_boundary_rejects(self) -> None:
        silence = [0] * 10000
        with self.assertRaisesRegex(ExtractionRejected, "no adequate pause"):
            measure_gap(silence, 10000, .1, .2)
        with self.assertRaisesRegex(ExtractionRejected, "outside the WAV"):
            measure_gap(silence, 10000, .8, 1.2)

    def test_gap_must_be_low_energy(self) -> None:
        samples = [0] * 5000
        samples[2200:2400] = [16000] * 200
        with self.assertRaisesRegex(ExtractionRejected, "no unique guarded low-energy run"):
            measure_gap(samples, 10000, .1, .4)

    def test_deterministic_extraction_records_audio_evidence_and_rechecks_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root / "raw.wav", root / "target.wav"
            # Two synthetic voiced blocks with a 300 ms silent carrier/target gap.
            samples = [0] * 10000
            for index in range(1000, 3000):
                samples[index] = int(5000 * math.sin(index * .1))
            for index in range(6000, 8500):
                samples[index] = int(5000 * math.sin(index * .1))
            with wave.open(str(source), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(10000)
                import struct
                handle.writeframes(struct.pack(f"<{len(samples)}h", *samples))
            raw = result(("Find", .1, .3), ("Luna.", .6, .85))
            target = result(("Luna.", .1, .35))

            def fake_transcribe(path: Path, locale: str) -> dict:
                self.assertEqual(locale, "en")
                return raw if path == source else target

            receipt = extract(
                source, output, locale="en", prefix="Find", target="Luna", remove_first_words=1,
                transcriber=fake_transcribe,
            )
            self.assertTrue(output.exists())
            self.assertEqual(receipt["status"], "EXTRACTED_PENDING_LISTENING")
            self.assertEqual(receipt["boundary"]["cut_sample"], 4500)
            self.assertEqual(receipt["human_review"], "PENDING")
            self.assertTrue(receipt["raw_word_alignment"])
            self.assertEqual(receipt["algorithm_version"], "greia-spoken-carrier-extractor-v2")
            self.assertGreaterEqual(receipt["extracted_voiced_seconds"], 0.08)

    def test_warn_policy_extracts_exact_prefix_with_unresolved_target_asr(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root / "raw.wav", root / "target.wav"
            samples = [0] * 10000
            for index in range(1000, 3000):
                samples[index] = int(5000 * math.sin(index * .1))
            for index in range(6000, 8500):
                samples[index] = int(5000 * math.sin(index * .1))
            with wave.open(str(source), "wb") as handle:
                handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(10000)
                import struct
                handle.writeframes(struct.pack(f"<{len(samples)}h", *samples))
            raw = result(("Find", .1, .3), ("l'une", .6, .7), ("à", .71, .8))
            extracted = result(("l'une", .1, .2), ("à", .21, .3))

            def fake_transcribe(path: Path, _locale: str) -> dict:
                return raw if path == source else extracted

            evidence = extract(
                source, output, locale="fr", prefix="Find", target="Luna", remove_first_words=1,
                transcriber=fake_transcribe, target_verification="warn",
            )
            self.assertTrue(output.exists())
            self.assertEqual(evidence["status"], "EXTRACTED_TARGET_WARN_PENDING_LISTENING")
            self.assertTrue(evidence["raw_prefix_exact_match"])
            self.assertFalse(evidence["raw_target_exact_match"])
            self.assertFalse(evidence["extracted_target_exact_match"])
            self.assertEqual(evidence["unremoved_raw_target_tokens"], ["l'une", "à"])
            self.assertEqual(evidence["target_verification_policy"], "warn")

    def test_warn_policy_rejects_asr_hallucination_on_near_silent_extracted_clip(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root / "raw.wav", root / "target.wav"
            samples = [0] * 10000
            for index in range(1000, 3000):
                samples[index] = int(5000 * math.sin(index * .1))
            for index in range(6000, 8500):
                samples[index] = int(5000 * math.sin(index * .1))
            with wave.open(str(source), "wb") as handle:
                handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(10000)
                import struct
                handle.writeframes(struct.pack(f"<{len(samples)}h", *samples))
            raw = result(("Find", .1, .3), ("Luna.", .6, .85))
            target = result(("Luna.", .1, .35))

            def hallucinating_transcriber(path: Path, _locale: str) -> dict:
                if path != source:
                    with wave.open(str(path), "wb") as handle:
                        handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(10000)
                        handle.writeframes(struct.pack("<10000h", *([0] * 10000)))
                    return target
                return raw

            with self.assertRaisesRegex(ExtractionRejected, "insufficient voiced duration"):
                extract(
                    source, output, locale="en", prefix="Find", target="Luna", remove_first_words=1,
                    transcriber=hallucinating_transcriber, target_verification="warn",
                )
            self.assertFalse(output.exists())

    def test_source_output_alias_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "raw.wav"
            with wave.open(str(source), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(10000)
                import struct
                handle.writeframes(struct.pack("<10000h", *([0] * 10000)))
            with self.assertRaisesRegex(ExtractionRejected, "same file"):
                extract(source, source, locale="en", prefix="Find", target="Luna", remove_first_words=1)

    def test_failed_extracted_transcript_keeps_existing_destination_and_cleans_temp(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root / "raw.wav", root / "target.wav"
            samples = [0] * 10000
            for index in range(1000, 3000):
                samples[index] = int(5000 * math.sin(index * .1))
            for index in range(6000, 8500):
                samples[index] = int(5000 * math.sin(index * .1))
            with wave.open(str(source), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(10000)
                import struct
                handle.writeframes(struct.pack(f"<{len(samples)}h", *samples))
            original = b"pre-existing reviewed output must survive"
            output.write_bytes(original)
            raw = result(("Find", .1, .3), ("Luna.", .6, .85))
            wrong = result(("Lina.", .1, .35))

            def fake_transcribe(path: Path, locale: str) -> dict:
                return raw if path == source else wrong

            with self.assertRaisesRegex(ExtractionRejected, "does not exactly match"):
                extract(
                    source, output, locale="en", prefix="Find", target="Luna", remove_first_words=1,
                    transcriber=fake_transcribe,
                )
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(list(root.glob(".target.wav.*.wav")), [])

    def test_late_word_timestamp_beyond_audio_duration_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root / "raw.wav", root / "target.wav"
            samples = [0] * 10000
            with wave.open(str(source), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(10000)
                import struct
                handle.writeframes(struct.pack(f"<{len(samples)}h", *samples))
            out_of_range = result(("Find", .1, .2), ("Luna.", .5, 1.2))
            with self.assertRaisesRegex(ExtractionRejected, "beyond raw WAV duration"):
                extract(
                    source, output, locale="en", prefix="Find", target="Luna", remove_first_words=1,
                    transcriber=lambda _path, _locale: out_of_range,
                )
            self.assertFalse(output.exists())

    def test_cli_receipt_alias_never_overwrites_raw_audio(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "raw.wav"
            original_samples = [0] * 10000
            with wave.open(str(source), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(10000)
                import struct
                handle.writeframes(struct.pack(f"<{len(original_samples)}h", *original_samples))
            original = source.read_bytes()
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                code = main([
                    str(source), str(Path(temp) / "target.wav"), "--locale", "en",
                    "--prefix", "Find", "--target", "Luna", "--remove-first-words", "1",
                    "--receipt", str(source),
                ])
            self.assertEqual(code, 2)
            self.assertEqual(source.read_bytes(), original)
            rejection = Path(temp) / "raw.wav.rejected.json"
            self.assertTrue(rejection.exists())
            self.assertEqual(json.loads(rejection.read_text())["status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
