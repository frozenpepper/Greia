# Greia Local Simulator Acceptance Protocol — Achievements + Refactored Activities

**Date:** 2026-08-23  
**Target feature baseline:** `bdcab9cf6c3b4e46e5ee5c5688aea3154619442d`  
**Evidence class:** local developer / simulator / runtime-semantic only  
**Primary scope:** achievement engine, Greia Stars, Badge Library, Clinica Cuccioli refactor, Memory completion path, Costruiamo Ponti event/completion path

> This protocol does **not** prove physical Acer performance, production sandboxing, compositor/display ownership, controller hardware, or microphone/audio quality.

## Mission

Test the current Greia reward/achievement flow through the **real Greia child Shell inside the local Activity Simulator**:

```text
Activity gameplay
  -> declared factual Activity event
  -> trusted Event Broker
  -> profile History
  -> once-per-session Greia Star rule
  -> achievement evaluation
  -> post-Activity badge celebration
  -> profile Badge Library
  -> persistence across restart
  -> isolation between child profiles
```

Also exercise the recently refactored **Clinica Cuccioli** behavior and the shared low-cost completion screens used by Clinic, Memory and Bridges.

This is a test assignment only. **Do not repair anything while running it.**

## Hard rules

1. Do not edit source, tests, manifests, runtime policies, docs or assets.
2. Do not run formatters, auto-fixers, migrations, generators or update scripts.
3. Do not run GitHub Actions.
4. Do not pull, merge, rebase, reset, checkout another commit or discard local changes.
5. Do not delete an existing simulator workspace to obtain a clean test.
6. Simulator state must remain outside the checkout.
7. Evidence belongs under `./tmp/greia-achievement-simulator-acceptance/` only.
8. Do not create ZIP files.
9. Do not modify SQLite or `achievements.json`; state inspection is read-only.
10. Do not manufacture badges, Stars, events or history records.
11. Automated prerequisite failure, Shell/Activity crash, unexpected exit or mandatory assertion failure is a **HARD STOP**.
12. Never fix code and rerun during this protocol. Return the first failure evidence.

## Setup and source identity

From repository root:

```bash
export GREIA_FEATURE_BASELINE="bdcab9cf6c3b4e46e5ee5c5688aea3154619442d"
export GREIA_SIM_STATE="$HOME/.greia-simulator-achievement-acceptance"
export GREIA_EVIDENCE="$PWD/tmp/greia-achievement-simulator-acceptance"

if [ -e "$GREIA_SIM_STATE" ]; then
  echo "HARD STOP: simulator state already exists: $GREIA_SIM_STATE"
  exit 1
fi
if [ -e "$GREIA_EVIDENCE" ]; then
  echo "HARD STOP: evidence directory already exists: $GREIA_EVIDENCE"
  exit 1
fi
mkdir -p "$GREIA_EVIDENCE/screenshots"

git rev-parse HEAD > "$GREIA_EVIDENCE/source_sha.txt"
git status --short > "$GREIA_EVIDENCE/git_status.txt"
git log -1 --oneline > "$GREIA_EVIDENCE/source_commit.txt"
git merge-base --is-ancestor "$GREIA_FEATURE_BASELINE" HEAD
```

If the ancestor check fails, stop; do not checkout another commit.

```bash
git status --porcelain -- \
  src/greia_platform src/greia_launcher runtime \
  activities/clinica_cuccioli \
  activities/memory_meraviglie \
  activities/costruiamo_ponti \
  tests tools \
  > "$GREIA_EVIDENCE/relevant_git_status.txt"
```

If the relevant status file is non-empty, stop; do not reset/clean the tree.

## Host prerequisites

```bash
python3 --version > "$GREIA_EVIDENCE/python_version.txt"
python3 - <<'PY' > "$GREIA_EVIDENCE/python_prerequisites.txt" 2>&1
import tkinter
import pygame
print("tkinter: OK")
print("pygame:", pygame.version.ver)
PY
```

Do not install packages automatically if this fails.

## Focused provider-free source gate

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_achievements \
  tests.test_pygame_achievements \
  tests.test_clinica_cuccioli_refactor \
  tests.test_costruiamo_ponti_contract \
  tests.test_pygame_completion \
  tests.test_history \
  tests.test_simulator_remote_bridge \
  -v > "$GREIA_EVIDENCE/focused_tests.txt" 2>&1
