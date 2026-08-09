# Greia — Standalone Engineering Handover

**Date:** 2026-08-09  
**Version:** `0.13.0-phase0-dev`  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical integration target:** `main`  
**Active branch:** `r7-direct-graphics`  
**Draft PR:** #4 — `R7: direct graphics/session migration and KMSDRM evidence path`  
**Current functional phase:** **R7 — Direct graphics/session migration**

## 1. Continuity state

Do **not** reopen the old v0.12 recovery incident. The recovered baseline is repository-managed.

The former post-v0.12 R5 `history.py` loss was resolved by a **new reviewed R5 reimplementation**, not by pretending prose was recovered source. R1–R6 are source-closed and should not be refactored again unless R7 exposes a concrete integration defect.

R7 is active. Production Greia still boots the known Xorg compatibility path. No direct-KMS normal-boot profile/package set is enabled.

GitHub is the persistent source of truth. This branch is intentionally being committed in small coherent tranches so work is not lost if an execution environment disappears.

## 2. Exact verification boundary

The last complete provider-free source gate that actually executed successfully before the current GitHub Actions launch problem was:

```text
source checkpoint: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

Do **not** claim a newer full test count until a complete gate actually executes.

Subsequent R7 source/tooling commits are persisted in GitHub but remain **awaiting executable full-run verification**. Earlier pull-request workflow jobs were created and immediately failed before step 1 with `steps = null` / zero executed steps. At the latest integration head (`eb9b8d40585579d5e5a2710eb59f6b4b7a48482d`) GitHub had not attached any workflow run or commit status at all when checked.

Those states are execution/control-plane evidence, not Greia source-test failures.

The branch head immediately before this handover update was:

```text
eb9b8d40585579d5e5a2710eb59f6b4b7a48482d
```

## 3. R7 architectural boundary

The accepted R7 target is **not** “let every Activity own DRM/input.”

The R7 dependency audit establishes:

- one Greia-owned seat/display/input authority;
- Activities remain runtime-neutral and use the existing Storage/Session/Event/Progression authorities;
- arbitrary Activities must not receive unrestricted raw DRM-master or raw-input authority merely because Xorg is removed;
- shell → Activity → shell continuity and crash recovery must be explicit;
- serial direct ownership and a tiny Greia-owned compositor/session broker must be measured rather than selected by assumption;
- Xorg remains the compatibility baseline until direct-session evidence is sufficient.

`ActivitySupervisor` remains the owner of Greia lifecycle, sandbox and platform resources. It should **not** become the DRM owner. Display/session ownership belongs above the runtime-specific process layer.

Current X behavior deliberately leaves the Shell Pygame/X surface alive while a child Activity runs. That behavior cannot simply be copied to two independent KMSDRM masters.

## 4. Legacy-X quarantine and typed HAL

R7-A/R7-B source work already in the branch:

- semantic HAL remains backend-neutral;
- legacy X display/input implementation is quarantined below the typed HAL;
- hardware watching uses injected typed controllers rather than importing X implementations into generic HAL;
- current installed launcher behavior is intentionally unchanged while direct-graphics evidence is incomplete;
- ordinary Activity APIs remain runtime/display neutral.

Detailed dependency audit:

```text
docs/reviews/2026-08-09_R7_X11_DIRECT_GRAPHICS_DEPENDENCY_AUDIT.md
```

## 5. Passive direct-graphics probe

`src/greia_platform/direct_graphics_probe.py` is passive by design. It records:

- Pygame and SDL versions;
- SDL compiled video-driver enumeration via SDL itself;
- whether `kmsdrm` is compiled;
- libdrm/GBM/EGL/input/seat library visibility;
- DRM card/render nodes and connector/mode metadata when actually available;
- bounded session transport facts;
- whether a connected connector with at least one mode is visible.

It never calls `pygame.display.set_mode`, never acquires DRM master and never treats installed libraries as active success.

A DRM card node by itself is not enough. The passive prerequisite classification requires a connected connector with at least one mode so broken/headless topology is not misdiagnosed as an ownership failure.

## 6. Active KMSDRM acceptance primitive

`src/greia_platform/kmsdrm_acceptance.py` is a separate active test. It requires:

- explicit takeover acknowledgement;
- `SDL_VIDEODRIVER=kmsdrm`;
- no X11 or Wayland transport variables;
- actual Pygame-selected driver exactly `kmsdrm`;
- fullscreen surface creation;
- deterministic rendered/flipped frames;
- bounded JSON evidence with frame SHA-256 data.

Installed maintenance path:

- `greia-kmsdrm-acceptance.service` is manual/disabled;
- runs as `greiakid` with `PAMName=login` on `/dev/tty1`;
- refuses live X and requires active VT1;
- runtime audit may collect prior evidence but never triggers the active test.

The root maintenance controller:

```text
/usr/local/sbin/greia-run-kmsdrm-acceptance
```

installs launcher restoration before stopping X and restores the normal launcher on every exit path.

## 7. PAM/logind least-privilege closure

R7 explicitly includes `libpam-systemd` in `build/package-sets/platform-base.txt` because the KMSDRM maintenance services depend on a PAM/logind seat session while images use `--no-install-recommends`.

This is deliberately **not** solved by adding `greiakid` permanently to `video`/`render`.

The intended authority is active session/seat ownership through PAM/logind/uaccess. A regression pins that policy.

## 8. Production-image hardening completed during R7

Real `modern-amd64` image work found and fixed:

- checkout UID/GID leaking into target filesystem ownership;
- interactive dpkg conffile prompts;
- unpinned debootstrap trust-root behavior;
- unbounded APT failure behavior;
- missing Plymouth/font runtime closure;
- missing ext4-fsck runtime closure;
- stale `pip-recovery` GRUB identity;
- builder cleanup errors being masked by later control flow;
- incomplete loop partition teardown;
- missing buffer flush/udev settling;
- lack of explicit partition-child disappearance checks;
- loop-association checks that reopened the block device rather than using sysfs.

A previous real image reached Debian package install, initramfs, Greia overlay, authenticated GRUB, BIOS GRUB install and footprint/profile generation. It was about 797 MiB accounted filesystem use but is **not accepted** because loop cleanup was incomplete at that revision.

The stricter cleanup helper later passed its privileged teardown micro-test. The exact finished production image still needs a complete executable rerun under the current branch.

## 9. Exact Debian SDL authority

The actual Greia image transaction resolved Debian Trixie:

```text
libsdl2-2.0-0  2.32.4+dfsg-1  amd64
python3-pygame  2.6.1-1+b2    amd64
```

Debian's SDL source packaging enables video KMSDRM and includes DRM/GBM build dependencies. That is package-build evidence only.

Greia still requires its own finished-image `SDL_GetNumVideoDrivers()` evidence and active acquisition test.

## 10. Disposable active QEMU harness

Baseline host tool:

```text
tools/r7_qemu_kmsdrm_acceptance.py
```

Baseline tests:

```text
tests/test_r7_qemu_kmsdrm_harness.py
```

Documentation:

```text
docs/testing/2026-08-09_R7_QEMU_KMSDRM_ACCEPTANCE.md
```

The harness:

1. hashes the finished production image;
2. clones it and never mutates the source image;
3. modifies only the disposable clone;
4. masks the normal launcher only in that clone;
5. boots after Greia first boot;
6. uses `virtio-vga`, `-display none`, no monitor and no guest network;
7. requires tty1 and no X;
8. runs the passive probe first;
9. starts the existing PAM/VT KMSDRM service only after passive prerequisites pass;
10. requires actual SDL driver `kmsdrm`;
11. requires rendered-frame hashes and valid surface dimensions;
12. powers off on all exit paths;
13. remounts the clone read-only and validates persisted evidence;
14. emits `ACTIVE_QEMU_KMSDRM_PASS` only on the full contract.

A QEMU PASS proves virtual DRM/KMS acquisition/rendering only. It does not prove Acer/Pi physical scanout, input routing, suspend/resume, no-visible-Linux behavior or production session architecture.

## 11. New serial shell↔child KMSDRM ownership experiment

R7-D now has a concrete serial-ownership evidence primitive:

```text
src/greia_platform/kmsdrm_serial_handoff.py
tests/test_kmsdrm_serial_handoff.py
```

Committed starting at:

```text
cb2b38b82b67fdc4aa9345526b09f6cf59c2ba04
5d18869d5b6f8374f31bca34ac664245445420cb
```

The sequence is intentionally explicit:

```text
Shell acquires KMSDRM and renders
        ↓
