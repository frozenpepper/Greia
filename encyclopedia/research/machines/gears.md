# Gears — factual authoring record

**Page ID:** `machines.gears`  
**Research status:** READY FOR PILOT AUTHORING  
**Reviewed:** 2026-08-27  
**Purpose:** provenance and child-safe wording authority for the first Greia Encyclopedia gears entry.

This is authoring/review material, not runtime prose. The child page should teach through a visible gear train the child can reverse, speed up and rearrange conceptually.

## Source set

### Open University — gears and gearing

- *Manufacturing: 1.13 Gears and gearing*  
  `https://www.open.edu/openlearn/mod/oucontent/view.php?id=3226&section=1.13`

Supported concepts:

- meshing gear teeth transfer rotational motion;
- directly meshed gears rotate in opposite directions;
- gear ratio can be expressed through gear size/tooth count;
- different ratios change rotational speed.

### University of Texas at Austin — Simple Machines: Gears

- `https://lecturedemos.ph.utexas.edu/demo/76`

Supported concepts:

- gears can be combined in gear trains;
- geared mechanisms can convert rotational and translational/linear motion using a gear and rack;
- mechanical advantage is a useful property of simple-machine systems.

### Cornell University — Reuleaux Kinematic Mechanisms Collection

- *Two Coupled Spur Gear Sets for Reverse Motion*  
  `https://digital.library.cornell.edu/catalog/ss:372568`

Supporting example:

- directly coupled spur gears in the documented mechanism rotate in opposite directions.

## Accepted pilot claims

1. **Teeth transfer turning.** When gear teeth mesh, turning one gear can turn the next.
2. **Neighbors reverse direction.** Two directly meshed ordinary spur gears rotate in opposite directions.
3. **Size changes speed.** A large gear driving a smaller gear makes the smaller gear rotate faster; a small gear driving a larger gear makes the larger gear rotate more slowly.
4. **Gear trains pass motion along.** Several meshed gears can carry rotation through a mechanism; each direct mesh reverses direction.
5. **Rotary motion can become straight motion.** A round gear meshed with a straight toothed rack can move the rack back and forth.

The page deliberately avoids claiming a universal increase in `power`. Ideal gears trade speed and torque; real machines also have losses. Those distinctions are beyond the first child page and should not be flattened into a false statement.

## Child-facing wording contract

Dani uses the accepted prerecorded `dani_system_speech` production path.

### Intro — Dani

**Italian**  
`Ingranaggi pronti! I denti si incastrano e fanno passare il movimento da una ruota all'altra. Prova a farli girare!`

**English**  
`Gears ready! Their teeth mesh together and pass motion from one wheel to the next. Try turning them!`

### Meshing teeth — Dani

**Italian**  
`I denti di due ingranaggi si incontrano. Quando uno gira, spinge i denti dell'altro e lo fa girare.`

**English**  
`The teeth of two gears meet. When one turns, it pushes the teeth of the other and makes it turn.`

### Direction — Dani

**Italian**  
`Due ingranaggi che si toccano girano in direzioni opposte. Se il primo gira a destra, il vicino gira a sinistra.`

**English**  
`Two gears that mesh turn in opposite directions. If the first turns one way, its neighbor turns the other way.`

### Size and speed — Dani

**Italian**  
`Se un ingranaggio grande fa girare uno piccolo, quello piccolo gira più veloce. Se uno piccolo fa girare uno grande, quello grande gira più lentamente.`

**English**  
`When a large gear drives a small gear, the small one turns faster. When a small gear drives a large gear, the large one turns more slowly.`

### Round to straight motion — Dani

**Italian**  
`Un ingranaggio rotondo può anche spingere una barra con denti e trasformare un movimento che gira in un movimento diritto.`

**English**  
`A round gear can also push a toothed rack and turn spinning motion into straight-line motion.`

## Interaction-to-claim mapping

- driver/crank control -> reverse the whole gear train while maintaining correct alternating direction;
- teeth hotspot -> exaggerate/flash the touching tooth pairs;
- ratio hotspot -> swap which of a large/small pair is the driver and visibly change relative angular speed;
- train hotspot -> highlight motion propagation through three gears;
- rack hotspot -> drive a small straight toothed rack left/right from a rotating pinion.

## Engineering guardrails

- Use deterministic angle relationships rather than a physics engine.
- Keep tooth counts low enough for clear rendering and Acer-class cost.
- The model should own gear ratios/direction; renderer code must not duplicate those rules.
- Do not recompute reusable static geometry through heavyweight transforms every frame.

## Scope guardrails

- Do not say gears create energy or power.
- Do not imply bigger gears are always `stronger` without defining the mechanical arrangement.
- Do not teach exact torque equations in the first page.
- Do not use a bicycle chain example as if chain-linked sprockets obey the same direction rule as directly meshed gears.