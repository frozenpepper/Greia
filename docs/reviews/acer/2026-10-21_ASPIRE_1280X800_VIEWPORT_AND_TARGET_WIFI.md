# Aspire 1280×800: Activity viewport and target Wi-Fi firmware

**Date:** 2026-10-21  
**Evidence classes:** SOURCE, FOCUSED TESTS, DEVICE/PHYSICAL (remote input), BUILD + USB READ-BACK  
**Device:** Acer Aspire laptop, 1280×800 panel, installed `legacy-x86-i686-rc`, image
`build_utc=2026-10-19T08:10:13Z`, Intel `iwl3945` Wi-Fi. Remote work used the
developer SSH account and `xdotool`/PIL captures; this is remote input, not a
hands-on physical-input acceptance.  
**Repository:** `main` `4fc0fee11` plus the suspend hook `9636e737` at the
correction; the initial fixes are `0a0b4659` (viewport), `813b43d0`
(complementary post-copy refresh) and `a8a64fdd` (executable `build_profile`
CLI). The installed device was source-deployed at the pre-rebase equivalent
`a2ac1386`; the rebuilt image in §2.6 was built from `fa15c88f` and predates
`4fc0fee11`.  
**Rebuilt image:** SHA-256
`ff339ad76b65acd4c0f998c81da61577127400c4aee13a59963e68d2bcd4838e`,
live media id `7b50ef65-a0a8-4427-afb3-667ef37a52d1`, payload accounted
**1,257 MiB** (< 1,300 owner gate).

---

## 0. Headline

1. **Activities opened a 1024×600 window on the 1280×800 panel.** The Activity
   itself was healthy; the window was smaller than the Shell, so the uncovered
   Shell kept its old pixels and its hidden pointer. The platform now replaces
   the Activity's requested `set_mode` size with the exact Shell viewport.
   Verified on the device: `alfabeto_leo` surface is `1280x800+0+0`, fills the
   panel, Home remains above it.
2. **The installed target lacked Wi-Fi firmware.** `iwl3945` could not load
   `iwlwifi-3945-2.ucode`; `iwd` had a wiphy but no usable station, so the
   installed OS found no networks. The live installer worked because it carries
   the broad firmware cover. The device was repaired with
   `firmware-iwlwifi`. **The actual source cause was
   `ProtectKernelModules=yes` hiding `/usr/lib/modules` from the install
   service**, so `modinfo` reported every driver as unknown and no driver
   firmware was selected. See §6; `4fc0fee11` fixes that. The post-copy refresh
   from `813b43d0` remains a complementary late-binding guard, not the root
   cause.
3. **The LaCie image in §2.6 predates the real firmware fix and the
   suspend/resume hook.** It includes the viewport fix and the initial
   post-copy refresh, and its gates pass. Rebuild and clean-install again after
   `4fc0fee11` + the resume hook; that is the next acceptance step.

---

## 1. Activity viewport

### 1.1 Symptom

On the installed 1280×800 laptop, an Activity opened at 1024×600. The right and
bottom bands showed the last Shell frame; the pointer disappeared when moved
into them. The Activity logic and its own content were fine.

### 1.2 Root cause

While R7 is open, first-party Python Activities call `pygame.display.set_mode`
themselves. Most built-ins call:

```python
pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
# REFERENCE_WIDTH/HEIGHT = 1024x600
```

On the reference 1024×600 netbook that happens to equal the screen. On
1280×800 it creates a smaller SDL window over the still-mapped Shell window.
`PygameReferenceCanvas` was already mapping the 1024×600 design correctly; it
never received the real physical surface.

### 1.3 Implementation

New module: `src/greia_platform/activity_display.py`.

| Member | Contract |
| --- | --- |
| `VIEWPORT_ENVIRONMENT` | `GREIA_ACTIVITY_VIEWPORT`, platform-owned `WIDTHxHEIGHT` of the current Shell surface |
| `parse_viewport(value)` | strict bounded `WxH` parser (320..7680 × 240..4320); invalid/empty returns `None` |
| `remember_viewport(size)` | writes the current Shell size into the process environment for the next launch; bounds-checked |
| `current_display_size(pygame, index)` | real desktop size via `pygame.display.get_desktop_sizes()`, falling back to `pygame.display.Info()`; never guesses when no display exists |
| `target_viewport(pygame, environ, index)` | recorded Shell viewport first, desktop size second |
| `normalize_display_request(size, flags, target_size)` | replaces only the size; flags are preserved |
| `install_display_request_policy(pygame, environ)` | wraps `pygame.display.set_mode`, records the original, returns it |

