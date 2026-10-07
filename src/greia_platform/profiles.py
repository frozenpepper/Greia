from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import shutil
import stat
import tempfile
import tomllib
import unicodedata
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterator, Mapping

from .activity_discovery import ChallengePreference


class ProfileError(ValueError):
    """Raised when child-profile data violates the bounded platform contract."""


@dataclass(frozen=True, slots=True)
class ProfilePolicy:
    schema_version: int
    max_profiles: int
    max_name_characters: int
    max_secret_characters: int
    secret_iterations: int
    default_name: str
    default_avatar: str
    default_mask_secret: bool
    avatars: tuple[str, ...]

    @classmethod
    def default_safe(cls) -> "ProfilePolicy":
        """Built-in immutable fallback policy for profile defaults."""
        return cls(
            schema_version=1,
            max_profiles=8,
            max_name_characters=16,
            max_secret_characters=32,
            secret_iterations=100_000,
            default_name="Greia",
            default_avatar="rainbow",
            default_mask_secret=True,
            avatars=(
                "rainbow",
                "yellow_star",
                "green_leaf",
                "blue_droplet",
                "pink_heart",
                "orange_sun",
                "purple_flower",
                "red_apple",
            ),
        )

    @classmethod
    def load(cls, path: Path) -> "ProfilePolicy":
        try:
            if not path.is_file() or path.stat().st_size == 0:
                return cls.default_safe()
            with path.resolve(strict=True).open("rb") as handle:
                raw = tomllib.load(handle)
            policy = cls(
                schema_version=_integer(raw, "schema_version", minimum=1),
                max_profiles=_integer(raw, "max_profiles", minimum=1, maximum=16),
                max_name_characters=_integer(raw, "max_name_characters", minimum=1, maximum=64),
                max_secret_characters=_integer(raw, "max_secret_characters", minimum=1, maximum=128),
                secret_iterations=_integer(raw, "secret_iterations", minimum=10_000, maximum=2_000_000),
                default_name=_text(raw, "default_name"),
                default_avatar=_text(raw, "default_avatar"),
                default_mask_secret=_boolean(raw, "default_mask_secret"),
                avatars=tuple(_string_list(raw, "avatars")),
            )
            if len(set(policy.avatars)) != len(policy.avatars):
                return cls.default_safe()
            policy.validate_avatar(policy.default_avatar)
            policy.validate_name(policy.default_name)
            return policy
        except Exception:
            return cls.default_safe()

    def validate_avatar(self, avatar_id: str) -> str:
        if avatar_id not in self.avatars:
            raise ProfileError(f"unknown profile avatar: {avatar_id}")
        return avatar_id

    def validate_name(self, display_name: str) -> str:
        if not isinstance(display_name, str):
            raise ProfileError("profile name must be text")
        normalized = unicodedata.normalize("NFC", display_name).strip()
        if not normalized:
            raise ProfileError("profile name must not be empty")
        if len(normalized) > self.max_name_characters:
            raise ProfileError(
                f"profile name may contain at most {self.max_name_characters} characters"
            )
        if any(unicodedata.category(character).startswith("C") for character in normalized):
            raise ProfileError("profile name contains unsupported control characters")
        return normalized

    def validate_secret(self, secret: str) -> str:
        if not isinstance(secret, str):
            raise ProfileError("profile secret must be text")
        if len(secret) > self.max_secret_characters:
            raise ProfileError(
                f"profile secret may contain at most {self.max_secret_characters} characters"
            )
        if any(character in "\r\n\x00" for character in secret):
            raise ProfileError("profile secret contains unsupported characters")
        return secret

    @staticmethod
    def validate_approximate_age(value: int | None) -> int | None:
        if value is None:
            return None
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 18:
            raise ProfileError("approximate child age must be an integer from 1 through 18")
        return value

    @staticmethod
    def validate_challenge_preference(
        value: ChallengePreference | str,
    ) -> ChallengePreference:
        if isinstance(value, ChallengePreference):
            return value
        try:
            return ChallengePreference(value)
        except (TypeError, ValueError) as exc:
            raise ProfileError("unsupported child challenge preference") from exc


