# Greia Voice Generation and Canonical Character Voices

**Status:** accepted voice policy + canonical authoring Voice Production Engine + owner-accepted shared/introduction v0.2 assets  
**Reviewed:** 2026-10-19
**Scope:** presenter speech, researched narration, shared reactions, pedagogical speech, Dani system speech, character introductions, multilingual static audio and human review  
**Canonical production tool:** `tools/greia_voice.py`

Related authorities:

```text
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
docs/design/GREIA_CANONICAL_CAST_SYSTEM.md
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
```

## 1. Voice Studio is an authoring workflow

“Voice Studio” is shorthand for Greia's authoring workflow around `VoiceEngine`:

```text
semantic request
-> tools/greia_voice.py / VoiceEngine
-> provider routing
-> optional advisory verification
-> review audio + receipt
-> human listening
-> versioned accepted asset promotion
```

It is not a child-runtime TTS service and does not require a GUI.

No VoxCPM2/Chatterbox/Whisper model stack runs on the Acer/child device for normal narration. Child runtime consumes reviewed prerecorded assets.

## 2. Speech has semantic jobs

Greia does not route every string through one generic TTS rule.

```text
character_dialogue
  presenter welcome, narration, researched facts, contextual hints,
  story/dialogue, natural-character introductions

shared_character_utterance
  reusable praise/success/retry/progress/start reactions

pedagogical_speech
  letters, syllables, phonics, spelling/pronunciation targets

dani_system_speech
  Dani-specific robotic dialogue/introduction
```

Governing rule:

> **If the sound itself is the educational truth being taught, use pedagogical speech. If speech communicates content through a character, use character speech.**

Text length is not the selector. A one-word character exclamation may be `character_dialogue`; a short syllable may be `pedagogical_speech`.

## 3. Canonical production boundary

All new prerecorded Greia speech production goes through:

```text
tools/greia_voice.py
```

Callers provide semantic intent:

```text
speaker
kind
locale
exact reviewed text
cue/output identity
```

Callers do not own:

```text
VoxStage/Chatterbox/MLX model selection or lifecycle
canonical cloning references/hashes
native host voice names/rates
pedagogical pronunciation workarounds
Whisper commands/models
FFmpeg trim/packaging mechanics
token budgets/silence heuristics
```

Those mechanics belong behind `VoiceEngine` and provider interfaces. Historical direct-backend producers are not accepted extension points; new work should migrate them to thin semantic VoiceEngine clients.

## 4. Canonical character identities — v0.2 active

**Performance direction and corpus follow-up (2026-10-19):** each VoxStage
recording now has acting direction from
`tools/greia_voice_core/character_delivery.json`, or a semantic
`delivery_prompt` override (CLI `--delivery-prompt`, batch and warm service).
Direction controls tone/mood/rhythm separately from spoken text; the reference
establishes identity. Receipts retain the actual effective direction.

After selecting the masters, the owner explicitly requested existing
Activity/system speech replacement, except deterministic isolated letters and
syllables. Use `tools/regenerate_voice_corpus.py` under
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`. This scoped operation revoices
whole words/numbers too, retains original backups and installs fresh takes as
human-review pending. It supersedes older no-overwrite/add-only instructions for
this operation only. V2 production completed on 2026-10-21 (4,168 DONE,
741 PRESERVED); all new takes remain listening-pending. Follow
`docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md` and the corpus tool
`review` command for read-only installed-audio screening, cached-only eligible
ASR and prioritized listening reports. Generation completion, automated coverage
and human acceptance are separate; unavailable ASR is incomplete review.

Owner decision 2026-10-19: replace the active masters with the six selected local
VoxStage voice designs and make VoxCPM2 the default character provider. The owner
accepted the selected-master comparison in English, Italian, French and Spanish.

| Character | Current voice ID | Selected audition | Speech personality |
|---|---|---|---|
| Lilli | `greia.lilli.v2` | round 2, candidate 3 | silvery theatrical cartoon unicorn, wonder and imagination |
| Leo | `greia.leo.v2` | round 1, candidate 3 | warm older storyteller, thoughtful curiosity |
| Flash | `greia.flash.v2` | round 1, candidate 2 | springy, bright, playful challenge |
| Dani | `greia.dani.v2` | round 2, candidate 3 | buzzy, precise, bouncy toy robot |
| Tito | `greia.tito.v2` | round 2, candidate 1 | cheeky woodland fox, nimble adventurous curiosity |
| Momo | `greia.momo.v2` | round 2, candidate 3 | round, furry, rubbery comic monster with musical rhythm |

Active source masters/references:

```text
assets/source/audio/character-voice-masters/v0.2/
assets/source/audio/character-voice-masters/v0.2/provenance.json
assets/audio/characters/canonical/v0.2/manifest.toml
```

Every reference is the full, unchanged selected master WAV. The registry records
its transcript, canonical ID, saved VoxStage ID and existing identity hash.
Dani now has a reviewed cloning reference. v0.1 masters/references remain
historical; they are not the source for new production. Existing accepted
runtime recordings and receipts retain their earlier identity and acceptance.

## 5. Current provider implementation

```text
all six canonical characters (dialogue, shared utterances, Dani speech)
  -> VoxStageProvider -> shared local VoxStage -> VoxCPM2 (default)

