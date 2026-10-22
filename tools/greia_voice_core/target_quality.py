"""Shared delivered-target screening, independent of synthesis and installation."""
from .review import signal_metrics
from .review_policy import ASR_PASS_THRESHOLD
from .verification import transcript_similarity


class TargetQualityChecker:
    """Score the actual delivered PCM; optionally require target token count."""

    def __init__(self, transcriber=None):
        from voice_carrier import _whisper_transcribe
        self.transcriber = transcriber or _whisper_transcribe

    def check(self, extracted, delivered, extraction, *, text, locale,
              ignore_accents=True, enabled=True, require_word_count=False):
        """Return a verdict; changed delivery bytes require a new transcription."""
        from voice_carrier import _read_pcm16, comparison_words
        if not enabled:
            return {"disposition": "NOT_RUN", "score": None,
                    "transcript": extraction.get("extracted_transcript"),
                    "detail": "Target scoring explicitly disabled"}
        transcript = extraction["extracted_transcript"]
        if _read_pcm16(delivered) != _read_pcm16(extracted):
            transcript = self.transcriber(delivered, locale).get("text", "")
        expected_tokens = comparison_words(text, ignore_accents=ignore_accents)
        actual_tokens = comparison_words(transcript, ignore_accents=ignore_accents)
        from .number_comparison import SUPPORTED_COMPARISON_POLICIES
        number_policy = extraction.get("comparison_policy") in SUPPORTED_COMPARISON_POLICIES
        comparison = None
        if number_policy:
            from .number_comparison import compare_target_transcript
            comparison = compare_target_transcript(locale, text, transcript, ignore_accents=ignore_accents,
                                                   policy=extraction["comparison_policy"])
            score = comparison.score
        else:
            score = transcript_similarity(text, transcript, ignore_accents=ignore_accents)
        try:
            metrics, flags = signal_metrics(delivered)
        except ValueError as exc:
            metrics, flags = {"signal_error": str(exc)}, ["INVALID_SIGNAL"]
        if comparison is not None:
            flags.extend(comparison.flags(require_word_count=require_word_count))
        elif require_word_count and len(expected_tokens) != len(actual_tokens):
            flags.append("TARGET_WORD_COUNT_MISMATCH")
        return {"disposition": "PASS" if score > ASR_PASS_THRESHOLD and not flags else "WARN",
                "score": score, "transcript": transcript, "metrics": metrics, "flags": flags,
                "ignore_accents": ignore_accents, "comparison_policy": extraction.get("comparison_policy", "legacy-text"),
                "model_id": extraction["model_id"],
                "model_revision": extraction["model_revision"],
                "detail": "Packaged target scored with Base; human listening remains pending"}
