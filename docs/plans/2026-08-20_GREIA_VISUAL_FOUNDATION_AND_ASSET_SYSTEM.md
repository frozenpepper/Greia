# Greia Visual Foundation and Asset System — Active Art Workstream Plan

**Status:** ACTIVE ART WORKSTREAM PLAN  
**Started:** 2026-08-20  
**Owner:** Greia project  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Scope:** Greia visual language, character system, motion vocabulary, reusable art/scene/UI asset library, visual-authoring skills, and staged adoption by Shell/Activities  
**Blocking-platform relationship:** subordinate to `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`; this art workstream does not close, bypass, reorder, or weaken R7/R8/R9/R10/R14 or any accepted ADR gate.

---

## 0. Purpose

Greia needs a visual system that is beautiful **because it is designed around the project’s real production and hardware constraints**, not one that depends on a professional animation department or fragile automated traditional-character rigging.

The accepted direction is:

> **Simple expressive characters + strong faces + whole-body motion + chunky illustrated props + cozy layered scenes + tactile Greia UI.**

This is a constraint-native Greia language, not an imitation of South Park or any other existing property. The useful lesson from economical animation styles is that limits can become a deliberate visual identity.

The repeated detailed-unicorn experiments established useful negative evidence: one-shot AI sprite sheets, automatic detailed quadruped decomposition, and after-the-fact recreation of detailed generated art as articulated vectors are not reliable enough to be Greia’s default visual architecture.

---

# 1. Authority

This file owns **art-workstream sequencing, checkpoints, closure criteria, and append-only art progress history while active**.

It does not replace:

- `AGENTS.md` — repository-wide contributor rules;
- accepted ADRs — architecture/runtime/trust authority;
- `docs/design/GREIA_VISUAL_STYLE_GUIDE.md` — accepted cross-product visual language;
- `docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md` — production-art inventory;
- source/runtime declarations — exact implemented APIs and file contracts;
- the blocking architecture plan;
- `HANDOVER.md` — current continuation/evidence boundary.

Current practical visual-authoring guidance:

```text
skills/greia-visual-authoring/SKILL.md
```

Current non-runtime visual-library seed:

```text
assets/visual/README.md
assets/visual/library_v0.1.toml
```

Accepted character grammar:

```text
docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md
```

Current A2 expression/motion design authority:

```text
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
assets/visual/specimens/a2/base_motion_v0.1.toml
assets/visual/specimens/a2/review.html
```

A candidate expression/motion rule does not become a runtime API merely because it is committed. Runtime-facing animation architecture remains a later reviewed phase.

---

# 2. Multi-session progress protocol

## 2.1 Mutable current checkpoint

This table is the intentionally mutable summary. Keep it short and accurate.

| Field | Current state |
|---|---|
| Active art phase | **A2 — Expression and motion system** |
| Current design direction | approved constraint-native **Puff / Bean / Cutout Critter / Object Friend** character language |
| Working core cast | **Lilli** (unicorn Puff), **Nino** (owl Bean), **Tito** (fox Puff), **Momo** (friendly monster Puff) — approved as static style anchors, not frozen release assets |
| Current motion seed | `idle_bounce`, `blink`, `happy_hop`, `celebrate_pop`, `surprised_wobble`, `sleepy_sway` |
| Current implementation status | A1 grammar is promoted/closed; A2 expression specification, normalized motion seed, static-fallback rules and Puff/Bean/Object Friend review harness are committed; no runtime character-motion API has been added |
| Current evidence | **OWNER REVIEW + DESIGN SPEC + SOURCE + DESKTOP VISUAL REVIEW** for A1; **DESIGN SPEC + SOURCE + DESKTOP VISUAL REVIEW of A2 expression variants/representative keyframes**; no simulator, C0/Acer, Pi or runtime-motion acceptance claimed |
| Current blocker/gate | A2 visual review plus simulator/reference-viewport clarity/performance evidence before A2 closure |
| Next exact step | owner-review `assets/visual/specimens/a2/review.html`; refine expression/motion amplitudes if needed, perform simulator/reference-viewport review without inventing a new runtime engine, then close A2 and begin A3 shared character/Object Friend library expansion |

## 2.2 Append-only ledger rule

Every substantive art/visual session MUST append a dated entry under **§10 Progress ledger**. Do not rewrite older entries to make experiments look cleaner.

Record:

1. phase;
2. files/artifacts changed;
3. decisions;
4. evidence actually obtained;
5. failures/rejected directions worth retaining;
6. next exact action;
7. relevant commit SHA(s).

## 2.3 Resume rule

A later agent resuming visual work must read, in order:

1. `AGENTS.md`;
2. this checkpoint and latest ledger entry;
3. `docs/design/GREIA_VISUAL_STYLE_GUIDE.md`;
4. `docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md`;
5. `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md`;
6. `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`;
7. `skills/greia-visual-authoring/SKILL.md`;
8. the active phase’s specimen/spec files and current asset inventory.

Continue from the first incomplete acceptance item unless the owner explicitly reprioritizes.

## 2.4 Evidence vocabulary

- **DESIGN SPEC** — documented visual rule only;
- **SOURCE** — committed source/assets exist and parse/render as applicable;
- **OWNER REVIEW** — explicit owner disposition of the visual direction/candidate;
- **DESKTOP VISUAL REVIEW** — visually inspected on a development machine;
- **SIMULATOR VISUAL REVIEW** — inspected through Greia Simulator at named viewports;
- **PHYSICAL VISUAL REVIEW** — inspected on named Greia reference hardware;
- **REJECTED EXPERIMENT** — retained lesson, not a candidate asset.

Never turn a browser/SVG/screenshot result into physical Greia acceptance.

---

# 3. Permanent product constraints for this workstream

1. **No assumed art department.** The default pipeline must be viable for maintainers and model-assisted contributors.
2. **C0 matters.** Static SVG/PNG/sprites and cheap bounded transforms are preferred; common charm must not require a heavyweight animation runtime.
3. **Small displays matter.** Important silhouettes/faces/states must survive 800×600 / 1024×600 contexts and intended 64/128/256 character usages.
4. **Offline runtime.** Core visuals never require network generation/CDNs.
5. **Static meaning first.** Animation enriches meaning; it cannot be the only carrier of meaning.
6. **Language-light child UX.** Shape, expression, position, symbol and optional speech/motion communicate before prose where appropriate.
7. **Protected Greia chrome stays protected.** Art does not authorize Activities to replace or imitate system Home/Back.
8. **One coherent world.** Shell, Activities, rewards, profiles and recovery should look related without forbidding Activity-specific themes.
9. **Generation is constrained by grammar/library.** A model should not invent a new art system for every Activity.
10. **Provenance remains required.** Generated/contributed/distributed assets need origin/right/status records.

---

# 4. Working visual foundation

## 4.1 Accepted character archetypes

### Puff

One soft round/oval/fluffy primary mass, large face, zero/two tiny feet, optional stub arms, and a small identity-cue budget. Default for many animals/mascots.

### Bean

One vertical rounded/drop mass, face in upper half, tiny feet, optional wing/flap/arm shapes. Good for owl/bird/helper identities.

### Cutout Critter

Deliberately flat felt/sticker/paper-cut construction with a few large overlapping layers. Flatness is intentional, not missing anatomy.

### Object Friend

The pedagogical object remains the primary silhouette and receives a face/tiny optional appendages. Prefer it when the number/letter/tool/shape itself can carry the role.

## 4.2 Default complexity discipline

Conceptual budget:

```text
1 main body mass
1 face region
0–2 tiny feet
0–2 tiny arms/wings/flaps
0–3 identity attachment groups
```

Avoid default dependence on articulated knees/elbows, front/back quadruped limb rigs, complex neck/torso anatomy, many small fur/hair pieces, or details that only work at large sizes.

## 4.3 Static style anchors

- **Lilli** — unicorn Puff; wonder, kindness, imagination;
- **Nino** — owl Bean; observation, books, thoughtfulness;
- **Tito** — fox Puff; curiosity, exploration, playful cleverness;
- **Momo** — friendly monster Puff; humor, emotion, experimentation.

The 2026-08-20 owner review approved these as **static style anchors / design direction**. This does not freeze the current SVGs as release art or imply runtime/physical acceptance.

## 4.4 Expression vocabulary

```text
neutral
happy
excited
surprised
sleepy
sad_gentle
thinking
proud
silly
```

`blink` is a transient micro-state. Normal educational mistakes must not use anger, shame or disappointed-at-the-child imagery. `sad_gentle` must be reviewed specifically so brow/eye cues cannot read as irritation or accusation.

## 4.5 Base Animation Set v0.1

