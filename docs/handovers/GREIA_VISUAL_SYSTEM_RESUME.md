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
- visual work must not deepen provisional X11 coupling or bypass protected platform UI/chrome architecture.

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

# 4. V5 Shell seam is proven

The active phase remains **V5 — shared consumption/integration**.

Current proven Shell flow:

```text
reviewed SVG master
→ explicit source manifest
→ build-time PNG rendition
→ generated runtime catalogue
→ AssetCatalogue
→ PygameVisualSurfaceCache
→ real Greia Shell consumer
```

`ui.shadow.soft` is the first accepted shared Shell visual consumer beneath launcher Activity tiles.

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

# 5. Activity semantic seam now exists in source

The first Python Activity semantic request/resolution contract is now implemented in:

```text
src/greia_platform/activity_api.py
```

Current API:

```python
get_shared_visual(asset_id, variant="default")
get_shared_visual_path(asset_id, variant="default")
```

`get_shared_visual(...)` returns a read-only `SharedVisualReference` with semantic ID, kind, role, variant and the current Python runtime path realization.

Important invariants:

- Activity requests semantic ID + explicit variant;
- Activity does not supply an arbitrary host path;
- Activity cannot mutate the catalogue;
- core icons remain available when optional generated visuals are absent/invalid;
- unknown visual IDs/variants fail narrowly;
- Activity-private art remains supported;
- this does not freeze the future Web transport as a filesystem path API.

First source consumer:

```text
activities/shape_garden/main.py
```

Shape Garden resolves `ui.shadow.soft` once at startup, scales it once to a bounded reference size, and reuses that prepared surface while drawing shapes. Missing/invalid shared visuals keep the Activity playable.

This Activity seam is currently **SOURCE only** until simulator acceptance completes.

---

# 6. Current exact next work

Do not create more artwork and do not add another launcher-only decorative consumer yet.

The exact next action is now:

```text
1. sync current main
2. read docs/testing/2026-08-20_V5_ACTIVITY_SHARED_VISUAL_SIMULATOR.md
3. execute Shape Garden through the real Greia Activity Simulator
4. verify normal semantic visual consumption
5. verify missing generated catalogue fallback
6. verify malformed generated catalogue fallback
7. verify corrupt/missing soft_shadow.png fallback
8. verify Home/input lifecycle
9. execute the full responsive simulator matrix
10. perform frame-count sanity with many shapes present
11. fix only shared owners/root causes
12. rerun affected simulator cases
13. update active plan, this resume and HANDOVER with exact evidence
14. commit/push accepted work to main
```

After that gate passes, the next architecture task is the **future Web Activity equivalent** using the same semantic IDs/variant names through a controlled URL/handle adapter rather than host filesystem access.

Only after the Activity reuse seam is established should another Shell-only UI consumer (`ui.panel.base`, `ui.card.activity`, `ui.button.primary`) be considered.

---

# 7. Current simulator protocol

Use:

```text
docs/testing/2026-08-20_V5_ACTIVITY_SHARED_VISUAL_SIMULATOR.md
```

For owner-directed local-agent runtime/visual/fallback/responsive acceptance, use the Greia Activity Simulator.

Do not use GitHub Actions unless the owner explicitly authorizes the hosted execution.

The simulator bridge is local loopback only. No Cloudflare/tunnel/hosted service belongs in this workflow.

---

# 8. Rejected/drift directions

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
- broad exception swallowing to hide optional-visual failures.

---

# 9. Documentation map

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

Current Activity semantic simulator protocol:

```text
docs/testing/2026-08-20_V5_ACTIVITY_SHARED_VISUAL_SIMULATOR.md
```

---

# 10. End-of-session rule

Update this file whenever any of these changes materially:

- active visual phase;
- next exact action;
- runtime-consumption state;
- evidence boundary;
- blocker;
- testing rule;
- accepted/rejected architectural direction.

Keep this file concise. Chronology belongs in the active plan's append-only progress ledger; stable architecture belongs in `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`; project-wide state belongs in `HANDOVER.md`.
