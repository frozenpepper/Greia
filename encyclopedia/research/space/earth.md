# Earth — factual authoring record

**Page ID:** `space.earth`  
**Research status:** READY FOR AUTHORING  
**Reviewed:** 2026-08-27  
**Purpose:** provenance and child-safe wording authority for the Greia Encyclopedia Earth-as-a-planet entry.

This page is the Space-section view of Earth. It should complement, not duplicate, the separate `earth` section about terrestrial nature and processes.

## Source set

Primary authority:

- NASA Science — *Facts About Earth*  
  `https://science.nasa.gov/earth/facts/`

Supporting authority:

- NASA Science / Earth Observatory — *The Water Cycle*  
  `https://science.nasa.gov/earth/earth-observatory/the-water-cycle/`

Supported concepts used by this page:

- Earth is the third planet from the Sun and a rocky terrestrial planet;
- Earth rotates once in about 23.9 hours, producing the familiar day/night cycle as different parts face toward or away from the Sun;
- Earth takes about 365.25 days to orbit the Sun;
- Earth's rotational axis is tilted about 23.4 degrees, and this tilt drives the yearly seasons;
- oceans cover most of Earth's surface and hold most of its water;
- Earth has an atmosphere and is the only world currently known to support life.

## Accepted claims

1. **Our rocky world.** Earth is the third planet from the Sun and has a solid rocky crust.
2. **Rotation makes day and night.** Earth turns once in roughly one day; the side facing the Sun has daylight while the side turned away has night.
3. **A water world.** Oceans cover most of Earth's surface and contain most of the planet's water.
4. **Tilt makes seasons.** Earth's axis is tilted, so each hemisphere receives different patterns of sunlight during the year; seasons are not caused simply by Earth being closer to or farther from the Sun.
5. **A living atmosphere-covered planet.** Earth has an atmosphere and is the only world currently known to host life.

## Child-facing wording contract

### Intro — Leo

**Italian**  
`Questa è casa nostra vista dallo spazio: la Terra, il terzo pianeta dal Sole. È un mondo roccioso con oceani, aria e vita.`

**English**  
`This is our home seen from space: Earth, the third planet from the Sun. It is a rocky world with oceans, air, and life.`

### Rotation and day/night — Leo

**Italian**  
`La Terra gira continuamente. La parte rivolta verso il Sole è illuminata e vive il giorno; quella girata dall'altra parte vive la notte.`

**English**  
`Earth is always turning. The side facing the Sun is lit and has daytime; the side turned away has nighttime.`

### Water — Leo

**Italian**  
`La maggior parte della superficie terrestre è coperta d'acqua. Quasi tutta l'acqua del pianeta si trova negli oceani.`

**English**  
`Most of Earth's surface is covered by water. Almost all of the planet's water is held in the oceans.`

### Seasons — Leo

**Italian**  
`L'asse della Terra è inclinato. Mentre la Terra gira intorno al Sole, questa inclinazione cambia quanta luce ricevono i due emisferi e crea le stagioni.`

**English**  
`Earth's axis is tilted. As Earth travels around the Sun, that tilt changes how much sunlight each hemisphere receives and creates the seasons.`

### Atmosphere and life — Leo

**Italian**  
`La Terra è avvolta da un'atmosfera di gas. È anche l'unico mondo che conosciamo finora dove esiste la vita.`

**English**  
`Earth is wrapped in an atmosphere of gases. It is also the only world we currently know that has life.`

## Interaction-to-claim mapping

- rotation hotspot -> rotate a simple Earth disk relative to a fixed Sun and visibly move the day/night boundary;
- water hotspot -> highlight the ocean-covered portion of the globe without pretending the map is geographically exact;
- seasons hotspot -> tilt the axis and show two opposite hemisphere sunlight-emphasis states;
- atmosphere/life hotspot -> reveal a thin atmospheric halo and a few symbolic land/ocean life marks.

## Engineering guardrails

- no globe texture, 3-D engine, shader or live map data;
- day/night boundary is a simple clipped overlay;
- seasonal demo uses two or four finite states, not orbital physics;
- all decorative stars and life markers are fixed-count.

## Scope guardrails

- do not teach seasons as caused by changing Earth-Sun distance;
- do not imply the schematic ocean/continent shapes are a geographic map;
- do not claim Earth is the only possible place for life, only the only one currently known to host it;
- do not duplicate the broader water-cycle/nature material owned by the `earth` section.
