# Greia Parent Controls — Local Validation and Continuation Runbook

Date: 2026-09-01
Branch prepared by remote agent: `feature/parent-controls-foundation`

This file is written for the local implementation/test agent. Follow it literally unless repository evidence proves a step is wrong. If a command fails, capture the exact failure before changing code.

## 0. Mission and boundaries

The owner wants:

- a much clearer Parents web application;
- per-child Activity visibility, including explicit enable/disable;
- useful age/difficulty management;
- daily usage limits per Greia device and/or child profile;
- a calm remaining-time indication on child home when a finite limit exists;
- authoritative enforcement at Greia platform/lifecycle level.

The remote branch already contains a first implementation slice. Your job is to **validate it first**, repair only proven defects, then complete the usage-limit integration and declarative difficulty policy if the repository architecture supports the steps below.

### Hard boundaries

1. Read root `AGENTS.md` before editing anything.
2. Read `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`.
3. Read `docs/adr/0022-parent-management-api-client-pairing-and-privilege-boundary.md`.
4. Read `docs/design/PARENT_CONTROLS_USAGE_LIMITS_AND_ACTIVITY_VISIBILITY.md`.
5. Do **not** declare R7 or R12 complete.
6. Do not add shell-command shortcuts to the Parent web app/API.
7. Do not let browser code write Greia state files.
8. Do not let the usage-limit service kill Activity processes or own display/sandbox behavior. The supervisor/lifecycle owner must enforce.
9. Do not implement Activity hiding with CSS, launcher-only conditionals, package uninstall, or a second hidden-activity file. Use `ActivityDiscoveryPolicy`.
10. Do not change package trust, permissions, sandbox, update, installer, or root/service privilege boundaries for this feature.
11. Preserve OOP/service ownership. Prefer injected collaborators and typed read models over global state.
12. Never use an Activity's wall clock or self-reported duration for time accounting.
13. Do not weaken tests to make the branch pass.
14. If you discover that a requested integration conflicts with an active architectural invariant, STOP that integration, document the conflict and return evidence. Do not bypass it.

## 1. Prepare the branch

From the Greia repository root:

```bash
git status --short
git fetch origin
git switch feature/parent-controls-foundation
git pull --ff-only origin feature/parent-controls-foundation
git status --short
git log --oneline -8
```

Expected: clean tree before you begin. If the tree is not clean, do not discard owner work. Report the files and ask the owner only if you cannot safely preserve them.

Record:

```bash
git rev-parse HEAD
python3 --version
```

## 2. Inspect the prepared changes before testing

Run:

```bash
git diff origin/main...HEAD -- src/greia_parent/web_client.py
git diff origin/main...HEAD -- src/greia_platform/usage_limits.py
git diff origin/main...HEAD -- tests/test_usage_limits.py
git diff origin/main...HEAD -- docs/design/PARENT_CONTROLS_USAGE_LIMITS_AND_ACTIVITY_VISIBILITY.md
git diff origin/main...HEAD -- docs/agents/GREIA_PARENT_CONTROLS_LOCAL_CONTINUATION.md
```

Confirm the branch currently contains these intended concepts:

- redesigned fallback Parents UI;
- child selector and age/challenge editing;
- Activity automatic visibility mode;
- per-Activity `Automatic` / `Always show` / `Hide from child`;
- management-list search, age and difficulty filters;
- `UsageLimitPolicy`, `UsageLimitStore`, `UsageLimitService`;
- tests for device/profile budgets, rollover, rollback and persistence.

Do not assume the code is correct merely because it is present.

## 3. Fast static checks — STOP on first real failure

Run exactly:

```bash
PYTHONPATH=src python3 -m py_compile \
  src/greia_parent/web_client.py \
  src/greia_platform/usage_limits.py \
  tests/test_usage_limits.py
```

Then render the fallback HTML and make sure the Python function itself executes:

```bash
PYTHONPATH=src python3 - <<'PY'
from greia_parent.web_client import render_parent_web_app
html = render_parent_web_app()
assert html.startswith("<!doctype html>")
assert "/api/v1" in html
assert "Hide from child" in html
assert "activity-policy" in html
print("PARENT_WEB_RENDER_PASS", len(html))
PY
```

If `node` is installed, syntax-check the embedded JavaScript without adding Node as a Greia dependency:

```bash
if command -v node >/dev/null 2>&1; then
  PYTHONPATH=src python3 - <<'PY'
from pathlib import Path
from greia_parent.web_client import render_parent_web_app
html = render_parent_web_app()
script = html.split("<script>", 1)[1].split("</script>", 1)[0]
Path("./tmp_parent_controls_web.js").write_text(script, encoding="utf-8")
PY
  node --check ./tmp_parent_controls_web.js
  rm -f ./tmp_parent_controls_web.js
fi
```

If JavaScript fails syntax validation, fix the **actual syntax defect only**, rerun this section, and commit the repair separately.

Also inspect the age selector. The platform accepts ages `1..18`; the UI must not accidentally omit age 1. If it does, fix it before proceeding.

## 4. Usage-limit unit tests

Run only the new tests first:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_usage_limits.py' -v
```

Expected: all tests pass.

Before changing anything for a failure, classify it:

- implementation defect;
- test defect (only if the test contradicts documented semantics);
- platform/environment defect.

### Additional cases you must add if absent

Add focused unit tests for all of these before integration:

1. `daily_minutes=None` clears a profile policy;
2. `daily_minutes=None` clears device policy;
3. zero elapsed seconds does not create incorrect usage;
4. invalid/unsafe profile IDs are rejected;
5. malformed JSON is rejected;
6. unsupported schema version is rejected;
7. over-sized state file is rejected;
8. old usage buckets are pruned to the bounded retention count;
9. device usage and profile usage both increment exactly once per recorded interval;
10. a finite device limit with unlimited profile still restricts the profile;
11. finite profile limit with unlimited device still restricts the profile;
12. no finite policies returns `effective_remaining_seconds=None`.

Do not test implementation-private tuple layout unless it is required for persistence compatibility.

## 5. Run the relevant existing tests

Locate the current Parent API, discovery, profile, launcher/supervisor and child-shell tests. Do not guess names if the repository changed:

```bash
find tests -maxdepth 1 -type f -name 'test_*.py' | sort | grep -E 'parent|profile|discover|catalog|launcher|shell|supervisor|lifecycle|activity_api'
```

Run each relevant file with `unittest discover`, for example:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_parent*.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_profile*.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p '*discovery*.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p '*supervisor*.py' -v
```

Use the actual matching filenames returned by `find`. A pattern with zero tests is not evidence.

## 6. Full repository gate before integration

Run:

```bash
make verify
```

Capture the complete final summary. If `make verify` fails because of the branch changes, fix the real regression before adding more implementation. If it fails for a clearly pre-existing unrelated issue, record the exact failure and continue only if the owner/project protocol permits it; do not claim green.

Commit any validated repair before continuing.

---

# PART B — Parent web/API acceptance of the already-implemented Activity controls

## 7. Verify existing authoritative Activity-policy behavior

Read these implementations first:

- `src/greia_platform/activity_discovery.py`
- `src/greia_launcher/adaptive_discovery_presentation.py`
- `src/greia_parent/api_server.py`
- relevant tests found in section 5.

Confirm from code/tests that:

1. policy is per child profile;
2. `always_hide` removes an Activity from the effective set;
3. `always_show` can restore a known Activity against automatic age filtering;
4. launcher uses the effective set;
5. launcher reloads policy changes without reboot if that is the current contract;
6. Parent API validates Activity IDs and policy enum values.

If any statement is false, report it before changing architecture.

## 8. Local Parent web manual test

Use the repository's documented safe local/dev launch method for the Parent API. Do **not** invent a root/system service install just for this test. If the repo has a test/dev server fixture, prefer it.

Open the fallback Parents client in a browser and verify at desktop width and a narrow/mobile width.

### Children page

For a disposable test profile:

1. create child;
2. set age;
3. set challenge preference;
4. toggle CAPITAL/normal text;
5. reload browser;
6. confirm values persisted;
7. clear approximate age and reload;
8. confirm age is truly unset, not zero/string.

### Activities page

For the same profile:

1. select `Show all Activities`;
2. pick one known Activity A;
3. set A to `Hide from child`;
4. reload browser;
5. confirm A still reports hidden;
6. verify API `effective_activity_ids` omits A;
7. if a live child launcher is available, verify A disappears without reboot;
8. set A back to `Automatic` and confirm it follows the base mode;
9. use `Recommended for age` and verify Activity cards/effective set make sense for the profile age;
10. set another Activity B to `Always show`; change the base mode so B would normally be filtered; confirm B remains effective;
11. test Activity search;
12. test age metadata list filter;
13. test difficulty list filter;
14. confirm list filters do **not** mutate child policy merely by browsing them.

