# Adaptive Activity Discovery — Local Simulator Acceptance

**Status:** operator protocol; not yet executed at current head  
**Date:** 2026-08-23  
**Evidence scope:** Activity Simulator / source-level child discovery only  
**Does not prove:** real hardware display/input lifecycle, Parent transport security, package trust/signature policy, R7 closure

## 1. Goal

Prove that the implemented child-specific Activity discovery pipeline behaves coherently when catalogue density, Parent policy and profile audience preferences change.

The exact source under test includes:

```text
src/greia_platform/activities.py
src/greia_platform/activity_discovery.py
src/greia_platform/profiles.py
src/greia_launcher/catalogue_view.py
src/greia_launcher/adaptive_discovery_presentation.py
src/greia_launcher/child_shell.py
src/greia_parent/api_server.py
```

Product/source checkpoint:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_IMPLEMENTATION_STATUS.md
```

## 2. Hard rules for the local agent

- Work in the actual Greia checkout supplied by the owner.
- Read root `AGENTS.md` before running anything.
- Do not install packages, alter the OS, rewrite unrelated source, or trigger hosted CI.
- Do not write evidence to filesystem-root `/tmp`.
- If temporary/evidence state is needed, use a project-local directory such as `./tmp/adaptive-discovery-acceptance/`.
- Do not create ZIP archives unless the owner explicitly asks.
- Stop on the first unexplained source/test failure; record the exact command, exit code and output.
- Do not label a committed test as PASS unless it actually ran in this session.
- Simulator evidence must remain labeled Simulator evidence.

## 3. Preflight

From repository root:

```bash
pwd
git status --short
git rev-parse HEAD
python3 --version
```

Record the exact HEAD. The worktree must not contain unexplained edits before testing.

Inspect the current discovery contract:

```bash
sed -n '1,260p' docs/product/CHILD_ACTIVITY_DISCOVERY_IMPLEMENTATION_STATUS.md
sed -n '1,320p' skills/greia-activity-authoring/DISCOVERY.md
```

## 4. Focused source tests

First discover the current test names rather than guessing an obsolete module list:

```bash
find tests -maxdepth 1 -type f -name '*discover*' -o -name '*catalog*' -o -name '*profile*' -o -name '*parent*' | sort
```

Then run the focused discovery/profile/catalogue/Parent tests that exist in the checkout using the repository's established Python test command. If the checkout uses `unittest`, prefer an explicit module list; if it uses another documented runner, follow `AGENTS.md`/current test docs.

Minimum behaviors that must be covered or separately probed:

- manifest age bounds and adaptive difficulty validation;
- missing audience metadata fails open;
- explicit always-show/always-hide precedence;
- profile approximate-age/challenge preference persistence;
- adaptive planner direct/subdivided behavior;
- 10/8 hysteresis;
- Parent policy payload/update validation.

Record every command and result.

## 5. Synthetic catalogue matrix

Use the Activity Simulator's existing synthetic/developer Activity loading seam. Do **not** add fake production packages to the built-in catalogue solely for this test.

Create or select deterministic synthetic Activities with valid manifests and known primary Collection/discovery tags so each case below can be reproduced.

### Case A — four effective Activities

Target one primary Collection with exactly 4 visible Activities.

Expected:

```text
Home → primary Collection → 4 Activities
```

No sub-Collection chooser.

### Case B — ten effective Activities

Target exactly 10 visible Activities.

Expected for a fresh/non-subdivided state:

```text
Home → primary Collection → 10 Activities
```

No new subdivision merely because the Collection is dense.

### Case C — eleven coherent Activities

Target 11 visible Activities whose recognized discovery hints form 2–5 coherent groups with no stranded Activity.

Expected:

```text
Home → primary Collection → sub-Collection chooser → Activities
```

Verify:

- group labels/icons are platform-owned;
- every effective Activity is reachable;
- no package-defined arbitrary group becomes child chrome;
- keyboard and pointer both open groups;
- Back returns sub-Collection → primary Collection → Home.

### Case D — eleven incoherent Activities

Target >10 visible Activities that cannot form a valid coherent partition.

Expected:

```text
Home → primary Collection → direct Activities
```

The threshold must not manufacture an `Other` group or strand an Activity.

### Case E — 20+ coherent Activities

Target at least 20 visible Activities with several coherent recognized hints.

Expected:

- at most one sub-Collection layer;
- bounded 2–5 useful groups where planner/source contract allows;
- no deeper nested taxonomy;
- only visible/paged items rendered according to the normal launcher contract.

## 6. Hysteresis matrix

Use the same child/profile and same primary Collection. Start from a clean non-subdivided policy state.

Exercise this sequence with coherent metadata:

```text
10 → 11 → 10 → 9 → 8
```

Expected:

1. 10: direct;
2. 11: planner may adopt useful subdivision;
3. 10: remain subdivided if the adopted partition remains coherent;
4. 9: remain subdivided if still coherent;
5. 8: collapse to direct.

Restart/re-enter the Shell after the subdivided state is established and verify the platform-owned hysteresis state persists for the child rather than flapping solely because presentation was reconstructed.

## 7. Per-child effective count

Use one installed/synthetic registry but two child profiles.

Example setup:

- Child A effective visible count: 8;
- Child B effective visible count: 11 coherent.

Achieve the difference through supported per-child policy/age metadata—not by changing package registration between child switches.

Expected:

- Child A sees direct Activities;
- Child B sees the optional semantic sub-Collection layer;
- switching children recomputes the catalogue cleanly;
- package identity/saves/progression are not duplicated;
- switching back restores the appropriate presentation for Child A.

## 8. Parent override precedence

For a child with approximate age set, test both automatic policy and explicit overrides.

Required assertions:

- `recommended_only` uses declared age range but keeps unknown/no-age Activities visible;
- `hide_too_simple` can hide an Activity whose declared maximum is below the child's approximate age;
- `always_show` restores an Activity that automatic policy would hide;
- `always_hide` hides an Activity automatic policy would otherwise show;
- clearing an override returns control to automatic policy.

Do not use Activity code changes to achieve the result.

## 9. Challenge preference

With several visible Activities that differ in baseline `difficulty`, exercise:

```text
automatic
easier
standard
harder
```

Verify the preference changes supported discovery ordering/presentation only. It must not change package registration, permissions or saved Activity progression.

For an Activity that declares an adaptive difficulty range, verify only that the manifest facts are available/valid unless a separate Activity-runtime contract explicitly consumes the range. Do not invent gameplay adaptation at the launcher layer.

## 10. Responsive/UI matrix

Run the adaptive chooser at least at:

```text
640×480
800×600
1024×600
1920×1080
```

Also use one narrow/portrait stress viewport if supported by the Simulator.

Verify:

- no clipped required controls;
- readable Collection/sub-Collection identity;
- no overlap with profile/Home-safe region;
- keyboard focus remains visible;
- pointer hit targets remain usable;
- Back remains reachable;
- no extra nested depth appears to solve layout pressure.

## 11. Optional shared-visual fail-soft probe

If the Simulator has an established safe way to make `ui.portal.frame` unavailable/corrupt, exercise it without modifying production assets permanently.

Expected:

- adaptive chooser falls back to primitive drawing;
- navigation remains usable;
- only the established typed visual-asset/decode/cache failures are swallowed by the presentation fallback;
- unrelated programmer errors are not blanket-suppressed.

## 12. Parent HTML client

In the `Greia-Parent-App-Html` checkout pinned by Greia, run:

```bash
npm test
```

Then serve the client locally using its documented dependency-free path and inspect `?demo=1` on desktop and a narrow/mobile viewport.

Required Activity-policy UI checks:

- Activity policy controls appear only when `activities.policy` is advertised;
- child selector is bounded to known profiles;
- approximate-age control can be left unset;
- challenge preference values match API vocabulary;
- visibility mode values match API vocabulary;
- per-Activity Automatic / Always show / Always hide controls work in demo state;
- API-provided text is rendered as text, not HTML;
- no polling loop is introduced.

## 13. Evidence to return

Return a concise result containing:

```text
exact Greia HEAD
exact Parent HTML HEAD/runtime revision tested
commands executed
focused test result counts
Case A result
Case B result
Case C result
Case D result
Case E result
hysteresis result
per-child result
Parent override result
challenge-preference result
responsive viewport results
Parent npm test result
manual Parent UI result
first failure, if any
project-relative evidence paths, if files were produced
```

Screenshots are useful for visual cases but do not replace behavioral assertions.

## 14. PASS meaning

A PASS proves the adaptive discovery implementation at source/Activity-Simulator/Parent-client scope for the exact tested revisions.

It does **not** prove:

- R7 hardware/display-session lifecycle closure;
- real controller/touch hardware behavior beyond Simulator input semantics;
- Parent LAN transport security;
- signed official Activity distribution;
- every third-party Activity's metadata quality;
- production translation/RTL completeness.
