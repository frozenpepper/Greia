# Greia Shared Character Utterances

**Status:** accepted design; Voice Production Engine ready; **shared audio generation and owner listening are still pending**  
**Reviewed:** 2026-08-28  
**Scope:** small OS-owned multilingual character reactions shared across Activities  
**Production authority:** `tools/greia_voice.py` / `tools/record_shared_character_utterances.py`

Related:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_CANONICAL_CAST_SYSTEM.md
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
skills/greia-voice-production/SKILL.md
```

## 1. Decision

Greia will ship a small, bounded library of **canonical prerecorded character reactions** that can be reused across Activities.

Activities request meaning, not a sentence or filename:

```text
character = lilli
utterance = praise.general
locale = it
```

The child device never synthesizes these lines. Greia resolves only already-reviewed static audio.

The library exists to:

1. give recurring characters consistent personality across Activities;
2. avoid duplicating generic praise/retry audio into many packages;
3. give Activity authors useful spoken reactions without needing a voice model locally;
4. keep random wording variation presentation-only and bounded.

It is **not** a general dialogue system and it is **not** pronunciation authority.

## 2. Current v0.1 families

The semantic ID names the meaning. Every phrase inside one family must be interchangeable in every context where that family is requested.

| Family | Italian variants | English variants | Expression | Motion |
|---|---|---|---|---|
| `praise.general` | `Complimenti!` · `Ottimo lavoro!` · `Ben fatto!` | `Congratulations!` · `Great work!` · `Well done!` | `happy` | `happy_hop` |
| `celebrate.success` | `Ce l'hai fatta!` · `Evviva!` · `Che meraviglia!` | `You did it!` · `Hooray!` · `Wonderful!` | `happy` | `celebrate_pop` |
| `encourage.retry` | `Riproviamo!` · `Quasi! Proviamo ancora!` · `Ancora una volta!` | `Let's try again!` · `Almost! Let's try again!` · `One more time!` | `happy` | `idle_bounce` |
| `encourage.progress` | `Continua così!` · `Ci sei quasi!` · `Vai avanti!` | `Keep going!` · `Almost there!` · `You're doing great!` | `happy` | `idle_bounce` |
| `ready.go` | `Forza, andiamo!` · `Ci siamo? Via!` · `Si parte!` | `Come on, let's go!` · `Ready? Go!` · `Here we go!` | `happy` | `happy_hop` |

The Italian phrases deliberately avoid child-gender agreement such as `bravo/brava`.

## 3. Production target — still pending

The v0.1 target is:

```text
6 characters
× 5 semantic families
× 3 variants
× 2 locales (it, en)
= 180 review candidates
```

Characters:

```text
lilli
leo
flash
dani
tito
momo
```

**Do not describe this library as generated, accepted, packaged or runtime-complete until the recording/review evidence exists.**

Current authoritative state:

```text
Voice Engine / producer: IMPLEMENTED
phrase matrix:          DEFINED
generation:             COMPLETE (192 candidates: 180 shared + 12 intros)
owner listening:        COMPLETE (in-session 2026-08-28)
accepted asset set:     assets/audio/characters/shared/v0.2/   (registry_version v0.2, 192 clips, OWNER_ACCEPTED)
retired predecessor:    assets/audio/characters/shared/v0.1/   (RETIRED.md; preserved as historical evidence)
runtime completeness:   PENDING (assets accepted; runtime resolver wiring to v0.2/ is a separate child-runtime task)
```

A future partial accepted library is valid: one or two accepted variants may survive for a family. Zero accepted variants means that family is unavailable and must fail soft.

## 4. Canonical production route

All 180 candidates are produced through the Greia Voice Production Engine using:

```text
kind = shared_character_utterance
```

Automatic routing:

```text
Lilli/Leo/Flash/Tito/Momo -> canonical cloned-character provider
Dani                       -> deterministic native/system Dani provider
```

No shared-library script may own Chatterbox, MLX, Whisper, native TTS, trimming, token budgets or FFmpeg packaging directly.

Dani remains intentionally robotic/system-generated and uses `greia.dani.system-v1`.

Production/runbook authority:

```text
tools/record_shared_character_utterances.py
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
```

## 5. Runtime contract

Once accepted audio is integrated, each character + locale + family resolves to a non-empty reviewed array:

```text
shared_utterances[character][locale][family] = [
    reviewed_file_01,
    reviewed_file_02,
    reviewed_file_03,
]
```

Selection semantics:

```python
variants = resolved_family.variants
selected = variants[0] if len(variants) == 1 else rng.choice(variants)
```

Rules:

- one accepted recording is valid;
- multiple accepted recordings add variety;
- rejected/missing recordings are absent, never silent placeholders;
- Activities never request a variant number, filename or array index;
- randomness is presentation-only;
- adding/removing a reviewed variant requires no Activity gameplay change;
- visual feedback remains sufficient if the family is unavailable;
- no speech variant may change correctness, score, reward, difficulty or progression.

Do not add shuffle histories, adaptive reinforcement or weighting until there is evidence they are useful.

## 6. Scheduling and animation

The utterance and its expression/motion are one presentation event. Do not pair cheerful praise with a conflicting expression.

Use only established semantic states/motions, for example:

```text
neutral
happy
surprised
idle_bounce
happy_hop
celebrate_pop
surprised_wobble
```

Speech must not interrupt:

- a pronunciation target;
- a timed answer;
- a drawing/recording gesture;
- another spoken instruction;
- another character clip.

Do not speak after every trivial interaction. Use bounded cooldown/repetition suppression where needed.

## 7. Pedagogical speech remains separate

Shared reactions communicate emotion and feedback. They do not teach a sound.

> If the sound itself is the educational truth, use `pedagogical_speech`, not a shared character reaction.

Letters, syllables, phonemes, spelling units and pronunciation exercises remain deterministic pedagogical audio even when a mascot is visually present.

## 8. Character introductions are a different asset family

Greia also plans a small **OS-owned character introduction pack**: one fun self-introduction per character per locale for possible first-run/Home/character-gallery use.

Those introductions are **not** a sixth shared-reaction family. They are character-specific content and therefore use:

```text
Lilli/Leo/Flash/Tito/Momo -> kind = character_dialogue
Dani                       -> kind = dani_system_speech
```

Stable cue IDs:

```text
character.intro.lilli
character.intro.leo
character.intro.flash
character.intro.dani
character.intro.tito
character.intro.momo
```

Their final product placement is intentionally undecided. Candidate UX includes:

- an optional first-run “meet the characters” moment;
- characters wandering/appearing on Home and speaking when tapped/clicked;
- a future character gallery/profile page;
- occasional non-blocking discovery moments.

Do **not** auto-play all six introductions in sequence at boot. At most one voice should play at a time, introductions must be interruptible/skippable, and core navigation must never depend on hearing them.

The exact v0.1 scripts live in `docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md` and the production commands live in `docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md`.

## 9. Acceptance gate

Every candidate produced by the Voice Engine remains:

```text
human_review = PENDING
```

Human listening must verify:

- exact locale and words;
- recognizable canonical identity for Lilli/Leo/Flash/Tito/Momo;
- clearly synthetic/fun robotic Dani identity;
- no invented/repeated sounds;
- no clipping or unwanted tails;
- acceptable pronunciation/stress;
- lively but not exhausting delivery;
- acceptable playback on small laptop speakers.

Whisper is only an advisory warning/regeneration aid for suitable natural-character lines. It never accepts audio, and tiny reactions/Dani may legitimately be `NOT_APPLICABLE`.

Accepted bytes must be versioned. Do not silently replace reviewed audio in place.

## 10. Completion definition

The shared-utterance work is complete only when all of the following are true:

```text
Voice Engine readiness verified on the production workstation
180 intended candidates attempted
human listening recorded
accepted/rejected set explicit
accepted assets promoted into the shared runtime catalogue
runtime resolver exposes only accepted variants
missing-family fail-soft behavior tested
Activities can request semantic families without package duplication
```

The character-introduction pack has a separate completion line:

```text
12 intended intro candidates attempted (6 × 2 locales)
human listening recorded
accepted intro assets versioned
runtime placement deliberately chosen and separately tested
```
