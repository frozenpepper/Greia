from __future__ import annotations

import unittest

from tools.encyclopedia_v01_source_gate import (
    GateFailure,
    integration_disposition,
    porcelain_path,
    unexpected_initial_paths,
)


class EncyclopediaV01SourceGateTests(unittest.TestCase):
    def test_porcelain_path_handles_plain_untracked_and_rename_rows(self) -> None:
        self.assertEqual(
            porcelain_path(" M encyclopedia/VOICE_RECORDING_REQUESTS.md"),
            "encyclopedia/VOICE_RECORDING_REQUESTS.md",
        )
        self.assertEqual(
            porcelain_path("?? encyclopedia/pages/animals/lion/assets/audio/it/intro.ogg"),
            "encyclopedia/pages/animals/lion/assets/audio/it/intro.ogg",
        )
        self.assertEqual(
            porcelain_path("R  old-name -> activities/enciclopedia_greia/main.py"),
            "activities/enciclopedia_greia/main.py",
        )

    def test_initial_worktree_allows_only_voice_coordination_and_evidence_state(self) -> None:
        allowed = (
            " M encyclopedia/VOICE_RECORDING_REQUESTS.md",
            "?? encyclopedia/pages/animals/lion/assets/audio/it/intro.ogg",
            "?? tmp/encyclopedia-v01-acceptance/example/log.txt",
        )
        self.assertEqual(unexpected_initial_paths(allowed), ())

    def test_initial_worktree_rejects_runtime_or_unrelated_source_changes(self) -> None:
        dirty = (
            " M encyclopedia/VOICE_RECORDING_REQUESTS.md",
            " M activities/enciclopedia_greia/pages/lion.py",
            " M src/greia_platform/localization.py",
        )
        self.assertEqual(
            unexpected_initial_paths(dirty),
            (
                "activities/enciclopedia_greia/pages/lion.py",
                "src/greia_platform/localization.py",
            ),
        )

    def test_integration_exit_contract_is_explicit(self) -> None:
        self.assertEqual(integration_disposition(0), "PASS")
        self.assertEqual(integration_disposition(1), "DRIFT")
        with self.assertRaises(GateFailure) as raised:
            integration_disposition(2)
        self.assertEqual(raised.exception.step, "voice-assets-check-before")
        self.assertEqual(raised.exception.returncode, 2)

    def test_malformed_porcelain_row_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            porcelain_path("??")


if __name__ == "__main__":
    unittest.main()
