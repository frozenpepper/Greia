from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS = PROJECT_ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from greia_platform import developer_control as devctl  # noqa: E402
from greia_platform import developer_input as devinput  # noqa: E402
from greia_platform.developer_capture import (  # noqa: E402
    DeveloperCaptureError,
    capture_legacy_x11_png,
)
from greia_remote import GreiaRemote, RemoteError  # noqa: E402
from provision_developer_image import (  # noqa: E402
    DeveloperImageProvisionError,
    DeveloperImageProvisioner,
    ProvisionConfig,
)
from build_profile import BuildProfile  # noqa: E402


PNG = b"\x89PNG\r\n\x1a\nsynthetic"


class DeveloperRemoteTests(unittest.TestCase):
    def test_development_profile_is_explicit_and_normal_profile_is_not(self):
        dev = BuildProfile.load(PROJECT_ROOT / "build/profiles/modern-amd64-dev.toml")
        normal = BuildProfile.load(PROJECT_ROOT / "build/profiles/modern-amd64.toml")
        self.assertIn("developer-remote", dev.package_set_names("target"))
        self.assertNotIn("developer-remote", normal.package_set_names("target"))
        self.assertEqual(dev.image.hostname, "greia-dev")
        self.assertEqual(dev.identity.certification_state, "experimental")
        packages = dev.resolve_packages(PROJECT_ROOT / "build/package-sets", "target")
        self.assertIn("openssh-server", packages)
        self.assertIn("xdotool", packages)

    def test_capture_rejects_unbounded_display_selector_before_backend_access(self):
        with self.assertRaises(DeveloperCaptureError):
            capture_legacy_x11_png("bad display")

    def test_screenshot_runs_as_display_user_and_requires_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / "developer-remote"
            marker.write_text("enabled\n", encoding="utf-8")
            state = root / "state"
            with (
                mock.patch.object(devctl, "DEVELOPER_MARKER", marker),
                mock.patch.object(devctl, "STATE_ROOT", state),
                mock.patch.object(devctl, "STAGING_ROOT", state / "staging"),
                mock.patch.object(devctl, "BACKUP_ROOT", state / "backups"),
                mock.patch.object(devctl, "STATE_FILE", state / "deployments.json"),
                mock.patch("greia_platform.developer_control.os.geteuid", return_value=0),
                mock.patch(
                    "greia_platform.developer_control.subprocess.run",
                    return_value=subprocess.CompletedProcess([], 0, PNG, b""),
                ) as run,
            ):
                payload = devctl.DeveloperControl().screenshot()
            self.assertEqual(payload, PNG)
            argv = run.call_args.args[0]
            self.assertEqual(argv[:4], ["runuser", "--user", "greiakid", "--"])
            self.assertIn("DISPLAY=:0", argv)
            self.assertNotIn("XAUTHORITY", " ".join(argv))

    def test_devctl_refuses_non_developer_images_even_as_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing-marker"
            with (
                mock.patch.object(devctl, "DEVELOPER_MARKER", missing),
                mock.patch("greia_platform.developer_control.os.geteuid", return_value=0),
            ):
                with self.assertRaisesRegex(devctl.DeveloperControlError, "not enabled"):
                    devctl.DeveloperControl()

    def test_activity_id_validation_rejects_path_escape(self):
        devctl._validate_activity_id("maze.one")
        with self.assertRaises(devctl.DeveloperControlError):
            devctl._validate_activity_id("../escape")

    def test_gui_input_runs_only_xdotool_as_display_user(self):
        with mock.patch(
            "greia_platform.developer_input.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, "", ""),
        ) as run:
            devinput.key(["Return", "ctrl+l"])
        argv = run.call_args.args[0]
        self.assertEqual(argv[:4], ["runuser", "--user", "greiakid", "--"])
        self.assertIn("DISPLAY=:0", argv)
        self.assertIn("/usr/bin/xdotool", argv)
        self.assertEqual(argv[-4:], ["key", "--clearmodifiers", "Return", "ctrl+l"])

    def test_gui_input_rejects_shell_like_key_expression(self):
        with self.assertRaises(devinput.DeveloperInputError):
            devinput.key(["Return;touch/tmp/x"])
        with self.assertRaises(devinput.DeveloperInputError):
            devinput.type_text("line1\nline2")
        with self.assertRaises(devinput.DeveloperInputError):
            devinput.mousemove(-1, 0)

    def test_provisioner_requires_exact_dev_profile_and_marker_package_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_path = root / "etc/greia-os/image-profile.json"
            profile_path.parent.mkdir(parents=True)
            profile_path.write_text(
                json.dumps(
                    {
                        "profile": {"profile_id": "modern-amd64-dev"},
                        "package_sets": {"target": ["developer-remote"]},
                    }
                ),
                encoding="utf-8",
            )
            provisioner = DeveloperImageProvisioner(
                ProvisionConfig(image=root / "unused.img", output_dir=root / "out")
            )
            payload = provisioner._validate_profile(root)
            self.assertEqual(payload["profile"]["profile_id"], "modern-amd64-dev")
            profile_path.write_text(
                json.dumps(
                    {
                        "profile": {"profile_id": "modern-amd64"},
                        "package_sets": {"target": ["developer-remote"]},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(DeveloperImageProvisionError, "non-developer"):
                provisioner._validate_profile(root)

    def test_provisioner_rejects_persisted_ssh_host_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ssh = root / "etc/ssh"
            ssh.mkdir(parents=True)
            (ssh / "ssh_host_ed25519_key").write_text("private", encoding="utf-8")
            with self.assertRaisesRegex(DeveloperImageProvisionError, "retained SSH host identity"):
                DeveloperImageProvisioner._assert_no_host_keys(root)

    def test_remote_ssh_uses_key_only_batch_mode_and_private_known_hosts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = root / "key"
            key.write_text("private\n", encoding="utf-8")
            known = root / "known_hosts"
            remote = GreiaRemote(
                host="greia-dev.local",
                user="greiaadmin",
                key=key,
                known_hosts=known,
            )
            argv = remote.ssh_base()
            self.assertIn("BatchMode=yes", argv)
            self.assertIn("StrictHostKeyChecking=accept-new", argv)
            self.assertIn(f"UserKnownHostsFile={known.resolve()}", argv)
            self.assertEqual(argv[-1], "greiaadmin@greia-dev.local")

    def test_remote_screenshot_writes_only_valid_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = root / "key"
            key.write_text("private\n", encoding="utf-8")
            remote = GreiaRemote(
                host="host",
                user="greiaadmin",
                key=key,
                known_hosts=root / "known_hosts",
            )
            output = root / "screen.png"
            with mock.patch.object(
                remote,
                "devctl",
                return_value=subprocess.CompletedProcess([], 0, PNG, b""),
            ):
                self.assertEqual(remote.screenshot(output), output.resolve())
            self.assertEqual(output.read_bytes(), PNG)

    def test_remote_gui_methods_stay_inside_devctl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = root / "key"
            key.write_text("private\n", encoding="utf-8")
            remote = GreiaRemote(
                host="host",
                user="greiaadmin",
                key=key,
                known_hosts=root / "known_hosts",
            )
            with mock.patch.object(
                remote,
                "devctl",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as call:
                remote.key(["Escape"])
                call.assert_called_with("key", "Escape")
                remote.mousemove(12, 34)
                call.assert_called_with("mousemove", "12", "34")
                remote.click(1)
                call.assert_called_with("click", "1")
                remote.type_text("hello")
                call.assert_called_with("type", "hello")

    def test_remote_rejects_invalid_activity_id_before_ssh(self):
        from greia_remote import _validate_activity_id

        with self.assertRaises(RemoteError):
            _validate_activity_id("../bad")

    def test_remote_overlay_scripts_are_guarded_and_mode_normalized(self):
        unit = (
            PROJECT_ROOT
            / "build/overlay/etc/systemd/system/greia-developer-remote.service"
        ).read_text(encoding="utf-8")
        self.assertIn("ConditionPathExists=/etc/greia-os/developer-remote", unit)
        self.assertIn("Before=ssh.service", unit)
        self.assertIn("ExecStart=/bin/sh /usr/local/lib/greia-os/prepare-developer-remote", unit)
        ssh = (
            PROJECT_ROOT / "build/overlay/etc/ssh/sshd_config.d/20-greia-parent.conf"
        ).read_text(encoding="utf-8")
        self.assertIn("PasswordAuthentication no", ssh)
        self.assertIn("PermitRootLogin no", ssh)
        self.assertIn("AllowUsers greiaadmin", ssh)
        tmpfiles = (
            PROJECT_ROOT
            / "build/overlay/usr/lib/tmpfiles.d/greia-developer-remote.conf"
        ).read_text(encoding="utf-8")
        self.assertIn("/usr/local/sbin/greia-devctl 0755 root root", tmpfiles)

    def test_developer_builder_wraps_canonical_image_builder(self):
        wrapper = (PROJECT_ROOT / "build/build-developer-image.sh").read_text(encoding="utf-8")
        self.assertIn('"$SCRIPT_DIR/build-image.sh" "$PROFILE" "$OUTPUT_DIR"', wrapper)
        self.assertIn("tools/provision_developer_image.py", wrapper)
        self.assertNotIn("debootstrap", wrapper)


if __name__ == "__main__":
    unittest.main()
