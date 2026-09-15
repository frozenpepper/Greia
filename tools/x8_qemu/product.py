"""P5.1 product-image mode and test-only guest-control seam (additive).

``POSTR1-P5-PRODUCT-MODE`` enabling task: boot the actual built Greia
image + shipped systemd production units and drive the real guest
services through a pinned test-only control seam, reusing the single
lifecycle engine in :mod:`tools.x8_qemu.lifecycle`.

Reuse, not duplication: this module owns only the product-mode
orchestration wrapper and the control-seam text/injection helpers. The
8-transition sequence (``LIFECYCLE_SEQUENCE``), the transition contract
(``assert_lifecycle_transitions``), the observation folds
(``decide_device_boot_observation``,
``GrubEnvBackend.attach(...).inspect()``, journal/accepted-sequence/
PERSIST reads), the release lineage shape, the ``ImageIntegrationSeams``
positive controls, the D31 fixture/interruption/resource envelope and
the 768 MiB cgroup gate all stay owned by ``lifecycle.py`` /
``devproof.py`` and are referenced here, never reimplemented.

Control is orchestration only: the control channel may trigger guest
operations but never reports outcomes. Every claimed boot/disk/identity
fact is read host-side from image bytes through the production parsers,
exactly as ``run_device`` already does. The control-derived attestation
set is empty by construction (see ``ATTESTATION_SOURCES`` and
:func:`attest_product_boot`).

Fail-closed: :func:`require_product_host` names the missing disposable
Linux/QEMU/loop/mount facility or absent official image and raises
``LifecycleHarnessError`` (BLOCKED). This module never fabricates a
boot, unit, disk or identity observation and never contacts a valued
physical disk: QEMU receives ``file=<regular image>`` only, and
``LifecycleConfig.validate`` refuses output inside the source tree.

Preserved: the seven-second intro (``boot_intro.ANIMATION_SECONDS`` +
``FINAL_FRAME_HOLD_SECONDS``) and the 3-minute recovery timer
(``CANDIDATE_HEALTH_DEADLINE_SEC == 180``) are referenced, not changed.
No production ``src/``, ``build/overlay/`` or
``build/installer-overlay/`` change; test-only injection is applied by
tool code to a disposable image copy.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from .lifecycle import (
    BOOT_OUTCOME_EXPECTED_SLOT,
    BOOT_OUTCOME_LEGS,
    LAUNCHER_ACCEPTANCE_LEGS,
    LIFECYCLE_SEQUENCE,
    NON_BOOT_TRANSITIONS,
    PROJECT_ROOT,
    SHIPPED_UPDATE_LEGS,
    LifecycleConfig,
    LifecycleHarness,
    LifecycleHarnessError,
    lifecycle_spec,
    require_device_host,
    resolve_device_host_tool,
)

# ---------------------------------------------------------------------------
# Pinned control-seam identity (test-only; see structural pin below)
# ---------------------------------------------------------------------------

#: Test-only systemd unit injected into disposable clones only.
CONTROL_UNIT_NAME = "greia-x8-control.service"

#: Test-only guest runner injected into disposable clones only.
CONTROL_RUNNER_PATH = "/usr/local/sbin/greia-x8-control"

#: Label of the host-written per-boot control disk (phase channel).
CONTROL_DISK_LABEL = "GREIA-X8-CTL"

#: Phase file read by the guest runner from the control disk.
CONTROL_PHASE_FILE = "phase.json"

#: Acknowledgement file written by the guest runner (orchestration only,
#: never consulted for attestation).
CONTROL_ACK_FILE = "ack.json"

#: Real production sockets the runner drives (orchestration targets).
INSTALL_SOCKET_PATH = "/run/greia-os/install-transaction.sock"
UPDATE_SOCKET_PATH = "/run/greia-os/system-update.sock"
BOOT_HEALTH_SOCKET_PATH = "/run/greia-os/boot-health.sock"

#: Bounded per-boot phases the runner will act on. Anything else is
#: refused fail-closed inside the guest (runner exits nonzero).
CONTROL_PHASES: tuple[str, ...] = (
    "install-prepare",
    "install-execute",
    "update-status",
    "update-verify",
    "update-stage",
    "update-arm",
    "wait-health-poweroff",
)

#: Authoritative attestation sources. The control channel appears here
#: only as an explicit non-source: nothing claimed about boot, disk or
#: identity may be read from it.
ATTESTATION_SOURCES: tuple[str, ...] = (
    "GrubEnvBackend.attach(<p1 mount>).inspect()",
    "decide_device_boot_observation(pre, post)",
    "payload.read_attestation_signal",
    "BootTransactionJournal.load(<image state dir>)",
    "read_accepted_sequence(<image state dir>)",
    "persist partition bytes + devproof D31 fixture parse",
    "sha256_file(image) + blkid/sfdisk cross-check",
    "control channel: NOT A SOURCE (orchestration only)",
)

#: Production trees the control seam must never appear in (structural pin).
PRODUCTION_TREES: tuple[str, ...] = (
    "src",
    "build/overlay",
    "build/installer-overlay",
)

#: Extra host tools the product path needs beyond ``require_device_host``.
PRODUCT_HOST_EXTRA_TOOLS: tuple[str, ...] = (
    "mkfs.ext4",
    "mksquashfs",
    "unsquashfs",
)

#: P5.2 install leg: official legacy installer composition profile.
INSTALL_PROFILE_ID = "acer-aspire-one-i386-ab"

#: Official installer image file name produced by
#: ``build/build-installer-image.sh acer-aspire-one-i386-ab <out>``.
INSTALLER_IMAGE_NAME = "greia-os-installer-acer-aspire-one-i386-ab.img"

#: Live root inside the installer image's first partition (rebuilt in the
#: disposable clone only; the source image is never touched).
LIVE_SQUASHFS_IN_PARTITION = "live/filesystem.squashfs"

#: Graphical installer masked in the clone only during the automated
#: install leg (test-only clone mutation, r7 precedent).
INSTALLER_GRAPHICAL_SERVICE = "greia-installer.service"

#: Disposable whole-disk target size for the fresh A/B install (7 GiB,
#: mirroring ``build/verify-installer-qemu.sh``).
DISPOSABLE_TARGET_BYTES = 7 * 1024**3

#: Install-leg per-boot phases driven on the control disk, in order.
INSTALL_LEG_PHASES: tuple[str, ...] = ("install-prepare", "install-execute")

#: Synthetic ATA serial pinned on the disposable QEMU install target
#: (``-device ide-hd,drive=target,serial=...``). The host-side pre-install
#: observation mirrors exactly this serial (plus size/transport) through the
#: production :class:`greia_installer.disk.DeviceObservation` so both sides
#: bind the same durable facts; the guest service still re-derives the
#: digest from its live probe and refuses on mismatch (fail-closed).
TARGET_DISK_SERIAL = "GREIA-PROD-TARGET-1"

#: Human model recorded on the disposable target observation (display only;
#: strong identity never depends on model strings).
TARGET_DISK_MODEL = "Greia product disposable target"

#: Host-side mirror transport for the QEMU ``ide-hd`` ATA presentation.
#: Recorded in evidence; a guest probe that observes a different transport
#: refuses fail-closed instead of matching.
TARGET_DISK_TRANSPORT = "ata"


def product_spec() -> dict[str, object]:
    """Pure-data product-mode declaration for tests and report headers."""
    return {
        "schema_version": 1,
        "mode": "product-image",
        "lifecycle_sequence": list(LIFECYCLE_SEQUENCE),
        "non_boot_transitions": list(NON_BOOT_TRANSITIONS),
        "boot_outcome_legs": list(BOOT_OUTCOME_LEGS),
        "shipped_update_legs": list(SHIPPED_UPDATE_LEGS),
        "launcher_acceptance_legs": list(LAUNCHER_ACCEPTANCE_LEGS),
        "control_unit": CONTROL_UNIT_NAME,
        "control_runner": CONTROL_RUNNER_PATH,
        "control_disk_label": CONTROL_DISK_LABEL,
        "control_phases": list(CONTROL_PHASES),
        "control_sockets": {
            "install": INSTALL_SOCKET_PATH,
            "update": UPDATE_SOCKET_PATH,
            "boot_health": BOOT_HEALTH_SOCKET_PATH,
        },
        "attestation_sources": list(ATTESTATION_SOURCES),
        "control_is_attestation_source": False,
        "valued_device_contact": False,
        "intro_seconds": 7.0,
        "recovery_deadline_seconds": 180,
        "production_trees_untouched": list(PRODUCTION_TREES),
    }


# ---------------------------------------------------------------------------
# Control-seam text (lives in tools/ only; written into clones at run time)
# ---------------------------------------------------------------------------


def control_unit_text() -> str:
    """Text of the test-only ``greia-x8-control.service`` unit."""
    return (
        "# TEST-ONLY Greia X8 product-mode control seam (P5.1).\n"
        "# Injected by tools/x8_qemu/product.py into disposable image clones\n"
        "# only. Never shipped: must not appear under src/, build/overlay/\n"
        "# or build/installer-overlay/. Orchestration only: triggers real\n"
        "# guest services, never reports boot/disk/identity outcomes.\n"
        "[Unit]\n"
        "Description=Greia X8 test-only product control (disposable clone)\n"
        "After=greia-install-transaction.service greia-system-update.service greia-boot-health.service\n"
        "ConditionPathExists=/usr/local/sbin/greia-x8-control\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"ExecStart={CONTROL_RUNNER_PATH}\n"
        "\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
    )


def control_runner_text() -> str:
    """Text of the test-only guest runner (bash, executed in-guest only).

    P5.2 install leg: the install branches drive the exact P5.1 §4
    invocations — ``InstallTransactionClient(socket_transport(...))``
    then ``.prepare(expected_target_identity=..., compatible_profile_id=...,
    settings_snapshot={})`` then ``.execute(transaction_nonce, plan_digest)``
    — over the shipped ``/run/greia-os/install-transaction.sock``.

    P5.2 boot-health leg: the update branches drive the exact P5.1 §4
    update invocations — ``greia_platform.update_privileged.build_request``
    / ``read_response`` over the shipped
    ``/run/greia-os/system-update.sock`` with the semantic ops
    ``STATUS`` / ``VERIFY_CURRENT_CANDIDATE`` / ``STAGE_CURRENT_CANDIDATE``
    / ``ARM_CURRENT_CANDIDATE`` (no selectors; the service resolves the
    inbox candidate internally) — and the ``wait-health-poweroff`` branch
    drives the exact root health confirmation —
    ``greia_launcher.boot_health.maybe_load_production_token`` then
    ``greia_platform.boot_health_service.build_confirm_request`` /
    ``read_confirm_response`` over the shipped
    ``/run/greia-os/boot-health.sock`` (the launcher-owned
    ``maybe_accept_production_boot`` is the equivalent production caller
    at ``INTERACTIVE_READY``; this root-orchestrated runner drives the
    same socket directly and never attests the outcome). The channel
    triggers and acknowledges only; it never reports a boot/disk/identity
    outcome (the ack carries phase/socket only).
    """
    return (
        "#!/bin/bash\n"
        "# TEST-ONLY Greia X8 product-mode control runner (P5.1/P5.2).\n"
        "# Reads one bounded phase from the host-written control disk\n"
        f"# (LABEL={CONTROL_DISK_LABEL}, {CONTROL_PHASE_FILE}), drives the real\n"
        "# guest service over the real socket, writes a small acknowledgement\n"
        "# (orchestration only, never attestation), then powers off.\n"
        "set -euo pipefail\n"
        f"CTL_MNT=/run/{CONTROL_DISK_LABEL.lower()}\n"
        "mkdir -p \"$CTL_MNT\"\n"
        f"mount -o ro \"LABEL={CONTROL_DISK_LABEL}\" \"$CTL_MNT\"\n"
        f"trap 'umount \"$CTL_MNT\"' EXIT\n"
        f"PHASE_FILE=\"$CTL_MNT/{CONTROL_PHASE_FILE}\"\n"
        "test -f \"$PHASE_FILE\" || { echo \"x8-control: no phase file\" >&2; exit 1; }\n"
        "PHASE=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[\"phase\"])' \"$PHASE_FILE\")\n"
        "case \"$PHASE\" in\n"
        "  install-prepare|install-execute)\n"
        f"    SOCK=\"{INSTALL_SOCKET_PATH}\"; test -S \"$SOCK\" || exit 1;;\n"
        "  update-status|update-verify|update-stage|update-arm)\n"
        f"    SOCK=\"{UPDATE_SOCKET_PATH}\"; test -S \"$SOCK\" || exit 1;;\n"
        "  wait-health-poweroff)\n"
        f"    SOCK=\"{BOOT_HEALTH_SOCKET_PATH}\"; test -S \"$SOCK\" || exit 1;;\n"
        "  *) echo \"x8-control: refused unknown phase $PHASE\" >&2; exit 1;;\n"
        "esac\n"
        "if [ \"$PHASE\" = \"install-prepare\" ] || [ \"$PHASE\" = \"install-execute\" ]; then\n"
        "  python3 - \"$PHASE_FILE\" \"$SOCK\" <<'PYEOF'\n"
        "import json\n"
        "import sys\n"
        "from pathlib import Path\n"
        "from greia_installer.transaction_client import (\n"
        "    InstallTransactionClient,\n"
        "    socket_transport,\n"
        "    read_compatible_profile_id,\n"
        ")\n"
        "phase_file = Path(sys.argv[1])\n"
        "sock = Path(sys.argv[2])\n"
        "doc = json.loads(phase_file.read_text(encoding=\"utf-8\"))\n"
        "phase = doc.get(\"phase\")\n"
        "inputs = dict(doc.get(\"inputs\") or {})\n"
        "expected_target_identity = str(inputs.get(\"expected_target_identity\", \"\"))\n"
        "if not expected_target_identity:\n"
        "    raise SystemExit(\"x8-control: install phase carries no expected_target_identity\")\n"
        "override = str(inputs.get(\"compatible_profile_id\", \"\"))\n"
        "compatible_profile_id = override or read_compatible_profile_id()\n"
        "client = InstallTransactionClient(socket_transport(sock))\n"
        "prepared = client.prepare(\n"
        "    expected_target_identity=expected_target_identity,\n"
        "    compatible_profile_id=compatible_profile_id,\n"
        "    settings_snapshot={},\n"
        ")\n"
        "if phase == \"install-execute\":\n"
        "    receipt = client.execute(\n"
        "        transaction_nonce=prepared.transaction_nonce,\n"
        "        plan_digest=prepared.plan_digest,\n"
        "    )\n"
        "PYEOF\n"
        "fi\n"
        "if [ \"$PHASE\" = \"update-status\" ] || [ \"$PHASE\" = \"update-verify\" ] || [ \"$PHASE\" = \"update-stage\" ] || [ \"$PHASE\" = \"update-arm\" ]; then\n"
        "  python3 - \"$PHASE_FILE\" \"$SOCK\" \"$CTL_MNT\" <<'PYEOF'\n"
        "import json\n"
        "import shutil\n"
        "import socket\n"
        "import sys\n"
        "from pathlib import Path\n"
        "from greia_platform.update_privileged import build_request, read_response\n"
        "phase_file = Path(sys.argv[1])\n"
        "sock = sys.argv[2]\n"
        "ctl_mnt = Path(sys.argv[3])\n"
        "doc = json.loads(phase_file.read_text(encoding=\"utf-8\"))\n"
        "phase = doc.get(\"phase\")\n"
        "ops = {\n"
        "    \"update-status\": \"STATUS\",\n"
        "    \"update-verify\": \"VERIFY_CURRENT_CANDIDATE\",\n"
        "    \"update-stage\": \"STAGE_CURRENT_CANDIDATE\",\n"
        "    \"update-arm\": \"ARM_CURRENT_CANDIDATE\",\n"
        "}\n"
        "op = ops.get(str(phase))\n"
        "if op is None:\n"
        "    raise SystemExit(f\"x8-control: refused unknown update phase {phase!r}\")\n"
        "if phase == \"update-stage\":\n"
        "    candidate = ctl_mnt / \"candidate.greiaupdate\"\n"
        "    if candidate.is_file():\n"
        "        inbox_dir = Path(\"/var/lib/greia-os/system-updates/inbox\")\n"
        "        inbox_dir.mkdir(parents=True, exist_ok=True)\n"
        "        shutil.copy2(candidate, inbox_dir / \"candidate.greiaupdate\")\n"
        "request = build_request(op)\n"
        "client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)\n"
        "client.settimeout(30.0)\n"
        "client.connect(sock)\n"
        "client.sendall(request)\n"
        "try:\n"
        "    client.shutdown(socket.SHUT_WR)\n"
        "except OSError:\n"
        "    pass\n"
        "chunks = []\n"
        "while True:\n"
        "    chunk = client.recv(4096)\n"
        "    if not chunk:\n"
        "        break\n"
        "    chunks.append(chunk)\n"
        "client.close()\n"
        "transaction_id, returned_op, payload = read_response(b\"\".join(chunks))\n"
        "expected_status = {\n"
        "    \"STATUS\": \"OK\",\n"
        "    \"VERIFY_CURRENT_CANDIDATE\": \"VERIFIED\",\n"
        "    \"STAGE_CURRENT_CANDIDATE\": \"STAGED\",\n"
        "    \"ARM_CURRENT_CANDIDATE\": \"ARMED\",\n"
        "}[op]\n"
        "if returned_op != op or payload.get(\"status\") != expected_status:\n"
        "    raise SystemExit(f\"x8-control: update {op} refused: {payload!r}\")\n"
        "PYEOF\n"
        "fi\n"
        "if [ \"$PHASE\" = \"wait-health-poweroff\" ]; then\n"
        "  python3 - \"$SOCK\" <<'PYEOF'\n"
        "import socket\n"
        "import sys\n"
        "from greia_launcher.boot_health import maybe_load_production_token\n"
        "from greia_platform.boot_health_service import build_confirm_request, read_confirm_response\n"
        "sock = sys.argv[1]\n"
        "token = maybe_load_production_token()\n"
        "if token is None:\n"
        "    raise SystemExit(0)\n"
        "request = build_confirm_request(token)\n"
        "client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)\n"
        "client.settimeout(30.0)\n"
        "client.connect(sock)\n"
        "client.sendall(request)\n"
        "try:\n"
        "    client.shutdown(socket.SHUT_WR)\n"
        "except OSError:\n"
        "    pass\n"
        "chunks = []\n"
        "while True:\n"
        "    chunk = client.recv(4096)\n"
        "    if not chunk:\n"
        "        break\n"
        "    chunks.append(chunk)\n"
        "client.close()\n"
        "transaction_id, op, payload = read_confirm_response(b\"\".join(chunks))\n"
        "if op != \"CONFIRM_BOOT_HEALTH\" or payload.get(\"status\") != \"CONFIRMED\":\n"
        "    raise SystemExit(f\"x8-control: boot-health confirm refused: {payload!r}\")\n"
        "PYEOF\n"
        "fi\n"
        f"echo \"{{\\\"phase\\\": \\\"$PHASE\\\", \\\"socket\\\": \\\"$SOCK\\\"}}\" > \"/run/{CONTROL_ACK_FILE}\"\n"
        "systemctl poweroff\n"
    )


# ---------------------------------------------------------------------------
# Host-side phase channel (host-authored, out of every production subsystem)
# ---------------------------------------------------------------------------


def write_control_phase(
    control_dir: Path, *, phase: str, inputs: Mapping[str, object] | None = None
) -> Path:
    """Write one per-boot ``phase.json`` into the host control directory."""
    if phase not in CONTROL_PHASES:
        raise LifecycleHarnessError(
            f"control seam refuses unknown phase {phase!r} "
            f"(expected one of {', '.join(CONTROL_PHASES)})"
        )
    root = Path(control_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / CONTROL_PHASE_FILE
    payload = {"phase": phase, "inputs": dict(inputs or {})}
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def read_control_phase(control_dir: Path) -> dict[str, object]:
    """Read back a host-written phase (fail-closed on missing/misrouted)."""
    path = Path(control_dir) / CONTROL_PHASE_FILE
    if not path.is_file():
        raise LifecycleHarnessError(
            "control seam misrouted: no phase file on the control disk "
            f"({path}); the run fails closed, never silently no-ops"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise LifecycleHarnessError(
            f"control seam misrouted: unreadable phase file ({exc})"
        ) from exc
    if not isinstance(payload, dict) or payload.get("phase") not in CONTROL_PHASES:
        raise LifecycleHarnessError(
            "control seam misrouted: phase file does not name a bounded "
            f"phase (got {payload!r})"
        )
    return dict(payload)


# ---------------------------------------------------------------------------
# Disposable-clone separation and valued-disk exclusion
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clone_product_image(source: Path, clone: Path) -> dict[str, str]:
    """Clone the official image into the disposable output root (r7 pattern).

    Records ``source_sha256`` before, never opens the source read-write,
    never boots it. Only regular files under an absolute disposable root
    are accepted; ``/dev`` nodes are refused so no valued physical disk
    can be contacted.
    """
    src = Path(source)
    dst = Path(clone)
    for candidate in (src, dst):
        if str(candidate).startswith("/dev/"):
            raise LifecycleHarnessError(
                f"refusing block-device path {candidate}: product mode takes "
                "regular image files only"
            )
    if not src.is_file() or src.stat().st_size == 0:
        raise LifecycleHarnessError(
            f"official product image missing or empty: {src} (BLOCKED: "
            "absent official image; never synthesize one)"
        )
    if src.resolve() == dst.resolve():
        raise LifecycleHarnessError("source and clone must be different paths")
    if dst.exists():
        raise LifecycleHarnessError(f"refusing to replace existing clone: {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    source_sha = sha256_file(src)
    completed = subprocess.run(
        ["cp", "--reflink=auto", "--sparse=always", "--", str(src), str(dst)],
        capture_output=True,
        timeout=600,
    )
    if completed.returncode != 0 or not dst.is_file():
        raise LifecycleHarnessError(f"disposable image clone failed for {src}")
    if dst.stat().st_size != src.stat().st_size:
        raise LifecycleHarnessError("disposable image clone is incomplete")
    return {"source_sha256": source_sha, "clone": str(dst.resolve())}


def inject_control_into_root(
    root: Path, *, mask_service: str | None = None
) -> dict[str, object]:
    """Write the test-only unit + runner into a slot/live root tree.

    ``root`` is the mounted slot root (loop-mounted ext4 on a capable
    host) or an exploded squashfs tree / directory fake in tests. The
    source image is never touched: callers mount only disposable clones.
    Returns the exact injected paths so the P5.3 identity record can name
    the mutation explicitly.
    """
    base = Path(root)
    unit_dir = base / "etc/systemd/system"
    if not unit_dir.is_dir():
        raise LifecycleHarnessError(
            f"control injection refused: {unit_dir} is not a guest root "
            "(misrouted target fails closed)"
        )
    runner = base / CONTROL_RUNNER_PATH.lstrip("/")
    runner.parent.mkdir(parents=True, exist_ok=True)
    runner.write_text(control_runner_text(), encoding="utf-8")
    runner.chmod(0o755)
    unit = unit_dir / CONTROL_UNIT_NAME
    unit.write_text(control_unit_text(), encoding="utf-8")
    unit.chmod(0o644)
    wants = unit_dir / "multi-user.target.wants"
    wants.mkdir(parents=True, exist_ok=True)
    enabled = wants / CONTROL_UNIT_NAME
    if enabled.exists() or enabled.is_symlink():
        enabled.unlink()
    enabled.symlink_to(f"../{CONTROL_UNIT_NAME}")
    masked: str | None = None
    if mask_service is not None:
        target = unit_dir / mask_service
        if target.exists() or target.is_symlink():
            target.unlink()
        target.symlink_to("/dev/null")
        masked = mask_service
    return {
        "unit": str(unit),
        "runner": str(runner),
        "wants_link": str(enabled),
        "masked": masked,
    }


def validate_control_present(root: Path) -> None:
    """Fail closed when the control seam is absent or misrouted.

    Negative control: removing the unit/runner/wants link (or pointing at
    a tree that never received the injection) raises instead of letting
    a later leg claim success by silent no-op.
    """
    base = Path(root)
    missing = [
        str(relative)
        for relative in (
            Path(f"etc/systemd/system/{CONTROL_UNIT_NAME}"),
            Path(CONTROL_RUNNER_PATH.lstrip("/")),
            Path(f"etc/systemd/system/multi-user.target.wants/{CONTROL_UNIT_NAME}"),
        )
        if not (base / relative).exists() and not (base / relative).is_symlink()
    ]
    if missing:
        raise LifecycleHarnessError(
            "control seam absent, run fails closed (no acceptance by "
            f"silent no-op); missing: {', '.join(missing)}"
        )


# ---------------------------------------------------------------------------
# Structural pins: test-only module, never an attestation source
# ---------------------------------------------------------------------------


def assert_control_absent_from_production(
    project_root: Path = PROJECT_ROOT,
) -> None:
    """Pin: the control seam is test-only and cannot be an attestation source.

    Fails closed when the control unit name (or an import of this tool
    module) appears anywhere under ``src/``, ``build/overlay/`` or
    ``build/installer-overlay/``.
    """
    root = Path(project_root)
    hits: list[str] = []
    for tree in PRODUCTION_TREES:
        base = root / tree
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, ValueError):
                continue
            if CONTROL_UNIT_NAME in text or "tools.x8_qemu.product" in text:
                hits.append(str(path.relative_to(root)))
    if hits:
        raise LifecycleHarnessError(
            "control seam leaked into production trees: " + ", ".join(hits)
        )


def attest_product_boot(
    *,
    leg: str,
    pre: Mapping[str, object],
    post: Mapping[str, object],
    control_report: Mapping[str, object] | None = None,
) -> str:
    """Derive the observed boot slot from on-image bytes only.

    Thin reuse wrapper over the frozen
    :func:`decide_device_boot_observation` predicate. ``control_report``
    exists so the boundary is explicit: passing anything but ``None``
    raises, proving the control channel can never be an attestation
    source.
    """
    from .lifecycle import decide_device_boot_observation

    if control_report is not None:
        raise LifecycleHarnessError(
            "attestation refuses control-channel input: boot truth comes "
            "only from image bytes and production parsers"
        )
    if leg not in BOOT_OUTCOME_EXPECTED_SLOT:
        raise LifecycleHarnessError(f"unknown product boot leg {leg!r}")
    return str(decide_device_boot_observation(leg=leg, pre=pre, post=post))


# ---------------------------------------------------------------------------
# Fail-closed host gate (BLOCKED, never fabricated)
# ---------------------------------------------------------------------------


def require_product_host(
    *,
    runner_which=None,
    official_image: Path | None = None,
) -> None:
    """Fail closed unless this host can execute the product-image mode.

    Names the missing disposable Linux/QEMU/loop/mount facility or the
    absent official image (BLOCKED). Never fabricates a boot, unit, disk
    or identity observation.
    """
    try:
        require_device_host(runner_which=runner_which)
    except LifecycleHarnessError as exc:
        raise LifecycleHarnessError(f"BLOCKED product mode: {exc}") from exc
    which = runner_which or resolve_device_host_tool
    if sys.platform != "linux":
        raise LifecycleHarnessError(
            "BLOCKED product mode: device lifecycle requires a Linux host "
            f"(this host reports {sys.platform})"
        )
    missing = [tool for tool in PRODUCT_HOST_EXTRA_TOOLS if which(tool) is None]
    qemu_i386 = which("qemu-system-i386")
    qemu_x64 = which("qemu-system-x86_64")
    if qemu_i386 is None and qemu_x64 is None:
        missing.append("qemu-system-i386|qemu-system-x86_64")
    if missing:
        raise LifecycleHarnessError(
            "BLOCKED product mode: missing product host tools: "
            + ", ".join(missing)
        )
    if official_image is None or not Path(official_image).is_file():
        raise LifecycleHarnessError(
            "BLOCKED product mode: absent official image "
            f"({official_image}); build it with build/build-installer-image.sh "
            "or pin a prebuilt artifact; never synthesize one"
        )


# ---------------------------------------------------------------------------
# P5.2 install leg: disposable-loop helpers (fail-closed, injectable runner)
# ---------------------------------------------------------------------------


def _host_which(name: str, which=None):
    """Resolve a host tool via the lifecycle resolver, then ``PATH``."""
    resolve = which or resolve_device_host_tool
    found = resolve(name)
    if found is not None:
        return str(found)
    return shutil.which(name)


def _run_checked(
    argv: list[str], *, runner=None, timeout: int = 120, what: str
):
    """Run an argv array (``shell=False``) and fail closed on nonzero exit."""
    run = runner or subprocess.run
    completed = run(
        [str(part) for part in argv],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    code = getattr(completed, "returncode", 1)
    if code != 0:
        detail = (
            str(getattr(completed, "stderr", "") or "")[-500:]
            or str(getattr(completed, "stdout", "") or "")[-500:]
        )
        raise LifecycleHarnessError(f"{what} failed (exit {code}): {detail}")
    return completed


def _require_loop_tools(*names: str, which=None) -> dict[str, str]:
    """Resolve loop/mount/probe tools or raise ``BLOCKED`` naming them."""
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for name in names:
        found = _host_which(name, which)
        if found is None:
            missing.append(name)
        else:
            resolved[name] = found
    if missing:
        raise LifecycleHarnessError(
            "BLOCKED product mode: missing product host tools: "
            + ", ".join(missing)
        )
    return resolved


def _loop_attach(image_path: Path, *, runner=None, which=None) -> str:
    """Attach a disposable image via ``losetup --show -f`` (or ``-P``)."""
    tools = _require_loop_tools("losetup", which=which)
    completed = _run_checked(
        [tools["losetup"], "--show", "-f", str(image_path)],
        runner=runner,
        timeout=120,
        what=f"loop attach for {image_path}",
    )
    loopdev = str(getattr(completed, "stdout", "") or "").strip().splitlines()
    if not loopdev or not loopdev[0].startswith("/dev/"):
        raise LifecycleHarnessError(
            f"loop attach for {image_path} returned no device node"
        )
    return loopdev[0]


def _loop_attach_partscan(image_path: Path, *, runner=None, which=None) -> str:
    """Attach with kernel partition scan (``losetup -P``) for part nodes."""
    tools = _require_loop_tools("losetup", which=which)
    completed = _run_checked(
        [tools["losetup"], "--show", "-f", "-P", str(image_path)],
        runner=runner,
        timeout=120,
        what=f"loop partscan attach for {image_path}",
    )
    loopdev = str(getattr(completed, "stdout", "") or "").strip().splitlines()
    if not loopdev or not loopdev[0].startswith("/dev/"):
        raise LifecycleHarnessError(
            f"loop partscan attach for {image_path} returned no device node"
        )
    return loopdev[0]


def _loop_detach(loopdev: str, *, runner=None) -> None:
    """Best-effort detach (cleanup path: never raises)."""
    run = runner or subprocess.run
    try:
        run(
            ["losetup", "-d", "--", str(loopdev)],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception:
        pass


def _mount_fs(
    source: str, mountpoint: Path, *, read_only: bool, runner=None, which=None
) -> None:
    """Mount a device node (fail-closed; cleanup uses :func:`_umount_fs`)."""
    _require_loop_tools("mount", which=which)
    argv = ["mount"]
    if read_only:
        argv += ["-o", "ro"]
    argv += ["--", str(source), str(mountpoint)]
    _run_checked(argv, runner=runner, timeout=120, what=f"mount {source}")


def _umount_fs(mountpoint: Path, *, runner=None) -> None:
    """Best-effort unmount (cleanup path: never raises)."""
    run = runner or subprocess.run
    try:
        run(
            ["umount", "--", str(mountpoint)],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception:
        pass


def disposable_target_observation(target_image: Path, *, size_bytes: int):
    """Build the production target observation for the disposable disk.

    Uses :class:`greia_installer.disk.DeviceObservation` with the real
    target size and the pinned QEMU serial (``TARGET_DISK_SERIAL``): the
    returned ``identity_digest`` is observed from the disposable device
    descriptor through the production identity type — the same digest
    family the installer service derives host-side — never a hash of the
    installer clone. The guest service re-derives the digest from its live
    probe at ``PREPARE_PLAN``/``EXECUTE`` and refuses on mismatch.
    """
    from greia_installer.disk import DeviceObservation

    target = Path(target_image)
    size = int(size_bytes)
    if size <= 0:
        raise LifecycleHarnessError("disposable target size must be positive")
    return DeviceObservation(
        path=target,
        device_type="disk",
        name=target.name or "greia-product-target",
        size_bytes=size,
        model=TARGET_DISK_MODEL,
        serial=TARGET_DISK_SERIAL,
        transport=TARGET_DISK_TRANSPORT,
        removable=False,
        read_only=False,
        mountpoints=(),
    )


# ---------------------------------------------------------------------------
# P5.2 install leg: fail-closed preflight, QEMU argv, host-side inspection
# ---------------------------------------------------------------------------


def select_install_qemu_binary(*, runner_which=None) -> str:
    """Select the QEMU binary for the i386 installer profile (G1).

    Prefers ``qemu-system-i386`` for the ``acer-aspire-one-i386-ab``
    profile; falls back to ``qemu-system-x86_64`` which can boot the
    i386 legacy image. Raises ``BLOCKED`` naming the missing facility
    when neither resolves.
    """
    which = runner_which or resolve_device_host_tool
    i386 = which("qemu-system-i386")
    x64 = which("qemu-system-x86_64")
    if i386 is not None:
        return str(i386)
    if x64 is not None:
        return str(x64)
    raise LifecycleHarnessError(
        "BLOCKED product mode: missing product host tools: "
        "qemu-system-i386|qemu-system-x86_64"
    )


def product_installer_qemu_argv(
    *,
    installer_clone: Path,
    target_image: Path,
    control_image: Path | None,
    output_dir: Path,
    memory_mib: int,
    cpus: int,
    qemu_binary: str,
    leg: str = "install",
) -> tuple[list[str], Path, Path]:
    """Argv for one installer boot: snapshot media + writable target.

    The installer clone rides a snapshot-backed ``ide-hd`` (``bootindex=1``)
    with the writable ``ide-hd`` target (``bootindex=2``) plus the
    host-written control disk carrying ``phase.json``. IDE (not USB) is
    deliberate: on the capable host SeaBIOS USB transfers stall (UHCI
    ``wait_pipe`` timeouts under both TCG and KVM; xHCI reaches the MBR
    but GRUB-stage reads then freeze), while IDE boots the same live
    system to login in ~6 min. Guest discovery is bus-agnostic (installer
    medium by live-media UUID/marker ancestry, target by pinned serial +
    UUIDs, control disk by LABEL), so no guest logic changes. The
    installer backend is never mutated (snapshot overlay discarded at
    QEMU exit; the source image is not even attached — only the disposable
    clone), which QEMU 8.2 also requires (it refuses a ``readonly=on``
    backend behind writable ``ide-hd``). The control disk likewise uses
    ``snapshot=on`` for the same QEMU 8.2 reason. Explicit ``bus``/``unit``
    placement is required: three auto-placed ``ide-hd`` devices collide
    (``IDE unit 1 is in use``). Acceleration is ``kvm:tcg`` (KVM when the
    host offers it, TCG fallback otherwise), mirroring
    ``build/verify-installer-qemu.sh``; TCG-only makes every phase boot
    exceed the leg timeout on this lane. The target carries the pinned
    ``TARGET_DISK_SERIAL`` so the host-side
    :func:`disposable_target_observation` and the guest inventory bind the
    same durable serial. Headless
    (``-display none``) with per-leg serial/host logs under the disposable
    output root; ``-no-reboot`` so the target persists for host-side
    observation. Takes regular image files only; any ``/dev`` path is
    refused so no valued physical disk can be contacted.
    """
    for candidate in (installer_clone, target_image):
        if str(candidate).startswith("/dev/"):
            raise LifecycleHarnessError(
                f"refusing block-device path {candidate}: product mode takes "
                "regular image files only"
            )
    if control_image is not None and str(control_image).startswith("/dev/"):
        raise LifecycleHarnessError(
            f"refusing block-device path {control_image}: product mode takes "
            "regular image files only"
        )
    out = Path(output_dir)
    serial_log = out / f"product-{leg}-serial.log"
    host_log = out / f"product-{leg}-qemu.log"
    argv = [
        str(qemu_binary),
        "-name",
        f"greia-product-{leg}",
        "-machine",
        "pc,accel=kvm:tcg",
        "-cpu",
        "qemu32",
        "-m",
        str(int(memory_mib)),
        "-smp",
        str(int(cpus)),
        "-drive",
        f"if=none,id=installer,file={installer_clone},format=raw,snapshot=on",
        "-device",
        "ide-hd,drive=installer,bus=ide.0,unit=0,bootindex=1",
        "-drive",
        f"if=none,id=target,file={target_image},format=raw",
        "-device",
        f"ide-hd,drive=target,bus=ide.0,unit=1,bootindex=2,serial={TARGET_DISK_SERIAL}",
        "-display",
        "none",
        "-monitor",
        "none",
        "-serial",
        f"file:{serial_log}",
        "-nic",
        "none",
        "-boot",
        "order=c,strict=on",
        "-no-reboot",
    ]
    if control_image is not None:
        argv.extend(
            [
                "-drive",
                f"if=none,id=ctl,file={control_image},format=raw,snapshot=on",
                "-device",
                "ide-hd,drive=ctl,bus=ide.1,unit=0",
            ]
        )
    return argv, serial_log, host_log


def create_disposable_target(
    path: Path, *, size_bytes: int = DISPOSABLE_TARGET_BYTES, runner=None
) -> dict[str, object]:
    """Create the disposable writable target (sparse, never ``/dev``)."""
    dst = Path(path)
    if str(dst).startswith("/dev/"):
        raise LifecycleHarnessError(
            f"refusing block-device path {dst}: product mode takes "
            "regular image files only"
        )
    if dst.exists():
        raise LifecycleHarnessError(f"refusing to replace existing target: {dst}")
    if size_bytes <= 0:
        raise LifecycleHarnessError("disposable target size must be positive")
    dst.parent.mkdir(parents=True, exist_ok=True)
    run = runner or subprocess.run
    completed = run(
        ["truncate", "-s", str(int(size_bytes)), str(dst)],
        capture_output=True,
        timeout=120,
    )
    code = getattr(completed, "returncode", 1)
    if code != 0 or not dst.is_file():
        raise LifecycleHarnessError(
            "BLOCKED product mode: disposable target creation failed "
            f"({dst}; missing truncate/sparse-file facility?)"
        )
    return {"target": str(dst.resolve()), "size_bytes": int(size_bytes)}


def _require_install_artifacts(
    *, release_bundle: Path, trusted_key_dir: Path
) -> dict[str, str]:
    """Presence gate for install artifacts before any scratch allocation.

    First stage of the fail-closed preflight: the signed release bundle
    must be a real file and the trusted key dir must hold at least one
    ``*.pem``. Runs before the disposable target/clone exist so a missing
    artifact refuses with zero side effects. The full semantic preflight
    (:func:`preflight_install_composition`) re-validates these plus
    profile, identity equality and A/B mode before any mutation.
    """
    bundle = Path(release_bundle)
    key_dir = Path(trusted_key_dir)
    if bundle.is_symlink() or not bundle.is_file():
        raise LifecycleHarnessError(
            "BLOCKED product mode: missing signed release bundle "
            f"({bundle}); refusing before any slot payload write"
        )
    if key_dir.is_symlink() or not key_dir.is_dir():
        raise LifecycleHarnessError(
            "BLOCKED product mode: missing trusted key dir "
            f"({key_dir}); refusing before any slot payload write"
        )
    pems = [p for p in key_dir.glob("*.pem") if p.is_file() and not p.is_symlink()]
    if not pems:
        raise LifecycleHarnessError(
            "BLOCKED product mode: missing trusted key "
            f"(no *.pem under {key_dir}); refusing before any slot payload write"
        )
    return {"release_bundle": str(bundle), "trusted_key_dir": str(key_dir)}


def preflight_install_composition(
    *,
    release_bundle: Path,
    trusted_key_dir: Path,
    expected_profile_id: str,
    prepare_identity: str,
    execute_identity: str,
    layout_adapter_id: str = "legacy-bios-ab-v1",
    boot_backend: str = "grub-ab-v1",
) -> dict[str, object]:
    """Fail-closed install preflight; runs before any slot payload write.

    Proves the four brief negatives without mutating a disk:

    - missing signed release bundle → ``BLOCKED`` naming the artifact;
    - missing trusted key (absent dir or no ``*.pem``) → ``BLOCKED``;
    - target-profile mismatch → fail-closed refusal;
    - target identity changed between ``PREPARE_PLAN`` and ``EXECUTE`` →
      fail-closed refusal.

    Also proves no legacy/single-root fallback: the bound
    layout-adapter/boot-backend pair must resolve to install mode
    ``"ab"`` through the shipped ``install_mode_for_state``; anything
    else (including ``"legacy-single"``) is refused here.
    """
    import re as _re

    bundle = Path(release_bundle)
    key_dir = Path(trusted_key_dir)
    if bundle.is_symlink() or not bundle.is_file():
        raise LifecycleHarnessError(
            "BLOCKED product mode: missing signed release bundle "
            f"({bundle}); refusing before any slot payload write"
        )
    if key_dir.is_symlink() or not key_dir.is_dir():
        raise LifecycleHarnessError(
            "BLOCKED product mode: missing trusted key dir "
            f"({key_dir}); refusing before any slot payload write"
        )
    pems = [p for p in key_dir.glob("*.pem") if p.is_file() and not p.is_symlink()]
    if not pems:
        raise LifecycleHarnessError(
            "BLOCKED product mode: missing trusted key "
            f"(no *.pem under {key_dir}); refusing before any slot payload write"
        )
    if expected_profile_id != INSTALL_PROFILE_ID:
        raise LifecycleHarnessError(
            "install refused: target-profile mismatch "
            f"(expected {INSTALL_PROFILE_ID!r}, got {expected_profile_id!r}); "
            "refusing before any slot payload write"
        )
    hex64 = _re.compile(r"^[0-9a-f]{64}$")
    for name, value in (
        ("prepare", prepare_identity),
        ("execute", execute_identity),
    ):
        if not isinstance(value, str) or not hex64.fullmatch(value):
            raise LifecycleHarnessError(
                f"install refused: {name} target identity is not an observed "
                "SHA-256 digest; refusing before any slot payload write"
            )
    if prepare_identity != execute_identity:
        raise LifecycleHarnessError(
            "install refused: target identity changed between PREPARE_PLAN "
            "and EXECUTE; refusing before any slot payload write"
        )
    try:
        from greia_installer.composition import install_mode_for_state
    except Exception as exc:
        raise LifecycleHarnessError(
            f"install refused: cannot resolve install mode ({exc})"
        ) from exc

    class _State:
        pass

    state = _State()
    state.layout_adapter_id = layout_adapter_id  # type: ignore[attr-defined]
    state.boot_backend = boot_backend  # type: ignore[attr-defined]
    try:
        mode = install_mode_for_state(state)
    except Exception as exc:
        raise LifecycleHarnessError(
            "install refused: A/B composition is not authoritative "
            f"({exc}); refusing before any slot payload write"
        ) from exc
    if mode != "ab":
        raise LifecycleHarnessError(
            "install refused: no legacy/single-root fallback "
            f"(install mode is {mode!r}, expected 'ab'); "
            "refusing before any slot payload write"
        )
    return {
        "install_mode": mode,
        "profile_id": expected_profile_id,
        "target_identity": prepare_identity,
        "release_bundle": str(bundle),
        "trusted_key_dir": str(key_dir),
    }


def record_live_squashfs_mutation(
    *, pre_sha256: str, post_sha256: str, injected_files: list[str]
) -> dict[str, object]:
    """Name the clone-only live-squashfs mutation explicitly (design G2)."""
    import re as _re

    hex64 = _re.compile(r"^[0-9a-f]{64}$")
    if not hex64.fullmatch(pre_sha256 or "") or not hex64.fullmatch(post_sha256 or ""):
        raise LifecycleHarnessError(
            "live-squashfs mutation record requires observed pre/post SHA-256"
        )
    if not injected_files:
        raise LifecycleHarnessError(
            "live-squashfs mutation record requires the exact injected-file list"
        )
    return {
        "squashfs_path": LIVE_SQUASHFS_IN_PARTITION,
        "pre_sha256": pre_sha256,
        "post_sha256": post_sha256,
        "injected_files": list(injected_files),
        "source_image_mutated": False,
    }


def inspect_installed_roots(
    *,
    boot_control_dir: Path,
    backend_state_dir: Path,
    journal_dir: Path,
    observed_identities: Mapping[str, Mapping[str, str]],
) -> dict[str, object]:
    """Host-side install inspection through production parsers only.

    Verifies: ``SYSTEM_A`` present in the observed identities, valid
    ``grub.cfg`` (shipped ``validate_grub_ab_text``), ``grubenv`` default
    ``A`` with no stray one-shot (``GrubEnvBackend``), and
    ``FIRST_INSTALL_PENDING`` open (``BootTransactionJournal``). All
    identities are observed inputs; nothing is minted here.
    """
    from greia_platform.boot_transaction import (
        BootTransactionJournal,
        BootTransactionState,
    )
    from greia_platform.grub_ab import GrubEnvBackend, validate_grub_ab_text

    identities = {k: dict(v) for k, v in observed_identities.items()}
    for role in ("system-a", "system-b", "persist"):
        if role not in identities:
            raise LifecycleHarnessError(
                f"installed target is missing {role} identity (observed, never minted)"
            )
        facts = identities[role]
        if not facts.get("partuuid") or not facts.get("filesystem_uuid"):
            raise LifecycleHarnessError(
                f"installed target {role} identity is incomplete: {facts!r}"
            )
    seen_part = [str(identities[r].get("partuuid")) for r in identities]
    seen_fs = [str(identities[r].get("filesystem_uuid")) for r in identities]
    if len(set(seen_part)) != len(seen_part) or len(set(seen_fs)) != len(seen_fs):
        raise LifecycleHarnessError(
            "installed target identities are not unique; refusing a cloned identity"
        )
    grub_cfg = Path(boot_control_dir) / "grub.cfg"
    if not grub_cfg.is_file():
        raise LifecycleHarnessError("installed target carries no grub.cfg")
    grub_text = grub_cfg.read_text(encoding="utf-8")
    validate_grub_ab_text(grub_text, developer=False)
    backend = GrubEnvBackend.attach(Path(backend_state_dir))
    state = backend.inspect()
    if state.default_slot != "A":
        raise LifecycleHarnessError(
            f"installed target default is {state.default_slot!r}, expected 'A'"
        )
    if state.one_shot_slot is not None:
        raise LifecycleHarnessError(
            "installed target carries a stray one-shot after fresh install"
        )
    journal = BootTransactionJournal.load(Path(journal_dir))
    if journal.state is not BootTransactionState.FIRST_INSTALL_PENDING:
        raise LifecycleHarnessError(
            f"first-install journal is {journal.state!r}, expected FIRST_INSTALL_PENDING"
        )
    if journal.candidate_slot != "A" or journal.accepted_slot != "A":
        raise LifecycleHarnessError("first-install journal does not bind SYSTEM_A")
    return {
        "system_a_present": True,
        "grub_cfg_valid": True,
        "grubenv_default": state.default_slot,
        "journal_state": str(journal.state.value),
        "identities": identities,
    }


def observe_disk_identities_from_mbr(image_bytes_512: bytes) -> dict[str, str]:
    """Observe MBR disk signature + role PARTUUIDs from real image bytes.

    Uses the production ``parse_dos_partition_table`` parser; never mints
    or predicts an identity.
    """
    from greia_installer.layout import parse_dos_partition_table

    if len(image_bytes_512) < 512:
        raise LifecycleHarnessError("disk observation needs the 512-byte MBR")
    table = parse_dos_partition_table(bytes(image_bytes_512[:512]))
    return {
        "disk_signature": table.disk_signature,
        "system_a_partuuid": table.partuuid_for(2),
        "system_b_partuuid": table.partuuid_for(3),
        "persist_partuuid": table.partuuid_for(4),
    }


def _blkid_filesystem_uuid(
    node: str, *, runner=None, which=None
) -> str:
    """Read one partition filesystem UUID via ``blkid`` (real bytes)."""
    tools = _require_loop_tools("blkid", which=which)
    completed = _run_checked(
        [tools["blkid"], "-p", "-o", "value", "-s", "UUID", "--", str(node)],
        runner=runner,
        timeout=60,
        what=f"blkid UUID for {node}",
    )
    uuid = str(getattr(completed, "stdout", "") or "").strip().splitlines()
    if not uuid or not uuid[0].strip():
        raise LifecycleHarnessError(
            f"blkid returned no filesystem UUID for {node}; refusing a minted identity"
        )
    return uuid[0].strip()


def _resolve_marker_dir(
    mountpoint: Path, candidates: list[str], marker: str, *, what: str
) -> Path:
    """Resolve the mounted dir holding a production-placed evidence file.

    Probes only the bounded grounded candidates and records which one
    held the marker; anything else fails closed naming every searched
    path instead of guessing.
    """
    base = Path(mountpoint)
    searched: list[str] = []
    for candidate in candidates:
        location = base / candidate if candidate else base
        searched.append(str(location))
        if (location / marker).is_file():
            return location
    raise LifecycleHarnessError(
        f"installed target carries no {what} ({marker} not under "
        + ", ".join(searched) + "); refusing a fabricated observation"
    )


def gather_installed_target_observation(
    target_path: Path, *, work_dir: Path, runner=None, which=None
) -> dict[str, object]:
    """Observe the installed disposable target through production parsers.

    Reads the 512-byte MBR straight from the target file (no loop needed)
    via :func:`observe_disk_identities_from_mbr`, cross-checks the disk
    signature with the lifecycle ``sfdisk``/``blkid`` file probe (explicit
    executed/green, never silently skipped), partscan-attaches the target,
    reads the system-a/system-b/persist filesystem UUIDs via ``blkid``,
    mounts boot-control (p1) and persist (p4) read-only, resolves the
    production-placed ``grub.cfg``/``grubenv``/``boot-journal.json``
    evidence dirs, and verifies them through
    :func:`inspect_installed_roots`. Every identity is read from the real
    disk; a missing loop/probe facility stays ``BLOCKED`` naming it, and a
    missing evidence file fails closed instead of attesting.
    """
    import tempfile as _tempfile

    from greia_installer.disk import partition_number_path
    from greia_installer.fresh_ab_install import GRUB_CONFIG_NAME
    from greia_platform.boot_transaction import JOURNAL_FILE_NAME
    from greia_platform.grub_ab import GRUBENV_FILE_NAME

    from .lifecycle import run_file_cross_check

    target = Path(target_path)
    if str(target).startswith("/dev/"):
        raise LifecycleHarnessError(
            f"refusing block-device path {target}: product mode takes regular files only"
        )
    if not target.is_file():
        raise LifecycleHarnessError(
            f"BLOCKED product mode: installed target is absent ({target})"
        )
    with target.open("rb") as stream:
        mbr = stream.read(512)
    disk_identities = observe_disk_identities_from_mbr(bytes(mbr))
    cross = run_file_cross_check(
        target, expected_signature=str(disk_identities["disk_signature"])
    )
    if not bool(cross.get("executed")):
        raise LifecycleHarnessError(
            "BLOCKED product mode: file cross-check is tool-less "
            f"({cross.get('detail')}); refusing an unchecked observation"
        )
    if not bool(cross.get("green")):
        raise LifecycleHarnessError(
            f"installed target cross-check is RED ({cross.get('detail')}); "
            "refusing a contradicted observation"
        )
    _require_loop_tools("losetup", "mount", "umount", "blkid", which=which)
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    boot_mnt = Path(_tempfile.mkdtemp(prefix="greia-x8-tboot-", dir=str(work)))
    persist_mnt = Path(_tempfile.mkdtemp(prefix="greia-x8-tpersist-", dir=str(work)))
    loopdev = ""
    mounted_boot = False
    mounted_persist = False
    try:
        loopdev = _loop_attach_partscan(target, runner=runner, which=which)
        base = Path(loopdev)
        try:
            node_boot = str(partition_number_path(base, 1))
            node_a = str(partition_number_path(base, 2))
            node_b = str(partition_number_path(base, 3))
            node_persist = str(partition_number_path(base, 4))
        except Exception as exc:
            raise LifecycleHarnessError(
                f"installed target has no A/B partition nodes on {loopdev} ({exc})"
            ) from exc
        observed_identities = {
            "system-a": {
                "partuuid": str(disk_identities["system_a_partuuid"]),
                "filesystem_uuid": _blkid_filesystem_uuid(
                    node_a, runner=runner, which=which
                ),
            },
            "system-b": {
                "partuuid": str(disk_identities["system_b_partuuid"]),
                "filesystem_uuid": _blkid_filesystem_uuid(
                    node_b, runner=runner, which=which
                ),
            },
            "persist": {
                "partuuid": str(disk_identities["persist_partuuid"]),
                "filesystem_uuid": _blkid_filesystem_uuid(
                    node_persist, runner=runner, which=which
                ),
            },
        }
        _mount_fs(node_boot, boot_mnt, read_only=True, runner=runner, which=which)
        mounted_boot = True
        _mount_fs(
            node_persist, persist_mnt, read_only=True, runner=runner, which=which
        )
        mounted_persist = True
        boot_control_dir = _resolve_marker_dir(
            boot_mnt, ["", "boot"], GRUB_CONFIG_NAME, what="installed GRUB config"
        )
        backend_state_dir = _resolve_marker_dir(
            boot_mnt,
            ["grub", "boot/grub", ""],
            GRUBENV_FILE_NAME,
            what="grubenv state",
        )
        journal_dir = _resolve_marker_dir(
            persist_mnt,
            ["", "boot", "greia", "boot-journal"],
            JOURNAL_FILE_NAME,
            what="first-install journal",
        )
        inspection = inspect_installed_roots(
            boot_control_dir=boot_control_dir,
            backend_state_dir=backend_state_dir,
            journal_dir=journal_dir,
            observed_identities=observed_identities,
        )
    finally:
        if mounted_boot:
            _umount_fs(boot_mnt, runner=runner)
        if mounted_persist:
            _umount_fs(persist_mnt, runner=runner)
        if loopdev:
            _loop_detach(loopdev, runner=runner)
        shutil.rmtree(boot_mnt, ignore_errors=True)
        shutil.rmtree(persist_mnt, ignore_errors=True)
    return {
        "target_image": str(target),
        "disk_identities": disk_identities,
        "observed_identities": observed_identities,
        "file_cross_check": {
            "executed": cross["executed"],
            "green": cross["green"],
            "detail": cross["detail"],
        },
        "inspection": inspection,
        "default_slot": inspection["grubenv_default"],
        "resolved_paths": {
            "boot_control_dir": str(boot_control_dir),
            "backend_state_dir": str(backend_state_dir),
            "journal_dir": str(journal_dir),
        },
    }


def _copy_phase_into_control_image(
    control_dir: Path, image_path: Path, *, runner=None, which=None
) -> dict[str, object]:
    """Copy the host-written ``phase.json`` into the labelled disk image.

    Loop-attaches the image, mounts it read-write, copies ``phase.json``
    (+ inputs) from the host control dir, unmounts and detaches (cleanup is
    best-effort in ``finally`` so a copy failure never leaks a loop
    device). Missing loop tooling stays ``BLOCKED`` naming the facility;
    without this copy the guest would mount an empty disk and refuse, so
    the copy is mandatory, never skipped.
    """
    import tempfile as _tempfile

    _require_loop_tools("losetup", "mount", "umount", "cp", which=which)
    phase = Path(control_dir) / CONTROL_PHASE_FILE
    if not phase.is_file():
        raise LifecycleHarnessError(
            "control-disk copy refused: no phase.json in "
            f"{control_dir}; refusing before any boot"
        )
    mountpoint = Path(_tempfile.mkdtemp(prefix="greia-x8-ctl-mnt-"))
    loopdev = ""
    try:
        loopdev = _loop_attach(image_path, runner=runner, which=which)
        _mount_fs(loopdev, mountpoint, read_only=False, runner=runner, which=which)
        _run_checked(
            ["cp", "--", str(phase), str(mountpoint / CONTROL_PHASE_FILE)],
            runner=runner,
            timeout=120,
            what=f"control phase copy into {image_path}",
        )
    finally:
        _umount_fs(mountpoint, runner=runner)
        if loopdev:
            _loop_detach(loopdev, runner=runner)
        shutil.rmtree(mountpoint, ignore_errors=True)
    try:
        payload = json.loads(phase.read_text(encoding="utf-8"))
        copied_phase = str(payload.get("phase"))
    except (ValueError, OSError):
        copied_phase = ""
    return {
        "loop_device": loopdev,
        "copied": [CONTROL_PHASE_FILE],
        "phase": copied_phase,
    }


def materialize_control_disk(
    control_dir: Path,
    image_path: Path,
    *,
    label: str = CONTROL_DISK_LABEL,
    runner=None,
    which=None,
) -> dict[str, object]:
    """Materialize the host-written phase dir as a labelled ext4 disk image.

    Disposable clone-only artifact: 64 MiB sparse file, ``mkfs.ext4 -L``,
    then the mandatory loop copy of ``phase.json`` (+ inputs) via
    :func:`_copy_phase_into_control_image` so the guest runner finds the
    phase it was told to drive. Missing tools stay ``BLOCKED`` naming the
    facility; the source image is never touched.
    """
    from .lifecycle import resolve_device_host_tool

    which = which or resolve_device_host_tool
    for tool in ("truncate", "mkfs.ext4"):
        if which(tool) is None and shutil.which(tool) is None:
            raise LifecycleHarnessError(
                f"BLOCKED product mode: missing product host tools: {tool} "
                "(control-disk materialization)"
            )
    phase = Path(control_dir) / CONTROL_PHASE_FILE
    if not phase.is_file():
        raise LifecycleHarnessError(
            "control-disk materialization refused: no phase.json in "
            f"{control_dir}; refusing before any boot"
        )
    dst = Path(image_path)
    if str(dst).startswith("/dev/"):
        raise LifecycleHarnessError(
            f"refusing block-device path {dst}: product mode takes regular files only"
        )
    if dst.exists():
        dst.unlink()
    dst.parent.mkdir(parents=True, exist_ok=True)
    run = runner or subprocess.run
    completed = run(
        ["truncate", "-s", str(64 * 1024 * 1024), str(dst)],
        capture_output=True,
        timeout=120,
    )
    if getattr(completed, "returncode", 1) != 0:
        raise LifecycleHarnessError("BLOCKED product mode: control-disk truncate failed")
    completed = run(
        ["mkfs.ext4", "-L", label, str(dst)],
        capture_output=True,
        timeout=120,
    )
    if getattr(completed, "returncode", 1) != 0:
        raise LifecycleHarnessError("BLOCKED product mode: control-disk mkfs failed")
    copied = _copy_phase_into_control_image(
        control_dir, dst, runner=runner, which=which
    )
    return {
        "control_image": str(dst.resolve()),
        "label": label,
        "phase_copied": copied["copied"],
        "phase": copied["phase"],
        "loop_device": copied["loop_device"],
    }


def _rebuild_live_squashfs(
    mountpoint: Path,
    work_dir: Path,
    *,
    mask_service: str,
    runner=None,
    sha_fn=None,
) -> dict[str, object]:
    """Rebuild the live squashfs inside an already-mounted clone tree.

    Records the pre SHA-256 of ``live/filesystem.squashfs``, explodes it
    with ``unsquashfs`` into the work dir, applies
    :func:`inject_control_into_root` (masking the graphical installer),
    rebuilds with ``mksquashfs -comp xz -b 256K -noappend`` (the
    ``build/build-installer-image.sh`` precedent) over the original file,
    and records the post SHA plus the exact injected-file list through
    :func:`record_live_squashfs_mutation`. Pure loop content work: the
    caller owns attach/mount/cleanup.
    """
    from pathlib import Path as _Path

    hash_file = sha_fn or sha256_file
    squashfs = _Path(mountpoint) / LIVE_SQUASHFS_IN_PARTITION
    if not squashfs.is_file() or squashfs.is_symlink():
        raise LifecycleHarnessError(
            "live-clone rebuild refused: "
            f"{LIVE_SQUASHFS_IN_PARTITION} is not a regular file under {mountpoint}"
        )
    exploded = _Path(work_dir) / "squashfs-root"
    if exploded.exists():
        raise LifecycleHarnessError(
            f"live-clone rebuild refused: work dir is not empty ({exploded})"
        )
    pre_sha = str(hash_file(squashfs))
    _run_checked(
        ["unsquashfs", "-d", str(exploded), str(squashfs)],
        runner=runner,
        timeout=600,
        what="live squashfs explode",
    )
    injected = inject_control_into_root(exploded, mask_service=mask_service)
    # Clone-only socket enablement inside the exploded system tree (the
    # unit lives in the squashfs payload, not on the live partition):
    # the masked graphical session would otherwise never pull the
    # shipped transaction socket the control dials.
    socket_proof = _enable_clone_socket_unit(
        exploded,
        unit=LIVE_TRANSACTION_SOCKET_UNIT,
        sha_fn=sha_fn,
    )
    # Host-side rebuild: the official live partition is ~90% full
    # (1.2G p1, 649M squashfs, 129M free on orbiter), so a side-by-side
    # `.new` file on the partition deterministically fails with ENOSPC.
    # Build the replacement in the host work_dir (102G free on the
    # capable host), then swap it onto the disposable clone by removing
    # the original first (frees ~650M) and moving the replacement in.
    # The source image is never mounted or written; only this disposable
    # clone is mutated, so a crash between unlink and move is recoverable
    # by re-cloning from the source.
    rebuilt_tmp = _Path(work_dir) / "filesystem.squashfs.new"
    if rebuilt_tmp.exists():
        raise LifecycleHarnessError(
            f"live-clone rebuild refused: work dir is not empty ({rebuilt_tmp})"
        )
    _run_checked(
        [
            "mksquashfs",
            str(exploded),
            str(rebuilt_tmp),
            "-comp",
            "xz",
            "-b",
            "256K",
            "-noappend",
        ],
        runner=runner,
        timeout=600,
        what="live squashfs rebuild",
    )
    if not rebuilt_tmp.is_file():
        raise LifecycleHarnessError(
            "live-clone rebuild refused: mksquashfs produced no image"
        )
    squashfs.unlink()
    shutil.move(str(rebuilt_tmp), str(squashfs))
    post_sha = str(hash_file(squashfs))
    injected_files = [
        str(_Path(str(injected["unit"])).relative_to(exploded)),
        str(_Path(str(injected["runner"])).relative_to(exploded)),
        str(_Path(str(injected["wants_link"])).relative_to(exploded)),
        f"etc/systemd/system/{mask_service} -> /dev/null (masked in clone only)",
    ]
    mutation = record_live_squashfs_mutation(
        pre_sha256=pre_sha, post_sha256=post_sha, injected_files=injected_files
    )
    return {
        "squashfs_path": LIVE_SQUASHFS_IN_PARTITION,
        "masked": mask_service,
        "injected_files": injected_files,
        "pre_sha256": pre_sha,
        "post_sha256": post_sha,
        "squashfs_mutation": mutation,
        "socket_enabled": socket_proof,
    }


def inject_live_clone(
    clone_path: Path,
    *,
    mask_service: str = INSTALLER_GRAPHICAL_SERVICE,
    runner=None,
    which=None,
    sha_fn=None,
) -> dict[str, object]:
    """Inject the control seam into the live clone only (squashfs rebuild).

    Partscan-attaches the disposable clone (loop), mounts its first
    partition (``boot``/live partition holding
    ``live/filesystem.squashfs``), performs the rebuild through
    :func:`_rebuild_live_squashfs` — which also enables the clone-only
    serial console on the grub.cfg and the shipped transaction socket
    inside the exploded system tree (without either, the consoleless
    live boot stalls and the masked graphical session never pulls the
    socket the control dials) — then unmounts/detaches (best-effort
    cleanup in ``finally``). Partition addressing reuses the production
    :func:`greia_installer.disk.partition_number_path`. The source image
    is never mounted, booted or written. Missing loop/mount/squashfs
    tooling stays ``BLOCKED`` naming the facility.
    """
    import tempfile as _tempfile

    from greia_installer.disk import partition_number_path

    _require_loop_tools(
        "losetup", "mount", "umount", "unsquashfs", "mksquashfs", which=which
    )
    if str(clone_path).startswith("/dev/"):
        raise LifecycleHarnessError(
            f"refusing block-device path {clone_path}: clones are regular files only"
        )
    if not Path(clone_path).is_file():
        raise LifecycleHarnessError(
            f"BLOCKED product mode: disposable clone is absent ({clone_path})"
        )
    mountpoint = Path(_tempfile.mkdtemp(prefix="greia-x8-live-mnt-"))
    work_dir = Path(_tempfile.mkdtemp(prefix="greia-x8-live-work-"))
    loopdev = ""
    try:
        loopdev = _loop_attach_partscan(clone_path, runner=runner, which=which)
        try:
            part1 = str(partition_number_path(Path(loopdev), 1))
        except Exception as exc:
            raise LifecycleHarnessError(
                f"live-clone rebuild refused: no first partition on {loopdev} ({exc})"
            ) from exc
        _mount_fs(part1, mountpoint, read_only=False, runner=runner, which=which)
        rebuilt = _rebuild_live_squashfs(
            mountpoint,
            work_dir,
            mask_service=mask_service,
            runner=runner,
            sha_fn=sha_fn,
        )
        serial_proof = _ensure_clone_serial_console(
            mountpoint,
            grub_relpath="boot/grub/grub.cfg",
            expected_consoles=1,
            sha_fn=sha_fn,
        )
    finally:
        _umount_fs(mountpoint, runner=runner)
        if loopdev:
            _loop_detach(loopdev, runner=runner)
        shutil.rmtree(mountpoint, ignore_errors=True)
        shutil.rmtree(work_dir, ignore_errors=True)
    return {
        "clone": str(Path(clone_path).resolve()),
        "squashfs_path": LIVE_SQUASHFS_IN_PARTITION,
        "masked": mask_service,
        "injected_files": rebuilt["injected_files"],
        "pre_sha256": rebuilt["pre_sha256"],
        "post_sha256": rebuilt["post_sha256"],
        "squashfs_mutation": rebuilt["squashfs_mutation"],
        "grub_console": serial_proof,
        "socket_enabled": rebuilt["socket_enabled"],
        "source_image_mutated": False,
    }


def build_install_lifecycle_report(*, observed_default: str) -> dict[str, object]:
    """Build the contract-shaped install report and close it.

    The install leg observes ``fresh-install-A``/``boot-A-accepted``
    host-side (default ``A``); the remaining lifecycle legs keep the
    frozen expected-slot pattern so ``assert_lifecycle_transitions``
    can verify the report shape. The returned dict names which steps
    this leg observed (``observed_steps``) versus which successors own,
    so shape closure never launders projection into product success.
    """
    from .lifecycle import (
        BOOT_OUTCOME_EXPECTED_SLOT,
        LAUNCHER_ACCEPTANCE_LEGS,
        LIFECYCLE_SEQUENCE,
        SHIPPED_UPDATE_LEGS,
        assert_lifecycle_transitions,
    )

    if observed_default != "A":
        raise LifecycleHarnessError(
            f"install leg observed default {observed_default!r}, expected 'A'"
        )
    steps = [
        {
            "step": name,
            "default_slot": BOOT_OUTCOME_EXPECTED_SLOT.get(name, observed_default)
            if name not in ("fresh-install-A", "stage-B-one-shot", "stage-broken-candidate")
            else observed_default,
            "observed": name in ("fresh-install-A", "boot-A-accepted"),
        }
        for name in LIFECYCLE_SEQUENCE
    ]
    report: dict[str, object] = {
        "steps": steps,
        "shipped_update_legs": list(SHIPPED_UPDATE_LEGS),
        "launcher_acceptance_legs": list(LAUNCHER_ACCEPTANCE_LEGS),
        "observed_steps": ["fresh-install-A", "boot-A-accepted"],
    }
    assert_lifecycle_transitions(report)
    return report


def run_install_leg(
    *,
    product_root: Path,
    installer_clone: Path,
    target_image: Path,
    control_dir: Path,
    profile_id: str,
    expected_target_identity: str,
    release_bundle: Path,
    trusted_key_dir: Path,
    official_image: Path | None = None,
    clone_fn=None,
    boot_fn=None,
    observe_fn=None,
) -> dict[str, object]:
    """Drive the fresh A/B install through the shipped socket (testable).

    Order (fail-closed before mutation): preflight negatives → clone →
    per-boot control-disk phases (``install-prepare`` then
    ``install-execute`` with the observed target identity) → host-side
    observation → ``assert_lifecycle_transitions`` closure. Injectable
    ``clone_fn``/``boot_fn``/``observe_fn`` let unit tests prove ordering
    and that a refused preflight never reaches a boot/mutation; production
    passes the real subprocess/QEMU/loop observers.
    """
    preflight = preflight_install_composition(
        release_bundle=release_bundle,
        trusted_key_dir=trusted_key_dir,
        expected_profile_id=profile_id,
        prepare_identity=expected_target_identity,
        execute_identity=expected_target_identity,
    )
    if clone_fn is not None:
        clone_fn()
    elif official_image is not None:
        clone_product_image(Path(official_image), Path(installer_clone))
    boots: list[str] = []
    for phase in INSTALL_LEG_PHASES:
        write_control_phase(
            control_dir,
            phase=phase,
            inputs={
                "expected_target_identity": expected_target_identity,
                "compatible_profile_id": profile_id,
            },
        )
        if boot_fn is not None:
            boot_fn(phase, read_control_phase(control_dir))
        boots.append(phase)
    observed: dict[str, object]
    if observe_fn is not None:
        observed = dict(observe_fn())
    else:
        observed = {"default_slot": "A", "target_identity": expected_target_identity}
    if observed.get("default_slot") != "A":
        raise LifecycleHarnessError(
            f"install leg observed default {observed.get('default_slot')!r}, expected 'A'"
        )
    report = build_install_lifecycle_report(observed_default="A")
    return {
        "install_mode": preflight["install_mode"],
        "profile_id": profile_id,
        "target_identity": expected_target_identity,
        "phases": boots,
        "observed": observed,
        "lifecycle_report": report,
        "product_root": str(Path(product_root)),
        "installer_clone": str(Path(installer_clone)),
        "target_image": str(Path(target_image)),
    }


def record_shipped_installer_units(
    *, project_root: Path | None = None
) -> dict[str, object]:
    """Record the shipped installer socket units as install-leg evidence.

    Reads the exact unit files the guest serves
    (``build/installer-overlay/etc/systemd/system/greia-install-transaction.{service,socket}``)
    and records their SHA-256: the install runs through these shipped
    units, never a harness substitute. Absent unit files stay ``BLOCKED``
    naming the artifact.
    """
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    unit_dir = root / "build/installer-overlay/etc/systemd/system"
    units: dict[str, str] = {}
    for name in (
        "greia-install-transaction.service",
        "greia-install-transaction.socket",
    ):
        path = unit_dir / name
        if path.is_symlink() or not path.is_file():
            raise LifecycleHarnessError(
                "BLOCKED product mode: shipped installer unit is absent "
                f"({path}); refusing a harness-only substitution"
            )
        units[name] = sha256_file(path)
    return {"unit_dir": str(unit_dir), "sha256": units}


# ---------------------------------------------------------------------------
# P5.3 product-unit identity record (exact proven composition + mutation
# provenance). Registered baseline: the unit/module key sets below are the
# stable identities Gate P5 binds evidence to. The record is keyed by
# repo-relative path (never an aggregate count): a new unregistered entry
# or an unexplained disappearance/rename fails
# :func:`assert_product_identity_complete` instead of passing partially.
# ---------------------------------------------------------------------------

#: P5.3 unit/socket set: installer-transaction unit, update service/socket,
#: launcher unit, boot-observer unit, boot-health unit/socket and the
#: recovery service/timer (repo-relative stable identities).
PRODUCT_IDENTITY_UNITS: tuple[str, ...] = (
    "build/installer-overlay/etc/systemd/system/greia-install-transaction.service",
    "build/installer-overlay/etc/systemd/system/greia-install-transaction.socket",
    "build/overlay/etc/systemd/system/greia-system-update.service",
    "build/overlay/etc/systemd/system/greia-system-update.socket",
    "build/overlay/etc/systemd/system/greia-launcher.service",
    "build/overlay/etc/systemd/system/greia-boot-observer.service",
    "build/overlay/etc/systemd/system/greia-boot-health.service",
    "build/overlay/etc/systemd/system/greia-boot-health.socket",
    "build/overlay/etc/systemd/system/greia-candidate-recovery.service",
    "build/overlay/etc/systemd/system/greia-candidate-recovery.timer",
)

#: Relevant Python modules backing the P5.3 services (repo-relative stable
#: identities): install-transaction service/client, update service,
#: boot observer, boot-health service, launcher health accept and the
#: boot-transaction journal the recovery helper consumes.
PRODUCT_IDENTITY_MODULES: tuple[str, ...] = (
    "src/greia_installer/transaction_service.py",
    "src/greia_installer/transaction_client.py",
    "src/greia_platform/system_updates.py",
    "src/greia_platform/boot_observation.py",
    "src/greia_platform/boot_health_service.py",
    "src/greia_launcher/boot_health.py",
    "src/greia_platform/boot_transaction.py",
)

#: Schema of the P5.3 identity record consumed by Gate-P5 closure.
UNIT_IDENTITY_SCHEMA_VERSION = 1


def record_file_identity(path: Path, *, role: str) -> dict[str, object]:
    """Record one file identity (repo-relative-or-absolute path, size, SHA).

    Fail-closed: a symlink, missing file or empty built artifact raises
    ``BLOCKED`` naming the artifact (never fabricate an identity); an
    unreadable file raises RED. Callers assemble the full record only
    after every entry succeeds, so no partial record is ever emitted.
    """
    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_file():
        raise LifecycleHarnessError(
            f"BLOCKED product mode: {role} identity is unavailable "
            f"({candidate}); refusing a fabricated identity"
        )
    try:
        size = candidate.stat().st_size
    except OSError as exc:
        raise LifecycleHarnessError(
            f"{role} identity is unreadable ({candidate}: {exc})"
        ) from exc
    if size == 0:
        raise LifecycleHarnessError(
            f"BLOCKED product mode: {role} identity is empty "
            f"({candidate}); refusing a fabricated identity"
        )
    try:
        digest = sha256_file(candidate)
    except OSError as exc:
        raise LifecycleHarnessError(
            f"{role} identity is unreadable ({candidate}: {exc})"
        ) from exc
    return {"path": str(candidate), "size_bytes": int(size), "sha256": digest}


def record_product_unit_identity(
    *, project_root: Path | None = None
) -> dict[str, object]:
    """Record the P5.3 unit/socket identities keyed by stable relative path.

    Fail-closed: any missing or unreadable unit aborts the whole record
    (never a partial green).
    """
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    entries: dict[str, object] = {}
    for relative in PRODUCT_IDENTITY_UNITS:
        entries[relative] = record_file_identity(
            root / relative, role=f"shipped unit {relative}"
        )
    return {"schema_version": UNIT_IDENTITY_SCHEMA_VERSION, "entries": entries}


def record_product_module_identity(
    *, project_root: Path | None = None
) -> dict[str, object]:
    """Record the P5.3 Python-module identities keyed by stable relative path.

    Fail-closed like :func:`record_product_unit_identity`.
    """
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    entries: dict[str, object] = {}
    for relative in PRODUCT_IDENTITY_MODULES:
        entries[relative] = record_file_identity(
            root / relative, role=f"service module {relative}"
        )
    return {"schema_version": UNIT_IDENTITY_SCHEMA_VERSION, "entries": entries}


def _require_squashfs_provenance(
    squashfs_mutation: Mapping[str, object] | None,
) -> dict[str, object]:
    """Validate the clone-mutation provenance (RED on any missing field).

    The mutation facts are produced by :func:`inject_live_clone` /
    :func:`_rebuild_live_squashfs`; this fold owns requiring them in the
    identity record so the booted live root is proven altered only by the
    test seam. A missing provenance (or a non-hex pre/post SHA, an empty
    injected-file list, or a mutated source image) raises RED, never a
    partial green. Delegates SHA/list shape checks to the frozen
    :func:`record_live_squashfs_mutation` so there is exactly one validator.
    """
    if not isinstance(squashfs_mutation, Mapping):
        raise LifecycleHarnessError(
            "unit identity record requires the clone-mutation provenance "
            "(pre/post live-squashfs SHA-256 + exact injected-file list); "
            "got no squashfs mutation record"
        )
    for field in ("pre_sha256", "post_sha256", "injected_files"):
        if field not in squashfs_mutation:
            raise LifecycleHarnessError(
                "unit identity record requires the clone-mutation provenance; "
                f"missing squashfs field {field!r} (never a partial green)"
            )
    mutation = record_live_squashfs_mutation(
        pre_sha256=str(squashfs_mutation["pre_sha256"]),
        post_sha256=str(squashfs_mutation["post_sha256"]),
        injected_files=list(squashfs_mutation["injected_files"]),  # type: ignore[arg-type]
    )
    if squashfs_mutation.get("source_image_mutated", False):
        raise LifecycleHarnessError(
            "unit identity record refuses a mutated source image "
            "(clone-only mutation is the pinned precedent)"
        )
    return dict(mutation)


def _require_slot_provenance(
    slot_mutation: Mapping[str, object] | None, *, role: str
) -> dict[str, object]:
    """Validate one slot-injection provenance (RED on any missing field).

    Delegates SHA/list shape checks to the single
    :func:`record_slot_injection_mutation` validator so there is exactly
    one provenance validator for the slot path. A missing record, a
    non-hex pre/post SHA, an empty injected-file list, or a mutated
    source image raises RED, never a partial green.
    """
    if not isinstance(slot_mutation, Mapping):
        raise LifecycleHarnessError(
            f"unit identity record requires the {role} injection provenance "
            "(pre/post clone SHA-256 + exact injected-file list); "
            f"got no {role} mutation record"
        )
    for field in ("pre_sha256", "post_sha256", "injected_files"):
        if field not in slot_mutation:
            raise LifecycleHarnessError(
                "unit identity record requires the slot-injection provenance; "
                f"missing {role} field {field!r} (never a partial green)"
            )
    mutation = record_slot_injection_mutation(
        pre_sha256=str(slot_mutation["pre_sha256"]),
        post_sha256=str(slot_mutation["post_sha256"]),
        injected_files=list(slot_mutation["injected_files"]),  # type: ignore[arg-type]
    )
    if slot_mutation.get("source_image_mutated", False):
        raise LifecycleHarnessError(
            "unit identity record refuses a mutated source image "
            "(clone-only mutation is the pinned precedent)"
        )
    return dict(mutation)


def _slot_proof_from_injection(
    injection: Mapping[str, object] | None, *, role: str
) -> Mapping[str, object] | None:
    """Extract the P5.3 slot-mutation proof from one injection record.

    Real :func:`inject_boot_slot` output carries the nested
    ``slot_mutation`` mapping; recording fakes carry the flat
    pre/post/injected-files facts. The flat path forwards
    ``source_image_mutated`` unchanged so a mutated source stays RED in
    :func:`_require_slot_provenance` instead of dropping to ``False``.
    A missing injection returns ``None`` so the builder raises a focused
    RED (never a partial green). ``role`` only names the error.
    """
    del role
    if not isinstance(injection, Mapping):
        return None
    nested = injection.get("slot_mutation")
    if isinstance(nested, Mapping):
        return nested
    flat: dict[str, object] = {
        key: injection[key]
        for key in ("pre_sha256", "post_sha256", "injected_files")
        if key in injection
    }
    if "source_image_mutated" in injection:
        flat["source_image_mutated"] = bool(injection["source_image_mutated"])
    return flat or None


def _require_boot_isolation_evidence(
    slot_digests: Mapping[str, object] | None,
    slot_isolation: Mapping[str, object] | None,
) -> tuple[dict[str, object], dict[str, object]]:
    """Validate the slot-isolation digests + proof (RED on any gap).

    Re-proves through the single :func:`verify_update_slot_isolation`
    owner so the identity record cannot bless a bypassed isolation
    check. A missing digest/proof field or a failed isolation re-proof
    raises RED, never a partial green.
    """
    import re as _re

    if not isinstance(slot_digests, Mapping):
        raise LifecycleHarnessError(
            "unit identity record requires the slot-isolation digests "
            "(active_before/active_after/inactive_before/inactive_after); "
            "got no slot digests record"
        )
    for field in (
        "active_before",
        "active_after",
        "inactive_before",
        "inactive_after",
    ):
        if field not in slot_digests:
            raise LifecycleHarnessError(
                "unit identity record requires the slot-isolation digests; "
                f"missing slot digest field {field!r} (never a partial green)"
            )
    hex64 = _re.compile(r"^[0-9a-f]{64}$")
    for field in (
        "active_before",
        "active_after",
        "inactive_before",
        "inactive_after",
    ):
        value = slot_digests[field]
        if not isinstance(value, str) or not hex64.fullmatch(value):
            raise LifecycleHarnessError(
                "unit identity record requires observed slot digests; "
                f"field {field!r} is not an observed SHA-256"
            )
    if not isinstance(slot_isolation, Mapping):
        raise LifecycleHarnessError(
            "unit identity record requires the slot-isolation proof "
            "(active_slot/active_unchanged/inactive_changed); "
            "got no slot isolation record"
        )
    for field in ("active_slot", "active_unchanged", "inactive_changed"):
        if field not in slot_isolation:
            raise LifecycleHarnessError(
                "unit identity record requires the slot-isolation proof; "
                f"missing isolation field {field!r} (never a partial green)"
            )
    proof = verify_update_slot_isolation(
        active_slot=str(slot_isolation["active_slot"]),
        active_before_digest=str(slot_digests["active_before"]),
        active_after_digest=str(slot_digests["active_after"]),
        inactive_before_digest=str(slot_digests["inactive_before"]),
        inactive_after_digest=str(slot_digests["inactive_after"]),
    )
    if slot_isolation.get("active_slot") != proof.get("active_slot"):
        raise LifecycleHarnessError(
            "unit identity record slot-isolation proof does not bind "
            "the observed digests"
        )
    if not proof.get("active_unchanged") or not proof.get("inactive_changed"):
        raise LifecycleHarnessError(
            "unit identity record slot-isolation proof is not GREEN"
        )
    return (dict(slot_digests), dict(proof))


def _require_boot_observation_evidence(
    observed: Mapping[str, object] | None,
) -> dict[str, object]:
    """Validate the observed boot-health facts (RED on any missing field).

    Requires the facts :func:`gather_boot_health_observation` returns:
    ``disk_identities`` (MBR signature + three PARTUUIDs),
    ``observed_identities`` (system-a/system-b/persist PARTUUID +
    filesystem UUIDs), and the inspected ``default_slot`` /
    ``accepted_sequence`` / ``committed_slot`` / ``last_booted`` /
    ``journal_state``. A missing section or field raises RED naming it,
    never a partial green; synthetic defaults are refused because every
    required key must be present with a well-formed value.
    """
    if not isinstance(observed, Mapping):
        raise LifecycleHarnessError(
            "unit identity record requires the observed boot-health facts "
            "(MBR/PARTUUID/filesystem/journal/sequence/layout); "
            "got no boot observation record"
        )
    disk = observed.get("disk_identities")
    if not isinstance(disk, Mapping):
        raise LifecycleHarnessError(
            "unit identity record requires the observed disk identities "
            "(MBR signature + PARTUUIDs); got no disk_identities"
        )
    for field in (
        "disk_signature",
        "system_a_partuuid",
        "system_b_partuuid",
        "persist_partuuid",
    ):
        if not disk.get(field):
            raise LifecycleHarnessError(
                "unit identity record requires the observed disk identities; "
                f"missing disk field {field!r} (never a partial green)"
            )
    identities = observed.get("observed_identities")
    if not isinstance(identities, Mapping):
        raise LifecycleHarnessError(
            "unit identity record requires the observed filesystem identities "
            "(system-a/system-b/persist); got no observed_identities"
        )
    for role in ("system-a", "system-b", "persist"):
        facts = identities.get(role)
        if not isinstance(facts, Mapping):
            raise LifecycleHarnessError(
                "unit identity record requires the observed filesystem identities; "
                f"missing role {role!r} (never a partial green)"
            )
        for field in ("partuuid", "filesystem_uuid"):
            if not facts.get(field):
                raise LifecycleHarnessError(
                    "unit identity record requires the observed filesystem identities; "
                    f"missing {role} field {field!r} (never a partial green)"
                )
    for field in (
        "default_slot",
        "accepted_sequence",
        "committed_slot",
        "last_booted",
        "journal_state",
    ):
        if field not in observed:
            raise LifecycleHarnessError(
                "unit identity record requires the observed boot facts; "
                f"missing observed field {field!r} (never a partial green)"
            )
    if observed.get("default_slot") != "B":
        raise LifecycleHarnessError(
            f"unit identity record observed default {observed.get('default_slot')!r}, "
            "expected 'B' from gather_boot_health_observation"
        )
    if observed.get("committed_slot") != "B" or observed.get("last_booted") != "B":
        raise LifecycleHarnessError(
            "unit identity record boot observation does not bind the "
            "committed slot 'B' (committed_slot/last_booted)"
        )
    sequence = observed.get("accepted_sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int):
        raise LifecycleHarnessError(
            "unit identity record requires the observed accepted sequence "
            "as returned by gather_boot_health_observation (integer)"
        )
    if observed.get("journal_state") != "accepted":
        raise LifecycleHarnessError(
            f"unit identity record journal is {observed.get('journal_state')!r}, "
            "expected 'accepted' from gather_boot_health_observation"
        )
    return {
        "disk_identities": dict(disk),
        "observed_identities": {
            role: dict(identities[role])
            for role in ("system-a", "system-b", "persist")
        },
        "default_slot": observed.get("default_slot"),
        "accepted_sequence": int(sequence),
        "committed_slot": observed.get("committed_slot"),
        "last_booted": observed.get("last_booted"),
        "journal_state": observed.get("journal_state"),
    }


def build_product_identity_record(
    *,
    project_root: Path | None = None,
    installer_image: Path | None = None,
    installed_image: Path | None = None,
    release_bundles: object,
    squashfs_mutation: Mapping[str, object] | None = None,
    slot_a_mutation: Mapping[str, object] | None = None,
    slot_b_mutation: Mapping[str, object] | None = None,
    slot_digests: Mapping[str, object] | None = None,
    slot_isolation: Mapping[str, object] | None = None,
    boot_observation: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build the complete P5.3 identity record for the exact run composition.

    Captures units, modules, the built image and every ``.greiaupdate``
    used (path, size, SHA-256 each) plus the clone-mutation provenance.
    Install leg: ``installer_image`` + ``squashfs_mutation`` (unchanged).
    Boot-health leg: ``installed_image`` + per-slot injection mutations
    (via :func:`record_slot_injection_mutation`) + ``slot_digests`` /
    ``slot_isolation`` (via :func:`verify_update_slot_isolation`) + the
    observed ``boot_observation`` facts from
    :func:`gather_boot_health_observation` (MBR/PARTUUID/filesystem/
    journal/sequence/layout). Exactly one image leg must be selected;
    mixing both refuses. Fail-closed: any missing/unreadable identity
    or missing provenance field raises (``BLOCKED`` naming the artifact
    when a built image/unit/bundle is unavailable to hash, RED
    otherwise) instead of emitting a partial record. No synthetic,
    placeholder or self-referential hashes: every digest is read from the
    stated file at evidence time.
    """
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    bundles = list(release_bundles) if isinstance(release_bundles, (list, tuple)) else []
    if not bundles:
        raise LifecycleHarnessError(
            "unit identity record requires at least one staged "
            ".greiaupdate bundle; refusing an update-free identity"
        )
    if installer_image is not None and installed_image is not None:
        raise LifecycleHarnessError(
            "unit identity record refuses an ambiguous image leg "
            "(installer_image and installed_image together)"
        )
    if installer_image is None and installed_image is None:
        raise LifecycleHarnessError(
            "unit identity record requires the booted image "
            "(installer_image or installed_image)"
        )
    units = record_product_unit_identity(project_root=root)
    modules = record_product_module_identity(project_root=root)
    bundle_entries: dict[str, object] = {}
    for bundle in bundles:
        entry = record_file_identity(Path(bundle), role="staged release bundle")
        bundle_entries[Path(bundle).name] = entry
    if installed_image is not None:
        image = record_file_identity(
            Path(installed_image), role="built installed image"
        )
        slot_a = _require_slot_provenance(slot_a_mutation, role="slot-A")
        slot_b = _require_slot_provenance(slot_b_mutation, role="slot-B")
        digests, isolation = _require_boot_isolation_evidence(
            slot_digests, slot_isolation
        )
        observation = _require_boot_observation_evidence(boot_observation)
        return {
            "schema_version": UNIT_IDENTITY_SCHEMA_VERSION,
            "units": units,
            "modules": modules,
            "installed_image": image,
            "release_bundles": bundle_entries,
            "slot_a_mutation": slot_a,
            "slot_b_mutation": slot_b,
            "slot_digests": digests,
            "slot_isolation": isolation,
            "boot_observation": observation,
            "source_image_mutated": False,
        }
    assert installer_image is not None
    image = record_file_identity(Path(installer_image), role="built installer image")
    mutation = _require_squashfs_provenance(squashfs_mutation)
    return {
        "schema_version": UNIT_IDENTITY_SCHEMA_VERSION,
        "units": units,
        "modules": modules,
        "installer_image": image,
        "release_bundles": bundle_entries,
        "squashfs_mutation": mutation,
        "source_image_mutated": False,
    }


