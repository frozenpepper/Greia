---
name: greia-activity-authoring
description: Design and build one or more Greia Activities from a parent's request. Child/play/teaching design comes first, followed by clean implementation, prerecorded speech, repeated headless Simulator integration and final GUI user review.
---

# Greia Activity Authoring

**Status:** living Activity-authoring contract  
**Reviewed:** 2026-09-03

The normal entry point is simple:

> **A parent asks for one or more Activities.**

Act as a small Activity designer/producer, not merely a coder. Turn the request into coherent child experiences, plan the set, implement each Activity cleanly, and prove the final result through Greia.

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

Before coding a new first-party Activity or materially redesigning gameplay, load:

```text
DESIGN_AND_TEACHING.md
PRE_READER_UX.md
DISCOVERY.md
FEEDBACK_ORCHESTRATION.md
ACHIEVEMENTS.md
ENGINEERING.md
SIMULATOR_WORKFLOW.md
```

These seven companions are the normal creation core:

- `DESIGN_AND_TEACHING.md` — parent-request decomposition, gameplay and learning design;
- `PRE_READER_UX.md` — operation without reading and spoken-command requirements;
- `DISCOVERY.md` — mandatory minimum age, difficulty and Collection/discovery metadata;
- `FEEDBACK_ORCHESTRATION.md` — audio/event conflicts, shared reactions and terminal transitions;
- `ACHIEVEMENTS.md` — local score/progress/events versus Greia-owned rewards;
- `ENGINEERING.md` — clean architecture, runtime rules and performance;
- `SIMULATOR_WORKFLOW.md` — repeated headless integration and final GUI review.

Do not load every specialist companion merely because it exists.

## 3. First action: decompose the parent's request

If several Activities are requested, plan the set before coding.

Decide whether the request is best represented as:

- several distinct Activities;
- one Activity with progressive stages;
- or one coherent Activity with multiple modes.

Prefer separate Activities when the child fantasy, primary learning goal or core interaction is materially different.

For multiple Activities, first make a compact matrix:

```text
Activity | child fantasy | learning/development goal | core mechanic | presenter | age/challenge | why distinct
```

Avoid producing several copies of the same quiz with different nouns/art.

Infer ordinary design details from the request and Greia's existing product language. Ask only when a missing choice genuinely changes product direction.

## 4. No code before the child loop is clear

Every Activity gets the compact brief in `DESIGN_AND_TEACHING.md` first.

At minimum know:

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

Normal Greia operation must not depend on reading button labels, prose or instructions.

Prefer:

```text
obvious scene composition
+ large child-sized targets
+ pictures / shapes / numbers / icons
+ short visual demonstration or motion cue
+ spoken instruction when language is necessary
+ immediate visual/audio cause-and-effect
```

Text is secondary support.

Even a reading/phonics Activity is not exempt: letters/words may be learning content, but the instruction for how to play must still be understandable to a pre-reader.

### Required language commands are spoken

If exact language is needed to know what to do, it must be spoken.

Examples:

```text
“Trova la lettera S.”
“Metti tre mele nel cestino.”
“Quale animale fa questo verso?”
```

Do not ship these as text-only commands.

Required speech is short, localized, semantically identified, repeatable when useful, produced through Greia's prerecorded voice system and human-reviewed before final acceptance.

## 6. Age metadata is part of design

Every first-party Activity must declare a defensible:

```toml
[education]
recommended_age_min = N
```

Choose the youngest ordinary child for whom the **actual shipped interaction** is appropriate considering concepts, language/reading assumptions, working-memory load and motor demands.

Do not copy `difficulty` into age. Difficulty and developmental suitability are independent.

`recommended_age_max` is optional. Open-ended creative/sensory/imaginative Activities should not receive fake upper limits merely for symmetry.

Parent restrictive age presets depend on truthful metadata. See `DISCOVERY.md` for exact semantics, including unknown-age compatible packages and explicit Parent overrides.

## 7. Teaching happens through play

Do not put a worksheet on a cute background.

Prefer mechanics where the educational idea is what the child actually does:

```text
count visible objects by touching/moving them
fit shapes into meaningful silhouettes
hear a phoneme and manipulate/choose its symbol
arrange a sequence and watch the consequence
build/experiment and see cause-and-effect
```

Useful default progression:

```text
tiny demonstration
-> guided first attempt
-> independent repetition
-> gentle variation
-> slightly harder variation
-> natural completion/continuation
```

Increase challenge through the learning mechanic, not through tiny targets, dense screens, reading requirements, punitive timers or confusing layout.

Mistakes should reorient and encourage, not shame or punish.

### Four-language rollout (2026-10-12)

