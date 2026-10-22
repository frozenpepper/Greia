"""Versioned corpus continuation through the normal automatic short API."""
from __future__ import annotations
import json
from pathlib import Path
from greia_voice_core.models import VoiceRequest, SpeechKind, VerificationMode
from greia_voice_core.number_comparison import COMPARISON_POLICY, compare_target_transcript
from greia_voice_core.asr_policy import DEFAULT_ASR_MODEL, DEFAULT_ASR_REVISION
from greia_voice_core.short_policy import ShortPhrasePolicy, COMPOSITION_POLICY
from greia_voice_core.direction import character_delivery
from voice_carrier_search import ALGORITHM_VERSION
from .inventory import digest, receipt_path
from .store import write_json
from .carrier_generation import CarrierExtractionFailure

POLICY = "automatic-short-v7-period-warm-v2"
NATURAL_POLICY = "automatic-natural-context-v1"


def natural_enabled(plan):
    return plan.get("automatic_short_generation_policy") == NATURAL_POLICY


class AutomaticRecoveryRequired(RuntimeError):
    """Unknown provider/ASR/IO outcome; stop without another submission."""


def enabled(plan: dict) -> bool:
    value = plan.get("automatic_short_generation_policy")
    if value is not None and value not in {POLICY, NATURAL_POLICY}:
        raise ValueError("unsupported automatic short corpus policy")
    return value in {POLICY, NATURAL_POLICY}


def request_for(row: dict, candidate: Path, *, max_attempts: int = 1) -> VoiceRequest:
    """One automatic generation only; cumulative reservations live in RunStore."""
    if row.get("spoken_carrier"):
        raise ValueError("automatic corpus row must not wrap a second carrier")
    data = {k:v for k,v in row["request"].items() if k not in {"kind","max_attempts","verification","short_text_mode","output"}}
    return VoiceRequest(**data, kind=SpeechKind(row["request"]["kind"]), output=candidate,
                        max_attempts=max_attempts, verification=VerificationMode.REQUIRED, short_text_mode="on")


def generate_candidate(engine, store, row: dict) -> None:
    """Delegate to VoiceEngine; continue only a durable one-take quality failure."""
    candidate = store.work / "candidates" / row["path"]
    maximum = 3 if natural_enabled(store.plan) else 1
    request = request_for(row, candidate, max_attempts=maximum)
    if natural_enabled(store.plan):
        from greia_voice_core.natural_carrier import NaturalCarrierPolicy
        policy=NaturalCarrierPolicy()
        prefix,text,delivery=policy.composite(request,request.delivery_prompt)
        expected={'prefix':prefix,'composite_text':text,'effective_delivery':delivery,
                  'composition_policy':policy.composition_policy,'comparison_policy':COMPARISON_POLICY}
        if row.get('natural_carrier') != expected:
            raise ValueError('frozen natural recipe differs before submission')
    result = engine.generate(request)
    write_json(candidate.with_name(candidate.name + ".result.json"), result.to_dict())
    if result.disposition.value == "REVIEW_REQUIRED" and 1 <= result.attempts <= maximum:
        return
    if result.evidence_dir:
        state_path = result.evidence_dir / "state.json"
        state = json.loads(state_path.read_text())
        if (state.get("status") == "FAILED_QUALITY" and result.attempts == maximum
                and state.get("request") == request.to_dict() and len(state.get("history", [])) == maximum):
            evidence = {"result": result.to_dict(), "state": state, "state_path": str(state_path)}
            write_json(store.work / "carrier-evidence" / (row["path"] + ".failure.json"), evidence)
            raise CarrierExtractionFailure("automatic short final take failed quality; original preserved", evidence=evidence)
    raise AutomaticRecoveryRequired("automatic short outcome needs exact provider/evidence recovery: " + result.detail)


