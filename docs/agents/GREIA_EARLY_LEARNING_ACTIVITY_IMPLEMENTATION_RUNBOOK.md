# Greia Early-Learning Activities — Local Agent Implementation & Acceptance Runbook

**Date:** 2026-08-24  
**Audience:** local coding/test agent working in the canonical `frozenpepper/Greia` checkout  
**Purpose:** complete, verify, visually review, audio-review where needed, and commit the ten Activities in `docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/` without weakening Greia architecture or evidence standards.

This is an execution handoff, not a replacement for the Activity skill or the per-Activity plan. **Work on one Activity at a time.** For each Activity, the plan file defines *what the Activity must be*; `skills/greia-activity-authoring/SKILL.md` defines *how to author/test one Greia Activity*.

---

## 0. Non-negotiable operating rules

1. Work directly on `main`; do not create a branch unless the owner explicitly asks.
2. Before each Activity tranche:
   ```bash
   git pull --ff-only origin main
   git status --short
   git rev-parse HEAD
   ```
   Stop if the tree contains unknown/unowned changes.
3. Read `AGENTS.md`, `SETUP.md`, `HANDOVER.md`, the named Activity plan file, and `skills/greia-activity-authoring/SKILL.md`.
4. Follow only the task-specific routes selected by the Activity skill. Do **not** turn the skill into a portfolio workflow.
5. Keep `main.py` a composition root. Do not collapse a game into a giant script because it is faster to type.
6. Reuse Greia platform services for lifecycle, protected Home/Back, viewport/input, storage, localization, typography, shared visuals, events, and completion.
7. Do not add a new platform abstraction merely because two new Activities look superficially similar. Promote only after semantics recur and platform ownership is clear.
8. Never claim Simulator or physical evidence unless it actually ran against the exact final SHA.
9. Never fabricate a human language/audio review. A successful generator or test process is not human review.
10. Do not install/download Chatterbox, model weights, or another large voice stack unless the owner explicitly requests toolchain installation. Existing setup only.
11. Do not use hosted GitHub Actions.
12. Do not package `.pyc`, `__pycache__`, model caches, review WAV masters, temporary screenshots, or local test state.

---

## 1. Current checkpoint

The first Activity, `activities/luci_di_momo`, has been started as a modular source implementation.

Current intended module ownership:

```text
activity.toml
main.py                 thin composition root
firefly_model.py        immutable rounds + session truth + bounded adaptation
firefly_services.py     Greia Storage/event adapters
firefly_audio.py        bounded nonverbal prepared cues
firefly_art.py          baked background + shared Momo preparation/fallback
firefly_renderer.py     1024x600 presentation + stable hit geometry
firefly_app.py          lifecycle, phases, input, READY/STOP, terminal state
locales/it.json
locales/en.json
assets/source/icon.svg
assets/icon.png
tests/test_activity_luci_di_momo.py
```

The source was authored against the current Activity skill and current platform APIs. The handoff author locally exercised the pure/domain/storage tests in an isolated stubbed platform context and stress-generated 1,000 seeds at each of four levels. **That is not Greia repository validation or Simulator evidence.**

Luci di Momo (`activities/luci_di_momo`) source implementation, platform contract integration, visual review, and test gates are **COMPLETE & ACCEPTED**.

Status:
```text
IMPLEMENTED
LOCAL DOMAIN & INTEGRATION TESTS PASS (10/10)
GREIA SOURCE & PLATFORM VALIDATION PASS (21/21 activities valid, 1198 unit tests green)
VISUAL REVIEW COMPLETE (vector reload arrow, 1024x600 + multi-res review)
AUDIO: Nonverbal synthesis prepared
SIMULATOR SUPERVISOR PASS
```

Next Activity: `activities/casa_del_dieci` (`02-casa-del-dieci.md`).

---

## 2. First job: finish and accept Luci di Momo

### 2.1 Read the exact authorities

```bash
sed -n '1,240p' skills/greia-activity-authoring/SKILL.md
sed -n '1,260p' skills/greia-activity-authoring/ENGINEERING.md
sed -n '1,260p' skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
sed -n '1,240p' skills/greia-activity-authoring/TERMINAL_RENDERING.md
sed -n '1,240p' skills/greia-activity-authoring/ACHIEVEMENTS.md
sed -n '1,240p' skills/greia-activity-authoring/DISCOVERY.md
sed -n '1,320p' skills/greia-activity-authoring/VOICE_GENERATION.md
sed -n '1,260p' docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/01-luci-di-momo.md
```

