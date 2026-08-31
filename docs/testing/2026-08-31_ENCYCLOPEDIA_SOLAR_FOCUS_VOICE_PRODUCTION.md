# Greia Encyclopedia — Solar-System Focus-Name Voice Production

**Date:** 2026-08-31  
**Batch authority:** `encyclopedia/VOICE_RECORDING_REQUESTS.md` → `E6-FOCUS-01`  
**Production authority:** `skills/greia-voice-production/SKILL.md`  
**Runtime rule:** prerecorded audio only; no runtime TTS

## 1. Purpose

The interactive Space page now has left/right focus navigation and a de-duplicated focus-audio hook. The remaining product requirement is real prerecorded speech for the focused body name.

This protocol produces and reviews exactly the existing `E6-FOCUS-01` requests. It does not invent new wording, cue IDs, speakers or backend choices.

Target bodies:

```text
Sun
Mercury
Venus
Earth
Moon
Mars
Jupiter
Saturn
Uranus
Neptune
```

Both supported locales are required by the existing ledger batch, for 20 requested cues total.

## 2. Preconditions

From a clean current Greia checkout:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git status --short --untracked-files=all
git rev-parse HEAD
```

Read:

```text
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
encyclopedia/VOICE_RECORDING_REQUESTS.md
```

Do not invoke Chatterbox, `mlx_audio`, Whisper, macOS `say`, FFmpeg trimming or reference files directly. `tools/greia_voice.py` owns all backend mechanics.

## 3. Doctor

Run the non-mutating probe:

```bash
python3 tools/greia_voice.py doctor \
  | tee ./tmp/encyclopedia-e6-focus-voice-doctor.json
```

If the required Leo production provider/reference is unavailable, stop and report the doctor output. Do not silently switch to another character or provider.

## 4. Build the batch from ledger authority

Create:

```text
./tmp/encyclopedia-e6-focus-01/requests.jsonl
```

Populate it from the 20 `E6-FOCUS-01` rows in `encyclopedia/VOICE_RECORDING_REQUESTS.md`.

For each row preserve exactly:

```text
speaker
kind
locale
exact text
cue ID
```

Use the row's exact reviewed body name as `text`; do not paraphrase or add articles/explanations.

All requests in this batch use the semantic speaker/kind specified by the ledger. The caller must not choose a model/backend.

Generate review outputs under:

```text
./tmp/encyclopedia-e6-focus-01/review/<locale>/
```

Do **not** generate directly into package/runtime asset locations.

Each JSONL object should have the semantic fields accepted by the engine, e.g.:

```json
{"speaker":"leo","kind":"character_dialogue","locale":"it","text":"Terra","cue_id":"<ledger cue>","output_path":"./tmp/encyclopedia-e6-focus-01/review/it/<review-name>.ogg"}
```

Use the actual ledger values for every row.

## 5. Generate with one warm batch worker

Run:

```bash
python3 tools/greia_voice.py batch \
  --input ./tmp/encyclopedia-e6-focus-01/requests.jsonl \
  | tee ./tmp/encyclopedia-e6-focus-01/batch-results.json
```

Do not launch parallel Chatterbox/model workers.

Generation success is not owner acceptance.

Expected mechanical result:

```text
20 requested rows processed
20 review audio outputs produced
no competing-worker error
no missing output path
```

If one row fails, preserve successful outputs and report the failed row. Do not regenerate the entire batch blindly unless the production engine requires it.

## 6. Human review

Listen to all 20 review files.

For each cue review:

```text
exact word/name
correct locale
Leo identity
pronunciation
no clipping or cut tail
no extra words
no doubled/repeated name
comfortable level on small speakers
natural short-utterance delivery
```

The voice engine may provide ASR/verification evidence, but that does not replace listening or owner acceptance.

Record a review table under:

```text
./tmp/encyclopedia-e6-focus-01/review-disposition.md
```

Use only:

```text
OWNER_ACCEPTED
REGENERATE
REJECTED
```

If owner review is not available yet, leave every otherwise usable cue as:

```text
HUMAN_REVIEW_PENDING
```

Do not integrate pending cues.

## 7. Bounded regeneration

Regenerate only cues marked `REGENERATE`.

Use the same semantic text/cue/locale/speaker. Do not alter wording merely to make the synthesis engine easier unless the owner explicitly approves a wording change and the ledger is updated first.

After regeneration, listen again and update the disposition table.

## 8. Integration after owner acceptance

Only after all 20 rows are owner-accepted:

1. install the accepted OGGs into the Encyclopedia package using the repository's existing authoring/package audio layout;
2. add the matching cue mappings to both `activities/enciclopedia_greia/locales/it.json` and `en.json`;
3. update the `E6-FOCUS-01` ledger rows from `REQUESTED` to the repository's accepted state and record the accepted file/receipt information required by the voice workflow;
4. do not alter factual/narration cues unrelated to this batch.

The runtime mapping must resolve the exact cue IDs already emitted by the Space focus logic.

## 9. Audio regression checks

After integration, run the focused Encyclopedia suite plus the interaction tests:

```bash
PYTHONPATH=src /opt/homebrew/bin/python3.12 -m unittest \
  tests.test_activity_enciclopedia \
  tests.test_encyclopedia_interactions
```

Add/retain a regression proving:

```text
all ten Space focus-name cue IDs resolve in Italian
all ten resolve in English
focus transition announces once
repeated POINTER_MOVE inside the same target does not restart the same name
changing target allows the new target name to play
```

Then run:

```bash
make PYTHON=/opt/homebrew/bin/python3.12 verify
```

## 10. Runtime spot check

Run Space through the real Greia Simulator/Shell path.

At minimum exercise:

```text
Earth -> Moon -> Mars -> Jupiter -> Saturn
then back toward Earth
```

Listen for:

```text
one name per focus transition
correct body name
no overlapping/restarting spam
no need to click the moving planet itself
normal orbit animation while audio plays
```

This audio spot-check complements, but does not replace, the separate visual interactive-runtime review.

## 11. Commit discipline

Keep production/review staging under ignored `./tmp` paths.

After all cues are accepted, prefer one bounded integration commit containing only:

```text
accepted E6-FOCUS-01 audio assets
Italian/English locale mappings
voice ledger status/receipts required by project policy
focused audio regression tests if needed
```

Do not mix unrelated Encyclopedia art or interaction redesign into the audio commit.

## 12. Required report

```text
ENCYCLOPEDIA_E6_FOCUS_VOICE_REPORT

source_sha:
doctor:
requests_count:
generated_count:
generation_failures:

review:
  owner_accepted:
  regenerate:
  rejected:
  pending:

integration:
  performed: YES/NO
  locale_it_entries:
  locale_en_entries:
  assets_installed:
  ledger_updated:

focused_tests:
make_verify:
space_runtime_audio_spot_check:

final_sha:
final_git_status:
FIRST_FAILURE: NONE | <exact blocker>
```

Do not mark the overall Encyclopedia quality/interactivity pass COMPLETE from voice generation alone. Final completion still requires owner runtime visual/interaction acceptance.