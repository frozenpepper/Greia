# ADR 0023 — Open Activity Ecosystem and Official Catalogue Boundary

**Status:** ACCEPTED (public technical summary revised 2026-10-31)  
**Date:** 2026-08-17  
**Clarifies:** ADR 0012 (platform), ADR 0015 (Activity identity) and ADR 0022 (Parents API)

## Context

Greia is a free, open-source child-computing platform. Parents, teachers, developers and software agents should be able to build, share and install child-appropriate Activities using documented public interfaces. Future distribution services must not turn those interfaces into proprietary dependencies.

## Decision

### 1. Public Activity authoring

The Activity package contract, platform APIs, validation tooling, examples, and human- and agent-facing documentation must be public and sufficient for independent authors. First-party and community Activities use the same foundational contracts; no hidden API may be required to create a conforming Activity.

### 2. Independent parent-authorized installation

Greia must retain a supported way for a parent to install a compatible Activity obtained independently of any official catalogue. Installation is an explicit parent action subject to the normal sandbox, compatibility, validation, and provenance/trust controls. No child-side autorun or bypass of those controls is implied.

### 3. Optional curated catalogue

An official catalogue may offer easier discovery, independent quality review, compatibility checks, provenance and update handling. Being installable and being officially reviewed are different claims. An optional catalogue must not be the exclusive installation route. The service architecture, protocol and availability are not committed by this ADR.

### 4. Child-first distribution

Children must not be subjected to advertising, behavioral targeting, purchase prompts, paid random rewards, coercive unlock loops, or hidden external shopping links. If a distribution service ever handles transactions, any such interactions belong solely in an authenticated parent-facing surface; no particular commerce product is proposed here.

### 5. Parent API parity and offline operation

Any companion Parents client uses the same documented Parent API and cannot require a privileged parallel management protocol. Essential administration remains available locally without a catalogue, account, or optional third-party service. Installed offline-capable Activities, saves and progression continue to work without network access.

### 6. Independent licensing and provenance

An Activity's publisher/source, validation or review status, compatibility and copyright license are separate facts. Activity authors retain the choice of license for their independent work, subject to incorporated dependencies and their licenses; consuming Greia's public APIs alone does not force unrelated source under Greia's platform license. ADR 0024 and the public licensing/trademark policy govern the platform.

## Consequences

Greia remains open to independent educational, nonprofit and commercial distributors under applicable licenses; parents control what is installed and children are not exposed to commercial pressure. Public package authoring and validation requirements carry a compatibility and maintenance cost. Future catalogue, package-identity, signature and UI details require separate decisions and implementations; none may eliminate independent installation.

## Rejected approaches

- Making an official catalogue the only legitimate Activity installation channel.
- An open-core split that withholds essential platform or parent-management capabilities.
- Child-facing advertising and manipulative purchases.
- Requiring every independent Activity to use Greia's own platform software license.

## Implementation references

- [Activity ecosystem requirements](../product/ACTIVITY_ECOSYSTEM_AND_DISTRIBUTION.md)
- [Activity package format](../architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md)
- [Create an Activity](../development/CREATE_AN_ACTIVITY.md)
- [Licensing and trademark](../governance/LICENSING_AND_TRADEMARK.md)

This ADR records technical openness and child-safety boundaries, **not** a product launch, catalogue roadmap, pricing model, or business plan.
