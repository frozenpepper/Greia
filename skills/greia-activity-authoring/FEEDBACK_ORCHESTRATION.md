# Greia Activity Feedback, Audio and Reward Orchestration

**Status:** mandatory cross-cutting Activity design/implementation guidance  
**Audience:** Activity authors, coding agents, reviewers  
**Reviewed:** 2026-10-30

Read this file for **every new Activity** and whenever an existing Activity changes success/failure feedback, spoken reactions, completion timing, score/progression events or performance-sensitive feedback presentation.

This companion owns the boundary between several systems that are individually simple but commonly collide in the same child action:

```text
local gameplay feedback
Activity sound effects
prerecorded character speech
pedagogical speech
shared character reactions
completion / score / milestone events
Greia Stars / medals / trophies / achievements
rendering and runtime performance
```

The detailed specialist authorities remain:

```text
skills/greia-activity-authoring/VOICE_GENERATION.md
skills/greia-activity-authoring/ACHIEVEMENTS.md
skills/greia-activity-authoring/ENGINEERING.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
```

This document does not create a new audio, progression or reward API. Inspect current source owners before naming exact runtime methods.

---

## 1. One child action can have several meanings

A common Greia bug is to let every subsystem react independently to the same input.

Example:

```text
child collects the last item
    -> ordinary item-collected chime
    -> spoken item/count feedback
    -> score increment
    -> round-completed event
    -> local completion animation
    -> presenter congratulations
    -> possible Greia Star / achievement consequence
```

If those effects are coded as unrelated callbacks, the result is usually bad:

- the collection sound and victory fanfare start together;
- congratulations cuts off the final counted number or phoneme;
- multiple character clips overlap;
- the completion screen appears before the child hears the final teaching cue;
- an Activity fakes a medal/trophy while Greia is separately awarding one;
- a slow decode/render path shifts the intended sequence enough to create intermittent timing bugs.

Treat the input as **one semantic transition** first. Then deliberately decide which presentation effects survive, which are sequenced and which are suppressed.

---

## 2. Resolve semantics before playing sounds

Do not write logic shaped like:

```text
on_collect:
    play_collect_sound()
    if last_item:
        play_victory_sound()
```

Instead reason in terms of the resulting semantic outcome:

```text
transition = model.collect(item)

if transition.completed_round:
    present_terminal_collection(transition)
else:
    present_ordinary_collection(transition)
```

The exact class/function names are Activity-specific. The invariant is:

> **model/state decides what happened before presentation/audio decides how to express it.**

A terminal action is not merely an ordinary action plus another callback. It is a distinct semantic result.

This applies to:

- last object collected;
- final correct answer;
- final letter/word pronounced;
- last puzzle piece placed;
- final patient/object repaired;
- score threshold reached on the same action as round completion;
- last creation step followed by save/completion;
- timeout/failure occurring while another cue is still active.

---

## 3. Feedback priority: protect meaning first

Use this default priority when cues conflict:

```text
1. pedagogical truth / required instruction
2. state-critical feedback the child must understand
3. local completion meaning
4. generic character praise / motivation
5. decorative SFX / fanfare / ambience
```

Examples:

### Final counted item

Preferred:

```text
child touches fifth apple
-> show/move fifth apple immediately
-> speak/hear "cinque" if that is part of the learning loop
-> after that cue is safe, show/play one concise completion celebration
-> emit the semantic completion fact once
```

Avoid:

```text
"cinque" + collect chime + victory fanfare + "bravissimo" all at once
```

### Final phonics target

The correct target sound must not be cut off by generic praise. A short celebratory visual can begin silently while pronunciation finishes; speech/fanfare follows only when it will not stomp the teaching sound.

### Wrong answer during presenter speech

Do not queue three retry messages because the child tapped rapidly. Coalesce/reject repeated equivalent feedback while the relevant cue is already active.

---

## 4. Sequence, suppress or replace — do not just stack

For every potentially colliding pair, deliberately choose one policy:

```text
SEQUENCE
    both meanings matter; play/present in a defined order

SUPPRESS
    the terminal/specific feedback subsumes the routine cue

REPLACE
    use one terminal variant instead of routine + terminal variants

INTERRUPT
    a higher-priority safety/required cue cancels a lower-priority cue

COALESCE
    repeated equivalent events produce one current/pending reaction
```

Good examples:

```text
ordinary collect chime + final victory fanfare
    -> SUPPRESS ordinary chime or use a terminal collect variant

spoken final number + congratulations
    -> SEQUENCE; number first

three rapid wrong taps
    -> COALESCE retry speech

Home/Activity termination while presenter talks
    -> INTERRUPT Activity-owned playback and cleanly release resources
```

Avoid unbounded FIFO speech queues. The child may already have moved on by the time queued speech plays.

---

## 5. Prefer semantic completion over magic delays

A fixed delay such as `sleep(1.0)` or `celebrate_at = now + 1.0` can be a temporary/product-specific solution, but it is not a general audio architecture.

