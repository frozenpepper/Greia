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

    def test_punctuation_timestamps_and_split_apostrophe_clitics_are_not_extra_words(self) -> None:
        observed = {
            "text": "C'est ici. Trouve Luna.",
            "segments": [{"words": [
                {"word": "C", "start": .1, "end": .2},
                {"word": "'est", "start": .2, "end": .3},
                {"word": " ici", "start": .31, "end": .5},
                {"word": ".", "start": .5, "end": .51},
                {"word": " Trouve", "start": .8, "end": 1.1},
                {"word": " Luna.", "start": 1.11, "end": 1.4},
                {"word": "?", "start": 1.4, "end": 1.45},
            ]}],
        }
        timings, prefix_count, target_exact, _, _ = validate_transcript_and_boundary(
            observed, "C'est ici", "Trouve Luna", 2, duration_seconds=1.5
        )
        self.assertEqual(prefix_count, 2)
        self.assertEqual([item.token for item in timings], ["c'est", "ici", "trouve", "luna"])
        self.assertEqual(timings[0].start, .1)
        self.assertEqual(timings[0].end, .3)
        self.assertTrue(target_exact)

    def test_asr_grouped_words_cannot_straddle_known_prefix_boundary(self) -> None:
        observed = {
            "text": "Cette phrase Luna.",
            "segments": [{"words": [
                {"word": "Cette phrase", "start": .1, "end": .4},
                {"word": "Luna.", "start": .8, "end": 1.1},
            ]}],
        }
        with self.assertRaisesRegex(ExtractionRejected, "falls inside one timestamped ASR span"):
            validate_transcript_and_boundary(observed, "Cette", "phrase Luna", 1)

    def test_zero_duration_target_suffix_tokens_are_tolerated_but_prefix_is_not(self) -> None:
        observed = {
            "text": "Find Luna the cat",
            "segments": [{"words": [
                {"word": "Find", "start": .1, "end": .3},
                {"word": "Luna", "start": .7, "end": .9},
                {"word": "the", "start": .9, "end": .9},
                {"word": "cat", "start": .9, "end": 1.1},
            ]}],
        }
        timings, _, target_exact, _, _ = validate_transcript_and_boundary(
            observed, "Find", "Luna the cat", 1, duration_seconds=1.2
        )
        self.assertTrue(target_exact)
        self.assertEqual(timings[2].start, timings[2].end)
        observed["segments"][0]["words"][0]["end"] = .1
        # Disposable intro timings need not have nonzero duration.
        validate_transcript_and_boundary(
            observed, "Find", "Luna the cat", 1, duration_seconds=1.2
        )

    def test_punctuation_timestamp_beyond_source_duration_rejects(self) -> None:
        observed = {
            "text": "Find Luna.",
            "segments": [{"words": [
                {"word": "Find", "start": .1, "end": .3},
                {"word": "Luna", "start": .7, "end": .9},
                {"word": ".", "start": .9, "end": 1.1},
            ]}],
        }
        with self.assertRaisesRegex(ExtractionRejected, "extends beyond WAV duration"):
            validate_transcript_and_boundary(
                observed, "Find", "Luna", 1, duration_seconds=1.0
            )

    def test_prefix_word_count_must_match_explicit_remove_count(self) -> None:
        observed = result(("Find", .1, .2), ("Luna", .5, .7))
        with self.assertRaisesRegex(ExtractionRejected, "disagrees"):
            validate_transcript_and_boundary(observed, "Find.", "Luna.", 2)

    def test_target_suffix_ignores_corrupt_and_different_length_intro(self) -> None:
        for intro in [[("garble", .1, .2)], [("uh", .1, .15), ("noise", .16, .2)]]:
            observed = result(*intro, ("Trouve", .5, .7), ("Luna", .71, .9))
            _, boundary, exact, _, _ = validate_transcript_and_boundary(
                observed, "Cette phrase est en français", "Trouve Luna", 5)
            self.assertEqual(boundary, len(intro))
            self.assertTrue(exact)

    def test_warn_target_policy_requires_identifiable_target_suffix(self) -> None:
        _, boundary, exact, _, _ = validate_transcript_and_boundary(
            result(("garble", .1, .2), ("Louna", .5, .7)),
            "Find", "Luna", 1, target_verification="warn")
        self.assertEqual(boundary, 1)
        self.assertFalse(exact)
        with self.assertRaisesRegex(ExtractionRejected, "no matching final target"):
            validate_transcript_and_boundary(result(("garble", .1, .2), ("banana", .5, .7)),
                "Find", "Luna", 1, target_verification="warn")

    def test_final_target_ignores_same_words_in_discarded_intro(self):
        _, boundary, exact, _, _ = validate_transcript_and_boundary(
            result(("Luna", .1, .2), ("Luna", .6, .8)), "Find", "Luna", 1)
        self.assertEqual(boundary, 1)
        self.assertTrue(exact)

    def test_missing_or_changed_target_rejects(self) -> None:
        for words in [
            (("Find", .1, .2),),
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
            self.assertEqual(receipt["algorithm_version"], "greia-spoken-carrier-extractor-v6")
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
            raw = result(("Find", .1, .3), ("Louna", .6, .8))
            extracted = result(("Louna", .1, .3))

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
            self.assertEqual(evidence["unremoved_raw_target_tokens"], ["louna"])
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
            with self.assertRaisesRegex(ExtractionRejected, "beyond WAV duration") as rejected:
                extract(
                    source, output, locale="en", prefix="Find", target="Luna", remove_first_words=1,
                    transcriber=lambda _path, _locale: out_of_range,
                )
            self.assertEqual(rejected.exception.evidence["raw_transcript"], "Find Luna.")
            self.assertEqual(rejected.exception.evidence["raw_word_alignment"][-1]["word"], "Luna.")
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


class CoincidentBoundaryTests(unittest.TestCase):
    def exercise(self, root: Path, *, removed_text="Find", target_text="Luna", two_gaps=False):
        import struct
        source, destination = root / "source.wav", root / "target.wav"
        rate = 10000
        samples = [0] * 14000
        for left, right in ((1000, 6000), (10000, 12500)):
            for index in range(left, right):
                samples[index] = int(6000 * math.sin(index * .13))
        if two_gaps:
            samples[4500:5500] = [0] * 1000
            samples[5500:6000] = [5000] * 500
            # Two individually qualifying gaps inside the search interval.
            samples[4500:7000] = [0] * 2500
            samples[7000:7500] = [5000] * 500
        with wave.open(str(source), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(rate)
            handle.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        before = source.read_bytes()
        calls = []

        def transcribe(path, locale):
            calls.append(str(path))
            if path == source:
                return result(("Find", .1, .4), ("Luna", .4, 1.25))
            if ".removed-" in path.name:
                return result((removed_text, .1, .6))
            return result((target_text, .2, .45))

        try:
            return extract(source, destination, locale="en", prefix="Find", target="Luna",
                           remove_first_words=1, target_verification="warn", transcriber=transcribe)
        finally:
            self.assertEqual(source.read_bytes(), before)
            self.assertFalse(list(root.glob(".*.wav")))

    def test_pause_assigned_to_first_target_span_requires_both_exact_halves(self):
        with tempfile.TemporaryDirectory() as temp:
            receipt = self.exercise(Path(temp))
            self.assertEqual(receipt["boundary"]["search_strategy"],
                             "target-suffix-expanded-boundary")
            self.assertIsNone(receipt["removed_prefix_transcript"])
            self.assertEqual(receipt["boundary"]["cut_sample"], 8000)

    def test_discarded_intro_is_not_transcribed_or_verified(self):
        with tempfile.TemporaryDirectory() as temp:
            receipt = self.exercise(Path(temp), removed_text="garbled unimportant noise")
            self.assertTrue((Path(temp) / "target.wav").exists())
            self.assertEqual(receipt["intro_verification_policy"], "ignored-disposable-intro")

    def test_warn_mode_cannot_waive_recovery_target_check(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ExtractionRejected, "requires an exact extracted target"):
                self.exercise(Path(temp), target_text="na")
            self.assertFalse((Path(temp) / "target.wav").exists())

    def test_multiple_silent_runs_are_not_a_recovery_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ExtractionRejected, "no unique"):
                self.exercise(Path(temp), two_gaps=True)
            self.assertFalse((Path(temp) / "target.wav").exists())


if __name__ == "__main__":
    unittest.main()
