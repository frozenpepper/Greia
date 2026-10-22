"""Resumable sidecar review of installed DONE cues; source and journal are read-only."""
from collections import Counter
from datetime import datetime, timezone
from dataclasses import replace
import csv
import fnmatch
import hashlib
import json
from pathlib import Path
import sqlite3

from greia_voice_core.models import VoiceRequest, SpeechKind
from greia_voice_core.registry import VoiceRegistry
from greia_voice_core.asr_policy import DEFAULT_ASR_MODEL, DEFAULT_ASR_REVISION
from greia_voice_core.review_policy import POLICY_VERSION, ASR_PASS_THRESHOLD, reassess_result
from .inventory import digest, receipt_path, safe_target
from .runner import Heartbeat
from .store import write_json, atomic_bytes


class CorpusReview:
    """Own report/cache lifecycle while delegating audio and ASR to engine collaborators."""

    def __init__(self, work: Path, reviewer) -> None:
        self.work, self.reviewer = work.resolve(), reviewer
        self.plan = json.loads((self.work / "plan.json").read_text(encoding="utf-8"))
        self.root = Path(self.plan["root"])
        self.registry = VoiceRegistry.load(self.root)

    def _metadata(self, row: dict, path: Path) -> tuple[dict, list[str]]:
        receipt = json.loads(receipt_path(path).read_text(encoding="utf-8"))
        problems = []
        for key in ("speaker", "kind", "locale", "text", "cue_id", "delivery_prompt"):
            if receipt["request"].get(key) != row["request"].get(key):
                problems.append(f"RECEIPT_REQUEST_MISMATCH:{key}")
        profile = self.registry.get(row["request"]["speaker"])
        if receipt.get("voice_id") != profile.voice_id or receipt.get("reference_sha256") != profile.anchor_sha256:
            problems.append("RECEIPT_MASTER_MISMATCH")
        if receipt.get("provider_id") != "voxstage-voxcpm2":
            problems.append("RECEIPT_PROVIDER_MISMATCH")
        expected_delivery = (row.get("spoken_carrier", {}).get("composite_delivery_prompt")
                             if row.get("spoken_carrier") else row["request"]["delivery_prompt"])
        if receipt.get("generation_parameters", {}).get("delivery_prompt") != expected_delivery:
            problems.append("RECEIPT_PERFORMANCE_MISMATCH")
        if receipt["output"].get("sha256") != digest(path) or receipt["output"].get("bytes") != path.stat().st_size:
            problems.append("AUDIO_RECEIPT_MISMATCH")
        return receipt, problems

    @staticmethod
    def _apply_carrier_review_flags(result: dict, row: dict, receipt: dict) -> dict:
        """Keep a target transcription warning visible through automated review."""
        extraction = receipt.get("extraction", {})
        if row.get("spoken_carrier") and extraction.get("target_verification_warning"):
            from greia_voice_core.verification import normalize_transcript
            target = row["request"]["text"]
            ignore_accents = result.get("ignore_accents", row["request"].get("ignore_accents", True))
            kept = extraction.get("extracted_transcript")
            raw_suffix = extraction.get("unremoved_raw_aligned_tokens")
            if (ignore_accents and isinstance(kept, str) and isinstance(raw_suffix, list)
                    and normalize_transcript(kept) == normalize_transcript(target)
                    and normalize_transcript(" ".join(raw_suffix)) == normalize_transcript(target)):
                result["carrier_accent_only_warning_ignored"] = True
                result["flags"] = [f for f in result.get("flags", []) if f != "CARRIER_TARGET_TRANSCRIPT_MISMATCH"]
                return reassess_result(result)
            flags = result.setdefault("flags", [])
            if "CARRIER_TARGET_TRANSCRIPT_MISMATCH" not in flags:
                flags.append("CARRIER_TARGET_TRANSCRIPT_MISMATCH")
            if result.get("status") == "PASS":
                result["status"] = "WARN"
        return result

    def run(self, report: Path, *, limit: int = 0, match: str = "*", evidence: Path | None = None) -> int:
        if limit < 0:
            raise ValueError("review limit must be nonnegative")
        report = report.resolve()
        if report.is_relative_to(self.root.resolve()) or report.is_relative_to(self.work) or self.work.is_relative_to(report):
            raise ValueError("use a separate external report directory, outside the corpus run and repository")
        report.mkdir(parents=True, exist_ok=True)
        configuration = {"policy_version": POLICY_VERSION, "plan_sha256": digest(self.work / "plan.json"),
                         "registry": {name: {"voice_id": p.voice_id, "anchor_sha256": p.anchor_sha256} for name, p in self.registry.profiles.items()},
                         "asr": self.reviewer.asr, "verifier": self.reviewer.verifier.verifier_id,
                         "model": getattr(self.reviewer.verifier, "model_id", "injected"),
                         "model_revision": DEFAULT_ASR_REVISION if getattr(self.reviewer.verifier, "model_id", None) == DEFAULT_ASR_MODEL else None,
                         "threshold": getattr(self.reviewer.verifier, "pass_threshold", ASR_PASS_THRESHOLD),
                         "ignore_accents_override": getattr(self.reviewer, "ignore_accents", None)}
        source_rows, source_config = {}, None
        if evidence:
            evidence = evidence.resolve()
            if evidence == report:
                raise ValueError('reassessment requires a fresh report directory')
            source_config = json.loads((evidence / 'configuration.json').read_text())
            summary = json.loads((evidence / 'summary.json').read_text())
            if not summary.get('complete') or not summary.get('full_corpus_coverage'):
                raise ValueError('reassessment requires completed full-corpus evidence')
            for key in ('plan_sha256', 'registry'):
                if source_config.get(key) != configuration[key]:
                    raise ValueError(f'saved evidence differs from current {key}')
            source_rows = {r['path']: r for r in
                           map(json.loads, (evidence / 'review.jsonl').read_text().splitlines())}
            configuration['evidence_source'] = str(evidence)
            configuration['execution'] = 'REASSESSED_SAVED_EVIDENCE'
            configuration['source_asr_model'] = source_config.get('model')
            configuration['source_asr_verifier'] = source_config.get('verifier')
            configuration['source_asr_model_revision'] = source_config.get('model_revision')
        config_path = report / "configuration.json"
        if config_path.exists() and json.loads(config_path.read_text()) != configuration:
            raise ValueError("report configuration differs; choose a new directory")
        write_json(config_path, configuration)
        for profile in self.registry.profiles.values():
            self.registry.verify_anchor(profile)
        with sqlite3.connect(f"file:{self.work / 'state.sqlite3'}?mode=ro", uri=True) as db:
            states = dict(db.execute("SELECT path,state FROM cues"))
        generation_problems = {path: state for path, state in states.items() if state not in {"DONE", "PRESERVED"}}
        eligible = [row for row in self.plan["rows"] if states.get(row["path"]) == "DONE"]
        selected = [row for row in eligible if fnmatch.fnmatchcase(row["path"], match)]
        if limit:
            selected = selected[:limit]
        results = []
        write_json(report / "summary.json", {"complete": False, "selected": len(selected), "phase": "RUNNING"})
        for index, row in enumerate(selected, 1):
            relative = row["path"]
            cache = report / "records" / (hashlib.sha256(relative.encode()).hexdigest() + ".json")
            fingerprint = None
            try:
                path = safe_target(self.root, relative)
                before = (digest(path), digest(receipt_path(path)))
                fingerprint = hashlib.sha256(json.dumps([configuration, row["request"], before], sort_keys=True).encode()).hexdigest()
                if cache.exists():
                    cached = json.loads(cache.read_text())
                    if cached.get("fingerprint") == fingerprint and cached.get("status") in {"PASS", "WARN", "FAIL"} and cached.get("error") is None:
                        results.append(cached)
                        print(f"[{index}/{len(selected)}] cached {cached['status']} | {relative}", flush=True)
                        continue
                receipt, flags = self._metadata(row, path)
                if flags:
                    result = {"status": "FAIL", "flags": flags, "asr": {"status": "NOT_RUN_METADATA_FAILURE"}}
                else:
                    request = VoiceRequest(**{k: v for k, v in row["request"].items() if k != "kind"}, kind=SpeechKind(row["request"]["kind"]))
                    if evidence:
                        old = source_rows.get(relative)
                        old_fingerprint = hashlib.sha256(json.dumps([source_config, row['request'], before], sort_keys=True).encode()).hexdigest()
                        if not old or old.get('fingerprint') != old_fingerprint:
                            raise ValueError('saved evidence is absent or audio/receipt changed; run a fresh live review')
                        result = reassess_result(old, expected_text=request.text, locale=request.language,
                                                 ignore_accents=(self.reviewer.ignore_accents if self.reviewer.ignore_accents is not None
                                                                 else request.ignore_accents))
                        result['source_reviewed_at_utc'] = old.get('reviewed_at_utc')
                    else:
                        with Heartbeat(f"review {relative}"):
                            result = self.reviewer.review(request, path)
                    result = self._apply_carrier_review_flags(result, row, receipt)
                if before != (digest(path), digest(receipt_path(path))):
                    raise ValueError("audio/receipt changed during review; run after production is idle")
                result["human_review_unchanged"] = receipt.get("human_review", "UNKNOWN")
            except Exception as exc:
                result = {"status": "FAIL", "flags": ["REVIEW_ERROR"], "error": str(exc), "asr": {"status": "NOT_RUN_ERROR"}}
            result.update(path=relative, fingerprint=fingerprint, reviewed_at_utc=datetime.now(timezone.utc).isoformat(),
                          request=row["request"], human_acceptance_granted=False)
            write_json(cache, result)
            results.append(result)
            print(f"[{index}/{len(selected)}] {result['status']} | {relative} | {','.join(result.get('flags', []))}", flush=True)
            if index % 25 == 0:
                write_json(report / "summary.json", {"complete": False, "processed": index, "selected": len(selected), "counts": dict(Counter(r["status"] for r in results))})
        counts = Counter(r["status"] for r in results)
        asr_counts = Counter(r["asr"]["status"] for r in results)
        full_coverage = bool(eligible) and len(results) == len(eligible) and not generation_problems
        speech_complete = self.reviewer.asr and all(r["asr"]["status"] in {"PASS", "WARN", "NOT_APPLICABLE_POLICY"} for r in results)
        summary = {"complete": True, "scope": "AUTOMATED_SCREEN_NOT_HUMAN_ACCEPTANCE", "full_corpus_coverage": full_coverage,
                   "eligible_asr_complete": bool(speech_complete), "counts": dict(counts), "asr_counts": dict(asr_counts),
                   "selected": len(results), "total_done": len(eligible), "preserved": sum(s == "PRESERVED" for s in states.values()),
                   "generation_problems": generation_problems, "asr_readiness": self.reviewer.asr_ready,
                   "unassessed": ["speaker identity", "acting/mood", "pronunciation truth", "independent language identification", "small-speaker intelligibility"],
                   "human_acceptance_granted": False}
        atomic_bytes(report / "review.jsonl", "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results).encode())
        fields = ("path", "status", "flags", "asr_status", "score", "expected", "transcript", "error")
        with (report / "listening_queue.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            priority = {"FAIL": 0, "BLOCKED": 1, "WARN": 2, "PASS": 3}
            for row in sorted(results, key=lambda r: (priority[r["status"]], r["path"])):
                writer.writerow({"path": row["path"], "status": row["status"], "flags": ";".join(row.get("flags", [])),
                                 "asr_status": row["asr"]["status"], "score": row["asr"].get("score"),
                                 "expected": row["request"]["text"], "transcript": row["asr"].get("transcript", ""), "error": row.get("error", "")})
        write_json(report / "summary.json", summary)
        print(json.dumps(summary, indent=2), flush=True)
        if counts.get("FAIL") or counts.get("WARN"):
            return 2
        return 0 if full_coverage and speech_complete and not counts.get("BLOCKED") else 3
