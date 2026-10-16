# Greia Activity-Themed Achievement Art

**Status:** active implementation contract  
**Date:** 2026-08-24  
**Scope:** optional Activity-owned decorative art inside platform-owned global achievements

## 1. Decision

Greia global achievements remain platform-owned, but an Activity may optionally contribute **visual emblems based on its own content**.

This produces the desired child-facing effect:

```text
recognizable Activity personality
        +
consistent Greia medal/trophy/rosette language
        +
trusted global progression semantics
```

The Activity contributes art, not authority.

---

## 2. Authority boundary

The fundamental achievement rule remains unchanged:

> Activities report facts. Greia decides rewards and achievements.

An Activity contribution cannot:

- create a global achievement;
- choose an achievement ID;
- choose unlock criteria;
- award itself;
- mutate profile progress;
- choose Greia Star economics;
- choose bronze/silver/gold/special tier;
- choose library placement or visibility;
- choose locked/secret behavior;
- provide global child-facing title/description/hint text;
- create its own global popup or fullscreen achievement UI.

The platform policy must explicitly admit every Activity emblem used by a global badge.

Therefore a parent-installed Activity cannot flood the Badge Library simply by adding entries to its own manifest.

---

## 3. Data flow

```text
Activity package
  activity.toml
    [achievement_art]
      optional decorative emblem declarations
           |
           v
src/greia_platform/achievement_art.py
  validates safe package-local PNG contributions
           |
           v
runtime/achievement-policy.toml
  Greia explicitly admits one emblem for a platform achievement
           |
           v
AchievementPolicy
  retains trusted fallback icon + admitted Activity emblem metadata
           |
           v
PygameAchievementBadgeRenderer
  Greia frame + Activity emblem
  OR Greia frame + fallback platform icon
```

Unlock evaluation remains completely separate:

```text
Activity factual event -> trusted History -> Achievement criteria -> unlock
```

Artwork never participates in achievement truth.

---

## 4. Activity manifest contract

Optional V1 syntax:

```toml
[achievement_art]
emblems = [
  { id = "activity", asset = "assets/icon.png" },
  { id = "first-rescue", asset = "assets/achievements/first-rescue.png" },
]
```

`emblems` is intentionally only a catalogue of **possible decorative contributions**.

No achievement ID, threshold, tier, Star reward or localization is permitted in this table.

### Limits

One Activity may currently declare at most 12 emblems.

Each emblem:

- has a bounded lower-case ID;
- references a safe relative path inside the Activity package;
- must be a regular PNG file;
- cannot be a symlink;
- must be square;
- must be 32–1024 px on each side;
- must be at most 512 KiB compressed.

Recommended production asset:

```text
256×256 transparent PNG
clear silhouette / central subject
no text
strong readability at 30–100 px
```

The upper 1024 px bound is compatibility/safety headroom, not the recommended authoring target.

---

## 5. Platform admission

A Greia achievement definition may opt into one Activity emblem:

```toml
[[achievements]]
id = "greia.care.first-friend"
category = "care"
tier = "bronze"
icon_id = "pink_heart"
secret = false
art = { activity_id = "org.greia.clinica-cuccioli", emblem_id = "activity" }

# localized title/description/hint
# trusted criteria
```

Policy loading verifies:

1. the Activity exists in the trusted runtime catalogue;
2. the Activity manifest can be read;
3. the Activity declares `achievement_art` correctly;
4. the requested emblem ID exists;
5. the asset is package-local and valid;
6. the PNG size/dimensions are within bounds.

An invalid referenced contribution fails achievement-policy loading rather than silently granting arbitrary package influence.

Unreferenced Activity art does not appear anywhere globally.

---

## 6. Rendering model

Greia always owns the **award frame**.

Current shared frame families (flat `ui.award.<family>` renditions from `assets/source/achievements/`; procedural fallback):

```text
bronze          -> round copper medal, short blue ribbons
silver          -> scalloped silver-blue medal, longer ribbons
gold            -> cup trophy
special/secret  -> purple rosette over a star burst
```

The admitted Activity emblem replaces only the **center semantic artwork** when unlocked.

Locked achievements remain grey Greia tier silhouettes with a padlock, so Activity artwork does not spoil locked content.

If the Activity emblem cannot decode at runtime:

```text
Activity emblem fails
      ↓
use platform icon_id fallback
      ↓
achievement remains fully usable
```

Presentation failure never changes unlock truth.

---

## 7. Performance contract

The low-resource Acer-class floor remains authoritative.

The runtime renderer:

- keeps final badge surfaces bounded to 48–220 px;
- decodes an Activity emblem only when preparing a new cached badge surface;
- scales it once into the small award surface;
- reuses the existing bounded badge cache on repeated draws;
- never decodes source artwork every frame;
- never creates a fullscreen alpha layer for badge presentation;
- never executes vector scripts or arbitrary Activity drawing code.