- `idle_bounce` — nominal 2.0 s living/resting loop;
- `blink` — nominal 0.22 s micro-life cue;
- `happy_hop` — nominal 0.90 s anticipation/squash → hop → settle;
- `celebrate_pop` — nominal 1.15 s bigger pop + bounded FX;
- `surprised_wobble` — nominal 0.72 s recoil/damped wobble;
- `sleepy_sway` — nominal 2.4 s slow sway/compression.

Exact candidate phases/amplitude limits/static fallbacks are owned by `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md` and mirrored as non-runtime design data in `assets/visual/specimens/a2/base_motion_v0.1.toml`.

Candidate v0.2 additions remain `think`, `yes_nod`, `no_wobble`, `look_or_point`, `reward_sparkle`, `enter_pop`, `exit_pop`, `listen`.

Do not proliferate motion names until v0.1 closes A2 across multiple archetypes.

## 4.6 Scene/prop/FX direction

Environment grammar: cozy storybook diorama / felt-board / paper-cut / toy-world layers with a quiet playable center and chunky readable props.

Priority environment families: meadow, forest, workshop, clinic, reading/classroom, night/sky, simple fantasy/castle, water/pond/underwater.

Priority effects: sparkles, stars, hearts, dust/impact puffs, glow rings, sleepy Zs, discovery rays, confetti. Counts/lifetimes must stay bounded.

## 4.7 UI visual direction

Existing Screen/Overlay/Panel/Card/Collection/Control architecture remains authoritative. The visual layer should be rounded, tactile, warm, large, soft-depth, and consistent with the same motion language: lift, press/squash, pop, gentle wobble, pulse, sparkle.

---

# 5. Asset-library direction

Conceptual semantic families:

```text
assets/visual/
  characters/
  expressions/
  animations/
  props/
  environments/
  ui/
  fx/
  specimens/
  library_v0.1.toml
```

This tree is a design/library organization, **not runtime filesystem-discovery authority**.

Asset tiers:

- **Tier A** — carefully reviewed reusable Greia foundations;
- **Tier B** — guided generated/contributed content reviewed before shared use;
- **Tier C** — local/disposable content where style drift cannot undermine system identity/gameplay comprehension.

Asset review states:

```text
concept
candidate
approved
superseded
rejected
```

Presence in Git never means `approved`. `approved` must carry a meaningful scope such as `design_grammar` or `static_style_anchor`; it must not be read as runtime/release/physical acceptance unless explicitly stated.

---

# 6. Rejected/default-nonviable approaches

Retain these lessons unless materially new evidence justifies reopening them:

1. one-shot AI 8×8 sprite sheet assumed to be production animation;
2. automatic detailed traditional quadruped decomposition/rigging as Greia’s default character architecture;
3. programmatic recreation of a detailed generated animal into unrelated full-anatomy vector geometry;
4. raw tutorial/debug Pygame geometry as final represented art;
5. solving visual production by assuming professional artists/animators will appear;
6. random unrelated visual language per generated Activity.

A donated bespoke high-quality asset is not forbidden; the **reusable default architecture** simply cannot depend on it.

---

# 7. Phased work plan

## A0 — Workstream foundation **[COMPLETE — DESIGN SPEC/SOURCE]**

- [x] active art plan + multi-session protocol;
- [x] `AGENTS.md` registration;
- [x] `skills/greia-visual-authoring/SKILL.md`;
- [x] `assets/visual/README.md` and non-runtime inventory seed;
- [x] HANDOVER/documentation authority registration;
- [x] coherent work committed to `main`.

## A1 — Canonical style grammar and archetype specimens **[COMPLETE — OWNER-REVIEWED DESIGN/STATIC SCOPE]**

- [x] promote accepted constraint-native character direction into `GREIA_VISUAL_STYLE_GUIDE.md`;
- [x] define Puff/Bean/Cutout Critter/Object Friend construction grammar;
- [x] define outline/shadow/fill/detail/color disciplines;
- [x] create 256/128/64 static comparison review source;
- [x] define economical versus placeholder failure patterns;
- [x] owner visual review of Lilli/Nino/Tito/Momo;
- [x] approve static style-anchor scope and promote accepted rules.

Accepted grammar:

```text
docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md
```

A1 review:

```text
assets/visual/specimens/a1/review.html
```

A1 closure is a design/static-style decision only; release/runtime/physical character acceptance remains later work.

## A2 — Expression and motion system **[ACTIVE]**

