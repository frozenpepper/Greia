# Shared UI Visual Pack v0.1 — Desktop Review

**Status:** candidate visual pack; not runtime integration or owner approval.

## Individual/multi-ground review

The individual SVGs were rasterized locally and reviewed on Greia cream, Greia sky, and dark charcoal. Representative panels, focused activity card, primary button, selected tab, speech bubble and reward frame remained readable across the three grounds.

The pack uses rounded toy-like silhouettes, Greia theme colors, restrained gradients, local sheen instead of heavy gloss, reusable soft shadows, and focus/selection cues using shape/frame/depth in addition to color. Reusable masters contain no child-facing text.

## State tranche

Static state masters include primary default/hover/pressed/disabled; focused/completed activity cards; selected tab; new/done/favorite/locked badges; progress complete; loading, gentle error, empty-state and portal illustrations.

## Target-size composition review

Real references were built from the shared masters and existing character anchors:

- `reference_1024x600.svg`
- `reference_800x600.svg`
- `LOW_RES_REVIEW.md`

The 800×600 version is independently laid out rather than letterboxed from 1024×600.

Findings: card focused/completed/new/favorite states remain distinct at both sizes; focus is not color-only; the primary action remains clear without a heavy glow; top navigation remains quieter than activity cards; the same reusable masters work at both targets without separate low-resolution redraws.

## Explicit boundaries

- These files do not replace Greia Screen/Overlay/Panel/Card/Control semantics.
- They do not create an Activity-owned imitation of protected system Home/Back chrome.
- `runtime_consumed = false` remains true for the pack.
- Current evidence is **SOURCE + DESKTOP VISUAL REVIEW** only.

## Next UI work

Owner revision should target concrete weak components rather than adding more decorative variants. Cheap hover/press/launch motion deltas remain a later design/runtime seam and should reuse these same static masters.
