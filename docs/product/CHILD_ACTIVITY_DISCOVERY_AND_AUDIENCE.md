# Greia Child Activity Discovery and Audience Requirements

**Status:** accepted product requirement; foundational manifest/profile/discovery/adaptive-Collection implementation active  
**Date:** 2026-08-23  
**Scope:** child Shell/Home, Activity catalogue projection, Activity educational/presentation metadata, child-profile discovery preferences, Parent per-child Activity visibility policy  
**Related:** `docs/adr/0018-lightweight-ui-foundation.md`, `docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md`, `docs/product/PARENT_MANAGEMENT.md`, `docs/product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md`, `skills/greia-activity-authoring/SKILL.md`

## 1. Product intent

Greia must remain easy to navigate when a device contains four Activities and when it contains dozens of Activities.

The child Shell therefore uses a **Collection-first discovery model** rather than treating normal Home as a flat application catalogue with category filters.

Normal child mental model:

```text
Greia Home
  → primary Collection
    → Activity
```

When a primary Collection becomes too dense and a coherent semantic partition exists, Greia may introduce exactly one additional grouping layer:

```text
Greia Home
  → primary Collection
    → optional sub-Collection
      → Activity
```

This is a Greia navigation model, not a filesystem model. A Collection may visually resemble a shelf, box, book, bag, art case, toy box, room or other child-friendly object, but it never exposes Linux directories or paths.

## 2. Primary Collections are destinations, not filter tabs

The platform-owned high-level child vocabulary is:

```text
create
play
learn
explore
my_greia
```

These are normal major child-facing destinations on Greia Home, using strong semantic icon/art identity and localized titles.

`All` remains an internal catalogue projection, Parent/admin/search/browse compatibility surface; **`All` is not normal child Home**.

A child entering `Create` experiences a navigation transition into that Collection. Collection identity remains visible while browsing, and local Back returns toward the containing Collection/Home.

### 2.1 Packages do not manufacture primary Home destinations

`[presentation].categories` is Activity metadata consumed by a platform-owned projection. It is not authority to extend Greia Home.

A package may declare recognized primary IDs from the vocabulary above. Other bounded strings may remain tolerated metadata for compatibility, but arbitrary values such as `care`, `art`, `geometry` or `storybook` do **not** automatically become root Home portals.

This keeps Home small and predictable and prevents packages from reshaping the OS information architecture by inventing labels.

### 2.2 Unknown-only Activities fail open through Browse/More

A valid Activity with no recognized primary Collection must not disappear.

Greia projects such Activities into one platform-owned bounded recovery destination:

```text
browse
```

Current child-facing localization is equivalent to `Altro` / `More`. It appears only when needed and is not a sixth package-owned taxonomy.

An Activity with at least one valid primary category stays in its valid primary Collection(s) even if it also declares extra unknown metadata.

## 3. One Activity may belong to more than one Collection

Collection membership is presentation metadata, not package/storage identity.

For example:

```text
Shape Garden
  → Create
  → Learn
```

This never duplicates installation, Activity ID, saves, permissions, session history, progression or Awards.

Therefore Collections/sub-Collections must never be taught as literal filesystem folders containing unique copies of files.

## 4. Adaptive Collection depth

Greia does not force every primary Collection to contain sub-Collections.

### 4.1 Density policy

Current platform policy is:

- **1–8 effective visible Activities:** direct presentation; any previous subdivision collapses;
- **9–10 effective visible Activities:** remain direct unless the Collection was already validly subdivided;
- **more than 10 effective visible Activities:** evaluate a semantic one-level subdivision;
- crossing the threshold alone never forces subdivision;
- if no complete, useful semantic partition exists, retain direct bounded browsing.

The implementation expresses this as `enter_threshold = 10` and `collapse_threshold = 8`.

### 4.2 Semantic-quality requirement

A useful subdivision normally has:

- 2–5 platform-recognized child-understandable groups;
- at least two Activities in each retained group;
- no stranded Activities;
- no fabricated giant `Other` bucket;
- material reduction in simultaneous choice density;
- stable localized semantic labels/icons.

`AdaptiveCollectionPlanner` currently requires the semantic grouping to cover the Collection cleanly. If Activities remain unassigned or the grouping is otherwise poor, it returns the direct Collection instead.

### 4.3 Maximum depth

Hard conceptual depth remains:

```text
Home → primary Collection → optional sub-Collection → Activity
```

Do not build filesystem-like trees such as:

```text
Home → Create → Art → Drawing → Painting → Activity
```

If the catalogue cannot be made usable within the allowed depth, improve grouping, ranking, bounded browse/search or Collection presentation instead of nesting deeper.

### 4.4 Stability / hysteresis

Navigation should not flap when one Activity is installed/removed.

`ActivityDiscoveryPolicy` stores bounded platform-owned `subdivided_collections` state separately from Parent visibility intent, and the adaptive planner applies the 10/8 enter/collapse thresholds. This state is UI stability memory, not package authority and not a Parent preference.

