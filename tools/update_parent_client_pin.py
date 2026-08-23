#!/usr/bin/env python3
"""Regenerate Greia's exact Parent HTML client pin from a local reviewed checkout.

This tool never fetches moving repository state. The caller supplies a local
Parent checkout and the exact commit SHA that was reviewed/tested. The existing
Greia runtime manifest defines the bounded runtime file set; every listed file
must exist and is re-hashed from exact bytes before the pin is rewritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


REVISION_LINE = re.compile(r'^revision = "[0-9a-f]{40}"$', re.MULTILINE)


class PinError(RuntimeError):
    pass


def _git(parent_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(parent_root), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PinError(f"could not inspect Parent checkout: {exc}") from exc
    return completed.stdout.strip()


def _validate_parent_checkout(parent_root: Path, revision: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise PinError("revision must be an exact 40-character lowercase Git SHA")
    head = _git(parent_root, "rev-parse", "HEAD")
    if head != revision:
        raise PinError(f"Parent checkout HEAD is {head}, expected {revision}")
    dirty = _git(parent_root, "status", "--porcelain")
    if dirty:
        raise PinError("Parent checkout is dirty; commit/review changes before pinning")


def _load_manifest(path: Path) -> dict[str, object]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PinError(f"invalid existing Parent manifest: {exc}") from exc
    files = document.get("files")
    if document.get("schema_version") != 1 or not isinstance(files, dict) or not files:
        raise PinError("Parent manifest must be schema 1 with a non-empty files object")
    for relative in files:
        if not isinstance(relative, str) or relative.startswith("/") or ".." in Path(relative).parts:
            raise PinError(f"unsafe runtime manifest path: {relative!r}")
    return document


def _hash_runtime_files(parent_root: Path, relative_paths: list[str]) -> dict[str, dict[str, object]]:
    output: dict[str, dict[str, object]] = {}
    for relative in relative_paths:
        path = (parent_root / relative).resolve()
        try:
            path.relative_to(parent_root.resolve())
        except ValueError as exc:
            raise PinError(f"runtime file escapes Parent checkout: {relative}") from exc
        if not path.is_file():
            raise PinError(f"required Parent runtime file is missing: {relative}")
        data = path.read_bytes()
        output[relative] = {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    return output


def update_pin(greia_root: Path, parent_root: Path, revision: str) -> tuple[Path, Path]:
    greia_root = greia_root.resolve()
    parent_root = parent_root.resolve()
    _validate_parent_checkout(parent_root, revision)

    config_path = greia_root / "runtime" / "parent-app-client.toml"
    manifest_path = greia_root / "runtime" / "parent-app-client.manifest.json"
    manifest = _load_manifest(manifest_path)
    files = manifest["files"]
    assert isinstance(files, dict)
    relative_paths = list(files)

    hashed = _hash_runtime_files(parent_root, relative_paths)
    rewritten_manifest = {
        "files": hashed,
        "repository": manifest.get("repository", "frozenpepper/Greia-Parent-App-Html"),
        "revision": revision,
        "schema_version": 1,
    }

    try:
        config = config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PinError(f"could not read Parent pin config: {exc}") from exc
    matches = REVISION_LINE.findall(config)
    if len(matches) != 1:
        raise PinError("Parent pin config must contain exactly one exact revision line")
    rewritten_config = REVISION_LINE.sub(f'revision = "{revision}"', config, count=1)

    # Build both complete outputs before touching either authority file.
    manifest_text = json.dumps(rewritten_manifest, indent=2, ensure_ascii=False) + "\n"
    config_tmp = config_path.with_name(f".{config_path.name}.tmp")
    manifest_tmp = manifest_path.with_name(f".{manifest_path.name}.tmp")
    try:
        config_tmp.write_text(rewritten_config, encoding="utf-8")
        manifest_tmp.write_text(manifest_text, encoding="utf-8")
        config_tmp.replace(config_path)
        manifest_tmp.replace(manifest_path)
    finally:
        config_tmp.unlink(missing_ok=True)
        manifest_tmp.unlink(missing_ok=True)
    return config_path, manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--greia-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Greia checkout root (default: inferred from this tool)",
    )
    parser.add_argument("--parent-root", type=Path, required=True, help="reviewed Parent HTML checkout")
    parser.add_argument("--revision", required=True, help="exact reviewed Parent commit SHA")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config, manifest = update_pin(args.greia_root, args.parent_root, args.revision)
    except PinError as exc:
        raise SystemExit(f"parent pin update refused: {exc}")
    print(f"updated {config}")
    print(f"updated {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
