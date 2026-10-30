# Greia OS Work Skill — Boot, Recovery and First-Boot Safety

**Status:** mandatory companion to `skills/greia-os-work/SKILL.md` for any substantive boot/image/installer/initramfs/GRUB/first-boot/Xorg-startup/recovery work  
**Reviewed:** 2026-10-30  
**Audience:** coding agents, maintainers, build/recovery operators, reviewers

## When to use / Read first

Load this before touching anything on the boot chain (firmware/bootloader policy, kernel command line, initramfs, root mount, first-boot/systemd prerequisites, VT/Xorg start, boot artwork, physical boot repair). Start with §1 (mandatory reading), then the sections for the layer you are changing; §10 is the physical-device repair protocol and §12 the pre-commit review questions.

This companion exists because Greia boot work crosses several independently dangerous layers. A source edit that looks local can regenerate a different initramfs, remove remote recovery, hide the actual failure, or create a reboot loop on physical hardware.

This file is a **derived operating protocol**, not a second source of exact constants. Exact implemented contracts remain source-owned; accepted ADRs/product requirements outrank this guide. When prose and source disagree, stop, resolve the contradiction, add a regression lock, and update the living documents in the same tranche.

---

## 1. Mandatory reading for boot work

Before changing any boot-critical path, read:

```text
AGENTS.md
skills/greia-os-work/SKILL.md
skills/greia-os-work/BOOT.md
docs/DOCUMENTATION.md
docs/engineering/BOOT_PIPELINE_AGENT_GUIDE.md
docs/engineering/boot/INSTALLATION_ISSUES_LOG.md
docs/engineering/boot/INSTALLED_OS_BOOT_POSTMORTEM.md
docs/engineering/boot/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/design/GREIA_BOOT_EXPERIENCE.md
docs/design/GREIA_BOOT_PROGRESS.md
HANDOVER.md
```

Then inspect the **current source owners**, especially:

```text
src/greia_platform/grub_security.py
src/greia_platform/boot_contract.py
src/greia_installer/engine.py
build/overlay/etc/grub.d/01_greia_auth
build/overlay/etc/grub.d/10_greia_appliance
build/overlay/usr/local/lib/greia-os/first-boot
build/overlay/usr/local/lib/greia-os/prepare-developer-ssh
build/overlay/etc/systemd/system/greia-first-boot.service
build/overlay/etc/systemd/system/greia-launcher.service
build/build-image.sh
build/build-installer-image.sh
build/live-syslinux/syslinux.cfg.in
build/early-boot/greia-fb-splash.c
src/greia_launcher/boot_intro.py
```

Do not work from remembered commands or an old rescue transcript.

---

## 2. Treat boot as a dependency chain, not one feature

Keep the layers separate:

```text
firmware / removable-media bootloader
  -> GRUB or Syslinux policy
  -> kernel command line
  -> initramfs + root-device discovery
  -> installed root mount
  -> first-boot / recurring systemd prerequisites
  -> VT/display-server acquisition
  -> Greia launcher
  -> launcher-owned boot intro
```

A failure at one layer is not evidence that a later layer is broken.

Before modifying anything, identify:

1. the first layer known to work;
2. the first layer known to fail;
3. the artifact that actually executes on the physical machine;
4. whether that artifact is source-shipped or regenerated during build/install;
5. what recovery channel remains if the next reboot fails.

Change the smallest layer that explains the evidence.

---

## 3. Owner recovery credentials are an explicit Greia development invariant

The current owner-approved development recovery contract is:

```text
GRUB edit/command user: greia
GRUB password:          greia
Developer SSH user:    greia
Developer SSH password:greia
Root SSH:               disabled
```

Normal automatic Greia boot remains `--unrestricted`; the GRUB credential protects editing/command access, not ordinary child boot.

### GRUB rules

- Never reintroduce the historical `greia-recovery` user.
- Never make a randomly generated secret the default owner recovery credential.
- The target stores the GRUB password as a PBKDF2 hash, not a plaintext secret.
- `src/greia_platform/grub_security.py`, the checked-in GRUB generator, installer-media GRUB generation and tests must agree on the same identity.
- A compatibility build report may state the known owner password, but the installed target must not need a generated plaintext recovery-code file.

