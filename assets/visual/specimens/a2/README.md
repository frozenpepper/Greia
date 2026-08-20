# Greia A2 Expression/Motion Specimens

Status: candidate design/evidence harness, not runtime assets.

Open `review.html` to compare the Base Animation Set v0.1 on Lilli (Puff), Nino (Bean), and an Object Friend.

The harness uses exact A1 SVG body masters with semantic face replacement/overlays. It applies only bounded whole-body transforms and bounded decorative FX.

Authoritative candidate design spec:

`docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`

Machine-readable authoring/design seeds:

```text
assets/visual/specimens/a2/expression_templates_v0.1.toml
assets/visual/specimens/a2/base_motion_v0.1.toml
```

The expression template file records the nine persistent semantic face states, transient blink, and explicit rejection cues such as angry/disappointed-at-the-child treatment for `sad_gentle`.

`runtime_consumed = false`: this directory does not define or authorize a Greia runtime animation API.
