"""Fail-closed integrity check for the installed Parent browser client.

``runtime/parent-app-client.toml`` pins ``repository``
(``frozenpepper/Greia:parent-app``, the in-repo browser client source) and
``revision``: the 40-hex Git tree id of the committed ``parent-app/`` directory
at pin time. ``runtime/parent-app-client.manifest.json`` repeats both and lists
every shipped runtime file with its size and SHA-256. The service checks that
pin and manifest agree and that the installed files match the manifest exactly.
The tree id is an identity label that is not re-derived on the device, because
images carry no Git objects. ``tools/update_parent_client_pin.py`` produces the
pin, manifest and image overlay from one committed tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


_ALLOWED_ROOTS = frozenset({"src", "styles", "assets"})


class ParentClientIntegrityError(ValueError):
    """Installed Parent client bytes do not match the reviewed Greia runtime."""


@dataclass(frozen=True, slots=True)
class ExpectedRuntimeFile:
    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class ParentClientRuntimeContract:
    repository: str
    revision: str
    files: tuple[ExpectedRuntimeFile, ...]

    @classmethod
    def load(cls, manifest_path: Path, pin_path: Path) -> "ParentClientRuntimeContract":
        try:
            with pin_path.open("rb") as handle:
                pin = tomllib.load(handle)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, json.JSONDecodeError) as exc:
            raise ParentClientIntegrityError(f"cannot load Parent client integrity contract: {exc}") from exc

        repository = pin.get("repository")
        revision = pin.get("revision")
        if not isinstance(repository, str) or not repository:
            raise ParentClientIntegrityError("Parent client pin has no repository")
        if not isinstance(revision, str) or len(revision) != 40:
            raise ParentClientIntegrityError("Parent client pin has an invalid revision")
        if manifest.get("schema_version") != 1:
            raise ParentClientIntegrityError("unsupported Parent client manifest schema")
        if manifest.get("repository") != repository or manifest.get("revision") != revision:
            raise ParentClientIntegrityError("Parent client manifest does not match the configured pin")

        raw_files = manifest.get("files")
        if not isinstance(raw_files, dict) or not raw_files:
            raise ParentClientIntegrityError("Parent client manifest has no runtime files")

        expected: list[ExpectedRuntimeFile] = []
        for relative, record in sorted(raw_files.items()):
            if not isinstance(relative, str) or not isinstance(record, dict):
                raise ParentClientIntegrityError("Parent client manifest contains malformed records")
            _validate_runtime_path(relative)
            if relative.startswith("src/demo"):
                raise ParentClientIntegrityError("production Parent client manifest contains demo runtime code")
            try:
                size = int(record["bytes"])
                digest = str(record["sha256"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ParentClientIntegrityError(f"invalid Parent client record for {relative}") from exc
            if size < 0:
                raise ParentClientIntegrityError(f"invalid Parent client size for {relative}")
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ParentClientIntegrityError(f"invalid Parent client digest for {relative}")
            expected.append(ExpectedRuntimeFile(relative, size, digest))

        if not any(item.path == "index.html" for item in expected):
            raise ParentClientIntegrityError("Parent client manifest does not contain index.html")
        return cls(repository, revision, tuple(expected))

    def verify(self, root: Path) -> None:
        if root.is_symlink():
            raise ParentClientIntegrityError("Parent client root must not be a symlink")
        try:
            resolved_root = root.resolve(strict=True)
        except FileNotFoundError as exc:
            raise ParentClientIntegrityError(f"Parent client root is missing: {root}") from exc
        if not resolved_root.is_dir():
            raise ParentClientIntegrityError(f"Parent client root is not a directory: {root}")

        expected_paths = {item.path for item in self.files}
        actual_paths: set[str] = set()
        for candidate in resolved_root.rglob("*"):
            if candidate.is_symlink():
                raise ParentClientIntegrityError(
                    f"Parent client runtime contains a symlink: {candidate.relative_to(resolved_root)}"
                )
            if candidate.is_file():
                actual_paths.add(candidate.relative_to(resolved_root).as_posix())

        missing = sorted(expected_paths - actual_paths)
        unexpected = sorted(actual_paths - expected_paths)
        if missing:
            raise ParentClientIntegrityError(f"Parent client runtime is missing files: {', '.join(missing)}")
        if unexpected:
            raise ParentClientIntegrityError(
                f"Parent client runtime contains unexpected files: {', '.join(unexpected)}"
            )

        for item in self.files:
            candidate = resolved_root / item.path
            try:
                data = candidate.read_bytes()
            except OSError as exc:
                raise ParentClientIntegrityError(f"cannot read Parent client runtime file: {item.path}") from exc
            if len(data) != item.bytes:
                raise ParentClientIntegrityError(f"Parent client size mismatch: {item.path}")
            if hashlib.sha256(data).hexdigest() != item.sha256:
                raise ParentClientIntegrityError(f"Parent client digest mismatch: {item.path}")


def _validate_runtime_path(value: str) -> None:
    path = PurePosixPath(value)
    parts = path.parts
    if value.startswith("/") or not parts or any(
        part in {"", ".", ".."} or part.startswith(".") for part in parts
    ):
        raise ParentClientIntegrityError(f"unsafe Parent client runtime path: {value}")
    if value == "index.html":
        return
    if parts[0] not in _ALLOWED_ROOTS:
        raise ParentClientIntegrityError(f"Parent client file is outside runtime roots: {value}")


def verify_parent_client_runtime(root: Path, manifest_path: Path, pin_path: Path) -> str:
    contract = ParentClientRuntimeContract.load(manifest_path, pin_path)
    contract.verify(root)
    return contract.revision


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the installed Greia Parent client")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--pin", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        revision = verify_parent_client_runtime(args.root, args.manifest, args.pin)
    except ParentClientIntegrityError as exc:
        raise SystemExit(f"Greia Parent client integrity failure: {exc}") from exc
    print(f"Greia Parent client integrity OK: {revision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
