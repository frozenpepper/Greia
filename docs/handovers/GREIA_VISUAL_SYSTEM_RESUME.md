# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-20  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Active plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Project-wide handover:** `HANDOVER.md`

---

# 1. Why this file exists

This file is the **fastest safe way to resume the Greia art/graphics work in a new session**.

It is deliberately shorter than the main visual-system guide and the active plan. It records:

- the accepted direction;
- what already exists;
- what is currently active;
- what is explicitly rejected/stale;
- the exact next work;
- the current testing/evidence rule.

At the beginning of a new visual session:

```bash
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
```

Then read, in order:

```text
1. AGENTS.md
2. docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
3. docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
4. this file
5. HANDOVER.md
6. skills/greia-visual-authoring/SKILL.md
7. exact source files for the current V5 task
```

Do not resume from chat memory alone.

---

# 2. Accepted visual direction

The accepted production pipeline is:

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → explicit semantic runtime consumption → Shell/Activity reuse**

Core rules:

- asset-first, never crude scene-first production;
- polished storybook/toy-diorama feel;
- low-resolution readability;
- static assets remain complete without animation;
- reuse generic assets instead of repainting duplicates;
- runtime does not scan visual source directories;
- SVG masters are pre-rendered to PNG on a build host;
- target runtime caches remain bounded;
- no per-frame filesystem/decode work;
- visual work must not deepen provisional X11 coupling or bypass platform UI/system-chrome architecture.

---

# 3. Character direction

Core cast:

```text
Lilli — unicorn Puff
Nino  — owl Bean
Tito  — fox Puff
Momo  — friendly monster Puff
```

Shared states:

```text
neutral
blink
happy
surprised
sleepy
```

Shared base motions:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Rules:

- character identity must remain stable across states;
- `blink` must visibly close eyes;
- no complex anatomical rig as the default;
- do not let character minutiae derail the current V5 integration work.

---

# 4. Source library already built

Broad source coverage exists. Do not create another environment pack by default.

Current packs:

```text
assets/visual/environments/forest_meadow/v0.2/
assets/visual/ui/v0.1/
assets/visual/environments/workshop/v0.1/
assets/visual/environments/clinic/v0.1/
assets/visual/environments/reading_classroom/v0.1/
assets/visual/environments/fantasy_village_night/v0.1/
assets/visual/environments/water_pond/v0.1/
```

Design inventories:

```text
assets/visual/library_v0.1.toml
assets/visual/packs_v0.1.toml
```

All current packs remain candidate unless a narrower file explicitly records a stronger scope.

Broad art evidence remains primarily:

```text
SOURCE
DESKTOP VISUAL REVIEW
```

Do not call candidate pack presence release approval or runtime acceptance.

---

# 5. Active phase: V5 shared consumption/integration

V5 is the active visual phase.

The objective is not to produce more artwork. The objective is to prove one clean path from reviewed source art to a real Greia consumer.

Current source architecture already includes:

```text
src/greia_platform/assets.py
src/greia_platform/pygame_visual_assets.py
src/greia_launcher/visual_assets.py
assets/catalog/core_icons_v1.toml
assets/catalog/shared_visuals_v1_source.toml
tools/build_visual_renditions.py
tools/validate_visual_renditions.py
Makefile: visual-assets / visual-assets-check
```

Implemented design:

```text
reviewed SVG master
→ explicit source manifest
→ build-time PNG rendition
→ explicit generated runtime catalogue
→ AssetCatalogue
→ PygameVisualSurfaceCache
→ Shell consumer
```

Important invariants:

- one semantic namespace for icons + visuals;
- explicit variants with `default`;
- no arbitrary directory discovery;
- file/path containment and duplicate-ID rejection;
- build-time SVG rasterization only;
- generated output validation;
- bounded runtime surface cache;
- optional generated visuals must fail back to the established static launcher path.

---

# 6. First V5 runtime consumer

The first real Shell integration target remains:

```text
ui.shadow.soft
```

under existing launcher Activity tiles.

Why this is first:

- low architectural risk;
- decorative only;
- proves the full semantic-rendition-cache-consumer pipeline;
- does not require a launcher redesign;
- existing primitive/static shadow can remain fallback.

Do not jump directly to replacing the full card/button/panel system before this path is accepted.

The consumer must not change:

```text
tile hit geometry
responsive grid geometry
label-band geometry
selection behavior
launch lifecycle
protected system chrome
```

---

# 7. Current local-agent execution rule

