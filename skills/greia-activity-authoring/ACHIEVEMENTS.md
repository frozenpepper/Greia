# Greia Activity Achievement, Progress, Score and Reward Authoring

**Status:** mandatory specialist Activity guidance  
**Audience:** Activity authors, coding agents, reviewers  
**Reviewed:** 2026-10-30

Read this file completely for **every new Activity design**, and whenever an Activity adds/changes local progress, score, completion/milestone events, Greia Stars, badges/achievements, trophy presentation, or achievement artwork.

Primary design authority:

```text
docs/design/GREIA_ACHIEVEMENTS_AND_BADGE_LIBRARY.md
docs/design/GREIA_ACTIVITY_ACHIEVEMENT_ART.md
runtime/achievement-policy.toml
runtime/progression-policy.toml
src/greia_platform/history.py
src/greia_platform/achievements.py
src/greia_platform/achievement_art.py
src/greia_launcher/achievement_localization.py
```

## 1. Mandatory progress/reward design pass for every new Activity

A new Activity must explicitly decide all of these, even when the answer is `none`:

```text
LOCAL_SESSION_SCORE=
DURABLE_ACTIVITY_PROGRESS=
COMPLETION_EVENT=
MILESTONE_EVENTS=
PERSONAL_BEST_SCORE_EVENT=
GREIA_STAR_ELIGIBILITY=
GLOBAL_ACHIEVEMENT_OPPORTUNITIES=
ACTIVITY_ACHIEVEMENT_EMBLEM=
```

Do not accidentally omit progression because the first implementation focuses only on gameplay and visuals.

Do not invent a score merely because games usually have one. Open-ended creative/sensory Activities may legitimately have no numeric score. In those cases, meaningful completion/creation/milestone facts are usually better.

Likewise, not every Activity needs its own global badge. The important requirement is to expose truthful semantic facts so Greia can remember meaningful progress now or later without rewriting Activity code.

## 2. Keep the four authority layers separate

Agents must not collapse these concepts:

### A. Activity-local transient state

Examples:

```text
current round
current points in this play session
lives/tries when product-appropriate
level currently being played
combo or temporary challenge state
```

This is ordinary gameplay state. It may disappear when the session ends unless there is a reason to persist it.

### B. Activity-owned durable progress/save state

Examples:

```text
highest Activity-local level reached
saved creation/document
unlocked local puzzle set
bounded Activity-specific history
child's current Activity-local options/state
```

Persist this only through Greia's approved Activity storage APIs. Do not write arbitrary profile/global files.

Durable Activity progress is **not** the global badge store and is **not** the Greia Star balance.

### C. Trusted Greia history/progression facts

Examples:

```text
activity completed
patient healed
bridge finished
creation completed
round score = 125
personal best score/time
meaningful milestone count
```

The Activity declares and emits these semantic facts. Greia's event/history layer validates and records them idempotently.

This layer is what platform progression and achievement policy may consume.

### D. Global Greia rewards and achievements

Examples:

```text
Greia Stars
global achievement unlocked
bronze/silver medal
gold trophy
special/secret rosette
Badge Library state
NEW/seen/announced state
```

These are platform-owned. The Activity never grants, stores or authoritatively renders them itself.

A **trophy is not a separate Activity-owned reward authority**. In the current Greia visual language, a gold-tier global achievement is presented with a trophy cup; bronze/silver use medals, and special/secret achievements use richer rosette/constellation treatment.

## 3. Non-negotiable authority rule

> The Activity reports facts. Greia decides rewards and achievements.

Activity code must never:

- award/unlock a badge directly;
- award a trophy directly;
- contain global achievement IDs as gameplay commands;
- write `achievements.json` or any profile progress authority;
- increment/decrement Greia Star balances;
- copy global badge policy into Activity storage;
- make gameplay correctness/difficulty depend on a global achievement;
- infer another child's/profile's progress.

There is intentionally no Activity `award_badge()` or `award_trophy()` API.

An Activity **may optionally contribute decorative achievement emblems**. This does not grant achievement authority. Greia policy must explicitly admit each emblem before it appears in a global badge/trophy frame.

## 4. Scores: use them only when they mean something

A score should represent a meaningful comparable result for the child's **own** performance.

Good examples:

```text
number of correct targets in a bounded round
points earned from meaningful successful actions
elapsed completion time when speed is genuinely part of the skill
accuracy percentage when the domain makes it understandable and useful
```

