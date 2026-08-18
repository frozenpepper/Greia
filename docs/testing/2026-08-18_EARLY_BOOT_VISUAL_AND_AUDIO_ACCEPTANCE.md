# Greia — Local Agent Early-Boot Visual, Audio and Boot-Speed Session

**Status:** mandatory addendum to the current full local-agent test/fix session  
**Date:** 2026-08-18  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`

This protocol implements and proves the accepted boot architecture in:

```text
docs/design/GREIA_BOOT_EXPERIENCE.md
build/early-boot/README.md
build/early-boot/greia-fb-splash.c
```

This is **not** a passive test checklist. You are authorized and expected to diagnose, edit, add regressions, rebuild, retest, commit coherent fixes directly to `main`, and continue through ordinary source/build/runtime failures.

Do not use, query or trigger GitHub-hosted Actions. All execution/evidence belongs to the owner-controlled Linux builder and target hardware.

---

## 0. Product goal — understand this before touching source

The normal child-visible boot must become:

```text
firmware
  → minimal graphical bootloader
  → white Greia frame + vertically large logo/artwork
  → same visual survives kernel/initramfs as early as framebuffer permits
  → short launcher-owned animated continuation + gentle one-shot chime
  → profile picker
```

Greia must **not intentionally expose**:

- kernel/service console text;
- a blinking VT cursor;
- getty/login prompt;
- shell prompt;
- Plymouth;
- an interactive GRUB menu in ordinary boot;
- a black frame inserted by our own handoff;
- a seven-second fixed boot animation.

The first useful child-facing frame matters more than animation fidelity. Boot branding must never block the real boot waiting for graphics or audio.

The `1024x600` Acer screen is a **reference design resolution only**. The implementation must query actual framebuffer/display geometry and preserve artwork aspect ratio on other resolutions.

Developer/test installs must remain remotely diagnosable over SSH according to current owner policy (`greia / greia` unless deliberately changed through Greia Parents). Root SSH stays disabled. Removing the console must not remove logs or remote diagnostics.

---

## 1. Hard project invariants

Treat these as hard constraints, not suggestions.

1. **No Acer-specific logic in generic boot code.** No PCI ID, model name, literal framebuffer dimensions or machine-name branch.
2. **No waiting for splash.** No `sleep`/poll loop for `/dev/fb0`; a missing framebuffer is fail-soft and boot continues immediately.
3. **No heavy initramfs graphics stack.** No Python, SDL/Pygame, Xorg, PNG/JPEG decoder stack or audio in initramfs.
4. **Target binary must match target architecture.** Never copy a build-host executable into an i386/amd64/ARM image by accident.
5. **No diagnostics destruction.** Console suppression means redirect/suppress child-visible output while preserving journal/SSH evidence.
6. **Plymouth removal must be coherent.** Do not merely uninstall the package while leaving profile mappings, service dependencies, build scripts or asset paths that assume it.
7. **GRUB remains only where the platform needs it.** For current BIOS x86 profiles it remains a minimal zero-timeout loader; do not expand GRUB into the animation engine.
8. **Intro animation must not create a long boot tax.** Intentional launcher intro budget is 0.75–0.95 s and must never exceed 1.0 s before profile picker.
9. **Boot sound is optional polish, never a prerequisite.** Start it after the first launcher frame; failure or missing audio must not delay or fail boot.
10. **Evidence follows exact SHA.** If source changes after an image was built, that image no longer proves the new source.
11. **Do not weaken tests to preserve old Plymouth behavior.** Old tests/docs asserting Plymouth is authoritative are policy drift and should be updated when the new implementation is complete.
12. **Do not declare the new backend release-safe from source reasoning alone.** Physical acceptance is required.

---

## 2. Session setup and evidence root

From the Greia repository:

```bash
set -Eeuo pipefail

git fetch origin
git switch main
git pull --ff-only origin main

