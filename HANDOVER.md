# Greia — Current Engineering Handover

**Updated:** 2026-09-08  
**Canonical repository/branch:** `frozenpepper/Greia` / `main`  
**Version:** `0.13.0-phase0-dev`  
**Primary blocking phase:** **R8 — Raspberry Pi 400 / Pi 500 ARM64 board and image adapters**  
**Public-source readiness:** **IN PROGRESS**  
**Ordinary-family release:** **NOT READY**

This file is current-state routing only. Historical implementation detail belongs in Git history, dated reviews, testing records, and the append-only active plan ledger.

## 1. Start here

Read in this order:

```text
AGENTS.md
README.md
docs/DOCUMENTATION.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
HANDOVER.md
skills/greia-os-work/SKILL.md
```

Before installing/configuring tools also read:

```text
SETUP.md
docs/agents/GREIA_AGENT_OPERATIONS.md
```

Do not use GitHub-hosted Actions without explicit owner authorization.

## 2. Current major platform state

R7 display/session/trusted-chrome work is complete and has physical Acer evidence at its recorded accepted candidate. The primary architecture plan remains active and the next blocking architecture family is R8 ARM64/Pi work.

Do not infer current implementation state from old numbered sections that previously accumulated in this file; use the active plan, source, and current dated acceptance procedures.

Current first-party catalogue remains 41 Activities unless live catalogue discovery shows a later accepted addition. Catalogue assertions must be discovery-based, not fixed-count gates.

## 3. Parent management — current source authority

The maintained browser client lives in the separate repository:

```text
frozenpepper/Greia-Parent-App-Html
```

The exact Parent revision currently integrated into Greia is:

```text
01301d285c6ba2a9a1f2948a9768b821d2536729
```

Greia's production chain is:

```text
Greia-Parent-App-Html accepted revision
  -> runtime/parent-app-client.toml
  -> runtime/parent-app-client.manifest.json
  -> vendor/parent-app/
  -> build/overlay/usr/share/greia-parent-app/
  -> /usr/share/greia-parent-app in the built image
```

The pin state is:

```text
revision = 01301d285c6ba2a9a1f2948a9768b821d2536729
integration_state = vendored-image-integrity-enforced
```

The vendor and image-overlay runtime are synchronized to that frozen Parent revision. The installed service verifies the runtime against the pin/manifest before serving it.

## 4. Parent authentication contract

The old human-entered shared `parent-pairing-token` model is retired from the installed production path.

Current browser authentication is:

```text
Parent enters Greia password once
  -> POST /api/v1/pairing/bootstrap
     body: {password, device_name}
  -> Greia verifies MainCredential locally
  -> Greia issues one revocable per-device credential
  -> browser stores only that device credential
  -> ordinary requests use Authorization: Bearer <device credential>
```

Initial Parent credential on a fresh system remains:

```text
username: greia
password: greia
```

Parents can change the password through Parent management. Existing browser devices remain separate credentials and can be revoked independently.

The route word `pairing` remains API-v1 vocabulary only. Do not reintroduce `pairing_token`, `X-Pip-Token`, token query URLs, a shared household bearer token, or a filesystem-token retrieval workflow.

## 5. Parent integration work completed in the current tranche

The September 8 authentication/runtime tranche has now done the following on `main`:

- Greia backend password bootstrap and device-only ordinary authorization were already implemented;
- production password attempts are bounded/rate-limited;
- stale legacy `parent-pairing-token` state is removed in installed production composition;
- the standalone Parent source uses password bootstrap and stores only the issued device credential;
- the accepted Parent runtime was frozen at `01301d285c6ba2a9a1f2948a9768b821d2536729`;
- Greia's pin and exact runtime manifest were advanced to that revision;
- `vendor/parent-app/` was synchronized to the frozen Parent bytes;
- `build/overlay/usr/share/greia-parent-app/` was also synchronized, closing the earlier defect where the actual image payload still contained the old browser;
- the Parent runtime manifest is dependency-derived from the accepted entrypoint rather than maintained as a fragile hand-written list;
- `tests/test_parent_client_image_integration.py` no longer hard-codes a specific Parent revision; it checks the pin/manifest invariant instead;
- Parent architecture/source-integration documentation now describes the password/device-credential model;
- a new exact-current acceptance procedure exists for the password/bootstrap/reload/password-change/revocation lifecycle;
- the first owner-controlled frozen attempt correctly detected one stale manifest digest before any image was built;
- that manifest-only defect was corrected without changing runtime bytes or the Parent pin.

