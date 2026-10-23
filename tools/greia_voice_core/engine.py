from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Iterable

from .audio import AudioPipeline, AudioPipelineError
from .locking import GenerationLockError, InterprocessGenerationLock
from .models import (
    GenerationDisposition,
    GenerationResult,
    SpeechKind,
    VerificationDisposition,
    VerificationMode,
    VerificationResult,
    VoiceProfile,
    VoiceRequest,
)
from .providers import VoiceProvider, VoiceProviderError
from .paths import voice_home
from .registry import VoiceRegistry, VoiceRegistryError
from .verification import ParakeetVerifier, SpeechVerifier
from .generation_evidence import GenerationEvidence, save_json


class VoiceRoutingError(RuntimeError):
    pass


class VoiceEngine:
    """Single owner for Greia authoring-time speech routing and generation lifecycle.

    The engine owns provider selection, one long-lived provider instance per backend,
    canonical reference validation, bounded regeneration, packaging, machine receipts,
    and cleanup. It never marks generated audio human-accepted.

    ``shared_character_utterance`` is valid here only because this is an
    *authoring* engine: it allows the central reviewed shared library to be
    produced through the same provider abstraction. Runtime Activities still
    resolve shared families from Greia's reviewed catalogue and never synthesize
    them on the child device.
    """

    def __init__(
        self,
        project_root: Path,
        registry: VoiceRegistry,
        providers: Iterable[VoiceProvider],
        verifier: SpeechVerifier | None = None,
        audio_pipeline: AudioPipeline | None = None,
        generation_lock: object | None = None,
        short_phrase_pipeline=None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.registry = registry
        self.providers = tuple(providers)
        self.verifier = verifier or ParakeetVerifier()
        self.audio = audio_pipeline or AudioPipeline()
        self.generation_lock = generation_lock or InterprocessGenerationLock(
            voice_home() / "generation.lock"
        )
        from .short_phrases import ShortPhrasePipeline
        self.short_phrases = short_phrase_pipeline or ShortPhrasePipeline(verifier=self.verifier)

    def close(self) -> None:
        for provider in self.providers:
            provider.close()

    def __enter__(self) -> "VoiceEngine":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _profile_for(self, request: VoiceRequest) -> VoiceProfile | None:
        if request.kind is SpeechKind.PEDAGOGICAL_SPEECH:
            if request.speaker not in {"pedagogical", "system"}:
                raise VoiceRoutingError(
                    "pedagogical_speech must use speaker 'pedagogical' or 'system'; "
                    "do not pretend a canonical character speaks pronunciation-authoritative audio"
                )
            return None

        if request.kind is SpeechKind.DANI_SYSTEM_SPEECH:
            if request.speaker != "dani":
                raise VoiceRoutingError("dani_system_speech requires speaker 'dani'")
            return self.registry.get("dani")

        if request.kind is SpeechKind.SHARED_CHARACTER_UTTERANCE:
            profile = self.registry.get(request.speaker)
            if profile.production not in {"cloned_reference", "greia_os_tts"}:
                raise VoiceRoutingError(
                    f"speaker {request.speaker} has no production profile for shared utterances"
                )
            return profile

        profile = self.registry.get(request.speaker)
        if profile.production != "cloned_reference":
            if profile.character == "dani":
                raise VoiceRoutingError(
                    "Dani must use kind=dani_system_speech for Activity-specific dialogue, "
                    "when configured with a legacy system-speech profile"
                )
            raise VoiceRoutingError(
                f"speaker {request.speaker} does not have a cloned character-speech profile"
            )
        return profile

    def route(self, request: VoiceRequest) -> tuple[VoiceProvider, VoiceProfile | None]:
        profile = self._profile_for(request)
        if profile is not None and profile.anchor_path is not None:
            self.registry.verify_anchor(profile)
        for provider in self.providers:
            if provider.supports(request, profile):
                if request.delivery_prompt and not provider.supports_delivery_prompt:
                    raise VoiceRoutingError(f"{provider.provider_id} does not support delivery_prompt")
                return provider, profile
        raise VoiceRoutingError(
            f"no provider registered for kind={request.kind.value}, speaker={request.speaker}"
        )

    @staticmethod
    def _default_output(request: VoiceRequest) -> Path:
        safe_cue = (request.cue_id or request.speaker).replace("/", "_").replace("..", "_")
        suffix = hashlib.sha256(request.text.encode("utf-8")).hexdigest()[:10]
        return voice_home() / "review" / request.language / f"{safe_cue}-{suffix}.wav"

    def _resolve_output(self, request: VoiceRequest) -> Path:
        if request.output is None:
            return self._default_output(request)
        output = request.output
        if output.is_absolute():
            return output
        resolved = (self.project_root / output).resolve()
        if self.project_root not in resolved.parents and resolved != self.project_root:
            raise ValueError("relative output path escapes the Greia repository")
        return resolved

    def _portable_output_path(self, output: Path) -> str:
        try:
            return str(output.resolve().relative_to(self.project_root))
        except ValueError:
            # Machine-local review receipts may contain machine-local paths. Portable
            # source receipts use repository-relative paths and never embed home dirs.
            return str(output)

    def _write_receipt(
        self,
        request: VoiceRequest,
        provider: VoiceProvider,
        profile: VoiceProfile | None,
        output: Path,
        verification: VerificationResult,
        attempts: int,
        generation_parameters: dict,
    ) -> Path:
        receipt_path = output.with_suffix(output.suffix + ".receipt.json")
        request_payload = request.to_dict()
        if request.output is not None:
            # The caller may pass an absolute path; keep the committed receipt portable.
            request_payload["output"] = self._portable_output_path(output)
        receipt = {
            "schema_version": 1,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "request": request_payload,
            "provider_id": provider.provider_id,
            "voice_id": profile.voice_id if profile else None,
            "voice_registry_version": self.registry.registry_version,
            "reference_sha256": profile.anchor_sha256 if profile else None,
            "generation_parameters": generation_parameters,
            "verification": verification.to_dict(),
            "attempts": attempts,
            "output": {
                "path": self._portable_output_path(output),
                "bytes": output.stat().st_size,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            },
            "human_review": "PENDING",
            "acceptance_note": (
                "Machine generation/verification is never Greia audio acceptance. "
                "A human listening gate is still required."
            ),
        }
        temporary = receipt_path.with_name(receipt_path.name + ".tmp")
        temporary.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
        temporary.replace(receipt_path)
        return receipt_path

    def generate_disposable_carrier(self, request: VoiceRequest) -> GenerationResult:
        """Create one internal raw carrier whose target is checked downstream.

        This is reserved for the frozen corpus carrier flow: the resulting audio
        is an intermediate containing an introduction and requested target, and
        is never the product recording. The caller must extract and verify the
        final target before it can be installed. Public ``generate`` rejects OFF.
        """
        from .disposable_carrier import DisposableCarrierGenerator
        return DisposableCarrierGenerator(self).generate(request)

    def generate(self, request: VoiceRequest) -> GenerationResult:
        # New public speech must never silently bypass the delivered-audio gate.
        # ShortPhrasePipeline uses OFF only for its disposable carrier request,
        # which is internal and always followed by target extraction + Parakeet.
        if request.verification is VerificationMode.OFF:
            return GenerationResult(
                GenerationDisposition.REJECTED, request, None, None, None,
                VerificationResult(VerificationDisposition.NOT_RUN, "none",
                                   detail="verification=off is not supported for new public speech"),
                0, "new speech creation requires automatic delivered-audio verification",
            )
        try:
            provider, profile = self.route(request)
        except (VoiceRoutingError, VoiceRegistryError, ValueError) as exc:
            return GenerationResult(
                disposition=GenerationDisposition.REJECTED,
                request=request,
                provider_id=None,
                output_path=None,
                receipt_path=None,
                verification=VerificationResult(
                    disposition=VerificationDisposition.NOT_RUN,
                    verifier_id="none",
                    detail="generation did not start",
                ),
                attempts=0,
                detail=str(exc),
            )

        status = provider.probe()
        if not status.available:
            return GenerationResult(
                disposition=GenerationDisposition.UNAVAILABLE,
                request=request,
                provider_id=provider.provider_id,
                output_path=None,
                receipt_path=None,
                verification=VerificationResult(
                    disposition=VerificationDisposition.NOT_RUN,
                    verifier_id="none",
                    detail="provider unavailable",
                ),
                attempts=0,
                detail=status.detail,
            )

        probe_verifier = getattr(self.verifier, "probe", None)
        ready, verifier_detail = probe_verifier() if callable(probe_verifier) else (True, "injected verifier")
        if not ready:
            return GenerationResult(
                GenerationDisposition.UNAVAILABLE, request, provider.provider_id, None, None,
                VerificationResult(VerificationDisposition.NOT_RUN,
                                   getattr(self.verifier, "verifier_id", "parakeet"),
                                   detail=verifier_detail),
                0, "pinned Parakeet verification is unavailable; no synthesis was submitted",
            )

        output = self._resolve_output(request)
        try:
            if self.short_phrases.policy.selected(request, provider):
                return self.short_phrases.generate(self, request, provider, profile)
        except (ValueError, VoiceProviderError, AudioPipelineError, GenerationLockError, OSError) as exc:
            return GenerationResult(
                GenerationDisposition.REJECTED, request, provider.provider_id, None, None,
                VerificationResult(VerificationDisposition.NOT_RUN, "none", detail=str(exc)), 0, str(exc))
        evidence = GenerationEvidence(request.to_dict())
        best_verification = VerificationResult(
            VerificationDisposition.NOT_RUN, getattr(self.verifier, "verifier_id", "parakeet"),
            detail="not yet run")
        attempts = 0
        take = None
        try:
            with self.generation_lock:
                for attempts in range(1, min(request.max_attempts, 3) + 1):
                    attempt_dir = evidence.attempt(attempts)
                    raw = attempt_dir / "provider-output.wav"
                    candidate = attempt_dir / ("candidate" + output.suffix.lower())
                    delivered = attempt_dir / "delivered.wav"
                    evidence.write_state("GENERATING", attempt=attempts,
                                         attempt_dir=str(attempt_dir), provider_id=provider.provider_id,
                                         provider_request=request.to_dict())
                    take = None
                    take = provider.generate(request, profile)
                    shutil.copyfile(take.temporary_wav, raw)
                    take.temporary_wav.unlink(missing_ok=True)
                    self.audio.validate_review_wav(raw)
                    self.audio.package(raw, candidate)
                    self.audio.decode_for_review(candidate, delivered)
                    self.audio.validate_review_wav(delivered)
                    verification = self.verifier.verify(request, delivered)
                    best_verification = verification
                    row = {
                        "attempt": attempts,
                        "provider_id": provider.provider_id,
                        "generation_parameters": take.generation_parameters,
                        "raw_audio": {"path": str(raw), "sha256": hashlib.sha256(raw.read_bytes()).hexdigest()},
                        "candidate": str(candidate),
                        "delivered_audio": {"path": str(delivered), "sha256": hashlib.sha256(delivered.read_bytes()).hexdigest()},
                        "verification": verification.to_dict(),
                    }
                    evidence.append(row)
                    evidence.write_state("QUALITY_CHECKED", attempt=attempts)
                    if verification.disposition is VerificationDisposition.PASS:
                        output.parent.mkdir(parents=True, exist_ok=True)
                        staging = output.with_name(output.name + "." + evidence.path.name + ".tmp")
                        shutil.copyfile(candidate, staging)
                        staging.replace(output)
                        receipt = self._write_receipt(
                            request, provider, profile, output, verification, attempts,
                            take.generation_parameters)
                        receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
                        receipt_payload["generation_evidence"] = {
                            "path": str(evidence.path),
                            "history": str(evidence.path / "history.json"),
                        }
                        save_json(receipt, receipt_payload)
                        evidence.write_state("VERIFIED_PENDING_LISTENING", output=str(output), receipt=str(receipt))
                        return GenerationResult(
                            GenerationDisposition.REVIEW_REQUIRED, request, provider.provider_id,
                            output, receipt, verification, attempts,
                            "delivered audio passed automatic Parakeet checks; human listening remains mandatory",
                            evidence_dir=evidence.path)
                    if verification.disposition is not VerificationDisposition.WARN:
                        # NOT_RUN/NOT_APPLICABLE is uncertainty, never a quality
                        # retry or pass. Preserve evidence and require recovery.
                        evidence.write_state("NEEDS_RECOVERY", attempt=attempts,
                                             verification=verification.to_dict())
                        return GenerationResult(
                            GenerationDisposition.REJECTED, request, provider.provider_id,
                            None, None, verification, attempts,
                            "delivery verification returned no determinate result; inspect saved evidence before retry: " + str(evidence.path),
                            evidence_dir=evidence.path)
            evidence.write_state("FAILED_QUALITY", attempt=attempts)
            return GenerationResult(
                GenerationDisposition.REJECTED, request, provider.provider_id, None, None,
                verification=best_verification,
                attempts=attempts,
                detail="delivered audio did not pass automatic Parakeet checks; evidence: " + str(evidence.path),
                evidence_dir=evidence.path,
            )
        except Exception as exc:
            evidence.write_state("NEEDS_RECOVERY", attempt=attempts, error=str(exc),
                                 provider_job_id=getattr(take, "generation_parameters", {}).get("job_id"))
            return GenerationResult(
                disposition=GenerationDisposition.REJECTED,
                request=request,
                provider_id=provider.provider_id,
                output_path=None,
                receipt_path=None,
                verification=best_verification,
                attempts=attempts,
                detail=str(exc) + "; inspect saved evidence before retry: " + str(evidence.path),
                evidence_dir=evidence.path,
            )
        finally:
            if take is not None:
                take.temporary_wav.unlink(missing_ok=True)
