# Greia Child Activity Discovery and Audience Requirements

**Status:** accepted product requirement  
**Reviewed:** 2026-09-04  
**Scope:** child Shell/Home, Activity catalogue projection, audience/challenge metadata, child-profile discovery preferences, Parent per-child Activity visibility policy  
**Source owners:** `src/greia_platform/activities.py`, `src/greia_platform/activity_discovery.py`, `src/greia_launcher/activity_policy_presentation.py`, `src/greia_launcher/child_shell.py`, `src/greia_launcher/trusted_presentation.py`, `src/greia_launcher/catalogue_view.py`, `src/greia_parent/api_server.py`

## 1. Product intent

Greia must remain easy for a child to navigate with a small or large installed Activity catalogue, while giving parents a simple trustworthy way to decide what is appropriate for each child.

Normal child discovery remains Collection-first:

```text
Greia Home
  -> primary Collection
    -> Activity
```

When a Collection becomes dense and a coherent platform-owned semantic grouping exists, Greia may add exactly one optional grouping layer:

```text
Greia Home
  -> primary Collection
    -> optional sub-Collection
      -> Activity
```

Collections are child-facing navigation concepts, never filesystem folders.

## 2. Primary Collections are platform-owned

Normal primary destinations are:

```text
create
play
learn
explore
my_greia
```

`All` is an internal/Parent/admin/browse projection, not a normal child Home destination.

An Activity may belong to more than one Collection without duplicating installation, saves, permissions, progression or identity.

Package metadata cannot manufacture arbitrary new root destinations. A valid Activity with no recognized primary Collection remains recoverable through the bounded platform-owned Browse/More path rather than disappearing.

## 3. Effective catalogue is computed per child

Greia reasons about the **effective visible Activity set**, not merely the raw installed set:

```text
validated installed registry
  -> Parent per-child visibility policy / explicit overrides
  -> profile age + challenge presentation policy
  -> effective visible Activities
  -> Collection projection / optional semantic subdivision
```

The per-child policy projection is mandatory launcher authority. Every installed child launcher composition that can expose an Activity for launch must consume it, including the emergency trusted presentation used when the richer child Shell exits.

The normal rich Shell may add adaptive sub-Collections only **after** visibility projection. The trusted emergency fallback intentionally stays direct/non-adaptive, but it receives the same Parent visibility, age and difficulty projection before presenting any Activity. A fallback path must never reconstruct a raw unfiltered catalogue merely because richer presentation failed.

Launcher selection is also constrained by this projected catalogue: presentation chooses an Activity from the effective set, then resolves that Activity identity back to the validated registry for launch. Visibility filtering therefore does not replace registry/runtime/trust authority, but a hidden Activity cannot be selected merely by entering a different launcher composition.

Visibility filtering never changes package trust, installation, permissions, saves or Activity identity.

Activity code does not decide whether itself or another Activity is visible to a child.

## 4. Age suitability and difficulty are independent

Age/developmental suitability answers:

> Who was this exact shipped Activity designed to be suitable for?

Difficulty answers:

> How challenging is it within its intended content/audience domain?

They must never be collapsed into one number.

Current manifest shape:

```toml
[education]
difficulty = 3
recommended_age_min = 3
recommended_age_max = 6
```

`difficulty` is `1..10`.

Age bounds are `1..18`, and minimum must not exceed maximum when both exist.

### First-party requirement

Every first-party Greia Activity must declare a defensible:

```toml
recommended_age_min = N
```

The complete first-party catalogue is regression-checked for this requirement.

The minimum is the youngest ordinary child for whom the **actual shipped interaction** is appropriate considering concepts, language/reading assumptions, working-memory load and motor demands.

`recommended_age_max` remains optional. Open-ended creative/sensory/imaginative Activities should not receive a fake upper age merely to make the metadata symmetrical:

```toml
recommended_age_min = 3
```

means `3+`.