Key Greia commits in this cutover include:

```text
1f31e2b7e2e3b2326940a8b2828ece0e5c1091a3  repin Greia Parent runtime/vendor
25399c491e205e83808ecb3b533632aabc6218a9  synchronize actual image overlay
c533f9a6de4c9818a62167acf93ad77c31a24620  refresh stale pin assertion
ef49e88023d4900214d49e2666b163edf5de5a10  remove fixed-revision test coupling
91f058b500f2e1a2d91847a79a07f085e7f5b5c4  reconcile Parent source-integration authority
9a065cd7abe39a53af4d444639028485583422d1  reconcile Parent management auth/runtime state
818285807b3ab99cabb61a1fc501ea9afdb80c5b  add exact-current Parent password acceptance gate
35b88c79fc10d81ef844df941a3a48321bbce8ab  correct stale src/views_activities.js manifest digest
```

A documentation commit containing this handover is necessarily a descendant of those implementation commits; use `git rev-parse HEAD` for the exact checkout under test.

## 6. Parent evidence boundary

What is currently established:

```text
PASSWORD BOOTSTRAP ARCHITECTURE: IMPLEMENTED
PER-DEVICE CREDENTIAL AUTHORIZATION: IMPLEMENTED
LEGACY SHARED-TOKEN PRODUCTION FALLBACK: RETIRED IN SOURCE
PARENT RUNTIME PIN: 01301d... IMPLEMENTED
VENDOR RUNTIME: SYNCHRONIZED
IMAGE OVERLAY RUNTIME: SYNCHRONIZED
INSTALLED-RUNTIME INTEGRITY CONTRACT: IMPLEMENTED
PARENT SOURCE GATE AT 01301d...: PASS — npm test 77/77, node syntax, runtime_manifest.mjs
FIRST GREIA FROZEN ATTEMPT AT 1f01d413: STOPPED AT §4 MANIFEST COMPARISON
FIRST FAILURE: stale src/views_activities.js digest only
STALE DIGEST: FIXED IN 35b88c79
POST-FIX GREIA FOCUSED TESTS: PENDING
POST-FIX make verify: PENDING
OFFICIAL IMAGE BUILD WITH THIS DESCENDANT: PENDING
REAL-BROWSER PASSWORD/RELOAD/CHANGE/REVOKE ACCEPTANCE: PENDING
PHYSICAL ACER PARENT REAL-RUNTIME ACCEPTANCE FOR THIS DESCENDANT: PENDING
AUTHENTICATED ENCRYPTED TRANSPORT FOR ORDINARY-FAMILY RELEASE: PENDING
```

The failed `1f01d413` attempt was valid evidence: it proved the source gate detects exact runtime-metadata drift and stopped before image construction. Do not erase or reinterpret it as a later PASS.

## 7. Current Parent acceptance route

The authoritative authentication/runtime gate is:

```text
docs/testing/2026-09-08_PARENT_PASSWORD_RUNTIME_INTEGRATION_ACCEPTANCE.md
```

It supersedes the obsolete shared-token bootstrap instructions inside:

```text
docs/testing/2026-09-02_PARENT_REAL_RUNTIME_FINAL_ACCEPTANCE.md
```

The older document remains relevant for its wider system-control/hardware evidence after the new password-authentication sections are green.

The new gate requires, in order:

```text
1. exact Parent source SHA 01301d... + node syntax + npm test
2. dependency-derived Parent runtime manifest regeneration
3. semantic equality with Greia's committed manifest
4. Greia Parent staging/image/password/production focused tests
5. vendor integrity verification
6. image-overlay integrity verification
7. current make verify
8. official image/runtime integrity
9. real browser: default greia password bootstrap
10. close/reopen: device credential reconnect without password
11. Parent password change: old rejected, new accepted for new bootstrap
12. independent device revocation
13. revoked browser rebootstrap only with current password
14. obsolete shared-token state/helper negative proof
15. wider physical system-control checks where applicable
```

