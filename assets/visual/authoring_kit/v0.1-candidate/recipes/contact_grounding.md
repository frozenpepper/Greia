# Greia Recipe — Contact Grounding

**Status:** Candidate Authoring Recipe (v0.1)  
**Parent Authority:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`

---

## 1. The Grounding Formula (Eliminating the Flying Object Flaw)

To prevent objects from appearing suspended or flying above the ground:

1. **Rule 1 — Outward Flare or Flat Line:**
   - Base width must be at its widest at the soil line ($y=455$ for trees, $y=226$ for rocks/bushes).
   - Never taper inward at the bottom.
2. **Rule 2 — Dual-Pass Contact Shadow:**
   - **Pass A (Tight Occlusion):** Dark, dense ellipse (`#1C120A` / `#0F1415`, opacity `0.30..0.35`) directly overlapping the bottom edge.
   - **Pass B (Soft Ambient Spread):** Wider blurred ellipse (`opacity 0.18..0.20`, `blur 6..8px`) spreading softly around the base.
3. **Rule 3 — Turf Anchoring:**
   - In composed scenes, overlap the foreground grass blades / clover patches slightly over the bottom root flare for complete environmental integration.