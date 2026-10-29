#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


MAX_FILE_BYTES = 512 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024
_ALLOWED_ROOTS = frozenset({"src", "styles", "assets"})
_ALLOWED_SUFFIXES = frozenset({".html", ".css", ".js", ".json", ".svg", ".png", ".webp", ".ico"})


class ParentAppStageError(ValueError):
    """Pinned Parent App source does not match the Greia build contract."""


@dataclass(frozen=True, slots=True)
class ExpectedAsset:
    path: str
    sha256: str
    bytes: int


@dataclass(frozen=True, slots=True)
class ParentAppPin:
    repository: str
    revision: str
    runtime_root: str

    @classmethod
    def load(cls, path: Path) -> "ParentAppPin":
        try:
            with path.open("rb") as handle:
                raw = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ParentAppStageError(f"invalid Parent App pin {path}: {exc}") from exc
        try:
            schema_version = int(raw["schema_version"])
            api_version = int(raw["api_version"])
            repository = str(raw["repository"])
            revision = str(raw["revision"])
            runtime_root = str(raw["runtime_root"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ParentAppStageError(f"Parent App pin is missing required fields: {exc}") from exc
        if schema_version != 1 or api_version != 1:
            raise ParentAppStageError("unsupported Parent App pin schema/API version")
        if not repository or len(revision) != 40 or any(ch not in "0123456789abcdef" for ch in revision):
            raise ParentAppStageError("Parent App repository/revision pin is invalid")
        if runtime_root != "/usr/share/greia-parent-app":
            raise ParentAppStageError("Parent App runtime root changed without build-contract review")
        return cls(repository=repository, revision=revision, runtime_root=runtime_root)


@dataclass(frozen=True, slots=True)
class ParentAppManifest:
    repository: str
    revision: str
    assets: tuple[ExpectedAsset, ...]

    @classmethod
    def load(cls, path: Path, pin: ParentAppPin) -> "ParentAppManifest":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ParentAppStageError(f"invalid Parent App manifest {path}: {exc}") from exc
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            raise ParentAppStageError("unsupported Parent App manifest schema")
        if raw.get("repository") != pin.repository or raw.get("revision") != pin.revision:
            raise ParentAppStageError("Parent App manifest does not match repository/revision pin")
        files = raw.get("files")
        if not isinstance(files, dict) or not files:
            raise ParentAppStageError("Parent App manifest has no files")
        assets: list[ExpectedAsset] = []
        total = 0
        for rel, record in sorted(files.items()):
            if not isinstance(rel, str) or not isinstance(record, dict):
                raise ParentAppStageError("Parent App manifest contains malformed file records")
            _validate_relative_asset(rel)
            try:
                digest = str(record["sha256"])
                size = int(record["bytes"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ParentAppStageError(f"invalid Parent App record for {rel}: {exc}") from exc
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ParentAppStageError(f"invalid SHA-256 for {rel}")
            if size < 0 or size > MAX_FILE_BYTES:
                raise ParentAppStageError(f"Parent App asset exceeds per-file bound: {rel}")
            total += size
            if total > MAX_TOTAL_BYTES:
                raise ParentAppStageError("Parent App runtime payload exceeds total size bound")
            assets.append(ExpectedAsset(rel, digest, size))
        if not any(asset.path == "index.html" for asset in assets):
            raise ParentAppStageError("Parent App manifest must include index.html")
        return cls(pin.repository, pin.revision, tuple(assets))


class ParentAppStager:
    """Verify exact pinned static client bytes before copying into a fresh image root."""

    def __init__(self, pin: ParentAppPin, manifest: ParentAppManifest):
        self.pin = pin
        self.manifest = manifest

    def verify_source(self, source: Path) -> None:
        try:
            root = source.resolve(strict=True)
        except FileNotFoundError as exc:
            raise ParentAppStageError(f"Parent App source is missing: {source}") from exc
        if not root.is_dir():
            raise ParentAppStageError(f"Parent App source is not a directory: {source}")
        for asset in self.manifest.assets:
            candidate = root / asset.path
            try:
                if candidate.is_symlink():
                    raise ParentAppStageError(f"Parent App asset must not be a symlink: {asset.path}")
                resolved = candidate.resolve(strict=True)
                resolved.relative_to(root)
                if not resolved.is_file():
                    raise ParentAppStageError(f"Parent App asset is not a regular file: {asset.path}")
                data = resolved.read_bytes()
            except ParentAppStageError:
                raise
            except (FileNotFoundError, OSError, ValueError) as exc:
                raise ParentAppStageError(f"cannot read Parent App asset {asset.path}: {exc}") from exc
            if len(data) != asset.bytes:
                raise ParentAppStageError(f"Parent App asset size mismatch: {asset.path}")
            digest = hashlib.sha256(data).hexdigest()
            if digest != asset.sha256:
                raise ParentAppStageError(f"Parent App asset digest mismatch: {asset.path}")

    def stage(self, source: Path, target: Path) -> None:
        self.verify_source(source)
        if target.exists() or target.is_symlink():
            raise ParentAppStageError(f"Parent App target must not already exist: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.staging")
        if temporary.exists() or temporary.is_symlink():
            raise ParentAppStageError(f"Parent App staging path already exists: {temporary}")
        try:
            temporary.mkdir(mode=0o755)
            root = source.resolve(strict=True)
            for asset in self.manifest.assets:
                destination = temporary / asset.path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((root / asset.path).read_bytes())
                destination.chmod(0o644)
            # The Parent service is unprivileged; do not let the invoking
            # process's umask make the staged tree inaccessible to it.
            temporary.chmod(0o755)
            for directory in temporary.rglob("*"):
                if directory.is_dir():
                    directory.chmod(0o755)
            temporary.replace(target)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise


def _validate_relative_asset(value: str) -> None:
    path = PurePosixPath(value)
    parts = path.parts
    if value.startswith("/") or not parts or any(part in {"", ".", ".."} or part.startswith(".") for part in parts):
        raise ParentAppStageError(f"unsafe Parent App asset path: {value}")
    if value == "index.html":
        return
    if parts[0] not in _ALLOWED_ROOTS:
        raise ParentAppStageError(f"Parent App asset is outside runtime directories: {value}")
    if Path(parts[-1]).suffix.lower() not in _ALLOWED_SUFFIXES:
        raise ParentAppStageError(f"unsupported Parent App asset type: {value}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify and stage the pinned Greia Parent App")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--pin", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pin = ParentAppPin.load(args.pin)
    manifest = ParentAppManifest.load(args.manifest, pin)
    ParentAppStager(pin, manifest).stage(args.source, args.target)
    print(f"Greia Parent App staged: {pin.repository}@{pin.revision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
