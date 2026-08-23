"""Stable distribution identity for Greia Activity packages.

A ``.greiaactivity`` file is deliberately a normal ZIP container.  The custom
extension and media type are routing/UX signals for parent clients and file
pickers; they are never trusted as validation.  The canonical archive reader in
``activity_packages.py`` remains responsible for bounded extraction, path and
file-type safety, manifest validation, trust assignment and atomic activation.
"""

from __future__ import annotations

from pathlib import Path


ACTIVITY_PACKAGE_EXTENSION = ".greiaactivity"
ACTIVITY_PACKAGE_MEDIA_TYPE = "application/vnd.greia.activity+zip"
ACTIVITY_PACKAGE_CONTAINER = "zip"
ACTIVITY_PACKAGE_MANIFEST = "activity.toml"


def is_activity_package_filename(value: str | Path) -> bool:
    """Return whether a user-selected name carries Greia's package extension."""

    name = value.name if isinstance(value, Path) else Path(str(value)).name
    return name.casefold().endswith(ACTIVITY_PACKAGE_EXTENSION)


def ensure_activity_package_filename(value: str | Path) -> Path:
    """Return a path with the canonical extension, replacing only a final .zip.

    This helper is intended for authoring/export tooling.  Installers must not
    rename arbitrary incoming files and then infer trust from the result.
    """

    path = Path(value)
    if is_activity_package_filename(path):
        return path
    if path.suffix.casefold() == ".zip":
        return path.with_suffix(ACTIVITY_PACKAGE_EXTENSION)
    return path.with_name(path.name + ACTIVITY_PACKAGE_EXTENSION)


__all__ = [
    "ACTIVITY_PACKAGE_CONTAINER",
    "ACTIVITY_PACKAGE_EXTENSION",
    "ACTIVITY_PACKAGE_MANIFEST",
    "ACTIVITY_PACKAGE_MEDIA_TYPE",
    "ensure_activity_package_filename",
    "is_activity_package_filename",
]