The current owner-directed V5 local-agent runbook is:

```text
docs/testing/2026-08-20_V5_VISUAL_INTEGRATION_SIMULATOR_LOCAL_AGENT.md
```

For this current tranche:

> **all runtime/visual/fallback/responsive test acceptance is handled through the Greia Activity Simulator.**

Build generation is allowed outside the simulator:

```bash
make visual-assets
```

That command creates prerequisites; it is not itself PASS evidence.

Do not use GitHub Actions.

Do not substitute VM/physical tests for the current local-agent simulator acceptance tranche unless the owner changes the instruction.

Do not invent Cloudflare/tunnels/hosted web dependencies. The simulator bridge is local loopback only.

---

# 8. Exact next work

Resume in this order:

```text
1. sync current main and record SHA
2. read the current V5 section in the active plan
3. ensure build host has librsvg / rsvg-convert
4. run make visual-assets
5. inspect generated PNGs + assets/catalog/shared_visuals_v1.toml
6. wire the existing launcher visual bridge into the real launcher initialization
7. create/use one launcher-owned PygameVisualSurfaceCache
8. render ui.shadow.soft beneath existing Activity tiles
9. preserve current primitive/static shadow as fallback
10. start the Activity Simulator
11. test normal consumption through simulator
12. test missing generated catalogue through simulator
13. test invalid generated catalogue through simulator
14. test missing/corrupt optional shadow PNG through simulator
15. test hover, selection and launch behavior through simulator
16. test the required viewport/interface-size matrix through simulator
17. inspect gross frame-count/stall behavior through simulator
18. fix root causes only in shared owners
19. rerun affected simulator cases
20. update active plan, this resume file, HANDOVER and visual skill if contracts changed
21. commit/push coherent work to main
```

Required viewport/interface-size matrix from the current local-agent protocol:

```text
1024×600  + normal
1024×600  + large
1280×800  + normal
1366×768  + compact
1920×1080 + normal
1111×700  + normal
```

---

# 9. Known evidence boundary

Current V5 state:

- `make visual-assets` generated `assets/visual/runtime/v1/ui/soft_shadow.png` and `assets/catalog/shared_visuals_v1.toml`;
- `ui.shadow.soft` is wired and accepted as the first shared visual in the Launcher under Activity tiles;
- Tested and accepted across 6 responsive viewports, selection/hover/launch interaction, fail-soft fallbacks (missing catalogue, invalid catalogue, corrupt PNG), and steady 29.4 FPS frame rate via Greia Activity Simulator;
- Evidence recorded in `./tmp/v5-simulator-evidence/` (**SIMULATOR VISUAL REVIEW**);
- No physical hardware or R7 architecture closure claimed.

---

# 10. Rejected/drift directions

Do not resume any of these as if they were current work:

- complex quadruped/character rig architecture;
- generated sprite sheets assumed production-ready;
- redrawing accepted characters into worse variants;
- fake expression overlays;
- non-blinking blink animation;
- crude full-screen UI/background mockups;
- decorative HTML presentations used instead of actual asset production;
- one-shot generated concept scenes used as source architecture;
- more environment packs without a concrete reuse gap;
- runtime SVG rendering on the low-end target;
- arbitrary asset-directory discovery;
- a second visual catalogue/cache system;
- per-frame PNG decode/scale;
- unbounded caches;
- simulator-specific production launcher code;
- per-resolution launcher forks;
- deepening provisional X11 coupling for visual convenience.

---

# 11. Documentation map for visual work

Stable entry point:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
```

Visual-language details:

```text
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
```

Artwork inventory:

```text
docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md
```

Characters:

```text
docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
```

Practical production rules:

```text
skills/greia-visual-authoring/SKILL.md
```

Current sequencing/history:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
```

Current runtime integration test protocol:

```text
docs/testing/2026-08-20_V5_VISUAL_INTEGRATION_SIMULATOR_LOCAL_AGENT.md
```

Source-tree summary:

```text
assets/visual/README.md
```

---

# 12. End-of-session update rule

At the end of every substantive visual-system session, update this file if any of these changed:

- current active visual phase;
- current exact next action;
- first consumer / runtime integration state;
- evidence boundary;
- blocker;
- testing rule;
- major accepted/rejected direction.

Do not use this file as an append-only diary. Keep it short enough that a new agent can resume quickly.

Chronology belongs in the active plan's append-only progress ledger.

Architecture belongs in `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`.

Project-wide current evidence belongs in `HANDOVER.md`.
