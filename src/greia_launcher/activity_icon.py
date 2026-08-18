from __future__ import annotations

from greia_platform.activity_assets import (
    ActivityAssetError,
    PACKAGE_ICON_PREFIX,
    package_icon_path,
)


# Compatibility name for launcher callers/tests. Validation authority lives in
# greia_platform so package installation can reject bad icon references before
# an Activity becomes visible.
ActivityIconError = ActivityAssetError

__all__ = ["ActivityIconError", "PACKAGE_ICON_PREFIX", "package_icon_path"]
