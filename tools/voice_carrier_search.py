#!/usr/bin/env python3
"""Experimental target-only search for a safe spoken-carrier cut.

This separately versioned prototype searches waveform quiet runs and asks the
installed Base recognizer to transcribe each retained suffix independently.
It does not inspect or require an ASR transcript of the disposable intro.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import uuid
import wave
from typing import Any, Callable, Sequence

from greia_voice_core.asr_policy import (
    DEFAULT_ASR_MODEL,
    DEFAULT_ASR_REVISION,
    DEFAULT_ASR_VERIFIER,
)
from greia_voice_core.number_comparison import (
    COMPARISON_POLICY,
    SUPPORTED_COMPARISON_POLICIES,
    canonical_number_tokens,
    compare_target_transcript,
)
from voice_carrier import (
    ExtractionRejected,
    _cached_model_revision,
    _package_version,
    _pcm16_bytes,
    _read_pcm16,
    _same_file_path,
    _whisper_transcribe,
    sha256,
    spoken_words,
)

ALGORITHM_VERSION = "greia-spoken-carrier-extractor-v7"
CONTEXT_ALGORITHM_VERSION = "greia-spoken-carrier-extractor-v7-saved-wav-context-v1"
MAX_CANDIDATES = 6
MAX_CLIP_SECONDS = 120
FRAME_MS = 10
MIN_QUIET_RUN_SECONDS = 0.20
MIN_RUN_START_SECONDS = 0.35
MIN_FOLLOWING_PCM_SECONDS = 0.12
CUT_PADDING_SECONDS = 0.10
MIN_VOICED_SECONDS = 0.08
MAX_FRAME_RMS_DBFS = -42.0
MAX_FRAME_PEAK_DBFS = -30.0


class CandidateTranscriptionError(RuntimeError):
    """Fatal ASR uncertainty; callers must not spend another synthesis attempt."""

    def __init__(self, message: str, *, evidence: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.evidence = evidence or {}


def _validate_parameters(
    source: Path,
    destination: Path,
    *,
    locale: str,
    prefix: str,
    target: str,
    remove_first_words: int,
    padding_seconds: float,
    source_receipt_path: Path | None,
    target_verification: str,
    ignore_accents: bool,
    comparison_policy: str,
) -> tuple[Path, Path | None]:
    """Validate the public v6-compatible call shape before touching output."""
    if not isinstance(locale, str) or locale not in {"en", "it", "fr", "es"}:
        raise ExtractionRejected("locale must be one of en, it, fr, es")
    if not isinstance(source, Path) or not isinstance(destination, Path):
        raise ExtractionRejected("source and destination must be pathlib.Path values")
    if not isinstance(prefix, str) or not isinstance(target, str):
        raise ExtractionRejected("prefix and target must be strings")
    prefix_words = spoken_words(prefix)
    target_words = spoken_words(target)
    if not prefix_words or not target_words:
        raise ExtractionRejected("prefix and target must both contain spoken words")
    if isinstance(remove_first_words, bool) or not isinstance(remove_first_words, int):
        raise ExtractionRejected("remove_first_words must be an integer")
    if remove_first_words != len(prefix_words):
        raise ExtractionRejected(
            f"remove-first-words={remove_first_words} disagrees with prefix word count {len(prefix_words)}"
        )
    if isinstance(padding_seconds, bool) or not isinstance(padding_seconds, (int, float)):
        raise ExtractionRejected("padding_seconds must be numeric")
    if not math.isfinite(float(padding_seconds)) or float(padding_seconds) != CUT_PADDING_SECONDS:
        raise ExtractionRejected("v7 uses fixed 0.10 second cut padding")
    if not isinstance(target_verification, str) or target_verification not in {"required", "warn"}:
        raise ExtractionRejected("target verification must be required or warn")
    if not isinstance(ignore_accents, bool):
        raise ExtractionRejected("ignore_accents must be a boolean")

    if comparison_policy not in SUPPORTED_COMPARISON_POLICIES:
        raise ExtractionRejected("unsupported comparison policy")
    try:
        prefix_units = canonical_number_tokens(locale, prefix, ignore_accents=ignore_accents, policy=comparison_policy)
        target_units = canonical_number_tokens(locale, target, ignore_accents=ignore_accents, policy=comparison_policy)
    except (TypeError, ValueError) as exc:
        raise ExtractionRejected(f"invalid target comparison configuration: {exc}") from exc
    if not prefix_units or not target_units:
        raise ExtractionRejected("prefix and target must have canonical comparison units")
    width = len(target_units)
    if any(prefix_units[i:i + width] == target_units for i in range(len(prefix_units) - width + 1)):
        raise ExtractionRejected("target units occur contiguously in prefix; target-only search is unsafe")

    try:
        source_resolved = source.resolve(strict=True)
        destination_resolved = destination.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise ExtractionRejected(f"source or destination path is invalid: {exc}") from exc
    if source_resolved == destination_resolved or _same_file_path(source, destination):
        raise ExtractionRejected("source and output resolve to the same file")
    receipt = source_receipt_path
    if receipt is not None:
        if not receipt.is_file():
            raise ExtractionRejected(f"explicit provider receipt does not exist: {receipt}")
        if _same_file_path(receipt, source) or _same_file_path(receipt, destination):
            raise ExtractionRejected("provider receipt aliases source or destination")
    return source_resolved, receipt


def _quiet_runs(samples: Sequence[int], rate: int) -> list[dict[str, Any]]:
    """Return globally measured contiguous low-energy PCM runs in sample units."""
    frame_samples = max(1, round(rate * FRAME_MS / 1000))
    runs: list[dict[str, Any]] = []
    active_start: int | None = None
    active_end = 0

    def finish_run() -> None:
        nonlocal active_start, active_end
        if active_start is None:
            return
        duration = (active_end - active_start) / rate
        start_seconds = active_start / rate
        if (duration >= MIN_QUIET_RUN_SECONDS
                and start_seconds >= MIN_RUN_START_SECONDS
                and (len(samples) - active_end) / rate >= MIN_FOLLOWING_PCM_SECONDS):
            runs.append({
                "start_sample": active_start,
                "end_sample": active_end,
                "start_seconds": start_seconds,
                "end_seconds": active_end / rate,
                "duration_seconds": duration,
            })
        active_start = None
        active_end = 0

    for offset in range(0, len(samples) - frame_samples + 1, frame_samples):
        frame = samples[offset:offset + frame_samples]
        if len(frame) != frame_samples:
            continue
        peak = max(abs(value) for value in frame)
        rms = math.sqrt(sum(value * value for value in frame) / frame_samples)
        rms_db = -120.0 if rms == 0 else 20.0 * math.log10(rms / 32768.0)
        peak_db = -120.0 if peak == 0 else 20.0 * math.log10(peak / 32768.0)
        quiet = rms_db <= MAX_FRAME_RMS_DBFS and peak_db <= MAX_FRAME_PEAK_DBFS
        if quiet:
            if active_start is None:
                active_start = offset
            active_end = offset + frame_samples
        else:
            finish_run()
    finish_run()
    return runs


def _voiced_seconds(samples: Sequence[int], rate: int) -> float:
    """Count bounded 10 ms PCM frames above the existing -42 dBFS RMS floor."""
    frame_samples = max(1, round(rate * FRAME_MS / 1000))
    voiced = 0
    for offset in range(0, len(samples), frame_samples):
        frame = samples[offset:offset + frame_samples]
        if not frame:
            continue
        rms = math.sqrt(sum(value * value for value in frame) / len(frame))
        db = -120.0 if rms == 0 else 20.0 * math.log10(rms / 32768.0)
        if db >= MAX_FRAME_RMS_DBFS:
            voiced += 1
    return voiced * FRAME_MS / 1000.0


def _write_pcm(path: Path, samples: Sequence[int], rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(_pcm16_bytes(samples))


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def extract(
    source: Path,
    destination: Path,
    *,
    locale: str,
    prefix: str,
    target: str,
    remove_first_words: int,
    transcriber: Callable[[Path, str], dict[str, Any]] = _whisper_transcribe,
    padding_seconds: float = CUT_PADDING_SECONDS,
    source_receipt_path: Path | None = None,
    target_verification: str = "required",
    ignore_accents: bool = True,
    comparison_policy: str = COMPARISON_POLICY,
    candidate_verifier=None,
) -> dict[str, Any]:
    """Extract one unique number-aware exact target from verified PCM gaps.

    By default no raw-intro transcription is requested. An explicitly injected
    saved-WAV verifier may hear a reconstructed prefix, without requiring intro
    correctness; its metadata and algorithm version are separate. Each candidate is
    transcribed independently without an expected-text prompt. Required mode
    accepts an exact canonical-token match. Warn mode accepts a score above
    0.8 only when canonical token count and numeric sequence still match.
    """
    # Opt-in only: no normal engine or corpus caller injects this collaborator.
    from greia_voice_core.contextual_target import CONTEXT_VERIFICATION_POLICY
    if candidate_verifier is not None and (not callable(candidate_verifier) or
            getattr(candidate_verifier, "policy_id", None) != CONTEXT_VERIFICATION_POLICY):
        raise ExtractionRejected("unsupported candidate verification collaborator")
    algorithm = CONTEXT_ALGORITHM_VERSION if candidate_verifier is not None else ALGORITHM_VERSION
    intro_asr = ("prefix-heard-on-fallback; wording-agreement-not-required"
                 if candidate_verifier is not None else "not-run-disposable-intro")
    if not isinstance(destination, Path):
        raise ExtractionRejected("destination must be a pathlib.Path value")
    search_root = destination.with_name(destination.name + ".search")
    search_root.mkdir(parents=True, exist_ok=True)
    run_dir = search_root / uuid.uuid4().hex
    run_dir.mkdir()
    report_path = run_dir / "search.json"
    report: dict[str, Any] = {
        "algorithm_version": algorithm,
        "comparison_policy": comparison_policy,
        "status": "SEARCHING",
        "source": str(source),
        "destination": str(destination),
        "source_receipt": str(source_receipt_path) if source_receipt_path else None,
        "locale": locale,
        "prefix": prefix,
        "target": target,
        "remove_first_words": remove_first_words,
        "target_verification_requested": target_verification,
        "target_verification_policy": (
            "canonical-token-exact" if target_verification == "required"
            else "similarity-greater-than-0.8-with-same-word-count-and-numeric-sequence"
        ),
        "ignore_accents": ignore_accents,
        "search_policy": {
            "frame_ms": FRAME_MS,
            "min_quiet_run_seconds": MIN_QUIET_RUN_SECONDS,
            "min_run_start_seconds": MIN_RUN_START_SECONDS,
            "min_following_pcm_seconds": MIN_FOLLOWING_PCM_SECONDS,
            "cut_padding_seconds": CUT_PADDING_SECONDS,
            "min_voiced_seconds_each_side": MIN_VOICED_SECONDS,
            "max_frame_rms_dbfs": MAX_FRAME_RMS_DBFS,
            "max_frame_peak_dbfs": MAX_FRAME_PEAK_DBFS,
            "candidate_cap": MAX_CANDIDATES,
            "selection": "longest-runs-then-time-order; exact-match cardinality must be one",
        },
        "raw_intro_asr": intro_asr,
        "candidate_results": [],
        "human_review": "PENDING",
        "evidence_boundary": "Recognizer and PCM checks are screening evidence only; human listening remains required.",
    }
    temp_output: Path | None = None
    try:
        source_resolved, receipt_path = _validate_parameters(
            source, destination, locale=locale, prefix=prefix, target=target,
            remove_first_words=remove_first_words, padding_seconds=padding_seconds,
            source_receipt_path=source_receipt_path, target_verification=target_verification,
            ignore_accents=ignore_accents, comparison_policy=comparison_policy,
        )
        report["source"] = str(source_resolved)
        report["destination"] = str(destination.resolve(strict=False))
        report["source_receipt"] = str(receipt_path) if receipt_path else None
        report["expected_target_tokens"] = list(canonical_number_tokens(locale, target, ignore_accents=ignore_accents, policy=comparison_policy))

        if receipt_path is not None:
            try:
                provider_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                if not isinstance(provider_receipt, dict):
                    raise ValueError("receipt root is not an object")
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                raise ExtractionRejected(f"provider receipt is unreadable or malformed: {exc}") from exc
            report["source_provider_receipt_sha256"] = sha256(receipt_path)
        rate, channels, samples = _read_pcm16(source_resolved)
        duration = len(samples) / rate
        if not (0 < duration <= MAX_CLIP_SECONDS):
            raise ExtractionRejected(f"input duration must be in (0, {MAX_CLIP_SECONDS}] seconds")
        source_sha = sha256(source_resolved)
        report.update({"source_sha256": source_sha, "sample_rate": rate, "channels": channels,
                       "duration_seconds": duration, "raw_intro_asr": intro_asr})
        runs = _quiet_runs(samples, rate)
        selected = sorted(runs, key=lambda run: (-run["duration_seconds"], run["start_sample"]))[:MAX_CANDIDATES]
        selected.sort(key=lambda run: run["start_sample"])
        report["qualifying_quiet_run_count"] = len(runs)
        report["qualifying_quiet_runs"] = runs
        report["candidate_run_selection"] = selected
        target_tokens = canonical_number_tokens(locale, target, ignore_accents=ignore_accents, policy=comparison_policy)
        candidates: list[dict[str, Any]] = []
        qualifying_matches: list[dict[str, Any]] = []

        # Materialize at most six deterministic suffixes before ASR. This keeps
        # evidence on reject while avoiding any recognizer call when the global
        # run count already exceeds the ambiguity-search bound.
        for index, run in enumerate(selected, start=1):
            cut_sample = run["end_sample"] - round(CUT_PADDING_SECONDS * rate)
            candidate_path = run_dir / f"candidate-{index:02}.wav"
            item: dict[str, Any] = {
                "candidate_id": f"candidate-{index:02}",
                "quiet_run": run,
                "cut_sample": cut_sample,
                "cut_time_seconds": cut_sample / rate,
                "candidate_path": str(candidate_path),
            }
            candidates.append(item)
            report["candidate_results"] = candidates
            try:
                if cut_sample <= 0 or cut_sample >= len(samples):
                    raise ExtractionRejected("candidate cut sample is outside source PCM")
                before_voiced = _voiced_seconds(samples[:cut_sample], rate)
                suffix = samples[cut_sample:]
                suffix_voiced = _voiced_seconds(suffix, rate)
                item.update({"preceding_voiced_seconds": round(before_voiced, 3),
                             "retained_voiced_seconds": round(suffix_voiced, 3),
                             "retained_duration_seconds": len(suffix) / rate})
                if before_voiced < MIN_VOICED_SECONDS:
                    raise ExtractionRejected("insufficient energetic speech before candidate boundary")
                if suffix_voiced < MIN_VOICED_SECONDS:
                    raise ExtractionRejected("insufficient voiced duration in retained suffix")
                _write_pcm(candidate_path, suffix, rate)
                item["candidate_sha256"] = sha256(candidate_path)
            except ExtractionRejected as exc:
                item.update({"error": str(exc), "exact_target_match": False})
            _save_json(report_path, report)

        if len(runs) > MAX_CANDIDATES:
            raise ExtractionRejected(
                f"{len(runs)} qualifying quiet runs exceed bounded candidate cap {MAX_CANDIDATES}",
                evidence={"qualifying_quiet_run_count": len(runs), "candidate_cap": MAX_CANDIDATES},
            )
        ineligible = [item for item in candidates if "error" in item]
        if ineligible:
            raise ExtractionRejected(
                "one or more quiet-run candidates failed the energetic-signal floor",
                evidence={"candidate_errors": [item["error"] for item in ineligible]},
            )

        for item in candidates:
            candidate_path = Path(item["candidate_path"])
            try:
                # No expected-text prompt is supplied. Every retained suffix is
                # independently screened by the installed Base transcriber.
                result = (transcriber(candidate_path, locale) if candidate_verifier is None else
                          candidate_verifier(source_resolved, candidate_path,
                              cut_sample=item["cut_sample"], locale=locale, target=target,
                              ignore_accents=ignore_accents, comparison_policy=comparison_policy))
                if candidate_verifier is not None:
                    quality = result.get("candidate_quality") if isinstance(result, dict) else None
                    if (not isinstance(quality, dict) or
                            quality.get("verification_strategy") != CONTEXT_VERIFICATION_POLICY or
                            quality.get("disposition") not in {"PASS", "WARN"} or
                            not isinstance(quality.get("flags"), list) or
                            quality.get("transcript") != result.get("text")):
                        raise ValueError("malformed candidate verification evidence")
                    item["candidate_quality"] = quality
            except Exception as exc:
                item.update({"transcription_error": str(exc), "exact_target_match": False})
                report["candidate_results"] = candidates
                _save_json(report_path, report)
                raise CandidateTranscriptionError(
                    f"Base transcription failed for {item['candidate_id']}: {exc}",
                    evidence={"candidate_id": item["candidate_id"], "candidate_path": str(candidate_path)},
                ) from exc
            if not isinstance(result, dict) or not isinstance(result.get("text"), str):
                item.update({"transcription_error": "Base recognizer returned malformed transcript",
                             "exact_target_match": False})
                report["candidate_results"] = candidates
                _save_json(report_path, report)
                raise CandidateTranscriptionError(
                    "Base recognizer returned malformed transcript",
                    evidence={"candidate_id": item["candidate_id"], "candidate_path": str(candidate_path)},
                )
            transcript = result["text"].strip()
            comparison = compare_target_transcript(
                locale, target, transcript, ignore_accents=ignore_accents, policy=comparison_policy
            )
            exact = comparison.exact_match
            if target_verification == "required":
                qualifies = exact
                effective_policy = "canonical-token-exact"
            else:
                qualifies = (
                    comparison.score > 0.8
                    and comparison.word_count_matches
                    and comparison.numbers_match
                )
                effective_policy = "similarity>0.8+same-word-count+same-numeric-sequence"
            if candidate_verifier is not None:
                qualifies = qualifies and quality["disposition"] == "PASS" and not quality["flags"]
            segments = result.get("segments", [])
            item.update({
                "extracted_transcript": transcript,
                "canonical_transcript_tokens": list(comparison.actual_tokens),
                "exact_target_match": exact,
                "target_comparison_score": comparison.score,
                "target_word_count_matches": comparison.word_count_matches,
                "target_numbers_match": comparison.numbers_match,
                "target_comparison_flags": comparison.flags(require_word_count=True),
                "target_verification_requested": target_verification,
                "target_verification_effective_policy": effective_policy,
                "target_verification_qualifies": qualifies,
                "asr_segment_count": len(segments) if isinstance(segments, list) else None,
            })
            if qualifies:
                qualifying_matches.append(item)
            _save_json(report_path, report)

        if len(qualifying_matches) != 1:
            raise ExtractionRejected(
                "no candidate suffix meets target verification policy" if not qualifying_matches
                else "multiple candidate suffixes meet target verification policy",
                evidence={
                    "candidate_transcripts": [item.get("extracted_transcript", "") for item in candidates],
                    "matching_candidate_ids": [item["candidate_id"] for item in qualifying_matches],
                },
            )

        chosen = qualifying_matches[0]
        chosen_path = Path(chosen["candidate_path"])
        extracted_transcript = chosen["extracted_transcript"]
        output_sha = sha256(chosen_path)
        output_size = chosen_path.stat().st_size
        boundary = {
            "search_strategy": "target-only-global-quiet-run-v7",
            "verified_silence_start_seconds": chosen["quiet_run"]["start_seconds"],
            "verified_silence_end_seconds": chosen["quiet_run"]["end_seconds"],
            "verified_silence_duration_seconds": chosen["quiet_run"]["duration_seconds"],
            "cut_sample": chosen["cut_sample"],
            "cut_time_seconds": chosen["cut_time_seconds"],
            "padding_seconds": CUT_PADDING_SECONDS,
            "quiet_run_start_sample": chosen["quiet_run"]["start_sample"],
            "quiet_run_end_sample": chosen["quiet_run"]["end_sample"],
            "cut_policy": "100 ms before the end of the unique qualifying low-energy PCM run",
        }
        recognizer_owner = getattr(transcriber, "__self__", transcriber)
        selected_recognizer = getattr(recognizer_owner, "verifier_id", DEFAULT_ASR_VERIFIER)
        selected_model = getattr(recognizer_owner, "model_id", DEFAULT_ASR_MODEL)
        selected_revision = getattr(recognizer_owner, "model_revision", None)
        is_parakeet = selected_recognizer == "mlx-audio-parakeet-tdt-v3"
        receipt: dict[str, Any] = {
            "schema_version": 1,
            "algorithm_version": algorithm,
            "comparison_policy": comparison_policy,
            "status": "EXTRACTED_PENDING_LISTENING",
            "source": str(source_resolved),
            "source_sha256": source_sha,
            "output": str(destination),
            "output_sha256": output_sha,
            "output_bytes": output_size,
            "locale": locale,
            "prefix": prefix,
            "target": target,
            "remove_first_words": remove_first_words,
            "ignore_accents": ignore_accents,
            "target_verification_requested": target_verification,
            "target_verification_policy": (
                "canonical-token-exact" if target_verification == "required"
                else "similarity-greater-than-0.8-with-same-word-count-and-numeric-sequence"
            ),
            "target_comparison_score": chosen["target_comparison_score"],
            "target_word_count_matches": chosen["target_word_count_matches"],
            "target_numbers_match": chosen["target_numbers_match"],
            "target_comparison_flags": chosen["target_comparison_flags"],
            "target_transcript_warning": not chosen["exact_target_match"],
            "recognizer": selected_recognizer,
            "recognizer_version": _package_version("mlx-audio" if is_parakeet else "mlx-whisper"),
            "model_id": selected_model,
            "model_revision": selected_revision or (_cached_model_revision() or DEFAULT_ASR_REVISION),
            "extracted_transcript": extracted_transcript,
            "expected_target_tokens": list(target_tokens),
            "extracted_target_tokens": chosen["canonical_transcript_tokens"],
            "extracted_target_exact_match": chosen["exact_target_match"],
            "transcription_settings": ({
                "language_detection": "automatic",
                "expected_text_prompt": None,
                "timestamps": "model-provided-token-timestamps",
            } if is_parakeet else {
                "language": locale,
                "initial_prompt": None,
                "word_timestamps": True,
                "temperature": 0.0,
                "condition_on_previous_text": False,
            }),
            "sample_rate": rate,
            "duration_seconds": duration,
            "boundary": boundary,
            "search_evidence_dir": str(run_dir),
            "search_evidence_json": str(report_path),
            "source_provider_receipt": str(receipt_path) if receipt_path else None,
            "source_provider_receipt_sha256": report.get("source_provider_receipt_sha256"),
            "candidate_sha256": output_sha,
            "candidate_id": chosen["candidate_id"],
            "candidate_count": len(candidates),
            "qualifying_quiet_run_count": len(runs),
            "candidate_results": candidates,
            "human_review": "PENDING",
            "evidence_boundary": "Base transcript and PCM cut evidence are screening only; human listening remains required.",
        }
        if candidate_verifier is not None:
            receipt.update(candidate_verification_policy=CONTEXT_VERIFICATION_POLICY,
                           selected_candidate_quality=chosen["candidate_quality"], raw_intro_asr=intro_asr)
        report.update({"status": "VALIDATED_CANDIDATE_READY", "chosen_candidate_id": chosen["candidate_id"],
                       "output": str(destination), "output_sha256": output_sha, "receipt": receipt})
        _save_json(report_path, report)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
        os.close(fd)
        temp_output = Path(temp_name)
        temp_output.write_bytes(chosen_path.read_bytes())
        if hashlib.sha256(temp_output.read_bytes()).hexdigest() != output_sha:
            raise ExtractionRejected("candidate copy hash changed before publication")
        temp_output.replace(destination)
        temp_output = None
        report.update({"status": "EXTRACTED_PENDING_LISTENING"})
        try:
            _save_json(report_path, report)
        except OSError as exc:
            # Publication already succeeded atomically; return the actual take
            # rather than report rejection while leaving a changed destination.
            receipt["search_evidence_update_warning"] = str(exc)
        return receipt
    except CandidateTranscriptionError as exc:
        if temp_output is not None:
            temp_output.unlink(missing_ok=True)
        report.update({"status": "ASR_ERROR", "rejection": str(exc),
                       "rejection_evidence": exc.evidence})
        try:
            _save_json(report_path, report)
        except OSError:
            pass
        exc.evidence.setdefault("search_evidence_dir", str(run_dir))
        exc.evidence.setdefault("search_evidence_json", str(report_path))
        raise
    except Exception as exc:
        if temp_output is not None:
            temp_output.unlink(missing_ok=True)
        report.update({"status": "REJECTED" if isinstance(exc, ExtractionRejected) else "ERROR",
                       "rejection": str(exc)})
        if isinstance(exc, ExtractionRejected):
            report["rejection_evidence"] = exc.evidence
        try:
            _save_json(report_path, report)
        except OSError:
            pass
        if isinstance(exc, ExtractionRejected):
            exc.evidence.setdefault("search_evidence_dir", str(run_dir))
            exc.evidence.setdefault("search_evidence_json", str(report_path))
            raise
        # Disk, programming and other infrastructure faults are not acoustic
        # rejections and must never cause the caller to synthesize another take.
        raise
