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

Future repins now have one canonical command:

```bash
python3 tools/update_parent_client_pin.py \
  --parent-root /path/to/Greia-Parent-App-Html \
  --revision <exact-reviewed-parent-sha>
```

That command captures the dependency-derived Parent runtime bytes once, derives the manifest from those bytes, stages the pin/manifest/vendor/image-overlay artifacts together, and rolls back the previous Greia state if a multi-path replacement fails. Do not manually advance those four artifacts as separate repin steps.

## 4. Parent authentication contract

The old human-entered shared `parent-pairing-token` model is retired from API v1 and from the installed production path.

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

`ParentApiApplication` owns this boundary for every API-v1 composition: during inherited initialization it removes stale `parent-pairing-token` state and returns no shared token. `ProductionParentApiApplication` no longer carries a production-only token-suppression override. The older `ParentStatusApplication` still owns its compatibility token only for the standalone legacy status server; that server is not production Parent API authority.

The route word `pairing` remains API-v1 vocabulary only. Do not reintroduce `pairing_token`, `X-Pip-Token`, token query URLs, a shared household bearer token, or a filesystem-token retrieval workflow into API v1 or the installed Parent path.

## 5. Parent integration work completed in the current tranche

The September 8 authentication/runtime tranche has now done the following on `main`:

- Greia backend password bootstrap and device-only ordinary authorization were already implemented;
- production password attempts are bounded/rate-limited;
- stale legacy `parent-pairing-token` state is removed by the API-v1 composition boundary rather than by a production-only override;
- direct API-v1 composition and installed production therefore share the same no-shared-token initialization rule;
- the standalone legacy status server retains its compatibility token behavior as a separate legacy boundary;
- direct API-v1 behavior, structural ownership, and legacy-status compatibility regressions protect all sides of that boundary;
- the standalone Parent source uses password bootstrap and stores only the issued device credential;
- the accepted Parent runtime was frozen at `01301d285c6ba2a9a1f2948a9768b821d2536729`;
- Greia's pin and exact runtime manifest were advanced to that revision;
- `vendor/parent-app/` was synchronized to the frozen Parent bytes;
- `build/overlay/usr/share/greia-parent-app/` was also synchronized, closing the earlier defect where the actual image payload still contained the old browser;
- the Parent runtime manifest is dependency-derived from the accepted entrypoint rather than maintained as a fragile hand-written list;
- `tests/test_parent_client_image_integration.py` no longer hard-codes a specific Parent revision; it checks the pin/manifest invariant instead;
- Parent architecture/source-integration documentation describes the password/device-credential model;
- the exact-current acceptance procedure covers password/bootstrap/reload/password-change/revocation plus the API-v1/legacy auth ownership boundary;
- the first owner-controlled frozen attempt correctly detected one stale manifest digest before any image was built;
- that manifest-only defect was corrected without changing runtime bytes or the Parent pin;
- `tools/update_parent_client_pin.py` was hardened so one operation owns pin, manifest, vendor and image-overlay synchronization from the same captured Parent bytes;
- `tests/test_update_parent_client_pin.py` covers transitive runtime discovery, exact byte/digest equality, stale-file removal, dirty-source refusal and rollback after a partial swap failure.

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
c4da23a9fd706bb42c0f06f0b47b000b164a0582  make Parent repin synchronize all runtime copies
c86016f4e6f27ceaeb01d0537dc55f080acbfa5c  add atomic/synchronized repin regression tests
6efbba2489f56374ec508056e42029c5f84c5ff6  remove production-only token retirement ownership
a1b67afbcd0ca4e4e0b3463c45b9f485d8934d09  retire shared token at API-v1 boundary
5e834ec05a524cf61f5680f3c932767ec0e2a020  test direct API-v1 shared-token retirement
e7dbcdc977a8c26e69ed6b81ace4f3f50719c50e  protect legacy status auth boundary
a17ff8fc6c29ca9442dc78113e01cdeb47ecd8be  protect Parent API auth ownership seam
397e6cd29a3c468d1165cb0c4ef194ebe07d0dfe  add auth ownership seam to Parent gate
```

A documentation commit containing this handover is necessarily a descendant of those implementation commits; use `git rev-parse HEAD` for the exact checkout under test.

## 6. Parent evidence boundary

What is currently established:

```text
PASSWORD BOOTSTRAP ARCHITECTURE: IMPLEMENTED
PER-DEVICE CREDENTIAL AUTHORIZATION: IMPLEMENTED
API-V1 SHARED-TOKEN INITIALIZATION: RETIRED IN SOURCE
PRODUCTION-ONLY TOKEN OVERRIDE: REMOVED; PRODUCTION INHERITS API-V1 RULE
LEGACY STANDALONE STATUS TOKEN: COMPATIBILITY-ONLY, SOURCE UNCHANGED
PARENT RUNTIME PIN: 01301d... IMPLEMENTED
VENDOR RUNTIME: SYNCHRONIZED
IMAGE OVERLAY RUNTIME: SYNCHRONIZED
INSTALLED-RUNTIME INTEGRITY CONTRACT: IMPLEMENTED
PARENT SOURCE GATE AT 01301d...: PASS — npm test 77/77, node syntax, runtime_manifest.mjs
FIRST GREIA FROZEN ATTEMPT AT 1f01d413: STOPPED AT §4 MANIFEST COMPARISON
FIRST FAILURE: stale src/views_activities.js digest only
STALE DIGEST: FIXED IN 35b88c79
SINGLE-OPERATION REPIN TOOL: IMPLEMENTED
REPIN TOOL REGRESSION TEST: COMMITTED, LOCAL EXECUTION PENDING
API-V1 BEHAVIOR / OWNERSHIP / LEGACY AUTH-BOUNDARY TESTS: COMMITTED, LOCAL EXECUTION PENDING
POST-FIX GREIA FOCUSED TESTS: PENDING
POST-FIX make verify: PENDING
OFFICIAL IMAGE BUILD WITH THIS DESCENDANT: PENDING
REAL-BROWSER PASSWORD/RELOAD/CHANGE/REVOKE ACCEPTANCE: PENDING
PHYSICAL ACER PARENT REAL-RUNTIME ACCEPTANCE FOR THIS DESCENDANT: PENDING
AUTHENTICATED ENCRYPTED TRANSPORT FOR ORDINARY-FAMILY RELEASE: PENDING
```

The failed `1f01d413` attempt was valid evidence: it proved the source gate detects exact runtime-metadata drift and stopped before image construction. Do not erase or reinterpret it as a later PASS.

The repin-tool and API-v1 ownership commits do not change the frozen Parent client, pin revision, manifest data, vendor bytes or image-overlay bytes. They do invalidate any claim that the Greia exact-head source gate itself has already passed; the new tests and current `make verify` still have to execute.

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

The current gate requires, in order:

```text
1. exact Parent source SHA 01301d... + node syntax + npm test
2. dependency-derived Parent runtime manifest regeneration
3. semantic equality with Greia's committed manifest
4. synchronized-repin transaction regression test
5. direct API-v1 behavior + structural ownership + legacy-status compatibility boundary tests
6. Greia Parent staging/image/password/production focused tests
7. vendor integrity verification
8. image-overlay integrity verification
9. current make verify
10. official image/runtime integrity
11. real browser: default greia password bootstrap
12. close/reopen: device credential reconnect without password
13. Parent password change: old rejected, new accepted for new bootstrap
14. independent device revocation
15. revoked browser rebootstrap only with current password
16. obsolete shared-token state/helper negative proof
17. wider physical system-control checks where applicable
```

STOP on the first failure and return the evidence collected so far.

### Resume rule after the 1f01d413 failure

Because Parent `01301d...` did not change and its source gate already passed 77/77, the next attempt does not need to repeat `npm test` merely because Greia changed.

The next operator must:

```text
1. pull current Greia main
2. prove clean tree and HEAD == origin/main
3. keep Parent exactly at 01301d...
4. regenerate the Parent manifest or reuse the retained generated file only if its provenance is still exact 01301d...
5. resume at §4 semantic manifest comparison
6. run the synchronized-repin regression test
7. run the direct API-v1 behavior, structural ownership, and legacy-status compatibility tests
8. if green, continue all remaining Greia focused/integrity/make verify steps in order
```

Any Parent checkout/source change invalidates reuse of the earlier Parent source gate and requires §3 again.

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
tools/update_parent_client_pin.py
tests/test_update_parent_client_pin.py
tests/test_parent_api.py
tests/test_parent_auth_ownership.py
tests/test_parent_legacy_status_auth.py
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

The earlier token-initialization ownership debt is resolved: `ParentApiApplication` now owns API-v1 retirement of stale shared-token state, and production inherits that rule. The old `ParentStatusApplication` token remains only because the standalone legacy status server still has its compatibility authentication path. If that legacy server is later deleted, remove its token mechanism with the server rather than migrating it back into API v1.

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

The already-green Parent source gate from the failed frozen attempt may be reused because Parent source did not change. Re-run the §4 manifest comparison, then execute all eight focused commands in the documented order. If and only if all eight focused tests, both integrity checks and current `make verify` are green, proceed to the sanctioned image and real-browser password/bootstrap/reload/password-change/revocation sequence.

Do not use the old shared-token instructions.
