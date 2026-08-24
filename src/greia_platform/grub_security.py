"""GRUB credential provisioning for the Greia appliance boot path.

Normal boot remains unrestricted and automatic. Editing boot entries and opening
GRUB's command line use the owner-approved default credential ``greia / greia``.
Only a PBKDF2 hash is stored in the installed target; the plaintext password is
not persisted there. Build tooling may copy the known credential to an external
report for compatibility, but it must never invent a per-image secret by default.
"""

from __future__ import annotations

import argparse
import os
import secrets
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence


GRUB_USER = "greia"
DEFAULT_GRUB_PASSWORD = "greia"
# Compatibility alias for code/tests that still refer to the historical name.
# The actual GRUB identity is now the normal owner/developer identity: greia.
RECOVERY_USER = GRUB_USER
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_HASH_PREFIX = "grub.pbkdf2."


class GrubCredentialError(RuntimeError):
    """Raised when a GRUB owner credential cannot be provisioned safely."""


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
                f"could not generate GRUB password hash: {detail.strip()}"
            ) from exc
        for token in completed.stdout.split():
            if token.startswith(_HASH_PREFIX) and len(token) > len(_HASH_PREFIX) + 16:
                return token
        raise GrubCredentialError("grub-mkpasswd-pbkdf2 returned no usable PBKDF2 hash")


@dataclass(frozen=True, slots=True)
class GrubRecoveryCredential:
    """Compatibility-shaped GRUB credential value.

    ``code`` remains available as a property because older build plumbing used
    that name for the human-entered secret. New code should use ``password``.
    """

    user: str
    password: str
    password_hash: str

    @property
    def code(self) -> str:
        return self.password


def generate_recovery_code(length: int = 20) -> str:
    """Generate an explicit random credential when a caller truly requests one.

    This helper is retained for compatibility and specialist uses only. It is
    deliberately *not* used by the default image/installer provisioning path.
    """

    if not 12 <= length <= 64:
        raise ValueError("GRUB recovery code length must be between 12 and 64 characters")
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))


def _validate_password(password: str) -> str:
    if not password:
        raise GrubCredentialError("GRUB password must not be empty")
    if "\n" in password or "\r" in password:
        raise GrubCredentialError("GRUB password must be a single line")
    if len(password) > 128:
        raise GrubCredentialError("GRUB password is unexpectedly long")
    return password


def provision_recovery_material(
    root: Path,
    *,
    hasher: GrubPasswordHasher | None = None,
    password: str | None = None,
    code: str | None = None,
) -> GrubRecoveryCredential:
    """Write the GRUB PBKDF2 hash below ``root``.

    The default human credential is always ``greia / greia``. ``code`` is
    accepted as a compatibility alias for callers that explicitly supplied the
    old parameter; it never causes random generation. Plaintext is not stored
    inside the target root.
    """

    if password is not None and code is not None:
        raise GrubCredentialError("specify either password or legacy code, not both")

    root = root.resolve()
    grub_password = _validate_password(
        password if password is not None else code if code is not None else DEFAULT_GRUB_PASSWORD
    )
    password_hash = (hasher or SubprocessGrubPasswordHasher()).hash(grub_password)
    if not password_hash.startswith(_HASH_PREFIX):
        raise GrubCredentialError("GRUB password hash has an invalid format")

    state_dir = root / "etc/greia-os"
    state_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(state_dir, 0o755)

    # Remove legacy plaintext material if an older target is being refreshed.
    legacy_code_path = state_dir / "grub-recovery-code"
    legacy_code_path.unlink(missing_ok=True)

    hash_path = state_dir / "grub-recovery.pbkdf2"
    _atomic_private_write(hash_path, password_hash + "\n")
    return GrubRecoveryCredential(GRUB_USER, grub_password, password_hash)


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
        description="Provision the Greia GRUB owner credential as a PBKDF2 hash."
    )
    parser.add_argument("root", type=Path)
    parser.add_argument(
        "--password",
        default=DEFAULT_GRUB_PASSWORD,
        help="GRUB password to hash (default: greia).",
    )
    parser.add_argument(
        "--copy-code-to",
        type=Path,
        help=(
            "Compatibility option: also write the human GRUB password to this "
            "external root-only report. The installed target still stores only the hash."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    credential = provision_recovery_material(args.root, password=args.password)
    if args.copy_code_to is not None:
        args.copy_code_to.parent.mkdir(parents=True, exist_ok=True)
        _atomic_private_write(args.copy_code_to.resolve(), credential.password + "\n")
    print(f"Provisioned GRUB owner user {credential.user}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
