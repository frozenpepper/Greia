from __future__ import annotations

import os
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SystemOverlayContractTests(unittest.TestCase):
    def test_hardware_state_directories_are_setgid_for_cross_service_reads(self) -> None:
        config = (PROJECT_ROOT / "build/overlay/etc/tmpfiles.d/greia-os.conf").read_text()
        self.assertIn(
            "d /var/lib/greia-system-settings 2770 greiapanel greiasettings -",
            config,
        )
        self.assertIn("d /run/greia-hardware 2750 greiakid greiapanel -", config)
        # tmpfiles must name groups compose.sh actually creates (see
        # test_image_tmpfiles_identities); a missing group broke boot once.
        self.assertIn("d /var/lib/greia-profiles 2770 greiakid greiaprofiles -", config)
        self.assertIn("d /run/greia-os 0770 greiakid greiaprofiles -", config)

    def test_wifi_resume_hook_is_installed_executable_and_bounded(self) -> None:
        hook = (
            PROJECT_ROOT
            / "build/overlay/usr/lib/systemd/system-sleep/greia-wifi-resume"
        )
        self.assertTrue(hook.is_file())
        self.assertTrue(os.access(hook, os.X_OK))
        text = hook.read_text()
        self.assertTrue(text.startswith("#!/bin/sh"))
        self.assertIn('[ "${1:-}" = "post" ]', text)
        self.assertIn(
            'WIFI_RESUME_DRIVERS="iwl3945 iwl4965 iwlwifi b43 b43legacy brcmsmac ath5k '
            'ath9k rt2800pci rtl8192ce rtl8180 rtl8187 ipw2100 ipw2200"',
            text,
        )
        self.assertIn("/sys/class/net", text)
        self.assertIn("station list", text)
        self.assertIn('-r "$driver"', text)
        self.assertIn("systemctl try-restart iwd.service", text)
        self.assertIn("/usr/bin/timeout 20", text)
        self.assertIn("exit 0", text)

    def _run_wifi_hook(self, *, interface: bool, station: bool) -> list[str]:
        import subprocess
        import tempfile

        hook = (
            PROJECT_ROOT
            / "build/overlay/usr/lib/systemd/system-sleep/greia-wifi-resume"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "modules").write_text("iwl3945 100 0 - Live 0x0\n")
            net = root / "net"
            net.mkdir()
            if interface:
                wlan = net / "wlan0"
                (wlan / "wireless").mkdir(parents=True)
                (wlan / "device").mkdir()
                (root / "drivers" / "iwl3945").mkdir(parents=True)
                (wlan / "device" / "driver").symlink_to(root / "drivers" / "iwl3945")
                (wlan / "operstate").write_text("down\n")
            log = root / "modprobe.log"
            modprobe = root / "modprobe"
            modprobe.write_text(f'#!/bin/sh\necho "$@" >> {log}\n')
            iwctl = root / "iwctl"
            iwctl.write_text("#!/bin/sh\n" + ("echo wlan0\n" if station else ""))
            for tool in (modprobe, iwctl):
                tool.chmod(0o755)
            env = {
                "PATH": os.environ.get("PATH", ""),
                "GREIA_SYS_NET": str(net),
                "GREIA_PROC_MODULES": str(root / "modules"),
                "GREIA_MODPROBE": str(modprobe),
                "GREIA_IWCTL": str(iwctl),
                "GREIA_WIFI_RESUME_WAIT": "1",
            }
            subprocess.run(["/bin/sh", str(hook), "post"], env=env, check=True)
            return log.read_text().splitlines() if log.exists() else []

    def test_wifi_resume_hook_leaves_a_healthy_resume_alone(self) -> None:
        self.assertEqual(self._run_wifi_hook(interface=True, station=True), [])

    def test_wifi_resume_hook_reloads_when_station_or_interface_is_gone(self) -> None:
        reload_log = ["-r iwl3945", "iwl3945"]
        self.assertEqual(self._run_wifi_hook(interface=True, station=False), reload_log)
        self.assertEqual(self._run_wifi_hook(interface=False, station=False), reload_log)

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

    def test_release_build_uses_an_explicit_accepted_boot_cover(self) -> None:
        for profile in (PROJECT_ROOT / "build/profiles").glob("*.toml"):
            text = profile.read_text()
            self.assertIn('cover_backend = "greia-early-framebuffer-v1"', text)
        profile_tool = (PROJECT_ROOT / "tools/build_profile.py").read_text()
        self.assertIn("_RELEASE_SAFE_BOOT_COVERS", profile_tool)
        self.assertIn(
            'frozenset({"greia-early-framebuffer-v1"})', profile_tool
        )
        self.assertIn("not registered as release-safe", profile_tool)
        # T02: live-installer release gating lives in the shared engine; both
        # thin consumers delegate (compose_resolve_profile) rather than
        # reimplement.
        engine = (PROJECT_ROOT / "build/lib/compose.sh").read_text()
        self.assertIn('PIP_RELEASE_BUILD:-0', engine)
        self.assertIn('check-release', engine)
        self.assertIn("Release build refused", engine)
        for consumer_name in ("build/build-image.sh", "build/build-installer-image.sh"):
            consumer = (PROJECT_ROOT / consumer_name).read_text()
            self.assertNotIn("Release build refused", consumer)
            self.assertNotIn('check-release', consumer)
        consumer = (PROJECT_ROOT / "build/build-image.sh").read_text()
        self.assertIn('compose_resolve_profile "$PROFILE_PATH" "target"', consumer)
        installer = (PROJECT_ROOT / "build/build-installer-image.sh").read_text()
        self.assertIn('compose_resolve_profile "$PROFILE_PATH" "live-installer"', installer)
        # The lowercase footprint field stays with the role consumers that
        # own footprint reporting (target consumer here; installer until T02).
        for builder_name in ("build/build-image.sh", "build/build-installer-image.sh"):
            builder = (PROJECT_ROOT / builder_name).read_text()
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
        # access to greiakid:greiaprofiles group-owned profile dirs, so bwrap could
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
        engine = (PROJECT_ROOT / "build/lib/compose.sh").read_text()
        self.assertIn("accounted_bytes >= required_limit_bytes", image_builder)
        self.assertIn("filesystem_used_bytes", image_builder)
        self.assertNotIn("WARNING: installed root is ${installed_mib} MiB; Phase 0 required", image_builder)
        # T01: build-info composition (PROJECT_VERSION) lives in the engine;
        # the thin consumer carries the engine's result into its footprint
        # report instead of recomputing it.
        self.assertIn("PROJECT_VERSION=", engine)
        self.assertIn("compose_root --profile", image_builder)
        self.assertIn("greia-rootfs.squashfs.sha256", installer_builder)
        self.assertIn("expected-payload.sha256", installer_builder)
        self.assertIn("target_payload_sha256", installer_builder)
        # Step 8A.5 split: the payload digest is verified by the root
        # transaction service from its own environment, never by the
        # unprivileged UI.
        self.assertIn("GREIA_INSTALL_PAYLOAD_DIGEST=/etc/greia-os/expected-payload.sha256", (
            PROJECT_ROOT / "build/installer-overlay/etc/systemd/system/greia-install-transaction.service"
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
        # T01: the engine appends only to the caller's MOUNTS bookkeeping and
        # never deletes the build tree itself; teardown stays with the caller.
        engine = (PROJECT_ROOT / "build/lib/compose.sh").read_text()
        self.assertIn("MOUNTS+=(", engine)
        self.assertNotIn('rm -rf "$BUILD_DIR"', engine)
        self.assertNotIn("safe_remove_build_dir", engine)
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
            # The X server must OWN tty1: an unprivileged Xorg cannot activate a
            # VT it does not control, and the reference Acer proved that with
            # "xf86OpenConsole: Switching VT failed" behind a repainting cover.
            # tty-fail, not tty-force, so a terminal another process already
            # holds fails the unit closed instead of being stolen.
            self.assertIn("StandardInput=tty-fail", unit_text)
            self.assertNotIn("StandardInput=tty-force", unit_text)
        for overlay, client, application in (
            (
                "build/overlay",
                "greia-x-session",
                "-m greia_launcher.child_shell",
            ),
            (
                "build/installer-overlay",
                "greia-installer-client",
                "-m greia_installer.entrypoint",
            ),
        ):
            # The application tree must never inherit the VT as stdin: a
            # background process group reading the tty is SIGTTIN-stopped,
            # freezing the install and the child shell. The client detaches
            # stdin instead of the unit denying itself the terminal.
            client_path = (
                PROJECT_ROOT / overlay / "usr/local/lib/greia-os" / client
            )
            client_text = client_path.read_text()
            self.assertIn("exec </dev/null", client_text)
            self.assertLess(
                client_text.index("exec </dev/null"),
                client_text.index(application),
            )
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
        self.assertIn("xinit", unit)
        # The graphical application is exec'd by the xinit client wrapper, which
        # also owns the stdin detach; the unit names that client, not the module.
        self.assertIn("greia-installer-client", unit)
        self.assertIn(
            "greia_installer.entrypoint",
            (
                PROJECT_ROOT
                / "build/installer-overlay/usr/local/lib/greia-os/greia-installer-client"
            ).read_text(),
        )
        # T02: live-installer systemd composition lives in the shared engine;
        # the thin installer consumer delegates instead of reimplementing
        # the mask list.
        engine = (PROJECT_ROOT / "build/lib/compose.sh").read_text()
        self.assertIn("getty@tty6.service", engine)
        self.assertIn("getty@.service", engine)
        self.assertIn("autovt@.service", engine)
        self.assertIn("debug-shell.service", engine)
        self.assertIn("kbrequest.target", engine)
        self.assertIn('compose_configure_systemd "$LIVE_ROOT" "live-installer"', (
            PROJECT_ROOT / "build/build-installer-image.sh"
        ).read_text())
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
            self.assertIn("console=tty1", text)
            self.assertNotIn("console=null", text)
            self.assertEqual(text.count("console="), 1)
            self.assertIn("systemd.crash_shell=no", text)
            self.assertIn("systemd.crash_chvt=0", text)
            self.assertTrue("panic=0" in text or "panic=5" in text)
        self.assertIn("GRUB_DISABLE_RECOVERY=true", installed_grub)
        self.assertIn("GRUB_DISABLE_RECOVERY=true", installer_grub)
        self.assertIn("greia_platform.boot_contract", image_builder)
        self.assertIn("greia_platform.boot_contract", installer_builder)
        # T02 Repair B: clone-neutral target state is owned once by the shared
        # composer; the thin disk-image consumer carries no duplicate.
        compose_engine = (PROJECT_ROOT / "build/lib/compose.sh").read_text()
        self.assertIn("compose_prepare_clone_neutral_target", compose_engine)
        self.assertIn(': > "$rootfs/etc/machine-id"', compose_engine)
        self.assertNotIn(': > "$ROOTFS/etc/machine-id"', image_builder)
        self.assertNotIn('rm -f "$ROOTFS/etc/ssh/ssh_host_"*', image_builder)
        self.assertNotIn("var/lib/dbus/machine-id", image_builder)
        self.assertNotIn("var/lib/systemd/random-seed", image_builder)
        self.assertNotIn("ssh-keygen -A", first_boot)
        self.assertIn("ssh-keygen -A", enable_ssh)
        # T03 Repair C: fstab policy has one owner (greia_platform.fstab);
        # the composer seam only forwards GREIA_ROOT_UUID disk identity to
        # that renderer, and the thin consumer still feeds the UUID.
        engine = (PROJECT_ROOT / "build/lib/compose.sh").read_text()
        self.assertIn("compose_write_fstab() {", engine)
        self.assertIn("greia_platform.fstab", engine)
        self.assertIn("render_fstab", engine)
        self.assertNotIn("UUID=$root_uuid / ext4", engine)
        self.assertNotIn("errors=remount-ro", engine)
        fstab_owner = (
            PROJECT_ROOT / "src/greia_platform/fstab.py"
        ).read_text()
        self.assertIn("errors=remount-ro", fstab_owner)
        self.assertIn('export GREIA_ROOT_UUID="$root_uuid"', image_builder)
        self.assertNotIn("LABEL=PIP_ROOT / ext4", engine)
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
        builder = (PROJECT_ROOT / "build/lib/compose.sh").read_text()
        consumer = (PROJECT_ROOT / "build/build-image.sh").read_text()
        self.assertIn("package-manifest.tsv", builder)
        self.assertIn("check-support-status --no-heading", builder)
        self.assertIn("security_support_state", builder)
        self.assertIn("security_support_probe_exit", builder)
        # T01: the thin consumer carries the engine's probe outcome into its
        # footprint report instead of re-probing.
        self.assertIn("security_support_state=$COMPOSE_SECURITY_SUPPORT_STATE", consumer)
        self.assertIn("security_support_probe_exit=$COMPOSE_SECURITY_SUPPORT_EXIT", consumer)
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
        composer = (PROJECT_ROOT / "build/lib/compose.sh").read_text()
        for argument in (
            "greia.live_media_id=",
            "live-media-timeout=15",
            "nopersistence",
            "noeject",
            "nonetworking",
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

        # Session 03 real-build regression: the hook above executes from a
        # kernel package postinst. Therefore the live-media identity must be a
        # shared composition prerequisite, not a late installer-only insert.
        self.assertIn("compose_prepare_live_media_identity() {", composer)
        self.assertIn('identity_path="$rootfs/etc/greia-os/live-media-id"', composer)
        self.assertIn("uuid.uuid4()", composer)
        self.assertIn(
            'compose_prepare_live_media_identity "$rootfs" || return 1',
            composer,
        )
        self.assertIn('compose_prepare_live_media_identity "$LIVE_ROOT"', builder)
        self.assertIn('live_media_id="$COMPOSE_LIVE_MEDIA_ID"', builder)
        self.assertNotIn("uuid.uuid4()", builder)

    def test_https_bootstrap_includes_ca_and_requires_executable_target_architecture(self) -> None:
        # T02: live-installer bootstrap lives in the shared engine; both thin
        # consumers delegate debootstrap + host-arch validation to the engine.
        engine = (PROJECT_ROOT / "build/lib/compose.sh").read_text()
        self.assertIn("--include=ca-certificates", engine)
        self.assertIn("dpkg --print-architecture", engine)
        self.assertIn("host_arch=", engine)
        for consumer_name in ("build/build-image.sh", "build/build-installer-image.sh"):
            consumer = (PROJECT_ROOT / consumer_name).read_text()
            self.assertIn("compose_check_host_arch", consumer)
            self.assertNotIn("dpkg --print-architecture", consumer)
            self.assertNotIn("--include=ca-certificates", consumer)
        installer = (PROJECT_ROOT / "build/build-installer-image.sh").read_text()
        self.assertIn('compose_debootstrap "$LIVE_ROOT"', installer)

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


    def test_builds_share_a_persistent_apt_cache_instead_of_redownloading(self) -> None:
        helper = (PROJECT_ROOT / "build/lib/apt-cache.sh").read_text()
        self.assertIn('GREIA_APT_CACHE:-/var/cache/greia-apt', helper)
        self.assertIn('GREIA_POOL_CACHE:-/var/cache/greia-pool', helper)
        self.assertIn('mount_apt_archives_cache', helper)
        self.assertIn('mount_pool_cache', helper)
        self.assertIn('mount --bind', helper)
        # T02: live-installer apt-cache composition lives in the shared engine;
        # the thin installer consumer delegates instead of reimplementing the
        # cache mount and hygiene.
        image_builder = (PROJECT_ROOT / "build/lib/compose.sh").read_text()
        installer_builder = (PROJECT_ROOT / "build/build-installer-image.sh").read_text()
        consumer = (PROJECT_ROOT / "build/build-image.sh").read_text()
        self.assertIn('compose_root --profile', consumer)
        self.assertNotIn('mount_apt_archives_cache', consumer)
        live_firmware = (PROJECT_ROOT / "build/install-live-hardware-firmware.sh").read_text()
        pool_builder = (PROJECT_ROOT / "build/populate-hardware-support-pool.sh").read_text()
        self.assertIn('lib/apt-cache.sh', installer_builder)
        self.assertIn('apt-cache.sh', image_builder)
        # The engine remains the single owner of the apt-cache mount, bounded
        # hygiene and footprint pruning.
        self.assertIn('mount_apt_archives_cache', image_builder)
        self.assertIn('apt-get autoclean', image_builder)
        self.assertNotIn('apt-get clean', image_builder)
        self.assertIn('var/lib/apt/lists/', image_builder)
        self.assertNotIn('var/cache/apt/archives/', image_builder)
        # The thin installer delegates those blocks instead of duplicating
        # them, while retaining the live-only pool cache.
        for call in (
            'compose_mount_apt_cache "$LIVE_ROOT"',
            'compose_debootstrap "$LIVE_ROOT"',
            'compose_mount_virtual "$LIVE_ROOT"',
            'compose_install_packages "$LIVE_ROOT" "live-installer"',
            'compose_footprint_hygiene "$LIVE_ROOT"',
        ):
            self.assertIn(call, installer_builder)
        self.assertNotIn('debootstrap --arch=', installer_builder)
        self.assertNotIn('apt-get autoclean', installer_builder)
        self.assertNotIn('var/lib/apt/lists/', installer_builder)
        self.assertIn('mount_pool_cache', installer_builder)
        # Mount sequencing (debootstrap-era .deb trap): the apt host cache must
        # be bound BEFORE debootstrap so base downloads land on the host. A
        # post-debootstrap mount shadows the real archives dir (invisible to
        # du -sx, counted by df) and bakes stale .debs into the image/squashfs.
        # The engine is a function library, so its execution order is the
        # compose_root call sequence (not file order); the thin installer
        # consumer is a linear script calling the same engine functions, so
        # file order is execution order there.
        engine_calls = [
            'compose_mount_apt_cache "$rootfs" || return 1',
            'compose_debootstrap "$rootfs" || return 1',
            'compose_prepare_live_media_identity "$rootfs" || return 1',
            'compose_mount_virtual "$rootfs" || return 1',
            'compose_install_packages "$rootfs" "$role" || return 1',
        ]
        engine_positions = [image_builder.index(call) for call in engine_calls]
        self.assertEqual(engine_positions, sorted(engine_positions))
        self.assertIn('mount_apt_archives_cache "$rootfs"', image_builder)
        self.assertIn('debootstrap --arch=', image_builder)
        self.assertIn('apt-get "${APT_ACQUIRE_OPTIONS', image_builder)
        self.assertIn('MOUNTS+=(', image_builder)
        # Virtual mounts + resolver stub still precede any APT fetch.
        self.assertIn('tmpfs "$rootfs/run"', image_builder)
        self.assertIn('stub-resolv.conf', image_builder)
        # Thin installer consumer preserves the same sequencing through the
        # engine functions: apt cache before debootstrap before virtual
        # mounts before package install; the live-media id is seeded before
        # the install so the kernel postinst hook embeds it.
        builder = installer_builder
        installer_calls = [
            'compose_mount_apt_cache "$LIVE_ROOT"',
            'compose_debootstrap "$LIVE_ROOT"',
            'compose_mount_virtual "$LIVE_ROOT"',
            'compose_prepare_live_media_identity "$LIVE_ROOT"',
            'compose_install_packages "$LIVE_ROOT" "live-installer"',
        ]
        installer_positions = [builder.index(call) for call in installer_calls]
        self.assertEqual(installer_positions, sorted(installer_positions))
        self.assertIn('MOUNTS+=(', builder)
        self.assertIn('mount_pool_cache', builder)
        pool_mount = builder.index('mount_pool_cache')
        bootstrap = builder.index('compose_debootstrap "$LIVE_ROOT"')
        self.assertLess(pool_mount, bootstrap)
        # Installer live root shares both caches; the existing pre-mksquashfs
        # teardown releases them before compression.
        unmount = installer_builder.index('safe_unmount_paths "${MOUNTS[@]}"')
        squash = installer_builder.index('mksquashfs "$LIVE_ROOT"')
        self.assertLess(unmount, squash)
        # Footprint hygiene stays intact (not reverted for the cache port).
        self.assertIn('purge --auto-remove binutils', image_builder)
        self.assertIn('rm -f "$rootfs"/usr/lib/gcc', image_builder)
        # Live firmware keeps only autoclean; pool downloads route through the
        # persistent pool cache and are staged into a fresh pool afterwards.
        self.assertIn('apt-get autoclean', live_firmware)
        self.assertNotIn('apt-get clean', live_firmware)
        self.assertIn('POOL_CACHE_IN_CHROOT', pool_builder)
        self.assertIn('/var/cache/greia-pool', pool_builder)
        self.assertIn('POOL_CACHE_HOST', pool_builder)
        self.assertIn('Dir::Cache::archives="$POOL_CACHE_IN_CHROOT"', pool_builder)
        self.assertNotIn('Dir::Cache::archives=/opt/greia-hardware-support/pool', pool_builder)
        self.assertIn('Dir::Cache::archives="$POOL_CACHE_IN_CHROOT" autoclean', pool_builder)
        self.assertIn('"$POOL_CACHE_HOST"', pool_builder)
        pool_copy = pool_builder.index('"$POOL_CACHE_HOST"')
        finalize = pool_builder.index('finalize_hardware_support_pool.py')
        self.assertLess(pool_copy, finalize)

        # Session 03 real-build regression: compose_root is allowed to finish
        # with image hygiene already applied, including removal of remote APT
        # lists. The hardware-pool producer is a standalone APT consumer and
        # must therefore refresh the metadata it needs before apt-cache
        # candidate discovery / dependency resolution, then restore hygiene
        # after it has finalized the self-contained pool.
        self.assertIn('rm -rf "$rootfs/var/lib/apt/lists/"*', image_builder)
        pool_refresh = pool_builder.index(
            'apt-get "${APT_NETWORK_OPTIONS[@]}" update'
        )
        candidate_probe = pool_builder.index(
            'apt-cache show --no-all-versions "$package"'
        )
        download_resolve = pool_builder.index('--download-only install')
        pool_finalize = pool_builder.index('finalize_hardware_support_pool.py')
        pool_hygiene = pool_builder.index(
            'rm -rf "$LIVE_ROOT/var/lib/apt/lists/"*'
        )
        self.assertLess(pool_refresh, candidate_probe)
        self.assertLess(candidate_probe, download_resolve)
        self.assertLess(download_resolve, pool_finalize)
        self.assertLess(pool_finalize, pool_hygiene)
        # The finalized pool must match the fail-closed release archive
        # allowlist (manifest.json, Packages, Packages.gz, pool/): the
        # producer removes its candidate-discovery intermediates after
        # finalization consumes the manifest instead of widening the
        # archive check.
        pool_intermediate_cleanup = pool_builder.index(
            'rm -f "$CANDIDATE_MANIFEST" "$AVAILABLE_LIST"'
        )
        self.assertLess(pool_finalize, pool_intermediate_cleanup)
        self.assertLess(pool_intermediate_cleanup, pool_hygiene)

    def test_installer_powers_off_before_parent_removes_live_usb(self) -> None:
        installer = (PROJECT_ROOT / "src/greia_installer/main.py").read_text()
        # 2026-10-18: the unprivileged UI cannot call logind itself (denied),
        # so it writes the finish marker its own RuntimeDirectory owns and the
        # root greia-installer-finish.path unit performs the power-off.
        self.assertIn('POWEROFF_REQUEST_PATH', installer)
        self.assertIn('finish-request', installer)
        self.assertNotIn('["systemctl", "poweroff"]', installer)
        self.assertNotIn('["systemctl", "reboot"]', installer)
        self.assertIn("I'm ready", installer)

    def test_installer_bounds_unsquashfs_memory_queues(self) -> None:
        engine = (PROJECT_ROOT / "src/greia_installer/engine.py").read_text()
        self.assertIn('"-strict-errors"', engine)
        self.assertIn('"-processors"', engine)
        self.assertIn('"-data-queue"', engine)
        self.assertIn('"-frag-queue"', engine)
        self.assertGreaterEqual(engine.count('"32"'), 2)

