# Greia Awards, Badges, Celebrations, and Collection — Product Requirements

**Status:** accepted product direction; Shell badge subset implemented (SOURCE + DESKTOP VISUAL REVIEW, 2026-10-16) — see §23; new-best, chime, spoken names, backup export and Parent view still pending  
**Date:** 2026-08-17  
**Architecture owner:** ADR 0025  
**Progression foundation:** ADR 0017  
**Audience:** Greia Shell designers, platform developers, Activity authors, parent-client developers, reviewers, and agents

## 1. Purpose

Greia should make meaningful achievement feel visible, joyful, and memorable to a young child.

When a child completes something important, earns a badge, or genuinely improves a score, Greia should acknowledge it with a polished platform-owned celebration and preserve the result in the child's personal collection.

This is not a game-local feature. It is part of the Greia operating experience.

The product goal is:

> **Activities provide the challenge and report what happened. Greia recognizes progress, grants durable awards, celebrates them consistently, and gives the child a beautiful place to revisit what they have achieved.**

The system must work offline, across Activity runtimes, across supported hardware, and across backup/restore. It must not depend on advertising, cloud accounts, purchases, daily-login pressure, or Activity-specific persistence tricks.

## 2. Relationship to existing progression

Greia already has the correct authority model through ADR 0017:

- the supervisor owns Activity sessions;
- Activities emit declared factual events;
- Greia validates those events;
- Greia compares scores according to declared `higher_better` / `lower_better` semantics;
- Greia owns best-score aggregates;
- Greia owns global reward policy and the reward ledger;
- Activities cannot directly modify global progression.

Awards and celebrations extend that model; they do not replace it.

Conceptually:

```text
Activity session
      │
      ├── completion event
      ├── factual milestone event
      └── score/result
              │
              ▼
       Greia progression
              │
      ┌───────┼──────────┐
      ▼       ▼          ▼
 best score  reward    award/badge
             ledger      ledger
                           │
                   celebration request
                           │
                           ▼
                Greia child presentation
                           │
                  ┌────────┴────────┐
                  ▼                 ▼
             celebration      badge collection
```

## 3. Product vocabulary

The UI may use simple child-facing words, but implementation and documentation should keep these concepts distinct.

### Reward

A quantity or balance managed by Greia, for example a star.

Rewards may later feed bounded Greia-owned customization or unlock systems. They are not the same thing as badges.

### Award

A durable achievement earned by a child profile.

A badge is the initial visual form of an Award. Future award presentation may include medals, stickers, trophies, shelf objects, or other collectible metaphors without changing the underlying authority model.

Examples:

- First Painting
- Maze Master
- Perfect Run
- Creative Spark
- Curious Explorer

### Celebration

A short transient acknowledgement shown by Greia.

Examples:

- `NEW BEST!`
- a badge reveal;
- a sparkle/confetti animation;
- a short musical sting;
- optional spoken praise;
- a badge flying toward the collection icon.

A celebration may occur without a new permanent badge, especially when a child improves a personal best.

### Collection

The Greia-owned child-facing place where the profile's durable Awards can be revisited.

The visual metaphor may be a badge book, sticker album, treasure cabinet, trophy shelf, magical collection, or integrated place in the Greia world. The product requirements below apply regardless of metaphor.

## 4. Core child journeys

### 4.1 Completing a meaningful goal

A typical experience should be:

```text
child completes meaningful challenge
        ↓
Activity reports factual completion
        ↓
Greia validates and records it
        ↓
award rule becomes satisfied
        ↓
award is durably granted
        ↓
Greia presents a short celebration at a safe moment
        ↓
child continues or opens collection
```

The child should experience one coherent Greia celebration even though the underlying Activity may be Python, Web, or another future runtime.

### 4.2 Improving a personal best

A typical experience:

```text
old best: 870
new result: 930
score direction: higher_better
        ↓
Greia determines genuine improvement
        ↓
best score is updated
        ↓
Greia may show "NEW BEST!" celebration
```

For a time-based Activity:

```text
old best: 48 seconds
new result: 42 seconds
score direction: lower_better
        ↓
Greia determines genuine improvement
```

