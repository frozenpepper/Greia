# Greia — Current Engineering Handover

**Updated:** 2026-09-08  
**Canonical repository/branch:** `frozenpepper/Greia` / `main`  
**Version:** `0.13.0-phase0-dev`  
**Primary blocking platform phase:** **R8 — Raspberry Pi 400 / Pi 500 ARM64 board and image adapters**  
**Public-source readiness:** **IN PROGRESS**  
**Ordinary-family release:** **NOT READY**

This file is current-state routing only. Historical implementation detail belongs in Git history, dated reviews, testing records, and the append-only active architecture plan.

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

## 2. Platform state

R7 display/session/trusted-chrome work is complete and has recorded physical Acer evidence. The next blocking architecture family is R8 ARM64/Pi board and image support.

Current catalogue assertions must remain discovery-based. Do not freeze a first-party Activity count into new architecture or release gates.

The Parent authentication/runtime work below is a cross-cutting release-readiness tranche. It does not replace or skip R8 or later platform phases.

## 3. Parent client authority and frozen runtime

Maintained Parent browser source:

```text
frozenpepper/Greia-Parent-App-Html
```

Exact accepted Parent revision integrated into Greia:

```text
01301d285c6ba2a9a1f2948a9768b821d2536729
```

Production runtime chain:

```text
accepted Parent revision
  -> runtime/parent-app-client.toml
  -> runtime/parent-app-client.manifest.json
  -> vendor/parent-app/
  -> build/overlay/usr/share/greia-parent-app/
  -> /usr/share/greia-parent-app in the built image
```

Current pin contract:

```text
revision = 01301d285c6ba2a9a1f2948a9768b821d2536729
integration_state = vendored-image-integrity-enforced
```

The vendor and image-overlay copies are synchronized to that frozen Parent revision. The installed service verifies the browser runtime against the committed pin/manifest before serving it.

Future repins use only:

```bash
python3 tools/update_parent_client_pin.py \
  --parent-root /path/to/Greia-Parent-App-Html \
  --revision <exact-reviewed-parent-sha>
```

Do not manually advance the pin, manifest, vendor tree and image overlay as separate operations.

## 4. Parent authentication contract

The old human-entered shared `parent-pairing-token` model is retired from API-v1 and installed production.

Current flow:

```text
Parent enters Greia password once
  -> POST /api/v1/pairing/bootstrap
     {password, device_name}
  -> Greia verifies MainCredential locally
  -> Greia issues one revocable per-device credential
  -> browser stores only that device credential
  -> ordinary API requests use the device credential
```

Fresh-system credential remains:

```text
username: greia
password: greia
```

Parents can change that password from Parent management. Existing authorized browsers use independent device credentials and can be revoked separately.

Retired API-v1/production paths include:

```text
parent-pairing-token
X-Pip-Token
?token=<shared secret>
greia_parent=<shared secret> legacy cookie
pairing_token bootstrap input
filesystem-token retrieval as a user workflow
```

`ParentApiApplication` rejects those legacy transports and uses only device-scoped authorization. The older standalone `ParentStatusApplication` retains a separate compatibility token path for its legacy server only; that server is not production API-v1 authority.

The API-v1 wire names `/pairing/bootstrap` and `pairing_required` are compatibility vocabulary, not evidence that a shared token remains supported.

## 5. Authentication/runtime implementation state

Implemented in source and committed:

```text
password bootstrap -> per-device credential
independent Parent-device revocation
bounded failed-password limiter in production
legacy shared-token rejection in API-v1
stale legacy shared-token state retirement on API-v1 startup
real HTTP negative regression for X-Pip-Token / legacy cookie / query token / pairing_token input
separate legacy-status compatibility regression
API-v1 authentication ownership regression
exact Parent runtime revision pin
exact dependency-derived runtime manifest
synchronized vendor runtime
synchronized image-overlay runtime
installed-runtime integrity verifier
single-operation atomic Parent repin tool + regression coverage
```

The real HTTP negative regression is:

```text
tests/test_parent_api_legacy_token_negative.py
```

It proves retired shared-token transports fail at the actual API-v1 handler boundary and that only the supported device credential transports succeed.

## 6. Evidence boundary — do not overclaim

Already established from earlier owner-controlled evidence:

```text
PARENT SOURCE AT 01301d...:
  node syntax: PASS
  npm test: 77/77 PASS
  runtime_manifest.mjs: PASS

FIRST GREIA FROZEN ATTEMPT:
  stopped correctly at manifest comparison
  first failure was one stale src/views_activities.js digest
  stale digest was corrected without changing Parent runtime bytes
```

