# Greia Boot Experience

**Status:** active architecture; exact full-colour presentation requires physical acceptance for each materially changed boot path  
**Date:** 2026-08-24  
**Authority:** this document defines the child-visible boot UX; exact build profiles/source remain authoritative for what is actually implemented.

For implementation/recovery procedure, also read:

```text
docs/engineering/BOOT_PIPELINE_AGENT_GUIDE.md
skills/greia-os-work/BOOT.md
```

## 1. Product requirement

Greia must feel like a children's appliance, not a Linux desktop that happens to launch an application.

For a normal successful boot the child-visible sequence is:

```text
firmware
  → immediate Greia graphical first frame
  → visually continuous Greia artwork through kernel + initramfs
  → launcher-owned five-second animation
  → two-second hold on the final frame + gentle boot chime
  → profile picker
```

There must be no intentional child-visible Linux console, blinking text cursor, ordinary kernel/service log stream, getty, shell prompt, boot menu or black interstitial introduced by Greia in the successful release path.

The Greia-owned boot artwork is **full colour**. It must never be reduced to a binary mask, thresholded into a two-colour silhouette, recoloured as a single foreground colour, or stretched to match the physical display. The composition must remain proportional and centred.

During an open physical-hardware recovery gate, explicit `*-dev` profiles intentionally keep tty1/status output available. Diagnostic visibility is development policy and does not redefine the normal child-facing release UX.

Greia should reach an interactive profile picker as quickly as the hardware permits **before** the intentional launcher presentation begins. Hidden stalls/retries must be removed; the explicit 5-second animation plus 2-second final-frame hold is product presentation and must not be shortened incidentally as a performance optimization.

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

For installed GRUB, the static image is rendered through a theme using proportional `padding` and centred horizontal/vertical alignment. Raw `background_image` stretch is forbidden for Greia artwork.

The normal Greia menu entry is automatic and `--unrestricted`. Editing/command access is protected separately by the canonical owner credential; normal child boot must not require a password.

### Kernel/initramfs

Plymouth is not part of the target Greia architecture.

As soon as a writable fbdev framebuffer exists, a tiny Greia-owned early renderer paints the canonical static composition directly. It must be architecture-safe, nonblocking, fail-soft and independent from high-level graphics runtimes.

Initramfs regeneration is **not** part of every boot/presentation change. It is required only when an initramfs-owned input changes; see the boot operating guide/skill for the mandatory generated-artifact checks before a physical reboot.

### Graphical session / launcher

The launcher owns the actual intro animation. Animation starts only after Greia has a real graphical surface. The launcher first presents a continuation of the static artwork, animates the complete sequence for five seconds, then deliberately holds the final frame for two more seconds before revealing the profile picker.

Audio also starts here, never in initramfs.

## 3. Canonical artwork and generated presentation canvas

The retained final legacy frame is the authoritative raw artwork source:

```text
assets/boot/frames/frame_0051.png
```

Current source contract in `tools/generate_boot_artwork.py`:

```text
untouched full-colour source frame (222×600)
        ↓
canonical 1024×600 white presentation canvas
  - source centred at native resolution
  - pure-white surrounding background
  - no mask / threshold / recolour / quantisation
        ├─ GRUB/static launcher PNG
        └─ initramfs P6 PPM
```

The generated 1024×600 canvas is one current shared intermediate composition, not a request to bake separate files for every display. GRUB and the early framebuffer renderer fit that whole composition proportionally to the actual viewport. The launcher animation owns its own viewport centering/fitting behavior.

This corrects older living prose that described a 1600×900 generated canvas; source now uses `CANVAS_SIZE = (1024, 600)`.

The physical legacy installer builder must regenerate derivatives immediately before composing the live and target filesystems. A successful source-tree edit is not evidence that an image contains the new splash.

## 4. Why destructive artwork extraction is rejected

The historical generator attempted to extract a light foreground from a dark legacy frame using luminance thresholds and a median filter, then repainted the result as indigo on white.

