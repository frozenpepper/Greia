"""POSTR1-P3-UPDATE-ACTIVATION-RECONCILE contract: activation + canonical wiring.

Merge of the reviewed P3.4 update-activation delta
(``POSTR1-P3-UPDATE-ACTIVATION``) with the integrated canonical pre-intro
timing instrument (``POSTR1-P3-PREINTRO-TIMING-INSTRUMENT``):

- The exact installed update socket/service is the normal on-demand product
  contract (no absent-marker gate), stays off the pre-intro critical path,
  and a normal boot with no update candidate performs no block-device work.
  The service keeps exactly the six semantic operations (no generic
  Parent->root command surface) and the seven-second intro is unchanged.
- The timing instrument consumes the single-owner production marker shape
  ``GREIA_BOOT event=<name> monotonic_ns=<int>`` (emitted only via
  ``src/greia_platform/boot_markers.py::emit_boot_marker``), with the
  canonical ``launcher_interactive_ready`` interactive-ready default — never
  the stale ``event=interactive_ready`` wording no producer emits.

Structured assertions (configparser + targeted reads + the real shipped
composition path + the real shipped parser/instrument), never full-file
snapshots.
"""

from __future__ import annotations

import ast
import configparser
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import replace
from pathlib import Path

from support_artifacts import valid_hardware_support_archive_bytes
from unittest import mock

from greia_platform.slot_writer import HardwareInventoryAttestation

ROOT = Path(__file__).resolve().parents[1]
UNIT_DIR = ROOT / "build/overlay/etc/systemd/system"
SERVICE_PATH = UNIT_DIR / "greia-system-update.service"
SOCKET_PATH = UNIT_DIR / "greia-system-update.socket"
BOOT_INTRO_PATH = ROOT / "src/greia_launcher/boot_intro.py"
PREINTRO_PATH = ROOT / "tools/x8_qemu/preintro_timing.py"
ANALYZE_PATH = ROOT / "tools/boot/analyze_boot_markers.py"
LAUNCHER_MAIN_PATH = ROOT / "src/greia_launcher/main.py"

_ABSENT_GATE = "/run/greia-os/enable-privileged-transactions"

_EXPECTED_OPS = (
    "STATUS",
    "VERIFY_CURRENT_CANDIDATE",
    "STAGE_CURRENT_CANDIDATE",
    "ARM_CURRENT_CANDIDATE",
    "CONFIRM_BOOT_HEALTH",
    "RECONCILE",
)

# Units that own the pre-intro first-frame path. None of them may pull the
# update socket/service (Requires/Wants), and the update pair may not order
# itself before them (Before=).
_PRE_INTRO_UNITS = (
    "greia-first-boot.service",
    "greia-launcher.service",
    "greia-intro-sweep.service",
    "greia-candidate-recovery.service",
    "greia-candidate-recovery.timer",
)

_FAMILY = "legacy-x86"
_ARCH = "i386"
_PROFILE = "legacy-x86-i686"

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"


@contextmanager
def _patched_env(**overrides: str):
    previous = dict(os.environ)
    os.environ.update(overrides)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(previous)


