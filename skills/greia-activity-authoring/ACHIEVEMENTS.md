# Greia Activity Achievement and Reward Authoring

**Status:** mandatory specialist Activity guidance  
**Audience:** Activity authors, coding agents, reviewers  
**Reviewed:** 2026-08-23

Read this file completely whenever an Activity adds/changes completion, milestone or score events; participates in Greia Stars; or is being designed with badges/achievements in mind.

Primary design authority:

```text
docs/design/GREIA_ACHIEVEMENTS_AND_BADGE_LIBRARY.md
runtime/achievement-policy.toml
runtime/progression-policy.toml
src/greia_platform/history.py
src/greia_platform/achievements.py
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

An Activity may show its own immediate local success feedback, but global badge art/library state is platform-owned.

Current system celebration is shown after the Activity returns to the Shell. A future trusted compositor may surface it immediately above an Activity. Do not create a second Activity-local achievement popup framework to work around that lifecycle.

In particular, do not reintroduce the performance anti-pattern of a live 30 Hz game underneath a full-screen translucent badge/victory overlay.

## 11. Review checklist

Before accepting achievement-relevant Activity changes, verify:

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
- [ ] child-facing reward design avoids grind/comparison/manipulation;
- [ ] provider-free tests cover the factual event transition;
- [ ] Simulator acceptance verifies the event occurs at the child-visible semantic moment.
