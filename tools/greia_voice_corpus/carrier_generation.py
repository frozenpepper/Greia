"""Produce and audit one spoken-carrier target candidate through VoiceEngine."""
from __future__ import annotations

import json
from pathlib import Path

from greia_voice_core.models import GenerationDisposition, SpeechKind, VerificationMode, VoiceRequest
from voice_carrier import ALGORITHM_VERSION, GAP_POLICY, ExtractionRejected, extract
from greia_voice_core.asr_policy import DEFAULT_ASR_MODEL, DEFAULT_ASR_REVISION
from .inventory import digest, receipt_path
from .store import write_json


class CarrierExtractionFailure(ExtractionRejected):
    """A provider receipt and raw carrier exist, but the target was safely rejected."""


def generate_candidate(engine, store, row: dict, profile, verification: str, *, transcriber=None) -> Path:
    """Keep raw synthesis immutable, extract to PCM WAV, then package target."""

    relative = row["path"]
    carrier = row["spoken_carrier"]
    if carrier.get("extractor_version") != ALGORITHM_VERSION or carrier.get("gap_policy") != GAP_POLICY:
        raise ValueError("frozen carrier extraction policy differs from the executable algorithm")
    if (carrier.get("asr_model") != DEFAULT_ASR_MODEL or carrier.get("asr_revision") != DEFAULT_ASR_REVISION):
        raise ValueError("frozen carrier ASR model differs from the configured default")
    raw = store.work / "carrier-raw" / (relative + ".raw.wav")
    extracted = store.work / "carrier-extracted" / (relative + ".extracted.wav")
    delivery = store.work / "carrier-extracted" / (relative + ".delivery.wav")
    candidate = store.work / "candidates" / relative
    for path in (raw, receipt_path(raw), extracted, delivery, candidate, receipt_path(candidate)):
        if path.exists():
            raise ValueError(f"spoken-carrier attempt path already exists; archive it before retry: {path}")
    raw.parent.mkdir(parents=True, exist_ok=True)
    request_data = dict(row["request"])
    request_data["text"] = carrier["composite_text"]
    request_data["delivery_prompt"] = carrier["composite_delivery_prompt"]
    request = VoiceRequest(
        **{key: value for key, value in request_data.items() if key not in {"kind", "short_text_mode"}},
        kind=SpeechKind(request_data["kind"]), output=raw,
        verification=VerificationMode.OFF, max_attempts=1, short_text_mode="off",
    )
    result = engine.generate(request)
    write_json(raw.with_name(raw.name + ".result.json"), result.to_dict())
    if result.disposition is not GenerationDisposition.REVIEW_REQUIRED:
        raise ValueError(f"{result.disposition.value}: {result.detail}")

    return prepare_saved_candidate(engine, store, row, profile, verification, transcriber=transcriber)


