# Greia R7 — X11 to direct-graphics dependency audit

**Date:** 2026-08-09
**Branch:** `r7-direct-graphics`
**Base:** merged R0–R6 source spine at `ea39f3a0455023472e9489083fe053aaf3927aca`
**Status:** R7 dependency audit complete enough to begin bounded source decoupling; direct hardware path is **not yet implemented or accepted**.

## Purpose

R7 must remove accidental X11 authority without losing the appliance properties that the current X path also happens to provide: one graphical owner, no visible Linux desktop/text path, stable shell↔Activity return, display/input settings, and a branded boot-cover handoff.

This audit therefore separates:

1. stable Greia interfaces that must survive unchanged;
2. provisional X implementation code to move behind those interfaces;
3. build/session glue that must eventually be replaced;
4. security/boot invariants that must be re-proven under direct graphics;
5. evidence gaps that cannot be closed by source tests.

## Current source architecture

### Stable interfaces to preserve

`src/greia_platform/hal.py` already defines the correct semantic layer:

- `DisplayHAL.probe() -> DisplayState`;
- `InputHAL.probe() -> InputState`;
- Audio/Media/Network/Power HALs;
- `GreiaHAL` composition;
- semantic `DeviceCapabilityService` above HAL.

Activity manifests, PermissionBroker and RuntimeManager consume semantic capabilities such as `display`, `pointer`, `keyboard` and `touch`; they must not learn DRM connector names, X display names, evdev nodes, seats or SDL backend details.

### Provisional X backend leakage

The stable HAL module still imports `XSessionHardwareController` and defines `LegacyXDisplayHAL` / `LegacyXInputHAL` inline. `LegacyXInputHAL` additionally treats presence of the `DISPLAY` environment variable as keyboard availability. These are implementation leaks into the semantic module and are the first safe R7 refactor target.

`src/greia_platform/hardware_session.py` is also X-specific:

- display topology/modes: `xrandr --query`;
- resolution change: `xrandr --output ... --auto/--mode`;
- pointer discovery: `xinput --list --short`;
- touchpad/mouse properties: `xinput list-props` / `xinput set-prop`;
- topology change token derived from raw xrandr/xinput output;
- watcher is typed directly to `XSessionHardwareController`.

The watcher behavior itself is reusable: observe settings/topology, validate against available modes, apply, persist bounded status, retry driver failures. Its controller type must become backend-neutral rather than duplicating the watcher for direct graphics.

## Build/session dependencies

### Installed launcher session

`build/overlay/etc/systemd/system/greia-launcher.service` starts:

```text
/usr/bin/xinit /usr/local/lib/greia-os/greia-x-session -- :0 vt1 ...
```

Current X-related responsibilities include:

- X server ownership of VT1;
- graphical process launch under `greiakid`;
- `xinit` process/session lifetime;
- no TCP listener;
- no VT switch/reset background flash;
- X runtime state (`/tmp/.X11-unix`, `.X0-lock`, `/var/lib/xkb`).

`greia-x-session` itself is intentionally thin: it starts the hardware-settings watcher, then the Greia launcher. The major X coupling is around this script rather than inside it.

### Boot-cover handoff

`prepare-launcher-vt` currently:

- validates/removes only a proven-stale `.X0-lock` + X socket;
- refuses ambiguous/live X ownership;
- switches to VT1;
- asks Plymouth to quit while retaining rendered pixels;
- relies on Xorg starting on the same VT with `-background none`.

This logic encodes real product/security invariants even though the mechanism is X-specific. R7 must replace the mechanism with a direct-session equivalent rather than simply deleting these checks.

### X server policy

`Xwrapper.config` restricts X startup to the physical console. `10-greia-kiosk.conf` disables VT switching, zap, zoom and VidMode. These files are implementation-specific, but the equivalent invariants remain mandatory under direct graphics: child input must not reveal a console, and ordinary application code must not acquire arbitrary display-mode/session-control authority.

### Package/profile model

The current display package set installs Xorg. `platform-shell-pygame` installs Pygame separately from the display stack, which is useful: the shell/runtime abstraction need not change when the display backend changes.

The Acer i386 profile is Debian 12 Bookworm and explicitly declares:

```toml
[display]
adapter = "xorg"
...
extra_packages = ["xserver-xorg-legacy"]
```

Direct graphics should therefore become an explicit build-profile adapter/capability. Do not silently reinterpret the existing `xorg` adapter or remove the compatibility profile before direct evidence exists.

