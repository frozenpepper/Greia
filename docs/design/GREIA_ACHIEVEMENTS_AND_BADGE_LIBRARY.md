# Greia Achievements and Badge Library

**Status:** active shared design and implementation contract  
**Date:** 2026-08-23  
**Audience:** Greia platform maintainers, Activity authors, simulator/test authors

## 1. Purpose

Greia achievements should make a child feel that the system **remembers meaningful things they have done**.

They are not a leaderboard, a productivity system, a daily-retention mechanic, or another score counter.

The feature has three child-facing jobs:

1. **celebrate** a meaningful new milestone;
2. **remember** that milestone durably as part of the child's profile;
3. **invite reflection/exploration** through a simple library of earned and attainable badges.

The system therefore distinguishes three concepts that must not be collapsed:

```text
Greia Stars / reward balances
    repeatable platform-owned currencies or counters

Achievements / badges
    durable one-time milestones

Celebrations
    transient presentation when a newly earned achievement is surfaced
```

An Activity must never manufacture any of these authorities itself.

---

## 2. Product principles

### 2.1 Reward meaning, not grinding

Good achievements describe meaningful actions or progress:

- complete a first challenge;
- help a first patient;
- complete several genuinely separate sessions/challenges;
- reach a personal-best score threshold;
- explore enough of Greia to collect a modest number of platform Stars;
- combine several independent trusted milestones.

Avoid achievements for:

- clicking the same control hundreds of times;
- leaving the app open;
- arbitrary daily streaks;
- punishing missed days;
- speed unless speed is genuinely part of the educational/game skill;
- comparing siblings/children;
- rank, percentile, rarity or social status;
- failure, mistakes or embarrassment;
- spending money or installing more content.

Greia should reward curiosity, persistence, care, creativity, mastery and exploration without training compulsive engagement.

### 2.2 Personal progress only

Achievements are always evaluated against the child's own trusted history.

No child-vs-child rankings, global leaderboards, public rarity percentages, or sibling comparisons belong in this subsystem.

### 2.3 Tiers describe milestone depth, not child worth

The visual tiers are:

```text
bronze
silver
gold
special
```

They describe the depth or distinctiveness of a milestone. They do not rank children.

A bronze badge may be emotionally important because it marks a first success. A special badge is not evidence that one child is “better” than another.

### 2.4 Locked and secret badges

Normal locked badges remain visible as silhouettes/locks with a positive hint. This makes the library useful for discovery.

Secret badges are absent until earned. The UI must not leak their existence through grid placeholders or denominator counts.

---

## 3. Authority architecture

The fundamental rule is:

> Activities report facts. Greia decides rewards and achievements.

Current trusted data flow:

```text
Activity
  |
  | emit declared factual event
  v
ActivityEventBroker
  |
  +--> ProfileHistoryStore
  |      - validates session/activity/event
  |      - records event idempotently
  |      - updates event_count / best_score
  |      - applies Greia-owned progression rules
  |      - updates Greia Star/reward ledger
  |
  +--> ProfileAchievementService
         - reads trusted HistorySummary
         - evaluates platform achievement policy
         - records first unlock metadata
         - returns newly unlocked IDs in trusted receipt

Shell
  |
  +--> short post-Activity celebration
  +--> profile-owned Badge Library
```

The Activity receives no writable achievement store, no badge policy path, and no `award_badge()` authority.

An Activity event receipt may report `achievement_unlocks` because that is a **trusted platform result**, not an Activity request. Current Shell presentation waits for the Activity/display handoff before celebrating. A future R7/compositor presentation can surface that trusted result immediately without changing achievement truth or Activity permissions.

---

## 4. Why achievements are derived from history

The authoritative inputs already exist in Greia history:

- cumulative factual event counts;
- best scores, respecting the event's declared `higher_better` or `lower_better` order;
- Greia-owned reward balances;
- session records.

Achievement state must therefore not become a second gameplay database.

`ProfileAchievementService` derives whether each definition is satisfied from `HistorySummary`. Its profile JSON stores only metadata that history cannot reconstruct exactly:

```text
unlocked_at
announced_at
seen_at
```

If that metadata file is missing or corrupt, Greia can recover earned status from authoritative history. Reconstructed unlock time becomes the recovery time because the original first-evaluation timestamp is no longer knowable.

The state writer is serialized inside the service, uses atomic replacement, and retains only a known-good backup. A presentation-state failure does not invalidate an already accepted Activity event or Star reward.

---

## 5. Achievement policy

Canonical platform policy:

```text
runtime/achievement-policy.toml
```

Version 1 deliberately uses a small typed vocabulary instead of an arbitrary expression language.

Supported criterion types:

### `event_count`

```toml
[[achievements.criteria]]
type = "event_count"
activity_id = "org.greia.example"
event_id = "example.completed"
threshold = 5
```

Meaning: the trusted cumulative count of that declared event reached the threshold.

### `best_score`

```toml
[[achievements.criteria]]
type = "best_score"
activity_id = "org.greia.example"
event_id = "round.score"
threshold = 100
comparison = "at_least"
```