### Developer SSH rules

On an explicit developer/test image, `greia / greia` must work **by itself**. Do not configure:

```text
AuthenticationMethods publickey,password
```

That OpenSSH form means both methods are required and destroys password-only recovery.

The intended effective development policy is:

```text
PasswordAuthentication yes
KbdInteractiveAuthentication no
AuthenticationMethods password
PermitRootLogin no
AllowUsers greia
```

Machine-local SSH host identity may be generated on the actual device. That is server identity, not an operator login requirement.

Before any developer-hardware reboot after boot-stack work, prove SSH is enabled/configured to return automatically and preserve the `/etc/greia-os/developer-remote` marker unless the owner explicitly changes the development policy.

---

## 4. Never hide a development boot failure behind an automatic reboot loop

The accepted developer/test boot policy is observable:

```text
console=tty1
panic=0
loglevel=4
systemd.show_status=true
rd.systemd.show_status=true
```

`panic=0` means a fatal kernel failure remains on screen instead of rebooting seconds later and destroying the evidence.

For developer/test hardware:

- never reintroduce `panic=5`, `panic=30`, or another timed panic reboot;
- never suppress the only available diagnostic console while actively debugging boot;
- preserve developer SSH as the independent recovery channel;
- if the machine stops before SSH, capture the full screen/last visible lines before changing anything else.

Normal child/release presentation is a separate product policy. Do not copy development verbosity into release merely because it is useful for diagnosis. Conversely, do not make release-console changes during a recovery tranche without the appropriate physical acceptance for the current display backend.

---

## 5. Initramfs regeneration is a boot mutation, not a verification ritual

This rule is mandatory.

**Do not run `update-initramfs -u` merely because the task touches boot, graphics, GRUB, a logo, first-boot logic, SSH, or systemd.**

Regenerate initramfs only when an input that belongs inside initramfs changed, for example:

- initramfs-tools hook/script/config;
- early-framebuffer binary or data copied by an initramfs hook;
- boot-critical target-kernel module policy;
- kernel/initramfs package state;
- another explicit initramfs-owned dependency.

### Why

A previous Greia install regenerated initramfs in a chroot with host-derived dependency selection. The generated initrd silently lost the SATA/AHCI storage stack, so the real internal disk never appeared and the machine entered an opaque panic/reboot loop. Inspecting the payload's older initramfs had falsely suggested the drivers existed.

### Before regenerating a known-working physical target

- identify the exact target root and kernel version;
- preserve a recoverable copy of the known-working initrd when doing emergency/device repair;
- verify there is an independent recovery route;
- confirm the initramfs policy uses target-kernel-aware inclusion, not build-host hardware discovery.

### After regeneration, before reboot

Inspect the **newly generated installed artifact**, not a source/payload copy. For a legacy x86 target that needs SATA/AHCI, verify the target kernel/initrd retains the required root-storage stack according to current policy. Verify any Greia early-boot hook/data expected in the initrd is actually present.

A successful `update-initramfs` exit code proves only that the command completed. It does not prove the machine can find its root disk.

---

## 6. GRUB regeneration is also change-scoped

Run `update-grub` when GRUB inputs changed: `grub.d`, boot arguments, root UUID policy, theme/config inputs, or equivalent bootloader policy.

After generation and **before reboot**:

1. run `grub-script-check /boot/grub/grub.cfg`;
2. validate with `python3 -m greia_platform.boot_contract` using the correct release/developer/live mode;
3. confirm the intended root filesystem UUID matches the actual target;
4. confirm the kernel/initrd paths resolve;
5. confirm exactly one normal Greia entry and no accidental recovery/alternate boot entries;
6. confirm the normal entry is `--unrestricted`;
7. confirm GRUB owner auth is the canonical `greia` PBKDF2 declaration.

Do **not** run `grub-install` during a targeted GRUB-policy/config repair when the existing bootloader is already executing unless evidence specifically shows the installed bootloader itself is damaged or must be replaced.

---

## 7. First-boot and systemd dependencies must remain satisfiable on every boot

