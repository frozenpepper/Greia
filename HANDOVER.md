# Greia — Current Engineering Handover

**Updated:** 2026-08-29
**Canonical repository:** `frozenpepper/Greia`
**Canonical branch:** `main`
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**
**Current parallel visual focus:** **Encyclopedia owner-directed golden-master source repair after E2R rejection**
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

### E2R visuals rejected; direct correction active

The original Encyclopedia graphics were rejected, and the later E2R golden-master package was also rejected by the owner after review of the actual Simulator pixels.

The E2R technical evidence remains valid for its exact SHA, but **it is not visual approval**.

Owner-identified E2R failures:

```text
Home      — six category worlds did not fit naturally inside the illustrated book
Lion      — face/head/mane looked disconnected and the tail looked detached
Animals   — elephant was not recognizable; adjacent lion was also ambiguous
Gears     — wheels did not convincingly look like gears and did not physically mesh
```

Current direct repair record:

```text
docs/reviews/visual/2026-08-29_encyclopedia_owner_direct_repairs/REVIEW.md
```

Current source repairs on `main` include:

```text
Home      enlarged book spread while preserving portal artwork/centers
Animals   recognizable full-body lion + clear elephant profile/trunk/ear/tusks
Lion      unified head/mane/face, attached tail, visible connected legs
Gears     three 12-tooth gears in a real meshing train + corrected reveal geometry
```

The previous six runtime PNGs have **not** yet been rebuilt after these source edits. Therefore:

```text
EDITABLE SVG MASTERS:                    UPDATED FOR HOME/ANIMALS/LION/GEARS
COMMITTED RUNTIME PNG PACK:              STALE FOR THOSE FOUR SCENES
build --check:                           EXPECTED TO FAIL UNTIL REBUILD
PREVIOUS E2R SIMULATOR SCREENSHOTS:      STALE FOR CURRENT SOURCE
OWNER VISUAL DIRECTION APPROVAL:         NOT GRANTED
E3 / E4:                                 BLOCKED
```

Source-art rendering/inspection has been performed locally at 1024×600 for the four corrected scenes. Home/Animals semantic target centers remain unchanged, and the new gear tooth envelopes visibly overlap at their two real mesh boundaries.

No local-agent art task is currently authorized. The rolling task file is intentionally a HOLD notice:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

Current Encyclopedia continuation authority:

```text
encyclopedia/HANDOVER.md
docs/reviews/visual/2026-08-29_encyclopedia_owner_direct_repairs/REVIEW.md
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
```

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

Exact next sequence:

1. add/enforce the Activity backend-independence validator and contributor contract;
2. run a repository-wide first-party Activity scan and classify backend/trusted-chrome/raw-input findings;
3. capture physical performance baselines for Writing, Painting, one dirty-render/static Activity, one animated Activity, launch/return and idle before changing those paths;
4. harden the existing `DisplaySessionBackend` seam with Legacy X as the reference implementation, moving generic-launcher X-specific behavior behind it **without adding frame proxying/copies or high-rate input IPC**;
5. implement trusted system chrome/input for the current Xorg session through the existing `SystemChromeCoordinator` boundary, keeping it bounded/event-driven rather than a continuous full-screen compositing cost;
6. migrate Writing/Painting first, then reference-canvas exemplars, then capability-rich Activities, then the remaining catalogue, preserving each Activity's accepted performance optimizations;
7. only after the contract and baseline performance are proven on Legacy X, implement/prototype Wayland behind the same contract and compare on real Acer/Pi hardware.

Do not begin by replacing Xorg. First make the rest of Greia genuinely independent of it, and do not trade away measured performance merely to make the abstraction look cleaner.

### Current Encyclopedia visual lane

Continue **direct owner/primary-agent source-art repair** of the rejected golden masters. Do not delegate another visual-authoring pass and do not start E3/E4.

Current sequence:

```text
inspect corrected Home / Animals / Lion / Gears source renders
→ make only obvious targeted corrections
→ when source art is worth runtime review, rebuild canonical PNG pack
→ build --check
→ focused tests / required local verification
→ fresh final-SHA real Greia Simulator capture
→ owner review
```

No broad 43-page visual recapture before the corrected golden-master direction is explicitly accepted.

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
