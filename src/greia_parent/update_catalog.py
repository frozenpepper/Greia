"""Bounded reader for Greia's image-configured public update index.

The catalog is discovery data only. A selected row is re-read before download,
and the existing Greia inbox/updater validates the complete bundle again.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

from greia_platform.system_updates import MAX_BUNDLE_BYTES


DEFAULT_UPDATE_INDEX_URL = (
    "https://www.frozenpepper.it/greia/updates/greia-updates.json"
)
MAX_UPDATE_INDEX_BYTES = 512 * 1024
MAX_CHANNEL_ENTRIES = 128
MAX_PUBLIC_RELEASES = 32
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_VERSION = re.compile(
    r"^[vV]?(?P<core>[0-9]+(?:\.[0-9]+){0,7})"
    r"(?:-(?P<prerelease>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


class UpdateCatalogError(RuntimeError):
    """An update index or selected release did not meet Greia's bounds."""


@dataclass(frozen=True, slots=True)
class DeviceUpdateIdentity:
    """Installed identity returned by the privileged update authority."""

    version: str
    release_id: str
    profile: str
    platform_family: str
    architecture: str
    board: str | None

    @classmethod
    def from_status(cls, status: Mapping[str, object]) -> "DeviceUpdateIdentity":
        raw = status.get("identity")
        if not isinstance(raw, Mapping):
            raise UpdateCatalogError("device update identity is unavailable")
        fields = ("version", "release_id", "profile", "platform_family", "architecture")
        values: dict[str, str] = {}
        for field in fields:
            value = raw.get(field)
            if not isinstance(value, str) or not value or len(value) > 96:
                raise UpdateCatalogError("device update identity is incomplete")
            values[field] = value
        board = raw.get("board")
        if board is not None and (not isinstance(board, str) or not board or len(board) > 64):
            raise UpdateCatalogError("device board identity is invalid")
        return cls(**values, board=board)


@dataclass(frozen=True, slots=True)
class UpdateRelease:
    """One catalog row scoped to a single exact Greia profile."""

    release_id: str
    version: str
    profiles: tuple[str, ...]
    target_profile: str
    platform_family: str
    architecture: str
    board: str | None
    url: str
    size: int
    sha256: str
    published_at: str
    notes: Mapping[str, str]

    def public_dict(self) -> dict[str, object]:
        """Return UI-safe release facts without exposing the download URL."""

        return {
            "release_id": self.release_id,
            "version": self.version,
            "profile": self.target_profile,
            "platform_family": self.platform_family,
            "architecture": self.architecture,
            "board": self.board,
            "size": self.size,
            "sha256": self.sha256,
            "published_at": self.published_at,
            "notes": dict(self.notes),
        }


