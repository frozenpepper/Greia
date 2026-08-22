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

Greia has two distinct visual-authoring tracks.

## Track A — maintainer-side source/toolbox/canonical-cast production

The owner's local maintainer agent may create/improve Greia source art. Its drawing ability is not a product dependency and is not evidence about arbitrary future Activity-authoring agents.

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

Theme/source bundles are provenance pools. Generic semantic collections are the primary discovery interface.

---

# 2. Generic toolbox state — DISCOVERY TOOLING AVAILABLE

Current indexed state:

```text
57 preferred finished assets
37 candidate-reference finished assets
7 preferred authoring ingredients
101 indexed reusable visual resources
```

Discovery helper:

`tools/visual_authoring_library.py`

Focused tests:

`tests/test_visual_authoring_library.py`

Permanent rules:

- `preferred` is the first-choice direct-reuse state;
- `candidate_reference` is primarily adaptation/reference material;
- generic assets encode reusable form while Activity-specific meaning stays separable where practical;
- absence of a perfect asset does not automatically authorize new generic production;
- **Generic Batch B remains unauthorized** until real Activity demand demonstrates a concrete generic gap.

---

# 3. Canonical cast v0.1 — ACCEPTED AT SIMULATOR RUNTIME SCOPE

Current cast:

```text
Lilli — unicorn                        → creativity / stories / art / imagination
Leo   — owl with integrated glasses   → learning / reading / language / knowledge
Flash — white rabbit + lightning top  → games / speed / action / playful challenge
Dani  — friendly robot                → math / logic / patterns / sequencing
Tito  — fox                            → exploration / nature / discovery / investigation
Momo  — monster                        → emotion / music / silly play / celebration
```

Historical Nino remains provenance. Current owl identity is Leo.

Stable source:

`assets/visual/characters/canonical/v0.1/`

Accepted states:

```text
neutral
blink
happy
surprised
sleepy
```

Accepted semantic motions:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Runtime architecture:

> **complete authored state art + authoring-time semantic source components + build-time PNG renditions + simple whole-character fixed-size runtime transforms**

Do not replace this with skeletal rigs, runtime body-part composition, continuously varying raster sizes, or a second runtime asset/cache architecture.

Final owner acceptance:

`docs/reviews/visual/2026-08-22_canonical-cast-v01-final-capture/OWNER_REVIEW.md`

Evidence class: **SIMULATOR VISUAL REVIEW**.

No further cast proof fixture or pure-art cast pass is currently required.

---

# 4. Stable runtime foundation to preserve

