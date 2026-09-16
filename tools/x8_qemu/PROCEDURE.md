# X8 Disposable SeaBIOS QEMU Procedure — Legacy A/B Adapter

Source scope (X8-QEMU-HARNESS). Live SeaBIOS execution on a QEMU-capable
Linux host is **deferred per the source-first amendment** and stays RED
until a capable host backfills it. The procedure below is complete at
source scope: `make verify` green plus the unit contract in
`tests/test_x8_qemu/`.

Documents `tools/x8_qemu/runner.py` as implemented: the unsigned
`.greiaupdate` v3 bundle path (`build_update_bundle` /
`inspect_update_bundle`) with `release_id` release identity. No
signing step, no key material, and no extra signing dependency exist
in this procedure.

## 1. Exact layout / profile / release under test

- **Layout adapter:** `legacy-bios-ab-v1` (executable MBR A/B/PERSIST:
  `boot-control` 32 MiB, `system-a`, `system-b`, `persist` remainder;
  roles owned by `greia_installer.layout.LegacyBiosAbAdapter`).
- **Boot backend:** `grub-ab-v1` — real 1024-byte `grubenv` one-shot
  semantics (`saved_entry` persistent default, `next_entry`
  candidate-only one-shot, authoritative booted-slot observation via
  `GrubEnvBackend`). `simulate_reboot` is a source-scope test hook and is
  never used to assert VM behavior.
- **Reference profile:** `build/profiles/legacy-x86-i686.toml`
  (`legacy-x86-i686`): `system_slot_bytes` 1073741824, PERSIST minimum
  268435456, bounds preferred 800 / required 1000 / review 1250 MiB.
  That profile still declares `bios-single-ext4` + `none-v1`; this
  procedure builds the `legacy-bios-ab-v1` + `grub-ab-v1` test variant and
  claims **no profile-bounds conformance** beyond the stated MiB
  comparison in the report.
- **Release lineage:** `greia-x8qemu-0.20.0` (slot A) →
  `greia-x8qemu-0.21.0` (slot B) →
  `greia-x8qemu-0.22.0` (slot A), each an unsigned `.greiaupdate` v3
  bundle built through `build_update_bundle` and identified per run by
  `inspect_update_bundle` (release_id, payload SHA-256, bundle SHA-256).
  No sequence authority under ADR 0036; lineage order is the launch
  order only.

## 2. Host prerequisites (Linux x86_64 only)

1. Linux x86_64 host.
2. `qemu-system-x86_64` with SeaBIOS firmware for the `pc` machine
   (default SeaBIOS; explicit `-bios <path>` when supplied).
3. GRUB tooling compatible with the boot-control `grubenv` block.
4. Loopback + mount capability (`losetup`, `mount`, `partprobe`,
   `udevadm`, `mkfs.ext4`) for disposable raw-image assembly.
5. `python3` with Greia `src` on `PYTHONPATH`; v3 bundles need no key
   material.
6. Root for the privileged run (`os.geteuid() == 0` is enforced).

No GitHub-hosted Actions are used (opt-in only; no owner authorization).

## 3. Disposable-image build (outside the source tree)

1. Create an absolute `--output-dir` **outside** the repository
   (inside-tree output is refused fail-closed).
2. Prove the declarative MBR plan from profile sizing facts
   (`plan_for_profile` + `LegacyBiosAbAdapter.plan`); mint fresh
   PARTUUID/filesystem-UUID pairs per role
   (`mint_fresh_partition_identities` — never cloned template UUIDs).
3. Stage the inactive slot through `SlotWriter` (bounded-chunk streaming,
   readback digest) and `SlotFinalizer` (role-UUID restore, receipt) via
   the unsigned `.greiaupdate` v3 install/update path. No parallel writer,
   updater, installer, or boot manager exists in this procedure.
4. Render `grub.cfg` from the trusted layout record only
   (`render_grub_ab_config_from_record`); validate with
   `validate_grub_ab_text`. Initialize `grubenv` with the accepted slot
   as persistent default (`GrubEnvBackend.initialize`).
5. Assemble the raw image on loopback; record its SHA-256 identity.
   Valued devices are never contacted: the runner takes no device path.

## 4. Boot sequence (real SeaBIOS, real GRUB one-shot)

QEMU argv: `qemu-system-x86_64 -machine pc,accel=tcg -cpu max -display
none -monitor none -serial file:<serial.log> -nic none -boot
order=c,strict=on -no-reboot -drive
file=<image>,format=raw,if=ide,index=0,media=disk,cache=writeback`
(no snapshot flag: guest disk writes persist for observation).

| Run | Expected observation |
| --- | -------------------- |
| `cold-boot-A` | default A, booted A, no one-shot |
| `arm-B-one-shot` | default A, one-shot B armed |
| `boot-B-commit` | booted B, health commit advances default to B |
| `cold-boot-B` | default B, booted B, stable |
| `arm-A-one-shot-fail` | one-shot A armed, candidate fails health |
| `fallback-A` | default stays B…(see note), failed candidate falls back |
| `persist-verify-ABA` | PERSIST markers byte-identical across A→B→A |

Note: the exact default-slot assertions per run follow the
`GrubEnvBackend` contract (default moves only through the verified
health commit after the candidate provably booted; a consumed one-shot
without a health commit leaves the accepted default in place). Each run
records `release_id`, payload SHA-256, bundle SHA-256,
`image_sha256`, and the full `boot_backend_state`.

The 8-step lifecycle in `tools/x8_qemu/LIFECYCLE.md` builds on this
7-run sequence for lifecycle purposes; this 7-run sequence remains the
intact procedure for `runner.py`.

## 5. Footprint and staging-memory method

- **Disk footprint:** `require_finalized_slot_capacity` gate plus the
  disposable image size compared against the 800/1000/1250 MiB reference
  bounds (`footprint_report`). Comparison only.
- **Update-staging memory:** bounded by `SLOT_WRITE_CHUNK_BYTES` per
  chunk (`staging_memory_report`); no second payload-sized temporary.

## 6. Evidence and current status

- Per-run JSON report (`greia-x8-qemu-report.json`): procedure spec,
  QEMU version/argv, per-run release hashes + image identity +
  boot-backend state, footprint/memory comparisons, limitations.
- **RED / deferred:** live SeaBIOS boots on a QEMU-capable Linux host,
  trusted interactive-health observation, and any Acer contact. To be
  backfilled on-site per the source-first amendment; no hardware claim is
  made from source evidence.
