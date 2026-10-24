"""Small installed-mount fixture shared by source-level updater tests.

The updater's production readiness checks are intentionally unchanged. These
tests model the three installed mounts and the matching ``/boot`` fstab UUID
so each test can reach the later update behavior it is meant to exercise.
Independent activation/readiness tests cover missing and mismatched mounts.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

from greia_platform.update_activation import (
    BOOT_CONTROL_MOUNTPOINT,
    GREIA_OS_STATE_MOUNTPOINT,
    PERSIST_MOUNTPOINT,
)


BOOT_CONTROL_UUID = "dddddddd-eeee-ffff-0000-111111111111"


class _InstalledMountProbe:
    """Model the expected installed PERSIST, state bind and boot mounts."""

    def __init__(self, persist_uuid: str) -> None:
        self._expected = {
            PERSIST_MOUNTPOINT: (persist_uuid, "/"),
            GREIA_OS_STATE_MOUNTPOINT: (
                persist_uuid,
                "/greia/namespaces/parent-credentials",
            ),
            BOOT_CONTROL_MOUNTPOINT: (BOOT_CONTROL_UUID, "/"),
        }

    def mounted_uuid_matches(
        self,
        mountpoint: Path,
        filesystem_uuid: str,
        *,
        expected_mount_root: str | None = None,
    ) -> bool:
        return self._expected.get(Path(mountpoint)) == (
            filesystem_uuid,
            expected_mount_root,
        )


def _read_fixture_fstab_uuid(fstab_path: Path, mountpoint: str) -> str:
    if Path(fstab_path) != Path("/etc/fstab") or mountpoint != "/boot":
        raise ValueError("fixture only declares the installed /boot mount")
    return BOOT_CONTROL_UUID


def installed_mount_patchers(persist_uuid: str) -> tuple[object, object]:
    """Return patchers that model exact installed mount and fstab evidence."""
    return (
        mock.patch(
            "greia_platform.update_activation.RuntimeMountProbe",
            new=lambda: _InstalledMountProbe(persist_uuid),
        ),
        mock.patch(
            "greia_platform.fstab.read_fstab_uuid_for_mount",
            side_effect=_read_fixture_fstab_uuid,
        ),
    )


def start_installed_mount_fixture(persist_uuid: str) -> tuple[object, object]:
    """Start a module-scoped installed-mount model for source integration tests."""
    patchers = installed_mount_patchers(persist_uuid)
    for patcher in patchers:
        patcher.start()  # type: ignore[attr-defined]
    return patchers


def stop_installed_mount_fixture(patchers: tuple[object, object]) -> None:
    for patcher in reversed(patchers):
        patcher.stop()  # type: ignore[attr-defined]
