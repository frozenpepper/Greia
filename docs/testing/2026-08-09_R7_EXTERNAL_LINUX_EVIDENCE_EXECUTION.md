# Greia R7 — Local Linux Evidence Execution Protocol

**Date:** 2026-08-09  
**Status:** active local operator protocol  
**GitHub Actions policy:** not used; hosted workflows are not part of this procedure  
**Purpose:** execute the existing R7 source/image/package/QEMU evidence chain on a controlled Linux host without GitHub-hosted runners.

---

## 1. Authority and scope

This protocol is an operator procedure around existing Greia implementations. It does **not** create another image builder, package probe, KMSDRM implementation, handoff implementation, evidence classification, or production session profile.

The reused implementations are:

```text
build/build-image.sh
tools/r7_local_evidence.py
tools/r7_compositor_package_probe.py
tools/r7_qemu_kmsdrm_acceptance.py
tools/r7_qemu_kmsdrm_handoff_acceptance.py
src/greia_platform/direct_graphics_probe.py
```

`tools/r7_local_evidence.py` is only the local orchestrator. The underlying probes/harnesses retain their own strict acceptance contracts.

The orchestrator never installs host packages and never commits generated evidence. It writes all generated images/logs/reports beneath an operator-selected run root outside the repository.

---

## 2. Hard safety rules

1. **Do not use GitHub Actions.** Do not enable, trigger, rerun, or recreate automatic hosted workflows for this evidence run.
2. Use a disposable or otherwise controlled **x86-64 Linux** environment with root access.
3. Use a **disposable checkout**. Root-owned checkout is preferred because the orchestrator and image tooling run as root; do not run it inside a normal personal development checkout whose ownership/state must be preserved.
4. The run root must be outside the repository and must not already exist.
5. The repository must be clean and on `r7-direct-graphics`.
6. Never modify the production image in place. Package and QEMU probes operate on disposable clones; passive inventory mounts the production image read-only.
7. Preserve the **first failure**. Do not rerun active/serial QEMU in the same evidence attempt merely to obtain PASS.
8. Do not weaken tests, timeouts, package policy, namespace isolation, or expected classifications to make a run pass.
9. If a cleanup helper cannot detach a mount/loop device, stop and preserve diagnostics.
10. Generated evidence is reviewed before anything is copied/committed into `docs/reviews/evidence`.

---

## 3. Host prerequisites

Recommended Debian/Ubuntu-style host packages:

```bash
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  debootstrap \
  parted \
  e2fsprogs \
  grub-pc-bin \
  grub-common \
  rsync \
  gpgv \
  udev \
  util-linux \
  qemu-system-x86 \
  python3 \
  python3-pil \
  make \
  git
```

The orchestrator does **not** run `apt-get`; missing host commands fail closed with an explicit list.

Use at least 20 GiB of disposable temporary storage. Hardware KVM acceleration is not required by the current harness.

---

## 4. Prepare a disposable checkout

Example only; use your normal authenticated Git method:

```bash
git clone <GREIA_REPOSITORY> /var/tmp/greia-r7-evidence-source
cd /var/tmp/greia-r7-evidence-source
git checkout r7-direct-graphics
git status --short
```

The checkout must be clean.

If the clone is owned by a normal user and the evidence process will run as root, make a disposable root-owned copy rather than changing ownership of your normal working clone.

Example:

```bash
sudo cp -a /var/tmp/greia-r7-evidence-source /var/tmp/greia-r7-evidence-root
sudo chown -R root:root /var/tmp/greia-r7-evidence-root
cd /var/tmp/greia-r7-evidence-root
```

Do not use this procedure on the Acer internal disk or another machine whose device/filesystem state must be preserved.

---

## 5. Inspect the plan without mutation

From the disposable checkout:

```bash
SOURCE_SHA="$(git rev-parse HEAD)"
RUN_ROOT="/var/tmp/greia-r7-${SOURCE_SHA}"

python3 tools/r7_local_evidence.py \
  --run-root "$RUN_ROOT" \
  --plan-only
```

