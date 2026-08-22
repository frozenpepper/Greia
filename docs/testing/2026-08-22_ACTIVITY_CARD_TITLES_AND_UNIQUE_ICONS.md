# Activity Card Titles & Unique Icons — Launcher Productization Gate

**Status:** ACTIVE IMPLEMENTATION / LOCAL-AGENT EXECUTION REQUIRED  
**Date:** 2026-08-22  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`

This is the next exact cross-cutting child-UX/visual gate.

---

# 1. Problem to solve

The owner has identified two unacceptable launcher problems:

1. **Activity names are effectively unreadable** because the current launcher card path tries to fit the localized title onto one line and then progressively shortens it. This wastes the available label area and causes routine clipping/ellipsis.
2. **Activity icons have weak identity and inconsistent framing.** Several current icons are visibly clipped or poorly fitted, and many Activities reuse the same small set of shared icons. Activities need recognisable individual identities.

The existing implementation confirms the title problem: `GreiaLauncherPresentation._render_activity_label()` renders one line, shrinks to 16px, then character-slices until an ellipsis fits. The shared card path calls that same helper inside the authored card label region.

The launcher already supports package-owned PNG/WebP icons through `package:...`; preserve that architecture rather than inventing another icon system.

---

# 2. Required reading

Before editing, read the repository authorities required by `AGENTS.md`, then specifically:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
skills/greia-activity-authoring/SKILL.md
skills/greia-visual-authoring/SKILL.md
src/greia_launcher/presentation.py
src/greia_launcher/shared_ui_presentation.py
src/greia_launcher/activity_icon.py
src/greia_platform/activity_assets.py
```

Inspect existing launcher/card/icon tests before adding coverage.

---

# 3. Title presentation contract

## 3.1 Normal card titles MUST use two lines

Replace the current single-line-first behavior for Activity cards with a two-line title presentation designed for the actual authored card label area.

Required behavior:

- maximum **2 visible lines** on the normal card;
- word-aware wrapping first;
- for languages/strings without useful spaces, fall back to safe grapheme-aware wrapping rather than naïve Python codepoint slicing;
- centered title block;
- preserve normal font proportions; never geometrically squash text;
- prefer a comfortable child-readable size and only reduce to the existing accepted minimum when genuinely necessary;
- use the currently wasted vertical room in the card rather than leaving most of the title area empty;
- no title pixels may escape the card/title region.

## 3.2 Card display cap

Use an explicit defensive card-display cap of **48 grapheme clusters** before the normal-card ellipsis is applied.

This is deliberately far more generous than the current practical single-line limit and is intended to support normal two-line Activity names.

Do **not** treat Python `len()` slicing as correct Unicode title segmentation if an existing Greia grapheme helper is available. Inspect the repository first and reuse the existing Unicode/grapheme authority where possible.

If the source title exceeds the defensive 48-grapheme card cap:

- the normal card may end in `…`;
- the hover/focus disclosure described below must still expose the complete localized source title.

## 3.3 Full title on hover/focus

When the pointer genuinely hovers an Activity card, display the **full localized Activity name** in a small Greia-native tooltip/callout/pill associated with that card.

Also show the same full-title disclosure for the currently keyboard-selected/focused Activity so pointer-only behavior is not the sole path to the information.

Requirements:

- full source title, not the card-truncated form;
- bounded to the visible Shell/panel area;
- may wrap to multiple lines as needed;
- must not cover the platform Home/Back protected region;
- must not intercept launch/click authority or create a new navigation layer;
- fail-soft presentation only;
- tooltip/callout should be visually modest and disappear when no card is hovered/focused.

Do not bake the full title into cached per-tile surfaces if doing so makes hover state stale or expensive. Prefer drawing the disclosure in the final launcher composition pass.

---

# 4. Icon rendering contract

## 4.1 Fix launcher fitting first

Package-owned icons currently get smooth-scaled directly to `(size, size)`. Replace this with a **contain-fit** path:

- preserve source aspect ratio;
- center the icon in a square target surface;
- reserve approximately **10–12% safe padding** around meaningful artwork before launcher shadow/depth treatment;
- never crop meaningful source pixels merely to fill the square;
- transparent padding is acceptable and preferred;
- the launcher shadow must also fit inside the card content region rather than being clipped by the icon box.

Shared semantic legacy icons should receive equivalent safe framing where practical so old packages do not remain visibly clipped.

Do not add runtime SVG support. Runtime launcher icons remain PNG/WebP or existing shared catalogue renditions.

## 4.2 Activity identity policy

From this gate forward, **every new or substantively updated user-facing Activity must provide its own recognisable package-owned launcher icon** unless a documented platform-owned exception applies.

Canonical manifest form:

```toml
[activity]
icon = "package:assets/icon.png"
```

PNG is the default recommendation; WebP remains supported by the existing package boundary.

Shared semantic icon IDs remain a compatibility/fallback mechanism, not the preferred identity mechanism for new Activities.

## 4.3 Authoring fallback when image generation is unavailable

This MUST be made explicit in both authoring skills.

An Activity-authoring agent does **not** need access to an image-generation service in order to provide an icon.

Required fallback workflow:

```text
concept / silhouette
→ author a simple vector icon (normally SVG) locally
→ render/bake it at authoring/build time into PNG
→ ship only the supported package icon reference in activity.toml
```

The source SVG may remain in an Activity-local source-art folder when package validation allows it, but the launcher must consume the baked PNG/WebP, never runtime-rasterize the SVG.

## 4.4 Icon visual rules for authoring skills

Update `skills/greia-activity-authoring/SKILL.md` and `skills/greia-visual-authoring/SKILL.md` so they clearly state:

- unique Activity icon is part of normal Activity completion, not optional polish;
- icon should communicate the Activity's own mechanic/theme, not merely its broad Collection;
- square source canvas;
- meaningful art kept inside a safe zone with roughly 10–12% outer padding;
- strong silhouette at small launcher size;
- transparent background where appropriate;
- no required readable text;
- no baked language flags (Greia owns dynamic language presentation);
- no screenshot-as-icon unless intentionally designed and still readable at launcher scale;
- if no generated/painted image is available, create a clean vector icon and bake it to PNG/WebP;
- inspect the actual launcher-rendered icon before considering the Activity visually complete.

---

# 5. First-party icon migration

Audit all current first-party Activities under `activities/`.

Produce a small machine-readable report listing for each Activity:

```text
activity id
current icon declaration
shared semantic vs package-owned
icon source path
whether another Activity uses the same visual/icon ID
visible clipping/framing issue yes/no
migration action
```

Then migrate the current built-in child-facing Activities away from the repeated-small-icon-set problem.

Expected target:

- each current first-party Activity has a distinct package-owned icon that visually belongs to that Activity;
- do not create 19 complex paintings merely to satisfy uniqueness;
- use existing Activity art where it provides a strong identity;
- otherwise create concise vector-authored icons and bake them to PNG;
- shared/common stylistic treatment is welcome, but silhouettes/content must be distinct;
- preserve package footprint discipline.

Do not modify third-party/fixture manifests merely to eliminate deliberate test cases.

---

# 6. Code quality requirements

Do not solve this with scattered magic numbers in multiple renderers.

Prefer small reusable helpers/contracts for:

- title wrapping/measurement;
- card title surface generation;
- full-title disclosure layout;
- contain-fit icon composition.

The shared-card path and primitive/fallback card path must agree on title/icon semantics.

Keep caches bounded. Include all new layout-relevant inputs in cache keys. Hover tooltip state must not poison static card caches.

Do not deepen X11 coupling or alter Activity lifecycle/trust/navigation authority.

---

# 7. Tests required

Add/extend focused automated tests covering at least:

### Titles