The wrapper keeps the Activity's flags (`RESIZABLE`, `FULLSCREEN`, `NOFRAME`
etc.). It handles both the modern keyword signature and the legacy
`set_mode(size, flags, depth)` form. It is fail-soft: no desktop/session
viewport means the Activity's request is left alone.

Wiring:

- `src/greia_platform/python_activity_entry.py` installs the mixer lease, then
  the display policy, then the launch cover, then runs the Activity. The order
  matters: the launch cover wraps the policy, so its hidden/shown first-window
  calls are normalized too, and after the cover removes its own wrapper the
  policy remains installed for later re-modes.
- `src/greia_launcher/main.py` and `src/greia_launcher/presentation.py` call
  `remember_viewport(screen.get_size())` after the initial `set_mode` and on any
  `VIDEORESIZE`. A windowed developer Shell therefore passes its 960×540
  surface rather than the desktop size.
- `src/greia_launcher/supervisor.py` adds `GREIA_ACTIVITY_VIEWPORT` from the
  launcher process to every supervised Activity environment. It is empty when
  no Shell has recorded a size; the entry then falls back to the real desktop.
- `src/greia_simulator/python_activity.py` is unchanged: the Simulator already
  normalizes `set_mode` to its selected synthetic viewport and never uses the
  production entry's policy.

The launch card is captured at the Shell surface size, so the card, the first
Activity window and the final Activity frame now all match.

### 1.4 Author contract

Updated in `docs/design/GREIA_ACTIVITY_CANVAS_AND_VIEWPORT_AUTHORING.md` §9.1
and `skills/greia-activity-authoring/SKILL.md`:

- `screen.get_size()` is the real session viewport, not `1024×600`.
- Use `PygameReferenceCanvas`, `PygameCanvasMapper` or `ChildUiMetrics` for
  layout and pointer mapping.
- Do not open a smaller window because the reference canvas was 1024×600.
- Outside a Greia session (tests, headless captures, direct developer runs)
  the requested size is left untouched; fixtures must not depend on the
  production normalization.

### 1.5 Tests

- `tests/test_activity_display.py`: parser/bounds, environment precedence,
  desktop fallback, flag preservation, legacy three-argument retry, and a real
  subprocess through `greia_platform.python_activity_entry` at 1280×800.
- `tests/test_activity_launch_cover.py`: updated to assert that the first and a
  second `set_mode` both fill the recorded viewport in a session, and that the
  request is untouched outside a session.
- `tests/test_supervisor.py`: environment construction still passes.

Run:

```bash
find src tests -name __pycache__ -type d -prune -exec rm -rf {} +
PYTHONPATH=src python3 -m unittest tests.test_activity_display tests.test_activity_launch_cover -v
PYTHONPATH=src:tests python3 -m unittest tests.test_supervisor -v
```

### 1.6 Device verification

After `greia-devctl source-deploy` and a Shell restart, the installed device was
driven with `xdotool` on `DISPLAY=:0`:

```text
Window 1088
  Position: 0,0
  Geometry: 1280x800
Window 8388609
  Position: 0,0
  Geometry: 84x84     # trusted Home overlay
```

The `alfabeto_leo` capture shows the sky/ground scene and card filling the full
1280×800 panel, with the platform Home control still at top-left. Before the
fix the same Activity occupied only the top-left 1024×600 region.

### 1.7 Limits and risks

- The policy picks the display index passed to `set_mode` (normally 0); a
  multi-monitor Activity that intentionally targets another display is not
  separately designed yet.
- A future Web runtime must implement equivalent viewport semantics; this
  module is the Python-runtime adapter, not a universal renderer contract.
- This does not select a compositor or change R7 display ownership.
- `make verify` is not an aggregate green gate: the fast lane ran 5,480 tests
  with the inherited ARM64-profile error, the known `morbidi_mostriciattoli`
  start-up-budget flake and the stale MBR-message expectation. The
  `build_profile` executable-mode test error was fixed by `a8a64fdd`. The
  focused suites above pass.

