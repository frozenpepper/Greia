# Encyclopedia Golden-Master — Primary Visual Review

**Date:** 2026-08-29  
**Evidence source SHA:** `08fe71b077d47b511c105bde5c2e8fdb88be7b92`  
**Reviewed repository head:** `d74cc26510e2d52ed12ba20062b856572e15cce8`  
**Evidence:** `docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/` plus the complete owner-supplied local evidence archive  
**Disposition:** **E1 ARCHITECTURE ACCEPTED / E2 VISUAL DIRECTION REQUIRES ONE MORE BOUNDED REFINEMENT / E3 REMAINS BLOCKED**

This review is a primary-agent visual/design assessment of the real Greia Simulator pixels. It does not override the owner's final aesthetic authority. It deliberately separates engineering/runtime success from visual-direction approval.

---

## 1. Evidence validity

The evidence is valid for the runtime-art source state at `08fe71b`:

- the six built runtime PNGs are committed there;
- `build_encyclopedia_visual_assets.py --check` passed against the committed masters;
- focused Encyclopedia tests passed;
- `make verify` passed 1462/1462;
- all six golden-master sessions launched through the real Greia Shell path;
- the Activity survived the required interval and returned through protected Greia Home;
- the package contains real 1024x600 Home, Animals, Lion, Saturn, Gears and Pyramids captures plus activated states and compact/larger samples.

The later `d74cc26` head is three commits ahead of `08fe71b`; the intervening changes are evidence/docs/capture tooling plus an unrelated release-readiness documentation merge. No runtime-art change invalidates the captured pixels.

The recurring child-log line:

```text
libpng error: bad adaptive filter value
```

remains unresolved diagnostic evidence. No traceback, crash or visible missing-asset pattern in this capture set proves a causal link to the Encyclopedia golden-master PNGs, so it is not used as an aesthetic verdict here.

---

## 2. What succeeded

The reauthoring is a major improvement over the rejected procedural/card prototype.

### Architecture and low-resource production

Accepted as the correct direction:

- editable Activity-local source masters;
- deterministic authoring-time SVG -> PNG build;
- bounded runtime art cache;
- no runtime SVG/CairoSVG dependency;
- no page hot-path decode/scale;
- semantic input/state models preserved;
- explicit visual/input geometry contract for selection worlds;
- authored scene carries the main pictorial burden while procedural drawing is reserved for meaningful dynamic overlays.

This is the visual-production architecture to keep.

### Navigation and pre-reader structure

The new pages clearly communicate selection/focus and preserve readable Home/Back affordances. The six prototypes are understandable without needing prose for the first action. The local no-reading result is credible for this narrow prototype set.

### Strongest individual improvements

- **Saturn** is the strongest reference screen: dominant subject, coherent dark palette, clear astronomy identity and good use of the full stage.
- **Lion** establishes a workable hero-subject composition and is substantially better than the rejected programmer-art version.
- **Home** replaces generic launcher cards with a genuine book metaphor.
- **Animals** is now one continuous illustrated world rather than six white cards.
- **Gears** has a coherent workshop frame and preserves genuine mechanism clarity.
- **Pyramids** has meaningful environmental/construction context instead of a bare classroom diagram.

These are real advances and should be preserved rather than restarted.

---

## 3. Why E2 is not yet approved for broad migration

The current screenshots still reproduce several failure modes that the reauthoring plan explicitly set out to remove.

### 3.1 Discovery controls still read as instrumentation

The dominant four-discovery treatment on Lion, Saturn, Gears and Pyramids is still a set of large pale circular controls floating around the subject. They are clearer than the old bubbles, but aesthetically they still read as UI instruments pasted over an illustration rather than tactile discoveries belonging to the world.

This conflicts with the plan's intended sticker/felt-medallion/object language.

**Required correction:** keep the fixed semantic hit/focus model, but reduce the visual chrome and make each discovery feel scene-native: irregular felt/paper badges, pinned specimen tags, workshop tokens, telescope cards, archaeological markers, etc. The four pages may share interaction states without sharing an identical white-circle silhouette.

### 3.2 Presenters are still mostly corner stamps

The new presenter sizes are better, but the actual Simulator pixels still place Tito/Leo/Dani largely at the lower screen corners, visually separate from the teaching action.

The plan explicitly prohibited making the tiny/corner mascot treatment the default.

**Required correction:** integrate presenters compositionally. Examples:

- Leo leaning over/pointing into the Home book;
- Tito peeking through grass or inspecting the Animals habitat;
- Tito reacting beside the lion rather than sitting on an unrelated corner patch;
- Leo looking through/standing by the Saturn telescope;
- Dani holding or inspecting a workshop tool next to the gears;
- Leo observing the construction scene or holding a small field notebook near the Pyramids foreground.

Do not introduce skeletal rigs or expensive animation. Whole-character placement/reaction remains enough.

### 3.3 Material/depth quality is still too flat

