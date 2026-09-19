from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from greia_installer import hardware_support_archive as _archive


_PACKAGE_RE = _archive._PACKAGE_RE
_SHA256_RE = _archive._SHA256_RE
_MAX_POOL_PACKAGES = _archive.MAX_ARCHIVE_POOL_PACKAGES
_MAX_POOL_BYTES = _archive.MAX_ARCHIVE_POOL_BYTES
_MAX_INDEX_BYTES = _archive.MAX_ARCHIVE_INDEX_BYTES
_MAX_FIRMWARE_PROVIDERS = _archive.MAX_ARCHIVE_FIRMWARE_PROVIDERS
_MAX_FIRMWARE_PATH_BYTES = _archive.MAX_ARCHIVE_FIRMWARE_PATH_BYTES


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
    installed_bytes: int

    def __post_init__(self) -> None:
        # Single-owner field validation lives in the shared archive module;
        # translate its verdict into the pool error type.
        try:
            _archive.validate_package_fields(
                package=self.package,
                version=self.version,
                architecture=self.architecture,
                filename=self.filename,
                size=self.size,
                sha256=self.sha256,
                candidate=self.candidate,
                installed_bytes=self.installed_bytes,
            )
        except _archive.HardwareSupportArchiveError as exc:
            raise HardwareSupportPoolError(str(exc)) from exc


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
    total_installed_bytes: int
    firmware_providers: tuple[tuple[str, tuple[str, ...]], ...] = ()
    broad_firmware: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if (
            isinstance(self.total_installed_bytes, bool)
            or not isinstance(self.total_installed_bytes, int)
            or not 0 <= self.total_installed_bytes <= _MAX_POOL_BYTES
        ):
            raise HardwareSupportPoolError("hardware-support installed total size is invalid")
        if sum(package.installed_bytes for package in self.packages) != self.total_installed_bytes:
            raise HardwareSupportPoolError(
                "hardware-support installed total does not match package installed sizes"
            )

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
        # Single-owner manifest semantics (schema, suite/arch, packages,
        # totals, candidate sets, providers, index shape) live in the
        # shared archive module; filesystem proof below stays here.
        try:
            validated = _archive.parse_manifest_dict(raw)
        except _archive.HardwareSupportArchiveError as exc:
            raise HardwareSupportPoolError(str(exc)) from exc
        suite = raw.get("suite")
        architecture = raw.get("architecture")
        if expected_suite is not None and suite != expected_suite:
            raise HardwareSupportPoolError("hardware-support suite does not match installer")
        if expected_architecture is not None and architecture != expected_architecture:
            raise HardwareSupportPoolError("hardware-support architecture does not match installer")

        packages: list[HardwareSupportPoolPackage] = []
        expected_paths: set[Path] = set()
        total = 0
        total_installed = 0
        for item in validated.packages:
            try:
                package = HardwareSupportPoolPackage(
                    package=item.package,
                    version=item.version,
                    architecture=item.architecture,
                    filename=item.filename,
                    size=item.size,
                    sha256=item.sha256,
                    candidate=item.candidate,
                    installed_bytes=item.installed_bytes,
                )
            except (KeyError, TypeError) as exc:
                raise HardwareSupportPoolError("hardware-support package entry is incomplete") from exc
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
            total_installed += package.installed_bytes
            if total_installed > _MAX_POOL_BYTES:
                raise HardwareSupportPoolError(
                    "hardware-support pool installed size exceeds runtime byte bound"
                )

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

        # Manifest semantics (totals, candidate sets, providers, broad
        # coverage) already proven by the shared parser above; reuse its
        # verdict instead of re-implementing it here.
        provided = validated.provided_candidates
        firmware = validated.provided_firmware
        microcode = validated.provided_microcode
        broad_firmware = validated.broad_firmware
        providers = validated.firmware_providers
        if validated.total_bytes != total or validated.total_installed_bytes != total_installed:
            raise HardwareSupportPoolError(
                "hardware-support pool installed total does not match manifest"
            )

        return cls(
            root,
            suite,
            architecture,
            tuple(packages),
            provided,
            firmware,
            microcode,
            total,
            total_installed,
            providers,
            broad_firmware,
        )

    @staticmethod
    def _validated_package_set(raw: dict[str, object], field: str) -> frozenset[str]:
        # Thin compat shim: set semantics ownership lives in shared module.
        try:
            return _archive._validated_package_set(raw, field)
        except _archive.HardwareSupportArchiveError as exc:
            raise HardwareSupportPoolError(str(exc)) from exc

    @staticmethod
    def _validated_firmware_providers(
        raw: dict[str, object], firmware_packages: frozenset[str]
    ) -> tuple[tuple[str, tuple[str, ...]], ...]:
        # Thin compat shim: provider-map ownership lives in shared module.
        try:
            return _archive._validated_firmware_providers(raw, firmware_packages)
        except _archive.HardwareSupportArchiveError as exc:
            raise HardwareSupportPoolError(str(exc)) from exc

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
            if (
                not isinstance(size, int)
                or isinstance(size, bool)
                or not 0 <= size <= _MAX_INDEX_BYTES
            ):
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