## Launcher / installer / Activity SDL behavior

The launcher, installer and bundled Shape Garden Activity use ordinary Pygame fullscreen display creation:

```python
pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
```

They do not call Xlib/Xrandr themselves. This is a strong migration property: SDL backend selection can remain below their drawing/event code.

The installer is not yet backend-neutral in one place: `_available_resolutions()` directly constructs `XSessionHardwareController`. That must move behind the same typed Display/Settings service used by the installed shell.

## Activity sandbox implications

The current Activity sandbox:

- passes `/dev/dri` through with `--dev-bind-try`;
- inherits selected display transport variables including `DISPLAY`, `XAUTHORITY`, `WAYLAND_DISPLAY`, `SDL_VIDEODRIVER` and `XDG_RUNTIME_DIR`;
- deliberately does **not** unshare IPC because XShm currently needs shared host IPC.

Those are provisional compatibility concessions, not desired Greia APIs.

A direct Greia display/session architecture should target:

- one Greia-owned seat/display/input authority;
- no direct DRM master handoff to arbitrary Activities;
- no Activity ownership of raw input devices;
- removal of X socket/Xauthority transport;
- `--unshare-ipc` becoming possible again after XShm is gone;
- no unconditional `/dev/dri` pass-through to ordinary Activities unless a narrowly reviewed runtime/render transport actually requires it.

This is both an architectural and security improvement.

## Current external implementation evidence

Research performed 2026-08-09 against upstream/current documentation:

### SDL / Pygame

- SDL2 documents `kmsdrm` as a Linux video driver and allows selection through `SDL_VIDEODRIVER` before SDL initialization.
- Pygame 2 likewise documents `SDL_VIDEODRIVER` selection before `pygame.init()`/display initialization.
- SDL2 and SDL3 both document that KMSDRM normally requires DRM-master ownership to change display state and render.
- SDL3 3.4 adds/favors KMSDRM atomic operation where the kernel/driver supports atomic + universal planes; the current upstream SDL release line is newer than Greia's Debian 12 base.
- Debian Bookworm's SDL2 package depends on libdrm/GBM but its package description explicitly advertises X11 and Wayland builds. Therefore dependency presence is **not proof** that Greia's stock Bookworm SDL exposes a usable `kmsdrm` driver.
- Debian's current Pygame remains SDL2-based and exists on i386, so direct Pygame is architecturally plausible on legacy x86, but the exact Greia image must probe the compiled SDL driver list and perform a real KMSDRM window/frame test.

### Input / seat authority

- libinput is designed as an input stack for display servers/compositors and similar system components, not as per-application input authority.
- libinput delegates device opening through `open_restricted` / `close_restricted`, which provides a clean place to integrate seat/session authority.
- systemd-logind's `TakeControl`/`TakeDevice` model can provide/revoke seat device file descriptors according to active-session state without requiring broad direct device-node access.

These facts support a Greia-owned session/display/input layer rather than granting `/dev/input` and DRM master separately to every Activity.

### Research references

- SDL2 FAQUsingSDL: https://wiki.libsdl.org/SDL2/FAQUsingSDL
- SDL2 KMSDRM DRM-master hint: https://wiki.libsdl.org/SDL2/SDL_HINT_KMSDRM_REQUIRE_DRM_MASTER
- SDL3 KMSDRM DRM-master hint: https://wiki.libsdl.org/SDL3/SDL_HINT_KMSDRM_REQUIRE_DRM_MASTER
- SDL3 atomic KMSDRM hint: https://wiki.libsdl.org/SDL3/SDL_HINT_KMSDRM_ATOMIC
- SDL upstream releases: https://github.com/libsdl-org/SDL/releases
- Pygame environment/backend documentation: https://www.pygame.org/docs/ref/pygame.html
- Debian Bookworm SDL2 i386 package metadata: https://packages.debian.org/bookworm/i386/libsdl2-2.0-0
- libinput current documentation: https://wayland.freedesktop.org/libinput/doc/latest/
- systemd-logind device/session-control overview: https://wiki.freedesktop.org/www/Software/systemd/logind/

## Dependency classification