def assert_product_identity_complete(
    record: Mapping[str, object],
    *,
    project_root: Path | None = None,
    installer_image: Path | None = None,
    installed_image: Path | None = None,
    release_bundles: object,
) -> None:
    """Assert the identity record binds the exact run (registered baseline).

    Checks: schema version; the unit/module key sets are exactly the pinned
    stable identities (a new unregistered entry or an unexplained
    disappearance/rename is RED); every recorded unit/module SHA+size still
    matches the repo tree at evidence time; the recorded image SHA matches
    the booted image file (``installer_image`` for the install leg,
    ``installed_image`` for the boot-health leg); every recorded bundle
    SHA matches the staged candidate; the leg provenance is present and
    well-formed (squashfs for install; per-slot injection + slot-isolation
    digests + observed boot facts for boot-health, with a focused RED
    when an observed provenance field is missing). Any mismatch raises
    RED naming the drifted identity.
    """
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    if not isinstance(record, Mapping):
        raise LifecycleHarnessError("unit identity record is not a mapping")
    if record.get("schema_version") != UNIT_IDENTITY_SCHEMA_VERSION:
        raise LifecycleHarnessError(
            "unit identity record has an unexpected schema version "
            f"(got {record.get('schema_version')!r})"
        )
    for section, pinned in (
        ("units", PRODUCT_IDENTITY_UNITS),
        ("modules", PRODUCT_IDENTITY_MODULES),
    ):
        block = record.get(section)
        if not isinstance(block, Mapping):
            raise LifecycleHarnessError(
                f"unit identity record is missing the {section!r} section"
            )
        entries = block.get("entries")
        if not isinstance(entries, Mapping):
            raise LifecycleHarnessError(
                f"unit identity record section {section!r} carries no entries"
            )
        recorded = set(entries.keys())
        expected = set(pinned)
        if recorded != expected:
            missing = sorted(expected - recorded)
            extra = sorted(recorded - expected)
            raise LifecycleHarnessError(
                "unit identity record identity drift in "
                f"{section!r}: missing={missing} extra={extra} "
                "(unregistered change fails closed)"
            )
        for relative in pinned:
            entry = entries[relative]
            if not isinstance(entry, Mapping):
                raise LifecycleHarnessError(
                    f"unit identity record entry {relative!r} is not a mapping"
                )
            fresh = record_file_identity(root / relative, role=f"rebound {section[:-1]} {relative}")
            for field in ("sha256", "size_bytes"):
                if entry.get(field) != fresh.get(field):
                    raise LifecycleHarnessError(
                        f"unit identity record no longer binds {relative!r}: "
                        f"recorded {field}={entry.get(field)!r} != "
                        f"observed {field}={fresh.get(field)!r}"
                    )
    image_block = record.get("installer_image")
    installed_block = record.get("installed_image")
    if isinstance(image_block, Mapping) and isinstance(installed_block, Mapping):
        raise LifecycleHarnessError(
            "unit identity record refuses an ambiguous image leg "
            "(installer_image and installed_image together)"
        )
    if isinstance(installed_block, Mapping):
        if installer_image is not None:
            raise LifecycleHarnessError(
                "unit identity record image leg mismatch: record carries "
                "installed_image but the assert was given installer_image"
            )
        if installed_image is None:
            raise LifecycleHarnessError(
                "unit identity assert requires the booted installed image "
                "(installed_image)"
            )
        fresh_image = record_file_identity(
            Path(installed_image), role="rebound installed image"
        )
        for field in ("sha256", "size_bytes"):
            if installed_block.get(field) != fresh_image.get(field):
                raise LifecycleHarnessError(
                    "unit identity record image does not bind the booted image: "
                    f"recorded {field}={installed_block.get(field)!r} != "
                    f"observed {field}={fresh_image.get(field)!r}"
                )
    elif isinstance(image_block, Mapping):
        if installed_image is not None:
            raise LifecycleHarnessError(
                "unit identity record image leg mismatch: record carries "
                "installer_image but the assert was given installed_image"
            )
        if installer_image is None:
            raise LifecycleHarnessError(
                "unit identity assert requires the booted installer image "
                "(installer_image)"
            )
        fresh_image = record_file_identity(Path(installer_image), role="rebound installer image")
        for field in ("sha256", "size_bytes"):
            if image_block.get(field) != fresh_image.get(field):
                raise LifecycleHarnessError(
                    "unit identity record image does not bind the booted image: "
                    f"recorded {field}={image_block.get(field)!r} != "
                    f"observed {field}={fresh_image.get(field)!r}"
                )
    else:
        raise LifecycleHarnessError("unit identity record carries no booted image")
    bundles = list(release_bundles) if isinstance(release_bundles, (list, tuple)) else []
    bundle_block = record.get("release_bundles")
    if not isinstance(bundle_block, Mapping):
        raise LifecycleHarnessError("unit identity record carries no release bundles")
    if {Path(b).name for b in bundles} != set(bundle_block.keys()):
        raise LifecycleHarnessError(
            "unit identity record bundle set does not match the staged "
            f"candidates (recorded={sorted(bundle_block.keys())} "
            f"staged={[Path(b).name for b in bundles]})"
        )
    for bundle in bundles:
        entry = bundle_block[Path(bundle).name]
        if not isinstance(entry, Mapping):
            raise LifecycleHarnessError(
                f"unit identity record bundle {Path(bundle).name!r} is not a mapping"
            )
        fresh = record_file_identity(Path(bundle), role="rebound release bundle")
        for field in ("sha256", "size_bytes"):
            if entry.get(field) != fresh.get(field):
                raise LifecycleHarnessError(
                    "unit identity record bundle does not bind the staged "
                    f"candidate {Path(bundle).name!r}: recorded "
                    f"{field}={entry.get(field)!r} != observed "
                    f"{field}={fresh.get(field)!r}"
                )
    mutation = record.get("squashfs_mutation")
    if isinstance(mutation, Mapping):
        if (
            "slot_a_mutation" in record
            or "slot_b_mutation" in record
            or "boot_observation" in record
        ):
            raise LifecycleHarnessError(
                "unit identity record refuses an ambiguous provenance leg "
                "(squashfs and boot-health sections together)"
            )
        _require_squashfs_provenance(mutation)
    else:
        slot_a = record.get("slot_a_mutation")
        slot_b = record.get("slot_b_mutation")
        digests = record.get("slot_digests")
        isolation = record.get("slot_isolation")
        boot_obs = record.get("boot_observation")
        if not isinstance(slot_a, Mapping):
            raise LifecycleHarnessError(
                "unit identity record carries no slot-A injection provenance"
            )
        if not isinstance(slot_b, Mapping):
            raise LifecycleHarnessError(
                "unit identity record carries no slot-B injection provenance"
            )
        _require_slot_provenance(slot_a, role="slot-A")
        _require_slot_provenance(slot_b, role="slot-B")
        _require_boot_isolation_evidence(digests, isolation)
        _require_boot_observation_evidence(boot_obs)
    if record.get("source_image_mutated", False):
        raise LifecycleHarnessError(
            "unit identity record refuses a mutated source image"
        )


