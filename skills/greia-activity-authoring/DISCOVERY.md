# Greia Activity Discovery and Audience Authoring

**Status:** current source-aligned Activity-authoring contract  
**Reviewed:** 2026-08-23  
**Source authorities:** `src/greia_platform/activities.py`, `src/greia_platform/activity_discovery.py`, `src/greia_launcher/catalogue_view.py`

This file exists because older product/authoring prose described the discovery fields as a future migration. That migration is now implemented. Where an older Greia document still says the fields below are “conceptual”, “future”, or “not parsed”, **current source plus this source-aligned authoring file wins for implementation facts**. Product intent remains owned by `docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md`.

## 1. Keep three concepts separate

Do not collapse these into one number or one taxonomy:

1. **Primary launcher Collection membership** — where the Activity may appear on Greia Home.
2. **Discovery grouping hints** — what the Activity can sensibly be grouped with if a primary Collection becomes dense.
3. **Audience/challenge metadata** — who the Activity is designed for and how challenging it is.

Educational skill/category metadata remains a fourth, separate learning/progression concern.

## 2. Current manifest syntax

A current Activity may declare:

```toml
[presentation]
categories = ["play", "learn"]
discovery_tags = ["puzzles", "numbers"]

[education]
categories = ["problem_solving", "early_math"]
difficulty = 4
recommended_age_min = 5
recommended_age_max = 8
difficulty_min = 2
difficulty_max = 7
adaptive_difficulty = true
```

All of those fields are currently parsed by `src/greia_platform/activities.py`.

### Optional fields

`recommended_age_min`, `recommended_age_max`, `difficulty_min`, `difficulty_max`, `adaptive_difficulty` and `presentation.discovery_tags` are optional.

Do not add data just to fill fields. Honest unknown/open-ended metadata is better than invented precision.

## 3. Primary launcher Collections

Current platform-owned primary IDs are:

```text
create
play
learn
explore
my_greia
```

Use only the destinations that genuinely fit the Activity:

```toml
[presentation]
categories = ["create", "learn"]
```

An Activity may appear in several primary Collections without duplicating package state, saves, progression or permissions.

Package metadata does **not** create arbitrary root portals. Unknown-only valid Activities remain recoverable through Greia's platform-owned Browse/More projection.

Do not use educational taxonomy values such as `fine_motor`, `phonics`, `geometry` or `empathy` as launcher categories merely because they exist in `[education]`.

## 4. Discovery tags are hints, not folders

Current platform-owned grouping vocabulary is:

```text
drawing
writing
music
building
numbers
words
puzzles
nature
stories
making
care
action
settings
```

Example:

```toml
[presentation]
categories = ["create", "play"]
discovery_tags = ["stories", "making"]
```

Rules:

- maximum eight hints;
- each hint is a bounded lower-case semantic identifier accepted by the manifest parser;
- only platform-owned recognized group IDs can become child-facing adaptive sub-Collections;
- a tag never commands Greia to create a folder;
- a tag never defines a filesystem path;
- Activities do not own sub-Collection labels/icons/navigation depth;
- do not mechanically copy `education.categories` or skills into `discovery_tags`.

Choose a small number of strong semantic hints. One or two good hints are normally better than a bag of weak tags.

## 5. Age suitability is not difficulty

### `recommended_age_min` / `recommended_age_max`

These describe the approximate developmental/product audience the Activity was primarily designed for.

Bounds currently accepted by source:

```text
1..18
```

The minimum must not exceed the maximum when both are present.

Examples:

Early-learning Activity:

```toml
recommended_age_min = 3
recommended_age_max = 6
```

Open-ended creative Activity:

```toml
recommended_age_min = 3
```

Omitting the upper bound is appropriate when an Activity does not meaningfully become “too old” for a child.

Do **not** invent an upper age merely to make filtering look complete.

Missing age metadata means unknown/general for ordinary discovery and fails open. It is not a hidden/unsuitable marker.

### `difficulty`

`difficulty` remains the baseline challenge indicator and is validated from:

```text
1..10
```

It does not encode age.

