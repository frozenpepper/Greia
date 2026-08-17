# Greia Visual Style Guide

**Status:** accepted visual-design direction; implementation pending where noted  
**Date:** 2026-08-17  
**Audience:** Greia Shell designers, platform developers, Activity authors, installer/Parent UI developers, artists, reviewers, and software agents  
**Related:** `docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md`, ADR 0018, ADR 0019, ADR 0025, `runtime/theme-defaults.toml`

## 1. Purpose and authority

This document is the living **visual-language and typography guide for Greia**. It defines how Greia should look and read across the child Shell, platform-owned UI, first-party Activities, celebrations/awards, installer, recovery, and parent-facing surfaces.

It complements `GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md`:

- the **asset requirements** document defines what graphical assets and production artwork Greia needs;
- this **style guide** defines the visual character and reusable presentation rules those assets and interfaces should follow.

Accepted ADRs remain authoritative for architecture and trust boundaries. Source/runtime declarations remain authoritative for exact implemented theme/UI APIs. This guide must not invent an API merely to describe a desired design system.

The current implementation already has color/theme primitives in `runtime/theme-defaults.toml` and shared UI semantics in `src/greia_platform/ui_core.py`, but **a platform typography-token API and bundled Nunito Sans font files are not yet implemented merely because this document selects them**.

## 2. Visual personality

Greia should feel like a coherent, welcoming child computer rather than a collection of unrelated Linux applications.

The visual language should be:

- **warm and playful without looking like baby software**;
- friendly enough for a young child without becoming visually noisy or patronizing;
- easy to understand before it is impressive;
- shape-first and language-light for navigation;
- readable on the 800×600 / 1024×600 low-resource floor as well as modern displays;
- consistent between Shell, Activities, profiles, awards, installer, recovery, and Greia Parents;
- rich in illustration and personality where useful, while keeping controls visually stable and predictable;
- accessible under color-vision differences and usable without relying on tiny decorative detail;
- capable of richer animation on stronger hardware without making animation necessary to understand state.

Fun should come primarily from **illustration, character, motion, sound, spacing, shape, and celebration**, not from making ordinary interface text difficult to read.

## 3. Typography decision

### 3.1 Default family — Nunito Sans

**Selected default Greia interface typeface: `Nunito Sans`.**

Nunito Sans is selected because it sits deliberately between a neutral system sans-serif and an overtly childish display face:

- rounded forms make it friendly without becoming cartoon typography;
- conventional letterforms remain suitable for children who are learning to read;
- it works for both large display text and ordinary interface labels;
- the family provides sufficient weight range for hierarchy without requiring multiple unrelated font families;
- it allows Greia to create personality through size, weight, spacing, animation, and illustration rather than novelty letterforms;
- its open font license is compatible with bundling it with Greia while keeping Greia software under its own licenses.

The default design direction is therefore **one coherent family across most of the operating environment**, rather than a playful heading font paired with a separate utilitarian body font.

### 3.2 Scope of the default

Nunito Sans should be the default for:

- Greia Shell navigation and labels;
- profile selection;
- platform-owned Home/Back and other system presentation where text is present;
- badge/award titles and celebration text;
- standard first-party Activity controls and explanatory text;
- installer UI;
- recovery UI;
- Greia Parents UI unless a platform-specific native client has a strong accessibility reason to use the host system typeface;
- documentation-generated screenshots/mockups representing the canonical Greia UI.

An Activity may use another appropriately licensed typeface **inside its expressive or pedagogical content** when that is genuinely part of the Activity design. That must not turn every Activity into its own unrelated UI system. Standard controls, navigation, feedback, and ordinary explanatory text should normally follow Greia typography.

Specialized literacy Activities may require pedagogically specific letterforms. Those cases should be decided for learning value and legibility rather than visual novelty.

## 4. Nunito Sans licensing and provenance

Nunito Sans is distributed under the **SIL Open Font License 1.1 (OFL-1.1)**.

For Greia this means the font may be bundled and redistributed with the operating system, including in a distribution that also contains software under other licenses. The font itself remains under OFL-1.1; bundling it does not relicense Greia software.

When Greia actually vendors/distributes the font, the repository/public-release licensing audit must:

- obtain the font from a traceable upstream source;
- preserve the upstream copyright and OFL-1.1 license notice;
- record the exact font version/source used;
- record whether the files are unmodified;
- retain any upstream Reserved Font Name conditions that apply;
- keep Nunito Sans listed as third-party font software rather than treating it as Greia-owned CC BY media or MPL software.

**Current state:** typography choice selected; font vendoring/package integration not yet implied or completed by this document.

## 5. Initial weight system

Greia should begin with a small static weight set rather than requiring variable-font rendering.

Preferred initial roles:

| Role | Preferred Nunito Sans weight | Typical use |
|---|---|---|
| Body | Regular | ordinary explanatory text, descriptions |
| Control | SemiBold | buttons, navigation, short labels |
| Title | Bold | screen titles, Activity/card titles, profile names |
| Celebration | ExtraBold | `NEW BADGE!`, major score/award moments, very short emphasis |

Avoid Light/ExtraLight as normal child-facing UI weights. Thin strokes reduce robustness on old LCDs, low resolutions, scaling paths, and visually busy backgrounds.

The implementation should initially prefer **static font files for the exact weights Greia uses**. Variable-font support may be evaluated later, but Greia should not make old-hardware correctness depend on it.

A likely eventual deployed set is conceptually:

```text
NunitoSans-Regular
NunitoSans-SemiBold
NunitoSans-Bold
NunitoSans-ExtraBold
```

The exact filenames/version/package source are implementation/provenance facts and must be recorded when the files are actually introduced.

## 6. Initial child-facing type scale

The following are **design targets for physical testing, not a frozen renderer API**:

| Semantic role | Initial 1024×600 target |
|---|---:|
| Major celebration | 48–64 px |
| Screen title | 34–42 px |
| Activity/card title | 26–32 px |
| Primary button/control | 23–27 px |
| Ordinary child-facing text | 21–24 px |
| Small secondary child label | 18–20 px |

Meaningful child-facing UI should generally avoid going below about **18 px** on the 1024×600 reference experience unless physical testing demonstrates excellent legibility and the information is genuinely secondary.

These values must be tested on real low-resolution hardware. A CSS point size or desktop screenshot is not evidence of readability on the Acer-class floor.

Parent-facing dense informational surfaces may use a more compact scale where appropriate, but should still favor clarity over desktop-style information density.

## 7. Hierarchy and text treatment

### 7.1 Use weight before decorative typography

Prefer:

```text
Regular → SemiBold → Bold → ExtraBold
```

for hierarchy before introducing a second family, outlines, shadows, or novelty lettering.

### 7.2 Avoid excessive all-caps

All-caps is acceptable for very short celebratory or status phrases such as:

```text
NEW BADGE!
NEW BEST!
```

It should not become the default for paragraphs, instructions, Activity descriptions, or long button labels.

### 7.3 Comfortable spacing

Child-facing text should use generous line spacing and avoid tightly packed desktop layouts. Multi-line explanatory text should normally have enough leading that adjacent lines remain visually distinct at low resolution.

Letter spacing should remain close to the typeface's intended metrics unless a tested accessibility/localization case requires otherwise.

### 7.4 Contrast and backgrounds

Text must remain readable independently of decorative artwork. Avoid placing ordinary text directly over detailed illustrations without a stable contrast treatment such as a panel, card, soft backing shape, or deliberately quiet region.

Color is not the only carrier of state. Weight, icon, shape, text, and state change should reinforce important meaning.

## 8. Young-reader legibility checks

Typography review should use realistic Greia material rather than `Lorem ipsum` alone.

A standard specimen should include at least:

```text
Greta
Gaia

1 2 3 4 5 6 7 8 9 10

b d
p q
I l 1
O 0
m n
c e

GIOCA
DISEGNA
CASA
INDIETRO

Nuovo record!
Hai vinto un distintivo!

42
126
1000
```

The exact specimen may expand as Greia supports more languages. Its purpose is to expose ambiguous characters, score readability, child vocabulary, accents, and short/long UI labels at actual rendered sizes.

Physical testing should consider both children who already read and younger children who rely primarily on shape/icon/audio cues.

## 9. Localization and fallback

Greia's typography system must be language-aware without making individual Activities manage host font files.

Nunito Sans is the selected default family where the required glyphs are present and suitable. As language coverage expands, Greia may need platform-owned fallback fonts for scripts or glyphs outside the selected family.

Rules:

- missing glyphs must never silently become boxes in a supported locale;
- fallback is a Greia platform/theme concern, not an Activity-specific filesystem hunt;
- localized text may need different sizing/line wrapping while preserving semantic hierarchy;
- future fallback families require the same provenance/license review as the default font;
- support for a locale must be verified against the actual bundled font files/version, not assumed from a website specimen.

## 10. Accessibility typography

Greia should preserve an extension point for a future **high-legibility/accessibility font mode**.

This document does **not** select or implement that alternate family yet. The important architectural rule is that accessibility typography should be switched through platform-owned semantic typography roles so Shell and conforming Activities change coherently.

An accessibility font mode must not require every Activity author to ship alternate font assets or manually duplicate layouts.

## 11. Platform typography roles

The long-term design system should expose semantic typography roles rather than requiring consumers to open arbitrary `.ttf` paths.

Conceptually, consumers need roles such as:

```text
body
secondary
control
title
display / celebration
```

This is intentionally **not a declaration of a current Python or Web API**. Exact role names, schema, caching objects, theme serialization, and runtime bridge become source-owned when implemented.