def _parse_unit(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    parser.optionxform = str  # type: ignore[assignment]
    parser.read(path, encoding="utf-8")
    return parser


def _directive_values(path: Path, name: str) -> set[str]:
    """Collect every value of a (possibly repeated) unit directive."""
    values: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith(name + "="):
            values.update(stripped.split("=", 1)[1].split())
    return values


def _record_dict() -> dict[str, object]:
    return {
        "accepted_release_id": "greia-0.16.0",
        "accepted_slot": "A",
        "boot_backend": "grub-ab-v1",
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": _PROFILE,
        "install_target_sha256": "ab" * 32,
        "installed_at_unix": 1757000000,
        "layout_id": "legacy-bios-ab-v1",
        "persist": {"filesystem_uuid": _UUID_P_FS, "partuuid": _UUID_P},
        "platform_family": _FAMILY,
        "schema_version": 1,
        "slot_bytes": 1073741824,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }


def _payload(size: int, tag: bytes) -> bytes:
    body = bytes((index * 31 + 7) % 256 for index in range(size))
    raw = tag + body[len(tag):]
    fixed = bytearray(raw)
    if fixed[510:512] == b"\x55\xaa":
        fixed[510:512] = b"\x00\x00"
    if fixed[512:520] == b"EFI PART":
        fixed[512:520] = b"\x00" * 8
    return bytes(fixed)


def _directive_lines(path: Path) -> list[str]:
    """Non-comment, non-section unit directive lines (directive matching)."""
    lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("["):
            continue
        lines.append(stripped)
    return lines


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _emitted_boot_events(path: Path) -> list[str]:
    """Event names passed to ``emit_boot_marker("...")`` in a source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and getattr(node.func, "id", "") == "emit_boot_marker"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            found.append(str(node.args[0].value))
    return found


class ActivationDeclarationTests(unittest.TestCase):
    def test_absent_marker_gate_removed(self) -> None:
        for path in (SERVICE_PATH, SOCKET_PATH):
            directives = _directive_lines(path)
            self.assertEqual(
                [line for line in directives if line.startswith("Condition")],
                [],
                msg=path.name,
            )
            self.assertEqual(
                [line for line in directives if _ABSENT_GATE in line],
                [],
                msg=path.name,
            )

    def test_socket_is_narrow_on_demand_listener(self) -> None:
        parser = _parse_unit(SOCKET_PATH)
        self.assertEqual(
            parser.get("Socket", "ListenStream").strip(),
            "/run/greia-os/system-update.sock",
        )
        self.assertEqual(parser.get("Socket", "Accept").strip(), "no")
        self.assertEqual(parser.get("Socket", "SocketMode").strip(), "0600")
        self.assertEqual(parser.get("Socket", "SocketUser").strip(), "root")
        # Narrow activation: wanted only by sockets.target, nothing else.
        self.assertEqual(
            _directive_values(SOCKET_PATH, "WantedBy"), {"sockets.target"}
        )
        self.assertEqual(
            _directive_values(SOCKET_PATH, "After"), {"local-fs.target"}
        )

    def test_service_starts_only_via_socket(self) -> None:
        parser = _parse_unit(SERVICE_PATH)
        self.assertIn("greia-system-update.socket", parser.get("Unit", "Requires"))
        self.assertIn("greia-system-update.socket", parser.get("Unit", "After"))
        self.assertEqual(
            _directive_values(SERVICE_PATH, "After"), {"greia-system-update.socket"}
        )
        # The service is never wanted directly: no [Install] section at all.
        self.assertNotIn("Install", parser.sections())
        self.assertNotIn("WantedBy=", SERVICE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(parser.get("Service", "Type").strip(), "simple")
        # Native fd-store activation (POSTR1-P5): the entry consumes
        # LISTEN_FDS + fd 3, so the unit must NOT select inetd-style
        # stdin passing (StandardInput=socket leaves LISTEN_FDS unset
        # and the entry exits fail-closed). Standard input stays
        # disconnected (absent or null).
        stdin_value = (
            parser.get("Service", "StandardInput").strip()
            if parser.has_option("Service", "StandardInput")
            else None
        )
        self.assertIn(
            stdin_value,
            (None, "null"),
            msg="service must activate through the native fd store; "
            "StandardInput=socket breaks activation",
        )
        self.assertEqual(
            parser.get("Service", "ExecStart").strip(),
            "/usr/bin/python3 -m greia_platform.system_updates --socket-activated",
        )


class PreIntroOrderingTests(unittest.TestCase):
    def test_update_pair_orders_nothing_before_first_frame(self) -> None:
        for path in (SERVICE_PATH, SOCKET_PATH):
            directives = _directive_lines(path)
            self.assertEqual(
                [line for line in directives if line.startswith("Before=")],
                [],
                msg=path.name,
            )
            for unit in ("greia-launcher", "greia-first-boot", "greia-parent",
                         "greia-intro-sweep", "greia-candidate-recovery",
                         "graphical.target", "multi-user.target"):
                self.assertEqual(
                    [line for line in directives if unit in line],
                    [],
                    msg=f"{path.name}:{unit}",
                )

    def test_no_shipped_unit_pulls_update_onto_boot(self) -> None:
        for unit_file in sorted(UNIT_DIR.iterdir()):
            if not unit_file.is_file():
                continue
            if unit_file.suffix not in (".service", ".socket", ".timer"):
                continue
            if unit_file.name in (
                "greia-system-update.service",
                "greia-system-update.socket",
            ):
                continue
            raw = unit_file.read_text(encoding="utf-8")
            self.assertNotIn(
                "greia-system-update", raw, msg=unit_file.name
            )

    def test_pre_intro_chain_untouched_by_update(self) -> None:
        for name in _PRE_INTRO_UNITS:
            raw = (UNIT_DIR / name).read_text(encoding="utf-8")
            self.assertNotIn("system-update", raw, msg=name)
            self.assertNotIn("SystemUpdate", raw, msg=name)

    def test_seven_second_intro_fixed(self) -> None:
        # The intro is fixed at 5 s animation + 2 s final hold and must not
        # be shortened to improve the pre-intro metric.
        tree = ast.parse(BOOT_INTRO_PATH.read_text(encoding="utf-8"))
        values = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and isinstance(
                    node.value, ast.Constant
                ):
                    values[target.id] = node.value.value
        self.assertEqual(values.get("ANIMATION_SECONDS"), 5.0)
        self.assertEqual(values.get("FINAL_FRAME_HOLD_SECONDS"), 2.0)
        total = values["ANIMATION_SECONDS"] + values["FINAL_FRAME_HOLD_SECONDS"]
        self.assertEqual(total, 7.0)


class CandidateAbsentNoOpTests(unittest.TestCase):
    def _compose(self, root: Path):
        from greia_platform.system_updates import build_live_update_service

        state_dir = root / "state"
        layout_path = root / "installed-layout.json"
        layout_path.write_bytes(
            (json.dumps(_record_dict(), sort_keys=True, separators=(",", ":"))
             + "\n").encode()
        )
        with _patched_env(
            GREIA_SYSTEM_VERSION="0.16.0",
            GREIA_SYSTEM_PLATFORM_FAMILY=_FAMILY,
            GREIA_SYSTEM_ARCHITECTURE=_ARCH,
            GREIA_SYSTEM_PROFILE=_PROFILE,
        ):
            return build_live_update_service(
                state_dir=state_dir,
                layout_record_path=layout_path,
                boot_backend_auto=False,
            )

    def test_empty_inbox_status_touches_no_destination_seam(self) -> None:
        from greia_platform.system_updates import UpdateSlotSeams
        from greia_platform.update_privileged import (
            UpdatePrivilegedEndpoint,
            build_request,
            read_response,
        )
        from greia_platform.privileged_channel import PeerCredential

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = self._compose(root)
            # The shipped main() path binds production seams, never an
            # injected test double.
            self.assertIsInstance(authority.backend.seams, UpdateSlotSeams)
            demanded: list[str] = []
            original_require = authority.backend._require_seam  # type: ignore[attr-defined]

            def _spying_require(name: str, factory):  # type: ignore[no-untyped-def]
                demanded.append(name)
                return original_require(name, factory)

            state_before = sorted(
                str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()
            )
            layout_before = (root / "installed-layout.json").read_bytes()
            try:
                authority.backend._require_seam = _spying_require  # type: ignore[method-assign]
                # Direct authority path: no candidate present.
                summary = authority.candidate_summary()
                self.assertFalse(summary.present)
                layout = authority.layout_summary()
                self.assertEqual(layout["slots"], ["A", "B"])
                # Real protocol path: STATUS through the production endpoint
                # (root peer, interactive boot state) answers absent. The
                # endpoint renders the legacy summary shape, so the v3
                # authority is adapted at the socket boundary (T04 notes).
                from greia_platform.update_privileged import CurrentCandidateSummary

                _real_authority = authority

                class _SocketAuthority:
                    def candidate_summary(self) -> CurrentCandidateSummary:
                        summary = _real_authority.candidate_summary()
                        return CurrentCandidateSummary(
                            present=summary.present,
                            release_id=summary.release_id,
                            bundle_sha256=summary.bundle_sha256,
                        )

                    def layout_summary(self) -> dict[str, object]:
                        return dict(_real_authority.layout_summary())

                endpoint = UpdatePrivilegedEndpoint(_SocketAuthority())  # type: ignore[arg-type]
                raw = endpoint.handle_request(
                    build_request("STATUS"),
                    peer=PeerCredential(uid=0),
                    boot_state="update_ready",
                )
                _transaction_id, op, payload = read_response(raw)
                self.assertEqual(op, "STATUS")
                self.assertFalse(payload["candidate"]["present"])
            finally:
                authority.backend._require_seam = original_require  # type: ignore[method-assign]
            # No destination-seam demand means no block-device work; no
            # state side effects and the layout record is untouched.
            self.assertEqual(demanded, [])
            state_after = sorted(
                str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()
            )
            self.assertEqual(state_after, state_before)
            self.assertEqual(
                (root / "installed-layout.json").read_bytes(), layout_before
            )

    def test_candidate_present_but_no_device_still_fails_closed(self) -> None:
        # Sensitivity control: the spy above is live — with an unsigned v3
        # candidate present but no inactive device resolvable, the same
        # shipped composition demands a destination seam and then refuses
        # fail-closed with no journal write and no slot artifacts.
        import zstandard

        from greia_platform.system_updates import (
            SystemUpdateInbox,
            UpdateBackendUnavailable,
            build_update_bundle,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = self._compose(root)
            state_dir = root / "state"
            layout_path = root / "installed-layout.json"
            work = root / "releases" / "r9"
            work.mkdir(parents=True, exist_ok=True)
            raw = _payload(220 * 1024, b"postr1-p34:")
            (work / "slot.ext4.zst").write_bytes(
                zstandard.ZstdCompressor(level=3).compress(raw)
            )
            (work / "hw.tar.zst").write_bytes(
                valid_hardware_support_archive_bytes(architecture=_ARCH)
            )
            bundle = work / "r9.greiaupdate"
            build_update_bundle(
                payload_path=work / "slot.ext4.zst",
                hardware_support_path=work / "hw.tar.zst",
                output_path=bundle,
                version="0.17.0",
                release_id="greia-0.17.0",
                platform_family=_FAMILY,
                architecture=_ARCH,
                profile=_PROFILE,
                payload_uncompressed_bytes=len(raw),
                minimum_slot_bytes=len(raw),
                persist_read_schema_min=1,
                persist_read_schema_max=1,
                persist_write_schema=1,
                release_notes="POSTR1-P3-UPDATE-ACTIVATION sensitivity control.",
            )
            SystemUpdateInbox(state_dir).receive(bundle)
            # Isolate the predicate named by this test: provide a complete
            # inventory attestation, but keep the shipped production
            # filesystem/device resolver. The fake PARTUUIDs have no backing
            # device, so staging must fail at that destination seam.
            authority.backend.seams = replace(
                authority.backend.seams,
                inventory_factory=lambda: HardwareInventoryAttestation(
                    token="cd" * 32
                ),
            )
            demanded: list[str] = []
            original_require = authority.backend._require_seam  # type: ignore[attr-defined]

            def _spying_require(name: str, factory):  # type: ignore[no-untyped-def]
                demanded.append(name)
                return original_require(name, factory)

            layout_before = layout_path.read_bytes()
            try:
                authority.backend._require_seam = _spying_require  # type: ignore[method-assign]
                with _patched_env(
                    GREIA_SYSTEM_VERSION="0.16.0",
                    GREIA_SYSTEM_PLATFORM_FAMILY=_FAMILY,
                    GREIA_SYSTEM_ARCHITECTURE=_ARCH,
                    GREIA_SYSTEM_PROFILE=_PROFILE,
                ):
                    verified = authority.verify_current_candidate()
                    self.assertTrue(verified.present)
                    self.assertEqual(verified.release_id, "greia-0.17.0")
                    with self.assertRaises(UpdateBackendUnavailable) as raised:
                        authority.stage_current_candidate()
            finally:
                authority.backend._require_seam = original_require  # type: ignore[method-assign]
            message = str(raised.exception)
            # Support + PERSIST + inventory prerequisites are valid. The
            # shipped production resolver must now reach the inactive-slot
            # filesystem seam and refuse because the layout's PARTUUID has no
            # backing device. This proves the intended no-device predicate.
            self.assertIn("inactive-slot filesystem is unavailable", message)
            self.assertEqual(
                demanded,
                [
                    "release support set",
                    "installed PERSIST schema",
                    "hardware inventory attestation",
                    "slot filesystem",
                ],
            )
            journal_file = (
                state_dir / "system-updates" / "journal" / "boot-journal.json"
            )
            self.assertFalse(journal_file.exists())
            self.assertEqual(layout_path.read_bytes(), layout_before)
            # No slot-image or loop-store artifacts under the update state.
            leftovers = [
                str(p.relative_to(state_dir))
                for p in state_dir.rglob("*")
                if p.is_file() and ("slot-" in p.name or p.suffix == ".img")
            ]
            self.assertEqual(leftovers, [])


class NoGenericCommandSurfaceTests(unittest.TestCase):
    def test_exactly_six_semantic_operations(self) -> None:
        from greia_platform.update_privileged import UPDATE_PRIVILEGED_OPS

        self.assertEqual(tuple(UPDATE_PRIVILEGED_OPS), _EXPECTED_OPS)

    def test_endpoint_rejects_unknown_ops_and_selectors(self) -> None:
        from greia_platform.privileged_channel import (
            PeerCredential,
            PrivilegedChannelError,
            encode_request,
        )
        from greia_platform.update_privileged import (
            UpdatePrivilegedEndpoint,
            UpdatePrivilegedError,
            build_request,
        )

        authority = mock.Mock()
        endpoint = UpdatePrivilegedEndpoint(authority)
        peer = PeerCredential(uid=0)
        for op in ("REBOOT", "RUN_COMMAND", "EXEC", "STATUS_EXTRA"):
            with self.assertRaises(UpdatePrivilegedError, msg=op):
                endpoint.handle_request(
                    encode_request(op, {}),
                    peer=peer,
                    boot_state="update_ready",
                )
        with self.assertRaises(UpdatePrivilegedError):
            build_request("RUN_COMMAND")
        with self.assertRaises(UpdatePrivilegedError):
            build_request("")
        # Semantic-only: non-empty params are rejected even for known ops.
        # Client-side encoding already refuses raw-authority shapes; the
        # endpoint independently refuses any non-empty selector set, so
        # build a raw frame that bypasses the client-side builder.
        client_refused = encode_request("STATUS", {})
        document = json.loads(client_refused.decode("utf-8"))
        document["params"] = {"slot": "B"}
        raw_selectors = (
            json.dumps(document, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
        with self.assertRaises(UpdatePrivilegedError):
            endpoint.handle_request(
                raw_selectors,
                peer=peer,
                boot_state="update_ready",
            )
        with self.assertRaises(PrivilegedChannelError):
            encode_request("STATUS", {"command": "/bin/true"})
        # Ordinary pre-intro boot stays inactive even for the root peer.
        with self.assertRaises(UpdatePrivilegedError):
            endpoint.handle_request(
                build_request("STATUS"), peer=peer, boot_state="pre_intro"
            )
        with self.assertRaises((UpdatePrivilegedError, PrivilegedChannelError)):
            endpoint.handle_request(
                build_request("STATUS"),
                peer=PeerCredential(uid=1000),
                boot_state="update_ready",
            )

    def test_units_carry_no_generic_exec_surface(self) -> None:
        for path in (SERVICE_PATH, SOCKET_PATH):
            raw = path.read_text(encoding="utf-8")
            self.assertNotIn("/bin/sh", raw)
            self.assertNotIn("shell", raw.lower())
            self.assertNotIn("Command=", raw)
        service_lines = [
            line.strip()
            for line in SERVICE_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("Exec")
        ]
        self.assertEqual(
            service_lines,
            [
                "ExecStart=/usr/bin/python3 -m greia_platform.system_updates "
                "--socket-activated"
            ],
        )


class PreIntroInstrumentAlignmentTests(unittest.TestCase):
    """The timing instrument consumes the production marker vocabulary.

    Regression guard for the parallel-vocabulary defect: default serial
    patterns must match what the shipped emitters actually write
    (``GREIA_BOOT event=<name>`` via ``boot_markers.emit_boot_marker``),
    never a wording no producer emits. The ``--marker`` override exists so
    a measurement run can bind an explicit harness observable without
    weakening these defaults.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.preintro = _load_module("preintro_timing_alignment", PREINTRO_PATH)

    def test_defaults_match_canonical_boot_markers(self) -> None:
        import re

        module = self.preintro
        patterns = dict(module.DEFAULT_MARKERS)
        self.assertEqual(
            sorted(patterns),
            [
                "first_intro_frame",
                "interactive_ready",
                "intro_end",
                "update_service_started",
            ],
        )
        # Exact lines in the shape emit_boot_marker writes (stdout + spool).
        self.assertIsNotNone(
            re.search(
                patterns["first_intro_frame"],
                "GREIA_BOOT event=intro_first_frame_flipped monotonic_ns=1",
            )
        )
        self.assertIsNotNone(
            re.search(
                patterns["intro_end"],
                "GREIA_BOOT event=intro_end monotonic_ns=2",
            )
        )
        self.assertIsNotNone(
            re.search(
                patterns["interactive_ready"],
                "GREIA_BOOT event=launcher_interactive_ready monotonic_ns=3",
            )
        )
        # The parallel wording no emitter writes must be gone.
        for stale in (
            "first frame visible",
            "Greia intro",
            "Greia launcher",
        ):
            for name, pattern in patterns.items():
                self.assertNotIn(stale, pattern, msg=name)
        # The predecessor's stale interactive_ready default (a bare
        # ``event=interactive_ready`` no production emitter writes) must be
        # gone from every default pattern; the canonical default carries the
        # ``launcher_``-prefixed event name instead.
        for name, pattern in patterns.items():
            self.assertNotIn("event=interactive_ready", pattern, msg=name)
        self.assertIn(
            "launcher_interactive_ready", patterns["interactive_ready"]
        )

    def test_update_marker_watches_service_activation_not_socket(self) -> None:
        import re

        module = self.preintro
        pattern = module.DEFAULT_MARKERS["update_service_started"]
        self.assertIsNotNone(
            re.search(
                pattern,
                "[  12.345678] Started Greia OS system-update semantic service.",
            )
        )
        # The pre-intro socket listener (sockets.target) is Exec-free and
        # expected on every boot: it must never trip P4.
        for listener_line in (
            "Listening on Greia OS system-update semantic socket.",
            "Reached target Sockets.",
            "Starting Greia OS system-update semantic service...",
        ):
            self.assertIsNone(
                re.search(pattern, listener_line), msg=listener_line
            )

    def test_measure_cli_accepts_marker_overrides(self) -> None:
        import io

        module = self.preintro
        name, pattern = module.parse_marker_override(
            "interactive_ready=GREIA_BOOT event=ready_for_kids"
        )
        self.assertEqual(
            (name, pattern), ("interactive_ready", "GREIA_BOOT event=ready_for_kids")
        )
        with self.assertRaises(module.PreIntroTimingError):
            module.parse_marker_override("no-such-marker=x")
        with self.assertRaises(module.PreIntroTimingError):
            module.parse_marker_override("interactive_ready=([unclosed")
        # The advertised flag must parse: on a host without the QEMU
        # facility the run must reach the facility gate (BLOCKED, return 2),
        # not die in argparse with "unrecognized arguments" (SystemExit).
        # On a host WITH the facility the same flag must still parse and
        # the marker override must be accepted (return 0 with tmp paths),
        # so the test never depends on a no-QEMU/host-path assumption.
        try:
            module.require_timing_host()
            has_facility = True
        except module.PreIntroTimingError:
            has_facility = False
        if not has_facility:
            captured = io.StringIO()
            with redirect_stderr(captured):
                code = module.main(
                    [
                        "measure",
                        "--label",
                        "probe",
                        "--serial-log",
                        "/nonexistent-probe/serial.log",
                        "--output",
                        "/nonexistent-probe/out.json",
                        "--marker",
                        "interactive_ready=ready",
                        "true",
                    ]
                )
            self.assertEqual(code, 2)
            self.assertIn("BLOCKED", captured.getvalue())
        else:
            with tempfile.TemporaryDirectory() as directory:
                serial_log = str(Path(directory) / "serial.log")
                output = str(Path(directory) / "out.json")
                captured = io.StringIO()
                with redirect_stderr(captured):
                    code = module.main(
                        [
                            "measure",
                            "--label",
                            "probe",
                            "--serial-log",
                            serial_log,
                            "--output",
                            output,
                            "--marker",
                            "interactive_ready=ready",
                            "true",
                        ]
                    )
                self.assertEqual(code, 0)
                record = json.loads(Path(output).read_text(encoding="utf-8"))
                self.assertEqual(record["label"], "probe")

    def test_compare_still_interprets_canonical_pair(self) -> None:
        module = self.preintro
        base = module.BootMeasurement(
            label="baseline",
            qemu_start_monotonic=100.0,
            first_intro_frame=110.0,
            intro_end=117.0,
            interactive_ready=120.0,
            update_service_started=None,
            timed_out=False,
        )
        activated = module.BootMeasurement(
            label="activated",
            qemu_start_monotonic=200.0,
            first_intro_frame=210.0,
            intro_end=217.0,
            interactive_ready=220.0,
            update_service_started=None,
            timed_out=False,
        )
        result = module.compare(base, activated)
        self.assertEqual(result["overall"], "PASS")
        missing = module.BootMeasurement(
            label="activated",
            qemu_start_monotonic=200.0,
            first_intro_frame=None,
            intro_end=None,
            interactive_ready=None,
            update_service_started=None,
            timed_out=True,
        )
        red = module.compare(base, missing)
        self.assertEqual(red["overall"], "NOT_READY")


class SevenSecondIntroFixedTests(unittest.TestCase):
    def test_seven_second_intro_fixed(self) -> None:
        tree = ast.parse(BOOT_INTRO_PATH.read_text(encoding="utf-8"))
        values = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and isinstance(
                    node.value, ast.Constant
                ):
                    values[target.id] = node.value.value
        self.assertEqual(values.get("ANIMATION_SECONDS"), 5.0)
        self.assertEqual(values.get("FINAL_FRAME_HOLD_SECONDS"), 2.0)
        total = values["ANIMATION_SECONDS"] + values["FINAL_FRAME_HOLD_SECONDS"]
        self.assertEqual(total, 7.0)


class PreIntroCanonicalWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.preintro = _load_module("preintro_timing_under_test", PREINTRO_PATH)
        cls.analyze = _load_module("analyze_boot_markers_under_test", ANALYZE_PATH)

    def test_default_markers_equal_canonical_emitted_events(self) -> None:
        """No default regex may exist that production can never match."""
        preintro = self.preintro
        mapping = dict(preintro.MARKER_TO_CANONICAL_EVENT)
        # The three Greia markers each name a real canonical event.
        self.assertEqual(mapping["first_intro_frame"], "intro_first_frame_flipped")
        self.assertEqual(mapping["intro_end"], "intro_end")
        self.assertEqual(
            mapping["interactive_ready"], "launcher_interactive_ready"
        )
        for key in ("first_intro_frame", "intro_end", "interactive_ready"):
            event = mapping[key]
            assert event is not None
            pattern = preintro.DEFAULT_MARKERS[key]
            # The default regex literally carries its canonical event name.
            self.assertIn(event, pattern)
            # ... and matches a real canonical sample line.
            sample = f"GREIA_BOOT event={event} monotonic_ns=123456789"
            self.assertRegex(sample, pattern)
            # ... and is shared with the canonical vocabulary.
            self.assertIn(event, set(self.analyze.KNOWN_EVENTS))
        # Module-level constants agree with the analyzer owner.
        self.assertEqual(
            preintro.CANONICAL_FIRST_FRAME_EVENT,
            self.analyze.FIRST_FRAME_EVENT,
        )
        self.assertIn(
            preintro.CANONICAL_INTERACTIVE_READY_EVENT,
            set(self.analyze.KNOWN_EVENTS),
        )

    def test_production_actually_emits_the_consumed_events(self) -> None:
        """Sensitivity anchor: defaults must be produced, not just parsed."""
        intro_emitted = _emitted_boot_events(BOOT_INTRO_PATH)
        self.assertIn("intro_enter", intro_emitted)
        self.assertIn("intro_first_frame_flipped", intro_emitted)
        self.assertIn("intro_end", intro_emitted)
        main_emitted = _emitted_boot_events(LAUNCHER_MAIN_PATH)
        self.assertIn("launcher_interactive_ready", main_emitted)

    def test_parallel_vocabulary_is_gone(self) -> None:
        """Negative control: the old human-readable strings match nothing."""
        preintro = self.preintro
        for key, pattern in preintro.DEFAULT_MARKERS.items():
            with self.subTest(marker=key):
                self.assertNotIn("Greia intro:", pattern)
                self.assertNotIn("Greia launcher:", pattern)
        source = PREINTRO_PATH.read_text(encoding="utf-8")
        self.assertNotIn("Greia intro: first frame visible", source)
        self.assertNotIn("Greia intro: complete", source)
        self.assertNotIn("Greia launcher: interactive ready", source)

    def test_marker_override_is_implemented(self) -> None:
        """The advertised ``--marker NAME=PATTERN`` override really exists."""
        preintro = self.preintro
        name, pattern = preintro.parse_marker_override(
            "interactive_ready=GREIA_BOOT event=custom_ready\\b"
        )
        self.assertEqual(name, "interactive_ready")
        self.assertEqual(pattern, r"GREIA_BOOT event=custom_ready\b")
        with self.assertRaises(preintro.PreIntroTimingError):
            preintro.parse_marker_override("bogus-name-without-equals")
        with self.assertRaises(preintro.PreIntroTimingError):
            preintro.parse_marker_override("unknown_key=x")
        with self.assertRaises(preintro.PreIntroTimingError):
            preintro.parse_marker_override("interactive_ready=([unclosed")
        # The `measure` subparser exposes the flag (not docstring-only).
        buffer = io.StringIO()
        with self.assertRaises(SystemExit) as raised:
            with redirect_stdout(buffer):
                preintro.main(["measure", "--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("--marker", buffer.getvalue())


def _synthetic_measurements(preintro, **overrides):
    """Two full canonical runs: 10 s to first frame, 7 s intro, ready at 20 s."""
    base_kwargs = {
        "label": "baseline",
        "qemu_start_monotonic": 1000.0,
        "first_intro_frame": 1010.0,
        "intro_end": 1017.0,
        "interactive_ready": 1020.0,
        "update_service_started": None,
        "timed_out": False,
    }
    act_kwargs = dict(base_kwargs)
    act_kwargs["label"] = "activated"
    act_kwargs.update(overrides.pop("activated", {}))
    base_kwargs.update(overrides.pop("baseline", {}))
    base_kwargs.update(overrides)
    return (
        preintro.BootMeasurement(**base_kwargs),
        preintro.BootMeasurement(**act_kwargs),
    )


class PreIntroCompareCanonicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.preintro = _load_module("preintro_timing_compare", PREINTRO_PATH)

    def test_synthetic_canonical_stream_drives_full_pass(self) -> None:
        """A canonical serial stream scans clean and compares to PASS."""
        preintro = self.preintro
        text = (
            "[    5.000000] GREIA_BOOT event=intro_enter monotonic_ns=5000000000\n"
            "[   10.000000] GREIA_BOOT event=intro_first_frame_flipped "
            "monotonic_ns=10000000000\n"
            "[   17.000000] GREIA_BOOT event=intro_end monotonic_ns=17000000000\n"
            "[   20.000000] GREIA_BOOT event=launcher_interactive_ready "
            "monotonic_ns=20000000000\n"
        )
        seen = preintro.scan_serial_text(text)
        self.assertTrue(seen["first_intro_frame"])
        self.assertTrue(seen["intro_end"])
        self.assertTrue(seen["interactive_ready"])
        self.assertFalse(seen["update_service_started"])
        baseline, activated = _synthetic_measurements(preintro)
        result = preintro.compare(baseline, activated)
        self.assertEqual(result["overall"], "PASS")
        predicates = result["predicates"]
        for key in (
            "P1_power_to_first_frame_no_regression",
            "P2_intro_duration_unchanged",
            "P3_interactive_ready_reached",
            "P4_no_update_work_pre_intro",
        ):
            self.assertEqual(predicates[key]["verdict"], "PASS", msg=key)

    def test_withdraw_first_frame_yields_not_ready(self) -> None:
        preintro = self.preintro
        baseline, activated = _synthetic_measurements(
            preintro, activated={"first_intro_frame": None, "intro_end": None}
        )
        result = preintro.compare(baseline, activated)
        self.assertEqual(
            result["predicates"]["P1_power_to_first_frame_no_regression"]["verdict"],
            "NOT_READY",
        )
        self.assertEqual(
            result["predicates"]["P4_no_update_work_pre_intro"]["verdict"],
            "NOT_READY",
        )
        self.assertEqual(result["overall"], "NOT_READY")

    def test_withdraw_interactive_ready_yields_not_ready(self) -> None:
        preintro = self.preintro
        baseline, activated = _synthetic_measurements(
            preintro, activated={"interactive_ready": None}
        )
        result = preintro.compare(baseline, activated)
        self.assertEqual(
            result["predicates"]["P3_interactive_ready_reached"]["verdict"],
            "NOT_READY",
        )
        self.assertEqual(result["overall"], "NOT_READY")


class AnalyzeInteractiveReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.analyze = _load_module("analyze_boot_markers_check", ANALYZE_PATH)

    def test_interactive_ready_parses_with_no_unknown_warning(self) -> None:
        analyze = self.analyze
        text = (
            "[    5.000000] GREIA_BOOT event=intro_enter monotonic_ns=5000000000\n"
            "[   10.000000] GREIA_BOOT event=intro_first_frame_flipped "
            "monotonic_ns=10000000000\n"
            "[   17.000000] GREIA_BOOT event=intro_end monotonic_ns=17000000000\n"
            "[   20.000000] GREIA_BOOT event=launcher_interactive_ready "
            "monotonic_ns=20000000000\n"
        )
        analysis = analyze.analyze_journal(text)
        names = [event.name for event in analysis.events]
        self.assertIn("launcher_interactive_ready", names)
        self.assertEqual(analysis.unknown_events, [])


if __name__ == "__main__":
    unittest.main()
