from __future__ import annotations

import hashlib
import json
import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from voice_carrier import ExtractionRejected  # noqa: E402
from voice_carrier_search import (  # noqa: E402
    ALGORITHM_VERSION,
    CandidateTranscriptionError,
    extract,
)


RATE = 10_000


def _tone(samples: list[int], start: float, end: float, *, amplitude: int = 9000) -> None:
    for index in range(round(start * RATE), round(end * RATE)):
        samples[index] = int(amplitude * math.sin(index * 0.1))


def _wav(path: Path, *, gaps: bool = True, silent: bool = False, no_prefix_voice: bool = False) -> bytes:
    samples = [0] * (RATE * 3)
    if not silent:
        if gaps:
            if no_prefix_voice:
                _tone(samples, .40, .45)
            else:
                _tone(samples, .40, 1.00)
            _tone(samples, 1.40, 2.90)
        else:
            if not no_prefix_voice:
                _tone(samples, .40, 2.90)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        import struct
        wav.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return path.read_bytes()


def _two_gap_wav(path: Path) -> bytes:
    samples = [0] * (RATE * 3)
    _tone(samples, .40, .80)
    _tone(samples, 1.20, 1.60)
    _tone(samples, 2.00, 2.90)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        import struct
        wav.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return path.read_bytes()


def _many_gap_wav(path: Path, count: int = 7) -> bytes:
    """Create more qualifying gaps than v7 may inspect."""
    duration = 0.45 + count * 0.55 + 0.40
    samples = [0] * round(RATE * duration)
    _tone(samples, .10, .40)
    for index in range(count):
        quiet_start = .55 + index * .55
        _tone(samples, quiet_start - .15, quiet_start)
        _tone(samples, quiet_start + .25, quiet_start + .40)
    _tone(samples, .55 + (count - 1) * .55 + .40, duration - .05)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        import struct
        wav.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return path.read_bytes()


def _result(text: str) -> dict:
    return {"text": text, "segments": []}


