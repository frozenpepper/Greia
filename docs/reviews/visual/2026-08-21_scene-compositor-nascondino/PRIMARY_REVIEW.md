# Primary review — Scene Compositor / Nascondino

**Date:** 2026-08-21  
**Reviewed commit:** `d9eeae74a00b4380cab51266a206489b074d5eff`  
**Scope:** source/evidence cross-check by the primary project agent after the local-agent simulator run.

## Important evidence limitation

The committed PNG files are present and retained, but the current private-GitHub connector exposes repository PNGs to this agent as base64 text rather than as a directly viewable image surface. Therefore this review must **not** be described as an independent pixel-level visual inspection of the PNGs by the primary agent.

The local agent's screenshot review remains useful evidence, but its prose/layout audit is not accepted blindly. Source and evidence values are cross-checked below.

## Cross-check findings

The local-agent `REVIEW.md` / `layout-audit.json` contains several factual mismatches with the accepted source and scene contract:

1. **Target animal label size**
   - local review claims `22 px`;
   - accepted source at `d9eeae7` renders the target animal label at **18 px** (`FontRole.DISPLAY`).
   - This sits at Greia's lower child-facing typography guardrail and must be reworked rather than represented as 22 px.

2. **Target card geometry**
   - local audit records `[352, 24, 320, 84]`;
   - accepted source uses **`[352, 14, 320, 94]`**.
   - Future audits must be generated from runtime/source values, not manually transcribed.

3. **Large interface claim**
   - local audit says `controls_scaled: true` for the 1024×600 Large row;
   - the Nascondino HUD card/text geometry in accepted source is fixed on the 1024×600 reference canvas and does not use the profile `InterfaceSize` preference for those controls.
   - The screenshot may still be usable, but the claim that this HUD itself scales for Large is unsupported by source.

4. **1920×1080 fit description**
   - local review says letterbox/pillarbox;
   - `forest_meadow_day_v1.toml` explicitly uses **`fit = "cover"`**.
   - At differing aspect ratios the scene is symmetrically cropped, not letterboxed/pillarboxed. Critical content is intended to remain in the declared central safe span.

5. **Performance wording/value**
   - local run summary reports **258 frames / 10.01 s = 25.8 FPS**;
   - some documentation text still says ~27.5 FPS / "rock-solid".
   - Keep the measured 25.8 FPS value and treat simulator timing as regression sanity only, not low-resource physical performance proof.

## Disposition

The scene compositor integration is retained as a valid **runtime/architecture proof with simulator evidence**, but the primary agent does not promote the local agent's prose audit to an independently verified pixel review.

Before the Nascondino visual tranche is treated as visually closed:

- increase/reflow the target HUD so meaningful text is comfortably above the lower guardrail;
- make the Large interface preference genuinely affect the Activity HUD or stop claiming it does;
- regenerate the layout audit from actual runtime/source geometry;
- describe `cover` crop semantics correctly;
- retain the measured simulator FPS without embellishment.

These corrections are folded into the next scene/actor integration gate rather than starting another standalone micro-validation cycle.
