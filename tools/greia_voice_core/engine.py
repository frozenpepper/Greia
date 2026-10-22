from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Iterable

from .audio import AudioPipeline, AudioPipelineError
from .locking import GenerationLockError, InterprocessGenerationLock
from .models import (
    GenerationDisposition,
    GenerationResult,
    SpeechKind,
    VerificationDisposition,
    VerificationResult,
    VoiceProfile,
    VoiceRequest,
)
from .providers import VoiceProvider, VoiceProviderError
from .paths import voice_home
from .registry import VoiceRegistry, VoiceRegistryError
from .verification import SpeechVerifier, WhisperVerifier


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
        self.verifier = verifier or WhisperVerifier()
        self.audio = audio_pipeline or AudioPipeline()
        self.generation_lock = generation_lock or InterprocessGenerationLock(
            voice_home() / "generation.lock"
        )
        from .short_phrases import ShortPhrasePipeline
        self.short_phrases = short_phrase_pipeline or ShortPhrasePipeline()

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
        receipt_path.write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return receipt_path

    def generate(self, request: VoiceRequest) -> GenerationResult:
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

        output = self._resolve_output(request)
        try:
            if self.short_phrases.policy.selected(request, provider):
                return self.short_phrases.generate(self, request, provider, profile)
        except (ValueError, VoiceProviderError, AudioPipelineError, GenerationLockError, OSError) as exc:
            return GenerationResult(
                GenerationDisposition.REJECTED, request, provider.provider_id, None, None,
                VerificationResult(VerificationDisposition.NOT_RUN, "none", detail=str(exc)), 0, str(exc))
        best_take = None
        best_verification = VerificationResult(
            disposition=VerificationDisposition.NOT_RUN,
            verifier_id=getattr(self.verifier, "verifier_id", "none"),
            detail="not yet run",
        )
        attempts = 0
        take = None
        try:
            with self.generation_lock:
                for attempts in range(1, request.max_attempts + 1):
                    take = provider.generate(request, profile)
                    self.audio.validate_review_wav(take.temporary_wav)
                    verification = self.verifier.verify(request, take.temporary_wav)
                    if best_take is not None and best_take.temporary_wav.exists():
                        best_take.temporary_wav.unlink()
                    best_take = take
                    best_verification = verification
                    if verification.disposition is not VerificationDisposition.WARN:
                        break

            assert best_take is not None
            self.audio.package(best_take.temporary_wav, output)
            receipt = self._write_receipt(
                request,
                provider,
                profile,
                output,
                best_verification,
                attempts,
                best_take.generation_parameters,
            )
            disposition = (
                GenerationDisposition.REVIEW_REQUIRED_ASR_WARNING
                if best_verification.disposition is VerificationDisposition.WARN
                else GenerationDisposition.REVIEW_REQUIRED
            )
            return GenerationResult(
                disposition=disposition,
                request=request,
                provider_id=provider.provider_id,
                output_path=output,
                receipt_path=receipt,
                verification=best_verification,
                attempts=attempts,
                detail="generated successfully; human listening review remains mandatory",
            )
        except (VoiceProviderError, AudioPipelineError, GenerationLockError, OSError) as exc:
            return GenerationResult(
                disposition=GenerationDisposition.REJECTED,
                request=request,
                provider_id=provider.provider_id,
                output_path=None,
                receipt_path=None,
                verification=best_verification,
                attempts=attempts,
                detail=str(exc),
            )
        finally:
            if take is not None and take is not best_take:
                take.temporary_wav.unlink(missing_ok=True)
            if best_take is not None and best_take.temporary_wav.exists():
                best_take.temporary_wav.unlink()
