# Acer Installer Boot Regression — 2026-08-20

**Status:** active recovery record; source rollback complete, physical re-acceptance pending  
**Reference hardware:** Acer Aspire One, BIOS-only legacy x86  
**Authoritative historical inputs:**

- `docs/INSTALLATION_USB_BOOT_POSTMORTEM.md`
- `docs/INSTALLED_OS_BOOT_POSTMORTEM.md`
- `docs/INSTALLATION_ISSUES_LOG.md`
- `docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md`
- `docs/design/GREIA_BOOT_EXPERIENCE.md`

## 1. Physical symptom

After a newly built installer was actually written to the USB key, the reference Acer no longer reached the graphical installer. The visible sequence was approximately:

```text
very brief Syslinux text
→ grey screen
→ delayed reboot
→ repeat
```

This was a regression from the immediately preceding language-enabled installer build, which physically reached the new language chooser.

The symptom is particularly important because the installed-OS postmortem already records **grey screen + delayed reboot** as the characteristic result of an early boot failure hidden by console suppression plus an automatic panic reboot. It must therefore be treated as an early-boot diagnostic event first, not as evidence of an ordinary graphical-service failure.

## 2. Last physically useful baseline

The retained handover records that `legacy-x86-i686-dev` using the Syslinux/FAT32 removable-media path is the physically proven reference profile/path. The later language-first build also reached the installer before the boot-polish/SSH-hardening tranche described below.

For recovery purposes, commit `2f123a9bec193a1ee33870fa4f6bc57a201dab3c` was used as the source blob baseline for boot-medium and installed-boot files that were known to precede this regression. This is **not** a claim that every file at that commit is current product truth; it is a narrow boot recovery boundary.

## 3. Engineering rules that were violated

### 3.1 Observable Syslinux output was removed

`INSTALLATION_USB_BOOT_POSTMORTEM.md` explicitly establishes:

> Keep bootloader output observable.

The successful Acer investigation depended on seeing Syslinux itself and the `Loading /vmlinuz...` / `Loading /initrd.img...` progress. A later change added a form-feed `DISPLAY` clear file and changed the live kernel command line from:

```text
console=tty1
```

to:

```text
console=null
```

while retaining an automatic panic timeout.

That was a direct violation of the accepted hardware-debugging rule. Even if it was not the root cause of the reboot, it converted a diagnosable early failure into the same grey-screen/reboot blindness documented in the installed-OS postmortem.

### 3.2 The accepted RGB565-safe artwork decision was replaced without hardware proof

`INSTALLER_IMAGE_CREATION_AND_BOOT.md` records the accepted splash diagnosis:

- the observed blue/white corruption was attributed to a noisy extraction;
- the accepted transform uses a luminance floor + median filter;
- the foreground is indigo `(62,70,130)` on white so it remains visible on RGB565;
- the early framebuffer renderer remains the hardware-neutral runtime adapter.

A later source change instead made the boot generator copy the retained legacy frame's raw RGB pixels directly into all boot derivatives and then made the legacy physical build regenerate those full-colour assets automatically.

That contradicted the accepted hardware record and introduced new binary raster content into initramfs without a physical acceptance pass.

### 3.3 Verification was mixed into the firmware-sensitive USB writer

The original `tools/build-live-usb.sh` is the proven antiX-style recipe:

1. wipe device;
2. one active FAT32 partition at sector 2048;
3. copy kernel/initrd/live squashfs/payload/identity;
4. install Syslinux VBR;
5. write Syslinux `mbr.bin` to the first 440 bytes;
6. sync.

A later safety pass substantially expanded that same writer with read-back/fsck behavior and the new clear-screen file. Most of those checks were sensible, but changing the firmware-sensitive writer itself violated the principle that the proven recipe should remain stable while verification is added around it.

The recovery design now separates these concerns:

```text
physically proven writer
        ↓
finished USB media
        ↓
separate read-only verifier
```

`tools/verify-live-usb.sh` performs FAT, MBR, identity, Syslinux-config and byte-for-byte payload checks without partitioning, formatting, installing a bootloader or writing to the device.

### 3.4 An unproven GRUB presentation change entered the installed payload

The installed target had physically reached the launcher using the previous GRUB script. A later splash-size fix replaced raw `background_image` usage with a new GRUB theme. That may be architecturally reasonable, but it was not physically accepted on the reference Acer before being included in the same rebuild tranche.

During recovery the installed GRUB script was therefore restored to the known booting baseline. Splash geometry/presentation improvements must be reintroduced independently after boot viability is re-established.

## 4. What was restored

Recovery commit:

```text
b81358a9ac7f78eb64dbef8ef63537e21bb5fecf
```

restored the following exact historical blobs from the known pre-regression boot boundary:

- `build/live-syslinux/syslinux.cfg.in`
- `tools/generate_boot_artwork.py`
- `build/build-legacy-x86-sd-installer.sh`
- `tools/build-live-usb.sh`
- `build/overlay/etc/grub.d/10_greia_appliance`
- `tests/test_boot_experience_contract.py`

and removed the unaccepted:

- `build/live-syslinux/clear.msg`
- `build/overlay/boot/grub/greia-theme.txt`

