from __future__ import annotations

import os
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RealHardwareInstallationRegressionTests(unittest.TestCase):
    """Source-level locks for failures discovered on physical legacy hardware.

    These are intentionally hardware-family-neutral. They protect build/session
    invariants that were learned on the Acer but must remain true for every
    installer/target profile built away from its eventual machine.
    """

    def read(self, relative: str) -> str:
        return (PROJECT_ROOT / relative).read_text(encoding="utf-8")

    def test_live_media_identity_and_payload_are_built_together(self) -> None:
        builder = self.read("build/build-installer-image.sh")
        self.assertIn('"$USB_MOUNT/.disk/live-uuid"', builder)
        self.assertIn('"$USB_MOUNT/payload/pip-rootfs.squashfs"', builder)
        self.assertIn('"$USB_MOUNT/payload/pip-rootfs.squashfs.sha256"', builder)
        self.assertIn('"$USB_MOUNT/payload/target-image-profile.json"', builder)
        self.assertIn("greia.live_media_id=$live_media_id", builder)

    def test_target_and_live_initramfs_keep_target_kernel_storage_policy(self) -> None:
        for prefix in ("build/overlay", "build/installer-overlay"):
            with self.subTest(prefix=prefix):
                config = self.read(f"{prefix}/etc/initramfs-tools/conf.d/greia-hardware")
                modules = self.read(f"{prefix}/etc/initramfs-tools/modules")
                hook_path = PROJECT_ROOT / prefix / "etc/initramfs-tools/hooks/greia-storage-modules"
                hook = hook_path.read_text(encoding="utf-8")
                self.assertIn("MODULES=most", config)
                self.assertTrue(os.access(hook_path, os.X_OK))
                self.assertIn("modinfo", hook)
                self.assertIn("manual_add_modules", hook)
                # Shared overlays must not force x86-only modules on every future
                # architecture. The hook consults the TARGET kernel instead.
                module_lines = {
                    line.strip()
                    for line in modules.splitlines()
                    if line.strip() and not line.lstrip().startswith("#")
                }
                for module in ("ahci", "libata", "sd_mod"):
                    self.assertNotIn(module, module_lines)
                    self.assertIn(module, hook)

    def test_graphical_services_can_never_inherit_the_vt_as_stdin(self) -> None:
        for unit in (
            "build/installer-overlay/etc/systemd/system/greia-installer.service",
            "build/overlay/etc/systemd/system/greia-launcher.service",
        ):
            with self.subTest(unit=unit):
                text = self.read(unit)
                self.assertIn("StandardInput=null", text)
                self.assertNotIn("StandardInput=tty", text)
        engine = self.read("src/greia_installer/engine.py")
        self.assertIn("stdin=subprocess.DEVNULL", engine)

    def test_shared_runtime_directories_are_recreated_before_services_every_boot(self) -> None:
        tmpfiles = self.read("build/overlay/etc/tmpfiles.d/greia-runtime.conf")
        launcher = self.read("build/overlay/etc/systemd/system/greia-launcher.service")
        parent = self.read("build/overlay/etc/systemd/system/greia-parent.service")
        first_boot = self.read("build/overlay/usr/local/lib/greia-os/first-boot")
        prepare = self.read("build/overlay/usr/local/lib/greia-os/prepare-launcher-vt")

        self.assertIn("d /run/greia-os       0770 greiakid pipprofiles", tmpfiles)
        self.assertIn("d /run/greia-hardware 2750 greiakid greiapanel", tmpfiles)
        self.assertIn("systemd-tmpfiles-setup.service", launcher)
        self.assertIn("systemd-tmpfiles-setup.service", parent)
        # Shared runtime ownership must not depend on which app starts first.
        self.assertNotIn("RuntimeDirectory=greia-os", launcher)
        self.assertNotIn("/run/greia-hardware", first_boot)
        self.assertIn("Missing Greia runtime root", prepare)
        self.assertNotIn("chown greiakid:pipprofiles /run/greia-os", prepare)

    def test_parent_activity_root_remains_traversable_without_exposing_private_children(self) -> None:
        first_boot = self.read("build/overlay/usr/local/lib/greia-os/first-boot")
        parent_unit = self.read("build/overlay/etc/systemd/system/greia-parent.service")
        self.assertIn(
            "install -d -m 0755 -o greiapanel -g greiapanel /var/lib/greia-os",
            first_boot,
        )
        self.assertIn("StateDirectory=greia-os", parent_unit)
        self.assertIn("StateDirectoryMode=0755", parent_unit)
        self.assertIn(
            "GREIA_PARENT_ACTIVITY_PACKAGE_ROOT=/var/lib/greia-os/activity-packages",
            parent_unit,
        )

    def test_provisional_xorg_service_is_not_wrapped_in_desktop_style_namespace(self) -> None:
        unit = self.read("build/overlay/etc/systemd/system/greia-launcher.service")
        # These proved incompatible with the current Xorg-owned VT/DRM/input
        # session. Reintroducing them requires a new R7 backend-specific proof.
        for directive in (
            "ProtectSystem=",
            "ProtectHome=",
            "PrivateTmp=",
            "ReadWritePaths=",
        ):
            self.assertNotIn(directive, unit)

    def test_xorg_wrapper_matches_systemd_appliance_session(self) -> None:
        wrapper = self.read("build/overlay/etc/X11/Xwrapper.config")
        self.assertIn("allowed_users=anybody", wrapper)
        self.assertIn("needs_root_rights=yes", wrapper)
        self.assertNotIn("allowed_users=console", wrapper)

    def test_legacy_mouse_compatibility_nodes_are_ignored(self) -> None:
        config = self.read("build/overlay/etc/X11/xorg.conf.d/90-greia-input-defaults.conf")
        self.assertIn('MatchDevicePath "/dev/input/mouse*"', config)
        self.assertIn('Option "Ignore" "true"', config)

    def test_activity_sandbox_creates_private_run_and_mount_targets(self) -> None:
        supervisor = self.read("src/greia_launcher/supervisor.py")
        self.assertIn('"--tmpfs",\n            "/run"', supervisor)
        self.assertIn('"--dir",\n                str(SANDBOX_ACTIVITY_ROOT)', supervisor)
        self.assertNotIn('"--unshare-user"', supervisor)
        self.assertNotIn('"--disable-userns"', supervisor)

    def test_launcher_keeps_explicit_x11_focus_handoff_without_a_window_manager(self) -> None:
        launcher = self.read("src/greia_launcher/main.py")
        self.assertIn("_set_x11_input_focus(screen, pygame)", launcher)
        self.assertIn("XSetInputFocus", launcher)

    def test_canonical_builders_never_mint_root_or_unguarded_password_ssh(self) -> None:
        # Root SSH and unguarded password SSH are always forbidden. The
        # owner-approved greia/greia development login is only minted for
        # explicit developer-remote profiles, guarded by the profile package
        # set; normal/release profiles always emit the closed floor.
        forbidden = (
            "PermitRootLogin yes",
            "AllowUsers greia root",
            "chpasswd -e",
            "greia-passwd-entry",
            "$6$greia$",
        )
        for builder_path in (
            "build/build-image.sh",
            "build/build-installer-image.sh",
        ):
            with self.subTest(builder=builder_path):
                builder = self.read(builder_path)
                for token in forbidden:
                    self.assertNotIn(token, builder)
                self.assertIn("PasswordAuthentication no", builder)
                self.assertIn("AuthenticationMethods publickey", builder)
                self.assertIn("PermitRootLogin no", builder)
                self.assertIn("disable ssh.service", builder)
                # The dev login is guarded by the developer-remote package set.
                self.assertIn("developer-remote", builder)
                self.assertIn("provision_developer_ssh", builder)
                # The dev floor keeps root denied.
                self.assertIn("DenyUsers root", builder)
                self.assertIn("AllowUsers greia", builder)
                self.assertIn("PasswordAuthentication yes", builder)
                # The dev profile must rewrite BOTH sshd_config.d drop-ins so
                # the later-sorted 20-greia-parent.conf does not reintroduce
                # publickey-only / PasswordAuthentication no and defeat the
                # developer floor (sshd first-value-wins across the include).
                self.assertTrue(
                    "AuthenticationMethods publickey,password" in builder
                    or "AuthenticationMethods password" in builder
                )
                self.assertIn("20-greia-parent.conf", builder)

        # Developer reachability is also available through the explicit
        # post-build provisioning path; a profile/package-set name is not
        # credential authority by itself, but the owner-approved greia/greia
        # login plus the operator key is the accepted dev identity.
        developer_builder = self.read("build/build-developer-image.sh")
        self.assertIn("verify-development-target-image.sh", developer_builder)
        provisioner = self.read("tools/provision_developer_image.py")
        self.assertIn('"ed25519"', provisioner)
        self.assertIn("AUTHORIZED_KEYS", provisioner)
        self.assertIn("greiaadmin", provisioner)
        self.assertIn('_DEVELOPMENT_USER = "greia"', provisioner)
        self.assertIn('_DEVELOPMENT_PASSWORD = "greia"', provisioner)
        self.assertIn("chpasswd", provisioner)

        live_provisioner = self.read("tools/provision_developer_installer.py")
        self.assertIn("public_key", live_provisioner)
        self.assertIn("authorized_keys", live_provisioner)
        self.assertIn('"password_authentication": True', live_provisioner)
        self.assertIn('"root_login": False', live_provisioner)

    def test_ssh_security_floor_and_first_boot_lock_historical_identities(self) -> None:
        for prefix in ("build/overlay", "build/installer-overlay"):
            with self.subTest(prefix=prefix):
                floor = self.read(
                    f"{prefix}/etc/ssh/sshd_config.d/00-greia-security-floor.conf"
                )
                self.assertIn("PasswordAuthentication no", floor)
                self.assertIn("KbdInteractiveAuthentication no", floor)
                self.assertIn("AuthenticationMethods publickey", floor)
                self.assertIn("PermitRootLogin no", floor)
                # The managed greia account is not denied in the shared floor;
                # base images lock it and keep SSH off, while explicit developer
                # provisioning enables the greia/greia login on dev images.
                self.assertIn("DenyUsers root", floor)
        first_boot = self.read("build/overlay/usr/local/lib/greia-os/first-boot")
        self.assertIn("passwd --lock root", first_boot)


if __name__ == "__main__":
    unittest.main()
