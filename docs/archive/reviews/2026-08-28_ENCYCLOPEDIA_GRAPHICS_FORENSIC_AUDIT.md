# Greia Encyclopedia v0.1 — Deep Graphics Forensic Audit

**Date:** 2026-08-28  
**Scope:** `activities/enciclopedia_greia/`  
**Evidence reviewed:** owner-machine 1024×600 mechanical traversal ZIP `20260828_074819-mechanical-traversal.zip` plus current runtime source on `main`  
**Disposition:** **MECHANICALLY HEALTHY / VISUALLY UNACCEPTABLE AS A PRODUCT TARGET**

This review supersedes any earlier language implying that the current Encyclopedia visuals were close to acceptance. The owner has correctly rejected the present graphics quality. The problem is systemic, not a short list of polish defects.

The frozen 43-page runtime architecture and navigation can remain useful. The visual presentation needs a serious reauthoring pass before final Simulator visual acceptance.

---

## 1. What is actually wrong

The current Encyclopedia is dominated by **programmer-drawn Pygame primitives** arranged into technically clear but aesthetically crude diagrams. It is readable and deterministic, but it does not look like the Greia visual system described by the accepted art authorities.

The strongest existing visual-system rule says:

> polished storybook / felt-board / toy-diorama presentation with strong silhouettes, warm local light, shallow tactile depth, clean alpha edges, controlled gradients, soft cast/contact shadows and low-resolution readability.

The current Encyclopedia largely does the opposite:

- hero subjects are often circles, ellipses, rectangles, arcs and flat polygons;
- section pages resemble debug menus or classroom diagrams rather than inviting worlds;
- backgrounds are usually flat fills plus one or two primitive hills/floors;
- important objects have little or no texture/material/light treatment;
- visual depth is almost absent;
- characters are reduced to small corner mascots rather than integrated scene actors;
- discovery controls are small floating white circles that read like instrumentation, not playful child affordances;
- text bars at the bottom carry too much explanatory burden for a pre-reader-first experience;
- the visual language varies by page because every page manually draws its own subject rather than consuming a coherent reusable presentation kit;
- interaction feedback is often a tiny change to a diagram rather than a delightful transformation of the scene.

The result is not merely "simple." It looks unfinished.

---

## 2. Why this happened

### 2.1 The runtime architecture is cleaner than the presentation architecture

The page/navigation architecture is explicit and bounded, but the visual layer never received an equivalent reusable design system.

Typical page code directly performs:

```text
surface.fill(...)
pygame.draw.circle(...)
pygame.draw.ellipse(...)
pygame.draw.rect(...)
pygame.draw.line(...)
pygame.draw.polygon(...)
```

for both layout and the *main illustrated subject*.

That is acceptable for:

- diagrams;
- tiny indicators;
- focus rings;
- simple pedagogical overlays;
- particles or motion helpers.

It is not acceptable as the default authoring method for final lions, elephants, planets, bicycles, aircraft, pyramids, volcanoes, body scenes, section worlds or navigation portals.

### 2.2 The Encyclopedia bypasses much of Greia's existing visual foundation

Greia already has:

- generic source-art discovery;
- activity-local asset authoring rules;
- canonical character renditions;
- build-time source→PNG workflow;
- bounded visual caches;
- scene composition with layers/parallax/ambient motion;
- shared shadows, atmosphere and UI components.

The current Encyclopedia uses only a small fraction of this. The recurring character renderer appears, but most page art remains local procedural drawing.

### 2.3 The current layout template encourages sameness without coherence

Most factual pages use roughly:

```text
TITLE

small circular discovery token    small circular discovery token

              large central primitive diagram

small circular discovery token    small circular discovery token

              text caption pill
                                  small mascot
```

This is structurally consistent, but it is visually sterile. The page changes topic while retaining the feeling of a diagnostic/control panel.

### 2.4 Pre-reader support is technically present but aesthetically weak

There are icons and audio cues, but the child is still confronted with:

- abstract icon buttons;
- tiny symbols;
- caption-heavy bottom strips;
- weak visual storytelling;
- little environmental context explaining what should be touched.

A three- or four-year-old should want to touch the scene because the illustration itself invites exploration.

---

## 3. Evidence-level findings

### 3.1 Home

Current Home is a 2×3 grid of bordered white cards over primitive green hills.

Problems:

- looks like a launcher/menu inside another launcher;
- duplicates card-based OS presentation instead of feeling like opening an encyclopedia;
- category symbols are competent placeholders but not evocative mini-worlds;
- large empty areas and flat colors create a prototype feel;
- Leo is too small and disconnected from the composition.

Required direction: **six illustrated discovery portals/mini-dioramas**, not six plain UI cards.

### 3.2 Section pages

Animals, Body, Machines and History show the issue most clearly.