That design is rejected because it:

- discards the source colours;
- destroys antialiasing and fine detail;
- can turn noisy source/background transitions into visible speckle and broken silhouettes;
- creates a result that can look like corrupted framebuffer output even when pixel packing is correct;
- made source-level tests encode a visual defect as an invariant.

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
- uses the generated composition background for any letterboxing;
- fits the entire generated canvas proportionally and centres it;
- emits no boot-console output of its own;
- never waits for a framebuffer;
- currently accepts explicit real milestone progress through `--progress` as defined by `GREIA_BOOT_PROGRESS.md`.

The P6 parser consumes exactly the one structural newline after `maxval`; it must never skip arbitrary low-valued raster bytes as if binary pixel data were whitespace.

Initramfs invokes the idempotent draw attempt at natural stages rather than polling/sleeping. If no compatible fbdev device appears, the helper exits immediately and boot continues.

### Stage C — X/display handoff

The framebuffer composition must not be deliberately cleared to black immediately before the launcher appears.

The current Xorg path uses `-background none`, requesting that the video driver preserve the previous framebuffer where possible. Physical hardware decides whether that is sufficient for a seamless transition. If a driver cannot preserve it, fallback presentation should use the same composition/background rather than a black flash.

The current compatibility backend launches Xorg on `vt1`. Console/VT policy therefore cannot be changed in isolation from Xorg acquisition and physical acceptance. R7 remains the authority for replacing this provisional display architecture.

### Native-size rule for pygame boot art (owner request 2026-10-21)

The launcher intro (frames and static canvas) and the live-installer intro draw the Greia logo at its **original pixel size**, centred on pure white. They never upscale (an upscaled logo looks soft on a 1280x800 laptop). The art shrinks proportionally, with one shared factor `min(1, screen_w/art_w, screen_h/art_h)` (`greia_platform.boot_animation.native_scale`), only when the display is smaller than the art (e.g. the 1024x600 Acer shows the 222x600 frames at native size, a 1024x480 display scales them down). Not yet covered: GRUB (`desktop-image-scale-method: padding` has no native option and scales to fit) and the early framebuffer splash (`build/early-boot/greia-fb-splash.c` fits proportionally to the screen); both still enlarge on larger screens, a possible follow-up needing a generated-canvas or C change.

### Stage D — launcher intro

The launcher owns a real intro. It is distinct from the static early-boot cover.

Current source timing in `src/greia_launcher/boot_intro.py` is:

```text
ANIMATION_SECONDS = 5.0
FINAL_FRAME_HOLD_SECONDS = 2.0
MAX_INTRO_SECONDS = ANIMATION_SECONDS + FINAL_FRAME_HOLD_SECONDS
```

The intended visual sequence is therefore exactly:

```text
0.0s → 5.0s   sequential 52-frame animation
5.0s → 7.0s   exact final frame held unchanged
then           profile picker
```

Requirements:

- first frame visually continues the boot presentation;
- the complete animation phase lasts five seconds;
- the exact final frame remains visible for an additional two seconds;
- timing is driven from monotonic elapsed time;
- display/events are pumped during the intentional presentation so the session remains responsive;
- frames may be dropped if rendering is slow, but timing must remain duration-based rather than sleeping a fixed amount per source frame;
- automatically fit to the real viewport without distorting artwork;
- no dependency on `/usr/share/plymouth`;
- play once per machine boot, not on every launcher restart;
- a development/test escape hatch may skip it, but release UX defaults to enabled.

The earlier 0.75–0.95-second/≤1.0-second prose and the brief 2.2/2.5-second recovery-session implementation were both incorrect for the intended design and are superseded by this explicit 5+2-second contract.

### Stage D (installer) — live-installer start-up animation

The live installer plays the same Greia logo animation before its language-first screen (added 2026-10-17; SOURCE + headless/desktop review only, no physical evidence yet):

