# Session 03 — Linux owner-release build acceptance

**Date:** 2026-09-21  
**Scope:** one real Session 03 owner-command release build using the current Acer-only release matrix.  
**Purpose:** close Session 03 by proving that the owner-facing CLI can produce the complete current Greia release bundle on a supported x86_64 Linux build host without low-level parameter archaeology.

This is **not** the universal Setup-image acceptance. Session 03 intentionally has only the real acer-aspire-one-i386-ab release profile in the matrix. The universal greia-setup-<version>.img.xz is a Session 08 output after amd64 and ARM/Pi boot paths are real.

## 1. Host boundary

Run this only on an owner-approved **x86_64 Linux build host** with root/sudo access, adequate disposable disk space, and the network/repository access required by the existing composer.

Do **not** run this acceptance on the owner's macOS workstation.

Permitted because they are part of the production owner build path:

- debootstrap and chroot execution;
- exact bind mounts and teardown owned by Greia's build scripts;
- ext4 image creation/shrink/check operations;
- package download/cache use;
- zstd compression.

Not permitted:

- write-media;
- writing any physical disk, USB drive, SD card, or other block device;
- manual mount, umount, losetup, recursive unmounts, or ad-hoc cleanup outside the Greia-owned build path;
- QEMU, Docker, or physical Acer installation/boot;
- source edits during the frozen acceptance;
- git reset --hard, stash, clean, or deletion of unknown work;
- clearing Greia's persistent apt/pool caches.

If the build fails, preserve the first failure and the scratch directory reported by greia_release.py. Do not patch source and continue the same acceptance.

## 2. Freeze the exact source

From the repository root:

~~~bash
git pull --ff-only
git status --short
git rev-parse HEAD
git log --oneline -5
cat VERSION
uname -a
python3 --version
~~~

Required: current main, clean tree, and the full HEAD recorded as SOURCE_HEAD. Do not pull again during the run.

Prepare a project-local ignored evidence root:

~~~bash
SOURCE_HEAD="$(git rev-parse HEAD)"
VERSION="$(cat VERSION)"
EVIDENCE="./tmp/session03-linux-release-$SOURCE_HEAD"
OUT="$EVIDENCE/out"

mkdir -p "$EVIDENCE"
printf '%s\n' "$SOURCE_HEAD" > "$EVIDENCE/source-head.txt"
printf '%s\n' "$VERSION" > "$EVIDENCE/version.txt"
~~~

## 3. Pre-build source validation

The first Linux owner-build attempt exposed a real shared-composer defect and
the composer has since changed. Therefore the repaired checkout requires a
fresh source gate before another privileged build attempt. Do not reuse a
PASS from the pre-repair SHA.

Run:

~~~bash
set -o pipefail

bash -n build/lib/compose.sh build/build-installer-image.sh

PYTHONPATH=src:tools python3 -m unittest discover \
  -s tests \
  -p 'test_greia_release.py' \
  -v 2>&1 | tee "$EVIDENCE/test_greia_release.log"

PYTHONPATH=src:tools python3 -m unittest discover \
  -s tests \
  -p 'test_system_overlay_contract.py' \
  -v 2>&1 | tee "$EVIDENCE/test_system_overlay_contract.log"

git diff --check

make verify 2>&1 | tee "$EVIDENCE/make-verify.log"

git status --short
~~~

Expected:

- shell syntax PASS;
- release CLI suite PASS (11 tests at the time this procedure was updated);
- system-overlay contract suite PASS;
- `git diff --check` exit 0;
- `make verify` exit 0 with no FAIL/ERROR;
- tree remains clean.

If any check fails, STOP before the privileged build. After a subsequent
source/build-script repair, this full source gate becomes required again for
the new SHA; documentation-only commits do not invalidate a source PASS.

## 4. Run the owner-facing doctor

~~~bash
set -o pipefail

sudo python3 tools/greia_release.py doctor \
  --output "$OUT" \
  2>&1 | tee "$EVIDENCE/doctor.json"
~~~

Expected: exit 0, JSON ok=true, Linux/x86_64/root/tool/profile/workspace checks green, and the current matrix resolves acer-aspire-one-i386-ab.

If doctor fails, STOP and return its complete output. Do not install packages or alter host configuration unless the owner separately authorizes that change.

## 5. Build through the single owner command

This is the acceptance-defining action:

~~~bash
set -o pipefail

sudo python3 tools/greia_release.py build \
  --version "$VERSION" \
  --output "$OUT" \
  2>&1 | tee "$EVIDENCE/owner-build-result.json"
~~~

Do not replace this with calls to compose-release-profile.sh, build_release.py, or greia_update.py build. Those are implementation details; this acceptance proves the owner command.

Expected final directory:

~~~text
$OUT/greia-$VERSION/
  release-report.json
  updates/
    acer-aspire-one-i386-ab.greiaupdate
  intermediate/
    acer-aspire-one-i386-ab/
      payload.ext4.zst
      payload-receipt.json
      hardware-support.tar.zst
      build.log
~~~

The universal Setup image is expected to be reported as deferred and must not be fabricated in Session 03.

On build failure: STOP, preserve the evidence directory and the .greia-work scratch directory named in the error, and return the first failure, exit code, build log, and preserved-work path. Do not modify source or manually clean mounts and then continue the same acceptance.

## 6. Inspect the produced release

After a successful build:

~~~bash
RELEASE="$OUT/greia-$VERSION"
REPORT="$RELEASE/release-report.json"
BUNDLE="$RELEASE/updates/acer-aspire-one-i386-ab.greiaupdate"

