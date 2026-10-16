"""tools/build_update_index.py writes the public update channel index."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
