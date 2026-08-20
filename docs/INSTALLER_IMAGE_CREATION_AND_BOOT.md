# Greia — Installer Image Creation, USB Media, and Installation Boot

**Status:** accepted operating reference for the reference Acer development path  
**Date:** 2026-08-20  
**Audience:** build engineers, agents, release engineering

This document is the concise operating reference for the physical Acer path. Historical failure detail lives in:

```text
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/INSTALLED_OS_BOOT_POSTMORTEM.md
docs/INSTALLATION_ISSUES_LOG.md
docs/reviews/2026-08-20_ACER_INSTALLER_BOOT_REGRESSION.md
docs/design/GREIA_BOOT_EXPERIENCE.md
```

## 1. There are three independent contracts

Do not merge these into one debugging problem:

1. **removable-media boot** — BIOS → Syslinux/FAT32 → live kernel/initramfs;
2. **installed-system boot** — installed GRUB → kernel/initramfs → systemd → X/launcher;
3. **boot presentation** — the pixels and geometry shown by GRUB/initramfs/launcher.

A presentation change must not rewrite the proven removable-media mechanics merely because both are visible during boot.

## 2. Reference Acer removable media: keep the proven Syslinux/FAT32 recipe

The reference BIOS reliably boots the antiX-style Syslinux/FAT32 layout:

- one active FAT32 partition;
- `vmlinuz`, `initrd.img`, `filesystem.squashfs` at the filesystem root;
- target payload under `payload/`;
- `.disk/live-uuid` copied from the verified installer image;
- Syslinux VBR + `mbr.bin` MBR;
- `TIMEOUT 0`, straight to the installer.

The canonical writer remains:

```text
tools/build-live-usb.sh
```

Read-back verification remains a **separate** step:

```text
tools/verify-live-usb.sh
```

Do not fold filesystem repair, probing, artwork generation or unrelated verification back into the firmware-sensitive writer.

## 3. Preferred physical development workflow

For the reference Acer, use the high-level development front door:

```bash
sudo bash tools/build-and-flash-development-usb.sh \
  legacy-x86-i686-dev \
  /dev/sdX
```

`/dev/sdX` is the whole removable USB device and is destroyed.

For image-only construction:

```bash
sudo bash tools/build-development-installer.sh \
  legacy-x86-i686-dev \
  ./out
```

These commands deliberately route legacy-x86 through:

```text
build/build-legacy-x86-sd-installer.sh
```

That wrapper is now responsible for generating and validating the current splash derivatives before the lower-level image builder runs.

### Important: do not bypass the physical front door accidentally

`build/build-installer-image.sh` is a lower-level image composer. Calling it directly can intentionally bypass physical-Acer wrapper responsibilities such as the fresh splash-generation gate.

Therefore this is **not** the recommended command for an Acer acceptance build:

```bash
# Lower-level builder — not the physical Acer acceptance front door.
sudo bash build/build-installer-image.sh legacy-x86-i686-dev ./out
```

The high-level wrapper exists specifically so a build cannot appear fresh while consuming stale generated boot artwork.

## 4. Live-media identity remains a three-way invariant

The following must identify the same live medium:

```text
kernel command line greia.live_media_id
USB /.disk/live-uuid
initramfs /conf/uuid.conf
```

The image builder validates the identifier embedded in the final live initramfs after the final `update-initramfs`. The USB writer copies the verified initrd and identity marker, and the read-only USB verifier compares the actual removable media back to the source image.

A splash change must never alter this contract.

## 5. Installed root/initramfs storage policy

The installed-OS postmortem established the critical rule: the initramfs regenerated inside the target during installation must not infer target storage requirements from build/chroot hardware.

The target keeps:

- `MODULES=most`;
- the Greia target-kernel storage hook;
- conditional inclusion of storage modules such as `ahci`, `libata`, `sd_mod` when the target kernel supplies them.

Always reason about the **regenerated installed initramfs**, not only the initramfs that happened to exist inside the original payload.

## 6. Development SSH is a hard invariant

For explicit `*-dev` profiles, both the live installer and installed OS must expose:

```text
user: greia
password: greia
```

No operator/client SSH private key is required. No generated 16-character operator password is part of the development workflow. Root SSH remains denied.

The build provisions the `greia` account and enables sshd. Immediately before sshd validation/start, the Greia development bootstrap enforces the effective policy:

```text
PasswordAuthentication yes
KbdInteractiveAuthentication no
AuthenticationMethods password
PermitRootLogin no
AllowUsers greia
```

