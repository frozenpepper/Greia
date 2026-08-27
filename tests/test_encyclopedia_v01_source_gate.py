from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "encyclopedia_v01_source_gate.py"
SPEC = importlib.util.spec_from_file_location("greia_encyclopedia_v01_source_gate", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

GateFailure = MODULE.GateFailure
integration_disposition = MODULE.integration_disposition
porcelain_path = MODULE.porcelain_path
unexpected_final_paths = MODULE.unexpected_final_paths
unexpected_initial_paths = MODULE.unexpected_initial_paths


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

    def test_final_worktree_without_audio_integration_allows_only_coordination_state(self) -> None:
        allowed = (
            " M encyclopedia/VOICE_RECORDING_REQUESTS.md",
            "?? encyclopedia/pages/animals/lion/assets/audio/it/intro.ogg",
            "?? tmp/encyclopedia-v01-acceptance/example/source-gate-summary.json",
        )
        self.assertEqual(
            unexpected_final_paths(allowed, integration_executed=False),
            (),
        )

    def test_final_worktree_allows_runtime_audio_only_when_integrator_ran(self) -> None:
        runtime_changes = (
            " M encyclopedia/VOICE_RECORDING_REQUESTS.md",
            " M activities/enciclopedia_greia/locales/it.json",
            " M activities/enciclopedia_greia/locales/en.json",
            "?? activities/enciclopedia_greia/assets/audio/it/animals/lion/intro-tito.ogg",
        )
        self.assertEqual(
            unexpected_final_paths(runtime_changes, integration_executed=True),
            (),
        )
        self.assertEqual(
            unexpected_final_paths(runtime_changes, integration_executed=False),
            (
                "activities/enciclopedia_greia/locales/it.json",
                "activities/enciclopedia_greia/locales/en.json",
                "activities/enciclopedia_greia/assets/audio/it/animals/lion/intro-tito.ogg",
            ),
        )

    def test_final_worktree_rejects_unrelated_mutations_even_after_integration(self) -> None:
        dirty = (
            " M encyclopedia/VOICE_RECORDING_REQUESTS.md",
            " M activities/enciclopedia_greia/locales/it.json",
            " M activities/enciclopedia_greia/pages/lion.py",
            " M src/greia_platform/localization.py",
        )
        self.assertEqual(
            unexpected_final_paths(dirty, integration_executed=True),
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
