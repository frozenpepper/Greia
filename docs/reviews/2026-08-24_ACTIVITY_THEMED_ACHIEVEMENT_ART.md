# Activity-Themed Achievement Art — Implementation Review

**Date:** 2026-08-24  
**Repository:** `frozenpepper/Greia` / `main`  
**Prior accepted simulator baseline:** `850bf6d`  
**Status of this tranche:** implemented in source; provider-free/local simulator verification still required

## 1. Purpose

This tranche answers a product-design question that emerged after the initial Greia Badge Library acceptance:

> Should Activities be able to make achievements feel visually connected to their own content?

Decision: **yes, but as optional decorative contribution rather than global achievement authority.**

The target child-facing result is:

```text
Activity personality + Greia award identity
```

For example, Clinic can put recognizable Clinic artwork inside a Greia medal, while Greia still owns the fact that the badge exists, when it unlocks, how it is localized, how it is stored and how it appears in the global library.

---

## 2. Authority preserved

No Activity-facing `award_badge()` API was added.

Activities still cannot:

- create global achievement definitions;
- award themselves;
- choose global IDs or criteria;
- edit Greia Stars;
- write profile achievement state;
- choose tier/frame/library behavior;
- supply global localized badge copy;
- create custom global achievement popups.

New Activity artwork is inert until `runtime/achievement-policy.toml` explicitly admits it.

This is especially important for parent-installed/third-party packages: installation alone cannot add arbitrary content to the global Badge Library.

---

## 3. New Activity art contract

New platform owner:

```text
src/greia_platform/achievement_art.py
```

An Activity may optionally add:

```toml
[achievement_art]
emblems = [
  { id = "activity", asset = "assets/icon.png" },
  { id = "first-rescue", asset = "assets/achievements/first-rescue.png" },
]
```

V1 deliberately accepts only bounded static PNG emblems.

Validation includes:

```text
max 12 emblems per Activity
bounded lower-case emblem ID
safe relative package-local path
PNG extension
PNG signature/IHDR dimensions
square image
32..1024 px source dimensions
<= 512 KiB compressed size
no symlink
content SHA-256 fingerprint
```

Recommended Activity-authoring target is 256×256 transparent PNG with no embedded text and strong readability at small sizes.

The content digest is retained in the immutable emblem metadata so a changed Activity image at the same path invalidates the prepared badge cache rather than reusing stale artwork.

---

## 4. Platform policy admission

`AchievementDefinition` now has optional:

```text
activity_emblem: ActivityAchievementEmblem | None
```

A platform definition may explicitly admit one contribution:

```toml
art = { activity_id = "org.greia.clinica-cuccioli", emblem_id = "activity" }
```

Policy loading verifies that:

- the Activity exists in the runtime catalogue;
- its optional art declaration is valid;
- the requested emblem ID exists.

The existing Greia `icon_id` remains mandatory and acts as the fail-soft semantic fallback.

No criterion/evaluation/state semantics were moved into Activity packages.

---

## 5. Renderer integration

Updated owner:

```text
src/greia_platform/pygame_achievements.py
```

For an **unlocked** achievement:

```text
if platform admitted Activity emblem:
    decode emblem while preparing a new cached award
    scale once into the small badge surface
else:
    use Greia icon_id
```

If Activity image decode fails, the renderer falls back to `icon_id`; if the normal icon provider also fails, its existing yellow-star fallback remains.

For a **locked** achievement, Greia renders the lock and does not decode/reveal Activity art.

Performance constraints remain:

```text
final award surface: 48..220 px
bounded cache
small alpha area only
no per-frame Activity-art decode
no runtime SVG
no Activity rendering callback
no fullscreen alpha overlay
```

The cache identity includes the Activity asset path and its content fingerprint.

---

## 6. Seed adoption

Three existing first-party Activities now declare an `activity` emblem using their existing 256-class launcher artwork:

```text
org.greia.clinica-cuccioli
org.greia.memory-meraviglie
org.greia.costruiamo-ponti
```

