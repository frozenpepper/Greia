#!/usr/bin/env python3
"""Export encyclopedia voice-ledger rows as Greia Voice Engine JSONL requests.

Authoring-time only. The Markdown ledger remains the coordination authority; this
adapter only translates eligible rows into the repository-wide semantic voice
request contract. It never generates speech and never changes ledger status.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import sys

try:
    from .voice_ledger import VoiceLedgerRow, parse_ledger_rows
except ImportError:  # Direct script execution from the repository checkout.
    from voice_ledger import VoiceLedgerRow, parse_ledger_rows


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = ROOT / "encyclopedia" / "VOICE_RECORDING_REQUESTS.md"
SUPPORTED_KINDS = frozenset(
    {
        "character_dialogue",
        "pedagogical_speech",
        "dani_system_speech",
    }
)
SUPPORTED_SPEAKERS = frozenset(
    {"leo", "lilli", "flash", "tito", "momo", "dani", "pedagogical"}
)


def _staging_path(row: VoiceLedgerRow, root: Path) -> Path:
    """Validate and resolve one ledger staging path inside the authoring tree."""

    raw = PurePosixPath(row.path)
    if raw.is_absolute() or ".." in raw.parts:
        raise ValueError(f"unsafe staging path for {row.key!r}: {row.path!r}")
    if raw.suffix.casefold() != ".ogg":
        raise ValueError(f"voice batch output must be OGG for {row.key!r}: {row.path!r}")
    if raw.name != row.filename:
        raise ValueError(
            f"ledger filename/path mismatch for {row.key!r}: "
            f"{row.filename!r} != {raw.name!r}"
        )

    expected_prefix = ("encyclopedia", "pages")
    if raw.parts[:2] != expected_prefix:
        raise ValueError(
            f"voice batch output must use encyclopedia page staging for {row.key!r}: "
            f"{row.path!r}"
        )
    try:
        audio_index = raw.parts.index("audio")
    except ValueError as exc:
        raise ValueError(f"staging path lacks assets/audio for {row.key!r}: {row.path!r}") from exc
    if audio_index < 4 or raw.parts[audio_index - 1] != "assets":
        raise ValueError(f"invalid staging audio path for {row.key!r}: {row.path!r}")
    if audio_index + 1 >= len(raw.parts) or raw.parts[audio_index + 1] != row.locale:
        raise ValueError(
            f"staging locale/path mismatch for {row.key!r}: {row.path!r}"
        )

    root_resolved = root.resolve()
    resolved = (root / Path(*raw.parts)).resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"staging path escapes repository for {row.key!r}") from exc
    return resolved


def _receipt_path(staging: Path) -> Path:
    """Match the Voice Production Engine's sibling receipt naming contract."""

    return staging.with_suffix(staging.suffix + ".receipt.json")


def request_mapping(row: VoiceLedgerRow, root: Path, *, reject_existing: bool = True) -> dict[str, object]:
    """Translate one ledger row into the stable Voice Production Engine request."""

    if row.kind not in SUPPORTED_KINDS:
        raise ValueError(f"unsupported voice kind for {row.key!r}: {row.kind!r}")

    speaker = row.speaker.casefold()
    if row.kind == "pedagogical_speech":
        speaker = "pedagogical"
    if speaker not in SUPPORTED_SPEAKERS:
        raise ValueError(f"unsupported voice speaker for {row.key!r}: {row.speaker!r}")
    if row.kind == "character_dialogue" and speaker in {"dani", "pedagogical"}:
        raise ValueError(
            f"character_dialogue must name a canonical cloned character for {row.key!r}"
        )
    if row.kind == "dani_system_speech" and speaker != "dani":
        raise ValueError(f"dani_system_speech must use Dani for {row.key!r}")

    staging = _staging_path(row, root)
    if reject_existing:
        existing = tuple(
            path
            for path in (staging, _receipt_path(staging))
            if path.exists()
        )
        if existing:
            relative = ", ".join(
                str(path.relative_to(root.resolve()))
                if path.is_relative_to(root.resolve())
                else str(path)
                for path in existing
            )
            raise FileExistsError(
                f"REQUESTED review output/evidence already exists for {row.key!r}: {relative}; "
                "inspect the take/receipt and update recorder status instead of overwriting it"
            )

    verification = "auto" if row.kind == "character_dialogue" else "off"
    return {
        "speaker": speaker,
        "kind": row.kind,
        "locale": row.locale,
        "text": row.exact_text,
        "cue_id": row.cue_id,
        "output": row.path,
        "verification": verification,
        "max_attempts": 2,
    }


def batch_requests(
    ledger_text: str,
    root: Path,
    *,
    status: str = "REQUESTED",
    reject_existing: bool = True,
) -> tuple[dict[str, object], ...]:
    """Return deterministic semantic requests for rows with the selected status."""

    rows = parse_ledger_rows(ledger_text)
    selected = tuple(row for row in rows.values() if row.status == status)
    return tuple(
        request_mapping(row, root, reject_existing=reject_existing)
        for row in selected
    )


def render_jsonl(requests: tuple[dict[str, object], ...]) -> str:
    if not requests:
        return ""
    return "\n".join(
        json.dumps(request, ensure_ascii=False, separators=(",", ":"))
        for request in requests
    ) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export encyclopedia voice-ledger rows as Greia Voice Engine JSONL"
    )
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--status", default="REQUESTED")
    parser.add_argument("--output", type=Path, help="write JSONL here instead of stdout")
    parser.add_argument(
        "--allow-existing",
        action="store_true",
        help="include rows whose staging output/receipt already exists (normally unsafe)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="require --output to already equal the deterministic rendered batch",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.check and args.output is None:
        print("--check requires --output", file=sys.stderr)
        return 2

    try:
        ledger_text = args.ledger.read_text(encoding="utf-8")
        requests = batch_requests(
            ledger_text,
            ROOT,
            status=args.status,
            reject_existing=not args.allow_existing,
        )
        rendered = render_jsonl(requests)

        if args.check:
            if not args.output.exists():
                print(f"missing batch file: {args.output}", file=sys.stderr)
                return 1
            if args.output.read_text(encoding="utf-8") != rendered:
                print(f"voice batch is out of sync: {args.output}", file=sys.stderr)
                return 1
            print(f"voice batch in sync: requests={len(requests)} path={args.output}")
            return 0

        if args.output is None:
            sys.stdout.write(rendered)
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
            print(f"wrote voice batch: requests={len(requests)} path={args.output}")
        return 0
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
