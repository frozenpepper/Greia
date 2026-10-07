"""Bounded shared PNG conversion guardrails."""
from __future__ import annotations

import unittest
from unittest import mock

from greia_platform.pygame_png import (
    MAX_PNG_BYTES,
    PygamePngError,
    decode_png_surface,
)


class _HugeImage:
    format = "PNG"
    size = (3201, 10)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def convert(self, _mode):
        raise AssertionError("oversized source must fail before conversion")


class PygamePngBoundsTests(unittest.TestCase):
    def test_payload_byte_limit_fails_before_image_open(self):
        payload = b"x" * (MAX_PNG_BYTES + 1)
        with mock.patch(
            "greia_platform.pygame_png.Image.open"
        ) as image_open:
            with self.assertRaises(PygamePngError):
                decode_png_surface(payload, (16, 16))
        image_open.assert_not_called()

    def test_source_dimension_limit_fails_before_pixel_conversion(self):
        with mock.patch(
            "greia_platform.pygame_png.Image.open",
            return_value=_HugeImage(),
        ):
            with self.assertRaises(PygamePngError):
                decode_png_surface(b"png", (16, 16))


if __name__ == "__main__":
    unittest.main()
