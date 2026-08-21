# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-21  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Scene-runtime plan:** `docs/plans/2026-08-21_GREIA_SCENE_COMPOSITION_RUNTIME.md`  
**Parent visual plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Project-wide handover:** `HANDOVER.md`

---

# 1. Resume order

Read, in order:

```text
1. AGENTS.md
2. docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
3. docs/design/GREIA_SCENE_COMPOSITION_RUNTIME.md
4. docs/plans/2026-08-21_GREIA_SCENE_COMPOSITION_RUNTIME.md
5. docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md
6. this file
7. HANDOVER.md
8. skills/greia-visual-authoring/SKILL.md
9. exact source files for the current gate
```

Do not resume from chat memory alone.

---

# 2. Stable production direction

Greia visual production remains:

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → explicit semantic runtime consumption → Shell/Activity reuse**

Non-negotiables:

- asset-first, not crude full-screen mockups;
- polished storybook/toy-diorama language;
- readable at low resolution;
- reuse before duplication;
- no target runtime SVG rasterization;
- no arbitrary runtime asset-directory scanning;
- no per-frame PNG decode/scale;
- bounded runtime caches;
- no simulator-specific production rendering;
- visual work must not deepen provisional X11 coupling or bypass protected platform Home/Back authority;
- no new environment pack merely to keep producing assets.

Broad reusable source coverage already exists under the Forest/Meadow, Shared UI, Workshop, Clinic, Reading/Classroom, Fantasy/Village/Night and Water/Pond packs. Core characters remain Lilli, Nino, Tito and Momo in the accepted Puff/Bean direction.

---

# 3. Proven runtime foundation

The V5 asset/runtime seam is proven across real Shell consumers:

```text
reviewed SVG master
→ explicit source rendition manifest
→ build-time PNG via rsvg-convert
→ generated runtime catalogue
→ AssetCatalogue
→ PygameVisualSurfaceCache
→ real consumer
```

Accepted Shell/product consumers include cards, panels, profile chrome, loading/error feedback, navigation chrome and Collection-first Home.

The graphics workstream has now advanced beyond Shell decoration into the Scene Composition Runtime.

Current scene source owners:

```text
src/greia_platform/scene.py
src/greia_platform/pygame_scene.py
src/greia_platform/scene_actor.py
assets/scenes/forest_meadow_day_v1.toml
```

`PygameSceneRenderer` now also remembers failed optional realizations for the renderer lifetime so a corrupt decorative PNG is not retried/decode-failed every frame. Explicit `clear()` resets both visual cache and failure suppression.

No physical Acer/Pi scene-performance claim and no R7 closure.

---

# 4. First scene integration — retained, but evidence audit corrected

Nascondino nel Bosco is the first real Activity using the shared Forest/Meadow scene compositor.

Retained runtime facts from the headless simulator run:

- background and foreground/atmosphere split passes;
- parallax + ambient motion;
- deliberate legacy background fallback for required scene-art failure;
- optional atmosphere isolation;
- six responsive simulator rows;
- measured **25.8 FPS** over the recorded 10.01 s scene run;
- curated PNG evidence committed under `docs/reviews/visual/2026-08-21_scene-compositor-nascondino/`.

Primary source/evidence cross-check is recorded in:

```text
docs/reviews/visual/2026-08-21_scene-compositor-nascondino/PRIMARY_REVIEW.md
```

Important correction: the local-agent `REVIEW.md` / `layout-audit.json` was not numerically trustworthy. It claimed 22 px target text while accepted source rendered 18 px, recorded a different target-card rectangle from source, claimed Large-interface HUD scaling that source did not perform, and described the scene's `cover` fit as letterbox/pillarbox.

Do not carry those claims forward.

The committed private-repo PNGs are retained for visual evidence, but this primary-agent environment currently receives repository PNG bytes through the GitHub connector as base64 rather than a directly viewable image surface. Therefore the primary agent must not pretend it independently pixel-reviewed those PNGs. Source/runtime geometry and local-agent pixel review remain separate evidence layers.

---

# 5. Current exact gate — first shared Greia character actor

Renderer-neutral actor source is now implemented:

```text
src/greia_platform/scene_actor.py
```

It provides:

```text
semantic character state
neutral/blink variant selection
deterministic blink timing
cheap vertical idle
shared contact shadow
scene z/parallax placement
motion-off static sample
```

