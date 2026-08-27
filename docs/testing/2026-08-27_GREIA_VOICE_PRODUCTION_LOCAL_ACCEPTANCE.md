# Greia Voice Production Engine — Local Provider Acceptance Protocol

**Reviewed:** 2026-08-28  
**Audience:** owner-controlled local coding/test agent  
**Purpose:** verify the canonical Voice Production Engine against the real workstation providers and audio outputs. The engine is already the repository-wide authoring interface; this protocol establishes machine/provider evidence, not permission to bypass the engine.

## 0. Non-negotiable boundaries

Do not:

- create a branch; work on current `main` unless the owner explicitly says otherwise;
- use GitHub-hosted Actions;
- expose the voice service on `0.0.0.0` or a LAN address;
- run two Chatterbox inference workers concurrently;
- regenerate/overwrite owner-accepted Activity audio merely to test the engine;
- edit canonical reference recordings or hashes;
- write or accept silent placeholder audio;
- mark any clip human-accepted because Whisper passed;
- bypass `tools/greia_voice.py` with direct Chatterbox/native-TTS commands to make a test pass;
- install/download missing heavy dependencies or model weights unless the owner authorizes voice setup.

Preserve unrelated work. Stop immediately on canonical-reference hash or source-integrity failures.

## 1. Read first

```text
AGENTS.md
SETUP.md
HANDOVER.md
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

Only if provider troubleshooting is required, additionally read:

```text
docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md
```

Record:

```bash
git status --short
git rev-parse HEAD
python3 --version
```

If unrelated uncommitted work exists, preserve it. Do not reset/clean it.

## 2. Provider-free source gate

Run exactly:

```bash
python3 -m unittest tests.test_greia_voice_tool -v
```

Expected: all tests PASS, including semantic routing, shared-library routing, Dani separation, pedagogical safeguards, advisory ASR behavior, receipts and worker locking.

Then run:

```bash
make verify
```

Expected: full repository verification PASS.

**STOP on the first failure.** Fix the implementation cleanly; do not skip tests or weaken assertions.

## 3. Machine-local evidence area

On macOS:

```bash
export GREIA_VOICE_HOME="${GREIA_VOICE_HOME:-${HOME}/Library/Application Support/Greia/voice-production}"
export VOICE_ACCEPTANCE_DIR="${GREIA_VOICE_HOME}/acceptance/voice-engine"
mkdir -p "${VOICE_ACCEPTANCE_DIR}"
```

Model weights, venvs, caches and rejected scratch audio stay outside Git.

## 4. Doctor gate

Run:

```bash
python3 tools/greia_voice.py doctor | tee "${VOICE_ACCEPTANCE_DIR}/doctor.json"
```

For a full Apple-Silicon acceptance run, require:

```text
canonical Lilli/Leo/Flash/Tito/Momo anchors present + hash-valid
ffmpeg available
chatterbox-mlx-multilingual-v3 available
macos-native-say available
mlx-whisper-tiny available for the optional ASR lane
```

If the environment is absent and installation is authorized, install only from:

```text
tools/greia_voice_core/README.md
tools/greia_voice_requirements_mlx.txt
```

Then rerun `doctor`. Never modify canonical hashes to obtain PASS.

## 5. Deterministic pedagogical speech gate

Generate three deliberately pronunciation-sensitive samples:

```bash
python3 tools/greia_voice.py generate \
  --speaker pedagogical \
  --kind pedagogical_speech \
  --locale it \
  --text "ma" \
  --cue-id acceptance.phonics.ma \
  --verification off \
  --output "${VOICE_ACCEPTANCE_DIR}/phonics-ma.wav"

python3 tools/greia_voice.py generate \
  --speaker pedagogical \
  --kind pedagogical_speech \
  --locale it \
  --text "to" \
  --cue-id acceptance.phonics.to \
  --verification off \
  --output "${VOICE_ACCEPTANCE_DIR}/phonics-to.wav"

python3 tools/greia_voice.py generate \
  --speaker pedagogical \
  --kind pedagogical_speech \
  --locale it \
  --text "b" \
  --cue-id acceptance.letter.b \
  --verification off \
  --output "${VOICE_ACCEPTANCE_DIR}/letter-b.wav"
