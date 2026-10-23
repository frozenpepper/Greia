# Greia Parent — Unified Authentication, Runtime, Browser and Physical Acceptance

**Date:** 2026-09-08  
**Status:** HISTORICAL FROZEN SEPTEMBER PARENT AUTHENTICATION BASELINE. For current self-signed HTTPS and exact current pinned client SHA use [2026-10-23 Parent HTTPS acceptance](2026-10-23_PARENT_HTTPS_ACCEPTANCE.md); do not execute this older HTTP/version-frozen procedure as current production acceptance.  
**Greia repository:** `frozenpepper/Greia` / `main`  
**Frozen Parent client repository:** `frozenpepper/Greia-Parent-App-Html`  
**Frozen Parent client revision:** `01301d285c6ba2a9a1f2948a9768b821d2536729`  
**Execution rule:** **STOP ON THE FIRST FAILURE.** Do not repair source, mutate evidence, weaken a check, or substitute a later rerun inside the same frozen attempt.

This document is the single unified procedure for closing the September 2026 Parent authentication/runtime integration tranche. It supersedes the authentication instructions in:

- `docs/testing/2026-09-08_PARENT_PASSWORD_RUNTIME_INTEGRATION_ACCEPTANCE.md`
- the obsolete shared-token authentication portions of `docs/testing/2026-09-02_PARENT_REAL_RUNTIME_FINAL_ACCEPTANCE.md`

The older documents remain historical evidence and may still contain subsystem-specific context, but they are not the authority for authentication sequencing after this file lands.

---

## 1. Contract under test

The production Parent flow is:

```text
LAN discovery
  -> browser opens Greia Parent service
  -> if no valid device credential exists, ask for Greia Parent password
  -> POST /api/v1/pairing/bootstrap
       {"password": "<Parent password>", "device_name": "<browser label>"}
  -> Greia verifies MainCredential locally
  -> Greia issues one fresh random per-device credential
  -> browser persists only that device credential
  -> normal API requests use Authorization: Bearer <device credential>
     or the API-v1 device cookie greia_parent_device
  -> Parent devices can be revoked independently
```

Fresh systems start with:

```text
username: greia
password: greia
```

The wire names `/pairing/bootstrap` and `pairing_required` are retained API-v1 vocabulary. They do **not** mean the retired shared pairing-token model remains valid.

Retired from API-v1 and installed production:

```text
parent-pairing-token filesystem secret
X-Pip-Token
?token=<shared-token>
greia_parent=<shared-token> legacy cookie
pairing_token bootstrap field
hidden token retrieval helpers
QR/PIN/Allow ceremony as a required authentication path
one household-wide shared bearer token
```

Current transport is still provisional HTTP. Passing this procedure proves the authentication/runtime behavior; it does **not** close the separate ordinary-family release blocker for authenticated encrypted transport and endpoint identity.

---

## 2. Evidence classes and non-negotiable rules

Every result belongs to one evidence class:

```text
SOURCE
IMAGE
BROWSER
PHYSICAL
```

Never promote evidence between classes. A unit test is not browser proof. HTTP 200 is not proof that ALSA, Wi-Fi, or another physical subsystem actually changed.

During the frozen attempt do not:

- use GitHub-hosted Actions;
- edit either repository after recording the candidate SHA;
- use `?demo=1` or a demo adapter as production evidence;
- manually copy Parent files into `/usr/share/greia-parent-app`;
- edit the Parent pin, runtime manifest, vendor tree, image overlay, credential store, password digest, or device registry;
- read a hidden legacy token to make authentication work;
- expose the Parent password or bearer credentials in screenshots/logs/evidence;
- revoke unrelated real Parent devices;
- weaken the Parent service sandbox or give it generic root/sudo/shell authority;
- claim PASS for a lane that was not executed.

If any prohibited action appears necessary, stop and report `INCOMPLETE` with the first failing invariant.

---

## 3. Create one evidence root