```text
explicit semantic asset catalogues
build-time SVG/source → runtime PNG renditions
bounded Pygame visual cache
bounded failed-rendition memory
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
- Activity-local assets stay inside Activity packages;
- generic authoring indexes/tooling are authoring-time facilities, not a second runtime catalogue.

---

# 5. Platform relationship

Soft lead-mascot affinities remain:

```text
create  → Lilli often leads
play    → Flash often leads
learn   → Leo often leads
explore → Tito often leads
```

Dani and Momo remain cross-cutting. `my_greia` remains child/profile-centered.

Do not create six top-level Home Collections.

Do **not** implement `lead_character` / `supporting_characters` package metadata merely because character presentation is available. Let real Activity-authoring demand establish whether that schema is useful.

---

# 6. Shape Garden authoring workflow — OWNER ACCEPTED

Executed gate:

`docs/testing/2026-08-22_SHAPE_GARDEN_VISUAL_AUTHORING_WORKFLOW_EXERCISE.md`

Implementation/evidence commit:

`072004174237ca15727283dc19850e8a1765c6e3`

Owner review:

`docs/reviews/visual/2026-08-22_shape-garden-visual-authoring-workflow/OWNER_REVIEW.md`

Disposition: **ACCEPTED — SIMULATOR VISUAL REVIEW**.

Shape Garden primarily proved disciplined direct `REUSE`, light Activity-local adaptation, and justified Dani companion use. Library-gap result: **NO_GAP**.

---

# 7. Costruiamo Ponti authoring stress exercise — OWNER ACCEPTED

Executed gate:

`docs/testing/2026-08-22_COSTRUIAMO_PONTI_VISUAL_AUTHORING_STRESS_EXERCISE.md`

Implementation/evidence commit:

`cf349b7`

Owner review:

`docs/reviews/visual/2026-08-22_costruiamo-ponti-visual-authoring-stress/OWNER_REVIEW.md`

Disposition: **ACCEPTED — SIMULATOR VISUAL REVIEW**.

This second real first-party exercise proved the harder authoring paths:

- `REUSE` of generic scenery/character resources;
- `COMPOSE_ADAPT` across materially distinct River / Canyon / Space worlds;
- `CREATE_ORIGINAL` for gameplay-critical bridge-material and prop art;
- preservation of puzzle mechanics, storage, events, audio, and platform navigation.

Library-gap result: **NO_GAP**.

Therefore:

- Generic Batch B remains unauthorized;
- no new character package metadata is justified;
- no further Costruiamo Ponti acceptance rerun is required.

---

# 8. Completed visual-authoring gate — PAINTING PRODUCTIZATION

Completed runbook:

`docs/testing/2026-08-22_PAINTING_VISUAL_PRODUCTIZATION_EXERCISE.md`

Target:

`activities/painting/` (`org.greia.painting`)

Outcome: **COMPLETE & VERIFIED**
- Proved authoring workflow on a UI-heavy Phase-0 core creation activity:
  - `COMPOSE_ADAPT`: Storybook warm cream studio tabletop mat background framing the drawing canvas without eating screen space.
  - `CREATE_ORIGINAL`: Complete tactile activity-local UI asset family in `activities/painting/assets/` (`tool_gallery.png`, `tool_undo.png`, `tool_new.png`, `tool_eraser.png`, `brush_small.png`, `brush_medium.png`, `brush_large.png`, `canvas_card_frame.png`, `color_well_dish.png`) with clean SVG masters in `source/` and build-time PNGs in `runtime/`.
  - `KEEP_EXISTING_INTENTIONAL`: 100% preservation of PaintingRepository, StrokeHistory, autosave idle loop, undo limits, and platform Home button integration.
  - Mascot Decision: Intentionally omitted mascot to ensure the child's drawing canvas remains generous, uncluttered, and unencumbered.
- Captured complete 12-PNG curated evidence suite in `docs/reviews/visual/2026-08-22_painting-visual-productization/` with `AUTHORING_AUDIT.md`, `authoring-audit.json`, `simulator-trace.json`, and `OWNER_RECHECK.md`.
- Packaged owner transfer ZIP: `GREIA_VISUAL_REVIEW_PAINTING_PRODUCTIZATION_2026-08-22.zip`.
- Generic library gap outcome: **`NO_GAP`**. Generic Batch B remains unauthorized.


---

# 9. Completed launcher gate — ACTIVITY CARD TITLES & UNIQUE ICONS

Completed runbook:

`docs/testing/2026-08-22_ACTIVITY_CARD_TITLES_AND_UNIQUE_ICONS.md`

Outcome: **COMPLETE & VERIFIED**
- Two-line centered title wrapping with safe Unicode grapheme cluster fallback and 48-grapheme cluster defensive cap.
- Full uncapped localized title disclosure on pointer hover and keyboard selection via floating callout pill avoiding protected controls.
- Aspect-ratio preserving contain-fit icon scaling with 10–12% safe padding around artwork.
- 100% unique package-owned icon migration (`package:assets/icon.png`) with clean SVG masters and baked PNGs across all 19 first-party Activities.
- 12 curated Simulator captures in `docs/reviews/visual/2026-08-22_activity-card-titles-and-unique-icons/`, `runtime-audit.json`, `OWNER_RECHECK.md`, and root review archive `GREIA_VISUAL_REVIEW_ACTIVITY_CARD_TITLES_UNIQUE_ICONS_2026-08-22.zip`.

---

# 10. Completed launcher gate — LAUNCHER SHELL PRODUCTIZATION & CATEGORY NAVIGATION

Completed runbook:

`docs/testing/2026-08-22_LAUNCHER_SHELL_PRODUCTIZATION_AND_CATEGORY_NAVIGATION.md`

Outcome: **COMPLETE & VERIFIED**
- Full Category Switcher Strip in the in-category header with active category pill (`Crea (6)`), interactive chips for other categories, and tactile Back/Home button returning to Collection Home.
- Responsive pagination controls when activities exceed 3x2 grid capacity: bottom pagination capsule pill (`● ○`, `1 / 2`), floating tactile side arrows (`[ < ]` and `[ > ]`), and `PAGE_UP` / `PAGE_DOWN` keyboard support.
- Rich selection, hover, and launching visual polish: card hover elevation (-3px lift, soft shadow, accent outline), distinct keyboard focus ring with golden star badge (`⭐`), and animated launching badge (`Avvio...` coral pill with white border).
- 12 curated Simulator captures in `docs/reviews/visual/2026-08-22_launcher-shell-productization/`, `runtime-audit.json`, `simulator-trace.json`, `OWNER_RECHECK.md`, and root transfer archive `GREIA_VISUAL_REVIEW_LAUNCHER_SHELL_PRODUCTIZATION_2026-08-22.zip`.

---

# 11. Drift to avoid

- no theme-by-theme pack roadmap;
- no Generic Batch B by inertia;
- no redraw of every candidate reference;
- no hero-tree/specimen rabbit hole;
- no further Lilli/Leo/Flash/Dani/Tito/Momo redesign absent a concrete defect;
- no detailed skeletal character rig;
- no runtime wardrobe system;
- no six-character → six-Home-category mapping;
- no treating maintainer-agent drawing ability as arbitrary-agent evidence;
- no second runtime asset system;
- no proof-only Activity when a real first-party Activity can exercise the system;
- no package character metadata before a real use case demonstrates value;
- no relabeling untouched shared assets as `COMPOSE_ADAPT`;
- no promotion of Activity-specific art into the generic library without demonstrated cross-Activity value;
- no turning Painting into a desktop-class graphics editor.

---

# 10. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual/content work closes, reorders, or bypasses R7.

No physical Acer/Pi acceptance should be claimed without actual hardware evidence.
