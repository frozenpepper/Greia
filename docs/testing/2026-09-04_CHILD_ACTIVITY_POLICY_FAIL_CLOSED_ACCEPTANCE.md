# Child Activity policy fail-closed + trusted-fallback acceptance — 2026-09-04

**Status:** exact-current local acceptance procedure  
**Scope:** Parent per-child Activity policy projection in the normal child Shell and emergency trusted launcher fallback  
**Evidence lane:** SOURCE + LOCAL TESTS; physical/runtime fallback evidence remains part of the active R7 device gate  
**Execution rule:** **STOP ON THE FIRST FAILURE. Do not repair or weaken the gate inside the frozen attempt.**

## 0. Product invariant

For an active child profile, Parent Activity visibility policy is mandatory launcher authority, not an optional rich-presentation feature.

Required composition:

```text
validated Activity registry
  -> mandatory per-child visibility / age / difficulty projection
  -> child-visible catalogue
      -> normal rich Shell: adaptive Collection presentation allowed
      -> trusted emergency fallback: direct catalogue presentation
```

A missing policy file is a legitimate default and may produce the normal `show_all` policy.

A policy path that exists but is malformed, unreadable, an unsupported schema, or a symlink is **not** equivalent to `show_all`. Until repaired it must expose **zero launchable Activities** while leaving the Shell/fallback process able to render recovery/profile UI.

## 1. Hard prohibitions

During this gate do not:

- edit source after freezing the candidate;
- replace a malformed-policy failure with a default policy by hand;
- bypass `ActivityDiscoveryPolicyStore`;
- remove the trusted fallback from the installed X-session path;
- use `?demo=1` as device evidence;
- use GitHub-hosted Actions;
- delete/stash/reset unrelated owner work;
- claim physical fallback evidence from source tests.

## 2. Freeze the exact candidate

From the canonical Greia checkout:

```bash
set -euo pipefail
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
GREIA_CHILD_POLICY_SHA=<full SHA>
```

If `origin/main` advances during the run, finish only the current command, mark the attempt `STALE`, and restart from this section on the new head.

## 3. Structural source gate

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_launcher_activity_policy_safety -v
```

Required: exit 0.

The suite must prove all of the following:

- `GreiaChildShell` inherits the shared `ActivityPolicyEnforcementMixin` boundary through the policy-enforced adaptive composition;
- `TrustedGreiaLauncherPresentation` inherits the same boundary through the direct policy composition;
- an explicit Parent `always_hide` applies in both paths;
- restrictive age policy also applies in the trusted fallback;
- a genuinely missing policy file retains normal default behavior;
- malformed JSON exposes zero Activities in both paths;
- unsupported policy schema exposes zero Activities;
- a symlink policy exposes zero Activities;
- repairing rejected policy state is detected and restores the effective catalogue;
- the trusted fallback remains deliberately direct/non-adaptive rather than inheriting rich sub-Collection UI merely to obtain policy enforcement.

Any failure: STOP and return the full traceback/output.

## 4. Existing discovery/Parent regressions

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_activity_audience_manifest \
  tests.test_activity_discovery_policy \
  tests.test_first_party_activity_audience_metadata \
  tests.test_parent_activity_policy -v
```

Required: exit 0.

This protects the existing age/difficulty/override contract while closing the launcher-composition hole.

## 5. Installed fallback wiring guard

The focused suite in §3 owns the source-level composition assertion for this
work: the normal installed Shell and `TrustedGreiaLauncherPresentation` must
both inherit the mandatory policy boundary, while the trusted fallback remains
direct/non-adaptive.

In addition, inspect the exact-current installed `greia-x-session` source during
review and confirm it still launches the normal child Shell first and the
trusted presentation only as its fallback. Do not invent or rely on a historical
test-module name that is absent from the current tree. `make verify` below is
the regression authority for all currently tracked wiring tests.

## 6. Full source regression

Run:

```bash
make verify
```

Required: exit 0. Record the exact fresh test count.

On failure: STOP. Do not proceed to runtime/device evidence with a failed source gate.

## 7. Adversarial policy-file probe

Using a project-local temporary profile fixture or the repository's existing launcher test fixture — **never a real child's persistent profile** — exercise these states in order:

```text
missing file
valid SHOW_ALL
valid ALWAYS_HIDE for one Activity
malformed JSON
unsupported schema
symlink
repaired valid policy
```

For each rejected state, confirm that the effective catalogue contains zero launchable Activities and that the process itself remains alive/recoverable. For the repaired state, confirm normal policy projection resumes without restarting into a more-permissive emergency catalogue.

If no current project-local runtime fixture can exercise this without touching real profile data, mark this section `NOT_RUN` rather than improvising. The automated source suite in §3 remains mandatory regardless.

## 8. Physical R7 evidence boundary

This gate does not manufacture hardware proof. The exact-current physical R7 closure must still verify the installed crash/fallback behavior on the actual Greia device under the active R7 procedure.

When that physical fallback scenario is run, add one Parent-policy assertion:

1. hide one harmless installed Activity through the normal Parent API/UI;
2. confirm it is absent in the normal child Shell;
3. trigger only the already-sanctioned child-Shell failure/fallback scenario from the R7 procedure;
4. confirm the trusted fallback does **not** expose the hidden Activity;
5. restore the normal Shell and Parent policy through normal supported paths.

Do not invent a new destructive crash mechanism for this test.

## 9. Re-freeze and verdict

Repeat:

```bash
git status --short
git rev-parse HEAD
git rev-parse origin/main
```

Require clean and equal to the exact revision tested.

Return:

```text
GREIA_CHILD_POLICY_SHA=
FOCUSED_POLICY_SAFETY_TESTS=PASS/FAIL
EXISTING_DISCOVERY_TESTS=PASS/FAIL
FALLBACK_WIRING_TESTS=PASS/FAIL
MAKE_VERIFY=PASS/FAIL
MAKE_VERIFY_TEST_COUNT=
ADVERSARIAL_RUNTIME_PROBE=PASS/FAIL/NOT_RUN
PHYSICAL_R7_POLICY_FALLBACK=PASS/FAIL/NOT_RUN
VERDICT=PASS/FAIL/STALE/INCOMPLETE
FIRST_FAILURE=
```

`PASS` here means exact-current source/local acceptance only unless the physical field is separately `PASS`. Never collapse those evidence lanes.
