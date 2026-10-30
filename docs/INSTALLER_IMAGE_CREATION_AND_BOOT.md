# Greia — Installer Image Creation, USB Media, and Installation Boot

**Status:** accepted operating reference for the reference Acer development path  
**Date:** 2026-08-20  
**Audience:** build engineers, agents, release engineering

This document is the concise operating reference for the physical Acer path. Historical failure detail lives in:

```text
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/INSTALLED_OS_BOOT_POSTMORTEM.md
docs/INSTALLATION_ISSUES_LOG.md
docs/archive/reviews/2026-08-20_ACER_INSTALLER_BOOT_REGRESSION.md
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

The canonical installer artifact name now includes the repository version and
build commit:

```text
greia-os-installer-<PROFILE>-<VERSION>-build-<12-char-commit>.img
```

The builder also creates `greia-os-installer-<PROFILE>.img` as a compatibility
symlink for existing flash/verification front doors. Sidecar report/manifest
names remain stable; the report records `version`, `build`, `output` and
`compatibility_image`. A dirty source tree appends `-dirty` to the build id.

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

### Target hardware support is re-confirmed after the copy

The pre-erase hardware plan remains the fail-closed authority, but module
binding can still settle while the payload is copied. The engine therefore
takes one second complete inventory immediately before target configuration
and merges only verified packages from the same frozen support pool into the
initial plan. A late-binding driver (the reference `iwl3945` Wi-Fi case) then
adds its firmware to the target instead of leaving the installed system unable
to scan networks while the live installer could. An incomplete refresh never
weakens the initial decision. `install-record.json` records the final merged
package list; the ordinary record still contains package names only, never raw
inventory.

The refresh only helps when the inventory actually changed. Driver firmware is
found through `modinfo`, so the install-transaction and system-update services
must be able to read `/usr/lib/modules`: they do not set
`ProtectKernelModules=yes` (it hid that tree, made every driver look built-in
and left every installed target without driver firmware) and deny module
loading with the capability bounding set plus `SystemCallFilter=~@module`
instead. An unreadable module tree, a loaded module that `modinfo` cannot
describe, or a missing `modinfo` makes the hardware plan incomplete.

**Incomplete detection never stops the install** (owner decision 2026-10-21).
An incomplete plan adds the common network/Wi-Fi firmware set
(`FALLBACK_NETWORK_FIRMWARE` in `greia_installer/hardware_enablement.py`:
`firmware-iwlwifi`, `-realtek`, `-atheros`, `-brcm80211`, `-libertas`,
`-misc-nonfree`), restricted to what the verified pool provides, to whatever the
plan did resolve plus microcode. The A/B seam does the same and includes the
fallback in `selected_installed_bytes`. `install-record.json` gains
`hardware_detection: "incomplete"`, `hardware_fallback_packages` and up to three
`hardware_detection_diagnostics`; the transaction journal (stderr) logs the same,
and the completion page shows a short localized note. Pool verification
failures (corrupt/unverified pool, identity mismatch) still refuse before any
disk change; only the "incomplete detection" case changed.

## 6. Development SSH is a hard invariant

For explicit developer profiles (`*-dev`, and the release candidate `legacy-x86-i686-rc`), both the live installer and installed OS must expose:

```text
user: greia
password: greia
```

Root SSH remains denied. The build provisions the `greia` account and enables sshd. Immediately before sshd validation/start, `prepare-developer-ssh` regenerates the effective policy (so nothing hand-edited survives a restart by accident):

```text
PasswordAuthentication yes
KbdInteractiveAuthentication no
PubkeyAuthentication no|yes
AuthorizedKeysFile /etc/ssh/greia-operator-keys/%u .ssh/authorized_keys
AuthenticationMethods password            # no operator key installed
AuthenticationMethods publickey password  # key OR password, when a key is installed
PermitRootLogin no
AllowUsers greia
```

**Operator key for agents (optional, public key only).** Pass `--operator-key /path/key.pub` to `tools/build-and-flash-development-usb.sh` or `tools/build-development-installer.sh` (or export `GREIA_OPERATOR_AUTHORIZED_KEY_FILE`). `build/lib/operator_key.py` refuses private keys, `authorized_keys` options and malformed lines, and prints the SHA256 fingerprint. The key is installed root-owned at `/etc/ssh/greia-operator-keys/greia` in both roots. A non-developer profile refuses the input. A hand-provisioned `~greia/.ssh/authorized_keys` also switches the policy to key-or-password, so key access no longer disappears on an sshd restart (Acer parity audit B1). Never commit the key file or a private key.

**Passwordless privilege stays bounded.** The only sudoers entry is `greia ALL=(root) NOPASSWD: /usr/local/sbin/greia-devctl`. In-place source deploys (`tools/dev_source_deploy.py`) use `greia-devctl source-deploy probe|prepare|extract|parse-gate|swap|status|cleanup` (fixed paths, `build/overlay/usr/local/lib/greia-os/greia-source-deploy`); older images need `--legacy-generic-sudo` and a hand-provisioned generic `sudo -n`. Replacing `/opt/greia-os` is root-equivalent by nature; the verb keeps it auditable, it is not a boundary against the operator.

The verifier also generates nothing: one machine-local Ed25519 **server host key** is created on first sshd start. The artifact verifiers inspect both squashfs roots for this contract before reporting PASS.

## 7. Boot console policy (diagnostic vs quiet)

The console is a profile fact, `boot.console_policy`, independent of the developer marker. When a profile omits it, `*-dev` profiles are `diagnostic` and all others `quiet`, so existing profiles behave exactly as before.

| Policy | Profiles | Kernel line | Hidden fallback |
| --- | --- | --- | --- |
| `diagnostic` | `*-dev` | `console=tty1 panic=0 loglevel=4 systemd.show_status=true rd.systemd.show_status=true vt.global_cursor_default=1` | not needed |
| `quiet` | release profiles, `legacy-x86-i686-rc` | `quiet splash loglevel=0 console=tty1 panic=0 systemd.show_status=false rd.systemd.show_status=false udev.log_priority=3 vt.global_cursor_default=0` | RC only: Syslinux `LABEL verbose`, GRUB `greia-os-diagnostics` |

Every policy keeps `panic=0`: a fatal kernel/initramfs error is never turned into a timed reboot loop.

Both policies keep the real `console=tty1`; `quiet` silences it. **Never `console=null`** (or an empty `console=`): the Debian 686 kernel has no `ttynull` driver (`CONFIG_NULL_TTY` unset), so the system boots with no console, PID 1 has no stdio, live-boot's `exec 6>&1` (and initramfs-tools' final `exec run-init ... <dev/console`) fail, and the kernel panics before anything is drawn. That froze the 2026-10-17 RC stick on the Syslinux banner; `boot_contract.FATAL_CONSOLE_ARGUMENTS` and `tools/verify-live-usb.sh` now reject it.

Where it is enforced (change all of them together):

- `tools/build_profile.py` (schema, default, `diagnostic` requires `developer-remote`; manifest `boot.console_policy`, shell `BOOT_CONSOLE_POLICY`);
- `build/lib/compose.sh` writes `/etc/greia-os/boot-console-policy` in both roots;
- `build/overlay/etc/grub.d/10_greia_appliance` renders the installed entry and declares `# greia-boot-console-policy: <policy>`; a quiet developer image adds `insmod keystatus` + "hold Shift shows the menu" and an owner-restricted (no `--unrestricted`) `greia-os-diagnostics` entry with the diagnostic arguments;
- `src/greia_platform/boot_contract.py` validates both (`BootConsolePolicy`, `--console-policy`); the installer engine's post-install check passes only `developer=`, and the declaration in the generated `grub.cfg` selects the policy;
- `src/greia_platform/grub_ab.py` takes the same optional `console_policy`;
- live USB: `build/lib/live-syslinux.sh` reads `.disk/installer-image-profile.json` and selects `build/live-syslinux/syslinux.cfg.in` (diagnostic, unchanged) or `syslinux-quiet.cfg.in`; `tools/verify-live-usb.sh` uses the same selection;
- `tools/verify-development-installer.sh` and `tools/verify-development-target-image.sh` (shared `build/lib/verify-composed-root.sh`) check the recorded policy and run the boot contract on the rendered `grub.cfg`.

