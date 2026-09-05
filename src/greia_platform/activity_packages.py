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
    ActivityRegistration,
    ActivityRegistry,
    ActivityValidationError,
    RuntimeCatalogue,
    package_digest,
)
from .activity_assets import package_icon_path
from .activity_index import (
    ActivityIndex,
    ActivityIndexLoader,
    build_index,
    runtime_policy_fingerprint,
)
from .activity_tree_cleanup import scrub_activity_tree
from .trust import ActivitySource, PackageTrust


MAX_ARCHIVE_ENTRIES = 512
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_PATH_CHARACTERS = 220
MAX_COMPRESSION_RATIO = 200
_INSTALL_LOCK_NAME = ".install.lock"

# T34 active-set generation layout (consumed by T36 launcher composition).
# Each generation is a complete versioned active set:
#   generations/<generation-id>/activities/<activity-id>/...
#   generations/<generation-id>/index.json
# The platform-owned `active` path is an indirection file whose entire
# content is "<generation-id>\n", swapped atomically via tmp+replace so a
# normal boot never observes a mixed generation. No symlinks are used
# anywhere in this layout, and in particular never inside Activity packages.
GENERATIONS_DIRNAME = "generations"
ACTIVE_POINTER_NAME = "active"
ACTIVITIES_DIRNAME = "activities"
ACTIVE_INDEX_FILENAME = "index.json"
_INITIAL_GENERATION_ID = "gen-000001"


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


@dataclass(frozen=True, slots=True)
class ActivityUninstallReceipt:
    """Result of deactivating one parent-installed Activity package.

    Child/profile data is deliberately outside the package state tree and is
    never touched by uninstall. This typed result makes that product contract
    explicit to Parent clients.
    """

    activity_id: str
    version: str
    package_digest: str
    source_id: str
    profile_data_preserved: bool = True

    def as_json_dict(self) -> dict[str, str | bool]:
        return {
            "activity_id": self.activity_id,
            "version": self.version,
            "package_digest": self.package_digest,
            "source_id": self.source_id,
            "profile_data_preserved": self.profile_data_preserved,
        }