| Dependency | Current role | Classification | R7 action |
| --- | --- | --- | --- |
| `DisplayHAL`, `InputHAL`, `GreiaHAL` | semantic platform interface | **target interface** | preserve |
| `DeviceCapabilityService` | trusted semantic capability authority | **target interface** | preserve |
| `LegacyXDisplayHAL`, `LegacyXInputHAL` | X implementation of HAL | provisional backend | move out of generic HAL; retain only as compatibility adapter |
| `XSessionHardwareController` | display/input settings + topology | provisional backend | put behind backend-neutral controller/service contract |
| hardware settings watcher loop | apply/retry/status orchestration | reusable platform logic | keep; inject controller |
| `xinit`/Xorg on VT1 | graphical session owner | build/session glue | replace with Greia direct session owner |
| Xwrapper / Xorg kiosk flags | console/session hardening | mechanism-specific invariant carrier | preserve equivalent behavior, then remove X files |
| `.X0-lock`, `.X11-unix` cleanup | X ownership safety | X-specific glue | replace with direct seat/DRM ownership checks |
| XShm / shared host IPC | X rendering transport | legacy debt | remove; then enable Activity IPC isolation |
| `DISPLAY`, `XAUTHORITY` | X Activity transport | legacy debt | remove from direct profile/environment |
| `/dev/dri` Activity bind | current SDL/X acceleration access | over-broad provisional transport | narrow/remove after direct session design |
| Pygame fullscreen API | shell/Activity drawing abstraction | viable client API | preserve while changing SDL/session backend beneath it |
| Plymouth retained splash | branded boot cover | product invariant mechanism | redesign direct DRM handoff; retain branded-only requirement |
| Acer `display.adapter="xorg"` | compatibility profile | explicit legacy adapter | retain until direct Acer evidence passes |

## R7 implementation sequence

### R7-A — decouple stable source interfaces from X implementation

1. move `LegacyX*HAL` implementation out of generic `hal.py`;
2. make hardware-settings watcher depend on a backend-neutral controller protocol;
3. stop using `DISPLAY` as semantic keyboard detection;
4. keep existing X behavior through a compatibility adapter and require all current tests to remain green.

This tranche is source-only and should not change the installed display backend yet.

### R7-B — image/runtime direct-backend probe

Add an explicit build/runtime probe that records at minimum:

- SDL/Pygame versions;
- compiled SDL video-driver list;
- whether `kmsdrm` is present;
- available `/dev/dri/card*` + render nodes and kernel driver;
- KMS connectors/modes;
- GBM/EGL availability;
- seat/logind state;
- libinput seat/device visibility.

The gate must distinguish “libraries installed” from “backend usable”.

### R7-C — direct session prototype

Implement a Greia direct session adapter on a dedicated test/profile path. Initial target is one graphical owner on VT1 with explicit seat/DRM ownership, no desktop/WM, branded cover retained until the first Greia frame, and a guaranteed recovery path.

Prototype shell rendering first. Activity handoff comes only after ownership/recovery is deterministic.

### R7-D — shell↔Activity ownership decision

Measure two designs:

1. serial DRM ownership transfer between shell and Activity;
2. tiny Greia-owned compositor/session broker with shell and Activity as clients.

Choose from measured startup/transition latency, memory, crash recovery, Web-runtime needs, input routing and hardware compatibility. Do not adopt a compositor because it is conventional; do not reject one merely to minimize package count.

### R7-E — security and boot-cover migration

Only after direct rendering works:

- remove X socket/authority transport from direct profiles;
- enable IPC namespace isolation if no remaining runtime requires host IPC;
- remove unnecessary raw DRM access from Activity sandboxes;
- replace X lock/socket checks with direct seat/display ownership checks;
- replace X-specific same-VT boot-cover tests with direct frame-continuity tests;
- retain explicit X compatibility profile only where evidence still requires it.

## Acceptance evidence required before R7 closure

Source tests are necessary but insufficient. R7 closure needs:

- clean `make verify`;
- image/runtime proof that selected SDL direct backend exists and starts;
- QEMU/x86 direct boot to Greia shell with no X server;
- shell→Activity→shell normal and crash return;
- display mode and input-settings behavior through stable HAL;
- no `DISPLAY`/Xauthority requirement in direct profile;
- no child-accessible VT/text path under supported interactions;
- frame-by-frame boot-cover/first-frame evidence;
- RAM/disk/startup/transition measurements versus current X profile;
- available Acer physical evidence; unsupported hardware remains explicitly classified rather than silently falling back.

## Immediate next code change

Perform R7-A only: split the legacy-X HAL implementation from the generic typed HAL and make the hardware-settings watcher consume a controller protocol. Preserve behavior and run the complete provider-free gate before any package/service/display-backend change.
