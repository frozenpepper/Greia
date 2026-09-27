# Session 04 recovery after Acer physical boot mistake — local agent runbook

**Date:** 2026-09-27
**Required ancestor:** `cc679a9b5a51ffc221f71ccff1ff9a78f4f4df5d`
**Purpose:** clean up the documentation/source-state confusion, build and flash the physically proven Acer Syslinux development installer, then resume the real Session-04 legacy A/B lifecycle work without confusing that engineering image with the future universal Setup image.

## 0. Non-negotiable architecture facts

Do not redesign these:

1. The product requirement remains **one universal Greia Setup image**.
2. “One image” does **not** mean “one bootloader”.
3. The authoritative universal layout is ADR 0036 + the active 2026-09-15 plan:
   - legacy BIOS / Acer removable boot: **SYSLINUX on active FAT32**;
   - modern amd64 UEFI: distro-supported UEFI shim/GRUB path on the same FAT boot partition;
   - Pi 400/500: Raspberry Pi firmware/config/DTB/kernel paths on that same FAT boot partition;
   - bulk i386/amd64/arm64 live roots and four release bundles live on P2.
4. Installed Acer/internal-disk boot remains **GRUB A/B**. The GRUB failure is specific to the removable USB first-stage path on the reference Acer/stick.
5. Session 04 is **not** “build the universal image”. Session 04 is still legacy-i386 fresh-install/update/rollback closure in product-mode QEMU. The real universal image is Session 08 after Sessions 05–07 provide amd64 and Pi boot paths.
6. Do not add `CAP_CHOWN` unless a new bounded apt/dpkg fatal tail proves it is actually required.
7. Do not add new gate frameworks, orchestration scaffolding, or parallel installer implementations.

## 1. Synchronize safely

```bash
cd /home/orb/Works/Greia
git fetch origin
git pull --ff-only
git rev-parse HEAD
git rev-parse origin/main
git merge-base --is-ancestor cc679a9b5a51ffc221f71ccff1ff9a78f4f4df5d HEAD
git status --short
```

Require:
- HEAD == origin/main;
- ancestor check exits 0;
- tracked tree clean.

If pull/fetch credentials fail, stop and fix authentication. Do not continue from a stale checkout and do not infer that a remote SHA “does not exist”.

Never use `git reset --hard`, `git clean`, or broad stashing/deletion to resolve divergence.

## 2. Read the authority chain before touching source

Read, in this order:

- `AGENTS.md`
- `README.md`
- `docs/DOCUMENTATION.md`
- `HANDOVER.md`
- `skills/greia-os-work/SKILL.md`
- `skills/greia-os-work/BOOT.md`
- `docs/engineering/BOOT_PIPELINE_AGENT_GUIDE.md`
- `docs/adr/0036-unified-system-slot-releases-and-platform-install-media.md`
- `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`
- `docs/INSTALLATION_USB_BOOT_POSTMORTEM.md`
- `docs/reviews/2026-08-20_ACER_INSTALLER_BOOT_REGRESSION.md`
- `docs/reviews/2026-09-27_ACER_AB_GRUB_INSTALLER_PHYSICAL_BOOT_FAILURE.md`
- `docs/agents/GREIA_AGENT_OPERATIONS.md`

The active plan and ADR 0036 are authoritative where older universal-media documents conflict.

## 3. Reconcile the misleading documentation, narrowly

The older `docs/architecture/UNIVERSAL_GREIA_SETUP_MEDIA_ARCHITECTURE.md` still describes the legacy Acer path as GRUB MBR. That conflicts with accepted physical evidence and current ADR 0036/A16.

Do **not** rewrite history. Make a small, explicit current-state correction:

- add a prominent banner near the top saying this older architecture draft is superseded where it conflicts with ADR 0036 / the 2026-09-15 active plan;
- specifically state that the legacy BIOS first stage is now authoritative as:
  `MBR -> active FAT32 -> SYSLINUX -> i386 live kernel/initramfs`;
- preserve UEFI and Pi coexistence on the same universal FAT boot partition;
- do not replace the document wholesale or invent another architecture.

Append a correction to the 2026-09-27 physical-failure review:
- the failed raw A/B GRUB installer was an **intermediate Session-04 engineering artifact**, not the final universal Setup architecture;
- the physical failure does not invalidate the one-image requirement;
- the final one-image design already preserves Syslinux for Acer and uses different first-stage paths for UEFI and Pi.

