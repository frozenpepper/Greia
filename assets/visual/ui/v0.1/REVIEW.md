# Shared UI Visual Pack v0.1 — Desktop Review

**Status:** candidate visual pack; not runtime integration or owner approval.

## Review performed

The individual SVGs were rasterized locally and reviewed on:

- Greia cream;
- Greia sky;
- a dark charcoal ground.

Representative panels, focused activity card, primary button, selected tab, speech bubble and reward frame remained readable on all three grounds.

## Current direction

The pack intentionally uses:

- rounded toy-like silhouettes;
- Greia theme colors from `runtime/theme-defaults.toml`;
- restrained vertical gradients;
- bright local sheen instead of heavy glossy effects;
- reusable soft shadows;
- selected/focused states with both shape/frame cues and color;
- no embedded child-facing text so the same art can be localized/reused.

## Explicit boundaries

- These files do not replace Greia Screen/Overlay/Panel/Card/Control semantics.
- They do not create an Activity-owned imitation of protected system Home/Back chrome.
- `runtime_consumed = false` remains true for the pack.
- Generic-looking or over-glossy components should be revised before shared adoption.

## Next UI work

1. add hover/pressed/disabled visual-state masters where a static asset is useful;
2. add favorite and progress-complete/reward variants;
3. add loading/error/empty-state illustration pieces;
4. create a low-resolution component composition using only this pack;
5. define cheap motion deltas separately from the SVG artwork so the same assets remain usable without animation.
