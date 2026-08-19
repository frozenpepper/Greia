"""Isolated, portable simulator workspace built from real Greia state services."""

from __future__ import annotations

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


@dataclass(slots=True)
class SimulatorWorkspace:
    """Own synthetic-device state without mutating or racing the Greia checkout."""

    repo_root: Path
    state_root: Path
    _lock_fd: int | None = field(default=None, init=False, repr=False)

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
        self.state_root.mkdir(parents=True, exist_ok=True)
        self._ensure_metadata(allow_repo_rebind=allow_repo_rebind)
        for path in (
            self.profiles_root,
            self.run_root,
            self.developer_root,
            self.package_root,
            self.media_root,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def acquire_lock(self) -> None:
        """Take the workspace's cross-platform single-writer lease."""

        self.ensure()
        if self._lock_fd is not None:
            return
        payload = json.dumps(
            {
                "pid": os.getpid(),
                "repo_root": str(self.repo_root),
                "schema_version": _WORKSPACE_SCHEMA_VERSION,
            },
            sort_keys=True,
        ).encode("utf-8")
        for attempt in range(2):
            try:
                descriptor = os.open(
                    self.lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError:
                if attempt or not self._discard_stale_lock():
                    raise RuntimeError(
                        "simulator workspace is already in use; choose another --state-dir"
                    )
                continue
            try:
                os.write(descriptor, payload)
                os.fsync(descriptor)
            except Exception:
                os.close(descriptor)
                self.lock_path.unlink(missing_ok=True)
                raise
            self._lock_fd = descriptor
            return
        raise RuntimeError("could not acquire simulator workspace lock")

    def release_lock(self) -> None:
        descriptor = self._lock_fd
        self._lock_fd = None
        if descriptor is not None:
            try:
                os.close(descriptor)
            finally:
                self.lock_path.unlink(missing_ok=True)

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
            "GREIA_SKIP_BOOT_HANDOFF": "1",
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
        """Write a named profile's real Greia UI preference."""

        store = self.profile_store()
        context = store.context(profile_id)
        preferences = UiPreferencesStore(context.customization_dir).set_interface_size(value)
        return preferences.interface_size

    def load_activity(self, source: Path):
        """Safely stage and atomically publish one developer Activity folder."""

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
            registrations = staging_registry.discover_registrations()
            registration = next(
                (
                    item
                    for item in registrations
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
                final_registrations = final_registry.discover_registrations()
                final = next(
                    (
                        item
                        for item in final_registrations
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
            if not published and destination is not None and previous.exists() and not destination.exists():
                os.replace(previous, destination)
            shutil.rmtree(staging_parent, ignore_errors=True)

    def install_activity_package(self, archive: Path) -> Any:
        """Exercise the canonical Parent-approved package transaction locally.

        Import is deliberately lazy so non-package simulator functionality can
        remain portable on hosts where the canonical package lock backend is not
        available. There is never a simulator-only extraction fallback.
        """

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
            if not isinstance(current, dict) or current.get("schema_version") != _WORKSPACE_SCHEMA_VERSION:
                raise RuntimeError("simulator workspace schema is incompatible")
            current_root = current.get("repo_root")
            if current_root != str(self.repo_root) and not allow_repo_rebind:
                raise RuntimeError(
                    "simulator workspace belongs to another Greia checkout; "
                    "use another --state-dir or --rebind-state deliberately"
                )
            if current_root == str(self.repo_root):
                return
        temporary = self.metadata_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.metadata_path)

    def _discard_stale_lock(self) -> bool:
        try:
            raw = json.loads(self.lock_path.read_text(encoding="utf-8"))
            pid = int(raw.get("pid", -1)) if isinstance(raw, dict) else -1
        except (OSError, ValueError, TypeError):
            pid = -1
        if pid > 0 and _pid_alive(pid):
            return False
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass
        return True

    def _inspect_development_tree(
        self,
        source: Path,
        runtime: RuntimeCatalogue,
    ) -> tuple[_TreeEntry, ...]:
        """Create a finite lstat snapshot before any managed copy occurs."""

        entries: list[_TreeEntry] = []
        total = 0
        for current_raw, dirnames, filenames in os.walk(source, topdown=True, followlinks=False):
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
                    raise ValueError(f"Activity source has a non-directory tree entry: {path}")
                if name.casefold() in runtime.forbidden_path_names:
                    raise ValueError(f"forbidden package directory: {name}")
                kept_dirs.append(name)
                entries.append(
                    _TreeEntry(
                        path.relative_to(source),
                        True,
                        0,
                        metadata.st_mode,
                        metadata.st_dev,
                        metadata.st_ino,
                    )
                )
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
                entries.append(
                    _TreeEntry(
                        path.relative_to(source),
                        False,
                        metadata.st_size,
                        metadata.st_mode,
                        metadata.st_dev,
                        metadata.st_ino,
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
            if (
                metadata.st_dev != entry.device
                or metadata.st_ino != entry.inode
                or stat.S_IFMT(metadata.st_mode) != stat.S_IFMT(entry.mode)
                or (not entry.is_dir and metadata.st_size != entry.size)
            ):
                raise ValueError(f"Activity source changed while staging: {origin}")
            if stat.S_ISLNK(metadata.st_mode):
                raise ValueError(f"Activity source symlinks are forbidden: {origin}")
            if entry.is_dir:
                target.mkdir(parents=True, exist_ok=False)
                os.chmod(target, 0o755)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            flags = os.O_RDONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(origin, flags)
            try:
                opened = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(opened.st_mode)
                    or opened.st_dev != entry.device
                    or opened.st_ino != entry.inode
                    or opened.st_size != entry.size
                ):
                    raise ValueError(f"Activity source changed while staging: {origin}")
                with os.fdopen(descriptor, "rb", closefd=False) as source_handle, target.open("xb") as sink:
                    remaining = entry.size
                    while remaining:
                        chunk = source_handle.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise ValueError(f"Activity source file ended while staging: {origin}")
                        sink.write(chunk)
                        copied += len(chunk)
                        remaining -= len(chunk)
                        if copied > runtime.maximum_activity_bytes:
                            raise ValueError("Activity source exceeded platform size while staging")
                    if source_handle.read(1):
                        raise ValueError(f"Activity source file grew while staging: {origin}")
                os.chmod(target, 0o644)
            finally:
                os.close(descriptor)

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
        for registration in registry.discover_registrations():
            if registration.manifest.root == destination.resolve(strict=False):
                continue
            identities = {registration.manifest.activity_id, *registration.manifest.legacy_ids}
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


def _pid_alive(pid: int) -> bool:
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
