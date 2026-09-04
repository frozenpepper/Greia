#!/usr/bin/env python3
"""Analyze Greia boot markers from a journal text export.

Consumes the Phase 1 marker contract:

- shell lines ``GREIA_BOOT event=<name>`` (journal monotonic time owns
  shell intervals; PLAN Step 1.2 / task B02);
- Python lines ``GREIA_BOOT event=<name> monotonic_ns=<int>``
  (PLAN Step 1.3 / task B03);
- optionally ``systemd-analyze time`` output.

Output: the ordered event list, adjacent-event durations, and the
aggregate intervals named by PLAN Step 1.4.

The parser exits non-zero when ``intro_first_frame_flipped`` is absent
or duplicated. Malformed/unrelated journal lines are ignored. Unknown
``GREIA_BOOT`` event names are kept but reported as warnings so a
vocabulary deviation is never silently assumed away.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field


FIRST_FRAME_EVENT = "intro_first_frame_flipped"

# PLAN Step 1.1 required vocabulary. B02 reported (and B02 review
# accepted) that ``launcher_execstartpre_hardware_begin/_end`` have no
# shell hook point anywhere in the tree, so that pair is expected to be
# absent-by-design until B05 reconciles the vocabulary.
KNOWN_EVENTS = frozenset(
    [
        "first_boot_enter",
        "first_boot_marker_exit",
        "launcher_execstartpre_scrub_begin",
        "launcher_execstartpre_scrub_end",
        "launcher_execstartpre_vt_begin",
        "launcher_execstartpre_vt_end",
        "launcher_execstartpre_hardware_begin",
        "launcher_execstartpre_hardware_end",
        "x_session_enter",
        "hardware_watcher_spawned",
        "child_shell_exec",
        "launcher_python_enter",
        "launcher_construct_begin",
        "launcher_construct_end",
        "activity_sources_begin",
        "activity_sources_end",
        "activity_discover_begin",
        "activity_discover_end",
        "activity_runtime_build_begin",
        "activity_runtime_build_end",
        "history_prepare_begin",
        "history_prepare_end",
        "pygame_display_init_begin",
        "pygame_display_init_end",
        "display_set_mode_begin",
        "display_set_mode_end",
        "intro_enter",
        "intro_first_frame_flipped",
        "intro_end",
    ]
)

# Aggregate intervals owned by PLAN Step 1.4: (key, human label,
# start event, end event). The userspace entry is anchored at boot
# (t=0) because journal short-monotonic timestamps count from boot.
AGGREGATE_SPECS = (
    (
        "userspace_to_launcher_service",
        "userspace -> launcher service (boot to first pre-hook marker)",
        None,
        "launcher_execstartpre_scrub_begin",
    ),
    (
        "launcher_pre_hooks",
        "launcher pre-hooks (scrub begin -> VT end)",
        "launcher_execstartpre_scrub_begin",
        "launcher_execstartpre_vt_end",
    ),
    (
        "x_session",
        "X/session (x-session enter -> child-shell exec)",
        "x_session_enter",
        "child_shell_exec",
    ),
    (
        "python_pre_display",
        "Python pre-display (python enter -> display set-mode end)",
        "launcher_python_enter",
        "display_set_mode_end",
    ),
    (
        "display_creation",
        "display creation (pygame display-init begin -> set-mode end)",
        "pygame_display_init_begin",
        "display_set_mode_end",
    ),
    (
        "intro_first_frame",
        "intro first frame (intro enter -> first frame flipped)",
        "intro_enter",
        "intro_first_frame_flipped",
    ),
    (
        "first_frame_to_intro_end",
        "first frame -> intro end",
        "intro_first_frame_flipped",
        "intro_end",
    ),
)

# ``journalctl -o short-monotonic`` prefixes lines with ``[  SEC.usec]``.
JOURNAL_TS_RE = re.compile(r"^\[\s*(\d+)\.(\d+)\]")

MARKER_RE = re.compile(
    r"GREIA_BOOT event=([A-Za-z0-9_]+)(?:\s+monotonic_ns=(\d+))?"
)


@dataclass
class BootEvent:
    """One parsed marker line."""

    name: str
    line_no: int
    journal_ns: int | None = None
    payload_ns: int | None = None

    @property
    def effective_ns(self) -> int | None:
        """Journal time when present, else the Python monotonic payload."""
        if self.journal_ns is not None:
            return self.journal_ns
        return self.payload_ns


@dataclass
class BootAnalysis:
    """Parsed result plus derived intervals."""

    events: list[BootEvent] = field(default_factory=list)
    # (prev_name, cur_name, delta_ns or None when untimed)
    adjacent: list[tuple[str, str, int | None]] = field(default_factory=list)
    # aggregate key -> (delta_ns or None, detail string)
    aggregates: dict[str, tuple[int | None, str]] = field(default_factory=dict)
    unknown_events: list[str] = field(default_factory=list)
    systemd_userspace_ns: int | None = None


def parse_journal_text(text: str) -> list[BootEvent]:
    """Parse marker events from journal export text.

    Lines without a well-formed ``GREIA_BOOT event=<name>`` token are
    ignored, as are lines whose event name is empty.
    """
    events: list[BootEvent] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        match = MARKER_RE.search(line)
        if match is None:
            continue
        name, payload = match.group(1), match.group(2)
        journal_ns: int | None = None
        ts_match = JOURNAL_TS_RE.match(line)
        if ts_match is not None:
            seconds = int(ts_match.group(1))
            fraction = ts_match.group(2)
            # Journal prints microseconds; scale to nanoseconds exactly.
            journal_ns = seconds * 1_000_000_000 + int(
                (fraction + "000000000")[:9]
            )
        events.append(
            BootEvent(
                name=name,
                line_no=line_no,
                journal_ns=journal_ns,
                payload_ns=int(payload) if payload is not None else None,
            )
        )
    return events


def validate_events(events: list[BootEvent]) -> list[str]:
    """Return invariant violations (empty means the set is acceptable)."""
    count = sum(1 for event in events if event.name == FIRST_FRAME_EVENT)
    if count == 0:
        return [
            f"missing required marker: {FIRST_FRAME_EVENT} is absent "
            "(no unambiguous first-frame timestamp)"
        ]
    if count > 1:
        return [
            f"duplicated required marker: {FIRST_FRAME_EVENT} appears "
            f"{count} times (first-frame timestamp is ambiguous)"
        ]
    return []


def compute_adjacent(events: list[BootEvent]) -> list[tuple[str, str, int | None]]:
    """Duration between each adjacent event pair in journal order."""
    adjacent: list[tuple[str, str, int | None]] = []
    for previous, current in zip(events, events[1:]):
        if previous.effective_ns is None or current.effective_ns is None:
            adjacent.append((previous.name, current.name, None))
        else:
            adjacent.append(
                (previous.name, current.name, current.effective_ns - previous.effective_ns)
            )
    return adjacent


def _first_at_or_after(
    events: list[BootEvent], name: str, start_index: int = 0
) -> tuple[int, BootEvent | None]:
    for index in range(start_index, len(events)):
        if events[index].name == name:
            return index, events[index]
    return -1, None


def compute_aggregates(events: list[BootEvent]) -> dict[str, tuple[int | None, str]]:
    """Compute the PLAN Step 1.4 aggregate intervals."""
    aggregates: dict[str, tuple[int | None, str]] = {}
    for key, _label, start_name, end_name in AGGREGATE_SPECS:
        if start_name is None:
            # Anchored at boot: journal time of the end marker.
            _, end = _first_at_or_after(events, end_name)
            if end is None or end.effective_ns is None:
                aggregates[key] = (
                    None,
                    f"unknown (missing or untimed {end_name})",
                )
            else:
                aggregates[key] = (end.effective_ns, f"boot -> {end_name}")
            continue
        start_index, start = _first_at_or_after(events, start_name)
        if start is None:
            aggregates[key] = (None, f"unknown (missing {start_name})")
            continue
        _, end = _first_at_or_after(events, end_name, start_index)
        if end is None:
            aggregates[key] = (
                None,
                f"unknown (missing {end_name} at/after {start_name})",
            )
            continue
        if start.effective_ns is None or end.effective_ns is None:
            aggregates[key] = (
                None,
                f"unknown (untimed {start_name} -> {end_name})",
            )
            continue
        aggregates[key] = (
            end.effective_ns - start.effective_ns,
            f"{start_name} -> {end_name}",
        )
    return aggregates


_TIME_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(ms|s|min|h)")


def _to_ns(value: float, unit: str) -> int:
    scale = {"ms": 1_000_000, "s": 1_000_000_000, "min": 60_000_000_000,
             "h": 3_600_000_000_000}[unit]
    return int(value * scale)


def parse_systemd_analyze_time(text: str) -> dict[str, int]:
    """Parse ``systemd-analyze time`` output into component nanoseconds.

    Handles lines like ``Startup finished in 1.2s (kernel) + 3.4s
    (initrd) + 5.6s (userspace) = 10.2s`` plus the firmware/loader
    variants newer systemd prints.
    """
    result: dict[str, int] = {}
    for match in _TIME_RE.finditer(text):
        rest = text[match.end():]
        label_match = re.match(r"\s*\(([^)]+)\)", rest)
        if label_match is None:
            continue
        label = label_match.group(1).strip().lower()
        result[label] = _to_ns(float(match.group(1)), match.group(2))
    return result


def analyze_journal(
    text: str, systemd_time_text: str | None = None
) -> BootAnalysis:
    """Parse journal text and derive intervals and aggregates."""
    events = parse_journal_text(text)
    unknown = sorted({event.name for event in events} - KNOWN_EVENTS)
    analysis = BootAnalysis(
        events=events,
        adjacent=compute_adjacent(events),
        aggregates=compute_aggregates(events),
        unknown_events=unknown,
    )
    if systemd_time_text:
        components = parse_systemd_analyze_time(systemd_time_text)
        analysis.systemd_userspace_ns = components.get("userspace")
    return analysis


def format_ns(value_ns: int | None) -> str:
    """Render nanoseconds as seconds with millisecond-friendly precision."""
    if value_ns is None:
        return "unknown"
    return f"{value_ns / 1_000_000_000:.6f}s"


def render_text(analysis: BootAnalysis) -> str:
    """Render the ordered event list, durations, and aggregates."""
    lines = ["ordered events:"]
    for index, event in enumerate(analysis.events):
        lines.append(
            f"  [{index:3d}] line={event.line_no} "
            f"t={format_ns(event.effective_ns)} event={event.name}"
        )
    lines.append("adjacent durations:")
    if not analysis.adjacent:
        lines.append("  (fewer than two events)")
    for previous, current, delta_ns in analysis.adjacent:
        lines.append(f"  {previous} -> {current}: {format_ns(delta_ns)}")
    lines.append("aggregates:")
    for key, label, _start, _end in AGGREGATE_SPECS:
        delta_ns, detail = analysis.aggregates.get(key, (None, "unknown"))
        lines.append(f"  {key}: {format_ns(delta_ns)} [{detail}]")
    if analysis.systemd_userspace_ns is not None:
        lines.append(
            "systemd userspace total: "
            f"{format_ns(analysis.systemd_userspace_ns)}"
        )
    if analysis.unknown_events:
        lines.append(
            "unknown GREIA_BOOT events (kept, check vocabulary): "
            + ", ".join(analysis.unknown_events)
        )
    return "\n".join(lines) + "\n"


def render_json(analysis: BootAnalysis) -> str:
    """Render the analysis as JSON for B05 metric collection."""
    payload = {
        "events": [
            {
                "name": event.name,
                "line_no": event.line_no,
                "t_ns": event.effective_ns,
                "journal_ns": event.journal_ns,
                "payload_ns": event.payload_ns,
            }
            for event in analysis.events
        ],
        "adjacent": [
            {"from": previous, "to": current, "delta_ns": delta_ns}
            for previous, current, delta_ns in analysis.adjacent
        ],
        "aggregates": {
            key: {"delta_ns": delta_ns, "detail": detail}
            for key, (delta_ns, detail) in analysis.aggregates.items()
        },
        "unknown_events": analysis.unknown_events,
        "systemd_userspace_ns": analysis.systemd_userspace_ns,
    }
    return json.dumps(payload, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        description="Analyze Greia GREIA_BOOT markers from a journal "
        "text export (PLAN Step 1.4)."
    )
    parser.add_argument("journal", help="journal text export file")
    parser.add_argument(
        "--systemd-analyze-time",
        default=None,
        help="optional `systemd-analyze time` output file",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    args = parser.parse_args(argv)

    try:
        with open(args.journal, encoding="utf-8") as handle:
            journal_text = handle.read()
    except OSError as exc:
        print(f"error: cannot read journal file: {exc}", file=sys.stderr)
        return 1

    systemd_text: str | None = None
    if args.systemd_analyze_time is not None:
        try:
            with open(args.systemd_analyze_time, encoding="utf-8") as handle:
                systemd_text = handle.read()
        except OSError as exc:
            print(
                f"error: cannot read systemd-analyze file: {exc}",
                file=sys.stderr,
            )
            return 1

    analysis = analyze_journal(journal_text, systemd_text)

    for error in validate_events(analysis.events):
        print(f"error: {error}", file=sys.stderr)
    if validate_events(analysis.events):
        return 2

    for unknown in analysis.unknown_events:
        print(
            f"warning: unknown GREIA_BOOT event kept as-is: {unknown}",
            file=sys.stderr,
        )

    if args.format == "json":
        sys.stdout.write(render_json(analysis))
    else:
        sys.stdout.write(render_text(analysis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