Prefer, in order:

1. a real playback-complete/state-complete signal when the current runtime abstraction exposes one;
2. a known reviewed clip duration owned by the prepared audio resource/sequencer;
3. a short bounded semantic timer when completion signalling is unavailable and the timing has been reviewed.

Never block the main loop waiting for audio.

Do not use a guessed delay that happens to work on a fast development machine. Different clip lengths, locales and slow hardware make guessed timing fragile.

If a fixed delay is genuinely required, name it for its semantic purpose and document why it exists.

---

## 6. One explicit Activity audio/feedback owner

Non-trivial Activities should centralize playback arbitration in one cohesive owner, for example an Activity-specific `AudioSequencer` / `FeedbackPresenter` concept.

It may own:

- currently active semantic cue;
- priority;
- replacement/interruption policy;
- a **bounded** pending cue, if one is necessary;
- cooldown/coalescing state for repeated feedback;
- prepared/cached sound resources;
- playback-completion transition;
- cleanup on Activity stop/Home.

It should not own:

- global Greia reward policy;
- microphone hardware policy;
- system Home/Back;
- Chatterbox/TTS generation;
- global achievement presentation;
- physical device discovery.

Do not scatter `pygame.mixer.Sound(...).play()` calls throughout model, renderer and input handlers when sequencing matters.

---

## 7. Shared character speech: current canonical pool

Greia already has owner-accepted reusable character material at:

```text
assets/audio/characters/shared/v0.2/
```

Current accepted contents:

```text
180 shared character reactions
12 canonical character introductions
192 owner-accepted clips total
```

The generic reaction families currently documented by the Activity speech contract are:

```text
ready.go
praise.general
celebrate.success
encourage.retry
encourage.progress
```

These are available across the canonical characters where the current shared runtime resolver exposes them.

Important distinction:

```text
accepted asset bytes != guaranteed runtime resolver availability
```

Before depending on a shared family, inspect the current resolver/source contract. If the required family is not exposed by the runtime path yet, do not invent a private resolver or pretend it is available.

### Canonical introductions

The shared set also contains the accepted character self-introductions. They are shared/OS presentation material and must not be rerecorded independently for every Activity.

### Generic greetings

Do **not** assume a generic `hello` / `greeting` family exists merely because introductions do. As of this reviewed contract, the accepted reusable generic families are the five listed above. A new generic hello/goodbye family requires an explicit shared-library expansion and review.

An Activity-specific welcome such as:

```text
"Ciao! Oggi costruiamo un ponte!"
```

is normal `character_dialogue` because its wording carries Activity-specific meaning.

---

## 8. Reuse shared reactions instead of cloning praise

When a generic meaning is already represented by an accepted shared family **and the runtime resolver supports it**, use that family instead of generating another copy inside the Activity.

Benefits:

- consistent character identity;
- fewer duplicated audio files;
- smaller package/storage footprint;
- less authoring/review work;
- better cache reuse;
- cleaner localization/semantic behavior.

Generate Activity-specific dialogue only when the wording itself matters to the Activity.

Examples:

```text
"Ottimo!"                              -> shared praise when available
"Quasi, riproviamo!"                   -> shared retry when available
"Hai rimesso tutte le stelle nel cielo!" -> Activity-specific character dialogue
```

Do not copy shared WAV files into each Activity merely to make lookup convenient. Use the Greia-owned shared resource path/resolver contract.

---

## 9. Score, progress, Stars, medals and trophies

Every new Activity performs the mandatory design pass in `ACHIEVEMENTS.md`.

Keep these layers separate:

```text
Activity-local transient score/result
Activity-owned durable progress
trusted completion/milestone/score facts emitted to Greia
platform-owned Greia Stars / achievements / medals / trophies
```

The key authority rule remains:

> **The Activity reports facts. Greia decides global rewards.**

Therefore the same terminal child action may legitimately do both:

```text
show immediate local success
emit round.completed / score / milestone fact
```

but it must not additionally:

- increment the global Star balance itself;
- unlock a badge itself;
- decide bronze/silver/gold itself;
- draw an authoritative medal/trophy popup;
- play an audio cue claiming a global award that Greia has not granted.

Current global award presentation is Greia/Shell-owned. Do not create a parallel Activity achievement framework.

### Local celebration versus global award

A local completion celebration answers:

> "You finished this round/activity."

A Greia medal/trophy/Star answers:

> "Trusted platform policy granted a global reward based on recorded facts."

They may be related, but they are not the same event and must not be conflated in code or speech.

---

## 10. Terminal transitions should commit facts once

A completion path should have one authoritative state transition and one idempotent semantic event occurrence.

Do not let audio callbacks themselves award score or emit completion repeatedly.

Prefer:

```text
model applies final action once
-> terminal result object/state produced
-> local score/progress finalized
-> trusted fact emitted once with stable idempotency
-> presentation/audio expresses that already-decided result
```

