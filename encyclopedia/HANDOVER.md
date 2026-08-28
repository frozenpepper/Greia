# Greia Encyclopedia workstream handover

**Updated:** 2026-08-28  
**Construction state:** v0.1 source breadth complete and source gate GREEN; headless Shell-route retest pending  
**Runtime pages:** **43 / 43 planned executable pages**  
**Current evidence:** **SOURCE-VERIFIED / SIMULATOR-UNVERIFIED / NARRATION ACCEPTANCE PENDING**  
**Runtime Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)

This is the current continuation contract for the Encyclopedia workstream. Historical construction detail remains in `encyclopedia/PROGRESS.md` and dated reviews.

---

## 1. Frozen v0.1 scope

Exactly 43 executable pages:

```text
home

animals
├── animals.lion
├── animals.elephant
├── animals.octopus
├── animals.bee
├── animals.penguin
└── animals.frog

space
├── space.sun
├── space.mercury
├── space.venus
├── space.earth
├── space.moon
├── space.mars
├── space.jupiter
├── space.saturn
├── space.uranus
└── space.neptune

earth
├── earth.volcano
├── earth.rain
├── earth.ocean
├── earth.tree
└── earth.rainbow

body
├── body.heart
├── body.lungs
├── body.bones
├── body.teeth
└── body.senses

machines
├── machines.gears
├── machines.magnet
├── machines.bicycle
├── machines.airplane
└── machines.bridge

history
├── history.dinosaurs
├── history.fossils
├── history.mammoth
├── history.cave_paintings
└── history.pyramids
```

Do not add v0.1 topics unless the owner deliberately changes scope.

---

## 2. Architecture invariants

- `main.py` stays a thin composition root.
- `enciclopedia_engine.py` owns lifecycle, semantic input, explicit registry and bounded navigation only.
- Subject behavior stays inside page modules.
- Use small domain models only when coupled mutable invariants justify them; do not invent generic exhibit/planet/anatomy/machine/history frameworks.
- Runtime remains offline and low-resource: no runtime TTS, speech recognition, AI/LLM, network factual lookup or heavy physics.
- Greia protected Home remains platform-owned; Encyclopedia internal Back remains distinct.
- Italian and English are the initial locales.
- Visual/text/audio caches remain explicitly bounded.
- The Acer Aspire One-class machine remains the performance floor.

---

## 3. Research and narration authorities

All 36 factual final pages have one provenance/wording authority under:

```text
encyclopedia/research/<section>/<entry>.md
```

The research corpus intentionally contains two historical wording formats; `sync_voice_requests.py` supports both fail-closed.

The canonical voice coordination file is:

```text
encyclopedia/VOICE_RECORDING_REQUESTS.md
```

It is now checked in at exactly:

```text
378 rows
378 REQUESTED
0 RECORDED_UNREVIEWED
0 OWNER_ACCEPTED
```

`378` means request rows, not generated files.

Voice generation remains a separate authoring/parent-machine workflow. Simulator acceptance does **not** wait for those recordings.

Status flow:

```text
REQUESTED
→ RECORDED_UNREVIEWED
→ OWNER_ACCEPTED
```

Only real owner listening can set `OWNER_ACCEPTED`.

Accepted recordings are packaged deterministically with:

```bash
python3 encyclopedia/integrate_voice_assets.py
python3 encyclopedia/integrate_voice_assets.py --check
```

The integrator never generates speech and packages only already-`OWNER_ACCEPTED` rows.

---

## 4. Source gate — GREEN

Green runtime/source commit:

```text
d89809a43cdfe62c85775ccdcfd04eb6e34fbd05
```

Evidence directory:

```text
tmp/encyclopedia-v01-acceptance/20260828_044052/
```

Proven by the owner-machine local agent:

```text
voice-sync                         PASS
voice-sync-check                   PASS
voice rows                         378 / 378
focused Encyclopedia tests          53 / 53 PASS
make verify                       1431 / 1431 PASS
first-party Activity validations    35 / 35 PASS
accepted-audio sync check            PASS (0 OWNER_ACCEPTED rows)
git diff --check                     PASS
worktree postflight                  clean
```

Source-gate summary:

```json
{
  "branch": "main",
  "integration_check_after": "not-applicable",
  "integration_check_before": "PASS",
  "integration_executed": false,
  "simulator_pending": true,
  "starting_sha": "d89809a43cdfe62c85775ccdcfd04eb6e34fbd05",
  "status_counts": {"REQUESTED": 378},
  "voice_rows": 378
}
```