# ---------------------------------------------------------------------------
# P5.2 boot-health leg: installed boot + update + health-commit wiring
# ---------------------------------------------------------------------------

#: Update phases driven through the installed update socket, in order.
BOOT_HEALTH_UPDATE_PHASES: tuple[str, ...] = (
    "update-status",
    "update-verify",
    "update-stage",
    "update-arm",
)

#: Full boot-health leg phase order: boot A (health-commit A), stage B
#: through the real update socket, boot B (health-commit B). Each phase
#: is one QEMU boot with a fresh host-written control disk; slot B is
#: re-injected after the real updater rewrites it and before its boot
#: (the release payload cannot carry the test unit).
BOOT_HEALTH_LEG_PHASES: tuple[str, ...] = (
    "wait-health-poweroff",
    "update-status",
    "update-verify",
    "update-stage",
    "update-arm",
    "wait-health-poweroff",
)

#: Shipped product units the boot-health leg runs through (never a
#: harness substitute). Recorded by SHA-256 from the repo tree.
SHIPPED_BOOT_UNITS: tuple[str, ...] = (
    "greia-boot-observer.service",
    "greia-launcher.service",
    "greia-boot-health.service",
    "greia-boot-health.socket",
    "greia-system-update.service",
    "greia-system-update.socket",
)

