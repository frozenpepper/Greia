# Greia Activity Ecosystem and Distribution — Product Requirements

**Status:** accepted product direction; independent new-install/package seam partly implemented, broader catalogue/update lifecycle incremental  
**Date:** 2026-08-23  
**Architecture owner:** ADR 0023  
**Package-format contract:** `docs/architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md`  
**Licensing owner:** ADR 0024 and `docs/governance/LICENSING_AND_TRADEMARK.md`

## 1. Product purpose

Greia should make it unusually easy for a parent, teacher, hobbyist, developer or software agent to create a safe child-facing Activity and share it with another Greia family.

The ecosystem must preserve two values simultaneously:

- **openness:** the OS, Activity contract, authoring knowledge and supported independent installation path are not locked behind Greia's commercial services;
- **trust:** parents can choose an official, highly curated catalogue where review, provenance and compatibility are significantly stronger than “download arbitrary code from the Internet”.

The official catalogue therefore exists to reduce parent uncertainty, not to become the only technically permitted source of Activities.

## 2. Public authoring experience

A contributor should not need to understand Linux internals to make an Activity.

The target public authoring journey is:

```text
idea
  ↓
create Activity from documented scaffold/example
  ↓
implement against Greia Activity APIs
  ↓
run locally/development environment
  ↓
validate
  ↓
package as .greiaactivity
  ↓
share independently OR submit to official catalogue
```

The corresponding agent journey should be equally explicit:

```text
human describes desired Activity
  ↓
agent reads canonical Greia authoring skill/docs
  ↓
agent creates package against public contracts
  ↓
Greia validator reports deterministic structural/policy errors
  ↓
agent/human fixes
  ↓
package is ready for parent-authorized test/install
```

No hidden prompt, private schema or internal-only validator may be required to create a conforming Activity.

The current canonical agent/developer guide is `skills/greia-activity-authoring/SKILL.md`. Exact implemented APIs remain source-owned as defined by `docs/DOCUMENTATION.md`.

## 3. Authoring documentation target

As the public ecosystem matures, Greia should provide a small, obvious authoring documentation entry point containing at least:

```text
Quick start
Designing for young children
Activity package/manifest reference
Greia Activity API
Input profiles and learned controls
Storage and portable saves
Lifecycle / READY / STOP
Progression and event reporting
Permissions/capabilities
Performance on low-resource hardware
Testing and validation
Packaging
Independent sharing
Official catalogue submission
```

Examples should include small, understandable Activities rather than only large first-party applications.

Documentation should be useful to humans and structured enough that coding agents can reliably locate authoritative rules.

## 4. Independent Activity installation

Parents must retain a supported way to install a compatible Activity obtained outside the official catalogue.

The normal parent-facing distribution file is now defined:

```text
<activity-name>.greiaactivity
```

A `.greiaactivity` file is an ordinary ZIP archive containing the Activity package tree directly at archive root, including root `activity.toml`. Its media type is `application/vnd.greia.activity+zip`.

The custom extension exists so Parent clients and operating-system file pickers can isolate Activity packages from ordinary files. It is a **UX/routing signal only**. Greia never treats the extension, browser-supplied media type, or filename as proof that a package is valid or trusted.

The authoritative format/security details live in `docs/architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md`.

The user experience must not expose Linux paths/package-manager concepts and must never autorun removable code.

A conceptual independent-install flow is:

```text
parent obtains .greiaactivity
  ↓
parent chooses Install Activity / inserts media
  ↓
Greia scans bounded package metadata
  ↓
Greia validates archive + Activity format + compatibility + provenance/trust
  ↓
parent sees clear source/trust information
  ↓
parent explicitly approves installation
  ↓
transactional package service installs or rejects
```

Independent installation does not bypass sandboxing, permissions, package validation, system Home/Back or standard input rules.

### Current implementation boundary

The canonical bounded new-install service and Parent upload seam now exist, and the HTML Parent client can restrict its picker to `.greiaactivity` files when the capability is available.

This does **not** close the full R10 lifecycle. In-place Activity update/replacement, migrations, rollback/recovery, richer provenance/signature handling and final trust UX remain separate work and must not be inferred merely because the container format is now named.

Developer/simulator tools may continue to accept unpacked Activity directories and raw `.zip` inputs for convenience. Those are development inputs, not the normal parent-facing distribution type.

## 5. Official Greia Catalogue

The Official Greia Catalogue is an optional curated distribution source.

Its parent-facing promise should be substantially stronger than “this package parses”. A catalogue Activity may be reviewed for dimensions such as:

