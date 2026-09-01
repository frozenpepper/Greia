# Greia Parent Controls: Usage Limits and Activity Visibility

Status: focused feature design and implementation note, 2026-09-01

This document is subordinate to the repository's authoritative architecture/remediation plan and to ADR 0022 (`parent-management-api-client-pairing-and-privilege-boundary`). It does **not** move or waive the active R7 hardware-acceptance gate and it does **not** declare the later R12 parent-management phase complete.

## 1. Goal

Make ordinary parent administration understandable without weakening Greia's platform boundaries.

The concrete parent jobs are:

1. choose a child profile and adjust age/challenge preferences;
2. decide which Activities that child can discover;
3. explicitly hide or show any individual Activity;
4. understand Activity age/difficulty metadata without knowing internal IDs;
5. set a daily Greia-use budget for the whole computer and/or one child;
6. let the child see a calm, understandable indication of remaining time on the home screen when a finite budget exists;
7. enforce those choices in the platform, not merely in browser JavaScript.

The Parents web application is a client. It is never the authority for visibility, time accounting, process termination, package trust, or privileges.

## 2. Existing Greia capabilities reused

This work intentionally reuses mechanisms already present in the repository.

### 2.1 Child profile metadata

`greia_platform.profiles` already owns:

- `approximate_age` (1..18 or unknown);
- `challenge_preference` (`automatic`, `easier`, `standard`, `harder`);
- child-facing letter-case preference;
- profile identity and managed profile directories.

No second parent-profile database should be introduced.

### 2.2 Activity audience metadata

`ActivityManifest` already carries:

- `recommended_age_min` / `recommended_age_max`;
- `difficulty`;
- optional `difficulty_min` / `difficulty_max`;
- `adaptive_difficulty`;
- categories and semantic discovery tags.

Missing audience metadata intentionally fails open. A package is not hidden merely because an older manifest lacks age metadata.

### 2.3 Authoritative Activity visibility

`ActivityDiscoveryPolicyStore` already persists per-profile visibility policy, including automatic modes and explicit `always_show` / `always_hide` overrides.

`ActivityDiscoveryService` computes the effective Activity set.

The launcher adaptive-discovery presentation consumes that effective set and watches the policy file for changes. Therefore an `always_hide` decision already removes the Activity from the child-facing catalogue without rebooting or changing package installation/trust.

This is the correct enforcement primitive. Do not add a separate `disabled_activities.json`, CSS hiding, or launcher exception list.

### 2.4 Versioned Parent API

The Parent API already exposes:

- profiles;
- Activity metadata;
- per-profile Activity policy;
- hardware/admin state.

The web client must continue to use `/api/v1`; it must not invoke shell commands or write platform files directly.

## 3. Parent web UX

The fallback dependency-free client has been reorganized around four ordinary parent concepts:

- **Children** — profile identity, approximate age, challenge preference, text style;
- **Activities** — automatic visibility and per-Activity overrides;
- **Device** — system facts and hardware controls;
- **Parent access** — paired devices/password and administrative capabilities.

### 3.1 Selected-child model

A parent selects one child at the top of Children or Activities. All child-specific controls visibly apply to that child. Do not hide scope in a modal or require the parent to infer it from URLs.

### 3.2 Activity cards

Each card should expose, where available:

- human-readable Activity name/identifier;
- whether the child currently sees it;
- recommended age range;
- nominal difficulty, or adaptive difficulty range;
- top presentation categories;
- explicit selector:
  - `Automatic`;
  - `Always show`;
  - `Hide from child`.

The current implementation uses the existing Parent API `activity-policy` endpoint. The displayed `Shown to child` / `Hidden from child` state comes from `effective_activity_ids`, not from reconstructing the platform policy in JavaScript.

### 3.3 Automatic age modes

Expose the platform modes in parent language:

- **Show all Activities** (`show_all`);
- **Show only Activities recommended for this age** (`recommended_only`);
- **Hide Activities marked too young** (`hide_too_simple`);
- **Only use my explicit per-Activity choices** (`custom`).

Explicit `always_hide` and `always_show` choices retain their existing precedence.

### 3.4 Parent-side browsing filters vs child policy

Search, age-metadata and difficulty selectors in the browser are *management-list filters*: they help a parent find Activities to configure. They must not pretend to be policy if the platform did not persist that policy.

A future difficulty-policy extension should be declarative in `ActivityDiscoveryPolicy`, not implemented by silently expanding a difficulty choice into hundreds of per-Activity overrides. This avoids destroying a parent's explicit exceptions and gives newly installed Activities predictable behavior.