git status --short
git rev-parse HEAD
```

The working tree must be understood before editing. Do not discard owner work. If there are existing local edits, inspect them and preserve them unless the owner explicitly says otherwise.

Create project-local evidence only:

```bash
SESSION_ROOT="./work/evidence/boot-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$SESSION_ROOT"
printf '%s\n' "$(git rev-parse HEAD)" > "$SESSION_ROOT/start-sha.txt"
```

Do **not** use filesystem-root `/tmp` for project evidence and do not make a ZIP unless the owner explicitly requests one.

Read, in order:

```text
AGENTS.md
docs/DOCUMENTATION.md
docs/design/GREIA_BOOT_EXPERIENCE.md
build/early-boot/README.md
docs/testing/LOCAL_AGENT_START_HERE.md
docs/testing/2026-08-18_LOCAL_AGENT_FULL_TEST_AND_FIX_SESSION.md
HANDOVER.md
```

---

## 3. Capture the current Plymouth/boot baseline before changing it

Run and save all output:

```bash
git grep -n -iE 'plymouth|stock-plymouth-provisional' -- \
  build tools src tests runtime docs HANDOVER.md \
  > "$SESSION_ROOT/plymouth-baseline.txt" || true

git grep -n -E 'GRUB_TIMEOUT|gfxpayload|GFXPAYLOAD|quiet|loglevel|show_status|vt.global_cursor|console=' -- \
  build tools src tests \
  > "$SESSION_ROOT/boot-configuration-baseline.txt" || true

git grep -n -E 'getty|autovt|debug-shell|console-shell|TTYPath|StandardInput' -- \
  build/overlay build/installer-overlay \
  > "$SESSION_ROOT/vt-baseline.txt" || true