Bad examples:

```text
raw clicks
minutes left open
number of animations triggered
arbitrary points added only to make the screen look game-like
```

If a score is only useful inside the current session, it may remain local Activity state.

If Greia should remember a personal best, emit a genuine `kind = "score"` event with numeric `score` and correct ordering:

```toml
score_order = "higher_better"
```

or:

```toml
score_order = "lower_better"
```

Do not encode the comparable score only inside free-form payload.

Never compare children to each other. No sibling/global leaderboards, ranks or percentiles.

## 5. Design good semantic events

Achievement-worthy Activities need high-quality factual events even when no badge exists yet.

Good examples:

```text
round.completed
patient.healed
puzzle.solved
creation.completed
course.finished
round.score
```

Poor examples:

```text
button.clicked
particle.spawned
screen.opened
mouse.moved
confetti.played
```

A semantic event should describe something Greia can truthfully remember independently of the Activity's current UI implementation.

## 6. Manifest and implementation must agree exactly

Every emitted event ID must be declared in `activity.toml`.

Before using an event for progression/achievement policy, verify all three together:

```text
activity.toml declaration
Activity source emission
trusted history/progression/achievement consumer
```

Do not “fix” a rejected event by weakening the broker or adding wildcard policy. Repair the contract drift.

## 7. Event kinds

Use the existing manifest event vocabulary honestly:

```text
completion
creation
milestone
score
```

`score` is special and follows section 4.

Use `completion` for a meaningful finished Activity/challenge/session semantic moment, not for every minor action.

Use `creation` when the child actually completes/commits a meaningful creative result.

Use `milestone` for meaningful intermediate accomplishments that Greia may reasonably remember independently.

## 8. Idempotency matters

One semantic occurrence must use a stable idempotency key for retries of that same occurrence.

Do not generate a new key merely because an emit call is retried after transport uncertainty. The trusted history store uses idempotency to prevent duplicate events, duplicate rewards and duplicate milestone counts.

## 9. Greia Stars

Activities never decide Star economics.

`runtime/progression-policy.toml` may choose to award a Star for an Activity fact. Current preferred pattern is at most one Star per qualifying Activity session for a meaningful completion/creation event.

Therefore Activity authors should emit the fact at the correct semantic moment and stop there.

Never add Activity-local code such as:

```python
stars += 1  # when this means the global Greia reward
```

Activity-local score/progress counters are fine when they are genuinely local gameplay state; do not present them as the authoritative Greia Star balance.

## 10. Achievement criteria are platform policy

Current Greia policy can derive milestones from:

```text
event_count
best_score
reward_balance
```

Multiple criteria are all-of.

The Activity does not need to know whether its event currently powers a badge. This is deliberate: Greia can introduce/rebalance non-gameplay milestone presentation without changing Activity code or allowing packages to define global reward economics.

## 11. Personal-best achievements

For a score milestone:

1. define a genuine score event;
2. declare `score_order` correctly;
3. emit the score value;
4. let history choose the personal best;
5. let platform achievement policy choose thresholds.

Examples:

```text
higher_better: 100 points -> achievement comparison at_least 100
lower_better:  60 seconds -> achievement comparison at_most 60
```

Never compare children to each other.

## 12. Avoid manipulative achievement inputs

Do not design events primarily to make a reward loop more addictive.

Avoid proposing achievements for:

- daily streaks;
- missed-day penalties;
- raw click/action counts;
- AFK time;
- arbitrary enormous repetition counts;
- purchases/installations;
- sibling/global rank;
- failures or embarrassing outcomes.

Prefer curiosity, care, creativity, exploration, persistence and real mastery.

## 13. Presentation belongs to Greia

An Activity may show its own immediate local success feedback, including its local points/result/progress, but global badge/trophy library state and presentation behavior are platform-owned.

Current system celebration is shown after the Activity returns to the Shell. A future trusted compositor may surface it immediately above an Activity. Do not create a second Activity-local achievement popup framework to work around that lifecycle.

Do not fake a global trophy by drawing a trophy and claiming it was earned before Greia trusted policy says so.

In particular, do not reintroduce the performance anti-pattern of a live 30 Hz game underneath a full-screen translucent badge/victory overlay.

## 14. Localization and pre-reader presentation

Achievement/event identifiers are stable machine identifiers and remain language-neutral. Human-facing achievement presentation does not.

