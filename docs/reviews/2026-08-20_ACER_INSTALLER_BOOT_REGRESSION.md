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

The later binary-P6 parser correction in `build/early-boot/greia-fb-splash.c` was intentionally **retained**. It is a valid parser correctness fix: P6 raster bytes are binary and must not be skipped merely because their numeric value is <= ASCII space. The renderer's initramfs invocation is fail-soft.

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

## 6. Current safety architecture

The preferred development flow remains one command, but its responsibilities are now separated:

```text
tools/build-and-flash-development-usb.sh
        |
        +-- build-development-installer.sh
        |      +-- verifies developer-remote in live + target
        |      +-- builds image
        |      +-- verify-development-installer.sh (read-only image check)
        |
        +-- build-live-usb.sh
        |      +-- physically proven Syslinux/FAT32 writer
        |
        +-- verify-live-usb.sh
               +-- read-only final-media verification
```

For the reference Acer, the accepted development Syslinux template must remain observable:

```text
console=tty1
panic=30
```

and must not contain the rejected recovery-path experiment:

```text
console=null
DISPLAY ...clear.msg
NOESCAPE
NOCOMPLETE
```

until a separate consoleless design receives explicit physical acceptance.

## 7. Evidence boundary

No source inspection can prove which specific experimental change caused the physical reboot. At this point we know with high confidence that:

1. the boot-polish tranche materially changed boot-critical inputs after a physically booting language-selector image;
2. it violated explicit accepted postmortem rules;
3. it hid the early diagnostic output needed to distinguish live-boot identity, kernel/initramfs, framebuffer and userspace failures;
4. those boot-critical changes have now been removed/restored behind the accepted boundary.

The next Acer boot is therefore a **recovery acceptance test**, not an ordinary feature test.

Do not reintroduce full-colour boot raster, Syslinux clearing, console suppression, new GRUB theme behavior, or writer-mechanics changes before that test.

## 8. Required next physical test

Build from the exact current `main` SHA and record it with the artifact evidence. Use the physically proven reference profile:

```text
legacy-x86-i686-dev
```

The preferred USB command is:

```bash
sudo bash tools/build-and-flash-development-usb.sh \
  legacy-x86-i686-dev \
  /dev/sdX
```

Before booting the Acer, the run must report both installer-artifact verification and final read-only USB verification as PASS.

On the Acer, **do not suppress or ignore early text during this recovery pass**. Record the exact last visible line if boot does not reach the installer. In particular distinguish:

- Syslinux starts / does not start;
- `Loading /vmlinuz...` appears;
- `Loading /initrd.img...` appears;
- Linux/live-boot prints an error;
- early Greia framebuffer appears;
- graphical language chooser appears.

If the language chooser appears, then test the later features independently:

1. mouse pointer works on language selector;
2. select Italian;
3. following installer pages are Italian;
4. connect networking and confirm `ssh greia@greia-installer.local` with password `greia`;
5. install;
6. boot installed OS;
7. if it does not reach launcher, preserve visible tty1 output and try `ssh greia@greia-dev.local` with password `greia` before modifying anything.

## 9. Process rule established by this regression

For boot-critical physical-hardware code:

> **presentation polish is never allowed to cross a physically proven boot boundary as part of an unrelated functional tranche.**

A bootloader, kernel command line, initramfs raster/parser, target GRUB handoff, storage policy or removable-media writer change gets its own narrow build and hardware acceptance. Tests lock the accepted state only after that evidence exists.