- [x] expression specification and face-state templates;
- [x] normalized timing/phase/easing for Base Animation Set v0.1;
- [x] demonstrate all six base motions on Puff, Bean and Object Friend in a non-runtime review harness;
- [x] define static fallbacks;
- [x] inspect existing `src/greia_platform/ui_motion.py` seam; no parallel animation framework added;
- [ ] owner visual review/refinement of A2 expression/motion harness;
- [ ] simulator/reference-viewport clarity and appropriate performance evidence before closure.

A2 sources:

```text
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
assets/visual/specimens/a2/base_motion_v0.1.toml
assets/visual/specimens/a2/review.html
```

## A3 — Starter character and Object Friend library

- [ ] canonical/reusable Lilli/Nino/Tito/Momo package assets after A2 state/motion requirements settle;
- [ ] 8–12 reusable standard creatures;
- [ ] 10–15 Object Friends;
- [ ] explicit metadata/provenance;
- [ ] appropriate vector masters and/or deterministic 64/128/256 derivatives.

## A4 — Props, environments and FX

- [ ] first meadow/forest/workshop/clinic scene families;
- [ ] 20–30 initial reusable props;
- [ ] common FX pack;
- [ ] layered scene/safe-playfield guidance;
- [ ] low-resolution scene review.

## A5 — UI visual component language

- [ ] reusable visual variants for buttons/cards/panels/trays/progress/bubbles;
- [ ] hover/focus/press/selected/new/completed/locked/error treatment;
- [ ] icon/depth sizing rules;
- [ ] loading/error/recovery illustration system;
- [ ] shared motion mapping;
- [ ] 800×600 and 1024×600 reference compositions.

## A6 — Model authoring/validation pack

- [ ] mature visual-authoring skill with approved examples/rejection criteria;
- [ ] Activity skill points to/reuses visual skill;
- [ ] lightweight deterministic validation only for objective contracts, never fake subjective beauty scoring;
- [ ] test the authoring instructions with weaker and stronger models.

## A7 — Platform/library integration

Prerequisite: source/architecture review of runtime-facing asset/motion APIs.

- [ ] explicit catalogue/loader contract if needed;
- [ ] bounded caching/no per-frame decode or I/O;
- [ ] Python/Pygame helpers only through accepted platform seams;
- [ ] future Web runtime uses the same semantic art system;
- [ ] fallback/package composition;
- [ ] simulator preview tooling if useful.

## A8 — First-party Shell/Activity refit and acceptance

- [ ] inventory prototype-art debt;
- [ ] refit in small reviewable tranches;
- [ ] preserve gameplay/input/storage/localization behavior;
- [ ] simulator review at named viewports;
- [ ] physical Acer/Pi review where runtime/performance claims require it;
- [ ] retire superseded provisional assets intentionally.

---

# 8. Quality gates

## Character

- silhouette recognizable at intended 64/128/256 uses;
- face clear and expression distinguishable;
- no unnecessary anatomy/attachments;
- color/outline/detail coherent with Greia;
- neutral static pose works;
- motion should not require anatomy that the style intentionally removed.

## Expression/motion

- semantic state readable across Puff, Bean and Object Friend;
- `sad_gentle`/wrong-choice feedback does not read as anger/shame/disappointment;
- static fallback preserves meaning;
- amplitude remains bounded and appropriate to the archetype;
- Object Friend deformation preserves pedagogical recognition;
- no anatomy-specific rig or parallel runtime framework introduced merely for motion.

## Scene

- gameplay entities separate from decoration;
- background supports rather than overwhelms play;
- no accidental giant dead areas;
- represented props are intentional art, not leftover debug geometry;
- protected system-safe region clear;
- 800×600 / 1024×600 readable.

## UI

- large child targets;
- states readable by shape/depth/icon/position, not color alone;
- Greia typography roles;
- protected system controls unmistakable;
- effects bounded/cheap.

## Runtime/performance

- no per-frame asset decode/filesystem work;
- caches, particles and transient animation state bounded;
- static fallback path;
- no heavyweight character runtime required on C0 merely for common mascots;
- no physical-hardware claim without physical evidence.

---

# 9. Workstream completion

This workstream becomes COMPLETE only when:

- living design authorities contain the accepted visual language;
- model authoring guidance has been exercised;
- meaningful reusable character/prop/environment/FX/UI foundations exist with provenance;
- semantic expression/motion is consumable through accepted bounded architecture;
- multiple actual Greia surfaces demonstrate the system;
- desktop/simulator reference-viewport review is recorded;
- physical low-resource review covers claims that require it;
- HANDOVER identifies stable extension points and remaining limitations.

