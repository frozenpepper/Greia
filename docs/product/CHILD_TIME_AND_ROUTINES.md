# Greia: Time, Duration and Everyday Days

**State:** PRODUCT PROPOSAL + EARLY SOURCE INCUBATOR; **not yet an accepted
production release scope or an installer/hardware claim**  
**Date:** 2026-10-08  
**Product identity:** My Time / Il Mio Tempo  
**Source prototype:** `activity_incubator/tempo_di_greia/`  
**Existing educational authority:** `ACTIVITY_CATALOGUE_AGES_3_5_STRATEGY.md`  
**Runtime ownership:** Platform owns clock validity/system settings and any
cross-Activity alarm; Activity owns its own pedagogical scene and session-only
stopwatch/timer state.

## Why this belongs in Greia

Time is both something children use in ordinary life and a rich learning
subject. Treat it as a connected **utility + experience + personal meaning**,
not four unrelated quiz apps. The child should be able to check the time,
measure an experiment, visualize a short waiting period, explore a clock, and
recognize upcoming meaningful events without reading filenames or menus.

This is not a school timetable, behavioral compliance timer, electronic
babysitter or an attempt to demand perfect time knowledge from a preschooler.
Greia should encourage real-world observation and play rather than maximizing
screen engagement.

## Time family — functional boundaries

| Surface | First useful child action | Current/proposed owner |
|---|---|---|
| Real Clock | See current local time; analogue hands + optional digital display | My Time Activity using read-only trusted system time |
| Practice Clock | Change the illustrated time without changing the actual clock | My Time Activity only |
| Stopwatch | Start, pause, resume, reset duration during a short task | My Time Activity, monotonic elapsed time |
| Visual Timer | Choose 1, 3, 5 or 10 minutes; start, pause, see remaining proportion, restart | My Time Activity, monotonic elapsed time |
| Time Workshop | Match familiar routine times, compare short/long and try elapsed-time experiments | Separate playful learning mode/Activity, not in initial prototype |
| My Days | Large today/tomorrow/yesterday and short upcoming-events visual calendar | Separate calendar experience; Parent-authorized event source plus profile-scoped child stickers |
| Background timer | Persist/alert while another Activity runs or system suspends | Future **platform-owned** timer/alarm lifecycle, NOT current Activity |
| Parent screen-time accounting | Limit Greia usage independently from playful timers | Existing `UsageLimitService`; absolutely no child timer privilege over it |

There should not be two competing wall clocks in the Shell and Activity:
the Shell may offer a passive current-time affordance, while My Time provides
the large interactive experience. The Clock and lesson should not independently
invent date/time parsing, localization or trust.

## First playable slice — code currently present, SOURCE-ONLY

`activity_incubator/tempo_di_greia/` contains:

- one coherent Activity with Clock / Stopwatch / Timer modes;
- real wall clock rendered as a large analog dial plus HH:MM readout;
- weekday and day/month formatted from a single local-time snapshot;
- independent practice clock with separate touch rings for twelve inner illustrated hour stops and four outer quarter-hour stops;
- monotonic pause/resume stopwatch;
- countdown with duration presets, one-time finish state and replay;
- letterboxed 1024×600 logical scene, protected Greia Home physical region,
  keyboard mode shortcuts and interactive mouse controls;
- low-frequency, at-most-ten-Hz screen redraw, cached Greia typography;
- provisional icon-first clock/stopwatch/timer mode buttons and play/pause/restart controls; visible Left/Right/Tab focus and Enter activation; gentle visual countdown completion (all SOURCE-WIP, new screenshots/audio/child review pending);
- small authored SVG clock icon with an exact verified WebP rendition;
- separate IT and EN localization bundles, source tests, and a small
  dependency-injected semantic voice coordinator with a bounded one-cue
  pending sequence;
