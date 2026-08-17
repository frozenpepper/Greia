# ADR 0022 — Parent Management API, Client Parity, Pairing, and Privilege Boundary

**Status:** ACCEPTED  
**Date:** 2026-08-17  
**Scope:** Greia Parents, local-network discovery, parent-client authentication, HTML/native client parity, privileged parent operations, and SSH maintenance policy  
**Clarifies:** ADR 0012 parent-management architecture and active-plan R12

## Context

Greia needs a practical parent-management surface before a polished native mobile application is justified. Parents must be able to manage child accounts, Activities, hardware settings, system status, network/maintenance features, backups, and eventually software updates without exposing Linux administration concepts.

The repository already contains a useful `greia_parent` HTTP prototype with profile, progress, customization, and hardware controls. It also contains a separate developer-only SSH/remote-control path. Those are useful foundations, but neither should define the long-term product protocol:

- the parent web page must not become a privileged monolith that directly edits Linux;
- a future phone app must not require a second management protocol;
- SSH must remain an optional maintenance facility, not the Parent App transport;
- one long-lived shared browser token is insufficient as the final paired-device model;
- LAN discovery is useful, but a LAN is not a trusted security boundary.

## Decision

### 1. Greia Parent Service is the durable product boundary

Greia exposes one versioned **Greia Parent API**. The first supported client is a small responsive HTML application served by Greia itself.

A future iOS, Android, desktop, or other parent client MUST use the same semantic API, discovery, pairing, authentication, authorization, capability, and long-operation contracts rather than acquiring special Linux-side powers.

Conceptually:

```text
Greia Parents HTML client
Future phone/desktop client
            │
            │ same versioned protocol
            ▼
      Greia Parent API
            │
            ├── profiles
            ├── Activities
            ├── progress/status
            ├── settings
            ├── paired devices
            └── maintenance requests
                    │
                    ▼
         typed Greia services/brokers
                    │
                    ▼
           Linux/platform adapters
```

The HTML application is therefore a client, not the authority implementation.

### 2. API semantics are versioned and transport-neutral

The initial namespace is:

```text
/api/v1
```

JSON is the client-facing representation for API v1.

The API MUST expose stable semantic resource IDs and typed errors. It MUST NOT expose Linux paths, arbitrary command lines, implementation-specific X11/DRM details, raw package-manager commands, or host credentials as its public model.

Long-running operations such as Activity installation, system update, backup/restore, or package verification SHOULD use an operation resource with explicit state/progress rather than keeping an HTTP request open indefinitely.

### 3. Capability discovery is part of the protocol

Greia hardware and platform features vary. Clients must not infer support from CPU architecture, device model, or UI heuristics.

The Parent API exposes semantic capability availability. A client may therefore show, hide, or disable features such as:

```text
profiles.manage
activities.install
settings.input
settings.display
settings.audio
network.manage
backup.manage
maintenance.ssh
```

A false/unavailable capability is not permission to emulate the operation through shell commands.

### 4. Local discovery uses a Greia-specific mDNS service

Normal network-capable Greia images advertise:

```text
_greia-parent._tcp.local
```

The service record identifies the Parent API port/version/path but carries no authentication secret.

mDNS/Bonjour is a convenience discovery mechanism, not identity or authorization. Pairing material must remain sufficient to connect when multicast discovery is unavailable.

### 5. Parent clients receive independent revocable credentials

The final pairing model is **per-device**.

Each parent client receives its own high-entropy credential. Greia stores only a one-way verifier/digest where practical and exposes only non-secret device metadata to other clients.

Parents can list and revoke paired devices independently. Losing one phone must not require rotating every parent's credential.

One global forever-token shared by all clients is rejected as the final design.

### 6. Pairing requires explicit local approval in the final product

The intended first-pairing flow is:

```text
parent chooses "Add a Greia"
→ client discovers nearby Greia or follows local connection information
→ parent opens Pair a device on the Greia itself
→ Greia shows short-lived QR challenge + numeric fallback
→ client presents the challenge
→ Greia displays the requesting device and asks Allow / Deny
→ successful client receives its own revocable credential
```

The current long-lived token endpoint may remain temporarily as a **PROVISIONAL development/bootstrap mechanism** while the local Greia pairing UI is implemented. It is not the production security design.

Pairing challenges must be bounded, short-lived, single-purpose, and must not be logged.

### 7. LAN transport is not automatically trusted

The current `http://<device>:8766` implementation is explicitly **PROVISIONAL**.

Production parent credentials MUST NOT be considered safe merely because traffic remains on a home LAN. Before production pairing is accepted, Greia requires authenticated encryption for the parent channel, with device identity bound during pairing so a client can detect connecting to the wrong endpoint.

The exact TLS/device-certificate mechanism is intentionally left to a focused security design/implementation tranche. This ADR fixes the requirement, not an unreviewed certificate lifecycle.

