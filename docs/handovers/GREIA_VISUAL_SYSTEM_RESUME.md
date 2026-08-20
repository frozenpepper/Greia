# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-20  
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
- after the consumption seam is proven, keep converting it into **visible real Greia improvements** rather than endless proof-only plumbing.

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

`ui.shadow.soft` is simulator-accepted beneath launcher Activity tiles.

Evidence recorded in `LOCAL_AGENT_RESULT.md`:

```text
6/6 responsive simulator rows PASS
selection PASS
hover PASS
Activity launch lifecycle PASS
missing catalogue fallback PASS
malformed catalogue fallback PASS
corrupt/missing PNG fallback PASS
299 frames / 10.165 s = 29.41 FPS sanity
```

Evidence class: **SIMULATOR VISUAL REVIEW**.

No physical Acer/Pi visual-performance claim and no R7 closure.

---

# 5. Activity semantic seam exists in source

The first Python Activity semantic request/resolution contract is in:

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

Shape Garden resolves `ui.shadow.soft` once at startup, scales it once and reuses it. Missing/invalid shared visuals keep the Activity playable.

This Activity seam is still **SOURCE only** until:

```text
docs/testing/2026-08-20_V5_ACTIVITY_SHARED_VISUAL_SIMULATOR.md
```

passes in the Activity Simulator.

---

# 6. Substantial visible shared UI is now in source

The production child Shell now also consumes:

```text
ui.card.activity/default
ui.card.activity/focused
```

through:

```text
src/greia_launcher/shared_ui_presentation.py
src/greia_launcher/child_shell.py
```

The shared card path is intentionally presentation-only:

- normal cards use the reviewed default master;
- selected / hovered / launching cards use the focused master;
- authored 360:430 portrait geometry is preserved instead of stretching into a square;
- icon and localized title are placed into the authored illustration well and label band;
- logical launcher hit targets/navigation/lifecycle remain unchanged;
- the existing primitive tile renderer is the fail-soft fallback if the optional shared card path fails.

This is intended to be a **visibly different launcher**, not another invisible plumbing proof.

Required simulator protocol:

```text
docs/testing/2026-08-20_V5_SHARED_UI_CARD_SIMULATOR.md
```

Current evidence: **SOURCE only**.

---

# 7. Current exact next work

If the Shape Garden simulator run is already in progress, finish it; do not restart from scratch merely because the visible card source landed meanwhile.

Then:

```text
1. sync current main
2. complete/record Shape Garden semantic seam simulator evidence
3. read docs/testing/2026-08-20_V5_SHARED_UI_CARD_SIMULATOR.md
4. run the real Greia child Shell in the Activity Simulator
5. verify shared portrait cards are visibly present
6. verify default/focused states, hover, selection and launch animation
7. run the 6-row responsive matrix
8. verify missing/malformed catalogue fallback
9. verify corrupt shared-card PNG fallback
10. perform frame-count sanity
11. fix only shared/root causes
12. rerun affected simulator cases
13. update active plan, this resume and HANDOVER with exact evidence
14. commit/push accepted work to main
```

After both current simulator gates pass:

1. implement the Web Activity semantic adapter/transport using the same IDs/variants without exposing host paths;
2. continue **visible** Greia Shell integration with an existing shared UI family only where it materially improves the real product (`ui.panel.base` / category or launch surfaces are the likely next candidates, followed by `ui.button.primary`);
3. do not return to new environment-pack production unless a concrete reusable gap appears.

---

# 8. Current simulator protocols

```text
docs/testing/2026-08-20_V5_ACTIVITY_SHARED_VISUAL_SIMULATOR.md
docs/testing/2026-08-20_V5_SHARED_UI_CARD_SIMULATOR.md
```

For owner-directed local-agent runtime/visual/fallback/responsive acceptance, use the Greia Activity Simulator.

Do not use GitHub Actions unless the owner explicitly authorizes hosted execution.

The simulator bridge is local loopback only. No Cloudflare/tunnel/hosted service belongs in this workflow.

---

# 9. Rejected/drift directions

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

# 10. Documentation map

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

First Shell-consumer execution result:

```text
LOCAL_AGENT_RESULT.md
```

Current simulator protocols:

```text
docs/testing/2026-08-20_V5_ACTIVITY_SHARED_VISUAL_SIMULATOR.md
docs/testing/2026-08-20_V5_SHARED_UI_CARD_SIMULATOR.md
```

---

# 11. End-of-session rule

Update this file whenever any of these changes materially:

- active visual phase;
- next exact action;
- runtime-consumption state;
- evidence boundary;
- blocker;
- testing rule;
- accepted/rejected architectural direction.

Keep this file concise. Chronology belongs in the active plan's append-only progress ledger; stable architecture belongs in `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`; project-wide state belongs in `HANDOVER.md`.
