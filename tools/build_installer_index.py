#!/usr/bin/env python3
"""Register a published installer image in the public Greia index.

The website's Downloads page reads the same static ``greia-updates.json`` that
Parent clients use for update discovery. Installer images live in a separate
``greia_os.installers`` list next to ``greia_os.channels``; device and Parent
update readers only read ``channels``, so an installer entry never becomes an
update offer. Like the rest of the index this is discovery only: the SHA-256 is
a transfer check for the person downloading, not a signature.

Typical use after uploading the image to the site's ``os-images/`` folder::

    python3 tools/build_installer_index.py \\
        --image ../greia-os-installer-i386-ab-0.13.1-preview.1-build-9ba22f764ed1.img \\
        --base-url https://www.frozenpepper.it/greia/os-images \\
        --target legacy-x86-i386 --status technical-preview \\
        --notes-en notes-en.txt --notes-it notes-it.txt \\
        --index ../website/updates/greia-updates.json

Version and build are read from the standard installer file name
(``greia-os-installer-<profile>-<version>-build-<commit>.img``, as written by
``build/build-installer-image.sh``) unless given explicitly. The builder's
version-less compatibility symlink is resolved to the real file first. The newest entries per target are listed first; the newest
three per target are kept. Image files are never deleted.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_update_index as _index  # noqa: E402  (shared load/write/hash helpers)

STATUSES = ("technical-preview", "release")
BOOT_MODES = ("bios", "uefi", "uefi-experimental")
DEFAULT_KEEP = 3
# Common USB stick sizes; the page tells people the smallest one that fits.
MEDIA_SIZES_GB = (2, 4, 8, 16, 32, 64)
_IMAGE_NAME = re.compile(
    r"^greia-os-installer-(?P<profile>[a-z0-9][a-z0-9_-]*?)-"
    r"(?P<version>\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?)-build-(?P<build>[0-9a-f]{7,40})\.img$"
)
_TARGET = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

# Defaults per target so a routine publish needs only the image and notes.
TARGETS: dict[str, dict[str, object]] = {
    "legacy-x86-i386": {
        "title": "Netbooks & PCs",
        "platform_family": "legacy-x86",
        "architecture": "i386",
        "boot": ["bios", "uefi-experimental"],
        "reference_hardware": ["Acer Aspire One (first generation)"],
    },
}


def parse_image_name(name: str) -> dict[str, str]:
    match = _IMAGE_NAME.fullmatch(name)
    return match.groupdict() if match else {}


def minimum_media_gb(size: int) -> int:
    for gigabytes in MEDIA_SIZES_GB:
        # Sticks are sold in decimal GB and real capacity is a little lower.
        if size <= gigabytes * 1000**3 * 0.93:
            return gigabytes
    raise SystemExit("image is larger than the supported USB size table")


def installer_entry(
    image: Path,
    *,
    base_url: str,
    target: str,
    status: str,
    version: str | None,
    build: str | None,
    notes: dict[str, str],
    published_at: str,
) -> dict[str, object]:
    if not image.is_file():
        raise SystemExit(f"{image}: image not found")
    image = image.resolve()
    if not _TARGET.fullmatch(target):
        raise SystemExit(f"{target!r}: target id must be lower-case letters, digits and dashes")
    parsed = parse_image_name(image.name)
    version = version or parsed.get("version")
    build = build or parsed.get("build")
    if not version:
        raise SystemExit(f"{image.name}: cannot read the version; pass --version")
    defaults = TARGETS.get(target, {})
    size = image.stat().st_size
    return {
        "id": target,
        "title": defaults.get("title", target),
        "version": version,
        "build": build,
        "status": status,
        "published_at": published_at,
        "platform_family": defaults.get("platform_family"),
        "architecture": defaults.get("architecture"),
        "boot": list(defaults.get("boot", ["bios"])),
        "reference_hardware": list(defaults.get("reference_hardware", [])),
        "min_media_gb": minimum_media_gb(size),
        "notes": notes,
        "image": {
            "url": f"{base_url.rstrip('/')}/{image.name}",
            "file_name": image.name,
            "size": size,
            "sha256": _index.sha256_file(image),
        },
    }


def merge_installer(index: dict[str, object], entry: dict[str, object], *, keep: int = DEFAULT_KEEP) -> dict[str, object]:
    greia_os = index.setdefault("greia_os", {})
    current = greia_os.get("installers") or []  # type: ignore[union-attr]
    others = [item for item in current if item.get("id") != entry["id"]]
    same_target = [
        item for item in current
        if item.get("id") == entry["id"] and item.get("version") != entry["version"]
    ]
    greia_os["installers"] = [entry, *same_target[: keep - 1], *others]  # type: ignore[index]
    index["updated_at"] = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--image", required=True, type=Path, help="the exact installer image that was uploaded")
    parser.add_argument("--base-url", required=True, help="public folder URL where the image is hosted")
    parser.add_argument("--index", required=True, type=Path, help="greia-updates.json to create or update")
    parser.add_argument("--target", default="legacy-x86-i386", help="hardware target id (one current image per target)")
    parser.add_argument("--status", choices=STATUSES, default="technical-preview")
    parser.add_argument("--version")
    parser.add_argument("--build", help="short source commit of the build")
    parser.add_argument("--boot", action="append", choices=BOOT_MODES,
                        help="boot modes, repeatable (default: the target's known modes)")
    parser.add_argument("--notes-en")
    parser.add_argument("--notes-it")
    parser.add_argument("--notes-es")
    parser.add_argument("--notes-fr")
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP, help="entries kept per target (default: 3)")
    parser.add_argument("--published-at", default=_dt.date.today().isoformat())
    args = parser.parse_args(argv)

    if not 1 <= args.keep <= 16:
        parser.error("--keep must be between 1 and 16")
    if not args.base_url.startswith("https://"):
        parser.error("--base-url must be https")
    notes = {locale: value for locale in ("en", "it", "es", "fr")
             if (value := _index.read_notes(getattr(args, f"notes_{locale}")))}
    entry = installer_entry(
        args.image, base_url=args.base_url, target=args.target, status=args.status,
        version=args.version, build=args.build, notes=notes, published_at=args.published_at,
    )
    if args.boot:
        entry["boot"] = args.boot
    index = _index.load_index(args.index)
    merge_installer(index, entry, keep=args.keep)
    _index.write_index(args.index, index)
    image = entry["image"]
    print(f"{args.index}: {entry['id']} {entry['version']} -> {image['url']} "  # type: ignore[index]
          f"({image['size']} bytes, sha256 {image['sha256']})")  # type: ignore[index]
    return 0


if __name__ == "__main__":
    sys.exit(main())
