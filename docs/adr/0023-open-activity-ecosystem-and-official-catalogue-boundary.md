# ADR 0023 — Open Activity Ecosystem and Official Catalogue Boundary

**Status:** ACCEPTED  
**Date:** 2026-08-17  
**Scope:** Activity authoring, third-party distribution, official catalogue, monetization boundary, parent purchase authority, companion clients, and community interoperability  
**Clarifies:** ADR 0012 Activity/package architecture, ADR 0015 Activity identity/trust concepts, ADR 0022 Greia Parents client parity, and the future R10 package/distribution work

## Context

Greia is intended to be a free, open-source child computing platform and also a platform on which people other than the core project can create useful Activities.

That creates several product questions which must be answered before package distribution and a future native parent app harden into accidental architecture:

- whether Activity creation depends on unpublished project knowledge;
- whether an official store becomes the only legitimate installation route;
- whether Greia may sustainably earn revenue without turning the OS into an open-core product;
- whether free, open-source and commercial Activities can coexist;
- whether package trust, price and source-code license are incorrectly treated as the same thing;
- whether a paid native phone app would make essential parent administration paywalled;
- whether child-facing software can remain free from advertising, tracking and manipulative purchase mechanics while still supporting a viable ecosystem.

The current architecture already provides the correct foundation: Activity is runtime-neutral; Greia owns lifecycle, storage, profiles, permissions, progression, system navigation and standard input; network access is denied by default; package installation is intended to be parent-authorized and transactional.

## Decision

### 1. Greia is an open platform, not an open-core product

The Greia OS platform, its Activity interfaces, authoring documentation and validation contracts must remain available without payment.

The project may charge for convenience, curation, support, premium first-party content, commercial distribution services, or optional companion products. It must not make payment a prerequisite for creating a conforming Activity, understanding the Activity format, validating an Activity, or installing a parent-authorized compatible Activity through a supported non-catalogue route.

A future business model must therefore preserve this invariant:

> **The platform is the public good; official distribution and convenience services may be commercial products around it.**

### 2. Human and agent Activity authoring are first-class public interfaces

Greia must deliberately support both human developers and software agents.

Canonical Activity-authoring material must be repository-visible, versioned and sufficient to create conforming Activities without chat history or private project knowledge. This includes, as the implementation matures:

- a concise quick start;
- manifest and platform-API reference;
- child-interaction/design guidance;
- storage, input, progression and lifecycle guidance;
- representative example Activities;
- machine-usable authoring guidance such as `skills/greia-activity-authoring/SKILL.md`;
- deterministic validation and packaging commands;
- clear compatibility and trust diagnostics.

The same public validator/contracts used by first-party Activities should be usable by community authors. The official catalogue may apply additional review, safety and quality requirements, but it must not depend on a secret Activity API.

### 3. Supported non-catalogue installation is a permanent platform property

The future official catalogue is optional distribution infrastructure, not a technical monopoly.

Greia must retain a parent-authorized supported path to install valid Activities obtained elsewhere, for example from removable media or another explicit import mechanism implemented by R10.

That path must preserve all normal package validation, sandbox, compatibility, signature/trust presentation and fail-closed rules. “Open installation” does not mean autorun, bypassed verification or silent child-side installation.

### 4. Community distribution and the Official Greia Catalogue are distinct lanes

Greia recognizes two conceptual distribution lanes:

1. **Community / independent distribution** — authors may publish Activities through their own repositories, websites, organizations or community indexes, subject to the Activity package contract and the parent-authorized install path.
2. **Official Greia Catalogue** — an optional Greia-operated curated source with stronger review, signing/provenance, metadata quality, compatibility testing, update handling and parent-facing discovery.

The exact servers, index schema, signing infrastructure and store implementation remain future work. This ADR fixes the product boundary, not a premature network protocol.

### 5. Catalogue curation is the value proposition

The official catalogue should optimize for parent trust and quality rather than maximum item count.

Catalogue policy may require evidence such as:

- no child-facing advertising;
- no third-party behavioral tracking;
- no hidden external links or browser escape surfaces;
- no manipulative purchase loops;
- declared/mediated network use only;
- age and interaction review;
- compatibility/resource testing on relevant Greia classes;
- lifecycle, Home/Back, storage and input-contract compliance;
- privacy and data-flow review;
- stable package identity and update provenance.

An Activity can be technically installable without being “Greia Approved”. Official approval is a distribution/quality statement, not a prerequisite for the Activity abstraction itself.

### 6. Package trust, price and software license are independent dimensions

Greia must not collapse these concepts into one flag.

An Activity may be, for example:

