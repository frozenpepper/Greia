# Primary Review — Canonical Cast Expansion (Leo, Flash, Dani)

**Date:** 2026-08-22  
**Authority:** `docs/testing/2026-08-22_CANONICAL_CAST_EXPANSION_LEO_FLASH_DANI.md`  
**Candidate Workspace:** `assets/visual/pack_candidates/canonical_cast_expansion/2026-08-22/`  
**Review Sheets:** `docs/reviews/visual/2026-08-22_canonical-cast-expansion/` (14 PNGs)

---

## 1. Executive Summary

This gate completes the maintainer-side visual design package for Greia's **six-character canonical ensemble**:
- **Lilli** (unicorn Puff — creativity / stories / art)
- **Leo** (owl Bean — learning / reading / knowledge) [Refined from Nino with signature teal glasses]
- **Flash** (rabbit Puff — games / action / playful challenge) [New energetic raspberry rabbit]
- **Dani** (friendly robot — math / logic / patterns) [New sky-blue toy-like logic friend]
- **Tito** (fox Puff — exploration / discovery)
- **Momo** (friendly monster Puff — emotion / music / silly play)

The candidate package delivers:
- **15 new finished state SVGs** across Leo, Flash, and Dani (5 registered states each: `neutral`, `blink`, `happy`, `surprised`, `sleepy`);
- **3 new source master SVGs** with clean semantic layer grouping;
- **9 standalone authoring components** (3 per character);
- **14 curated review PNGs** covering ensemble alignment, silhouette separation, multi-scale readability down to 64px, role mapping, and shared motion storyboards.

---

## 2. Answers to Section 14 Evidence Questions

### Q1: Is Leo readable as the same broad owl family while clearly superseding Nino's identity/name?
**Yes.** Leo preserves the chestnut bean silhouette, ear tufts, wing scallops, cream belly, and amber beak/feet of the owl archetype, while establishing his distinct persona as the studious, curious learning mascot via signature teal rounded glasses. The teal feather badge was removed to eliminate visual clutter.

### Q2: Do the glasses remain readable without double-ring/goggle clutter?
**Yes.** By redesigning the facial mask with soft integrated rectangular lens backings rather than drawing glasses over heavy circular outline rings, Leo's face is clean and readable at 128px and 64px. The teal frame (`#0D9488`) provides crisp contrast without double-stroking.

### Q3: Can Flash be distinguished from Tito and Lilli by silhouette alone at 64/128 px?
**Yes.** As proven in `08-six-character-silhouettes.png`:
- **Flash** features unmistakable tall, perked rabbit ears with forward energy, a compact springy body stance, and a small round cream pom-pom tail.
- **Tito** features broad triangular fox ears and a massive bushy side-swept tail.
- **Lilli** features a centered golden horn and 3-ribbon curved forelock tuft.
At silhouette-only review, Flash cannot be mistaken for either Tito or Lilli.

### Q4: Does Dani read as a character rather than a device icon at 64/128 px?
**Yes.** Dani combines soft toy-like pill-rounded chassis corners, expressive digital eye arcs, a glowing antenna bulb with reflection highlight, and pill-roller feet. He reads clearly as a warm, friendly character rather than a flat smartphone/app icon or cold robot.

### Q5: Are `blink`, `happy`, `surprised`, and `sleepy` genuinely distinguishable for Leo/Flash/Dani at claimed sizes?
**Yes.** As verified in `09-new-character-expression-small-size.png`:
- At 128px, all expressions are distinct and expressive.
- At 64px, `happy` (upturned crescent eyes + open smile), `surprised` (large dilated round eyes + open mouth), and `blink`/`sleepy` remain readable due to clear value contrast against the faceplates.

### Q6: Do all six feel like one cast without becoming six clones?
**Yes.** The six characters share common stroke weights (3.5px primary, 2.5px secondary), warm grounding contact shadows, soft gradients, and toy-diorama charm, yet feature 6 distinct geometric silhouettes (Puff, Bean, Tall-Ear Rabbit, Box-Robot, Bushy-Tail Fox, Scallop Monster) and unique color palettes.

### Q7: Did any existing Lilli/Tito/Momo art need alteration? If yes, why exactly?
**No.** Lilli, Tito, and Momo candidate SVGs from `canonical_characters/2026-08-22` were preserved completely intact as reviewed anchors. The new characters were designed to harmonize with and contrast against them without requiring modifications to the existing art.

---

## 3. Review Sheets Inventory

| Sheet | Filename | Description |
| :---: | :--- | :--- |
| **01** | `01-four-character-anchor.png` | Baseline reviewed 4-character candidate reference (Lilli, Nino, Tito, Momo) |
| **02** | `02-six-character-neutral-ensemble.png` | Full 6-character neutral ensemble lineup side-by-side |
| **03** | `03-nino-to-leo-refinement.png` | Direct side-by-side comparison of Nino vs Leo with integrated glasses |
| **04** | `04-leo-state-matrix.png` | Leo 5-state matrix: Neutral, Blink, Happy, Surprised, Sleepy |
| **05** | `05-flash-state-matrix.png` | Flash 5-state matrix: Neutral, Blink, Happy, Surprised, Sleepy |
| **06** | `06-dani-state-matrix.png` | Dani 5-state matrix: Neutral, Blink, Happy, Surprised, Sleepy |
| **07** | `07-six-character-multiscale.png` | Multi-scale inspection across all 6 characters at 256px, 128px, and 64px |
| **08** | `08-six-character-silhouettes.png` | Zero-color silhouette validation proving geometric separation at 128px & 64px |
| **09** | `09-new-character-expression-small-size.png` | Leo, Flash, and Dani expression readability at 128px and 64px |
| **10** | `10-role-map.png` | Neutral presentation of the 6 soft primary mascot domains |
| **11** | `11-happy-hop-all-six.png` | Shared motion storyboard: `happy_hop` across all 6 characters |
| **12** | `12-secondary-motion-all-six.png` | Secondary motion storyboard: `surprised_wobble` across all 6 characters |
| **13** | `13-new-source-component-structure.png` | Semantic SVG layer grouping & authoring components for Leo, Flash, and Dani |
| **14** | `14-detail-crops.png` | High-resolution close-ups of glasses, rabbit ears, robot screen & antenna |

---

## 4. Architectural Boundary Confirmation

- **Zero runtime code altered:** `SceneActorDefinition`, `greia_launcher`, Activities, and platform Collections remain untouched.
- **Zero catalogue promotions:** Candidates reside solely in `assets/visual/pack_candidates/canonical_cast_expansion/2026-08-22/` awaiting owner pixel review.
