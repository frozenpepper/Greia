#!/usr/bin/env python3
"""Inventory and replace Greia speech through VoxStage and the selected masters.

See docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md before the long production run.
Planning never generates speech; run installs fresh, human-review-pending audio.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import signal
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from greia_voice_core.direction import DEFAULT_DELIVERY_FILE
from greia_voice_core.locking import InterprocessGenerationLock
from greia_voice_core.paths import voice_home
from greia_voice_corpus.inventory import CorpusInventory, digest, receipt_path, safe_target
from greia_voice_corpus.store import RunStore, write_json


def _external_work(raw: Path) -> Path:
    work = raw.expanduser().resolve()
    if work.is_relative_to(PROJECT_ROOT):
        raise ValueError("use a work directory outside Git for candidates, journal and original backups")
    return work


def _interrupt(*_args) -> None:
    raise KeyboardInterrupt


def plan_command(args) -> int:
    overrides = json.loads(args.overrides.read_text(encoding="utf-8")) if args.overrides else {}
    plan = CorpusInventory(PROJECT_ROOT, args.delivery_file, overrides).build()
    store = RunStore.create(_external_work(args.work_dir), plan)
    try:
        blocked = [r for r in plan["rows"] if r["state"] == "BLOCKED_METADATA"]
        with (store.work / "blocked.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=("path", "reason", "known_request"))
            writer.writeheader()
            writer.writerows({"path": r["path"], "reason": r["reason"], "known_request": json.dumps(r.get("request"), ensure_ascii=False)} for r in blocked)
        write_json(store.work / "overrides.template.json", {r["path"]: r["request"] for r in blocked})
        print(json.dumps({"work_dir": str(store.work), "summary": store.summary(), "source_census_advisories": len(plan["source_inventory_errors"])}, indent=2))
        return 2 if blocked else 0
    finally:
        store.close()


def status_command(args) -> int:
    store = RunStore(_external_work(args.work_dir))
    try:
        while True:
            payload = {"summary": store.summary(), "active": [p for p in store.problems() if p["state"] in {"GENERATING", "INSTALLING"}]}
            if args.details:
                payload["problems"] = store.problems()
            print(json.dumps(payload, indent=2, ensure_ascii=False), flush=True)
            if not args.watch:
                return 0
            time.sleep(10)
    finally:
        store.close()


def mutate_command(args) -> int:
    from greia_voice import build_engine
    from greia_voice_core.locking import NullGenerationLock
    from greia_voice_corpus.runner import CorpusRunner

    with InterprocessGenerationLock(voice_home() / "generation.lock"):
        store = RunStore(_external_work(args.work_dir))
        try:
            if store.root.resolve() != PROJECT_ROOT.resolve():
                raise ValueError("plan belongs to another checkout")
            if args.command == "restore":
                store.restore()
                print(f"Restored original files. {store.summary()}")
                return 0
            if args.command == "resolve":
                overrides = json.loads(args.overrides.read_text(encoding="utf-8"))
                pending = {r["path"] for r in store.plan["rows"] if store.state(r["path"]) == "BLOCKED_METADATA"}
                if set(overrides) - pending:
                    raise ValueError("resolve overrides must name only currently BLOCKED_METADATA paths")
                rebuilt = CorpusInventory(PROJECT_ROOT, args.delivery_file, overrides).build()
                indexed = {r["path"]: r for r in rebuilt["rows"]}
                updates = []
                for index, old in enumerate(store.plan["rows"]):
                    if old["path"] not in pending:
                        continue
                    new = indexed[old["path"]]
                    if any(new[key] != old[key] for key in ("original_sha256", "original_receipt_sha256")):
                        raise ValueError(f"blocked source changed since planning: {old['path']}")
                    store.plan["rows"][index] = new
                    updates.append(new)
                # Writing the plan first makes an interruption conservative:
                # unresolved DB rows remain blocked until resolve is run again.
                write_json(store.work / "plan.json", store.plan)
                for row in updates:
                    store.set_state(row["path"], row["state"], row["reason"])
                print(store.summary())
                return 2 if store.summary().get("BLOCKED_METADATA", 0) else 0
            if args.command == "retry":
                if not args.acknowledge_provider_idle:
                    raise ValueError("inspect the external job first, then supply --acknowledge-provider-idle")
                row = next((r for r in store.plan["rows"] if r["path"] == args.path), None)
                if not row or store.state(args.path) not in {"FAILED", "NEEDS_RECOVERY", "GENERATING"}:
                    raise ValueError("retry requires one FAILED/NEEDS_RECOVERY/GENERATING cue")
                target = safe_target(store.root, args.path)
                if digest(target) != row["original_sha256"] or digest(receipt_path(target)) != row["original_receipt_sha256"]:
                    raise ValueError("destination changed; recover transaction or create a new plan")
                candidate = store.work / "candidates" / args.path
                for path in (candidate, receipt_path(candidate), candidate.with_name(candidate.name + ".result.json")):
                    if path.exists():
                        archive = store.work / "failed-candidates" / str(time.time_ns()) / path.relative_to(store.work / "candidates")
                        archive.parent.mkdir(parents=True, exist_ok=True)
                        path.replace(archive)
                store.set_state(args.path, "READY", "operator inspected provider and authorized a fresh attempt")
                return 0
            if args.limit < 0:
                raise ValueError("--limit must be zero (all) or positive")
            with build_engine(generation_lock=NullGenerationLock(), character_provider="voxstage") as engine:
                return CorpusRunner(store, engine, args.verification).run(limit=args.limit, match=args.match)
        finally:
            store.close()


def review_command(args) -> int:
    from greia_voice_core.review import AudioReviewer, probe_cached_asr
    from greia_voice_core.verification import WhisperVerifier
    from greia_voice_corpus.review import CorpusReview

    with InterprocessGenerationLock(voice_home() / "generation.lock"):
        verifier = WhisperVerifier()
        readiness = ((True, f'Reusing saved ASR evidence from {args.evidence_dir}') if args.command == 'reassess'
                     else probe_cached_asr(verifier) if args.asr == "auto" else (False, "ASR explicitly disabled"))
        reviewer = AudioReviewer(verifier, asr=args.asr == "auto", asr_ready=readiness)
        corpus = CorpusReview(_external_work(args.work_dir), reviewer)
        if corpus.root.resolve() != PROJECT_ROOT.resolve():
            raise ValueError("review plan belongs to another checkout")
        return corpus.run(args.report_dir, limit=args.limit, match=args.match, evidence=getattr(args, "evidence_dir", None))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "run", "status", "restore", "retry", "resolve", "review", "reassess"):
        command = commands.add_parser(name)
        command.add_argument("--work-dir", type=Path, required=True)
        if name == "plan":
            command.add_argument("--overrides", type=Path)
            command.add_argument("--delivery-file", type=Path, default=DEFAULT_DELIVERY_FILE)
            command.set_defaults(func=plan_command)
        elif name == "status":
            command.add_argument("--details", action="store_true")
            command.add_argument("--watch", action="store_true", help="refresh every ten seconds; Ctrl-C to leave")
            command.set_defaults(func=status_command)
        elif name in {"review", "reassess"}:
            if name == "reassess":
                command.add_argument("--evidence-dir", type=Path, required=True)
            command.add_argument("--report-dir", type=Path, required=True)
            command.add_argument("--asr", choices=("auto", "off"), default="auto", help="use installed cached Whisper only; never download models")
            command.add_argument("--limit", type=int, default=0)
            command.add_argument("--match", default="*")
            command.set_defaults(func=review_command)
        else:
            command.set_defaults(func=mutate_command)
            if name == "run":
                command.add_argument("--limit", type=int, default=0, help="maximum cues this pass; zero means all remaining")
                command.add_argument("--match", default="*", help="repository-relative path glob, quoted")
                command.add_argument("--verification", choices=("off", "auto", "required"), default="off", help="off is explicit: host Whisper is currently unavailable; listening still required")
            elif name == "retry":
                command.add_argument("--path", required=True, help="one repository-relative cue path")
                command.add_argument("--acknowledge-provider-idle", action="store_true")
            elif name == "resolve":
                command.add_argument("--overrides", type=Path, required=True)
                command.add_argument("--delivery-file", type=Path, default=DEFAULT_DELIVERY_FILE)
    args = parser.parse_args(argv)
    signal.signal(signal.SIGTERM, _interrupt)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        message = ("Review interrupted; cached reports retained. Repeat the same review command to resume."
                   if args.command in {"review", "reassess"} else "Interrupted; journal retained. Inspect the provider job before retrying an in-flight cue.")
        print(message, file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
