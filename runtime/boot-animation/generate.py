#!/usr/bin/env python3
"""Generate Greia's Acer-safe Plymouth frames from canonical compressed data."""
from __future__ import annotations

import argparse
import base64
import binascii
import bz2
import hashlib
import os
from pathlib import Path
import struct
import tempfile
import zlib

WIDTH = 222
HEIGHT = 600
CHANNELS = 3
FRAME_COUNT = 52
FPS = 7
CHUNK_COUNT = 24
FRAME_BYTES = WIDTH * HEIGHT * CHANNELS
RAW_STREAM_BYTES = FRAME_BYTES * FRAME_COUNT
COMPRESSED_SHA256 = "1d96618f67f087e39e68fcba37fe2bf020079d497e4361bd1b12e2f9460445b2"
RAW_STREAM_SHA256 = "3c0fd1190d51e4222eb0cd6f013a78e2e7ed0c68df14b434e19652a4643a871f"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class AnimationDataError(RuntimeError):
    pass


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_compressed_payload(data_dir: Path) -> bytes:
    expected_names = [f"chunk_{index:03d}.b85" for index in range(CHUNK_COUNT)]
    actual_names = sorted(path.name for path in data_dir.glob("chunk_*.b85") if path.is_file())
    if actual_names != expected_names:
        raise AnimationDataError(
            f"boot-animation chunks do not match canonical sequence: expected {expected_names!r}, got {actual_names!r}"
        )
    encoded = "".join(
        (data_dir / name).read_text(encoding="ascii").strip()
        for name in expected_names
    )
    try:
        compressed = base64.b85decode(encoded.encode("ascii"))
    except (ValueError, binascii.Error) as exc:
        raise AnimationDataError("boot-animation base85 payload is invalid") from exc
    digest = _sha256(compressed)
    if digest != COMPRESSED_SHA256:
        raise AnimationDataError(
            f"boot-animation compressed SHA-256 mismatch: expected {COMPRESSED_SHA256}, got {digest}"
        )
    return compressed


def _read_delta_stream(data_dir: Path) -> bytes:
    try:
        raw = bz2.decompress(_read_compressed_payload(data_dir))
    except OSError as exc:
        raise AnimationDataError("boot-animation bzip2 payload is invalid") from exc
    if len(raw) != RAW_STREAM_BYTES:
        raise AnimationDataError(
            f"boot-animation raw byte count mismatch: expected {RAW_STREAM_BYTES}, got {len(raw)}"
        )
    digest = _sha256(raw)
    if digest != RAW_STREAM_SHA256:
        raise AnimationDataError(
            f"boot-animation raw SHA-256 mismatch: expected {RAW_STREAM_SHA256}, got {digest}"
        )
    return raw


def _frames_from_delta_stream(raw: bytes):
    previous = raw[:FRAME_BYTES]
    yield previous
    for index in range(1, FRAME_COUNT):
        start = index * FRAME_BYTES
        delta = raw[start : start + FRAME_BYTES]
        current = bytes(
            left ^ right for left, right in zip(previous, delta, strict=True)
        )
        yield current
        previous = current


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(kind)
    checksum = zlib.crc32(payload, checksum) & 0xFFFFFFFF
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", checksum)
    )


def _png_bytes(rgb: bytes) -> bytes:
    if len(rgb) != FRAME_BYTES:
        raise AnimationDataError(f"unexpected RGB frame size: {len(rgb)}")
    stride = WIDTH * CHANNELS
    scanlines = b"".join(
        b"\x00" + rgb[row * stride : (row + 1) * stride]
        for row in range(HEIGHT)
    )
    ihdr = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    return b"".join(
        (
            PNG_SIGNATURE,
            _png_chunk(b"IHDR", ihdr),
            _png_chunk(b"IDAT", zlib.compress(scanlines, 9)),
            _png_chunk(b"IEND", b""),
        )
    )


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def generate_frames(data_dir: Path, output_dir: Path) -> tuple[int, int]:
    raw = _read_delta_stream(data_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    expected = {f"frame_{index:04d}.png" for index in range(FRAME_COUNT)}
    unexpected = sorted(
        path.name
        for path in output_dir.glob("frame_*.png")
        if path.is_file() and path.name not in expected
    )
    if unexpected:
        raise AnimationDataError(
            f"unexpected boot-animation frames already exist: {unexpected!r}"
        )
    total_bytes = 0
    count = 0
    for index, rgb in enumerate(_frames_from_delta_stream(raw)):
        payload = _png_bytes(rgb)
        _atomic_write(output_dir / f"frame_{index:04d}.png", payload)
        total_bytes += len(payload)
        count += 1
    if count != FRAME_COUNT:
        raise AnimationDataError(f"generated {count} frames; expected {FRAME_COUNT}")
    return count, total_bytes


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("/opt/greia-os/runtime/boot-animation/data"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/usr/share/plymouth/themes/greia/frames"),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    count, total_bytes = generate_frames(args.data_dir, args.output_dir)
    print(
        f"Greia boot animation: generated {count} frames ({total_bytes} bytes) "
        f"at {WIDTH}x{HEIGHT}, {FPS} fps."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
