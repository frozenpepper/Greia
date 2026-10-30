# Activity Age Policy + Parent Preset Acceptance — 2026-09-03

**Status:** exact-current local acceptance procedure  
**Scope:** first-party Activity age metadata, Greia discovery semantics, Parent API policy, maintained HTML Parent client (`parent-app/`, same repository since 2026-10-30; see `parent-app/AGENTS.md`)  
**Do not use GitHub-hosted Actions for this procedure.**

## 0. Purpose

Prove that Greia can reliably offer parents age-based Activity visibility without confusing age with difficulty.

Required product behavior:

```text
Age N only
  -> only Activities whose declared recommended range contains N
  -> wholly unknown age metadata is not automatically included

Age N + easier
  -> Activities with declared audience metadata whose declared minimum age is <= N
  -> must never automatically include an Activity whose minimum age is > N
  -> wholly unknown age metadata is not automatically included

All age ranges
  -> no automatic age restriction

Custom choices
  -> explicit per-Activity choices remain authoritative
```

Every first-party Activity must declare `recommended_age_min`. `recommended_age_max` remains optional for genuinely open-ended Activities.

Compatible third-party/legacy Activities may still have missing age metadata. They remain installable and visible under unrestricted policy, but a restrictive age preset must not silently classify them as age-suitable. A parent may deliberately expose one with `Always show`.

Legacy persisted/API value `hide_too_simple` must remain readable but normalize to canonical `age_and_easier`.

## 1. Prerequisites

Use an existing clean local clone of `frozenpepper/Greia`. The browser Parent client is its `parent-app/` directory (it was the separate `Greia-Parent-App-Html` repository until 2026-10-30), so one checkout covers both.

Do not install new packages, edit source, regenerate assets, repair failures or run hosted CI inside this gate.

Required existing tools:

```text
python3
node
npm
Git
```

If the repository is missing, dirty before the gate, or cannot fast-forward to current `origin/main`, STOP and report that condition. Do not discard local work.

## 2. Freeze exact revisions

In Greia:

```bash
cd /path/to/Greia
git fetch origin
git switch main
git pull --ff-only origin main
git status --short
git rev-parse HEAD
git rev-parse origin/main
```

Require:

```text
git status --short -> empty
HEAD == origin/main
```

Record:

```text
GREIA_AGE_POLICY_SHA=<full SHA>
```

Record the pinned Parent client revision (the git tree id of `parent-app/`) and confirm the pin is in sync:

```bash
git rev-parse HEAD:parent-app
python3 tools/update_parent_client_pin.py --check
```

Record:

```text
PARENT_AGE_POLICY_SHA=<git rev-parse HEAD:parent-app>
```

If `main` advances during this procedure, complete the current command only, mark the result STALE, and restart from §2 on the new exact heads before claiming PASS.

## 3. Greia focused source tests

From Greia root run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_activity_audience_manifest \
  tests.test_activity_discovery_policy \
  tests.test_first_party_activity_audience_metadata \
  tests.test_parent_activity_policy
