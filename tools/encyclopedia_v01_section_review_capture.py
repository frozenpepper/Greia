"""Capture the Encyclopedia E3 Home + six-section Simulator review set.

This is a narrow visual-review driver. It deliberately reuses the proven
``encyclopedia_v01_golden_master_capture`` Shell/workspace/input machinery
instead of creating another Simulator authority. Each job launches the built-in
``org.greia.enciclopedia`` through the real Greia Shell/profile/catalogue path,
navigates to one section with semantic keyboard input, captures one frame, and
exercises the protected Greia Home return before shutdown.

The driver binds evidence to one clean tracked Git tree. It requires the exact
complete eleven-PNG Activity art inventory, records the source SHA and SHA-256
digest of every Activity runtime PNG before capture, then proves that neither
the tracked checkout nor HEAD nor the runtime-art inventory changed while the
sessions ran.

It does not walk factual entries and it does not replace the 43-page mechanical
traversal. E4 remains outside this tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import encyclopedia_v01_golden_master_capture as golden  # noqa: E402


SECTION_ORDER = (
    "animals",
    "space",
    "earth",
    "body",
    "machines",
    "history",
)
SHOT_NUMBER = {
    "home": 1,
    "animals": 2,
    "space": 3,
    "earth": 4,
    "body": 5,
    "machines": 6,
    "history": 7,
}
EXPECTED_RUNTIME_ART = {
    "home_discovery_book.png",
    "animals_field_table.png",
    "lion_savanna.png",
    "saturn_observatory.png",
    "gears_workbench.png",
    "pyramids_diorama.png",
    "space_gallery_observatory.png",
    "earth_gallery_landscape.png",
    "body_gallery_discovery_room.png",
    "machines_gallery_workbench.png",
    "history_gallery_time_trail.png",
}


def _jobs(*, viewport: str, interface_size: str) -> list[dict[str, object]]:
    jobs: list[dict[str, object]] = [
        {
            "tag": "home",
            "navigation_keys": (),
            "capture": golden.Capture("home", "01-home.png"),
            "viewport": viewport,
            "interface_size": interface_size,
        }
    ]
    for section_id in SECTION_ORDER:
        number = SHOT_NUMBER[section_id]
        jobs.append(
            {
                "tag": section_id,
                "navigation_keys": golden._route_home_to_section(section_id),
                "capture": golden.Capture(
                    section_id,
                    f"{number:02d}-{section_id}.png",
                ),
                "viewport": viewport,
                "interface_size": interface_size,
            }
        )
    return jobs


def _git_output(*args: str) -> str:
    completed = subprocess.run(
        ("git", *args),
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _tracked_status() -> str:
    """Return tracked changes only; project-local ignored evidence is allowed."""

    return _git_output("status", "--short", "--untracked-files=no")


def _runtime_art_sha256() -> dict[str, str]:
    runtime = golden.ACTIVITY_DIR / "assets" / "runtime"
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(runtime.glob("*.png"))
        if path.is_file()
    }


def _write_manifest(
    evidence_root: Path,
    *,
    source_sha: str,
    locale: str,
    viewport: str,
    interface_size: str,
    selected_jobs: list[str],
    completed_jobs: list[str],
    runtime_art_sha256: dict[str, str],
    status: str,
    failure: str | None = None,
) -> None:
    payload = {
        "schema_version": 1,
        "activity_id": golden.ACTIVITY_ID,
        "source_sha": source_sha,
        "locale": locale,
        "viewport": viewport,
        "interface_size": interface_size,
        "selected_jobs": selected_jobs,
        "completed_jobs": completed_jobs,
        "runtime_art_sha256": runtime_art_sha256,
        "status": status,
        "failure": failure,
    }
    (evidence_root / "source-sha.txt").write_text(source_sha + "\n", encoding="utf-8")
    (evidence_root / "capture-manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locale", default="it")
    parser.add_argument("--viewport", default="1024x600")
    parser.add_argument(
        "--interface-size",
        default="normal",
        choices=("compact", "normal", "large"),
    )
    parser.add_argument(
        "--jobs",
        default="all",
        help=(
            "Comma-separated tags. Default 'all' runs home plus all six "
            "sections. Valid tags: home, animals, space, earth, body, "
            "machines, history."
        ),
    )
    parser.add_argument("--evidence-root", required=True)
    args = parser.parse_args(argv)

    evidence_root = Path(args.evidence_root).expanduser()
    evidence_root.mkdir(parents=True, exist_ok=True)

    try:
        source_sha = _git_output("rev-parse", "HEAD")
        dirty = _tracked_status()
    except (OSError, subprocess.CalledProcessError) as exc:
        golden._log(f"cannot bind E3 capture to Git source: {exc}")
        return 2
    if dirty:
        golden._log("tracked checkout is dirty; commit or restore source before capture")
        golden._log(dirty)
        return 2

    runtime_hashes = _runtime_art_sha256()
    present_art = set(runtime_hashes)
    if present_art != EXPECTED_RUNTIME_ART:
        missing = sorted(EXPECTED_RUNTIME_ART - present_art)
        extra = sorted(present_art - EXPECTED_RUNTIME_ART)
        golden._log("E3 capture requires the exact complete 11-PNG runtime-art pack")
        if missing:
            golden._log(f"missing runtime art: {missing}")
        if extra:
            golden._log(f"unexpected runtime art: {extra}")
        return 3

    requested = {tag.strip() for tag in args.jobs.split(",") if tag.strip()}
    valid = {"home", *SECTION_ORDER}
    if "all" in requested:
        requested = valid
    unknown = requested - valid
    if unknown:
        golden._log(f"unknown E3 section-review jobs: {sorted(unknown)}")
        return 1

    selected = [
        job
        for job in _jobs(
            viewport=args.viewport,
            interface_size=args.interface_size,
        )
        if job["tag"] in requested
    ]
    if not selected:
        golden._log(f"no E3 section-review jobs match {args.jobs!r}")
        return 1

    selected_tags = [str(job["tag"]) for job in selected]
    completed_tags: list[str] = []
    _write_manifest(
        evidence_root,
        source_sha=source_sha,
        locale=args.locale,
        viewport=args.viewport,
        interface_size=args.interface_size,
        selected_jobs=selected_tags,
        completed_jobs=completed_tags,
        runtime_art_sha256=runtime_hashes,
        status="RUNNING",
    )

    for job in selected:
        tag = str(job["tag"])
        # The golden-master driver intentionally keeps Simulator workspace
        # state outside the repository tree; preserve that boundary here.
        workspace = Path(f"~/.greia-simulator-encyclopedia-e3-{tag}").expanduser()
        code = golden._run_session(
            workspace_dir=workspace,
            evidence_dir=evidence_root / tag,
            locale=args.locale,
            viewport=str(job["viewport"]),
            interface_size=str(job["interface_size"]),
            navigation_keys=tuple(job["navigation_keys"]),  # type: ignore[arg-type]
            captures=(job["capture"],),  # type: ignore[arg-type]
        )
        if code != 0:
            failure = f"E3 section-review job {tag} returned {code}"
            _write_manifest(
                evidence_root,
                source_sha=source_sha,
                locale=args.locale,
                viewport=args.viewport,
                interface_size=args.interface_size,
                selected_jobs=selected_tags,
                completed_jobs=completed_tags,
                runtime_art_sha256=runtime_hashes,
                status="FAIL",
                failure=failure,
            )
            golden._log(failure)
            return code
        completed_tags.append(tag)

    try:
        final_sha = _git_output("rev-parse", "HEAD")
        final_dirty = _tracked_status()
    except (OSError, subprocess.CalledProcessError) as exc:
        failure = f"cannot re-check Git source after E3 capture: {exc}"
        _write_manifest(
            evidence_root,
            source_sha=source_sha,
            locale=args.locale,
            viewport=args.viewport,
            interface_size=args.interface_size,
            selected_jobs=selected_tags,
            completed_jobs=completed_tags,
            runtime_art_sha256=runtime_hashes,
            status="FAIL",
            failure=failure,
        )
        golden._log(failure)
        return 10

    if final_sha != source_sha or final_dirty:
        failure = "tracked source changed while E3 Simulator evidence was being captured"
        _write_manifest(
            evidence_root,
            source_sha=source_sha,
            locale=args.locale,
            viewport=args.viewport,
            interface_size=args.interface_size,
            selected_jobs=selected_tags,
            completed_jobs=completed_tags,
            runtime_art_sha256=runtime_hashes,
            status="FAIL",
            failure=failure,
        )
        golden._log(failure)
        if final_sha != source_sha:
            golden._log(f"start={source_sha} end={final_sha}")
        if final_dirty:
            golden._log(final_dirty)
        return 10

    final_runtime_hashes = _runtime_art_sha256()
    if final_runtime_hashes != runtime_hashes:
        failure = "runtime PNG pack changed while E3 Simulator evidence was being captured"
        _write_manifest(
            evidence_root,
            source_sha=source_sha,
            locale=args.locale,
            viewport=args.viewport,
            interface_size=args.interface_size,
            selected_jobs=selected_tags,
            completed_jobs=completed_tags,
            runtime_art_sha256=runtime_hashes,
            status="FAIL",
            failure=failure,
        )
        golden._log(failure)
        return 10

    _write_manifest(
        evidence_root,
        source_sha=source_sha,
        locale=args.locale,
        viewport=args.viewport,
        interface_size=args.interface_size,
        selected_jobs=selected_tags,
        completed_jobs=completed_tags,
        runtime_art_sha256=runtime_hashes,
        status="PASS",
    )
    golden._log(f"E3 Home + section review capture PASS at {source_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
