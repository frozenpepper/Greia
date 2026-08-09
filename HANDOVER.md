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

The former lost post-v0.12 R5 `history.py` was replaced by a new reviewed R5 implementation. It must never be described as recovered historical source.

Production Greia still boots through the known Xorg compatibility path. No direct-KMS production profile/package set is enabled.

GitHub is the persistent source of truth. Coherent R7 tranches have been committed continuously so session/environment loss cannot erase the work.

The last substantive source/CI commit immediately before this handover rewrite is:

```text
cbf5f99de5fff9d17a9a16294926419bc1c3b0b6
```

That commit keeps the exact-image R7 gate eligible until real evidence has been generated.

---

## 2. Exact verification boundary — do not overclaim

The last complete provider-free source gate that actually executed successfully is still:

```text
source checkpoint: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

Do **not** claim a newer complete test count.

Current GitHub Actions executions are still failing before step 1. At current R7 source heads:

- source verification run `31292322548`: `verify` failed with `steps = null`;
- exact-image run `31292322559`: `preflight` failed with `steps = null`, therefore the expensive image job was skipped;
- clean-tree run `31292322575`: `verify` failed with `steps = null`.

A controlled rerun of the source verification job and exact-image preflight reproduced the same `steps = null` / no-log boundary. No further CI retries should be burned merely to reproduce that condition.

This is **not evidence that Greia tests failed**. It means no checkout/test/build step executed.

The one focused test result that was actually executed during this R7 tranche is:

```text
serial KMSDRM handoff fake-SDL/process suite: 8 / 8 PASS
```

That focused result is not a substitute for `make verify`, QEMU, or physical hardware evidence.

---

## 3. R7 architectural rule

R7 is not “remove Xorg by handing DRM/input to every Activity.”

The accepted boundary is:

- Greia owns the seat/display/input authority;
- arbitrary Activities must not receive broad raw `/dev/dri` or `/dev/input` authority merely because Xorg is removed;
- `ActivitySupervisor` continues to own Greia lifecycle, sandbox and platform resources, but it should **not** become the DRM owner;
- shell → Activity → shell ownership/recovery belongs above runtime-specific process mechanics;
- Python and future Web Activities must share the same platform session semantics;
- serial DRM ownership and a tiny persistent Greia-owned compositor/session broker are candidates to be **measured**, not assumed;
- production Xorg remains until the direct-session architecture has evidence and physical legacy-Intel/Acer acceptance.

Primary audit:

```text
docs/reviews/2026-08-09_R7_X11_DIRECT_GRAPHICS_DEPENDENCY_AUDIT.md
```

Candidate comparison matrix:

```text
docs/reviews/2026-08-09_R7_SESSION_OWNERSHIP_CANDIDATE_MATRIX.md
```

---

## 4. R7-A/R7-B already present

The branch already has the direct-graphics dependency cleanup needed before session migration:

- semantic HAL remains backend-neutral;
- legacy X display/input implementation is quarantined below typed interfaces;
- hardware watching uses injected typed controllers rather than importing X implementation into generic HAL;
- ordinary Activity APIs remain display/runtime neutral;
- passive direct-graphics probing is separate from active display acquisition.

`src/greia_platform/direct_graphics_probe.py` records SDL/Pygame driver inventory, DRM nodes/connectors/modes, relevant library visibility and bounded transport facts without calling `pygame.display.set_mode()` or acquiring DRM master.

A DRM card node by itself is not sufficient. The probe requires a connected connector with at least one mode before active acquisition is treated as a meaningful next test.

---

## 5. Active KMSDRM primitive and least-privilege PAM/logind path

`src/greia_platform/kmsdrm_acceptance.py` is the active acquisition primitive. It requires:

- explicit takeover acknowledgement;
- `SDL_VIDEODRIVER=kmsdrm`;
- no X11/Wayland transport variables;
- actual selected SDL driver exactly `kmsdrm`;
- fullscreen surface creation;
- rendered/flipped frames;
- bounded JSON evidence with valid frame hashes.

Installed maintenance service:

```text
build/overlay/etc/systemd/system/greia-kmsdrm-acceptance.service
```

It is manual/disabled, runs as `greiakid` with `PAMName=login` on tty1, refuses live X, and does not replace the normal launcher.

`libpam-systemd` is an explicit image dependency because this acceptance path relies on a PAM/logind seat session. Greia deliberately does **not** solve DRM authority by permanently adding `greiakid` to `video`/`render`.

Root maintenance controller:

```text
build/overlay/usr/local/sbin/greia-run-kmsdrm-acceptance
```

It installs launcher restoration before stopping X and restores the normal launcher on every exit path.

---

## 6. Serial shell↔child KMSDRM ownership experiment

New evidence-only source:

```text
src/greia_platform/kmsdrm_serial_handoff.py
tests/test_kmsdrm_serial_handoff.py
build/overlay/etc/systemd/system/greia-kmsdrm-handoff-acceptance.service
```

Important commits:

```text
cb2b38b82b67fdc4aa9345526b09f6cf59c2ba04  serial ownership probe
5d18869d5b6f8374f31bca34ac664245445420cb  focused recovery tests
906117ec3a2321778521de0f8a8c00b10a25736d  manual PAM/VT handoff service
92043ef151074ff448380d4c36eeab34dd4e5282  shared safe maintenance controller
```

Sequence:

```text
Shell acquires KMSDRM and renders
        ↓
