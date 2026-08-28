from __future__ import annotations

import inspect
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from greia_voice_core.providers import ChatterboxMLXProvider
from record_shared_character_utterances import _result_counts_as_success


class ChatterboxProviderPolicyTests(unittest.TestCase):
    def test_character_speech_does_not_use_word_count_token_budget(self):
        self.assertFalse(hasattr(ChatterboxMLXProvider, "_token_budget"))
        source = inspect.getsource(ChatterboxMLXProvider.generate)
        self.assertNotIn("max_new_tokens", source)

    def test_shared_asr_warning_is_unresolved_production_work(self):
        self.assertTrue(_result_counts_as_success("REVIEW_REQUIRED"))
        self.assertTrue(_result_counts_as_success("EXISTING_REVIEW_CANDIDATE"))
        self.assertFalse(_result_counts_as_success("REVIEW_REQUIRED_ASR_WARNING"))
        self.assertFalse(_result_counts_as_success("REJECTED"))
        self.assertFalse(_result_counts_as_success("UNAVAILABLE"))
        self.assertFalse(_result_counts_as_success("BLOCKED_PARTIAL_OUTPUT"))


if __name__ == "__main__":
    unittest.main()
