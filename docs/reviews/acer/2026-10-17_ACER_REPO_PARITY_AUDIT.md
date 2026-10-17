# Acer repo parity audit (2026-10-17)

Purpose: before a fresh release-candidate image is built, confirm that every fix tested live on the developer Acer is in the repo, and list device-only state.

- Repo: `main` at `fdbb319f`. Device `/opt/greia-os/.deployed-sha`: `3f3cff7b908c5caefc13cbae51f7c16813de9372`. The two commits after it (`ddee0fa3`, `fdbb319f`) change only `docs/product/ACTIVITY_SYSTEM_NAVIGATION.md` and the Acer sweep review, so the deployed tree equals `HEAD` for code.
- Device: image profile `legacy-x86-i686-dev` (single ext4 root, i686, Debian 12.15, kernel 6.1.0-53-686), installed 2026-10-06.
- Method: read-only (`sudo -n` stat/cat/tar/dpkg/systemctl/journalctl). Nothing on the device was changed; no secrets were read (authorized keys, GRUB recovery hash, Wi-Fi PSK, parent credential were only listed).
- Evidence label: DEVICE STATE OBSERVATION plus SOURCE comparison. It does not prove a fresh image will behave the same.

Classes: (a) device-only fix that must go into the repo; (b) operator/dev provisioning or runtime state, intentionally not in the image; (c) stale state from an older image that the new image replaces; (d) unknown or repo-side defect found while auditing.

## 1. Greia tree parity (`/opt/greia-os`, activity index)

`tools/dev_source_deploy.py stage` of `HEAD` was hashed per file and compared with `sha256sum` of every file under `/opt/greia-os` on the device (bytecode excluded; the device tree has no `__pycache__`).

| Item | Result |
| --- | --- |
| Files in staged bundle / on device | 9031 / 9031 |
| Missing, extra or different content | 0 |
| Only difference | `.deployed-sha` (expected: device holds `3f3cff7b`, bundle holds `fdbb319f`) |
| `/usr/share/greia/activity-index-v1.json` | identical (`dde60498...`) |
| Symlinks in `/opt/greia-os` | none |

Conclusion: every Python/asset/Activity fix tested on the Acer since 2026-10-16 is in the repo. The earlier one-off `parent_panel.py` Python 3.11 hotfix and the temporary `greia-x-session` faulthandler edit are gone (tree is hash-identical; `greia-x-session` is byte-identical to the overlay, sha256 `91d311cf...`).

## 2. System configuration parity

### 2.1 Overlay files (`build/overlay/**`, 94 files)

All 94 paths exist on the device. 89 are byte-identical. Executable bits: five files are committed `0644` but installed `0755/0750` on the device; this is correct, because `usr/lib/tmpfiles.d/greia-*.conf` (`z` lines for `greia-devctl`, `prepare-developer-remote`, `greia-languagectl`, `greia-run-kmsdrm-acceptance`) and `compose_configure_systemd` (audio probe) set the modes on every image. No gap.

| File | Difference | Class | Action |
| --- | --- | --- | --- |
| `etc/greia-os/build-info` | Device has the composer-generated file (version `0.13.0-phase0-dev`, `PIP_BUILD_PROFILE=...`). The overlay copy says `0.12.0` and lacks the profile keys; `compose_write_build_info` always overwrites it from `VERSION`. | (c) | None for the image. Optional: delete or refresh the dead overlay copy so it cannot mislead. |
| `boot/grub/greia-theme.txt` | One comment line is older on the device. | (c) | None. |
| `etc/X11/Xwrapper.config` | Same two directives, different order. | (c) | None. |
| `etc/ssh/sshd_config.d/00-greia-security-floor.conf`, `20-greia-parent.conf` | Operator variant (`PubkeyAuthentication yes`, `AuthenticationMethods publickey password`) written on 2026-10-16 by a one-off script. Backups `*.before-operator` sit beside them. See B1 below. | (b) | See B1. |

### 2.2 Files written by the composer (not in the overlay)

