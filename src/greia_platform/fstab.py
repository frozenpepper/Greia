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


def render_fstab(root_uuid: str) -> str:
    """Render the canonical ``/etc/fstab`` text for one destination UUID."""
    normalized = normalize_root_uuid(root_uuid)
    return (
        f"UUID={normalized} / ext4 defaults,noatime,errors=remount-ro 0 1\n"
        f"{_TMPFS_TMP}\n"
        f"{_TMPFS_VAR_TMP}\n"
    )


def write_fstab(root: Path, root_uuid: str) -> Path:
    """Write the canonical fstab under ``root`` and return its path.

    The destination file always lands at :data:`FSTAB_FILE_MODE`
    (``0o644``) regardless of the caller umask, so fresh assembly and
    the finalizer path are metadata-equivalent.
    """
    path = Path(root) / FSTAB_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_fstab(root_uuid), encoding="ascii")
    os.chmod(path, FSTAB_FILE_MODE)
    return path
