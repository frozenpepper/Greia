# ADR 0022 — Parent Management API, Client Authentication, and Privilege Boundary

**Status:** ACCEPTED  
**Date:** 2026-08-17  
**Authentication amendment:** 2026-09-08  
**Scope:** Greia Parents, local-network discovery, Parent-client authentication, HTML/native client parity, privileged Parent operations, and SSH maintenance policy  
**Clarifies:** ADR 0012 parent-management architecture and active-plan R12

## Context

Greia needs a practical Parent-management surface that does not expose Linux administration concepts and does not tie the product to one browser implementation. The Parent web application and any future native client therefore consume the same semantic Greia Parent API.

The first authentication prototype used one long-lived shared pairing token. That proved to be the wrong product boundary: the token was filesystem state hidden from parents, required shell knowledge to retrieve, and provided no human benefit over the Parent password Greia already owns. Retaining it as a compatibility credential would also preserve an unnecessary second authentication secret indefinitely.

A LAN remains an untrusted transport boundary. Replacing the hidden token with the Parent password fixes the authentication workflow, not plaintext transport security.

## Decision

### 1. Greia Parent API is the durable product boundary

Greia exposes one versioned **Greia Parent API** under `/api/v1`. The dependency-light HTML application is a client of that API. Future iOS, Android, desktop, or other Parent clients use the same semantic resources and authentication model rather than acquiring special Linux-side powers.

The network API must not become a parallel implementation of profiles, package management, backup, networking, audio, updates, or other platform services.

### 2. API semantics are versioned and transport-neutral

API v1 uses JSON representations and typed errors. It exposes semantic resource IDs, not arbitrary shell commands, Linux paths, package-manager commands, host credentials, or implementation-specific graphics/input details.

Long-running mutations should use explicit operation resources rather than holding an HTTP request open indefinitely.

### 3. Capability discovery is part of the contract

Clients must follow the API capability map. Hardware/service detection alone is insufficient to advertise a mutation: if the installed Parent service cannot safely complete the semantic operation under its actual authority, the capability is false.

A false capability is never permission for a browser-side Linux workaround.

### 4. Discovery does not authorize

Greia may advertise `_greia-parent._tcp.local` and clients may use bounded LAN discovery/fallback probing to find Parent API endpoints. Discovery metadata carries no secret and grants no management authority.

### 5. The Parent password is the human bootstrap credential

An unpaired browser authorizes its first device identity with:

```text
POST /api/v1/pairing/bootstrap
{
  "password": "<Parent password>",
  "device_name": "<client label>"
}
```

The password is verified only through Greia's canonical `MainCredential` authority. The browser must not persist it.

The initial owner-approved credential is `greia` / `greia`; parents may change the password through the existing Parent-password management path. The stored authority is a bounded password digest, not plaintext.

Repeated failed bootstrap attempts are rate-limited per client address with bounded in-memory state. A successful verification clears that client's failure history.

### 6. Successful bootstrap becomes an independent revocable device identity

After password verification Greia issues a fresh high-entropy per-device credential. Normal management requests use:

```text
Authorization: Bearer <device credential>
```

Greia stores only verifier/hash material for issued device credentials where practical. Raw issued credentials are returned only at creation time.

Parents can list and revoke paired devices independently. Losing or revoking one device must not rotate every other Parent client.

The Parent password is therefore an authorization/bootstrap secret, not the ordinary bearer credential sent on every management request.

### 7. The old shared pairing-token model is retired, not transitional

The following are rejected from the production Parent API:

- `parent-pairing-token` as a durable/shared authentication authority;
- `X-Pip-Token` fallback authorization;
- token query URLs such as `/pair?token=...` on the production service;
- shared-token authentication cookies;
- `/usr/local/bin/greia-parent-token` or any equivalent shell requirement for ordinary parents;
- accepting both password and old token during a compatibility period.

Production startup removes stale `parent-pairing-token` state and must not recreate it.

The reason for rejecting backwards compatibility is architectural: leaving the old secret valid would keep an invisible alternate authentication path and make the migration impossible to reason about or finish.

### 8. LAN transport remains provisional until authenticated encryption lands

The current `http://<device>:8766` transport is explicitly **PROVISIONAL**.

The Parent password and device credentials must not be considered ordinary-family release-safe merely because traffic remains on a home LAN. Before release acceptance, Greia requires authenticated encrypted transport plus a reviewed device/endpoint identity lifecycle that prevents credential interception and wrong-endpoint impersonation.

That transport work must preserve the simple Parent-password bootstrap. It must not reintroduce hidden tokens, shell commands, or mandatory Linux administration as a security ceremony.

### 9. Parent API and privileged authority remain separate

`greia-parent.service` remains narrowly unprivileged. Operations requiring root/system authority cross a small typed Greia-owned privileged boundary.

Good privileged vocabulary is semantic, for example:

```text
maintenance.ssh.enable
maintenance.ssh.disable
activities.install
system.update
network.configure
backup.restore
```

Rejected privileged vocabulary includes arbitrary command strings, argv arrays, client-selected filesystem writes, generic `sudo`, or raw package-manager access.

The Parent API reuses platform services such as ProfileStore, Hardware Settings/HAL, Activity/package services, backup, update, and maintenance services. It does not fork those systems inside HTTP handlers.

### 10. SSH remains optional maintenance, disabled by default

Greia Parents does not use SSH as its transport. Normal release images do not enable SSH merely to support the Parent app.

