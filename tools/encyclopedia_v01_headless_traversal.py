"""Mechanical Greia Encyclopedia v0.1 traversal through the real child Shell.

This acceptance helper is intentionally narrower than a visual/UX review. It:

* launches the built-in Encyclopedia through the real Greia child Shell;
* visits all six section pages and all 36 factual entries using only semantic
  keyboard input exposed by the Activity's public navigation profile;
* sends one bounded primary semantic interaction on every entry;
* captures before/after PNG evidence for later human/vision review;
* returns through the Encyclopedia's own semantic Back command;
* finally uses Greia's protected Home chrome to return to the Shell.

It never imports or instantiates Encyclopedia page classes, never reaches into
page state, never uses hidden test-only runtime hooks, and never claims that an
interaction is visually/educationally correct merely because a frame changed.
The resulting screenshots are the evidence input for the separate signature-
interaction and pre-reader visual review.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Iterable

from PIL import Image, ImageChops


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = Path(__file__).resolve().parent
for candidate in (str(REPO_ROOT), str(REPO_ROOT / "src"), str(TOOLS_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import headless_greia_simulator as headless  # noqa: E402
from encyclopedia.pages.catalogue import PLANNED_PAGES  # noqa: E402


ACTIVITY_ID = "org.greia.enciclopedia"
ACTIVITY_DIR = REPO_ROOT / "activities" / "enciclopedia_greia"
SECTION_ORDER = ("animals", "space", "earth", "body", "machines", "history")

# Child-visible source order inside each section page. These are acceptance
# navigation contracts, not runtime imports. Their exact IDs are already locked
# by tests/test_activity_enciclopedia.py against the implemented section source.
SECTION_ENTRY_ORDER: dict[str, tuple[str, ...]] = {
    "animals": (
        "animals.lion",
        "animals.elephant",
        "animals.octopus",
        "animals.bee",
        "animals.penguin",
        "animals.frog",
    ),
    "space": (
        "space.sun",
        "space.mercury",
        "space.venus",
        "space.earth",
        "space.moon",
        "space.mars",
        "space.jupiter",
        "space.saturn",
        "space.uranus",
        "space.neptune",
    ),
    "earth": (
        "earth.rain",
        "earth.tree",
        "earth.rainbow",
        "earth.volcano",
        "earth.ocean",
    ),
    "body": (
        "body.senses",
        "body.teeth",
        "body.lungs",
        "body.heart",
        "body.bones",
    ),
    "machines": (
        "machines.gears",
        "machines.magnet",
        "machines.bicycle",
        "machines.airplane",
        "machines.bridge",
    ),
    "history": (
        "history.dinosaurs",
        "history.fossils",
        "history.mammoth",
        "history.cave_paintings",
        "history.pyramids",
    ),
}

# Every entry page is required to offer a meaningful ACTIVATE action from its
# initial focus. The visual review decides whether that action actually expresses
# the planned signature interaction; this mechanical gate only delivers it.
PRIMARY_INTERACTION_KEYS = ("RETURN",)


class TraversalFailure(RuntimeError):
    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage


@dataclass(frozen=True, slots=True)
class EntryPlan:
    page_id: str
    section_id: str
    home_keys: tuple[str, ...]
    entry_keys: tuple[str, ...]
    interaction_keys: tuple[str, ...] = PRIMARY_INTERACTION_KEYS


@dataclass(frozen=True, slots=True)
class EntryEvidence:
    page_id: str
    section_id: str
    before_png: str
    after_png: str
    interaction_keys: tuple[str, ...]
    changed_pixel_fraction: float


def _grid_route(index: int, *, columns: int) -> tuple[str, ...]:
    if index < 0 or columns < 1:
        raise ValueError("grid route requires non-negative index and positive columns")
    row, column = divmod(index, columns)
    return ("DOWN",) * row + ("RIGHT",) * column


def _section_home_route(section_id: str) -> tuple[str, ...]:
    try:
        index = SECTION_ORDER.index(section_id)
    except ValueError as exc:
        raise ValueError(f"unknown Encyclopedia section {section_id!r}") from exc
    return _grid_route(index, columns=3)


def _entry_route(section_id: str, page_id: str) -> tuple[str, ...]:
    order = SECTION_ENTRY_ORDER[section_id]
    index = order.index(page_id)
    if section_id == "animals":
        return _grid_route(index, columns=3)
    if section_id == "space":
        # The Solar-System section intentionally starts semantic focus on Earth.
        delta = index - 3
        return ("RIGHT",) * delta if delta >= 0 else ("LEFT",) * (-delta)
    if section_id in {"earth", "history"}:
        return ("RIGHT",) * index
    if section_id == "body":
        return _grid_route(index, columns=2)
    if section_id == "machines":
        return _grid_route(index, columns=3)
    raise ValueError(f"no entry navigation contract for {section_id!r}")


def build_entry_plans() -> tuple[EntryPlan, ...]:
    plans: list[EntryPlan] = []
    planned_entries = tuple(page for page in PLANNED_PAGES if page.role == "entry")
    for page in planned_entries:
        section_id = page.page_id.split(".", 1)[0]
        if section_id not in SECTION_ENTRY_ORDER:
            raise ValueError(f"planned page has unknown section: {page.page_id}")
        if page.page_id not in SECTION_ENTRY_ORDER[section_id]:
            raise ValueError(f"planned page lacks section navigation route: {page.page_id}")
        plans.append(
            EntryPlan(
                page_id=page.page_id,
                section_id=section_id,
                home_keys=_section_home_route(section_id),
                entry_keys=_entry_route(section_id, page.page_id),
            )
        )
    if len(plans) != 36 or len({plan.page_id for plan in plans}) != 36:
        raise ValueError("mechanical traversal must resolve exactly 36 unique entries")
    return tuple(plans)


def changed_pixel_fraction(before_path: Path, after_path: Path) -> float:
    with Image.open(before_path) as before_raw, Image.open(after_path) as after_raw:
        before = before_raw.convert("RGB")
        after = after_raw.convert("RGB")
        if before.size != after.size:
            raise ValueError("before/after screenshots have different dimensions")
        difference = ImageChops.difference(before, after)
        pixels = before.width * before.height
        if pixels < 1:
            return 0.0
        changed = sum(1 for pixel in difference.getdata() if pixel != (0, 0, 0))
        return changed / pixels


def _verify_png(path: Path, expected_size: tuple[int, int]) -> None:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            if image.size != expected_size:
                raise ValueError(
                    f"expected screenshot {expected_size[0]}x{expected_size[1]}, got {image.size}"
                )
    except Exception as exc:  # noqa: BLE001
        raise TraversalFailure("png-evidence", f"invalid PNG evidence {path}: {exc}") from exc


def _parse_viewport(value: str) -> tuple[int, int]:
    from greia_simulator.device import parse_viewport

    return parse_viewport(value)


class HeadlessEncyclopediaTraversal:
    """Own one real Shell/Activity session for the complete mechanical pass."""

    def __init__(
        self,
        *,
        workspace_dir: Path,
        evidence_dir: Path,
        locale: str,
        viewport: str,
    ) -> None:
        self.workspace_dir = workspace_dir.expanduser().resolve(strict=False)
        self.evidence_dir = evidence_dir.resolve(strict=False)
        self.locale = locale
        self.viewport = viewport
        self.viewport_size = _parse_viewport(viewport)
        self.screenshots_dir = self.evidence_dir / "screenshots"
        self.child_log_path = self.evidence_dir / "enciclopedia-child.log"
        self._workspace = None
        self._child: subprocess.Popen | None = None
        self._child_log = None
        self._launch_route = None
        self._records: list[EntryEvidence] = []
        self._section_pngs: dict[str, str] = {}
        self._status = "NOT_STARTED"
        self._first_failure: dict[str, str] | None = None

    @property
    def records(self) -> tuple[EntryEvidence, ...]:
        return tuple(self._records)

    def _log(self, message: str) -> None:
        print(f"[encyclopedia-traversal] {message}", flush=True)

    def _require_child(self) -> subprocess.Popen:
        if self._child is None:
            raise TraversalFailure("session", "headless child Shell has not started")
        return self._child

    def _current_activity_state(self) -> dict[str, object]:
        child = self._require_child()
        if child.poll() is not None:
            raise TraversalFailure(
                "child-lifecycle",
                f"child Shell exited unexpectedly with rc={child.returncode}",
            )
        try:
            state = headless._http_get_json("/api/state")
        except Exception as exc:  # noqa: BLE001
            raise TraversalFailure("remote-state", f"cannot read Simulator state: {exc}") from exc
        if state.get("mode") != "activity":
            raise TraversalFailure(
                "activity-mode",
                f"expected remote mode=activity, got {state.get('mode')!r}",
            )
        return state

    def _key(self, key: str, *, stage: str, timeout: float = 4.0) -> dict[str, object]:
        child = self._require_child()
        state = self._current_activity_state()
        before = int(state.get("frame_count", 0))
        if not headless._bridge_key(key):
            raise TraversalFailure(stage, f"remote key {key} was rejected")
        updated = headless._wait_for_state(
            lambda candidate: (
                candidate.get("mode") == "activity"
                and int(candidate.get("frame_count", 0)) > before
            ),
            timeout=timeout,
            child=child,
        )
        if updated is None:
            raise TraversalFailure(stage, f"no fresh Activity frame after semantic key {key}")
        return updated

    def _keys(self, keys: Iterable[str], *, stage: str) -> None:
        for index, key in enumerate(tuple(keys), start=1):
            self._key(key, stage=f"{stage} [{index}] {key}")

    def _capture(self, relative: str) -> Path:
        path = self.screenshots_dir / relative
        if not headless._screenshot(path):
            raise TraversalFailure("screenshot", f"could not capture {relative}")
        _verify_png(path, self.viewport_size)
        return path

    def start(self) -> None:
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        if self.workspace_dir.exists():
            shutil.rmtree(self.workspace_dir, ignore_errors=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        try:
            workspace, target_id = headless._prepare_workspace(
                self.workspace_dir,
                ACTIVITY_DIR,
                ACTIVITY_ID,
            )
        except Exception as exc:  # noqa: BLE001
            raise TraversalFailure("workspace", f"cannot prepare Simulator workspace: {exc}") from exc
        self._workspace = workspace
        if target_id != ACTIVITY_ID:
            raise TraversalFailure("workspace", f"resolved wrong Activity identity: {target_id}")
        try:
            route, visible_ids = headless._discover_launch_route(
                workspace,
                ACTIVITY_ID,
                locale=self.locale,
            )
        except Exception as exc:  # noqa: BLE001
            raise TraversalFailure("shell-route", f"cannot resolve child-visible launch route: {exc}") from exc
        self._launch_route = route
        self._log(f"Shell route ({len(visible_ids)} visible): {route.describe()}")

        env = os.environ.copy()
        env["PYTHONPATH"] = "src"
        env["GREIA_SIMULATOR_HEADLESS"] = "1"
        env["SDL_VIDEODRIVER"] = "dummy"
        env["SDL_AUDIODRIVER"] = "dummy"
        env.update(workspace.environment())

        self._child_log = self.child_log_path.open("wb")
        child = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "greia_simulator.child_shell",
                "--viewport",
                self.viewport,
                "--language",
                self.locale,
                "--capability",
                "display",
                "--capability",
                "keyboard",
                "--capability",
                "pointer",
                "--capability",
                "touch",
                "--capability",
                "audio.basic",
                "--remote-port",
                str(headless.DEFAULT_PORT),
            ],
            cwd=str(REPO_ROOT),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=self._child_log,
            stderr=subprocess.STDOUT,
        )
        self._child = child
        try:
            workspace.update_lock_child_pid(child.pid)
        except Exception as exc:  # noqa: BLE001
            raise TraversalFailure("workspace-lock", f"cannot register child PID: {exc}") from exc

        if not headless._wait_for_bridge(headless.DEFAULT_PORT, timeout=15.0):
            raise TraversalFailure("remote-bridge", "remote bridge never came up")
        shell_state = headless._wait_for_state(
            lambda state: int(state.get("frame_count", 0)) > 0,
            timeout=30.0,
            child=child,
        )
        if shell_state is None:
            raise TraversalFailure("shell-first-frame", "first Shell frame never arrived")
        self._capture("00-shell-profile-picker.png")

        activity_state = headless._send_profile_and_activity_launch(
            child=child,
            route=route,
        )
        if activity_state is None:
            raise TraversalFailure("activity-launch", "real Shell never produced Encyclopedia frame")
        self._capture("00-encyclopedia-home.png")
        self._status = "RUNNING"

    def traverse(self) -> None:
        plans = build_entry_plans()
        by_section = {
            section: tuple(plan for plan in plans if plan.section_id == section)
            for section in SECTION_ORDER
        }

        for section_index, section_id in enumerate(SECTION_ORDER, start=1):
            section_plans = by_section[section_id]
            if not section_plans:
                raise TraversalFailure("plan", f"section {section_id} has no entry plans")
            self._log(f"section {section_index}/6: {section_id}")
            self._keys(
                _section_home_route(section_id),
                stage=f"home -> {section_id} focus",
            )
            self._key("RETURN", stage=f"home -> {section_id} activate")
            section_png = self._capture(f"sections/{section_index:02d}-{section_id}.png")
            self._section_pngs[section_id] = section_png.relative_to(self.evidence_dir).as_posix()

            for entry_index, plan in enumerate(section_plans, start=1):
                self._log(
                    f"  entry {entry_index}/{len(section_plans)}: {plan.page_id}"
                )
                self._keys(
                    plan.entry_keys,
                    stage=f"{section_id} -> {plan.page_id} focus",
                )
                self._key("RETURN", stage=f"{section_id} -> {plan.page_id} activate")
                before = self._capture(f"entries/{plan.page_id}-before.png")

                self._keys(
                    plan.interaction_keys,
                    stage=f"{plan.page_id} primary interaction",
                )
                # Give short-lived visual effects a bounded opportunity to reach
                # their visible state while keeping the run deterministic.
                time.sleep(0.12)
                after = self._capture(f"entries/{plan.page_id}-after.png")
                fraction = changed_pixel_fraction(before, after)
                self._records.append(
                    EntryEvidence(
                        page_id=plan.page_id,
                        section_id=section_id,
                        before_png=before.relative_to(self.evidence_dir).as_posix(),
                        after_png=after.relative_to(self.evidence_dir).as_posix(),
                        interaction_keys=plan.interaction_keys,
                        changed_pixel_fraction=round(fraction, 6),
                    )
                )
                if fraction <= 0.0:
                    raise TraversalFailure(
                        "interaction-frame",
                        f"{plan.page_id} produced an identical before/after frame",
                    )
                self._key("ESCAPE", stage=f"{plan.page_id} internal Back -> {section_id}")

            self._key("ESCAPE", stage=f"{section_id} internal Back -> home")

        if len(self._records) != 36:
            raise TraversalFailure(
                "traversal-count",
                f"expected 36 entry evidence records, found {len(self._records)}",
            )
        self._capture("98-encyclopedia-home-after-traversal.png")
        self._status = "MECHANICAL_TRAVERSAL_COMPLETE"

    def return_to_shell(self) -> None:
        child = self._require_child()
        returned = headless._return_home(child=child, viewport=self.viewport)
        if returned is None:
            raise TraversalFailure("protected-home", "protected Home did not return to Shell")
        path = self.evidence_dir / "screenshots" / "99-returned-shell.png"
        if not headless._screenshot(path):
            raise TraversalFailure("protected-home", "could not capture returned Shell frame")
        _verify_png(path, self.viewport_size)
        self._status = "PASS"

    def close(self) -> None:
        child = self._child
        workspace = self._workspace
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=8.0)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=3.0)
        if workspace is not None:
            try:
                workspace.update_lock_child_pid(None)
            except Exception:  # noqa: BLE001
                pass
        if self._child_log is not None and not self._child_log.closed:
            self._child_log.close()
        if workspace is not None:
            try:
                workspace.release_lock()
            except Exception:  # noqa: BLE001
                pass

    def child_warnings(self) -> tuple[str, ...]:
        if not self.child_log_path.is_file():
            return ()
        try:
            lines = self.child_log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return ()
        return tuple(
            line
            for line in lines
            if "libpng" in line.casefold() or "warning" in line.casefold()
        )

    def summary(self) -> dict[str, object]:
        return {
            "status": self._status,
            "activity_id": ACTIVITY_ID,
            "locale": self.locale,
            "viewport": self.viewport,
            "shell_route": self._launch_route.describe() if self._launch_route else None,
            "sections_expected": 6,
            "sections_captured": len(self._section_pngs),
            "section_pngs": self._section_pngs,
            "entries_expected": 36,
            "entries_captured": len(self._records),
            "entry_evidence": [asdict(record) for record in self._records],
            "visual_signature_review_pending": True,
            "pre_reader_review_pending": True,
            "pointer_parity_review_pending": True,
            "narration_acceptance_pending": True,
            "child_warnings": list(self.child_warnings()),
            "first_failure": self._first_failure,
        }

    def record_failure(self, failure: TraversalFailure) -> None:
        self._status = "FAIL"
        self._first_failure = {"stage": failure.stage, "message": str(failure)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Traverse all Greia Encyclopedia v0.1 pages headlessly through the real Shell"
    )
    parser.add_argument("--workspace-dir", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--locale", default="it")
    parser.add_argument("--viewport", default="1024x600")
    args = parser.parse_args(argv)

    runner = HeadlessEncyclopediaTraversal(
        workspace_dir=args.workspace_dir,
        evidence_dir=args.evidence_dir,
        locale=args.locale,
        viewport=args.viewport,
    )
    exit_code = 0
    try:
        runner.start()
        runner.traverse()
        runner.return_to_shell()
    except TraversalFailure as failure:
        runner.record_failure(failure)
        print(
            f"ENCYCLOPEDIA MECHANICAL TRAVERSAL STOPPED at {failure.stage}: {failure}",
            file=sys.stderr,
            flush=True,
        )
        exit_code = 1
    except Exception as exc:  # noqa: BLE001
        failure = TraversalFailure("unexpected", f"{type(exc).__name__}: {exc}")
        runner.record_failure(failure)
        print(
            f"ENCYCLOPEDIA MECHANICAL TRAVERSAL STOPPED unexpectedly: {exc}",
            file=sys.stderr,
            flush=True,
        )
        exit_code = 1
    finally:
        runner.close()

    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.evidence_dir / "traversal-summary.json"
    summary_path.write_text(
        json.dumps(runner.summary(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if runner.summary().get("first_failure"):
        failure = runner.summary()["first_failure"]
        assert isinstance(failure, dict)
        (args.evidence_dir / "FIRST_FAILURE.txt").write_text(
            f"stage={failure.get('stage')}\nmessage={failure.get('message')}\n",
            encoding="utf-8",
        )

    if exit_code == 0:
        print("ENCYCLOPEDIA MECHANICAL TRAVERSAL PASS", flush=True)
        print(f"Evidence: {args.evidence_dir}", flush=True)
        print("Visual signature/pre-reader/pointer review is still pending.", flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
