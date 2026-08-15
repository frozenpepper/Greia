# Greia — Developer Remote Control and Test Console

**Date:** 2026-08-09  
**Status:** source-implemented / runtime-UNPROVEN  
**Scope:** explicit development images only  
**Production impact:** normal/release Greia remains SSH-disabled and does not register the developer Activity source

---

## 1. Goal

A Greia development machine should behave like a remotely controllable appliance.

After the machine has been installed and powered on, normal development/testing should be possible from the operator computer without touching the netbook:

- detect when Greia is ready on the LAN;
- inspect platform/service status;
- obtain the actual current display as a PNG screenshot;
- inject bounded keyboard, mouse and text input for GUI testing;
- upload, validate, install, update and remove developer Activities;
- deliberately replace and later restore a built-in Activity when testing platform-integrated Activities;
- inspect bounded system/launcher/parent/network/SSH logs;
- restart the Greia launcher;
- reboot or power off the machine;
- use an explicit SSH maintenance shell when typed controls are insufficient.

This is a **developer/test surface**, not a child feature and not a production remote-management architecture.

---

## 2. Hard separation from normal Greia

The developer profile is:

```text
build/profiles/modern-amd64-dev.toml
```

It is explicitly `experimental` and includes:

```text
developer-remote
```

The normal `modern-amd64` profile does not.

Remote control requires all of the following:

1. an explicit developer profile;
2. `/etc/greia-os/developer-remote` provisioned into the image;
3. a provisioned SSH public key;
4. the developer remote preparation service;
5. the root-owned developer display endpoint descriptor.

Normal/release images therefore do not become remotely accessible merely because the source tree contains developer tooling.

Do not add `developer-remote` to a release profile.

---

## 3. Build the installed developer image

Use the canonical image builder through the development wrapper on a controlled Debian/Ubuntu Linux build host:

```bash
sudo bash build/build-developer-image.sh out
```

The wrapper first calls:

```text
build/build-image.sh modern-amd64-dev
```

and then performs bounded developer-only provisioning. It is not a second OS builder.

Expected developer artifacts include:

```text
out/greia-os-modern-amd64-dev.img
out/greia-os-modern-amd64-dev-ssh-key
out/greia-os-modern-amd64-dev-ssh-key.pub
out/greia-os-modern-amd64-dev-developer-remote.json
```

The private key is operator credential material. It must not be committed to Git, pasted into documentation, or copied into the Greia image.

The public half is installed into:

```text
/var/lib/greia-admin/.ssh/authorized_keys
```

The image deliberately contains no persistent SSH host keys. The actual netbook generates its own host identity at first boot.

---

## 4. Network identity

The installed developer profile hostname is:

```text
greia-dev
```

With Avahi/mDNS functioning on the local LAN, the expected operator hostname is:

```text
greia-dev.local
```

The development-only preparation service establishes an explicit wired policy:

```text
Ethernet -> DHCP
IPv6 RA -> enabled
mDNS -> enabled
```

It restarts networkd/resolved before SSH starts.

**Recommended first remote acceptance: use wired Ethernet.**

`iwd` is present for Wi-Fi work, but this development path does not currently embed Wi-Fi credentials. Do not solve this by committing an SSID/password to the repository. A future credential-injection path must accept local secret material at build/provision time and keep it outside Git/evidence bundles.

---

## 5. SSH security model

Remote transport uses the existing hardened OpenSSH policy:

```text
user: greiaadmin
PasswordAuthentication no
KbdInteractiveAuthentication no
AuthenticationMethods publickey
PermitRootLogin no
X11Forwarding no
AllowTcpForwarding no
PermitTunnel no
```

The `greiaadmin` password remains locked. Public-key login is the intended authentication method.

Passwordless sudo is deliberately restricted to exactly:

```text
/usr/local/sbin/greia-devctl
```

The Mac/client helper does not use `sudo sh`, `sudo bash`, unrestricted `sudo`, or a generic privileged command API.

