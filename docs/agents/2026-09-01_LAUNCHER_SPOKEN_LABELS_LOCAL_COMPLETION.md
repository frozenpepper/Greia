# Local completion — Greia launcher spoken labels

**Date:** 2026-09-01  
**Purpose:** finish, test and evidence the launcher-owned localized spoken-name tranche started on `main`.

This is an execution checklist for a competent local agent. Do not redesign the feature while following it.

## 0. Authority and stop conditions

Read, in order:

```text
AGENTS.md
README.md
docs/DOCUMENTATION.md
docs/adr/0012-platform-architecture-constitution.md
docs/adr/0018-lightweight-ui-foundation.md
docs/adr/0028-platform-and-activity-localization-language-context.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
docs/engineering/ENGINEERING_FOUNDATIONS.md
skills/greia-os-work/SKILL.md
skills/greia-activity-authoring/SKILL.md
skills/greia-activity-authoring/VOICE_GENERATION.md
skills/greia-activity-authoring/LAUNCHER_SPOKEN_LABELS.md
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
HANDOVER.md
```

Work directly on current `main`; do not create a branch. Preserve concurrent changes.

STOP and report instead of improvising if:

- current `main` no longer contains `src/greia_launcher/spoken_labels.py`;
- accepted ADR/source authority now defines a different launcher narration service;
- pygame mixer is not the launcher playback owner anymore;
- the current launcher has acquired a different authoritative locale source that conflicts with the assumptions below;
- any test uncovers a platform-authority or Activity-boundary regression.

Do not use GitHub-hosted Actions.

## 1. Confirm starting state

Run:

```bash
git status --short
git log -8 --oneline
python3 -m pytest -q tests/test_launcher_spoken_labels.py
```

Expected repository additions already on `main`:

```text
src/greia_launcher/spoken_labels.py
tests/test_launcher_spoken_labels.py
skills/greia-activity-authoring/LAUNCHER_SPOKEN_LABELS.md
```

The focused test must PASS before integration work. If it fails, fix only the root cause; do not weaken the test.

## 2. Architectural contract — do not deviate

The final flow is:

```text
pointer hover OR keyboard/controller selection
        ↓
Greia Shell semantic destination identity
        ↓
launcher-owned SpokenLabelPlayer
        ↓
locale-aware static clip resolver
        ↓
existing pygame mixer, one interruptible narration channel
```

Activity package responsibility is data only:

```text
locales/<locale>.json
  audio.activity.title.path -> reviewed static WAV/OGG
```

Activity code must know nothing about hover, focus or launcher narration.

Platform Collection/category speech is Greia-owned:

```text
assets/audio/system/launcher-labels/<locale>/<collection_id>.wav
```

No runtime TTS. No subprocess-per-hover `aplay`. No queue of names. No unbounded cache. No new mixer/runtime inside each Activity.

## 3. Wire Activity selection into `GreiaLauncherPresentation`

Edit the current authoritative launcher source, normally:

```text
src/greia_launcher/presentation.py
```

Import:

```python
from .spoken_labels import (
    SpokenLabelPlayer,
    activity_title_audio,
    collection_title_audio,
)
```

Create exactly one player per launcher presentation instance:

```python
self._spoken_labels = SpokenLabelPlayer()
```

### Locale source

Before writing a new locale variable, inspect the current launcher/profile localization implementation.

Use the authoritative resolved **child Shell UI locale** if it now exists.

If the implementation is still in the known migration state where catalogue construction defaults to Italian and no profile locale has yet been wired, introduce one small launcher-owned method/property such as `_catalogue_locale()` that returns the same locale used to build the catalogue. Keep the seam injectable/future-ready. Do NOT read Linux `LANG` as product authority.

Do not create a second localization service.

### Keyboard Activity focus

Whenever arrow navigation actually changes `self._selected`, resolve the newly selected Activity and call:

```python
clip = activity_title_audio(activity, resolved_shell_locale)
self._spoken_labels.announce(
    f"activity:{activity.activity_id}",
    clip,
    pygame,
)
```

Apply the same semantic behavior when page navigation changes the selected Activity.

Rules:

- only announce after the selected identity changed;
- no announcement when an arrow is clamped and selection stays on the same tile;
- no automatic queue;
- absence/corruption of a clip must not affect navigation or launchability.

### Pointer Activity hover

The existing event loop already compares old/new `HitTarget` on `MOUSEMOTION`.

When the semantic target changes:

- if the new target denotes an Activity tile/select target, announce that Activity;
- if it denotes a platform Collection/category, announce that Collection;
- if it denotes neither, call `self._spoken_labels.clear_focus()` so re-entering the same destination can speak again.

Do NOT make every raw `MOUSEMOTION` replay speech.

Do not change click semantics merely to make speech easier.

## 4. Wire Collection-first Home selection

The child Home is currently owned by:

```text
src/greia_launcher/collection_home_presentation.py
```

Its `_set_home_collection_selected(...)` is the correct semantic keyboard-focus seam.

Refactor minimally so the method can announce only when selection identity changes. If it currently lacks `pygame`, either:

1. add a tiny dedicated `_announce_home_collection(pygame)` call in the key handler immediately after a successful selection change; or
2. adjust the setter signature only if that produces the cleaner source and all callers remain obvious.

Do not let this mixin instantiate another player.

Collection clip resolution:

```python
collection_title_audio(
    self.paths.root,
    collection.collection_id,
    resolved_shell_locale,
)
```

Identity:

```text
collection:<collection_id>
```

Pointer hover over `home_collection` targets must use the same player and identity.

## 5. Category/subcollection coverage

Inventory the platform-owned child Collection IDs from current source rather than guessing.

At minimum inspect:

```text
src/greia_launcher/catalogue_view.py
src/greia_launcher/collection_home_presentation.py
src/greia_launcher/adaptive_discovery_presentation.py
```

Expected vocabulary currently includes primary/fallback IDs such as:

```text
create
play
learn
explore
my_greia
browse
all
```

and bounded discovery IDs such as:

```text
drawing
writing
music
building
numbers
words
puzzles
nature
stories
making
care
action
settings
```

Only generate platform clips for IDs that are actually child-facing in current `main`.

## 6. Add source tests for integration

Extend tests without requiring a real audio device.

Required cases:

1. keyboard Activity selection announces the new Activity once;
2. clamped keyboard navigation does not replay the same Activity;
3. page jump that changes selected Activity announces the new Activity;
4. pointer crossing from empty space into Activity A announces A;
5. repeated pointer movement within Activity A does not replay A;
6. pointer A -> Activity B interrupts/replaces A semantically;
7. pointer leaves all speakable targets, then re-enters A -> A may speak again;
8. Collection Home keyboard selection announces one Collection;
9. Collection Home pointer hover uses the same player;
10. missing clip is fail-silent and does not alter selection/launch;
11. corrupt/unloadable clip is fail-silent;
12. locale fallback chooses exact locale, then base language, then allowed compatibility fallback;
13. Activity code remains untouched by launcher speech architecture.

Prefer injected/fake player/resolver seams where practical. Do not initialize a physical mixer in unit tests.

## 7. Add a first-party catalogue audit

Create a small source/build audit, e.g.:

```text
tools/audit_launcher_spoken_labels.py
```

Purpose: first-party release completeness, NOT third-party runtime rejection.

For every built-in Activity and every catalogue locale considered complete, verify:

- localization bundle exists;
- `strings.activity.title` exists;
- `audio.activity.title` exists;
- path is package-relative/safe and resolves inside package;
- file exists;
- suffix is accepted by localization (`.wav` or `.ogg`).

For every child-facing platform Collection locale considered complete, verify the Greia-owned clip exists.

Important: do **not** modify `ActivityRegistry` to reject third-party Activities just because a spoken title is missing. Runtime remains fail-soft; official/built-in release quality is enforced by the audit/build gate.

Add the audit to `make verify` only after its initial migration can pass, or add an explicit migration mode if accepted by existing verification policy. Do not make the repository permanently red with an unclosable gate.

## 8. Update Activity-authoring guidance

Update:

```text
skills/greia-activity-authoring/SKILL.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```

Keep both concise; do not duplicate the full companion text.

In `SKILL.md`, add `LAUNCHER_SPOKEN_LABELS.md` to:

- new Activity creation reading when localization/voice is relevant (preferably universal new-Activity checklist because this is now mandatory first-party catalogue behavior);
- localization/manifest work;
- completion checklist wording.

In `VOICE_GENERATION.md`, add a short subsection pointing to `LAUNCHER_SPOKEN_LABELS.md` and state:

```text
activity.title is mandatory first-party launcher speech per completed catalogue locale;
production uses VoiceEngine;
runtime playback remains Shell-owned.
```

Do not copy the whole companion into either file.

## 9. Platform Collection voice production

Do NOT generate accepted binaries blindly.

First run:

```bash
python3 tools/greia_voice.py doctor
```

