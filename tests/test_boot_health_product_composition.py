"""P4.6 product-composition proof: the shipped BOOT_HEALTHY path (Gate P4).

Supersedes the RED characterization (Post-R1 P1.3 / RC-1): the three
product-boundary predicates are now asserted as SATISFIED against the
composed product. Each test enters through the shipped launcher
path/unit and asserts authority ownership and ordering, never
method-call counts.

Shipped path under test:
  greia_launcher.boot_health.maybe_accept_production_boot (called once
  from LauncherApplication.apply_prepared_state after
  mark_interactive_ready) presenting the root-issued token to the root
  greia-boot-health service/socket; the platform-owned early-boot
  observer (greia-boot-observer.service); the root capability generator
  (greia-boot-health-credential.service); build/build-image.sh.

Fakes/fixtures below are in-module and file only inside disposable
tmpdirs. The kernel boot ID and the launcher UID are fixture-driven.
"""

from __future__ import annotations

import inspect
import json
import os
import socket
import shlex
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

import greia_launcher.boot_health as launcher_health
from greia_launcher.boot_health import TRUSTED_BOOTSTRAP_PATH
from greia_launcher.bootstrap import BootLifecycleGuard
from greia_platform.boot_capability import build_production_verifier
from greia_platform.boot_health import (
    BootHealthError,
    default_capability_authority,
    maybe_issue_boot_capability,
)
from greia_platform.boot_health_service import (
    BootHealthEndpoint,
    BootHealthService,
    handle_boot_health_connection,
)
from greia_platform.boot_observation import observe_and_reconcile_boot
from greia_platform.boot_transaction import (
    BootArtifactSet,
    BootTransactionJournal,
    BootTransactionState,
)
from greia_platform.grub_ab import GrubEnvBackend
from greia_platform.privileged_channel import PeerCredential
from greia_platform.system_updates import load_installed_layout_record


_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_KERNEL_SHA = "ab" * 32
_INITRAMFS_SHA = "cd" * 32
_RELEASE = "greia-0.15.0"
_RELEASE_SEQ = 11
_LAYOUT_ID = "modern-gpt-ab-v1"
_BACKEND_ID = "grub-ab-v1"

_BOOT_ID = "aaaaaaaa-1111-2222-3333-444444444444"
_PEER_UID = 1001


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _shipped_units_dir() -> Path:
    return _repo_root() / "build" / "overlay" / "etc" / "systemd" / "system"