explicit character-provider=chatterbox
  -> retained ChatterboxMLXProvider, same v0.2 character references

pedagogical_speech
  -> independent deterministic native/system provider

optional semantic warning
  -> existing advisory Whisper verifier where available
```

`dani_system_speech` remains a compatible semantic kind; it now uses Dani’s
cloned master. Dani may also use ordinary `character_dialogue`. The kind never
means permission to use another character's reference.

Select the retained alternative through `--character-provider chatterbox` on
`doctor`, `generate`, `batch` or `serve`, or set
`GREIA_VOICE_CHARACTER_PROVIDER=chatterbox` for repository producers.
Unavailable default synthesis is reported, never silently replaced by another
backend or native imitation. Pedagogical pronunciation keeps its separate route.

VoxStage is an authoring dependency, not a second Greia content-production API.
Activity/OS/Encyclopedia scripts still submit semantic requests to VoiceEngine.
The adapter reuses its single serialized local worker; it owns no second MLX
process. Fresh workstations import missing saved IDs from the versioned repository
references without replacing existing voices. Language follows native text plus
concise direction; VoxCPM2 has no hard language selector. Listening remains the
pronunciation and identity gate.

Rejected directions remain rejected: cloned character speech as phonics
correctness authority, silent placeholders, and narration models on child devices.

## 6. Presenter/speech design belongs to Activity/content design

Every new Activity decides explicitly:

```text
lead presenter/mascot or deliberate none
shared character reaction plan
custom Activity-specific dialogue
pedagogical speech, if any
optional researched curiosity/fact narration
supported locales and spoken coverage
```

Use the shared library when generic praise/retry meaning is sufficient. Do not create package-local copies of generic reactions just to vary wording.

Detailed Activity guidance:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
skills/greia-activity-authoring/VOICE_GENERATION.md
skills/greia-activity-authoring/LAUNCHER_SPOKEN_LABELS.md
```

## 7. Multilingual contract

Speech uses stable semantic cue IDs independent of locale:

```text
presenter.welcome
curiosity.orca.family_pods
phonics.ma
character.intro.lilli
activity.title
```

Each shipped spoken locale owns reviewed wording/audio. Displayed and spoken wording must remain semantically aligned.

Do not:

- hard-code locale-specific gameplay branches;
- impersonate canonical characters with arbitrary system voices;
- make correctness/score/reward/difficulty depend on locale or spoken variant;
- claim a selectable locale is a fully supported spoken release language without the required content/evidence.

If a provider is unavailable during authoring, retain the cue/text plan and report audio pending. Do not fake completion.

## 8. Character dialogue and researched narration

Use `character_dialogue` for:

```text
brief welcome/orientation
contextual hints
short story/narration beats
Activity-specific explanation
finite reviewed curiosity/researched facts
natural-character introductions
launcher Activity title when that accepted presenter is the speaker
```

Facts are finite reviewed authoring content with provenance. They are never generated by an LLM at child runtime and never require network access to be spoken.

## 9. Pedagogical speech

Use `pedagogical_speech` when the child is expected to learn or imitate the sound itself:

```text
letters
letter names
syllables
phonics
spelling units
pronunciation exercises
foreign-language pronunciation targets
```

Provider-specific spellings/accent workarounds are private engine details. A fluent speaker/educator must review pronunciation-critical output.

Do not use pedagogical speech merely because a launcher label/title is short.

## 10. Shared character reaction library — v0.2 accepted assets

Semantic families:

```text
praise.general
celebrate.success
encourage.retry
encourage.progress
ready.go
```

Matrix:

```text
6 characters × 5 families × 3 variants × 2 locales = 180 shared clips
```

Current authoritative state:

```text
accepted library:       assets/audio/characters/shared/v0.2/
shared reactions:       180 generated + owner-accepted
character introductions:12 generated + owner-accepted
accepted total:         192
owner listening:        COMPLETE (2026-08-28)
retired predecessor:    assets/audio/characters/shared/v0.1/
runtime resolver wiring:separate/pending where not yet completed
```

The older v0.1 production tranche is retired historical material; see its retirement notice. Do not regress runtime/content authority back to it.

Exact semantic/status authority:

```text
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
```