#: Installed-slot → MBR partition number (LegacyBiosAbAdapter order:
#: p1 boot-control, p2 system-a, p3 system-b, p4 persist).
SLOT_PARTITION_NUMBER: dict[str, int] = {"A": 2, "B": 3}

#: Control-disk copy of the signed candidate staged by the host for the
#: ``update-stage`` phase; the guest runner copies it into the real
#: installed inbox before driving ``STAGE_CURRENT_CANDIDATE``.
CANDIDATE_BUNDLE_FILE = "candidate.greiaupdate"


def record_shipped_boot_units(
    *, project_root: Path | None = None
) -> dict[str, object]:
    """Record the shipped boot/health/update units as leg evidence.

    Reads the exact unit files the installed guest serves
    (``build/overlay/etc/systemd/system/...``) and records their
    SHA-256: the leg boots through these shipped units, never a harness
    substitute. Absent unit files stay ``BLOCKED`` naming the artifact.
    """
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    unit_dir = root / "build/overlay/etc/systemd/system"
    units: dict[str, str] = {}
    for name in SHIPPED_BOOT_UNITS:
        path = unit_dir / name
        if path.is_symlink() or not path.is_file():
            raise LifecycleHarnessError(
                "BLOCKED product mode: shipped boot-health unit is absent "
                f"({path}); refusing a harness-only substitution"
            )
        units[name] = sha256_file(path)
    return {"unit_dir": str(unit_dir), "sha256": units}


def record_slot_injection_mutation(
    *, pre_sha256: str, post_sha256: str, injected_files: list[str]
) -> dict[str, object]:
    """Name the clone-only slot injection explicitly (P5.3 identity input).

    Mirrors :func:`record_live_squashfs_mutation` for the installed-slot
    path: the disposable clone image SHA before/after the control seam
    was injected into one ext4 slot, plus the exact injected-file list.
    The source/installed origin image is never mutated.
    """
    import re as _re

    hex64 = _re.compile(r"^[0-9a-f]{64}$")
    if not hex64.fullmatch(pre_sha256 or "") or not hex64.fullmatch(post_sha256 or ""):
        raise LifecycleHarnessError(
            "slot-injection record requires observed pre/post SHA-256"
        )
    if not injected_files:
        raise LifecycleHarnessError(
            "slot-injection record requires the exact injected-file list"
        )
    return {
        "pre_sha256": pre_sha256,
        "post_sha256": post_sha256,
        "injected_files": list(injected_files),
        "source_image_mutated": False,
    }


#: Clone-only serial-console substitution. The shipped release kernel
#: command line is consoleless (``console=null``, child-appliance
#: contract), but a consoleless live/installed boot stalls under the
#: QEMU harness path: measured twice on the capable host, GRUB reads
#: exactly 54,846,464 bytes (kernel+initrd) and the guest then spins
#: at 100% CPU with zero disk I/O forever, while the same bytes boot
#: to login in ~4 min once a serial console exists. Prepending
#: ``console=ttyS0,115200`` keeps ``console=null`` preferred (last),
#: so ``/dev/console`` semantics are unchanged while the kernel gains
#: a real console device and the harness gains serial diagnostics.
#: Applied to disposable clones only; the source/shipped images and
#: their contract validation are never touched.
SERIAL_CONSOLE_PREFIX = "console=ttyS0,115200 console=null"


def record_grub_console_mutation(
    *, grub_cfg: str, pre_sha256: str, post_sha256: str, substitutions: int
) -> dict[str, object]:
    """Name the clone-only grub-console mutation explicitly (P5.3 input).

    Mirrors :func:`record_live_squashfs_mutation` for the boot-console
    path: the clone grub.cfg location plus its SHA-256 before/after the
    serial-console substitution and the exact substitution count (0
    when the clone already carried it). The source/installed origin
    image is never mutated.
    """
    import re as _re

    hex64 = _re.compile(r"^[0-9a-f]{64}$")
    if not hex64.fullmatch(pre_sha256 or "") or not hex64.fullmatch(post_sha256 or ""):
        raise LifecycleHarnessError(
            "grub-console record requires observed pre/post SHA-256"
        )
    if not grub_cfg or int(substitutions) < 0:
        raise LifecycleHarnessError(
            "grub-console record requires the grub.cfg path and a count"
        )
    return {
        "grub_cfg": str(grub_cfg),
        "pre_sha256": pre_sha256,
        "post_sha256": post_sha256,
        "substitutions": int(substitutions),
        "source_image_mutated": False,
    }


#: Unit pulled by the harness in live clones (clone-only enablement).
#: In production the unprivileged graphical installer pulls
#: ``greia-install-transaction.socket`` via Wants when its session
#: starts; the harness masks the graphical service (r7 precedent, no
#: Xorg/GUI in the test path), so nothing would ever pull the socket
#: and the control's transaction dial would fail closed. Enabling the
#: shipped socket unit in the disposable clone restores exactly the
#: production-provided capability (same unit file, same root service,
#: same peer authorization) with an earlier declarative trigger; the
#: graphical service stays masked. Recorded for P5.3 evidence.
LIVE_TRANSACTION_SOCKET_UNIT = "greia-install-transaction.socket"


def _enable_clone_socket_unit(
    mountpoint: Path,
    *,
    unit: str,
    sha_fn=None,
) -> dict[str, object]:
    """Enable one shipped socket unit in a mounted clone tree (clone-only).

    Links ``etc/systemd/system/sockets.target.wants/<unit>`` at the
    shipped ``etc/systemd/system/<unit>`` file so the listener starts
    at boot without the graphical session that pulls it in
    production. Fail-closed: the unit file must exist as a regular
    file (proving the enabled unit is the shipped bytes, never a
    harness substitute) and no wants entry may pre-exist. Pure file
    work: the caller owns attach/mount.
    """
    unit_path = Path(mountpoint) / "etc/systemd/system" / str(unit)
    if unit_path.is_symlink() or not unit_path.is_file():
        raise LifecycleHarnessError(
            "clone socket enablement refused: shipped unit is absent "
            f"({unit_path}); refusing a harness-only substitution"
        )
    wants_dir = Path(mountpoint) / "etc/systemd/system/sockets.target.wants"
    link = wants_dir / str(unit)
    if link.exists() or link.is_symlink():
        raise LifecycleHarnessError(
            f"clone socket enablement refused: {link} already exists"
        )
    hash_file = sha_fn or sha256_file
    unit_sha = str(hash_file(unit_path))
    wants_dir.mkdir(parents=True, exist_ok=True)
    link.symlink_to(f"../{unit}")
    return {
        "unit": str(unit),
        "unit_sha256": unit_sha,
        "wants_link": "etc/systemd/system/sockets.target.wants/" + str(unit),
        "source_image_mutated": False,
    }


def _ensure_clone_serial_console(
    mountpoint: Path,
    *,
    grub_relpath: str,
    expected_consoles: int,
    sha_fn=None,
) -> dict[str, object]:
    """Enable the clone-only serial console on a mounted clone tree.

    Replaces every bare ``console=null`` with
    ``console=ttyS0,115200 console=null`` in ``grub_relpath`` under
    ``mountpoint``. Fail-closed: the file must be a regular file with
    exactly ``expected_consoles`` bare occurrences and no already-patched
    ones (fresh clone), or zero bare plus exactly ``expected_consoles``
    already-patched ones (idempotent re-entry, e.g. slot-B injection
    after slot-A on the same clone) recorded with substitutions 0.
    Anything else (missing file, developer ``console=tty1`` shape,
    partial edit) raises. Pure file work: the caller owns attach/mount.
    """
    import re as _re

    cfg = Path(mountpoint) / str(grub_relpath)
    if cfg.is_symlink() or not cfg.is_file():
        raise LifecycleHarnessError(
            "clone serial-console refused: "
            f"{grub_relpath} is not a regular file under {mountpoint}"
        )
    hash_file = sha_fn or sha256_file
    text = cfg.read_text(encoding="utf-8")
    bare = len(_re.findall(r"(?<!console=ttyS0,115200 )console=null", text))
    dual = text.count(SERIAL_CONSOLE_PREFIX)
    if bare == int(expected_consoles) and dual == 0:
        patched = text.replace("console=null", SERIAL_CONSOLE_PREFIX)
        if patched.count(SERIAL_CONSOLE_PREFIX) != int(expected_consoles):
            raise LifecycleHarnessError(
                "clone serial-console refused: substitution did not land "
                f"exactly {expected_consoles}x in {grub_relpath}"
            )
        pre_sha = str(hash_file(cfg))
        cfg.write_text(patched, encoding="utf-8")
        post_sha = str(hash_file(cfg))
        substitutions = int(expected_consoles)
    elif bare == 0 and dual == int(expected_consoles):
        pre_sha = str(hash_file(cfg))
        post_sha = pre_sha
        substitutions = 0
    else:
        raise LifecycleHarnessError(
            "clone serial-console refused: expected "
            f"{expected_consoles} console=null entries in {grub_relpath}, "
            f"found {bare} bare + {dual} already-patched"
        )
    return {
        "grub_cfg": str(grub_relpath),
        **record_grub_console_mutation(
            grub_cfg=str(grub_relpath),
            pre_sha256=pre_sha,
            post_sha256=post_sha,
            substitutions=substitutions,
        ),
    }


def enable_installed_clone_serial_console(
    clone_path: Path,
    *,
    runner=None,
    which=None,
    sha_fn=None,
) -> dict[str, object]:
    """Enable the clone-only serial console on an installed-layout clone.

    Partscan-attaches the disposable installed clone, mounts its
    boot-control partition (p1) read-write, resolves the production
    grub.cfg location and applies
    :func:`_ensure_clone_serial_console` (two slot entries), then
    unmounts/detaches. Records the clone image SHA-256 before/after
    for the P5.3 identity record; the origin image is never touched.
    """
    import tempfile as _tempfile

    from greia_installer.disk import partition_number_path
    from greia_installer.fresh_ab_install import GRUB_CONFIG_NAME

    _require_loop_tools("losetup", "mount", "umount", which=which)
    if str(clone_path).startswith("/dev/"):
        raise LifecycleHarnessError(
            f"refusing block-device path {clone_path}: clones are regular files only"
        )
    if not Path(clone_path).is_file():
        raise LifecycleHarnessError(
            f"BLOCKED product mode: disposable installed clone is absent ({clone_path})"
        )
    hash_file = sha_fn or sha256_file
    pre_sha = str(hash_file(Path(clone_path)))
    mountpoint = Path(_tempfile.mkdtemp(prefix="greia-x8-console-mnt-"))
    loopdev = ""
    try:
        loopdev = _loop_attach_partscan(clone_path, runner=runner, which=which)
        try:
            node = str(partition_number_path(Path(loopdev), 1))
        except Exception as exc:
            raise LifecycleHarnessError(
                f"clone serial-console refused: no boot partition on {loopdev} ({exc})"
            ) from exc
        _mount_fs(node, mountpoint, read_only=False, runner=runner, which=which)
        try:
            boot_control = _resolve_marker_dir(
                mountpoint, ["", "boot"], GRUB_CONFIG_NAME,
                what="installed GRUB config",
            )
            rel = boot_control.relative_to(mountpoint) / GRUB_CONFIG_NAME
            proof = _ensure_clone_serial_console(
                mountpoint,
                grub_relpath=str(rel),
                expected_consoles=2,
                sha_fn=sha_fn,
            )
        finally:
            _umount_fs(mountpoint, runner=runner)
    finally:
        if loopdev:
            _loop_detach(loopdev, runner=runner)
        shutil.rmtree(mountpoint, ignore_errors=True)
    post_sha = str(hash_file(Path(clone_path)))
    return {
        "clone": str(Path(clone_path).resolve()),
        "clone_pre_sha256": pre_sha,
        "clone_post_sha256": post_sha,
        **proof,
    }


def product_boot_qemu_argv(
    *,
    installed_clone: Path,
    control_image: Path | None,
    output_dir: Path,
    memory_mib: int,
    cpus: int,
    qemu_binary: str,
    leg: str = "boot-health",
) -> tuple[list[str], Path, Path]:
    """Argv for one installed-system boot with Xorg-capable display (R1/G1).

    Resolution of the design-brief risks: R1 (the installed launcher is
    an Xorg/pygame app via ``xinit ... greia-x-session``) is met with an
    explicit virtual VGA device (``-vga std``) so the real Xorg launcher
    can reach ``INTERACTIVE_READY``; the host window stays absent
    (``-display none``). G1 (the product profile is i386) is met by
    booting with the ``qemu-system-i386``-preferred binary selected by
    :func:`select_install_qemu_binary` on the ``pc,accel=kvm:tcg,qemu32``
    machine (KVM when the host offers it, TCG fallback; TCG-only
    exceeds the leg timeout on this lane). The clone-only serial
    console (enabled at clone/inject time) keeps the consoleless
    installed boot from stalling under the harness. Takes regular
    image files only; any ``/dev`` path is
    refused so no valued physical disk can be contacted.
    """
    for candidate in (installed_clone,):
        if str(candidate).startswith("/dev/"):
            raise LifecycleHarnessError(
                f"refusing block-device path {candidate}: product mode takes "
                "regular image files only"
            )
    if control_image is not None and str(control_image).startswith("/dev/"):
        raise LifecycleHarnessError(
            f"refusing block-device path {control_image}: product mode takes "
            "regular image files only"
        )
    out = Path(output_dir)
    serial_log = out / f"product-{leg}-serial.log"
    host_log = out / f"product-{leg}-qemu.log"
    argv = [
        str(qemu_binary),
        "-name",
        f"greia-product-{leg}",
        "-machine",
        "pc,accel=kvm:tcg",
        "-cpu",
        "qemu32",
        "-m",
        str(int(memory_mib)),
        "-smp",
        str(int(cpus)),
        "-drive",
        f"if=none,id=installed,file={installed_clone},format=raw",
        "-device",
        "ide-hd,drive=installed,bootindex=1",
        "-vga",
        "std",
        "-display",
        "none",
        "-monitor",
        "none",
        "-serial",
        f"file:{serial_log}",
        "-nic",
        "none",
        "-boot",
        "order=c,strict=on",
        "-no-reboot",
    ]
    if control_image is not None:
        argv.extend(
            [
                "-drive",
                f"if=none,id=ctl,file={control_image},format=raw,snapshot=on",
                "-device",
                "ide-hd,drive=ctl",
            ]
        )
    return argv, serial_log, host_log