class UpdateCatalogClient:
    """Fetch and validate a small HTTPS catalog from an image-owned URL."""

    def __init__(
        self,
        index_url: str = DEFAULT_UPDATE_INDEX_URL,
        *,
        timeout_seconds: float = 15.0,
        opener: object | None = None,
    ) -> None:
        self.index_url = _validate_https_url(index_url)
        self.timeout_seconds = timeout_seconds
        self._opener = opener or build_opener()

    def fetch(self, channel: str, identity: DeviceUpdateIdentity) -> tuple[UpdateRelease, ...]:
        if channel not in {"stable", "dev"}:
            raise UpdateCatalogError("Greia update channel is invalid")
        request = Request(
            self.index_url,
            headers={"Accept": "application/json", "User-Agent": "Greia-Parent/1"},
        )
        try:
            response = self._opener.open(request, timeout=self.timeout_seconds)  # type: ignore[attr-defined]
            with response:
                raw = response.read(MAX_UPDATE_INDEX_BYTES + 1)
        except (OSError, HTTPError, URLError, TimeoutError) as exc:
            raise UpdateCatalogError("Greia update catalog could not be reached") from exc
        if len(raw) > MAX_UPDATE_INDEX_BYTES:
            raise UpdateCatalogError("Greia update catalog exceeds its size limit")
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UpdateCatalogError("Greia update catalog is invalid") from exc
        if not isinstance(document, dict) or document.get("schema") != "greia-updates/1":
            raise UpdateCatalogError("Greia update catalog has an unsupported schema")
        greia_os = document.get("greia_os")
        channels = greia_os.get("channels") if isinstance(greia_os, dict) else None
        rows = channels.get(channel) if isinstance(channels, dict) else None
        if not isinstance(rows, list) or len(rows) > MAX_CHANNEL_ENTRIES:
            raise UpdateCatalogError("Greia update channel is invalid or exceeds its bound")

        installed_version = _numeric_version_key(identity.version)
        if installed_version is None:
            # Without a comparable installed release, offering a candidate
            # would turn unknown identity into an accidental downgrade/reinstall.
            return ()

        releases: list[UpdateRelease] = []
        seen: dict[str, tuple[object, ...]] = {}
        for row in rows:
            release = self._parse_release(row)
            if release is None or not _matches_device(release, identity):
                continue
            candidate_version = _numeric_version_key(release.version)
            if candidate_version is None or candidate_version <= installed_version:
                continue
            release = replace(release, target_profile=identity.profile)
            signature = (
                release.version,
                release.target_profile,
                release.platform_family,
                release.architecture,
                release.board,
                release.url,
                release.size,
                release.sha256,
            )
            previous = seen.get(release.release_id)
            if previous is not None and previous != signature:
                raise UpdateCatalogError("Greia update catalog has an ambiguous release id")
            if previous is not None:
                continue
            seen[release.release_id] = signature
            releases.append(release)
        releases.sort(
            key=lambda item: (
                _numeric_version_key(item.version),
                item.published_at,
            ),
            reverse=True,
        )
        return tuple(releases[:MAX_PUBLIC_RELEASES])

    def resolve(self, channel: str, identity: DeviceUpdateIdentity, release_id: str) -> UpdateRelease:
        """Re-fetch the index and resolve one exact compatible release id."""

        for release in self.fetch(channel, identity):
            if release.release_id == release_id:
                return release
        raise UpdateCatalogError("selected Greia release is no longer available for this device")

    def open_bundle(self, release: UpdateRelease, *, timeout_seconds: float = 30.0):
        """Open the HTTPS bundle URL selected from the configured catalog."""

        request = Request(
            release.url,
            headers={
                "Accept": "application/vnd.greia.system-update+zip",
                "User-Agent": "Greia-Parent/1",
            },
        )
        return self._opener.open(request, timeout=timeout_seconds)  # type: ignore[attr-defined]

    def _parse_release(self, row: object) -> UpdateRelease | None:
        if not isinstance(row, dict):
            raise UpdateCatalogError("Greia update catalog contains an invalid release")
        release_id = row.get("release_id")
        version = row.get("version")
        profiles = row.get("profiles")
        family = row.get("platform_family")
        architecture = row.get("architecture")
        board = row.get("board")
        update = row.get("update")
        published_at = row.get("published_at")
        if not isinstance(release_id, str) or not _IDENTIFIER.fullmatch(release_id):
            raise UpdateCatalogError("Greia update catalog release identity is invalid")
        if not isinstance(version, str) or not version or len(version) > 64:
            raise UpdateCatalogError("Greia update catalog version is invalid")
        if _numeric_version_key(version) is None:
            # A row with an unknown version cannot safely be classified as a
            # newer release. Ignore that row while preserving other valid
            # compatible catalog entries.
            return None
        if (
            not isinstance(profiles, list)
            or not profiles
            or len(profiles) > 32
            or any(not isinstance(item, str) or not _IDENTIFIER.fullmatch(item) for item in profiles)
        ):
            raise UpdateCatalogError("Greia update catalog profile list is invalid")
        if not isinstance(family, str) or not family or len(family) > 64:
            raise UpdateCatalogError("Greia update catalog platform family is invalid")
        if not isinstance(architecture, str) or not architecture or len(architecture) > 64:
            raise UpdateCatalogError("Greia update catalog architecture is invalid")
        if board is not None and (not isinstance(board, str) or not _IDENTIFIER.fullmatch(board)):
            raise UpdateCatalogError("Greia update catalog board is invalid")
        if not isinstance(update, dict):
            raise UpdateCatalogError("Greia update catalog bundle is missing")
        url = update.get("url")
        size = update.get("size")
        digest = update.get("sha256")
        if not isinstance(url, str) or not _SHA256.fullmatch(digest if isinstance(digest, str) else ""):
            raise UpdateCatalogError("Greia update catalog bundle reference is invalid")
        _validate_https_url(url)
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0 or size > MAX_BUNDLE_BYTES:
            raise UpdateCatalogError("Greia update catalog bundle size is outside Greia bounds")
        if not isinstance(published_at, str) or len(published_at) > 64:
            raise UpdateCatalogError("Greia update catalog publication time is invalid")
        notes_raw = row.get("notes", {})
        if not isinstance(notes_raw, dict) or len(notes_raw) > 4:
            raise UpdateCatalogError("Greia update catalog notes are invalid")
        notes: dict[str, str] = {}
        for locale, note in notes_raw.items():
            if locale not in {"en", "it", "es", "fr"} or not isinstance(note, str) or len(note) > 4096:
                raise UpdateCatalogError("Greia update catalog notes exceed their bound")
            notes[locale] = note
        # The generator may emit a multi-profile row. Keep the complete bounded
        # list so matching can require the device's exact profile.
        matching_profiles = tuple(item for item in profiles if _IDENTIFIER.fullmatch(item))
        if len(matching_profiles) != len(profiles):
            raise UpdateCatalogError("Greia update catalog profile list is invalid")
        return UpdateRelease(
            release_id,
            version,
            matching_profiles,
            "",
            family,
            architecture,
            board,
            url,
            size,
            digest,
            published_at,
            notes,
        )


