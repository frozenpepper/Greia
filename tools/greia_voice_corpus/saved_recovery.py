"""Explicit v7 adapter for saved v6 provider takes; synthesis is forbidden."""
from __future__ import annotations

from greia_voice_core.asr_policy import DEFAULT_ASR_MODEL, DEFAULT_ASR_REVISION
from greia_voice_core.number_comparison import COMPARISON_POLICY, ORTHOGRAPHIC_COMPARISON_POLICY, ENGLISH_SPOKEN_COMPARISON_POLICY, compare_target_transcript
from voice_carrier_search import ALGORITHM_VERSION, CONTEXT_ALGORITHM_VERSION, extract
from .context_recovery import POLICY as CONTEXT_POLICY

POLICY = "target-only-v7-saved-v1"
ORTHOGRAPHIC_POLICY = "target-only-v7-saved-oskar-en-v1"
ENGLISH_SPOKEN_POLICY = "target-only-v7-saved-spoken-en-v1"
POLICIES = {CONTEXT_POLICY: COMPARISON_POLICY, POLICY: COMPARISON_POLICY, ORTHOGRAPHIC_POLICY: ORTHOGRAPHIC_COMPARISON_POLICY, ENGLISH_SPOKEN_POLICY: ENGLISH_SPOKEN_COMPARISON_POLICY}


def recovery_enabled(plan: dict) -> bool:
    """Recognize one explicit opt-in; unknown policy names fail closed."""
    value = plan.get("saved_recovery_policy")
    if value is None:
        return False
    if value not in POLICIES:
        raise ValueError("unsupported saved recovery policy")
    return True


def adapt_extraction(extraction: dict, carrier: dict, policy: str = POLICY) -> dict:
    """Retain v7 semantics while mapping historical CorpusRunner field names."""
    result = dict(extraction)
    result["target_verification_effective_policy"] = result["target_verification_policy"]
    result["target_verification_policy"] = carrier["target_verification"]
    result["target_verification_warning"] = result["target_transcript_warning"]
    result["status"] = ("EXTRACTED_TARGET_WARN_PENDING_LISTENING" if result["target_transcript_warning"]
                        else "EXTRACTED_PENDING_LISTENING")
    result["saved_recovery_policy"] = policy
    return result


def validate_recovery_receipt(receipt: dict, enabled: bool, policy: str = POLICY) -> None:
    """Require matching plan opt-in and independently recompute final text guards."""
    extraction = receipt.get("extraction", {})
    opted = extraction.get("saved_recovery_policy")
    if not enabled:
        if opted or extraction.get("algorithm_version") in {ALGORITHM_VERSION, CONTEXT_ALGORITHM_VERSION}:
            raise ValueError("v7 saved candidate requires explicit recovery plan")
        return
    quality = receipt.get("verification", {})
    if policy not in POLICIES:
        raise ValueError("unsupported saved recovery policy")
    expected_algorithm = CONTEXT_ALGORITHM_VERSION if policy == CONTEXT_POLICY else ALGORITHM_VERSION
    if (opted != policy or extraction.get("algorithm_version") != expected_algorithm
            or extraction.get("comparison_policy") != POLICIES[policy]
            or quality.get("comparison_policy") != POLICIES[policy]
            or quality.get("model_id") != DEFAULT_ASR_MODEL
            or quality.get("model_revision") != DEFAULT_ASR_REVISION
            or quality.get("disposition") != "PASS" or quality.get("flags")
            or receipt.get("request", {}).get("verification") != "required"):
        raise ValueError("saved v7 candidate lacks required recovery/quality evidence")
    request = receipt["target_request"]
    comparison = compare_target_transcript(request["locale"], request["text"],
                                          quality.get("transcript", ""),
                                          ignore_accents=extraction.get("ignore_accents", True), policy=POLICIES[policy])
    if (comparison.score <= .8 or comparison.flags(require_word_count=True)
            or quality.get("score") != comparison.score):
        raise ValueError("saved v7 delivered transcript fails canonical quality guards")