@dataclass(frozen=True, slots=True)
class SecretDigest:
    salt: str
    digest: str
    iterations: int

    @classmethod
    def create(cls, secret: str, iterations: int) -> "SecretDigest":
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations)
        return cls(
            salt=base64.b64encode(salt).decode("ascii"),
            digest=base64.b64encode(digest).decode("ascii"),
            iterations=iterations,
        )

    def verify(self, secret: str) -> bool:
        try:
            salt = base64.b64decode(self.salt.encode("ascii"), validate=True)
            expected = base64.b64decode(self.digest.encode("ascii"), validate=True)
        except (ValueError, UnicodeEncodeError):
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", secret.encode("utf-8"), salt, self.iterations
        )
        return hmac.compare_digest(candidate, expected)

    def as_json_dict(self) -> dict[str, object]:
        return {
            "algorithm": "pbkdf2-sha256",
            "salt": self.salt,
            "digest": self.digest,
            "iterations": self.iterations,
        }


@dataclass(frozen=True, slots=True)
class ChildProfile:
    profile_id: str
    display_name: str
    avatar_id: str
    secret_digest: SecretDigest | None
    mask_secret: bool
    approximate_age: int | None = None
    challenge_preference: ChallengePreference = ChallengePreference.AUTOMATIC
    # Child-facing UI words default to CAPITAL letters because target children
    # learn capitals first. Purely presentational; a parent may disable it.
    uppercase_text: bool = True

    @property
    def has_secret(self) -> bool:
        return self.secret_digest is not None

    def public_dict(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "avatar_id": self.avatar_id,
            "has_secret": self.has_secret,
            "mask_secret": self.mask_secret,
            "approximate_age": self.approximate_age,
            "challenge_preference": self.challenge_preference.value,
            "uppercase_text": self.uppercase_text,
        }

    def storage_dict(self) -> dict[str, object]:
        payload = self.public_dict()
        payload["secret"] = (
            self.secret_digest.as_json_dict() if self.secret_digest is not None else None
        )
        return payload


@dataclass(frozen=True, slots=True)
class ProfileContext:
    profile: ChildProfile
    root: Path
    customization_dir: Path
    activities_dir: Path
    storage_dir: Path
    progress_dir: Path

    @property
    def activity_discovery_policy_path(self) -> Path:
        return self.root / "activity-discovery.json"

    def activity_data_dir(self, activity_id: str) -> Path:
        if not activity_id or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for character in activity_id):
            raise ProfileError("unsafe activity identifier")
        _ensure_managed_directory(self.activities_dir, self.root, mode=0o2770)
        target = self.activities_dir / activity_id
        _ensure_managed_directory(target, self.root, mode=0o770)
        return target

    def activity_storage_dir(self, activity_id: str) -> Path:
        if not activity_id or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789._-"
            for character in activity_id
        ):
            raise ProfileError("unsafe activity identifier")
        _ensure_managed_directory(self.storage_dir, self.root, mode=0o2770)
        target = self.storage_dir / activity_id
        _ensure_managed_directory(target, self.root, mode=0o770)
        return target


