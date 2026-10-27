# Acer A/B clean-source smoke retry

> **HISTORICAL RETRY PROCEDURE (superseded 2026-10-27):** For current source fixes and consolidated A/B update acceptance, use [GREIA_UPDATE_RELEASE_ACCEPTANCE.md](GREIA_UPDATE_RELEASE_ACCEPTANCE.md). This older command sequence and its pinned fixture assumptions are reference material only, not an additional mandatory gate.

Date: 2026-10-25 · Status: **UNPROVEN; Linux VM work order; Session 04 OPEN**

**Latest result (2026-10-26, current-source rerun from `1275e0be1`):**
install and first boot PASS; `update-status` and
`update-verify` return `STATUS -> OK` / `VERIFIED`, then the test-only guest
control's hard-coded 30 s socket timeout fires during `update-stage` while the
~714 MB candidate is being written. Healthy B is not reached. The failure is a
harness control-bound defect; loops leaked and were cleaned with the safe
helper. The stage-retry guide below now permits reuse only after explicit source and
artifact checks. See
`docs/reviews/2026-10-26_AB_SMOKE_CLEAN_SOURCE_RERUN_EVIDENCE.md`.

## Current route (2026-10-26 follow-up)

Start with [`2026-10-26_AB_STAGE_RETRY.md`](2026-10-26_AB_STAGE_RETRY.md).
It retries only healthy A-to-B using the current-source `1275e0be1` bundles
and accepted-A image when its source-diff, artifact-hash, first-boot and offline
checks all pass. The current fixes affect test orchestration only. Old `866ba6827`
artifacts remain invalid. Do not use the failed healthy-update clone.

Use this rebuild procedure only when shipped/build inputs changed or the
required images/packages are actually missing or corrupt. A failed harness
test, missing host tool, attached loop, timeout or report-schema check is not
a rebuild trigger; diagnose it against the existing inputs first. When a
rebuild is justified, build
both fixtures and installer from one current committed `main` SHA, install,
first-A health, then healthy A-to-B. Do not patch the guest manually. Stop at
the first failed leg before any larger fault matrix. Routine Python/Activity
ZIP updates do not require rebuilding an A/B image.

Use the documented x86_64 Debian/Ubuntu host with root/sudo, QEMU i386,
`qemu-img`, loop/mount, squashfs and GRUB EFI i386+x64; disk use below 80%.
Read `SETUP.md` and `docs/agents/GREIA_AGENT_OPERATIONS.md`; evidence goes
outside checkout. Manual QEMU uses `-cpu n270`. No Mac build/mount/QEMU,
hosted Actions, physical device, USB media or host `/dev`.

## 1. Freeze source and gates

Start after capacity and role-aware hash changes are committed on clean `main`.
Freeze one SHA for all build inputs; use a unique evidence directory:

```bash
set -euo pipefail
test "$(git branch --show-current)" = main
git pull --ff-only
test -z "$(git status --porcelain)"
export SOURCE_HEAD="$(git rev-parse HEAD)" RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
export UPDATE_EVIDENCE="/var/tmp/greia-ab-smoke-$SOURCE_HEAD-$RUN_ID"
mkdir -m 0700 "$UPDATE_EVIDENCE"
git rev-parse HEAD > "$UPDATE_EVIDENCE/source-head.txt"
git status --short > "$UPDATE_EVIDENCE/source-status.txt"
uname -a > "$UPDATE_EVIDENCE/host.txt"
python3 --version >> "$UPDATE_EVIDENCE/host.txt"
qemu-system-i386 --version >> "$UPDATE_EVIDENCE/host.txt"
qemu-img --version >> "$UPDATE_EVIDENCE/host.txt"
df -h "$UPDATE_EVIDENCE" > "$UPDATE_EVIDENCE/free-space.txt"
```