---

## 2. Target Wi-Fi firmware

### 2.1 Symptom

The installed OS found no Wi-Fi networks. The same laptop found and joined the
network during installation from the live installer.

### 2.2 Root cause

**Correction (see §6):** the primary source cause was
`ProtectKernelModules=yes` on `greia-install-transaction.service` (and the
system-update service), which hid the module tree from `modinfo`; the resolver
treated the resulting exit 1 as a built-in driver. The late-binding refresh in
§2.3 runs in the same sandbox and could not change that. The text below records
the observed target state; §6 owns the corrected source cause.

On the installed system:

```text
iwl3945 ... firmware: failed to load iwlwifi-3945-2.ucode (-2)
iwl3945 ... Could not read microcode: -2
iwd: Wiphy phy0 ... Error bringing interface up
```

`firmware-iwlwifi` was not installed. The live installer carries the broad
firmware cover (`build/install-live-hardware-firmware.sh`), which is why its
scan worked. The target's ordinary support plan recorded only
`["intel-microcode"]` in `/etc/greia-os/install-record.json`, despite the
bound `iwl3945` driver declaring `iwlwifi-3945-2.ucode`.

### 2.3 Implementation (complementary late-binding refresh)

**This was not the root-cause fix.** It remains useful for a genuinely
late-binding driver, but it runs inside the same module-hiding sandbox and
therefore could not install `firmware-iwlwifi` on the Aspire. The real fix is
`4fc0fee11` (§6).

The pre-erase plan remains the fail-closed safety authority. A second complete
inventory now runs after the payload copy and before target configuration:

- `src/greia_installer/engine.py::InstallationEngine._refresh_hardware_support`
  reloads and re-verifies the same frozen hardware-support pool, takes a fresh
  `InstallerHardwareEnablementPlanner.linux_default(pool=...).plan()`, and
  merges it into the initial decision.
- `src/greia_installer/hardware_enablement.py::merge_hardware_enablement_plans`
  unions `required_firmware` and `required_microcode`, deduplicates/sorts, and
  keeps the initial plan unchanged when the refresh is incomplete. Only
  packages already accepted by the verified pool can enter the target.
- The refreshed result is used by `_write_initial_configuration`, so
  `install-record.json` records the final merged package list.
- The old plan was taken at the start (2%) and used unchanged at the target
  install (74%). The refresh at 68% is specifically for drivers that finish
  binding while the payload is copied; it does not weaken the pre-erase check.
- A refresh failure or incomplete refresh is logged to the install-transaction
  journal and the initial plan is kept. No network repository or guessed
  package is introduced; the local verified pool remains the only source.

Why not simply ship all firmware in the target: the broad cover is hundreds of
MiB and the owner gate is 1,300 MiB. The image already carries the local pool
for machine-specific selection.

### 2.4 Device recovery (installed system)

The current installed system was repaired in place, not reinstalled:

```bash
# The device RTC/clock was at 2026-04-27, so HTTPS TLS failed until corrected.
sudo date -u -s '2026-10-21 07:32:00'
sudo apt-get update
sudo apt-get install -y firmware-iwlwifi
sudo modprobe -r iwl3945; sudo modprobe iwl3945
sudo systemctl restart iwd
```

Result:

```text
wlan0: associated
systemd-networkd: wlan0: Connected WiFi access point: Wireless Pendente
networkctl: State: routable (configured), Address: 192.168.68.112 (DHCP4)
iwctl: State connected, IPv4 address 192.168.68.112
```

The saved installer-carried profile reconnected without re-entering the
passphrase.

### 2.5 Tests

- `tests/test_installer_hardware_enablement.py::HardwarePlanRefreshTests`:
  late-bound firmware is merged; an incomplete refresh cannot weaken the initial
  plan; duplicates are deduplicated/sorted.
- Existing planner/resolver tests (firmware provider mapping, wildcard
  declarations, modinfo exit 1, missing providers, advisory packages) still
  pass.
