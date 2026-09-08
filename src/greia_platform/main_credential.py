"""Platform-owned main Parent credential.

Greia keeps exactly one human-readable admin credential for the initial
installation/management identity. Per the active owner policy it starts as
``greia`` / ``greia`` and may be changed from Greia Parents. Only a password
digest is persisted; no API or log path ever returns the password or its digest.

This is deliberately separate from per-parent-device bearer credentials managed
by ``greia_parent.credentials``. Device credentials are individually revocable
client identities; the main Parent password is the Greia-level admin identity.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import tempfile
from dataclasses import dataclass
from pathlib import Path


INITIAL_PARENT_USERNAME = "greia"
INITIAL_PARENT_PASSWORD = "greia"
SCHEMA_VERSION = 1
_DEFAULT_ITERATIONS = 120_000
MIN_PASSWORD_CHARACTERS = 4
MAX_PASSWORD_CHARACTERS = 64
_MAX_STATE_BYTES = 64 * 1024


class MainCredentialError(ValueError):
    """The main Parent credential store is invalid or a change was rejected."""


@dataclass(frozen=True, slots=True)
class MainCredentialDigest:
    salt: str
    digest: str
    iterations: int

    @classmethod
    def create(cls, password: str, iterations: int = _DEFAULT_ITERATIONS) -> "MainCredentialDigest":
        salt = secrets.token_bytes(16)
        derived = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations
        )
        return cls(
            salt=base64.b64encode(salt).decode("ascii"),
            digest=base64.b64encode(derived).decode("ascii"),
            iterations=iterations,
        )

    def verify(self, password: str) -> bool:
        try:
            salt = base64.b64decode(self.salt.encode("ascii"), validate=True)
            expected = base64.b64decode(self.digest.encode("ascii"), validate=True)
        except (ValueError, UnicodeEncodeError):
            return False
        if self.iterations < 10_000 or self.iterations > 2_000_000:
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, self.iterations
        )
        return hmac.compare_digest(candidate, expected)

    def as_json_dict(self) -> dict[str, object]:
        return {
            "algorithm": "pbkdf2-sha256",
            "salt": self.salt,
            "digest": self.digest,
            "iterations": self.iterations,
        }


class MainCredentialStore:
    """Own the main Parent password as a bounded PBKDF2 digest.

    The store is intentionally small and typed: ``ensure_initialized`` seeds the
    owner-approved default, ``verify`` checks a candidate without revealing the
    digest, and ``change`` requires the current password before replacing the
    stored digest. The web Parent service can therefore manage the credential
    without ever receiving or storing plaintext application state.
    """

    def __init__(self, path: Path, iterations: int = _DEFAULT_ITERATIONS):
        self.path = path.resolve()
        self.iterations = iterations

    @classmethod
    def from_environment(cls) -> "MainCredentialStore":
        root = Path(
            os.environ.get("GREIA_MAIN_CREDENTIAL_PATH", "/var/lib/greia-os/main-credential.json")
        ).resolve()
        return cls(root)

    def ensure_initialized(self) -> None:
        if self.path.is_file():
            os.chmod(self.path, 0o600)
            return
        digest = MainCredentialDigest.create(
            INITIAL_PARENT_PASSWORD, self.iterations
        )
        self._write(digest)

    def verify(self, candidate: str) -> bool:
        digest = self._read()
        if digest is None:
            return False
        return digest.verify(candidate)

    def change(self, current: str, new: str) -> None:
        validated = _validate_password(new)
        if not self.verify(current):
            raise MainCredentialError("current Parent password is incorrect")
        self._write(MainCredentialDigest.create(validated, self.iterations))

    def _read(self) -> MainCredentialDigest | None:
        if not self.path.exists():
            return None
        if self.path.is_symlink():
            raise MainCredentialError("main credential state must not be a symlink")
        try:
            stat = self.path.stat()
            if not self.path.is_file() or stat.st_size > _MAX_STATE_BYTES:
                raise MainCredentialError("main credential state has invalid size/type")
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except MainCredentialError:
            raise
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MainCredentialError("main credential state is invalid") from exc
        if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
            raise MainCredentialError("unsupported main credential schema")
        if raw.get("algorithm") != "pbkdf2-sha256":
            raise MainCredentialError("unsupported main credential algorithm")
        salt = raw.get("salt")
        digest = raw.get("digest")
        iterations = raw.get("iterations")
        if not isinstance(salt, str) or not isinstance(digest, str):
            raise MainCredentialError("main credential digest is invalid")
        if (
            not isinstance(iterations, int)
            or isinstance(iterations, bool)
            or iterations < 10_000
            or iterations > 2_000_000
        ):
            raise MainCredentialError("main credential iterations are invalid")
        try:
            decoded_salt = base64.b64decode(salt.encode("ascii"), validate=True)
            decoded_digest = base64.b64decode(digest.encode("ascii"), validate=True)
        except (ValueError, UnicodeEncodeError) as exc:
            raise MainCredentialError("main credential digest is invalid") from exc
        if len(decoded_salt) != 16 or len(decoded_digest) != hashlib.sha256().digest_size:
            raise MainCredentialError("main credential digest has an invalid size")
        return MainCredentialDigest(salt, digest, iterations)

    def _write(self, digest: MainCredentialDigest) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            **digest.as_json_dict(),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        if len(encoded.encode("utf-8")) > _MAX_STATE_BYTES:
            raise MainCredentialError("main credential state exceeds size limit")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=self.path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
            os.chmod(self.path, 0o600)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise


def _validate_password(password: str) -> str:
    if not isinstance(password, str):
        raise MainCredentialError("Parent password must be text")
    if len(password) < MIN_PASSWORD_CHARACTERS or len(password) > MAX_PASSWORD_CHARACTERS:
        raise MainCredentialError(
            f"Parent password must be {MIN_PASSWORD_CHARACTERS}-{MAX_PASSWORD_CHARACTERS} characters"
        )
    if any(character in "\r\n\x00" for character in password):
        raise MainCredentialError("Parent password contains unsupported characters")
    return password