This establishes:

```text
SOURCE-VERIFIED / SIMULATOR-UNVERIFIED
```

Do not rerun the source gate merely to begin Simulator review unless runtime/source files change.

---

## 5. Source drifts already resolved during closure

The source gate successfully exposed and drove fixes for:

- voice-ledger row parser rejecting empty notes;
- synchronizer non-idempotent separator accumulation;
- source-gate silent preflight exits;
- invalid `tests.test_xxx` unittest invocation from non-package `tests/`;
- missing Saturn `## Scope guardrails` authority section;
- stale `org.greia.piccola_serra` test expectation vs authoritative `org.greia.piccola-serra` manifest ID;
- Encyclopedia generic `globe` launcher icon replaced by unique package-owned `assets/icon.png`.

Do not revert these fixes.

---

## 6. Simulator harness evidence and next exact task

Single rolling local-agent instruction:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

### 6.1 First terminal-only Simulator attempt

The first headless attempt failed before launch because the helper republished the already built-in Encyclopedia as developer-unsigned and correctly hit the duplicate-identity guard. That was a **Simulator harness defect**, not Encyclopedia runtime evidence. The helper was changed so built-in Activities launch in place.

### 6.2 Second terminal-only Simulator attempt

Evidence:

```text
tmp/encyclopedia-v01-acceptance/20260828_061732-headless-smoke/
```

Owner-machine report:

```text
FOCUSED_SIMULATOR_TESTS       PASS
HEADLESS_BUILTIN_DETECTION    PASS
SHELL_FIRST_FRAME             PASS
HEADLESS_SMOKE_RC             7
worktree                      clean
```

The real child Shell and remote bridge reached a 1024x600 `mode=profiles` frame. No duplicate-ID collision remained. The run then failed to obtain an Encyclopedia Activity frame.

Review established that the second helper still modeled the launcher incorrectly: it computed a raw ActivityRegistry index and sent RIGHT repeatedly after profile activation. The production child UI is **Collection-first**, so those keys operate on Collection portals, not raw Activity cards.

Current production navigation shape:

```text
profile picker
→ Collection Home
→ optional adaptive sub-Collection
→ Activity cards
→ Activity
```

That harness drift is now repaired:

- headless routing is represented by typed `ShellLaunchRoute`;
- the route is derived from the same profile-visible `ActivityCatalogue` projection used by the child Shell;
- built-in, developer and Parent-installed Activity sources are represented;
- selected-profile visibility, age and challenge policy are applied;
- the route records Collection Home index, optional sub-Collection index and Activity-card index;
- every semantic Shell navigation step requires a fresh real `mode=activities` frame before continuing;
- focused tests cover both direct Collection → Activity and Collection → sub-Collection → Activity routes.

This is still harness work. No Encyclopedia runtime failure should be claimed until the corrected route actually reaches `mode=activity` and the Activity itself fails.

### 6.3 Next exact gate

Run the rolling prompt above. It performs only:

```text
focused Simulator tooling tests
one real built-in Encyclopedia headless smoke
profile → Collection Home → optional sub-Collection → Encyclopedia
first Encyclopedia frame
12 s survival + one bounded interaction
protected Home → Shell
```

Do **not** run the 43-page traversal until that smoke is green.
Do **not** rerun the 1431-test source gate.
Do **not** generate voices.

After the headless smoke is green, the next tranche is mechanical 43-page reachability/interactions/screenshot capture. Subjective pre-reader/no-reading and visual-quality judgment remains a separate human/vision review rather than a terminal-agent claim.

Missing narration is always reported separately:

```text
NARRATION ACCEPTANCE PENDING
```

It is not a reason to add runtime TTS and is not itself a blocker for visual/input Simulator acceptance.

If every later Simulator/input/pre-reader/responsive gate passes, the exact truthful label becomes:

```text
SOURCE + SIMULATOR ACCEPTED / NARRATION ACCEPTANCE PENDING
```

---

## 7. Evidence authority

Canonical reusable runbook:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md
```

Current one-step operator prompt:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

Durable reviews:

```text
docs/reviews/2026-08-27_ENCYCLOPEDIA_V01_POST_BUILD_DRIFT_REVIEW.md
docs/reviews/2026-08-27_ENCYCLOPEDIA_V01_CLOSURE_TOOLING_REVIEW.md
```

Physical Acer/Pi acceptance and complete owner-approved narration coverage remain separate later gates.