The later binary-P6 parser correction in `build/early-boot/greia-fb-splash.c` was intentionally **retained**. It is a parser correctness fix: P6 raster bytes are binary and must not be skipped merely because their numeric value is <= ASCII space. The renderer's initramfs invocation is fail-soft.

The physically proven USB writer was subsequently left unchanged and final-media checking moved to the separate read-only `tools/verify-live-usb.sh`.

## 5. What was deliberately NOT rolled back

The regression occurred before the installer UI appeared, so unrelated later product work remains:

- language-first installer entrypoint;
- Italian installer presentation layer;
- first-screen pointer/hover fix;
- device-language persistence and Parent surfaces;
- developer SSH `greia / greia` hardening;
- automatic machine-local Ed25519 SSH host identity;
- explicit live installer networking/mDNS dependencies;
- artifact-level live/target SSH verification;
- unrelated Activity/localization/launcher work.

These components run after or outside the firmware/Syslinux/kernel/live-root transition and are not rolled back merely because they are temporally newer.

## 6. Current recovery safety architecture

The preferred development flow remains one command, but its responsibilities are separated:

```text
tools/build-and-flash-development-usb.sh
        |
        +-- build-development-installer.sh
        |      +-- verifies developer-remote in live + target
        |      +-- builds image through the restored legacy front door
        |      +-- verify-development-installer.sh (read-only image check)
        |
        +-- build-live-usb.sh
        |      +-- physically proven Syslinux/FAT32 writer
        |
        +-- verify-live-usb.sh
               +-- read-only final-media verification
```

For the current Acer recovery acceptance, the Syslinux template is deliberately diagnostic rather than cosmetically silent:

```text
console=tty1
panic=0
loglevel=4
systemd.show_status=true
rd.systemd.show_status=true
```

`panic=0` is intentional: a fatal kernel/initramfs/live-boot failure must remain on screen rather than being destroyed by another timed reboot. The recovery template also does not use `quiet`, `splash`, `loglevel=0`, `console=null`, Syslinux `DISPLAY` clearing, `NOESCAPE`, or `NOCOMPLETE`.

Normal/release **installed** Greia remains consoleless. The installed `developer-remote` payload is different by design: its GRUB generator emits tty1-visible diagnostics and `panic=0`, while the normal/release branch retains the appliance console/panic policy. `tools/verify-development-installer.sh` checks the actual embedded target squashfs for this dev-only policy before the installer is considered valid.

## 7. Causal assessment

The looping image crossed four boot-critical boundaries in one tranche after a language-enabled image had physically reached the installer:

1. Syslinux output was cleared and the kernel console changed to `console=null`;
2. the legacy build began injecting a new raw/full-colour initramfs raster automatically;
3. the firmware-sensitive USB writer itself was expanded and changed;
4. the installed payload changed GRUB presentation behavior at the same time.

Those changes are the **regression cluster** and have been removed from the recovery build path. Source inspection cannot honestly distinguish which individual member caused the physical early reboot because the same tranche also removed the diagnostic channel needed to discriminate them. It is therefore incorrect to invent a single proven cause.

Several tempting alternatives have been checked and are not supported by current source:

- the recovery profile remains `i386` with Debian `linux-image-686`; it was not silently switched to the separate PAE profile;
- the live builder embeds the generated media ID into initramfs `/conf/uuid.conf` and verifies it after the final `update-initramfs`;
- the proven USB writer copies that exact initrd plus the same `.disk/live-uuid` marker;
- target/live initramfs policy remains `MODULES=most` with target-kernel-aware storage-module handling;
- the SSH hardening adds userspace networking/SSH behavior and does not replace the live kernel or early storage policy.

The recovery therefore fixes the actual unaccepted early-boot delta first, while retaining functional language and SSH work. If the physical Acer still fails, the next boot will now stop on the exact failing stage instead of looping.

## 8. Required next physical test

Build from the exact current `main` SHA and record it with the artifact evidence. Use:

```text
legacy-x86-i686-dev
```

Preferred command:

```bash
sudo bash tools/build-and-flash-development-usb.sh \
  legacy-x86-i686-dev \
  /dev/sdX
```

Before booting the Acer, the run must report both installer-artifact verification and final read-only USB verification as PASS.

On the Acer, record the exact last visible stage if boot does not reach the installer. In particular distinguish:

- Syslinux starts / does not start;
- `Loading /vmlinuz...` appears;
- `Loading /initrd.img...` appears;
- Linux/live-boot prints an error;
- early Greia framebuffer appears;
- graphical language chooser appears.

There should be **no timed reboot** after a fatal kernel/initramfs error on this recovery build. The error should remain visible.

If the language chooser appears, test the later features independently:

1. mouse pointer works on language selector;
2. select Italian;
3. following installer pages are Italian;
4. connect networking and confirm `ssh greia@greia-installer.local` with password `greia`;
5. install;
6. boot installed OS;
7. if it does not reach launcher, preserve tty1 output and try `ssh greia@greia-dev.local` with password `greia` before modifying anything.

## 9. Process rule established by this regression

For boot-critical physical-hardware code:

> **presentation polish is never allowed to cross a physically proven boot boundary as part of an unrelated functional tranche.**

A bootloader, kernel command line, initramfs raster/parser, target GRUB handoff, storage policy or removable-media writer change gets its own narrow build and hardware acceptance. Tests lock the accepted state only after that evidence exists.
