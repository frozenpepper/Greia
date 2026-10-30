# Greia Activity Discovery and Audience Authoring

**Status:** current source-aligned Activity-authoring contract  
**Reviewed:** 2026-10-30  
**Source authorities:** `src/greia_platform/activities.py`, `src/greia_platform/activity_discovery.py`, `src/greia_launcher/catalogue_view.py`

Discovery metadata directly affects what a parent can make visible to a child. Product intent remains owned by `docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md`; exact parser/filter behavior remains source-owned.

## 1. Keep the concepts separate

Do not collapse these into one number or taxonomy:

1. **Primary launcher Collection membership** — where the Activity may appear on Greia Home.
2. **Discovery grouping hints** — what the Activity may sensibly be grouped with.
3. **Age/developmental suitability** — who the shipped Activity is appropriate for.
4. **Difficulty/challenge** — how challenging it is within its domain.
5. **Educational skills/categories** — what learning/progression facts it contributes.

Age is not difficulty, and discovery tags are not educational taxonomy or folders.

## 2. First-party age metadata is mandatory

Every first-party Greia Activity must declare a defensible minimum age:

```toml
[education]
difficulty = 3
recommended_age_min = 3
```

This is product metadata, not decoration. Parent age presets depend on it.

`tests/test_first_party_activity_audience_metadata.py` discovers the complete first-party catalogue and requires `recommended_age_min` for every Activity without pinning a catalogue count.

Choose the youngest ordinary child for whom the **actual shipped interaction** is suitable, considering:

- concepts/prerequisite knowledge;
- ability to understand the spoken/visual instructions;
- reading assumptions;
- working-memory load;
- number of simultaneous choices;
- fine-motor/precision demands;
- pace and interaction complexity.

Do not lower the age because the art looks preschool-oriented. Do not hide an age mismatch inside `difficulty`.

`recommended_age_max` is optional. For genuinely open-ended creative, sensory or imaginative Activities, omit a fake upper limit rather than inventing one for symmetry:

```toml
recommended_age_min = 3
```

A bounded curricular Activity may instead use:

```toml
recommended_age_min = 3
recommended_age_max = 6
```

The parser accepts age bounds in `1..18`, with minimum not exceeding maximum.

## 3. Compatible unknown-age packages

The manifest parser still tolerates missing age metadata for compatible legacy/external packages.

That does **not** mean an unknown-age Activity may be silently classified as suitable for a restrictive Parent age preset.

Current rule:

```text
All age ranges / Custom
    unknown-age Activity may remain available

Age N only / Age N + easier
    wholly unknown age metadata is NOT automatically included

Always show
    parent may deliberately expose it

Always hide
    parent may deliberately hide it
```

The Parent UI displays wholly missing metadata as `Age not specified` rather than inventing `All ages`.

## 4. Parent age presets

Greia computes the effective Activity set. Activity code and the Parent browser must not create private competing age engines.

Canonical modes are:

```text
show_all
recommended_only
age_and_easier
custom
```

### `recommended_only` — “Age N only”

The Activity must have declared age metadata, and the declared range must contain the child age:

```text
minimum is absent or minimum <= age
AND
maximum is absent or age <= maximum
```

A first-party `3+` Activity therefore qualifies at age 3 and later. A `4+` Activity does not qualify for age 3.

### `age_and_easier` — “Age N + easier”

The Activity must have declared age metadata and its declared minimum must not be above the child:

```text
minimum is absent or minimum <= age
```

This deliberately allows simpler/younger Activities even when their declared maximum is below the child age, but it never automatically admits an Activity designed to start above the child's age.

For a three-year-old, `4+` and `5–8` are excluded.

### Compatibility

Old stored/API value:

```text
hide_too_simple
```

is compatibility input only. It normalizes immediately to `age_and_easier`; new stored/API output uses the canonical value.

### No child age

If the profile has no `approximate_age`, automatic age filtering is inactive. The Parent app disables the age-specific choices and tells the parent to set an approximate age in Children.

## 5. Difficulty stays independent

`education.difficulty` is `1..10` and describes baseline challenge, not age.

An Activity can be appropriate for age 3 and still be relatively challenging for a three-year-old. Conversely, a 5+ Activity with difficulty 1 does not become appropriate for age 3 merely because it is easy within its intended domain.

For genuinely adaptive Activities only:

```toml
[education]
difficulty = 4
difficulty_min = 2
difficulty_max = 7
adaptive_difficulty = true
```

Rules:

- declare both bounds or neither;
- bounds are `1..10`;
- baseline difficulty lies inside the range;
- range requires `adaptive_difficulty = true`;
- do not claim adaptability the shipped Activity does not implement.

Parent difficulty filtering is an additional independent dimension after explicit visibility overrides.

## 6. Primary launcher Collections

Platform-owned primary IDs are:

```text
create
play
learn
explore
my_greia
```

Example:

```toml
[presentation]
categories = ["create", "learn"]
```

An Activity may appear in multiple Collections without duplicating package state, saves, progression or permissions.

Do not use educational taxonomy values such as `phonics`, `geometry` or `empathy` as launcher categories merely because they exist in `[education]`.

Unknown-only valid package categories do not manufacture new Home destinations; platform Browse/More remains the bounded recovery path.

## 7. Discovery tags are hints, not folders

Current recognized grouping vocabulary:

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

Use a few strong semantic hints. A tag:

- never creates a filesystem path;
- never commands Greia to create a folder;
- never owns a child-facing label/icon;
- never creates deeper launcher hierarchy;
- should not be a mechanical copy of `education.categories`.

Adaptive grouping is computed by Greia after the effective per-child Activity set is known.

Normal depth remains:

```text
Home -> primary Collection -> optional sub-Collection -> Activity
```

## 8. Authoring examples

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

### Variable-challenge maze

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

## 9. Review checklist

Before accepting a first-party Activity, verify:

- `recommended_age_min` exists and is defensible;
- an upper age exists only when meaningful;
- age reflects the shipped cognitive/motor/language demands;
- difficulty reflects challenge, not age;
- launcher categories are genuine platform destinations;
- discovery tags are few and semantic;
- adaptive difficulty is declared only when actually implemented;
- Activity code contains no private per-child visibility policy;
- restrictive Parent age presets cannot auto-include wholly unknown age metadata;
- explicit Parent `always_show` / `always_hide` remains authoritative.

Ask explicitly:

> Would I intentionally offer this exact shipped Activity to an ordinary child at the declared minimum age without relying on unusual reading, motor or conceptual ability?

If not, raise the minimum instead of compensating elsewhere.

## 10. Evidence

When these contracts change, validate at least:

1. manifest/parser audience tests;
2. first-party catalogue metadata test;
3. discovery-policy tests;
4. Parent API policy tests;
5. maintained Parent-client tests where labels/modes changed;
6. the active cross-repository age-policy acceptance procedure.

A committed test is not a PASS. Do not claim acceptance until the exact-current procedures actually execute.
