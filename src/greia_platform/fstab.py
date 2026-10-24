"""Single canonical ``/etc/fstab`` renderer for Greia destinations.

One owner for destination-dependent fstab policy, shared by fresh target
assembly (``build/lib/compose.sh`` via ``GREIA_ROOT_UUID`` and
``greia_installer.engine``) and by :class:`SlotFinalizer
<greia_platform.slot_writer.SlotFinalizer>` for post-binding destination
specialization.

Canonical policy (frozen, Repair C):

.. code-block:: text

    UUID=<uuid> / ext4 defaults,noatime,errors=remount-ro 0 1
    tmpfs /tmp tmpfs nosuid,nodev,noexec,mode=1777,size=64M 0 0
    tmpfs /var/tmp tmpfs nosuid,nodev,noexec,mode=1777,size=32M 0 0

Only the root UUID varies per destination role; the tmpfs lines are
identical everywhere. The release payload carries no fake final root UUID:
the finalizer renders this policy after binding the destination role's
stable filesystem UUID.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from .persistent_layout import (
    build_namespace_map,
    persist_mount_source_path,
)

#: Slot-relative fstab path written by every destination assembly path.
FSTAB_REL_PATH = "etc/fstab"

#: Canonical on-disk mode for every destination ``/etc/fstab`` write.
#: ``/etc/fstab`` carries no secrets; Debian convention and sibling Greia
#: config writes (``engine._write_grub_root_uuid``,
#: ``compose_write_metadata_manifests``) are world-readable ``0644``.
#: Fresh assembly (``write_fstab``, installer engine, ``compose.sh`` seam)
#: and the ``SlotFinalizer`` path must all land on this mode so a freshly
#: installed slot and an updated slot are metadata-equivalent. The shared
#: block seam (``BlockSlotFilesystem.write_file``) keeps its ``0o600``
#: default for all other finalized files; the finalizer explicitly
#: re-chmods only the fstab path after its ``write_file`` call.
FSTAB_FILE_MODE = 0o644

_TMPFS_TMP = "tmpfs /tmp tmpfs nosuid,nodev,noexec,mode=1777,size=64M 0 0"
_TMPFS_VAR_TMP = "tmpfs /var/tmp tmpfs nosuid,nodev,noexec,mode=1777,size=32M 0 0"

#: Root-owned bootstrap mount for the canonical PERSIST filesystem.
PERSIST_BOOT_MOUNTPOINT = "/run/greia-persist"
#: Shared A/B GRUB boot-control filesystem mounted before Greia services.
BOOT_CONTROL_MOUNTPOINT = "/boot"


def normalize_root_uuid(value: object) -> str:
    """Return the canonical lowercase UUID text for ``value``.

    Raises :class:`ValueError` when ``value`` is not a valid UUID, so shell
    and installer call sites fail closed instead of writing a guess.
    """
    if not isinstance(value, str):
        raise ValueError("root filesystem UUID must be text")
    try:
        parsed = uuid.UUID(value.strip())
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"invalid root filesystem UUID: {value!r}") from exc
    return str(parsed)


def normalize_filesystem_uuid(value: object, *, field_name: str) -> str:
    """Return one canonical filesystem UUID with field-specific diagnostics."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text")
    try:
        return str(uuid.UUID(value.strip()))
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"invalid {field_name}: {value!r}") from exc


