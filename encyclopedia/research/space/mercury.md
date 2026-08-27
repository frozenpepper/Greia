# Mercury — factual authoring record

**Page ID:** `space.mercury`  
**Research status:** READY FOR AUTHORING  
**Reviewed:** 2026-08-27  
**Purpose:** provenance and child-safe wording authority for the Greia Encyclopedia Mercury entry.

This is authoring/review material, not runtime prose. The runtime page should make Mercury's small size, fast orbit, cratered surface and extreme day/night contrast visible through a few bounded state changes.

## Source set

Primary authority:

- NASA Science — *Mercury: Facts*  
  `https://science.nasa.gov/mercury/facts/`

Supporting authority:

- NASA Science — *Solar System Temperatures*  
  `https://science.nasa.gov/resource/solar-system-temperatures/`

Supported concepts used by this page:

- Mercury is the closest planet to the Sun and the smallest major planet;
- it completes an orbit around the Sun in 88 Earth days;
- it has only a very thin exosphere rather than a substantial heat-retaining atmosphere;
- sunlit and nighttime surface temperatures differ enormously;
- the surface is heavily cratered;
- permanently shadowed polar craters can preserve water ice.

## Accepted claims

1. **Closest and smallest.** Mercury is the closest planet to the Sun and the smallest major planet in our solar system.
2. **Fast year.** One Mercury year lasts only 88 Earth days.
3. **Huge temperature contrast.** Its sunlit surface can become extremely hot while nighttime areas become extremely cold because Mercury lacks a thick atmosphere that would retain and redistribute heat.
4. **Cratered world.** Impacts have left many craters and bright crater rays on the surface.
5. **Polar ice.** Some permanently shadowed craters near Mercury's poles can contain water ice despite the planet's closeness to the Sun.

## Child-facing wording contract

### Intro — Leo

**Italian**  
`Questo piccolo mondo è Mercurio, il pianeta più vicino al Sole. È il più piccolo dei pianeti principali e corre intorno al Sole molto velocemente.`

**English**  
`This small world is Mercury, the planet closest to the Sun. It is the smallest major planet, and it races around the Sun very quickly.`

### Place and size — Leo

**Italian**  
`Mercurio è il pianeta più vicino al Sole ed è anche il più piccolo degli otto pianeti principali.`

**English**  
`Mercury is the planet closest to the Sun, and it is also the smallest of the eight major planets.`

### Fast year — Leo

**Italian**  
`Mercurio completa un giro intorno al Sole in appena ottantotto giorni terrestri. Il suo anno è molto più corto del nostro.`

**English**  
`Mercury goes around the Sun in only eighty-eight Earth days. Its year is much shorter than ours.`

### Hot and cold — Leo

**Italian**  
`Mercurio non ha una spessa atmosfera che trattenga il calore. Al Sole può diventare caldissimo, mentre nella notte può diventare freddissimo.`

**English**  
`Mercury does not have a thick atmosphere to hold heat. In sunlight it can become extremely hot, while at night it can become extremely cold.`

### Craters and polar ice — Leo

**Italian**  
`La superficie di Mercurio è piena di crateri. E c'è una sorpresa: nei crateri polari che restano sempre in ombra può conservarsi ghiaccio d'acqua.`

**English**  
`Mercury's surface is covered with craters. And there is a surprise: water ice can survive in polar craters that stay permanently in shadow.`

## Interaction-to-claim mapping

- place/size hotspot -> compare Mercury with a larger Earth disk and show it nearest the Sun;
- orbit hotspot -> run one quick bounded orbit around a schematic Sun;
- temperature hotspot -> toggle a stark sunlit/night-side visual with warm/cold markers;
- crater hotspot -> reveal several crater/ray overlays and a small polar-shadow ice marker.

## Engineering guardrails

- orbit animation uses simple trigonometry, no physics engine;
- crater set is fixed and predeclared;
- day/night comparison is a state toggle, not a lighting engine;
- no changing astronomical ephemeris or network data.

## Scope guardrails

- do not call Mercury the hottest planet; Venus is hotter because of its dense atmosphere;
- do not say Mercury has literally no gas around it; NASA describes a thin exosphere;
- do not imply the whole polar region is icy;
- do not imply every crater contains water ice.