STATUS=$?
cat "$GREIA_EVIDENCE/focused_tests.txt"
[ "$STATUS" -eq 0 ] || exit "$STATUS"

PYTHONPATH=src python3 -m unittest tests.test_greia_simulator -v \
  > "$GREIA_EVIDENCE/simulator_tests.txt" 2>&1
STATUS=$?
cat "$GREIA_EVIDENCE/simulator_tests.txt"
[ "$STATUS" -eq 0 ] || exit "$STATUS"
```

Do **not** run `make verify` in this focused assignment.

## Read-only state inspector

Create `$GREIA_EVIDENCE/inspect_state.py`:

```python
from __future__ import annotations
import json, os, sqlite3
from pathlib import Path

root = Path(os.environ["GREIA_SIM_STATE"]).expanduser().resolve()
print(f"SIM_STATE={root}\n")
registry = root / "profiles" / "profiles.json"
if registry.is_file():
    raw = json.loads(registry.read_text(encoding="utf-8"))
    print("PROFILES:")
    for item in raw.get("profiles", []):
        if isinstance(item, dict):
            print(f"  id={item.get('profile_id')} name={item.get('display_name')} avatar={item.get('avatar_id')}")
print()
for db_path in sorted(root.rglob("history.sqlite3")):
    print(f"HISTORY_DATABASE={db_path}")
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        print("  REWARD_BALANCES:")
        for row in connection.execute("SELECT reward_id, balance FROM reward_balances ORDER BY reward_id"):
            print(f"    {row[0]}={row[1]}")
        print("  EVENT_COUNTS:")
        for row in connection.execute("SELECT activity_id, event_id, count FROM event_counts ORDER BY activity_id, event_id"):
            print(f"    {row[0]}:{row[1]}={row[2]}")
        print("  BEST_SCORES:")
        for row in connection.execute("SELECT activity_id, event_id, score_order, best_score FROM best_scores ORDER BY activity_id, event_id"):
            print(f"    {row[0]}:{row[1]} order={row[2]} best={row[3]}")
    finally:
        connection.close()
    print()
paths = sorted(root.rglob("achievements.json"))
if not paths:
    print("ACHIEVEMENT_FILES: none")
for path in paths:
    print(f"ACHIEVEMENT_FILE={path}")
    print(json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2, ensure_ascii=False, sort_keys=True))
    print()