Current platform policy admits those emblems for their Activity-specific achievements.

Global Greia Star achievements deliberately remain platform-art-only.

Using launcher art is an initial integration choice, not the desired final art ceiling. The Activity authoring guide now explicitly encourages purpose-made generated achievement emblems based on the Activity's characters, objects and content when that produces a stronger result.

Examples:

```text
Clinic   -> patient / paw / care object
Memory   -> distinctive card-pair motif
Bridges  -> recognizable bridge / construction / Flash motif
```

The infrastructure already supports several emblem IDs per Activity, so later art passes require no platform API change.

---

## 7. Documentation updated

New design authority:

```text
docs/design/GREIA_ACTIVITY_ACHIEVEMENT_ART.md
```

Updated:

```text
docs/design/GREIA_ACHIEVEMENTS_AND_BADGE_LIBRARY.md
skills/greia-activity-authoring/ACHIEVEMENTS.md
```

The authoring skill now makes explicit that:

- Activity art is decorative only;
- global policy admission is required;
- badge images must be language-neutral;
- Greia still owns frame/localization/unlock/state;
- purpose-made Activity emblems are encouraged;
- Activity-local stickers/collections/treasures should become a separate future subsystem rather than being forced into global achievements.

---

## 8. Tests authored in this tranche

New:

```text
tests/test_achievement_art.py
tests/test_achievement_emblem_cache.py
```

Expanded:

```text
tests/test_pygame_achievements.py
```

Authored coverage includes:

- current seed Activity emblem declarations;
- explicit policy admission;
- path escape rejection;
- PNG-extension rejection;
- invalid PNG signature rejection;
- non-square rejection;
- out-of-bounds dimension rejection;
- duplicate emblem ID rejection;
- symlink rejection at the art boundary;
- unknown/undeclared policy emblem rejection;
- Activity emblem used instead of platform icon when available;
- Activity-art decode failure falling back to platform icon;
- prepared badge cache reuse;
- content-digest change invalidating same-path cached art.

### Evidence boundary

These tests were **authored but not executed in the GitHub editing environment**.

Do not inherit the previous `1,110/1,110 PASS` result onto this source tranche. That result belongs to the earlier owner/local-agent acceptance baseline around `850bf6d`.

---

## 9. Required local verification

Focused provider-free gate:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_achievement_art \
  tests.test_achievement_emblem_cache \
  tests.test_achievements \
  tests.test_pygame_achievements \
  tests.test_achievement_localization \
  tests.test_activity_contract \
  -v
```

Then run the repository's normal complete local unit/validation gate used by the current checkout.

Minimal Simulator visual acceptance — **do not replay the whole already accepted achievement protocol unless a regression appears**:

1. launch the real child Shell in the Activity Simulator;
2. use Italian Greia locale and confirm the Badge Library remains Italian;
3. inspect an unlocked Clinic achievement and confirm its centre artwork is Activity-derived inside the Greia medal frame;
4. inspect an unlocked Memory achievement and confirm Activity-derived centre art;
5. inspect Bridge Builder and confirm Activity-derived centre art;
6. inspect a locked Activity achievement and confirm the lock hides its Activity art;
7. inspect `A Handful of Stars` and confirm it remains Greia/platform art, not one Activity's icon;
8. switch language to English through the normal supported simulator/device path if convenient and confirm artwork is unchanged while child-facing text changes;
9. leave the Badge Library idle for roughly five seconds and verify no obvious continuous repaint regression.

Capture exact tested SHA with results.

Simulator acceptance does not prove Acer-class hardware performance.

---

## 10. Follow-up art direction

The platform architecture is sufficient for Activity-generation agents to create purpose-made emblem art now.

A later first-party art pass should replace launcher-icon reuse where a dedicated emblem is materially nicer. It should be done Activity-by-Activity, using that Activity's own visual world and the practical rules in the authoring skill.

No further authority expansion is required for that work.

The separate concept of Activity-local collections/treasures remains deliberately unimplemented here and should receive its own design/storage contract before code is added.