A one-time initializer that is also a hard dependency of a recurring service must remain satisfiable after the first boot.

Do not put a unit-level condition such as:

```text
ConditionPathExists=!/var/lib/greia-os/initialized
```

on `greia-first-boot.service` while `greia-launcher.service` has `Requires=greia-first-boot.service`.

The unit starts normally; the script owns exact idempotency:

```sh
marker=/var/lib/greia-os/initialized
[ ! -e "$marker" ] || exit 0
```

Use the exact marker path and quote it. Do not use a wildcard such as `init*`; future files can make a wildcard expand to multiple arguments and break the test expression.

For volatile `/run` paths required before a service starts, use systemd ownership (`RuntimeDirectory=` or tmpfiles as appropriate), not an `ExecStartPre` that runs after namespace construction.

---

## 8. Current Xorg compatibility backend has real VT/device requirements

R7 remains open; Xorg/xinit is a compatibility implementation, not the final Greia display architecture.

While it remains active:

- the launcher/installer uses `xinit ... vt1`;
- Xwrapper configuration must permit the platform-owned appliance session according to current source;
- the display-owning launcher cannot be hardened like an ordinary daemon with namespace rules that block VT/DRM/input/tmp/log access;
- `StandardInput=null` remains required so GUI children do not inherit the VT and get SIGTTIN-stopped;
- current Xorg behavior must not leak upward into portable Greia semantics.

Do not change console/VT policy from prose alone. Verify the generated kernel command line, the service's `vt1` ownership, Xwrapper policy, and physical behavior together.

---

## 9. Artwork and boot presentation changes are still boot-critical changes

Visual-only is not the same as risk-free.

The current source owns these different representations:

- canonical portrait source frame;
- generated static landscape presentation canvas for GRUB/early framebuffer;
- P6 PPM used by the raw framebuffer renderer;
- launcher animation frames/presentation.

Do not infer dimensions or timing from an old document. Inspect `tools/generate_boot_artwork.py`, `src/greia_launcher/boot_intro.py` and the current tests.

Rules:

- preserve the source artwork RGB detail; no threshold/mask/recolour hack;
- keep runtime display fitting proportional and centered;
- do not modify removable-media boot layout just to change presentation bytes;
- prove the finished image contains the intended assets, not merely the checkout;
- do not regenerate initramfs unless the changed visual bytes are actually packaged through initramfs;
- if they are, apply the initramfs artifact checks from §5.

The current milestone progress implementation is source-owned by `docs/design/GREIA_BOOT_PROGRESS.md`, initramfs stage scripts, the raw framebuffer renderer and launcher handoff. Do not claim a progress bar was removed while those sources still draw/require it. Any product decision to remove it must change source, tests and docs together and then receive physical visual acceptance.

### Launcher animation timing is intentional product behavior

The intended launcher-owned sequence is:

```text
5 seconds — animate the complete 52-frame boot sequence
2 seconds — keep the exact final frame visible
then       — reveal the profile picker
```

Do **not** shorten that seven-second intentional presentation as a generic performance/boot-speed optimization. Optimization work should remove hidden stalls, retries, decode overhead or service latency; it must not silently rewrite explicit product timing. A timing change requires an explicit owner/product decision and must update source, regression tests and living boot docs together.

---

## 10. Physical-device boot repair protocol

When repairing an already-installed machine, do not jump straight to reinstalling.

### Before mutation

- re-resolve repository `main` and record source SHA;
- establish the safest available independent access path;
- identify target partition by Greia identity/label plus filesystem UUID and non-removable parent device;
- never assume `/dev/sda1` merely because the reference Acer often uses it;
- capture current `grub.cfg`, kernel command line, initrd/kernel links, relevant source files and SSH state;
- preserve a backup of the exact files to be changed.

### During repair

- mutate one causal layer at a time;
- do not repartition/format/reinstall during a targeted boot repair without evidence that filesystem/layout is the cause;
- do not mix bootloader install, initramfs regeneration, GRUB policy, SSH, graphics and unrelated system changes in one unreviewable command block;
- fail closed on ambiguous target identity.

