# Greia Visual Library — Active Plan

**Status:** ACTIVE  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`

This plan is intentionally simple.

Greia is building **one shared visual library** that every Greia surface can reuse:

1. a small character library;
2. a shared animation library;
3. a shared artwork library (props, scenes, FX, UI pieces);
4. one shared consumption system for Shell and Activities.

The visual style is the already accepted constraint-native Greia style: simple cute characters, strong expressions, simple motion, chunky illustrated assets.

---

## Current checkpoint

| Field | State |
|---|---|
| Current milestone | **L1 — character + base animation library** |
| Core characters | **Lilli, Nino, Tito, Momo** |
| Current character states | accepted neutral art + **real blink variants for all four** |
| Base animations | `idle_bounce`, `blink`, `happy_hop`, `celebrate_pop`, `surprised_wobble`, `sleepy_sway` |
| Current shared library | `assets/visual/library/` + `assets/visual/characters/` |
| Current rule | animation work MUST reuse the same character art; it must not redraw/degrade the character |
| Next exact work | add the small useful shared expression set (`happy`, `surprised`, `sleepy`) for Lilli/Nino/Tito/Momo, then keep expanding the same library rather than inventing new architecture |
| Next milestone | **L2 — props, backgrounds/scenes, FX and UI artwork library** |
| Later milestone | **L3 — shared runtime consumption helpers/catalogue for all Greia surfaces** |

### Progress tracking

Every substantive session updates this checkpoint and appends one short entry under **Progress log**:

- what library assets were added/changed;
- what was visually reviewed;
- what failed/rejected;
- next exact work item;
- commit SHA.

No extra phase machinery is required.

---

# L1 — Small character + animation library

Initial shared cast:

- **Lilli** — unicorn Puff
- **Nino** — owl Bean
- **Tito** — fox Puff
- **Momo** — friendly monster Puff

The character must remain visually the same character across animation/expression states.

Shared motions:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Rules:

- `blink` MUST actually display closed eyes;
- use simple whole-character translate/rotate/squash/stretch;
- expression changes use authored variants of the same character;
- no character redraw per animation;
- no detailed rigging;
- no anatomy-specific animation requirement;
- motion is optional enrichment; static art remains valid.

L1 is complete when the four core characters have the small set of useful shared expression states and all six motions can be demonstrated without degrading their accepted look.

---

# L2 — Shared artwork library

Build a useful reusable library instead of drawing every Activity from scratch.

Initial families:

```text
props/
  nature/
  learning/
  workshop/
  clinic/
  toys/
  transport/

environments/
  meadow/
  forest/
  workshop/
  clinic/
  reading/
  night/

fx/
  sparkles/
  stars/
  hearts/
  puffs/
  glow/
  confetti/

ui/
  buttons/
  cards/
  bubbles/
  panels/
  trays/
  reward_frames/
```

Start small and reusable. Prefer a good shared asset over many nearly identical local assets.

---

# L3 — Shared system for all Greia surfaces

Once the library is useful, expose it through one shared Greia consumption path.

Goals:

- Shell and Activities reference semantic asset IDs;
- no Activity-private copy of a shared asset;
- no per-frame file/decode work;
- Python/Pygame first, Web uses the same semantic catalogue later;
- simple fallback when animation is disabled;
- existing Greia UI/runtime architecture remains authoritative.

Do not build multiple competing animation/asset systems.

---

# Model/contributor rule

Before creating visual content:

1. inspect the shared Greia visual library;
2. reuse it where possible;
3. create a new asset only when needed;
4. keep it inside the accepted Greia visual style;
5. add it back to the shared library when it is broadly reusable.

The practical model guide remains:

`skills/greia-visual-authoring/SKILL.md`

---

# Rejected work

Retained only so it is not repeated:

- detailed traditional quadruped rigging as the default;
- generated sprite sheets assumed to be production animation;
- recreating characters into visibly worse vector art for animation;
- changing/redrawing the character while supposedly testing motion;
- fake face overlays that break the original art;
- a `blink` animation that does not actually blink;
- unrelated Object Friend experiments while the core character library is unfinished.

---

# Progress log

## 2026-08-20 — Visual direction established

- Constraint-native Puff/Bean/etc. direction chosen.
- Lilli, Nino, Tito, Momo accepted as static style anchors.
- Earlier detailed-character/rig approaches rejected.

## 2026-08-20 — Overcomplication rejected; plan simplified

- The workstream drifted into excessive expression/motion architecture and bad review harnesses.
- One harness degraded character faces; a later correction preserved the art but still failed to implement a real blink.
- Owner clarified the actual goal: **artwork library + animation library + small character library + one shared system**.
- The workstream was simplified to L1/L2/L3.

## 2026-08-20 — L1 shared library started correctly

- Added a real authored blink variant for **Lilli, Nino, Tito and Momo**, preserving the accepted A1 character artwork.
- Added `assets/visual/library/README.md`, `catalog.toml`, `animations.toml`, and `review.html`.
- The shared review now uses the accepted A1 neutral artwork and swaps to the authored blink art for `blink`; it does not redraw faces.
- Retired the previous bad A2 review harness and marked the old A2 specimen directory historical.
- Removed the accidental placeholder file.

### Commits

- simplify plan: `d80b8731eeff4c9281803a244834595cb0cdb026`
- simplify motion spec: `9cf7161b1c438ba152b4e57ac6515a8b7f78aae9`
- Lilli blink: `91d85950f3c1f4be3a9d65385efb3eb8e9180190`
- Nino blink: `975e351d1be517c16869a09113a70cc4a5361142`
- Tito blink: `c47422ea014b0ca499a385c0c3afd872e72fcce4`
- Momo blink: `64dfc69cdc1baea185830ee1b2d3b6d1a0527d27`
- shared library seed: `4dbe9c645c578cbbe6c9de85eaad344ebd4f91f9`
- animation catalog: `0789b77e3777fb00e1fb024457f32e1a6483b665`
- visual catalog: `c3fac5c87913de2e6b73e4b1b25c2f2d1c91a724`
- shared review: `06d6812785492e09f47f41542c7a064ee56f3624`
- retire bad A2 review: `9785cb73940984fdd20c72f56d19d8002332c94e`
- mark old A2 historical: `30b6a8bfa83e305d54a0f0af915ef7a2b625a7e3`
- remove obsolete placeholder: `4f1889968a2f3b8b2f98957045b27adade9e7716`

### Next exact action

Add the small reusable `happy`, `surprised`, and `sleepy` expression variants to the same four character packages, visually review them, and then continue directly into reusable props/scenes/FX/UI assets.