Recommended extension:

- nullable `difficulty_min` and `difficulty_max` in `ActivityDiscoveryPolicy`;
- bounds match the Activity manifest difficulty vocabulary;
- base automatic visibility first applies age mode, then the declared difficulty interval;
- `always_hide` remains strongest;
- `always_show` overrides automatic age/difficulty filtering;
- schema migration must accept current schema-1 policy files without losing adaptive collection state.

Do this only with corresponding platform/API/launcher tests. It is not required for the first web-client improvement commit.

## 4. Usage-limit semantics

### 4.1 What is counted in v1

The first limit is **daily child Activity time**.

Count time from authoritative Activity lifecycle ownership, using monotonic elapsed time. Do **not** count:

- boot time;
- profile chooser time;
- time sitting on the Greia home/catalogue screen;
- parent-management time;
- wall-clock seconds supplied by an Activity.

This definition is deliberate. It is cheap, deterministic on Acer Aspire One-class hardware, maps to Greia's existing one-Activity supervisor, and avoids penalizing a child who is deciding what to play.

If a later product decision wants full signed-in session time, add a separate counting mode and a shell/session owner. Do not silently change the meaning of existing budgets.

### 4.2 Scopes

Support two independent optional policies:

- **Device daily limit** — shared Activity-time budget across all child profiles on this Greia;
- **Profile daily limit** — Activity-time budget for one child profile.

`null` means unlimited.

If both are finite, the effective remaining time is the smaller remaining budget.

Example:

- device: 90 min/day, 40 min already used by all children;
- Gaia: 30 min/day, 10 min already used by Gaia;
- effective Gaia remaining = `min(50, 20) = 20 min`.

There is no loophole from switching profiles because the device counter is shared.

### 4.3 Persistence and clocks

Implemented foundation: `src/greia_platform/usage_limits.py`.

It provides:

- `UsageLimitPolicy`;
- `UsageLimitStore` with bounded atomic JSON and managed `0660` mode;
- `UsageLimitService` for device/profile policies, status, and elapsed-time accounting;
- daily accounting buckets with bounded history;
- clock-rollback protection: a calendar date older than the newest accounting date does not create a fresh budget.

Elapsed seconds passed to `record_activity_time()` must come from a monotonic lifecycle clock. Calendar time is used only to choose the daily bucket.

The storage path must be injected by composition. Do not hard-code a privileged path in the service class.

### 4.4 Crash/reboot behavior

The lifecycle integration should checkpoint usage periodically while an Activity is running, not only at clean exit. A useful first value is every 15 seconds and at all terminal/stop transitions. This limits lost accounting after power failure while keeping disk writes tiny.

The checkpoint code should record only newly elapsed whole seconds since the previous checkpoint. Never repeatedly add total session duration.

### 4.5 Enforcement

Enforcement belongs at the authoritative launch/lifecycle boundary.

Before launch:

1. resolve the child profile;
2. obtain `UsageLimitStatus`;
3. if exhausted, refuse the Activity start and remain/return on child home;
4. present a friendly `time finished for today` state from the shell, not a Python traceback.

While running:

1. supervisor/lifecycle owner periodically checkpoints monotonic elapsed seconds;
2. read the returned effective remaining value;
3. at zero, request graceful Activity stop;
4. after the existing bounded graceful-stop interval, use the normal lifecycle forced-stop path if needed;
5. normalize cleanup/display restoration exactly as any other Activity termination.

Do not give the usage-limit module direct process-killing, display, or sandbox authority.

A dedicated normalized exit reason such as `USAGE_LIMIT_REACHED` is preferable if adding it can be done without breaking current lifecycle consumers/history; otherwise preserve a separate platform event/status while using the normal parent-requested graceful stop. Decide with tests before expanding enums.

## 5. Child home-screen time indicator

Yes: tie a home-screen indicator to finite limits, but keep it calm and legible.

### 5.1 Display rules

- Unlimited: show no countdown at all.
- Finite budget: show remaining approximate time, e.g. `42 min left today`.
- Over one hour: `1 h 20 min left today`.
- Under ten minutes: still show whole minutes; do not create an anxiety-producing seconds countdown.
- Zero: replace the countdown with a friendly finished-for-today state and disable Activity launch affordances.

### 5.2 Warning thresholds

Recommended child-facing transitions while an Activity is running:

- 15 minutes: optional soft/non-modal notice;
- 5 minutes: clear soft notice;
- 1 minute: clear final notice;
- zero: graceful return home.

No alarm sound by default. If voice guidance is added, use a short prerecorded Greia system/character utterance; no on-device neural TTS requirement.