- `tests.test_installer_engine` and the hardware-support installer/service
  tests pass.

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_installer_hardware_enablement -v
PYTHONPATH=src python3 -m unittest tests.test_installer_engine -v
```

### 2.6 Image rebuild and flash (predates the real firmware fix)

**This image was built from `fa15c88f`, before `4fc0fee11` and the suspend
hook. It is not the final Wi-Fi acceptance image.** The data below is retained
as the media/build evidence for the viewport + initial-refresh candidate.


```text
source: fa15c88f (viewport + firmware refresh + executable build_profile + v0.3 masters)
image: ff339ad76b65acd4c0f998c81da61577127400c4aee13a59963e68d2bcd4838e
live_media_id: 7b50ef65-a0a8-4427-afb3-667ef37a52d1
payload: 1,257 MiB
target_payload_bytes: 518,950,912
boot_console_policy: quiet
artifact verification: PASS
USB read-back: PASS (independent re-run also PASS)
loop hygiene: PASS
```

Written to the authorized 8 GB LaCie (`/dev/sdc`, `iamaKey`, serial
`eca3505216d7d3`) through
`tools/build-and-flash-development-usb.sh legacy-x86-i686-rc /dev/sdc ./out
--operator-key /home/orb/greia-rc/greia-operator.pub` inside
`sudo -n unshare --mount --propagation private`.

### 2.7 Limits and risks

- **Clean install from the new image is still unproven.** The installed device
  was repaired manually; the new image's automatic firmware selection should be
  accepted by installing from the rebuilt LaCie.
- The refresh can only see drivers bound at 68%. If the live installer has not
  bound a device at either inventory, the target still cannot infer its
  firmware. A future hardening step should verify selected target firmware
  against the bound drivers and fail/repair visibly rather than shipping a
  silent gap.
- The target package set still lacks `iproute2`/`iputils-ping` (observed:
  `ip` and `ping` are not installed). Diagnostics currently use `networkctl`
  and `iwctl`; this is a separate diagnostics/package-composition gap.
- The installed system clock was wrong (`2026-04-27`) and
  `timedatectl set-ntp true` reports `NTP not supported`; it was corrected
  manually for package installation. Clock/real-time-clock provisioning is a
  separate open issue.
- The rebuilt image was built just before concurrent `a3e70618` (voice-corpus
  audio replacement). The display and Wi-Fi fixes are in it; the latest audio
  replacement is not. Rebuild after that workstream settles if the image must
  contain it.

---

### 2.8 Follow-up: suspend/resume, not firmware

The firmware repair made Wi-Fi work for hours, but the link was still not
stable. At 14:55 the laptop lid was closed and reopened. The kernel did resume,
but the wireless resume callback failed:

```text
iwl3945 0000:06:00.0: Unable to change power state from D3hot to D0,
device inaccessible
iwl3945 0000:06:00.0: Wait for START_ALIVE timeout after 2000ms.
ieee80211 phy1: PM: failed to resume async: error -110
iwd: Received Deauthentication event, reason: 3
networkd: wlan0: Lost carrier; Link DOWN
```

`operstate` became `down`, `networkctl` showed `off (configured)`, and
`iwctl` reported `No station on device: 'wlan0'`. The interface did not recover
on its own. Reloading the driver did recover it without a reboot:

```bash
sudo modprobe -r iwl3945
sudo modprobe iwl3945
sudo systemctl restart iwd
# iwd re-associated with the saved profile; DHCP returned 192.168.68.112
```

Target fix: `build/overlay/usr/lib/systemd/system-sleep/greia-wifi-resume`.
The `systemd-sleep` post hook:

- runs only for `post` and only when `iwl3945` is loaded (no-op on other
  hardware);
- bounds both `modprobe` calls with `timeout 20`;
- reloads `iwl3945` and `try-restart`s `iwd`, which re-associates with the
  existing saved profile;
- is target-only; it does not add network authority or change the child API.

Contract test:
`tests/test_system_overlay_contract.py::test_iwl3945_resume_hook_is_installed_executable_and_bounded`.

Manual verification on the installed device: copying the hook to
`/usr/lib/systemd/system-sleep/` and invoking
`greia-wifi-resume post` brought `wlan0` back to `routable (configured)` with
`192.168.68.112` and HTTPS to `deb.debian.org` returned 200.

**Test caution:** an unattended `rtcwake -m mem -s 20` on this laptop did
**not** wake from the RTC alarm; the machine stayed suspended and had to be
woken with the power button. The lid-close/ lid-open path is the path that was
observed to resume (with the `wiphy_resume` failure). Do not use `rtcwake` as
an unattended acceptance step on this hardware without first proving its RTC
alarm wake.

## 3. Commands for other agents

Check source state and focused tests:

```bash
git status --short
git rev-parse HEAD
find src tests -name __pycache__ -type d -prune -exec rm -rf {} +
PYTHONPATH=src python3 -m unittest \
  tests.test_activity_display tests.test_activity_launch_cover \
  tests.test_installer_hardware_enablement tests.test_installer_engine -v