Production/review authority:

```text
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
```

Asset acceptance and runtime resolver completion are different gates. The v0.2 files are accepted; consumers still need to prove correct resolver/fail-soft behavior where integration remains open.

## 11. Character introductions — accepted assets, UX placement separate

The accepted v0.2 set includes:

```text
6 characters × 2 locales = 12 intro clips
assets/audio/characters/shared/v0.2/_intros/
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

Routing used for production:

```text
Lilli/Leo/Flash/Tito/Momo -> character_dialogue
Dani                       -> dani_system_speech
```

The reviewed scripts are the canonical character-introduction copy. The asset-production/listening gate is complete; **final product placement is not**.

Candidate product uses include an optional first-run meet-the-cast moment, tappable/wandering Home characters or a future gallery.

Constraints regardless of final placement:

- never auto-play six introductions in sequence at boot;
- one voice at a time;
- speech is interruptible/skippable;
- core navigation is obvious without hearing audio;
- playing an intro cannot affect permission/progression/gameplay truth;
- reuse accepted platform assets rather than re-recording per Activity.

## 12. Launcher spoken labels

Launcher spoken labels are Shell-owned prerecorded presentation, not Activity-owned hover logic and not runtime TTS.

Current initial set:

```text
34 Activities × it/en = 68 Activity-title clips
19 Collection/sub-Collection IDs × it/en = 38 system clips
106 total owner-accepted launcher-label clips
```

Policy:

- platform Collections/sub-Collections use Leo;
- Activity title uses an explicitly accepted lead presenter when established, otherwise Leo;
- natural speakers route through `character_dialogue`;
- Dani uses `dani_system_speech`;
- never use `pedagogical_speech` merely for a launcher title;
- runtime uses reviewed static assets and fails soft if a third-party clip is absent.

Exact authoring/runtime authorities:

```text
skills/greia-activity-authoring/LAUNCHER_SPOKEN_LABELS.md
src/greia_launcher/spoken_labels.py
```

## 13. Whisper is advisory

Suitable multi-word natural-character speech may be transcribed by the configured verifier with the requested language explicitly set.

```text
PASS -> plausible transcript match; human listening still required
WARN -> likely mismatch; inspect/regenerate as appropriate
NOT_RUN / NOT_APPLICABLE -> no machine transcript gate
```

Do not use Whisper to certify letters, syllables or phonics. Dani and very short reactions may legitimately skip ASR.

## 14. Human acceptance

Every **new** engine result starts with:

```text
human_review = PENDING
```

Human listening verifies:

- intended words and locale;
- canonical character identity where applicable;
- no invented/repeated words/sounds;
- pronunciation/stress;
- no clipping/unwanted tail;
- appropriate delivery;
- small-speaker intelligibility where relevant.

A receipt, valid container, provider return code or Whisper PASS is never acceptance.

Accepted sets are versioned. Regeneration creates a new review candidate; do not silently replace accepted bytes in place.

## 15. Installation/readiness

Start with:

```bash
python3 tools/greia_voice.py doctor
```

Quick install/use:

```text
tools/greia_voice_core/README.md
```

Detailed workstation setup:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

Low-level Chatterbox details are maintainer/troubleshooting material, not the ordinary production API.

## 16. Package/runtime boundary

Never package authoring machinery into Activities/child runtime:

```text
VoxCPM2/Chatterbox/Whisper model weights
MLX/PyTorch environments
model caches
canonical cloning-reference masters
FFmpeg authoring binaries
rejected/unreviewed scratch audio
```

Runtime microphone capture is a different platform subsystem (`audio.basic`) and must not be confused with build-time speech generation.

## 17. Current status summary

Implemented authoring infrastructure:

- semantic `VoiceRequest` / `VoiceEngine` abstraction;
- canonical voice registry + hash validation;
- default shared-worker VoxStage/VoxCPM2 provider for all six v0.2 characters;
- retained explicit Chatterbox MLX alternative;
- independent deterministic macOS pedagogical provider; compatible Dani speech kind now cloned;
- shared-library authoring kind;
- optional advisory verifier;
- bounded retries;
- cross-process single-worker lock;
- warm localhost service + batch mode;
- WAV/OGG packaging;
- review receipts and owner-acceptance stamping;
- `doctor` readiness probe;
- repository setup/production runbooks.

Accepted content currently includes:

```text
shared reactions:       180 v0.2 owner-accepted clips
character introductions:12 v0.2 owner-accepted clips
launcher labels:        106 owner-accepted it/en clips
```

Separate/future work includes:

- accepted Windows/Linux native authoring providers;
- non-MLX natural-character provider where needed;
- runtime shared-utterance resolver completion where still missing;
- final character-introduction UX;
- broader release-language spoken-content certification.