```

Use it read-only at checkpoints:

```bash
GREIA_SIM_STATE="$GREIA_SIM_STATE" python3 "$GREIA_EVIDENCE/inspect_state.py" > "$GREIA_EVIDENCE/<checkpoint>.txt"
```

## Start Simulator

```bash
python3 tools/greia_simulator.py --state-dir "$GREIA_SIM_STATE"
```

In a second repo-root terminal:

```bash
export GREIA_SIM_STATE="$HOME/.greia-simulator-achievement-acceptance"
export GREIA_EVIDENCE="$PWD/tmp/greia-achievement-simulator-acceptance"
python3 tools/greia_simulator_ctl.py status > "$GREIA_EVIDENCE/simulator_initial_status.txt" 2>&1
```

Initial configuration:

```text
Reference 1024x600
interface size normal
display + pointer + audio.basic enabled
```

Use the real child Shell and default child profile.

## A — Initial Badge Library

On Home verify the badge/star library button exists near profile chrome, is clickable and does not overlap profile/Collection controls. Enter one Collection and verify the route remains available. If a sub-Collection chooser naturally exists, test it there too; otherwise record `NOT EXERCISED`.

Open Badge Library. Fresh expected state:

```text
0/6 visible unlocked
six normal locked badge entries
secret Greia Constellation absent
no denominator leak to 7
locked selection shows a positive hint
Back works
pointer remains above UI
```

Capture screenshots for Home, Collection and initial library.

## B — Clinica Cuccioli

Launch Clinic normally.

Before completing the first suitable prescription, deliberately select the second required treatment before the first. Expected: selection/feedback may occur, but the later treatment does not complete, patient does not heal and prescription does not advance.

Then heal all **five patients in one Activity session**, respecting prescription order. At victory verify the shared completion screen is stable, Play Again reachable and protected Greia Home works. Leave via Home.

Expected celebration: `First Friend Helped / Primo amico curato`. Dismiss it. Immediately open Badge Library: First Friend must be unlocked and still `NEW/NUOVO`, Gentle Helper locked, count `1/6`. Leave library and reopen: NEW must now be cleared.

Read-only checkpoint must show:

```text
org.greia.clinica-cuccioli:vet.patient_healed = 5
global star = 1
greia.care.first-friend unlocked
Gentle Helper / Handful / Constellation not unlocked
```

Clinic's local stars are not global Greia Stars. Five heals in one session must still award only one global Star.

## C — Restart persistence

Restart child Shell through normal simulator control. Same profile must retain First Friend, no NEW marker, count `1/6`, star=1 and unchanged history.

## D — Memory first completion

Complete one full Memory game. Verify shared completion screen freezes active gameplay presentation and remains responsive. Leave via Home.

Expected celebration: `Memory in Action / Memoria in azione`. Badge Library expected `2/6`, with First Friend + Memory unlocked. Read-only checkpoint:

```text
memory.game_completed = 1
global star = 2
greia.memory.first-finish unlocked
```

## E — Bridges

Complete all three worlds (`river`, `canyon`, `space`) in the **same session**, placing the exact required material in each slot and pressing GO/VAI.

Expected final celebration: `Bridge Builder / Costruttore di ponti`. Badge Library expected `3/6`.

Read-only checkpoint:

```text
bridge.level_completed = 3
global star = 3
greia.building.bridge-builder unlocked
```

Critical: three crossing events in one session award only one additional global Star. If star moves 2 -> 5, FAIL.

## F — Reach exactly five global Stars

Second Clinic session: heal exactly one patient, then Home. Expected Clinic cumulative heals=6, global star=4, no duplicate First Friend celebration, Gentle Helper still locked.

Second Memory session: complete one game and Home. Expected global star=5 and new `A Handful of Stars / Una manciata di stelle` celebration.

Badge Library now expected:

```text
4/6 visible unlocked
First Friend
Memory in Action
Bridge Builder
A Handful of Stars
Gentle Helper locked
Pair Finder locked
secret Constellation absent
```

Trusted checkpoint:

```text
star=5
Clinic healed=6
Memory completed=2
Bridge completed=3
first-friend + memory.first-finish + bridge-builder + stars.handful unlocked
Gentle Helper / persistent-matcher / constellation not unlocked
```

## G — Profile isolation

Stop child Shell and close simulator controller. Do not edit profiles JSON. Create a second profile through canonical Greia API:

```bash
GREIA_SIM_STATE="$GREIA_SIM_STATE" PYTHONPATH=src python3 - <<'PY' > "$GREIA_EVIDENCE/create_second_profile.txt" 2>&1
import os
from pathlib import Path
from greia_platform.profiles import ProfileStore
state = Path(os.environ["GREIA_SIM_STATE"]).expanduser().resolve()
store = ProfileStore.load(Path("runtime/profile-defaults.toml"), state / "profiles")
profiles = store.ensure_initialized()
if any(p.display_name == "BadgeTest2" for p in profiles):
    raise SystemExit("HARD STOP: BadgeTest2 already exists")