class ProfileStore:
    """Atomic, bounded app-level child profiles over one unprivileged OS user."""

    REGISTRY_NAME = "profiles.json"
    BACKUP_NAME = "profiles.backup.json"
    LOCK_NAME = ".profiles.lock"

    def __init__(self, policy: ProfilePolicy, root: Path):
        self.policy = policy
        self.root = root.resolve()
        self.registry_path = self.root / self.REGISTRY_NAME
        self.backup_path = self.root / self.BACKUP_NAME
        self.data_root = self.root / "data"

    @classmethod
    def load(cls, policy_path: Path, root: Path) -> "ProfileStore":
        return cls(ProfilePolicy.load(policy_path), root)

    def ensure_initialized(self) -> tuple[ChildProfile, ...]:
        with self._mutation_lock():
            profiles = self._read_unlocked()
            if profiles:
                self._ensure_profile_directories(profiles)
                return profiles
            profile = self._new_profile(
                self.policy.default_name,
                self.policy.default_avatar,
                "",
                self.policy.default_mask_secret,
            )
            profiles = (profile,)
            self._commit_new_profile(profile, profiles)
            return profiles

    def list_profiles(self) -> tuple[ChildProfile, ...]:
        profiles = self._read_unlocked()
        if not profiles:
            return self.ensure_initialized()
        return profiles

    def get(self, profile_id: str) -> ChildProfile:
        _validate_profile_id(profile_id)
        for profile in self.list_profiles():
            if profile.profile_id == profile_id:
                return profile
        raise ProfileError("profile does not exist")

    def context(self, profile_id: str) -> ProfileContext:
        profile = self.get(profile_id)
        root = self.data_root / profile.profile_id
        context = ProfileContext(
            profile=profile,
            root=root,
            customization_dir=root / "customization",
            activities_dir=root / "activities",
            storage_dir=root / "storage",
            progress_dir=root / "progress",
        )
        self._ensure_context_directories(context)
        return context

    def create(
        self,
        display_name: str,
        avatar_id: str,
        *,
        secret: str = "",
        mask_secret: bool | None = None,
        approximate_age: int | None = None,
        challenge_preference: ChallengePreference | str = ChallengePreference.AUTOMATIC,
        uppercase_text: bool = True,
    ) -> ChildProfile:
        with self._mutation_lock():
            profiles = self._read_unlocked()
            if len(profiles) >= self.policy.max_profiles:
                raise ProfileError(f"at most {self.policy.max_profiles} child profiles are allowed")
            profile = self._new_profile(
                display_name,
                avatar_id,
                secret,
                self.policy.default_mask_secret if mask_secret is None else bool(mask_secret),
                approximate_age=approximate_age,
                challenge_preference=challenge_preference,
                uppercase_text=bool(uppercase_text),
            )
            updated = (*profiles, profile)
            self._commit_new_profile(profile, updated)
            return profile

    def update(
        self,
        profile_id: str,
        *,
        display_name: str | None = None,
        avatar_id: str | None = None,
        secret_action: str = "keep",
        secret: str = "",
        mask_secret: bool | None = None,
        approximate_age: int | None = None,
        clear_approximate_age: bool = False,
        challenge_preference: ChallengePreference | str | None = None,
        uppercase_text: bool | None = None,
    ) -> ChildProfile:
        _validate_profile_id(profile_id)
        if secret_action not in {"keep", "set", "clear"}:
            raise ProfileError("secret action must be keep, set, or clear")
        if clear_approximate_age and approximate_age is not None:
            raise ProfileError("cannot set and clear approximate age in one update")
        with self._mutation_lock():
            profiles = list(self._read_unlocked())
            for index, current in enumerate(profiles):
                if current.profile_id != profile_id:
                    continue
                digest = current.secret_digest
                if secret_action == "set":
                    validated_secret = self.policy.validate_secret(secret)
                    if not validated_secret:
                        raise ProfileError("set secret requires a non-empty value")
                    digest = SecretDigest.create(validated_secret, self.policy.secret_iterations)
                elif secret_action == "clear":
                    digest = None
                if clear_approximate_age:
                    resolved_age = None
                elif approximate_age is not None:
                    resolved_age = self.policy.validate_approximate_age(approximate_age)
                else:
                    resolved_age = current.approximate_age
                resolved_challenge = (
                    self.policy.validate_challenge_preference(challenge_preference)
                    if challenge_preference is not None
                    else current.challenge_preference
                )
                resolved_uppercase = (
                    current.uppercase_text if uppercase_text is None else bool(uppercase_text)
                )
                updated = replace(
                    current,
                    display_name=(
                        self.policy.validate_name(display_name)
                        if display_name is not None
                        else current.display_name
                    ),
                    avatar_id=(
                        self.policy.validate_avatar(avatar_id)
                        if avatar_id is not None
                        else current.avatar_id
                    ),
                    secret_digest=digest,
                    mask_secret=(current.mask_secret if mask_secret is None else bool(mask_secret)),
                    approximate_age=resolved_age,
                    challenge_preference=resolved_challenge,
                    uppercase_text=resolved_uppercase,
                )
                profiles[index] = updated
                self._write_unlocked(tuple(profiles))
                return updated
        raise ProfileError("profile does not exist")

    def set_avatar(self, profile_id: str, avatar_id: str) -> ChildProfile:
        return self.update(profile_id, avatar_id=avatar_id)

    def delete(self, profile_id: str) -> None:
        _validate_profile_id(profile_id)
        with self._mutation_lock():
            profiles = self._read_unlocked()
            if len(profiles) <= 1:
                raise ProfileError("the final child profile cannot be deleted")
            if not any(profile.profile_id == profile_id for profile in profiles):
                raise ProfileError("profile does not exist")
            target = self.data_root / profile_id
            if os.path.lexists(target):
                if target.is_symlink() or not target.is_dir():
                    raise ProfileError("profile data path is not a managed directory")
                resolved_root = self.data_root.resolve(strict=True)
                resolved_target = target.resolve(strict=True)
                if resolved_target.parent != resolved_root:
                    raise ProfileError("profile data path escaped the managed root")
            retained = tuple(profile for profile in profiles if profile.profile_id != profile_id)
            self._write_unlocked(retained)
            if target.exists():
                shutil.rmtree(target)

    def avatar_request_path(self, profile_id: str) -> Path:
        _validate_profile_id(profile_id)
        return self.data_root / profile_id / ".avatar-request.json"

    def consume_avatar_request(self, profile_id: str) -> ChildProfile | None:
        request_path = self.avatar_request_path(profile_id)
        try:
            if request_path.stat().st_size > 4096:
                raise ProfileError("avatar request is too large")
            raw = json.loads(request_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProfileError("avatar request is invalid") from exc
        finally:
            request_path.unlink(missing_ok=True)
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            raise ProfileError("avatar request schema is invalid")
        if raw.get("profile_id") != profile_id:
            raise ProfileError("avatar request does not match the active child")
        avatar_id = raw.get("avatar_id")
        if not isinstance(avatar_id, str):
            raise ProfileError("avatar request has no valid avatar")
        return self.set_avatar(profile_id, avatar_id)

    def verify_secret(self, profile_id: str, candidate: str) -> bool:
        profile = self.get(profile_id)
        if profile.secret_digest is None:
            return candidate == ""
        validated = self.policy.validate_secret(candidate)
        return profile.secret_digest.verify(validated)

    def _commit_new_profile(
        self,
        profile: ChildProfile,
        profiles: tuple[ChildProfile, ...],
    ) -> None:
        """Establish the shared directory contract before publishing a profile.

        A Parent-created profile must never become visible in profiles.json
        until its shared root and Parent-owned subdirectories are group-writable
        for the child. If directory preparation fails, remove only a directory
        created by this transaction and leave the registry unchanged.
        """

        profile_root = self.data_root / profile.profile_id
        existed_before = os.path.lexists(profile_root)
        try:
            self._ensure_profile_directories((profile,))
            self._write_unlocked(profiles)
        except BaseException:
            if (
                not existed_before
                and profile_root.exists()
                and not profile_root.is_symlink()
            ):
                shutil.rmtree(profile_root, ignore_errors=True)
            raise

    def _new_profile(
        self,
        display_name: str,
        avatar_id: str,
        secret: str,
        mask_secret: bool,
        *,
        approximate_age: int | None = None,
        challenge_preference: ChallengePreference | str = ChallengePreference.AUTOMATIC,
        uppercase_text: bool = True,
    ) -> ChildProfile:
        name = self.policy.validate_name(display_name)
        avatar = self.policy.validate_avatar(avatar_id)
        validated_secret = self.policy.validate_secret(secret)
        digest = (
            SecretDigest.create(validated_secret, self.policy.secret_iterations)
            if validated_secret
            else None
        )
        return ChildProfile(
            uuid.uuid4().hex,
            name,
            avatar,
            digest,
            bool(mask_secret),
            self.policy.validate_approximate_age(approximate_age),
            self.policy.validate_challenge_preference(challenge_preference),
            bool(uppercase_text),
        )

    def _read_unlocked(self) -> tuple[ChildProfile, ...]:
        try:
            raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return ()
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as primary_exc:
            try:
                raw = json.loads(self.backup_path.read_text(encoding="utf-8"))
            except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
                raise ProfileError(f"cannot read profile registry: {primary_exc}") from primary_exc
        if not isinstance(raw, dict) or raw.get("schema_version") != self.policy.schema_version:
            raise ProfileError("unsupported profile registry schema")
        entries = raw.get("profiles")
        if not isinstance(entries, list):
            raise ProfileError("profile registry profiles must be an array")
        if len(entries) > self.policy.max_profiles:
            raise ProfileError("profile registry exceeds the configured profile limit")
        profiles = tuple(self._parse_profile(entry) for entry in entries)
        ids = [profile.profile_id for profile in profiles]
        if len(set(ids)) != len(ids):
            raise ProfileError("duplicate profile identifier")
        return profiles

    def _parse_profile(self, raw: object) -> ChildProfile:
        if not isinstance(raw, dict):
            raise ProfileError("invalid profile entry")
        profile_id = raw.get("profile_id")
        display_name = raw.get("display_name")
        avatar_id = raw.get("avatar_id")
        mask_secret = raw.get("mask_secret", self.policy.default_mask_secret)
        approximate_age = raw.get("approximate_age")
        challenge_preference = raw.get(
            "challenge_preference", ChallengePreference.AUTOMATIC.value
        )
        uppercase_text = raw.get("uppercase_text", True)
        if not isinstance(profile_id, str):
            raise ProfileError("profile identifier must be text")
        _validate_profile_id(profile_id)
        if not isinstance(display_name, str) or not isinstance(avatar_id, str):
            raise ProfileError("profile name and avatar must be text")
        if not isinstance(mask_secret, bool):
            raise ProfileError("mask_secret must be a boolean")
        if not isinstance(uppercase_text, bool):
            raise ProfileError("uppercase_text must be a boolean")
        secret_raw = raw.get("secret")
        digest: SecretDigest | None = None
        if secret_raw is not None:
            if not isinstance(secret_raw, dict):
                raise ProfileError("profile secret record is invalid")
            if secret_raw.get("algorithm") != "pbkdf2-sha256":
                raise ProfileError("unsupported profile secret algorithm")
            salt = secret_raw.get("salt")
            encoded_digest = secret_raw.get("digest")
            iterations = secret_raw.get("iterations")
            if not isinstance(salt, str) or not isinstance(encoded_digest, str):
                raise ProfileError("profile secret digest is invalid")
            if (
                not isinstance(iterations, int)
                or isinstance(iterations, bool)
                or iterations < 10_000
                or iterations > 2_000_000
            ):
                raise ProfileError("profile secret iterations are invalid")
            try:
                decoded_salt = base64.b64decode(salt.encode("ascii"), validate=True)
                decoded_digest = base64.b64decode(
                    encoded_digest.encode("ascii"), validate=True
                )
            except (ValueError, UnicodeEncodeError) as exc:
                raise ProfileError("profile secret digest is invalid") from exc
            if len(decoded_salt) != 16 or len(decoded_digest) != hashlib.sha256().digest_size:
                raise ProfileError("profile secret digest has an invalid size")
            digest = SecretDigest(salt, encoded_digest, iterations)
        return ChildProfile(
            profile_id,
            self.policy.validate_name(display_name),
            self.policy.validate_avatar(avatar_id),
            digest,
            mask_secret,
            self.policy.validate_approximate_age(approximate_age),
            self.policy.validate_challenge_preference(challenge_preference),
            uppercase_text,
        )

    def _write_unlocked(self, profiles: tuple[ChildProfile, ...]) -> None:
        payload = {
            "schema_version": self.policy.schema_version,
            "profiles": [profile.storage_dict() for profile in profiles],
        }
        _atomic_write_json(self.registry_path, payload)
        try:
            _atomic_write_json(self.backup_path, payload)
        except OSError:
            pass

    def _ensure_profile_directories(self, profiles: tuple[ChildProfile, ...]) -> None:
        for profile in profiles:
            self._ensure_context_directories(
                ProfileContext(
                    profile=profile,
                    root=self.data_root / profile.profile_id,
                    customization_dir=self.data_root / profile.profile_id / "customization",
                    activities_dir=self.data_root / profile.profile_id / "activities",
                    storage_dir=self.data_root / profile.profile_id / "storage",
                    progress_dir=self.data_root / profile.profile_id / "progress",
                )
            )

    #: Directories the child opens and owns itself. The Parent service runs as
    #: greiapel, not root, so anything it creates here is greiapel-owned, and the
    #: child then cannot chmod it: the history store requires to own its own
    #: progress directory and refused to open a parent-owned one, killing the
    #: launcher the moment a profile was entered. These are deliberately not
    #: pre-created here; each owning service creates them as the child.
    CHILD_OWNED_DIRECTORY_NAMES = frozenset({"storage", "progress"})

    def _ensure_context_directories(self, context: ProfileContext) -> None:
        if self.data_root.is_symlink():
            raise ProfileError("profile data root may not be a symbolic link")
        self.data_root.mkdir(parents=True, exist_ok=True)
        if not self.data_root.is_dir():
            raise ProfileError("profile data root is not a directory")
        _ensure_directory_contract(
            self.data_root,
            reference_root=self.root,
            mode=0o2770,
        )
        for path in (
            context.root,
            context.customization_dir,
            context.activities_dir,
            context.storage_dir,
            context.progress_dir,
        ):
            if path.name in self.CHILD_OWNED_DIRECTORY_NAMES:
                # Still validated, never created. A symlink or a plain file here
                # is a tampering signal the Parent service must reject even
                # though the child is the one that will create it.
                if path.is_symlink():
                    raise ProfileError("managed profile path contains a symbolic link")
                if path.exists() and not path.is_dir():
                    raise ProfileError("managed profile path contains a non-directory")
                continue
            _ensure_managed_directory(path, self.data_root, mode=0o2770)

    @contextmanager
    def _mutation_lock(self) -> Iterator[None]:
        self.root.mkdir(parents=True, exist_ok=True)
        _ensure_directory_contract(
            self.root,
            reference_root=self.root,
            mode=0o2770,
        )
        lock_path = self.root / self.LOCK_NAME
        with lock_path.open("a+b") as handle:
            try:
                os.chmod(lock_path, 0o660)
            except PermissionError:
                pass
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


def _ensure_directory_contract(
    path: Path,
    *,
    reference_root: Path,
    mode: int,
) -> None:
    """Require one shared directory to match the managed group/mode contract."""

    try:
        reference = reference_root.stat()
        current = path.stat()
    except OSError as exc:
        raise ProfileError(f"managed profile directory is not statable: {path}: {exc}") from exc

    expected_gid = reference.st_gid
    actual_mode = stat.S_IMODE(current.st_mode)
    if actual_mode != mode:
        try:
            os.chmod(path, mode)
        except OSError as exc:
            raise ProfileError(
                f"managed profile directory mode is {actual_mode:04o}, "
                f"expected {mode:04o}, and chmod was refused: {path}"
            ) from exc
        try:
            current = path.stat()
        except OSError as exc:
            raise ProfileError(
                f"managed profile directory is not statable after chmod: {path}: {exc}"
            ) from exc
        actual_mode = stat.S_IMODE(current.st_mode)

    if current.st_gid != expected_gid:
        raise ProfileError(
            f"managed profile directory group is {current.st_gid}, "
            f"expected managed group {expected_gid}: {path}"
        )
    if actual_mode != mode:
        raise ProfileError(
            f"managed profile directory mode is {actual_mode:04o}, "
            f"expected {mode:04o}: {path}"
        )


def _ensure_managed_directory(path: Path, managed_root: Path, *, mode: int) -> None:
    try:
        relative = path.relative_to(managed_root)
    except ValueError as exc:
        raise ProfileError("managed profile path escaped its root") from exc
    current = managed_root
    if current.is_symlink() or (current.exists() and not current.is_dir()):
        raise ProfileError("managed profile root is not a real directory")
    current.mkdir(parents=True, exist_ok=True)
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise ProfileError("managed profile path contains a symbolic link")
        if current.exists():
            if not current.is_dir():
                raise ProfileError("managed profile path contains a non-directory")
        else:
            current.mkdir()
        _ensure_directory_contract(
            current,
            reference_root=managed_root,
            mode=mode,
        )


class ActiveProfileSession:
    """Runtime profile claim shared by launcher and parent mutations."""

    LOCK_SUFFIX = ".lock"

    def __init__(self, path: Path):
        self.path = path.resolve()
        self.lock_path = self.path.with_name(self.path.name + self.LOCK_SUFFIX)

    def activate(self, store: "ProfileStore", profile_id: str) -> ProfileContext:
        with self._mutation_lock():
            context = store.context(profile_id)
            self._write_unlocked(context.profile)
            return context

    def delete_inactive(self, store: "ProfileStore", profile_id: str) -> None:
        with self._mutation_lock():
            active = self._read_unlocked()
            if active and active.get("profile_id") == profile_id:
                raise ProfileError("switch away from this child before deleting the account")
            store.delete(profile_id)

    def write(self, profile: ChildProfile) -> None:
        with self._mutation_lock():
            self._write_unlocked(profile)

    def clear(self) -> None:
        with self._mutation_lock():
            self.path.unlink(missing_ok=True)

    def read(self) -> dict[str, object] | None:
        with self._mutation_lock():
            return self._read_unlocked()

    def _write_unlocked(self, profile: ChildProfile) -> None:
        _atomic_write_json(self.path, profile.public_dict())

    def _read_unlocked(self) -> dict[str, object] | None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None
        return {
            key: raw.get(key)
            for key in (
                "profile_id",
                "display_name",
                "avatar_id",
                "has_secret",
                "mask_secret",
                "approximate_age",
                "challenge_preference",
                "uppercase_text",
            )
        }

    @contextmanager
    def _mutation_lock(self) -> Iterator[None]:
        try:
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            handle = self.lock_path.open("a+b")
        except OSError:
            yield
            return

        with handle:
            try:
                os.chmod(self.lock_path, 0o660)
            except OSError:
                pass
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


def write_avatar_request(
    policy: ProfilePolicy,
    request_path: Path,
    profile_id: str,
    avatar_id: str,
) -> dict[str, object]:
    _validate_profile_id(profile_id)
    validated_avatar = policy.validate_avatar(avatar_id)
    payload: dict[str, object] = {
        "schema_version": 1,
        "profile_id": profile_id,
        "avatar_id": validated_avatar,
    }
    _atomic_write_json(request_path.resolve(), payload)
    return payload


def _validate_profile_id(profile_id: str) -> None:
    try:
        parsed = uuid.UUID(hex=profile_id)
    except (ValueError, AttributeError) as exc:
        raise ProfileError("invalid profile identifier") from exc
    if parsed.hex != profile_id:
        raise ProfileError("profile identifier must be canonical lowercase UUID hex")


def _atomic_write_json(path: Path, payload: Mapping[str, object]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o660)
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _integer(
    container: Mapping[str, object],
    key: str,
    *,
    minimum: int,
    maximum: int | None = None,
) -> int:
    value = container.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ProfileError(f"{key} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        raise ProfileError(f"{key} is outside the allowed range")
    return value


def _text(container: Mapping[str, object], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProfileError(f"{key} must be non-empty text")
    return value.strip()


def _boolean(container: Mapping[str, object], key: str) -> bool:
    value = container.get(key)
    if not isinstance(value, bool):
        raise ProfileError(f"{key} must be a boolean")
    return value


def _string_list(container: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = container.get(key)
    if not isinstance(value, list) or not value:
        raise ProfileError(f"{key} must be a non-empty array")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ProfileError(f"{key} contains invalid text")
    return tuple(item.strip() for item in value)