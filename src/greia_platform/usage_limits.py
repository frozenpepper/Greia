from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Iterator


class UsageLimitError(ValueError):
    """Raised when screen-time policy or accounting state is invalid."""


MAX_DAILY_MINUTES = 24 * 60


@dataclass(frozen=True, slots=True)
class UsageLimitPolicy:
    """A bounded daily Activity-time budget.

    ``daily_minutes=None`` means unlimited. The first implementation counts
    time while a child Activity owns the Greia Activity session; time spent on
    the launcher/profile chooser is deliberately not charged.
    """

    daily_minutes: int | None = None

    def __post_init__(self) -> None:
        if self.daily_minutes is None:
            return
        if (
            not isinstance(self.daily_minutes, int)
            or isinstance(self.daily_minutes, bool)
            or not 1 <= self.daily_minutes <= MAX_DAILY_MINUTES
        ):
            raise UsageLimitError(
                f"daily_minutes must be null or an integer from 1 through {MAX_DAILY_MINUTES}"
            )

    @property
    def limited(self) -> bool:
        return self.daily_minutes is not None

    @property
    def budget_seconds(self) -> int | None:
        return None if self.daily_minutes is None else self.daily_minutes * 60


@dataclass(frozen=True, slots=True)
class UsageLimitStatus:
    """Effective budget facts for one child profile on one Greia device."""

    accounting_date: date
    profile_id: str
    device_policy: UsageLimitPolicy
    profile_policy: UsageLimitPolicy
    device_used_seconds: int
    profile_used_seconds: int
    device_remaining_seconds: int | None
    profile_remaining_seconds: int | None
    effective_remaining_seconds: int | None

    @property
    def exhausted(self) -> bool:
        return self.effective_remaining_seconds == 0

    def public_dict(self) -> dict[str, object]:
        return {
            "date": self.accounting_date.isoformat(),
            "profile_id": self.profile_id,
            "device_daily_minutes": self.device_policy.daily_minutes,
            "profile_daily_minutes": self.profile_policy.daily_minutes,
            "device_used_seconds": self.device_used_seconds,
            "profile_used_seconds": self.profile_used_seconds,
            "device_remaining_seconds": self.device_remaining_seconds,
            "profile_remaining_seconds": self.profile_remaining_seconds,
            "effective_remaining_seconds": self.effective_remaining_seconds,
            "exhausted": self.exhausted,
            "counting_mode": "activity_time",
        }


@dataclass(frozen=True, slots=True)
class _UsageState:
    device_policy: UsageLimitPolicy
    profile_policies: tuple[tuple[str, UsageLimitPolicy], ...]
    latest_accounting_date: date | None
    device_usage: tuple[tuple[str, int], ...]
    profile_usage: tuple[tuple[str, tuple[tuple[str, int], ...]], ...]

    @classmethod
    def empty(cls) -> "_UsageState":
        return cls(UsageLimitPolicy(), (), None, (), ())

    def profile_policy(self, profile_id: str) -> UsageLimitPolicy:
        return dict(self.profile_policies).get(profile_id, UsageLimitPolicy())


StateMutation = Callable[[_UsageState], _UsageState]


