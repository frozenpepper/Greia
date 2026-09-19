"""R4-C-PERSIST: resident bundle is not double-counted in staging preflight.

Proves the corrected ``require_support_staging_free_space`` accounting:
the already-stored ``candidate.greiaupdate`` bytes are diagnostic only and
the refusal inequality spends only ``extracted_size_bound + reserve``
against current free space. All disk state stays in disposable tmpdirs
with a mocked ``disk_usage`` free value; no mounts, no Docker.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from greia_platform import candidate_support as _candidate_support
from greia_platform.candidate_support import (
    STAGING_OPERATING_RESERVE_BYTES,
    CandidateSupportError,
    SupportStagingCapacity,
    refuse_unless_persist_fits,
    require_support_staging_free_space,
)

_MIB = 1024 * 1024
_BUNDLE_400 = 400 * _MIB
_EXTRACTED_100 = 100 * _MIB
_FREE_500 = 500 * _MIB
_FREE_355 = 355 * _MIB
_RESERVE = STAGING_OPERATING_RESERVE_BYTES
_REQUIRED_356 = _EXTRACTED_100 + STAGING_OPERATING_RESERVE_BYTES


def _disk_free(free_bytes: int):
    def _fake(path) -> SimpleNamespace:
        return SimpleNamespace(total=10 * 1024 * _MIB, used=0, free=free_bytes)

    return mock.patch.object(_candidate_support.shutil, "disk_usage", _fake)


class ResidentBundleNotDoubleCountedTests(unittest.TestCase):
    """400 MiB resident + 500 MiB free + 100 MiB tree must PASS."""

    def test_resident_bundle_passes(self) -> None:
        self.assertEqual(_RESERVE, 256 * _MIB)
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / "staging"
            with _disk_free(_FREE_500):
                verdict = require_support_staging_free_space(
                    parent,
                    bundle_size=_BUNDLE_400,
                    extracted_size_bound=_EXTRACTED_100,
                )
            # Old formula demanded 400 + 100 + 256 = 756 MiB > 500 MiB
            # free and would have refused; the corrected formula demands
            # only 100 + 256 = 356 MiB of additional free space.
            self.assertIsInstance(verdict, SupportStagingCapacity)
            self.assertEqual(verdict.free_bytes, _FREE_500)
            self.assertEqual(verdict.extracted_size_bound, _EXTRACTED_100)
            self.assertEqual(verdict.reserve_bytes, 256 * _MIB)
            self.assertEqual(
                verdict.required_additional_free_bytes, _REQUIRED_356
            )
            self.assertEqual(verdict.bundle_size_bytes, _BUNDLE_400)
            # No tree materialization: preflight creates at most the empty
            # staging parent.
            self.assertTrue(parent.is_dir())
            self.assertEqual(list(parent.iterdir()), [])

    def test_short_free_refuses_before_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / "staging"
            with _disk_free(_FREE_355):
                with self.assertRaises(CandidateSupportError) as raised:
                    require_support_staging_free_space(
                        parent,
                        bundle_size=_BUNDLE_400,
                        extracted_size_bound=_EXTRACTED_100,
                    )
            message = str(raised.exception)
            self.assertIn("PERSIST", message)
            self.assertIn("refusing before extraction", message)
            # Nothing was materialized beyond the empty staging parent.
            self.assertEqual(list(parent.iterdir()), [])

    def test_exact_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            exact = Path(directory) / "exact"
            with _disk_free(_REQUIRED_356):
                verdict = require_support_staging_free_space(
                    exact,
                    bundle_size=_BUNDLE_400,
                    extracted_size_bound=_EXTRACTED_100,
                )
            self.assertEqual(
                verdict.required_additional_free_bytes, _REQUIRED_356
            )
            short = Path(directory) / "short"
            with _disk_free(_REQUIRED_356 - 1):
                with self.assertRaises(CandidateSupportError):
                    require_support_staging_free_space(
                        short,
                        bundle_size=_BUNDLE_400,
                        extracted_size_bound=_EXTRACTED_100,
                    )

    def test_bundle_size_is_diagnostic_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for bundle_size in (1 * _MIB, _BUNDLE_400, 500 * _MIB):
                with self.subTest(bundle_size=bundle_size):
                    parent = Path(directory) / f"staging-{bundle_size}"
                    with _disk_free(_FREE_500):
                        verdict = require_support_staging_free_space(
                            parent,
                            bundle_size=bundle_size,
                            extracted_size_bound=_EXTRACTED_100,
                        )
                    # The required additional bytes never move with the
                    # already-stored bundle size.
                    self.assertEqual(
                        verdict.required_additional_free_bytes,
                        _EXTRACTED_100 + STAGING_OPERATING_RESERVE_BYTES,
                    )
                    self.assertEqual(verdict.bundle_size_bytes, bundle_size)

    def test_legacy_alias_shares_corrected_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / "staging"
            with _disk_free(_FREE_500):
                legacy = refuse_unless_persist_fits(
                    parent,
                    bundle_size=_BUNDLE_400,
                    extracted_size_bound=_EXTRACTED_100,
                )
                current = require_support_staging_free_space(
                    parent,
                    bundle_size=_BUNDLE_400,
                    extracted_size_bound=_EXTRACTED_100,
                )
            self.assertEqual(legacy, current)
            self.assertEqual(
                legacy.required_additional_free_bytes, _REQUIRED_356
            )
            with _disk_free(_FREE_355):
                with self.assertRaises(CandidateSupportError):
                    refuse_unless_persist_fits(
                        parent,
                        bundle_size=_BUNDLE_400,
                        extracted_size_bound=_EXTRACTED_100,
                    )


if __name__ == "__main__":
    unittest.main()