Run the source gate and preserve pipeline statuses. Compare exact IDs/messages
with `HANDOVER.md` and clean-baseline findings in
`docs/reviews/2026-10-23_SYSTEM_UPDATE_IMPLEMENTATION_EVIDENCE.md`; do not reuse
old counts. Latest comparable Linux retry: **5,959 tests, 7 failures, 3 errors,
3 skips** (`docs/reviews/2026-10-26_AB_SMOKE_RETRY_EVIDENCE.md`, source `866ba6827`). It is
comparison evidence, not a waiver; full gate is NOT GREEN. Improvements may
disappear on Linux. Stop on new failures, higher counts, changed cause or lost
logs. A later native macOS abort is not a Linux baseline.

```bash
set +e; set -o pipefail
make verify 2>&1 | tee "$UPDATE_EVIDENCE/make-verify.log"
VERIFY_PIPE_STATUS=("${PIPESTATUS[@]}"); VERIFY_STATUS="${VERIFY_PIPE_STATUS[0]}"
VERIFY_TEE_STATUS="${VERIFY_PIPE_STATUS[1]}"
set -e
printf '%s\n' "$VERIFY_STATUS" > "$UPDATE_EVIDENCE/make-verify.exit"
printf '%s\n' "$VERIFY_TEE_STATUS" > "$UPDATE_EVIDENCE/make-verify-tee.exit"
```

Compare this log's exact failures/errors with the cited baseline. Stop on any
new failure, increased count, changed cause, or failed log write. If the run
is either green or matches the documented red baseline, record that review:

```bash
export BASELINE_REVIEW=matched   # set only after the exact comparison above
test "$VERIFY_TEE_STATUS" = 0
test "$BASELINE_REVIEW" = matched
```

Then run the focused source suites; all must pass before building:

```bash
set +e; set -o pipefail
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/run_tests.py \
  test_x8_qemu.test_product test_x8_qemu.test_product_install \
  test_x8_qemu.test_product_boot_health test_x8_qemu.test_session04_legs \
  test_x8_qemu.test_product_boot_health_identity test_system_update_service \
  test_system_updates test_parent_system_updates test_update_privileged_bridge -v \
  2>&1 | tee "$UPDATE_EVIDENCE/ab-product-focused.log"
FOCUSED_PIPE_STATUS=("${PIPESTATUS[@]}"); FOCUSED_STATUS="${FOCUSED_PIPE_STATUS[0]}"
FOCUSED_TEE_STATUS="${FOCUSED_PIPE_STATUS[1]}"
set -e
printf '%s\n' "$FOCUSED_STATUS" > "$UPDATE_EVIDENCE/ab-product-focused.exit"
printf '%s\n' "$FOCUSED_TEE_STATUS" > "$UPDATE_EVIDENCE/ab-product-focused-tee.exit"
if (( FOCUSED_STATUS != 0 || FOCUSED_TEE_STATUS != 0 )); then
  echo "Focused A/B source suite failed; stop before image build." >&2; exit 1
fi
```

## 2. Build clean baseline fixture and installer

Use the existing experimental fixture and image builders, not old bundles or
the patched installer from the prior retry:

```bash
test "$(git rev-parse HEAD)" = "$SOURCE_HEAD" && test -z "$(git status --porcelain)"
export UPDATE_BASE_VERSION="$(cat VERSION)"
export UPDATE_BASE_FIXTURE_ID="greia-acceptance-fixture-$UPDATE_BASE_VERSION"
export UPDATE_BASE_OUT="$UPDATE_EVIDENCE/base-fixture"
sudo -E unshare --mount --propagation private -- python3 tools/greia_release.py doctor --output "$UPDATE_EVIDENCE"
sudo -E unshare --mount --propagation private -- python3 tools/greia_release.py build-acceptance-fixture --version "$UPDATE_BASE_VERSION" --output "$UPDATE_BASE_OUT"
export UPDATE_BASE_FIXTURE="$UPDATE_BASE_OUT/$UPDATE_BASE_FIXTURE_ID"
export UPDATE_BASE_REPORT="$UPDATE_BASE_FIXTURE/release-report.json"
export UPDATE_BASE_BUNDLE="$UPDATE_BASE_FIXTURE/updates/acer-aspire-one-i386-ab.greiaupdate"
python3 - "$UPDATE_BASE_REPORT" "$UPDATE_BASE_FIXTURE_ID" <<'PYCODE'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert (r["artifact_class"], r["release_eligible"], r["release_id"]) == ("experimental_acceptance_fixture", False, sys.argv[2]), r
PYCODE
python3 tools/greia_release.py inspect "$UPDATE_BASE_REPORT"
python3 tools/greia_update.py inspect "$UPDATE_BASE_BUNDLE"
sudo -E unshare --mount --propagation private -- env PIP_RELEASE_BUILD=0 bash build/build-installer-image.sh acer-aspire-one-i386-ab "$UPDATE_EVIDENCE/base-installer" --release-bundle "$UPDATE_BASE_BUNDLE"
export UPDATE_INSTALLER="$UPDATE_EVIDENCE/base-installer/greia-os-installer-acer-aspire-one-i386-ab.img"
test -f "$UPDATE_INSTALLER"
```