class UsageLimitStore:
    """Atomic, inter-process-safe usage policy/accounting persistence.

    Parent policy updates and launcher accounting can originate in separate
    processes. Atomic replacement prevents torn JSON, while the adjacent lock
    serializes the complete read/modify/write transaction so neither writer can
    silently erase the other's change.
    """

    SCHEMA_VERSION = 1
    MAX_BYTES = 128 * 1024
    MAX_PROFILES = 32
    MAX_DAYS = 8
    LOCK_SUFFIX = ".lock"

    def __init__(self, path: Path):
        self.path = path
        self.lock_path = path.with_name(path.name + self.LOCK_SUFFIX)

    def read(self) -> _UsageState:
        with self._mutation_lock():
            return self._read_unlocked()

    def write(self, state: _UsageState) -> None:
        with self._mutation_lock():
            self._write_unlocked(state)

    def mutate(self, mutation: StateMutation) -> _UsageState:
        """Apply one serialized read/modify/write transaction and return it."""
        with self._mutation_lock():
            current = self._read_unlocked()
            updated = mutation(current)
            if not isinstance(updated, _UsageState):
                raise TypeError("usage-limit mutation must return _UsageState")
            self._write_unlocked(updated)
            return updated

    def _read_unlocked(self) -> _UsageState:
        try:
            if self.path.is_symlink():
                raise UsageLimitError("usage-limit state may not be a symlink")
            raw_bytes = self.path.read_bytes()
        except FileNotFoundError:
            return _UsageState.empty()
        except OSError as exc:
            raise UsageLimitError(f"cannot read usage-limit state: {exc}") from exc
        if len(raw_bytes) > self.MAX_BYTES:
            raise UsageLimitError("usage-limit state exceeds its size bound")
        try:
            raw = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UsageLimitError("usage-limit state is invalid JSON") from exc
        return self._parse(raw)

    def _write_unlocked(self, state: _UsageState) -> None:
        encoded = json.dumps(
            self._payload(state),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > self.MAX_BYTES:
            raise UsageLimitError("usage-limit state exceeds its size bound")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self.path.is_symlink():
            raise UsageLimitError("usage-limit state may not be a symlink")
        fd, temporary = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=str(self.path.parent)
        )
        temp_path = Path(temporary)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_path, 0o660)
            os.replace(temp_path, self.path)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    @contextmanager
    def _mutation_lock(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.path.parent, 0o2770)
        except PermissionError:
            pass
        if self.lock_path.is_symlink():
            raise UsageLimitError("usage-limit lock may not be a symlink")
        with self.lock_path.open("a+b") as handle:
            try:
                os.chmod(self.lock_path, 0o660)
            except PermissionError:
                pass
            try:
                import fcntl
            except ImportError:
                # Greia runtime and supported Unix authoring hosts provide
                # fcntl. Preserve a single-process fallback for other developer
                # hosts without pretending a failed POSIX lock was acquired.
                yield
                return
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            except OSError as exc:
                raise UsageLimitError(
                    "cannot acquire usage-limit state lock"
                ) from exc
            # Closing the file releases the advisory lock even when the body
            # raises, so an explicit unlock cannot mask the primary exception.
            yield

    def _parse(self, raw: object) -> _UsageState:
        if not isinstance(raw, dict) or raw.get("schema_version") != self.SCHEMA_VERSION:
            raise UsageLimitError("unsupported usage-limit state schema")
        device_policy = UsageLimitPolicy(
            _optional_minutes(raw.get("device_daily_minutes"))
        )
        raw_profile_policies = raw.get("profile_daily_minutes", {})
        if (
            not isinstance(raw_profile_policies, dict)
            or len(raw_profile_policies) > self.MAX_PROFILES
        ):
            raise UsageLimitError("invalid profile usage-limit policies")
        profile_policies: list[tuple[str, UsageLimitPolicy]] = []
        for profile_id, minutes in raw_profile_policies.items():
            _validate_profile_id(profile_id)
            profile_policies.append(
                (profile_id, UsageLimitPolicy(_optional_minutes(minutes)))
            )

        latest_raw = raw.get("latest_accounting_date")
        latest = _parse_date(latest_raw) if latest_raw is not None else None
        device_usage = _parse_usage_map(raw.get("device_usage", {}), self.MAX_DAYS)

        raw_profile_usage = raw.get("profile_usage", {})
        if (
            not isinstance(raw_profile_usage, dict)
            or len(raw_profile_usage) > self.MAX_PROFILES
        ):
            raise UsageLimitError("invalid profile usage accounting")
        profile_usage: list[tuple[str, tuple[tuple[str, int], ...]]] = []
        for profile_id, usage in raw_profile_usage.items():
            _validate_profile_id(profile_id)
            profile_usage.append(
                (profile_id, _parse_usage_map(usage, self.MAX_DAYS))
            )

        return _UsageState(
            device_policy=device_policy,
            profile_policies=tuple(sorted(profile_policies)),
            latest_accounting_date=latest,
            device_usage=device_usage,
            profile_usage=tuple(sorted(profile_usage)),
        )

    def _payload(self, state: _UsageState) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "device_daily_minutes": state.device_policy.daily_minutes,
            "profile_daily_minutes": {
                profile_id: policy.daily_minutes
                for profile_id, policy in state.profile_policies
            },
            "latest_accounting_date": (
                None
                if state.latest_accounting_date is None
                else state.latest_accounting_date.isoformat()
            ),
            "device_usage": dict(state.device_usage),
            "profile_usage": {
                profile_id: dict(usage)
                for profile_id, usage in state.profile_usage
            },
        }


