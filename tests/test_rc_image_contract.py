"""Release-candidate image contracts (2026-10-17).

Covers the source side of the developer RC (``legacy-x86-i686-rc``): the boot
console policy decoupled from the developer/SSH marker, the quiet Syslinux and
GRUB paths with their hidden verbose fallbacks, operator public-key input, the
microphone module build that must fail loudly, Wi-Fi netdev grants, the live
installer bytecode/SDL settings and the shared artifact verifier. Evidence
class: SOURCE only; none of this proves boot behaviour on hardware.
"""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from greia_platform.boot_contract import (  # noqa: E402
    BootConsolePolicy,
    GrubContractError,
    KernelCommandLine,
    validate_grub_text,
    validate_kernel_command_line,
)
from greia_platform.grub_security import GRUB_USER  # noqa: E402
from build_profile import BuildProfile, BuildProfileError  # noqa: E402

AUTH = (
    f'set superusers="{GRUB_USER}"\n'
    "export superusers\n"
    f"password_pbkdf2 {GRUB_USER} grub.pbkdf2.sha512.10000.ABCD1234\n"
)
UUID = "12345678-1234-5678-9abc-def012345678"
QUIET = (
    f"linux /vmlinuz root=UUID={UUID} ro quiet splash loglevel=0 "
    "systemd.show_status=false rd.systemd.show_status=false udev.log_priority=3 "
    "vt.global_cursor_default=0 console=tty1 panic=0 systemd.crash_shell=no "
    "systemd.crash_chvt=0 consoleblank=0"
)
DIAGNOSTIC = (
    f"linux /vmlinuz root=UUID={UUID} ro loglevel=4 systemd.show_status=true "
    "rd.systemd.show_status=true udev.log_priority=4 vt.global_cursor_default=1 "
    "console=tty1 panic=0 systemd.crash_shell=no systemd.crash_chvt=0 consoleblank=0"
)


def entry(line: str, *, entry_id: str = "greia-os", unrestricted: bool = True) -> str:
    flag = " --unrestricted" if unrestricted else ""
    return f"menuentry 'Greia OS'{flag} --id {entry_id} {{\n  {line}\n  initrd /initrd.img\n}}\n"


def declared(policy: str) -> str:
    return f"# greia-boot-console-policy: {policy}\n"


class ConsolePolicyContractTests(unittest.TestCase):
    def test_rc_quiet_developer_config_with_restricted_diagnostics_passes(self) -> None:
        text = (
            AUTH + declared("quiet") + entry(QUIET)
            + entry(DIAGNOSTIC, entry_id="greia-os-diagnostics", unrestricted=False)
        )
        lines = validate_grub_text(text, developer=True)
        self.assertEqual(len(lines), 1)
        self.assertIn("console=tty1", lines[0].arguments)
        validate_grub_text(text, developer=True, console_policy="quiet")

    def test_developer_default_stays_diagnostic(self) -> None:
        validate_grub_text(AUTH + entry(DIAGNOSTIC), developer=True)
        with self.assertRaises(GrubContractError):
            validate_grub_text(AUTH + entry(QUIET), developer=True)

    def test_release_never_accepts_diagnostic_or_restricted_entries(self) -> None:
        validate_grub_text(AUTH + entry(QUIET))
        with self.assertRaisesRegex(GrubContractError, "quiet"):
            validate_grub_text(AUTH + declared("diagnostic") + entry(DIAGNOSTIC))
        with self.assertRaises(GrubContractError):
            validate_grub_text(
                AUTH + declared("quiet") + entry(QUIET)
                + entry(DIAGNOSTIC, entry_id="greia-os-diagnostics", unrestricted=False)
            )

    def test_diagnostic_developer_rejects_extra_entry(self) -> None:
        with self.assertRaises(GrubContractError):
            validate_grub_text(
                AUTH + entry(DIAGNOSTIC)
                + entry(DIAGNOSTIC, entry_id="greia-os-diagnostics", unrestricted=False),
                developer=True,
            )

    def test_diagnostics_entry_shape_is_strict(self) -> None:
        base = AUTH + declared("quiet") + entry(QUIET)
        for extra, why in (
            (entry(DIAGNOSTIC, entry_id="other", unrestricted=False), "wrong id"),
            (entry(QUIET, entry_id="greia-os-diagnostics", unrestricted=False), "quiet args"),
            (entry(DIAGNOSTIC.replace("panic=0", "panic=30"), entry_id="greia-os-diagnostics",
                   unrestricted=False), "timed panic"),
            (entry(DIAGNOSTIC + " init=/bin/sh", entry_id="greia-os-diagnostics",
                   unrestricted=False), "shell"),
            (entry(DIAGNOSTIC, entry_id="greia-os-diagnostics", unrestricted=False) * 2, "two"),
        ):
            with self.subTest(why=why), self.assertRaises(GrubContractError):
                validate_grub_text(base + extra, developer=True)
        with self.assertRaisesRegex(GrubContractError, "first"):
            validate_grub_text(
                AUTH + declared("quiet")
                + entry(DIAGNOSTIC, entry_id="greia-os-diagnostics", unrestricted=False)
                + entry(QUIET),
                developer=True,
            )

    def test_explicit_policy_must_match_declaration(self) -> None:
        with self.assertRaisesRegex(GrubContractError, "declares"):
            validate_grub_text(
                AUTH + declared("quiet") + entry(QUIET), developer=True, console_policy="diagnostic"
            )
        with self.assertRaises(GrubContractError):
            validate_grub_text(AUTH + declared("loud") + entry(QUIET), developer=True)

    def test_quiet_policy_keeps_panic_zero_and_hidden_cursor(self) -> None:
        required = BootConsolePolicy.QUIET.required_arguments
        self.assertIn("panic=0", required)
        self.assertIn("vt.global_cursor_default=0", required)
        self.assertIn("panic=0", BootConsolePolicy.DIAGNOSTIC.required_arguments)


