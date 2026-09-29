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