def prepare_saved_candidate(engine, store, row: dict, profile, verification: str, *, transcriber=None) -> Path:
    """Extract/package an existing immutable provider take; never synthesize here."""
    relative = row["path"]
    carrier = row["spoken_carrier"]
    raw = store.work / "carrier-raw" / (relative + ".raw.wav")
    extracted = store.work / "carrier-extracted" / (relative + ".extracted.wav")
    delivery = store.work / "carrier-extracted" / (relative + ".delivery.wav")
    candidate = store.work / "candidates" / relative
    if (carrier.get("extractor_version") != ALGORITHM_VERSION or carrier.get("gap_policy") != GAP_POLICY
            or carrier.get("asr_model") != DEFAULT_ASR_MODEL or carrier.get("asr_revision") != DEFAULT_ASR_REVISION):
        raise ValueError("saved take recovery policy differs from the executable policy")
    if candidate.exists() or receipt_path(candidate).exists() or extracted.exists() or delivery.exists():
        raise ValueError("archive previous extraction/candidate before recovering a saved take")
    provider_receipt = json.loads(receipt_path(raw).read_text(encoding="utf-8"))
    if (provider_receipt.get("provider_id") != "voxstage-voxcpm2"
            or provider_receipt.get("voice_id") != profile.voice_id
            or provider_receipt.get("reference_sha256") != profile.anchor_sha256
            or provider_receipt.get("output", {}).get("sha256") != digest(raw)):
        raise ValueError("saved carrier source/master/receipt differs")
    expected = {**row["request"], "text": carrier["composite_text"],
                "delivery_prompt": carrier["composite_delivery_prompt"]}
    if any(provider_receipt.get("request", {}).get(key) != expected.get(key)
           for key in ("speaker", "locale", "kind", "text", "delivery_prompt")):
        raise ValueError("saved carrier provider request differs from the frozen source request")
    try:
        extraction_args = {} if transcriber is None else {"transcriber": transcriber}
        extraction = extract(
            raw, extracted, locale=row["request"]["locale"],
            prefix=carrier["prefix"], target=carrier["target"],
            remove_first_words=carrier["prefix_word_count"],
            padding_seconds=carrier["gap_policy"]["cut_padding_seconds"],
            source_receipt_path=receipt_path(raw),
            target_verification=carrier["target_verification"],
            ignore_accents=carrier.get("ignore_accents", True),
            **extraction_args,
        )
    except ExtractionRejected as exc:
        write_json(store.work / "carrier-evidence" / f"{relative}.failure.json", {
            "status": "REJECTED", "error": str(exc), "failure_evidence": exc.evidence,
            "raw_audio": str(raw.relative_to(store.work)), "raw_sha256": digest(raw),
            "raw_receipt_sha256": digest(receipt_path(raw)), "carrier_plan": carrier,
        })
        raise CarrierExtractionFailure(str(exc), evidence=exc.evidence) from exc

    from greia_voice_core.short_delivery import prepare_delivery
    extraction["delivery"] = prepare_delivery(extracted, delivery, extraction)
    engine.audio.package(delivery, candidate)
    decoded = store.work / "carrier-extracted" / (relative + ".validation.wav")
    engine.audio.decode_for_review(candidate, decoded)
    engine.audio.validate_review_wav(decoded)

    from greia_voice_core.target_quality import TargetQualityChecker
    quality = TargetQualityChecker(transcriber).check(
        extracted, decoded, extraction, text=row["request"]["text"],
        locale=row["request"]["locale"], ignore_accents=carrier.get("ignore_accents", True),
        enabled=verification != "off")
    if quality["disposition"] == "WARN":
        write_json(store.work / "carrier-evidence" / f"{relative}.failure.json", {
            "status": "REJECTED", "error": "FINAL_TARGET_QUALITY_REJECTED", "quality": quality,
            "raw_audio": str(raw.relative_to(store.work)), "raw_sha256": digest(raw),
            "raw_receipt_sha256": digest(receipt_path(raw)), "carrier_plan": carrier})
        raise CarrierExtractionFailure("final target quality rejected: " + str(quality), evidence=quality)

    raw_receipt = json.loads(receipt_path(raw).read_text(encoding="utf-8"))
    receipt = {
        "schema_version": 1,
        "created_utc": raw_receipt.get("created_utc"),
        "kind": "greia-spoken-carrier-target",
        "mode": carrier["mode"],
        "carrier_plan": carrier,
        "target_request": row["request"],
        "request": {**row["request"], "output": relative,
                    "verification": verification, "max_attempts": 1},
        "provider_id": raw_receipt.get("provider_id"),
        "voice_id": profile.voice_id,
        "voice_registry_version": raw_receipt.get("voice_registry_version"),
        "reference_sha256": profile.anchor_sha256,
        "generation_parameters": raw_receipt.get("generation_parameters", {}),
        "verification": {**quality, "verifier_id": extraction.get("recognizer")},
        "attempts": 1,
        "human_review": "PENDING",
        "raw_audio": {
            "path": str(raw.relative_to(store.work)),
            "sha256": digest(raw),
            "receipt_sha256": digest(receipt_path(raw)),
        },
        "extracted_pcm": {
            "path": str(extracted.relative_to(store.work)),
            "sha256": digest(extracted),
        },
        "delivery_pcm": {
            "path": str(delivery.relative_to(store.work)),
            "sha256": digest(delivery),
        },
        "extraction": extraction,
        "output": {"path": relative, "sha256": digest(candidate), "bytes": candidate.stat().st_size},
    }
    write_json(receipt_path(candidate), receipt)
    return candidate
