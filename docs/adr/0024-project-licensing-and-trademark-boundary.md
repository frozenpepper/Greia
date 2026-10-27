# ADR 0024 — Project Licensing and Trademark Boundary

**Status:** ACCEPTED  
**Date:** 2026-08-17  
**Scope:** Greia-owned software, Activity authoring material, documentation, reusable media, third-party Activities, contribution licensing, and project marks  
**Related:** ADR 0023 open Activity ecosystem and official catalogue boundary

## Context

Greia is intended to become a public open-source project while still supporting commercial Activities, optional paid companion software and a curated official catalogue.

The license therefore needs to satisfy two goals at once:

1. improvements to Greia's own platform code should remain shareable when redistributed; and
2. independent software built for Greia should not be forced into the same license merely because it uses the Activity API or interoperates with the platform.

A strongly permissive license such as MIT or Apache-2.0 across the entire platform would permit closed redistribution of modified Greia platform files. A strong whole-work copyleft license such as GPL/AGPL would create more friction around embedded/proprietary integrations and independent Activity development than Greia currently needs.

Mozilla Public License 2.0 provides file-level copyleft: modifications to MPL-covered source files remain under MPL when distributed, while separate files in a larger work may use different terms. MPL 2.0 also includes contributor patent grants and explicitly does not grant trademark rights.

The repository also contains non-software material and will eventually include copyable Activity templates, documentation and media assets. Applying one software license mechanically to every byte would be poor licensing hygiene.

## Decision

### 1. Default license for Greia-owned software is MPL-2.0

Greia-authored platform software is selected to be licensed under the **Mozilla Public License 2.0 (MPL-2.0)** unless a narrower file/directory notice explicitly states otherwise.

This includes, by default, Greia-owned software in areas such as:

- platform/core services;
- Greia Shell and launcher;
- Greia Parents server/client implementation maintained in this repository;
- installer code;
- runtime adapters and platform SDK implementation;
- build/tooling software;
- first-party software tests;
- Greia-authored first-party Activity code unless separately marked.

The intent is simple:

> **Modify and redistribute Greia's covered files: keep those covered files open. Build separate software around Greia: that separate software may use its own license.**

This ADR selects the license policy; it does not override third-party copyrights or existing external license obligations.

### 2. Greia's Activity API must remain usable by differently licensed Activities

An Activity author's independent source files are not required to become MPL merely because they:

- implement the public Activity package contract;
- call a Greia API;
- communicate with a Greia service through its documented interface;
- are installed or distributed on Greia.

MPL-covered Greia library/source files remain governed by MPL. Separate Activity source files remain under the Activity author's chosen terms unless another incorporated dependency imposes its own obligations.

Architecture and SDK design should preserve this clean boundary instead of encouraging authors to copy large chunks of MPL platform implementation into their Activities.

### 3. Copyable scaffolding/templates may use Apache-2.0

Files deliberately intended to be copied into a new independent Activity — for example future starter templates, generated scaffold boilerplate or standalone integration samples — may be explicitly licensed **Apache-2.0**.

The purpose is to let authors copy and modify starter material without accidentally turning their own Activity files into MPL-covered files merely because the scaffold originated in the Greia repository.

A template is not Apache-2.0 merely because it appears in documentation. The applicable file/directory must be explicitly marked.

### 4. Greia-authored documentation defaults to CC BY 4.0

Greia-authored prose/documentation intended for public reuse defaults to **Creative Commons Attribution 4.0 International (CC BY 4.0)** unless explicitly marked otherwise.

This includes architectural/product/authoring documentation and agent-readable guides where Greia owns the underlying text.

Code examples embedded in documentation may be separately marked or treated according to the surrounding documentation policy where legally appropriate. Future substantial reusable code samples should prefer an explicit software license rather than relying on ambiguity.

### 5. Reusable Greia-owned media requires explicit asset licensing

Artwork, icons, audio, fonts and other media must not silently inherit the software license merely because they are stored in the same repository.

The intended default for reusable **Greia-owned** media is **CC BY 4.0** unless a narrower asset notice selects another open license.

However, this default must only be applied after provenance is confirmed. Third-party fonts, icons, sounds, images or generated/derived material retain their own applicable licenses/rights and must carry attribution/provenance as required.

No repository-wide statement may be used to erase or supersede those external rights.

### 6. Third-party Activities choose their own license

Greia does not require a third-party Activity to use MPL, Apache or a Creative Commons license.

Activity authors choose the license for their independent code/content, subject to:

- licenses of incorporated dependencies/assets;
- applicable law;
- package metadata/notice requirements;
- any additional official-catalogue distribution agreement they voluntarily accept.

Price and catalogue approval remain independent from source-code license as specified by ADR 0023.