When complete or explicitly replaced by the owner, preserve this plan as history and remove/update its active references from `AGENTS.md`/HANDOVER.

---

# 10. Progress ledger — append only

## 2026-08-20 — A0 started: constraint-native visual pivot

**Phase:** A0 — Workstream foundation  
**Evidence:** DESIGN SPEC / prior REJECTED EXPERIMENTS

### Decisions

- Detailed traditionally articulated animals are not the default Greia architecture.
- Adopt Puff, Bean, Cutout Critter and Object Friend as the initial constrained archetypes.
- Make face/expression and whole-body motion the primary animation tools.
- Use scene composition, props, tactile UI and small FX for richness.
- Adopt the working names Lilli, Nino, Tito and Momo.
- Seed Base Animation Set v0.1 with idle bounce, blink, happy hop, celebrate pop, surprised wobble and sleepy sway.
- Use a mutable checkpoint plus append-only ledger for multi-session persistence.

### Lessons retained

- Attractive single images do not imply reliable generated sprite sheets.
- Detailed articulated decomposition is materially harder than coherent simple character construction.
- Technically valid rig mechanics can still produce unacceptable art.
- Greia needs reproducible charm, not a weak imitation of studio animation.

### Next action

Complete A0 repository wiring, then begin A1 static grammar/specimens.

### Commit

- initial plan: `f05dda2d5e7f4dddb4f49eadfb971667591d0ec6`

## 2026-08-20 — A0 repository wiring complete; A1 activated

**Phase:** A0 closure → A1 start  
**Evidence:** DESIGN SPEC / SOURCE

### Established

- active plan;
- visual-authoring skill;
- visual-library README/inventory;
- AGENTS/documentation/HANDOVER registration.

### Boundary

- architecture-remediation remains the blocking plan;
- `runtime_consumed = false` on the visual design seed;
- no release art, simulator or physical visual acceptance claimed.

### Commits

- plan: `f05dda2d5e7f4dddb4f49eadfb971667591d0ec6`
- visual skill: `33e8067b4c5f7b7e5151f7473e30173f36ff9216`
- asset README: `be8f0f788c29b803c2361ec64983565e9243bae7`
- library seed: `df746e025cc01ebaff45ae6f314767194590e954`
- AGENTS: `dc41f82e6eeb16e1729d68088f8c59d509d63aba`
- documentation map: `cd6a3fdd6104aceb722f281767396a6627073ffb`
- HANDOVER: `7c3443d04900f38109db197a7a9dabbdb34605b8`
- A0 closure/A1 activation: `3ae3007a6b8631d091b4f983f0847b04a80dfd57`

## 2026-08-20 — A1 candidate grammar and static cast specimens

**Phase:** A1 — Canonical style grammar and archetype specimens  
**Evidence:** DESIGN SPEC / SOURCE / DESKTOP VISUAL REVIEW

### Files/artifacts

- `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md` — candidate numeric/visual construction grammar;
- `assets/visual/specimens/a1/lilli.svg`;
- `assets/visual/specimens/a1/nino.svg`;
- `assets/visual/specimens/a1/tito.svg`;
- `assets/visual/specimens/a1/momo.svg`;
- `assets/visual/specimens/a1/cutout_critter.svg`;
- `assets/visual/specimens/a1/object_friend_3.svg`;
- `assets/visual/specimens/a1/review.html` — 256/128/64 comparison;
- `assets/visual/library_v0.1.toml` updated to `0.1.1` and candidate specimen/status references.

### Candidate design rules exercised

- 256×256 reusable-character review artboard;
- one dominant body mass;
- large face region;
- roughly 3–4 px tinted outer contour / 2–3 px secondary contour at 256;
- broad flat/two-stop fill treatment rather than detailed fur/3D painting;
- restrained identity-cue and interior-detail budgets;
- species recognition through horn/ears/tuft, mask/beak/wings, ears/tail/muzzle, antennae/fluff rather than full anatomy;
- explicit distinction between intentionally economical design and placeholder/debug primitives.

### Desktop review

The six SVG specimens were locally rasterized and visually inspected at 256, 128 and 64 px. The four named characters remained recognizably distinct at the tested sizes. This is **desktop visual review only**; it is not owner approval, simulator acceptance or physical/C0 evidence.

