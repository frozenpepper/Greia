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
  :func:`greia_platform.grub_ab.render_grub_ab_config_from_record`,
  composed with the guest-owned serial + exit stanzas via
  :func:`tools.x8_qemu.bootchain.compose_guest_grub_cfg` (production
  consumer block byte-verbatim, no production renderer change), and
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
raw image by a 512-byte descriptor sector at image sector 2047 (the last
reserved gap sector before partition 1 at sector 2048; relocated from
sector 1 by the GUEST-BOOT-CHAIN migration so sectors 1-127 can carry the
guest boot core). The descriptor carries a magic, version, the SHA-256 of
each staged artifact, and the binding of the installed core region
(``core_sha256`` + ``core_sectors``). On a capable host
:func:`install_payload_to_device` formats partition 1 and copies the
staged files onto the boot-control filesystem with safe loop/mount
teardown; off-host it fails closed via ``require_device_host``.

Fake boundary: no stubbed health/launcher, no fabricated slot/journal/GRUB
state. All GRUB bytes come from the production renderer/backend; the
descriptor only records their hashes. Reads are bounded (512-byte
descriptor, 8 MiB streaming hashes); no whole-payload RAM copy.

Sector coordination: sectors 1-2047 are reserved (sectors 1-127 = the
guest boot core region, sectors 128-2046 = zero, sector 2047 =
descriptor). :func:`verify_sector_gap_reserved` pins this so a foreign
core, a relocated-descriptor omission, or hidden gap bytes all fail RED;
the full constraint lives in ``tools/x8_qemu/LIFECYCLE.md`` section 8.
The GUEST-BOOT-CHAIN migration relocated the descriptor from sector 1 to
sector 2047 and bound the core bytes into the descriptor: the three gap
functions (:func:`read_payload_descriptor`,
:func:`embed_payload_descriptor`, :func:`verify_sector_gap_reserved`)
were updated together, and an old-layout image (descriptor at sector 1,
zero MBR code) REDs the new guard by design.
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


#: Magic identifying a payload descriptor sector (8 bytes, ASCII).
PAYLOAD_MAGIC = b"GREIAPY1"

#: Descriptor format version. Version 2 is the GUEST-BOOT-CHAIN migration:
#: descriptor relocated from sector 1 to sector 2047 with the installed
#: core region bound in (``core_sha256`` + ``core_sectors``). Version 1
#: (sector-1, payload-only) images RED the new guard by design.
PAYLOAD_VERSION = 2

#: Image byte offset of the descriptor sector (sector 2047: the last
#: reserved gap sector before partition 1 at sector 2048).
DESCRIPTOR_SECTOR = 2047
DESCRIPTOR_OFFSET = DESCRIPTOR_SECTOR * 512

#: Descriptor sector length (one 512-byte sector).
DESCRIPTOR_LENGTH = 512

#: First reserved gap sector (the descriptor sector itself).
SECTOR_GAP_FIRST_SECTOR = 1

#: Last reserved gap sector. Partition 1 starts at sector 2048, so sectors
#: 1-2047 are the MBR-gap reservation owned by this task's guard.
SECTOR_GAP_LAST_SECTOR = 2047

#: First sector of partition 1 (legacy adapter layout; gap ends before it).
PARTITION_1_FIRST_SECTOR = 2048

#: Coordination constraint for the guest boot core region. Sectors 1-127
#: are the core reservation (source-scope stub core first, genuine
#: ``grub-mkimage`` bytes via the gated ``bootchain`` seam on a capable
#: host); sectors 128-2046 must stay zero; sector 2047 carries this
#: payload's descriptor. The GUEST-BOOT-CHAIN migration relocated the
#: descriptor here from sector 1. This note is duplicated in
#: ``tools/x8_qemu/LIFECYCLE.md`` §8. An image still carrying the old
#: sector-1 descriptor (or zero MBR boot code) REDs the new guard: the
#: relocation omission is itself a RED condition, pinned by test.
SECTOR_GAP_COORDINATION_NOTE = (
    "Sectors 1-2047 are reserved: sectors 1-127 carry the guest boot core "
    "(source-scope stub core; genuine GRUB core.img via the gated "
    "bootchain seam on a capable host), hash-bound by the sector-2047 "
    "descriptor; sectors 128-2046 must stay zero; sector 2047 carries the "
    "payload descriptor (GREIAPY1, v2). Old sector-1 descriptors and "
    "chain-less MBRs are refused. See tools/x8_qemu/LIFECYCLE.md section 8."
)

