from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from greia_platform.activity_api import get_input_profile
from greia_platform.input_core import InteractionProfile


class ActivityInputApiTests(unittest.TestCase):
    def test_missing_profile_uses_api_01_hybrid_compatibility(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIs(get_input_profile(), InteractionProfile.HYBRID)

    def test_platform_launch_profile_is_exposed_as_typed_semantic_context(self) -> None:
        with patch.dict(
            os.environ,
            {"GREIA_ACTIVITY_INPUT_PROFILE": "pointer"},
            clear=True,
        ):
            self.assertIs(get_input_profile(), InteractionProfile.POINTER)

    def test_invalid_runtime_mutation_is_not_silently_accepted(self) -> None:
        with patch.dict(
            os.environ,
            {"GREIA_ACTIVITY_INPUT_PROFILE": "brand-specific-magic"},
            clear=True,
        ):
            with self.assertRaises(ValueError):
                get_input_profile()


if __name__ == "__main__":
    unittest.main()
