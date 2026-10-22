"""Pinned selection of already completed provider sources from historical runs."""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
from .inventory import digest, receipt_path


def load_selection(path: Path, source: Path, priority: Path) -> dict:
    """Validate the index against immutable source/scope and current remaining IDs."""
    data = json.loads(path.read_text())
    if (data.get("schema_version") != 1
            or data.get("source_plan_sha256") != digest(source / "plan.json")
            or data.get("priority_sha256") != digest(priority)):
        raise ValueError("source selection plan/priority identity differs")
    remaining_file = Path(data["remaining_file"])
    if digest(remaining_file) != data["remaining_sha256"]:
        raise ValueError("source selection remaining list changed")
    remaining = set(json.loads(remaining_file.read_text())["remaining"])
    entries = data["sources"]
    if not entries or len({e["path"] for e in entries}) != len(entries):
        raise ValueError("empty or duplicated source selection")
    if any(e["path"] not in remaining for e in entries):
        raise ValueError("source selection contains non-remaining target")
    return {e["path"]: e for e in entries}


def validate_selected_source(entry: dict, source: Path, row: dict) -> None:
    """Verify pinned PCM/receipt plus exact completed VoxStage job provenance."""
    relative = row["path"]
    raw = source / "carrier-raw" / (relative + ".raw.wav")
    receipt = receipt_path(raw)
    if digest(raw) != entry["sha256"] or digest(receipt) != entry["receipt_sha256"]:
        raise ValueError("selected raw source or receipt changed")
    rec = json.loads(receipt.read_text())
    params = rec["generation_parameters"]
    manifest = Path(entry["job_manifest"])
    if digest(manifest) != entry["job_manifest_sha256"]:
        raise ValueError("selected provider manifest changed")
    job = json.loads(manifest.read_text())
    if (job.get("id") != params.get("job_id") or job.get("status") != "completed"
            or not params.get("idempotency_key")
            or job.get("idempotency_key") != params["idempotency_key"]):
        raise ValueError("selected provider job/key is not the exact completed submission")
    recordings = job.get("plan", {}).get("recordings", [])
    results = job.get("results", [])
    if len(recordings) != 1 or len(results) != 1:
        raise ValueError("selected provider job is not one unsplit recording")
    spec = recordings[0]
    if (spec.get("text") != rec["request"]["text"]
            or spec.get("direction") != params.get("effective_delivery")
            or spec.get("voice") != params.get("voxstage_voice_id")
            or spec.get("reference_sha256") != rec.get("reference_sha256")
            or spec.get("mode") != "reference"):
        raise ValueError("selected provider text/direction/master/output differs")

    mixes = job.get("mixes", [])
    if len(mixes) != 1:
        raise ValueError("selected provider job has no unique mixed output")
    mix = mixes[0]
    media = (manifest.parent / mix["file"]).resolve()
    if not media.is_relative_to(manifest.parent.resolve()) or digest(media) != mix.get("sha256"):
        raise ValueError("selected provider output hash differs")
    # VoiceEngine packages the provider's 48 kHz output before retaining its raw
    # carrier. Compare that exact existing packaging transform, not file hashes
    # across different sample rates. Never synthesize to reconstruct provenance.
    if digest(media) != entry["sha256"]:
        from greia_voice_core.audio import AudioPipeline
        with tempfile.TemporaryDirectory(prefix="greia-source-provenance-") as temp:
            packaged = Path(temp) / "provider.wav"
            AudioPipeline().package(media, packaged)
            if digest(packaged) != entry["sha256"]:
                raise ValueError("selected raw source is not the packaged provider output")
