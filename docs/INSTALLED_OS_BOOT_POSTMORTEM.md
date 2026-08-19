# Greia Installed OS Boot — Full Post-Mortem

**Status:** accepted engineering record  
**Date:** 2026-08-18  
**Audience:** install/boot engineers, release engineering, agents  
**Scope:** the complete, chronological account of why a freshly installed Greia
OS would not boot on the reference Acer Aspire One (grey screen, silent reboot
loop), every diagnostic that was used to isolate the cause, and the exact fixes
that finally made the installed system boot to the launcher. Durable rules are
in `INSTALLATION_ISSUES_LOG.md`; this document preserves the *why* and the
*how* so nobody re-walks this path.

---

## 1. The symptom

After a **successful** install (installer reached the "All done" screen and
showed the recovery code), removing the USB key and powering on produced:

1. GRUB loaded (the "Greia OS" menuentry was reachable);
2. selecting it → the screen went **grey**;
3. after a few seconds → the machine **rebooted** into the same loop, endlessly.

The Acer's Wi-Fi never came up, so there was no SSH, no way to look at logs,
and no serial console. The only observable signals were: GRUB works, the kernel
starts (or not), and the machine reboots.

The reboot loop was **intentional behavior hiding the bug**: the appliance
kernel command line includes `panic=5 console=null quiet splash`, so any kernel
panic is invisible (black/grey screen) and the machine auto-reboots five seconds
later. We were flying blind by design.

---

## 2. What we knew was correct (checked first, ruled out)

Before finding the real cause, we verified and excluded:

| Area | Check | Result |
|---|---|---|
| GRUB installed | MBR of `/dev/sda` starts with `eb 63 90` (valid GRUB boot code) | OK |
| GRUB config | `menuentry 'Greia OS'` has `search --fs-uuid` + `root=UUID=` matching the disk | OK |
| UUID consistency | `grub.cfg`, `/etc/fstab`, `/etc/greia-os/root-filesystem-uuid` all reference the same UUID, equal to `blkid /dev/sda1` | OK |
| Kernel/initrd links | `/vmlinuz`, `/initrd.img` symlinks resolve to real files in `/boot` | OK |
| Storage drivers in initramfs | `ahci.ko`, `ata_piix.ko`, `libata.ko`, `sd_mod.ko`, `ext4.ko` all present in the initramfs | OK (they were present!) |
| Initramfs scripts | `/scripts/local` (root mount logic), `/init`, `resolve_device` via `blkid` | OK |

The disk, GRUB, and initramfs *appeared* complete. The UUIDs matched. Yet it
would not boot. This is why the problem took so long: **every static check
passed**, and the failure was in the *runtime* behavior of the initramfs.

---

## 3. First diagnostic: `break=top` / `break=premount`

`break=top` (or `break=premount`) is an initramfs-tools debug parameter that
drops to a shell inside the initramfs before/around root mount.

**What we learned:**
- Editing the GRUB menuentry requires the recovery password
  (`greia-recovery` user). The user had it.
- The initramfs shell **worked**: `blkid`, `cat /proc/cmdline`, `ls /dev/sd*`
  all ran. So the kernel, initramfs, and console were healthy.
- `blkid` returned **nothing** and `ls /dev/sd*` returned
  **"No such file or directory"**.

**Conclusion:** the internal SATA disk was **invisible inside the initramfs**.
No `/dev/sda` at all. The kernel had not attached the disk.

---

## 4. Second diagnostic: what modules are loaded?

Inside the initramfs shell:

```
cat /proc/modules
```

Output contained USB host controllers (`xhci_hcd`, `uhci_hcd`, `ohci_hcd`,
`ehci_pci`) but **no** `ahci`, `libata`, or `sd_mod`.

```
find / -name "ahci.ko" 2>/dev/null
```

Returned **nothing** — the module file was not even *present* in the installed
initramfs, despite the earlier check on the *payload's* initramfs showing it
was there.

**Key distinction discovered:** the initramfs that ships inside the
`pip-rootfs.squashfs` payload (and that we had inspected earlier) contained the
drivers. But during install, `update-initramfs -u` **regenerates** the initramfs
inside the target chroot, and that regenerated one did **not** contain them.

---

## 5. Root cause: host-derived module selection in a chroot

The installed target's initramfs is built by running `update-initramfs` in the
**target chroot** during install. initramfs-tools decides which modules to
include based on:

- `/etc/initramfs-tools/initramfs.conf` → `MODULES=` setting;
- the modules actually loadable/detected in that environment.

