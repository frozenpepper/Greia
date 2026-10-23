"""Self-signed TLS for the Greia Parents LAN service.

Created on the installed device, never embedded into release images.
"""
from __future__ import annotations

import os
import ssl
import subprocess
import tempfile
from pathlib import Path

CERT_NAME = "parent.crt"
KEY_NAME = "parent.key"


def parent_tls_context(state_dir: Path) -> ssl.SSLContext:
    directory = state_dir / "parent-tls"
    if directory.is_symlink():
        raise RuntimeError("Parent TLS state must not be a symlink")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    certificate = directory / CERT_NAME
    key = directory / KEY_NAME
    if certificate.is_symlink() or key.is_symlink():
        raise RuntimeError("Parent TLS certificate/key must not be symlinks")
    if not certificate.exists() and not key.exists():
        _generate_certificate(directory, certificate, key)
    elif not (certificate.is_file() and key.is_file()):
        raise RuntimeError("Parent TLS certificate/key pair is incomplete; no HTTP fallback")
    key.chmod(0o600)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=str(certificate), keyfile=str(key))
    return context


def _generate_certificate(directory: Path, certificate: Path, key: Path) -> None:
    with tempfile.TemporaryDirectory(prefix=".creating-", dir=directory) as scratch:
        temporary = Path(scratch)
        temporary_key = temporary / KEY_NAME
        temporary_cert = temporary / CERT_NAME
        try:
            subprocess.run(
                [
                    "openssl", "req", "-x509", "-newkey", "rsa:2048",
                    "-sha256", "-nodes", "-days", "3650",
                    "-subj", "/CN=Greia Parents",
                    "-addext", "subjectAltName=DNS:greia.local,IP:127.0.0.1",
                    "-keyout", str(temporary_key), "-out", str(temporary_cert),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=30,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("Could not generate Greia Parents HTTPS certificate (openssl required)") from exc
        os.chmod(temporary_key, 0o600)
        os.chmod(temporary_cert, 0o644)
        # A partial pair fails closed; avoid silently rotating certificates.
        os.replace(temporary_key, key)
        os.replace(temporary_cert, certificate)