class ActivityPackageService:
    """Bounded authority for parent-approved local Activity packages.

    The service owns installation and removal of the *parent package source*.
    Built-in Activities remain outside this state tree and cannot be removed by
    this service. Uninstall removes package code while deliberately preserving
    all profile-scoped Activity data. In-place package update/replacement and
    rollback remain separate R10 work.

    Package mutations are serialized twice: a small in-process lock avoids
    redundant contenders inside one service object, while a private ``flock``
    file under the package state root serializes separate package-service
    processes that share the same authoritative store.
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
        self.generations_root = self.state_root / GENERATIONS_DIRNAME
        self._active_pointer = self.state_root / ACTIVE_POINTER_NAME
        self.versions_root = self.state_root / "versions"
        self.staging_root = self.state_root / "staging"
        self.receipts_root = self.state_root / "receipts"
        self.runtime = RuntimeCatalogue.load(runtime_catalogue)
        self.built_in_root = built_in_root.resolve() if built_in_root else None
        self._install_lock = threading.Lock()

    @property
    def active_root(self) -> Path:
        """Resolved activities directory of the current active generation.

        This stays a directory of active packages so existing callers keep
        working; the atomic publish boundary is the generation directory
        plus the platform-owned ``active`` pointer file beneath it.
        """
        return self._resolve_active_activities_root()

    @property
    def active_pointer(self) -> Path:
        """Platform-owned indirection file naming the active generation."""
        return self._active_pointer

    @classmethod
    def from_environment(cls) -> "ActivityPackageService":
        default_root = Path(__file__).resolve().parents[2]
        configured_os_root = Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os")).resolve()
        if (configured_os_root / "runtime" / "child-runtime.toml").is_file():
            os_root = configured_os_root
        elif (default_root / "runtime" / "child-runtime.toml").is_file():
            os_root = default_root
        else:
            os_root = configured_os_root
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
                    # A legacy `active` directory (pre-generation layout) is
                    # migrated under the same exclusive lock before the
                    # install builds its new generation on top.
                    self._migrate_legacy_active_dir_locked()
                    return self._install_archive_serialized(archive_path)
        except ActivityPackageError:
            raise
        except OSError as exc:
            raise ActivityPackageError(
                f"could not establish Activity package transaction lock: {exc}"
            ) from exc

    def uninstall(self, activity_id: str) -> ActivityUninstallReceipt:
        """Remove one parent-installed Activity package, preserving child data.

        Identity is resolved through the validated parent-package registry rather
        than interpolated into a filesystem path from the request. Built-in
        Activities therefore never enter this removal path.
        """

        if not isinstance(activity_id, str) or not activity_id.strip():
            raise ActivityPackageError("Activity id is required")
        try:
            self._ensure_roots()
            with self._install_lock:
                with self._process_install_lock():
                    self._migrate_legacy_active_dir_locked()
                    return self._uninstall_serialized(activity_id.strip())
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

    # -- T34 active-set generation boundary --------------------------------

    def active_generation_id(self) -> str | None:
        """Return the active generation id, or None when no generation exists yet.

        A legacy pre-generation ``active`` directory reports None so callers
        can distinguish the unmigrated layout from a versioned generation.
        """
        try:
            return self._read_pointer_id()
        except FileNotFoundError:
            return None

    def active_index_path(self) -> Path | None:
        """Return the active generation index file, or None for legacy/missing."""
        generation_id = self.active_generation_id()
        if generation_id is None:
            return None
        return self._generation_index_path(generation_id)

    def active_source(self) -> ActivitySource:
        """Return the configured parent-package source bound to the active set."""
        return ActivitySource(
            self._resolve_active_activities_root(),
            PackageTrust.PARENT_TRUSTED_UNSIGNED,
            self.SOURCE_ID,
        )

    def load_active_registrations(self) -> tuple[ActivityRegistration, ...]:
        """Load the active set through its versioned index when available.

        The index path never re-reads package trees and never recomputes
        digests; it reconstructs the already-validated registrations recorded
        at publish time. A legacy layout (or a missing index) falls back to
        a fail-closed validated registry scan so hygiene is never bypassed.
        A corrupt index raises rather than serving an unvalidated set.
        """
        activities_root = self._resolve_active_activities_root()
        index_path = self.active_index_path()
        if index_path is not None and index_path.is_file():
            loader = ActivityIndexLoader.from_runtime(
                ActivitySource(
                    activities_root,
                    PackageTrust.PARENT_TRUSTED_UNSIGNED,
                    self.SOURCE_ID,
                ),
                self.runtime,
            )
            return loader.load_file(index_path)
        registry = ActivityRegistry(
            (
                ActivitySource(
                    activities_root,
                    PackageTrust.PARENT_TRUSTED_UNSIGNED,
                    self.SOURCE_ID,
                ),
            ),
            self.runtime,
        )
        return registry.discover_registrations()

    def _generation_dir(self, generation_id: str) -> Path:
        return self.generations_root / generation_id

    def _generation_activities_path(self, generation_id: str) -> Path:
        return self._generation_dir(generation_id) / ACTIVITIES_DIRNAME

    def _generation_index_path(self, generation_id: str) -> Path:
        return self._generation_dir(generation_id) / ACTIVE_INDEX_FILENAME

    @staticmethod
    def _require_safe_generation_id(generation_id: str) -> None:
        if (
            not isinstance(generation_id, str)
            or not generation_id
            or "/" in generation_id
            or "\\" in generation_id
            or generation_id in {".", ".."}
            or generation_id.startswith(".")
            or any(part in {".", ".."} for part in PurePosixPath(generation_id).parts)
        ):
            raise ActivityPackageError(
                f"Activity generation id is not a safe portable name: {generation_id!r}"
            )

    def _read_pointer_id(self) -> str | None:
        pointer = self._active_pointer
        if pointer.is_dir():
            return None
        try:
            text = pointer.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise
        except OSError as exc:
            raise ActivityPackageError(
                f"cannot read the active Activity generation: {exc}"
            ) from exc
        generation_id = text.strip()
        if not generation_id:
            raise ActivityPackageError("the active Activity generation is empty")
        self._require_safe_generation_id(generation_id)
        return generation_id

    def _resolve_active_activities_root(self) -> Path:
        try:
            generation_id = self._read_pointer_id()
        except FileNotFoundError:
            generation_id = None
        if generation_id is not None:
            return self._generation_activities_path(generation_id)
        legacy = self._active_pointer
        if legacy.is_dir():
            return legacy
        # Fresh or crash-window state without a pointer: serve the latest
        # complete generation when one exists so boot never observes a mix.
        latest = self._latest_generation_id()
        if latest is not None:
            return self._generation_activities_path(latest)
        return self._generation_activities_path(_INITIAL_GENERATION_ID)

    def _latest_generation_id(self) -> str | None:
        if not self.generations_root.is_dir():
            return None
        candidates: list[str] = []
        try:
            entries = list(self.generations_root.iterdir())
        except OSError:
            return None
        for entry in entries:
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            try:
                self._require_safe_generation_id(entry.name)
            except ActivityPackageError:
                continue
            if (entry / ACTIVITIES_DIRNAME).is_dir():
                candidates.append(entry.name)
        if not candidates:
            return None
        return sorted(candidates)[-1]

    def _next_generation_id(self) -> str:
        latest = self._latest_generation_id()
        if latest is None:
            return _INITIAL_GENERATION_ID
        suffix = latest.rsplit("-", 1)[-1] if "-" in latest else ""
        try:
            number = int(suffix)
            width = len(suffix)
        except ValueError:
            number = 0
            width = 6
        return f"gen-{number + 1:0{max(width, 6)}d}"

    def _write_active_pointer(self, generation_id: str) -> None:
        self._require_safe_generation_id(generation_id)
        pointer = self._active_pointer
        if pointer.is_dir():
            raise ActivityPackageError(
                "the active Activity path is still a legacy directory"
            )
        temporary_handle, temporary_name = tempfile.mkstemp(
            prefix=pointer.name + ".", dir=str(pointer.parent)
        )
        temporary = Path(temporary_name)
        try:
            with open(temporary_handle, "w", encoding="utf-8") as handle:
                handle.write(generation_id + "\n")
            os.chmod(temporary, 0o644)
            os.replace(temporary, pointer)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    def _publish_generation(self, generation_id: str) -> None:
        """Swap the platform-owned pointer to a fully staged generation.

        The generation directory (activities plus index) is complete before
        this single atomic file replace, so a fault anywhere earlier still
        exposes the previous complete generation.
        """
        target = self._generation_dir(generation_id)
        if not (target / ACTIVITIES_DIRNAME).is_dir():
            raise ActivityPackageError(
                f"Activity generation {generation_id!r} is not staged"
            )
        if not (target / ACTIVE_INDEX_FILENAME).is_file():
            raise ActivityPackageError(
                f"Activity generation {generation_id!r} has no index"
            )
        self._write_active_pointer(generation_id)

    def _list_generation_package_ids(self, activities_root: Path) -> list[str]:
        if not activities_root.is_dir():
            return []
        names: list[str] = []
        for entry in sorted(activities_root.iterdir(), key=lambda item: item.name):
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                names.append(entry.name)
        return names

    def _hardlink_tree(self, source: Path, destination: Path) -> None:
        shutil.copytree(source, destination, copy_function=os.link)
        self._make_tree_read_only(destination)

    def _stage_generation(
        self,
        generation_id: str,
        *,
        carry_ids: list[str],
        extra_trees: dict[str, Path],
    ) -> Path:
        """Stage a complete new generation directory (not yet published)."""
        self._require_safe_generation_id(generation_id)
        current_activities = self._resolve_active_activities_root()
        staging = Path(
            tempfile.mkdtemp(
                prefix=f".staging-{generation_id}-",
                dir=str(self.generations_root),
            )
        )
        staging_activities = staging / ACTIVITIES_DIRNAME
        staging_activities.mkdir(parents=True, exist_ok=True)
        os.chmod(staging_activities, 0o755)
        try:
            for activity_id in carry_ids:
                if activity_id in extra_trees:
                    continue
                source = current_activities / activity_id
                if not source.is_dir():
                    raise ActivityPackageError(
                        f"previously active Activity {activity_id!r} is missing"
                    )
                self._hardlink_tree(source, staging_activities / activity_id)
            for activity_id, source in extra_trees.items():
                destination = staging_activities / activity_id
                if destination.exists():
                    raise ActivityPackageError(
                        f"Activity {activity_id} is already installed; update is not enabled yet"
                    )
                self._hardlink_tree(source, destination)
            registrations = self._validate_generation_activities(staging_activities)
            parent_source = ActivitySource(
                staging_activities,
                PackageTrust.PARENT_TRUSTED_UNSIGNED,
                self.SOURCE_ID,
            )
            parent_registrations = tuple(
                item for item in registrations if item.source_id == self.SOURCE_ID
            )
            index = build_index(
                parent_registrations, source=parent_source, runtime=self.runtime
            )
            index.write_file(staging / ACTIVE_INDEX_FILENAME)
            os.replace(staging, self._generation_dir(generation_id))
            return self._generation_dir(generation_id)
        except BaseException:
            self._discard_private_tree(staging)
            raise

    def _validate_generation_activities(
        self, activities_root: Path
    ) -> tuple[ActivityRegistration, ...]:
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
                activities_root,
                PackageTrust.PARENT_TRUSTED_UNSIGNED,
                self.SOURCE_ID,
            )
        )
        registry = ActivityRegistry(tuple(sources), self.runtime)
        try:
            return registry.discover_registrations()
        except ActivityValidationError as exc:
            raise ActivityPackageError(str(exc)) from exc

    def _discard_old_generations(self, keep_id: str) -> None:
        if not self.generations_root.is_dir():
            return
        for entry in list(self.generations_root.iterdir()):
            if entry.name.startswith("."):
                continue
            if entry.name == keep_id or not entry.is_dir():
                continue
            try:
                self._require_safe_generation_id(entry.name)
            except ActivityPackageError:
                continue
            self._discard_private_tree(entry)

    def _migrate_legacy_active_dir_locked(self) -> None:
        legacy = self._active_pointer
        if not legacy.is_dir():
            return
        if self._latest_generation_id() is not None:
            # Generations already exist; a stray legacy directory must not
            # shadow the pointer. This state should not occur in normal
            # operation; fail closed rather than guessing which set is live.
            raise ActivityPackageError(
                "legacy Activity active directory shadows versioned generations"
            )
        generation_id = _INITIAL_GENERATION_ID
        staging = Path(
            tempfile.mkdtemp(
                prefix=f".staging-{generation_id}-",
                dir=str(self.generations_root),
            )
        )
        staging_activities = staging / ACTIVITIES_DIRNAME
        staging_activities.mkdir(parents=True, exist_ok=True)
        os.chmod(staging_activities, 0o755)
        try:
            for activity_id in self._list_generation_package_ids(legacy):
                self._hardlink_tree(
                    legacy / activity_id, staging_activities / activity_id
                )
            registrations = self._validate_generation_activities(staging_activities)
            parent_source = ActivitySource(
                staging_activities,
                PackageTrust.PARENT_TRUSTED_UNSIGNED,
                self.SOURCE_ID,
            )
            parent_registrations = tuple(
                item for item in registrations if item.source_id == self.SOURCE_ID
            )
            index = build_index(
                parent_registrations, source=parent_source, runtime=self.runtime
            )
            index.write_file(staging / ACTIVE_INDEX_FILENAME)
            os.replace(staging, self._generation_dir(generation_id))
        except BaseException:
            self._discard_private_tree(staging)
            raise
        backup = self.state_root / ".active-legacy-backup"
        if backup.exists():
            self._discard_private_tree(backup)
        os.rename(legacy, backup)
        try:
            self._write_active_pointer(generation_id)
        except BaseException:
            os.rename(backup, legacy)
            raise
        self._discard_private_tree(backup)

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
        try:
            self._extract_bounded_archive(archive_path, package_root)
            # 2A trust boundary: staged-tree hygiene lives inside this
            # activation transaction, not in a recurring boot scrub. Remove
            # only curated regenerable host/editor noise before registry
            # validation so noisy-but-valid packages install while symlinks,
            # executable bits and forbidden content still fail validation
            # below and the previous active set stays untouched.
            staged_scrub = scrub_activity_tree(package_root)
            if staged_scrub.failed_removals:
                raise ActivityPackageError(
                    "staged Activity package could not be sanitized"
                )
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
                if not immutable.is_dir() or package_digest(immutable) != digest:
                    raise ActivityPackageError(
                        "stored immutable Activity version does not match its package digest"
                    )
                shutil.rmtree(package_root)
            else:
                os.replace(package_root, immutable)
                self._make_tree_read_only(immutable)

            # T34 atomic generation publish: the complete new active set
            # (previous packages carried by hardlink plus the new immutable
            # package) is staged, validated and indexed in a new generation
            # directory. The single atomic pointer swap below publishes the
            # set and its index together; any fault before it leaves the
            # previous complete generation untouched.
            current_activities = self._resolve_active_activities_root()
            carry_ids = self._list_generation_package_ids(current_activities)
            if manifest.activity_id in carry_ids:
                raise ActivityPackageError(
                    f"Activity {manifest.activity_id} is already installed; update is not enabled yet"
                )
            generation_id = self._next_generation_id()
            staged_generation: Path | None = None
            receipt = ActivityInstallReceipt(
                activity_id=manifest.activity_id,
                version=manifest.version,
                package_digest=digest,
                package_trust=PackageTrust.PARENT_TRUSTED_UNSIGNED,
                source_id=self.SOURCE_ID,
            )
            try:
                staged_generation = self._stage_generation(
                    generation_id,
                    carry_ids=carry_ids,
                    extra_trees={manifest.activity_id: immutable},
                )
                self._write_receipt(receipt)
            except BaseException:
                if staged_generation is not None:
                    self._discard_private_tree(staged_generation)
                else:
                    candidate = self._generation_dir(generation_id)
                    if candidate.exists():
                        self._discard_private_tree(candidate)
                self._receipt_path(manifest.activity_id).unlink(missing_ok=True)
                raise
            try:
                self._publish_generation(generation_id)
            except BaseException as exc:
                self._discard_private_tree(self._generation_dir(generation_id))
                self._receipt_path(manifest.activity_id).unlink(missing_ok=True)
                raise ActivityPackageError(
                    f"could not publish Activity generation {generation_id!r}: {exc}"
                ) from exc
            self._discard_old_generations(generation_id)
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
            self._discard_private_tree(stage_parent)

    def _uninstall_serialized(self, activity_id: str) -> ActivityUninstallReceipt:
        current_activities = self._resolve_active_activities_root()
        registry = ActivityRegistry(
            (
                ActivitySource(
                    current_activities,
                    PackageTrust.PARENT_TRUSTED_UNSIGNED,
                    self.SOURCE_ID,
                ),
            ),
            self.runtime,
        )
        try:
            registration = next(
                item
                for item in registry.discover_registrations()
                if item.manifest.activity_id == activity_id
            )
        except StopIteration as exc:
            raise ActivityPackageError(
                f"Activity {activity_id} is not a removable parent-installed Activity"
            ) from exc
        except ActivityValidationError as exc:
            raise ActivityPackageError(str(exc)) from exc

        active = registration.manifest.root.resolve()
        if active.parent != current_activities.resolve():
            raise ActivityPackageError("installed Activity path is outside the package source")
        digest = registration.package_digest
        version = registration.manifest.version

        # T34 atomic generation publish for removal: stage the complete
        # remaining set plus its new index, then swap the pointer. The swap
        # is the commit point; child saves live under profile-scoped storage
        # elsewhere and are never part of this transaction.
        carry_ids = [
            name
            for name in self._list_generation_package_ids(current_activities)
            if name != activity_id
        ]
        generation_id = self._next_generation_id()
        try:
            self._stage_generation(
                generation_id, carry_ids=carry_ids, extra_trees={}
            )
        except BaseException:
            candidate = self._generation_dir(generation_id)
            if candidate.exists():
                self._discard_private_tree(candidate)
            raise
        try:
            self._publish_generation(generation_id)
        except BaseException as exc:
            self._discard_private_tree(self._generation_dir(generation_id))
            raise ActivityPackageError(
                f"could not publish Activity generation {generation_id!r}: {exc}"
            ) from exc

        self._receipt_path(activity_id).unlink(missing_ok=True)
        self._discard_private_tree(self.versions_root / activity_id)
        self._discard_old_generations(generation_id)
        return ActivityUninstallReceipt(
            activity_id=activity_id,
            version=version,
            package_digest=digest,
            source_id=self.SOURCE_ID,
        )

    def _ensure_roots(self) -> None:
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.generations_root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.generations_root, 0o755)
        for path, mode in (
            (self.versions_root, 0o700),
            (self.staging_root, 0o700),
            (self.receipts_root, 0o700),
        ):
            path.mkdir(parents=True, exist_ok=True)
            os.chmod(path, mode)
        # An existing legacy `active` directory is left for the locked
        # migration step; a missing pointer with no generations gets an
        # initial empty generation so readers always resolve a directory.
        # This runs outside the install locks, so concurrent first-time
        # callers must converge: a lost creation race is success, not error.
        if self._active_pointer.is_dir() or self._active_pointer.is_file():
            return
        if self._latest_generation_id() is not None:
            return
        staging = Path(
            tempfile.mkdtemp(
                prefix=f".staging-{_INITIAL_GENERATION_ID}-",
                dir=str(self.generations_root),
            )
        )
        staging_activities = staging / ACTIVITIES_DIRNAME
        staging_activities.mkdir(parents=True, exist_ok=True)
        os.chmod(staging_activities, 0o755)
        try:
            ActivityIndex(
                platform_activity_api_version=self.runtime.api_version,
                source_id=self.SOURCE_ID,
                package_trust=PackageTrust.PARENT_TRUSTED_UNSIGNED,
                generated_from_policy_version=self.runtime.api_version,
                generated_from_policy_hash=runtime_policy_fingerprint(self.runtime),
                registrations=(),
            ).write_file(staging / ACTIVE_INDEX_FILENAME)
            try:
                os.replace(staging, self._generation_dir(_INITIAL_GENERATION_ID))
            except OSError:
                # A concurrent first-time caller published the initial
                # generation first; our staging is residue, their set is live.
                self._discard_private_tree(staging)
                if self._latest_generation_id() is None:
                    raise
                if not self._active_pointer.exists():
                    try:
                        latest = self._latest_generation_id()
                        if latest is not None:
                            self._write_active_pointer(latest)
                    except OSError:
                        pass
                return
            try:
                self._write_active_pointer(_INITIAL_GENERATION_ID)
            except OSError:
                # The generation directory is already published; a pointer
                # written concurrently names the same initial generation.
                if self.active_generation_id() != _INITIAL_GENERATION_ID:
                    raise
        except BaseException:
            self._discard_private_tree(staging)
            raise

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
        package_icon_path(staged.manifest)

        staged_id = staged.manifest.activity_id
        if self.active_root is not None and (self.active_root / staged_id).exists():
            raise ActivityPackageError(
                f"Activity {staged_id} is already installed; update is not enabled yet"
            )

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
        """Remove a service-owned tree that may contain read-only entries."""

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
