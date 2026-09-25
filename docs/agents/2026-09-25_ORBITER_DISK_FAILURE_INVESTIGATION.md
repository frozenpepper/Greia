# Orbiter host disk failure — investigation and agent-hygiene report

**Date:** 2026-09-25
**Host:** Orbiter (Mac mini, x86_64) — Greia build / Session-04 QEMU validation host
**Author:** agent (opencode), ordered by repository owner
**Status:** DISK FAILURE CONFIRMED (hardware); full-disk migration to replacement drive in progress
**Audience:** future agents working on this repository. This is a durable host-hygiene contract; the prevention rules in §5 are also enforced in `docs/agents/GREIA_AGENT_OPERATIONS.md` §12.

## 1. What happened

The Orbiter root disk — SAMSUNG HN-M500MBB, 500 GB, 2.5" 5400 rpm SATA, serial
`S2R7J9HB601575`, holding `/` (`sda2`) and the ESP (`sda1`) — entered media
failure. The failure surfaced as a Session-04 diagnostic installer build dying
during squashfs verification:

```text
unsquashfs: Read failed because Input/output error
FATAL ERROR: Can't find a valid SQUASHFS superblock on
/tmp/greia-installer-build.9GFAXv/pip-rootfs.squashfs
```

The file had just been written by `mksquashfs` (exit 0); the read-back failed
because the underlying disk sector could not be read. This was **not** a Greia
source defect.

SMART confirms a terminal hardware state:

```text
SMART overall-health self-assessment test result: FAILED!
Drive failure expected in less than 24 hours. SAVE ALL DATA.

ID  ATTRIBUTE              VALUE THRESH RAW        STATE
  1 Raw_Read_Error_Rate      001    051   63911    FAILING_NOW
197 Current_Pending_Sector   100    000   2        (pending)
  5 Reallocated_Sector_Ct    252    010   0
191 G-Sense_Error_Rate       054    000   469569
  9 Power_On_Hours           100    000   1622
194 Temperature_Celsius      058    000   42
```

Two sectors are stuck un-remapped (`Reallocated = 0`, `Current_Pending = 2`),
matching exactly the two persistent failing regions in the kernel journal:

- sector `962589320` ≈ byte offset 492.9 GB
- sector `710844416` ≈ byte offset 364.0 GB

## 2. Timeline (kernel journal evidence)

First Medium Errors predate the heavy Greia build churn by 8+ days:

| When | What | Greia activity that day |
|---|---|---|
| 2026-09-15 01:55 | system boot (10-day uptime begins) | — |
| **2026-09-15 02:05:10** | **first I/O errors** (sectors 962589184/5408, 858801544, 69330792, 974610432, 421557704…) | none; repo commits that day are docs-only (18:32–20:02) |
| 2026-09-15 02:12–03:04 | same-sector retry storm every ~4 s (flags `0x0`, `phys_seg 3` — a userspace tool retrying one file region) | none |
| 2026-09-16 22:45 | Medium Error burst | (prior session work) |
| 2026-09-20 02:01–03:58 | 14 Medium Errors | — |
| 2026-09-22 18:16 | — | Session-03 release source commit |
| 2026-09-23 02:21 → 09-24 05:44 | — | ≥5 logged Session-04 installer builds (`/tmp/greia-session04-installer-build*.log`) |
| 2026-09-25 16:17 | 2 Medium Errors at sector 710844416 — **caused the build failure above** | installer rebuild |

39 Medium Error lines exist since 2026-09-01 in the persistent journal; the
first is 2026-09-15 02:05. Conclusion: **the drive was already failing before
the heaviest Greia I/O began.** Reads do not create bad sectors on a healthy
drive; heavy load only exposes an existing defect sooner.

## 3. What the agent work actually contributed (honest accounting)

The owner asked how this work "managed to fuck up a hard drive". The honest,
evidence-based answer has three parts.

### 3.1 Real damage I caused: leaked loop devices and mount-hygiene failure

At inspection time **17 Greia build loop devices** were still attached with
`(deleted)` backing files, e.g.:

```text
/dev/loop0: [2050]:12328004 (/tmp/greia-installer-build.o6rfun/target-out/greia-os-acer-aspire-one-i386-ab.img (deleted))
… (17 total; 2–3 GB PIP_ROOT images, each with a partition table + ext4 partition)
```

Consequences:

