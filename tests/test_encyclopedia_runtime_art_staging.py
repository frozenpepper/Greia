from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "import_encyclopedia_runtime_art_staging.py"
SPEC = importlib.util.spec_from_file_location("encyclopedia_runtime_art_staging", TOOL)
assert SPEC is not None and SPEC.loader is not None
staging = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(staging)


def _png_bytes(seed: str) -> bytes:
    return (
        staging.PNG_SIGNATURE
        + b"\x00\x00\x00\rIHDR"
        + struct.pack(">II", *staging.REFERENCE_SIZE)
        + bytes((8, staging.PNG_COLOR_TYPE_RGB))
        + seed.encode("ascii")
    )


def _write_runtime(root: Path) -> dict[str, bytes]:
    runtime = root / staging.RUNTIME_RELATIVE
    runtime.mkdir(parents=True, exist_ok=True)
    written: dict[str, bytes] = {}
    for name in (
        "home_discovery_book.png",
        "animals_field_table.png",
        "lion_savanna.png",
        "gears_workbench.png",
        *staging.PRESERVED_NAMES,
    ):
        data = _png_bytes(f"old-{name}")
        (runtime / name).write_bytes(data)
        written[name] = data
    return written


def _write_staging_zip(
    path: Path,
    *,
    corrupt_sha: str | None = None,
    legacy_manifest: bool = False,
    unexpected_png: bool = False,
) -> dict[str, bytes]:
    payloads = {
        name: _png_bytes(f"new-{index}-{name}")
        for index, name in enumerate(staging.STAGED_NAMES)
    }
    records = []
    for name in staging.STAGED_NAMES:
        data = payloads[name]
        digest = hashlib.sha256(data).hexdigest()
        if corrupt_sha == name:
            digest = "0" * 64
        records.append(
            {
                "name": name,
                "bytes": len(data),
                "width": staging.REFERENCE_SIZE[0],
                "height": staging.REFERENCE_SIZE[1],
                "mode": "RGB",
                "sha256": digest,
            }
        )
    manifest = {
        "schema_version": 3,
        "evidence_class": "LOCAL_STAGING_NOT_ACCEPTANCE",
        "files": records,
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "bundle/runtime-manifest.json",
            json.dumps(manifest, sort_keys=True),
        )
        if legacy_manifest:
            archive.writestr("bundle/manifest.json", json.dumps(manifest))
        for name, data in payloads.items():
            archive.writestr(f"bundle/runtime/{name}", data)
        if unexpected_png:
            archive.writestr("bundle/runtime/unexpected.png", _png_bytes("unexpected"))
    return payloads


class EncyclopediaRuntimeArtStagingTests(unittest.TestCase):
    def test_check_only_validates_without_mutating_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before = _write_runtime(root)
            zip_path = root / "staging.zip"
            payloads = _write_staging_zip(zip_path)

            hashes = staging.import_staging(zip_path, root=root, check_only=True)

            self.assertEqual(set(hashes), set(staging.STAGED_NAMES))
            self.assertEqual(
                hashes,
                {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()},
            )
            runtime = root / staging.RUNTIME_RELATIVE
            self.assertEqual(
                {path.name for path in runtime.glob("*.png")}, set(before)
            )
            for name, data in before.items():
                self.assertEqual((runtime / name).read_bytes(), data)

    def test_import_replaces_exact_nine_and_preserves_two(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before = _write_runtime(root)
            preserved = {name: before[name] for name in staging.PRESERVED_NAMES}
            zip_path = root / "staging.zip"
            payloads = _write_staging_zip(zip_path)

            hashes = staging.import_staging(zip_path, root=root)

            runtime = root / staging.RUNTIME_RELATIVE
            self.assertEqual(
                {path.name for path in runtime.glob("*.png")}, set(staging.ALL_NAMES)
            )
            for name, data in payloads.items():
                self.assertEqual((runtime / name).read_bytes(), data)
                self.assertEqual(hashes[name], hashlib.sha256(data).hexdigest())
            for name, data in preserved.items():
                self.assertEqual((runtime / name).read_bytes(), data)

    def test_rejects_stale_manifest_hash_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before = _write_runtime(root)
            zip_path = root / "staging.zip"
            _write_staging_zip(
                zip_path,
                corrupt_sha="earth_gallery_landscape.png",
            )

            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                staging.import_staging(zip_path, root=root)

            runtime = root / staging.RUNTIME_RELATIVE
            for name, data in before.items():
                self.assertEqual((runtime / name).read_bytes(), data)

    def test_rejects_legacy_duplicate_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_runtime(root)
            zip_path = root / "staging.zip"
            _write_staging_zip(zip_path, legacy_manifest=True)

            with self.assertRaisesRegex(ValueError, "exactly one authoritative"):
                staging.import_staging(zip_path, root=root, check_only=True)

    def test_rejects_unexpected_runtime_png(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_runtime(root)
            zip_path = root / "staging.zip"
            _write_staging_zip(zip_path, unexpected_png=True)

            with self.assertRaisesRegex(ValueError, "inventory mismatch"):
                staging.import_staging(zip_path, root=root, check_only=True)

    def test_rejects_missing_preserved_runtime_art(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_runtime(root)
            (root / staging.RUNTIME_RELATIVE / "saturn_observatory.png").unlink()
            zip_path = root / "staging.zip"
            _write_staging_zip(zip_path)

            with self.assertRaisesRegex(FileNotFoundError, "preserved runtime PNG"):
                staging.import_staging(zip_path, root=root, check_only=True)


if __name__ == "__main__":
    unittest.main()
