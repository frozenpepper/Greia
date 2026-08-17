# ADR 0025 — Platform-Owned Awards, Badges, Celebrations, and Collection

**Status:** ACCEPTED  
**Date:** 2026-08-17  
**Scope:** child achievements, badges/awards, personal-best celebration, award persistence, cross-Activity achievements, celebration presentation, collection UI, backup/restore, and display/session requirements  
**Extends:** ADR 0017 platform-owned sessions/events/progression/reward ledger; ADR 0019 trusted platform-owned system presentation; ADR 0018 lightweight UI foundation  
**Product requirement:** `docs/product/AWARDS_BADGES_AND_CELEBRATIONS.md`

## Context

Greia already owns the authoritative progression pipeline. ADR 0017 established that Activities report bounded factual events and scores, while Greia owns sessions, best-score comparison, progression policy, reward balances, and the reward ledger. An Activity cannot authorize its own global rewards by placing fields such as `stars` or `reward_delta` in an event payload.

That foundation is intentionally stronger than a game-local achievement implementation, but it currently stops before the child-facing experience. Greia needs a coherent way to:

- celebrate completion of meaningful Activity goals;
- celebrate genuine personal improvement, including a new best score or lower best time according to the Activity's declared score direction;
- grant durable badges/awards for meaningful milestones;
- support both Activity-specific and cross-Activity Greia achievements;
- show a delightful, consistent Greia-owned celebration without every Activity reimplementing it;
- preserve the child's earned collection across Activity uninstall, backup/restore, CPU architecture changes, and future runtime changes;
- expose a child-friendly place in Greia Shell where earned awards can be revisited;
- avoid turning rewards into manipulative retention, purchasing, advertising, or screen-time mechanics.

Without a platform decision, Activities would inevitably invent incompatible badge stores, duplicate score logic, render conflicting popups, lose awards when uninstalled, or make their own reward economics. That would violate the Activity-first architecture and fragment the child's Greia experience.

## Decision

### 1. Awards are a Greia platform concept

Greia owns the authoritative award state for every child profile.

An **Award** is a durable, named achievement granted to a profile because validated platform evidence satisfied a defined achievement rule. The initial child-facing form is a **badge**. Future presentation families such as medals, stickers, trophies, or collectible objects may exist without changing the authority model.

The stable logical distinction is:

```text
factual Activity event / score
            ↓
Greia progression evidence
            ↓
   ┌────────┼─────────┐
   │        │         │
best score reward   award grant
           balance      │
                       award ledger
```

Activities never receive direct write access to the award ledger.

### 2. Rewards, awards, and celebrations are different concepts

Greia must not collapse all motivation/progression concepts into one structure.

- **Reward** — a quantity or balance such as a star. Rewards live in the Greia reward ledger and may later feed bounded platform customization/unlocks.
- **Award / badge** — a durable achievement identity such as `Maze Master` or `First Painting`. Once legitimately earned, it becomes part of the child's collection.
- **Celebration** — a transient presentation event such as `New Best!`, sparkle animation, badge reveal, sound, or spoken praise. A celebration is not itself durable progression authority.

A new personal best normally creates a celebration and updates the best-score aggregate. It does **not** create an endless stream of permanent badges. Specific score or mastery milestones may separately grant a badge when policy defines one.

### 3. Greia remains the authority that evaluates and grants

Award grants are derived from trusted Greia progression evidence: validated Activity events, score aggregates, session history, and other platform-owned state.

An Activity may report facts such as:

```text
level.completed
puzzle.solved
creation.saved
score.submitted = 930
```

It may not send an authoritative command equivalent to:

```text
grant_badge("maze-master")
award_global_trophy(...)
```

Nor may an event payload obtain award authority merely by containing `badge_id`, `award_id`, `achievement`, or similar fields.

Award evaluation must be transactional/idempotent so retries cannot duplicate once-only awards.

### 4. Activity-scoped awards and Greia-wide awards are distinct

Greia supports two logical award sources.

#### Activity-scoped awards

An Activity may eventually package **declarative award definitions** for achievements meaningful within that Activity, for example:

```text
First Maze
Perfect Run
Ten Puzzles Solved
Master Gardener
```

This does not give Activity runtime code award-ledger authority. The package definition is validated during installation/registration and can only bind to allowed factual evidence from that Activity's own stable identity and declared event/score semantics.

The exact package/manifest schema is deferred to the package/progression implementation tranche and remains source-owned when implemented.

#### Greia-wide awards

Greia policy alone defines cross-Activity achievements, for example:

```text
Creative Spark — create work in several creative Activities
Curious Explorer — meaningfully try Activities from several categories
Getting Better — improve personal bests in several different Activities
Puzzle Friend — complete puzzle goals across more than one Activity
```

No individual Activity can grant, redefine, or forge a Greia-wide award because only Greia has authoritative cross-Activity history.

