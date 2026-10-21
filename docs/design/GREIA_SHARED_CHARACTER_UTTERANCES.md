# Greia Shared Character Utterances

**Status:** accepted design + historical owner-accepted v0.2 baseline; rows replaced by the 2026-10-21 v3 corpus and subsequent all-actor priority retakes are listening-pending; runtime resolver integration remains separate
**Reviewed:** 2026-09-02  
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

Greia has a small bounded library of canonical prerecorded character reactions intended for reuse across Activities.

Activities request meaning, not a sentence or filename:

```text
character = lilli
utterance = praise.general
locale = it
```

The child device never synthesizes these lines. Runtime may resolve only versioned, human-accepted static audio.

The library exists to:

1. give recurring characters consistent personality across Activities;
2. avoid duplicating generic praise/retry recordings in many packages;
3. let Activity authors request useful spoken reactions without owning a voice model;
4. keep wording variation presentation-only and bounded.

It is **not** a dialogue generator and it is **not** pronunciation authority.

## 2. Semantic families

Every phrase inside one family must be interchangeable wherever that semantic family is requested.

| Family | Italian variants | English variants | Expression | Motion |
|---|---|---|---|---|
| `praise.general` | `Complimenti!` · `Ottimo lavoro!` · `Ben fatto!` | `Congratulations!` · `Great work!` · `Well done!` | `happy` | `happy_hop` |
| `celebrate.success` | `Ce l'hai fatta!` · `Evviva!` · `Che meraviglia!` | `You did it!` · `Hooray!` · `Wonderful!` | `happy` | `celebrate_pop` |
| `encourage.retry` | `Riproviamo!` · `Quasi! Proviamo ancora!` · `Ancora una volta!` | `Let's try again!` · `Almost! Let's try again!` · `One more time!` | `happy` | `idle_bounce` |
| `encourage.progress` | `Continua così!` · `Ci sei quasi!` · `Vai avanti!` | `Keep going!` · `Almost there!` · `You're doing great!` | `happy` | `idle_bounce` |
| `ready.go` | `Forza, andiamo!` · `Ci siamo? Via!` · `Si parte!` | `Come on, let's go!` · `Ready? Go!` · `Here we go!` | `happy` | `happy_hop` |

Italian reaction copy deliberately avoids child-gender agreement such as `bravo/brava`.

## 3. Current production state

### 2026-10-21 scoped v3 replacement status

The 180 shared reactions and 12 introductions listed below describe the
previously owner-accepted v0.2 baseline, not the current human-review state for
all paths. Under a separate owner-authorized 1,340-cue runtime corpus plan,
selected Dani/Momo/Tito shared-utterance and introduction files were regenerated
in their existing versioned paths. These replacement receipts and review rows
are `PENDING`; the prior bytes/receipts and frozen v2 plan history remain
recoverable/unchanged in the external v3 run evidence. Lilli/Leo/Flash shared
rows were preserved. The base design remains unchanged: runtime consumption
must expose only audio that has individually reached the accepted state, and
automated review does not confer that state.

The intended shared reaction matrix is:

```text
6 characters
× 5 semantic families
× 3 variants
× 2 locales (it, en)
= 180 shared clips
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

Historical pre-v3 baseline state (2026-08-28):

```text
Voice Engine / producer: IMPLEMENTED
phrase matrix:          DEFINED
shared generation:      COMPLETE (180)
intro generation:       COMPLETE (12)
owner listening:        COMPLETE (192 total, 2026-08-28)
accepted asset set:     assets/audio/characters/shared/v0.2/
registry version:       v0.2
accepted state:         OWNER_ACCEPTED
retired predecessor:    assets/audio/characters/shared/v0.1/
runtime resolver:       SEPARATE / PENDING where not yet wired to v0.2
```

The pre-v3 accepted baseline contained **192 reviewed EN/IT clips: 180 shared reactions + 12 character introductions**. The 2026-10-21 status correction above identifies which of those paths now contain pending v3 takes.

Do not infer review state from the v0.2 path/version name: consult the current manifest and review ledger. Accepted asset bytes do not by themselves prove that every child runtime/API consumer already resolves the library.

The older `v0.1` set is historical/retired and must not silently become the runtime source of truth again.

## 4. Canonical production route

Shared reactions are produced through VoiceEngine with:

```text
kind = shared_character_utterance
```

Provider routing remains an engine implementation detail:

```text
All six characters -> active selected master in the canonical registry
                    -> v0.3 for Dani/Momo/Tito; v0.2 for Lilli/Leo/Flash