Capture screenshots of:

- Children page;
- Activities page showing one explicit hidden Activity;
- narrow/mobile layout.

If the fallback client is not what an installed build serves because a separately-vendored web root overrides it, document that clearly. Do not claim installed UX acceptance from testing only the fallback.

---

# PART C — Complete authoritative usage-limit integration

Do this only after Parts A/B are green or failures are understood.

## 9. Composition/storage ownership

First identify how Parent API and launcher are composed and what managed state root they can both legitimately access.

Search:

```bash
grep -R "ParentApiApplication(" -n src tests build | head -50
grep -R "ActivitySupervisor(" -n src tests build | head -80
grep -R "profiles_dir" -n src/greia_parent src/greia_launcher build | head -80
grep -R "ProfileStore" -n src/greia_launcher src/greia_parent | head -80
```

Pick **one injected usage-limit state path** owned by Greia platform state and writable/readable under the existing Parent/launcher group boundary. Prefer an existing shared managed state directory already used by these two services. Do not create world-writable state and do not make the web service root.

The service module deliberately does not hard-code a path.

Add composition tests for the selected path/permissions.

## 10. Parent API wiring

Inject one `UsageLimitService` into `ParentApiApplication` through composition. Do not instantiate scattered stores per request.

Implement authenticated routes consistent with the design doc:

### Device

`GET /api/v1/usage-limits`

Return at least:

```json
{
  "daily_minutes": 90,
  "date": "2026-09-01",
  "used_seconds": 1200,
  "remaining_seconds": 4200
}
```

The exact response may include more typed facts, but keep names stable and obvious.

`PUT /api/v1/usage-limits`

Body:

```json
{"daily_minutes": 90}
```

or

```json
{"daily_minutes": null}
```

### Per profile

`GET /api/v1/profiles/{profile_id}/usage-limit`

Return `UsageLimitStatus.public_dict()` plus any small policy wrapper that improves API clarity.

`PUT /api/v1/profiles/{profile_id}/usage-limit`

Body:

```json
{"daily_minutes": 45}
```

or null.

### API hard requirements

- normal Parent API authorization on every route;
- validate profile existence before GET/PUT per-profile;
- body stays within existing JSON size limit;
- invalid minutes => 400 with stable error code;
- unknown profile => 404;
- no filesystem path in API input;
- no reset/credit endpoint in this phase unless the owner explicitly asks for it.

### Required API tests

Add tests proving:

1. unauthorized GET/PUT rejected;
2. device GET default unlimited;
3. device PUT finite then GET persists;
4. device PUT null clears;
5. profile PUT finite then GET returns effective facts;
6. profile PUT null clears;
7. unknown profile rejected;
8. 0, negative, boolean and >1440 rejected;
9. two profiles see the same device usage but separate profile usage;
10. API never exposes raw state path or private persistence representation.

## 11. Lifecycle accounting and enforcement

Inspect `src/greia_launcher/supervisor.py` and its tests carefully before editing.

### Injection

Add an optional/injected usage-limit collaborator to `ActivitySupervisor` or the correct higher lifecycle composition object. Installed production composition must inject the real service. Development/unit construction may remain optional if that is the repository's established pattern.

Do not make the supervisor open JSON files itself.

### Before Activity launch

Immediately before launching an Activity process, after profile identity is authoritative but before resources/process are committed:

1. request usage status for `profile.profile.profile_id` (or the actual current profile-id access path);
2. if `status.exhausted`, do not launch;
3. return/raise a **typed platform/lifecycle result** that the shell can render as `time finished for today`;
4. do not classify this as package corruption or Activity failure;
5. do not start history as if an Activity ran if no process was launched, unless current history has a dedicated blocked-launch event.

Choose the integration point based on existing lifecycle contracts and tests, not this prose if the code proves a better owner exists.

### While Activity runs

Use the supervisor's monotonic lifecycle clock.

Maintain per-active-session accounting state such as:

- last checkpoint monotonic timestamp;
- uncommitted fractional remainder if needed;
- profile id.

Recommended checkpoint interval: 15 seconds.

At each checkpoint:

```text
new_whole_seconds = floor(now - last_accounted_monotonic)
record exactly new_whole_seconds once
advance accounting cursor by the seconds actually recorded
```

Also checkpoint at:

- normal process exit;
- requested stop;
- forced stop;
- platform shutdown cleanup;
- failed/terminal transition after process launch.

Avoid double-counting when `poll()` sees the same terminal state more than once. Existing idempotent result behavior must remain intact.

### At zero

When the returned status reaches exhausted:

1. request the normal graceful stop once;
2. let the existing bounded graceful-stop machinery run;
3. use existing forced-stop mechanics only after that grace period;
4. preserve display restore/resource cleanup/history normalization.

Do not call `kill()` from `usage_limits.py`.

### Required lifecycle tests

Use fake monotonic time and fake UsageLimitService/store where appropriate. Test:

1. exhausted profile never launches process;
2. unlimited profile behavior is unchanged;
3. finite device-only budget allows launch before zero;
4. finite profile-only budget allows launch before zero;
5. most restrictive budget is used;
6. 15-second checkpoint adds 15 seconds exactly once;
7. multiple polls before checkpoint do not overcount;
8. terminal checkpoint records tail seconds;
9. normal exit does not double-count tail;
10. forced stop does not double-count tail;
11. shutdown path does not double-count tail;
12. zero triggers graceful stop once;
13. uncooperative Activity reaches normal existing force-stop path;
14. switching to another profile consumes shared device budget correctly;
15. lifecycle resource/display cleanup stays identical to pre-feature tests.

If a dedicated exit reason is added, update all exhaustive enum consumers/tests. Do not casually reuse `PLATFORM_FAILURE` for a successful parent-policy enforcement event.

## 12. Child-home remaining-time read model

Find the narrowest platform/presentation boundary used by `child_shell.py`, `collection_home_presentation.py`, and/or the current home composition.

Implement a tiny read model. It should not expose the persistence store.

Suggested immutable model:

```python
@dataclass(frozen=True, slots=True)
class ChildUsagePresentation:
    limited: bool
    remaining_seconds: int | None
    exhausted: bool
```

The presenter obtains it from `UsageLimitService.status(selected_profile_id)`.

### Display behavior

- unlimited => no timer/clock shown;
- >= 60 min => `1 h 20 min left today` style;
- < 60 min => whole minutes;
- < 1 min but > 0 => `Less than 1 min left today`;
- 0 => friendly finished-for-today state;
- do not show seconds ticking on home;
- refresh only at low frequency (30–60 s) plus profile/policy/Activity-return events;
- exhausted state must disable/short-circuit Activity launch UI without breaking profile navigation or shutdown.

Do not replace the ordinary wall clock if Greia already has one unless the UX code clearly makes that appropriate. The usage indicator can sit beside it. If no wall clock exists, do not add a clock merely for decoration; show the remaining-time status.

Add presenter formatting tests independent of pygame rendering.

## 13. Child warning presentation while running

Only after lifecycle enforcement is green, locate the existing shell/system-notice mechanism. If none exists, do **not** inject overlays directly into arbitrary Activities in this round.

Minimum acceptable completion is:

- home shows remaining time;
- zero reliably returns to home;
- finished state explains why no Activity can launch.

15/5/1-minute warnings are desirable but may be a follow-up if there is no existing platform-owned notification surface. Record the deferral explicitly rather than adding fragile Activity-specific overlays.

---

# PART D — Declarative difficulty policy

## 14. Do not fake this with browser filters

The current web client's Difficulty selector only filters the management list. The owner wants the possibility of showing only Activities of certain difficulty. Implement that as platform policy, not as hidden JavaScript state and not by expanding a range into a giant permanent override list.

## 15. Extend `ActivityDiscoveryPolicy`

Before coding, inspect actual manifest difficulty validation to determine exact global bounds. Do not assume `1..5` merely because the fallback UI currently offers 1..5; reconcile any mismatch.

Add nullable policy fields, preferably:

- `difficulty_min: int | None`;
- `difficulty_max: int | None`.

Semantics:

1. no bounds => no automatic difficulty filtering;
2. one bound => one-sided interval;
3. both => inclusive interval and `min <= max`;
4. use Activity nominal `difficulty` as the basic comparable value;
5. for `adaptive_difficulty` with declared `difficulty_min/max`, an Activity is eligible if its supported interval intersects the parent's allowed interval, unless product tests establish a different clearly documented rule;
6. `always_hide` wins;
7. `always_show` overrides automatic age and difficulty filters;
8. missing Activity difficulty metadata must follow existing manifest guarantees; do not invent English keyword heuristics.

