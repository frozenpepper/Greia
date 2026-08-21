# Greia Primary Collection Vocabulary — Activity Simulator Acceptance

**Status:** owner/local-agent acceptance protocol  
**Date:** 2026-08-21  
**Evidence class:** `SIMULATOR VISUAL REVIEW` for visible behavior  
**Required execution path:** Greia Activity Simulator, headless preferred  
**Target source:** `ActivityCatalogue` primary-Collection projection + Collection-first Home

## 1. Purpose

Collection-first Home is accepted, but the first simulator run exposed one important information-architecture defect: arbitrary Activity presentation categories could manufacture additional top-level Home destinations. The built-in Clinic Activity therefore produced a sixth `Care` portal even though Greia's platform-owned primary Home vocabulary is:

```text
create
play
learn
explore
my_greia
```

This gate verifies the correction:

- package metadata does **not** get to proliferate Greia Home;
- recognized primary categories still project normally;
- an Activity with no recognized primary category is **not hidden** and instead appears through the bounded platform-owned `More`/`Altro` fallback;
- education taxonomy remains separate from child navigation.

This is not adaptive sub-Collection acceptance and does not implement Parent visibility or age/development policy.

## 2. Hard constraints

- Runtime/visual/input acceptance is through the Activity Simulator only.
- Use `GREIA_SIMULATOR_HEADLESS=1`.
- Do not use GitHub Actions.
- Do not substitute direct pytest/unittest/make-verify output for simulator acceptance.
- No new visual asset is required for this gate; do **not** create one.
- Work inside the repository tree; do not use filesystem-root `/tmp`.
- Keep evidence under `tmp/collection-primary-vocabulary-evidence/`.
- Do not change the five primary Collection IDs merely to make a fixture pass.
- Do not hide an otherwise valid unknown-category Activity.
- Commit and push accepted fixes/results to canonical `main`.

## 3. Preparation

From repository root:

```bash
git status --short
git branch --show-current
git pull --ff-only origin main

export GREIA_SIMULATOR_HEADLESS=1
export GREIA_SIMULATOR_STATE="$HOME/.greia-simulator-primary-vocabulary"
rm -rf "$GREIA_SIMULATOR_STATE"
rm -rf tmp/collection-primary-vocabulary-evidence
mkdir -p tmp/collection-primary-vocabulary-evidence
python3 tools/greia_simulator.py --state-dir "$GREIA_SIMULATOR_STATE"
```

Use only the loopback simulator bridge:

```text
http://127.0.0.1:8767
```

## 4. Baseline built-in Home — mandatory

At `1024×600`, interface size `normal`:

1. select a child profile;
2. capture Collection Home;
3. verify the built-in Home contains only the non-empty members of the platform primary vocabulary:
   - `Crea` / Create;
   - `Gioca` / Play;
   - `Impara` / Learn;
   - `Esplora` / Explore;
   - `Mio Greia` / My Greia;
4. specifically verify there is **no top-level `Care` portal**;
5. verify there is no `Altro` / `More` fallback for the normal built-in catalogue when every built-in Activity has a recognized primary destination;
6. verify the Home still uses the accepted portal/panel/profile visual composition.

Capture:

```text
tmp/collection-primary-vocabulary-evidence/01-home-primary-only.png
tmp/collection-primary-vocabulary-evidence/01-status.json
```

Reject if arbitrary metadata such as `care`, `empathy`, `art`, `geometry`, or other package/education tags becomes a new Home portal.

## 5. Clinic recoverability — mandatory

The former `Care` portal must disappear **without losing the Clinic Activity**.

1. enter `Gioca` / Play;
2. verify `Clinica dei Cuccioli` is present and launchable through its normal Activity identity;
3. return through normal lifecycle;
4. enter `Impara` / Learn;
5. verify the same Clinic Activity is also present there according to its corrected presentation metadata;
6. verify there is still only one package/session/save identity.

Capture:

```text
tmp/collection-primary-vocabulary-evidence/10-clinic-play.png
tmp/collection-primary-vocabulary-evidence/11-clinic-learn.png
```

This proves that `caregiving`/health concepts remain education taxonomy rather than becoming a permanent Home level.

## 6. Unknown-only package fallback — mandatory synthetic catalogue case

Create a disposable developer Activity fixture **inside the repository-local `tmp/` tree**, not under `activities/` and not under filesystem-root `/tmp`.

Use:

```text
tmp/collection-primary-fixture/unknown_only/
```

Create a valid minimal Activity package with:

```toml
[activity]
id = "org.greia.acceptance.unknown-only"
title_key = "Unknown-only acceptance"
version = "0.1.0"
icon = "backpack"
languages = ["en", "it"]

[presentation]
categories = ["storybook"]

[education]
categories = ["acceptance_fixture"]
difficulty = 1
skills = []
events = []

[runtime]
type = "python"
api_version = "0.1"
entrypoint = "main.py"

[input]
profile = "hybrid"

[requirements]
required_capabilities = ["display"]
optional_capabilities = ["keyboard", "pointer"]

[permissions]
requested = []

[storage]
schema_version = 1
```

Create `main.py` as a minimal valid Python entrypoint only as required by package validation. Do not launch this fixture unless necessary.

Restart the simulator with the fixture root supplied through the existing developer-Activity source environment used by Greia:

```bash
export GREIA_DEVELOPER_ACTIVITY_ROOT="$PWD/tmp/collection-primary-fixture"
```

Use a fresh isolated simulator state if necessary.

Verify:

1. there is **no `Storybook` top-level portal**;
2. a bounded `Altro` / `More` portal appears because one valid Activity otherwise has no recognized primary destination;
3. entering `Altro` / `More` shows `Unknown-only acceptance`;
4. the ordinary five primary Collections remain unchanged;
5. the fixture is not duplicated into unrelated primary Collections;
6. Back returns `More → Collection Home → profile picker` with the normal hierarchy.

Capture:

```text
tmp/collection-primary-vocabulary-evidence/20-home-with-more.png
tmp/collection-primary-vocabulary-evidence/21-more-open.png
tmp/collection-primary-vocabulary-evidence/22-more-back-home.png
```

After this case, stop the simulator, unset the developer root and remove only the disposable fixture:

```bash
unset GREIA_DEVELOPER_ACTIVITY_ROOT
rm -rf tmp/collection-primary-fixture
```

Do not commit the fixture.

## 7. Multi-membership regression

Using the normal built-in catalogue, verify one Activity with several recognized primary memberships still appears in each relevant Collection without package/state duplication.

Capture at least one representative pair under:

```text
tmp/collection-primary-vocabulary-evidence/30-multi-*.png
```

## 8. Navigation regression

Verify:

- Home arrows/Tab move among visible primary portals;
- Enter/click opens the selected Collection;
- in-Collection local Back returns to Home;
- Home Back/Escape returns to profile picker;
- no hidden keyboard path cycles into an arbitrary package category because arbitrary package categories are not launcher Collections.

Capture one Home and one opened-Collection keyboard state.

## 9. Responsive matrix

Exercise the normal built-in Home at:

| Row | Viewport | Interface size |
|---|---:|---|
| 1 | 1024×600 | normal |
| 2 | 1024×600 | large |
| 3 | 1280×800 | normal |
| 4 | 1366×768 | compact |
| 5 | 1920×1080 | normal |
| 6 | 1111×700 | normal |

For each row verify:

- only recognized non-empty primary Collections appear;
- no `Care` portal;
- no unnecessary `More` portal in the built-in catalogue;
- portal geometry remains circular and unclipped;
- profile control and panel remain intact.

Store screenshots/status using `50-...` through `55-...` names.

The synthetic unknown-only `More` case only needs `1024×600 normal` plus one larger viewport unless a layout defect is found.

## 10. Frame sanity

Measure 10 seconds on the normal Collection Home and record:

```text
tmp/collection-primary-vocabulary-evidence/frame-before.json
tmp/collection-primary-vocabulary-evidence/frame-after.json
```

Use this only as simulator regression evidence against Greia's intended ~30 FPS clock. Do not claim physical Acer/Pi performance.

## 11. Fix policy

If anything fails:

- fix the shared projection/root cause;
- do not add per-Activity special cases to the launcher;
- do not create a `care` Home portal just for Clinic;
- do not silently discard unknown-only Activities;
- do not reinterpret `education.categories` as permanent child navigation;
- do not add arbitrary package categories to the platform primary vocabulary;
- do not add another hierarchy level;
- preserve registry/runtime/trust/lifecycle authority;
- rerun baseline plus every affected simulator case.

## 12. Required result/documentation updates

On acceptance update:

```text
LOCAL_AGENT_RESULT.md
HANDOVER.md
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
```

Record accurately:

- five platform-owned primary Collection IDs;
- arbitrary presentation categories do not manufacture Home destinations;
- unknown-only valid Activities use the bounded `browse`/`More` recovery destination;
- Clinic is reachable through Play/Learn rather than a top-level Care Collection;
- adaptive sub-Collections remain a separate future gate.

## 13. Git completion

After accepted fixes/docs:

```bash
git status --short
git add -A
git commit -m "accept bounded primary Collection vocabulary in simulator"
git pull --rebase origin main
git push origin main
git rev-parse HEAD
```

Do not force-push.

Return the canonical SHA and a concise PASS / SOURCE-NOT-EXERCISED / FAIL matrix.
