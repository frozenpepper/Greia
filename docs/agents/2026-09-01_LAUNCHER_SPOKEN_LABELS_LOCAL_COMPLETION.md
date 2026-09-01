# Greia OS — Launcher Spoken Labels: Complete Local-Agent Implementation & Voice-Production Runbook

**Date:** 2026-09-01  
**Scope:** Greia Shell / launcher Collection and Activity spoken names  
**Repository:** `frozenpepper/Greia`

**Starting implementation already present on `main`:**

```text
src/greia_launcher/spoken_labels.py
tests/test_launcher_spoken_labels.py
skills/greia-activity-authoring/LAUNCHER_SPOKEN_LABELS.md
```

This document is the execution authority for the local agent completing this tranche. Follow the current repository authorities named below if they have advanced. Do not invent a second speech, localization or launcher-input architecture.

---

# 0. Outcome required

When this tranche is complete:

1. Every child-facing **Greia Collection / sub-Collection** speaks its localized name when selected with keyboard/controller navigation or deliberately hovered by the pointer.
2. Every built-in **Activity** speaks its localized launcher title under the same interaction rules.
3. Pointer movement does not create chatter: moving inside one tile does not replay, brief fly-over does not need to speak, rapidly crossing many tiles does not queue/chop many names, and the final stable hovered destination speaks after a tiny dwell.
4. Keyboard/controller focus speaks immediately after a real semantic selection change; a clamped arrow does not replay.
5. All speech is **prerecorded authoring-time audio**. No Chatterbox/TTS/Whisper model is installed or run on the child device.
6. Greia Shell owns focus timing, playback, interruption, cache and lifecycle behavior.
7. Activity packages contribute only localized `strings.activity.title` and `audio.activity.title` resources.
8. First-party catalogue title coverage is audited and complete for the currently supported launcher locales.
9. The implementation is cheap enough for the first-generation Acer Aspire One reference floor: effectively zero extra idle work, bounded memory, no speech-driven redraw loop, no queued backlog and no noticeable navigation delay.

---

# 1. Read authority before editing

Read in order:

```text
AGENTS.md
README.md
SETUP.md
docs/DOCUMENTATION.md
docs/architecture/GREIA_ARCHITECTURE.md
docs/adr/0012-platform-architecture-constitution.md
docs/adr/0018-lightweight-ui-foundation.md
docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md
docs/adr/0028-platform-and-activity-localization-language-context.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
docs/engineering/ENGINEERING_FOUNDATIONS.md
skills/greia-os-work/SKILL.md
skills/greia-activity-authoring/SKILL.md
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
skills/greia-activity-authoring/VOICE_GENERATION.md
skills/greia-activity-authoring/LAUNCHER_SPOKEN_LABELS.md
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
HANDOVER.md
```

Do not use GitHub-hosted Actions.

Work directly on current `main` per `AGENTS.md`.

Before substantive edits:

```bash
git status --short
git branch --show-current
git pull --ff-only
git rev-parse HEAD
git log -8 --oneline
```

Expected branch:

```text
main
```

If unrelated local modifications exist, STOP and report them. Do not overwrite, stash away, reset or hide concurrent work.

---

# 2. Architecture — do not redesign this

Final runtime flow:

```text
keyboard / controller selection ──────────────┐
                                               │
pointer semantic hover + short dwell ──────────┤
                                               ▼
                                  Greia Shell semantic focus
                                               │
                         Activity ID or Collection semantic ID
                                               │
                                               ▼
                               launcher-owned spoken-label seam
                                               │
                            localized static clip resolution
                                               │
                                               ▼
                           one interruptible narration channel
                                               │
                                               ▼
                               existing pygame mixer / audio
```

Activity package responsibility:

```text
activities/<activity>/
├── activity.toml
└── locales/
    ├── it.json
    ├── en.json
    └── <locale>/audio/activity-title.wav
```

Localized mapping:

```json
{
  "strings": {
    "activity.title": "L'Acquario Magico"
  },
  "audio": {
    "activity.title": {
      "path": "locales/it/audio/activity-title.wav",
      "caption_key": "activity.title"
    }
  }
}
```

Platform Collection clips:

```text
assets/audio/system/launcher-labels/<locale>/<collection_id>.wav
```