For a lower-is-better score such as elapsed time:

```toml
comparison = "at_most"
threshold = 60
```

Policy loading verifies that the referenced manifest event is actually `kind = "score"`. Greia history remains responsible for selecting the true personal best according to that event's `score_order`.

### `reward_balance`

```toml
[[achievements.criteria]]
type = "reward_balance"
reward_id = "star"
threshold = 5
```

Meaning: a Greia-owned balance reached the threshold.

### Multiple criteria

Multiple criteria on one achievement are **all-of**.

Do not add generic Python snippets, boolean expression strings, regexes or arbitrary payload queries to the policy. Add another typed criterion only when a reusable semantic need is demonstrated.

---

## 6. Definition metadata

One achievement currently owns:

```text
id
category
tier
icon_id
secret
localized title
localized description
localized locked_hint
criteria[]
```

Rules:

- IDs are stable and lower-case. Never reuse an old ID for a different meaning.
- Category is semantic organization, not a filesystem path.
- Icon IDs refer to Greia-owned visual vocabulary.
- English is the safe platform fallback locale; additional localized copy is preferred.
- A normal locked badge needs a useful, non-spoiling hint.
- A secret badge still has a hint in policy for future/admin tooling, but child UI hides the badge until unlocked.

Initial categories include:

```text
care
puzzles
building
greia
```

As the catalogue grows, preferred broad categories are concepts such as creativity, discovery, care, puzzles, learning/mastery and Greia exploration. Do not create one category per Activity.

---

## 7. Greia Stars

Greia Stars are governed separately by:

```text
runtime/progression-policy.toml
```

Current direction is one Star at most once per qualifying Activity session for a meaningful completion/creation fact.

That is intentional:

```text
GOOD: first real patient-heal event in a Clinic session -> session Star
GOOD: completed Memory game -> session Star
GOOD: completed Bridge level -> session Star

BAD: every tool click -> Star
BAD: every card flip -> Star
BAD: every particle/action -> Star
```

The ledger and `once_per_session` progression rule prevent high-frequency event farming inside one Activity session.

Stars may later power other benign profile customization, but achievements must never be reduced to “spend N Stars”. Earning and spending are separate concepts.

---

## 8. Event authoring contract

Achievement quality depends on factual event quality.

Activity authors must:

1. declare every emitted event in `activity.toml`;
2. emit a stable semantic fact, not presentation detail;
3. use idempotency correctly;
4. use `kind = "score"` only for genuine comparable personal scores and declare `score_order`;
5. keep event identity language-independent;
6. not mention achievement IDs in Activity code;
7. not write achievement/Star balances to Activity storage;
8. not branch gameplay based on whether a global badge was earned.

Examples:

```text
vet.patient_healed          good factual milestone
memory.game_completed       good completion fact
bridge.level_completed      good completion fact
button.clicked              poor achievement input
confetti.spawned            presentation detail; never achievement input
```

A manifest/source event-ID mismatch is a contract bug. The broker rejects undeclared events and achievement policy must never paper over that drift.

---

## 9. Child Badge Library

The Badge Library belongs to the active **profile**, not to an Activity or launcher Collection.

Current Shell behavior:

- a star/badge route is available from child Activity/Home navigation;
- the route shows the child's unlocked count;
- the library is an opaque full Shell mode, not a modal over a live Activity;
- six badges are shown per page in a 3×2 grid at the 1024×600 reference floor;
- normal locked badges show a lock medallion and positive hint;
- secret locked badges are omitted entirely;
- unlocked badges show their Greia icon and tier medallion;
- newly unlocked/unreviewed badges carry a `NEW` / `NUOVO` marker;
- selecting a badge shows its title and description/hint;
- keyboard/pointer navigation is supported;
- leaving the library marks the achievements that were available for review as seen.

The total shown to the child is based on **visible** achievements, so locked secret content cannot be inferred from the count.

### When the catalogue becomes larger

The current flat paged grid is appropriate for the seed catalogue. When visible policy grows beyond roughly 12–18 achievements, add a bounded category navigation layer using the existing semantic categories rather than shrinking every badge or creating a huge scroll surface.

---

## 10. Unlock celebration

A newly earned badge should feel special but never block the machine with heavy animation.

Current implementation:

```text
Activity ends / display returns to Shell
        ↓
compare pre-session vs current trusted achievement snapshot
        ↓
short ~0.34 s badge pop/rays intro
        ↓
small opaque card remains until child dismisses
        ↓
mark announced
```

If several achievements genuinely unlock in the same just-finished session, they are queued one at a time.

Historical/reconstructed achievements are **not** replayed as a popup storm when a profile is activated. They remain marked NEW in the library until reviewed.

If Greia crashes after the event was accepted but before presentation, the achievement still exists. Missing presentation metadata may be reconstructed from history; celebration delivery is secondary to achievement truth.

---

## 11. Visual language

Shared Pygame medallion renderer:

```text
src/greia_platform/pygame_achievements.py
```

Visual structure:

```text
small soft shadow
outer tier ring
cream inner medallion
semantic Greia icon OR geometric lock
small tier-colored ribbon
```

Tier uses color, but **locked/unlocked state never depends on color alone**: locked badges visibly use a lock glyph/geometry, unlocked badges use their semantic icon.

The shared badge renderer is intentionally independent of Activity art. Activities do not redraw or fork badge assets.

---

## 12. Performance contract

This subsystem must respect the same Acer-class rules established by launcher/terminal rendering work.

### Badge medallions

`PygameAchievementBadgeRenderer`:

- creates only small badge-sized alpha surfaces;
- bounds requested size to 48–220 px;
- uses a bounded LRU cache;
- keys cache by semantic identity, tier, icon, locked state and size;
- does not allocate a full-screen alpha surface.

Small alpha artwork is acceptable. The measured problem is large changing alpha area.

### Library

The library is an ordinary opaque Shell mode. It redraws only when the Shell's invalidation/event loop asks it to; there is no perpetual 30 Hz idle animation.

### Celebration

The intro is short and bounded. It restores the already optimized Shell frame and draws only a small opaque card plus simple geometry. It never runs a hidden Activity scene behind itself and never dims the whole display with a changing RGBA overlay.

Any future richer badge animation must preserve these properties.

---

## 13. Security and trust boundary

The following must remain impossible for an Activity package:

```text
award an achievement directly
edit runtime/achievement-policy.toml
write profile achievements.json
write global Star balances
read another profile's achievements/history
invent a trusted event outside its manifest
claim a different live Activity/session identity
```

The Event Broker validates session token, Activity identity, manifest event declarations, payload bounds and idempotency before history/progression/achievement evaluation.

Parent-installed content must not be allowed to flood the global child badge library merely by shipping its own badge definitions. If third-party achievement proposals are supported later, they require an explicit trusted package/policy admission model rather than automatic merge into global policy.

---

## 14. Failure behavior

Achievements are enrichment, not an Activity-launch safety authority.

If achievement policy cannot load:

- Activity launch still works;
- history still works;
- progression still works;
- the Badge Library route is unavailable.

If achievement state cannot be written:

- an accepted event remains accepted;
- its Star reward remains valid;
- later history refresh can re-derive earned milestones.

If a badge icon is missing:

- shared presentation falls back to the Greia star icon;
- achievement truth is unaffected.

---

## 15. Testing contract

Provider-free source tests should cover at least:

- event-count criterion;
- higher/lower score threshold semantics;
- reward-balance criterion;
- multi-criterion all-of behavior;
- one-time unlock / stable first timestamp;
- secret visibility;
- announcement and review state independently;
- reconstruction from missing metadata;
- corrupt-primary / valid-backup recovery;
- concurrent metadata update serialization;
- policy rejection of unknown Activity/event and non-score best-score criteria;
- event receipt achievement-unlock parsing;
- bounded badge surface/cache behavior;
- library pointer/keyboard navigation;
- secret count non-disclosure;
- no historical popup storm;
- Activity event declarations matching implementation.

Physical/simulator acceptance must additionally verify:

1. unlock one seed achievement through normal gameplay;
2. Greia Star balance changes at most once for that Activity session;
3. achievement celebration appears after Activity handoff;
4. dismissing celebration does not mark the badge reviewed;
5. library shows the badge as NEW;
6. opening/reviewing and leaving the library clears NEW;
7. normal locked badge remains visible with a hint;
8. secret locked badge is absent and does not affect the visible denominator;
9. switching profiles shows independent badge state;
10. restart preserves earned badges;
11. library and static celebration do not create a 30 Hz idle CPU loop;
12. no fullscreen `SRCALPHA` completion/achievement presentation is introduced.

Hardware performance claims require the exact source SHA and named machine.

---

## 16. Current implementation map

```text
runtime/achievement-policy.toml
    platform achievement catalogue

runtime/progression-policy.toml
    Greia Star economics

src/greia_platform/achievements.py
    policy validation, trusted evaluation, durable profile metadata

src/greia_platform/history.py
    authoritative event counts, best scores, reward balances

src/greia_launcher/event_broker.py
    trusted event boundary + immediate achievement evaluation

src/greia_platform/event_client.py
    trusted receipt including reward_deltas + achievement_unlocks

src/greia_platform/pygame_achievements.py
    shared bounded medallion renderer

src/greia_launcher/achievement_presentation.py
    child library + post-Activity celebration

src/greia_launcher/child_shell.py
    production composition
```

---

## 17. Deliberate future extensions

Good candidates after current acceptance evidence:

- category browsing once the library is large enough;
- a platform-owned notification sound/chime for badge unlocks;
- richer but still bounded medallion art from the Greia asset library;
- immediate system-compositor celebration after R7 can safely own overlays above an Activity;
- additional typed criteria such as distinct-Activity count or category breadth;
- Parent read-only view of a child's achievements if useful;
- explicit achievement-policy migration/versioning when semantics genuinely evolve.

Do **not** add these by making Activities more powerful. Extend the trusted platform contract instead.