The Greia overlay shipped `MODULES=most` via
`/etc/initramfs-tools/conf.d/greia-hardware` and `greia-framebuffer`. But those
files were **not present in the installed target root**. The target had no
`/etc/initramfs-tools/` at all in the tested image. So `update-initramfs` fell
back to its default `MODULES=dep` (dependency-based) mode.

In `dep` mode, initramfs-tools scans the modules that are currently loadable in
the environment it runs in — i.e. the **chroot**, which has no Acer SATA
controller and no loaded `ahci` — and builds a dependency closure that excludes
the storage drivers. The regenerated initramfs therefore could not bring up the
disk, `/dev/sda` never appeared, root never mounted, the kernel panicked
invisibly, and `panic=5` rebooted the machine.

**Why the earlier static check misled us:** we inspected the initramfs that
ships *inside the payload squashfs* (which is built on the build host with the
right config). We did not inspect the *regenerated* initramfs written to the
installed `/boot`. The regenerated one is the one that boots.

**Why the live installer booted fine:** the live system boots from the initramfs
on the removable medium, which was built with `MODULES=most` and has all
drivers. Only the installed target's regenerated initramfs was affected.

---

## 6. Fix 1: restore the initramfs-tools policy and rebuild

From the live installer (reachable over SSH with Wi-Fi up), on the installed
target:

```
mkdir -p /etc/initramfs-tools/conf.d
cp /etc/initramfs-tools/initramfs.conf <target>/etc/initramfs-tools/
cp /etc/initramfs-tools/conf.d/greia-hardware <target>/etc/initramfs-tools/conf.d/
printf 'ahci\nlibata\nsd_mod\n' > <target>/etc/initramfs-tools/modules
```

then, with `/dev`, `/proc`, `/sys` bind-mounted into the target:

```
chroot <target> update-initramfs -u -k all
```

The regenerated initramfs grew to include `ahci.ko`, `libata.ko`, `sd_mod.ko`
(verified by extracting and listing modules).

**Result:** the machine booted past the grey screen for the first time — it got
to systemd and started services. The disk, root mount, and boot were fixed.

**Structural lesson (later hardened in the repo):** never let the hardware
visible to the build chroot decide whether a boot-critical target driver exists,
and never hardcode x86 module names into a shared cross-architecture overlay.
The fix implemented in the repo uses **target-kernel-aware policy**:
`MODULES=most` + an executable `greia-storage-modules` hook that runs
`modinfo -k "$version"` against the *target* kernel and calls
`manual_add_modules` when that kernel provides `ahci`/`libata`/`sd_mod`. See
`INSTALLATION_ISSUES_LOG.md` §2.

---

## 7. After the boot fix: a second wall of service failures

Once the system booted, systemd showed a cascade of failures:

- `ssh.service` failed;
- `greia-launcher.service` failed (restarting in a loop);
- (others not visible, console scrolled).

Each was a separate defect, found and fixed in order:

---

## 8. Issue A — `ssh.service` fails: no host keys

**Symptom:** `ssh.service` failed on boot; no SSH.

**Root cause:** the installer's `_personalize_target` deliberately removes SSH
host keys so they are regenerated on first boot. On this image the regeneration
did not happen (the `first-boot` service comment says keys are deferred until a
parent enables SSH; the dev image expected them earlier), so sshd could not
start.

**Fix:** generate host keys in the installed target:

```
chroot <target> dpkg-reconfigure openssh-server
```

(or `ssh-keygen -A`). Verify `/etc/ssh/ssh_host_*` exist. Then `ssh.service`
starts and the Acer is reachable remotely — which is what made every later
diagnostic possible.

---

## 9. Issue B — launcher fails with `status 226/NAMESPACE`

**Symptom:**

```
greia-launcher.service: Failed at step NAMESPACE spawning
/usr/local/lib/greia-os/prepare-launcher-vt: No such file or directory
Failed to set up mount namespacing: /run/systemd/unit-root/run/greia-os: No such file or directory
```

**Root cause:** the service sandbox lists `ReadWritePaths=/run/greia-os` with
`ProtectSystem=strict`. systemd builds the mount namespace **before**
`ExecStartPre` runs, and it requires every `ReadWritePaths` target to already
exist. `/run` is tmpfs and wiped each boot, so `/run/greia-os` did not exist
yet → namespace setup failed → service failed at the ExecStartPre step.

**Fix:** add `RuntimeDirectory=greia-os` to the service. systemd then creates
`/run/greia-os` itself before the namespace is constructed.

