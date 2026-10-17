#!/usr/bin/env python3
"""Integrate owner-approved audio assets and receipts into canonical repository paths.

Copies staged review audio candidates (.wav, .ogg) and their .receipt.json records
into their canonical locations in activities/, assets/audio/, and activity_incubator/.
Updates receipt human_review status to APPROVED and records owner acceptance.

Committed recordings are owner-approved and final: this tool NEVER overwrites an
existing destination file (audio or receipt). A collision is reported and skipped,
and the run exits non-zero so the operator notices.

Layouts:

* ``app`` (default, historical): ``<review>/<app>/<locale>/<subpath>``;
* ``mirror``: ``<review>/<repository-relative path>`` — the review tree mirrors the
  canonical destination exactly (shared character library, vocabulary/number
  banks, first-boot lines, Activity packages).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW_DIR = PROJECT_ROOT / "tmp" / "greia-all-app-voices-20261014-050339" / "review"
DEFAULT_LEDGER = PROJECT_ROOT / "tmp" / "greia-all-app-voices-20261014-050339" / "inventory" / "RECORDING_LEDGER.csv"
DEFAULT_PROGRESS = PROJECT_ROOT / "tmp" / "greia-all-app-voices-20261014-050339" / "inventory" / "app-progress.csv"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_destination(app: str, loc: str, subpath: Path) -> list[Path]:
    destinations: list[Path] = []
    if app == "launcher-labels":
        destinations.append(PROJECT_ROOT / "assets" / "audio" / "system" / "launcher-labels" / loc / subpath)
    elif app == "tempo_di_greia":
        destinations.append(PROJECT_ROOT / "activity_incubator" / "tempo_di_greia" / "locales" / loc / "audio" / subpath)
    elif app == "sottomarino_giramondo":
        if subpath.name == "activity-title.wav":
            destinations.append(PROJECT_ROOT / "activities" / "sottomarino_giramondo" / "audio" / loc / "sub_title.wav")
            destinations.append(PROJECT_ROOT / "activities" / "sottomarino_giramondo" / "locales" / loc / "audio" / "activity-title.wav")
        else:
            destinations.append(PROJECT_ROOT / "activities" / "sottomarino_giramondo" / "audio" / loc / subpath)
    else:
        if subpath.name == "activity-title.wav":
            destinations.append(PROJECT_ROOT / "activities" / app / "locales" / loc / "audio" / "activity-title.wav")
        else:
            destinations.append(PROJECT_ROOT / "activities" / app / "assets" / "audio" / loc / subpath)
    return destinations


DEFAULT_ACCEPTANCE_NOTE = "Approved by repository owner on 2026-10-15."


def integrate(
    review_dir: Path,
    ledger_path: Path | None = None,
    progress_path: Path | None = None,
    *,
    layout: str = "app",
    acceptance_note: str = DEFAULT_ACCEPTANCE_NOTE,
    dry_run: bool = False,
) -> int:
    audio_files = sorted(p for p in review_dir.glob("**/*") if p.is_file() and p.suffix in (".wav", ".ogg"))
    print(f"Found {len(audio_files)} audio candidates in {review_dir}")

    installed_count = 0
    receipts_count = 0
    collisions: list[Path] = []

    for af in audio_files:
        rel = af.relative_to(review_dir)
        receipt_source = af.with_name(af.name + ".receipt.json")

        receipt_data: dict[str, object] | None = None
        if receipt_source.exists():
            try:
                receipt_data = json.loads(receipt_source.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"Warning: failed to read receipt {receipt_source}: {e}", file=sys.stderr)

        if layout == "mirror":
            targets = [PROJECT_ROOT / rel]
        else:
            targets = compute_destination(rel.parts[0], rel.parts[1], Path(*rel.parts[2:]))
        for dest in targets:
            dest_receipt_path = dest.with_name(dest.name + ".receipt.json")
            if dest.exists() or dest_receipt_path.exists():
                collisions.append(dest)
                continue
            if dry_run:
                installed_count += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(af, dest)
            installed_count += 1

            if receipt_data is not None:
                dest_receipt = dest.with_name(dest.name + ".receipt.json")
                updated_receipt = dict(receipt_data)
                updated_receipt["human_review"] = "APPROVED"
                updated_receipt["acceptance_note"] = acceptance_note
                dest_sha = _sha256(dest)
                updated_receipt["output"] = {
                    "path": str(dest.relative_to(PROJECT_ROOT)),
                    "bytes": dest.stat().st_size,
                    "sha256": dest_sha,
                }
                dest_receipt.write_text(
                    json.dumps(updated_receipt, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                receipts_count += 1

    print(f"Successfully integrated {installed_count} audio files and {receipts_count} receipts.")
    for dest in collisions:
        print(f"SKIPPED existing destination (never overwritten): {dest}", file=sys.stderr)

    # Update ledger if available
    if not dry_run and ledger_path and ledger_path.exists():
        rows: list[dict[str, str]] = []
        with open(ledger_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            for r in reader:
                if r.get("state") == "REVIEW_PENDING":
                    r["state"] = "ACCEPTED"
                    r["human_review"] = "APPROVED"
                    r["notes"] = "Owner-approved on 2026-10-15; integrated into main asset paths."
                rows.append(r)
        with open(ledger_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Updated recording ledger: {ledger_path}")

    # Update progress if available
    if not dry_run and progress_path and progress_path.exists():
        rows = []
        with open(progress_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            for r in reader:
                if r.get("status") == "REVIEW_PENDING":
                    r["status"] = "ACCEPTED"
                    r["notes"] = "Audio recorded, reviewed and approved by repository owner on 2026-10-15."
                rows.append(r)
        with open(progress_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Updated app progress: {progress_path}")

    return 3 if collisions else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-dir", type=Path, default=DEFAULT_REVIEW_DIR)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--progress", type=Path, default=DEFAULT_PROGRESS)
    parser.add_argument("--layout", choices=("app", "mirror"), default="app")
    parser.add_argument("--acceptance-note", default=DEFAULT_ACCEPTANCE_NOTE)
    parser.add_argument("--dry-run", action="store_true", help="report what would be copied")
    args = parser.parse_args()
    return integrate(
        args.review_dir,
        args.ledger,
        args.progress,
        layout=args.layout,
        acceptance_note=args.acceptance_note,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
