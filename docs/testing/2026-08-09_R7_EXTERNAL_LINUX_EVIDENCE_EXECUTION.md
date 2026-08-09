# Greia R7 — External Linux Evidence Execution Protocol

**Date:** 2026-08-09  
**Status:** operator protocol; does not create a second R7 gate  
**Authority:** subordinate to `.github/workflows/r7-production-image-probe-v3.yml`, the active remediation plan, and the R7 acceptance documents  
**Purpose:** allow the existing R7 source/image/package/QEMU evidence chain to be executed on a controlled Linux host when GitHub-hosted Actions cannot start jobs.

---

## 1. What this protocol is — and is not

This document is a deterministic operator procedure around the **existing Greia implementation**.

It does not add:

- another image builder;
- another package probe;
- another KMSDRM acceptance implementation;
- another serial-handoff implementation;
- another evidence classification;
- another production boot profile.

The authoritative implementations remain:

```text
build/build-image.sh
tools/r7_compositor_package_probe.py
tools/r7_qemu_kmsdrm_handoff_acceptance.py
src/greia_platform/direct_graphics_probe.py
.github/workflows/r7-production-image-probe-v3.yml
```

The operator must preserve negative evidence. Never edit a test, relax a predicate, change a timeout merely to obtain PASS, install extra compositor packages into the source tree, or modify the production image in place.

---

## 2. Host requirements

Use a disposable or otherwise controlled **x86-64 Linux host** with:

- root/sudo access;
- `apt-get`;
- working network access to the Debian repositories already configured by the Greia builder/image;
- at least 20 GiB free temporary storage;
- enough RAM for image construction and a 2 GiB QEMU guest;
- the Greia repository cloned locally;
- no unrelated loop-device/mount experiments running against the same Greia image paths.

Hardware KVM acceleration is not an acceptance requirement. The existing QEMU harness decides its own QEMU invocation; do not rewrite it merely to make the test faster.

Do **not** run this protocol on the Acer internal disk or another machine whose filesystem/device state must be preserved.

---

## 3. Non-negotiable stop conditions

Stop immediately and return the evidence collected so far if any of these occurs:

1. the repository is dirty before execution;
2. the checked-out commit changes during the run;
3. `make verify` fails;
4. production image construction fails;
5. the builder returns success but leaves a loop device attached to the production image;
6. the passive finished-image probe cannot be read as valid JSON;
7. a compositor package probe reports source-image mutation, baseline package removal/change, boot/service-state change, or host namespace exposure;
8. active or serial QEMU acceptance starts and fails;
9. the source production image SHA-256 changes;
10. a cleanup helper reports that a mount/loop resource could not be detached.

**Do not rerun a failed active/serial QEMU acquisition in the same evidence attempt.** The first failure is the result for that attempt.

If installed SDL does not contain `kmsdrm`, that is **not** an active-QEMU failure. Record the packaging classification and intentionally do not run active/serial KMSDRM.

---

## 4. Prepare an isolated evidence workspace

From the repository root:

```bash
set -euo pipefail

git status --short
test -z "$(git status --short)"

git rev-parse --verify HEAD
SOURCE_SHA="$(git rev-parse HEAD)"
BRANCH="$(git branch --show-current)"
test "$BRANCH" = "r7-direct-graphics"

RUN_ROOT="${TMPDIR:-/tmp}/greia-r7-external-${SOURCE_SHA}"
test ! -e "$RUN_ROOT"
mkdir -p "$RUN_ROOT"/{image,packages,qemu,evidence,logs,mount}
printf '%s\n' "$SOURCE_SHA" | tee "$RUN_ROOT/evidence/source-sha.txt"
```

Do not put `RUN_ROOT` inside the repository.

---

## 5. Install host prerequisites

On a Debian/Ubuntu-style apt host:

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
  python3-pil
```

Confirm the commands required by the existing Greia tools are present:

```bash
for command in \
  python3 losetup mount umount findmnt partx blockdev udevadm \
  chroot du df qemu-system-x86_64; do
  command -v "$command" >/dev/null || {
    echo "MISSING HOST COMMAND: $command" >&2
    exit 1
  }