| Item | Device | Image build | Class |
| --- | --- | --- | --- |
| `/etc/greia-os/image-profile.json` | identical to `tools/build_profile.py manifest legacy-x86-i686-dev --scope target` | same | match |
| `/etc/fstab` | identical to `greia_platform.fstab.render_fstab(uuid)` | same | match |
| `/etc/hostname`, `/etc/hosts`, `/etc/apt/sources.list` | `greia-dev`, bookworm main/updates/security | same | match |
| `/etc/sudoers.d/greia-developer-remote`, `/etc/greia-os/developer-remote` | identical to the composer heredoc | same | match |
| `/usr/lib/python3/dist-packages/pip_os.pth` | `/opt/greia-os/src` | same | match |
| `/usr/lib/greia-boot/greia-fb-splash` and initramfs hooks/binary | present, in the initrd | same | match |
| Users/groups | `greiakid`, `greiapanel`, `greiaadmin`, `greia` exist; groups `pipsettings`, `pipprofiles` | same | match, plus A1 |
| `/etc/greia-os/developer-display.json` | absent | written by `compose_write_developer_display_endpoint` (since `560f494f`, 2026-10-07) | (c): image predates the commit; the new dev image gets it |
| `/usr/lib/i386-linux-gnu/alsa-lib/libasound_module_pcm_greia_mic_light.so` | absent (`/etc/asound.conf` references it) | built by `compose_build_audio_endpoint_plugin` (since `e859fb4b`, 2026-09-30) | (c): image predates the plugin; see D2 |

### 2.3 Device-only changes

