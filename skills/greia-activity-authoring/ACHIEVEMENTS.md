# Greia Activity Achievement and Reward Authoring

**Status:** mandatory specialist Activity guidance  
**Audience:** Activity authors, coding agents, reviewers  
**Reviewed:** 2026-08-24

Read this file completely whenever an Activity adds/changes completion, milestone or score events; participates in Greia Stars; or is being designed with badges/achievements in mind.

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

## 1. Non-negotiable authority rule

> The Activity reports facts. Greia decides rewards and achievements.

Activity code must never:

- award/unlock a badge directly;
- contain global achievement IDs as gameplay commands;
- write `achievements.json` or any profile progress authority;
- increment/decrement Greia Star balances;
- copy global badge policy into Activity storage;
- make gameplay correctness/difficulty depend on a global achievement;
- infer another child's/profile's progress.

There is intentionally no Activity `award_badge()` API.

An Activity **may optionally contribute decorative achievement emblems**. This does not grant achievement authority. Greia policy must explicitly admit each emblem before it appears in a global badge.

## 2. Design good semantic events

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

## 3. Manifest and implementation must agree exactly

Every emitted event ID must be declared in `activity.toml`.

Before using an event for progression/achievement policy, verify all three together:

```text
activity.toml declaration
Activity source emission
trusted history/progression/achievement consumer
```

Do not “fix” a rejected event by weakening the broker or adding wildcard policy. Repair the contract drift.

## 4. Event kinds

Use the existing manifest event vocabulary honestly:

```text
completion
creation
milestone
score
```

`score` is special. A score event must declare:

```toml
score_order = "higher_better"
```

or:

```toml
score_order = "lower_better"
```

and must emit a genuine numeric comparable score through `emit_activity_event(..., score=...)`.

Do not encode scores only inside free-form payload if Greia is expected to track a personal best.

## 5. Idempotency matters

One semantic occurrence must use a stable idempotency key for retries of that same occurrence.

Do not generate a new key merely because an emit call is retried after transport uncertainty. The trusted history store uses idempotency to prevent duplicate events, duplicate rewards and duplicate milestone counts.

## 6. Greia Stars

Activities never decide Star economics.

`runtime/progression-policy.toml` may choose to award a Star for an Activity fact. Current preferred pattern is at most one Star per qualifying Activity session for a meaningful completion/creation event.

Therefore Activity authors should emit the fact at the correct semantic moment and stop there.

Never add Activity-local code such as:

```python
stars += 1  # when this means the global Greia reward
```

Activity-local score/progress counters are fine when they are genuinely local gameplay state; do not present them as the authoritative Greia Star balance.

## 7. Achievement criteria are platform policy

Current Greia policy can derive milestones from:

```text
event_count
best_score
reward_balance
```

Multiple criteria are all-of.

The Activity does not need to know whether its event currently powers a badge. This is deliberate: Greia can introduce/rebalance non-gameplay milestone presentation without changing Activity code or allowing packages to define global reward economics.

## 8. Personal-best achievements

For a score milestone:

1. define a genuine score event;
2. declare `score_order` correctly;
3. emit the score value;
4. let history choose the personal best;
5. let platform achievement policy choose thresholds.

Examples:

```text
higher_better: 100 points → achievement comparison at_least 100
lower_better:  60 seconds → achievement comparison at_most 60
```

Never compare children to each other.

## 9. Avoid manipulative achievement inputs

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

## 10. Presentation belongs to Greia

An Activity may show its own immediate local success feedback, but global badge library state and presentation behavior are platform-owned.

Current system celebration is shown after the Activity returns to the Shell. A future trusted compositor may surface it immediately above an Activity. Do not create a second Activity-local achievement popup framework to work around that lifecycle.

In particular, do not reintroduce the performance anti-pattern of a live 30 Hz game underneath a full-screen translucent badge/victory overlay.