Owner decision 2026-10-30 supersedes the former key-only restriction: the explicit Parent-controlled switch enables SSH with login `greia` and password `greia`, including on normal images. SSH remains off by default, root login is disabled, and enable/disable remain typed maintenance operations. This does not enable the separate developer remote-control surface.

### 11. Foundations may land without falsely closing later platform phases

Parent API/client foundations may expose existing safe functionality and honestly advertise unavailable later capabilities. They must not create substitute package, backup, update, network, or privileged systems merely to make the UI appear complete.

## API-v1 authentication foundation

Public/bootstrap endpoints:

```text
GET  /api/v1/meta
POST /api/v1/pairing/bootstrap
```

All ordinary management resources require a valid per-device bearer credential, including the API index, system state, profiles, activities, settings, progress, paired devices, and other enabled resources.

## Security/storage invariants

Source and tests must preserve these invariants:

- password bootstrap verifies against `MainCredential` only;
- the Parent password is not returned, logged, or browser-persisted;
- main credential state stores only bounded digest material with restrictive permissions;
- final-path symlink substitution for credential state is rejected;
- failed password bootstrap is bounded/rate-limited without unbounded per-address allocation;
- raw device credentials are not persisted by the server;
- device credentials are independently revocable;
- unauthenticated management fails;
- retired shared-token headers/cookies/routes do not authorize management;
- stale token state is removed by the installed production composition;
- no secret is advertised through discovery metadata.

## Consequences

Positive:

- parents use one understandable human credential they already know;
- successful login immediately becomes a revocable device identity rather than a household-wide shared bearer secret;
- browser and future native clients share one protocol;
- the password is not kept in browser storage or sent on every management call;
- privilege remains narrow and auditable;
- the unusable shell/token pairing workflow is removed rather than papered over.

Costs and remaining work:

- the pragmatic home-LAN HTTPS transport is an owner-approved convenience/security tradeoff;
- API compatibility and device-credential lifecycle remain maintained product contracts;
- long operations and privileged management still require their planned typed service boundaries;
- physical multi-device/revocation testing remains necessary in image acceptance.

## Rejected alternatives

### Keep the shared token as a fallback

Rejected. A fallback would retain the exact hidden, global authentication authority this migration is intended to eliminate.

### Use the Parent password as every-request bearer auth

Rejected. It would repeatedly expose the human password, make independent device revocation impossible, and couple all clients to one credential.

### Require an additional QR/PIN/Allow ceremony for ordinary bootstrap

Rejected as the default architecture. The owner-selected Parent password is the explicit authorization action. A future transport may use device-identity/trust UX where necessary, but it must not create a second human secret or mandatory hidden-token workflow.

### Trust any device on local Wi-Fi

Rejected. Discovery and network proximity are not authorization.

### Use SSH as the Parent protocol

Rejected. SSH exposes broader authority than the product needs and would make a maintenance service a release dependency.

### Implement platform operations directly inside `greia_parent`

Rejected. Those operations belong to shared platform services and typed privileged boundaries.

## Verification obligations

Before this authentication migration is described as source-verified at an exact head:

- default and changed Parent passwords bootstrap correctly;
- wrong passwords fail and are rate-limited;
- limiter state stays bounded and expires correctly;
- old shared-token authorization is rejected;
- device bearer authorization and independent revocation work;
- main credential digest state is bounded, mode `0600`, non-plaintext, atomic, and symlink-safe;
- installed production startup removes stale token state;
- the Parent browser sends only `{password, device_name}` for bootstrap and persists only the returned device credential;
- the exact Parent browser runtime revision/integrity manifest is pinned in Greia.

Before ordinary-family production Parent authentication is accepted:

- installed LAN endpoint uses HTTPS and localhost-only HTTP; certificate persists across updates; browsers can connect after handling the self-signed warning;
- browser/device reconnect and independent revocation are proven on real hardware;
- password-change → new bootstrap behavior is proven;
- image install/upgrade removes obsolete token helper/state;
- resource measurements remain acceptable on the C0 reference floor.

## Amendment 2026-10-30: Parent browser client source merged into this repository

The browser Parent client no longer lives in the separate private repository `frozenpepper/Greia-Parent-App-Html`. Its source is the `parent-app/` directory of `frozenpepper/Greia`, which is now the single editable source; the former `vendor/parent-app/` provenance copy and `tools/stage_parent_app.py` are removed. Earlier text of this ADR that speaks of a separate Parent client repository or a pinned Parent commit is accepted history and is superseded by this amendment where it differs.

Unchanged: the decisions above (versioned `/api/v1`, Parent-password bootstrap, per-device credentials, privilege boundary), the frozen image payload `build/overlay/usr/share/greia-parent-app/`, the `runtime/parent-app-client.toml` pin and `runtime/parent-app-client.manifest.json` formats, and the on-device integrity check (`greia-parent.service` `ExecStartPre`). Greia still never serves a moving source tree: it serves only the integrity-checked frozen runtime closure.

Changed:

- the pin `repository` is `frozenpepper/Greia:parent-app` and its `revision` is the Git tree id of the committed `parent-app/` directory (`git rev-parse HEAD:parent-app`), not a commit id of another repository;
- workflow: edit `parent-app/`, run `make parent-app-test`, commit, run `python3 tools/update_parent_client_pin.py`, then commit the pin, manifest and overlay; `--check` reports drift and `tests/test_parent_client_image_integration.py` fails on drift;
- client-specific rules live in `parent-app/AGENTS.md`, under the repository-root `AGENTS.md`;
- the Parent client still ships only in full-system images: a Python application update cannot change it.

See `docs/architecture/PARENT_APP_SOURCE_INTEGRATION.md` for the exact procedure.
