# Greia Activity Ecosystem — Architecture Synthesis

**Status:** living architecture synthesis; implementation future/incremental  
**Date:** 2026-08-17  
**Normative owners:** ADR 0023 and ADR 0024  
**Product owner:** `docs/product/ACTIVITY_ECOSYSTEM_AND_DISTRIBUTION.md`  
**Exact future package/catalogue APIs:** source/R10 decisions when implemented

## 1. Purpose

This document translates the accepted open-ecosystem decisions into a concrete system shape for future R10/package/catalogue work without inventing implementation APIs before they exist.

The key architectural separation is:

```text
authoring  ≠  packaging  ≠  provenance/trust  ≠  distribution  ≠  catalogue review  ≠  commerce
```

Those concerns interact but must not collapse into one store-specific pipeline.

## 2. Ecosystem planes

Greia's eventual Activity ecosystem has six logical planes.

### A. Authoring plane

Human or agent authors use public repository contracts:

```text
Activity docs + examples + authoring skill
                 ↓
        public Greia Activity APIs
                 ↓
       local/dev execution helpers
                 ↓
      deterministic validation
```

No official-catalogue credential is required to author or validate an Activity.

### B. Package plane

A future R10 package service turns an authored Activity into or consumes a versioned `.greiaactivity` package.

The package carries the technical material required for installation, such as:

- stable Activity identity/version;
- runtime/entrypoint metadata;
- capability/permission declarations;
- compatibility requirements;
- payload/assets;
- integrity metadata;
- license/notice metadata;
- provenance/signature material where applicable.

Exact fields remain future source/ADR-owned implementation details.

### C. Provenance/trust plane

Greia records what it can establish about a package's source and review path independently of the package's price or source-code license.

Conceptually:

```text
package bytes
    ↓
integrity verification
    ↓
signature / publisher provenance
    ↓
source/channel metadata
    ↓
review evidence / policy level
    ↓
parent-facing trust presentation
```

A structurally valid independently obtained package is not automatically official-catalogue approved. Conversely, a paid package is not inherently more trusted than a free package.

### D. Distribution plane

Multiple package sources can feed the same package service:

```text
Official Greia Catalogue ─┐
community repository      ├──→ Parent-approved Package Service → Activity Registry
removable media           │
explicit local import     ┘
```

The Package Service owns validation/transactional activation. Distribution sources do not get separate privileged installers.

### E. Catalogue plane

The Official Greia Catalogue adds services around packages:

- publisher identity;
- metadata/discovery;
- editorial/age categorization;
- privacy and child-safety review;
- compatibility/resource evidence;
- signed update channels;
- quality review;
- optional commercial entitlement/distribution.

Catalogue approval is therefore additional evidence/policy, not a different Activity runtime.

### F. Commerce/entitlement plane

If paid Activities are introduced, payment remains outside the child Activity runtime.

Conceptually:

```text
parent catalogue client
        ↓
parent authentication / purchase
        ↓
commercial entitlement record
        ↓
package/update authorization
        ↓
normal Greia Package Service
        ↓
installed Activity
```

The installed Activity still launches through the same Greia runtime/lifecycle/storage/input/permission architecture as a free Activity.

## 3. Package Service is the single installation authority

Greia must not implement:

- one installer for official store content;
- another for USB packages;
- another in the native phone app;
- another in community tooling.

All parent-authorized package installation/update/removal converges on one typed R10 Package Service.

This preserves:

- manifest validation;
- path safety;
- compatibility checks;
- trust/provenance evaluation;
- permissions;
- transactional activation;
- rollback;
- Activity registry integrity;
- uninstall/data-separation behavior.

A future native Greia Parents app asks the Parent API to initiate the same package operation. It never copies package files directly into privileged installation roots.

## 4. Distribution source abstraction

A future implementation should model package acquisition as a narrow source abstraction rather than embedding HTTP/store assumptions in Package Manager.

Conceptually:

```text
ActivityPackageSource
    acquire(package_ref) -> bounded package stream/file + source metadata

implementations may include:
    OfficialCatalogueSource
    RemovableMediaSource
    LocalImportSource
    future CommunityIndexSource
```

This is an architectural shape, not a current Python interface.

The package verifier/installer consumes the acquired package through one common contract.

## 5. Trust/provenance model must be typed and multi-dimensional

Avoid one `trusted = true/false` flag.

At minimum the architecture needs independent facts for:

```text
origin/source
publisher identity confidence
signature/integrity status
official review level
compatibility result
permission/network risk summary
license metadata
commercial entitlement state
```

Parent UI can synthesize these facts into understandable language, but source code should preserve the dimensions so a future policy change does not require parsing human labels.

## 6. Independent installation does not mean unsafe installation

The independent lane remains parent-controlled and fail-closed.

A package from removable media or a community website still goes through:

1. bounded acquisition;
2. path/archive safety validation;
3. manifest/API/runtime compatibility validation;
4. integrity/provenance inspection;
5. clear parent trust presentation;
6. explicit approval;
7. transactional install/activation;
8. normal sandbox/runtime supervision.

Greia never executes Activity code directly from removable media.

## 7. Official catalogue trust

The official catalogue should be able to issue/package metadata which Greia can verify offline after download, so catalogue trust does not require a live network connection on every Activity launch.

The future signing design should separate at least:

- publisher signing/identity;
- Greia catalogue/review attestation;
- package integrity;
- update-channel authorization/revocation.

The exact key hierarchy, rotation, expiry, revocation and recovery design remains future security/R10 work.

Do not encode “official” merely as a package path or server hostname.

## 8. Offline entitlement principle

If Greia sells catalogue content, an already entitled/installed Activity should not require the child machine to contact a payment server every time it launches.

The target direction is a bounded locally verifiable entitlement/install state with network access required only for operations such as acquisition, restoring purchases, update checks or policy-required renewal where a future business model explicitly chooses one.

The initial preferred product direction remains purchase/convenience rather than dependency on recurring online authentication.

Exact entitlement cryptography and refund/revocation behavior remain future commerce/security design.

## 9. Parent API integration

ADR 0022 remains authoritative for clients.

Future Activity ecosystem operations should appear as semantic Parent API capabilities/resources rather than app-specific store RPCs.

Conceptually:

```text
activities.read
activities.install
activities.update
activities.remove
catalogue.read                 # future
catalogue.entitlements.read    # future
catalogue.purchase             # future, parent authenticated
```

These names are illustrative only until `src/greia_parent/protocol.py` implements them.

The HTML client and any paid native app use the same semantic operations.

## 10. Child runtime is commerce-blind

Ordinary Activity launch/runtime APIs should not expose payment-provider tokens, app-store credentials or catalogue purchasing authority.

An Activity may receive ordinary platform state required for its own content model, but it should not need to know how it was purchased.

If optional downloadable content is ever supported, it requires a separate child-safety/package design; do not smuggle commerce into normal Activity network permissions.

## 11. Author/publisher identity

Stable Activity ID remains package identity. Official distribution additionally needs stable publisher identity.

The architecture must prevent an unrelated publisher from silently taking over updates for another publisher's Activity ID merely because a higher version number exists.

Future update acceptance therefore needs a relationship between:

```text
activity_id
publisher identity / signing authority
installed provenance
allowed update channel
version
```

The exact representation remains R10/signing work.

## 12. Licensing metadata

ADR 0024 separates Greia platform licensing from Activity author licensing.

Future package metadata should support standard machine-readable identifiers where practical, preferably SPDX-compatible expressions, plus packaged human-readable license/notice files where required.

Do not infer legal rights from catalogue price or approval state.

Current `activity.toml` does not yet expose a frozen license field; implementation must not invent one outside the future package-schema tranche.

## 13. Agent authoring architecture

Agent support is not a separate runtime.

The durable interface is documentation + schemas/APIs + validators:

```text
canonical docs/skill
       ↓
agent plans/writes Activity
       ↓
normal source tree
       ↓
normal validator/tests
       ↓
normal package tool
```

This is preferable to a special “AI Activity format” because it keeps human and agent work interoperable and reviewable.

Agent instructions should expose architectural intent and common failure modes, while deterministic tools own structural/package validation.

## 14. Resource/security implications

Catalogue support must not compromise the Acer/C0 floor.

The child OS should not require a permanently resident heavy store process. Catalogue browsing may be parent-only/on-demand, and package metadata/index caches must be bounded.

Network parsing must be bounded and treated as untrusted input. Downloaded packages remain untrusted until verified. Signature verification and metadata handling must avoid loading unbounded archives into memory.

## 15. Architecture anti-patterns

Reject:

- store-only Activity APIs;
- catalogue installer bypassing Package Service;
- native phone app directly writing package roots;
- one trust boolean combining signature/review/license/price;
- online DRM check on every child Activity launch;
- child-visible purchase/payment UI;
- Activity-specific payment SDKs in the normal runtime;
- hidden authoring schemas available only to official publishers;
- community packages executing directly from media/download location;
- official approval inferred from file path, filename or URL;
- proprietary package format required merely to sell an Activity.

## 16. Implementation sequence when R10 reaches this scope

A sensible dependency order is:

1. finalize versioned `.greiaactivity` package schema;
2. implement one transactional Package Service for local/imported packages;
3. implement typed provenance/trust records and parent presentation;
4. implement signing/publisher/update authority;
5. preserve and prove the independent install route;
6. add catalogue metadata/acquisition as another package source;
7. add official review attestations;
8. only then add optional commercial entitlement/payment integration;
9. add native-client catalogue UX through the same Parent API.

Commerce must not drive or distort the lower package/runtime architecture.
