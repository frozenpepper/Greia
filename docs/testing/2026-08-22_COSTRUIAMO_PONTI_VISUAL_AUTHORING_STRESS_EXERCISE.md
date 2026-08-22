# Costruiamo Ponti — Visual-Authoring Stress Exercise

**Status:** EXECUTE  
**Date:** 2026-08-22  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Target Activity:** `activities/costruiamo_ponti/` (`org.greia.costruiamo-ponti`)  
**Preceding accepted gate:** `docs/reviews/visual/2026-08-22_shape-garden-visual-authoring-workflow/OWNER_REVIEW.md`  
**Evidence class if accepted:** **SIMULATOR VISUAL REVIEW**

## 1. Purpose

Run the second real first-party Greia visual-authoring exercise on **Costruiamo Ponti**.

Shape Garden successfully proved discovery-first reuse, canonical-character integration, light Activity-local adaptation and the existing runtime visual seams. It did **not** strongly stress the harder authoring decisions where a real Activity needs unique gameplay-critical art.

This gate is deliberately selected to exercise:

```text
REUSE
COMPOSE_ADAPT
CREATE_ORIGINAL
KEEP_EXISTING_INTENTIONAL
```

on a real Activity that already has:

- three visually distinct worlds: `river`, `canyon`, `space`;
- four gameplay-semantic bridge materials: `wood`, `stone`, `shroom`, `rainbow`;
- a bridge crossing/traveler sequence;
- success/failure feedback;
- a bottom material palette;
- localization, storage, events, audio and hybrid input contracts that must not regress.

This is **not** authorization for Generic Batch B, a new renderer, a new asset loader, a new character system, or a redesign of gameplay.

---

## 2. Mandatory read order

Before changing source, read the repository authorities required by `AGENTS.md`, including at minimum:

```text
AGENTS.md
docs/DOCUMENTATION.md
docs/architecture/GREIA_ARCHITECTURE.md
docs/adr/0012-platform-architecture-constitution.md
docs/adr/0018-lightweight-ui-foundation.md
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md
docs/design/GREIA_CANONICAL_CAST_SYSTEM.md
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
skills/greia-activity-authoring/SKILL.md
skills/greia-visual-authoring/SKILL.md
activities/costruiamo_ponti/activity.toml
activities/costruiamo_ponti/main.py
relevant Costruiamo Ponti tests and localization files
```

Do not rely on this runbook as a replacement for those authorities.

---

## 3. Preserve the Activity contract

The visual pass must not change the meaning of the Activity.

Preserve at minimum:

- Activity ID: `org.greia.costruiamo-ponti`;
- Collections: `create`, `play`;
- hybrid input profile;
- pointer/keyboard/touch behavior already supported;
- platform-owned Home behavior and protected input region;
- three existing levels and their progression order;
- the existing required bridge-material sequences unless a pre-existing bug is independently proven;
- material selection semantics;
- bridge-slot placement semantics;
- crossing/start/go behavior;
- success and failure logic;
- storage key/schema compatibility;
- event emission semantics;
- English/Italian localization behavior;
- existing audio behavior unless a concrete bug is found;
- no Linux/file/browser surface in the child path.

The visual system must support the gameplay; it must not become a different game.

---

## 4. Why this Activity was selected

Current source visibly contains programmer-drawn or one-off procedural visual treatment for major gameplay objects and three level environments.

That makes Costruiamo Ponti a useful stress test for whether the authoring architecture can handle:

- reusable shared scenery where appropriate;
- Activity-specific environment composition;
- unique bridge pieces whose visual identity is part of the game mechanic;
- one recurring traveler/companion character;
- feedback and celebration;
- multiple worlds without creating a generic theme-pack explosion.

If the Activity somehow turns out not to require any meaningful `COMPOSE_ADAPT` or `CREATE_ORIGINAL` work after honest inspection, stop and record that it is a poor stress-test candidate rather than manufacturing pointless assets merely to satisfy labels.

---

## 5. Baseline evidence before authoring

Start from current canonical `main` and a clean working tree.

