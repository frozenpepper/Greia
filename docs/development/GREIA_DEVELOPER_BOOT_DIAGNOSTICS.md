# Greia Developer Boot Diagnostics

**Status:** living developer/operator guide  
**Date:** 2026-08-20

This guide covers development-image diagnosis when an installed Greia machine does not reach the child launcher. It does not change release UX: normal/release Greia must remain consoleless and must not expose development SSH.

Normative boot architecture remains in `docs/design/GREIA_BOOT_EXPERIENCE.md`; the historical Acer investigations are preserved in `docs/engineering/boot/INSTALLATION_USB_BOOT_POSTMORTEM.md` and `docs/engineering/boot/INSTALLED_OS_BOOT_POSTMORTEM.md`. The current 2026-08-20 regression/recovery boundary is recorded in `2026-08-20_ACER_INSTALLER_BOOT_REGRESSION.md` (archived; see git history) and takes precedence for the next physical Acer build.

## 1. Interpreting `PIP_ROOT: clean ...`

A line such as:

```text
PIP_ROOT: clean, 24048/492880 files, 321602/1969664 blocks
```

is an ext filesystem check/status line for the installed root filesystem. It is important evidence:

- GRUB has loaded the installed kernel/initramfs;
- the kernel/initramfs has discovered the installed root filesystem;
- the filesystem check completed cleanly;
- this is later than the historical "internal disk missing from initramfs" failure.

It is **not** evidence that the machine is frozen at filesystem checking.

During the current hardware-recovery phase, development images deliberately use `console=tty1`, `panic=0`, `loglevel=4` and visible systemd status so a fatal boot failure remains readable rather than rebooting. Normal/release images remain consoleless. If a development machine reaches `PIP_ROOT: clean ...` and then continues running without reaching the launcher, SSH and persistent journals are the next authorities for userspace/graphical-session diagnosis.

Treat this symptom as:

> root filesystem reached; determine whether userspace/network/SSH are alive and whether the graphical session failed.

## 2. Development SSH is a hard recovery invariant

For explicit Greia `*-dev` profiles, **both** artifacts must expose the same simple recovery login:

```text
user: greia
password: greia
```

The operator does not need an SSH private key, public key, generated 16-character password, recovery token, or second authentication method.

The server still requires a cryptographic host identity. That identity is machine-owned and invisible to the login workflow: Greia generates one Ed25519 host key locally and automatically. It is not a credential the parent/developer has to type or preserve.

Normal/release profiles remain intentionally different and must not inherit this development exposure.

### Development hostnames

The live installer hostname is:

```text
greia-installer.local
```

Acer development target profiles currently use:

```text
greia-dev.local
```

If `.local` resolution is unavailable, use the router/DHCP lease table and connect to the assigned IP address directly.

## 3. Use the fail-closed development builder

For a development installer image without flashing media yet:

```bash
sudo bash tools/build-development-installer.sh legacy-x86-i686-dev
```

The wrapper refuses to proceed unless `developer-remote` is present in **both** profile scopes:

```text
target
installer
```

For `legacy-x86`, it deliberately routes through `build/build-legacy-x86-sd-installer.sh`, because that is the physical-hardware image-builder front door used before the 2026-08-20 regression. The recovery rule is intentionally conservative: do not inject boot-art, Syslinux or installed-GRUB presentation experiments into this path before the next physical acceptance pass.

The wrapper then invokes:

```text
tools/verify-development-installer.sh
```

against the finished image.

The artifact verifier mounts the produced installer image read-only and checks **both** embedded squashfs files:

- live installer has a password-enabled `greia` account;
- installed-system payload has a password-enabled `greia` account;
- `ssh.service` is enabled in both;
- the Greia sshd pre-start bootstrap is present in both;
- runtime policy forces password-only `greia` authentication;
- root SSH remains denied;
- Ed25519 host identity generation is present;
- DHCP policy exists for wired and wireless interfaces;
- the target payload is explicitly marked as a development image;
- the embedded installed-system GRUB policy contains the dev-only `console=tty1`, `panic=0`, `loglevel=4` and visible systemd-status contract.

A build that fails these checks is not ready to flash.

### Preferred physical Acer workflow: build and flash in one command

To avoid the separate human/agent step that previously allowed a fresh image to be built but an old USB key to remain in use, prefer:

```bash
sudo bash tools/build-and-flash-development-usb.sh \
  legacy-x86-i686-dev \
  /dev/sdX
```

Replace `/dev/sdX` with the **whole removable USB device** discovered on the build machine. The command destroys that removable device.

This wrapper deliberately separates writing from verification:

1. refuses a non-removable/non-whole-disk target before starting the long build;
2. builds the explicit development installer;
3. runs the live+target SSH artifact verifier;
4. calls the unchanged `tools/build-live-usb.sh` to create the Acer-proven Syslinux/FAT32 media rather than raw-flashing the GRUB installer image;
5. after the writer has finished and synced the stick, calls `tools/verify-live-usb.sh`;
6. the verifier checks the FAT filesystem **read-only**;
7. it mounts the actual USB key read-only and byte-compares kernel, initrd, live squashfs, target payload, Syslinux config and live-media identifier with the verified source image;
8. it verifies `ldlinux.sys`, the active partition flag and the first 440 bytes of the Syslinux MBR bootstrap;
9. it refuses any Syslinux entry with `console=null` (fatal on the Debian 686 kernel: no `ttynull`, PID 1 has no console and panics), and a recovery template that reintroduces timed panic reboot, `quiet`/`splash`/`loglevel=0`, or any `DISPLAY` line (the recovery/diagnostic path must stay observable). Since the owner decision 2026-10-18 it additionally requires the quiet template and quiet media to carry the approved one-byte `clear.msg` display file, byte-compared at read-back;
10. reports success only after the final removable media itself passes read-back.

The reason for keeping verification separate is architectural, not cosmetic: `tools/build-live-usb.sh` is the firmware-sensitive recipe established by `INSTALLATION_USB_BOOT_POSTMORTEM.md`. Safety checks should surround that recipe rather than continuously modifying it.

A successful final run must include:

```text
Developer installer artifact verification: PASS
Greia live USB read-only verification: PASS
usb_readback_verification=PASS
source_artifact_verification=PASS
usb_flash_readback_verification=PASS
panic_policy=halt-on-panic
```

Do not flash the intermediate ext/GRUB installer `.img` directly onto the reference Acer USB and assume that is equivalent. The physically proven Acer removable-media boot path remains Syslinux + active FAT32, produced by `tools/build-live-usb.sh` or the combined wrapper above.

### Recovery-pass visibility rule

For the current physical Acer recovery pass, early boot visibility is intentional and required:

```text
console=tty1
panic=0
loglevel=4
systemd.show_status=true
rd.systemd.show_status=true
```

The recovery Syslinux line intentionally omits `quiet`, `splash` and `loglevel=0`. `panic=0` means a fatal kernel/initramfs/live-boot failure remains on screen instead of rebooting after a timeout. On the recovery/diagnostic media never clear Syslinux output and never replace the console with `console=null`. The separate quiet release-candidate path may clear the stock banner with the owner-approved `clear.msg` display file (2026-10-18) because it keeps `console=tty1` and `panic=0`, so emergency output is still printed; its media and verifier enforce the exact byte.

This is a development/recovery contract, not the final child-facing presentation design. The installer USB postmortem established that observable Syslinux/kernel/live-boot output is what distinguishes a bootloader failure from kernel/initramfs/live-media failure. Child-visible console suppression remains a later release UX goal and must be reintroduced only as a separately accepted boot-critical change.

## 4. Runtime SSH bootstrap contract

Development images need SSH specifically because graphical boot failures must remain diagnosable on physical hardware.

Greia ships a developer sshd pre-start bootstrap in both roots:

```text
build/overlay/usr/local/lib/greia-os/prepare-developer-ssh
build/installer-overlay/usr/local/lib/greia-os/prepare-developer-ssh
```

with matching `ssh.service` drop-ins.

Immediately before Debian's canonical `sshd -t` validation, the helper:

1. proves that this is an explicitly provisioned development SSH configuration;
2. proves the `greia` account exists and is password-enabled;
3. rewrites Greia-owned sshd drop-ins to the unambiguous development policy:

   ```text
   PasswordAuthentication yes
   KbdInteractiveAuthentication no
   AuthenticationMethods password
   PermitRootLogin no
   AllowUsers greia
   ```

4. generates one Ed25519 host key on the booted machine/live system when no machine-local host identity has yet been prepared;
5. retains that identity across ordinary sshd restarts, avoiding needless client `known_hosts` churn;
6. evaluates `sshd -T` and fails before sshd starts unless the **effective** configuration still allows password authentication for `greia`, requires exactly `password`, denies root, and uses the expected host key;
7. lets Debian run canonical `sshd -t` syntax/key validation immediately afterward.

The historical configuration:

```text
AuthenticationMethods publickey,password
```

was incorrect because the comma requires both methods in sequence. It must never again be treated as the Greia development recovery contract.

The historical active developer-image helper also generated a separate `greiaadmin` client keypair. That key-based workflow has been removed from the active `build/build-developer-image.sh` path. Active development builders now converge on one recovery model: the `greia` account using the simple development password. Only the server gets an automatically generated host identity.

## 5. Installer networking is explicit

The live installer must not rely on Debian package presets to happen to make SSH reachable.

`greia-installer.service` therefore explicitly wants:

```text
iwd.service
systemd-resolved.service
systemd-networkd.service
avahi-daemon.service
```

and the live installer ships the same bounded DHCP policies used by Greia's installed platform for wired and wireless interfaces.

