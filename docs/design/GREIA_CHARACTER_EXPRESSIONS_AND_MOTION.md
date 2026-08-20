# Greia Shared Animation Library v0.1

**Active plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`

This is a small shared animation vocabulary for Greia characters and compatible visual assets.

The system is deliberately simple.

## Base motions

- `idle_bounce` — gentle living bob;
- `blink` — **real eye closure** using the character's authored blink state;
- `happy_hop` — short squash/hop/settle;
- `celebrate_pop` — larger hop with optional sparkle;
- `surprised_wobble` — recoil/wobble;
- `sleepy_sway` — slow sway.

## Rules

1. Never redraw or degrade a character merely to animate it.
2. Expression changes use authored variants of the same character.
3. Whole-body translate/rotate/squash/stretch is enough for the base library.
4. No detailed rig is required.
5. All motions are shared semantic motions; individual characters may vary slightly in amplitude.
6. Animation is optional. Static art remains valid without motion.
7. `blink` is not accepted unless the eyes visibly close.

## Current character states

The first useful shared states are:

```text
neutral
blink
happy
surprised
sleepy
```

Add more only when a real Greia use requires them.

## Shared-library location

```text
assets/visual/library/
assets/visual/characters/
```

This is currently design/source artwork. Runtime consumption is handled later through the single shared Greia asset path defined by the active plan.