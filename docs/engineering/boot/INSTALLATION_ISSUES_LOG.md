# Greia OS Installation & Boot Issues Log

**Status:** accepted engineering record, reconciled with build tree  
**Date:** 2026-08-18  
**Audience:** platform developers, install/boot engineers, reviewers, agents  
**Scope:** failures encountered while bringing the Greia installer and installed OS up on legacy physical hardware, plus the hardware-independent engineering lessons that now protect future builds.

> The Acer Aspire One used during this tranche was the machine that exposed the
> defects. It is **not** the scope of the fixes. The rules below are written so a
> clean Greia build made on different hardware does not rely on the build host
> resembling its eventual target.

---

## 1. Installer `BOOT FAILED` after probing the live medium

**Symptom:** the Greia live installer mounted and unmounted the removable medium,
then `live-boot` reported that it could not find a medium containing a live file
system.

**Root cause:** `live-boot` identity matching requires the initramfs media ID to
match `.disk/live-uuid` on the removable medium. The hand-assembled medium had
the kernel/initrd/squashfs but not that identity marker, so it was probed and
rejected.

**Fix / invariant:**

- the official media builder creates `.disk/live-uuid` from the same generated
  ID passed to the initramfs as `greia.live_media_id`;
- the media identity, live filesystem and installation payload are treated as
  one build product;
- `tests/test_installation_hardware_regressions.py` locks the marker and payload
  paths together.

**Hardware note:** the tested Acer BIOS would not boot from its SD reader and did
not execute the tested USB stick's GRUB MBR reliably. A clean FAT32 active
partition with syslinux booted successfully. That is a firmware/media-adapter
compatibility observation, not a reason to make syslinux universal policy for
all Greia hardware. The full narrative — every attempt, the antiX toolchain
analysis, and the final working recipe — is documented separately in
`INSTALLATION_USB_BOOT_POSTMORTEM.md`.

---

## 2. Installed system grey-screened and rebooted in a loop

**Symptom:** GRUB loaded Greia, the screen went grey, and the machine rebooted
repeatedly.

**Root cause:** the regenerated installed initramfs did not contain the generic
SATA/AHCI root-disk stack (`ahci`, `libata`, `sd_mod`). The image was assembled
in a chroot/VM that could not probe the eventual laptop's storage controller, so
host-derived dependency selection was not valid target-hardware authority.
With no root disk, the kernel could not mount the filesystem; the appliance
kernel command line intentionally hid the panic and rebooted.

**Fix / invariant:** both target and live image inputs now use a target-aware
policy rather than either build-host probing or unconditional x86 module lists:

1. `MODULES=most` provides the broad generic initramfs driver set;
2. executable `greia-storage-modules` hooks inspect the **target kernel** with
   `modinfo -k "$version"`;
3. when that target kernel provides `ahci`, `libata`, or `sd_mod`, the hook calls
   `manual_add_modules` so the x86 SATA/AHCI root-storage floor is guaranteed;
4. shared `/etc/initramfs-tools/modules` files remain architecture-neutral and
   do not hardcode x86-only names onto future ARM/board images.

The regression suite requires the same target-kernel-aware policy in both live
and target overlays.

**Important correction to the earlier log:** commit `de6299e` added installed
GRUB/root-UUID/kernel/initrd **boot-config verification**; it did not inspect the
contents of the generated initramfs. The target-kernel-aware storage policy
prevents the specific host-probing omission structurally. As of 2026-09-28 the
legacy installer also inspects the **regenerated target initramfs itself** after
`update-initramfs`: every `ahci`, `libata` or `sd_mod` driver that the
target kernel exposes as a module must be present in that initrd before GRUB is
written or the installer may report completion. This turns the historical
post-install grey-screen/reboot loop into an installer-time failure.

**General lesson:** never let the hardware visible to the build VM/chroot decide
whether a boot-critical target driver exists, and never solve that mistake by
putting one architecture's module names into a shared cross-architecture
overlay. Compatibility-profile/target-kernel policy must own the decision.

The full chronological account of this boot-loop — every diagnostic used
(`break=top`, `/proc/modules`, `find / -name '*.ko'`, persistent journald,
stderr capture), the reason the static checks misled us, and the complete
fix sequence through to the working launcher — is documented in
`INSTALLED_OS_BOOT_POSTMORTEM.md`.

---

## 3. Installer stalled at “Adding support for this computer”

**Symptom:** installer progress stopped; a child `apt-get` process was in stopped
state `T` and could not make progress.

**Root cause:** the graphical installer service had `StandardInput=tty` on tty1.
When X became the foreground process group, installer children still inherited
the terminal as stdin. A child that attempted to read from it received
**SIGTTIN** because it belonged to a background process group. The same class of
failure later affected other command-line helpers.

**Fix / invariant (updated after the 2026-09-27 physical VT proof):**

- the graphical service gives **Xorg**, and only the X-server side of the
  session, a real controlling tty1 via `TTYPath=/dev/tty1` and
  `StandardInput=tty-fail`; this is required for the unprivileged service to
  activate the VT and fails closed rather than stealing an occupied terminal;
- the xinit graphical client (`greia-installer-client` or
  `greia-x-session`) immediately redirects its own stdin to `/dev/null`
  **before** starting the installer/launcher application, so the application
  tree and every descendant still cannot read the VT and receive SIGTTIN;
- installer subprocess execution independently keeps
  `stdin=subprocess.DEVNULL`;
- hardware regressions require both halves of the invariant: X owns tty1,
  application descendants do not inherit tty stdin.

The earlier `StandardInput=null` unit-level workaround is historical and must
not be restored: it prevented SIGTTIN but also denied Xorg the controlling VT,
which the reference Acer later proved makes the graphical service fail before
the UI appears.

**General lesson:** VT ownership belongs to the display server; terminal stdin
does not belong to the graphical application tree. Preserve those as separate
contracts.

---

## 4. “installation payload not found”

**Symptom:** the live installer itself started but could not find the target OS
payload.

**Root cause:** the hand-built medium contained the files needed to boot the
live environment but omitted `payload/pip-rootfs.squashfs`, its digest and
`target-image-profile.json`.

**Fix / invariant:** the official media contract emits and verifies the complete
payload set with the live boot files. Custom-media runbooks/tools must copy the
contract as a whole, never a remembered subset.

---

## 5. SSH developer bootstrap diverged from the security architecture

**Observed problem:** remote developer access was unreliable during hardware
work, and older builder paths compensated by writing a known `greia/greia`
password and permissive root/password SSH configuration. Separately, image
personalization removes host keys so cloned machines do not share SSH identity.

**Root cause:** two concepts became conflated:

- **normal/release images:** SSH is disabled; host keys are intentionally absent
  until a future parent-owned enablement path exists;
- **developer images:** the supported provisioning architecture was key-only
  `greiaadmin`, root/password SSH disabled, with per-machine host keys generated
  on the actual device.

A package/profile flag that installs developer prerequisites is not authority to
mint credentials or enable SSH.

**2026-08-18 owner policy amendment (active):** the owner explicitly changed
the development direction. During active development/hardware bring-up,
developer/test installations must remain reachable over SSH after installation
and reboot with the predictable login `greia` / `greia`. Root SSH login remains
disabled. Key authentication is retained as an additional automation path but
must not make the `greia` / `greia` login disappear.

**Final source fix / invariant (reconciled):**

- both target and live installer overlays contain `00-greia-security-floor.conf`;
- the shared floor denies `root` only and does not deny the managed `greia`
  account; base images keep the `greia` account password-locked and SSH off;
- `PermitRootLogin no` is always required;
- **the canonical target builder never enables SSH or mints a password** and
  always emits a closed base configuration;
- **the canonical live-installer builder likewise never creates a password or
  enables SSH**, including for a developer profile;
- developer reachability is an explicit post-build step through
  `build/build-developer-image.sh` → `tools/provision_developer_image.py`, which
  sets the `greia` / `greia` development login, keeps root denied, installs an
  operator key as an additional automation path, and rewrites the security floor
  for the developer image before enabling SSH;
- live-installer remote control is an explicit
  `tools/provision_developer_installer.py` operation that likewise enables the
  `greia` / `greia` login and keeps root SSH disabled.

`tests/test_installation_hardware_regressions.py` locks the invariant that the
canonical builders never mint credentials and that the explicit developer
provisioning path enables the owner-approved `greia` / `greia` login with root
denied.

> **2026-08-19 reconciliation:** the owner policy requires developer/test
> installs and the live installer to be reachable as `greia / greia` during
> active hardware bring-up, and a manual post-build provisioning step proved
> too easy to miss (a flashed installer once shipped with SSH off). The
> canonical builders now **detect the `developer-remote` package set in the
> profile and enable the `greia / greia` SSH login at build time** (unlock/set
> the `greia` account, rewrite the SSH floor to `AllowUsers greia` with root
> denied, enable `ssh.service`, and write `/etc/greia-os/developer-remote`).
> Normal/release profiles remain fail-closed. The explicit
> `provision_developer_*` tools remain as an additional path but are no longer
> the only way. See `docs/engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md` §4.

**General lesson:** a base builder must fail closed even if a later developer
provisioning step is interrupted. Development convenience belongs in an
explicit privileged provisioning stage, not in the reproducible base image. An
owner policy change that redefines development credentials is a contract
migration for source, tests, and living documentation together, not a reason to
keep two competing instructions.

---

## 6. `greia-launcher.service` failed with status `226/NAMESPACE`

**Symptom:** launcher failed before its pre-start helper with a missing
`/run/greia-os` path.

**Root cause:** `/run` is a fresh tmpfs every boot, and systemd constructs a
service namespace before `ExecStartPre`. Creating a namespace-required path from
`ExecStartPre` is therefore too late.

**Fix / invariant:** `greia-launcher.service` now uses:

```ini
RuntimeDirectory=greia-os
RuntimeDirectoryMode=0755
```

so systemd creates the path before namespace/service setup.

**General lesson:** service-owned volatile paths required during unit setup must
be declared to systemd, not lazily created by a command that runs after setup.

---

## 7. Xorg refused to start: “Only console users are allowed”

**Symptom:** Xorg.wrap rejected the launcher service and Xorg processes died.

**Root cause:** `allowed_users=console` assumes a conventional console/login
session. Greia's current provisional Xorg backend runs from a systemd-owned
appliance session and does not satisfy that desktop heuristic.

**Fix / invariant:** the current compatibility backend explicitly uses:

```text
allowed_users=anybody
needs_root_rights=yes
```

This is authority granted to the platform-owned X server, not to Activities.
Activity isolation remains in the supervisor/runtime boundary.

---

## 8. Xorg was blocked by launcher service namespace hardening

**Symptom:** even after the wrapper change, Xorg did not produce a fresh usable
session/log and the launcher restarted.

**Root cause:** desktop-daemon-style hardening (`ProtectSystem=strict`,
`ProtectHome`, `PrivateTmp` and narrow path namespaces) prevented the current
platform-owned Xorg process from opening the VT, DRM/input devices and normal
runtime/log paths.

**Fix / invariant:** those mount-namespace directives were removed from the
**current provisional Xorg-owning launcher service**. The regression suite now
forbids silently restoring them while this backend owns the display session.

This is **not** a blanket rejection of systemd hardening. A future R7 backend
must define its exact path/device contract, then apply and physically prove the
hardening compatible with that contract. Activity sandboxing is independent and
remains enforced.

---

## 9. Touchpad pointer appeared frozen

