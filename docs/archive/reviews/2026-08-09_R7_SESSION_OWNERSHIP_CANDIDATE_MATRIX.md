# R7 Shell/Activity Session Ownership Candidate Matrix

**Date:** 2026-08-09  
**Status:** active R7 design/measurement record  
**Scope:** compare the serial direct-KMSDRM ownership candidate with a persistent Greia-owned compositor/session broker without changing production boot.

## 1. Decision boundary

R7 does not ask only whether SDL can open KMSDRM. It asks who owns the seat, DRM master, input devices and visible surface across:

```text
Greia Shell -> Activity start -> Activity READY -> Activity running
             -> normal/crash/timeout/forced return -> Greia Shell
```

The chosen architecture must preserve the existing R1-R6 authority model:

- Greia owns lifecycle and forced return;
- Activities do not become platform authority;
- Storage, Session, Event, Progression and Reward remain runtime-neutral Greia services;
- arbitrary Activities must not gain broad raw input or DRM authority merely because Xorg is removed;
- Python and future Web Activities must use the same platform session semantics;
- no desktop environment, generic window manager, terminal, login UI or user-visible compositor chrome is permitted.

The source-level contract is now represented by:

```text
src/greia_launcher/display_session.py
```

It models only bounded display transport plus shell/Activity ownership recovery. It cannot represent a raw device-node grant.

## 2. Candidate A — serial direct KMSDRM ownership

### Mechanism

```text
Shell owns DRM/KMS
  -> Shell destroys/releases SDL display
  -> child Activity process opens KMSDRM
  -> child exits/dies
  -> Shell opens KMSDRM again
```

### Evidence already implemented

```text
src/greia_platform/kmsdrm_serial_handoff.py
build/overlay/etc/systemd/system/greia-kmsdrm-handoff-acceptance.service
tools/r7_qemu_kmsdrm_handoff_acceptance.py
```

The experiment requires both clean child exit and intentional abrupt `os._exit(23)` without `pygame.display.quit()`, followed by shell reacquisition.

### Potential advantages

- minimum resident graphics stack while the Activity owns the display;
- no composition layer in the steady Activity path;
- easiest path to understand mechanically.

### Architectural risks

- a real Activity would need enough DRM/seat authority to acquire KMSDRM;
- raw input still needs a separate solution and must not simply be exposed wholesale;
- shell display teardown/recreation can create visible black frames or mode churn;
- every runtime must tolerate the direct-display lifecycle;
- crash/suspend/VT changes can strand the shell unless recovery is extremely reliable;
- future Web runtime integration may require a second display/session mechanism anyway.

### Current disposition

**Evidence candidate only. Not approved as production architecture.**

A QEMU PASS means only that Linux/SDL can release and reacquire KMSDRM between processes under the tested virtual topology.

## 3. Candidate B — persistent Greia-owned Wayland compositor/session broker

### Mechanism

```text
Greia compositor owns seat + DRM/KMS + input continuously
  -> Shell is one client surface
  -> Activity is another client surface
  -> Greia changes visibility/focus atomically
  -> child crash destroys its client connection
  -> Greia reveals/focuses Shell again
```

The compositor is an internal appliance component, not a desktop.

### Potential advantages

- one persistent trusted display/input owner;
- Activities receive a Wayland socket/surface transport instead of raw DRM/input devices;
- clean shell return after child crash is a compositor-owned operation rather than device reacquisition;
- Python SDL and future Web engines can share the same surface/session model;
- transition timing/focus/input policy can remain Greia-owned.

### Costs to prove

- package closure and installed-image delta;
- idle and peak RSS on C0 memory targets;
- composition/GPU cost on legacy Intel and Pi;
- cold-start and shell<->Activity transition latency;
- i386 and ARM64 availability;
- DRM/input/logind integration;
- security-maintenance burden;
- whether the selected implementation drags Xwayland/X11 runtime back into the image.

## 4. Debian Trixie reference candidates

These are **measurement references**, not accepted dependencies.

### 4.1 Cage 0.2.0-2

Debian Trixie ships Cage 0.2.0-2 for amd64, i386 and arm64. The binary itself is tiny (about 76 KiB installed on amd64 and 67 KiB on i386), and it uses `libwlroots-0.18`.

However, the Trixie binary package has a **hard dependency on `xwayland`**.

That makes the stock Trixie Cage package unsuitable as the default answer to Greia's “remove accidental X dependency” goal without further evidence. It is still valuable as a ready-made kiosk-compositor benchmark/reference implementation.

Authoritative Debian package pages used for this conclusion:

- `https://packages.debian.org/trixie/cage`
- `https://packages.debian.org/trixie/i386/cage`
- `https://packages.debian.org/trixie/arm64/cage`

### 4.2 wlroots 0.18

Debian Trixie `libwlroots-0.18` is available on amd64, i386 and arm64. It already depends on the DRM/GBM/EGL/libinput/Wayland/XKB primitives relevant to a small compositor.

