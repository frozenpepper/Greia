from __future__ import annotations

import fcntl
import json
import os
import shutil
import stat
import tempfile
import threading
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .activities import (
    ActivityManifest,
    ActivityRegistry,
    ActivityValidationError,
    RuntimeCatalogue,
    package_digest,
)
from .activity_assets import package_icon_path
from .trust import ActivitySource, PackageTrust


MAX_ARCHIVE_ENTRIES = 512
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_PATH_CHARACTERS = 220
MAX_COMPRESSION_RATIO = 200
_INSTALL_LOCK_NAME = ".install.lock"


class ActivityPackageError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ActivityInstallReceipt:
    activity_id: str
    version: str
    package_digest: str
    package_trust: PackageTrust
    source_id: str

    def as_json_dict(self) -> dict[str, str]:
        return {
            "activity_id": self.activity_id,
            "version": self.version,
            "package_digest": self.package_digest,
            "package_trust": self.package_trust.value,
            "source_id": self.source_id,
        }


class ActivityPackageService:
    """Single bounded authority for parent-approved local Activity packages.

    This tranche intentionally supports *new installs only*. It establishes the
    R10 safety/transaction seams without pretending update/signature policy is
    solved: bounded acquisition, archive containment, normal ActivityRegistry
    validation, immutable version storage, atomic activation and typed parent
    provenance. Updates/removal remain separate future operations.

    Installation is serialized twice: a small in-process lock avoids redundant
    contenders inside one service object, while a private ``flock`` file under
    the package state root serializes separate package-service processes that
    share the same authoritative store. Receipt preparation and active-tree
    publication therefore cannot race merely because HTTP/process composition
    changes later.
    """

    SOURCE_ID = "greia-parent-package-service"

    def __init__(
        self,
        *,
        state_root: Path,
        runtime_catalogue: Path,
        built_in_root: Path | None = None,
    ) -> None:
        self.state_root = state_root.resolve()
        self.active_root = self.state_root / "active"
        self.versions_root = self.state_root / "versions"
        self.staging_root = self.state_root / "staging"
        self.receipts_root = self.state_root / "receipts"
        self.runtime = RuntimeCatalogue.load(runtime_catalogue)
        self.built_in_root = built_in_root.resolve() if built_in_root else None
        self._install_lock = threading.Lock()

    @classmethod
    def from_environment(cls) -> "ActivityPackageService":
        os_root = Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os")).resolve()
        return cls(
            state_root=Path(
                os.environ.get(
                    "GREIA_PARENT_ACTIVITY_PACKAGE_ROOT",
                    "/var/lib/greia-os/activity-packages",
                )
            ),
            runtime_catalogue=os_root / "runtime" / "child-runtime.toml",
            built_in_root=os_root / "activities",
        )

    def install_archive(self, archive_path: Path) -> ActivityInstallReceipt:
        """Install one new Activity under a process-wide serialized transaction."""

        try:
            self._ensure_roots()
            with self._install_lock:
                with self._process_install_lock():
                    return self._install_archive_serialized(archive_path)
        except ActivityPackageError:
            raise
        except OSError as exc:
            raise ActivityPackageError(
                f"could not establish Activity package transaction lock: {exc}"
            ) from exc

    @contextmanager
    def _process_install_lock(self) -> Iterator[None]:
        lock_path = self.state_root / _INSTALL_LOCK_NAME
        flags = os.O_CREAT | os.O_RDWR
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(lock_path, flags, 0o600)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise ActivityPackageError(
                    "Activity package transaction lock is not a regular file"
                )
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)

    def _install_archive_serialized(
        self, archive_path: Path
    ) -> ActivityInstallReceipt:
        archive_path = archive_path.resolve(strict=True)
        if not archive_path.is_file():
            raise ActivityPackageError("Activity package is not a file")
        size = archive_path.stat().st_size
        if size <= 0 or size > MAX_ARCHIVE_BYTES:
            raise ActivityPackageError(
                f"Activity package archive must be between 1 and {MAX_ARCHIVE_BYTES} bytes"
            )
        stage_parent = Path(
            tempfile.mkdtemp(prefix="install-", dir=str(self.staging_root))
        )
        package_root = stage_parent / "package"
        package_root.mkdir(mode=0o700)
        activation: Path | None = None
        try:
            self._extract_bounded_archive(archive_path, package_root)
            if not (package_root / "activity.toml").is_file():
                raise ActivityPackageError(
                    "Activity package must contain activity.toml at archive root"
                )
            manifest, digest = self._validate_staged(stage_parent, package_root)
            final_active = self.active_root / manifest.activity_id
            if final_active.exists():
                raise ActivityPackageError(
                    f"Activity {manifest.activity_id} is already installed; update is not enabled yet"
                )

            immutable = self.versions_root / manifest.activity_id / digest
            immutable.parent.mkdir(parents=True, exist_ok=True)
            os.chmod(immutable.parent, 0o700)
            if immutable.exists():
                # Recover an immutable version left by an interrupted attempt.
                # Its digest-addressed path is not trusted by name alone.
                if not immutable.is_dir() or package_digest(immutable) != digest:
                    raise ActivityPackageError(
                        "stored immutable Activity version does not match its package digest"
                    )
                shutil.rmtree(package_root)
            else:
                os.replace(package_root, immutable)
                self._make_tree_read_only(immutable)

            activation = self.active_root / f".{manifest.activity_id}.activating-{digest[:12]}"
            if activation.exists():
                shutil.rmtree(activation)
            # Hard links keep the active view cheap while remaining a real tree:
            # ActivityRegistry never follows a package-root symlink and future
            # updates can atomically swap one active directory for another.
            shutil.copytree(immutable, activation, copy_function=os.link)
            self._make_tree_read_only(activation)
            receipt = ActivityInstallReceipt(
                activity_id=manifest.activity_id,
                version=manifest.version,
                package_digest=digest,
                package_trust=PackageTrust.PARENT_TRUSTED_UNSIGNED,
                source_id=self.SOURCE_ID,
            )

            # The active-directory rename is the install commit point. Write the
            # audit receipt first, so any error that reaches the caller occurs
            # before executable code becomes visible. A crash in this narrow
            # pre-commit window can leave an orphan receipt/immutable version,
            # both of which are safe and recoverable on retry.
            self._write_receipt(receipt)
            try:
                os.rename(activation, final_active)
            except (FileExistsError, OSError) as exc:
                self._receipt_path(manifest.activity_id).unlink(missing_ok=True)
                if isinstance(exc, FileExistsError):
                    raise ActivityPackageError(
                        f"Activity {manifest.activity_id} became installed concurrently"
                    ) from exc
                raise
            return receipt
        except ActivityPackageError:
            raise
        except (
            ActivityValidationError,
            OSError,
            zipfile.BadZipFile,
            zipfile.LargeZipFile,
        ) as exc:
            raise ActivityPackageError(str(exc)) from exc
        finally:
            # The stage tree and any non-committed activation residue are private
            # to this attempt. A receipt failure (or any error before the atomic
            # rename) must not leave a launch-visible active entry behind.
            self._discard_private_tree(stage_parent)
            if activation is not None:
                self._discard_private_tree(activation)

    def _ensure_roots(self) -> None:
        self.state_root.mkdir(parents=True, exist_ok=True)
        for path, mode in (
            (self.active_root, 0o755),
            (self.versions_root, 0o700),
            (self.staging_root, 0o700),
            (self.receipts_root, 0o700),
        ):
            path.mkdir(parents=True, exist_ok=True)
            os.chmod(path, mode)

    def _extract_bounded_archive(self, archive_path: Path, destination: Path) -> None:
        seen: set[str] = set()
        total = 0
        with zipfile.ZipFile(archive_path, "r", allowZip64=False) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > MAX_ARCHIVE_ENTRIES:
                raise ActivityPackageError(
                    f"Activity package must contain 1..{MAX_ARCHIVE_ENTRIES} archive entries"
                )
            for info in entries:
                relative = self._safe_archive_path(info)
                canonical = relative.as_posix().casefold()
                if canonical in seen:
                    raise ActivityPackageError(
                        f"Activity package contains a duplicate portable path: {relative.as_posix()}"
                    )
                seen.add(canonical)
                if info.flag_bits & 0x1:
                    raise ActivityPackageError(
                        "encrypted Activity package entries are not supported"
                    )
                mode = (info.external_attr >> 16) & 0xFFFF
                file_type = stat.S_IFMT(mode)
                if file_type and stat.S_ISLNK(mode):
                    raise ActivityPackageError("Activity package symlinks are forbidden")
                if file_type and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                    raise ActivityPackageError(
                        "Activity package contains a special filesystem entry"
                    )
                if info.is_dir():
                    target = destination.joinpath(*relative.parts)
                    target.mkdir(parents=True, exist_ok=True)
                    os.chmod(target, 0o755)
                    continue
                total += info.file_size
                if total > self.runtime.maximum_activity_bytes:
                    raise ActivityPackageError(
                        "Activity package exceeds the platform uncompressed size limit"
                    )
                if (
                    info.file_size > 1024 * 1024
                    and info.compress_size > 0
                    and info.file_size > info.compress_size * MAX_COMPRESSION_RATIO
                ):
                    raise ActivityPackageError(
                        "Activity package has an unsafe compression ratio"
                    )
                target = destination.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source, target.open("xb") as sink:
                    remaining = info.file_size
                    while remaining:
                        chunk = source.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise ActivityPackageError(
                                "Activity package entry ended unexpectedly"
                            )
                        sink.write(chunk)
                        remaining -= len(chunk)
                    if source.read(1):
                        raise ActivityPackageError(
                            "Activity package entry exceeds declared size"
                        )
                os.chmod(target, 0o644)

    @staticmethod
    def _safe_archive_path(info: zipfile.ZipInfo) -> PurePosixPath:
        name = info.filename
        if (
            not name
            or len(name) > MAX_PATH_CHARACTERS
            or "\\" in name
            or "\x00" in name
        ):
            raise ActivityPackageError("Activity package contains an invalid path")
        path = PurePosixPath(name)
        parts = tuple(part for part in path.parts if part != "")
        if (
            path.is_absolute()
            or not parts
            or any(part in {".", ".."} for part in parts)
        ):
            raise ActivityPackageError("Activity package path escapes archive root")
        if any(part.startswith(".") for part in parts):
            raise ActivityPackageError("hidden Activity package paths are not supported")
        return PurePosixPath(*parts)

    def _validate_staged(
        self, stage_parent: Path, package_root: Path
    ) -> tuple[ActivityManifest, str]:
        sources: list[ActivitySource] = []
        if self.built_in_root is not None:
            sources.append(
                ActivitySource(
                    self.built_in_root,
                    PackageTrust.BUILT_IN,
                    "greia-system",
                )
            )
        sources.append(
            ActivitySource(
                stage_parent,
                PackageTrust.PARENT_TRUSTED_UNSIGNED,
                self.SOURCE_ID,
            )
        )
        registry = ActivityRegistry(tuple(sources), self.runtime)
        registrations = registry.discover_registrations()
        staged = next(
            (
                registration
                for registration in registrations
                if registration.manifest.root == package_root.resolve()
            ),
            None,
        )
        if staged is None:
            raise ActivityPackageError(
                "staged Activity did not validate as one installable package"
            )
        # Package-owned presentation assets are part of install validity, not a
        # launcher-time best-effort concern. A malformed icon reference must be
        # rejected before the package becomes visible.
        package_icon_path(staged.manifest)

        # A staged package may never shadow a built-in identity. Discovery of the
        # built-in source happens here, so a fresh package colliding with a
        # built-in is reported clearly.
        staged_id = staged.manifest.activity_id
        if self.active_root is not None and (self.active_root / staged_id).exists():
            raise ActivityPackageError(
                f"Activity {staged_id} is already installed; update is not enabled yet"
            )

        # The staged package must not collide (including legacy aliases) with any
        # already installed parent package. Discovery of the active source is done
        # separately so the already-installed case above wins with the clearer
        # message rather than a registry collision.
        if self.active_root.exists():
            combined = ActivityRegistry(
                (
                    *sources,
                    ActivitySource(
                        self.active_root,
                        PackageTrust.PARENT_TRUSTED_UNSIGNED,
                        self.SOURCE_ID,
                    ),
                ),
                self.runtime,
            )
            try:
                combined.discover_registrations()
            except ActivityValidationError as exc:
                raise ActivityPackageError(str(exc)) from exc
        return staged.manifest, staged.package_digest

    @staticmethod
    def _make_tree_read_only(root: Path) -> None:
        for path in root.rglob("*"):
            if path.is_dir():
                os.chmod(path, 0o555)
            elif path.is_file():
                os.chmod(path, 0o444)
        os.chmod(root, 0o555)

    @staticmethod
    def _discard_private_tree(root: Path) -> None:
        """Remove a private service tree that may contain read-only entries.

        ``shutil.rmtree`` alone cannot delete directories whose mode bits were
        cleared by ``_make_tree_read_only``, so restore write permission before
        removing. Only private staging/activation trees are passed here; the
        committed immutable/active trees are never discarded this way.
        """

        if not root.exists():
            return
        for path in root.rglob("*"):
            if path.is_dir() and not os.access(path, os.W_OK):
                os.chmod(path, 0o700)
            elif path.is_file() and not os.access(path, os.W_OK):
                os.chmod(path, 0o600)
        if root.is_dir() and not os.access(root, os.W_OK):
            os.chmod(root, 0o700)
        shutil.rmtree(root, ignore_errors=True)

    def _receipt_path(self, activity_id: str) -> Path:
        return self.receipts_root / f"{activity_id}.json"

    def _write_receipt(self, receipt: ActivityInstallReceipt) -> None:
        destination = self._receipt_path(receipt.activity_id)
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(
                receipt.as_json_dict(),
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary, 0o600)
        os.replace(temporary, destination)
