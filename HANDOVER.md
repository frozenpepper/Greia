# Greia — Standalone Engineering Handover

**Date:** 2026-08-09  
**Version:** `0.13.0-phase0-dev`  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical integration target:** `main`  
**Active branch:** `r7-direct-graphics`  
**Draft PR:** #4 — `R7: direct graphics/session migration and KMSDRM evidence path`  
**Current functional phase:** **R7 — Direct graphics/session migration**

## 1. Continuity state

Do **not** reopen the old v0.12 recovery incident. The recovered baseline is already repository-managed.

The former post-v0.12 R5 `history.py` loss was resolved by a **new reviewed R5 reimplementation**, not by pretending prose was recovered source. R1–R6 are source-closed and are not to be refactored again unless R7 exposes a concrete integration defect.

R7 is active. Production Greia still boots the known Xorg compatibility path. No direct-KMS normal-boot profile/package set is enabled.

## 2. Exact verification boundary

The last complete provider-free source gate that actually executed successfully before the current GitHub Actions launch problem was:

```text
source checkpoint: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

Subsequent R7 source/tooling commits are persisted in GitHub but must **not** be described as fully CI-verified yet. Current pull-request workflow jobs are being created and immediately failing before step 1 (`steps = null` / zero executed steps), including ordinary R7 source verification and R0 clean verification. That is an Actions runner/account launch failure boundary, not test evidence.

The branch head immediately before this handover update was:

```text
aff082f8c8c1c280dcb9167cd8df2efb5a756f0b
```

## 3. R7 source architecture already implemented

### 3.1 Legacy-X quarantine

- semantic HAL remains backend-neutral;
- legacy X display/input implementation is quarantined below the typed HAL;
- current installed launcher behavior is intentionally unchanged while direct-graphics evidence is incomplete;
- ordinary Activity APIs remain runtime/display neutral.

### 3.2 Passive direct-graphics probe

`src/greia_platform/direct_graphics_probe.py` is passive by design. It records:

- Pygame and SDL versions;
- SDL compiled video-driver enumeration via SDL itself;
- whether `kmsdrm` is compiled;
- libdrm/GBM/EGL/input/seat library visibility;
- DRM card/render nodes and connector/mode metadata when actually available;
- bounded session transport facts.

It never calls `pygame.display.set_mode`, never acquires DRM master and never treats installed libraries as active success.

### 3.3 Active KMSDRM acceptance primitive

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
- root controller stops current X only after installing a restoration trap and restores the normal launcher on every exit path;
- runtime audit may collect prior evidence but never triggers the active test.

## 4. Real production-image work completed during R7

Building the real Debian Trixie `modern-amd64` image exposed multiple production defects. These were fixed rather than bypassed:

- overlay copy no longer imports checkout UID/GID into the target filesystem;
- intended Greia conffiles install noninteractively;
- APT has bounded native retries/timeouts;
- debootstrap signature verification is forced against a pinned official Debian archive trust root;
- Plymouth/initramfs closure includes `plymouth-label`;
- ext4 root closure includes `e2fsprogs`;
- cleanup failure can no longer be returned as successful image construction;
- loop cleanup uses normal unmounts, partition removal, buffer flush, udev settling and fail-closed association checks;
- partition children must actually disappear before the parent loop is detached;
- loop association is checked from sysfs rather than by reopening the block device;
- stale GRUB recovery identity was corrected from `pip-recovery` to authoritative `greia-recovery` and regression-tested.

Important durable commits include:

```text
478c148e...  ownership-safe/noninteractive image assembly
b67fea8a...  pinned Debian bootstrap trust root
f84d2e26...  bind checked-in GRUB generator to Greia recovery identity
097f0281...  stale GRUB contract-test identity corrected; 232/232 executed PASS
de875088...  verify kernel partition-child removal before loop detach
```

A real image build reached all of the following before the loop-teardown work was finalized:

- valid Debian Trixie Release signature;
- target package installation;
- initramfs generation;
- Greia first-boot/session overlay installation;
- authenticated `greia-recovery` GRUB contract;
- BIOS GRUB installation;
- image footprint/profile generation.

That earlier image was about 797 MiB accounted filesystem use. Its build was **not accepted** because the builder still reported an associated loop device. Do not turn that image into a PASS retroactively.

After `de875088...`, the stricter cleanup helper passed its own live privileged micro-test. The exact full production image has not yet been rebuilt successfully under that revision because GitHub Actions stopped launching jobs before step 1.

## 5. Loop teardown forensic conclusions

Do not reopen discarded theories without new evidence.

Diagnostics established:

- the historical leaked loop showed `AUTOCLEAR=1`;
- no live mount, sysfs holder or process FD was found at inspection time;
- a disposable `--partscan` lifecycle detached cleanly;
- a disposable explicit `partx -a/-d` lifecycle also detached cleanly;
- an isolated BIOS `grub-install --target=i386-pc --recheck` lifecycle detached cleanly.

Therefore:

- do not switch production from `--partscan` to explicit `partx` merely as cargo-cult;
- do not blame GRUB itself;
- current production cleanup instead verifies child partition disappearance and fails closed if it cannot prove teardown.

## 6. Exact Debian SDL authority

The actual Greia image package transaction resolved Debian Trixie:

```text
libsdl2-2.0-0  2.32.4+dfsg-1  amd64
python3-pygame  2.6.1-1+b2    amd64
```

Debian's exact SDL source package build dependencies include `libdrm-dev` and `libgbm-dev`, and its `debian/rules` explicitly uses:

```text
--disable-kmsdrm-shared
--enable-video-kmsdrm
```

This is strong package-build authority that Debian intends KMSDRM compiled into SDL rather than as an optional shared backend. It does **not** replace Greia's stricter finished-image `SDL_GetNumVideoDrivers()` runtime probe.

See:

- `docs/testing/2026-08-09_R7_QEMU_KMSDRM_ACCEPTANCE.md`
- Debian source-package/rules links recorded there.

## 7. PAM/logind least-privilege closure

A static review found a concrete R7 dependency gap after the last executed full gate:

- the acceptance service uses `PAMName=login`;
- `greiakid` intentionally does **not** belong permanently to `video` or `render`;
- the image was built with `--no-install-recommends`, so `libpam-systemd` was not guaranteed present.

Debian documents `libpam-systemd` as the PAM module that registers user sessions with logind and says software depending on logind functionality must depend on it. DRM `card*` devices are tagged for `uaccess` by systemd rules.

R7 now therefore includes `libpam-systemd` in `build/package-sets/platform-base.txt` and a regression that requires it while also forbidding the shortcut of broad static `video`/`render` membership for `greiakid`.

This change is committed but awaits an executable full CI/image run because of the current Actions launch problem.

## 8. Disposable active QEMU harness

New host tool:

```text
tools/r7_qemu_kmsdrm_acceptance.py
```

Tests:

```text
tests/test_r7_qemu_kmsdrm_harness.py
```

Documentation:

```text
docs/testing/2026-08-09_R7_QEMU_KMSDRM_ACCEPTANCE.md
```

The harness deliberately does **not** create or enable a production direct-KMS boot profile. It:

1. hashes the finished production image;
2. creates a sparse/reflink-capable disposable clone;
3. mutates only that clone;
4. verifies the installed R7 probes/services exist;
5. masks the normal X launcher only inside the clone;
6. installs a test-only one-shot boot unit after `greia-first-boot.service`;
7. boots QEMU with TCG, `virtio-vga`, `-display none`, no monitor and no guest network;
8. requires tty1 and refuses X;
9. runs the passive probe first;
10. only then starts the existing Greia PAM/VT KMSDRM acceptance service;
11. requires actual SDL driver `kmsdrm` and rendered-frame evidence;
12. powers the guest off on all exit paths;
13. remounts the clone read-only and validates persisted evidence;
14. emits `ACTIVE_QEMU_KMSDRM_PASS` only on the full evidence contract.

Host image mounting uses Greia's fail-closed cleanup helper. Cleanup errors are never hidden by an earlier exception. Guest summary failure is also not allowed to prevent shutdown.

A QEMU PASS proves virtual DRM/KMS acquisition/rendering only. It does not prove legacy Intel/Acer or Raspberry Pi physical scanout/input/session behavior and does not authorize production migration by itself.

## 9. Unified exact-image → QEMU evidence gate

`.github/workflows/r7-production-image-probe-v3.yml` now represents one authoritative chain:

1. build exact `modern-amd64` production image;
2. require builder exit 0 and zero leaked resources;
3. mount finished image read-only;
4. execute installed SDL driver enumeration inside that image;
5. if `kmsdrm` is absent, stop before active takeover and classify package work required;
6. if `kmsdrm` is present, install QEMU and run the disposable active harness;
7. require report image SHA to equal the just-built production-image SHA;
8. rerun full provider-free source gate;
9. commit bounded image/package/passive/QEMU evidence;
10. self-retire the one-off workflow only after successful evidence persistence.

Positive classification:

```text
SDL_KMSDRM_COMPILED_QEMU_ACTIVE_PASS
```

Negative installed-package classification:

```text
SDL_KMSDRM_NOT_COMPILED_PACKAGING_WORK_REQUIRED
```

This workflow currently cannot execute because Actions jobs fail before step 1. Do not interpret those red jobs as a failed image/QEMU result.

## 10. GitHub Actions launch blocker

Current symptom on connector-authored PR commits:

```text
workflow run created
job conclusion: failure
job steps: null / zero steps executed
no build/test log exists
```

It affects at least:

- `R7 direct-graphics source verification`;
- `R0 clean-tree verification`;
- `R7 exact production image and active QEMU KMSDRM evidence`.

A rerun showed the same no-step failure. This is presently an external execution blocker. Do not weaken Greia gates or alter source merely to make those red run summaries disappear.

## 11. Mandatory resume order

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

## 12. Exact next work

When Actions can execute jobs again:

1. run the permanent R7 source gate on the current branch and record the new exact test count;
2. run the unified production image → installed SDL → conditional active QEMU gate;
3. if installed SDL does not enumerate KMSDRM, fix package/build authority and repeat before active takeover;
4. if passive KMSDRM passes but QEMU active acquisition fails, preserve the guest evidence and investigate PAM/logind/DRM-master/connector/GBM/EGL ownership without changing production boot;
5. if QEMU passes, keep Xorg as production compatibility path and proceed to physical legacy-x86/Acer acceptance before considering session migration;
6. Raspberry Pi 400/500 direct DRM/KMS remains a separate physical R8 gate.

No direct-KMS production profile/package set should be created until the evidence justifies it.

## 13. Non-negotiable continuity rules

- GitHub is canonical source of truth; commit coherent tranches as work proceeds.
- Do not reopen v0.12 recovery.
- Do not describe the new R5 implementation as recovered historical source.
- Do not fork Storage/Session/Event/Progression/Reward by runtime or display backend.
- Do not make Activity environment text trusted authority.
- Do not expose a Linux desktop, terminal, login prompt or WM in the normal child path.
- Xorg is provisional, but it stays the production path until direct-session evidence is sufficient.
- Never claim hardware success from source tests, package metadata or QEMU alone.
- Preserve negative evidence and distinguish a job that never started from a test that actually failed.
