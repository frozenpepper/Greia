"""Build staging contract: a fix must reach the image, not just the appliance.

Every defect in the install/first-boot sequence this work recorded was verified
by hand on the reference Acer. Several were then hot-patched onto that machine
to prove the *diagnosis*. A hot patch proves nothing about what a fresh install
contains: the payload is built by applying ``build/overlay`` to the target root
and ``build/installer-overlay`` to the live installer root, then rsyncing the
repository ``src/`` to ``/opt/greia-os``. A fix made only on the appliance, or
only in the wrong overlay, produces an image that is still broken while the
machine in front of you looks perfect.

These tests bind the role-to-overlay mapping and the fixed content to the
repository, so that failure mode is a test failure rather than the next
installer's problem. They parse and assert only; they never invoke the
composition engine, so they need no root and no build.

The mapping is asserted against ``build/lib/compose.sh`` rather than
reimplemented, because a silent change of that mapping would move every fix in
this file to the wrong image.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPOSE = PROJECT_ROOT / "build" / "lib" / "compose.sh"
TARGET_OVERLAY = PROJECT_ROOT / "build" / "overlay"
INSTALLER_OVERLAY = PROJECT_ROOT / "build" / "installer-overlay"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class RoleOverlayMappingTests(unittest.TestCase):
    """The target payload and the live installer take different overlays."""

    def test_compose_maps_each_role_to_its_own_overlay(self) -> None:
        text = _read(COMPOSE)
        body = text[text.index("compose_role_overlay_dir()") :]
        body = body[: body.index("\n}")]
        self.assertIn('printf \'%s\\n\' "$project_root/build/overlay"', body)
        self.assertIn(
            'printf \'%s\\n\' "$project_root/build/installer-overlay"', body
        )
        # target must resolve to the overlay, not the installer overlay.
        target_branch = body[body.index("if [[") : body.index("else")]
        self.assertIn("build/overlay", target_branch)
        self.assertNotIn("installer-overlay", target_branch)

    def test_target_src_is_staged_from_the_repository(self) -> None:
        """`/opt/greia-os/src` is the repository src, so src fixes ship."""

        text = _read(COMPOSE)
        self.assertIn('"$project_root/src" "$project_root/runtime"', text)
        self.assertIn('"$rootfs/opt/greia-os/"', text)
        self.assertIn("--exclude '__pycache__'", text)

    def test_each_changed_artifact_has_exactly_one_build_tree_copy(self) -> None:
        """A second copy in the build tree could shadow the fixed one."""

        wanted = (
            "greia-launcher.service",
            "greia-boot-health-credential.service",
            "greia-install-transaction.service",
            "first-boot",
        )
        build_root = PROJECT_ROOT / "build"
        for name in wanted:
            found = sorted(
                str(p.relative_to(PROJECT_ROOT))
                for p in build_root.rglob(name)
                if p.is_file()
            )
            with self.subTest(artifact=name):
                self.assertEqual(
                    len(found), 1, f"{name} has competing build copies: {found}"
                )


class TargetImageCarriesFirstBootFixesTests(unittest.TestCase):
    """Fixes proven on the appliance must be present in the target overlay."""

    def test_launcher_starts_the_unprivileged_x_server(self) -> None:
        text = _read(TARGET_OVERLAY / "etc/systemd/system/greia-launcher.service")
        exec_lines = [l for l in text.splitlines() if l.startswith("ExecStart=")]
        self.assertEqual(len(exec_lines), 1)
        self.assertIn("/usr/lib/xorg/Xorg :0 vt1", exec_lines[0])
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", ";")):
                continue
            self.assertNotIn("/usr/bin/Xorg", stripped, line)

    def test_boot_health_credential_declares_its_runtime_directory(self) -> None:
        text = _read(
            TARGET_OVERLAY / "etc/systemd/system/greia-boot-health-credential.service"
        )
        self.assertEqual(text.count("RuntimeDirectory=greia-boot-health-authority"), 1)
        self.assertIn("RuntimeDirectoryMode=0700", text)
        self.assertIn("RuntimeDirectoryPreserve=yes", text)

    def test_first_boot_repairs_profile_data_ownership(self) -> None:
        text = _read(TARGET_OVERLAY / "usr/local/lib/greia-os/first-boot")
        self.assertIn("b3-profile-data-ownership-v1", text)
        self.assertIn("chown greiakid:pipprofiles", text)
        self.assertIn("chmod 2770", text)
        # 2755 is the shipped defect: group gets r-x, so the child cannot write.
        self.assertNotIn("chmod 2755", text)
        self.assertNotIn("chmod 0777", text)


class InstallerImageCarriesTransactionFixesTests(unittest.TestCase):
    """The privileged install unit is sized for the install, not for a guess."""

    def test_suid_restriction_is_off_and_declared_once(self) -> None:
        text = _read(
            INSTALLER_OVERLAY
            / "etc/systemd/system/greia-install-transaction.service"
        )
        # Effective directives only: the unit's rationale comments deliberately
        # quote both measured values, so a raw substring count is meaningless.
        # A repeated declaration is dangerous here because the later assignment
        # wins while the file still reads correctly.
        effective = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith(("#", ";"))
        ]
        declared = [l for l in effective if l.startswith("RestrictSUIDSGID=")]
        self.assertEqual(declared, ["RestrictSUIDSGID=no"], declared)
        self.assertNotIn("RestrictSUIDSGID=yes", effective)

    def test_task_limit_clears_the_measured_peak(self) -> None:
        text = _read(
            INSTALLER_OVERLAY
            / "etc/systemd/system/greia-install-transaction.service"
        )
        declared = int(
            re.search(r"^TasksMax=(\d+)$", text, re.MULTILINE).group(1)
        )
        self.assertGreater(declared, 16)

    def test_every_evidenced_capability_is_present(self) -> None:
        text = _read(
            INSTALLER_OVERLAY
            / "etc/systemd/system/greia-install-transaction.service"
        )
        bounding = re.search(
            r"^CapabilityBoundingSet=(.*)$", text, re.MULTILINE
        ).group(1)
        for capability in (
            "CAP_MKNOD",     # unsquashfs device nodes
            "CAP_CHOWN",     # original uid/gid restore
            "CAP_FOWNER",    # chmod of files the caller does not own
            "CAP_FSETID",    # setgid bits; absent, it fails silently
            "CAP_DAC_OVERRIDE",  # apt rename inside /var/lib/apt/lists
        ):
            with self.subTest(capability=capability):
                self.assertIn(capability, bounding)
        # CAP_DAC_READ_SEARCH was tested and is not needed.
        self.assertNotIn("CAP_DAC_READ_SEARCH", bounding)


class RepositorySourceCarriesRuntimeFixesTests(unittest.TestCase):
    """The staged src/ tree must contain the runtime fixes, not a stale copy."""

    def test_boot_health_entry_point_honours_sys_argv(self) -> None:
        text = _read(PROJECT_ROOT / "src/greia_platform/boot_health.py")
        self.assertIn("sys.argv[1:]", text)
        self.assertNotIn("parse_args(list(argv or []))", text)

    def test_history_chmod_failure_names_ownership_and_mode(self) -> None:
        text = _read(PROJECT_ROOT / "src/greia_platform/history.py")
        self.assertIn("owned by the child identity", text)

    def test_install_diagnostics_are_present(self) -> None:
        self.assertIn(
            "_greia_log_event",
            _read(PROJECT_ROOT / "src/greia_installer/transaction_service.py"),
        )
        self.assertIn(
            "greia-installer/status.json",
            _read(PROJECT_ROOT / "src/greia_installer/main.py"),
        )

    def test_no_staged_bytecode_in_the_repository_source(self) -> None:
        stale = [str(p) for p in (PROJECT_ROOT / "src").rglob("__pycache__")]
        self.assertEqual(stale, [])


if __name__ == "__main__":
    unittest.main()
