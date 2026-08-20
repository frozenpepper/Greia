# Greia Visual Foundation and Asset System — Active Art Workstream Plan

**Status:** ACTIVE ART WORKSTREAM PLAN  
**Started:** 2026-08-20  
**Owner:** Greia project  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Scope:** Greia visual language, character system, motion vocabulary, reusable art/scene/UI asset library, visual-authoring skills, and staged adoption by Shell/Activities  
**Blocking-platform relationship:** subordinate to `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`; this art workstream does not close, bypass, reorder, or weaken R7/R8/R9/R10/R14 or any accepted ADR gate.

---

## 0. Why this plan exists

The initial Greia UI and model-generated Activities proved that merely telling a capable coding/model system to “make it cute” does not produce a coherent child product. The Shell has some promising illustration and interaction direction, but individual Activities can still collapse into prototype graphics: flat rectangles, primitive trees, unrelated control styles, empty compositions, weak hierarchy, and characters that look like development placeholders.

A second experiment exposed another important limit: Greia cannot make its default visual architecture depend on generating detailed traditionally proportioned animals and then automatically deriving production-quality articulated animation rigs. Attempts to produce exact sprite sheets or decomposed multi-joint animals were unreliable, and programmatic full-anatomy vector recreation created visually poor results even when the underlying rig mechanics worked.

That failure is useful evidence. Greia should not spend an open-source project’s nonexistent art-department budget fighting the medium. The project should instead develop a **constraint-native visual language** that makes simple, reproducible art look intentional, charming and recognizably Greia.

The accepted direction of this workstream is therefore:

> **Simple expressive characters + strong faces + whole-body motion + chunky illustrated props + cozy layered scenes + tactile Greia UI.**

The visual system should turn current limitations into a style advantage rather than treating them as defects to hide.

This is not an instruction to imitate South Park or any other existing show. The useful lesson is only that a memorable visual language can be designed around economical, repeatable construction and animation. Greia must develop its own child-safe visual identity.

---

# 1. Authority and relationship to existing Greia documentation

This plan owns **sequencing, checkpoints, closure criteria, and append-only progress history for art/visual-system work while it is active**.

It does not replace:

- `AGENTS.md` — repository-wide rules;
- accepted ADRs — architecture/trust/runtime authority;
- `docs/design/GREIA_VISUAL_STYLE_GUIDE.md` — living cross-product visual-language and typography direction;
- `docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md` — art inventory/production requirements;
- source/runtime declarations — exact implemented APIs, file formats and runtime behavior;
- `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` — blocking platform implementation sequence;
- `HANDOVER.md` — current continuation/evidence boundary.

When work in this plan settles a reusable visual rule, update the appropriate design authority rather than leaving the decision only in this plan. When it changes an implemented Activity/UI/asset API, update source-owned contracts and the relevant living skills/manuals in the same tranche.

---

# 2. Multi-session progress protocol

This plan is designed to survive many work sessions and different agents.

## 2.1 Mutable current checkpoint

The small checkpoint below is the **only intentionally mutable summary** in this document. Keep it short and current.

| Field | Current state |
|---|---|
| Active art phase | **A1 — Canonical style grammar and archetype specimens** |
| Current design direction | constraint-native **puff / bean / cutout / object-friend** character language |
| Working core cast | **Lilli** (unicorn puff), **Nino** (owl bean), **Tito** (fox puff), **Momo** (friendly monster fluff) |
| Current motion seed | idle bounce, blink, happy hop, celebrate pop, surprised wobble, sleepy sway |
| Current implementation status | A0 repository wiring complete: active plan, AGENTS registration, documentation authority map, visual-authoring skill, HANDOVER state, and non-runtime visual library seed are committed |
| Current evidence | DESIGN SPEC + SOURCE only; no release-quality canonical character art, simulator visual acceptance, or C0/physical visual acceptance claimed |
| Next exact step | begin A1 by defining the static construction/style grammar for Puff, Bean, Cutout Critter and Object Friend, then produce 256/128/64 comparison specimens for owner review before runtime motion APIs |

## 2.2 Append-only progress ledger

Every substantive art/visual-system session MUST append a new dated entry under **§15 Progress ledger**. Do not rewrite older entries to make the history look cleaner.

