# Greia Licensing and Trademark Policy

**Status:** selected project policy; public-release mechanical application/audit still required  
**Date:** 2026-08-17  
**Normative architecture decision:** ADR 0024  
**Related ecosystem decision:** ADR 0023

## 1. Purpose

This document is the practical licensing/trademark guide for contributors, Activity authors and future distributors.

It records the selected policy without pretending that every existing file and asset has already completed a public-release provenance audit.

When a file contains a more specific valid license/provenance notice, that narrower notice wins for that file.

## 2. License matrix

| Material | Selected/default policy |
|---|---|
| Greia-owned platform/application/tooling software | MPL-2.0 |
| Greia-owned SDK implementation files | MPL-2.0 unless specifically marked otherwise |
| Future copyable Activity scaffolds/templates/boilerplate explicitly intended for incorporation into third-party Activities | Apache-2.0 when explicitly marked |
| Greia-owned documentation and agent/developer guides | CC BY 4.0 unless specifically marked otherwise |
| Greia-owned reusable artwork/icons/audio/media | intended CC BY 4.0 default after provenance confirmation, unless specifically marked otherwise |
| Third-party code/fonts/media/content | original applicable license/rights; never overwritten by repository defaults |
| Independent third-party Activities | author/publisher chooses, subject to incorporated dependencies and distribution terms |
| Greia names/logos/official trust marks | not granted by the software/content licenses; governed separately below |

This matrix is deliberately not “one license for everything”. Software, documentation, reusable media and marks have different legal/technical purposes.

## 3. MPL-2.0 platform rule

Greia-owned software is selected for MPL-2.0 because the project wants reciprocal openness at the file level without making independent Activities adopt Greia's license.

Practical rule:

- if you modify an MPL-covered Greia source file and redistribute that covered software, the MPL obligations continue to apply to that covered source;
- separate files in a larger work may use different terms subject to the actual license and dependency relationships;
- using a public Greia interface does not by itself license your independent Activity source under MPL.

Use the official Mozilla license text and FAQ for the legal terms. This policy is only a project guide.

Official reference: `https://www.mozilla.org/MPL/2.0/`

## 4. Activity author licensing

Greia Activity authors choose the license for their own work.

Greia should eventually expose package license metadata clearly enough that a parent, catalogue reviewer or downstream distributor can identify what terms apply.

Until R10 freezes the package schema, do not invent unsupported `activity.toml` license fields. An independently shared Activity source repository should nevertheless include an appropriate LICENSE/NOTICE for its own code/assets.

The Official Greia Catalogue may impose distribution, safety, support or commercial terms without changing the underlying copyright license chosen by the author unless a future publisher agreement explicitly says otherwise.

## 5. Copyable templates and examples

A source file merely being an “example” does not automatically make it permissively licensed.

When Greia creates boilerplate specifically intended to be copied into third-party Activities, that material should be placed in an explicitly marked Apache-2.0 area or carry an equivalent clear permissive notice.

Do not copy implementation-heavy MPL platform files into a new Activity merely to avoid designing a proper SDK interface.

Official Apache License reference: `https://www.apache.org/licenses/LICENSE-2.0`

## 6. Documentation

Greia-owned documentation is selected for CC BY 4.0 unless a file says otherwise.

This permits broad reuse, adaptation and translation with attribution, including by schools, nonprofits, commercial developers and agent-tool authors.

Official CC BY 4.0 reference: `https://creativecommons.org/licenses/by/4.0/`

Substantial reusable source-code examples should eventually receive explicit software licensing where ambiguity would matter.

## 7. Assets and provenance

Do not assume an image, font, sound or icon is Greia-owned simply because it is committed to this repository.

Before public release, asset inventory must classify each distributable asset as at least one of:

- Greia-owned original work;
- commissioned/assigned work with documented rights;
- generated material with documented provenance/usage basis;
- third-party openly licensed work;
- third-party proprietary material with explicit distribution permission;
- non-distributable development/reference material.

Required attribution, source links, license texts and modification notices must be preserved where applicable.

