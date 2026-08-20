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
| Current required character states | `neutral`, `blink` first; add shared happy/surprised/sleepy states as the library grows |
| Base animations | `idle_bounce`, `blink`, `happy_hop`, `celebrate_pop`, `surprised_wobble`, `sleepy_sway` |
| Current rule | animation work MUST reuse the same character art; it must not redraw/degrade the character |
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
- The workstream is simplified to L1/L2/L3 above.
- Next exact action: build the real L1 shared character/animation library from the accepted art, starting with an actual blink and the six shared motions.