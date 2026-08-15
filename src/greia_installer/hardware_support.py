from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


_PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MAX_POOL_PACKAGES = 1024
_MAX_POOL_BYTES = 2 * 1024 * 1024 * 1024


class HardwareSupportPoolError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class HardwareSupportPoolPackage:
    package: str
    version: str
    architecture: str
    filename: str
    size: int
    sha256: str
    candidate: bool

    def __post_init__(self) -> None:
        if not _PACKAGE_RE.fullmatch(self.package):
            raise HardwareSupportPoolError("hardware-support package name is invalid")
        path = Path(self.filename)
        if path.is_absolute() or ".." in path.parts or path.parts[:1] != ("pool",):
            raise HardwareSupportPoolError("hardware-support package filename is unsafe")
        if path.name != self.filename.split("/")[-1] or not path.name.endswith(".deb"):
            raise HardwareSupportPoolError("hardware-support package filename is invalid")
        if not self.version or len(self.version) > 256:
            raise HardwareSupportPoolError("hardware-support package version is invalid")
        if not self.architecture or len(self.architecture) > 32:
            raise HardwareSupportPoolError("hardware-support package architecture is invalid")
        if not 0 <= self.size <= _MAX_POOL_BYTES:
            raise HardwareSupportPoolError("hardware-support package size is invalid")
        if not _SHA256_RE.fullmatch(self.sha256):
            raise HardwareSupportPoolError("hardware-support package digest is invalid")


@dataclass(frozen=True, slots=True)
class VerifiedHardwareSupportPool:
    root: Path
    suite: str
    architecture: str
    packages: tuple[HardwareSupportPoolPackage, ...]
    provided_candidates: frozenset[str]
    total_bytes: int

    @classmethod
    def load(
        cls,
        root: Path,
        *,
        expected_suite: str | None = None,
        expected_architecture: str | None = None,
    ) -> "VerifiedHardwareSupportPool":
        root = root.resolve()
        manifest_path = root / "manifest.json"
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HardwareSupportPoolError("hardware-support manifest is unreadable") from exc
        if raw.get("schema_version") != 1:
            raise HardwareSupportPoolError("unsupported hardware-support manifest schema")
        suite = raw.get("suite")
        architecture = raw.get("architecture")
        if not isinstance(suite, str) or not suite or len(suite) > 64:
            raise HardwareSupportPoolError("hardware-support suite is invalid")
        if not isinstance(architecture, str) or not architecture or len(architecture) > 32:
            raise HardwareSupportPoolError("hardware-support architecture is invalid")
        if expected_suite is not None and suite != expected_suite:
            raise HardwareSupportPoolError("hardware-support suite does not match installer")
        if expected_architecture is not None and architecture != expected_architecture:
            raise HardwareSupportPoolError("hardware-support architecture does not match installer")

        entries = raw.get("packages")
        if not isinstance(entries, list) or len(entries) > _MAX_POOL_PACKAGES:
            raise HardwareSupportPoolError("hardware-support package list is invalid")
        packages: list[HardwareSupportPoolPackage] = []
        seen_identity: set[tuple[str, str]] = set()
        expected_paths: set[Path] = set()
        total = 0
        for entry in entries:
            if not isinstance(entry, dict):
                raise HardwareSupportPoolError("hardware-support package entry is invalid")
            try:
                package = HardwareSupportPoolPackage(
                    package=entry["package"],
                    version=entry["version"],
                    architecture=entry["architecture"],
                    filename=entry["filename"],
                    size=entry["size"],
                    sha256=entry["sha256"],
                    candidate=entry["candidate"],
                )
            except (KeyError, TypeError) as exc:
                raise HardwareSupportPoolError("hardware-support package entry is incomplete") from exc
            if not isinstance(package.candidate, bool):
                raise HardwareSupportPoolError("hardware-support candidate flag is invalid")
            identity = (package.package, package.architecture)
            if identity in seen_identity:
                raise HardwareSupportPoolError("hardware-support package identity is duplicated")
            seen_identity.add(identity)
            path = root / package.filename
            if path.is_symlink() or not path.is_file():
                raise HardwareSupportPoolError(f"hardware-support package is missing: {package.package}")
            resolved = path.resolve()
            if root not in resolved.parents:
                raise HardwareSupportPoolError("hardware-support package escaped pool root")
            if path.stat().st_size != package.size:
                raise HardwareSupportPoolError(f"hardware-support package size changed: {package.package}")
            if _sha256(path) != package.sha256:
                raise HardwareSupportPoolError(f"hardware-support package digest changed: {package.package}")
            expected_paths.add(resolved)
            packages.append(package)
            total += package.size
            if total > _MAX_POOL_BYTES:
                raise HardwareSupportPoolError("hardware-support pool exceeds runtime byte bound")

        actual_paths = {
            path.resolve()
            for path in (root / "pool").glob("*.deb")
            if path.is_file() and not path.is_symlink()
        }
        if actual_paths != expected_paths:
            raise HardwareSupportPoolError("hardware-support pool contains unmanifested package payloads")
        for index_name in ("Packages", "Packages.gz"):
            index = root / index_name
            if index.is_symlink() or not index.is_file():
                raise HardwareSupportPoolError(f"hardware-support repository index is missing: {index_name}")

        candidates = raw.get("provided_candidate_packages")
        if not isinstance(candidates, list) or not all(
            isinstance(item, str) and _PACKAGE_RE.fullmatch(item) for item in candidates
        ):
            raise HardwareSupportPoolError("hardware-support candidate list is invalid")
        provided = frozenset(candidates)
        manifest_candidates = {package.package for package in packages if package.candidate}
        if not provided <= manifest_candidates:
            raise HardwareSupportPoolError("hardware-support candidate list references non-candidate payloads")
        manifest_total = raw.get("total_bytes")
        if not isinstance(manifest_total, int) or manifest_total != total:
            raise HardwareSupportPoolError("hardware-support pool total size does not match manifest")

        return cls(root, suite, architecture, tuple(packages), provided, total)

    def require_candidates(self, packages: Iterable[str]) -> tuple[str, ...]:
        requested = tuple(dict.fromkeys(packages))
        for package in requested:
            if not _PACKAGE_RE.fullmatch(package):
                raise HardwareSupportPoolError(f"invalid requested hardware package: {package!r}")
            if package not in self.provided_candidates:
                raise HardwareSupportPoolError(
                    f"hardware-support package is not available in the verified pool: {package}"
                )
        return requested

    @property
    def apt_source_line(self) -> str:
        return "deb [trusted=yes] file:/run/greia-hardware-support ./"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
