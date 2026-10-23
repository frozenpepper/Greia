"""One bounded automatic carrier lifecycle behind VoiceEngine's public API."""
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import uuid

from .direction import character_delivery
from .audio import AudioPipelineError
from .models import (GenerationDisposition, GenerationResult, VerificationDisposition,
                     VerificationMode, VerificationResult)
from .paths import voice_home
from .short_policy import ShortPhrasePolicy, COMPOSITION_POLICY
from .short_delivery import prepare_delivery
from .target_quality import TargetQualityChecker
from .verification import ParakeetVerifier
from .number_comparison import PARAKEET_COMPARISON_POLICY, SUPPORTED_COMPARISON_POLICIES


def save_evidence(path: Path, value: dict) -> None:
    """Durable single-writer metadata; each attempt directory is never reused."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
    temporary.replace(path)


class ShortPhrasePipeline:
    """Own automatic selection, raw retention, extraction and bounded retries.

    The engine supplies its existing provider, audio pipeline and generation lock;
    this collaborator never recursively calls engine.generate or starts a worker.
    """

    def __init__(self, *, transcriber=None, readiness=None, evidence_root=None, policy=None,
                 attempt_reservation=None, verifier=None):
        self.policy = policy or ShortPhrasePolicy()
        self.attempt_reservation = attempt_reservation
        self.verifier = verifier or (None if transcriber is not None else ParakeetVerifier())
        verifier_transcriber = getattr(self.verifier, "transcribe", None)
        self.transcriber = transcriber or (verifier_transcriber if callable(verifier_transcriber) else None)
        verifier_probe = getattr(self.verifier, "probe", None)
        self.readiness = readiness or (verifier_probe if callable(verifier_probe) else
                                       (lambda: (True, "injected transcriber")) if self.transcriber else
                                       (lambda: (False, "no short-target transcriber configured")))
        self.evidence_root = evidence_root

    def generate(self, engine, request, provider, profile):
        """Return only a safe final target, retaining failed/uncertain attempts."""
        from voice_carrier import ExtractionRejected, spoken_words
        from voice_carrier_search import extract
        comparison_policy = request.comparison_policy or PARAKEET_COMPARISON_POLICY
        if comparison_policy not in SUPPORTED_COMPARISON_POLICIES:
            raise ValueError("unsupported short-phrase comparison policy")
        prefix, composite, delivery = self.policy.composite(request, character_delivery()[profile.character])
        spoken_target = getattr(self.policy, "spoken_target", lambda item: item.text)(request)
        available, detail = self.readiness()
        if not available:
            return GenerationResult(GenerationDisposition.UNAVAILABLE, request, provider.provider_id,
                                    None, None, VerificationResult(VerificationDisposition.WARN,
                                    getattr(self.verifier, "verifier_id", "parakeet"), detail="carrier alignment unavailable: " + detail), 0,
                                    "Pinned Parakeet is required before short-target synthesis")
        output = engine._resolve_output(request)
        if output.suffix.lower() not in {".wav", ".ogg"}:
            raise ValueError("output extension must be .wav or .ogg")
        base = Path(self.evidence_root or voice_home() / "short-phrases").resolve()
        if base.is_relative_to(engine.project_root):
            raise ValueError("short-phrase evidence must remain outside the source repository")
        work = base / uuid.uuid4().hex
        work.mkdir(parents=True, exist_ok=False)
        history = []
        attempts = 0
        last = VerificationResult(VerificationDisposition.WARN, getattr(self.verifier, "verifier_id", "parakeet"), detail="no passing short take")
        checker = TargetQualityChecker(self.transcriber, always_transcribe_delivered=True)
        try:
            with engine.generation_lock:
                for attempts in range(1, min(request.max_attempts, 3) + 1):
                    attempt = work / f"attempt-{attempts:02}"
                    attempt.mkdir()
                    raw = attempt / "raw.wav"
                    raw_request = replace(request, text=composite, delivery_prompt=delivery, output=raw,
                                          verification=VerificationMode.OFF, max_attempts=1, short_text_mode="off")
                    # Persist before submission: a crash here is uncertain and must
                    # be reconciled with the provider, never blindly resubmitted.
                    save_evidence(work / "state.json", {"status": "GENERATING", "attempt": attempts,
                                  "request": request.to_dict(), "raw_request": raw_request.to_dict(), "history": history})
                    if self.attempt_reservation is not None:
                        self.attempt_reservation(request, attempts, work)
                    take = provider.generate(raw_request, profile)
                    try:
                        shutil.copyfile(take.temporary_wav, raw)
                    finally:
                        take.temporary_wav.unlink(missing_ok=True)
                    raw_check = VerificationResult(VerificationDisposition.NOT_RUN, "none", detail="disposable intro not scored")
                    raw_receipt = engine._write_receipt(raw_request, provider, profile, raw, raw_check, 1, take.generation_parameters)
                    try:
                        engine.audio.validate_review_wav(raw)
                    except AudioPipelineError as exc:
                        history.append({"attempt": attempts, "status": "REJECTED_INVALID_AUDIO", "error": str(exc)})
                        save_evidence(attempt / "rejection.json", history[-1])
                        continue
                    kwargs = {} if self.transcriber is None else {"transcriber": self.transcriber}
                    try:
                        extracted = attempt / "target.wav"
                        extraction = extract(raw, extracted, locale=request.locale, prefix=prefix, target=spoken_target,
                                             remove_first_words=len(spoken_words(prefix)), source_receipt_path=raw_receipt,
                                             target_verification="warn", ignore_accents=request.ignore_accents,
                                             comparison_policy=comparison_policy, **kwargs)
                        candidate = attempt / ("candidate" + output.suffix.lower())
                        delivery_wav = attempt / "delivery-target.wav"
                        extraction["delivery"] = prepare_delivery(extracted, delivery_wav, extraction)
                        engine.audio.package(delivery_wav, candidate)
                        decoded = attempt / "delivered.wav"
                        engine.audio.decode_for_review(candidate, decoded)
                        engine.audio.validate_review_wav(decoded)
                        quality = checker.check(extracted, decoded, extraction, text=spoken_target, locale=request.locale,
                                                ignore_accents=request.ignore_accents,
                                                enabled=True,
                                                require_word_count=True)
                    except ExtractionRejected as exc:
                        history.append({"attempt": attempts, "status": "REJECTED_CUT", "error": str(exc), "evidence": exc.evidence})
                        save_evidence(attempt / "rejection.json", history[-1])
                        continue
                    last = VerificationResult(
                        VerificationDisposition(quality["disposition"]),
                        getattr(self.verifier, "verifier_id", extraction["recognizer"]),
                        transcript=quality.get("transcript"), score=quality.get("score"), detail=quality["detail"],
                        model_id=quality.get("model_id", extraction["model_id"]),
                        model_revision=quality.get("model_revision", extraction["model_revision"]),
                        ignore_accents=request.ignore_accents,
                        comparison_policy=extraction.get("comparison_policy"),
                        flags=tuple(quality.get("flags", [])), metrics=quality.get("metrics"))
                    history.append({"attempt": attempts, "status": quality["disposition"], "quality": quality,
                                    "extraction": extraction, "candidate": str(candidate)})
                    save_evidence(attempt / "check.json", history[-1])
                    if quality["disposition"] == "WARN":
                        continue
                    if quality["disposition"] != "PASS":
                        history.append({"attempt": attempts, "status": "NEEDS_RECOVERY",
                                        "quality": quality})
                        save_evidence(attempt / "recovery.json", history[-1])
                        save_evidence(work / "state.json", {
                            "status": "NEEDS_RECOVERY", "request": request.to_dict(),
                            "attempt": attempts, "history": history,
                        })
                        return GenerationResult(
                            GenerationDisposition.REJECTED, request, provider.provider_id,
                            None, None, last, attempts,
                            "short-target verification was indeterminate; inspect saved evidence before retry",
                            evidence_dir=work)
                    # A delivered target replaces the requested destination only
                    # after an explicit PASS; all uncertain evidence stays local.
                    output.parent.mkdir(parents=True, exist_ok=True)
                    staging = output.with_name(output.name + "." + work.name + ".tmp")
                    shutil.copyfile(candidate, staging)
                    staging.replace(output)
                    receipt = engine._write_receipt(request, provider, profile, output, last, attempts, take.generation_parameters)
                    payload = json.loads(receipt.read_text())
                    payload["short_phrase"] = {"mode": "automatic-carrier", "composition_policy": self.policy.composition_policy, "evidence_dir": str(work),
                                               "prefix": prefix, "composite_text": composite,
                                               "effective_delivery": delivery, "semantic_target": request.text,
                                               "spoken_target": spoken_target,
                                               "spoken_target_policy": getattr(self.policy, "spoken_target_policy", "identity-v1"),
                                               "extraction": extraction,
                                               "quality": quality, "history": history}
                    save_evidence(receipt, payload)
                    save_evidence(work / "state.json", {"status": "VERIFIED" if quality["disposition"] == "PASS" else "UNVERIFIED",
                                  "request": request.to_dict(), "output": str(output), "history": history})
                    return GenerationResult(GenerationDisposition.REVIEW_REQUIRED, request, provider.provider_id,
                                            output, receipt, last, attempts, "short target extracted; human listening pending", evidence_dir=work)
            save_evidence(work / "state.json", {"status": "FAILED_QUALITY", "request": request.to_dict(), "history": history})
            return GenerationResult(GenerationDisposition.REJECTED, request, provider.provider_id, None, None,
                                    last, attempts, "short-phrase quality budget exhausted; evidence: " + str(work), evidence_dir=work)
        except Exception as exc:
            save_evidence(work / "state.json", {"status": "NEEDS_RECOVERY" if attempts else "BLOCKED", "error": str(exc),
                          "request": request.to_dict(), "attempt": attempts, "history": history,
                          "raw_request": raw_request.to_dict() if attempts else None})
            if isinstance(exc, Exception):
                return GenerationResult(GenerationDisposition.REJECTED, request, provider.provider_id, None, None,
                                        last, attempts, str(exc) + "; inspect saved evidence before retry: " + str(work), evidence_dir=work)
            raise