Verify `HANDOVER.md` and the active plan say the same thing. Keep the dated negative physical result intact.

Commit this documentation reconciliation as one coherent docs commit.

## 4. Do not “fix” the wrong source owner

Current profile facts are intentionally different responsibilities:

```toml
[boot]
installed_adapter / standalone engineering installer details

[setup]
live_boot_adapter = "pc-live-syslinux-v1"
```

Do not simply change every `grub-pc-bios-live` string to Syslinux.

The current standalone `acer-aspire-one-i386-ab` raw image was useful for Session-04 transaction/QEMU work. The **future public universal Setup image** owns the Syslinux removable first stage.

The installed Acer uses GRUB A/B. Preserve that.

## 5. Validate the already-landed safe-writer bug fix, but keep it bounded

Commit `d4bece3188ec497a6fa2e5501c8ccada7d2e4d94` changed `build/write-image.sh` so util-linux 2.39.x flat partition siblings no longer make every partitioned USB look invalid.

Do not build a new testing framework.

At minimum:
- shell syntax check the script;
- inspect the current probe logic;
- if an existing focused media-writer/safety test file exists, add one narrow regression for “whole removable disk + direct partition siblings is accepted; unrelated/mapper sibling is refused”;
- if no such test owner exists, do not create a large harness merely for this. The change can be validated later through the normal raw-media writer path.

Do not block the Acer Syslinux test on this raw-writer fix: the named Acer development procedure uses the proven Syslinux writer.

## 6. Clear the two stale loop devices from the failed physical build

The 2026-09-27 review records two autoclear Greia loops that require reboot:
- `/dev/loop2`
- `/dev/loop34`

Before another image build:

```bash
sudo losetup -a | grep greia || true
```

If either recorded stale loop still exists, reboot Orbiter once. After reboot:

```bash
sudo losetup -a | grep greia || true
findmnt | grep -E 'greia|PIP_ROOT|greia-slots' || true
```

Require no stale Greia loops/mounts.

Do not use `losetup -D`.
Do not delete a backing file while its loop is attached.
Do not use host-wide recursive unmounts.

## 7. Build and flash the physically proven Acer Syslinux development image

This is a **sanity/physical boot test**, not a product split and not the Session-08 universal image.

The owner will return/attach the same ~8 GB USB. Identify it:

```bash
lsblk -b -d -o NAME,SIZE,MODEL,SERIAL,TRAN,RM,HOTPLUG
```

Expected historical stick:
- model: LaCie iamaKey
- serial: `eca3505216d7d3`
- size: `8086618112` bytes

Do not assume `/dev/sdb`; identify current path.

Unmount only partitions on that exact USB if auto-mounted.

Then use the named, physically proven procedure:

```bash
sudo bash tools/build-and-flash-development-usb.sh   legacy-x86-i686-dev   /dev/sdX
```

Replace `/dev/sdX` with the exact confirmed USB whole-device path.

Do not:
- use the generic raw A/B GRUB image;
- use `sgdisk --zap-all` as an ad-hoc workaround unless the named procedure explicitly requires it;
- modify the Syslinux template for cosmetics;
- add `quiet`, `splash`, `console=null`, `loglevel=0`, or timed panic reboot;
- run another QEMU cycle merely to “certify” this physical Syslinux test.

The named procedure must report:
- source artifact verification PASS;
- final read-only USB verification PASS;
- boot writer = Syslinux/FAT32;
- observable tty1 diagnostics;
- panic policy keeps a failure visible.

Record:
- source HEAD;
- generated image path;
- image SHA-256;
- USB device/model/serial/size;
- final media verification result.

Then stop for owner physical testing.

## 8. Owner physical Acer test — what to ask for

On the reference Acer, record only the last visible stage:

1. Does SYSLINUX appear?
2. Does `Loading /vmlinuz...` appear?
3. Does `Loading /initrd.img...` appear?
4. Does Linux/live-boot print text?
5. Does the early Greia framebuffer appear?
6. Does the graphical language chooser appear?

There should be no timed reboot hiding a failure.

If the language chooser appears, the preserved removable-boot path is re-confirmed. Do not reinterpret that as Session-04 A/B lifecycle closure; it proves only the physical USB first stage/live path.