The Activity must not duplicate this comparison logic.

A personal-best improvement normally does **not** create a new permanent badge every time. Specific milestones may grant badges separately.

### 4.3 Several awards becoming true together

One event may satisfy more than one rule.

Greia must avoid a barrage of overlapping or sequential interruptions such as five popups and five sound effects.

The presentation scheduler should group, order, or defer celebrations so the result feels special rather than noisy.

The durable grants happen independently from presentation; presentation coalescing must not lose awards.

### 4.4 Award earned during unsafe gameplay

If the child earns something while:

- holding a drawing gesture;
- steering a character;
- solving a timed puzzle;
- interacting with a moving object;
- entering text;
- or otherwise using a state where an overlay would cause failure or confusion,

Greia records the award immediately but waits for an appropriate presentation moment.

Possible safe moments include a round-complete state, Activity transition, or return to Shell. The exact safe-point API/mechanism is an implementation detail; the product rule is that celebration must never sabotage the child's current task.

### 4.5 Activity later removed

A child earns a badge from an Activity and the parent later uninstalls that Activity.

Expected result:

- the badge remains in the child's collection;
- the child can still recognize/view it;
- its source can be shown in child-friendly terms where useful;
- no Linux path/package error appears;
- reinstalling the Activity reconnects to the same stable Activity/award identities.

### 4.6 Backup restored to another machine

A child earns awards on an old i386 Greia machine, the family creates a `.greiabackup`, and restores it onto ARM64.

Expected result:

- all earned award identities survive;
- collection presentation remains meaningful even if some originating Activities are not yet installed;
- no architecture-specific serialized state is required;
- no cloud account is required.

## 5. What should be rewarded

Greia should use awards to reinforce intrinsically useful experiences, not merely usage volume.

Good categories include:

### Mastery

Examples:

- finish a beginner set;
- complete a meaningful level series;
- solve a difficult challenge;
- achieve a well-defined skill milestone.

### Improvement

Examples:

- reach a significant personal-best threshold;
- improve in several different Activities;
- demonstrate increasing accuracy or efficiency where the Activity provides meaningful evidence.

### Creation

Examples:

- save a first painting;
- complete a story;
- create music;
- build a project;
- produce meaningful work in several creative Activities.

### Curiosity and exploration

Examples:

- meaningfully try several different kinds of Activities;
- complete experiences across science, art, music, puzzles, or other categories;
- discover a new tool or concept.

### Persistence through genuine challenge

Where an Activity can report this safely and meaningfully, Greia can celebrate completing a challenge after multiple attempts or overcoming a difficult step.

This must not become a mechanic that manufactures frustration merely to award persistence afterward.

### Cross-Activity accomplishments

Greia itself can recognize patterns no individual Activity can know, such as:

- **Creative Spark** — create something in several creative Activities;
- **Curious Explorer** — meaningfully use Activities from several areas;
- **Getting Better** — improve personal bests in multiple Activities;
- **Puzzle Friend** — complete puzzle milestones across multiple Activities.

Cross-Activity rules are Greia-owned.

## 6. What should not be rewarded

Greia is for young children. The achievement system must not become a behavioral-retention machine.

Core Greia policy must avoid:

- daily-login streaks whose loss causes anxiety;
- expiring earned badges;
- `return tomorrow or lose this reward` mechanics;
- paying to obtain achievement badges;
- watching adverts to obtain badges or rewards;
- artificial scarcity/FOMO around ordinary progression;
- global/public leaderboards by default;
- endless grind where the real criterion is screen time;
- rewards for simply keeping Greia open for long periods;
- dark-pattern notifications designed to pull the child back into the device;
- child-facing purchase prompts triggered by achievements.

The official catalogue may apply corresponding rules to third-party Activity achievement design.

## 7. Activity-specific awards

Third-party and first-party Activities should eventually be able to participate without Greia OS requiring a code update for every new badge.

The intended model is declarative.

An Activity package may define a bounded catalogue of Activity-specific Awards whose earning rules bind only to validated evidence from that Activity.

Conceptually:

```text
Activity: org.greia.maze

Awards:
  first-maze
    visual: badge
    evidence: maze.completed milestone

  perfect-run
    visual: badge
    evidence: validated perfect_run event

  maze-master
    visual: badge
    evidence: platform aggregate over declared Activity facts
```

This example communicates semantics only. The exact future package schema remains source-owned when implemented.

Important boundaries:

- runtime code does not call `grant_badge()`;
- arbitrary event payload fields do not grant awards;
- an Activity cannot define Greia-wide awards;
- an Activity cannot mutate another Activity's award state;
- an Activity cannot award global currency/rewards by embedding deltas in badge metadata;
- package award assets/metadata are validated and bounded;
- network-hosted badge artwork is not required for normal operation.

## 8. Greia-wide awards

Greia can define awards based on platform-wide evidence such as:

- number/categories of Activities meaningfully completed;
- creations saved across several Activities;
- personal best improvements across Activities;
- broad exploration or progression milestones;
- future child-safe platform customization milestones.

These rules belong to Greia policy because Greia alone owns authoritative cross-Activity history.

Activities must not be able to manufacture the evidence by writing another Activity's state or global progression records.

## 9. Celebration experience

### 9.1 It should feel special

A badge should not appear as a desktop toast notification.

The visual treatment should be playful, physical, and collectible. Possible metaphors include:

- enamel pin;
- embroidered patch;
- magical sticker;
- medal;
- wooden token;
- jewel;
- constellation;
- small character/object;
- trophy.

The exact art direction can evolve independently from the award authority model.

### 9.2 Typical presentation sequence

A good sequence could be:

```text
small sparkle / anticipation
        ↓
award appears, assembles, spins, or unfolds
        ↓
short celebratory sound and visual effect
        ↓
large badge/title presentation
        ↓
optional spoken name
        ↓
badge visually joins the child's collection
        ↓
continue / inspect collection
```

The duration should be short enough not to trap the child and should remain responsive to Greia-owned navigation/input.

### 9.3 New-best presentation

A personal-best celebration can be lighter than a badge ceremony:

```text
✨ NEW BEST! ✨
930
```

or a similarly visual child-friendly treatment.

It should clearly celebrate improvement without implying that every score lower than the best is failure.

### 9.4 Input ownership

The official Greia celebration surface is platform-owned.

It must not:

- disable or cover the real Home/Back route;
- hand trusted system input to Activity content;
- require the Activity to draw the official badge popup;
- become an arbitrary notification/window layer available to Activities.

### 9.5 Sound and speech

Audio enhances celebration but must not be required.

A celebration should communicate success visually when muted or when the child cannot hear it.

Where speech support exists, Greia may speak a localized phrase such as:

> “You earned Puzzle Friend!”

Speech wording must be child-positive and concise.

## 10. The collection experience

Every profile needs an obvious child-facing route to its earned Awards.

This is not a parent settings table or a desktop-style achievements list.

### 10.1 Visual-first design

The primary surface should use:

- large badge artwork;
- generous spacing;
- clear grouping;
- large selection targets;
- minimal mandatory reading;
- predictable input across pointer/touch/keyboard/controller where supported.

A child should be able to enjoy browsing the collection even before reading fluently.

### 10.2 Inspecting an award

Selecting one award should show a focused large presentation with information such as:

```text
[large badge]

PUZZLE FRIEND

You solved 10 puzzles!

Maze Adventure
Earned Sunday
```

The exact wording/metadata can be simplified for younger children and localized.

Optional speech may read the award name and explanation.

Technical information such as package version, Activity ID, ledger row, or database key must not appear in normal child UI.

### 10.3 Avoid shame-oriented collection UI

Greia should be cautious about prominent completion fractions such as:

```text
23 / 100 badges
```

when the primary effect is to make a young child feel they are missing dozens of things.

Progress/group completion can be shown where genuinely useful, but the collection should feel like **“look what I have discovered and achieved”**, not a deficit dashboard.

### 10.4 Missing/uninstalled source Activity

The badge remains visible.