done
```

If the host package manager cannot provide these commands, stop. Do not substitute a different builder implementation.

---

## 6. Run the current complete source gate before spending build time

This is an early sanity gate, not a replacement for the workflow's later source reconfirmation.

```bash
set -o pipefail
make verify 2>&1 | tee "$RUN_ROOT/logs/00-make-verify-prebuild.log"
```

Record:

```bash
git status --short | tee "$RUN_ROOT/evidence/status-after-preverify.txt"
test -z "$(git status --short)"
test "$(git rev-parse HEAD)" = "$SOURCE_SHA"
```

If `make verify` fails, stop and return the log. Do not build an image from a source tree that failed the source gate.

---

## 7. Build the exact current `modern-amd64` production image

Use the existing production builder:

```bash
set +e
sudo build/build-image.sh modern-amd64 "$RUN_ROOT/image" \
  >"$RUN_ROOT/logs/10-build-stdout.log" \
  2>"$RUN_ROOT/logs/10-build-stderr.log"
BUILD_STATUS=$?
set -e
printf '%s\n' "$BUILD_STATUS" | tee "$RUN_ROOT/evidence/build-status.txt"
```

Expected image path:

```bash
IMAGE="$RUN_ROOT/image/greia-os-modern-amd64.img"
```

Require successful production output:

```bash
test "$BUILD_STATUS" -eq 0
test -s "$IMAGE"
test -s "$RUN_ROOT/image/greia-os-modern-amd64-footprint.txt"
test -s "$RUN_ROOT/image/greia-os-modern-amd64-image-profile.json"
```

Require that the builder did not leave the production image attached:

```bash
LEAKED="$(sudo losetup -j "$IMAGE" 2>/dev/null || true)"
printf '%s\n' "$LEAKED" | tee "$RUN_ROOT/evidence/post-builder-loop-associations.txt"
test -z "$LEAKED"
```

If `LEAKED` is non-empty, stop. Capture diagnostics before attempting cleanup:

```bash
sudo losetup --list --json --output NAME,BACK-FILE,AUTOCLEAR,PARTSCAN,RO,OFFSET,SIZELIMIT \
  >"$RUN_ROOT/evidence/loop-diagnostics.json" || true
sudo lsblk -a -o NAME,KNAME,MAJ:MIN,TYPE,PKNAME,MOUNTPOINTS \
  >"$RUN_ROOT/evidence/lsblk-diagnostics.txt" || true
```

Do not continue to package/QEMU evidence from a builder run that leaked resources.

Record immutable image identity:

```bash
sha256sum "$IMAGE" | tee "$RUN_ROOT/evidence/production-image.sha256"
IMAGE_SHA="$(cut -d' ' -f1 "$RUN_ROOT/evidence/production-image.sha256")"
cp "$RUN_ROOT/image/greia-os-modern-amd64-footprint.txt" \
  "$RUN_ROOT/evidence/production-footprint.txt"
cp "$RUN_ROOT/image/greia-os-modern-amd64-image-profile.json" \
  "$RUN_ROOT/evidence/production-image-profile.json"
```

---

## 8. Passively inspect installed SDL and direct-graphics prerequisites

Mount the **finished source production image read-only** only for this inventory step:

```bash
ROOT="$RUN_ROOT/mount"
LOOP="$(sudo losetup --find --show --partscan --read-only "$IMAGE")"
```

Install a cleanup trap before doing anything else:

```bash
cleanup_passive_mount() {
  set +e
  mountpoint -q "$ROOT" && sudo umount "$ROOT"
  sudo bash -c "source '$PWD/build/lib/safe-cleanup.sh'; safe_detach_loop '$LOOP'" || true
}
trap cleanup_passive_mount EXIT INT TERM
```

Wait for partition 1 and mount it read-only:

```bash
for _ in $(seq 1 30); do
  test -b "${LOOP}p1" && break
  sleep 0.1