## 11. Localization is mandatory for child-facing achievement copy

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
empty-library/help copy
```

Rules:

- never hardcode English badge/library strings in an Activity;
- never use `if Italian else English` as the platform localization architecture;
- resolve badge copy from the active Greia profile/device locale;
- explicit Simulator/device launch locale must not be lost merely because an installed-language store is absent;
- use the platform fallback locale only when a requested translation is genuinely unavailable;
- raw localization keys must never reach the child UI;
- changing locale must not change achievement identity, unlock state, criteria or Star economics;
- **never bake words into an Activity-contributed badge emblem**: the emblem must remain language-neutral artwork.

## 12. Optional Activity-generated achievement art

Activities that want stronger visual identity may ship one or more **decorative emblems** based on their own characters, objects, environments or visual language.

V1 manifest syntax:

```toml
[achievement_art]
emblems = [
  { id = "activity", asset = "assets/icon.png" },
  { id = "first-rescue", asset = "assets/achievements/first-rescue.png" },
]
```

This declaration means only:

> “This package offers these safe pieces of artwork if Greia chooses to use them.”

It does **not** create achievements.

The platform-owned policy must explicitly admit the artwork:

```toml
[[achievements]]
id = "greia.care.first-friend"
category = "care"
tier = "bronze"
icon_id = "pink_heart" # trusted fallback
art = { activity_id = "org.greia.clinica-cuccioli", emblem_id = "activity" }
# localized copy + trusted criteria follow
```

### V1 emblem requirements

- PNG only;
- square;
- 32–1024 px on each side;
- at most 512 KiB compressed;
- transparent background strongly preferred;
- **256×256 is the recommended production size**;
- no child-facing text baked into the image;
- no badge tier words/numbers/rank claims;
- no animation;
- no executable/vector-script content;
- no path outside the Activity package;
- no symlink;
- artwork should read clearly when reduced to roughly 30–100 px.

The Activity creation workflow is encouraged to generate a purpose-made emblem from its own content rather than simply reusing its launcher icon when good art-generation tooling is available. Good examples include a recognizable patient/paw from Clinic, a bridge silhouette from Bridges, or a distinctive Memory card motif.

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

An Activity cannot choose a giant card, fullscreen image, custom popup, custom frame implementation or global reward behavior.

### Fail-soft rendering

`icon_id` remains mandatory as a trusted semantic fallback. If admitted Activity artwork cannot decode at presentation time, Greia renders the platform icon and achievement truth remains unchanged.

## 13. Award visual language

The Greia frame stays reusable and coherent across Activities:

```text
bronze / silver -> medal + ribbons
gold            -> trophy cup
special/secret  -> richer rosette / constellation treatment
```

Activity art lives **inside** that Greia frame. This gives the child both signals at once:

```text
“This came from Clinica Cuccioli”
AND
“This is a Greia achievement”
```

Runtime award art must stay bounded and cached. Greia source masters live under:

```text
assets/source/achievements/
```

Activity-specific source art belongs in that Activity's own asset tree.

## 14. Activity-local collectibles are a separate future concept

Do not overload global Greia achievements with every reward an Activity may want.

A future Activity-local collection/album system may support much freer things such as:

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

## 15. Review checklist

Before accepting achievement-relevant Activity or platform changes, verify:

- [ ] emitted IDs exist in manifest exactly;
- [ ] event kind matches semantics;
- [ ] score events have correct `score_order` and numeric `score` emission;
- [ ] repeated transport cannot duplicate the semantic event;
- [ ] no Activity code writes global rewards/achievements;
- [ ] no badge ID is needed for Activity gameplay;
- [ ] event frequency is bounded/meaningful;
- [ ] event identity is language-independent;
- [ ] progression policy, if changed, references a real declared event;
- [ ] achievement policy, if changed, references a real declared event/score/reward;
- [ ] achievement title/description/hint have required locale parity;
- [ ] Badge Library and celebration use the active Greia locale rather than hardcoded English;
- [ ] Activity achievement art is optional and decorative only;
- [ ] Activity emblem PNG passes path/type/size/dimension validation;
- [ ] Activity emblem contains no localized words;
- [ ] global policy explicitly admits the Activity emblem;
- [ ] platform `icon_id` fallback remains valid;
- [ ] child-facing reward design avoids grind/comparison/manipulation;
- [ ] award rendering remains bounded/cached and does not add fullscreen alpha work;
- [ ] provider-free tests cover factual events and art admission boundaries;
- [ ] Simulator acceptance verifies the child-visible semantic moment and themed artwork.
