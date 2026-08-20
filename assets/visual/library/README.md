# Greia Shared Visual Library v0.1

This is the shared Greia artwork/animation library seed.

Current contents:

- core characters: Lilli, Nino, Tito, Momo;
- accepted neutral artwork from `assets/visual/specimens/a1/`;
- real authored blink variants in `assets/visual/characters/<id>/blink.svg`;
- shared base animation vocabulary in `assets/visual/library/animations.toml`;
- browser review in `assets/visual/library/review.html`.

Rules:

1. Do not redraw a character merely to animate it.
2. Reuse the same shared art across Shell and Activities.
3. `blink` must actually close the eyes.
4. Base motion uses simple translate/rotate/squash/stretch.
5. Add reusable props/scenes/FX/UI assets to this shared library rather than recreating them per Activity.

This is currently design/source artwork. Runtime consumption comes later through one shared Greia asset path.