Shell calls SDL display quit / releases
        ↓
clean child process acquires KMSDRM and renders
        ↓
clean child exits
        ↓
Shell reacquires and renders
        ↓
second child acquires KMSDRM and renders
        ↓
second child persists evidence then os._exit(23)
WITHOUT pygame.display.quit()
        ↓
Shell reacquires after abrupt child death and renders
```

The crash child exists specifically to test kernel/SDL recovery from an Activity-like process dying without orderly SDL cleanup.

Focused provider-free tests for this new primitive were executed outside GitHub Actions against fake SDL/process boundaries:

```text
8 / 8 PASS
```

That focused result is **not** a replacement for `make verify` or hardware evidence.

### 11.1 Manual installed service

New disabled/manual unit:

```text
build/overlay/etc/systemd/system/greia-kmsdrm-handoff-acceptance.service
```

It:

- runs as `greiakid`;
- uses `PAMName=login`;
- uses tty1;
- explicitly selects `SDL_VIDEODRIVER=kmsdrm`;
- unsets X11/Wayland transport;
- refuses live X;
- is not enabled at boot;
- conflicts with the simpler active KMSDRM maintenance unit, not with normal launcher startup.

The existing root maintenance controller now accepts:

```text
greia-run-kmsdrm-acceptance active
greia-run-kmsdrm-acceptance handoff
```

`active` remains the default for compatibility.

Both modes share the same root-only stop-X / require-VT1 / strict-result-validation / unconditional-launcher-restore path.

### 11.2 Disposable two-boot QEMU handoff harness

New host tool:

```text
tools/r7_qemu_kmsdrm_handoff_acceptance.py
```

Tests:

```text
tests/test_r7_qemu_kmsdrm_handoff_harness.py
```

The wrapper deliberately reuses `QemuKMSDRMAcceptanceHarness` rather than duplicating the production-image acceptance logic.

Boot 1:

```text
exact production image
→ disposable clone
→ passive prerequisites
→ active KMSDRM acquisition/render
→ ACTIVE_QEMU_KMSDRM_PASS
```

Only after boot 1 passes, the already-disposable clone's **test runner only** is replaced for boot 2.

Boot 2:

```text
same disposable clone
→ tty1 / no X
→ serial handoff service
→ shell/clean-child/shell/crash-child/shell sequence
→ strict persisted evidence
→ SERIAL_QEMU_KMSDRM_HANDOFF_PASS
```

The source production image is never mounted or modified by this wrapper.

Focused host-side checks executed before commit proved:

- wrapper module compiles;
- generated guest script passes `sh -n`;
- plan contains the expected two boots over one disposable clone;
- strict synthetic passing evidence validates.

Again, this is source/orchestration evidence, not a real QEMU PASS yet.

## 12. Unified exact-image → active-QEMU → serial-handoff gate

`.github/workflows/r7-production-image-probe-v3.yml` remains the **single authoritative R7 production-image chain**.

At commit:

```text
eb9b8d40585579d5e5a2710eb59f6b4b7a48482d
```

the workflow was upgraded to:

1. build exact `modern-amd64` production image;
2. require builder exit 0 and zero surviving resources;
3. mount finished image read-only;
4. execute installed SDL driver enumeration inside that image;
5. if `kmsdrm` is absent, classify package work required and do not attempt takeover;
6. if `kmsdrm` is present, install QEMU;
7. run `tools/r7_qemu_kmsdrm_handoff_acceptance.py`;
8. require boot-1 `ACTIVE_QEMU_KMSDRM_PASS`;
9. require boot-2 `SERIAL_QEMU_KMSDRM_HANDOFF_PASS`;
10. require both reports to identify the exact just-built production-image SHA;
11. rerun the complete provider-free source gate;
12. persist bounded passive/package/active/handoff evidence;
13. retire the one-off workflow only after successful evidence persistence.

Positive classification becomes:

```text
SDL_KMSDRM_COMPILED_QEMU_ACTIVE_AND_SERIAL_HANDOFF_PASS
```

Negative installed-package classification remains:

```text
SDL_KMSDRM_NOT_COMPILED_PACKAGING_WORK_REQUIRED
```

A positive serial classification still does **not** select serial direct ownership as production architecture.

## 13. Current external execution blocker

Earlier current-generation PR workflow runs exhibited:

```text
workflow run created
job conclusion: failure
job steps: null
zero steps executed
no test/build log
```

This affected ordinary source verification and the production-image/QEMU gate.

For current head `eb9b8d405...`, a later check returned:

```text
workflow runs: []
combined statuses: []
```

So no current workflow execution can be claimed at all.

Do not weaken Greia gates to make GitHub summaries look green. Preserve the distinction between:

- test/build actually ran and failed;
- job was created but executed zero steps;
- no run/status was attached to the commit.

## 14. Why the serial experiment does not finish R7-D

Even if the serial QEMU experiment passes mechanically, production Greia cannot simply hand arbitrary Activities `/dev/dri/card*` and `/dev/input/*`.

That would undermine the R1–R6 authority model and make each runtime responsible for hardware ownership/recovery.

R7 still needs an explicit measured comparison between:

### Candidate A — serial direct ownership

Potential benefit:

- smallest graphics stack;
- no compositor while an Activity owns the screen.

Costs/risks to measure:

- shell surface destruction/recreation;
- black-frame/flicker latency;
- direct DRM authority in child sandbox;
- input authority problem;
- crash recovery;
- suspend/resume;
- runtime portability;
- Web runtime integration.

### Candidate B — tiny Greia-owned compositor/session broker

Potential benefit:

- one persistent Greia seat/DRM/input owner;
- Activities receive a surface protocol rather than raw hardware;
- shell and Activity recovery can remain Greia-owned;
- Web/Python can share session semantics.

Costs/risks to measure:

- installed footprint;
- idle/peak RSS;
- composition overhead on C0 hardware;
- startup latency;
- i386/Pi package feasibility;
- dependency/security maintenance.

Do not introduce a general desktop environment, shell, window manager or user-facing compositor UI. Any compositor candidate is a hidden appliance/session component only.

## 15. Mandatory resume order

Before further R7 work:

1. `AGENTS.md`
2. `README.md`
3. `docs/architecture/GREIA_ARCHITECTURE.md`
4. ADR 0012 through ADR 0017
5. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`
6. `docs/reviews/2026-08-09_R7_X11_DIRECT_GRAPHICS_DEPENDENCY_AUDIT.md`
7. `docs/testing/2026-08-09_R7_KMSDRM_ACCEPTANCE.md`
8. `docs/testing/2026-08-09_R7_QEMU_KMSDRM_ACCEPTANCE.md`
9. this handover

## 16. Exact next work

Source-side work that does **not** require physical Acer/Pi testing:

1. keep the serial handoff experiment evidence-only;
2. define the smallest Greia-owned compositor/session-broker candidate and measurement contract;
3. measure/record candidate package closure, installed delta, idle/peak RSS and process count on exact images when runners execute;
4. prototype shell↔Activity surface transition and forced-return semantics without moving Storage/Session/Event authority;
5. move display/input settings behind the final selected typed backend adapters;
6. compare direct path vs Xorg baseline for cold launch, steady RAM, crash recovery and visible transition behavior;
7. only after evidence select the R7 session architecture.

When Actions can execute:

1. run the current full source gate and record the exact test count;
2. run the unified exact-image → installed SDL → active QEMU → serial-handoff QEMU gate;
3. preserve all negative evidence;
4. if baseline active acquisition fails, investigate PAM/logind/DRM-master/connector/GBM/EGL;
5. if active passes but serial recovery fails, treat that as evidence against serial ownership rather than weakening the test;
6. if both pass, keep Xorg production and continue the compositor/session-broker comparison;
7. physical legacy Intel/Acer acceptance remains mandatory before production migration;
8. Raspberry Pi 400/500 direct DRM/KMS remains a separate R8/R14 physical gate.

No direct-KMS production profile/package set should be created until the evidence justifies it.

## 17. Non-negotiable continuity rules

- GitHub is canonical source of truth; commit coherent tranches as work proceeds.
- Do not reopen v0.12 recovery.
- Do not describe the new R5 implementation as recovered historical source.
- Do not fork Storage/Session/Event/Progression/Reward by runtime or display backend.
- Do not make Activity environment text trusted authority.
- Do not hand arbitrary Activities broad DRM/input authority merely to remove X.
- Do not expose a Linux desktop, terminal, login prompt or WM in the normal child path.
- Xorg is provisional, but it stays production until direct-session evidence is sufficient.
- Never claim hardware success from source tests, package metadata or QEMU alone.
- Preserve negative evidence.
- Distinguish “job never started,” “no workflow attached,” and “test actually failed.”
