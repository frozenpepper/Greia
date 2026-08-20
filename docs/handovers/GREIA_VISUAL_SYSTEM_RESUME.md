# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-21  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Active plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Project-wide handover:** `HANDOVER.md`

---

# 1. Purpose

This is the fastest safe way to resume Greia art/graphics work in a new session.

Read, in order:

```text
1. AGENTS.md
2. docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
3. docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
4. this file
5. HANDOVER.md
6. skills/greia-visual-authoring/SKILL.md
7. the exact source files for the current V5 task
```

Do not resume from chat memory alone.

---

# 2. Accepted production direction

The visual system remains:

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → explicit semantic runtime consumption → Shell/Activity reuse**

Non-negotiables:

- asset-first; do not return to crude scene-first mockups;
- polished storybook/toy-diorama character and environment language;
- good static readability at low resolution;
- reuse generic assets rather than repainting duplicates;
- no runtime SVG rasterization on low-end targets;
- no arbitrary runtime directory scanning;
- no per-frame image decode/scale from disk;
- runtime image/surface caches stay bounded;
- visual work must not deepen provisional X11 coupling or bypass protected platform UI/chrome architecture;
- now that the consumption seam is proven, keep converting it into **visible real Greia improvements** rather than proof-only plumbing.

Core characters remain Lilli, Nino, Tito and Momo in the accepted Puff/Bean direction. Character minutiae do not block V5.

---

# 3. Source library already exists

Do not create another environment pack by default.

```text
assets/visual/environments/forest_meadow/v0.2/
assets/visual/ui/v0.1/
assets/visual/environments/workshop/v0.1/
assets/visual/environments/clinic/v0.1/
assets/visual/environments/reading_classroom/v0.1/
assets/visual/environments/fantasy_village_night/v0.1/
assets/visual/environments/water_pond/v0.1/
```

Inventories:

```text
assets/visual/library_v0.1.toml
assets/visual/packs_v0.1.toml
```

Most source packs remain candidate artwork with SOURCE + DESKTOP VISUAL REVIEW evidence. Do not convert pack presence into release approval.

---

# 4. V5 proven Shell seam

The active phase remains **V5 — shared consumption/integration**.

Proven Shell flow:

```text
reviewed SVG master
→ explicit source manifest
→ build-time PNG rendition
→ generated runtime catalogue
→ AssetCatalogue
→ PygameVisualSurfaceCache
→ real Greia Shell consumer
```

Accepted visible/shared Shell consumers:

```text
ui.shadow.soft       SIMULATOR VISUAL REVIEW
ui.card.activity     SIMULATOR VISUAL REVIEW
ui.panel.base        SIMULATOR VISUAL REVIEW
ui.button.primary    SIMULATOR VISUAL REVIEW
```

The latest accepted category-button run also confirmed category open/back navigation, isolated hover-button fallback, full responsive matrix and ~29.6 FPS simulator sanity.

No physical Acer/Pi visual-performance claim and no R7 closure.

---

# 5. Activity semantic seam exists in source

The Python Activity semantic request/resolution contract is in:

```text
src/greia_platform/activity_api.py
```

Current API:

```python
get_shared_visual(asset_id, variant="default")
get_shared_visual_path(asset_id, variant="default")
```

First source consumer:

```text
activities/shape_garden/main.py
```

Shape Garden remains a non-blocking SOURCE proof. Do not let it displace visible Shell work again. Future Web Activity support must use the same semantic IDs/variants through a controlled URL/handle adapter rather than host path exposure.

---

# 6. Current visible Shell architecture

Implementation:

```text
src/greia_launcher/shared_ui_presentation.py
src/greia_launcher/profile_chrome_presentation.py
src/greia_launcher/child_shell.py
assets/catalog/shared_visuals_v1_source.toml
```

Already accepted:

- `ui.panel.base` frames the profile picker and Activity catalogue;
- `ui.card.activity/default|focused` renders Activity tiles;
- `ui.button.primary/default|hover` renders the root category row;
- `ui.shadow.soft` provides shared tile grounding;
- all remain presentation-only with narrow fail-soft fallback.

A later source fix also aligned the Activity grid to the authored inner region of `ui.panel.base`; preserve that relationship when changing grid/panel geometry.

---

# 7. Current exact gate — shared profile identity frame

New source consumer:

```text
ui.avatar.frame/default
```

Source master:

```text
assets/visual/ui/v0.1/avatar_frame.svg
```

Source rendition declaration:

```text
assets/catalog/shared_visuals_v1_source.toml
```

Expected generated runtime path after `make visual-assets`:

```text
assets/visual/runtime/v1/ui/avatar_frame.png
```

Implementation:

```text
src/greia_launcher/profile_chrome_presentation.py
```

`SharedUiProfileChromeMixin` overlays the reviewed frame in two real child-Shell locations:

1. each visible profile identity in the profile picker;
2. the active-profile switcher at the top-left of the Activity catalogue.

It deliberately leaves profile storage, selection, hit targets and lifecycle in the existing launcher. The base primitive profile treatment is already drawn first, so a missing/corrupt frame falls back without replacing profile authority.

Current evidence: **SOURCE only** until the required simulator protocol passes.

Required protocol:

```text
docs/testing/2026-08-21_V5_SHARED_PROFILE_IDENTITY_SIMULATOR.md
```

The local agent must regenerate runtime renditions first with `make visual-assets`, then execute all runtime/visual/fallback/responsive acceptance through the Greia Activity Simulator.

---

# 8. Exact continuation sequence

```text
1. sync current main
2. read docs/testing/2026-08-21_V5_SHARED_PROFILE_IDENTITY_SIMULATOR.md
3. run make visual-assets to generate ui.avatar.frame/default PNG + catalogue entry
4. start the real Greia Activity Simulator
5. verify profile-picker shared frames
6. verify active-profile switcher shared frame
7. verify profile switch lifecycle
8. verify missing/malformed catalogue fallback
9. verify corrupt avatar-frame PNG fallback is isolated while panel/cards/buttons remain shared
10. run full responsive matrix
11. run frame-count sanity
12. fix only shared/root causes
13. update plan/resume/HANDOVER/LOCAL_AGENT_RESULT.md
14. commit and push accepted work to main
```

After this gate, continue with another coherent product-visible UI tranche or the Web semantic adapter. Do not return to new environment-pack production unless a concrete reusable coverage gap appears.

---

# 9. Simulator protocols

Accepted visible-Shell protocols:

```text
docs/testing/2026-08-20_V5_SHARED_UI_CARD_SIMULATOR.md
docs/testing/2026-08-20_V5_SHARED_UI_PANEL_SIMULATOR.md
docs/testing/2026-08-20_V5_SHARED_UI_CATEGORY_BUTTON_SIMULATOR.md
```

Current pending protocol:

```text
docs/testing/2026-08-21_V5_SHARED_PROFILE_IDENTITY_SIMULATOR.md
```

For owner-directed local-agent runtime/visual/fallback/responsive acceptance, use the Greia Activity Simulator.

Do not use GitHub Actions unless the owner explicitly authorizes hosted execution.

The simulator bridge is local loopback only. No Cloudflare/tunnel/hosted service belongs in this workflow.

---

# 10. Rejected/drift directions

Do not resume these as current work:

- complex traditional character rigs as the default;
- generated sprite sheets treated as production-ready;
- fake expression overlays / non-blinking blink states;
- crude full-screen UI/background mockups;
- decorative HTML presentations instead of real reusable assets;
- one-shot concept scenes as source architecture;
- more environment packs without a concrete reuse gap;
- runtime SVG rendering on low-end targets;
- arbitrary visual-directory discovery;
- a second visual catalogue or second image-cache framework;
- per-frame PNG decode/scale;
- unbounded caches;
- simulator-specific production launcher code;
- per-resolution launcher forks;
- broad exception swallowing to hide optional-visual failures;
- endless testing of visually irrelevant proof consumers after the architecture seam is already established.

---

# 11. Documentation map

Main stable architecture/index:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
```

Current sequencing/history:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
```

Visual language / inventory / character details:

```text
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md
docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
```

Practical production rules:

```text
skills/greia-visual-authoring/SKILL.md
```

Source-tree summary:

```text
assets/visual/README.md
```

Execution/result authority:

```text
LOCAL_AGENT_RESULT.md
```

---

# 12. End-of-session rule

Update this file whenever any of these changes materially:

- active visual phase;
- next exact action;
- runtime-consumption state;
- evidence boundary;
- blocker;
- testing rule;
- accepted/rejected architectural direction.

Keep this file concise. Chronology belongs in the active plan's append-only progress ledger; stable architecture belongs in `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`; project-wide state belongs in `HANDOVER.md`.