For visual work, route through:

```bash
sed -n '1,260p' skills/greia-visual-authoring/SKILL.md
```

Then read only the visual docs selected by that router.

### 2.2 Inspect before editing

Check every Luci file. Do not blindly rewrite it.

Verify specifically:

- `main.py` stays thin and imports work in both script and package contexts.
- `FireflyRoundFactory` is deterministic under an injected seed.
- every round has one answer and two unique distractors;
- fireflies are at least 72 logical px apart and remain inside the safe playfield;
- L1 uses 1–3 / 1600 ms, L2 1–4 / 1400 ms, L3 1–5 / 1200 ms, L4 1–5 / 1100 ms;
- replay never advances or counts as failure;
- wrong answer never changes the challenge identity and shows the same quantity one-by-one;
- five correct completed rounds produce one terminal completion fact;
- event ID is exactly `firefly.garden_completed`;
- no click/action telemetry exists;
- history is bounded to 8;
- terminal state freezes gameplay animation;
- hidden controls are not clickable (replay only while visible);
- pointer coordinates are mapped through the same Greia canvas used for rendering;
- protected system chrome input is rejected;
- Momo is loaded through semantic shared visual `character.momo`, with a harmless Activity-local fallback;
- images/fonts/backgrounds are prepared, not rebuilt in the hot loop;
- static choice and terminal screens do not repaint continuously.

### 2.3 Run focused source tests

From repository root:

```bash
find activities/luci_di_momo -type d -name __pycache__ -prune -exec rm -rf {} +
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_luci_di_momo -v
PYTHONPATH=src:tools python3 tools/validate_activity.py activities/luci_di_momo
```

Expected:

```text
all Luci tests PASS
validate_activity prints PASS org.greia.luci-di-momo 0.1.0
no traceback
```

If either command fails: **stop acceptance, fix the root cause, rerun both.**

### 2.4 Run the relevant cumulative source gate

```bash
PYTHONPATH=src:tests:. python3 -m unittest \
  tests.test_activity_luci_di_momo \
  tests.test_activity_contract \
  tests.test_activity_audience_manifest \
  tests.test_first_party_activity_audience_metadata \
  tests.test_first_party_activity_readiness \
  tests.test_core_activity_system_safe_ui \
  tests.test_activity_ui \
  tests.test_activity_viewport \
  tests.test_localization \
  tests.test_typography_emoji -v
```

Then:

```bash
make verify
git diff --check
```

Do not hide unrelated pre-existing failures. Record them accurately and distinguish them from regressions introduced by this tranche.

### 2.5 Simulator launch acceptance — mandatory

Read:

```text
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
```

Launch using the canonical repository procedure, currently:

```bash
python3 tools/greia_simulator.py
```

Load `activities/luci_di_momo` using **Load Activity Folder…**, not by copying files into simulator state.

At minimum verify on 1024×600:

1. Activity appears in the launcher.
2. Italian launch shows a usable first frame.
3. Keep it running for >=10 seconds.
4. Let a reveal finish.
5. Press a wrong numeral: same round remains; fireflies replay one-by-one; no score/life loss.
6. Press replay: same round remains; reveal repeats; replay button is not active while hidden.
7. Complete all five rounds.
8. Verify one opaque completion screen, no active firefly animation underneath.
9. Press Play Again and verify a fresh valid set.
10. Use protected Greia Home and return cleanly to Shell.
11. Repeat the materially relevant flow in English.
12. Resize/use at least one non-reference Simulator size supported by the current acceptance docs and confirm no clipped answer/replay targets.

If any import/startup/first-interaction/restart/Home failure occurs, Luci is **FAILED**, not “mostly working.” Fix and rerun from the beginning against the new final source state.

### 2.6 Visual review

Inspect actual rendered screenshots. Reject programmer-looking placeholder art, Momo floating/detached from scene, undersized targets, system chrome overlap, firefly size/spacing leaking the answer, illegible numerals, replay controls that imitate system chrome, moving gameplay behind the completion card, or severe scaling artifacts.

If Luci needs better local firefly/lantern art, create/review Activity-local source masters under `assets/source/` and package flattened runtime assets. Do not modify canonical shared Momo in place.

### 2.7 Luci audio/voice decision

**Do not generate a custom Momo voice merely because Momo is on screen.**

Luci teaches visual quantity. The current v1 source intentionally uses only nonverbal feedback. This is acceptable and preferred.