**Lesson:** any systemd unit that sandboxes with `ReadWritePaths` under `/run`
must declare the runtime directories with `RuntimeDirectory=`, otherwise fresh
boots fail before the unit's own setup scripts run.

---

## 10. Issue C — Xorg refuses to start: "Only console users are allowed"

**Symptom:** launcher runs, but no X; journal shows

```
/usr/lib/xorg/Xorg.wrap: Only console users are allowed to run the X server
```

and `[Xorg] <defunct>` zombie processes.

**Root cause:** `Xwrapper.config` shipped with `allowed_users=console`. Xorg's
suid wrapper checks whether the invoking user has a **logind session on the
physical console**. The launcher service runs under systemd with a PAM session
that is *not* registered with logind as a console session (systemd service
sessions are not `logind` seats), so the wrapper rejects it.

**Fix:** for the appliance, set in `/etc/X11/Xwrapper.config`:

```
allowed_users=anybody
needs_root_rights=yes
```

The Acer is a single-purpose kiosk; the launcher service is the only X user.

---

## 11. Issue D — Xorg blocked by the launcher service sandbox

**Symptom:** even after the wrapper fix, Xorg never started; the Xorg log was
stale (not being written), and the launcher kept restarting.

**Root cause:** the launcher unit still had `ProtectSystem=strict`,
`PrivateTmp=yes`, `ProtectHome=yes`. A display server cannot run under that
sandbox: it needs to open `/dev/tty1` (VT), `/dev/input/*` (input), `/dev/dri/*`
(DRM), write its log to `/var/log`, and create sockets under `/tmp`
(`/tmp/.X11-unix`). The namespace blocked these, so Xorg could not initialize —
and with `PrivateTmp=yes` it could not even write a log, which is why the log
was stale.

**Fix:** remove the heavy sandbox from `greia-launcher.service` and run it
display-manager style (`User=root`, `StandardInput=null`). This immediately
fixed both Xorg startup and the restart loop.

**Lesson:** do not apply container-style sandboxes to a process that hosts an
X server. The sandbox options that look good for a daemon are fatal for a
display session.

---

## 12. Issue E — frozen touchpad pointer

**Symptom:** the launcher UI rendered, the pointer drew, but could not move.

**Root cause (from `Xorg.0.log`):**

```
libinput: SynPS/2 Synaptics TouchPad: Failed to create a device for /dev/input/mouse0
(EE) PreInit returned 2 for "SynPS/2 Synaptics TouchPad"
```

The touchpad is exposed by udev as **two** devices: the real
`/dev/input/event6` (which libinput handles correctly) and the legacy
`/dev/input/mouse0`. The shipped input class `90-greia-input-defaults.conf`
used `MatchIsPointer` which also matched `mouse0`, and libinput cannot open the
legacy device, so the whole touchpad device failed.

**Fix:** add an InputClass that ignores the legacy device:

```
Section "InputClass"
    Identifier "Ignore legacy mouse0"
    MatchDevicePath "/dev/input/mouse*"
    Option "Ignore" "true"
EndSection
```

and scope the pointer libinput rule to `/dev/input/event*`. The touchpad then
worked.

**Lesson:** legacy `mouse*` device nodes are duplicates of `event*` nodes on
input-classification setups; an Xorg InputClass that matches broadly
(`MatchIsPointer`) can break devices by double-opening them.

---

## 13. Issue F — Activity launch crashes inside Bubblewrap

**Symptom:** clicking an Activity did nothing (silent return to launcher).
Instrumentation showed `ActivityExitReason.CRASH` and stderr:

```
bwrap: Can't find source path
/var/lib/greia-profiles/data/<profile>/activities/org.greia.<id>: Permission denied
```

**Root cause (three stacked problems):**

1. The sandbox bound the per-session storage/event socket roots to
   `/run/greia-storage` and `/run/greia-events`, but those targets did not exist
   under the read-only `--ro-bind / /` root, so bwrap could not create the
   mount points.
2. `/run` is read-only in the sandbox; bind targets under it could not be
   created at all.
3. `--unshare-user`/`--disable-userns` remapped the process into a user
   namespace whose root **loses access to `greiakid:pipprofiles` group-owned
   profile directories**, so bwrap could not traverse the activity-data source
   path.

**Fix (in `greia_launcher/supervisor.py`):**
- add `--dir` before the storage/event `--ro-bind` targets;
- add `--tmpfs /run` so mount points under `/run` can be created;
- remove `--unshare-user`/`--disable-userns` (PID/network/UTS isolation and
  read-only root remain);