Do **not** add launcher speech fields to `activity.toml` such as `spoken_title_it`, `speaker`, `hover_audio`, etc.

Do **not** add a second localization format.

Do **not** add launcher hover/input logic inside Activities.

Do **not** use Linux `LANG` as child-language authority.

---

# 3. Voice identity policy

This tranche requires no new runtime speaker metadata.

## 3.1 Platform Collections / sub-Collections

All Greia Shell Collection names use:

```text
speaker = leo
kind = character_dialogue
```

Reasons:

- one consistent Shell navigation narrator;
- Leo is the accepted warm oldish/savvy voice;
- system structure does not randomly change speaker while navigating;
- one natural voice can remain warm during bulk production;
- a future narrator change is an asset regeneration, not a manifest/runtime migration.

## 3.2 Activity titles

For each Activity:

1. If current accepted design/source authority explicitly defines a lead presenter, use that presenter.
2. If no lead presenter is explicitly defined, use **Leo**.
3. Do not infer a presenter from topic, icon, directory name or education category.

Routing:

```text
Lilli / Leo / Flash / Tito / Momo -> character_dialogue
Dani                               -> dani_system_speech
```

Launcher titles are ordinary communicative speech and are **never** `pedagogical_speech`, even when the title is one word.

## 3.3 Production boundary

Use only:

```text
python3 tools/greia_voice.py ...
```

Never invoke directly from this workflow:

```text
Chatterbox
mlx_audio
mlx_whisper
macOS say
afconvert
ffmpeg
canonical cloning-reference files
```

Those are VoiceEngine provider details.

---

# 4. Required locales

For this initial migration, Italian and English are the minimum required launcher speech pair because accepted Greia voice/content production currently uses `it` + `en` as its initial locale set.

Execution rule:

```text
REQUIRED_NOW = it + en wherever current catalogue/localization authority supplies them
PLUS any additional locale that current main explicitly declares as a completed/shipping child Shell catalogue locale
```

Do not treat a translated string sitting in a mapping as sufficient proof that an entire locale is a shipping locale.

Do not permanently hard-code the runtime to two locales.

---

# 5. Current built-in Activity inventory

At creation of this runbook, current `activities/` contains these **34 built-in Activity roots**:

```text
acquario_magico
baia_delle_orche
bottega_delle_misure
casa_del_dieci
clinica_cuccioli
costruiamo_ponti
cucciolo_mio
enciclopedia_greia
festa_delle_rime
foresta_parole
la_discesa_della_biglia
labirinto_magico
luci_di_momo
memory_meraviglie
morbidi_mostriciattoli
nanna_delle_nuvolette
nascondino_bosco
officina_dei_suoni
orchestra_animali
painting
pasticceria_magica
piccola_serra
posta_di_leo
shape_garden
sillabe_magiche
specchi_magici
stelle_incantate
storie_della_mia_voce
teatrino_fiabe
treno_numeri
viaggio_delfino
volo_draghetto
workshop_settings
writing
```

Before generation, compare against actual current main:

```bash
find activities -mindepth 1 -maxdepth 1 -type d -print | sort
```

Current `main` is authority. Mention additions/removals in the final report.

Never synthesize spoken titles from directory names. Exact spoken copy comes from each locale bundle's:

```text
strings.activity.title
```

---

# 6. Platform Collection voice inventory

Child-facing Collection vocabulary derives from:

```text
src/greia_launcher/catalogue_view.py
src/greia_launcher/collection_home_presentation.py
src/greia_launcher/adaptive_discovery_presentation.py
```

Use **Leo** for all system entries below.

## 6.1 Primary/fallback Collections

| ID | Italian | English |
|---|---|---|
| `create` | `Crea` | `Create` |
| `play` | `Gioca` | `Play` |
| `learn` | `Impara` | `Learn` |
| `explore` | `Esplora` | `Explore` |
| `my_greia` | `Mio Greia` | `My Greia` |
| `browse` | `Altro` | `More` |

## 6.2 Adaptive sub-Collections

