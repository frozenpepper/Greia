# Greia Shared Character Utterances — Production & Review

**Status:** production runbook; original v0.2 shared library and 12-intro baseline were **OWNER_ACCEPTED** (2026-08-28) and live in `assets/audio/characters/shared/v0.2/`. v0.1 (2026-08-23) is **RETIRED** — see `assets/audio/characters/shared/v0.1/RETIRED.md`. Future regenerations of any cue land in the same v0.2 catalogue (incremental promotion), not in a new v0.3.

**Languages:** original accepted baseline Italian (`it`) and English (`en`); current released corpus also includes French (`fr`) and Spanish (`es`), with per-cue status

**Characters:** Lilli, Leo, Flash, Tito, Momo and Dani  
**Canonical engine:** `tools/greia_voice.py`

**Owner-scoped corpus replacement update (2026-10-21):** the prior v0.2
owner-accepted state above is historical for rows selected by the separate
three-character v3 corpus plan. Those Dani/Momo/Tito files now carry replacement
audio with `human_review=PENDING`; their old bytes and receipts are in the
external corpus-run backups. The authorized bulk operation used
`tools/regenerate_voice_corpus.py` and the dedicated corpus work order, not this
additive shared-library producer. Future incremental additions still use this
runbook and remain in the existing v0.2 catalogue after individual listening.

**2026-10-22 priority continuation:** selected short rows across all six actors
may now be replaced by `finish_voice_priority.py`. The directory remains v0.2;
current acceptance belongs to each receipt/manifest, not the baseline above.
See the corpus runbook and HANDOVER.

## 1. Canonical rule

Generate the shared reaction library with:

```text
tools/record_shared_character_utterances.py
```

The script is a thin semantic producer over `VoiceEngine`. It inherits the VoxStage/VoxCPM2 default from the common engine composition (2026-10-19); existing accepted library bytes are not replaced by this provider change. It must remain free of direct Chatterbox, Whisper, native-TTS, trimming and FFmpeg implementation logic.

Read first:

```text
AGENTS.md
SETUP.md
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
```

For installation/readiness:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

## 2. Historical accepted baseline and current exceptions

Do not infer content completion from the existence of the producer — confirm against the
catalogue, not the script.

Accepted baseline as of 2026-08-28, before the separately authorized 2026-10-21
corpus replacement:

```text
shared reaction candidates: 180 generated, 180 OWNER_ACCEPTED; published to assets/audio/characters/shared/v0.2/
character intro candidates:  12 generated,  12 OWNER_ACCEPTED; published to assets/audio/characters/shared/v0.2/_intros/
catalogue manifest:          assets/audio/characters/shared/v0.2/manifest.toml   (registry_version v0.2, total_clips 192)
catalogue review ledger:     assets/audio/characters/shared/v0.2/review.csv      (192 OWNER_ACCEPTED rows)
engine receipt ledger:       every receipt stamped human_review=OWNER_ACCEPTED + owner_decision_at_utc
runtime resolver wiring:     PENDING (separate child-runtime task; v0.2 is the source of truth)
v0.1 status:                 RETIRED 2026-08-28; see assets/audio/characters/shared/v0.1/RETIRED.md
```

The work becomes accepted only through generation + human listening + explicit promotion
of accepted static assets. Future incremental promotion of additional accepted clips
(e.g. a per-Activity requested Lilli line) follows the same procedure: produce via the
engine, listen, mark `OWNER_ACCEPTED`, append a new `[[utterance]]` to v0.2/manifest.toml
with its actual SHA-256. The v0.1 → v0.2 path was a wholesale supersession driven by
engine changes; future work is incremental within v0.2.

## 3. Engine routing

Every shared reaction line uses:

```text
kind = shared_character_utterance
```

Routing is automatic:

```text
All six characters -> selected v0.2 cloned-character provider
Default            -> shared local VoxStage/VoxCPM2
Explicit alternative -> retained Chatterbox provider
```

Suitable multi-word natural-character lines may receive advisory Whisper verification. Tiny reactions and Dani may legitimately skip ASR.

The engine owns:

```text
canonical identity/reference validation
model loading/reuse
single-worker protection
MLX cleanup
native voice profiles
optional Whisper checks
WAV/OGG packaging
receipts
```

## 4. Preflight

Record source identity:

```bash
git status --short
git rev-parse HEAD
python3 --version
```

Run:

```bash
python3 tools/greia_voice.py doctor
```

A cloning-reference hash failure is a hard stop. If a required provider is unavailable, follow the canonical setup guide; do not substitute a different backend directly.

Default review workspace:

```text
./tmp/shared-character-utterances/
```

Review/rejected audio is not runtime content.