Current Greia OS selectable locales: **English and Italian**.
Spanish and French are translation/voice targets but not globally
selectable. The accepted cross-surface plan is
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PLAN.md`;
the exact local recording work order is the sibling
`LOCAL_AGENT_VOICE_PRODUCTION.md`. All built-in Activity semantic
UI/lesson-language separation, locale bundle keys, launcher titles,
caption/audio mappings and human-listened speech must pass before
ES/FR are promoted. Never mark a locale supported merely because
you copied `en.json` or created placeholder WAV paths. Preserve
current English/Italian recording assets and repair only identified
missing/incorrect cues.

### Source-staged Activity text (2026-10-13)

All 45 built-in Activity packages have staged
`locales/es.json` and `locales/fr.json` source text
bundles, now with **45/45 declared source-key parity**.
Word Forest (since the 2026-10 rework the "catch the
first letter of the spoken picture word" game, ages 5-7)
owns 21 Spanish and 21 French
letter-to-example-word lessons in its pure
`foresta_content.PHONICS_DATA` domain catalogue;
its 24 previously missing source `word.*`/
`phonics.*` strings are now authored per locale.
No ES/FR lessons are selectable until the
required real speech clips, exact prompt scripts
and pedagogical review pass. The source-only
voice ledger separately inventories 126 new
ES/FR phonics clips (letter, prompt and word).
Four other letter/rhyme/syllable Activities have
complete UI strings but still need
language-relative playable teaching rules
and approved pronunciation.
The Encyclopedia now has all 260 source text
keys in ES/FR but still needs its **200 source
narration cues/locale** reconciled with exact scripts
and newly recorded/listened translated voice.
Submarine has 77 text keys and 55 cue IDs/locale
and requires all new voice assets before promotion.
Number Train's live puzzle count is >=2;
the plural `prompt.load` string is dormant, not a
reproduced one-item runtime bug. Consult the roster
in `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PROGRESS.md`;
but no generated voice assets yet. **The manifests still correctly
advertise only en/it.** Do not add `es`/`fr` to a manifest or
fill `audio` mappings with nonexistent WAVs merely because
translated text exists. Resolve real missing/speaker-assigned
speech first via the central four-language local-agent voice
work order, then test UI, actual voice and profile language
inheritance before release. Test per-language semantic
interpolation with `tests/test_staged_activity_translations.py`.
Do not translate a lesson's target content language as if it
were ordinary UI text.

## 7A. Mandatory Greia localization API for new Activities

**Implemented shared owner (2026-10-15):** `greia_platform.localization`,
with `activity_resources(package_root)` as the composition factory and
`LocalizedResources.text(key, variables)` /
`LocalizedResources.audio_path(key)` as the two Activity-facing lookups.
This consolidates ordinary text and prerecorded speech across child languages.

```python
from pathlib import Path
from greia_platform.localization import activity_resources

resources = activity_resources(Path(__file__).resolve().parent)
caption = resources.text("instruction.find_letter", {"letter": "A"})
voice_path = resources.audio_path("instruction.find_letter")
if voice_path is not None:
    audio_owner.play_voice_file(voice_path)  # Activity's own sound method
