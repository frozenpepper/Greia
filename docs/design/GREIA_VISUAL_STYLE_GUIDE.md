# Greia Visual Style Guide

**Status:** accepted visual-design direction; Nunito typography and initial color-emoji/picker path implemented in source, physical/C0 evidence pending where noted  
**Date:** 2026-08-20  
**Audience:** Greia Shell designers, platform developers, Activity authors, installer/Parent UI developers, artists, reviewers, and software agents  
**Related:** `docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md`, `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md`, `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`, ADR 0018, ADR 0019, ADR 0025, `runtime/theme-defaults.toml`, `src/greia_platform/typography.py`, `src/greia_platform/emoji_palette.py`

## 1. Purpose and authority

This document is the living **visual-language and typography guide for Greia**. It defines how Greia should look and read across the child Shell, platform-owned UI, first-party Activities, celebrations/awards, installer, recovery, and parent-facing surfaces.

It complements `GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md`:

- the **asset requirements** document defines what graphical assets and production artwork Greia needs;
- this **style guide** defines the visual character and reusable presentation rules those assets and interfaces should follow.

Accepted ADRs remain authoritative for architecture and trust boundaries. Source/runtime declarations remain authoritative for exact implemented theme/UI APIs. The exact current typography implementation is owned by `src/greia_platform/typography.py`; the bounded shared emoji-palette model is owned by `src/greia_platform/emoji_palette.py`; this guide owns the visual intent and cross-product design rules.

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

Fun should come primarily from **illustration, character, motion, sound, spacing, shape, celebration, and expressive content**, not from making ordinary interface text difficult to read.

## 3. Typography decision

### 3.1 Default family — Nunito Sans

**Selected default Greia interface typeface: `Nunito Sans`.**

Nunito Sans sits deliberately between a neutral system sans-serif and an overtly childish display face:

- rounded forms make it friendly without becoming cartoon typography;
- conventional letterforms remain suitable for children who are learning to read;
- it works for both large display text and ordinary interface labels;
- the family provides sufficient weight range for hierarchy without requiring multiple unrelated font families;
- it allows Greia to create personality through size, weight, spacing, animation, and illustration rather than novelty letterforms;
- its open font license is compatible with bundling it with Greia while keeping Greia software under its own licenses.

The default design direction is therefore **one coherent family across most of the operating environment**, rather than a playful heading font paired with a separate utilitarian body font.

### 3.2 Scope of the default

Nunito Sans is the default for:

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

### 3.3 Child text letter case — CAPITALS by default

**Accepted product rule (ADR 0034):** child-facing UI words are presented in CAPITAL letters by default, because target children learn and recognize capitals first. This applies to Activity names, Collection/Category labels, instructions, buttons, feedback and achievement copy across the Shell and first-party Activities.

- The policy is platform-owned and per child: a parent may choose normal text in the Parent App (`uppercase_text` profile preference).
- Implementation authority: `src/greia_platform/child_text.py` (`display_text`), applied automatically by `LocalizedResources.text()`; Activity-local literals must go through `display_text(...)`; the Shell applies it at its child-facing render chokepoints.
- Child-authored content (Writing documents, child-typed names) is never case-transformed.
- Parent-facing surfaces keep normal sentence case; the policy is a child presentation rule, not a documentation or adult-UI rule.

## 4. Nunito Sans licensing and provenance

Nunito Sans is distributed under the **SIL Open Font License 1.1 (OFL-1.1)**.

Greia now vendors the selected static weights under `assets/fonts/nunito-sans/`, with the upstream OFL text and provenance recorded under `build/trust/nunito-sans-2.3.2.provenance`.

The font itself remains under OFL-1.1; bundling it does not relicense Greia software. The public-release provenance/licensing audit must continue to preserve the upstream copyright/license material and exact source/derivation record.

## 5. Weight system

Greia uses a small static weight set rather than making variable-font rendering a low-end runtime requirement.

| Role | Nunito Sans weight | Typical use |
|---|---|---|
| Body | Regular | ordinary explanatory text, descriptions |
| Secondary | Regular | secondary child text where hierarchy comes from size/placement |
| Control | SemiBold | buttons, navigation, short labels |
| Title | Bold | screen titles, Activity/card titles, profile names |
| Display | ExtraBold | `NEW BADGE!`, major score/award moments, very short emphasis |