| ID | Italian | English |
|---|---|---|
| `drawing` | `Disegna` | `Drawing` |
| `writing` | `Scrivi` | `Writing` |
| `music` | `Musica` | `Music` |
| `building` | `Costruisci` | `Building` |
| `numbers` | `Numeri` | `Numbers` |
| `words` | `Parole` | `Words` |
| `puzzles` | `Rompicapi` | `Puzzles` |
| `nature` | `Natura` | `Nature` |
| `stories` | `Storie` | `Stories` |
| `making` | `Crea cose` | `Making` |
| `care` | `Prenditi cura` | `Caring` |
| `action` | `Azione` | `Action` |
| `settings` | `Il mio spazio` | `My space` |

Initial expected system candidate count:

```text
19 IDs × 2 locales = 38 candidates
```

`all` is currently an internal catalogue projection, not a normal child Home destination. Do not generate `all.wav` just because a translation exists. Add it only if the final current UI exposes `all` as a selectable child destination.

If current `main` adds a child-facing Collection, include it.

Runtime destination:

```text
assets/audio/system/launcher-labels/it/<id>.wav
assets/audio/system/launcher-labels/en/<id>.wav
```

---

# 7. Runtime implementation pass

Read current:

```text
src/greia_launcher/spoken_labels.py
src/greia_launcher/presentation.py
src/greia_launcher/collection_home_presentation.py
src/greia_launcher/adaptive_discovery_presentation.py
src/greia_launcher/catalogue_view.py
src/greia_launcher/child_shell.py
```

Confirm the exact mixin/composition order used by the real child launcher. Do not wire a dead class that is not composed into the child Shell.

## 7.1 Keep `SpokenLabelPlayer` narrow

It owns only:

```text
static Sound load/cache
one narration channel
deduplication of same semantic identity
stop/replace previous spoken label
bounded cache
fail-silent optional presentation errors
```

It must not own:

```text
mouse geometry
Activity grid indices
Collection layout
keyboard key codes
raw controller IDs
profile policy
gameplay
```

## 7.2 One shared semantic spoken-focus seam

Do not scatter five slightly different announcement implementations across presentation mixins.

Preferred behavior surface:

```text
announce_activity(...)
announce_collection(...)
pointer_focus_changed(...)
navigation_focus_changed(...)
poll_pending_pointer_focus(...)
clear_pointer_focus(...)
stop(...)
```

This can be a small controller in `spoken_labels.py` or cohesive launcher helper methods. Do not create a framework. Collection Home, adaptive sub-Collections and Activity cards must route through the same semantic path/player.

---

# 8. Pointer hover policy — add a tiny dwell

Raw `MOUSEMOTION` must not directly produce speech for every crossed tile.

Use a semantic pointer dwell of approximately:

```text
140–180 ms
starting value: 160 ms
```

Keyboard/controller selection has no dwell.

Flow:

```text
pointer enters speakable target
-> remember identity + clip + due_at
-> same target remains active
-> after ~160 ms announce once
```

If pointer leaves before due time, cancel the pending announcement.

Rapid A -> B -> C should become:

```text
A cancelled
B cancelled
C survives dwell
-> only C speaks
```

This prevents audio scrubbing/chopped first syllables.

Do not create a timer thread. Use existing monotonic time / launcher polling. A timestamp comparison while an announcement is pending is enough and does not require a redraw.

Semantic identity:

```text
activity:<canonical_activity_id>
collection:<collection_id>
```

Never use localized title strings or screen coordinates as identity.

Leaving a target cancels pending speech and clears pointer focus so later re-entry can speak again. It does not have to abruptly cut a title that already began merely because the pointer moved one pixel away; a new semantic destination/navigation focus will interrupt it.

---

# 9. Keyboard/controller selection policy

Announce immediately after a **real semantic focus change**.

For Activity cards, pattern:

```python
old_index = self._selected
# existing bounded navigation mutates self._selected
if self._selected != old_index:
    self._announce_selected_activity(pygame)
```

Apply the same semantic change check to:

```text
Collection Home
adaptive sub-Collection chooser
TAB navigation where it changes focus
page navigation where it changes selected Activity
```

A clamped arrow at a boundary must not replay.

Controller support must use the existing runtime-neutral navigation path from ADR 0020. Do not add controller-brand or raw joystick logic to spoken labels.

---

# 10. Pointer target coverage

Inspect current target actions. At minimum the speech router should understand actual child destination targets such as:

```text
home_collection
activity_subcollection
presented_activity
presented_activity_select
activity_category
```

