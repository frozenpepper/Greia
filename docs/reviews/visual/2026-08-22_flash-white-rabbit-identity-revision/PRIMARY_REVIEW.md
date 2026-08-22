# Owner Primary Review — Flash White-Rabbit Identity Revision

**Date:** 2026-08-22  
**Candidate commit:** `fba60ff31c8bb7e825163bb349e349bd1b72d0f3`  
**Candidate source:** `assets/visual/pack_candidates/flash_identity_revision/2026-08-22/`  
**Evidence reviewed:** all 10 PNGs from `GREIA_VISUAL_REVIEW_FLASH_WHITE_RABBIT_REVISION_2026-08-22.zip`, plus `REVIEW.md` and `audit.json`  
**Previous six-cast candidate:** `cfbb9512723353dd34f6081c174410401e290ca8`

## 1. Verdict

**ACCEPT — Flash revision closes the remaining pure-art blocker for the six-character canonical cast.**

The revised Flash is materially better than the raspberry-bodied candidate and should become the canonical Flash source for the first promoted cast version.

The current six-character source lineup is therefore accepted for promotion:

```text
Lilli — current 2026-08-22 canonical-character candidate
Leo   — current 2026-08-22 cast-expansion candidate
Flash — white-rabbit identity revision from this gate
Dani  — current 2026-08-22 cast-expansion candidate
Tito  — current 2026-08-22 canonical-character candidate
Momo  — current 2026-08-22 canonical-character candidate
```

No further pure-art cast iteration is authorized before promotion/runtime integration unless implementation exposes a concrete source defect.

## 2. Pixel-level findings

### 2.1 Flash now reads as a rabbit first

The prior raspberry candidate read first as a colored round mascot and only second as a rabbit. The revised candidate fixes that hierarchy:

- white/warm-white fur is now the dominant animal mass;
- tall pink-inner ears immediately carry rabbit identity;
- the small round tail remains a useful secondary species cue;
- the coral shirt is visually separate from the white fur;
- the golden bolt creates an immediate speed/energy cue without tying Flash to one specific game.

The direct old/new sheet and the Lilli/Flash/Tito comparison both support this conclusion.

### 2.2 The shirt treatment is sufficient

On the compact Puff anatomy, the shirt reads closer to a simple jersey/bib-like torso garment than a fully anatomical T-shirt with explicit sleeves. That is acceptable for the Greia character grammar: it is clearly a clothing/color layer rather than an anatomical fur patch, and adding sleeves/shorts/shoes would risk over-designing the mascot.

Do not reopen Flash merely to make the clothing more anatomically literal.

### 2.3 Lightning-bolt readability

At 256 and 128 px the lightning bolt reads clearly as a bolt. At 64 px the exact zig-zag shape is smaller, but the high-contrast golden action-emblem mass remains visible enough to reinforce identity.

Do not turn this into a guarantee that every tiny emblem detail is semantically readable at 64 px. At 64 px the primary contract remains rabbit silhouette + white/coral color mass + readable face.

### 2.4 Species separation is strong

The revised Flash is now clearly distinct from both nearby mammal silhouettes:

```text
Lilli → cream unicorn / horn / rainbow forelock / gentle Puff
Flash → white rabbit / long ears / coral torso / bolt / pom tail
Tito  → orange fox / triangular ears / large bushy tail
```

This distinction survives the supplied 128/64 evidence without relying only on labels.

### 2.5 Five-state system remains usable

The revised `neutral`, `blink`, `happy`, `surprised`, and `sleepy` states remain registered and coherent.

At 64 px, `happy` and `surprised` separate most strongly; `blink` and `sleepy` are naturally closer because both use closed/low eyes. This is acceptable at icon scale because the full character state system is primarily useful at larger dialogue/world sizes, while 64 px needs identity and broad emotional readability rather than fine eyelid taxonomy.

### 2.6 Six-character ensemble is accepted

The revised ensemble now has useful visual and semantic separation:

```text
Lilli → warm cream / magical
Leo   → chestnut + teal glasses / thoughtful
Flash → white + coral / energetic
Dani  → cyan / precise friendly robot
Tito  → terracotta / exploratory
Momo  → purple / playful-emotional
```

They share outline/face/grounding grammar without becoming six recolors of one body.

## 3. Canonical source decision

The first canonical promoted source version should use:

```text
character.lilli
character.leo
character.flash
character.dani
character.tito
character.momo
```

Each supports the five source states:

```text
neutral
blink
happy
surprised
sleepy
```

Historical `character.nino` remains provenance. Do not rewrite old review evidence or silently pretend Nino never existed. Current product identity is Leo.

## 4. Runtime architecture decision

The accepted runtime direction remains deliberately cheap:

> complete authored state renditions + semantic state selection + whole-character translation motion.

Do not introduce:

- skeletal/bone rigs;
- runtime limb composition;
- continuous per-frame raster-size churn for squash/stretch;
- continuous per-frame rotated-surface allocation merely to mimic storyboard angles;
- frame-by-frame sprite explosions.

For the first runtime gate, shared motions may be realized with fixed-size state swaps and bounded positional offsets. The semantic vocabulary matters more than reproducing every storyboard transform literally.

## 5. Next exact gate

Execute:

`docs/testing/2026-08-22_CANONICAL_CAST_V01_PROMOTION_RUNTIME_SIMULATOR.md`

This gate owns:

1. stable six-character source promotion;
2. explicit Nino→Leo current-identity migration while preserving provenance;
3. build-time PNG rendition selection for all six × five states;
4. minimal renderer-neutral semantic expression/motion support;
5. automated source/build tests;
6. real runtime visual/fallback/responsive acceptance through the Greia Activity Simulator;
7. curated owner-review screenshots and transfer ZIP.

No additional character-art gate precedes it.

## 6. Evidence boundary

This review accepts **source art/design** only.

It does not yet prove:

- generated runtime PNG correctness for all 30 states;
- runtime semantic state switching;
- runtime shared motion behavior;
- cache/resource behavior;
- fail-soft behavior;
- responsive Activity integration;
- physical Acer/Pi performance;
- Web runtime support;
- optional Activity `lead_character` metadata.

Those belong to the next simulator/runtime gate.