Each entry records:

1. exact date/time or date;
2. phase worked;
3. files/artifacts changed;
4. decisions made;
5. evidence actually obtained;
6. failures/rejected directions worth remembering;
7. next exact action;
8. relevant commit SHA(s) when known.

## 2.3 Session-resume rule

An agent resuming art work must:

1. read `AGENTS.md`;
2. read this plan’s **Current checkpoint** and latest ledger entries;
3. read `docs/design/GREIA_VISUAL_STYLE_GUIDE.md` and `docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md`;
4. read `skills/greia-visual-authoring/SKILL.md` once present;
5. inspect current source/assets before creating parallel systems;
6. continue from the first incomplete acceptance item in the active art phase unless the owner explicitly reprioritizes.

## 2.4 Evidence labels for art work

Use evidence scope precisely:

- **DESIGN SPEC** — documented visual rule or asset contract only;
- **SOURCE** — committed source/assets exist and parse/validate as applicable;
- **DESKTOP VISUAL REVIEW** — rendered/inspected on a normal development machine;
- **SIMULATOR VISUAL REVIEW** — inspected through the Greia Activity Simulator at named synthetic viewports;
- **PHYSICAL VISUAL REVIEW** — inspected on named Greia reference hardware;
- **REJECTED EXPERIMENT** — deliberately retained lesson, not a candidate asset.

Do not convert a source SVG, screenshot, HTML mock-up, or simulator result into Acer/Pi acceptance without the named physical review.

---

# 3. Product constraints that shape the art system

The visual system must be designed around Greia’s actual constraints rather than an imaginary production studio.

1. **Open-source/no-art-department reality.** The default workflow must be viable for maintainers and model-assisted contributors without assuming a team of professional character animators.
2. **C0 hardware floor.** Static SVG/PNG/sprite use, small bounded animation state and cheap transforms are preferred. Never require heavyweight real-time character software on the child device merely to make the product charming.
3. **800×600 / 1024×600 readability.** Important silhouettes, expressions, icons and interaction states must survive small/old displays.
4. **Offline first.** Runtime visuals cannot depend on network generation/CDNs.
5. **Static meaning first.** Animation may enrich a state but cannot be the only way to understand it.
6. **Language-light child UX.** Shape, expression, position, symbol, optional speech and motion should communicate before prose when appropriate.
7. **Platform-owned system chrome remains authoritative.** Art work does not authorize Activities to replace/mimic protected Home/Back or other Greia trust surfaces.
8. **One coherent world.** Shell, first-party Activities, rewards, profiles and common error/recovery states should feel related even when individual Activities have their own theme.
9. **Generation must be constrained.** Models should compose within a Greia grammar instead of inventing a new visual system for every Activity.
10. **Asset provenance/licensing remains mandatory.** Generated/contributed assets need a traceable source/license record appropriate to their origin and Greia governance.

---

# 4. The new Greia character language

## 4.1 Default archetypes

Greia should initially concentrate on a very small family of construction archetypes.

### Puff

A soft round/oval main mass with a large face area, zero or tiny feet, optional stub arms/wings, and a few species/identity attachments.

Good for unicorns, foxes, cats, dogs, rabbits, baby animals, monsters and recurring companions.

### Bean

A vertical rounded bean/drop body with face on the upper half, tiny feet and optional flap-like arms/wings.

Good for owls, birds, penguin-like creatures, little helpers and compact character roles.

### Cutout critter

A deliberately flatter sticker/felt/paper-cut construction with very few layers and a strong silhouette.

Good for activity-local characters, simple animals and scenes where flat composition is an asset rather than a compromise.

### Object friend

A pedagogical object with a face and very limited appendages: number, letter, block, palette, train wagon, tool, shape, food item, star, cloud, etc.

Object friends are especially valuable because many Activities do not need an animal cast at all.

## 4.2 Default anatomy rule

Unless an Activity has a strong reason and dedicated art, Greia characters should use:

- one primary body mass;
- one face region;
- zero to two tiny feet;
- zero to two tiny arms/flaps/wings;
- zero to three identity attachments such as ears, horn, tuft, tail, antennae, bow, hat or marking.

Avoid as the default:

- articulated knees/elbows;
- anatomically realistic quadruped gait;
- front/back multi-limb rigs;
- complex neck/torso anatomy;
- many independently animated hair/fur pieces;
- detailed body rendering that only looks correct at large sizes.

A rare bespoke hero asset may exceed these limits, but the reusable Greia architecture must not depend on it.

## 4.3 Recognition rule

Identity should come primarily from:

- silhouette;
- face;
- major color blocks;
- two or three distinctive attachments;
- personality/motion/sound.

A “unicorn” does not need horse anatomy if a cream puff with a rainbow tuft, horn, tiny hoof cues and expressive face reads instantly as Lilli.

## 4.4 Working core cast

The current simple, internationally pronounceable Italian working names are:

- **Lilli** — unicorn puff; wonder, kindness, imagination;
- **Nino** — owl bean; observation, books, thoughtfulness;
- **Tito** — fox puff; curiosity, exploration, playful cleverness;
- **Momo** — friendly monster fluff; humor, emotion, experimentation.

These names anchor design experiments; their existence does not require every Activity to use them.

---

# 5. Expression system

Expression is more important than anatomical articulation in the new style.

## 5.1 Base expression vocabulary

Reusable/hero characters should work toward:

- `neutral`
- `happy`
- `excited`
- `surprised`
- `sleepy`
- `sad_gentle`
- `thinking`
- `proud`
- `silly`

Normal educational mistakes must not use anger, shame or disappointed-at-the-child imagery.

## 5.2 Expression ingredients

Prefer changing:

- eye shape;
- eyelid state;
- pupil direction;
- mouth shape;
- cheek/blush intensity;
- tiny ear/tuft/antenna orientation;
- whole-body tilt/squash;
- optional small particles.

This should provide emotional range without multiplying body rigs.

## 5.3 Readability

Expressions must remain recognizably different at 128 px and should retain the intended emotional cue at 64 px where the character is used that small. Tiny internal linework that disappears at those sizes is not a substitute for expression.

---

# 6. Base motion vocabulary

The motion system should be semantic and reusable across compatible simplified characters.

## 6.1 Base Animation Set v0.1

### `idle_bounce`

Purpose: default living/resting state.  
Typical ingredients: 1.6–2.4 s gentle bob/breath, tiny sway, occasional blink, optional tail/tuft lag.

### `blink`

Purpose: micro-life and expression support.  
Typical ingredients: 0.15–0.30 s eye close/open with tiny settle; may be embedded into idle.

### `happy_hop`

Purpose: small success/joy.  
Typical ingredients: 0.7–1.1 s anticipation squash → short hop → stretch → soft landing → happy face.

### `celebrate_pop`

Purpose: completion/reward/major success.  
Typical ingredients: 0.9–1.4 s larger pop, arms/flaps/ears reacting, happy/excited face, bounded sparkles/stars/hearts.

### `surprised_wobble`

Purpose: discovery, comic reaction, gentle wrong-choice feedback.  
Typical ingredients: 0.5–0.9 s recoil/wobble, wide eyes, small settle.

### `sleepy_sway`

Purpose: night/rest/waiting variation.  
Typical ingredients: 1.8–2.8 s slow sway, closed/half-lid eyes, soft body compression.

## 6.2 Candidate v0.2 additions

- `think`
- `yes_nod`
- `no_wobble`
- `look_or_point`
- `reward_sparkle`
- `enter_pop`
- `exit_pop`
- `listen`

Do not proliferate animation names before the v0.1 set is tested across multiple archetypes.

## 6.3 Motion implementation principle

A semantic motion should describe intent and normalized phase/transform behavior, not assume a horse knee or human elbow. Character-specific adapters may map the same semantic cue onto arms, wings, ears, tail, antennae or whole-body motion.

The eventual runtime implementation should reuse `src/greia_platform/ui_motion.py` concepts or another accepted source-owned seam rather than creating uncontrolled per-Activity animation engines. Exact APIs are deferred until architecture/source review.

---

# 7. Scene, prop and effects language

Simpler characters free Greia to place visual richness where it is easier to produce reliably.

## 7.1 Environments

Preferred scene logic:

- storybook diorama;
- felt-board / paper-cut layering;
- cozy toy-world composition;
- large foreground/midground/background shapes;
- chunky readable decorative props;
- a quiet enough play area that children can identify interactive objects.