class InstalledGrubGeneratorTests(unittest.TestCase):
    """Run the real 10_greia_appliance against a fixture /etc/greia-os."""

    def render(self, *, developer: bool, policy: str | None) -> subprocess.CompletedProcess[str]:
        script = (ROOT / "build/overlay/etc/grub.d/10_greia_appliance").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as raw:
            etc = Path(raw) / "etc-greia-os"
            etc.mkdir()
            (etc / "root-filesystem-uuid").write_text(UUID + "\n", encoding="ascii")
            if developer:
                (etc / "developer-remote").write_text("profile=test\n", encoding="ascii")
            if policy is not None:
                (etc / "boot-console-policy").write_text(policy + "\n", encoding="ascii")
            generator = Path(raw) / "10_greia_appliance"
            generator.write_text(script.replace("/etc/greia-os/", f"{etc}/"), encoding="utf-8")
            return subprocess.run(["sh", str(generator)], capture_output=True, text=True, check=False)

    def test_release_quiet(self) -> None:
        result = self.render(developer=False, policy="quiet")
        self.assertEqual(result.returncode, 0, result.stderr)
        validate_grub_text(AUTH + result.stdout)
        self.assertNotIn("greia-os-diagnostics", result.stdout)
        self.assertNotIn("keystatus", result.stdout)

    def test_developer_without_policy_file_is_unchanged_diagnostic(self) -> None:
        result = self.render(developer=True, policy=None)
        self.assertEqual(result.returncode, 0, result.stderr)
        validate_grub_text(AUTH + result.stdout, developer=True, console_policy="diagnostic")
        self.assertNotIn("greia-os-diagnostics", result.stdout)

    def test_rc_quiet_developer_has_shift_menu_and_owner_diagnostics(self) -> None:
        result = self.render(developer=True, policy="quiet")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = validate_grub_text(AUTH + result.stdout, developer=True, console_policy="quiet")
        self.assertIn("console=tty1", lines[0].arguments)
        self.assertIn("keystatus --shift", result.stdout)
        self.assertIn("--id greia-os-diagnostics", result.stdout)
        self.assertNotRegex(result.stdout, r"panic=[1-9]")

    def test_release_cannot_render_diagnostic_or_unknown(self) -> None:
        self.assertNotEqual(self.render(developer=False, policy="diagnostic").returncode, 0)
        self.assertNotEqual(self.render(developer=True, policy="loud").returncode, 0)


class LiveSyslinuxTemplateTests(unittest.TestCase):
    @staticmethod
    def appends(path: Path) -> dict[str, str]:
        label, result = None, {}
        for raw in path.read_text(encoding="utf-8").splitlines():
            parts = raw.split(None, 1)
            if parts and parts[0] == "LABEL":
                label = parts[1].strip()
            elif parts and parts[0] == "APPEND" and label:
                result[label] = parts[1].strip()
        return result

    def test_quiet_template_default_is_silent_and_verbose_matches_diagnostic(self) -> None:
        quiet = self.appends(ROOT / "build/live-syslinux/syslinux-quiet.cfg.in")
        diagnostic = self.appends(ROOT / "build/live-syslinux/syslinux.cfg.in")
        self.assertEqual(set(quiet), {"live", "verbose"})
        self.assertEqual(quiet["verbose"], diagnostic["live"])
        line = KernelCommandLine(1, "linux", "/vmlinuz", tuple(quiet["live"].split()))
        validate_kernel_command_line(line, developer=True, console_policy="quiet")
        verbose = KernelCommandLine(1, "linux", "/vmlinuz", tuple(quiet["verbose"].split()))
        self.assertIn("console=tty1", verbose.arguments)
        self.assertIn("panic=0", verbose.arguments)
        text = (ROOT / "build/live-syslinux/syslinux-quiet.cfg.in").read_text(encoding="utf-8")
        # Owner decision 2026-10-18: the quiet path clears the stock SYSLINUX
        # banner with the one-byte form-feed display file. The diagnostic
        # template must stay observable (asserted separately in
        # test_boot_diagnostics_hardening).
        for required in (
            "DISPLAY /boot/syslinux/clear.msg",
            "DEFAULT live",
            "PROMPT 0",
            "TIMEOUT 0",
        ):
            self.assertIn(required, text)
        for banned in ("UI ", "panic=30", "NOESCAPE"):
            self.assertNotIn(banned, text)
        diagnostic = (ROOT / "build/live-syslinux/syslinux.cfg.in").read_text(encoding="utf-8")
        self.assertNotIn("DISPLAY ", diagnostic)
        self.assertNotIn("clear.msg", diagnostic)

    def test_writer_and_verifier_share_the_manifest_driven_selection(self) -> None:
        lib = (ROOT / "build/lib/live-syslinux.sh").read_text(encoding="utf-8")
        self.assertIn(".disk/installer-image-profile.json", lib)
        self.assertIn('get("console_policy", "diagnostic")', lib)
        for tool in ("tools/build-live-usb.sh", "tools/verify-live-usb.sh"):
            text = (ROOT / tool).read_text(encoding="utf-8")
            self.assertIn("build/lib/live-syslinux.sh", text)
            self.assertIn("greia_live_console_policy", text)
            self.assertIn("$SYSLINUX_TEMPLATE", text)


