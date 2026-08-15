from __future__ import annotations

import fnmatch
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
_MAX_INDEX_BYTES = 32 * 1024 * 1024
_MAX_FIRMWARE_PROVIDERS = 65536
_MAX_FIRMWARE_PATH_BYTES = 1024


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
        if not isinstance(self.candidate, bool):
            raise HardwareSupportPoolError("hardware-support candidate flag is invalid")


@dataclass(frozen=True, slots=True)
class VerifiedHardwareSupportPool:
    root: Path
    suite: str
    architecture: str
    packages: tuple[HardwareSupportPoolPackage, ...]
    provided_candidates: frozenset[str]
    provided_firmware: frozenset[str]
    provided_microcode: frozenset[str]
    total_bytes: int
    firmware_providers: tuple[tuple[str, tuple[str, ...]], ...] = ()

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
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise HardwareSupportPoolError("hardware-support manifest is missing or unsafe")
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

        pool_dir = root / "pool"
        if not pool_dir.is_dir() or pool_dir.is_symlink():
            raise HardwareSupportPoolError("hardware-support package directory is invalid")
        pool_entries = tuple(sorted(pool_dir.glob("*.deb")))
        if any(path.is_symlink() or not path.is_file() for path in pool_entries):
            raise HardwareSupportPoolError("hardware-support pool contains a symlinked or invalid package")
        actual_paths = {path.resolve() for path in pool_entries}
        if actual_paths != expected_paths:
            raise HardwareSupportPoolError("hardware-support pool contains unmanifested package payloads")

        cls._verify_repository_indexes(root, raw)

        manifest_candidates = {package.package for package in packages if package.candidate}
        provided = cls._validated_package_set(raw, "provided_candidate_packages")
        firmware = cls._validated_package_set(raw, "provided_firmware_packages")
        microcode = cls._validated_package_set(raw, "provided_microcode_packages")
        providers = cls._validated_firmware_providers(raw, firmware)
        if not firmware.isdisjoint(microcode):
            raise HardwareSupportPoolError("hardware-support firmware/microcode classes overlap")
        if firmware | microcode != provided:
            raise HardwareSupportPoolError("hardware-support candidate classes do not match candidate set")
        if not provided <= manifest_candidates:
            raise HardwareSupportPoolError("hardware-support candidate list references non-candidate payloads")
        manifest_total = raw.get("total_bytes")
        if not isinstance(manifest_total, int) or manifest_total != total:
            raise HardwareSupportPoolError("hardware-support pool total size does not match manifest")

        return cls(
            root,
            suite,
            architecture,
            tuple(packages),
            provided,
            firmware,
            microcode,
            total,
            providers,
        )

    @staticmethod
    def _validated_package_set(raw: dict[str, object], field: str) -> frozenset[str]:
        value = raw.get(field)
        if not isinstance(value, list) or not all(
            isinstance(item, str) and _PACKAGE_RE.fullmatch(item) for item in value
        ):
            raise HardwareSupportPoolError(f"hardware-support {field} is invalid")
        if len(value) != len(set(value)):
            raise HardwareSupportPoolError(f"hardware-support {field} contains duplicates")
        return frozenset(value)

    @staticmethod
    def _validated_firmware_providers(
        raw: dict[str, object], firmware_packages: frozenset[str]
    ) -> tuple[tuple[str, tuple[str, ...]], ...]:
        value = raw.get("firmware_providers")
        if not isinstance(value, dict) or len(value) > _MAX_FIRMWARE_PROVIDERS:
            raise HardwareSupportPoolError("hardware-support firmware provider map is invalid")
        result: list[tuple[str, tuple[str, ...]]] = []
        for firmware_name, package_names in value.items():
            if not _safe_firmware_name(firmware_name):
                raise HardwareSupportPoolError("hardware-support firmware provider path is invalid")
            if not isinstance(package_names, list) or not package_names or not all(
                isinstance(item, str) and _PACKAGE_RE.fullmatch(item) for item in package_names
            ):
                raise HardwareSupportPoolError("hardware-support firmware provider packages are invalid")
            unique = tuple(dict.fromkeys(package_names))
            if len(unique) != len(package_names):
                raise HardwareSupportPoolError("hardware-support firmware provider packages contain duplicates")
            if any(package not in firmware_packages for package in unique):
                raise HardwareSupportPoolError("hardware-support firmware provider references non-firmware package")
            result.append((firmware_name, unique))
        return tuple(sorted(result))

    @staticmethod
    def _verify_repository_indexes(root: Path, raw: dict[str, object]) -> None:
        indexes = raw.get("repository_indexes")
        if not isinstance(indexes, dict) or set(indexes) != {"Packages", "Packages.gz"}:
            raise HardwareSupportPoolError("hardware-support repository index manifest is invalid")
        for index_name in ("Packages", "Packages.gz"):
            metadata = indexes.get(index_name)
            if not isinstance(metadata, dict):
                raise HardwareSupportPoolError("hardware-support repository index metadata is invalid")
            size = metadata.get("size")
            digest = metadata.get("sha256")
            if not isinstance(size, int) or not 0 <= size <= _MAX_INDEX_BYTES:
                raise HardwareSupportPoolError("hardware-support repository index size is invalid")
            if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
                raise HardwareSupportPoolError("hardware-support repository index digest is invalid")
            index = root / index_name
            if index.is_symlink() or not index.is_file():
                raise HardwareSupportPoolError(f"hardware-support repository index is missing: {index_name}")
            if index.stat().st_size != size or _sha256(index) != digest:
                raise HardwareSupportPoolError(
                    f"hardware-support repository index changed: {index_name}"
                )

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

    def require_firmware(self, packages: Iterable[str]) -> tuple[str, ...]:
        requested = self.require_candidates(packages)
        if any(package not in self.provided_firmware for package in requested):
            raise HardwareSupportPoolError("requested hardware package is not verified firmware")
        return requested

    def require_microcode(self, packages: Iterable[str]) -> tuple[str, ...]:
        requested = self.require_candidates(packages)
        if any(package not in self.provided_microcode for package in requested):
            raise HardwareSupportPoolError("requested hardware package is not verified microcode")
        return requested

    def packages_for_firmware(self, firmware_pattern: str) -> tuple[str, ...]:
        """Return a minimal deterministic package set covering matched firmware.

        Debian Contents can name multiple packages providing one file. Greia
        chooses one verified provider per concrete firmware file, preferring the
        smallest downloaded candidate payload and then package name. Wildcard
        declarations still cover every concrete firmware file they match.
        """

        if not _safe_firmware_name(firmware_pattern):
            raise HardwareSupportPoolError("requested firmware path/pattern is invalid")
        wildcard = any(character in firmware_pattern for character in "*?[")
        package_sizes: dict[str, int] = {}
        for package in self.packages:
            if package.package in self.provided_firmware:
                previous = package_sizes.get(package.package)
                if previous is None or package.size < previous:
                    package_sizes[package.package] = package.size
        selected: set[str] = set()
        for firmware_name, providers in self.firmware_providers:
            matched = (
                fnmatch.fnmatchcase(firmware_name, firmware_pattern)
                if wildcard
                else firmware_name == firmware_pattern
            )
            if not matched:
                continue
            preferred = min(
                providers,
                key=lambda package: (package_sizes.get(package, _MAX_POOL_BYTES + 1), package),
            )
            selected.add(preferred)
        return tuple(sorted(selected))

    @property
    def apt_source_line(self) -> str:
        # This source is trusted only after load() has verified the frozen
        # package payloads and both repository indexes against the manifest.
        return "deb [trusted=yes] file:/run/greia-hardware-support ./"


def _safe_firmware_name(value: object) -> bool:
    if not isinstance(value, str) or not value or "\x00" in value:
        return False
    try:
        encoded = value.encode("utf-8")
    except UnicodeError:
        return False
    if len(encoded) > _MAX_FIRMWARE_PATH_BYTES or value.startswith("/"):
        return False
    return ".." not in Path(value).parts


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
