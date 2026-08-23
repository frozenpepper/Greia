from __future__ import annotations

import os
import unittest
from unittest import mock

from greia_platform.activity_api import (
    get_profile_grammatical_gender,
    get_profile_presentation,
)
from greia_platform.profile_presentation import GrammaticalGender, ProfilePresentation


class ActivityProfilePresentationApiTests(unittest.TestCase):
    def test_shell_injected_girl_context_maps_to_feminine(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "GREIA_PROFILE_PRESENTATION": "girl",
                "GREIA_PROFILE_GRAMMATICAL_GENDER": "feminine",
            },
            clear=True,
        ):
            self.assertEqual(get_profile_presentation(), ProfilePresentation.GIRL)
            self.assertEqual(
                get_profile_grammatical_gender(),
                GrammaticalGender.FEMININE,
            )

    def test_missing_context_fails_safe_to_neutral(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_profile_presentation(), ProfilePresentation.NEUTRAL)
            self.assertEqual(
                get_profile_grammatical_gender(),
                GrammaticalGender.NEUTRAL,
            )

    def test_invalid_direct_gender_falls_back_to_presentation_derivation(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "GREIA_PROFILE_PRESENTATION": "boy",
                "GREIA_PROFILE_GRAMMATICAL_GENDER": "nonsense",
            },
            clear=True,
        ):
            self.assertEqual(
                get_profile_grammatical_gender(),
                GrammaticalGender.MASCULINE,
            )


if __name__ == "__main__":
    unittest.main()
