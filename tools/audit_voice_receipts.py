#!/usr/bin/env python3
"""Audit Voice Engine receipts against the canonical similarity scorer.

Recomputes ``transcript_similarity(expected, transcript)`` from
``tools/greia_voice_core/verification.py`` for every receipt under a review
workspace and compares the recomputed score to the stored ``verification.score``.

Hard-fails the audit (exit 2) if any receipt's stored score is not
reproducible from its own text + transcript within tolerance, or if the stored
disposition disagrees with the recomputed disposition at the
``pass_threshold`` (default 0.72).

Exits 0 on a clean audit. Prints a per-row summary table to stdout.

This is an evidence-only tool. It does not regenerate audio, does not call
Whisper, and does not modify receipts. It is the audit that the
``WHISPER_MISMATCH_REPORT.md`` table is built on.

Usage::

    python3 tools/audit_voice_receipts.py \
        --shared-root tmp/shared-character-utterances \
        --intro-root tmp/character-intros
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from greia_voice_core.verification import (  # noqa: E402
    normalize_transcript,
    transcript_similarity,
)


@dataclass
class Row:
    file: str
    character: str
    locale: str
    expected: str
    actual: str
    stored_disp: str
    stored_score: float | None
    recomputed: float | None
    char_score: float
    precision: float
    recall: float
    f1: float
    attempts: int


def _scan(root: Path) -> list[Row]:
    rows: list[Row] = []
    for p in sorted(root.rglob("*.wav.receipt.json")):
        rows.extend(_row_for(p))
    for p in sorted(root.rglob("*.ogg.receipt.json")):
        rows.extend(_row_for(p))
    return rows


def _row_for(p: Path) -> list[Row]:
    r = json.loads(p.read_text(encoding="utf-8"))
    v = r.get("verification") or {}
    expected = r["request"]["text"]
    actual = v.get("transcript") or ""
    stored_disp = v.get("disposition")
    stored_score = v.get("score")
    if stored_disp in ("NOT_APPLICABLE", "NOT_RUN") or stored_score is None:
        # Not scorable; skip audit but keep in the count.
        return [
            Row(
                file=str(p),
                character=r["request"]["speaker"],
                locale=r["request"]["locale"],
                expected=expected,
                actual=actual,
                stored_disp=stored_disp or "NONE",
                stored_score=stored_score,
                recomputed=None,
                char_score=0.0,
                precision=0.0,
                recall=0.0,
                f1=0.0,
                attempts=r.get("attempts", 0),
            )
        ]
    en = normalize_transcript(expected)
    an = normalize_transcript(actual)
    recomputed = transcript_similarity(expected, actual)
    ewords = en.split()
    awords = an.split()
    e_set = set(ewords)
    a_set = set(awords)
    overlap = len(e_set & a_set)
    precision = overlap / max(1, len(a_set))
    recall = overlap / max(1, len(e_set))
    f1 = 0.0 if not (precision + recall) else 2 * precision * recall / (precision + recall)
    # Character ratio for the table.
    from difflib import SequenceMatcher
    char = SequenceMatcher(None, en, an).ratio()
    return [
        Row(
            file=str(p),
            character=r["request"]["speaker"],
            locale=r["request"]["locale"],
            expected=expected,
            actual=actual,
            stored_disp=stored_disp,
            stored_score=stored_score,
            recomputed=recomputed,
            char_score=round(char, 4),
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1=round(f1, 4),
            attempts=r.get("attempts", 0),
        )
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--shared-root",
        type=Path,
        default=PROJECT_ROOT / "tmp" / "shared-character-utterances",
    )
    parser.add_argument(
        "--intro-root",
        type=Path,
        default=PROJECT_ROOT / "tmp" / "character-intros",
    )
    parser.add_argument(
        "--pass-threshold",
        type=float,
        default=0.72,
        help="Pass threshold used by the Whisper verifier; audit checks stored disposition against it.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.0005,
        help="Allowed |stored - recomputed| before hard-fail.",
    )
    args = parser.parse_args(argv)

    rows: list[Row] = []
    if args.shared_root.is_dir():
        rows.extend(_scan(args.shared_root))
    if args.intro_root.is_dir():
        rows.extend(_scan(args.intro_root))

    scorable = [r for r in rows if r.recomputed is not None]
    nonscorable = [r for r in rows if r.recomputed is None]

    score_mismatches: list[Row] = []
    disp_mismatches: list[Row] = []
    for r in scorable:
        if r.stored_score is None or abs(r.stored_score - r.recomputed) > args.tolerance:
            score_mismatches.append(r)
        expected_disp = "PASS" if r.recomputed >= args.pass_threshold else "WARN"
        if r.stored_disp != expected_disp:
            disp_mismatches.append(r)

    pass_n = sum(1 for r in scorable if r.stored_disp == "PASS")
    warn_n = sum(1 for r in scorable if r.stored_disp == "WARN")
    print(f"Audited receipts: {len(rows)} total, {len(scorable)} scorable, {len(nonscorable)} NOT_APPLICABLE/NOT_RUN.")
    print(f"  PASS: {pass_n}  WARN: {warn_n}")
    print(f"  Score mismatches (|stored - recomputed| > {args.tolerance}): {len(score_mismatches)}")
    print(f"  Disposition mismatches (stored disagrees with recomputed at threshold {args.pass_threshold}): {len(disp_mismatches)}")

    if score_mismatches:
        print("\nSCORE MISMATCHES:")
        for r in score_mismatches:
            print(f"  {r.file}")
            print(f"    stored: {r.stored_disp} score={r.stored_score}  recomputed={r.recomputed}")
            print(f"    expected: {r.expected!r}")
            print(f"    transcript: {r.actual!r}")

    if disp_mismatches:
        print("\nDISPOSITION MISMATCHES:")
        for r in disp_mismatches:
            print(f"  {r.file}")
            print(f"    stored: {r.stored_disp} score={r.stored_score}  recomputed={r.recomputed}")

    if warn_n:
        print(f"\nWARN rows ({warn_n}), sorted by stored score:")
        for r in sorted([r for r in scorable if r.stored_disp == "WARN"], key=lambda x: x.stored_score):
            print(
                f"  {r.stored_score:.4f}  char={r.char_score:.4f} p={r.precision:.4f} r={r.recall:.4f} f1={r.f1:.4f}  {r.file}"
            )
            print(f"    expected: {r.expected!r}  ->  whisper: {r.actual!r}")

    if score_mismatches or disp_mismatches:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