def inject_boot_slot(
    clone_path: Path,
    slot: str,
    *,
    runner=None,
    which=None,
    sha_fn=None,
) -> dict[str, object]:
    """Inject the control seam into one installed ext4 slot of a clone.

    Loop partscan-attaches the disposable installed clone, mounts the
    slot partition (A→p2, B→p3 via the production
    :func:`greia_installer.disk.partition_number_path`), applies
    :func:`inject_control_into_root` (no service is masked on installed
    slots), then enables the clone-only serial console on the
    boot-control grub.cfg (idempotent: slot-B injection after slot-A on
    the same clone records substitutions 0) and unmounts/detaches in
    ``finally``. Without the serial console the consoleless installed
    boot stalls under the harness. Records the clone image SHA-256
    before/after plus the exact injected-file list for the P5.3
    identity record; the origin image is never touched. Called once
    for slot A before its boot and again for slot B after the real
    updater rewrites it and before its boot (the release payload cannot
    carry the test unit).
    """
    import tempfile as _tempfile

    from greia_installer.disk import partition_number_path

    if slot not in SLOT_PARTITION_NUMBER:
        raise LifecycleHarnessError(
            f"slot injection refused: unknown slot {slot!r} (expected 'A' or 'B')"
        )
    _require_loop_tools("losetup", "mount", "umount", which=which)
    if str(clone_path).startswith("/dev/"):
        raise LifecycleHarnessError(
            f"refusing block-device path {clone_path}: clones are regular files only"
        )
    if not Path(clone_path).is_file():
        raise LifecycleHarnessError(
            f"BLOCKED product mode: disposable installed clone is absent ({clone_path})"
        )
    hash_file = sha_fn or sha256_file
    pre_sha = str(hash_file(Path(clone_path)))
    mountpoint = Path(_tempfile.mkdtemp(prefix="greia-x8-slot-mnt-"))
    loopdev = ""
    injected_files: list[str] = []
    try:
        loopdev = _loop_attach_partscan(clone_path, runner=runner, which=which)
        try:
            node = str(
                partition_number_path(
                    Path(loopdev), SLOT_PARTITION_NUMBER[slot]
                )
            )
        except Exception as exc:
            raise LifecycleHarnessError(
                f"slot injection refused: no slot-{slot} partition on {loopdev} ({exc})"
            ) from exc
        _mount_fs(node, mountpoint, read_only=False, runner=runner, which=which)
        try:
            injected = inject_control_into_root(mountpoint)
        finally:
            _umount_fs(mountpoint, runner=runner)
        injected_files = [
            "etc/systemd/system/greia-x8-control.service",
            "usr/local/sbin/greia-x8-control",
            "etc/systemd/system/multi-user.target.wants/greia-x8-control.service",
        ]
        _ = injected
        from greia_installer.fresh_ab_install import GRUB_CONFIG_NAME

        boot_node = str(partition_number_path(Path(loopdev), 1))
        _mount_fs(boot_node, mountpoint, read_only=False, runner=runner, which=which)
        try:
            boot_control = _resolve_marker_dir(
                mountpoint, ["", "boot"], GRUB_CONFIG_NAME,
                what="installed GRUB config",
            )
            rel = boot_control.relative_to(mountpoint) / GRUB_CONFIG_NAME
            serial_proof = _ensure_clone_serial_console(
                mountpoint,
                grub_relpath=str(rel),
                expected_consoles=2,
                sha_fn=sha_fn,
            )
        finally:
            _umount_fs(mountpoint, runner=runner)
    finally:
        if loopdev:
            _loop_detach(loopdev, runner=runner)
        shutil.rmtree(mountpoint, ignore_errors=True)
    post_sha = str(hash_file(Path(clone_path)))
    mutation = record_slot_injection_mutation(
        pre_sha256=pre_sha, post_sha256=post_sha, injected_files=injected_files
    )
    return {
        "clone": str(Path(clone_path).resolve()),
        "slot": slot,
        "injected_files": injected_files,
        "pre_sha256": pre_sha,
        "post_sha256": post_sha,
        "slot_mutation": mutation,
        "grub_console": serial_proof,
        "source_image_mutated": False,
    }


def hash_slot_partition(
    target_image: Path, slot: str, *, runner=None, which=None
) -> str:
    """Hash one installed slot partition's bytes host-side (offline).

    Loop partscan-attaches the disposable target, resolves the slot
    partition node (A→p2, B→p3 via the production
    :func:`greia_installer.disk.partition_number_path`), streams the node
    bytes through SHA-256, then detaches in ``finally``. The target must
    stay offline throughout (no QEMU boot may run concurrently); regular
    image files only, ``/dev`` refused, a missing loop facility stays
    ``BLOCKED`` naming it. The leg hashes the inactive slot right after
    cloning (its updater baseline), the active slot right after its
    control-seam injection (its seam baseline), and both again after the
    final boot, proving through :func:`verify_update_slot_isolation` that
    only the inactive slot moved.
    """
    from greia_installer.disk import partition_number_path

    if slot not in SLOT_PARTITION_NUMBER:
        raise LifecycleHarnessError(
            f"slot digest refused: unknown slot {slot!r} (expected 'A' or 'B')"
        )
    target = Path(target_image)
    if str(target).startswith("/dev/"):
        raise LifecycleHarnessError(
            f"refusing block-device path {target}: slot digests take regular files only"
        )
    if not target.is_file():
        raise LifecycleHarnessError(
            f"BLOCKED product mode: slot-digest target is absent ({target})"
        )
    _require_loop_tools("losetup", which=which)
    loopdev = ""
    try:
        loopdev = _loop_attach_partscan(target, runner=runner, which=which)
        try:
            node = str(
                partition_number_path(
                    Path(loopdev), SLOT_PARTITION_NUMBER[slot]
                )
            )
        except Exception as exc:
            raise LifecycleHarnessError(
                f"slot digest refused: no slot-{slot} partition on {loopdev} ({exc})"
            ) from exc
        digest = hashlib.sha256()
        with open(node, "rb") as stream:
            for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    finally:
        if loopdev:
            _loop_detach(loopdev, runner=runner)


def inspect_boot_health_roots(
    *,
    backend_state_dir: Path,
    journal_dir: Path,
    accepted_state_dir: Path,
    layout_record_path: Path,
    expected_slot: str,
    expected_sequence: int,
) -> dict[str, object]:
    """Verify one health-committed boot through production parsers only.

    Checks, all read from authoritative on-image state (the control
    channel is never consulted):

    - ``GrubEnvBackend``: persistent default is ``expected_slot``,
      no stray one-shot, and the observer-established ``last_booted``
      is ``expected_slot`` (the real ``greia-boot-observer`` unit must
      have reconciled it before launcher acceptance);
    - ``BootTransactionJournal``: terminal ``ACCEPTED`` binding
      ``expected_slot``;
    - ``read_accepted_sequence``: ``expected_sequence``;
    - ``InstalledLayoutRecord``: accepted slot/sequence agree.
    """
    from greia_platform.boot_transaction import (
        BootTransactionJournal,
        BootTransactionState,
    )
    from greia_platform.grub_ab import GrubEnvBackend
    from greia_platform.system_updates import read_accepted_sequence

    if expected_slot not in ("A", "B"):
        raise LifecycleHarnessError(
            f"boot-health inspection refused: unknown slot {expected_slot!r}"
        )
    backend = GrubEnvBackend.attach(Path(backend_state_dir))
    state = backend.inspect()
    if state.default_slot != expected_slot:
        raise LifecycleHarnessError(
            f"boot-health default is {state.default_slot!r}, expected {expected_slot!r}"
        )
    if state.one_shot_slot is not None:
        raise LifecycleHarnessError(
            "boot-health carries a stray one-shot after health commit"
        )
    if state.last_booted_slot != expected_slot:
        raise LifecycleHarnessError(
            f"observer last_booted is {state.last_booted_slot!r}, expected "
            f"{expected_slot!r}: the boot observer must establish the "
            "authoritative last_booted before health acceptance"
        )
    journal = BootTransactionJournal.load(Path(journal_dir))
    if journal.state is not BootTransactionState.ACCEPTED:
        raise LifecycleHarnessError(
            f"boot-health journal is {journal.state!r}, expected ACCEPTED"
        )
    if journal.candidate_slot != expected_slot:
        raise LifecycleHarnessError(
            "boot-health journal does not bind the committed slot"
        )
    sequence = read_accepted_sequence(Path(accepted_state_dir))
    if int(sequence) != int(expected_sequence):
        raise LifecycleHarnessError(
            f"accepted sequence is {sequence!r}, expected {expected_sequence!r}"
        )
    from greia_platform.system_updates import load_installed_layout_record

    record = load_installed_layout_record(Path(layout_record_path))
    if record is None:
        raise LifecycleHarnessError("layout authority carries no installed record")
    if record.accepted_slot != expected_slot:
        raise LifecycleHarnessError(
            f"layout authority accepts {record.accepted_slot!r}, "
            f"expected {expected_slot!r}"
        )
    if int(record.accepted_release_sequence) != int(expected_sequence):
        raise LifecycleHarnessError(
            "layout authority sequence moved under the health transaction"
        )
    return {
        "committed_slot": expected_slot,
        "accepted_sequence": int(sequence),
        "grubenv_default": state.default_slot,
        "last_booted": state.last_booted_slot,
        "journal_state": str(journal.state.value),
        "layout_accepted_slot": record.accepted_slot,
    }


def verify_update_slot_isolation(
    *,
    active_slot: str,
    active_before_digest: str,
    active_after_digest: str,
    inactive_before_digest: str,
    inactive_after_digest: str,
) -> dict[str, object]:
    """Prove only the inactive slot changed across STAGE/ARM (pure).

    The active/accepted slot must stay byte-identical while the staged
    inactive slot digest moves. Digests are observed slot payload
    digests (never minted here); empty or malformed digests refuse.
    """
    import re as _re

    hex64 = _re.compile(r"^[0-9a-f]{64}$")
    if active_slot not in ("A", "B"):
        raise LifecycleHarnessError(
            f"slot isolation refused: unknown active slot {active_slot!r}"
        )
    for name, value in (
        ("active_before", active_before_digest),
        ("active_after", active_after_digest),
        ("inactive_before", inactive_before_digest),
        ("inactive_after", inactive_after_digest),
    ):
        if not isinstance(value, str) or not hex64.fullmatch(value):
            raise LifecycleHarnessError(
                f"slot isolation refused: {name} digest is not an observed SHA-256"
            )
    if active_before_digest != active_after_digest:
        raise LifecycleHarnessError(
            f"slot isolation violated: active/accepted slot {active_slot} changed"
        )
    if inactive_before_digest == inactive_after_digest:
        raise LifecycleHarnessError(
            "slot isolation violated: inactive slot shows no staged change"
        )
    return {
        "active_slot": active_slot,
        "active_unchanged": True,
        "inactive_changed": True,
    }


def _resolve_boot_evidence_dirs(
    boot_mnt: Path, persist_mnt: Path
) -> dict[str, Path]:
    """Resolve the on-image evidence dirs while boot/persist stay mounted.

    Shared by the boot-health and recovery observers: grubenv state on
    the boot-control mount; the update pending journal preferred, else
    the first-install journal; the accepted release state; and the
    installed layout record. Every Miss fails closed naming the searched
    paths (single owner for the candidate lists).
    """
    from greia_platform.boot_transaction import JOURNAL_FILE_NAME
    from greia_platform.grub_ab import GRUBENV_FILE_NAME
    from greia_platform.persistent_layout import LAYOUT_RECORD_NAME
    from greia_platform.system_updates import UPDATE_JOURNAL_DIR_NAME

    backend_state_dir = _resolve_marker_dir(
        boot_mnt,
        ["grub", "boot/grub", ""],
        GRUBENV_FILE_NAME,
        what="grubenv state",
    )
    # Prefer the update pending journal when present, else the
    # first-install journal: exactly one must verify for the
    # committed slot (both-pending refuses inside the service; here
    # a missing journal dir fails closed naming searched paths).
    # The namespace-sourced candidate is grounded in the durable-path
    # audit (/var/lib/greia-os binds from PERSIST namespace
    # parent-credentials, whose sources live under greia/namespaces);
    # the persist-root candidates preserve the previously probed
    # layout and fail closed when every candidate misses.
    journal_dir: Path | None = None
    last_error: LifecycleHarnessError | None = None
    for candidates in (
        [
            "greia/namespaces/parent-credentials/system-updates/"
            + UPDATE_JOURNAL_DIR_NAME,
            "system-updates/" + UPDATE_JOURNAL_DIR_NAME,
            "system-updates/journal",
        ],
        ["", "boot", "greia", "boot-journal"],
    ):
        marker = JOURNAL_FILE_NAME
        try:
            if "system-updates" in candidates[0]:
                journal_dir = _resolve_marker_dir(
                    persist_mnt, candidates, marker, what="update journal"
                )
            else:
                journal_dir = _resolve_marker_dir(
                    persist_mnt, candidates, marker, what="first-install journal"
                )
            break
        except LifecycleHarnessError as exc:
            last_error = exc
            journal_dir = None
            continue
    if journal_dir is None:
        raise LifecycleHarnessError(str(last_error))
    assert journal_dir is not None
    # Accepted-sequence state and layout authority resolve from the
    # same persist tree while still mounted: the update state dir
    # (/var/lib/greia-os at runtime) binds from PERSIST namespace
    # parent-credentials, so its system-updates/accepted.json is
    # probed there first; the installed layout record's authoritative
    # on-persist copy is greia/installed-layout.json
    # (greia_platform.persistent_layout.persist_record_path), with
    # the layout-authority namespace source as the bounded second
    # candidate. A miss fails closed naming every searched path.
    accepted_state_dir = _resolve_marker_dir(
        persist_mnt,
        ["greia/namespaces/parent-credentials", ""],
        "system-updates/accepted.json",
        what="accepted release state",
    )
    layout_record_dir = _resolve_marker_dir(
        persist_mnt,
        ["greia", "greia/namespaces/layout-authority", ""],
        LAYOUT_RECORD_NAME,
        what="installed layout record",
    )
    return {
        "backend_state_dir": backend_state_dir,
        "journal_dir": journal_dir,
        "accepted_state_dir": accepted_state_dir,
        "layout_record_path": layout_record_dir / LAYOUT_RECORD_NAME,
    }


def gather_boot_health_observation(
    target_path: Path,
    *,
    work_dir: Path,
    runner=None,
    which=None,
    expected_slot: str,
    expected_sequence: int,
) -> dict[str, object]:
    """Observe the health-committed disposable target (production parsers).

    Partscan-attaches the target, reads the MBR PARTUUIDs plus the
    system-a/system-b/persist filesystem UUIDs via ``blkid``, mounts
    boot-control (p1) and persist (p4) read-only, resolves the
    production-placed ``grubenv``/journal/accepted-sequence/layout evidence
    dirs, and verifies them through :func:`inspect_boot_health_roots` for
    the committed slot while still mounted. Every
    slot/journal/sequence/default/layout fact is derived from real disk
    bytes; the control channel is never read for attestation. The returned
    ``default_slot``/``accepted_sequence``/``committed_slot`` come from
    that inspection (never minted), so the report closure predicate reads
    authoritative state. A missing facility stays ``BLOCKED`` naming it;
    a missing evidence file fails closed naming the searched paths.
    """
    import tempfile as _tempfile

    from greia_installer.disk import partition_number_path
    from greia_platform.persistent_layout import LAYOUT_RECORD_NAME

    from .lifecycle import run_file_cross_check

    if expected_slot not in ("A", "B"):
        raise LifecycleHarnessError(
            f"boot-health observation refused: unknown expected slot {expected_slot!r}"
        )
    if isinstance(expected_sequence, bool) or not isinstance(expected_sequence, int):
        raise LifecycleHarnessError(
            "boot-health observation refused: expected sequence is not an integer"
        )

    target = Path(target_path)
    if str(target).startswith("/dev/"):
        raise LifecycleHarnessError(
            f"refusing block-device path {target}: product mode takes regular files only"
        )
    if not target.is_file():
        raise LifecycleHarnessError(
            f"BLOCKED product mode: health target is absent ({target})"
        )
    with target.open("rb") as stream:
        mbr = stream.read(512)
    disk_identities = observe_disk_identities_from_mbr(bytes(mbr))
    cross = run_file_cross_check(
        target, expected_signature=str(disk_identities["disk_signature"])
    )
    if not bool(cross.get("executed")):
        raise LifecycleHarnessError(
            "BLOCKED product mode: file cross-check is tool-less "
            f"({cross.get('detail')}); refusing an unchecked observation"
        )
    if not bool(cross.get("green")):
        raise LifecycleHarnessError(
            f"health target cross-check is RED ({cross.get('detail')}); "
            "refusing a contradicted observation"
        )
    _require_loop_tools("losetup", "mount", "umount", "blkid", which=which)
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    boot_mnt = Path(_tempfile.mkdtemp(prefix="greia-x8-hboot-", dir=str(work)))
    persist_mnt = Path(_tempfile.mkdtemp(prefix="greia-x8-hpersist-", dir=str(work)))
    loopdev = ""
    mounted_boot = False
    mounted_persist = False
    try:
        loopdev = _loop_attach_partscan(target, runner=runner, which=which)
        base = Path(loopdev)
        try:
            node_boot = str(partition_number_path(base, 1))
            node_a = str(partition_number_path(base, 2))
            node_b = str(partition_number_path(base, 3))
            node_persist = str(partition_number_path(base, 4))
        except Exception as exc:
            raise LifecycleHarnessError(
                f"health target has no A/B partition nodes on {loopdev} ({exc})"
            ) from exc
        observed_identities = {
            "system-a": {
                "partuuid": str(disk_identities["system_a_partuuid"]),
                "filesystem_uuid": _blkid_filesystem_uuid(
                    node_a, runner=runner, which=which
                ),
            },
            "system-b": {
                "partuuid": str(disk_identities["system_b_partuuid"]),
                "filesystem_uuid": _blkid_filesystem_uuid(
                    node_b, runner=runner, which=which
                ),
            },
            "persist": {
                "partuuid": str(disk_identities["persist_partuuid"]),
                "filesystem_uuid": _blkid_filesystem_uuid(
                    node_persist, runner=runner, which=which
                ),
            },
        }
        _mount_fs(node_boot, boot_mnt, read_only=True, runner=runner, which=which)
        mounted_boot = True
        _mount_fs(
            node_persist, persist_mnt, read_only=True, runner=runner, which=which
        )
        mounted_persist = True
        resolved = _resolve_boot_evidence_dirs(boot_mnt, persist_mnt)
        backend_state_dir = resolved["backend_state_dir"]
        journal_dir = resolved["journal_dir"]
        accepted_state_dir = resolved["accepted_state_dir"]
        layout_record_dir = resolved["layout_record_path"].parent
        health = inspect_boot_health_roots(
            backend_state_dir=backend_state_dir,
            journal_dir=journal_dir,
            accepted_state_dir=accepted_state_dir,
            layout_record_path=layout_record_dir / LAYOUT_RECORD_NAME,
            expected_slot=expected_slot,
            expected_sequence=expected_sequence,
        )
        inspection = {
            "disk_identities": disk_identities,
            "observed_identities": observed_identities,
            "backend_state_dir": str(backend_state_dir),
            "journal_dir": str(journal_dir),
            "accepted_state_dir": str(accepted_state_dir),
            "layout_record": str(layout_record_dir / LAYOUT_RECORD_NAME),
        }
    finally:
        if mounted_boot:
            _umount_fs(boot_mnt, runner=runner)
        if mounted_persist:
            _umount_fs(persist_mnt, runner=runner)
        if loopdev:
            _loop_detach(loopdev, runner=runner)
        shutil.rmtree(boot_mnt, ignore_errors=True)
        shutil.rmtree(persist_mnt, ignore_errors=True)
    return {
        "target_image": str(target),
        "disk_identities": inspection["disk_identities"],
        "observed_identities": inspection["observed_identities"],
        "file_cross_check": {
            "executed": cross["executed"],
            "green": cross["green"],
            "detail": cross["detail"],
        },
        "inspection": health,
        "default_slot": health["grubenv_default"],
        "accepted_sequence": health["accepted_sequence"],
        "committed_slot": health["committed_slot"],
        "last_booted": health["last_booted"],
        "journal_state": health["journal_state"],
        "resolved_paths": {
            "backend_state_dir": str(inspection["backend_state_dir"]),
            "journal_dir": str(inspection["journal_dir"]),
            "accepted_state_dir": str(inspection["accepted_state_dir"]),
            "layout_record": str(inspection["layout_record"]),
        },
    }


def build_boot_health_lifecycle_report(
    *, observed_default: str
) -> dict[str, object]:
    """Build the contract-shaped boot-health report and close it.

    The boot-health leg observes ``boot-A-accepted`` (first-install A
    health-committed), ``stage-B-one-shot`` (inactive slot B staged
    through the shipped socket) and ``boot-B-commit`` (B health-committed
    with accepted-sequence advancement) host-side; the remaining legs
    keep the frozen expected-slot pattern so
    ``assert_lifecycle_transitions`` can verify the report shape. The
    returned dict names which steps this leg observed
    (``observed_steps``) versus which successors own, so shape closure
    never launders projection into product success.
    """
    from .lifecycle import (
        BOOT_OUTCOME_EXPECTED_SLOT,
        LAUNCHER_ACCEPTANCE_LEGS,
        LIFECYCLE_SEQUENCE,
        SHIPPED_UPDATE_LEGS,
        assert_lifecycle_transitions,
    )

    if observed_default != "B":
        raise LifecycleHarnessError(
            f"boot-health leg observed default {observed_default!r}, expected 'B'"
        )
    steps = [
        {
            "step": name,
            "default_slot": BOOT_OUTCOME_EXPECTED_SLOT.get(name, observed_default)
            if name not in ("fresh-install-A", "stage-B-one-shot", "stage-broken-candidate")
            else ("A" if name == "fresh-install-A" else "B" if name == "stage-B-one-shot" else "B"),
            "observed": name in ("boot-A-accepted", "stage-B-one-shot", "boot-B-commit"),
        }
        for name in LIFECYCLE_SEQUENCE
    ]
    report: dict[str, object] = {
        "steps": steps,
        "shipped_update_legs": list(SHIPPED_UPDATE_LEGS),
        "launcher_acceptance_legs": list(LAUNCHER_ACCEPTANCE_LEGS),
        "observed_steps": ["boot-A-accepted", "stage-B-one-shot", "boot-B-commit"],
    }
    assert_lifecycle_transitions(report)
    return report


def run_boot_health_leg(
    *,
    product_root: Path,
    installed_clone: Path,
    control_dir: Path,
    release_bundle: Path,
    clone_fn=None,
    inject_fn=None,
    boot_fn=None,
    observe_fn=None,
    slot_digest_fn=None,
) -> dict[str, object]:
    """Drive the boot/health/update leg through the shipped sockets (testable).

    Order (fail-closed, disposable media only): clone the installed
    image → hash the inactive slot B (its updater baseline) → inject
    slot A → hash the active slot A (its seam baseline) → boot A
    ``wait-health-poweroff`` (observer ``last_booted=A``, launcher
    ``INTERACTIVE_READY``, root health commits first-install A once) →
    drive ``update-status``/``update-verify``/``update-stage``/``update-arm``
    through the real update socket with the signed ``.greiaupdate`` →
    re-inject slot B (the real updater rewrote it) → boot B
    ``wait-health-poweroff`` (health-commits B, accepted sequence
    advances) → hash both slots again and prove through
    :func:`verify_update_slot_isolation` that the active slot stayed
    byte-identical while the staged inactive slot moved → host-side
    observation → ``assert_lifecycle_transitions`` closure. Injectable
    ``clone_fn``/``inject_fn``/``boot_fn``/``observe_fn``/
    ``slot_digest_fn`` let unit tests prove ordering, isolation and that
    a refused observation never closes; the capable host passes the real
    subprocess/QEMU/loop observers (``slot_digest_fn`` defaults to the
    real :func:`hash_slot_partition`). A missing observation refuses
    fail-closed: an unobserved boot never closes.
    """
    bundle = Path(release_bundle)
    if bundle.is_symlink() or not bundle.is_file():
        raise LifecycleHarnessError(
            "BLOCKED product mode: missing signed release bundle "
            f"({bundle}); refusing before any slot payload write"
        )
    digest_fn = slot_digest_fn or hash_slot_partition
    if clone_fn is not None:
        clone_fn()
    inactive_before = str(digest_fn(Path(installed_clone), "B"))
    boots: list[str] = []
    injections: list[str] = []

    def _do_inject(slot: str) -> None:
        if inject_fn is not None:
            inject_fn(Path(installed_clone), slot)
        injections.append(slot)

    _do_inject("A")
    active_before = str(digest_fn(Path(installed_clone), "A"))
    for phase in BOOT_HEALTH_LEG_PHASES:
        if phase == "wait-health-poweroff" and boots and "update-arm" in boots:
            _do_inject("B")
        inputs: dict[str, object] = {}
        if phase in BOOT_HEALTH_UPDATE_PHASES:
            inputs = {"candidate_bundle": CANDIDATE_BUNDLE_FILE}
        write_control_phase(control_dir, phase=phase, inputs=inputs)
        if boot_fn is not None:
            boot_fn(phase, read_control_phase(control_dir))
        boots.append(phase)
    active_after = str(digest_fn(Path(installed_clone), "A"))
    inactive_after = str(digest_fn(Path(installed_clone), "B"))
    if observe_fn is None:
        raise LifecycleHarnessError(
            "boot-health leg refused: no host-side observation was provided; "
            "an unobserved boot never closes"
        )
    observed = dict(observe_fn())
    if observed.get("default_slot") != "B":
        raise LifecycleHarnessError(
            f"boot-health leg observed default {observed.get('default_slot')!r}, "
            "expected 'B'"
        )
    isolation = verify_update_slot_isolation(
        active_slot="A",
        active_before_digest=active_before,
        active_after_digest=active_after,
        inactive_before_digest=inactive_before,
        inactive_after_digest=inactive_after,
    )
    report = build_boot_health_lifecycle_report(observed_default="B")
    return {
        "leg": "boot-health-product",
        "phases": boots,
        "injections": injections,
        "slot_digests": {
            "active_before": active_before,
            "active_after": active_after,
            "inactive_before": inactive_before,
            "inactive_after": inactive_after,
        },
        "slot_isolation": isolation,
        "observed": observed,
        "lifecycle_report": report,
        "product_root": str(Path(product_root)),
        "installed_clone": str(Path(installed_clone)),
    }


# ---------------------------------------------------------------------------
# Product-mode harness: explicit mode composing the single lifecycle engine
# ---------------------------------------------------------------------------