- cached, package-local prerecorded audio playback through Greia's existing
  localized audio cue resolver. A large icon-only speaker/replay control
  appears only if the relevant reviewed instruction clip actually exists.
  No voice generation or cloud service is present on the child device.

**Dual-ring practice input remains SOURCE-ONLY.** The inner ring changes the illustrated hour in the current AM/PM half-day and the outer ring changes imagined minutes. Practice mode hides the real calendar date rather than implying an imaginary time has a real weekday. Visual, small-screen and child usability review remains outstanding, and the dual-ring teaching interaction is not an accepted pedagogical design yet.

**What it does NOT yet have:** recorded/approved spoken labels or instructions,
mapped locale audio files or local launcher title WAVs,
finished child-safe sound, real children usability evidence, accepted full-size
art/composition/character presenters, touch-controller acceptance, visual
calendar, background alarm persistence, time-validity status, explicit offline
wrong-RTC handling, external Greia Home integration, or any release approval.

The source candidate stays in `activity_incubator/`, not `activities/`,
until those responsibilities are satisfied. Promoting it prematurely would
break the current first-party spoken-label completeness contract and expose
unreviewed prereader UI in shipped builds. This is a deliberate non-regression
boundary, not a permanent second Activity system.

**Single deferred local-agent acceptance queue:**
`docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md` lists exact test commands,
evidence expectations, dependency/stop conditions, queue-only commit rules,
status updates and the separate hardware authorization gate. It does not
replace the existing Creations P1–P7 acceptance procedure or product plan.

### Prereader voice source brief (not yet produced)

`activity_incubator/tempo_di_greia/VOICE_PRODUCTION_BRIEF.md` now records
intended semantic cues, exact Italian/English text, Dani speaker kind and
event triggers. All authoring is through existing Greia VoiceEngine; a
Modal-backed authoring provider would require separate integration and approval,
not Activity-owned cloud TTS. There are no reviewed WAVs, title audio, locale audio mappings,
actual listened playback acceptance or provider invocations. The optional
playback/first-use/replay **source implementation** now exists; it does
nothing when audio is missing rather than inventing speech or making a
cross-language fallback. The Activity remains incomplete for pre-readers.

## Clock trust and hardware rules

1. **Real time vs elapsed time:** actual date/hour requires the installed
   platform's trustworthy local clock and timezone. Stopwatch and foreground
   countdown must use a monotonic elapsed clock, not `datetime.now()`.
2. **Invalid clock:** an offline first boot, flat RTC battery, timezone change
   or manual Parent clock correction may make system date/time uncertain.
   Treat that as an explicit product state; do not tell a child an invented
   current time/date with false certainty. Dev acceptance must test invalid
   clock and daylight-saving boundaries before promotion.
3. **No clock-setting permission:** changing system date, time, timezone or
   NTP source remains Parent/platform authority. The practice dial is
   disposable simulation; exiting always returns to real read-only time.
4. **Background semantics:** today's foreground-only countdown cancels when
   the Activity ends. Cross-Activity notification or suspend/resume cannot be
   solved by letting an Activity subprocess keep running in the background.
   That future milestone needs a tiny Greia-owned timer service using durable
   deadlines, profile routing, notification priority, wake-policy and
   authoritative clock validity.
5. **Parent limits:** child timers, calendar entry and practice clock never
   mutate `UsageLimitService` state or grant extra screen time.
6. **Resource floor:** avoid 30-FPS unconditionally repainted clocks, runtime
   SVG, continual voice synthesis, high-frequency wake-ups or multiple
   timer threads per Activity. Only meaningful pointer/clock changes redraw.

## Prereader interaction and speech

Children aged ~3–5 must understand the interaction without reading:

- tactile large Clock / Stopwatch / Timer destinations with explicit
  demonstration; labels supplement pictures, never replace them;
- short recorded prompts and optional repeat-audio affordance;
- distinguish green-ish Start, pause and restart by geometry/symbol, not color
  alone; preserve selected timer duration visually;
