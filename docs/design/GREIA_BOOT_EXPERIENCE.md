# Greia Boot Experience

**Status:** accepted target architecture; Linux-builder and physical-hardware proof still required  
**Date:** 2026-08-18  
**Authority:** this document defines the child-visible boot UX; build profiles/source remain authoritative for what is actually implemented.

## 1. Product requirement

Greia must feel like a children's appliance, not a Linux desktop that happens to launch an application.

For a normal boot the child-visible sequence is:

```text
firmware
  → immediate Greia graphical first frame
  → same white/logo visual survives kernel + initramfs
  → short launcher-owned animated logo + gentle boot chime
  → profile picker
```

There must be no intentional child-visible Linux console, blinking text cursor, kernel/service log stream, getty, shell prompt, boot menu or black interstitial introduced by Greia.

The **first Greia-owned frame is white with the Greia logo/artwork filling essentially the full vertical display height** on the 1024×600 reference hardware. Other resolutions/aspect ratios preserve the artwork rather than stretching it.

Greia should reach an interactive profile picker as quickly as the hardware permits. Branding must not become a reason to add seconds of artificial delay.

## 2. Ownership boundaries

### Firmware

Greia cannot control arbitrary BIOS/UEFI vendor screens before its bootloader receives control. Firmware time is still measured in physical acceptance so we know what the child sees, but it is not Greia rendering.

### Bootloader

Legacy BIOS profiles currently require GRUB. GRUB is retained as a **minimal bootloader**, not as an application framework.

Its Greia responsibilities are only:

1. enter a graphical mode when the target hardware supports it safely;
2. present the static white Greia first frame with no interactive menu in the ordinary path;
3. load the kernel/initramfs immediately;
4. preserve the graphics payload into Linux where hardware acceptance proves that this is reliable.

A future platform may use a different bootloader. The visual contract is platform-owned; it is not a GRUB-specific design.

### Kernel/initramfs

Plymouth is not part of the target Greia architecture.

As soon as a writable fbdev framebuffer exists, a tiny Greia-owned early renderer paints the same white/logo frame directly. It must be architecture-safe, nonblocking, fail-soft and independent from high-level graphics runtimes.

### Graphical session / launcher

The launcher owns the actual intro animation. Animation starts only after Greia has a real graphical surface. The launcher first presents a continuation of the white/logo frame, then animates it briefly before revealing the profile picker.

Audio also starts here, never in initramfs.

## 3. Why Plymouth is removed

Plymouth solves a generic distribution problem. Greia has a narrower appliance requirement.

Keeping Plymouth would create:

- another graphics runtime and theme language;
- another asset copy;
- another handoff between renderers;
- extra initramfs/runtime packages;
- a renderer that can appear later than the first framebuffer opportunity;
- a long fixed animation that competes with boot speed.

The existing repository's 52-frame/7-fps Plymouth sequence is therefore legacy implementation material, not the future boot architecture.

## 4. Continuous visual chain

### Stage A — GRUB first frame

Normal boot must have zero interactive timeout.

The GRUB graphical frame should use the **same canonical static artwork** as later stages, rendered on white. The bootloader should not print menu/status text in the normal path.

`gfxpayload=keep`/equivalent may be used only after the relevant profile has demonstrated that preserving the chosen graphics mode is reliable on physical hardware. Hardware that cannot preserve the mode must still boot; loss of splash continuity must never brick a machine.

### Stage B — earliest framebuffer repaint

Source scaffold:

```text
build/early-boot/greia-fb-splash.c
```

Runtime target:

```text
/usr/lib/greia-boot/greia-fb-splash
/etc/greia-boot/boot-logo.ppm
```

The helper:

- discovers screen geometry and colour layout from fbdev ioctls;
- paints white first;
- scales the artwork by height, constrained by width only when necessary;
- supports common 16/24/32-bit true-colour layouts;
- emits no boot-console output;
- never waits for a framebuffer.

Initramfs should invoke the idempotent draw attempt at multiple natural stages rather than polling/sleeping. The first stage that sees `/dev/fb0` wins; later calls simply reinforce the same static frame if still useful.

If no fbdev device ever appears, the helper exits immediately and boot continues. Future DRM-only profiles may add another Greia early-render adapter behind the same visual contract rather than corrupting this helper with hardware-name branches.

## 5. Console suppression

Normal production/developer-test Greia boot must suppress ordinary console presentation independently from the splash implementation.

The local acceptance agent must reconcile the actual kernel/systemd/initramfs parameters, but the intended policy includes the equivalent of:

- quiet kernel logging on the child-visible VT;
- systemd status display disabled;
- initramfs/udev normal chatter suppressed;
- visible VT cursor disabled;
- getty/autovt/debug shell masked on child-accessible VTs;
- launcher graphical service owns its VT without inheriting it as stdin;
- diagnostics remain available through the journal and authorized development SSH.

Do not solve consolelessness by deleting diagnostics. **Invisible is not the same as unavailable.**

Catastrophic pre-userspace kernel/firmware failures are a separate recovery/debugging class; the normal-boot acceptance requirement is that Greia itself never intentionally exposes a Linux console while the system is successfully booting or recovering from ordinary service-level conditions.

