# Greia achievement award source art

This directory contains reusable vector source artwork for the child achievement system.

The visual language was developed from dedicated Greia medal/trophy concept generation on 2026-08-23 and then simplified into clean, inspectable vector masters that fit the OS style and low-resource constraints.

## Masters

- `medal_gold_star.svg` — classic gold star medal.
- `medal_silver_heart.svg` — care/kindness medal.
- `medal_bronze_paw.svg` — animal/care milestone medal.
- `trophy_gold_star.svg` — high-tier trophy cup.
- `rosette_special_star.svg` — special/secret celebration rosette.

## Runtime contract

These SVG files are **source masters**, not runtime dependencies. The current Pygame runtime deliberately renders matching medal/trophy/rosette geometry through `greia_platform.pygame_achievements.PygameAchievementBadgeRenderer` and caches the resulting tiny surfaces. This avoids adding an SVG decoder or shipping oversized source art on the Atom-class hardware floor.

If Greia later standardizes a raster build step for achievement art, rasterize these masters into bounded transparent PNG variants through the shared asset pipeline and semantic catalogue. Do not decode or scale the source SVGs every frame.

Achievement meaning remains separate from the frame: the centre icon comes from each trusted achievement definition (`icon_id`), while bronze/silver/gold/special frames communicate milestone depth only.