class VoiceCarrierSearchTests(unittest.TestCase):
    def setup_case(self, root: Path, *, target="10 house", prefix="Find a number", gaps=True,
                   silent=False, no_prefix_voice=False, two_gaps=False, transcripts=None,
                   destination_bytes=None, target_verification="required"):
        source = root / "source.wav"
        destination = root / "target.wav"
        raw = _two_gap_wav(source) if two_gaps else _wav(
            source, gaps=gaps, silent=silent, no_prefix_voice=no_prefix_voice
        )
        source_before = source.read_bytes()
        if destination_bytes is not None:
            destination.write_bytes(destination_bytes)
        provider_receipt = root / "provider.receipt.json"
        provider_receipt.write_text(json.dumps({"request": {"cue_id": "fixture.cue"}}))
        calls: list[Path] = []
        responses = transcripts or ["ten house"]

        def transcriber(path: Path, locale: str) -> dict:
            self.assertIn(locale, {"en", "fr"})
            calls.append(path)
            self.assertNotEqual(path, source, "v7 must not transcribe the disposable raw intro")
            index = int(path.stem.rsplit("-", 1)[1]) - 1
            text = responses[min(index, len(responses) - 1)]
            return _result(text)

        kwargs = {
            "locale": "en", "prefix": prefix, "target": target,
            "remove_first_words": len(prefix.split()), "source_receipt_path": provider_receipt,
            "transcriber": transcriber, "target_verification": target_verification,
        }
        return source, destination, raw, source_before, provider_receipt, calls, kwargs

    def test_independently_transcribes_suffix_without_intro_asr_and_records_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, destination, raw, source_before, provider_receipt, calls, kwargs = self.setup_case(root)
            receipt = extract(source, destination, **kwargs)
            self.assertTrue(calls)
            self.assertTrue(all(path.parent.parent.name == "target.wav.search" for path in calls))
            self.assertEqual(source.read_bytes(), source_before)
            self.assertEqual(receipt["algorithm_version"], ALGORITHM_VERSION)
            self.assertEqual(receipt["comparison_policy"], "locale-number-tokens-v1")
            self.assertEqual(receipt["extracted_transcript"], "ten house")
            self.assertEqual(receipt["model_id"], "mlx-community/whisper-base-mlx")
            self.assertTrue(receipt["model_revision"])
            self.assertEqual(receipt["recognizer"], "mlx-whisper-base")
            self.assertEqual(receipt["source_provider_receipt_sha256"], hashlib.sha256(provider_receipt.read_bytes()).hexdigest())
            self.assertEqual(receipt["output_sha256"], hashlib.sha256(destination.read_bytes()).hexdigest())
            self.assertEqual(receipt["boundary"]["cut_sample"], 13_000)
            self.assertGreaterEqual(receipt["boundary"]["cut_time_seconds"], receipt["boundary"]["verified_silence_start_seconds"])
            self.assertLess(receipt["boundary"]["cut_time_seconds"], receipt["boundary"]["verified_silence_end_seconds"])
            report = json.loads(Path(receipt["search_evidence_json"]).read_text())
            self.assertEqual(report["raw_intro_asr"], "not-run-disposable-intro")
            self.assertEqual(len(report["candidate_results"]), 1)
            self.assertTrue(report["candidate_results"][0]["exact_target_match"])
            self.assertEqual(report["candidate_results"][0]["candidate_sha256"], receipt["candidate_sha256"])
            with wave.open(str(source), "rb") as source_wav, wave.open(str(destination), "rb") as output_wav:
                source_wav.setpos(13_000)
                self.assertEqual(output_wav.readframes(output_wav.getnframes()),
                                 source_wav.readframes(source_wav.getnframes() - 13_000))

    def test_corrupted_or_omitted_intro_text_does_not_affect_exact_suffix(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, destination, _, _, _, calls, kwargs = self.setup_case(root, transcripts=["ten house"])
            receipt = extract(source, destination, **kwargs)
            self.assertTrue(receipt["extracted_target_exact_match"])
            self.assertTrue(calls)
            self.assertNotIn(source, calls)

    def test_zero_exact_candidates_rejects_wrong_extra_or_missing_target_and_keeps_output(self):
        for transcript in ("eleven house", "ten house cat", "ten", "unrelated words"):
            with self.subTest(transcript=transcript), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                sentinel = b"existing output remains untouched"
                source, destination, _, source_before, _, _, kwargs = self.setup_case(
                    root, transcripts=[transcript], destination_bytes=sentinel
                )
                with self.assertRaisesRegex(ExtractionRejected, "no candidate suffix meets target verification policy") as rejected:
                    extract(source, destination, **kwargs)
                self.assertEqual(source.read_bytes(), source_before)
                self.assertEqual(destination.read_bytes(), sentinel)
                evidence_dir = Path(rejected.exception.evidence["search_evidence_dir"])
                report = json.loads((evidence_dir / "search.json").read_text())
                self.assertEqual(report["status"], "REJECTED")
                self.assertEqual(report["candidate_results"][0]["extracted_transcript"], transcript)
                self.assertTrue((evidence_dir / "candidate-01.wav").is_file())

    def test_multiple_exact_candidates_rejects_without_selecting_score_or_time(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.wav"
            _two_gap_wav(source)
            destination = root / "target.wav"
            calls = []

            def transcriber(path: Path, locale: str) -> dict:
                calls.append(path)
                return _result("ten house")

            with self.assertRaisesRegex(ExtractionRejected, "multiple candidate suffixes") as rejected:
                extract(source, destination, locale="en", prefix="Find a number", target="10 house",
                        remove_first_words=3, transcriber=transcriber)
            self.assertEqual(len(calls), 2)
            self.assertFalse(destination.exists())
            report = json.loads((Path(rejected.exception.evidence["search_evidence_dir"]) / "search.json").read_text())
            self.assertEqual(report["qualifying_quiet_run_count"], 2)
            self.assertEqual(sum(c["exact_target_match"] for c in report["candidate_results"]), 2)

    def test_silence_and_no_pause_reject_and_save_search_evidence(self):
        for options in ({"silent": True}, {"gaps": False}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                source, destination, _, before, _, calls, kwargs = self.setup_case(root, **options)
                with self.assertRaises(ExtractionRejected) as rejected:
                    extract(source, destination, **kwargs)
                self.assertEqual(source.read_bytes(), before)
                self.assertFalse(destination.exists())
                report = json.loads((Path(rejected.exception.evidence["search_evidence_dir"]) / "search.json").read_text())
                self.assertEqual(report["status"], "REJECTED")
                self.assertEqual(calls, [])

    def test_speech_floor_and_unsafe_prefix_configuration_reject(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, destination, _, _, _, _, kwargs = self.setup_case(root, no_prefix_voice=True)
            with self.assertRaisesRegex(ExtractionRejected, "energetic-signal floor") as rejected:
                extract(source, destination, **kwargs)
            report = json.loads((Path(rejected.exception.evidence["search_evidence_dir"]) / "search.json").read_text())
            self.assertIn("before candidate boundary", report["candidate_results"][0]["error"])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, destination, _, _, _, _, kwargs = self.setup_case(root, prefix="Find 10 now", target="10")
            kwargs["remove_first_words"] = 3
            with self.assertRaisesRegex(ExtractionRejected, "occur contiguously in prefix") as rejected:
                extract(source, destination, **kwargs)
            self.assertEqual(json.loads((Path(rejected.exception.evidence["search_evidence_dir"]) / "search.json").read_text())["status"], "REJECTED")

    def test_warn_policy_never_waives_exact_target_requirement(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, destination, _, _, _, _, kwargs = self.setup_case(root, transcripts=["eleven house"], target_verification="warn")
            with self.assertRaisesRegex(ExtractionRejected, "no candidate suffix meets target verification policy"):
                extract(source, destination, **kwargs)

    def test_warn_policy_accepts_one_minor_asr_difference_but_required_stays_exact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, destination, _, _, _, _, kwargs = self.setup_case(root, transcripts=["ten hous"])
            with self.assertRaisesRegex(ExtractionRejected, "no candidate suffix meets target verification policy"):
                extract(source, destination, **kwargs)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, destination, _, _, _, _, kwargs = self.setup_case(
                root, transcripts=["ten hous"], target_verification="warn"
            )
            receipt = extract(source, destination, **kwargs)
            self.assertFalse(receipt["extracted_target_exact_match"])
            self.assertTrue(receipt["target_transcript_warning"])
            self.assertEqual(receipt["target_verification_requested"], "warn")
            self.assertEqual(
                receipt["target_verification_policy"],
                "similarity-greater-than-0.8-with-same-word-count-and-numeric-sequence",
            )
            self.assertGreater(receipt["target_comparison_score"], 0.8)
            self.assertTrue(receipt["target_word_count_matches"])
            self.assertTrue(receipt["target_numbers_match"])
            self.assertEqual(receipt["target_comparison_flags"], [])
            report = json.loads(Path(receipt["search_evidence_json"]).read_text())
            candidate = report["candidate_results"][0]
            self.assertEqual(candidate["target_verification_effective_policy"],
                             "similarity>0.8+same-word-count+same-numeric-sequence")
            self.assertTrue(candidate["target_verification_qualifies"])

    def test_warn_policy_still_rejects_wrong_number_extra_or_missing_words(self):
        for transcript in ("eleven house", "ten house cat", "ten"):
            with self.subTest(transcript=transcript), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                source, destination, _, _, _, _, kwargs = self.setup_case(
                    root, transcripts=[transcript], target_verification="warn"
                )
                with self.assertRaisesRegex(ExtractionRejected, "no candidate suffix meets target verification policy") as rejected:
                    extract(source, destination, **kwargs)
                candidate = json.loads(Path(rejected.exception.evidence["search_evidence_json"]).read_text())["candidate_results"][0]
                self.assertFalse(candidate["target_verification_qualifies"])
                if transcript.startswith("eleven"):
                    self.assertFalse(candidate["target_numbers_match"])
                else:
                    self.assertFalse(candidate["target_word_count_matches"])

    def test_warn_policy_rejects_multiple_qualifying_candidates_without_score_tiebreak(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.wav"
            _two_gap_wav(source)
            destination = root / "target.wav"
            responses = iter(("ten hous", "ten house"))

            def transcriber(path: Path, locale: str) -> dict:
                return _result(next(responses))

            with self.assertRaisesRegex(ExtractionRejected, "multiple candidate suffixes meet target verification policy") as caught:
                extract(source, destination, locale="en", prefix="Find a number", target="10 house",
                        remove_first_words=3, transcriber=transcriber, target_verification="warn")
            report = json.loads(Path(caught.exception.evidence["search_evidence_json"]).read_text())
            candidates = report["candidate_results"]
            self.assertEqual(len(candidates), 2)
            self.assertTrue(all(candidate["target_verification_qualifies"] for candidate in candidates))
            self.assertGreater(candidates[1]["target_comparison_score"], candidates[0]["target_comparison_score"])
            self.assertFalse(destination.exists())

    def test_unsafe_parameters_and_receipt_alias_reject(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, destination, _, _, receipt_path, _, kwargs = self.setup_case(root)
            invalid_kwargs = dict(kwargs, padding_seconds=.09)
            with self.assertRaisesRegex(ExtractionRejected, "fixed 0.10"):
                extract(source, destination, **invalid_kwargs)
            invalid_kwargs = dict(kwargs, remove_first_words=True)
            with self.assertRaisesRegex(ExtractionRejected, "must be an integer"):
                extract(source, destination, **invalid_kwargs)
            invalid_kwargs = dict(kwargs, ignore_accents=1)
            with self.assertRaisesRegex(ExtractionRejected, "boolean"):
                extract(source, destination, **invalid_kwargs)
            invalid_kwargs = dict(kwargs, source_receipt_path=source)
            with self.assertRaisesRegex(ExtractionRejected, "does not exist|aliases"):
                extract(source, destination, **invalid_kwargs)
            # Each invalid call leaves original source and any prior output untouched.
            self.assertTrue(source.exists())
            self.assertTrue(receipt_path.exists())

    def test_number_comparison_policy_is_used_for_target_match(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, destination, _, _, _, _, kwargs = self.setup_case(root, target="17", transcripts=["dix-sept"])
            kwargs["locale"] = "fr"
            kwargs["prefix"] = "Voici un mot"
            kwargs["remove_first_words"] = 3
            receipt = extract(source, destination, **kwargs)
            self.assertTrue(receipt["extracted_target_exact_match"])
            self.assertEqual(receipt["expected_target_tokens"], ["<num:17>"])

    def test_transcriber_failure_is_fatal_once_and_preserves_source_and_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.wav"
            source_before = _wav(source)
            destination = root / "target.wav"
            destination_before = b"previous accepted take"
            destination.write_bytes(destination_before)
            calls = []

            def broken_transcriber(path: Path, locale: str) -> dict:
                calls.append(path)
                raise OSError("cached Base backend unavailable")

            with self.assertRaises(CandidateTranscriptionError) as caught:
                extract(source, destination, locale="en", prefix="Find a number", target="10 house",
                        remove_first_words=3, transcriber=broken_transcriber)

            self.assertNotIsInstance(caught.exception, ExtractionRejected)
            self.assertEqual(len(calls), 1, "an ASR infrastructure failure must not trigger another call")
            self.assertEqual(source.read_bytes(), source_before)
            self.assertEqual(destination.read_bytes(), destination_before)
            report_path = Path(caught.exception.evidence["search_evidence_json"])
            report = json.loads(report_path.read_text())
            self.assertEqual(report["status"], "ASR_ERROR")
            self.assertIn("cached Base backend unavailable", report["candidate_results"][0]["transcription_error"])
            self.assertTrue(Path(report["candidate_results"][0]["candidate_path"]).is_file())

    def test_malformed_transcriber_result_is_fatal_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.wav"
            source_before = _wav(source)
            destination = root / "target.wav"
            destination_before = b"previous accepted take"
            destination.write_bytes(destination_before)
            calls = []

            def malformed_transcriber(path: Path, locale: str):
                calls.append(path)
                return {"text": None}

            with self.assertRaises(CandidateTranscriptionError) as caught:
                extract(source, destination, locale="en", prefix="Find a number", target="10 house",
                        remove_first_words=3, transcriber=malformed_transcriber)
            self.assertEqual(len(calls), 1)
            self.assertEqual(source.read_bytes(), source_before)
            self.assertEqual(destination.read_bytes(), destination_before)
            report = json.loads(Path(caught.exception.evidence["search_evidence_json"]).read_text())
            self.assertEqual(report["status"], "ASR_ERROR")
            self.assertIn("malformed transcript", report["candidate_results"][0]["transcription_error"])

    def test_candidate_cap_rejects_before_asr_and_persists_at_most_six_suffixes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.wav"
            _many_gap_wav(source)
            destination = root / "target.wav"
            calls = []

            def should_not_transcribe(path: Path, locale: str) -> dict:
                calls.append(path)
                return _result("ten house")

            with self.assertRaisesRegex(ExtractionRejected, "exceed bounded candidate cap") as caught:
                extract(source, destination, locale="en", prefix="Find a number", target="10 house",
                        remove_first_words=3, transcriber=should_not_transcribe)
            self.assertEqual(calls, [])
            report = json.loads(Path(caught.exception.evidence["search_evidence_json"]).read_text())
            self.assertGreater(report["qualifying_quiet_run_count"], 6)
            self.assertLessEqual(len(report["candidate_results"]), 6)
            self.assertEqual(len(list(Path(caught.exception.evidence["search_evidence_dir"]).glob("candidate-*.wav"))), 6)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
