# Greia Boot Experience

**Status:** active architecture; exact full-colour presentation requires physical re-acceptance  
**Date:** 2026-08-20  
**Authority:** this document defines the child-visible boot UX; build profiles/source remain authoritative for what is actually implemented.

## 1. Product requirement

Greia must feel like a children's appliance, not a Linux desktop that happens to launch an application.

For a normal boot the child-visible sequence is:

```text
firmware
  → immediate Greia graphical first frame
  → visually continuous Greia artwork through kernel + initramfs
  → short launcher-owned animated logo + gentle boot chime
  → profile picker
```

There must be no intentional child-visible Linux console, blinking text cursor, kernel/service log stream, getty, shell prompt, boot menu or black interstitial introduced by Greia in the release path.

The Greia-owned boot artwork is **full colour**. It must never be reduced to a binary mask, thresholded into a two-colour silhouette, recoloured as a single foreground colour, or stretched to match the physical display. The composition must remain proportional and centred on every supported aspect ratio.

During an open physical-hardware recovery gate, explicit `*-dev` profiles may intentionally keep tty1/status output visible. Diagnostic visibility is temporary development policy and does not redefine the child-facing release UX.

Greia should reach an interactive profile picker as quickly as the hardware permits. Branding must not become a reason to add seconds of artificial delay.

## 2. Ownership boundaries

### Firmware

Greia cannot control arbitrary BIOS/UEFI vendor screens before its bootloader receives control. Firmware time is still measured in physical acceptance so we know what the child sees, but it is not Greia rendering.

### Bootloader

Installed legacy BIOS profiles currently require GRUB. The reference Acer removable installer uses the separately proven Syslinux/FAT32 path. Neither bootloader is an application framework.

Bootloader responsibilities are only:

1. enter a graphical mode when the target hardware supports it safely;
2. present the canonical static Greia composition without distorting it;
3. load the kernel/initramfs immediately;
4. preserve diagnostics or graphics according to the currently accepted profile policy.

For installed GRUB, the static image must be rendered through a theme using proportional `padding` and centred horizontal/vertical alignment. Raw `background_image` stretch is forbidden for Greia artwork.

### Kernel/initramfs

Plymouth is not part of the target Greia architecture.

As soon as a writable fbdev framebuffer exists, a tiny Greia-owned early renderer paints the same static composition directly. It must be architecture-safe, nonblocking, fail-soft and independent from high-level graphics runtimes.

### Graphical session / launcher

The launcher owns the actual intro animation. Animation starts only after Greia has a real graphical surface. The launcher first presents a continuation of the static artwork, then animates it briefly before revealing the profile picker.

Audio also starts here, never in initramfs.

## 3. Canonical artwork and generated presentation canvas

The retained final legacy frame is currently the authoritative raw artwork source:

```text
assets/boot/source/legacy-plymouth-theme/frames/frame_0051.png
```

It is source material, not a runtime Plymouth dependency.

The generation contract is:

```text
untouched full-colour source frame
        ↓
1600×900 landscape presentation canvas
  - source centred at native resolution
  - surrounding canvas extends the source background palette
  - no mask / threshold / recolour / quantisation
        ├─ GRUB / launcher PNG
        └─ initramfs P6 PPM
```

The landscape canvas intentionally owns visual scale and safe margins. Runtime adapters then fit that **whole canvas** proportionally to their viewport. This prevents a portrait source from becoming either a huge narrow full-height object or a horizontally stretched full-screen image.

The physical legacy installer builder must regenerate these derivatives immediately before composing the live and target filesystems. A successful source-tree edit is not evidence that an image contains the new splash.

## 4. Why the old white/indigo derivative is rejected

The historical generator attempted to extract the light foreground from a dark legacy frame using luminance thresholds and a median filter, then repainted the result as indigo `(62,70,130)` on white.

That design is now explicitly rejected because it:

- discards the source colours;
- destroys antialiasing and fine detail;
- can turn noisy source/background transitions into visible speckle and broken silhouettes;
- creates a result that can look like corrupted framebuffer output even when pixel packing is correct;
- made source-level tests encode the visual defect as an invariant.

RGB565 compatibility must be solved in the renderer/pixel-format adapter and by validating the real artwork on hardware, **not by destructively flattening the artwork into two colours**.

## 5. Continuous visual chain

### Stage A — installed GRUB first frame

Normal release boot has zero interactive timeout.

Installed GRUB loads the generated landscape PNG through `greia-theme.txt` with:

```text
desktop-image-scale-method: padding
desktop-image-h-align: center
desktop-image-v-align: center
```

The old raw `background_image` path is forbidden because GRUB's default behavior stretches the image to the screen and visibly distorts the Greia composition.

The reference Acer installer remains on its physically proven Syslinux/FAT32 boot path. Splash work must not modify that removable-media layout merely to change presentation bytes.

### Stage B — earliest framebuffer repaint

Source:

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
- supports common 16/24/32-bit true-colour layouts;
- rejects unsupported reversed bitfields fail-soft rather than painting known-bad colours;
- uses the generated composition's own background colour for any letterboxing;
- fits the entire landscape canvas proportionally and centres it;
- emits no boot-console output of its own;
- never waits for a framebuffer.

The P6 parser consumes exactly the one structural newline after `maxval`; it must never skip arbitrary low-valued raster bytes as if binary pixel data were whitespace.

Initramfs invokes the idempotent draw attempt at natural stages rather than polling/sleeping. If no compatible fbdev device appears, the helper exits immediately and boot continues.

### Stage C — X/display handoff

The framebuffer composition must not be deliberately cleared to black immediately before the launcher appears.

The current Xorg path uses `-background none`, requesting that the video driver preserve the previous framebuffer where possible. Physical hardware decides whether that is sufficient for a seamless transition. If a driver cannot preserve it, fallback presentation should use the same composition/background palette rather than a black flash.

### Stage D — launcher intro

The launcher owns a real intro. It is distinct from the static early-boot cover.

Requirements:

- first frame visually matches the static boot composition;
- target duration **0.75–0.95 seconds**;
- never exceed **1.0 second** of intentional delay before the profile picker;
- driven from monotonic elapsed time, not `sleep()` per frame;
- frames may be dropped if rendering/decoding is slow;
- automatically fit to the real viewport without distorting artwork;
- no dependency on `/usr/share/plymouth`;
- play once per machine boot, not on every launcher restart;
- a development/test escape hatch may skip it, but release UX defaults to enabled.

## 6. Console and diagnostic policy

Console suppression is independent from splash implementation.

Normal/release Greia intends to suppress ordinary console presentation on the child-visible VT while preserving diagnostics through the journal and authorized maintenance paths.

During current Acer recovery, explicit development profiles intentionally use visible diagnostics, including tty1 and non-rebooting panic behavior. This is required so a failure is not reduced to an unexplained frozen or grey screen.

Do not solve consolelessness by deleting diagnostics. **Invisible is not the same as unavailable.**

Developer/test installs must remain reachable over SSH according to the owner-approved development contract:

```text
user: greia
password: greia
```

Root SSH remains disabled. The server may generate its own machine-local host identity automatically; that is not an operator credential.

## 7. Graphical-session resilience

The current installed path remains provisional Xorg on the reference hardware.

The hardware-proven systemd/Xorg service invariants include:

- `RuntimeDirectory=greia-os` exists before launcher startup;
- `StandardInput=null` prevents GUI children from being SIGTTIN-stopped;
- the Xorg-owning launcher service is not wrapped in the desktop-style namespace restrictions that previously blocked VT/DRM/input access;
- Xwrapper policy matches the appliance session;
- VT1 is deliberately owned by the graphical session.

The richer profile-aware `greia_launcher.child_shell` was introduced after the original physical Xorg proof. It remains the primary entrypoint, but a failure in that composition must not turn an otherwise healthy display session into a blind restart loop. The X session therefore has a one-shot fallback to the simpler presentation entrypoint while preserving the original failure in the journal.