**Reaching the diagnostics on a quiet RC (owner only):**

- USB installer: hold **Shift** or **Alt** (or turn Caps Lock / Scroll Lock on) while the stick boots. Syslinux shows `boot:`; type `verbose` and Enter. That label carries exactly the diagnostic APPEND line.
- Installed OS: hold **Shift** while GRUB starts. The menu appears; choose *Greia OS diagnostics* and enter the GRUB owner credential (`greia` + the recovery code).
- Both paths are UNPROVEN on the Acer until checked physically (premortem F2).

**Owner decision 2026-10-18 — the quiet RC clears the stock Syslinux banner.** Stock SYSLINUX prints its version/copyright line before it can parse any configuration, and with a quiet kernel that text then survives the fbcon takeover (which redraws the console buffer) until the Greia framebuffer cover paints — the visible "SYSLINUX 6.04 … H. Peter Anvin" line the owner asked to remove. The quiet template now consumes `build/live-syslinux/clear.msg` (one form-feed byte) through `DISPLAY /boot/syslinux/clear.msg`; `tools/build-live-usb.sh` places the byte on quiet media only and `tools/verify-live-usb.sh` requires it there. This is presentation-only: `console=tty1` is kept, so a kernel/initramfs panic still prints its emergency message, the `verbose` recovery label is unchanged, and the diagnostic template/media intentionally keep fully observable boot output (the verifier refuses any `DISPLAY` there). The short `Loading /vmlinuz…` / `Loading /initrd.img…` lines remain for the load duration. A physical Acer re-acceptance of this quiet path remains required (premortem F2); the 2026-08-20 review's objection applied to the combination with the fatal `console=null` argument, which is separately rejected.