It also generates one machine-local Ed25519 **server host key** when needed. That server identity is automatic and is not a credential the operator types or preserves.

The artifact verifier inspects both squashfs roots for this recovery contract before reporting PASS.

## 7. Development boot diagnostics

During the current Acer recovery gate, development boots intentionally remain observable and non-rebooting on fatal errors:

```text
console=tty1
panic=0
loglevel=4
systemd.show_status=true
rd.systemd.show_status=true
```

Normal/release appliance presentation can return to console suppression only after the hardware path is accepted.

If the screen stops on a successful systemd line such as:

```text
Finished systemd-update-utmp-runlevel.service -- Record Runlevel Change in UTMP
```

that line is not automatically the blocker. It may simply be the last successful unit printed before the graphical target starts. In particular, inspect `greia-launcher.service`/Xorg over the development SSH channel before diagnosing a systemd runlevel hang.

## 8. Splash presentation — current corrected contract

The rejected historical splash pipeline thresholded a noisy legacy frame, median-filtered the result, and repainted it indigo `(62,70,130)` on white. That process intentionally destroyed colour/detail and is the direct reason a successful boot could still show a white/blue broken-looking image.

That pipeline is no longer the accepted design.

Current source:

```text
assets/boot/source/legacy-plymouth-theme/frames/frame_0051.png
```

Current generated presentation:

```text
untouched full-colour 222×600 source
        ↓
1600×900 landscape canvas
  - source centred at native resolution
  - background extended from source corner palette
  - no threshold, mask, recolour or quantisation
        ├─ PNG for installed GRUB + launcher
        └─ exact P6 PPM for live + installed initramfs
```

### Early framebuffer geometry

`build/early-boot/greia-fb-splash.c` fits the entire generated landscape canvas proportionally into the detected framebuffer and centres it. It no longer scales the portrait source to nearly the full physical display height.

The renderer uses the canvas background colour for any remaining letterbox pixels and fails soft on unsupported reversed framebuffer bitfields instead of knowingly painting corrupt colours.

### Installed GRUB geometry

The installed GRUB path uses:

```text
build/overlay/boot/grub/greia-theme.txt
```

with proportional centred padding. Raw `background_image` stretch in the installed Greia GRUB script is rejected because it was responsible for horizontally stretching the portrait artwork across the Acer panel.

## 9. Why this splash change is different from earlier claimed fixes

A source edit is not accepted as a splash fix.

For a physical legacy build, `build/build-legacy-x86-sd-installer.sh` now:

1. backs up generated derivatives in the checkout;
2. runs `tools/generate_boot_artwork.py` immediately before image composition;
3. verifies that the canonical source copy is pixel-identical to the retained full-colour frame;
4. verifies the 1600×900 canvas and exact P6 encodings;
5. builds the live and target roots while those generated bytes are present;
6. restores the checkout generated files afterward;
7. records splash mode/hashes in the build report.

Then `tools/verify-development-installer.sh` examines the **finished image** and rejects PASS unless:

- live and target embedded PPMs are identical 1600×900 canvases;
- the raster has real full-colour diversity;
- the historical white/indigo two-colour signature is absent;
- installed GRUB PNG and launcher PNG decode to exactly the same RGB canvas;
- installed GRUB theme uses centred proportional `padding`;
- the installed GRUB script does not contain an active raw stretch command.

This still requires physical visual acceptance. It simply removes the previous loophole where source looked changed while the booted artifact was unchanged.

## 10. Graphical launcher handoff

The systemd/Xorg service keeps the hardware-proven invariants from the Acer bring-up:

- `RuntimeDirectory=greia-os`;
- `StandardInput=null`;
- no desktop-style service namespace blocking Xorg device/path access;
- the accepted Xwrapper policy;
- Xorg on VT1.

The newer profile-aware `greia_launcher.child_shell` remains primary. Because it was introduced after the original hardware proof, the X session now falls back once to `greia_launcher.presentation` if the child-shell process exits non-zero. The original error remains in the journal. This protects the graphical boot from a new composition-layer exception without hiding an Xorg failure.

## 11. What a successful physical build must report

The exact wording may grow, but the development build must at minimum complete the artifact and USB gates rather than merely creating an `.img`:

```text
Developer installer artifact verification: PASS
Greia live USB read-only verification: PASS
usb_readback_verification=PASS
```

The image report must also identify:

```text
boot_artwork_mode=full-color-landscape-canvas-v1
boot_artwork_canvas=1600x900
boot_artwork_grub_scaling=padding-centered
```

Do not call the splash physically fixed until the Acer itself shows the corrected image.