1. **Finder sidebar litter.** Every attached loop with a recognizable
   filesystem/partition is enumerated by udisks2/GNOME Files, producing the
   "pip_root" / "1.1 GB Volume" entries in every window. (Some sidebar volumes
   — the `aaaaaaaa-bbbb-…` UUIDs on `loop13/24/30/31` — come from partition
   tables embedded inside vendor snap images, not Greia; the PIP_ROOT entries
   are Greia's.)
2. **Pinned disk space.** Deleted-but-attached files stay allocated
   (~35–45 GB unreachable-but-used on the already-pressured root filesystem,
   which ran 83–90 % full during multi-GB image churn).
3. **Pointless repeated reads against the failing disk.** Desktop volume
   monitors re-probe the stale loops on every enumeration; reads through the
   loop backing files are reads of the failing root disk. Live example during
   this migration: `Buffer I/O error on dev loop31p1/p2/p4` logged at 17:32
   while the file manager was open.
4. **Host tooling stalls.** A full `blkid` scan timed out (>120 s) probing the
   stale loops; any block-device enumeration now walks them all.

**Cause chain:** installer builds create partitioned 2–3 GB images, attach
them with `losetup` + partscan, and on failure paths the image file was
deleted while the loop stayed attached; no post-run audit existed, and I did
not add one after failures. The stuck state is self-perpetuating: once
`autoclear=1` is set with partition mappings present, `losetup -d` returns 0
but never clears, and `partx -d` refuses (`error deleting partition`) — **only
a reboot clears it**. All 17 loops will clear during the disk-swap reboot.

### 3.2 Real damage I caused: retry storms without health checks

Each installer build writes ~3–4.5 GB of disk image plus a ~700 MB squashfs
and re-reads the full debootstrap rootfs. After each failure I re-ran the full
build instead of first checking `dmesg`/SMART — multiplying heavy I/O against
a drive that was already emitting Medium Errors (including the failing region
that caused the failure I was retrying into). ≥17 historical build temp
directories testify to the volume of runs.

### 3.3 What I did NOT cause

Loop attach/detach and mount cycles are in-kernel file mappings; they add no
mechanical wear. Medium Errors are magnetic-media/head degradation on a
2011-era laptop drive (`G-Sense_Error_Rate` raw 469569 also indicates a long
history of physical shock/vibration events). My workload amplified read load,
pinned space, and desktop probe traffic, and plausibly made the failure surface
sooner — but the root cause is hardware. First journal errors (09-15 02:05)
preceded the heavy build churn (09-22 onward).

## 4. Failure propagation to Session 04

The 2026-09-25 Session-04 validation stopped here. The build failure was
environmental; the source tree at `c8054717` was verified first (9 focused
suites, all green: seam-composition 14, pool-cleanup 6, engine 18,
hardware-support 3, unit-contract 23, transaction-service 46, S04-legs 20,
product-install 38, update-seam 17). S03 bundle SHA and all four candidate
SHAs verified before the build attempt. **No capability/security decision is
pending on account of this failure** — the fatal-tail investigation from
`docs/testing/2026-09-25_SESSION04_APT_OWNERSHIP_DECISION.md` remains exactly
where it was; the next step after the host is repaired is to rebuild the
diagnostic installer and run fresh-install only, per the Session-04 procedure
§11.

## 5. Prevention rules (binding for future agents)

Also enforced in `docs/agents/GREIA_AGENT_OPERATIONS.md` §12:

1. **Disk-health preflight before heavy image churn.** Run
   `sudo smartctl -a <root-disk>` and `sudo journalctl -k -p err --since -1d`
   before build sessions. If overall-health is not `PASSED`, or pending-sector
   count grows, or any `Medium Error` appears: **stop disk-heavy work and
   escalate to the owner.** Do not "just retry".
2. **On any build I/O error, suspect the disk first.** Check
   `sudo dmesg | grep -i 'I/O error'` before touching source. A
   `Read failed because Input/output error` / squashfs-superblock failure after
   a clean `mksquashfs` is a disk fault until proven otherwise.
3. **Loop-device audit after every run** (success, failure, interrupt):

   ```bash
   sudo losetup -a | grep greia    # must be empty
   ```

   Detach **before** deleting image files: `losetup -d` → verify gone → `rm`.
   Never delete a backing file while its loop is attached. A loop that sticks
   with `autoclear=1` + partition mappings cannot be cleared without reboot —
   record it and do not accumulate more.
4. **Clean build temp dirs** (`/tmp/greia-installer-build.*`, old
   `/tmp/greia-session04-*` runs) after each run; do not leave 17 generations
   of debris.
5. **Free-space preflight.** Keep the build root filesystem below ~80 % during
   image churn; pinned/stale loops count as used space.
6. **Never leave stale volumes for the desktop to enumerate** — each one is a
   standing invitation for udisks/gvfs probe reads against the backing disk.

## 6. Replacement and migration record (2026-09-25)

Owner attached a replacement drive (same model, SAMSUNG HN-M500MBB, serial
`S2R7J9HB601552`, USB-3/UAS enclosure) and ordered a full-disk transfer so the
disk can be physically swapped into the Mac mini and the system boots as
before.

Migration steps executed (target verified by serial before every destructive
step; `sda` never written):

1. `wipefs -a /dev/sdb` (old MBR/HFS content cleared).
2. GPT cloned from the source via `sfdisk -d /dev/sda | sfdisk /dev/sdb`:
   identical geometry and **identical partition GUIDs**
   (`bb7e800d-c4e7-46ab-99e3-4029c21fa15b` ESP, `e5a2bbe1-…` root), so the
   firmware NVRAM entry `Boot0001* Ubuntu` (which references
   `HD(1,GPT,bb7e800d…,0x800,0x219800)`) keeps pointing at the new disk after
   the swap with no firmware changes.
3. Filesystems created with **cloned UUIDs**:
   `mkfs.ext4 -U 7893f386-186a-42d9-a8ef-9321c6fb9337` (root),
   `mkfs.vfat -i 9BFEA487` (ESP) — so `/etc/fstab`, the ESP stub
   (`search.fs_uuid 7893f386…`), `grub.cfg` and initramfs all work unchanged.
4. Full transfer: `rsync -aHAX --numeric-ids` from `/` to the new root,
   excluding only virtual/mount filesystems (`/dev /proc /sys /run /mnt
   /media /lost+found`), followed by a second catch-up pass, error review,
   `fsck`, and clean unmount.
5. Replacement SMART before trusting it: `PASSED`, 88 power-on hours,
   0 pending, 0 reallocated.

(Estimated timeline and final verification results are appended in §8 after
completion.)

## 7. Evidence pointers

- SMART: `sudo smartctl -a /dev/sda` (failing) and `/dev/sdb` (healthy) —
  outputs quoted in §1/§6; `smartmontools` installed 2026-09-25 for this.
- Kernel journal: `sudo journalctl -k --since 2026-09-01 | grep -E 'Medium|I/O error'`.
- Failed build tail: Session-04 build log of 2026-09-25 16:17 (§1).
- Build-run history: `/tmp/greia-session04-installer-build*.log` (5 files,
  2026-09-23…24), 17 `/tmp/greia-installer-build.*/` temp dirs.
- Loop inventory: `sudo losetup -a | grep greia` (17 entries at report time).
- Prior Session-04 evidence: `docs/testing/2026-09-25_SESSION04_APT_OWNERSHIP_DECISION.md`,
  `docs/testing/session04-evidence/`.

## 8. Completion addendum (appended 2026-09-25, migration complete)

### 8.1 Transfer results

- `rsync -aHAX --numeric-ids --info=progress2` of `/` to `/mnt/newroot`
  (excludes `/dev /proc /sys /run /mnt /media /lost+found`), run detached.
- **Pass 1: 18:05–20:58 (2 h 53 m), 376,342,209,141 bytes, 1,063,266 files
  transferred, 1,381,940 items walked. Exit code 23** with exactly two error
  causes, both accounted for below.
- **Pass 2 (catch-up): 20:59–21:18 (19 m), +6,442,610,343 bytes / 92 files**
  of live-changed data. Exit 23, same two causes only.
- Error list, complete:
  1. `opendir "/home/orb/Mounted/Argh" failed: No such device (19)` — the
     unattached exFAT automount stub (fstab `noauto,x-systemd.automount`).
     Not data. The stub directory was mirrored afterwards with attributes.
  2. `read errors mapping ".../Long-John-Silver/data/ljs.db": Input/output
     error` — the single real casualty; full account in §8.2.
- Pre-transfer USB event: before pass 1, the target enclosure logged one
  UAS link drop (buffer error on `sdb` sector 536, `device offline error`,
  `uas_eh_device_reset_handler FAILED to get lock`, device re-enumerated
  17:49:18). The mount and target filesystem survived; **zero further `sdb`
  errors** were observed for the remainder of the migration.

### 8.2 The one casualty: `ljs.db` and its recovery

File: `~/Works/Long-John-Silver/data/ljs.db`, 1,008,160,768 bytes, SQLite 3,
heavily fragmented (73 extents), data spanning the failing source region.

- rsync cannot tolerate a sender EIO, so the file was skipped (exit 23).
- Recovery attempt 1: `dd bs=512 conv=noerror,sync` — stalled >10 min in
  kernel retry grind; killed, partial output discarded.
- Recovery attempt 2: `dd bs=1M conv=noerror,sync` — completed in 55 s but
  short-read + sync-padding zeroed two 1 MiB blocks → a **2 MiB hole at file
  offsets 4,194,304–6,291,458** (the source of every integrity error seen).
- The hole's pages were also poisoned in the page cache (instant EIO on
  re-read). `posix_fadvise(POSIX_FADV_DONTNEED)` cleared the poison and
  proved the zone largely readable again.