Do not blindly announce every `HitTarget`.

Exclude unrelated actions such as profile switching, error dismissal, page arrows, Parent controls and protected system chrome unless a separate product requirement explicitly adds them.

This feature is Collection/category and Activity naming, not a generic screen reader.

---

# 11. Lifecycle / stop behavior

Launcher narration must not leak into an Activity.

Stop/clear spoken labels:

```text
immediately before Activity launch
logout / leave child launcher session
profile switch
launcher shutdown
mode changes where the previous launcher focus is no longer meaningful
```

Do not delay Activity launch waiting for a name to finish.

Click launch must remain immediate.

---

# 12. Audio-channel ownership

The current player uses pygame mixer. Inspect other current launcher mixer usage before finalizing channel allocation.

Goal:

```text
one dedicated/interruption-safe Shell narration channel
```

Avoid randomly stealing an important concurrent Shell sound.

If compatible with current audio ownership, reserve one narration channel once and reuse it. Do not repeatedly increase the global channel count, allocate a new channel per hover, or use a subprocess audio player.

Add focused tests around the final channel rule.

---

# 13. Runtime audio format and cache

Prefer `.wav` launcher labels unless physical evidence gives a concrete reason to choose OGG.

VoiceEngine's WAV packaging is already:

```text
PCM signed 16-bit
22050 Hz
mono
```

This is appropriate for small low-latency launcher clips and avoids a first-touch Vorbis decode on the Acer.

Keep the Sound cache bounded. Starting target:

```text
cache_entries ~= 48
```

Do not preload the entire catalogue at boot. Start with lazy loading. Only consider prewarming the current visible page if actual physical first-hover latency is unacceptable; never preload all Activities just in case.

Speech playback must not trigger a full-screen repaint.

---

# 14. Clip delivery targets

Launcher speech is navigation, not narration.

Targets:

```text
Collection label: normally <= 1.5 s
Activity title:   normally <= 2.5 s
investigate/review > 3.0 s
```

Human review rejects:

```text
long dead air before speech
clipped first consonant
clipped ending
repeated title
invented words/syllables
wrong locale
wrong canonical speaker identity
excessively theatrical delivery
unwanted long tail
poor small-speaker intelligibility
```

Do not rename an Activity only to make the clip shorter without product/design authority.

---

# 15. Build deterministic Activity inventory before generation

Create a temporary migration workspace:

```text
tmp/voice-review/launcher-spoken-labels/
```

Do not commit the temporary candidate workspace.

Generate a machine-readable inventory with:

```text
activity_root
canonical activity id
locale
strings.activity.title
audio.activity.title present?
resolved current audio file exists?
explicit accepted lead presenter?
presenter source path
chosen launcher-title speaker
candidate output path
human review state
```

Parse:

```text
activities/*/activity.toml
activities/*/locales/*.json
```

with `tomllib` and `json`, not regex.

Presenter resolution:

```text
explicit current accepted presenter -> that speaker
otherwise                         -> leo
```

Record the source as one of:

```text
explicit:<project-relative-path>
fallback:launcher-leo
```

Do not infer from directory name/topic/icon.

If a valid owner-accepted launcher title already exists, do not regenerate merely for uniformity. If acceptance provenance is unclear, mark it `EXISTING_UNVERIFIED` and include it in human review.

---

# 16. Voice Studio / VoiceEngine readiness

From repository root:

```bash
python3 tools/greia_voice.py doctor
```

For natural canonical voices on Apple Silicon confirm the canonical anchors are hash-valid and the Chatterbox MLX provider is available. Also inspect:

```text
ffmpeg availability
canonical voice anchors
Chatterbox multilingual provider
Whisper verifier, when installed
macOS system provider for Dani
```

If the production environment is not ready, follow:

```text
tools/greia_voice_core/README.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

Do not silently download/install a multi-GB model stack without existing owner/project authorization.

---

# 17. Generate efficiently — keep the model warm

Do not run a hundred isolated one-shot generations that repeatedly load Chatterbox.

Bulk first-pass production:

```bash
python3 tools/greia_voice.py batch --input <requests.jsonl>
```

`batch` owns the generation lock and keeps the engine/model warm.

Recommended sequence:

```text
1. doctor
2. create system Collection request JSONL
3. create Activity-title request JSONL
4. run batch sequentially / as one production session
5. inspect per-row results
6. use warm serve only for targeted retries
7. shutdown cleanly
```

For targeted retries:

```bash
python3 tools/greia_voice.py serve
```

then `request`, then:

```bash
python3 tools/greia_voice.py shutdown
```

Never run a warm service and batch concurrently. Never launch multiple Chatterbox workers.

---

# 18. System Collection request contract

Every system request uses:

```text
speaker = leo
kind = character_dialogue
cue_id = launcher.collection.<collection_id>
output = tmp/voice-review/launcher-spoken-labels/system/<locale>/<collection_id>.wav
```

Example:

```json
{"speaker":"leo","kind":"character_dialogue","locale":"it","text":"Crea","cue_id":"launcher.collection.create","output":"tmp/voice-review/launcher-spoken-labels/system/it/create.wav","verification":"off","max_attempts":2}
```

For one-word/very-short labels, `verification:"off"` is acceptable because Whisper is low-value on tiny natural labels; human listening remains mandatory.

For multi-word labels (`Mio Greia`, `My Greia`, `Crea cose`, `Prenditi cura`, `Il mio spazio`, `My space`) leave verification `auto` unless the verifier demonstrably misbehaves.

Whisper PASS never equals human acceptance.

---

# 19. Activity title request contract

For every missing title candidate:

```text
speaker = explicit accepted lead presenter OR leo fallback
kind = character_dialogue, except Dani -> dani_system_speech
locale = exact localization-bundle locale
text = exact strings.activity.title
cue_id = activity.title
output = tmp/voice-review/launcher-spoken-labels/activities/<root>/<locale>/activity-title.wav
```

Example natural presenter:

```json
{"speaker":"tito","kind":"character_dialogue","locale":"it","text":"L'Acquario Magico","cue_id":"activity.title","output":"tmp/voice-review/launcher-spoken-labels/activities/acquario_magico/it/activity-title.wav","verification":"auto","max_attempts":2}
```

Fallback example:

```json
{"speaker":"leo","kind":"character_dialogue","locale":"en","text":"Example Activity","cue_id":"activity.title","output":"tmp/voice-review/launcher-spoken-labels/activities/example/en/activity-title.wav","verification":"auto","max_attempts":2}
```

Explicit Dani example:

```json
{"speaker":"dani","kind":"dani_system_speech","locale":"it","text":"<exact localized title>","cue_id":"activity.title","output":"tmp/voice-review/launcher-spoken-labels/activities/<activity>/it/activity-title.wav","verification":"off","max_attempts":2}
```

Do not manually call macOS system TTS for Dani. VoiceEngine routes it.

---

# 20. Human review workflow

Every generated result begins:

```text
human_review = PENDING
```

The agent must not mark it accepted because generation returned 0, WAV parses, receipt exists or Whisper says PASS.

Prepare a review manifest ordered:

```text
system IT
system EN
Activities IT
Activities EN
other required locales
```

For each candidate:

```text
[ ] exact words
[ ] correct locale
[ ] correct speaker identity
[ ] no invented/repeated sounds
[ ] no clipped start
[ ] no clipped end
[ ] no excessive silence/tail
[ ] concise launcher delivery
[ ] intelligible on small speaker
[ ] accepted / reject / regenerate
```

Only human/owner listening can promote a candidate into runtime source.

Rejected candidates stay in the temp workspace and must not be packaged.

---

# 21. Promote accepted system clips

Create final roots when needed:

```bash
mkdir -p assets/audio/system/launcher-labels/it
mkdir -p assets/audio/system/launcher-labels/en
```

Copy only accepted candidates:

```text
tmp/voice-review/launcher-spoken-labels/system/it/<id>.wav
  -> assets/audio/system/launcher-labels/it/<id>.wav
```

and equivalent English/other required locales.

Keep receipts according to current Voice Production evidence policy. Do not dump receipts/model/cache material into runtime asset directories unless current authority explicitly says so.

---

# 22. Promote accepted Activity clips

For each accepted locale:

```text
candidate:
tmp/voice-review/launcher-spoken-labels/activities/<root>/<locale>/activity-title.wav