It outputs ordinary `SceneNode` data and therefore reuses `PygameSceneRenderer` and the existing semantic cache. No skeletal rig and no second character renderer/cache was added.

First promoted runtime actor assets:

```text
character.lilli/default
character.lilli/blink
shadow.contact.small.01/default
```

Build-time outputs are expected at:

```text
assets/visual/runtime/v1/characters/lilli_neutral.png
assets/visual/runtime/v1/characters/lilli_blink.png
assets/visual/runtime/v1/shared/shadow_contact_small.png
```

Current simulator gate:

```text
docs/testing/2026-08-21_SCENE_ACTOR_LILLI_NASCONDINO_SIMULATOR.md
```

That gate deliberately combines the next graphics-engine feature with correction of the real Nascondino HUD defects rather than spawning another isolated audit cycle.

It must prove:

- Lilli rendered through `SceneActorDefinition` / `actor_scene_sample` using the existing scene renderer;
- neutral + physically closed-eye blink;
- grounded contact shadow;
- subtle idle motion and complete motion-off state;
- no obstruction of protected chrome/gameplay/HUD;
- target animal HUD around 22–24 px normal, >=20 px compact, visibly larger in Large;
- `SCOIATTOLO` fits without clipping/collision/ellipsis;
- profile InterfaceSize affects fixed-reference HUD semantics without double-applying physical viewport scale;
- layout audit is derived from actual runtime/source values rather than hand-entered;
- `cover` crop is described and checked correctly;
- optional corrupt scene art is not retried every frame;
- measured FPS is reported neutrally.

---

# 6. Collection-first product state

Normal child navigation remains:

```text
profile
  → Greia Home
    → primary Collection
      → Activity
```

Primary Home vocabulary is bounded to:

```text
create
play
learn
explore
my_greia
```

Unknown-only valid Activities recover through conditional platform-owned `browse` / `Altro` rather than creating arbitrary Home roots or disappearing. This product work is accepted at simulator scope and is no longer the center of the graphics workstream.

Do not return to category/Home micro-polish unless a real product defect is exposed.

---

# 7. Simulator/evidence rule

Owner-directed local runtime/visual/fallback/responsive acceptance uses the Greia Activity Simulator, preferably:

```bash
GREIA_SIMULATOR_HEADLESS=1 python3 tools/greia_simulator.py --state-dir <isolated-state>
```

Remote bridge remains local loopback only at `http://127.0.0.1:8767`. Do not query/run GitHub-hosted Actions without explicit owner authorization.

Visual gates must follow:

```text
docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md
```

A local-agent prose `PASS` is not enough. Numeric text/layout claims must agree with actual source/runtime values. `layout-audit.json` must not be hand-transcribed when the renderer/layout can report the real geometry.

---

# 8. What comes after the actor gate

Advance from real caller needs, not speculative engine features.

Likely sequence:

```text
first Lilli actor accepted
→ reusable scene/actor Activity authoring adapter
→ one more real Activity family proving reuse
→ only then add missing motion/FX primitives justified by that caller
→ Web scene renderer/transport after Python semantics stabilize
→ physical low-resource proof later
```

Candidate future features such as quantized tilt, Water/Pond shimmer, color/light pulse or low-count particles are not automatic milestones. Add them only when a real scene needs them.

---

# 9. Rejected/drift directions

Do not resume:

- All+filters as normal child Home;
- arbitrary package categories creating Home roots;
- filesystem folders/deep taxonomy;
- endless Shell-widget restyling after the shared seam is proven;
- proof-only Shape Garden work displacing real scenes;
- detailed traditional character rigs;
- generated sprite sheets treated as production-ready;
- crude backgrounds/mockups;
- more environment packs without a demonstrated gap;
- runtime SVG on target;
- arbitrary visual-directory discovery;
- second visual catalogue/cache framework;
- per-frame PNG decode/scale;
- unbounded caches;
- per-resolution production forks;
- simulator-specific production branches;
- hand-written layout audits that disagree with source.

---

# 10. End-of-session rule

Update this file whenever the active visual phase, next action, runtime consumption, evidence boundary, blocker or testing rule materially changes. Chronology belongs in the active plan; stable architecture belongs in `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`; project-wide continuation belongs in `HANDOVER.md`.
