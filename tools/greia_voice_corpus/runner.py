"""One warm VoiceEngine, visible heartbeat, and journaled replacement per cue."""
from contextlib import AbstractContextManager
import fnmatch
import json
import math
from pathlib import Path
import threading
import time

from greia_voice_core.models import VerificationMode, VoiceRequest, SpeechKind
from greia_voice_core.registry import CANONICAL_MANIFEST, VoiceRegistry
from .catalogues import derived_replacements
from .carrier_generation import CarrierExtractionFailure, generate_candidate
from .inventory import digest, receipt_path, safe_target
from .store import RunStore, write_json


class Heartbeat(AbstractContextManager):
    """Own one bounded console reporter; it never accesses SQLite or the model."""

    def __init__(self, label: str, interval: float = 15) -> None:
        self.label, self.interval = label, interval
        self.stop = threading.Event()
        self.started = time.monotonic()
        self.thread = threading.Thread(target=self._report, daemon=True)

    def _report(self) -> None:
        while not self.stop.wait(self.interval):
            print(f"  working {time.monotonic() - self.started:.0f}s | {self.label}", flush=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set()
        self.thread.join()


class CorpusRunner:
    """Coordinate synthesis and recoverable installation; never approve audio."""

    def __init__(self, store: RunStore, engine, verification: str = "off") -> None:
        self.store, self.engine = store, engine
        self.verification = VerificationMode(verification)

    def _validate_candidate(self, row: dict, candidate: Path) -> dict:
        receipt = json.loads(receipt_path(candidate).read_text(encoding="utf-8"))
        from .automatic_generation import enabled as automatic_enabled, validate_candidate as validate_automatic
        if automatic_enabled(self.store.plan):
            if self.verification is not VerificationMode.REQUIRED:
                raise ValueError("automatic corpus requires final verification")
            profile = VoiceRegistry.load(self.store.root).get(row["request"]["speaker"])
            return validate_automatic(self.store, row, candidate, receipt, profile)
        from .saved_recovery import recovery_enabled, validate_recovery_receipt
        validate_recovery_receipt(receipt, recovery_enabled(self.store.plan))
        if row.get("spoken_carrier"):
            carrier = row["spoken_carrier"]
            profile = VoiceRegistry.load(self.store.root).get(row["request"]["speaker"])
            if (receipt.get("kind") != "greia-spoken-carrier-target" or
                    receipt.get("mode") != carrier["mode"] or
                    receipt.get("carrier_plan") != carrier or
                    receipt.get("target_request") != row["request"] or
                    receipt.get("extraction", {}).get("status") != (
                        "EXTRACTED_PENDING_LISTENING" if carrier["target_verification"] == "required"
                        else "EXTRACTED_PENDING_LISTENING" if not receipt.get("extraction", {}).get("target_verification_warning")
                        else "EXTRACTED_TARGET_WARN_PENDING_LISTENING") or
                    receipt.get("extraction", {}).get("prefix") != carrier["prefix"] or
                    receipt.get("extraction", {}).get("target") != carrier["target"] or
                    receipt.get("extraction", {}).get("target_verification_policy") != carrier["target_verification"] or
                    receipt.get("extraction", {}).get("ignore_accents", True) != carrier.get("ignore_accents", True) or
                    receipt.get("provider_id") != "voxstage-voxcpm2" or
                    receipt.get("voice_id") != profile.voice_id or
                    receipt.get("reference_sha256") != profile.anchor_sha256 or
                    receipt.get("human_review") != "PENDING"):
                raise ValueError("spoken-carrier candidate evidence/master/review differs from frozen plan")
            if self.verification is VerificationMode.REQUIRED:
                from greia_voice_core.review_policy import ASR_PASS_THRESHOLD
                checked = receipt.get("verification", {})
                if (checked.get("disposition") != "PASS" or type(checked.get("score")) not in (int, float)
                        or not math.isfinite(checked["score"])
                        or checked["score"] <= ASR_PASS_THRESHOLD or checked.get("flags")):
                    raise ValueError("staged carrier candidate has no passing final-target quality check")
            if digest(candidate) != receipt["output"]["sha256"] or candidate.stat().st_size != receipt["output"]["bytes"]:
                raise ValueError("incomplete extracted candidate/receipt pair")
            raw = self.store.work / receipt["raw_audio"]["path"]
            raw_receipt = receipt_path(raw)
            if digest(raw) != receipt["raw_audio"]["sha256"] or digest(raw_receipt) != receipt["raw_audio"]["receipt_sha256"]:
                raise ValueError("spoken-carrier raw source or provider receipt changed")
            extracted = self.store.work / receipt["extracted_pcm"]["path"]
            if digest(extracted) != receipt["extracted_pcm"]["sha256"]:
                raise ValueError("spoken-carrier extracted PCM source changed")
            if "delivery_pcm" in receipt:
                delivered = self.store.work / receipt["delivery_pcm"]["path"]
                if digest(delivered) != receipt["delivery_pcm"]["sha256"]:
                    raise ValueError("spoken-carrier delivery PCM source changed")
            return receipt
        for key in ("speaker", "kind", "locale", "text", "delivery_prompt"):
            if receipt["request"].get(key) != row["request"][key]:
                raise ValueError(f"candidate {key} differs from plan: {row['path']}")
        profile = VoiceRegistry.load(self.store.root).get(row["request"]["speaker"])
        if (receipt.get("provider_id") != "voxstage-voxcpm2" or receipt.get("voice_id") != profile.voice_id
                or receipt.get("reference_sha256") != profile.anchor_sha256
                or receipt.get("human_review") != "PENDING"
                or receipt["generation_parameters"].get("delivery_prompt") != row["request"]["delivery_prompt"]):
            raise ValueError("candidate provider/master/performance/review identity differs from plan")
        if receipt["verification"]["disposition"] == "WARN":
            raise ValueError("candidate has unresolved ASR warning; original retained")
        if self.verification is VerificationMode.REQUIRED and receipt["request"].get("verification") != "required":
            raise ValueError("staged candidate was not produced with requested required verification")
        if digest(candidate) != receipt["output"]["sha256"] or candidate.stat().st_size != receipt["output"]["bytes"]:
            raise ValueError("incomplete candidate audio/receipt pair")
        return receipt

    def run(self, *, limit: int = 0, match: str = "*", continue_after_carrier_rejection: bool = False) -> int:
        store = self.store
        from .automatic_generation import enabled as automatic_enabled, natural_enabled, AutomaticRecoveryRequired
        if automatic_enabled(store.plan) and self.verification is not VerificationMode.REQUIRED:
            raise ValueError("automatic corpus requires final verification")
        if digest(store.root / CANONICAL_MANIFEST) != store.plan["registry_manifest_sha256"]:
            raise ValueError("canonical registry changed since planning; create a new plan")
        if any(store.state(r["path"]) == "RESTORED" for r in store.plan["rows"]):
            raise ValueError("this run was restored; create a new plan/work directory")
        registry = VoiceRegistry.load(store.root)
        if natural_enabled(store.plan):
            from .method_budget import MethodAttemptBudget
            MethodAttemptBudget(store).reconcile_mirror()
        for profile in registry.profiles.values():
            registry.verify_anchor(profile)
        store.recover()
        if any(store.summary().get(state, 0) for state in ("FAILED", "NEEDS_RECOVERY")):
            print("Resolve FAILED/NEEDS_RECOVERY cues before submitting more jobs (status --details).", flush=True)
            return 2
        total = sum(r["state"] == "READY" for r in store.plan["rows"])
        processed, started = 0, time.monotonic()
        for row in store.plan["rows"]:
            relative = row["path"]
            state = store.state(relative)
            if not fnmatch.fnmatchcase(relative, match) or state in {"DONE", "PRESERVED", "BLOCKED_METADATA", "FAILED", "NEEDS_RECOVERY"}:
                continue
            if limit and processed >= limit:
                break
            processed += 1
            done = store.summary().get("DONE", 0)
            print(f"[{done}/{total} done; this pass {processed}] {row['request']['speaker']}/{row['request']['locale']} | {relative}", flush=True)
            candidate = store.work / "candidates" / relative
            try:
                target = safe_target(store.root, relative)
                if digest(target) != row["original_sha256"] or digest(receipt_path(target)) != row["original_receipt_sha256"]:
                    raise ValueError("original audio/receipt changed since planning")
                # A crash during synthesis can leave a complete candidate, or an
                # uncertain external job. Only the complete pair can auto-resume.
                if state == "GENERATING" and not (candidate.is_file() and receipt_path(candidate).is_file()):
                    store.set_state(relative, "NEEDS_RECOVERY", "interrupted/uncertain provider job; inspect worker before retry")
                    return 2
                if not (candidate.exists() and receipt_path(candidate).exists()):
                    if candidate.exists() or receipt_path(candidate).exists():
                        raise ValueError("partial candidate; inspect before retry")
                    from .saved_recovery import recovery_enabled
                    if recovery_enabled(store.plan):
                        raise ValueError("saved recovery plans forbid synthesis; stage a complete candidate first")
                    store.set_state(relative, "GENERATING", "provider call in progress; interruption requires job inspection")
                    from .automatic_generation import enabled as automatic_enabled, generate_candidate as generate_automatic
                    if automatic_enabled(store.plan) or row.get("spoken_carrier"):
                        profile = registry.get(row["request"]["speaker"])
                        if natural_enabled(store.plan):
                            MethodAttemptBudget(store).assert_unstarted(relative)
                        else:
                            attempts_path = store.work / "carrier-attempt-counts.json"
                            attempts = json.loads(attempts_path.read_text()) if attempts_path.exists() else {}
                            count = int(attempts.get(relative, 0))
                            if count >= 3:
                                raise ValueError("spoken-carrier fresh-generation limit of 3 reached for this cue")
                            if automatic_enabled(store.plan) and count != 2:
                                raise ValueError("automatic final-take policy requires exactly two prior attempts")
                            attempts[relative] = count + 1
                            write_json(attempts_path, attempts)
                        with Heartbeat(relative):
                            if automatic_enabled(store.plan):
                                if self.verification is not VerificationMode.REQUIRED:
                                    raise ValueError("automatic corpus requires final verification")
                                generate_automatic(self.engine, store, row)
                            else:
                                generate_candidate(self.engine, store, row, profile, self.verification.value)
                    else:
                        request = VoiceRequest(**{k: v for k, v in row["request"].items() if k != "kind"},
                                               kind=SpeechKind(row["request"]["kind"]), output=candidate,
                                               verification=self.verification, max_attempts=1)
                        with Heartbeat(relative):
                            result = self.engine.generate(request)
                        write_json(candidate.with_name(candidate.name + ".result.json"), result.to_dict())
                        if result.disposition.value != "REVIEW_REQUIRED":
                            raise ValueError(f"{result.disposition.value}: {result.detail}")
                receipt = self._validate_candidate(row, candidate)
                if row.get("spoken_carrier") or automatic_enabled(store.plan):
                    receipt["output"]["path"] = relative
                else:
                    receipt["request"]["output"] = relative
                receipt["output"]["path"] = relative
                if automatic_enabled(store.plan):
                    receipt["request"]["output"] = relative
                receipt["corpus_replacement"] = {"original_sha256": row["original_sha256"], "owner_authorization": "2026-10-19 corpus regeneration; listening pending"}
                write_json(receipt_path(candidate), receipt)
                replacements = {relative: candidate, str(receipt_path(Path(relative))): receipt_path(candidate)}
                replacements.update(derived_replacements(store.root, relative, receipt, store.work / "metadata" / relative))
                transaction = store.prepare(relative, replacements)
                store.install(transaction)
                elapsed = time.monotonic() - started
                print(f"  DONE (listening pending) | pass elapsed {elapsed / 60:.1f}m | {store.summary()}", flush=True)
            except Exception as exc:
                # Installation must retain its journal state for recovery. Never
                # retry an uncertain synthesis automatically under another job ID.
                failure_state = ("INSTALLING" if store.state(relative) == "INSTALLING" else
                                 "NEEDS_RECOVERY" if isinstance(exc, AutomaticRecoveryRequired) else
                                 "PRESERVED" if automatic_enabled(store.plan) and isinstance(exc, CarrierExtractionFailure)
                                 else "FAILED")
                store.set_state(relative, failure_state, str(exc))
                print(f"  FAILED | {relative} | {exc}", flush=True)
                if continue_after_carrier_rejection and isinstance(exc, CarrierExtractionFailure):
                    print("  Continuing after fail-closed carrier rejection; original and raw evidence retained.", flush=True)
                    continue
                # Stop the producer on provider or installation failure. A worker
                # may still be busy after a timeout; submitting the next cue can
                # create a growing queue and conceal the first broken boundary.
                return 2
        summary = store.summary()
        print(f"Summary: {summary}", flush=True)
        return 2 if any(summary.get(s, 0) for s in ("FAILED", "NEEDS_RECOVERY", "BLOCKED_METADATA", "INSTALLING", "GENERATING")) else (3 if summary.get("READY", 0) else 0)