def render_fstab(
    root_uuid: str,
    *,
    persist_filesystem_uuid: str | None = None,
    boot_control_filesystem_uuid: str | None = None,
) -> str:
    """Render root-only or installer-bound A/B mount policy.

    Omitting both optional identities preserves the historical single-root
    fstab byte-for-byte. A/B callers provide both identities from verified
    installer/layout facts; partial authority is refused.
    """
    normalized = normalize_root_uuid(root_uuid)
    lines = [
        f"UUID={normalized} / ext4 defaults,noatime,errors=remount-ro 0 1\n"
        f"{_TMPFS_TMP}\n"
        f"{_TMPFS_VAR_TMP}\n"
    ]
    if (persist_filesystem_uuid is None) != (boot_control_filesystem_uuid is None):
        raise ValueError("A/B fstab requires both PERSIST and boot-control UUIDs")
    if persist_filesystem_uuid is None:
        return "".join(lines)

    persist_uuid = normalize_filesystem_uuid(
        persist_filesystem_uuid, field_name="PERSIST filesystem UUID"
    )
    boot_uuid = normalize_filesystem_uuid(
        boot_control_filesystem_uuid, field_name="boot-control filesystem UUID"
    )
    if len({normalized, persist_uuid, boot_uuid}) != 3:
        raise ValueError("A/B filesystem UUIDs must be distinct")

    lines.extend(
        (
            f"UUID={persist_uuid} {PERSIST_BOOT_MOUNTPOINT} ext4 "
            "defaults,noatime,nodev,nosuid,errors=remount-ro 0 2\n",
            f"UUID={boot_uuid} {BOOT_CONTROL_MOUNTPOINT} ext4 "
            "defaults,noatime,nodev,nosuid,errors=remount-ro 0 2\n",
        )
    )
    namespace_map = build_namespace_map()
    for mount in namespace_map.mount_plan():
        source = persist_mount_source_path(Path(PERSIST_BOOT_MOUNTPOINT), mount)
        lines.append(
            f"{source} {mount.target} none "
            f"bind,x-systemd.requires-mounts-for={PERSIST_BOOT_MOUNTPOINT} 0 0\n"
        )
    return "".join(lines)


def read_fstab_uuid_for_mount(fstab_path: Path, mountpoint: str) -> str:
    """Read one strict ``UUID=`` source for ``mountpoint`` from an fstab.

    Duplicate targets, missing entries, malformed rows and non-UUID sources
    fail closed. This is used by the updater only after mountinfo confirms
    that the live mount matches the declared filesystem identity.
    """
    if not isinstance(mountpoint, str) or not mountpoint.startswith("/"):
        raise ValueError("fstab mountpoint must be an absolute path")
    location = Path(fstab_path)
    try:
        raw = location.read_text(encoding="ascii")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError("fstab is not readable as ASCII") from exc
    found: list[str] = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        fields = line.split("#", 1)[0].split()
        if not fields:
            continue
        if len(fields) < 4:
            raise ValueError(f"fstab line {line_number} has too few fields")
        if fields[1] != mountpoint:
            continue
        source = fields[0]
        if not source.startswith("UUID="):
            raise ValueError(f"fstab source for {mountpoint} is not UUID-based")
        found.append(
            normalize_filesystem_uuid(
                source[5:], field_name=f"{mountpoint} filesystem UUID"
            )
        )
    if len(found) != 1:
        raise ValueError(f"fstab must contain exactly one UUID entry for {mountpoint}")
    return found[0]


def write_fstab(
    root: Path,
    root_uuid: str,
    *,
    persist_filesystem_uuid: str | None = None,
    boot_control_filesystem_uuid: str | None = None,
) -> Path:
    """Write the canonical fstab under ``root`` and return its path.

    The destination file always lands at :data:`FSTAB_FILE_MODE`
    (``0o644``) regardless of the caller umask, so fresh assembly and
    the finalizer path are metadata-equivalent.
    """
    path = Path(root) / FSTAB_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_fstab(
            root_uuid,
            persist_filesystem_uuid=persist_filesystem_uuid,
            boot_control_filesystem_uuid=boot_control_filesystem_uuid,
        ),
        encoding="ascii",
    )
    os.chmod(path, FSTAB_FILE_MODE)
    return path


__all__ = [
    "BOOT_CONTROL_MOUNTPOINT",
    "FSTAB_FILE_MODE",
    "FSTAB_REL_PATH",
    "PERSIST_BOOT_MOUNTPOINT",
    "normalize_filesystem_uuid",
    "normalize_root_uuid",
    "read_fstab_uuid_for_mount",
    "render_fstab",
    "write_fstab",
]
