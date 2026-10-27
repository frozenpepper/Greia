# A/B candidate-only healthy-update retry

> **HISTORICAL CANDIDATE RETRY (superseded 2026-10-27):** The previous frozen-image attempt has been diagnosed. Do not run its old-source/hash gates as prerequisites. For implementation and current-source Linux/QEMU testing use [GREIA_UPDATE_RELEASE_ACCEPTANCE.md](GREIA_UPDATE_RELEASE_ACCEPTANCE.md); preserve this file for prior evidence and tool examples.

Date: 2026-10-26 · Status: **HISTORICAL — superseded by installed-updater simplification**

**Do not execute this artifact-reuse procedure for the current change.** The
production updater now discovers the package directly; old images do not
contain that fix. Use [the clean build/install/healthy-update procedure](2026-10-25_AB_SMOKE_RETRY.md).
The remaining text preserves the preceding harness-only retry instructions.
Session 04 remains OPEN.

This retries only healthy A-to-B from the [October 26 evidence report](../reviews/2026-10-26_AB_SMOKE_RETRY_EVIDENCE.md), reusing its clean bundles and accepted-A clone instead of repeating the long install/first boot. Reuse is conditional on every artifact, hash, source-path, first-boot and focused-test check below. Any failed/missing check means stop and use the [clean three-leg route](2026-10-25_AB_SMOKE_RETRY.md). Never repair or diagnose the old guest manually.

## 1. Freeze current harness source

Run on the capable x86_64 Linux build host from clean committed `main`. No Mac image build/mount/QEMU, hosted Actions, physical device or host `/dev` target. The old artifacts came from `866ba68277be8500db62de55a9189d78c9ea704b`; require it as an ancestor and allow only harness/tests/docs/skills/HANDOVER changes since then. Any other changed path invalidates reuse.

```bash
set -euo pipefail
test "$(git branch --show-current)" = main
test -z "$(git status --porcelain)"
export OLD_SOURCE=866ba68277be8500db62de55a9189d78c9ea704b
export SOURCE_HEAD="$(git rev-parse HEAD)" RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
git merge-base --is-ancestor "$OLD_SOURCE" "$SOURCE_HEAD"
git diff --name-only "$OLD_SOURCE..$SOURCE_HEAD" > /tmp/greia-ab-retry-changed-paths.txt
if grep -Ev '^(tools/x8_qemu/|tests/|docs/|skills/|HANDOVER\.md$)' /tmp/greia-ab-retry-changed-paths.txt; then
  echo "Changed path is outside reuse allowlist; use clean three-leg route." >&2; exit 1
fi
export UPDATE_EVIDENCE="/var/tmp/greia-ab-candidate-$SOURCE_HEAD-$RUN_ID"
mkdir -m 0700 "$UPDATE_EVIDENCE"
git rev-parse HEAD > "$UPDATE_EVIDENCE/source-head.txt"
cp /tmp/greia-ab-retry-changed-paths.txt "$UPDATE_EVIDENCE/changed-paths-since-866.txt"
uname -a > "$UPDATE_EVIDENCE/host.txt"
python3 --version >> "$UPDATE_EVIDENCE/host.txt"
qemu-system-i386 --version >> "$UPDATE_EVIDENCE/host.txt"
qemu-img --version >> "$UPDATE_EVIDENCE/host.txt"
```

This proves shipped/producer/runtime inputs unchanged; focused tests validate the harness.

## 2. Run focused harness source suites

Run current source selectors before VM boot (expected 168 tests); record count
and log. Any failure or selector/count drift stops. Full gate remains NOT GREEN
(latest: 5,959 tests, 7 failures, 3 errors, 3 skips); this retry does not rerun
or waive it.

```bash
set +e; set -o pipefail
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/run_tests.py \
  test_x8_qemu.test_product test_x8_qemu.test_product_install \
  test_x8_qemu.test_product_boot_health test_x8_qemu.test_session04_legs \
  test_x8_qemu.test_product_boot_health_identity -v \
  2>&1 | tee "$UPDATE_EVIDENCE/focused-source.log"
FOCUSED_PIPE_STATUS=("${PIPESTATUS[@]}"); FOCUSED_STATUS="${FOCUSED_PIPE_STATUS[0]}"
FOCUSED_TEE_STATUS="${FOCUSED_PIPE_STATUS[1]}"
set -e
printf '%s\n' "$FOCUSED_STATUS" > "$UPDATE_EVIDENCE/focused-source.exit"
printf '%s\n' "$FOCUSED_TEE_STATUS" > "$UPDATE_EVIDENCE/focused-source-tee.exit"
if (( FOCUSED_STATUS != 0 || FOCUSED_TEE_STATUS != 0 )); then
  echo "Focused harness source gate failed; stop before VM boot." >&2; exit 1
fi
```

