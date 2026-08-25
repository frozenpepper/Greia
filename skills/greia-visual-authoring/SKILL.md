---
name: greia-visual-authoring
description: Task router for Greia visual asset creation, reuse, adaptation, scene composition, character art, Activity visual integration and visual acceptance. Load only the task-specific local docs required for the work.
---

# Greia Visual Authoring — task router

**Status:** living derived contributor router  
**Reviewed:** 2026-08-24

Keep this file small. It tells an agent **what to read for the visual task**; it is not a duplicate art/style/runtime manual.

## Universal rules

These apply to substantive Greia visual work:

1. Preserve Greia visual coherence, but do not force reuse when an Activity genuinely needs original art.
2. Choose deliberately between **REUSE**, **COMPOSE/ADAPT**, and **CREATE ORIGINAL**. Existing library content is a toolbox, not a completeness promise.
3. Shared/canonical assets are not Activity-owned. Do not modify shared source assets in place from an Activity.
4. Activity-local art stays portable inside the Activity package. Do not hard-code host filesystem paths or add runtime directory scanning.
5. Authoring-time richness must become runtime-efficient assets. Do not make low-end Greia hardware repeatedly decode, rasterize, scale or rebuild static art during play.
6. Do not imitate protected Greia Home/Back/system chrome with Activity artwork.
7. Meaningful visual work requires inspection of actual rendered pixels. A producer-written `PASS` is not visual acceptance.
8. If visual work changes Activity runtime code/assets/resources, also follow the Activity authoring router and final Simulator launch gate.

Start from the task map below. Do **not** read every visual document by default.

## Read by task

### Broad Greia visual-system architecture

Use only for genuinely cross-cutting visual-system work:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
```

These explain source-library/runtime-rendition ownership and the boundary between maintaining Greia's art system and authoring one Activity.

### Style, visual language or quality-bar decisions

Read:

```text
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md
docs/adr/0034-child-text-letter-case-policy.md
```

Use these when deciding shape language, palette/value relationships, material treatment, silhouette quality, typography relationship or the reusable visual quality bar.

Child-facing UI words are presented in CAPITAL letters by default (ADR 0034, style guide §3.3); treat letter case as part of the accepted visual language and never hand-style it per asset.

### Finding reusable generic art

Read:

```text
docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md
```

Use the repository discovery helper instead of manually crawling source folders:

```bash
python tools/visual_authoring_library.py collections
python tools/visual_authoring_library.py search <need>
python tools/visual_authoring_library.py show <semantic-id>
```

Prefer `library_status = "preferred"` for direct reuse. Treat `candidate_reference` as reference/adaptation material unless a narrower accepted document says otherwise.

The canonical authoring index lives under:

```text
assets/visual/authoring_library/
```

### Creating or adapting Activity-local art

Read:

```text
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
```

Then inspect the Activity's own:

```text
activity.toml
assets/
rendering/presentation code
```

Do not let library availability dictate gameplay design. If no suitable reusable asset exists, create coherent Activity-local artwork rather than shipping programmer placeholders.

### Scene composition, layers or runtime visual integration

Read:

```text
docs/design/GREIA_SCENE_COMPOSITION_RUNTIME.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
```

For Activity viewport/layout behavior also read:

```text
docs/design/GREIA_ACTIVITY_CANVAS_AND_VIEWPORT_AUTHORING.md
docs/adr/0026-resolution-adaptive-ui-layout.md
docs/adr/0027-activity-coordinate-spaces-canvas-and-world-camera.md
```

Use existing Greia scene/runtime boundaries instead of inventing another compositor, global asset catalogue or unbounded cache.

### Canonical characters, expressions or motion

Read:

```text
docs/design/GREIA_CANONICAL_CAST_SYSTEM.md
docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
```

Preserve canonical identity when using recurring Greia characters. Do not infer current cast/voice facts from older screenshots or stale prose when a narrower current authority exists.

### Activity launcher icon work

Read:

```text
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
skills/greia-activity-authoring/SKILL.md
```

Inspect the exact current package-icon validator/resolver before authoring final files:

```text
src/greia_platform/activity_assets.py
src/greia_launcher/title_presentation.py
```

Do not bake language flags or localized text into Activity icons; Greia owns dynamic title/language presentation.

### Achievement/badge artwork

Read:

```text
docs/design/GREIA_ACTIVITY_ACHIEVEMENT_ART.md
docs/design/GREIA_ACHIEVEMENTS_AND_BADGE_LIBRARY.md
```

Activity artwork may provide bounded decorative emblems where allowed, but the platform owns achievement truth, tier/frame, localization, profile state and celebration behavior.

### Shell/launcher visual work

Read:

```text
docs/adr/0018-lightweight-ui-foundation.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
```

For platform implementation changes also route through:

```text
skills/greia-os-work/SKILL.md
```

### Boot artwork or boot animation

Do not treat this as ordinary asset work. Route through the boot/recovery contract first:

```text
skills/greia-os-work/BOOT.md
docs/design/GREIA_BOOT_EXPERIENCE.md
docs/design/GREIA_BOOT_PROGRESS.md
```

Any physical boot change must preserve the OS-work boot safety/recovery invariants.

### Activity visual refresh that changes runtime assets/code

Read:

```text
skills/greia-activity-authoring/SKILL.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
```

The final runtime-relevant Activity state must launch through Greia Simulator and survive the required acceptance path. A beautiful asset set attached to an Activity that no longer launches is failed work.

### Visual acceptance / screenshot evidence

Read:

```text
docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md
```

For meaningful runtime visual work:

```text
render actual target state
capture representative screenshots
inspect clipping / hierarchy / scaling / grounding / occlusion / coherence
include responsive evidence when relevant
record the exact source state and evidence lane
```

Simulator visual evidence is not physical Acer/Pi evidence.

### Performance-sensitive visual optimization

Read:

```text
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
skills/greia-os-work/SKILL.md        # platform/Shell work
skills/greia-activity-authoring/SKILL.md  # Activity work
```

Do not trade visual correctness for speed without inspecting the optimized output. Hardware speed claims require named physical hardware and exact source SHA.

### Maintaining/promoting the shared visual library itself

Read:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
```

Promotion is deliberate:

```text
Activity-local / source candidate
-> proven useful
-> broadly reusable?
-> maintainer review
-> optional shared-library promotion
```

Do not automatically promote every good Activity asset into the global library.

## Completion check

Before calling substantive visual work done, record:

```text
1. What visual task was being performed?
2. Which task-specific local authorities were read?
3. Was each important asset REUSE / COMPOSE-ADAPT / CREATE ORIGINAL?
4. What actual rendered evidence was inspected?
5. If Activity runtime assets/code changed, what exact final state passed LAUNCH_ACCEPTANCE?
6. What remains unverified, especially physical-device appearance/performance?
```

Use this router to load the smallest relevant context. Expand to broad visual-system documents only when the task genuinely crosses several visual subsystems.