### 7. Contributions are inbound under the license of the target material

Unless a future governance decision establishes another contribution mechanism, a contribution is accepted under the license governing the material to which it is contributed.

Examples:

- contribution to an MPL-covered software file → MPL-2.0;
- contribution to CC BY documentation → CC BY 4.0;
- contribution to an explicitly Apache-2.0 template → Apache-2.0.

This ADR does not establish copyright assignment, exclusive relicensing rights or a Contributor License Agreement.

### 8. Software/content licenses do not grant Greia trademark rights

The names, logos and official trust marks associated with Greia are separate from copyright licensing.

Open-source rights to copy and modify Greia software do **not** automatically grant a right to represent a modified fork, unofficial catalogue or independently reviewed Activity as an official Greia product.

The project must maintain a separate trademark/use policy covering at least:

- `Greia` and `Greia OS` product identity;
- the Greia logo and distinctive project marks;
- `Greia Approved` or any equivalent official catalogue/certification mark;
- nominative/descriptive use such as “Activity for Greia”;
- redistribution of unmodified official builds;
- rebranding expectations for materially modified forks;
- rules preventing implication of endorsement or official catalogue approval.

This ADR does not claim that any mark is formally registered in any jurisdiction. Registration strategy is a separate legal/business decision.

### 8a. 2026-10-27 trademark-use clarification

Commercial use and sale of Greia under MPL-2.0 do not require a project fee or
commercial software license. Truthful identification such as “Runs Greia OS”
(including on packaging), normal distribution with existing in-software marks
and ordinary community references are permitted without a separate trademark
agreement, provided they do not imply official endorsement.

Prominent Greia logo **product branding** on a manufacturer's own packaging,
official partner/certification claims, and endorsement are different matters:
they may require explicit optional authorization and a commercial agreement.
Substantial forks may describe their origins but cannot masquerade as official
Greia releases; a practical rebranding path is required. This does not alter
open-source code rights.

The [practical trademark-use policy](../governance/LICENSING_AND_TRADEMARK.md)
provides the operative detail. No mark registration or official certification
programme is claimed and public-release legal review is pending.

### 9. Licensing must be mechanically explicit before public release

License selection is not enough. Before the repository is made public or an official release is distributed, Greia must complete a licensing/provenance audit and make licensing machine- and human-readable.

At minimum:

- include canonical license texts in the repository/distributions;
- add a clear top-level licensing notice;
- mark directory/file exceptions where the default differs;
- use SPDX identifiers where practical for software/source files;
- inventory third-party code, packages, fonts, media and required notices;
- ensure copied/derived assets have documented provenance;
- ensure binary/image distributions carry required license/notice material;
- verify that the repository owner has the rights required to apply the selected licenses to existing Greia-authored work.

Until that audit/mechanical application is complete, project documentation must distinguish **license policy selected** from **public-release licensing complete**.

## Why MPL-2.0 rather than alternatives

### MIT

Not selected as the platform default because it allows a redistributor to modify Greia's covered platform source and distribute those modifications without a reciprocal source-sharing obligation.

### Apache-2.0

A strong choice for permissive SDK/templates and includes useful patent terms, but not selected as the platform-wide default because it is permissive rather than copyleft.

### GPL-3.0

Not selected as the platform default because Greia's extension model intentionally includes independently licensed Activities and potentially proprietary integrations. The stronger whole-work copyleft boundary creates more integration uncertainty than the project currently wants.

### AGPL-3.0

Not selected because Greia's core is an operating-system/platform project, not primarily a hosted network service whose central risk is unshared server-side modification.

## Consequences

Positive:

- distributed improvements to Greia's own covered files remain open;
- independent Activity authors retain broad licensing freedom;
- proprietary and paid Activities can coexist without changing the platform license;
- copyable templates can be intentionally permissive;
- documentation and media receive licenses suited to non-software works;
- trademarks can protect official identity/curation without restricting software freedom.

Costs/risks:

- a multi-license repository requires careful per-directory/per-file notices;
- asset provenance must be audited before public release;
- contributors must understand that software copyright and project marks are separate;
- commercial distribution and trademark enforcement may eventually require professional legal review.

## Authoritative external license references

For legal text and interpretation, use the license stewards' official materials rather than paraphrases in this ADR:

- Mozilla Public License 2.0: `https://www.mozilla.org/MPL/2.0/`
- Apache License 2.0: `https://www.apache.org/licenses/LICENSE-2.0`
- Creative Commons Attribution 4.0 International: `https://creativecommons.org/licenses/by/4.0/`

This ADR is an engineering/project policy decision, not individualized legal advice. Before public launch, marketplace operation or trademark enforcement, the project should have the final repository/distribution policy reviewed for the actual legal entity and jurisdictions involved.
