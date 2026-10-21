import unittest
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from greia_voice_corpus.carriers import CARRIER_MODE, PREFIXES, eligible_text, freeze_row


class SpokenCarrierPolicyTests(unittest.TestCase):
    def row(self, *, speaker="dani", locale="fr", text="Trouve Luna.", state="READY"):
        return {"path": "activities/example/en/hello.wav", "state": state,
                "request": {"speaker": speaker, "locale": locale, "text": text,
                            "delivery_prompt": "Clear and friendly."}}

    def test_short_policy_word_and_unicode_letter_limits(self):
        self.assertTrue(eligible_text("Bravo!"))
        self.assertTrue(eligible_text("Trouve Luna."))
        self.assertTrue(eligible_text("Find the red moon!"))
        self.assertFalse(eligible_text("Find the very bright red moon!"))

    def test_freezes_exact_localized_target_and_word_count(self):
        frozen = freeze_row(self.row())
        self.assertEqual(frozen["mode"], CARRIER_MODE)
        self.assertEqual(frozen["prefix"], PREFIXES["fr"])
        self.assertEqual(frozen["target"], "Trouve Luna.")
        self.assertEqual(frozen["target_word_count"], 2)
        self.assertEqual(frozen["composite_text"], f"{PREFIXES['fr']} Trouve Luna.")

    def test_policy_does_not_select_other_speakers_or_blocked_rows(self):
        self.assertIsNone(freeze_row(self.row(speaker="leo")))
        self.assertIsNone(freeze_row(self.row(state="BLOCKED_METADATA")))
        self.assertIsNone(freeze_row(self.row(locale="de")))


if __name__ == "__main__":
    unittest.main()