Initial environment families should include at least:

- meadow;
- forest;
- workshop;
- clinic;
- classroom/reading corner;
- night/sky;
- simple fantasy/castle;
- water/pond/underwater as needed.

## 7.2 Props

Props should usually be more illustrative than raw primitives but simpler than realistic objects. Favor a few strong shapes, soft depth/shadow, recognizable silhouette and limited internal detail.

Initial prop families:

- nature;
- learning/letters/numbers;
- making/building;
- clinic/care;
- toys;
- home/workshop furniture;
- transport;
- food;
- rewards/treasure.

## 7.3 Effects

A small effects library can make economical assets feel rich:

- sparkles;
- stars;
- hearts;
- dust puffs;
- little impact clouds;
- glow/pulse rings;
- sleepy Zs;
- discovery rays;
- confetti/celebration particles.

Effects must be bounded and cheap; they should not turn every screen into visual noise.

---

# 8. UI visual architecture workstream

The existing semantic Screen/Overlay/Panel/Card/Collection/Control architecture remains authoritative. This plan concerns the **visual language and reusable assets/components** layered onto it.

The target UI feeling is:

- rounded and tactile;
- toy-like without pretending to be a physical toy everywhere;
- soft shadows/depth;
- warm palette;
- clear state hierarchy;
- large child-sized targets;
- coherent motion with the character system.

Priority reusable presentation pieces:

1. primary/secondary/icon buttons;
2. activity card and selected/new/completed states;
3. profile card/avatar frame;
4. bottom/tool trays;
5. speech/thought bubbles;
6. counters/progress pills;
7. reward/badge presentation frames;
8. modal/sheet surfaces;
9. hint/highlight treatments;
10. loading/error/recovery illustrations;
11. scene decorations and category/location portal art.

UI motion should reuse the same vocabulary: small lift, squash/press, pop-in, wobble, pulse, sparkle. It should never interfere with input latency or semantic clarity.

---

# 9. Asset library direction

The intended long-term library is organized by semantic purpose, not by ad-hoc filenames discovered at runtime.

Conceptual layout:

```text
assets/
  characters/
    heroes/
    standard/
    activity_cast/
    object_friends/
  expressions/
  animations/
  props/
  environments/
  ui/
  fx/
  icons/
  catalog/
```

Exact repository paths/catalog schemas become source-owned only when implemented. Do not make a new runtime filesystem-discovery API merely to mirror this conceptual tree.

## 9.1 Asset tiers

### Tier A — canonical shared foundations

Carefully reviewed reusable assets: core cast, body archetype exemplars, common expressions, common effects, core props, UI visuals.

### Tier B — guided generated/contributed content

Minor characters, Activity cast, secondary props and scene variants created under Greia authoring rules and reviewed before inclusion.

### Tier C — local/disposable content

One-off decorative variants where failure cannot undermine system identity or gameplay comprehension.

## 9.2 Canonical asset rule

Greia should prefer explicit asset IDs/catalogues over “scan this directory and guess what it means.” The existing Core Icons v1 catalogue is precedent for semantic inventory. New character/scene catalogues should follow the same general explicitness once formats are designed and reviewed.

---

# 10. Model/agent authoring skills

Model-assisted contribution is a first-class economic constraint of this project. Greia must teach models how to stay inside the visual language.

The living practical guide is:

```text
skills/greia-visual-authoring/SKILL.md
```

It covers:

- mandatory project/design context;
- character archetype selection;
- silhouette and face rules;
- species simplification;
- expression generation;
- motion selection;
- scene composition;
- prop generation;
- UI illustration rules;
- use/reuse of the asset library;
- prohibited complexity/style drift;
- required small-size checks;
- evidence/provenance expectations.

The Activity authoring skill should eventually direct Activity models to this visual skill instead of expecting each Activity prompt to rediscover art direction.

---

# 11. Phased work plan

## A0 — Workstream foundation **[COMPLETE — DESIGN SPEC/SOURCE]**

Deliverables:

- [x] create this active art plan with multi-session progress protocol;
- [x] reference it from `AGENTS.md` as the mandatory current art-related workstream plan without superseding the blocking architecture plan;
- [x] establish `skills/greia-visual-authoring/SKILL.md`;
- [x] create a starter repository asset-library contract/readme that clearly distinguishes design inventory from runtime API;
- [x] record the art workstream in `HANDOVER.md` without changing R7 evidence/priority;
- [x] commit the tranche to `main`.

Closure criterion: another agent can resume art work from repository files alone and knows the exact next visual task, rules, progress location and evidence boundary. **Satisfied at repository/source scope on 2026-08-20.**

## A1 — Canonical style grammar and archetype specimens **[ACTIVE]**

Deliverables:

- [ ] promote the constraint-native character direction into the appropriate living design guide;
- [ ] define Puff, Bean, Cutout Critter and Object Friend construction sheets;
- [ ] define canonical outline/shadow/fill/detail rules consistent with `runtime/theme-defaults.toml` while allowing themed content palettes;
- [ ] create comparison specimens at 256/128/64 px;
- [ ] define “too simple/placeholder” versus “appropriately economical” examples;
- [ ] owner visual review of at least Lilli, Nino, Tito and Momo in static form.

Closure criterion: independent contributors/models can make recognizably Greia characters without copying a specific existing character.

## A2 — Expression and motion system

Deliverables:

- [ ] expression spec and face-state templates;
- [ ] Base Animation Set v0.1 normalized timing/phase/easing rules;
- [ ] demonstrate all six v0.1 motions on at least Puff, Bean and Object Friend archetypes;
- [ ] static fallbacks for each semantic reaction;
- [ ] assess whether any shared runtime motion helper needs extension; do not implement a parallel animation framework without review;
- [ ] simulator/desktop performance and clarity checks.

Closure criterion: motion looks intentional across multiple simple archetypes without anatomical rigs.

## A3 — Starter character and object-friend library

Deliverables:

- [ ] canonical core cast assets for Lilli/Nino/Tito/Momo after owner approval;
- [ ] 8–12 reusable standard creatures;
- [ ] 10–15 object friends/educational characters;
- [ ] semantic metadata/catalogue design with explicit provenance;
- [ ] 64/128/256 variants or vector masters with deterministic raster pipeline where appropriate.

Closure criterion: Activities can draw from a meaningful shared cast before inventing new characters.

## A4 — Props, environments and FX library

Deliverables:

- [ ] first coherent meadow/forest/workshop/clinic scene families;
- [ ] 20–30 initial reusable chunky props across priority categories;
- [ ] common FX pack;
- [ ] layered scene composition guidance and safe playfield conventions;
- [ ] low-resolution screenshots showing that scenes are rich without becoming cluttered.

Closure criterion: a simple generated Activity can look substantially better by composing shared assets instead of drawing prototype geometry.

## A5 — UI visual component language

Deliverables:

- [ ] visual variants for existing semantic buttons/cards/panels/trays/progress/bubbles;
- [ ] hover/focus/press/selected/new/completed/locked/error state treatment;
- [ ] consistent icon/illustration sizing and depth rules;
- [ ] reusable child-safe loading/error/recovery art;
- [ ] interaction-motion mapping to shared semantic motion vocabulary;
- [ ] 800×600 and 1024×600 reference compositions.

Closure criterion: Greia-owned controls and common first-party Activity UI no longer look like unrelated prototype widgets.

## A6 — Model authoring/validation pack

Deliverables:

- [ ] mature `greia-visual-authoring` skill with examples and rejection criteria;
- [ ] update `greia-activity-authoring` to require/reuse the visual skill for relevant work;
- [ ] define lightweight static validation/checklist for asset dimensions, paths, provenance, missing states and obvious style-contract violations;
- [ ] explicitly avoid pretending deterministic code can judge subjective beauty;
- [ ] test instructions with at least one weaker/local model and one stronger model.

Closure criterion: model-assisted contributors reliably reuse the Greia grammar/library instead of starting from raw rectangles or unrelated art styles.

## A7 — Platform/library integration

Prerequisite: source/architecture review for any runtime-facing asset or motion API.

Deliverables:

- [ ] explicit catalogue/loader contract if needed;
- [ ] bounded caching and no per-frame decode/I/O;
- [ ] Python/Pygame shared helpers first where current runtime authority allows;
- [ ] future Web runtime consumes the same semantics/assets rather than a parallel design system;
- [ ] asset fallback behavior and package/image composition;
- [ ] simulator asset preview/gallery tooling if useful.

Closure criterion: shared art is inexpensive and easy to consume without violating Greia runtime/trust boundaries.

## A8 — First-party Activity/Shell visual refit and acceptance

Deliverables:

- [ ] identify first-party screens/Activities with prototype-art debt;
- [ ] refit in small reviewable tranches using shared components/assets;
- [ ] preserve gameplay/input/storage/localization behavior while improving presentation;
- [ ] simulator review at named viewports;
- [ ] physical Acer/Pi visual/performance review where relevant;
- [ ] update screenshots/docs and retire superseded provisional assets intentionally.

Closure criterion: the initial public Greia experience visibly belongs to one product and simple model-generated Activities can meet a useful visual baseline by default.

---

# 12. Quality gates

A candidate visual foundation is not accepted merely because it renders.

## 12.1 Character gate

Check:

- silhouette recognizable at 64/128/256;
- face clear at expected usage sizes;
- expression states visibly distinct;
- no unnecessary anatomy/parts;
- accessory count restrained;
- color/outline/detail coherent with Greia;
- neutral static pose works without animation;
- motion does not expose ugly gaps or require bespoke anatomy to look plausible.

## 12.2 Activity scene gate

Check:

- interactive objects clearly separate from decoration;
- background does not overpower gameplay;
- layout has visual hierarchy and no giant accidental dead zones;
- props look intentional rather than raw debug primitives;
- system-safe region remains respected;
- 800×600 / 1024×600 remain legible;
- no essential meaning depends on subtle animation or color only.

## 12.3 UI gate

Check:

- child hit targets remain large;
- state changes are clear by shape/depth/icon/position, not color alone;
- typography follows Greia roles;
- standard controls look related across Activities;
- protected system controls remain unmistakably Greia-owned;
- shadows/effects are bounded and cheap.

## 12.4 Performance gate

Check at the appropriate implementation phase:

- no per-frame asset decode or filesystem access;
- bounded caches/particles/animation state;
- static fallback path;
- no heavyweight animation runtime required on C0 merely for common mascots;
- physical evidence before claiming the Acer floor is accepted.

---

# 13. Explicit rejected/default-nonviable directions

Record these so future sessions do not repeat the same dead ends without new evidence.

1. **One-shot 8×8 AI sprite sheet as the default character pipeline:** rejected as unreliable for temporal identity, loop continuity and exact frame count.
2. **Automatic detailed traditional quadruped decomposition/rigging as the default Greia character architecture:** currently nonviable; occlusion, face states, limb topology and style preservation create too many failure modes.
3. **Programmatic vector recreation of a detailed generated animal after the fact:** rejected as a default pipeline; mechanics can work while visual identity collapses.
4. **“Just draw with Pygame primitives” as production art:** acceptable for prototypes/debug geometry, not a sufficient production aesthetic for represented trees, animals, clinics, rivers, etc.
5. **Solve the problem by hiring an art/animation department:** not a viable project assumption.
6. **Random visual style per generated Activity:** explicitly contrary to the Greia product direction.

These are default architecture conclusions, not a ban on a contributor donating an excellent bespoke asset.

---

# 14. Completion definition

This art workstream can be marked COMPLETE only when:

- the Greia character/scene/UI language is documented and reflected in living design authorities;
- a practical model authoring skill exists and has been exercised;
- a meaningful shared character/prop/environment/FX/UI asset foundation exists with provenance;
- the base semantic expression/motion vocabulary is implemented or consumable through an accepted bounded path;
- multiple first-party Activities/Shell surfaces demonstrate the system rather than isolated mock-ups;
- 800×600 / 1024×600 simulator/desktop review is recorded;
- physical low-resource review is recorded for the runtime/rendering claims that require it;
- HANDOVER and authoring docs identify the resulting stable extension points;
- this plan’s open acceptance items are either completed or explicitly deferred into a successor plan with owner approval.

When completed, preserve this document as historical evidence and remove/update its active-art-plan references from `AGENTS.md`/HANDOVER.

---

# 15. Progress ledger — append only