created = store.create("BadgeTest2", "green_leaf")
print(created.profile_id, created.display_name)
PY
```

Restart simulator with same state. `BadgeTest2` must start at `0/6`, with no inherited Stars or achievements. Switch to original profile: it must still show `4/6`, global star=5 and prior history. Any cross-profile state is FAIL.

## H — Responsive visual smoke

Using original populated profile, test Badge Library at:

```text
1024x600 normal
1024x600 large
1280x800 normal
1366x768 compact
1920x1080 normal
```

At every setting verify Back/title/grid/detail/labels/hit targets fit, `4/6` remains visible and secret badge remains hidden. Capture each screenshot.

Activity smoke (launch + one normal interaction + Home return; no more grinding):

```text
Clinic: 1024x600 normal, 1280x800 normal
Memory: 1280x800 normal
Bridges: 1280x800 normal
```

Verify no clipping, correct pointer mapping, protected Home and no Linux/browser/window-manager surface.

## I — Static presentation sanity

Simulator-only sanity, not hardware evidence. With library idle:

```bash
python3 tools/greia_simulator_ctl.py status > "$GREIA_EVIDENCE/status_library_idle_before.txt"
sleep 3
python3 tools/greia_simulator_ctl.py status > "$GREIA_EVIDENCE/status_library_idle_after.txt"
```

Look for no obvious perpetual ~30 Hz Shell repaint caused by the static library. If a celebration is naturally available, record the same check. Do not fail solely from an ambiguous counter; report exactly what status shows. Never call this Acer performance evidence.

## Language check

Use the naturally selected device language. Verify no raw localization keys and no accidental mixed-language title/description pairs. If normal product UI can switch language, optional English+Italian visual check is useful; do not invent a simulator-only override.

## Failure protocol

On first mandatory failure: stop, do not edit/retry around it, preserve state, capture screenshot/status/read-only state where possible, and write exact expected vs observed behavior into `results.md`.

## Required results file

Create `./tmp/greia-achievement-simulator-acceptance/results.md` with:

```markdown
# Greia Achievement + Activity Simulator Acceptance Results

## Source
- SHA:
- Branch:
- Host OS:
- Python:
- Pygame:

## Automated gates
- Focused achievement/activity suites: PASS / FAIL
- Simulator contract suite: PASS / FAIL

## A — Initial Badge Library
- Home route:
- Collection route:
- Sub-Collection route: PASS / FAIL / NOT EXERCISED
- Initial count:
- Secret hidden:
- Locked hints:

## B — Clinica Cuccioli
- Out-of-order treatment rejected:
- Five patients completed:
- Completion stable:
- First Friend celebration:
- Dismiss preserved NEW:
- Leaving/reopening cleared NEW:
- Healed event count:
- Global Star after 5 patients:

## C — Restart
- Badge persisted:
- NEW state correct:
- Star/history unchanged:

## D — Memory
- Game completed:
- Completion stable:
- Celebration:
- Event count:
- Global Star:

## E — Bridges
- Three crossings one session:
- Completion count:
- Celebration:
- Star before:
- Star after:
- once-per-session confirmed:

## F — Five Stars
- Second Clinic:
- Second Memory:
- Star exactly 5:
- Handful celebration:
- Library count:
- Secret denominator safe:

## G — Profile isolation
- Second profile created via ProfileStore:
- Second profile 0/6:
- Reward/history isolation:
- Original restored 4/6:
- Original star still 5:

## H — Responsive smoke
- 1024x600 normal:
- 1024x600 large:
- 1280x800 normal:
- 1366x768 compact:
- 1920x1080 normal:
- Clinic:
- Memory:
- Bridges:

## I — Static repaint sanity
- Library:
- Celebration:
- Simulator-only scope noted:

## Language
- Locale:
- Raw keys:
- Mixed fallback errors:

## Final disposition
PASS / FAIL

## First failure, if any
- Step:
- Action:
- Expected:
- Observed:
- Screenshot:
- State evidence:
- Console/error:

## Evidence returned
- list files/directories
```

Return in place, **no ZIP**:

```text
results.md
source_sha.txt
source_commit.txt
git_status.txt
relevant_git_status.txt
python_version.txt
python_prerequisites.txt
focused_tests.txt
simulator_tests.txt
simulator_initial_status.txt
state_*.txt
status_*.txt
screenshots/
```

Do not delete `$HOME/.greia-simulator-achievement-acceptance` until owner reviews evidence.

## PASS definition

PASS only if all mandatory assertions pass. Core invariants:

```text
Activity facts accepted through declared events
Clinic out-of-order treatment cannot advance prescription
5 Clinic heals in one session -> 1 global Greia Star
1 Memory completion session -> 1 additional global Star
3 Bridge completions in one session -> 1 additional global Star
5 global Stars unlock Handful of Stars
popup dismissal does not mark badge seen
leaving Badge Library clears NEW
secret locked badge is invisible and denominator-safe
Stars/achievements persist across restart
Stars/achievements are profile-isolated
Badge Library is usable at tested viewports/interface sizes
```

PASS means **developer/simulator semantic + visual acceptance at the recorded SHA only**; it does not replace physical Acer acceptance.