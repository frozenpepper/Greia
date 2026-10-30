# Greia OS Boot Pipeline & Display Operating Guide

> **Audience:** agents and engineers working on Greia OS boot, graphics, initramfs, first-boot/systemd services, installer media, GRUB/Syslinux, Xorg startup and physical recovery.  
> **Status:** **derived mandatory operating guide**. Exact implemented contracts remain owned by source/runtime declarations; accepted ADRs/product requirements outrank this guide.  
> **Reviewed:** 2026-08-24 after the reference-Acer boot-loop/recovery incident.

For any substantive boot/recovery work, also read the mandatory OS-skill companion:

```text
skills/greia-os-work/BOOT.md
```

The historical incident record remains in:

```text
docs/engineering/boot/INSTALLED_OS_BOOT_POSTMORTEM.md
docs/engineering/boot/INSTALLATION_ISSUES_LOG.md
docs/engineering/boot/INSTALLATION_USB_BOOT_POSTMORTEM.md
```

Do not copy a command or constant from an old postmortem without checking current source.

---

## 1. Boot is a chain of separately owned artifacts

Treat these layers independently:

```text
firmware / removable-media bootloader
  -> GRUB or Syslinux policy
  -> kernel command line
  -> initramfs + root-device discovery
  -> installed root mount
  -> first-boot / recurring systemd prerequisites
  -> VT/display-server acquisition
  -> Greia launcher
  -> launcher-owned intro
```

A source edit is not proof of the generated artifact that executes on the machine. Before changing boot behavior, identify the first known-working layer, the first failing layer, which artifact the target actually executes, and what build/install step may regenerate it later.

---

## 2. Current artwork lineage and display behavior

### 2.1 Canonical source artwork

The retained full-colour Professor Pip frame is the source artwork:

```text
assets/boot/frames/frame_0051.png
```

Its current expected source size in `tools/generate_boot_artwork.py` is:

```text
222 x 600
```

Never use thresholding, colour-distance keying, binary masking or automated background removal on these frames. Earlier experiments destroyed dark pupils, outlines, shading and antialiasing.

### 2.2 Generated GRUB / early-framebuffer presentation canvas

Current source does **not** hand the raw 222×600 portrait directly to every boot layer. `tools/generate_boot_artwork.py` currently creates one canonical **1024×600 white presentation canvas**, pastes the untouched 222×600 source at native size in its center, and emits:

```text
assets/boot/static/greia-boot-logo.png
build/overlay/etc/greia-boot/boot-logo.ppm
build/installer-overlay/etc/greia-boot/boot-logo.ppm
build/overlay/boot/grub/greia-theme.txt
```

That 1024×600 canvas is a current intermediate composition, not permission to generate a different baked asset for every physical display. Runtime adapters still fit the whole composition proportionally to the actual viewport.

If this intermediate design changes, update generator source, tests, design docs and finished-image verification together. Do not silently treat an old 1600×900 description or a raw-portrait description as current implementation truth.

### 2.3 GRUB presentation

Current installed GRUB uses a theme rather than raw `background_image` stretching:

```text
title-text: ""
desktop-color: "#ffffff"
desktop-image: "greia-boot-logo.png"
desktop-image-scale-method: "padding"
desktop-image-h-align: "center"
desktop-image-v-align: "center"
```

The normal Greia menu entry remains automatic and `--unrestricted`. GRUB edit/command access is protected separately by the owner credential.

### 2.4 Early framebuffer renderer

`build/early-boot/greia-fb-splash.c`:

1. opens `/dev/fb0` and reads real geometry/pixel format;
2. fills the framebuffer using the generated composition's background pixel;
3. proportionally fits and centers the **whole generated PPM composition**;
4. fails soft if the framebuffer/pixel layout is unsupported;
5. emits no console text of its own.

**Release acceptance (2026-10-28):** the early framebuffer backend is
registered release-safe for the technical-preview composition after the
recorded QEMU visual acceptance in
`2026-10-28_BOOT_COVER_ACCEPTANCE.md` (archived; see git history). Physical Acer visual
acceptance and any ordinary-family release decision remain separate.