- short title remains one line when natural;
- medium title wraps to two lines rather than premature ellipsis;
- long title is bounded to two lines and defensive 48-grapheme card cap;
- non-ASCII/multilingual title does not corrupt grapheme sequences;
- full source title is available to hover/focus disclosure even when card text is shortened;
- no label surface exceeds its assigned bounds.

### Icons

- non-square package icon is contain-fitted without distortion;
- meaningful edge pixels are not clipped by launcher fitting/shadow;
- invalid package icon still follows existing fail-soft behavior;
- cache remains bounded;
- first-party icon audit detects duplicate/reused icon identity where forbidden by the new policy;
- migrated first-party package icons validate through the existing package/icon validator.

Run the closest existing launcher/card/package/Activity tests as well.

---

# 8. Simulator acceptance

This is a child-facing launcher change, so source tests alone are not enough.

Create review directory:

`docs/reviews/visual/2026-08-22_activity-card-titles-and-unique-icons/`

Required evidence includes at least:

1. `01-before-title-clipping.png` — current/baseline title problem if reproducible from retained baseline or pre-change capture;
2. `02-two-line-titles-1024x600.png` — several normal Activity cards, including names that use both lines;
3. `03-full-title-hover.png` — hovered long-title Activity with complete localized name visible;
4. `04-full-title-keyboard-focus.png` — keyboard-selected full-title disclosure;
5. `05-unique-icons-grid-1024x600.png` — current first-party grid showing clearly distinct icons;
6. `06-icon-safe-padding-proof.png` — icons previously prone to clipping now visibly contained;
7. `07-responsive-large-1024x600.png`;
8. `08-responsive-compact-1366x768.png`;
9. `09-responsive-normal-1280x800.png`;
10. `10-long-localized-title.png` — intentionally long localized fixture proving wrap/ellipsis + full disclosure;
11. `11-non-square-package-icon.png` — contain-fit proof;
12. `12-icon-fallback.png` — malformed/missing package icon fail-soft proof.

Do not use decorative mockups. Capture the real Greia Shell/Activity catalogue path through the Simulator.

Create:

- `OWNER_RECHECK.md`
- `runtime-audit.json`
- `simulator-trace.json`
- `first-party-icon-audit.json`

Package a narrow owner-transfer bundle:

`GREIA_VISUAL_REVIEW_ACTIVITY_CARD_TITLES_UNIQUE_ICONS_2026-08-22.zip`

Include only the curated evidence and audit/recheck/trace files.

---

# 9. Documentation updates required in the same tranche

Update, as applicable:

```text
skills/greia-activity-authoring/SKILL.md
skills/greia-visual-authoring/SKILL.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

Record clearly that:

- normal Activity cards support two-line names;
- card display has a defensive 48-grapheme cap;
- full title appears on hover/focus;
- unique package-owned icons are the normal authoring requirement;
- vector→PNG/WebP baking is the explicit no-image-generator fallback;
- shared semantic Activity icons are legacy/compatibility rather than the preferred new-Activity identity path.

If implementation changes a source-owned API/validation contract, update the exact source tests/docs that own it rather than only prose.

---

# 10. Verification / stop conditions

At minimum run:

```text
make validate
make visual-assets-check
```

plus all focused launcher/card/icon/package/authoring-skill tests touched by this tranche.

Run `make verify` if the local environment can legitimately complete it without invoking unauthorized hosted CI.

Stop and report rather than claiming PASS if:

- two-line labels still clip routine Activity names;
- the full-title disclosure can cover protected Home/Back chrome;
- package icons are distorted or crop meaningful art;
- first-party Activities still visibly collapse onto the same small repeated icon set without documented exception;
- icon migration breaks package validation or materially inflates footprint;
- the implementation requires runtime SVG rasterization;
- Simulator evidence does not come from the real child Shell.

---

# 11. Return contract

Commit and push coherent work to `origin/main`.

Return to the owner only:

1. concise implementation summary;
2. exact test/verification results;
3. exact review directory;
4. exact transfer ZIP path/name;
5. exact commit SHA.

Do not paste this protocol back into chat.
