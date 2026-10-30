# Child Activity Discovery — Current Implementation Status

**Status:** source-aligned implementation checkpoint; acceptance still pending where noted  
**Date:** 2026-08-23  
**Product authority:** `docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md`  
**Source authority:** `src/greia_platform/activities.py`, `src/greia_platform/activity_discovery.py`, `src/greia_platform/profiles.py`, `src/greia_launcher/catalogue_view.py`, `src/greia_launcher/adaptive_discovery_presentation.py`, `src/greia_parent/api_server.py`

## Why this status document exists

The product/design documents for child Activity discovery were written while age metadata, discovery tags, profile audience preferences, Parent policy and adaptive sub-Collections were still targets. The implementation has now overtaken several “future/not implemented” paragraphs in those older living documents.

Until those larger documents are fully normalized, **do not use their old implementation-status sentences as source truth**. Their product intent remains authoritative; exact implemented fields/limits/behavior come from current source and are summarized here.

## Implemented manifest facts

`ActivityManifest` now parses and validates:

```toml
[presentation]
categories = ["play", "learn"]
discovery_tags = ["puzzles", "numbers"]

[education]
difficulty = 4
recommended_age_min = 5
recommended_age_max = 8
difficulty_min = 2
difficulty_max = 7
adaptive_difficulty = true
```

Current bounds/invariants:

- recommended age values: 1–18;
- baseline/adaptive difficulty values: 1–10;
- recommended minimum must not exceed maximum;
- adaptive difficulty minimum/maximum are declared together;
- an adaptive range requires `adaptive_difficulty = true`;
- `adaptive_difficulty = true` requires the range;
- baseline `difficulty` must lie inside the adaptive range;
- up to eight bounded discovery tags;
- older packages that omit these optional fields remain compatible.

Age suitability and challenge are separate facts. Missing age metadata means unknown/general and fails open for ordinary discovery.

## Implemented child-profile facts

`ChildProfile` now supports:

- optional approximate age rather than date of birth;
- challenge preference: `automatic`, `easier`, `standard`, `harder`.

These are discovery/presentation preferences. They do not grant package authority and do not rewrite Activity-owned progression.

## Implemented Parent policy

Per-child Activity discovery policy is stored separately from profile identity and exposed through the Parent API.

Current visibility modes:

```text
show_all
hide_too_simple
recommended_only
custom
```

Current explicit overrides:

```text
always_show
always_hide
```

Explicit per-Activity Parent override wins over automatic age policy.

Missing/corrupt ordinary discovery metadata must not silently erase valid Activities. Launcher policy loading fails open to the default policy while surfacing bounded catalogue error state.

Parent API capability:

```text
activities.policy
```

Resources:

```text
GET /api/v1/profiles/{profile_id}/activity-policy
PUT /api/v1/profiles/{profile_id}/activity-policy
PATCH /api/v1/profiles/{profile_id}
```

The standalone HTML Parent client now contains and loads the corresponding policy UI. Greia pins the runtime-bearing Parent client revision:

```text
d019af39119f19043b08d0de9c892fe54f152614
```

through:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

The integrity manifest includes `src/activity_policy_ui.js`; runtime network fetch remains forbidden.

## Implemented effective-catalogue order

The active child's navigation is projected in this order:

```text
validated Activity registry
    ↓
Parent per-child visibility policy + explicit overrides
    ↓
profile approximate-age/challenge discovery preference
    ↓
effective visible Activity tuple
    ↓
primary Collection projection
    ↓
adaptive direct-vs-sub-Collection planning
```

Package trust, registration, permissions, storage and launch authority are never derived from this presentation pipeline.

## Implemented adaptive depth and hysteresis

Current platform policy:

```text
0..8 effective Activities  → direct Activities
9..10                      → direct unless previously subdivided
>10                        → evaluate one semantic subdivision layer
```

Crossing 10 does not force a hierarchy. The planner subdivides only if it can form a coherent bounded set of useful groups without stranding Activities in a manufactured catch-all.

A previously subdivided Collection may stay subdivided through the 9–10 band. At eight or fewer effective Activities it collapses to direct presentation.

Normal child discovery never exceeds:

```text
Home → primary Collection → optional sub-Collection → Activity
```

## Platform-owned grouping vocabulary

Primary Collections remain:

```text
create
play
learn
explore
my_greia
```

Current platform-owned adaptive grouping vocabulary:

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

Packages may provide these as grouping hints. Packages do not manufacture arbitrary child-facing sub-Collection labels or filesystem-like paths.

## First-party catalogue migration

All current first-party Activity manifests have been classified with discovery metadata rather than leaving every Activity at an undifferentiated `difficulty = 1` baseline.

Classification policy is intentionally conservative:

- open-ended creative/general Activities do not receive arbitrary upper-age limits;
- early-learning Activities may have bounded audience ranges when defensible;
- adaptive difficulty is declared only where the shipped Activity genuinely supports varying challenge;
- discovery hints describe real semantic affinity rather than forcing every Activity into an artificial taxonomy.

## Presentation implementation

`AdaptiveActivityDiscoveryMixin` is composed into the production child Shell.

It currently provides:

- active-profile effective catalogue reload;
- policy-file change detection while the Shell is running;
- re-evaluation after Activity/profile rescans;
- one optional sub-Collection chooser;
- keyboard and pointer navigation;
- local Back from sub-Collection to primary Collection and from primary Collection toward Home;
- bounded responsive columns;
- persistent hysteresis state scoped to the child policy store;
- narrow typed fail-soft handling for optional shared visual assets rather than blanket exception suppression.

## Authoring contract

Activity authors must read:

```text
skills/greia-activity-authoring/SKILL.md
skills/greia-activity-authoring/DISCOVERY.md
```

`DISCOVERY.md` is the current source-aligned manifest guide and explicitly supersedes older “these fields are future/not parsed” implementation warnings.

## Evidence boundary

Implementation is **not the same as accepted evidence**.

Committed focused tests cover manifest/profile/policy/planner/Parent-contract behavior, but this status document does not claim they have been executed for the current exact head.

The remaining acceptance work should exercise at least:

1. direct Collection with four effective Activities;
2. direct Collection with ten effective Activities;
3. coherent subdivision when moving above ten;
4. incoherent >10 catalogue staying direct;
5. hysteresis across 10 → 11 → 10 → 9 → 8;
6. different effective counts for two child profiles over the same installed registry;
7. explicit Parent always-show/always-hide precedence;
8. missing age metadata failing open;
9. Back/keyboard/pointer behavior inside sub-Collections;
10. low-resolution and larger responsive Simulator viewports;
11. Parent HTML policy controls against the versioned API.

Do not promote committed tests or this implementation checkpoint into PASS until the corresponding commands/manual acceptance have actually run and evidence is recorded.

## Unrelated blocking platform work

This discovery implementation does not bypass or close the active R7 display/lifecycle/input platform gate. Discovery remains a projection/presentation/policy tranche over existing registry/profile seams. R7 closure requires its own evidence under the active architecture-remediation plan.
