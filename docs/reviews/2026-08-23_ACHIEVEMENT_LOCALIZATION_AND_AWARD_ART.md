# Achievement Localization and Award Art Review — 2026-08-23

## Scope

Post-acceptance correction and visual refinement of the shared Greia achievement experience.

The owner/local agent completed the full interactive achievement/activity Simulator acceptance on commit:

```text
850bf6d9e0857f7606253b8fa4e68fc4eee9ebec
```

That acceptance reported 1,110/1,110 unit tests passing plus the complete interactive Badge Library / Clinic / Memory / Bridges progression protocol.

**Important provenance rule:** that acceptance predates the localization/art changes in this review. Do not cite the 1,110-pass result as execution evidence for the commits below.

## Bug found after acceptance

On an Italian Simulator launch, the Badge Library displayed English Shell chrome (`MY BADGES`, `NEW BADGE!`) even though the seed achievement definitions already contained Italian title/description/hint copy.

Root cause:

1. the Simulator correctly supplied `GREIA_PROFILE_LOCALE=it` and `GREIA_DEVICE_LOCALE=it`;
2. `AchievementLibraryMixin` first called `SystemLanguageStore.from_environment().read()`;
3. a Simulator workspace has no installed-device language record;
4. `SystemLanguageStore.read()` therefore *successfully* returned its normal platform default (`en`);
5. because this was not an exception, the old environment fallback was never consulted;
6. the achievement Shell chrome additionally used a two-way `Italian else English` branch.

This was a presentation/localization defect. Achievement authority, trusted history, progression economics, persistence and profile isolation were not involved.

## Correction

### Locale resolution

New:

```text
src/greia_launcher/achievement_localization.py
```

The achievement Shell now resolves locale in this order:

```text
explicit GREIA_PROFILE_LOCALE
explicit GREIA_DEVICE_LOCALE
persistent SystemLanguageStore
safe platform default
```

Invalid higher-priority process-local values do not hide a valid lower-priority value.

The achievement presentation refreshes locale at meaningful Shell transition boundaries (profile activation, Activity return, library open), avoiding per-frame filesystem reads while allowing Simulator/device locale changes to be observed.

### Shell chrome localization

Removed the `if Italian else English` presentation architecture.

Achievement-library Shell chrome now has a typed localization catalogue aligned with all currently declared Greia system languages:

```text
en, it, es, de, fr, zh-CN, pt, ar, hi, id, bn, sw
```

This catalogue owns only platform chrome such as library title, empty state, NEW label and NEW BADGE celebration eyebrow.

Achievement-specific title/description/locked-hint copy remains in `runtime/achievement-policy.toml`. The current seed definitions already provide complete Italian + English copy; other locales retain the achievement policy's normal fallback behavior until their definition copy is translated.

## Award visual system

The previous runtime renderer drew essentially one generic circular medallion for every tier.

`src/greia_platform/pygame_achievements.py` now has reusable visual families:

```text
bronze / silver -> scalloped medal + twin ribbons
gold            -> trophy cup
special         -> colorful rosette
secret unlocked -> special rosette + constellation/orbit accents
```

The semantic `icon_id` remains in the center. Decorative frame type never changes achievement meaning or authority.

Performance contract is preserved:

- alpha only on the small badge-sized surface;
- requested size remains clamped to 48..220 px;
- bounded `BoundedCache` remains authoritative;
- no fullscreen translucent surface;
- no runtime SVG parser;
- no repeated source-art file decode.

## Source art library

Added reusable vector masters under:

```text
assets/source/achievements/
```

Masters:

```text
medal_gold_star.svg
medal_silver_heart.svg
medal_bronze_paw.svg
trophy_gold_star.svg
rosette_special_star.svg
```

These are source masters/art direction, not runtime dependencies. The live low-resource renderer intentionally reproduces the same visual vocabulary with cached Pygame geometry. If a later asset build pipeline rasterizes these masters, it should produce bounded transparent PNG variants through the shared semantic asset catalogue rather than decode source SVGs at runtime.

## Regression coverage authored

New:

```text
tests/test_achievement_localization.py
```

Covers:

- exact Simulator failure geometry: Italian explicit launch locale + empty system-language store resolves Italian;
- profile locale priority over device locale;
- every declared Greia system language has Badge Library Shell chrome;
- Italian library strings are Italian;
- Spanish proves the architecture is not `Italian else English`;
- unknown locales fail soft to English.

Updated:

```text
tests/test_pygame_achievements.py
```

Retains cache/locked/size tests and adds medal/trophy/special family coverage plus secret-special cache coverage.

## Verification status

The code and tests above were authored through the repository connector after the owner's accepted Simulator run. This environment cannot execute the private repository test suite, and no GitHub Actions workflow was run (owner authorization is required for Actions).

Therefore the correct state is:

```text
PREVIOUS BASELINE 850bf6d: owner/local-agent ACCEPTED
NEW LOCALIZATION/ART TRANCHE: implementation + regression tests committed; local execution still required
```

Recommended focused local verification before folding this tranche into the accepted baseline:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_achievement_localization \
  tests.test_pygame_achievements \
  tests.test_achievements \
  tests.test_greia_simulator \
  -v
```

Then one visual Simulator smoke test:

1. select Italian in the Simulator;
2. Start/Apply;
3. open Badge Library;
4. verify `I MIEI DISTINTIVI`, Italian badge titles/hints and `NUOVO`/`NUOVO DISTINTIVO!` when applicable;
5. inspect bronze/silver awards and confirm the new medal art is clean at 1024×600;
6. if a gold/special test fixture is available, inspect trophy/rosette rendering;
7. idle the library and confirm no repaint regression.
