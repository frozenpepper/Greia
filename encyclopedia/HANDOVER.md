# Greia Encyclopedia workstream handover

**Updated:** 2026-08-29  
**Runtime pages:** **43 / 43 planned executable pages**  
**Runtime Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)  
**Last Simulator-captured visual SHA:** `8fa41a3e9ab4b8cff6cce9607c32492fedc6ae8f` — **E2R pixels rejected by owner**  
**Current state:** **MECHANICAL FOUNDATION HEALTHY / E1 ARCHITECTURE PRESERVED / E2R VISUAL DIRECTION REJECTED / OWNER-DIRECTED SOURCE REPAIR ACTIVE / RUNTIME PNGS STALE / E3+E4 BLOCKED / NARRATION SEPARATE**

This file is the current continuation contract. Historical construction detail remains in `encyclopedia/PROGRESS.md`, Git history, and dated visual reviews.

---

## 1. Frozen v0.1 scope

Exactly 43 executable pages:

```text
home
animals + 6 entries
space + 10 entries
earth + 5 entries
body + 5 entries
machines + 5 entries
history + 5 entries
```

The 36 factual entry IDs remain frozen by `encyclopedia/pages/catalogue.py` and the runtime registry. Visual repair is not permission to change factual scope.

---

## 2. Runtime architecture invariants to preserve

- `main.py` remains a thin composition root.
- `enciclopedia_engine.py` owns lifecycle, explicit page registry, semantic input and bounded internal navigation.
- Subject behavior stays in page modules/models.
- Runtime remains offline and low-resource: no runtime TTS, speech recognition, AI/LLM, network factual lookup or heavy physics.
- Spoken material remains authoring-time prerecorded audio only.
- Greia protected Home remains platform-owned; Encyclopedia internal Back is separate.
- Italian and English remain the initial locales.
- Visual/text/audio caches remain explicitly bounded.
- Acer Aspire One-class hardware remains the performance floor.
- Keep the Activity-local authored-art source/runtime split and deterministic SVG→PNG authoring build.
- No runtime SVG/CairoSVG and no page-hot-path image decode/scale.

The owner rejected the art, **not** these architectural boundaries.

---

## 3. Previously proven mechanical foundation

Older evidence established:

```text
43 / 43 page reachability
36 / 36 entry semantic ACTIVATE delivery
36 / 36 internal Back returns
protected Greia Home -> Shell
continuous real-Shell lifecycle
focused source gates / make verify
```

That evidence remains useful for mechanics. It does not aesthetically approve newer artwork and does not substitute for fresh Simulator evidence after runtime-relevant visual edits.

---

## 4. E2/E2R evidence disposition

The real E2R Simulator capture at:

```text
8fa41a3e9ab4b8cff6cce9607c32492fedc6ae8f
```

was technically valid, but the owner rejected its visual quality after inspecting the actual pixels.

Owner-identified failures:

```text
Home      six category worlds did not fit naturally inside the illustrated book
Lion      face/head/mane looked disconnected; tail looked detached from body
Animals   elephant was not recognizable; adjacent lion was also ambiguous
Gears     wheels did not convincingly look like gears and did not physically mesh
```

Therefore:

```text
E1 VISUAL/ASSET ARCHITECTURE: PRESERVE
E2/E2R AESTHETIC DIRECTION: REJECTED
OWNER DIRECTION APPROVAL: NOT GRANTED
E3 SECTION MIGRATION: BLOCKED
E4 ENTRY MIGRATION: BLOCKED
```

Do not reinterpret the prior green tests or Simulator survival as visual approval.

Primary correction record:

```text
docs/reviews/visual/2026-08-29_encyclopedia_owner_direct_repairs/REVIEW.md
```

---

## 5. Current owner-directed source repairs on `main`

The owner explicitly requested that the primary agent make the visual corrections directly and slowly rather than delegate another art pass to the local agent.

### Home — enlarge the existing book, do not redesign the menu

Commit:

```text
46a937616610b3ce8c089ef8a1f0dc835373b36e
```

The existing six miniature category worlds and semantic centers were retained. Only the illustrated book/grounding was enlarged so the cards sit inside the page artwork:

```text
book width:  roughly x=120..904 -> x=78..946
book height: bottom roughly 488 -> 520
```

### Lion — coherent animal silhouette

Commits:

```text
a7b8840528118f393aad91bb5b5692d6149799cf
e955d3e3d662d45ff53018a6197a4ed21f659cef
```

The face is nested into one head/mane mass, the tail grows continuously from the rump, and connected visible legs/paws now make the subject read as one standing lion.

### Animals — recognizable selection subjects

Commit:

```text
51f20f0ae6fbf204a155bdf96962d2330985195c
```

The continuous habitat and all semantic centers remain unchanged. The weak lion/elephant silhouettes were redrawn with unmistakable body cues:

```text
lion      body + mane/head + legs + attached tail
elephant  profile body + oversized ear + attached trunk + tusks + four legs + tail
```

### Gears — actual meshing mechanism

Commits:

```text
bbc3ca209a471202e57adc6630ee79e65da734f0
eab952ea75f6b0d4b67ec27b82ccf27d8bbde39f
```

Three separated wheel-like objects were replaced by a 12-tooth three-gear train. Adjacent tooth envelopes visibly overlap at exactly two mesh boundaries. The teaching overlays now point at those real contact points instead of the obsolete geometry.

---

## 6. Current source-art evidence

The four corrected SVGs were rendered locally at 1024×600 through CairoSVG and inspected as source art.

Static checks:

```text
Home XML parse                         PASS
Animals XML parse                      PASS
Lion XML parse                         PASS
Gears XML parse                        PASS
Home SVG target centers                MATCH page semantic centers
Animals SVG target centers             MATCH page semantic centers
blue↔orange gear tooth overlap         ~11 px
aorange↔green gear tooth overlap       ~10 px
gear mesh geometry                     PASS
```

These are **source/static checks only**.

---

## 7. Important current evidence boundary

The committed runtime PNG pack still represents the rejected E2R SVG state. The edited SVG masters are now newer than these runtime files.

Current truth:

```text
activities/enciclopedia_greia/assets/source/home_discovery_book.svg   UPDATED
activities/enciclopedia_greia/assets/source/animals_field_table.svg   UPDATED
activities/enciclopedia_greia/assets/source/lion_savanna.svg          UPDATED
activities/enciclopedia_greia/assets/source/gears_workbench.svg       UPDATED

corresponding assets/runtime/*.png                                     STALE
```

Consequences:

```text
build_encyclopedia_visual_assets.py --check   expected to fail until runtime rebuild
previous E2R Simulator captures               stale for current source
final-SHA Activity launch acceptance           pending
owner review of final runtime composition      pending
```

Do not call the current source repairs complete/accepted until the runtime pack is regenerated and a fresh final-source Simulator review occurs.

---

## 8. No delegated visual task right now

The rolling file:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

is intentionally a **HOLD** notice. The local agent is not authorized to continue visual-authoring work unless the owner/primary agent explicitly creates a new bounded task.

---

## 9. Narration remains separate

Canonical coordination:

```text
encyclopedia/VOICE_RECORDING_REQUESTS.md
```

The historical ledger checkpoint is 378 REQUESTED rows. Only owner-listened `OWNER_ACCEPTED` clips may enter runtime audio. This visual repair does not generate or integrate narration.

---

## 10. Immediate next step

Continue direct owner/primary-agent inspection of the corrected Home, Animals, Lion and Gears source renders. Make only targeted visual corrections that are evident in the actual pixels.

When the source-art tranche is worth runtime review:

```text
rebuild canonical six-PNG pack
→ build --check
→ focused Encyclopedia tests
→ required local source verification
→ commit/push final runtime assets
→ fresh final-SHA Greia Simulator launch
→ capture only the relevant golden masters
→ owner visual review
```

No E3/E4 migration before explicit owner approval.

---

## 11. Current authorities

```text
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
docs/reviews/visual/2026-08-29_encyclopedia_owner_direct_repairs/REVIEW.md
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md

docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
skills/greia-visual-authoring/SKILL.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
```