### 5.3 Data flow

The home UI should consume a small platform-owned usage-status presentation model. It should not parse the JSON ledger itself.

Suggested read model fields:

- `limited: bool`;
- `remaining_seconds: int | None`;
- `exhausted: bool`;
- `accounting_date`;
- `next_display_refresh_seconds` (optional presentation hint).

Refresh on:

- profile selection;
- return from Activity;
- parent policy file/state change;
- a low-frequency home timer (30–60 s is enough for whole-minute display).

## 6. Parent API shape for usage limits

When wiring the foundation into the Parent API, keep the surface boring and explicit.

Recommended routes:

- `GET /api/v1/usage-limits`
  - device policy and current device usage;
- `PUT /api/v1/usage-limits`
  - `{ "daily_minutes": 90 }` or `{ "daily_minutes": null }`;
- `GET /api/v1/profiles/{profile_id}/usage-limit`
  - profile policy plus effective/device/profile remaining facts;
- `PUT /api/v1/profiles/{profile_id}/usage-limit`
  - `{ "daily_minutes": 45 }` or `{ "daily_minutes": null }`.

All routes require the normal Parent API authorization. Validate profile existence before accepting a per-profile policy. Never return or accept arbitrary filesystem paths.

A future schedule/bedtime feature should be a separate policy concept rather than overloading `daily_minutes`.

## 7. Parent web usage-limit UX

Once the API/lifecycle path is wired and tested, add to the Children page:

- **Daily Activity time**: Unlimited / 15 / 30 / 45 / 60 / 90 / 120 / Custom minutes;
- summary: `18 min used · 27 min left today`;
- if device limit is also restricting the child, explain it: `This Greia has 12 min left for everyone today`.

Add to Device:

- **Shared daily Activity time**: same presets/custom input;
- summary of shared use today.

Do not offer a control before its API/enforcement path exists. Disabled mock controls are worse than an honest unavailable feature.

## 8. Security and ownership invariants

1. Browser UI never writes profile/policy/ledger files directly.
2. Parent API remains authenticated per ADR 0022.
3. Usage limits grant no package, root, update, network, or sandbox authority.
4. Activity visibility changes discovery only; they do not uninstall packages or change package trust.
5. Activities cannot reset, pause or credit their own time.
6. Activities cannot learn or mutate another profile's budget through their sandbox API.
7. Time accounting uses platform lifecycle observations, not Activity claims.
8. Missing/corrupt policy must follow an explicit safe behavior and emit diagnostics; never silently invent restrictive data that strands the child UI.
9. Existing R7/R12 phase gates remain intact.

## 9. Implementation status on `feature/parent-controls-foundation`

Implemented in this slice:

- redesigned dependency-free Parent web fallback;
- selected-child workflow;
- profile age/challenge editing;
- Activity search and metadata filters;
- authoritative effective-visible count;
- per-Activity `Automatic` / `Always show` / `Hide from child` control using the existing platform policy;
- automatic age-policy selector using the existing discovery modes;
- `UsageLimitPolicy`, atomic store, service/status/accounting foundation;
- unit tests for limits, precedence, persistence, day rollover and clock rollback.

Not yet claimed complete:

- Parent API routes for usage limits;
- supervisor launch blocking/checkpoint/zero-time stop integration;
- child home-screen remaining-time indicator;
- child-facing warning presentation;
- declarative difficulty-range policy;
- physical-device/browser acceptance;
- R7 or R12 phase acceptance.

The local-agent runbook created with this feature is the required next validation/continuation step.

## 10. Acceptance criteria for the completed feature

The feature is complete only when all are true:

1. parent can set/clear device and per-profile daily Activity limits;
2. both policies persist over reboot;
3. most restrictive finite budget wins;
4. device budget is shared across profiles;
5. exhausted profile cannot launch an Activity;
6. running Activity exits through normal lifecycle cleanup when budget reaches zero;
7. abrupt reboot can lose at most one checkpoint interval of counted time;
8. moving the wall clock backwards does not grant a fresh budget;
9. new day produces a fresh budget without deleting historical state immediately;
10. finite remaining time appears on child home and updates after Activity return/parent change;
11. unlimited state shows no unnecessary clock;
12. explicit hidden Activity disappears from launcher without reboot;
13. explicit always-show Activity can override automatic age/difficulty filtering;
14. parent web UI remains usable at phone and desktop widths;
15. no Activity/package trust, sandbox, privilege or lifecycle regression;
16. `make verify` is green;
17. required real-hardware acceptance from the active repository plan remains separately satisfied before release claims.
