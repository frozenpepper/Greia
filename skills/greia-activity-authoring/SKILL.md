---
name: greia-activity-authoring
description: Design and build one or more Greia Activities from a parent's request. Child/play/teaching design comes first, followed by clean implementation, prerecorded speech, repeated headless Simulator integration and final GUI user review.
---

# Greia Activity Authoring

## Current corpus voice operation (2026-10-19)

The owner authorized existing Activity/system speech replacement through
`tools/regenerate_voice_corpus.py`; follow
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md` for planning, metadata repair,
serial production, progress, restore and pending listening. Deterministic
isolated letters/syllables stay unchanged. Normal authoring still uses
VoiceEngine. Its `delivery_prompt` field now supports per-cue tone/mood direction
through VoxStage; six editable character defaults apply when omitted.
After generation, follow `docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md` for
read-only screening and a prioritized listening queue. Missing ASR is incomplete
review; machine results never grant human acceptance.

**Status:** living Activity-authoring contract  
**Reviewed:** 2026-10-17

The normal entry point is simple:

> **A parent asks for one or more Activities.**

Act as a small Activity designer/producer, not merely a coder. Turn the request into coherent child experiences, plan the set, implement each Activity cleanly, and prove the final result through Greia.

## 0. One-shot checklist

Follow every line to get a decent Activity before any live test. Numbers are Acer Aspire One (Atom N270, 1024×600) measurements unless stated; each line points to its detailed section.

**Design and UX**
- Design the child loop before code: fantasy, repeated action, first five seconds, a real ending in 1–3 minutes (§3, §4, §7).
- A pre-reader must be able to play: pictures, motion and demonstration; any language needed to know what to do is spoken, never text-only (§5).
- One feedback grammar through `CastFeedback`: try-again demonstrates, never a bare "wrong"; no answer-revealing UI (§11.3).
- Idle hints only through `IdleHintScheduler` (6 s, +12 s, +24 s, then silence until input); wrap hint animations in `animation_seconds()` (≤1.5 s on the floor). A held steering key or button is play, not absence: it resets idle timers (§11.3).

**Layout and controls**
- Author once on the 1024×600 logical canvas with `ControlLayout.for_canvas`; capture at 1024×600 **and** 800×480; nothing in `layout.protected` (Home/Back, top-left, is platform-owned, ADR 0019) (§11.1).
- Compose buttons, tabs, HUD, prompts and completion from the kit (`greia_platform.activity_controls`, ADR 0037), never hand-drawn; custom hit areas are `ExternalTarget` so keyboard/controller focus still reaches them (§11.1).
- Mouse-first: controls used together form one `layout.cluster(...)` bottom-right/bottom-centre, at most 1–2 button widths apart. No two-thumb split layouts (colline's GO/BRAKE ~740 px apart was the counter-example); only paging arrows may flank their content (§11.1).
- Sizes for 4–7-year-olds: primary targets ≥64×64 logical px; the kit enforces a ≥40 px physical touch floor; large CAPITAL labels from `LocalizedResources.text` (ADR 0034) (§5, §11.1).
- Play acting directly on arrows/Space (`directional`, `game`, direct-key `hybrid`) shows a `KeyboardHint` in the cluster's hint slot that lights with the real key or D-pad/south button (§11.1).

**Art**
- Shared library first (`python3 tools/visual_authoring_library.py search <need>`): `bg.*`, `prop.*`, `creature.*`, `icon.hud.*`, `ui.keycap.*`, `fx.*`, `character.<id>` poses from `assets/catalog/shared_visuals_v1.toml`, by semantic ID. Never redraw the cast; no emoji as content (§11.2).
- New SVG only for a demonstrated gap: Opus + `docs/design/GREIA_SVG_AUTHORING_RULES.md`, `rsvg-convert` in scratch, then register shared art in `shared_visuals_v1_source.toml` + `make visual-assets`, or keep it Activity-private and list it for promotion (§11.2).

**Performance (reference floor)**
- The loop is a `FrameGovernor`: no `Clock.tick`, no unchanged flips. Decoration is `ambient` (frozen after 6 s idle on the floor); only steering, feedback and physics are `animating` (§11.6).
- Prepare every alpha surface blitted per frame: a per-pixel-alpha blit costs ~0.22 µs/px (≈134 ms full screen) against ~1.5 ms RLE-encoded, so use `prepare_static` / `PreparedSurfaces` / `FadeSteps` / `HudOverlay`. That includes big one-off sprites (volo's 900 px finish rainbow cost ~90 ms a frame; prepare it when built, not on the frame it appears) and cast poses (`CastFeedback` does it; your own pose blits use `art.presentable(pose, canvas)`: a 150 px pose 4.9 → 0.2 ms) (§11.7).
- Nothing expensive per frame: no sprite `set_alpha`, `smoothscale`, `rotate`, text rendering, font construction, gradients, decoding or file IO. Keep the display-format canvas (a 24-bit canvas alone cost ~25 ms/frame) (§11.5, §11.7).
- Motion games: ≤40 ms of work per frame so they reach the 24 fps floor cap; small sprites over a cached background use `plan_regions` dirty rectangles (§11.6, §11.7).
- Come to rest when the child stops: nothing self-drives to a finish while idle; finished levels, auto-motion and celebrations end in a still screen (colline's buggy now parks after 3 s without a pedal, idle 47% → 1–2%; volo and delfino slow to rest 20 s after the last input, after both idle hints, volo idle 97% → 1.1%). An unattended round ends within ~20 s (foresta's rain 40 → 20 s, RSS flat). A full render costs 150–220 ms, so never re-render a still screen on a timer or on plain pointer motion (§11.6).
- Bound every cache, list and queue; RSS stays flat while idle (§11.5).

**Start-up and audio**
- Nothing heavy before the first frame: synthesized cues **and voice clips** go into a `DeferredSoundBank` (synthesis cost 2–7 s of launch; delfino 8.0 → 5.6 s once its voice decode also moved after the first frame and its picker thumbnails shared identical scene parts), then `mark_activity_ready()` right after the first presented frame. Target ~7 s to READY on the Acer (games measured 6.4–8.5 s; the Shell's ready timeout is 15 s) (§11.4).
- The platform covers the start-up gap: the Activity entry presents the Shell's launch card in your window right after your first `set_mode` (no black screen; ADR 0037 §6a *Launch cover*). Call `set_mode` once early, do not pass `HIDDEN` yourself (the entry opens your first window hidden and shows it with the card, so nothing black is mapped) and do not paint a blank/black frame before your real first frame. Greia's Home is on screen from the launch card on; a Home tap before your READY ends the launch at once, so do not do irreversible work before READY. The cover hides the wait, it does not shorten it, so the start-up budget above still applies.
- Use the shared synthesis primitives, never a private copy: `greia_platform.pygame_audio` provides `decaying_sine`, `mix_samples`, `sweep_samples`/`sweep_sound` and the cue recipes `bell_sound`, `chord_sound`, `chime_run_sound`, `fanfare_sound`; `tools/validate_activity.py` now also checks the import allowlist (`runtime/child-runtime.toml`) through the runtime adapter, so an import the launcher would refuse (exit 126) fails validation.
- Keep synthesis cheap: the platform paces the bank's background worker so it cannot starve your loop, but a 10 s synthesis stays a 17 s warm-up; build sample lists and pack them with `mono_pcm16_bytes` instead of per-sample `append_mono_pcm16`, and compute decaying partials as a complex phasor under `itertools.accumulate` instead of a `sin` + `exp` per sample (identical 16-bit samples, 2.8× faster: colline_allegre 0.16 → 0.057 s on the Mac, ~10 s on the Atom) (§11.4).
- Play audio only through plain `pygame.mixer` (lease-aware). Never ctypes/`pygame._sdl2` playback, `mixer.quit()`, music or end-events; `Sound.play` on a closed mixer segfaults pygame 2.1.2 (§11.4).
- Speech: shared cast lines and the vocab bank, locale → base → English → silence; fully playable in silence; no new voice lines without owner acceptance (§7A, §8).

**Data and language**
- Never emit facts (or write storage) on the frame thread in a tap's path: an emit is a synchronous broker round trip (Acer: 61–86 ms, outliers 0.5–1.6 s), so quattro_amici froze the falling disc 95–618 ms after every child tap; a bounded one-worker FIFO (`GreiaQuattroEvents`, `GreiaDelfinoEvents`) brought release → first falling frame to 31–58 ms.
- Event/idempotency keys ≤64 bytes (`runtime/history-policy.toml`); declare a bound for every new interpolated value in `tests/test_activity_event_key_bounds.py` (§10).
- Text only via `resources.text(key, variables)` (`$name` placeholders), resolved once; no fixed-language fallback sentences; manifests declare the four released locales en/it/es/fr (§7A).

**Pre-flight without hardware**
- `tools/validate_activity.py`, focused tests, headless captures at both sizes (one with `--press-key`), `tools/measure_activity_idle_cpu.py --settle 15` (~0 presents/s on a still screen); then the Acer method in `docs/agents/GREIA_AGENT_OPERATIONS.md` §8 with `tools/dev_source_deploy.py` (§13, §16).

## 1. Mandatory authoring loop

For every new Activity request:

```text
parent request
-> decompose into one or more coherent Activity concepts
-> design child fantasy + play/teaching loop
-> choose defensible minimum age + challenge model
-> design no-reading communication + required speech
-> choose presenter, feedback/audio sequencing and progression semantics
-> plan implementation + Activity-local authoring tools
-> implement one small vertical slice
-> headless Greia Simulator
-> iterate with focused tests + headless Simulator
-> produce/review required prerecorded voice/assets
-> final exact-state headless Simulator
-> launch GUI Greia Simulator
-> user reviews actual child experience
-> accepted only after applicable evidence is complete
```

Do not build first and try to make it child-friendly afterward.

## 2. Creation core — load these every time

Before coding a new first-party Activity or materially redesigning gameplay, load these seven companions:

- `DESIGN_AND_TEACHING.md` — parent-request decomposition, gameplay and learning design;
- `PRE_READER_UX.md` — operation without reading and spoken-command requirements;
- `DISCOVERY.md` — mandatory minimum age, difficulty and Collection/discovery metadata;
- `FEEDBACK_ORCHESTRATION.md` — audio/event conflicts, shared reactions and terminal transitions;
- `ACHIEVEMENTS.md` — local score/progress/events versus Greia-owned rewards;
- `ENGINEERING.md` — clean architecture, runtime rules and performance;
- `SIMULATOR_WORKFLOW.md` — repeated headless integration and final GUI review.

Where a companion and this file disagree on frame rate, frame loop, audio or blit rules, §11 of this file reflects the current platform source. Do not load every specialist companion merely because it exists.

## 3. First action: decompose the parent's request

If several Activities are requested, plan the set before coding. Decide whether the request is best represented as several distinct Activities, one Activity with progressive stages, or one coherent Activity with multiple modes. Prefer separate Activities when the child fantasy, primary learning goal or core interaction is materially different.

For multiple Activities, first make a compact matrix:

```text
Activity | child fantasy | learning/development goal | core mechanic | presenter | age/challenge | why distinct
```

Avoid producing several copies of the same quiz with different nouns/art. Infer ordinary design details from the request and Greia's existing product language. Ask only when a missing choice genuinely changes product direction.

## 4. No code before the child loop is clear

Every Activity gets the compact brief in `DESIGN_AND_TEACHING.md` first. At minimum know:

```text
what world/fantasy the child enters
what the child repeatedly does
what the child learns/practices/creates
what happens in the first five seconds
how a non-reader knows what to do
recommended_age_min and why it is defensible
how challenge/scaffolding changes
what keeps repetition varied
what success and mistakes look/sound like
which presenter/character is used
which commands require spoken language
which locales ship
how completion/progress works
what score/events exist, if any
what happens on the final item/final answer
which cue wins when speech/SFX/celebration collide
```

If these are vague, keep designing instead of writing infrastructure.

## 5. Design for children who cannot read instructions

Normal Greia operation must not depend on reading button labels, prose or instructions. Prefer:

```text
obvious scene composition
+ large child-sized targets (primary targets >=64x64 logical px, preferably larger)
+ pictures / shapes / numbers / icons
+ short visual demonstration or motion cue
+ spoken instruction when language is necessary
+ immediate visual/audio cause-and-effect
```

Text is secondary support. Even a reading/phonics Activity is not exempt: letters/words may be learning content, but the instruction for how to play must still be understandable to a pre-reader. Increase difficulty through the learning mechanic, never through precision clicking, tiny arrows or tightly packed choices.

### Required language commands are spoken

If exact language is needed to know what to do, it must be spoken ("Trova la lettera S.", "Metti tre mele nel cestino.", "Quale animale fa questo verso?"). Do not ship these as text-only commands.

Required speech is short, localized, semantically identified, repeatable when useful, produced through Greia's prerecorded voice system and human-reviewed before final acceptance.

## 6. Age metadata is part of design

Every first-party Activity must declare a defensible:

```toml
[education]
recommended_age_min = N
```

Choose the youngest ordinary child for whom the **actual shipped interaction** is appropriate considering concepts, language/reading assumptions, working-memory load and motor demands. Do not copy `difficulty` into age; difficulty and developmental suitability are independent. `recommended_age_max` is optional; open-ended creative/sensory/imaginative Activities should not receive fake upper limits. Parent restrictive age presets depend on truthful metadata; `DISCOVERY.md` owns the exact semantics.

## 7. Teaching happens through play

Do not put a worksheet on a cute background. Prefer mechanics where the educational idea is what the child actually does:

```text
count visible objects by touching/moving them
fit shapes into meaningful silhouettes
hear a phoneme and manipulate/choose its symbol
arrange a sequence and watch the consequence
build/experiment and see cause-and-effect
```

Useful default progression:

```text
tiny demonstration -> guided first attempt -> independent repetition
-> gentle variation -> slightly harder variation -> natural completion/continuation
```

Increase challenge through the learning mechanic, not through tiny targets, dense screens, reading requirements, punitive timers or confusing layout. Mistakes reorient and encourage, never shame or punish.

## 7A. Localization: the mandatory Greia API

Owner: `greia_platform.localization`. `activity_resources(package_root)` is the composition factory; `LocalizedResources.text(key, variables)` and `LocalizedResources.audio_path(key)` are the two Activity-facing lookups for ordinary text and prerecorded speech.

```python
from pathlib import Path
from greia_platform.localization import activity_resources

