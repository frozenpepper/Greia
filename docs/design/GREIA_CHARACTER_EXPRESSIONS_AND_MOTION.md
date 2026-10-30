# Greia Shared Animation Library v0.1

**Active plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Canonical cast system:** `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`

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
5. All motions are shared semantic motions; individual characters may vary slightly in amplitude/timing so personality survives.
6. Animation is optional. Static art remains valid without motion.
7. `blink` is not accepted unless the eyes visibly close.
8. A motion storyboard is design evidence only; runtime/simulator acceptance requires the actual renderer path to be exercised later.

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

## Current target cast

The current design target is the six-character family defined by `GREIA_CANONICAL_CAST_SYSTEM.md`:

```text
Lilli
Leo
Flash
Dani
Tito
Momo
```

The previous `Nino` owl source remains historical provenance until the Leo visual candidate and later ID migration are explicitly approved.

All six should share the semantic state/motion names without being forced into identical geometry. For example, Flash may use a more energetic `happy_hop`, Leo a compact thoughtful hop, and Momo a broader comic pop.

## Shared-library location

```text
assets/visual/library/
assets/visual/characters/
```

Candidate/source art may also live under reviewed candidate workspaces until promotion.

This document defines design/source semantics. Runtime consumption must continue through the single explicit Greia asset/scene path rather than a new character renderer or body-part rig.

## Runtime Semantic States and Motion API (v0.1)

Promoted and verified under `2026-08-22_CANONICAL_CAST_V01_PROMOTION_RUNTIME_SIMULATOR.md` (archived; see git history):

### 1. Semantic States (`CharacterState`)
- `neutral`: Maps to runtime variant `default` (standard authored calm/friendly expression).
- `blink`: Maps to `blink` (closed eyes, neutral mouth).
- `happy`: Maps to `happy` (upturned joyful eyes, open happy smile).
- `surprised`: Maps to `surprised` (wide round eyes, open rounded 'o' mouth).
- `sleepy`: Maps to `sleepy` (curved resting eyes, peaceful gentle mouth).

### 2. Semantic Motions (`CharacterMotion`)
- `idle_bounce`: Neutral state with periodic eye blink and subtle breathing vertical lift.
- `blink`: Bounded closed-eye state swap (~0.18s) with settle.
- `happy_hop`: Joyful state swap + vertical parabolic hop with grounded contact shadow.
- `celebrate_pop`: High-energy pop with celebratory happy state.
- `surprised_wobble`: Surprised state swap + recoil horizontal oscillation.
- `sleepy_sway`: Sleepy state swap + slow gentle lateral sway.

### 3. Fail-Soft Architecture
- If a requested non-default state rendition is unavailable/corrupt, `PygameSceneRenderer` cleanly falls back once to `node.fallback_variant` (`default` neutral) without raising an exception.
- If the default required rendition fails, `SceneRenderError` is raised cleanly to allow Activity-level fallback.
