# My Time — Voice production brief (approved recordings, runtime acceptance pending)

**Status, 2026-10-15:** All 16 packaged Italian/English WAV clips (title
plus seven interaction cues per locale) have been personally reviewed and
approved by the owner. The previously empty `audio` dictionaries do **not**
prevent playback anymore: `time_audio.py` requests semantic IDs through
`LocalizedResources.audio_path(key, filename="<key_with_underscores>.wav")`,
which finds approved files under `locales/<locale>/audio/` and falls back
to English. The launcher can also resolve the existing
`activity_title.wav` spelling without renaming it.

**My Time remains incubated, not release-accepted.** Runtime Pygame
speech/interaction, sound timing and installed-device testing have not yet
been executed and verified during this GitHub-only source migration.
Do not enable My Time merely because audio lookup is now connected.

**Authorities:** `skills/greia-voice-production/SKILL.md`,
`skills/greia-activity-authoring/VOICE_GENERATION.md`,
`tools/greia_voice.py` / VoiceEngine. **Speaker:** Dani's canonical
`dani_system_speech` for basic mechanism guidance; keep existing
shared ready/success/retry utterances central rather than duplicating them.
If the team prefers Modal as an authoring compute provider, it must be
integrated behind VoiceEngine; do **not** call a separate Modal API from
this Activity or silently substitute a new speaker. No voice provider
invocations are approved by this document.

## Semantically keyed recording requests

| Semantic ID | Locale | Kind / speaker | Exact intended spoken text | Trigger |
|---|---|---|---|---|
| `activity.title` | it | `dani_system_speech` / `dani` | Il mio tempo. | Greia launcher speaks the Activity name |
| `activity.title` | en | same | My Time. | Launcher |
| `presenter.welcome` | it | same | Ciao! Scopriamo il tempo insieme. | First useful frame, once |
| `presenter.welcome` | en | same | Hello! Let's explore time together. | First useful frame |
| `instruction.clock` | it | same | Guarda! Queste sono le lancette dell'orologio. | First Clock entry, repeatable |
| `instruction.clock` | en | same | Look! These are the hands of a clock. | First Clock entry |
| `instruction.practice` | it | same | Tocca i puntini per spostare le lancette. | First Practice toggle, repeatable |
| `instruction.practice` | en | same | Touch the dots to move the clock hands. | First Practice toggle |
| `instruction.stopwatch` | it | same | Premi avvia. Vediamo quanto dura! | First Stopwatch entry |
| `instruction.stopwatch` | en | same | Press start. Let's see how long it takes! | First Stopwatch entry |
| `instruction.timer` | it | same | Scegli i minuti, poi premi avvia. | First Timer entry |
| `instruction.timer` | en | same | Pick the minutes, then press start. | First Timer entry |
| `feedback.timer_finished` | it | same | Il tempo è finito! | One-shot completion |
| `feedback.timer_finished` | en | same | Time's up! | One-shot completion |
| `instruction.real_time` | it | same | Ora guardiamo l'ora vera. | Leaving Practice, optional |
| `instruction.real_time` | en | same | Now let's look at the real time. | Leaving Practice |

Keep statements emotionally neutral and non-pressuring; no shame, no
countdown alarm that startles children, no narrator speaking continuously.
Full/short first-use and repeat behavior must be decided in source *before*
audio is installed. The child may not be able to read: text labels alone are
not accepted substitutes for spoken guidance. The UI also needs a visible
repeat-voice affordance designed and tested with the canonical voice
resolver before promotion.

## Production / acceptance boundaries

1. Author reviews and approves this semantic content and chosen speaker.
2. On a prepared authoring host run only `python3 tools/greia_voice.py doctor`
   until provider use is authorized. Do not install multi-GB stacks or
   download model weights without approval.
3. Use VoiceEngine's semantic `generate`/`batch` into an external
   **review** directory. Preserve the generated receipts and exact
   input text. Natural/deterministic provider routing is the engine's job.
4. Listen to all Italian/English cues on ordinary speakers **and**
   small child-device speakers. Reject mismatch, unnatural cadence,
   clipping, silence and inappropriate synthetic voice identity.
5. **Completed for IT/EN and owner-approved:** the recordings are
   already packaged below `locales/<locale>/audio/`. Greia's shared
   filename-first resolver now connects them without one JSON mapping
   per language. Existing title files use `activity_title.wav`, a
   recognized legacy convention. Do not re-record/rename these clips.
6. Implement one shared Activity cue controller using accepted
   platform speech/feedback APIs; don't call a random mixer channel,
   stomp other Activities' voices, or make runtime synthesis requests.
   Hook welcome, first-use instructions, repeat, mode switches and
   one-shot finish. Verify every cue with live audio and focus/Home exit.
7. Pass the full pre-reader/real Shell acceptance at exact committed
   source before promotion into `activities/` or changing its
   `release` selection. Generation receipts alone never prove
   listened acceptance.

**Voice source implemented, runtime unverified:** `time_speech.py`
owns sequencing, the single pending instruction and first-use/replay/terminal
cues. `time_audio.py` uses `LocalizedResources.audio_path()` and its
legacy underscore-filename alias for the seven approved speech cues; all
selected-locale cues, including phonemes elsewhere in Greia, now permit
English audio fallback when the selected-language file is absent. Clips
decode lazily after the first useful Activity frame, not at startup.
`main.py` uses the shared `activity_resources` manifest/profile
factory. The normal Activity's audio owner still controls its own mixer,
cache and interruptions. New focused source test cases were committed
to `tests/test_activity_time_audio.py`,
`tests/test_launcher_spoken_labels.py` and
`tests/test_shared_localized_audio_paths.py`, but no Python execution
or Pygame playback evidence is claimed here.

**Additional sequencing guarantee (SOURCE-WIP):** A timer that is
already complete when the Activity starts cannot speak before READY.
Its terminal cue is held until the first meaningful frame is on screen,
and replaces (rather than queues behind) obsolete welcome/instruction
speech. A missing or invalid welcome cue does not suppress the
immediately relevant instructional recording. Closing the Activity
prevents any subsequent cue from starting. These cases are covered by
new provider-free tests but **not yet locally executed or heard**.

**Still not performed:** running the new/old Python unit tests, live
headless/GUI playback, first-frame replay and exit timing verification,
small-device speaker quality checks, real Shell launch and installed
Acer acceptance. No new audio production, owner approval or locale JSON
mapping is required for **existing** IT/EN My Time speech files.
