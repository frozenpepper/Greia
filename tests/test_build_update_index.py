"""tools/build_update_index.py writes the public update channel index."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_update_index", REPO / "tools" / "build_update_index.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def fake_release(root: Path, version: str) -> Path:
    release = root / f"greia-{version}"
    (release / "updates").mkdir(parents=True)
    (release / "updates" / "acer-aspire-one-i386-ab.greiaupdate").write_bytes(b"bundle-" + version.encode())
    (release / "release-report.json").write_text(json.dumps({
        "status": "complete", "version": version, "release_id": f"greia-{version}",
        "profiles": [{"profile_id": "acer-aspire-one-i386-ab", "platform_family": "legacy-x86", "architecture": "i386", "board": "acer"}],
    }))
    return release


class BuildUpdateIndexTests(unittest.TestCase):
    def test_creates_and_merges_releases(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            index = tmp / "site" / "greia-updates.json"
            notes = tmp / "notes.txt"
            notes.write_text("Faster Parent app.")
            for version in ("0.14.0", "0.15.0"):
                tool.main(["--release", str(fake_release(tmp, version)), "--base-url", f"https://x.test/u/{version}/",
                           "--index", str(index), "--notes-en", str(notes)])
            data = json.loads(index.read_text())
        self.assertEqual(data["schema"], "greia-updates/1")
        stable = data["greia_os"]["channels"]["stable"]
        self.assertEqual([entry["version"] for entry in stable], ["0.15.0", "0.14.0"])
        entry = stable[0]
        self.assertEqual(entry["profiles"], ["acer-aspire-one-i386-ab"])
        self.assertEqual(entry["update"]["url"], "https://x.test/u/0.15.0/acer-aspire-one-i386-ab.greiaupdate")
        self.assertEqual(len(entry["update"]["sha256"]), 64)
        self.assertEqual(entry["notes"], {"en": "Faster Parent app."})

    def test_rerun_replaces_same_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            index = tmp / "greia-updates.json"
            release = fake_release(tmp, "0.14.0")
            for _ in range(2):
                tool.main(["--release", str(release), "--base-url", "https://x.test/u", "--index", str(index)])
            data = json.loads(index.read_text())
        self.assertEqual(len(data["greia_os"]["channels"]["stable"]), 1)

    def test_four_languages_retention_and_other_channel_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = root / "index.json"
            original = tool.empty_index()
            original["parents_app"] = {"version": "2.0"}
            original["greia_os"]["channels"]["dev"] = [{"version": "dev-sentinel"}]
            tool.write_index(index, original)
            note_args = []
            for locale in ("en", "it", "es", "fr"):
                note = root / f"{locale}.txt"
                note.write_text(f"Notes {locale}")
                note_args.extend([f"--notes-{locale}", str(note)])
            for version in ("1.0.0", "1.0.1", "1.0.2", "1.0.3"):
                tool.main(["--release", str(fake_release(root, version)),
                           "--base-url", "https://x.test/u", "--index", str(index), *note_args])
            data = json.loads(index.read_text())
            stable = data["greia_os"]["channels"]["stable"]
            self.assertEqual([row["version"] for row in stable], ["1.0.3", "1.0.2", "1.0.1"])
            self.assertEqual(set(stable[0]["notes"]), {"en", "it", "es", "fr"})
            self.assertEqual(data["parents_app"], {"version": "2.0"})
            self.assertEqual(data["greia_os"]["channels"]["dev"], [{"version": "dev-sentinel"}])
            self.assertTrue((root / "greia-1.0.0/updates/acer-aspire-one-i386-ab.greiaupdate").is_file())

    def test_failed_publication_preserves_previous_index_and_cleans_temporary(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / "index.json"
            index.write_bytes(b"previous complete index")
            with patch.object(tool.os, "replace", side_effect=OSError("interrupted")):
                with self.assertRaises(OSError):
                    tool.write_index(index, tool.empty_index())
            self.assertEqual(index.read_bytes(), b"previous complete index")
            self.assertEqual(list(Path(tmp).iterdir()), [index])

    def test_oversized_index_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / "index.json"
            index.write_bytes(b"previous")
            with self.assertRaises(SystemExit):
                tool.write_index(index, {"oversized": "x" * tool.MAX_INDEX_BYTES})
            self.assertEqual(index.read_bytes(), b"previous")


if __name__ == "__main__":
    unittest.main()