Its installed shared-library size is about 1.2 MiB on amd64 and 1.3 MiB on i386 before dependency closure.

A Greia-specific wlroots compositor could avoid stock Cage's Xwayland policy, but that would move implementation/security-maintenance responsibility into Greia. That trade must be measured rather than assumed acceptable.

Authority:

- `https://packages.debian.org/trixie/libwlroots-0.18`

### 4.3 Weston 14.0.2-1

Debian Trixie Weston is a useful reference compositor because it supports Linux KMS directly and exposes a mature Wayland implementation.

The amd64 `weston` binary package itself is about 5 MiB installed and has a larger dependency surface than Cage. `xwayland` is a **recommendation**, not a hard dependency, so Greia's `--no-install-recommends` image policy can measure Weston without necessarily installing Xwayland.

Weston is therefore a useful correctness/resource reference, not an assumed production choice.

Authority:

- `https://packages.debian.org/trixie/amd64/weston`

## 5. Required measurement schema

Every backend candidate report must identify:

### Identity

- schema version;
- source commit;
- exact image profile;
- exact image SHA-256;
- architecture;
- backend ID/version;
- package source/origin.

### Installed cost

- exact package closure newly introduced relative to the Xorg production image;
- downloaded package bytes;
- installed filesystem delta;
- total image accounted MiB;
- whether any X server/Xwayland/Xorg package is introduced;
- whether any desktop/terminal/polkit/portal/session-manager recommendation was pulled in.

### Runtime cost

- compositor/session-owner process count;
- idle RSS/PSS where measurable;
- peak RSS/PSS during Shell->Activity transition;
- CPU idle sample;
- file-descriptor count;
- DRM/input devices held by the trusted owner;
- child-visible device nodes.

### Transition behavior

Measure at least 20 iterations where the platform permits it:

- Shell ready -> Activity process start;
- process start -> Activity READY;
- READY -> first visible Activity frame;
- Activity normal exit -> first restored Shell frame;
- Activity abrupt death -> first restored Shell frame;
- forced return -> first restored Shell frame;
- frame hash/visual continuity evidence;
- blank/black interval if observable.

Report median, p95 and maximum for repeated timing values. Preserve raw samples.

### Authority/security

A candidate FAILS if an ordinary Activity can:

- open the compositor's DRM card directly when it should only receive a client surface;
- read arbitrary `/dev/input/event*` nodes;
- connect to another child's private IPC/storage/event namespace;
- select an alternate user-facing desktop/session;
- spawn Xwayland/Xorg unexpectedly;
- bypass Greia's forced-return lifecycle.

### Recovery

Test:

- normal child exit;
- child crash;
- child SIGKILL/forced return;
- never-READY timeout;
- compositor/session-owner crash;
- VT disturbance where applicable;
- suspend/resume on physical hardware;
- shell process crash/restart.

## 6. Selection rules

The production backend cannot be selected from one headline benchmark.

Prefer the smallest design that satisfies all of:

1. Greia remains the trusted seat/display/input owner or can prove an equally strong serial authority boundary;
2. arbitrary Activities do not receive broad raw hardware authority;
3. shell recovery is deterministic after crash/timeout/forced return;
4. Python and Web can share the same platform lifecycle semantics;
5. C0 disk/RAM/latency limits remain healthy with measured margin;
6. amd64, i386 and ARM64 have an evidence-backed path;
7. no user-visible desktop/session environment is introduced;
8. no unnecessary X server remains in the selected direct path.

A serial path that is lighter but requires broad child DRM/input authority **loses** on security architecture.

A compositor path that is robust but consumes unacceptable C0 memory/disk **loses** on product constraints.

## 7. Current decision

No production backend is selected yet.

Current status:

```text
Xorg compatibility production path     retained
Direct SDL/KMSDRM primitive             implemented, awaiting executable image/QEMU evidence
Serial shell/child ownership probe      implemented, awaiting executable QEMU evidence
Backend-neutral ownership semantics     implemented in source
Cage                                    benchmark/reference only; stock Trixie package hard-depends on Xwayland
Weston                                  benchmark/reference only
Greia-specific wlroots broker           design candidate; no implementation decision yet
Physical Acer/legacy Intel evidence     still mandatory before production migration
Pi direct-display evidence              deferred to R8/R14 physical gates
```

## 8. Next exact step

1. keep the existing Xorg production package/profile unchanged;
2. obtain the active + serial two-boot QEMU evidence when a runner executes;
3. add exact-image package-delta measurement for Cage/Weston/wlroots reference closures without enabling them at boot;
4. prototype the smallest persistent compositor path only after its package/resource baseline is known;
5. integrate the selected backend below `DisplaySessionCoordinator`;
6. run the full authority/recovery/latency matrix;
7. only then write the R7 session-architecture ADR and consider production migration.
