# Greia achievement award frames

Flat SVG masters for the child Badge Library and celebration, authored under
`docs/design/GREIA_SVG_AUTHORING_RULES.md` (2026-10-16 redraw; the earlier
glossy `feDropShadow` medals were retired).

## Masters

| File | Family | Shape |
|---|---|---|
| `award_bronze.svg` | bronze | round copper medal, two short blue ribbons |
| `award_silver.svg` | silver | scalloped silver-blue medal, longer ribbons |
| `award_gold.svg` | gold | cup trophy on a plinth |
| `award_special.svg` | special / secret | purple rosette with purple ribbons over a star burst |
| `award_<family>_locked.svg` | locked | the same silhouette in grey with a padlock |

Each master is 256×256 with an empty cream centre slot. The Shell composites
the admitted Activity emblem (or the Greia `icon_id` fallback) into that slot
at runtime; the slot circles are pinned in
`greia_platform.pygame_achievements.AWARD_SLOTS` and by
`tests/test_pygame_achievements.py`. Masters carry no contact shadow: the
Shell grounds, hops and flies the sprite itself.

## Runtime contract

These SVGs are source only. `assets/catalog/shared_visuals_v1_source.toml`
registers `ui.award.<family>` with `default`/`size_112`/`size_64` and
`locked`/`locked_112`/`locked_64` renditions (160/112/64 px PNGs under
`assets/visual/runtime/v1/ui/awards/`); rebuild with `make visual-assets` and
check with `make visual-assets-check`. Runtime never decodes SVG. When the
renditions are unavailable, `PygameAchievementBadgeRenderer` falls back to its
procedural frames.

Tier = shape + colour, legible in greyscale at 48 px. Achievement meaning stays
separate from the frame: the frame says milestone depth, the centre says what
the child did.
