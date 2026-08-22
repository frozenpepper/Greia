# Greia Adaptive Activity Discovery — Engineering Handover

**Date:** 2026-08-23  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Current live head observed before this handover:** `acb7bdd550674acbd896567109975b73d38b528b`  
**Parent HTML repository:** `frozenpepper/Greia-Parent-App-Html`  
**Pinned Parent runtime revision:** `d019af39119f19043b08d0de9c892fe54f152614`  
**Status:** adaptive discovery implementation and Parent runtime integration are source-complete for the current tranche; focused and Simulator acceptance remain unexecuted evidence gates

## 1. Why this handover exists

This tranche converted the previously accepted child-discovery design into real source while other agents continued work on Teatrino, Parent-panel reliability and low-resource rendering.

All intervening commits were reconciled before writes. The latest observed post-discovery local-agent commit (`acb7bdd...`) is a direct child of the adaptive-discovery test-protocol commit and changes only:

```text
activities/teatrino_fiabe/main.py
src/greia_launcher/main.py
src/greia_launcher/parent_panel.py
```

It does not overwrite adaptive discovery source.

## 2. Implemented source architecture

### Manifest metadata

`src/greia_platform/activities.py` now owns current optional fields:

```text
presentation.discovery_tags
education.recommended_age_min
education.recommended_age_max
education.difficulty_min
education.difficulty_max
education.adaptive_difficulty
```

Bounds/invariants are source-owned and summarized in:

```text
skills/greia-activity-authoring/DISCOVERY.md
```

### Child profile

Profiles support optional approximate age and challenge preference without requiring date of birth.

Challenge vocabulary:

```text
automatic
easier
standard
harder
```

### Per-child discovery policy

`src/greia_platform/activity_discovery.py` owns:

- visibility modes;
- explicit Activity overrides;
- effective-catalogue filtering/ranking;
- atomic bounded policy persistence;
- adaptive Collection planner;
- platform-owned hysteresis state.

Visibility modes:

```text
show_all
hide_too_simple
recommended_only
custom
```

Overrides:

```text
always_show
always_hide
```

Explicit Parent override wins over automatic age policy. Missing age metadata fails open.

### Launcher projection

`src/greia_launcher/catalogue_view.py` keeps the root vocabulary platform-owned:

```text
create
play
learn
explore
my_greia
```

Current platform-owned adaptive group vocabulary:

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

Package tags are hints; packages cannot manufacture arbitrary child navigation.

### Adaptive depth

Current hysteresis policy:

```text
0..8 effective Activities  → direct
9..10                      → direct unless previously subdivided
>10                        → evaluate coherent semantic subdivision
```

Subdivision is not forced by count. It must form a useful bounded partition without stranding Activities in an artificial catch-all.

Depth is capped at:

```text
Home → primary Collection → optional sub-Collection → Activity
```

### Shell integration

`AdaptiveActivityDiscoveryMixin` is composed into `GreiaChildShell` and reloads the effective catalogue on:

- profile activation;
- policy-file change;
- Activity rescan;
- relevant profile rescan.

It renders one optional sub-Collection chooser with keyboard/pointer semantics and local Back behavior.

The optional shared-visual fallback was tightened in commit:

```text
60ca0f8acddcb00056f3228980136b66357a6591
```

It no longer blanket-catches `Exception`; it follows the established Greia visual fail-soft set plus `pygame.error`.

## 3. First-party Activity metadata

All current first-party Activity manifests were classified with real discovery facts.

Policy used:

- open-ended creative/general Activities do not get invented upper ages;
- early-learning Activities may use bounded recommended ranges;
- difficulty is challenge, never age;
- adaptive ranges are declared only where shipped Activity behavior genuinely supports different challenge levels;
- discovery tags describe real semantic affinity rather than forcing every Activity into a taxonomy.

Future Activity work must read:

```text
skills/greia-activity-authoring/SKILL.md
skills/greia-activity-authoring/CORE.md
skills/greia-activity-authoring/DISCOVERY.md
```

The new discovery guide deliberately corrects older `CORE.md`/product prose that still says these fields are future/not parsed.

## 4. Parent API and HTML client

Greia Parent API advertises:

```text
activities.policy
```