Before implementation:

```bash
git status --short
git branch --show-current
git pull --ff-only origin main
python3 tools/visual_authoring_library.py validate --json
PYTHONPATH=src python3 tools/validate_activity.py activities/costruiamo_ponti
make visual-assets-check
```

Use a fresh project-local simulator/evidence state.

Capture **real Simulator** baseline pixels through the normal Activity loading path, not by executing `main.py` directly.

Required baseline captures:

```text
baseline-river-1024x600-normal.png
baseline-canyon-1024x600-normal.png
baseline-space-1024x600-normal.png
```

Record a concise visual-needs inventory before editing source.

At minimum inspect:

```text
river world/background
canyon world/background
space world/background
left/right bridge banks / gap / traversal zone
bridge slots
wood bridge material
stone bridge material
shroom/bounce bridge material
rainbow bridge material
material-palette presentation
traveler/character
success celebration
failure feedback
foreground/background depth
contact/grounding shadows
optional atmosphere/FX
launcher icon only if a real deficiency is exposed
```

Do not write the decisions after the implementation and pretend they were discovery-first.

---

## 6. Mandatory discovery-first pass

Use:

`tools/visual_authoring_library.py`

before manually browsing themed source folders.

Run and record useful queries. The exact set may evolve, but the pass must cover the semantic needs of all three worlds and gameplay objects.

Useful starting queries include:

```bash
python3 tools/visual_authoring_library.py search river --json
python3 tools/visual_authoring_library.py search water --json
python3 tools/visual_authoring_library.py search rock --json
python3 tools/visual_authoring_library.py search canyon --json
python3 tools/visual_authoring_library.py search desert --json
python3 tools/visual_authoring_library.py search hill --json
python3 tools/visual_authoring_library.py search cloud --json
python3 tools/visual_authoring_library.py search star --json
python3 tools/visual_authoring_library.py search space --json
python3 tools/visual_authoring_library.py search light --json
python3 tools/visual_authoring_library.py search shadow --json
python3 tools/visual_authoring_library.py search wood --json
python3 tools/visual_authoring_library.py search stone --json
python3 tools/visual_authoring_library.py search mushroom --json
python3 tools/visual_authoring_library.py search rainbow --json
python3 tools/visual_authoring_library.py search sparkle --json
```

Also use `show` on every serious candidate selected for reuse/adaptation.

For every important visual role, explicitly classify the decision as one of:

```text
REUSE
COMPOSE_ADAPT
CREATE_ORIGINAL
KEEP_EXISTING_INTENTIONAL
```

Record:

- query;
- candidate IDs inspected;
- selected resource if any;
- library status;
- exact source path;
- decision;
- rationale;
- final runtime realization.

Do not browse `Clinic`, `Fantasy`, `Water`, etc. as whole theme packs merely because their names seem relevant. Follow generic semantic discovery first, then inspect provenance sources only when a selected index entry or real gap justifies it.

---

## 7. Hard authoring objective: exercise the difficult paths honestly

This gate is only valuable if it goes beyond Shape Garden's mostly direct reuse.

### 7.1 `COMPOSE_ADAPT`

At least one major visual role should genuinely require composition/adaptation from existing Greia source language.

Likely candidates include, but are not forced to be:

- river-bank / cliff treatment;
- canyon environment;
- space platform/gap environment;
- bridge-bank framing;
- level-specific atmospheric treatment.

A valid `COMPOSE_ADAPT` result must be more than placing an untouched shared PNG at a different coordinate.

Examples of legitimate work:

- combine/rearrange generic rocks, ground edges, hills, clouds, light or FX into one Activity-specific scene treatment;
- adapt palette/material relationships while preserving source provenance;
- build an Activity-local flattened background/foreground from generic source ingredients where runtime economy benefits;
- derive an Activity-specific bank/platform silhouette using Greia source/material language rather than copying a generic object unchanged.

### 7.2 `CREATE_ORIGINAL`

At least one gameplay-critical visual family is expected to be Activity-specific because its meaning is unique to Costruiamo Ponti.

