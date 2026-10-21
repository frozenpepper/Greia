#!/usr/bin/env python3
"""Finish an owner-frozen priority corpus using existing VoiceEngine transactions.

No scope discovery: priority JSON must contain exact records from a previous
triage. Saved provider takes are rechecked before fresh, bounded production.
State and ASR evidence live in the external work directory, never in Git.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src"), str(ROOT)]
from greia_voice import build_engine
from greia_voice_core.locking import InterprocessGenerationLock, NullGenerationLock
from greia_voice_core.paths import voice_home
from greia_voice_core.registry import VoiceRegistry, CANONICAL_MANIFEST
from greia_voice_core.review import signal_metrics
from greia_voice_core.verification import transcript_similarity
from greia_voice_core.asr_policy import DEFAULT_ASR_MODEL, DEFAULT_ASR_REVISION
from greia_voice_corpus.carriers import freeze_row
from greia_voice_corpus.carrier_generation import prepare_saved_candidate, CarrierExtractionFailure
from greia_voice_corpus.inventory import digest, receipt_path, safe_target
from greia_voice_corpus.runner import CorpusRunner
from greia_voice_corpus.store import RunStore, write_json
from voice_carrier import _whisper_transcribe


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


class CachedTranscriber:
    """Cache exact audio/locale/model observations; never reroll ASR for a pass."""
    def __init__(self, work):
        self.work = work

    def __call__(self, audio, locale):
        identity = [digest(audio), locale, DEFAULT_ASR_MODEL, DEFAULT_ASR_REVISION,
                    "temperature=0;previous_text=false;prompt=null;word_timestamps=true"]
        key = hashlib.sha256(json.dumps(identity).encode()).hexdigest()
        dest = self.work / "asr-cache" / (key + ".json")
        if dest.exists():
            return read(dest)["result"]
        result = _whisper_transcribe(audio, locale)
        write_json(dest, {"identity": identity, "result": result})
        return result


def final_quality(engine, audio, row, transcribe, work):
    decoded = work / "current-decoded" / (row["path"] + ".wav")
    decoded.parent.mkdir(parents=True, exist_ok=True)
    engine.audio.decode_for_review(audio, decoded)
    result = transcribe(decoded, row["request"]["locale"])
    score = transcript_similarity(row["request"]["text"], result.get("text", ""), ignore_accents=True)
    try:
        metrics, flags = signal_metrics(decoded)
    except ValueError as exc:
        metrics, flags = {"signal_error": str(exc)}, ["INVALID_SIGNAL"]
    # Preserve the shared review policy, including its existing leading limit.
    return {"pass": math.isfinite(score) and score > .8 and not flags,
            "score": score, "transcript": result.get("text", ""), "flags": flags,
            "metrics": metrics, "audio_sha256": digest(audio),
            "model_id": DEFAULT_ASR_MODEL, "model_revision": DEFAULT_ASR_REVISION,
            "ignore_accents": True}


def fresh_row(original):
    row = copy.deepcopy(original)
    row.update(state="READY", reason="owner-frozen priority continuation")
    row["request"]["ignore_accents"] = True
    row["spoken_carrier"] = freeze_row(row, "warn")
    if row["spoken_carrier"] is None:
        raise ValueError("priority cue no longer satisfies the frozen short-cue policy: " + row["path"])
    carrier = row["spoken_carrier"]
    carrier["composite_text"] = carrier["prefix"].rstrip(".") + "...\n\n" + row["request"]["text"]
    carrier["composite_delivery_prompt"] = (
        "Clear, natural conversational delivery at an easy, unhurried pace. "
        "Say the introductory sentence, pause silently for two seconds, then say the final phrase exactly. Do not add words.")
    return row


def collect_history(history, selected):
    counts, done, sources = {}, {}, {}
    for count_file in history.rglob("carrier-attempt-counts.json"):
        for relative, value in read(count_file).items():
            if relative in selected:
                counts[relative] = max(counts.get(relative, 0), int(value))
    for plan_file in history.rglob("plan.json"):
        dbfile = plan_file.parent / "state.sqlite3"
        if not dbfile.exists():
            continue
        plan = read(plan_file)
        if Path(plan.get("root", "/")).resolve() != ROOT:
            continue
        with sqlite3.connect(dbfile) as db:
            states = dict(db.execute("SELECT path,state FROM cues"))
        for row in plan.get("rows", []):
            relative = row["path"]
            if relative not in selected or states.get(relative) != "DONE":
                continue
            candidate = plan_file.parent / "candidates" / relative
            if candidate.exists():
                done.setdefault(relative, set()).add(digest(candidate))
    for recfile in history.rglob("*.raw.wav.receipt.json"):
        marker = "/carrier-raw/"
        if marker not in str(recfile):
            continue
        relative = str(recfile).split(marker)[-1].removesuffix(".raw.wav.receipt.json")
        if relative not in selected:
            continue
        raw = Path(str(recfile).removesuffix(".receipt.json"))
        if not raw.exists():
            continue
        receipt = read(recfile)
        sha = digest(raw)
        if "output" not in receipt and receipt.get("status") == "completed" and receipt.get("id"):
            print("LEGACY provider manifest awaits faithful receipt recovery | " + str(recfile), flush=True)
            continue
        if sha != receipt.get("output", {}).get("sha256"):
            raise ValueError("saved provider take/receipt hash mismatch: " + str(raw))
        sources.setdefault(relative, {})[sha] = {"raw": str(raw), "receipt": str(recfile)}
    for relative, values in sources.items():
        counts[relative] = max(counts.get(relative, 0), len(values))
    return counts, done, {key: list(value.values()) for key, value in sources.items()}


def run(args):
    work = args.work_dir.resolve()
    history = args.history_root.resolve()
    if work.is_relative_to(ROOT) or work == history:
        raise ValueError("use a new external work directory, distinct from the history root")
    work.mkdir(parents=True, exist_ok=True)
    priority = read(args.priority_file)
    selected = {r["path"] for r in priority["records"]}
    original_plan = read(history / "run" / "plan.json")
    original = {r["path"]: r for r in original_plan["rows"] if r["path"] in selected}
    if len(original) != len(selected) or len(selected) != len(priority["records"]):
        raise ValueError("priority identities are missing or duplicated")
    # Never silently restart a partially executed orchestration. Existing pass
    # journals identify whether provider/installation inspection is required.
    if (work / "progress.json").exists():
        raise ValueError("existing run: inspect progress/pass journals before resuming; do not duplicate jobs")
    (work / "producer.pid").write_text(str(os.getpid()) + "\n", encoding="ascii")
    counts, prior_done, sources = collect_history(history, selected)
    registry = VoiceRegistry.load(ROOT)
    for profile in registry.profiles.values():
        registry.verify_anchor(profile)
    transcribe = CachedTranscriber(work)
    progress = {"status": "RUNNING", "scope": len(selected), "kept": {}, "installed": {},
                "blocked": {}, "unresolved": {}, "counts": counts,
                "priority_file": str(args.priority_file), "priority_sha256": digest(args.priority_file),
                "started_unix": time.time(), "model_id": DEFAULT_ASR_MODEL,
                "model_revision": DEFAULT_ASR_REVISION, "ignore_accents": True,
                "human_review": "PENDING"}
    def save():
        progress["updated_unix"] = time.time()
        write_json(work / "progress.json", progress)
    save()
    with InterprocessGenerationLock(voice_home() / "generation.lock"):
        with build_engine(generation_lock=NullGenerationLock(), character_provider="voxstage") as engine:
            remaining = {}
            for number, (relative, old) in enumerate(original.items(), 1):
                current = safe_target(ROOT, relative)
                sha = digest(current)
                row = fresh_row(old)
                row["original_sha256"] = sha
                row["original_receipt_sha256"] = digest(receipt_path(current))
                if relative in prior_done:
                    if sha not in prior_done[relative] and not (
                            sha == old["original_sha256"]
                            and row["original_receipt_sha256"] == old["original_receipt_sha256"]):
                        progress["blocked"][relative] = "current bytes differ from prior installed take; explicit reconciliation needed"
                        save(); continue
                    if sha in prior_done[relative]:
                        print(f"AUDIT {number}/{len(selected)} | {relative}", flush=True)
                        quality = final_quality(engine, current, row, transcribe, work)
                        write_json(work / "current-checks" / (relative + ".json"), quality)
                        if quality["pass"]:
                            progress["kept"][relative] = quality
                            save(); continue
                    else:
                        # The exact owner-selected pre-retake pair is back on
                        # disk, not unknown/custom bytes. The latest completion
                        # request still authorizes its original priority repair.
                        progress.setdefault("reconciled_original_restorations", []).append(relative)
                elif sha != old["original_sha256"]:
                    progress["blocked"][relative] = "source changed outside recorded priority transactions"
                    save(); continue
                remaining[relative] = row
            save()
            print(f"AUDIT DONE | kept={len(progress['kept'])} blocked={len(progress['blocked'])} remaining={len(remaining)}", flush=True)
            # Completed orphan/legacy receipts may have been reconciled while
            # the delivered-audio audit ran. Re-read history before synthesis.
            reconciled_counts, _, sources = collect_history(history, selected)
            for relative, count in reconciled_counts.items():
                counts[relative] = max(counts.get(relative, 0), count)
            # One immutable plan per recovery/fresh pass. Rejected attempts remain
            # in their original workdirs, and cumulative budgets carry forward.
            maximum_saved = max((len(sources.get(p, [])) for p in remaining), default=0)
            for pass_index in range(maximum_saved + (3 if args.fresh else 0)):
                recovery = pass_index < maximum_saved
                rows = []
                for relative, current_row in remaining.items():
                    if recovery and pass_index >= len(sources.get(relative, [])):
                        continue
                    if not recovery and counts.get(relative, 0) >= 3:
                        continue
                    row = copy.deepcopy(current_row)
                    if recovery:
                        source = sources[relative][pass_index]
                        source_receipt = read(Path(source["receipt"]))
                        req = source_receipt["request"]
                        if (any(req.get(k) != row["request"].get(k) for k in ("speaker", "locale", "kind"))
                                or not req["text"].strip().endswith(row["request"]["text"].strip())):
                            raise ValueError("saved source semantic identity differs: " + relative)
                        row["spoken_carrier"]["composite_text"] = req["text"]
                        row["spoken_carrier"]["composite_delivery_prompt"] = req["delivery_prompt"]
                    rows.append(row)
                if not rows:
                    continue
                pass_dir = work / (f"recovery-{pass_index + 1:02}" if recovery else f"fresh-{pass_index - maximum_saved + 1:02}")
                plan = {**original_plan, "rows": rows, "registry_manifest_sha256": digest(ROOT / CANONICAL_MANIFEST),
                        "priority_continuation": {"scope_sha256": digest(args.priority_file), "saved_recovery": recovery}}
                store = RunStore.create(pass_dir, plan)
                try:
                    write_json(pass_dir / "carrier-attempt-counts.json", counts)
                    if recovery:
                        for row in rows:
                            relative = row["path"]
                            source = sources[relative][pass_index]
                            raw = pass_dir / "carrier-raw" / (relative + ".raw.wav")
                            raw.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copyfile(source["raw"], raw)
                            shutil.copyfile(source["receipt"], receipt_path(raw))
                            print(f"RECOVER saved take | {relative}", flush=True)
                            try:
                                prepare_saved_candidate(engine, store, row, registry.get(row["request"]["speaker"]),
                                                        "required", transcriber=transcribe)
                            except CarrierExtractionFailure as exc:
                                store.set_state(relative, "PRESERVED", "saved take rejected; original retained: " + str(exc))
                                progress["unresolved"][relative] = str(exc)
                                save()
                    runner = CorpusRunner(store, engine, "required")
                    # Fresh generation uses the same exact ASR implementation;
                    # cache only changes duplicate saved-take observations.
                    result = runner.run(continue_after_carrier_rejection=True)
                    counts.update(read(pass_dir / "carrier-attempt-counts.json"))
                    for row in rows:
                        relative = row["path"]
                        state = store.state(relative)
                        if state == "DONE":
                            progress["installed"][relative] = {"work_dir": str(pass_dir), "sha256": digest(ROOT / relative)}
                            progress["unresolved"].pop(relative, None)
                            remaining.pop(relative)
                        elif state == "FAILED":
                            problem = next(p for p in store.problems() if p["path"] == relative)
                            progress["unresolved"][relative] = problem["detail"]
                            # Only known acoustic/ASR rejections may use another
                            # take. Infrastructure/provider/transaction failures stop.
                            if not (pass_dir / "carrier-evidence" / (relative + ".failure.json")).exists():
                                raise RuntimeError("uncertain/non-acoustic failure; inspect job before retry: " + str(problem))
                        elif state in {"NEEDS_RECOVERY", "GENERATING", "INSTALLING"}:
                            raise RuntimeError("uncertain transaction/provider job: " + relative)
                    progress["counts"] = counts
                    save()
                    print(f"PASS DONE | installed={len(progress['installed'])} kept={len(progress['kept'])} remaining={len(remaining)} result={result}", flush=True)
                finally:
                    store.close()
            for relative in remaining:
                progress["unresolved"].setdefault(relative, "no accepted saved take; fresh budget exhausted" if args.fresh else "fresh production not enabled")
            progress["status"] = "COMPLETE" if not remaining and not progress["blocked"] else "FINISHED_WITH_UNRESOLVED"
            save()
    print(json.dumps({k: len(progress[k]) for k in ("kept", "installed", "blocked", "unresolved")}), flush=True)
    return 0 if progress["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--priority-file", type=Path, required=True)
    parser.add_argument("--history-root", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--fresh", action="store_true", help="after saved recovery, spend remaining attempts up to three total")
    args = parser.parse_args()
    try:
        raise SystemExit(run(args))
    except Exception as exc:
        work = args.work_dir.resolve()
        if (work / "progress.json").exists():
            progress = read(work / "progress.json")
            progress.update(status="STOPPED_ERROR", error=str(exc), updated_unix=time.time())
            write_json(work / "progress.json", progress)
        raise