The renderer currently still supports explicit milestone progress through `--progress`. That behavior is also reflected by `docs/design/GREIA_BOOT_PROGRESS.md` and `tests/test_boot_progress_contract.py`.

**Do not claim the progress bar has been removed while those sources still draw and require it.** If the product decision is to remove progress presentation later, source, stage scripts, launcher handoff, tests and docs must change in one reviewed tranche and receive physical visual acceptance.

### 2.5 Launcher intro

`src/greia_launcher/boot_intro.py` owns the animated handoff after a real graphical surface exists.

The intended timing contract is:

```text
ANIMATION_SECONDS = 5.0
FINAL_FRAME_HOLD_SECONDS = 2.0
MAX_INTRO_SECONDS = 7.0 total intentional presentation time
```

The complete 52-frame sequence is spread across the five-second animation phase. After the final animation frame is presented, that exact final frame remains visible for an additional two seconds before the profile picker replaces it.

Timing is driven by `time.monotonic()`. The display/event connection is pumped during the intentional presentation so the launcher does not appear frozen. The intro remains one-shot per boot through the runtime marker under `/run/greia-os`.

The temporary 2.2/2.5-second implementation committed during the recovery session was not the intended product design and has been corrected. Do not shorten the animation merely as a generic boot-speed optimization: this seven-second sequence is intentional product presentation unless the owner explicitly changes it.

---

## 3. GRUB owner recovery contract

The current owner-approved default is intentionally simple:

```text
GRUB user:     greia
GRUB password: greia
```

Normal automatic boot does not ask for it; the Greia OS entry is `--unrestricted`. It protects GRUB editing/command access.

Rules:

- never reintroduce the historical default user `greia-recovery`;
- never make a generated random string the default owner recovery credential;
- the installed target stores the password as a PBKDF2 hash;
- default provisioning does not require a plaintext random recovery-code file on the target;
- installer-media and installed-target GRUB generation must use the same canonical identity;
- validate generated `grub.cfg`, not just the template.

Canonical source owners include:

```text
src/greia_platform/grub_security.py
build/overlay/etc/grub.d/01_greia_auth
build/overlay/etc/grub.d/10_greia_appliance
src/greia_platform/boot_contract.py
```

---

## 4. Developer SSH is a boot-recovery invariant

For explicit development/test images the owner-approved login is:

```text
user:     greia
password: greia
```

Root SSH remains disabled.

The effective developer policy must allow the password **by itself**:

```text
PasswordAuthentication yes
KbdInteractiveAuthentication no
AuthenticationMethods password
PermitRootLogin no
AllowUsers greia
```

Do not use:

```text
AuthenticationMethods publickey,password
```

because OpenSSH interprets that as requiring both methods, defeating password recovery.

`build/overlay/usr/local/lib/greia-os/prepare-developer-ssh` owns the boot-time repair/verification of this policy and creates a machine-local Ed25519 host identity before sshd starts. Server host identity is not an operator login requirement.

A boot/image change on the reference development Acer must preserve automatic SSH recovery unless the owner explicitly changes that policy.

---

## 5. Developer boots must preserve failure evidence

The console is a profile fact, `boot.console_policy` (`diagnostic` | `quiet`), independent of the developer/SSH marker since 2026-10-17. `*-dev` profiles default to `diagnostic`; release profiles and the developer release candidate `legacy-x86-i686-rc` are `quiet`. The composer writes `/etc/greia-os/boot-console-policy`; `10_greia_appliance` renders from it and declares `# greia-boot-console-policy: <policy>` in `grub.cfg`; `boot_contract.py` (`BootConsolePolicy`, `--console-policy`) validates it; the live USB template is chosen from the installer manifest (`build/lib/live-syslinux.sh`). A quiet developer image keeps diagnostics reachable: Syslinux `LABEL verbose` (hold Shift/Alt, type `verbose`) and an owner-restricted GRUB entry `greia-os-diagnostics` (hold Shift). Developer images also keep a bounded persistent journal (`journalctl -b -1` after a failed boot). Details: `docs/engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md` §7.

