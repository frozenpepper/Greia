# Encyclopedia Golden Masters — Owner-Directed Repair Review

**Status:** ACTIVE SOURCE-ART REPAIR / RUNTIME PNGS STALE / SIMULATOR-UNVERIFIED  
**Date:** 2026-08-29  
**Activity:** `org.greia.enciclopedia`  
**Branch:** `main`

## 1. Why this repair exists

The owner rejected the E2R golden-master package after reviewing the actual Simulator pixels. The technical run was valid, but the visual direction was not acceptable for propagation.

Specific owner findings:

```text
Home      category worlds did not fit naturally inside the illustrated open book
Lion      face/head/mane appeared disconnected and the tail appeared detached
Animals   elephant was not recognizable; the adjacent lion was also visually ambiguous
Gears     wheels did not convincingly read as gears and did not physically mesh
```

This review supersedes any prior suggestion that E2R was aesthetically approved. E3/E4 remain blocked.

## 2. Repair strategy

The owner explicitly requested direct, slow correction by the primary agent rather than another delegated local-agent art pass.

Rules for this tranche:

- preserve the proven Activity/page/input/cache/build architecture;
- fix the exact visible defect before broadening scope;
- render the edited SVG locally at 1024×600 after each meaningful change;
- do not use generated mockups as replacement source art;
- do not migrate another Encyclopedia page;
- do not rebuild/claim runtime acceptance until the source-art tranche is visually ready.

## 3. Changes landed

### Home — book scale/containment

Commit:

```text
46a937616610b3ce8c089ef8a1f0dc835373b36e
```

Changed only the illustrated book geometry/grounding. The six existing portal mini-worlds and their semantic centers/hit geometry were intentionally preserved.

Book spread changed from roughly `x=120..904 / bottom≈488` to `x=78..946 / bottom≈520`, with a correspondingly larger grounding shadow and lower bookmark. The six current portal worlds now sit inside the paper instead of visually spilling beyond its left/bottom page boundaries.

### Lion entry — coherent head/body/tail silhouette

Commits:

```text
a7b8840528118f393aad91bb5b5692d6149799cf
e955d3e3d662d45ff53018a6197a4ed21f659cef
```

Corrections:

- head/face moved into the mane mass rather than reading as a separate face disc;
- muzzle structure added so the face reads as part of the head;
- tail now grows continuously from the rump and ends in one dark tuft;
- body proportions tightened;
- visible connected legs/paws added so the subject reads as a standing lion rather than a floating/slug-like oval.

### Animals section — recognizability first

Commit:

```text
51f20f0ae6fbf204a155bdf96962d2330985195c
```

The continuous habitat composition and semantic centers were preserved. The two weak top-row subjects were redrawn:

- lion: full body, mane/head, legs, attached tail;
- elephant: clear body profile, very large ear, attached curved trunk, tusks, four legs and tail.

The remaining octopus/bee/penguin/frog remain distinct scene subjects at the same semantic centers.

### Gears — mechanically coherent gear train

Commits:

```text
bbc3ca209a471202e57adc6630ee79e65da734f0
eab952ea75f6b0d4b67ec27b82ccf27d8bbde39f
```

The former separated wheel-like objects were replaced with a compact three-gear train:

```text
blue   center=(385,318) approximate outer radius=70
orange center=(500,318) approximate outer radius=56
green  center=(592,318) approximate outer radius=46
```

Each gear now has twelve visible radial teeth. Adjacent outer tooth envelopes overlap by approximately 11 px and 10 px respectively, making the two mesh relationships visually explicit.

The teaching overlays were moved from the obsolete geometry to the real mechanism:

```text
mesh contacts: (450,318), (550,318)
direction arcs: around the three new gear centers
ratio markers: aligned to x=385,500,592
```

There are exactly two contact points for a three-gear linear train; the prior three-contact overlay was incorrect.

## 4. Source-only validation performed

Local 1024×600 CairoSVG renders were inspected for all four corrected screens.

Static checks performed against the edited source candidates:

```text
Home SVG XML parse                   PASS
Animals SVG XML parse                PASS
Lion SVG XML parse                   PASS
Gears SVG XML parse                  PASS
Home data-target centers             MATCH existing semantic centers
Animals data-target centers          MATCH existing semantic centers
Blue↔orange tooth-envelope overlap   ~11 px
Orange↔green tooth-envelope overlap  ~10 px
Gear mesh geometry                   PASS
```

This evidence is **source-art inspection**, not Greia Simulator acceptance.

## 5. Evidence boundary / current blocker

The committed runtime PNG pack still corresponds to the previously rejected E2R SVG state. Therefore after these new SVG edits:

```text
EDITABLE SOURCE MASTERS: UPDATED
COMMITTED RUNTIME PNGS: STALE FOR HOME / ANIMALS / LION / GEARS
build_encyclopedia_visual_assets.py --check: EXPECTED TO FAIL UNTIL REBUILD
FINAL-SHA SIMULATOR EVIDENCE: STALE
OWNER DIRECTION APPROVAL: NOT GRANTED
E3/E4: BLOCKED
```

Do not cite the previous E2R contact sheet as evidence for these source corrections.

## 6. Next visual step

Continue owner-directed inspection/refinement of these exact corrected sources. When the owner/primary agent considers the source-art tranche visually worth testing, rebuild the four changed runtime PNGs through the canonical six-asset build, verify `--check`, run focused tests, then capture fresh Greia Simulator pixels from that final runtime-relevant SHA.

No local-agent visual-authoring task is currently authorized.