### Pre-reboot gate

Never reboot a physical development machine merely because commands returned zero.

Before reboot, require all relevant checks to pass:

```text
target identity / UUID
bootloader config syntax
Greia boot contract
kernel + initrd existence
new initrd artifact contents, if regenerated
developer marker
SSH service enablement/effective auth policy
known owner recovery credential
```

Then make a second fresh SSH connection before reboot when the machine is already reachable remotely. This catches accidentally relying on a dying inherited session.

### Post-reboot gate

A hardware boot change is not accepted until the required real evidence exists:

- machine does not enter an automatic reboot loop;
- fresh `greia / greia` SSH returns automatically on a developer target once userspace/network are up;
- expected `/proc/cmdline` is running, not just present in a source file;
- launcher/display service reaches its intended state;
- `systemctl --failed` is reviewed;
- child-visible boot presentation is physically observed when the change affects it.

---

## 11. Evidence hierarchy for boot work

Different evidence proves different things:

```text
source/unit tests
  -> parser/policy/contract logic

builder syntax/static checks
  -> source composition consistency

finished image inspection
  -> what was actually packaged

VM/QEMU
  -> image/boot behavior on virtual hardware

physical target
  -> firmware, real storage, framebuffer, VT, input, network and timing behavior
```

Never promote a lower layer into a physical PASS.

A hardware fix is complete only when:

1. the physical machine works at the claimed scope;
2. authoritative build/source contains the fix;
3. a hardware-independent regression protects the invariant where practical;
4. living docs preserve the root-cause class and current contract;
5. historical postmortems remain honest about what happened.

---

## 12. Mandatory review questions before committing boot work

Ask all of these:

1. What exact boot layer owns this change?
2. What artifact actually executes on the target?
3. Does any build/install step regenerate that artifact later?
4. Is initramfs regeneration truly required?
5. If yes, did we inspect the newly generated initrd before reboot?
6. Is GRUB regeneration required, and was the generated config validated?
7. Does normal boot remain one automatic unrestricted Greia entry?
8. Is GRUB owner recovery still `greia / greia` with only a hash stored on target?
9. On a developer target, can `greia / greia` SSH work without an operator key?
10. Is root SSH still disabled?
11. Could a panic/failure automatically reboot and destroy the evidence?
12. Is first-boot still satisfiable on the second and later boots?
13. Are exact idempotency markers used rather than glob patterns?
14. Are Xorg/VT requirements being treated as compatibility-backend facts rather than architecture?
15. Are source, generated artifact, test expectations and living docs consistent?
16. If launcher timing changed, was the explicit 5-second animation + 2-second final-frame hold preserved or intentionally superseded by the owner?
17. Is the physical evidence scope stated honestly?
18. If we are about to reboot, what is the independent recovery path if it fails?

If the answer to the last question is “none”, stop and establish one before the reboot unless the owner explicitly accepts the risk.

---

## 13. Boot anti-patterns to reject

- random default GRUB recovery passwords;
- `greia-recovery` as the default owner identity;
- plaintext per-install secret required to recover GRUB;
- `AuthenticationMethods publickey,password` on owner-approved developer recovery;
- disabling/removing developer SSH during unrelated hardware work;
- timed panic reboot on a development target;
- blanket `update-initramfs -u` “just to be safe”;
- checking the payload initrd while assuming it proves the installed regenerated initrd;
- running `grub-install` during a config-only repair without evidence;
- changing several boot layers before one physical observation;
- hardcoding `/dev/sda1` without target identity verification;
- unit-level conditions that make a required first-boot service skip/fail on later boots;
- wildcard first-boot marker tests;
- Xorg service hardening that blocks VT/DRM/input paths;
- shortening the intentional 5-second animation + 2-second final-frame hold as an incidental performance tweak;
- relying on a source-test PASS as proof the physical image boots;
- manually fixing the Acer while leaving the builder/source wrong;
- updating code without updating the boot guide/postmortem/current handover;
- rewriting historical failures to pretend the broken contract never existed.

The goal is not to make boot code timid. It is to make every boot mutation **observable, reversible, artifact-verified and recoverable**.
