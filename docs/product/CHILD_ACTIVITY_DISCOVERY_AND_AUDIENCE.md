# Greia Child Activity Discovery and Audience Requirements

**Status:** accepted product requirement; implementation migration pending where explicitly noted  
**Date:** 2026-08-20  
**Scope:** child Shell/Home, Activity catalogue projection, Activity educational/presentation metadata, child-profile discovery preferences, Parent per-child Activity visibility policy  
**Related:** `docs/adr/0018-lightweight-ui-foundation.md`, `docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md`, `docs/product/PARENT_MANAGEMENT.md`, `docs/product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md`, `skills/greia-activity-authoring/SKILL.md`

## 1. Product intent

Greia must remain easy to navigate when a device contains four Activities and when it contains dozens of Activities.

The child Shell therefore uses a **Collection-first discovery model** rather than treating the normal Home screen as a flat application catalogue with category filters.

The normal child mental model is:

```text
Greia Home
  → primary Collection
    → Activity
```

When a primary Collection becomes too dense to browse comfortably, Greia may introduce exactly one additional semantic grouping layer:

```text
Greia Home
  → primary Collection
    → optional sub-Collection
      → Activity
```

This hierarchy is a Greia navigation model, not a filesystem model. A Collection may visually resemble a shelf, box, book, bag, art case, toy box, room or other child-friendly object, but it does not expose Linux directories or paths.

## 2. Primary Collections are destinations, not filter tabs

The recommended high-level child vocabulary remains:

```text
create
play
learn
explore
my_greia
```

These should be presented as major child-facing destinations on Greia Home, using strong semantic icon/art identity and localized titles.

The normal Home screen should not begin by showing every installed Activity. `All` may remain an internal catalogue projection, fallback, Parent/admin view, search/browse destination or compatibility surface, but **`All` is not the preferred child Home experience**.

A child entering `Create` should experience a clear navigation transition into that Collection rather than merely seeing a tab/filter state change.

The Collection identity remains visible while browsing its content, and local Back returns toward Greia Home or the containing Collection.

## 3. One Activity may belong to more than one Collection

Collection membership is presentation metadata, not package/storage identity.

An Activity may legitimately appear in more than one place, for example:

```text
Shape Garden
  → Create
  → Learn
```

This never duplicates:

- installation;
- Activity ID;
- saves;
- permissions;
- session history;
- progression;
- Awards.

For this reason Greia must not teach the primary/sub-Collection model as literal filesystem folders containing unique copies of files.

## 4. Adaptive Collection depth

Greia does not force every primary Collection to contain sub-Collections.

A small Collection is easier to understand when its Activities are shown directly. An extra navigation layer is justified only when it materially reduces choice density.

### 4.1 Initial density policy

The accepted initial policy is:

- **1–10 effective visible Activities:** present Activities directly;
- **more than 10 effective visible Activities:** evaluate whether one semantic sub-Collection layer would simplify discovery;
- **subdivision is not automatic merely because the count crossed 10**;
- if no good semantic partition exists, keep the Activities direct and use the normal bounded scrolling/paging model.

The exact threshold is platform-owned policy, not Activity metadata. Future user testing may tune it without changing Activity package identity.

### 4.2 Semantic-quality requirement

A sub-Collection layer should be introduced only when Greia can form a small number of useful, recognizable groups.

A useful partition normally has properties such as:

- approximately 2–5 child-understandable sub-Collections;
- more than one Activity in a meaningful group where practical;
- no requirement for a large meaningless `Other` bucket merely to satisfy the threshold;
- a measurable reduction in the number of simultaneous choices;
- stable semantic labels/icons that can be localized and understood without reading where possible.

For example, a large `Create` collection may eventually expose concepts such as drawing, writing/storytelling, music or building when the installed catalogue actually supports those groups.

Greia must not create deep taxonomies simply because Activity metadata contains many educational tags.

### 4.3 Maximum depth

Normal child Activity discovery has a hard conceptual depth limit:

```text
Home → primary Collection → optional sub-Collection → Activity
```

Do not build filesystem-like trees such as:

```text
Home → Create → Art → Drawing → Painting → Activity
```

If the catalogue cannot be made usable within the allowed depth, improve grouping, ranking, search/browse support or collection presentation rather than adding another nested level.

### 4.4 Stability / hysteresis

Installing or removing one Activity should not make the child's navigation structure flap back and forth unnecessarily.

The implementation must use a stability policy. The initial design target is:

- crossing above 10 triggers subdivision evaluation;
- once a useful subdivided presentation has been adopted, do not collapse it merely because the effective visible count falls by one or two items;
- a lower collapse threshold around **8 effective visible Activities** is the initial target;
- the exact enter/collapse thresholds and persistence mechanism are platform-owned policy.

The goal is predictable navigation, not mathematical cleverness.

## 5. Effective catalogue count is per child