The diagnostic generated kernel policy is source-owned by `10_greia_appliance` and `boot_contract.py`. Current required diagnostic arguments include:

```text
console=tty1
panic=0
loglevel=4
systemd.show_status=true
rd.systemd.show_status=true
udev.log_priority=4
vt.global_cursor_default=1
```

`panic=0` is critical: a fatal kernel/initramfs problem remains visible instead of rebooting after a few seconds and recreating an opaque loop.

Never reintroduce timed panic reboot (`panic=5`, `panic=30`, etc.) on developer/test hardware during bring-up. The quiet policy keeps `panic=0` too.

The current **release** source is deliberately different and remains source-owned. Do not invent a replacement "canonical release bootline" in this document. In particular, the provisional Xorg backend and release console policy still require explicit physical acceptance before a release claim. `greia-launcher.service` currently launches Xorg via `xinit ... vt1`; that compatibility fact must be reviewed together with generated kernel args rather than changed from prose alone.

---

## 6. Initramfs: regeneration is a mutation, not verification

This is the most important operational correction from the incident.

**Never run `update-initramfs -u` merely because a task is described as boot/display/GRUB/recovery work.**

Regenerate initramfs only when an initramfs-owned input changed, such as:

- initramfs-tools hooks/scripts/config;
- the early framebuffer binary/data copied by a hook;
- boot-critical target-kernel module policy;
- kernel/initramfs package state;
- another explicit dependency embedded in the initrd.

A GRUB theme-only, GRUB credential-only, SSH-only, first-boot-only, launcher-animation-only or unrelated systemd change does not automatically require it.

### Why this rule exists

During the historical Acer failure, the installed initramfs was regenerated in a context where host-derived probing did not represent the target laptop. The generated installed initrd lacked the root-storage SATA/AHCI stack even though another payload/source initrd inspected elsewhere contained it. The machine could not see the root disk and booted into an opaque failure loop.

### If regeneration is actually required

Before changing a known-working physical target:

1. identify exact root partition/UUID and kernel version;
2. preserve the known-working initrd when performing emergency repair;
3. establish an independent recovery path;
4. verify target-kernel-aware storage-module inclusion policy.

After regeneration and before reboot:

1. inspect the **new generated installed initrd**;
2. verify boot-critical storage modules required by that target remain present according to current policy;
3. verify the expected Greia initramfs hooks/assets are actually embedded;
4. preserve the command output/evidence.

`update-initramfs` exiting zero proves the command completed. It does not prove the resulting image can mount the physical root disk.

---

## 7. GRUB regeneration and bootloader installation are different operations

Run `update-grub` only when GRUB inputs changed.

After generation and before reboot:

```text
grub-script-check /boot/grub/grub.cfg
python3 -m greia_platform.boot_contract ...
```

Also verify:

- intended root UUID matches the actual target;
- kernel/initrd paths resolve;
- exactly one normal Greia entry exists;
- normal entry is `--unrestricted`;
- owner auth is `password_pbkdf2 greia ...`;
- no accidental recovery/alternate entry reappeared.

Do **not** run `grub-install` during a config/policy-only repair merely as a ritual when GRUB is already executing. Reinstall the bootloader only when evidence says the installed bootloader itself is damaged or intentionally being replaced.

---

## 8. First-boot/systemd dependency rule

`greia-launcher.service` has a hard dependency on `greia-first-boot.service`. Therefore the first-boot unit must remain satisfiable on later boots.

Never put a unit-level negative marker condition on that required service, for example:

```text
ConditionPathExists=!/var/lib/greia-os/initialized
```

The one-shot service should run and let its script exit successfully when initialization already happened. Current idempotency must use the exact marker:

```sh
marker=/var/lib/greia-os/initialized
[ ! -e "$marker" ] || exit 0
```

Do not use a wildcard marker such as `init*`; if more than one path later matches, the shell test can receive multiple arguments and fail.

`RemainAfterExit=yes` keeps the successful one-shot state available to dependents.

Volatile `/run` paths needed during service setup belong to systemd/tmpfiles ownership, not a late `ExecStartPre` workaround.

---

## 9. Current Xorg compatibility gotchas

