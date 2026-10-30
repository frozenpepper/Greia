from __future__ import annotations

import os
import re
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
        self.assertIn('"$USB_MOUNT/payload/greia-rootfs.squashfs"', builder)
        self.assertIn('"$USB_MOUNT/payload/greia-rootfs.squashfs.sha256"', builder)
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
                module_lines = {
                    line.strip()
                    for line in modules.splitlines()
                    if line.strip() and not line.lstrip().startswith("#")
                }
                for module in ("ahci", "libata", "sd_mod"):
                    self.assertNotIn(module, module_lines)
                    self.assertIn(module, hook)

    def test_graphical_xserver_owns_tty1_while_the_application_tree_detaches_stdin(
        self,
    ) -> None:
        """The controlling-TTY split, asserted as behaviour rather than bytes.

        A background process group that reads the controlling VT as stdin is
        SIGTTIN-stopped, which froze the installer and the child shell. The
        first fix denied the whole service the terminal with
        ``StandardInput=null``. That also denied the *X server* its VT, and an
        unprivileged Xorg cannot activate VT1 it does not own: on the reference
        Acer it aborted with "Cannot open log file", then "Cannot open virtual
        console", then "Switching VT failed", and the branded cover repainted
        forever.

        The invariant is therefore two-sided and both halves are required:

        * the X server owns tty1 as the service's controlling terminal; and
        * the graphical client detaches stdin to /dev/null before it spawns
          anything, so no descendant can read that terminal.
        """
        for unit, client, application in (
            (
                "build/installer-overlay/etc/systemd/system/greia-installer.service",
                "build/installer-overlay/usr/local/lib/greia-os/greia-installer-client",
                "-m greia_installer.entrypoint",
            ),
            (
                "build/overlay/etc/systemd/system/greia-launcher.service",
                "build/overlay/usr/local/lib/greia-os/greia-x-session",
                "-m greia_launcher.child_shell",
            ),
        ):
            with self.subTest(unit=unit):
                text = self.read(unit)
                # X server side: owns the controlling terminal, and fails closed
                # rather than stealing a terminal another process already holds.
                self.assertIn("TTYPath=/dev/tty1", text)
                self.assertIn("StandardInput=tty-fail", text)
                self.assertNotIn("StandardInput=tty-force", text)
                # An unprivileged Xorg opens the VT O_RDWR and needs a log path
                # it can actually write; both were reproduced hardware failures.
                self.assertIn("tty", self._supplementary_groups(text))
                self.assertIn("-logfile ", text)
                # Application side: stdin detached before the graphical
                # application is started, so no descendant can read the VT.
                client_text = self.read(client)
                self.assertIn("exec </dev/null", client_text)
                self.assertLess(
                    client_text.index("exec </dev/null"),
                    client_text.index(application),
                    "stdin must be detached before the graphical application starts",
                )
        engine = self.read("src/greia_installer/engine.py")
        self.assertIn("stdin=subprocess.DEVNULL", engine)

    def test_installer_can_reach_iwd_through_its_designated_group(self) -> None:
        """The unprivileged installer UI must be allowed to talk to iwd.

        iwd's shipped system-bus policy allows send_destination
        net.connman.iwd to root and to group netdev, and denies everything
        else by default. The installer UI runs as an unprivileged identity, so
        without group netdev the bus refuses it and the installer reports
        "no wifi card found" even though iwd is running and has already
        scanned. Reproduced on the reference Acer.
        """

        unit = self.read(
            "build/installer-overlay/etc/systemd/system/greia-installer.service"
        )
        self.assertIn("netdev", self._supplementary_groups(unit))
        # Still not root, and still without any privilege over raw disks.
        self.assertIn("User=nobody", unit)
        self.assertNotIn("User=root", unit)

    @staticmethod
    def _supplementary_groups(unit_text: str) -> list[str]:
        for line in unit_text.splitlines():
            if line.strip().startswith("SupplementaryGroups="):
                return line.split("=", 1)[1].split()
        return []

    def test_wireless_l3_owner_is_explicit_per_image_role(self) -> None:
        """Installer and target deliberately use different L3 owners.

        The live installer enables iwd's built-in network configuration, so its
        wireless link must be unmanaged by networkd. The installed target
        disables iwd network configuration, so networkd must retain DHCP there.
        Keeping these role contracts paired prevents either root from ending up
        with two DHCP clients or with no DHCP client at all.
        """

        roles = (
            (
                "build/installer-overlay",
                True,
                "iwd",
            ),
            (
                "build/overlay",
                False,
                "networkd",
            ),
        )
        for prefix, iwd_networks, l3_owner in roles:
            with self.subTest(prefix=prefix):
                iwd_conf = self.read(f"{prefix}/etc/iwd/main.conf")
                expected = (
                    "EnableNetworkConfiguration=true"
                    if iwd_networks
                    else "EnableNetworkConfiguration=false"
                )
                self.assertIn(expected, iwd_conf)

                policy = self._network_sections(
                    self.read(f"{prefix}/etc/systemd/network/25-greia-wireless.network")
                )
                if l3_owner == "iwd":
                    self.assertEqual(policy.get("Link", {}).get("Unmanaged"), "yes")
                    self.assertNotIn("DHCP", policy.get("Network", {}))
                else:
                    self.assertNotEqual(policy.get("Link", {}).get("Unmanaged"), "yes")
                    self.assertEqual(policy.get("Network", {}).get("DHCP"), "yes")

        package_sets = list((PROJECT_ROOT / "build/package-sets").glob("*.txt"))
        self.assertTrue(package_sets)
        for package_set in package_sets:
            with self.subTest(package_set=package_set.name):
                self.assertNotIn(
                    "wpa_supplicant",
                    package_set.read_text(encoding="utf-8").split(),
                    "iwd remains the sole Wi-Fi association/authentication authority",
                )
        self.assertIn(
            "iwd.service",
            self.read("build/lib/compose.sh"),
            "iwd must stay enabled in the installed target",
        )

    @staticmethod
    def _is_wireless_name(pattern: str) -> bool:
        """Whether a systemd-networkd Name= pattern targets a wireless link."""

        return any(pattern.startswith(prefix) for prefix in ("wl", "wifi", "ra", "ath"))

    @staticmethod
    def _network_sections(text: str) -> dict[str, dict[str, str]]:
        """Parse the simple subset of systemd .network syntax used by Greia."""

        sections: dict[str, dict[str, str]] = {}
        current = ""
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith(("#", ";")):
                continue
            if line.startswith("[") and line.endswith("]"):
                current = line[1:-1]
                sections.setdefault(current, {})
                continue
            if "=" in line and current:
                key, value = line.split("=", 1)
                sections[current][key.strip()] = value.strip()
        return sections

    def test_shared_runtime_directories_are_recreated_before_services_every_boot(self) -> None:
        tmpfiles = self.read("build/overlay/etc/tmpfiles.d/greia-runtime.conf")
        launcher = self.read("build/overlay/etc/systemd/system/greia-launcher.service")
        parent = self.read("build/overlay/etc/systemd/system/greia-parent.service")
        first_boot = self.read("build/overlay/usr/local/lib/greia-os/first-boot")
        prepare = self.read("build/overlay/usr/local/lib/greia-os/prepare-launcher-vt")

        self.assertIn("d /run/greia-os       0770 greiakid greiaprofiles", tmpfiles)
        self.assertIn("d /run/greia-hardware 2750 greiakid greiapanel", tmpfiles)
        self.assertIn("systemd-tmpfiles-setup.service", launcher)
        self.assertIn("systemd-tmpfiles-setup.service", parent)
        self.assertNotIn("RuntimeDirectory=greia-os", launcher)
        self.assertNotIn("/run/greia-hardware", first_boot)
        self.assertIn("Missing Greia runtime root", prepare)
        self.assertNotIn("chown greiakid:greiaprofiles /run/greia-os", prepare)

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

    def test_canonical_builders_never_mint_root_or_unguarded_password_ssh(self) -> None:
        forbidden = (
            "PermitRootLogin yes",
            "AllowUsers greia root",
            "chpasswd -e",
            "greia-passwd-entry",
            "$6$greia$",
        )
        # T02: live-installer SSH policy lives in the shared engine; the thin
        # installer consumer delegates instead of duplicating it.
        builder = self.read("build/lib/compose.sh")
        for token in forbidden:
            self.assertNotIn(token, builder)
        self.assertIn("PasswordAuthentication no", builder)
        self.assertIn("AuthenticationMethods publickey", builder)
        self.assertIn("PermitRootLogin no", builder)
        self.assertIn("disable ssh.service", builder)
        self.assertIn("developer-remote", builder)
        self.assertIn("provision_developer_ssh", builder)
        self.assertIn("DenyUsers root", builder)
        self.assertIn("AllowUsers greia", builder)
        self.assertIn("PasswordAuthentication yes", builder)
        self.assertTrue(
            "AuthenticationMethods publickey,password" in builder
            or "AuthenticationMethods password" in builder
        )
        self.assertIn("20-greia-parent.conf", builder)
        installer = self.read("build/build-installer-image.sh")
        for token in forbidden:
            self.assertNotIn(token, installer)
        self.assertIn('compose_configure_ssh_base "$LIVE_ROOT"', installer)
        self.assertIn('compose_maybe_provision_developer_ssh "$LIVE_ROOT" "live-installer"', installer)
        self.assertNotIn("PasswordAuthentication no", installer)
        self.assertNotIn("PermitRootLogin no", installer)

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

    def test_canonical_builder_passwordless_surface_is_only_greia_devctl(self) -> None:
        # T01: the sudoers rule lives in the shared engine; the thin consumer
        # must not mint privilege surface.
        consumer = self.read("build/build-image.sh")
        self.assertNotIn("NOPASSWD:", consumer)
        builder = self.read("build/lib/compose.sh")
        nopasswd_lines = [
            line.strip()
            for line in builder.splitlines()
            if "NOPASSWD:" in line
        ]
        self.assertEqual(len(nopasswd_lines), 1)
        self.assertEqual(
            nopasswd_lines[0],
            "greia ALL=(root) NOPASSWD: /usr/local/sbin/greia-devctl",
        )
        # The single rule is emitted only on the developer-remote path; the
        # shared overlay gains no new sudo surface for release profiles.
        self.assertIn("compose_provision_developer_ssh", builder)
        self.assertIn("developer-remote", builder)
        self.assertFalse(
            (PROJECT_ROOT / "build/overlay/etc/sudoers.d/greia-developer-remote").exists()
        )

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
                self.assertIn("DenyUsers root", floor)
        first_boot = self.read("build/overlay/usr/local/lib/greia-os/first-boot")
        self.assertIn("passwd --lock root", first_boot)

    def test_installed_generic_session_leaves_single_pointer_authority(self) -> None:
        """Installed X session must not carry direct pointer-preference authority.

        Single authority is settings store -> watcher/backend. The generic
        wrapper may export the session environment and launch the Greia
        hardware watcher + Shell/fallback, but must not issue direct
        preference commands (tap, accel, CTM, disable-while-typing) against a
        hard-coded device name.
        """

        def strip_inline_comment(raw: str) -> str:
            code: list[str] = []
            quote: str | None = None
            for ch in raw:
                if quote is not None:
                    code.append(ch)
                    if ch == quote:
                        quote = None
                elif ch in ("'", '"'):
                    quote = ch
                    code.append(ch)
                elif ch == "#":
                    break
                else:
                    code.append(ch)
            return "".join(code)

        def effective_lines(text: str) -> list[str]:
            effective: list[str] = []
            for raw in text.splitlines():
                stripped = raw.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                code = strip_inline_comment(raw).strip()
                if code:
                    effective.append(code)
            return effective

        session = self.read("build/overlay/usr/local/lib/greia-os/greia-x-session")
        effective = effective_lines(session)
        effective_text = "\n".join(effective)

        # Session contract still intact: env + watcher launch + Shell/fallback.
        for token in (
            "GREIA_OS_ROOT",
            "GREIA_SYSTEM_SETTINGS_DIR",
            "hardware_session_legacy_x",
            "hardware_pid",
            "trap cleanup",
            "greia_launcher.child_shell",
        ):
            self.assertIn(token, session, f"session contract lost: {token!r}")

        # No hard-coded device identity anywhere (comment or code).
        self.assertNotIn("SynPS/2 Synaptics TouchPad", session)

        # No hard-coded CTM anywhere (property name or matrix values).
        self.assertNotIn("Coordinate Transformation Matrix", session)
        self.assertIsNone(
            re.search(r"2\.4\s+0\s+0\s+0\s+2\.4", session),
            "hard-coded CTM matrix values remain in session wrapper",
        )

        # Parsing/behavioral: no effective direct preference-setting command.
        direct = [
            line
            for line in effective
            if re.search(r"\bxinput\b.*\bset-prop\b", line) is not None
        ]
        self.assertEqual(
            [],
            direct,
            f"direct xinput preference commands remain: {direct!r}",
        )
        self.assertNotRegex(
            effective_text,
            r"\bxinput\b.*\bset-prop\b",
        )


if __name__ == "__main__":
    unittest.main()
