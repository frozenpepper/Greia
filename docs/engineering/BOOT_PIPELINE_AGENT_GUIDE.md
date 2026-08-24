# Greia OS Boot Pipeline & Display Architecture Guide

> **Target Audience**: AI Agents and Engineers working on Greia OS boot, graphics, initramfs, systemd services, and display sessions.
> **Status**: Authoritative Reference / Non-Negotiable Contract.

---

## 1. Core Architectural Philosophy

### 1.1. Resolution-Agnostic Assets & Programmatic Runtime Backgrounds
* **DO NOT bake display-specific resolutions into static image files** (e.g. creating 1024x600, 1366x768, or 1920x1080 letterboxed images).
* **The Logo is an Immutable Fixed-Size Asset**: The canonical character/logo asset is stored at its native artist-rendered resolution (222x600 px for Professor Pip).
* **The Screen Background is Created Programmatically**:
  Every boot layer (GRUB, early framebuffer renderer, and Pygame launcher) is responsible for querying the physical display resolution (W x H) at runtime, filling the entire screen memory with the palette background color (pure white `#ffffff`), and blitting the unscaled 222x600 logo directly into the physical center:
  `x_0 = (W - 222) / 2`, `y_0 = (H - 600) / 2`
  - On a 1024x600 screen (e.g., Acer Aspire One): the logo spans 100% of the screen height (y = 0 to y = 600), perfectly centered at x = 401.
  - On a 1920x1080 screen: the background fills 1920x1080, and the logo sits cleanly centered at x = 849, y = 240 with zero distortion or blur.

### 1.2. Non-Destructive Asset Lineage
* **NEVER run color-distance thresholding, keying, or automated background removal on character frames.**
* The 52 animation frames (`frame_0000.png` ... `frame_0051.png`) in `assets/boot/frames/` are the **complete, full-color artist-drawn assets**.
* Running automated thresholding will replace dark navy/black interior details (eyes, pupils, shading, clothing lines) with white holes, destroying the artwork.

---

## 2. Boot Pipeline Implementation Layers

### 2.1. Layer 1: GRUB 2 Bootloader
* **File**: `build/overlay/boot/grub/greia-theme.txt` (and `tools/generate_boot_artwork.py`)
* **Configuration**:
  ```text
  title-text: ""
  desktop-color: "#ffffff"
  desktop-image: "greia-boot-logo.png"
  desktop-image-scale-method: "padding"
  desktop-image-h-align: "center"
  desktop-image-v-align: "center"
  ```
* **Behavior**: GRUB natively fills whatever VESA or UEFI GOP resolution is active with `#ffffff` and centers `greia-boot-logo.png` without stretching.

### 2.2. Layer 2: Early Framebuffer Splash (`greia-fb-splash.c`)
* **File**: `build/early-boot/greia-fb-splash.c`
* **Compiled Path**: `/usr/lib/greia-boot/greia-fb-splash`
* **Behavior**:
  1. Opens `/dev/fb0` and reads `xres`, `yres`, and pixel format via `FBIOGET_VSCREENINFO`.
  2. Fills the entire framebuffer memory with the theme background (`pack_pixel(&var, 255, 255, 255)`).
  3. Calculates centering coordinates (x0, y0) and copies the 222x600 P6 PPM pixels directly to memory.
  4. Progress bar drawing has been permanently removed from the splash binary.

### 2.3. Layer 3: Pygame Launcher Animation (`boot_intro.py`)
* **File**: `src/greia_launcher/boot_intro.py`
* **Timing Contract**:
  - `TARGET_INTRO_SECONDS = 2.2`
  - `MAX_INTRO_SECONDS = 2.5`
  - Driven monotonically via `time.monotonic()` (never `time.sleep()`).
  - Plays the 52 sequential frames smoothly at ~24 fps.
* **Display Hand-off**:
  - `_draw_frame` fills `screen.fill((255, 255, 255))` and blits the animation frame centered on the active display surface.
  - One-shot marker written to `/run/greia-os/boot-intro-played` so the intro only runs once per boot.

---