```

Also record the current build profile values:

```bash
for profile in build/profiles/*.toml; do
  printf '\n### %s\n' "$profile"
  sed -n '/^\[boot\]/,/^\[/p' "$profile"
done | tee "$SESSION_ROOT/profile-boot-backends.txt"
```

Do not delete the baseline files after the migration; they are useful proof that stale authority was actually removed.

---

## 4. Inspect the old 52-frame artwork before reusing anything

The old Plymouth animation is **source material**, not the new runtime implementation.

Inspect all frames. At minimum verify:

```bash
find build/overlay/etc/plymouth/themes/greia/frames \
  -maxdepth 1 -type f -name 'frame_*.png' -print | sort \
  > "$SESSION_ROOT/legacy-frame-list.txt"

file build/overlay/etc/plymouth/themes/greia/frames/frame_0000.png \
     build/overlay/etc/plymouth/themes/greia/frames/frame_0051.png \
  | tee "$SESSION_ROOT/legacy-frame-file.txt"
```

Use an **offline build/analysis tool** already available on the machine (Pillow or ImageMagick is fine for development tooling) to record:

- width/height/mode for every frame;
- the four corner pixel values for frame 0000 and frame 0051;
- whether the dark blue background is baked into the PNGs or exists only in the Plymouth script;
- whether the actual artwork touches/crops the full 600 px vertical reference area;
- whether alpha is available.

Save the analysis to:

```text
$SESSION_ROOT/legacy-frame-analysis.txt
```

If the old RGB frames contain a baked dark background, do **not** carry that background into the new design merely because it is convenient. Produce white-background or transparent-foreground derivatives from the best available canonical artwork/source.

Create a small contact sheet for owner review only if it materially helps evaluate the animation. Do not add large diagnostic media to the product runtime.

---

## 5. Establish one canonical boot artwork lineage

Do not hand-edit three unrelated logo copies.

Create a clear source/derived structure, for example:

```text
assets/boot/source/                  # canonical approved source artwork
assets/boot/static/greia-boot-logo.png
assets/boot/intro/frame_0000.png ... # short launcher-owned sequence
build/overlay/etc/greia-boot/boot-logo.ppm
build/installer-overlay/etc/greia-boot/boot-logo.ppm
```

Exact source filename may follow an existing canonical logo asset if one already exists. Reuse rather than duplicate when possible.

Required visual behavior:

- background: pure/near-pure white;
- Greia logo/artwork centered;
- at 1024x600 the artwork should use essentially the full vertical height without distortion;
- at other aspect ratios preserve aspect ratio; constrain by width only when full-height art would not fit;
- GRUB static frame, PPM static frame and first launcher animation pose should visually match.

The PPM is a **build/runtime derivative**, not a designer-authored master. Generate it deterministically from the canonical source and document the command/tool used.

Do not introduce network-time asset generation into the image builder.

---

## 6. Compile the early framebuffer helper for the TARGET architecture

Source:

```text
build/early-boot/greia-fb-splash.c
```

First run a normal host compiler warning gate as a source check:

```bash
cc -std=c11 -Wall -Wextra -Werror -O2 \
  -c build/early-boot/greia-fb-splash.c \
  -o "$SESSION_ROOT/greia-fb-splash-host.o"
```

This proves only source/compiler cleanliness. It does **not** prove target compatibility.

The real binary must be built inside the image target root/chroot. Preferred Debian strategy:

1. temporarily install `libklibc-dev` in the target root;
2. compile using the target's `klcc`;
3. request a static/standalone binary appropriate for initramfs;
4. strip it if supported;
5. verify architecture and dependency shape;
6. remove the build-only development package before final image manifest/footprint capture.

A representative command to investigate inside the chroot is:

```bash
klcc -static -Os -s \
  -o /usr/lib/greia-boot/greia-fb-splash \
  /path/to/greia-fb-splash.c
```

Do not cargo-cult this exact command if the target `klcc` version uses different supported flags. Inspect `klcc --help`/Debian tooling on the actual builder and record the final command.

After compilation record:

```bash
file /usr/lib/greia-boot/greia-fb-splash
readelf -h /usr/lib/greia-boot/greia-fb-splash || true
readelf -l /usr/lib/greia-boot/greia-fb-splash || true
ls -lh /usr/lib/greia-boot/greia-fb-splash
```

The resulting architecture must match the profile architecture exactly.

If klibc cannot compile the helper on a supported target because of a real syscall/header/API incompatibility, stop that implementation branch, record the compiler output, diagnose the smallest architecture-neutral alternative, and only then change strategy. **Never solve this by copying a host binary.**

---

## 7. Integrate the helper into BOTH target and installer initramfs

This is mandatory for:

```text
build/overlay/
build/installer-overlay/
```

Add initramfs-tools hook/scripts that copy:

```text
/usr/lib/greia-boot/greia-fb-splash
/etc/greia-boot/boot-logo.ppm
```

into generated initramfs images.

Then invoke the draw attempt at multiple naturally available initramfs stages. The purpose is **not** to poll. The purpose is that the first normal stage at which `/dev/fb0` exists gets to paint it.

The call pattern is:

```sh
[ -c /dev/fb0 ] || exit 0
/usr/lib/greia-boot/greia-fb-splash >/dev/null 2>&1 || true
```

Use stages supported by the current Debian `initramfs-tools` version, beginning with `init-top` and adding an appropriate later pre-root stage plus `init-bottom` reinforcement where ordering is valid.

Requirements:

- executable hooks/scripts;
- correct `PREREQ` declarations;
- no sleep;
- no retry loop;
- no stderr/stdout to child VT;
- no hard-coded target machine name;
- no dependency on root filesystem being mounted;
- no failure of normal boot if `/dev/fb0` is absent.

Add deterministic source tests for all of the above.

---

## 8. Introduce the new boot-cover backend atomically

Use the exact backend identifier:

```text
greia-early-framebuffer-v1
```

Use the package-set identifier:

```text
boot-cover-greia-early-framebuffer
```

Update `tools/build_profile.py` so `_BOOT_COVER_PACKAGE_SETS` maps the new backend to the new package set.

The package set should contain **only real external runtime packages required by this backend**. If the renderer is entirely Greia-owned and its target binary is produced by the builder, keep the package set empty except for explanatory comments. Do not put `libklibc-dev`, compiler toolchains or other build-only packages in the final runtime set.

Do **not** add the new backend to `_RELEASE_SAFE_BOOT_COVERS` yet. Physical acceptance comes first.

Once target and installer builder integration exists and focused source tests are green, change every current x86 profile's:

```toml
cover_backend = "stock-plymouth-provisional"
```

to:

```toml
cover_backend = "greia-early-framebuffer-v1"
```

Do not update only the Acer profile and leave modern/legacy peers silently on a contradictory boot architecture unless a profile has a documented technical reason to remain provisional.

ARM64 schema support must remain future-safe. Do not force an x86-only module or bootloader choice into the generic framebuffer renderer/profile abstraction.

---

## 9. Remove Plymouth from active build/runtime authority

After the new backend is implemented, remove active Plymouth dependencies coherently from target and installer paths.

At minimum inspect and fix:

- `build/package-sets/boot-cover-plymouth.txt` and its profile mapping;
- `build/overlay/etc/plymouth/...`;
- installer equivalents if present;
- `plymouth-set-default-theme` / theme-copy logic in builders;
- `After=plymouth-start.service` or other service ordering;
- Plymouth quit/wait masking that exists only for the old handoff;
- launcher code loading `/usr/share/plymouth/...` as a logo source;
- stale `release-boot-cover` comments/behavior;
- tests that assert Plymouth is the required backend;
- active design/docs that call Plymouth authoritative.

Historical review/issue documents may still mention Plymouth as history. Do not rewrite history merely to make `grep` empty.

The final active-runtime audit should look like:

```bash
git grep -n -iE 'plymouth|stock-plymouth-provisional' -- \
  build tools src tests runtime \
  | tee "$SESSION_ROOT/plymouth-final-active-audit.txt" || true
```

Every remaining hit in active source/build/tests must have a deliberate reason. The target and installer package manifests must not contain Plymouth packages.

---

## 10. Minimal GRUB visual handoff

Do **not** remove the current legacy BIOS bootloader as part of this tranche. Keep GRUB minimal.

Normal boot requirements:

- zero interactive timeout;
- no ordinary menu text;
- graphical mode where accepted;
- white Greia static first frame while kernel/initramfs is loaded;
- load kernel immediately;
- no animation loop in GRUB.

Use the canonical boot PNG rather than inventing a GRUB-only image.

Investigate `gfxpayload=keep`/the generated equivalent on the actual target. It is acceptable only when physical acceptance proves it does not break that profile's video initialization.

If preserving the GRUB mode makes a supported machine fail or causes worse mode transitions, keep the boot reliable and document the visual continuity loss. Do **not** brick a hardware family in pursuit of a perfect splash.

Preserve the existing Greia boot-entry/authentication safety architecture while removing the obsolete random-password/recovery UX required by the owner. Do not accidentally re-open arbitrary recovery shell entries.

---

## 11. Consoleless kernel/initramfs/systemd policy

Inspect the **actual generated** `grub.cfg`, initramfs and `/proc/cmdline`; do not assume source snippets are what the machine booted.

The intended successful-boot policy is the current-version equivalent of:

```text
quiet
low kernel console verbosity
systemd status display disabled
initramfs/udev normal chatter suppressed
VT cursor disabled
no getty/autovt/debug shell on child-visible VTs
```

Do not blindly add a copied list of kernel parameters. Check what the current Debian kernel/systemd/initramfs versions accept, then encode only parameters that are valid and useful.

Capture final values:

```bash
cat /proc/cmdline | tee "$SESSION_ROOT/target-proc-cmdline.txt"
systemctl get-default | tee "$SESSION_ROOT/target-default-target.txt"
systemctl status getty@tty1.service --no-pager \
  > "$SESSION_ROOT/getty-tty1-status.txt" 2>&1 || true
systemctl status debug-shell.service --no-pager \
  > "$SESSION_ROOT/debug-shell-status.txt" 2>&1 || true
```

Diagnostics must remain available in:

```bash
journalctl -b
journalctl -b -u greia-launcher.service
```

and through authorized developer SSH.

---

## 12. Xorg/current display handoff

The current Xorg launch path uses `-background none`. Test it first; do not change it merely because a different flag seems aesthetically plausible.

Physical acceptance question:

> Does the static framebuffer image remain visible until the launcher has a real frame ready?

If yes, preserve the simpler path.

If Xorg/driver clears to black on actual supported hardware, investigate the smallest white-root/background fallback. The accepted UX is a coherent white transition; do not add a desktop/window manager/compositor just to hide a 100 ms handoff.

Any change here belongs to R7/display-session architecture and must retain keyboard focus/input/VT correctness already proven by prior hardware work.

---

## 13. Implement a REAL launcher-owned intro animation

The user has not been seeing a launcher intro because the old animation effectively lived in Plymouth. Add a launcher-owned sequence.

Requirements:

1. After creating the real fullscreen graphical surface, render the white/static Greia continuation frame and call `pygame.display.flip()` **immediately**.
2. Only after that first frame may noncritical intro work begin.
3. Animation duration target: **0.75–0.95 s**; hard product maximum: **1.0 s** intentional delay before profile picker.
4. Use `time.monotonic()` elapsed time to choose the frame. Do not sleep one frame at a time.
5. If the machine is slow, skip/drop frames; do not extend total duration to show them all.
6. Preload/decode the small intro asset set once for this sequence.
7. Scale to the actual fullscreen surface while preserving aspect ratio and the full-height visual intent.
8. Do not read any asset from `/usr/share/plymouth`.
9. Run once per **machine boot**, not once per launcher process restart. Use a `/run/greia-os/...` one-shot marker.
10. Keep a documented developer escape hatch to skip intro for diagnostics, but normal Greia UX defaults to enabled.
11. The profile picker should be ready immediately at animation completion; do not then start another blocking initialization phase.

A good implementation may sample the legacy 52-frame artwork into a much smaller launcher sequence or select frames by elapsed time. Do not replay all 52 at 7 fps.

Add source tests that enforce the one-second maximum and forbid a per-frame `sleep()` implementation.

---

## 14. Add the optional boot chime without putting audio on the critical path

Canonical provisional asset location:

```text
assets/audio/system/greia-boot-chime.wav
```

If a provisional chime exists in the repo, inspect/listen to it on the target before deciding it is final. A mechanically valid WAV is not evidence that it sounds pleasant on tiny netbook speakers.

Runtime requirements:

- start only **after the first graphical launcher frame is already presented**;
- play asynchronously/nonblocking;
- one shot per machine boot, using `/run/greia-os/...` state;
- no visible error when ALSA/audio device is absent;
- no boot failure if mixer/audio initialization fails;
- never play from initramfs;
- respect hardware/device mute and the platform audio state;
- design so a future Parent setting can disable boot sound globally;
- do not make a per-child choice before a child profile has even been selected.

On the Acer, test both:

1. normal audio device available;
2. audio unavailable/disabled (or equivalent safe simulation).

The second case must reach the profile picker at essentially the same time and without child-visible errors.

Record subjective owner-facing notes such as volume, harshness and speaker clipping separately from deterministic source validity.

---

## 15. Boot critical-path performance audit

Before optimization, capture a baseline from the current installed image if still available. After the new image boots, capture at least:

```bash
systemd-analyze time \
  | tee "$SESSION_ROOT/systemd-analyze-time.txt"

systemd-analyze blame \
  | tee "$SESSION_ROOT/systemd-analyze-blame.txt"

systemd-analyze critical-chain greia-launcher.service \
  | tee "$SESSION_ROOT/launcher-critical-chain.txt"

journalctl -b -o short-monotonic \
  > "$SESSION_ROOT/journal-short-monotonic.txt"
```

Also inspect the launcher's unit dependencies. Challenge any network, Parent-App, removable-media or other service that blocks the child shell despite not being a true prerequisite.

Do not optimize by deleting required safety/storage/profile initialization. Fix false critical-path dependencies, unnecessary sleeps and serial waits.

Do not claim “boot is faster” without before/after evidence from comparable boots.

### Physical timing

Film at 60 fps or preferably 120 fps if convenient. The video is for timing/visual continuity review; it is not a replacement for logs.

Record approximate timestamps for:

- power press;
- firmware end / GRUB first Greia-owned frame;
- first Linux/early-framebuffer Greia frame if visually distinguishable;
- launcher animation start;
- profile picker interactive.

Measure at least:

- one cold boot;
- one warm reboot.

Do not invent sub-frame precision if the recording does not support it.

---

## 16. Extend the boot regression suite as implementation lands

The repository may contain an initial scaffold test `tests/test_boot_experience_contract.py`. **Extend it as you implement the final backend.** The final test suite must enforce at least:

### Early renderer

- source exists;
- queries framebuffer geometry with `FBIOGET_FSCREENINFO` and `FBIOGET_VSCREENINFO`;
- no `1024`, `600`, `Acer` or hardware-ID branches;
- no sleep/poll/subprocess/console-print dependency;
- common 16/24/32 bpp handling remains;
- white background behavior remains;
- PPM path is platform-owned.

### Build/profile authority

- `greia-early-framebuffer-v1` is registered;
- current target/installer profiles select it after migration;
- no active profile selects `stock-plymouth-provisional`;
- build-only klibc/compiler dependency is not a final runtime package set;
- target and installer overlay both have initramfs integration;
- builders do not copy/set a Plymouth theme;
- launcher service does not order after `plymouth-start.service`;
- launcher source does not read `/usr/share/plymouth`.

### Consoleless contract

- generated boot-entry/kernel parameter contract includes the accepted quiet/status/cursor policy;
- getty/autovt/debug shell remain masked/disabled in produced images;
- launcher graphical service retains `StandardInput=null`.

### Intro/sound

- launcher intro has an explicit <=1.0 s maximum;
- animation is monotonic-time based and does not contain a per-frame fixed sleep loop;
- one-boot marker exists;
- boot chime WAV has a valid RIFF/WAVE header and a bounded duration (recommend <=1.2 s);
- audio failure is not treated as launcher-fatal;
- boot sound starts only after first display presentation in the source control flow/architecture test.

### No legacy runtime

- active build/package/source inputs contain no Plymouth dependency after migration;
- historical docs may still mention it.

Do not make tests search for the Acer model as a positive condition. The tests must prove generic behavior.

---

## 17. Focused source gate

First inspect the current test names rather than assuming an old module still exists:

```bash
find tests -maxdepth 1 -type f \( -name '*boot*.py' -o -name '*profile*.py' -o -name '*installation*.py' \) \
  -print | sort \
  | tee "$SESSION_ROOT/relevant-test-files.txt"
```

Run the exact current boot/profile/installation regression modules, including at least:

```bash
set -o pipefail
PYTHONPATH=src python3 -m unittest \
  tests.test_boot_experience_contract \
  tests.test_installation_hardware_regressions \
  -v 2>&1 | tee "$SESSION_ROOT/boot-focused.log"
```

If the current tree has a separate authoritative build-profile/boot-contract test module, include it in the same focused run. If a module was legitimately renamed, use its current replacement and record that fact; **do not skip the subsystem**.

After each genuine source fix:

1. rerun the smallest affected test;
2. rerun the focused boot gate;
3. commit a coherent root-cause fix;
4. push `main`;
5. continue.

Before building final images run the repository-wide gate:

```bash
make verify 2>&1 | tee "$SESSION_ROOT/final-make-verify.log"
```

Do not copy an old PASS result onto the new SHA.

---

## 18. Build a fresh developer/test target and installer

Use the current canonical build commands/profile chosen by the full session protocol and actual target inventory. **Do not assume the Acer is PAE/non-PAE/i386/amd64 from this document alone.** Read the recorded hardware/profile evidence and select the correct declared profile.

The build must produce both:

- the target/developer image used for installed-system acceptance;
- the installer/live media used to reach that target.

If source changes after either artifact is built, rebuild the affected artifact before calling physical evidence current.

Preserve the full session's destructive-media safety rules. Never guess an SD/USB target device.

---

## 19. Inspect generated images/initramfs BEFORE booting hardware

Mount/inspect the built images using the existing project-safe tooling.

For every generated initramfs, verify with the current Debian tools (for example `lsinitramfs`):

```text
usr/lib/greia-boot/greia-fb-splash
etc/greia-boot/boot-logo.ppm
expected Greia initramfs scripts/hooks
```

Also verify:

- the helper architecture matches the target architecture;
- no Plymouth binary/theme/module exists in the generated initramfs;
- no Plymouth package exists in target/installer package manifest;
- no build-only compiler/`libklibc-dev` package leaked into final runtime manifest;
- generated GRUB config has zero ordinary timeout and the intended graphical/static frame behavior;
- generated kernel command line matches the accepted consoleless policy;
- target and installer both contain the correct static artwork derivative.

Save exact inspection commands and output under `$SESSION_ROOT`.

If the image inspection contradicts the source, **fix the builder**. Do not proceed to hardware hoping runtime will somehow be different.

---

## 20. Physical acceptance — Acer/reference machine

Use the fresh image from the exact tested SHA.

### 20.1 Boot/install media

Observe from power-on to graphical installer:

- no Greia-controlled text console;
- no blinking cursor;
- no interactive GRUB menu;
- white Greia first frame as soon as the bootloader owns display;
- artwork vertically large/full-height at the 1024x600 reference resolution;
- no distortion;
- no intentional black flash introduced by the Greia chain;
- installer appears graphically.

Complete install following the full test protocol.

### 20.2 First installed boot

Film the boot.

Verify:

- white/static Greia frame appears immediately after firmware control passes to Greia;
- no kernel/systemd/initramfs text leaks during successful boot;
- no VT cursor flashes;
- static image remains coherent across GRUB → Linux → X/launcher as far as the hardware can preserve it;
- launcher logo animation is visibly present;
- intro lasts <=1.0 s intentional time;
- profile picker immediately follows;
- boot chime plays once when audio works;
- chime is not painfully loud/harsh/clipped on the tiny speakers;
- keyboard/touchpad remain usable at profile picker.

### 20.3 No-audio/failure behavior

Safely disable/unavailable the audio path and reboot.

Verify:

- same visual boot succeeds;
- no visible audio error;
- no meaningful boot wait is introduced trying to find audio;
- profile picker works.

Restore audio afterward.

### 20.4 One-shot behavior

After a normal boot, SSH in and restart only the launcher service using the supported development procedure.

Verify:

- profile UI returns;
- **boot intro does not replay** merely because the process restarted;
- **boot chime does not replay** merely because the process restarted.

Then perform a real reboot and verify they do play once again.

### 20.5 No hidden child shell/getty

Check child-accessible VTs using the safe acceptance procedure already established for Greia. Ordinary key combinations must not reveal a getty/login console.

Do not disable developer SSH to achieve this.

### 20.6 SSH/logging

From the owner workstation verify:

- SSH `greia` access works according to current development credential policy;
- root SSH is rejected;
- `journalctl -b` and `journalctl -b -u greia-launcher.service` contain useful diagnostics;
- console suppression did not erase the evidence needed to debug a white/blank screen remotely.

---

## 21. Second-machine/VM anti-Acer check

Repeat the relevant boot acceptance on at least one second x86 machine or VM with a different resolution/aspect ratio/framebuffer implementation.

Minimum checks:

- image boots;
- no model-specific assumption prevents early renderer/launcher startup;
- static artwork preserves aspect ratio;
- no hard-coded 1024x600 geometry corrupts the display;
- absence/difference of `/dev/fb0` fails soft rather than delaying boot;
- launcher intro/profile picker remain responsive at that resolution.

A second machine is not optional before calling the implementation hardware-independent.

---

## 22. Fix policy when something fails

You are expected to repair genuine defects.

For every failure:

1. preserve the first failure output/evidence;
2. identify whether the fault is source, builder, generated artifact, machine-specific configuration or hardware capability;
3. fix the **root cause at the authoritative layer**;
4. add/strengthen a regression when the cause is source/build-contract level;
5. do not weaken a valid test;
6. do not encode this Acer's PCI/model/resolution as the fix;
7. rerun the smallest affected gate;
8. rerun the boot-focused gate;
9. commit/push a coherent fix;
10. rebuild any artifact invalidated by the source change;
11. continue physical acceptance.

Ask the owner only for genuinely owner-controlled/non-discoverable choices such as which destructive media device is safe to overwrite, credentials you cannot obtain, or subjective approval of a final sound/visual. Do not ask the owner to copy terminal text manually when you can save an evidence file.

---

## 23. Commit discipline

Commit as you work so recoverable progress always exists on GitHub.

Good commit boundaries include:

```text
boot: add canonical white boot artwork derivatives
boot: build early framebuffer helper into initramfs
boot: migrate profiles off Plymouth
boot: add launcher intro and one-shot chime
tests: lock consoleless boot contract
build: remove Plymouth from target and installer
docs: record measured boot acceptance
```

Do not mix an unrelated UI refactor or Activity feature into this tranche.

---

## 24. Final required result

Update the full session's `LOCAL_AGENT_RESULT.md` and include a dedicated boot section containing:

```text
START SHA:
FINAL SHA:
TARGET PROFILE:
INSTALLER ARTIFACT:
TARGET ARTIFACT:

SOURCE GATES:
- boot-focused command/result
- make verify command/result

PLYMOUTH MIGRATION:
- active-source final grep summary
- target package/initramfs inspection
- installer package/initramfs inspection

EARLY FRAMEBUFFER:
- target binary architecture/size
- initramfs paths
- framebuffer behavior on Acer
- behavior on second machine/VM

CONSOLELESS ACCEPTANCE:
- cold boot observation
- warm reboot observation
- any visible text/cursor/black flash and exact stage

INTRO:
- duration
- one-shot behavior
- profile-picker handoff

AUDIO:
- asset used
- normal playback
- unavailable-audio behavior
- one-shot behavior
- subjective speaker/volume note

BOOT PERFORMANCE:
- systemd-analyze time
- launcher critical chain
- physical video-derived milestones
- before/after comparison where a valid baseline exists

DEVELOPER ACCESS:
- greia SSH result
- root SSH rejection
- journal availability

FIXES MADE:
- commit SHA + one-line root cause for each

UNRESOLVED:
- exact remaining limitation/evidence gap
```

Never write `PASS` for the visual/physical scope merely because source tests are green. The desired result is a genuinely appliance-like boot on real hardware, with enough retained remote evidence to debug it when it fails.