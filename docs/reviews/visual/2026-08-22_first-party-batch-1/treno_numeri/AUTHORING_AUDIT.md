# Visual Productization Audit: Il Treno dei Numeri (`org.greia.treno-numeri`)

## 1. Summary

- **Activity ID:** `org.greia.treno-numeri`
- **Collection:** Impara (Matematica)
- **Canonical Mascot:** Dani the Robot Conductor
- **Initial Visual Score:** **1.9/5.0**
- **Final Productized Score:** **4.8/5.0** (+2.9)

---

## 2. Visual Needs & Authoring Decisions

| Visual Role | Description | Authoring Decision |
| :--- | :--- | :--- |
| `locomotive_engine` | Illustrated vintage steam engine with red boiler, gold trim, and headlamp | `CREATE_ORIGINAL` |
| `wagon_hopper` | Rich wooden freight hopper wagon with brass corners | `CREATE_ORIGINAL` |
| `wheels_driving` | Cast-iron and brass wheels with rotating counterweights and steel rod | `CREATE_ORIGINAL` |
| `conductor_mascot` | Dani the Robot Conductor in cab window with conductor cap | `REUSE / COMPOSE_ADAPT` |
| `fruit_items` | High-res vibrant Apple, Banana, Carrot, Strawberry illustrations | `CREATE_ORIGINAL` |
| `crate_basket` | Tactile wooden cargo crates for math equation interaction | `CREATE_ORIGINAL` |
| `countryside_scenery` | Layered rolling emerald hills, cumulus clouds, smiling sun | `COMPOSE_ADAPT` |
| `railway_track` | Grounded gravel ballast bed and wooden ties | `CREATE_ORIGINAL` |

---

## 3. Evidence Artifacts

- `01-before-1024x600.png`: Pre-productization baseline screenshot.
- `02-after-main-1024x600.png`: Productized main view at reference resolution.
- `03-after-active-state.png`: Dynamic active gameplay state with animations.
- `04-best-product-proof.png`: High-delight proof demonstrating visual polish.
- `05-responsive-1366x768-compact.png`: Responsive scaling in compact 1366×768 viewport.
- `06-responsive-1280x800-normal.png`: Responsive scaling in normal 1280×800 viewport.
- `07-static-or-motion-disabled.png`: Visual layout proof under static conditions.
- `08-fail-soft-proof.png`: Fail-soft fallback rendering proof.

---

## 4. Verification & Asset Performance
- All assets are authored as clean SVG masters and pre-rendered as crisp runtime PNGs under `assets/runtime/`.
- In-memory scale caching ensures zero per-frame smoothscaling overhead.
- All focused contract tests pass.
