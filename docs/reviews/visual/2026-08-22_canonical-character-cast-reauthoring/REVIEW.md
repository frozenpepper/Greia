# Greia Canonical Character Cast — Reauthoring and State-Set Review

**Date:** 2026-08-22  
**Authority:** `docs/testing/2026-08-22_CANONICAL_CHARACTER_CAST_REAUTHORING_AND_STATE_SET.md`  
**Candidate Workspace:** `assets/visual/pack_candidates/canonical_characters/2026-08-22/`  
**Review Sheets:** `docs/reviews/visual/2026-08-22_canonical-character-cast-reauthoring/` (13 PNGs)

---

## 1. Executive Summary & Cast Scope

This gate delivered a complete maintainer-side reauthoring pass across Greia's 4 canonical recurring characters:
- **Lilli** (unicorn Puff — wonder, kindness, imagination)
- **Nino** (owl Bean — observation, books, thoughtfulness)
- **Tito** (fox Puff — playful curiosity, exploration)
- **Momo** (friendly monster Puff — humor, emotion, experimentation)

For each character, the candidate workspace provides:
- **5 complete finished state SVGs** (`neutral`, `blink`, `happy`, `surprised`, `sleepy`) registered on a shared 256×256 logical canvas (20 finished state SVGs total);
- **1 semantically grouped source master SVG** (`source_master.svg`);
- **3 high-value character-specific authoring components** (`components/` directory);
- Comprehensive candidate metadata in `catalog.toml` and `README.md`.

---

## 2. Review Sheets Inventory

| Sheet | Filename | Description |
| :---: | :--- | :--- |
| **01** | `01-current-a1-baseline-cast.png` | Baseline A1 style anchors from `assets/visual/specimens/a1/` |
| **02** | `02-candidate-neutral-cast.png` | Reauthored 2026-08-22 neutral candidate cast side-by-side |
| **03** | `03-lilli-state-matrix.png` | Lilli 5-state matrix: Neutral, Blink, Happy, Surprised, Sleepy |
| **04** | `04-nino-state-matrix.png` | Nino 5-state matrix: Neutral, Blink, Happy, Surprised, Sleepy |
| **05** | `05-tito-state-matrix.png` | Tito 5-state matrix: Neutral, Blink, Happy, Surprised, Sleepy |
| **06** | `06-momo-state-matrix.png` | Momo 5-state matrix: Neutral, Blink, Happy, Surprised, Sleepy |
| **07** | `07-small-size-cast-matrix.png` | Multi-scale inspection at 256px (hero), 128px (card/dialog), 64px (icon) |
| **08** | `08-expression-small-size-matrix.png` | Low-resolution expression readability verification at 128px and 64px |
| **09** | `09-motion-storyboards-a.png` | Motion storyboards: `idle_bounce`, `blink`, `happy_hop` |
| **10** | `10-motion-storyboards-b.png` | Motion storyboards: `celebrate_pop`, `surprised_wobble`, `sleepy_sway` |
| **11** | `11-shared-motion-personality-proof.png` | Shared semantic motion (`happy_hop`) executed across all 4 characters |
| **12** | `12-source-component-structure.png` | Semantic SVG layer grouping & authoring components breakdown |
| **13** | `13-detail-crops.png` | Source-resolution crops of facial details, material cues & identity marks |

---

## 3. Conservative Producing-Agent Self-Assessment

### 3.1 Strengths
1. **Silhouette & Identity Stability:** All 4 characters immediately preserve their accepted visual identity anchors (Lilli horn/forelock, Nino eye disks/mask/feather, Tito ears/muzzle/tail, Momo antennae/fluff/tooth).
2. **Registration Integrity:** Neutral→Blink and Neutral→State swaps maintain clean zero-drift body registration without geometric jumps.
3. **Motion Vocabulary Suitability:** All 5 authored states directly support the 6 semantic runtime motions (`idle_bounce`, `blink`, `happy_hop`, `celebrate_pop`, `surprised_wobble`, `sleepy_sway`) using simple whole-character transforms.
4. **Authoring System Utility:** Semantic SVG layer IDs (`#body`, `#face`, `#eyes`, `#mouth`, etc.) and standalone components (`horn.svg`, `wings.svg`, `tail.svg`, `antennae.svg`, `eyes_blink.svg`) provide high authoring leverage without runtime architectural complexity.

### 3.2 Known Limitations & Candidate Cautions
1. **64px Detail Limits:** While primary silhouettes, eyes, and color cues remain readable at 64px, subtle secondary details (e.g. Lilli's star mark, Nino's bookish feather badge, Momo's single tooth) are primarily readable at >=128px.
2. **Candidate Status Only:** No runtime manifests or shared visual catalogs were modified during this gate. Promotion into `assets/visual/characters/` or `shared_visuals_v1_source.toml` remains reserved for owner pixel review.
