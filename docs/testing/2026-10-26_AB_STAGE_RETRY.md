# A/B healthy-update retry after harness fixes

Date: 2026-10-26 · Status: **UNPROVEN; Linux VM retry; Session 04 OPEN**

This retries only healthy A-to-B from the [current-source evidence report](../reviews/2026-10-26_AB_SMOKE_CLEAN_SOURCE_RERUN_EVIDENCE.md), reusing its clean bundles and accepted-A clone instead of repeating the long install/first boot. Reuse is conditional on every artifact, hash, source-path, first-boot and focused-test check below. A failed preflight stops this attempt; it does not authorize another image
build. Fix host/harness problems before running a VM. Rebuild via the
[clean route](2026-10-25_AB_SMOKE_RETRY.md) only when shipped/build inputs
changed or the required artifacts are actually missing/corrupt. Preserve the
working artifacts. Never repair guest state manually.

## Work order: one retry, no rebuild loop

1. Run the cheap source preflight below before any build or VM work. It runs
   generated STAGE/ARM code against fake sockets and exercises teardown failure
   paths; the author and independent reviewer already ran it successfully.
2. Verify/reuse the recorded images. A missing tool, attached loop, timeout,
   failed test or report-schema mismatch is a host/harness diagnosis, not a
   reason to rebuild the OS. Record and fix that cause against the same inputs.
3. Run only healthy A-to-B on a new clone. Preserve the input image and all
   previous build outputs. On success or failure, commit the result and stop
   this work order; do not launch install, rebuild, fault or rollback matrices.

Record whether a failure occurred in host setup, test control, or the installed
updater, with the first concrete error. The agent should diagnose the relevant
layer before sending a parent/operator through another long attempt.

## 1. Freeze current harness source

Run on the capable x86_64 Linux build host from clean committed `main`. No Mac image build/mount/QEMU, hosted Actions, physical device or host `/dev` target. The old artifacts came from `1275e0be1a9e0cda724ce18151ae65a25f03c98c`; require it as an ancestor and allow only harness/tests/docs/skills/HANDOVER changes since then. Any other changed path invalidates reuse.

```bash
set -euo pipefail
test "$(git branch --show-current)" = main
git pull --ff-only
test -z "$(git status --porcelain)"
export OLD_SOURCE=1275e0be1a9e0cda724ce18151ae65a25f03c98c
export SOURCE_HEAD="$(git rev-parse HEAD)" RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
git merge-base --is-ancestor "$OLD_SOURCE" "$SOURCE_HEAD"
git diff --name-only "$OLD_SOURCE..$SOURCE_HEAD" > /tmp/greia-ab-retry-changed-paths.txt
if grep -Ev '^(tools/x8_qemu/|tests/|docs/|skills/|HANDOVER\.md$)' /tmp/greia-ab-retry-changed-paths.txt; then
  echo "Changed path is outside reuse allowlist; use clean three-leg route." >&2; exit 1
fi
export UPDATE_EVIDENCE="/var/tmp/greia-ab-stage-$SOURCE_HEAD-$RUN_ID"
mkdir -m 0700 "$UPDATE_EVIDENCE"
git rev-parse HEAD > "$UPDATE_EVIDENCE/source-head.txt"
cp /tmp/greia-ab-retry-changed-paths.txt "$UPDATE_EVIDENCE/changed-paths-since-1275.txt"
uname -a > "$UPDATE_EVIDENCE/host.txt"
python3 --version >> "$UPDATE_EVIDENCE/host.txt"
qemu-system-i386 --version >> "$UPDATE_EVIDENCE/host.txt"
qemu-img --version >> "$UPDATE_EVIDENCE/host.txt"
df -h "$UPDATE_EVIDENCE" > "$UPDATE_EVIDENCE/free-space.txt"
```

This checks shipped/producer/runtime source paths are unchanged; focused tests
validate the harness. The old report's requirement to rebuild for a harness-only
change is superseded by these explicit reuse checks. If any production/build
input changed, use the clean route. Never reuse the failed healthy-update clone.

## 2. Run focused harness source suites

Run current source selectors before VM boot; record their count and log. Any
failure stops. Full gate remains NOT GREEN (latest Linux: 5,961 tests, 6
failures, 3 errors, 3 skips); this bounded harness retry does not rerun or waive it.

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
`/var/tmp/greia-ab-smoke-1275e0be1a9e0cda724ce18151ae65a25f03c98c-20261026T014350Z`.
Require the selected images to be offline and unused by any process. The
bounded `fuser` check below records that precondition. Never clone a running guest. Keep disk use below the clean guide's
80% threshold; stop if the host lacks room for a fresh disposable clone.
Before and after this one leg, save loop associations. Any association under
the old/current evidence roots stops acceptance; do not detach unrelated loops.
If cleanup is needed, use the repository's `safe_detach_loop` with the exact
owned device after checking its backing image, and preserve that intervention
as a cleanup failure rather than reporting an unattended PASS.
If files are missing or hashes/inspection show corrupt artifacts, stop and
record why a rebuild is needed. A first-boot JSON/host preflight failure needs
inspection of that check before concluding the image is unusable. Never
reconstruct, delete or guess an image merely to make a check pass.

