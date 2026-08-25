# Installed Activity Resilience Hardening Review — 2026-08-25

**Scope:** follow-up to ADR 0033 after adversarial review of the installed Acer permission/deployment model.

**Baseline reviewed:** `52419ab727dbdd02df0cd4bd378d83975c2a1f09` (`main` at start of tranche).

## Finding

The first ADR-0033 implementation correctly fixed the progression cross-binding that converted one skipped Activity into a launcher restart loop, but its cleanup mechanism was placed at the wrong privilege boundary for the installed OS.

The image builder installs `/opt/greia-os` as `root:root` and removes write permissions recursively. `greia-launcher.service` deliberately runs as `greiakid`. Therefore a call to `scrub_activity_tree(/opt/greia-os/activities)` from `LauncherApplication.__init__` cannot be relied upon to remove host metadata from the built-in tree. The same installed launcher may also discover developer Activities under `/var/lib/greia-developer/activities` and parent packages under `/var/lib/greia-os/activity-packages/active`.

This is a device-resilience problem, not an agent-training problem.

## Hardening implemented

### Privileged pre-launch sanitation

`greia-launcher.service` now runs a narrow `ExecStartPre=+` helper before `prepare-launcher-vt`:

```text
/usr/local/lib/greia-os/scrub-activity-trees
```

The helper executes the platform scrubber as root while the real launcher remains `greiakid`. It covers built-in, developer and parent Activity roots.

The wrapper always exits zero. If Python/import/filesystem cleanup fails unexpectedly, the launcher still starts and Activity discovery remains the next containment boundary.

### Scrubber safety/observability

`src/greia_platform/activity_tree_cleanup.py` now:

- resolves the canonical installed Activity-root set from installed defaults/environment;
- rejects a symlink used as an Activity root;
- never follows directory symlinks outside a root;
- treats missing optional roots as normal;
- catches walk/path-resolution/delete failures;
- records `failed_removals` separately from successful removals;
- keeps a last-resort top-level exception boundary for the boot invocation;
- retains the fixed curated junk vocabulary only.

It does **not** repair real Activity files.

### Runtime enrichment isolation

`src/greia_launcher/composition.py` now separates strict source/build policy validation from installed runtime availability.

`ProgressionPolicy.load(...)` itself stays strict. A source/test call still rejects malformed policy and a loaded-Activity rule referencing an undeclared event.

At launcher runtime, `load_runtime_progression_policy(...)` catches progression-policy errors, logs them, and supplies an empty progression policy. History storage/event recording continues; only Star/progression enrichment is disabled for that launcher instance.

This aligns progression with the already fail-soft achievement-service composition without weakening history/storage/trust authority.

## Why this is safer than deployment instructions

The defense does not depend on how bytes reached the Acer.

Whether an agent used the canonical remote tool, raw `scp`, an ad-hoc root copy, a later updater, or another privileged maintenance path, launcher startup has the same installed-state hygiene and isolation boundaries.

Correct deployment tooling remains useful, but it is no longer the primary mechanism protecting child OS availability from this failure class.

## New focused regression coverage

`tests/test_installed_activity_resilience.py` covers:

1. the three installed Activity roots;
2. parent-root environment override behavior;
3. failed deletions are not falsely counted as successful cleanup;
4. symlink Activity roots are not followed;
5. malformed runtime progression policy disables progression rather than aborting runtime composition;
6. stale event binding remains a strict `ProgressionPolicy.load` failure but becomes runtime-empty progression;
7. systemd orders privileged scrub before VT preparation while the launcher stays `greiakid`;
8. the installed wrapper is explicitly fail-open.

## Evidence actually executed during authoring

This GitHub editing environment is not the Greia checkout/runtime and cannot run `make verify` or the Acer service.

The authored Python modules were syntax-parsed in an isolated local scratch environment. The scrubber was also exercised there against nested `.DS_Store` / `__pycache__` contamination and against a simulated failed deletion; its successful/failed counters behaved as intended. The shell wrapper passed `sh -n`.

These are authoring checks only, not repository/source closure or physical evidence.

## Required closure

Before claiming this hardening accepted on the installed Acer:

```text
1. run tests/test_activity_tree_cleanup.py
2. run tests/test_installed_activity_resilience.py
3. run the relevant history/composition/launcher tests
4. run make verify
5. deploy the final OS/service/source state to the Acer
6. place representative safe junk in a disposable/test Activity tree:
   .DS_Store
   ._*
   __pycache__/*.pyc
7. restart greia-launcher.service
8. verify journal shows privileged sanitation
9. verify junk is actually absent afterward
10. verify the Activity is either healthy/visible or, for a deliberately real defect,
    isolated without affecting the rest of the launcher
11. test a deliberately stale progression event binding and verify:
    launcher boots
    Activity/history work
    progression is disabled with a diagnostic
12. prove a fresh independent SSH connection and no launcher restart storm
13. record exact tested SHA and physical evidence
```

Do not deliberately corrupt trust/storage/history safety policy merely to test fail-soft behavior; those authorities remain intentionally hard.
