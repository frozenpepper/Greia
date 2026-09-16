from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

from greia_platform.grub_security import DEFAULT_GRUB_PASSWORD, GRUB_USER


ROOT = Path(__file__).resolve().parents[1]


class OwnerRecoveryContractTests(unittest.TestCase):
    def test_canonical_owner_identity_is_greia_greia(self) -> None:
        self.assertEqual(GRUB_USER, "greia")
        self.assertEqual(DEFAULT_GRUB_PASSWORD, "greia")

    def test_installed_grub_auth_uses_canonical_owner(self) -> None:
        script = (
            ROOT / "build/overlay/etc/grub.d/01_greia_auth"
        ).read_text(encoding="utf-8")
        self.assertIn('set superusers="greia"', script)
        self.assertIn("password_pbkdf2 greia $hash", script)
        self.assertNotIn("greia-recovery", script)

    def test_installer_media_grub_uses_canonical_owner(self) -> None:
        builder = (ROOT / "build/build-installer-image.sh").read_text(encoding="utf-8")
        self.assertIn('set superusers="greia"', builder)
        self.assertIn("password_pbkdf2 greia $installer_grub_hash", builder)
        self.assertNotIn('set superusers="greia-recovery"', builder)
        self.assertNotIn("password_pbkdf2 greia-recovery", builder)

    def test_developer_installer_ssh_is_simple_greia_password_login(self) -> None:
        # T02: live-installer SSH composition lives in the shared engine; the
        # thin installer consumer delegates instead of duplicating it. The
        # live path stays simple password-only (the target path keeps its
        # distinct publickey,password floor, so scope the negative there).
        engine = (ROOT / "build/lib/compose.sh").read_text(encoding="utf-8")
        live_start = engine.index("compose_provision_developer_ssh_live()")
        live_end = engine.index("compose_maybe_provision_developer_ssh()", live_start)
        live = engine[live_start:live_end]
        self.assertIn("printf 'greia:greia\\n'", live)
        self.assertIn("AuthenticationMethods password", live)
        self.assertIn("PasswordAuthentication yes", live)
        self.assertIn("KbdInteractiveAuthentication no", live)
        self.assertIn("AllowUsers greia", live)
        self.assertIn("PermitRootLogin no", live)
        self.assertIn("DenyUsers root", live)
        self.assertNotIn("AuthenticationMethods publickey,password", live)
        installer = (ROOT / "build/build-installer-image.sh").read_text(encoding="utf-8")
        self.assertIn('compose_configure_ssh_base "$LIVE_ROOT"', installer)
        self.assertIn('compose_maybe_provision_developer_ssh "$LIVE_ROOT" "live-installer"', installer)
        self.assertNotIn("printf 'greia:greia\\n'", installer)
        self.assertNotIn("AuthenticationMethods password", installer)

    def test_bootstrap_preserves_password_recovery_at_every_ssh_start(self) -> None:
        helper = (
            ROOT / "build/overlay/usr/local/lib/greia-os/prepare-developer-ssh"
        ).read_text(encoding="utf-8")
        unit = (
            ROOT
            / "build/overlay/etc/systemd/system/ssh.service.d/10-greia-developer-bootstrap.conf"
        ).read_text(encoding="utf-8")
        self.assertIn("developer-remote", helper)
        self.assertIn("PasswordAuthentication yes", helper)
        self.assertIn("AuthenticationMethods password", helper)
        self.assertIn("AllowUsers greia", helper)
        self.assertIn("passwd -S greia", helper)
        self.assertIn("prepare-developer-ssh", unit)

    def test_installer_builder_remains_shell_syntax_valid(self) -> None:
        completed = subprocess.run(
            ["bash", "-n", str(ROOT / "build/build-installer-image.sh")],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
