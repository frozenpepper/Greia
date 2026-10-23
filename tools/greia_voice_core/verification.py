from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import gc
import re
from pathlib import Path
from typing import Protocol

from .review_policy import ASR_PASS_THRESHOLD
from .asr_policy import DEFAULT_ASR_MODEL, DEFAULT_ASR_REVISION, DEFAULT_ASR_VERIFIER, cached_asr_model, comparison_text

from .models import (
    SpeechKind,
    VerificationDisposition,
    VerificationMode,
    VerificationResult,
    VoiceRequest,
)
from .parakeet_asr import ParakeetTranscriber, ParakeetTranscriptionError


class SpeechVerifier(Protocol):
    verifier_id: str

    def verify(self, request: VoiceRequest, wav_path: Path) -> VerificationResult: ...

    def probe(self) -> tuple[bool, str]: ...


def normalize_transcript(text: str, *, ignore_accents: bool = True) -> str:
    return " ".join(re.findall(r"\w+", comparison_text(text, ignore_accents=ignore_accents), flags=re.UNICODE))


def transcript_similarity(expected: str, actual: str, *, ignore_accents: bool = True) -> float:
    expected_norm = normalize_transcript(expected, ignore_accents=ignore_accents)
    actual_norm = normalize_transcript(actual, ignore_accents=ignore_accents)
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
    model_id: str = DEFAULT_ASR_MODEL
    pass_threshold: float = ASR_PASS_THRESHOLD
    verifier_id: str = DEFAULT_ASR_VERIFIER

    def probe(self) -> tuple[bool, str]:
        try:
            import mlx_whisper  # noqa: F401
            cached_asr_model(self.model_id)
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
                path_or_hf_repo=str(cached_asr_model(self.model_id)),
                language=request.language,
                temperature=0.0, condition_on_previous_text=False, initial_prompt=None,
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

        from .number_comparison import compare_target_transcript, COMPARISON_POLICY
        comparison = compare_target_transcript(request.language, request.text, transcript,
                                               ignore_accents=request.ignore_accents)
        score = comparison.score
        disposition = (
            VerificationDisposition.PASS
            if score > self.pass_threshold and comparison.numbers_match
            else VerificationDisposition.WARN
        )
        return VerificationResult(
            disposition=disposition,
            verifier_id=self.verifier_id,
            transcript=transcript,
            score=score,
            model_id=self.model_id,
            model_revision=DEFAULT_ASR_REVISION if self.model_id == DEFAULT_ASR_MODEL else None,
            ignore_accents=request.ignore_accents,
            detail=(
                f"transcript aligned with {COMPARISON_POLICY}; human listening still required"
                if disposition is VerificationDisposition.PASS
                else "transcript or numeric identity mismatch; regenerate or inspect manually"
            ),
        )


@dataclass
class ParakeetVerifier:
    """Current verifier for every newly created request and delivered rendition.

    Historical Whisper verification remains available through ``WhisperVerifier``
    for explicitly versioned receipts/replay. New requests use this pinned offline
    multilingual adapter and must pass text, word-count, numeric and signal checks.
    """

    transcriber: ParakeetTranscriber | None = None
    pass_threshold: float = ASR_PASS_THRESHOLD

    def __post_init__(self) -> None:
        self.transcriber = self.transcriber or ParakeetTranscriber()

    @property
    def verifier_id(self) -> str:
        assert self.transcriber is not None
        return self.transcriber.recognizer_id

    @property
    def model_id(self) -> str:
        assert self.transcriber is not None
        return self.transcriber.model_id

    @property
    def model_revision(self) -> str:
        assert self.transcriber is not None
        return self.transcriber.model_revision

    def probe(self) -> tuple[bool, str]:
        assert self.transcriber is not None
        return self.transcriber.probe()

    def transcribe(self, wav_path: Path, locale: str | None = None) -> dict:
        assert self.transcriber is not None
        return self.transcriber.transcribe(wav_path, locale)

    def __call__(self, wav_path: Path, locale: str | None = None) -> dict:
        return self.transcribe(wav_path, locale)

    def verify(self, request: VoiceRequest, wav_path: Path) -> VerificationResult:
        from .number_comparison import COMPARISON_POLICY, compare_target_transcript
        from .review import signal_metrics

        observed = self.transcribe(wav_path, request.language)
        transcript = observed["text"]
        comparison = compare_target_transcript(
            request.language, request.text, transcript,
            ignore_accents=request.ignore_accents, policy=COMPARISON_POLICY,
        )
        flags = comparison.flags(require_word_count=True)
        try:
            metrics, signal_flags = signal_metrics(wav_path)
        except ValueError as exc:
            metrics, signal_flags = {"signal_error": str(exc)}, ["INVALID_SIGNAL"]
        flags.extend(signal_flags)
        passes = comparison.score > self.pass_threshold and not flags
        disposition = VerificationDisposition.PASS if passes else VerificationDisposition.WARN
        return VerificationResult(
            disposition=disposition,
            verifier_id=self.verifier_id,
            transcript=transcript,
            score=comparison.score,
            model_id=self.model_id,
            model_revision=self.model_revision,
            ignore_accents=request.ignore_accents,
            comparison_policy=COMPARISON_POLICY,
            flags=tuple(flags),
            metrics=metrics,
            detail=("delivered audio passed Parakeet text and signal screening; human listening remains required"
                    if passes else "delivered audio failed Parakeet text/count/number or signal screening"),
        )
