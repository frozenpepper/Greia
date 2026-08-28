#!/usr/bin/env python3
"""Synchronize the encyclopedia's single voice-request ledger from research.

This is an authoring-time tool, never child-runtime code. It reads the approved
Italian/English narration authorities under ``encyclopedia/research/**`` and
writes factual requests into ``VOICE_RECORDING_REQUESTS.md`` while preserving
recorder-owned status and notes.

Two research generations intentionally coexist in v0.1:

- early pages use the original human-readable ``Child-facing wording contract``;
- later pages use machine-readable semantic cue headings under
  ``Approved narration wording``.

The synchronizer supports both without mass-rewriting historical authorities.
Legacy-format topics must already exist in the ledger; their queued bilingual
wording is checked exactly against research before being retained. Canonical
format topics are generated directly from semantic cue blocks.

The tool deliberately does not generate speech. Greia narration remains
prerecorded through the established voice-production workflow on
development/parent hardware.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import re
import sys

try:
    from .voice_ledger import LOCKED_STATUSES, VoiceLedgerRow, parse_ledger_rows
except ImportError:  # Direct script execution from the repository checkout.
    from voice_ledger import LOCKED_STATUSES, VoiceLedgerRow, parse_ledger_rows


ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "VOICE_RECORDING_REQUESTS.md"
RESEARCH_ROOT = ROOT / "research"
EXPECTED_V01_TOPIC_COUNT = 36
EXPECTED_V01_RECORDING_ROWS = 378

_PRESENTER_RE = re.compile(r"^\*\*Presenter:\*\*\s+(.+?)\s+\(`([^`]+)`\)\s*$", re.MULTILINE)
_CANONICAL_CUE_RE = re.compile(
    r"^### `(?P<cue>encyclopedia\.[^`]+)`\s*\n\n"
    r"\*\*it:\*\* (?P<it>.*?)\n\n"
    r"\*\*en:\*\* (?P<en>.*?)(?=\n\n### `|\Z)",
    re.MULTILINE | re.DOTALL,
)
_LEGACY_CUE_RE = re.compile(
    r"^### (?P<label>[^\n]+?) — (?P<speaker>[^\n]+?)\s*\n\n"
    r"\*\*Italian\*\*\s*\n`(?P<it>[^`]*)`\s*\n\n"
    r"\*\*English\*\*\s*\n`(?P<en>[^`]*)`",
    re.MULTILINE,
)
_CANONICAL_VOICE_IDS = {
    "Dani": "greia.dani.system-v1",
    "Flash": "greia.flash.v1",
    "Leo": "greia.leo.v1",
    "Lilli": "greia.lilli.v1",
    "Momo": "greia.momo.v1",
    "Tito": "greia.tito.v1",
}


@dataclass(frozen=True, slots=True)
class TopicSpec:
    batch_id: str
    page_id: str


@dataclass(frozen=True, slots=True)
class RequestRow:
    cue_id: str
    kind: str
    speaker: str
    voice_id: str
    locale: str
    exact_text: str
    filename: str
    path: str


# Stable v0.1 authoring order. The old historical E3/E4/E5 labels are retained
# where they already existed; later breadth batches continue monotonically.
TOPICS: tuple[TopicSpec, ...] = (
    TopicSpec("E4-LION-01", "animals.lion"),
    TopicSpec("E4-ELEPHANT-01", "animals.elephant"),
    TopicSpec("E3-OCTOPUS-01", "animals.octopus"),
    TopicSpec("E4-BEE-01", "animals.bee"),
    TopicSpec("E4-PENGUIN-01", "animals.penguin"),
    TopicSpec("E4-FROG-01", "animals.frog"),
    TopicSpec("E5-SUN-01", "space.sun"),
    TopicSpec("E5-MERCURY-01", "space.mercury"),
    TopicSpec("E5-VENUS-01", "space.venus"),
    TopicSpec("E5-EARTH-01", "space.earth"),
    TopicSpec("E5-MOON-01", "space.moon"),
    TopicSpec("E6-MARS-01", "space.mars"),
    TopicSpec("E6-JUPITER-01", "space.jupiter"),
    TopicSpec("E3-SATURN-01", "space.saturn"),
    TopicSpec("E6-URANUS-01", "space.uranus"),
    TopicSpec("E6-NEPTUNE-01", "space.neptune"),
    TopicSpec("E3-VOLCANO-01", "earth.volcano"),
    TopicSpec("E7-RAIN-01", "earth.rain"),
    TopicSpec("E7-OCEAN-01", "earth.ocean"),
    TopicSpec("E7-TREE-01", "earth.tree"),
    TopicSpec("E7-RAINBOW-01", "earth.rainbow"),
    TopicSpec("E3-HEART-01", "body.heart"),
    TopicSpec("E8-LUNGS-01", "body.lungs"),
    TopicSpec("E8-BONES-01", "body.bones"),
    TopicSpec("E8-TEETH-01", "body.teeth"),
    TopicSpec("E8-SENSES-01", "body.senses"),
    TopicSpec("E3-GEARS-01", "machines.gears"),
    TopicSpec("E9-MAGNET-01", "machines.magnet"),
    TopicSpec("E9-BICYCLE-01", "machines.bicycle"),
    TopicSpec("E9-AIRPLANE-01", "machines.airplane"),
    TopicSpec("E9-BRIDGE-01", "machines.bridge"),
    TopicSpec("E10-DINOSAURS-01", "history.dinosaurs"),
    TopicSpec("E3-FOSSILS-01", "history.fossils"),
    TopicSpec("E10-MAMMOTH-01", "history.mammoth"),
    TopicSpec("E10-CAVE-PAINTINGS-01", "history.cave_paintings"),
    TopicSpec("E10-PYRAMIDS-01", "history.pyramids"),
)


def _research_path(page_id: str) -> Path:
    section, topic = page_id.split(".", 1)
    return RESEARCH_ROOT / section / f"{topic}.md"


def _validate_topic_inventory() -> None:
    if len(TOPICS) != EXPECTED_V01_TOPIC_COUNT:
        raise ValueError(f"v0.1 topic inventory drifted: {len(TOPICS)} != {EXPECTED_V01_TOPIC_COUNT}")
    page_ids = tuple(spec.page_id for spec in TOPICS)
    batch_ids = tuple(spec.batch_id for spec in TOPICS)
    if len(set(page_ids)) != len(page_ids):
        raise ValueError("duplicate page_id in voice TOPICS")
    if len(set(batch_ids)) != len(batch_ids):
        raise ValueError("duplicate batch_id in voice TOPICS")


def _expected_voice_id(speaker: str) -> str:
    try:
        return _CANONICAL_VOICE_IDS[speaker]
    except KeyError as exc:
        raise ValueError(f"unknown encyclopedia presenter: {speaker!r}") from exc


def _request_from_existing(row: VoiceLedgerRow) -> RequestRow:
    return RequestRow(
        cue_id=row.cue_id,
        kind=row.kind,
        speaker=row.speaker,
        voice_id=row.voice_id,
        locale=row.locale,
        exact_text=row.exact_text,
        filename=row.filename,
        path=row.path,
    )


def _parse_canonical_topic(spec: TopicSpec, text: str) -> list[RequestRow] | None:
    cue_matches = list(_CANONICAL_CUE_RE.finditer(text))
    if not cue_matches:
        return None

    presenter_match = _PRESENTER_RE.search(text)
    if presenter_match is None:
        raise ValueError(f"missing Presenter metadata in {_research_path(spec.page_id)}")
    speaker = presenter_match.group(1).strip()
    voice_id = presenter_match.group(2).strip()
    expected_voice = _expected_voice_id(speaker)
    if voice_id != expected_voice:
        raise ValueError(
            f"presenter voice drift in {_research_path(spec.page_id)}: "
            f"{voice_id!r} != {expected_voice!r}"
        )
    kind = "dani_system_speech" if voice_id == "greia.dani.system-v1" else "character_dialogue"
    speaker_slug = speaker.casefold().replace(" ", "-")
    section, topic = spec.page_id.split(".", 1)

    rows: list[RequestRow] = []
    for cue_match in cue_matches:
        cue_id = cue_match["cue"]
        expected_prefix = f"encyclopedia.{spec.page_id}."
        if not cue_id.startswith(expected_prefix):
            raise ValueError(f"cue {cue_id!r} does not belong to {spec.page_id!r}")
        suffix = cue_id.rsplit(".", 1)[-1]
        filename = f"{suffix}-{speaker_slug}.ogg"
        for locale in ("it", "en"):
            exact_text = cue_match[locale].strip()
            if "\n" in exact_text:
                raise ValueError(f"multiline narration is not supported for {cue_id}/{locale}")
            rows.append(
                RequestRow(
                    cue_id=cue_id,
                    kind=kind,
                    speaker=speaker,
                    voice_id=voice_id,
                    locale=locale,
                    exact_text=exact_text,
                    filename=filename,
                    path=f"encyclopedia/pages/{section}/{topic}/assets/audio/{locale}/{filename}",
                )
            )
    return rows


def _parse_legacy_topic(
    spec: TopicSpec,
    text: str,
    existing_rows: dict[tuple[str, str], VoiceLedgerRow],
) -> list[RequestRow]:
    """Validate original human-readable wording against already-queued rows.

    Legacy authorities predate semantic cue headings, so cue IDs/filenames are
    retained from the established queue rather than guessed from prose labels.
    The research document still owns the wording: both locale strings and the
    named speaker must match exactly, in established cue order.
    """

    blocks = list(_LEGACY_CUE_RE.finditer(text))
    if not blocks:
        raise ValueError(
            f"research authority has neither canonical nor legacy narration blocks: "
            f"{_research_path(spec.page_id)}"
        )

    prefix = f"encyclopedia.{spec.page_id}."
    topic_rows = [
        row for row in existing_rows.values() if row.cue_id.startswith(prefix)
    ]
    if not topic_rows:
        raise ValueError(
            f"legacy narration for {spec.page_id!r} has no established ledger rows; "
            "migrate that research authority to canonical semantic cue headings first"
        )

    cue_ids: list[str] = []
    seen: set[str] = set()
    for row in topic_rows:
        if row.cue_id not in seen:
            seen.add(row.cue_id)
            cue_ids.append(row.cue_id)
    if len(cue_ids) != len(blocks):
        raise ValueError(
            f"legacy narration block count drift for {spec.page_id!r}: "
            f"research={len(blocks)} ledger={len(cue_ids)}"
        )

    rows: list[RequestRow] = []
    for cue_id, block in zip(cue_ids, blocks):
        speaker = block["speaker"].strip()
        expected_voice = _expected_voice_id(speaker)
        for locale in ("it", "en"):
            key = (cue_id, locale)
            try:
                existing = existing_rows[key]
            except KeyError as exc:
                raise ValueError(f"legacy ledger is missing bilingual row {key!r}") from exc
            approved_text = block[locale].strip()
            if existing.exact_text != approved_text:
                raise ValueError(
                    f"legacy research/ledger wording drift for {key!r}; "
                    "do not overwrite recorded wording in place"
                )
            if existing.speaker != speaker:
                raise ValueError(
                    f"legacy research/ledger speaker drift for {key!r}: "
                    f"{existing.speaker!r} != {speaker!r}"
                )
            if existing.voice_id != expected_voice:
                raise ValueError(
                    f"legacy voice-id drift for {key!r}: "
                    f"{existing.voice_id!r} != {expected_voice!r}"
                )
            rows.append(_request_from_existing(existing))
    return rows


def _parse_topic(
    spec: TopicSpec,
    existing_rows: dict[tuple[str, str], VoiceLedgerRow],
) -> list[RequestRow]:
    path = _research_path(spec.page_id)
    text = path.read_text(encoding="utf-8")
    canonical = _parse_canonical_topic(spec, text)
    if canonical is not None:
        return canonical
    return _parse_legacy_topic(spec, text, existing_rows)


def _row_markdown(row: RequestRow, existing: VoiceLedgerRow | None) -> str:
    status = existing.status if existing is not None else "REQUESTED"
    notes = existing.notes if existing is not None else ""

    if existing is not None and existing.status in LOCKED_STATUSES:
        immutable_expected = (
            row.kind,
            row.speaker,
            row.voice_id,
            row.exact_text,
            row.filename,
            row.path,
        )
        immutable_existing = (
            existing.kind,
            existing.speaker,
            existing.voice_id,
            existing.exact_text,
            existing.filename,
            existing.path,
        )
        if immutable_expected != immutable_existing:
            raise ValueError(
                f"locked recorded row drifted: {(row.cue_id, row.locale)}; "
                "create a revised cue/filename instead of overwriting it"
            )

    return (
        f"| {status} | `{row.cue_id}` | {row.kind} | {row.speaker} | `{row.voice_id}` | "
        f"{row.locale} | {row.exact_text} | `{row.filename}` | `{row.path}` | {notes} |"
    )


def _manual_prefix(existing_text: str) -> str:
    """Keep instructions, vocabulary and the manually-owned E0 navigation batch."""
    marker = "\n---\n\n## 4. Requested batch "
    index = existing_text.find(marker)
    if index < 0:
        raise ValueError("cannot find first factual-batch boundary in voice ledger")
    return existing_text[:index].rstrip()


def render_ledger(existing_text: str) -> str:
    _validate_topic_inventory()
    existing_rows = parse_ledger_rows(existing_text)
    parts = [_manual_prefix(existing_text)]
    generated_rows: list[RequestRow] = []

    for ordinal, spec in enumerate(TOPICS, start=4):
        rows = _parse_topic(spec, existing_rows)
        generated_rows.extend(rows)
        research_rel = _research_path(spec.page_id).relative_to(ROOT.parent).as_posix()
        parts.extend(
            (
                "",
                "---",
                "",
                f"## {ordinal}. Requested batch {spec.batch_id}",
                "",
                "Research/provenance authority for this batch:",
                "",
                "```text",
                research_rel,
                "```",
                "",
                "| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |",
                "|---|---|---|---|---|---|---|---|---|---|",
            )
        )
        for row in rows:
            parts.append(_row_markdown(row, existing_rows.get((row.cue_id, row.locale))))

    generated_keys = {(row.cue_id, row.locale) for row in generated_rows}
    if len(generated_keys) != len(generated_rows):
        raise ValueError("generated factual voice rows contain duplicate cue/locale keys")

    # E0 navigation/orientation is deliberately manual because it has no
    # factual research record. All of its cue IDs have exactly two dots.
    manual_keys = {key for key in existing_rows if key[0].count(".") == 2}
    unexplained = set(existing_rows) - generated_keys - manual_keys
    if unexplained:
        raise ValueError(f"existing factual rows are not represented by TOPICS: {sorted(unexplained)!r}")

    total_rows = len(generated_keys) + len(manual_keys)
    if total_rows != EXPECTED_V01_RECORDING_ROWS:
        raise ValueError(
            f"v0.1 recording row count drifted: {total_rows} != {EXPECTED_V01_RECORDING_ROWS}"
        )

    parts.extend(
        (
            "",
            "---",
            "",
            "## Full v0.1 queue checkpoint",
            "",
            f"Generated/retained exact recording rows: **{total_rows}**.",
            "",
            "All 36 factual v0.1 entries now have research-ready bilingual requests. Do not add post-v0.1 topic batches until the owner deliberately expands the encyclopedia scope.",
            "",
        )
    )
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the ledger differs; do not write")
    args = parser.parse_args(argv)

    current = LEDGER.read_text(encoding="utf-8")
    rendered = render_ledger(current)
    if current == rendered:
        print("voice request ledger already synchronized")
        return 0
    if args.check:
        print("voice request ledger is out of date", file=sys.stderr)
        return 1
    LEDGER.write_text(rendered, encoding="utf-8")
    print("voice request ledger synchronized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