The `developer-remote` package set explicitly carries Avahi/mDNS support so `greia-installer.local` is a declared recovery feature rather than an accidental dependency.

On Wi-Fi, SSH becomes reachable after the installer has associated to a network. Wired DHCP can become reachable without interacting with the Wi-Fi page.

## 6. First probes from another machine

For the live installer:

```bash
ping -c 3 greia-installer.local
nc -vz greia-installer.local 22
ssh greia@greia-installer.local
```

For the installed Acer dev OS:

```bash
ping -c 3 greia-dev.local
nc -vz greia-dev.local 22
ssh greia@greia-dev.local
```

Use the development password documented above when prompted.

### Result interpretation

- `ping` works, TCP/22 connects: Linux networking is alive and sshd is listening.
- `ping` works, TCP/22 says connection refused: Linux is alive but sshd is not listening/failed.
- TCP/22 connects but password authentication fails: this violates the development-image contract; capture `ssh.service` journal and effective sshd config.
- no network response: this does not prove root mount failed; Wi-Fi may not have associated, DHCP may not have completed, firmware may be missing, or userspace may have failed earlier.

## 7. Once SSH works: collect the boot evidence first

Do not immediately edit services. Capture what failed:

```bash
sudo systemctl --failed --no-pager
sudo systemctl status \
  greia-first-boot.service \
  greia-launcher.service \
  ssh.service \
  systemd-networkd.service \
  iwd.service \
  avahi-daemon.service \
  --no-pager -l

sudo journalctl -b \
  -u greia-first-boot.service \
  -u greia-launcher.service \
  -u ssh.service \
  --no-pager -n 400

sudo journalctl -b -p warning..alert --no-pager

sudo ls -la /tmp/.X11-unix /tmp/.X0-lock 2>/dev/null || true
sudo tail -n 250 /var/log/Xorg.0.log 2>/dev/null || true
```

Also record:

```bash
cat /etc/greia-os/build-info
cat /etc/greia-os/base-system-manifest
cat /etc/greia-os/install-record.json
uname -a
ip address
networkctl --no-pager
```

Do not include Wi-Fi credentials or private host-key material in returned evidence.

## 8. High-value launcher checks

The current provisional graphical path is:

```text
graphical.target
  -> greia-launcher.service
     -> ExecStartPre prepare-launcher-vt
     -> xinit
        -> greia-x-session
           -> greia_platform.hardware_session
           -> greia_launcher.child_shell
```

The unit intentionally owns VT1 and currently uses the provisional Xorg compatibility backend. Important source files:

```text
build/overlay/etc/systemd/system/greia-launcher.service
build/overlay/usr/local/lib/greia-os/prepare-launcher-vt
build/overlay/usr/local/lib/greia-os/greia-x-session
build/overlay/etc/X11/Xwrapper.config
```

If `greia-launcher.service` is failing/restarting, preserve its journal and Xorg log before changing anything.

## 9. If SSH is unavailable on an older installed image

An older development image may predate the hardened SSH bootstrap. In particular, historical images could have both of these defects:

1. `/etc/ssh/ssh_host_*` removed during image personalization with no boot-time regeneration;
2. `AuthenticationMethods publickey,password`, accidentally requiring both a public key and password.

Do not conclude "Linux never reached systemd" merely because SSH is unavailable.

For an old installation, the cleanest recovery path is normally to boot the current development installer/live environment, mount the installed root, and inspect its persistent journal/configuration. Do not copy SSH host private keys from another machine.

## 10. Evidence boundary

A source-level, artifact-level or USB read-back PASS is not physical boot evidence. After changing boot/session/SSH behavior, validation still requires a fresh install on the target Acer and a second supported machine where applicable.

For the immediate Acer recovery acceptance, record at minimum:

- exact source SHA used for the build;
- development source-artifact verification completes;
- final Syslinux/FAT32 USB read-only verification completes;
- visible Syslinux/kernel/live-boot progression or exact last visible line on failure;
- **no timed reboot on fatal live/install boot failure** (`panic=0` on dev recovery paths);
- language selector is first and its mouse pointer works;
- selecting Italian makes the following installer flow Italian;
- live installer resolves/replies as `greia-installer.local` or via its DHCP IP;
- live installer TCP/22 opens and `greia` password login succeeds;
- installation completes;
- installed development boot remains observable on tty1 if it fails;
- installed `greia-dev.local` resolves or its DHCP IP is found;
- installed TCP/22 opens and `greia` password login succeeds;
- `systemctl --failed`;
- `greia-launcher.service` journal;
- Xorg log when graphical startup fails;
- final launcher-visible result.

Splash presentation polish is **not** part of the recovery gate. The 2026-08-20 regression demonstrated that full-colour/raw-raster, Syslinux-cleanup and GRUB-theme changes must be reintroduced one narrow stage at a time only after boot viability has been re-proven.
