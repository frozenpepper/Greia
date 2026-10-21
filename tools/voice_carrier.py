#!/usr/bin/env python3
"""Fail-closed extraction of a spoken cue following a language carrier.

Whisper proposes word boundaries; a separate PCM energy-gap check must confirm
that a quiet, unambiguous boundary exists before deterministic sample cutting.
Neither transcript agreement nor this tool is listening acceptance.
"""
from __future__ import annotations

import argparse
from array import array
import hashlib
from difflib import SequenceMatcher
import importlib.metadata
import json
import math
import os
import re
import struct
import sys
import tempfile
import unicodedata
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence
from greia_voice_core.asr_policy import (DEFAULT_ASR_MODEL, DEFAULT_ASR_REVISION,
    DEFAULT_ASR_VERIFIER, cached_asr_model, comparison_text)


ALGORITHM_VERSION = "greia-spoken-carrier-extractor-v6"
MAX_CLIP_SECONDS = 120
GAP_POLICY = {
    "minimum_run_seconds": 0.20,
    "endpoint_guard_seconds": 0.05,
    "frame_ms": 10,
    "max_frame_rms_dbfs": -42.0,
    "max_frame_peak_dbfs": -30.0,
    "cut_padding_seconds": 0.10,
    "minimum_extracted_voiced_seconds": 0.08,
}