```bash
export OLD_EVIDENCE=/var/tmp/greia-ab-smoke-1275e0be1a9e0cda724ce18151ae65a25f03c98c-20261026T014350Z
export UPDATE_BASE_BUNDLE="$OLD_EVIDENCE/base-fixture/greia-acceptance-fixture-0.13.0-phase0-dev/updates/acer-aspire-one-i386-ab.greiaupdate"
export UPDATE_NEXT_BUNDLE="$OLD_EVIDENCE/next-fixture/greia-acceptance-fixture-0.13.1-phase0-dev/updates/acer-aspire-one-i386-ab.greiaupdate"
export ACCEPTED_A="$OLD_EVIDENCE/vm/first-boot/product/firstboot-clone.img"
export FIRST_BOOT_RESULT="$OLD_EVIDENCE/vm/first-boot/result.json"
test -s "$UPDATE_BASE_BUNDLE" && test -s "$UPDATE_NEXT_BUNDLE" && test -s "$ACCEPTED_A" && test -s "$FIRST_BOOT_RESULT"
test -s "$OLD_EVIDENCE/vm/install/product/disposable-target.img"
command -v fuser >/dev/null
if sudo timeout 10 fuser -v -- "$ACCEPTED_A" "$OLD_EVIDENCE/vm/install/product/disposable-target.img" > "$UPDATE_EVIDENCE/image-holders.txt" 2>&1; then
  echo "Selected image is in use; stop before cloning." >&2; exit 1
else
  HOLDER_STATUS=$?
  printf '%s\n' "$HOLDER_STATUS" > "$UPDATE_EVIDENCE/image-holders.exit"
  if (( HOLDER_STATUS != 1 )); then
    echo "Image-holder check failed or timed out; stop." >&2; exit 1
  fi
fi
sudo losetup --list --noheadings --output NAME,BACK-FILE > "$UPDATE_EVIDENCE/loops.before.txt"
if grep -F "$OLD_EVIDENCE/" "$UPDATE_EVIDENCE/loops.before.txt"; then
  echo "Old evidence still has attached loops; stop and preserve audit." >&2; exit 1
fi
test ! -L "$UPDATE_BASE_BUNDLE" && test ! -L "$UPDATE_NEXT_BUNDLE" && test ! -L "$ACCEPTED_A" && test ! -L "$FIRST_BOOT_RESULT"
printf '%s  %s\n' b45f0fc77aaf04883442a74be742dc4e1fa888648a55e274b51b836a5b662a9b "$UPDATE_BASE_BUNDLE" | sha256sum -c -
printf '%s  %s\n' 3ae9cdeafa6e52459016e1a23315648ee4b8887a314c77c288259c1df4d68aa5 "$UPDATE_NEXT_BUNDLE" | sha256sum -c -
python3 tools/greia_update.py inspect "$UPDATE_BASE_BUNDLE" > "$UPDATE_EVIDENCE/base-inspect.json"
python3 tools/greia_update.py inspect "$UPDATE_NEXT_BUNDLE" > "$UPDATE_EVIDENCE/next-inspect.json"
```

Validate the old first-boot result against the base bundle manifest and current
helper shape: accepted/default/committed A, accepted journal, schema-1 PERSIST
with observed identity, untouched B, and no input-image mutation. The report publishes the accepted-A image SHA; require it below as well as
recording and comparing this run's pre/post SHA.

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
printf '%s  %s\n' 83d693d915d53e314906fc7e4b319257ba201855121aa1f529f0bf998bf7d1a2 "$ACCEPTED_A" | sha256sum -c -
sha256sum "$ACCEPTED_A" | tee "$UPDATE_EVIDENCE/accepted-A-before.sha256"
```

The healthy-update leg is now eligible. The runner reads both bundle release
IDs from their manifests; never infer identities from filenames.

## 4. Run only healthy A-to-B

`run_boot_health_product` clones accepted A, receives the candidate through
`SystemUpdateInbox.receive`, preserves ownership/fsync, then verifies shipped
status/verify/stage/arm and B health via
production parsers. The guest uses the shipped update client for status/verify/stage, including its
finite 1,800-second staging timeout. Root-only arm retains its bounded control
request; the host phase ceiling is 2,400 seconds. Refusal
is a failure; do not repair the guest. Output stays separate from accepted A.

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
sudo losetup --list --noheadings --output NAME,BACK-FILE > "$UPDATE_EVIDENCE/loops.after.txt"
LOOP_AUDIT_STATUS=0
if grep -F -e "$OLD_EVIDENCE/" -e "$UPDATE_EVIDENCE/" "$UPDATE_EVIDENCE/loops.after.txt"; then
  LOOP_AUDIT_STATUS=1
  echo "Owned evidence loop association remains; preserve FAIL and diagnostics." >&2
fi
printf '%s\n' "$LOOP_AUDIT_STATUS" > "$UPDATE_EVIDENCE/loop-audit.exit"
if (( SMOKE_STATUS != 0 || SMOKE_TEE_STATUS != 0 || LOOP_AUDIT_STATUS != 0 )); then exit 1; fi
```

Record the command exit status, log, result JSON, accepted-A before/after SHA,
and current source SHA. On refusal, preserve FAIL/BLOCKED and inspect harness
serial/result artifacts only. Stop this work order after this result. Do not automatically start another
build or the full failure matrix, including after a successful healthy-B run.

## 5. Evidence boundary

Healthy A-to-B closes only if the command/tee and `loop-audit.exit` all report
zero, result is `ok: true`, observed/default/accepted slot B and next manifest ID
match, PERSIST validates, and accepted A's SHA is unchanged. A result JSON alone
does not override a failed final cleanup audit.
GUI, rollback/reverse, Parent/fault, complete full-system acceptance, physical
and USB remain separate open release work. Session 04 stays OPEN. Return this
one-leg outcome to HANDOVER; those other requirements are not extra steps in
this work order.
