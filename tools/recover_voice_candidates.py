#!/usr/bin/env python3
"""Recover failed frozen-priority carrier takes with v7, without synthesis.

Stage first; --install resumes that exact work directory through CorpusRunner.
Never rewrites source plans, source media, receipts or cumulative take budgets.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src"), str(ROOT)]
from finish_voice_priority import CachedTranscriber, collect_history
from greia_voice_core.audio import AudioPipeline
from greia_voice_core.locking import InterprocessGenerationLock
from greia_voice_core.paths import voice_home
from greia_voice_core.registry import CANONICAL_MANIFEST, VoiceRegistry
from greia_voice_corpus.carrier_generation import prepare_saved_candidate, CarrierExtractionFailure
from greia_voice_corpus.inventory import digest, receipt_path, safe_target
from greia_voice_corpus.runner import CorpusRunner
from greia_voice_corpus.saved_recovery import POLICY, POLICIES, CONTEXT_POLICY
from greia_voice_corpus.store import RunStore, write_json


class SavedAudioEngine:
    """Existing packaging collaborator with no provider or generation capability."""

    def __init__(self):
        self.audio = AudioPipeline()

    def generate(self, request):
        raise RuntimeError("SYNTHESIS_FORBIDDEN: saved-source recovery only")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def prepare_plan(args, root=ROOT):
    """Freeze only failed source rows inside the unchanged owner priority set."""
    policy = getattr(args, "policy", POLICY)
    if policy not in POLICIES:
        raise ValueError("unsupported saved recovery policy")
    if policy == CONTEXT_POLICY and not getattr(args, "source_selection", None):
        raise ValueError("context recovery requires pinned source selection")
    source = args.source_work.resolve()
    priority = read(args.priority_file)
    selected = {r["path"] for r in priority["records"]}
    if len(selected) != len(priority["records"]):
        raise ValueError("duplicated frozen priority IDs")
    priority_rows = {r["path"]: r for r in priority["records"]}
    if not source.is_relative_to(args.history_root.resolve()):
        raise ValueError("source work must lie inside the history root")
    plan = read(source / "plan.json")
    if plan.get("saved_recovery_policy"):
        raise ValueError("use the original frozen source run, not a recovery run")
    if Path(plan["root"]).resolve() != root.resolve():
        raise ValueError("source plan belongs to another project")
    if digest(root / CANONICAL_MANIFEST) != plan["registry_manifest_sha256"]:
        raise ValueError("selected registry differs from source plan")
    with sqlite3.connect(f"file:{source / 'state.sqlite3'}?mode=ro", uri=True) as db:
        states = dict(db.execute("SELECT path,state FROM cues"))
    selection = None
    if getattr(args, "source_selection", None):
        from greia_voice_corpus.source_selection import load_selection
        selection = load_selection(args.source_selection, source, args.priority_file)
    rows = []
    seen = set()
    for original in plan["rows"]:
        relative = original["path"]
        if relative in seen:
            raise ValueError("duplicated source plan path")
        seen.add(relative)
        if selection is not None:
            if relative not in selection:
                continue
            if states.get(relative) not in {"FAILED", "PRESERVED"}:
                raise ValueError("selected source has an uncertain/non-failed journal state")
        elif states.get(relative) != "FAILED":
            continue
        if relative not in selected or not original.get("spoken_carrier"):
            raise ValueError("failed source lies outside frozen carrier priority")
        frozen = priority_rows[relative]
        if any(original["request"].get(key) != frozen.get(key)
               for key in ("speaker", "locale", "text", "cue_id")):
            raise ValueError("source semantic request differs from frozen priority: " + relative)
        target = safe_target(root, relative)
        if (digest(target) != original["original_sha256"]
                or digest(receipt_path(target)) != original["original_receipt_sha256"]):
            raise ValueError("destination changed since source planning: " + relative)
        if selection is not None:
            from greia_voice_corpus.source_selection import validate_selected_source
            validate_selected_source(selection[relative], source, original)
        row = copy.deepcopy(original)
        row.update(state="READY", reason="v7 saved-source recovery; synthesis forbidden")
        rows.append(row)
    if selection is not None and len(rows) != len(selection):
        raise ValueError("selected source has no exact plan row")
    if not rows:
        raise ValueError("no failed saved source rows")
    result = {**plan, "rows": rows, "saved_recovery_policy": policy,
              "saved_recovery_source": {"work": str(source),
                  "plan_sha256": digest(source / "plan.json"),
                  "priority_file": str(args.priority_file.resolve()),
                  "priority_sha256": digest(args.priority_file)}}
    if selection is not None:
        result["saved_recovery_source"]["selection_file"] = str(args.source_selection.resolve())
        result["saved_recovery_source"]["selection_sha256"] = digest(args.source_selection)
        result["saved_recovery_source"]["selected_provider_sources"] = selection
    return result


def stage(args, root=ROOT):
    """Validate/copy immutable sources and prepare every eligible cut, no install."""
    plan = prepare_plan(args, root)
    source = args.source_work.resolve()
    counts, _, _ = collect_history(args.history_root.resolve(), {r["path"] for r in plan["rows"]})
    registry = VoiceRegistry.load(root)
    for profile in registry.profiles.values():
        registry.verify_anchor(profile)
    store = RunStore.create(args.work_dir, plan)
    outcomes = []
    try:
        write_json(store.work / "carrier-attempt-counts.json", counts)
        engine = SavedAudioEngine()
        if plan["saved_recovery_policy"] == CONTEXT_POLICY:
            from greia_voice_core.context_evidence import RecordedTranscriber
            transcriber = RecordedTranscriber(args.cache_root)
        else:
            transcriber = CachedTranscriber(args.cache_root)
        for index, row in enumerate(plan["rows"], 1):
            relative = row["path"]
            raw = source / "carrier-raw" / (relative + ".raw.wav")
            dest = store.work / "carrier-raw" / (relative + ".raw.wav")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(raw, dest)
            shutil.copyfile(receipt_path(raw), receipt_path(dest))
            try:
                prepare_saved_candidate(engine, store, row, registry.get(row["request"]["speaker"]),
                                        "required", transcriber=transcriber)
                CorpusRunner(store, engine, "required")._validate_candidate(
                    row, store.work / "candidates" / relative)
                state, detail = "STAGED_PASS", "human listening pending"
            except CarrierExtractionFailure as exc:
                state, detail = "REJECTED_SAVED", str(exc)
                store.set_state(relative, "PRESERVED", detail)
            outcomes.append({"path": relative, "result": state, "detail": detail,
                             "source_sha256": digest(raw),
                             "source_receipt_sha256": digest(receipt_path(raw)),
                             "cumulative_takes": counts.get(relative, 0)})
            write_json(store.work / "recovery-results.json", outcomes)
            print(f"[{index}/{len(plan['rows'])}] {state} | {relative}", flush=True)
        write_json(store.work / "stage-complete.json", {
            "policy": plan["saved_recovery_policy"], "plan_sha256": digest(store.work / "plan.json"),
            "counts_sha256": digest(store.work / "carrier-attempt-counts.json"),
            "results_sha256": digest(store.work / "recovery-results.json"),
            "source_plan_sha256": digest(source / "plan.json"),
            "passing": sum(r["result"] == "STAGED_PASS" for r in outcomes),
            "rejected": sum(r["result"] == "REJECTED_SAVED" for r in outcomes),
            "synthesis_calls": 0, "installed": 0})
        return 0
    finally:
        store.close()


def install(work):
    """Install only a fully staged manifest; recover interrupted transactions."""
    store = RunStore(work)
    try:
        marker = read(work / "stage-complete.json")
        if (store.plan.get("saved_recovery_policy") not in POLICIES
                or marker.get("policy") != store.plan.get("saved_recovery_policy")
                or marker["plan_sha256"] != digest(work / "plan.json")
                or marker["counts_sha256"] != digest(work / "carrier-attempt-counts.json")
                or marker["results_sha256"] != digest(work / "recovery-results.json")):
            raise ValueError("staged recovery manifest/evidence changed")
        return CorpusRunner(store, SavedAudioEngine(), "required").run()
    finally:
        store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--source-work", type=Path)
    parser.add_argument("--priority-file", type=Path)
    parser.add_argument("--history-root", type=Path)
    parser.add_argument("--cache-root", type=Path)
    parser.add_argument("--source-selection", type=Path)
    parser.add_argument("--policy", choices=sorted(POLICIES), default=POLICY)
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    work = args.work_dir.resolve()
    if work.is_relative_to(ROOT):
        parser.error("use an external work directory")
    args.work_dir = work
    with InterprocessGenerationLock(voice_home() / "generation.lock"):
        if args.install:
            return install(work)
        if any(getattr(args, key) is None for key in ("source_work", "priority_file", "history_root", "cache_root")):
            parser.error("staging requires source-work, priority-file, history-root and cache-root")
        return stage(args)


if __name__ == "__main__":
    raise SystemExit(main())
