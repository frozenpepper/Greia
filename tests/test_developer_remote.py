from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS = PROJECT_ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from greia_launcher.main import _activity_sources  # noqa: E402
from greia_platform import developer_control as devctl  # noqa: E402
from greia_platform import developer_input as devinput  # noqa: E402
from greia_platform.activities import ActivityValidationError  # noqa: E402
from greia_platform.developer_capture import (  # noqa: E402
    DeveloperCaptureError,
    capture_legacy_x11_png,
)
from greia_platform.developer_session import (  # noqa: E402
    DeveloperDisplayEndpoint,
    DeveloperSessionError,
)
from greia_platform.trust import PackageTrust  # noqa: E402
from greia_remote import GreiaRemote, RemoteError  # noqa: E402
from provision_developer_image import (  # noqa: E402
    DeveloperImageProvisionError,
    DeveloperImageProvisioner,
    ProvisionConfig,
)
from provision_developer_installer import (  # noqa: E402
    DeveloperInstallerProvisioner,
    ProvisionConfig as InstallerProvisionConfig,
)
from build_profile import BuildProfile  # noqa: E402


PNG = b"\x89PNG\r\n\x1a\nsynthetic"


class DeveloperRemoteTests(unittest.TestCase):
    def test_development_profile_is_explicit_and_normal_profile_is_not(self):
        dev = BuildProfile.load(PROJECT_ROOT / "build/profiles/modern-amd64-dev.toml")
        normal = BuildProfile.load(PROJECT_ROOT / "build/profiles/modern-amd64.toml")
        self.assertIn("developer-remote", dev.package_set_names("target"))
        self.assertIn("developer-remote", dev.package_set_names("installer"))
        self.assertNotIn("developer-remote", normal.package_set_names("target"))
        self.assertNotIn("developer-remote", normal.package_set_names("installer"))
        self.assertEqual(dev.image.hostname, "greia-dev")
        self.assertEqual(dev.identity.certification_state, "experimental")
        packages = dev.resolve_packages(PROJECT_ROOT / "build/package-sets", "target")
        self.assertIn("openssh-server", packages)
        self.assertIn("python3-pil", packages)
        self.assertIn("xdotool", packages)

    def test_display_endpoint_accepts_installed_and_live_users(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "endpoint.json"
            for user in ("greiakid", "root"):
                path.write_text(
                    json.dumps({"user": user, "display": ":0"}),
                    encoding="utf-8",
                )
                endpoint = DeveloperDisplayEndpoint.load(path)
                self.assertEqual(endpoint.user, user)
                self.assertEqual(endpoint.display, ":0")
                self.assertEqual(
                    endpoint.runuser_prefix()[:4],
                    ["runuser", "--user", user, "--"],
                )

    def test_display_endpoint_rejects_unbounded_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "endpoint.json"
            path.write_text(
                json.dumps({"user": "root;id", "display": ":0"}),
                encoding="utf-8",
            )
            with self.assertRaises(DeveloperSessionError):
                DeveloperDisplayEndpoint.load(path)
            path.write_text(
                json.dumps({"user": "root", "display": "bad display"}),
                encoding="utf-8",
            )
            with self.assertRaises(DeveloperSessionError):
                DeveloperDisplayEndpoint.load(path)

    def test_capture_rejects_unbounded_display_selector_before_backend_access(self):
        with self.assertRaises(DeveloperCaptureError):
            capture_legacy_x11_png("bad display")

    def test_screenshot_runs_as_declared_display_user_and_requires_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / "developer-remote"
            marker.write_text("enabled\n", encoding="utf-8")
            state = root / "state"
            endpoint = DeveloperDisplayEndpoint(user="greiakid", display=":0")
            with (
                mock.patch.object(devctl, "DEVELOPER_MARKER", marker),
                mock.patch.object(devctl, "STATE_ROOT", state),
                mock.patch.object(
                    devctl, "DEVELOPER_ACTIVITY_ROOT", state / "activities"
                ),
                mock.patch.object(devctl, "STAGING_ROOT", state / "staging"),
                mock.patch.object(devctl, "BACKUP_ROOT", state / "backups"),
                mock.patch.object(devctl, "STATE_FILE", state / "deployments.json"),
                mock.patch("greia_platform.developer_control.os.geteuid", return_value=0),
                mock.patch.object(
                    devctl.DeveloperDisplayEndpoint,
                    "load",
                    return_value=endpoint,
                ),
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

    def test_developer_state_permissions_expose_only_activity_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / "developer-remote"
            marker.write_text("enabled\n", encoding="utf-8")
            state = root / "state"
            endpoint = DeveloperDisplayEndpoint(user="greiakid", display=":0")
            with (
                mock.patch.object(devctl, "DEVELOPER_MARKER", marker),
                mock.patch.object(devctl, "STATE_ROOT", state),
                mock.patch.object(
                    devctl, "DEVELOPER_ACTIVITY_ROOT", state / "activities"
                ),
                mock.patch.object(devctl, "STAGING_ROOT", state / "staging"),
                mock.patch.object(devctl, "BACKUP_ROOT", state / "backups"),
                mock.patch.object(devctl, "STATE_FILE", state / "deployments.json"),
                mock.patch("greia_platform.developer_control.os.geteuid", return_value=0),
                mock.patch.object(
                    devctl.DeveloperDisplayEndpoint,
                    "load",
                    return_value=endpoint,
                ),
            ):
                devctl.DeveloperControl()
            self.assertEqual(stat.S_IMODE(state.stat().st_mode), 0o755)
            self.assertEqual(
                stat.S_IMODE((state / "activities").stat().st_mode), 0o755
            )
            self.assertEqual(stat.S_IMODE((state / "staging").stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((state / "backups").stat().st_mode), 0o700)

    def test_activity_id_validation_rejects_path_escape(self):
        devctl._validate_activity_id("maze.one")
        with self.assertRaises(devctl.DeveloperControlError):
            devctl._validate_activity_id("../escape")
        with self.assertRaises(devctl.DeveloperControlError):
            devctl._validate_activity_id(".hidden")

    def test_launcher_activity_sources_preserve_package_trust(self):
        paths = SimpleNamespace(
            activities=Path("/opt/greia-os/activities"),
            developer_activities=Path("/var/lib/greia-developer/activities"),
        )
        sources = _activity_sources(paths)
        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0].trust, PackageTrust.BUILT_IN)
        self.assertEqual(sources[1].trust, PackageTrust.DEVELOPER_UNSIGNED)
        self.assertEqual(sources[1].source_id, "greia-developer-remote")

    def test_launcher_rejects_overlapping_developer_and_system_roots(self):
        paths = SimpleNamespace(
            activities=Path("/opt/greia-os/activities"),
            developer_activities=Path("/opt/greia-os/activities/developer"),
        )
        with self.assertRaises(ActivityValidationError):
            _activity_sources(paths)

    def test_gui_input_runs_only_xdotool_as_declared_display_user(self):
        endpoint = DeveloperDisplayEndpoint(user="greiakid", display=":0")
        with (
            mock.patch.object(
                devinput,
                "_developer_endpoint",
                return_value=endpoint,
            ),
            mock.patch(
                "greia_platform.developer_input.subprocess.run",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as run,
        ):
            devinput.key(["Return", "ctrl+l"])
        argv = run.call_args.args[0]
        self.assertEqual(argv[:4], ["runuser", "--user", "greiakid", "--"])
        self.assertIn("DISPLAY=:0", argv)
        self.assertIn("/usr/bin/xdotool", argv)
        self.assertEqual(
            argv[-4:], ["key", "--clearmodifiers", "Return", "ctrl+l"]
        )

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
                        "profile": {"id": "modern-amd64-dev"},
                        "package_sets": {"target": ["developer-remote"]},
                    }
                ),
                encoding="utf-8",
            )
            provisioner = DeveloperImageProvisioner(
                ProvisionConfig(image=root / "unused.img", output_dir=root / "out")
            )
            payload = provisioner._validate_profile(root)
            self.assertEqual(payload["profile"]["id"], "modern-amd64-dev")
            profile_path.write_text(
                json.dumps(
                    {
                        "profile": {"id": "modern-amd64"},
                        "package_sets": {"target": ["developer-remote"]},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                DeveloperImageProvisionError, "non-developer"
            ):
                provisioner._validate_profile(root)

    def test_provisioner_rejects_persisted_ssh_host_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ssh = root / "etc/ssh"
            ssh.mkdir(parents=True)
            (ssh / "ssh_host_ed25519_key").write_text(
                "private", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                DeveloperImageProvisionError, "retained SSH host identity"
            ):
                DeveloperImageProvisioner._assert_no_host_keys(root)

    def test_live_installer_policy_is_remote_but_not_unattended(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "etc").mkdir(parents=True)
            provisioner = DeveloperInstallerProvisioner(
                InstallerProvisionConfig(
                    root=root,
                    public_key=root / "unused.pub",
                    report=root / "report.json",
                )
            )
            provisioner._write_developer_policy(root)
            provisioner._write_network_policy(root)
            provisioner._write_hostname(root)
            endpoint = json.loads(
                (root / "etc/greia-os/developer-display.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(endpoint, {"user": "root", "display": ":0"})
            network = (
                root / "etc/systemd/network/20-greia-developer-ethernet.network"
            ).read_text(encoding="utf-8")
            self.assertIn("DHCP=yes", network)
            self.assertEqual(
                (root / "etc/hostname").read_text(encoding="utf-8"),
                "greia-installer-dev\n",
            )
            service = (
                root / "etc/systemd/system/greia-developer-remote.service"
            ).read_text(encoding="utf-8")
            self.assertIn("Before=ssh.service", service)
            self.assertNotIn("greia-first-boot.service", service)

    def test_remote_ssh_uses_key_only_batch_mode_and_private_known_hosts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = root / "key"
            key.write_text("private\n", encoding="utf-8")
            known = root / "known_hosts"
            remote = GreiaRemote(
                host="greia-dev.local",
                user="greia",
                key=key,
                known_hosts=known,
            )
            argv = remote.ssh_base()
            self.assertIn("BatchMode=yes", argv)
            self.assertIn("StrictHostKeyChecking=accept-new", argv)
            self.assertIn(f"UserKnownHostsFile={known.resolve()}", argv)
            self.assertEqual(argv[-1], "greia@greia-dev.local")

    def test_remote_ssh_supports_greia_password_login(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            known = root / "known_hosts"
            remote = GreiaRemote(
                host="greia-dev.local",
                user="greia",
                key=Path("/nonexistent-key"),
                known_hosts=known,
                password="greia",
            )
            argv = remote.ssh_base()
            self.assertNotIn("BatchMode=yes", argv)
            self.assertIn("BatchMode=no", argv)
            self.assertIn("StrictHostKeyChecking=accept-new", argv)
            self.assertEqual(argv[-1], "greia@greia-dev.local")

    def test_remote_requires_key_or_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RemoteError):
                GreiaRemote(
                    host="host",
                    user="greia",
                    key=Path("/missing-key"),
                    known_hosts=Path(tmp) / "known_hosts",
                )

    def test_remote_screenshot_writes_only_valid_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = root / "key"
            key.write_text("private\n", encoding="utf-8")
            remote = GreiaRemote(
                host="host",
                user="greia",
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

    def test_remote_gui_and_restart_methods_stay_inside_devctl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = root / "key"
            key.write_text("private\n", encoding="utf-8")
            remote = GreiaRemote(
                host="host",
                user="greia",
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
                remote.restart_launcher()
                call.assert_called_with("restart-launcher")
                remote.restart_installer()
                call.assert_called_with("restart-installer")

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
        self.assertIn(
            "ExecStart=/bin/sh /usr/local/lib/greia-os/prepare-developer-remote",
            unit,
        )
        ssh = (
            PROJECT_ROOT / "build/overlay/etc/ssh/sshd_config.d/20-greia-parent.conf"
        ).read_text(encoding="utf-8")
        self.assertIn("PasswordAuthentication no", ssh)
        self.assertIn("PermitRootLogin no", ssh)
        tmpfiles = (
            PROJECT_ROOT
            / "build/overlay/usr/lib/tmpfiles.d/greia-developer-remote.conf"
        ).read_text(encoding="utf-8")
        self.assertIn("/usr/local/sbin/greia-devctl 0755 root root", tmpfiles)

    def test_developer_builder_wraps_canonical_image_builder(self):
        wrapper = (PROJECT_ROOT / "build/build-developer-image.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '"$SCRIPT_DIR/build-image.sh" "$PROFILE" "$OUTPUT_DIR"', wrapper
        )
        self.assertNotIn("tools/provision_developer_image.py", wrapper)
        self.assertNotIn("debootstrap", wrapper)

    def test_canonical_builder_emits_bounded_greia_devctl_sudoers(self):
        # T01: target-role developer provisioning lives in the shared engine;
        # the thin consumer must not mint SSH/sudo surface itself.
        consumer = (PROJECT_ROOT / "build/build-image.sh").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("NOPASSWD:", consumer)
        self.assertIn('compose_root --profile "$PROFILE_PATH" --role target', consumer)
        builder = (PROJECT_ROOT / "build/lib/compose.sh").read_text(
            encoding="utf-8"
        )
        expected = (
            "# Development-image only: privileged operations stay inside"
            " greia-devctl.\n"
            "greia ALL=(root) NOPASSWD: /usr/local/sbin/greia-devctl\n"
        )
        self.assertIn(expected, builder)
        self.assertIn("etc/sudoers.d/greia-developer-remote", builder)
        self.assertIn("0440", builder)
        self.assertIn("visudo", builder)
        self.assertIn("-cf", builder)
        # The rule lives inside the target developer-remote provisioner, whose
        # only caller is guarded by the developer-remote package-set
        # conditional.
        func_start = builder.index("compose_provision_developer_ssh_target()")
        func_body = builder[func_start:]
        self.assertIn("greia ALL=(root) NOPASSWD:", func_body)
        self.assertIn(
            'if [[ "$role_sets" == *developer-remote* ]]',
            builder,
        )
        # Bounded: no wildcards, no second principal, no second binary.
        rule_lines = [
            line
            for line in builder.splitlines()
            if "NOPASSWD:" in line and "greia-devctl" in line
        ]
        self.assertEqual(len(rule_lines), 1)
        rule = rule_lines[0].strip()
        self.assertEqual(
            rule, "greia ALL=(root) NOPASSWD: /usr/local/sbin/greia-devctl"
        )
        self.assertNotIn("*", rule)
        self.assertNotIn("greiaadmin", rule)
        self.assertNotIn("provision_developer_image.py", builder)
        # Release surface: no common-overlay sudoers file gains this rule.
        self.assertFalse(
            (
                PROJECT_ROOT
                / "build/overlay/etc/sudoers.d/greia-developer-remote"
            ).exists()
        )

    def test_canonical_builder_sudoers_bytes_are_visudo_clean(self):
        builder = (PROJECT_ROOT / "build/lib/compose.sh").read_text(
            encoding="utf-8"
        )
        marker = (
            "cat > \"$rootfs/etc/sudoers.d/greia-developer-remote\""
            " <<'SUDOERS'\n"
        )
        start = builder.index(marker) + len(marker)
        end = builder.index("\nSUDOERS", start)
        body = builder[start:end] + "\n"
        expected = (
            "# Development-image only: privileged operations stay inside"
            " greia-devctl.\n"
            "greia ALL=(root) NOPASSWD: /usr/local/sbin/greia-devctl\n"
        )
        self.assertEqual(body, expected)
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "greia-developer-remote"
            candidate.write_text(body, encoding="utf-8")
            os.chmod(candidate, 0o440)
            self.assertEqual(stat.S_IMODE(candidate.stat().st_mode), 0o440)
            visudo = Path("/usr/sbin/visudo")
            if visudo.exists():
                completed = subprocess.run(
                    [str(visudo), "-cf", str(candidate)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    completed.returncode,
                    0,
                    msg=completed.stderr or completed.stdout,
                )


if __name__ == "__main__":
    unittest.main()