## 3. Require and verify prior Linux artifacts

All files must still exist under
`/var/tmp/greia-ab-smoke-866ba68277be8500db62de55a9189d78c9ea704b-20261025T162521Z`.
Require the prior QEMU processes to have exited and the selected images to be offline. Never clone a running guest.
If pruned/missing, hash-mismatched, refused by inspection, or first-boot checks
fail, stop and use the clean route. Never reconstruct or guess an image.

```bash
export OLD_EVIDENCE=/var/tmp/greia-ab-smoke-866ba68277be8500db62de55a9189d78c9ea704b-20261025T162521Z
export UPDATE_BASE_BUNDLE="$OLD_EVIDENCE/base-fixture/greia-acceptance-fixture-0.13.0-phase0-dev/updates/acer-aspire-one-i386-ab.greiaupdate"
export UPDATE_NEXT_BUNDLE="$OLD_EVIDENCE/next-fixture/greia-acceptance-fixture-0.13.1-phase0-dev/updates/acer-aspire-one-i386-ab.greiaupdate"
export ACCEPTED_A="$OLD_EVIDENCE/vm/first-boot/product/firstboot-clone.img"
export FIRST_BOOT_RESULT="$OLD_EVIDENCE/vm/first-boot/result.json"
test -s "$UPDATE_BASE_BUNDLE" && test -s "$UPDATE_NEXT_BUNDLE" && test -s "$ACCEPTED_A" && test -s "$FIRST_BOOT_RESULT"
test ! -L "$UPDATE_BASE_BUNDLE" && test ! -L "$UPDATE_NEXT_BUNDLE" && test ! -L "$ACCEPTED_A" && test ! -L "$FIRST_BOOT_RESULT"
printf '%s  %s\n' 93f55468230ce4e2b63d4665b3e1f826ae384c47b918674fe5c432a2f3c29a17 "$UPDATE_BASE_BUNDLE" | sha256sum -c -
printf '%s  %s\n' 76ef1ffe2795124f06f73ec81306313101129b7e23f74de38d5fbd7926a6fee9 "$UPDATE_NEXT_BUNDLE" | sha256sum -c -
python3 tools/greia_update.py inspect "$UPDATE_BASE_BUNDLE" > "$UPDATE_EVIDENCE/base-inspect.json"
python3 tools/greia_update.py inspect "$UPDATE_NEXT_BUNDLE" > "$UPDATE_EVIDENCE/next-inspect.json"
```

Validate the old first-boot result against the base bundle manifest and current
helper shape: accepted/default/committed A, accepted journal, schema-1 PERSIST
with observed identity, untouched B, and no input-image mutation. No prior
authoritative whole-image SHA for accepted A was published; this run records a
new pre/post SHA and requires equality.

```bash
python3 - "$FIRST_BOOT_RESULT" "$UPDATE_BASE_BUNDLE" "$OLD_EVIDENCE/vm/install/product/disposable-target.img" "$ACCEPTED_A" <<'PYCODE'
import hashlib, json, sys, zipfile
from pathlib import Path
result_path, bundle, installed, accepted = map(Path, sys.argv[1:])
r = json.loads(result_path.read_text())
with zipfile.ZipFile(bundle) as z: base_id = json.loads(z.read("manifest.json"))["release_id"]
def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()
assert r.get("ok") is True and r.get("leg") == "first-boot-product", r
assert r.get("source_image_mutated") is False, r
assert Path(r["installed_image"]).resolve() == installed.resolve() and r["installed_image_sha256"] == sha(installed), r
assert r["release_bundle_sha256"] == sha(bundle), r
o = r["observed"]
assert o["default_slot"] == o["committed_slot"] == "A" and o["accepted_release_id"] == base_id, o
assert o["journal_state"] == "accepted" and o["inspection"]["persist_schema_version"] == 1, o
p = o["observed_identities"]["persist"]
assert p["partuuid"] and p["filesystem_uuid"], p
assert r["slot_hash_evidence"]["booted_slots"] == ["A"] and r["slot_hash_evidence"]["inactive_unchanged"] is True, r
assert accepted.is_file()
print(json.dumps({"base_release_id": base_id, "accepted_A_bytes": accepted.stat().st_size}, indent=2))
PYCODE
sha256sum "$ACCEPTED_A" | tee "$UPDATE_EVIDENCE/accepted-A-before.sha256"
```

The candidate-only leg is now eligible. The runner reads both bundle release
IDs from their manifests; never infer identities from filenames.

## 4. Run only healthy A-to-B

`run_boot_health_product` clones accepted A, receives the candidate through
`SystemUpdateInbox.receive`, projects canonical guest `status.json`, preserves
ownership/fsync, then verifies shipped status/verify/stage/arm and B health via
production parsers. Refusal/missing candidate is a failure; the current serial
marker fails promptly. Do not repair the guest; output stays separate from A.