def _parse_service_directives(text: str) -> dict[str, list[str]]:
    """Structured parse of a systemd unit into section/key values."""
    current = ""
    out: dict[str, list[str]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        out.setdefault(f"{current}.{key.strip()}", []).append(value.strip())
    return out


def _read_unit_text(name: str) -> str:
    return (_shipped_units_dir() / name).read_text(encoding="utf-8")


def _interactive_guard() -> BootLifecycleGuard:
    guard = BootLifecycleGuard()
    guard.mark_display_ready()
    guard.mark_first_frame_visible()
    guard.begin_preparing_runtime()
    guard.mark_interactive_ready()
    return guard


def _snapshot_tree(root: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            snapshot[str(path.relative_to(root))] = path.read_bytes()
    return snapshot


class _EnvGuard:
    """Save/restore the narrow production-path env surface."""

    NAMES = (
        "CREDENTIALS_DIRECTORY",
        "GREIA_BOOT_HEALTH_DELIVERY_DIR",
        "GREIA_BOOT_HEALTH_SOCKET_PATH",
        "GREIA_BOOT_HEALTH_AUTHORITY_DIR",
        "GREIA_BOOT_HEALTH_PEER_UID",
        "GREIA_BOOT_HEALTH_PEER_PATH",
        "GREIA_BOOT_ID_PATH",
        "GREIA_UPDATE_STATE_DIR",
        "GREIA_BOOT_JOURNAL_DIR",
        "GREIA_GRUBENV_DIR",
        "GREIA_INSTALLED_LAYOUT_RECORD",
        "GREIA_FINALIZATION_RECEIPT_PATH",
        "GREIA_BOOT_CMDLINE",
        "GREIA_RELEASE_IDENTITY_PATH",
    )

    def __init__(self, values: dict[str, str] | None = None) -> None:
        self.saved: dict[str, str | None] = {}
        self.values = values or {}

    def __enter__(self) -> "_EnvGuard":
        for name in self.NAMES:
            self.saved[name] = os.environ.get(name)
        for name in self.NAMES:
            os.environ.pop(name, None)
        for name, value in self.values.items():
            os.environ[name] = value
        return self

    def __exit__(self, *exc: object) -> bool:
        for name in self.NAMES:
            old = self.saved[name]
            if old is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = old
        return False


def _layout_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "accepted_release_id": _RELEASE,
        "accepted_slot": "A",
        "boot_backend": _BACKEND_ID,
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": "modern-amd64",
        "install_target_sha256": _KERNEL_SHA,
        "installed_at_unix": 1757000000,
        "layout_id": _LAYOUT_ID,
        "persist": {
            "filesystem_uuid": "cccccccc-dddd-eeee-ffff-000000000000",
            "partuuid": "33333333-4444-5555-6666-777777777777",
        },
        "platform_family": "standard-x86-64",
        "schema_version": 1,
        "slot_bytes": 1024 * 1024 * 1024,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }
    base.update(overrides)
    return base


def _identity_dict(*, slot: str) -> dict[str, object]:
    return {
        "boot_backend": _BACKEND_ID,
        "layout_id": _LAYOUT_ID,
        "release_id": _RELEASE,
        "role": f"system-{slot.lower()}",
        "slot": slot,
    }


def _canonical(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _artifact_sets_for_journal(
    journal: BootTransactionJournal,
) -> tuple[BootArtifactSet, BootArtifactSet]:
    candidate = BootArtifactSet(
        slot=journal.candidate_slot,
        layout_id=journal.layout_id,
        boot_backend=journal.boot_backend,
        generic_kernel_sha256=_KERNEL_SHA,
        generic_initramfs_sha256=_INITRAMFS_SHA,
        root_partuuid=_UUID_A if journal.candidate_slot == "A" else _UUID_B,
        root_filesystem_uuid=_UUID_A_FS if journal.candidate_slot == "A" else _UUID_B_FS,
        release_id=journal.release_id,
    )
    return candidate, candidate


class _StubArtifactResolver:
    def resolve(
        self, journal: BootTransactionJournal
    ) -> tuple[BootArtifactSet, BootArtifactSet]:
        return _artifact_sets_for_journal(journal)


# ---------------------------------------------------------------------------
# GREEN composition: the three P1.3 predicates hold on the shipped product
# ---------------------------------------------------------------------------


class BootHealthProductCompositionTests(unittest.TestCase):
    def test_1_platform_provisioned_capability_reaches_launcher(self) -> None:
        """GREEN: a one-use BOOT_HEALTHY capability reaches the launcher."""
        # Structural: the shipped launcher unit carries the capability
        # read-only (never writable), pulled after the root generator.
        service_text = _read_unit_text("greia-launcher.service")
        directives = _parse_service_directives(service_text)
        binds = directives.get("Service.BindReadOnlyPaths", [])
        self.assertIn("-/run/greia-os/boot-health", binds)
        self.assertIn(
            "greia-boot-health-credential.service",
            directives.get("Unit.After", [""])[0],
        )
        self.assertIn(
            "greia-boot-health-credential.service",
            directives.get("Unit.Wants", [""])[0],
        )
        generator_text = _read_unit_text("greia-boot-health-credential.service")
        generator = _parse_service_directives(generator_text)
        self.assertIn("greia-launcher.service", generator.get("Unit.Before", []))
        # Structural: the launcher loader is read-only by construction.
        loader_source = inspect.getsource(launcher_health.maybe_load_production_token)
        self.assertIn("O_RDONLY", loader_source)
        for forbidden in (
            "authority_dir",
            "issue_for_pending",
            "verify_and_consume",
            "atomic_write",
            "os.replace",
            "default_vault",
        ):
            self.assertNotIn(forbidden, loader_source)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir = root / "boot-journal"
            journal_dir.mkdir(parents=True)
            state_dir = root / "update-state"
            state_dir.mkdir(parents=True)
            BootTransactionJournal.begin_first_install(
                journal_dir,
                layout_id=_LAYOUT_ID,
                boot_backend=_BACKEND_ID,
                release_id=_RELEASE,
            )
            journal = BootTransactionJournal.load(journal_dir)
            # Root side: the production generator issues the one-use token
            # for the real pending transaction.
            owner = default_capability_authority(
                authority_dir=root / "authority",
                delivery_dir=root / "delivery",
            )
            issued = maybe_issue_boot_capability(
                authority=owner,
                boot_journal_dir=journal_dir,
                update_state_dir=state_dir,
                boot_id=_BOOT_ID,
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                peer_uid=_PEER_UID,
            )
            assert issued is not None
            self.assertTrue(owner.capability_live())
            with _EnvGuard(
                {"GREIA_BOOT_HEALTH_DELIVERY_DIR": str(root / "delivery")}
            ):
                # Launcher side: the unprivileged loader reads the token.
                loaded = launcher_health.maybe_load_production_token()
                self.assertEqual(loaded, issued.token)
                # The shipped production verifier consumes it exactly once
                # for the pending transaction; a replay fails closed.
                verifier = build_production_verifier(
                    authority=owner,
                    boot_journal_dir=journal_dir,
                    update_state_dir=state_dir,
                    boot_id=_BOOT_ID,
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                )
                record = verifier.verify_and_consume(token=loaded)
                self.assertEqual(record["transaction_id"], journal.transaction_id)
                self.assertFalse(owner.capability_live())
                with self.assertRaises(BootHealthError):
                    verifier.verify_and_consume(token=loaded)

    def test_2_platform_observer_records_last_booted_before_launcher(self) -> None:
        """GREEN: early-boot observation owns last_booted before acceptance."""
        # Structural: the observer unit precedes the launcher when an A/B
        # profile enables it; the launcher never Requires it (a refused boot
        # fact fails loudly without authorizing boot).
        observer_text = _read_unit_text("greia-boot-observer.service")
        observer = _parse_service_directives(observer_text)
        self.assertIn("greia-launcher.service", observer.get("Unit.Before", []))
        self.assertEqual(observer.get("Service.Type"), ["oneshot"])
        self.assertTrue(
            any(
                "greia_platform.boot_observation" in value
                for value in observer.get("Service.ExecStart", [])
            )
        )
        launcher_text = _read_unit_text("greia-launcher.service")
        launcher = _parse_service_directives(launcher_text)
        requires = " ".join(launcher.get("Unit.Requires", []))
        self.assertNotIn("greia-boot-observer", requires)
        # T01: service composition lives in the shared engine, consumed for
        # role `target` by the thin build-image.sh wrapper.
        build_text = (_repo_root() / "build" / "lib" / "compose.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'if [[ "$STORAGE_LAYOUT_ADAPTER" == *-ab-v1 ]]',
            build_text,
        )
        self.assertIn(
            "target_services+=(greia-boot-observer.service)",
            build_text,
        )
        self.assertIn(
            "target_services+=(greia-candidate-recovery.timer)",
            build_text,
        )

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cmdline = root / "cmdline"
            cmdline.write_text(
                f"BOOT_IMAGE=/boot/vmlinuz root=PARTUUID={_UUID_B} ro quiet\n",
                encoding="utf-8",
            )
            layout = root / "installed-layout.json"
            layout.write_bytes(_canonical(_layout_dict()))
            identity = root / "release-identity.json"
            identity.write_bytes(_canonical(_identity_dict(slot="B")))
            grubenv_dir = root / "boot-control"
            backend = GrubEnvBackend.initialize(grubenv_dir, default_slot="A")
            backend.arm_one_shot("B")
            # Production entry: kernel root B reconciles into last_booted B
            # with the persistent default untouched — before any launcher
            # acceptance runs.
            result = observe_and_reconcile_boot(
                cmdline_path=cmdline,
                layout_record_path=layout,
                release_identity_path=identity,
                grubenv_dir=grubenv_dir,
            )
            self.assertTrue(result.reconciled)
            self.assertEqual(result.observed_slot, "B")
            state = GrubEnvBackend.attach(grubenv_dir).inspect()
            self.assertEqual(state.last_booted_slot, "B")
            self.assertEqual(state.default_slot, "A")

    def test_2b_boot_observer_enablement_follows_storage_layout(self) -> None:
        compose = _repo_root() / "build" / "lib" / "compose.sh"

        def enabled_services(layout: str) -> str:
            with tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                probe = root / "usr/local/lib/greia-os/greia-audio-endpoint-probe"
                probe.parent.mkdir(parents=True)
                probe.write_text("#!/bin/sh\n", encoding="utf-8")
                bootstrap = probe.with_name("software-update-bootstrap.py")
                bootstrap.write_text("#!/usr/bin/python3\n", encoding="utf-8")
                bootstrap.chmod(0o755)
                script = f"""
set -Eeuo pipefail
source {shlex.quote(str(compose))}
systemctl() {{
  printf 'SYSTEMCTL %s\\n' "$*"
}}
chown() {{
  :
}}
STORAGE_LAYOUT_ADAPTER={layout}
compose_configure_systemd {shlex.quote(str(root))} target
"""
                result = subprocess.run(
                    ["bash", "-c", script],
                    cwd=_repo_root(),
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(0, result.returncode, result.stderr)
                return result.stdout

        single_root = enabled_services("bios-single-ext4")
        self.assertNotIn("greia-boot-observer.service", single_root)
        self.assertIn("greia-launcher.service", single_root)

        ab = enabled_services("legacy-bios-ab-v1")
        self.assertIn("greia-boot-observer.service", ab)
        self.assertIn("greia-launcher.service", ab)
    def test_3_root_service_owns_mutation_launcher_writes_nothing(self) -> None:
        """GREEN: CONFIRM_BOOT_HEALTH commits; the launcher writes nothing."""
        # Structural: the launcher is unprivileged; the health endpoint is
        # root-owned AF_UNIX on demand; the image enables the socket, never
        # the service.
        launcher_text = _read_unit_text("greia-launcher.service")
        launcher = _parse_service_directives(launcher_text)
        self.assertEqual(launcher.get("Service.User"), ["greiakid"])
        service_text = _read_unit_text("greia-boot-health.service")
        service = _parse_service_directives(service_text)
        self.assertEqual(service.get("Service.User"), ["root"])
        self.assertEqual(service.get("Service.RestrictAddressFamilies"), ["AF_UNIX"])
        self.assertEqual(
            set(" ".join(service.get("Unit.Requires", [])).split()),
            {"greia-boot-health.socket", "greia-software-update-recover.service"},
        )
        self.assertNotIn("Install.WantedBy", service)
        socket_text = _read_unit_text("greia-boot-health.socket")
        sock = _parse_service_directives(socket_text)
        self.assertEqual(
            sock.get("Socket.ListenStream"), ["/run/greia-os/boot-health.sock"]
        )
        build_text = (_repo_root() / "build" / "lib" / "compose.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("greia-boot-health.socket", build_text)
        for line in build_text.splitlines():
            if line.strip().startswith("#"):
                continue
            self.assertNotIn("greia-boot-health.service", line)
        # Structural: the shipped launcher production path performs no
        # privileged boot-state write and provisions no capability. (The
        # legacy in-process protocol helpers stay for their established
        # protocol-path tests; the production seam below never touches
        # them.) The production surface is exactly: read-only token load,
        # one socket transaction, outcome mapping.
        production_source = "\n".join(
            inspect.getsource(function)
            for function in (
                launcher_health.maybe_accept_production_boot,
                launcher_health._transact_with_health_service,
                launcher_health._outcome_from_service_detail,
                launcher_health.maybe_load_production_token,
            )
        )
        for forbidden in (
            "GrubEnvBackend.attach",
            "coordinator.observe_boot",
            "_advance_update_layout_authority",
            "_accept_pending_journal",
            "provision_for_boot_attempt",
            "default_vault",
        ):
            self.assertNotIn(forbidden, production_source)
        seam_source = inspect.getsource(launcher_health.maybe_accept_production_boot)
        self.assertIn("maybe_load_production_token", seam_source)
        self.assertIn("CONFIRM_BOOT_HEALTH", seam_source)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            boot_journal_dir = root / "boot-journal"
            state_dir = root / "update-state"
            history_dir = root / "history"
            grubenv_dir = root / "grubenv"
            for directory in (boot_journal_dir, state_dir, history_dir, grubenv_dir):
                directory.mkdir(parents=True, exist_ok=True)
            layout_path = root / "installed-layout.json"
            layout_path.write_bytes(_canonical(_layout_dict()))
            backend = GrubEnvBackend.initialize(grubenv_dir, default_slot="A")
            BootTransactionJournal.begin_first_install(
                boot_journal_dir,
                layout_id=_LAYOUT_ID,
                boot_backend=_BACKEND_ID,
                release_id=_RELEASE,
            )
            backend.simulate_reboot()
            assert backend.observe_booted_slot() == "A"
            # Root side: issue the one-use capability for the pending boot.
            owner = default_capability_authority(
                authority_dir=root / "authority",
                delivery_dir=root / "delivery",
            )
            issued = maybe_issue_boot_capability(
                authority=owner,
                boot_journal_dir=boot_journal_dir,
                update_state_dir=state_dir,
                boot_id=_BOOT_ID,
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                peer_uid=_PEER_UID,
            )
            assert issued is not None
            # Root side: the live health service behind a real AF_UNIX
            # socket, consuming through the shipped production verifier.
            verifier = build_production_verifier(
                authority=owner,
                boot_journal_dir=boot_journal_dir,
                update_state_dir=state_dir,
                boot_id=_BOOT_ID,
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
            )
            class _StubUpdateAuthority:
                backend = SimpleNamespace(layout_record_path=layout_path)

                @staticmethod
                def confirm_boot_health() -> dict[str, object]:
                    raise AssertionError("first-install never delegates")

            stub_authority = _StubUpdateAuthority()
            health_service = BootHealthService(
                boot_journal_dir=boot_journal_dir,
                update_state_dir=state_dir,
                history_dir=history_dir,
                update_authority=stub_authority,
                capability_verifier=verifier,
                artifact_resolver=_StubArtifactResolver(),
                boot_backend_factory=lambda: GrubEnvBackend.attach(grubenv_dir),
            )
            endpoint = BootHealthEndpoint(
                health_service, allowed_uids=(0, os.getuid())
            )
            socket_path = root / "boot-health.sock"
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            listener.bind(os.fspath(socket_path))
            listener.listen(1)

            def _serve_once() -> None:
                connection, _ = listener.accept()
                try:
                    handle_boot_health_connection(
                        connection,
                        endpoint=endpoint,
                        peer=PeerCredential(uid=os.getuid()),
                        boot_state="interactive_ready",
                    )
                finally:
                    listener.close()

            server = threading.Thread(target=_serve_once, daemon=True)
            server.start()
            # Launcher side: only the delivery bind and the socket path —
            # no journal, grubenv, layout or receipt paths are resolved.
            with _EnvGuard(
                {
                    "GREIA_BOOT_HEALTH_DELIVERY_DIR": str(root / "delivery"),
                    "GREIA_BOOT_HEALTH_SOCKET_PATH": os.fspath(socket_path),
                }
            ):
                outcome = launcher_health.maybe_accept_production_boot(
                    _interactive_guard()
                )
            server.join(timeout=10)
            self.assertFalse(server.is_alive())
            # The real outcome returns; the root endpoint committed all
            # five through the production mechanism.
            self.assertIsNotNone(outcome)
            assert outcome is not None
            self.assertEqual(outcome.accepted_slot, "A")
            self.assertTrue(outcome.first_install)
            self.assertEqual(outcome.recovery_medium_if_failed, "setup-medium")
            journal = BootTransactionJournal.load(boot_journal_dir)
            self.assertEqual(journal.state, BootTransactionState.ACCEPTED)
            self.assertTrue(journal.is_terminal)
            self.assertEqual(
                GrubEnvBackend.attach(grubenv_dir).inspect().default_slot, "A"
            )
            self.assertEqual(journal.release_id, _RELEASE)
            record = load_installed_layout_record(layout_path)
            assert record is not None
            self.assertEqual(record.accepted_release_id, _RELEASE)
            # One-use end to end: the consumed token is gone, so a second
            # launcher presentation is a bounded no-op, never a second
            # commit.
            with _EnvGuard(
                {
                    "GREIA_BOOT_HEALTH_DELIVERY_DIR": str(root / "delivery"),
                    "GREIA_BOOT_HEALTH_SOCKET_PATH": os.fspath(socket_path),
                }
            ):
                self.assertIsNone(
                    launcher_health.maybe_accept_production_boot(_interactive_guard())
                )


if __name__ == "__main__":
    unittest.main()
