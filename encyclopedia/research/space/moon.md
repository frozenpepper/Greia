# Moon — factual authoring record

**Page ID:** `space.moon`  
**Research status:** READY FOR AUTHORING  
**Reviewed:** 2026-08-27  
**Purpose:** provenance and child-safe wording authority for the Greia Encyclopedia Moon entry.

This page should directly address common early-childhood misconceptions: phases are not the Moon changing shape, the far side is not permanently dark, and seeing one face does not mean the Moon never rotates.

## Source set

Primary authorities:

- NASA Science — *Moon Facts*  
  `https://science.nasa.gov/moon/facts/`
- NASA Science — *Moon Phases*  
  `https://science.nasa.gov/moon/moon-phases/`
- NASA Science — *Top Moon Questions*  
  `https://science.nasa.gov/moon/top-moon-questions/`

Supported concepts used by this page:

- the Moon is Earth's only natural satellite;
- it orbits Earth at an average distance of about 384,400 km;
- the Moon is less than one-third Earth's width;
- it rotates once in the same time it takes to orbit Earth, so essentially the same hemisphere faces Earth;
- lunar phases happen because we see changing portions of the Moon's sunlit half as it orbits Earth;
- there is no permanently dark side of the Moon;
- the Moon has a solid rocky, cratered surface and a very thin exosphere;
- surface gravity is about one-sixth Earth's gravity.

## Accepted claims

1. **Earth's natural satellite.** The Moon goes around Earth and is Earth's only natural satellite.
2. **Phases are changing views of sunlight.** Half the Moon is illuminated by the Sun at any moment; from Earth we see different fractions of that lit half during its orbit.
3. **The Moon really rotates.** It spins once per orbit, which is why essentially the same side keeps facing Earth. The far side also receives sunlight.
4. **A cratered rocky world.** The surface is solid rock and dust marked by many impact craters and ancient dark lava plains.
5. **Lower gravity.** Surface gravity is about one-sixth Earth's, so the same object would weigh less there.

## Child-facing wording contract

### Intro — Leo

**Italian**  
`Ecco la Luna, il satellite naturale della Terra. Le gira intorno e ci mostra quasi sempre la stessa faccia, ma la Luna gira davvero anche su se stessa.`

**English**  
`Here is the Moon, Earth's natural satellite. It travels around Earth and shows us almost the same face, but the Moon really does spin on its axis too.`

### Phases — Leo

**Italian**  
`La Luna non cambia forma. Il Sole ne illumina sempre metà e, mentre la Luna gira intorno alla Terra, noi vediamo porzioni diverse della metà illuminata: sono le fasi lunari.`

**English**  
`The Moon does not change shape. The Sun always lights half of it, and as the Moon travels around Earth we see different portions of that lit half. Those are the Moon's phases.`

### Same side and rotation — Leo

**Italian**  
`La Luna ruota una volta mentre completa un giro intorno alla Terra. Per questo ci mostra quasi sempre lo stesso lato. Il lato lontano non è sempre buio: riceve anche lui la luce del Sole.`

**English**  
`The Moon rotates once while it completes one orbit around Earth. That is why it shows us almost the same side. The far side is not always dark; it receives sunlight too.`

### Surface — Leo

**Italian**  
`La Luna è un mondo roccioso coperto di polvere e crateri da impatto. Le grandi zone scure sono antiche pianure riempite molto tempo fa da lava.`

**English**  
`The Moon is a rocky world covered with dust and impact craters. Its large dark areas are ancient plains that were filled by lava long ago.`

### Gravity — Leo

**Italian**  
`Sulla Luna la gravità in superficie è circa un sesto di quella terrestre. Per questo gli astronauti possono sembrare molto più leggeri quando si muovono.`

**English**  
`Surface gravity on the Moon is about one-sixth as strong as Earth's. That is why astronauts can look much lighter as they move around.`

## Interaction-to-claim mapping

- phases hotspot -> step through eight familiar phase views while keeping one fixed Sun direction visible;
- rotation hotspot -> animate Moon orbit + spin together with one marked face kept toward Earth;
- surface hotspot -> toggle crater/highland and dark-maria highlights;
- gravity hotspot -> compare one identical schematic hop on Earth and on the Moon with clearly exaggerated teaching arcs.

## Engineering guardrails

- phase shapes are deterministic geometry/state, not masks or image processing;
- orbit/rotation demo uses simple trigonometry;
- hop comparison is a fixed schematic animation, not a physics engine;
- crater and maria shapes are fixed-count.

## Scope guardrails

- do not call the far side the `dark side` as if it never receives sunlight;
- do not explain ordinary phases as Earth's shadow; Earth's shadow is relevant to lunar eclipses, not the monthly phase cycle;
- do not imply the Moon is literally weightless;
- do not use a live/current lunar phase as page truth; the encyclopedia teaches the general cycle offline.
