#!/usr/bin/env python3
"""Validate and import a reviewed Encyclopedia runtime-art staging ZIP.

Maintainer-only recovery helper for the E3 visual gate. It does not generate art,
change source SVGs, or substitute for ``build_encyclopedia_visual_assets.py
--check``. The importer accepts exactly the nine changed/new E2+E3 renditions,
preserves the accepted Saturn/Pyramids runtime files, and leaves the runtime
directory with the exact eleven-image Encyclopedia pack.

A staging ZIP is recoverability/source-review material only. After import, the
normal source build check, focused tests, repository verification, commit/push,
and exact-SHA Greia Simulator review are still mandatory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import struct
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_RELATIVE = Path("activities/enciclopedia_greia/assets/runtime")
REFERENCE_SIZE = (1024, 600)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_COLOR_TYPE_RGB = 2

STAGED_NAMES = (
    "home_discovery_book.png",
    "animals_field_table.png",
    "lion_savanna.png",
    "gears_workbench.png",
    "space_gallery_observatory.png",
    "earth_gallery_landscape.png",
    "body_gallery_discovery_room.png",
    "machines_gallery_workbench.png",
    "history_gallery_time_trail.png",
)
PRESERVED_NAMES = (
    "saturn_observatory.png",
    "pyramids_diorama.png",
)
ALL_NAMES = STAGED_NAMES + PRESERVED_NAMES


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_png_bytes(data: bytes, *, label: str) -> None:
    if len(data) < 26 or not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"invalid PNG rendition: {label}")
    width, height = struct.unpack(">II", data[16:24])
    if (width, height) != REFERENCE_SIZE:
        raise ValueError(
            f"wrong rendition size for {label}: {width}x{height}; "
            f"expected {REFERENCE_SIZE[0]}x{REFERENCE_SIZE[1]}"
        )
    if data[25] != PNG_COLOR_TYPE_RGB:
        raise ValueError(
            f"Encyclopedia scene must be opaque RGB: {label} "
            f"PNG color_type={data[25]}"
        )


def _safe_member(info: zipfile.ZipInfo) -> PurePosixPath:
    path = PurePosixPath(info.filename)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe staging member path: {info.filename}")
    mode = info.external_attr >> 16
    if mode and stat.S_ISLNK(mode):
        raise ValueError(f"symlink staging member is forbidden: {info.filename}")
    return path


def _read_staging(zip_path: Path) -> tuple[dict[str, bytes], dict[str, object]]:
    if not zip_path.is_file():
        raise FileNotFoundError(zip_path)

    with zipfile.ZipFile(zip_path) as archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        paths = [(info, _safe_member(info)) for info in infos]

        manifest_infos = [
            info
            for info, path in paths
            if path.name in {"runtime-manifest.json", "manifest.json"}
        ]
        if (
            len(manifest_infos) != 1
            or PurePosixPath(manifest_infos[0].filename).name != "runtime-manifest.json"
        ):
            raise ValueError(
                "staging ZIP must contain exactly one authoritative runtime-manifest.json "
                "and no legacy manifest.json"
            )
        try:
            manifest = json.loads(archive.read(manifest_infos[0]).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid runtime staging manifest") from exc
        if not isinstance(manifest, dict):
            raise ValueError("runtime staging manifest must be a JSON object")

        png_infos: dict[str, zipfile.ZipInfo] = {}
        for info, path in paths:
            if path.suffix.lower() != ".png":
                continue
            if len(path.parts) < 2 or path.parts[-2] != "runtime":
                raise ValueError(f"PNG outside staging runtime directory: {info.filename}")
            name = path.name
            if name in png_infos:
                raise ValueError(f"duplicate staged PNG basename: {name}")
            png_infos[name] = info

        expected = set(STAGED_NAMES)
        present = set(png_infos)
        if present != expected:
            missing = sorted(expected - present)
            unexpected = sorted(present - expected)
            raise ValueError(
                f"staging PNG inventory mismatch: missing={missing}, unexpected={unexpected}"
            )

        records = manifest.get("files")
        if not isinstance(records, list):
            raise ValueError("runtime staging manifest files must be a list")
        record_map: dict[str, dict[str, object]] = {}
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get("name"), str):
                raise ValueError("invalid runtime staging manifest file record")
            name = str(record["name"])
            if name in record_map:
                raise ValueError(f"duplicate runtime staging manifest record: {name}")
            record_map[name] = record
        if set(record_map) != expected:
            raise ValueError("runtime staging manifest inventory does not match staged PNGs")

        payloads: dict[str, bytes] = {}
        for name in STAGED_NAMES:
            data = archive.read(png_infos[name])
            _validate_png_bytes(data, label=name)
            record = record_map[name]
            expected_sha = record.get("sha256")
            if expected_sha != _sha256(data):
                raise ValueError(f"staging SHA-256 mismatch for {name}")
            if record.get("bytes") != len(data):
                raise ValueError(f"staging byte-count mismatch for {name}")
            if (record.get("width"), record.get("height")) != REFERENCE_SIZE:
                raise ValueError(f"staging dimension metadata mismatch for {name}")
            if record.get("mode") != "RGB":
                raise ValueError(f"staging mode metadata mismatch for {name}")
            payloads[name] = data

    return payloads, manifest


def _validate_runtime_directory(runtime: Path) -> None:
    if not runtime.is_dir():
        raise FileNotFoundError(runtime)
    present = {path.name for path in runtime.glob("*.png") if path.is_file()}
    unexpected = sorted(present - set(ALL_NAMES))
    if unexpected:
        raise ValueError(f"unexpected Encyclopedia runtime PNGs: {unexpected}")
    for name in PRESERVED_NAMES:
        path = runtime / name
        if not path.is_file():
            raise FileNotFoundError(f"required preserved runtime PNG is missing: {path}")
        _validate_png_bytes(path.read_bytes(), label=name)


def import_staging(
    zip_path: Path,
    *,
    root: Path = ROOT,
    check_only: bool = False,
) -> dict[str, str]:
    payloads, _manifest = _read_staging(zip_path)
    runtime = root / RUNTIME_RELATIVE
    _validate_runtime_directory(runtime)

    hashes = {name: _sha256(payloads[name]) for name in STAGED_NAMES}
    if check_only:
        return hashes

    temp_paths: list[Path] = []
    try:
        for name in STAGED_NAMES:
            descriptor, raw_path = tempfile.mkstemp(
                prefix=f".{name}.", suffix=".tmp", dir=runtime
            )
            temp_path = Path(raw_path)
            temp_paths.append(temp_path)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payloads[name])
                handle.flush()
                os.fsync(handle.fileno())

        for name, temp_path in zip(STAGED_NAMES, temp_paths, strict=True):
            os.replace(temp_path, runtime / name)
        temp_paths.clear()
    finally:
        for temp_path in temp_paths:
            temp_path.unlink(missing_ok=True)

    final_names = {path.name for path in runtime.glob("*.png") if path.is_file()}
    if final_names != set(ALL_NAMES):
        raise RuntimeError(
            f"post-import runtime inventory is not exact 11/11: {sorted(final_names)}"
        )
    for name in ALL_NAMES:
        _validate_png_bytes((runtime / name).read_bytes(), label=name)
    return hashes


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("staging_zip", type=Path, help="reviewed E3 runtime-art staging ZIP")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="validate the staging ZIP and preserved runtime files without writing",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    hashes = import_staging(args.staging_zip, check_only=args.check_only)
    action = "validated" if args.check_only else "imported"
    for name in STAGED_NAMES:
        print(f"{action} {name} sha256={hashes[name]}")
    if not args.check_only:
        print("imported exact Encyclopedia runtime pack: 11 / 11 PNGs")
        print("NEXT: run tools/build_encyclopedia_visual_assets.py --check --group all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
