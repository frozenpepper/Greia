"""Resumable sidecar review of installed DONE cues; source and journal are read-only."""
from collections import Counter
from datetime import datetime, timezone
import csv
import fnmatch
import hashlib
import json
from pathlib import Path
import sqlite3

from greia_voice_core.models import VoiceRequest, SpeechKind
from greia_voice_core.registry import VoiceRegistry
from greia_voice_core.review import POLICY_VERSION
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
        if receipt.get("generation_parameters", {}).get("delivery_prompt") != row["request"]["delivery_prompt"]:
            problems.append("RECEIPT_PERFORMANCE_MISMATCH")
        if receipt["output"].get("sha256") != digest(path) or receipt["output"].get("bytes") != path.stat().st_size:
            problems.append("AUDIO_RECEIPT_MISMATCH")
        return receipt, problems

    def run(self, report: Path, *, limit: int = 0, match: str = "*") -> int:
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
                         "threshold": getattr(self.reviewer.verifier, "pass_threshold", .72)}
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
                    with Heartbeat(f"review {relative}"):
                        result = self.reviewer.review(request, path)
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