The strongest candidates are the four bridge materials:

```text
wood
stone
shroom
rainbow
```

They are not decorative props: children must recognize them consistently in the palette, placed bridge slots and crossing sequence.

Prefer a coherent Activity-local authored family rather than four unrelated programmer-drawn mini-icons.

A good result should preserve instant semantic recognition while improving:

- silhouette;
- material identity;
- tactile depth;
- consistent lighting;
- clean alpha edges;
- legibility at palette and bridge sizes;
- relationship to Greia's storybook/toy-diorama visual language.

Authoring source may be SVG or another maintainable source form if consistent with project conventions, but normal runtime must consume efficient package-local PNG/WebP or existing Greia semantic runtime assets. **No runtime SVG rasterization.**

Do not create a second global build/catalogue system just for this Activity.

If an existing first-party Activity-local asset convention exists, follow it.

---

## 8. Traveler / character decision

The current Activity has a bunny traveler. Make an explicit authoring decision; do not silently keep or replace it.

Evaluate at least these options:

### Option A — canonical Flash

Flash is naturally aligned with action/play/challenge and already has accepted states/motions.

If Flash genuinely improves the Activity:

- use `character.flash` through the existing semantic actor/runtime path;
- preserve the canonical design unchanged;
- use authored states/motions semantically;
- do not create package-level `lead_character` metadata;
- keep the character visually subordinate to bridge construction.

### Option B — Activity-local traveler

If the bridge game benefits from a distinct traveler identity rather than Flash:

- keep it Activity-local;
- treat it as `CREATE_ORIGINAL` and re-author it to Greia quality rather than retaining crude programmer-drawn geometry;
- do not promote it to the canonical cast or generic library;
- keep runtime art bounded and package-local.

Record the decision and rationale in the audit.

Do **not** add a seventh canonical mascot in this gate.

---

## 9. Three worlds must remain meaningfully distinct

The River, Canyon and Space levels must not become the same backdrop with only a background color change.

Each should have a distinct, coherent visual identity while remaining unmistakably one Activity.

### River

Expected feeling:

- friendly natural crossing;
- readable water/gap;
- green/earthy banks;
- gentle outdoor depth.

### Canyon

Expected feeling:

- warmer/drier geology;
- stronger cliff/rock massing;
- distinct atmospheric palette;
- still friendly and child-readable, not dangerous/grim.

### Space

Expected feeling:

- unmistakably non-terrestrial;
- dark/deep sky or void;
- simple readable platform/bank geometry;
- stars/glow/space atmosphere where useful;
- no dense sci-fi UI clutter.

Use shared generic resources where they fit, but do not force the same meadow assets into all three worlds merely to maximize reuse.

---

## 10. Material-palette and gameplay readability

The material palette is an interaction surface, not decoration.

For all four materials verify:

- same visual identity in palette and placed bridge;
- selected material is clearly indicated by existing Greia UI language or a restrained Activity-local treatment;
- no text dependence is introduced for a concept already communicated visually;
- hit targets remain child-sized;
- icons remain legible at 1024×600;
- visual flourish does not obscure material identity.

Do not hide puzzle information inside subtle shading or color alone.

---

## 11. Motion and feedback

Use motion only where it supports the Activity.

Good candidates:

- gentle traveler idle;
- clear crossing movement;
- shroom bounce response;
- brief successful-placement delight;
- success celebration;
- bounded failure reaction.

Preserve a complete static presentation when animation is disabled or not advancing.

Do not add continuous decorative motion that materially increases CPU cost or distracts from bridge decisions.

No continuously varying raster dimensions.

---

## 12. Runtime economy and architecture

Preserve the accepted runtime architecture.

Required properties:

- no runtime SVG parsing/rasterization;
- no arbitrary source-directory scanning;
- no per-frame disk I/O;
- no unbounded cache;
- no per-frame smoothscale churn for fixed visual objects;
- shared Greia visuals resolve through existing semantic asset APIs/cache;
- Activity-local runtime art stays inside the Activity package;
- `PygameSceneRenderer` / `SceneDefinition` / `SceneActorDefinition` may be used where they fit;
- do not build a parallel scene engine merely for this Activity;
- no X11-specific production dependency added by this visual pass.