| # | Device state | Evidence | Class | Recommended action |
| --- | --- | --- | --- | --- |
| A1 | `greiakid` and `greiapanel` were added to group `netdev` (`usermod -aG netdev`), and drop-ins `/etc/systemd/system/greia-launcher.service.d/10-netdev-wifi.conf` and `greia-parent.service.d/10-netdev-wifi.conf` (`SupplementaryGroups=` reset, then `netdev`) were created on 2026-10-15 23:41-23:52. Reason: iwd's D-Bus policy lets only `root` and group `netdev` talk to `net.connman.iwd`; without it the Shell and Parent cannot scan or join Wi-Fi. | `/tmp/fix.sh`, `/tmp/fix2.sh` on the device; `id`, `/proc/<pid>/status` Groups; `/usr/share/dbus-1/system.d/iwd-dbus.conf`. Repo: only the live-installer unit has `netdev` (`build/installer-overlay/.../greia-installer.service`); `compose_create_users_groups` and `greia-launcher.service` (`SupplementaryGroups=audio tty`) do not. | **(a)** | Add `netdev` to the `greiakid` and `greiapanel` group lists in `compose_create_users_groups`; and add `netdev` to the unit `SupplementaryGroups` (launcher: `audio tty netdev`, parent: `netdev`) rather than shipping a drop-in. Note the device drop-in's `SupplementaryGroups=` reset also removed `tty` from the launcher; the device has been tested without `tty`, the new image will have it. Add a contract test next to `tests/test_installation_hardware_regressions.py`. Existing installs need a first-boot migration (or a reinstall). |
| B1 | Operator access for this test device: `/var/lib/greia/.ssh/authorized_keys`, `/etc/sudoers.d/90-greia-dev-operator` (0440), the operator variants of the two sshd drop-ins, `*.before-operator` backups. | `/var/lib/greia/greia-update/setup-operator-access.sh` (one-off, not in the repo). | (b) | Intended not to be in the image. Two caveats for the owner: (1) it is not reproducible from the repo; (2) it does not survive an `ssh.service` restart or reboot: `ssh.service.d/10-greia-developer-bootstrap.conf` runs `prepare-developer-ssh`, which rewrites both drop-ins to `AuthenticationMethods password` on every start. Key login worked only because sshd was reloaded, not restarted (running since 2026-10-15 23:12). After a reboot, `dev_source_deploy.py` (BatchMode, key only) will stop working until the script is re-run. Decide whether to keep this as a documented, tools-owned step. |
| B2 | Installer-written state: `/etc/greia-os/install-record.json`, `root-filesystem-uuid`, `grub-recovery.pbkdf2` (root-only), `/etc/default/keyboard`, `/etc/machine-id`, SSH host key, packages `intel-microcode` and `iucode-tool` (hardware enablement). | `install-record.json` (`hardware_support_packages`), dpkg diff against `/etc/greia-os/package-manifest.tsv` (only those two added, nothing removed). | (b) | None. |
| B3 | Runtime user state: iwd known network (PSK file), `/var/lib/greia-os/main-credential.json`, `parent-devices.json`, the one profile tree under `/var/lib/greia-profiles`, ALSA `asound.state`. | listing only | (b) | None. Wipe or reinstall to start clean. |
| C1 | `greia-boot-observer.service` is enabled and failed: `status=226/NAMESPACE`. | The unit bind-mounts `/etc/greia-os/installed-layout.json` and `release-identity.json`; neither exists on this single-root layout. Journal for that boot is rotated. `compose_configure_systemd` now enables the observer only when `STORAGE_LAYOUT_ADAPTER` ends in `-ab-v1` (`82b82ac5`, 2026-10-07); profile `legacy-x86-i686-dev` is `bios-single-ext4`. | (c) | None for the image. Optionally `systemctl disable` on the device to stop the failed-unit noise (owner's call). |
| C2 | `.profiles.lock` is `greiapanel:pipprofiles 0660`, `activities/` dirs are parent-owned `2770`. | Repaired once by the one-off `apply-update.sh`; the temporary `chown greiakid` workaround from the sweep was undone. Source covers both: `ProfileStore` chmods the lock to `0660` (`profiles.py:685,875`), commit `2af434da` accepts a parent-owned `2770` activities folder, first-boot migration `b5-profile-shared-modes-v1` ran on 2026-10-16. | (c) | None. |
| C3 | Test debris: `/var/lib/greia/newtree` (247 MB), `/var/lib/greia/greia-update` (192 MB, includes `payload.tar.gz`, `apply-update.sh`, `hotfix-parent-panel.sh`), `parent-try.log`; `/tmp` scripts and PNGs (volatile tmpfs). | listing | (c) | Safe to remove, but per global rules this audit did not delete anything. Ask the owner. `tools/dev_source_deploy.py` replaced the `apply-update.sh` flow. |

### 2.4 Services

Image enable list (`compose_configure_systemd`, target): `greia-first-boot`, `greia-launcher`, `greia-parent`, `greia-boot-health.socket`, `greia-system-update.socket`, `greia-audio-endpoints`, `greia-microphone-level.socket`, `systemd-networkd`, `systemd-resolved`, `iwd`, `avahi-daemon` (+ `greia-boot-observer` only on A/B layouts), plus `ssh` for developer profiles; masks for getty, console-getty, debug-shell, emergency, rescue, console-shell, `kbrequest.target`; default target `graphical.target`.

Device: all of these are enabled and the masks match; `get-default` is `graphical.target`. Extra enabled units: `greia-boot-observer` (C1). Not enabled, as in the image: `greia-developer-remote`, `greia-intro-sweep`, `greia-microphone-level.service`, `greia-candidate-recovery.timer`. Remaining enabled units are Debian defaults (apt-daily timers, fstrim, e2scrub, dpkg-db-backup, network-generator, pstore). The sysctl values in effect equal `99-greia-kiosk.conf` and `30-greia-panic-reboot.conf`.

Failed units:

| Unit | Why | Class |
| --- | --- | --- |
| `greia-boot-observer` | see C1 (missing layout/release-identity files for the unit's namespace) | (c) |
| `greia-developer-remote` | Disabled; failed with `Result: signal`, killed by `SIGTERM` on 2026-10-16 05:11:51 when it was started manually (journal rotated). The script it ran wrote the developer ethernet files at 05:11 and then stopped. See D1. | (d) |

### 2.5 Packages and boot

- Package set `legacy-x86-i686-dev` resolves to 45 direct packages (`tools/build_profile.py packages ... --scope target`). All 45 are installed on the device, including `alsa-utils`, `libspeexdsp1`, `python3-pygame`, `python3-pil`, `bubblewrap`, `iwd`, `xserver-xorg-core`, `xserver-xorg-legacy`, `xserver-xorg-input-libinput`, `xserver-xorg-video-intel/vesa/fbdev`, `xinit`, `xdotool`, `grub-pc`, `linux-image-686`. Build-only packages (`gcc`, `libklibc-dev`, `libasound2-dev`, `libspeexdsp-dev`) are not installed, as intended. No Plymouth, PulseAudio daemon or PipeWire (none are in the package sets). Installed count 359 vs manifest 357 (the two installer additions in B2).
- `/proc/cmdline` is `root=UUID=... ro loglevel=4 systemd.show_status=true rd.systemd.show_status=true udev.log_priority=4 vt.global_cursor_default=1 console=tty1 panic=0 systemd.crash_shell=no systemd.crash_chvt=0 consoleblank=0`. This is exactly what `build/overlay/etc/grub.d/10_greia_appliance` generates for a developer image (`/etc/greia-os/developer-remote` present). `/etc/default/grub` is stock plus the overlay drop-in `10-greia-quiet.cfg`. Match.

## 3. Commit messages and docs that mention a device-side manual step

| Manual step on the device | In source? |
| --- | --- |
| Temporary `chown greiakid` of the profile `activities/` dir to get past the launch crash (sweep review) | Yes: `2af434da`. Device state was restored to the parent-owned `2770` layout. |
| `session.err` edit of `greia-x-session` (`-X faulthandler`) | Restored byte-identical (verified); launcher logging reaches the journal since `dd26f16d`. |
| `parent_panel.py` Python 3.11 hotfix | Yes: `ce2e2c95`, `7f745bca`; tree hash-identical. |
| `SDL_FRAMEBUFFER_ACCELERATION=0` proposed in the sweep | Yes: `3a295306`; present in `greia-launcher.service` and `runtime_adapter.py`. |
| `.profiles.lock` chgrp/chmod in `apply-update.sh` | Yes (code sets 0660 at creation). |
| Wi-Fi: `usermod -aG netdev` and unit drop-ins | **No.** Only in `/tmp` scripts on the device (A1). No commit message, plan or handover mentions it. |
| Operator key, sudoers, sshd operator variant | Not in the repo by design (B1), and `setup-operator-access.sh` exists only on the device. |

## 4. Defects and open questions found while auditing (class d)

| # | Finding | Recommended action |
| --- | --- | --- |
| D1 | `greia-developer-remote.service` / `prepare-developer-remote` is shipped in the overlay but is not enabled by `compose_root` or `build-developer-image.sh` (only the retired key-provisioning tools enable it), so on the current dev-image path it never runs. If started it cannot complete: (1) the unit has `Requires=systemd-networkd.service systemd-resolved.service` and the script runs `systemctl restart` on both, which restarts or stops the unit itself (matches the observed SIGTERM; inferred, the journal is rotated); (2) `chown -R greiaadmin ... /var/lib/greia-admin/.ssh` and `chmod 0600 authorized_keys` fail under `set -e` when no operator key was provisioned (the current dev workflow provisions none). | Owner decision: delete the unit and script (and `tests/test_developer_remote.py` expectations) as part of the retired workflow, or fix both points and enable it. Until then the failed state on this device is harmless. |
| D2 | `compose_build_audio_endpoint_plugin` runs inside `compose_build_audio_endpoint_plugin "$rootfs" \|\| return 1`, where `set -e` is suppressed, so a failing `gcc` or `install` is ignored. No artifact verifier (`tools/verify-development-target-image.sh`, `build/verify-image-qemu.sh`) checks that the `.so` exists. This is the failure mode the function's own comment describes (microphone processing silently off). The Acer cannot confirm the plugin because its image predates it. | Add an explicit check after the build step (and in the artifact verifier) that `libasound_module_pcm_greia_mic_light.so` exists for the target multiarch dir. After the RC image boots, confirm `/etc/asound.conf`'s `greia_mic_light` opens. |
| D3 | Identity naming mismatch: `AGENTS.md` lists groups `greiaprofiles` and `greiasettings`, but the composer, tmpfiles, first-boot, installer engine and tests all use `pipprofiles` / `pipsettings`, and no rename exists in source. The device matches the repo, so the new image will again create `pip*` groups. | Either correct `AGENTS.md` or schedule the rename together with a migration. Do not assume the device is "stale" on this point. |
| D4 | `/tmp` holds 77 empty `pulse-XXXXXXXX` directories owned by `greiakid` (one per child process start since boot), meaning SDL probes PulseAudio (`libpulse0` is present as a dependency) before ALSA. Harmless now (tmpfs, 40 bytes each) but unbounded over a long uptime, and it contradicts the single-ALSA-owner design. `SDL_AUDIODRIVER` is in the platform-owned environment allowlist but not set. | Set `SDL_AUDIODRIVER=alsa` in the Shell and Activity environment, or confirm why it is not. Low priority. |

## 5. Counts

| Class | Count | Items |
| --- | --- | --- |
| Tree parity | 0 real differences | `.deployed-sha` only |
| (a) must go into repo | 1 | A1 |
| (b) provisioning / runtime state | 3 | B1, B2, B3 |
| (c) stale, replaced by new image | 8 | build-info, grub-theme comment, Xwrapper order, developer-display.json, ALSA plugin (see D2), C1 observer, C2 profile repairs, C3 test debris |
| (d) unknown / repo-side defects | 4 | D1 to D4 |

## 6. Before building the RC image

1. Fix A1 (netdev) in `compose.sh` and the two unit files, with a test.
2. Decide D1 (remove or repair the developer-remote unit) and D3 (`AGENTS.md` identity names).
3. Add the D2 check so the microphone plugin cannot be silently missing.
4. Tell the owner that the operator SSH key path is lost on any `ssh` restart or reboot of this device (B1).
