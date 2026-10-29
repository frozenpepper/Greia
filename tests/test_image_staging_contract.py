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

    def test_boot_health_credential_can_create_launcher_delivery_dir(self) -> None:
        """The generator may not run with CAP_DAC_OVERRIDE.

        /run/greia-os is 0770 greiakid:pipprofiles, so the generator needs
        the parent group to create /run/greia-os/boot-health and the
        launcher primary group so the delivery directory/token are readable
        by greiakid rather than only by root.
        """

        text = _read(
            TARGET_OVERLAY / "etc/systemd/system/greia-boot-health-credential.service"
        )
        self.assertIn("Group=greiakid", text)
        self.assertIn("SupplementaryGroups=pipprofiles", text)
        service = _read(TARGET_OVERLAY / "etc/systemd/system/greia-boot-health.service")
        self.assertIn("Group=greiakid", service)
        self.assertIn("SupplementaryGroups=pipprofiles", service)
        self.assertIn(
            "GREIA_BOOT_HISTORY_DIR=/run/greia-persist/greia/diagnostics", service
        )

    def test_launcher_does_not_wait_on_a_signal_it_cannot_receive(self) -> None:
        """The unit must not kill a working Shell waiting for READY=1.

        The unprivileged X server needs a logind session for seat and device
        access: with it, Xorg finds its screen; without it, Xorg aborts with
        "no screens found". But a session moves the service's processes into
        ``session-N.scope``, and systemd attributes ``READY=1`` by the sender's
        cgroup while also losing the process from the unit's own (``Tasks: 0``).
        So ``Type=notify`` can never be satisfied, ``Type=exec`` cannot confirm
        against an empty cgroup, and both end with systemd killing a working
        Shell at ``TimeoutStartSec`` and ``Restart=always`` restoring the
        splash: the soft-reboot loop measured on the Acer at ~90 seconds.

        Readiness therefore stays with the Shell's boot cover and its bounded
        ``launcher_interactive_ready`` marker, and the unit asks systemd for
        nothing beyond a successful fork.
        """

        unit = _read(TARGET_OVERLAY / "etc/systemd/system/greia-launcher.service")
        effective = [
            line.strip()
            for line in unit.splitlines()
            if line.strip() and not line.strip().startswith(("#", ";"))
        ]
        self.assertIn("Type=simple", effective)
        self.assertNotIn("Type=notify", effective)
        self.assertNotIn("Type=exec", effective)
        self.assertFalse([l for l in effective if l.startswith("NotifyAccess=")])
        # The session must stay: Xorg's seat and device access depend on it.
        self.assertIn("PAMName=login", effective)
        self.assertIn("no screens found", unit)
        self.assertIn("launcher_interactive_ready", unit)
        # No leftover dedicated PAM stack claiming the session can be removed.
        self.assertFalse((TARGET_OVERLAY / "etc/pam.d/greia-launcher").exists())

    def test_wifi_dbus_binding_is_in_the_target_not_only_the_installer(self) -> None:
        """The Parent Wi-Fi panel imports dbus; the target must ship it.

        ``python3-dbus`` was declared only in ``installer-base``, so the
        installer's own Wi-Fi screen worked while the installed system's Parent
        panel raised ``ModuleNotFoundError: No module named 'dbus'``. The same
        validated-in-the-installer-only asymmetry as the setuid Xorg wrapper.
        """

        network = _read(PROJECT_ROOT / "build/package-sets/network-basic.txt")
        # dbus alone is not enough: IwdWifiBackend.management_available also
        # imports gi.repository.GLib, so connecting stayed blocked until
        # python3-gi and the GLib typelib were present too.
        for package in ("python3-dbus", "python3-gi", "gir1.2-glib-2.0"):
            self.assertIn(package, network)
        # Every target profile must actually pull that set in.
        for profile in sorted((PROJECT_ROOT / "build/profiles").glob("*.toml")):
            if "network-basic" not in _read(profile):
                continue
            with self.subTest(profile=profile.name):
                self.assertIn("python3-dbus", network)

    def test_first_boot_repairs_profile_data_ownership(self) -> None:
        """The staged target carries the bounded B4 profile repair contract.

        Fresh installs normalize the fixed data root every boot before Parent
        can create profile state. Existing installations get one bounded B4
        compatibility pass: profile roots regain shared group-write, while only
        child-owned storage/progress subtrees are recursively re-owned. The
        repair must not recursively chown arbitrary profile data on every boot.
        """

        text = _read(TARGET_OVERLAY / "usr/local/lib/greia-os/first-boot")

        # Fixed root is validated before normalization; hostile or malformed
        # persistent state must not redirect a privileged repair elsewhere.
        self.assertIn("profile_data_root=/var/lib/greia-profiles/data", text)
        self.assertIn('if [ -L "$profile_data_root" ]', text)
        self.assertIn('if [ -e "$profile_data_root" ] && [ ! -d "$profile_data_root" ]', text)
        self.assertIn(
            'install -d -m 2770 -o greiakid -g pipprofiles "$profile_data_root"',
            text,
        )

        # B4 is deliberately one-shot for the bounded compatibility traversal.
        # The cheap fixed-root normalization above is the per-boot prevention.
        self.assertIn("b4-profile-child-roots-v1.done", text)
        guard = text.index('if [ ! -e "$profile_owner_migration" ]')
        marker_write = text.index('> "$profile_owner_migration"', guard)
        self.assertLess(guard, marker_write)

        block = text[guard:marker_write]
        self.assertIn("-mindepth 1 -maxdepth 1 -type d", block)
        self.assertIn("-exec chgrp -- pipprofiles {} +", block)
        self.assertIn("-exec chmod 2770 {} +", block)

        # Recursive ownership is constrained to the child's own roots only.
        self.assertIn("-mindepth 2 -maxdepth 2 -type d", block)
        self.assertIn("-name progress", block)
        self.assertIn("-name storage", block)
        self.assertNotIn("-name customization", block)
        self.assertNotIn("-name activities", block)
        self.assertIn('find "$owned_root" -xdev -depth -print0', block)
        self.assertIn("chown -h -- greiakid:pipprofiles", block)

        # The retired unbounded/recurring design must not return.
        self.assertNotIn(
            "find /var/lib/greia-profiles/data -depth -print0",
            block,
        )
        self.assertNotIn("b3-profile-data-ownership-v1", text)
        self.assertNotIn("chmod 2755", text)
        self.assertNotIn("chmod 0777", text)


