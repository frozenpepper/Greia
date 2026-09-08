# Parent password runtime integration — source/image closure review

**Date:** 2026-09-08  
**Scope:** Greia Parent authentication migration and exact Parent browser runtime integration  
**Evidence class:** repository/source review plus partial owner-controlled local source execution; image-build and physical-browser evidence remain pending

## 1. Result

The migration from the old human-entered shared Parent pairing token to Greia-password bootstrap is coherent across the maintained Parent client, Greia API, Greia runtime pin, vendored browser runtime, and the actual image overlay.

The accepted Parent client revision is:

```text
frozenpepper/Greia-Parent-App-Html
01301d285c6ba2a9a1f2948a9768b821d2536729
```

Greia pins the same revision in:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

and carries the same frozen runtime under both:

```text
vendor/parent-app/
build/overlay/usr/share/greia-parent-app/
```

The earlier integration defect where Greia's backend expected `password` while the image still shipped a browser posting `pairing_token` is therefore source-fixed.

A first owner-controlled acceptance attempt at Greia `1f01d4139cc80ec4e0846412f3e7695a0cbc1927` correctly stopped in §4 because one committed manifest digest was stale. The runtime bytes themselves were already correct. That metadata defect is fixed by `35b88c79fc10d81ef844df941a3a48321bbce8ab` and requires a fresh resumed source gate before any image/browser claim.

## 2. Current authentication contract

The installed API/client contract is:

```text
human Parent password
  -> POST /api/v1/pairing/bootstrap
     {password, device_name}
  -> MainCredential verification
  -> fresh per-device credential
  -> ordinary Authorization: Bearer <device credential>
```

A fresh Greia starts with Parent password `greia`. Parents may change that password. The browser persists only its issued per-device credential, not the human password.

The route name `pairing/bootstrap` is retained API-v1 vocabulary. It does not preserve the retired shared-token input contract.

## 3. Legacy-token disposition

Installed production composition no longer authorizes the old household-wide token fallback. Production startup removes stale `parent-pairing-token` state and returns no legacy master credential.

The older standalone `ParentStatusApplication` implementation still contains shared-token machinery and remains a legacy inheritance dependency beneath the API-v1 class hierarchy. `ProductionParentApiApplication` currently suppresses that initializer with a narrow `_load_or_create_token()` retirement override.

This is maintainability debt, not an active production authorization fallback. A future local edit/test tranche may move legacy status-server authentication out of the API-v1 inheritance chain. That cleanup should not be conflated with this runtime acceptance and should not trigger a broad server rewrite.

## 4. Parent runtime closure

The accepted Parent source generates its runtime manifest by walking local dependencies from `index.html`. The generator follows HTML, JavaScript and CSS references, rejects remote runtime dependencies and path escapes, and hashes exact bytes.

Greia's vendor and image-overlay runtime are byte-synchronized to Parent `01301d...`. During the first local acceptance attempt, the generated Parent manifest exposed one stale Greia metadata entry:

```text
src/views_activities.js
bytes = 13323
stale Greia sha256 = d8a5ba84bbe387632d528489f88afe16a5d2836b14f7c74475638f38b451dcb5
actual Parent/vendor/overlay sha256 = f458a5c3cb4a7f21692cefb79e07039d277e14ebb8b27e49441d5ea6e8ec3c02
```

Parent source, `vendor/parent-app/src/views_activities.js`, and `build/overlay/usr/share/greia-parent-app/src/views_activities.js` are the same Git blob. Therefore the defect was isolated to `runtime/parent-app-client.manifest.json`, not the runtime payload. Commit `35b88c79fc10d81ef844df941a3a48321bbce8ab` corrects only that digest.

The previous review concern about a manually omitted `assets/greia-constellation.png` no longer applies to the accepted revision: the current frozen `index.html` does not reference that obsolete asset, and manifest ownership is dependency-derived rather than a hand-maintained runtime list.

## 5. Test-contract correction

During closure review, `tests/test_parent_client_image_integration.py` was found to hard-code the retired Parent revision `75ee2757...`.

That was corrected twice:

1. the stale value was first advanced so current source would not fail immediately;
2. the test was then improved so it verifies the stable invariant instead of naming a particular future Parent commit:

```text
pin.repository == manifest.repository
pin.revision == manifest.revision
runtime_root == /usr/share/greia-parent-app
integration_state == vendored-image-integrity-enforced
```

This prevents every legitimate Parent repin from requiring a policy-test edit merely to change a SHA.

## 6. Documentation/routing correction

The following current authorities were reconciled with the password/device-credential architecture and exact Parent revision:

```text
docs/architecture/PARENT_APP_SOURCE_INTEGRATION.md
docs/architecture/GREIA_PARENT_MANAGEMENT.md
HANDOVER.md
docs/testing/LOCAL_AGENT_START_HERE.md
```

`HANDOVER.md` was deliberately reduced to current continuation state rather than preserving a second historical ledger. R7 is recorded as complete and R8 remains the next blocking architecture family.

The old 2026-09-02 Parent real-runtime procedure still contains historical shared-token bootstrap instructions. Rather than rewriting that historical evidence document, the exact-current replacement is:

```text
docs/testing/2026-09-08_PARENT_PASSWORD_RUNTIME_INTEGRATION_ACCEPTANCE.md
```

That procedure explicitly supersedes the old authentication steps while retaining the older document's still-valid wider physical system-control checks.