**Symptom:** launcher rendered a pointer but it did not move; Xorg/libinput
reported failure against a legacy `/dev/input/mouse*` node.

**Root cause:** one physical touchpad was represented both by a modern
`/dev/input/event*` device and a legacy mouse compatibility node. The generic
pointer InputClass matched the compatibility node and attempted to treat it as
an independent libinput device.

**Fix / invariant:** Xorg input defaults ignore `/dev/input/mouse*` before the
real touchpad/pointer classes are applied. This is deliberately based on Linux
input namespace semantics rather than a Synaptics/Acer model-name exception.

---

## 10. Activities failed to launch inside Bubblewrap

**Symptom:** Activity activation returned to the launcher; Bubblewrap reported
missing/permission-denied source or destination paths.

**Root cause:** three sandbox-topology assumptions were wrong:

1. bind destinations under the read-only root were not created first;
2. `/run` was read-only although Activity-private bind targets lived beneath it;
3. user-namespace remapping removed access needed to traverse platform-owned
   group-accessible profile sources.

**Fix / invariant:**

- Activity sandbox creates a private `--tmpfs /run`;
- required bind destinations are created with `--dir` before binds;
- the broken `--unshare-user`/`--disable-userns` assumptions were removed;
- PID/network/UTS isolation and the read-only root remain;
- the regression suite locks this mount topology.

**General lesson:** sandbox policy is both *what is inaccessible* and *how the
private filesystem is constructed*. Mount targets must exist inside that
filesystem before authority is narrowed.

---

## 11. Arrow/Enter navigation was dead in the kiosk launcher

**Symptom:** pointer input worked but keyboard navigation did not.

**Root cause:** Greia launches the current Xorg compatibility session without a
window manager. SDL window creation alone did not establish X keyboard input
focus.

**Fix / invariant:** the X11 compatibility path explicitly calls
`XSetInputFocus` for the launcher window after creation. The regression suite
requires that handoff to remain present while this backend is active.

A future R7 backend must provide the same semantic guarantee through its own
focus/session implementation.

---

## 12. Activity startup felt frozen

**Symptom:** the delay between activation and Activity presentation looked like a
hung launcher; early feedback was too weak.

**First fix:** the launcher gained an immediate full-screen “Starting…” overlay
and spinner before the expensive startup path.

**2026-08-18 refinement:** the selected tile now performs a short bounded
squiggle/bounce flourish before the existing start overlay and authoritative
launch path. The animation is presentation-only and cannot affect permissions,
package trust or lifecycle authority.

See `docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md`.

---

## 13. Installer reported the Wi-Fi card but could never list a network

**Symptom:** on the reference Acer the installer stopped reporting "no wifi card
found" after the `netdev` group repair, but the network list stayed permanently
empty. Scanning, joining and the recovery-network path were all unreachable.

**Root cause class: two network managers were configured to own the same link.**
Greia ships **no `wpa_supplicant`** — `iwd` (in `build/package-sets/installer-base.txt`
and `build/package-sets/network-basic.txt`) is the only WPA2-capable path in the
product. Both build overlays also carried `25-greia-wireless.network` with
`Name=wl*` and `DHCP=yes`, which made `systemd-networkd` claim the adapter. iwd
only publishes its `Device`/`Station` D-Bus interfaces while it holds the adapter
in **station mode**, and it will not take a link that `systemd-networkd`
manages, so the installer's iwd backend saw an `Adapter` and no `Station`.

**Hardware evidence (read over the developer SSH surface on the live Acer):**

```
/net/connman/iwd/0  ->  only net.connman.iwd.Adapter
  .Name = "phy0"   .Powered = true   .SupportedModes = "ad-hoc" "station" "ap"
  no net.connman.iwd.Device, no net.connman.iwd.Station
networkctl status wlan0: Network File = /etc/systemd/network/25-greia-wireless.network
                         State = no-carrier (configuring)   wlan0 operstate = down
```

The `netdev` grant itself was correct and effective: introspecting iwd as the
service identity (`uid=nobody` **plus group `netdev`**) succeeded. Note that
`su nobody` is *not* a valid probe — `su` does not inherit systemd's
`SupplementaryGroups`, so it fails with `Access denied` even when the real
service can reach the bus.

**Why the old policy could never have worked anyway:** bare `DHCP=yes` on a
wireless link cannot speak WPA2 without `wpa_supplicant`, so
`25-greia-wireless.network` could only ever have joined an *open* network. The
2026-08-20 "wireless recovery networking" intent (`e0eb9cd5`) was therefore
never functional for an encrypted network, while silently blinding the Wi-Fi UI.

