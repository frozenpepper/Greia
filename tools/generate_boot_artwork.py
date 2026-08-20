#!/usr/bin/env python3
"""Generate Greia boot artwork derivatives with a hardware-safe Acer split.

The canonical source is the retained full-color final legacy frame. Static PNG
consumers (notably installed GRUB) receive that full-color source directly.
The initramfs framebuffer path is deliberately conservative for now: its P6 PPM
keeps the previously physically booting white/indigo transform after the first
full-color PPM experiment coincided with an Acer grey-screen/reboot regression.

This is an explicit temporary hardware-safety boundary, not the desired final
visual design. Reunifying all boot stages on full-color requires a fresh Acer
physical acceptance pass first.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageFilter


_LOGO_COLOR = (62, 70, 130)
_WHITE = (255, 255, 255)
EXPECTED_SIZE = (222, 600)

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


def canonical_full_color_frame(source: Path) -> Image.Image:
    return Image.open(source).convert("RGB")


def derive_hardware_safe_ppm(source: Path) -> Image.Image:
    """Return the previously booting white/indigo initramfs artwork."""

    image = Image.open(source).convert("RGB")
    width, height = image.size
    pixels = image.load()
    mask = Image.new("L", (width, height), 0)
    mask_px = mask.load()
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            if (r + g + b) / 3.0 > 90:
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
        help="canonical full-color boot source frame",
    )
    args = parser.parse_args(argv)

    if not args.source.is_file():
        print(f"canonical boot logo source missing: {args.source}", file=sys.stderr)
        return 1

    full_color = canonical_full_color_frame(args.source)
    safe_ppm = derive_hardware_safe_ppm(args.source)
    if full_color.size != EXPECTED_SIZE or safe_ppm.size != EXPECTED_SIZE:
        print(
            f"unexpected boot-art geometry full={full_color.size} ppm={safe_ppm.size}; "
            f"expected {EXPECTED_SIZE}",
            file=sys.stderr,
        )
        return 1

    SOURCE_OUT.parent.mkdir(parents=True, exist_ok=True)
    full_color.save(SOURCE_OUT)
    STATIC_OUT.parent.mkdir(parents=True, exist_ok=True)
    full_color.save(STATIC_OUT)
    write_ppm(safe_ppm, TARGET_PPM)
    write_ppm(safe_ppm, INSTALLER_PPM)

    print(f"wrote full-color {SOURCE_OUT}")
    print(f"wrote full-color {STATIC_OUT}")
    print(f"wrote hardware-safe PPM {TARGET_PPM}")
    print(f"wrote hardware-safe PPM {INSTALLER_PPM}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