If the owner later explicitly wants a mascot line:

1. read `VOICE_GENERATION.md`;
2. first check whether a shared Momo semantic family (`praise.general`, `celebrate.success`, `encourage.retry`, etc.) is sufficient;
3. only create custom Momo dialogue when unique wording is product-required;
4. use canonical Momo voice `greia.momo.v1` through the already-configured Chatterbox Multilingual V3 path;
5. human-review every generated recording;
6. package only accepted playback files, never the model/reference environment.

No spoken number is needed for Luci v1. If a future level teaches the *spoken number word itself*, classify that cue as pedagogical speech rather than Momo character dialogue.

### 2.8 Evidence to return for Luci

Return exact tested SHA, focused test output, validator output/package digest, `make verify`, Simulator locale/resolution/survival observations, wrong/replay/correct/full-session/restart/Home results, screenshots/evidence paths, event/idempotency observation, storage bound observation, visual disposition, audio disposition, and remaining physical evidence boundary.

Update `HANDOVER.md` and the applicable plan progress/evidence before the commit that claims acceptance.

---

## 3. Then implement the remaining Activities — one at a time

Do not open ten code-editing tranches at once. Finish the current Activity’s source/Simulator gate before moving to the next unless the owner explicitly chooses parallel WIP.

Order and specification authority:

```text
02-casa-del-dieci.md
03-bottega-delle-misure.md
04-specchi-magici.md
05-festa-delle-rime.md
06-officina-dei-suoni.md
07-posta-di-leo.md
08-tre-carte-una-storia.md
09-nanna-delle-nuvolette.md
10-morbidi-mostriciattoli.md
```

For **every** Activity:

1. pull latest `main`;
2. read its plan file;
3. read `skills/greia-activity-authoring/SKILL.md`;
4. follow only the skill routes the Activity actually needs;
5. inspect current platform APIs before naming or using an API;
6. implement cohesive model/app/render/services ownership;
7. add focused tests;
8. validate the package;
9. run relevant cumulative tests and `make verify`;
10. run final-source Simulator acceptance;
11. visually inspect actual rendered output;
12. add/review audio only if semantic purpose requires it;
13. update docs/handover;
14. commit the coherent Activity tranche to `main`;
15. only then start the next Activity.

---

## 4. Activity-specific traps and required checks

### Casa del Dieci

Plan: `02-casa-del-dieci.md`

Before coding, repair/clarify these specification inconsistencies in the plan itself:

- the plan currently describes L1 but declares adaptive range `2–5`; the implemented manifest/range must include every reachable level;
- L1 target values 2–5 alone provide only four values, while the plan asks for six unique challenge tuples. Define uniqueness across the complete challenge tuple or amend the requirement. Do **not** fake uniqueness by duplicate semantic challenges with different IDs.

Verify fixed 2×5 ten-frame truth, no result above 10 or below zero, one semantic action for pointer/keyboard, no timed arithmetic/shame. Dani speech, if genuinely needed, uses `greia.dani.system-v1`, never cloning.

### Bottega delle Misure

Plan: `03-bottega-delle-misure.md`

Repeated units must be equal-sized with no gaps/overlap; decorative parcel size must not leak the answer; measurement truth belongs in the model rather than rendered pixel width; keep targets child-sized. Do not add custom mascot voice unless unique dialogue genuinely adds value.

### Specchi Magici

Plan: `04-specchi-magici.md`

Model-test reflection/orientation truth; do not reduce the loop to free shape placement; cache finite transformed piece surfaces instead of per-frame rotation/scaling; freeze terminal state.

### Festa delle Rime

Plan: `05-festa-delle-rime.md`

This Activity **does require reviewed pedagogical speech**. Do not use Leo’s cloned character voice to teach rhyme targets.

Required flow:

```text
accepted per-locale corpus
-> approved deterministic/native pedagogical speech provider
-> WAV review masters OUTSIDE package
-> named fluent human review of every cue
-> reject/regenerate bad cues
-> copy only accepted OGG/WAV into package
-> hash parity between review record and package
```

Use the plan’s generation tool contract: `tools/generate_festa_delle_rime_audio.py`. Do not invent a different provider inside the Activity. Keep speech queue <=4 and prove no overlap.

### Officina dei Suoni

Plan: `06-officina-dei-suoni.md`

