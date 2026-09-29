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
> the only way. See `docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md` §4.

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
`docs/reviews/2026-08-18_REAL_HARDWARE_INSTALLATION_AND_LAUNCHER_REVIEW.md`.

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