```

Required: exit 0, no failures/errors.

This must prove at least:

- first-party minimum-age metadata gate applies to the complete current catalogue;
- `recommended_only` means declared range contains child age;
- `age_and_easier` excludes future-minimum-age Activities;
- wholly unknown age metadata is excluded from both restrictive automatic presets;
- explicit `always_show` can deliberately expose an unknown-age Activity and `always_hide` remains authoritative;
- old `hide_too_simple` storage/API input migrates to `age_and_easier`;
- difficulty bounds remain independent from age suitability.

On any failure: STOP. Preserve the complete failure text. Do not edit code in this gate.

## 4. Greia broader regression

Still from Greia root:

```bash
make verify
```

Record the exact fresh test count and final result.

Required: PASS.

If it fails, STOP and return the first failing command/test with its complete traceback/output. Do not continue into Parent acceptance and do not repair inline.

## 5. Parent client full automated tests

From the Greia repository root:

```bash
make parent-app-test        # node --test parent-app/tests/*.test.js
```

Required: exit 0, all Node tests PASS.

The suite must include the age-policy coverage added to:

```text
parent-app/tests/demo_management.test.js
parent-app/tests/product_surface.test.js
```

The demo-management test must include an Activity with both age bounds missing and prove that restrictive age presets exclude it until `Always show` is applied.

On failure: STOP and preserve the first failure.

## 6. Parent visual/interaction review on localhost demo

Serve the Parent app locally using its existing command:

```bash
cd parent-app && npm run serve
```

Open:

```text
http://127.0.0.1:8080/?demo=1#activities
```

Use the existing demo child profiles. Temporarily edit one child through the normal UI so its approximate age is **3**, then return to Activities.

Visually verify the Age guidance selector presents:

```text
All age ranges
Age 3 only
Age 3 + easier
Custom choices
```

Verify Activity rows display honest audience labels such as:

```text
Age 3+
3–8 years
Age not specified   (when the unknown-metadata fixture is present)
```

Select `Age 3 only`, save, and verify:

- the visible/hidden badges update after refresh;
- no Activity with wholly unknown age metadata is automatically visible;
- no Activity whose displayed range excludes age 3 is automatically visible;
- there are no browser-console errors.

Select `Age 3 + easier`, save, and verify:

- no Activity with a displayed minimum age above 3 becomes automatically visible;
- an Activity with wholly unknown age metadata remains hidden automatically;
- an explicit `Always show` can deliberately expose that Activity.

Set one known-age Activity to `Always show` and another to `Hide from child`; verify those explicit choices win over the selected age preset.

## 7. No-age UX

Edit a demo child so approximate age is unset, then return to Activities.

Verify:

- the two age-specific preset options are disabled;
- the page explicitly says to set an approximate age in Children;
- the UI does not imply an age filter is active;
- `All age ranges`, difficulty bounds and individual Activity choices remain usable.

## 8. Responsive smoke review

At minimum inspect:

```text
desktop viewport
1024×600 viewport
narrow mobile viewport
```

Required:

- Age guidance selector remains reachable/readable;
- help copy does not force horizontal page overflow;
- Activity age labels remain legible;
- save controls remain reachable;
- browser console has zero errors caused by this feature.

This is browser/source acceptance only. It is not Acer physical OS evidence.

## 9. Re-freeze before verdict

In both repositories repeat:

```bash
git status --short
git rev-parse HEAD
git rev-parse origin/main
```

Require each tree clean and each `HEAD == origin/main` at the exact revisions actually tested.

If either `origin/main` advanced, verdict is `STALE`, not PASS; restart from §2 for a current claim.

## 10. Evidence to return

Return one compact report containing:

```text
GREIA_AGE_POLICY_SHA=
PARENT_AGE_POLICY_SHA=
GREIA_FOCUSED_TESTS=PASS|FAIL
GREIA_MAKE_VERIFY=PASS|FAIL
GREIA_MAKE_VERIFY_TEST_COUNT=
PARENT_NODE_TEST=PASS|FAIL
PARENT_AGE3_ONLY_UI=PASS|FAIL
PARENT_AGE3_EASIER_UI=PASS|FAIL
PARENT_UNKNOWN_AGE_EXCLUSION=PASS|FAIL
PARENT_OVERRIDE_PRECEDENCE=PASS|FAIL
PARENT_NO_AGE_UI=PASS|FAIL
PARENT_1024X600=PASS|FAIL
PARENT_CONSOLE_ERRORS=<count>
FINAL_ACTIVITY_AGE_POLICY_VERDICT=ACCEPTED|REJECTED|STALE|INCOMPLETE
FIRST_FAILURE=<none or exact first failure>
```

Do not claim Simulator, VM or physical-device acceptance from this procedure.
