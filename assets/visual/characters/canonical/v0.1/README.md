# Greia Canonical Characters v0.1

Promoted stable source vector assets for Greia's six canonical mascots:
1. **Lilli** (`character.lilli`) — Unicorn Puff (Creativity / Stories / Art)
2. **Leo** (`character.leo`) — Owl Bean (Learning / Reading / Knowledge)
3. **Flash** (`character.flash`) — White Rabbit Puff (Games / Speed / Action)
4. **Dani** (`character.dani`) — Friendly Robot (Math / Logic / Patterns)
5. **Tito** (`character.tito`) — Fox Puff (Exploration / Discovery)
6. **Momo** (`character.momo`) — Friendly Monster Puff (Emotion / Music / Silly Play)

Each character provides:
- `source_master.svg`: Semantically grouped master with all layers
- 5 registered complete state SVGs: `neutral.svg`, `blink.svg`, `happy.svg`, `surprised.svg`, `sleepy.svg`
- 2 shared cast poses: `pose_cheer.svg` (celebration: raised appendages, happy face, small hop) and `pose_point.svg` (one appendage pointing toward the viewer's right, eyes glancing right, open explaining smile)
- `components/`: Standalone authoring components (source-level building blocks)

## Shared cast poses

Poses follow `docs/design/GREIA_SVG_AUTHORING_RULES.md` §8: every silhouette,
identity and appendage path is copied verbatim from the canonical states; only
whole-character translate/lean (≤ 3°), appendage rotation about its root and a
face built from the existing eye/mouth vocabulary are applied. Legless puffs
(Lilli, Flash, Tito) raise their front hooves/paws; Leo uses a wing, Dani and
Momo their arms.

Activities load them as runtime PNGs through the shared visual resolver, e.g.
`get_shared_visual("character.leo", variant="pose_cheer")` /
`variant="pose_point"`; they are registered in
`assets/catalog/shared_visuals_v1_source.toml` and rendered by
`tools/build_visual_renditions.py` into
`assets/visual/runtime/v1/characters/<id>_pose_{cheer,point}.png`.
Activities should use these instead of drawing cast members themselves.