Avoid Light/ExtraLight as normal child-facing UI weights. Thin strokes reduce robustness on old LCDs, low resolutions, scaling paths, and visually busy backgrounds.

The current semantic roles and exact static filenames are source-owned by `src/greia_platform/typography.py`.

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

Hello 🙂!
Bravissima! ⭐
Space 🚀 is fun
👩🏽‍🔬  🇮🇹  1️⃣  ❤️
```

The exact specimen may expand as Greia supports more languages. Its purpose is to expose ambiguous characters, score readability, child vocabulary, accents, emoji composition, and short/long UI labels at actual rendered sizes.

Physical testing should consider both children who already read and younger children who rely primarily on shape/icon/audio cues.

## 9. Localization and fallback

Greia's typography system is platform-owned and language-aware. Individual Activities must not search host font directories or implement independent fallback stacks.

Nunito Sans is the normal interface family where the required glyphs are present and suitable. As language coverage expands, additional platform-owned script fallback fonts may be added after license/provenance and real rendering review.

Rules:

- missing glyphs must never silently become boxes in a supported locale;
- fallback is a Greia platform/theme concern, not an Activity-specific filesystem hunt;
- localized text may need different sizing/line wrapping while preserving semantic hierarchy;
- fallback families require the same provenance/license review as the default font;
- support for a locale must be verified against the actual bundled font files/version, not assumed from a website specimen.

## 10. Emoji and expressive Unicode — platform requirement

### 10.1 Full emoji support is not optional polish

Greia must be able to display and edit ordinary Unicode emoji as real text content. This is especially important for young children, who naturally use emoji before or alongside fluent written language.

Emoji support belongs to the **platform typography/text layer**, not to individual Activities.

The current initial stack is:

```text
ordinary Greia text
    → Nunito Sans

emoji grapheme cluster
    → Noto Color Emoji
    → Pillow embedded-color rasterization
    → RGBA Pygame surface