Platform achievement definitions must keep localized child-facing fields together:

```text
title
description
locked_hint
```

The Shell owns localized achievement-library chrome such as:

```text
My Badges / I miei distintivi
New / Nuovo
New Badge! / Nuovo distintivo!
```

Rules:

- never hardcode English badge/library strings in an Activity;
- resolve badge copy from active Greia locale;
- changing locale must not change achievement identity, unlock state, criteria or Star economics;
- never bake words into an Activity-contributed badge emblem;
- the visual award object/icon must remain understandable and celebratory for a child who cannot read; text is descriptive support, not the only signal that something was earned.

## 15. Optional Activity-generated achievement art

Activities that want stronger visual identity may ship one or more **decorative emblems** based on their own characters, objects, environments or visual language.

V1 manifest syntax:

```toml
[achievement_art]
emblems = [
  { id = "activity", asset = "assets/icon.png" },
  { id = "first-rescue", asset = "assets/achievements/first-rescue.png" },
]
```

This means only:

> This package offers these safe pieces of artwork if Greia chooses to use them.

It does **not** create achievements.

The platform-owned policy must explicitly admit the artwork.

### V1 emblem requirements

- PNG only;
- square;
- 32–1024 px on each side;
- at most 512 KiB compressed;
- transparent background strongly preferred;
- **256×256 recommended**;
- no child-facing text baked into the image;
- no badge tier words/numbers/rank claims;
- no animation;
- no executable/vector-script content;
- no path outside the Activity package;
- no symlink;
- readable at roughly 30–100 px.

The Activity creation workflow is encouraged to generate a purpose-made emblem from its own content rather than simply reusing its launcher icon when good art-generation tooling is available.

### What Greia still owns

Even when Activity art is admitted, Greia still owns:

```text
achievement ID and meaning
unlock criteria
trusted event/history evaluation
bronze/silver/gold/special tier
medal/trophy/rosette frame
locked silhouette
secret visibility
localized title/description/hint
NEW/review state
celebration behavior
profile persistence
library layout
```

An Activity cannot choose global reward behavior or create its own authoritative award UI.

## 16. Award visual language

The Greia frame stays reusable and coherent across Activities:

```text
bronze / silver -> medal + ribbons
gold            -> trophy cup
special/secret  -> richer rosette / constellation treatment
```

Activity art lives **inside** that Greia frame.

Runtime award art must stay bounded and cached. Greia source masters live under:

```text
assets/source/achievements/
```

Activity-specific source art belongs in that Activity's own asset tree.

## 17. Activity-local collectibles are a separate future concept

Do not overload global Greia achievements with every reward an Activity may want.

A future Activity-local collection/album system may support things such as:

```text
stickers
postcards
saved patients
creations
characters discovered
blueprints
scene souvenirs
```

Those are not global Greia achievement authority and should have their own storage/presentation contract when implemented.

## 18. Review checklist

Before accepting a new Activity or reward/progress-related Activity change, verify:

- [ ] the mandatory progress/reward design pass is recorded;
- [ ] local session score is meaningful or deliberately absent;
- [ ] durable Activity progress uses approved Activity storage, if any;
- [ ] emitted IDs exist in manifest exactly;
- [ ] event kind matches semantics;
- [ ] score events have correct `score_order` and numeric `score` emission;
- [ ] repeated transport cannot duplicate the semantic event;
- [ ] no Activity code writes global rewards/achievements;
- [ ] no Activity code awards badges/trophies directly;
- [ ] no badge ID is needed for Activity gameplay;
- [ ] event frequency is bounded/meaningful;
- [ ] event identity is language-independent;
- [ ] progression policy, if changed, references a real declared event;
- [ ] achievement policy, if changed, references a real declared event/score/reward;
- [ ] achievement title/description/hint have required locale parity;
- [ ] Activity achievement art is optional and decorative only;
- [ ] Activity emblem PNG passes path/type/size/dimension validation;
- [ ] Activity emblem contains no localized words;
- [ ] global policy explicitly admits the Activity emblem;
- [ ] platform fallback icon remains valid;
- [ ] child-facing reward design avoids grind/comparison/manipulation;
- [ ] award rendering remains bounded/cached;
- [ ] provider-free tests cover factual events and art admission boundaries;
- [ ] Simulator acceptance exercises the actual completion/score/milestone path and immediate child-visible local feedback.
