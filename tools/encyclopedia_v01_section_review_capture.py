"""Capture the Encyclopedia E3 Home + six-section Simulator review set.

This is a narrow visual-review driver. It deliberately reuses the proven
``encyclopedia_v01_golden_master_capture`` Shell/workspace/input machinery
instead of creating another Simulator authority. Each job launches the built-in
``org.greia.enciclopedia`` through the real Greia Shell/profile/catalogue path,
navigates to one section with semantic keyboard input, captures one frame, and
exercises the protected Greia Home return before shutdown.

It does not walk factual entries and it does not replace the 43-page mechanical
traversal. E4 remains outside this tool.
"""
from __future__ import annotations

import argparse
from pathlib import Path
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
            golden._log(f"E3 section-review job {tag} returned {code}")
            return code

    golden._log("E3 Home + section review capture PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
