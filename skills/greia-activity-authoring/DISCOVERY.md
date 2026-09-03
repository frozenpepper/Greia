# Greia Activity Discovery and Audience Authoring

**Status:** current source-aligned Activity-authoring contract  
**Reviewed:** 2026-09-03  
**Source authorities:** `src/greia_platform/activities.py`, `src/greia_platform/activity_discovery.py`, `src/greia_launcher/catalogue_view.py`

This file exists because discovery metadata directly affects what a parent can make visible to a child. Product intent remains owned by `docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md`; exact parser/filter behavior remains source-owned.

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

### First-party age requirement

Every first-party Greia Activity must declare a defensible:

```toml
recommended_age_min = N
```

This is not decorative metadata. Parent age presets depend on it. `tests/test_first_party_activity_audience_metadata.py` enforces the catalogue-wide rule without pinning a maximum catalogue size, so future Activities are automatically covered.

`recommended_age_max` remains optional. Open-ended creative, sensory or imaginative Activities should normally omit a fake maximum if there is no meaningful developmental upper limit.

The parser still tolerates missing age metadata for compatibility with incomplete/legacy/external material. Such unknown metadata fails open in automatic discovery and must be displayed as unknown rather than silently invented. New first-party work must not rely on that compatibility path.

`difficulty_min`, `difficulty_max`, `adaptive_difficulty` and `presentation.discovery_tags` remain optional when they are not truthful/useful.

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

For first-party Activities, do not omit the minimum. Pick the youngest age for whom the shipped interaction, instructions, concepts and motor demands are genuinely appropriate without assuming exceptional prior skill.

### `difficulty`

`difficulty` remains the baseline challenge indicator and is validated from:

```text
1..10
```

It does not encode age.

A preschool Activity can be challenging for preschoolers and still be developmentally elementary for an older child. Conversely, an open-ended creative Activity can be easy to enter while remaining valuable for many ages.

## 6. Parent age presets — source contract

Greia computes the active child's effective Activity set; Activity code never performs this filtering itself.

Canonical Parent visibility modes are:

```text
show_all
recommended_only
age_and_easier
custom
```

Their age semantics are deliberately simple and explainable.

### `recommended_only` — “Age N only”

An Activity qualifies when the child's age is inside its declared recommended range:

```text
recommended_age_min <= age <= recommended_age_max
```

A missing upper bound means open-ended, so `recommended_age_min = 3` qualifies for ages 3 and above.

### `age_and_easier` — “Age N + easier”

An Activity qualifies when its declared minimum age is not above the child:

```text
recommended_age_min <= age
```

This includes age-fit and simpler/younger material but **never** admits an Activity designed to start above the child's age. For a three-year-old, an Activity marked `4+` or `5–8` is therefore excluded.

### Compatibility

Older stored/API policy value:

```text
hide_too_simple
```

is accepted as compatibility input and immediately normalized to `age_and_easier`. New writes use only the canonical value.

### No child age

If a profile has no approximate age, automatic age filtering is inactive and fails open. The Parent client explicitly tells the parent to set an approximate age before using age presets.

Explicit per-Activity overrides remain:

```text
always_show
always_hide
```

and win over automatic age policy.

## 7. Adaptive challenge ranges

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

## 8. Challenge preference is separate

Approximate age is optional and Greia does not require a date of birth for discovery.

Challenge preference is profile-level presentation/discovery preference:

```text
automatic
easier
standard
harder
```

It influences ordering/challenge presentation within the effective catalogue; it is not the same thing as an age visibility preset.

An Activity must not treat challenge preference as permission to rewrite saved progression or infer mastery.

## 9. Adaptive Collection depth is platform-owned

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

## 10. Authoring examples

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

## 11. Review checklist

Before accepting discovery metadata, verify:

- every first-party Activity has a defensible `recommended_age_min`;
- launcher categories use only genuine primary destinations;
- education taxonomy remains separate;
- discovery tags are few, semantic and from the platform-owned grouping vocabulary where child grouping is desired;
- age bounds are defensible and not invented;
- open-ended Activities omit arbitrary upper age bounds;
- `difficulty` represents challenge, not age;
- adaptive range exists only when the shipped Activity genuinely adapts;
- adaptive range validation is satisfied;
- Activity code contains no private per-child visibility policy;
- unknown external/legacy age metadata remains explicitly unknown and safe/usable;
- package remains launchable independently of whether Greia ever chooses to subdivide a Collection.

For a target-age review, explicitly ask: “Would I intentionally offer this shipped Activity to an ordinary child at the minimum age without relying on unusual reading, motor or conceptual ability?” If not, raise the minimum instead of compensating with difficulty metadata.

## 12. Evidence boundary

Source support and committed tests are not the same as executed acceptance.

When changing these contracts, validate at least:

1. manifest/parser audience tests;
2. first-party catalogue metadata test;
3. profile/discovery policy tests;
4. Parent API policy tests;
5. Parent client tests where labels/modes changed;
6. launcher/catalogue tests if presentation changes.

Do not claim PASS until the relevant tests were actually executed at the exact revision under review.
