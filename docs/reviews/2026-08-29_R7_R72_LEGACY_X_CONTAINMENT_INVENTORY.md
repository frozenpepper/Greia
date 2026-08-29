# R7.2 Legacy-X containment inventory

Date: 2026-08-29
Status: **source-integrated; execution pending; physical Acer evidence pending**

This document records the R7.2 containment boundary. It is not a backend-selection decision and it does not close R7.

## Goal

Greia may continue to use Xorg as the provisional installed compatibility backend while R7 is measured, but X11/Xorg must not become part of the Activity API or leak implementation mechanics through generic launcher/runtime code.

The intended boundary is:

- Activities: backend independent;
- generic Greia lifecycle/runtime/display contracts: backend neutral;
- trusted composition: selects one installed backend;
- Legacy-X modules/session/build profile: own X11/Xorg mechanics;
- future Wayland/direct prototypes: must implement the same semantic contracts without changing Activity code.

## Classification

### A. Explicit Legacy-X adapter/session ownership — acceptable during R7

These files intentionally own X-specific implementation mechanics:

- `src/greia_platform/hal_legacy_x.py`
  - `xrandr` display topology/mode application;
  - `xinput` pointer/keyboard probing and bounded libinput property application.
- `src/greia_platform/hardware_session_legacy_x.py`
  - production entrypoint that explicitly composes `LegacyXHardwareSessionController` into the backend-neutral watcher.
- `src/greia_launcher/display_session_legacy_x.py`
  - typed X11 display transport for the provisional shared-X session.
- `src/greia_launcher/shell_window_legacy_x.py`
  - one-shot no-window-manager X11 focus repair through libX11.
- `build/overlay/usr/local/lib/greia-os/greia-x-session`
  - provisional X session wrapper and startup-time XInput compatibility defaults.
- `build/overlay/etc/X11/**`
  - Xwrapper, kiosk flags, and libinput/Xorg compatibility configuration.

These are migration adapters, not Activity APIs.

### B. Build/profile compatibility plumbing — acceptable but provisional

The legacy x86 image profiles currently choose Xorg explicitly:

- `build/profiles/legacy-x86-i686.toml`
- `build/profiles/legacy-x86-i686-dev.toml`

Current package/profile dependencies include:

- `xserver-xorg-core`;
- `xserver-xorg-input-libinput`;
- `xinit`;
- `xinput`;
- `x11-xserver-utils`;
- legacy Intel/VESA/fbdev video packages;
- `xserver-xorg-legacy`.

The installed service also explicitly launches the provisional Xorg path:

- `build/overlay/etc/systemd/system/greia-launcher.service`
- `build/overlay/usr/local/lib/greia-os/prepare-launcher-vt`

These files must remain until a replacement backend has passed the physical Acer comparison. Removing them merely to make the repository look backend-neutral would destroy the known compatibility path without improving the Activity architecture.

### C. Generic platform leaks found and corrected in this tranche

#### C1. Generic launcher owned Xlib focus mechanics

Before R7.2, `greia_launcher/main.py` inspected SDL/X11 state and called Xlib directly to focus the fullscreen Shell window.

Now:

- generic launcher calls one `ShellWindowController.after_window_created()` hook;
- installed trusted composition chooses `LegacyXShellWindowController`;
- development composition chooses `NoopShellWindowController`;
- native Xlib mechanics live only in `shell_window_legacy_x.py`;
- the controller does not sniff `SDL_VIDEODRIVER` to choose whether it is active.

This is a one-shot post-window operation and adds no render-loop polling or per-frame work.

#### C2. Generic hardware watcher selected Legacy-X internally

Before this tranche, `greia_platform.hardware_session` had a backend-neutral watcher but its module `main()` still imported and instantiated `LegacyXHardwareSessionController`.

Now:

- `hardware_session.py` contains the semantic watcher/protocol only;
- `hardware_session_legacy_x.py` owns the current backend-specific executable entrypoint;
- `greia-x-session` invokes the Legacy-X entrypoint explicitly.

This makes the generic watcher reusable by the future selected backend rather than hiding X selection inside a generic module.

#### C3. Ordinary Activity sandbox received direct DRM authority

Before this tranche, Bubblewrap added:

`--dev-bind-try /dev/dri /dev/dri`

for ordinary Activity launches.

That contradicted the R7 contract: display transport is a platform-issued semantic lease, while ordinary Activities must not gain direct DRM device-node authority.

The bind has been removed. A regression test pins that ordinary Activity sandbox commands contain no `/dev/dri`, `/dev/input`, `/sys/class/drm`, or `/sys/class/input` host authority.

This change is **not yet physically accepted on Acer**. If an existing Activity fails because it relied on direct DRM nodes, treat that as evidence of leaked backend authority and investigate the actual SDL/X11 transport requirement; do not automatically restore broad DRM access.

## D. Activity-level backend assumptions

R7.1 supplies the Activity backend-independence policy and enforces it in:

- standalone Activity validation;
- project validation;
- installed Python runtime validation.

The policy rejects direct backend imports/environment probing/device paths/native-library probing/backend commands and SDL/Pygame backend introspection while allowing normal backend-neutral Pygame/SDL display, rendering and event APIs.

R7.2 does not weaken or duplicate that policy.

## Known provisional debt that is intentionally not hidden

### Hard-coded Synaptics startup tuning

`greia-x-session` still applies a small set of startup-time properties to the literal device name `SynPS/2 Synaptics TouchPad` before the parent-owned hardware controller applies persisted settings.

This is contained inside the Legacy-X compatibility session, so it is not an Activity or generic-platform API violation. It is nevertheless hardware-specific policy and should not survive into the final common display/input architecture. During later input work, replace this bootstrap hack with platform-owned semantic input discovery/settings where physical Acer evidence allows it.

### Xwrapper privilege

Current `Xwrapper.config` uses `allowed_users=anybody` and `needs_root_rights=yes` because the appliance systemd session must start the provisional X server outside a normal console login.

This is explicitly provisional compatibility plumbing and a security-sensitive release item. If Xorg remains the final v1 backend, it requires dedicated threat-model and negative-security acceptance; if Wayland/common compositor wins, remove the obsolete Xwrapper path.

### Wayland socket projection requirement

The Activity sandbox intentionally creates a private `/run` tmpfs. Therefore a future Wayland transport cannot merely pass the host `XDG_RUNTIME_DIR` and `WAYLAND_DISPLAY`: the compositor socket would be hidden.

R7.6 must project only the required compositor socket into a private child runtime directory and set child-facing transport values accordingly. Do **not** solve this by broadly bind-mounting the host runtime directory, which could expose unrelated D-Bus/PipeWire/desktop sockets.

## Source-level acceptance required before advancing

The R7.2 source gate must prove at least:

1. generic launcher imports and starts without direct Xlib/X11 focus mechanics;
2. installed composition explicitly selects Legacy-X shell/display/HAL collaborators;
3. development composition remains backend-neutral/no-op where appropriate;
4. generic hardware watcher has no Legacy-X backend selection;
5. Legacy-X entrypoint composes the existing hardware controller;
6. Activity sandbox command exposes no direct DRM/raw-input host device nodes;
7. display transport injection remains typed and strips stale inherited competing backend variables;
8. R7.1 Activity backend-independence audit is green;
9. canonical `make verify` is green.

See `docs/testing/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_SOURCE_AND_ACER_ACCEPTANCE.md`.

## Physical Acer acceptance required

R7.2 is not closed until the actual Acer proves that containment did not break the known compatibility path, especially after removal of direct Activity `/dev/dri` access.

Minimum physical evidence includes:

- boot to Greia Shell with no child-visible Linux UI;
- keyboard focus in the no-WM X session;
- pointer/touchpad operation;
- Writing launch/render/input/save/return;
- Painting launch/render/input/save/return;
- deliberate Activity crash recovery to Shell;
- repeated launch/return cycles;
- no material frame-pacing, CPU, or memory regression against the accepted Acer baseline.

## R7.2 disposition

**Implementation status:** source-integrated.

**Verification status:** execution pending.

**Hardware status:** Acer acceptance pending.

**R7 status:** open.

Do not begin treating Xorg as the final architecture merely because the compatibility adapter is now cleaner. The later R7 backend comparison still decides whether the common Greia userspace stack is Wayland/compositor or Xorg for v1.