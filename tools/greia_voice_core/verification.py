from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from pathlib import Path
from typing import Protocol

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
    if request.kind is not SpeechKind.CHARACTER_DIALOGUE:
        return False
    words = normalize_transcript(request.text).split()
    # Whisper-tiny is not a pronunciation authority and is particularly noisy on
    # isolated letters/syllables and tiny exclamations. Those stay human-review only.
    return len(words) >= 2 and len(request.text) <= 500


@dataclass
class WhisperVerifier:
    model_id: str = "mlx-community/whisper-tiny"
    pass_threshold: float = 0.72
    verifier_id: str = "mlx-whisper-tiny"

    def probe(self) -> tuple[bool, str]:
        try:
            import mlx_whisper  # noqa: F401
        except Exception as exc:
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

        try:
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

        score = transcript_similarity(request.text, transcript)
        disposition = (
            VerificationDisposition.PASS
            if score >= self.pass_threshold
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