### Persistence migration

Do not break existing schema-1 files.

Either:

- introduce schema 2 with explicit schema-1 migration on read; or
- add optional backward-compatible fields while retaining schema number only if repository schema policy explicitly permits additive fields.

Preserve:

- current visibility mode;
- explicit overrides;
- adaptive `subdivided_collections` state.

Add round-trip and migration tests.

## 16. Parent API and web UI for difficulty policy

Extend the existing Activity-policy GET/PUT response with the difficulty bounds.

In the web app add a clearly labeled **Child catalogue difficulty** control separate from the management-list filter.

Use simple parent language, for example:

- Any difficulty;
- Easier Activities;
- Middle range;
- More challenging;
- Custom min/max.

If the manifest vocabulary is genuinely 1..5, a dual min/max select is fine. If not, derive labels/options from the platform contract rather than hard-coding an invalid range.

The UI must show that explicit per-Activity choices can override automatic filtering.

Required tests:

1. no bounds preserves current effective catalogue;
2. min only;
3. max only;
4. inclusive bounds;
5. invalid min/max rejected;
6. always-hide precedence;
7. always-show precedence;
8. adaptive interval behavior;
9. API persistence;
10. launcher hot-reload sees policy change;
11. existing age policy behavior is unchanged when no difficulty bounds set.

---

# PART E — Final validation

## 17. Targeted suites again

Run all new/relevant tests. At minimum:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_usage_limits.py' -v
```

Then the exact Parent API, discovery, profile, supervisor/lifecycle, child-shell/home test files you modified.

## 18. Full verification

Run:

```bash
make verify
```

This is mandatory before calling the branch code-complete at source level.

## 19. Real installed-device acceptance

If you have the Acer/Greia target available and the active project protocol permits testing this branch on it, test all of the following. If not available, report `NOT RUN — requires installed target`.

### Activity visibility

1. Parent hides Activity A.
2. Child home loses A without reboot.
3. Running unrelated Activity B is unaffected.
4. Parent restores A.
5. A returns according to policy without reboot.

### Usage limits

Use small disposable limits only on a disposable test profile/device state.

1. set profile limit to 2 minutes;
2. home shows approximately 2 minutes remaining;
3. start Activity;
4. verify countdown/accounting advances from authoritative runtime;
5. at zero Activity receives graceful stop path and Greia returns home;
6. launching another Activity is blocked cleanly;
7. reboot and verify exhausted state persists for the accounting day;
8. clear profile limit and verify launch works again;
9. set device limit and verify two profiles share it;
10. confirm profile switching cannot reset the device budget;
11. change parent policy while child is on home and verify status updates without full reboot if watcher contract supports it.

### Power-loss durability

If safe on the test machine:

1. start a 5-minute budget;
2. run Activity for >30 seconds;
3. hard reboot only if project hardware-testing protocol explicitly allows it;
4. verify no more than roughly one checkpoint interval was lost.

Do not perform unsafe power cycling merely to satisfy this checklist.

## 20. Evidence to return to the owner

Return one concise report containing:

- starting commit SHA;
- ending commit SHA;
- every file changed;
- all commits made;
- static-check results;
- targeted-test counts;
- `make verify` final result and count/summary;
- Parent web screenshots or their project-local evidence paths;
- installed-device checks and which were NOT RUN;
- exact API examples for device/profile limits;
- exact activity-policy example showing hidden Activity absent from effective IDs;
- any architecture decision/deviation and why;
- any remaining TODO, clearly separated into source-code vs real-hardware acceptance.

Do not package random build caches, virtual environments, generated audio, or system state into the repo.

## 21. Commit discipline

Use small semantic commits, for example:

1. `Fix parent controls validation defects` (only if Part A finds any)
2. `Expose usage limits through parent API`
3. `Enforce usage limits in activity lifecycle`
4. `Show remaining activity time on child home`
5. `Add declarative activity difficulty filtering`
6. `Document parent controls acceptance`

Before each commit:

```bash
git diff --check
git status --short
```

At the end:

```bash
git status --short
git log --oneline origin/main..HEAD
```

The final working tree should be clean unless the owner explicitly requested returned uncommitted evidence.