- no alarming countdown sounds or time-pressure shame;
- a gentle, bounded completion animation and optional audible celebration;
- subtitles/captions always paired with spoken instructions;
- English and Italian voice pedagogy must be separately reviewed, especially
  weekday pronunciation, 12/24-hour wording, and 'minutes remaining';
- real clock and practice mode must visually say and look different.

Greia's existing local prerecorded-voice pipeline remains the production
contract; Modal may be used at authoring time where approved, but the child
runtime never gains cloud TTS or a hidden network dependency.

The clock may use Dani as the main guide for experimenting with hands and
Flash for stopwatch challenges, with optional Lilli/Tito appearances. This is
a **presenter concept**, not a finalized extra character or replacement of the
canonical shared cast. Reuse its semantic art catalogue/runtime renditions.

## Developmental progression (guidance, not age tests)

- **First:** day/night, now/later, visually measuring brief waits, before/after.
- **Next:** shorter/longer, meaningful daily routines and a few clock positions.
- **Then:** whole hours, half-hours, analog/digital comparison through play.
- **Later:** quarter-hours, minutes and elapsed-time problems if child is ready.

Every introduction requires an understandable short demonstration and
immediate observable consequence. Do not start with rote seven-day drills.

## My Days / Calendar — next product design

Start with a three-day visual strip centered on today, then a weekly view.
A monthly grid can be progressive/optional rather than the default. Event
tiles should show large icons/photos for family or school activities, birthday
celebrations, weekend adventures, weather sketches and child-made drawings.

Events written by Parent remain Parent-authorized: child controls may place
private stickers or record a memory, but may not silently change shared
family schedules or reveal another profile's events. Never expose raw
filesystem paths, external calendars, contact identity or private location
to ordinary Activities. Offline behavior is a requirement.

Calendar data must carry local timezone/absolute date, event owner, child
visibility and safe backup/restore semantics. Clock/date corrections must
not destroy journal entries or silently move birthdays across local days.
Reusing My Creations should reference/copy media through its existing typed
broker, never give the calendar blanket child-data filesystem rights.

## Acceptance and promotion, in order

1. Run isolated model/source tests at exact candidate SHA; review text locale
   parity and manifest package validation in a disposable sandbox.
2. Generate actual source screenshots at 1024×600 and 800×480, check the real
   trusted top-left Greia Home, hit regions, text/baseline scale, focus and
   presentation cost on low-end hardware; compare analog clock/visual timer
   clarity to actual physical clocks/timers.
3. Produce bilingual prerecorded short prompts and title clips. Verify with
   **listening**, not mere file presence. Test touch/controller and keyboard
   navigation, silence/focus-loss, first-frame READY and clean exit/relaunch.
4. Decide how a passive clock appears in Greia Home without being a mandatory
   Activity launch. Preserve existing Collection-first model.
5. Explicitly promote source package from incubator to normal
   `activities/`, reconcile first-party readiness/spoken-label tests, stage as
   **draft candidate** only after exact source and visual gates. No
   `[release].status = "approved"` before family acceptance.
6. Design Time Workshop and My Days only after first real utility use and
   child feedback; platform timer service only when background semantics are
   actually requested and acceptance-defined.

## Related technical ownership

- `src/greia_platform/usage_limits.py` owns screen-time accounting;
- `src/greia_platform/activity_viewport.py` and
  `pygame_canvas.py` own reference scale/input;
- `src/greia_platform/typography.py` owns readable text rendering;
- `src/greia_platform/localization.py` owns locale resource bundles;
- `assets/visual/authoring_library/making_learning_play.toml` includes
  mechanical clock/dial components; future activity illustration should
  evaluate **REUSE / COMPOSE / CREATE** rather than silently duplicating art;
- `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md` owns presenter identities;
- `docs/product/MY_GREIA_SETTINGS.md` remains independent: My Time is not
  the OS configuration page and cannot set system time.