## 3. Build next fixture from the same SHA

The next bundle must come from a disposable copy at `SOURCE_HEAD` with only
`VERSION` changed. `0.13.1-phase0-dev` is the next fixture for current
`0.13.0-phase0-dev`; if `VERSION` differs, select and record the next version
under the existing repository convention.

```bash
export UPDATE_NEXT_VERSION=0.13.1-phase0-dev UPDATE_NEXT_SOURCE="$UPDATE_EVIDENCE/source-next"
test "$(git rev-parse HEAD)" = "$SOURCE_HEAD" && test -z "$(git status --porcelain)" && git clone --shared --no-checkout . "$UPDATE_NEXT_SOURCE"
git -C "$UPDATE_NEXT_SOURCE" checkout --detach "$SOURCE_HEAD"
test "$(git -C "$UPDATE_NEXT_SOURCE" rev-parse HEAD)" = "$SOURCE_HEAD"
printf '%s\n' "$UPDATE_NEXT_VERSION" > "$UPDATE_EVIDENCE/next-version.txt"
printf '%s\n' "$UPDATE_NEXT_VERSION" > "$UPDATE_NEXT_SOURCE/VERSION"
test "$(git -C "$UPDATE_NEXT_SOURCE" diff --name-only)" = VERSION
git -C "$UPDATE_NEXT_SOURCE" diff -- VERSION > "$UPDATE_EVIDENCE/next-version.patch"
export UPDATE_NEXT_ID="greia-acceptance-fixture-$UPDATE_NEXT_VERSION" UPDATE_NEXT_OUT="$UPDATE_EVIDENCE/next-fixture"
sudo -E unshare --mount --propagation private -- python3 "$UPDATE_NEXT_SOURCE/tools/greia_release.py" doctor --output "$UPDATE_EVIDENCE"
sudo -E unshare --mount --propagation private -- python3 "$UPDATE_NEXT_SOURCE/tools/greia_release.py" build-acceptance-fixture --version "$UPDATE_NEXT_VERSION" --output "$UPDATE_NEXT_OUT"
export UPDATE_NEXT_FIXTURE="$UPDATE_NEXT_OUT/$UPDATE_NEXT_ID"
export UPDATE_NEXT_REPORT="$UPDATE_NEXT_FIXTURE/release-report.json"
export UPDATE_NEXT_BUNDLE="$UPDATE_NEXT_FIXTURE/updates/acer-aspire-one-i386-ab.greiaupdate"
python3 - "$UPDATE_NEXT_REPORT" <<'PYCODE'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r["artifact_class"] == "experimental_acceptance_fixture" and r["release_eligible"] is False, r
PYCODE
python3 "$UPDATE_NEXT_SOURCE/tools/greia_release.py" inspect "$UPDATE_NEXT_REPORT"
python3 "$UPDATE_NEXT_SOURCE/tools/greia_update.py" inspect "$UPDATE_NEXT_BUNDLE"
sha256sum "$UPDATE_BASE_REPORT" "$UPDATE_BASE_BUNDLE" "$UPDATE_INSTALLER" "$UPDATE_NEXT_REPORT" "$UPDATE_NEXT_BUNDLE" > "$UPDATE_EVIDENCE/artifacts.sha256"
stat -c '%n %s bytes' "$UPDATE_BASE_BUNDLE" "$UPDATE_INSTALLER" "$UPDATE_NEXT_BUNDLE" > "$UPDATE_EVIDENCE/artifacts.size"
```

