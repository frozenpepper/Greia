from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_platform.grub_security import (
    GrubCredentialError,
    SubprocessGrubPasswordHasher,
    generate_recovery_code,
    provision_recovery_material,
)


class FakeHasher:
    def hash(self, secret: str) -> str:
        return "grub.pbkdf2.sha512.10000.TESTHASH" + secret[:2]


class GrubSecurityTests(unittest.TestCase):
    def test_generated_codes_avoid_ambiguous_characters(self) -> None:
        code = generate_recovery_code()
        self.assertEqual(len(code), 20)
        self.assertFalse(set(code) & set("01IO"))

    def test_provisioning_writes_root_only_code_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            credential = provision_recovery_material(
                root,
                hasher=FakeHasher(),
                code="ABCDEFGHJKLMNPQRSTUV",
            )
            code_path = root / "etc/greia-os/grub-recovery-code"
            hash_path = root / "etc/greia-os/grub-recovery.pbkdf2"
            self.assertEqual(code_path.read_text().strip(), credential.code)
            self.assertTrue(hash_path.read_text().startswith("grub.pbkdf2."))
            self.assertEqual(os.stat(code_path).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(hash_path).st_mode & 0o777, 0o600)

    def test_invalid_custom_code_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(GrubCredentialError):
                provision_recovery_material(
                    Path(temporary),
                    hasher=FakeHasher(),
                    code="contains-lowercase",
                )

    def test_subprocess_hasher_extracts_only_grub_pbkdf2_token(self) -> None:
        completed = subprocess.CompletedProcess(
            ["grub-mkpasswd-pbkdf2"],
            0,
            "Enter password: PBKDF2 hash of your password is grub.pbkdf2.sha512.10000.ABCDEF\n",
            "",
        )
        with mock.patch("greia_platform.grub_security.subprocess.run", return_value=completed) as run:
            result = SubprocessGrubPasswordHasher().hash("ABCDEFGHJKLM")
        self.assertEqual(result, "grub.pbkdf2.sha512.10000.ABCDEF")
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertIn("ABCDEFGHJKLM\nABCDEFGHJKLM\n", run.call_args.kwargs["input"])


if __name__ == "__main__":
    unittest.main()
