# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-28  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Active visual plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Current Activity visual subplan:** `docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md`  
**Visual-authoring architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Generic art taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**Canonical cast system:** `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`

---

# 1. Current focus — Encyclopedia visual reauthoring

The owner rejected the present `org.greia.enciclopedia` graphics quality as a final product target after reviewing the complete 43-page 1024×600 mechanical traversal evidence.

The problem is systemic rather than a small polish list. The current Activity relies too heavily on raw Pygame primitives for its main illustrated subjects and environments, producing mechanically clear but crude screens that conflict with Greia's accepted storybook/felt-board/toy-diorama art direction.

Forensic review:

```text
docs/reviews/2026-08-28_ENCYCLOPEDIA_GRAPHICS_FORENSIC_AUDIT.md
```

Active bounded reauthoring plan:

```text
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
```

Current rule:

> **Do not bulk-redraw 43 pages. Build an Encyclopedia visual foundation, then a representative golden-master set, obtain owner direction approval, and only then migrate the complete Activity.**

Golden-master targets:

```text
Home
Animals section
Lion
Saturn
Gears
Pyramids
optional Body/Heart anatomy proof
```

No broad 43-page visual recapture is useful until this direction is reauthored.

---

# 2. Architecture to preserve

Greia still uses two visual-authoring tracks.

## Track A — maintainer-side source/toolbox/canonical-cast production

The owner's local maintainer agent may create or improve Greia source art. That drawing ability is not a product dependency and is not evidence about arbitrary future Activity-authoring agents.

## Track B — arbitrary Activity-authoring agents

Model/tool-agnostic workflow:

```text
inventory Activity needs
→ query/search generic semantic library
→ use canonical characters/states where appropriate
→ REUSE / COMPOSE-ADAPT / CREATE ORIGINAL
→ create Activity-local final art where required
→ flatten/build efficient runtime renditions
→ integrate through existing Greia package/scene boundaries
→ inspect actual rendered pixels
```

For the Encyclopedia, the library is a toolbox rather than a requirement to force reuse. Most topic-specific heroes will legitimately require original Activity-local artwork.

---

# 3. Generic toolbox state

Current indexed state remains:

```text
57 preferred finished assets
37 candidate-reference finished assets
7 preferred authoring ingredients
101 indexed reusable visual resources
```

Discovery helper:

```text
tools/visual_authoring_library.py
```

Permanent rules:

- `preferred` is first-choice direct reuse;
- `candidate_reference` is primarily reference/adaptation material;
- generic assets encode reusable form while Activity-specific meaning stays separable where practical;
- **Generic Batch B remains unauthorized** unless real demand proves a concrete generic gap.

The Encyclopedia redesign does not automatically authorize a new generic pack. Topic-specific art should normally stay Activity-local.

---

# 4. Canonical cast v0.1 — accepted runtime family

Current cast:

```text
Lilli — unicorn                        creativity / stories / art / imagination
Leo   — owl with integrated glasses   learning / reading / language / knowledge
Flash — white rabbit + lightning top  games / speed / action / challenge
Dani  — friendly robot                math / logic / patterns / sequencing
Tito  — fox                           exploration / nature / discovery
Momo  — monster                       emotion / music / silly play / celebration
```

Stable source:

```text
assets/visual/characters/canonical/v0.1/
```

Accepted states:

```text
neutral
blink
happy
surprised
sleepy
```

Accepted motions:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Runtime rule remains:

> complete authored state art + authoring-time semantic source components + build-time PNG renditions + simple whole-character fixed-size transforms.

For the Encyclopedia specifically, characters should be integrated compositionally rather than stamped as tiny bottom-corner mascots.

---

# 5. Stable runtime foundation to preserve

```text
explicit semantic asset catalogues
build-time source/SVG → runtime PNG renditions
bounded Pygame visual cache
bounded failed-rendition memory
SceneDefinition / SceneNode / SceneCamera
PygameSceneRenderer
SceneActorDefinition / actor_scene_sample
Greia Activity Simulator real Shell/runtime composition
```

Runtime rules:

- no arbitrary runtime source scanning;
- no normal runtime SVG rasterization;
- no per-frame disk decode/scale;
- bounded caches;
- Activity-local assets remain inside Activity packages;
- generic authoring indexes remain authoring-time facilities;
- rich authored art should be cropped/flattened into economical runtime surfaces.

---

# 6. Existing accepted visual work remains valid

Prior accepted/reviewed work is not invalidated by the Encyclopedia failure. Stable evidence/history remains in the active visual plan and dated review directories, including:

- canonical cast v0.1 runtime acceptance;
- Shape Garden authoring workflow;
- Costruiamo Ponti stress exercise;
- Painting productization;
- Activity title/icon gate;
- launcher Shell/category-navigation productization;
- first-party visual audit and Batch 1 productization (`treno_numeri`, `labirinto_magico`, `acquario_magico`).

The lesson from the Encyclopedia is narrower but important: **mechanical completion does not excuse programmer-art presentation, and a page-heavy Activity needs a reusable visual grammar before mass content production.**

---

# 7. Current Encyclopedia evidence boundary

Already proven and preserved:

```text
43-page source/runtime structure
real Shell launch
43/43 reachability
36/36 internal Back return
protected Greia Home return
bounded semantic interactions
headless transition-settle harness repair
```

Not visually accepted:

```text
current Home aesthetic
current six section-page aesthetics
current factual-entry art direction
current discovery-token treatment
current presenter composition
final pre-reader visual quality
final responsive visual quality
```

Narration remains a separate owner-listening workflow.

---

# 8. Immediate next action

Implement only:

```text
E1 — Encyclopedia shared visual foundation
+
E2 — golden-master prototypes
```

Sequence:

```text
inventory reusable assets
→ define Activity-local source/runtime art structure
→ implement DiscoveryToken + hero-stage/page-shell helpers only where genuinely shared
→ reauthor Home + Animals section + Lion
→ extend same grammar to Saturn + Gears + Pyramids
→ focused tests
→ actual Simulator prototype captures
→ one contact sheet
→ STOP for owner/primary visual review
```

Do not migrate the remaining pages before direction approval.

---

# 9. Drift to avoid

- no 43-page bulk redraw before golden-master approval;
- no primitive-art polishing loop;
- no generic Batch B by inertia;
- no second runtime asset/cache/scene system;
- no runtime SVG;
- no AI-generated inconsistent full-screen art dump;
- no detailed skeletal character rigs;
- no tiny corner-mascot default;
- no text-heavy rescue of unclear visuals;
- no broad acceptance reruns before a visually meaningful state changes;
- no R7/hardware claims from Activity visual work.

R7 remains the primary blocking platform phase. No physical Acer/Pi acceptance is claimed without real hardware evidence.