## 5. Effective catalogue count is per child

Adaptive depth uses the **effective visible Activity set for the active child**, not raw installed count.

Conceptually:

```text
validated installed registry
  ↓
Parent per-child visibility policy / explicit overrides
  ↓
profile audience and challenge presentation policy
  ↓
effective visible Activities
  ↓
Collection projection + adaptive-depth decision
```

Example: if 22 Activities are installed under `Learn` but Parent policy leaves 8 visible for a child, Greia reasons about those 8 rather than creating hierarchy from the raw 22.

Presentation filtering never upgrades package trust or bypasses registry/runtime authority.

## 6. Age/developmental suitability and difficulty are independent

Greia never overloads one number to mean both developmental suitability and challenge.

### Age/developmental suitability answers

> Who was this Activity primarily designed for?

### Difficulty answers

> How challenging is this Activity within its intended audience/content domain?

A preschool Activity can be challenging for preschoolers while still being elementary for an older child. An open-ended creative tool can be easy to enter while remaining worthwhile at many ages.

Filtering/ranking therefore treats audience age and difficulty as separate dimensions.

## 7. Baseline challenge: `education.difficulty`

Current source requires:

```toml
[education]
difficulty = 3
```

`src/greia_platform/activities.py` validates `difficulty` as an integer **1 through 10**. It is the baseline challenge indicator and must not be reinterpreted as age.

## 8. Audience and adaptive-difficulty metadata — implemented

Current Activity manifests support optional audience fields:

```toml
[education]
difficulty = 3
recommended_age_min = 5
recommended_age_max = 8
```

Bounds:

- `recommended_age_min`: optional integer 1–18;
- `recommended_age_max`: optional integer 1–18;
- when both are present, min must not exceed max.

Open-ended Activities may omit one bound, for example:

```toml
[education]
difficulty = 1
recommended_age_min = 3
```

Current source also supports a true adaptive challenge span:

```toml
[education]
difficulty = 3
difficulty_min = 1
difficulty_max = 7
adaptive_difficulty = true
recommended_age_min = 5
recommended_age_max = 10
```

Rules:

- `difficulty_min` / `difficulty_max` are optional integers 1–10;
- they must be declared together;
- the lower value must not exceed the upper value;
- a difficulty range requires `adaptive_difficulty = true`;
- `adaptive_difficulty = true` requires a declared range.

The exact parser/validation contract is source-owned by `src/greia_platform/activities.py` and its tests.

## 9. Discovery/sub-Collection metadata — implemented

High-level launcher Collections remain separate from educational taxonomy.

Current presentation metadata supports:

```toml
[presentation]
categories = ["create", "learn"]
discovery_tags = ["drawing", "shapes"]
```

`discovery_tags` are bounded semantic grouping hints. They do **not** command Greia to create a folder or root destination.

The launcher owns a bounded recognized sub-Collection vocabulary (`DISCOVERY_GROUP_IDS`). Packages may contribute recognized hints, but cannot manufacture arbitrary child navigation labels.

`education.categories` and `education.skills` remain learning/progression metadata and do not automatically become navigation levels.

## 10. Child profile audience information — implemented

`ChildProfile` contains:

```text
approximate_age: optional integer 1–18
challenge_preference: automatic / easier / standard / harder
```

No exact date of birth is required.

Challenge preference affects discovery ordering:

- Automatic and Standard preserve age relevance ordering;
- Easier prefers lower baseline difficulty among otherwise similarly ranked visible Activities;
- Harder prefers higher baseline difficulty.

It does not rewrite Activity save data and is not a mastery assessment.

## 11. Recommendation is not restriction

Audience metadata primarily improves emphasis/order. It is deliberately forgiving of incomplete metadata.

Potential child-facing discovery views may later use neutral equivalents of:

```text
For me
Easier
Harder
All
```

Such labels are views, not grades. Greia avoids messages describing a child as too young, too old, bad or behind.

## 12. Parent per-child visibility policy — implemented

Parent authority may apply stronger rules through a profile-scoped `ActivityDiscoveryPolicy`.

Implemented modes:

```text
show_all
hide_too_simple
recommended_only
custom
```

Implemented individual overrides:

```text
always_show
always_hide
```

An explicit Activity override is evaluated before automatic age-based policy:

- `always_hide` hides;
- `always_show` shows;
- missing age or missing audience metadata fails open in automatic policy;
- `hide_too_simple` only hides when a declared upper recommended age is below the child's approximate age;
- `recommended_only` respects declared min/max while unknown/general metadata remains visible.

The Parent API exposes `GET/PUT /api/v1/profiles/{profile_id}/activity-policy`, and the rebuilt HTML Parent client renders and mutates this typed policy.

Visibility policy affects catalogue presentation only; it does not mutate package trust, installation, permissions, saves or Activity identity.

## 13. Missing/incomplete metadata fails open

