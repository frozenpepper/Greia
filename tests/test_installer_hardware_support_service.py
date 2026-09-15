from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _directive_text(unit_text: str) -> str:
    """Return only systemd directive lines (skip blanks/comments).

    A line is a comment when its first non-whitespace character is
    ``#`` or ``;``.  Everything else — including section headers and
    directives with trailing comments — is kept verbatim so the
    absence guards measure enforcement, not prose.
    """
    kept: list[str] = []
    for line in unit_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith(";"):
            continue
        kept.append(line)
    return "\n".join(kept)


class InstallerHardwareSupportServiceTests(unittest.TestCase):
    def test_root_transaction_service_explicitly_opts_into_frozen_hardware_support(self) -> None:
        # Step 8A.5 split: the unprivileged UI owns no pool/profile facts.
        # The root transaction service rematerializes them from its own
        # Greia-owned environment.
        service = (
            PROJECT_ROOT
            / "build/installer-overlay/etc/systemd/system/greia-install-transaction.service"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "Environment=GREIA_HARDWARE_SUPPORT_POOL=/opt/greia-hardware-support",
            service,
        )
        self.assertIn(
            "Environment=GREIA_TARGET_IMAGE_PROFILE=/etc/greia-os/target-image-profile.json",
            service,
        )
        ui = (
            PROJECT_ROOT
            / "build/installer-overlay/etc/systemd/system/greia-installer.service"
        ).read_text(encoding="utf-8")
        self.assertNotIn("GREIA_HARDWARE_SUPPORT_POOL", _directive_text(ui))

    def test_service_does_not_grant_network_or_vendor_driver_install_commands(self) -> None:
        for unit_name in (
            "greia-installer.service",
            "greia-install-transaction.service",
        ):
            with self.subTest(unit=unit_name):
                service = (
                    PROJECT_ROOT
                    / "build/installer-overlay/etc/systemd/system"
                    / unit_name
                ).read_text(encoding="utf-8")
                directives = _directive_text(service)
                self.assertNotIn("apt-get", directives)
                self.assertNotIn("curl", directives)
                self.assertNotIn("wget", directives)

    def test_directive_scope_positive_control(self) -> None:
        # Comment-only mention of a guarded tool is not enforcement.
        comment_only = (
            "# Never fetch vendor drivers with curl here.\n"
            "   # apt-get would also be forbidden in a directive.\n"
            "   ; wget likewise.\n"
            "\n"
            "[Service]\n"
            "ExecStart=/usr/bin/python3 -m greia_installer.transaction_service\n"
        )
        comment_directives = _directive_text(comment_only)
        self.assertNotIn("apt-get", comment_directives)
        self.assertNotIn("curl", comment_directives)
        self.assertNotIn("wget", comment_directives)

        # A real directive naming a guarded tool is enforcement and hits.
        directive_hit = (
            "[Service]\n"
            "ExecStart=/usr/bin/curl https://example.invalid/driver\n"
        )
        self.assertIn("curl", _directive_text(directive_hit))


if __name__ == "__main__":
    unittest.main()