Shell releases SDL display
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

The crash child exists specifically to test whether Linux/SDL ownership can recover after an Activity-like process dies without orderly SDL cleanup.

A PASS would prove mechanical release/reacquisition only. It does **not** prove that raw DRM/input authority is acceptable for production Activities.

The root maintenance controller now accepts:

```text
greia-run-kmsdrm-acceptance active
greia-run-kmsdrm-acceptance handoff
```

`active` remains the default.

---

## 7. Disposable two-boot QEMU evidence path

Baseline harness:

```text
tools/r7_qemu_kmsdrm_acceptance.py
```

Serial wrapper:

```text
tools/r7_qemu_kmsdrm_handoff_acceptance.py
```

Tests:

```text
tests/test_r7_qemu_kmsdrm_harness.py
tests/test_r7_qemu_kmsdrm_handoff_harness.py
```

Relevant commits:

```text
ddbe8d9633af77ee7281a80f219c84b4c3c9d462  two-boot wrapper
92abc06bc8127d4b1018dd45ae545888c83d73fc  strict host/guest evidence tests
eb9b8d40585579d5e5a2710eb59f6b4b7a48482d  exact-image active+handoff CI integration
```

Design:

### Boot 1

```text
exact production image
→ disposable clone
→ tty1 / no X / no guest network
→ passive prerequisites
→ active SDL KMSDRM acquisition/render
→ ACTIVE_QEMU_KMSDRM_PASS
```

### Boot 2

Only after boot 1 passes, the **already disposable clone's test runner** is changed:

```text
same disposable clone
→ tty1 / no X
→ serial handoff service
→ shell / clean child / shell / crashed child / shell
→ strict persisted evidence
→ SERIAL_QEMU_KMSDRM_HANDOFF_PASS
```

The source production image is never mounted or modified by this wrapper.

No real QEMU PASS has executed yet.

---

## 8. Runtime-neutral display-session ownership contract

New source:

```text
src/greia_launcher/display_session.py
tests/test_display_session.py
```

Key commits:

```text
1752eae2637e43a8a7d9c1bbc6ed8dc92f448756  display-session coordinator
772dc5b23a5a821d843738340f925122a7dd3e1a  recovery/state tests
d59f4fcad9f65bbb06224e93526bd906636ce80c  strict transport/backend pairing
f30a7c85c73387e1e39e4a0269002faad4cd6544  pairing regression tests
```

`DisplaySessionCoordinator` is deliberately above runtime-specific process launch. It models:

```text
SHELL
→ PREPARING_ACTIVITY
→ ACTIVITY_PREPARED
→ ACTIVITY_VISIBLE
→ RECOVERING_SHELL
→ SHELL
```

Prepare failure, READY/presentation failure, normal exit, crash and explicit abort converge on the same Greia-owned shell restore path. Restore failure enters a fail-closed `FAILED` state.

`DisplayTransport` can represent only bounded connection facts:

- legacy X11 endpoint;
- Wayland socket/runtime endpoint;
- evidence-only direct KMSDRM SDL selection.

It cannot represent a raw DRM/input device grant.

The pairing is strict:

```text
LEGACY_X11    -> SDL x11
WAYLAND       -> SDL wayland
DIRECT_KMSDRM -> SDL kmsdrm
```