```

`src/greia_platform/typography.py` owns the current Pygame implementation. `build/package-sets/platform-shell-pygame.txt` and `build/package-sets/runtime-python.txt` carry `fonts-noto-color-emoji` and `python3-regex` so the current Python/Pygame runtime has the actual font and Unicode grapheme segmentation dependency.

This is deliberately behind a Greia service boundary. A future Web or SDL3 renderer may implement the same semantics differently without changing Activity-facing text meaning.

### 10.2 Noto Color Emoji is fallback, not the Greia interface family

Nunito Sans remains Greia's visual voice. Noto Color Emoji is a specific fallback for emoji presentation.

Greia must **not** replace its semantic system iconography with Unicode emoji merely because emoji rendering exists. In particular:

- Home remains the canonical Greia Home glyph/icon, not `🏠`;
- Back remains Greia Back, not an arbitrary arrow emoji;
- audio, settings, package trust, awards, recovery and other system controls continue to use controlled Greia semantic assets;
- emoji are welcome in expressive text, child creations, messages, labels where appropriate, and Activity content.

This keeps trusted UI stable and visually controlled across font/Unicode versions.

### 10.3 Grapheme clusters are the editing unit

Many visible emoji are not one Unicode codepoint. Examples include:

```text
👍🏽       base + skin-tone modifier
👩‍🔬       ZWJ sequence
🏳️‍🌈      variation selector + ZWJ sequence
🇮🇹       regional-indicator pair
1️⃣        keycap sequence
❤️        variation-selector sequence
```

To the child these are each **one character**. Cursor movement, Backspace, Delete, selection, wrapping, hit-testing, truncation and preview generation must not split them.

The current source uses Unicode extended grapheme clusters (`\X`) from the packaged `python3-regex` implementation. `src/greia_platform/typography.py` exposes grapheme-boundary helpers for renderer/editor code. The first-party Writing Activity has been migrated to use those boundaries.

Do not implement new editable text by indexing visible characters as individual Python codepoints.

### 10.4 Persistence stays standard UTF-8

Emoji are stored as ordinary Unicode strings in Greia's logical UTF-8 text data. Do not substitute proprietary tokens such as `[GREIA_EMOJI_42]`, image filenames, or host-font glyph IDs.

That keeps child documents portable across CPU architectures, future runtimes, backups and other applications.

### 10.5 Current color-emoji rendering details are implementation facts

On the current Debian 12/bookworm target, the packaged Noto Color Emoji font uses an embedded color-bitmap strike. The current Pygame backend uses Pillow's embedded-color path at the font's supported native strike and scales the resulting RGBA glyph to the requested UI size. That backend-specific fact must remain inside `GreiaTypography`; Activities must not copy it.

The emoji surface cache is hard-bounded. Emoji must never be decoded/rasterized every frame without reuse. A present-but-corrupt/incompatible emoji resource degrades through the normal text path rather than crashing the child session; supported release images must nevertheless verify the required emoji package/font rather than treating degradation as successful release support.

### 10.6 Emoji input / picker

Greia now has an **initial source implementation** of child-facing emoji input:

- `src/greia_platform/emoji_palette.py` owns a bounded curated semantic palette;
- the first-party Writing Activity renders that model as a large visual picker inside its Greia-safe content region;
- the picker currently provides seven child-friendly categories with eighteen common emoji in each category;
- the grid derives its rows, columns and cell size from the actual safe viewport rather than assuming one physical resolution;
- selecting an item inserts the actual standard Unicode grapheme into the document.

This proves the platform model and gives Writing a usable visual route without requiring a desktop emoji keyboard shortcut. It is **not yet a universal platform picker renderer automatically available to every Greia text field or future Web runtime**. A later common picker component should reuse the same semantic palette/Unicode contract rather than inventing a second catalogue.

Normal keyboard/input-method text can still supply emoji beyond the curated picker set. Rendering is not restricted to the palette. Activities must not invent private emoji encodings to extend it.

### 10.7 Emoji acceptance

At minimum, visual/runtime acceptance should exercise:

```text
🙂 🚀 🦄
❤️ ☀️
👍🏽 👋🏻
👩‍🔬 👨‍🚀 🏳️‍🌈
🇮🇹 🇫🇷 🇯🇵
1️⃣ 5️⃣ #️⃣
```

and mixed strings at representative child UI sizes.

Acceptance is not merely “no exception.” It must check:

- no tofu/missing-glyph boxes for supported sequences;
- color pixels where color emoji are expected;
- whole-cluster cursor movement and deletion;
- correct wrapping/hit-testing around emoji;
- text/emoji presentation-selector behavior;
- bounded cache growth;
- picker containment/legibility at the supported low-resolution viewports;
- acceptable first-render and cached-render latency;
- installed-size/RSS impact on the C0/Acer floor.

The Debian font package is a meaningful disk addition, so low-resource image evidence is still required before calling the complete C0 emoji path physically accepted.

## 11. Accessibility typography

Greia preserves an extension point for a future **high-legibility/accessibility font mode**.

This document does **not** select that alternate family yet. The important architectural rule is that accessibility typography switches through platform-owned semantic typography roles so Shell and conforming Activities change coherently.

Emoji fallback remains orthogonal to the normal-text family: selecting a high-legibility body font should not require every Activity to rebuild its own emoji handling.

## 12. Platform typography roles

The current source exposes semantic typography roles rather than requiring consumers to open arbitrary `.ttf` paths:

```text
body
secondary
control
title
display
```

The exact enum/cache/fallback implementation is source-owned by `src/greia_platform/typography.py`. The design architecture is:

```text
Greia visual style
      ↓
platform typography roles + fallback
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

`src/greia_platform/pygame_ui.py` is the platform-wide Pygame import surface for shared renderer helpers and now re-exports the typography/grapheme contract and shared emoji-palette model for Pygame consumers.

## 13. Runtime and low-resource requirements

Typography is part of the low-resource architecture.

Implementations must:

- load fonts once and reuse them;
- use bounded font/glyph/surface caches;
- never construct/decode font resources per frame;
- ship only fonts justified by supported locales/design requirements;
- avoid making variable-font processing a C0 requirement without evidence;
- measure font package size and runtime memory/latency cost on reference hardware;
- produce stable enough metrics across supported renderer/runtime families that layouts do not become runtime-specific designs;
- preserve a child-safe degradation path when an optional fallback resource is missing while treating supported-release package composition as a verified build contract.

The final implementation must stay within Greia's existing bounded-resource UI philosophy rather than becoming a separate heavyweight text framework.

