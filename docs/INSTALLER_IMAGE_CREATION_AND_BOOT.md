# Greia — Installer Image Creation, USB Media, and Installation Boot

**Status:** accepted operating reference  
**Date:** 2026-08-19  
**Audience:** build engineers, agents, release engineering  
**Purpose:** give the exact, reproducible steps to create a Greia installer image, make a USB key that actually boots on the reference hardware, install, and understand the installed-OS boot path — with the **WHY** behind every step so nobody re-walks the hardware failure path.

This is the concise operator reference. The full blow-by-blow is in:

```text
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md      how the USB key boot was finally made to work
docs/INSTALLED_OS_BOOT_POSTMORTEM.md          why a freshly installed OS grey-rebooted and the fix
docs/INSTALLATION_ISSUES_LOG.md               durable invariants
```

---

## 1. The two things that must both be right

There are **two independent boot problems** on the reference Acer-class hardware, and fixing one does not fix the other:

1. **Booting the installer medium** (getting from power-on to the Greia graphical installer).
2. **Booting the installed OS** (getting from the internal disk to the launcher after a successful install).

Each has its own root cause and its own fix.

---

## 2. Booting the installer medium — WHY syslinux/FAT32

### The problem

The reference Acer Aspire One (BIOS-only, no UEFI) **does not reliably execute GRUB's MBR from a USB stick**. It also will not boot its SD readers at all. GRUB's MBR works fine on the *internal disk* but not on this USB stick + firmware combination.

### The proven solution

The **antiX-style syslinux/FAT32** live USB boots reliably:

- one **active FAT32** partition;
- live files at the partition **root**: `vmlinuz`, `initrd.img`, `filesystem.squashfs`;
- the installable target under `payload/` and the live-media identity at `.disk/live-uuid`;
- **syslinux** VBR on the partition + `mbr.bin` MBR on the device;
- a `syslinux.cfg` that **boots straight to the installer** (no menu, `TIMEOUT 0`).

### WHY syslinux works

Syslinux's MBR is a tiny self-contained loader that reads the active partition's VBR with its own minimal BIOS disk code, then loads `ldlinux.sys`. It does not discover modules, search by UUID, or set up graphics — it just hands control to the partition loader. The Acer's BIOS executes that. GRUB's stage-1 needs more elaborate disk reads that this firmware + stick does not complete silently.

### How to build it

```bash
# 1. Build the Greia installer image (target + live installer + payload).
sudo bash build/build-installer-image.sh legacy-x86-i686-dev /path/to/out

# 2. Make the Acer-bootable syslinux/FAT32 USB from that image.
#    <device> is the WHOLE removable USB disk (e.g. /dev/sdd). This is DESTRUCTIVE.
sudo bash tools/build-live-usb.sh \
  /path/to/out/greia-os-installer-legacy-x86-i686-dev.img \
  /dev/sdd
```

`tools/build-live-usb.sh` refuses to run unless the target is a **removable whole disk** (`RM=1`, `TYPE=disk`), so it cannot be pointed at a system disk by accident. It wipes, partitions FAT32, copies the live files/payload/`.disk`, installs syslinux (VBR + MBR), and writes `syslinux.cfg`.

### Verify before unplugging

```bash
# MBR should start with the syslinux bootstrap (33 c0 fa ...).
sudo dd if=<device> bs=1 count=16 2>/dev/null | xxd
# The media id must match everywhere.
cat <mounted>/boot/syslinux/syslinux.cfg | grep live_media_id
cat <mounted>/.disk/live-uuid
```

All three — the `syslinux.cfg` `greia.live_media_id`, `.disk/live-uuid`, and the initramfs `conf/uuid.conf` — must be identical. `tools/build-live-usb.sh` derives them all from the image.

---

## 3. The installed-OS boot — WHY the regenerated initramfs is the real one

### The problem

After a **successful** install, the machine grey-screens and reboots in a loop. The disk, GRUB, and UUIDs all check out. The boot hides the failure (`console=null panic=5` → silent reboot).

### The root cause

The initramfs that **ships inside the payload squashfs** can look complete, but during install `update-initramfs` **regenerates** the initramfs inside the target chroot. If that regenerated initramfs uses `MODULES=dep` (dependency-based), and the chroot has no Acer SATA controller, it **drops `ahci`/`libata`/`sd_mod`**. The installed kernel then cannot see the internal disk, cannot mount root, panics invisibly, and reboots.

### WHY the source fix works

The installed target carries:

- `/etc/initramfs-tools/initramfs.conf` → `MODULES=most`;
- `/etc/initramfs-tools/conf.d/greia-hardware` → `MODULES=most`;
- an executable `greia-storage-modules` initramfs hook that runs `modinfo -k "$version"` against the **target kernel** and `manual_add_modules` **only when** that kernel provides `ahci`/`libata`/`sd_mod`.

This means regeneration cannot drop boot-critical drivers regardless of what hardware the build chroot sees. It is architecture-aware (does not force x86 module names onto future ARM profiles).

**Rule:** never let build-host/chroot hardware be the authority for target boot-critical drivers. Verify the **regenerated** initramfs (`/boot/initrd.img-*` on the installed target), not just the one shipped in the payload.

---

## 4. Developer/test SSH is built into the canonical builders

### WHY

The owner policy requires developer/test installs **and** the live installer to be reachable as `greia / greia` (root denied) during active hardware bring-up. This must be reproducible — not dependent on a manual provisioning step that can be forgotten (a flashed installer once shipped with SSH off).

### How

Both canonical builders (`build-image.sh` and `build-installer-image.sh`) detect the `developer-remote` package set in the profile. For dev profiles they:

1. unlock/set the `greia` account (`chpasswd` then `passwd -u`);
2. rewrite **both** `sshd_config.d` drop-ins (`00-greia-security-floor.conf` and `20-greia-parent.conf`) to `AllowUsers greia` (password auth), `DenyUsers root` — so no later-sorted file re-introduces publickey-only and defeats the login;
3. enable `ssh.service`;
4. write `/etc/greia-os/developer-remote`, which also switches the installed boot to **observable** mode.

Normal/release profiles stay fail-closed (SSH off, greia locked). Root SSH is always disabled.

> **WHY both drop-ins:** sshd reads `/etc/ssh/sshd_config.d/*.conf` in glob order with first-value-wins. The base builder always writes `20-greia-parent.conf` with `PasswordAuthentication no` / `AuthenticationMethods publickey`. If only `00-` (the dev floor) is rewritten, the `20-` publickey-only value can defeat the developer floor and leave `greia/greia` password SSH rejected. Writing both keeps them coherent.

---

## 5. Observable boot — the diagnostic switch

Normal builds boot consoleless (`console=null panic=5`). This is the appliance intent, but it hides failures (a silent grey-reboot loop).

Developer/test builds use `console=tty1 panic=30` so a kernel panic **prints to the screen and waits 30 s** instead of silently rebooting after 5 s. This is what turns a blind boot loop into a diagnosable failure. It is controlled by `build/overlay/etc/grub.d/10_greia_appliance` (checks `/etc/greia-os/developer-remote`) and enforced by `src/greia_platform/boot_contract.py --developer`.

**WHY:** you cannot fix what you cannot see. Make the boot observable first, then diagnose.

---

## 6. Splash logo

Two splash defects were found on real hardware:

1. **Color glitch ("one color rendered, broken"):** caused by a **noisy logo extraction** (a crude brightness threshold over-captured the navy gradient), not by the renderer. The renderer's pixel packing is verified correct for RGB565/24/32-bit framebuffers.
2. **Geometry glitch ("full-screen-width, clipped vertically"):** the installed-OS splash could render the logo oversized/clipped when the initramfs framebuffer reported odd/degenerate geometry. Fixed in `build/early-boot/greia-fb-splash.c` to always preserve aspect ratio, cap to a margin fraction of the visible area, and guard every division.

- The logo is generated by `tools/generate_boot_artwork.py` (luminance floor + median filter) into the indigo `(62,70,130)` color that survives RGB565.
- Re-run `python3 tools/generate_boot_artwork.py` whenever the source frame changes.
- The regression suite (`tests/test_boot_experience_contract.py`) guards the white-frame + logo-color + PPM contract and the geometry invariant.

---

## 7. Quick reference — current commands

| Task | Command |
|---|---|
| Build installer image | `sudo bash build/build-installer-image.sh <profile> <out>` |
| Build Acer-bootable USB | `sudo bash tools/build-live-usb.sh <image> <device>` |
| Regenerate boot artwork | `python3 tools/generate_boot_artwork.py` |
| Focused boot/SSH tests | `PYTHONPATH=src python3 -m unittest tests.test_boot_experience_contract tests.test_boot_contract tests.test_boot_animation_contract tests.test_installation_hardware_regressions tests.test_installer_engine tests.test_launcher_presentation -v` |
| Full source gate | `make verify` |