This is the stable launcher-side semantic seam under which either serial teardown/reacquire or a persistent compositor can later be implemented.

---

## 9. Compositor/session-broker comparison

Decision record:

```text
docs/reviews/2026-08-09_R7_SESSION_OWNERSHIP_CANDIDATE_MATRIX.md
```

Current candidates:

### A. Serial direct ownership

Potentially smallest steady graphics stack, but carries serious authority/recovery/input/Web-runtime risks.

### B. Persistent Greia-owned Wayland compositor/session broker

Keeps seat/DRM/input authority in one trusted Greia-owned process and gives Activities a client surface rather than raw devices. Must prove C0 disk/RAM/latency viability.

Debian Trixie reference packages are used only as benchmarks:

- Cage 0.2.0-2: available on amd64/i386/arm64, but the stock binary hard-depends on Xwayland;
- `libwlroots-0.18`: reference runtime substrate available on amd64/i386/arm64;
- Weston 14.0.2-1: mature KMS/Wayland reference; Xwayland is a recommendation rather than a hard dependency.

No compositor package has been added to a Greia production package set.

---

## 10. Exact disposable compositor package-delta probe

New source:

```text
tools/r7_compositor_package_probe.py
tests/test_r7_compositor_package_probe.py
```

Key commits:

```text
37f01485080af27b3d0159b79104252d94be14f8  initial exact clone measurement tool
a2e63dfcfbdfba2f43646a1d74d9ceb5b915cb08  restore DNS / remove probe-log accounting
3d52118116dd8fe2203a4b4510a8f3205428e2b1  isolate probe from host session
fef55f88143ad330f2ffc30e5e036bd88fa05284  package-probe invariants/tests
c2dfd4064e319cae59320d758e3a3f28aff36c11  exact-image workflow integration
```

Fixed candidate IDs only:

```text
cage
weston
wlroots-runtime  -> libwlroots-0.18
```

The tool:

1. hashes the exact source production image;
2. clones it and never mounts the source image;
3. mounts only the disposable clone;
4. records the production package manifest and filesystem baseline;
5. snapshots `/etc/systemd/system`;
6. temporarily supplies bounded DNS plumbing and `policy-rc.d` inside the clone;
7. deliberately does **not** expose host `/run` to the chroot;
8. runs current Debian APT with bounded retries/timeouts;
9. installs the fixed candidate using:

```text
--no-install-recommends
--no-upgrade
--no-remove
--force-confold
```

10. records exact final dpkg state and downloaded `.deb` bytes;
11. cleans APT lists/cache and truncates logs to the same policy used by the production builder;
12. restores the clone's original resolver state;
13. requires `/etc/systemd/system` to be byte/symlink-identical to baseline;
14. fails if a baseline package was removed or changed;
15. computes added package count/Installed-Size plus final file/filesystem byte deltas;
16. flags newly introduced X server and desktop-risk components;
17. rehashes the source image and requires it to be unchanged.

The measurement is explicitly **incremental relative to the current Xorg production image**. It is not the eventual Xorg-removed direct-image footprint.

The clone is never enabled or booted by this tool.

No real package-delta report has executed yet because Actions never reached step 1.

---

## 11. Single authoritative exact-image workflow

File:

```text
.github/workflows/r7-production-image-probe-v3.yml
```

Current intended chain:

1. build exact `modern-amd64` production image;
2. require builder success and zero surviving loop/resources;
3. mount finished image read-only;
4. execute installed SDL driver enumeration inside that image;
5. measure Cage, Weston and wlroots incremental package deltas in separate disposable clones;
6. if installed SDL lacks `kmsdrm`, classify packaging work required and do not claim active graphics;
7. if `kmsdrm` exists, run two-boot active + serial-handoff QEMU evidence;
8. require source image SHA identity in all reports;
9. rerun the complete provider-free source gate;
10. persist package/passive/active/handoff evidence;
11. retire the one-off workflow only after successful evidence persistence.

Commit `cbf5f99de5fff9d17a9a16294926419bc1c3b0b6` fixes a subtle preflight bug: while

```text
docs/reviews/2026-08-09_R7_PRODUCTION_IMAGE_SDL_EVIDENCE.md
```

is absent, the exact-image gate remains eligible even if the newest commit is documentation-only. This prevents later handover/plan commits from accidentally suppressing the still-unexecuted evidence gate.

---

## 12. Production-image hardening already done in R7

