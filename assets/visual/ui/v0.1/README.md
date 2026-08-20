# Greia Shared UI Visual Pack v0.1

Status: **candidate reusable visual pack**.

This is an individual-asset pack, not a launcher mockup.

Current reusable visual masters cover:

- panel / sheet;
- default, focused and completed activity cards;
- primary, primary-hover, primary-pressed, disabled, secondary, quiet and icon buttons;
- default + selected tabs;
- new / completed / favorite / locked badges;
- progress track / fill / complete;
- speech + thought bubbles;
- reward and avatar frames;
- loading orbit, gentle-error cloud and empty basket;
- category/location portal frame;
- common focus ring, soft shadow and highlight sheen.

The semantic UI architecture remains owned by Greia's accepted UI contracts. These files supply only the reusable visual treatment.

The artwork follows `runtime/theme-defaults.toml` and deliberately avoids embedded child-facing text so labels can be localized and reused.

Review requirements:

- inspect on cream, sky and dark grounds;
- verify focus/selected state is not color-only;
- verify pressed/disabled/completed states remain visually distinct without animation;
- verify highlights/shadows survive 800×600 / 1024×600 scaling;
- reject generic web-app chrome or over-glossy treatment;
- do not turn these candidate SVGs into a parallel UI runtime.

`catalog.toml` is the candidate inventory. `REVIEW.md` records the current evidence boundary. `runtime_consumed = false` remains authoritative for this pack.