runtime:
activities/<root>/locales/<locale>/audio/activity-title.wav
```

Update the locale JSON by **merging**:

```json
"audio": {
  "activity.title": {
    "path": "locales/<locale>/audio/activity-title.wav",
    "caption_key": "activity.title"
  }
}
```

Preserve all existing audio entries and unrelated localization content.

Do not modify Activity Python merely to support launcher title speech.

---

# 23. Create first-party completeness audit

Create:

```text
tools/audit_launcher_spoken_labels.py
```

This is a first-party release-quality audit, **not** a third-party runtime rejection mechanism.

For every built-in Activity locale considered complete, verify:

```text
locale JSON parses
strings.activity.title exists
audio.activity.title exists
caption_key is sensible / activity.title when supplied
path is safe and package-relative
resolved path remains inside Activity root
file exists
suffix is .wav or .ogg
```

Report totals for complete/missing text/missing mapping/missing file/unsafe path.

For platform Collections, verify every current child-facing ID + required Shell locale has:

```text
assets/audio/system/launcher-labels/<locale>/<id>.wav
```

Derive Collection vocabulary from platform authority where practical; do not maintain another drifting hard-coded catalogue if avoidable.

Do **not** change `ActivityRegistry` so third-party Activities become invalid solely because spoken title audio is missing. Runtime remains fail-soft: missing optional clip means silence, not hidden/unlaunchable Activity.

Integrate the final audit into `make verify` only when the migrated built-in tree can pass, or use an explicit migration/report mode during the production tranche. Final release-gate mode must fail on first-party omissions.

---

# 24. Automated test requirements

Expand focused tests to cover real integration, not only the standalone resolver/player.

Required cases:

1. Activity keyboard selection changes -> title announced once.
2. Clamped arrow -> no replay.
3. Page change that changes Activity -> new title announced.
4. Pointer enters Activity -> does not spam before dwell.
5. Stable pointer past dwell -> one announcement.
6. Repeated motion inside same tile -> no replay.
7. A -> B -> C faster than dwell -> only final stable target speaks.
8. Pointer leaves before dwell -> pending speech cancelled.
9. Leave after speech and later re-enter -> may speak again.
10. New semantic destination interrupts/replaces previous label.
11. Collection Home keyboard selection speaks.
12. Collection Home pointer hover uses same dwell/controller.
13. Adaptive sub-Collection keyboard selection speaks.
14. Adaptive sub-Collection pointer hover speaks.
15. Missing Activity clip fail-silent.
16. Missing Collection clip fail-silent.
17. Corrupt/unloadable Sound fail-silent.
18. Exact locale fallback.
19. Base-language fallback.
20. English compatibility fallback according to current contract.
21. Activity launch calls `stop()`.
22. Logout/profile switch clears/stops stale narration.
23. Cache remains bounded after more unique clips than capacity.
24. Activity package code does not import launcher spoken-label code.
25. Controller behavior stays on the existing runtime-neutral navigation path with no raw-controller speech branch.

Unit tests should use fake mixer/channel objects where possible; no physical audio device is required.

---

# 25. Source verification commands

Minimum focused test:

```bash
python3 -m pytest -q tests/test_launcher_spoken_labels.py
```

Discover current relevant launcher tests:

```bash
find tests -maxdepth 1 -type f -name 'test_*launcher*.py' -print | sort
find tests -maxdepth 1 -type f -name 'test_*collection*.py' -print | sort
find tests -maxdepth 1 -type f -name 'test_*discovery*.py' -print | sort
```

Run the actual matching files without suppressing final failures.

Lint changed Python:

```bash
ruff check \
  src/greia_launcher/spoken_labels.py \
  src/greia_launcher/presentation.py \
  src/greia_launcher/collection_home_presentation.py \
  src/greia_launcher/adaptive_discovery_presentation.py \
  tests/test_launcher_spoken_labels.py \
  tools/audit_launcher_spoken_labels.py