R7 direct graphics/session/input remains open. Xorg/xinit is a compatibility implementation, not the final architecture.

Current hardware-proven source includes these constraints:

- launcher/installer launches Xorg on `vt1`;
- `StandardInput=null` prevents GUI children from being SIGTTIN-stopped by the VT;
- current Xwrapper policy permits the appliance-owned non-desktop session;
- desktop-daemon namespace hardening must not block the display owner from VT/DRM/input/runtime paths;
- current Xorg details must stay below stable platform semantics so R7 can replace them.

Do not copy an Xorg workaround into Activity or portable platform APIs.

---

## 10. Persistent diagnostics

Boot polish must not delete diagnostics.

Persistent journald and authorized developer SSH are the primary non-child-facing evidence channels once userspace is available. If a developer boot fails before SSH, `console=tty1` + `panic=0` deliberately preserves the last fatal evidence on the display.

Do not trade diagnostics for a prettier failure loop.

---

## 11. Physical repair protocol

For an already-installed device:

1. refresh/re-resolve repository `main` and record source SHA;
2. establish the safest existing independent access path;
3. identify the target by Greia filesystem identity/UUID and verify its parent disk is non-removable;
4. never assume `/dev/sda1` without checking;
5. capture current `grub.cfg`, running/target kernel state, relevant initrd, first-boot/SSH state and files to be modified;
6. back up the exact target files before mutation;
7. change one causal layer at a time;
8. do not repartition, format or reinstall during a targeted boot repair without evidence that layout/filesystem is the cause;
9. do not mix `grub-install`, initramfs regeneration, GRUB policy, SSH, graphics and unrelated package changes into one unreviewable repair block.

### Mandatory pre-reboot checks

Depending on what changed, verify:

```text
target identity + UUID
kernel/initrd paths
generated initrd contents if regenerated
grub.cfg syntax + Greia boot contract if regenerated
developer marker
SSH enablement/effective auth policy
known greia / greia recovery credential
```

If the device is already reachable over SSH, establish a **second fresh SSH connection** before reboot. Do not rely only on an inherited session that may survive despite a broken restart configuration.

### Mandatory post-reboot checks

For a developer target:

- no automatic reboot loop;
- fresh `greia / greia` SSH returns automatically after userspace/network;
- inspect actual `/proc/cmdline`;
- verify launcher/display service state;
- review `systemctl --failed`;
- physically observe child-visible presentation if it changed.

---

## 12. Verification checklist for agents

Before declaring boot/display work complete:

1. [ ] Re-resolve current source SHA and review concurrent work.
2. [ ] Run focused source/unit tests for the touched contract; run the full project gate before claiming repository-wide green.
3. [ ] Verify artwork/source lineage if presentation changed.
4. [ ] Verify generated/final image bytes when build output is part of the claim.
5. [ ] Regenerate initramfs **only if an initramfs-owned input changed**; if regenerated, inspect the new installed artifact before reboot.
6. [ ] Regenerate GRUB **only if GRUB inputs changed**; validate generated `grub.cfg` before reboot.
7. [ ] Do not run `grub-install` unless bootloader installation itself is the evidenced problem/change.
8. [ ] Preserve `greia / greia` GRUB owner recovery and developer SSH recovery where the developer profile applies.
9. [ ] Preserve `panic=0`/visible diagnostics on developer/test hardware.
10. [ ] Verify exact first-boot idempotency and required-unit behavior on second/later boots.
11. [ ] If launcher intro changed, preserve the intentional **5-second animation + 2-second final-frame hold** unless the owner explicitly changes the product design.
12. [ ] Cleanly sync/unmount any offline-mounted target before reboot.
13. [ ] Establish a recovery path before the physical reboot.
14. [ ] After reboot, verify fresh SSH, actual cmdline, launcher/display state and failed units at the claimed scope.
15. [ ] Update source tests, living docs, `skills/greia-os-work/BOOT.md`, active-plan progress and `HANDOVER.md` when the contract/evidence changed.

A source test PASS is not a physical boot PASS. A successful command is not proof that the artifact it generated is bootable. The standard is: **observable, reversible, artifact-verified and recoverable boot work**.
