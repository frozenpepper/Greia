from __future__ import annotations

from pathlib import Path
import unittest

from encyclopedia.export_voice_batch import batch_requests
from encyclopedia.sync_voice_requests import render_ledger


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "encyclopedia" / "VOICE_RECORDING_REQUESTS.md"


class EncyclopediaVoiceBatchLocalStateTests(unittest.TestCase):
    def test_requested_rows_have_no_preexisting_staging_output(self) -> None:
        """A produced take must leave REQUESTED before another batch can overwrite it."""

        synchronized = render_ledger(LEDGER.read_text(encoding="utf-8"))
        batch_requests(synchronized, ROOT)


if __name__ == "__main__":
    unittest.main()
