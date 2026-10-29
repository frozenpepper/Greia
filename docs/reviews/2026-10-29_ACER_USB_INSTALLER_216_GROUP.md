# Acer USB installer first-boot failure: systemd 216/GROUP

Date: 2026-10-29 · Evidence class: **physical Acer console photograph + source inspection**.
Status: **corrected image built and QEMU default-service acceptance PASS; LaCie reflashed with byte-identical readback; physical Acer boot PENDING.** The original source-only repair record is preserved below.

## Evidence

The LaCie installer USB flashed from SHA-256
`b81279afe4c8d72bb458670efda95c6a422deddbceef69051a5e6da309c2bd80`
matched the candidate image byte-for-byte on readback (report:
[2026-10-28_FIRST_PUBLIC_RELEASE_PREPARATION_RESULT.md](2026-10-28_FIRST_PUBLIC_RELEASE_PREPARATION_RESULT.md)).
On the physical Acer Aspire One it remained at the branded framebuffer cover.
The owner used the GRUB diagnostic path and supplied a photograph with:

```text
greia-installer.service: Failed to determine supplementary groups: No such process
greia-installer.service: Failed at step GROUP spawning /usr/local/lib/greia-os/prepare-installer-vt: No such process
greia-installer.service: Control process exited, code=exited, status=216/GROUP
greia-installer.service: Failed with result 'exit-code'
...
Start request repeated too quickly
```

These are **systemd identity-resolution errors occurring before ExecStartPre**,
not graphical framebuffer, Xorg, payload checksum, grub, or disk/installer
transaction failures. No installed-device write is established by this
photograph.

## Source root cause

The live image ships
`build/installer-overlay/etc/systemd/system/greia-installer.service` with:

```ini
User=nobody
Group=nogroup
SupplementaryGroups=video input tty netdev audio
```

Shared image composition only ran `compose_create_users_groups` for the
`target` role. That target-only function explicitly creates `netdev`, but
the `live-installer` role has never created the group. Debian minbase plus the
installer package set **does not guarantee** that `netdev` (or every other
requested supplemental group) is present. The exact missing group in the
flashed squashfs has not yet been independently inspected; `netdev` is the
specific proven source omission. Systemd refuses the unit if **any** named
group is missing.

The prior QEMU installer acceptance used the shipped installer transaction
socket via a control harness. That proves the install transaction, but it did
not demonstrate that the **systemd graphical installer UI service** launched
under its declared identity. Accordingly it did not catch this boot blocker.

## Repair in source

- `build/lib/compose.sh`: `compose_create_live_installer_groups` reads the
  actual service's `SupplementaryGroups=`, validates names and uses
  `groupadd --system --force` in the **live** root after package install
  and before service enablement. The target's separate user/group creation
  is unchanged.
- `build/package-sets/installer-base.txt`: explicitly includes `passwd`
  to provide `/usr/sbin/groupadd`; no dependency on accidental minbase
  contents.
- `build/lib/verify-composed-root.sh`: checks live `nobody` identity,
  primary group and **every** supplemental group against the composed
  image's `/etc/passwd` and `/etc/group`. A missing group now fails
  verification before media flash.
- `tests/test_live_installer_groups.py`: local, unprivileged regression
  reproducing the missing-group creation scenario and absence of groupadd.

No actual image build, source test, new USB flash, physical boot or physical
install was performed by this GitHub-only repair. In particular, the old USB
is **still broken**.

## Required acceptance before declaring fixed

1. On the Linux build host, run the focused regression, then normal source
   verification and a fresh build from a pinned corrected `main` SHA.
2. Before any media write, **inspect the live filesystem.squashfs from the
   exact new image** and confirm `nobody`, `nogroup` and every name from
   `SupplementaryGroups=` exist in its actual databases. Confirm the image
   verification command passes. A successful `groupadd` during composition
   is not by itself the final artifact proof.
3. Boot the **actual new installer image** in QEMU with its normal default
   `greia-installer.service` (not only the installer socket/harness) and
   observe `systemctl is-active greia-installer.service` plus an actual
   interactive installer screen. Retain unit journal and relevant screenshot.