class NoNullConsoleRegressionTests(unittest.TestCase):
    """2026-10-17 RC stick froze on the Syslinux banner (QEMU-reproduced).

    ``console=null`` selects the ``ttynull`` driver, which the Debian 686
    kernel does not build (``CONFIG_NULL_TTY`` unset). The system then has no
    console, PID 1 starts without stdio, live-boot's ``exec 6>&1`` fails with
    "Bad file descriptor", /init exits and the kernel panics (panic=0 keeps it
    frozen) before anything is drawn. Quiet boots must silence a real tty1.
    """

    BOOT_SOURCES = (
        "build/live-syslinux/syslinux-quiet.cfg.in",
        "build/live-syslinux/syslinux.cfg.in",
        "build/build-installer-image.sh",
        "build/overlay/etc/grub.d/10_greia_appliance",
        "build/overlay/etc/default/grub.d/10-greia-quiet.cfg",
        "build/installer-overlay/etc/default/grub.d/10-greia-quiet.cfg",
        "tools/prepare-antix-sd-boot.sh",
    )

    def test_no_boot_source_passes_a_null_console_to_the_kernel(self) -> None:
        import re

        for rel in self.BOOT_SOURCES:
            with self.subTest(source=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                kernel_lines = [
                    line for line in text.splitlines()
                    if not line.lstrip().startswith("#") and "console=" in line
                ]
                self.assertTrue(kernel_lines, f"no kernel command line found in {rel}")
                for line in kernel_lines:
                    self.assertNotRegex(line, r"console=(null)?([\s\"']|$)")
                    self.assertIn("console=tty1", line)

    def test_contract_rejects_null_console_in_every_policy(self) -> None:
        quiet_ok = QUIET.split()[2:]
        for console in ("console=null", "console="):
            args = tuple(a if not a.startswith("console=") else console for a in quiet_ok)
            line = KernelCommandLine(1, "linux", "/vmlinuz", args)
            for developer in (False, True):
                with self.subTest(console=console, developer=developer):
                    with self.assertRaisesRegex(GrubContractError, "without a console"):
                        validate_kernel_command_line(
                            line, developer=developer, console_policy="quiet"
                        )

    def test_quiet_syslinux_default_has_exactly_one_real_console(self) -> None:
        quiet = LiveSyslinuxTemplateTests.appends(
            ROOT / "build/live-syslinux/syslinux-quiet.cfg.in"
        )
        for label, append in quiet.items():
            with self.subTest(label=label):
                consoles = [a for a in append.split() if a.startswith("console=")]
                self.assertEqual(consoles, ["console=tty1"])


class LiveInstallerQuietScreenTests(unittest.TestCase):
    """2026-10-17 QEMU findings after the console fix: no text may reach VT1."""

    LIVE_ENTRIES = (
        "build/live-syslinux/syslinux-quiet.cfg.in",
        "build/live-syslinux/syslinux.cfg.in",
        "build/build-installer-image.sh",
        "tools/prepare-antix-sd-boot.sh",
    )

    def test_every_live_entry_disables_live_boot_ifupdown_preconfiguration(self) -> None:
        # Without it live-boot's Netbase() printed "/init: line 29: can't
        # create /root/etc/network/interfaces" (the live root uses networkd).
        for rel in self.LIVE_ENTRIES:
            with self.subTest(source=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                lines = [
                    line for line in text.splitlines()
                    if "boot=live" in line and not line.lstrip().startswith("#")
                ]
                self.assertTrue(lines)
                for line in lines:
                    self.assertIn(" nonetworking ", f" {line} ")
        from greia_platform.boot_contract import LIVE_REQUIRED_ARGUMENTS

        self.assertIn("nonetworking", LIVE_REQUIRED_ARGUMENTS)

    def test_installer_restarts_after_a_crash_behind_the_cover(self) -> None:
        unit = (
            ROOT / "build/installer-overlay/etc/systemd/system/greia-installer.service"
        ).read_text(encoding="utf-8")
        directives = [line.strip() for line in unit.splitlines() if not line.startswith("#")]
        # xinit is the main process and exits 0 after a client traceback, so
        # on-failure never fired.
        self.assertIn("ExecStart=/usr/bin/xinit", unit)
        self.assertIn("Restart=always", directives)
        self.assertNotIn("Restart=on-failure", directives)
        interval = next(d for d in directives if d.startswith("StartLimitIntervalSec="))
        burst = next(d for d in directives if d.startswith("StartLimitBurst="))
        self.assertGreaterEqual(int(interval.split("=")[1]), 300)
        self.assertLessEqual(int(burst.split("=")[1]), 6)
        self.assertIn(
            "ExecStopPost=+/usr/local/lib/greia-os/installer-exit-cover", directives
        )
        helper = ROOT / "build/installer-overlay/usr/local/lib/greia-os/installer-exit-cover"
        self.assertTrue(os.access(helper, os.X_OK))
        script = helper.read_text(encoding="utf-8")
        self.assertIn("/usr/lib/greia-boot/greia-fb-splash", script)
        self.assertIn("exit 0", script)
        verifier = (ROOT / "build/lib/verify-composed-root.sh").read_text(encoding="utf-8")
        self.assertIn("installer-exit-cover", verifier)


class RcProfileTests(unittest.TestCase):
    def test_rc_profile_is_base_composition_plus_developer_remote_and_quiet(self) -> None:
        base = BuildProfile.load(ROOT / "build/profiles/legacy-x86-i686.toml")
        rc = BuildProfile.load(ROOT / "build/profiles/legacy-x86-i686-rc.toml")
        self.assertEqual(rc.identity.profile_id, "legacy-x86-i686-rc")
        self.assertEqual(rc.boot.console_policy, "quiet")
        self.assertEqual(rc.image.hostname, "greia-rc")
        self.assertNotEqual(rc.identity.certification_state, "certified")
        for scope in ("target", "installer"):
            self.assertEqual(
                set(rc.package_set_names(scope)) - set(base.package_set_names(scope)),
                {"developer-remote"},
            )
        self.assertEqual(rc.base, base.base)
        self.assertEqual(rc.storage, base.storage)
        self.assertEqual(rc.resources.required_core_mib, 1500)
        manifest = rc.declared_manifest("installer")
        self.assertEqual(manifest["boot"]["console_policy"], "quiet")
        self.assertIn("BOOT_CONSOLE_POLICY=quiet", rc.shell_assignments().splitlines())

    def test_console_policy_validation(self) -> None:
        source = (ROOT / "build/profiles/legacy-x86-i686.toml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "p.toml"
            path.write_text(
                source.replace('cover_backend = "greia-early-framebuffer-v1"',
                               'cover_backend = "greia-early-framebuffer-v1"\nconsole_policy = "diagnostic"'),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(BuildProfileError, "developer-remote"):
                BuildProfile.load(path)
            path.write_text(
                source.replace('cover_backend = "greia-early-framebuffer-v1"',
                               'cover_backend = "greia-early-framebuffer-v1"\nconsole_policy = "loud"'),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(BuildProfileError, "console_policy"):
                BuildProfile.load(path)

    def test_single_root_size_gate_follows_owner_decision(self) -> None:
        for path in sorted((ROOT / "build/profiles").glob("*.toml")):
            profile = BuildProfile.load(path)
            with self.subTest(profile=path.name):
                if profile.storage.layout_adapter == "bios-single-ext4":
                    self.assertEqual(profile.resources.required_core_mib, 1500)
                else:
                    # A/B system slots are 1 GiB: the root must stay below it.
                    self.assertLess(
                        profile.resources.required_core_mib * 1024 * 1024,
                        profile.storage.system_slot_bytes + 1,
                    )

    def test_front_doors_accept_rc_and_operator_key(self) -> None:
        installer = (ROOT / "tools/build-development-installer.sh").read_text(encoding="utf-8")
        flash = (ROOT / "tools/build-and-flash-development-usb.sh").read_text(encoding="utf-8")
        developer = (ROOT / "build/build-developer-image.sh").read_text(encoding="utf-8")
        self.assertIn("*-dev|*-rc)", installer)
        self.assertIn("*-dev|*-rc)", developer)
        self.assertIn("--operator-key", installer)
        self.assertIn("GREIA_OPERATOR_AUTHORIZED_KEY_FILE", installer)
        self.assertIn("--operator-key", flash)
        self.assertIn("boot_console_policy=", flash)
        image = (ROOT / "build/build-image.sh").read_text(encoding="utf-8")
        self.assertIn('--console-policy "$BOOT_CONSOLE_POLICY"', image)


class CompositionContractTests(unittest.TestCase):
    compose = (ROOT / "build/lib/compose.sh").read_text(encoding="utf-8")
    installer = (ROOT / "build/build-installer-image.sh").read_text(encoding="utf-8")

    def function(self, name: str) -> str:
        start = self.compose.index(f"{name}() {{")
        end = self.compose.index("\n}\n", start)
        return self.compose[start:end]

    def test_policy_file_written_for_both_roles(self) -> None:
        self.assertIn('compose_write_boot_console_policy "$rootfs" || return 1', self.compose)
        self.assertIn('compose_write_boot_console_policy "$LIVE_ROOT"', self.installer)
        self.assertIn("/etc/greia-os/boot-console-policy", self.function("compose_write_boot_console_policy"))

    def test_mic_plugin_build_fails_loudly_in_both_roles(self) -> None:
        body = self.function("compose_build_audio_endpoint_plugin")
        self.assertIn("libc6-dev", body)
        self.assertIn("gcc -print-multiarch", body)
        code = "\n".join(l for l in body.splitlines() if not l.strip().startswith("#"))
        self.assertNotIn("dpkg-architecture", code)
        self.assertIn("compose_verify_audio_endpoint_plugin", body)
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith(("chroot ", "install ", "cp ")) and not stripped.endswith("\\"):
                if "autoremove" in stripped:
                    continue
                self.assertTrue(
                    "|| return 1" in stripped or "|| {" in stripped,
                    f"unchecked step in plugin build: {stripped}",
                )
        self.assertIn('compose_build_audio_endpoint_plugin "$LIVE_ROOT"', self.installer)
        self.assertIn('compose_verify_audio_endpoint_plugin "$LIVE_ROOT"', self.installer)
        self.assertIn('compose_verify_audio_endpoint_plugin "$rootfs" || return 1', self.compose)

    def test_mic_plugin_build_stops_on_compile_failure(self) -> None:
        """Behavioural: a failing compile returns non-zero even under `|| return 1`."""
        with tempfile.TemporaryDirectory() as raw:
            script = f'''
set -u
source "{ROOT}/build/lib/compose.sh"
set +e
ARCH=i386
chroot() {{
  case "$*" in
    *print-multiarch*) echo i386-linux-gnu ;;
    *"gcc -O2"*) return 1 ;;
  esac
  return 0
}}
wrapper() {{ compose_build_audio_endpoint_plugin "{raw}" || return 1; }}
wrapper
echo "rc=$?"
'''
            result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
            self.assertIn("rc=1", result.stdout, result.stderr)
            self.assertIn("failed to compile", result.stderr)

    def test_wifi_and_journal_and_bytecode(self) -> None:
        users = self.function("compose_create_users_groups")
        self.assertIn("groupadd --system -f netdev", users)
        self.assertIn("audio,netdev greiakid", users)
        self.assertIn("pipprofiles,netdev greiapanel", users)
        self.assertIn('install -d -m 0700 -o root -g root "$rootfs/var/lib/iwd"', users)
        self.assertNotIn("greiaprofiles", users.split("compose_create_users_groups() {")[1])
        journal = self.function("compose_configure_developer_journal")
        self.assertIn("Storage=persistent", journal)
        self.assertIn("SystemMaxUse=48M", journal)
        self.assertIn('compose_precompile_bytecode "$LIVE_ROOT"', self.installer)
        root_body = self.function("compose_root")
        self.assertIn('compose_precompile_bytecode "$rootfs" || return 1', root_body)
        self.assertNotIn('if [[ "$role" == "target" ]]; then\n    compose_precompile_bytecode', root_body)

    def test_units_and_overlays(self) -> None:
        launcher = (ROOT / "build/overlay/etc/systemd/system/greia-launcher.service").read_text()
        parent = (ROOT / "build/overlay/etc/systemd/system/greia-parent.service").read_text()
        installer = (ROOT / "build/installer-overlay/etc/systemd/system/greia-installer.service").read_text()
        self.assertIn("SupplementaryGroups=audio tty netdev\n", launcher)
        self.assertIn("SupplementaryGroups=netdev\n", parent)
        self.assertIn("Environment=SDL_FRAMEBUFFER_ACCELERATION=0\n", installer)
        self.assertIn("Environment=PYTHONPYCACHEPREFIX=/usr/lib/greia/pycache\n", installer)
        for overlay in ("build/overlay", "build/installer-overlay"):
            text = (ROOT / overlay / "etc/modprobe.d/greia-audio.conf").read_text()
            self.assertIn("options snd_hda_intel power_save=0", text)

    def test_developer_remote_unit_cannot_kill_itself(self) -> None:
        unit = (ROOT / "build/overlay/etc/systemd/system/greia-developer-remote.service").read_text()
        script = (ROOT / "build/overlay/usr/local/lib/greia-os/prepare-developer-remote").read_text()
        self.assertNotIn("Requires=greia-first-boot.service systemd-networkd", unit)
        self.assertNotRegex(unit, r"Requires=.*systemd-(networkd|resolved)")
        self.assertNotIn("systemctl restart systemd-networkd", script)
        self.assertNotIn("/usr/bin/ssh-keygen -A", script)
        self.assertNotIn("greia-developer-remote.service", self.function("compose_configure_systemd"))


class OperatorKeyTests(unittest.TestCase):
    tool = ROOT / "build/lib/operator_key.py"

    def run_tool(self, content: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "in.pub"
            source.write_text(content, encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-I", "-B", str(self.tool), str(source), str(Path(raw) / "out")],
                capture_output=True, text=True,
            )

    @staticmethod
    def fake_key(kind: str = "ssh-ed25519") -> str:
        blob = len(kind).to_bytes(4, "big") + kind.encode() + (32).to_bytes(4, "big") + bytes(32)
        return f"{kind} {base64.b64encode(blob).decode()} op@host"

    def test_accepts_public_key_and_prints_fingerprint(self) -> None:
        result = self.run_tool(self.fake_key() + "\n# comment\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("operator_ssh_key=SHA256:", result.stdout)

    def test_rejects_private_keys_options_and_mismatched_types(self) -> None:
        for content in (
            "-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n-----END OPENSSH PRIVATE KEY-----\n",
            'command="/bin/sh" ' + self.fake_key() + "\n",
            self.fake_key().replace("ssh-ed25519 ", "ssh-rsa ", 1) + "\n",
            "ssh-ed25519 not-base64!!\n",
            "\n",
        ):
            with self.subTest(content=content[:30]):
                self.assertEqual(self.run_tool(content).returncode, 1)

    def test_ssh_bootstrap_keeps_password_and_adds_key_or(self) -> None:
        for overlay in ("build/overlay", "build/installer-overlay"):
            helper = (ROOT / overlay / "usr/local/lib/greia-os/prepare-developer-ssh").read_text()
            with self.subTest(overlay=overlay):
                self.assertIn("operator_keys=/etc/ssh/greia-operator-keys/greia", helper)
                self.assertIn("/var/lib/greia/.ssh/authorized_keys", helper)
                self.assertIn("PasswordAuthentication yes", helper)
                self.assertIn("PermitRootLogin no", helper)
                self.assertIn("DenyUsers root", helper)


@unittest.skipUnless(shutil.which("bash"), "bash required")
class SharedArtifactVerifierTests(unittest.TestCase):
    """Run build/lib/verify-composed-root.sh against a fixture root."""

    def make_root(self, raw: str, *, policy: str = "quiet") -> Path:
        root = Path(raw) / "root"
        overlay = ROOT / "build/overlay"
        def put(rel: str, text: str = "x\n") -> None:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        for rel in ("etc/systemd/system/greia-launcher.service",
                    "etc/systemd/system/greia-parent.service",
                    "etc/grub.d/10_greia_appliance",
                    "etc/modprobe.d/greia-audio.conf",
                    "usr/local/lib/greia-os/prepare-developer-ssh"):
            put(rel, (overlay / rel).read_text(encoding="utf-8"))
        for rel in (
            "etc/systemd/system/greia-software-update-recover.service",
            "etc/systemd/system/greia-software-update-apply.service",
            "etc/systemd/system/greia-software-update-apply.timer",
        ):
            put(rel, (overlay / rel).read_text(encoding="utf-8"))
        put("usr/local/lib/greia-os/software-update-bootstrap.py",
            (overlay / "usr/local/lib/greia-os/software-update-bootstrap.py").read_text(encoding="utf-8"))
        os.chmod(root / "usr/local/lib/greia-os/software-update-bootstrap.py", 0o755)
        put("etc/greia-os/software-update-bootstrap.json", '{"schema_version":1}\n')
        put("opt/greia-software/generations/base/activity-index-v1.json", "{}\n")
        (root / "opt/greia-os").symlink_to("greia-software/generations/base")
        (root / "usr/share/greia/activity-index-v1.json").parent.mkdir(parents=True, exist_ok=True)
        (root / "usr/share/greia/activity-index-v1.json").symlink_to(
            "../../../opt/greia-os/activity-index-v1.json"
        )
        wants = root / "etc/systemd/system/timers.target.wants"
        wants.mkdir(parents=True, exist_ok=True)
        (wants / "greia-software-update-apply.timer").symlink_to(
            "../greia-software-update-apply.timer"
        )
        put("etc/greia-os/developer-remote", "profile=legacy-x86-i686-rc\n")
        put("etc/greia-os/boot-console-policy", policy + "\n")
        put("etc/greia-os/image-profile.json", '{"boot": {"console_policy": "quiet"}}\n')
        put("etc/group", "netdev:x:108:greiakid,greiapanel\n")
        put("etc/systemd/journald.conf.d/20-greia-developer-persistent.conf",
            "[Journal]\nStorage=persistent\nSystemMaxUse=48M\n")
        put("usr/lib/i386-linux-gnu/alsa-lib/libasound_module_pcm_greia_mic_light.so", "ELF\n")
        put("usr/lib/greia/pycache/opt/greia-os/src/greia_platform/boot_contract.cpython-311.pyc")
        iwd = root / "var/lib/iwd"
        iwd.mkdir(parents=True)
        os.chmod(iwd, 0o700)
        (root / "etc/greia-os/root-filesystem-uuid").write_text(UUID + "\n")
        grub = subprocess.run(
            ["sh", "-c", (overlay / "etc/grub.d/10_greia_appliance").read_text().replace(
                "/etc/greia-os/", f"{root}/etc/greia-os/")],
            capture_output=True, text=True, check=True,
        )
        put("boot/grub/grub.cfg", AUTH + grub.stdout)
        return root

    def verify(self, root: Path) -> subprocess.CompletedProcess[str]:
        script = (
            f'set -Eeuo pipefail; source "{ROOT}/build/lib/verify-composed-root.sh"; '
            f'greia_verify_composed_root "{root}" target fixture "{ROOT}"; '
            'echo "policy=$BOOT_CONSOLE_POLICY_FOUND"'
        )
        env = dict(os.environ, GREIA_VERIFY_ROOT_UID=str(os.getuid()), PYTHONDONTWRITEBYTECODE="1")
        env.pop("GREIA_OPERATOR_AUTHORIZED_KEY_FILE", None)
        return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env)

    def test_complete_rc_fixture_passes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            result = self.verify(self.make_root(raw))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("policy=quiet", result.stdout)

    def test_installer_extraction_includes_the_generation_layout(self) -> None:
        verifier = (ROOT / "tools/verify-development-installer.sh").read_text(encoding="utf-8")
        self.assertIn(
            'extract_for_contract "$TARGET" "$WORK/target-root" target', verifier
        )
        self.assertIn(
            'extract_for_contract "$LIVE" "$WORK/live-root" live-installer', verifier
        )
        self.assertIn("opt/greia-software/generations/base/activity-index-v1.json", verifier)
        self.assertIn("usr/share/greia/activity-index-v1.json", verifier)
        self.assertIn("paths+=(opt/greia-os ", verifier)

    def test_each_missing_contract_fails(self) -> None:
        for rel, why in (
            ("usr/lib/i386-linux-gnu/alsa-lib/libasound_module_pcm_greia_mic_light.so", "ALSA module"),
            ("etc/modprobe.d/greia-audio.conf", "power_save"),
            ("usr/lib/greia/pycache/opt/greia-os/src/greia_platform/boot_contract.cpython-311.pyc", "bytecode"),
            ("etc/systemd/journald.conf.d/20-greia-developer-persistent.conf", "journal"),
            ("etc/greia-os/boot-console-policy", "policy file"),
        ):
            with self.subTest(why=why), tempfile.TemporaryDirectory() as raw:
                root = self.make_root(raw)
                (root / rel).unlink()
                result = self.verify(root)
                self.assertNotEqual(result.returncode, 0, why)

    def make_live_root(self, raw: str) -> Path:
        root = Path(raw) / "live"
        def put(rel: str, text: str = "x\n") -> None:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        put("etc/systemd/system/greia-installer.service",
            (ROOT / "build/installer-overlay/etc/systemd/system/greia-installer.service").read_text())
        put("etc/modprobe.d/greia-audio.conf",
            (ROOT / "build/installer-overlay/etc/modprobe.d/greia-audio.conf").read_text())
        put("usr/local/lib/greia-os/prepare-developer-ssh",
            (ROOT / "build/installer-overlay/usr/local/lib/greia-os/prepare-developer-ssh").read_text())
        put("etc/greia-os/developer-remote", "profile=legacy-x86-i686-rc\n")
        put("etc/greia-os/boot-console-policy", "quiet\n")
        put("etc/greia-os/image-profile.json", '{"boot": {"console_policy": "quiet"}}\n')
        put("etc/passwd",
            "root:x:0:0:root:/root:/bin/sh\n"
            "nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin\n")
        put("etc/group",
            "root:x:0:\n"
            "video:x:44:\n"
            "audio:x:29:\n"
            "nogroup:x:65534:\n"
            "input:x:104:\n"
            "tty:x:5:\n"
            "netdev:x:108:greiakid,greiapanel\n")
        put("usr/lib/i386-linux-gnu/alsa-lib/libasound_module_pcm_greia_mic_light.so", "ELF\n")
        put("usr/lib/greia/pycache/opt/greia-os/src/greia_platform/boot_contract.cpython-311.pyc")
        put("usr/bin/aplay", "#!/bin/sh\n")
        os.chmod(root / "usr/bin/aplay", 0o755)
        put("usr/local/lib/greia-os/installer-exit-cover",
            (ROOT / "build/installer-overlay/usr/local/lib/greia-os/installer-exit-cover").read_text())
        os.chmod(root / "usr/local/lib/greia-os/installer-exit-cover", 0o755)
        put("usr/local/lib/greia-os/greia-installer-finish",
            (ROOT / "build/installer-overlay/usr/local/lib/greia-os/greia-installer-finish").read_text())
        os.chmod(root / "usr/local/lib/greia-os/greia-installer-finish", 0o755)
        put("etc/systemd/system/greia-installer-finish.path",
            (ROOT / "build/installer-overlay/etc/systemd/system/greia-installer-finish.path").read_text())
        put("etc/systemd/system/greia-installer-finish.service",
            (ROOT / "build/installer-overlay/etc/systemd/system/greia-installer-finish.service").read_text())
        wants = root / "etc/systemd/system/multi-user.target.wants/greia-installer-finish.path"
        wants.parent.mkdir(parents=True, exist_ok=True)
        wants.symlink_to("../../greia-installer-finish.path")
        assets = root / "opt/greia-os/assets"
        for rel in ("boot/frames/frame_0000.png", "boot/frames/frame_0051.png",
                    "audio/system/greia-boot-chime.wav", "catalog/shared_visuals_v1.toml"):
            (assets / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / "assets" / rel, assets / rel)
        shutil.copytree(ROOT / "assets/visual/runtime", assets / "visual/runtime")
        return root

    def verify_live(self, root: Path) -> subprocess.CompletedProcess[str]:
        script = (
            f'set -Eeuo pipefail; source "{ROOT}/build/lib/verify-composed-root.sh"; '
            f'greia_verify_composed_root "{root}" live-installer live "{ROOT}"'
        )
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        env.pop("GREIA_OPERATOR_AUTHORIZED_KEY_FILE", None)
        return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env)

    def test_live_installer_fixture_passes_and_needs_installer_assets(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.make_live_root(raw)
            result = self.verify_live(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            # A crash-restart regression (back to on-failure) is refused.
            unit = root / "etc/systemd/system/greia-installer.service"
            original = unit.read_text(encoding="utf-8")
            unit.write_text(original.replace("Restart=always", "Restart=on-failure"), encoding="utf-8")
            self.assertIn("does not restart after a crash", self.verify_live(root).stderr)
            unit.write_text(original, encoding="utf-8")
            (root / "opt/greia-os/assets/visual/runtime/v1/characters/leo_happy.png").unlink()
            result = self.verify_live(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("catalogue", result.stderr)
        with tempfile.TemporaryDirectory() as raw:
            root = self.make_live_root(raw)
            (root / "opt/greia-os/assets/audio/system/greia-boot-chime.wav").unlink()
            self.assertNotEqual(self.verify_live(root).returncode, 0)

    def test_live_assets_are_staged_by_the_composer(self) -> None:
        compose = (ROOT / "build/lib/compose.sh").read_text(encoding="utf-8")
        body = compose[compose.index("compose_install_live_content() {"):]
        body = body[: body.index("\n}\n")]
        for include in ("/boot/frames/***", "/audio/system/greia-boot-chime.wav",
                        "/catalog/shared_visuals_v1.toml", "/visual/runtime/***"):
            self.assertIn(include, body)
        self.assertIn("alsa-utils", (ROOT / "build/package-sets/installer-base.txt").read_text())

    def test_policy_mismatch_and_diagnostic_grub_fail(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.make_root(raw, policy="diagnostic")
            self.assertNotEqual(self.verify(root).returncode, 0)


class InstallerCompletionPoweroffContractTests(unittest.TestCase):
    """2026-10-18: the completion button must actually switch the machine off.

    The installer UI runs as ``nobody`` with NoNewPrivileges and no logind
    session, so its direct ``systemctl poweroff`` is denied by logind/polkit
    and the button silently did nothing. The repair is a root-owned systemd
    path/service pair triggered by the marker file the UI owns.
    """

    def test_finish_path_unit_watches_the_ui_owned_marker(self) -> None:
        unit = (
            ROOT / "build/installer-overlay/etc/systemd/system/greia-installer-finish.path"
        ).read_text(encoding="utf-8")
        self.assertIn("PathExists=/run/greia-installer/finish-request", unit)
        self.assertIn("Unit=greia-installer-finish.service", unit)
        self.assertIn("WantedBy=multi-user.target", unit)

    def test_finish_service_is_one_root_poweroff_only(self) -> None:
        unit = (
            ROOT / "build/installer-overlay/etc/systemd/system/greia-installer-finish.service"
        ).read_text(encoding="utf-8")
        self.assertIn("Type=oneshot", unit)
        self.assertIn("ExecStart=/usr/local/lib/greia-os/greia-installer-finish", unit)
        self.assertNotIn("reboot", unit)

    def test_finish_helper_powers_off_without_printing_over_the_cover(self) -> None:
        helper = (
            ROOT / "build/installer-overlay/usr/local/lib/greia-os/greia-installer-finish"
        )
        text = helper.read_text(encoding="utf-8")
        self.assertIn("/usr/bin/systemctl poweroff", text)
        self.assertNotIn("reboot", text)
        # systemd-shutdown inherits PID1's log level; lowering it to emergency
        # for the final power-off keeps the Greia cover as the last frame.
        self.assertIn("LogLevel s emerg", text)
        # The 2026-10-18 diagnostic raise printed systemd/kernel text over the
        # branded cover; shutdown must stay silent now that power-off works.
        self.assertNotIn("SetShowStatus", text)
        self.assertNotIn("/proc/sys/kernel/printk", text)
        self.assertTrue(helper.stat().st_mode & 0o111)

    def test_composer_enables_the_finish_path_with_the_installer(self) -> None:
        compose = (ROOT / "build/lib/compose.sh").read_text(encoding="utf-8")
        self.assertIn(
            "systemctl --root=\"$rootfs\" enable greia-installer.service greia-installer-finish.path",
            compose,
        )

    def test_composed_root_verifier_requires_the_finish_contract(self) -> None:
        verifier = (ROOT / "build/lib/verify-composed-root.sh").read_text(encoding="utf-8")
        self.assertIn("PathExists=/run/greia-installer/finish-request", verifier)
        self.assertIn("ExecStart=/usr/local/lib/greia-os/greia-installer-finish", verifier)
        self.assertIn("installer finish helper does not power off", verifier)
        self.assertIn("does not silence the shutdown phase", verifier)
        self.assertIn("reintroduces shutdown console text", verifier)
        self.assertIn("multi-user.target.wants/greia-installer-finish.path", verifier)

    def test_installer_ui_writes_the_marker_instead_of_calling_logind(self) -> None:
        installer = (ROOT / "src/greia_installer/main.py").read_text(encoding="utf-8")
        self.assertIn("POWEROFF_REQUEST_PATH", installer)
        self.assertIn('"poweroff\\n"', installer)
        self.assertNotIn('["systemctl", "poweroff"]', installer)


if __name__ == "__main__":
    unittest.main()