STOP on the first failure and return the evidence collected so far.

### Resume rule after the 1f01d413 failure

Because Parent `01301d...` did not change and its source gate already passed 77/77, the next attempt does not need to repeat `npm test` merely because Greia's manifest metadata changed.

The next operator must:

```text
1. pull current Greia main
2. prove clean tree and HEAD == origin/main
3. keep Parent exactly at 01301d...
4. regenerate the Parent manifest or reuse the retained generated file only if its provenance is still exact 01301d...
5. resume at §4 semantic manifest comparison
6. if §4 passes, continue all Greia focused/integrity/make verify steps in order
```

Any Parent checkout/source change invalidates that reuse and requires §3 again.

## 8. Other active acceptance procedures

Still-current subsystem procedures include, when their owning workstream is being closed:

```text
docs/testing/2026-09-04_CHILD_ACTIVITY_POLICY_FAIL_CLOSED_ACCEPTANCE.md
docs/testing/2026-09-03_ACTIVITY_AGE_POLICY_ACCEPTANCE.md
docs/testing/2026-09-02_RECENT_COMMIT_CLEANUP_ACCEPTANCE.md
docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md
docs/testing/2026-09-02_R7_PARENT_SPOKEN_LABEL_UNIFIED_PROMOTION_GATE.md
```

Do not run every dated test procedure indiscriminately. Select the gate owned by the work being accepted.

## 9. Parent/API ownership and boundaries

Current owners include:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
vendor/parent-app/
build/overlay/usr/share/greia-parent-app/
src/greia_parent/static_client.py
src/greia_parent/parent_client_integrity.py
src/greia_parent/password_auth.py
src/greia_parent/protocol.py
src/greia_parent/api_server.py
src/greia_parent/package_api.py
src/greia_parent/update_api.py
src/greia_parent/production_api.py
src/greia_platform/main_credential.py
```

The Parent HTTP process remains unprivileged. Do not solve unavailable capabilities by giving it generic root/sudo/shell authority.

Production Wi-Fi remains fail-closed: real iwd only, and `network.manage=false` when the installed unprivileged composition cannot genuinely manage it.

Speaker volume/mute remains a typed desired-state path. The Parent HTTP process does not own ALSA; the child hardware session applies system-control state.

## 10. Known lower-priority Parent debt

`ParentApiApplication` still inherits from the older `ParentStatusApplication`, whose standalone legacy server owns shared-token initialization. Installed production suppresses that legacy initialization through a narrow `_load_or_create_token()` retirement override.

This is maintainability debt, not an active shared-token authorization fallback. Clean it in a normal local edit/test tranche by moving the retirement rule to the API-v1 composition boundary or separating legacy status-server authentication from the reusable domain application. Do not perform a large inheritance rewrite merely to remove one method.

The API metadata/route vocabulary still contains `pairing_required` and `/pairing/bootstrap`. Those names are not blockers while the semantics are password bootstrap -> per-device credential.

Current transport remains provisional HTTP. Password authentication must not be described as release-safe on a hostile LAN until authenticated encrypted transport and endpoint identity are implemented.

## 11. Evidence discipline

Always distinguish:

```text
SOURCE REVIEW
LOCAL AUTOMATED TEST
BROWSER
SIMULATOR
VM / IMAGE
PHYSICAL DEVICE
```

A committed regression test is not a PASS. A successful HTTP response is not proof that physical hardware changed. A later SHA does not inherit earlier physical evidence unless the relevant bytes and acceptance contract explicitly establish equivalence.

## 12. Next exact step

On the owner-controlled checkout:

```text
pull current Greia main
confirm clean HEAD == origin/main
keep Parent at exact 01301d285c6ba2a9a1f2948a9768b821d2536729
resume docs/testing/2026-09-08_PARENT_PASSWORD_RUNTIME_INTEGRATION_ACCEPTANCE.md at §4
```

The already-green Parent source gate from the failed frozen attempt may be reused because Parent source did not change. Re-run the §4 manifest comparison against the new Greia descendant. If and only if it is green, continue the four focused Greia suites, both integrity checks, and `make verify`.

Only after that complete source gate is green should the sanctioned image and real-browser password/bootstrap/reload/password-change/revocation sequence begin. Do not use the old shared-token instructions.