## 3. Systemd & Linux Platform Contracts (Critical Gotchas)

### 3.1. Debian Non-Root Xorg Wrapper (`/etc/X11/Xwrapper.config`)
> **The Problem**: Debian\x27s `/usr/lib/xorg/Xorg.wrap` denies non-root users from starting Xorg unless they have an active logind console session.
> Because `greia-launcher.service` runs as unprivileged user `greiakid` in a systemd service (not a console session), Xorg fails immediately on boot if `Xwrapper.config` is missing!

* **Required File**: `/etc/X11/Xwrapper.config`
  ```text
  allowed_users=anybody
  needs_root_rights=yes
  ```
* **Permissions**: `/usr/lib/xorg/Xorg.wrap` must have SUID permissions (`chmod u+s`).

### 3.2. Systemd `ConditionPathExists` vs `Requires=` Deadlock
> **The Trap**: If service B has `ConditionPathExists=!/file`, when `/file` exists, systemd **skips** service B (leaving it inactive).
> If service A has `Requires=service-B`, systemd will **refuse to start service A** because service B was skipped!

* **The Rule**: Never put `ConditionPathExists` on a service that other units depend on via `Requires=`.
* **The Solution**: Use an internal idempotency guard inside the script itself:
  ```sh
  marker=/var/lib/greia-os/init*
  [ ! -e $marker ] || exit 0
  ```
  with `RemainAfterExit=yes` in the unit. The service runs, exits 0 in 1 ms, and stays in `active (exited)` state so dependent services start normally.

### 3.3. Kernel Commandline & Intel i915 DPMS Power-down
> **The Trap**: Setting `console=null` detaches `/dev/tty1` from the kernel console. When `xinit ... vt1` runs, it fails to acquire `/dev/tty1`.
> Without a DRM master process, the Intel `i915` driver assumes an idle machine and enters DPMS display sleep after 10 seconds (turning off the LCD panel backlight).

* **Canonical Release Bootline**:
  ```text
  linux /vmlinuz root=UUID=... rw quiet splash loglevel=0 systemd.show_status=false rd.systemd.show_status=false udev.log_priority=3 vt.global_cursor_default=0 console=tty1 panic=0 systemd.crash_shell=no systemd.crash_chvt=0 consoleblank=0
  ```
  - `console=tty1`: Keeps VT1 valid for Xorg display acquisition.
  - `quiet splash loglevel=0 vt.global_cursor_default=0`: 100% silent boot (zero kernel text, zero blinking cursor).
  - `panic=0`: Prevents infinite boot loops on fatal errors.
  - `rw`: Mounts root read-write from second 0 so `systemd-journald` writes persistent logs immediately to `/var/log/journal`.

### 3.4. Persistent Systemd Journal Logging
* Directory `/var/log/journal/<machine-id>` must exist with ownership `root:systemd-journal` and permissions `2755`.
* Drop-in `/etc/systemd/journald.conf.d/00-persistent.conf` must contain:
  ```ini
  [Journal]
  Storage=persistent
  SyncIntervalSec=1s
  RateLimitIntervalSec=0
  RateLimitBurst=0
  ```

---

## 4. Verification Checklist for Agents

Before declaring any boot or display task complete:

1. [ ] **Automated Tests**: Run `make verify`. All 1,153+ tests must pass cleanly.
2. [ ] **Artwork Integrity**: Verify `assets/boot/frames/frame_0000.png` through `frame_0051.png` have not been altered with destructive thresholding.
3. [ ] **White Background**: Verify `greia-theme.txt` contains `desktop-color: "#ffffff"` and `boot_intro.py` fills `(255, 255, 255)`.
4. [ ] **Xwrapper Presence**: Verify `/etc/X11/Xwrapper.config` exists on target `/dev/sda1`.
5. [ ] **Initramfs & GRUB Regeneration**: Run `update-initramfs -u` and `update-grub` in chroot on the target root filesystem.
6. [ ] **Clean Unmount**: Ensure `/dev/sda1` is synced and cleanly unmounted before requesting a hardware reboot.