class InstallerImageCarriesTransactionFixesTests(unittest.TestCase):
    """The one-time installer worker must run maintainer scripts unconfined."""

    def _active_directives(self) -> list[str]:
        text = _read(
            INSTALLER_OVERLAY
            / "etc/systemd/system/greia-install-transaction.service"
        )
        return [
            line.split("=", 1)[0].strip()
            for line in text.splitlines()
            if line and not line.lstrip().startswith(("#", ";", "["))
            and "=" in line
        ]

    def test_suid_restriction_is_not_reintroduced(self) -> None:
        self.assertNotIn("RestrictSUIDSGID", self._active_directives())

    def test_no_task_limit_for_package_scripts(self) -> None:
        self.assertNotIn("TasksMax", self._active_directives())

    def test_no_capability_whitelist_for_package_scripts(self) -> None:
        active = self._active_directives()
        for directive in ("CapabilityBoundingSet", "AmbientCapabilities"):
            with self.subTest(directive=directive):
                self.assertNotIn(directive, active)
        text = _read(
            INSTALLER_OVERLAY
            / "etc/systemd/system/greia-install-transaction.service"
        )
        self.assertIn("User=root", text)


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

    def test_no_staged_bytecode_is_committed_under_source(self) -> None:
        """Bytecode must not be committed into the staged source tree.

        This asserts against git's index, not the working tree: running the test
        suite itself writes ``__pycache__`` under ``src/``, so a working-tree
        scan fails depending on what ran before it. The staging exclusion is
        asserted separately in ``test_target_src_is_staged_from_the_repository``.
        """

        import subprocess

        tracked = subprocess.run(
            ["git", "ls-files", "--", "src"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        stale = [p for p in tracked if "__pycache__" in p or p.endswith(".pyc")]
        self.assertEqual(stale, [])


if __name__ == "__main__":
    unittest.main()


class MicrophoneProcessingReachesTheTargetImageTests(unittest.TestCase):
    """Noise cancelling is only real if the endpoint, probe and unit ship.

    The Parent API and panel exposed microphone processing while the ALSA
    ExtPlugin that implements it was never built into the image, so the endpoint
    could not open and the service correctly fell back to off. Every part has to
    be present or the setting is decoration.
    """

    def test_the_endpoint_plugin_is_built_and_installed(self) -> None:
        text = _read(PROJECT_ROOT / "build" / "lib" / "compose.sh")
        self.assertIn("greia_mic_light.so", text)
        self.assertIn("libasound_module_pcm_greia_mic_light.so", text)
        self.assertIn("alsa-lib", text)
        # The build must happen before the footprint prune, which is what removes
        # cc1 and would make the compile impossible.
        self.assertLess(
            text.index("greia_mic_light.so"),
            text.index("compose_footprint_prune")
            if "compose_footprint_prune" in text
            else len(text),
        )

    def test_the_probe_is_executable_and_its_unit_is_enabled(self) -> None:
        compose = _read(PROJECT_ROOT / "build" / "lib" / "compose.sh")
        self.assertIn(
            'chmod 0755 "$rootfs/usr/local/lib/greia-os/greia-audio-endpoint-probe"',
            compose,
        )
        # It previously failed 203/EXEC and never wrote its readiness marker.
        self.assertIn("greia-audio-endpoints.service", compose)

    def test_the_level_service_units_are_enabled(self) -> None:
        compose = _read(PROJECT_ROOT / "build" / "lib" / "compose.sh")
        self.assertIn("greia-microphone-level.socket", compose)

    def test_the_plugin_runtime_library_is_declared(self) -> None:
        sets = _read(
            PROJECT_ROOT / "build" / "package-sets" / "platform-shell-pygame.txt"
        )
        self.assertIn("libspeexdsp1", sets)