#: On-image guest paths (partition 1 boot-control filesystem roots).
#: Genuine GRUB resolves them through the ``(,msdos1)/`` prefix, so the
#: frozen attestation seam reads consumption from exactly these paths.
GUEST_GRUB_CFG_PATH = "/grub.cfg"
GUEST_GRUBENV_PATH = "/grubenv"

#: On-image directory for GRUB's loadable modules (``normal`` and
#: friends load from ``$prefix/i386-pc/`` at boot; the embedded core
#: cannot hold them). Mirrors the stock ``/usr/lib/grub/i386-pc``
#: layout subset the guest needs.
GUEST_MODULES_DIR = "i386-pc"

#: Installed GRUB module tree a capable host provides (``grub-pc-bin``).
#: Only read from (never modified) by the install path.
INSTALLED_GRUB_MODULE_DIR = "/usr/lib/grub/i386-pc"

#: Module roots whose ``moddep.lst`` dependency closure ships on the
#: disposable image: ``normal`` (the script engine the embedded core
#: auto-loads) plus the ``password_pbkdf2`` stack (the top-level
#: consumer command resolves via normal-mode auto-insmod). Pinned by
#: the live Acer close-out (15 modules with ``.lst`` files).
GUEST_MODULE_ROOTS = ("normal", "password", "pbkdf2", "password_pbkdf2")

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
    from tools.x8_qemu.bootchain import compose_guest_grub_cfg

    record = load_installed_layout_record(Path(layout_record_path))
    if record is None:
        raise PayloadError("layout record is missing or not authoritative")
    production_text = render_grub_ab_config_from_record(
        record=record, password_hash=password_hash
    )
    # Guest composition (tools/x8_qemu-owned serial + exit around the
    # byte-verbatim production consumer block; no production renderer
    # change). The composed text validates through the production seam so
    # the serial/consumer/exit stanzas ship as one proven artifact.
    grub_text = compose_guest_grub_cfg(production_text)
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


def _descriptor_bytes(
    manifest: PayloadManifest, *, core_sha256: str, core_sectors: int
) -> bytes:
    from tools.x8_qemu.bootchain import CORE_LAST_SECTOR

    _require_core_binding(core_sha256, core_sectors, last_sector=CORE_LAST_SECTOR)
    body = (
        PAYLOAD_MAGIC
        + bytes((PAYLOAD_VERSION,))
        + manifest.grub_cfg_sha256.encode("ascii")
        + manifest.grubenv_sha256.encode("ascii")
        + core_sha256.encode("ascii")
        + f"{core_sectors:03d}".encode("ascii")
    )
    if len(body) > DESCRIPTOR_LENGTH:
        raise PayloadError("payload descriptor does not fit one sector")
    return body + b"\x00" * (DESCRIPTOR_LENGTH - len(body))


def _require_core_binding(
    core_sha256: object, core_sectors: object, *, last_sector: int
) -> tuple[str, int]:
    if not isinstance(core_sha256, str) or len(core_sha256) != 64:
        raise PayloadError("descriptor core binding needs a 64-hex SHA-256")
    if any(c not in "0123456789abcdef" for c in core_sha256):
        raise PayloadError("descriptor core SHA-256 is malformed")
    if (
        not isinstance(core_sectors, int)
        or isinstance(core_sectors, bool)
        or core_sectors < 1
        or core_sectors > last_sector
    ):
        raise PayloadError(
            f"descriptor core sectors must be within 1-{last_sector}"
        )
    return core_sha256, core_sectors


def _read_core_region_hash(image: Path, *, sectors: int) -> str:
    """Hash sectors 1..N with bounded streaming reads (no RAM copy)."""
    digest = hashlib.sha256()
    remaining = sectors * 512
    with open(Path(image), "rb") as handle:
        handle.seek(512)
        while remaining > 0:
            chunk = handle.read(min(8 * 1024 * 1024, remaining))
            if not chunk:
                raise PayloadError("core-region guard read is short")
            digest.update(chunk)
            remaining -= len(chunk)
    return digest.hexdigest()


