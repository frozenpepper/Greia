"""Single-shot internal intermediate generation for frozen carrier workflows."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

from .generation_evidence import GenerationEvidence, save_json
from .models import GenerationDisposition, GenerationResult, VerificationDisposition, VerificationMode, VerificationResult, VoiceRequest
from .registry import VoiceRegistryError


class DisposableCarrierGenerator:
    """Create a composite source that cannot be mistaken for a final recording.

    Its caller owns the next step: target extraction, packaged-audio quality
    verification and human review. This adapter deliberately makes one provider
    submission and never retries an uncertain intermediate job.
    """

    def __init__(self, engine) -> None:
        self.engine = engine

    def generate(self, request: VoiceRequest) -> GenerationResult:
        engine = self.engine
        if (request.verification is not VerificationMode.OFF or request.max_attempts != 1
                or request.short_text_mode != "off"):
            return GenerationResult(
                GenerationDisposition.REJECTED, request, None, None, None,
                VerificationResult(VerificationDisposition.NOT_RUN, "none",
                                   detail="invalid internal carrier request"),
                0, "disposable carrier requires verification=off, one attempt and short mode off",
            )
        try:
            provider, profile = engine.route(request)
        except (VoiceRegistryError, ValueError, RuntimeError) as exc:
            return GenerationResult(GenerationDisposition.REJECTED, request, None, None, None,
                VerificationResult(VerificationDisposition.NOT_RUN, "none", detail=str(exc)), 0, str(exc))
        status = provider.probe()
        if not status.available:
            return GenerationResult(GenerationDisposition.UNAVAILABLE, request, provider.provider_id,
                None, None, VerificationResult(VerificationDisposition.NOT_RUN, "none", detail=status.detail),
                0, status.detail)
        output = engine._resolve_output(request)
        if output.exists() or output.with_suffix(output.suffix + ".receipt.json").exists():
            return GenerationResult(GenerationDisposition.REJECTED, request, provider.provider_id,
                None, None, VerificationResult(VerificationDisposition.NOT_RUN, "none",
                    detail="internal carrier destination already exists"), 0,
                "internal carrier output and receipt must be fresh")
        evidence = GenerationEvidence(request.to_dict())
        take = None
        try:
            with engine.generation_lock:
                attempt_dir = evidence.attempt(1)
                raw = attempt_dir / "provider-output.wav"
                evidence.write_state("GENERATING_DISPOSABLE_CARRIER", attempt=1,
                                     provider_id=provider.provider_id, attempt_dir=str(attempt_dir),
                                     provider_request=request.to_dict())
                take = provider.generate(request, profile)
                shutil.copyfile(take.temporary_wav, raw)
                take.temporary_wav.unlink(missing_ok=True)
                engine.audio.validate_review_wav(raw)
                engine.audio.package(raw, output)
                not_run = VerificationResult(VerificationDisposition.NOT_RUN, "none",
                    detail="intermediate spoken carrier; target must be extracted and checked downstream")
                receipt = engine._write_receipt(request, provider, profile, output, not_run, 1,
                                                take.generation_parameters)
                receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
                receipt_payload["internal_disposable_carrier"] = {
                    "target_check_required": True, "evidence_dir": str(evidence.path),
                }
                save_json(receipt, receipt_payload)
                evidence.append({"attempt": 1, "provider_id": provider.provider_id,
                    "generation_parameters": take.generation_parameters,
                    "raw_audio": {"path": str(raw), "sha256": hashlib.sha256(raw.read_bytes()).hexdigest()},
                    "intermediate_output": str(output), "verification": not_run.to_dict()})
                evidence.write_state("CARRIER_READY_FOR_DOWNSTREAM_TARGET_CHECK", output=str(output),
                                     receipt=str(receipt))
            return GenerationResult(GenerationDisposition.REVIEW_REQUIRED, request, provider.provider_id,
                output, receipt, not_run, 1,
                "intermediate carrier created; downstream target extraction and verification are required",
                evidence_dir=evidence.path)
        except Exception as exc:
            evidence.write_state("NEEDS_RECOVERY", attempt=1, error=str(exc),
                provider_job_id=getattr(take, "generation_parameters", {}).get("job_id"))
            return GenerationResult(GenerationDisposition.REJECTED, request, provider.provider_id,
                None, None, VerificationResult(VerificationDisposition.NOT_RUN, "none", detail=str(exc)),
                1, str(exc) + "; inspect saved evidence before retry: " + str(evidence.path),
                evidence_dir=evidence.path)
        finally:
            if take is not None:
                take.temporary_wav.unlink(missing_ok=True)
