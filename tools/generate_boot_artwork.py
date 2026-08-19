#!/usr/bin/env python3
"""Generate Greia boot artwork derivatives from the canonical full-color frame.

The canonical source is the final frame of the retained legacy boot animation:
`assets/boot/source/legacy-plymouth-theme/frames/frame_0051.png`.

A previous implementation thresholded that image into a binary mask and then
painted every retained pixel one indigo color on white. That intentionally
threw away the source colors and also converted antialiasing/detail into a
speckled silhouette. The result looked exactly like corrupted white/blue
artwork on physical hardware even when framebuffer packing was correct.

Boot derivatives now preserve the source RGB pixels exactly. GRUB, the early
framebuffer cover and the launcher intro therefore share one visual source:

- `assets/boot/source/greia-boot-logo.png`
- `assets/boot/static/greia-boot-logo.png`
- `build/overlay/etc/greia-boot/boot-logo.ppm`
- `build/installer-overlay/etc/greia-boot/boot-logo.ppm`

The initramfs renderer remains deliberately PNG-free, so the P6 PPM files are
lossless RGB encodings of the same canonical image.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image


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
EXPECTED_SIZE = (222, 600)


def canonical_full_color_frame(source: Path) -> Image.Image:
    """Return the canonical frame without recoloring, masking or quantizing it."""

    return Image.open(source).convert("RGB")


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
    image = canonical_full_color_frame(args.source)
    if image.size != EXPECTED_SIZE:
        print(
            f"unexpected canonical source size {image.size}; expected {EXPECTED_SIZE}",
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