### 8. Parent API and privileged authority remain separate

The Parent HTTP process continues to run with narrow unprivileged authority.

Operations requiring root/system authority MUST cross a small typed Greia-owned privileged boundary. Examples include:

```text
maintenance.ssh.enable
maintenance.ssh.disable
maintenance.ssh.authorized_key.replace
activities.install/update/remove
system.update
backup.restore where privileged placement is required
network system configuration
power/recovery operations
```

The privileged service accepts validated semantic requests, not arbitrary shell text, argv arrays, paths chosen by clients, package-manager commands, or generic `sudo`.

The Parent API must reuse existing platform services such as ProfileStore, Hardware Settings/HAL, future R10 Package Manager, R11 Backup Service, and update/recovery services. It must not implement parallel versions of those systems.

### 9. SSH is optional parent-controlled maintenance, disabled by default

Normal/release Greia MUST NOT enable SSH merely to support Greia Parents.

When the typed maintenance service is implemented, a parent may explicitly enable SSH. The intended release policy is:

- SSH off by default;
- host keys created only when SSH is deliberately enabled, unless a later security ADR chooses another bounded lifecycle;
- root SSH login disabled;
- password SSH authentication disabled;
- key-based authentication only;
- dedicated administrative identity such as `greiaadmin`;
- parent UI can disable SSH and replace/revoke authorized key material;
- developer profiles remain a separate development mechanism.

Greia Parents itself continues to use the Parent API, not SSH.

### 10. Implementation may proceed in foundations without falsely closing R12

The active plan currently places full parent integration at R12 because Activity package management and backup/restore depend on R10/R11.

A limited foundation may be implemented earlier after the relevant shared services exist, provided it only:

- establishes API versioning, discovery, client parity, credential storage, and pairing foundations;
- exposes existing unprivileged profile/status/settings functionality;
- honestly reports later capabilities as unavailable;
- does not create substitute package/backup/update systems;
- does not add broad privilege.

R12 closure still requires its documented prerequisites and the complete typed privileged-management surface.

## Initial API-v1 foundation

The first implementation tranche establishes:

```text
GET    /api/v1/meta
GET    /api/v1
GET    /api/v1/system
GET    /api/v1/profiles
POST   /api/v1/profiles
PATCH  /api/v1/profiles/{id}
DELETE /api/v1/profiles/{id}
GET    /api/v1/activities
GET    /api/v1/settings/hardware
PUT    /api/v1/settings/hardware
POST   /api/v1/settings/hardware/reset
GET    /api/v1/progress
GET    /api/v1/devices
DELETE /api/v1/devices/{id}

POST   /api/v1/pairing/bootstrap   # provisional only
```

Activity installation, audio/network management, SSH, backup/restore and system update are intentionally not implemented by this foundation.

## Consequences

Positive:

- the prototype HTML interface exercises the same semantic protocol a native app can later use;
- product requirements can mature without rewriting Greia's management architecture;
- SSH remains optional and independently securable;
- parent privilege stays narrow and auditable;
- per-device revocation becomes possible;
- hardware-specific details remain behind HAL/services;
- low-resource Greia can keep a small dependency-free local web client.

Costs:

- API compatibility becomes a maintained product contract;
- pairing/device identity and encrypted local transport require dedicated security work;
- long operations require explicit job/state design;
- the web frontend can no longer bypass missing backend functionality by directly editing host state.

## Rejected alternatives

### Make the browser page the backend contract

Rejected. A future native app would require scraping/reimplementing HTML behavior and privileged logic would accumulate in one server module.

### Use SSH as the Parent App protocol

Rejected. SSH is a maintenance tool with much broader authority than the product needs and would force release machines to expose an unnecessary service.

### Give every parent device the same persistent token

Rejected. It prevents independent revocation and turns one lost device into a household-wide credential rotation.

### Trust any device on the local Wi-Fi

Rejected. Local networks contain guests, compromised devices, and traffic observation risks.

### Implement package/network/backup logic directly inside `greia_parent`

Rejected. Those are shared platform services with their own integrity/recovery contracts.

## Verification obligations

Before the foundation is described as source-verified:

- credential state rejects malformed/oversized input;
- raw issued tokens are not persisted;
- independent revocation works;
- unauthenticated API access fails except explicit discovery/bootstrap endpoints;
- API Activity output does not leak package filesystem paths;
- mDNS advertises the correct service without secrets;
- normal image composition still excludes developer SSH;
- HTML client performs management through `/api/v1`;
- existing parent/profile/hardware behavior remains compatible.

Before production parent pairing is accepted:

- authenticated encrypted transport;
- Greia-local short-lived pairing challenge;
- explicit local Allow/Deny;
- replay/expiry/credential-revocation tests;
- browser/mobile reconnect and discovery tests;
- resource measurements on the C0 reference floor.