## 5. Adaptive challenge is separate from age

A genuinely variable-challenge Activity may declare:

```toml
[education]
difficulty = 4
difficulty_min = 2
difficulty_max = 7
adaptive_difficulty = true
```

The baseline must lie inside the range. Both bounds are declared together and are `1..10`.

Do not mark an Activity adaptive merely because future code could add levels.

A low difficulty does not make an older-audience Activity suitable for a younger child, and a high difficulty does not change the Activity's intended developmental audience.

## 6. Child profile information

A child profile may contain:

```text
approximate_age: optional integer 1..18
challenge_preference: automatic / easier / standard / harder
```

Greia does not require an exact date of birth for Activity discovery.

Challenge preference influences ordering/challenge presentation inside the effective catalogue. It is not an age filter and is not a mastery assessment.

## 7. Parent age presets

Parent authority can apply stronger per-child visibility rules.

Canonical modes are:

```text
show_all
recommended_only
age_and_easier
custom
```

### `show_all` — “All age ranges”

No automatic age restriction is applied. Difficulty bounds and explicit per-Activity overrides may still apply.

### `recommended_only` — “Age N only”

An Activity is automatically visible only when it has declared audience metadata and the child's approximate age is inside its declared range:

```text
(minimum absent OR minimum <= age)
AND
(maximum absent OR age <= maximum)
```

Examples for age 3:

```text
2–5     visible
3–3     visible
3+      visible
4+      hidden
5–8     hidden
unknown hidden automatically
```

### `age_and_easier` — “Age N + easier”

An Activity is automatically visible only when it has declared audience metadata and its declared minimum age is not above the child:

```text
minimum absent OR minimum <= age
```

This intentionally includes simpler/younger material even if a declared upper age is below the child. It never automatically admits an Activity explicitly designed to start above the child's age.

For age 3, a `4+` or `5–8` Activity is hidden automatically.

### `custom`

Age automation is not used. The parent manages explicit Activity choices.

### Explicit overrides

Per-Activity overrides are:

```text
always_show
always_hide
```

They are evaluated before automatic age/difficulty policy and therefore remain authoritative.

This is also the deliberate escape hatch for a compatible Activity whose age metadata is unknown.

## 8. Unknown/missing audience metadata

Compatible legacy or third-party packages may have no age metadata. Greia does not invent an age for them.

Rules:

```text
All age ranges / Custom
    unknown-age content may remain available

Age N only / Age N + easier
    wholly unknown age metadata is not automatically included

Always show
    parent may deliberately expose it
```

The Parent UI describes wholly missing metadata as `Age not specified`, not `All ages`.

This distinction is important: an Activity being valid/installable is not evidence that it is developmentally appropriate for a specific age.

If the child profile itself has no approximate age, automatic age filtering is inactive. The Parent UI must make that clear rather than pretending a specific-age preset is meaningful.

### Invalid stored policy is different from a missing policy

The absence of a per-child discovery-policy file is a legitimate state. `ActivityDiscoveryPolicyStore.read()` resolves that absence to the normal default policy.

A policy path that exists but cannot be trusted is not the same state. Malformed JSON, an unsupported schema, an unreadable policy file, or a symlink policy is invalid Parent authority and must fail closed:

```text
missing policy
    -> legitimate default policy

valid policy
    -> apply Parent visibility / age / difficulty intent

invalid existing policy
    -> zero launchable Activities until repaired
    -> keep Shell/profile/recovery presentation alive
    -> never reinterpret corruption as SHOW_ALL
```

Both the normal child Shell and the trusted emergency fallback use this rule. When the policy is repaired through the supported authority path, normal rescan/reload must detect the replacement and restore the effective catalogue without widening policy during the broken interval.

## 9. Compatibility with old saved policy

Older persisted/API value:

```text
hide_too_simple
```

is compatibility input only. Current source normalizes it to:

```text
age_and_easier
```

New writes and new UI use only the canonical mode.