Current later Greia source state contains additional repin/authentication regressions. Those later tests have been **committed but not executed in an owner-controlled exact-current checkout in this connector session**.

Therefore current evidence remains:

```text
CURRENT GREIA FOCUSED AUTH/RUNTIME GATE: PENDING
CURRENT make verify: PENDING
OFFICIAL IMAGE BUILD FROM CURRENT DESCENDANT: PENDING
REAL BROWSER PASSWORD/RELOAD/CHANGE/REVOKE: PENDING
CURRENT PHYSICAL PARENT SYSTEM-CONTROL ACCEPTANCE: PENDING
```

A committed test is not a PASS.

## 7. One authoritative Parent acceptance protocol

Use only:

```text
docs/testing/2026-09-08_PARENT_UNIFIED_AUTH_RUNTIME_ACCEPTANCE.md
```

This is now the single execution authority for the Parent authentication/runtime tranche. It unifies:

```text
source identity
exact frozen Parent source tests
manifest regeneration + equality
9 focused Greia Parent suites
vendor + image-overlay integrity
make verify
canonical image build
installed runtime integrity
LAN discovery
default-password bootstrap
wrong-password rejection
browser credential persistence
Parent password change
independent device revocation
fresh rebootstrap after revocation
real HTTP rejection of every retired shared-token transport
production service sandbox sanity
physical volume/Wi-Fi/SSH/other advertised setting checks
profile/Activity-policy smoke test
owner-state restoration
final transport-security blocker and report
```

The older files remain historical only:

```text
docs/testing/2026-09-08_PARENT_PASSWORD_RUNTIME_INTEGRATION_ACCEPTANCE.md
docs/testing/2026-09-02_PARENT_REAL_RUNTIME_FINAL_ACCEPTANCE.md
```

Do not combine their obsolete token instructions with the unified procedure.

## 8. Current exact next step

On the owner-controlled checkout:

```bash
git fetch origin
git pull --ff-only
git status --short
git rev-parse HEAD
git rev-parse origin/main
```

Require a clean relevant tree and `HEAD == origin/main`.

Keep the Parent repository at exactly:

```text
01301d285c6ba2a9a1f2948a9768b821d2536729
```

Then execute from the beginning:

```text
docs/testing/2026-09-08_PARENT_UNIFIED_AUTH_RUNTIME_ACCEPTANCE.md
```

Stop on the first failure and return the evidence root plus the final report template from that protocol.

Do not edit source during the frozen attempt.

## 9. Parent/API ownership boundaries

Primary current owners:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
vendor/parent-app/
build/overlay/usr/share/greia-parent-app/
tools/update_parent_client_pin.py
src/greia_parent/static_client.py
src/greia_parent/parent_client_integrity.py
src/greia_parent/password_auth.py
src/greia_parent/protocol.py
src/greia_parent/api_server.py
src/greia_parent/package_api.py
src/greia_parent/update_api.py
src/greia_parent/production_api.py
src/greia_platform/main_credential.py
tests/test_update_parent_client_pin.py
tests/test_parent_api.py
tests/test_parent_api_legacy_token_negative.py
tests/test_parent_auth_ownership.py
tests/test_parent_legacy_status_auth.py
```

The Parent HTTP process remains unprivileged. Never solve unavailable functionality by giving it generic root/sudo/shell authority.

Production Wi-Fi remains fail-closed: real iwd only, and `network.manage=false` when the installed unprivileged composition cannot genuinely manage it.

Speaker volume/mute remains a typed desired-state path. The Parent HTTP process does not own ALSA; the child hardware session applies system-control state.

## 10. Remaining Parent release blocker

Current transport remains provisional HTTP.

Password bootstrap fixes the product authentication model, but Parent password and device bearer credentials are not ordinary-family release-safe over unauthenticated plaintext LAN transport.

Ordinary-family Parent release therefore remains blocked until Greia has accepted:

```text
authenticated encrypted transport
Greia endpoint/device identity
reviewed trust/onboarding lifecycle
```

The solution must preserve the simple Parent-password workflow. Do not reintroduce hidden filesystem tokens, mandatory QR/PIN ceremonies, or ad-hoc custom application crypto as a workaround.

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

A successful HTTP response is not proof that physical hardware changed. A later SHA does not inherit earlier physical evidence unless the relevant bytes and acceptance contract explicitly establish equivalence.
