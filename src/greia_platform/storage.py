from __future__ import annotations

import json
import math
import os
import shutil
import tempfile
import tomllib
import unicodedata
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Mapping

from .creation_capacity import VolumeBudget, VolumeSpaceError
from .profiles import ProfileContext


class StorageError(RuntimeError):
    """Base error for Greia-owned durable Activity storage."""


class StorageQuotaExceeded(StorageError):
    pass


class StorageMigrationRequired(StorageError):
    def __init__(self, stored_schema: int, requested_schema: int):
        self.stored_schema = stored_schema
        self.requested_schema = requested_schema
        super().__init__(
            f"storage schema migration required: {stored_schema} -> {requested_schema}"
        )


class StorageSchemaTooNew(StorageError):
    def __init__(self, stored_schema: int, requested_schema: int):
        self.stored_schema = stored_schema
        self.requested_schema = requested_schema
        super().__init__(
            f"stored schema {stored_schema} is newer than requested schema {requested_schema}"
        )


@dataclass(frozen=True, slots=True)
class StoragePolicy:
    policy_schema_version: int
    namespace_quota_bytes: int
    max_kv_bytes: int
    max_kv_value_bytes: int
    max_key_bytes: int
    max_file_bytes: int
    max_files: int
    max_path_bytes: int
    protected_free_bytes: int
    max_rollback_snapshots: int
    namespace_quota_fraction: float = 0.0

    def effective_namespace_quota_bytes(self, total_volume_bytes: int) -> int:
        if total_volume_bytes < 1:
            raise StorageError("storage volume size must be positive")
        proportional = int(total_volume_bytes * self.namespace_quota_fraction)
        return max(self.namespace_quota_bytes, proportional)

    @classmethod
    def load(cls, path: Path) -> "StoragePolicy":
        try:
            with path.resolve(strict=True).open("rb") as handle:
                raw = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise StorageError(f"invalid storage policy {path}: {exc}") from exc
        policy = cls(
            policy_schema_version=_integer(raw, "schema_version", minimum=1),
            namespace_quota_bytes=_integer(raw, "namespace_quota_bytes", minimum=4096),
            max_kv_bytes=_integer(raw, "max_kv_bytes", minimum=1024),
            max_kv_value_bytes=_integer(raw, "max_kv_value_bytes", minimum=128),
            max_key_bytes=_integer(raw, "max_key_bytes", minimum=8, maximum=4096),
            max_file_bytes=_integer(raw, "max_file_bytes", minimum=1024),
            max_files=_integer(raw, "max_files", minimum=1, maximum=100_000),
            max_path_bytes=_integer(raw, "max_path_bytes", minimum=32, maximum=4096),
            protected_free_bytes=_integer(raw, "protected_free_bytes", minimum=0),
            max_rollback_snapshots=_integer(
                raw, "max_rollback_snapshots", minimum=0, maximum=16
            ),
            namespace_quota_fraction=_fraction(
                raw,
                "namespace_quota_fraction",
                default=0.0,
            ),
        )
        if policy.max_kv_bytes > policy.namespace_quota_bytes:
            raise StorageError("max_kv_bytes exceeds namespace quota")
        if policy.max_kv_value_bytes > policy.max_kv_bytes:
            raise StorageError("max_kv_value_bytes exceeds KV quota")
        if policy.max_file_bytes > policy.namespace_quota_bytes:
            raise StorageError("max_file_bytes exceeds namespace quota")
        return policy


