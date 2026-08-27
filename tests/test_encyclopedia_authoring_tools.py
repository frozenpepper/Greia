from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from encyclopedia.integrate_voice_assets import (
    integrate_accepted_assets,
    plan_accepted_assets,
)
from encyclopedia.sync_voice_requests import (
    EXPECTED_V01_RECORDING_ROWS,
    render_ledger,
)
from encyclopedia.voice_ledger import parse_ledger_rows


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "encyclopedia" / "VOICE_RECORDING_REQUESTS.md"

_TABLE_HEADER = """| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|"""


def _row(
    *,
    status: str,
    cue: str,
    locale: str,
    path: str,
    filename: str = "intro-tito.ogg",
    notes: str = "",
) -> str:
    return (
        f"| {status} | `{cue}` | character_dialogue | Tito | `greia.tito.v1` | "
        f"{locale} | Exact approved line. | `{filename}` | `{path}` | {notes} |"
    )


def _ledger(*rows: str) -> str:
    return _TABLE_HEADER + "\n" + "\n".join(rows) + "\n"


def _write_locale(root: Path, locale: str) -> None:
    path = root / "activities" / "enciclopedia_greia" / "locales" / f"{locale}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "locale": locale,
                "direction": "ltr",
                "strings": {"keep.me": f"value-{locale}"},
                "audio": {},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


class VoiceLedgerAuthoringTests(unittest.TestCase):
    def test_full_v01_render_contains_exact_expected_row_count(self) -> None:
        rendered = render_ledger(LEDGER.read_text(encoding="utf-8"))
        rows = parse_ledger_rows(rendered)
        self.assertEqual(len(rows), EXPECTED_V01_RECORDING_ROWS)
        self.assertIn(("encyclopedia.history.pyramids.engineering", "en"), rows)
        self.assertIn(("encyclopedia.home.welcome", "it"), rows)

    def test_shared_parser_rejects_duplicate_cue_locale(self) -> None:
        row = _row(
            status="REQUESTED",
            cue="encyclopedia.animals.lion.intro",
            locale="it",
            path="encyclopedia/pages/animals/lion/assets/audio/it/intro-tito.ogg",
        )
        with self.assertRaisesRegex(ValueError, "duplicate voice-ledger row"):
            parse_ledger_rows(_ledger(row, row))

    def test_packager_integrates_only_owner_accepted_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            accepted_path = "encyclopedia/pages/animals/lion/assets/audio/it/intro-tito.ogg"
            pending_path = "encyclopedia/pages/animals/lion/assets/audio/en/intro-tito.ogg"
            ledger = _ledger(
                _row(
                    status="OWNER_ACCEPTED",
                    cue="encyclopedia.animals.lion.intro",
                    locale="it",
                    path=accepted_path,
                ),
                _row(
                    status="RECORDED_UNREVIEWED",
                    cue="encyclopedia.animals.lion.intro",
                    locale="en",
                    path=pending_path,
                ),
            )
            ledger_path = root / "encyclopedia" / "VOICE_RECORDING_REQUESTS.md"
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            ledger_path.write_text(ledger, encoding="utf-8")
            _write_locale(root, "it")
            _write_locale(root, "en")

            accepted_source = root / accepted_path
            accepted_source.parent.mkdir(parents=True, exist_ok=True)
            accepted_source.write_bytes(b"OggSaccepted")
            pending_source = root / pending_path
            pending_source.parent.mkdir(parents=True, exist_ok=True)
            pending_source.write_bytes(b"OggSpending")

            report = integrate_accepted_assets(root)
            self.assertEqual(report.accepted_rows, 1)

            target = (
                root
                / "activities"
                / "enciclopedia_greia"
                / "assets"
                / "audio"
                / "it"
                / "animals"
                / "lion"
                / "intro-tito.ogg"
            )
            self.assertEqual(target.read_bytes(), b"OggSaccepted")
            self.assertFalse(
                (
                    root
                    / "activities"
                    / "enciclopedia_greia"
                    / "assets"
                    / "audio"
                    / "en"
                    / "animals"
                    / "lion"
                    / "intro-tito.ogg"
                ).exists()
            )

            it_bundle = json.loads(
                (root / "activities/enciclopedia_greia/locales/it.json").read_text(
                    encoding="utf-8"
                )
            )
            en_bundle = json.loads(
                (root / "activities/enciclopedia_greia/locales/en.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(it_bundle["strings"], {"keep.me": "value-it"})
            self.assertEqual(
                it_bundle["audio"],
                {
                    "encyclopedia.animals.lion.intro": (
                        "assets/audio/it/animals/lion/intro-tito.ogg"
                    )
                },
            )
            self.assertEqual(en_bundle["audio"], {})

            check = integrate_accepted_assets(root, check_only=True)
            self.assertTrue(check.in_sync)

    def test_packager_fails_before_write_when_accepted_source_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_path = root / "encyclopedia" / "VOICE_RECORDING_REQUESTS.md"
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            ledger_path.write_text(
                _ledger(
                    _row(
                        status="OWNER_ACCEPTED",
                        cue="encyclopedia.animals.lion.intro",
                        locale="it",
                        path="encyclopedia/pages/animals/lion/assets/audio/it/intro-tito.ogg",
                    )
                ),
                encoding="utf-8",
            )
            _write_locale(root, "it")
            _write_locale(root, "en")

            with self.assertRaises(FileNotFoundError):
                integrate_accepted_assets(root)
            it_bundle = json.loads(
                (root / "activities/enciclopedia_greia/locales/it.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(it_bundle["audio"], {})

    def test_packager_rejects_non_ogg_owner_accepted_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            relative = "encyclopedia/pages/animals/lion/assets/audio/it/intro-tito.ogg"
            ledger_path = root / "encyclopedia" / "VOICE_RECORDING_REQUESTS.md"
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            ledger_path.write_text(
                _ledger(
                    _row(
                        status="OWNER_ACCEPTED",
                        cue="encyclopedia.animals.lion.intro",
                        locale="it",
                        path=relative,
                    )
                ),
                encoding="utf-8",
            )
            _write_locale(root, "it")
            _write_locale(root, "en")
            source = root / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(b"not-an-ogg")

            with self.assertRaisesRegex(ValueError, "not an OGG container"):
                integrate_accepted_assets(root)

    def test_packager_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            malicious = _ledger(
                _row(
                    status="OWNER_ACCEPTED",
                    cue="encyclopedia.animals.lion.intro",
                    locale="it",
                    path="encyclopedia/pages/../outside/assets/audio/it/intro-tito.ogg",
                )
            )
            with self.assertRaisesRegex(ValueError, "unsafe staging path"):
                plan_accepted_assets(malicious, root)


if __name__ == "__main__":
    unittest.main()