The schema also still accepts historical `subdivided_collections` values produced by older launcher versions. Those values are **presentation compatibility state, not Parent visibility authority**. The current rich child Shell may use them once as an in-memory hysteresis seed when a profile activates, but it must not write adaptive grouping state back into the Parent policy file. Parent visibility/age/difficulty updates must never be overwritten by stale launcher presentation state.

## 10. Discovery tags and adaptive depth

Presentation metadata may provide semantic grouping hints:

```toml
[presentation]
categories = ["create", "learn"]
discovery_tags = ["drawing", "making"]
```

Tags are hints, not folders or authority to create navigation levels.

Current adaptive Collection policy is:

```text
1–8 effective Activities  -> direct
9–10                      -> direct unless previously validly subdivided
>10                        -> evaluate one semantic subdivision layer
```

Subdivision occurs only when a coherent platform-owned grouping covers the Collection usefully. Crossing the numeric threshold alone does not force it.

Adaptive subdivision hysteresis for the active child session is launcher-owned in-memory presentation state. It is deliberately downstream of the stable Parent policy snapshot. The Shell must not perform a read-modify-write of Parent policy merely to remember grouping shape; otherwise a concurrent Parent `always_hide`, age mode, or difficulty update could be lost.

Maximum normal depth remains:

```text
Home -> primary Collection -> optional sub-Collection -> Activity
```

## 11. Responsive and input requirements

The discovery model must remain usable on the Acer-class 1024×600 floor and larger displays:

- bounded Home choices;
- no giant flat application wall;
- Activity/Collection lists reflow from the viewport;
- no device-specific hardcoded category layouts;
- pointer, keyboard, touch and controller use the same semantic navigation state;
- Back/launch origin remain coherent across input methods.

## 12. Safety/authority boundaries

Age metadata is developmental/product suitability inside Greia's curated ecosystem. It is **not** PEGI/ESRB/legal content rating, permission authority or parental-consent machinery.

Package trust, permissions, child safety, installation authority and age suitability remain separate concerns.

Parent Activity visibility is nevertheless a child-facing safety/authority boundary once configured. A degraded presentation path may simplify layout, but it may not become more permissive than the Parent-owned policy because another launcher composition is running.

## 13. Acceptance requirements

The living implementation must prove at least:

1. every first-party Activity has `recommended_age_min`;
2. open-ended Activities are not forced to invent `recommended_age_max`;
3. `recommended_only` means declared range contains the child age;
4. `age_and_easier` never automatically admits an Activity whose declared minimum is above the child age;
5. wholly unknown age metadata is excluded from restrictive automatic age presets;
6. explicit `always_show` / `always_hide` wins;
7. old `hide_too_simple` input migrates to `age_and_easier`;
8. age and difficulty remain independent;
9. a missing child age does not pretend to apply age filtering;
10. Parent UI exposes understandable age labels and presets;
11. effective per-child filtering occurs before adaptive Collection projection;
12. presentation filtering never bypasses registry/runtime/trust/permission authority;
13. responsive and input behavior remains usable on supported Greia viewports;
14. the normal rich child Shell and trusted emergency fallback enforce the same Parent visibility/age/difficulty authority before exposing Activities;
15. invalid existing policy data exposes zero launchable Activities in both paths and a supported repair is detected without a permissive fallback interval;
16. an atomic policy replacement during a launcher read cannot be acknowledged under the wrong snapshot;
17. adaptive subdivision hysteresis does not write Parent policy or clobber a concurrent Parent visibility/age/difficulty update.

The exact current local/browser procedures are:

```text
docs/testing/2026-09-03_ACTIVITY_AGE_POLICY_ACCEPTANCE.md
docs/testing/2026-09-04_CHILD_ACTIVITY_POLICY_FAIL_CLOSED_ACCEPTANCE.md
```

Committed source/tests do not by themselves constitute acceptance evidence.