Keep the reference-canvas/pointer/safe-area contract intact.

---

## 13. Library-gap policy

After the Activity is visually complete, classify any remaining reusable-library deficiency as exactly one of:

```text
NO_GAP
TRUE_MISSING
QUALITY_GAP
VARIETY_GAP
```

Important:

- a unique bridge-game object is normally Activity-local, not a generic-library gap;
- a weak existing generic object is `QUALITY_GAP`, not `TRUE_MISSING`;
- one Activity wanting a specialized object does not justify a new generic theme pack;
- **do not create Generic Batch B in this gate**.

If a real generic gap is exposed, record the evidence and proposed generic role, but stop short of adding a new generic tranche unless the owner separately authorizes it.

---

## 14. Automated/source tests

Add or update focused tests sufficient to protect the new visual/runtime contract without screenshot-pixel hardcoding.

At minimum cover source-level properties relevant to the implementation, such as:

- Activity-local runtime asset paths stay package-contained;
- no runtime source SVG dependency;
- all required Activity-local runtime art exists;
- bridge material mapping remains complete for the four IDs;
- all three levels remain present;
- semantic shared visual IDs referenced by the Activity exist;
- canonical character ID/state mapping if Flash is used;
- optional scenery remains fail-soft where marked optional;
- no visual refactor removes expected storage/event/input/localization contract source.

Use existing project testing style. Do not create brittle tests that assert exact drawing coordinates for artistic details unless those coordinates are a real interaction contract.

Required validation before final claim:

```bash
python3 tools/visual_authoring_library.py validate --json
PYTHONPATH=src python3 tools/validate_activity.py activities/costruiamo_ponti
make visual-assets-check
make validate
# focused Costruiamo Ponti tests added/found by inspection
```

Do not run/query GitHub Actions.

---

## 15. Simulator acceptance scenarios

Use a fresh Activity Simulator state and the real Activity-loading path.

Capture the actual child surface, including platform Home chrome where normally visible.

Required curated evidence set:

```text
01-before-river-1024x600.png
02-before-canyon-1024x600.png
03-before-space-1024x600.png
04-after-river-1024x600.png
05-after-canyon-1024x600.png
06-after-space-1024x600.png
07-material-family-and-selection.png
08-crossing-success.png
09-crossing-failure-or-bounce-feedback.png
10-responsive-large-1024x600.png
11-responsive-compact-1366x768.png
12-static-motion-disabled.png
13-optional-visual-fallback.png
```

If one still cannot self-prove a non-obvious condition, add a tiny **developer-only** diagnostic readout or pair it with a structured trace record. Do not ship diagnostics in ordinary child UI.

### 15.1 Before/after worlds

The three before/after pairs must make it possible to judge whether the visual system improved the Activity without changing the gameplay.

### 15.2 Material family

Show all four material visuals at meaningful sizes and prove selected-state readability.

### 15.3 Successful crossing

Capture a useful moment in a correctly built bridge crossing or completion sequence.

### 15.4 Failure/bounce feedback

Capture a meaningful visual response to an incorrect/interesting bridge interaction while preserving child-friendly tone.

### 15.5 Responsive

Prove at minimum:

```text
1024×600 / LARGE
1366×768 / COMPACT
```

and preserve contained/reference-canvas correctness.

### 15.6 Static mode

Disable Activity visual motion using the existing supported simulator/test path if available. The scene, bridge materials and traveler must remain complete and readable.

### 15.7 Optional failure

Corrupt/move one **optional decorative** visual only, in a clean isolated fault-injection session, and prove gameplay remains intact.

Do not corrupt a gameplay-critical bridge material merely to claim fail-soft behavior.

Restore all generated/runtime assets immediately afterward and rerun the relevant validator.

---

## 16. Structured authoring audit

Create:

`docs/reviews/visual/2026-08-22_costruiamo-ponti-visual-authoring-stress/`