- free and open source;
- paid and open source;
- free but source-unavailable under its author's terms;
- paid and source-unavailable under its author's terms;
- independently distributed;
- officially catalogued;
- built in by Greia;
- locally/developer installed.

Trust/provenance answers **where the package came from and what verification it passed**. Price answers **how access/distribution is funded**. License answers **what legal rights the recipient receives in the work**.

The future R10 package model must preserve these as separate metadata/policy concepts.

### 7. Paid Activities are allowed, but commerce is parent-facing

The Official Greia Catalogue may eventually contain both free and paid Activities, including third-party commercial Activities, provided they satisfy Greia catalogue and child-safety requirements.

Greia may also publish paid first-party Activity packs or other premium content while keeping the platform itself open.

Any purchase, subscription, entitlement-management or payment UI must live in an authenticated parent-facing context. Ordinary child Activities must not present purchase pressure, advertising-funded unlocks, loot-box-like mechanics, or direct payment flows to children.

The exact revenue share, taxes, refunds, pricing and payment provider are business/legal decisions and are intentionally not fixed by this ADR.

### 8. A paid native Greia Parents app is permitted but must remain optional convenience

A future iOS/Android/desktop Greia Parents client may be a paid product.

That commercial choice must not create a second privileged management architecture or paywall essential ownership of the Greia computer. Core parent administration must remain available through a free Greia-controlled path, initially the local Greia Parents HTML client and/or on-device parent surface, using the same Parent API defined by ADR 0022.

The paid native client may justify its price through polish, discovery, notifications, catalogue integration, backup convenience, multi-device management and similar usability benefits. It does not receive private root/SSH/package powers unavailable to other authorized clients.

### 9. Cloud services remain optional enhancement

Catalogue access, optional synchronization, remote notifications or backup convenience may use network services in the future.

Core installed Activities, local saves, progression and parent management must remain usable without a Greia cloud account. A catalogue outage must not disable already installed Activities or make a child unable to use the computer.

### 10. Greia does not require third-party Activities to adopt Greia's own software license

Activity authors retain licensing choice for their own independent Activity code/content, subject to licenses of any components they incorporate and any catalogue terms they voluntarily accept.

Using Greia's public Activity APIs or packaging contract must not, by itself, force an Activity author to license unrelated Activity source under Greia's platform license.

The project licensing boundary is fixed separately by ADR 0024.

## Consequences

Positive:

- Greia can remain genuinely open while still supporting sustainable revenue;
- the official catalogue competes on trust, curation and convenience rather than lock-in;
- commercial educational developers are not excluded by the platform license;
- parents retain ownership/control of their machines and can install compatible independent Activities;
- agent-generated Activities have a clear public contract rather than relying on hidden prompts;
- child-facing commerce and advertising pressure are structurally separated from Activities.

Costs/risks:

- independent installation increases the importance of excellent trust/provenance UI;
- catalogue review/signing infrastructure will be operationally expensive;
- supporting paid and free third-party content creates legal, tax, refund and moderation obligations when the catalogue is implemented;
- non-catalogue packages may vary widely in quality, so Greia must distinguish “installable” from “officially approved” without frightening or misleading parents;
- public authoring contracts increase compatibility obligations and require disciplined versioning.

## Rejected alternatives

### Official catalogue as the only installation path

Rejected because it would turn an open child-computing platform into a gatekept distribution appliance and make the catalogue a technical monopoly.

### Everything free, no revenue allowed

Rejected as an architectural requirement. Development, moderation, signing, compatibility testing, infrastructure and support have ongoing costs. Greia may earn revenue without withholding the platform itself.

### Open-core licensing

Rejected. Core parent/platform capability must not be split into a deliberately crippled open edition and a functionally necessary proprietary edition.

### Advertising-supported child Activities

Rejected for the official catalogue direction. It conflicts with Greia's child-first, privacy-first, low-distraction model and creates incentives directly opposed to the platform's purpose.

### Mandatory open-source licensing for every third-party Activity

Rejected. Greia should strongly support open Activities but should not make unrelated Activity source-code licensing a condition of using the public Activity API.

## Follow-up requirements

Before public third-party distribution is considered complete, future work must define and implement at least:

- R10 versioned `.greiaactivity` package schema;
- distribution signing and key lifecycle;
- parent-facing trust/provenance states;
- explicit independent/sideload installation flow;
- official catalogue metadata/review/update model;
- package license metadata and bundled license/notice handling;
- author/publisher identity rules;
- catalogue child-safety/privacy review policy;
- agent/human quick-start and scaffolding experience;
- deterministic `validate` and `package` tooling;
- offline entitlement behavior for any paid catalogue content.

None of those future implementation details may remove the open non-catalogue installation invariant established here.