python3 tools/greia_release.py inspect "$REPORT" \
  | tee "$EVIDENCE/inspect-report.json"

python3 tools/greia_release.py inspect "$BUNDLE" \
  | tee "$EVIDENCE/inspect-bundle.json"
~~~

Both commands must exit 0.

Then run this read-only consistency check:

~~~bash
python3 - "$SOURCE_HEAD" "$RELEASE" <<'PY' \
  | tee "$EVIDENCE/release-consistency.txt"
import hashlib
import json
import pathlib
import sys

source_head = sys.argv[1]
root = pathlib.Path(sys.argv[2]).resolve()
report = json.loads((root / "release-report.json").read_text(encoding="utf-8"))

assert report["schema_version"] == 1
assert report["status"] == "complete"
assert report["source_commit"] == source_head
assert report["public_artifacts"] == [
    "updates/acer-aspire-one-i386-ab.greiaupdate"
]
assert report["setup_image"]["status"] == "deferred"
assert report["setup_image"]["session"] == 8
assert len(report["profiles"]) == 1

profile = report["profiles"][0]
assert profile["profile_id"] == "acer-aspire-one-i386-ab"

required = [
    root / "updates" / "acer-aspire-one-i386-ab.greiaupdate",
    root / "intermediate" / "acer-aspire-one-i386-ab" / "payload.ext4.zst",
    root / "intermediate" / "acer-aspire-one-i386-ab" / "payload-receipt.json",
    root / "intermediate" / "acer-aspire-one-i386-ab" / "hardware-support.tar.zst",
    root / "intermediate" / "acer-aspire-one-i386-ab" / "build.log",
]
for path in required:
    assert path.is_file(), path
    assert path.stat().st_size > 0, path

assert ".greia-work" not in json.dumps(report, sort_keys=True)

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

for section in ("payload", "hardware_support", "bundle"):
    info = profile[section]
    artifact = root / info["path"]
    assert artifact.is_file(), artifact
    assert digest(artifact) == info["sha256"], (section, artifact)

print("PASS")
print(f"source_commit={report['source_commit']}")
print(f"bundle={profile['bundle']['path']}")
print(f"bundle_bytes={profile['bundle']['bytes']}")
print(f"payload_compressed_bytes={profile['payload']['compressed_bytes']}")
print(f"hardware_support_compressed_bytes={profile['hardware_support']['compressed_bytes']}")
print(f"updates_total_bytes={report['media_accounting']['updates_total_bytes']}")
print(f"intermediate_total_bytes={report['media_accounting']['intermediate_total_bytes']}")
PY
~~~

Expected first output line: PASS.

## 7. Confirm cleanup and source integrity

~~~bash
find "$OUT/.greia-work" -mindepth 1 -maxdepth 1 -print \
  | tee "$EVIDENCE/remaining-work-entries.txt"

findmnt -rn -o TARGET \
  | grep -F "$(realpath "$OUT/.greia-work")" \
  > "$EVIDENCE/remaining-build-mounts.txt" || true

git status --short
git rev-parse HEAD
~~~

Required:

- remaining-work-entries.txt is empty after success;
- remaining-build-mounts.txt is empty;
- working tree remains clean;
- final HEAD equals SOURCE_HEAD.

If a build mount remains, classify acceptance FAIL/INCOMPLETE and report it. Do not use recursive unmount as a workaround.

## 8. Evidence to return

~~~text
SESSION 03 LINUX OWNER RELEASE BUILD

SOURCE_HEAD:
<full sha>

VERSION:
<version>

HOST:
<uname -a>

TREE CLEAN BEFORE:
yes/no

FOCUSED RELEASE CLI TEST:
PASS/FAIL
<count>

DOCTOR:
PASS/FAIL
<failed checks if any>

OWNER BUILD:
PASS/FAIL
<exit code>

RELEASE ROOT:
<path>

PUBLIC ARTIFACTS:
<from release report>

BUNDLE:
<path>
<bytes>
<sha256>

PAYLOAD:
<compressed bytes>
<producer uncompressed bytes>
<producer minimum slot bytes>
<sha256>

HARDWARE SUPPORT:
<compressed bytes>
<relevant producer size facts>
<sha256>

MEDIA ACCOUNTING:
<updates total bytes>
<intermediate total bytes>

SETUP IMAGE:
deferred/session 8  (expected)

INSPECT REPORT:
PASS/FAIL

INSPECT BUNDLE:
PASS/FAIL

CONSISTENCY CHECK:
PASS/FAIL

TRANSIENT WORK CLEANED:
yes/no

LEFTOVER BUILD MOUNTS:
none/<paths>

TREE CLEAN AFTER:
yes/no

PROHIBITED ACTIONS RUN:
no

FAILURE DETAILS:
<first failure only, if any>
~~~

## 9. Session 03 verdict

Session 03 is COMPLETE only if:

1. source validation is green;
2. this exact owner-command build succeeds on the supported Linux host;
3. the release report is complete and source-bound;
4. the profile-specific update bundle and compact intermediates exist and inspect cleanly;
5. transient work/mounts are cleaned after success;
6. no manual low-level parameter plumbing was required.

A green Session 03 does not claim that a universal installer exists. It proves the release owner/orchestration layer with the current Acer-only matrix.

After this passes, Session 04 opens and consumes this real bundle to prove the legacy i386 lifecycle:

~~~text
fresh install
-> first healthy boot
-> update
-> commit
-> failed candidate
-> previous accepted release
~~~
