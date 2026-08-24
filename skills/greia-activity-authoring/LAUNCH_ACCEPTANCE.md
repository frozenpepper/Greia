# Greia Activity Simulator Launch Acceptance

**Status:** MANDATORY completion gate for Activity creation and substantive Activity work  
**Audience:** Activity authors, coding agents, reviewers, local test agents  
**Reviewed:** 2026-08-24

This is not an optional smoke-test recommendation. It is part of the definition of done for Greia Activity work.

> **An Activity is NOT complete, working, fixed, refactored, ready, or accepted until the final runtime-relevant source state has actually been launched through the Greia Activity Simulator/launcher path and has survived that launch.**

Repository validation, unit tests, import tests, AST/source checks, `python main.py`, a successful package build, or a clean `make verify` run do **not** substitute for this gate.

The reason is empirical and architectural: Activity work repeatedly passes static/source gates while still failing on the first real Greia launch because of package-local import mistakes, script-vs-package import differences, runtime-adapter policy, lifecycle wiring, missing assets/resources, initialization order, or exceptions reached only once Greia actually starts the Activity.

---

## 1. When this gate is mandatory

Run this gate after any substantive Activity change that can affect runtime behavior, including:

- creating a new Activity;
- refactoring or decomposing an Activity;
- moving/renaming Python modules or imports;
- changing `main.py`, the manifest entrypoint, lifecycle code or READY/STOP behavior;
- changing assets/resources/localization/audio loaded during startup or normal play;
- changing platform API use, permissions, capabilities, storage, events or progression integration;
- changing input, rendering, viewport/layout, terminal/victory or restart behavior;
- performance work that changes runtime code paths;
- bug fixes whose code executes at launch or during normal child interaction.

Pure documentation-only edits with no runtime/package change may mark this gate **not applicable**. Do not use that exception for source, manifest, asset or package changes merely because they look small.

---

## 2. The final-source rule

Simulator evidence applies only to the exact runtime-relevant source state that was launched.

If any runtime-relevant Activity file changes after a successful simulator run, the launch gate is invalidated and must be run again.

Examples:

```text
launch PASS -> edit renderer.py -> MUST relaunch
launch PASS -> fix one import -> MUST relaunch
launch PASS -> change activity.toml -> MUST relaunch
launch PASS -> replace startup asset -> MUST relaunch
```

Do not cite an earlier successful launch after changing the Activity.

---

## 3. Required acceptance sequence

Use the real Greia Activity Simulator over the real Greia runtime path. Read:

```text
docs/development/GREIA_ACTIVITY_SIMULATOR.md
```

Start the simulator using the repository's canonical launcher, currently:

```bash
python3 tools/greia_simulator.py
```

For iterative source development, load the Activity with the simulator's **Load Activity Folder…** path. Do not bypass Greia by copying directly into simulator-managed storage.

For package/distribution validation, use **Install Activity Package…** so the canonical package transaction is exercised.

The mandatory sequence is:

```text
1. simulator starts successfully
2. Activity source/package is loaded through Greia
3. Activity appears in the normal launcher/catalogue path
4. launch the Activity from the Greia launcher/Shell path
5. first usable child-facing frame is presented
6. Activity remains alive after startup instead of immediately crashing/exiting
7. leave it running for at least 10 seconds after the first usable frame
8. perform at least one meaningful child interaction
9. verify the Activity continues running after that interaction
10. use Greia Home/Back or the Activity's normal completion/exit path as applicable
11. confirm control returns cleanly to the Shell instead of leaving a dead/stuck runtime
```

The ten-second survival period is deliberately simple. It is not a performance benchmark; it exists to catch initialization/lifecycle failures that occur just after the first frame.

For a stateful/game-like Activity, startup survival alone is not full product acceptance. If the work touches gameplay, completion, scoring, storage, events, victory, restart, or input semantics, continue through the applicable happy path described in `ENGINEERING.md` / `REFACTORING.md`, including completion and restart where relevant.

---

## 4. What counts as a failed launch

Any of the following means the gate **FAILED**:

- `ImportError` / `ModuleNotFoundError`;
- package-local sibling imports fail under the real script/runtime context;
- Activity disappears or is rejected by runtime validation;
- startup traceback/exception;
- missing asset/resource/localization file at runtime;
- Activity process exits before or shortly after the first usable frame without an intentional child/system exit;
- READY is never reached/published when required;
- blank/dead/unusable first frame;
- Activity starts but does not respond to the first meaningful child interaction;
- first interaction crashes or kills the Activity;
- Greia cannot cleanly return to the Shell.

Do not downgrade these to "minor integration issues" while calling the Activity complete. They are failed acceptance.

On failure:

1. capture the concrete error/trace/log;
2. identify and fix the root cause;
3. rerun the relevant focused/source tests if the fix affects them;
4. rerun the simulator launch gate from the beginning against the new final source state;
5. only then consider the Activity launch-accepted.

---

## 5. Import errors: explicit mandatory checks

Modular Python Activities have multiple legitimate import contexts. A decomposition that works only in one is broken.

Before the simulator gate, check as applicable:

```text
runtime/script context
    Greia executes manifest.entrypoint as a file from the Activity root

repository/package context
    tests/tools may import activities.<activity>.* as package modules
```

Use the real `PythonRuntimeAdapter`/project validation path so package-local modules are distinguished from forbidden or unknown external imports.

But these checks are PRECONDITIONS only.

> **Even if every import/validator test passes, the Activity still must launch through the simulator.**

Likewise:

> **A direct `python main.py` success does not count as Greia launch acceptance.**

The launcher/runtime path is the integration boundary we actually ship.

---

## 6. Minimum evidence to record

For every substantive Activity tranche, record at least:

```text
Activity ID/name
exact repository/source SHA tested
simulator launch path used
source folder or package path used
viewport/resolution (1024x600 minimum reference when applicable)
profile/locale if materially relevant
whether first usable frame appeared
whether Activity survived >=10 seconds after first usable frame
meaningful child interaction exercised
whether Activity remained alive afterward
whether return to Shell succeeded
any additional full-session/completion/restart path exercised
result: PASS or FAIL
```

Do not write `PASS` from expected behavior or from tests that were authored but not executed.

---

## 7. Completion language is strict

If the simulator gate has not been run successfully on the final runtime-relevant source state, permitted status language is:

```text
SOURCE-VERIFIED / SIMULATOR-UNVERIFIED
INTEGRATION-UNVERIFIED
IMPLEMENTED, LAUNCH ACCEPTANCE PENDING
```

Do **not** call the Activity:

```text
done
complete
working
fixed
ready
accepted
launchable
finished
```

unless the mandatory simulator launch/survival gate has actually passed.

If the current execution environment cannot run the simulator, save/commit the work if appropriate, but report the limitation explicitly and leave the Activity **integration-unverified**. Lack of simulator access changes the status; it does not weaken the gate.

---

## 8. Reviewers must reject missing launch evidence

A reviewer evaluating substantive Activity work must ask first:

> **What exact final source SHA was launched in the Greia simulator, and did it survive launch plus a meaningful child interaction?**

If there is no concrete answer/evidence, the work is not done regardless of source quality or unit-test count.

This applies equally to:

- new Activities;
- "small" fixes;
- visual refreshes that touch runtime assets/code;
- architecture refactors;
- import/module cleanup;
- performance optimization;
- localization/audio integration;
- terminal/victory changes.

The simulator gate exists specifically to stop the recurring pattern of handing the owner Activities that fail on first launch.
