#!/usr/bin/env python3
"""Run the deterministic pre-Simulator Greia Encyclopedia v0.1 closure gate.

This helper is authoring/test tooling only. It performs the non-interactive part
of ``GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md`` in one fail-closed
process:

1. validate branch/worktree boundaries;
2. synchronize and check the 378-row voice ledger;
3. run focused provider-free Encyclopedia contracts;
4. run ``make verify``;
5. package only already-``OWNER_ACCEPTED`` narration when required;
6. rerun Encyclopedia contracts after runtime-audio changes;
7. reject unexpected post-gate worktree mutations;
8. run ``git diff --check`` and write a machine-readable summary.

It deliberately does NOT generate speech, change recorder statuses, launch the
Simulator, repair source, commit, push, or use GitHub-hosted execution.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER_RELATIVE = Path("encyclopedia/VOICE_RECORDING_REQUESTS.md")
EXPECTED_ROWS = 378
EXPECTED_BRANCH = "main"
EVIDENCE_DEFAULT = Path("tmp/encyclopedia-v01-acceptance")
RUNTIME_AUDIO_PREFIX = "activities/enciclopedia_greia/assets/audio/"
RUNTIME_LOCALE_PATHS = frozenset(
    {
        "activities/enciclopedia_greia/locales/it.json",
        "activities/enciclopedia_greia/locales/en.json",
    }
)

FOCUSED_TESTS = (
    "tests.test_encyclopedia_authoring_tools",
    "tests.test_encyclopedia_voice_batch_state",
    "tests.test_activity_enciclopedia",
    "tests.test_encyclopedia_v01_source_gate",
    "tests.test_activity_contract",
    "tests.test_first_party_activity_audience_metadata",
    "tests.test_first_party_activity_readiness",
)
POST_AUDIO_TESTS = (
    "tests.test_encyclopedia_authoring_tools",
    "tests.test_encyclopedia_voice_batch_state",
    "tests.test_activity_enciclopedia",
)


class GateFailure(RuntimeError):
    """One fail-closed acceptance step failed."""

    def __init__(self, step: str, message: str, *, returncode: int = 1) -> None:
        super().__init__(message)
        self.step = step
        self.returncode = returncode


@dataclass(frozen=True, slots=True)
class CommandResult:
    step: str
    command: tuple[str, ...]
    returncode: int
    log_path: Path


@dataclass(frozen=True, slots=True)
class GateSummary:
    starting_sha: str
    branch: str
    evidence_dir: str
    voice_rows: int
    status_counts: dict[str, int]
    integration_check_before: str
    integration_executed: bool
    integration_check_after: str
    simulator_pending: bool = True

    def as_json(self) -> dict[str, object]:
        return {
            "starting_sha": self.starting_sha,
            "branch": self.branch,
            "evidence_dir": self.evidence_dir,
            "voice_rows": self.voice_rows,
            "status_counts": dict(sorted(self.status_counts.items())),
            "integration_check_before": self.integration_check_before,
            "integration_executed": self.integration_executed,
            "integration_check_after": self.integration_check_after,
            "simulator_pending": self.simulator_pending,
        }


class EvidenceRunner:
    """Execute commands once and preserve their combined output per gate step."""

    def __init__(self, repo_root: Path, evidence_dir: Path) -> None:
        self.repo_root = repo_root
        self.evidence_dir = evidence_dir
        self.results: list[CommandResult] = []

    def run(
        self,
        step: str,
        command: Sequence[str],
        *,
        accepted_codes: Iterable[int] = (0,),
    ) -> CommandResult:
        accepted = frozenset(accepted_codes)
        log_path = self.evidence_dir / f"{step}.txt"
        rendered_command = " ".join(command)
        print(f"[{step}] {rendered_command}", flush=True)

        completed = subprocess.run(
            list(command),
            cwd=self.repo_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        output = completed.stdout or ""
        log_path.write_text(
            f"$ {rendered_command}\n\n{output}",
            encoding="utf-8",
        )
        if output:
            print(output, end="" if output.endswith("\n") else "\n")

        result = CommandResult(step, tuple(command), completed.returncode, log_path)
        self.results.append(result)
        if completed.returncode not in accepted:
            raise GateFailure(
                step,
                f"{step} failed with exit code {completed.returncode}; see {log_path}",
                returncode=completed.returncode or 1,
            )
        return result


# ``git status --porcelain=v1`` reserves columns 0:2 for status and column 2 as
# a separator. Renames are intentionally returned as their destination path so
# they still fail unless that destination itself is an allowed workflow path.
def porcelain_path(line: str) -> str:
    if len(line) < 4:
        raise ValueError(f"malformed git status line: {line!r}")
    path = line[3:]
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    return path


def _is_recording_staging_path(path: str) -> bool:
    return path.startswith("encyclopedia/pages/") and "/assets/audio/" in path


def _is_evidence_path(path: str) -> bool:
    return path.startswith("tmp/encyclopedia-v01-acceptance/")


def _is_runtime_audio_path(path: str) -> bool:
    return path.startswith(RUNTIME_AUDIO_PREFIX)


def unexpected_initial_paths(status_lines: Sequence[str]) -> tuple[str, ...]:
    """Return dirty paths that are not legitimate recorder/evidence state."""

    unexpected: list[str] = []
    for line in status_lines:
        if not line:
            continue
        path = porcelain_path(line)
        if path == LEDGER_RELATIVE.as_posix():
            continue
        if _is_recording_staging_path(path) or _is_evidence_path(path):
            continue
        unexpected.append(path)
    return tuple(unexpected)


def unexpected_final_paths(
    status_lines: Sequence[str],
    *,
    integration_executed: bool,
) -> tuple[str, ...]:
    """Reject mutations outside the gate's explicitly owned output surfaces.

    Voice synchronization may update the Markdown ledger. Evidence and recorder
    staging state are workflow-local. Runtime audio files and the two locale
    bundles are allowed only when the OWNER_ACCEPTED integrator actually ran.
    Any other source/runtime mutation means the deterministic gate did more than
    its contract permits and must not report PASS.
    """

    unexpected: list[str] = []
    for line in status_lines:
        if not line:
            continue
        path = porcelain_path(line)
        if path == LEDGER_RELATIVE.as_posix():
            continue
        if _is_recording_staging_path(path) or _is_evidence_path(path):
            continue
        if integration_executed and (
            _is_runtime_audio_path(path) or path in RUNTIME_LOCALE_PATHS
        ):
            continue
        unexpected.append(path)
    return tuple(unexpected)


def integration_disposition(returncode: int) -> str:
    if returncode == 0:
        return "PASS"
    if returncode == 1:
        return "DRIFT"
    raise GateFailure(
        "voice-assets-check-before",
        f"accepted-audio integration validation failed with exit code {returncode}",
        returncode=returncode or 2,
    )


def _git_output(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise GateFailure(
            "git-preflight",
            (completed.stderr or completed.stdout or "git command failed").strip(),
            returncode=completed.returncode,
        )
    return completed.stdout.rstrip("\n")


def _status_lines(repo_root: Path) -> tuple[str, ...]:
    text = _git_output(repo_root, "status", "--porcelain=v1", "--untracked-files=all")
    return tuple(line for line in text.splitlines() if line)


def _write_lines(path: Path, lines: Sequence[str]) -> None:
    text = "\n".join(lines)
    path.write_text(text + ("\n" if text else ""), encoding="utf-8")


def _voice_counts(repo_root: Path) -> tuple[int, dict[str, int]]:
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from encyclopedia.voice_ledger import parse_ledger_rows

    ledger = repo_root / LEDGER_RELATIVE
    rows = parse_ledger_rows(ledger.read_text(encoding="utf-8"))
    if len(rows) != EXPECTED_ROWS:
        raise GateFailure(
            "voice-row-count",
            f"voice ledger row invariant failed: {len(rows)} != {EXPECTED_ROWS}",
        )
    counts = Counter(row.status for row in rows.values())
    return len(rows), dict(counts)


def _focused_command(tests: Sequence[str]) -> tuple[str, ...]:
    return (sys.executable, "-m", "unittest", *tests, "-v")


def _make_evidence_dir(repo_root: Path, evidence_root: Path) -> Path:
    root = evidence_root if evidence_root.is_absolute() else repo_root / evidence_root
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    evidence = root / run_id
    evidence.mkdir(parents=True, exist_ok=False)
    latest = root / ".latest-run"
    relative = evidence.relative_to(repo_root) if evidence.is_relative_to(repo_root) else evidence
    latest.write_text(f"{relative.as_posix()}\n", encoding="utf-8")
    return evidence


def run_gate(repo_root: Path, evidence_root: Path) -> GateSummary:
    repo_root = repo_root.resolve()
    branch = _git_output(repo_root, "branch", "--show-current")
    starting_sha = _git_output(repo_root, "rev-parse", "HEAD")
    if branch != EXPECTED_BRANCH:
        raise GateFailure(
            "branch",
            f"expected branch {EXPECTED_BRANCH!r}, found {branch!r}",
        )

    initial_status = _status_lines(repo_root)
    unexpected = unexpected_initial_paths(initial_status)
    if unexpected:
        raise GateFailure(
            "worktree-preflight",
            "unexpected dirty paths before Encyclopedia acceptance: "
            + ", ".join(unexpected),
        )

    evidence = _make_evidence_dir(repo_root, evidence_root)
    _write_lines(evidence / "git-status-before.txt", initial_status)
    (evidence / "starting-sha.txt").write_text(f"{starting_sha}\n", encoding="utf-8")
    (evidence / "branch.txt").write_text(f"{branch}\n", encoding="utf-8")
    runner = EvidenceRunner(repo_root, evidence)

    try:
        runner.run(
            "voice-sync",
            (sys.executable, "encyclopedia/sync_voice_requests.py"),
        )
        runner.run(
            "voice-sync-check",
            (sys.executable, "encyclopedia/sync_voice_requests.py", "--check"),
        )
        voice_rows, status_counts = _voice_counts(repo_root)
        (evidence / "voice-row-count.json").write_text(
            json.dumps(
                {"rows": voice_rows, "status_counts": dict(sorted(status_counts.items()))},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        runner.run("focused-tests", _focused_command(FOCUSED_TESTS))
        runner.run("make-verify", ("make", "verify"))

        integration_check = runner.run(
            "voice-assets-check-before",
            (sys.executable, "encyclopedia/integrate_voice_assets.py", "--check"),
            accepted_codes=(0, 1),
        )
        before = integration_disposition(integration_check.returncode)
        integration_executed = before == "DRIFT"
        after = "not-applicable"
        if integration_executed:
            runner.run(
                "voice-assets-integrate",
                (sys.executable, "encyclopedia/integrate_voice_assets.py"),
            )
            runner.run(
                "voice-assets-check-after",
                (sys.executable, "encyclopedia/integrate_voice_assets.py", "--check"),
            )
            runner.run("post-audio-focused-tests", _focused_command(POST_AUDIO_TESTS))
            after = "PASS"

        runner.run("git-diff-check", ("git", "diff", "--check"))
        final_status = _status_lines(repo_root)
        _write_lines(evidence / "git-status-after.txt", final_status)
        unexpected_final = unexpected_final_paths(
            final_status,
            integration_executed=integration_executed,
        )
        if unexpected_final:
            raise GateFailure(
                "worktree-postflight",
                "unexpected paths changed during Encyclopedia source gate: "
                + ", ".join(unexpected_final),
            )

        summary = GateSummary(
            starting_sha=starting_sha,
            branch=branch,
            evidence_dir=(
                evidence.relative_to(repo_root).as_posix()
                if evidence.is_relative_to(repo_root)
                else str(evidence)
            ),
            voice_rows=voice_rows,
            status_counts=status_counts,
            integration_check_before=before,
            integration_executed=integration_executed,
            integration_check_after=after,
        )
        (evidence / "source-gate-summary.json").write_text(
            json.dumps(summary.as_json(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("SOURCE GATE PASS — Simulator acceptance is still pending.")
        print(f"Evidence: {summary.evidence_dir}")
        return summary
    except GateFailure as exc:
        (evidence / "FIRST_FAILURE.txt").write_text(
            f"step={exc.step}\nreturncode={exc.returncode}\nmessage={exc}\n",
            encoding="utf-8",
        )
        _write_lines(evidence / "git-status-at-failure.txt", _status_lines(repo_root))
        print(f"SOURCE GATE STOPPED at {exc.step}: {exc}", file=sys.stderr)
        print(f"Evidence: {evidence}", file=sys.stderr)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Greia checkout root (default: repository containing this tool)",
    )
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=EVIDENCE_DEFAULT,
        help="evidence parent directory; relative paths are resolved under the checkout",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="print the deterministic step order without executing or mutating anything",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.plan_only:
        print("Encyclopedia v0.1 deterministic source gate:")
        print("1. branch/worktree preflight")
        print("2. sync voice ledger")
        print("3. sync --check + 378-row invariant")
        print("4. focused provider-free tests")
        print("5. make verify")
        print("6. OWNER_ACCEPTED integration check/integration if required")
        print("7. post-audio focused tests if runtime resources changed")
        print("8. git diff --check + strict worktree postflight + summary")
        print("9. STOP: real Simulator pass remains manual and mandatory")
        return 0

    try:
        run_gate(args.repo_root, args.evidence_root)
    except GateFailure as exc:
        return exc.returncode or 1
    except (OSError, ValueError) as exc:
        print(f"source gate failed before completion: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