A preschool Activity can be challenging for preschoolers and still be developmentally elementary for an older child. Conversely, an open-ended creative Activity can be easy to enter while remaining valuable for many ages.

## 6. Adaptive challenge ranges

Only use an adaptive range if the Activity genuinely supports varying challenge.

Valid example:

```toml
[education]
difficulty = 4
difficulty_min = 2
difficulty_max = 7
adaptive_difficulty = true
```

Current validation rules:

- min/max are both `1..10`;
- declare both or neither;
- `adaptive_difficulty = true` requires both bounds;
- declaring bounds requires `adaptive_difficulty = true`;
- minimum must not exceed maximum;
- baseline `difficulty` must lie inside the declared range.

Do not mark an Activity adaptive merely because future code *could* add levels. Metadata describes the Activity that actually ships.

## 7. Greia owns per-child visibility

Activity code must not privately hide itself or another Activity based on age/difficulty.

Greia computes the active child's effective visible set from platform/profile/Parent policy. Current Parent visibility modes are:

```text
show_all
hide_too_simple
recommended_only
custom
```

Current explicit per-Activity overrides are:

```text
always_show
always_hide
```

Explicit Parent overrides win over automatic age policy.

Approximate age is optional and Greia does not require a date of birth for this discovery feature.

Challenge preference is profile-level presentation/discovery preference:

```text
automatic
easier
standard
harder
```

An Activity must not treat that preference as permission to rewrite its saved progression or infer mastery.

## 8. Adaptive Collection depth is platform-owned

Grouping is computed **after** Greia has determined the effective visible Activity set for the active child.

Current initial hysteresis policy is:

```text
0..8 effective Activities  → direct Activities
9..10                      → remain direct unless this Collection was already subdivided
>10                        → evaluate semantic subdivision
```

Crossing the count threshold does not guarantee subdivision. Greia only adopts the optional layer when it can form a coherent set of useful platform-owned groups without stranding Activities in a meaningless catch-all.

Once subdivided, the Collection can remain stable through the 9–10 band and collapses at eight or fewer effective Activities.

Maximum normal discovery depth remains:

```text
Home → primary Collection → optional sub-Collection → Activity
```

Activity authors must not design deeper launcher trees.

## 9. Authoring examples

### Open-ended drawing tool

```toml
[presentation]
categories = ["create"]
discovery_tags = ["drawing", "making"]

[education]
categories = ["creativity", "art", "fine_motor"]
difficulty = 1
recommended_age_min = 3
```

No artificial upper age is needed.

### Early literacy Activity

```toml
[presentation]
categories = ["learn", "play"]
discovery_tags = ["words", "puzzles"]

[education]
categories = ["language", "phonics"]
difficulty = 3
recommended_age_min = 4
recommended_age_max = 7
```

### Genuine variable-challenge maze

```toml
[presentation]
categories = ["play", "explore"]
discovery_tags = ["puzzles", "action"]

[education]
categories = ["spatial_awareness", "problem_solving"]
difficulty = 4
recommended_age_min = 4
recommended_age_max = 9
difficulty_min = 2
difficulty_max = 8
adaptive_difficulty = true
```

## 10. Review checklist

Before accepting discovery metadata, verify:

- launcher categories use only genuine primary destinations;
- education taxonomy remains separate;
- discovery tags are few, semantic and from the platform-owned grouping vocabulary where child grouping is desired;
- age bounds are defensible and not invented;
- open-ended Activities omit arbitrary upper age bounds;
- `difficulty` represents challenge, not age;
- adaptive range exists only when the shipped Activity genuinely adapts;
- adaptive range validation is satisfied;
- Activity code contains no private per-child visibility policy;
- missing metadata remains safe/usable;
- package remains launchable independently of whether Greia ever chooses to subdivide a Collection.

## 11. Evidence boundary

Source support and committed tests are not the same as executed acceptance.

When changing these contracts, validate at least:

1. manifest parser/validation tests;
2. profile/discovery policy tests;
3. Parent API contract tests where affected;
4. launcher/catalogue tests;
5. Activity Simulator scenarios for direct/subdivided/hysteresis navigation where presentation changes.

Do not claim PASS until the relevant tests were actually executed at the exact revision under review.