## 6. X/display-server handoff

The framebuffer/logo should not be deliberately cleared to black immediately before the launcher appears.

The current Xorg path already uses `-background none`, which exists specifically to request that a driver preserve the previous framebuffer contents where supported. Physical hardware decides whether that is sufficient for a seamless transition.

If a driver cannot preserve the old frame, the fallback must still be visually coherent: prefer a white root/background before launcher presentation rather than a black flash. Do not add a window manager or compositor solely to cover this transition.

R7 remains authoritative for the eventual permanent display/session backend; this boot design must survive a future transition away from Xorg.

## 7. Launcher intro animation

The launcher owns a real intro. It is distinct from the static early-boot cover.

Requirements:

- white full-screen background;
- logo/artwork visually continuous with the static boot frame;
- target duration **0.75–0.95 seconds**;
- never exceed **1.0 second** of intentional delay before the profile picker;
- driven from monotonic elapsed time, not `sleep()` per frame;
- frames may be dropped if rendering/decoding is slow;
- decoded/cached once for the short sequence;
- automatically scale to the real viewport;
- no dependency on `/usr/share/plymouth`;
- play once per machine boot, not on every launcher restart;
- a development/test escape hatch may skip it, but release UX defaults to enabled.

The current 52 legacy frames may be used as artwork source material, but they must not simply be replayed at 7 fps. That would add roughly seven seconds and violate the boot-speed goal.

## 8. Boot sound

A short Greia startup chime is allowed and desired, but **sound must never be on the critical path to the first visible launcher frame**.

Contract:

- default asset is a short, gentle, child-friendly chime;
- start playback only after the launcher has presented its first graphical frame;
- initialize/play asynchronously or otherwise without blocking profile-picker readiness;
- fail silently if no usable audio device exists;
- play once per boot;
- respect platform/device mute and a future Parent-controlled boot-sound setting;
- do not route errors to the visible VT;
- do not initialize ALSA/Pulse/PipeWire/audio inside initramfs.

A provisional WAV may live at:

```text
assets/audio/system/greia-boot-chime.wav
```

The sound is presentation polish, not a boot dependency.

## 9. Asset authority

Boot visuals must not fork into unrelated hand-edited copies.

Establish one canonical approved static artwork source, then derive:

```text
canonical static source
  ├─ GRUB-compatible PNG
  ├─ initramfs P6 PPM
  └─ launcher intro PNG sequence
```

The local agent must inspect the existing 52-frame animation and determine whether its dark background is baked into the PNG pixels or supplied only by the old Plymouth script. The final derivatives must be white-background/transparent-foreground as appropriate.

The static image shown by GRUB and initramfs should match the first/last launcher intro pose closely enough that a child perceives one continuous animation.

## 10. Boot speed rules

Boot polish is not permission to slow Greia down.

Forbidden on the normal boot critical path:

- arbitrary sleeps;
- polling loops waiting for graphics/audio;
- Python or SDL inside initramfs;
- runtime PNG/JPEG decoding inside initramfs;
- network waits before profile picker;
- waiting for Parent HTML/network services before showing the child shell;
- playing every legacy animation frame at a fixed rate;
- synchronous audio initialization before the first launcher frame.

The local agent must measure before/after with `systemd-analyze`, monotonic journal timestamps and physical video. Any service found blocking launcher start without being a true prerequisite must be challenged and, when safe, moved off the critical path.

## 11. Installer

The live installer must follow the same consoleless visual philosophy:

```text
firmware → minimal bootloader → white Greia early frame → graphical installer
```

It does not need the child launcher intro/profile picker, but it must not reintroduce Plymouth or console chatter merely because it is installation media.

Installer errors should be rendered by the graphical installer when users can act on them; detailed diagnostics remain in logs/authorized development access.

## 12. Developer access

Consolelessness must **not** remove the owner-approved developer maintenance path.

During active development/test installs:

- SSH remains reachable according to the current owner policy (`greia / greia` unless the Parent credential has deliberately been changed);
- root SSH remains disabled;
- journal/system diagnostics remain inspectable over SSH;
- a blank/white screen must therefore be diagnosable remotely without exposing a child-facing shell.

## 13. Acceptance definition

This architecture is not complete because source files exist.

A target profile may switch its boot-cover backend from the current provisional Plymouth value to the Greia early-framebuffer backend only when all of the following are true:

1. source/regression gates pass on the exact SHA;
2. target and installer images build without Plymouth installed;
3. generated initramfs contains the target-architecture Greia framebuffer helper and boot PPM;
4. no build-only compiler/development payload leaked into the final image;
5. real hardware boots without child-visible console text/cursor/getty;
6. the earliest attainable Greia frame is white/full-height branded artwork;
7. no black/text flash is introduced between bootloader, initramfs and launcher under the accepted hardware path;
8. the launcher intro is actually visible and remains under its one-second budget;
9. boot sound is pleasant, one-shot and fail-silent;
10. developer SSH and journal diagnostics still work;
11. boot timing is measured and any regression is explained/optimized;
12. at least one second x86 machine/VM verifies that the design did not encode Acer-only assumptions.

Only then should the backend be considered for release-safe registration.