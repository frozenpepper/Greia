from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SystemOverlayContractTests(unittest.TestCase):
    def test_hardware_state_directories_are_setgid_for_cross_service_reads(self) -> None:
        config = (PROJECT_ROOT / "build/overlay/etc/tmpfiles.d/greia-os.conf").read_text()
        self.assertIn(
            "d /var/lib/greia-system-settings 2750 greiapanel greiasettings -",
            config,
        )
        self.assertIn("d /run/greia-hardware 2750 greiakid greiapanel -", config)
        self.assertIn("d /var/lib/greia-profiles 2770 greiakid greiaprofiles -", config)
        self.assertIn("d /run/greia-os 0770 greiakid greiaprofiles -", config)

    def test_installed_x_session_starts_hardware_controller_before_launcher(self) -> None:
        session = (
            PROJECT_ROOT / "build/overlay/usr/local/lib/greia-os/greia-x-session"
        ).read_text()
        self.assertIn("greia_platform.hardware_session", session)
        # The child shell composes the authoritative launcher/presentation
        # classes with safe profile visual context.
        self.assertIn("greia_launcher.child_shell", session)
        self.assertNotIn("exec /usr/bin/python3 -m greia_launcher.main", session)
        self.assertIn("launcher_status=$?", session)
        self.assertIn("trap cleanup EXIT INT TERM", session)
        self.assertIn("GREIA_PROFILES_DIR=/var/lib/greia-profiles", session)



    def test_removable_mount_helpers_reject_path_like_device_names(self) -> None:
        for helper_name in ("mount-removable", "unmount-removable"):
            helper = (
                PROJECT_ROOT
                / "build/overlay/usr/local/lib/greia-os"
                / helper_name
            ).read_text()
            self.assertIn('case "$device_name" in', helper)
            self.assertIn('*) exit 1', helper)
            self.assertNotIn('eval ', helper)
        mount_helper = (
            PROJECT_ROOT / "build/overlay/usr/local/lib/greia-os/mount-removable"
        ).read_text()
        self.assertIn("blkid -p", mount_helper)
        self.assertIn("vfat|exfat|ntfs|ntfs3", mount_helper)
        self.assertNotIn("ext2|ext3|ext4|iso9660", mount_helper)
        self.assertIn("nosuid,nodev,noexec", mount_helper)

    def test_release_build_is_blocked_until_boot_cover_is_physically_accepted(self) -> None:
        for profile in (PROJECT_ROOT / "build/profiles").glob("*.toml"):
            text = profile.read_text()
            self.assertIn('cover_backend = "greia-early-framebuffer-v1"', text)
        profile_tool = (PROJECT_ROOT / "tools/build_profile.py").read_text()
        self.assertIn("_RELEASE_SAFE_BOOT_COVERS", profile_tool)
        self.assertIn("frozenset()", profile_tool)
        for builder_name in ("build/build-image.sh", "build/build-installer-image.sh"):
            builder = (PROJECT_ROOT / builder_name).read_text()
            self.assertIn('PIP_RELEASE_BUILD:-0', builder)
            self.assertIn('check-release "$PROFILE_PATH"', builder)
            self.assertIn("Release build refused", builder)
            self.assertIn("boot_cover_backend=$BOOT_COVER_BACKEND", builder)

    def test_activity_namespace_sandbox_is_a_profile_composed_package_set(self) -> None:
        packages = (PROJECT_ROOT / "build/package-sets/activity-sandbox.txt").read_text().splitlines()
        self.assertIn("bubblewrap", packages)
        for profile in (PROJECT_ROOT / "build/profiles").glob("*.toml"):
            self.assertIn('"activity-sandbox"', profile.read_text())
        supervisor = (PROJECT_ROOT / "src/greia_launcher/supervisor.py").read_text()
        for boundary in (
            "--unshare-pid",
            "--unshare-net",
            "--new-session",
            "--die-with-parent",
            "--tmpfs",
            "/run",
            "/var/lib/greia-profiles",
            "/var/lib/greia-os",
            "--ro-bind",
            "/",
            "/",
        ):
            self.assertIn(boundary, supervisor)
        # --unshare-user is intentionally not used: its user-namespace root loses
        # access to greiakid:pipprofiles group-owned profile dirs, so bwrap could
        # not traverse the activity-data source and every Activity failed to
        # launch. PID/network/UTS isolation plus read-only root remains.
        self.assertNotIn("--unshare-user", supervisor)
        self.assertNotIn("--disable-userns", supervisor)
        # X11's shared-memory extension requires host IPC for acceptable low-end
        # performance, so do not accidentally isolate IPC before replacing X11.
        self.assertNotIn('"--unshare-ipc"', supervisor)

    def test_build_enforces_hard_sub_one_gib_budget_and_payload_digest(self) -> None:
        image_builder = (PROJECT_ROOT / "build/build-image.sh").read_text()
        installer_builder = (PROJECT_ROOT / "build/build-installer-image.sh").read_text()
        self.assertIn("accounted_bytes >= required_limit_bytes", image_builder)
        self.assertIn("filesystem_used_bytes", image_builder)
        self.assertNotIn("WARNING: installed root is ${installed_mib} MiB; Phase 0 required", image_builder)
        self.assertIn("PROJECT_VERSION=", image_builder)
        self.assertIn("pip-rootfs.squashfs.sha256", installer_builder)
        self.assertIn("expected-payload.sha256", installer_builder)
        self.assertIn("target_payload_sha256", installer_builder)
        self.assertIn("--payload-digest /etc/greia-os/expected-payload.sha256", (
            PROJECT_ROOT / "build/installer-overlay/etc/systemd/system/greia-installer.service"
        ).read_text())
        self.assertNotIn("-no-xattrs", installer_builder)
        self.assertIn("mount -o ro,noload", installer_builder)

    def test_build_cleanup_never_recursively_removes_live_mounts(self) -> None:
        helper = (PROJECT_ROOT / "build/lib/safe-cleanup.sh").read_text()
        for builder_name in ("build/build-image.sh", "build/build-installer-image.sh"):
            builder = (PROJECT_ROOT / builder_name).read_text()
            self.assertIn("safe_unmount_paths", builder)
            self.assertIn("safe_remove_build_dir", builder)
            self.assertNotIn('rm -rf "$BUILD_DIR"', builder)
        self.assertIn("findmnt -rn -R", helper)
        self.assertIn("rm -rf --one-file-system", helper)

    def test_boot_cover_handoff_keeps_early_framebuffer_and_xorg_on_same_vt(self) -> None:
        units = (
            PROJECT_ROOT / "build/overlay/etc/systemd/system/greia-launcher.service",
            PROJECT_ROOT / "build/installer-overlay/etc/systemd/system/greia-installer.service",
        )
        for unit in units:
            unit_text = unit.read_text()
            self.assertIn(" vt1 ", unit_text)
            self.assertIn("TTYPath=/dev/tty1", unit_text)
            self.assertNotIn(" vt2 ", unit_text)
            self.assertNotIn("TTYPath=/dev/tty2", unit_text)
            # The GUI must never have the VT as stdin: a background process
            # group reading the tty is SIGTTIN-stopped, freezing the install
            # (apt-get / grub-mkpasswd-pbkdf2). stdin must be /dev/null.
            self.assertIn("StandardInput=null", unit_text)
            self.assertNotIn("StandardInput=tty", unit_text)
        for overlay in ("build/overlay", "build/installer-overlay"):
            release = (
                PROJECT_ROOT / overlay / "usr/local/lib/greia-os/release-boot-cover"
            ).read_text()
            prepare_name = "prepare-launcher-vt" if overlay == "build/overlay" else "prepare-installer-vt"
            prepare = (PROJECT_ROOT / overlay / "usr/local/lib/greia-os" / prepare_name).read_text()
            self.assertIn("chvt 1", prepare)
            self.assertNotIn("chvt 2", release)
            # The early-framebuffer cover owns the frame; no Plymouth handoff.
            self.assertNotIn("plymouth", release)
            self.assertNotIn("plymouth", prepare)
            self.assertIn('> "$marker"', release)
            self.assertIn("boot-cover-released", release)

    def test_usb_writer_requires_removable_media_and_rechecks_identity(self) -> None:
        writer = (PROJECT_ROOT / "build/write-image.sh").read_text()
        self.assertIn("Refusing non-removable internal disk", writer)
        self.assertIn("Image does not fit target", writer)
        self.assertIn("Target identity changed after confirmation", writer)
        self.assertIn('lsblk", "-srno", "PATH"', writer)

    def test_installer_masks_visible_gettys_and_starts_graphical_service(self) -> None:
        unit = (
            PROJECT_ROOT
            / "build/installer-overlay/etc/systemd/system/greia-installer.service"
        ).read_text()
        builder = (PROJECT_ROOT / "build/build-installer-image.sh").read_text()
        self.assertIn("xinit", unit)
        self.assertIn("greia_installer.entrypoint", unit)
        self.assertIn("getty@tty6.service", builder)
        self.assertIn("getty@.service", builder)
        self.assertIn("autovt@.service", builder)
        self.assertIn("debug-shell.service", builder)
        self.assertIn("kbrequest.target", builder)
        for overlay in ("build/overlay", "build/installer-overlay"):
            logind = (PROJECT_ROOT / overlay / "etc/systemd/logind.conf.d/10-greia-vts.conf").read_text()
            xorg = (PROJECT_ROOT / overlay / "etc/X11/xorg.conf.d/10-greia-kiosk.conf").read_text()
            self.assertIn("NAutoVTs=0", logind)
            self.assertIn('Option "DontVTSwitch" "true"', xorg)
            self.assertIn('Option "DisableVidModeExtension" "true"', xorg)
    def test_no_console_text_and_clone_identity_contracts_are_present(self) -> None:
        installed_grub = (
            PROJECT_ROOT / "build/overlay/etc/default/grub.d/10-greia-quiet.cfg"
        ).read_text()
        installer_grub = (
            PROJECT_ROOT / "build/installer-overlay/etc/default/grub.d/10-greia-quiet.cfg"
        ).read_text()
        installer_builder = (PROJECT_ROOT / "build/build-installer-image.sh").read_text()
        image_builder = (PROJECT_ROOT / "build/build-image.sh").read_text()
        first_boot = (
            PROJECT_ROOT / "build/overlay/usr/local/lib/greia-os/first-boot"
        ).read_text()
        enable_ssh = (
            PROJECT_ROOT / "build/overlay/usr/local/sbin/greia-enable-ssh"
        ).read_text()
        for text in (installed_grub, installer_grub, installer_builder):
            self.assertIn("console=null", text)
            self.assertEqual(text.count("console="), 1)
            self.assertIn("systemd.crash_shell=no", text)
            self.assertIn("systemd.crash_chvt=0", text)
            self.assertTrue("panic=0" in text or "panic=5" in text)
        self.assertIn("GRUB_DISABLE_RECOVERY=true", installed_grub)
        self.assertIn("GRUB_DISABLE_RECOVERY=true", installer_grub)
        self.assertIn("greia_platform.boot_contract", image_builder)
        self.assertIn("greia_platform.boot_contract", installer_builder)
        self.assertIn('rm -f "$ROOTFS/etc/ssh/ssh_host_"*', image_builder)
        self.assertIn(': > "$ROOTFS/etc/machine-id"', image_builder)
        self.assertNotIn("ssh-keygen -A", first_boot)
        self.assertIn("ssh-keygen -A", enable_ssh)
        self.assertIn("UUID=$root_uuid / ext4", image_builder)
        self.assertNotIn("LABEL=PIP_ROOT / ext4", image_builder)
        auth_script = (PROJECT_ROOT / "build/overlay/etc/grub.d/01_greia_auth").read_text()
        appliance_script = (PROJECT_ROOT / "build/overlay/etc/grub.d/10_greia_appliance").read_text()
        self.assertIn('set superusers="greia"', auth_script)
        self.assertIn("password_pbkdf2 greia", auth_script)
        self.assertIn("--unrestricted", appliance_script)
        self.assertIn("root-filesystem-uuid", appliance_script)
        self.assertIn("grub-script-check", image_builder)
        self.assertIn("grub-script-check", installer_builder)
        engine = (PROJECT_ROOT / "src/greia_installer/engine.py").read_text()
        self.assertNotIn('"ssh-keygen", "-A"', engine)
        self.assertNotIn('"systemd-machine-id-setup"', engine)

    def test_base_profiles_record_security_support_and_legacy_x_on_acer(self) -> None:
        builder = (PROJECT_ROOT / "build/build-image.sh").read_text()
        self.assertIn("package-manifest.tsv", builder)
        self.assertIn("check-support-status --no-heading", builder)
        self.assertIn("security_support_state", builder)
        self.assertIn("security_support_probe_exit", builder)
        platform_base = (PROJECT_ROOT / "build/package-sets/platform-base.txt").read_text()
        installer_base = (PROJECT_ROOT / "build/package-sets/installer-base.txt").read_text()
        self.assertIn("debian-security-support", platform_base)
        self.assertIn("debian-security-support", installer_base)
        for profile in (PROJECT_ROOT / "build/profiles").glob("acer-aspire-one-*.toml"):
            text = profile.read_text()
            self.assertIn('extra_packages = ["xserver-xorg-legacy"]', text)
            self.assertIn('mirror = "https://', text)
            self.assertIn('support_end_date = "', text)
        modern = (PROJECT_ROOT / "build/profiles/modern-amd64.toml").read_text()
        self.assertIn('extra_packages = []', modern)
        installer_builder = (PROJECT_ROOT / "build/build-installer-image.sh").read_text()
        self.assertIn("live-package-manifest.tsv", installer_builder)
        self.assertIn("live-base-system-manifest.txt", installer_builder)
        self.assertIn("live-security-support-status.txt", installer_builder)
        self.assertIn("live_security_support_state", installer_builder)
        self.assertIn("declared security-support end date", builder)
        self.assertIn("declared_support_end_date", builder)

    def test_xorg_services_do_not_switch_back_to_text_vt_on_reset(self) -> None:
        for unit_path in (
            PROJECT_ROOT / "build/overlay/etc/systemd/system/greia-launcher.service",
            PROJECT_ROOT / "build/installer-overlay/etc/systemd/system/greia-installer.service",
        ):
            unit_text = unit_path.read_text()
            self.assertIn("-novtswitch", unit_text)
            self.assertIn("-background none", unit_text)
            self.assertIn("-quiet", unit_text)
        for overlay in ("build/overlay", "build/installer-overlay"):
            wrapper = (PROJECT_ROOT / overlay / "etc/X11/Xwrapper.config").read_text()
            # The current provisional Xorg compatibility backend runs from a
            # systemd appliance session. It deliberately uses the platform-owned
            # appliance authorization rather than a desktop-console heuristic.
            self.assertIn("allowed_users=anybody", wrapper)
            self.assertIn("needs_root_rights=yes", wrapper)
            self.assertNotIn("allowed_users=console", wrapper)

    def test_runtime_audit_is_bounded_and_excludes_known_secrets(self) -> None:
        collector_path = (
            PROJECT_ROOT / "build/overlay/usr/local/sbin/greia-collect-runtime-audit"
        )
        collector = collector_path.read_text()
        self.assertTrue(collector_path.stat().st_mode & 0o111)
        self.assertIn("package-manifest.tsv", collector)
        self.assertIn("systemd-analyze time", collector)
        self.assertIn("systemd-analyze security", collector)
        self.assertIn("block-devices-sanitized", collector)
        self.assertIn("console-shell-enable-state", collector)
        self.assertIn("emergency.service", collector)
        self.assertIn("rescue.service", collector)
        self.assertIn("kbrequest.target", collector)
        self.assertIn("collector_version=3", collector)
        self.assertIn("ssh-host-public-fingerprints", collector)
        self.assertNotIn("SERIAL,WWN", collector)
        self.assertNotIn("pairing-token", collector)
        self.assertNotIn("journalctl", collector)
        self.assertIn("tail -n 1200", collector)

    def test_live_boot_is_bounded_nonpersistent_and_uuid_matched(self) -> None:
        builder = (PROJECT_ROOT / "build/build-installer-image.sh").read_text()
        for argument in (
            "greia.live_media_id=",
            "live-media-timeout=15",
            "nopersistence",
            "noeject",
            "silent",
            "overlay-size=128M",
            "consoleblank=0",
            "/.disk/live-uuid",
            "unmkinitramfs",
        ):
            self.assertIn(argument, builder)
        self.assertNotIn("live-media=removable", builder)
        self.assertIn("--live-installer", builder)
        hook = (
            PROJECT_ROOT
            / "build/installer-overlay/etc/initramfs-tools/hooks/greia-live-media-id"
        ).read_text()
        self.assertIn("$DESTDIR/conf/uuid.conf", hook)
        self.assertIn("/etc/greia-os/live-media-id", hook)

    def test_https_bootstrap_includes_ca_and_requires_executable_target_architecture(self) -> None:
        for builder_name in ("build/build-image.sh", "build/build-installer-image.sh"):
            builder = (PROJECT_ROOT / builder_name).read_text()
            self.assertIn("--include=ca-certificates", builder)
            self.assertIn("dpkg --print-architecture", builder)
            self.assertIn("host_arch=", builder)

    def test_first_boot_is_required_and_service_resource_counts_are_bounded(self) -> None:
        launcher = (PROJECT_ROOT / "build/overlay/etc/systemd/system/greia-launcher.service").read_text()
        parent = (PROJECT_ROOT / "build/overlay/etc/systemd/system/greia-parent.service").read_text()
        installer = (PROJECT_ROOT / "build/installer-overlay/etc/systemd/system/greia-installer.service").read_text()
        first_boot = (PROJECT_ROOT / "build/overlay/etc/systemd/system/greia-first-boot.service").read_text()
        self.assertIn("Requires=greia-first-boot.service", launcher)
        self.assertIn("Requires=greia-first-boot.service", parent)
        self.assertIn("Restart=on-failure", first_boot)
        self.assertIn("TasksMax=128", launcher)
        self.assertIn("TasksMax=32", parent)
        self.assertIn("TasksMax=128", installer)
        for unit in (launcher, parent, installer):
            self.assertIn("LimitCORE=0", unit)

    def test_qemu_uses_an_atom_era_cpu_model_instead_of_max(self) -> None:
        for helper_path in (
            PROJECT_ROOT / "build/verify-installer-qemu.sh",
            PROJECT_ROOT / "build/verify-image-qemu.sh",
        ):
            helper = helper_path.read_text()
            self.assertNotIn("-cpu max", helper)
            self.assertIn("n270", helper)
            self.assertIn("PIP_QEMU_CPU_MODEL", helper)

    def test_qemu_installer_uses_usb_media_bootindex_and_profile_architecture(self) -> None:
        helper = (PROJECT_ROOT / "build/verify-installer-qemu.sh").read_text()
        self.assertIn("usb-storage", helper)
        self.assertIn("bootindex=1", helper)
        self.assertIn("bootindex=2", helper)
        self.assertNotIn("-boot order=", helper)
        self.assertIn("qemu-system-x86_64", helper)
        self.assertIn("architecture=", helper)

    def test_xorg_preparation_never_deletes_a_live_server_lock(self) -> None:
        for overlay, script_name in (
            ("build/overlay", "prepare-launcher-vt"),
            ("build/installer-overlay", "prepare-installer-vt"),
        ):
            script = (
                PROJECT_ROOT / overlay / "usr/local/lib/greia-os" / script_name
            ).read_text()
            self.assertIn('kill -0 "$x_pid"', script)
            self.assertIn("Refusing malformed Xorg display lock", script)
            self.assertIn("Refusing orphan Xorg display socket", script)
            self.assertNotIn("rm -f /tmp/.X0-lock", script)


    def test_installer_powers_off_before_parent_removes_live_usb(self) -> None:
        installer = (PROJECT_ROOT / "src/greia_installer/main.py").read_text()
        self.assertIn('["systemctl", "poweroff"]', installer)
        self.assertNotIn('["systemctl", "reboot"]', installer)
        self.assertIn("I'm ready", installer)

    def test_installer_bounds_unsquashfs_memory_queues(self) -> None:
        engine = (PROJECT_ROOT / "src/greia_installer/engine.py").read_text()
        self.assertIn('"-strict-errors"', engine)
        self.assertIn('"-processors"', engine)
        self.assertIn('"-data-queue"', engine)
        self.assertIn('"-frag-queue"', engine)
        self.assertGreaterEqual(engine.count('"32"'), 2)