**Fix:** the wireless link is declared explicitly **unmanaged** by
`systemd-networkd` in both overlays (`Unmanaged=yes`), rather than merely
failing to match, so a future `wl*` policy cannot silently re-claim it. Wired
DHCP is unchanged in `20-greia-wired.network`. `Unmanaged=yes` is the documented
systemd mechanism for exactly this case ("preventing later matching network files
from interfering with interfaces that are fully controlled by" another manager).

This also aligns the image with what the installer already does: it persists the
chosen iwd `.psk`/`.open` profile into the installed target
(`src/greia_installer/engine.py` — `request.wifi_profile.write_to(target_root)`),
and `iwd.service` is already enabled in the `target` role
(`build/lib/compose.sh` — `compose_configure_systemd`). Those persisted profiles
were unusable while `systemd-networkd` held the link.

**Regression-locked** by
`tests/test_installation_hardware_regressions.py::test_iwd_alone_owns_the_wireless_link_in_every_built_root`
(no `systemd-networkd` policy may claim a wireless link; wired DHCP must
survive; `wpa_supplicant` must stay absent) and by
`tests/test_boot_diagnostics_hardening.py::test_live_installer_explicitly_starts_recovery_network_services`.
Both were confirmed to fail against the previous `DHCP=yes` policy.

---

## Regression rule established by this hardware tranche

A real-hardware fix is not complete until all four conditions hold:

1. the physical machine works;
2. the authoritative build source contains the fix;
3. a hardware-independent test/invariant prevents accidental reversal;
4. documentation records the root-cause class, not just the machine-specific
   symptom.

The August 18 repository review found several cases where the hardware had been
manually fixed and the issue log described the fix, but the build overlay still
contained the old Xorg/systemd/input configuration. Those mismatches were
corrected during the review and are now explicitly regression-locked.

For the complete cross-cutting review and remaining risks, see
`2026-08-18_REAL_HARDWARE_INSTALLATION_AND_LAUNCHER_REVIEW.md` (archived; see git history).

---

## Key commits from the physical-hardware tranche

| Commit | Description |
|---|---|
| `b1c9669` | launcher: full-screen launch overlay and X input focus for kiosk keyboard |
| `51c7592` | supervisor: fix Bubblewrap sandbox mount failures breaking Activity launch |
| `de6299e` | installer: verify installed boot config root UUID and kernel/initrd before done |
| `665909d` | installer: do not give the VT as stdin to the GUI service |
| `9654d01` | installer: detach subprocess stdin to prevent SIGTTIN stall |
| `2940be1` | installer: tolerate legacy hardware defaults and guarantee frame throttle |
| `1b11c79` | installer: physical-key layout probes instead of active-layout assumptions |

Subsequent 2026-08-18 review commits persist the missing Xorg/runtime/input
build fixes, make live/target storage-module inclusion target-kernel-aware,
remove password/root SSH bootstrap behavior from both canonical builders, add
hardware-independent regression locks, and introduce the richer
launcher/Activity-package foundation. The repository history is authoritative
for the exact commit IDs of that follow-up tranche.

---

## 14. Installer Wi-Fi page reported "No networks found" although five were in range

**Symptom:** after the wireless ownership repair (§13), iwd correctly held the
adapter in station mode, yet the installer still displayed "No networks found.
Refresh, or continue offline." indefinitely.

**This was not an iwd or driver fault.** Running the shipped backend directly
on the running machine, as the service identity, returned five real networks
(`Wireless Pendente`, `Vodafone-C64216910`, `enel-WiFi_75A9E161`,
`WINDTRE-F4D0A0`, `TP-LINK_5490D2`), from both the main thread and a worker
thread. The defect was in how the result was *consumed*.

**Root cause class: a startup race whose empty result was latched, with the
failure mode hidden.** The installer reaches the Wi-Fi page within seconds of
the language screen. iwd publishes its `Station` interface only once the
adapter has settled into station mode, so an early scan can legitimately return
nothing. `WifiSetupController.drain()` treated any successful-but-empty scan as
a final `READY` state and published it, and the UI's empty-network branch drew
"No networks found" *before* considering the phase — so a genuine scan **error**
was also reported as an absence of networks. Both halves had to be fixed: the
scan had to become retried, and the error had to stop being masked.

**Fix:** an empty scan now re-scans up to `SCAN_RETRY_LIMIT` (4) times with a
short settle delay, staying in `SCANNING` rather than publishing a false
negative; and `_draw_wifi_networks` surfaces a real error instead of reporting
it as "no networks".

**Regression-locked** by
`WifiSetupScanRetryTests` in `tests/test_installer_wifi_setup.py`: an adapter
that reports empty then non-empty must end `READY` with the real networks, and
an adapter that never reports anything must stop at exactly
`SCAN_RETRY_LIMIT + 1` calls rather than spinning.

## 15. Input settings page was visually broken on the Acer

**Symptom:** on the reference Acer the Pointer Setup page drew the "Pointer
feel" subtitle on top of the "Pointer setup" title, clipped "Touchpad feel" in
half, dropped "Mouse feel" outside its own row, and overlapped the rows
themselves. Reproduced headlessly against the Acer's real fonts, so it was a
layout defect rather than a perception problem.

**Root cause class: layout measured against assumed font metrics, with a
height that omitted the header.** The development host's fonts are shorter than
the Acer's, and the page was laid out with fixed constants: a fixed `+52` title
gap, a fixed `POINTER_HEADER_H = 96`, a fixed strip tail, and row heights
clamped to a hard minimum that could be *shorter than the label font itself*.
Worse, `_pointer_vertical_budget` returned a content height that **omitted the
header**, so every fit comparison under-counted the panel by the header's full
height and let the test strip run into the Back/Continue row.

**Fix:** the header, the row floor, the strip label and the strip tail are all
measured from the fonts in use; a row can never be shorter than its own label;
and content height includes the header. When five legible rows plus the test
strip genuinely cannot fit a 600 px panel — which is provably true at the
Acer's metrics — the **strip is dropped entirely** and its space goes to the
rows, rather than letting it collide with the system navigation. No capability
is lost: the same pointer test is still reachable from the `1` `2` `3` keys,
which is why those keys exist. System navigation is still drawn when the strip
is dropped, because Home/Back chrome is platform-owned and must never vanish.

**Regression-locked** by `test_pointer_rows_never_render_a_label_outside_its_own_pill`,
`test_pointer_header_is_measured_from_the_fonts_in_use`, and the corrected
`test_pointer_page_layout_fits_the_reference_1024x600_display`, which now
measures content height from the top of the panel including the header.

## 16. ~97% CPU spin on the Acer: a failing helper respawned 2754 times per boot

**Symptom:** the installer pinned a core from boot onward.

**Root cause class: an unbounded retry loop on a permanently failing
one-shot.** `_release_boot_cover_once()` re-invoked
`/usr/local/lib/greia-os/release-boot-cover` every 0.5 s until it succeeded.
It could never succeed: the helper wrote its marker into `/run/greia-os`, which
on the live installer is created **root-owned** by the install-transaction
socket unit, while the installer runs unprivileged as `User=nobody`. The helper
exited 2 with `Permission denied`, `_boot_released` never latched, and the
retry continued for the whole session.

```
/run/greia-os           drwxr-xr-x root root       <- not writable by nobody
release-boot-cover: 10: cannot create /run/greia-os/boot-cover-released
spawns observed in one boot: 2754
```

**Fix, in two parts.** The marker moved to `/run/greia-installer`, the runtime
directory the installer unit already owns (`RuntimeDirectory=greia-installer`,
mode 0750, chowned to the service's user); verified on the running Acer as
`nobody`, which now exits 0. The installed launcher is unaffected: its
`/run/greia-os` is group-writable through tmpfiles and its own copy of the
helper keeps the original path. Independently, the retry is now **capped and
backs off**, so no helper failure can ever become a busy loop again.

**Regression-locked** by `BootCoverHandoffBoundTests`: a failing helper is
invoked at most `BOOT_HANDOFF_MAX_ATTEMPTS` times across 2000 ticks, and a
succeeding one latches after a single call.

## 17. Cross-hardware class analysis: what the Acer defects share

The §13–16 defects have no Acer-specific cause. They were re-analysed as ten
recurring classes, each researched for known instances on other hardware, and
sequenced for removal in `docs/plans/2026-09-28_CROSS_HARDWARE_ROBUSTNESS_PLAN.md`.

The class that matters most going forward is **C5, silent under-provisioning**:
the storage-module set is the fixed triple `("ahci", "libata", "sd_mod")` in both
`greia-storage-modules` and `InstallerEngine._verify_installed_initramfs_storage`.
Because the hook probes with `modinfo`, a machine whose root sits behind NVMe,
SAS/RAID, Intel RST/VMD, USB or MMC gets **no** storage module added, and the
install-time guard then passes **vacuously**. That is the same failure class as
§2, and it is latent rather than observed.

Second is **C10, single-machine evidence**: §14 was reported fixed on the strength
of source tests and a direct backend call, and only a real installer UI run
exposed that the latch was still consuming the result. Any claim whose subject is
physical hardware needs physical evidence, not source-closed evidence.

## 18. Installer could list Wi-Fi but could not join: writing into iwd's private state

**Symptom:** after the §14 repair the installer listed real networks, but
selecting one failed immediately with

```
[Errno 1] Operation not permitted: 'var/lib/iwd'
```

**Root cause class: C1 again — undeclared resource ownership, this time over a
state directory rather than a link.** `IwdWifiBackend.connect` wrote the iwd
profile straight into `/var/lib/iwd` and then asked iwd to pick it up. That
directory belongs to iwd:

```
/var/lib/iwd   root:root 700
sudo -u nobody chmod 0700 /var/lib/iwd
  -> chmod: changing permissions of '/var/lib/iwd': Operation not permitted
```

The installer runs unprivileged as `User=nobody`, so the write was impossible
by construction. §13 fixed who owns the *wireless link*; this was the same
mistake about the *state directory*.

**Fix: use iwd's own sanctioned unprivileged path — a passphrase agent.**
`IwdWifiBackend` now registers a `net.connman.iwd.Agent` object, hands iwd the
passphrase over D-Bus when it asks, and iwd persists the profile itself. The
uninstaller-side file write, its `chmod`, and its rollback dance are gone. The
agent answers **only** for the object path of the network the child selected and
cancels any other request, so a passphrase is never handed to a network that
was not chosen.

**A second consequence, found while fixing the first.**
`ProductionParentApiApplication._wifi_management_available` deliberately
withheld the `network.manage` capability unless `/var/lib/iwd` was writable.
That gate was honest under the old design and is now wrong: it would hide a
capability that genuinely works unprivileged. It is replaced by
`WifiBackend.management_available()`, which checks the real requirement — bus
reachability plus the ability to serve a D-Bus agent object — with no side
effects, so a stripped image missing PyGObject correctly withholds joining
instead of advertising it.

**Two implementation traps worth recording, both found only on the hardware:**

- `dbus.Interface(bus, path, interface)` is the newer three-argument form and
  raises `TypeError` on the image's python3-dbus. The module's existing
  `bus.get_object(...)` then `dbus.Interface(proxy, ...)` shape is the one that
  works.
- `dbus.SystemBus()` is a shared singleton that the scan path has already
  opened **without a main loop**. Exporting an object on it fails with
  "connections must be attached to a main loop". The agent therefore opens its
  own private `BusConnection` with an explicit main loop and closes it with the
  thread.

**Verified on the reference Acer** (deliberately wrong password, so the only
honest available expectation is a rejection):

```
available: True   management_available: True
WifiError: Wi-Fi connection was rejected
iwd: 4-Way handshake failed for ifindex: 4, reason: 15
/var/lib/iwd: no profile written
```

iwd received the passphrase from the agent and ran the WPA 4-way handshake, so
the agent path is proven end to end; a *successful* join still needs the real
credential and remains owner-side evidence.

**Regression-locked** by `InstallerWifiConnectOwnershipTests`: `connect` must not
create, chmod or populate iwd's state directory, and an open network must not
register a passphrase agent. Verified RED against the reintroduced write.

## 19. Wi-Fi screen reported no adapter after a reboot: a latched UNAVAILABLE state

**Symptom:** after §18 the installer could list networks and offer to join, but
on the next boot of that image the Wi-Fi screen reported no adapter and no
networking at all.

**This was not caused by §18.** The `scan()` and `drain()` code is byte-identical
between the two images (verified by comparing SHA-256 over those exact source
ranges across the two commits), and the backend returned 4–5 networks when run
directly on the running Acer as the service identity. Only `connect()` and the
Parent capability gate changed.

**Root cause class: C3 again, in the same function that §14 had already fixed
once.** `WifiSetupController.begin()` latched `UNAVAILABLE` on its first
availability check:

```python
if not self._backend.available():
    self._phase = WifiSetupPhase.UNAVAILABLE
    return
```

`UNAVAILABLE` is not in the `{IDLE, ERROR}` set that `begin()` accepts, so the
state was **permanent**. iwd publishes its Station interface only once the
adapter settles into station mode, so reaching the Wi-Fi screen even slightly
early produced a terminal verdict that no amount of waiting could undo; the
only escape was the Refresh button. A boot-timing difference is enough to flip
between "works" and "permanently dead", which is exactly the unreproducibility
this project has been fighting.

**Fix:** `begin()` no longer decides availability at all. It enters the bounded
scan-retry loop, and once the budget is spent the final state is derived from a
real availability check: no station interface after the retries means
`UNAVAILABLE`, otherwise `READY` with an empty list. A late adapter is therefore
absorbed, and a genuinely absent adapter is still reported honestly — it just
takes a few seconds to say so.

**Verified on the reference Acer:**

```
late-adapter (unavailable twice, then ready): READY, 4 networks
real adapter, normal path:                    READY, 4 networks, 0 retries
```

**Regression-locked** by `WifiSetupAdapterReadinessTests`: a late-settling
adapter must reach `READY`, `begin()` must never latch on a single early check,
and a genuinely absent adapter must still end `UNAVAILABLE` after exactly
`SCAN_RETRY_LIMIT + 1` scans. All three were confirmed RED against the restored
latch. The pre-existing `test_no_adapter_is_nonfatal` also had to be corrected:
its fake reported "no adapter" while still returning three networks, which was
only survivable while `begin()` latched before scanning. The fake is now honest.

**Lesson recorded for the class, not the instance:** §14 fixed the empty-scan
latch and this was the second latch in the same twenty lines. When a class is
identified, every instance of it in the same code must be enumerated, not just
the one the current symptom exposed.

## 20. The entire installer UI was frozen: state changes never repainted

**Symptom:** on the reference Acer nothing in the installer updated on its own.
The Wi-Fi list only appeared once the pointer moved, and the "Connecting..."
screen never advanced until the pointer moved. Owner diagnosis: "it is a view /
layout refresh issue". That was correct, and it was not Wi-Fi-specific.

**Root cause class: an optimisation whose safety net was inverted.**
`InstallerApplication.run` skips the redraw and display flip when the render
signature is unchanged, which is a legitimate optimisation on slow hardware. The
signature is meant to be uncomputable-safe: its docstring promised that "any
failure at all returns `None`, which forces a redraw" and that it "can never
leave a stale screen behind". Both promises were false:

1. `InstallerState` is declared `@dataclass(slots=True)`, so its instances have
   **no `__dict__`**. The signature walked it with `vars()`, which raised
   `TypeError: vars() argument must have __dict__ attribute` on **every frame**,
   so the signature was always `None`.
2. The remembered signature `_last_render_signature` was also initialised to
   `None`. The gate is `if handled_event or signature != self._last_render_signature`,
   and `None != None` is false, so the "forced redraw" never happened. The
   installer painted one frame and then only ever repainted in response to an
   input event — which is exactly why moving the pointer fixed it.

**Fix, in two independent parts so neither can regress alone.** Slotted
dataclasses are read through their declared fields, and a `TypeError` from
`vars()` now degrades to an empty contribution rather than poisoning the whole
signature. The initial fingerprint is a unique sentinel that no computed
signature can equal, so a genuinely uncomputable signature really does force a
redraw.

**Two further gaps the same fix exposed,** found by measuring rather than
reasoning. The scalar walk cannot see an `Enum` or a tuple of dataclasses, so
`page`, `progress`, `settings` and the Wi-Fi network list were all absent from
the fingerprint — a page change would not have invalidated either. State is now
fingerprinted field-by-field through a bounded recursive walk, with the network
list named explicitly.

**Verified on the reference Acer**, after the fix:

```
signature computable: True    first frame repaints: True
page change repaints: True    networks arriving repaints: True
connected state repaints: True
```

Measured cost on that machine: **0.33 ms per frame against a 33.3 ms budget** at
30 fps, so the added fidelity is about 1% of a frame.

**Regression-locked** by `RenderSignatureTests` (5 cases). All were confirmed to
fail against the true original code — injecting the original unguarded `vars()`
walk plus the original `None` initial value turns 4 of them red, and the sentinel
case red on its own.

**The launcher is unaffected:** it does not use a render signature and repaints
unconditionally. Worth recording, because the installer is the only surface
carrying this optimisation.

## 21. First real install died at `update-initramfs`: the install service lacked `CAP_MKNOD`

**Symptom:** the Acer install reached the point of writing the target and then
failed with the installer's own error, now visible because the repaint defect
(§20) is fixed:

```
fatal error: create_inode: failed to create character device
/tmp/pip-install-target.3vyxk7p2/dev/console. because operation not permitted
```

**Root cause class: a capability set proved sufficient only by the evidence that
was cheap to gather.** `greia-install-transaction.service` carried a
deliberately minimal set, and the unit's own comment says each capability was
added "only with executable evidence": `CAP_SYS_ADMIN` from a disposable-loop
mount/write proof, `CAP_SYS_CHROOT` from a Session-04 V12F EPERM traceback, and
`CAP_SETUID`/`CAP_SETGID` from Session-04 product-mode QEMU. Every piece of that
evidence came from a harness that stops before the end of a real install.

The step no harness reached is the one that closes an install: after the target
is written, the engine runs `chroot <target> update-initramfs -u -k all`.
`mkinitramfs` stages a fresh target under the installed system's `/tmp` and
creates its device nodes with `mknod`, which needs `CAP_MKNOD`. The service held
exactly `CAP_SETUID CAP_SETGID CAP_SYS_ADMIN CAP_SYS_CHROOT` and no `MKNOD`.

**Confirmed on the appliance, not inferred:**

```
CapEff/CapBnd/CapAmb: CAP_SETUID CAP_SETGID CAP_SYS_ADMIN CAP_SYS_CHROOT   (no MKNOD)
mknod as an unprivileged user : PermissionError [Errno 1] Operation not permitted
mknod as root                 : OK
mknod with CAP_MKNOD in the bounding set : OK
```

The unprivileged failure is byte-for-byte the reported error, which is what
distinguishes a capability check from a filesystem-permission problem.

**Fix:** `CAP_MKNOD` added to the unit's `CapabilityBoundingSet` and
`AmbientCapabilities`. It is strictly narrower than the `CAP_SYS_ADMIN` the set
already carries, so it grants no authority the service did not already hold.

**This is a systemic lesson, not a one-line fix.** The unit was made minimal by
construction, and the minimality was verified only as far as the evidence
reached. A capability set proven by a harness that cannot complete an install is
not proven for an install. The unit comment now records the Acer evidence
alongside each capability, and `InitramfsDeviceNodeCapabilityTests` locks both
the name and the stated reason, so a later pass that tidies the set back to the
QEMU-proven four fails a test instead of breaking every real install silently.
Two further tests were found asserting the old exact four-capability list and
were corrected.

## 21b. The very next install needed a second capability from the same step: `CAP_CHOWN`

**Symptom:** immediately after `CAP_MKNOD` was added and applied, the next Acer
install failed in the *same* `mkinitramfs` staging step:

```
fatal error : set_attributes: failed to change UID and gids on
/tmp/pip-install-target.m5dz4tui/etc/gshadow. because operation not permitted
```

**Cause:** `mkinitramfs`'s `set_attributes` calls `chown(2)` to restore each
staged file's original owner and group. Changing owner or group to one the
caller does not hold requires `CAP_CHOWN`, which — like `CAP_MKNOD` — the
QEMU-proven capability set never accounted for. `CAP_CHOWN` is bit 0; the
service's mask was `0x2400c0` (bits 6, 7, 18, 21), so it was provably absent.

**Evidence honesty:** the runtime A/B demonstration did not succeed on the
appliance. A `prctl(PR_CAPBSET_DROP)` attempt was invalid (the bounding set
does not remove an already-raised capability) and a `ctypes` `capset` attempt
segfaulted. The conclusion therefore rests on the capability-mask arithmetic,
the `chown(2)` semantics, and the error message naming UID/GID — not on a
constructed before/after run. The fix is nonetheless safe to try because
`CAP_CHOWN` is strictly narrower than the `CAP_SYS_ADMIN` the set already
carries.

**The systemic point, which matters more than either line.** Two capabilities
were needed by one step that no harness could reach. The capability set was
"minimal" in the sense that nothing unproven had been added, but it was
**systematically under-specified for the path the evidence could not execute**,
and each missing capability costs a full install cycle to discover. The correct
follow-up is not a third one-at-a-time addition: it is to run the real
`update-initramfs` leg once inside a throwaway chroot with capabilities
stripped, and enumerate the complete set empirically in a single experiment.
Recorded in the plan as the required method change.

## 21c. Install failures were unreadable except by hand-transcription

**Symptom (process, not a single defect):** every real install failure on the
Acer had to be diagnosed by the owner reading the framebuffer and typing the
message. Three separate causes:

1. The privileged service's boundary traces exist but are gated behind the
   Session-04 test marker `/run/greia-x8-debug` and are written **only to the
   serial console**, so on real hardware they never fired at all.
2. The service had no always-on record of a refusal. `format_log_record` is
   called only on success and its result is discarded (`_ =`), so a failed
   install left no trace in the journal.
3. The installer draws its error on the framebuffer and journals nothing.

**Fix, two bounded channels:**

- `transaction_service._greia_log_event` writes one always-on record to stderr
  (the journal) for refusal (with the service's own bounded reason), unexpected
  exception escape, client hang-up, and successful install. Nonce, plan digest,
  settings values and credentials are excluded, matching `format_log_record`'s
  existing discipline; volume is roughly four lines per install request on a
  local one-request-per-connection socket.
- The installer mirrors its visible state to `/run/greia-installer/status.json`
  (page, progress stage, fraction, detail, error) and `entrypoint.main()`
  publishes a boot stage before the language chooser, so the file exists from
  process start rather than only after the first click.

**Two defects in the first version of this, both caught on the appliance before
any install was attempted:** it read `progress.phase` where the field is
`progress.stage`, and it caught only `OSError`, so the resulting `AttributeError`
escaped the frame loop and the installer service exited 1. A diagnostic channel
that can take down the product it exists to explain is worse than none, so the
whole body is now wrapped and absorbing, and both failure modes are locked by
`InstallerStatusRecordTests`.

**Regression-locked** by `RemoteDiagnosableInstallTests` and
`InstallerBootStatusTests`, including assertions that the logged and written
content carries no nonce, digest, passphrase or hash, inspected through the AST
so the functions' own docstrings — which deliberately *name* the excluded
secrets — cannot satisfy or trip the check.

## 21d. `set_attributes` failed on a setgid file; the missing authority was measured, not guessed

The attempt after §21b got further — it reached the install phase and wrote
about 19 MB to `/dev/sda` — and then failed in the same staging helper as §21b,
on a different operation:

```
fatal error: set_attributes: failed to change mode
/tmp/pip-install-target.4sf84owr/usr/bin/chage, because operation not permitted
```

`/usr/bin/chage` in the target is mode **2755, setgid** with group `shadow`; the
trailing `s` sits in the group position of `-rwxr-sr-x`. I first read it as
setuid and reached for `CAP_FSETID` on that reasoning. Measuring instead of
reasoning changed the answer.

`systemd-run` reproduces the service's capability set exactly, and the
reproduction was checked against its own `/proc/self/status` before any result
was trusted. Against the real binary from the payload, restoring its original
owner and mode:

| capability set | `chmod 2755` | resulting mode |
| --- | --- | --- |
| without `CAP_FSETID` | returns success | **755** — setgid silently dropped |
| with `CAP_FSETID` | returns success | **2755** — correct |

This is the more serious of the two findings. Without `CAP_FSETID` nothing
raises: `chmod` reports success while discarding the setgid bit, so the
installed initramfs would have shipped `chage` without the group privilege it
depends on, and the install would have completed and claimed to work.

Two of my own errors are recorded here as well. The first was reading the mode
wrong. The second was a probe that appeared to disprove the need for `CAP_FSETID`
— it did not, because the first version of the harness never printed its own
capability set, so "chmod 4755 succeeded" was only ever a statement about a
process that may not have lost the capability at all. A test that cannot fail is
not evidence.

`CAP_FOWNER` is granted as the companion authority for chmod/chown of staged
files the caller does not own, which is what mkinitramfs's original-ownership
restore does. It is **not** separately proven for this failure — the `CAP_FSETID`
reproduction above does not itself raise `EPERM` — and is recorded as granted on
that narrower rationale rather than on a clean reproduction. The unexplained
`EPERM` is not fully accounted for.

A full enumeration of the staging step's requirements by running
`update-initramfs` in a chroot was attempted and is not possible on the
appliance: the live overlay is 128 MiB and `/run` has 95 MiB free, against a
roughly 1 GB writable payload. Capability grants so far are `MKNOD`, `CHOWN`,
`FSETID`, `FOWNER`, each strictly narrower than the `CAP_SYS_ADMIN` this set
already carries.

## 21e. Correction to §21d: `RestrictSUIDSGID`, not a capability, was the cause

§21d attributed the setgid `chmod` failure to a missing capability and granted
`CAP_FSETID` and `CAP_FOWNER` on that reasoning. The next attempt failed
identically, with `CapEff = 0x82400d9` live, so that reasoning was wrong. The
cause is `RestrictSUIDSGID=yes` in the service unit.

The restriction denies mode changes that set SUID/SGID bits. That is precisely
mkinitramfs's job when it restores each staged file's original mode onto a
target rootfs that legitimately contains setgid binaries. It is a property of
the **mount namespace**, not of the capability set, which is why no capability
could ever have substituted for it and why adding capabilities changed nothing.

A/B on the appliance against the real binary, with `CapEff = 0x82400d9` in both
runs and the restriction as the only difference:

| `RestrictSUIDSGID` | `chmod 2755` |
| --- | --- |
| `yes` | fails, `errno=1` operation not permitted |
| `no` | succeeds, mode `2755` |

Confirmed inside the **live** service namespace via `nsenter -m`, where the mode
becomes `2755`, against a control with the restriction re-applied, which fails
`errno=1`. That comparison held capabilities at full in both runs, so the mount
namespace is isolated as the only variable.

**What survives from §21d, and what does not.** `CAP_MKNOD` and `CAP_CHOWN` were
real and are retained. `CAP_FSETID` is retained on independent evidence: with
the restriction lifted, restoring a setgid mode without it returns success and
yields `755`, silently dropping the bit. `CAP_FOWNER` remains unproven for any
observed failure and is retained only as the companion authority for staged
files the caller does not own, which is recorded as a narrow rationale rather
than a reproduction.

**A second defect, in the fix itself.** The intended `RestrictSUIDSGID=no` was
added beside a pre-existing `RestrictSUIDSGID=yes`, and the later assignment
wins, so the restriction stayed in force while the unit still read correctly.
The test now requires the directive to be declared exactly once; it fails with
`['no', 'yes']` when the duplicate is re-added.

This is an accepted reduction in hardening, recorded rather than minimised: the
installer cannot construct a Debian rootfs without it. The restriction remains in
force on every other Greia service, and this unit's other mount and system-call
restrictions are unchanged.

## 21f. Whole-process review: the unit was never sized against its own workload

Four appliance cycles were spent granting one capability per error message. Each
fix was locally correct and each was followed by the same class of failure, so
the approach itself was wrong. This reviews the process rather than the error.

**What the privileged half actually does on EXECUTE.** Not a bounded declarative
operation. It unpacks the payload with `unsquashfs`, regenerates the target
initramfs, runs `update-grub`, runs **`apt-get update` and `apt-get install`
inside the target chroot** to add machine-specific support, installs GRUB to the
whole disk, and verifies the boot configuration. That is a full distribution
installation. All of the hardening in the unit — the capability bounding set,
`TasksMax=8`, `RestrictSUIDSGID`, `RestrictAddressFamilies=AF_UNIX` — was
authored for a narrower job, and the last two of those three `TasksMax`,
`RestrictSUIDSGID` and the apt leg's requirement for `CAP_DAC_OVERRIDE` were
never exercised on any appliance, because every attempt died at 0.1, long before
the hardware leg at 0.74.

**Method.** Rather than continue one hardware cycle per error, the whole leg was
reproduced on Orbiter against the real 352 MiB payload in a transient unit whose
directives are parsed from the shipped unit file, against a partitioned loop disk
standing in for `/dev/sda`. An iteration went from roughly thirty minutes to two.
Six legs are exercised: unpack, `update-initramfs`, `update-grub`, apt update,
apt install, `grub-install`, `grub-script-check`. The harness is kept at
`tests/integration/install_leg_harness.sh` with its fidelity notes.

**What that found, none of it visible from a single error:**

- `TasksMax=8` is below the service's own peak of 16, sampled from the unit's
  cgroup `pids.current`. `unsquashfs` dies with `FATAL ERROR: Failed to create
  thread` and `mkinitramfs` with `100: Cannot fork`. This was a second failure
  hidden behind the first: it cannot surface until the attribute failures are
  fixed, so fixing those alone would have bought another cycle and nothing else.
- The apt leg needs `CAP_DAC_OVERRIDE`, failing as `rename failed, Permission
  denied` in `/var/lib/apt/lists`. `CAP_DAC_READ_SEARCH` was tested and is not
  needed.
- `CAP_FOWNER` is genuinely required, which §21e could only assert. Without it
  `unsquashfs` cannot unpack the payload at all: `set_attributes: failed to
  change mode .../security-support.semaphore, because operation not permitted`.
- With the full set, all six legs pass: a real package installs from a local
  pool, `grub-install` reports `Installation finished`, and `/usr/bin/chage` is
  correctly `2755`.

**Correction to §21e's reasoning, kept explicit.** `CAP_FOWNER` was granted then
as a companion authority "not separately proven". It is now proven, by a
different phase of the same `set_attributes` helper. The `RestrictSUIDSGID`
conclusion from §21e stands and is unchanged.

**Process lessons, recorded because they are the actual defect here.** Granting
authority named by an error message treats the message as the specification; on
this platform the hardened-unit directives, not the capability set, were the
larger source of install failure, and a capability-shaped fix for a
namespace-shaped fault reads as plausible and fails identically. A unit that runs
a distribution package installation must be sized against that workload by
executing it, not inferred from whatever error surfaced first. Two harness
versions also produced false failures before the loop was trustworthy — a
pre-mounted read-only target, and `SystemCallArchitectures=native` killing an
i386 payload on an x86_64 host — which is why the fidelity notes are kept with it.

## 22. First boot from the installed disk: four defects, none of which the install could surface

The install completed and was verified on the disk before reboot: journal
`installed target=cb506170…`, MBR sector 0 carrying a GRUB boot sector,
`vmlinuz`/`initrd.img`/`grub.cfg`/`fstab` present, and `/usr/bin/chage` at mode
`02755` — the setgid bit that `RestrictSUIDSGID` would have silently stripped.
The system then booted from `/dev/sda1` and failed in four separate ways. None
was reachable during installation, so no amount of install debugging would have
found them. They are recorded here as a class: **first boot is a separate
execution surface and it had never been run.**

### 22a. Boot loop: Xorg reached through Debian's setuid wrapper

`greia-launcher.service` passed `-logfile /run/greia-os/Xorg.0.log`. It reaches X
through `/usr/bin/Xorg`, which execs `/usr/lib/xorg/Xorg.wrap`, and that wrapper
is **setuid root** (mode 4755). Setuid means `uid=greiakid` with `euid=0`, and
xorg-server refuses `-logfile` outright on a uid/euid mismatch:

```
(EE) Fatal server error:
(EE) Invalid argument -logfile with elevated privileges
```

The server exited at once, `Restart=always` re-ran it, and the visible symptom
was a splash refreshing roughly every minute. Reproduced both ways on the
appliance: through the wrapper the refusal is immediate; naming
`/usr/lib/xorg/Xorg` directly the log is written and the server starts.

`greia-x-session` already documented the intended design — *"the unprivileged X
server must own tty1 to activate it"* — and the unit's own comment records a
previous proof that an unprivileged Xorg needs the `tty` group. The setuid
wrapper was quietly defeating both. Fixed by naming the real binary in
`ExecStart`.

This hid for so long because **the live installer's own X is not setuid-wrapped**,
so `-logfile` worked there for hours. Only the installed payload's X refuses.
The launcher had been validated against the wrong X server.

### 22b. `greia-boot-health-credential.service` had never once succeeded

`boot_health.main()` did `parser.parse_args(list(argv or []))` and the module is
executed as `python3 -m greia_platform.boot_health --issue-for-pending`, which
reaches `main()` with `argv` as **None**. `None` was treated as an empty argument
list, so the unit's own flag was silently discarded: the generator printed its
usage text and exited `2` on every boot, and the service never issued a
capability. Every existing test passed an explicit argument list, so the suite
was blind to it by construction.

Fixed to read `sys.argv[1:]` when `argv` is None, while still honouring an
explicit `[]` from a caller. The service now prints `NO_PENDING` and exits `0` on
a plain boot, which is the documented behaviour. Regression-locked by driving
`main()` through `sys.argv` with no argument, exactly as `-m` does, plus a
negative test that the refusal path still exits `2`.

### 22c. The same service also failed before it reached its own code

`ReadWritePaths=/run/greia-os /run/greia-boot-health-authority`, and systemd
refuses to start a unit when a `ReadWritePaths` entry does not exist. The
generator creates that directory itself at mode 0700 — but only after the
sandbox is applied, so the path was pre-empted and the unit died at the
namespacing step on every boot. Fixed with `RuntimeDirectory=` plus
`RuntimeDirectoryMode=0700` and `RuntimeDirectoryPreserve=yes` (the record must
outlive the oneshot).

### 22d. Residual loop: the Shell exits 0 before INTERACTIVE_READY

Still open, and now much less violent: the Shell starts, initialises pygame,
sets the display mode, plays the intro, discovers Activities, builds the runtime
and prepares history — then exits `0` after roughly 25 seconds, before
`mark_interactive_ready`. Because the unit is `Type=notify` and expects
`READY=1` after the first frame, systemd records `Result=protocol` and
`Restart=always` re-runs it. The boot-marker spool is the oracle:
`intro_first_frame_flipped` = 28, `launcher_interactive_ready` = 0. The Shell's
own stdout does not reach the journal, which the x-session comments already
document as a known forwarding loss, so the exit reason is not yet captured.

### Lesson

Four consecutive defects, all invisible to installation and all invisible to
the unit suite, because the suite drives functions with explicit arguments and
the installer image's X is not the payload's X. The install leg now has an
offline harness; first boot needs the equivalent — a first-boot harness that
runs the *installed* system, not a live medium, with the payload's own X and
with `main()` reached the way `-m` reaches it.

## 22e. Root cause of the residual loop: the child's own profile data was owned by the parent identity

`child_shell` was exiting non-zero, `greia-x-session` silently fell back to
`trusted_presentation`, and because only the boot-intro path sends `READY=1`,
the `Type=notify` launcher unit recorded `Result=protocol` and restarted. A UI was
on screen the whole time, which is why it looked like a slow splash rather than a
crash. The Shell's own stdout never reaches the journal — a forwarding loss the
x-session comments already document — so the reason was invisible until the
display session was reproduced by hand with output captured.

```
File "/opt/greia-os/src/greia_platform/history.py", line 640, in _prepare_root
    os.chmod(self._root, 0o2770)
PermissionError: [Errno 1] Operation not permitted:
  '/var/lib/greia-profiles/data/1ec82f21…/progress'
```

Ownership on the appliance, measured:

| path | owner | mode | group write |
| --- | --- | --- | --- |
| `/var/lib/greia-profiles` | `greiakid:pipprofiles` | `2770` | yes — correct |
| `…/data/<id>/progress` and siblings | `greiapel:pipprofiles` | `2755` | **no** |

Two independent violations, not one:

1. **2755 gives the group only `r-x`**, so `greiakid` could not write its own
   progress at all.
2. **Setting setgid requires the caller to own the file** (`inode_owner_or_capable`),
   so `greiakid` could not chmod the tree back even though `pipprofiles` contains
   both identities. The child was neither the owner nor able to become one.

The tree's own parent already carried the correct `greiakid:pipprofiles 2770`,
which is what made the deviation diagnosable: the fix is to make the data subtree
match the pattern its parent already follows.

Fixed by a versioned first-boot migration `b3-profile-data-ownership-v1`, which
normalises the data tree to `greiakid:pipprofiles 2770` (depth-first, `-print0`
so an unusual profile id cannot break word splitting) and writes its marker only
after the repair succeeds, following the existing `b2-audio-groups-v1` pattern.
`history.py`'s chmod stays **unguarded** on purpose — unlike the parent-side
normaliser in `profiles.py`, which swallows `PermissionError` — because a silently
retained wrong mode would convert this boot crash into a later write failure. It
now raises a `HistoryError` naming the required ownership and mode and the actual
ones, because a bare `EPERM` is precisely what cost four blind cycles here.

Two of my own errors are recorded alongside. I dismissed this exact traceback as
an artifact of `sudo -u` dropping supplementary groups, and reasoned that
`history_prepare_end` being emitted proved success; it is emitted in a `finally`,
so it proves nothing. I also treated a `READY=1` sent from *outside* the service
cgroup as proof the mechanism worked — systemd correctly ignores those, and the
unit's transition I attributed to it was really just its start timeout expiring.
The in-cgroup probe is what actually established that the socket, binary,
permissions and attribution are all sound.

**Not claimed fixed:** `greia-boot-observer.service` remains failed on the
appliance. It is downstream of the boot-health capability, which is correctly
*not* issued on a plain boot with no pending journal (`NO_PENDING`), so whether
the observer should fail closed or stay inactive in that case is unresolved.

## 23. First boot, part 2: the "soft reboot" was systemd killing a working Shell

### 23a. What the parent saw was not a reboot

Uptime never reset and PID 1 kept its original start time, so the machine was
not rebooting. `greia-launcher` was cycling: the splash and login screen returned
roughly every 90 seconds, on the login screen and inside the Parent panel alike,
which is exactly why it read as a soft reboot.

### 23b. Cause: the readiness contract could not be satisfied

The unit was `Type=notify` with `NotifyAccess=all`, waiting for the Shell's
first-frame `READY=1`. Two measured facts explain the failure:

- `systemd-notify` was genuinely spawned, returned `rc=0`, and had
  `NOTIFY_SOCKET=/run/systemd/notify` in its environment. The datagram was sent.
- `xinit`, `Xorg` and the child Shell were all in
  `/user.slice/user-999.slice/session-402.scope`, while the unit's own
  `ControlGroup` was `/system.slice/greia-launcher.service` and held **zero**
  tasks.

`PAMName=login` runs `pam_systemd` from `common-session`, which opens a logind
session and moves the processes into a session scope. systemd attributes a
`READY=1` datagram to a unit by the *sender's* cgroup, so the readiness landed on
the session scope and the unit never saw it. The start job then waited out
`TimeoutStartSec=90` and systemd killed a Shell that was working perfectly, and
`Restart=always` put the splash back.

An earlier "proof" that the notify mechanism was sound was misleading: the probe
had been moved into the unit's cgroup by hand, so it was attributed correctly.
The mechanism was never the problem; the sender's cgroup was.

### 23c. The other half of the conflict, found by fixing it wrongly

Removing the logind session (a dedicated PAM stack without `pam_systemd`) fixed
the cgroup attribution — `Tasks: 2`, both PIDs in the unit cgroup — and
immediately broke Xorg:

```
xf86EnableIO: failed to enable I/O ports 0000-03ff (Operation not permitted)
vesa: Ignoring device with a bound kernel driver
(EE) Fatal server error: (EE) no screens found(EE)
```

So both halves are load-bearing: the logind session is what grants the
unprivileged X server its seat and device access, and it is also what destroys
the cgroup attribution. `Type=exec` does not escape the conflict either, because
systemd still cannot confirm the process against an empty cgroup.

### 23d. Fix: stop asking systemd for a signal it cannot receive

`Type=simple` asks for nothing beyond a successful fork and is immune to the
cgroup escape. Readiness stays where it already lives and is already
trustworthy: the Shell owns the branded boot cover and emits the bounded
`launcher_interactive_ready` boot marker that
`tools/boot/analyze_boot_markers.py` consumes. systemd never had a reliable
readiness signal for this unit, and the timeout was destroying the product to
compensate.

Verified on the reference Acer: `active/running`, `NRestarts=0` sustained for
150 seconds, past the old 90-second kill, with Xorg up, zero `no screens found`
errors and the child Shell alive.

A dedicated `/etc/pam.d/greia-launcher` was tried and reverted. It is not shipped:
it removes device access the X server genuinely needs, and keeping it would be
dead configuration implying the session is optional.

### 23e. `python3-dbus` was declared only for the installer

The Parent Wi-Fi panel failed with `ModuleNotFoundError: No module named 'dbus'`.
`python3-dbus` was in `build/package-sets/installer-base.txt` and nowhere else,
so the installer's own Wi-Fi screen worked and the installed system's did not.
Same asymmetry as the setuid Xorg wrapper: validated in the installer image,
absent from the target. Added to `build/package-sets/network-basic.txt`, which
every target profile already includes.

Not verifiable on the current machine: the target image ships no apt lists, being
offline-first, so `apt-get install python3-dbus` reports "Unable to locate
package". The fix is in the composition and lands on the next build, exactly like
the other image-level fixes.

### 23f. Two parent-reported gaps still open

- **No way to set the Parent password on the device.** The on-device panel's tabs
  are language, audio, wifi, ssh, info and pointer; none manages the credential,
  while the API already supports `POST /api/v1/parent-password` via
  `change_parent_password(current, new)`. Parents must currently use the web app
  on another device. Not started.
- **Audio settings layout.** Controls overlap the input-level visualisation,
  which is too small and does not work. Not yet investigated.

## 24. Parent panel: missing child accounts and Parent password, and a layout that could not survive translation

### 24a. What was missing

The on-device Parent panel could only ask the Parent service one question — is
this password correct. It had no way to set its own password and no way to add or
remove a child. The web API already supported both
(`POST /api/v1/profiles`, `DELETE /api/v1/profiles/{id}`,
`POST /api/v1/parent-password`), so parents had to use a browser on another
device. The panel's own tab list was language, audio, wifi, ssh, info and pointer.

### 24b. The layout could not survive a translation, and the screenshot review said so

There was no string table and no measurement. The audio tab had already drifted
into half-hardcoded Italian beside English — "Microphone Input Gain (Guadagno
Microfono)", "Preset rapidi consigliati:", "Livello:", "Normale/Medio/Alto/Forte/
Massimo" — on a system declaring twelve languages including Arabic, Chinese,
Bengali and Hindi.

Rendering every tab offscreen and looking at the images confirmed the reported
faults and found more:

- the level label was centred in a fixed 300 px badge and spilled onto the
  adjacent buttons;
- the `-25%` and `+25%` controls used U+2796 and U+2795, which the bundled Nunito
  Sans has no glyphs for, so they rendered as grey tofu boxes;
- there was no level meter at all, only a text badge, despite the screen implying
  one;
- the tab strip sized its columns arithmetically and centred labels inside them,
  so adding two tabs made the labels collide before any translation existed.

### 24c. What was built

`greia_launcher/panel_layout.py` measures every string through the same
fallback chain the panel renders with, wraps it to a width, grows a block
downwards, and clips with an ellipsis only where growth is impossible, reporting
that it did. `GreiaTypography.render` accepts one line at a time by design, so
wrapping composes measured single-line renders rather than bypassing the shared
emoji fallback, which previously produced tofu for every emoji on device.

`greia_launcher/panel_strings.py` is now the single translation surface: every
user-visible constant, 58 of them. It is deliberately not a gettext pipeline and
does not pretend to be one. Two gaps are named rather than hidden: right-to-left
languages need the whole layout mirrored, and non-Latin scripts need font
coverage this module cannot provide.

Layout changes driven by the screenshots:

- the tab strip wraps onto a second row instead of shrinking every label into an
  ellipsis, and the content area moves down to follow it. At 800 px with eight
  tabs it now shows every label in full where the old arithmetic produced
  "Languag" and "Remote &…";
- the audio tab has a real meter driven by the actual gain, with the readout and
  the track in separate bands after the first version drew the track straight
  through the text;
- the avatar stepper draws its triangles rather than asking the font for
  U+25C0/U+25B6, which are absent for the same reason the audio step buttons
  were;
- header-row action buttons reserve their column, after "Change password" was
  first painted on top of the intro's first line;
- tab content is composed on its own surface of exactly the content rect, so a
  form taller than the card is clipped instead of spilling onto the chrome. The
  "Add child" form was clipped in half until name and age shared a row, and the
  password form until its action moved to the header row.

### 24d. What was verified

`tools/panel_screenshots.py` renders every tab, and the add and confirm
sub-screens, at 1024x600 and 800x600, and reports overlapping hit targets. All 20
states pass with zero overlaps. Both new tabs were exercised on the reference
Acer as `greiakid`: eight tabs present, launcher `active` with 0 restarts over
60 s, and no errors.

`tests/test_panel_layout.py` replays every string constant through the layout at
both sizes, including a German compound longer than anything written today, so a
string that cannot be laid out fails the suite rather than a parent.
`tests/test_parent_panel_accounts.py` covers the behaviour: refusals, the
service's own reason reaching the parent, offline distinguished from a bad name,
the policy's name-length limit, avatar cycling, the password mismatch guard, and
a bare verifier still unlocking without a session. Four negatives were verified
individually: removing the empty-name guard, the session-on-unlock path, the
name-length limit, or the password mismatch guard each fails a test.

## 25. The Parent panel was unusable on the reference Acer: 300 ms per frame

### 25a. Two separate causes, one of them mine

Measured on the Acer rather than guessed, with the panel redrawn offscreen at
1024x600 as `greiakid`:

| tab | before | after |
| --- | --- | --- |
| language | 280 ms | 2.3 ms |
| audio | 351 ms | 15.3 ms |
| accounts | 344 ms | 2.3 ms |
| security | 335 ms | 2.3 ms |
| wifi | 263 ms | 2.3 ms |
| ssh | 266 ms | 2.3 ms |
| info | 279 ms | 2.4 ms |
| pointer | 272 ms | 2.3 ms |

That is 2.8-3.8 fps before, and 43-435 fps after. The display is software
(`hwaccel=0`), so every large translucent composite is expensive in C.

**Pre-existing, and the real reason it felt unusable.** Profiling attributed 97%
of the old frame to `Surface.blit`: about 56 large alpha blits per frame, costing
roughly 156 ms. `_ensure_panel_base` cached the dim and the large rounded chrome,
but the tab strip and the whole tab content were recomposited every frame. The
panel was already ~150 ms/frame before this session, which is why it had always
been painful on an Atom.

**Mine, and it doubled the problem.** The measured layout helpers added in §24
called `typography.render` and `typography.measure` for every line of every
string, every frame, with no cache. The old `_get_text` happened to cache; the
new helpers did not. Profiling showed 74 calls into the typography service per
frame and 45% of total frame time inside its grapheme segmentation. Measured
against the pre-change panel: ~150 ms before my changes, ~300 ms after.

### 25b. Fixes

- The layout helpers memoise measurement, wrapping and composed blocks, so text
  is measured and rendered once instead of 74 times a frame.
- The panel composes an unchanged frame once and then presents it with a single
  blit, keyed on a signature of everything the drawing code reads. An animated or
  externally-driven tab opts out via `_content_animating` rather than being
  frozen.

### 25c. Three defects the cache introduced, all caught before shipping

A cache that decides what to draw is a correctness risk, not a performance one,
and it produced three:

1. **The account list was missing from the signature.** Adding and removing a
   child would not have updated on screen until something else changed.
2. **The entire pointer tab and the SSH status were missing** — the pointer
   focus, its message, the test flash and the SSH line. The pointer tab would
   have been frozen.
3. **The Wi-Fi tab was invisible to the signature**, because it renders
   `wifi_controller.snapshot` from an injected collaborator. Excluding the tab
   restored correctness but cost the whole tab its speed, back to 242 ms, and
   Wi-Fi is exactly the tab a parent uses to set up a network. The signature now
   summarises the collaborator's *content*, so the tab is cacheable while idle
   and re-renders while scanning: 2.3 ms.

`tests/test_panel_frame_cache.py` now audits the draw methods for `self._x` reads
and fails if any is absent from the signature, so a future field cannot be left
out silently. `_targets` is exempt by design, and the exemption is written down.

### 25d. A latent cache bug found by an intermittent test

The layout cache was keyed on `id(typography)`. CPython reuses object addresses
after collection, so a collected typography service and a new one could share an
address, and the new one would be handed the old one's surfaces: stale text,
wrong size, wrong colour. This surfaced as a test that passed alone and failed in
a suite, which is exactly the shape of an address-reuse bug. The caches are now
held per typography instance in a `WeakKeyDictionary`, which makes it impossible
and collects an unused service's surfaces with it.

The same investigation found a fault in my own test rather than the code: it
hardcoded `"rainbow"` as the expected avatar, while the panel deliberately reads
the avatar list from the shipped profile policy, whose first entry is `unicorn`.
The code was right and the test was environment-dependent; it now derives the
expected value from the policy, consistent with not duplicating that list.

### 25e. Verification

`test_panel_frame_cache` 12/12, including the signature audit, the collaborator
invalidation cases and a served frame keeping its hit targets — a cached frame
that dropped them would leave the panel visible but dead to clicks.
`test_panel_layout` 20/20, `test_parent_panel_accounts` 18/18,
`test_parent_credential_client` 25/25, and the four pre-existing panel suites
unchanged at 41/41. Verified on the Acer: launcher `active` with 0 restarts,
child shell alive, no errors.

Not claimed: the audio tab sits at 15.3 ms against a 16.7 ms frame budget. It is
inside budget and was measured rather than assumed, but it is the one tab with
little headroom, and the cause is the periodic gain re-read on its draw path. It
is worth its own look if audio ever feels heavy.

## 26. Wi-Fi on the installed system: two missing runtime packages, not one

§23e added `python3-dbus` to the target's network set and correctly recorded
that it could not be verified on the appliance, because the offline-first target
ships no apt lists. The appliance turned out to have working DNS and an open TCP
connection to `deb.debian.org`, so the lists could simply be fetched and the
package installed.

`python3-dbus` alone was not enough, and this is why listing networks would have
looked like progress while the panel still could not connect:

- `IwdWifiBackend.available()` imports `dbus` and became `True`, and a scan
  returned five networks.
- `IwdWifiBackend.management_available()` — the gate that decides whether the
  panel may *join* a network rather than merely list one — additionally imports
  `gi.repository.GLib`, which was also absent. It stayed `False`.

With `python3-gi` and `gir1.2-glib-2.0` installed, the appliance reports
`available: True`, `management_available: True`, and enumerates five networks, so
the panel can both list and connect.

All three packages are now in `build/package-sets/network-basic.txt`, which every
target profile already includes, and the staging contract asserts all three by
name so a rebuild cannot ship a target that can list networks but never join one.

## 27. Microphone: no input level was shown anywhere, and the gain was clipping

The Parent panel's audio tab showed a gain meter that reflected only the
*setting*. Nothing reported what the microphone was actually hearing, so a parent
could not tell a working microphone from a muted one, nor notice that the gain was
too high. There was no level-reading API in the platform at all.

Measured on the reference Acer's ALC268 analog input, in its native format
(S16_LE, 48 kHz, **2-channel** — it rejects `-c 1` outright):

```
left RMS   11591.3  (-9.0 dBFS)
left peak  32768    ( 0.0 dBFS)   <- clipping, and invisible in the UI
```

`MicrophoneLevelReader` adds a live input meter. Design points, each from the
hardware rather than assumption:

- **No new dependency.** `arecord` from alsa-utils is already present and writes
  raw PCM, so the level is computed in-process. A Python ALSA binding would have
  been another package to ship in an image that has already been bitten by a
  missing one.
- **Channel count is discovered, not assumed**, and only the left channel is
  measured, because averaging would let a loud right channel mask a silent left.
- **Never blocks the Shell.** Capture runs on one daemon thread and the panel
  reads a plain snapshot; a wedged or absent device yields "no level", never an
  exception and never a stall.
- **Silence is not failure.** A silent microphone reports silence; a device that
  cannot be opened reports unavailable, so the two are distinguishable on screen.
- **Capture follows the tab**, not the panel's lifetime, so a parent looking at
  Wi-Fi does not hold the microphone open.

Verified on the appliance as `greiakid` against the real microphone: RMS tracked
live between -4.5 and -24.6 dBFS with the peak held, and the device released on
stop. The audio tab is now excluded from the composite frame cache, because
caching it would freeze the one number the parent opened the tab to watch.

## 28. Renaming a child account

The Kids tab could add and remove a child but not rename one, so a typo in a name
was permanent without deleting and recreating the account, which discards that
child's saved work.

`ProfileStore.update(display_name=...)` already existed and the panel's client
already spoke to the service; what was missing was the route between them.
Added `PUT /api/v1/profiles/{id}`, which accepts **only** `display_name`. Every
other profile field keeps its own considered route, because a partial update that
silently accepted an avatar or an age here would bypass their validation.

The rename deliberately goes through the service rather than the panel writing
profile state as the child identity, and that is load-bearing rather than
ceremonial: the policy's 24-character name bound lives in the same profile policy
the service validates against, and the panel alone cannot enforce it. Verified
live on the appliance as `greiakid` — an over-long name was refused with "profile
name may contain at most 24 characters", a valid rename applied, and the original
name was restored afterwards.

The panel reuses the add form as an edit mode, pre-filled with the child's
current name, age and avatar, and the row now carries Rename beside Remove. The
frame-cache signature audit flagged the new `_renaming` field and it was added
rather than exempted.

**Still open, and not claimed done:** the microphone processing settings. They
were never removed. `MicrophoneProcessingMode` (off, lightweight, advanced) and
`AudioSettingsStore` with `microphone_processing_enabled` and
`advanced_noise_reduction` have existed in the platform since
`f350ef3a feat(audio): add typed microphone processing service`, and
`git log -S"noise" -- src/greia_launcher/parent_panel.py` is empty: the on-device
panel has never exposed them, and neither does the Parent API. Wiring them needs
the same treatment as everything else here — a parent-service route, because
`/var/lib/greia-system-settings` is `greiapel:pipsettings 2750` and the panel
runs as `greiakid`, which has read but not write access to it.

## 29. 2026-10-03 — Wi-Fi L3 ownership is role-specific, not globally owned by iwd

A source-acceptance stop caught a false generalization before another Acer
build/flash cycle. Greia has two deliberate wireless L3 policies:

- **Live installer:** `build/installer-overlay/etc/iwd/main.conf` sets
  `EnableNetworkConfiguration=true`. iwd owns association/authentication and
  IP configuration. The installer wireless networkd policy therefore uses
  `[Link] Unmanaged=yes` and must not run a second DHCP client.
- **Installed target:** `build/overlay/etc/iwd/main.conf` sets
  `EnableNetworkConfiguration=false`. iwd owns association/authentication,
  while systemd-networkd owns L3/DHCP. The target wireless policy therefore
  keeps `[Network] DHCP=yes` and must not mark the link unmanaged.

The rejected V4 candidate had changed both roots to networkd DHCP while claiming
Greia never enabled iwd network configuration. That claim was contradicted by
the shipped installer `main.conf` and by
`tests/test_installer_wifi_build_contract.py`, which already pinned the live
installer's iwd network configuration.

The canonical regression now validates each role as a pair
(`iwd/main.conf` + `25-greia-wireless.network`) and both development artifact
verifiers reject either dangerous state: two L3/DHCP owners or no L3/DHCP owner.
No physical or image evidence is claimed yet for this correction.

## 30. 2026-10-07 — Fresh first boot loop: Parent-created profile root was 2750 after B4 had already completed

The fresh Acer install reached X and repeatedly entered the launcher, but the
child shell never became interactive. Read-only device forensics captured the
actual traceback: history initialization tried to create
`data/<profile>/progress` and received `EACCES`.

The fixed roots were correct:

- `/run/greia-os` = `greiakid:pipprofiles 0770`;
- `/var/lib/greia-profiles/data` = `greiakid:pipprofiles 2770`.

The newly Parent-created profile root and its Parent-owned
`customization` / `activities` children were instead
`greiapanel:pipprofiles 2750`. The B4 marker was written 17 seconds before
the Parent created that profile, so B4 could never repair it on a fresh system.
This is structural: first-boot is ordered before the Parent service.

The creation path had a second structural contradiction. The Parent service
runs with `RestrictSUIDSGID=yes`, while `ProfileStore` attempted to repair
new shared directories using `chmod(2770)` and silently swallowed
`PermissionError`. The parent setgid directory correctly caused new
directories to inherit SGID, but the service's effective umask removed group
write, leaving `2750`; the attempted chmod was then allowed to disappear
without a product error.

Source repair:

- `greia-parent.service` now uses `UMask=0007`, so directories under the
  setgid `pipprofiles` tree are born `2770` without weakening
  `RestrictSUIDSGID=yes`;
- `ProfileStore` verifies exact shared mode + managed group and raises
  `ProfileError` instead of swallowing chmod failure;
- new profiles establish/verify their directory contract **before** their
  registry entry is published; a failed new transaction cleans only its new
  profile root and leaves the registry unchanged;
- child-owned `progress` / `storage` remain child-created;
- B5 (`b5-profile-shared-modes-v1`) is a bounded upgrade-only repair for
  already-existing depth-1 profile roots plus depth-2
  `customization` / `activities`; it does not recursively re-own user data.

Regression coverage proves the Parent UMask path succeeds even when every SGID
chmod is synthetically refused, and separately proves a bad-mode create fails
before registry publication.

**Evidence boundary:** SOURCE FIXED / OWNER SOURCE ACCEPTANCE PENDING. A new
image is required; the USB that reproduced this failure predates the fix.

## 31. 2026-10-07 — Boot observer was enabled on a layout whose semantic records cannot exist

On the same fresh legacy single-root install,
`greia-boot-observer.service` failed every boot with systemd status 226
(namespace setup). Its sandbox bind-mounts
`installed-layout.json` and `release-identity.json`, but those are A/B slot
identity records and are not produced by `bios-single-ext4`.

The observer's own production implementation is A/B-specific: it maps kernel
PARTUUID to semantic slot A/B through the trusted installed-layout record and
cross-checks the slot-local release identity. Enabling it on single-root targets
therefore had no valid success state.

`compose_configure_systemd` now enables the observer only when
`STORAGE_LAYOUT_ADAPTER` ends in `-ab-v1`. The unit remains fail-closed on
A/B systems; missing authority files there are still a real failure. An
executable composition regression checks both `bios-single-ext4` (observer
absent) and `legacy-bios-ab-v1` (observer enabled).

## 32. 2026-10-07 — Developer status/logs incorrectly depended on a display descriptor the canonical target never provisioned

The failed Acer could still be diagnosed over direct SSH, but
`greia_remote.py status` and `logs` both failed before doing their work
because `DeveloperControl.__init__` eagerly loaded
`/etc/greia-os/developer-display.json`.

Source review found two distinct defects:

1. status/log collection was wrongly coupled to X display control;
2. the canonical developer target composition did not write the descriptor at
   all (the older standalone provisioner did, but current canonical composition
   bypasses it).

Repairs:

- `DeveloperControl` loads the display endpoint lazily; status reports
  `available=false` plus the endpoint error and logs remain usable;
- screenshot still fails closed without a valid endpoint;
- canonical developer composition now writes a deterministic role-specific
  descriptor: installed target = `greiakid :0`, live installer = `root :0`.

This restores the intended diagnostic lane while preserving display-operation
trust boundaries.

## 33. 2026-10-07 — One-per-cycle `pkexec` warning remains open and non-blocking

The fresh-failure capture also saw `sh: 1: pkexec: not found` once per launcher
cycle. Device forensics found no Greia source/config reference and proved normal
session progression continued beyond it. It is not part of the first-boot loop
root cause and is intentionally left open until a reproducible owner is found.

## 34. 2026-10-18 — Quiet RC showed the stock Syslinux banner for the whole early boot

The owner's acceptance run of the rebuilt RC reported the visible
`SYSLINUX 6.04 EDD … Copyright (C) 1994-2015 H. Peter Anvin et al` line staying
on screen for the long quiet kernel/initramfs phase, including after an
install when the machine reboots with the key still inserted. This is the same
presentation gap documented in `docs/design/GREIA_BOOT_EXPERIENCE.md`: stock
SYSLINUX prints the banner before it parses any configuration, and because
`quiet` prints nothing new, the text survives even the fbcon takeover (which
redraws the console buffer) until the Greia framebuffer cover paints.

The 2026-08-20 regression review had rolled back a form-feed `DISPLAY` clear
file together with the fatal `console=null` argument; the observable-output
rule then kept the banner. Owner decision 2026-10-18 separates the two:

- `build/live-syslinux/clear.msg` (one `0x0c` byte) is consumed only by the
  quiet template via `DISPLAY /boot/syslinux/clear.msg`;
- `tools/build-live-usb.sh` places the byte on quiet media only; the
  read-only verifier requires the line and byte-compares the file;
- the diagnostic/recovery template and media keep fully observable output and
  the verifier refuses any `DISPLAY` there;
- `console=tty1` + `panic=0` stay, so a fatal panic still prints its emergency
  message; the `verbose` recovery label is unchanged;
- The mechanism was reproduced on a scratch Syslinux image in QEMU
  (banner cleared at configuration time, `TIMEOUT 0`); QEMU verification of the
  rebuilt media and physical Acer re-acceptance remain the closure evidence
  (premortem F2).

## 35. 2026-10-17 — Quiet RC froze on the Syslinux banner (`console=null`, no ttynull driver)

First physical run of the redesigned RC installer: the key booted, showed the
stock Syslinux banner, and then nothing. Root cause: the quiet live entries
passed `console=null`. The Debian 686 kernel is built without `CONFIG_NULL_TTY`,
so `console=null` leaves the system with no console at all; PID 1 starts
without stdin/stdout/stderr, live-boot's `/init` dies at its first
`exec 6>&1` ("Bad file descriptor"), PID 1 exits, and `panic=0` halts the
kernel with the banner as the last framebuffer content. QEMU reproduced
"unable to open an initial console" / "Attempted to kill init" from the current
flashed image.

Fix (`672ae910`, published with `ee7a40d1`): quiet keeps a real
`console=tty1` and silences it with `quiet loglevel=0 show_status=false` plus
cursor off; `boot_contract.py` gained `FATAL_CONSOLE_ARGUMENTS` and every
template/verifier/test now rejects `console=null` or an empty `console=`.
QEMU then reached the installer language screen.

Verification pitfall found while reproducing: `-cpu pentium3` lacks SSE2, so
Debian's i386 NumPy refuses to import, the installer client dies, and
`Restart=always` plus `installer-exit-cover` repaint the Greia splash over the
dead service — indistinguishable from a stalled image. Use `-cpu n270` or
`build/verify-image-qemu.sh`. Root cause and fix are also recorded in
`docs/engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md` §7 and in the 2026-10-18 QEMU
evidence directories under `docs/reviews/acer/` (archived; see git history).

## 36. 2026-10-18 — Installer completion button was dead; live shutdown still hangs on the Acer (OPEN)

Owner report: the final "I'm ready — turn off" button appeared to do nothing,
and pressing the laptop's physical power button produced a black (powered-on)
screen that never switched the machine off; the only way out was a forced
reset. The same attempt on the previous image showed the Syslinux banner on
that screen, because the quiet console buffer had not been cleared yet.

Confirmed defect: the button's `systemctl poweroff` ran as the installer's
unprivileged `nobody` identity with no logind session. logind/polkit answered
"Call to PowerOff failed: Access denied" (QEMU-reproduced from the live
image). The black screen came from the physical button's root logind shutdown,
not from the button, which never had an effect.

Fix (`src/greia_installer/main.py`, installer overlay): the UI writes
`/run/greia-installer/finish-request` in the RuntimeDirectory it already owns
(same pattern as `release-boot-cover`); a new root
`greia-installer-finish.path` watches exactly that file and activates the
one-shot `greia-installer-finish.service`, whose root helper
(`/usr/local/lib/greia-os/greia-installer-finish`) raises shutdown visibility
(`SetShowStatus yes` plus kernel console loglevel 8) and then performs the
single `systemctl poweroff`. The composer enables the path unit, the
composed-root verifier requires the pair, the helper and the enable symlink,
and the completion page shows a manual fallback (four languages) if the marker
cannot be written. No new package, daemon or polkit rule; the privileged
surface is one fixed power-off plus making that power-off observable.

OPEN: the physical/logind shutdown path still hangs on the reference Acer
after systemd begins stopping (black screen, never powers off, no Greia cover;
QEMU powers off cleanly through both `systemctl poweroff` and the ACPI power
key, so it is hardware-specific). Next: reproduce with the hidden `verbose`
boot (or a diagnostic-profile build) and capture the last visible shutdown
stage before proposing a fix.

Verification of the repair (2026-10-18, rebuilt media
`369bb29b472708c3115f5125940baa83110765e63f6915a07d60e94a92ede5cd`,
live media `7de4bafd-a7fc-4706-9833-96690929eaf8`): QEMU boot of the flashed
stick showed `greia-installer-finish.path` active; creating the marker as the
installer's own unprivileged identity
(`sudo -u nobody touch /run/greia-installer/finish-request`) activated the
root service and the VM performed a clean ACPI power-off (QEMU exited).
Artifact and USB read-back verification both PASS; payload 1,203 MiB.
Physical Acer retest remains the closure evidence for F18.

Presentation follow-up (owner report, same day): while the diagnostic
visibility raise was active, the successful shutdown showed a terminal
transcript, then the Greia cover, then more systemd text drawn over the cover
with a glitchy look (fbcon and the direct framebuffer paint sharing VT1). Since
the on-screen path now powers off correctly, the raise was removed: the finish
helper performs only `systemctl poweroff`, and the existing
`installer-exit-cover` repaint is the last thing drawn before power-off. The
composed-root verifier rejects reintroducing show-status/printk changes in that
helper. The quiet shutdown keeps the Greia artwork on screen through power-off.

Second presentation follow-up (same day): removing the diagnostic raise stopped
the systemd stop-job transcript, but `systemd-shutdown` still printed its final
live-medium/loop teardown errors over the Greia cover ("Failed to unmount
/run/live/medium", "Could not detach loopback /dev/loop0", "Failed to finalize
file systems, loop devices, ignoring"). PID1 passes its current log level to
`systemd-shutdown`, and the Manager `LogLevel` property is writable, so the
root finish helper now lowers PID1's log level to `emerg` immediately before
`systemctl poweroff`. This is runtime-only: normal boot logging and the journal
are unaffected, kernel emergencies still print, and the branded cover remains
the last frame. QEMU frame capture of the shutdown (marker created as
`nobody`) ends on the clean Greia splash with no terminal text.

Final media verification (2026-10-18): rebuilt/flashed at `6f3c809c`
(image `47ab4ec639175f8b21aa69aec0f3aa1d172eab7d8a4ce24fdc775f92031fb6a0`,
live media `a1d8e713-5090-4570-be68-83db7cfda8c6`, payload 1,203 MiB; artifact,
USB read-back and loop hygiene PASS). QEMU captured the shutdown triggered by
an unprivileged `nobody` marker: the final frame is the Greia splash with no
terminal text, followed by a clean power-off. Evidence:
`docs/reviews/acer/2026-10-18_QUIET_SHUTDOWN_QEMU_VERIFICATION/` (archived; see git history).

## 37. 2026-09-30 — Microphone processing endpoint was never installed

Symptom: the Parent panel's noise cancelling controls stored correctly and
changed nothing. The API reported
`effective: mode=off, capture_device=default, fallback_reason=lightweight_unavailable`.

Chain, measured on the Acer rather than inferred:

```
/etc/asound.conf defines greia_mic_light                 present
greia-audio-endpoints.service + probe                    present
/usr/lib/i386-linux-gnu/alsa-lib/                        did not exist
arecord -D greia_mic_light                               "No such device or address"
/run/greia-audio/lightweight-ready                       never written
```

The ALSA ExtPlugin in `src/greia_platform/audio_alsa/greia_mic_light.c` was
never compiled or installed, so the PCM could not open. The probe correctly
declined to mark the endpoint ready and the service correctly fell back to
`off`; fail-closed behaviour indistinguishable from "not installed".

Three provisioning gaps, all fixed in `build/lib/compose.sh` and
`build/overlay/`:

- the plugin is now built with the target toolchain inside the root, the way
  the framebuffer renderer is, and installed as
  `libasound_module_pcm_greia_mic_light.so`; this runs before the footprint
  prune, which is what removes `cc1`;
- the probe is `chmod 0755` (it previously failed `203/EXEC`);
- `greia-audio-endpoints.service` is enabled in the target role.

Verified on the Acer after installing the module by hand:

```
backend:   lightweight_capture_device='greia_mic_light'
available: {'lightweight': True, 'advanced': False}
effective: mode='lightweight' capture_device='greia_mic_light' fallback_reason=None
arecord -D greia_mic_light: 64044 bytes at 16 kHz mono
```

Advanced reduction remains unavailable and is reported as such: there is no
`greia_mic_advanced` PCM and no plugin for it. Lightweight is Speex
preprocessing at -15 dB with AGC disabled.

## 38. 2026-09-30 — Two boot loops from provisioning

**Group name that was never created.** `greia-os.conf` named the group
`greiaprofiles`; `compose.sh` creates `pipprofiles`. `systemd-tmpfiles` failed
with "Failed to resolve group" and left `/run/greia-os` as `root:root 0755`.
Xorg runs as `greiakid` and could not open `/run/greia-os/Xorg.0.log`, so
`greia-launcher.service` restart-looped on every boot.

**Child could not traverse the parent home.** The launcher runs as `greiakid`
and activity discovery stats `/var/lib/greia-os/activity-packages`, which sits
under `/var/lib/greia-os` at `0750 greiapel:greiapel`. `greiakid` got `EACCES`
instead of `ENOENT`, so a directory that nothing had ever created presented as
a permission fault:

```
PermissionError: [Errno 13] '/var/lib/greia-os/activity-packages/active'
  greia_platform/activities.py:421 discovery_token
```

`child_shell` exited 1 about 20 s into every start, the trusted-presentation
fallback also exited non-zero, and the unit looped indefinitely. Fixed by
making `/var/lib/greia-os` `0751` (traverse-only; the parent service's files
stay unreadable to the child) and creating the activity package root
explicitly. `tests/test_image_tmpfiles_identities.py` now fails the build if
`tmpfiles.d` names an identity `compose.sh` does not create.

Both loops presented as `is-active` returning healthy; only `NRestarts`
climbing showed them.

## 39. 2026-09-30 — Microphone gain appeared not to respond on the reference Acer

OPEN QUESTION, no product decision taken. A parent raising the gain watched
nothing happen on this machine. Measured on the Acer:

```
amixer scontrols -> Simple mixer control 'Capture',0
Limits: Capture 0 - 31
Mono:  Capture 31 [100%] [31.50dB]
```

`_apply_audio` maps `mic_gain` to an ALSA Capture percentage as
`mic_gain / 2.0`, clamped to 100. So:

```
preset 100% (1.0) -> 50% ALSA
preset 200% (2.0) -> 100% ALSA   hardware maximum
preset 300% (3.0) -> clamped, identical to 2.0
preset 400% (4.0) -> clamped, identical to 2.0
```

On this machine the 300% and 400% presets are therefore indistinguishable from
200%, and 2.0 is the ceiling. That is an observation about one ALSA control on
one device, not a product conclusion: other hardware may expose a higher
Capture limit, a separate `Mic Boost` control (present on the Acer but not yet
characterised), or a different mapping. The 0.5-4.0 product range and the
existing presets are unchanged.

The open design question, for the owner to decide rather than an agent: whether
the achievable range should be discovered per device and surfaced, or whether
the gain control should be expressed in real hardware terms at all. Either way
a parent needs to be told what ceiling they have reached instead of watching a
control that appears inert.

A second finding from the same measurements, recorded because it is an
environment limit and not a defect: with `Capture` pinned at maximum, an internal
ALC268 mic and five fans running, the raw capture floor measured about
-30 dBFS RMS and the processed endpoint about -36 to -38 dBFS, i.e. roughly 7 dB
of attenuation. Normal speech therefore sits only a few dB above the noise
floor. The available remedies are exhausted in software: gain is at maximum,
denoise gives about 7 dB, and the internal mic has no directional response. This
needs a quieter machine or an external microphone to assess speech quality.

## 40. 2026-09-30 — Shareable-device contention between the meter and Activities

Recording stopped working in every microphone-using Activity once the live
Parent meter existed. The ALSA capture device is exclusive and only one holder
wins:

```
meter holding the device continuously   Activity 0 of 6 capture attempts
meter sampling 0.4 s every 1.0 s        Activity 3 of 8
meter sampling 0.15 s every 0.15 s      Activity 7 of 8
```

The meter now samples in short bursts at the protocol's full rate (measured
19.9 lines/s against a 20 lines/s ceiling) and yields for 30 s the moment an
open fails because the device is busy, so an Activity that starts meets a meter
that gets out of the way.

This is not fully solvable by scheduling: there is one capture device and no
signal yet for "an Activity is recording". Until the platform exposes one, the
meter yields on contention rather than competing, and that is a real remaining
limitation rather than a tuning detail.

Note for anyone measuring this later: counting distinct level *values* to judge
meter responsiveness is wrong in a quiet room, because the value does not
change and the meter looks frozen while publishing happily. Measure the publish
rate off the socket.
