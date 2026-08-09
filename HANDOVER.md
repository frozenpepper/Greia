# Greia — Standalone Engineering Handover

**Date:** 2026-08-09  
**Version:** `0.13.0-phase0-dev`  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical integration target:** `main`  
**Active branch:** `r7-direct-graphics`  
**Draft PR:** #4 — `R7: direct graphics/session migration and KMSDRM evidence path`  
**Current blocking phase:** **R7 — Direct graphics/session architecture**

---

## 1. Resume state

R0–R6 are source-closed. Do **not** reopen the old v0.12 recovery incident or refactor the completed authority/storage/session/runtime spine without a concrete R7 integration defect.

The former lost post-v0.12 R5 `history.py` was replaced by a new reviewed R5 implementation. Never describe it as recovered historical source.

Production Greia still boots through the known Xorg compatibility path. No direct-KMS production profile/package set is enabled and no compositor has been selected.

GitHub is the persistent source of truth. Resolve the exact branch tip from `r7-direct-graphics` when resuming rather than trusting a hand-written hash. The last source commit immediately before this handover refresh is:

```text
42b4fb416703c7fb7ef4e3c8a93475d804813661
```

That commit extends the passive direct-graphics probe with bounded seat/logind/VT/input-topology prerequisites.

---

## 2. Verification boundary — do not overclaim

The last complete provider-free source gate that actually executed successfully remains:

```text
source checkpoint: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

Do **not** claim a newer complete test count until the current tree actually executes `make verify` successfully.

Focused checks that were actually executed during R7 source development:

```text
serial KMSDRM fake-SDL/process suite before the latest evidence-strengthening edits: 8 / 8 PASS
isolated current DisplaySessionCoordinator fixture: 22 / 22 PASS
isolated current compositor-package pure-logic fixture: 14 / 14 PASS
```

The 14-test package fixture stubs only the QEMU/raw-image mount dependency required to import the helper. It covers fixed candidates, private chroot runtime planning, APT policy, package manifest comparison, resolver restoration, boot-state signatures, source-hash recheck and disposable-clone cleanup.

The serial KMSDRM source/tests were strengthened **after** the earlier 8/8 focused run. Therefore do not claim the current strengthened serial suite as executed until it really runs.

The later hardware-settings, installer-adapter, passive-seat/input, and active/serial evidence regressions are committed but have not executed in a real checkout in this session. The execution container has no GitHub DNS/network access and no existing authenticated repository checkout.

### Current GitHub Actions blocker

The newest current-head runs again failed before step 1:

```text
source verification: 31294925789
  job verify: failure, steps = null, logs = null

exact image / package delta / active+serial QEMU: 31294925798
  preflight: failure, steps = null, logs = null
  build-probe-record: skipped because preflight never executed

clean-tree verification: 31294925820
  job verify: failure, steps = null, logs = null
