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

# 1. Current focus — Encyclopedia golden-master validation

The owner rejected the old `org.greia.enciclopedia` graphics quality as a final product target after reviewing the complete 43-page 1024×600 mechanical traversal evidence.

The diagnosis remains systemic: final subjects/environments were dominated by raw Pygame primitives, sparse flat backgrounds, instrumentation-like discovery bubbles, corner-stamped presenters and weak visual payoff.

Forensic review:

```text
docs/reviews/2026-08-28_ENCYCLOPEDIA_GRAPHICS_FORENSIC_AUDIT.md
```

Active bounded reauthoring plan:

```text
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
```

E1 + E2 source and runtime art are now implemented on `main`, the six golden-master runtime PNGs are committed and sha256-verified by the build tool's `--check`, and the real Greia Simulator has been launched at the final SHA (`08fe71b`) to capture one curated set of 1024×600 + responsive screenshots. The current rule is therefore narrower still:

> **STOP. The owner must now approve the new visual direction on the six golden-master prototypes. No E3 / E4 page migration before that approval.**

Golden-master targets remain:

```text
Home
Animals section
Lion
Saturn
Gears
Pyramids
optional Body/Heart anatomy proof only if a later review shows it is needed
```

Curated review set:

```text
docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/
  REVIEW.md
  layout-audit.json
  contact-sheet-primary.png
  screenshots/01-home.png            1024x600
  screenshots/02-lion-activated.png  1024x600
  screenshots/03-home-compact.png    1024x600 + interface_size=compact
  screenshots/04-home-large.png      1280x800
```

Owner-transfer archive (not committed):

```text
GREIA_VISUAL_REVIEW_ENCYCLOPEDIA_GOLDEN_MASTER_2026-08-28.zip
```

---

# 2. E1 visual foundation now present in source

Activity-local source owners:

```text
activities/enciclopedia_greia/enciclopedia_presentation.py
activities/enciclopedia_greia/enciclopedia_services.py
```

The bounded foundation now provides:

```text
PageShellLayout safe zones
DiscoveryToken tactile idle/focus/recent language
caption ribbon with adaptive fitting
authored-scene placement
object focus/lift treatment
bounded Activity-local visual cache
explicit semantic-id -> runtime PNG mapping
```

The stable page engine/navigation/factual models were not replaced. The new presentation code is an Activity-local layer over existing Greia boundaries, not a second platform compositor.

Runtime rules remain:

```text
no runtime SVG rasterization
no arbitrary runtime source scanning
no page hot-path pygame.image.load
no page hot-path smoothscale
bounded cache misses only
protected Greia Home untouched
```

---

# 3. E2 golden-master source now present

Editable Activity-local source masters:

```text
activities/enciclopedia_greia/assets/source/home_discovery_book.svg
activities/enciclopedia_greia/assets/source/animals_field_table.svg
activities/enciclopedia_greia/assets/source/lion_savanna.svg
activities/enciclopedia_greia/assets/source/saturn_observatory.svg
activities/enciclopedia_greia/assets/source/gears_workbench.svg
activities/enciclopedia_greia/assets/source/pyramids_diorama.svg
```

Golden-master page source has been migrated for:

```text
Home
Animals section
Lion
Saturn
Gears
Pyramids
```

The pages preserve their semantic input/state contracts. Authored scenes now carry the main pictorial burden while procedural drawing is retained for legitimate dynamic teaching overlays, particles/focus/discovery affordances and interaction responses.

Authoring-only build recipe:

```text
tools/build_encyclopedia_visual_assets.py
```

Focused source contract:

```text
tests/test_activity_enciclopedia_visual_foundation.py
```

A local mirror check of this source shape passed 6/6 plus AST parse. This is **SOURCE/STATIC evidence only**, not Simulator acceptance.

---

# 4. Architecture to preserve

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

For the Encyclopedia, the library is a toolbox rather than a requirement to force reuse. Topic-specific heroes legitimately remain Activity-local.

---

# 5. Generic toolbox state

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

The Encyclopedia redesign does not authorize Generic Batch B by inertia.

---

# 6. Canonical cast v0.1 — accepted runtime family

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

The Encyclopedia golden masters deliberately enlarge/integrate presenters rather than using the old tiny bottom-corner default. Actual composition quality still requires Simulator review.

---

# 7. Stable runtime foundation to preserve

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
- rich authored art should be flattened/cropped into economical runtime surfaces.

---

# 8. Existing accepted visual work remains valid

Prior accepted/reviewed work is not invalidated by the Encyclopedia failure. Stable evidence/history remains in the active visual plan and dated review directories, including:

- canonical cast v0.1 runtime acceptance;
- Shape Garden authoring workflow;
- Costruiamo Ponti stress exercise;
- Painting productization;
- Activity title/icon gate;
- launcher Shell/category-navigation productization;
- first-party visual audit and Batch 1 productization (`treno_numeri`, `labirinto_magico`, `acquario_magico`).

The Encyclopedia lesson remains: **mechanical completion does not excuse programmer-art presentation, and a page-heavy Activity needs a reviewed reusable visual grammar before mass content production.**

---

# 9. Current Encyclopedia evidence boundary

Previously proven and preserved mechanically:

```text
43-page source/runtime structure
real Shell launch on older source
43/43 reachability
36/36 internal Back return
protected Greia Home return
bounded semantic interactions
headless transition-settle harness repair
```

New source evidence:

```text
E1 shared presentation source landed
six editable golden-master SVG masters landed
six golden-master page visual integrations landed
authoring-time build recipe landed
focused visual-foundation source contract landed
local mirror source contracts 6/6 PASS
changed source AST parse PASS
```

Still unverified on the final visual source:

```text
six generated runtime PNGs committed to main
real-checkout focused tests after generation
final-SHA Greia Simulator launch/survival
actual 1024×600 golden-master pixels
activated-state visual payoff
compact/larger responsive samples
pre-reader/no-reading prototype review
owner direction approval
```

Narration remains a separate owner-listening workflow.

---

# 10. Immediate next action

The rolling execution pointer is now:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

Exact sequence:

```text
refresh main
→ build six runtime PNGs from committed SVG masters
→ focused tests + required local verification
→ commit/push generated PNG pack
→ run final-SHA real Greia Simulator gate
→ capture Home / Animals / Lion / Saturn / Gears / Pyramids
→ capture representative ACTIVATE payoffs
→ one compact + one larger responsive sample
→ produce curated contact sheet
→ perform no-reading review
→ update evidence/docs
→ STOP for owner visual direction review
```

**No E3/E4 page migration before owner approval.**

---

# 11. Drift to avoid

- no 43-page bulk redraw before golden-master approval;
- no primitive-art polishing loop;
- no generic Batch B by inertia;
- no second runtime asset/cache/scene system;
- no runtime SVG;
- no CairoSVG child-runtime dependency;
- no AI-generated inconsistent full-screen art dump;
- no detailed skeletal character rigs;
- no tiny corner-mascot default;
- no text-heavy rescue of unclear visuals;
- no broad acceptance reruns before the golden masters are runtime-complete;
- no narration integration in this visual gate;
- no R7/hardware claims from Activity visual work.

R7 remains the primary blocking platform phase. No physical Acer/Pi acceptance is claimed without real hardware evidence.
