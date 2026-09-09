"""T7-PAYLOAD minimal bootable-guest payload for the disposable image.

The T6-HARNESS3 disposable image carried an MBR table but no guest payload:
host-dir ``machine/boot-control`` grubenv/grub.cfg bytes never reached the
image, so no QEMU guest could consume the one-shot entry (T7-ATTEST D1).
This module owns the minimal payload that closes that gap, frozen to the
T7-ATTEST-selected design (grubenv-on-image with post-boot loop
remount/read, option b; guest-agent option rejected, narrowed-acceptance
rejected as laundering).

Payload contents (minimal only; no Activity, no D31 state, no interruption
matrix, no resource envelope):

- ``grub.cfg``: the fixed two-entry appliance config rendered from the
  trusted layout record via
  :func:`greia_platform.grub_ab.render_grub_ab_config_from_record` and
  validated via :func:`greia_platform.grub_ab.validate_grub_ab_text`.
  The config itself is the one-shot consumer: its
  ``if [ -n "${next_entry}" ]`` block boots the candidate exactly once and
  ``save_env next_entry`` clears the one-shot. No guest agent is added.
- ``grubenv``: the 1024-byte GRUB environment block staged via the
  production :class:`greia_platform.grub_ab.GrubEnvBackend` (``initialize``
  default A). Real GRUB (``grub-pc``/``grub-pc-bin`` per
  ``build/package-sets/boot-grub-pc.txt``) reads this block as
  ``saved_entry``/``next_entry`` on partition 1 (``$prefix/grubenv``).
- Success signal: the grubenv consumption record itself
  (``next_entry`` absent AND ``greia_last_booted == <expected slot>``),
  read post-boot via the production seam
  ``GrubEnvBackend.attach(mountpoint).inspect()`` after loop-attaching the
  image and mounting partition 1 read-only. ATTEST §3(5) explicitly bounds
  the minimal-boot predicate to clean exit + consumption + topology bind +
  journal fold + this signal; launcher ``INTERACTIVE_READY`` acceptance is
  NOT claimed for minimal legs. Serial/QEMU host logs corroborate that QEMU
  ran; they never prove consumption.

Image binding without privileged tools: assembly runs source-scope without
loop/mount/mkfs, so the payload staging (``grub.cfg`` + ``grubenv`` +
``manifest.json``) is written to the harness output dir and bound to the
raw image by a 512-byte descriptor sector at image sector 1 (bytes
512..1023; free space — partition 1 starts at sector 2048). The descriptor
carries a magic, version, and the SHA-256 of each staged artifact. On a
capable host :func:`install_payload_to_device` formats partition 1 and
copies the staged files onto the boot-control filesystem with safe
loop/mount teardown; off-host it fails closed via ``require_device_host``.

Fake boundary: no stubbed health/launcher, no fabricated slot/journal/GRUB
state. All GRUB bytes come from the production renderer/backend; the
descriptor only records their hashes. Reads are bounded (512-byte
descriptor, 8 MiB streaming hashes); no whole-payload RAM copy.

Sector coordination: sectors 1-2047 are reserved (sector 1 = descriptor,
sectors 2-2047 = zero). :func:`verify_sector_gap_reserved` pins this so
a future GRUB ``core.img`` gap embed cannot silently clobber the
descriptor; the full constraint lives in ``tools/x8_qemu/LIFECYCLE.md``
section 8, where the future GRUB installer must read it. No gap embed
lands in this task.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


#: Magic identifying a T7-PAYLOAD descriptor sector (8 bytes, ASCII).
PAYLOAD_MAGIC = b"GREIAPY1"

#: Descriptor format version.
PAYLOAD_VERSION = 1

#: Image byte offset of the descriptor sector (sector 1; MBR table owns 0).
DESCRIPTOR_OFFSET = 512

#: Descriptor sector length (one 512-byte sector).
DESCRIPTOR_LENGTH = 512

#: First reserved gap sector (the descriptor sector itself).
SECTOR_GAP_FIRST_SECTOR = 1

#: Last reserved gap sector. Partition 1 starts at sector 2048, so sectors
#: 1-2047 are the MBR-gap reservation owned by this task's guard.
SECTOR_GAP_LAST_SECTOR = 2047

#: First sector of partition 1 (legacy adapter layout; gap ends before it).
PARTITION_1_FIRST_SECTOR = 2048

#: Coordination constraint for the future GRUB installer. A real GRUB
#: ``core.img`` gap embed MUST NOT land in sectors 1-2047 without first
#: relocating the T7-PAYLOAD descriptor (magic ``GREIAPY1`` at sector 1)
#: through an explicit, reviewed migration: the embed must either reserve
#: a different gap region or move the descriptor and update
#: :func:`read_payload_descriptor`, :func:`embed_payload_descriptor` and
#: :func:`verify_sector_gap_reserved` together. This note is duplicated in
#: ``tools/x8_qemu/LIFECYCLE.md`` §8, which is where the future GRUB
#: installer must read it. No gap embed lands in this task.
SECTOR_GAP_COORDINATION_NOTE = (
    "Sectors 1-2047 are reserved: sector 1 carries the T7-PAYLOAD "
    "descriptor (GREIAPY1); sectors 2-2047 must stay zero. A future GRUB "
    "core.img gap embed must relocate the descriptor explicitly, never "
    "silently clobber it. See tools/x8_qemu/LIFECYCLE.md section 8."
)

#: On-image guest paths (partition 1 boot-control filesystem roots).
GUEST_GRUB_CFG_PATH = "/grub.cfg"
GUEST_GRUBENV_PATH = "/grubenv"

#: Staging file names inside the harness output ``guest-payload`` dir.
STAGED_GRUB_CFG_NAME = "grub.cfg"
STAGED_GRUBENV_NAME = "grubenv"
STAGED_MANIFEST_NAME = "manifest.json"


class PayloadError(RuntimeError):
    """Minimal-guest payload missing, corrupt, or refused fail-closed."""


@dataclass(frozen=True, slots=True)
class PayloadManifest:
    """Content binding for one composed guest payload staging."""

    grub_cfg_sha256: str
    grubenv_sha256: str
    grub_cfg_bytes: int
    grubenv_bytes: int
    guest_paths: tuple[str, str] = (GUEST_GRUB_CFG_PATH, GUEST_GRUBENV_PATH)

    def as_dict(self) -> dict[str, object]:
        return {
            "magic": PAYLOAD_MAGIC.decode("ascii"),
            "version": PAYLOAD_VERSION,
            "grub_cfg_sha256": self.grub_cfg_sha256,
            "grubenv_sha256": self.grubenv_sha256,
            "grub_cfg_bytes": self.grub_cfg_bytes,
            "grubenv_bytes": self.grubenv_bytes,
            "guest_paths": list(self.guest_paths),
        }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compose_guest_payload(
    *,
    layout_record_path: Path,
    password_hash: str,
    output_dir: Path,
) -> PayloadManifest:
    """Compose the minimal guest payload staging via the production path.

    Loads the trusted layout record, renders + validates ``grub.cfg``
    through the production GRUB seams, and stages ``grubenv`` through the
    production :class:`GrubEnvBackend` (``initialize`` default A). Writes
    ``grub.cfg``, ``grubenv`` and ``manifest.json`` into ``output_dir``.
    Nothing is hand-written: any render/validation/initialize failure
    raises fail-closed before a single payload byte is staged.
    """
    from greia_platform.grub_ab import (
        GRUBENV_FILE_NAME,
        GrubEnvBackend,
        render_grub_ab_config_from_record,
        validate_grub_ab_text,
    )
    from greia_platform.system_updates import load_installed_layout_record

    record = load_installed_layout_record(Path(layout_record_path))
    if record is None:
        raise PayloadError("layout record is missing or not authoritative")
    grub_text = render_grub_ab_config_from_record(
        record=record, password_hash=password_hash
    )
    validate_grub_ab_text(grub_text)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    grub_bytes = grub_text.encode("utf-8")
    (out / STAGED_GRUB_CFG_NAME).write_bytes(grub_bytes)

    env_stage = out / ".grubenv-stage"
    if env_stage.exists():
        shutil.rmtree(env_stage)
    env_stage.mkdir(parents=True, exist_ok=True)
    GrubEnvBackend.initialize(env_stage, default_slot="A")
    staged_env = env_stage / GRUBENV_FILE_NAME
    if not staged_env.is_file():
        raise PayloadError("production backend staged no grubenv")
    (out / STAGED_GRUBENV_NAME).write_bytes(staged_env.read_bytes())
    shutil.rmtree(env_stage)

    manifest = PayloadManifest(
        grub_cfg_sha256=_sha256_bytes(grub_bytes),
        grubenv_sha256=_sha256_file(out / STAGED_GRUBENV_NAME),
        grub_cfg_bytes=len(grub_bytes),
        grubenv_bytes=(out / STAGED_GRUBENV_NAME).stat().st_size,
    )
    if manifest.grubenv_bytes != 1024:
        raise PayloadError("staged grubenv is not the 1024-byte GRUB block")
    (out / STAGED_MANIFEST_NAME).write_text(
        json.dumps(manifest.as_dict(), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def _descriptor_bytes(manifest: PayloadManifest) -> bytes:
    body = (
        PAYLOAD_MAGIC
        + bytes((PAYLOAD_VERSION,))
        + manifest.grub_cfg_sha256.encode("ascii")
        + manifest.grubenv_sha256.encode("ascii")
    )
    if len(body) > DESCRIPTOR_LENGTH:
        raise PayloadError("payload descriptor does not fit one sector")
    return body + b"\x00" * (DESCRIPTOR_LENGTH - len(body))


def embed_payload_descriptor(image: Path, manifest: PayloadManifest) -> None:
    """Bind staged payload hashes to the raw image at descriptor sector 1.

    Reads back the written sector and fails closed on mismatch. Refuses to
    overwrite a non-zero sector carrying a different magic (never silently
    rebind one payload over another).
    """
    image = Path(image)
    if image.stat().st_size < DESCRIPTOR_OFFSET + DESCRIPTOR_LENGTH:
        raise PayloadError("image is too small for the payload descriptor")
    verify_sector_gap_reserved(image, allow_current_descriptor=True)
    with open(image, "r+b") as handle:
        handle.seek(DESCRIPTOR_OFFSET)
        previous = handle.read(DESCRIPTOR_LENGTH)
        if any(previous) and not previous.startswith(PAYLOAD_MAGIC):
            raise PayloadError("descriptor sector carries foreign bytes; refusing")
        handle.seek(DESCRIPTOR_OFFSET)
        handle.write(_descriptor_bytes(manifest))
        handle.flush()
        os.fsync(handle.fileno())
    observed = read_payload_descriptor(image)
    if (
        observed["grub_cfg_sha256"] != manifest.grub_cfg_sha256
        or observed["grubenv_sha256"] != manifest.grubenv_sha256
    ):
        raise PayloadError("descriptor re-read does not match staged payload")


def read_payload_descriptor(image: Path) -> dict[str, object]:
    """Read and validate the payload descriptor (512 bounded bytes only)."""
    with open(Path(image), "rb") as handle:
        handle.seek(DESCRIPTOR_OFFSET)
        raw = handle.read(DESCRIPTOR_LENGTH)
    if len(raw) != DESCRIPTOR_LENGTH or not raw.startswith(PAYLOAD_MAGIC):
        raise PayloadError("bootable-guest payload is missing from the image")
    if raw[len(PAYLOAD_MAGIC)] != PAYLOAD_VERSION:
        raise PayloadError("bootable-guest payload descriptor version is unknown")
    try:
        grub_cfg_sha = raw[9:73].decode("ascii")
        grubenv_sha = raw[73:137].decode("ascii")
    except UnicodeDecodeError as exc:
        raise PayloadError("payload descriptor hashes are not ASCII") from exc
    for digest in (grub_cfg_sha, grubenv_sha):
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise PayloadError("payload descriptor hashes are malformed")
    return {
        "magic": PAYLOAD_MAGIC.decode("ascii"),
        "version": PAYLOAD_VERSION,
        "grub_cfg_sha256": grub_cfg_sha,
        "grubenv_sha256": grubenv_sha,
        "guest_paths": [GUEST_GRUB_CFG_PATH, GUEST_GRUBENV_PATH],
    }


def assert_payload_present(image: Path) -> dict[str, object]:
    """Boot-gate payload check: RED (raise) when the payload is missing.

    Called by the clean-exit gate path (``LifecycleHarness.run_device``)
    before any QEMU boot is claimed: an image without the descriptor
    sector cannot consume the one-shot, so the gate must fail closed
    rather than boot a payload-less disk green.
    """
    return read_payload_descriptor(image)


def verify_sector_gap_reserved(
    image: Path, *, allow_current_descriptor: bool = False
) -> dict[str, object]:
    """Pin the sector 1-2047 gap reservation against future GRUB core use.

    Sector 1 must carry either zeroes (pre-payload assembly) or the
    current ``GREIAPY1`` descriptor; sectors 2-2047 must read all zero.
    Any foreign/non-zero byte raises :class:`PayloadError` RED so a
    future ``core.img`` gap embed cannot silently clobber the descriptor
    (or hide inside the reserved gap). Reads are bounded to the gap
    window in 8 MiB streaming chunks; no whole-gap RAM copy is held.

    When ``allow_current_descriptor`` is true (embed path), sector 1 may
    already carry this payload's descriptor; otherwise only zeroes are
    accepted there (post-assembly guard path).
    """
    image = Path(image)
    gap_end = PARTITION_1_FIRST_SECTOR * 512
    if image.stat().st_size < gap_end:
        raise PayloadError("image is too small for the sector-gap guard")
    with open(image, "rb") as handle:
        handle.seek(DESCRIPTOR_OFFSET)
        sector1 = handle.read(DESCRIPTOR_LENGTH)
        if len(sector1) != DESCRIPTOR_LENGTH:
            raise PayloadError("sector-1 guard read is short")
        if sector1.startswith(PAYLOAD_MAGIC):
            if not allow_current_descriptor:
                _check_descriptor_hashes_ascii(sector1)
        elif any(sector1):
            raise PayloadError(
                "sector 1 carries foreign bytes; refusing "
                "(gap sectors 1-2047 are reserved, see coordination note)"
            )
        handle.seek(DESCRIPTOR_OFFSET + DESCRIPTOR_LENGTH)
        remaining = gap_end - (DESCRIPTOR_OFFSET + DESCRIPTOR_LENGTH)
        while remaining > 0:
            chunk = handle.read(min(8 * 1024 * 1024, remaining))
            if not chunk:
                raise PayloadError("sector-gap guard read is short")
            if any(chunk):
                raise PayloadError(
                    "gap sectors 2-2047 carry foreign bytes; refusing "
                    "(reserved for the payload descriptor coordination)"
                )
            remaining -= len(chunk)
    return {
        "reserved_first_sector": SECTOR_GAP_FIRST_SECTOR,
        "reserved_last_sector": SECTOR_GAP_LAST_SECTOR,
        "partition_1_first_sector": PARTITION_1_FIRST_SECTOR,
        "sector_1_state": (
            "descriptor" if sector1.startswith(PAYLOAD_MAGIC) else "zero"
        ),
        "note": SECTOR_GAP_COORDINATION_NOTE,
    }


def _check_descriptor_hashes_ascii(sector1: bytes) -> None:
    if sector1[len(PAYLOAD_MAGIC)] != PAYLOAD_VERSION:
        raise PayloadError("payload descriptor version is unknown")
    try:
        digests = (sector1[9:73].decode("ascii"), sector1[73:137].decode("ascii"))
    except UnicodeDecodeError as exc:
        raise PayloadError("payload descriptor hashes are not ASCII") from exc
    for digest in digests:
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise PayloadError("payload descriptor hashes are malformed")


def verify_staged_payload(payload_dir: Path) -> PayloadManifest:
    """Re-prove a staging dir against its manifest + production seams.

    Re-hashes both files (streaming), re-validates ``grub.cfg`` through
    ``validate_grub_ab_text``, and re-inspects ``grubenv`` through
    ``GrubEnvBackend.attach(...).inspect()`` (must be default A, no
    one-shot armed at staging time). Raises :class:`PayloadError` RED on
    any mismatch.
    """
    from greia_platform.grub_ab import GrubEnvBackend, validate_grub_ab_text

    root = Path(payload_dir)
    manifest_raw = json.loads((root / STAGED_MANIFEST_NAME).read_text(encoding="utf-8"))
    grub_bytes = (root / STAGED_GRUB_CFG_NAME).read_bytes()
    validate_grub_ab_text(grub_bytes.decode("utf-8"))
    if _sha256_bytes(grub_bytes) != manifest_raw["grub_cfg_sha256"]:
        raise PayloadError("staged grub.cfg does not match the payload manifest")
    if _sha256_file(root / STAGED_GRUBENV_NAME) != manifest_raw["grubenv_sha256"]:
        raise PayloadError("staged grubenv does not match the payload manifest")

    probe = root / ".attest-probe"
    if probe.exists():
        shutil.rmtree(probe)
    probe.mkdir(parents=True, exist_ok=True)
    try:
        (probe / "grubenv").write_bytes((root / STAGED_GRUBENV_NAME).read_bytes())
        state = GrubEnvBackend.attach(probe).inspect()
    finally:
        shutil.rmtree(probe, ignore_errors=True)
    if state.default_slot != "A" or state.one_shot_slot is not None:
        raise PayloadError("staged grubenv is not a clean default-A block")
    return PayloadManifest(
        grub_cfg_sha256=str(manifest_raw["grub_cfg_sha256"]),
        grubenv_sha256=str(manifest_raw["grubenv_sha256"]),
        grub_cfg_bytes=int(manifest_raw["grub_cfg_bytes"]),
        grubenv_bytes=int(manifest_raw["grubenv_bytes"]),
    )


def read_attestation_signal(
    boot_control_dir: Path, *, expected_booted_slot: str
) -> dict[str, object]:
    """Evaluate the post-boot success signal through the production seam.

    ``boot_control_dir`` is the loop-mounted partition 1 on device, or a
    directory carrying the guest-mutated ``grubenv`` at source scope. The
    signal is the consumption record: ``next_entry`` absent AND
    ``greia_last_booted == expected_booted_slot``. Returns the observed
    state with ``consumed``; raises :class:`PayloadError` RED when the
    one-shot is still armed (N2: armed-but-unconsumed must not attest) or
    the observation names a different slot.
    """
    from greia_platform.grub_ab import GrubEnvBackend

    if expected_booted_slot not in ("A", "B"):
        raise PayloadError("expected_booted_slot must be the semantic slot A or B")
    state = GrubEnvBackend.attach(Path(boot_control_dir)).inspect()
    if state.one_shot_slot is not None:
        raise PayloadError(
            "armed-but-unconsumed one-shot must not attest: "
            f"next_entry still targets {state.one_shot_slot}"
        )
    if state.last_booted_slot != expected_booted_slot:
        raise PayloadError(
            f"no consumption delta for slot {expected_booted_slot}: "
            f"guest observation is {state.last_booted_slot!r}"
        )
    return {
        "consumed": True,
        "default_slot": state.default_slot,
        "last_booted_slot": state.last_booted_slot,
        "one_shot_slot": state.one_shot_slot,
        "seam": "GrubEnvBackend.attach(mountpoint).inspect()",
    }


def install_payload_to_device(image: Path, payload_dir: Path) -> dict[str, object]:
    """Copy the staged payload onto image partition 1 (capable host only).

    Device path for T7-DEVRUN2: requires a Linux+root host with
    losetup/mount/umount/partprobe/udevadm/mkfs.ext4 (fails closed
    elsewhere via the harness ``require_device_host``). Formats partition
    1, copies ``grub.cfg`` + ``grubenv`` to its root, syncs, and tears down
    loop/mount state in finally. Returns the post-copy verification
    (descriptor + staged hashes re-proven from the mountpoint). Never
    called source-scope; unit tests pin only the fail-closed gate.
    """
    from tools.x8_qemu.lifecycle import require_device_host

    require_device_host()
    manifest = verify_staged_payload(payload_dir)
    device = _loop_attach(Path(image))
    mounted: Path | None = None
    try:
        part = Path(str(device) + "p1")
        _run(["partprobe", str(device)])
        _run(["udevadm", "settle"])
        time.sleep(0.5)
        _run(["mkfs.ext4", "-L", "GREIA-BOOT", str(part)])
        mountpoint = Path(payload_dir).parent / "payload-mnt"
        mountpoint.mkdir(parents=True, exist_ok=True)
        _run(["mount", "-t", "ext4", str(part), str(mountpoint)])
        mounted = mountpoint
        try:
            shutil.copy2(
                Path(payload_dir) / STAGED_GRUB_CFG_NAME,
                mountpoint / STAGED_GRUB_CFG_NAME,
            )
            shutil.copy2(
                Path(payload_dir) / STAGED_GRUBENV_NAME,
                mountpoint / STAGED_GRUBENV_NAME,
            )
            subprocess.run(["sync"], capture_output=True, timeout=60)
            # Post-copy proof: the installed block must be a clean
            # default-A grubenv (default A, no one-shot armed). This is a
            # staging proof, not a boot attestation: a freshly staged
            # block carries no ``last_booted`` yet, so the consumption
            # gate (``read_attestation_signal``) must NOT run here — it
            # would RED on every install. Consumption is proven only
            # post-boot by the device lifecycle's loop remount/read path.
            from greia_platform.grub_ab import GrubEnvBackend as _Backend

            installed = _Backend.attach(mounted).inspect()
            if installed.default_slot != "A" or installed.one_shot_slot is not None:
                raise PayloadError(
                    "installed payload is not a clean default-A block"
                )
        finally:
            subprocess.run(
                ["umount", str(mountpoint)], capture_output=True, timeout=60
            )
            mounted = None
    finally:
        subprocess.run(
            ["losetup", "--detach", str(device)], capture_output=True, timeout=60
        )
    return {
        "installed": True,
        "grub_cfg_sha256": manifest.grub_cfg_sha256,
        "grubenv_sha256": manifest.grubenv_sha256,
    }


def _loop_attach(image: Path) -> Path:
    completed = subprocess.run(
        ["losetup", "--find", "--show", str(image)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if completed.returncode != 0:
        raise PayloadError("loop attach failed for the disposable image")
    return Path(completed.stdout.strip())


def _run(argv: list[str]) -> None:
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    if completed.returncode != 0:
        raise PayloadError(f"device payload install failed: {argv[0]}")


def payload_assembly_cost(payload_dir: Path) -> dict[str, object]:
    """Measured assembly cost: files touched, bounded reads, no RAM copy."""
    root = Path(payload_dir)
    files = sorted(p.name for p in root.iterdir() if p.is_file())
    total = sum(p.stat().st_size for p in root.iterdir() if p.is_file())
    return {
        "files": files,
        "files_touched": len(files),
        "total_bytes": total,
        "whole_payload_ram_copy": False,
        "largest_single_read_bytes": 512,
    }