done
test -b "${LOOP}p1"
sudo mount -o ro,noload "${LOOP}p1" "$ROOT"
```

Run only the passive Greia probe inside the image:

```bash
sudo chroot "$ROOT" /usr/bin/env \
  PYGAME_HIDE_SUPPORT_PROMPT=1 \
  PYTHONPATH=/opt/greia-os/src \
  PYTHONNOUSERSITE=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  python3 -m greia_platform.direct_graphics_probe \
  | tee "$RUN_ROOT/evidence/direct-graphics-probe.json"
```

Validate the basic evidence contract and record whether active KMSDRM is applicable:

```bash
python3 - "$RUN_ROOT/evidence/direct-graphics-probe.json" \
  "$RUN_ROOT/evidence/kmsdrm-compiled.txt" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert payload["schema_version"] == 1
assert payload["passive"] is True
assert payload["assessment"]["active_kmsdrm_test_required"] is True
compiled = payload["sdl"]["kmsdrm_compiled"]
assert isinstance(compiled, bool)
Path(sys.argv[2]).write_text("1\n" if compiled else "0\n", encoding="utf-8")
print("SDL drivers:", ", ".join(payload["sdl"]["video_drivers"]))
print("KMSDRM compiled:", compiled)
PY
```

Record relevant installed package versions:

```bash
sudo chroot "$ROOT" dpkg-query -W \
  '-f=${Package}\t${Version}\t${Architecture}\n' \
  libsdl2-2.0-0 python3-pygame libdrm2 libgbm1 libegl1 \
  plymouth plymouth-label e2fsprogs \
  > "$RUN_ROOT/evidence/graphics-packages.tsv"
cp "$ROOT/etc/greia-os/base-system-manifest" \
  "$RUN_ROOT/evidence/base-system-manifest.txt"
```

Release the passive mount and trap:

```bash
cleanup_passive_mount
trap - EXIT INT TERM
test -z "$(sudo losetup -j "$IMAGE" 2>/dev/null || true)"
```

Reconfirm the immutable source image:

```bash
AFTER_PASSIVE_SHA="$(sha256sum "$IMAGE" | cut -d' ' -f1)"
test "$AFTER_PASSIVE_SHA" = "$IMAGE_SHA"
```

---

## 9. Measure exact compositor/reference package deltas

The fixed R7 candidates are only:

```text
cage
weston
wlroots-runtime
```

Run the existing package probe once per candidate. Each invocation creates its own disposable clone:

```bash
for candidate in cage weston wlroots-runtime; do
  sudo python3 tools/r7_compositor_package_probe.py \
    --image "$IMAGE" \
    --output-dir "$RUN_ROOT/packages" \
    --candidate "$candidate" \
    >"$RUN_ROOT/logs/20-${candidate}-stdout.log" \
    2>"$RUN_ROOT/logs/20-${candidate}-stderr.log"
done
sudo chown -R "$(id -u):$(id -g)" "$RUN_ROOT/packages"
```

Require all three reports:

```bash
for candidate in cage weston wlroots-runtime; do
  REPORT="$RUN_ROOT/packages/greia-r7-${candidate}-package-probe.json"
  test -s "$REPORT"
  cp "$REPORT" "$RUN_ROOT/evidence/${candidate}-package-probe.json"
done
```

Validate the safety invariants:

```bash
python3 - "$RUN_ROOT/evidence" "$IMAGE_SHA" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
image_sha = sys.argv[2]
for candidate in ("cage", "weston", "wlroots-runtime"):
    payload = json.loads(
        (root / f"{candidate}-package-probe.json").read_text(encoding="utf-8")
    )
    assert payload["schema_version"] == 1
    assert payload["ok"] is True
    assert payload["candidate"] == candidate
    assert payload["source_image_sha256"] == image_sha
    assert payload["source_image_sha256_after"] == image_sha
    assert payload["source_image_mutated"] is False
    assert payload["host_devices_exposed"] is False
    assert payload["host_sysfs_exposed"] is False
    assert payload["host_run_exposed"] is False
    assert payload["boot_or_service_changes"] is False
    assert payload["packages"]["removed"] == []
    assert payload["packages"]["upgraded_or_changed"] == []
    print(
        candidate,
        "added=", payload["packages"]["added_count"],
        "installed_size_kib=", payload["packages"]["added_installed_size_kib"],
        "file_delta=", payload["filesystem"]["file_delta_bytes"],
        "fs_used_delta=", payload["filesystem"]["used_delta_bytes"],
        "x_server_components=", payload["packages"]["x_server_components"],
    )