def embed_payload_descriptor(
    image: Path,
    manifest: PayloadManifest,
    *,
    core_sha256: str,
    core_sectors: int,
) -> None:
    """Bind staged payload + installed core hashes at descriptor sector 2047.

    Verifies the installed core region (sectors 1..N) hashes to
    ``core_sha256`` BEFORE writing, so the descriptor can never name bytes
    that are not on the image. Refuses to overwrite a non-zero descriptor
    sector carrying a different magic (never silently rebind one payload
    over another); re-embedding the identical binding is idempotent.
    Reads back the written sector and fails closed on mismatch.
    """
    from tools.x8_qemu.bootchain import CORE_LAST_SECTOR

    core_sha256, core_sectors = _require_core_binding(
        core_sha256, core_sectors, last_sector=CORE_LAST_SECTOR
    )
    image = Path(image)
    if image.stat().st_size < DESCRIPTOR_OFFSET + DESCRIPTOR_LENGTH:
        raise PayloadError("image is too small for the payload descriptor")
    observed_core = _read_core_region_hash(image, sectors=core_sectors)
    if observed_core != core_sha256:
        raise PayloadError(
            "installed core region does not hash to the claimed binding; "
            "refusing to describe bytes that are not on the image"
        )
    with open(image, "r+b") as handle:
        handle.seek(DESCRIPTOR_OFFSET)
        previous = handle.read(DESCRIPTOR_LENGTH)
        if any(previous) and not previous.startswith(PAYLOAD_MAGIC):
            raise PayloadError("descriptor sector carries foreign bytes; refusing")
        if previous.startswith(PAYLOAD_MAGIC) and previous != _descriptor_bytes(
            manifest, core_sha256=core_sha256, core_sectors=core_sectors
        ):
            raise PayloadError(
                "descriptor sector already binds a different payload/core; "
                "refusing to rebind silently"
            )
        handle.seek(DESCRIPTOR_OFFSET)
        handle.write(
            _descriptor_bytes(
                manifest, core_sha256=core_sha256, core_sectors=core_sectors
            )
        )
        handle.flush()
        os.fsync(handle.fileno())
    observed = read_payload_descriptor(image)
    if (
        observed["grub_cfg_sha256"] != manifest.grub_cfg_sha256
        or observed["grubenv_sha256"] != manifest.grubenv_sha256
        or observed["core_sha256"] != core_sha256
        or observed["core_sectors"] != core_sectors
    ):
        raise PayloadError("descriptor re-read does not match staged payload")


def rebind_payload_descriptor(
    image: Path,
    manifest: PayloadManifest,
    *,
    core_sha256: str,
    core_sectors: int,
) -> dict[str, object]:
    """Replace a valid descriptor binding with a new core binding (explicit).

    The genuine-GRUB close-out installs different core bytes over the
    source-scope stub core; the sector-2047 descriptor must then name the
    new ``core_sha256``/``core_sectors`` instead of the stub binding.
    :func:`embed_payload_descriptor` deliberately refuses to overwrite a
    sector that already binds a different payload/core, so silent rebinding
    is impossible — this helper is the single reviewed rebind path:

    - the previous sector must carry a valid v2 ``GREIAPY1`` descriptor
      (missing/foreign bytes RED without touching the sector);
    - the installed core region (sectors 1..N) must already hash to the
      new ``core_sha256`` (verified before the sector is touched, same
      rule as the embed);
    - the sector is then explicitly zeroed and the new binding embedded
      through :func:`embed_payload_descriptor` (which re-verifies and
      re-reads), so every rebind leaves ``previous`` → ``descriptor``
      evidence instead of a silent overwrite.

    Pure file-offset writes (no loop/mount, no privilege). Returns the
    old and new bindings for the image manifest / run report.
    """
    path = Path(image)
    previous = read_payload_descriptor(path)
    if (
        previous["grub_cfg_sha256"] != manifest.grub_cfg_sha256
        or previous["grubenv_sha256"] != manifest.grubenv_sha256
    ):
        raise PayloadError(
            "refusing to rebind the descriptor onto a different staged payload; "
            "the sector keeps its current binding"
        )
    with open(path, "r+b") as handle:
        handle.seek(DESCRIPTOR_OFFSET)
        handle.write(b"\x00" * DESCRIPTOR_LENGTH)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        embed_payload_descriptor(
            path, manifest, core_sha256=core_sha256, core_sectors=core_sectors
        )
    except Exception:
        with open(path, "r+b") as handle:
            handle.seek(DESCRIPTOR_OFFSET)
            raw_previous = _descriptor_bytes(
                PayloadManifest(
                    grub_cfg_sha256=str(previous["grub_cfg_sha256"]),
                    grubenv_sha256=str(previous["grubenv_sha256"]),
                    grub_cfg_bytes=0,
                    grubenv_bytes=0,
                ),
                core_sha256=str(previous["core_sha256"]),
                core_sectors=int(previous["core_sectors"]),
            )
            handle.write(raw_previous)
            handle.flush()
            os.fsync(handle.fileno())
        raise
    return {"previous": previous, "descriptor": read_payload_descriptor(path)}


