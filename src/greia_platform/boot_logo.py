"""Canonical Greia boot logo resolution for the launcher and installer.

The white-frame Greia boot logo is produced from the canonical artwork lineage
under ``assets/boot/`` and installed into the image at
``/opt/greia-os/assets/boot/static/greia-boot-logo.png`` (and the live
installer's ``assets`` root). This resolver returns the canonical path so the
launcher and installer stop depending on the removed Plymouth runtime.
"""

from __future__ import annotations

import os
from pathlib import Path


_BOOT_LOGO = "assets/boot/static/greia-boot-logo.png"


def canonical_boot_logo(root: Path | None = None) -> Path | None:
    """Return the canonical white-frame boot logo path, or None if unavailable.

    ``root`` is the Greia OS root (defaults to ``GREIA_OS_ROOT`` or
    ``/opt/greia-os``). The logo is optional/fallible: callers should fall back
    to their existing icon handling when this returns None.
    """

    base = root or Path(
        os.environ.get("GREIA_OS_ROOT", "/opt/greia-os")
    ).resolve()
    candidate = base / _BOOT_LOGO
    if candidate.is_file():
        return candidate
    # The live installer runs with its own root; try the repository layout too
    # so windowed/dev runs can find it without an installed image.
    repo = Path(__file__).resolve().parents[2]
    candidate = repo / "assets" / "boot" / "static" / "greia-boot-logo.png"
    return candidate if candidate.is_file() else None
