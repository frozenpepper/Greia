from __future__ import annotations

import os
import unittest
from unittest import mock

from greia_platform.activity_ui import ChildUiMetrics


class ActivityUiPreferenceTests(unittest.TestCase):
    def test_reference_resolution_changes_shared_metrics_semantically(self) -> None:
        scales = {}
        for value in ("compact", "normal", "large"):
            with mock.patch.dict(os.environ, {"GREIA_INTERFACE_SIZE": value}, clear=False):
                scales[value] = ChildUiMetrics.for_size(1024, 600).scale
        self.assertLess(scales["compact"], scales["normal"])
        self.assertLess(scales["normal"], scales["large"])

    def test_bad_environment_value_fails_to_normal_not_arbitrary_scaling(self) -> None:
        with mock.patch.dict(os.environ, {"GREIA_INTERFACE_SIZE": "enormous"}, clear=False):
            malformed = ChildUiMetrics.for_size(1024, 600)
        with mock.patch.dict(os.environ, {"GREIA_INTERFACE_SIZE": "normal"}, clear=False):
            normal = ChildUiMetrics.for_size(1024, 600)
        self.assertEqual(malformed, normal)

    def test_resolution_and_profile_size_compose_with_bounds(self) -> None:
        with mock.patch.dict(os.environ, {"GREIA_INTERFACE_SIZE": "large"}, clear=False):
            small = ChildUiMetrics.for_size(320, 240)
            reference = ChildUiMetrics.for_size(1024, 600)
            huge = ChildUiMetrics.for_size(3840, 2160)
        self.assertGreaterEqual(small.scale, 0.5)
        self.assertGreater(reference.scale, 1.0)
        self.assertLessEqual(huge.scale, 1.9)


if __name__ == "__main__":
    unittest.main()