Greia may use a stable stored snapshot/fallback icon and a friendly source label. It must not show broken image placeholders or filesystem errors.

## 11. Profile identity and Greia world integration

Awards should eventually be usable as part of the child's identity and Greia environment, without making the collection competitive between children.

Possible future uses include:

- choose a favorite badge beside the profile avatar;
- pin badges in a personal room/workshop;
- place earned trophy objects on a shelf;
- unlock a child-safe decorative item;
- decorate profile cards with earned symbols.

These consequences remain platform-owned Greia policy.

An Activity event never receives direct authority to mutate Shell/world state.

## 12. Multi-profile behavior

Awards belong to the active child profile.

If Greta earns `Maze Master`, Gaia does not automatically receive it merely because both use the same machine or Activity installation.

The platform must scope:

- award grants;
- collection;
- best scores;
- related rewards;
- customization consequences;
- backup/restore

to the correct Greia profile.

Normal child UI must not turn sibling profiles into a ranking/leaderboard by default.

## 13. Persistence and uninstall semantics

Earned Awards are platform progression data, not Activity save files.

Therefore:

- uninstalling an Activity preserves awards;
- clearing/reinstalling an Activity package does not silently remove awards;
- deleting Activity save data is conceptually separate from deleting platform award history;
- restoring a backup can restore awards before the Activity itself is installed;
- stable Activity/award IDs reconnect future installs to prior history.

If future parent controls allow deliberately clearing progression, the action must be explicit, appropriately broad/narrow, and clearly separated from normal uninstall.

## 14. Backup and portability

The award collection is part of portable child identity/progression and must be included in the future logical `.greiabackup` model.

The export must preserve enough information to retain a meaningful collection on another Greia machine even if the originating Activity package is absent.

Do not serialize architecture-specific Python/native objects or copy internal SQLite bytes as the official backup contract.

## 15. Parent experience

Greia Parents may eventually show a bounded summary such as recent Awards or collection counts for a child, provided this is useful and respectful.

Parent UI should not be needed for the child to receive or browse awards.

Normal parent controls should not include a `grant arbitrary badge` button. Awards should represent real progression evidence.

A future developer/test tool may inject controlled fixtures in developer environments, but that is not product authority and must not leak into release behavior.

## 16. Accessibility and language

The system must be usable by children who cannot yet read, children using different languages, and children who do not rely on sound.

Requirements include:

- distinctive visual badge art;
- localized text where text appears;
- optional spoken title/explanation where supported;
- no audio-only success state;
- sufficiently large controls;
- support for future reduced-motion accessibility policy without removing the achievement itself;
- no reliance on color alone to distinguish earned/unearned state.

## 17. Performance and low-resource requirements

Awards are delightful only if they do not make Greia sluggish.

On low-resource hardware:

- animations should use bounded/simple assets and effects;
- award artwork caches must be bounded;
- pending celebration queues must be bounded;
- collection paging/rendering must not decode every award asset every frame;
- no network call is required to grant or show a normal badge;
- no heavyweight browser/3D engine is required solely for award presentation;
- transient objects/particles must be bounded;
- static collection UI should redraw on change rather than waste CPU where practical.

The visual ambition should scale to the hardware while preserving the same award identity and child experience.

## 18. R7 display/session requirement

The selected production display/session design must account for Greia-owned transient celebration presentation.

This does **not** mean Greia needs a desktop notification manager.

The required capability is narrowly scoped:

```text
Greia display/session/input authority
├── mandatory Home / context Back
├── protected system input
├── bounded transient Greia celebration surface OR safe platform transition presentation
└── Activity surface
```

A backend may present the celebration above Activity content when safe and inexpensive, or defer it to a safe Greia-controlled transition. What it may not do is force each Activity runtime to own the authoritative award UI.

ADR 0025 owns this architecture requirement.

## 19. Activity-author guidance

An Activity author should think in terms of **facts worth reporting**, not platform rewards worth granting.

Good:

```text
level.completed
painting.saved
puzzle.solved
perfect_run.completed
score.submitted
```

Bad:

```text
give_child_10_stars
unlock_global_hat
set_badge_earned
award_cross_activity_trophy
```