- Block-level refill (4 KiB reads with per-block timeout) restored
  **495 of 513 blocks**. **16 contiguous blocks (64 KiB) at offsets
  4,521,984–4,587,520 are physically unreadable** (kernel:
  "Unrecovered read error - auto reallocate failed") and remain
  zero-filled. Repaired file is at the exact source size; its
  `PRAGMA integrity_check` errors are confined to that zone.
- Per-table salvage produced `ljs.recovered.db`
  (1,002,643,456 bytes): **`PRAGMA integrity_check` = ok, 49 tables,
  446,119 rows copied.** Exceptions:
  - `vec_embeddings` and `vec_embeddings_r1` need the app's `sqlite-vec`
    (`vec0`) extension to even open; their shadow tables
    (`*_info`, `*_chunks`, `*_rowids`) were all recovered, so the app can
    likely rebuild the vector indexes.
  - `vec_embeddings_vector_chunks00`: "database disk image is malformed" —
    its pages lived in the dead 64 KiB zone; that chunk table is the only
    confirmed unrecoverable data.
- **Both files are kept side by side**, `orb:orb`:
  `ljs.db` (original name, repaired, one zeroed zone) and
  `ljs.recovered.db` (clean, salvaged). The owner/app decides which to use.

### 8.3 Final verification (all passed)