- child appropriateness and age range;
- privacy/data flow;
- absence of advertising and behavioral tracking;
- absence of manipulative monetization;
- clear educational/creative/play purpose;
- input usability;
- Greia Home/Back behavior;
- save/update/uninstall behavior;
- low-resource performance where claimed;
- compatibility with declared hardware/runtime classes;
- stable publisher/package identity;
- update provenance;
- accessibility/localization quality where applicable.

The catalogue should prefer a smaller collection of excellent Activities over a high-volume marketplace full of near-duplicates and low-quality content.

## 6. Parent-facing trust language

Greia must distinguish at least these semantic questions, even if final UI labels differ:

1. **Origin/provenance:** built in, official catalogue, independently obtained, developer/test, etc.
2. **Verification/review:** what checks or official review the package passed.
3. **Compatibility:** whether the current Greia device satisfies the package's declared requirements.
4. **License:** what legal rights apply to the Activity.
5. **Price/entitlement:** whether access was free, purchased or otherwise entitled.

These must not collapse into one vague “trusted/untrusted” boolean.

The current package service has explicit trust/source states for implemented sources. Future R10 provenance/signing work may extend those states but must preserve these semantic distinctions.

## 7. Child-facing commerce policy

Normal child Activities must not turn Greia into an advertising or purchase-pressure environment.

The official catalogue direction forbids child-facing patterns such as:

- display advertising;
- behavioral-ad targeting;
- purchase prompts addressed to the child;
- countdown-pressure sales;
- paid random-reward/loot-box mechanics;
- “watch an ad to continue” progression;
- deliberately frustrating free play intended to pressure a purchase;
- hidden external shopping links.

If an Activity or Activity pack is paid, purchase and entitlement management occur through an authenticated parent-facing surface.

After installation/entitlement, core Activity use should remain offline-capable unless a genuinely network-dependent Activity explicitly declares an approved network requirement.

## 8. Free and paid Activities may coexist

The official catalogue may contain:

- free first-party Activities;
- free community/third-party Activities;
- paid first-party Activity packs;
- paid third-party Activities.

Price does not determine review level or source-code license.

A paid Activity may be open source. An open-source Activity may be sold through the official catalogue. Parents may be paying for curation, convenient installation, signed updates, support and distribution rather than exclusive access to source code.

Exact pricing, revenue share, refunds, taxes and publisher contracts are intentionally outside this product requirement until marketplace implementation begins.

## 9. Greia Parents native app

A future native Greia Parents app may be sold as a paid product.

That app must remain an optional convenience layer over the same Greia Parent API defined by ADR 0022.

Essential management of a Greia computer must remain available without buying the native app. The free/local path may be the Greia-served HTML client, an on-device parent surface, or both as the product evolves.

The native app may add value through polish and convenience such as:

- easier discovery/pairing;
- multi-Greia management;
- notifications;
- catalogue browsing/purchases;
- richer backup workflows;
- easier Activity installation;
- family-device overview.

It must not receive a private shell/root/package protocol unavailable to other authorized Parent API clients.

## 10. Privacy and data minimization

The catalogue and companion services should collect the minimum data necessary to provide their parent-facing function.

Child profile data, drawings, saves and progression remain local-first and are not automatically uploaded merely because the parent uses the catalogue or a native companion app.

Any future cloud synchronization or backup must be explicit, parent-controlled and separately designed for child/privacy obligations.

## 11. Publisher and Activity identity

Stable Activity IDs remain technical identity.

The future catalogue additionally needs stable publisher identity and clear provenance so updates cannot silently move between unrelated publishers.

The exact publisher-signing model remains a future package/distribution decision.

An official `Greia Approved` label or equivalent must mean a defined review level, not merely “available in a list”.

## 12. Licensing presentation

Every distributable Activity should ultimately carry machine-readable and human-readable license information sufficient for Greia Parents/catalogue UI to show the parent what applies.

This may eventually include an SPDX-compatible license expression and packaged notice/license files, but the exact manifest fields are not frozen until the relevant R10 package-schema tranche.

Activity authors retain licensing choice as specified by ADR 0024.

## 13. Definition of ecosystem success

Greia's Activity ecosystem is succeeding when all of the following can be true at once:

- a hobbyist can create and share an Activity without commercial permission;
- an agent can create an Activity from public repository guidance and receive useful validator feedback;
- a school or nonprofit can maintain its own Activity collection;
- a commercial educational developer can sell a high-quality Activity without being forced to relicense unrelated source under Greia's platform license;
- a parent can choose the official catalogue for convenience and strong curation;
- a parent can still install a valid independent Activity through an explicit supported route;
- a child never has to understand stores, advertisements, Linux packages, filesystem paths or purchase mechanics to use the computer.

That combination — open creation, parent control and unusually strong curation — is the intended Greia ecosystem identity.