Default            -> shared local VoxStage/VoxCPM2
Explicit alternative -> retained Chatterbox provider
```

No shared-library producer may own VoxStage, Chatterbox, MLX, Whisper, native TTS, silence trimming, token budgets or FFmpeg packaging directly.

The accepted historical shared v0.2 Dani recordings used `greia.dani.system-v1`. Dani production now uses selected cloned master `greia.dani.v3`; Momo and Tito likewise use their selected v3 masters. VoxStage/VoxCPM2 remains the default, and `dani_system_speech` remains a compatible kind. The 2026-10-21 scoped corpus operation updated only its frozen rows; all fresh rows remain pending until human listening.

Production/runbook authority:

```text
tools/record_shared_character_utterances.py
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
```

## 5. Runtime contract

When the runtime resolver consumes the accepted catalogue, each available character + locale + semantic family resolves to a non-empty reviewed variant set:

```text
shared_utterances[character][locale][family] = [
    reviewed_file_01,
    reviewed_file_02,
    reviewed_file_03,
]
```

Selection semantics remain simple:

```python
variants = resolved_family.variants
selected = variants[0] if len(variants) == 1 else rng.choice(variants)
```

Rules:

- one accepted variant is valid;
- multiple accepted variants add presentation variety;
- rejected/missing candidates are absent, never silent placeholders;
- Activities request semantic family, never variant number/filename/index;
- selection randomness is presentation-only;
- changing the accepted variant set requires no gameplay rewrite;
- unavailable family fails soft to visual/non-spoken feedback;
- spoken variant may not change correctness, score, reward, difficulty or progression.

Do not add shuffle histories, adaptive reinforcement or weighting without evidence that they solve a real problem.

## 6. Scheduling and animation

Speech and character expression/motion form one presentation event. Do not pair a cheerful line with conflicting character state.

Established examples include:

```text
neutral
happy
surprised
idle_bounce
happy_hop
celebrate_pop
surprised_wobble
```

Shared reactions must not interrupt:

- a pronunciation target;
- a timed answer;
- a drawing/recording gesture;
- another spoken instruction;
- another character clip.

Do not speak after every trivial interaction. Use bounded cooldown/repetition suppression where a consumer needs it.

## 7. Pedagogical speech remains separate

Shared reactions communicate emotion and feedback. They do not teach a sound.

> If the sound itself is the educational truth, use `pedagogical_speech`, not a shared character reaction.

Letters, syllables, phonemes, spelling units and pronunciation exercises remain deterministic pedagogical audio even when a mascot is visually present.

## 8. Character introductions

The accepted v0.2 asset set also contains one Italian and one English self-introduction for each canonical character:

```text
6 characters × 2 locales = 12 accepted intro clips
assets/audio/characters/shared/v0.2/_intros/
```

Introductions are **not** a sixth shared-reaction family. They are character-specific content and were produced as:

```text
Lilli/Leo/Flash/Tito/Momo -> character_dialogue
Dani                       -> dani_system_speech
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

**Placement (2026-10-16): the tappable Home greeter.** The child's cast greeter on Collection Home (`src/greia_launcher/home_animator.py`, `HomeGreeterVoice`) plays that character's introduction on the *first* tap of the Shell process; later taps rotate the accepted `praise.general` / `ready.go` takes. Speech goes through the launcher's single spoken-label channel and only starts when that channel is silent (never interrupts a clip; navigation labels may interrupt it), with a 3 s cooldown and at most 4 clips per minute (20 rapid taps ⇒ motion only after the 4th clip). The same reaction is reachable by keyboard/controller (greeter focus + Enter/south). Taps grant nothing. Other candidate uses (an optional meet-the-cast moment, a future gallery) remain open.

Regardless of placement:

- never auto-play all six in sequence at boot;
- only one voice plays at a time;
- introductions are interruptible/skippable;
- core navigation never depends on hearing them;
- playing an introduction cannot grant permission/progression/gameplay truth;
- reuse the accepted platform asset rather than creating Activity-local copies.

Exact scripts/voice policy live in `GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md`.

## 9. Human acceptance rule

Every **new** VoiceEngine candidate begins with human review pending. Human listening checks:

- exact locale and intended words;
- recognizable canonical identity for natural characters;
- deliberately synthetic/fun Dani identity;
- no invented/repeated sounds;
- no clipping/unwanted tail;
- acceptable pronunciation/stress;
- lively but not exhausting delivery;
- small-speaker intelligibility where relevant.

Whisper is advisory only. It never accepts audio, and tiny reactions/Dani may legitimately skip ASR.

The pre-v3 v0.2 set completed this human acceptance step. New incremental library additions still require a candidate and explicit listening before acceptance. The separately authorized 2026-10-21 corpus replacement updated only paths in its frozen scope and left them pending; it did not authorize silent approval or a second shared-library version.

## 10. Completion boundaries

### Historical authoring/content production — COMPLETE for the pre-v3 v0.2 baseline

```text
180 shared candidates generated
12 intro candidates generated
human listening recorded
accepted set versioned
v0.1 retired
v0.2 owner-accepted assets committed
```

### Runtime shared-library completion — SEPARATE

Runtime work is complete only when applicable consumers also prove:

```text
resolver reads the accepted v0.2 catalogue
only accepted variants are exposed
missing family fails soft
Activities request semantic families rather than package-local filenames
duplicate per-Activity generic reactions are not required
```

### Introduction product completion — SEPARATE

The 12 accepted clips exist, but product placement is complete only when a selected OS UX is implemented and tested under the one-voice/interruptible/non-blocking constraints above.