## 7. Owner-controlled local attempt at 1f01d413

The first frozen attempt executed the new acceptance procedure and stopped exactly as designed.

Passed:

```text
Greia clean identity at 1f01d4139cc80ec4e0846412f3e7695a0cbc1927
Parent exact identity at 01301d285c6ba2a9a1f2948a9768b821d2536729
Parent node --check
Parent npm test: 77/77 PASS
Parent runtime_manifest.mjs
Greia pin revision/integration_state assertions
```

First failure:

```text
§4 semantic manifest comparison
only src/views_activities.js diverged
```

Per the runbook, the operator did not continue into focused Greia suites, `make verify`, image build, browser, or physical lanes. The evidence root is:

```text
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tmp/PARENT_PASSWORD_RUNTIME_2026-09-08
```

This is a valid REJECTED/STOPPED frozen attempt, not a failed runtime design. It proved the acceptance gate catches exact-byte metadata drift before image construction.

## 8. Exact-current acceptance still required

After pulling a descendant containing `35b88c79...`, the next attempt may reuse the already-green Parent source evidence because the Parent repository SHA is unchanged. It must re-establish the new Greia SHA/clean-tree identity and resume at §4 manifest comparison.

If §4 is green, continue in order:

```text
Greia Parent staging test
Greia Parent image-integration test
Greia password-auth tests
Greia production Parent API tests
vendor integrity verifier
overlay integrity verifier
make verify
canonical image build / installed-runtime integrity
real browser default-password bootstrap
browser close/reopen with persisted device credential
Parent password change: old rejected, new accepted for future bootstrap
independent device revocation
revoked-browser rebootstrap only with current password
negative proof that obsolete shared-token state/UI is absent
wider physical Parent system-control checks
```

Stop on the first new failure. GitHub-hosted Actions are not part of this gate.

## 9. Evidence boundary

Current status is:

```text
PASSWORD BOOTSTRAP SOURCE: IMPLEMENTED
PER-DEVICE CREDENTIAL AUTH SOURCE: IMPLEMENTED
OLD SHARED-TOKEN PRODUCTION FALLBACK: RETIRED IN SOURCE
PARENT PIN 01301d...: IMPLEMENTED
DEPENDENCY-DERIVED RUNTIME MANIFEST: IMPLEMENTED
VENDORED RUNTIME: SYNCHRONIZED
IMAGE OVERLAY RUNTIME: SYNCHRONIZED
PIN/MANIFEST TEST INVARIANT: IMPLEMENTED
CURRENT AUTH/RUNTIME DOCUMENTATION: RECONCILED
PARENT SOURCE GATE AT 01301d...: PASS 77/77
FIRST GREIA LOCAL ATTEMPT AT 1f01d413: STOPPED AT §4 STALE MANIFEST DIGEST
STALE MANIFEST DIGEST: FIXED IN 35b88c79
POST-FIX GREIA FOCUSED/MAKE VERIFY: NOT RUN
CURRENT CANONICAL IMAGE BUILD: NOT RUN
REAL-BROWSER PASSWORD LIFECYCLE: NOT RUN
CURRENT PHYSICAL ACER PARENT ACCEPTANCE: NOT RUN
AUTHENTICATED ENCRYPTED RELEASE TRANSPORT: NOT IMPLEMENTED
```

Do not promote source review or the partial local run into physical or release evidence.

## 10. Relevant Greia commits

The cutover/closure sequence includes:

```text
1f31e2b7e2e3b2326940a8b2828ece0e5c1091a3  advance Parent pin/vendor runtime
25399c491e205e83808ecb3b533632aabc6218a9  synchronize the actual image-overlay runtime
c533f9a6de4c9818a62167acf93ad77c31a24620  repair stale Parent revision assertion
ef49e88023d4900214d49e2666b163edf5de5a10  make the pin test revision-independent
91f058b500f2e1a2d91847a79a07f085e7f5b5c4  reconcile Parent source-integration authority
9a065cd7abe39a53af4d444639028485583422d1  reconcile Parent management auth/runtime architecture
818285807b3ab99cabb61a1fc501ea9afdb80c5b  add exact-current password/runtime acceptance gate
8ad7f0a838d687f0f355192ed739a91b70d4d2f1  refresh current handover
fe5b51bd5e7b81682a81fa60c2b94d24d56adcbd  refresh local-agent testing router
1f01d4139cc80ec4e0846412f3e7695a0cbc1927  record pre-run closure review
35b88c79fc10d81ef844df941a3a48321bbce8ab  fix stale views_activities.js manifest digest
```

Resolve the actual final tested Greia SHA with `git rev-parse HEAD`; documentation commits after the runtime correction are expected descendants.

## 11. Next exact step

On the owner-controlled checkout:

1. pull current Greia `main`;
2. confirm clean tree and record the new exact SHA;
3. keep Parent at exact `01301d285c6ba2a9a1f2948a9768b821d2536729`;
4. resume `docs/testing/2026-09-08_PARENT_PASSWORD_RUNTIME_INTEGRATION_ACCEPTANCE.md` at §4 manifest comparison;
5. if green, continue the focused Greia/integrity/`make verify` source gate;
6. only after that source gate is green, proceed to image/browser/physical lanes.

Do not start the lower-priority legacy-inheritance refactor or transport redesign before obtaining this current source/image/browser evidence, because either would invalidate the candidate and expand the failure surface unnecessarily.