```

Verify:

- each file exists and is audible;
- receipts say `human_review=PENDING`;
- the receipt request text remains the exact semantic target (`to`, not the provider's accent workaround);
- a fluent Italian listener approves the actual educational pronunciation.

A wrong/ambiguous phoneme is FAIL even if the synthesis sounds pleasant.

## 6. Character + Whisper gate

Generate one normal multi-word Leo line:

```bash
python3 tools/greia_voice.py generate \
  --speaker leo \
  --kind character_dialogue \
  --locale it \
  --text "Guardiamo con calma cosa succede." \
  --cue-id acceptance.leo.normal \
  --output "${VOICE_ACCEPTANCE_DIR}/leo-normal.ogg"
```

Inspect its receipt. Verify:

```text
provider = canonical Chatterbox/MLX provider
voice_id = greia.leo.v1
reference hash matches registry
verification is recorded
human_review = PENDING
```

Listen and require:

- exact Italian words;
- recognizable warm older/savvy Leo identity;
- no invented/repeated speech;
- no clipped onset/end or generated tail;
- suitable intelligibility.

Whisper PASS does not replace listening. If Whisper warns but the audio is actually correct, record that as verifier false-negative evidence rather than rewriting acceptance rules.

## 7. Short-character gate

Generate:

```bash
python3 tools/greia_voice.py generate \
  --speaker flash \
  --kind character_dialogue \
  --locale it \
  --text "Vai!" \
  --cue-id acceptance.flash.short \
  --output "${VOICE_ACCEPTANCE_DIR}/flash-vai.ogg"
```

Verify that tiny speech is not falsely treated as ASR authority and listen for clean primary-utterance trimming/no tail.

## 8. Dani gate

Generate:

```bash
python3 tools/greia_voice.py generate \
  --speaker dani \
  --kind dani_system_speech \
  --locale it \
  --text "Schema completato!" \
  --cue-id acceptance.dani \
  --output "${VOICE_ACCEPTANCE_DIR}/dani.ogg"
```

Require:

- system/native provider, never cloned-character provider;
- ASR `NOT_APPLICABLE`/not used;
- human review of intelligibility and sufficiently synthetic/robotic Dani identity.

If current host voice is not robotic enough, tune the engine-owned Dani profile/override and document it. Do not create a separate Dani generator.

## 9. Shared-library routing gate

Test a tiny subset through the central producer:

```bash
python3 tools/record_shared_character_utterances.py \
  --characters leo,dani \
  --output-root "${VOICE_ACCEPTANCE_DIR}/shared"
```

Verify:

- Leo routes through cloned provider;
- Dani routes through system/native provider;
- no direct TTS implementation exists in the producer;
- `review.csv` is written;
- each new candidate has a receipt;
- candidates remain review-required, not accepted.

Do not run the full 180-clip library merely for this smoke gate unless the owner requests it.

## 10. Warm-service/model-reuse gate

Start:

```bash
python3 tools/greia_voice.py serve > "${VOICE_ACCEPTANCE_DIR}/service.log" 2>&1 &
VOICE_SERVICE_PID=$!
```

Submit at least three character requests using `request` to distinct files. Inspect receipts and require:

```text
first Chatterbox load count = 1
subsequent requests          = model_load_count remains 1
```

While the service is live, attempt a separate one-shot character generation. It must fail fast on the cross-process generation lock instead of loading a second model.

Stop cleanly:

```bash
python3 tools/greia_voice.py shutdown
wait "${VOICE_SERVICE_PID}"
```

Confirm no stale Greia voice/Chatterbox process remains.

## 11. Batch gate

Create a small JSONL file with at least two cloned-character requests and run:

```bash
python3 tools/greia_voice.py batch --input "${VOICE_ACCEPTANCE_DIR}/batch.jsonl" \
  | tee "${VOICE_ACCEPTANCE_DIR}/batch-result.json"
```

Require model reuse and valid receipts. Do not use parallel workers.

## 12. Final evidence/report

Return:

```text
exact git SHA
focused test result
make verify result
doctor JSON
Python + host architecture
voice requirements versions actually installed
character/native/Whisper provider status
paths to generated acceptance clips + receipts
human listening result per clip
warm-service model_load_count evidence
second-worker rejection evidence
shared-library routing smoke result
batch reuse result
all remaining failures/limitations
```

If all gates pass, update `HANDOVER.md` with the exact provider/audio evidence. Do not claim Windows/Linux provider support or physical Acer evidence from this workstation test.

## 13. What this protocol does not authorize

A PASS does not authorize:

- child-runtime TTS or Whisper;
- shipping model weights/caches/venvs;
- cloud upload of canonical reference voices;
- replacing human listening with ASR;
- exposing the warm service beyond localhost;
- regenerating existing accepted audio without a content reason.
