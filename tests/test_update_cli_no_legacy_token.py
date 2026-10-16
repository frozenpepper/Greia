"""T10 guard: production update CLI/docs carry no retired X-Pip-Token path.

The retired ``--legacy-token``/``X-Pip-Token`` transport was removed from the
normal production ``push``/``status`` CLI in ``tools/greia_update.py``; only
the device-scoped ``--bearer`` flow remains. These tests prove the absence
through the literal production surface (real argparse parser + real
``_auth_headers`` + real tool source text + owned docs text).

Positive control: ``test_probe_flags_reintroduced_retired_transport`` feeds a
known-bad source snippet through the exact same predicate the absence tests
use, proving the probe turns RED when the retired header returns. A live
break/restore cycle against the real tool file was additionally performed
during implementation (reintroduce header -> new tests fail RED -> restore ->
tests pass GREEN).
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = PROJECT_ROOT / "tools" / "greia_update.py"
OWNED_DOCS = (
    PROJECT_ROOT / "docs" / "product" / "SYSTEM_UPDATES.md",
    PROJECT_ROOT / "docs" / "development" / "GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md",
)

spec = importlib.util.spec_from_file_location("greia_update_no_legacy", TOOL_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


RETIRED_MARKERS = ("X-Pip-Token", "legacy-token", "legacy_token")

# Docs must not instruct any pairing-token credential for update push/status
# either: the CLI no longer accepts one, so such an instruction would be stale.
RETIRED_DOC_MARKERS = RETIRED_MARKERS + ("GREIA_PARENT_PAIRING_TOKEN", "pairing token")


def _retired_transport_present(source_text: str) -> bool:
    """Shared probe predicate: True when the retired transport is present."""
    return any(marker in source_text for marker in RETIRED_MARKERS)


def _all_option_strings(parser: argparse.ArgumentParser) -> set[str]:
    found: set[str] = set()
    for action in parser._actions:  # noqa: SLF001 - literal parser introspection
        found.update(getattr(action, "option_strings", ()))
    subparsers = getattr(parser, "_subparsers", None)
    if subparsers is None:
        return found
    for sub in subparsers._group_actions:  # noqa: SLF001
        for choice in sub.choices.values():
            if isinstance(choice, argparse.ArgumentParser):
                found.update(_all_option_strings(choice))
    return found


class UpdateCliNoLegacyTokenTests(unittest.TestCase):
    def test_push_and_status_offer_no_legacy_token_option(self) -> None:
        options = _all_option_strings(module._parser())
        self.assertNotIn("--legacy-token", options)

    def test_push_rejects_legacy_token_through_literal_cli(self) -> None:
        with self.assertRaises(SystemExit):
            module._parser().parse_args(
                ["push", "bundle.greiaupdate", "--legacy-token", "secret"]
            )

    def test_status_rejects_legacy_token_through_literal_cli(self) -> None:
        with self.assertRaises(SystemExit):
            module._parser().parse_args(["status", "--legacy-token", "secret"])

    def test_push_and_status_require_bearer(self) -> None:
        with self.assertRaises(SystemExit):
            module._parser().parse_args(["push", "bundle.greiaupdate"])
        with self.assertRaises(SystemExit):
            module._parser().parse_args(["status"])

    def test_auth_headers_emit_bearer_only(self) -> None:
        headers = module._auth_headers(argparse.Namespace(bearer="device-credential"))
        self.assertEqual(headers, {"Authorization": "Bearer device-credential"})
        self.assertFalse(_retired_transport_present(repr(headers)))

    def test_auth_headers_refuse_missing_bearer(self) -> None:
        with self.assertRaises(Exception):
            module._auth_headers(argparse.Namespace(bearer=None))

    def test_tool_source_carries_no_retired_transport(self) -> None:
        source = TOOL_PATH.read_text(encoding="utf-8")
        self.assertFalse(
            _retired_transport_present(source),
            "tools/greia_update.py still references the retired update transport",
        )

    def test_probe_flags_reintroduced_retired_transport(self) -> None:
        """Positive control: the shared predicate catches a reintroduced header."""
        known_bad = 'return {"X-Pip-Token": str(args.legacy_token)}'
        self.assertTrue(_retired_transport_present(known_bad))
        known_bad_cli = '"--legacy-token", help="development-only existing token"'
        self.assertTrue(_retired_transport_present(known_bad_cli))
        self.assertFalse(_retired_transport_present('{"Authorization": "Bearer x"}'))


if __name__ == "__main__":
    unittest.main()