This fallback does not hide Xorg failure: if the display server itself cannot start, neither Python entrypoint can present a frame.

## 8. Boot sound

A short Greia startup chime is allowed and desired, but sound must never be on the critical path to the first visible launcher frame.

Contract:

- start playback only after the launcher has presented its first graphical frame;
- initialize/play asynchronously or otherwise without blocking profile-picker readiness;
- fail silently if no usable audio device exists;
- play once per boot;
- respect platform/device mute and future Parent-controlled boot-sound policy;
- do not initialize audio inside initramfs.

## 9. Build and artifact verification

The physical build is authoritative for what ships.

For the legacy development installer, the build must:

1. regenerate splash derivatives from the retained full-colour source immediately before image composition;
2. prove the canonical source copy is pixel-identical to the retained source frame;
3. prove the generated canvas is 1600×900 and contains the untouched source at its centre;
4. prove both PPMs are exact P6 encodings of that canvas;
5. build the installer and installed payload while those generated derivatives are present;
6. restore generated source-tree files afterward so the checkout is not dirtied merely by a build;
7. inspect the **finished live and target squashfs artifacts** before reporting PASS.

The artifact verifier must reject:

- the historical white/indigo two-colour signature;
- insufficient colour diversity;
- live/target PPM mismatch;
- GRUB or launcher PNG bytes that do not match the PPM canvas;
- missing/wrong 1600×900 canvas geometry;
- missing proportional GRUB theme;
- any active raw `background_image` stretch command in the installed Greia GRUB script.

A source test passing is not enough. A build report must identify the actual generated splash mode and hashes used for the produced image.

## 10. Boot speed rules

Boot polish is not permission to slow Greia down.

Forbidden on the normal boot critical path:

- arbitrary sleeps;
- polling loops waiting for graphics/audio;
- Python or SDL inside initramfs;
- runtime PNG/JPEG decoding inside initramfs;
- network waits before profile picker;
- waiting for Parent HTML/network services before showing the child shell;
- replaying every legacy animation frame at a fixed rate;
- synchronous audio initialization before the first launcher frame.

Measure with systemd/journal timestamps and physical video. Any service blocking launcher start without being a true prerequisite must be challenged.

## 11. Installer

The live installer uses the same generated full-colour PPM composition in its Linux-owned early framebuffer stage as the installed system.

On the reference Acer, the removable-media bootloader path remains the physically proven Syslinux/FAT32 implementation. Presentation changes must not be smuggled into Syslinux partitioning, MBR/VBR installation, live-media identity, kernel selection or storage-module policy.

During recovery builds, early text may intentionally remain visible. Release console suppression is reintroduced only after the boot path and graphical handoff are physically accepted.

## 12. Acceptance definition

Source existence does not constitute acceptance.

For the current full-colour/proportional splash tranche, acceptance requires all of the following on the exact built SHA:

1. source/regression checks are coherent with the full-colour contract;
2. physical builder reports `boot_artwork_mode=full-color-landscape-canvas-v1`;
3. finished-artifact verification PASS explicitly confirms full-colour 1600×900 live + target PPM and matching target PNGs;
4. installed GRUB artifact uses centred `padding` and no raw stretch path;
5. reference Acer installer still boots through the unchanged Syslinux/FAT32 media path;
6. installer early splash is visibly full-colour, clean and proportionally composed;
7. installed GRUB splash is visibly proportional and centred;
8. installed early-framebuffer splash is visibly clean/full-colour and does not change geometry unexpectedly;
9. launcher reaches a graphical frame or leaves actionable SSH/journal evidence;
10. development `greia / greia` SSH remains reachable;
11. no new kernel/initramfs/storage/live-media regression is introduced;
12. at least one second x86 target/VM eventually verifies the design contains no Acer-only geometry assumptions.

Only physical observation can close the visual acceptance gate.