@dataclass(frozen=True, slots=True)
class StorageMetadata:
    format_version: int
    activity_id: str
    save_schema_version: int
    created_at: str
    updated_at: str
    last_checkpoint_at: str | None
    last_checkpoint_token: str | None
    last_writer_package_version: str

    @classmethod
    def create(
        cls, activity_id: str, schema_version: int, package_version: str
    ) -> "StorageMetadata":
        now = _utc_now()
        return cls(
            format_version=1,
            activity_id=activity_id,
            save_schema_version=schema_version,
            created_at=now,
            updated_at=now,
            last_checkpoint_at=None,
            last_checkpoint_token=None,
            last_writer_package_version=package_version,
        )

    @classmethod
    def from_json(cls, raw: object) -> "StorageMetadata":
        if not isinstance(raw, dict):
            raise StorageError("storage metadata must be a JSON object")
        try:
            metadata = cls(
                format_version=_json_integer(raw, "format_version", minimum=1),
                activity_id=_json_string(raw, "activity_id"),
                save_schema_version=_json_integer(raw, "save_schema_version", minimum=1),
                created_at=_json_string(raw, "created_at"),
                updated_at=_json_string(raw, "updated_at"),
                last_checkpoint_at=_json_optional_string(raw, "last_checkpoint_at"),
                last_checkpoint_token=_json_optional_string(raw, "last_checkpoint_token"),
                last_writer_package_version=_json_string(raw, "last_writer_package_version"),
            )
        except (KeyError, TypeError, ValueError, StorageError) as exc:
            raise StorageError("storage metadata is incomplete or invalid") from exc
        if metadata.format_version != 1:
            raise StorageError("unsupported storage metadata format")
        if metadata.save_schema_version < 1:
            raise StorageError("save schema version must be positive")
        _validate_activity_id(metadata.activity_id)
        return metadata

    def as_dict(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "activity_id": self.activity_id,
            "save_schema_version": self.save_schema_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_checkpoint_at": self.last_checkpoint_at,
            "last_checkpoint_token": self.last_checkpoint_token,
            "last_writer_package_version": self.last_writer_package_version,
        }


@dataclass(frozen=True, slots=True)
class StorageInfo:
    activity_id: str
    schema_version: int
    quota_bytes: int
    used_bytes: int
    kv_bytes: int
    file_bytes: int
    file_count: int
    last_checkpoint_at: str | None
    last_checkpoint_token: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "activity_id": self.activity_id,
            "schema_version": self.schema_version,
            "quota_bytes": self.quota_bytes,
            "used_bytes": self.used_bytes,
            "kv_bytes": self.kv_bytes,
            "file_bytes": self.file_bytes,
            "file_count": self.file_count,
            "last_checkpoint_at": self.last_checkpoint_at,
            "last_checkpoint_token": self.last_checkpoint_token,
        }