Stop if either fixture is not marked experimental and non-release, inspection
fails, the copy differs beyond `VERSION`, or the clean installer build fails.

## 4. Run the three-leg A/B smoke

`ProductHarness.run_product` uses the control seam and production disk parsers
to drive the shipped installer on a disposable image; this is installer/service
proof, not rendered GUI proof. A raw digest change is observational if that
slot booted, because writable ext4 changes on its own boot. Still fail wrong
slot/default or release ID, health/transaction failure, invalid PERSIST, or a
changed unbooted inactive slot.

Run this standalone driver. It reads manifest IDs, uses separate output
directories, and writes a result/exception record per leg:

```bash
export UPDATE_BASE_BUNDLE UPDATE_NEXT_BUNDLE UPDATE_INSTALLER UPDATE_EVIDENCE
set -o pipefail
sudo -E env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:. python3 - <<'PYCODE' 2>&1 | tee "$UPDATE_EVIDENCE/ab-smoke.log"
import json, os, time, traceback, zipfile
from pathlib import Path
from tools.x8_qemu.lifecycle import LifecycleConfig
from tools.x8_qemu.product import ProductHarness
evidence = Path(os.environ["UPDATE_EVIDENCE"]); root = evidence / "vm"
root.mkdir(parents=True, exist_ok=False)
base = Path(os.environ["UPDATE_BASE_BUNDLE"]); nxt = Path(os.environ["UPDATE_NEXT_BUNDLE"])
installer = Path(os.environ["UPDATE_INSTALLER"])
def rid(path):
    with zipfile.ZipFile(path) as z: return json.loads(z.read("manifest.json"))["release_id"]
base_id, next_id = rid(base), rid(nxt)
if base_id == next_id: raise SystemExit(f"duplicate fixture IDs: {base_id}")
(evidence / "bundle-release-ids.json").write_text(json.dumps({"base": base_id, "next": next_id}, indent=2) + "\n")
def h(name, **kw):
    c = LifecycleConfig(output_dir=root / name, timeout_seconds=2400, memory_mib=1024, cpus=1, keep_image=True)
    return ProductHarness(c, **kw)
def run(name, action):
    out = root / name; out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        result = action()
    except Exception as exc:
        (out / "result.json").write_text(json.dumps({"ok": False, "error": repr(exc), "elapsed_seconds": time.monotonic() - started, "traceback": traceback.format_exc()}, indent=2) + "\n")
        raise
    result["driver_elapsed_seconds"] = time.monotonic() - started
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    if result.get("ok") is not True: raise SystemExit(f"{name} FAILED: {out / 'result.json'}")
    print(f"{name}: PASS ({out / 'result.json'})")
run("install", lambda: h("install", official_image=installer, release_bundle=base).run_product())
installed = root / "install/product/disposable-target.img"
run("first-boot", lambda: h("first-boot", release_bundle=base).run_first_boot_product(installed_image=installed, expected_release_id=base_id))
accepted_a = root / "first-boot/product/firstboot-clone.img"
run("healthy-update", lambda: h("healthy-update").run_boot_health_product(installed_image=accepted_a, release_bundle=nxt, expected_release_id_b=next_id))
PYCODE
```

Do not reuse or modify the harness images for later tests; each later leg gets
its own clone/output directory under the 10/23 and 10/24 procedures.

## 5. Record and continue

Record SHA/host, gates/test IDs, fixture IDs/hashes/sizes, each leg result,
logs and first failure; keep failed artifacts. Session 04 remains OPEN. GUI,
rollback/reverse, Parent 202/507/interruption/low-space, full-system, physical
and USB cases remain for the linked work orders.