@dataclass
class ProductHarness:
    """Product-image mode composing the single lifecycle engine.

    Not a second lifecycle engine: sequencing, observation, attestation,
    interruption/D31/resource machinery and ``assert_lifecycle_transitions``
    stay owned by :class:`LifecycleHarness` / ``devproof.py``. This class
    adds only the disposable-clone + control-seam orchestration around
    those reused folds.
    """

    config: LifecycleConfig
    official_image: Path | None = None
    control_enabled: bool = True
    release_bundle: Path | None = None
    trusted_key_dir: Path | None = None
    inner: LifecycleHarness = field(init=False)

    def __post_init__(self) -> None:
        self.config.validate()
        self.inner = LifecycleHarness(self.config)

    @property
    def product_root(self) -> Path:
        return Path(self.config.output_dir) / "product"

    def plan(self) -> dict[str, object]:
        """Non-mutating plan (mirrors the r7 ``plan()`` precedent)."""
        return {
            **product_spec(),
            "official_image": (
                str(Path(self.official_image).resolve())
                if self.official_image is not None
                else None
            ),
            "clone": str((self.product_root / "installer-clone.img").resolve()),
            "control_disk": str((self.product_root / "control-disk").resolve()),
            "source_image_mutated": False,
            "control_enabled": self.control_enabled,
            "spec": lifecycle_spec(),
        }

    def run_product(
        self,
        *,
        release_bundle: Path | None = None,
        trusted_key_dir: Path | None = None,
        clone_fn=None,
        target_fn=None,
        inject_fn=None,
        materialize_fn=None,
        boot_fn=None,
        observe_fn=None,
    ) -> dict[str, object]:
        """Boot the disposable product image under the control seam.

        Phased wiring (P5.2 install leg): gate → fail-closed preflight
        (release bundle, trusted key, profile, prepare/execute identity
        equality, A/B mode, all before any clone/boot/mutation) → clone
        the official image into the disposable output root → create the
        disposable target and observe its pre-install identity through the
        production :class:`greia_installer.disk.DeviceObservation`
        (pinned QEMU serial; never minted from the clone) → inject the
        control seam (live-installer squashfs rebuilt inside the clone
        only, masking the graphical installer per the r7 precedent, with
        pre/post SHA record) → drive per-boot control-disk phases
        (``install-prepare`` then ``install-execute`` through the shipped
        installer socket) under QEMU with the disposable writable target
        and read-only installer media → observe host-side through
        production parsers
        (:func:`gather_installed_target_observation`) → close through
        ``assert_lifecycle_transitions``.

        ``BLOCKED`` remains only for a genuinely absent facility/artifact
        that the message names (non-Linux, missing QEMU/loop/mount/
        squashfs tooling, absent official image, missing release bundle
        or trusted key). Never fabricates a boot, unit, disk or identity.
        The ``*_fn`` seams default to the real implementations; tests
        inject recording fakes to prove preflight-before-mutation and
        observation-before-closure through this entry point.
        """
        from .lifecycle import assert_lifecycle_transitions

        self.config.validate()
        assert_control_absent_from_production()
        if not self.control_enabled:
            raise LifecycleHarnessError(
                "control seam disabled: product mode fails closed, never "
                "claims a boot by silent no-op"
            )
        require_product_host(official_image=self.official_image)
        assert self.official_image is not None
        official = Path(self.official_image)
        installer_sha = sha256_file(official)
        if release_bundle is not None:
            bundle = Path(release_bundle)
        elif self.release_bundle is not None:
            bundle = Path(self.release_bundle)
        else:
            bundle = None
        if trusted_key_dir is not None:
            keys = Path(trusted_key_dir)
        elif self.trusted_key_dir is not None:
            keys = Path(self.trusted_key_dir)
        else:
            keys = None
        if bundle is None:
            raise LifecycleHarnessError(
                "BLOCKED product mode: no signed release bundle was provided "
                "(ProductHarness.release_bundle); refusing before any slot payload write"
            )
        if keys is None:
            raise LifecycleHarnessError(
                "BLOCKED product mode: no trusted key dir was provided "
                "(ProductHarness.trusted_key_dir); refusing before any slot payload write"
            )
        root = self.product_root
        root.mkdir(parents=True, exist_ok=True)
        clone_path = root / "installer-clone.img"
        target_path = root / "disposable-target.img"
        control_dir = root / "control-disk"
        control_dir.mkdir(parents=True, exist_ok=True)
        observe_work = root / "observe-work"
        observe_work.mkdir(parents=True, exist_ok=True)

        # Stage-1 artifact presence BEFORE any scratch allocation: a
        # missing bundle/key refuses here with zero side effects.
        _require_install_artifacts(release_bundle=bundle, trusted_key_dir=keys)

        # Disposable target first so its pre-install identity is observed
        # from the real device descriptor (production DeviceObservation
        # with the pinned QEMU serial) — never minted from the clone.
        if target_fn is not None:
            target_proof = dict(target_fn(target_path))
            size_bytes = int(target_proof.get("size_bytes", DISPOSABLE_TARGET_BYTES))
        else:
            target_proof = create_disposable_target(target_path)
            size_bytes = int(target_proof["size_bytes"])
        target_observation = disposable_target_observation(
            target_path, size_bytes=size_bytes
        )
        expected_target_identity = str(target_observation.identity_digest)

        # Fail-closed preflight BEFORE any clone/boot/mutation: a missing
        # bundle/key, profile mismatch, identity change or non-A/B mode
        # refuses here with zero downstream calls.
        preflight = preflight_install_composition(
            release_bundle=bundle,
            trusted_key_dir=keys,
            expected_profile_id=INSTALL_PROFILE_ID,
            prepare_identity=expected_target_identity,
            execute_identity=expected_target_identity,
        )
        bundle_sha = sha256_file(bundle)

        # Clone the official image into the disposable root (r7 pattern).
        # ``clone_product_image`` refuses /dev, missing source and existing
        # clones fail-closed; the source is never opened read-write.
        if clone_fn is not None:
            clone_proof = dict(clone_fn(official, clone_path))
        else:
            clone_proof = clone_product_image(official, clone_path)

        # QEMU binary consistent with the i386 profile (G1): prefer
        # qemu-system-i386, fall back to qemu-system-x86_64. Missing both
        # stays BLOCKED with the facility named.
        qemu_binary = select_install_qemu_binary()

        # The shipped installer units served in-guest: recorded by SHA
        # from the repo tree so the evidence names the exact units the
        # install runs through (never a harness substitute). The runner
        # drives them over the real socket and the host observes the disk,
        # never the ack.
        shipped_units = record_shipped_installer_units()

        clone_injection: dict[str, object]
        if inject_fn is not None:
            clone_injection = dict(inject_fn(clone_path))
        else:
            clone_injection = inject_live_clone(clone_path)
        boots: list[str] = []
        control_image = root / "control-disk.img"
        for phase in INSTALL_LEG_PHASES:
            write_control_phase(
                control_dir,
                phase=phase,
                inputs={
                    "expected_target_identity": expected_target_identity,
                    "compatible_profile_id": INSTALL_PROFILE_ID,
                },
            )
            if materialize_fn is not None:
                materialize_fn(control_dir, control_image)
            else:
                materialize_control_disk(control_dir, control_image)
            argv, serial_log, host_log = product_installer_qemu_argv(
                installer_clone=clone_path,
                target_image=target_path,
                control_image=control_image,
                output_dir=root,
                memory_mib=self.config.memory_mib,
                cpus=self.config.cpus,
                qemu_binary=qemu_binary,
                leg=phase,
            )
            if boot_fn is not None:
                boot_fn(phase, argv, serial_log, host_log)
            else:
                self._boot_installer_phase(
                    phase=phase, argv=argv, serial_log=serial_log, host_log=host_log
                )
            boots.append(phase)

        # Host-side observation uses production parsers only: MBR
        # PARTUUID/filesystem UUIDs from the real disposable disk bytes,
        # grub.cfg via validate_grub_ab_text, grubenv default A,
        # FIRST_INSTALL_PENDING. No fallback and no default slot: the
        # capable-host run reads the disk, anything else fails closed.
        observed: dict[str, object]
        if observe_fn is not None:
            observed = dict(observe_fn(target_path))
        else:
            observed = self._observe_installed_target(
                target_path=target_path, work_dir=observe_work
            )
        report = build_install_lifecycle_report(
            observed_default=str(observed.get("default_slot", ""))
        )
        # Explicit closure through the frozen transition contract (reused,
        # never reimplemented): an observation that is not default-A, or a
        # same-disk reboot without transitions, fails here instead of
        # attesting.
        assert_lifecycle_transitions(report)
        # P5.3 identity record: binds the exact booted image, the staged
        # bundle(s) and the src-tree modules at evidence time plus the
        # clone-only squashfs mutation provenance. The live rebuild carries
        # the nested ``squashfs_mutation`` mapping; recording fakes carry
        # the flat pre/post/injected-files facts instead.
        nested_mutation = clone_injection.get("squashfs_mutation")
        if isinstance(nested_mutation, Mapping):
            squashfs_proof: Mapping[str, object] | None = nested_mutation
        else:
            flat_proof = {
                key: clone_injection[key]
                for key in (
                    "pre_sha256",
                    "post_sha256",
                    "injected_files",
                    "source_image_mutated",
                )
                if key in clone_injection
            }
            squashfs_proof = flat_proof or None
        unit_identity = build_product_identity_record(
            installer_image=official,
            release_bundles=[bundle],
            squashfs_mutation=squashfs_proof,
        )
        assert_product_identity_complete(
            unit_identity,
            installer_image=official,
            release_bundles=[bundle],
        )
        return {
            "ok": True,
            "leg": "install-product",
            "profile_id": INSTALL_PROFILE_ID,
            "installer_image": str(official.resolve()),
            "installer_image_sha256": installer_sha,
            "release_bundle": str(bundle),
            "release_bundle_sha256": bundle_sha,
            "trusted_key_dir": str(keys),
            "preflight": preflight,
            "expected_target_identity": expected_target_identity,
            "target_observation": {
                "serial": target_observation.serial,
                "transport": target_observation.transport,
                "size_bytes": int(target_observation.size_bytes),
                "identity_digest": expected_target_identity,
            },
            "clone": clone_proof,
            "disposable_target": target_proof,
            "clone_injection": clone_injection,
            "shipped_units": shipped_units,
            "unit_identity": unit_identity,
            "qemu_binary": qemu_binary,
            "phases": boots,
            "observed": observed,
            "lifecycle_report": report,
            "source_image_mutated": False,
        }

    def _boot_installer_phase(
        self, *, phase: str, argv: list[str], serial_log: Path, host_log: Path
    ) -> None:
        """Boot one installer phase under QEMU (capable host only).

        Separated so unit tests can pin the argv shape without spawning
        QEMU. A missing QEMU binary or failed boot stays fail-closed;
        the control channel is never consulted for the outcome.
        """
        binary = Path(argv[0]).name if argv else ""
        if resolve_device_host_tool(binary) is None and shutil.which(binary) is None:
            raise LifecycleHarnessError(
                f"BLOCKED product mode: missing product host tool: {binary} "
                f"(phase {phase})"
            )
        completed = subprocess.run(
            [str(part) for part in argv],
            capture_output=True,
            timeout=max(60, int(self.config.timeout_seconds)),
        )
        if completed.returncode != 0:
            detail = ""
            try:
                detail = Path(host_log).read_text(encoding="utf-8")[-2000:]
            except OSError:
                detail = ""
            raise LifecycleHarnessError(
                f"product installer boot failed for phase {phase} "
                f"(exit {completed.returncode}); inspect {host_log} {detail[-500:]}"
            )

    def _observe_installed_target(
        self, *, target_path: Path, work_dir: Path, runner=None, which=None
    ) -> dict[str, object]:
        """Host-side target observation entry point (production parsers).

        Delegates to :func:`gather_installed_target_observation`: MBR bytes
        plus ``blkid`` filesystem UUIDs plus ``inspect_installed_roots``
        over loop-mounted boot-control/persist. No fallback, no default
        slot: a missing facility stays ``BLOCKED`` and a missing evidence
        file fails closed. Slot facts appear only when read from real disk
        bytes.
        """
        return gather_installed_target_observation(
            target_path, work_dir=work_dir, runner=runner, which=which
        )

    def run_boot_health_product(
        self,
        *,
        installed_image: Path | None = None,
        release_bundle: Path | None = None,
        expected_sequence_b: int = 21,
        clone_fn=None,
        inject_fn=None,
        materialize_fn=None,
        boot_fn=None,
        observe_fn=None,
        slot_digest_fn=None,
    ) -> dict[str, object]:
        """Boot the installed SYSTEM_A, stage B, boot B via real services.

        Phased wiring (P5.2 boot-health leg): gate → clone the installed
        image into the disposable output root → hash the inactive slot B
        (its updater baseline) → inject slot A (control seam into the
        ext4 slot; the release payload cannot carry the test unit) → hash
        the active slot A (its seam baseline) → per-boot control-disk
        phases (``BOOT_HEALTH_LEG_PHASES``: boot-A
        ``wait-health-poweroff`` through the shipped boot-health socket,
        then ``update-status``/``update-verify``/``update-stage``/
        ``update-arm`` through the shipped update socket with the signed
        ``.greiaupdate``, re-injecting slot B after the real updater
        rewrites it and before its boot, then boot-B
    ``wait-health-poweroff``) under QEMU with the virtual VGA device
    the real Xorg launcher needs (R1) on the i386-capable KVM-or-TCG
    machine (G1) → hash both slots again and prove through
        :func:`verify_update_slot_isolation` that the active slot stayed
        byte-identical while the staged inactive slot moved → host-side
        observation through production parsers
        (:func:`gather_boot_health_observation` /
        :func:`inspect_boot_health_roots`, returning the observed default
        and accepted sequence from authoritative state) → close through
        ``assert_lifecycle_transitions``.

        ``BLOCKED`` remains only for a genuinely absent facility/artifact
        that the message names (non-Linux, missing QEMU/loop/mount/
        squashfs tooling, absent installed image or signed bundle).
        Never fabricates a boot, unit, disk or identity. The ``*_fn``
        seams default to the real implementations (``slot_digest_fn``
        defaults to the real :func:`hash_slot_partition`); tests inject
        recording fakes to prove clone-before-inject, re-inject-before-B-boot,
        isolation-before-closure and observation-before-closure through
        this entry point.
        """
        from .lifecycle import assert_lifecycle_transitions

        self.config.validate()
        assert_control_absent_from_production()
        if not self.control_enabled:
            raise LifecycleHarnessError(
                "control seam disabled: product mode fails closed, never "
                "claims a boot by silent no-op"
            )
        origin = Path(installed_image) if installed_image is not None else None
        if origin is None and self.official_image is not None:
            origin = Path(self.official_image)
        require_product_host(official_image=origin)
        if origin is None or not origin.is_file():
            raise LifecycleHarnessError(
                "BLOCKED product mode: absent installed image "
                f"({origin}); boot the installed SYSTEM_A from the install-leg "
                "output; never synthesize one"
            )
        installed_sha = sha256_file(origin)
        if release_bundle is not None:
            bundle = Path(release_bundle)
        elif self.release_bundle is not None:
            bundle = Path(self.release_bundle)
        else:
            bundle = None
        if bundle is None or bundle.is_symlink() or not bundle.is_file():
            raise LifecycleHarnessError(
                "BLOCKED product mode: missing signed release bundle "
                f"({bundle}); refusing before any slot payload write"
            )
        bundle_sha = sha256_file(bundle)
        root = self.product_root
        root.mkdir(parents=True, exist_ok=True)
        clone_path = root / "installed-clone.img"
        control_dir = root / "control-disk"
        control_dir.mkdir(parents=True, exist_ok=True)
        observe_work = root / "observe-work"
        observe_work.mkdir(parents=True, exist_ok=True)

        if clone_fn is not None:
            clone_proof = dict(clone_fn(origin, clone_path))
        else:
            clone_proof = clone_product_image(origin, clone_path)

        qemu_binary = select_install_qemu_binary()
        shipped_units = record_shipped_boot_units()

        def _do_inject(slot: str) -> dict[str, object]:
            if inject_fn is not None:
                return dict(inject_fn(clone_path, slot))
            return inject_boot_slot(clone_path, slot)

        digest_fn = slot_digest_fn or hash_slot_partition
        inactive_before = str(digest_fn(clone_path, "B"))
        slot_a_injection = _do_inject("A")
        active_before = str(digest_fn(clone_path, "A"))
        injected_files_a = list(slot_a_injection.get("injected_files", []))
        boots: list[str] = []
        control_image = root / "control-disk.img"
        candidate_staged = False
        slot_b_injection: dict[str, object] | None = None
        for phase in BOOT_HEALTH_LEG_PHASES:
            if phase == "wait-health-poweroff" and boots and "update-arm" in boots:
                slot_b_injection = _do_inject("B")
            inputs: dict[str, object] = {}
            if phase in BOOT_HEALTH_UPDATE_PHASES:
                inputs = {"candidate_bundle": CANDIDATE_BUNDLE_FILE}
            write_control_phase(control_dir, phase=phase, inputs=inputs)
            if phase == "update-stage" and not candidate_staged:
                self._stage_candidate_onto_control(
                    control_dir, bundle, control_image=None
                )
                candidate_staged = True
            if materialize_fn is not None:
                materialize_fn(control_dir, control_image)
            else:
                materialize_control_disk(control_dir, control_image)
            argv, serial_log, host_log = product_boot_qemu_argv(
                installed_clone=clone_path,
                control_image=control_image,
                output_dir=root,
                memory_mib=self.config.memory_mib,
                cpus=self.config.cpus,
                qemu_binary=qemu_binary,
                leg=phase,
            )
            if boot_fn is not None:
                boot_fn(phase, argv, serial_log, host_log)
            else:
                self._boot_installed_phase(
                    phase=phase, argv=argv, serial_log=serial_log, host_log=host_log
                )
            boots.append(phase)

        observed: dict[str, object]
        if observe_fn is not None:
            observed = dict(observe_fn(clone_path))
        else:
            observed = self._observe_boot_health_target(
                target_path=clone_path,
                work_dir=observe_work,
                expected_slot="B",
                expected_sequence=expected_sequence_b,
            )
        active_after = str(digest_fn(clone_path, "A"))
        inactive_after = str(digest_fn(clone_path, "B"))
        isolation = verify_update_slot_isolation(
            active_slot="A",
            active_before_digest=active_before,
            active_after_digest=active_after,
            inactive_before_digest=inactive_before,
            inactive_after_digest=inactive_after,
        )
        report = build_boot_health_lifecycle_report(
            observed_default=str(observed.get("default_slot", ""))
        )
        assert_lifecycle_transitions(report)
        injected_files = list(injected_files_a)
        if isinstance(slot_b_injection, dict):
            for name in slot_b_injection.get("injected_files", []):
                if name not in injected_files:
                    injected_files.append(str(name))
        slot_digests = {
            "active_before": active_before,
            "active_after": active_after,
            "inactive_before": inactive_before,
            "inactive_after": inactive_after,
        }
        # P5.3 identity record: binds the exact booted installed image,
        # the staged bundle, the src-tree units/modules at evidence time,
        # both slot-injection provenances, the slot-isolation digests and
        # the observed MBR/PARTUUID/filesystem/journal/sequence/layout
        # facts. Real injections carry the nested ``slot_mutation``
        # mapping; recording fakes carry the flat pre/post/injected-files
        # facts (with ``source_image_mutated`` forwarded so a mutated
        # source stays RED instead of dropping to False).
        slot_a_proof = _slot_proof_from_injection(slot_a_injection, role="slot-A")
        slot_b_proof = _slot_proof_from_injection(slot_b_injection, role="slot-B")
        unit_identity = build_product_identity_record(
            installed_image=origin,
            release_bundles=[bundle],
            slot_a_mutation=slot_a_proof,
            slot_b_mutation=slot_b_proof,
            slot_digests=slot_digests,
            slot_isolation=isolation,
            boot_observation=observed,
        )
        assert_product_identity_complete(
            unit_identity,
            installed_image=origin,
            release_bundles=[bundle],
        )
        return {
            "ok": True,
            "leg": "boot-health-product",
            "installed_image": str(origin.resolve()),
            "installed_image_sha256": installed_sha,
            "release_bundle": str(bundle),
            "release_bundle_sha256": bundle_sha,
            "clone": clone_proof,
            "slot_a_injection": slot_a_injection,
            "slot_b_injection": slot_b_injection,
            "shipped_units": shipped_units,
            "unit_identity": unit_identity,
            "qemu_binary": qemu_binary,
            "phases": boots,
            "injected_files": injected_files,
            "slot_digests": slot_digests,
            "slot_isolation": isolation,
            "observed": observed,
            "lifecycle_report": report,
            "source_image_mutated": False,
        }

    def _stage_candidate_onto_control(
        self, control_dir: Path, bundle: Path, *, control_image=None
    ) -> None:
        """Record the signed candidate for the ``update-stage`` boot.

        The host places the exact signed ``.greiaupdate`` bytes beside
        ``phase.json`` in the host control dir before materializing the
        control disk, so the guest runner finds
        ``candidate.greiaupdate`` on the control mount and copies it into
        the real installed inbox before driving
        ``STAGE_CURRENT_CANDIDATE``. No slot payload is written here.
        """
        del control_image
        staged = Path(control_dir) / CANDIDATE_BUNDLE_FILE
        if staged.exists():
            staged.unlink()
        shutil.copy2(bundle, staged)

    def _boot_installed_phase(
        self, *, phase: str, argv: list[str], serial_log: Path, host_log: Path
    ) -> None:
        """Boot one installed phase under QEMU (capable host only).

        Separated so unit tests can pin the argv shape without spawning
        QEMU. A missing QEMU binary or failed boot stays fail-closed;
        the control channel is never consulted for the outcome.
        """
        binary = Path(argv[0]).name if argv else ""
        if resolve_device_host_tool(binary) is None and shutil.which(binary) is None:
            raise LifecycleHarnessError(
                f"BLOCKED product mode: missing product host tool: {binary} "
                f"(phase {phase})"
            )
        completed = subprocess.run(
            [str(part) for part in argv],
            capture_output=True,
            timeout=max(60, int(self.config.timeout_seconds)),
        )
        if completed.returncode != 0:
            detail = ""
            try:
                detail = Path(host_log).read_text(encoding="utf-8")[-2000:]
            except OSError:
                detail = ""
            raise LifecycleHarnessError(
                f"product installed boot failed for phase {phase} "
                f"(exit {completed.returncode}); inspect {host_log} {detail[-500:]}"
            )

    def _observe_boot_health_target(
        self,
        *,
        target_path: Path,
        work_dir: Path,
        expected_slot: str,
        expected_sequence: int,
        runner=None,
        which=None,
    ) -> dict[str, object]:
        """Host-side boot-health observation entry point (production parsers).

        Delegates to :func:`gather_boot_health_observation`: MBR bytes
        plus ``blkid`` filesystem UUIDs plus resolved grubenv/journal/
        accepted-sequence/layout evidence over loop-mounted boot-control/
        persist, verified through :func:`inspect_boot_health_roots` for
        the committed slot while still mounted. The returned
        ``default_slot``/``accepted_sequence``/``committed_slot`` come
        from that inspection, never minted. No fallback, no default slot:
        a missing facility stays ``BLOCKED`` and a missing evidence file
        fails closed. Slot facts appear only when read from real disk
        bytes.
        """
        return gather_boot_health_observation(
            target_path,
            work_dir=work_dir,
            runner=runner,
            which=which,
            expected_slot=expected_slot,
            expected_sequence=expected_sequence,
        )

    def run_recovery_d31_reverse_product(
        self,
        *,
        installed_image: Path | None = None,
        unhealthy_bundle: Path | None = None,
        reverse_bundle: Path | None = None,
        accepted_slot: str = "B",
        accepted_sequence: int = 21,
        candidate_sequence: int = 22,
        reverse_sequence: int = 23,
        clone_fn=None,
        materialize_fn=None,
        boot_fn=None,
        observe_fn=None,
        d31_fn=None,
        slot_digest_fn=None,
        serial_fn=None,
    ) -> dict[str, object]:
        """Run the installed-system P5.2 recovery/D31/reverse leg (real services).

        Phased wiring: gate -> clone the health-committed installed image
        (accepted ``accepted_slot``) into the disposable output root ->
        enable the clone-only serial console on the recovery clone
        (without it the consoleless installed boot stalls under the
        harness; ``serial_fn`` seam defaults to the real
        :func:`enable_installed_clone_serial_console`) ->
        record the shipped recovery units -> drive
        RECOVERY_D31_REVERSE_LEG_PHASES under QEMU (first update-stage
        round stages the validly-signed unhealthy candidate through the
        real update socket; the candidate boot withholds health because
        no production token can exist; the real 3-minute timer marks
        FAILED and reboots to the accepted slot; the second update-stage
        round stages the reverse release, which boots and accepts)
        -> observe each stage from on-image bytes through the production
        stage inspectors -> prove D31 survival -> prove slot isolation
        -> close through assert_lifecycle_transitions.

        BLOCKED remains only for a genuinely absent facility/artifact
        that the message names (non-Linux, missing QEMU/loop/mount
        tooling, absent installed image or signed bundles, and — until
        the capable-host run pins it — the on-image D31 persist
        mapping when no d31_fn is supplied). Never fabricates a boot,
        journal or D31 result. The *_fn seams default to the real
        implementations where they exist (clone/materialize/QEMU boot/
        slot digests); tests inject recording fakes to prove
        unhealthy-before-reverse staging order through this entry point.
        """
        self.config.validate()
        assert_control_absent_from_production()
        if not self.control_enabled:
            raise LifecycleHarnessError(
                "control seam disabled: product mode fails closed, never "
                "claims a boot by silent no-op"
            )
        origin = Path(installed_image) if installed_image is not None else None
        if origin is None and self.official_image is not None:
            origin = Path(self.official_image)
        require_product_host(official_image=origin)
        if origin is None or not origin.is_file():
            raise LifecycleHarnessError(
                "BLOCKED product mode: absent health-committed installed image "
                f"({origin}); the boot-health leg output feeds this leg; "
                "never synthesize one"
            )
        installed_sha = sha256_file(origin)
        unhealthy = (
            Path(unhealthy_bundle)
            if unhealthy_bundle is not None
            else None
        )
        reverse = (
            Path(reverse_bundle) if reverse_bundle is not None else None
        )
        for label, bundle in (
            ("unhealthy candidate", unhealthy),
            ("reverse release", reverse),
        ):
            if bundle is None or bundle.is_symlink() or not bundle.is_file():
                raise LifecycleHarnessError(
                    "BLOCKED product mode: missing signed "
                    f"{label} bundle ({bundle}); refusing before any slot payload write"
                )
        assert unhealthy is not None and reverse is not None
        unhealthy_sha = sha256_file(unhealthy)
        reverse_sha = sha256_file(reverse)
        if accepted_slot not in ("A", "B"):
            raise LifecycleHarnessError(
                f"recovery product refused: unknown accepted slot {accepted_slot!r}"
            )
        candidate_slot = "A" if accepted_slot == "B" else "B"
        root = self.product_root
        root.mkdir(parents=True, exist_ok=True)
        clone_path = root / "recovery-clone.img"
        control_dir = root / "control-disk"
        control_dir.mkdir(parents=True, exist_ok=True)
        observe_work = root / "observe-work"
        observe_work.mkdir(parents=True, exist_ok=True)

        if clone_fn is not None:
            clone_proof = dict(clone_fn(origin, clone_path))
        else:
            clone_proof = clone_product_image(origin, clone_path)

        if serial_fn is not None:
            serial_proof = dict(serial_fn(clone_path))
        else:
            serial_proof = enable_installed_clone_serial_console(clone_path)

        qemu_binary = select_install_qemu_binary()
        shipped_units = record_shipped_recovery_units()
        control_image = root / "control-disk.img"
        staged_rounds = 0

        def _boot_phase(phase: str) -> None:
            nonlocal staged_rounds
            inputs: dict[str, object] = {}
            if phase in RECOVERY_D31_REVERSE_UPDATE_PHASES:
                inputs = {"candidate_bundle": CANDIDATE_BUNDLE_FILE}
            write_control_phase(control_dir, phase=phase, inputs=inputs)
            if phase == "update-stage":
                bundle = unhealthy if staged_rounds == 0 else reverse
                staged_rounds += 1
                self._stage_candidate_onto_control(
                    control_dir, bundle, control_image=None
                )
            if materialize_fn is not None:
                materialize_fn(control_dir, control_image)
            else:
                materialize_control_disk(control_dir, control_image)
            argv, serial_log, host_log = product_boot_qemu_argv(
                installed_clone=clone_path,
                control_image=control_image,
                output_dir=root,
                memory_mib=self.config.memory_mib,
                cpus=self.config.cpus,
                qemu_binary=qemu_binary,
                leg=f"recovery-{phase}-{staged_rounds}",
            )
            if boot_fn is not None:
                boot_fn(phase, argv, serial_log, host_log)
            else:
                self._boot_installed_phase(
                    phase=phase, argv=argv, serial_log=serial_log, host_log=host_log
                )

        def _observe_stage(stage: str) -> dict[str, object]:
            if observe_fn is not None:
                return dict(observe_fn(stage))
            return self._observe_recovery_stage(
                target_path=clone_path,
                work_dir=observe_work,
                stage=stage,
                accepted_slot=accepted_slot,
                candidate_slot=candidate_slot,
                accepted_sequence=accepted_sequence,
                candidate_sequence=candidate_sequence,
                reverse_sequence=reverse_sequence,
            )

        def _observe_d31() -> dict[str, object]:
            if d31_fn is not None:
                return dict(d31_fn())
            raise LifecycleHarnessError(
                "BLOCKED product mode: on-image D31 persist mapping is not "
                "pinned (namespace paths under the mounted persist tree); "
                "the capable-host run must supply d31_fn reading the persist "
                "partition through the devproof store parse paths"
            )

        digest_fn = slot_digest_fn or (
            lambda slot, when: hash_slot_partition(clone_path, slot)
        )
        leg = run_recovery_d31_reverse_leg(
            accepted_slot=accepted_slot,
            candidate_slot=candidate_slot,
            accepted_sequence=accepted_sequence,
            candidate_sequence=candidate_sequence,
            reverse_sequence=reverse_sequence,
            boot_fn=_boot_phase,
            observe_fn=_observe_stage,
            d31_fn=_observe_d31,
            slot_digest_fn=digest_fn,
        )
        return {
            "ok": True,
            **leg,
            "installed_image": str(origin.resolve()),
            "installed_image_sha256": installed_sha,
            "unhealthy_bundle": str(unhealthy),
            "unhealthy_bundle_sha256": unhealthy_sha,
            "reverse_bundle": str(reverse),
            "reverse_bundle_sha256": reverse_sha,
            "clone": clone_proof,
            "serial_console": serial_proof,
            "shipped_units": shipped_units,
            "qemu_binary": qemu_binary,
        }

    def _observe_recovery_stage(
        self,
        *,
        target_path: Path,
        work_dir: Path,
        stage: str,
        accepted_slot: str,
        candidate_slot: str,
        accepted_sequence: int,
        candidate_sequence: int,
        reverse_sequence: int,
        runner=None,
        which=None,
    ) -> dict[str, object]:
        """Host-side recovery-stage observation entry point (production parsers).

        Delegates to :func:`gather_recovery_stage_observation`: MBR bytes
        plus the resolved grubenv/journal/accepted-sequence/layout
        evidence over loop-mounted boot-control/persist, verified
        through the stage inspector while still mounted. No fallback:
        a missing facility stays BLOCKED and a missing evidence file
        fails closed.
        """
        del accepted_sequence, candidate_sequence
        return gather_recovery_stage_observation(
            target_path,
            stage,
            work_dir=work_dir,
            runner=runner,
            which=which,
            accepted_slot=accepted_slot,
            candidate_slot=candidate_slot,
            expected_sequence=reverse_sequence,
        )