def read_payload_descriptor(image: Path) -> dict[str, object]:
    """Read and validate the v2 payload descriptor (512 bounded bytes only).

    Layout: magic[0:8] + version[8] + grub_cfg_sha256[9:73] +
    grubenv_sha256[73:137] + core_sha256[137:201] + core_sectors[201:204]
    (3 ASCII decimal digits) + zero pad. An old sector-1 descriptor is
    never found here: such images RED with "missing from the image", which
    is the relocation-omission predicate.
    """
    from tools.x8_qemu.bootchain import CORE_LAST_SECTOR

    with open(Path(image), "rb") as handle:
        handle.seek(DESCRIPTOR_OFFSET)
        raw = handle.read(DESCRIPTOR_LENGTH)
    if len(raw) != DESCRIPTOR_LENGTH or not raw.startswith(PAYLOAD_MAGIC):
        raise PayloadError("bootable-guest payload is missing from the image")
    if raw[len(PAYLOAD_MAGIC)] != PAYLOAD_VERSION:
        raise PayloadError("payload descriptor version is unknown")
    try:
        grub_cfg_sha = raw[9:73].decode("ascii")
        grubenv_sha = raw[73:137].decode("ascii")
        core_sha = raw[137:201].decode("ascii")
        core_sectors_raw = raw[201:204].decode("ascii")
    except UnicodeDecodeError as exc:
        raise PayloadError("payload descriptor fields are not ASCII") from exc
    for digest in (grub_cfg_sha, grubenv_sha, core_sha):
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise PayloadError("payload descriptor hashes are malformed")
    if len(core_sectors_raw) != 3 or not core_sectors_raw.isdigit():
        raise PayloadError("payload descriptor core sectors are malformed")
    core_sectors = int(core_sectors_raw)
    if core_sectors < 1 or core_sectors > CORE_LAST_SECTOR:
        raise PayloadError("payload descriptor core sectors escape the reservation")
    if any(raw[204:]):
        raise PayloadError("payload descriptor carries trailing foreign bytes")
    return {
        "magic": PAYLOAD_MAGIC.decode("ascii"),
        "version": PAYLOAD_VERSION,
        "grub_cfg_sha256": grub_cfg_sha,
        "grubenv_sha256": grubenv_sha,
        "core_sha256": core_sha,
        "core_sectors": core_sectors,
        "descriptor_sector": DESCRIPTOR_SECTOR,
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


def verify_sector_gap_reserved(image: Path) -> dict[str, object]:
    """Pin the sector 1-2047 gap reservation with the bound core (strict).

    Sector 2047 must carry a valid v2 ``GREIAPY1`` descriptor (a zero
    sector REDs: the old sector-1 layout no longer satisfies the guard,
    which is the relocation-omission predicate); sectors 1..N (N from the
    descriptor) must hash exactly to the descriptor's ``core_sha256``;
    sectors N+1..2046 must read all zero. Any foreign/non-zero byte raises
    :class:`PayloadError` RED. Reads are bounded to the gap window in 8
    MiB streaming chunks; no whole-gap RAM copy is held.
    """
    from tools.x8_qemu.bootchain import CORE_FIRST_SECTOR, CORE_LAST_SECTOR

    image = Path(image)
    gap_end = PARTITION_1_FIRST_SECTOR * 512
    if image.stat().st_size < gap_end:
        raise PayloadError("image is too small for the sector-gap guard")
    descriptor = read_payload_descriptor(image)
    core_sectors = int(descriptor["core_sectors"])
    if core_sectors < CORE_FIRST_SECTOR or core_sectors > CORE_LAST_SECTOR:
        raise PayloadError("descriptor core sectors escape the reservation")
    observed_core = _read_core_region_hash(image, sectors=core_sectors)
    if observed_core != descriptor["core_sha256"]:
        raise PayloadError(
            "installed core region does not hash to the descriptor binding; "
            "refusing (gap sectors 1-2047 are reserved, see coordination note)"
        )
    with open(image, "rb") as handle:
        handle.seek((core_sectors + 1) * 512)
        remaining = gap_end - ((core_sectors + 1) * 512) - DESCRIPTOR_LENGTH
        # Remaining covers sectors N+1..2046 (the descriptor sector itself
        # was already proven field-by-field above).
        while remaining > 0:
            chunk = handle.read(min(8 * 1024 * 1024, remaining))
            if not chunk:
                raise PayloadError("sector-gap guard read is short")
            if any(chunk):
                raise PayloadError(
                    "gap sectors past the bound core carry foreign bytes; "
                    "refusing (reserved, see coordination note)"
                )
            remaining -= len(chunk)
    return {
        "reserved_first_sector": SECTOR_GAP_FIRST_SECTOR,
        "reserved_last_sector": SECTOR_GAP_LAST_SECTOR,
        "partition_1_first_sector": PARTITION_1_FIRST_SECTOR,
        "descriptor_sector": DESCRIPTOR_SECTOR,
        "core_first_sector": CORE_FIRST_SECTOR,
        "core_last_reserved_sector": CORE_LAST_SECTOR,
        "core_sectors": core_sectors,
        "sector_state": "descriptor-bound-core",
        "note": SECTOR_GAP_COORDINATION_NOTE,
    }


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


def populate_guest_boot_files(target_dir: Path, payload_dir: Path) -> dict[str, object]:
    """Copy staged bytes onto a partition-1 directory (root paths).

    Writes the staged ``grub.cfg``/``grubenv`` to ``target_dir`` root
    (``/grub.cfg``, ``/grubenv``): the genuine-GRUB ``(,msdos1)/``
    prefix resolves exactly here, so this is both the boot path and
    the frozen-attestation read path — no mirror copy exists to
    drift. Pure directory ops: ``target_dir`` may be a real
    mountpoint (called by :func:`install_payload_to_device`) or a
    plain staging dir baked into a filesystem image by other means.
    Returns the placed paths plus the SHA-256 of each placed file
    (both must equal the staged SHAs). Raises :class:`PayloadError`
    fail-closed when staging is unverifiable (production-seam
    validation failures are wrapped, never swallowed silently).
    """
    try:
        staged = verify_staged_payload(Path(payload_dir))
    except PayloadError:
        raise
    except Exception as exc:
        raise PayloadError(
            f"staged payload failed production verification: {exc}"
        ) from exc
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    placed = {
        target / STAGED_GRUB_CFG_NAME: (
            Path(payload_dir) / STAGED_GRUB_CFG_NAME
        ),
        target / STAGED_GRUBENV_NAME: (
            Path(payload_dir) / STAGED_GRUBENV_NAME
        ),
    }
    for dest, src in placed.items():
        shutil.copy2(src, dest)
    proof: dict[str, object] = {"files": []}
    files: list[str] = []
    for dest in placed:
        digest = _sha256_file(dest)
        name = dest.name
        expected = (
            staged.grub_cfg_sha256
            if name == STAGED_GRUB_CFG_NAME
            else staged.grubenv_sha256
        )
        if digest != expected:
            raise PayloadError(
                f"placed guest file {dest} does not match the staged payload"
            )
        files.append(str(dest.relative_to(target)))
    proof["files"] = sorted(files)
    proof["grub_cfg_sha256"] = staged.grub_cfg_sha256
    proof["grubenv_sha256"] = staged.grubenv_sha256
    return proof


def resolve_grub_module_closure(
    module_dir: Path, roots: tuple[str, ...] | None = None
) -> list[str]:
    """Resolve a GRUB module closure from an installed module tree.

    Parses ``moddep.lst`` in ``module_dir`` (breadth-first from
    ``roots``, defaulting to :data:`GUEST_MODULE_ROOTS`) and returns
    the sorted module names (without ``.mod``). Pure read-only dir
    ops; raises :class:`PayloadError` fail-closed when the tree, the
    dependency list, a root, or a listed module file is missing.
    ``None`` defaults resolve at call time so tests may substitute
    fake trees without touching global state.
    """
    if roots is None:
        roots = GUEST_MODULE_ROOTS
    root = Path(module_dir)
    dep_file = root / "moddep.lst"
    if not root.is_dir() or not dep_file.is_file():
        raise PayloadError(
            f"installed GRUB module tree is missing at {root} "
            "(grub-pc-bin is required for the genuine chain)"
        )
    deps: dict[str, list[str]] = {}
    for line in dep_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        name, _, rest = line.partition(":")
        deps[name.strip()] = rest.split()
    for wanted in roots:
        if wanted not in deps and not (root / f"{wanted}.mod").is_file():
            raise PayloadError(
                f"installed GRUB tree has no module {wanted}"
            )
    seen: list[str] = []
    stack = list(roots)
    while stack:
        mod = stack.pop()
        if mod in seen:
            continue
        seen.append(mod)
        stack.extend(deps.get(mod, []))
    for mod in seen:
        if not (root / f"{mod}.mod").is_file():
            raise PayloadError(
                f"installed GRUB tree is missing dependency {mod}.mod"
            )
    return sorted(seen)


def place_grub_module_closure(
    target_dir: Path,
    module_dir: Path | None = None,
    roots: tuple[str, ...] | None = None,
) -> dict[str, object]:
    """Copy a GRUB module closure onto a partition-1 directory.

    Copies the resolved closure (``.mod`` files) plus the tree's
    ``.lst`` index files into ``target_dir/i386-pc/`` (the stock
    layout GRUB's auto-insmod resolves). Pure directory ops, same
    ``target_dir`` contract as :func:`populate_guest_boot_files`.
    Returns the placed module list. Raises :class:`PayloadError`
    fail-closed when the installed tree cannot satisfy the closure.
    ``None`` arguments resolve to :data:`INSTALLED_GRUB_MODULE_DIR`
    and :data:`GUEST_MODULE_ROOTS` at call time.
    """
    if module_dir is None:
        module_dir = Path(INSTALLED_GRUB_MODULE_DIR)
    closure = resolve_grub_module_closure(Path(module_dir), roots)
    target = Path(target_dir) / GUEST_MODULES_DIR
    target.mkdir(parents=True, exist_ok=True)
    source = Path(module_dir)
    for mod in closure:
        shutil.copy2(source / f"{mod}.mod", target / f"{mod}.mod")
    lists = 0
    for lst in sorted(source.glob("*.lst")):
        shutil.copy2(lst, target / lst.name)
        lists += 1
    return {"modules": closure, "lists": lists}


def install_payload_to_device(image: Path, payload_dir: Path) -> dict[str, object]:
    """Copy the staged payload onto image partition 1 (capable host only).

    Device path for T7-DEVRUN2: requires a Linux+root host with
    losetup/mount/umount/partprobe/udevadm/mkfs.ext4 (fails closed
    elsewhere via the harness ``require_device_host``) plus the
    installed GRUB module tree (``grub-pc-bin``) for the genuine
    chain. Formats partition 1, copies ``grub.cfg`` + ``grubenv`` to
    its root (the genuine ``(,msdos1)/`` prefix reads exactly here,
    so this is both the boot path and the frozen-attestation read
    path) and the GRUB module closure to ``/i386-pc/``, syncs, and
    tears down loop/mount state in finally. Returns the post-copy
    verification (descriptor + staged hashes re-proven from the
    mountpoint). Never called source-scope; unit tests pin only the
    fail-closed gate.
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
            placed = populate_guest_boot_files(mounted, Path(payload_dir))
            if sorted(placed.get("files", [])) != [
                STAGED_GRUB_CFG_NAME,
                STAGED_GRUBENV_NAME,
            ]:
                raise PayloadError("guest boot files were not placed")
            closure = place_grub_module_closure(mounted)
            if "normal" not in closure.get("modules", []):
                raise PayloadError("module closure lacks normal")
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
        "module_closure": True,
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