```

Inspect an Activity surface on a device (remote input, not physical evidence):

```bash
DISPLAY=:0 xdotool search --onlyvisible --name '.*' \
  | while read id; do xdotool getwindowname "$id"; xdotool getwindowgeometry "$id"; done
DISPLAY=:0 python3 -c 'from PIL import ImageGrab; ImageGrab.grab().save("/tmp/screen.png")'
```

Check Wi-Fi and target firmware:

```bash
networkctl status wlan0
iwctl station wlan0 show
dmesg | grep -i iwl
dpkg -l firmware-iwlwifi
```

Deploy source to a developer image (SSH key login and passwordless
`greia-devctl` are required; the installed RC uses key+password or the
developer password):

```bash
python3 tools/dev_source_deploy.py deploy --target greia@greia-rc.local
python3 tools/dev_source_deploy.py status --target greia@greia-rc.local
```

Build and flash only with whole-device owner authorization:

```bash
sudo bash tools/build-and-flash-development-usb.sh \
  legacy-x86-i686-rc /dev/sdX ./out --operator-key /path/operator.pub
```

---

## 4. Commit map

| Commit | Purpose |
| --- | --- |
| `0a0b4659` | Activity display policy, launcher/supervisor plumbing, design/skill docs, tests |
| `813b43d0` | Post-copy hardware-support refresh, merge helper, installer doc, tests |
| `a8a64fdd` | Restore executable mode of `tools/build_profile.py` (unblocked its CLI test) |
| `443044fc` | HANDOVER + lifecycle evidence for the Aspire fixes |
| `fa15c88f` | Point evidence at rebased commit hashes |
| `9271f0ac` | Record the rebuilt/flashed RC image |
| `4fc0fee11` | **Real firmware-selection fix:** remove `ProtectKernelModules`, gate on `LinuxKernelModules`, refuse incomplete resolution |
| `9636e737` | Suspend/resume `iwl3945` recovery hook and contract test |

The device itself reports `.deployed-sha=a2ac13868028434e1ad4e84e5ea581fed1744000`
(the pre-rebase equivalent of `0a0b4659`+`813b43d0`+`a8a64fdd`). A future source
deploy or clean install will move it to the current `main`.

---

## 5. Next exact steps

1. Rebuild/flash with `4fc0fee11` plus the `iwl3945` resume hook (the current
   LaCie predates both), then install on a disposable/approved target (or on
   this Aspire after owner approval) and confirm:
   - the installed target contains `firmware-iwlwifi` (or the pool-selected
     package) and `iwd` connects without manual package installation;
   - the install record lists the final support packages;
   - Activities fill the real panel and the pointer remains visible everywhere;
   - closing/opening the lid leaves Wi-Fi connected automatically.
2. Run the Acer premortem §5 F1–F19 physical checklist, including the hidden
   `verbose` recovery path.
3. Decide whether to add a post-install firmware verification/repair step and
   whether `iproute2`/NTP provisioning belong in the target package set.

---

## 6. Correction (2026-10-21, later the same day): the real firmware root cause

§2.2/§2.3 attributed the missing `firmware-iwlwifi` to a driver that bound
late. That does not fit: the installer had already joined Wi-Fi, so
`iwl3945` was bound when the pre-erase plan ran. The actual cause was the
install service's own sandbox: `ProtectKernelModules=yes` hides
`/usr/lib/modules`, `modinfo -F firmware <driver>` exits 1 ("module not
found"), and the resolver treated exit 1 as a built-in driver. No driver
firmware was selected on any machine; the `813b43d0` refresh runs inside the
same sandbox and returns the same empty result. The fix, tests and sandbox
evidence are recorded in `HANDOVER.md` and the lifecycle plan under
"Firmware selection unblocked inside the install/update sandboxes". The image
in §2.6 predates that fix.

