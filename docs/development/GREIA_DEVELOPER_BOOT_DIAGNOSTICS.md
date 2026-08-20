# Greia Developer Boot Diagnostics

**Status:** living developer/operator guide  
**Date:** 2026-08-20

This guide covers development-image diagnosis when an installed Greia machine does not reach the child launcher. It does not change release UX: normal/release Greia must remain consoleless and must not expose development SSH.

Normative boot architecture remains in `docs/design/GREIA_BOOT_EXPERIENCE.md`; the historical Acer investigation is preserved in `docs/INSTALLED_OS_BOOT_POSTMORTEM.md`.

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

Development images deliberately use `console=tty1` so a panic can remain observable, while still retaining `quiet`, `systemd.show_status=false` and `rd.systemd.show_status=false`. Therefore, after root mount, systemd may continue starting services without printing ordinary unit progress. If the graphical launcher/Xorg path then fails, VT1 can simply remain showing the last filesystem line indefinitely.

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

For `legacy-x86`, it deliberately routes through `build/build-legacy-x86-sd-installer.sh`, because that is the physical-hardware front door that regenerates the boot derivatives from the canonical full-color frame before building. It then invokes:

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
- the target payload is explicitly marked as a development image.

The legacy front door also runs this verifier itself whenever the selected profile is `*-dev`. Therefore bypassing the convenience wrapper does not bypass the SSH artifact gate.

A build that fails these checks is not ready to flash.

### Preferred physical Acer workflow: build and flash in one command

To avoid the separate human/agent step that previously allowed a fresh image to be built but an old USB key to remain in use, prefer:

```bash
sudo bash tools/build-and-flash-development-usb.sh \
  legacy-x86-i686-dev \
  /dev/sdX
```

Replace `/dev/sdX` with the **whole removable USB device** discovered on the build machine. The command destroys that removable device.

This wrapper:

1. refuses a non-removable/non-whole-disk target before starting the long build;
2. builds the explicit development installer;
3. runs the live+target SSH artifact verifier;
4. calls `tools/build-live-usb.sh` to create the Acer-proven Syslinux/FAT32 media rather than raw-flashing the GRUB installer image;
5. refuses to overwrite a removable device that currently has mounted filesystems;
6. verifies the final FAT filesystem read-only;
7. re-mounts the **actual USB key** read-only and byte-compares its kernel, initrd, live squashfs, target payload, Syslinux config, clear-screen message and live-media identifier with the verified source image;
8. verifies `ldlinux.sys` and the first 440 bytes of the Syslinux MBR bootstrap;
9. reports success only after the final removable media itself passes read-back.

A successful final run must include:

```text
Developer installer artifact verification: PASS
Developer SSH artifact verified: 1
usb_flash_verification=PASS
source_artifact_verification=PASS
usb_flash_readback_verification=PASS
```

Do not flash the intermediate ext/GRUB installer `.img` directly onto the reference Acer USB and assume that is equivalent. The physically proven Acer removable-media boot path remains Syslinux + active FAT32, produced by `tools/build-live-usb.sh` or the combined wrapper above.

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

For Acer development acceptance, record at minimum:

- development source-artifact verification completes;
- final Syslinux/FAT32 USB read-back verification completes;
- language selector is first and its mouse pointer works;
- selecting Italian makes the following installer flow Italian;
- corrected full-color/aspect-preserving splash behavior is observed;
- live installer resolves/replies as `greia-installer.local` or via its DHCP IP;
- live installer TCP/22 opens and `greia` password login succeeds;
- root filesystem reaches the clean line after install;
- installed `greia-dev.local` resolves or its DHCP IP is found;
- installed TCP/22 opens and `greia` password login succeeds;
- `systemctl --failed`;
- `greia-launcher.service` journal;
- Xorg log when graphical startup fails;
- final launcher-visible result.
