from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_platform.grub_security import (
    DEFAULT_GRUB_PASSWORD,
    GRUB_USER,
    GrubCredentialError,
    SubprocessGrubPasswordHasher,
    generate_recovery_code,
    provision_recovery_material,
)


class FakeHasher:
    def __init__(self) -> None:
        self.secrets: list[str] = []

    def hash(self, secret: str) -> str:
        self.secrets.append(secret)
        return "grub.pbkdf2.sha512.10000.TESTHASH" + secret[:2]


class GrubSecurityTests(unittest.TestCase):
    def test_owner_default_is_explicitly_greia_greia(self) -> None:
        self.assertEqual(GRUB_USER, "greia")
        self.assertEqual(DEFAULT_GRUB_PASSWORD, "greia")

    def test_generated_random_code_remains_explicit_opt_in_helper(self) -> None:
        code = generate_recovery_code()
        self.assertEqual(len(code), 20)
        self.assertFalse(set(code) & set("01IO"))
        self.assertNotEqual(code, DEFAULT_GRUB_PASSWORD)

    def test_default_provisioning_hashes_greia_without_storing_plaintext_in_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hasher = FakeHasher()
            credential = provision_recovery_material(root, hasher=hasher)
            hash_path = root / "etc/greia-os/grub-recovery.pbkdf2"
            legacy_code_path = root / "etc/greia-os/grub-recovery-code"

            self.assertEqual(credential.user, "greia")
            self.assertEqual(credential.password, "greia")
            self.assertEqual(credential.code, "greia")
            self.assertEqual(hasher.secrets, ["greia"])
            self.assertTrue(hash_path.read_text().startswith("grub.pbkdf2."))
            self.assertFalse(legacy_code_path.exists())
            self.assertEqual(os.stat(hash_path).st_mode & 0o777, 0o600)

    def test_refresh_removes_legacy_plaintext_code_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_dir = root / "etc/greia-os"
            state_dir.mkdir(parents=True)
            legacy = state_dir / "grub-recovery-code"
            legacy.write_text("OLD-RANDOM-SECRET\n", encoding="ascii")

            provision_recovery_material(root, hasher=FakeHasher())

            self.assertFalse(legacy.exists())

    def test_explicit_custom_password_is_supported_without_changing_user(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            hasher = FakeHasher()
            credential = provision_recovery_material(
                Path(temporary),
                hasher=hasher,
                password="owner-choice",
            )
            self.assertEqual(credential.user, GRUB_USER)
            self.assertEqual(credential.password, "owner-choice")
            self.assertEqual(hasher.secrets, ["owner-choice"])

    def test_legacy_code_parameter_is_only_an_explicit_password_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            credential = provision_recovery_material(
                Path(temporary),
                hasher=FakeHasher(),
                code="legacy-explicit",
            )
            self.assertEqual(credential.password, "legacy-explicit")

    def test_invalid_password_shape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for password in ("", "bad\npassword", "bad\rpassword", "x" * 129):
                with self.subTest(password=repr(password)):
                    with self.assertRaises(GrubCredentialError):
                        provision_recovery_material(
                            root,
                            hasher=FakeHasher(),
                            password=password,
                        )

    def test_password_and_legacy_code_cannot_both_be_supplied(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(GrubCredentialError):
                provision_recovery_material(
                    Path(temporary),
                    hasher=FakeHasher(),
                    password="greia",
                    code="other",
                )

    def test_subprocess_hasher_extracts_only_grub_pbkdf2_token(self) -> None:
        completed = subprocess.CompletedProcess(
            ["grub-mkpasswd-pbkdf2"],
            0,
            "Enter password: PBKDF2 hash of your password is grub.pbkdf2.sha512.10000.ABCDEF\n",
            "",
        )
        with mock.patch("greia_platform.grub_security.subprocess.run", return_value=completed) as run:
            result = SubprocessGrubPasswordHasher().hash("greia")
        self.assertEqual(result, "grub.pbkdf2.sha512.10000.ABCDEF")
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertIn("greia\ngreia\n", run.call_args.kwargs["input"])


if __name__ == "__main__":
    unittest.main()
