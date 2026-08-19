"""Isolated, portable simulator workspace built from real Greia state services."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.profiles import ChildProfile, ProfileStore
from greia_platform.trust import ActivitySource, PackageTrust
from greia_platform.ui_preferences import InterfaceSize, UiPreferencesStore


_WORKSPACE_SCHEMA_VERSION = 1
_IGNORED_DEVELOPMENT_NAMES = frozenset(
    {".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache"}
)


@dataclass(frozen=True, slots=True)
class _TreeEntry:
    relative: Path
    is_dir: bool
    size: int
    mode: int
    device: int
    inode: int
    mtime_ns: int
    digest: str | None = None


@dataclass(slots=True)
class SimulatorWorkspace:
    """Own synthetic-device state without mutating or racing the Greia checkout."""

    repo_root: Path
    state_root: Path
    _lock_fd: int | None = field(default=None, init=False, repr=False)
    _child_pid: int | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        repo_root = self.repo_root.resolve(strict=True)
        state_root = self.state_root.expanduser().resolve(strict=False)
        if not (repo_root / "runtime" / "child-runtime.toml").is_file():
            raise ValueError("repo_root is not a Greia source checkout")
        if state_root == repo_root or repo_root in state_root.parents:
            raise ValueError("simulator state must live outside the Greia source tree")
        self.repo_root = repo_root
        self.state_root = state_root

    @property
    def profiles_root(self) -> Path:
        return self.state_root / "profiles"

    @property
    def run_root(self) -> Path:
        return self.state_root / "run"

    @property
    def developer_root(self) -> Path:
        return self.state_root / "developer-activities"

    @property
    def package_root(self) -> Path:
        return self.state_root / "activity-packages"

    @property
    def media_root(self) -> Path:
        return self.state_root / "media"

    @property
    def metadata_path(self) -> Path:
        return self.state_root / "workspace.json"

    @property
    def lock_path(self) -> Path:
        return self.state_root / ".workspace.lock"

    def ensure(self, *, allow_repo_rebind: bool = False) -> None:
        """Prepare state; rebind is allowed only while this object holds the lease."""

        self.state_root.mkdir(parents=True, exist_ok=True)
        if allow_repo_rebind and self._lock_fd is None:
            raise RuntimeError("workspace rebind requires the active writer lock")
        self._ensure_metadata(allow_repo_rebind=allow_repo_rebind)
        self._ensure_state_directories()

    def acquire_lock(self, *, allow_repo_rebind: bool = False) -> None:
        """Take the workspace single-writer lease before any optional rebind."""

        self.state_root.mkdir(parents=True, exist_ok=True)
        if self._lock_fd is not None:
            self.ensure(allow_repo_rebind=allow_repo_rebind)
            return

        payload = self._lock_payload()
        for attempt in range(2):
            try:
                descriptor = os.open(
                    self.lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_RDWR,
                    0o600,
                )
            except FileExistsError:
                if attempt or not self._discard_stale_lock():
                    raise RuntimeError(
                        "simulator workspace is already in use; choose another --state-dir"
                    )
                continue
            try:
                self._write_lock_payload(descriptor, payload)
                self._lock_fd = descriptor
                self.ensure(allow_repo_rebind=allow_repo_rebind)
            except Exception:
                if self._lock_fd is None:
                    try:
                        self._unlink_owned_lock(descriptor)
                    finally:
                        os.close(descriptor)
                else:
                    self._child_pid = None
                    self.release_lock()
                raise
            return
        raise RuntimeError("could not acquire simulator workspace lock")

    def update_lock_child_pid(self, child_pid: int | None) -> None:
        """Bind/unbind the owned Shell process to the active writer lease."""

        descriptor = self._lock_fd
        if descriptor is None:
            raise RuntimeError("cannot update simulator child ownership without writer lock")
        if child_pid is not None and (not isinstance(child_pid, int) or child_pid <= 0):
            raise ValueError("simulator child PID must be a positive integer")
        if not self._lock_path_is_owned(descriptor):
            raise RuntimeError("simulator workspace lock ownership was lost")
        previous = self._child_pid
        self._child_pid = child_pid
        try:
            self._write_lock_payload(descriptor, self._lock_payload())
        except Exception:
            self._child_pid = previous
            raise

    def release_lock(self) -> None:
        descriptor = self._lock_fd
        if descriptor is None:
            return
        if self._child_pid is not None:
            raise RuntimeError("cannot release simulator workspace while owned Shell is registered")
        self._lock_fd = None
        try:
            self._unlink_owned_lock(descriptor)
        finally:
            os.close(descriptor)

    def environment(self) -> dict[str, str]:
        """Return isolated normal-Greia roots for the real child shell."""

        self.ensure()
        return {
            "GREIA_OS_ROOT": str(self.repo_root),
            "GREIA_PROFILES_DIR": str(self.profiles_root),
            "GREIA_ACTIVE_PROFILE_STATUS": str(self.run_root / "active-profile.json"),
            "GREIA_DEVELOPER_ACTIVITY_ROOT": str(self.developer_root),
            "GREIA_PARENT_ACTIVITY_ROOT": str(self.package_root / "active"),
            "GREIA_PARENT_ACTIVITY_PACKAGE_ROOT": str(self.package_root),
            "GREIA_MEDIA_ROOT": str(self.media_root),
            "GREIA_MAIN_CREDENTIAL_PATH": str(self.state_root / "main-credential.json"),
            "GREIA_SKIP_BOOT_HANDOFF": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }

    def profile_store(self) -> ProfileStore:
        self.ensure()
        return ProfileStore.load(
            self.repo_root / "runtime" / "profile-defaults.toml",
            self.profiles_root,
        )

    def profiles(self) -> tuple[ChildProfile, ...]:
        return self.profile_store().ensure_initialized()

    def set_interface_size(
        self,
        profile_id: str,
        value: str | InterfaceSize,
    ) -> InterfaceSize:
        store = self.profile_store()
        context = store.context(profile_id)
        preferences = UiPreferencesStore(context.customization_dir).set_interface_size(value)
        return preferences.interface_size

    def load_activity(self, source: Path):
        """Safely snapshot, validate and atomically publish a developer Activity."""

        self.ensure()
        source = source.expanduser().resolve(strict=True)
        if not source.is_dir():
            raise ValueError("Activity source must be a directory")
        if self._paths_overlap(source, self.state_root):
            raise ValueError("Activity source must not overlap simulator managed state")

        runtime = RuntimeCatalogue.load(self.repo_root / "runtime" / "child-runtime.toml")
        snapshot = self._inspect_development_tree(source, runtime)
        staging_parent = Path(
            tempfile.mkdtemp(prefix="greia-simulator-load-", dir=str(self.state_root))
        )
        staged = staging_parent / "activity"
        previous = staging_parent / "previous"
        destination: Path | None = None
        published = False
        try:
            self._copy_development_snapshot(source, staged, snapshot, runtime)
            built_in_source = ActivitySource(
                self.repo_root / "activities",
                trust=PackageTrust.BUILT_IN,
                source_id="greia-system",
            )
            staging_source = ActivitySource(
                staging_parent,
                trust=PackageTrust.DEVELOPER_UNSIGNED,
                source_id="greia-simulator-staging",
            )
            staging_registry = ActivityRegistry((built_in_source, staging_source), runtime)
            registration = next(
                (
                    item
                    for item in staging_registry.discover_registrations()
                    if item.manifest.root == staged.resolve()
                ),
                None,
            )
            if registration is None:
                raise ValueError("staged Activity did not validate as one Greia package")

            destination = self.developer_root / registration.manifest.activity_id
            self._reject_other_developer_collision(
                registration.manifest.activity_id,
                destination,
                built_in_source,
                runtime,
            )
            if destination.is_symlink():
                raise ValueError("managed developer Activity destination must not be a symlink")
            if destination.exists() and not destination.is_dir():
                raise ValueError("managed developer Activity destination is not a directory")

            if destination.exists():
                os.replace(destination, previous)
            try:
                os.replace(staged, destination)
                final_source = ActivitySource(
                    self.developer_root,
                    trust=PackageTrust.DEVELOPER_UNSIGNED,
                    source_id="greia-developer-remote",
                )
                final_registry = ActivityRegistry((built_in_source, final_source), runtime)
                final = next(
                    (
                        item
                        for item in final_registry.discover_registrations()
                        if item.manifest.root == destination.resolve()
                    ),
                    None,
                )
                if final is None:
                    raise ValueError("loaded Activity was not discoverable by Greia")
                published = True
                return final
            except Exception:
                self._discard_tree(destination)
                if previous.exists():
                    os.replace(previous, destination)
                raise
        finally:
            if (
                not published
                and destination is not None
                and previous.exists()
                and not destination.exists()
            ):
                os.replace(previous, destination)
            shutil.rmtree(staging_parent, ignore_errors=True)

    def install_activity_package(self, archive: Path) -> Any:
        """Exercise only the canonical Parent-approved package transaction."""

        self.ensure()
        try:
            from greia_platform.activity_packages import ActivityPackageService
        except ImportError as exc:
            raise RuntimeError(
                "canonical Activity package installation is unavailable on this host"
            ) from exc
        service = ActivityPackageService(
            state_root=self.package_root,
            runtime_catalogue=self.repo_root / "runtime" / "child-runtime.toml",
            built_in_root=self.repo_root / "activities",
        )
        return service.install_archive(archive.expanduser())

    def _lock_payload(self) -> bytes:
        return json.dumps(
            {
                "pid": os.getpid(),
                "child_pid": self._child_pid,
                "repo_root": str(self.repo_root),
                "schema_version": _WORKSPACE_SCHEMA_VERSION,
            },
            sort_keys=True,
        ).encode("utf-8")

    @staticmethod
    def _write_lock_payload(descriptor: int, payload: bytes) -> None:
        os.lseek(descriptor, 0, os.SEEK_SET)
        os.ftruncate(descriptor, 0)
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("could not write simulator workspace lock")
            remaining = remaining[written:]
        os.fsync(descriptor)

    def _ensure_state_directories(self) -> None:
        for path in (
            self.profiles_root,
            self.run_root,
            self.developer_root,
            self.package_root,
            self.media_root,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def _ensure_metadata(self, *, allow_repo_rebind: bool) -> None:
        expected = {
            "schema_version": _WORKSPACE_SCHEMA_VERSION,
            "repo_root": str(self.repo_root),
        }
        if self.metadata_path.exists():
            try:
                current = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError) as exc:
                raise RuntimeError("simulator workspace metadata is invalid") from exc
            if (
                not isinstance(current, dict)
                or current.get("schema_version") != _WORKSPACE_SCHEMA_VERSION
            ):
                raise RuntimeError("simulator workspace schema is incompatible")
            current_root = current.get("repo_root")
            if current_root != str(self.repo_root) and not allow_repo_rebind:
                raise RuntimeError(
                    "simulator workspace belongs to another Greia checkout; "
                    "use another --state-dir or --rebind-state deliberately"
                )
            if current_root == str(self.repo_root):
                return
        self._atomic_write_json(self.metadata_path, expected)

    def _atomic_write_json(self, path: Path, value: object) -> None:
        descriptor, raw = tempfile.mkstemp(prefix=".workspace-", dir=str(self.state_root))
        temporary = Path(raw)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(value, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def _discard_stale_lock(self) -> bool:
        # Python's os.kill(pid, 0) is a harmless existence probe on POSIX, but
        # on Windows non-console-event signals are implemented via
        # TerminateProcess. Fail closed there rather than probing/killing a PID.
        if os.name != "posix":
            return False
        try:
            raw = json.loads(self.lock_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            # A newly created/re-written lock may be observed before its owner
            # has finished the payload. Partial state cannot be classified stale.
            return False
        if not isinstance(raw, dict):
            return False
        if raw.get("schema_version") != _WORKSPACE_SCHEMA_VERSION:
            return False
        if not isinstance(raw.get("repo_root"), str):
            return False
        try:
            pid = int(raw.get("pid", -1))
        except (TypeError, ValueError):
            return False
        if pid <= 0:
            return False
        child_raw = raw.get("child_pid")
        if child_raw is None:
            child_pid = None
        else:
            try:
                child_pid = int(child_raw)
            except (TypeError, ValueError):
                return False
            if child_pid <= 0:
                return False
        if _posix_pid_alive(pid):
            return False
        if child_pid is not None and _posix_pid_alive(child_pid):
            return False
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass
        return True

    def _lock_path_is_owned(self, descriptor: int) -> bool:
        try:
            owned = os.fstat(descriptor)
            current = self.lock_path.lstat()
        except FileNotFoundError:
            return False
        return (owned.st_dev, owned.st_ino) == (current.st_dev, current.st_ino)

    def _unlink_owned_lock(self, descriptor: int) -> None:
        if self._lock_path_is_owned(descriptor):
            self.lock_path.unlink(missing_ok=True)

    def _inspect_development_tree(
        self,
        source: Path,
        runtime: RuntimeCatalogue,
    ) -> tuple[_TreeEntry, ...]:
        """Create a finite, content-fingerprinted lstat snapshot before copying."""

        entries: list[_TreeEntry] = []
        total = 0
        for current_raw, dirnames, filenames in os.walk(
            source,
            topdown=True,
            followlinks=False,
        ):
            current = Path(current_raw)
            kept_dirs: list[str] = []
            for name in sorted(dirnames):
                path = current / name
                metadata = path.lstat()
                if stat.S_ISLNK(metadata.st_mode):
                    raise ValueError(f"Activity source symlinks are forbidden: {path}")
                if name in _IGNORED_DEVELOPMENT_NAMES:
                    continue
                if not stat.S_ISDIR(metadata.st_mode):
                    raise ValueError(
                        f"Activity source has a non-directory tree entry: {path}"
                    )
                if name.casefold() in runtime.forbidden_path_names:
                    raise ValueError(f"forbidden package directory: {name}")
                kept_dirs.append(name)
                entries.append(self._entry(path, source, metadata, is_dir=True))
            dirnames[:] = kept_dirs

            for name in sorted(filenames):
                path = current / name
                metadata = path.lstat()
                if stat.S_ISLNK(metadata.st_mode):
                    raise ValueError(f"Activity source symlinks are forbidden: {path}")
                if name in _IGNORED_DEVELOPMENT_NAMES:
                    continue
                if not stat.S_ISREG(metadata.st_mode):
                    raise ValueError(f"Activity source contains a special file: {path}")
                folded = name.casefold()
                if folded in runtime.forbidden_file_names:
                    raise ValueError(f"forbidden package file: {name}")
                if path.suffix.casefold() in runtime.forbidden_suffixes:
                    raise ValueError(f"forbidden package suffix: {path}")
                if metadata.st_mode & 0o111:
                    raise ValueError(f"executable Activity files are forbidden: {path}")
                total += metadata.st_size
                if total > runtime.maximum_activity_bytes:
                    raise ValueError(
                        f"Activity source exceeds {runtime.maximum_activity_bytes} bytes"
                    )
                digest = self._hash_source_file(path, metadata)
                entries.append(
                    self._entry(
                        path,
                        source,
                        metadata,
                        is_dir=False,
                        digest=digest,
                    )
                )
        return tuple(entries)

    def _copy_development_snapshot(
        self,
        source: Path,
        destination: Path,
        entries: tuple[_TreeEntry, ...],
        runtime: RuntimeCatalogue,
    ) -> None:
        destination.mkdir(mode=0o700)
        copied = 0
        for entry in entries:
            target = destination / entry.relative
            origin = source / entry.relative
            metadata = origin.lstat()
            self._assert_same_entry(origin, metadata, entry)
            if entry.is_dir:
                target.mkdir(parents=True, exist_ok=False)
                os.chmod(target, 0o755)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            descriptor = self._open_source_file(origin)
            try:
                opened = os.fstat(descriptor)
                self._assert_same_entry(origin, opened, entry)
                digest = hashlib.sha256()
                with os.fdopen(descriptor, "rb", closefd=False) as source_handle, target.open(
                    "xb"
                ) as sink:
                    remaining = entry.size
                    while remaining:
                        chunk = source_handle.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise ValueError(
                                f"Activity source file ended while staging: {origin}"
                            )
                        digest.update(chunk)
                        sink.write(chunk)
                        copied += len(chunk)
                        remaining -= len(chunk)
                        if copied > runtime.maximum_activity_bytes:
                            raise ValueError(
                                "Activity source exceeded platform size while staging"
                            )
                    if source_handle.read(1):
                        raise ValueError(
                            f"Activity source file grew while staging: {origin}"
                        )
                if digest.hexdigest() != entry.digest:
                    raise ValueError(f"Activity source changed while staging: {origin}")
                final_metadata = os.fstat(descriptor)
                self._assert_same_entry(origin, final_metadata, entry)
                os.chmod(target, 0o644)
            finally:
                os.close(descriptor)

    def _hash_source_file(self, path: Path, expected: os.stat_result) -> str:
        descriptor = self._open_source_file(path)
        try:
            opened = os.fstat(descriptor)
            if not self._stat_matches(opened, expected, is_dir=False):
                raise ValueError(f"Activity source changed while inspecting: {path}")
            digest = hashlib.sha256()
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            final = os.fstat(descriptor)
            if not self._stat_matches(final, expected, is_dir=False):
                raise ValueError(f"Activity source changed while inspecting: {path}")
            return digest.hexdigest()
        finally:
            os.close(descriptor)

    @staticmethod
    def _open_source_file(path: Path) -> int:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        return os.open(path, flags)

    @staticmethod
    def _entry(
        path: Path,
        source: Path,
        metadata: os.stat_result,
        *,
        is_dir: bool,
        digest: str | None = None,
    ) -> _TreeEntry:
        return _TreeEntry(
            relative=path.relative_to(source),
            is_dir=is_dir,
            size=0 if is_dir else metadata.st_size,
            mode=metadata.st_mode,
            device=metadata.st_dev,
            inode=metadata.st_ino,
            mtime_ns=metadata.st_mtime_ns,
            digest=digest,
        )

    def _assert_same_entry(
        self,
        path: Path,
        metadata: os.stat_result,
        entry: _TreeEntry,
    ) -> None:
        if not self._stat_matches_entry(metadata, entry):
            raise ValueError(f"Activity source changed while staging: {path}")
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"Activity source symlinks are forbidden: {path}")

    @staticmethod
    def _stat_matches_entry(metadata: os.stat_result, entry: _TreeEntry) -> bool:
        expected_type = stat.S_IFDIR if entry.is_dir else stat.S_IFREG
        return (
            stat.S_IFMT(metadata.st_mode) == expected_type
            and metadata.st_dev == entry.device
            and metadata.st_ino == entry.inode
            and metadata.st_mtime_ns == entry.mtime_ns
            and (entry.is_dir or metadata.st_size == entry.size)
        )

    @staticmethod
    def _stat_matches(
        current: os.stat_result,
        expected: os.stat_result,
        *,
        is_dir: bool,
    ) -> bool:
        expected_type = stat.S_IFDIR if is_dir else stat.S_IFREG
        return (
            stat.S_IFMT(current.st_mode) == expected_type
            and current.st_dev == expected.st_dev
            and current.st_ino == expected.st_ino
            and current.st_mtime_ns == expected.st_mtime_ns
            and (is_dir or current.st_size == expected.st_size)
        )

    def _reject_other_developer_collision(
        self,
        activity_id: str,
        destination: Path,
        built_in_source: ActivitySource,
        runtime: RuntimeCatalogue,
    ) -> None:
        final_source = ActivitySource(
            self.developer_root,
            trust=PackageTrust.DEVELOPER_UNSIGNED,
            source_id="greia-developer-remote",
        )
        registry = ActivityRegistry((built_in_source, final_source), runtime)
        for manifest_path in sorted(self.developer_root.glob("*/activity.toml")):
            root = manifest_path.parent.resolve()
            if root == destination.resolve(strict=False):
                continue
            registration = registry.validate_registration(root, final_source)
            identities = {
                registration.manifest.activity_id,
                *registration.manifest.legacy_ids,
            }
            if activity_id in identities:
                raise ValueError(f"Activity identity collision: {activity_id}")

    @staticmethod
    def _discard_tree(path: Path) -> None:
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
        elif path.exists():
            shutil.rmtree(path)

    @staticmethod
    def _paths_overlap(left: Path, right: Path) -> bool:
        return left == right or left in right.parents or right in left.parents


def _posix_pid_alive(pid: int) -> bool:
    if os.name != "posix":
        raise RuntimeError("POSIX PID probing is unavailable on this host")
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


__all__ = ["SimulatorWorkspace"]
