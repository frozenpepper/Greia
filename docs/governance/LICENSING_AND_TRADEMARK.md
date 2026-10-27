# Greia Licensing and Trademark Policy

**Status:** selected project policy (trademark-use clarification 2026-10-27); public-release rights/provenance audit and legal review still required  
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

The intended default for confirmed Greia-owned reusable media is CC BY 4.0, but that default must not be used to overwrite a third party's terms. Distinctive Greia identity logos, wordmarks and official partner/certification badges are **not** covered by that general media default. Their copyright status and trademark permissions must be considered separately. Do not claim exclusive rights to third-party or uncleared artwork.

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

## 10. Greia marks and the software license

**Greia remains fully open-source.** Anyone may install, modify, redistribute
and commercially sell MPL-covered Greia software, including computers with
Greia preinstalled, without permission or royalties from the project,
provided the applicable open-source licenses are respected. Other
third-party components and independently licensed Activities retain
their own distribution conditions.

The Greia name, Greia OS, Greia Shell, Greia Parents, distinctive Greia
logos/wordmarks and any future official partner/certification badges are
project marks, subject to the rights actually held in each jurisdiction.
Open-source software licenses do not automatically grant trademark rights
to imply endorsement. **This policy does not claim that any mark is
registered**, or that the project owns rights it has not cleared.

## 11. Trademark uses permitted without a separate agreement

Where Greia holds the necessary rights, the following uses are permitted
without seeking permission or paying a fee, provided they are accurate
and do not imply official endorsement:

- **Truthful written identification**, even in commercial advertising,
  store listings and product packaging: “Runs Greia OS”, “Includes Greia”,
  “Powered by Greia OS”, “Compatible with Greia”, “An Activity for Greia”,
  “Based on the Greia open-source project”.
- Community and school/NGO tutorials, teaching material, screenshots,
  reviews, links and acknowledgement of the source project.
- Commercial or free distribution of authentic, unmodified Greia software
  with the original branding already **inside the software** and its
  preserved notices. This does not make the seller an official distributor.
- Normal supported user configuration and independent Activity installation,
  which alone do not make the original installation an unofficial fork.

A truthful **text mention** of Greia on a box is not the same as making
Greia's distinctive logo the box's primary product/endorsement brand.
Independent sellers should prominently identify themselves and avoid any
suggestion that Greia manufactured, warranted or certified their product.
If the association could be misunderstood, a simple phrase such as
“Independently distributed; not an official Greia product” is enough.

No clause here restricts legitimate referential/nominative use allowed
by law, any legally required attribution, or any open-source license right.

## 12. Official commercial branding and certification

Request written authorization before using a project-controlled mark to:

- market a third-party device, product or service **as an official Greia
  edition**, or imply that its manufacturer is officially endorsed;
- make the distinctive Greia logo or lockup the prominent **manufacturer's
  product/box brand** rather than merely identifying included software;
- claim “Official Greia Partner”, “Greia Certified”, “Greia Approved”, or
  use any resembling official seal, badge or catalogue trust mark;
- incorporate Greia marks into the independent seller's business/product
  identity in a confusing way.

These optional permissions may be supplied under a free or paid agreement.
An OEM agreement may include official branding, integration, custom
educational Activities and graphics, hardware testing, support, co-marketing
or negotiated annual/per-unit commercial fees. Such fees **cannot be
presented as a charge for exercising the existing MPL-2.0 rights**.

**No formal Greia certification programme, badge licensing service or
royalty schedule has been launched yet.** A future programme must establish
real criteria, a review process and a written agreement before making
certification or support promises. The word “Certified” in this document
only identifies a possible future reserved mark.

## 13. Forks, rebranding and community trust

Forks and derivatives remain allowed, including for profit. A substantially
modified product should have its own prominent product identity and must not
present itself as an official Greia OS release without authorization. It
may freely and truthfully say it is *based on Greia*; required copyright,
license and attribution notices must remain. Minor settings changes or
ordinary parent-installed Activities do not automatically require rebranding.

Greia must provide a practical way to replace its prominent identity marks
in a derivative; trademark controls must never become a technical gate on
the open-source right to build, modify or redistribute the covered software.

Independent Activities may truthfully describe compatibility without
implying they passed an official Greia review. Software license, price,
package trust and optional catalogue approval remain distinct as ADR 0023
requires.

**Policy principle:** do not charge for honest identification of Greia or
use trademark rules to hinder normal open-source distribution. Reserve
commercial agreements for genuine official association and services.

Questions about possible official co-branding can go to the current project
maintainers through established repository contact channels until a
dedicated contact is published. No unstaffed address is presumed.

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
10. confirm ownership of proposed Greia names/logos; search earlier conflicting marks in the intended countries/classes; choose whether and where to register; review the official-versus-descriptive use policy with legal counsel;
11. review marketplace/payment/privacy obligations separately before operating a paid catalogue.

Until this gate is completed, describe the state as **license policy selected; public-release licensing audit pending**, not “all repository material is licensed under MPL-2.0”.

## 15. Relationship to monetization

Nothing in MPL-2.0, Apache-2.0 or CC BY 4.0 inherently means Greia must charge zero money for every service or distribution.

The project may charge for an optional native parent app, catalogue distribution, premium Activities, support, commissioned educational/localization work and voluntary official OEM branding/integration/support agreements consistent with ADR 0023. This must not be turned into a fee for merely redistributing the open-source platform.

The architectural non-lock-in rule remains: payment must not be required to understand the Activity contract, create a conforming Activity, or use the supported independent parent-authorized Activity installation path.

## 16. Legal review boundary

This file is a project governance/engineering policy, not a substitute for professional legal advice.

Before public launch, paid marketplace operation, formation of a nonprofit/legal entity, privacy-policy publication or trademark enforcement, have the applicable legal documents reviewed for the actual entity and jurisdictions involved.
