# Review — Activity authoring simulator launch completion gate

**Date:** 2026-08-24  
**Scope:** contributor/agent Activity definition-of-done guidance only  
**Runtime implementation changed:** no  
**Platform phase closed:** no

## Problem

Repeated Activity creation/refactor work was reaching the owner with first-launch failures, especially Python `ImportError` / `ModuleNotFoundError` defects introduced by module decomposition. Existing Activity engineering/refactoring guidance already required a real Simulator launch, but that requirement was buried late enough in the documentation that agents were treating source validation and tests as sufficient completion evidence.

That behavior is unacceptable because Greia's actual Activity integration boundary is the normal Simulator/launcher/runtime path, not `python main.py`, a package import, a static validator, or an authored unit test.

## Correction

Created:

```text
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
```

and elevated the rule to the top of:

```text
skills/greia-activity-authoring/SKILL.md
```

The completion contract is now explicit:

- every new Activity and every substantive runtime-relevant Activity change must be loaded through the real Greia Activity Simulator/launcher path;
- it must reach a usable first frame;
- it must survive at least 10 seconds after that frame;
- at least one meaningful child interaction must execute without killing/stalling the Activity;
- Greia must regain clean Shell control through Home/Back or the applicable normal exit/completion path;
- stateful/gameplay/completion work still requires the fuller happy-path acceptance already defined by `ENGINEERING.md` / `REFACTORING.md`;
- any runtime-relevant edit after a launch PASS invalidates that evidence and requires a new launch;
- missing simulator access does not permit a completion claim; status must remain `INTEGRATION-UNVERIFIED` / `SOURCE-VERIFIED / SIMULATOR-UNVERIFIED`.

Explicit failed-acceptance examples now include:

```text
ImportError / ModuleNotFoundError
runtime validation rejection
startup traceback
missing startup resource
immediate/unintentional exit
READY never reached
blank/dead first frame
first meaningful input crash
failure to return cleanly to Shell
```

## Important distinction

This is a contributor/evidence contract change. It does not itself execute an Activity, fix an Activity, change the Simulator runtime, or establish new hardware/runtime evidence.

Future Activity reviewers should reject substantive work with no concrete final-source Simulator launch evidence regardless of unit-test count or source quality.