An interactive SSH shell is intentionally available under `greiaadmin` for development/recovery, but privileged product operations should normally use `greia-devctl` so automated tests do not encode arbitrary filesystem/systemd implementation details.

---

## 6. Operator helper

From the Greia repository on the operator machine:

```text
tools/greia_remote.py
```

Defaults:

```text
host: greia-dev.local
user: greiaadmin
key: out/greia-os-modern-amd64-dev-ssh-key
known-hosts: ~/.greia/known_hosts
```

SSH uses batch/key authentication and a dedicated Greia known-hosts file.

Wait for power-on/boot:

```bash
python3 tools/greia_remote.py wait --timeout 180
```

Inspect state:

```bash
python3 tools/greia_remote.py status
```

Open explicit maintenance shell:

```bash
python3 tools/greia_remote.py shell
```

---

## 7. Screenshots

Capture the actual current Greia screen to the operator computer:

```bash
python3 tools/greia_remote.py screenshot out/screen.png
```

Current R7 compatibility implementation:

```text
SSH/root devctl
 -> root-owned developer display endpoint
 -> run screenshot helper as greiakid
 -> DISPLAY=:0
 -> Pillow ImageGrab/X11
 -> PNG bytes over SSH
 -> local file
```

The SSH user is not given arbitrary X authority.

This screenshot backend is **development compatibility code for the current Xorg session**, not a decision to retain X11. When R7 changes the display backend, the implementation below the developer display/session seam must change while the operator command remains stable.

Runtime acceptance must prove that the installed Pillow/X11 backend captures the real framebuffer content correctly on the Acer/netbook.

---

## 8. Remote GUI input

The developer image includes `xdotool` only in the explicit developer package set.

Supported operator commands:

```bash
python3 tools/greia_remote.py key Return
python3 tools/greia_remote.py key Escape
python3 tools/greia_remote.py mousemove 500 300
python3 tools/greia_remote.py click
python3 tools/greia_remote.py click 3
python3 tools/greia_remote.py type "hello"
```

The privileged helper cannot supply an arbitrary executable. The implementation always executes the fixed `/usr/bin/xdotool` binary as the declared display-session user and bounds:

- key expressions;
- number of key expressions;
- mouse coordinates;
- mouse button numbers;
- typed-text length and line shape.

This is sufficient to remotely exercise the profile picker, Activity launcher and Activities on the current Xorg developer image.

It is not a production input architecture. R7's eventual Greia-owned input/session path must replace this compatibility implementation.

---

## 9. Developer Activity deployment

Upload a normal test Activity:

```bash
python3 tools/greia_remote.py deploy path/to/activity
```

The client:

1. uploads to a `greiaadmin`-owned temporary directory;
2. calls only `sudo -n /usr/local/sbin/greia-devctl deploy-activity ...`;
3. revalidates the package using the real ActivityRegistry/runtime catalogue;
4. records it as `DEVELOPER_UNSIGNED`;
5. refuses privileged permission requests for an ordinary developer deployment;
6. moves the accepted package into:

```text
/var/lib/greia-developer/activities/<activity-id>
```

7. seals the deployed package read-only;
8. restarts the launcher.

The launcher registers this root as a separate:

```text
PackageTrust.DEVELOPER_UNSIGNED
```

source. The built-in root remains:

```text
/opt/greia-os/activities
PackageTrust.BUILT_IN
```

Remote file placement therefore cannot upgrade package trust.

The two roots may not be identical or nested.

Remove an ordinary developer deployment:

```bash
python3 tools/greia_remote.py remove <activity-id>
```

---

## 10. Deliberate built-in replacement

Testing a platform-integrated built-in may require replacement of the installed built-in copy:

```bash
python3 tools/greia_remote.py deploy path/to/activity --replace-system
```

This is intentionally explicit.

The tool:

- requires the Activity ID to already identify an installed system Activity;
- refuses an ordinary developer copy with the same ID;
- moves the original built-in package into a root-only backup;
- validates the replacement with built-in trust semantics only because the operator explicitly requested system replacement;
- installs the replacement read-only;
- records the original backup path.

Restore the original:

