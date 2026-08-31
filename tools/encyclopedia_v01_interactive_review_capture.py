#!/usr/bin/env python3
"""Bounded interactive Encyclopedia review through the real Greia child Shell.

This drives the showcase interactions that determine whether the quality /
interactivity pass is actually child-usable. Each case uses a fresh real
Shell -> Encyclopedia session to avoid hidden state coupling. Evidence is
exact-SHA bound and requires human/owner visual review.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = Path(__file__).resolve().parent
for candidate in (str(REPO_ROOT), str(REPO_ROOT / "src"), str(TOOLS_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import headless_greia_simulator as headless  # noqa: E402
from encyclopedia_v01_headless_traversal import (  # noqa: E402
    HeadlessEncyclopediaTraversal,
    PAGE_CHANGE_FRAME_ADVANCE,
    TraversalFailure,
    _entry_route,
    _section_home_route,
)


@dataclass(frozen=True, slots=True)
class FrameEvidence:
    case: str
    state: str
    png: str


@dataclass(frozen=True, slots=True)
class CaseEvidence:
    case: str
    page_id: str
    frames: tuple[FrameEvidence, ...]
    status: str


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()


def _tracked_tree_clean() -> bool:
    output = subprocess.check_output(
        ["git", "status", "--short", "--untracked-files=no"], cwd=REPO_ROOT, text=True
    )
    return not output.strip()


def _click_and_wait(
    runner: HeadlessEncyclopediaTraversal,
    x: int,
    y: int,
    *,
    stage: str,
    settle: float = 0.12,
) -> None:
    before = int(runner._current_activity_state().get("frame_count", 0))
    if not headless._bridge_click(x, y):
        raise TraversalFailure(stage, f"remote click ({x}, {y}) was rejected")
    updated = headless._wait_for_state(
        lambda state: state.get("mode") == "activity"
        and int(state.get("frame_count", 0)) > before,
        timeout=4.0,
        child=runner._require_child(),
    )
    if updated is None:
        raise TraversalFailure(stage, f"no fresh frame after click ({x}, {y})")
    if settle:
        time.sleep(settle)


def _go_to_section(runner: HeadlessEncyclopediaTraversal, section_id: str) -> None:
    runner._keys(_section_home_route(section_id), stage=f"home -> {section_id} focus")
    runner._key(
        "RETURN",
        stage=f"home -> {section_id} activate",
        min_frame_advance=PAGE_CHANGE_FRAME_ADVANCE,
    )


def _go_to_entry(
    runner: HeadlessEncyclopediaTraversal,
    section_id: str,
    page_id: str,
) -> None:
    _go_to_section(runner, section_id)
    runner._keys(_entry_route(section_id, page_id), stage=f"{section_id} -> {page_id} focus")
    runner._key(
        "RETURN",
        stage=f"{section_id} -> {page_id} activate",
        min_frame_advance=PAGE_CHANGE_FRAME_ADVANCE,
    )


def _back_entry_to_home(runner: HeadlessEncyclopediaTraversal, section_id: str) -> None:
    runner._key(
        "ESCAPE",
        stage=f"entry -> {section_id}",
        min_frame_advance=PAGE_CHANGE_FRAME_ADVANCE,
    )
    runner._key(
        "ESCAPE",
        stage=f"{section_id} -> home",
        min_frame_advance=PAGE_CHANGE_FRAME_ADVANCE,
    )


def _capture(
    runner: HeadlessEncyclopediaTraversal,
    case: str,
    state: str,
) -> FrameEvidence:
    path = runner._capture(f"review/{state}.png")
    return FrameEvidence(case, state, path.relative_to(runner.evidence_dir).as_posix())


def _case_home(runner: HeadlessEncyclopediaTraversal):
    frames = [_capture(runner, "home", "01-animals-selected")]
    runner._key("RIGHT", stage="home select Space")
    frames.append(_capture(runner, "home", "02-space-selected"))
    return "home", tuple(frames)


def _case_space(runner: HeadlessEncyclopediaTraversal):
    _go_to_section(runner, "space")
    frames = [_capture(runner, "space", "01-earth-selected")]
    runner._key("RIGHT", stage="space Earth -> Moon")
    frames.append(_capture(runner, "space", "02-moon-selected"))
    _click_and_wait(runner, 315, 540, stage="space pause")
    frames.append(_capture(runner, "space", "03-paused"))
    _click_and_wait(runner, 120, 540, stage="space slow speed", settle=0.25)
    runner._key("LEFT", stage="space Moon -> Earth")
    frames.append(_capture(runner, "space", "04-earth-selected-slow"))
    runner._key(
        "ESCAPE",
        stage="space -> home",
        min_frame_advance=PAGE_CHANGE_FRAME_ADVANCE,
    )
    return "space", tuple(frames)


def _case_earth_planet(runner: HeadlessEncyclopediaTraversal):
    _go_to_entry(runner, "space", "space.earth")
    frames = [_capture(runner, "space-earth", "01-earth-hero")]
    runner._key("RIGHT", stage="Earth select water")
    frames.append(_capture(runner, "space-earth", "02-water-selected"))
    runner._key("RETURN", stage="Earth activate water")
    time.sleep(0.18)
    frames.append(_capture(runner, "space-earth", "03-water-active"))
    _back_entry_to_home(runner, "space")
    return "space.earth", tuple(frames)


def _case_volcano(runner: HeadlessEncyclopediaTraversal):
    _go_to_entry(runner, "earth", "earth.volcano")
    frames = [_capture(runner, "volcano", "01-idle")]
    _click_and_wait(runner, 512, 485, stage="volcano erupt", settle=0.35)
    frames.append(_capture(runner, "volcano", "02-erupting"))
    _click_and_wait(runner, 245, 485, stage="volcano strength high")
    _click_and_wait(runner, 512, 485, stage="volcano erupt high", settle=0.35)
    frames.append(_capture(runner, "volcano", "03-high-eruption"))
    _click_and_wait(runner, 700, 485, stage="volcano smoke toggle")
    frames.append(_capture(runner, "volcano", "04-smoke-toggle"))
    _back_entry_to_home(runner, "earth")
    return "earth.volcano", tuple(frames)


def _case_pyramids(runner: HeadlessEncyclopediaTraversal):
    _go_to_entry(runner, "history", "history.pyramids")
    frames = [_capture(runner, "pyramids", "01-initial")]
    for index in range(2):
        runner._key("RETURN", stage=f"pyramids place block {index + 1}")
        time.sleep(0.72)
    frames.append(_capture(runner, "pyramids", "02-partial-build"))
    for index in range(2, 4):
        runner._key("RETURN", stage=f"pyramids place block {index + 1}")
        time.sleep(0.72)
    frames.append(_capture(runner, "pyramids", "03-completed-build"))
    _back_entry_to_home(runner, "history")
    return "history.pyramids", tuple(frames)


def _case_gears(runner: HeadlessEncyclopediaTraversal):
    _go_to_entry(runner, "machines", "machines.gears")
    frames = [_capture(runner, "gears", "01-running")]
    _click_and_wait(runner, 380, 485, stage="gears pause")
    frames.append(_capture(runner, "gears", "02-paused"))
    _click_and_wait(runner, 700, 485, stage="gears reverse")
    _click_and_wait(runner, 380, 485, stage="gears resume")
    _click_and_wait(runner, 245, 485, stage="gears high speed", settle=0.35)
    frames.append(_capture(runner, "gears", "03-reversed-fast"))
    _back_entry_to_home(runner, "machines")
    return "machines.gears", tuple(frames)


def _case_heart(runner: HeadlessEncyclopediaTraversal):
    _go_to_entry(runner, "body", "body.heart")
    frames = [_capture(runner, "heart", "01-idle")]
    _click_and_wait(runner, 512, 485, stage="heart beat", settle=0.22)
    frames.append(_capture(runner, "heart", "02-beating"))
    _back_entry_to_home(runner, "body")
    return "body.heart", tuple(frames)


def _case_lungs(runner: HeadlessEncyclopediaTraversal):
    _go_to_entry(runner, "body", "body.lungs")
    frames = [_capture(runner, "lungs", "01-idle")]
    _click_and_wait(runner, 512, 485, stage="lungs breathe", settle=0.22)
    frames.append(_capture(runner, "lungs", "02-breathe"))
    _back_entry_to_home(runner, "body")
    return "body.lungs", tuple(frames)


def _case_lion(runner: HeadlessEncyclopediaTraversal):
    _go_to_entry(runner, "animals", "animals.lion")
    frames = [_capture(runner, "lion", "01-idle")]
    _click_and_wait(runner, 512, 485, stage="lion roar", settle=0.22)
    frames.append(_capture(runner, "lion", "02-reaction"))
    _back_entry_to_home(runner, "animals")
    return "animals.lion", tuple(frames)


CASES = (
    ("home", _case_home),
    ("space", _case_space),
    ("space-earth", _case_earth_planet),
    ("volcano", _case_volcano),
    ("pyramids", _case_pyramids),
    ("gears", _case_gears),
    ("heart", _case_heart),
    ("lungs", _case_lungs),
    ("lion", _case_lion),
)


def _build_contact_sheet(root: Path, frames: list[FrameEvidence]) -> Path:
    thumb_w, thumb_h, label_h, gap, columns = 512, 300, 24, 12, 3
    rows = (len(frames) + columns - 1) // columns
    sheet = Image.new(
        "RGB",
        (
            columns * thumb_w + (columns + 1) * gap,
            rows * (thumb_h + label_h) + (rows + 1) * gap,
        ),
        "white",
    )
    draw = ImageDraw.Draw(sheet)
    for index, frame in enumerate(frames):
        row, col = divmod(index, columns)
        x = gap + col * (thumb_w + gap)
        y = gap + row * (thumb_h + label_h + gap)
        with Image.open(root / frame.case / frame.png) as raw:
            image = raw.convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        sheet.paste(image, (x, y))
        draw.text((x + 4, y + thumb_h + 4), f"{frame.case}: {frame.state}", fill="black")
    output = root / "interactive-contact-sheet.png"
    sheet.save(output)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture bounded interactive Encyclopedia owner-review evidence"
    )
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--locale", default="it")
    parser.add_argument("--viewport", default="1024x600")
    args = parser.parse_args(argv)

    if not _tracked_tree_clean():
        print("ERROR: tracked checkout is dirty; evidence must be exact-SHA bound", file=sys.stderr)
        return 2

    source_sha = _git_sha()
    evidence_root = args.evidence_root.resolve()
    if evidence_root.exists():
        shutil.rmtree(evidence_root)
    evidence_root.mkdir(parents=True, exist_ok=True)

    workspace_root = (
        args.workspace_root.resolve()
        if args.workspace_root
        else Path(tempfile.gettempdir()) / "greia-encyclopedia-interactive-review"
    )
    if workspace_root.exists():
        shutil.rmtree(workspace_root)
    workspace_root.mkdir(parents=True, exist_ok=True)

    results: list[CaseEvidence] = []
    all_frames: list[FrameEvidence] = []
    first_failure: dict[str, str] | None = None

    for case_name, case_func in CASES:
        runner = HeadlessEncyclopediaTraversal(
            workspace_dir=workspace_root / case_name,
            evidence_dir=evidence_root / case_name,
            locale=args.locale,
            viewport=args.viewport,
        )
        try:
            runner.start()
            page_id, frames = case_func(runner)
            all_frames.extend(frames)
            runner.return_to_shell()
            results.append(CaseEvidence(case_name, page_id, frames, "PASS"))
        except TraversalFailure as exc:
            runner.record_failure(exc)
            first_failure = {"case": case_name, "stage": exc.stage, "message": str(exc)}
            results.append(CaseEvidence(case_name, case_name, (), "FAIL"))
            break
        except Exception as exc:  # noqa: BLE001
            first_failure = {"case": case_name, "stage": "unexpected", "message": repr(exc)}
            results.append(CaseEvidence(case_name, case_name, (), "FAIL"))
            break
        finally:
            runner.close()

    ending_sha = _git_sha()
    clean_after = _tracked_tree_clean()
    contact_sheet = _build_contact_sheet(evidence_root, all_frames) if all_frames else None
    status = (
        "PASS"
        if first_failure is None
        and len(results) == len(CASES)
        and all(result.status == "PASS" for result in results)
        and source_sha == ending_sha
        and clean_after
        else "FAIL"
    )
    manifest = {
        "status": status,
        "source_sha": source_sha,
        "ending_sha": ending_sha,
        "tracked_tree_clean_after": clean_after,
        "locale": args.locale,
        "viewport": args.viewport,
        "cases_expected": [name for name, _ in CASES],
        "cases_completed": [result.case for result in results if result.status == "PASS"],
        "frames": [asdict(frame) for frame in all_frames],
        "contact_sheet": contact_sheet.name if contact_sheet else None,
        "owner_visual_review_required": True,
        "audio_acceptance_separate": True,
        "first_failure": first_failure,
    }
    (evidence_root / "interactive-review-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (evidence_root / "source-sha.txt").write_text(source_sha + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