def validate_candidate(store, row: dict, candidate: Path, receipt: dict, profile) -> dict:
    """Validate the normal API's target, selected master, raw take and final gate."""
    natural = natural_enabled(store.plan)
    request = request_for(row, candidate, max_attempts=3 if natural else 1)
    short = receipt.get("short_phrase", {})
    extraction = short.get("extraction", {})
    quality = short.get("quality", {})
    from greia_voice_core.natural_carrier import NaturalCarrierPolicy
    policy = NaturalCarrierPolicy() if natural else ShortPhrasePolicy()
    prefix, composite, delivery = policy.composite(request, character_delivery()[profile.character])
    actual_request = dict(receipt.get("request", {}))
    if actual_request.get("output") == row["path"]:
        actual_request["output"] = str(candidate)
    if (actual_request != request.to_dict() or receipt.get("provider_id") != "voxstage-voxcpm2"
            or receipt.get("voice_id") != profile.voice_id or receipt.get("reference_sha256") != profile.anchor_sha256
            or receipt.get("human_review") != "PENDING" or type(receipt.get("attempts")) is not int
            or not 1 <= receipt["attempts"] <= (3 if natural else 1)
            or short.get("mode") != "automatic-carrier" or short.get("composition_policy") != policy.composition_policy
            or short.get("prefix") != prefix
            or short.get("composite_text") != composite or short.get("effective_delivery") != delivery
            or extraction.get("algorithm_version") != ALGORITHM_VERSION
            or extraction.get("comparison_policy") != COMPARISON_POLICY
            or extraction.get("target") != request.text
            or extraction.get("ignore_accents") != request.ignore_accents
            or receipt.get("verification", {}).get("disposition") != "PASS"
            or receipt.get("verification", {}).get("score") != quality.get("score")
            or type(quality.get("score")) not in (int, float)
            or quality.get("comparison_policy") != COMPARISON_POLICY
            or quality.get("disposition") != "PASS" or quality.get("flags")
            or quality.get("model_id") != DEFAULT_ASR_MODEL or quality.get("model_revision") != DEFAULT_ASR_REVISION):
        raise ValueError("automatic short candidate differs from the planned master/request/policy or final gate")
    if natural:
        expected = {"prefix":prefix,"composite_text":composite,"effective_delivery":delivery,
                    "composition_policy":policy.composition_policy,"comparison_policy":COMPARISON_POLICY}
        if row.get("natural_carrier") != expected:
            raise ValueError("natural carrier differs from frozen recipe")
        from .method_budget import MethodAttemptBudget
        ledger = MethodAttemptBudget(store).snapshot()["entries"][row["path"]]
        if (ledger['prior_count'] != row['historical_attempts']
                or len(ledger['attempts']) != receipt['attempts']
                or len(short.get('history',[])) != receipt['attempts']
                or any(a['evidence_dir'] != short.get('evidence_dir') or a['request'] != request.to_dict()
                       for a in ledger['attempts'])):
            raise ValueError("natural candidate lacks exact reserved-attempt provenance")
    comparison = compare_target_transcript(request.locale,request.text,quality.get("transcript", ""),ignore_accents=request.ignore_accents)
    if comparison.score <= .8 or comparison.flags(require_word_count=True) or comparison.score != quality.get("score"):
        raise ValueError("automatic short delivered text fails canonical guards")
    raw = Path(extraction["source"])
    raw_receipt = Path(extraction["source_provider_receipt"])
    if digest(raw) != extraction["source_sha256"] or digest(raw_receipt) != extraction["source_provider_receipt_sha256"]:
        raise ValueError("automatic short raw provider evidence changed")
    rec = json.loads(raw_receipt.read_text())
    if (rec.get("voice_id") != profile.voice_id or rec.get("reference_sha256") != profile.anchor_sha256
            or rec.get("request", {}).get("text") != composite
            or rec.get("request", {}).get("delivery_prompt") != delivery
            or any(rec.get("request", {}).get(k) != request.to_dict().get(k)
                   for k in ("speaker", "kind", "locale", "cue_id"))
            or rec.get("request", {}).get("short_text_mode") != "off"
            or rec.get("generation_parameters") != receipt.get("generation_parameters")):
        raise ValueError("automatic short raw request/master/provider differs")
    if digest(candidate) != receipt["output"]["sha256"] or candidate.stat().st_size != receipt["output"]["bytes"]:
        raise ValueError("automatic short output/receipt mismatch")
    return receipt
