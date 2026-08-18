# Greia OS Installation & Boot Issues Log

**Status:** accepted engineering record, reconciled with build tree  
**Date:** 2026-08-18  
**Audience:** platform developers, install/boot engineers, reviewers, agents  
**Scope:** failures encountered while bringing the Greia installer and installed OS up on legacy physical hardware, plus the hardware-independent engineering lessons that now protect future builds.

> The Acer Aspire One used during this tranche was the machine that exposed the
> defects. It is **not** the scope of the fixes. The rules below are written so a
> clean Greia build made on different hardware does not rely on the build host
> resembling its eventual target.

---

## 1. Installer `BOOT FAILED` after probing the live medium

**Symptom:** the Greia live installer mounted and unmounted the removable medium,
then `live-boot` reported that it could not find a medium containing a live file
system.

**Root cause:** `live-boot` identity matching requires the initramfs media ID to
match `.disk/live-uuid` on the removable medium. The hand-assembled medium had
the kernel/initrd/squashfs but not that identity marker, so it was probed and
rejected.

**Fix / invariant:**

- the official media builder creates `.disk/live-uuid` from the same generated
  ID passed to the initramfs as `greia.live_media_id`;
- the media identity, live filesystem and installation payload are treated as
  one build product;
- `tests/test_installation_hardware_regressions.py` locks the marker and payload
  paths together.

**Hardware note:** the tested Acer BIOS would not boot from its SD reader and did
not execute the tested USB stick's GRUB MBR reliably. A clean FAT32 active
partition with syslinux booted successfully. That is a firmware/media-adapter
compatibility observation, not a reason to make syslinux universal policy for
all Greia hardware.

---

## 2. Installed system grey-screened and rebooted in a loop

**Symptom:** GRUB loaded Greia, the screen went grey, and the machine rebooted
repeatedly.

**Root cause:** the regenerated installed initramfs did not contain the generic
SATA/AHCI root-disk stack (`ahci`, `libata`, `sd_mod`). The image was assembled
in a chroot/VM that could not probe the eventual laptop's storage controller, so
host-derived dependency selection was not valid target-hardware authority.
With no root disk, the kernel could not mount the filesystem; the appliance
kernel command line intentionally hid the panic and rebooted.

**Fix / invariant:** both target and live image inputs now carry all three
hardware-independent safeguards:

1. `MODULES=most`;
2. explicit `/etc/initramfs-tools/modules` entries for `ahci`, `libata`,
   `sd_mod`;
3. executable `greia-storage-modules` initramfs hooks that call
   `manual_add_modules` for those drivers.

The regression suite requires the same policy in both live and target overlays.

**Important correction to the earlier log:** commit `de6299e` added installed
GRUB/root-UUID/kernel/initrd **boot-config verification**; it did not inspect the
contents of the generated initramfs. The new storage-module policy prevents the
specific host-probing omission structurally. Generated-image acceptance should
still inspect the produced initramfs as an artifact-level check.

**General lesson:** never let the hardware visible to the build VM/chroot decide
whether a boot-critical target driver exists. Compatibility-profile policy must
own that decision.

---

## 3. Installer stalled at “Adding support for this computer”

**Symptom:** installer progress stopped; a child `apt-get` process was in stopped
state `T` and could not make progress.

**Root cause:** the graphical installer service had `StandardInput=tty` on tty1.
When X became the foreground process group, installer children still inherited
the terminal as stdin. A child that attempted to read from it received
**SIGTTIN** because it belonged to a background process group. The same class of
failure later affected other command-line helpers.

**Fix / invariant:**

- graphical installer and launcher units use `StandardInput=null`;
- installer subprocess execution uses `stdin=subprocess.DEVNULL`;
- the hardware regression suite forbids reintroducing TTY stdin to these GUI
  services.

**General lesson:** a VT used to own a display session is not implicit stdin for
graphical application children.

---

## 4. “installation payload not found”

**Symptom:** the live installer itself started but could not find the target OS
payload.

