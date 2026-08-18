#!/usr/bin/env python3
"""Generate Greia boot artwork derivatives from the canonical source.

The canonical Greia boot logo is the final frame of the legacy boot
animation (`build/overlay/etc/plymouth/themes/greia/frames/frame_0051.png`),
which contains the Professor Pip mascot plus the GREIA wordmark drawn in
cream/white on a dark navy background.

This tool derives the white-frame boot assets from that source so GRUB,
the initramfs framebuffer cover and the launcher intro all use the same
canonical artwork lineage:

- `assets/boot/source/greia-boot-logo.png`   canonical white/dark derivative
- `assets/boot/static/greia-boot-logo.png`   GRUB-compatible PNG
- `build/overlay/etc/greia-boot/boot-logo.ppm`        initramfs P6 PPM (target)
- `build/installer-overlay/etc/greia-boot/boot-logo.ppm`  initramfs P6 PPM (installer)

The renderer does not decode PNG in initramfs, so the runtime initramfs asset
is a P6 PPM generated here at build/source time.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image


# The dark navy background of the legacy frames. Pixels at or below this
# brightness belong to the background; brighter pixels form the logo.
_BACKGROUND_THRESHOLD = 150
_LOGO_COLOR = (13, 30, 60)  # Greia brand dark navy for a white frame
_WHITE = (255, 255, 255)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FRAME = (
    ROOT / "build" / "overlay" / "etc" / "plymouth" / "themes" / "greia" / "frames" / "frame_0051.png"
)
SOURCE_OUT = ROOT / "assets" / "boot" / "source" / "greia-boot-logo.png"
STATIC_OUT = ROOT / "assets" / "boot" / "static" / "greia-boot-logo.png"
TARGET_PPM = ROOT / "build" / "overlay" / "etc" / "greia-boot" / "boot-logo.ppm"
INSTALLER_PPM = ROOT / "build" / "installer-overlay" / "etc" / "greia-boot" / "boot-logo.ppm"


def is_background(pixel: tuple[int, int, int]) -> bool:
    r, g, b = pixel
    return r < 35 and g < 55 and b < 95 and (r + g + b) < _BACKGROUND_THRESHOLD


def derive_white_frame(source: Path) -> Image.Image:
    """Return the canonical logo rendered as dark-on-white from the legacy frame."""
    image = Image.open(source).convert("RGB")
    output = Image.new("RGB", image.size, _WHITE)
    pixels = image.load()
    out = output.load()
    for y in range(image.size[1]):
        for x in range(image.size[0]):
            if not is_background(pixels[x, y]):
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
