from __future__ import annotations

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

    def test_target_and_live_initramfs_keep_generic_storage_stack(self) -> None:
        for prefix in ("build/overlay", "build/installer-overlay"):
            with self.subTest(prefix=prefix):
                config = self.read(f"{prefix}/etc/initramfs-tools/conf.d/greia-hardware")
                modules = self.read(f"{prefix}/etc/initramfs-tools/modules")
                self.assertIn("MODULES=most", config)
                for module in ("ahci", "libata", "sd_mod"):
                    self.assertIn(module, modules.splitlines())

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

    def test_launcher_runtime_directory_exists_before_namespace_setup(self) -> None:
        unit = self.read("build/overlay/etc/systemd/system/greia-launcher.service")
        self.assertIn("RuntimeDirectory=greia-os", unit)
        self.assertIn("RuntimeDirectoryMode=0755", unit)

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


if __name__ == "__main__":
    unittest.main()
