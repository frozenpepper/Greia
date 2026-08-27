# Greia Voice Production Engine — Local Finalization & Acceptance Protocol

**Date:** 2026-08-27  
**Audience:** local owner-controlled coding/test agent  
**Purpose:** finish integration of the new authoring-time voice engine on the real production workstation, exercise actual Chatterbox/native/Whisper providers, and only then switch Greia authoring guidance away from legacy one-off generator mechanics.

## 0. Non-negotiable boundaries

Do not:

- create a branch; work on current `main` unless the owner explicitly says otherwise;
- use GitHub-hosted Actions;
- expose the voice service on `0.0.0.0` or a LAN address;
- run two Chatterbox inference workers concurrently;
- regenerate or overwrite already owner-accepted Activity audio merely to test the engine;
- edit canonical reference recordings or hashes;
- write silent placeholder audio on failure;
- mark any generated clip human-accepted because Whisper passed;
- change the semantic routing policy to make a test convenient;
- install/download a missing heavy toolchain unless the owner has explicitly authorized voice setup.

Preserve unrelated current work. Stop on source-integrity or canonical-reference hash failures.

## 1. Read first

From the current Greia checkout:

```text
AGENTS.md
SETUP.md
HANDOVER.md
skills/greia-os-work/SKILL.md
skills/greia-activity-authoring/SKILL.md
skills/greia-voice-production/SKILL.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md
```

Record:

```bash
git status --short
git rev-parse HEAD
python3 --version
```

If the checkout has unrelated uncommitted work, preserve it. Do not reset/clean it away.

## 2. Provider-free source gate

Run exactly:

```bash
python3 -m unittest tests.test_greia_voice_tool -v
```

Expected: all Greia voice-tool tests PASS.

Then run:

```bash
make verify
```

Expected: full repository verification PASS.

**STOP** if either command fails. Fix the implementation cleanly; do not skip tests or weaken assertions.

## 3. Create machine-local evidence area

Use the existing Greia voice-production home if configured:

```bash
export GREIA_VOICE_HOME="${GREIA_VOICE_HOME:-${HOME}/Library/Application Support/Greia/voice-production}"
export VOICE_ACCEPTANCE_DIR="${GREIA_VOICE_HOME}/acceptance/2026-08-27-engine"
mkdir -p "${VOICE_ACCEPTANCE_DIR}"
```

Do not put model weights/venvs/caches in the repository.

## 4. Non-mutating doctor gate

Run:

```bash
python3 tools/greia_voice.py doctor | tee "${VOICE_ACCEPTANCE_DIR}/doctor.json"
```

Required observations for full Apple-Silicon character-voice acceptance:

```text
canonical anchor hashes: OK for lilli/leo/flash/tito/momo
ffmpeg.available: true
chatterbox-mlx-multilingual-v3.available: true
macos-native-say.available: true
mlx-whisper-tiny.available: true  # optional for generation, required for the ASR acceptance subsection below
```

If canonical anchor hash validation fails: **STOP**. Do not repair the manifest/reference ad hoc.

If Chatterbox is unavailable but the existing voice environment is expected to exist, diagnose against `GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md`; do not create another venv in the repo.

If Whisper alone is unavailable, character generation may still be tested but classify ASR acceptance as `NOT_RUN / BLOCKED`; do not claim the complete engine acceptance gate.

## 5. Pedagogical/system TTS pilot

Generate three Italian pedagogical clips without touching Activity assets:

```bash
python3 tools/greia_voice.py generate \
  --speaker pedagogical \
  --kind pedagogical_speech \
  --locale it \
  --text "ma" \
  --cue-id acceptance.phonics.ma \
  --verification off \
  --output "${VOICE_ACCEPTANCE_DIR}/pedagogical-ma.wav" \
  | tee "${VOICE_ACCEPTANCE_DIR}/pedagogical-ma.result.json"

python3 tools/greia_voice.py generate \
  --speaker pedagogical \
  --kind pedagogical_speech \
  --locale it \
  --text "to" \
  --cue-id acceptance.phonics.to \
  --verification off \
  --output "${VOICE_ACCEPTANCE_DIR}/pedagogical-to.wav" \
  | tee "${VOICE_ACCEPTANCE_DIR}/pedagogical-to.result.json"

python3 tools/greia_voice.py generate \
  --speaker pedagogical \
  --kind pedagogical_speech \
  --locale it \
  --text "B" \
  --cue-id acceptance.letter.b \
  --verification off \
  --output "${VOICE_ACCEPTANCE_DIR}/pedagogical-b.wav" \
  | tee "${VOICE_ACCEPTANCE_DIR}/pedagogical-b.result.json"
```

Verify:

- each result disposition is `REVIEW_REQUIRED`, not accepted;
- each output and `.receipt.json` exists;
- output is mono 22,050 Hz;
- the receipt request retains exact target text (`to`), while native generation parameters may show provider-only synthesis text (`tò`);
- lowercase handling prevents the host voice from saying “maiuscola/capital” for the letter target.

**Human listening required:** listen to all three. `ma`, `to` and the letter name must be educationally correct and unambiguous. If not, tune only the native provider profile/override layer, add a provider-free regression test, and rerun this section.

## 6. Character-dialogue + Whisper pilot

Use a normal multi-word Leo sentence so ASR is eligible:

```bash
python3 tools/greia_voice.py generate \
  --speaker leo \
  --kind character_dialogue \
  --locale it \
  --text "Guardiamo con calma questa piccola meraviglia." \
  --cue-id acceptance.leo.dialogue \
  --verification auto \
  --max-attempts 2 \
  --output "${VOICE_ACCEPTANCE_DIR}/leo-dialogue.ogg" \
  | tee "${VOICE_ACCEPTANCE_DIR}/leo-dialogue.result.json"
```

Required machine behavior:

- canonical Leo reference hash is validated before generation;
- output is not a stub/silence;
- receipt records `greia.leo.v1` and the canonical reference SHA-256;
- receipt records `model_load_count = 1`;
- Whisper uses Italian explicitly;
- normal result is `REVIEW_REQUIRED`; `REVIEW_REQUIRED_ASR_WARNING` is allowed only if the produced audio is then inspected manually and the warning is understood;
- no result ever says human accepted.

**Human listening required:** confirm exact words, Italian pronunciation, Leo's oldish/savvy canonical identity, no invented/repeated tail, no clipping/click, suitable delivery.

If Chatterbox says the wrong words internally, reject/regenerate; do not waveform-splice the phrase into correctness.

## 7. Ultra-short character reaction pilot

Exercise the short-dialogue trim path separately:

```bash
python3 tools/greia_voice.py generate \
  --speaker flash \
  --kind character_dialogue \
  --locale it \
  --text "Vai!" \
  --cue-id acceptance.flash.short \
  --verification auto \
  --max-attempts 2 \
  --output "${VOICE_ACCEPTANCE_DIR}/flash-vai.wav" \
  | tee "${VOICE_ACCEPTANCE_DIR}/flash-vai.result.json"
```

Expected:

- Whisper reports `NOT_APPLICABLE` because the one-word reaction is intentionally below the reliable ASR gate;
- short-dialogue token/trim policy is used;
- no extra Chatterbox tail survives obvious review;
- human listening remains the only semantic/identity acceptance gate.

## 8. Warm-service / one-model lifecycle gate

Start the localhost service:

```bash
python3 tools/greia_voice.py serve \
  > "${VOICE_ACCEPTANCE_DIR}/service.log" 2>&1 &
VOICE_SERVICE_PID=$!
```

Wait until the log contains a `READY` JSON line. If the process exits, inspect the log and stop.

Send three Leo requests through the same service:

```bash
python3 tools/greia_voice.py request --speaker leo --kind character_dialogue --locale it \
  --text "Prima osserviamo." --cue-id acceptance.service.1 \
  --output "${VOICE_ACCEPTANCE_DIR}/service-1.wav" \
  > "${VOICE_ACCEPTANCE_DIR}/service-1.result.json"

python3 tools/greia_voice.py request --speaker leo --kind character_dialogue --locale it \
  --text "Poi proviamo insieme." --cue-id acceptance.service.2 \
  --output "${VOICE_ACCEPTANCE_DIR}/service-2.wav" \
  > "${VOICE_ACCEPTANCE_DIR}/service-2.result.json"

python3 tools/greia_voice.py request --speaker leo --kind character_dialogue --locale it \
  --text "Infine guardiamo il risultato." --cue-id acceptance.service.3 \
  --output "${VOICE_ACCEPTANCE_DIR}/service-3.wav" \
  > "${VOICE_ACCEPTANCE_DIR}/service-3.result.json"
```

Inspect the three receipts. **All must report `model_load_count = 1`.** This proves the daemon keeps the Chatterbox model instance warm instead of reloading per clip.

Stop cleanly:

```bash
python3 tools/greia_voice.py shutdown | tee "${VOICE_ACCEPTANCE_DIR}/shutdown.json"
wait "${VOICE_SERVICE_PID}"
```

Confirm no stale `greia_voice.py serve` process remains.

## 9. Cross-process single-worker gate

The provider-free unit test already proves the lock primitive. Perform one real smoke check only if easy to overlap safely:

1. start one long character request;
2. while it is actively generating, launch a second one-shot character request;
3. the second request must fail fast with a message that another Greia voice worker is active;
4. it must **not** start another model instance.

Do not repeat this test if timing makes it unreliable. The deterministic unit test is the primary gate; this is supplemental workstation evidence.

## 10. Batch gate

Create:

```bash
cat > "${VOICE_ACCEPTANCE_DIR}/batch.jsonl" <<'EOF'
{"speaker":"tito","kind":"character_dialogue","locale":"it","text":"Osserviamo questo dettaglio.","cue_id":"acceptance.batch.1"}
{"speaker":"tito","kind":"character_dialogue","locale":"it","text":"Adesso scopriamo qualcosa di nuovo.","cue_id":"acceptance.batch.2"}
EOF
```

Run:

```bash
python3 tools/greia_voice.py batch --input "${VOICE_ACCEPTANCE_DIR}/batch.jsonl" \
  | tee "${VOICE_ACCEPTANCE_DIR}/batch.result.json"
```

Confirm both outputs exist in the machine-local default review tree and both receipts report `model_load_count = 1` for that batch engine lifecycle.

## 11. Dani gate — provisional profile review

Generate one Dani line:

```bash
python3 tools/greia_voice.py generate \
  --speaker dani \
  --kind dani_system_speech \
  --locale it \
  --text "Schema completato!" \
  --cue-id acceptance.dani \
  --verification off \
  --output "${VOICE_ACCEPTANCE_DIR}/dani.wav" \
  | tee "${VOICE_ACCEPTANCE_DIR}/dani.result.json"
```

Listen. The important architecture gate is that Dani never routes through Chatterbox. The **voice identity itself is still provisional**. If the current host voice is not robotic/fun enough, set/tune `GREIA_VOICE_DANI_VOICE_IT`/`EN` or adjust the native Dani profile centrally. Do not add Dani-specific voice commands to Activities.

Record whether Dani identity is:

```text
ACCEPTED_FOR_NOW
or
PROVISIONAL_NEEDS_PROFILE_TUNING
```

Do not block the rest of the engine acceptance solely because Dani profile taste needs tuning, provided routing is correct and this limitation is documented honestly.

## 12. Final source integration after provider gates are green

Only after Sections 2–10 are green:

1. update `skills/greia-activity-authoring/VOICE_GENERATION.md` so actual production says **use `tools/greia_voice.py` / `skills/greia-voice-production/SKILL.md`** instead of teaching agents to invoke providers directly;
2. update `skills/greia-activity-authoring/SKILL.md` voice section to route actual generation to the new voice skill/tool;
3. update `skills/greia-os-work/SKILL.md` voice-production section the same way;
4. update `SETUP.md` readiness ledger: unified provider probe and authoring engine are now implemented; native adapters beyond macOS remain pending;
5. keep `GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md` as **engine-maintainer/troubleshooting** documentation, not ordinary Activity-author instructions;
6. update `HANDOVER.md` with exact provider evidence, Dani disposition, test counts and any remaining migration work;
7. append an accurate non-blocking implementation entry to `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` without claiming R7 completion;
8. update `docs/DOCUMENTATION.md` only if documentation ownership changed materially;
9. commit directly to current `main`, preserving any concurrent owner work.

## 13. Legacy generator migration — do not mass-regenerate audio

After the engine is accepted, migrate **code**, not already-reviewed sound assets.

First pilots:

```text
tools/generate_sillabe_audio.py
tools/generate_stelle_incantate_audio.py (or another currently-used Chatterbox generator)
```

Goal:

- retain each script only as a thin semantic batch definition/compatibility entry point if still useful;
- call `greia_voice_core` / `tools/greia_voice.py` for actual production;
- delete duplicated Chatterbox model-load/cache/trim/hash/Whisper mechanics from the legacy script;
- delete duplicated macOS `say`/phonetic-override mechanics from Sillabe and use the native provider;
- do **not** regenerate accepted Activity assets just because the generator changed;
- add focused regression tests for any behavior moved out of the script.

Once two opposite pilots are clean, migrate other `generate_*_audio.py` scripts opportunistically rather than in one risky mass rewrite.

## 14. Evidence to return to the owner

Return a concise report containing:

```text
source SHA tested
provider-free test result/count
full make verify result/count
doctor status summary
pedagogical ma/to/B listening disposition
Leo dialogue listening disposition + Whisper result
Flash short-reaction listening disposition
warm-service model_load_count evidence
batch model_load_count evidence
Dani routing + profile disposition
paths to machine-local acceptance outputs/receipts/logs
files changed during final integration
remaining blockers/limitations
```

Do not create a ZIP unless the owner explicitly requests one. Keep evidence in the named machine-local acceptance directory and source changes in the repository.