A CSS-authoring error in the first local render (`{{ ... }}` instead of valid `{ ... }` style blocks) temporarily suppressed intended outline styling. It was caught during visual inspection, fixed, re-rendered and the corrected SVG source was committed. Preserve this as a reminder that “it renders” must include inspection of the intended visual treatment, not merely successful SVG parsing.

### Commit

- A1 grammar/specimen source: `b3cf90c109eae14b2013ad62f69c64dccaa12e8a`

### Gate / next exact action

Owner reviews `assets/visual/specimens/a1/review.html` and the four static cast candidates. Record which are approved, revised/superseded or rejected. Do **not** close A1 or implement the shared runtime motion layer before that review. After acceptance, reconcile the accepted grammar into `GREIA_VISUAL_STYLE_GUIDE.md`, update library statuses, close A1, and begin A2.

## 2026-08-20 — A1 owner-approved; grammar promoted; A2 expression/motion harness started

**Phase:** A1 closure → A2 active  
**Evidence:** OWNER REVIEW / DESIGN SPEC / SOURCE / DESKTOP VISUAL REVIEW

### Owner disposition

After reviewing the A1 direction, the owner explicitly asked to move forward. This is recorded as approval of:

- the constraint-native Puff/Bean/Cutout Critter/Object Friend architecture;
- Lilli/Nino/Tito/Momo as **static style anchors**;
- the A1 construction grammar as the default visual direction.

The scope is deliberately bounded. This is not a claim that the current SVGs are final release art, runtime-ready packages, or physically accepted on Greia hardware.

### A1 promotion work

- `docs/design/GREIA_VISUAL_STYLE_GUIDE.md` now contains the accepted constraint-native character language;
- `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md` is now accepted rather than candidate;
- `assets/visual/library_v0.1.toml` is `0.1.2` and records explicit `approval_scope` values while retaining `runtime_consumed = false`;
- the visual-authoring skill now treats the grammar/static anchors as accepted design guidance.

### A2 work started

Added:

- `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`;
- `assets/visual/specimens/a2/base_motion_v0.1.toml`;
- `assets/visual/specimens/a2/review.html`;
- `assets/visual/specimens/a2/README.md`.

A2 defines nine semantic persistent expressions plus transient blink, normalized Base Animation Set v0.1 timing/phases/amplitude limits, static fallbacks and archetype mapping. The review harness demonstrates the six motions on Lilli/Puff, Nino/Bean and an Object Friend without anatomical rigs.

### Desktop review / correction

Local expression variants and representative motion keyframes were rendered and visually inspected. One useful failure was caught: an early Lilli `sad_gentle` brow treatment could read as irritation/disappointment. It was revised to a softer eye/mouth treatment. Preserve this lesson in future model guidance: gentle sadness/wrong-choice feedback must never look angry at the child.

Object Friend rotation/squash was deliberately reduced relative to Puff/Bean so the pedagogical glyph silhouette remains legible.

### Runtime seam review

`src/greia_platform/ui_motion.py` was inspected. Its immutable renderer-neutral mathematical sampling is the preferred architectural precedent, but its present `MotionSample` is UI-control-oriented and lacks character rotation, anisotropic squash/stretch, face state and optional attachment/FX channels.

No runtime extension was made in A2. The design harness is not runtime authority, and no parallel animation framework was introduced.

### Commits

- A2 expression/motion spec: `7a6a741f9bdc5f14157063833af4b55d152ba16f`
- A2 motion design seed: `12bb4d71b7a046fa6b1e7d1528197d95b1340ec4`
- A2 README: `006516af4c0a9aef933da87ee77c7b80dbc32347`
- A2 review harness: `a6871f814105724615c14c09032dbae16088afdf`
- visual-style promotion: `48f935b328f75b3b1dcda09a93f5d51f8e0e39a9`
- accepted A1 grammar: `82832e2a3f5087e4da20d5fd38abe48b456af53d`
- library approval scopes/A2 set: `e15b45e43651e0c91dfc89def07618b9c3618119`
- visual-authoring skill update: `55cab9339fc5776da4b3b03fa4a0bbad9e5fa824`

### Next exact action

Review/refine the A2 expressions and motion feel using `assets/visual/specimens/a2/review.html`, obtain reference-viewport/simulator evidence appropriate to a design harness, and close A2 only if semantic motion remains charming/readable across Puff, Bean and Object Friend. Runtime animation integration remains deferred to the architecture-reviewed A7 seam.