## 2026-08-20 — A0 started: constraint-native visual pivot

**Phase:** A0 — Workstream foundation  
**Evidence:** DESIGN SPEC / prior REJECTED EXPERIMENTS

### Decisions

- Abandon detailed traditionally articulated animals as the *default* Greia character architecture.
- Develop an original Greia visual language around Puff, Bean, Cutout Critter and Object Friend archetypes.
- Make expression and whole-body motion the primary character-animation tools.
- Use scene composition, props, tactile UI and small FX to provide richness rather than anatomical complexity.
- Adopt simple Italian working names that are also easy for foreign children to pronounce: Lilli, Nino, Tito, Momo.
- Seed Base Animation Set v0.1 with idle bounce, blink, happy hop, celebrate pop, surprised wobble and sleepy sway.
- Make this file the durable multi-session art progress ledger, with a short mutable checkpoint plus append-only dated history.

### Lessons retained

- Attractive single character illustrations do not imply reliable generated sprite sheets.
- Exact articulated part generation/decomposition is substantially harder than producing a coherent simple character.
- Rig mechanics can be technically acceptable while the artwork remains visibly unacceptable.
- Greia needs a style designed around reproducibility, not a weaker imitation of a studio-animation style.

### Work started

- Active plan created.
- `AGENTS.md`, visual-authoring skill, starter asset-library contract and HANDOVER registration are the immediate A0 follow-up tranche.

### Next exact action

Complete A0 repository wiring, then produce A1 static archetype/style specimens and owner-review them before investing in runtime motion APIs.

### Commits

- Initial plan: `f05dda2d5e7f4dddb4f49eadfb971667591d0ec6`.

## 2026-08-20 — A0 repository wiring complete; A1 activated

**Phase:** A0 closure → A1 start  
**Evidence:** DESIGN SPEC / SOURCE

### Files/artifacts established

- `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md` — durable art sequencing/checkpoint/ledger;
- `skills/greia-visual-authoring/SKILL.md` — practical model/contributor visual rules;
- `assets/visual/README.md` — starter library/provenance/runtime-boundary contract;
- `assets/visual/library_v0.1.toml` — explicit non-runtime design seed for archetypes, core cast, expressions and base motions;
- `AGENTS.md` — art plan + visual skill added to mandatory read/update rules;
- `docs/DOCUMENTATION.md` — blocking-plan versus art-workstream authority clarified;
- `HANDOVER.md` — current art direction/evidence boundary/next exact step registered without altering R7 priority.

### Decisions/clarifications

- The architecture-remediation plan remains the only blocking implementation sequence; the art plan is a subordinate cross-cutting visual workstream.
- The initial visual library inventory deliberately declares `runtime_consumed = false`; this tranche does not invent an asset loader or motion API.
- Visual evidence remains DESIGN SPEC/SOURCE only. The four working core characters are not release-approved art merely because their conceptual entries now exist.
- Future substantive art sessions must update the checkpoint plus append-only ledger, so the work can continue reliably across sessions/agents.

### Verification/evidence

- Repository writes completed through the canonical GitHub connector on `main`.
- No GitHub Actions were used or inspected.
- No `make verify`, simulator visual acceptance or physical visual acceptance is claimed for this documentation/library-seed tranche.

### Commits

- plan creation: `f05dda2d5e7f4dddb4f49eadfb971667591d0ec6`
- visual-authoring skill: `33e8067b4c5f7b7e5151f7473e30173f36ff9216`
- asset-library README: `be8f0f788c29b803c2361ec64983565e9243bae7`
- library seed inventory: `df746e025cc01ebaff45ae6f314767194590e954`
- `AGENTS.md` registration: `dc41f82e6eeb16e1729d68088f8c59d509d63aba`
- documentation authority map: `cd6a3fdd6104aceb722f281767396a6627073ffb`
- HANDOVER registration: `7c3443d04900f38109db197a7a9dabbdb34605b8`

### Next exact action

Begin A1. Define the canonical static construction/style grammar for Puff, Bean, Cutout Critter and Object Friend, including outline/shadow/fill/detail limits and positive/negative examples; then build 256/128/64 static specimens for Lilli/Nino/Tito/Momo and seek owner visual review before any runtime animation-system integration.
