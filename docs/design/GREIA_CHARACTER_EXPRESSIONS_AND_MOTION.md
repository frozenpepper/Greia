# Greia Character Expressions and Base Motion — A2 Candidate Specification

**Status:** A2 candidate design specification  
**Date:** 2026-08-20  
**Active plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Character grammar:** `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md`

## 1. Purpose

Greia's simplified characters derive life primarily from **face state + whole-body transform + one or two optional identity-cue reactions**. The base animation vocabulary must work across Puff, Bean, Cutout Critter and Object Friend without assuming knees, elbows or a species-specific skeleton.

The goal is not identical choreography. The goal is identical **semantic meaning**.

## 2. Face-state model

A reusable character works toward these semantic states:

| State | Primary cue | Secondary cue |
|---|---|---|
| `neutral` | open relaxed eyes | small friendly mouth |
| `happy` | smiling/closed-happy eyes or bright open eyes | wider smile, optional stronger cheeks |
| `excited` | open/bright eyes | open happy mouth, optional upward body energy |
| `surprised` | visibly wider/rounder eyes | small `o` mouth/recoil |
| `sleepy` | closed or half-lid eyes | small relaxed mouth/body compression |
| `sad_gentle` | softened upper-eye/brow angle | shallow down curve; never shame/anger |
| `thinking` | pupils/look direction or asymmetric eye cue | tiny tilt/question cue |
| `proud` | relaxed bright eyes | tiny upward smile/chest/body lift |
| `silly` | playful asymmetry | tongue/odd mouth or pupil variation if still readable |

At 128 px the emotional state must remain obvious. At 64 px the state should remain readable where that size is an intended use.

## 3. Base motion rule

Every semantic motion is defined in normalized terms:

- phase / time;
- whole-body translation;
- whole-body rotation;
- squash/stretch;
- expression cue;
- optional identity-attachment response;
- optional bounded FX;
- static fallback.

No semantic motion definition may require a horse knee, human elbow, front/back gait rig, or other anatomy absent from the archetype.

## 4. Base Animation Set v0.1

### `idle_bounce`

- **Duration:** nominal 2.0 s, allowed 1.6–2.4 s.
- **Loop:** yes.
- **Meaning:** alive, calm, available.
- **Motion:** up/down travel <= ~3.5% body height; rotation <= 2°; scale change <= 2.5%.
- **Expression:** neutral; occasional blink may be injected.
- **Static fallback:** neutral still.

### `blink`

- **Duration:** nominal 0.22 s, allowed 0.15–0.30 s.
- **Loop:** no; may be scheduled inside idle.
- **Phases:** close 0–35%; hold 35–55%; reopen 55–100%.
- **Motion:** face only by default.
- **Static fallback:** neutral still. A blink itself carries no essential meaning.

### `happy_hop`

- **Duration:** nominal 0.90 s, allowed 0.70–1.10 s.
- **Loop:** no.
- **Phases:** anticipation 0–18%; launch 18–42%; apex 42–58%; fall 58–78%; landing/settle 78–100%.
- **Motion:** hop <= ~22% body height; squash/stretch <= ~10%; rotation <= 2.5°.
- **Expression:** happy from launch through settle.
- **Static fallback:** happy still.

### `celebrate_pop`

- **Duration:** nominal 1.15 s, allowed 0.90–1.40 s.
- **Loop:** no.
- **Phases:** anticipation 0–14%; pop 14–38%; apex 38–52%; settle 52–82%; tiny rebound 82–100%.
- **Motion:** travel <= ~28% body height; squash/stretch <= ~12%; rotation <= 4°.
- **Expression:** happy/excited.
- **FX:** optional stars/sparkles/hearts; bounded, short-lived.
- **Static fallback:** happy still, optionally with a single static reward mark.

### `surprised_wobble`

- **Duration:** nominal 0.72 s, allowed 0.50–0.90 s.
- **Loop:** no.
- **Phases:** recoil 0–20%; alternating overshoot 20–68%; settle 68–100%.
- **Motion:** rotation <= 7°; translation small; scale change <= 6%.
- **Expression:** surprised for the reaction, then neutral/happy depending on context.
- **Static fallback:** surprised still.

### `sleepy_sway`

- **Duration:** nominal 2.4 s, allowed 1.8–2.8 s.
- **Loop:** yes.
- **Meaning:** low energy, rest, nighttime, waiting.
- **Motion:** rotation <= 4°; travel <= ~2.5% body height; compression <= 4%.
- **Expression:** sleepy.
- **Static fallback:** sleepy still.

## 5. Archetype mapping

### Puff

The body mass does most of the acting. Tiny feet/arms/tail/tuft may lag or react, but the motion must still work when those extras are absent.

### Bean

The upright mass may sway slightly more. Wings/flaps may open for celebration, but they are not required for semantic clarity.

### Object Friend

Preserve the pedagogical silhouette first. A number/letter/tool must remain identifiable throughout squash/rotation. Keep distortion more conservative if deformation risks confusing the symbol.

### Cutout Critter

Use layer transforms sparingly. The flat cutout look is intentional; do not add pseudo-anatomy just because layers exist.

## 6. Easing language

Use a tiny shared family instead of bespoke easing per asset:

- `soft_in_out` — calm loops such as idle/sleepy;
- `anticipate_pop` — small squash then quick launch;
- `settle_bounce` — one restrained landing rebound;
- `damped_wobble` — alternating rotation with decreasing amplitude;
- `snap_blink` — fast eye close/open.

Exact renderer implementations may differ, but semantic phase timing should remain comparable.

## 7. Static fallback matrix

| Motion | Required still |
|---|---|
| `idle_bounce` | `neutral` |
| `blink` | `neutral` |
| `happy_hop` | `happy` |
| `celebrate_pop` | `happy` or `excited` |
| `surprised_wobble` | `surprised` |
| `sleepy_sway` | `sleepy` |

Meaning must survive with animation disabled.

## 8. Existing runtime seam assessment

`src/greia_platform/ui_motion.py` is a good architectural precedent:

- immutable renderer-neutral samples;
- mathematical bounded motion;
- no retained heavyweight animation framework;
- cheap sampling suitable for low-resource hardware;
- presentation semantics do not grant input authority.

Its current `MotionSample` is intentionally UI-control-oriented (`scale`, x/y offset, `shadow_lift`) and does **not** yet represent character rotation, anisotropic squash/stretch, face state, or optional attachment/FX cues.

Therefore A2 does **not** extend the runtime yet. A future runtime-facing character-motion seam should follow the same lightweight/polymorphic philosophy after the blocking architecture/runtime review, rather than creating an unrelated animation engine inside Activities.

## 9. A2 specimen review

The review specimen must demonstrate all six motions on at least:

- Lilli — Puff;
- Nino — Bean;
- Object Friend number 3.

It uses the exact A1 character body masters with semantic face-state overlays/variants, and applies only bounded whole-image transforms plus bounded FX. It is a design/evidence harness, not runtime source.

## 10. Acceptance

A2 can close when:

- the expression vocabulary is accepted;
- all six motions read correctly across Puff, Bean and Object Friend;
- static fallbacks remain understandable;
- the motions do not require detailed anatomy;
- the visual result remains charming rather than robotic;
- the runtime seam assessment remains compatible with accepted Greia architecture;
- any simulator/performance evidence required by the active plan is recorded honestly.