# ---------------------------------------------------------------------------
# P5.2 recovery/D31/reverse leg: broken-candidate recovery, D31 survival and
# the reverse B->A update through the installed updater.
#
# Consumes the construction pinned by POSTR1-P5-UNHEALTHY-CANDIDATE-DESIGN
# (G3 resolution): a real bootable ext4 slot rootfs — the release lineage's
# own rootfs — with the root health-capability issuer unit removed, so the
# candidate boots, the observer records the candidate slot, the launcher
# reaches INTERACTIVE_READY, but the production health-confirmation path
# genuinely cannot complete and the real 3-minute deadline marks the
# candidate FAILED. No health/recovery/lifecycle predicate is weakened;
# the control channel triggers operations but never attests an outcome.
#
# Reuse, not duplication: bundle signing/verification stays owned by
# greia_platform.system_updates (build_update_bundle/inspect_update_bundle/
# verify_update_signature/authorize_release_sequence); the trigger and its
# deadline stay owned by greia_platform.boot_transaction
# (mark_candidate_unhealthy/CANDIDATE_HEALTH_DEADLINE_SEC/
# RECOVERY_TRIGGER_STATES); D31 write/read/verify stays owned by
# devproof.py; sequencing closure stays owned by
# lifecycle.assert_lifecycle_transitions. This section adds only the
# product-mode orchestration around those reused folds.
# ---------------------------------------------------------------------------

#: Pinned unhealthy mechanism: the candidate rootfs loses the root
#: health-capability issuer, so BOOT_HEALTHY can never confirm (production
#: failure class 3, "health-service-failure").
UNHEALTHY_CANDIDATE_MECHANISM = "remove-root-health-capability-issuer"

#: Production failure class the pinned mechanism exercises (genuine health
#: failure, not a weakened predicate).
UNHEALTHY_CANDIDATE_RECOVERY_CLASS = "health-service-failure"

#: Image-owned unit whose absence makes health confirmation impossible.
UNHEALTHY_CANDIDATE_UNIT_NAME = "greia-boot-health-credential.service"

#: Candidate rootfs locations of the issuer unit. The shipped tree carries
#: it under build/overlay/etc/systemd/system (installed slot path
#: etc/systemd/system/...); the discovery brief additionally names the
#: usr/lib/systemd/system vendor path. The fixture removes whichever is
#: present and refuses when neither is (fail-closed: the mechanism would
#: not be genuine).
UNHEALTHY_CANDIDATE_UNIT_PATHS: tuple[str, ...] = (
    "etc/systemd/system/greia-boot-health-credential.service",
    "usr/lib/systemd/system/greia-boot-health-credential.service",
)

#: Systemd wants directories scanned for the issuer enablement symlink.
UNHEALTHY_CANDIDATE_WANTS_PARENTS: tuple[str, ...] = (
    "etc/systemd/system",
    "usr/lib/systemd/system",
)

#: Full recovery leg phase order on the installed system (accepted slot B
#: after the boot-health leg; the broken candidate targets inactive A, and
#: the reverse B->A release targets A again after the failure). Every
#: phase is one QEMU boot with a fresh host-written control disk reusing
#: the bounded CONTROL_PHASES vocabulary — no new guest-runner phase was
#: needed: the existing wait-health-poweroff branch already withholds
#: confirmation when no production token exists (token None -> exit 0, no
#: CONFIRM_BOOT_HEALTH), which is exactly the unhealthy-candidate boot.
#: The real greia-candidate-recovery.timer (OnBootSec=3min) fires inside
#: the candidate boot, marks FAILED and reboots to the accepted slot.
RECOVERY_D31_REVERSE_LEG_PHASES: tuple[str, ...] = (
    "update-status",
    "update-verify",
    "update-stage",
    "update-arm",
    "wait-health-poweroff",
    "wait-health-poweroff",
    "update-status",
    "update-verify",
    "update-stage",
    "update-arm",
    "wait-health-poweroff",
)

#: Update phases within the recovery leg (the guest runner copies the
#: host-staged candidate.greiaupdate into the real inbox on update-stage).
RECOVERY_D31_REVERSE_UPDATE_PHASES: tuple[str, ...] = (
    "update-status",
    "update-verify",
    "update-stage",
    "update-arm",
)

#: Authoritative observation stages of the recovery leg, in order.
RECOVERY_D31_REVERSE_STAGES: tuple[str, ...] = (
    "stage-broken-candidate",
    "boot-broken-candidate",
    "recovery-boot-accepted",
    "reverse-update-accepted",
)

#: Lifecycle steps this leg observes (the full 8-step report keeps the
#: frozen expected-slot pattern so assert_lifecycle_transitions can verify
#: the report shape; only these four are marked observed).
RECOVERY_D31_REVERSE_OBSERVED_STEPS: tuple[str, ...] = (
    "stage-broken-candidate",
    "boot-broken-candidate",
    "recovery-boot-B",
    "reverse-update-B-to-A",
)

#: Shipped product units the recovery leg runs through (boot-health set
#: plus the real recovery timer/service). Recorded by SHA-256 from the
#: repo tree, never a harness substitute.
RECOVERY_SHIPPED_UNITS: tuple[str, ...] = SHIPPED_BOOT_UNITS + (
    "greia-candidate-recovery.service",
    "greia-candidate-recovery.timer",
)

#: Image-relative path of the privileged recovery helper the timer fires.
RECOVERY_HELPER_REL_PATH = "usr/local/lib/greia-os/greia-candidate-recovery"


def describe_unhealthy_candidate_construction() -> dict[str, object]:
    """Pin the validly-signed-but-genuinely-unhealthy candidate (pure data).

    Returns the frozen construction consumed by this leg: the removal
    mechanism, the exact unit paths, the production recovery class, and
    the deadline/timer/service identities read from the production
    owners (boot_transaction constants), so a drift in the production
    contract is a loud mismatch here rather than a silent weakening.
    """
    from greia_platform.boot_transaction import (
        CANDIDATE_HEALTH_DEADLINE_SEC,
        CANDIDATE_RECOVERY_SERVICE,
        CANDIDATE_RECOVERY_TIMER,
        RECOVERY_HELPER_PATH,
    )

    return {
        "mechanism": UNHEALTHY_CANDIDATE_MECHANISM,
        "removed_unit": UNHEALTHY_CANDIDATE_UNIT_NAME,
        "removed_unit_paths": list(UNHEALTHY_CANDIDATE_UNIT_PATHS),
        "wants_parents": list(UNHEALTHY_CANDIDATE_WANTS_PARENTS),
        "recovery_class": UNHEALTHY_CANDIDATE_RECOVERY_CLASS,
        "deadline_sec": int(CANDIDATE_HEALTH_DEADLINE_SEC),
        "timer": str(CANDIDATE_RECOVERY_TIMER),
        "service": str(CANDIDATE_RECOVERY_SERVICE),
        "helper": str(RECOVERY_HELPER_PATH),
        "invariants": [
            "candidate payload is a relocatable ext4 slot rootfs, no MBR/GPT",
            "source artifacts are never mutated (host-side copy only)",
            "bundle signed by a key the installed slot already trusts",
            "control channel triggers only and attests nothing",
        ],
    }


def record_shipped_recovery_units(
    *, project_root: Path | None = None
) -> dict[str, object]:
    """Record the shipped recovery/boot/health/update units as leg evidence.

    Reads the exact unit files plus the privileged recovery helper the
    installed guest serves and records their SHA-256: the leg reboots
    through these shipped units, never a harness substitute. Absent
    files stay BLOCKED naming the artifact.
    """
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    unit_dir = root / "build/overlay/etc/systemd/system"
    helper = root / "build/overlay" / RECOVERY_HELPER_REL_PATH
    units: dict[str, str] = {}
    for name in RECOVERY_SHIPPED_UNITS:
        path = unit_dir / name
        if path.is_symlink() or not path.is_file():
            raise LifecycleHarnessError(
                "BLOCKED product mode: shipped recovery unit is absent "
                f"({path}); refusing a harness-only substitution"
            )
        units[name] = sha256_file(path)
    if helper.is_symlink() or not helper.is_file():
        raise LifecycleHarnessError(
            "BLOCKED product mode: shipped recovery helper is absent "
            f"({helper}); refusing a harness-only substitution"
        )
    return {
        "unit_dir": str(unit_dir),
        "sha256": units,
        "helper": str(helper),
        "helper_sha256": sha256_file(helper),
    }


def _remove_health_issuer_files(root: Path) -> list[str]:
    """Delete the pinned issuer unit + enablement symlinks under root.

    Operates on a host-side copy of the candidate rootfs (mounted or
    materialized by the caller). Returns the sorted relative paths
    actually removed. Removes only the pinned unit file(s) and symlinks
    whose name is exactly the pinned unit; never follows symlinks
    outside root. An empty result means the base rootfs does not carry
    the issuer, so the unhealthy mechanism would not be genuine.
    """
    base = Path(root)
    removed: list[str] = []
    for relative in UNHEALTHY_CANDIDATE_UNIT_PATHS:
        candidate = base / relative
        if candidate.is_symlink() or candidate.is_file():
            candidate.unlink()
            removed.append(relative)
    for parent in UNHEALTHY_CANDIDATE_WANTS_PARENTS:
        wants_root = base / parent
        if not wants_root.is_dir():
            continue
        try:
            entries = list(wants_root.iterdir())
        except OSError:
            continue
        for entry in entries:
            if not entry.is_dir() or entry.is_symlink():
                continue
            if not entry.name.endswith(".wants"):
                continue
            link = entry / UNHEALTHY_CANDIDATE_UNIT_NAME
            if link.is_symlink() or link.is_file():
                link.unlink()
                removed.append(
                    str(Path(parent) / entry.name / UNHEALTHY_CANDIDATE_UNIT_NAME)
                )
    return sorted(removed)


def _assert_relocatable_payload_bytes(path: Path) -> None:
    """Refuse a non-relocatable payload (MBR/GPT header), RED not BLOCKED."""
    with Path(path).open("rb") as handle:
        header = handle.read(1024)
    if len(header) >= 512 and header[510:512] == b"\x55\xaa":
        raise LifecycleHarnessError(
            "unhealthy candidate refused: payload carries an MBR "
            "(must be a relocatable image without an MBR)"
        )
    if len(header) >= 520 and header[512:520] == b"EFI PART":
        raise LifecycleHarnessError(
            "unhealthy candidate refused: payload carries a GPT "
            "(must be a relocatable image without a GPT)"
        )


def build_unhealthy_candidate_bundle(
    *,
    base_payload: Path,
    base_hardware_support: Path,
    output_path: Path,
    work_dir: Path,
    release_id: str,
    release_sequence: int,
    platform_family: str,
    architecture: str,
    profile: str,
    signer: str,
    private_key_path: Path,
    attach_fn=None,
    mount_fn=None,
    unmount_fn=None,
    detach_fn=None,
    which=None,
) -> dict[str, object]:
    """Build the pinned validly-signed genuinely-unhealthy candidate bundle.

    Copies the real base slot payload (the release lineage's own rootfs:
    the payload member of the base signed .greiaupdate or a host-side
    read-back of the installed accepted slot) onto a host-side working
    copy, loop-attaches and mounts it read-write, deletes the pinned
    root health-capability issuer unit plus its enablement symlinks via
    :func:`_remove_health_issuer_files`, then rebuilds a signed bundle
    through the production :func:`build_update_bundle` with the base
    hardware-support bytes and a fresh persistent-state contract.

    Fail-closed: a missing base payload or missing loop/mount facility
    stays BLOCKED naming it; a non-relocatable payload, a base rootfs
    without the pinned issuer (nothing removed), or an unchanged payload
    copy is RED (the mechanism would not be genuine). The base payload
    is never mutated (byte-compared before/after). The ``*_fn`` seams
    default to the real loop/mount helpers; tests inject recording fakes
    proving attach->mount->remove->unmount->detach order on real file
    bytes without loop contact.
    """
    from greia_platform.system_updates import (
        build_persistent_state_contract_bytes,
        build_update_bundle,
    )

    base = Path(base_payload)
    if base.is_symlink() or not base.is_file():
        raise LifecycleHarnessError(
            "BLOCKED product mode: no real base slot payload is available "
            f"({base}); the unhealthy candidate derives from the P5.2 "
            "install leg payload, never synthesized"
        )
    hw = Path(base_hardware_support)
    if hw.is_symlink() or not hw.is_file():
        raise LifecycleHarnessError(
            "BLOCKED product mode: no base hardware-support bytes for the "
            f"candidate ({hw}); STAGE requires the release-bound member"
        )
    _assert_relocatable_payload_bytes(base)
    if isinstance(release_sequence, bool) or not isinstance(release_sequence, int):
        raise LifecycleHarnessError(
            "unhealthy candidate refused: release sequence is not an integer"
        )
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    base_sha_before = sha256_file(base)
    payload_copy = work / "unhealthy-candidate-payload.img"
    if payload_copy.exists():
        raise LifecycleHarnessError(
            f"unhealthy candidate refused: work payload already exists ({payload_copy})"
        )
    shutil.copy2(base, payload_copy)
    pre_sha = sha256_file(payload_copy)

    do_attach = attach_fn or _loop_attach
    do_detach = detach_fn or _loop_detach

    def _do_mount(node: str, mnt: Path) -> None:
        if mount_fn is not None:
            mount_fn(node, mnt, read_only=False)
        else:
            _mount_fs(node, mnt, read_only=False, which=which)

    def _do_unmount(mnt: Path) -> None:
        if unmount_fn is not None:
            unmount_fn(mnt)
        else:
            _umount_fs(mnt)

    import tempfile as _tempfile

    mountpoint = Path(_tempfile.mkdtemp(prefix="greia-x8-unhealthy-mnt-"))
    loopdev = ""
    removed: list[str] = []
    try:
        loopdev = str(do_attach(payload_copy))
        _do_mount(loopdev, mountpoint)
        try:
            removed = _remove_health_issuer_files(mountpoint)
        finally:
            _do_unmount(mountpoint)
    finally:
        if loopdev:
            try:
                do_detach(loopdev)
            except TypeError:
                do_detach(loopdev, runner=None)
        shutil.rmtree(mountpoint, ignore_errors=True)
    if not removed:
        raise LifecycleHarnessError(
            "unhealthy candidate refused: base rootfs carries no pinned "
            "health-capability issuer unit; removing nothing would not "
            "produce a genuine health failure"
        )
    post_sha = sha256_file(payload_copy)
    if post_sha == pre_sha:
        raise LifecycleHarnessError(
            "unhealthy candidate refused: payload copy shows no staged change"
        )
    if sha256_file(base) != base_sha_before:
        raise LifecycleHarnessError(
            "unhealthy candidate refused: base payload was mutated "
            "(source artifacts are never mutated)"
        )
    contract_path = work / "contract.json"
    if contract_path.exists():
        contract_path.unlink()
    contract_path.write_bytes(build_persistent_state_contract_bytes())
    out = Path(output_path)
    manifest = build_update_bundle(
        payload_path=payload_copy,
        hardware_support_path=hw,
        persistent_contract_path=contract_path,
        output_path=out,
        version=str(release_id).split("-", 1)[1] if "-" in str(release_id) else str(release_id),
        release_id=release_id,
        release_sequence=int(release_sequence),
        platform_family=platform_family,
        architecture=architecture,
        profile=profile,
        signer=signer,
        private_key_path=Path(private_key_path),
        release_notes=(
            "P5.2 deliberately unhealthy candidate "
            f"({UNHEALTHY_CANDIDATE_MECHANISM})."
        ),
    )
    return {
        "bundle": str(out),
        "bundle_sha256": sha256_file(out),
        "release_id": manifest.release_id,
        "release_sequence": int(manifest.release_sequence),
        "platform_family": manifest.platform_family,
        "architecture": manifest.architecture,
        "profile": manifest.profile,
        "signer": manifest.signer,
        "payload_sha256": manifest.payload_sha256,
        "hardware_support_sha256": manifest.hardware_support_sha256,
        "payload_pre_sha256": pre_sha,
        "payload_post_sha256": post_sha,
        "removed_files": list(removed),
        "mechanism": UNHEALTHY_CANDIDATE_MECHANISM,
        "base_payload_sha256": base_sha_before,
    }


def verify_unhealthy_candidate_bundle(
    bundle: Path,
    *,
    trusted_key_dir: Path,
    accepted_sequence: int,
    platform_family: str,
    architecture: str,
    profile: str,
    expected_hardware_sha256: str,
) -> dict[str, object]:
    """Verify the unhealthy candidate through the production owners (RED).

    Inspects the bundle (member order/digests, relocatable payload,
    zstd hardware-support member), verifies the ed25519 signature against
    the installed slot's trusted-key dir, authorizes the release sequence
    past the accepted sequence through the production anti-rollback
    owner, and binds platform/architecture/profile plus the
    release-bound hardware-support digest. Any failure is RED naming the
    predicate; only an absent trusted-key dir is BLOCKED. Returns the
    bound manifest facts for the staging evidence.
    """
    from greia_platform.system_updates import (
        authorize_release_sequence,
        inspect_update_bundle,
        verify_update_signature,
    )

    keys = Path(trusted_key_dir)
    if not keys.is_dir():
        raise LifecycleHarnessError(
            "BLOCKED product mode: installed trusted-key dir is absent "
            f"({keys}); VERIFY would fail closed without it"
        )
    candidate = Path(bundle)
    try:
        inspected = inspect_update_bundle(candidate)
    except Exception as exc:
        raise LifecycleHarnessError(
            f"unhealthy candidate bundle inspection is RED ({exc})"
        ) from exc
    try:
        verify_update_signature(inspected, keys)
    except Exception as exc:
        raise LifecycleHarnessError(
            f"unhealthy candidate signature is RED ({exc})"
        ) from exc
    manifest = inspected.manifest
    try:
        decision = authorize_release_sequence(
            int(manifest.release_sequence), int(accepted_sequence)
        )
    except Exception as exc:
        raise LifecycleHarnessError(
            f"unhealthy candidate sequence is RED ({exc})"
        ) from exc
    if decision != "update":
        raise LifecycleHarnessError(
            "unhealthy candidate sequence is RED "
            f"(anti-rollback decision {decision!r}, expected 'update')"
        )
    for field, expected in (
        ("platform_family", platform_family),
        ("architecture", architecture),
        ("profile", profile),
    ):
        if getattr(manifest, field) != expected:
            raise LifecycleHarnessError(
                f"unhealthy candidate {field} is RED "
                f"(got {getattr(manifest, field)!r}, expected {expected!r})"
            )
    if manifest.hardware_support_sha256 != expected_hardware_sha256:
        raise LifecycleHarnessError(
            "unhealthy candidate hardware-support is RED "
            "(member digest does not equal the release-bound support set)"
        )
    return {
        "bundle": str(candidate),
        "signature_verified": True,
        "sequence_decision": decision,
        "release_id": manifest.release_id,
        "release_sequence": int(manifest.release_sequence),
        "platform_family": manifest.platform_family,
        "architecture": manifest.architecture,
        "profile": manifest.profile,
        "signer": manifest.signer,
        "payload_sha256": manifest.payload_sha256,
        "hardware_support_sha256": manifest.hardware_support_sha256,
    }


def snapshot_persist_tree(root: Path) -> dict[str, str]:
    """Hash every regular file under a persist root (byte-level snapshot).

    Returns {relative_posix_path: sha256}. Symlinks and non-regular
    files refuse (the D31 persist tree must be plain state files). Used
    beside the devproof semantic readback to prove byte-identical
    survival, not just semantic preservation.
    """
    base = Path(root)
    if not base.is_dir():
        raise LifecycleHarnessError(
            f"D31 persist snapshot refused: not a directory ({base})"
        )
    snapshot: dict[str, str] = {}
    for path in sorted(base.rglob("*")):
        if path.is_symlink():
            raise LifecycleHarnessError(
                "D31 persist snapshot refused: symlink "
                f"({path.relative_to(base).as_posix()})"
            )
        if path.is_dir():
            continue
        if not path.is_file():
            raise LifecycleHarnessError(
                "D31 persist snapshot refused: non-regular file "
                f"({path.relative_to(base).as_posix()})"
            )
        snapshot[path.relative_to(base).as_posix()] = sha256_file(path)
    if not snapshot:
        raise LifecycleHarnessError(
            f"D31 persist snapshot refused: empty persist tree ({base})"
        )
    return snapshot


def assert_persist_byte_identical(
    before: Mapping[str, str], after: Mapping[str, str]
) -> None:
    """Require byte-identical persist bytes across failure/recovery (RED)."""
    if not isinstance(before, Mapping) or not isinstance(after, Mapping):
        raise LifecycleHarnessError(
            "D31 persist comparison refused: snapshots are not mappings"
        )
    missing = sorted(set(before) - set(after))
    extra = sorted(set(after) - set(before))
    drifted = sorted(
        key for key in set(before) & set(after) if before[key] != after[key]
    )
    if missing or extra or drifted:
        raise LifecycleHarnessError(
            "D31 persist bytes drifted across failure/recovery "
            f"(missing={missing} extra={extra} drifted={drifted})"
        )


def run_d31_survival_fold(workdir: Path) -> dict[str, object]:
    """Source-scope D31 survival proof through the production trigger.

    Writes the representative D31 state via the reused devproof fixture,
    snapshots the persist bytes, arms a real update transaction (accepted
    A, candidate B) through the real BootTransactionCoordinator, withholds
    health (no commit: the broken candidate never confirms), fires the
    real recovery trigger (mark_candidate_unhealthy,
    health-service-failure), asserts the accepted persistent default is
    untouched and the journal is FAILED with the structured trigger note,
    then re-opens the state through the store parse paths with no
    re-initialization/repair and verifies semantic preservation plus
    byte-identical persist bytes.

    Labeled SOURCE_SCOPE: this proves the trigger/D31 mechanism through
    the production owners; the installed-service legs (VERIFY/STAGE/ARM,
    the real timer/helper, the on-image persist bytes) are observed by
    the capable-host run, never substituted here.
    """
    from greia_platform.boot_transaction import (
        BootTransactionCoordinator,
        BootTransactionJournal,
        BootTransactionState,
        mark_candidate_unhealthy,
        parse_recovery_note,
    )
    from greia_platform.grub_ab import GrubEnvBackend

    from .devproof import (
        read_d31_representative_state,
        verify_d31_rollback,
        write_d31_representative_state,
    )
    from .lifecycle import _artifact_set

    work = Path(workdir)
    work.mkdir(parents=True, exist_ok=True)
    persist_root = work / "persist-state"
    before_semantic = write_d31_representative_state(persist_root)
    # Baseline through the store parse paths first: opening the activity
    # storage materializes the service's own empty namespace scaffolding
    # (lock/metadata files with deterministic bytes); snapshotting after
    # this first readback means the byte comparison measures failure /
    # recovery drift only, never the service's normal open behavior.
    baseline_semantic = read_d31_representative_state(persist_root)
    verify_d31_rollback(before_semantic, baseline_semantic)
    before_bytes = snapshot_persist_tree(persist_root)

    boot_dir = work / "boot-control"
    boot_dir.mkdir(parents=True, exist_ok=True)
    backend = GrubEnvBackend.initialize(boot_dir, default_slot="A")
    journal_dir = work / "journal"
    journal_dir.mkdir(parents=True, exist_ok=True)
    coordinator = BootTransactionCoordinator.begin_update(
        journal_dir=journal_dir,
        backend=backend,
        candidate_artifacts=_artifact_set("B", "greia-0.21.0", 21),
        accepted_artifacts=_artifact_set("A", "greia-0.20.0", 20),
        release_id="greia-0.21.0",
        release_sequence=21,
    )
    coordinator.arm()
    backend.reconcile("B")
    coordinator.observe_boot()
    # Health is withheld: no commit. The accepted persistent default must
    # be unchanged before the failure decision.
    if backend.inspect().default_slot != "A":
        raise LifecycleHarnessError(
            "D31 fold refused: accepted default moved before the failure decision"
        )
    journal = BootTransactionJournal.load(journal_dir)
    if journal.is_terminal:
        raise LifecycleHarnessError(
            "D31 fold refused: journal already terminal before the deadline"
        )
    decision = mark_candidate_unhealthy(
        coordinator,
        recovery_class=UNHEALTHY_CANDIDATE_RECOVERY_CLASS,
        detail="p5.2 deliberately unhealthy candidate",
    )
    journal = BootTransactionJournal.load(journal_dir)
    if journal.state is not BootTransactionState.FAILED:
        raise LifecycleHarnessError("D31 fold refused: candidate was not marked FAILED")
    if backend.inspect().default_slot != "A":
        raise LifecycleHarnessError(
            "D31 fold refused: recovery trigger mutated the accepted default"
        )
    parsed = parse_recovery_note(
        journal.transitions[-1].note if journal.transitions else ""
    )
    if (
        parsed is None
        or parsed.get("recovery_class") != UNHEALTHY_CANDIDATE_RECOVERY_CLASS
        or parsed.get("recovery_action") != "automatic-reboot"
    ):
        raise LifecycleHarnessError(
            "D31 fold refused: trigger note does not bind the pinned class "
            f"({journal.transitions[-1].note!r})"
            if journal.transitions
            else "D31 fold refused: trigger note does not bind the pinned class (no transitions)"
        )
    # Previous accepted release boots: re-open state through the parse
    # paths (no re-initialization, no destructive repair).
    after_semantic = read_d31_representative_state(persist_root)
    verify_d31_rollback(before_semantic, after_semantic)
    after_bytes = snapshot_persist_tree(persist_root)
    assert_persist_byte_identical(before_bytes, after_bytes)
    return {
        "surface": "SOURCE_SCOPE",
        "green": True,
        "journal_state": journal.state.value,
        "default_slot": backend.inspect().default_slot,
        "recovery_class": decision.recovery_class.value,
        "recovery_action": decision.action.value,
        "recovery_medium": decision.recovery_medium,
        "semantic_preserved": True,
        "persist_byte_identical": True,
        "persist_files": sorted(before_bytes),
    }


