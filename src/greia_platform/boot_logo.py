"""Canonical Greia boot artwork resolution for launcher and installer.

Installed Greia carries the canonical PNG beneath ``/opt/greia-os/assets``.
The live installer deliberately keeps its application payload smaller and
already carries the same build-generated RGB artwork as a P6 PPM for the early
framebuffer cover. Callers may use either representation; both are generated
from the same full-color canonical source during the legacy installer build.
"""

from __future__ import annotations

import os
from pathlib import Path


_BOOT_LOGO = "assets/boot/static/greia-boot-logo.png"
_LIVE_BOOT_PPM = Path("/etc/greia-boot/boot-logo.ppm")


def canonical_boot_logo(root: Path | None = None) -> Path | None:
    """Return the best canonical boot-art representation available.

    ``root`` is the Greia OS root (defaults to ``GREIA_OS_ROOT`` or
    ``/opt/greia-os``). Installed/development source prefers the PNG. A live
    installer that does not stage the PNG may reuse its lossless P6 PPM, which
    Pygame can load directly. Missing artwork remains fail-soft for callers.
    """

    base = root or Path(
        os.environ.get("GREIA_OS_ROOT", "/opt/greia-os")
    ).resolve()
    candidate = base / _BOOT_LOGO
    if candidate.is_file():
        return candidate

    # The live root already needs this exact RGB derivative for initramfs. Reuse
    # it instead of carrying a second large copy only for the Welcome page.
    live_ppm = Path(os.environ.get("GREIA_BOOT_PPM", str(_LIVE_BOOT_PPM)))
    if live_ppm.is_file():
        return live_ppm

    # Windowed/dev runs can resolve the repository PNG without an installed root.
    repo = Path(__file__).resolve().parents[2]
    candidate = repo / "assets" / "boot" / "static" / "greia-boot-logo.png"
    return candidate if candidate.is_file() else None