From the Greia repository root:

```bash
set -euo pipefail
EVIDENCE="$PWD/tmp/PARENT_UNIFIED_ACCEPTANCE_2026-09-08"
rm -rf "$EVIDENCE"
mkdir -p "$EVIDENCE"/{identity,parent,source,image,browser,physical,restore}
```

The destructive command above is permitted only for that exact project-local evidence directory.

---

## 4. Freeze repository identities

### 4.1 Greia

```bash
set -euo pipefail
git fetch origin
git status --short | tee "$EVIDENCE/identity/greia-status.txt"
git rev-parse HEAD | tee "$EVIDENCE/identity/greia-head.txt"
git rev-parse origin/main | tee "$EVIDENCE/identity/greia-origin-main.txt"
git diff --check | tee "$EVIDENCE/identity/greia-diff-check.txt"
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
```

Expected:

- clean relevant tree;
- `HEAD == origin/main`;
- `git diff --check` exits 0.

Record:

```bash
GREIA_SHA="$(git rev-parse HEAD)"
printf '%s\n' "$GREIA_SHA" > "$EVIDENCE/identity/GREIA_SHA.txt"
```

Do not change Greia source after this point.

### 4.2 Frozen Parent client

In the separate Parent repository:

```bash
cd /ABSOLUTE/PATH/TO/Greia-Parent-App-Html
set -euo pipefail
git status --short | tee "$EVIDENCE/parent/parent-status.txt"
git rev-parse HEAD | tee "$EVIDENCE/parent/parent-head.txt"
test "$(git rev-parse HEAD)" = "01301d285c6ba2a9a1f2948a9768b821d2536729"
```

Expected exact Parent SHA:

```text
01301d285c6ba2a9a1f2948a9768b821d2536729
```

Do not silently test a newer Parent `main`.

---

## 5. Parent client source gate

Still in the exact Parent checkout:

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

Required:

```text
NODE_SYNTAX=PASS
PARENT_NPM_TEST=PASS
RUNTIME_MANIFEST_GENERATION=PASS
```

The manifest must represent the dependency-derived closure reachable from `index.html`; remote runtime dependencies, escaping local paths, or missing imports/assets are failures.

Do not continue if this section fails.

---

## 6. Greia pin and runtime identity gate

Return to the Greia repository root.

```bash
cd /ABSOLUTE/PATH/TO/Greia
set -euo pipefail
```

Prove the exact frozen pin and integration state:

```bash
grep -F 'revision = "01301d285c6ba2a9a1f2948a9768b821d2536729"' \
  runtime/parent-app-client.toml

grep -F 'integration_state = "vendored-image-integrity-enforced"' \
  runtime/parent-app-client.toml
```

Compare the Parent-generated manifest with Greia's committed manifest semantically:

```bash
python3 - "$EVIDENCE/parent/generated-runtime-manifest.json" \
  runtime/parent-app-client.manifest.json <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    parent = json.load(fh)
with open(sys.argv[2], encoding="utf-8") as fh:
    greia = json.load(fh)
assert parent == greia, "Parent-generated runtime manifest differs from Greia manifest"
print("PARENT_RUNTIME_MANIFEST_MATCH")
PY
```

Expected:

```text
PARENT_RUNTIME_MANIFEST_MATCH
```

---

## 7. Greia focused source gate

Run these commands **in this order**. Stop at the first non-zero exit.

### 7.1 Canonical repin transaction

```bash
PYTHONPATH=src python3 -m unittest discover -s tests \
  -p 'test_update_parent_client_pin.py' -v \
  |& tee "$EVIDENCE/source/test-update-parent-client-pin.log"
```

### 7.2 API-v1 semantic authentication

```bash
PYTHONPATH=src python3 -m unittest discover -s tests \
  -p 'test_parent_api.py' -v \
  |& tee "$EVIDENCE/source/test-parent-api.log"
```

