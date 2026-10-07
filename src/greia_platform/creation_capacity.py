"""Adaptive disk headroom policy for child-created data.

This policy is a platform-wide *growth ceiling*, not an Activity quota. Measure
only the writable filesystem containing durable profile data: total physical
media capacity may include separate immutable OS/update partitions.
"""

from __future__ import annotations

from dataclasses import dataclass
import shutil
from pathlib import Path
from typing import Callable


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
class CreationCapacityPolicy:
    """Allow growth only while preserving a proportional and absolute reserve.

    All writable profile consumers must eventually share this same growth
    authority; library-only enforcement cannot prevent a *different* service
    from filling the filesystem. The policy is safe to integrate incrementally.
    """

    maximum_used_fraction: float = 0.75
    minimum_free_bytes: int = 512 * 1024 * 1024

    def __post_init__(self) -> None:
        if not 0.0 < self.maximum_used_fraction < 1.0:
            raise ValueError("maximum_used_fraction must be between 0 and 1")
        if self.minimum_free_bytes < 0:
            raise ValueError("minimum_free_bytes must be non-negative")

    def remaining_growth_bytes(self, usage: VolumeUsage) -> int:
        occupancy_room = int(usage.total_bytes * self.maximum_used_fraction) - usage.used_bytes
        free_space_room = usage.free_bytes - self.minimum_free_bytes
        return max(0, min(occupancy_room, free_space_room))

    def require_growth(self, usage: VolumeUsage, byte_count: int) -> None:
        if byte_count < 0:
            raise ValueError("growth must be non-negative")
        if byte_count > self.remaining_growth_bytes(usage):
            raise CreationSpaceError("child content storage would exhaust protected disk headroom")


class CreationSpaceError(RuntimeError):
    """Refusing new content preserves the ability to keep running the OS."""


class VolumeBudget:
    """Small injectable system-volume probe used at the trusted storage owner."""

    def __init__(
        self,
        policy: CreationCapacityPolicy | None = None,
        probe: Callable[[Path], VolumeUsage] | None = None,
    ) -> None:
        self.policy = policy or CreationCapacityPolicy()
        self._probe = probe or self._usage_from_system

    @staticmethod
    def _usage_from_system(root: Path) -> VolumeUsage:
        usage = shutil.disk_usage(root)
        return VolumeUsage(usage.total, usage.used, usage.free)

    def require_growth(self, managed_root: Path, byte_count: int) -> None:
        self.policy.require_growth(self._probe(managed_root), byte_count)
