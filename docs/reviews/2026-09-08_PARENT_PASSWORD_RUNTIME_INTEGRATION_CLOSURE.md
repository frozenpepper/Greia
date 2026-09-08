# Parent password runtime integration — source/image closure review

**Date:** 2026-09-08  
**Scope:** Greia Parent authentication migration and exact Parent browser runtime integration  
**Evidence class:** repository/source review and committed integration only; local automated, image-build and physical-browser evidence remain pending

## 1. Result

The migration from the old human-entered shared Parent pairing token to Greia-password bootstrap is now coherent across the maintained Parent client, Greia API, Greia runtime pin, vendored browser runtime, and the actual image overlay.

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

Greia's committed manifest for `01301d...` contains the exact accepted runtime closure. The vendor and image-overlay runtime were synchronized to those bytes.

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

## 7. Exact-current acceptance required

No local command execution is claimed for the current descendant from this connector-only work.

The new acceptance procedure requires, in order:

```text
Parent exact-SHA node syntax checks
Parent npm test
Parent dependency-derived runtime-manifest regeneration
semantic manifest equality with Greia's committed manifest
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

The run stops on the first failure. GitHub-hosted Actions are not part of this gate.

## 8. Evidence boundary

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
EXACT-CURRENT LOCAL TEST EXECUTION: NOT RUN
CURRENT CANONICAL IMAGE BUILD: NOT RUN
REAL-BROWSER PASSWORD LIFECYCLE: NOT RUN
CURRENT PHYSICAL ACER PARENT ACCEPTANCE: NOT RUN
AUTHENTICATED ENCRYPTED RELEASE TRANSPORT: NOT IMPLEMENTED
```

Do not promote source review into physical or release evidence.

## 9. Relevant Greia commits

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
```

Resolve the actual final tested Greia SHA with `git rev-parse HEAD`; documentation commits after the runtime cutover are expected descendants.

## 10. Next exact step

On an owner-controlled local checkout, execute:

```text
docs/testing/2026-09-08_PARENT_PASSWORD_RUNTIME_INTEGRATION_ACCEPTANCE.md
```

against current Greia `main` and exact Parent revision `01301d285c6ba2a9a1f2948a9768b821d2536729`.

Do not start the lower-priority legacy-inheritance refactor or transport redesign before obtaining this current source/image/browser evidence, because either would invalidate the candidate and expand the failure surface unnecessarily.
