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

The accepted working direction is:

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

Current A1 candidate character grammar:

```text
docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md
```

A candidate rule does not become canonical merely because it is committed. Owner review and promotion into the living visual style guide remain explicit gates.

---

# 2. Multi-session progress protocol

## 2.1 Mutable current checkpoint

This table is the intentionally mutable summary. Keep it short and accurate.

| Field | Current state |
|---|---|
| Active art phase | **A1 — Canonical style grammar and archetype specimens** |
| Current design direction | constraint-native **Puff / Bean / Cutout Critter / Object Friend** language |
| Working core cast | **Lilli** (unicorn Puff), **Nino** (owl Bean), **Tito** (fox Puff), **Momo** (friendly monster Puff) |
| Current motion seed | `idle_bounce`, `blink`, `happy_hop`, `celebrate_pop`, `surprised_wobble`, `sleepy_sway` |
| Current implementation status | A1 candidate grammar plus first static SVG specimens are committed; visual library points to them as `candidate`, not approved runtime assets |
| Current evidence | **DESIGN SPEC + SOURCE + DESKTOP VISUAL REVIEW** at 256/128/64; no simulator, C0/Acer, Pi or release-art acceptance claimed |
| Current blocker/gate | **owner visual review of Lilli/Nino/Tito/Momo** before the candidate grammar is promoted and A1 closes |
| Next exact step | inspect `assets/visual/specimens/a1/review.html`; revise/approve/reject the four cast candidates, then promote accepted grammar into `GREIA_VISUAL_STYLE_GUIDE.md` and proceed to A2 |

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
5. `skills/greia-visual-authoring/SKILL.md`;
6. the active phase’s specimen/spec files and current asset inventory.

Continue from the first incomplete acceptance item unless the owner explicitly reprioritizes.

## 2.4 Evidence vocabulary

- **DESIGN SPEC** — documented visual rule only;
- **SOURCE** — committed source/assets exist and parse/render as applicable;
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

## 4.1 Character archetypes

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

## 4.3 Working core cast

- **Lilli** — unicorn Puff; wonder, kindness, imagination;
- **Nino** — owl Bean; observation, books, thoughtfulness;
- **Tito** — fox Puff; curiosity, exploration, playful cleverness;
- **Momo** — friendly monster Puff; humor, emotion, experimentation.

These remain design anchors/candidates until explicitly approved.

## 4.4 Expression seed

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

Normal educational mistakes must not use anger, shame or disappointed-at-the-child imagery.

## 4.5 Motion seed

Base Animation Set v0.1:

- `idle_bounce` — 1.6–2.4 s living/resting loop;
- `blink` — 0.15–0.30 s micro-life cue;
- `happy_hop` — 0.7–1.1 s anticipation/squash → hop → settle;
- `celebrate_pop` — 0.9–1.4 s bigger pop + appendage response + bounded FX;
- `surprised_wobble` — 0.5–0.9 s recoil/wobble + wide face;
- `sleepy_sway` — 1.8–2.8 s slow sway/compression.

Candidate v0.2 additions remain `think`, `yes_nod`, `no_wobble`, `look_or_point`, `reward_sparkle`, `enter_pop`, `exit_pop`, `listen`.

Do not proliferate motion names until v0.1 is demonstrated across multiple archetypes.

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

Presence in Git never means `approved`.

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

## A1 — Canonical style grammar and archetype specimens **[ACTIVE]**

- [ ] promote accepted constraint-native character direction into `GREIA_VISUAL_STYLE_GUIDE.md`;
- [x] define candidate Puff/Bean/Cutout Critter/Object Friend construction grammar;
- [x] define candidate outline/shadow/fill/detail/color disciplines;
- [x] create 256/128/64 static comparison review source;
- [x] define economical versus placeholder failure patterns;
- [ ] **owner visual review of Lilli/Nino/Tito/Momo**;
- [ ] revise/approve/reject candidates and promote accepted rules.

Candidate grammar:

```text
docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md
```

Candidate review:

```text
assets/visual/specimens/a1/review.html
```

A1 closes only after owner visual review and reconciliation into the canonical living style guide/library statuses.

## A2 — Expression and motion system

- [ ] expression specification and face-state templates;
- [ ] normalized timing/phase/easing for Base Animation Set v0.1;
- [ ] demonstrate all six base motions on at least Puff, Bean and Object Friend;
- [ ] define static fallbacks;
- [ ] inspect existing `ui_motion`/runtime seams before any implementation; no parallel animation framework;
- [ ] desktop/simulator clarity/performance evidence.

## A3 — Starter character and Object Friend library

- [ ] approved Lilli/Nino/Tito/Momo assets;
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