```

Then:

```bash
make verify
```

Do not use `|| true` on final verification.

---

# 26. Simulator acceptance

Unit/source tests are not enough. Use the real Greia Simulator according to current Simulator/launch-acceptance documentation.

## Collection Home

Exercise:

```text
enter child profile
land on Home
arrow across >=4 Collections
press repeatedly against a boundary
slow pointer hover and hold
move inside same Collection target
rapidly sweep across >=4 Collections
stop on final Collection
```

Expected:

```text
keyboard focus -> immediate speech
boundary -> no replay
stable pointer -> one speech
motion inside same tile -> no replay
rapid fly-over -> no queue/chopped sequence
final stable hover -> final name
```

## Adaptive sub-Collection layer

Enter a currently subdivided Collection and repeat keyboard/pointer checks on the sub-Collection chooser.

## Activity grid

Exercise:

```text
enter Collection
arrow across >=5 Activities
page if applicable
hover >=5 Activities
rapidly sweep across them
leave/re-enter same Activity
launch while title is currently playing
```

Expected launch behavior:

```text
Activity launch begins immediately
launcher narration stops
title speech does not leak into Activity
```

Repeat materially for Italian and English/current required locale set.

---

# 27. Performance requirements

These are correctness constraints.

## Idle CPU

No background TTS/audio worker. Allowed additional idle work is only a tiny timestamp comparison while pointer speech is pending. No speech-driven continuous redraw, filesystem polling, subprocess or busy loop.

## Input latency

Selection/navigation updates first. Speech is best-effort presentation afterward. Audio load failure cannot delay or undo navigation.

## No queue

Never create a spoken-label FIFO. New semantic focus interrupts/replaces previous narration. Pointer dwell prevents most accidental starts.

## Cache

Keep bounded, starting around 48 Sound entries. Verify eviction after exceeding capacity. Do not add unbounded localization/audio dictionaries.

## Decode/disk

Prefer short 22.05 kHz mono WAV. Lazy-load; do not preload full catalogue at boot.

## Rendering

Speech does not require repaint. Existing hover/selection visuals own their normal invalidation only.

---

# 28. Physical Acer acceptance

When physical Acer hardware is available, measure/observe:

```text
idle launcher CPU before/after
launcher RSS before/after
first uncached label start latency
cached label start latency
rapid pointer traversal
rapid keyboard traversal
Activity launch during speech
small-speaker intelligibility
```

Minimum acceptance:

```text
[ ] no noticeable UI pause when speech begins
[ ] no audio backlog after fast navigation
[ ] no runaway RSS after visiting many destinations
[ ] idle CPU unchanged within ordinary measurement noise
[ ] Activity launch remains immediate
[ ] names understandable through Acer speaker
```

Use existing Greia instrumentation where practical; do not permanently add a heavyweight profiler.

If physical test cannot run, report exactly:

```text
PHYSICAL-UNVERIFIED
```

Simulator evidence is not Acer evidence.

---

# 29. Update authoring skills

Update `skills/greia-activity-authoring/SKILL.md` so every new first-party Activity includes spoken launcher-title completion for every completed catalogue locale and points to `LAUNCHER_SPOKEN_LABELS.md`.

Update `skills/greia-activity-authoring/VOICE_GENERATION.md` with a concise launcher-title rule:

```text
semantic cue = activity.title
runtime playback = Shell-owned
production = VoiceEngine
explicit accepted lead presenter -> use presenter
no explicit presenter -> Leo
never pedagogical_speech
human review mandatory
```

Update `skills/greia-activity-authoring/LAUNCHER_SPOKEN_LABELS.md` so fallback behavior is deterministic:

```text
explicit accepted lead presenter -> use presenter
no explicit presenter            -> Leo
platform Collections             -> Leo
```

Do not add speaker metadata to `activity.toml`.

Update `skills/greia-os-work/SKILL.md` only with a concise rule/pointer if needed. Keep routers small.

---

# 30. Documentation / repository closure

Because final execution is substantive platform implementation, follow `AGENTS.md` after code/audio integration:

1. Append an accurate dated progress entry to `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`.
2. Update `HANDOVER.md` with ending SHA, files, voice totals, human-review state, tests, Simulator state, Acer state and blockers.
3. Update the stable launcher/product/design authority if spoken hover/focus becomes normative behavior there.
4. Never rewrite older historical progress entries.
5. Commit coherent work directly to `main`.

Do not claim whole-feature completion until source integration is green, required first-party clips are human-approved, the final catalogue audit passes, and final state passes Simulator acceptance. Keep physical evidence separately labeled.

---

# 31. Required generation accounting

System baseline:

```text
19 Collection/sub-Collection IDs × 2 locales = 38 candidates
```

If `all` becomes child-facing, add 2. Add `19 × N` for any additional currently shipping Shell locales.

Current built-in Activity roots:

```text
34
```

Maximum simple it/en title combinations if every Activity has both bundles:

```text
34 × 2 = 68
```

Do not assume 68; inventory real bundle coverage and existing accepted audio.

Report:

```text
TITLE_LOCALE_COMBINATIONS=
ALREADY_ACCEPTED=
NEEDS_GENERATION=
GENERATED=
REJECTED_OR_RETRY=
HUMAN_ACCEPTED=
MISSING=
```

A completely missing simple two-locale catalogue would therefore be roughly:

```text
38 system + up to 68 Activity = up to 106 clips
```

Actual generation must reuse accepted existing clips.

---

# 32. Final audit acceptance

Before completion:

```bash
python3 tools/audit_launcher_spoken_labels.py
make verify
```

Final audit should conceptually report:

```text
BUILT_IN_ACTIVITIES=<n>
ACTIVITY_TITLE_LOCALE_COMBINATIONS=<n>
ACTIVITY_TITLE_COMPLETE=<same n>
COLLECTION_LABELS_REQUIRED=<n>
COLLECTION_LABELS_COMPLETE=<same n>
UNSAFE_PATHS=0
MISSING_AUDIO_MAPPINGS=0
MISSING_AUDIO_FILES=0
RESULT=PASS
```

Do not weaken the final gate just to get green.

---

# 33. Stop conditions

STOP and report rather than improvising if:

- current main replaced `SpokenLabelPlayer` with a different accepted owner;
- the real child launcher no longer composes the files named here;
- current locale authority contradicts the assumed initial it/en baseline;
- a newer accepted decision selects another Shell narrator;
- VoiceEngine/anchors are unhealthy;
- making the feature work would require Activity participation or child-runtime TTS;
- mixer/channel conflicts require a broader audio architecture change;
- Acer evidence shows unacceptable latency/CPU/RSS and the remedy is a significant architecture redesign.

Do not create an out-of-contract workaround.

---

# 34. Evidence to return to Otta

Return one continuation-safe report:

```text
STARTING_MAIN_SHA=
ENDING_MAIN_SHA=

