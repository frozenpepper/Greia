# Greia Encyclopedia workstream handover

**Updated:** 2026-08-28  
**Construction state:** v0.1 source breadth complete and source gate GREEN; Simulator acceptance is next  
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

## 6. Next exact task — Simulator/UX acceptance

Single rolling local-agent instruction:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

It now performs **Simulator-only acceptance**. It must not rerun the 1431-test source gate and must not generate voices.

The Simulator pass must establish on the frozen runtime state:

```text
launch + >=10 s survival
all 6 sections reachable
all 36 factual entries reachable
all 36 signature interactions visibly work
internal Back works across traversal
protected Greia Home + clean return to Shell
pointer vs semantic-keyboard parity on:
  animals.octopus
  space.saturn
  earth.volcano
  body.heart
  machines.gears
  history.fossils
mandatory pre-reader/no-reading review
responsive sample across required viewport/profile presets
```

Missing narration is reported separately:

```text
NARRATION ACCEPTANCE PENDING
```

It is not a reason to add runtime TTS and is not itself a blocker for the visual/input Simulator pass.

If every Simulator/input/pre-reader/responsive gate passes, the exact truthful label becomes:

```text
SOURCE + SIMULATOR ACCEPTED / NARRATION ACCEPTANCE PENDING
```

If a blocking runtime/Simulator defect appears:

```text
SOURCE-VERIFIED / SIMULATOR-FAILED
```

Stop and preserve evidence; do not repair inside the acceptance run.

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