### 5. Award identity is stable and independent from display text

Every award has a stable logical ID. Child-facing title, description, artwork, localization, spoken label, and presentation style are metadata around that identity.

Conceptually, a definition needs to express concerns such as:

```text
award_id
source kind (Greia or Activity)
source Activity ID where applicable
child-facing title/description
icon / presentation asset
category
localization / spoken accessibility metadata
once-only or explicitly repeatable presentation semantics
rule/evidence binding
schema/version metadata
```

Exact implemented fields are not fixed by this ADR.

Renaming a title or improving artwork must not silently create a second award. Updating/removing an Activity must not erase already-earned award identity.

### 6. Award grants are profile-scoped, durable, local-first, and non-revocable by ordinary content

Earned awards belong to the child profile.

Normal properties are:

- local/offline operation;
- durable persistence independent of Activity save files;
- once-earned permanence under ordinary product operation;
- no Activity API for deleting/revoking a child's earned award;
- architecture-neutral logical backup/restore;
- no cloud account requirement;
- no dependency on an Activity process remaining installed or runnable.

Administrative data-repair/migration may correct corrupt state, but ordinary gameplay, Activity updates, catalogue changes, or loss of network connectivity do not take earned badges away.

### 7. The collection must survive Activity uninstall and restore without the Activity

Greia's child-facing collection must remain meaningful when the originating Activity is absent.

Therefore the durable award record/backup representation must preserve enough bounded, portable presentation information to render an earned award safely, or must guarantee a stable platform-owned fallback representation. It must not require reading an icon/title from a package path that may no longer exist.

The exact storage schema is deferred, but the contract is not: an i386 machine may award a badge, the Activity may later be uninstalled, and a `.greiabackup` restored on ARM64 must still preserve the child's earned badge collection.

### 8. Granting an award and presenting its celebration are separate operations

A valid award is committed immediately when the trusted progression transaction determines it has been earned.

The **celebration presentation** is scheduled separately.

This prevents a popup from covering a timed puzzle, hiding an important game state, stealing input during a drawing gesture, or causing a child to fail the very challenge they just completed.

Conceptually:

```text
trusted event / score
      ↓
award transaction commits
      ↓
celebration request queued
      ↓
Greia presentation scheduler
      ↓
show at an appropriate safe moment
```

A crash or reboot after the grant but before animation must not lose the award. The presentation queue itself must be bounded and duplicate-aware; the system must not replay an unbounded history of old celebrations after recovery.

### 9. Greia owns official celebration presentation

The official badge/new-best celebration is rendered by Greia, not by Activity content.

The child should receive one coherent visual language across Python, Web, and future runtimes. A typical celebration may include a short animation, badge reveal, sparkle/confetti effect, short sound, optional spoken label, and a clear continue/dismiss behavior.

Activity authors may create ordinary in-Activity feedback, but they must not be required to implement or persist the authoritative Greia award ceremony.

The platform-owned celebration layer must never replace, obscure, or disable the mandatory Greia Home/Back authority.

### 10. Celebration presentation must not become a desktop/windowing system

The display/session architecture must support the smallest mechanism needed to present bounded Greia-owned transient UI above or between Activity content while preserving system navigation and protected input.

This requirement does **not** authorize:

- a general-purpose desktop compositor UI;
- arbitrary movable/resizable windows;
- a notification center modeled on a desktop OS;
- unbounded z-order or background app surfaces;
- Activity-owned access to the trusted presentation layer.

Where the selected backend can safely compose a tiny transient Greia overlay above an Activity, it may do so. Where presenting immediately would be unsafe or disproportionately expensive, Greia may defer celebration until a lifecycle/safe transition such as completion or return to Shell.

R7 display/session acceptance must therefore preserve a bounded platform-owned transient-presentation capability or an equivalent safe platform-controlled presentation path, in addition to ADR 0019 Home/Back requirements.

### 11. Personal-best detection belongs to Greia

ADR 0017 already owns best-score comparison and the manifest declares whether higher or lower is better.

Therefore Greia, not the Activity, determines whether a submitted score is a genuine personal best.

Examples:

```text
higher_better:
old best 870 → new 930 = improvement

lower_better:
old best 48.0 s → new 42.0 s = improvement
```

A genuine improvement may enqueue a `New Best!` celebration. Milestone badges are separate policy.

This avoids duplicated or incorrect comparison logic across runtimes and Activities.

### 12. Greia Shell provides a child-facing collection

Every child profile has a Greia-owned place to revisit earned awards.

The product metaphor may evolve — badge book, treasure cabinet, trophy shelf, sticker album, or an integrated place in the Greia world — but the semantic requirements are stable:

- large visual items suitable for young children;
- minimal reading required for basic recognition;
- optional speech/audio explanation;
- tap/select to inspect a badge;
- clear source/context without exposing technical IDs;
- support for Greia-wide and Activity-specific awards;
- no Linux filesystem or package concepts;
- no dependency on network connectivity;
- no loss of awards when an Activity is absent.

The exact child-facing requirements live in `docs/product/AWARDS_BADGES_AND_CELEBRATIONS.md`.

### 13. Award mechanics must avoid manipulative engagement design

Greia awards exist to celebrate mastery, improvement, curiosity, creation, persistence, and meaningful exploration — not to maximize screen time.

The platform must not build core achievement policy around:

- daily-login streak loss;
- expiring earned badges;
- `come back tomorrow or lose this` mechanics;
- paying money to obtain achievement badges;
- watching advertising to obtain awards;
- artificial scarcity/FOMO for ordinary child progression;
- public/global leaderboards by default;
- rewards whose primary criterion is simply spending more time in Greia.

Catalogue policy may impose the same restrictions on Activity-local achievement design.

### 14. Awards can influence Greia customization only through platform policy

Future awards may unlock or expose child-safe Greia customization such as a shelf object, avatar decoration, workshop item, color/theme option, or collectible display.

The relationship remains Greia-owned policy. An Activity cannot directly mutate Shell/world state or global unlocks because it emitted an event.

The award ledger records achievement; a separate Greia customization/unlock policy decides whether that achievement has additional presentation consequences.

### 15. Accessibility and localization are part of the platform contract

Award presentation must not require reading English text or hearing audio.

A conforming child-facing celebration/collection should support:

- recognizable visual/icon presentation;
- localized title/description where text is used;
- optional spoken name/description where speech support exists;
- reduced-motion or equivalent accessibility policy if Greia later exposes it;
- non-audio cues so muted/deaf use still communicates success;
- bounded, child-sized controls.

Activities must not be required to reinvent these platform concerns.

### 16. Resource use is bounded and C0-aware

Award presentation must remain viable on the Acer/low-resource floor.

The implementation must bound at least:

- pending celebration queue size;
- decoded/scaled award artwork cache;
- retained per-profile award rows/metadata growth;
- animation/transient object count;
- audio resources;
- parent/collection query sizes.

Celebrations must not require a heavyweight 3D engine, browser process, network service, or permanently resident animation subsystem.

### 17. Parent surfaces receive logical summaries only

Greia Parents may eventually expose a bounded read-only achievement summary for a child profile, using the same semantic Parent API principles as other progress data.

The parent client must not read internal databases, Activity package paths, or raw ledger implementation details. Parent write authority to fabricate child awards is not part of the normal product model.

### 18. Backup/restore uses logical award state

The future `.greiabackup` format must export/import award state through a versioned architecture-neutral logical representation, not by copying the internal SQLite database.

Restore must preserve stable award identity and sufficient child-facing representation even when the originating Activity is not currently installed.

## Consequences

Positive consequences:

- every Activity benefits from one polished celebration system;
- badges feel like part of Greia rather than isolated game UI;
- personal-best logic is correct and consistent across runtimes;
- third-party Activities can eventually participate without receiving platform write authority;
- cross-Activity achievements become possible;
- earned collections survive uninstall and architecture migration;
- R7 learns about the transient platform-presentation requirement before the display/session backend is frozen;
- reward design can be child-positive rather than engagement-maximizing.

Costs/complexity:

- progression storage needs a durable award/achievement representation in addition to reward balances;
- the Shell needs a collection surface;
- the display/session path needs a bounded Greia-owned transient-presentation path or safe deferred equivalent;
- package/manifest work must eventually define validated Activity-scoped award metadata;
- backup/restore must preserve award identity/presentation independently from installed package state;
- localization/accessibility and asset provenance must be handled for award definitions.

## Rejected alternatives

Rejected:

- each Activity owning its own badge database;
- Activities directly calling a privileged `grant_badge()` API;
- treating every personal-best improvement as a permanent badge;
- putting badge authority in arbitrary event payload fields;
- losing badges when an Activity is uninstalled;
- presenting rewards only through an Activity-rendered popup;
- interrupting gameplay immediately whenever an award transaction commits;
- cloud-only achievement state;
- daily-login/streak-loss/FOMO award systems as Greia core progression;
- using the requirement as justification for a general desktop notification/window manager.

## Implementation boundary

This ADR selects product/architecture semantics; it does not claim the complete award subsystem is implemented.

Current ADR 0017 source already provides the required trusted ingredients for sessions, factual events, score ordering, best-score aggregates, reward policy, local history, and logical export. Future implementation must add the award definition/ledger/evaluation/presentation/collection pieces without weakening those boundaries.

Until source, tests, and required runtime/hardware evidence land, documentation must describe awards/badges/celebrations as **SELECTED architecture / accepted product requirement**, not as a completed runtime feature.