class UsageLimitService:
    """Policy and accounting authority used by Parent API and Activity lifecycle.

    Wall-clock dates select the daily bucket, while elapsed Activity runtime must
    be supplied from a monotonic clock by the lifecycle owner. If the calendar
    moves backwards, accounting stays on the newest date ever observed so a
    child cannot receive a fresh budget by changing or correcting the clock.
    """

    def __init__(
        self,
        store: UsageLimitStore,
        *,
        date_provider: Callable[[], date] = date.today,
    ):
        self.store = store
        self._date_provider = date_provider

    def device_policy(self) -> UsageLimitPolicy:
        return self.store.read().device_policy

    def profile_policy(self, profile_id: str) -> UsageLimitPolicy:
        _validate_profile_id(profile_id)
        return self.store.read().profile_policy(profile_id)

    def set_device_policy(self, policy: UsageLimitPolicy) -> None:
        def update(state: _UsageState) -> _UsageState:
            return _UsageState(
                policy,
                state.profile_policies,
                state.latest_accounting_date,
                state.device_usage,
                state.profile_usage,
            )

        self.store.mutate(update)

    def set_profile_policy(
        self, profile_id: str, policy: UsageLimitPolicy
    ) -> None:
        _validate_profile_id(profile_id)

        def update(state: _UsageState) -> _UsageState:
            policies = dict(state.profile_policies)
            if policy.limited:
                policies[profile_id] = policy
            else:
                policies.pop(profile_id, None)
            return _UsageState(
                state.device_policy,
                tuple(sorted(policies.items())),
                state.latest_accounting_date,
                state.device_usage,
                state.profile_usage,
            )

        self.store.mutate(update)

    def remove_profile(self, profile_id: str) -> None:
        """Remove stale per-profile policy/accounting after profile deletion."""
        _validate_profile_id(profile_id)

        def update(state: _UsageState) -> _UsageState:
            policies = dict(state.profile_policies)
            policies.pop(profile_id, None)
            profile_usage = dict(state.profile_usage)
            profile_usage.pop(profile_id, None)
            return _UsageState(
                state.device_policy,
                tuple(sorted(policies.items())),
                state.latest_accounting_date,
                state.device_usage,
                tuple(sorted(profile_usage.items())),
            )

        self.store.mutate(update)

    def status(self, profile_id: str) -> UsageLimitStatus:
        _validate_profile_id(profile_id)
        return self._status_from_state(profile_id, self.store.read())

    def record_activity_time(
        self, profile_id: str, elapsed_seconds: int
    ) -> UsageLimitStatus:
        """Persist monotonic Activity elapsed time and return the new status."""
        _validate_profile_id(profile_id)
        if (
            not isinstance(elapsed_seconds, int)
            or isinstance(elapsed_seconds, bool)
            or elapsed_seconds < 0
        ):
            raise UsageLimitError(
                "elapsed Activity time must be a non-negative integer"
            )

        def update(state: _UsageState) -> _UsageState:
            accounting_date = self._accounting_date(state)
            key = accounting_date.isoformat()
            device_usage = dict(state.device_usage)
            profile_usage = {
                profile: dict(usage) for profile, usage in state.profile_usage
            }
            if elapsed_seconds:
                device_usage[key] = device_usage.get(key, 0) + elapsed_seconds
                child_usage = profile_usage.setdefault(profile_id, {})
                child_usage[key] = child_usage.get(key, 0) + elapsed_seconds
            keep_dates = _latest_date_keys(
                (
                    *device_usage.keys(),
                    *(
                        usage_key
                        for usage in profile_usage.values()
                        for usage_key in usage
                    ),
                ),
                self.store.MAX_DAYS,
            )
            device_usage = {
                usage_key: value
                for usage_key, value in device_usage.items()
                if usage_key in keep_dates
            }
            profile_usage = {
                profile: {
                    usage_key: value
                    for usage_key, value in usage.items()
                    if usage_key in keep_dates
                }
                for profile, usage in profile_usage.items()
            }
            return _UsageState(
                state.device_policy,
                state.profile_policies,
                accounting_date,
                tuple(sorted(device_usage.items())),
                tuple(
                    sorted(
                        (profile, tuple(sorted(usage.items())))
                        for profile, usage in profile_usage.items()
                        if usage
                    )
                ),
            )

        updated = self.store.mutate(update)
        return self._status_from_state(profile_id, updated)

    def _status_from_state(
        self, profile_id: str, state: _UsageState
    ) -> UsageLimitStatus:
        accounting_date = self._accounting_date(state)
        key = accounting_date.isoformat()
        device_used = dict(state.device_usage).get(key, 0)
        profile_usage = dict(state.profile_usage).get(profile_id, ())
        profile_used = dict(profile_usage).get(key, 0)
        profile_policy = state.profile_policy(profile_id)
        device_remaining = _remaining(state.device_policy, device_used)
        profile_remaining = _remaining(profile_policy, profile_used)
        effective = _most_restrictive(device_remaining, profile_remaining)
        return UsageLimitStatus(
            accounting_date=accounting_date,
            profile_id=profile_id,
            device_policy=state.device_policy,
            profile_policy=profile_policy,
            device_used_seconds=device_used,
            profile_used_seconds=profile_used,
            device_remaining_seconds=device_remaining,
            profile_remaining_seconds=profile_remaining,
            effective_remaining_seconds=effective,
        )

    def _accounting_date(self, state: _UsageState) -> date:
        observed = self._date_provider()
        latest = state.latest_accounting_date
        if latest is not None and observed < latest:
            return latest
        return observed