PY
```

If any assertion fails, stop. Do not edit the report to make it pass.

Reconfirm the source image has no loop association and has the same SHA:

```bash
test -z "$(sudo losetup -j "$IMAGE" 2>/dev/null || true)"
test "$(sha256sum "$IMAGE" | cut -d' ' -f1)" = "$IMAGE_SHA"
```

---

## 10. Run active + serial QEMU only when installed SDL contains KMSDRM

Check:

```bash
KMSDRM_COMPILED="$(tr -d '\n' < "$RUN_ROOT/evidence/kmsdrm-compiled.txt")"
```

### If the value is `0`

Record:

```bash
printf '%s\n' 'not-run-kmsdrm-not-compiled' \
  | tee "$RUN_ROOT/evidence/qemu-status.txt"
```

Do **not** run active/serial KMSDRM. Continue to the final source reconfirmation.

### If the value is `1`

Run the existing two-boot harness exactly once:

```bash
set +e
sudo python3 tools/r7_qemu_kmsdrm_handoff_acceptance.py \
  --image "$IMAGE" \
  --output-dir "$RUN_ROOT/qemu" \
  --timeout-seconds 240 \
  >"$RUN_ROOT/logs/30-qemu-stdout.log" \
  2>"$RUN_ROOT/logs/30-qemu-stderr.log"
QEMU_STATUS=$?
set -e
printf '%s\n' "$QEMU_STATUS" \
  | tee "$RUN_ROOT/evidence/qemu-exit-status.txt"
sudo chown -R "$(id -u):$(id -g)" "$RUN_ROOT/qemu"
```

Copy any generated reports before evaluating the exit status:

```bash
for report in \
  greia-r7-qemu-kmsdrm-report.json \
  greia-r7-qemu-kmsdrm-handoff-report.json; do
  if test -s "$RUN_ROOT/qemu/$report"; then
    cp "$RUN_ROOT/qemu/$report" "$RUN_ROOT/evidence/$report"
  fi
done
```

If `QEMU_STATUS` is non-zero, stop here and return the first-run logs/reports. **Do not rerun it in this evidence attempt.**

For a successful exit, strictly validate classifications:

```bash
python3 - "$RUN_ROOT/evidence" "$IMAGE_SHA" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
image_sha = sys.argv[2]
active = json.loads((root / "greia-r7-qemu-kmsdrm-report.json").read_text())
handoff = json.loads(
    (root / "greia-r7-qemu-kmsdrm-handoff-report.json").read_text()
)
assert active["schema_version"] == 1
assert active["ok"] is True
assert active["classification"] == "ACTIVE_QEMU_KMSDRM_PASS"
assert active["source_image_sha256"] == image_sha
assert handoff["schema_version"] == 1
assert handoff["ok"] is True
assert handoff["classification"] == "SERIAL_QEMU_KMSDRM_HANDOFF_PASS"
assert handoff["source_image_sha256"] == image_sha
assert handoff["baseline"]["classification"] == "ACTIVE_QEMU_KMSDRM_PASS"
assert handoff["handoff"]["recovery"]["clean_child_reacquired"] is True
assert handoff["handoff"]["recovery"]["crash_child_reacquired"] is True
PY
printf '%s\n' 'active-and-serial-handoff-qemu-pass' \
  | tee "$RUN_ROOT/evidence/qemu-status.txt"
```

This QEMU PASS still does not select production serial ownership and does not substitute for physical Acer evidence.

---

## 11. Re-run the full source gate on the exact same commit

After the image/package/QEMU chain:

```bash
test "$(git rev-parse HEAD)" = "$SOURCE_SHA"
test -z "$(git status --short)"
set -o pipefail
make verify 2>&1 | tee "$RUN_ROOT/logs/40-make-verify-final.log"
test -z "$(git status --short)"
test "$(git rev-parse HEAD)" = "$SOURCE_SHA"
```

If this final `make verify` fails, the entire evidence attempt is incomplete even if image/QEMU stages passed.

---

## 12. Final immutable-image and resource checks

```bash
FINAL_IMAGE_SHA="$(sha256sum "$IMAGE" | cut -d' ' -f1)"
printf '%s\n' "$FINAL_IMAGE_SHA" \
  | tee "$RUN_ROOT/evidence/final-production-image-sha256.txt"