For this reason V1 uses PNG rather than runtime SVG.

Activity authors should prefer 256×256 source PNGs rather than shipping unnecessarily large images.

---

## 8. Localization contract

Activity-contributed emblem artwork must contain **no child-facing words**.

All child-visible achievement text remains Greia-localized policy/presentation data:

```text
title
description
locked_hint
NEW label
library title
celebration chrome
```

Changing Greia language therefore changes text without requiring alternate badge image files.

Machine IDs and emblem IDs remain language-neutral.

---

## 9. Art-direction guidance for Activity creators

A purpose-made emblem should feel like a distilled visual memory of the Activity.

Good directions:

```text
Clinic          recognizable puppy/paw, bandage, heart-shaped care object
Bridges         bridge silhouette, plank/bolt motif, Flash crossing
Memory          distinctive pair of cards, recurring flower/object motif
Garden          recognizable plant/creation from that Activity
Music           characteristic animal/instrument motif
Exploration     landmark, creature, discovery object
```

Avoid:

- tiny screenshots;
- full scenes with unreadable detail;
- words or achievement titles;
- numerical ranks;
- photographic UI captures;
- large transparent padding;
- low-contrast iconography;
- trophy/medal frames baked into the emblem itself.

The Activity creates the **content symbol**. Greia creates the **award object**.

---

## 10. Current seed adoption

The first implementation deliberately reuses existing package icons as V1 Activity emblems for:

```text
org.greia.clinica-cuccioli
org.greia.memory-meraviglie
org.greia.costruiamo-ponti
```

Their current platform achievements explicitly admit those contributions.

This makes the architecture visible immediately without requiring new binary assets in the same code tranche.

It is not the final art-direction target. Future Activity-authoring passes should replace/reinforce generic launcher-icon reuse with purpose-made emblem PNGs where that produces a noticeably stronger result.

Global Greia-wide Star achievements remain platform-art-only because they do not belong to a single Activity.

---

## 11. Why the platform still keeps a fallback icon

Every achievement continues to declare `icon_id` even when Activity art is admitted.

Reasons:

- Activity asset decode can fail;
- a future package version may remove/restructure optional art incorrectly;
- administration/testing needs a stable semantic symbol;
- global visual meaning should remain recoverable without Activity decoration.

Therefore Activity art enhances rather than replaces the platform contract.

---

## 12. Third-party / parent-installed Activities

V1 does **not** auto-import achievements from parent-installed Activities.

A third-party Activity may safely ship `[achievement_art]` declarations, but they remain inert unless a trusted Greia achievement policy explicitly references one.

Future store/community ecosystems may introduce a reviewed achievement-admission layer, but that must remain a platform trust decision.

Never implement:

```text
scan installed Activities -> automatically add their badges to global library
```

---

## 13. Activity-local collections are different

The global Badge Library should not become the only reward vocabulary.

A future Activity-local collection system may support much freer content such as:

- stickers;
- postcards;
- saved patients;
- characters encountered;
- discoveries;
- creations;
- blueprints;
- scene souvenirs.

That future system can allow more Activity ownership because it is scoped to the Activity rather than claiming global Greia progression authority.

It must receive its own storage, portability and presentation contract instead of being smuggled through global achievement art.

---

## 14. Implementation map

```text
src/greia_platform/achievement_art.py
    Activity contribution parser + safety validation

src/greia_platform/achievements.py
    platform policy admission and immutable association

src/greia_platform/pygame_achievements.py
    cached Greia frame + admitted Activity emblem rendering

runtime/achievement-policy.toml
    explicit trusted art admission

activities/*/activity.toml
    optional [achievement_art] contribution declarations

skills/greia-activity-authoring/ACHIEVEMENTS.md
    Activity-authoring rules
```

---

## 15. Required tests

Provider-free tests must cover:

- valid package-local emblem parsing;
- path escape rejection;
- PNG type validation;
- size/dimension bounds;
- duplicate contribution IDs;
- platform-policy rejection of unknown Activity/emblem;
- policy admission of valid Activity art;
- locked badge not decoding/revealing Activity art;
- unlocked badge uses admitted Activity art;
- fallback platform icon on runtime decode failure;
- badge cache reuse after first decode;
- global Star achievements remaining valid without Activity art.

Simulator acceptance should visually confirm:

- Clinic / Memory / Bridges badges visibly inherit their Activity identity;
- Greia frame language remains coherent across all three;
- locked badges do not reveal Activity emblem art;
- Italian/English text remains independent from emblem image;
- no idle repaint regression is introduced.