and exposes:

```text
GET /api/v1/profiles/{profile_id}/activity-policy
PUT /api/v1/profiles/{profile_id}/activity-policy
PATCH /api/v1/profiles/{profile_id}
```

The standalone Parent HTML client now loads a real Activity-policy UI. The runtime-bearing revision is:

```text
d019af39119f19043b08d0de9c892fe54f152614
```

Greia pins that exact revision through:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

The integrity manifest includes `src/activity_policy_ui.js` with exact byte count/SHA-256. Do not switch to runtime fetching from Parent `main`.

Later Parent commits add source tests/docs/handover only; they do not change the d019 runtime bytes.

Current Parent repository handover:

```text
Greia-Parent-App-Html/HANDOVER.md
```

## 5. Documentation added/updated in this tranche

Current implementation checkpoint:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_IMPLEMENTATION_STATUS.md
```

Current Activity-authoring contract:

```text
skills/greia-activity-authoring/DISCOVERY.md
```

Activity-authoring index now requires the discovery guide for manifest/discovery work:

```text
skills/greia-activity-authoring/SKILL.md
```

Exact local acceptance matrix:

```text
docs/testing/2026-08-23_ADAPTIVE_ACTIVITY_DISCOVERY_SIMULATOR.md
```

The older product/design documents retain useful design history but contain stale implementation-status sentences such as “future/not parsed”. Until they are normalized wholesale, use the new implementation-status document and exact source for current facts.

## 6. Parent client pin changes

Greia's Parent runtime pin was advanced from the previous language-enabled revision to d019 so the child Activity-policy module is actually staged.

The pin/integrity updates were committed before the later documentation work. Current live files, not remembered commit numbers, are authoritative.

Runtime integration state deliberately remains:

```text
source-pinned-not-yet-vendored
```

unless a later image-build tranche has changed that state.

## 7. Evidence boundary

### Implemented

- parser/schema fields;
- profile audience/challenge preferences;
- policy store/service;
- Parent API resources;
- Parent HTML controls;
- effective child catalogue;
- adaptive planner/hysteresis;
- launcher one-level chooser;
- first-party metadata;
- focused test source;
- local Simulator acceptance protocol.

### Not proven in this connector session

- no current-head Greia focused test execution;
- no current-head Parent `npm test` execution;
- no manual Simulator 4/10/11/20+ matrix execution;
- no manual Parent mobile/desktop policy UI acceptance;
- no real-hardware discovery/input/display acceptance.

GitHub combined-status queries for the observed current Greia and Parent heads returned no status records. No hosted workflow was triggered.

Do **not** convert committed tests into PASS.

## 8. Exact next verification

On an owner-controlled current Greia checkout:

1. read root `AGENTS.md`;
2. ensure clean/unexplained-work-safe worktree;
3. run the focused discovery/profile/catalogue/Parent source suites that exist at current HEAD;
4. execute:

```text
docs/testing/2026-08-23_ADAPTIVE_ACTIVITY_DISCOVERY_SIMULATOR.md
```

5. in the Parent HTML checkout run:

```bash
npm test
```

6. manually inspect `?demo=1` at mobile and desktop widths, including child Activity-policy controls;
7. record exact revisions and first failure.

## 9. Acceptance scenarios that must not be skipped

```text
4 effective Activities → direct
10 effective Activities → direct when fresh
11 coherent → optional sub-Collections
11 incoherent → remain direct
20+ coherent → one bounded sub-Collection layer only
10 → 11 → 10 → 9 → 8 → hysteresis then collapse
same registry + different child policy → different effective depth
always_show / always_hide → explicit precedence
missing age metadata → visible/fail-open
Back/keyboard/pointer → coherent at every layer
640×480 / 800×600 / 1024×600 / 1080p + narrow stress → usable
```

## 10. Architecture boundary

This tranche does not close or bypass R7.

Adaptive discovery is deliberately implemented in existing registry/profile/catalogue/Parent-policy seams. Package trust, runtime permissions, display-session authority, system navigation and lifecycle remain owned by their existing platform systems.

Future work must not turn adaptive Collections into filesystem folders, package-defined arbitrary navigation, deeper trees, or deterministic age gates hidden inside individual Activities.