Adaptive depth is based on the **effective visible Activity set for the active child**, not simply the raw installed Activity count.

Conceptually:

```text
validated installed registry
  ↓
Parent per-child visibility policy / explicit overrides
  ↓
child/profile audience and challenge presentation policy
  ↓
current child discovery view where applicable
  ↓
effective visible Activities
  ↓
Collection projection + adaptive depth decision
```

Example: if 22 Activities are installed under `Learn` but Parent policy hides 14 for a particular child, Greia should reason about the 8 effective visible Activities rather than create unnecessary sub-Collections based on 22.

No presentation filter may upgrade package trust or bypass registry/runtime authority.

## 6. Age/developmental suitability and difficulty are different concepts

Greia must not overload one number to mean both developmental suitability and challenge.

### Age/developmental suitability answers

> Who was this Activity primarily designed for?

### Difficulty answers

> How challenging is this Activity within its intended audience/content domain?

Examples:

- a preschool counting Activity may be difficult for its intended audience while still being too elementary for an older child;
- Painting may be mechanically easy to enter but remain worthwhile for many ages;
- two Activities aimed at the same age range may intentionally have very different challenge levels.

Therefore filtering/ranking must treat age/developmental suitability and difficulty as independent dimensions.

## 7. Current manifest fact: `education.difficulty`

Current source already requires:

```toml
[education]
difficulty = 1
```

and `src/greia_platform/activities.py` validates `difficulty` as an integer from **1 through 10**.

This field is the current baseline challenge indicator. It must not be reinterpreted as the child's age.

The current built-in Activities largely use `difficulty = 1`; those values are not evidence that a complete calibrated difficulty taxonomy already exists. Calibration should be reviewed as the Activity catalogue grows.

## 8. Target audience metadata

Greia should extend Activity educational metadata with optional developmental/audience facts.

The accepted semantic target is equivalent to:

```toml
[education]
difficulty = 3
recommended_age_min = 5
recommended_age_max = 8
```

An open-ended Activity may omit an upper bound:

```toml
[education]
difficulty = 1
recommended_age_min = 3
```

An Activity whose challenge can genuinely adapt should eventually be able to declare the supported challenge span separately from its default/baseline difficulty, conceptually:

```toml
[education]
difficulty = 3
difficulty_min = 1
difficulty_max = 7
adaptive_difficulty = true
recommended_age_min = 5
recommended_age_max = 10
```

### Important current implementation boundary

As of 2026-08-20, the current manifest parser implements `education.difficulty` but **does not yet implement** `recommended_age_min`, `recommended_age_max`, `difficulty_min`, `difficulty_max` or `adaptive_difficulty`.

These names document the accepted target semantics; they must not be placed into packages and described as working until parser/runtime/tests are migrated together.

When the schema is implemented, exact field names, bounds and compatibility behavior become source-owned by `src/greia_platform/activities.py` and its tests.

## 9. Discovery/sub-Collection metadata

High-level launcher Collections remain separate from educational taxonomy.

Current metadata:

```toml
[presentation]
categories = ["create", "learn"]
```

A future manifest migration may add bounded semantic discovery/grouping hints for optional sub-Collections. Conceptually:

```toml
[presentation]
categories = ["create", "learn"]
discovery_tags = ["drawing", "shapes"]
```

These hints describe what the Activity can sensibly be grouped with. They do **not** command Greia to create a permanent folder and do not define a filesystem path.

Greia decides whether a sub-Collection is useful for the current effective catalogue.

`education.categories` and `education.skills` remain learning/progression metadata and must not automatically become child navigation levels.

As of 2026-08-20, `presentation.discovery_tags` is a target semantic example, **not a currently parsed field**.

## 10. Child profile audience information

Greia should be able to use optional per-child audience information to improve discovery.

The product does **not** need a child's exact date of birth for this feature.

A Parent may provide a coarse/approximate age or developmental stage sufficient for discovery policy. The exact profile storage/UI representation should minimize unnecessary personal data.

Greia may also support a child challenge preference such as:

```text
Automatic
Easier
Standard
More challenging
```

This preference affects recommendation/ranking/view selection. It must not rewrite Activity-owned save data or pretend the platform can infer educational mastery from age alone.

As of 2026-08-20, current `ChildProfile` source does not yet contain age/development/challenge fields. This document defines the product requirement for the future profile-policy migration.

## 11. Recommendation is not the same as restriction

Audience metadata should normally help Greia decide what to emphasize, not act as an inflexible gate.

Default behavior should favor relevant Activities while remaining forgiving of imperfect metadata.

Possible child-facing discovery views may include icon-led equivalents of:

```text
For me
Easier
Harder
All
```

These are discovery views, not grades or judgments about the child.

Greia should avoid messaging that labels a child as "too young", "too old", "bad" or "behind".

## 12. Parent per-child visibility policy

Parent authority may apply stronger per-child rules.

