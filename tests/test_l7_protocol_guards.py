"""L7-PROTOCOLS: permanent architecture guards (source-level, R0/R1).

Each test locks one regression family named by the brief so future work
cannot silently reintroduce it: a second system authority beside the
release bundle, split writer/finalizer copies, the ``allow_mmc`` policy
API, path/index-only authorization, label-only media self-exclusion,
unknown-ARM Pi selection, the GRUB Pi backend, identical A/B UUIDs,
active-slot writer/finalizer entry, single-root update availability, raw
command/path/block fields in Parent/UI protocol, UID-only health
authorization, pre-health persistent defaults, and production private keys
in image/repo fixtures — plus the new semantic socket definitions.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class SingleReleaseAuthorityGuardTests(unittest.TestCase):
    """Single unsigned v3 bundle authority; no signing/key authority."""

    def test_no_signing_verifier_authority(self) -> None:
        source = read("src/greia_platform/system_updates.py")
        self.assertEqual(len(re.findall(r"def verify_update_signature", source)), 0)
        self.assertEqual(len(re.findall(r"def _verify_ed25519", source)), 0)
        self.assertNotIn("SignatureEnvelope", source)
        self.assertNotIn("generate_ed25519_keypair", source)
        self.assertNotIn("SIGNATURE_NAME", source)

    def test_no_trusted_key_dir_authority(self) -> None:
        source = read("src/greia_platform/system_updates.py")
        self.assertNotIn("trusted_key_dir", source)
        self.assertNotIn("trusted_key_dirs", source)
        self.assertNotIn("trusted_key_root", source)

    def test_single_unsigned_bundle_authority(self) -> None:
        source = read("src/greia_platform/system_updates.py")
        self.assertEqual(len(re.findall(r"def build_update_bundle", source)), 1)
        self.assertEqual(
            len(re.findall(r"^def inspect_update_bundle\(", source, re.MULTILINE)), 1
        )
        self.assertIn("SCHEMA_VERSION = 3", source)

    def test_no_signature_bypass_strings(self) -> None:
        for relative in (
            "src/greia_platform/system_updates.py",
            "src/greia_platform/update_privileged.py",
        ):
            with self.subTest(path=relative):
                source = read(relative)
                for marker in (
                    "skip_signature",
                    "skip_verify",
                    "insecure",
                    "verify=False",
                    "no_verify",
                ):
                    self.assertNotIn(marker, source)


class SharedWriterFinalizerGuardTests(unittest.TestCase):
    """One SlotWriter/SlotFinalizer implementation, reused — never copied."""

    def test_single_writer_finalizer_definitions(self) -> None:
        platform_source = read("src/greia_platform/slot_writer.py")
        self.assertEqual(len(re.findall(r"^class SlotWriter", platform_source, re.M)), 1)
        self.assertEqual(
            len(re.findall(r"^class SlotFinalizer", platform_source, re.M)), 1
        )

    def test_installer_reuses_instead_of_copying(self) -> None:
        adapter = read("src/greia_installer/slots.py")
        self.assertNotIn("class SlotWriter", adapter)
        self.assertNotIn("class SlotFinalizer", adapter)
        self.assertIn("from greia_platform.slot_writer import", adapter)


class DiskPolicyGuardTests(unittest.TestCase):
    """Typed disk policy: no allow_mmc switch, no path/index authorization."""

    def test_no_allow_mmc_policy_api(self) -> None:
        source = read("src/greia_installer/disk.py")
        self.assertIsNone(re.search(r"def allow_mmc\b", source))
        self.assertIsNone(re.search(r"allow_mmc\s*[:=]", source))
        self.assertIn("is removed", source)

    def test_authorization_by_identity_digest_only(self) -> None:
        source = read("src/greia_installer/disk.py")
        self.assertIn("identity_digest", source)
        self.assertIn("never a ``/dev`` path", source)

    def test_labels_are_hints_never_authority(self) -> None:
        source = read("src/greia_installer/disk.py")
        self.assertIn("labels are hints, never authority", source)
        self.assertIn("live_media_id", source)

    def test_unknown_arm_pi_selection_and_profile_routing(self) -> None:
        source = read("src/greia_installer/disk.py")
        self.assertIn("class PiBuiltInMicroSdTargetPolicy", source)
        self.assertIn("policy_for_profile_id", source)
        self.assertIn("mmc_host_built_in", source)


class BootBackendGuardTests(unittest.TestCase):
    """GRUB backend covers Pi natively; A/B UUIDs stay distinct."""

    def test_pi_behind_shared_boot_protocol(self) -> None:
        source = read("src/greia_platform/boot_transaction.py")
        self.assertIn("tryboot", source)
        self.assertIn("autoboot", source)

    def test_identical_ab_uuids_rejected(self) -> None:
        source = read("src/greia_platform/slot_writer.py")
        self.assertIn("A/B role filesystem UUIDs must be distinct", source)

    def test_active_slot_writer_entry_refused(self) -> None:
        source = read("src/greia_platform/slot_writer.py")
        self.assertIn("refusing to stage into the active slot", source)

    def test_active_slot_finalizer_entry_refused(self) -> None:
        source = read("src/greia_platform/slot_writer.py")
        self.assertIn("refusing to finalize the active slot", source)


class SingleRootAvailabilityGuardTests(unittest.TestCase):
    """Current single-root backend stays unavailable for staging/arming."""

    def test_unavailable_backend_is_fail_closed(self) -> None:
        from greia_platform.system_updates import UnavailableSystemUpdateBackend

        backend = UnavailableSystemUpdateBackend()
        self.assertFalse(backend.available)
        with self.assertRaises(Exception):
            backend.stage(object())  # type: ignore[arg-type]

    def test_single_root_carries_no_writable_ab_slot(self) -> None:
        source = read("src/greia_platform/slot_writer.py")
        self.assertIn("single-root layouts carry no writable A/B slot", source)


class ParentUiProtocolGuardTests(unittest.TestCase):
    """No raw command/path/block authority in Parent/UI protocol surfaces."""

    PARENT_FILES = (
        "src/greia_parent/production_api.py",
        "src/greia_parent/update_api.py",
        "src/greia_parent/package_api.py",
        "src/greia_parent/api_server.py",
    )

    def test_no_shell_execution_surface(self) -> None:
        for relative in self.PARENT_FILES:
            with self.subTest(path=relative):
                source = read(relative)
                self.assertNotIn("subprocess", source)
                self.assertNotIn("shell=True", source)
                self.assertNotIn("os.system", source)

    def test_no_device_or_boot_arg_fields(self) -> None:
        for relative in self.PARENT_FILES:
            with self.subTest(path=relative):
                source = read(relative)
                self.assertNotIn("device_path", source)
                self.assertNotIn("mountpoint", source)
                self.assertNotIn("boot_arg", source)

    def test_privileged_channel_forbids_raw_keys(self) -> None:
        from greia_platform.privileged_channel import FORBIDDEN_REQUEST_KEYS

        for key in (
            "path",
            "device",
            "command",
            "url",
            "mountpoint",
            "partition",
            "boot_args",
        ):
            self.assertIn(key, FORBIDDEN_REQUEST_KEYS)


class HealthAuthorizationGuardTests(unittest.TestCase):
    """Health authorization binds the peer bootstrap path, never UID alone."""

    def test_platform_checks_peer_bootstrap_path(self) -> None:
        source = read("src/greia_platform/boot_health.py")
        self.assertIn("peer_bootstrap_path", source)

    def test_single_trusted_path_holder(self) -> None:
        source = read("src/greia_launcher/boot_health.py")
        self.assertIn("TRUSTED_BOOTSTRAP_PATH", source)

    def test_no_vault_default_without_systemd_credentials(self) -> None:
        source = read("src/greia_launcher/boot_health.py")
        self.assertIn("LoadCredential=", source)
        self.assertIn("raise BootHealthError", source)

    def test_protocol_requires_explicit_vault_and_observer(self) -> None:
        source = read("src/greia_platform/boot_health.py")
        self.assertIn("vault: BootHealthCredentialVault", source)
        self.assertIn("observer: ActualBootObserver", source)


class PrivateKeyFixtureGuardTests(unittest.TestCase):
    """No production private keys in image overlays, repo or fixtures."""

    def test_no_pem_or_private_key_material(self) -> None:
        offenders = [
            path
            for path in ROOT.rglob("*")
            if ".git/" not in str(path)
            and path.is_file()
            and (
                path.suffix == ".pem"
                or path.name in ("id_rsa", "id_ed25519", "id_ecdsa")
                or "private" in path.name.lower() and path.suffix in (".pem", ".key")
            )
        ]
        self.assertEqual(offenders, [])

    def test_no_private_key_strings_in_overlays(self) -> None:
        for overlay in ("build/overlay", "build/installer-overlay"):
            for path in (ROOT / overlay).rglob("*"):
                if not path.is_file():
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                self.assertNotIn("BEGIN PRIVATE KEY", text, msg=str(path))
                self.assertNotIn("BEGIN RSA PRIVATE KEY", text, msg=str(path))


class SemanticServiceDefinitionGuardTests(unittest.TestCase):
    """Socket-activated semantic services: defined, bounded, never enabled."""

    def test_installer_ops_are_prepare_and_execute_only(self) -> None:
        from greia_installer.install_transaction import INSTALL_TRANSACTION_OPS

        self.assertEqual(tuple(INSTALL_TRANSACTION_OPS), ("PREPARE_PLAN", "EXECUTE", "LIVE_SSH_STATUS", "LIVE_SSH_SET"))

    def test_update_ops_are_semantic_only(self) -> None:
        from greia_platform.update_privileged import UPDATE_PRIVILEGED_OPS

        self.assertEqual(
            tuple(UPDATE_PRIVILEGED_OPS),
            (
                "STATUS",
                "VERIFY_CURRENT_CANDIDATE",
                "STAGE_CURRENT_CANDIDATE",
                "ARM_CURRENT_CANDIDATE",
                "CONFIRM_BOOT_HEALTH",
                "RECONCILE",
                "REQUEST_RESTART",
            ),
        )

    def test_no_manager_daemon_parser_classes_added(self) -> None:
        for relative in (
            "src/greia_platform/privileged_channel.py",
            "src/greia_installer/install_transaction.py",
            "src/greia_platform/update_privileged.py",
        ):
            with self.subTest(path=relative):
                source = read(relative)
                self.assertIsNone(re.search(r"^class \w*Manager\b", source, re.M))
                self.assertIsNone(re.search(r"^class \w*Daemon\b", source, re.M))
                self.assertIsNone(re.search(r"^class \w*Parser\b", source, re.M))

    def test_socket_units_on_demand_without_enable_gate(self) -> None:
        # Activated contract (POSTR1-P3-UPDATE-ACTIVATION): the old
        # enable gate file is removed from the installed-system update
        # pair. Narrow on-demand socket identity/separation is preserved
        # structurally (listener node only, first-connection start, never
        # boot-wanted on the service), with no generic command/daemon
        # surface.
        socket_unit = "build/overlay/etc/systemd/system/greia-system-update.socket"
        service_unit = "build/overlay/etc/systemd/system/greia-system-update.service"
        socket_text = read(socket_unit)
        self.assertIn("ListenStream=/run/greia-os/", socket_text)
        self.assertIn("SocketMode=0660", socket_text)
        self.assertIn("SocketGroup=greiapanel", socket_text)
        self.assertIn("Accept=no", socket_text)
        self.assertNotIn("ConditionPathExists=", socket_text)
        for line in socket_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or not stripped or stripped.startswith("["):
                continue
            self.assertFalse(
                stripped.startswith("Condition"),
                f"activated contract must not gate: {stripped!r}",
            )
        service_text = read(service_unit)
        self.assertNotIn("ConditionPathExists=", service_text)
        for line in service_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or not stripped or stripped.startswith("["):
                continue
            self.assertFalse(
                stripped.startswith("Condition"),
                f"activated contract must not gate: {stripped!r}",
            )
        self.assertNotIn("WantedBy=", service_text)
        self.assertIn("WantedBy=sockets.target", socket_text)
        self.assertIn("User=root", service_text)
        self.assertNotIn("RestrictAddressFamilies=", service_text)
        self.assertIn(
            "ExecStart=/usr/bin/python3 -m greia_platform.update_privileged "
            "--socket-activated",
            service_text,
        )

    def test_installer_socket_active_by_image_scope_not_gate_file(self) -> None:
        # Step 8A.5 split: the installer overlay ships only to installer
        # media, never to the installed system, so the transaction socket is
        # active by image scope. The confinement shape stays identical, and
        # the socket additionally restricts connects to the UI identity.
        socket_text = read(
            "build/installer-overlay/etc/systemd/system/greia-install-transaction.socket"
        )
        self.assertIn("ListenStream=/run/greia-os/", socket_text)
        self.assertIn("SocketMode=0600", socket_text)
        self.assertIn("SocketUser=nobody", socket_text)
        self.assertIn("Accept=no", socket_text)
        self.assertNotIn("ConditionPathExists", socket_text)
        service_text = read(
            "build/installer-overlay/etc/systemd/system/greia-install-transaction.service"
        )
        self.assertNotIn("ConditionPathExists", service_text)
        self.assertNotIn("WantedBy=", service_text)
        self.assertIn("User=root", service_text)
        self.assertNotIn("RestrictAddressFamilies=", service_text)

    def test_no_destructive_backend_wired(self) -> None:
        for relative in (
            "src/greia_installer/install_transaction.py",
            "src/greia_platform/update_privileged.py",
        ):
            with self.subTest(path=relative):
                source = read(relative)
                self.assertNotIn("subprocess", source)
                self.assertNotIn("shell=True", source)
                self.assertNotIn("/dev/", source)


if __name__ == "__main__":
    unittest.main()