### 7.3 Retired shared-token negative HTTP boundary

```bash
PYTHONPATH=src python3 -m unittest discover -s tests \
  -p 'test_parent_api_legacy_token_negative.py' -v \
  |& tee "$EVIDENCE/source/test-parent-api-legacy-token-negative.log"
```

This suite must prove at the real API-v1 HTTP handler boundary that all of the following fail:

```text
X-Pip-Token: <legacy token>
Cookie: greia_parent=<legacy token>
/api/v1/...?...token=<legacy token>
POST /api/v1/pairing/bootstrap with pairing_token and no password
```

It must also prove that the supported device credential transports work:

```text
Authorization: Bearer <device credential>
Cookie: greia_parent_device=<device credential>
```

### 7.4 Legacy standalone compatibility boundary

```bash
PYTHONPATH=src python3 -m unittest discover -s tests \
  -p 'test_parent_legacy_status_auth.py' -v \
  |& tee "$EVIDENCE/source/test-parent-legacy-status-auth.log"
```

This does not authorize legacy authentication in API-v1. It only protects the deliberately separate standalone compatibility server until that server is removed.

### 7.5 Authentication ownership structure

```bash
PYTHONPATH=src python3 -m unittest discover -s tests \
  -p 'test_parent_auth_ownership.py' -v \
  |& tee "$EVIDENCE/source/test-parent-auth-ownership.log"
```

### 7.6 Static Parent client staging

```bash
PYTHONPATH=src python3 -m unittest discover -s tests \
  -p 'test_parent_app_staging.py' -v \
  |& tee "$EVIDENCE/source/test-parent-app-staging.log"
```

### 7.7 Image integration contract

```bash
PYTHONPATH=src python3 -m unittest discover -s tests \
  -p 'test_parent_client_image_integration.py' -v \
  |& tee "$EVIDENCE/source/test-parent-client-image-integration.log"
```

### 7.8 Password authority

```bash
PYTHONPATH=src python3 -m unittest discover -s tests \
  -p 'test_parent_password_auth.py' -v \
  |& tee "$EVIDENCE/source/test-parent-password-auth.log"
```

### 7.9 Installed production composition

```bash
PYTHONPATH=src python3 -m unittest discover -s tests \
  -p 'test_parent_production_api.py' -v \
  |& tee "$EVIDENCE/source/test-parent-production-api.log"
```

Required:

```text
FOCUSED_COMMANDS=9/9 PASS
```

A committed test that was not executed is not PASS.

---

## 8. Exact runtime integrity gate

Verify both committed copies against the same pin/manifest contract.

### Vendor runtime

```bash
PYTHONPATH=src python3 -m greia_parent.parent_client_integrity \
  --root vendor/parent-app \
  --manifest runtime/parent-app-client.manifest.json \
  --pin runtime/parent-app-client.toml \
  | tee "$EVIDENCE/source/vendor-integrity.txt"
```

### Image-overlay runtime

```bash
PYTHONPATH=src python3 -m greia_parent.parent_client_integrity \
  --root build/overlay/usr/share/greia-parent-app \
  --manifest runtime/parent-app-client.manifest.json \
  --pin runtime/parent-app-client.toml \
  | tee "$EVIDENCE/source/overlay-integrity.txt"
```

Both must print:

```text
Greia Parent client integrity OK: 01301d285c6ba2a9a1f2948a9768b821d2536729
```

---

## 9. Full Greia source gate

```bash
make verify |& tee "$EVIDENCE/source/make-verify.log"
```

Required:

```text
MAKE_VERIFY=PASS
```

Do not build or deploy an image from source that fails sections 5–9.

---

## 10. Build the canonical image

Use the **current sanctioned Greia builder/profile for the target machine** from `SETUP.md`, `docs/agents/GREIA_AGENT_OPERATIONS.md`, and the active hardware/image plan. Do not invent a new builder, image profile, partition layout, or ad-hoc overlay copy for this acceptance.