4. Reflash the **specifically re-authorized, positively identified** LaCie
   removable media, verify full image-byte readback, boot on physical Acer
   and observe the actual graphical installer screen before attempting any
   internal-disk installation.
5. Report the exact source SHA, image SHA, disk identity, group database,
   unit journal and outcome. Do not claim release readiness before this
   physical behavior passes.

A physical Acer installation would be a separate destructive action requiring
explicit owner approval; booting an installer is not authority to overwrite the
internal disk.

## Corrected-image acceptance (2026-10-29)

**Source and gates.** Current `main` `4d2b65f78` plus two test-only fixture
repairs needed because the new verifier checks exposed stale fixtures.
Focused group/verifier regressions passed, then `make verify` was **GREEN**:
6,016 tests OK, 5 skipped. The installer was rebuilt from this tree with the
already-validated unchanged target bundle
`2572bf0829152c24aaf0e82f897b9ba651f871f30c4c9ad5d4f9349729dab3d0`;
the live-installer repair is installer-side only.

**Exact image.** Profile `acer-aspire-one-i386-ab`, image
`d12568abd9c60a6d23f75b7afe0204f53bf5567ff37ae95bf799fd91b7b0cabd`
(2,270,167,040 bytes), live media ID
`8ff1a118-b6a5-48d1-a07e-e531141e5737`, quiet boot, A/B bundle builder
validation PASS. Output directory:
`/home/orb/Greia-Images/installer-2026-10-29/`.

**Actual live squashfs inspection.** `unsquashfs` against the image's own
`live/filesystem.squashfs` confirmed:

```text
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
nogroup:x:65534:
video:x:44:
input:x:101:
tty:x:5:
netdev:x:996:
audio:x:29:
```

The shipped unit still declares `User=nobody`, `Group=nogroup`,
`SupplementaryGroups=video input tty netdev audio`; `usr/sbin/groupadd`
(passwd package) and the enabled `graphical.target.wants` link are present.

**Default-service QEMU boot.** The actual image booted under QEMU 8.2.2/KVM,
i386, `-cpu n270`, 768 MiB with snapshot media and reached the interactive
installer language screen. A disposable observation-only clone (only a test
unit appended; shipped service and group database unchanged) recorded:

```text
systemctl is-active greia-installer.service  -> active
systemctl is-enabled greia-installer.service -> enabled
Active: active (running)
ExecStartPre=/usr/local/lib/greia-os/prepare-installer-vt (status=0/SUCCESS)
Main PID: xinit ... greia-installer-client
```

Evidence: [QEMU acceptance](acer/2026-10-29_INSTALLER_216_GROUP_QEMU/README.md).

**LaCie reflash.** Positively identified `/dev/sdc` (LaCie `iamaKey`, serial
`eca3505216d7d3`, 7.5 GiB, removable whole disk), owner-authorized. Raw write
followed by a full first-2,270,167,040-byte readback matched the image
SHA-256 exactly. The media exposes `GREIA_EFI` (64 MiB vfat) and
`PIP_INSTALL` (2.1 GiB ext4); the bundle on the media re-read as
`2572bf08…`, and the flashed squashfs re-checked the same group database.

**Remaining.** Physical Acer boot from this USB and observation of the
graphical installer screen are still required. Any internal-disk installation
remains a separate destructive action requiring explicit owner approval.

**Later rebuild (same day):** owner requested a rebuild after the USB
failure-logging commits. Image
`b853330f624d816077c1149aa715e03aa2886e3571bbb834bb3e868d6072a436`
(2,270,167,040 bytes, source `9dd3625fb`, live media ID
`0af73bfd-a236-4140-a837-6073212f3438`) retains the group fix, adds
`install_diagnostics.py` and the simplified unconfined root workers, and was
flashed to the same LaCie with byte-identical readback. `make verify`:
6,012 tests OK, 5 skipped. Physical Acer boot remains PENDING.
