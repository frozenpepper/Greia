"""Hermetic filesystem-capacity probe for tests.

Production ``VolumeBudget`` measures the real host volume and (by design)
refuses child-data writes when that volume is nearly full. Tests that are not
about capacity policy must not depend on how full the developer's disk is, so
they install a roomy synthetic probe for the duration of their module.

Tests that exercise the refusal path keep passing their own explicit
``VolumeBudget(probe=...)``; those are unaffected because only the *default*
system probe is replaced and the policy thresholds are never touched.

Usage in a test module::

    import hermetic_volume

    def setUpModule() -> None:
        hermetic_volume.install_for_module()
"""

from __future__ import annotations

from pathlib import Path
import unittest
from unittest import mock

from greia_platform.creation_capacity import VolumeBudget, VolumeUsage

_TOTAL_BYTES = 1024 * 1024 * 1024 * 1024  # 1 TiB synthetic volume
_USED_BYTES = 1024 * 1024 * 1024  # 1 GiB used: far below every threshold


def roomy_volume_usage(root: Path) -> VolumeUsage:
    """Synthetic, nearly empty volume satisfying the default capacity policy."""
    return VolumeUsage(
        _TOTAL_BYTES, _USED_BYTES, _TOTAL_BYTES - _USED_BYTES
    )


def install_for_module() -> None:
    """Replace the default system probe until the module's cleanup runs."""
    patcher = mock.patch.object(
        VolumeBudget, "_usage_from_system", staticmethod(roomy_volume_usage)
    )
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)