If the future package format allows Activity-specific award definitions, those definitions remain declarative and validated by Greia.

Authors may still show ordinary local feedback inside their own game, but Greia owns the authoritative system badge ceremony and collection.

## 20. Example initial award set

These are examples for design discussion, not frozen IDs or launch requirements.

### Greia-wide

- **First Adventure** — complete a first meaningful Activity goal.
- **Creative Spark** — save creations in several creative Activities.
- **Curious Explorer** — meaningfully engage with several Activity categories.
- **Getting Better** — improve personal bests in several different Activities.
- **Puzzle Friend** — complete puzzle milestones across multiple Activities.

### Activity-specific

A maze Activity might define:

- **First Maze**
- **Perfect Path**
- **Maze Master**

A painting Activity might define:

- **First Painting**
- **Color Explorer**
- **Little Artist**

The final set should be designed with restraint. A small number of meaningful badges is better than hundreds of meaningless ones.

## 21. Acceptance principles

The complete feature should eventually prove at least:

- validated event/score evidence can grant an award exactly once;
- retry/idempotency cannot duplicate the award;
- Activity payloads cannot forge award authority;
- higher/lower-best score semantics produce correct `New Best` behavior;
- award grant survives process crash before presentation;
- celebration presentation does not compromise Home/Back or Activity input safety;
- multiple simultaneous celebrations are bounded/coalesced sensibly;
- collection is profile-scoped;
- awards survive Activity uninstall;
- logical backup/restore preserves awards with the source Activity absent;
- Python/Web runtimes use the same platform semantics;
- child UI is visual, readable at 1024×600, and does not expose Linux internals;
- queue/cache/asset behavior is bounded on the C0/Acer floor;
- no network, advertising, purchase, or streak dependency exists in core award granting.

## 22. Non-goals for the first implementation

Do not turn this requirement into a giant gamification framework.

The first implementation does not need:

- public leaderboards;
- social feeds;
- cloud achievement sync accounts;
- rarity markets;
- trading;
- purchasable badges;
- animated 3D trophy rooms;
- hundreds of award classes;
- complex rule scripting exposed to Activities;
- a desktop notification subsystem.

A strong first slice is enough:

```text
trusted evidence
→ durable once-only badge grants
→ personal-best celebration
→ bounded Greia presentation
→ simple beautiful collection
→ logical backup hooks
```

Everything else should grow from demonstrated child/product needs.

## 23. Implemented subset (2026-10-16)

Evidence class: SOURCE + DESKTOP VISUAL REVIEW only (headless renders). No Simulator, VM or physical review yet.

- **Celebration (§9.2):** after an Activity returns, the badge card scales in, the badge overshoots and settles, sparkles appear (gold/secret: star bursts and confetti), the child's greeter reacts and says one accepted shared `celebrate.success` line (first badge of a return only; never interrupts other speech). The card then waits, completely still, for a tap or key. On dismiss the badge flies into the Home star, the star bounces and its count goes up — this teaches pre-readers what the star is for. Further badges from the same return get a shorter intro and no voice.
- **Collection (§10):** a "trophy shelf" on the child's meadow: two wooden shelves of four badges, locked badges as grey tier silhouettes with a padlock, secret badges absent, a sparkle on newly earned badges, the unlocked count as a star pill with **no denominator**. Tapping a badge makes it hop; the greeter says `praise.general` (earned) or `encourage.progress` (locked), at most once every 3 s. A detail strip shows the title and one line.
- **Navigation:** the Home star is part of the keyboard/controller focus cycle (Up from the top portal row, or Tab after the last portal); Enter/south opens the shelf; arrows move, Enter makes the badge hop, Esc/Back returns.
- **Catalogue:** 15 badges; bronze is always "the first time" so the first badge can arrive in the first session (garden, postcard, voice story, concert, maze, dragon flight, patient, memory game), silver adds a little persistence (10 patients, 5 memory games, 3 bridges, 15 maze stars, 15 pearls in one dolphin journey), one secret gold (20 Greia Stars). Nothing is derived from usage time, streaks or Home taps.