## 5. Generate the 180 shared-reaction candidates

Full matrix:

```bash
python3 tools/record_shared_character_utterances.py
```

Useful subset while validating the workstation:

```bash
python3 tools/record_shared_character_utterances.py \
  --characters leo,dani
```

The producer keeps one engine/model warm, holds the global generation lock for the complete run and refuses to overwrite an existing audio/receipt pair blindly.

Expected layout:

```text
tmp/shared-character-utterances/
  lilli/it/*.wav
  lilli/en/*.wav
  leo/...
  flash/...
  tito/...
  momo/...
  dani/...
  review.csv
```

Each generated candidate also has:

```text
<audio>.receipt.json
```

All remain:

```text
human_review = PENDING
```

## 6. Shared phrase matrix

### `praise.general`

Italian:

```text
Complimenti!
Ottimo lavoro!
Ben fatto!
```

English:

```text
Congratulations!
Great work!
Well done!
```

### `celebrate.success`

Italian:

```text
Ce l'hai fatta!
Evviva!
Che meraviglia!
```

English:

```text
You did it!
Hooray!
Wonderful!
```

### `encourage.retry`

Italian:

```text
Riproviamo!
Quasi! Proviamo ancora!
Ancora una volta!
```

English:

```text
Let's try again!
Almost! Let's try again!
One more time!
```

### `encourage.progress`

Italian:

```text
Continua così!
Ci sei quasi!
Vai avanti!
```

English:

```text
Keep going!
Almost there!
You're doing great!
```

### `ready.go`

Italian:

```text
Forza, andiamo!
Ci siamo? Via!
Si parte!
```

English:

```text
Come on, let's go!
Ready? Go!
Here we go!
```

Preserve source wording/punctuation during a run. If owner listening leads to a wording change, update the design authority and regenerate that cue rather than silently changing bytes.

## 7. Expected shared count

```text
6 characters × 5 families × 3 variants × 2 locales = 180
```

One failed variant does not invalidate a family. A family with zero accepted variants remains unavailable.

## 8. Review the shared candidates

`review.csv` contains machine dispositions such as:

```text
REVIEW_REQUIRED
REVIEW_REQUIRED_ASR_WARNING
EXISTING_REVIEW_CANDIDATE
UNAVAILABLE
REJECTED
BLOCKED_PARTIAL_OUTPUT
```

These are not acceptance decisions.

Human review should record a separate disposition, for example:

```text
ACCEPT
REGENERATE
BAD_PRONUNCIATION
EXTRA_SPEECH
WRONG_WORDS
VOICE_DRIFT
CLIPPED
BAD_DELIVERY
OTHER
```

`ACCEPT` requires:

- exact words;
- correct locale/pronunciation;
- no invented/repeated speech;
- no clipped starts/ends or unwanted tails;
- recognizable canonical identity for natural characters;
- clearly fun/robotic Dani identity;
- delivery suitable for repeated child-facing use;
- acceptable playback on small speakers.

Whisper PASS never replaces listening.

## 9. Do not promote review output automatically

Generation success must **not** copy candidates directly into runtime assets.

After listening, the later integration tranche should:

1. take only `ACCEPT` candidates;
2. place them in the versioned OS/shared audio catalogue;
3. expose only accepted variants through the semantic resolver;
4. omit rejected/missing variants rather than using placeholders;
5. test fail-soft behavior for unavailable families/locales;
6. verify at least one real Activity consumes a semantic family without copying the bytes into its package.

Until that exists, report:

```text
SHARED-UTTERANCE-AUDIO-PENDING
```

not “shared library complete”.

## 10. Generate the 12 character introductions

The introduction pack is separate from shared generic reactions. It can be generated in the same workstation session after the shared run.

Create a review queue:

```bash
mkdir -p ./tmp/character-intros
cat > ./tmp/character-intro-requests.jsonl <<'EOF'
{"speaker":"lilli","kind":"character_dialogue","locale":"it","text":"Ciao! Io sono Lilli! Adoro inventare storie, disegnare cose colorate e trovare un po' di magia dappertutto. Hai un'idea buffa? Vieni con me!","cue_id":"character.intro.lilli","output":"tmp/character-intros/it/lilli.ogg","verification":"auto","max_attempts":2}
{"speaker":"lilli","kind":"character_dialogue","locale":"en","text":"Hi! I'm Lilli! I love making up stories, drawing colorful things, and finding a little magic everywhere. Got a silly idea? Come with me!","cue_id":"character.intro.lilli","output":"tmp/character-intros/en/lilli.ogg","verification":"auto","max_attempts":2}
{"speaker":"leo","kind":"character_dialogue","locale":"it","text":"Oh, ciao! Io sono Leo. Mi piacciono le storie, le parole e tutte quelle domande che cominciano con perché. Se c'è qualcosa da scoprire, io sono pronto!","cue_id":"character.intro.leo","output":"tmp/character-intros/it/leo.ogg","verification":"auto","max_attempts":2}
{"speaker":"leo","kind":"character_dialogue","locale":"en","text":"Oh, hello! I'm Leo. I like stories, words, and all those questions that start with why. If there's something to discover, I'm ready!","cue_id":"character.intro.leo","output":"tmp/character-intros/en/leo.ogg","verification":"auto","max_attempts":2}
{"speaker":"flash","kind":"character_dialogue","locale":"it","text":"Ehi! Io sono Flash! Adoro correre, giocare e provare sfide velocissime. Se senti qualcuno gridare via, probabilmente sono già partito!","cue_id":"character.intro.flash","output":"tmp/character-intros/it/flash.ogg","verification":"auto","max_attempts":2}
{"speaker":"flash","kind":"character_dialogue","locale":"en","text":"Hey! I'm Flash! I love running, playing, and trying super-fast challenges. If you hear someone shout go, I've probably already started!","cue_id":"character.intro.flash","output":"tmp/character-intros/en/flash.ogg","verification":"auto","max_attempts":2}
{"speaker":"dani","kind":"dani_system_speech","locale":"it","text":"Bip-bop! Io sono Dani! Mi piacciono numeri, schemi, puzzle e cose che fanno clic proprio al posto giusto. Modalità amicizia: attivata!","cue_id":"character.intro.dani","output":"tmp/character-intros/it/dani.ogg","verification":"off","max_attempts":1}
{"speaker":"dani","kind":"dani_system_speech","locale":"en","text":"Beep-bop! I'm Dani! I like numbers, patterns, puzzles, and things that click into exactly the right place. Friendship mode: activated!","cue_id":"character.intro.dani","output":"tmp/character-intros/en/dani.ogg","verification":"off","max_attempts":1}
{"speaker":"tito","kind":"character_dialogue","locale":"it","text":"Ciao, esploratore! Io sono Tito! Mi piace curiosare tra boschi, mari, sentieri e piccoli misteri. Andiamo a vedere cosa c'è dietro l'angolo!","cue_id":"character.intro.tito","output":"tmp/character-intros/it/tito.ogg","verification":"auto","max_attempts":2}
{"speaker":"tito","kind":"character_dialogue","locale":"en","text":"Hello, explorer! I'm Tito! I love poking around forests, seas, trails, and little mysteries. Let's see what's around the corner!","cue_id":"character.intro.tito","output":"tmp/character-intros/en/tito.ogg","verification":"auto","max_attempts":2}
{"speaker":"momo","kind":"character_dialogue","locale":"it","text":"Buuu! Scherzavo! Io sono Momo! Adoro musica, rumori buffi, esperimenti strani e feste improvvise. Se qualcosa fa boing, voglio provarla!","cue_id":"character.intro.momo","output":"tmp/character-intros/it/momo.ogg","verification":"auto","max_attempts":2}
{"speaker":"momo","kind":"character_dialogue","locale":"en","text":"Booo! Just kidding! I'm Momo! I love music, silly noises, strange experiments, and surprise parties. If something goes boing, I want to try it!","cue_id":"character.intro.momo","output":"tmp/character-intros/en/momo.ogg","verification":"auto","max_attempts":2}
EOF

python3 tools/greia_voice.py batch --input ./tmp/character-intro-requests.jsonl
```

The canonical text authority remains:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
```

If shell-safe queue wording differs only by removed quotation marks around `perché/why/via/go`, the intended spoken meaning must be checked during listening. Prefer the design-document wording when manually regenerating a line.

## 11. Review the introductions separately

Do not mix intro acceptance with generic shared-family acceptance.

For each intro verify:

- the character sounds immediately recognizable;
- the line is fun and short enough for optional OS use;
- personality matches the canonical cast;
- no line sounds like a mandatory tutorial;
- pronunciation is natural;
- the clip works when triggered alone;
- Dani remains charming/robotic rather than generic navigation TTS.

Possible future placement—first-run, tappable Home characters, gallery—is **not** decided by this audio run.

## 12. Evidence to return

Return:

```text
1. exact Greia source SHA
2. doctor result
3. shared review output directory
4. shared review.csv
5. shared generated/existing/blocked count per character + locale
6. representative receipts
7. human accepted/rejected shared count
8. missing/retry shared variants
9. character intro batch result
10. human accepted/rejected intro count
11. Dani voice assessment
12. any script wording recommended for revision after listening
```

Do not hide failures and do not commit model environments, caches, canonical references or rejected/unreviewed review audio.
