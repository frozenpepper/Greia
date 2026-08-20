#!/usr/bin/env python3
"""Generate Greia boot artwork derivatives from the last physically booting Acer transform.

The canonical Greia boot logo is the final frame of the retained legacy boot
animation. The 2026-08-20 attempt to switch the boot-critical initramfs path to
full-color derivatives landed before hardware acceptance and the next Acer live
USB regressed into grey-screen/reboot. Until that regression is isolated, the
legacy-x86 physical installer deliberately uses the previously booting white /
indigo derivative again. Visual fidelity work must be reintroduced separately
after boot viability is proven.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image


_BACKGROUND_THRESHOLD = 150
_LOGO_COLOR = (62, 70, 130)
_WHITE = (255, 255, 255)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FRAME = (
    ROOT
    / "assets"
    / "boot"
    / "source"
    / "legacy-plymouth-theme"
    / "frames"
    / "frame_0051.png"
)
SOURCE_OUT = ROOT / "assets" / "boot" / "source" / "greia-boot-logo.png"
STATIC_OUT = ROOT / "assets" / "boot" / "static" / "greia-boot-logo.png"
TARGET_PPM = ROOT / "build" / "overlay" / "etc" / "greia-boot" / "boot-logo.ppm"
INSTALLER_PPM = ROOT / "build" / "installer-overlay" / "etc" / "greia-boot" / "boot-logo.ppm"


def is_background(pixel: tuple[int, int, int]) -> bool:
    r, g, b = pixel
    return r < 35 and g < 55 and b < 95 and (r + g + b) < _BACKGROUND_THRESHOLD


def derive_white_frame(source: Path) -> Image.Image:
    """Return the previously hardware-booting dark-on-white derivative."""
    from PIL import ImageFilter

    image = Image.open(source).convert("RGB")
    width, height = image.size
    pixels = image.load()
    mask = Image.new("L", (width, height), 0)
    mask_px = mask.load()
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            luminance = (r + g + b) / 3.0
            if luminance > 90:
                mask_px[x, y] = 255
    mask = mask.filter(ImageFilter.MedianFilter(3))
    output = Image.new("RGB", (width, height), _WHITE)
    out = output.load()
    for y in range(height):
        for x in range(width):
            if mask_px[x, y] > 128:
                out[x, y] = _LOGO_COLOR
    return output


def write_ppm(image: Image.Image, path: Path) -> None:
    rgb = image.convert("RGB")
    width, height = rgb.size
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(b"P6\n")
        handle.write(f"{width} {height}\n255\n".encode("ascii"))
        handle.write(rgb.tobytes())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=SOURCE_FRAME,
        help="canonical boot logo source frame",
    )
    args = parser.parse_args(argv)

    if not args.source.is_file():
        print(f"canonical boot logo source missing: {args.source}", file=sys.stderr)
        return 1
    image = derive_white_frame(args.source)
    if image.size != (222, 600):
        print(
            f"unexpected canonical source size {image.size}; expected (222, 600)",
            file=sys.stderr,
        )
        return 1

    SOURCE_OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(SOURCE_OUT)
    STATIC_OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(STATIC_OUT)
    write_ppm(image, TARGET_PPM)
    write_ppm(image, INSTALLER_PPM)
    print(f"wrote {SOURCE_OUT}")
    print(f"wrote {STATIC_OUT}")
    print(f"wrote {TARGET_PPM}")
    print(f"wrote {INSTALLER_PPM}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