The architecture goal is:

```text
Greia visual style
      ↓
platform typography/theme roles
      ↓
Shell / system UI / first-party Activities / future Web runtime
```

not:

```text
Activity A → hard-coded font file
Activity B → different font loader
Shell      → another copy
Installer  → another copy
```

## 12. Runtime and low-resource requirements

Typography is part of the low-resource architecture.

Implementations should:

- load fonts once and reuse them;
- use a bounded font cache keyed by semantic family/weight/size or equivalent implementation state;
- never construct/decode font resources per frame;
- ship only the weights/glyph coverage actually justified by supported locales and design requirements;
- avoid making variable-font processing a C0 requirement without evidence;
- measure font package size and runtime memory cost on reference hardware;
- produce stable metrics across supported renderer/runtime families closely enough that layouts do not become runtime-specific designs.

The final implementation must work with Greia's existing bounded-resource UI philosophy rather than becoming a separate typography framework.

## 13. Relationship to Activities

Activity authors should not infer that selecting Nunito Sans means they should bundle their own copy into each `.greiaactivity` package.

The intended direction is a platform-owned shared typography service/theme so standard UI can reuse the system font efficiently and consistently.

Until that contract is implemented, authors must follow the current source/authoring guide rather than inventing font paths or future APIs.

Where an Activity deliberately ships a custom content font, it must:

- have a legitimate pedagogical/expressive reason;
- preserve readability;
- carry valid redistributable rights and provenance;
- include its font cost inside the Activity package/resource budget;
- not impersonate Greia system chrome or use typography to obscure required platform controls.

## 14. Relationship to awards and celebrations

ADR 0025 makes celebrations a Greia-owned presentation responsibility. Typography should reinforce that ownership.

A badge reveal or personal-best celebration may use larger Nunito Sans Bold/ExtraBold, animation, scale, sound, and artwork, while ordinary explanatory text remains calm and readable.

The celebration should feel special because of presentation—not because Greia temporarily switches to a hard-to-read novelty font.

## 15. Relationship to the current palette/theme

`runtime/theme-defaults.toml` currently owns implemented color choices such as cream backgrounds, cocoa text, sunshine/coral/leaf/ocean accents, and related theme IDs.

This style guide does not replace that source-owned contract. It records the design intention that typography, colors, icons, panels, and artwork should function as **one coherent Greia visual system**.

A future expansion of the theme model to typography should be implemented deliberately, with migrations/tests and updated authoring documentation, rather than by sprinkling font paths into individual consumers.

## 16. What Greia should avoid

Avoid as default OS styling:

- Comic Sans-like or novelty fonts chosen merely to signal “for kids”;
- highly geometric or condensed faces that sacrifice young-reader clarity;
- thin/light UI text;
- multiple unrelated type families across Shell surfaces;
- tiny desktop-style labels;
- decorative outlines/shadows that reduce glyph clarity;
- text embedded permanently into raster artwork where localization is expected;
- Activities overriding the visual identity of trusted Greia system chrome;
- font loading from network/CDN resources for core operation;
- per-Activity copies of a platform font once shared platform typography exists.

## 17. Implementation checklist for introducing Nunito Sans

Selecting the font in this document is not the same as shipping it. When implementation begins, the tranche should at minimum:

1. select and pin an upstream Nunito Sans version/source;
2. copy only the required static weights/glyph coverage into the appropriate repository/package location;
3. include the upstream OFL-1.1 license/copyright material;
4. add the font to the third-party licensing/provenance inventory required by ADR 0024;
5. define source-owned semantic typography roles and a bounded cache/load path;
6. migrate Greia-owned UI consumers through that common path rather than hard-coded per-consumer files;
7. update `skills/greia-activity-authoring/SKILL.md` when an Activity-facing typography contract actually exists;
8. validate Italian and English glyphs/accents plus the young-reader specimen;
9. perform 800×600 / 1024×600 visual review and physical Acer-class testing;
10. measure installed-size/RAM/rendering impact;
11. retain a child-safe fallback if the font resource becomes unavailable/corrupt.

No implementation PASS is implied until those source/runtime/evidence steps actually occur.

## 18. Current selected state

As of 2026-08-17:

- **visual direction:** warm, playful, coherent, readable, not babyish;
- **default interface font:** **Nunito Sans**;
- **font license:** **SIL Open Font License 1.1 (OFL-1.1)**;
- **initial weight direction:** Regular / SemiBold / Bold / ExtraBold;
- **initial deployment direction:** static weights, platform-owned and cached;
- **accessibility alternate:** extension point required, specific family not yet selected by this guide;
- **font files bundled in Greia by this documentation change:** **no**;
- **typography theme/API implemented by this documentation change:** **no**.

This distinction should remain explicit so a design decision is never mistaken for an implemented or physically verified platform capability.