test "$FINAL_IMAGE_SHA" = "$IMAGE_SHA"

test -z "$(sudo losetup -j "$IMAGE" 2>/dev/null || true)"
sudo findmnt -rn -R --target "$RUN_ROOT" \
  > "$RUN_ROOT/evidence/final-mounts.txt" || true
test ! -s "$RUN_ROOT/evidence/final-mounts.txt"
```

A surviving loop or mount is a failure, not a cleanup detail to hide.

---

## 13. Build a bounded evidence archive outside the repository

Create a manifest first:

```bash
(
  cd "$RUN_ROOT"
  find evidence logs -type f -print0 \
    | sort -z \
    | xargs -0 sha256sum
) > "$RUN_ROOT/evidence-file-manifest.sha256"
```

Archive only the bounded evidence/logs — **not** the raw disk image or disposable clones:

```bash
ARCHIVE="${RUN_ROOT}.evidence.tar.gz"
tar -C "$RUN_ROOT" -czf "$ARCHIVE" \
  evidence logs evidence-file-manifest.sha256
sha256sum "$ARCHIVE" | tee "${ARCHIVE}.sha256"
printf 'EVIDENCE_ARCHIVE=%s\n' "$ARCHIVE"
```

Do not copy the raw production image into GitHub.

---

## 14. Report back exactly this information

Return:

1. source commit SHA;
2. host distribution/kernel and architecture;
3. pre-build and final `make verify` result, including real test count;
4. production image SHA-256;
5. passive SDL driver list and `kmsdrm_compiled` value;
6. Cage package report summary;
7. Weston package report summary;
8. wlroots-runtime package report summary;
9. active QEMU result or explicit `not-run-kmsdrm-not-compiled` classification;
10. serial-handoff result if active QEMU ran;
11. final source-image SHA equality result;
12. final zero-loop / zero-mount result;
13. evidence archive path and SHA-256;
14. every failure/stop condition encountered, without retrying or concealing it.

Attach or provide the bounded evidence archive where practical.

---

## 15. Prohibited actions

Do not:

- install Greia to a physical internal disk;
- modify the production `.img` in place;
- use `--keep-test-image` unless specifically requested for forensic diagnosis after a failure;
- add `greiakid` permanently to broad graphics/input groups as a workaround;
- start Xorg inside the active KMSDRM guest acceptance path;
- give an Activity raw `/dev/input` authority to make a test pass;
- change package-probe candidates;
- use `apt install --fix-broken` or upgrade/remove baseline packages inside measurement clones;
- weaken source/package/QEMU assertions;
- rerun a failed active/serial QEMU acquisition in the same evidence attempt;
- commit logs, raw images, APT archives, QEMU clones or heavyweight evidence into the source repository.

---

## 16. Interpretation rules

### Source PASS only

A source PASS proves source contracts, not Linux image or hardware behavior.

### `kmsdrm_compiled = false`

This means the exact installed SDL packaging does not expose the direct backend needed by the current active probe. Treat it as packaging/architecture evidence. Do not call it an active graphics failure or PASS.

### Active QEMU PASS

This proves SDL/Pygame can actively acquire/render through KMSDRM in the tested QEMU guest. It does not prove physical Acer scanout/input/suspend behavior.

### Serial QEMU PASS

This proves mechanical release/reacquisition after clean and abrupt child termination in that QEMU path. It does not authorize per-Activity DRM/input ownership and does not select serial production architecture.

### Package delta results

These are incremental deltas relative to the **current Xorg production image**. They are input to the compositor/session-architecture decision, not the final Xorg-removed installed footprint.

### All stages PASS

Even a complete external Linux evidence PASS does **not** automatically switch production away from Xorg. R7 still requires measured runtime/resource comparison of the viable session candidates and physical legacy Intel/Acer acceptance before production migration.
