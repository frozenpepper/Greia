#!/usr/bin/env python3
"""Install reviewed canonical voice assets into a Greia checkout.

The input pack must contain repository-relative ``assets/`` paths. Every file
is checked against the canonical manifest in the target checkout before
anything is published. Existing differing files are never overwritten unless
``--replace`` is explicitly supplied.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
import tomllib

from greia_voice_core.registry import CANONICAL_MANIFEST


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("greia_checkout", type=Path)
    parser.add_argument(
        "--pack-root",
        type=Path,
        required=True,
        help="Extracted asset-pack root containing repository-relative assets/ paths.",
    )
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    return parser


def publish(source: Path, target: Path, replace: bool) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if sha256(target) == sha256(source):
            return
        if not replace:
            raise RuntimeError(f"Refusing to replace differing file: {target}")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", dir=target.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copyfile(source, temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    args = build_parser().parse_args()
    checkout = args.greia_checkout.resolve()
    pack_root = args.pack_root.resolve()
    manifest_path = checkout / CANONICAL_MANIFEST
    if not manifest_path.is_file():
        raise RuntimeError(f"Canonical manifest not found: {manifest_path}")

    with manifest_path.open("rb") as stream:
        manifest = tomllib.load(stream)

    expected: list[tuple[Path, str, int]] = []
    for voice in manifest.get("voice", []):
        if voice.get("production") != "cloned_reference":
            continue
        source_relative = Path(voice["source_master"])
        anchor_relative = (
            CANONICAL_MANIFEST.parent
            / voice["production_anchor"]
        )
        expected.extend(
            [
                (
                    source_relative,
                    voice["source_sha256"],
                    int(voice["source_bytes"]),
                ),
                (
                    anchor_relative,
                    voice["anchor_sha256"],
                    int(voice["anchor_bytes"]),
                ),
            ]
        )

    if len(expected) != 12:
        raise RuntimeError(f"Expected twelve registered files, found {len(expected)}")

    validated: list[tuple[Path, Path]] = []
    for relative, expected_hash, expected_bytes in expected:
        source = pack_root / relative
        if not source.is_file():
            raise RuntimeError(f"Pack file missing: {relative}")
        actual_bytes = source.stat().st_size
        actual_hash = sha256(source)
        if actual_bytes != expected_bytes:
            raise RuntimeError(
                f"Size mismatch for {relative}: "
                f"{actual_bytes} != {expected_bytes}"
            )
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"SHA-256 mismatch for {relative}: "
                f"{actual_hash} != {expected_hash}"
            )
        validated.append((source, checkout / relative))

    if args.check_only:
        print("PASS: all twelve canonical voice files match manifest.toml")
        return 0

    for source, target in validated:
        publish(source, target, args.replace)

    print("PASS: installed six WAV masters and six WAV references")
    print("Review git status and commit the exact binary assets.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