```

The preceding current-tree runs `31294436584`, `31294436591`, and `31294436589` showed the same zero-step condition.

No checkout, Greia test, image build, package transaction, SDL probe or QEMU step executed in those failed jobs. Do not weaken gates or burn repeated reruns merely to reproduce this infrastructure boundary.

---

## 3. Non-negotiable R7 architecture

R7 does **not** mean “remove Xorg by giving every Activity DRM/input devices.”

The accepted boundary is:

- Greia owns seat/display/input authority;
- arbitrary Activities must not receive broad raw `/dev/dri` or `/dev/input` authority merely because Xorg is removed;
- `ActivitySupervisor` continues to own lifecycle, sandbox and platform session resources, but it must not become the DRM owner;
- shell → Activity → shell surface ownership/recovery sits above runtime-specific process mechanics;
- Python and future Web Activities share the same platform session semantics;
- serial direct KMSDRM ownership and a tiny persistent Greia-owned compositor/session broker remain measurement candidates;
- production Xorg remains until evidence plus physical legacy-Intel/Acer acceptance justify migration.

Primary records:

```text
docs/reviews/2026-08-09_R7_X11_DIRECT_GRAPHICS_DEPENDENCY_AUDIT.md
docs/reviews/2026-08-09_R7_SESSION_OWNERSHIP_CANDIDATE_MATRIX.md
```

---

## 4. R7-A source decoupling is materially implemented

The R7 dependency audit identified two source leaks: X-specific HAL/settings implementation in generic platform code, and installer resolution discovery directly constructing the X controller.

Current source now has:

- semantic `DisplayHAL` / `InputHAL` unchanged in `src/greia_platform/hal.py`;
- all literal `xrandr`, `xinput`, libinput-property and subprocess mapping quarantined in `src/greia_platform/hal_legacy_x.py`;
- `LegacyXHardwareSessionController` explicitly identifies itself as `legacy-x11`;
- `src/greia_platform/hardware_session.py` contains the backend-neutral watcher/status/retry contract and requires an injected `HardwareSessionController`;
- the installed watcher CLI still explicitly composes `LegacyXHardwareSessionController` so production behavior remains Xorg today;
- hardware status now records the selected backend ID;
- `src/greia_launcher/composition.py` explicitly composes the legacy-X HAL for the installed production compatibility path;
- installer UI/state code depends only on `HardwareSessionController`;
- `src/greia_installer/composition.py` is the explicit provisional legacy-X installer composition boundary;
- installer resolution discovery can be exercised with a non-X semantic controller and demo mode requires no hardware controller.

Regression sources include:

```text
tests/test_hardware_session.py
tests/test_hal_legacy_x.py
tests/test_installer_hardware_adapter.py
```

R7-A should not be called fully verified until the current full source gate executes, but its intended source decoupling is implemented.

---

## 5. Runtime-neutral display-session ownership contract

Source:

```text
src/greia_launcher/display_session.py
tests/test_display_session.py
```

`DisplaySessionCoordinator` now models:

```text
SHELL
→ PREPARING_ACTIVITY
→ ACTIVITY_PREPARED
→ PRESENTING_ACTIVITY
→ ACTIVITY_VISIBLE
→ RECOVERING_SHELL
→ SHELL
```

Important invariants:

- `prepare_activity()` issues a launcher-internal `DisplaySessionLease`;
- READY/present/end/abort callbacks require the **exact lease object**, not merely a session ID;
- stale callbacks cannot drive a later generation even if a session ID is reused;
- a fabricated equal-value lease is not ownership;
- the backend declares its `DisplayTransportKind` and returned transport must match it;
- X11, Wayland and direct KMSDRM transports are strictly paired with SDL `x11`, `wayland` and `kmsdrm` respectively;
- Xauthority/XDG-runtime paths must be absolute and transport endpoint values are bounded;
- prepare/present failures recover through the same shell-restore path;
- combined primary + restore failures enter fail-closed `FAILED` with bounded provenance.

The isolated current fixture executed **22/22 PASS** before the subsequent unrelated R7-A/passive-probe edits.

This contract is not yet wired to a selected direct/compositor production backend. Do not invent such a backend before exact package/resource evidence exists.

---

## 6. Passive direct-graphics/seat/input probe

Source:

```text
src/greia_platform/direct_graphics_probe.py
tests/test_direct_graphics_probe.py
```

The probe is passive. It does not initialize SDL video, open DRM/input devices, acquire DRM master, call logind TakeDevice, change display state or claim working input.

It now records bounded facts for:

- exact compiled SDL video-driver inventory;
- Pygame/SDL versions;
- DRM card/render nodes;
- DRM connectors, status and modes;
- libdrm/GBM/EGL/libinput/libseat library visibility;
- `/dev/input/event*` visibility;
- bounded sysfs input-event names;
- logind runtime presence;
- seat0 runtime presence;
- count of runtime session records without leaking session IDs;
- active VT visibility;
- presence (not values) of X/Wayland/Xauthority/session transport state.

Assessment fields deliberately distinguish:

```text
scanout_connector_visible
input_topology_visible
seat_runtime_visible
kmsdrm_prerequisites_visible
active_kmsdrm_test_required = true
active_seat_input_test_required = true
```

A card node alone is not enough: KMS prerequisites require a connected connector with at least one mode. Input topology or logind runtime presence is **not** input-delivery evidence.

---

## 7. Active KMSDRM evidence primitive

Source:

```text
src/greia_platform/kmsdrm_acceptance.py
tests/test_kmsdrm_acceptance.py
```

The active primitive now requires:

- explicit display-takeover acknowledgement;
- real integer frame count, bounded 1..16 (`bool` is rejected);
- `SDL_VIDEODRIVER=kmsdrm`;
- no `DISPLAY`, `XAUTHORITY` or `WAYLAND_DISPLAY` authority;
- actual SDL-selected driver exactly `kmsdrm`;
- positive bounded fullscreen surface dimensions;
- deterministic render/flip/pump operations;
- expected rendered-buffer hash diversity before PASS;
- bounded persisted JSON evidence.

A static/no-op rendered buffer therefore fails closed instead of satisfying the gate merely by producing repeated SHA-256 strings.

The current strengthened regression file is committed but was **not executed** in a real current checkout because of the runner/container limitations above.

---

## 8. Serial shell↔child KMSDRM recovery experiment

Source:

```text
src/greia_platform/kmsdrm_serial_handoff.py
tests/test_kmsdrm_serial_handoff.py
build/overlay/etc/systemd/system/greia-kmsdrm-handoff-acceptance.service
```

Sequence remains evidence-only:

```text
Shell KMSDRM acquire/render
→ release
→ clean child acquire/render/exit
→ Shell reacquire/render
→ second child acquire/render
→ child persists evidence and os._exit(23) without pygame.display.quit()
→ Shell reacquire/render
```

The strengthened validator now additionally requires:

- no `DISPLAY`, `XAUTHORITY` or Wayland authority;
- finite bounded child timeout and strict integer frame count;
- clean child frame count exactly matches the requested count;
- each child hash is a lowercase 64-character SHA-256 digest;
- expected child frame diversity;
- valid bounded child surface dimensions;
- crash child exact intentional abrupt-exit evidence;
- three distinct shell rendered buffers across initial, clean-recovery and crash-recovery phases;
- failure-path crash-child SDL cleanup before an intentional successful `os._exit(23)` path.

A PASS still proves only mechanical serial ownership recovery. It does **not** authorize arbitrary Activities to own DRM/input hardware and does not select serial ownership as production architecture.

No current real QEMU serial PASS exists.

---

## 9. Exact compositor/reference package-delta probe

Source:

```text
tools/r7_compositor_package_probe.py
tests/test_r7_compositor_package_probe.py
```

Fixed candidates only:

```text
cage
weston
wlroots-runtime -> libwlroots-0.18
```

Each candidate is measured in its own disposable clone of the exact production image. The source image is never mounted.

The current probe:

1. hashes the source image before work;
2. clones it with reflink/sparse semantics where available;
3. records the authoritative production package manifest and filesystem baseline;
4. snapshots protected boot/service state:
   - `/etc/systemd/system`
   - `/etc/default/grub`
   - `/etc/default/grub.d`
   - `/boot/grub`;
5. temporarily supplies bounded resolver state and `policy-rc.d` inside the clone;
6. exposes **none** of host `/dev`, `/sys` or `/run`;
7. mounts a private 64 KiB tmpfs `/dev` containing only `null`, `zero`, `full`, `random`, `urandom` plus fd/stdin/stdout/stderr links;
8. mounts a fresh procfs;
9. uses fixed package names with `--no-install-recommends --no-upgrade --no-remove --force-confold`;
10. requires each requested package actually to be present after the transaction;
11. rejects baseline package removals/version/architecture changes;
12. rejects protected boot/service state changes;
13. cleans APT state/log noise and restores resolver plumbing;
14. rehashes the source image even when measurement fails;
15. removes the disposable clone by default on both success and failure; `--keep-test-image` is explicit diagnostic opt-in;
16. records exact package/file/filesystem deltas and introduced X-server/desktop-risk components.

The chroot is explicitly **not** claimed to sandbox arbitrary hostile package code. The candidates are fixed trusted Debian packages; unnecessary host namespaces are removed because the measurement does not need them.

The isolated current pure-logic fixture executed **14/14 PASS**. No real package transaction on the current production image has executed yet.

---

## 10. Single authoritative exact-image workflow

File:

```text
.github/workflows/r7-production-image-probe-v3.yml
```

Do not create another image builder or competing R7 evidence chain.

The intended chain remains:

```text
exact modern-amd64 production image
→ builder success + zero leaked loop/resources
→ installed SDL/passive direct probe
→ Cage delta
→ Weston delta
→ wlroots-runtime delta
→ if kmsdrm compiled: active KMSDRM QEMU
→ serial clean/crash/reacquire QEMU
→ complete provider-free source gate
→ persist bounded evidence
→ retire one-off workflow only after successful persistence
```

The preflight remains eligible while:

```text
docs/reviews/2026-08-09_R7_PRODUCTION_IMAGE_SDL_EVIDENCE.md
```

is absent, so later documentation commits cannot suppress the still-unexecuted evidence gate.

---

## 11. Activity sandbox boundary remains intentionally unchanged for now

Current installed Activity sandbox still has compatibility concessions:

- shared host IPC because current XShm needs it;
- selected X/Wayland/SDL transport variables may be inherited;
- broad `/dev/dri` is currently bind-passed for the accepted X compatibility path.

Do **not** remove these blindly while production still uses Xorg.

The target direct-session architecture must instead make display transport and sandbox authority explicit so that, after a compositor/direct design is selected and proven, R7-E can:

- remove X socket/Xauthority transport;
- enable IPC namespace isolation where no runtime requires host IPC;
- remove or narrowly broker raw DRM access for ordinary Activities;
- keep seat/input/DRM authority in trusted Greia components.

`ActivitySupervisor` must not become the DRM owner.

---

## 12. Production decision remains unchanged

Production boot stays on Xorg.

Do not infer any of the following from current source work:

- no compositor is selected;
- serial direct ownership is not selected;
- Cage/Weston/wlroots are references only;
- no current real package-delta report exists;
- no current active-QEMU KMSDRM PASS exists;
- no current serial-handoff QEMU PASS exists;
- no legacy Intel/Acer direct-graphics PASS exists;
- no Pi direct-graphics PASS exists;
- no current source head has a successful complete `make verify` result.

Even a future QEMU active+serial PASS will not switch production. Physical legacy Intel/Acer scanout/input/suspend/crash evidence remains mandatory before migration.

---

## 13. Exact next work

The next useful result must come from a **genuinely executable** source/exact-image environment, not another speculative display mechanism.

When a runner actually starts:

1. run the current complete source gate and record its exact count;
2. run the existing unified exact-image workflow;
3. preserve all negative classifications;
4. compare exact Cage/Weston/wlroots package/file deltas;
5. if installed SDL lacks `kmsdrm`, fix packaging before active acquisition;
6. if active KMSDRM or serial recovery fails, treat it as architectural evidence rather than weakening the test;
7. only after exact package/resource evidence exists, choose the smallest compositor/session-broker reference worth runtime prototyping below `DisplaySessionCoordinator`;
8. measure idle/peak RSS, process/FD count, startup and shell↔Activity transition/recovery latency against serial ownership and Xorg;
9. prove ordinary Activities receive only the selected client transport, not raw seat/input/DRM authority;
10. write the R7 session-architecture ADR only after evidence supports a choice;
11. perform physical legacy Intel/Acer acceptance before any production migration.

Raspberry Pi 400/500 direct-display evidence remains an R8/R14 gate after Pi image adapters exist.

---

## 14. Mandatory resume order

1. `AGENTS.md`
2. `README.md`
3. `docs/architecture/GREIA_ARCHITECTURE.md`
4. ADR 0012 through ADR 0017
5. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`
6. `docs/reviews/2026-08-09_R7_X11_DIRECT_GRAPHICS_DEPENDENCY_AUDIT.md`
7. `docs/reviews/2026-08-09_R7_SESSION_OWNERSHIP_CANDIDATE_MATRIX.md`
8. `docs/testing/2026-08-09_R7_KMSDRM_ACCEPTANCE.md`
9. `docs/testing/2026-08-09_R7_QEMU_KMSDRM_ACCEPTANCE.md`
10. this `HANDOVER.md`

---

## 15. Continuity rules

- GitHub is canonical; commit coherent tranches continuously.
- Do not reopen v0.12 recovery.
- Do not describe the new R5 implementation as recovered historical source.
- Do not fork Storage/Session/Event/Progression/Reward by runtime or display backend.
- Do not make Activity environment text trusted authority.
- Do not hand arbitrary Activities broad DRM/input authority merely to remove X.
- Do not expose a Linux desktop, terminal, login prompt or generic WM in normal child paths.
- Xorg remains production until direct-session evidence is sufficient.
- Never claim hardware success from source tests, package metadata, isolated fixtures or QEMU alone.
- Preserve negative evidence.
- Distinguish `job never started`, `job skipped by dependency`, `focused source check passed`, and `full test/build actually passed`.
