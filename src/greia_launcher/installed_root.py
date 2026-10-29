"""Identify the installed application through its update-generation link."""

from pathlib import Path


INSTALLED_APPLICATION_ROOT = Path("/opt/greia-os")


def is_installed_root(root: Path) -> bool:
    """Compare resolved roots so the installed generation symlink is recognized."""
    return root == INSTALLED_APPLICATION_ROOT or root.resolve() == INSTALLED_APPLICATION_ROOT.resolve()