def _matches_device(release: UpdateRelease, identity: DeviceUpdateIdentity) -> bool:
    return (
        identity.profile in release.profiles
        and release.platform_family == identity.platform_family
        and release.architecture == identity.architecture
        and (release.board is None or release.board == identity.board)
    )


def _numeric_version_key(value: str) -> tuple[tuple[int, ...], int, tuple[tuple[int, object], ...]] | None:
    """Parse Greia's numeric release versions and SemVer prerelease ordering.

    Build metadata is ignored. Unknown or malformed versions fail closed so a
    catalog cannot present a reinstall/downgrade as a new update.
    """

    if not isinstance(value, str) or len(value) > 64:
        return None
    match = _VERSION.fullmatch(value)
    if match is None:
        return None
    components: list[int] = []
    for part in match.group("core").split("."):
        if len(part) > 1 and part.startswith("0"):
            return None
        components.append(int(part))
    if len(components) < 3:
        components.extend([0] * (3 - len(components)))
    prerelease = match.group("prerelease")
    prerelease_key: list[tuple[int, object]] = []
    if prerelease is not None:
        for identifier in prerelease.split("."):
            if identifier.isdigit():
                if len(identifier) > 1 and identifier.startswith("0"):
                    return None
                prerelease_key.append((0, int(identifier)))
            else:
                prerelease_key.append((1, identifier))
    return (
        tuple(components),
        1 if prerelease is None else 0,
        tuple(prerelease_key),
    )


def _validate_https_url(value: str) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise UpdateCatalogError("Greia HTTPS update URL is invalid")
    try:
        parsed = urlsplit(value)
        valid = (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and (parsed.port is None or 1 <= parsed.port <= 65535)
        )
    except ValueError:
        valid = False
    if not valid:
        raise UpdateCatalogError("Greia update URLs must use HTTPS")
    return value
