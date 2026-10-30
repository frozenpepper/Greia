"""tools/build_installer_index.py lists installer images in the public index."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_installer_index", REPO / "tools" / "build_installer_index.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
update_tool = sys.modules["build_update_index"]

NAME = "greia-os-installer-i386-ab-{version}-build-9ba22f764ed1.img"
BASE = "https://example.test/greia/os-images"


def fake_image(root: Path, version: str) -> Path:
    image = root / NAME.format(version=version)
    image.write_bytes(b"image-" + version.encode())
    return image


class BuildInstallerIndexTests(unittest.TestCase):
    def test_reads_version_and_build_from_the_standard_name(self):
        parsed = tool.parse_image_name(NAME.format(version="0.13.1-preview.1"))
        self.assertEqual(parsed["version"], "0.13.1-preview.1")
        self.assertEqual(parsed["build"], "9ba22f764ed1")
        self.assertEqual(parsed["profile"], "i386-ab")
        other = tool.parse_image_name("greia-os-installer-legacy-x86-i686-0.14.0-rc.2-build-0123456789ab.img")
        self.assertEqual((other["profile"], other["version"]), ("legacy-x86-i686", "0.14.0-rc.2"))
        self.assertEqual(tool.parse_image_name("random.img"), {})

    def test_compatibility_symlink_resolves_to_the_versioned_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = fake_image(root, "0.13.1")
            link = root / "greia-os-installer-i386-ab.img"
            link.symlink_to(image.name)
            entry = tool.installer_entry(link, base_url=BASE, target="legacy-x86-i386", status="release",
                                         version=None, build=None, notes={}, published_at="2026-10-30")
            self.assertEqual(entry["version"], "0.13.1")
            self.assertEqual(entry["image"]["file_name"], image.name)

    def test_minimum_media_size(self):
        self.assertEqual(tool.minimum_media_gb(2_273_312_768), 4)
        self.assertEqual(tool.minimum_media_gb(1_000_000_000), 2)
        self.assertEqual(tool.minimum_media_gb(7_000_000_000), 8)

    def test_adds_entry_without_touching_update_channels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = root / "greia-updates.json"
            original = update_tool.empty_index()
            original["parents_app"] = {"latest": "1.0.0"}
            original["greia_os"]["channels"]["stable"] = [{"version": "0.12.0"}]
            index.write_text(json.dumps(original))
            image = fake_image(root, "0.13.1-preview.1")
            self.assertEqual(tool.main(["--image", str(image), "--base-url", BASE + "/", "--index", str(index)]), 0)
            data = json.loads(index.read_text())
            self.assertEqual(data["parents_app"], {"latest": "1.0.0"})
            self.assertEqual(data["greia_os"]["channels"]["stable"], [{"version": "0.12.0"}])
            [entry] = data["greia_os"]["installers"]
            self.assertEqual(entry["id"], "legacy-x86-i386")
            self.assertEqual(entry["version"], "0.13.1-preview.1")
            self.assertEqual(entry["build"], "9ba22f764ed1")
            self.assertEqual(entry["status"], "technical-preview")
            self.assertEqual(entry["image"]["url"], f"{BASE}/{image.name}")
            self.assertEqual(entry["image"]["size"], image.stat().st_size)
            self.assertEqual(entry["image"]["sha256"], update_tool.sha256_file(image))

    def test_newest_first_replaces_same_version_and_keeps_bounded_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = root / "greia-updates.json"
            for version in ("0.13.0", "0.13.1", "0.14.0", "0.14.0", "0.15.0"):
                tool.main(["--image", str(fake_image(root, version)), "--base-url", BASE,
                           "--index", str(index), "--keep", "3"])
            versions = [item["version"] for item in json.loads(index.read_text())["greia_os"]["installers"]]
            self.assertEqual(versions, ["0.15.0", "0.14.0", "0.13.1"])

    def test_update_index_builder_preserves_installers(self):
        index = update_tool.empty_index()
        index["greia_os"]["installers"] = [{"id": "legacy-x86-i386", "version": "0.13.1"}]
        update_tool.merge(index, "stable", [])
        self.assertEqual(index["greia_os"]["installers"][0]["version"], "0.13.1")

    def test_rejects_plain_http_and_unreadable_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = fake_image(root, "0.13.1")
            with self.assertRaises(SystemExit):
                tool.main(["--image", str(image), "--base-url", "http://x.test", "--index", str(root / "i.json")])
            odd = root / "odd.img"
            odd.write_bytes(b"x")
            with self.assertRaisesRegex(SystemExit, "pass --version"):
                tool.main(["--image", str(odd), "--base-url", BASE, "--index", str(root / "i.json")])


if __name__ == "__main__":
    unittest.main()