The exact `modern-amd64` work previously found and fixed real build/image issues including:

- target filesystem ownership leaking checkout UID/GID;
- dpkg conffile interaction;
- debootstrap trust-root ambiguity;
- unbounded APT failure behavior;
- Plymouth/font closure;
- ext4-fsck runtime closure;
- stale `pip-recovery` GRUB identity;
- builder cleanup failures masked by later exceptions;
- incomplete loop partition teardown;
- missing flush/udev settle;
- missing partition-child disappearance checks;
- unsafe loop-association checks.

A previous real image reached package installation, initramfs, Greia overlay, authenticated GRUB, BIOS GRUB install and footprint/profile generation at about 797 MiB accounted filesystem use, but that historical image was not accepted because cleanup was incomplete at that revision.

The exact current image still needs a successful executable rerun.

---

## 13. What is intentionally **not** decided

Do not infer any of the following from current source work:

- serial direct ownership is **not** selected as production architecture;
- Cage is **not** selected as production compositor;
- Weston is **not** selected as production compositor;
- wlroots is **not** yet an accepted Greia-maintained dependency;
- QEMU has **not** passed current R7;
- physical Acer/legacy Intel has **not** passed direct graphics;
- Raspberry Pi direct graphics has **not** been tested in R7;
- production boot has **not** moved off Xorg;
- the current source gate has **not** produced a newer full test count.

---

## 14. Exact next work

The next blocking evidence is intentionally simple:

### When GitHub Actions can execute

Run the existing unified workflow. Do not create a parallel builder/gate.

Expected first useful evidence from one exact production image:

```text
production image build + cleanup
        ↓
installed SDL enumeration
        ↓
Cage package delta
Weston package delta
wlroots-runtime package delta
        ↓
if kmsdrm compiled:
  active QEMU KMSDRM PASS/FAIL
        ↓
  serial clean/crash/reacquire PASS/FAIL
        ↓
full make verify
```

Preserve negative evidence.

If the serial recovery test fails, treat it as evidence against serial ownership rather than weakening the test.

If active and serial both pass, **keep production Xorg** and continue the compositor/session-broker comparison.

### After exact package/resource evidence exists

1. compare exact Cage/Weston/wlroots package/file deltas;
2. select the smallest compositor/session-broker prototype worth runtime measurement;
3. implement that backend **below `DisplaySessionCoordinator`**, not inside Activity APIs;
4. measure idle/peak RSS, process count, FDs, cold start and shell↔Activity transition/recovery latency;
5. verify ordinary Activities receive only the surface transport, not raw DRM/input authority;
6. compare against the serial path and Xorg baseline;
7. write the R7 session-architecture ADR only after the evidence supports a choice;
8. perform physical legacy Intel/Acer acceptance before any production migration.

Raspberry Pi 400/500 direct-display evidence remains an R8/R14 gate after Pi image adapters exist.

---

## 15. Mandatory resume order

Before changing R7 implementation:

1. `AGENTS.md`
2. `README.md`
3. `docs/architecture/GREIA_ARCHITECTURE.md`
4. ADR 0012 through ADR 0017
5. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`
6. `docs/reviews/2026-08-09_R7_X11_DIRECT_GRAPHICS_DEPENDENCY_AUDIT.md`
7. `docs/reviews/2026-08-09_R7_SESSION_OWNERSHIP_CANDIDATE_MATRIX.md`
8. `docs/testing/2026-08-09_R7_KMSDRM_ACCEPTANCE.md`
9. `docs/testing/2026-08-09_R7_QEMU_KMSDRM_ACCEPTANCE.md`
10. this handover

---

## 16. Non-negotiable continuity rules

- GitHub is canonical source of truth; commit coherent tranches as work proceeds.
- Do not reopen v0.12 recovery.
- Do not describe the new R5 implementation as recovered historical source.
- Do not fork Storage/Session/Event/Progression/Reward by runtime or display backend.
- Do not make Activity environment text trusted authority.
- Do not hand arbitrary Activities broad DRM/input authority merely to remove X.
- Do not expose a Linux desktop, terminal, login prompt or generic WM in the normal child path.
- Xorg is provisional, but remains production until direct-session evidence is sufficient.
- Never claim hardware success from source tests, package metadata or QEMU alone.
- Preserve negative evidence.
- Distinguish clearly between `job never started`, `job skipped by dependency`, and `test/build actually failed`.