#: zstd framing every built hardware-support archive must carry (the same
#: magic the release bundle seam requires for compressed members).
#: Canonical owner is the shared archive module; kept here as an alias.
_SUPPORT_ARCHIVE_ZSTD_MAGIC = _archive.ARCHIVE_ZSTD_MAGIC

#: Single production compressed bound for ``hardware-support.tar.zst``
#: (512 MiB). The historical 2 GiB outer bound is retired; the shared
#: archive module owns the canonical value and both build and runtime
#: wrappers enforce it identically.
_MAX_SUPPORT_ARCHIVE_BYTES = _archive.MAX_ARCHIVE_COMPRESSED_BYTES

#: Decompressed-tar bound owned by the shared module (streaming cap).
#: Kept as an alias; the old whole-artifact buffering cap is retired.
_SUPPORT_ARCHIVE_TAR_SLOP_BYTES = _archive.MAX_ARCHIVE_UNCOMPRESSED_BYTES

#: Largest embedded manifest.json accepted from a support archive.
#: Canonical owner is the shared archive module; kept here as an alias.
_MAX_SUPPORT_ARCHIVE_MANIFEST_BYTES = _archive.MAX_ARCHIVE_MANIFEST_BYTES

#: Top-level non-pool members every built archive carries.
#: Canonical owner is the shared archive module; kept here as an alias.
_SUPPORT_ARCHIVE_TOP_MEMBERS = tuple(sorted(_archive.TOP_FILES))


def _normalize_archive_name(name: str) -> str:
    # Thin alias: naming/shape ownership lives in the shared module.
    return _archive.normalize_archive_name(name)


def installed_size_bound_from_support_archive(path: Path) -> int:
    """Return the verified installed-size bound from a built support archive.

    Thin build-side wrapper: delegates every header/member/manifest
    verdict to the shared streaming parser
    (``hardware_support_archive.inspect_archive_file``) and returns
    ``total_installed_bytes``. Compressed archive/``.deb`` bytes are
    transfer size only and never substitute.
    """
    try:
        metadata = _archive.inspect_archive_file(Path(path))
    except _archive.HardwareSupportArchiveError as exc:
        raise HardwareSupportPoolError(str(exc)) from exc
    return metadata.total_installed_bytes


def support_installed_size_bound(path: Path | None) -> int:
    """Return the verified installed-size bound for release capacity proof.

    ``None`` (no ``--hardware-support``) yields 0. A pool directory is
    verified through :meth:`VerifiedHardwareSupportPool.load`; a built
    ``hardware-support.tar.zst`` archive file is verified through
    :func:`installed_size_bound_from_support_archive`. Both routes return
    ``total_installed_bytes`` from verified metadata — never
    operator-entered values and never compressed ``.deb`` bytes.
    """
    if path is None:
        return 0
    location = Path(path)
    if location.is_dir() and not location.is_symlink():
        return VerifiedHardwareSupportPool.load(location).total_installed_bytes
    return installed_size_bound_from_support_archive(location)


def _safe_firmware_name(value: object) -> bool:
    # Single owner lives in the shared archive module.
    return _archive._safe_firmware_name(value)


def _sha256(path: Path) -> str:
    return _archive._sha256_file(Path(path))