resources = activity_resources(Path(__file__).resolve().parent)
caption = resources.text("instruction.find_letter", {"letter": "A"})
voice_path = resources.audio_path("instruction.find_letter")
if voice_path is not None:
    audio_owner.play_voice_file(voice_path)  # the Activity's own sound method, not a platform API
```

Localization returns a string or a file path; it never plays audio.

**Text rules**

- Strings live in `locales/<locale>.json` under stable semantic IDs. Placeholders are `string.Template` style (`$letter`, not `{letter}`).
- `.text(key, variables=None)` is the only display lookup; there is no `.string()`. Never wrap lookups in `except Exception`: it hides a real localization defect and can silently force fallback copy in every locale. Review by tracing normal rendering through `.text` and the concrete locale JSON, not by counting keys.
- `.text` already applies the child letter-case policy (CAPITALS by default, ADR 0034). Package-local literal strings go through `greia_platform.child_text.display_text(...)`; never hand-capitalize.
- Resolve strings once at the composition root and hand the resolved strings to the renderer, which keys on stable semantic state IDs (Painting passes `status.saved`/`status.saving`/`status.error` once and caches the surfaces; Greenhouse stores semantic toolbar keys). No per-frame locale resolution, and never choose a UI language from process `LANG` inside a renderer.
- Missing-resource emergencies use a language-neutral visual symbol, never a fixed-language sentence (Word Forest feedback, `viaggio_delfino` completion). A missing required translation is still a release defect, not a reason to declare a language complete.
- Renderer tests constructed without resources use concept pictograms or neutral icons, not arbitrary fixed-language text.
- Lesson content is not UI text. Letters, phonemes, syllables, rhymes and target words are pedagogical data owned by the Activity's domain catalogue (e.g. `foresta_content.PHONICS_DATA`); never translate them as ordinary UI strings. Derive displays from the actually selected curriculum (Magic Syllables may show `MÉ` in French), not from an assumed Italian grid.
- Launch language comes from the Greia profile/device setting and the manifest; never build an Activity language selector.

**Speech and audio paths**

- New narration lives at `assets/audio/<locale>/<semantic-id>.wav` or `.ogg`; legacy English JSON cue paths are projected into the selected locale automatically; nonstandard legacy names use `audio_path(key, filename="existing-stem.wav")`.
- For a finite list of known IDs request each `resources.audio_path("cue.id")`. When migrating an existing sound manager that eagerly preloads legacy cue files, use `resources.speech_paths()` (`{stem: Path}` from `assets/audio/<locale>/` and `locales/<locale>/audio/`, selected language first, English for gaps); the Activity still decodes into Pygame Sounds (deferred, §11.4). Never add another per-Activity locale scanner or duplicate an audio map per language.
- Fallback for all speech, including literacy and phonics for now: selected locale, then its base for a regional locale (`es-MX → es`), then English, then silence. Text keys follow the same regional/base order before the package default. Keep a silent path: the Activity must stay fully playable without any clip.
- Shared cast lines: `shared_character_audio_path(project_root, speaker, cue_id, locale)` (shared character v0.2 library). Shared picture names: `shared_vocab_audio_path(project_root, noun_id, locale)` over `assets/audio/vocab/v1/<locale>/<noun_id>.wav` (+ `.receipt.json`), `noun_id` = the language-neutral last segment of the picture's semantic id. Never copy cast or noun clips into an Activity package (installed-disk budget); add missing approved nouns to the bank (clip, receipt, README provenance row); the bank ships with the rest of `assets/audio/**` and is read from `project_root`. Never reach shared audio through relative `../..` paths (installed-image safety).
- Spoken numbers 0..25: `shared_number_audio_path(project_root, n, locale)` over `assets/audio/numbers/v1/<locale>/<n>.wav` (same fallback; out-of-range returns `None`). Use it instead of new per-package `count_<n>` copies.
- Keep procedural SFX, speech channels, event ordering and caching in the Activity's sound owner.
- Wiring a recorded line: play it through the Activity's existing speech owner (its `SpeechQueue`, the speech channel's one-slot `Channel.queue` after the line playing, or only-when-quiet for light helper lines) or let it replace the generic shared reaction at that moment; never stack two voices, and never let a host line run into an open microphone. A language-neutral (`*`) package with locale bundles passes `supported_locales` to `activity_resources`. Map of every 2026-10-17 line to its call site: `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/VOICE_WIRING_2026-10-17.md`; `tests/test_voice_wiring_contract.py` guards it.
- A recorded clip behind a module allowlist (`SPOKEN_COUNTS`, `SPOKEN_SHAPES`, a `startswith` filter over `speech_paths()`, a `PACKAGE_CUES` tuple) is silently never played: extend the allowlist with the recording and test that it resolves in en/it/es/fr.
- All committed voice files are owner-reviewed and accepted: never regenerate them for perceived provenance problems. No anti-tamper or signing; user-edited files are permitted.

**Released languages and extension**

- The **currently released set** is `en`, `it`, `es`, `fr` (owner decision 2026-10-17). This is not a permanent four-language limit. `greia_platform.system_language` discovers selectable language manifests from `src/greia_platform/languages/<locale>/manifest.json`, supplying `SUPPORTED_SYSTEM_LANGUAGES` and `SUPPORTED_SYSTEM_LOCALES` to installer, Shell and Parent UI. Never build a second selector list.
- A built-in Activity declares its actual supported locales in `activity.toml` (or `["*"]` if truly language-neutral) and ships matching `locales/<locale>.json` with complete semantic keys and formatting placeholders. For the four currently released languages, maintain EN/IT/ES/FR parity. When another language is approved and manifests are released, extend the Activity's JSON/TOML/audio and source checks **without editing core Python language-selection code**. `PYTHONPATH=src python3 tools/scaffold_greia_language.py <locale>` creates an unadvertised translation draft; `tools/check_greia_language.py <locale> --staged` checks source readiness before promotion.
- New spoken cues require recorded, reviewed sound in each **claimed** locale, using `tools/greia_voice.py` and the selected VoxStage/VoxCPM2 + v0.3 master route (Dani/Momo/Tito v3 IDs; Lilli/Leo/Flash v2 identities). `pedagogical` pronunciation remains on the native/system path where supported. Integrate only accepted outputs with the existing `tools/integrate_reviewed_voices.py --layout mirror` flow. Never declare an audio map entry for a file not present or overwrite owner-approved takes.
- New-language guide/agent route: `docs/development/ADD_A_GREIA_LANGUAGE.md`, `skills/greia-language-expansion/SKILL.md`; locale/content separation is governed by ADR 0028. Four-language historical rollout evidence is under `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/`.
- Tests: `tests/test_language_manifests.py`, `tests/test_four_language_release_contract.py` (checks manifest-derived inventory and declared audio/text), `tests/test_staged_activity_translations.py`, `tests/test_four_language_activity_runtime_text.py`.

## 8. Greia already owns voice production

Normal Activity narration/instructions are **authoring-time prerecorded audio**. Canonical production entry point: `tools/greia_voice.py`. The child device does not run VoxCPM2/Chatterbox/Whisper or narration TTS, and Activity code/tooling must not create a parallel VoxStage/Chatterbox/MLX/Whisper/native-TTS/FFmpeg stack. New speech needs fresh human acceptance; until approved clips exist, request lines (current list: `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/VOICE_LINES_REQUESTED_2026-10-16.md`) and keep the Activity playable in silence.

Speech kinds are semantic:

```text
character_dialogue          presenter welcome, instruction, hint, narration, fact
shared_character_utterance  generic ready/praise/retry/progress/celebration from the shared resolver
pedagogical_speech          the exact sound is educational truth: letter/syllable/phonics/pronunciation
dani_system_speech          Dani's intentionally robotic presenter/logic speech
```

Do not classify all speech in an educational Activity as `pedagogical_speech`. When actual speech needs producing/replacing, load `VOICE_GENERATION.md` and `skills/greia-voice-production/SKILL.md`.

### Shared character speech

Shared v0.2 assets live at `assets/audio/characters/shared/v0.2/` (EN/IT: 180 reactions + 12 introductions accepted 2026-08-28; ES/FR: the same 30 cues × 3 takes per character + intros added 2026-10-17). Documented generic families include `ready.go`, `praise.general`, `celebrate.success`, `encourage.retry`, `encourage.progress`. Reuse them instead of generating duplicate generic praise when the resolver exposes the family. Do not assume a generic greeting family exists, and do not copy the shared WAV catalogue into Activities.

## 9. Resolve semantic feedback before playing sound

One child action can simultaneously mean: ordinary item collected, teaching target completed, score changed, milestone emitted, round finished, victory reached. These must not independently fire competing sounds.

Classic failure: collect final item → collect SFX starts → final-word speech starts → victory fanfare replaces it → character congratulations overlaps everything.

Resolve the state transition first, then deliberately choose `SEQUENCE`, `SUPPRESS`, `REPLACE`, `INTERRUPT` or `COALESCE`. The final item/answer/piece is normally a **terminal transition**, not an ordinary success plus another victory callback. Protect pedagogical/required speech, keep queues bounded, and emit completion/score/milestone facts once. A performance stall can turn into exactly this bug by delaying feedback until events collide. `FEEDBACK_ORCHESTRATION.md` owns the detailed rules.

## 10. Score, Stars, medals, achievements and event keys

Every Activity explicitly decides its progression relationship, even if the answer is `none`. Keep separate:

```text
local Activity score/progress          Activity-owned presentation/state
normalized completion/milestone facts  emitted by the Activity through Greia contracts
Greia Stars / medals / trophies        platform-owned policy and ledger
```

Activities report facts; they never grant or mutate global rewards. Do not add streaks, points or reward spam because games often have them. Event ids stay stable for achievements (e.g. `bridge.level_completed`) unless deliberately renamed.

**Idempotency keys are ≤64 bytes** (`max_idempotency_key_bytes` in `runtime/history-policy.toml`); a longer key is rejected and the event is lost (Shape Garden's 76-byte completion key was silently dropped; Pasticceria's cake key was also over the limit). `tests/test_activity_event_key_bounds.py` statically computes every key's worst case and must stay green: a key with a new interpolated expression needs a declared bound in its `BOUNDS` table. Prefer short ids over descriptive prose in keys. `ACHIEVEMENTS.md` owns the event/reward contract.

## 11. Technical implementation standard

For first-party Python Activities:

- keep `main.py` a thin bootstrap/composition root;
- use cohesive modules/classes around real responsibilities; composition over deep inheritance; polymorphism at genuine variation points (stdlib `abc` is allowed in the curated runtime; check the runtime policy before relying on any other new import);
- reuse Greia platform services/primitives rather than cloning them;
- preserve both Greia script-launch and repository/package import contexts;
- use Greia storage/events/progression/permissions rather than private substitutes;
- keep Activity code display/input-backend neutral, and never draw or own the real Home/Back system controls;
- do not set or override SDL environment variables, import `pkg_resources`/`setuptools`, or write bytecode into the Activity folder (the platform supplies a read-only precompiled prefix; validation rejects cached bytecode).

Load `ENGINEERING.md` before implementation.

### 11.0 Storage and shared child creations

**Storage sizing:** the per-Activity namespace is adaptive (25% of the writable profile-data filesystem, the old byte quota only as a minimum/fallback), and the platform `VolumeBudget` caps aggregate variable child-data growth at 75% used plus 512 MiB free. Per-file/KV/media bounds still apply. Never implement your own disk-usage policy or bypass the trusted storage broker.

**Creations:** the platform-owned PNG/WAV/UTF-8 `CreationLibrary` has a guarded transfer API (`get_creations`) and manifest `creations.produces`/`creations.consumes` declarations. The universal `CreationsGalleryScreen` and the nonblocking `request_selection(...)` / `poll_selection(...)` / `cancel_selection(...)` protocol connect to a trusted modal host (SOURCE-WIP; Legacy-X and Simulator implement the same Shell modal contract). An Activity cannot enumerate/delete the profile library or mint its own handle. **Never** read another Activity namespace, mount a shared directory, build an Activity-local chooser, or block a frame loop waiting for human input. Painting is the reference PNG integration (private autosaves; up-arrow publishes an immutable snapshot; down-arrow requests `image/png`, polls at a bounded cadence and imports the one-use handle as a new private painting after digest/type validation; not yet accepted in a complete checkout/GUI; new consumers copy the pattern only after that consolidated acceptance is green). Shape Garden is a persistent composition studio with a 24-garden gallery and a PNG share/backdrop-import round trip. Tracking: the Creations PLAN/PROGRESS under `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/`.

### 11.1 Shared control kit and layout (ADR 0037, Accepted)

Do not hand-draw buttons, mode tabs, HUD counters, prompt bubbles, try-again banners or completion cards. Compose them from `greia_platform.activity_controls` (+ `activity_feedback`, `activity_keyboard_hint`, `pygame_completion`): one look, bounded cached rendering and keyboard / D-pad / stick / south-button focus for free. References: `activities/casa_del_dieci/ten_house_controls.py` (icon-only listen + check pills, `CastFeedback`, completion scene), `activities/pasticceria_magica/pasticceria_controls.py` (pantry, counted badges, bell), `activities/painting/` and `activities/writing/` (galleries/toolbars), `activities/quattro_amici/` (keyboard hint), `activities/morbidi_mostriciattoli/monster_layout.py` (drawers beside the tray). The sample shows API shape only; Activities are word-free, so prefer icon-only pills (`kit.glyph(...)`) and picture prompts over labels such as "OK".

```python
from greia_platform.activity_controls import (
    BodyShape, ButtonRole, ControlKit, ControlLayout, ControlTheme, ExternalTarget, PygameControlInput,
)
from greia_platform.activity_feedback import CastFeedback
from greia_platform.activity_keyboard_hint import KeyboardHint, KeyCap
from greia_platform.ui_core import SurfaceNavigator, UiEventResult

kit = ControlKit(typography, ControlTheme.for_accent("orange"))      # primary Collection hue token
layout = ControlLayout.for_canvas(canvas, screen.get_size())          # protected Home/Back mapped to logical px
tabs = kit.tool_strip("mode", [("a", res.text("tab.a"), kit.text_icon("🧁", 30)), ...], on_select=switch_mode)
stars = kit.hud_chip("hud.stars", rect, icon=kit.star(40), value=0)
ok = kit.pill_button("ok", rect, label="OK", icon=kit.glyph("check", 40), role=ButtonRole.PRIMARY, on_activate=confirm)
prompt = kit.prompt_banner("prompt", rect, text=res.text("prompt.x"), replay_icon=kit.glyph("listen", 34), on_replay=replay_cue)
cells = [ExternalTarget(f"cell.{i}", r, lambda i=i: tap_cell(i)) for i, r in enumerate(CELL_RECTS)]  # your art, kit focus ring
keys = {KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE}
cluster = layout.cluster([(132, 132), (132, 132)], hint_size=KeyboardHint.preferred_size(keys))
hint = kit.keyboard_hint("keys", cluster.hint, active=keys)             # display-only, never hit/focused
layer = kit.layer([*cells, *tabs.controls, stars, ok, *prompt.controls, hint])
surfaces = SurfaceNavigator(layer)
kit_input = PygameControlInput(to_logical=canvas.pointer, is_safe=safe_point)
cast = CastFeedback("dani", height=170, art=kit.art)                  # cast.correct() / cast.try_again()

# loop: result = surfaces.dispatch(kit_input.translate(event)) when not None; repeat = kit_input.poll() per frame;
# IGNORED pointer input is gameplay. Draw: scene -> cast.draw(surface, midbottom) -> surfaces.draw(surface).
```

- **One layout, every screen.** `ControlLayout` maps the protected Home/Back region (top-left, ADR 0019) into logical space; `top_bar(control_height(64, maximum=...))`, `bottom_bar`, `row(...)`, `fit(...)` (labels shrink first, then pills go icon-only) and `clear_of_chrome` make the same authored layout hold at 1024×600, 800×480, 480×320 and 1280×800 (ADR 0026). Never hard-code per-device coordinates; never place controls in `layout.protected`, and never imitate Home/Back. Check headless captures at 1024×600 and 800×480.
- **The platform owns the window size.** A Greia session normalizes your `set_mode` request to the real Shell surface (1280×800, 800×480, ...) and keeps your flags; the Simulator uses its synthetic viewport. `screen.get_size()` is therefore not guaranteed to be the 1024×600 reference. Do not size your content from `REFERENCE_WIDTH/HEIGHT` or open a smaller window over the Shell: use `PygameReferenceCanvas`/`ChildUiMetrics` for layout and pointer mapping. Outside a Greia session (tests, headless captures) the requested size is left untouched.
- **Opt-in high-resolution rendering.** `PygameReferenceCanvas(..., hires=True)` makes surfaces physical-pixel (logical API) on displays at least 1.2x the reference, so drawn shapes and text stay sharp (design doc §9.3; `GREIA_ACTIVITY_HIRES=0` disables). Create surfaces after the canvas; do not cache `pygame.Surface`/`pygame.draw.*` in module globals; do not rely on `subsurface` pixel sharing for canvas-made surfaces. Pilots: `alfabeto_leo`, `memory_meraviglie`.
- **The canvas owns the letterbox bands.** On non-1024×600 displays `PygameReferenceCanvas.present()` repaints the CONTAIN bands every full frame with one solid colour (darkened scene-edge average, or your `clear` colour), resamples non-integer scales smoothly, and `present_pointer`/`present_regions` repair from its cached physical frame at any scale. Never draw into the bands yourself or rely on them keeping pixels between frames (design doc §9.2).
- **Sizes.** `control_height` and `cluster` raise every control to the ≥40 px physical touch floor (`ControlLayout.MIN_TOUCH_PHYSICAL`); primary game actions are larger (colline's pedals are 132 px). Keep keycaps legible (colline's hint keeps ≥28 px keys on screen at every size).
- **Mouse-first placement (ADR 0037 §4a; `ACTIVITY_INPUT_STANDARDS.md` § Mouse-first control placement).** Greia is driven by one mouse/touchpad pointer: controls used together or in alternation (go + brake, left + right, jump + act) form one compact `layout.cluster(sizes, anchor=..., shape=ROW|CROSS, hint_size=...)` bottom-right or bottom-centre, at most 1–2 button widths apart, never covering what the child steers. Split-screen two-thumb layouts are not used. Only previous/next paging arrows may flank the content they move. Unrelated families (tool strip vs save/share vs top status bar) keep their own places. Audit and examples: `docs/reviews/activities/2026-10-16_CONTROL_PLACEMENT_AUDIT.md`.
- **Keyboard hint (ADR 0037 §4b; `ACTIVITY_INPUT_STANDARDS.md` § Keyboard affordance).** Required for `directional`/`game` profiles and `hybrid` play that acts directly on arrows/Space (not for plain focus navigation; letter-key play and Writing are exempt). `KeyboardHint` draws the acting keys from `ui.keycap.*` art (inverted-T arrows with non-acting arrows dimmed, Space, Enter only where it has its own meaning). Call `show(8.0)` at start, `demonstrate()` on idle-hint steps, `observe_event(event)` for every event (True → redraw), `update()` once per loop (True → redraw) and `frames.wake_at(hint.deadline())`. It is display-only, language-neutral and never covers gameplay or chrome. Over a moving scene draw it inside the cached `HudOverlay` and include its look in the overlay key.
- **Labels** come from `LocalizedResources.text` (CAPITALS per ADR 0034); Spanish/French labels run longer, so let `fit` shrink them and check captures rather than sizing to the Italian string. HUD/system glyphs: `kit.glyph("listen" | "replay" | "check" | "trophy" | "bell" | "clear")`; stars: `kit.star(size, filled=...)`.
- **Completion:** `PygameCompletionScreen(typography, scene=CompletionScene(kit, character="dani", star_total=N))`, then `surfaces.push_overlay(CompletionOverlay(completion, on_primary=restart, on_secondary=next_or_None))`; add `secondary_label` to `CompletionContent` for a "next" button. The scene supports one cast member.
- **State changes only on model change.** Mutate `label`, `value`, `visible`, `enabled`, `selected` only when the model changes; the kit caches every state/content surface in bounded LRU caches, so `draw` is blits only.
- **Pointer and input parity.** `PygameReferenceCanvas.present()` draws the platform pointer (`pointer=True` default); never draw your own cursor. A `hybrid` profile still provides keyboard and controller paths for every action (kit focus covers kit controls; custom hit targets need `ExternalTarget`). Ordinary Activities never open raw input devices (ADR 0020).

### 11.2 Shared art library and Shell theme folders

- **Library first.** Reuse scenes, props, creatures, HUD glyphs, keycaps, FX and cast poses by semantic ID from `assets/catalog/shared_visuals_v1.toml` (`bg.<biome>.<layer>`, `prop.<family>.<name>` incl. 100+ `prop.vocab.*` nouns, `creature.<role>.<name>`, `icon.hud.*`, `ui.keycap.*`, `fx.*`, `character.<id>` variants such as `pose_cheer`/`pose_point`/`pose_think`). Search with `python3 tools/visual_authoring_library.py search <need>`; consume through the catalogue and the bounded PNG cache, never by scanning folders. Inventory and registration rules: `assets/visual/README.md` and `skills/greia-visual-authoring/SKILL.md`.
- **Canonical cast only.** Never redraw a cast member inside an Activity or in Activity code; no off-model variants; no emoji as content.
- **New art only for a demonstrated gap.** Every new or redrawn SVG is authored with **Opus** following `docs/design/GREIA_SVG_AUTHORING_RULES.md` (lint grep §9, budgets §11), rendered with `rsvg-convert` (≥2.40) at 256/64/48 into a scratch folder and inspected at 1:1. Shared art: register it in `assets/catalog/shared_visuals_v1_source.toml`, run `make visual-assets` and `make visual-assets-check`, commit SVG, PNG and both catalogues. Activity-private art: keep it small, commit `assets/source/*.svg` beside the rendered PNG, and list it as a promotion candidate (P7 §8 in `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P7_ACTIVITY_QUALITY_PROGRAM.md`). Runtime never rasterizes SVG.
- **Prepare art for blitting once:** scale to final size at load, then `prepare_static` / `PreparedSurfaces` (§11.7). Never scale or decode on a frame path.
- **Curated wallpapers:** `greia_platform.activity_api.set_curated_wallpaper(asset_id)` (requires `customization.manage`; `bg.wallpaper.*` only, never a caller path). USB wallpaper import belongs to a trusted Parent/system workflow.
- **Theme folders:** one Activity is one experience; the Shell groups related Activities. Add a theme to the manifest's `discovery_tags` (e.g. `["sea", "nature"]`). A theme becomes a one-level Shell folder only if listed in `FOLDER_THEME_IDS` (`src/greia_launcher/catalogue_view.py`, currently `sea`) with at least 3 visible members after Parent/age filtering; a new folder theme is a platform change (icon + constant + test). Never build multi-game hubs inside one Activity.

### 11.3 Play patterns shared by all Activities

Copy these conventions rather than inventing variants (programme record: P7 plan above).

- **One Activity = one core experience.** Levels/stages of one loop are fine; no multi-game hubs or tab piles.
- **One feedback grammar through `CastFeedback`.** Correct: `pose_cheer` + FX + a short approved line. Try again: `pose_think` + a *demonstration* (never a bare "wrong"), unlimited kind retry. Finish: the shared cast completion scene (1–3 stars).
- **Graduated hints with bounded back-off (`IdleHintScheduler`, ADR 0037 §6b).** Never write your own "every N seconds" loop. Own one `IdleHintScheduler`, `reset(now)` it on every child input and new round, and in `step()` call `step = hints.poll(now, since)` (or `is_due` + `fire` when the hint may find no valid target): hint 1 after 6 s idle, hint 2 a further 12 s, hint 3 a further 24 s, then silence until the next input. Pick graduated content from the step (cast `pose_point` + pulse on the next valid target → demonstrate one step → glow the right target). Wrap every hint animation length in `hints.animation_seconds(x)` (capped at 1.5 s on the reference floor). A hint never shows the answer as text, a number or a pre-marked slot.
- **Never answer-revealing UI.** No printed sums, lit target counters, auto-focused right choice, per-slot answer icons or pre-GO right/wrong marks. Options that are sometimes right are never offered as wrong; distractors are near-misses (±1/±2, look-alike, contrast).
- **Finite, kind rounds:** spoken goal, act, celebrate, progress dots, a real ending in 1–3 minutes; adaptive stages saved per profile; nothing fails or loses progress; old saves migrate forward (schema bump, never silent reset). A round that runs without the child (rain, a demonstration) ends within ~20 s, which still leaves room for the 6 s and 18 s hints (foresta's 40 s rain held 33% CPU and grew RSS 109 → 114 MB).
- **Holding is playing.** Idle timers (hints, rest, unattended rounds) reset while a steering key, D-pad or button is held, not only on key-down; otherwise a child holding an arrow gets nudged and the scene parks under them.
- **End in stillness.** After a finish, celebration or completion overlay the scene must settle to a still frame: stop simulations and auto-motion, stop declaring `animating` (§11.6).
- **Child-work custody:** every saved item is reachable (paged big-card gallery); delete is deliberate (preview, Back/keep is the default, never hover or a single stray tap); a full shelf shows a sheet or refuses a new item, never evicts silently; no blank or duplicate saves; drafts survive Home; sharing publishes immutable PNG/WAV/UTF-8 snapshots through the platform API; gallery actions target the *focused* item (selection follows kit focus; see the `552011a1` regression).
- **Evidence honesty:** SOURCE + headless desktop review is not Acer evidence; requested voice lines are not recorded lines.

### 11.4 Start-up and audio

Before the first frame, Atom launch time was dominated by pure-Python sound synthesis (2–7 s per Activity) and speech-clip loading. Current games reach READY in 6.4–8.5 s through the Shell (third sweep median 7.4 s); the Shell's hard ready timeout is 15 s, so treat ~7 s as the target and anything over ~10 s as a defect (`viaggio_delfino` at 13.8 s is the known outlier).

- **Declare sounds, do not synthesize them at start-up.** Put synthesized cues and speech clips in a `greia_platform.pygame_audio.DeferredSoundBank`: `bank.define(name, factory)` with a zero-argument factory (`sfx.define("correct", lambda: self._tone(880.0, 0.14, 0.20))`; `speech.define(cue_id, lambda path=path: pygame.mixer.Sound(str(path)))`). `bank.get(name)` returns `None` for a missing or failed cue (fail-soft). One daemon worker builds the rest after READY; a cue needed sooner is built on first use, never twice, with identical output. A sound whose synthesis consumes the shared random sequence must keep its order (`colline_allegre`, `orchestra_animali` build those particular voices eagerly inside the bank); nothing else is eager.
- **Background synthesis is paced; keep it short anyway.** Pure-Python synthesis holds the GIL: unpaced, the warm-up worker made every `sleep`/`flip`/blit in the loop wait for the next forced switch, and colline_allegre (7 cues, ~10 s of synthesis) dropped from 129 to 91–95 frames in its first 6 s with 20–23 loop gaps over 100 ms. The bank's `SynthesisPacer` (4 ms work / 4 ms rest at every 128th `append_mono_pcm16`, 1 ms switch interval, no rests for a cue the Activity is waiting for) brings that to 109–125 frames and 3–6 gaps, at the price of a ~17 s warm-up. So keep cues short and cheap: compute samples into a list (comprehension) and pack them with `mono_pcm16_bytes(samples, channels, scale=volume)` (identical bytes, ~2× faster packing than per-sample appends at ~5–6 µs each); prefer short tails and few partials, since a 4.6 s fanfare asked for before the worker reached it is built on the loop thread. A factory that never calls `append_mono_pcm16` gets only the cue-boundary yields (every Activity now packs with `mono_pcm16_bytes`, so keep each cue short). For the maths use C-level iteration: a partial `gain*sin(2*pi*f*t)*exp(-d*t)` is `Im(z0*r**k)` with `r = cmath.exp(complex(-d, 2*pi*f)/rate)`, i.e. `[z.imag for z in accumulate(repeat(r, n-1), operator.mul, initial=z0)]`; sum partials with `map(operator.add, ...)`; a frequency sweep is `accumulate` over the per-sample phase increments then `map(math.sin, phases)`. `colline_allegre` cues are bit-identical to the per-sample loops (fanfare 0.074 → 0.022 s on the Mac); the cue-per-sample `sin`/`exp` calls were the cost, not the packing (§11.4).
- **Voice clips too.** Decoding speech (`pygame.mixer.Sound(path)`) belongs in a bank or after the first frame, not in `__init__` (`viaggio_delfino`); a clip requested earlier is decoded on demand.
- **Picker thumbnails share scene parts.** Several looks of one scene (delfino's postcards) reuse identical layers while thumbnails are baked instead of composing each from scratch.
- **READY means a presented frame.** Call `mark_activity_ready()` (`greia_platform.activity_api`) once, immediately after the first `display.flip()`/`canvas.present()`; it releases deferred work (`greia_platform.first_frame_work`). Start no background work earlier. Other work the first screen does not need registers with `after_first_frame(self._method)` (bound method, weak reference; runs at READY or immediately if already READY) and gets its own bound and owner.
- **Bake static scenes once** (as `viaggio_delfino` bakes its bay scene) instead of composing them in the first frame; do not make terminal/completion the first time a font or large surface is created.
- **The platform owns the audio device.** `greia_platform.python_activity_entry` installs `greia_platform.activity_mixer_lease` before your code runs, so `pygame.mixer.Sound` / `pygame.mixer.Channel` are lease-aware. An open SDL mixer alone costs ~5% CPU on the Atom, so the mixer closes once the child is idle (no input for 30 s, no `animating` motion) and nothing has played for 10 s; it never closes while the child plays (closing mid-play caused 220–340 ms freezes). When the child returns, the frame governor reopens it off the loop thread right after the answering frame (same format, channels, reservations, volumes); a sound that comes first reopens it itself. While closed, `get_init()` still reports the format and `get_busy`/`stop`/`get_length` answer without reopening.
- **Therefore:** create Sounds/Channels only through `pygame.mixer` — never ctypes/SDL or `pygame._sdl2` playback, because `Sound.play`/`Channel.play` on a closed mixer **segfaults** pygame 2.1.2; never `quit()`/re-`init()` the mixer yourself; prefer one-shot `Sound`/`Channel` playback over `pygame.mixer.music` and channel end-events (either keeps the device open for the whole visit). A capture device (`pygame._sdl2.audio`, microphone) keeps the mixer open while it is open. The lease needs a `FrameGovernor` loop (`events()`/`note_input()`), which every Activity has anyway.
- **No black window at launch, and the platform owns the size.** `greia_platform.python_activity_entry` installs the display policy (`greia_platform.activity_display`), which replaces your requested `set_mode` size with the exact Shell viewport and keeps your flags, then wraps the first window with the launch cover: hidden, shown, the Shell's launch card (or the theme colour), the cover's wrapper removed, the card removed. Your first `flip` replaces it; READY is still yours to signal after that flip. The display policy stays installed, so a later re-mode also fills the session. Do not assume `screen.get_size() == (1024, 600)`; see the "platform owns the window size" bullet above. Keep start-up light anyway: the child still waits, just on the launch card instead of black.
- **SDL environment is the platform's.** The runtime adapter sets `SDL_FRAMEBUFFER_ACCELERATION=0` (`greia_launcher.runtime_adapter`): window creation 0.03–0.15 s instead of 0.7–1.2 s and ~70 MB less RSS per process.
- Validate with `tests/test_launch_startup_performance.py`; Acer claims follow the sweep method in `docs/reviews/acer/2026-10-16_ACER_ACTIVITY_SWEEP.md`.

### 11.4A Package size guideline

Per-Activity size: **64 MiB guideline** (`maximum_activity_bytes`, `runtime/child-runtime.toml`); `@2x` art counts normally. Larger Activities are allowed with a build-time warning (`tools/validate_activity.py` and registry logging) and an install-time size notice (`large_activity` / `size_notice` in the install receipt) - owner decision 2026-10-21. Every other footprint/safety rule stays fail-closed.

### 11.5 Performance is correctness

The Acer-class floor (Atom N270, 2 logical CPUs, 1 GB RAM, no swap, 1024×600) is a design target, not a later optimization pass. Never on a frame path:

```text
filesystem scans / storage or config reads     asset decoding/loading
image scaling, smoothscale, rotate, transforms  font construction, text rendering
per-sprite set_alpha / per-frame alpha surfaces gradients or procedural fills
subprocess/device discovery                     large allocation churn
unbounded audio/event queues/histories          full-screen work that never settles
```

Prefer preloaded immutable assets, bounded caches/queues (size them for 768 MiB–1 GB RAM), event-driven/invalidation rendering and cheap static states. RSS must stay flat while the child is idle (a live round in foresta crept 109 → 114 MB in 60 s). Pre-render text once per value, pre-rotate sprite frames in angle steps, pre-render gradients into strips.

### 11.6 Frame governance (ADR 0037 §6a, mandatory)

Never flip unchanged frames and never use a bare `Clock.tick` loop. Every loop uses `greia_platform.frame_governor`:

```python
from greia_platform.frame_governor import FrameGovernor, FrameKind

frames = FrameGovernor()                       # policy from GREIA_FRAME_PROFILE / CPU count
while running and not activity_stop_requested():
    for event in frames.events():              # drains pygame.event.get(), notes input/pointer motion
        handle(event)                          # state change -> self._dirty = True
    animating = self.step()                    # True only while something essential moves
    frame = frames.frame(dirty=self._dirty, animating=animating, ambient=idle_motion)
    if frame is FrameKind.FULL:
        self.render(); self.canvas.present(); pygame.display.flip(); self._dirty = False
        # first FULL frame -> mark_activity_ready()
    elif frame is FrameKind.POINTER:
        self.canvas.present_pointer()          # only Greia's pointer moved: no scene re-render
    frames.wait(polling=self._input.repeating) # replaces Clock.tick
```

- **Mark dirty** for every visible state change: input handled, timer/timeline fired, `cast.update()` returned True, `layer.invalidation.should_draw`, a keyboard hint `update()`/`observe_event()` returning True, a time-based visual state flip (caret blink). `frames.invalidate()` does the same without a dirty flag; `frames.wake_at(deadline)` bounds the idle block for a timer that must fire on time.
- **`animating=True`** only for essential motion (feedback, a steered character, physics after GO); `frames.animate_for(seconds)` requests a fixed window. Essential motion is never frozen and caps at 24 fps on the floor.
- **`ambient=True`** for decorative idle motion (bubbles, clouds, breathing cast, sparkles, bobbing marks, band sway): full rate after input, then 12 fps on `standard` (after 8 s idle) and **frozen (0 fps) on the reference floor** after 6 s idle (`FramePolicy.reference_floor()`), resuming instantly on input. The floor profile is selected automatically on ≤2 logical CPUs or by `GREIA_FRAME_PROFILE=reference-floor`; never branch on it yourself. Misclassifying decoration as `animating` or a perpetual `dirty` keeps the Atom above 100% CPU (`clinica_cuccioli`'s bobbing marks held 24 fps forever). Loops that pace decoration themselves or simulate purely decorative actors gate that on `not frames.ambient_frozen`.
- **Settle.** A static screen blocks for input (≤250 ms; SDL wakes within ~1 ms of an X event), so idle CPU is near zero only if nothing keeps declaring motion. When the child stops, gameplay that is not being steered must come to rest and must not drive itself to a finish; auto-motion that continues without input (volo's auto-flight: 90% CPU idle) or a post-finish scene that keeps animating (colline: 51% CPU with the mixer held open) is a defect. Patterns: colline parks the buggy (velocity damping 0.985 per step, ~0.4 s half-life, once no pedal for 3 s, then `animating=False` after 0.5 s still); volo/delfino slow to a resting pose 20 s after the last input, i.e. after both idle hints; any steer, tap or pointer move resumes.
- **Fixed-step simulations** keep their step with `frames.wait(polling=True)` and present only when `frame()` says so; `polling=True` also keeps held-stick repeats on cadence. Pacing is deadline-based (oversleep is repaid), so work that fits in a frame reaches the cap; never add sleeps or `Clock.tick`.
- **Pointer without redraw.** Never mark the whole frame dirty on plain pointer motion: Greia's pointer is a `POINTER` frame; hover changes come from kit invalidation (`workshop_settings` once repainted ~220 ms per move on the Atom). Activities drawing straight to the display (Writing, Painting) keep the pointer in a `PygamePointerSprite` (`greia_platform.pygame_canvas`, save-under): `POINTER` frames call `sprite.refresh(screen)`; a painting stroke pushes only its dirty rectangle (`erase` → blit region → `refresh(extra=(region,))`).
- **Dirty rectangles** for small moving sprites over a cached background: ask the renderer for the sprites' logical rects, `plan = canvas.plan_regions(previous + current)`; if `plan` is not None, `canvas.render_regions(plan, self.render)` + `canvas.present_regions(plan)`, else a full frame. Force a full frame on any non-motion input, model event, timeline action or kit invalidation, and cover it with a test comparing the dirty-rect surface to a full render (`corsa_bacche`, `foresta_parole`).
- **Never re-render a still screen on a timer.** A full 1024×600 render costs 150–220 ms on the Atom and input arriving meanwhile waits for it. `keepalive_seconds` is a migration aid only (it pauses on the floor once the child is idle).
- Desktop proxy: `PYTHONDONTWRITEBYTECODE=1 python3 tools/measure_activity_idle_cpu.py --settle 15 <activity>` (add `GREIA_FRAME_PROFILE=reference-floor`); a static screen shows ~0 presents/s. Absolute CPU differs from the Atom by about an order of magnitude; the ratio is what it shows.

### 11.7 Blit cost: RLE every per-frame alpha surface (`greia_platform.pygame_blit`)

Measured on the Acer (pygame 2.1.2 / SDL 2.26.5, 32-bit X11) onto the 1024×600 canvas: opaque display-format blit ~2 ms; **per-pixel-alpha blit ~134 ms (~0.22 µs/pixel, even for fully opaque or transparent pixels)**; the same surface RLE-encoded ~1.5 ms, identical within 1/255. That one path made colline_allegre (4 fps) and viaggio_delfino (4.3 fps) unplayable. After preparing surfaces, every motion game needs ≤40 ms of work per frame and runs at the 24 fps floor cap (colline 4.0 → 21.7 → 23.6 fps, frame work 252 → 22 ms; labirinto and corsa 24.0 fps with 9.6 ms work after the kit was prepared too).

- **Every alpha surface blitted per frame** goes through `prepare_static(surface)` once it is final (display format + `RLEACCEL`; the source is not modified). Renderers that blit loader/kit-owned surfaces keep one `PreparedSurfaces()` and blit `fast(image)` (bounded, identity-keyed RLE copies; only for surfaces nobody draws on afterwards).
- **No per-frame `set_alpha`** on sprites: it forces the slow path and drops RLE. Use `FadeSteps(surface).at(fraction)` or `fast.faded(image, fraction)` (a few baked levels).
- **Never `set_alpha(None)` on a per-pixel-alpha surface:** it disables alpha blending for later blits and transparent pixels draw solid. Reset with `set_alpha(255)`.
- **Opaque targets only.** RLE alpha blits write opaque destination alpha, so translucent pixels turn opaque on a `SRCALPHA` target (an overlay or composite you are building): blit the plain source there. `fast.for_target(image, target)` and `kit.painter.presentable(surface, target)` choose for you; a bare `fast(image)` does not.
- **Kit controls are already prepared:** `ControlLayer.draw` / `KitControl.draw` / focus rings blit cached RLE copies onto opaque targets (kit layer <1 ms instead of 6–10 ms per frame). If you blit a painter/kit product yourself every frame (`painter.body(...)`, `painter.label(...)`, `kit.art.image(...)`), blit `kit.painter.presentable(surface, canvas)`.
- **Cast poses:** `CastFeedback.draw` blits an RLE copy per pose onto opaque targets (96 px 2.1 → 0.1 ms, 220 px 10.6 → 0.4 ms per frame on the Acer). Poses you draw yourself (`pose_point`, `pose_wave`) go through `art.presentable(pose, target)` (`ControlArt`, bounded, keyed by asset/variant/size; plain pose on alpha targets).
- **Big one-off sprites** (a finish rainbow, a banner) are prepared when they are built: volo's 900 px rainbow cost ~90 ms a frame un-encoded.
- **HUD over a moving scene:** `HudOverlay().draw(canvas, key, layer_draw, stale=layer.invalidation.should_draw)` composes the kit layer once into a transparent RLE overlay and recomposes only on key change/invalidation/resize (`colline_allegre`, `baia_delle_orche`).
- **Display-format canvas.** The logical canvas stays in the display format (`PygameReferenceCanvas` default); a 24-bit or alpha canvas cost sottomarino ~25 ms a frame.
- **Static and scrolling scenes:** compose static backgrounds once and `convert()` them (opaque). Scrolling worlds pre-render terrain/parallax into strips once (colline `CollineArt.chunk`, delfino `ParallaxStrip`).
- Never draw on, `subsurface` or `smoothscale` from an RLE surface on a frame path (each lock decodes and re-encodes it); keep the plain source for composition and blit the prepared copy.

## 12. Project-specific tools stay with the project

Activity-specific authoring/generation/migration tooling belongs under `activities/<activity_dir>/tools/` (e.g. `generate_voice_requests.py`, `build_local_assets.py`, `migrate_content.py`). Rules:

1. place project-specific tools there from the start;
2. runtime code does not belong in `tools/`;
3. repository root `tools/` is only for genuinely Greia-wide tooling;
4. remove obsolete/one-shot tools and scratch output when work closes;
5. the Activity directory is also package input—do not ship development machinery accidentally;
6. promote a local tool to root only when it becomes a reusable Greia-wide facility with a stable contract.

## 13. Verify without hardware, throughout development

Do not wait for the Activity to be finished. Run the loop at: minimal valid skeleton; first meaningful child interaction; each major runtime/resource/refactor change; completion/restart/audio integration; and again after the final runtime edit.

```bash
export PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=src python3 tools/validate_activity.py activities/<activity_dir>
PYTHONPATH=src python3 -m unittest tests.test_activity_<activity_dir> tests.test_activity_event_key_bounds -v

# fast single-Activity capture (both reference sizes; one run pressing an acting key)
PYTHONPATH=src python3 tools/headless_greia_activity.py --activity-main activities/<activity_dir>/main.py \
  --locale it --viewport 1024x600 --screenshot-prefix /tmp/greia-<activity_dir>-1024
PYTHONPATH=src python3 tools/headless_greia_activity.py --activity-main activities/<activity_dir>/main.py \
  --locale en --viewport 800x480 --press-key right --screenshot-prefix /tmp/greia-<activity_dir>-800

# full-Shell integration (profile, catalogue, supervisor, trusted Home)
PYTHONPATH=src python3 tools/headless_greia_simulator.py \
  --activity-dir activities/<activity_dir> --workspace-dir /tmp/greia-sim-<activity_dir> \
  --locale it --viewport 1024x600 --survival-seconds 12 --screenshot-prefix /tmp/greia-<activity_dir>-it

# idle proxy: a still screen must show ~0 presents/s
GREIA_FRAME_PROFILE=reference-floor python3 tools/measure_activity_idle_cpu.py --settle 15 <activity_dir>
python3 tools/clean_bytecode.py
```

Use `--press-key` or `--click-x/--click-y` for meaningful interaction, test every shipped locale, and inspect the captures for chrome overlap, clipped labels at 800×480, the lit keycap and cluster placement. Keep evidence out of the repository. For Acer evidence use `docs/agents/GREIA_AGENT_OPERATIONS.md` §8 (`tools/dev_source_deploy.py deploy` of a committed `HEAD`, quote `/opt/greia-os/.deployed-sha`) and the measurement method in `docs/reviews/acer/2026-10-16_ACER_ACTIVITY_SWEEP.md`; remote `xdotool` injection is never physical-input evidence. `SIMULATOR_WORKFLOW.md` owns the detailed loop.

## 14. Final GUI Simulator review is mandatory

Headless integration cannot decide whether a toddler understands the first action, the game is fun/coherent, targets are large enough, the teaching mechanic works, presenter/audio timing feels right, final-item feedback collides, 1024×600 presentation is pleasant, or obvious performance stalls exist. After final headless integration launch:

```bash
python3 tools/greia_simulator.py --state-dir ~/.greia-simulator-review-<activity_dir>
```

Present that exact final state to the user/reviewer. If GUI review cannot be performed, the strongest honest result is `SOURCE-VERIFIED / HEADLESS-SIMULATOR-PASS / GUI-REVIEW-PENDING`. Any runtime-relevant edit after evidence requires rerunning the applicable final checks.

## 15. Load specialist companions only when relevant

```text
PRESENTERS_AND_CURIOSITY.md   presenter/factual-curiosity design
VOICE_GENERATION.md           actual speech production/replacement
MICROPHONE_RECORDING.md       child microphone recording
LAUNCHER_SPOKEN_LABELS.md     launcher title speech
TERMINAL_RENDERING.md         completion/Continue/Replay presentation
REFACTORING.md                substantive existing-Activity refactor
LAUNCH_ACCEPTANCE.md          detailed final launch/evidence procedure
```

Parent-installed package storage is owned by `greiapanel`; root-side software updates must preserve that owner and leave published Activities readable but not writable by the child. For the Linux permission regression and clean-image rerun, follow `docs/testing/2026-10-24_SOFTWARE_UPDATE_ACCEPTANCE.md`.

For visual asset creation/adaptation load `skills/greia-visual-authoring/SKILL.md`. For `.greiaactivity` packaging use `docs/architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md`, `src/greia_platform/activity_packages.py` and `src/greia_platform/activity_package_format.py`. To distribute a typed one/set/all Activity update, read `docs/development/GREIA_SOFTWARE_UPDATE_PACKAGES.md` and use `tools/greia_software_update.py`; keep built-in and Parent-source trust separate, and never package an Activity update as a Python filesystem destination. Combined packages now carry platform language manifest/UI JSON alongside Python; Activity translations remain inside the selected Activity archive. Old pre-manifest receivers need the guide's one-time source-matched bridge before a current combined package.

## 16. Definition of done

A new first-party Activity is not done until all applicable items are true:

```text
PARENT_REQUEST_DECOMPOSED=yes
ACTIVITY_SET_PLAN_COMPLETE=yes/not-applicable
CHILD_PLAY_LOOP_CLEAR=yes
LEARNING_OR_CREATIVE_PURPOSE_CLEAR=yes
RECOMMENDED_AGE_MIN_DEFINED=yes
DISCOVERY_METADATA_VALID=yes
FIRST_ACTION_CLEAR_WITHOUT_READING=yes
REQUIRED_SPOKEN_COMMANDS_COMPLETE=yes/not-applicable
VOICE_KIND_SEMANTICS_CORRECT=yes/not-applicable
HUMAN_AUDIO_REVIEW_COMPLETE=yes/not-applicable
FINAL_ACTION_FEEDBACK_CONFLICT_RESOLVED=yes
PROGRESSION_REWARD_RELATIONSHIP_DEFINED=yes
EVENT_KEYS_WITHIN_64_BYTES=yes
KIT_CONTROLS_AND_CLUSTER_PLACEMENT=yes
KEYBOARD_HINT_SHOWN=yes/not-applicable
SHARED_ART_REUSED_OR_GAP_LISTED=yes
CAPTURES_1024x600_AND_800x480_CLEAN=yes
FRAME_GOVERNED_AND_SETTLES_IDLE=yes
PER_FRAME_ALPHA_SURFACES_PREPARED=yes
PERFORMANCE_HOT_PATHS_BOUNDED=yes
NOTHING_HEAVY_BEFORE_FIRST_FRAME=yes
PROJECT_LOCAL_TOOLS_CLEAN=yes
FOCUSED_TESTS_PASS=yes
FINAL_HEADLESS_SIMULATOR_PASS=yes
GUI_SIMULATOR_USER_REVIEW=PASS
```

Physical/Acer evidence is additionally required for claims that depend on physical performance, hardware behavior or production display/input paths. Never upgrade source or Simulator evidence into a stronger evidence class that did not actually run.

## 17. Keeping this skill current

This file is the one-shot manual other agents rely on before any live test. Every Activity or platform tranche that discovers a performance, layout, graphics, input, audio or shared-asset lesson updates this file **in the same commit**, stating the rule and the measured reason (device, build, before → after). Fold the lesson into the section it belongs to and into §0 if it changes what a first attempt must do; do not append dated narrative sections, and delete any statement the change makes stale. When a rule's owner is an ADR, product requirement or platform module, update that owner too and keep this file pointing to it.