SOURCE_FILES_CHANGED=
DOCS_FILES_CHANGED=

BUILT_IN_ACTIVITY_ROOTS=
ACTIVITY_TITLE_LOCALE_COMBINATIONS=
ACTIVITY_ALREADY_ACCEPTED=
ACTIVITY_GENERATED=
ACTIVITY_HUMAN_ACCEPTED=
ACTIVITY_PENDING_OR_REJECTED=

SYSTEM_LABELS_REQUIRED=
SYSTEM_LABELS_GENERATED=
SYSTEM_LABELS_HUMAN_ACCEPTED=
SYSTEM_LABELS_PENDING_OR_REJECTED=

VOICE_DOCTOR_RESULT=
CHATTERBOX_PROVIDER=
WHISPER_VERIFIER=
GENERATION_BATCH_RESULT=

FOCUSED_PYTEST=
LAUNCHER_REGRESSION_TESTS=
RUFF=
MAKE_VERIFY=
SPOKEN_LABEL_AUDIT=

SIMULATOR_IT=
SIMULATOR_EN=
RAPID_POINTER_TRAVERSAL=
RAPID_KEYBOARD_TRAVERSAL=
ACTIVITY_LAUNCH_DURING_SPEECH=

ACER_CPU=
ACER_RSS=
ACER_AUDIO_LATENCY=
PHYSICAL_STATUS=

BLOCKERS=
NEXT_EXACT_ACTION=
```

Preserve the review manifest, generation receipts, rejected/retry list and exact human-acceptance list according to current Voice Production policy.

Do not return/commit model weights, model caches, MLX environment, rejected candidate WAVs as runtime assets or unrelated build artifacts.

---

# 35. Final implementation principles

```text
one semantic focus system
one launcher playback owner
one interruptible narration channel
one bounded Sound cache
one localization contract
one Voice Production Engine
zero runtime TTS
zero Activity-side launcher speech
zero queued name backlog
zero guessed presenter metadata
```

The goal is to make Greia substantially easier for pre-readers without turning the Shell into a speech framework or making Activities dependent on launcher implementation details.
