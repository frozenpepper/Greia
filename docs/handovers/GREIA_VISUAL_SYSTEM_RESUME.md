# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-22  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Visual-authoring architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Generic art taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**Canonical cast system:** `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`  
**Character grammar:** `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md`  
**Character motion:** `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`  
**Maintainer plan:** `docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md`

---

# 1. Architecture

There are two separate visual-authoring tracks.

## Track A — maintainer-side source/toolbox/canonical-cast production

The owner's local maintainer agent may create/improve Greia source art. Its drawing ability is not a product dependency and is not evidence about arbitrary future Activity-authoring agents.

Generic object/environment discovery uses six semantic authoring-library indexes. Shared UI and Canonical Characters remain stronger-consistency families.

## Track B — arbitrary Activity-authoring agents

The model/tool-agnostic workflow remains:

```text
inventory Activity needs
→ query/search generic semantic library
→ use canonical Greia characters/states where appropriate
→ prefer reviewed/preferred resources where they fit
→ inspect candidate/source references as needed
→ REUSE / COMPOSE-ADAPT / CREATE ORIGINAL
→ create Activity-local final art
→ flatten/build efficient runtime rendition
→ integrate through existing Greia package/scene boundaries
→ inspect actual pixels
```

---

# 2. Generic toolbox state

Current indexed state:

```text
57 preferred finished assets
37 candidate-reference finished assets
7 preferred authoring ingredients
101 indexed reusable visual resources
```

Discovery helper:

`tools/visual_authoring_library.py`

No generic Batch B is authorized merely to increase counts.

Permanent rule:

> **Generic assets encode reusable form; Activity-specific meaning and contents remain separable whenever practical.**

---

# 3. Canonical cast source-art state — ACCEPTED

The pure-art cast loop is now complete at owner pixel-review scope.

## Four-character state-system foundation

Candidate commit:

`59336d1c34e119e04c40b32f2c1901e1dbfb1b60`

Primary review:

`docs/reviews/visual/2026-08-22_canonical-character-cast-reauthoring/PRIMARY_REVIEW.md`

Established the five source states:

```text
neutral
blink
happy
surprised
sleepy
```

and shared design/motion vocabulary:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

## Six-character expansion

Candidate commit:

`cfbb9512723353dd34f6081c174410401e290ca8`

Primary review:

`docs/reviews/visual/2026-08-22_canonical-cast-expansion/PRIMARY_REVIEW.md`

Leo and Dani were accepted; Flash's structure/state/motion design worked but required one identity correction.

## Flash white-rabbit revision

Candidate commit:

`fba60ff31c8bb7e825163bb349e349bd1b72d0f3`

Owner primary review:

`docs/reviews/visual/2026-08-22_flash-white-rabbit-identity-revision/PRIMARY_REVIEW.md`

Actual owner-transfer pixels were inspected.

**Result: ACCEPTED.**

The accepted current cast is:

```text
Lilli — unicorn                        → creativity / stories / art / imagination
Leo   — owl with integrated glasses   → learning / reading / language / knowledge
Flash — white rabbit + lightning top  → games / speed / action / playful challenge
Dani  — friendly robot                → math / logic / patterns / sequencing
Tito  — fox                           → exploration / nature / discovery / investigation
Momo  — monster                       → emotion / music / silly play / celebration
```

Historical Nino remains provenance. Current owl identity is Leo.

No further pure-art cast pass is authorized before runtime integration unless a concrete source defect is exposed.

---

# 4. Character architecture rule

Use:

> **complete authored state art + authoring-time semantic source components + build-time PNG renditions + simple whole-character runtime transforms**

Avoid:

- skeletal/bone rigs;
- runtime limb/body-part composition;
- runtime clothing systems;
- frame-by-frame sprite explosions;
- continuously varying raster sizes for motion;
- a second runtime asset/cache system.

For the first runtime pass, fixed-size state swaps + bounded x/y translation are sufficient for the semantic motion vocabulary. Do not reproduce storyboard rotation/squash literally if that causes per-frame allocation/cache churn.

---

# 5. Exact current maintainer task

Execute:

```text
docs/testing/2026-08-22_CANONICAL_CAST_V01_PROMOTION_RUNTIME_SIMULATOR.md
```

