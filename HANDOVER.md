# Greia — Current Engineering Handover

**Updated:** 2026-08-28  
**Canonical repository:** `frozenpepper/Greia`  
**Canonical branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Current parallel visual focus:** **Encyclopedia golden-master runtime validation / owner visual gate**  
**Purpose:** short current continuation contract. Detailed chronology belongs in active plans and dated reviews/handovers.

Historical long-form root state remains preserved under:

```text
docs/handovers/GREIA_ROOT_HANDOVER_ARCHIVE_2026-08-27.md
```

and in Git history / dated reviews.

---

## 1. Resume rules

Before substantive work, read:

```text
AGENTS.md
README.md
docs/DOCUMENTATION.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
HANDOVER.md
```

Then load the relevant OS/Activity/visual/voice skill.

For visual work also read:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
```

Work on current `main`, refresh before writes, preserve concurrent work, and do not use GitHub-hosted Actions unless the owner explicitly authorizes that execution.

No PASS claim may be generalized beyond the exact source/evidence lane that actually executed.

---

## 2. Platform state

R7 remains the first incomplete blocking platform phase. Current production still uses the provisional Xorg/xinit compatibility path while direct appliance display/session/input ownership is resolved.

R7 invariants remain:

- Greia owns display/session authority;
- protected Home/Back remain outside Activity rendering/input authority;
- protected system input is intercepted before Activity delivery;
- controller discovery/normalization is platform-owned;
- ordinary Activities do not gain raw `/dev/input` or DRM authority;
- any direct/compositor migration requires its own exact source, VM and physical legacy-x86 evidence.

Activity, visual, voice, launcher, microphone and Encyclopedia work do **not** close or reorder R7.

Authority:

```text
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
```

The first-generation Acer Aspire One remains the low-resource floor. Physical evidence applies only to the exact source state measured.

---

## 3. Visual workstream

Stable architecture:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
```

