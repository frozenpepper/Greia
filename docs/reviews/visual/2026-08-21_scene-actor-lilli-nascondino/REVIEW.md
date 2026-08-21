# Visual Review — Scene Actor Lilli & Nascondino HUD Correction

**Date:** 2026-08-21  
**Runbook Authority:** `docs/testing/2026-08-21_SCENE_ACTOR_LILLI_NASCONDINO_SIMULATOR.md`  
**Evidence Contract:** `docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md`  
**Target Activity:** `org.greia.nascondino-bosco`  
**Evidence Class:** `SIMULATOR VISUAL REVIEW`

---

## 1. Summary of Accomplishments

This gate advances the graphics composition runtime from environment-only layering to character actor rendering and corrects the typography, card geometry, and interface scaling defects identified in `PRIMARY_REVIEW.md`:

1. **First Shared Greia Scene Actor:**
   - Integrated Lilli as a renderer-neutral scene actor using `SceneActorDefinition` and `actor_scene_sample` from `src/greia_platform/scene_actor.py`.
   - Rendered using the existing `PygameSceneRenderer` and bounded `PygameVisualSurfaceCache` without custom loaders or duplicate caches.
   - Grounded contact shadow (`shadow.contact.small.01`) positioned at $[78, 232, 96, 24]$ beneath body at $[50, 105, 150, 150]$.
   - Subtle vertical idle oscillation ($\\pm 3$ px, 2.4s period) moves the character body while the contact shadow remains grounded.
   - Deterministic eye blink (0.18s duration every 4.8s) visibly swaps to `character.lilli/blink`.

2. **Truthful, Reflowed Child HUD Geometry:**
   - **Normal Interface:** Target card reflowed to $[337, 14, 350, 94]$ with **24 px** animal label font (`FontRole.DISPLAY`).
   - **Large Interface:** Target card genuinely scales to $[322, 10, 380, 104]$ with **26 px** font, 76 px animal portrait, and scaled star dots.
   - **Compact Interface:** Target card sized to $[352, 16, 320, 88]$ with **20 px** font (never dropping below the 20 px guardrail).
   - **Word Length Accommodation:** The longest Italian animal name (`SCOIATTOLO`, 105 px wide in Normal, 109 px in Large) fits comfortably inside available text spans (148 px in Normal, 161 px in Large) with zero clipping, collision, or ellipsis.
   - **Zero Chrome Overlap:** Maintained 112 px clear horizontal margin between star pill right edge ($x=210$) and target card left edge ($x=322..337$).

3. **Accurate Fit Semantics:**
   - `forest_meadow_day_v1.toml` declares `fit = "cover"`. Differing aspect ratios use symmetrical centered cropping across the 1024×600 reference scene while preserving the $[112, 912]$ central gameplay safe span.

---

## 2. Visual Evidence Analysis

| Screenshot | Scenario / State | Key Visual Inspection Points | Result |
|---|---|---|---|
| `01-reference.png` | 1024×600 Normal Baseline | Lilli neutral guide visible in upper-left clearing; contact shadow grounded; target card $[337, 14, 350, 94]$ with 24 px `SCOIATTOLO` text; 112 px clear space from star pill. | **PASS** |
| `02-blink.png` | 1024×600 Normal Blink State | Lilli eyes physically closed in smiling arc; contact shadow remains grounded on grass; all scene layers intact. | **PASS** |
| `03-large.png` | 1024×600 Large Interface | Target card scaled to $[322, 10, 380, 104]$; animal text 26 px; portrait 76 px; star indicators scaled; no overlap with star pill ($x=210$) or screen top. | **PASS** |
| `04-compact.png` | 1366×768 Compact Interface | 1366×768 display with Compact UI preference; card $[352, 16, 320, 88]$; animal text 20 px (above 20 px guardrail); COVER crop preserves all spots. | **PASS** |
| `05-large-viewport.png` | 1920×1080 Large Viewport (COVER) | Symmetrical vertical crop on 16:9 viewport; central safe span $[112, 912]$ intact; Lilli and all 5 hiding spots fully visible. | **PASS** |
| `06-fallback.png` | Required Asset Failure Fallback | Corrupted `distant_hills.png` triggers fail-soft `_draw_legacy_forest_background`; game loop and UI remain fully interactive. | **PASS** |

---

## 3. Runtime-Derived Layout Audit

Derived directly from `nascondino.compute_hud_layout()` and `GreiaTypography` rendering:

```json
{
  "normal": {
    "target_card_rect": [337, 14, 350, 94],
    "font_size_px": 24,
    "scoiattolo_rendered_rect": [499, 53, 105, 16],
    "available_span_px": 148,
    "clipped_or_colliding": false,
    "margin_star_to_card_px": 127
  },
  "large": {
    "target_card_rect": [322, 10, 380, 104],
    "font_size_px": 26,
    "scoiattolo_rendered_rect": [497, 54, 109, 17],
    "available_span_px": 161,
    "clipped_or_colliding": false,
    "margin_star_to_card_px": 112
  },
  "compact": {
    "target_card_rect": [352, 16, 320, 88],
    "font_size_px": 20,
    "scoiattolo_rendered_rect": [502, 54, 85, 13],
    "available_span_px": 134,
    "clipped_or_colliding": false,
    "margin_star_to_card_px": 142
  }
}
```

---

## 4. Performance & Fail-Soft Measurements

- **Measured Idle Performance:** 230 frames rendered across 10.01 seconds (**23.0 FPS** on headless SDL dummy driver).
- **Optional Fog Asset Isolation:** When `fog_strip.png` is corrupted, `PygameSceneRenderer` logs one fail-soft warning, caches the failure to prevent per-frame decode storms, and renders all other 14 background/foreground nodes and Lilli cleanly.
- **Required Asset Fallback:** When `distant_hills.png` is corrupted, the Activity falls back to `_draw_legacy_forest_background` without disrupting child input or game lifecycle.

---

## 5. Independent Review Package

Per Section 10 of the protocol, the review package for independent owner pixel inspection is assembled at:
`./GREIA_VISUAL_REVIEW_SCENE_ACTOR_LILLI_2026-08-21.zip`