If a diagnostic boot stops on a successful systemd line such as:

```text
Finished systemd-update-utmp-runlevel.service -- Record Runlevel Change in UTMP
```

that line is not automatically the blocker. It may simply be the last successful unit printed before the graphical target starts. Inspect `greia-launcher.service`/Xorg over SSH, and the persistent developer journal (`journalctl -b -1`), before diagnosing a systemd runlevel hang.

## 8. Splash presentation — current corrected contract

The rejected historical splash pipeline thresholded a noisy legacy frame, median-filtered the result, and repainted it indigo `(62,70,130)` on white. That process intentionally destroyed colour/detail and is the direct reason a successful boot could still show a white/blue broken-looking image.

That pipeline is no longer the accepted design.

Current source:

```text
assets/boot/frames/frame_0051.png
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

The systemd/Xorg service keeps the hardware-proven invariants from the Acer bring-up, updated by the 2026-09-27 physical VT investigation:

- the launcher remains `User=greiakid`;
- `TTYPath=/dev/tty1` + `StandardInput=tty-fail` gives the X server the controlling VT and fails closed rather than stealing an occupied terminal;
- `greia-x-session` immediately redirects its own stdin to `/dev/null` before starting the child shell or helpers, preserving the earlier SIGTTIN fix for the application tree;
- Xorg writes its explicit log to the greiakid-owned `/run/greia-os/Xorg.0.log`;
- no desktop-style service namespace blocks Xorg device/path access;
- the accepted Xwrapper and legacy-input policies remain present;
- Xorg stays on VT1 so the early framebuffer cover and graphical handoff do not deliberately switch VTs.

Shared volatile roots are owned by `systemd-tmpfiles`, not by a launcher-specific `RuntimeDirectory=greia-os`. The launcher is ordered after tmpfiles setup and asserts the required roots before starting.

The profile-aware `greia_launcher.child_shell` remains primary, with the trusted presentation fallback retained for a child-shell composition failure. The original error remains in the journal. This protects graphical boot from a composition-layer exception without hiding an Xorg failure.

## 11. Repeated rebuilds reuse the persistent host apt/pool caches

`build/lib/apt-cache.sh` keeps two persistent host caches outside the produced
image (`GREIA_APT_CACHE=/var/cache/greia-apt`,
`GREIA_POOL_CACHE=/var/cache/greia-pool`). Both builders bind-mount them for
the chroot's lifetime, with the apt cache mounted BEFORE debootstrap (before
any `apt-get`) so base downloads land on the host, and the existing
`MOUNTS`/`safe_unmount_paths` teardown releases
them before footprint measurement and `mksquashfs`. Chroots run `apt-get
autoclean` (never `clean`), so a repeated
`build/build-installer-image.sh <profile>` run reuses already-downloaded
`.deb`s instead of re-fetching the whole package set. Never clear the host
caches to "save space" — that only forces a full re-download next build.

## 12. What a successful physical build must report
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

## 13. Release-candidate build runbook (`legacy-x86-i686-rc`)

The RC is one build (installer redesign + boot animation + quiet boot), installed on the reference Acer through the graphical installer. It is a **developer RC**, not an ADR 0036 release: it carries all Activities, SSH is on and the release roster is still draft.

**What the RC image contains beyond `legacy-x86-i686`:** the `developer-remote` set in both roots (SSH, mDNS, `greia-devctl`), hostname `greia-rc`, `boot.console_policy = "quiet"`, a bounded persistent journal (`/etc/systemd/journald.conf.d/20-greia-developer-persistent.conf`, 48 MiB), the read-only bytecode prefix in both roots, the microphone ALSA module in both roots (the build fails if it is missing) and `snd_hda_intel power_save=0`. The hard size gate is 1,500 MiB (owner decision 2026-10-21, raised from 1,300 MiB so the four-language `@2x` art and the UEFI/BIOS boot payload fit one image).

### 13.1 Pre-build gates (premortem G1–G11)

Run G1–G8 on the frozen SHA before touching the build host. Nothing lands on `main` during the build.

| Gate | Where | Check |
| --- | --- | --- |
| G1 | local | `git status` clean; record the frozen SHA; the build host uses a fresh clone at that SHA (the composer rsyncs the working tree) |
| G2 | local | `make verify-full` green (known load-flakes re-run in isolation) |
| G3 | local | `make validate`, `make visual-assets-check`, `make assets-check`, `make shell-check` |
| G4 | local | `tools/audit_activity_backend_independence.py activities`; `tools/audit_activity_system_chrome_ownership.py --strict` |
| G5 | local | the focused contract list in the premortem §4, plus `tests/test_rc_image_contract.py`, `tests/test_boot_contract.py`, `tests/test_grub_ab.py`, `tests/test_dev_source_deploy.py` |
| G6 | local | footprint estimate below 1,500 MiB with margin (see the RC report) |
| G7 | local | `tools/panel_screenshots.py` and `tools/installer_screenshots.py` at 1024×600 and 800×480; no overlap |
| G8 | Acer | `python3 tools/dev_source_deploy.py deploy --target greia@<acer>` (current image: add `--legacy-generic-sudo`), then `status`, launch 5 Activities, `cleanup` |
| G9 | build host | `smartctl -a`, `journalctl -k -p err --since -1d`, root fs below 80 %, **reboot**, `losetup -a \| grep greia` empty, apt/pool caches present |
| G10 | build host | the front door below reports every PASS line |
| G11 | build host (optional) | `build/verify-image-qemu.sh` on the target `.img` (768 MiB, 1 vCPU) |

### 13.2 Build host commands (Debian x86, no Docker)

```bash
# Once per host (as root): build prerequisites
apt-get install -y debootstrap parted e2fsprogs dosfstools grub-pc-bin grub-common \
  grub-efi-ia32-bin grub-efi-amd64-bin \
  rsync squashfs-tools syslinux syslinux-common mtools python3 python3-pil \
  util-linux gdisk binutils smartmontools