**Root cause:** the hand-built medium contained the files needed to boot the
live environment but omitted `payload/pip-rootfs.squashfs`, its digest and
`target-image-profile.json`.

**Fix / invariant:** the official media contract emits and verifies the complete
payload set with the live boot files. Custom-media runbooks/tools must copy the
contract as a whole, never a remembered subset.

---

## 5. SSH developer bootstrap diverged from the security architecture

**Observed problem:** remote developer access was unreliable during hardware
work, and older builder paths compensated by writing a known `greia/greia`
password and permissive root/password SSH configuration. Separately, image
personalization removes host keys so cloned machines do not share SSH identity.

**Root cause:** two concepts became conflated:

- **normal/release images:** SSH is disabled; host keys are intentionally absent
  until a future parent-owned enablement path exists;
- **developer images:** the supported provisioning architecture is key-only
  `greiaadmin`, root/password SSH disabled, with per-machine host keys generated
  on the actual device.

The stale builder convenience branch no longer matches that architecture.

**Current fix / invariant:**

- both target and live installer overlays contain
  `00-greia-security-floor.conf`;
- password and keyboard-interactive authentication are disabled;
- `AuthenticationMethods publickey` is required;
- root login is disabled;
- historical `root` and `greia` bootstrap identities are explicitly denied;
- target first boot locks any historical bootstrap passwords;
- secure developer provisioning continues to use `greiaadmin` authorized keys.

Because the security-floor drop-in sorts before profile convenience drop-ins,
a raw/interrupted build cannot re-enable password/root remote access by later
configuration.

**Remaining cleanup:** remove the obsolete password-writing branches from the
large builders themselves. They are now non-authoritative dead code, but should
not remain indefinitely.

---

## 6. `greia-launcher.service` failed with status `226/NAMESPACE`

**Symptom:** launcher failed before its pre-start helper with a missing
`/run/greia-os` path.

**Root cause:** `/run` is a fresh tmpfs every boot, and systemd constructs a
service namespace before `ExecStartPre`. Creating a namespace-required path from
`ExecStartPre` is therefore too late.

**Fix / invariant:** `greia-launcher.service` now uses:

```ini
RuntimeDirectory=greia-os
RuntimeDirectoryMode=0755
```

so systemd creates the path before namespace/service setup.

**General lesson:** service-owned volatile paths required during unit setup must
be declared to systemd, not lazily created by a command that runs after setup.

---

## 7. Xorg refused to start: “Only console users are allowed”

**Symptom:** Xorg.wrap rejected the launcher service and Xorg processes died.

**Root cause:** `allowed_users=console` assumes a conventional console/login
session. Greia's current provisional Xorg backend runs from a systemd-owned
appliance session and does not satisfy that desktop heuristic.

**Fix / invariant:** the current compatibility backend explicitly uses:

```text
allowed_users=anybody
needs_root_rights=yes
```

This is authority granted to the platform-owned X server, not to Activities.
Activity isolation remains in the supervisor/runtime boundary.

---

## 8. Xorg was blocked by launcher service namespace hardening

**Symptom:** even after the wrapper change, Xorg did not produce a fresh usable
session/log and the launcher restarted.

**Root cause:** desktop-daemon-style hardening (`ProtectSystem=strict`,
`ProtectHome`, `PrivateTmp` and narrow path namespaces) prevented the current
platform-owned Xorg process from opening the VT, DRM/input devices and normal
runtime/log paths.

**Fix / invariant:** those mount-namespace directives were removed from the
**current provisional Xorg-owning launcher service**. The regression suite now
forbids silently restoring them while this backend owns the display session.

This is **not** a blanket rejection of systemd hardening. A future R7 backend
must define its exact path/device contract, then apply and physically prove the
hardening compatible with that contract. Activity sandboxing is independent and
remains enforced.

---

## 9. Touchpad pointer appeared frozen

**Symptom:** launcher rendered a pointer but it did not move; Xorg/libinput
reported failure against a legacy `/dev/input/mouse*` node.