The intended Parent controls include policies equivalent to:

```text
Show everything
Hide Activities probably too simple
Show recommended range only
Custom
```

Parents must also be able to override individual Activities, for example:

```text
Always show this Activity to Gaia
Always hide this Activity from Gaia
```

An explicit per-Activity Parent override wins over automatic age/difficulty recommendation policy.

This extends the existing Parent requirement for per-child Activity availability/policy; it does not give Activities authority to hide competitors or modify another Activity's visibility.

## 13. Missing/incomplete metadata fails open for ordinary discovery

Missing audience metadata must not silently make an otherwise valid Activity disappear.

Rules:

- no `recommended_age_max` means no declared upper age bound;
- no age metadata means **unknown/general**, not automatically unsuitable;
- creative/open-ended tools may intentionally have no meaningful upper age bound;
- missing future adaptive-difficulty metadata means Greia uses the ordinary baseline difficulty behavior;
- Parent explicit hide remains authoritative;
- invalid manifest fields, once implemented as schema fields, remain package validation errors according to source policy.

Third-party/open-source metadata may be imperfect. Greia should prefer transparent unknown state to confident but invented classification.

## 14. Age metadata is not a content-safety rating

`recommended_age_*` describes developmental/product suitability inside Greia's curated child Activity ecosystem.

It is not an ESRB/PEGI/legal content rating, parental-consent mechanism or permission boundary.

Greia's package curation, permissions, trust model and child-safety requirements remain separate controls.

## 15. Ranking and recent/favorite shortcuts

Collection-first navigation does not forbid lightweight shortcuts.

A future Home or Collection screen may expose a small bounded `Continue`, recent or favorite Activity area so a frequently used Activity does not become harder to reach merely because the installed catalogue grew.

Such shortcuts must:

- remain bounded;
- obey Parent visibility policy;
- never duplicate package/state authority;
- not reintroduce a giant flat application wall;
- not make engagement/streak mechanics the primary discovery system.

This is an optional extension, not required for the first collection-first implementation.

## 16. Responsive behavior

The Collection-first model must obey `RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md`.

In particular:

- Home should contain only a small bounded set of primary Collection choices and should normally require no scrolling;
- Collection cards/objects reflow from the actual viewport;
- optional sub-Collections and Activity collections use shared bounded scrolling/paging;
- the same semantic hierarchy works on the low-resolution Acer reference and larger displays;
- no device-specific category layout tables are allowed.

## 17. Input parity

Pointer, keyboard, touch and controller must operate on the same semantic navigation state.

The adaptive hierarchy must not exist only for pointer users. Focus movement, Back behavior, launch origin and return destination must remain coherent for controller/keyboard navigation.

## 18. Implementation migration status

This document is an **accepted target product requirement**. It deliberately distinguishes current source from accepted future behavior.

Current source already has:

- `ActivityCatalogue` as a projection over registry-owned Activities;
- semantic `Collection` objects;
- high-level `[presentation].categories`;
- one Activity in multiple categories;
- bounded Activity scrolling;
- `education.difficulty` validated 1–10;
- Parent product direction for later per-child Activity availability/policy.

Current source does **not yet fully implement**:

- Collection-first Home replacing normal `All` landing;
- adaptive optional sub-Collections;
- subdivision discovery tags;
- age/developmental manifest fields;
- adaptive difficulty range metadata;
- age/development/challenge profile fields;
- automatic per-child audience ranking/filtering;
- Parent UI/API controls for these policies.

Implementation must update source, tests, manifest examples, Parent API/client contracts and derived authoring documentation together. Do not claim this requirement as implemented merely because this document exists.

## 19. Acceptance requirements

When implemented, focused acceptance must cover at least:

1. **small catalogue:** 1–10 visible Activities remain direct;
2. **large coherent catalogue:** >10 visible Activities can produce useful sub-Collections;
3. **large incoherent catalogue:** no forced bad subdivision; bounded direct browsing remains usable;
4. **maximum depth:** no path exceeds Home → primary Collection → optional sub-Collection → Activity;
5. **multi-membership:** one Activity can appear in several Collections without state duplication;
6. **per-child count:** adaptive depth uses the effective visible set after Parent policy;
7. **hysteresis:** small install/remove changes do not cause repeated hierarchy flapping;
8. **age/difficulty independence:** recommendation logic does not treat age as difficulty or vice versa;
9. **missing metadata:** ordinary valid Activities remain discoverable unless Parent policy hides them;
10. **Parent override:** explicit always-show/always-hide wins over automatic recommendation;
11. **profile privacy:** exact date of birth is not required merely for discovery;
12. **responsive matrix:** Home/Collections remain usable at required Greia viewport tests;
13. **input parity:** pointer, keyboard and controller/touch paths share hierarchy and Back semantics;
14. **authority:** presentation filtering never bypasses registry/runtime/trust/permission authority.