```bash
python3 tools/greia_remote.py restore <activity-id>
```

Do not use `--replace-system` for normal third-party/developer Activities.

---

## 11. Logs, service control and power

Launcher logs:

```bash
python3 tools/greia_remote.py logs --service launcher --lines 500
```

Other bounded groups include:

```text
parent
ssh
developer-remote
network
installer
all
```

Restart installed Greia Shell:

```bash
python3 tools/greia_remote.py restart
```

The client also has a `restart-installer` command for the planned remotely operated developer live installer.

Reboot or shut down:

```bash
python3 tools/greia_remote.py reboot
python3 tools/greia_remote.py poweroff
```

A reboot/poweroff may terminate SSH before it can return status; the client explicitly treats that transport disconnect as an expected outcome of a successful power transition request.

---

## 12. Live graphical installer: designed but not yet integrated into the canonical USB artifact

Source now includes:

```text
tools/provision_developer_installer.py
```

Its intended role is to provision the **existing graphical installer live root** for developer media with:

- the same operator public key as the installed target;
- `greiaadmin` key-only SSH;
- host identity generated at live boot rather than cloned;
- hostname `greia-installer-dev.local`;
- wired DHCP + mDNS;
- a developer display endpoint of `root@:0`, matching the current root-owned installer X session;
- screenshot/input/log/restart controls through the same `greia-devctl` surface.

Critically, it does **not** add an unattended install or disk-wipe command. The operator would remotely drive the existing graphical installer, preserving its eligible-target checks, payload verification, device revalidation and confirmation flow.

### Current boundary

The provisioner is source-implemented and unit-contract coverage is committed, but it is **not yet wired into `build/build-installer-image.sh`**.

Reason: the installer builder creates both a target raw image and a live Debian root and is destructive-media-sensitive. Adding provisioning at the two correct points should be a very small change, but that change must be made and exercised on a real Linux builder rather than hidden inside an untested post-processing wrapper.

Therefore, do not claim that first-time Greia USB installation is remotely operable yet.

Current installed developer-image remote control can be tested independently once a dev image is installed by an existing safe path.

---

## 13. Intended future remote installation flow

Once the canonical installer hook is implemented and Linux-accepted, the intended flow is:

```text
create modern-amd64-dev installer media
 -> boot USB on netbook
 -> operator waits for greia-installer-dev.local
 -> screenshot installer from Mac
 -> drive graphical installer with key/mouse controls
 -> installer performs normal target/payload safety checks
 -> installation completes
 -> reboot
 -> installed machine appears as greia-dev.local
 -> operator continues with the same client private key
```

The live USB and installed target use different hostnames and generate independent SSH host keys, avoiding known-host identity collision while using the same operator client key.

---

## 14. Test/acceptance requirements

Source tests are not hardware proof.

Before this capability is labelled accepted, a real developer image should prove at minimum:

1. normal `modern-amd64` still has SSH disabled and no developer marker;
2. `modern-amd64-dev` boots with unique machine SSH host keys;
3. password login fails;
4. root SSH login fails;
5. operator key login as `greiaadmin` succeeds;
6. wired DHCP comes up without local interaction;
7. `greia-dev.local` resolves from the operator machine where LAN mDNS permits it;
8. `status` works;
9. screenshot returns the actual visible screen;
10. keyboard/mouse/text controls drive the expected UI;
11. ordinary Activity deployment appears with `DEVELOPER_UNSIGNED` trust and cannot request privileged permissions;
12. built-in collision is refused without `--replace-system`;
13. explicit built-in replacement and restore preserve the original;
14. launcher restart recovers to the graphical shell;
15. reboot disconnects and the machine becomes remotely available again;
16. developer SSH/control does not appear in normal/release images.

Later, once the live installer hook is integrated, add remote graphical-install acceptance without weakening any destructive-device invariant.

---

## 15. No GitHub-hosted execution

This developer workflow does not authorize GitHub Actions.

Build/test it on a local or otherwise explicitly owner-approved Linux environment. GitHub remains the source-persistence/review system.
