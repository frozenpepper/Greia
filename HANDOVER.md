# Greia — Current Engineering Handover

**Updated:** 2026-08-29
**Canonical repository:** `frozenpepper/Greia`
**Canonical branch:** `main`
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**
**Current parallel visual focus:** **Encyclopedia E3 six-section source reauthoring after owner approval of corrected golden-master direction**
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

For R7 display/session/input work also read:

```text
docs/reviews/2026-08-29_R7_ACTIVITY_BACKEND_INDEPENDENCE_AND_DISPLAY_SESSION_REVIEW.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
```

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

R7 remains the first incomplete blocking platform phase. Current production still uses the provisional Xorg/xinit compatibility path while the final appliance display/session/input implementation is resolved.

The 2026-08-29 R7 review clarified the execution architecture without closing any R7 gate:

- Activity rendering is backend-independent by invariant. Ordinary Pygame/SDL drawing is valid; Activities must not know/select/probe X11, Wayland, DRM/KMS, evdev/libinput or backend-specific environment.
- Do **not** invent a Greia drawing API. SDL/Pygame remains the renderer abstraction.
- `src/greia_launcher/display_session.py` is the existing polymorphic runtime seam. Complete `DisplaySessionCoordinator` / `DisplaySessionBackend`; do not create a parallel giant HAL.
- `LegacyXDisplaySessionBackend` is the first/reference compatibility implementation. A Wayland implementation may later sit behind the same contract and must require zero Activity changes.
- The major current Activity drift is not widespread direct Xlib usage; it is cooperative trust: first-party Activities/shared canvas helpers still draw and hit-test the nominally trusted Home chrome inside the Activity process.
- R7 implementation must first enforce backend independence, then implement real trusted chrome/input above Activities, then migrate first-party Activities by shared pattern before comparing Xorg and Wayland on physical hardware.
- **Backend independence must not create an abstraction tax.** Existing low-resource optimization strategies remain valid and must survive the migration: precomposed opaque backdrops, converted surfaces, bounded caches, cached transforms, dirty/invalidation rendering, adaptive pacing and direct high-rate SDL pointer/text handling where safe.
- Backend-specific fast paths are allowed and expected below the common contract. Portable semantics do not require identical backend internals.

R7 invariants remain:

- Greia owns display/session authority;
- protected Home/Back remain outside Activity rendering/input authority;
- protected system input is intercepted before Activity delivery;
- controller discovery/normalization is platform-owned;
- ordinary Activities do not gain raw `/dev/input` or DRM authority;
- backend selection is trusted platform/profile composition, never Activity logic;
- normal Activity pixels must not be proxied through a generic Python framebuffer/IPC layer merely for abstraction;
- trusted chrome must remain bounded/event-driven and must not impose a permanent full-screen composition/redraw cost;
- accepted Activity optimization opportunities must remain available on every production backend;
- any backend migration requires exact source, VM/simulator where applicable, and physical reference-device evidence including performance evidence.

Current detailed R7 execution review:

```text
docs/reviews/2026-08-29_R7_ACTIVITY_BACKEND_INDEPENDENCE_AND_DISPLAY_SESSION_REVIEW.md
```

Activity, visual, voice, launcher, microphone and Encyclopedia work do **not** close or reorder R7.

Primary phase authority remains:

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

### Golden-master direction owner-approved after direct repair

The original Encyclopedia graphics and the first E2R golden-master package were rejected aesthetically despite valid technical evidence.

The primary agent then repaired the actual source assets directly at owner request:

```text
Home      enlarged book + complete 3x2 portal block centered at x=267/512/757
          with the middle column intentionally straddling the book spine
Animals   recognizable full-body lion + clear elephant profile/trunk/ear/tusks
Lion      unified face/head/mane, attached tail, connected visible legs
Gears     unmistakably toothed gears in a real meshing train + corrected reveal contacts
```

After inspecting these source corrections, the owner explicitly approved proceeding with the plan.

Current gate:

```text
E1 VISUAL/ASSET ARCHITECTURE:        COMPLETE
E2/E2R VISUAL DIRECTION:             OWNER APPROVED
LATEST CORRECTED RUNTIME PNGS:       REBUILD PENDING
LATEST EXACT-SOURCE SIMULATOR PROOF: PENDING
E3 SECTION-PAGE REAUTHORING:         ACTIVE
E4 FACTUAL-ENTRY MIGRATION:          BLOCKED UNTIL E3 REVIEW
```

The old E2R runtime PNGs/screenshots predate the latest Home/Animals/Lion/Gears source corrections and are stale for exact-current-source claims.

### E3 six-section source family

Animals remains the section-world reference. Five new authored section masters are now on `main`:

```text
space_gallery_observatory.svg
earth_gallery_landscape.svg
body_gallery_discovery_room.svg
machines_gallery_workbench.svg
history_gallery_time_trail.svg
```

Source direction:

```text
Animals          continuous habitat
Space            observatory around the existing live orbiting Solar System
Earth & Nature   one layered landscape with rain/tree/rainbow/volcano/ocean
Body             one discovery room with physical anatomy exhibits
Machines         one workshop with recognizable gears/magnet/bicycle/plane/bridge
History          one time/excavation trail with T-rex/fossil/mammoth/cave/pyramid
```

The first source contact review caught and corrected panel-like Body stations, weak Machines gear/bridge silhouettes and an ambiguous History dinosaur before persistence.

Source-review authority:

```text
docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/SOURCE_REVIEW.md
```

The five section pages are source-wired through the existing bounded `VisualLibrary`. Missing E3 generated PNGs deliberately fall back to the prior procedural scene. Space preserves its live orbital teaching model regardless of backdrop.

Build groups now exist for `golden`, `sections`, or `all`. The source contract forbids a partial E3 runtime pack: section art may be 0/5 during staged source work or 5/5 when generated.

Current Encyclopedia continuation authority:

```text
encyclopedia/HANDOVER.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/SOURCE_REVIEW.md
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
```

No local-agent visual-authoring task is currently authorized; the owner asked the primary agent to perform this work directly.

### Narration

Narration remains separate from graphics acceptance.

Canonical coordination:

```text
encyclopedia/VOICE_RECORDING_REQUESTS.md
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

### Blocking platform lane — R7

Resume with the R7.1 tranche defined in:

```text
docs/reviews/2026-08-29_R7_ACTIVITY_BACKEND_INDEPENDENCE_AND_DISPLAY_SESSION_REVIEW.md
```

Exact next sequence remains owned by that review/active architecture plan. Do not let the visual lane reorder R7.

### Current Encyclopedia visual lane

Do **not** begin E4.

Next exact visual gate:

```text
build corrected six golden-master PNGs + five E3 section PNGs
→ verify all 11 current SVG/PNG renditions
→ focused Encyclopedia tests + required repository verification
→ commit/push the complete current runtime-art state
→ fresh exact-SHA real Greia Simulator
→ review Home + all six section pages as one family
→ if accepted, close E3 and unblock E4
```

`docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md` remains HOLD unless the owner explicitly changes the direct-work instruction.

---

## 8. Non-negotiable continuation reminders

- `main` is canonical unless the owner changes branch policy;
- GitHub is canonical persistence;
- no unauthorized hosted Actions execution/inspection;
- Activity `main.py` stays a bootstrap/composition boundary;
- Activities are display-backend independent; backend plumbing terminates in trusted Greia composition/adapters;
- Activities never implement the real Home/Back or own physical controller/device authority;
- performance is a correctness contract on the Acer floor, not a secondary optimization pass;
- backend abstraction must preserve accepted Activity optimization strategies and allow backend-private fast paths;
- do not add generic pixel proxying, avoidable full-frame copies, continuous chrome redraw/composition or high-rate input IPC merely for architectural symmetry;
- multiple physical inputs converge on semantic/domain actions;
- child-facing flows remain offline-first and pre-reader friendly;
- no runtime AI/TTS/speech recognition merely to fill content gaps;
- all new prerecorded speech production goes through the Greia Voice Production Engine;
- visual/runtime/Activity caches stay bounded with explicit invalidation;
- performance claims require measurement on the claimed execution scope;
- **simplified graphics means low production/runtime complexity, not crude final art**;
- R7 remains open until its own evidence/closure criteria are satisfied.
