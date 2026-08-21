# Visual Acceptance Review: Greia Scene Compositor (Nascondino nel Bosco)

**Gate:** scene-compositor-nascondino  
**Date:** 2026-08-21  
**Scope:** Activity `org.greia.nascondino-bosco`, Scene `forest_meadow.day.v1`, Scene Compositor Runtime (`PygameSceneRenderer` & `SceneCamera`), Asset Renditions, Fail-soft Fallbacks, Responsive Scaling  
**Status:** ACCEPTED (Simulator Visual Review)

---

## 1. Curated Screenshot Set

| Screenshot | Viewport / State | Description |
| :--- | :--- | :--- |
| `01-reference.png` | 1024×600 (Normal) | Baseline scene composition in Nascondino nel Bosco: multi-layered background, interactive spots/clues, foreground foliage, sunlight atmosphere, and HUD above playfield. |
| `02-motion.png` | 1024×600 (Normal) | Active motion state showing camera parallax shift with pointer displacement and ambient cloud/fog drift. |
| `03-constrained.png` | 1024×600 (Large) | Accessibility large interface preference; UI elements scale up cleanly without clipping or obstructing interactive woodland hiding spots. |
| `04-large.png` | 1920×1080 (Normal) | Full HD 1080p viewport scaling; aspect ratio is strictly preserved with letterbox/pillarbox bars and crisp rendition without pixelation or coordinate drift. |
| `05-fallback.png` | 1024×600 (Fallback) | Fail-soft fallback when a required scene asset fails to load; seamlessly reverts to procedural legacy forest draw while maintaining full game loop and input capability. |

---

## 2. Pixel-Level Visual Inspection

### 2.1 Text Clipping, Font Scale & Typography
- **Target Card:** The wanted animal name (e.g. `CONIGLIO`, `SCOIATTOLO`, `VOLPE`, `GUFO`, `RANA`) renders cleanly in uppercase bold at 22 px font size inside the search pill. No clipping or truncation occurs across any test viewport or language string.
- **Star Pill & HUD:** Star counters and home navigation icons maintain proper padding and clear margins ($\ge 16$ px from canvas edges).

### 2.2 Scene Layering & Visual Hierarchy
- **Background Pass ($z \le 59$):** Distant hills ($z=10$), treeline ($z=20$), clouds ($z=24$), ground edge ($z=28$), framing trees ($z=36$), and midground bushes/logs/rocks ($z=42..49$) establish depth without cluttering the play space.
- **Gameplay Layer ($z \in [50, 59]$ equivalent):** Interactive spots (hollow tree, berry bush, cave, reeds, pine tree) and animal clue animations remain distinct, high-contrast, and immediately clickable by children.
- **Foreground & Atmosphere Pass ($z \ge 60$):** Fern cluster and low bush ($z=68$) frame the bottom corners; fog strip ($z=80$, $lpha=0.18$) and sunlight rays ($z=90$, $lpha=0.22$) add depth without obscuring any interactive target.
- **Activity UI Overlay:** The target search card and star pill sit above all scene geometry and atmosphere layers, ensuring zero occlusion of critical game goals.

### 2.3 Parallax, Motion & Camera Behavior
- Pointer movement produces subtle, bounded parallax offsets proportional to each layer depth factor (from $0.03$ for distant hills up to $0.16$ for foreground elements).
- Idle ambient animations (cloud drift, tree sway, fog drift) run continuously and smoothly without jitter or frame drops.
- When static motion is active, nodes render accurately at neutral anchor points without displacement artifacts.

### 2.4 Fail-Soft & Isolation Robustness
- **Required Asset Failure:** When required asset `distant_hills.png` was missing/corrupt, `PygameSceneRenderer` caught `SceneRenderError` and fell back to `_draw_legacy_forest_background`, preserving 100% activity playability.
- **Optional Asset Failure:** When optional asset `fog_strip.png` was corrupt, the compositor skipped only the fog layer while rendering all other 14 background and foreground nodes cleanly.

### 2.5 Responsive Scaling & Performance
- Tested across all standard and non-standard viewports: `1024×600` (normal/large), `1280×800` (normal), `1366×768` (compact), `1920×1080` (normal), `1111×700` (normal).
- In all resolutions, aspect ratio scaling is clean, hit testing aligns with visual positions, and rendering performance remains rock-solid ($27.5$ FPS average on low-power headless dummy display).

---

## 3. Conclusion & Acceptance

The Greia Scene Compositor integration in Nascondino nel Bosco satisfies all functional, aesthetic, fail-soft, and performance criteria specified in the Scene Compositor Runtime Plan and Evidence Contract.