Before running the builder, record the exact command in:

```text
$EVIDENCE/image/build-command.txt
```

Required facts to retain:

```text
GREIA_SHA
TARGET_PROFILE
BUILDER_COMMAND
IMAGE_PATH
IMAGE_SHA256
BUILD_EXIT_CODE
```

The build must consume the committed Greia tree. Do not manually replace `/usr/share/greia-parent-app` after the image is built.

If the current machine/profile has no sanctioned build path, report `IMAGE_INTEGRITY=NOT_RUN` and stop before browser/physical claims that require that image.

---

## 11. Verify the installed Parent runtime inside the built root

Before booting the image, inspect the produced root filesystem through the builder's sanctioned mount/chroot/image-inspection mechanism.

Run the equivalent of:

```bash
PYTHONPATH=<MOUNT>/opt/greia-os/src \
python3 -m greia_parent.parent_client_integrity \
  --root <MOUNT>/usr/share/greia-parent-app \
  --manifest <MOUNT>/opt/greia-os/runtime/parent-app-client.manifest.json \
  --pin <MOUNT>/opt/greia-os/runtime/parent-app-client.toml \
  | tee "$EVIDENCE/image/installed-parent-integrity.txt"
```

Expected:

```text
Greia Parent client integrity OK: 01301d285c6ba2a9a1f2948a9768b821d2536729
```

Also prove the installed static runtime contains no retired browser token UI/request vocabulary:

```bash
! grep -R -n --fixed-string 'pairing_token' <MOUNT>/usr/share/greia-parent-app
! grep -R -n --fixed-string 'Pairing token' <MOUNT>/usr/share/greia-parent-app
```

Do not fail merely because the API route name contains the word `pairing`.

---

## 12. Boot and discovery acceptance

Boot the exact image on the accepted target or accepted disposable test installation.

From another real LAN device/browser:

1. Confirm the Greia Parent service is discoverable by the product's supported discovery mechanism.
2. Confirm the discovered endpoint resolves to the intended Greia machine.
3. Open the production Parent URL, normally:

```text
http://<GREIA-IP>:8766/
```

4. Confirm the unauthenticated metadata/discovery surface does not expose child/profile data, Parent password material, device credentials, machine secrets, or a legacy shared token.

Record discovery evidence without recording secrets.

---

## 13. Fresh/default-password bootstrap

Use a genuinely unpaired browser profile/private browser or an owner-approved disposable test environment. Do not destroy unrelated live device credentials merely to manufacture a fresh state.

Expected page:

- asks for **Greia password**;
- explains that new Greia systems start with `greia`;
- contains no pairing-token field;
- contains no instruction to retrieve a hidden token from the machine.

Enter the fresh-system password:

```text
greia
```

Expected network behavior:

```text
POST /api/v1/pairing/bootstrap
Content-Type: application/json
body keys: password, device_name
HTTP 201
```

Required browser-state proof:

- Parent password is not persisted in localStorage/sessionStorage/IndexedDB;
- one per-device credential is persisted under the current Parent credential-storage contract;
- the raw bearer credential is not copied into screenshots/evidence;
- normal management API requests authenticate with the device credential, not the Parent password.

Capture sanitized screenshots and DevTools request metadata. Do not save request bodies containing the password.

---

## 14. Wrong-password negative test

Use a separate unpaired/private browser.

Attempt bootstrap with a definitely wrong Parent password.

Expected:

```text
bootstrap rejected
no new Parent device appears
no browser device credential is stored
normal management API remains unavailable
```

Do not continue if a wrong password creates a device credential.

---

## 15. Reload and browser restart persistence

With the successfully paired browser:

1. Record the visible Parent device count.
2. Refresh the page.
3. Close the Parent tab completely.
4. Reopen the production URL.
5. Restart the browser if practical and reopen once more.

Expected:

- no Parent-password prompt;
- existing device credential authenticates successfully;
- reload/reopen does not create an additional Parent device;
- Parent password is still absent from browser persistence.