# Fresh clone at the frozen SHA (never the working tree of another checkout)
git clone https://github.com/frozenpepper/Greia.git greia-rc && cd greia-rc
git checkout --detach <FROZEN_SHA>
git status --porcelain            # must print nothing

# Operator PUBLIC key for agent SSH (copy only the .pub file to the host)
ls -l ~/greia-operator.pub         # never a private key, never committed
```

### 13.3 Identify the USB stick before writing

```bash
lsblk -d -o NAME,SIZE,MODEL,SERIAL,TRAN,RM,TYPE
# Pick the line whose SIZE, MODEL and SERIAL match the stick in your hand,
# with TRAN=usb RM=1 TYPE=disk. Unplug it, re-run lsblk, confirm that exact
# line disappears, plug it back, confirm it returns under the same /dev/sdX.
udevadm info --query=property --name=/dev/sdX | grep -E 'ID_SERIAL=|ID_BUS='
```

The front door refuses non-removable or mounted devices, but only the size/model/serial check above proves it is the right stick.

### 13.4 Build, flash and verify in one command

```bash
mkdir -p ./out
setsid nohup sudo -n unshare --mount --propagation private -- \
  bash tools/build-and-flash-development-usb.sh \
  legacy-x86-i686-rc /dev/sdX ./out \
  --operator-key ~/greia-operator.pub \
  > ./out/rc-build.log 2>&1 < /dev/null &
