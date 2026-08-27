# Venus — factual authoring record

**Page ID:** `space.venus`  
**Research status:** READY FOR AUTHORING  
**Reviewed:** 2026-08-27  
**Purpose:** provenance and child-safe wording authority for the Greia Encyclopedia Venus entry.

This is authoring/review material, not runtime prose. The child page should contrast Venus's bright cloud-covered appearance with the very hot rocky world hidden underneath.

## Source set

Primary authority:

- NASA Science — *Venus: Facts*  
  `https://science.nasa.gov/venus/venus-facts/`

Supporting authority:

- NASA Science — *Solar System Temperatures*  
  `https://science.nasa.gov/resource/solar-system-temperatures/`

Supported concepts used by this page:

- Venus is the second planet from the Sun and similar to Earth in size and internal structure;
- Venus is the hottest planet in the solar system even though Mercury is closer to the Sun;
- its dense atmosphere is mostly carbon dioxide and traps heat through an extreme greenhouse effect;
- thick clouds contain sulfuric acid and hide the rocky surface from ordinary visible-light views;
- Venus has mountains, valleys and many volcanic features;
- Venus rotates very slowly and in the opposite direction from most planets.

## Accepted claims

1. **Second planet, Earth-sized neighbor.** Venus is second from the Sun and is similar in size to Earth.
2. **Hottest planet.** Its dense carbon-dioxide atmosphere traps heat so strongly that Venus is hotter than Mercury.
3. **Cloud-covered rocky surface.** Thick clouds hide a rocky world with mountains and many volcanic features.
4. **Backward, slow rotation.** Venus rotates in the opposite direction from most planets and turns very slowly.

## Child-facing wording contract

### Intro — Leo

**Italian**  
`Questa è Venere. Da lontano sembra avvolta da nuvole tranquille, ma sotto quelle nuvole c'è un mondo roccioso caldissimo.`

**English**  
`This is Venus. From far away it looks wrapped in calm clouds, but beneath those clouds is an extremely hot rocky world.`

### Earth-size comparison — Leo

**Italian**  
`Venere è il secondo pianeta dal Sole ed è quasi grande quanto la Terra. Per questo i due pianeti vengono spesso confrontati.`

**English**  
`Venus is the second planet from the Sun and is nearly the same size as Earth, so the two planets are often compared.`

### Hottest planet — Leo

**Italian**  
`Venere è il pianeta più caldo del Sistema Solare. La sua atmosfera molto densa, ricca di anidride carbonica, intrappola tantissimo calore.`

**English**  
`Venus is the hottest planet in the solar system. Its very dense, carbon-dioxide-rich atmosphere traps an enormous amount of heat.`

### Clouds and surface — Leo

**Italian**  
`Spesse nuvole nascondono la superficie di Venere. Sotto ci sono rocce, montagne, valli e tantissime forme vulcaniche.`

**English**  
`Thick clouds hide Venus's surface. Underneath are rocks, mountains, valleys, and many volcanic features.`

### Backward rotation — Leo

**Italian**  
`Venere gira molto lentamente e ruota al contrario rispetto alla maggior parte dei pianeti. Lì il Sole sembrerebbe sorgere a ovest e tramontare a est.`

**English**  
`Venus turns very slowly and rotates backward compared with most planets. There, the Sun would appear to rise in the west and set in the east.`

## Interaction-to-claim mapping

- Earth-size hotspot -> place Earth and Venus disks side by side at intentionally comparable schematic scale;
- heat hotspot -> reveal a thick atmosphere/heat-trapping overlay and contrast Venus with Mercury;
- clouds hotspot -> toggle opaque cloud layer to a simplified rocky/volcanic surface view;
- rotation hotspot -> animate a slow reverse-direction arrow around Venus.

## Engineering guardrails

- cloud/surface reveal is a two-state layer toggle, not transparency-heavy per-pixel simulation;
- atmosphere heat visualization uses a few fixed arcs/rings;
- reverse rotation is simple angle math;
- no live mission/weather data.

## Scope guardrails

- do not say Venus is hottest merely because it is close to the Sun;
- do not say the cloud layer is ordinary water cloud;
- do not present speculative current volcanism status as settled child fact;
- do not use the sensational nickname `evil twin` in child-facing copy.
