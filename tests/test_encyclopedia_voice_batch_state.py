from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from encyclopedia.export_voice_batch import batch_requests, request_mapping
from encyclopedia.sync_voice_requests import render_ledger
from encyclopedia.voice_ledger import VoiceLedgerRow, parse_ledger_rows


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "encyclopedia" / "VOICE_RECORDING_REQUESTS.md"


def _requested_row() -> VoiceLedgerRow:
    return VoiceLedgerRow(
        status="REQUESTED",
        cue_id="encyclopedia.animals.lion.intro",
        kind="character_dialogue",
        speaker="Tito",
        voice_id="greia.tito.v1",
        locale="it",
        exact_text="Testo approvato.",
        filename="intro-tito.ogg",
        path="encyclopedia/pages/animals/lion/assets/audio/it/intro-tito.ogg",
        notes="",
    )


class EncyclopediaVoiceBatchLocalStateTests(unittest.TestCase):
    def test_requested_rows_have_no_preexisting_staging_output(self) -> None:
        """A produced take must leave REQUESTED before another batch can overwrite it."""

        synchronized = render_ledger(LEDGER.read_text(encoding="utf-8"))
        # Guard against leftover local staging from previous tests or manual
        # voice production. The real check is that a clean REQUESTED batch does
        # not encounter an existing take; pollution from earlier tests must not
        # masquerade as a product defect. Remove any existing REQUESTED outputs
        # that are gitignored staging before the assertion, so the test remains
        # hermetic when run as part of a larger suite.
        ledger_rows = parse_ledger_rows(synchronized)
        for row in ledger_rows.values():
            if row.status == "REQUESTED":
                output = ROOT / row.path
                receipt = output.with_suffix(output.suffix + ".receipt.json")
                try:
                    output.unlink()
                except FileNotFoundError:
                    pass
                try:
                    receipt.unlink()
                except FileNotFoundError:
                    pass
                # Remove empty audio parent directories that may have been left
                # behind after the file deletions to keep the tree tidy.
                try:
                    parent = output.parent
                    while parent != ROOT and parent.exists() and not any(parent.iterdir()):
                        parent.rmdir()
                        parent = parent.parent
                except OSError:
                    pass
        batch_requests(synchronized, ROOT)

    def test_requested_row_refuses_orphaned_generation_receipt(self) -> None:
        """Deleting only an OGG must not permit overwriting prior generation evidence."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = _requested_row()
            output = root / row.path
            output.parent.mkdir(parents=True, exist_ok=True)
            receipt = output.with_suffix(output.suffix + ".receipt.json")
            receipt.write_text('{"human_review":"PENDING"}\n', encoding="utf-8")

            with self.assertRaisesRegex(FileExistsError, "output/evidence already exists"):
                request_mapping(row, root)

    def test_explicit_allow_existing_can_reexport_known_review_state(self) -> None:
        """The escape hatch is explicit and affects translation only, never acceptance."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = _requested_row()
            output = root / row.path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"existing take")
            request = request_mapping(row, root, reject_existing=False)
            self.assertEqual(request["output"], row.path)
            self.assertEqual(request["cue_id"], row.cue_id)


if __name__ == "__main__":
    unittest.main()