The intended default for confirmed Greia-owned reusable media is CC BY 4.0, but that default must not be used to overwrite a third party's terms.

## 8. Third-party dependency notices

Greia OS images will contain Linux and many upstream packages under their own licenses.

The Greia project license does not relicense those components.

Release/image work must preserve the license/notice obligations of included dependencies and make corresponding source/notice information available as required by those upstream licenses.

This policy is especially important for generated OS images: a root repository license is never a substitute for a distribution's third-party notices.

## 9. Contribution licensing

Unless a future governance decision states otherwise, contributions are accepted under the license already governing the target material.

Contributors must only submit work they have the right to contribute under those terms.

A contributor must not silently paste incompatible third-party source/assets into a Greia-owned file. If external material is necessary, its origin/license must be made explicit during review.

No copyright assignment or Contributor License Agreement is established by this policy.

## 10. Greia marks

The open-source licenses grant rights in covered software/content, not an unrestricted right to present a fork or service as official Greia.

Project marks include, at minimum, subject to actual legal rights in each jurisdiction:

- Greia;
- Greia OS;
- Greia Shell;
- Greia Parents;
- Greia project/logo artwork used as brand identity;
- `Greia Approved` or any future equivalent official catalogue/certification mark.

This document does **not** claim that any of these marks are registered trademarks.

## 11. Permitted descriptive use direction

A future formal trademark policy should allow good-faith descriptive statements such as:

- “an Activity for Greia”;
- “compatible with Greia OS”;
- “built using the Greia Activity API”;
- “forked from the Greia project”.

Such use must not imply sponsorship, official catalogue approval, certification or ownership by the Greia project when that relationship does not exist.

## 12. Fork/rebranding direction

Open-source forks are allowed by the applicable software licenses.

A materially modified distribution should not be presented as an official Greia OS build unless the project has explicitly authorized that use of the marks.

The eventual public trademark policy should define a simple rebranding path so a fork can exercise all open-source rights without depending on permission to use official branding.

Unmodified redistribution rules may be more permissive, but exact rules should be reviewed before public launch.

## 13. Official catalogue/trust marks

No independent author, repository, store or distributor may describe an Activity as `Greia Approved` (or use an equivalent official trust mark) merely because:

- the package validates structurally;
- it runs on Greia;
- it is open source;
- it was once reviewed informally;
- it appears in a community index.

Official trust marks must correspond to a defined current Greia review/signing policy.

This separation is important because catalogue trust is one of the legitimate services Greia may provide around an open platform.

## 14. Public-release licensing gate

Before making the repository public or distributing an official public Greia release, complete and record a licensing audit.

Minimum gate:

1. verify ownership/provenance of existing Greia-authored source;
2. inventory third-party source/code snippets;
3. inventory distributable images/icons/audio/fonts;
4. add canonical full license texts to the repository/distribution;
5. add top-level licensing/notice files appropriate to the selected matrix;
6. add SPDX identifiers or directory-level notices where practical;
7. explicitly license future copyable scaffolds/templates;
8. preserve required third-party notices/attributions;
9. verify image-build license/source-offer obligations for included Linux/upstream packages;
10. review the trademark policy for the actual project/legal entity and intended jurisdictions;
11. review marketplace/payment/privacy obligations separately before operating a paid catalogue.

Until this gate is completed, describe the state as **license policy selected; public-release licensing audit pending**, not “all repository material is licensed under MPL-2.0”.

## 15. Relationship to monetization

Nothing in MPL-2.0, Apache-2.0 or CC BY 4.0 inherently means Greia must charge zero money for every service or distribution.

The project may charge for an optional native parent app, catalogue distribution, premium Activities, support or other services consistent with ADR 0023.

The architectural non-lock-in rule remains: payment must not be required to understand the Activity contract, create a conforming Activity, or use the supported independent parent-authorized Activity installation path.

## 16. Legal review boundary

This file is a project governance/engineering policy, not a substitute for professional legal advice.

Before public launch, paid marketplace operation, formation of a nonprofit/legal entity, privacy-policy publication or trademark enforcement, have the applicable legal documents reviewed for the actual entity and jurisdictions involved.
