# Parent password runtime integration acceptance

**Date:** 2026-09-08  
**Purpose:** prove that the exact Parent client pinned into Greia uses the Greia Parent password for browser bootstrap, persists only a revocable per-device credential, and is the runtime actually installed in the image.  
**Evidence lanes:** SOURCE + IMAGE + REAL BROWSER + PHYSICAL DEVICE  
**Execution rule:** STOP ON THE FIRST FAILURE. Do not repair source inside the frozen attempt and do not replace a failed step with a later rerun.

This procedure supersedes the authentication/pairing-token instructions in `docs/testing/2026-09-02_PARENT_REAL_RUNTIME_FINAL_ACCEPTANCE.md`. That older procedure remains useful for its wider Parent hardware/system-control checks, but its old shared-token bootstrap steps are obsolete.

## 0. Fixed authorities

Greia repository:

```text
frozenpepper/Greia
branch: main
```

Accepted Parent client repository and revision:

```text
frozenpepper/Greia-Parent-App-Html
01301d285c6ba2a9a1f2948a9768b821d2536729
```

Greia must pin that exact Parent revision in:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

The browser flow under test is:

```text
Greia Parent password
  -> POST /api/v1/pairing/bootstrap with {password, device_name}
  -> fresh per-device credential
  -> Authorization: Bearer <device credential> on normal requests
```

The route name `pairing/bootstrap` is API-v1 vocabulary. It does not mean the retired shared `parent-pairing-token` is valid input.

## 1. Hard prohibitions

During this acceptance do not:

- use GitHub-hosted Actions;
- add `?demo=1`;
- use a localhost demo client as production evidence;
- read a hidden pairing token from the Greia filesystem;
- send `pairing_token`, `X-Pip-Token`, a token query parameter, or a legacy shared-token cookie;
- manually copy Parent files into `/usr/share/greia-parent-app`;
- edit the pin, manifest, vendor tree, image overlay, credential store or password digest during the frozen run;
- delete an existing Parent device credential merely to make a step easier;
- persist the Parent password in evidence;
- persist bearer credentials in evidence;
- weaken the Parent service sandbox;
- treat browser UI changes alone as proof of an API or hardware mutation.

If any prohibited action appears necessary, stop and report `INCOMPLETE` with the first failing invariant.

## 2. Prepare one evidence root

From the Greia repository root:

```bash
set -euo pipefail
EVIDENCE="$PWD/tmp/PARENT_PASSWORD_RUNTIME_2026-09-08"
rm -rf "$EVIDENCE"
mkdir -p "$EVIDENCE"/{source,parent,image,browser,physical}
```

The `rm -rf` above is allowed only for that exact project-local evidence directory.

Record source identity:

```bash
git status --short | tee "$EVIDENCE/source/greia-status.txt"
git rev-parse HEAD | tee "$EVIDENCE/source/greia-head.txt"
git rev-parse origin/main | tee "$EVIDENCE/source/greia-origin-main.txt"
git diff --check | tee "$EVIDENCE/source/greia-diff-check.txt"
```

Expected: no unexplained relevant local modifications and `HEAD == origin/main`. If not, stop unless the owner explicitly requested that exact local descendant.

Record the frozen Parent checkout identity from the separate Parent repository:

```bash
cd /ABSOLUTE/PATH/TO/Greia-Parent-App-Html
git status --short | tee "$EVIDENCE/parent/parent-status.txt"
git rev-parse HEAD | tee "$EVIDENCE/parent/parent-head.txt"
test "$(git rev-parse HEAD)" = "01301d285c6ba2a9a1f2948a9768b821d2536729"
```

If the checkout is not that exact Parent revision, stop. Do not silently test moving Parent `main`.

## 3. Parent source gate

Still in the frozen Parent checkout:

```bash
set -euo pipefail
for f in src/*.js tests/*.js tests/support/*.js tools/*.mjs; do
  node --check "$f"
done |& tee "$EVIDENCE/parent/node-check.log"

npm test |& tee "$EVIDENCE/parent/npm-test.log"

node tools/runtime_manifest.mjs \
  01301d285c6ba2a9a1f2948a9768b821d2536729 \
  "$EVIDENCE/parent/generated-runtime-manifest.json" \
  |& tee "$EVIDENCE/parent/runtime-manifest.log"
```

All commands must exit 0.

