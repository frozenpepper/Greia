from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from greia_platform.main_credential import (
    INITIAL_PARENT_PASSWORD,
    INITIAL_PARENT_USERNAME,
    MainCredentialError,
    MainCredentialStore,
    _validate_password,
)


class MainCredentialTests(unittest.TestCase):
    def test_initial_parent_credential_is_simple_and_predictable(self) -> None:
        self.assertEqual(INITIAL_PARENT_USERNAME, "greia")
        self.assertEqual(INITIAL_PARENT_PASSWORD, "greia")

    def test_store_seeds_default_and_verifies_initial_password(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = MainCredentialStore(Path(temporary) / "main-credential.json")
            store.ensure_initialized()
            self.assertTrue(store.verify("greia"))
            self.assertFalse(store.verify("wrong"))

    def test_store_persists_only_a_digest_never_plaintext(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "main-credential.json"
            store = MainCredentialStore(path)
            store.ensure_initialized()
            raw = path.read_text(encoding="utf-8")
            self.assertNotIn("greia", json.loads(raw).get("digest", ""))
            self.assertNotIn("greia", raw)
            self.assertIn("pbkdf2-sha256", raw)
            self.assertNotIn("password", raw)

    def test_change_requires_current_password_and_rejects_old_after(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = MainCredentialStore(Path(temporary) / "main-credential.json")
            store.ensure_initialized()
            with self.assertRaises(MainCredentialError):
                store.change("wrong-current", "newpass1")
            store.change("greia", "newpass1")
            self.assertTrue(store.verify("newpass1"))
            self.assertFalse(store.verify("greia"))

    def test_password_validation_bounds(self) -> None:
        with self.assertRaises(MainCredentialError):
            _validate_password("abc")
        with self.assertRaises(MainCredentialError):
            _validate_password("x" * 65)
        with self.assertRaises(MainCredentialError):
            _validate_password("has\nnewline")
        self.assertEqual(_validate_password("greia"), "greia")


if __name__ == "__main__":
    unittest.main()