## 14. Relationship to Activities

Activity authors must not bundle private copies of Nunito/Noto merely to obtain ordinary Greia text behavior.

Standard Greia/Pygame UI should use the shared typography path. Activities should not:

- open `/usr/share/fonts/...` directly;
- hard-code `/opt/greia-os/assets/fonts/...` paths;
- implement their own emoji-range tables or ZWJ parser;
- split user-editable text by Python codepoint when grapheme semantics are required;
- use emoji as substitutes for protected Greia system controls.

Where an Activity deliberately ships a custom content font, it must:

- have a legitimate pedagogical/expressive reason;
- preserve readability;
- carry valid redistributable rights and provenance;
- include its font cost inside the Activity package/resource budget;
- not impersonate Greia system chrome or use typography to obscure required platform controls.

## 15. Relationship to awards and celebrations

ADR 0025 makes celebrations a Greia-owned presentation responsibility. Typography should reinforce that ownership.

A badge reveal or personal-best celebration may use larger Nunito Sans Bold/ExtraBold, animation, scale, sound, artwork, and appropriate expressive emoji where it adds meaning. Ordinary explanatory text remains calm and readable.

The celebration should feel special because of presentation—not because Greia temporarily switches to a hard-to-read novelty font.

## 16. Relationship to the current palette/theme

`runtime/theme-defaults.toml` owns implemented color choices such as cream backgrounds, cocoa text, sunshine/coral/leaf/ocean accents, and related theme IDs.

This style guide does not replace that source-owned contract. Typography, colors, icons, panels, artwork, and expressive Unicode should function as **one coherent Greia visual system**.

## 17. What Greia should avoid

Avoid as default OS styling/typography:

- Comic Sans-like or novelty fonts chosen merely to signal “for kids”;
- highly geometric or condensed faces that sacrifice young-reader clarity;
- thin/light UI text;
- multiple unrelated type families across Shell surfaces;
- tiny desktop-style labels;
- decorative outlines/shadows that reduce glyph clarity;
- text embedded permanently into raster artwork where localization is expected;
- Activities overriding the visual identity of trusted Greia system chrome;
- font loading from network/CDN resources for core operation;
- per-Activity copies of platform fonts;
- direct dependency on host fontconfig behavior as the Activity API;
- ad-hoc emoji codepoint/range logic copied between Activities;
- using emoji as a replacement for Greia semantic system icons.

## 18. Implementation/evidence checklist

For platform typography and emoji support, maintain at least:

1. pinned/provenanced Nunito Sans static weights and OFL material;
2. explicit image/runtime dependency for the selected emoji fallback font;
3. source-owned semantic typography/fallback service with bounded caches;
4. Unicode extended-grapheme segmentation for editable text;
5. mixed ordinary-text + emoji rendering without per-Activity font hunting;
6. first-party text editor deletion/cursor/wrapping/hit-testing that is grapheme-safe;
7. bounded semantic emoji-palette model plus a large Writing picker using standard Unicode insertion;
8. authoring documentation for the shared contract;
9. Italian/English glyph and accent verification plus the young-reader/emoji specimen;
10. provider-free regression tests for segmentation/editing/palette/package composition;
11. actual 800×600 / 1024×600 visual review and physical Acer-class testing;
12. installed-size/RAM/first-render/cached-render measurements;
13. child-safe behavior if a fallback resource becomes unavailable/corrupt;
14. future universal/shared picker-renderer acceptance if Greia promotes the Writing proof into a common cross-surface component.

## 19. Current state

As of 2026-08-19:

- **visual direction:** warm, playful, coherent, readable, not babyish;
- **default interface font:** **Nunito Sans**;
- **Nunito license:** **SIL Open Font License 1.1 (OFL-1.1)**;
- **bundled Nunito weights:** Regular / SemiBold / Bold / ExtraBold;
- **semantic typography service:** implemented in `src/greia_platform/typography.py`;
- **color emoji fallback:** source-implemented with system `Noto Color Emoji` + Pillow embedded-color rendering;
- **emoji failure behavior:** source-implemented safe degradation rather than child-session failure, without weakening release package verification requirements;
- **grapheme segmentation:** source-implemented with packaged `python3-regex` Unicode `\X` path plus a development-host fallback;
- **Python/Pygame package composition:** declares `fonts-noto-color-emoji`, `python3-pil`, `python3-pygame`, and `python3-regex`;
- **shared emoji-palette model:** implemented in `src/greia_platform/emoji_palette.py`;
- **Writing Activity:** migrated to grapheme-safe editing, mixed text/emoji rendering, and an initial large visual emoji picker whose grid stays inside the actual safe viewport;
- **provider-free emoji/Writing regressions:** committed, **not yet executed in an owner-controlled checkout at this head**;
- **universal cross-surface emoji-picker renderer:** not yet implemented; the Writing implementation is the current reference consumer;
- **C0/Acer installed-size/RAM/latency/visual acceptance:** pending;
- **accessibility alternate normal-text family:** extension point required, specific family not yet selected by this guide.

Do not convert this source status into a physical/release-support claim until the current tests and low-resource evidence actually execute.

## 20. Constraint-native character and illustration language

As of 2026-08-20, Greia's **default reusable character language** is constraint-native rather than traditionally articulated. The accepted construction grammar is owned in detail by `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md`.

The default archetypes are:

- **Puff** — one soft round/oval/fluffy mass, large face, tiny or absent limbs, a few identity cues;
- **Bean** — one compact upright rounded/drop mass, large face, tiny feet and optional wing/flap shapes;
- **Cutout Critter** — a deliberately flat felt/sticker/paper-cut construction using a few large overlapping layers;
- **Object Friend** — the pedagogical object remains the primary silhouette and gains a face/tiny optional appendages.

Default character construction should usually remain within:

```text
1 main body mass
1 face region
0–2 tiny feet
0–2 tiny arms/wings/flaps
0–3 identity attachment groups
```

Identity should come from silhouette, face, major color blocks and two or three strong cues rather than realistic anatomy. A unicorn may read through horn + ears + localized rainbow tuft; a fox through ears + muzzle/chest patch + chunky tail; an owl through mask + beak + flaps. If a species only reads after adding a complex jointed skeleton, simplify the design brief instead.

For reusable vector masters, the current accepted review convention is a 256×256 logical artboard with small-size checks at 128 and 64 px where those sizes are supported. At the 256 master, normal primary contours are about 3–4 px and secondary contours about 2–3 px, with rounded joins/caps and tinted darks such as cocoa/plum/navy rather than pure black. Depth should use broad flat or restrained two-stop fills and a small number of large patches rather than detailed fur, glossy 3D rendering or micro-texture.

The face is the primary emotional engine. Large eyes, simple mouths, cheeks and small whole-body posture changes should carry more emotional range than articulated anatomy. Normal educational mistakes must never use anger, shame, or a disappointed-at-the-child expression.

The first approved **static style anchors** are Lilli (unicorn Puff), Nino (owl Bean), Tito (fox Puff), and Momo (friendly monster Puff). Their approval establishes the visual direction and reusable construction grammar; it does **not** claim that the current SVGs are final release assets, runtime-integrated character packages, or physically accepted on C0 hardware. They may continue to receive visual refinement without reopening the architecture decision.

Character motion is being standardized separately in `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`. The accepted principle is semantic whole-body motion plus face state and optional bounded identity-cue/FX response. Animation must enrich a state, while a clear static fallback remains sufficient for meaning. Runtime implementation must remain lightweight and architecture-reviewed rather than introducing a parallel animation engine inside Activities.

## 20.1 Accepted SVG recipe and glossy-3D retirement (2026-10-15)

The binding construction recipe for all new and redrawn Greia vector art (canvas per asset kind, palette tokens, stroke and shading rules, forbidden constructs, size budgets, 48 px legibility and review procedure) is `docs/design/GREIA_SVG_AUTHORING_RULES.md`; this guide keeps the *language* (§20) and that file owns the *recipe*. The glossy painted-3D raster core icons (`assets/icons/core/v1`) are a style outlier and are being replaced by flat SVG-built icons under that recipe, keeping their IDs. Opus is the selected SVG authoring model per the 2026-10-15 bake-off (`icon_marble_run`, `leo_celebrate`, `scene_river_valley`); outputs are still accepted only after rendered-pixel inspection. See `docs/reviews/visual/2026-10-15_asset_library_audit/REVIEW.md` (archived; see git history).
