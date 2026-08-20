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

# 4. V5 architecture now proven in the Shell

The active visual phase is still **V5 — shared consumption/integration**, but the first Shell-consumer gate is complete.

Current implemented flow:

```text
reviewed SVG master
→ assets/catalog/shared_visuals_v1_source.toml
→ tools/build_visual_renditions.py / rsvg-convert
→ assets/visual/runtime/v1/.../*.png
→ assets/catalog/shared_visuals_v1.toml
→ AssetCatalogue
→ PygameVisualSurfaceCache
→ real Greia Shell consumer
```

Current source owners:

```text
src/greia_platform/assets.py
src/greia_platform/pygame_visual_assets.py
src/greia_launcher/visual_assets.py
src/greia_launcher/main.py
src/greia_launcher/presentation.py
assets/catalog/core_icons_v1.toml
assets/catalog/shared_visuals_v1_source.toml
assets/catalog/shared_visuals_v1.toml
tools/build_visual_renditions.py
tools/validate_visual_renditions.py
```

Important invariants:

- core icons and shared visuals use one semantic namespace;
- variants are explicit and require `default`;
- catalogue roots and paths remain contained;
- duplicate IDs fail;
- generated shared visuals remain optional for launcher startup;
- one bounded Pygame surface cache performs PNG decode/scale on miss and reuse on hit;
- generated shared visuals fail soft to the established primitive/static launcher path.

---

# 5. Accepted first runtime consumer

`ui.shadow.soft` is no longer a candidate. It is the **first accepted shared Shell visual consumer**.

It is consumed beneath existing launcher Activity tiles without changing tile hit geometry, responsive grid geometry, label-band geometry, selection behavior, or Activity launch lifecycle.

Current fallback remains `draw_soft_shadow`.

The integration also established:

- generated `assets/visual/runtime/v1/ui/soft_shadow.png`;
- generated `assets/catalog/shared_visuals_v1.toml`;
- `load_launcher_assets(...)` integration in `LauncherApplication`;
- one launcher-owned `PygameVisualSurfaceCache`;
- display/viewport cache invalidation;
- malformed optional visual catalogues contained by `AssetCatalogueError`;
- corrupt/missing optional PNGs contained by the launcher visual fallback;
- correct RGB simulator frame capture.

Evidence is recorded in `LOCAL_AGENT_RESULT.md`.

---

# 6. Simulator acceptance already completed

The first consumer passed the owner-directed Activity Simulator tranche.

Accepted matrix:

```text
1024×600  + normal
1024×600  + large
1280×800  + normal
1366×768  + compact
1920×1080 + normal
1111×700  + normal
```

Accepted interactions:

```text
keyboard selection
pointer hover
Activity launch lifecycle
```

Accepted fail-soft cases:

```text
missing generated shared catalogue
malformed generated catalogue
corrupt/missing optional ui.shadow.soft PNG
```

Frame sanity evidence:

```text
299 frames / 10.165 s = 29.41 FPS
```

Evidence class:

```text
SIMULATOR VISUAL REVIEW
```

Explicit non-claims:

- no Acer/Raspberry Pi physical visual-performance claim;
- no R7 architecture closure;
- no blanket release-art approval for the rest of the visual library.

---

# 7. Current exact next work

Do **not** produce another environment pack and do **not** restyle the whole launcher.

The next V5 tranche is to generalize the proven seam instead of multiplying one-off consumers.

Proceed in this order:

```text
1. inspect current AssetCatalogue / PygameVisualSurfaceCache / Activity runtime boundaries
2. define the smallest renderer-neutral semantic shared-visual request contract for Activities
3. keep Python and future Web Activities converging on the same semantic IDs + explicit variants
4. do not expose arbitrary host filesystem paths or catalogue mutation to Activities
5. add the first controlled Activity-facing implementation without creating a second catalogue/cache system
6. keep Activity-private art supported
7. prove the Activity-facing path through the Greia Activity Simulator
8. only after that, decide whether ui.panel.base / ui.card.activity / ui.button.primary need additional Shell consumption
```

Why this is next:

- the Shell seam is already proven;
- another launcher-only decorative consumer would add less architectural value;
- V5 explicitly requires shared Shell/Activity reuse;
- the Activity contract must be renderer-neutral enough for Python and future Web runtimes.

Do not freeze a broad API prematurely. Start with one semantic request/resolution path and preserve the existing platform boundaries.

---

# 8. Testing rule for the next V5 tranche

For owner-directed local-agent runtime/visual acceptance, use the Greia Activity Simulator.

Relevant current protocol:

```text
docs/testing/2026-08-20_V5_VISUAL_INTEGRATION_SIMULATOR_LOCAL_AGENT.md
```

That document describes the completed first-consumer tranche. If the next Activity-facing tranche requires a materially different simulator procedure, update or add the appropriate dated simulator test document before claiming PASS.

Do not use GitHub Actions unless the owner explicitly authorizes that hosted execution.

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
- broad exception swallowing to hide optional-visual failures.

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

First-consumer execution result:

```text
LOCAL_AGENT_RESULT.md
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
