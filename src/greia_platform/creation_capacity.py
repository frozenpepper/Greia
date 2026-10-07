"""Adaptive machine headroom policy for child-owned durable data.

This is a platform-wide growth ceiling, not an Activity quota. Measure only
the writable filesystem containing durable profile data: total physical media
may include separate immutable OS/update partitions.

VolumeBudget is intentionally shareable across storage owners. A held growth
reservation serializes measure -> write sections inside one Greia process so
Activity private storage and My Creations cannot both pass the same stale free
space check and overcommit the filesystem.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import shutil
import threading
from typing import Callable, Iterator


@dataclass(frozen=True, slots=True)
class VolumeUsage:
    total_bytes: int
    used_bytes: int
    free_bytes: int

    def __post_init__(self) -> None:
        if min(self.total_bytes, self.used_bytes, self.free_bytes) < 0:
            raise ValueError("disk usage must not be negative")
        if self.used_bytes + self.free_bytes > self.total_bytes:
            raise ValueError("disk usage exceeds filesystem capacity")


@dataclass(frozen=True, slots=True)
class VolumeCapacityPolicy:
    """Allow growth only while preserving proportional and absolute headroom."""

    maximum_used_fraction: float = 0.75
    minimum_free_bytes: int = 512 * 1024 * 1024

    def __post_init__(self) -> None:
        if not 0.0 < self.maximum_used_fraction < 1.0:
            raise ValueError("maximum_used_fraction must be between 0 and 1")
        if self.minimum_free_bytes < 0:
            raise ValueError("minimum_free_bytes must be non-negative")

    def remaining_growth_bytes(self, usage: VolumeUsage) -> int:
        occupancy_room = (
            int(usage.total_bytes * self.maximum_used_fraction)
            - usage.used_bytes
        )
        free_space_room = usage.free_bytes - self.minimum_free_bytes
        return max(0, min(occupancy_room, free_space_room))

    def require_growth(self, usage: VolumeUsage, byte_count: int) -> None:
        if byte_count < 0:
            raise ValueError("growth must be non-negative")
        if byte_count > self.remaining_growth_bytes(usage):
            raise VolumeSpaceError(
                "child content storage would exhaust protected disk headroom"
            )


CreationCapacityPolicy = VolumeCapacityPolicy


class VolumeSpaceError(RuntimeError):
    """Refusing new child data preserves the ability to keep running the OS."""


CreationSpaceError = VolumeSpaceError


class VolumeBudget:
    """Injectable shared filesystem-growth authority.

    growth_reservation() holds one process-local lock from the measurement
    through the caller's write section. Callers must pass positive net growth
    only: replacements that shrink or preserve size do not consume capacity.
    """

    def __init__(
        self,
        policy: VolumeCapacityPolicy | None = None,
        probe: Callable[[Path], VolumeUsage] | None = None,
    ) -> None:
        self.policy = policy or VolumeCapacityPolicy()
        self._probe = probe or self._usage_from_system
        self._lock = threading.RLock()

    @staticmethod
    def _usage_from_system(root: Path) -> VolumeUsage:
        usage = shutil.disk_usage(root)
        return VolumeUsage(usage.total, usage.used, usage.free)

    def remaining_growth_bytes(self, managed_root: Path) -> int:
        with self._lock:
            return self.policy.remaining_growth_bytes(self._probe(managed_root))

    def require_growth(self, managed_root: Path, byte_count: int) -> None:
        with self._lock:
            self.policy.require_growth(self._probe(managed_root), byte_count)

    @contextmanager
    def growth_reservation(
        self, managed_root: Path, byte_count: int
    ) -> Iterator[None]:
        """Serialize a bounded growth check with the following write section."""
        if byte_count < 0:
            raise ValueError("growth must be non-negative")
        with self._lock:
            self.policy.require_growth(self._probe(managed_root), byte_count)
            yield


__all__ = [
    "CreationCapacityPolicy",
    "CreationSpaceError",
    "VolumeBudget",
    "VolumeCapacityPolicy",
    "VolumeSpaceError",
    "VolumeUsage",
]