def _remaining(policy: UsageLimitPolicy, used_seconds: int) -> int | None:
    budget = policy.budget_seconds
    return None if budget is None else max(0, budget - used_seconds)


def _most_restrictive(*remaining: int | None) -> int | None:
    finite = [value for value in remaining if value is not None]
    return min(finite) if finite else None


def _optional_minutes(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise UsageLimitError("daily usage limit must be an integer or null")
    return value


def _parse_usage_map(
    value: object, maximum: int
) -> tuple[tuple[str, int], ...]:
    if not isinstance(value, dict) or len(value) > maximum:
        raise UsageLimitError("invalid usage accounting map")
    result: list[tuple[str, int]] = []
    for raw_date, seconds in value.items():
        if not isinstance(raw_date, str):
            raise UsageLimitError("usage accounting date must be text")
        _parse_date(raw_date)
        if (
            not isinstance(seconds, int)
            or isinstance(seconds, bool)
            or seconds < 0
        ):
            raise UsageLimitError(
                "usage accounting seconds must be non-negative integers"
            )
        result.append((raw_date, seconds))
    return tuple(sorted(result))


def _parse_date(value: object) -> date:
    if not isinstance(value, str):
        raise UsageLimitError("usage accounting date must be text")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise UsageLimitError("usage accounting date is invalid") from exc


def _latest_date_keys(values: tuple[str, ...], maximum: int) -> frozenset[str]:
    unique = sorted({_parse_date(value) for value in values}, reverse=True)[:maximum]
    return frozenset(value.isoformat() for value in unique)


def _validate_profile_id(profile_id: object) -> None:
    if (
        not isinstance(profile_id, str)
        or not profile_id
        or len(profile_id) > 128
        or any(
            character
            not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
            for character in profile_id
        )
    ):
        raise UsageLimitError("unsafe profile identifier")