Rules:

- no `recommended_age_max` means no declared upper age bound;
- no age metadata means **unknown/general**, not automatically unsuitable;
- creative/open-ended tools may intentionally have no meaningful upper bound;
- no adaptive difficulty range means ordinary baseline difficulty behavior;
- unknown/unrecognized primary presentation metadata does not hide a valid Activity; it is recoverable through Browse/More;
- Parent explicit hide remains authoritative;
- invalid declared schema fields remain package validation errors according to source policy.

Greia prefers transparent unknown state to invented classification.

## 14. Age metadata is not a content-safety rating

`recommended_age_*` describes developmental/product suitability inside Greia's curated child Activity ecosystem.

It is not an ESRB/PEGI/legal content rating, parental-consent mechanism or permission boundary.

Package curation, permissions, trust and child-safety controls remain separate.

## 15. Ranking and bounded shortcuts

Collection-first navigation does not forbid lightweight `Continue`, recent or favorite shortcuts.

Any such extension must:

- remain bounded;
- obey effective Parent visibility policy;
- never duplicate package/state authority;
- not recreate a giant flat application wall;
- not make streak/engagement mechanics the primary discovery system.

This remains optional product extension work.

## 16. Responsive behavior

The Collection-first model obeys `RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md`:

- Home contains a small bounded set of primary choices and normally requires no scrolling;
- Browse/More appears only when needed;
- Collection cards reflow from actual viewport;
- optional sub-Collections and Activity lists use bounded shared presentation;
- the same hierarchy works on the low-resolution Acer reference and larger displays;
- no device-specific category layout tables.

## 17. Input parity

Pointer, keyboard, touch and controller operate on the same semantic navigation state.

Adaptive hierarchy is not pointer-only. Focus, Back, launch origin and return destination remain coherent across input paths.

## 18. Current implementation status

Current source implements the foundational contract described above:

- registry-owned Activity catalogue projection;
- Collection-first Home;
- bounded platform-owned root Collection vocabulary plus Browse/More recovery;
- one Activity in multiple Collections without state duplication;
- bounded Activity scrolling;
- baseline `education.difficulty` 1–10;
- `recommended_age_min/max` audience fields;
- `difficulty_min/max` plus `adaptive_difficulty` validation;
- `presentation.discovery_tags`;
- optional profile `approximate_age` and `challenge_preference`;
- profile-scoped atomic Activity discovery policy storage;
- fail-open audience filtering and challenge-aware ordering;
- explicit Parent visibility overrides with override precedence;
- effective per-child catalogue computation before launcher projection;
- adaptive optional sub-Collections with bounded platform-owned discovery vocabulary;
- 10/8 enter/collapse hysteresis model and stored subdivision state;
- Parent API resources for Activity inventory and per-child policy;
- rebuilt responsive Parent HTML controls for child age/challenge and Activity policy;
- Collection-first, bounded-vocabulary and adaptive catalogue simulator acceptance recorded in the repository testing documentation.

The Activity Card Titles and Unique Icons contract also remains active: two-line title wrapping, defensive title cap/full-title disclosure, contain-fit icon padding and unique first-party package icons are separate presentation requirements and are not changed by adaptive discovery.

Still-open/future work includes product calibration/user testing of thresholds and metadata quality, optional richer bounded recent/favorite discovery surfaces, and any future expansion of the recognized semantic group vocabulary. Those extensions must preserve the authority/depth/fail-open rules in this document.

## 19. Acceptance requirements

Focused acceptance for this architecture covers:

1. **bounded root vocabulary:** arbitrary package categories cannot manufacture primary Home destinations;
2. **unknown-category recoverability:** valid unknown-only Activities remain discoverable through Browse/More;
3. **mixed metadata:** valid primary membership is preserved despite extra unknown metadata;
4. **small catalogue:** direct presentation remains usable;
5. **large coherent catalogue:** useful one-level subdivision can occur;
6. **large incoherent catalogue:** no forced bad subdivision;
7. **maximum depth:** no path exceeds Home → primary Collection → optional sub-Collection → Activity;
8. **multi-membership:** no Activity-state duplication;
9. **per-child count:** adaptive depth uses the effective visible set after Parent policy;
10. **hysteresis:** minor catalogue changes do not repeatedly reshape navigation;
11. **age/difficulty independence:** age is never treated as difficulty;
12. **missing metadata:** valid Activities fail open unless Parent policy explicitly hides them;
13. **Parent override:** explicit always-show/always-hide wins over automatic recommendation;
14. **profile privacy:** exact DOB is not required;
15. **responsive matrix:** hierarchy remains usable at required Greia viewports;
16. **input parity:** pointer, keyboard and controller/touch share hierarchy and Back semantics;
17. **authority:** presentation filtering never bypasses registry/runtime/trust/permission authority.

Do not infer completion of unrelated package-management, pairing-security or education-assessment work merely because this discovery architecture is implemented.