```bash
export UPDATE_BASE_BUNDLE UPDATE_NEXT_BUNDLE ACCEPTED_A UPDATE_EVIDENCE
set +e; set -o pipefail
sudo -E env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:. python3 - <<'PYCODE' 2>&1 | tee "$UPDATE_EVIDENCE/healthy-a-to-b.log"
import hashlib, json, os, time, traceback, zipfile
from pathlib import Path
from tools.x8_qemu.lifecycle import LifecycleConfig
from tools.x8_qemu.product import ProductHarness
e = Path(os.environ["UPDATE_EVIDENCE"]); origin = Path(os.environ["ACCEPTED_A"])
base = Path(os.environ["UPDATE_BASE_BUNDLE"]); bundle = Path(os.environ["UPDATE_NEXT_BUNDLE"])
out = e / "healthy-a-to-b"
if not origin.is_file() or not bundle.is_file() or out.exists(): raise SystemExit("input missing or output already exists")
def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()
with zipfile.ZipFile(base) as z: base_id = json.loads(z.read("manifest.json"))["release_id"]
with zipfile.ZipFile(bundle) as z: release_id = json.loads(z.read("manifest.json"))["release_id"]
if base_id == release_id: raise SystemExit(f"fixture IDs are equal: {base_id}")
(e / "bundle-release-ids.json").write_text(json.dumps({"base": base_id, "next": release_id}, indent=2)+"\n")
before = sha(origin); (e / "accepted-A-run-before.sha256").write_text(f"{before}  {origin}\n")
result_path = out / "result.json"; started = time.monotonic()
try:
    harness = ProductHarness(LifecycleConfig(output_dir=out, timeout_seconds=2400,
        memory_mib=1024, cpus=1, keep_image=True), release_bundle=bundle)
    result = harness.run_boot_health_product(installed_image=origin,
        release_bundle=bundle, expected_release_id_b=release_id)
    observed = result["observed"]
    assert observed["default_slot"] == observed["committed_slot"] == "B", observed
    assert observed["accepted_release_id"] == release_id, observed
    assert observed["journal_state"] == "accepted", observed
    assert observed["inspection"]["persist_schema_version"] == 1, observed
except Exception as exc:
    after = sha(origin); out.mkdir(parents=True, exist_ok=True)
    (e / "accepted-A-run-after.sha256").write_text(f"{after}  {origin}\n")
    result_path.write_text(json.dumps({"ok": False, "error": repr(exc),
        "traceback": traceback.format_exc(), "elapsed_seconds": time.monotonic()-started,
        "origin_sha256_before": before, "origin_sha256_after": after}, indent=2)+"\n")
    raise
after = sha(origin)
(e / "accepted-A-run-after.sha256").write_text(f"{after}  {origin}\n")
result.update(driver_elapsed_seconds=time.monotonic()-started,
              origin_sha256_before=before, origin_sha256_after=after)
if after != before or result.get("installed_image_sha256") != before:
    result.update(ok=False, driver_error="accepted-A input changed/hash mismatch")
result_path.parent.mkdir(parents=True, exist_ok=True)
result_path.write_text(json.dumps(result, indent=2)+"\n")
if result.get("ok") is not True: raise SystemExit(f"healthy A-to-B FAILED; inspect {result_path}")
print(f"healthy A-to-B: PASS; release_id={release_id}; result={result_path}")
PYCODE
SMOKE_PIPE_STATUS=("${PIPESTATUS[@]}"); SMOKE_STATUS="${SMOKE_PIPE_STATUS[0]}"
SMOKE_TEE_STATUS="${SMOKE_PIPE_STATUS[1]}"
set -e
printf '%s\n' "$SMOKE_STATUS" > "$UPDATE_EVIDENCE/healthy-a-to-b.exit"
printf '%s\n' "$SMOKE_TEE_STATUS" > "$UPDATE_EVIDENCE/healthy-a-to-b-tee.exit"
if (( SMOKE_STATUS != 0 || SMOKE_TEE_STATUS != 0 )); then exit 1; fi
```

Record the command exit status, log, result JSON, accepted-A before/after SHA,
and current source SHA. On refusal, preserve FAIL/BLOCKED and inspect harness
serial/result artifacts only. Do not run the full failure matrix before this
healthy-B result is resolved.

## 5. Evidence boundary

Healthy A-to-B closes only if result is `ok: true`, observed/default/accepted slot B and next manifest ID match, PERSIST validates, and A's SHA is unchanged.
GUI, rollback/reverse, Parent/fault, full-system, physical and USB remain open; Session 04 stays OPEN. Return the outcome to HANDOVER owner.
