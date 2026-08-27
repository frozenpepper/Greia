from __future__ import annotations

import ast
import json
from pathlib import Path
import tempfile
import unittest

from encyclopedia.export_voice_batch import batch_requests, render_jsonl
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
ACTIVITY_PAGES = ROOT / "activities" / "enciclopedia_greia" / "pages"

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


def _write_locale(
    root: Path,
    locale: str,
    *,
    audio: dict[str, object] | None = None,
) -> None:
    path = root / "activities" / "enciclopedia_greia" / "locales" / f"{locale}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "locale": locale,
                "direction": "ltr",
                "strings": {"keep.me": f"value-{locale}"},
                "audio": audio or {},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _runtime_narration_cues() -> set[str]:
    cues: set[str] = set()
    for path in ACTIVITY_PAGES.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        cues.update(
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.startswith("encyclopedia.")
        )
    return cues


class VoiceLedgerAuthoringTests(unittest.TestCase):
    def test_full_v01_render_contains_exact_expected_row_count(self) -> None:
        rendered = render_ledger(LEDGER.read_text(encoding="utf-8"))
        rows = parse_ledger_rows(rendered)
        self.assertEqual(len(rows), EXPECTED_V01_RECORDING_ROWS)
        self.assertIn(("encyclopedia.history.pyramids.engineering", "en"), rows)
        self.assertIn(("encyclopedia.home.welcome", "it"), rows)

    def test_runtime_narration_cues_match_full_synchronized_ledger(self) -> None:
        rendered = render_ledger(LEDGER.read_text(encoding="utf-8"))
        ledger_cues = {row.cue_id for row in parse_ledger_rows(rendered).values()}
        self.assertEqual(_runtime_narration_cues(), ledger_cues)

    def test_full_synchronized_requested_rows_translate_to_voice_engine_contract(self) -> None:
        rendered = render_ledger(LEDGER.read_text(encoding="utf-8"))
        rows = parse_ledger_rows(rendered)
        requests = batch_requests(rendered, ROOT, reject_existing=False)
        expected = [row for row in rows.values() if row.status == "REQUESTED"]

        self.assertEqual(len(requests), len(expected))
        self.assertEqual(len({str(request["output"]) for request in requests}), len(requests))
        for request in requests:
            with self.subTest(cue=request["cue_id"], locale=request["locale"]):
                self.assertIn(request["speaker"], {"leo", "lilli", "flash", "tito", "momo"})
                self.assertEqual(request["kind"], "character_dialogue")
                self.assertIn(request["locale"], {"it", "en"})
                self.assertTrue(str(request["cue_id"]).startswith("encyclopedia."))
                self.assertTrue(str(request["output"]).endswith(".ogg"))
                self.assertEqual(request["verification"], "auto")
                self.assertEqual(request["max_attempts"], 2)

        parsed_jsonl = [json.loads(line) for line in render_jsonl(requests).splitlines()]
        self.assertEqual(parsed_jsonl, list(requests))

    def test_voice_batch_exports_only_requested_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            requested = "encyclopedia/pages/animals/lion/assets/audio/it/intro-tito.ogg"
            accepted = "encyclopedia/pages/animals/lion/assets/audio/en/intro-tito.ogg"
            requests = batch_requests(
                _ledger(
                    _row(
                        status="REQUESTED",
                        cue="encyclopedia.animals.lion.intro",
                        locale="it",
                        path=requested,
                    ),
                    _row(
                        status="OWNER_ACCEPTED",
                        cue="encyclopedia.animals.lion.intro",
                        locale="en",
                        path=accepted,
                    ),
                ),
                root,
            )
            self.assertEqual(
                requests,
                (
                    {
                        "speaker": "tito",
                        "kind": "character_dialogue",
                        "locale": "it",
                        "text": "Exact approved line.",
                        "cue_id": "encyclopedia.animals.lion.intro",
                        "output": requested,
                        "verification": "auto",
                        "max_attempts": 2,
                    },
                ),
            )

    def test_voice_batch_refuses_to_overwrite_existing_requested_take(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            relative = "encyclopedia/pages/animals/lion/assets/audio/it/intro-tito.ogg"
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"existing review take")
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                batch_requests(
                    _ledger(
                        _row(
                            status="REQUESTED",
                            cue="encyclopedia.animals.lion.intro",
                            locale="it",
                            path=relative,
                        )
                    ),
                    root,
                )

    def test_voice_batch_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "unsafe staging path"):
                batch_requests(
                    _ledger(
                        _row(
                            status="REQUESTED",
                            cue="encyclopedia.animals.lion.intro",
                            locale="it",
                            path="encyclopedia/pages/../outside/assets/audio/it/intro-tito.ogg",
                        )
                    ),
                    Path(tmp),
                )

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
            unrelated_it = {
                "encyclopedia.animals.lion.real_roar": {
                    "path": "assets/sfx/lion-real-roar.ogg"
                }
            }
            _write_locale(root, "it", audio=unrelated_it)
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
                    "encyclopedia.animals.lion.intro": {
                        "path": "assets/audio/it/animals/lion/intro-tito.ogg"
                    },
                    "encyclopedia.animals.lion.real_roar": {
                        "path": "assets/sfx/lion-real-roar.ogg"
                    },
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