The same stick may be tried on other **legacy BIOS-capable x86** machines as an extra smoke test, but do not use failure on UEFI-only hardware against this dev image as evidence against the future universal Setup image.

## 9. Resume Session 04 after the physical stick is prepared

Session 04 remains:

```text
fresh A/B install
-> first healthy A acceptance
-> healthy A->B update
-> B commit
-> broken userspace candidate recovery
-> nonboot candidate + reset recovery
-> PERSIST-incompatible candidate refusal before mutation
```

The last deterministic source checkpoint before the hardware-disk interruption:
- all 9 focused suites PASS at core source `c8054717`;
- S03 immutable bundle verified;
- all four Session-04 candidate bundles verified.

Later commits through current main changed documentation and the safe raw-media writer, not the core transaction path.

Use the existing:
- `docs/testing/2026-09-25_SESSION04_POST_GITHUB_REPAIR_ORBITER_VALIDATION.md`
- `docs/testing/2026-09-25_SESSION04_APT_OWNERSHIP_DECISION.md`

The replacement Orbiter disk is healthy and the heavy-I/O prohibition is closed.

## 10. Session-04 exact continuation

Re-verify the immutable S03 bundle before the build:

```text
bundle SHA-256:
6b5cf05f6ad81979fc9bd53c4f1ae1491da024eaf436aabe31e35779f4860a67
```

Use the unchanged four candidate bundles from the prior evidence.

Build a new diagnostic Session-04 installer from current source + unchanged S03 bundle.

Run **fresh install only first**.

Reason: the previous apt refusal preserved an early `SetupAPTPartialDirectory` chown warning but truncated the actual fatal stderr tail. Current source now keeps bounded stderr head + fatal tail.

Do not add `CAP_CHOWN` from the warning.

If fresh install fails:
- preserve exact bounded stderr HEAD;
- preserve exact bounded stderr TAIL;
- record command exit code and actual final fatal line;
- fix the real owner;
- reconsider a fifth capability only if the actual fatal operation proves it necessary.

Current allowed transaction-service capabilities remain exactly:

```text
CAP_SYS_ADMIN
CAP_SYS_CHROOT
CAP_SETUID
CAP_SETGID
```

Keep:
- `NoNewPrivileges=yes`
- `ProtectSystem=strict`

If diagnostic fresh install passes:
1. remove temporary Session-04 diagnostics only;
2. keep permanent entrypoint/capability/refusal/head+tail/cleanup fixes;
3. rebuild a clean installer;
4. rerun fresh install on the clean build;
5. complete the remaining lifecycle legs;
6. run `make verify`;
7. close Session 04 and open Session 05.

## 11. What not to do next

Do not prematurely implement the universal image in Session 04.

The active sequence is:
- Session 04: finish legacy i386 lifecycle;
- Session 05: real amd64 target + UEFI A/B;
- Session 06: ARM64 build substrate + Pi profiles;
- Session 07: Pi live-boot board adapters;
- Session 08: compose the real universal Setup image with all boot paths.

Do not create:
- an Acer-only public installer;
- a Pi-only public installer;
- a second installer application;
- GRUB/U-Boot on Pi for symmetry;
- a new gate framework.

## 12. Final report from this local-agent run

Return:

```text
SOURCE_HEAD:
<sha>

DOC RECONCILIATION:
PASS/FAIL
<commit>

SAFE WRITER:
current fix present yes/no
focused validation <what actually ran>

STALE GREIA LOOPS BEFORE:
<none/list>

STALE GREIA LOOPS AFTER:
<none/list>

ACER SYSINUX DEV BUILD:
PASS/FAIL

DEV IMAGE:
<path>
<SHA-256>

USB:
<device>
<model>
<serial>
<size>

FINAL USB VERIFICATION:
PASS/FAIL

READY FOR OWNER ACER TEST:
yes/no

SESSION04 SOFTWARE STATUS:
OPEN

SESSION04 NEXT SOFTWARE STEP:
diagnostic installer rebuild + fresh-install-only fatal-tail run

CAP_CHOWN:
NOT AUTHORIZED / proven required with exact evidence

TREE:
clean/dirty

HEAD == ORIGIN/MAIN:
yes/no
```