---

## 16. Password-change lifecycle

From the authenticated Parent UI, change the Parent password from `greia` to an owner-chosen temporary test password.

**Do not write the new password into evidence.**

Immediately prove:

1. the already-paired browser remains authenticated using its independent device credential;
2. an unpaired/private browser fails bootstrap with old password `greia`;
3. the same unpaired/private browser succeeds with the new Parent password;
4. success creates a distinct second Parent device credential;
5. no shared household bearer token appears anywhere in the workflow.

If existing paired devices are unexpectedly invalidated by the password change, record a product-contract failure and stop; do not reinterpret the behavior during acceptance.

---

## 17. Independent Parent-device revocation

With two independently paired browsers/devices available:

1. Identify browser/device A and browser/device B in Parent device management.
2. Revoke only A.
3. Refresh A.
4. Refresh B.

Expected:

```text
A loses authenticated API access
A's old credential remains rejected after refresh/reopen
B remains authenticated
```

Then bootstrap A again with the **current Parent password**.

Expected:

- A can return only through password bootstrap;
- it receives a **fresh** credential;
- the revoked credential is not resurrected;
- B remains unaffected.

---

## 18. Retired shared-token negative proof on the real API

Do not retrieve or invent a real secret for these checks. Use a clearly fake value such as:

```text
LEGACY_TEST_TOKEN=LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL
```

Against a protected API-v1 endpoint, verify all retired transports fail:

```text
X-Pip-Token: <fake legacy token>                  -> 401 pairing_required
Cookie: greia_parent=<fake legacy token>          -> 401 pairing_required
/api/v1/devices?token=<fake legacy token>         -> 401 pairing_required
bootstrap JSON with pairing_token and no password -> 400 invalid_request
```

Also prove the legacy server route is not accidentally exposed by the API-v1 service:

```text
GET /pair?token=<fake legacy token> -> 404
```

On the installed machine, prove stale production token state is absent:

```bash
test ! -e /var/lib/greia-parent/parent-pairing-token \
  && test ! -e /var/lib/greia-os/parent-pairing-token
```

If the current installed Parent state directory is documented elsewhere, use that exact path and record it. Do not search the entire disk for secrets.

---

## 19. Production process/sandbox sanity

On the Greia machine, confirm the real Parent service is the intended unprivileged production composition.

Record:

```text
systemctl status greia-parent.service
systemctl show greia-parent.service --property=User --property=Group \
  --property=NoNewPrivileges --property=ProtectSystem --property=CapabilityBoundingSet
```

Expected architecture:

- service runs as the documented unprivileged Parent user;
- no generic root/sudo/shell bridge;
- capability map is fail-closed to operations the installed composition can genuinely perform.

Do not mutate unit hardening to make a browser feature pass.

---

## 20. Real Parent system-control acceptance

Only test controls that the API capability map advertises as available on this exact installed target. A hidden/false capability is not a failure merely because another machine supports it.

For every advertised mutation:

```text
1. record pre-state from the actual machine/service
2. trigger the mutation through the real Parent browser UI
3. verify post-state independently from the actual machine/service
4. restore the desired owner state
```

### 20.1 Speaker volume/mute

If advertised, verify at minimum:

- volume change in browser causes actual ALSA/system-control desired/applied state to change;
- mute causes the actual playback state to change;
- unmute restores it;
- browser UI alone is not accepted as proof.

### 20.2 Wi-Fi

If `network.manage=true`:

- scan results come from the real installed backend;
- connecting to an owner-approved test network changes actual network association;
- reconnect/restart behavior matches product policy;
- no synthetic/manual network object is accepted as production evidence.

If the installed process cannot genuinely manage iwd, expected capability is `network.manage=false`.

### 20.3 SSH maintenance

If `maintenance.ssh=true`:

- toggle through Parent UI;
- verify actual service state independently;
- verify the typed maintenance boundary rather than arbitrary shell execution;
- restore the owner's desired state.

### 20.4 Language and other advertised system settings

For each tested setting:

- browser mutation succeeds;
- canonical Greia state changes;
- the corresponding system/session consumer observes the change;
- persistence across the documented restart/reload boundary is proven where promised.

Record `NOT_APPLICABLE` for capabilities intentionally unavailable on the target.

---

## 21. Device/profile/Activity management smoke acceptance

Using the real Parent browser and the real Greia machine, perform a bounded smoke test of already-supported unprivileged management:

- list existing child profiles without exposing filesystem paths;
- change and restore one harmless profile setting;
- verify Activity visibility/policy changes affect the child launcher according to current policy;
- verify a hidden Activity disappears and reappears after restoration;
- verify no unrelated profile/device state changes.

Use a disposable/known-safe setting and restore it before ending the attempt.

This section does not substitute for the separate full package/update/backup release gates.

---

## 22. Restore owner state

Before final reporting:

1. Restore the owner's desired Parent password through the normal Parent UI.
2. Revoke only temporary test Parent devices that were clearly created by this procedure.
3. Restore Wi-Fi, SSH, volume/mute, language, profile policy, and Activity visibility changes made for testing.
4. Do not edit password digests, credential JSON, or policy files directly to perform restoration.

Record restoration as facts only; do not record passwords or bearer credentials.

---

## 23. Transport release blocker

Even if every section above passes, record:

```text
AUTHENTICATED_ENCRYPTED_TRANSPORT=NOT_COMPLETE
ORDINARY_FAMILY_PARENT_RELEASE=BLOCKED
```

until Greia has accepted evidence for:

- authenticated encrypted Parent transport;
- Greia endpoint/device identity;
- a reviewed trust/onboarding lifecycle that preserves the simple Parent-password UX;
- no reintroduction of hidden filesystem secrets or mandatory QR/PIN/token ceremonies as a workaround.

Do not implement ad-hoc application crypto inside this test procedure.

---

## 24. Final report template

Return exactly one report containing at least:

```text
GREIA_SHA=<exact tested Greia SHA>
PARENT_SHA=01301d285c6ba2a9a1f2948a9768b821d2536729

SOURCE_IDENTITY=PASS|FAIL
PARENT_NODE_SYNTAX=PASS|FAIL|NOT_RUN
PARENT_NPM_TEST=PASS|FAIL|NOT_RUN
PARENT_RUNTIME_MANIFEST=PASS|FAIL|NOT_RUN
GREIA_MANIFEST_MATCH=PASS|FAIL|NOT_RUN
REPIN_TRANSACTION_TEST=PASS|FAIL|NOT_RUN
API_V1_TEST=PASS|FAIL|NOT_RUN
LEGACY_TOKEN_NEGATIVE_HTTP_TEST=PASS|FAIL|NOT_RUN
LEGACY_STATUS_COMPAT_TEST=PASS|FAIL|NOT_RUN
AUTH_OWNERSHIP_TEST=PASS|FAIL|NOT_RUN
PARENT_APP_STAGING_TEST=PASS|FAIL|NOT_RUN
PARENT_IMAGE_INTEGRATION_TEST=PASS|FAIL|NOT_RUN
PARENT_PASSWORD_AUTH_TEST=PASS|FAIL|NOT_RUN
PARENT_PRODUCTION_API_TEST=PASS|FAIL|NOT_RUN
VENDOR_RUNTIME_INTEGRITY=PASS|FAIL|NOT_RUN
OVERLAY_RUNTIME_INTEGRITY=PASS|FAIL|NOT_RUN
MAKE_VERIFY=PASS|FAIL|NOT_RUN

IMAGE_BUILD=PASS|FAIL|NOT_RUN
IMAGE_SHA256=<value|NOT_RUN>
INSTALLED_RUNTIME_INTEGRITY=PASS|FAIL|NOT_RUN

DISCOVERY=PASS|FAIL|NOT_RUN
DEFAULT_PASSWORD_BOOTSTRAP=PASS|FAIL|NOT_RUN
WRONG_PASSWORD_REJECTED=PASS|FAIL|NOT_RUN
PASSWORD_NOT_PERSISTED_IN_BROWSER=PASS|FAIL|NOT_RUN
DEVICE_CREDENTIAL_PERSISTENCE=PASS|FAIL|NOT_RUN
PASSWORD_CHANGE_OLD_REJECTED_NEW_ACCEPTED=PASS|FAIL|NOT_RUN
EXISTING_DEVICE_SURVIVES_PASSWORD_CHANGE=PASS|FAIL|NOT_RUN
INDEPENDENT_DEVICE_REVOCATION=PASS|FAIL|NOT_RUN
REBOOTSTRAP_GETS_FRESH_CREDENTIAL=PASS|FAIL|NOT_RUN
LEGACY_SHARED_TOKEN_HTTP_NEGATIVE=PASS|FAIL|NOT_RUN
LEGACY_SHARED_TOKEN_STATE_ABSENT=PASS|FAIL|NOT_RUN

PARENT_SERVICE_SANDBOX=PASS|FAIL|NOT_RUN
VOLUME_MUTE_PHYSICAL=PASS|FAIL|NOT_APPLICABLE|NOT_RUN
WIFI_PHYSICAL=PASS|FAIL|NOT_APPLICABLE|NOT_RUN
SSH_MAINTENANCE_PHYSICAL=PASS|FAIL|NOT_APPLICABLE|NOT_RUN
OTHER_SYSTEM_SETTINGS_PHYSICAL=PASS|FAIL|NOT_APPLICABLE|NOT_RUN
PROFILE_ACTIVITY_POLICY_SMOKE=PASS|FAIL|NOT_RUN
OWNER_STATE_RESTORED=PASS|FAIL|NOT_RUN

AUTHENTICATED_ENCRYPTED_TRANSPORT=PASS|FAIL|NOT_COMPLETE
ORDINARY_FAMILY_PARENT_RELEASE=READY|BLOCKED

FIRST_FAILURE=<none or exact first failing invariant>
EVIDENCE_ROOT=<absolute path>
```

### Verdict rule

- **ACCEPTED**: all required source, image, browser, negative-auth, restoration, and applicable physical lanes pass. Transport may still separately report `NOT_COMPLETE`, which means the authentication/runtime tranche is accepted but ordinary-family release remains blocked.
- **REJECTED**: a required invariant was genuinely tested and failed.
- **INCOMPLETE**: a required evidence lane was not executable or was stopped before execution.

Never convert `NOT_RUN` into PASS by inference.

---

## 25. Minimum evidence bundle to return

Return/archive the complete evidence root, excluding secrets, with at least:

```text
identity/greia-head.txt
identity/greia-origin-main.txt
identity/greia-status.txt
parent/parent-head.txt
parent/node-check.log
parent/npm-test.log
parent/generated-runtime-manifest.json
source/test-update-parent-client-pin.log
source/test-parent-api.log
source/test-parent-api-legacy-token-negative.log
source/test-parent-legacy-status-auth.log
source/test-parent-auth-ownership.log
source/test-parent-app-staging.log
source/test-parent-client-image-integration.log
source/test-parent-password-auth.log
source/test-parent-production-api.log
source/vendor-integrity.txt
source/overlay-integrity.txt
source/make-verify.log
image/build-command.txt
image/installed-parent-integrity.txt
browser/<sanitized screenshots and network metadata>
physical/<system-control evidence>
restore/<restoration facts>
FINAL_REPORT.txt
```

Before returning the archive, inspect it for accidental Parent passwords or bearer credentials. If secrets were captured, delete/redact those evidence files and repeat only the affected evidence capture—not the product action—without exposing the secret.
