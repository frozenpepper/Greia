"""Declarative first-party release Activity selection.

This is build/release policy, not package metadata and not launcher filtering.
The repository may contain experiments or held first-party Activities without
making them installed built-ins. A release selection names exact package
directories and expected Activity IDs; the staging/build path re-validates
those packages through ActivityRegistry before they can become image content.
"""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath


_SCHEMA_VERSION = 1
_MAX_SELECTION_BYTES = 256 * 1024
_MAX_ACTIVITIES = 128
_ID = re.compile(r"^[a-z][a-z0-9._-]{1,127}$")
_PACKAGE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,95}$")


class ReleaseSelectionError(ValueError):
    """Release Activity policy is malformed, unsafe or not approved."""


class ReleaseSelectionStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"


@dataclass(frozen=True, slots=True)
class ReleaseActivity:
    activity_id: str
    package_relpath: str

    def __post_init__(self) -> None:
        if not isinstance(self.activity_id, str) or not _ID.fullmatch(self.activity_id):
            raise ReleaseSelectionError("invalid release Activity ID")
        if (
            not isinstance(self.package_relpath, str)
            or not _PACKAGE.fullmatch(self.package_relpath)
        ):
            raise ReleaseSelectionError("invalid release Activity package")
        path = PurePosixPath(self.package_relpath)
        if path.is_absolute() or len(path.parts) != 1 or path.name != self.package_relpath:
            raise ReleaseSelectionError("release Activity package must be one safe directory")


@dataclass(frozen=True, slots=True)
class FirstPartyReleaseSelection:
    schema_version: int
    release_id: str
    status: ReleaseSelectionStatus
    activities: tuple[ReleaseActivity, ...]

    def __post_init__(self) -> None:
        if self.schema_version != _SCHEMA_VERSION:
            raise ReleaseSelectionError("unsupported release Activity selection schema")
        if not isinstance(self.release_id, str) or not _ID.fullmatch(self.release_id):
            raise ReleaseSelectionError("invalid release selection ID")
        if len(self.activities) > _MAX_ACTIVITIES:
            raise ReleaseSelectionError("release Activity selection exceeds bound")
        ids = [item.activity_id for item in self.activities]
        packages = [item.package_relpath for item in self.activities]
        if len(set(ids)) != len(ids):
            raise ReleaseSelectionError("duplicate release Activity ID")
        if len(set(packages)) != len(packages):
            raise ReleaseSelectionError("duplicate release Activity package")
        if tuple(ids) != tuple(sorted(ids)):
            raise ReleaseSelectionError(
                "release Activities must be sorted by Activity ID for stable review"
            )

    @classmethod
    def load(cls, path: Path) -> "FirstPartyReleaseSelection":
        candidate = Path(path)
        try:
            stat = candidate.stat()
            if not candidate.is_file() or stat.st_size > _MAX_SELECTION_BYTES:
                raise ReleaseSelectionError("release Activity selection is unusable")
            raw = tomllib.loads(candidate.read_text(encoding="utf-8"))
        except ReleaseSelectionError:
            raise
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise ReleaseSelectionError(
                f"cannot read release Activity selection: {exc}"
            ) from exc
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: object) -> "FirstPartyReleaseSelection":
        if not isinstance(raw, dict):
            raise ReleaseSelectionError("release Activity selection must be a table")
        if raw.get("schema_version") != _SCHEMA_VERSION:
            raise ReleaseSelectionError("unsupported release Activity selection schema")
        release = raw.get("release")
        if not isinstance(release, dict):
            raise ReleaseSelectionError("release table is required")
        release_id = release.get("id")
        status_raw = release.get("status")
        try:
            status = ReleaseSelectionStatus(status_raw)
        except (TypeError, ValueError) as exc:
            raise ReleaseSelectionError(
                "release status must be draft or approved"
            ) from exc
        items = raw.get("activities", [])
        if not isinstance(items, list):
            raise ReleaseSelectionError("activities must be an array of tables")
        parsed: list[ReleaseActivity] = []
        for item in items:
            if not isinstance(item, dict):
                raise ReleaseSelectionError("release Activity entry must be a table")
            if set(item) != {"activity_id", "package"}:
                raise ReleaseSelectionError(
                    "release Activity entry accepts only activity_id and package"
                )
            parsed.append(
                ReleaseActivity(
                    activity_id=item.get("activity_id"),
                    package_relpath=item.get("package"),
                )
            )
        return cls(
            schema_version=_SCHEMA_VERSION,
            release_id=release_id,
            status=status,
            activities=tuple(parsed),
        )

    def require_approved(self) -> None:
        if self.status is not ReleaseSelectionStatus.APPROVED:
            raise ReleaseSelectionError(
                "release Activity selection is still draft; release build refused"
            )

    @property
    def activity_ids(self) -> tuple[str, ...]:
        return tuple(item.activity_id for item in self.activities)


__all__ = [
    "FirstPartyReleaseSelection",
    "ReleaseActivity",
    "ReleaseSelectionError",
    "ReleaseSelectionStatus",
]