class ActivityStorage:
    """Platform-owned logical storage for one `(profile_id, activity_id)` pair.

    The physical root must not be mounted into the Activity sandbox. Activities
    use a broker/client API, while package update/backup code can call this
    service directly from trusted Greia processes.
    """

    METADATA_NAME = "metadata.json"
    KV_NAME = "kv.json"
    FILES_NAME = "files"
    LOCK_NAME = ".storage.lock"

    def __init__(
        self,
        root: Path,
        activity_id: str,
        policy: StoragePolicy,
        *,
        protected_root: Path,
        volume_budget: VolumeBudget | None = None,
    ):
        self.root = root.resolve(strict=False)
        self.activity_id = _validate_activity_id(activity_id)
        self.policy = policy
        self.protected_root = protected_root.resolve(strict=False)
        self.volume_budget = volume_budget or VolumeBudget()
        self.metadata_path = self.root / self.METADATA_NAME
        self.kv_path = self.root / self.KV_NAME
        self.files_root = self.root / self.FILES_NAME
        self.lock_path = self.root / self.LOCK_NAME

    @property
    def metadata(self) -> StorageMetadata:
        with self._lock():
            return self._read_metadata_unlocked()

    def kv_get(self, key: str, default: object = None) -> object:
        normalized = self._validate_key(key)
        with self._lock():
            return self._read_kv_unlocked().get(normalized, default)

    def kv_set(self, key: str, value: object) -> None:
        normalized = self._validate_key(key)
        normalized_value = _normalize_json_value(value)
        encoded_value = _encode_json(normalized_value)
        if len(encoded_value) > self.policy.max_kv_value_bytes:
            raise StorageQuotaExceeded("KV value exceeds per-value limit")
        with self._lock():
            kv = self._read_kv_unlocked()
            kv[normalized] = normalized_value
            payload = _encode_json(kv)
            if len(payload) > self.policy.max_kv_bytes:
                raise StorageQuotaExceeded("KV state exceeds KV quota")
            self._check_total_quota_unlocked(kv_bytes=len(payload))
            self._write_managed_atomic_unlocked(
                self.kv_path, payload, mode=0o660
            )
            self._touch_metadata_unlocked()

    def kv_delete(self, key: str) -> bool:
        normalized = self._validate_key(key)
        with self._lock():
            kv = self._read_kv_unlocked()
            if normalized not in kv:
                return False
            del kv[normalized]
            self._write_managed_atomic_unlocked(
                self.kv_path, _encode_json(kv), mode=0o660
            )
            self._touch_metadata_unlocked()
            return True

    def kv_list(self, prefix: str | None = None) -> tuple[str, ...]:
        if prefix is not None:
            prefix = self._validate_key_prefix(prefix)
        with self._lock():
            keys = sorted(self._read_kv_unlocked())
        if prefix is None:
            return tuple(keys)
        return tuple(key for key in keys if key.startswith(prefix))

    def file_read(self, name: str) -> bytes:
        target = self._file_path(name)
        with self._lock():
            if target.is_symlink():
                raise StorageError("private file path may not be a symbolic link")
            try:
                size = target.stat().st_size
                if size > self.policy.max_file_bytes:
                    raise StorageError("private file exceeds configured file-size limit")
                return target.read_bytes()
            except FileNotFoundError as exc:
                raise StorageError("private file does not exist") from exc
            except OSError as exc:
                raise StorageError(f"cannot read private file: {exc}") from exc

    def file_write_atomic(self, name: str, payload: bytes) -> None:
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise StorageError("private file payload must be bytes")
        data = bytes(payload)
        if len(data) > self.policy.max_file_bytes:
            raise StorageQuotaExceeded("private file exceeds per-file limit")
        target = self._file_path(name)
        with self._lock():
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink():
                raise StorageError("private file path may not be a symbolic link")
            file_count = self._file_count_unlocked(excluding=target if target.exists() else None)
            if not target.exists() and file_count >= self.policy.max_files:
                raise StorageQuotaExceeded("private file count limit reached")
            self._check_total_quota_unlocked(
                replacement_path=target,
                replacement_bytes=len(data),
            )
            self._write_managed_atomic_unlocked(target, data, mode=0o660)
            self._touch_metadata_unlocked()

    def file_delete(self, name: str) -> bool:
        target = self._file_path(name)
        with self._lock():
            if target.is_symlink():
                raise StorageError("private file path may not be a symbolic link")
            try:
                target.unlink()
            except FileNotFoundError:
                return False
            except IsADirectoryError as exc:
                raise StorageError("private file name refers to a directory") from exc
            self._remove_empty_parents(target.parent)
            self._touch_metadata_unlocked()
            return True

    def file_list(self, prefix: str | None = None) -> tuple[str, ...]:
        normalized_prefix = _validate_relative_name(prefix, self.policy) if prefix else None
        with self._lock():
            if not self.files_root.exists():
                return ()
            names: list[str] = []
            for path in self.files_root.rglob("*"):
                if path.is_symlink():
                    raise StorageError("private storage contains a symbolic link")
                if path.is_file():
                    relative = path.relative_to(self.files_root).as_posix()
                    if normalized_prefix is None or relative.startswith(normalized_prefix):
                        names.append(relative)
            return tuple(sorted(names))

    def info(self) -> StorageInfo:
        with self._lock():
            metadata = self._read_metadata_unlocked()
            kv_bytes = self.kv_path.stat().st_size if self.kv_path.exists() else 0
            file_bytes, file_count = self._files_usage_unlocked()
            return StorageInfo(
                activity_id=self.activity_id,
                schema_version=metadata.save_schema_version,
                quota_bytes=self._effective_namespace_quota_bytes(),
                used_bytes=kv_bytes + file_bytes,
                kv_bytes=kv_bytes,
                file_bytes=file_bytes,
                file_count=file_count,
                last_checkpoint_at=metadata.last_checkpoint_at,
                last_checkpoint_token=metadata.last_checkpoint_token,
            )

    def checkpoint(self) -> str:
        with self._lock():
            metadata = self._read_metadata_unlocked()
            token = uuid.uuid4().hex
            now = _utc_now()
            self._write_metadata_unlocked(
                replace(
                    metadata,
                    updated_at=now,
                    last_checkpoint_at=now,
                    last_checkpoint_token=token,
                )
            )
            return token

    def validate_namespace(self) -> None:
        """Fail closed when an existing namespace violates current storage policy.

        Opening durable child state must never silently grandfather symlinks,
        oversized files, excess file counts, malformed KV state, or total data
        beyond the namespace quota. The protected free-space reserve is enforced
        only on growth; low free space must not make existing saves unreadable.
        """

        with self._lock():
            self._read_metadata_unlocked()
            kv = self._read_kv_unlocked()
            kv_bytes = len(_encode_json(kv))
            if kv_bytes > self.policy.max_kv_bytes:
                raise StorageError("KV state exceeds configured KV limit")
            file_bytes, _ = self._files_usage_unlocked()
            if kv_bytes + file_bytes > self._effective_namespace_quota_bytes():
                raise StorageError("Activity storage namespace exceeds configured quota")

    def _read_metadata_unlocked(self) -> StorageMetadata:
        try:
            raw = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise StorageError("storage metadata is missing") from exc
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StorageError("storage metadata is unreadable") from exc
        metadata = StorageMetadata.from_json(raw)
        if metadata.activity_id != self.activity_id:
            raise StorageError("storage metadata Activity ID mismatch")
        return metadata

    def _write_metadata_unlocked(self, metadata: StorageMetadata) -> None:
        self._write_managed_atomic_unlocked(
            self.metadata_path,
            _encode_json(metadata.as_dict()),
            mode=0o660,
        )

    def _touch_metadata_unlocked(self) -> None:
        metadata = self._read_metadata_unlocked()
        self._write_metadata_unlocked(replace(metadata, updated_at=_utc_now()))

    def _read_kv_unlocked(self) -> dict[str, object]:
        try:
            if self.kv_path.exists() and self.kv_path.stat().st_size > self.policy.max_kv_bytes:
                raise StorageError("KV state exceeds configured KV limit")
            raw = json.loads(self.kv_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StorageError("KV state is unreadable") from exc
        if not isinstance(raw, dict) or not all(isinstance(key, str) for key in raw):
            raise StorageError("KV state must be a JSON object")
        normalized: dict[str, object] = {}
        for key, value in raw.items():
            normalized_key = self._validate_key(key)
            if normalized_key in normalized and normalized_key != key:
                raise StorageError("KV state contains colliding normalized keys")
            normalized[normalized_key] = _normalize_json_value(value)
        return normalized

    def _validate_key(self, key: str) -> str:
        if not isinstance(key, str):
            raise StorageError("storage key must be text")
        normalized = unicodedata.normalize("NFC", key).strip()
        encoded = normalized.encode("utf-8")
        if not normalized or len(encoded) > self.policy.max_key_bytes:
            raise StorageError("storage key has invalid length")
        if any(character in "/\\\x00\r\n" for character in normalized):
            raise StorageError("storage key contains a forbidden character")
        if any(unicodedata.category(character).startswith("C") for character in normalized):
            raise StorageError("storage key contains a control character")
        return normalized

    def _validate_key_prefix(self, prefix: str) -> str:
        if prefix == "":
            return ""
        return self._validate_key(prefix)

    def _file_path(self, name: str) -> Path:
        normalized = _validate_relative_name(name, self.policy)
        target = self.files_root.joinpath(*normalized.split("/"))
        try:
            target.relative_to(self.files_root)
        except ValueError as exc:
            raise StorageError("private file path escaped storage root") from exc
        current = self.files_root
        for component in Path(normalized).parts[:-1]:
            current = current / component
            if current.is_symlink():
                raise StorageError("private file path contains a symbolic link")
        return target

    def _check_total_quota_unlocked(
        self,
        *,
        kv_bytes: int | None = None,
        replacement_path: Path | None = None,
        replacement_bytes: int | None = None,
    ) -> None:
        current_kv = self.kv_path.stat().st_size if self.kv_path.exists() else 0
        if kv_bytes is None:
            kv_bytes = current_kv
        file_bytes, _ = self._files_usage_unlocked()
        if replacement_path is not None and replacement_bytes is not None:
            try:
                old = replacement_path.stat().st_size
            except FileNotFoundError:
                old = 0
            file_bytes = file_bytes - old + replacement_bytes
        total = kv_bytes + file_bytes
        if total > self._effective_namespace_quota_bytes():
            raise StorageQuotaExceeded("Activity storage namespace quota exceeded")

    def _effective_namespace_quota_bytes(self) -> int:
        try:
            usage = self.volume_budget.usage(self.protected_root)
        except OSError as exc:
            raise StorageError("cannot measure storage volume capacity") from exc
        return self.policy.effective_namespace_quota_bytes(usage.total_bytes)

    def _write_managed_atomic_unlocked(
        self,
        target: Path,
        payload: bytes,
        *,
        mode: int,
    ) -> None:
        try:
            old_bytes = target.stat().st_size
        except FileNotFoundError:
            old_bytes = 0
        except OSError as exc:
            raise StorageError("cannot inspect existing storage file") from exc
        final_growth = max(0, len(payload) - old_bytes)
        try:
            with self.volume_budget.write_reservation(
                self.protected_root,
                final_growth_bytes=final_growth,
                peak_additional_bytes=len(payload),
            ):
                _atomic_write_bytes(target, payload, mode=mode)
        except VolumeSpaceError as exc:
            raise StorageQuotaExceeded(
                "platform child-data headroom would be violated"
            ) from exc

    def _files_usage_unlocked(self) -> tuple[int, int]:
        total = 0
        count = 0
        if not self.files_root.exists():
            return total, count
        for path in self.files_root.rglob("*"):
            if path.is_symlink():
                raise StorageError("private storage contains a symbolic link")
            if path.is_file():
                size = path.stat().st_size
                if size > self.policy.max_file_bytes:
                    raise StorageError("private storage contains an oversized file")
                total += size
                count += 1
                if count > self.policy.max_files:
                    raise StorageError("private storage exceeds configured file-count limit")
        return total, count

    def _file_count_unlocked(self, *, excluding: Path | None = None) -> int:
        _, count = self._files_usage_unlocked()
        if excluding is not None and excluding.exists() and excluding.is_file():
            return max(0, count - 1)
        return count

    def _remove_empty_parents(self, start: Path) -> None:
        current = start
        while current != self.files_root:
            try:
                current.rmdir()
            except OSError:
                return
            current = current.parent

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self.root.mkdir(parents=True, exist_ok=True)
        if self.root.is_symlink() or not self.root.is_dir():
            raise StorageError("storage namespace root is not a real directory")
        if self.lock_path.is_symlink():
            raise StorageError("storage lock may not be a symbolic link")
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(self.lock_path, flags, 0o660)
        except OSError as exc:
            raise StorageError("cannot open storage lock safely") from exc
        with os.fdopen(descriptor, "a+b", closefd=True) as handle:
            try:
                os.fchmod(handle.fileno(), 0o660)
            except OSError as exc:
                raise StorageError("cannot secure storage lock") from exc
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            except (ImportError, OSError):
                pass
            try:
                yield
            finally:
                try:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                except (ImportError, OSError):
                    pass


class ActivityStorageService:
    """Factory/transaction owner for Greia durable Activity namespaces."""

    ROLLBACK_ROOT_NAME = ".storage-rollbacks"
    WORKING_ROOT_NAME = ".storage-working"

    def __init__(
        self,
        policy: StoragePolicy,
        *,
        volume_budget: VolumeBudget | None = None,
    ):
        self.policy = policy
        self.volume_budget = volume_budget or VolumeBudget()

    def open(
        self,
        profile: ProfileContext,
        activity_id: str,
        *,
        schema_version: int,
        package_version: str,
    ) -> ActivityStorage:
        _validate_schema_version(schema_version)
        root = profile.activity_storage_dir(activity_id)
        storage = ActivityStorage(
            root,
            activity_id,
            self.policy,
            protected_root=profile.root,
            volume_budget=self.volume_budget,
        )
        self._initialize_if_needed(storage, schema_version, package_version)
        metadata = storage.metadata
        storage.validate_namespace()
        if metadata.save_schema_version < schema_version:
            raise StorageMigrationRequired(metadata.save_schema_version, schema_version)
        if metadata.save_schema_version > schema_version:
            raise StorageSchemaTooNew(metadata.save_schema_version, schema_version)
        if metadata.last_writer_package_version != package_version:
            with storage._lock():
                current = storage._read_metadata_unlocked()
                storage._write_metadata_unlocked(
                    replace(
                        current,
                        updated_at=_utc_now(),
                        last_writer_package_version=package_version,
                    )
                )
        return storage

    def begin_migration(
        self,
        profile: ProfileContext,
        activity_id: str,
        *,
        target_schema_version: int,
        package_version: str,
    ) -> "StorageMigrationTransaction":
        _validate_schema_version(target_schema_version)
        active_root = profile.activity_storage_dir(activity_id)
        active = ActivityStorage(
            active_root,
            activity_id,
            self.policy,
            protected_root=profile.root,
            volume_budget=self.volume_budget,
        )
        if not active.metadata_path.exists():
            raise StorageError("cannot migrate an uninitialized storage namespace")
        metadata = active.metadata
        if metadata.save_schema_version >= target_schema_version:
            raise StorageError("migration target must be newer than stored schema")

        transaction_id = uuid.uuid4().hex
        working_parent = profile.root / self.WORKING_ROOT_NAME / activity_id
        working_root = working_parent / transaction_id
        rollback_parent = profile.root / self.ROLLBACK_ROOT_NAME / activity_id
        for path in (working_parent, rollback_parent):
            path.mkdir(parents=True, exist_ok=True)
            if path.is_symlink():
                raise StorageError("storage migration root may not be a symbolic link")
            os.chmod(path, 0o770)
        if working_root.exists():
            raise StorageError("storage migration working directory already exists")
        active_bytes = _directory_bytes(active_root)
        try:
            with self.volume_budget.write_reservation(
                profile.root,
                final_growth_bytes=active_bytes,
                peak_additional_bytes=active_bytes,
            ):
                with active._lock():
                    shutil.copytree(active_root, working_root, symlinks=False)
        except VolumeSpaceError as exc:
            raise StorageQuotaExceeded(
                "storage migration would violate platform child-data headroom"
            ) from exc
        working = ActivityStorage(
            working_root,
            activity_id,
            self.policy,
            protected_root=profile.root,
            volume_budget=self.volume_budget,
        )
        with working._lock():
            copied = working._read_metadata_unlocked()
            working._write_metadata_unlocked(
                replace(
                    copied,
                    save_schema_version=target_schema_version,
                    updated_at=_utc_now(),
                    last_writer_package_version=package_version,
                )
            )
        return StorageMigrationTransaction(
            service=self,
            profile=profile,
            activity_id=activity_id,
            source_schema_version=metadata.save_schema_version,
            target_schema_version=target_schema_version,
            package_version=package_version,
            active_root=active_root,
            working_root=working_root,
            rollback_parent=rollback_parent,
            working=working,
        )

    def _initialize_if_needed(
        self,
        storage: ActivityStorage,
        schema_version: int,
        package_version: str,
    ) -> None:
        storage.root.mkdir(parents=True, exist_ok=True)
        if storage.root.is_symlink():
            raise StorageError("storage namespace root may not be a symbolic link")
        os.chmod(storage.root, 0o770)
        with storage._lock():
            storage.files_root.mkdir(parents=True, exist_ok=True)
            os.chmod(storage.files_root, 0o770)
            if storage.metadata_path.exists():
                return
            if any(
                path.name not in {storage.LOCK_NAME, storage.FILES_NAME}
                for path in storage.root.iterdir()
            ):
                raise StorageError("uninitialized storage namespace contains unexpected data")
            metadata = StorageMetadata.create(
                storage.activity_id, schema_version, package_version
            )
            storage._write_metadata_unlocked(metadata)
            storage._write_managed_atomic_unlocked(
                storage.kv_path, b"{}", mode=0o660
            )

    def _prune_rollbacks(self, rollback_parent: Path) -> None:
        snapshots = sorted(
            (path for path in rollback_parent.iterdir() if path.is_dir()),
            key=lambda path: path.stat().st_mtime_ns,
        )
        keep = self.policy.max_rollback_snapshots
        for path in snapshots[: max(0, len(snapshots) - keep)]:
            shutil.rmtree(path)


@dataclass(slots=True)
class StorageMigrationTransaction:
    service: ActivityStorageService
    profile: ProfileContext
    activity_id: str
    source_schema_version: int
    target_schema_version: int
    package_version: str
    active_root: Path
    working_root: Path
    rollback_parent: Path
    working: ActivityStorage
    committed: bool = False
    rolled_back: bool = False

    def commit(self) -> Path:
        if self.committed or self.rolled_back:
            raise StorageError("storage migration transaction is already closed")
        info = self.working.info()
        metadata = self.working.metadata
        if metadata.save_schema_version != self.target_schema_version:
            raise StorageError("migration working copy has wrong target schema")
        if info.used_bytes > info.quota_bytes:
            raise StorageQuotaExceeded("migrated storage exceeds quota")

        snapshot_name = f"schema-{self.source_schema_version}-{uuid.uuid4().hex}"
        snapshot = self.rollback_parent / snapshot_name
        moved_active = False
        try:
            self.active_root.rename(snapshot)
            moved_active = True
            self.working_root.rename(self.active_root)
        except OSError as exc:
            if moved_active and not self.active_root.exists() and snapshot.exists():
                try:
                    snapshot.rename(self.active_root)
                except OSError:
                    pass
            raise StorageError("cannot atomically activate migrated storage") from exc
        self.committed = True
        self.service._prune_rollbacks(self.rollback_parent)
        return snapshot

    def rollback(self) -> None:
        if self.committed:
            raise StorageError("committed storage migration cannot be rolled back")
        if self.rolled_back:
            return
        shutil.rmtree(self.working_root, ignore_errors=True)
        self.rolled_back = True

    def __enter__(self) -> "StorageMigrationTransaction":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if not self.committed:
            self.rollback()
        return False


def _validate_activity_id(activity_id: str) -> str:
    if not isinstance(activity_id, str) or not activity_id:
        raise StorageError("Activity ID must be non-empty text")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
    if not activity_id[0].isalnum() or any(character not in allowed for character in activity_id):
        raise StorageError("Activity ID is not safe for storage")
    return activity_id


def _validate_schema_version(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise StorageError("storage schema version must be a positive integer")
    return value


def _validate_relative_name(name: str | None, policy: StoragePolicy) -> str:
    if not isinstance(name, str):
        raise StorageError("private file name must be text")
    normalized = unicodedata.normalize("NFC", name).strip()
    if not normalized or normalized.startswith("/") or "\\" in normalized:
        raise StorageError("private file name must be a relative portable path")
    if len(normalized.encode("utf-8")) > policy.max_path_bytes:
        raise StorageError("private file path is too long")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
    parts = normalized.split("/")
    if any(
        not part
        or part in {".", ".."}
        or any(character not in allowed for character in part)
        for part in parts
    ):
        raise StorageError("private file path contains a non-portable component")
    return "/".join(parts)


def _normalize_json_value(value: object, *, depth: int = 0) -> object:
    if depth > 32:
        raise StorageError("JSON value nesting is too deep")
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise StorageError("JSON numbers must be finite")
        return value
    if isinstance(value, (list, tuple)):
        return [_normalize_json_value(item, depth=depth + 1) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise StorageError("JSON object keys must be strings")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                raise StorageError("JSON object contains colliding normalized keys")
            normalized[normalized_key] = _normalize_json_value(
                item, depth=depth + 1
            )
        return normalized
    raise StorageError("storage value is not JSON-compatible")


def _encode_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise StorageError("value is not portable JSON") from exc


def _atomic_write_bytes(path: Path, payload: bytes, *, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def _directory_bytes(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        if path.is_symlink():
            raise StorageError("storage namespace contains a symbolic link")
        if path.is_file():
            total += path.stat().st_size
    return total


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _json_string(container: Mapping[str, object], key: str) -> str:
    value = container[key]
    if not isinstance(value, str) or not value:
        raise StorageError(f"{key} must be non-empty text")
    return value


def _json_optional_string(container: Mapping[str, object], key: str) -> str | None:
    value = container.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise StorageError(f"{key} must be null or non-empty text")
    return value


def _json_integer(
    container: Mapping[str, object],
    key: str,
    *,
    minimum: int,
) -> int:
    value = container[key]
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise StorageError(f"{key} must be an integer >= {minimum}")
    return value


def _fraction(
    container: Mapping[str, object],
    key: str,
    *,
    default: float,
) -> float:
    value = container.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StorageError(f"{key} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise StorageError(f"{key} must be between 0 and 1")
    return result


def _integer(
    container: Mapping[str, object],
    key: str,
    *,
    minimum: int,
    maximum: int | None = None,
) -> int:
    value = container.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise StorageError(f"{key} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        upper = f" and <= {maximum}" if maximum is not None else ""
        raise StorageError(f"{key} must be >= {minimum}{upper}")
    return value