Active art plan:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
```

Current resume:

```text
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
```

Existing accepted visual/runtime foundations remain valid: semantic visual catalogues, build-time PNG renditions, bounded Pygame cache, scene composition runtime, shared UI, canonical six-character cast, and previously owner-reviewed Activity productization work.

The current visual lesson is that mechanically complete Activities may still fail the product quality bar. Final real-world subjects must not default to crude programmer-drawn primitives merely because they are fast and deterministic.

---

## 4. Greia Encyclopedia v0.1 — current parallel Activity workstream

Activity:

```text
activities/enciclopedia_greia/
org.greia.enciclopedia
```

Frozen runtime scope remains:

```text
1 Home
6 section pages
36 factual entries
43 executable pages total
```

### Mechanical/runtime foundation already proven

Prior owner-machine evidence established:

```text
source gate                                  PASS at prior verified SHA
real Shell -> Encyclopedia lifecycle         PASS
43 / 43 page reachability                    PASS
36 / 36 entry semantic ACTIVATE delivery     PASS
36 / 36 Encyclopedia internal Back returns  PASS
protected Greia Home -> Shell                PASS
```

The headless traversal's generic page-transition capture race has since been repaired on `main`; preserve that fix.

### Graphics correction and E1/E2 source status

The owner rejected the old Encyclopedia graphics quality as a product target. The forensic diagnosis remains that the old visual layer relied too heavily on raw Pygame primitives, sparse flat environments, instrumentation-like discovery bubbles, corner-stamped presenters and weak visual payoff.

Authoritative forensic review:

```text
docs/reviews/2026-08-28_ENCYCLOPEDIA_GRAPHICS_FORENSIC_AUDIT.md
```

Active visual reauthoring subplan:

```text
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
```

The first bounded E1/E2 source tranche is now on `main`:

```text
activities/enciclopedia_greia/enciclopedia_presentation.py
activities/enciclopedia_greia/enciclopedia_services.py
activities/enciclopedia_greia/assets/source/*.svg   # six golden-master masters
Home / Animals / Lion / Saturn / Gears / Pyramids page integrations
tools/build_encyclopedia_visual_assets.py
tests/test_activity_enciclopedia_visual_foundation.py
```

The build tool now supports:

```bash
python3 tools/build_encyclopedia_visual_assets.py
python3 tools/build_encyclopedia_visual_assets.py --check
```

`--check` rebuilds the six masters temporarily and byte-compares them against the committed runtime PNG pack, preventing stale generated art from silently passing.

Current truthful visual state:

```text
E1 SHARED PRESENTATION SOURCE: IMPLEMENTED ON MAIN
E2 SIX GOLDEN-MASTER PAGE SOURCES: IMPLEMENTED ON MAIN
EDITABLE SVG MASTERS: 6 / 6 ON MAIN
SOURCE CONTRACTS: IMPLEMENTED; local mirror checks passed where recorded
RUNTIME PNG PACK: BUILD / COMMIT PENDING ON OWNER-MACHINE CHECKOUT
FINAL-SHA SIMULATOR GATE: PENDING
OWNER VISUAL DIRECTION APPROVAL: PENDING
E3 / E4 BULK MIGRATION: BLOCKED
```

The Activity fails soft to its previous procedural scenes when the generated runtime art is absent, so current `main` remains mechanically usable. That fallback does **not** count as golden-master visual evidence.

Current Encyclopedia continuation authority:

```text
encyclopedia/HANDOVER.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

### Narration

Narration remains separate from graphics acceptance.

Canonical coordination:

```text
encyclopedia/VOICE_RECORDING_REQUESTS.md
```

Current ledger checkpoint:

```text
378 rows
378 REQUESTED
```

Only owner-listened `OWNER_ACCEPTED` clips may be integrated. No runtime TTS is allowed.

---

## 5. Greia Voice Production Engine

Canonical authoring-time voice subsystem:

```text
tools/greia_voice.py
tools/greia_voice_core/
skills/greia-voice-production/SKILL.md
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
```

Important boundaries:

- authoring-time only;
- canonical characters routed through the Voice Engine rather than Activity-owned backend code;
- deterministic pedagogical/Dani system paths remain provider-controlled by the engine;
- optional Whisper verification is advisory and cannot owner-accept audio;
- one warm model/service path and cross-process lock prevent duplicate inference workers;
- every new recording still requires human listening acceptance.

Owner workstation Apple-Silicon setup/doctor and narrow smoke generation have succeeded. Shared character reaction/introduction library v0.2 has 192 owner-accepted clips; historical v0.1 is retained as retired evidence. Exact voice history/evidence remains in dated docs and Git history.

Do not introduce `tools/greia_voice.py`, Whisper or any voice model into child runtime.

---

## 6. Parent / microphone / updates

The external Parent client remains source-pinned/integrity-checked. Production pairing/encrypted transport remains separate from provisional development transport.

Runtime microphone cleanup remains platform-owned and lightweight by default; advanced processing requires explicit parent opt-in and real availability.

Build-time prerecorded voice production and child microphone capture are separate systems.

Current x86 update architecture remains provisional single-root; signed-update foundations do not authorize unsafe active-root mutation.

---

## 7. Immediate next work

### Current Encyclopedia visual lane

Do **not** implement more Encyclopedia pages yet. Execute the existing golden-master validation gate:

```text
refresh clean main
→ build six runtime PNGs
→ run build tool --check
→ focused Encyclopedia tests + required local source verification
→ commit/push the generated PNG pack
→ record exact final SHA
→ real Greia Simulator launch/survival on that SHA
→ capture Home / Animals / Lion / Saturn / Gears / Pyramids at 1024×600
→ capture representative ACTIVATE payoffs
→ capture one compact + one larger responsive sample
→ perform no-reading prototype review
→ produce one curated contact sheet
→ STOP for owner visual direction approval
```

Exact local execution contract:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

Do not run the broad 43-page visual recapture and do not enter E3/E4 until the owner explicitly accepts the golden-master direction.

### Blocking platform lane

R7 remains open and may continue independently from the first incomplete gate in the active architecture plan.

---

## 8. Non-negotiable continuation reminders

- `main` is canonical unless the owner changes branch policy;
- GitHub is canonical persistence;
- no unauthorized hosted Actions execution/inspection;
- Activity `main.py` stays a bootstrap/composition boundary;
- multiple physical inputs converge on semantic/domain actions;
- child-facing flows remain offline-first and pre-reader friendly;
- no runtime AI/TTS/speech recognition merely to fill content gaps;
- all new prerecorded speech production goes through the Greia Voice Production Engine;
- visual/runtime/Activity caches stay bounded with explicit invalidation;
- performance claims require measurement on the claimed execution scope;
- **simplified graphics means low production/runtime complexity, not crude final art**;
- R7 remains open until its own evidence/closure criteria are satisfied.