Commit:

```text
OWNER_RECHECK.md          # local-agent factual summary, not owner acceptance
authoring-audit.json
simulator-trace.json
13 curated PNGs
```

`authoring-audit.json` must include at least:

```text
activity_id
baseline_commit
baseline_weaknesses
discovery_queries
candidate_assets_inspected
visual_role_decisions
reuse_resources
compose_adapt_resources_and_derivations
create_original_resources
activity_local_source_files
activity_local_runtime_files
traveler_character_decision
three_world_visual_strategy
runtime_architecture
focused_tests_and_results
simulator_scenarios
fault_injection_and_restoration
library_gap_analysis
evidence_classification
```

For every `COMPOSE_ADAPT` or `CREATE_ORIGINAL` item, make it possible for the owner to see exactly what was created and why.

The audit must not call a plain untouched shared asset `COMPOSE_ADAPT` merely because its rectangle/alpha changed.

---

## 17. Owner transfer bundle

Create at repository root and **do not commit**:

`GREIA_VISUAL_REVIEW_COSTRUIAMO_PONTI_AUTHORING_STRESS_2026-08-22.zip`

Include only:

```text
OWNER_RECHECK.md
authoring-audit.json
simulator-trace.json
01-before-river-1024x600.png
02-before-canyon-1024x600.png
03-before-space-1024x600.png
04-after-river-1024x600.png
05-after-canyon-1024x600.png
06-after-space-1024x600.png
07-material-family-and-selection.png
08-crossing-success.png
09-crossing-failure-or-bounce-feedback.png
10-responsive-large-1024x600.png
11-responsive-compact-1366x768.png
12-static-motion-disabled.png
13-optional-visual-fallback.png
```

Do not include the whole project, old review bundles, raw simulator state or unrelated logs in this owner-review ZIP.

---

## 18. Documentation updates on completion

If the exercise succeeds, update the living continuation documents accurately:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

Update `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` or `skills/greia-visual-authoring/SKILL.md` only if the exercise establishes a reusable architectural/practical rule that is not already documented.

Do not rewrite prior Shape Garden or canonical-cast history into this gate.

If the gate fails, preserve the evidence and record the exact blocker rather than writing an optimistic PASS narrative.

---

## 19. Stop conditions

Stop and report instead of improvising if:

- a proposed visual change requires changing puzzle/progression semantics merely to make the art work;
- runtime SVG rasterization seems necessary;
- an Activity-local asset would need to escape the package boundary;
- the work starts creating a second global visual catalogue/cache/scene engine;
- the agent is about to add Generic Batch B merely because a bridge-specific object is missing;
- a canonical character would need to be modified to fit the Activity;
- the existing traveler cannot be replaced without changing gameplay and an original traveler cannot be safely retained/re-authored;
- responsive/safe-area behavior regresses;
- localization, storage, events, audio or hybrid input regress;
- any intentionally corrupted runtime asset remains unrestored;
- the Activity Simulator exposes a traceback, Linux shell or crash surface to the child path;
- the final art is visually worse or materially less readable than the baseline despite technical PASS.

---

## 20. Git completion

Work directly on canonical `main` as required by current project policy.

Before final commit:

```bash
git status --short
python3 tools/visual_authoring_library.py validate --json
PYTHONPATH=src python3 tools/validate_activity.py activities/costruiamo_ponti
make visual-assets-check
make validate
# focused tests

git status --short
```

Then commit coherent source/test/docs/curated-evidence work, pull/rebase or fast-forward safely as appropriate, and push without force.

Final local-agent response should be concise and include:

- final pushed SHA;
- exact `REUSE` / `COMPOSE_ADAPT` / `CREATE_ORIGINAL` summary;
- traveler/character decision;
- generic library-gap classification;
- focused validation results;
- review directory;
- transfer bundle path;
- any unproven physical/runtime claims explicitly excluded.

End with exactly:

```text
VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_COSTRUIAMO_PONTI_AUTHORING_STRESS_2026-08-22.zip
```
