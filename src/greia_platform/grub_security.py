"""GRUB recovery credential provisioning for the kiosk appliance boot path.

Normal boot remains unrestricted and automatic. Editing boot entries and opening
GRUB's command line require a per-machine recovery credential stored root-only on
the installed system. The child launcher and activities never receive it.
"""

from __future__ import annotations

import argparse
import os
import secrets
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence


RECOVERY_USER = "greia-recovery"
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_HASH_PREFIX = "grub.pbkdf2."


class GrubCredentialError(RuntimeError):
    """Raised when a secure GRUB recovery credential cannot be provisioned."""


class GrubPasswordHasher(Protocol):
    def hash(self, secret: str) -> str: ...


class SubprocessGrubPasswordHasher:
    def __init__(self, executable: str = "grub-mkpasswd-pbkdf2"):
        self.executable = executable

    def hash(self, secret: str) -> str:
        try:
            completed = subprocess.run(
                [self.executable],
                input=f"{secret}\n{secret}\n",
                check=True,
                shell=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            detail = getattr(exc, "stderr", "") or str(exc)
            raise GrubCredentialError(
                f"could not generate GRUB recovery password hash: {detail.strip()}"
            ) from exc
        for token in completed.stdout.split():
            if token.startswith(_HASH_PREFIX) and len(token) > len(_HASH_PREFIX) + 16:
                return token
        raise GrubCredentialError("grub-mkpasswd-pbkdf2 returned no usable PBKDF2 hash")


@dataclass(frozen=True, slots=True)
class GrubRecoveryCredential:
    user: str
    code: str
    password_hash: str


def generate_recovery_code(length: int = 20) -> str:
    if not 12 <= length <= 64:
        raise ValueError("GRUB recovery code length must be between 12 and 64 characters")
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))


def provision_recovery_material(
    root: Path,
    *,
    hasher: GrubPasswordHasher | None = None,
    code: str | None = None,
) -> GrubRecoveryCredential:
    """Write one root-only recovery code and PBKDF2 hash below ``root``."""

    root = root.resolve()
    recovery_code = code or generate_recovery_code()
    if not recovery_code or any(character not in _CODE_ALPHABET for character in recovery_code):
        raise GrubCredentialError("recovery code contains unsupported characters")
    password_hash = (hasher or SubprocessGrubPasswordHasher()).hash(recovery_code)
    if not password_hash.startswith(_HASH_PREFIX):
        raise GrubCredentialError("GRUB recovery password hash has an invalid format")

    state_dir = root / "etc/greia-os"
    state_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(state_dir, 0o755)
    code_path = state_dir / "grub-recovery-code"
    hash_path = state_dir / "grub-recovery.pbkdf2"
    _atomic_private_write(code_path, recovery_code + "\n")
    _atomic_private_write(hash_path, password_hash + "\n")
    return GrubRecoveryCredential(RECOVERY_USER, recovery_code, password_hash)


def _atomic_private_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(content, encoding="ascii")
        os.chmod(temporary, 0o600)
        temporary.replace(path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Provision a per-image GRUB recovery code and PBKDF2 hash."
    )
    parser.add_argument("root", type=Path)
    parser.add_argument(
        "--copy-code-to",
        type=Path,
        help="Also write the generated recovery code to this external root-only file.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    credential = provision_recovery_material(args.root)
    if args.copy_code_to is not None:
        args.copy_code_to.parent.mkdir(parents=True, exist_ok=True)
        _atomic_private_write(args.copy_code_to.resolve(), credential.code + "\n")
    print(f"Provisioned GRUB recovery user {credential.user}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