Then create review candidates in a temp/review workspace for every current child-facing Collection in the target locales.

For Italian examples the spoken words should match the accepted platform catalogue labels (e.g. `Crea`, `Gioca`, `Impara`, `Esplora`) rather than internal IDs.

Use one consistent approved Greia speaker/voice policy for platform Collections. If the repository does not currently define which canonical voice owns Shell navigation, STOP before accepting binaries and report that small product decision to Otta. Do not choose a random character voice just to close the task.

Human listening is mandatory. Only accepted clips are copied to:

```text
assets/audio/system/launcher-labels/<locale>/<collection_id>.wav
```

## 10. Existing Activity migration inventory

Do not edit Activity Python.

Run an inventory over `activities/*/locales/*.json` and produce a table:

```text
activity_id | locale | displayed activity.title | audio.activity.title present? | candidate generated? | human accepted?
```

For every missing built-in title clip:

- use the Activity's accepted presenter voice when its design clearly has one;
- otherwise follow the launcher-title speaker rule in `LAUNCHER_SPOKEN_LABELS.md` / Voice Production authority;
- generate outside the package;
- retain receipts as required by Voice Production;
- do not mark human acceptance yourself.

Do not bulk-copy unreviewed candidates into runtime packages.

## 11. Verification

After source integration, run at minimum:

```bash
python3 -m pytest -q tests/test_launcher_spoken_labels.py
python3 -m pytest -q tests/test_launcher_state.py tests/test_launcher_presentation.py 2>/dev/null || true
ruff check src/greia_launcher/spoken_labels.py src/greia_launcher/presentation.py src/greia_launcher/collection_home_presentation.py tests/test_launcher_spoken_labels.py
make verify
```

If exact launcher test filenames differ, identify the current corresponding tests and run them. Do not hide real failures with `|| true`; the example above is only to tolerate a non-existent filename during discovery. Once the current files are known, rerun without suppression.

Then run the real Greia Simulator with audio enabled and manually exercise:

```text
A. enter child Home
B. arrow across at least 4 Collections
C. hold/repeat arrow against a boundary
D. move pointer within one Collection target
E. move pointer across 3 Collections quickly
F. enter one Collection
G. arrow across at least 5 Activity cards
H. move pointer across at least 5 Activity cards
I. leave and re-enter the same Activity card
J. launch an Activity after its name is spoken
K. return Home and repeat
```

Expected:

- each new semantic destination speaks once;
- no chatter from raw mouse-motion events inside one tile;
- rapid movement replaces old speech rather than queues a backlog;
- navigation remains responsive while audio plays;
- missing clip is silent, never a crash;
- no Activity code participates;
- no measurable redraw loop is introduced merely for speech.

## 12. Performance evidence

On the Acer-class target when available, capture:

- idle Shell CPU before/after: narration must add effectively zero idle work;
- RSS before/after after visiting many tiles: cache remains bounded;
- input-to-audio-start qualitative/quantitative latency;
- rapid 10-tile traversal: no queued speech after navigation stops;
- Activity launch while a title is playing: launch remains immediate and title stops/does not leak into gameplay if current lifecycle policy requires that.

If physical hardware is unavailable, label this `PHYSICAL-UNVERIFIED`; Simulator evidence is not Acer evidence.

## 13. Documentation and repository closure

Because this is substantive platform implementation, follow `AGENTS.md` exactly:

1. append an accurate dated progress entry to `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`;
2. update `HANDOVER.md` with implemented source, exact tests, audio migration state and remaining human/physical evidence;
3. update `skills/greia-os-work/SKILL.md` only with a concise pointer/rule if this new launcher seam materially changes contributor navigation;
4. update `skills/greia-activity-authoring/SKILL.md` and `VOICE_GENERATION.md` as above;
5. update any product/design doc that owns accepted launcher interaction if spoken hover/focus behavior is now normative;
6. commit coherent changes directly to `main`.

Do not claim the whole feature complete until the current first-party catalogue has human-approved clips for the target locales and the final source state has passed the required Simulator gate. Physical-device acceptance remains separately labeled.

## 14. Evidence to return

Return one concise report containing:

```text
starting main SHA
ending main SHA
files changed
focused pytest result
launcher regression pytest result
ruff result
make verify result
Simulator result
spoken-label audit totals by locale
Collection candidate/accepted totals
Activity candidate/accepted totals
missing/human-review-pending list
physical evidence status
exact next action
```

Attach or preserve generated review receipts according to the existing Voice Production workflow. Do not attach model weights, caches, rejected generations or unrelated build artifacts.