- ensure profile parent directories are traversable (o+x) for the sandbox
  process.

**Lesson:** bwrap `--unshare-user` is not free. If the host paths bound into
the sandbox are group-owned by a group the user-namespace root is not mapped
into, source traversal fails with "Permission denied" — which looks nothing
like a sandbox bug. Test the full bwrap command line with the real source path.

---

## 14. Issue G — keyboard navigation dead in the kiosk

**Symptom:** pointer worked, arrow keys and Enter did nothing.

**Root cause:** the launcher runs Xorg with **no window manager**. Without a
WM, X delivers keyboard events only to the input-focused window; there was
none (`XGetInputFocus` returned `0x0`).

**Fix:** after creating the SDL window, set X input focus to it directly via
`XSetInputFocus` (ctypes call `_set_x11_input_focus` in `greia_launcher/main.py`).

**Lesson:** a single-window X kiosk without a window manager must explicitly
grab input focus; SDL does not do it for you.

---

## 15. Issue H — activity startup felt frozen

**Symptom:** long delay between clicking and the activity appearing, screen
frozen.

**Root cause:** `_launch_selected` pumped SDL events in a tight loop without
repainting while the sandbox + python runtime started.

**Fix:** draw an immediate full-screen "Starting…" overlay (panel + pulsing
spinner) and keep repainting it until the activity is ready.

---

## 16. The diagnostic toolbox that made all of this possible

These were the techniques that actually produced answers. They are worth
preserving:

1. **Make the boot visible.** The appliance hides panics by design
   (`console=null panic=5 quiet splash`). For debugging, temporarily replace
   them: `console=tty1`, remove `quiet splash`, remove `panic=5`. This converts
   a silent grey screen into readable output.
2. **`break=top` / `break=premount`** — initramfs-tools debug shell. Gives a
   shell *inside* the initramfs: `blkid`, `ls /dev/sd*`, `cat /proc/modules`,
   `find / -name '*.ko'`. This is how we proved the disk was invisible and the
   driver missing.
3. **`init=/bin/bash`** — kernel parameter to get a root shell after root
   mount. Caveat: if root cannot mount, it prints
   "No such file or directory" for `/bin/bash`, which itself tells you root
   did not mount.
4. **Persistent journald** (`Storage=persistent` in
   `/etc/systemd/journald.conf`) — so service failures survive reboots and can
   be read from the next live-boot session or SSH.
5. **Instrument the running code.** Patching `_launch_selected` to append the
   `ActivityResult` to a log file, and patching the runtime adapter to capture
   the child's stderr, turned "clicking does nothing" into a concrete
   `bwrap: Permission denied` line.
6. **Check both initramfs copies.** The payload-shipped initramfs and the
   install-regenerated one are different artifacts; verify the one that boots.
7. **Verify with the real hardware.** QEMU validated images and bootloaders but
   could not reproduce the firmware's refusal to execute GRUB's MBR or the
   missing-driver boot loop (the chroot had no Acer hardware).

---

## 17. Durable rules

1. **The initramfs that boots is the regenerated one, not the shipped one.**
   Always inspect `/boot/initrd.img-*` on the *installed* target, and make the
   build policy target-kernel-aware so regeneration cannot drop boot-critical
   drivers.
2. **Do not let build-host/chroot hardware be the authority for target driver
   selection.** Use `MODULES=most` + target-kernel module inspection
   (`modinfo -k`), not `MODULES=dep` in an unrelated chroot.
3. **GUI service units must not own the VT as stdin and must not be sandboxed
   like daemons.** `StandardInput=null`, `RuntimeDirectory=` for `/run` paths,
   and no `ProtectSystem=strict`/`PrivateTmp` on the X server host process.
4. **The Xorg suid wrapper needs a console session; a kiosk needs
   `allowed_users=anybody`** and an explicit input-focus grab when no WM runs.
5. **InputClass rules must not double-open legacy `mouse*` devices.**
6. **Bubblewrap user namespaces break on group-owned host paths; verify the
   full sandbox command against the real paths.**
7. **Turn invisible failures into visible ones first** (`console=tty1`,
   remove `panic=5`, persistent journald, stderr capture) before debugging.

---

## 18. Relationship to the other post-mortem

The USB boot post-mortem (`INSTALLATION_USB_BOOT_POSTMORTEM.md`) covers how the
installer medium boots. This document covers what happens after install. They
share one theme: **the reference Acer is unforgiving, and everything must be
verified on the real machine** — bootloader execution, initramfs content,
service sandboxes, X input, and the bwrap command line.