```text
static boot canvas (first flip, continues the fb splash) → boot cover released
  → 5 s animation → 2 s hold on frame_0051 → chime (if audio works)
  → language-first screen
```

- Frame discovery, viewport fitting and duration-based frame selection are shared with the launcher in `src/greia_platform/boot_animation.py`; the launcher keeps its own markers/KPIs/systemd readiness in `boot_intro.py` and its behaviour is unchanged. The `aplay` chime player is shared through `src/greia_platform/boot_chime.py`.
- Owner: `src/greia_installer/boot_intro.py` (`InstallerIntro`), started from `entrypoint.choose_language` on the same display.
- Unlike the Shell intro it is **skippable by any key, mouse button, touch or controller button**; the skipping input is consumed and never chooses a language (the chooser also needs its own press before a release counts).
- Once per boot through `/run/greia-installer/intro-played`; chime marker `/run/greia-installer/boot-chime-played`. `GREIA_SKIP_BOOT_INTRO=1` / `GREIA_SKIP_BOOT_CHIME=1` remain development escape hatches.
- Frames are scaled to the viewport height and converted to the display format once at load; the loop only blits and flips when the frame index changes.
- Fail-soft: the animation needs `assets/boot/frames/` and the chime needs `assets/audio/system/greia-boot-chime.wav` **inside the live root**. `compose_install_live_content` (build owner) currently stages only core icons and fonts, so until the live allowlist adds them the installer shows the static canvas and goes straight to the language screen. The unprivileged installer user also needs audio-device access for the chime; without it the chime is silently skipped.

## 6. Console, diagnostics and owner recovery

Console suppression is independent from splash implementation.

Normal/release Greia intends to suppress ordinary child-visible console presentation while preserving diagnostics through the journal and authorized maintenance paths. Exact current release kernel arguments are source-owned by `10_greia_appliance` + `boot_contract.py` and must not be copied from stale prose.

During current Acer development/recovery, explicit development profiles (`*-dev`, `boot.console_policy = "diagnostic"`) intentionally use visible diagnostics, including tty1 and non-rebooting panic behavior. Every policy requires `panic=0`, so a fatal kernel/initramfs error remains observable instead of automatically rebooting into an evidence-destroying loop.

The developer release candidate (`legacy-x86-i686-rc`, 2026-10-17) keeps SSH but uses the quiet policy in both the installer and the installed OS: no kernel, systemd, live-boot or login text and no cursor; the Greia artwork and animation are the only visible stages. Diagnostics stay available, not visible: the Syslinux `verbose` label (hold Shift/Alt at USB boot), the owner-restricted GRUB `greia-os-diagnostics` entry (hold Shift), developer SSH and a bounded persistent journal. Owner decision 2026-10-18: the quiet RC also clears the stock Syslinux version/copyright banner with the one-byte form-feed `clear.msg` display file (quiet template/media only; the diagnostic template stays observable). The short `Loading /vmlinuz…` lines remain until the kernel starts, then the Greia framebuffer cover owns the screen. Exact arguments and enforcement points: `docs/engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md` §7. Physical evidence for the quiet RC path: UNPROVEN.

Do not solve consolelessness by deleting diagnostics. **Invisible is not the same as unavailable.**

Developer/test installs must remain reachable over developer SSH according to the owner-approved development contract:

```text
user: greia
password: greia
```

GRUB edit/command recovery uses the same owner identity:

```text
user: greia
password: greia
```

The target stores only the GRUB PBKDF2 hash. The historical default `greia-recovery` identity/random per-install secret is no longer the current default contract.

Root SSH remains disabled. The server may generate its own machine-local host identity automatically; that is not an operator credential.

## 7. Graphical-session resilience

The current installed path remains provisional Xorg on the reference hardware.

The hardware-proven systemd/Xorg service invariants include:

- volatile runtime roots exist before launcher startup through their systemd/tmpfiles owner;
- `StandardInput=null` prevents GUI children from being SIGTTIN-stopped;
- the Xorg-owning launcher service is not wrapped in desktop-style namespace restrictions that block VT/DRM/input/runtime/log access;
- Xwrapper policy matches the appliance session;
- VT1 is deliberately owned by the graphical session.

The richer profile-aware `greia_launcher.child_shell` was introduced after the original physical Xorg proof. It remains the primary entrypoint, but a failure in that composition must not turn an otherwise healthy display session into a blind restart loop. The X session therefore has a one-shot fallback to the simpler presentation entrypoint while preserving the original failure in the journal.

This fallback does not hide Xorg failure: if the display server itself cannot start, neither Python entrypoint can present a frame.

### First-boot dependency invariant

`greia-launcher.service` requires `greia-first-boot.service`. Therefore first boot must remain a successful/satisfiable oneshot on later boots rather than being skipped by a unit-level marker condition.

The script owns exact idempotency using:

```text
/var/lib/greia-os/initialized
```

Do not use a wildcard marker such as `init*`.

## 8. Boot sound

A short Greia startup chime is allowed and desired, but sound must never be on the critical path to the first visible launcher frame.

Contract:

- start playback only after the launcher has presented its first graphical frame;
- initialize/play asynchronously or otherwise without blocking the intentional animation/hold timing;
- fail silently if no usable audio device exists;
- play once per boot;
- respect platform/device mute and future Parent-controlled boot-sound policy;
- do not initialize audio inside initramfs.

## 9. Build and artifact verification

The physical build is authoritative for what ships.

For the legacy development installer, the build must:

1. regenerate splash derivatives from the retained full-colour source immediately before image composition;
2. prove the canonical source copy is pixel-identical to the retained source frame;
3. prove the generated canvas uses the current source-declared geometry and contains the untouched source at its centre;
4. prove both PPMs are exact P6 encodings of that canvas;
5. build the installer and installed payload while those generated derivatives are present;
6. restore generated source-tree files afterward so the checkout is not dirtied merely by a build;
7. inspect the **finished live and target artifacts** before reporting PASS.

The artifact verifier must reject:

- the historical white/indigo two-colour signature;
- insufficient colour diversity;
- live/target PPM mismatch;
- GRUB or static PNG bytes that do not match the intended generated composition;
- geometry that disagrees with the current generator contract;
- missing proportional GRUB theme;
- any active raw `background_image` stretch command in the installed Greia GRUB script.

A source test passing is not enough. A build report must identify the actual generated splash mode and hashes used for the produced image.

### Change-scoped boot regeneration

Do not add `update-initramfs -u`, `update-grub` or `grub-install` to a verification checklist as generic rituals.

- regenerate initramfs only for initramfs-owned changes, then inspect the newly generated target initrd before reboot;
- regenerate GRUB only for GRUB-owned changes, then run `grub-script-check` and the Greia boot contract against generated `grub.cfg`;
- run `grub-install` only when bootloader installation itself is the evidenced change/problem.

See `skills/greia-os-work/BOOT.md` for the physical pre-reboot recovery gate.

## 10. Boot speed rules

Boot polish is not permission to tolerate hidden boot latency.

Forbidden on the normal boot critical path:

- arbitrary sleeps outside the explicit launcher presentation timing;
- polling loops waiting for graphics/audio;
- Python or SDL inside initramfs;
- runtime PNG/JPEG decoding inside initramfs;
- network waits before the launcher presentation/profile picker;
- waiting for Parent HTML/network services before showing the child shell;
- synchronous audio initialization before the first launcher frame.

Measure with systemd/journal timestamps and physical video. Any service blocking launcher start without being a true prerequisite must be challenged.

The launcher presentation deliberately consumes seven seconds after the graphical handoff: five seconds of animation and two seconds holding the final frame. That is intentional product timing, not a performance regression. Performance work must reduce everything **around** that explicit sequence rather than silently shortening it.
