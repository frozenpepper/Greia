"""Unit tests for the boot-marker analyzer (task B04, PLAN Steps 1.4/1.5).

Proves the Phase 1 marker contract at the parser surface: marker
parsing, the single first-frame invariant (missing and duplicate both
fail with a non-zero CLI exit, proven via subprocess, not claims),
malformed lines ignored, and intro duration calculation.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "tools" / "boot")
)

from analyze_boot_markers import (  # noqa: E402
    FIRST_FRAME_EVENT,
    analyze_journal,
    parse_systemd_analyze_time,
    validate_events,
)

ANALYZER = (
    Path(__file__).resolve().parent.parent
    / "tools"
    / "boot"
    / "analyze_boot_markers.py"
)


def _journal_line(ts: float, source: str, body: str) -> str:
    return f"[{ts:10.6f}] acer {source}: {body}"


FULL_JOURNAL = "\n".join(
    [
        _journal_line(
            5.0, "scrub[1]", "GREIA_BOOT event=launcher_execstartpre_scrub_begin"
        ),
        _journal_line(
            5.2, "scrub[1]", "GREIA_BOOT event=launcher_execstartpre_scrub_end"
        ),
        _journal_line(
            5.3, "vt[2]", "GREIA_BOOT event=launcher_execstartpre_vt_begin"
        ),
        _journal_line(
            5.4, "vt[2]", "GREIA_BOOT event=launcher_execstartpre_vt_end"
        ),
        _journal_line(6.0, "x-session[3]", "GREIA_BOOT event=x_session_enter"),
        _journal_line(
            6.1, "x-session[3]", "GREIA_BOOT event=hardware_watcher_spawned"
        ),
        _journal_line(
            6.5, "x-session[3]", "GREIA_BOOT event=child_shell_exec"
        ),
        _journal_line(
            7.0,
            "child_shell[4]",
            "GREIA_BOOT event=launcher_python_enter monotonic_ns=7000000000",
        ),
        _journal_line(
            8.0,
            "child_shell[4]",
            "GREIA_BOOT event=intro_enter monotonic_ns=8000000000",
        ),
        _journal_line(
            9.5,
            "child_shell[4]",
            f"GREIA_BOOT event={FIRST_FRAME_EVENT} monotonic_ns=9500000000",
        ),
        _journal_line(
            16.5,
            "child_shell[4]",
            "GREIA_BOOT event=intro_end monotonic_ns=16500000000",
        ),
    ]
) + "\n"


def _run_cli(journal_text: str) -> subprocess.CompletedProcess[str]:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".log", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(journal_text)
        path = handle.name
    try:
        return subprocess.run(
            [sys.executable, str(ANALYZER), path],
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        Path(path).unlink(missing_ok=True)


class TestMarkerParsing(unittest.TestCase):
    def test_shell_and_python_lines_parse_in_order(self) -> None:
        analysis = analyze_journal(FULL_JOURNAL)
        names = [event.name for event in analysis.events]
        self.assertEqual(
            names,
            [
                "launcher_execstartpre_scrub_begin",
                "launcher_execstartpre_scrub_end",
                "launcher_execstartpre_vt_begin",
                "launcher_execstartpre_vt_end",
                "x_session_enter",
                "hardware_watcher_spawned",
                "child_shell_exec",
                "launcher_python_enter",
                "intro_enter",
                "intro_first_frame_flipped",
                "intro_end",
            ],
        )
        # Journal monotonic time owns shell intervals; Python payload
        # is captured alongside.
        python_enter = analysis.events[7]
        self.assertEqual(python_enter.journal_ns, 7_000_000_000)
        self.assertEqual(python_enter.payload_ns, 7_000_000_000)
        scrub_begin = analysis.events[0]
        self.assertEqual(scrub_begin.journal_ns, 5_000_000_000)
        self.assertIsNone(scrub_begin.payload_ns)

    def test_valid_journal_passes_cli(self) -> None:
        proc = _run_cli(FULL_JOURNAL)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("intro_first_frame_flipped", proc.stdout)
        self.assertIn("first_frame_to_intro_end", proc.stdout)


class TestFirstFrameInvariant(unittest.TestCase):
    def test_missing_first_frame_marker_fails(self) -> None:
        journal = "\n".join(
            line
            for line in FULL_JOURNAL.splitlines()
            if FIRST_FRAME_EVENT not in line
        )
        analysis = analyze_journal(journal)
        errors = validate_events(analysis.events)
        self.assertTrue(errors, "expected an invariant violation")
        self.assertIn("absent", errors[0])
        proc = _run_cli(journal)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("absent", proc.stderr)

    def test_duplicate_first_frame_marker_fails(self) -> None:
        duplicate = (
            FULL_JOURNAL
            + _journal_line(
                10.0,
                "child_shell[4]",
                f"GREIA_BOOT event={FIRST_FRAME_EVENT} monotonic_ns=10000000000",
            )
            + "\n"
        )
        analysis = analyze_journal(duplicate)
        errors = validate_events(analysis.events)
        self.assertTrue(errors, "expected an invariant violation")
        self.assertIn("duplicat", errors[0])
        proc = _run_cli(duplicate)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("duplicat", proc.stderr)


class TestMalformedLines(unittest.TestCase):
    def test_malformed_and_unrelated_lines_are_ignored(self) -> None:
        journal = "\n".join(
            [
                "this is a normal unrelated journal line",
                "[    1.0] acer kernel: some kernel message",
                "GREIA_BOOT event=   ",
                "GREIA_BOOT event",
                "[    2.0] acer app[1]: GREIA_BOOT event=intro_enter",
                "[bad-timestamp] acer app[1]: GREIA_BOOT event=intro_end",
                "[    9.5] acer app[1]: "
                f"GREIA_BOOT event={FIRST_FRAME_EVENT}",
                "",
            ]
        ) + "\n"
        analysis = analyze_journal(journal)
        names = [event.name for event in analysis.events]
        self.assertEqual(
            names,
            ["intro_enter", "intro_end", FIRST_FRAME_EVENT],
        )
        # The untimed line keeps file order with no timestamp.
        self.assertIsNone(analysis.events[1].effective_ns)
        self.assertEqual(validate_events(analysis.events), [])
        proc = _run_cli(journal)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)


class TestIntroDuration(unittest.TestCase):
    def test_first_frame_to_intro_end_duration(self) -> None:
        analysis = analyze_journal(FULL_JOURNAL)
        delta_ns, detail = analysis.aggregates["first_frame_to_intro_end"]
        self.assertEqual(delta_ns, 7_000_000_000)
        self.assertIn(FIRST_FRAME_EVENT, detail)
        delta_ns, _detail = analysis.aggregates["intro_first_frame"]
        self.assertEqual(delta_ns, 1_500_000_000)

    def test_adjacent_durations_follow_journal_order(self) -> None:
        analysis = analyze_journal(FULL_JOURNAL)
        self.assertEqual(len(analysis.adjacent), len(analysis.events) - 1)
        first = analysis.adjacent[0]
        self.assertEqual(
            (first[0], first[1], first[2]),
            (
                "launcher_execstartpre_scrub_begin",
                "launcher_execstartpre_scrub_end",
                200_000_000,
            ),
        )


class TestSystemdAnalyzeTime(unittest.TestCase):
    def test_userspace_component_parses(self) -> None:
        text = (
            "Startup finished in 2.134s (kernel) + 3.001s (initrd) "
            "+ 12.456s (userspace) = 17.591s\n"
            "graphical.target reached after 12.100s in userspace\n"
        )
        components = parse_systemd_analyze_time(text)
        self.assertEqual(components["userspace"], 12_456_000_000)
        analysis = analyze_journal(FULL_JOURNAL, text)
        self.assertEqual(analysis.systemd_userspace_ns, 12_456_000_000)


if __name__ == "__main__":
    unittest.main()
