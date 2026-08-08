from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class PackageTrust(StrEnum):
    """Platform-owned package trust/origin classification.

    Only ``BUILT_IN`` is currently resolved by the Phase-0 source tree. The
    remaining states are reserved by the architecture for the future package
    manager/signature policy and deliberately do not gain system privileges yet.
    """

    BUILT_IN = "built_in"
    SIGNED_CURATED = "signed_curated"
    SIGNED_PUBLISHER = "signed_publisher"
    PARENT_TRUSTED_UNSIGNED = "parent_trusted_unsigned"
    DEVELOPER_UNSIGNED = "developer_unsigned"
    INVALID = "invalid"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True)
class ActivitySource:
    """Trusted platform description of where Activity packages came from.

    This value is configuration supplied by Greia itself, never by
    ``activity.toml``. A package cannot become built-in by claiming an Activity
    ID or title; it must actually be discovered through a source the platform
    configured with built-in trust.
    """

    root: Path
    trust: PackageTrust = PackageTrust.DEVELOPER_UNSIGNED
    source_id: str = "development"

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.resolve())
        if not self.source_id or any(character.isspace() for character in self.source_id):
            raise ValueError("activity source_id must be a non-empty token without whitespace")