```

The last line is an example of a game-owned playback method, **not**
a Greia-platform or guaranteed existing method name. Localization returns
a string or file path, never plays audio itself.

Strings live in `locales/<locale>.json` with stable semantic IDs.
New narration can live at
`assets/audio/<locale>/<semantic-id>.wav` or `.ogg`; legacy
English JSON cue paths are projected into the selected locale automatically.
For existing nonstandard legacy filenames, `audio_path(key,
filename="existing-stem.wav")` is available. Activity launch language
comes from the Greia profile/device setting and manifest, **not** an
Activity-maintained language selector.

For a game that has a finite list of known semantic IDs, request each
`resources.audio_path("cue.id")` directly. When migrating an **existing**
SoundManager which eagerly preloads many legacy physical cue filenames,
use `resources.speech_paths()`: it returns `{stem: Path}` for existing
WAV/OGG in `assets/audio/<locale>/` and
`locales/<locale>/audio/`, selected language first and English for gaps.
The Activity retains responsibility for decoding into Pygame Sound objects.
Do not add a third local language-path scanner merely to enumerate preloads.

Greia-owned shared character sounds (e.g. Leo/Flash praise) use
`shared_character_audio_path(project_root, speaker, cue_id, locale)`
from the same localization module. These canonical voices live in the
shared character v0.2 library, not each Activity; do not duplicate or
rerecord them in an Activity package.

**Shared vocabulary audio bank.** Spoken picture/noun names ("apple",
"mela") live once in `assets/audio/vocab/v1/<locale>/<noun_id>.wav`
(+ `.receipt.json`), resolved with
`shared_vocab_audio_path(project_root, noun_id, locale)`
(locale chain -> base -> English -> `None`, so keep a silent path).
`noun_id` is the language-neutral concept id (`apple`, `ice_cream`), the
last segment of the picture's semantic id. Use the bank for any
naming/matching game; **never copy noun clips into an Activity package**
(installed-disk budget). Add missing approved nouns to the bank (clip,
receipt, provenance row in its README), not to the Activity. The bank
ships in images with the rest of `assets/audio/**` and is read from
`project_root` exactly like the shared character library.

For all speech, **including literacy and phonics for now**, choose
selected-language file if present, then its base-language file for a
regional locale (`es-MX → es`, `fr-CA → fr`), otherwise English,
otherwise silence. Text keys follow the same regional/base ordering
before their existing last-resort package default.
Keep procedural sound effects, speech channels, event ordering and
caching in the Activity sound owner; do not write per-Activity locale
directory scanners or duplicate the same audio map four times.
All **already committed** voice files are owner-reviewed and accepted.
No anti-tamper system; user-edited files are permitted.

**Migration status:** the shared resolver, launcher Activity titles,
Measurement Workshop, Ten House, Magic Syllables, Alphabet Leo and Word
Forest have source adaptations. Other Activities may still use legacy
loaders and should migrate incrementally without replacing their
approved audio. Complete runtime/source tests separately; no ES/FR
selector promotion is implied. See
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md`.

## 8. Greia already owns voice production

Normal Activity narration/instructions are **authoring-time prerecorded audio**.

Canonical production entry point:

```text
tools/greia_voice.py
```

The child device does not run Chatterbox/Whisper or normal narration TTS.

Activity code and Activity-local tooling must not create a parallel Chatterbox/MLX/Whisper/native-TTS/FFmpeg routing stack.

Speech kinds are semantic:

```text
character_dialogue
    presenter welcome, instruction, hint, narration, fact

shared_character_utterance
    generic ready/praise/retry/progress/celebration when the shared resolver exposes it

pedagogical_speech
    the exact sound itself is educational truth: letter/syllable/phonics/pronunciation

dani_system_speech
    Dani's intentionally robotic presenter/logic speech
```

Do not classify all speech in an educational Activity as `pedagogical_speech`.

When actual speech needs producing/replacing, load:

```text
VOICE_GENERATION.md
skills/greia-voice-production/SKILL.md
```

### Shared character speech

Accepted shared v0.2 assets live at:

```text
assets/audio/characters/shared/v0.2/
```

Current accepted set:

```text
180 shared reactions
12 canonical character introductions
```

Documented generic families include:

```text
ready.go
praise.general
celebrate.success
encourage.retry
encourage.progress
```

Reuse shared reactions instead of generating duplicate generic praise when the current runtime resolver exposes the needed family.

Do not assume a generic greeting family exists, and do not copy the shared WAV catalogue into individual Activities.

## 9. Resolve semantic feedback before playing sound

One child action can simultaneously mean:

```text
ordinary item collected
teaching target completed
score changed
milestone emitted
round finished
victory reached
```

These events must not independently fire competing sounds.

Classic failure:

```text
collect final item
-> ordinary collect SFX starts
-> final-word speech starts
-> victory fanfare replaces it
-> character congratulations overlaps everything
```

Instead resolve the state transition first, then deliberately choose one of:

```text
SEQUENCE
SUPPRESS
REPLACE
INTERRUPT
COALESCE
```

The final item/final answer/final piece is normally a **terminal transition**, not merely an ordinary success plus another victory callback.

Protect pedagogical/required speech, keep queues bounded, and emit completion/score/milestone facts once.

`FEEDBACK_ORCHESTRATION.md` owns the detailed rules.

## 10. Score, Stars, medals and achievements

Every Activity must explicitly decide its progression relationship, even if the correct answer is `none`.

Keep these separate:

```text
local Activity score/progress
    Activity-owned presentation/state where appropriate

normalized completion/milestone/score facts
    emitted by Activity through Greia contracts

Greia Stars / medals / trophies / global progression
    platform-owned policy and ledger
```

Activities report facts. They do not directly grant or mutate global rewards.

Do not add streaks, points or reward spam simply because games often have them.

`ACHIEVEMENTS.md` owns the exact event/reward contract.

## 11. Technical implementation standard

For first-party Python Activities:

- keep `main.py` a thin bootstrap/composition root;
- use cohesive modules/classes around real responsibilities;
- prefer composition over deep inheritance;
- use polymorphism at genuine variation points;
- reuse Greia platform services/primitives rather than cloning them;
- preserve both Greia script-launch and repository/package import contexts;
- use Greia storage/events/progression/permissions rather than private substitutes;
- keep Activity code display/input-backend neutral;
- never draw or own the real Greia Home/Back system controls.

### Shared child creations — active platform workstream (not yet public SDK)

**Storage sizing:** do not assume the historical 32 MiB private namespace. Shipped Greia now uses an adaptive per-Activity namespace (25% of the actual writable profile-data filesystem, with the old byte quota only as a minimum/fallback), while a shared platform `VolumeBudget` caps aggregate variable child-data growth at 75% used plus 512 MiB free. Per-file/KV/media bounds still apply. Activities must never implement their own disk-usage policy or bypass the trusted storage broker.

The platform-owned PNG/WAV/UTF-8 `CreationLibrary` has a guarded Activity transfer API (`get_creations`) and manifest `creations.produces`/`creations.consumes` declarations. The universal `CreationsGalleryScreen`/controller and the nonblocking `request_selection(...)` / `poll_selection(...)` / `cancel_selection(...)` protocol now connect in SOURCE-WIP to a trusted modal host. Legacy-X and Simulator each implement the same runtime-neutral Shell modal contract; an Activity still cannot enumerate/delete the profile library or mint its own handle. **Never** read another Activity namespace, mount a global shared directory, create an Activity-local chooser, or block a frame loop waiting for human input.

Painting is the reference PNG integration: normal autosaves stay private; an explicit up-arrow publishes an immutable snapshot; from Painting's own gallery a down-arrow requests `image/png`, the Activity polls at a bounded cadence, and a child-selected one-use handle is imported as a new independent editable private painting after digest/type validation. This latest interaction is **SOURCE-WIP and not yet accepted in a complete checkout/GUI**. New consumers should copy the semantic pattern only after the consolidated acceptance is green. The cross-Activity implementation and 45-Activity release review remain tracked in the single Creations PLAN/PROGRESS; Shape Garden (2026-10 rework) is now a word-free composition studio with a persistent project model, a gallery of up to 24 gardens and a flattened PNG share/backdrop-import round trip; its older "not a persistent editor" status is superseded.

### Use the shared control kit (ADR 0037, Accepted)

Do not hand-draw buttons, mode tabs, HUD counters, prompt bubbles, try-again banners or completion cards. Compose them from `greia_platform.activity_controls` (+ `activity_feedback`, `pygame_completion`), which gives one look, cached rendering and keyboard / D-pad / stick / south-button focus for free. Reference implementations (all 45 Activities now use the kit): `activities/casa_del_dieci/ten_house_controls.py` (icon-only listen + check pills, ten-frame rooms, `CastFeedback`, completion scene), `activities/pasticceria_magica/pasticceria_controls.py` (pantry, counted badges, bell), and for galleries/toolbars `activities/painting/` and `activities/writing/`. The sample below shows API shape only; the reworks are word-free, so prefer icon-only pills (`kit.glyph(...)`) and picture prompts over text labels such as "OK".

```python
from greia_platform.activity_controls import (
    BodyShape, ButtonRole, ControlKit, ControlLayout, ControlTheme, ExternalTarget, PygameControlInput,
)
from greia_platform.activity_feedback import CastFeedback
from greia_platform.ui_core import SurfaceNavigator, UiEventResult

kit = ControlKit(typography, ControlTheme.for_accent("orange"))      # primary Collection hue token
layout = ControlLayout.for_canvas(canvas, screen.get_size())          # protected Home/Back mapped to logical px
tabs = kit.tool_strip("mode", [("a", res.text("tab.a"), kit.text_icon("🧁", 30)), ...], on_select=switch_mode)
stars = kit.hud_chip("hud.stars", rect, icon=kit.star(40), value=0)
ok = kit.pill_button("ok", rect, label="OK", icon=kit.glyph("check", 40), role=ButtonRole.PRIMARY, on_activate=confirm)
prompt = kit.prompt_banner("prompt", rect, text=res.text("prompt.x"), replay_icon=kit.glyph("listen", 34), on_replay=replay_cue)
cells = [ExternalTarget(f"cell.{i}", r, lambda i=i: tap_cell(i)) for i, r in enumerate(CELL_RECTS)]  # your own art, kit focus ring
layer = kit.layer([*cells, *tabs.controls, stars, ok, *prompt.controls])
surfaces = SurfaceNavigator(layer)
kit_input = PygameControlInput(to_logical=canvas.pointer, is_safe=safe_point)
cast = CastFeedback("dani", height=170, art=kit.art)                  # cast.correct() / cast.try_again()

# loop: result = surfaces.dispatch(kit_input.translate(event)) when not None; repeat = kit_input.poll() per frame;
# IGNORED pointer input is gameplay. Draw: scene -> cast.draw(surface, midbottom) -> surfaces.draw(surface).
```

- Lay bars with `layout.top_bar(layout.control_height(64, maximum=...))`, `layout.row(...)` and `layout.fit(...)` (labels shrink first, then pills go icon-only); never place controls in `layout.protected`.
- Labels must come from `LocalizedResources.text` (already CAPITALS per ADR 0034). HUD/system glyphs: `kit.glyph("listen" | "replay" | "check" | "trophy" | "bell" | "clear")`; stars: `kit.star(size, filled=...)`.
- Completion: `PygameCompletionScreen(typography, scene=CompletionScene(kit, character="dani", star_total=N))`, then `surfaces.push_overlay(CompletionOverlay(completion, on_primary=restart, on_secondary=next_or_None))`; add `secondary_label` to `CompletionContent` for a "next" button.
- Mutate control state (`label`, `value`, `visible`, `enabled`, `selected`) only when the model changes; the kit caches every state/content surface in bounded LRU caches, so `draw` stays blits only.

### Shared art library and Shell theme folders

- **Shared art library:** reuse scenes, props, creatures, HUD glyphs, FX and cast poses by semantic ID (`bg.*`, `prop.*`, `creature.*`, `icon.hud.*`, `fx.*`, `character.<id>` variants) instead of drawing private art; inventory and registration rules are in `assets/visual/README.md` and `skills/greia-visual-authoring/SKILL.md`. Never redraw a cast member inside an Activity.
- **Theme folders:** one Activity is one experience; the Shell groups related Activities. Add a theme to the manifest's `discovery_tags` (e.g. `discovery_tags = ["sea", "nature"]`) to join that theme's Shell folder. A theme becomes a one-level folder only if it is listed in `FOLDER_THEME_IDS` (`src/greia_launcher/catalogue_view.py`, currently `sea`) and has at least 3 visible members after Parent/age filtering; adding a new folder theme is a platform change (icon + constant + test), not an Activity change. Do not build multi-game hubs inside one Activity.
- **Mouse-first placement and keyboard hint (ADR 0037 §4a/§4b; `ACTIVITY_INPUT_STANDARDS.md`):** Greia is driven by a mouse/touchpad, so controls used together (go + brake, left + right, jump + act) form one compact cluster bottom-right or bottom-centre: place them with `layout.cluster(sizes, hint_size=...)` (`ControlCluster.rects`, `.hint`), never in opposite corners; previous/next paging arrows may flank the content they move. `directional`/`game` Activities and `hybrid` play that acts directly on arrows/Space show a `KeyboardHint` (`kit.keyboard_hint(id, rect, active={KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})`, size from `KeyboardHint.preferred_size`): `show(8.0)` at start, `demonstrate()` on idle-hint steps, `observe_event(event)` for every event (True → redraw), `update()` once per loop (True → redraw) and `frames.wake_at(hint.deadline())`. Add it to the `ControlLayer` targets (display-only, never hit or focused). Reference: `activities/quattro_amici/` (hint), `activities/morbidi_mostriciattoli/monster_layout.py` (drawers beside the tray). Audit and follow-up list: `docs/reviews/activities/2026-10-16_CONTROL_PLACEMENT_AUDIT.md`.
- **Pointer and input parity:** `PygameReferenceCanvas.present()` already draws the platform pointer (`pointer=True` default); do not draw your own cursor. Do not present every frame to keep the pointer live: the frame governor's `POINTER` frames call `canvas.present_pointer()` (see "Frame governance" below). A `hybrid` input profile must still provide keyboard and controller paths for every action (kit focus navigation does this for kit controls; custom hit targets need `ExternalTarget`).

### Patterns from the 2026-10 reworks (all 45 Activities)

These are the conventions the reworked Activities share; copy them rather than inventing variants. Full programme record: `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P7_ACTIVITY_QUALITY_PROGRAM.md`.

- **One Activity = one core experience.** Levels/stages of one loop are fine; no multi-game hubs or tab piles. Related Activities are grouped by Shell theme folders, never merged.
- **One feedback grammar through `CastFeedback`.** Correct: `pose_cheer` + FX + a short approved line. Try again: `pose_think` + a *demonstration* (never a bare "wrong"), unlimited kind retry. Finish: the shared cast completion scene (`pygame_completion`, 1-3 stars); the scene currently supports one cast member and has no calm variant or icon parameter (see P7 section 8).
- **Graduated hints with a bounded back-off (`IdleHintScheduler`, ADR 0037 §6b):** never write your own "every N seconds" hint loop. Own one `IdleHintScheduler` (`greia_platform.activity_feedback`), `reset(now)` it on every child input and new round, and in `step()` call `step = hints.poll(now, since)` (or `is_due` + `fire` when the hint may find no valid target): hint 1 after 6 s idle, hint 2 a further 12 s, hint 3 a further 24 s, then silence until the next input. Use the returned step to pick your graduated content: cast `pose_point` + pulse on the next valid target, then demonstrate one step, then glow the right target. Wrap every hint animation length in `hints.animation_seconds(x)`, which caps it at 1.5 s on the reference-floor frame profile. A hint never shows the answer as text, a number or a pre-marked slot.
- **Never answer-revealing UI.** No printed sums, lit target counters, auto-focused right choice, per-slot answer icons or pre-GO right/wrong marks. Wrong options that are "sometimes right" are never offered as wrong; distractors are near-misses (+-1/+-2, look-alike, contrast).
- **Finite, kind rounds:** spoken goal, act, celebrate, progress dots, a real ending in 1-3 minutes; adaptive stages saved per profile; nothing fails or loses progress; old saves migrate forward (schema bump, never silent reset). Event ids stay stable for achievements (e.g. `bridge.level_completed`) unless deliberately renamed.
- **Child-work custody:** every saved item is reachable (paged big-card gallery); delete is deliberate (preview, Back/keep is the default, never hover or single stray tap); a full shelf shows a sheet or refuses a new item, it never evicts silently; no blank or duplicate saves; drafts survive Home; share to My Creations publishes immutable PNG/WAV/UTF-8 snapshots through the platform API; gallery actions must target the *focused* item (selection follows kit focus; see the `552011a1` regression).
- **Pygame `set_alpha` pitfall:** never call `Surface.set_alpha(None)` on a per-pixel-alpha surface; it disables alpha blending for every later blit and transparent pixels draw solid. Reset with `set_alpha(255)`. Cache static composition once (no per-frame alpha surfaces, decode or scale) and bound every cache and list.
- **Shared vocabulary audio bank.** Picture-name clips live once in `assets/audio/vocab/v1/<locale>/<noun_id>.wav` and resolve through `greia_platform.localization.shared_vocab_audio_path` (locale, base, English, silence). Never copy noun clips into an Activity package. Spoken numbers will use a shared `shared_number_audio_path` (F6, awaiting voice approval; probe it with `getattr(..., None)` as `pasticceria_magica` does). Cast lines come from `shared_character_audio_path`; do not reach them with relative `../..` paths (installed-image safety).
- **Runtime policy:** the stdlib `abc` module is allowed in the curated child runtime, so abstract base classes at genuine variation points are fine. Do not rely on other new imports without checking the runtime policy.
- **Canonical cast and library art only:** no off-model redraws, no emoji as content; if the library lacks a needed picture, keep the Activity-private asset small and list it as a promotion candidate in P7 section 8.
- **Platform APIs added during the reworks:** `greia_platform.activity_api.set_curated_wallpaper(asset_id)` (requires `customization.manage`; curated `bg.wallpaper.*` scenes only, never a caller path). USB wallpaper import is not part of the child flow; it belongs to a trusted Parent/system workflow.
- **Evidence honesty:** reworks are SOURCE + headless desktop review. Voice lines are requested, not recorded (`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/VOICE_LINES_REQUESTED_2026-10-16.md`); until approved clips exist the Activity must stay fully playable in silence.

### Performance is correctness

The Acer-class floor is part of the design target, not a later optimization pass.

Avoid hot-path work such as:

```text
filesystem scans
asset decoding/loading
image scaling/transforms
font recreation
subprocess/device discovery
storage/config reads
large allocation churn
unbounded audio/event queues
full-screen expensive alpha work that never settles
```

Prefer preloaded/cached immutable assets, bounded caches/queues, event-driven/invalidation rendering where appropriate, and cheap static states.

A performance stall can become an audio/timing bug by delaying feedback until semantic events collide.

### Start-up cost: nothing heavy before the first frame

On the Atom reference floor, launch time before the first frame was dominated by pure-Python sound synthesis (2-7 s per Activity in the 2026-10-16 Acer re-sweep) and by speech clip loading. Rules:

- **Declare sounds, do not synthesize them at start-up.** Put synthesized cues in a `greia_platform.pygame_audio.DeferredSoundBank`: `bank.define(name, factory)` with a zero-argument factory (`sfx.define("correct", lambda: self._tone(880.0, 0.14, 0.20))`; speech clips: `speech.define(cue_id, lambda path=path: pygame.mixer.Sound(str(path)))`). The bank is a read-only mapping (`bank.get(name)` returns `None` for a missing or failed cue, so audio stays fail-soft). One daemon worker builds the remaining cues only after READY; a cue needed sooner is built on first use, never twice, with identical output. A sound whose synthesis consumes the shared random sequence must keep that order unchanged by deferral (`colline_allegre`, `orchestra_animali` render those particular voices eagerly inside the bank for that reason); do not synthesize anything else eagerly.
- **READY means a presented frame.** Call `mark_activity_ready()` once, immediately after the first `display.flip()`/`canvas.present()`; it releases the deferred work (`greia_platform.first_frame_work`). Never call it before a frame is on screen, and do not start other background work earlier. Other start-up work that the first screen does not need may register with `after_first_frame(self._method)` (bound method, weak reference, runs at READY or immediately if already READY); give such work its own bound and owner.
- **Bake static scenes once** (as `viaggio_delfino` bakes its bay scene) instead of composing them in the first frame.
- **Audio uses plain `pygame.mixer`; the platform owns when the device is open.** `greia_platform.python_activity_entry` installs `greia_platform.activity_mixer_lease` before your code runs, so `pygame.mixer.Sound` / `pygame.mixer.Channel` are lease-aware and the mixer closes after 10 s with nothing playing (an open SDL mixer alone costs ~5% CPU on the Atom) and reopens in the same format, channel count, reservation and channel volumes right before the next sound (~0.1 s, only for the first sound after silence; voice completion via `channel.get_busy()` is unaffected). While closed, `get_init()` still reports the format and status calls (`get_busy`, `stop`, `get_length`) answer without reopening. Therefore: create Sounds/Channels only through `pygame.mixer`, never through ctypes/SDL or `pygame._sdl2` playback; do not `quit()`/re-`init()` the mixer to save CPU yourself; prefer one-shot `Sound`/`Channel` playback over `pygame.mixer.music` and channel end-events (either keeps the device open for the rest of the visit). A capture device (`pygame._sdl2.audio`, microphone) keeps the mixer open while it is open.
- **`SDL_FRAMEBUFFER_ACCELERATION=0` is set by the runtime adapter** (`greia_launcher.runtime_adapter`, `SDL_SOFTWARE_FRAMEBUFFER_ENVIRONMENT`) for Activities and by `greia-launcher.service` for the Shell; it makes window creation on the Atom 0.03-0.15 s instead of 0.7-1.2 s and saves about 70 MB RSS per process. Activities must not set or override SDL environment variables themselves. Do not import `pkg_resources`/`setuptools` (blocked before pygame loads) and do not write bytecode into the Activity folder (the platform supplies a read-only precompiled prefix).
- Validate with `tests/test_launch_startup_performance.py` (budget guard for representative Activities) and, for Acer claims, the sweep method in `docs/reviews/acer/2026-10-16_ACER_ACTIVITY_SWEEP.md`.

### Frame governance (ADR 0037 §6a, mandatory)

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

- **Mark dirty** for every visible state change: input handled, timer/timeline fired, `cast.update()` returned True, `controls.layer.invalidation.should_draw`, a time-based visual flipping state (e.g. caret blink phase). `frames.invalidate()` does the same from code that has no dirty flag.
- **`animating=True`** only for essential motion (feedback, a steered character, physics after GO); `frames.animate_for(seconds)` requests a fixed animation window.
- **`ambient=True`** for decorative idle motion (bubbles, clouds, breathing cast, sparkles, bobbing marks, band sway): full rate after input, then 12 fps on `standard` (after 8 s idle) and **0 fps (frozen last frame) on the reference floor** (`FramePolicy.reference_floor()`: 24 fps cap, decoration freezes after 6 s idle), resuming instantly on input. The reference-floor (low-end) profile is selected automatically on devices with at most 2 logical CPUs (the Atom N270 reports 2) or by `GREIA_FRAME_PROFILE=reference-floor`; never branch on it yourself, and keep hint animations short through `IdleHintScheduler.animation_seconds()` (capped at 1.5 s there). Essential motion (`animating=True`) is not frozen, so do not misclassify decoration as essential: `clinica_cuccioli`'s bobbing problem marks did exactly that and held 24 fps forever. Never declare decoration as `animating` or as a perpetual `dirty` — that keeps the Atom above 100% CPU. Loops that pace decoration themselves (e.g. an 8 fps drift sent as `dirty`) or simulate purely decorative actors gate that on `not frames.ambient_frozen`, so the scene resumes where it froze.
- **Fixed-step simulations** keep their step with `frames.wait(polling=True)` and present only when `frame()` says so; `polling=True` also keeps held-stick repeats on cadence.
- Activities that draw straight to the display (no reference canvas, e.g. Writing/Painting) keep Greia's pointer in a `PygamePointerSprite` (`greia_platform.pygame_canvas`; save-under: it restores the pixels beneath the pointer and redraws only the two small rects): `POINTER` frames call `sprite.refresh(screen)`, never a full redraw; a painting stroke pushes only its dirty rectangle (`erase` → blit region → `refresh(extra=(region,))`).
- **Dirty rectangles for small moving sprites** over a cached background (games): ask the renderer for the sprites' logical rectangles each frame, then `plan = canvas.plan_regions(previous + current)`; if `plan` is not None, `canvas.render_regions(plan, self.render)` + `canvas.present_regions(plan)`, else a full frame. Force a full frame on any non-motion input, model event, timeline action, state change or kit invalidation, and cover the rule with a test that compares the dirty-rect surface to a full render (see corsa_bacche / foresta_parole).
- **Never re-render a still screen on a timer.** A full 1024×600 render costs 150–220 ms on the Atom and input that arrives meanwhile waits for it (the SDL idle wait itself wakes within ~1 ms of input). `keepalive_seconds` is a migration aid only, and on the reference floor it pauses once the child is idle (resuming from the next input). Do not mark the whole frame dirty on plain pointer motion (Greia's pointer is a `POINTER` frame / `PygamePointerSprite`; hover changes come from the kit's invalidation): `workshop_settings` still does and repaints ~220 ms per move on the Atom.
- Check with `PYTHONDONTWRITEBYTECODE=1 python3 tools/measure_activity_idle_cpu.py --settle 15 <activity>`: a static screen should show ~0 presents/s.

### Blit cost: RLE every per-frame alpha surface (`greia_platform.pygame_blit`)

Measured on the Acer (Debian pygame 2.1.2 / SDL 2.26.5, 32-bit X11), onto the 1024×600 canvas: opaque display-format blit ~2 ms; **per-pixel-alpha blit ~134 ms (~0.22 µs/pixel, even for fully opaque or transparent pixels)**; the same surface RLE-encoded ~1.5 ms (≈16 ns/pixel where pixels are translucent), identical within 1/255. That one SDL path was why colline_allegre (4 fps) and viaggio_delfino (4.3 fps) were unplayable: their parallax bands and ground strips were `convert_alpha()` surfaces blitted every frame. Recipe:

- **Every alpha surface blitted per frame** goes through `prepare_static(surface)` once, after it is final (display format + `RLEACCEL`; the source is not modified). Renderers that blit surfaces owned by a loader/kit cache keep one `PreparedSurfaces()` and blit `fast(image)` (bounded, identity-keyed RLE copies; only for surfaces nobody draws on afterwards).
- **No per-frame `set_alpha`** on sprites: it forces the slow path and drops RLE. Use `FadeSteps(surface).at(fraction)` or `fast.faded(image, fraction)` (a few baked levels).
- **HUD over a moving scene:** `HudOverlay().draw(canvas, key, layer_draw, stale=layer.invalidation.should_draw)` composes the kit layer once into a transparent RLE overlay and re-composes only on key change/invalidation/resize (colline_allegre, baia_delle_orche).
- The logical canvas stays in the display format (`PygameReferenceCanvas` default). Never replace it with a 24-bit or alpha surface: sottomarino's 24-bit canvas alone cost ~25 ms a frame.
- Static backgrounds: compose once, `convert()` (opaque). Scrolling worlds: pre-render terrain/parallax into strips once and blit them (colline `CollineArt.chunk`, delfino `ParallaxStrip`); pre-rotate sprite frames in angle steps; render text once.
- Do not draw on, `subsurface` or `smoothscale` from an RLE surface on a frame path (each lock decodes and re-encodes it); keep the plain source for composition and blit the prepared copy.
- After the fix (Acer, scripted play, 2026-10-16): colline 4.0→21.7 fps (frame work 252→22 ms), delfino 4.3→23.3, treno 8.7→20.3, sottomarino 16.3→21.4, labirinto 14.9→23.3, foresta 17.0→23.1; every motion game now needs ≤40 ms of work per frame, so it runs at the reference-floor cap (24 fps; 20–23 measured because of sleep overshoot and mixer-reopen stalls).

Load `ENGINEERING.md` before implementation.

## 12. Project-specific tools stay with the project

Activity-specific authoring/generation/migration tooling belongs under:

```text
activities/<activity_dir>/tools/
```

Examples:

```text
activities/my_activity/tools/generate_voice_requests.py
activities/my_activity/tools/build_local_assets.py
activities/my_activity/tools/migrate_content.py
```

Rules:

1. place project-specific tools there from the start;
2. runtime code does not belong in `tools/`;
3. repository root `tools/` is only for genuinely Greia-wide tooling;
4. remove obsolete/one-shot tools and scratch output when work closes;
5. remember the Activity directory is also package input—do not ship development machinery accidentally;
6. promote a local tool to root only when it genuinely becomes a reusable Greia-wide facility with a stable contract.

## 13. Use the headless Simulator throughout development

Do not wait for the Activity to be finished.

Typical loop:

```text
minimal valid skeleton
-> headless Simulator

first meaningful child interaction
-> focused tests + headless Simulator

major runtime/resource/refactor change
-> focused tests + headless Simulator

completion/restart/audio integration
-> headless Simulator

final runtime edit
-> final headless Simulator again
```

Canonical runner:

```bash
PYTHONPATH=src python3 tools/headless_greia_simulator.py \
  --activity-dir activities/<activity_dir> \
  --workspace-dir /tmp/greia-sim-<activity_dir> \
  --locale it \
  --viewport 1024x600 \
  --survival-seconds 12 \
  --screenshot-prefix /tmp/greia-<activity_dir>-it
```

Use `--press-key` or `--click-x/--click-y` for meaningful mechanical interaction where practical, and test relevant shipped locales.

`SIMULATOR_WORKFLOW.md` owns the detailed loop.

## 14. Final GUI Simulator review is mandatory

Headless integration cannot decide whether:

- a toddler understands the first action;
- the game is fun/coherent;
- targets are large enough;
- the teaching mechanic works;
- presenter/audio timing feels right;
- final-item feedback collides;
- 1024×600 presentation is pleasant;
- obvious performance stalls exist.

After final headless integration launch:

```bash
python3 tools/greia_simulator.py \
  --state-dir ~/.greia-simulator-review-<activity_dir>
```

Present that exact final state to the user/reviewer.

If GUI review cannot be performed, the strongest honest result is:

```text
SOURCE-VERIFIED / HEADLESS-SIMULATOR-PASS / GUI-REVIEW-PENDING
```

Any runtime-relevant edit after evidence requires rerunning the applicable final checks.

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

For actual visual asset creation/adaptation load:

```text
skills/greia-visual-authoring/SKILL.md
```

For `.greiaactivity` packaging use current package authority:

```text
docs/architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md
src/greia_platform/activity_packages.py
src/greia_platform/activity_package_format.py
```

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
PROJECT_LOCAL_TOOLS_CLEAN=yes
PERFORMANCE_HOT_PATHS_BOUNDED=yes
FOCUSED_TESTS_PASS=yes
FINAL_HEADLESS_SIMULATOR_PASS=yes
GUI_SIMULATOR_USER_REVIEW=PASS
```

Physical/Acer evidence is additionally required for claims that depend on physical performance, hardware behavior or production display/input paths.

Never upgrade source or Simulator evidence into a stronger evidence class that did not actually run.


### Missing localized Activity feedback (2026-10-13)

When a built-in Activity cannot resolve a requested
`LocalizedResources.text("feedback.*")` message,
**never substitute a fixed-language sentence** in the
runtime error fallback. Word Forest has been repaired:
normal feedback remains locale-bundle owned, and its
emergency presentation is a language-neutral visual
celebration symbol. Missing required translations are
still audit/release defects, not a reason to declare a
language complete. See
`tests/test_word_forest_phonics_inventory.py`.


### Painting save-status text ownership (2026-10-13)

Painting now resolves `status.saved`,
`status.saving`, `status.error` through the
existing Activity `LocalizedResources`, passing
the three locale strings to its renderer once for
cached visual surfaces. The renderer uses stable
semantic state IDs rather than Italian words.
Follow that pattern for other Activity UI:
never choose a UI language from process `LANG`
inside the renderer and never make cross-locale
text fallback a hidden Italian phrase. An
isolated no-context renderer uses neutral symbols.
Visual sizing is source WIP, especially for
longer ES/FR labels. Test:
`tests/test_painting_contract.py`.


### Live Activity copy: source API, classroom text and renderer separation (2026-10-13)

The only public string-display lookup on the current `LocalizedResources`
class is **`.text(key, variables=None)`**, not `.string()`. The latter
is not implemented; surrounding it with `except Exception` hides a real
localization defect and can silently force the fallback copy in *every*
locale. When reviewing or authoring an Activity, trace normal rendering
through `.text` and the concrete locale JSON instead of counting keys.
Greia uses `string.Template` placeholders (`$consonant`, not Python
`{consonant}`) for this API. The result honors child text-case policy.

The Magic Syllables Activity now derives its exploration header from the
**actual selected curriculum's displayed syllables**, not an assumed
Italian vowel grid (French may show `MÉ`). Its real explorer/catcher/
word-slot instructional copy is authored in four locale bundles, while
ES/FR *teaching scripts and recordings remain unapproved*. Use the
same separation of lesson data vs translated UI in other literacy games.
Greenhouse toolbar geometry stores semantic keys, with its app resolving
translated labels once at launch and the renderer using neutral icons
when independently constructed. Avoid per-frame locale resolution and
hardcoded Italian emergency completion text. Follow
`tests/test_four_language_activity_runtime_text.py` and the existing
GLA-015 for source/visual acceptance; no live review has run yet.


### Opposites state words and real language presentation (2026-10-13)

*(Historical lesson: `mondo_contrari` was later reworked into Flash's guided opposite game with no tabs or state banners; the locale-resolution rule below still applies.)*

`activities/mondo_contrari` originally had perfectly good `opposite.*`
translations in EN/IT/ES/FR bundles but drew ten fixed Italian state
banners and only switched the category tabs between IT and EN. The real
runtime now resolves the ten semantic state words once from
`LocalizedResources.text()`; five category labels reuse the identical
two words, with GreiaTypography supporting accented glyphs and bounded
text-surface caches. The composition root resolves only the declared
EN/IT profile locale; staged ES/FR rendering uses explicit test-only
resource injection. Do not equate stageable source strings with
accepted language-bearing speech. For non-localized independent renderer
tests use concept pictograms, not arbitrary fixed-language text. See
`tests/test_activity_mondo_contrari.py` and
`tests/test_four_language_activity_runtime_text.py`.
`viaggio_delfino` also now uses visual symbols for missing-resource
completion emergencies instead of forcing Italian replay copy; its
real EN/IT completion title/replay/body remain semantic resources.