Animals is six white cards with tiny primitive animal icons. Machines is a flat tan board containing schematic object symbols. Body is a mannequin with circular callouts. History is essentially a horizontal row of cards.

These are legible information diagrams, not child-facing illustrated spaces.

Required direction: sections should feel like **places or spreads** — habitat shelf, star observatory, nature field table, body discovery room, workshop bench, history trail — while preserving simple bounded navigation.

### 3.3 Factual entry pages

The factual logic is often good. The visuals do not carry it.

Examples:

- Lion: flat assembled circles/rectangles with four floating icon buttons.
- Elephant: simplified gray geometry with almost no environmental identity.
- Octopus: flat magenta procedural octopus over a minimal sea strip.
- Bee: minimal flowers and a tiny bee; interaction reads more as state change than discovery.
- Gears: textbook-colored gear diagram on a beige field.
- Magnet: bar magnets on a flat pale background.
- Bicycle: thin line diagram.
- Airplane: translucent-looking triangle construction rather than a charming aircraft illustration.
- Bridge: a beam plus pillars and a small block.
- Pyramids: schematic courses, useful conceptually but visually unfinished.

Space is somewhat stronger because the dark field creates focus and the geometry suits astronomy, but the planets still lack authored material, glow, atmospheric richness and scene depth.

### 3.4 Characters

Canonical characters are among the strongest assets on these screens, but their use is weak:

- typically 120–155 px tall in a corner;
- not visibly connected to the subject;
- rarely framed by scene composition;
- do not guide the child's eye toward the active discovery;
- often look pasted on after the page was designed.

Characters should not dominate every page, but when present they need to participate in the composition.

### 3.5 Interaction language

Current selected discovery token = yellow focus ring around a small circular icon.

This is mechanically clear but emotionally flat.

The final system should use tactile discovery tokens that feel like:

- stickers;
- chunky wooden/felt badges;
- magnifying lenses;
- specimen tags;
- glowing stars;
- knobs/levers where semantically appropriate.

Selection should create a visible change in depth/scale/glow, not only a thin border.

---

## 4. What should be preserved

A redesign must **not** throw away good engineering because the art is weak.

Preserve:

- 43-page frozen information architecture;
- explicit `PageRegistry` and bounded navigation;
- semantic input model;
- protected Greia Home separation;
- Encyclopedia internal Back;
- narration cue IDs and research authority;
- existing factual interaction state/models where educationally sound;
- low-resource/offline constraints;
- canonical cast identities;
- 1024×600 baseline and responsive layout contracts;
- source/runtime separation;
- fail-soft visual loading;
- bounded caches;
- current headless traversal infrastructure after its capture-settle repair.

The target is **visual reauthoring on top of stable mechanics**, not a rewrite of the entire Activity.

---

## 5. New quality bar

No factual page may be called visually complete merely because:

```text
it launches
it has no clipping
its before/after pixels differ
all text fits
all controls are reachable
```

A visually complete Encyclopedia page must additionally satisfy:

1. **Focal illustration:** one clearly authored hero subject or scene, recognizable before reading.
2. **Material/depth:** at least shallow tactile depth through authored shading, contact shadow, layered silhouette or controlled light.
3. **Context:** enough environmental/story context that the subject does not float on an empty debug canvas unless abstraction is pedagogically intentional.
4. **Discovery affordance:** child-sized, high-contrast, visually inviting hotspots/tokens.
5. **Interaction payoff:** the first activation produces a clear, meaningful visual response.
6. **Character integration:** when a canonical character is present, it feels composed into the scene rather than stamped in a corner.
7. **Pre-reader readability:** the main action and subject are understandable without reading the caption.
8. **Low-resolution clarity:** silhouette and action survive 1024×600 and compact layouts.
9. **System coherence:** page follows the Encyclopedia visual grammar while retaining topic-specific personality.
10. **Runtime economy:** richness is authored/build-time; target hardware performs cheap bounded composition.

---

## 6. Hard prohibitions for the reauthoring

Do not solve this by:

- replacing primitive art with a larger pile of slightly nicer primitives;
- generating 43 unrelated full-screen pictures with no reusable system;
- using AI-generated raster scenes with inconsistent style and no editable source provenance;
- making every page a card grid;
- adding more text to explain unclear visuals;
- creating a heavy animation/runtime framework;
- rasterizing SVG at runtime;
- decoding/scaling assets every frame;
- using realistic detailed character rigs;
- hiding poor interaction design under particles/glow;
- bulk-redrawing all 43 pages before a small golden-master set is owner-approved.

---

## 7. Immediate decision

The next Encyclopedia milestone is **not final visual acceptance** and not another broad 43-page evidence run.

The next milestone is a **visual reauthoring foundation + golden-master prototype set**. Only after that visual direction is demonstrably good should the design be propagated to all 43 pages.

Detailed implementation sequencing is owned by:

`docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md`