Also **requires reviewed pedagogical speech**. The phoneme/sound itself is educational truth. Never use Leo clone for isolated phonemes; never infer segmentation from string length; never enable advanced levels when the reviewed corpus says `omitted_v1`; never splice an incorrect generated phoneme until it appears correct.

Use `tools/generate_officina_dei_suoni_audio.py` and the same review-master/hash discipline as Festa.

### Posta di Leo

Plan: `07-posta-di-leo.md`

This is a bounded postcard creator, not a second Writing Activity. Preserve invented spelling/marks; save profile-scoped bounded data; emit creation only after durable save. For generic Leo praise/help, prefer shared semantic utterance families. Use custom Leo `greia.leo.v1` only for genuinely unique dialogue.

### Tre Carte, Una Storia

Plan: `08-tre-carte-una-storia.md`

Keep event-order/cause-effect truth in model/content, not renderer coordinates; caption entry remains small/purposeful; do not duplicate Teatrino Fiabe; prefer shared character utterances before custom cloned lines.

### Nanna delle Nuvolette

Plan: `09-nanna-delle-nuvolette.md`

This is calm open-ended age-3 play. Reject score, lives, countdown, rapid flashing, forced finish, or correctness pressure. Voice is optional; prefer silence/gentle nonverbal sound rather than filling silence with cloning.

### Morbidi Mostriciattoli

Plan: `10-morbidi-mostriciattoli.md`

Activity-owned portraits cannot mutate profile avatar; composition/save data is bounded; touch/pointer targets are large; creation event occurs only after durable save. No voice needed unless a unique product requirement appears.

---

## 5. Voice production decision tree for every Activity

Before generating anything, classify each cue:

```text
Is the sound/word/phoneme itself being taught?
  YES -> pedagogical_speech
  NO  -> continue

Is it Dani speaking?
  YES -> dani_system_speech (`greia.dani.system-v1`)
  NO  -> continue

Is it generic praise/retry/celebration/readiness?
  YES -> shared_character_utterance family
  NO  -> continue

Is unique character wording genuinely required?
  YES -> character_dialogue with canonical character voice
  NO  -> do not generate speech
```

Canonical custom character voices:

```text
Lilli  greia.lilli.v1
Leo    greia.leo.v1
Flash  greia.flash.v1
Tito   greia.tito.v1
Momo   greia.momo.v1
Dani   greia.dani.system-v1 (system speech, not cloning)
```

For Lilli/Leo/Flash/Tito/Momo custom lines, use the already configured **Chatterbox Multilingual V3** workflow in:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md
```

Do not install it just because this runbook mentions it.

Human-review custom character audio for voice identity, language, exact wording, pronunciation/stress, clipped starts/ends, extra generated tails, noise/distortion, and appropriate child-facing delivery. Human-review pedagogical audio even more strictly: any ambiguous/wrong target sound is a reject.

Keep review masters outside the Activity package. Package only accepted final playback assets.

---

## 6. Source quality checklist before every commit

Reject the tranche yourself if any answer is “yes”:

```text
Is main.py becoming the game?
Is one module >~500 lines because unrelated responsibilities were combined?
Is a method >~80 lines because transition + IO + rendering are mixed?
Is there Activity-local Home/Back?
Is raw physical controller/microphone ownership being added?
Is there per-frame decode/smoothscale/font creation/filesystem IO/storage write?
Is there an unbounded cache/history/queue?
Is a new platform abstraction being invented for one Activity?
Is localization bypassed by hard-coded child-facing strings?
Is the Activity awarding Stars/badges directly?
Are undeclared events emitted?
Can hidden/offscreen controls still receive input?
Does a terminal state continue running the active simulation?
Is generated audio being accepted without human listening?
Is custom character voice being used for pedagogical phonemes/letters?
```

If yes: fix before committing.

---

## 7. Commit/evidence discipline

Prefer one coherent commit per Activity after the final-source Simulator gate. If a source tranche must be committed before Simulator access exists, use accurate status such as `IMPLEMENTED, LAUNCH ACCEPTANCE PENDING` or `SOURCE-VERIFIED / SIMULATOR-UNVERIFIED`.

After the final runtime-relevant edit, rerun the Simulator gate. Earlier Simulator evidence becomes stale.

At the end of each Activity, update:

```text
HANDOVER.md
the Activity plan/session evidence
applicable visual progress docs if visual work materially changed them
skills/greia-activity-authoring/* only if a genuinely reusable single-Activity authoring lesson changed
```

Do not alter the Activity skill merely to encode this ten-Activity portfolio’s order or project management.