This gate owns:

1. stable six-character source promotion under `assets/visual/characters/canonical/v0.1/`;
2. explicit current Leo identity with historical Nino provenance preserved;
3. all 30 build-time runtime renditions (6 × 5 states);
4. minimal typed/validated semantic expression + motion support in the existing scene-actor path;
5. bounded non-default-state fallback to neutral/default;
6. a developer-only test Activity fixture loaded through the real Simulator source-loader path;
7. runtime/visual/fallback/responsive acceptance through the Greia Activity Simulator;
8. owner-transfer ZIP containing curated runtime evidence.

Required owner ZIP:

```text
GREIA_VISUAL_REVIEW_CANONICAL_CAST_V01_RUNTIME_SIMULATOR_2026-08-22.zip
```

Do not count `make visual-assets`, `make visual-assets-check`, pytest, or direct Activity execution as visual acceptance. They are prerequisites/source evidence only.

---

# 6. Platform relationship

The soft lead-mascot model remains:

```text
create  → Lilli often leads
play    → Flash often leads
learn   → Leo often leads
explore → Tito often leads
```

Dani and Momo are cross-cutting. `my_greia` remains child/profile-centered.

Do not create six top-level Home Collections.

Optional Activity metadata such as `lead_character` / `supporting_characters` remains a **later** gate after runtime character acceptance.

---

# 7. Stable runtime foundation to preserve

```text
explicit semantic asset catalogues
build-time SVG/source → runtime PNG renditions
bounded Pygame visual cache
SceneDefinition / SceneNode / SceneCamera
PygameSceneRenderer
SceneActorDefinition / actor_scene_sample
Greia Activity Simulator real Shell/runtime composition
```

Runtime rules remain:

- no arbitrary runtime source scanning;
- no normal runtime SVG rasterization;
- no per-frame disk decode/scale;
- bounded caches;
- Activity-local assets remain inside Activity packages;
- generic authoring indexes/tooling remain authoring-time facilities, not a second runtime catalogue.

---

# 8. What follows successful runtime owner review

After the canonical cast v0.1 runtime/simulator evidence is owner-reviewed and accepted:

1. consider optional Activity lead/supporting-character presentation metadata;
2. exercise the model-agnostic visual-authoring skill/toolbox in a real Activity-authoring workflow;
3. let actual Activity demand drive any further generic art work;
4. do not resume art-count production by inertia.

---

# 9. Drift to avoid

- no theme-by-theme pack roadmap;
- no generic Batch B merely to increase counts;
- no hero-tree optimization;
- no Clinic finalization;
- no further Flash/cast redesign loop absent a concrete blocker;
- no detailed skeletal character rig;
- no runtime wardrobe system;
- no six-character → six-Home-category mapping;
- no treating maintainer-agent drawing ability as arbitrary-agent evidence;
- no second runtime asset system.

---

# 10. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual/cast work closes, reorders, or bypasses R7.

No physical Acer/Pi acceptance should be claimed without actual hardware evidence.

---

### Canonical Cast v0.1 Final Capture Integrity & Acceptance Recheck (2026-08-22)

- **3-Phase Scenario Isolation:** Executed strict 3-phase execution model separating clean normal baseline evidence (Phase A) from single-fault state fallback (Phase B, `flash_happy.png`) and required-default safe fallback error screen (Phase C, `dani_neutral.png`).
- **Self-Proving On-Screen Diagnostic Readouts:** Added live 2-line diagnostic overlay onto fixture canvas displaying requested variant, rendered variant, fallback status (`YES (default)` vs `NO`), reference canvas, outer viewport, and active interface-size setting (`NORMAL`, `LARGE`, `COMPACT`).
- **Renderer Fallback Node Tracking:** Enhanced `SceneRenderStats` and `PygameSceneRenderer` to increment `fallback_nodes` upon fallback resolution.
- **Verified Bundle Deliverables:** Curated `docs/reviews/visual/2026-08-22_canonical-cast-v01-final-capture/` and generated root `GREIA_VISUAL_REVIEW_CANONICAL_CAST_V01_FINAL_CAPTURE_2026-08-22.zip` containing strictly 10 PNGs + `OWNER_FINAL_RECHECK.md` + `runtime-audit.json` + `simulator-trace.json`.