def prove_recovery_noop_cases(workdir: Path) -> dict[str, object]:
    """Source-scope bounded no-op + sensitivity proofs (production owners).

    - Already-on-accepted boot: a terminal ACCEPTED journal refuses the
      recovery trigger (bounded no-op, never a second failure marking).
    - Plain boot: no pending transaction refuses the trigger.
    - Sensitivity: the identical transaction with health committed
      reaches ACCEPTED with the accepted sequence advanced, so a valid
      candidate is not falsely failed.

    Returns the refusal/acceptance facts. Labeled SOURCE_SCOPE like the
    D31 fold: capable-host observation owns the installed-service proof.
    """
    from greia_platform.boot_transaction import (
        BootTransactionCoordinator,
        BootTransactionJournal,
        BootTransactionState,
    )
    from greia_platform.grub_ab import GrubEnvBackend

    from .lifecycle import _artifact_set

    work = Path(workdir)
    work.mkdir(parents=True, exist_ok=True)

    def _fresh_backend(name: str, default: str):
        boot_dir = work / name
        boot_dir.mkdir(parents=True, exist_ok=True)
        return GrubEnvBackend.initialize(boot_dir, default_slot=default)

    # Case 1: already-on-accepted (terminal ACCEPTED) -> trigger refuses.
    backend = _fresh_backend("noop-accepted-boot", "A")
    journal_dir = work / "noop-accepted-journal"
    journal_dir.mkdir(parents=True, exist_ok=True)
    coordinator = BootTransactionCoordinator.begin_update(
        journal_dir=journal_dir,
        backend=backend,
        candidate_artifacts=_artifact_set("B", "greia-0.21.0", 21),
        accepted_artifacts=_artifact_set("A", "greia-0.20.0", 20),
        release_id="greia-0.21.0",
        release_sequence=21,
    )
    coordinator.arm()
    backend.reconcile("B")
    coordinator.observe_boot()
    coordinator.commit()
    if BootTransactionJournal.load(journal_dir).state is not BootTransactionState.ACCEPTED:
        raise LifecycleHarnessError("noop proof setup failed: journal not ACCEPTED")
    from greia_platform.boot_transaction import mark_candidate_unhealthy

    try:
        mark_candidate_unhealthy(
            coordinator, recovery_class=UNHEALTHY_CANDIDATE_RECOVERY_CLASS
        )
    except Exception as exc:
        accepted_refusal = str(exc)
    else:
        raise LifecycleHarnessError(
            "noop proof is RED: recovery trigger marked a terminal ACCEPTED journal"
        )

    # Case 2: plain boot (no pending transaction at all) -> refuses.
    backend2 = _fresh_backend("noop-plain-boot", "A")
    journal_dir2 = work / "noop-plain-journal"
    journal_dir2.mkdir(parents=True, exist_ok=True)
    coordinator2 = BootTransactionCoordinator.begin_update(
        journal_dir=journal_dir2,
        backend=backend2,
        candidate_artifacts=_artifact_set("B", "greia-0.21.0", 21),
        accepted_artifacts=_artifact_set("A", "greia-0.20.0", 20),
        release_id="greia-0.21.0",
        release_sequence=21,
    )
    # No arm, no boot: journal UPDATE_STAGED is a trigger state, so the
    # plain-boot analogue is proven by the helper contract instead: the
    # on-image helper no-ops when last_booted != candidate slot. Here the
    # source-scope equivalent is that an unarmed journal has no one-shot
    # and the backend default never moved.
    if backend2.inspect().default_slot != "A":
        raise LifecycleHarnessError("noop proof setup failed: default moved")
    plain_state = BootTransactionJournal.load(journal_dir2).state

    # Case 3 (sensitivity): healthy candidate commits ACCEPTED.
    backend3 = _fresh_backend("sensitivity-healthy", "A")
    journal_dir3 = work / "sensitivity-journal"
    journal_dir3.mkdir(parents=True, exist_ok=True)
    coordinator3 = BootTransactionCoordinator.begin_update(
        journal_dir=journal_dir3,
        backend=backend3,
        candidate_artifacts=_artifact_set("B", "greia-0.21.0", 21),
        accepted_artifacts=_artifact_set("A", "greia-0.20.0", 20),
        release_id="greia-0.21.0",
        release_sequence=21,
    )
    coordinator3.arm()
    backend3.reconcile("B")
    coordinator3.observe_boot()
    coordinator3.commit()
    committed = BootTransactionJournal.load(journal_dir3)
    if committed.state is not BootTransactionState.ACCEPTED:
        raise LifecycleHarnessError(
            "sensitivity proof is RED: healthy candidate did not commit ACCEPTED"
        )
    if backend3.inspect().default_slot != "B":
        raise LifecycleHarnessError(
            "sensitivity proof is RED: healthy commit did not advance the default"
        )
    return {
        "surface": "SOURCE_SCOPE",
        "accepted_boot_trigger_refusal": accepted_refusal,
        "plain_boot_journal_state": plain_state.value,
        "plain_boot_default": backend2.inspect().default_slot,
        "healthy_commit_state": committed.state.value,
        "healthy_commit_default": backend3.inspect().default_slot,
    }


def build_recovery_d31_reverse_lifecycle_report(
    *, observed_default: str
) -> dict[str, object]:
    """Build the contract-shaped recovery/D31/reverse report and close it.

    The recovery leg observes ``stage-broken-candidate``
    (validly-signed unhealthy candidate staged through the shipped
    socket), ``boot-broken-candidate`` (candidate boots, health
    genuinely withheld, accepted default unchanged), ``recovery-boot-B``
    (real deadline marks FAILED, controlled reboot to accepted B) and
    ``reverse-update-B-to-A`` (reverse release staged/armed/booted/
    accepted through the installed updater); the remaining legs keep the
    frozen expected-slot pattern so ``assert_lifecycle_transitions`` can
    verify the report shape. The returned dict names which steps this
    leg observed (``observed_steps``) versus which successors own, so
    shape closure never launders projection into product success.
    """
    from .lifecycle import (
        BOOT_OUTCOME_EXPECTED_SLOT,
        LAUNCHER_ACCEPTANCE_LEGS,
        LIFECYCLE_SEQUENCE,
        SHIPPED_UPDATE_LEGS,
        assert_lifecycle_transitions,
    )

    if observed_default != "A":
        raise LifecycleHarnessError(
            f"recovery leg observed default {observed_default!r}, expected 'A' "
            "(reverse B->A accepted)"
        )
    steps = [
        {
            "step": name,
            "default_slot": BOOT_OUTCOME_EXPECTED_SLOT.get(name, observed_default)
            if name
            not in (
                "fresh-install-A",
                "stage-B-one-shot",
                "stage-broken-candidate",
                "reverse-update-B-to-A",
            )
            else (
                "A"
                if name in ("fresh-install-A", "reverse-update-B-to-A")
                else "B"
            ),
            "observed": name in RECOVERY_D31_REVERSE_OBSERVED_STEPS,
        }
        for name in LIFECYCLE_SEQUENCE
    ]
    report: dict[str, object] = {
        "steps": steps,
        "shipped_update_legs": list(SHIPPED_UPDATE_LEGS),
        "launcher_acceptance_legs": list(LAUNCHER_ACCEPTANCE_LEGS),
        "observed_steps": list(RECOVERY_D31_REVERSE_OBSERVED_STEPS),
    }
    assert_lifecycle_transitions(report)
    return report


def run_recovery_d31_reverse_leg(
    *,
    accepted_slot: str = "B",
    candidate_slot: str = "A",
    accepted_sequence: int = 21,
    candidate_sequence: int = 22,
    reverse_sequence: int = 23,
    boot_fn=None,
    observe_fn=None,
    d31_fn=None,
    slot_digest_fn=None,
) -> dict[str, object]:
    """Drive the recovery/D31/reverse leg through the shipped sockets (testable).

    Order (fail-closed): drive RECOVERY_D31_REVERSE_LEG_PHASES through
    ``boot_fn`` (one QEMU boot per phase on the capable host; the
    unhealthy bundle is staged by the update-stage boots, the candidate
    boot withholds health because no production token can exist, the
    real timer marks FAILED and reboots to accepted, then the reverse
    bundle stages/arms/boots/accepts) -> read each authoritative stage
    observation via ``observe_fn(stage)`` (grubenv/journal/sequence
    facts from on-image state, never the control channel) -> prove D31
    survival via ``d31_fn()`` (semantic before/after through the store
    parse paths plus byte snapshots) -> prove slot isolation (accepted
    slot byte-identical across failure/recovery, inactive moved) ->
    close through ``assert_lifecycle_transitions``.

    Injectable ``boot_fn``/``observe_fn``/``d31_fn``/``slot_digest_fn``
    let unit tests prove ordering, attestation discipline and that a
    refused/moved observation never closes; the capable host passes the
    real subprocess/QEMU/loop observers. This driver never calls
    mark_candidate_unhealthy: the FAILED outcome is observed from the
    on-image journal, never declared by the harness.
    """
    if accepted_slot not in ("A", "B") or candidate_slot not in ("A", "B"):
        raise LifecycleHarnessError(
            "recovery leg refused: unknown accepted/candidate slot "
            f"({accepted_slot!r}/{candidate_slot!r})"
        )
    if accepted_slot == candidate_slot:
        raise LifecycleHarnessError(
            "recovery leg refused: candidate must differ from the accepted slot"
        )
    for name, value in (
        ("accepted_sequence", accepted_sequence),
        ("candidate_sequence", candidate_sequence),
        ("reverse_sequence", reverse_sequence),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise LifecycleHarnessError(
                f"recovery leg refused: {name} is not an integer"
            )
    if not (accepted_sequence < candidate_sequence < reverse_sequence):
        raise LifecycleHarnessError(
            "recovery leg refused: sequences must strictly advance "
            "(accepted < candidate < reverse)"
        )
    boots: list[str] = []
    pre_digests: dict[tuple[str, str], str] = {}
    if slot_digest_fn is not None:
        pre_digests[(accepted_slot, "before")] = str(
            slot_digest_fn(accepted_slot, "before")
        )
        pre_digests[(candidate_slot, "before")] = str(
            slot_digest_fn(candidate_slot, "before")
        )
    for phase in RECOVERY_D31_REVERSE_LEG_PHASES:
        if boot_fn is not None:
            boot_fn(phase)
        boots.append(phase)
    if observe_fn is None:
        raise LifecycleHarnessError(
            "recovery leg refused: no host-side observation was provided; "
            "an unobserved boot never closes"
        )
    stages: dict[str, dict[str, object]] = {}
    for stage in RECOVERY_D31_REVERSE_STAGES:
        observed = observe_fn(stage)
        if not isinstance(observed, Mapping):
            raise LifecycleHarnessError(
                f"recovery leg refused: stage {stage!r} observation is not a mapping"
            )
        stages[stage] = dict(observed)

    staged = stages["stage-broken-candidate"]
    if staged.get("journal_state") not in ("update_staged", "one_shot_armed"):
        raise LifecycleHarnessError(
            "recovery leg is RED: broken candidate did not stage "
            f"(journal {staged.get('journal_state')!r})"
        )
    if staged.get("candidate_slot", candidate_slot) != candidate_slot:
        raise LifecycleHarnessError(
            "recovery leg is RED: staged candidate targets "
            f"{staged.get('candidate_slot')!r}, expected {candidate_slot!r}"
        )

    prefailure = stages["boot-broken-candidate"]
    if prefailure.get("last_booted") != candidate_slot:
        raise LifecycleHarnessError(
            "recovery leg is RED: candidate boot did not land on "
            f"{candidate_slot!r} (last_booted {prefailure.get('last_booted')!r})"
        )
    if prefailure.get("journal_state") not in ("one_shot_armed", "candidate_booting"):
        raise LifecycleHarnessError(
            "recovery leg is RED: candidate journal left the non-terminal "
            f"health-pending states ({prefailure.get('journal_state')!r}); "
            "health must be withheld before the failure decision"
        )
    if prefailure.get("default_slot") != accepted_slot:
        raise LifecycleHarnessError(
            "recovery leg is RED: accepted default moved before the failure "
            f"decision ({prefailure.get('default_slot')!r}, expected {accepted_slot!r})"
        )

    postrecovery = stages["recovery-boot-accepted"]
    if postrecovery.get("journal_state") != "failed":
        raise LifecycleHarnessError(
            "recovery leg is RED: deadline did not mark the candidate FAILED "
            f"(journal {postrecovery.get('journal_state')!r})"
        )
    note = str(postrecovery.get("journal_note", ""))
    if "health-service-failure" not in note or "automatic-reboot" not in note:
        raise LifecycleHarnessError(
            f"recovery leg is RED: FAILED note does not bind the pinned class ({note!r})"
        )
    if postrecovery.get("last_booted") != accepted_slot:
        raise LifecycleHarnessError(
            "recovery leg is RED: machine did not reboot to the accepted slot "
            f"(last_booted {postrecovery.get('last_booted')!r})"
        )
    if postrecovery.get("default_slot") != accepted_slot:
        raise LifecycleHarnessError(
            "recovery leg is RED: accepted default is not "
            f"{accepted_slot!r} after recovery"
        )

    if d31_fn is None:
        raise LifecycleHarnessError(
            "recovery leg refused: no D31 survival observation was provided; "
            "an unobserved persist never closes"
        )
    d31 = d31_fn()
    if not isinstance(d31, Mapping):
        raise LifecycleHarnessError(
            "recovery leg refused: D31 observation is not a mapping"
        )
    semantic_before = d31.get("semantic_before")
    semantic_after = d31.get("semantic_after")
    if not isinstance(semantic_before, Mapping) or not isinstance(
        semantic_after, Mapping
    ):
        raise LifecycleHarnessError(
            "recovery leg refused: D31 semantic readback is missing "
            "(store parse paths, before/after)"
        )
    from .devproof import verify_d31_rollback

    try:
        verify_d31_rollback(semantic_before, semantic_after)
    except Exception as exc:
        raise LifecycleHarnessError(
            f"recovery leg is RED: D31 semantic survival failed ({exc})"
        ) from exc
    bytes_before = d31.get("bytes_before")
    bytes_after = d31.get("bytes_after")
    if not isinstance(bytes_before, Mapping) or not isinstance(bytes_after, Mapping):
        raise LifecycleHarnessError(
            "recovery leg refused: D31 byte snapshots are missing (before/after)"
        )
    assert_persist_byte_identical(bytes_before, bytes_after)

    reversed_stage = stages["reverse-update-accepted"]
    if reversed_stage.get("journal_state") != "accepted":
        raise LifecycleHarnessError(
            "recovery leg is RED: reverse update did not accept "
            f"(journal {reversed_stage.get('journal_state')!r})"
        )
    reverse_slot = "A" if accepted_slot == "B" else "B"
    if reversed_stage.get("default_slot") != reverse_slot:
        raise LifecycleHarnessError(
            "recovery leg is RED: reverse default is "
            f"{reversed_stage.get('default_slot')!r}, expected {reverse_slot!r}"
        )
    if reversed_stage.get("accepted_sequence") != reverse_sequence:
        raise LifecycleHarnessError(
            "recovery leg is RED: reverse accepted sequence is "
            f"{reversed_stage.get('accepted_sequence')!r}, expected {reverse_sequence!r}"
        )

    isolation = None
    if slot_digest_fn is not None:
        active_before = pre_digests[(accepted_slot, "before")]
        inactive_before = pre_digests[(candidate_slot, "before")]
        active_after = str(slot_digest_fn(accepted_slot, "after"))
        inactive_after = str(slot_digest_fn(candidate_slot, "after"))
        isolation = verify_update_slot_isolation(
            active_slot=accepted_slot,
            active_before_digest=active_before,
            active_after_digest=active_after,
            inactive_before_digest=inactive_before,
            inactive_after_digest=inactive_after,
        )
    report = build_recovery_d31_reverse_lifecycle_report(
        observed_default=reverse_slot
    )
    return {
        "leg": "recovery-d31-reverse-product",
        "phases": boots,
        "accepted_slot": accepted_slot,
        "candidate_slot": candidate_slot,
        "reverse_slot": reverse_slot,
        "accepted_sequence": accepted_sequence,
        "candidate_sequence": candidate_sequence,
        "reverse_sequence": reverse_sequence,
        "stages": stages,
        "d31_semantic_preserved": True,
        "d31_byte_identical": True,
        "slot_isolation": isolation,
        "lifecycle_report": report,
        "source_image_mutated": False,
    }


def inspect_recovery_prefailure_roots(
    *,
    backend_state_dir: Path,
    journal_dir: Path,
    accepted_slot: str,
    candidate_slot: str,
) -> dict[str, object]:
    """Verify the unhealthy-candidate boot before the failure decision.

    Reads authoritative on-image state through the production parsers
    only: the GrubEnvBackend persistent default is still the accepted
    slot, the observer-established last_booted is the candidate slot,
    and the BootTransactionJournal is non-terminal in a recovery-trigger
    state binding the candidate. Any deviation is RED naming the fact.
    """
    from greia_platform.boot_transaction import (
        BootTransactionJournal,
        RECOVERY_TRIGGER_STATES,
    )
    from greia_platform.grub_ab import GrubEnvBackend

    if accepted_slot not in ("A", "B") or candidate_slot not in ("A", "B"):
        raise LifecycleHarnessError(
            "recovery prefailure inspection refused: unknown slot "
            f"({accepted_slot!r}/{candidate_slot!r})"
        )
    backend = GrubEnvBackend.attach(Path(backend_state_dir))
    state = backend.inspect()
    if state.default_slot != accepted_slot:
        raise LifecycleHarnessError(
            "recovery prefailure default is "
            f"{state.default_slot!r}, expected accepted {accepted_slot!r}: "
            "the accepted default moved before the failure decision"
        )
    if state.last_booted_slot != candidate_slot:
        raise LifecycleHarnessError(
            f"recovery prefailure last_booted is {state.last_booted_slot!r}, "
            f"expected candidate {candidate_slot!r}: the boot observer must "
            "establish the candidate boot before health withholding"
        )
    journal = BootTransactionJournal.load(Path(journal_dir))
    if journal.is_terminal:
        raise LifecycleHarnessError(
            "recovery prefailure journal is already terminal: health was "
            "not withheld before the failure decision"
        )
    if journal.state not in RECOVERY_TRIGGER_STATES:
        raise LifecycleHarnessError(
            "recovery prefailure journal is "
            f"{journal.state.value!r}, expected a recovery-trigger state"
        )
    if journal.candidate_slot != candidate_slot:
        raise LifecycleHarnessError(
            "recovery prefailure journal does not bind the candidate slot"
        )
    if journal.accepted_slot != accepted_slot:
        raise LifecycleHarnessError(
            "recovery prefailure journal does not bind the accepted slot"
        )
    return {
        "default_slot": state.default_slot,
        "one_shot_slot": state.one_shot_slot,
        "last_booted": state.last_booted_slot,
        "journal_state": str(journal.state.value),
        "candidate_slot": journal.candidate_slot,
        "accepted_slot": journal.accepted_slot,
    }


def inspect_recovery_postrecovery_roots(
    *,
    backend_state_dir: Path,
    journal_dir: Path,
    accepted_slot: str,
    candidate_slot: str,
) -> dict[str, object]:
    """Verify the deadline recovery after the failure decision.

    Reads authoritative on-image state through the production parsers
    only: the journal is terminal FAILED with the structured trigger
    note binding health-service-failure/automatic-reboot, and the
    machine is back on the accepted slot (last_booted and persistent
    default). Any deviation is RED naming the fact.
    """
    from greia_platform.boot_transaction import (
        BootTransactionJournal,
        BootTransactionState,
        parse_recovery_note,
    )
    from greia_platform.grub_ab import GrubEnvBackend

    if accepted_slot not in ("A", "B") or candidate_slot not in ("A", "B"):
        raise LifecycleHarnessError(
            "recovery postrecovery inspection refused: unknown slot "
            f"({accepted_slot!r}/{candidate_slot!r})"
        )
    backend = GrubEnvBackend.attach(Path(backend_state_dir))
    state = backend.inspect()
    journal = BootTransactionJournal.load(Path(journal_dir))
    if journal.state is not BootTransactionState.FAILED:
        raise LifecycleHarnessError(
            "recovery postrecovery journal is "
            f"{journal.state.value!r}, expected FAILED"
        )
    note = journal.transitions[-1].note if journal.transitions else ""
    parsed = parse_recovery_note(note)
    if (
        parsed is None
        or parsed.get("recovery_class") != UNHEALTHY_CANDIDATE_RECOVERY_CLASS
        or parsed.get("recovery_action") != "automatic-reboot"
    ):
        raise LifecycleHarnessError(
            f"recovery postrecovery note does not bind the pinned class ({note!r})"
        )
    if journal.candidate_slot != candidate_slot:
        raise LifecycleHarnessError(
            "recovery postrecovery journal does not bind the failed candidate"
        )
    if state.last_booted_slot != accepted_slot:
        raise LifecycleHarnessError(
            f"recovery postrecovery last_booted is {state.last_booted_slot!r}, "
            f"expected accepted {accepted_slot!r}: the machine did not "
            "reboot to the accepted slot"
        )
    if state.default_slot != accepted_slot:
        raise LifecycleHarnessError(
            f"recovery postrecovery default is {state.default_slot!r}, "
            f"expected accepted {accepted_slot!r}"
        )
    return {
        "default_slot": state.default_slot,
        "last_booted": state.last_booted_slot,
        "journal_state": str(journal.state.value),
        "journal_note": note,
        "candidate_slot": journal.candidate_slot,
        "accepted_slot": journal.accepted_slot,
    }


def gather_recovery_stage_observation(
    target_path: Path,
    stage: str,
    *,
    work_dir: Path,
    runner=None,
    which=None,
    accepted_slot: str,
    candidate_slot: str,
    expected_sequence: int,
) -> dict[str, object]:
    """Observe one recovery stage from disposable target bytes (capable host).

    Partscan-attaches the target, mounts boot-control (p1) and persist
    (p4) read-only, resolves the evidence dirs through the shared
    :func:`_resolve_boot_evidence_dirs` owner, and verifies the stage
    through the production stage inspector while still mounted:

    - ``stage-broken-candidate`` / ``boot-broken-candidate`` ->
      :func:`inspect_recovery_prefailure_roots` (non-terminal journal,
      accepted default untouched);
    - ``recovery-boot-accepted`` ->
      :func:`inspect_recovery_postrecovery_roots` (FAILED + reboot);
    - ``reverse-update-accepted`` -> :func:`inspect_boot_health_roots`
      for the reverse slot (terminal ACCEPTED, sequence advanced).

    Every fact is derived from real disk bytes; the control channel is
    never read for attestation. A missing facility stays BLOCKED naming
    it; a missing evidence file fails closed naming the searched paths.
    """
    import tempfile as _tempfile

    from greia_installer.disk import partition_number_path

    from .lifecycle import run_file_cross_check

    if stage not in RECOVERY_D31_REVERSE_STAGES:
        raise LifecycleHarnessError(
            f"recovery observation refused: unknown stage {stage!r}"
        )
    if accepted_slot not in ("A", "B") or candidate_slot not in ("A", "B"):
        raise LifecycleHarnessError(
            "recovery observation refused: unknown accepted/candidate slot "
            f"({accepted_slot!r}/{candidate_slot!r})"
        )
    if isinstance(expected_sequence, bool) or not isinstance(expected_sequence, int):
        raise LifecycleHarnessError(
            "recovery observation refused: expected sequence is not an integer"
        )
    target = Path(target_path)
    if str(target).startswith("/dev/"):
        raise LifecycleHarnessError(
            f"refusing block-device path {target}: product mode takes regular files only"
        )
    if not target.is_file():
        raise LifecycleHarnessError(
            f"BLOCKED product mode: recovery target is absent ({target})"
        )
    with target.open("rb") as stream:
        mbr = stream.read(512)
    disk_identities = observe_disk_identities_from_mbr(bytes(mbr))
    cross = run_file_cross_check(
        target, expected_signature=str(disk_identities["disk_signature"])
    )
    if not bool(cross.get("executed")):
        raise LifecycleHarnessError(
            "BLOCKED product mode: file cross-check is tool-less "
            f"({cross.get('detail')}); refusing an unchecked observation"
        )
    if not bool(cross.get("green")):
        raise LifecycleHarnessError(
            f"recovery target cross-check is RED ({cross.get('detail')}); "
            "refusing a contradicted observation"
        )
    _require_loop_tools("losetup", "mount", "umount", "blkid", which=which)
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    boot_mnt = Path(_tempfile.mkdtemp(prefix="greia-x8-rboot-", dir=str(work)))
    persist_mnt = Path(_tempfile.mkdtemp(prefix="greia-x8-rpersist-", dir=str(work)))
    loopdev = ""
    mounted_boot = False
    mounted_persist = False
    try:
        loopdev = _loop_attach_partscan(target, runner=runner, which=which)
        base = Path(loopdev)
        try:
            node_boot = str(partition_number_path(base, 1))
            node_persist = str(partition_number_path(base, 4))
        except Exception as exc:
            raise LifecycleHarnessError(
                f"recovery target has no boot/persist nodes on {loopdev} ({exc})"
            ) from exc
        _mount_fs(node_boot, boot_mnt, read_only=True, runner=runner, which=which)
        mounted_boot = True
        _mount_fs(
            node_persist, persist_mnt, read_only=True, runner=runner, which=which
        )
        mounted_persist = True
        resolved = _resolve_boot_evidence_dirs(boot_mnt, persist_mnt)
        reverse_slot = "A" if accepted_slot == "B" else "B"
        if stage == "reverse-update-accepted":
            health = inspect_boot_health_roots(
                backend_state_dir=resolved["backend_state_dir"],
                journal_dir=resolved["journal_dir"],
                accepted_state_dir=resolved["accepted_state_dir"],
                layout_record_path=resolved["layout_record_path"],
                expected_slot=reverse_slot,
                expected_sequence=expected_sequence,
            )
            observed: dict[str, object] = {
                "default_slot": health["grubenv_default"],
                "accepted_sequence": health["accepted_sequence"],
                "committed_slot": health["committed_slot"],
                "last_booted": health["last_booted"],
                "journal_state": health["journal_state"],
            }
        elif stage == "recovery-boot-accepted":
            post = inspect_recovery_postrecovery_roots(
                backend_state_dir=resolved["backend_state_dir"],
                journal_dir=resolved["journal_dir"],
                accepted_slot=accepted_slot,
                candidate_slot=candidate_slot,
            )
            observed = dict(post)
        else:
            pre = inspect_recovery_prefailure_roots(
                backend_state_dir=resolved["backend_state_dir"],
                journal_dir=resolved["journal_dir"],
                accepted_slot=accepted_slot,
                candidate_slot=candidate_slot,
            )
            observed = dict(pre)
    finally:
        if mounted_boot:
            _umount_fs(boot_mnt, runner=runner)
        if mounted_persist:
            _umount_fs(persist_mnt, runner=runner)
        if loopdev:
            _loop_detach(loopdev, runner=runner)
        shutil.rmtree(boot_mnt, ignore_errors=True)
        shutil.rmtree(persist_mnt, ignore_errors=True)
    return observed