If playback is interrupted or fails, gameplay/progression truth must not duplicate or disappear merely because a fanfare callback did not run.

Conversely, do not emit completion merely because a victory animation started; emit because the domain state actually completed.

---

## 11. Performance is part of feedback correctness

On Greia's Acer-class floor, slow feedback paths become timing bugs.

A 100–300 ms decode, scale, filesystem lookup or full-screen alpha reconstruction can reorder the experience enough that two cues that looked sequential on a developer machine overlap on device.

Mandatory rules:

- preload/decode reusable short sounds outside the interaction hot path;
- cache prepared audio resources with explicit bounds and lifecycle;
- never load a WAV/OGG from disk on every tap;
- never walk/stat asset directories on every playback;
- do not construct a new mixer/channel/worker/thread for every cue;
- keep pending speech/feedback queues bounded, normally one replaceable/coalesced pending semantic cue rather than an unlimited list;
- do not busy-poll audio completion at a high rate when an event/state callback or normal Activity tick can observe it cheaply;
- keep visual celebration bounded in area/duration; do not run a permanent full-screen translucent overlay over a live 30 Hz game;
- pre-render/cache stable celebration art and text;
- stop or reduce irrelevant continuous animation while a terminal result screen is static where product design permits;
- keep the input loop responsive while speech plays; never block the main loop on playback;
- cleanly stop Activity-owned sounds and release resources on lifecycle termination/Home.

Use `ENGINEERING.md` and `docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md` for the broader performance contract.

### Performance acceptance principle

Do not call a feedback timing fix complete because it sounds correct on a fast desktop.

Headless/source tests can prove state/ordering contracts. GUI Simulator review can prove semantic timing/comprehension. Acer/Pi performance claims require named physical evidence at the exact source SHA.

---

## 12. Design-time collision table

For every non-trivial Activity, write a tiny collision table before implementation or review the equivalent logic explicitly:

```text
trigger | routine feedback | terminal/special feedback | policy | progression fact
```

Example:

```text
collect normal apple
    collect chime + count word
    none
    routine
    optional meaningful milestone only if designed

collect final apple
    collect chime + final count word
    basket-complete celebration
    final count first; suppress routine chime if it masks speech; then one celebration
    basket.filled completion/milestone once

wrong answer while retry speech active
    retry reaction
    repeated retry reaction
    coalesce/replace
    none
```

The point is not paperwork. It forces the model to notice the exact edge where independent callbacks would conflict.

---

## 13. Required tests/review scenarios

For Activities with non-trivial feedback/audio, explicitly exercise at least:

```text
ordinary successful action
terminal successful action (last item / final answer / final piece)
wrong action
rapid repeated wrong actions
rapid repeated successful taps where legal
completion while another cue is active
replay/restart after completion
Home/stop while audio is active
all shipped locales whose clip lengths differ
```

Verify:

- the final pedagogical/required cue is intelligible and not cut off;
- routine and terminal SFX do not double-fire undesirably;
- no overlapping copies of the same character voice accumulate;
- progress/completion event emits exactly once;
- local score finalizes exactly once;
- no Activity-owned Star/medal/trophy authority appears;
- replay resets sequencing state cleanly;
- Home/stop leaves no Activity audio running;
- final/static states do not waste continuous CPU without product reason.

A model/unit test should cover terminal-vs-routine state selection. GUI review should cover actual perceived audio timing.

---

## 14. Authoring/review gate

Before accepting a new or materially changed Activity, answer all of these:

1. What semantic result does each important child action produce?
2. Which actions are terminal/special variants of a routine action?
3. Can one action currently trigger two spoken clips or SFX at the same time?
4. Which cue wins when pedagogical speech conflicts with praise/fanfare?
5. Are repeated equivalent reactions coalesced/replaced instead of queued indefinitely?
6. Is sequencing event/state-driven rather than dependent on guessed sleeps where possible?
7. Is there one clear owner for non-trivial playback arbitration?
8. Are shared `ready.go`, `praise.general`, `celebrate.success`, `encourage.retry`, `encourage.progress` families reused when the runtime resolver supports them?
9. Are canonical character introductions reused rather than duplicated?
10. Has the Activity avoided assuming a generic greeting family that does not exist?
11. Is local success presentation clearly distinct from platform-owned Stars/medals/trophies?
12. Are completion/score/milestone facts emitted once from semantic state, not from audio callbacks?
13. Are sound resources prepared/cached rather than decoded in interaction hot paths?
14. Are queues/caches/animations bounded?
15. Does the static/terminal presentation avoid unnecessary continuous repaint/large alpha work?
16. Were terminal-action, rapid-input, replay and Home-during-audio cases exercised?
17. Was final perceived timing reviewed in the GUI Simulator, and physical performance only claimed with physical evidence?

If these questions have not been answered, feedback orchestration is not complete even if every individual sound file is correct.