The screens are clean, readable and coherent, but they still lean toward generic flat-vector illustration. The target is cut-paper/felt/storybook/toy-diorama: baked material variation, contact shadow, edge treatment, overlap and shallow foreground/background depth.

The local review itself scored depth/material quality only `3/5` across all six prototypes. That is the correct warning signal. It should not be averaged away by stronger recognizability scores.

**Required correction:** one authored-art pass should add restrained baked texture/material and more explicit depth bands without increasing runtime complexity. Do this in the SVG/source/build lane, not with runtime shaders or per-frame effects.

### 3.4 Interaction payoff is technically present but sometimes too subtle

The activated-state claims are valid, but not all are strong enough to carry the learning visually:

- Lion's mane ring is understandable but modest.
- Saturn's Earth/orbit hint is small compared with the dominant planet.
- Gears' contact-point rings are readable but small.
- Pyramids' base-layer highlight is particularly easy to miss.

The caption often does more explanatory work than the visual change.

**Required correction:** strengthen the first activation on the four entry prototypes so the subject itself visibly changes/reveals/animates. Captions remain secondary support.

### 3.5 Home is a good frame but its domains are still icons, not mini-worlds

The open-book metaphor works. However, the six domains remain simplified symbols on a page rather than the more evocative mini-diorama/portal scenes described in the plan.

Do not replace the book architecture. Improve the six domain illustrations so each one immediately suggests a world worth entering.

### 3.6 Animals still has composition/scene issues

The six subjects are recognizable, but scale and habitat relationship remain loose: several animals read as floating stickers distributed across a landscape rather than inhabitants of a coherent explorer scene. The sun also crowds/overlaps the Back area as already recorded.

**Required correction:** tighten the spatial composition, remove the sun/Back conflict, and use small habitat/context cues so the six selectable subjects feel deliberately placed rather than scattered.

### 3.7 Gears and Pyramids still show prototype artifacts

- Gears: the right-hand rack intrudes on the green gear and the board still reads somewhat like a polished diagram rather than a physical toy/workbench.
- Pyramids: worker figures and construction props remain very schematic; the central pyramid's grid lines still lean toward classroom-diagram language.

These are good bases, not final exemplars for 37 more pages.

---

## 4. Page-by-page disposition

| Prototype | Disposition | Notes |
|---|---|---|
| Home | **REFINE** | Keep open-book concept; enrich six portals; integrate Leo into book scene |
| Animals | **REFINE** | Keep continuous world; improve habitat composition; fix Back/sun conflict; integrate Tito |
| Lion | **REFINE LIGHTLY** | Keep hero/layout; improve material depth, discovery-token integration, presenter relation and activation payoff |
| Saturn | **REFERENCE / REFINE LIGHTLY** | Strongest current exemplar; preserve composition/palette; integrate tokens/presenter; strengthen first reveal |
| Gears | **REFINE** | Keep workshop/mechanism; fix rack overlap; increase toy/workbench material depth; integrate Dani |
| Pyramids | **REFINE** | Keep construction/diorama idea; replace stick-figure/prototype feeling; reduce diagram-grid dominance; strengthen reveal |

No page needs to be thrown away. This is a bounded refinement pass, not another restart.

---

## 5. E2R refinement gate

Before E3 can start, perform **E2R — Golden-master visual refinement** only on the same six pages.

Required outcomes:

1. discovery controls no longer read as identical floating white instrumentation circles;
2. presenters are compositionally connected to each scene;
3. each page has visibly stronger material/depth treatment baked into authored art;
4. Home domains read as miniature worlds rather than abstract icons;
5. Animals composition/habitat placement is tightened and the Back/sun collision is gone;
6. first activation payoff on Lion/Saturn/Gears/Pyramids is visually stronger without relying on caption text;
7. Gears rack/gear overlap is corrected;
8. Pyramids workers/construction foreground feels illustrated rather than stick-figure/prototype;
9. the low-resource architecture and semantic behavior remain unchanged;
10. capture only the same six golden masters again, not the full 43-page catalogue.

After E2R, produce one new 3x2 Simulator contact sheet plus before/after activated samples. Then stop for owner review again.

---

## 6. Gate decision

```text
E1 VISUAL ARCHITECTURE:            ACCEPTED
E2 RUNTIME/TEST/SIMULATOR EVIDENCE: VALID
E2 PRE-READER PROTOTYPE FLOW:       PASS AT NARROW SCOPE
E2 VISUAL DIRECTION FOR PROPAGATION: NOT YET APPROVED
E2R GOLDEN-MASTER REFINEMENT:       REQUIRED
E3 SECTION MIGRATION:               BLOCKED
E4 ENTRY MIGRATION:                 BLOCKED
NARRATION:                          SEPARATE / UNCHANGED
PHYSICAL HARDWARE ACCEPTANCE:       SEPARATE / UNCHANGED
```

The important conclusion is not that the golden masters failed. They proved the architecture and moved the Encyclopedia from crude programmer art to a coherent authored visual system. The remaining work is a **quality refinement of that system before multiplication**, which is exactly what the golden-master gate was designed to catch.