class ExtractionRejected(ValueError):
    """Raised when evidence is malformed or cannot establish a safe cut."""

    def __init__(self, message: str, *, evidence: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.evidence = evidence or {}


def spoken_words(text: str) -> list[str]:
    """Normalize punctuation but preserve Unicode spelling and apostrophes."""
    normalized = unicodedata.normalize("NFC", text).casefold().replace("’", "'").replace("‘", "'")
    return re.findall(r"[^\W_]+(?:'[^\W_]+)*", normalized, flags=re.UNICODE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _cached_model_revision() -> str:
    return DEFAULT_ASR_REVISION


def comparison_words(text: str, *, ignore_accents: bool = True) -> list[str]:
    """Recognition tokens only; authored text and recorded tokens remain intact."""
    return spoken_words(comparison_text(text, ignore_accents=ignore_accents))


def _asr_score_evidence(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Preserve available recognizer confidence metadata without treating it as truth."""
    evidence = []
    for segment in result.get("segments", []):
        if not isinstance(segment, dict):
            continue
        evidence.append({
            key: segment[key] for key in ("avg_logprob", "no_speech_prob", "compression_ratio")
            if isinstance(segment.get(key), (int, float)) and not isinstance(segment.get(key), bool)
        } | {
            "word_probabilities": [
                word.get("probability") for word in segment.get("words", [])
                if isinstance(word, dict) and isinstance(word.get("probability"), (int, float))
                and not isinstance(word.get("probability"), bool)
            ]
        })
    return evidence


def _raw_word_alignment_evidence(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Keep raw word entries even when parsing rejects their representation."""
    evidence: list[dict[str, Any]] = []
    for segment in result.get("segments", []):
        if not isinstance(segment, dict) or not isinstance(segment.get("words"), list):
            continue
        for word in segment["words"]:
            if not isinstance(word, dict):
                evidence.append({"malformed_entry": repr(word)})
                continue
            item: dict[str, Any] = {"word": word.get("word")}
            for source, destination in (("start", "start_seconds"), ("end", "end_seconds")):
                value = word.get(source)
                if isinstance(value, bool):
                    item[destination] = value
                elif isinstance(value, (int, float)):
                    item[destination] = float(value)
                else:
                    item[destination] = repr(value)
            evidence.append(item)
    return evidence


@dataclass(frozen=True)
class WordTiming:
    token: str
    start: float
    end: float
    span_id: int = 0


def parse_word_timings(
    result: dict[str, Any], *, duration_seconds: float | None = None,
) -> tuple[str, list[WordTiming]]:
    """Normalize lexical tokens while retaining Whisper's indivisible timing spans.

    Whisper may return punctuation-only entries or split an apostrophe clitic
    (for example ``C`` + ``'est``) across adjacent entries. Those are transcript
    representation details, not spoken-word boundaries. Tokens from one timed
    entry share a span id, so callers can refuse a cut inside that entry.
    """
    recognized: list[str] = []
    timings: list[WordTiming] = []
    previous_start: float | None = None
    previous_end: float | None = None
    next_span_id = 0
    segments = result.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ExtractionRejected("ASR returned no timestamped segments")
    for segment in segments:
        if not isinstance(segment, dict) or not isinstance(segment.get("words"), list):
            raise ExtractionRejected("ASR segment is missing word timestamps")
        for word in segment["words"]:
            if not isinstance(word, dict) or not isinstance(word.get("word"), str):
                raise ExtractionRejected("malformed ASR word entry")
            if isinstance(word.get("start"), bool) or isinstance(word.get("end"), bool):
                raise ExtractionRejected("ASR word timestamp is boolean, not numeric")
            try:
                start, end = float(word["start"]), float(word["end"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ExtractionRejected("ASR word timestamp is missing or invalid") from exc
            if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end < start:
                raise ExtractionRejected("ASR word timestamp is non-finite or has invalid extent")
            if duration_seconds is not None and end > duration_seconds:
                raise ExtractionRejected("ASR word timestamp extends beyond WAV duration")
            if previous_start is not None and (start < previous_start or start < previous_end - 0.01):
                raise ExtractionRejected("ASR word timestamps overlap or move backwards")
            previous_start, previous_end = start, end
            tokens = spoken_words(word["word"])
            if not tokens:
                # Punctuation has timing metadata but is not a spoken token.
                continue
            raw_word = word["word"].strip()
            if raw_word[:1] in {"'", "’", "‘"} and len(tokens) == 1 and timings:
                # Whisper's French/Italian clitic split is one orthographic word.
                previous = timings[-1]
                joined = previous.token + "'" + tokens[0]
                timings[-1] = WordTiming(joined, previous.start, end, previous.span_id)
                recognized[-1] = joined
                continue
            span_id = next_span_id
            next_span_id += 1
            for token in tokens:
                timings.append(WordTiming(token, start, end, span_id))
                recognized.append(token)
    return " ".join(recognized), timings


def validate_transcript_and_boundary(
    result: dict[str, Any], prefix: str, target: str, remove_first_words: int,
    target_verification: str = "required",
    duration_seconds: float | None = None,
    ignore_accents: bool = True,
) -> tuple[list[WordTiming], int, bool, list[str], list[str]]:
    """Locate the final target suffix; the disposable intro is never text-verified."""
    prefix_words = spoken_words(prefix)
    target_words = spoken_words(target)
    if not prefix_words or not target_words:
        raise ExtractionRejected("prefix and target must both contain spoken words")
    if target_verification not in {"required", "warn"}:
        raise ExtractionRejected("target verification must be required or warn")
    if remove_first_words != len(prefix_words):
        raise ExtractionRejected(
            f"remove-first-words={remove_first_words} disagrees with prefix word count {len(prefix_words)}"
        )
    recognized_text, timings = parse_word_timings(result, duration_seconds=duration_seconds)
    recognized_words = spoken_words(recognized_text)
    transcript_words = spoken_words(str(result.get("text", "")))
    # Locate the intended suffix, never count recognized introductory words.
    # Introductory speech can be corrupt, omitted or hallucinated by ASR.
    candidates = []
    target_comparison = comparison_words(target, ignore_accents=ignore_accents)
    aligned_comparison = comparison_words(recognized_text, ignore_accents=ignore_accents)
    expected = " ".join(target_comparison)
    for count in range(max(1, len(target_words) - 1), len(target_words) + 2):
        boundary = len(timings) - count
        if boundary < 1:
            continue
        suffix = aligned_comparison[boundary:]
        score = SequenceMatcher(None, expected, " ".join(suffix), autojunk=False).ratio()
        exact = suffix == target_comparison
        if exact or (target_verification == "warn" and len(expected) >= 4 and score >= .8):
            candidates.append((score, boundary, exact))
    candidates.sort(reverse=True)
    if not candidates:
        raise ExtractionRejected("no matching final target suffix in timestamped ASR",
                                 evidence={"raw_transcript": result.get("text", ""),
                                           "recognized_words": recognized_words})
    score, boundary, aligned_exact = candidates[0]
    if len(candidates) > 1 and abs(score - candidates[1][0]) < .03:
        raise ExtractionRejected("ambiguous final target suffix alignment")
    if timings[boundary - 1].span_id == timings[boundary].span_id:
        raise ExtractionRejected("target boundary falls inside one timestamped ASR span")
    if timings[boundary].end <= timings[boundary].start:
        raise ExtractionRejected("first target word has no usable ASR boundary timestamp")
    # The full transcript may tokenize the discarded intro differently. Only
    # its final target words matter, and no prefix spelling check is performed.
    transcript_exact = comparison_words(str(result.get("text", "")), ignore_accents=ignore_accents)[-len(target_words):] == target_comparison
    return timings, boundary, aligned_exact and transcript_exact, transcript_words, recognized_words


def _read_pcm16(path: Path) -> tuple[int, int, list[int]]:
    try:
        with wave.open(str(path), "rb") as source:
            channels, width, rate = source.getnchannels(), source.getsampwidth(), source.getframerate()
            frame_count = source.getnframes()
            if rate <= 0 or rate > 192000 or frame_count <= 0 or frame_count / rate > MAX_CLIP_SECONDS:
                raise ExtractionRejected(f"input duration must be in (0, {MAX_CLIP_SECONDS}] seconds")
            if path.stat().st_size > (MAX_CLIP_SECONDS * max(rate, 1) * 2 + 65536):
                raise ExtractionRejected("input WAV exceeds the bounded PCM16 size limit")
            frames = source.readframes(frame_count)
    except (wave.Error, OSError) as exc:
        raise ExtractionRejected(f"input is not a readable PCM WAV: {exc}") from exc
    if channels != 1 or width != 2 or not rate:
        raise ExtractionRejected("input must be mono PCM16 WAV")
    usable = len(frames) - (len(frames) % 2)
    samples = list(struct.unpack(f"<{usable // 2}h", frames[:usable]))
    if not samples:
        raise ExtractionRejected("input WAV has no audio samples")
    return rate, channels, samples


def _pcm16_bytes(samples: Sequence[int]) -> bytes:
    packed = array("h", samples)
    if sys.byteorder != "little":
        packed.byteswap()
    return packed.tobytes()


def _same_file_path(left: Path, right: Path) -> bool:
    if left.resolve(strict=False) == right.resolve(strict=False):
        return True
    return left.exists() and right.exists() and os.path.samefile(left, right)


@dataclass(frozen=True)
class GapEvidence:
    start_sample: int
    end_sample: int
    duration_seconds: float
    rms_dbfs: float
    peak_dbfs: float
    quiet_fraction: float
    run_start_seconds: float
    run_end_seconds: float


def measure_gap(
    samples: Sequence[int], rate: int, start: float, end: float,
    *, min_gap_seconds: float = GAP_POLICY["minimum_run_seconds"],
    endpoint_guard_seconds: float = GAP_POLICY["endpoint_guard_seconds"],
    frame_ms: int = GAP_POLICY["frame_ms"],
    max_rms_dbfs: float = GAP_POLICY["max_frame_rms_dbfs"],
    max_peak_dbfs: float = GAP_POLICY["max_frame_peak_dbfs"],
) -> GapEvidence:
    """Find one guarded, low-energy run inside the timestamped inter-word gap."""
    left = round(start * rate)
    right = round(end * rate)
    if not (0 <= left <= len(samples) and 0 <= right <= len(samples)):
        raise ExtractionRejected("proposed word boundary lies outside the WAV")
    if left >= right:
        raise ExtractionRejected("adjacent word timestamps have no positive inter-word gap")
    duration = (right - left) / rate
    if duration < min_gap_seconds:
        raise ExtractionRejected(f"word boundary has no adequate pause ({duration:.3f}s)")
    frame_samples = max(1, round(rate * frame_ms / 1000))
    energy: list[tuple[int, int, float, float, int]] = []
    for offset in range(left, right - frame_samples + 1, frame_samples):
        chunk = samples[offset:min(offset + frame_samples, right)]
        if not chunk:
            continue
        peak = max(abs(value) for value in chunk)
        rms = math.sqrt(sum(value * value for value in chunk) / len(chunk))
        db = -120.0 if rms == 0 else 20 * math.log10(rms / 32768.0)
        peak_db = -120.0 if peak == 0 else 20 * math.log10(peak / 32768.0)
        energy.append((offset, offset + len(chunk), db, peak_db, peak))
    guard = round(endpoint_guard_seconds * rate)
    runs: list[list[tuple[int, int, float, float, int]]] = []
    current: list[tuple[int, int, float, float, int]] = []
    for frame in energy:
        offset, _, rms_db, peak_db, _ = frame
        quiet = rms_db <= max_rms_dbfs and peak_db <= max_peak_dbfs
        interior = offset >= left + guard and frame[1] <= right - guard
        if quiet and interior:
            current.append(frame)
        else:
            if current:
                runs.append(current)
                current = []
    if current:
        runs.append(current)
    candidates = [run for run in runs if sum(f[1] - f[0] for f in run) / rate >= min_gap_seconds]
    if len(candidates) != 1:
        run_summaries = [
            {
                "start_seconds": round(run[0][0] / rate, 4),
                "end_seconds": round(run[-1][1] / rate, 4),
                "duration_seconds": round(sum(f[1] - f[0] for f in run) / rate, 4),
            }
            for run in runs
        ]
        raise ExtractionRejected(
            "timestamped word boundary has no unique guarded low-energy run "
            f"(qualifying_runs={len(candidates)}, timestamp_gap={duration:.3f}s, runs={run_summaries})",
            evidence={
                "timestamp_gap_seconds": duration,
                "candidate_low_energy_runs": run_summaries,
                "thresholds": {
                    "minimum_run_seconds": min_gap_seconds,
                    "endpoint_guard_seconds": endpoint_guard_seconds,
                    "max_frame_rms_dbfs": max_rms_dbfs,
                    "max_frame_peak_dbfs": max_peak_dbfs,
                },
            },
        )
    run = candidates[0]
    run_start, run_end = run[0][0], run[-1][1]
    run_duration = (run_end - run_start) / rate
    run_samples = samples[run_start:run_end]
    rms = math.sqrt(sum(value * value for value in run_samples) / max(1, len(run_samples)))
    rms_db = -120.0 if rms == 0 else 20 * math.log10(rms / 32768.0)
    peak = max(abs(value) for value in run_samples)
    peak_db = -120.0 if peak == 0 else 20 * math.log10(peak / 32768.0)
    quiet_fraction = sum(f[1] - f[0] for f in run) / (run_end - run_start)
    return GapEvidence(run_start, run_end, run_duration, rms_db, peak_db, quiet_fraction,
                       run_start / rate, run_end / rate)


def _whisper_transcribe(path: Path, locale: str) -> dict[str, Any]:
    """Use only installed mlx-whisper and cached weights; never fetch a model."""
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        import mlx_whisper
        return mlx_whisper.transcribe(
            str(path), path_or_hf_repo=str(cached_asr_model()), language=locale,
            word_timestamps=True, initial_prompt=None, temperature=0.0,
            condition_on_previous_text=False, verbose=False,
        )
    except Exception as exc:
        raise ExtractionRejected(f"offline Whisper timestamp pass failed: {exc}") from exc


def extract(
    source: Path, destination: Path, *, locale: str, prefix: str, target: str,
    remove_first_words: int, transcriber: Callable[[Path, str], dict[str, Any]] = _whisper_transcribe,
    padding_seconds: float = 0.10, source_receipt_path: Path | None = None,
    target_verification: str = "required", ignore_accents: bool = True,
) -> dict[str, Any]:
    """Analyze, fail closed, cut deterministically, and verify extracted target."""
    if not isinstance(ignore_accents, bool):
        raise ExtractionRejected("ignore_accents must be a boolean")
    if locale not in {"en", "it", "fr", "es"}:
        raise ExtractionRejected("locale must be one of en, it, fr, es")
    if not 0 <= padding_seconds <= 0.15:
        raise ExtractionRejected("per-side cut padding must be between 0 and 0.15 seconds")
    source_resolved = source.resolve(strict=True)
    destination_resolved = destination.resolve(strict=False)
    source_receipt = source_receipt_path or source.with_suffix(source.suffix + ".receipt.json")
    if source_resolved == destination_resolved or _same_file_path(source, destination):
        raise ExtractionRejected("source and output resolve to the same file")
    if source_receipt_path is not None and not source_receipt_path.is_file():
        raise ExtractionRejected(f"explicit provider receipt does not exist: {source_receipt_path}")
    if source_receipt.exists() and _same_file_path(source_receipt, source):
        raise ExtractionRejected("provider receipt aliases the source WAV")
    source_receipt_sha256 = sha256(source_receipt) if source_receipt.is_file() else None
    source_request: dict[str, Any] = {}
    if source_receipt_sha256:
        try:
            source_data = json.loads(source_receipt.read_text(encoding="utf-8"))
            if not isinstance(source_data, dict) or not isinstance(source_data.get("request", {}), dict):
                raise ValueError("receipt schema is not an object")
            source_request = source_data.get("request", {})
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise ExtractionRejected(f"provider receipt is unreadable or malformed: {exc}") from exc
    rate, channels, samples = _read_pcm16(source)
    duration = len(samples) / rate
    raw_result = transcriber(source, locale)
    try:
        timings, prefix_count, raw_target_match, raw_transcript_words, raw_aligned_words = validate_transcript_and_boundary(
            raw_result, prefix, target, remove_first_words, target_verification,
            duration_seconds=duration, ignore_accents=ignore_accents,
        )
    except ExtractionRejected as exc:
        exc.evidence.setdefault("raw_transcript", raw_result.get("text", ""))
        exc.evidence.setdefault("raw_word_alignment", _raw_word_alignment_evidence(raw_result))
        raise
    if any(timing.end > duration for timing in timings):
        raise ExtractionRejected("ASR word timestamp extends beyond raw WAV duration")
    prefix_end = timings[prefix_count - 1].end
    target_start = timings[prefix_count].start
    # First try the inter-word interval. If Whisper attributes the real pause
    # to an adjacent word, search both boundary spans, then demand an exact
    # independent retained-target transcript. Never verify discarded speech.
    expanded_boundary = False
    search_start, search_end = prefix_end, target_start
    try:
        gap = measure_gap(samples, rate, search_start, search_end)
    except ExtractionRejected:
        expanded_boundary = True
        search_start = timings[prefix_count - 1].start
        search_end = timings[prefix_count].end
        try:
            gap = measure_gap(samples, rate, search_start, search_end)
        except ExtractionRejected as exc:
            exc.evidence.update({"raw_transcript": raw_result.get("text", ""),
                                 "raw_word_alignment": _raw_word_alignment_evidence(raw_result),
                                 "target_boundary_index": prefix_count})
            raise
    cut_time = (gap.run_start_seconds + gap.run_end_seconds) / 2
    if cut_time <= search_start or cut_time >= search_end or min(
        cut_time - gap.run_start_seconds, gap.run_end_seconds - cut_time
    ) < padding_seconds:
        raise ExtractionRejected("safe deterministic cut point is outside the verified gap")
    cut_sample = round(cut_time * rate)
    if cut_sample <= 0 or cut_sample >= len(samples):
        raise ExtractionRejected("computed cut sample is outside source audio")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".wav", dir=destination.parent
    )
    os.close(descriptor)
    temporary_output = Path(temporary_name)
    try:
        # Exact PCM sample slice: stable and auditable; FFmpeg is not involved.
        with wave.open(str(temporary_output), "wb") as output:
            output.setnchannels(channels)
            output.setsampwidth(2)
            output.setframerate(rate)
            output.writeframes(_pcm16_bytes(samples[cut_sample:]))
        extracted_result = transcriber(temporary_output, locale)
        extracted_rate, _, extracted_samples = _read_pcm16(temporary_output)
        extracted_text, extracted_timings = parse_word_timings(
            extracted_result, duration_seconds=len(extracted_samples) / extracted_rate
        )
        extracted_transcript_words = spoken_words(str(extracted_result.get("text", "")))
        if not extracted_timings:
            raise ExtractionRejected("extracted clip has no word-level ASR timestamps")
        expected_comparison = comparison_words(target, ignore_accents=ignore_accents)
        extracted_target_match = (comparison_words(extracted_text, ignore_accents=ignore_accents) == expected_comparison
                                  and comparison_words(str(extracted_result.get("text", "")), ignore_accents=ignore_accents) == expected_comparison)
        if expanded_boundary and not extracted_target_match:
            raise ExtractionRejected(
                "expanded boundary search requires an exact extracted target",
                evidence={"extracted_transcript": extracted_result.get("text", "")},
            )
        if not extracted_target_match and target_verification == "required":
            raise ExtractionRejected("extracted-clip ASR does not exactly match the target")
        frame = max(1, round(extracted_rate * 0.01))
        voiced_frames = 0
        for offset in range(0, len(extracted_samples), frame):
            chunk = extracted_samples[offset:offset + frame]
            if not chunk:
                continue
            rms = math.sqrt(sum(value * value for value in chunk) / len(chunk))
            if rms / 32768.0 >= 10 ** (-42.0 / 20):
                voiced_frames += 1
        voiced_seconds = voiced_frames * 0.01
        minimum_voiced_seconds = GAP_POLICY["minimum_extracted_voiced_seconds"]
        if voiced_seconds < minimum_voiced_seconds:
            raise ExtractionRejected(
                "extracted audio has insufficient voiced duration above the -42 dBFS RMS floor "
                f"({voiced_seconds:.3f}s < {minimum_voiced_seconds:.3f}s)"
            )
        # Preserve any pre-existing destination until both ASR checks have passed.
        temporary_output.replace(destination)
    except BaseException:
        temporary_output.unlink(missing_ok=True)
        raise
    whisper_version = _package_version("mlx-whisper")
    model_revision = _cached_model_revision()
    return {
        "algorithm_version": ALGORITHM_VERSION,
        "gap_policy": GAP_POLICY,
        "schema_version": 1,
        "status": ("EXTRACTED_PENDING_LISTENING" if raw_target_match and extracted_target_match
                   else "EXTRACTED_TARGET_WARN_PENDING_LISTENING"),
        "source": str(source),
        "source_sha256": sha256(source),
        "output": str(destination),
        "output_sha256": sha256(destination),
        "target_request": {
            "speaker": source_request.get("speaker"),
            "kind": source_request.get("kind"),
            "text": target,
            "locale": locale,
            "cue_id": source_request.get("cue_id"),
            "source_provider_receipt": str(source_receipt) if source_receipt_sha256 else None,
            "source_provider_receipt_sha256": source_receipt_sha256,
        },
        "locale": locale,
        "prefix": prefix,
        "target": target,
        "remove_first_words": remove_first_words,
        "target_verification_policy": target_verification,
        "recognizer": DEFAULT_ASR_VERIFIER + "-word-timestamps",
        "recognizer_version": whisper_version,
        "model_id": DEFAULT_ASR_MODEL,
        "model_revision": model_revision,
        "transcription_settings": {
            "word_timestamps": True,
            "initial_prompt": None,
            "temperature": 0.0,
            "condition_on_previous_text": False,
        },
        "ignore_accents": ignore_accents,
        "normalization_policy": "NFC/casefold/apostrophe word tokens; " + ("comparison diacritics ignored" if ignore_accents else "strict accents"),
        "model_source": "installed-code-and-cached-weights-only;offline",
        "raw_transcript": raw_result.get("text", ""),
        "removed_prefix_transcript": None,
        "removed_prefix_word_alignment": None,
        "extracted_transcript": extracted_result.get("text", ""),
        "raw_word_alignment": [
            {"word": item.token, "start_seconds": item.start, "end_seconds": item.end}
            for item in timings
        ],
        "extracted_word_alignment": [
            {"word": item.token, "start_seconds": item.start, "end_seconds": item.end}
            for item in extracted_timings
        ],
        "raw_asr_scores": _asr_score_evidence(raw_result),
        "extracted_asr_scores": _asr_score_evidence(extracted_result),
        "raw_prefix_exact_match": raw_aligned_words[:prefix_count] == spoken_words(prefix),
        "intro_verification_policy": "ignored-disposable-intro",
        "target_alignment_policy": "final-suffix-exact-or-warn-similarity-at-least-0.8",
        "recognized_intro_word_count": prefix_count,
        "raw_target_exact_match": raw_target_match,
        "extracted_target_exact_match": extracted_target_match,
        "target_verification_warning": not (raw_target_match and extracted_target_match),
        "extracted_voiced_frames": voiced_frames,
        "extracted_voiced_seconds": round(voiced_seconds, 3),
        "unremoved_raw_target_tokens": raw_transcript_words[-len(spoken_words(target)):],
        "unremoved_raw_aligned_tokens": raw_aligned_words[prefix_count:],
        "raw_transcript_alignment_suffix_match": raw_transcript_words[-len(spoken_words(target)):] == raw_aligned_words[prefix_count:],
        "duration_seconds": duration,
        "sample_rate": rate,
        "boundary": {
            "search_strategy": "target-suffix-expanded-boundary" if expanded_boundary else "target-suffix-inter-word-gap",
            "search_start_seconds": search_start,
            "search_end_seconds": search_end,
            "prefix_last_word_end_seconds": prefix_end,
            "target_first_word_start_seconds": target_start,
            "gap_seconds": gap.duration_seconds,
            "verified_silence_start_seconds": gap.run_start_seconds,
            "verified_silence_end_seconds": gap.run_end_seconds,
            "gap_rms_dbfs": round(gap.rms_dbfs, 3),
            "gap_peak_dbfs": round(gap.peak_dbfs, 3),
            "gap_quiet_fraction": round(gap.quiet_fraction, 4),
            "padding_seconds": padding_seconds,
            "cut_time_seconds": cut_time,
            "cut_sample": cut_sample,
            "cut_policy": "midpoint of the unique guarded low-energy PCM run between timestamped prefix and target word spans",
        },
        "evidence_boundary": (
            "ASR transcript/timestamps are probabilistic. PCM gap metrics and deterministic sample cut are "
            "technical evidence only; independent human listening remains required."
        ),
        "human_review": "PENDING",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--locale", required=True, choices=("en", "it", "fr", "es"))
    parser.add_argument("--prefix", required=True, help="Exact spoken carrier transcript")
    parser.add_argument("--target", required=True, help="Exact spoken target transcript")
    parser.add_argument("--remove-first-words", required=True, type=int)
    parser.add_argument("--target-verification", choices=("required", "warn"), default="required",
                        help="warn records ASR target mismatch while retaining strict prefix and acoustic-boundary gates")
    parser.add_argument("--receipt", type=Path, help="Extraction evidence JSON path; defaults beside output")
    parser.add_argument("--strict-accents", action="store_true", help="require matching ASR diacritics")
    parser.add_argument("--source-receipt", type=Path, help="Optional original VoiceEngine receipt path")
    args = parser.parse_args(argv)
    receipt_path = args.receipt or args.output.with_suffix(args.output.suffix + ".receipt.json")
    source_receipt = args.source_receipt or args.source.with_suffix(args.source.suffix + ".receipt.json")
    unsafe_paths = [args.source, args.output, receipt_path, source_receipt]
    aliases = [
        (unsafe_paths[i], unsafe_paths[j])
        for i in range(len(unsafe_paths))
        for j in range(i + 1, len(unsafe_paths))
        if _same_file_path(unsafe_paths[i], unsafe_paths[j])
    ]
    try:
        if aliases:
            raise ExtractionRejected("source, output, target receipt and provider receipt must be distinct files")
        if args.output.exists():
            raise ExtractionRejected(f"refusing to overwrite existing output: {args.output}")
        if receipt_path.exists():
            raise ExtractionRejected(f"refusing to overwrite existing target receipt: {receipt_path}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        if not os.access(args.output.parent, os.W_OK) or not os.access(receipt_path.parent, os.W_OK):
            raise ExtractionRejected("output or receipt directory is not writable")
        stage_fd, stage_name = tempfile.mkstemp(
            prefix=f".{args.output.name}.", suffix=".wav", dir=args.output.parent
        )
        os.close(stage_fd)
        staged_output = Path(stage_name)
        staged_output.unlink()
        temporary_receipt = receipt_path.with_suffix(receipt_path.suffix + ".tmp")
        try:
            receipt = extract(
                args.source, staged_output, locale=args.locale, prefix=args.prefix,
                target=args.target, remove_first_words=args.remove_first_words,
                source_receipt_path=args.source_receipt,
                target_verification=args.target_verification, ignore_accents=not args.strict_accents,
            )
            receipt["output"] = str(args.output)
            receipt["output_sha256"] = sha256(staged_output)
            receipt["receipt_path"] = str(receipt_path)
            temporary_receipt.write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            staged_output.replace(args.output)
            try:
                temporary_receipt.replace(receipt_path)
            except BaseException:
                args.output.unlink(missing_ok=True)
                raise
        except BaseException:
            staged_output.unlink(missing_ok=True)
            temporary_receipt.unlink(missing_ok=True)
            raise
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0
    except ExtractionRejected as exc:
        rejected = {
            "algorithm_version": ALGORITHM_VERSION,
            "status": "REJECTED",
            "source": str(args.source),
            "source_sha256": sha256(args.source) if args.source.is_file() else None,
            "output": str(args.output),
            "locale": args.locale,
            "prefix": args.prefix,
            "target": args.target,
            "remove_first_words": args.remove_first_words,
            "recognizer": DEFAULT_ASR_VERIFIER + "-word-timestamps",
            "ignore_accents": not args.strict_accents,
            "recognizer_version": _package_version("mlx-whisper"),
            "model_id": DEFAULT_ASR_MODEL,
            "model_revision": _cached_model_revision(),
            "transcription_settings": {
                "word_timestamps": True,
                "initial_prompt": None,
                "temperature": 0.0,
                "condition_on_previous_text": False,
            },
            "reason": str(exc),
            "partial_evidence": exc.evidence,
            "human_review": "PENDING",
            "evidence_boundary": "No extraction was accepted; ASR/alignment and PCM screens are technical evidence only.",
        }
        failure_path = receipt_path.with_suffix(receipt_path.suffix + ".rejected.json")
        if any(_same_file_path(failure_path, path) for path in unsafe_paths) or failure_path.exists():
            print(json.dumps(rejected, ensure_ascii=False, indent=2), file=sys.stderr)
            return 2
        try:
            failure_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_receipt = failure_path.with_suffix(failure_path.suffix + ".tmp")
            temporary_receipt.write_text(json.dumps(rejected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary_receipt.replace(failure_path)
            rejected["receipt_path"] = str(failure_path)
        except OSError:
            print(json.dumps(rejected, ensure_ascii=False, indent=2), file=sys.stderr)
            return 2
        print(json.dumps(rejected, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