# (setsid before sudo, and the private mount namespace: see
# docs/agents/GREIA_AGENT_OPERATIONS.md §"Build-host disk health and
# loop-device hygiene" — without unshare a desktop build leaks the chroot
# rootfs mount into system-service namespaces and the loop cannot detach)
tail -f ./out/rc-build.log
```

Required lines in the log (G10):

```text
operator_ssh_key=SHA256:...                       (matches ssh-keygen -lf of the .pub)
greia_mic_light ALSA module: /usr/lib/i386-linux-gnu/alsa-lib/... (Intel 80386)   (target and live)
bytecode prefix /usr/lib/greia/pycache ... greia=N   (target and live, no "error:" lines)
GRUB boot contract passed for 1 kernel command line(s).
Budgeted/accounted: NNN MiB                        (below 1,500)
Developer installer artifact verification: PASS
- boot console: quiet (installer + installed), panic=0; hidden Syslinux 'verbose' + owner-only GRUB diagnostics
Greia live USB read-only verification: PASS
  usb_readback_verification=PASS
  live_console_policy=quiet
boot_console_policy=quiet
loop_hygiene_verification=PASS
```

Also record from `out/greia-os-installer-legacy-x86-i686-rc-report.txt`: `sha256`, `boot_console_policy`, `boot_artwork_*`, `live_security_support_state`; and from the payload footprint report `accounted_mib` and `security_support_state`. Afterwards `losetup -a | grep greia` must be empty.

For any QEMU check of i386 media use `build/verify-image-qemu.sh` or, manually, `-cpu n270` (the reference Atom class). `-cpu pentium3` has no SSE2; Debian's i386 NumPy refuses to load, the installer client dies, and the bounded `Restart=always` plus `installer-exit-cover` repaint a clean Greia splash over the dead service — a CPU-model artifact that looks exactly like a stalled image. See `docs/INSTALLATION_ISSUES_LOG.md` §35.

### 13.5 First boot

Follow the Acer acceptance checklist in `docs/reviews/2026-10-17_RC_IMAGE_PREMORTEM.md` §5. Remote checks: `ssh -i <private key> greia@greia-rc.local` (installed) or `greia@greia-installer.local` (installer), `sudo -n /usr/local/sbin/greia-devctl status` (installed target; the live installer root ships SSH but not `greia-devctl`), `journalctl -b -1` after any reboot. Check the hidden verbose paths once (F2). Wi-Fi joined in the installer is expected to carry over to the installed system once the installer hand-off lands (credentials in `/var/lib/iwd`, root-only); until then re-join from the Parent panel.

After the installer's completion power-off, remove the USB key before powering the machine on (the installer's completion screen says so). If the key stays inserted, the firmware boots the stick again; since 2026-10-18 the quiet media clears the stock Syslinux banner, so that re-boot shows only Greia artwork, but the installed system is on the internal disk.

On the final "All done!" page, use the on-screen **"I'm ready — turn off"** button. It writes the finish marker that the root `greia-installer-finish.path` unit watches, so the machine powers off with the Greia cover as the final frame. The laptop's physical power button bypasses that helper and keeps stock shutdown logging; use it only if the on-screen path fails (and report what the screen shows).

## 14. Intel Mac / UEFI boot (UNPROVEN, LAB)

Status 2026-10-21: SOURCE only. No Mac or EFI machine has booted this. It implements the theory in
`docs/reviews/2026-10-21_PRE_M1_MAC_HARDWARE_SUPPORT.md` and must not be described as working.

**Installer USB.** `build/build-installer-image.sh` now writes one MBR table: p1 = 64 MiB FAT32 EFI System
Partition (type `0xEF`), p2 = ext4 root with the boot flag. BIOS `grub-pc` is installed exactly as before (MBR +
1 MiB gap + active root). The ESP gets removable-path GRUB images `EFI/BOOT/BOOTIA32.EFI` (32-bit EFI Macs
2006-2007) and `EFI/BOOT/BOOTX64.EFI` (64-bit EFI), built with `grub-install --removable --no-nvram`. Both are built with
`--boot-directory` on the ext4 root, so BIOS and both EFI images read the **same** `/boot/grub/grub.cfg` and the
same `$LIVE_KERNEL_CMDLINE`; there is no second cfg to drift. A pure GPT stick or an `sgdisk` hybrid MBR was not
used because it changes how legacy BIOSes (the Acer reference) see the stick; revisit only if a Mac refuses MBR+ESP
media (LAB). Build host needs `grub-efi-ia32-bin`, `grub-efi-amd64-bin`, `dosfstools`. Image consumers
(`tools/build-live-usb.sh`, the SD finalizer and both read-only verifiers) locate the ext4 live root by
filesystem type through `build/lib/installer-image-root.sh`; they never assume partition 1.

**Installed disk.** `src/greia_installer/efi_boot.py` holds the single-root layout adapters. The live installer
picks `uefi-or-bios-gpt-ext4` only when `/sys/firmware/efi` exists **and** the target profile composed the
`boot-grub-efi` package set; every other case keeps the unchanged MBR layout and `grub-install --target=i386-pc`.
The EFI layout is GPT: 1 MiB `bios_grub`, 256 MiB FAT32 ESP (`GREIA_EFI`), root ext4 (`legacy_boot`). EFI word size
comes from `/sys/firmware/efi/fw_platform_size` (missing file: 64-bit unless the CPU lacks `lm`). Install steps, all
argument arrays in the target chroot: native `grub-install --target={i386,x86_64}-efi --bootloader-id=greia
--no-nvram`; then `--removable` for both `i386-efi` and `x86_64-efi` (so `BOOTIA32.EFI` and `BOOTX64.EFI` both exist,
verified); then best-effort (never fatal) `efibootmgr --create` and an `i386-pc` install into the `bios_grub` partition
for CSM boots. Target packages are the `-bin` set only (`build/package-sets/boot-grub-efi.txt`): `grub-efi-ia32` and
`grub-efi-amd64` conflict with `grub-pc`. No `/boot/efi` fstab line is written (the ESP is only needed at install time).

**Open LAB questions.** (1) Can x64 EFI GRUB start the i686 kernel on 2008+ (64-bit EFI) Macs? Unknown; the 2006-2007
32-bit-EFI Macs are the native case. (2) Do Apple firmwares accept an MBR-table ESP stick? (3) Boot cover and Xorg on
the EFI GOP framebuffer. (4) Size of the added packages was not recorded in repo metadata; the footprint gate
(`required_core_mib = 1500` since the 2026-10-21 owner decision) measures it at build time.

**Fallback if EFI boot fails.** Hold Option at power-on and choose the "Windows" entry: Boot Camp style CSM boots the
BIOS path (MBR active root on the stick; `bios_grub` on the installed disk). Not available on T2 Macs. `rEFInd` on
another medium is a manual workaround, not a requirement.