The plan must state:

```text
hosted_execution = false
github_actions_used = false
source_image_mutated = false
host_packages_installed_by_tool = false
```

It must list only the fixed package candidates:

```text
cage
weston
wlroots-runtime
```

---

## 6. Execute the local evidence chain

Run exactly once for an evidence attempt:

```bash
sudo -E python3 tools/r7_local_evidence.py \
  --run-root "$RUN_ROOT"
```

The orchestrator performs, in order:

```text
clean branch/source identity preflight
→ make verify
→ production modern-amd64 image build
→ zero surviving source-image loop association check
→ immutable production-image SHA-256
→ passive read-only installed-image SDL/DRM/input/seat probe
→ exact Cage package delta in disposable clone
→ exact Weston package delta in disposable clone
→ exact wlroots-runtime package delta in disposable clone
→ if installed SDL contains kmsdrm:
     existing active QEMU KMSDRM proof
     existing serial clean/crash/reacquire QEMU proof
  else:
     record not-run-kmsdrm-not-compiled
→ make verify again
→ source commit/worktree integrity check
→ source production-image SHA-256 recheck
→ local bounded summary
```

No generated evidence is pushed or committed automatically.

---

## 7. First-failure behavior

On failure, the orchestrator writes:

```text
<RUN_ROOT>/evidence/failure.json
```

The report records the error type/message and explicitly marks the first failure as authoritative for that attempt.

Return the run root exactly as it exists after the failure. Do not delete logs or reports. Do not reuse the same run root for another attempt.

If installed SDL reports `kmsdrm_compiled = false`, QEMU is intentionally not run and the evidence contains:

```text
qemu-status.txt = not-run-kmsdrm-not-compiled
```

That is a packaging result, not an active-KMSDRM failure.

---

## 8. Successful evidence bundle

A completed run root contains at least:

```text
evidence/plan.json
evidence/source-sha.txt
evidence/build-status.txt
evidence/production-image.sha256
evidence/production-footprint.txt
evidence/production-image-profile.json
evidence/direct-graphics-probe.json
evidence/graphics-packages.tsv
evidence/base-system-manifest.txt
evidence/cage-package-probe.json
evidence/weston-package-probe.json
evidence/wlroots-runtime-package-probe.json
evidence/qemu-status.txt
evidence/r7-local-evidence-summary.json
logs/00-make-verify-prebuild.log
logs/10-build.log
logs/90-make-verify-postbuild.log
```

When KMSDRM is compiled and active/serial evidence succeeds, the bundle additionally contains the active and handoff QEMU reports under `evidence/` and detailed QEMU logs under `qemu/`.

The summary deliberately does **not** claim active seat/input completion or physical Acer/legacy-Intel completion. Those remain separate R7 requirements.

---

## 9. Evidence to return

Return the entire run root as an archive, preserving filenames and directory structure.

Example:

```bash
sudo tar -C "$(dirname "$RUN_ROOT")" \
  -czf "${RUN_ROOT}.tar.gz" \
  "$(basename "$RUN_ROOT")"
```

Return:

1. the `.tar.gz` archive;
2. the exact source SHA;
3. whether the run completed or stopped at first failure;
4. no interpretation beyond the generated classifications unless specifically requested.

Do not rerun or modify the source before returning the evidence.

---

## 10. Acceptance boundary

A successful local QEMU run is still **not** authorization to migrate production away from Xorg/xinit.

R7 still requires:

- active seat/input evidence;
- measured compositor/session-broker comparison if package/runtime evidence justifies a prototype;
- direct-profile sandbox authority migration only after a session design is selected;
- physical legacy Intel/Acer scanout, input, suspend/resume and crash-recovery evidence;
- an evidence-backed R7 session-architecture ADR before production migration.

Pi-specific physical display evidence remains an R8/R14 responsibility after the Pi image/board adapters exist.
