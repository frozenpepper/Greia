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

## 2. Development hostname and first probes

The Acer development profile currently uses:

```text
hostname = greia-dev
```

and enables DHCP/mDNS networking.

From another machine on the same LAN:

```bash
ping greia-dev.local
nc -vz greia-dev.local 22
ssh -vvv greia@greia-dev.local
```

The owner-approved development account is:

```text
username: greia
password: greia
```

If `.local` resolution is unavailable, find `greia-dev` in the router/DHCP lease table and probe its IP directly.

### Result interpretation

- `ping` works, TCP/22 connects: Linux networking is alive and sshd is listening.
- `ping` works, TCP/22 says connection refused: Linux is alive but sshd is not listening/failed.
- TCP/22 connects but authentication fails before a password can be accepted: inspect the development sshd policy.
- no network response: this does not prove root mount failed; Wi-Fi may not have associated, DHCP may not have completed, firmware may be missing, or userspace may have failed earlier.

## 3. Current developer SSH bootstrap contract

Development images need SSH specifically because graphical boot failures must remain diagnosable on physical hardware.

The sealed target image intentionally carries **no reusable SSH host keys**. Reusing host identity across cloned images would be incorrect.

Greia therefore ships a development-only sshd pre-start bootstrap:

```text
build/overlay/usr/local/lib/greia-os/prepare-developer-ssh
build/overlay/etc/systemd/system/ssh.service.d/10-greia-developer-bootstrap.conf
```

and the equivalent files in `build/installer-overlay/`.

Immediately before Debian's canonical `sshd -t` validation, the helper:

1. verifies that this is an explicitly marked development SSH configuration;
2. runs `ssh-keygen -A`, generating only missing host keys on the actual machine;
3. repairs the historical `AuthenticationMethods publickey,password` typo to `AuthenticationMethods any` for that development configuration;
4. then lets `sshd -t` validate the final configuration before sshd starts.

`publickey,password` means both methods are required in sequence. The Greia development contract supplies no preinstalled authorized key and intends the `greia` / `greia` password recovery login to work, so the development configuration must not require that unintended two-stage authentication.

Normal/release images remain different:

- `ssh.service` is disabled;
- the managed `greia` account remains password-locked unless explicitly provisioned as development;
- `PasswordAuthentication no`;
- `KbdInteractiveAuthentication no`;
- root SSH denied.

## 4. Once SSH works: collect the boot evidence first

Do not immediately edit services. Capture what failed:

```bash
sudo systemctl --failed --no-pager
sudo systemctl status \
  greia-first-boot.service \
  greia-launcher.service \
  ssh.service \
  systemd-networkd.service \
  iwd.service \
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

Do not include Wi-Fi credentials, private key material, or other secrets in returned evidence.

## 5. High-value launcher checks

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

## 6. If SSH is unavailable on an older installed image

An older development image may predate the SSH bootstrap above. In particular, earlier images could have both of these defects:

1. `/etc/ssh/ssh_host_*` removed during image personalization with no boot-time regeneration;
2. `AuthenticationMethods publickey,password`, accidentally requiring both a public key and password.

Do not conclude "Linux never reached systemd" merely because SSH is unavailable.

For an old installation, the cleanest recovery path is normally to boot the current development installer/live environment, mount the installed root, and inspect its persistent journal/configuration. If manually repairing that old target for diagnosis, generate unique host keys on the target (`ssh-keygen -A` in the target environment) and correct the development-only authentication policy before starting sshd. Do not copy host private keys from another machine.

## 7. Evidence boundary

A source-level fix is not physical evidence. After changing boot/session/SSH behavior, validation still requires a fresh image/install on the target Acer and a second supported machine where applicable.

For the Acer development acceptance, record at minimum:

- whether root filesystem reaches the clean line;
- whether `greia-dev.local` resolves;
- whether TCP/22 opens;
- whether `greia` / `greia` login succeeds;
- `systemctl --failed`;
- `greia-launcher.service` journal;
- Xorg log when graphical startup fails;
- final launcher-visible result.