- `diff /etc/fstab` source vs target: **byte-identical**.
- `diff -rq /boot/efi` source vs target: **byte-identical** (ESP).
- Repo spot checks (`AGENTS.md`, `HANDOVER.md`), Session-04 candidates
  (`/tmp/greia-session04-…/candidates/`), and the S03 bundle directory
  (`~/Works/Greia/tmp/session03-linux-release-6c58601e…/`) all present.
- `fsck -nf /dev/sdb2` **on cleanly unmounted filesystem**: passes 1–5,
  no errors (1,346,555 files, 94,900,890 blocks used).
- `dosfsck -n /dev/sdb1`: **clean** (11 files).
- Both filesystems cleanly unmounted after verification.
- Final SMART: source `S2R7J9HB601575` — Reallocated 0,
  Current_Pending **1** (down from 2); target `S2R7J9HB601552` — PASSED,
  0 pending, 0 reallocated.
- Incidental observation: an unidentified reader periodically re-read
  source sector 962589320 through the evening (journal, ~every 10–30 min);
  it did not affect the migration and is moot once the source disk is out.

### 8.4 Owner swap procedure

1. Power off completely (all writes flushed; both target filesystems are
   unmounted and fsck-clean).
2. Physically swap the failing Samsung `S2R7J9HB601575` out of the Mac mini
   for the prepared `S2R7J9HB601552` (or, if keeping the USB enclosure
   attached instead, treat it as the primary boot disk only if its firmware
   allows — the prepared disk is intended as the internal replacement).
3. Boot. Expected: GRUB/NVRAM `Boot0001* Ubuntu` resolves via the cloned
   GPT GUIDs, fstab mounts the cloned UUIDs, the system comes up unchanged.
   The 17 stale `PIP_ROOT` loops (deleted backings) are cleared by this
   reboot; `/home/orb/Mounted/Argh` remounts on demand from fstab.
4. Post-boot checks: `smartctl -a /dev/sda` (now the healthy drive) shows
   PASSED/0 pending; verify the Long-John-Silver project against `ljs.db`
   vs `ljs.recovered.db` and keep the better one; `git -C ~/Works/Greia
   pull` and resume Session-04 at procedure §3.

Swap/boot outcome itself is recorded in `HANDOVER.md` when the owner
executes it; nothing in this report depends on it retroactively.
