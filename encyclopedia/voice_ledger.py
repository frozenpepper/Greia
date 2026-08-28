"""Shared parser and invariants for the encyclopedia voice coordination ledger.

Authoring-time only. Runtime code must never depend on this module.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


ROW_RE = re.compile(
    r"^\| (?P<status>[^|]+?) \| `(?P<cue>[^`]+)` \| (?P<kind>[^|]+?) \| "
    r"(?P<speaker>[^|]+?) \| `(?P<voice>[^`]+)` \| (?P<locale>it|en) \| "
    r"(?P<text>.*?) \| `(?P<filename>[^`]+)` \| `(?P<path>[^`]+)`"
    r"(?: \| (?P<notes>.*?))?\|?$"
)

LOCKED_STATUSES = frozenset(
    {
        "RECORDED_UNREVIEWED",
        "OWNER_ACCEPTED",
        "REJECTED_REDO",
        "SUPERSEDED",
        "BLOCKED",
    }
)


@dataclass(frozen=True, slots=True)
class VoiceLedgerRow:
    status: str
    cue_id: str
    kind: str
    speaker: str
    voice_id: str
    locale: str
    exact_text: str
    filename: str
    path: str
    notes: str

    @property
    def key(self) -> tuple[str, str]:
        return self.cue_id, self.locale


def parse_ledger_rows(text: str) -> dict[tuple[str, str], VoiceLedgerRow]:
    """Parse all data rows and reject duplicate cue/locale identities."""

    rows: dict[tuple[str, str], VoiceLedgerRow] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = ROW_RE.match(line)
        if not match:
            continue
        row = VoiceLedgerRow(
            status=match["status"].strip(),
            cue_id=match["cue"],
            kind=match["kind"].strip(),
            speaker=match["speaker"].strip(),
            voice_id=match["voice"],
            locale=match["locale"],
            exact_text=match["text"].strip(),
            filename=match["filename"],
            path=match["path"],
            notes=match["notes"].strip(),
        )
        if row.key in rows:
            raise ValueError(
                f"duplicate voice-ledger row {row.key!r} at line {line_number}"
            )
        rows[row.key] = row
    return rows
