#!/usr/bin/env python3
"""Validate and install an operator SSH *public* key file for a developer image.

Usage (build host, as root, from build/lib/compose.sh)::

    python3 -I build/lib/operator_key.py SOURCE DESTINATION

SOURCE is the operator's ``authorized_keys``-style file given through
``GREIA_OPERATOR_AUTHORIZED_KEY_FILE``. It is never committed. Only plain
public-key lines are accepted (no ``command=``/``from=`` option prefixes, no
private key material, at most 16 keys, at most 16 KiB). DESTINATION receives
the normalised lines. The script prints one SHA256 fingerprint line per key
(public data only) so the build log records which key was installed.
"""

from __future__ import annotations

import base64
import hashlib
import os
import sys
from pathlib import Path

ALLOWED_KEY_TYPES = frozenset(
    {
        "ssh-ed25519",
        "ssh-rsa",
        "ecdsa-sha2-nistp256",
        "ecdsa-sha2-nistp384",
        "ecdsa-sha2-nistp521",
        "sk-ssh-ed25519@openssh.com",
        "sk-ecdsa-sha2-nistp256@openssh.com",
    }
)
MAX_BYTES = 16 * 1024
MAX_KEYS = 16


class OperatorKeyError(ValueError):
    """The operator key input is not a safe public-key file."""


def parse_public_keys(text: str) -> list[str]:
    if "PRIVATE KEY" in text:
        raise OperatorKeyError("input contains private key material; pass the .pub file")
    keys: list[str] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 2 or fields[0] not in ALLOWED_KEY_TYPES:
            raise OperatorKeyError(
                f"line {number}: expected '<key-type> <base64> [comment]' with a "
                "supported key type and no authorized_keys options"
            )
        try:
            blob = base64.b64decode(fields[1], validate=True)
        except ValueError as exc:
            raise OperatorKeyError(f"line {number}: key data is not base64") from exc
        # The wire blob starts with the length-prefixed key type.
        type_length = int.from_bytes(blob[:4], "big") if len(blob) >= 4 else -1
        if blob[4 : 4 + type_length].decode("ascii", "replace") != fields[0]:
            raise OperatorKeyError(f"line {number}: key data does not match type {fields[0]}")
        comment = " ".join(fields[2:])
        if any(ord(char) < 32 for char in comment):
            raise OperatorKeyError(f"line {number}: control characters in comment")
        keys.append(" ".join(fields[:2] + ([comment] if comment else [])))
    if not keys:
        raise OperatorKeyError("no public key found")
    if len(keys) > MAX_KEYS:
        raise OperatorKeyError(f"too many keys ({len(keys)} > {MAX_KEYS})")
    return keys


def fingerprint(line: str) -> str:
    blob = base64.b64decode(line.split()[1])
    digest = base64.b64encode(hashlib.sha256(blob).digest()).decode("ascii").rstrip("=")
    return f"SHA256:{digest} ({line.split()[0]})"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    source, destination = Path(argv[0]), Path(argv[1])
    try:
        if source.is_symlink() or not source.is_file():
            raise OperatorKeyError(f"{source} is not a regular file")
        if source.stat().st_size > MAX_BYTES:
            raise OperatorKeyError(f"{source} is larger than {MAX_BYTES} bytes")
        keys = parse_public_keys(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, OperatorKeyError) as exc:
        print(f"Operator key refused: {exc}", file=sys.stderr)
        return 1
    staging = destination.with_name(destination.name + ".tmp")
    staging.write_text("".join(f"{key}\n" for key in keys), encoding="utf-8")
    os.chmod(staging, 0o644)
    os.replace(staging, destination)
    for key in keys:
        print(f"operator_ssh_key={fingerprint(key)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
