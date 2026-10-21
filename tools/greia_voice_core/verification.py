from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import gc
import re
from pathlib import Path
from typing import Protocol

from .review_policy import ASR_PASS_THRESHOLD

from .models import (
    SpeechKind,
    VerificationDisposition,
    VerificationMode,
    VerificationResult,
    VoiceRequest,
)


class SpeechVerifier(Protocol):
    verifier_id: str

    def verify(self, request: VoiceRequest, wav_path: Path) -> VerificationResult: ...

    def probe(self) -> tuple[bool, str]: ...


def normalize_transcript(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold(), flags=re.UNICODE))


def transcript_similarity(expected: str, actual: str) -> float:
    expected_norm = normalize_transcript(expected)
    actual_norm = normalize_transcript(actual)
    if not expected_norm or not actual_norm:
        return 0.0
    char_score = SequenceMatcher(None, expected_norm, actual_norm).ratio()
    expected_words = expected_norm.split()
    actual_words = actual_norm.split()
    expected_set = set(expected_words)
    actual_set = set(actual_words)
    overlap = len(expected_set & actual_set)
    precision = overlap / max(1, len(actual_set))
    recall = overlap / max(1, len(expected_set))
    token_f1 = 0.0 if not (precision + recall) else 2 * precision * recall / (precision + recall)
    return round((char_score * 0.65) + (token_f1 * 0.35), 4)


def asr_eligible(request: VoiceRequest) -> bool:
    if request.verification is VerificationMode.OFF:
        return False
    # Preserve Dani's human-review-only verification policy across the v0.2
    # cloned-voice migration. This no longer implies a native synthesis provider;
    # neither that legacy route nor optional ASR can accept a new recording.
    if request.speaker == "dani":
        return False
    if request.kind not in {
        SpeechKind.CHARACTER_DIALOGUE,
        SpeechKind.SHARED_CHARACTER_UTTERANCE,
    }:
        return False
    words = normalize_transcript(request.text).split()
    # Whisper-tiny is not a pronunciation authority and is particularly noisy on
    # isolated letters/syllables and tiny exclamations. Those stay human-review only.
    return len(words) >= 2 and len(request.text) <= 500


def _release_mlx_transient_memory() -> None:
    """Return verifier intermediates cached by MLX to the system allocator.

    ``mlx_whisper`` intentionally caches its model for reuse but does not clear the
    shared MLX allocator cache after ``transcribe``. In Greia the verifier runs in
    the same long-lived process as Chatterbox, so leaving those transient buffers in
    the allocator can make the voice studio retain a much larger footprint than a
    one-shot Chatterbox process. Keep the tiny Whisper model warm, but explicitly
    release reusable/intermediate buffers after every verification pass.
    """

    gc.collect()
    try:
        import mlx.core as mx

        mx.clear_cache()
    except Exception:
        # Verification availability/probe owns reporting. Cleanup must never turn a
        # completed transcription into a new production failure on non-MLX hosts.
        pass


@dataclass
class WhisperVerifier:
    model_id: str = "mlx-community/whisper-tiny"
    pass_threshold: float = ASR_PASS_THRESHOLD
    verifier_id: str = "mlx-whisper-tiny"

    def probe(self) -> tuple[bool, str]:
        try:
            import mlx_whisper  # noqa: F401
        except BaseException as exc:
            return False, f"mlx_whisper unavailable: {exc}"
        return True, self.model_id

    def verify(self, request: VoiceRequest, wav_path: Path) -> VerificationResult:
        if not asr_eligible(request):
            return VerificationResult(
                disposition=VerificationDisposition.NOT_APPLICABLE,
                verifier_id=self.verifier_id,
                detail="ASR intentionally skipped for this semantic/utterance class",
            )
        available, detail = self.probe()
        if not available:
            disposition = (
                VerificationDisposition.WARN
                if request.verification is VerificationMode.REQUIRED
                else VerificationDisposition.NOT_RUN
            )
            return VerificationResult(
                disposition=disposition,
                verifier_id=self.verifier_id,
                detail=detail,
            )

        import mlx_whisper

        result = None
        try:
            # Chatterbox already clears its own transient MLX cache after a take.
            # Clear once more at this provider boundary so Whisper starts from a
            # predictable allocator state in a warm mixed-model worker.
            _release_mlx_transient_memory()
            result = mlx_whisper.transcribe(
                str(wav_path),
                path_or_hf_repo=self.model_id,
                language=request.language,
            )
            transcript = str(result.get("text", "")).strip()
        except Exception as exc:
            return VerificationResult(
                disposition=VerificationDisposition.WARN,
                verifier_id=self.verifier_id,
                detail=f"Whisper verification failed: {exc}",
            )
        finally:
            # Drop the transcription result before clearing the allocator. The
            # mlx_whisper ModelHolder may keep the small model resident by design;
            # its per-call mel/decoder/intermediate buffers must not remain cached
            # beside the warm Chatterbox model.
            result = None
            _release_mlx_transient_memory()

        score = transcript_similarity(request.text, transcript)
        disposition = (
            VerificationDisposition.PASS
            if score > self.pass_threshold
            else VerificationDisposition.WARN
        )
        return VerificationResult(
            disposition=disposition,
            verifier_id=self.verifier_id,
            transcript=transcript,
            score=score,
            detail=(
                "transcript is plausibly aligned; human listening still required"
                if disposition is VerificationDisposition.PASS
                else "transcript mismatch; regenerate or inspect manually"
            ),
        )