**Root cause:** one physical touchpad was represented both by a modern
`/dev/input/event*` device and a legacy mouse compatibility node. The generic
pointer InputClass matched the compatibility node and attempted to treat it as
an independent libinput device.

**Fix / invariant:** Xorg input defaults ignore `/dev/input/mouse*` before the
real touchpad/pointer classes are applied. This is deliberately based on Linux
input namespace semantics rather than a Synaptics/Acer model-name exception.

---

## 10. Activities failed to launch inside Bubblewrap

**Symptom:** Activity activation returned to the launcher; Bubblewrap reported
missing/permission-denied source or destination paths.

**Root cause:** three sandbox-topology assumptions were wrong:

1. bind destinations under the read-only root were not created first;
2. `/run` was read-only although Activity-private bind targets lived beneath it;
3. user-namespace remapping removed access needed to traverse platform-owned
   group-accessible profile sources.

**Fix / invariant:**

- Activity sandbox creates a private `--tmpfs /run`;
- required bind destinations are created with `--dir` before binds;
- the broken `--unshare-user`/`--disable-userns` assumptions were removed;
- PID/network/UTS isolation and the read-only root remain;
- the regression suite locks this mount topology.

**General lesson:** sandbox policy is both *what is inaccessible* and *how the
private filesystem is constructed*. Mount targets must exist inside that
filesystem before authority is narrowed.

---

## 11. Arrow/Enter navigation was dead in the kiosk launcher

**Symptom:** pointer input worked but keyboard navigation did not.

**Root cause:** Greia launches the current Xorg compatibility session without a
window manager. SDL window creation alone did not establish X keyboard input
focus.

**Fix / invariant:** the X11 compatibility path explicitly calls
`XSetInputFocus` for the launcher window after creation. The regression suite
requires that handoff to remain present while this backend is active.

A future R7 backend must provide the same semantic guarantee through its own
focus/session implementation.

---

## 12. Activity startup felt frozen

**Symptom:** the delay between activation and Activity presentation looked like a
hung launcher; early feedback was too weak.

**First fix:** the launcher gained an immediate full-screen “Starting…” overlay
and spinner before the expensive startup path.

**2026-08-18 refinement:** the selected tile now performs a short bounded
squiggle/bounce flourish before the existing start overlay and authoritative
launch path. The animation is presentation-only and cannot affect permissions,
package trust or lifecycle authority.

See `docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md`.

---

## Regression rule established by this hardware tranche

A real-hardware fix is not complete until all four conditions hold:

1. the physical machine works;
2. the authoritative build source contains the fix;
3. a hardware-independent test/invariant prevents accidental reversal;
4. documentation records the root-cause class, not just the machine-specific
   symptom.

The August 18 repository review found several cases where the hardware had been
manually fixed and the issue log described the fix, but the build overlay still
contained the old Xorg/systemd/input configuration. Those mismatches were
corrected during the review and are now explicitly regression-locked.

For the complete cross-cutting review and remaining risks, see
`docs/reviews/2026-08-18_REAL_HARDWARE_INSTALLATION_AND_LAUNCHER_REVIEW.md`.

---

## Key commits from the physical-hardware tranche

| Commit | Description |
|---|---|
| `b1c9669` | launcher: full-screen launch overlay and X input focus for kiosk keyboard |
| `51c7592` | supervisor: fix Bubblewrap sandbox mount failures breaking Activity launch |
| `de6299e` | installer: verify installed boot config root UUID and kernel/initrd before done |
| `665909d` | installer: do not give the VT as stdin to the GUI service |
| `9654d01` | installer: detach subprocess stdin to prevent SIGTTIN stall |
| `2940be1` | installer: tolerate legacy hardware defaults and guarantee frame throttle |
| `1b11c79` | installer: physical-key layout probes instead of active-layout assumptions |

Subsequent 2026-08-18 review commits persist the missing Xorg/runtime/input
build fixes, force the generic storage stack into live/target initramfs inputs,
add hardware-independent regression locks, add the SSH security floor, and
introduce the richer launcher/Activity-package foundation. The repository
history is authoritative for the exact commit IDs of that follow-up tranche.