The generated runtime closure must contain only files reachable from `index.html`; missing local imports/assets or any remote runtime dependency must fail this gate.

## 4. Greia pin, manifest, vendor and image-overlay gate

Return to the Greia repository root and verify the frozen pin:

```bash
set -euo pipefail
grep -F 'revision = "01301d285c6ba2a9a1f2948a9768b821d2536729"' runtime/parent-app-client.toml
grep -F 'integration_state = "vendored-image-integrity-enforced"' runtime/parent-app-client.toml
```

Compare the Parent-generated manifest semantically with Greia's committed manifest:

```bash
python3 - "$EVIDENCE/parent/generated-runtime-manifest.json" runtime/parent-app-client.manifest.json <<'PY'
import json, sys
left = json.load(open(sys.argv[1], encoding='utf-8'))
right = json.load(open(sys.argv[2], encoding='utf-8'))
assert left == right, 'Parent-generated runtime manifest differs from Greia manifest'
print('PARENT_RUNTIME_MANIFEST_MATCH')
PY
```

First prove the canonical repin operation cannot independently drift the manifest, vendor and image-overlay copies:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_update_parent_client_pin.py' -v \
  |& tee "$EVIDENCE/source/test-update-parent-client-pin.log"
```

Then run the remaining focused Greia source gate:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_parent_app_staging.py' -v \
  |& tee "$EVIDENCE/source/test-parent-app-staging.log"

PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_parent_client_image_integration.py' -v \
  |& tee "$EVIDENCE/source/test-parent-client-image-integration.log"

PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_parent_password_auth.py' -v \
  |& tee "$EVIDENCE/source/test-parent-password-auth.log"

PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_parent_production_api.py' -v \
  |& tee "$EVIDENCE/source/test-parent-production-api.log"
```

All five focused commands must exit 0.

Verify both committed runtime copies against the same contract:

```bash
PYTHONPATH=src python3 -m greia_parent.parent_client_integrity \
  --root vendor/parent-app \
  --manifest runtime/parent-app-client.manifest.json \
  --pin runtime/parent-app-client.toml \
  | tee "$EVIDENCE/source/vendor-integrity.txt"

PYTHONPATH=src python3 -m greia_parent.parent_client_integrity \
  --root build/overlay/usr/share/greia-parent-app \
  --manifest runtime/parent-app-client.manifest.json \
  --pin runtime/parent-app-client.toml \
  | tee "$EVIDENCE/source/overlay-integrity.txt"
```

Expected from both:

```text
Greia Parent client integrity OK: 01301d285c6ba2a9a1f2948a9768b821d2536729
```

Then run the repository-wide source gate:

```bash
make verify |& tee "$EVIDENCE/source/make-verify.log"
```

If anything in sections 3 or 4 fails, stop. Do not build or deploy an image from failed source.

## 5. Build/image gate

Use the current sanctioned Greia image/build procedure from `SETUP.md`, `docs/agents/GREIA_AGENT_OPERATIONS.md`, and the active boot/install plan. Do not invent a disk or profile from memory.

For the selected accepted target profile, build the normal installer/image through the canonical builder. After the root filesystem is produced, verify the installed Parent payload before booting it:

```bash
PYTHONPATH=/opt/greia-os/src python3 -m greia_parent.parent_client_integrity \
  --root /usr/share/greia-parent-app \
  --manifest /opt/greia-os/runtime/parent-app-client.manifest.json \
  --pin /opt/greia-os/runtime/parent-app-client.toml
```

If the builder's inspection mechanism uses a mounted root rather than `/`, prepend the mounted root consistently to all four paths.

Record:

```text
exact Greia SHA
exact Parent revision
image/profile name
image SHA-256
integrity-verifier output
```

Do not manually replace the installed browser bundle after the build.

## 6. Fresh/default-password browser bootstrap

This lane requires either a genuinely fresh Greia credential state or an owner-approved disposable test installation. Do not destroy a parent's live credential state merely to manufacture freshness.

From a second real browser device on the same LAN, open:

```text
http://<GREIA-IP>:8766/
```

Expected unpaired state:

- the page asks for the **Greia password**;
- it explains that new Greia systems start with `greia`;
- there is no pairing-token field;
- there is no instruction to retrieve a hidden token from the machine.

Enter:

```text
greia
```

Expected:

- bootstrap succeeds;
- the normal Parent application loads real Greia state;
- DevTools Network shows `POST /api/v1/pairing/bootstrap` with JSON field `password`, not `pairing_token`;
- the password itself is not stored in browser localStorage/sessionStorage;
- one device credential exists under the `greia.parent.v1.credential:` storage prefix.

Capture screenshots/network metadata without storing the password or bearer credential.

## 7. Reload/reconnect persistence

Close the Parent tab completely, reopen the same production URL, and refresh once.

Expected:

- the Parent app reconnects without asking for the Greia password;
- authenticated API calls use the existing per-device bearer credential;
- no new device is created merely because the page reloaded.

Record the visible device count before/after without recording secrets.

## 8. Password-change behavior

From the authenticated Parent UI, change the Parent password from:

```text
greia
```

to a temporary owner-chosen test password. Do not place that password in logs/evidence.

Immediately verify:

1. the already-paired browser remains authenticated by its per-device credential;
2. a separate unpaired/private browser fails bootstrap with old password `greia`;
3. that separate browser succeeds with the new password;
4. no shared household bearer token appears in browser or filesystem workflow.

If the already-paired browser is intentionally invalidated by current product policy, record that as a product-contract mismatch and stop; do not reinterpret it during the run.

## 9. Independent device revocation

In the Parent device-management view identify the first browser device and revoke it.

Expected:

- the revoked browser loses authenticated API access;
- another independently paired browser remains authenticated;
- refreshing the revoked browser does not restore access from the old credential;
- the revoked browser can bootstrap again only by entering the **current** Parent password;
- rebootstrap creates a fresh device credential, not resurrection of the revoked credential.

Do not inspect raw verifier material to prove this. Use the public Parent device/API behavior.

## 10. Retired shared-token negative proof

On the Greia machine/image, prove the obsolete production state/helper is absent or not recreated:

```bash
test ! -e /var/lib/greia-parent/parent-pairing-token
```

Use the actual installed Parent state directory if the image profile configures a different documented path.

Also confirm the installed runtime has no token-entry UI by searching only the installed static client text for the retired request vocabulary:

```bash
! grep -R -n --fixed-string 'pairing_token' /usr/share/greia-parent-app
! grep -R -n --fixed-string 'Pairing token' /usr/share/greia-parent-app
```

Do not treat the API route word `pairing` by itself as a failure.

## 11. Restore owner password/state

If this was not a disposable installation, restore the owner's desired Parent password through the normal Parent UI before ending the session. Never edit the password digest file directly.

If temporary Parent devices were created, revoke only those clearly created by this test. Do not revoke unrelated real devices.

Record only that restoration completed; do not record the password.

## 12. Wider Parent hardware checks

If sections 1–11 pass, continue the still-valid hardware/system-control portions of:

```text
docs/testing/2026-09-02_PARENT_REAL_RUNTIME_FINAL_ACCEPTANCE.md
```

Skip its obsolete shared-token bootstrap instructions. In particular, retain its requirement that browser volume/mute or other device mutations are proven against actual machine state, not merely against HTTP 200 or UI state.

## 13. Final report

Return one report containing:

```text
GREIA_SHA=<exact tested SHA>
PARENT_SHA=01301d285c6ba2a9a1f2948a9768b821d2536729
PARENT_SOURCE_GATE=PASS|FAIL
REPIn_TOOL_GATE=PASS|FAIL
GREIA_FOCUSED_GATE=PASS|FAIL
MAKE_VERIFY=PASS|FAIL
IMAGE_INTEGRITY=PASS|FAIL|NOT_RUN
DEFAULT_PASSWORD_BOOTSTRAP=PASS|FAIL|NOT_RUN
RELOAD_WITH_DEVICE_CREDENTIAL=PASS|FAIL|NOT_RUN
PASSWORD_CHANGE_OLD_REJECTED_NEW_ACCEPTED=PASS|FAIL|NOT_RUN
DEVICE_REVOCATION=PASS|FAIL|NOT_RUN
LEGACY_SHARED_TOKEN_ABSENT=PASS|FAIL|NOT_RUN
WIDER_PARENT_HARDWARE_GATE=PASS|FAIL|NOT_RUN
FIRST_FAILURE=<none or exact first invariant>
EVIDENCE_ROOT=<path>
```

Do not report PASS for an evidence lane that did not execute.
