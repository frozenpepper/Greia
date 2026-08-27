# Sun — factual authoring record

**Page ID:** `space.sun`  
**Research status:** READY FOR AUTHORING  
**Reviewed:** 2026-08-27  
**Purpose:** provenance and child-safe wording authority for the Greia Encyclopedia Sun entry.

This is authoring/review material, not runtime prose. The child page should make the Sun feel active and enormous without heavy simulation.

## Source set

Primary authority:

- NASA Science — *Sun: Facts*  
  `https://science.nasa.gov/sun/facts/`

Supported concepts used by this page:

- the Sun is the only star in our solar system and sits at its center;
- the Sun is a hot ball of plasma, mostly hydrogen and helium, not a solid object;
- its gravity holds the solar system together;
- nuclear fusion in the core converts hydrogen into helium and powers the Sun's light and heat;
- the Sun is roughly 100 times wider than Earth;
- because the Sun is not solid, different latitudes rotate at different rates: roughly 25 Earth days at the equator and 36 Earth days near the poles.

## Accepted claims

1. **Our star.** The Sun is the only star in our solar system and is at its center.
2. **No solid surface.** It is a huge ball of very hot plasma rather than a solid rocky body.
3. **Fusion powers it.** Nuclear fusion in the core combines hydrogen into helium and releases the energy that ultimately leaves as heat and light.
4. **Enormous compared with Earth.** The Sun is about 100 times wider than Earth.
5. **Different parts rotate at different speeds.** Its equator rotates faster than regions near its poles because the Sun is not solid.

The scale comparison is intentionally approximate and child-facing. Do not imply exactly 100 Earths fit through the diameter in a packing/geometric sense; it is a width comparison.

## Child-facing wording contract

### Intro — Leo

**Italian**  
`Questa è la nostra stella: il Sole! È una gigantesca palla di plasma caldissimo e tiene il Sistema Solare unito con la sua gravità.`

**English**  
`This is our star: the Sun! It is a gigantic ball of extremely hot plasma, and its gravity helps hold the solar system together.`

### Star and plasma — Leo

**Italian**  
`Il Sole è l'unica stella del nostro Sistema Solare. Non ha una superficie solida come la Terra: è fatto soprattutto di plasma, idrogeno ed elio.`

**English**  
`The Sun is the only star in our solar system. It has no solid surface like Earth; it is made mostly of plasma, hydrogen, and helium.`

### Scale — Leo

**Italian**  
`Il Sole è enorme: è largo circa cento volte la Terra. Guarda quante piccole Terre servono per attraversare il suo diametro!`

**English**  
`The Sun is enormous: it is about one hundred times wider than Earth. Look how many tiny Earth widths fit across its diameter!`

### Fusion — Leo

**Italian**  
`Nel nucleo del Sole, l'idrogeno si unisce e forma elio. Questo processo si chiama fusione e libera l'energia che ci arriva come luce e calore.`

**English**  
`In the Sun's core, hydrogen joins together to form helium. This process is called fusion, and it releases the energy that reaches us as light and heat.`

### Rotation — Leo

**Italian**  
`Il Sole non è solido, quindi non gira tutto alla stessa velocità. Vicino all'equatore ruota più in fretta che vicino ai poli.`

**English**  
`The Sun is not solid, so it does not all rotate at the same speed. Near its equator it turns faster than near its poles.`

## Interaction-to-claim mapping

- star/plasma hotspot -> reveal a simple glowing plasma-layer animation rather than a solid crust;
- scale hotspot -> draw a bounded row of Earth-width markers across the Sun's diameter;
- fusion hotspot -> pulse a bright core and send a few bounded energy rings outward;
- rotation hotspot -> show two surface marker bands rotating at visibly different schematic rates.

## Engineering guardrails

- no fluid/plasma simulation;
- all energy particles/rings are fixed-count or timer-derived;
- no per-frame asset decoding or scaling;
- differential rotation is schematic, not a physical surface simulation.

## Scope guardrails

- do not call the photosphere a solid surface;
- do not say the Sun is on fire in the ordinary combustion sense;
- do not turn approximate scale language into an exact packing claim;
- do not add current solar-storm forecasts or time-sensitive solar-cycle status to this offline v0.1 page.
